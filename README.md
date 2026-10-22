# College ERP Management System

CampusOne is a React and FastAPI college ERP starter with MongoDB-backed accounts, records, academic workflows, fee tracking and live dashboard charts. The project team is **Shubham Kumar, Gungun Gupta and Sakshi Kumari Rai**.

## Requirements

- Windows 10/11, PowerShell
- Python 3.11 or newer and `py` launcher
- Node.js 20 or newer and npm
- MongoDB Community Server 7+ and `mongosh`

Check the tools in PowerShell:

```powershell
python --version
node --version
npm --version
mongod --version
mongosh --version
```

Install Python from [python.org](https://www.python.org/downloads/windows/), Node.js LTS from [nodejs.org](https://nodejs.org/), and MongoDB Community Server from [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community). Install MongoDB Shell separately if `mongosh --version` is unavailable. During MongoDB installation, enable the Windows service.

## Database-first setup

Open PowerShell in the project folder:

```powershell
Set-Location 'C:\Users\Administrator\Desktop\shubham.py\COLLAGE ERP MANAGEMENT SYSTEM'
Get-Service MongoDB
Start-Service MongoDB
mongosh 'mongodb://127.0.0.1:27017/college_erp' --file '.\database\setup.js'
mongosh 'mongodb://127.0.0.1:27017/college_erp' --file '.\database\seed_data.js'
mongosh 'mongodb://127.0.0.1:27017/college_erp' --eval 'db.getCollectionNames().sort()'
```

The setup script creates missing collections and indexes, and adds validators only to collections without an existing validator. The seed script uses set-on-insert records and does not replace existing records. It never drops a database or collection.

## Configure and start the FastAPI backend

In a backend PowerShell terminal:

```powershell
Set-Location 'C:\Users\Administrator\Desktop\shubham.py\COLLAGE ERP MANAGEMENT SYSTEM\backend'
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Edit `backend\.env` before starting. Set `JWT_SECRET` to a strong unique value (generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"`); the API refuses to start if the placeholder or a short secret is still configured. `FRONTEND_ORIGIN` accepts a comma-separated list of exact allowed browser origins. Set `ERP_SEED_ADMIN_EMAIL` and choose a unique `ERP_SEED_ADMIN_PASSWORD` with at least 12 characters. Never commit `.env`.

Verify MongoDB before seeding or starting the API:

```powershell
mongosh 'mongodb://127.0.0.1:27017/college_erp' --eval 'db.runCommand({ ping: 1 })'
python -m app.seed
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

The seed command inserts the initial administrator only when that account does not already exist. Open `http://127.0.0.1:8001/docs` for interactive API documentation and `http://127.0.0.1:8001/api/health/database` to confirm the live database connection.

## Start the React frontend

In a separate PowerShell terminal:

```powershell
Set-Location 'C:\Users\Administrator\Desktop\shubham.py\COLLAGE ERP MANAGEMENT SYSTEM\frontend'
Copy-Item .env.example .env
npm install
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`) and sign in with the admin username or email and password configured for the seed command. The frontend API URL can be changed in `frontend\.env`.

## Implemented API and UI

- JWT sign-in, current-user endpoint, password hashing, role checks and protected student-specific results/records.
- Student and faculty create/search/list/update APIs with duplicate identifiers rejected by MongoDB indexes; faculty employee IDs are also stored as the legacy-compatible `faculty_id`.
- Administrator account provisioning with optional linked student/faculty profiles.
- Database-driven attendance, marks, result approval/publication and fee dashboard analytics.
- Duplicate attendance prevention per student, subject and class session; marks validation; invoice and confirmed-payment tracking; leave applications and administrator review.
- Generic administration of departments, courses, subjects, enrollments, assessments, library book records, timetables, notifications and feedback; audit events for key write actions.
- Responsive dashboards with empty/loading/error states, live Recharts visualizations, dark mode and navigation by role.

Payment records currently represent authorized offline/test-mode confirmations; no real payment gateway is configured. Configure and verify a gateway independently before accepting real payments. This starter is not a production compliance certification: add deployment-grade secret management, backups, monitoring, rate limiting and institution-specific authorization/workflows before production use.

## Tests and production build

With MongoDB running and backend requirements installed:

```powershell
Set-Location 'C:\Users\Administrator\Desktop\shubham.py\COLLAGE ERP MANAGEMENT SYSTEM\backend'
.\.venv\Scripts\Activate.ps1
pytest
```

Frontend production bundle:

```powershell
Set-Location 'C:\Users\Administrator\Desktop\shubham.py\COLLAGE ERP MANAGEMENT SYSTEM\frontend'
npm run build
```

For a manual end-to-end check, sign in as the admin, add a student and faculty record, verify the student with `mongosh 'mongodb://127.0.0.1:27017/college_erp' --eval 'db.students.find({}, {registration_number:1, full_name:1}).pretty()'`, then use the authenticated API docs to record attendance and marks, publish a result, create an invoice and record an offline payment. Refresh the dashboard to see analytics recomputed from MongoDB.
