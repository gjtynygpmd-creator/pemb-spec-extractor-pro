from pydantic import BaseModel, Field


class FieldUpdate(BaseModel):
    value: str | None = None
    status: str | None = Field(default=None, pattern="^(review|accepted|conflict|missing|not_applicable)$")


class FieldCreate(BaseModel):
    category: str
    field_name: str
    value: str | None = None
    status: str = Field(default="review", pattern="^(review|accepted|conflict|missing|not_applicable)$")
