from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict,Field
from app.api.dependencies import ActorContext,require_actor_context
from typing import Literal
from app.services.files_quarantine import file_quarantine_service
from app.services.user_files import upload_user_pdf

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

class DirectPdfInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filename:str=Field(default='document.pdf',min_length=1,max_length=240)
    purpose:Literal['INSTITUTION_APPOINTMENT','INSTITUTION_AGREEMENT','ORGANIZATION_EVIDENCE']
    content_base64:str=Field(min_length=24,max_length=15_000_000)

@router.post('/pdf',status_code=201)
def direct_pdf(payload:DirectPdfInput,actor:ActorContext=Depends(require_actor_context)):
    """Staff evidence PDF: scanned (fail-closed) and stored before a CLEAN record exists."""
    return upload_user_pdf(actor,payload.model_dump())

@router.post('/{file_id}/complete-upload',status_code=202)
def complete(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return file_quarantine_service.complete_upload(str(file_id),actor)

@router.post('/{file_id}/complete-scan',include_in_schema=False)
def retired_scan(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    raise HTTPException(410,detail={'code':'CLIENT_SCAN_REMOVED','message':'Complete upload; the worker scans stored bytes'})

@router.get('/{file_id}/download')
def download(file_id:UUID,actor:ActorContext=Depends(require_actor_context)):
    return file_quarantine_service.issue_signed_download_url_api_x03(file_id=str(file_id),actor=actor)
