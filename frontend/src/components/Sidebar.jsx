import { NavLink } from "react-router-dom";
import {
  FiDatabase,
  FiBarChart2,
  FiMap,
  FiCpu,
  FiMessageSquare,
} from "react-icons/fi";
import "./Sidebar.css";

export default function Sidebar({ menu }) {
  // Map labels to icons
  const iconMap = {
    Dataset: <FiDatabase />,
    "EDA": <FiBarChart2 />,
    "Geo Hotspot Map": <FiMap />,
    "Operational Efficiency": <FiCpu />,
    "Risk Analysis": <FiCpu />,
    "Gemma Chatbot": <FiMessageSquare />,
  };

  return (
    <div className="sidebar-container">
      <h1 className="sidebar-logo">
        EMS<span className="logo-accent">Insight</span>
      </h1>

      <nav className="sidebar-nav">
        {menu.map((item) => (
          <SidebarItem
            key={item.path}
            to={item.path}
            icon={iconMap[item.label] || <FiDatabase />}
            label={item.label}
          />
        ))}
      </nav>
    </div>
  );
}

function SidebarItem({ to, icon, label }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        isActive ? "nav-item active" : "nav-item"
      }
    >
      <span className="nav-icon">{icon}</span>
      <span className="nav-label">{label}</span>
    </NavLink>
  );
}
