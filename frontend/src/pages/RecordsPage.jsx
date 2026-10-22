import { useEffect, useState } from "react";
import { Plus, Search } from "lucide-react";
import api from "../services/api";

const configs = {
  students: { title: "Students", fields: [["registration_number", "Registration number"], ["full_name", "Full name"], ["email", "Email", "email"], ["phone", "Phone"], ["department", "Department"], ["course", "Course"], ["semester", "Semester", "number"], ["academic_session", "Academic session"], ["address", "Address", "textarea"], ["enrollment_status", "Enrollment status", "select:active,on_leave,inactive"]] },
  faculty: { title: "Faculty", fields: [["employee_id", "Employee ID"], ["full_name", "Full name"], ["email", "Email", "email"], ["phone", "Phone"], ["department", "Department"], ["designation", "Designation"], ["qualifications", "Qualifications (comma-separated)"], ["assigned_subjects", "Assigned subjects (comma-separated)"], ["assigned_classes", "Assigned classes (comma-separated)"], ["employment_status", "Employment status", "select:active,on_leave,inactive"]] },
  departments: { title: "Departments", fields: [["name", "Department name"], ["code", "Department code"]] },
  courses: { title: "Courses", fields: [["name", "Course name"], ["code", "Course code"], ["department_id", "Department ID"], ["duration_semesters", "Duration (semesters)", "number"]] },
  subjects: { title: "Subjects", fields: [["name", "Subject name"], ["code", "Subject code"], ["course_id", "Course ID"], ["semester", "Semester", "number"]] },
  enrollments: { title: "Enrollments", fields: [["student_id", "Student ID"], ["course_id", "Course ID"], ["academic_session", "Academic session"], ["semester", "Semester", "number"], ["status", "Status"]] },
  assessments: { title: "Assessments", fields: [["name", "Assessment name"], ["subject_id", "Subject ID"], ["max_marks", "Maximum marks", "number"], ["date", "Assessment date", "date"]] },
  library_books: { title: "Library", fields: [["isbn", "ISBN"], ["title", "Book title"], ["author", "Author"], ["copies", "Copies", "number"]] },
  book_issues: { title: "Book issues", fields: [["book_id", "Book"], ["student_id", "Student"], ["due_date", "Due date", "date"]] },
  timetables: { title: "Timetable", fields: [["course_id", "Course ID"], ["subject_id", "Subject ID"], ["semester", "Semester", "number"], ["day", "Day"], ["start_time", "Start time"], ["end_time", "End time"], ["room", "Room"]] },
  notifications: { title: "Notifications", fields: [["title", "Title"], ["message", "Message", "textarea"], ["audience", "Audience (all, student, faculty)"]] },
  feedback: { title: "Feedback", fields: [["subject", "Subject"], ["message", "Feedback", "textarea"]] },
  attendance: { title: "Attendance", fields: [["student_id", "Active student"], ["subject_id", "Subject"], ["class_session", "Class session identifier"], ["status", "Attendance status", "select:present,absent,late,excused"]] },
  marks: { title: "Marks entry", fields: [["student_id", "Student ID"], ["assessment_id", "Assessment ID"], ["subject_id", "Subject ID"], ["semester", "Semester", "number"], ["maximum_marks", "Maximum marks", "number"], ["marks_obtained", "Marks obtained", "number"]], columns: ["student_id", "subject_id", "semester", "marks_obtained", "maximum_marks", "percentage", "status"] },
  results: { title: "Published results" },
  fee_invoices: { title: "Fee invoices", fields: [["student_id", "Student (registration number)"], ["description", "Description"], ["amount_due", "Amount due", "number"], ["due_date", "Due date", "date"]] },
  payments: { title: "Payments", fields: [["invoice_id", "Invoice ID"], ["amount", "Payment amount", "number"], ["method", "Method (cash, bank, test)"], ["reference", "Reference"]] },
  fee_structures: { title: "Fee structures", fields: [["name", "Fee name"], ["academic_session", "Academic session"], ["semester", "Semester", "number"], ["department_id", "Department ID"], ["amount", "Amount", "number"]] },
  leave_applications: { title: "Leave applications", fields: [["start_date", "Start date", "date"], ["end_date", "End date", "date"], ["reason", "Reason", "textarea"]] },
  users: { title: "User accounts", fields: [["email", "Email", "email"], ["name", "Full name"], ["password", "Initial password (12+ characters)", "password"], ["role", "Role", "select:admin,faculty,student"], ["profile_id", "Linked student/faculty profile ID"]] },
  audit_logs: { title: "Audit logs" },
};

