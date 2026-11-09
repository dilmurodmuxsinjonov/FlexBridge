"""Real PostgreSQL with explicit test doubles at external service boundaries."""
import io
import socket
import struct
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.db.storage import table,transaction,now,enqueue,outbox_table
from app.services.billing import BillingInvariantError
from app.services.files_quarantine import file_quarantine_service
from app.adapters import storage,antivirus
from test_regressions import checkout,capture,count,billing

def draft(owner,org):
    from app.services.opportunities import opportunity_service
    return opportunity_service.create_opportunity_revision(organization_id=org,title='Quota test',opportunity_kind='PART_TIME_JOB',contract_type='LABOR_PART_TIME',
        compensation_type='HOURLY',hourly_pay=10000,published=False,actor_user_id=owner['user_id'])

def approve_for_test(revision):
    # A test fixture models an independent moderation decision; HTTP authors cannot assign APPROVED.
    with transaction() as conn:
        conn.execute(table('opportunities').update().where(table('opportunities').c.id==revision['opportunity_id']).values(status='APPROVED'))

def test_parallel_quota_sixth_rejected_and_close_frees_slot(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    ids=[]
    for _ in range(6):
        rev=draft(owner,organization);approve_for_test(rev);ids.append(rev['opportunity_id'])
    def publish(oid):
        try:billing.publish_opportunity_with_quota(organization_id=organization,opportunity_id=oid,actor_user_id=owner['user_id']);return oid
        except BillingInvariantError as e: assert str(e)=='CONCURRENT_QUOTA_REACHED';return None
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(publish,ids))
    assert sum(bool(r) for r in results)==5
    billing.update_opportunity_status(opportunity_id=next(r for r in results if r),new_status='CLOSED',actor_user_id=owner['user_id'])
    assert publish(ids[results.index(None)]) is not None

def test_single_credit_not_recharged_for_resume(identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization,plan='SINGLE_POST_30D');capture(a)
    rev=draft(owner,organization);approve_for_test(rev)
    kwargs={'organization_id':organization,'opportunity_id':rev['opportunity_id'],'actor_user_id':owner['user_id']}
    billing.publish_opportunity_with_quota(**kwargs)
    billing.update_opportunity_status(opportunity_id=rev['opportunity_id'],new_status='PAUSED',actor_user_id=owner['user_id'])
    assert billing.publish_opportunity_with_quota(**kwargs)['status']=='PUBLISHED'
    with transaction() as conn: assert conn.execute(select(table('service_entitlements').c.quota)).scalar_one()==0

def test_no_moderation_bypass(client,identities,organization):
    owner=identities('OWNER',organization);o,i,a=checkout(owner,organization);capture(a)
    rev=draft(owner,organization)
    r=client.post('/api/v1/opportunities/'+rev['opportunity_id']+'/publish',headers=owner['headers'])
    assert r.status_code==409,r.text

def test_canonical_orders_and_refund_requests(client,identities,organization):
    owner=identities('OWNER',organization)
    r=client.post('/api/v1/organizations/'+organization+'/orders',json={'plan_code':'ORG_PLAN_30D','idempotency_key':'canonical-order-key'},headers=owner['headers'])
    assert r.status_code==201 and r.json()['contract_id']=='API-094',r.text
    r=client.post('/api/v1/orders/'+r.json()['order']['id']+'/refund-requests',json={'amount_uzs':1,'reason':'Valid refund request reason'},headers=owner['headers'])
    assert r.status_code==409,r.text

def test_availability_scope_overlap_and_adjacent_merge(client,identities):
    from app.services.availability import availability_service
    owner,outsider=identities(),identities();url='/api/v1/candidates/'+owner['candidate_id']+'/availability-rules'
    args={'weekday':1,'start_minute':540,'end_minute':720}
    assert client.post(url,json=args,headers=outsider['headers']).status_code==403
    assert client.post(url,json=args,headers=owner['headers']).status_code==201
    assert client.post(url,json={**args,'start_minute':600},headers=owner['headers']).status_code==409
    assert client.post(url,json={**args,'start_minute':720,'end_minute':900},headers=owner['headers']).status_code==201
    assert availability_service.is_candidate_available_for_shift(candidate_id=owner['candidate_id'],weekday=1,start_minute=600,end_minute=850)

