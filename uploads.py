
import boto3
from botocore.config import Config
from fastapi import HTTPException
from app.core.config import settings

def get_s3():
    if not all([
        settings.s3_endpoint_url,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
        settings.s3_bucket,
    ]):
        raise HTTPException(503, "Object storage is not configured")
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )
