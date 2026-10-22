from datetime import datetime, timezone
from typing import Annotated, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.database import get_database
from app.middleware.auth import get_current_user, require_roles
from app.schemas.common import (
    AttendanceEntry,
    BookIssueCreate,
    FeedbackCreate,
    FeeInvoiceCreate,
    LeaveApplicationCreate,
    LeaveReview,
    MarksCreate,
    PaymentCreate,
)
from app.routes.records import serialize

router = APIRouter(prefix="/api", tags=["academics"])
STAFF = require_roles("admin", "faculty")
ADMIN = require_roles("admin")


@router.post("/attendance", status_code=status.HTTP_201_CREATED)
def record_attendance(
    payload: AttendanceEntry,
    user: Annotated[dict, Depends(STAFF)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    student_query = (
        {"_id": ObjectId(payload.student_id), "enrollment_status": "active"}
        if ObjectId.is_valid(payload.student_id)
        else {"registration_number": payload.student_id, "enrollment_status": "active"}
    )
    student = db.students.find_one(student_query)
    if not student:
        raise HTTPException(status_code=404, detail="Active student not found")
    subject_query = {
        "$or": [
            {"_id": ObjectId(payload.subject_id)}
            if ObjectId.is_valid(payload.subject_id)
            else {"_id": payload.subject_id},
            {"code": payload.subject_id},
        ]
    }
    subject = db.subjects.find_one(subject_query)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    student_id = str(student["_id"])
    subject_id = str(subject["_id"])
    key = {"student_id": student_id, "subject_id": subject_id, "class_session": payload.class_session}
    record = {
        **payload.model_dump(),
        "student_id": student_id,
        "subject_id": subject_id,
        "recorded_by": user["id"],
        "updated_at": datetime.now(timezone.utc),
    }
    try:
        db.attendance.insert_one(record)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Attendance already recorded for this class session") from exc
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "attendance.recorded", "record_id": student_id, "created_at": datetime.now(timezone.utc)})
    return {**record, "_id": str(db.attendance.find_one(key)["_id"])}


@router.patch("/attendance/{attendance_id}")
def edit_attendance(
    attendance_id: str,
    payload: dict[str, Any],
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if not ObjectId.is_valid(attendance_id):
        raise HTTPException(status_code=400, detail="Invalid attendance ID")
    if payload.get("status") not in ("present", "absent", "late", "excused"):
        raise HTTPException(status_code=422, detail="Invalid attendance status")
    updated = db.attendance.find_one_and_update(
        {"_id": ObjectId(attendance_id)},
        {"$set": {"status": payload["status"], "updated_at": datetime.now(timezone.utc), "edited_by": user["id"]}},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "attendance.updated", "record_id": attendance_id, "created_at": datetime.now(timezone.utc)})
    return serialize(updated)


@router.post("/marks", status_code=status.HTTP_201_CREATED)
def submit_mark(
    payload: MarksCreate,
    user: Annotated[dict, Depends(STAFF)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    maximum = payload.maximum_marks
    score = payload.marks_obtained
    if score > maximum:
        raise HTTPException(status_code=422, detail="Marks must be between zero and the positive maximum")
    student_id = payload.student_id
    assessment_id = payload.assessment_id
    if not ObjectId.is_valid(student_id) or not ObjectId.is_valid(assessment_id):
        raise HTTPException(status_code=400, detail="Valid student and assessment IDs are required")
    if not db.students.find_one({"_id": ObjectId(student_id)}):
        raise HTTPException(status_code=404, detail="Student not found")
    assessment = db.assessments.find_one({"_id": ObjectId(assessment_id)})
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.get("max_marks") is not None and float(assessment["max_marks"]) != maximum:
        raise HTTPException(status_code=422, detail="Maximum marks must match the assessment configuration")
    if assessment.get("subject_id") and assessment["subject_id"] != payload.subject_id:
        raise HTTPException(status_code=422, detail="Subject does not match the assessment")
    record = {
        **payload.model_dump(),
        "percentage": round(score / maximum * 100, 2),
        "status": "submitted",
        "submitted_by": user["id"],
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = db.marks.insert_one(record)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="A mark already exists for this student and assessment") from exc
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "mark.submitted", "record_id": str(result.inserted_id), "created_at": datetime.now(timezone.utc)})
    return serialize(db.marks.find_one({"_id": result.inserted_id}))


