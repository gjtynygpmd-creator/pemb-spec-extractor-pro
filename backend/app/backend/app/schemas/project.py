
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    name: str
    customer: str | None = None
    address: str | None = None
    bid_due: datetime | None = None

class ProjectOut(ProjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    created_at: datetime
    updated_at: datetime
    file_count: int = 0
    field_count: int = 0
    conflict_count: int = 0
