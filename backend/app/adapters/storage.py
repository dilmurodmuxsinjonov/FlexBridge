import os
from dataclasses import dataclass
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


class StorageReferenceError(Exception):
    def __init__(self, code='FILE_STORAGE_REFERENCE_REQUIRED', status_code=409):
        super().__init__(code)
        self.code, self.status_code = code, status_code


def _present(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


@dataclass(frozen=True)
class ObjectReference:
    bucket: str
    version_id: str
    etag: str

    def __post_init__(self):
        if (not all(_present(v) for v in (self.bucket, self.version_id, self.etag))
                or self.version_id.lower() == 'null'):
            raise StorageReferenceError()

    def values(self):
        return {'storage_bucket': self.bucket, 'storage_version_id': self.version_id,
                'storage_etag': self.etag}

    def check_bucket(self):
        if self.bucket != os.environ.get('S3_BUCKET'):
            raise StorageReferenceError('FILE_STORAGE_BUCKET_MISMATCH', 503)


def response_reference(response):
    try:
        return ObjectReference(bucket(), response.get('VersionId'), response.get('ETag'))
    except StorageReferenceError:
        raise StorageReferenceError('FILE_STORAGE_VERSIONING_REQUIRED', 503) from None


def file_reference(record):
    # Never infer provenance from legacy object_version (which also stored ETags).
    reference = ObjectReference(record.get('storage_bucket'), record.get('storage_version_id'), record.get('storage_etag'))
    reference.check_bucket()
    return reference


SNAPSHOT_FIELDS = ('sha256', 'object_version', 'storage_key', 'byte_size',
                   'storage_bucket', 'storage_version_id', 'storage_etag')


def file_snapshot(record):
    file_reference(record)
    return {key: record[key] for key in SNAPSHOT_FIELDS}

def presign_put(key,size):
    return client(public=True).generate_presigned_url('put_object',Params={'Bucket':bucket(),'Key':key,'ContentType':'application/pdf','ContentLength':size},ExpiresIn=300)

def head(key): return client().head_object(Bucket=bucket(),Key=key)

def read(key,reference,max_bytes):
    reference.check_bucket()
    response=client().get_object(Bucket=reference.bucket,Key=key,VersionId=reference.version_id,IfMatch=reference.etag)
    try:
        if response.get('VersionId')!=reference.version_id or response.get('ETag')!=reference.etag:
            raise StorageReferenceError('FILE_STORAGE_READ_MISMATCH',503)
        raw=response['Body'].read(max_bytes+1)
    finally:
        response['Body'].close()
    if len(raw)>max_bytes: raise ValueError('FILE_TOO_LARGE')
    return raw

def write_private(key,raw):
    result=client().put_object(Bucket=bucket(),Key=key,Body=raw,ContentType='application/pdf')
    return response_reference(result)

def presign_get(key,*,reference):
    reference.check_bucket()
    return client(public=True).generate_presigned_url('get_object',Params={'Bucket':reference.bucket,'Key':key,
        'VersionId':reference.version_id,'ResponseContentDisposition':'attachment'},ExpiresIn=60)