@router.post("/results/{mark_id}/approve")
def approve_result(
    mark_id: str,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if not ObjectId.is_valid(mark_id):
        raise HTTPException(status_code=400, detail="Invalid mark ID")
    result = db.marks.find_one_and_update(
        {"_id": ObjectId(mark_id), "status": "submitted"},
        {"$set": {"status": "published", "approved_by": user["id"], "published_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Submitted mark not found")
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "result.published", "record_id": mark_id, "created_at": datetime.now(timezone.utc)})
    result["status"] = "published"
    return serialize(result)


@router.get("/results")
def list_results(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    query = {"status": "published"}
    if user["role"] == "student":
        if not user.get("student_id"):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["student_id"] = user.get("student_id")
    elif user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"items": [serialize(item) for item in db.marks.find(query).sort("created_at", -1)]}


@router.post("/payments", status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: PaymentCreate,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if not ObjectId.is_valid(payload.invoice_id):
        raise HTTPException(status_code=400, detail="Invalid invoice ID")
    invoice = db.fee_invoices.find_one({"_id": ObjectId(payload.invoice_id)})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    now = datetime.now(timezone.utc)
    payment_id = ObjectId()
    receipt = {
        "_id": payment_id,
        "invoice_id": payload.invoice_id,
        "amount": payload.amount,
        "method": payload.method,
        "reference": payload.reference,
        "receipt_number": f"RCPT-{payment_id}",
        "status": "confirmed",
        "confirmed_by": user["id"],
        "created_at": now,
    }
    balance_expression = {"$ifNull": ["$balance", "$amount_due"]}
    remaining_expression = {"$subtract": [balance_expression, payload.amount]}
    updated_invoice = db.fee_invoices.find_one_and_update(
        {
            "_id": invoice["_id"],
            "$expr": {"$gte": [balance_expression, payload.amount]},
        },
        [
            {
                "$set": {
                    "balance": remaining_expression,
                    "paid_amount": {"$add": [{"$ifNull": ["$paid_amount", 0]}, payload.amount]},
                    "status": {"$cond": [{"$lte": [remaining_expression, 0]}, "paid", "partial"]},
                    "updated_at": now,
                }
            }
        ],
        return_document=ReturnDocument.AFTER,
    )
    if not updated_invoice:
        raise HTTPException(status_code=422, detail="Payment exceeds the outstanding invoice balance")
    try:
        db.payments.insert_one(receipt)
    except PyMongoError:
        paid_after_rollback = {"$subtract": [{"$ifNull": ["$paid_amount", 0]}, payload.amount]}
        db.fee_invoices.update_one(
            {"_id": invoice["_id"]},
            [
                {
                    "$set": {
                        "balance": {"$add": [{"$ifNull": ["$balance", 0]}, payload.amount]},
                        "paid_amount": paid_after_rollback,
                        "status": {
                            "$cond": [
                                {"$lte": [paid_after_rollback, 0]},
                                "pending",
                                {
                                    "$cond": [
                                        {"$gte": [paid_after_rollback, "$amount_due"]},
                                        "paid",
                                        "partial",
                                    ]
                                },
                            ]
                        },
                    }
                }
            ],
        )
        raise
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "payment.confirmed", "record_id": str(payment_id), "created_at": now})
    return serialize(db.payments.find_one({"_id": payment_id}))


@router.get("/marks")
def list_marks(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"items": [serialize(item) for item in db.marks.find({}).sort("created_at", -1).limit(500)]}


