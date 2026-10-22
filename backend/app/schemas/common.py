from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class UserCreate(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["admin", "faculty", "student"]
    profile_id: str | None = None


class StudentCreate(BaseModel):
    registration_number: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    department: str
    course: str
    semester: int = Field(ge=1, le=16)
    academic_session: str
    address: str = ""
    enrollment_status: Literal["active", "on_leave", "inactive"] = "active"


class FacultyCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=40)
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=30)
    department: str
    designation: str
    qualifications: list[str] = Field(default_factory=list)
    assigned_subjects: list[str] = Field(default_factory=list)
    assigned_classes: list[str] = Field(default_factory=list)
    employment_status: Literal["active", "on_leave", "inactive"] = "active"


class AttendanceEntry(BaseModel):
    student_id: str
    subject_id: str
    class_session: str
    status: str = Field(pattern="^(present|absent|late|excused)$")
    recorded_at: datetime = Field(default_factory=utc_now)


class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float = Field(gt=0)
    method: str = Field(min_length=2, max_length=30)
    reference: str = ""


class MarksCreate(BaseModel):
    student_id: str
    assessment_id: str
    subject_id: str
    semester: int = Field(ge=1, le=16)
    maximum_marks: float = Field(gt=0, le=100000)
    marks_obtained: float = Field(ge=0, le=100000)


class FeeInvoiceCreate(BaseModel):
    student_id: str
    description: str = Field(default="College fees", max_length=200)
    amount_due: float = Field(gt=0, le=100000000)
    due_date: date
    fee_structure_id: str | None = None


class LeaveApplicationCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=1000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveApplicationCreate":
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be earlier than start date")
        return self


class LeaveReview(BaseModel):
    status: Literal["approved", "rejected"]


class FeedbackCreate(BaseModel):
    subject: str = Field(min_length=2, max_length=150)
    message: str = Field(min_length=3, max_length=3000)


class BookIssueCreate(BaseModel):
    book_id: str
    student_id: str | None = None
    due_date: date | None = None


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    data: dict[str, Any]
