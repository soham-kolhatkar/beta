import uuid

from pydantic import BaseModel


class UserBrief(BaseModel):
    id: uuid.UUID
    name: str
    email: str

    model_config = {"from_attributes": True}
