
from pydantic import BaseModel

class UploadInit(BaseModel):
    project_id: str
    filename: str
    content_type: str = "application/octet-stream"
    size: int
    part_size: int = 16 * 1024 * 1024

class UploadPartUrl(BaseModel):
    upload_id: str
    object_key: str
    part_number: int

class UploadComplete(BaseModel):
    upload_id: str
    object_key: str
    project_id: str
    filename: str
    content_type: str = "application/octet-stream"
    size: int
    parts: list[dict]

class JobCreate(BaseModel):
    project_id: str
