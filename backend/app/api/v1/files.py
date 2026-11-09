from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from app.services.files_quarantine import file_quarantine_service

router=APIRouter(prefix='/api/v1/files',tags=['files'])
class InitiateUploadRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filename:str=Field(min_length=1,max_length=200)
    mime_type:str='application/pdf'
    size_bytes:int=Field(gt=0,le=20*1024*1024)

@router.post('/upload-intents',status_code=201)
@router.post('/upload-init',status_code=201,include_in_schema=False)
def upload(payload:InitiateUploadRequest,actor:ActorContext=Depends(require_actor_context)):
    return file_quarantine_service.initiate_upload_api_x01(actor=actor,**payload.model_dump())

@router.post('/{file_id}/complete-upload',status_code=202)
def complete(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return file_quarantine_service.complete_upload(str(file_id),actor)

@router.post('/{file_id}/complete-scan',include_in_schema=False)
def retired_scan(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    raise HTTPException(410,detail={'code':'CLIENT_SCAN_REMOVED','message':'Complete upload; the worker scans stored bytes'})

@router.get('/{file_id}/download')
def download(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return file_quarantine_service.issue_signed_download_url_api_x03(file_id=str(file_id),actor=actor)
