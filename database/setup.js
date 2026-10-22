const databaseName = "college_erp";
const databaseHandle = db.getSiblingDB(databaseName);

const collections = [
  "users", "students", "faculty", "departments", "courses", "subjects",
  "enrollments", "attendance", "assessments", "marks", "results",
  "fee_structures", "fee_invoices", "payments", "leave_applications",
  "library_books", "book_issues", "timetables", "notifications", "feedback",
  "audit_logs",
];
const validators = {
  users: { $jsonSchema: { bsonType: "object", required: ["email", "password_hash", "role"], properties: { email: { bsonType: "string" }, password_hash: { bsonType: "string" }, role: { enum: ["admin", "faculty", "student"] } } } },
  students: { $jsonSchema: { bsonType: "object", required: ["registration_number", "full_name", "email"], properties: { registration_number: { bsonType: "string" }, full_name: { bsonType: "string" }, email: { bsonType: "string" }, semester: { bsonType: ["int", "long", "double"] } } } },
  faculty: { $jsonSchema: { bsonType: "object", required: ["faculty_id", "employee_id", "full_name", "email"], properties: { faculty_id: { bsonType: "string", minLength: 1 }, employee_id: { bsonType: "string", minLength: 1 }, full_name: { bsonType: "string", minLength: 2 }, email: { bsonType: "string", minLength: 3 } } } },
  attendance: { $jsonSchema: { bsonType: "object", required: ["student_id", "subject_id", "class_session", "status"], properties: { status: { enum: ["present", "absent", "late", "excused"] } } } },
  payments: { $jsonSchema: { bsonType: "object", required: ["invoice_id", "amount", "status"], properties: { amount: { bsonType: ["int", "long", "double", "decimal"], minimum: 0 }, status: { enum: ["pending", "confirmed", "failed"] } } } },
};

const existing = new Set(databaseHandle.getCollectionNames());
for (const name of collections) {
  if (!existing.has(name)) {
    databaseHandle.createCollection(name);
  }
}
for (const [name, validator] of Object.entries(validators)) {
  const info = databaseHandle.getCollectionInfos({ name })[0];
  if (!info.options?.validator) {
    databaseHandle.runCommand({ collMod: name, validator, validationLevel: "moderate", validationAction: "error" });
  }
}

const sameKey = (left, right) => JSON.stringify(left) === JSON.stringify(right);
const ensureIndex = (collectionName, key, options = {}) => {
  const collection = databaseHandle.getCollection(collectionName);
  const existingIndex = collection.getIndexes().find((index) => sameKey(index.key, key));
  if (existingIndex && (!options.unique || existingIndex.unique)) return;
  if (existingIndex && options.unique) {
    const field = Object.keys(key)[0];
    collection.createIndex(key, {
      ...options,
      name: `${options.name}_present`,
      partialFilterExpression: options.partialFilterExpression || { [field]: { $type: "string" } },
    });
    return;
  }
  collection.createIndex(key, options);
};

ensureIndex("users", { email: 1 }, { unique: true, name: "users_email_unique" });
ensureIndex("students", { registration_number: 1 }, { unique: true, name: "students_registration_unique" });
ensureIndex("students", { email: 1 }, { unique: true, name: "students_email_unique" });
ensureIndex("faculty", { employee_id: 1 }, { unique: true, name: "faculty_employee_unique" });
ensureIndex("faculty", { email: 1 }, { unique: true, name: "faculty_email_unique" });
ensureIndex("enrollments", { student_id: 1, course_id: 1, academic_session: 1 }, { unique: true, name: "enrollments_student_course_session_unique" });
ensureIndex("attendance", { student_id: 1, subject_id: 1, class_session: 1 }, { unique: true, name: "attendance_session_unique" });
ensureIndex("attendance", { subject_id: 1, recorded_at: -1 }, { name: "attendance_subject_date" });
ensureIndex("marks", { student_id: 1, assessment_id: 1 }, { unique: true, name: "marks_student_assessment_unique" });
ensureIndex("fee_invoices", { student_id: 1, due_date: 1 }, { name: "invoices_student_due_date" });
ensureIndex("payments", { invoice_id: 1, status: 1 }, { name: "payments_invoice_status" });
ensureIndex("book_issues", { student_id: 1, returned_at: 1 }, { name: "book_issues_student_returned" });
ensureIndex("book_issues", { student_id: 1, book_id: 1 }, { unique: true, name: "book_issue_active_unique", partialFilterExpression: { returned_at: null } });
ensureIndex("audit_logs", { created_at: -1 }, { name: "audit_logs_recent" });

print(`Database ${databaseName} is ready. Collections: ${databaseHandle.getCollectionNames().length}`);
