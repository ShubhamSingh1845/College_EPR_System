from collections.abc import Generator
import secrets
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.database import get_database
from app.config import settings
from app.main import app
from app.utils.security import create_access_token, hash_password


@pytest.fixture()
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "jwt_secret", secrets.token_urlsafe(48))
    monkeypatch.setattr(
        settings,
        "frontend_origin",
        "http://127.0.0.1:5173,http://localhost:5173",
    )
    mongo = MongoClient("mongodb://127.0.0.1:27017", serverSelectionTimeoutMS=2000)
    test_database = mongo[f"college_erp_test_{uuid4().hex}"]
    app.dependency_overrides[get_database] = lambda: test_database
    test_database.users.create_index("email", unique=True)
    test_database.students.create_index("registration_number", unique=True)
    test_database.students.create_index("email", unique=True)
    test_database.create_collection(
        "faculty",
        validator={
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["faculty_id", "full_name", "email"],
                "properties": {
                    "faculty_id": {"bsonType": "string", "minLength": 1},
                    "full_name": {"bsonType": "string", "minLength": 2},
                    "email": {"bsonType": "string", "minLength": 3},
                    "department_id": {"bsonType": ["objectId", "null"]},
                },
            }
        },
    )
    test_database.faculty.create_index("faculty_id", unique=True)
    test_database.faculty.create_index("email", unique=True)
    test_database.faculty.create_index("employee_id", unique=True)
    test_database.attendance.create_index(
        [("student_id", 1), ("subject_id", 1), ("class_session", 1)], unique=True
    )
    test_database.marks.create_index([("student_id", 1), ("assessment_id", 1)], unique=True)
    admin_id = "test-admin"
    test_database.users.insert_one(
        {
            "_id": admin_id,
            "email": "admin@example.com",
            "name": "Test Admin",
            "role": "admin",
            "password_hash": hash_password("TestPassword!234"),
            "active": True,
        }
    )
    token = create_access_token(admin_id, "admin")
    app.dependency_overrides[get_database] = lambda: test_database
    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client
    app.dependency_overrides.clear()
    mongo.drop_database(test_database.name)
    mongo.close()


def test_database_backed_student_creation_and_analytics(client: TestClient) -> None:
    response = client.post(
        "/api/students",
        json={
            "registration_number": "ERP-TEST-001",
            "full_name": "Test Student",
            "email": "student@example.com",
            "phone": "1234567890",
            "department": "CSE",
            "course": "B.Tech",
            "semester": 1,
            "academic_session": "2026-27",
        },
    )
    assert response.status_code == 201
    assert response.json()["registration_number"] == "ERP-TEST-001"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["students"] == 1


def test_login_and_duplicate_registration_are_rejected(client: TestClient) -> None:
    login = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "TestPassword!234"})
    assert login.status_code == 200

    db = app.dependency_overrides[get_database]()
    db.users.update_one({"email": "admin@example.com"}, {"$set": {"email": "admin@123"}})
    username_login = client.post("/api/auth/login", json={"email": "admin@123", "password": "TestPassword!234"})
    assert username_login.status_code == 200

    student = {
        "registration_number": "ERP-TEST-002",
        "full_name": "Test Student",
        "email": "student2@example.com",
        "phone": "1234567890",
        "department": "CSE",
        "course": "B.Tech",
        "semester": 1,
        "academic_session": "2026-27",
    }
    assert client.post("/api/students", json=student).status_code == 201
    student["email"] = "student3@example.com"
    assert client.post("/api/students", json=student).status_code == 409


