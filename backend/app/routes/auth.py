from typing import Annotated
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.database import get_database
from app.middleware.auth import get_current_user, require_roles
from app.schemas.common import LoginRequest, UserCreate
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["authentication"])
user_router = APIRouter(prefix="/api/users", tags=["user management"])


@router.post("/login")
def login(payload: LoginRequest, db: Annotated[Database, Depends(get_database)]) -> dict:
    user = db.users.find_one({"email": payload.email.strip().lower(), "active": True})
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token(str(user["_id"]), user["role"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": str(user["_id"]), "email": user["email"], "name": user.get("name", ""), "role": user["role"]},
    }


@router.get("/me")
def me(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    return user


@user_router.get("")
def list_users(
    _: Annotated[dict, Depends(require_roles("admin"))],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    users = db.users.find({}, {"password_hash": 0}).sort("email", 1)
    return {"items": [{**user, "_id": str(user["_id"])} for user in users]}


@user_router.post("", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    actor: Annotated[dict, Depends(require_roles("admin"))],
    db: Annotated[Database, Depends(get_database)],
) -> dict:
    if payload.role in ("student", "faculty"):
        profile_collection = db.students if payload.role == "student" else db.faculty
        if not payload.profile_id or not ObjectId.is_valid(payload.profile_id):
            raise HTTPException(status_code=422, detail=f"A valid {payload.role} profile ID is required")
        profile = profile_collection.find_one({"_id": ObjectId(payload.profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail=f"{payload.role.title()} profile not found")
        profile_reference = {"student_id" if payload.role == "student" else "faculty_id": payload.profile_id}
    else:
        profile_reference = {}

    user_record = {
        "_id": str(ObjectId()),
        "email": payload.email.lower(),
        "name": payload.name,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "active": True,
        **profile_reference,
    }
    try:
        db.users.insert_one(user_record)
    except DuplicateKeyError as exc:
        raise HTTPException(status_code=409, detail="An account already uses this email") from exc
    db.audit_logs.insert_one(
        {
            "actor_id": actor["id"],
            "action": "user.created",
            "record_id": user_record["_id"],
            "created_at": datetime.now(timezone.utc),
        }
    )
    return {key: value for key, value in user_record.items() if key != "password_hash"}
