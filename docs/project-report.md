# Project report

## College ERP Management System

CampusOne brings user, academic, attendance, assessment, fee and campus-support records into one role-aware interface. React/Vite provides the responsive dashboard and CRUD screens; FastAPI validates requests and enforces authentication/authorization; PyMongo persists records in MongoDB.

### Project group

- Shubham Kumar
- Gungun Gupta
- Sakshi Kumari Rai

### Dashboard data

Charts and totals are calculated from MongoDB attendance, published marks, invoices and confirmed payments. Pending/failed payments are not treated as collected revenue. A missing dataset produces an empty chart state rather than fabricated sample values.

### Local development

Follow the setup and launch commands in [the README](../README.md). Database setup and reference seeds are additive and safe to rerun.

