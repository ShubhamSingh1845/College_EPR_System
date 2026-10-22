import { useMemo } from "react";
import { Activity, BookOpenCheck, CircleDollarSign, GraduationCap, Users } from "lucide-react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import ChartCard from "../components/ChartCard";
import StatCard from "../components/StatCard";
import { useDashboard } from "../hooks/useDashboard";

const colors = ["#5d6bdb", "#25b99a", "#f5a623", "#ec6688"];
const money = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value || 0);

function ChartState({ loading, error, empty, onRetry }) {
  if (loading) return <div className="chart-state">Loading live records…</div>;
  if (error) return <div className="chart-state error-state">{error} <button onClick={onRetry}>Retry</button></div>;
  if (empty) return <div className="chart-state">No records yet. Add data to see this chart.</div>;
  return null;
}

export default function DashboardPage() {
  const { data, loading, error, refresh } = useDashboard();
  const counts = data?.counts || {};
  const performance = useMemo(() => data?.marks_by_subject || [], [data]);

  return (
    <div className="page-content">
      <div className="page-heading">
        <div><p className="eyebrow">CAMPUS OVERVIEW</p><h1>Dashboard</h1><p className="muted">A live snapshot of your college operations.</p></div>
        <button className="secondary-button" onClick={refresh}><Activity size={16} /> Refresh data</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      <div className="stats-grid">
        <StatCard label="Active students" value={loading ? "—" : (counts.students || 0).toLocaleString()} hint="Current enrollment" icon={GraduationCap} />
        <StatCard label="Faculty members" value={loading ? "—" : (counts.faculty || 0).toLocaleString()} hint="Active staff" icon={Users} tone="purple" />
        <StatCard label="Attendance records" value={loading ? "—" : (counts.attendance_records || 0).toLocaleString()} hint="Recorded sessions" icon={BookOpenCheck} tone="green" />
        <StatCard label="Fees collected" value={loading ? "—" : money(counts.fees_collected)} hint={`${money(counts.fees_outstanding)} outstanding`} icon={CircleDollarSign} tone="orange" />
      </div>
      <div className="charts-grid">
        <ChartCard title="Attendance overview" subtitle="Present, absent, late and excused records">
          <ChartState loading={loading} error={error} empty={!data?.attendance?.some((item) => item.value)} onRetry={refresh} />
          {!loading && !error && data?.attendance?.some((item) => item.value > 0) && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.attendance} dataKey="value" nameKey="name" innerRadius={58} outerRadius={88} paddingAngle={4}>{data.attendance.map((entry, index) => <Cell key={entry.name} fill={colors[index]} />)}</Pie><Tooltip /><Legend verticalAlign="bottom" /></PieChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Subject attendance" subtitle="Percentage of sessions attended">
          <ChartState loading={loading} error={error} empty={!data?.attendance_by_subject?.length} onRetry={refresh} />
          {!loading && !error && !!data?.attendance_by_subject?.length && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.attendance_by_subject} margin={{ left: -18, right: 8 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="subject" tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="percentage" fill="#6675e8" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Published marks" subtitle="Student count by grade band">
          <ChartState loading={loading} error={error} empty={!data?.marks_distribution?.some((item) => item.value)} onRetry={refresh} />
          {!loading && !error && data?.marks_distribution?.some((item) => item.value > 0) && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data.marks_distribution} dataKey="value" nameKey="name" outerRadius={90} paddingAngle={3}>{data.marks_distribution.map((entry, index) => <Cell key={entry.name} fill={colors[index]} />)}</Pie><Tooltip /><Legend verticalAlign="bottom" /></PieChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Average marks by subject" subtitle="Published result percentage">
          <ChartState loading={loading} error={error} empty={!performance.length} onRetry={refresh} />
          {!loading && !error && !!performance.length && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={performance} margin={{ left: -18, right: 8 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="subject" tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="average" fill="#9b72cf" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Fee collection" subtitle="Confirmed money and open balances">
          <ChartState loading={loading} error={error} empty={!counts.fees_collected && !counts.fees_outstanding} onRetry={refresh} />
          {!loading && !error && (!!counts.fees_collected || !!counts.fees_outstanding) && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.fee_collection}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis tickFormatter={(value) => `₹${value}`} /><Tooltip formatter={(value) => money(value)} /><Bar dataKey="amount" fill="#25b99a" radius={[6, 6, 0, 0]} /></BarChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Academic performance" subtitle="Published average by semester">
          <ChartState loading={loading} error={error} empty={!data?.performance_by_semester?.length} onRetry={refresh} />
          {!loading && !error && !!data?.performance_by_semester?.length && <div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={data.performance_by_semester} margin={{ left: -18, right: 12 }}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="semester" tick={{ fontSize: 11 }} /><YAxis domain={[0, 100]} tick={{ fontSize: 11 }} /><Tooltip /><Line type="monotone" dataKey="average" stroke="#5969db" strokeWidth={3} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div>}
        </ChartCard>
        <ChartCard title="Recent activity" subtitle="Latest recorded administrative events">
          <ChartState loading={loading} error={error} empty={!data?.recent_activities?.length} onRetry={refresh} />
          {!loading && !error && !!data?.recent_activities?.length && <ul className="activity-list">{data.recent_activities.map((item) => <li key={item._id}><span className="activity-dot" /><div><strong>{(item.action || "Activity").replaceAll(".", " ")}</strong><p>{item.actor_id || "System"} · {item.created_at ? new Date(item.created_at).toLocaleString() : "Recently"}</p></div></li>)}</ul>}
        </ChartCard>
      </div>
      <footer className="project-footer">College ERP Management System <span>Project team: Shubham Kumar · Gungun Gupta · Sakshi Kumari Rai</span></footer>
    </div>
  );
}