def test_foreign_org_member_role_not_global_authority(client,identities,organization):
    from app.services.placements import insert_row
    with transaction() as conn:
        other=insert_row(conn,'organizations',tax_id=str(uuid4()),legal_name='Other',public_name='Other',region='Tashkent',status='VERIFIED')
    owner=identities('OWNER',other['id'])
    assert client.get('/api/v1/organizations/'+organization+'/memberships',headers=owner['headers']).status_code==403
    assert client.post('/api/v1/billing/orders',json={'organization_id':organization,'plan_code':'ORG_PLAN_30D','idempotency_key':'outside-org-key'},headers=owner['headers']).status_code==403

def test_outbox_fencing_rejects_stale_result():
    from app.workers.outbox import relay_pending_outbox_events
    with transaction() as conn:eid=enqueue(conn,'FENCE','a',{},'fenced-event')
    applied=[]
    def reclaim(event):
        # Simulate a newer worker reclaiming the expired lease while this handler is delayed.
        with transaction() as conn:conn.execute(outbox_table.update().where(outbox_table.c.id==eid).values(claim_token=str(uuid4())))
        return 'stale-result'
    assert relay_pending_outbox_events(registry={'FENCE':(reclaim,lambda c,e,r:applied.append(r))})==0
    assert applied==[]
    with transaction() as conn:assert conn.execute(select(outbox_table.c.processed_at).where(outbox_table.c.id==eid)).scalar_one() is None

@pytest.fixture
def pdf():
    from pypdf import PdfWriter
    writer=PdfWriter();writer.add_blank_page(width=100,height=100);buf=io.BytesIO();writer.write(buf);return buf.getvalue()

@pytest.fixture
def object_store(monkeypatch,pdf):
    objects={};writes=[]
    monkeypatch.setattr(storage,'presign_put',lambda key,size:'https://test.invalid/upload')
    monkeypatch.setattr(storage,'head',lambda key:{'ContentLength':len(objects[key]),'ETag':'pinned-etag','VersionId':'quarantine-version'})
    def read(key,reference,limit):
        assert reference==storage.ObjectReference('test-private-bucket','quarantine-version','pinned-etag');assert len(objects[key])<=limit
        return objects[key]
    monkeypatch.setattr(storage,'read',read)
    def write(key,raw):objects[key]=raw;writes.append(key);return storage.ObjectReference('test-private-bucket','private-version','private-etag')
    monkeypatch.setattr(storage,'write_private',write)
    monkeypatch.setattr(storage,'presign_get',lambda key,*,reference:'https://test.invalid/download/'+key)
    return objects,writes

def upload(client,user,pdf,objects):
    r=client.post('/api/v1/files/upload-intents',headers=user['headers'],json={'filename':'cv.pdf','mime_type':'application/pdf','size_bytes':len(pdf)})
    assert r.status_code==201,r.text
    fid=r.json()['id'];objects['quarantine/'+fid+'.pdf']=pdf
    assert client.post('/api/v1/files/'+fid+'/complete-upload',headers=user['headers']).status_code==202
    return fid

def test_file_pipeline_effect_before_clean(client,identities,pdf,object_store,monkeypatch):
    from app.workers.outbox import relay_pending_outbox_events
    objects,writes=object_store;owner=identities();fid=upload(client,owner,pdf,objects)
    assert client.get('/api/v1/files/'+fid+'/download',headers=owner['headers']).status_code==409
    scanned=[];monkeypatch.setattr(antivirus,'scan',lambda raw:scanned.append(raw))
    assert relay_pending_outbox_events()==1
    assert scanned==[pdf] and len(writes)==1
    assert client.get('/api/v1/files/'+fid+'/download',headers=owner['headers']).status_code==200
    outsider=identities()
    assert client.get('/api/v1/files/'+fid+'/download',headers=outsider['headers']).status_code==403

