from uuid import uuid4
import hashlib
from sqlalchemy import select
from app.db.storage import files_table,transaction,now,enqueue
from app.adapters import storage,antivirus
from app.workers.pdf_check import validate_pdf
from app.api.dependencies import ActorContext
from app.services.authority import account_authority

class FileQuarantineError(Exception):
    def __init__(self,code,message=None,status_code=409):
        super().__init__(message or code);self.code,self.status_code=code,status_code

def scan_pdf_bytes_and_structure(raw_bytes,**unused):
    try:
        validate_pdf(raw_bytes)
        return True,None
    except (ValueError,RuntimeError):
        return False,'INVALID_PDF_STRUCTURE'

class FileQuarantineService:
    def initiate_upload_api_x01(self,*,actor:ActorContext,filename,mime_type='application/pdf',size_bytes=1024):
        if mime_type!='application/pdf' or not 0<size_bytes<=20*1024*1024: raise FileQuarantineError('INVALID_UPLOAD',status_code=422)
        file_id=str(uuid4());key='quarantine/'+file_id+'.pdf'
        with transaction() as conn:
            account_authority(conn,actor)
            upload_url=storage.presign_put(key,size_bytes)
            conn.execute(files_table.insert().values(id=file_id,created_at=now(),updated_at=now(),owner_user_id=actor.user_id,
                storage_key=key,filename=filename,mime_type=mime_type,byte_size=size_bytes,sha256=None,
                scan_status='PENDING_SCAN',retention_class='VERIFICATION_EVIDENCE'))
        return {'id':file_id,'scan_status':'PENDING_SCAN','upload_url':upload_url,'expires_in_seconds':300}

    def complete_upload(self,file_id,actor:ActorContext):
        with transaction() as conn:
            record=conn.execute(select(files_table).where(files_table.c.id==file_id).with_for_update()).mappings().first()
            if not record or record['owner_user_id']!=actor.user_id: raise FileQuarantineError('FILE_ACCESS_DENIED',status_code=403)
            account_authority(conn,actor)
            if record['scan_status']!='PENDING_SCAN': raise FileQuarantineError('INVALID_FILE_STATE')
            head=storage.head(record['storage_key'])
            if head['ContentLength']!=record['byte_size']: raise FileQuarantineError('FILE_SIZE_MISMATCH')
            reference=storage.response_reference(head)
            conn.execute(files_table.update().where(files_table.c.id==file_id).values(**reference.values(),object_version=reference.etag,scan_status='SCANNING',updated_at=now()))
            source={'storage_key':record['storage_key'],'byte_size':record['byte_size'],**reference.values()}
            enqueue(conn,'FILE_SCAN_REQUESTED',str(file_id),{'file_id':str(file_id),'source':source},'scan:'+str(file_id))
        return {'id':file_id,'scan_status':'SCANNING'}

    def issue_signed_download_url_api_x03(self,*,file_id,actor:ActorContext):
        with transaction() as conn:
            record=conn.execute(select(files_table).where(files_table.c.id==file_id).with_for_update()).mappings().first()
            if not record or record['owner_user_id']!=actor.user_id: raise FileQuarantineError('FILE_ACCESS_DENIED',status_code=403)
            account_authority(conn,actor)
            if record['deleted_at'] or record['scan_status']!='CLEAN': raise FileQuarantineError('FILE_NOT_CLEAN_FOR_DOWNLOAD')
            reference=storage.file_reference(record)
            return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(record['storage_key'],reference=reference)}

def run_scan(event):
    file_id=event['payload']['file_id']
    with transaction() as conn:
        record=conn.execute(select(files_table).where(files_table.c.id==file_id)).mappings().one()
    if record['scan_status']!='SCANNING': return {'state':'UNCHANGED'}
    reference=storage.file_reference(record)
    source={key:record[key] for key in ('storage_key','byte_size','storage_bucket','storage_version_id','storage_etag')}
    if event['payload'].get('source')!=source:raise FileQuarantineError('FILE_SCAN_SOURCE_CHANGED')
    raw=storage.read(record['storage_key'],reference,20*1024*1024)
    if len(raw)!=record['byte_size']:raise FileQuarantineError('FILE_SIZE_MISMATCH')
    try:
        antivirus.scan(raw)
        validate_pdf(raw)
    except ValueError:
        return {'state':'QUARANTINED','source':source}
    digest=hashlib.sha256(raw).hexdigest()
    key='private/'+str(file_id)+'/'+digest+'.pdf'
    private_reference=storage.write_private(key,raw)
    if private_reference.bucket!=reference.bucket:
        raise storage.StorageReferenceError('FILE_STORAGE_BUCKET_MISMATCH',503)
    return {'state':'CLEAN','sha256':digest,'key':key,'reference':private_reference,'source':source}

def apply_scan(conn,event,result):
    if result['state']=='UNCHANGED': return
    current=conn.execute(select(files_table).where(files_table.c.id==event['payload']['file_id']).with_for_update()).mappings().one()
    if current['scan_status']!='SCANNING':return
    storage.file_reference(current)
    if {key:current[key] for key in result['source']}!=result['source']:
        raise FileQuarantineError('FILE_SCAN_SOURCE_CHANGED')
    values={'scan_status':result['state'],'scanned_at':now(),'updated_at':now()}
    if result['state']=='CLEAN':
        reference=result['reference'];reference.check_bucket()
        values.update(sha256=result['sha256'],storage_key=result['key'],object_version=reference.version_id,**reference.values())
    conn.execute(files_table.update().where(files_table.c.id==event['payload']['file_id'],files_table.c.scan_status=='SCANNING').values(**values))

file_quarantine_service=FileQuarantineService()
