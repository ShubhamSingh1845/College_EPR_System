import { lazy, Suspense, useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import {
  Activity, Bell, BookOpen, BookOpenCheck, CalendarDays, ChartNoAxesCombined,
  CircleDollarSign, FileCheck2, GraduationCap, LayoutDashboard, LogOut,
  Menu, Moon, Settings2, Sun, Users, X,
} from "lucide-react";
import LoginPage from "./pages/LoginPage";
import RecordsPage from "./pages/RecordsPage";
import api from "./services/api";

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const AboutPage = lazy(() => import("./pages/AboutPage"));

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, roles: ["admin", "faculty", "student"] },
  { to: "/students", label: "Students", icon: GraduationCap, roles: ["admin", "faculty", "student"] },
  { to: "/faculty", label: "Faculty", icon: Users, roles: ["admin", "faculty"] },
  { to: "/departments", label: "Departments", icon: BookOpen, roles: ["admin", "faculty"] },
  { to: "/courses", label: "Courses & subjects", icon: BookOpenCheck, roles: ["admin", "faculty"] },
  { to: "/subjects", label: "Subjects", icon: BookOpen, roles: ["admin", "faculty"] },
  { to: "/attendance", label: "Attendance", icon: CalendarDays, roles: ["admin", "faculty"] },
  { to: "/assessments", label: "Examinations", icon: FileCheck2, roles: ["admin", "faculty"] },
  { to: "/marks", label: "Marks entry", icon: ChartNoAxesCombined, roles: ["admin", "faculty"] },
  { to: "/results", label: "Results", icon: ChartNoAxesCombined, roles: ["admin", "faculty", "student"] },
  { to: "/fee_invoices", label: "Fees & payments", icon: CircleDollarSign, roles: ["admin", "student"] },
  { to: "/fee_structures", label: "Fee structures", icon: CircleDollarSign, roles: ["admin"] },
  { to: "/payments", label: "Payment history", icon: CircleDollarSign, roles: ["admin", "student"] },
  { to: "/library_books", label: "Library", icon: BookOpen, roles: ["admin", "faculty", "student"] },
  { to: "/book_issues", label: "Book issues", icon: BookOpenCheck, roles: ["admin", "faculty", "student"] },
  { to: "/timetables", label: "Timetable", icon: CalendarDays, roles: ["admin", "faculty", "student"] },
  { to: "/leave_applications", label: "Leave", icon: FileCheck2, roles: ["admin", "faculty", "student"] },
  { to: "/notifications", label: "Notifications", icon: Bell, roles: ["admin", "faculty", "student"] },
  { to: "/feedback", label: "Feedback", icon: Activity, roles: ["admin", "faculty", "student"] },
  { to: "/audit_logs", label: "Audit log", icon: Settings2, roles: ["admin"] },
  { to: "/reports", label: "Reports", icon: ChartNoAxesCombined, roles: ["admin", "faculty"] },
  { to: "/users", label: "User accounts", icon: Users, roles: ["admin"] },
  { to: "/about", label: "About the project", icon: GraduationCap, roles: ["admin", "faculty", "student"] },
];

export default function App() {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(Boolean(localStorage.getItem("erp-token")));
  const [dark, setDark] = useState(localStorage.getItem("erp-dark") === "true");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("erp-dark", String(dark));
  }, [dark]);

  useEffect(() => {
    const logout = () => { setUser(null); setChecking(false); navigate("/login"); };
    window.addEventListener("erp:unauthorized", logout);
    return () => window.removeEventListener("erp:unauthorized", logout);
  }, [navigate]);

  useEffect(() => {
    if (!localStorage.getItem("erp-token")) { setChecking(false); return; }
    api.get("/auth/me").then((response) => setUser(response.data)).catch(() => {
      localStorage.removeItem("erp-token");
      setUser(null);
    }).finally(() => setChecking(false));
  }, []);

  function signOut() {
    localStorage.removeItem("erp-token");
    setUser(null);
    navigate("/login");
  }

  if (checking) return <div className="loading-screen">Loading your secure workspace…</div>;
  if (!user) return <Routes><Route path="/login" element={<LoginPage onLogin={(value) => { setUser(value); navigate("/"); }} />} /><Route path="*" element={<Navigate to="/login" replace />} /></Routes>;

  const title = links.find((link) => link.to === location.pathname)?.label || "College ERP";
  const shownLinks = links.filter((link) => link.roles.includes(user.role));
  return (
    <div className={`app-shell ${dark ? "dark" : ""}`}>
      {sidebarOpen && <button aria-label="Close menu" className="mobile-scrim" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <div className="brand"><div className="brand-mark"><GraduationCap size={21} /></div><div><strong>CampusOne</strong><span>COLLEGE ERP</span></div><button aria-label="Close navigation" className="sidebar-close" onClick={() => setSidebarOpen(false)}><X size={18} /></button></div>
        <p className="nav-caption">WORKSPACE</p>
        <nav>{shownLinks.map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === "/"} onClick={() => setSidebarOpen(false)} className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}><Icon size={18} /><span>{label}</span></NavLink>)}</nav>
        <div className="sidebar-bottom"><div className="profile-mini"><div className="avatar">{user.name?.[0] || user.email[0]}</div><div><strong>{user.name || user.email}</strong><span>{user.role}</span></div></div><button className="nav-link logout" onClick={signOut}><LogOut size={18} /><span>Sign out</span></button></div>
      </aside>
      <main className="main-area">
        <header className="topbar"><div className="topbar-left"><button aria-label="Open navigation" className="menu-button" onClick={() => setSidebarOpen(true)}><Menu size={20} /></button><span className="breadcrumb">Workspace <span>/</span> {title}</span></div><div className="topbar-actions"><span className="role-chip">{user.role}</span><button className="icon-button" aria-label="Toggle dark mode" onClick={() => setDark(!dark)}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button><button className="icon-button notification-button" aria-label="Notifications" onClick={() => navigate("/notifications")}><Bell size={18} /><i /></button><div className="top-avatar">{user.name?.[0] || user.email[0]}</div></div></header>
        <Suspense fallback={<div className="loading-screen">Loading page…</div>}>
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/reports" element={<DashboardPage />} />
            {shownLinks.filter((link) => link.to !== "/" && link.to !== "/about" && link.to !== "/reports").map((link) => <Route key={link.to} path={link.to} element={<RecordsPage resource={link.to.slice(1)} user={user} />} />)}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