@router.post("/fee_invoices", status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: FeeInvoiceCreate,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    amount = payload.amount_due
    student_query = (
        {"_id": ObjectId(payload.student_id)}
        if ObjectId.is_valid(payload.student_id)
        else {"registration_number": payload.student_id}
    )
    student = db.students.find_one(student_query)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_id = str(student["_id"])
    now = datetime.now(timezone.utc)
    invoice = {
        "student_id": student_id,
        "fee_structure_id": payload.fee_structure_id,
        "description": payload.description,
        "amount_due": amount,
        "paid_amount": 0,
        "balance": amount,
        "due_date": payload.due_date.isoformat(),
        "status": "pending",
        "created_by": user["id"],
        "created_at": now,
        "updated_at": now,
    }
    inserted = db.fee_invoices.insert_one(invoice)
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "fee_invoice.created", "record_id": str(inserted.inserted_id), "created_at": now})
    return serialize(db.fee_invoices.find_one({"_id": inserted.inserted_id}))


@router.post("/leave_applications", status_code=status.HTTP_201_CREATED)
def apply_for_leave(
    payload: LeaveApplicationCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if user["role"] not in ("student", "faculty"):
        raise HTTPException(status_code=403, detail="Only students and faculty can apply for leave")
    applicant_id = user.get("student_id") or user.get("faculty_id") or user["id"]
    if user["role"] == "student" and not user.get("student_id"):
        raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
    record = {
        "applicant_id": applicant_id,
        "applicant_role": user["role"],
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "reason": payload.reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    inserted = db.leave_applications.insert_one(record)
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "leave.applied", "record_id": str(inserted.inserted_id), "created_at": datetime.now(timezone.utc)})
    return serialize(db.leave_applications.find_one({"_id": inserted.inserted_id}))


