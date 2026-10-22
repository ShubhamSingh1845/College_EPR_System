# API overview

Base URL: `http://127.0.0.1:8001/api`. Except login and health checks, endpoints require `Authorization: Bearer <access_token>`. Sign in through `POST /auth/login`; inspect the current identity with `GET /auth/me`.

| Method | Endpoint | Access |
|---|---|---|
| GET | `/dashboard` | All signed-in roles; student-scoped academic/fee data |
| GET, POST, PATCH | `/students` | Admin writes; staff reads; student reads only linked profile |
| GET, POST, PATCH | `/faculty` | Admin writes; staff reads |
| GET, POST, PATCH | `/departments`, `/courses`, `/subjects`, `/enrollments`, `/assessments`, `/library_books`, `/timetables`, `/notifications`, `/feedback` | Role-aware generic record administration |
| GET, POST, PATCH | `/attendance` | Staff record/authorized admin edit; reads are scoped for students |
| POST | `/marks` | Faculty/admin submits a validated mark |
| GET | `/results` | Admin/faculty all published; students their own published marks |
| POST | `/results/{mark_id}/approve` | Admin publishes a submitted mark |
| GET, POST | `/fee_invoices` | Admin creates invoices; students see their own |
| POST | `/payments` | Admin records confirmed authorized offline/test payments |
| GET, POST, PATCH | `/leave_applications` | Students/faculty apply; admin reads and approves/rejects |
| GET, POST | `/users` | Admin creates/list accounts; student/faculty accounts must link a profile |
| POST | `/feedback` | Any signed-in user submits feedback; students can view only their own submissions |
| GET | `/marks` | Admin/faculty review submitted marks |
| POST | `/book_issues` | Signed-in student requests an available book; staff can issue it to a student |
| PATCH | `/book_issues/{issue_id}/return` | Admin/faculty records a book return |
| GET | `/health/database` | Database connectivity check |
| GET | `/reports/summary` | Admin/faculty database-backed analytics report |

Interactive OpenAPI documentation is available at `/docs`. Most list endpoints accept `page` and `page_size`; student/faculty lists also accept `search`.

When creating a fee invoice, `student_id` may be the student's MongoDB profile ID or registration number. The invoice is stored with the canonical MongoDB profile ID.

When creating a book issue, `book_id` may be a MongoDB profile ID or ISBN. Staff-provided `student_id` may be a MongoDB profile ID or registration number. The API stores canonical MongoDB profile IDs and updates available copy counts atomically.

When recording attendance, `student_id` may be a MongoDB profile ID or student registration number, and `subject_id` may be a MongoDB profile ID or subject code. The API stores canonical MongoDB profile IDs.