def test_faculty_creation_satisfies_existing_mongodb_validator_and_indexes(client: TestClient) -> None:
    response = client.post(
        "/api/faculty",
        json={
            "employee_id": "EMP001",
            "full_name": "Rahul Sharma",
            "email": "rahul.sharma@example.edu",
            "phone": "9876543210",
            "department": "Computer Science",
            "designation": "Assistant Professor",
            "qualifications": ["MCA", "Ph.D."],
            "assigned_subjects": ["Python", "DBMS"],
            "assigned_classes": ["BCA 1st Year"],
            "employment_status": "on_leave",
        },
    )
    assert response.status_code == 201, response.text
    faculty = response.json()
    assert faculty["employee_id"] == "EMP001"
    assert faculty["faculty_id"] == "EMP001"

    updated = client.patch(f"/api/faculty/{faculty['_id']}", json={"employee_id": "EMP002"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["employee_id"] == updated.json()["faculty_id"] == "EMP002"


def create_student(client: TestClient, registration: str, email: str) -> dict:
    response = client.post(
        "/api/students",
        json={
            "registration_number": registration,
            "full_name": "Workflow Student",
            "email": email,
            "phone": "1234567890",
            "department": "CSE",
            "course": "B.Tech",
            "semester": 1,
            "academic_session": "2026-27",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_fee_invoice_accepts_student_registration_number(client: TestClient) -> None:
    student = create_student(client, "ERP-INVOICE-001", "invoice@example.com")
    response = client.post(
        "/api/fee_invoices",
        json={
            "student_id": student["registration_number"],
            "amount_due": 100,
            "due_date": "2026-11-01",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["student_id"] == student["_id"]


def test_attendance_marks_and_fee_analytics_use_saved_records(client: TestClient) -> None:
    student = create_student(client, "ERP-FLOW-001", "flow@example.com")
    db = app.dependency_overrides[get_database]()
    subject_id = "applied-math"
    db.subjects.insert_one({"_id": subject_id, "name": "Applied Mathematics", "code": "MATH-101"})

    for status in ("present", "absent", "late", "excused"):
        response = client.post(
            "/api/attendance",
            json={
                "student_id": student["registration_number"],
                "subject_id": "MATH-101" if status == "present" else subject_id,
                "class_session": f"session-{status}",
                "status": status,
            },
        )
        assert response.status_code == 201
        assert response.json()["student_id"] == student["_id"]
        assert response.json()["subject_id"] == subject_id
    duplicate = client.post(
        "/api/attendance",
        json={
            "student_id": student["registration_number"],
            "subject_id": subject_id,
            "class_session": "session-present",
            "status": "absent",
        },
    )
    assert duplicate.status_code == 409

    assessment_id = db.assessments.insert_one({"name": "Midterm", "max_marks": 100}).inserted_id
    mark = client.post(
        "/api/marks",
        json={
            "student_id": student["_id"],
            "assessment_id": str(assessment_id),
            "subject_id": str(subject_id),
            "semester": 1,
            "maximum_marks": 100,
            "marks_obtained": 80,
        },
    )
    assert mark.status_code == 201
    assert client.post(f"/api/results/{mark.json()['_id']}/approve").status_code == 200

    invoice = client.post(
        "/api/fee_invoices",
        json={"student_id": student["_id"], "amount_due": 100, "due_date": "2026-11-01"},
    )
    assert invoice.status_code == 201
    payment = client.post(
        "/api/payments",
        json={"invoice_id": invoice.json()["_id"], "amount": 40, "method": "bank"},
    )
    assert payment.status_code == 201
    assert payment.json()["receipt_number"].startswith("RCPT-")
    overpayment = client.post(
        "/api/payments",
        json={"invoice_id": invoice.json()["_id"], "amount": 61, "method": "bank"},
    )
    assert overpayment.status_code == 422

    book_id = db.library_books.insert_one(
        {"title": "ERP Testing", "isbn": "ERP-TEST-BOOK-001", "copies": "1", "copies_available": "1"}
    ).inserted_id
    issue = client.post(
        "/api/book_issues",
        json={
            "book_id": "ERP-TEST-BOOK-001",
            "student_id": student["registration_number"],
            "due_date": "2026-11-15",
        },
    )
    assert issue.status_code == 201
    assert issue.json()["book_id"] == str(book_id)
    assert issue.json()["student_id"] == student["_id"]
    assert db.library_books.find_one({"_id": book_id})["copies_available"] == 0
    assert client.post(
        "/api/book_issues",
        json={
            "book_id": "ERP-TEST-BOOK-001",
            "student_id": student["registration_number"],
            "due_date": "2026-11-15",
        },
    ).status_code == 409
    assert client.patch(f"/api/book_issues/{issue.json()['_id']}/return").status_code == 200
    assert db.library_books.find_one({"_id": book_id})["copies_available"] == 1

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["counts"]["attendance_records"] == 4
    assert dashboard["counts"]["published_results"] == 1
    assert dashboard["counts"]["fees_collected"] == 40
    assert dashboard["counts"]["fees_outstanding"] == 60
    assert dashboard["attendance_by_subject"][0]["percentage"] == 66.7
    assert dashboard["marks_distribution"][0]["value"] == 1
    report = client.get("/api/reports/summary")
    assert report.status_code == 200
    assert report.json()["counts"]["fees_collected"] == 40
    assert client.post(
        "/api/fee_structures",
        json={"name": "Tuition", "academic_session": "2026-27", "semester": 1, "department_id": "CSE", "amount": 100},
    ).status_code == 201


def test_student_account_is_limited_to_its_linked_private_records(client: TestClient) -> None:
    own_student = create_student(client, "ERP-OWN-001", "own@example.com")
    other_student = create_student(client, "ERP-OTHER-001", "other@example.com")
    db = app.dependency_overrides[get_database]()
    db.marks.insert_many(
        [
            {"student_id": own_student["_id"], "assessment_id": "assessment-1", "status": "published"},
            {"student_id": other_student["_id"], "assessment_id": "assessment-1", "status": "published"},
        ]
    )
    created_user = client.post(
        "/api/users",
        json={
            "email": "own.user@example.com",
            "name": "Own Student",
            "password": "UniquePassword!234",
            "role": "student",
            "profile_id": own_student["_id"],
        },
    )
    assert created_user.status_code == 201
    assert "password_hash" not in created_user.json()

    login = client.post(
        "/api/auth/login",
        json={"email": "own.user@example.com", "password": "UniquePassword!234"},
    )
    client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})

    student_list = client.get("/api/students")
    assert [item["_id"] for item in student_list.json()["items"]] == [own_student["_id"]]
    results = client.get("/api/results")
    assert {item["student_id"] for item in results.json()["items"]} == {own_student["_id"]}
    leave = client.post(
        "/api/leave_applications",
        json={"start_date": "2026-11-01", "end_date": "2026-11-02", "reason": "Medical appointment"},
    )
    assert leave.status_code == 201
    assert len(client.get("/api/leave_applications").json()["items"]) == 1
    assert client.get("/api/audit_logs").status_code == 403


def test_application_refuses_weak_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "jwt_secret", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        with TestClient(app):
            pass


@pytest.mark.parametrize("origin", ["http://127.0.0.1:5173", "http://localhost:5173"])
def test_login_preflight_allows_local_frontend_origins(client: TestClient, origin: str) -> None:
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
