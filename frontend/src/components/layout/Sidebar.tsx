import { NavLink } from "react-router-dom";
import { LayoutDashboard, Search, TrendingUp, Settings, BarChart3 } from "lucide-react";
import { ThemeToggle } from "../ui/Theme";

const LINKS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/overview", label: "Overview", icon: BarChart3, end: false },
  { to: "/search", label: "Search", icon: Search, end: false },
  { to: "/settings", label: "Settings", icon: Settings, end: false },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-brand-mark">
          <TrendingUp size={16} />
        </div>
        <span>RAG Stock Advisor</span>
      </div>

      <nav className="sidebar-nav">
        {LINKS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={({ isActive }) => `sidebar-link${isActive ? " active" : ""}`}>
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <ThemeToggle />
      </div>
    </aside>
  );
}
