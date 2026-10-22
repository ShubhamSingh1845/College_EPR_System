from datetime import datetime, timezone
from typing import Annotated, Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.middleware.auth import get_current_user, require_roles
from app.schemas.common import FacultyCreate, StudentCreate

router = APIRouter(prefix="/api", tags=["records"])
ADMIN = require_roles("admin")
STAFF = require_roles("admin", "faculty")
COLLECTION_ROLES = {
    "departments": ("admin", "faculty"),
    "courses": ("admin", "faculty"),
    "subjects": ("admin", "faculty"),
    "enrollments": ("admin", "faculty"),
    "assessments": ("admin", "faculty"),
    "library_books": ("admin", "faculty", "student"),
    "timetables": ("admin", "faculty", "student"),
    "notifications": ("admin", "faculty", "student"),
    "feedback": ("admin", "faculty", "student"),
    "fee_structures": ("admin", "faculty", "student"),
    "leave_applications": ("admin", "faculty", "student"),
    "fee_invoices": ("admin", "student"),
    "payments": ("admin", "student"),
    "book_issues": ("admin", "faculty", "student"),
    "audit_logs": ("admin",),
}
PROTECTED_FIELDS = {"_id", "password", "password_hash", "role", "created_at", "updated_at"}
SYSTEM_MANAGED_FIELDS = PROTECTED_FIELDS | {"faculty_id"}


def serialize(record: dict[str, Any]) -> dict[str, Any]:
    return {**record, "_id": str(record["_id"])}