@router.patch("/leave_applications/{application_id}")
def review_leave(
    application_id: str,
    payload: LeaveReview,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if not ObjectId.is_valid(application_id):
        raise HTTPException(status_code=400, detail="Invalid application ID")
    application = db.leave_applications.find_one_and_update(
        {"_id": ObjectId(application_id), "status": "pending"},
        {"$set": {"status": payload.status, "reviewed_by": user["id"], "reviewed_at": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not application:
        raise HTTPException(status_code=404, detail="Pending leave application not found")
    db.audit_logs.insert_one({"actor_id": user["id"], "action": f"leave.{payload.status}", "record_id": application_id, "created_at": datetime.now(timezone.utc)})
    return serialize(application)


@router.get("/attendance")
def list_attendance(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    query = {}
    if user["role"] == "student":
        if not user.get("student_id"):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["student_id"] = user["student_id"]
    elif user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"items": [serialize(item) for item in db.attendance.find(query).sort("recorded_at", -1).limit(500)]}


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    now = datetime.now(timezone.utc)
    record = {"user_id": user["id"], "role": user["role"], "subject": payload.subject, "message": payload.message, "status": "new", "created_at": now}
    inserted = db.feedback.insert_one(record)
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "feedback.submitted", "record_id": str(inserted.inserted_id), "created_at": now})
    return serialize(db.feedback.find_one({"_id": inserted.inserted_id}))


@router.post("/book_issues", status_code=status.HTTP_201_CREATED)
def issue_library_book(
    payload: BookIssueCreate,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if user["role"] not in ("admin", "faculty", "student"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    book_id = payload.book_id
    student_id = user.get("student_id") if user["role"] == "student" else payload.student_id
    if user["role"] == "student" and not student_id:
        raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
    student_query = (
        {"_id": ObjectId(student_id)}
        if ObjectId.is_valid(student_id or "")
        else {"registration_number": student_id}
    )
    student = db.students.find_one(student_query)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student_id = str(student["_id"])
    book_query = (
        {"_id": ObjectId(book_id)}
        if ObjectId.is_valid(book_id)
        else {"$or": [{"isbn": book_id}, {"book_id": book_id}, {"code": book_id}]}
    )
    book_record = db.library_books.find_one(book_query)
    if not book_record:
        raise HTTPException(status_code=404, detail="Book not found; choose a listed book or enter its ISBN")
    book_id = str(book_record["_id"])
    now = datetime.now(timezone.utc)
    if db.book_issues.find_one({"book_id": book_id, "student_id": student_id, "returned_at": None}):
        raise HTTPException(status_code=409, detail="This student already has an active issue for that book")
    available_copies = {
        "$convert": {
            "input": {"$ifNull": ["$copies_available", "$copies"]},
            "to": "int",
            "onError": 0,
            "onNull": 0,
        }
    }
    book = db.library_books.find_one_and_update(
        {"_id": ObjectId(book_id), "$expr": {"$gt": [available_copies, 0]}},
        [{"$set": {"copies_available": {"$subtract": [available_copies, 1]}}}],
        return_document=ReturnDocument.AFTER,
    )
    if not book:
        raise HTTPException(status_code=409, detail="Book is unavailable or has no copies available")
    issue = {
        "book_id": book_id,
        "student_id": student_id,
        "issued_at": now,
        "due_date": payload.due_date.isoformat() if payload.due_date else None,
        "returned_at": None,
        "status": "issued",
    }
    try:
        inserted = db.book_issues.insert_one(issue)
    except DuplicateKeyError as exc:
        db.library_books.update_one(
            {"_id": ObjectId(book_id)},
            [{"$set": {"copies_available": {"$add": [available_copies, 1]}}}],
        )
        raise HTTPException(status_code=409, detail="This student already has an active issue for that book") from exc
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "book.issued", "record_id": str(inserted.inserted_id), "created_at": now})
    return serialize(db.book_issues.find_one({"_id": inserted.inserted_id}))


@router.patch("/book_issues/{issue_id}/return")
def return_library_book(
    issue_id: str,
    user: Annotated[dict, Depends(STAFF)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if not ObjectId.is_valid(issue_id):
        raise HTTPException(status_code=400, detail="Invalid book issue ID")
    now = datetime.now(timezone.utc)
    issue = db.book_issues.find_one_and_update(
        {"_id": ObjectId(issue_id), "returned_at": None},
        {"$set": {"returned_at": now, "status": "returned"}},
        return_document=True,
    )
    if not issue:
        raise HTTPException(status_code=404, detail="Active book issue not found")
    available_copies = {
        "$convert": {
            "input": {"$ifNull": ["$copies_available", "$copies"]},
            "to": "int",
            "onError": 0,
            "onNull": 0,
        }
    }
    db.library_books.update_one(
        {"_id": ObjectId(issue["book_id"])},
        [{"$set": {"copies_available": {"$add": [available_copies, 1]}}}],
    )
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "book.returned", "record_id": issue_id, "created_at": now})
    return serialize(issue)


@router.get("/dashboard")
def dashboard(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    query = {}
    if user["role"] == "student":
        if not user.get("student_id"):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["student_id"] = user.get("student_id")
    elif user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    attendance = list(db.attendance.find(query, {"status": 1, "subject_id": 1}))
    counts = {label: sum(1 for item in attendance if item.get("status") == label) for label in ("present", "absent", "late", "excused")}
    subject_ids = {item.get("subject_id") for item in attendance if item.get("subject_id")}
    attendance_by_subject = []
    for subject_id in subject_ids:
        subject = db.subjects.find_one({"_id": ObjectId(subject_id)}) if ObjectId.is_valid(subject_id) else None
        rows = [item for item in attendance if item.get("subject_id") == subject_id]
        attended = sum(1 for item in rows if item.get("status") in ("present", "late"))
        eligible = sum(1 for item in rows if item.get("status") in ("present", "absent", "late"))
        attendance_by_subject.append({"subject": subject.get("name", subject_id) if subject else subject_id, "percentage": round(attended / eligible * 100, 1) if eligible else 0})

    marks_query = {"status": "published"}
    if user["role"] == "student":
        marks_query["student_id"] = user.get("student_id")
    published_marks = list(db.marks.find(marks_query, {"percentage": 1, "subject_id": 1}))
    grade_bands: dict[str, set[str]] = {"A (80-100%)": set(), "B (70-79%)": set(), "C (60-69%)": set(), "D (<60%)": set()}
    marks_by_subject: dict[str, list[float]] = {}
    for mark in published_marks:
        percentage = float(mark.get("percentage", 0))
        grade_bands["A (80-100%)" if percentage >= 80 else "B (70-79%)" if percentage >= 70 else "C (60-69%)" if percentage >= 60 else "D (<60%)"].add(str(mark.get("student_id", mark.get("_id"))))
        marks_by_subject.setdefault(str(mark.get("subject_id", "Unassigned")), []).append(percentage)

    payments = list(db.payments.find({"status": "confirmed"}, {"amount": 1}))
    confirmed_total = sum(float(payment.get("amount", 0)) for payment in payments)
    invoices = list(db.fee_invoices.find({}, {"balance": 1, "amount_due": 1, "student_id": 1}))
    if user["role"] == "student":
        if not user.get("student_id"):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        invoices = [invoice for invoice in invoices if invoice.get("student_id") == user.get("student_id")]
    outstanding_total = sum(float(invoice.get("balance", invoice.get("amount_due", 0))) for invoice in invoices)
    if user["role"] == "student":
        student_invoice_ids = {
            str(invoice["_id"])
            for invoice in db.fee_invoices.find({"student_id": user.get("student_id")}, {"_id": 1})
        }
        confirmed_total = sum(
            float(payment.get("amount", 0))
            for payment in db.payments.find({"status": "confirmed", "invoice_id": {"$in": list(student_invoice_ids)}})
        )
    elif user["role"] == "faculty":
        confirmed_total = 0
        outstanding_total = 0
    recent_query = {"actor_id": user["id"]} if user["role"] == "student" else {}
    recent = db.audit_logs.find(recent_query).sort("created_at", -1).limit(8)
    semester_averages: dict[str, list[float]] = {}
    for mark in published_marks:
        semester_averages.setdefault(str(mark.get("semester", "Unspecified")), []).append(float(mark.get("percentage", 0)))
    return {
        "counts": {
            "students": db.students.count_documents({"_id": ObjectId(user["student_id"])}) if user["role"] == "student" and ObjectId.is_valid(user.get("student_id", "")) else db.students.count_documents({"enrollment_status": {"$ne": "inactive"}}) if user["role"] != "student" else 0,
            "faculty": 1 if user["role"] == "faculty" else db.faculty.count_documents({"employment_status": {"$ne": "inactive"}}) if user["role"] == "admin" else 0,
            "attendance_records": len(attendance),
            "published_results": len(published_marks),
            "fees_collected": round(confirmed_total, 2),
            "fees_outstanding": round(outstanding_total, 2),
        },
        "attendance": [{"name": label.title(), "value": count} for label, count in counts.items()],
        "attendance_by_subject": attendance_by_subject,
        "marks_distribution": [{"name": label, "value": len(student_ids)} for label, student_ids in grade_bands.items()],
        "marks_by_subject": [{"subject": subject, "average": round(sum(values) / len(values), 1)} for subject, values in marks_by_subject.items()],
        "performance_by_semester": [{"semester": semester, "average": round(sum(values) / len(values), 1)} for semester, values in sorted(semester_averages.items())],
        "fee_collection": [{"name": "Confirmed", "amount": round(confirmed_total, 2)}, {"name": "Outstanding", "amount": round(outstanding_total, 2)}],
        "recent_activities": [serialize(item) for item in recent],
    }


@router.get("/health/database")
def database_health(db: Annotated[Database, Depends(get_database)]) -> dict:
    db.command("ping")
    return {"status": "connected", "database": db.name}


@router.get("/reports/summary")
def reports_summary(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return dashboard(user, db)
