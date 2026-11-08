import os
import boto3
from botocore.config import Config

def client(public=False):
    names=['S3_ENDPOINT_URL','S3_ACCESS_KEY','S3_SECRET_KEY','S3_BUCKET']
    if not all(os.environ.get(k) for k in names):
        raise RuntimeError('S3 storage is not configured')
    endpoint=os.environ.get('S3_PUBLIC_ENDPOINT_URL') if public else None
    return boto3.client('s3',endpoint_url=endpoint or os.environ['S3_ENDPOINT_URL'],aws_access_key_id=os.environ['S3_ACCESS_KEY'],
        aws_secret_access_key=os.environ['S3_SECRET_KEY'],region_name=os.environ.get('S3_REGION','us-east-1'),
        config=Config(signature_version='s3v4',connect_timeout=3,read_timeout=15,retries={'max_attempts':2}))

def bucket(): return os.environ['S3_BUCKET']

def presign_put(key,size):
    return client(public=True).generate_presigned_url('put_object',Params={'Bucket':bucket(),'Key':key,'ContentType':'application/pdf','ContentLength':size},ExpiresIn=300)

def head(key): return client().head_object(Bucket=bucket(),Key=key)

def read(key,identity,max_bytes):
    response=client().get_object(Bucket=bucket(),Key=key,IfMatch=identity)
    try:
        raw=response['Body'].read(max_bytes+1)
    finally:
        response['Body'].close()
    if len(raw)>max_bytes: raise ValueError('FILE_TOO_LARGE')
    return raw

def write_private(key,raw):
    result=client().put_object(Bucket=bucket(),Key=key,Body=raw,ContentType='application/pdf')
    return result.get('VersionId') or result['ETag']

def presign_get(key):
    return client(public=True).generate_presigned_url('get_object',Params={'Bucket':bucket(),'Key':key,'ResponseContentDisposition':'attachment'},ExpiresIn=60)
