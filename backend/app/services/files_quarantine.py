from uuid import uuid4
import hashlib
from sqlalchemy import select
from app.db.storage import files_table,transaction,now,enqueue
from app.adapters import storage,antivirus
from app.workers.pdf_check import validate_pdf

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
    def initiate_upload_api_x01(self,*,owner_id,filename,mime_type='application/pdf',size_bytes=1024):
        if mime_type!='application/pdf' or not 0<size_bytes<=20*1024*1024: raise FileQuarantineError('INVALID_UPLOAD',status_code=422)
        file_id=str(uuid4());key='quarantine/'+file_id+'.pdf'
        upload_url=storage.presign_put(key,size_bytes)
        with transaction() as conn:
            conn.execute(files_table.insert().values(id=file_id,created_at=now(),updated_at=now(),owner_user_id=owner_id,
                storage_key=key,filename=filename,mime_type=mime_type,byte_size=size_bytes,sha256=None,
                scan_status='PENDING_SCAN',retention_class='VERIFICATION_EVIDENCE'))
        return {'id':file_id,'scan_status':'PENDING_SCAN','upload_url':upload_url,'expires_in_seconds':300}

    def complete_upload(self,file_id,actor_id):
        with transaction() as conn:
            record=conn.execute(select(files_table).where(files_table.c.id==file_id).with_for_update()).mappings().first()
            if not record or record['owner_user_id']!=actor_id: raise FileQuarantineError('FILE_ACCESS_DENIED',status_code=403)
            if record['scan_status']!='PENDING_SCAN': raise FileQuarantineError('INVALID_FILE_STATE')
            head=storage.head(record['storage_key'])
            if head['ContentLength']!=record['byte_size']: raise FileQuarantineError('FILE_SIZE_MISMATCH')
            conn.execute(files_table.update().where(files_table.c.id==file_id).values(object_version=head['ETag'],scan_status='SCANNING',updated_at=now()))
            enqueue(conn,'FILE_SCAN_REQUESTED',str(file_id),{'file_id':str(file_id)},'scan:'+str(file_id))
        return {'id':file_id,'scan_status':'SCANNING'}

    def issue_signed_download_url_api_x03(self,*,file_id,requester_id):
        with transaction() as conn:
            record=conn.execute(select(files_table).where(files_table.c.id==file_id)).mappings().first()
            if not record or record['owner_user_id']!=requester_id: raise FileQuarantineError('FILE_ACCESS_DENIED',status_code=403)
            if record['deleted_at'] or record['scan_status']!='CLEAN': raise FileQuarantineError('FILE_NOT_CLEAN_FOR_DOWNLOAD')
        return {'file_id':file_id,'expires_in_seconds':60,'signed_url':storage.presign_get(record['storage_key'])}

def run_scan(event):
    file_id=event['payload']['file_id']
    with transaction() as conn:
        record=conn.execute(select(files_table).where(files_table.c.id==file_id)).mappings().one()
    if record['scan_status']!='SCANNING': return {'state':'UNCHANGED'}
    raw=storage.read(record['storage_key'],record['object_version'],20*1024*1024)
    try:
        antivirus.scan(raw)
        validate_pdf(raw)
    except ValueError:
        return {'state':'QUARANTINED'}
    digest=hashlib.sha256(raw).hexdigest()
    key='private/'+str(file_id)+'/'+digest+'.pdf'
    version=storage.write_private(key,raw)
    return {'state':'CLEAN','sha256':digest,'key':key,'version':version}

def apply_scan(conn,event,result):
    if result['state']=='UNCHANGED': return
    values={'scan_status':result['state'],'scanned_at':now(),'updated_at':now()}
    if result['state']=='CLEAN': values.update(sha256=result['sha256'],storage_key=result['key'],object_version=result['version'])
    conn.execute(files_table.update().where(files_table.c.id==event['payload']['file_id'],files_table.c.scan_status=='SCANNING').values(**values))

file_quarantine_service=FileQuarantineService()