@router.get("/students")
def list_students(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    query: dict[str, Any] = {"enrollment_status": {"$ne": "inactive"}}
    if user["role"] == "student":
        if not ObjectId.is_valid(user.get("student_id", "")):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["_id"] = ObjectId(user["student_id"])
    elif user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"registration_number": {"$regex": search, "$options": "i"}},
        ]
    total = db.students.count_documents(query)
    rows = db.students.find(query).sort("full_name", ASCENDING).skip((page - 1) * page_size).limit(page_size)
    return {"items": [serialize(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/students", status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    now = datetime.now(timezone.utc)
    record = payload.model_dump()
    record.update({"created_at": now, "updated_at": now})
    try:
        result = db.students.insert_one(record)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Registration number or email already exists") from exc
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "student.created", "record_id": str(result.inserted_id), "created_at": now})
    return serialize(db.students.find_one({"_id": result.inserted_id}))


@router.patch("/students/{student_id}")
def update_student(
    student_id: str,
    payload: dict[str, Any],
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    return update_record(db, "students", student_id, payload, user["id"])


@router.get("/faculty")
def list_faculty(
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    search: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    if user["role"] not in ("admin", "faculty"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    query: dict[str, Any] = {"employment_status": {"$ne": "inactive"}}
    if search:
        query["full_name"] = {"$regex": search, "$options": "i"}
    total = db.faculty.count_documents(query)
    rows = db.faculty.find(query).sort("full_name", ASCENDING).skip((page - 1) * page_size).limit(page_size)
    return {"items": [serialize(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/faculty", status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate,
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    now = datetime.now(timezone.utc)
    record = payload.model_dump()
    record["faculty_id"] = record["employee_id"]
    record.update({"created_at": now, "updated_at": now})
    try:
        result = db.faculty.insert_one(record)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="Employee ID or email already exists") from exc
    db.audit_logs.insert_one({"actor_id": user["id"], "action": "faculty.created", "record_id": str(result.inserted_id), "created_at": now})
    return serialize(db.faculty.find_one({"_id": result.inserted_id}))


def update_record(db: Database, collection: str, record_id: str, payload: dict[str, Any], actor_id: str) -> dict:
    if collection == "payments":
        raise HTTPException(status_code=405, detail="Payment records are immutable")
    if collection == "fee_invoices" and {"balance", "paid_amount", "status", "amount_due", "student_id"} & payload.keys():
        raise HTTPException(status_code=400, detail="Invoice balances, ownership, amount and payment status are managed by fee workflows")
    if not ObjectId.is_valid(record_id):
        raise HTTPException(status_code=400, detail="Invalid record ID")
    changes = {key: value for key, value in payload.items() if key not in SYSTEM_MANAGED_FIELDS}
    if not changes:
        raise HTTPException(status_code=400, detail="No editable fields supplied")
    if collection == "faculty" and "employee_id" in changes:
        changes["faculty_id"] = changes["employee_id"]
    changes["updated_at"] = datetime.now(timezone.utc)
    record = db[collection].find_one_and_update(
        {"_id": ObjectId(record_id)}, {"$set": changes}, return_document=ReturnDocument.AFTER
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.audit_logs.insert_one(
        {
            "actor_id": actor_id,
            "action": f"{collection}.updated",
            "record_id": record_id,
            "created_at": datetime.now(timezone.utc),
        }
    )
    return serialize(record)


@router.patch("/faculty/{faculty_id}")
def update_faculty(
    faculty_id: str,
    payload: dict[str, Any],
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    return update_record(db, "faculty", faculty_id, payload, user["id"])


@router.get("/{collection}")
def list_collection(
    collection: str,
    user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[Database, Depends(get_database)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    if collection not in COLLECTION_ROLES:
        raise HTTPException(status_code=404, detail="Collection not found")
    if user["role"] not in COLLECTION_ROLES[collection]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    query = {}
    if collection == "notifications" and user["role"] != "admin":
        query = {"$or": [{"audience": "all"}, {"audience": user["role"]}]}
    if collection == "feedback" and user["role"] == "student":
        query["user_id"] = user["id"]
    if collection == "book_issues" and user["role"] == "student":
        if not user.get("student_id"):
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["student_id"] = user["student_id"]
    if collection == "leave_applications" and user["role"] == "student":
        student_id = user.get("student_id")
        if not student_id:
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        query["applicant_id"] = student_id
    elif collection in ("fee_invoices", "payments") and user["role"] == "student":
        student_id = user.get("student_id")
        if not student_id:
            raise HTTPException(status_code=403, detail="Student profile is not linked to this account")
        if collection == "fee_invoices":
            query["student_id"] = student_id
        else:
            invoice_ids = [
                str(invoice["_id"])
                for invoice in db.fee_invoices.find({"student_id": student_id}, {"_id": 1})
            ]
            query["invoice_id"] = {"$in": invoice_ids}
    total = db[collection].count_documents(query)
    rows = db[collection].find(query).sort("_id", DESCENDING).skip((page - 1) * page_size).limit(page_size)
    return {"items": [serialize(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.post("/{collection}", status_code=status.HTTP_201_CREATED)
def create_collection_record(
    collection: str,
    payload: dict[str, Any],
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if collection not in COLLECTION_ROLES or collection in ("leave_applications", "fee_invoices", "payments", "audit_logs", "book_issues"):
        raise HTTPException(status_code=404, detail="Collection not found")
    now = datetime.now(timezone.utc)
    record = {key: value for key, value in payload.items() if key not in PROTECTED_FIELDS}
    if collection == "library_books":
        try:
            copies = int(record.get("copies", record.get("copies_available", 0)))
            copies_available = int(record.get("copies_available", copies))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Book copies must be a whole number") from exc
        if copies < 0 or copies_available < 0:
            raise HTTPException(status_code=422, detail="Book copies cannot be negative")
        record["copies"] = copies
        record["copies_available"] = copies_available
    record.update({"created_at": now, "updated_at": now})
    result = db[collection].insert_one(record)
    db.audit_logs.insert_one(
        {
            "actor_id": user["id"],
            "action": f"{collection}.created",
            "record_id": str(result.inserted_id),
            "created_at": now,
        }
    )
    return serialize(db[collection].find_one({"_id": result.inserted_id}))


@router.patch("/{collection}/{record_id}")
def patch_collection_record(
    collection: str,
    record_id: str,
    payload: dict[str, Any],
    user: Annotated[dict, Depends(ADMIN)],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if collection not in COLLECTION_ROLES or collection in ("payments", "audit_logs", "book_issues"):
        raise HTTPException(status_code=404, detail="Collection not found")
    return update_record(db, collection, record_id, payload, user["id"])
