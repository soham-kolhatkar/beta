import uuid

from pydantic import BaseModel

from app.schemas.common import UserBrief


class BranchBrief(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class DivisionBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class AcademicYearBrief(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class StudentMeResponse(BaseModel):
    id: uuid.UUID
    user: UserBrief
    prn: str
    roll_number: str
    branch: BranchBrief
    division: DivisionBrief
    academic_year: AcademicYearBrief
    face_registered: bool

    model_config = {"from_attributes": True}


class FacultyMeResponse(BaseModel):
    id: uuid.UUID
    user: UserBrief
    employee_id: str
    department: str

    model_config = {"from_attributes": True}
