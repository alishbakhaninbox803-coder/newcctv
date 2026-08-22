/*
FILE PATH: frontend/src/components/Nav.jsx
ACTION: REPLACE ENTIRE FILE
*/
import { NavLink } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

const links = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/events", label: "Events" },
  { to: "/alerts", label: "Alerts" },
  { to: "/persons", label: "Persons" },
  { to: "/unknown-persons", label: "Unknown Persons" },
  { to: "/zone-editor", label: "Zone Editor" },
  { to: "/stats", label: "Stats" },
  { to: "/health", label: "Health" },
];

export default function Nav() {
  const { username, logout } = useAuth();

  return (
    <nav className="border-b border-gray-800 bg-gray-950 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
      <div className="flex items-center gap-6">
        <span className="font-bold text-sm">🎥 Smart CCTV</span>
        <div className="flex gap-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded ${
                  isActive ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <span className="text-gray-400">{username}</span>
        <button
          onClick={logout}
          className="bg-gray-800 hover:bg-gray-700 rounded px-3 py-1.5"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}