const optionalFields = new Set(["address", "qualifications", "assigned_subjects", "assigned_classes", "reference", "profile_id"]);
const listFields = new Set(["qualifications", "assigned_subjects", "assigned_classes"]);

export default function RecordsPage({ resource, user, onSaved }) {
  const config = configs[resource] || { title: resource };
  const [items, setItems] = useState([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState({});
  const [editId, setEditId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [students, setStudents] = useState([]);
  const [studentsLoading, setStudentsLoading] = useState(false);
  const [studentsError, setStudentsError] = useState("");
  const [books, setBooks] = useState([]);
  const [booksLoading, setBooksLoading] = useState(false);
  const [booksError, setBooksError] = useState("");
  const [subjects, setSubjects] = useState([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);
  const [subjectsError, setSubjectsError] = useState("");

  async function load() {
    setLoadError("");
    try {
      const response = await api.get(`/${resource}`, { params: { search, page, page_size: 20 } });
      setItems(response.data.items || []);
      setTotal(response.data.total ?? response.data.items?.length ?? 0);
    } catch (requestError) {
      setLoadError(requestError.response?.data?.detail || `Unable to load ${config.title.toLowerCase()}.`);
    }
  }

  useEffect(() => { load(); }, [resource, search, page]);

  useEffect(() => {
    const needsInvoiceStudents = resource === "fee_invoices" && user.role === "admin";
    const needsIssueStudents = resource === "book_issues" && user.role !== "student";
    const needsAttendanceStudents = resource === "attendance" && ["admin", "faculty"].includes(user.role);
    if (!needsInvoiceStudents && !needsIssueStudents && !needsAttendanceStudents) return undefined;
    let cancelled = false;
    setStudentsLoading(true);
    setStudentsError("");
    api.get("/students", { params: { page_size: 100 } })
      .then((response) => {
        if (!cancelled) setStudents(response.data.items || []);
      })
      .catch((requestError) => {
        if (!cancelled) setStudentsError(requestError.response?.data?.detail || "Unable to load students.");
      })
      .finally(() => {
        if (!cancelled) setStudentsLoading(false);
      });
    return () => { cancelled = true; };
  }, [resource, user.role]);

  useEffect(() => {
    if (resource !== "book_issues") return undefined;
    let cancelled = false;
    setBooksLoading(true);
    setBooksError("");
    api.get("/library_books", { params: { page_size: 100 } })
      .then((response) => {
        if (!cancelled) setBooks(response.data.items || []);
      })
      .catch((requestError) => {
        if (!cancelled) setBooksError(requestError.response?.data?.detail || "Unable to load library books.");
      })
      .finally(() => {
        if (!cancelled) setBooksLoading(false);
      });
    return () => { cancelled = true; };
  }, [resource]);

  useEffect(() => {
    const needsAttendanceStudents = resource === "attendance" && ["admin", "faculty"].includes(user.role);
    if (resource !== "attendance") return undefined;
    if (resource === "attendance" && !needsAttendanceStudents) return undefined;
    let cancelled = false;
    setSubjectsLoading(true);
    setSubjectsError("");
    api.get("/subjects", { params: { page_size: 100 } })
      .then((response) => {
        if (!cancelled) setSubjects(response.data.items || []);
      })
      .catch((requestError) => {
        if (!cancelled) setSubjectsError(requestError.response?.data?.detail || "Unable to load subjects.");
      })
      .finally(() => {
        if (!cancelled) setSubjectsLoading(false);
      });
    return () => { cancelled = true; };
  }, [resource, user.role]);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = { ...form };
      for (const [key, , type] of config.fields || []) {
        if (type === "number" && payload[key] !== undefined && payload[key] !== "") payload[key] = Number(payload[key]);
        if (listFields.has(key) && typeof payload[key] === "string") payload[key] = payload[key].split(",").map((value) => value.trim()).filter(Boolean);
      }
      if (editId) await api.patch(`/${resource}/${editId}`, payload);
      else await api.post(`/${resource}`, payload);
      setForm({});
      setEditId("");
      setFormOpen(false);
      await load();
      onSaved?.();
      window.dispatchEvent(new Event("erp:refresh"));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not save the record.");
    } finally {
      setBusy(false);
    }
  }

  function beginEdit(item) {
    setEditId(item._id);
    setForm(Object.fromEntries((config.fields || []).map(([key]) => [key, Array.isArray(item[key]) ? item[key].join(", ") : item[key] ?? ""])));
    setFormOpen(true);
  }

  async function deactivate(item) {
    if (!window.confirm(`Safely deactivate ${item.full_name || "this record"}? The record will be retained.`)) return;
    const statusField = resource === "students" ? "enrollment_status" : "employment_status";
    try {
      await api.patch(`/${resource}/${item._id}`, { [statusField]: "inactive" });
      await load();
      window.dispatchEvent(new Event("erp:refresh"));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not deactivate this record.");
    }
  }

  async function reviewLeave(item, status) {
    try {
      await api.patch(`/leave_applications/${item._id}`, { status });
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not review the leave application.");
    }
  }

  async function returnBook(item) {
    try {
      await api.patch(`/book_issues/${item._id}/return`);
      await load();
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not return the book.");
    }
  }

  async function publishMark(item) {
    try {
      await api.post(`/results/${item._id}/approve`);
      await load();
      window.dispatchEvent(new Event("erp:refresh"));
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Could not publish this result.");
    }
  }

  const canCreate = user.role === "admin" && !!config.fields;
  const canRecord = ["attendance", "marks"].includes(resource) && ["admin", "faculty"].includes(user.role)
    || ["fee_invoices", "payments"].includes(resource) && user.role === "admin"
    || resource === "book_issues" && ["admin", "faculty", "student"].includes(user.role)
    || ["leave_applications", "feedback"].includes(resource) && ["student", "faculty"].includes(user.role);
  const editablePeople = ["students", "faculty"].includes(resource) && user.role === "admin";
  const columns = config.columns || (config.fields
    ? config.fields.map(([field]) => field).slice(0, 8)
    : Object.keys(items[0] || {}).filter((key) => !["_id", "password_hash"].includes(key)).slice(0, 5));
  const hasActions = editablePeople
    || resource === "leave_applications" && user.role === "admin"
    || resource === "book_issues" && ["admin", "faculty"].includes(user.role)
    || resource === "marks" && user.role === "admin";
  const selectableStudents = resource === "attendance"
    ? students.filter((student) => student.enrollment_status === "active")
    : students;

  return (
    <section className="page-content">
      <div className="page-heading">
        <div><p className="eyebrow">MANAGEMENT</p><h1>{config.title}</h1><p className="muted">Search and review records stored in the college database.</p></div>
        {(canCreate || canRecord) && <button className="primary-button" onClick={() => { setEditId(""); setForm({}); setFormOpen(!formOpen); }}><Plus size={17} /> Add record</button>}
      </div>
      {error && <div className="alert error">{error}</div>}
      {loadError && <div className="alert error">{loadError}</div>}
      {formOpen && (
        <form className="record-form" onSubmit={submit}>
          <h2>{editId ? "Edit record" : `New ${config.title.toLowerCase()} record`}</h2>
          <div className="form-grid">{config.fields.map(([key, label, type]) => {
            const required = !optionalFields.has(key) && !(resource === "book_issues" && user.role === "student" && key === "student_id");
            if (resource === "book_issues" && key === "student_id" && user.role === "student") return null;
            return <label key={key}>{label}{(resource === "fee_invoices" || resource === "book_issues" || resource === "attendance") && key === "student_id"
              ? <select required value={form[key] || ""} disabled={studentsLoading || selectableStudents.length === 0} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>
                  <option value="">{studentsLoading ? "Loading students…" : selectableStudents.length ? "Choose a student…" : "No active students available"}</option>
                  {selectableStudents.map((student) => <option key={student._id} value={student._id}>{student.registration_number} — {student.full_name}</option>)}
                </select>
              : resource === "attendance" && key === "subject_id"
                ? <select required value={form[key] || ""} disabled={subjectsLoading || subjects.length === 0} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>
                    <option value="">{subjectsLoading ? "Loading subjects…" : subjects.length ? "Choose a subject…" : "No subjects available"}</option>
                    {subjects.map((subject) => <option key={subject._id} value={subject._id}>{subject.name}{subject.code ? ` — ${subject.code}` : ""}</option>)}
                  </select>
              : resource === "book_issues" && key === "book_id"
                ? <select required value={form[key] || ""} disabled={booksLoading || !books.some((book) => Number(book.copies_available ?? book.copies) > 0)} onChange={(event) => setForm({ ...form, [key]: event.target.value })}>
                    <option value="">{booksLoading ? "Loading books…" : books.some((book) => Number(book.copies_available ?? book.copies) > 0) ? "Choose an available book…" : "No books available"}</option>
                    {books.filter((book) => Number(book.copies_available ?? book.copies) > 0).map((book) => <option key={book._id} value={book._id}>{book.title}{book.isbn ? ` — ISBN ${book.isbn}` : ""} (${Number(book.copies_available ?? book.copies)} available)</option>)}
                  </select>
              : type === "textarea" ? <textarea required={required} value={form[key] || ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })} /> : type?.startsWith("select:") ? <select required={required} value={form[key] || ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })}><option value="">Choose…</option>{type.slice(7).split(",").map((choice) => <option key={choice} value={choice}>{choice}</option>)}</select> : <input type={type || "text"} required={required} min={type === "number" && key === "semester" ? 1 : undefined} value={form[key] ?? ""} onChange={(event) => setForm({ ...form, [key]: event.target.value })} />}</label>;
          })}</div>
          {studentsError && ["fee_invoices", "book_issues"].includes(resource) && <p className="form-help">{studentsError}</p>}
          {resource === "fee_invoices" && !studentsError && <p className="form-help">Choose a student by registration number; the invoice will be linked to their profile.</p>}
          {resource === "book_issues" && booksError && <p className="form-help">{booksError}</p>}
          {resource === "book_issues" && !booksError && <p className="form-help">Choose an available book and student; the issue is saved with their profile IDs.</p>}
          {resource === "faculty" && <p className="form-help">Separate qualifications, assigned subjects and classes with commas.</p>}
          {resource === "attendance" && studentsError && <p className="form-help">{studentsError}</p>}
          {resource === "attendance" && subjectsError && <p className="form-help">{subjectsError}</p>}
          {resource === "attendance" && !studentsError && !subjectsError && <p className="form-help">Choose a student and subject; each class session can only be recorded once.</p>}
          {resource === "payments" && <p className="form-help">Only confirmed offline/test payments are recorded as collected funds.</p>}
          {resource === "book_issues" && user.role === "student" && <p className="form-help">The issue will be linked to your student profile.</p>}
          <div className="form-actions"><button type="button" className="secondary-button" onClick={() => setFormOpen(false)}>Cancel</button><button className="primary-button" disabled={busy}>{busy ? "Saving…" : "Save record"}</button></div>
        </form>
      )}
      <div className="table-toolbar"><label className="search-box"><Search size={17} /><input placeholder={`Search ${config.title.toLowerCase()}…`} value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label><span>{total} records</span></div>
      <div className="table-card"><div className="table-scroll"><table>
        <thead><tr>{columns.map((column) => <th key={column}>{column.replaceAll("_", " ")}</th>)}{hasActions && <th>Actions</th>}</tr></thead>
        <tbody>{items.map((item) => <tr key={item._id}>
          {columns.map((column) => <td key={column}>{Array.isArray(item[column]) ? item[column].join(", ") : item[column] instanceof Object ? JSON.stringify(item[column]) : String(item[column] ?? "—")}</td>)}
          {editablePeople && <td><div className="row-actions"><button onClick={() => beginEdit(item)}>Edit</button><button className="danger-link" onClick={() => deactivate(item)}>Deactivate</button></div></td>}
          {resource === "leave_applications" && user.role === "admin" && <td>{item.status === "pending" ? <div className="row-actions"><button onClick={() => reviewLeave(item, "approved")}>Approve</button><button className="danger-link" onClick={() => reviewLeave(item, "rejected")}>Reject</button></div> : item.status}</td>}
          {resource === "book_issues" && ["admin", "faculty"].includes(user.role) && <td>{item.returned_at ? "Returned" : <div className="row-actions"><button onClick={() => returnBook(item)}>Record return</button></div>}</td>}
          {resource === "marks" && user.role === "admin" && <td>{item.status === "submitted" ? <div className="row-actions"><button onClick={() => publishMark(item)}>Publish result</button></div> : item.status}</td>}
        </tr>)}{!items.length && <tr><td className="empty-cell" colSpan={Math.max(columns.length + (hasActions ? 1 : 0), 1)}>{loadError ? "Records could not be loaded." : "No records found."}</td></tr>}</tbody>
      </table></div></div>
      <div className="pagination"><span>Page {page} of {Math.max(1, Math.ceil(total / 20))}</span><div><button className="secondary-button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button><button className="secondary-button" disabled={page * 20 >= total} onClick={() => setPage(page + 1)}>Next</button></div></div>
    </section>
  );
}
