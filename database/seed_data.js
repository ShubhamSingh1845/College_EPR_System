const databaseHandle = db.getSiblingDB("college_erp");

const seedOnce = (collection, id, document) => {
  databaseHandle[collection].updateOne(
    { _id: id },
    { $setOnInsert: { ...document, _id: id, created_at: new Date() } },
    { upsert: true },
  );
};

seedOnce("departments", "computer-science", { name: "Computer Science", code: "CSE", active: true });
seedOnce("departments", "business", { name: "Business Administration", code: "BUS", active: true });
seedOnce("courses", "btech-cse", { name: "B.Tech Computer Science", code: "BTECH-CSE", department_id: "computer-science", duration_semesters: 8 });
seedOnce("courses", "bba", { name: "Bachelor of Business Administration", code: "BBA", department_id: "business", duration_semesters: 6 });
seedOnce("subjects", "web-development", { name: "Web Development", code: "CSE-301", course_id: "btech-cse", semester: 5 });
seedOnce("subjects", "database-systems", { name: "Database Systems", code: "CSE-302", course_id: "btech-cse", semester: 5 });

print("Development reference data inserted only where records were missing.");

