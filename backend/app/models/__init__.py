"""Importing this package registers every model with SQLAlchemy's mapper
registry. This matters beyond convenience: models that are only referenced
by string in a ForeignKey() (not imported as a Python class anywhere in the
app's actual route -> service -> model import chain) never get registered
in a real running process, which surfaces as `NoReferencedTableError` the
first time a flush/commit needs to sort tables by FK dependency — not on
reads, only on writes, which is why this can hide for a while. `app.main`
imports this package explicitly so the real app (not just tests/scripts
that happen to import every model directly) never hits it.
"""

from app.models.academic_year import AcademicYear  # noqa: F401
from app.models.attendance_session import AttendanceSession  # noqa: F401
from app.models.branch import Branch  # noqa: F401
from app.models.class_enrollment import ClassEnrollment  # noqa: F401
from app.models.class_offering import ClassOffering  # noqa: F401
from app.models.division import Division  # noqa: F401
from app.models.face_profile import FaceProfile  # noqa: F401
from app.models.faculty import Faculty  # noqa: F401
from app.models.institution import Institution  # noqa: F401
from app.models.session import UserSession  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.subject import Subject  # noqa: F401
from app.models.user import User  # noqa: F401
