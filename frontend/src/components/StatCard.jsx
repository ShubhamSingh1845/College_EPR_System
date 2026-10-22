import { ArrowUpRight } from "lucide-react";

export default function StatCard({ label, value, hint, icon: Icon, tone = "blue" }) {
  return (
    <article className="stat-card">
      <div className={`stat-icon ${tone}`}><Icon size={19} /></div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-hint"><ArrowUpRight size={14} /> {hint}</div>
    </article>
  );
}

