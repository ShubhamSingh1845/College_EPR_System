# Database design

Database: `college_erp`. Collection creation and indexes are in `database/setup.js`; non-destructive sample reference data is in `database/seed_data.js`.

| Collection | Purpose and principal references |
|---|---|
| users | Email, password hash, role, optional student/faculty profile reference |
| students, faculty | Separate student registrations and employee profiles; faculty forms expose `employee_id`, stored in both `employee_id` and the legacy-compatible `faculty_id` field |
| departments | Academic department records |
| courses, subjects | Course catalog and subject/course references |
| enrollments | Student, course and academic-session registration |
| attendance | Student, subject, class session and present/absent/late/excused status |
| assessments, marks, results | Assessment configuration, submitted scores and published result records |
| fee_structures, fee_invoices, payments | Student invoices, balances and confirmed/pending/failed payment records |
| leave_applications | Applicant, dates, reason and approval status |
| library_books, book_issues | Book catalog and student circulation |
| timetables | Course/class schedule records |
| notifications, feedback | User-facing announcements and submissions |
| audit_logs | Actor, action, affected record and timestamp |

Unique indexes protect account email, student registration number/email, faculty employee ID/email, enrollments per student/course/session, attendance per student/subject/session and marks per student/assessment. The setup script reuses existing indexes with compatible keys; if a same-key non-unique index exists, a partial unique index is added for populated string identifiers. Validators enforce required fields and status values for important collections. Existing collections and data are preserved; setup does not drop records, and existing validators are retained.

Object references are stored as stable string IDs in workflow records; primary MongoDB document identifiers are `ObjectId` for people and academic records. User account IDs are strings so bootstrap accounts can be created without modifying the people collection.