def test_antivirus_outage_cannot_mark_clean(client,identities,pdf,object_store,monkeypatch):
    from app.workers.outbox import relay_pending_outbox_events
    objects,writes=object_store;owner=identities();fid=upload(client,owner,pdf,objects)
    def unavailable(raw):raise RuntimeError('AV unavailable')
    monkeypatch.setattr(antivirus,'scan',unavailable)
    assert relay_pending_outbox_events()==0 and writes==[]
    with transaction() as conn:assert conn.execute(select(table('files').c.scan_status).where(table('files').c.id==fid)).scalar_one()=='SCANNING'
    assert client.get('/api/v1/files/'+fid+'/download',headers=owner['headers']).status_code==409

def test_malware_quarantined(client,identities,pdf,object_store,monkeypatch):
    from app.workers.outbox import relay_pending_outbox_events
    objects,writes=object_store;owner=identities();fid=upload(client,owner,pdf,objects)
    def malware(raw):raise ValueError('Malware found')
    monkeypatch.setattr(antivirus,'scan',malware)
    assert relay_pending_outbox_events()==1 and writes==[]
    with transaction() as conn:assert conn.execute(select(table('files').c.scan_status).where(table('files').c.id==fid)).scalar_one()=='QUARANTINED'

@pytest.mark.parametrize('reply,success',[(b'stream: OK\0',True),(b'stream: Eicar-Test-Signature FOUND\0',False)])
def test_actual_clamav_instream_protocol(monkeypatch,reply,success):
    # A local TCP protocol fixture, not a live ClamAV engine.
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1)
    monkeypatch.setenv('CLAMAV_HOST','127.0.0.1');monkeypatch.setenv('CLAMAV_PORT',str(listener.getsockname()[1]))
    received=[];errors=[]
    def exact(conn,n):
        raw=b''
        while len(raw)<n:
            chunk=conn.recv(n-len(raw))
            if not chunk:raise RuntimeError('Premature EOF')
            raw+=chunk
        return raw
    def server():
        try:
            with listener.accept()[0] as conn:
                assert exact(conn,10)==b'zINSTREAM\0'
                raw=b''
                while True:
                    n=struct.unpack('!I',exact(conn,4))[0]
                    if n==0:break
                    raw+=exact(conn,n)
                received.append(raw);conn.sendall(reply)
        except Exception as e:errors.append(e)
        finally:listener.close()
    thread=threading.Thread(target=server,daemon=True);thread.start()
    if success:antivirus.scan(b'actual stream data')
    else:
        with pytest.raises(ValueError):antivirus.scan(b'actual stream data')
    thread.join(3);assert not errors and received==[b'actual stream data']

def test_s3_adapter_signature_and_bounded_read(monkeypatch):
    from botocore.stub import Stubber
    from botocore.response import StreamingBody
    for k,v in {'S3_ENDPOINT_URL':'https://objects.invalid','S3_ACCESS_KEY':'test-access','S3_SECRET_KEY':'test-secret','S3_BUCKET':'private-test'}.items():monkeypatch.setenv(k,v)
    monkeypatch.delenv('S3_PUBLIC_ENDPOINT_URL',raising=False)
    assert 'X-Amz-Signature=' in storage.presign_put('quarantine/uuid.pdf',10)
    c=storage.client();stub=Stubber(c);raw=io.BytesIO(b'a'*11)
    stub.add_response('get_object',{'Body':StreamingBody(raw,11),'VersionId':'version-1','ETag':'etag'},
        {'Bucket':'private-test','Key':'key','VersionId':'version-1','IfMatch':'etag'})
    monkeypatch.setattr(storage,'client',lambda **unused:c)
    with stub,pytest.raises(ValueError,match='TOO_LARGE'):storage.read('key',storage.ObjectReference('private-test','version-1','etag'),10)

def test_runtime_without_database_config_never_creates_sqlite(monkeypatch):
    from app.db.storage import get_database_url
    monkeypatch.delenv('DATABASE_URL',raising=False);monkeypatch.delenv('FLEXBRIDGE_DATABASE_URL',raising=False)
    with pytest.raises(RuntimeError,match='PostgreSQL'):get_database_url()
