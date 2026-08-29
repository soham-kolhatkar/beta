from datetime import datetime

from pydantic import BaseModel


class FaceModelInfo(BaseModel):
    name: str
    version: str


class FaceRegisterResponse(BaseModel):
    face_registered: bool
    model: FaceModelInfo


class FaceStatusResponse(BaseModel):
    registered: bool
    model: FaceModelInfo | None = None
    updated_at: datetime | None = None
