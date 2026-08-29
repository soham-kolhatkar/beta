import uuid

from pydantic import BaseModel

from app.models.class_offering import ClassOffering
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


class SubjectBrief(BaseModel):
    id: uuid.UUID
    name: str
    code: str

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


class FacultyClassItem(BaseModel):
    """Shape for one item of GET /faculty/me/classes (docs/API.md §20)."""

    id: uuid.UUID
    name: str
    subject: SubjectBrief
    student_count: int

    @classmethod
    def from_class_offering(
        cls, class_offering: ClassOffering, student_count: int
    ) -> "FacultyClassItem":
        return cls(
            id=class_offering.id,
            name=class_offering.name,
            subject=SubjectBrief.model_validate(class_offering.subject),
            student_count=student_count,
        )


class FacultyClassListResponse(BaseModel):
    items: list[FacultyClassItem]
