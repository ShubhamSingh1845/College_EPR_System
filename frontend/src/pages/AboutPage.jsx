import { GraduationCap, Users } from "lucide-react";

const team = ["Shubham Kumar", "Gungun Gupta", "Sakshi Kumari Rai"];

export default function AboutPage() {
  return (
    <section className="page-content">
      <div className="page-heading"><div><p className="eyebrow">ABOUT CAMPUSONE</p><h1>College ERP Management System</h1><p className="muted">An original, role-aware workspace for academic and campus operations.</p></div></div>
      <div className="about-grid">
        <article className="chart-card"><div className="brand-mark"><GraduationCap size={22} /></div><h2>One campus, connected</h2><p>Manage people, courses, attendance, examinations, fees, library records and campus communications from a responsive dashboard powered by MongoDB.</p></article>
        <article className="chart-card"><div className="brand-mark"><Users size={22} /></div><h2>Project team</h2><ul>{team.map((name) => <li key={name}>{name}</li>)}</ul></article>
      </div>
      <p className="muted about-note">CampusOne is an independent project and is not affiliated with or endorsed by any university.</p>
    </section>
  );
}

