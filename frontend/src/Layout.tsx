import React, { useState } from "react";
import AmbientBar from "./components/AmbientBar";

const NAV = [
  { key: "pipeline",   label: "Pipeline",   icon: "▦" },
  { key: "sourcing",   label: "Sourcing",   icon: "◎" },
  { key: "intake",     label: "Intake",     icon: "＋" },
  { key: "diagnostic", label: "Diagnostic", icon: "◈" },
  { key: "icprep",     label: "IC Prep",    icon: "◻" },
  { key: "execution",  label: "Execution",  icon: "▶" },
  { key: "portfolio",  label: "Portfolio",  icon: "◉" },
];

type Props = {
  page: string;
  onNav: (p: string) => void;
  userEmail?: string;
  onLogout: () => void;
  children: React.ReactNode;
  dealCount?: number;
};

export default function Layout({ page, onNav, userEmail, onLogout, children, dealCount = 0 }: Props) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{ display: "flex", height: "100vh", background: "#111", color: "#e2e2e2", fontFamily: "'ZenSerif', 'Inter', sans-serif", overflow: "hidden" }}>

      {/* SIDEBAR */}
      <aside style={{
        width: collapsed ? 48 : 200,
        background: "#111",
        borderRight: "1px solid #1e1e1e",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
        transition: "width 0.2s ease",
        overflow: "hidden",
      }}>

        {/* Logo + Toggle */}
        <div style={{ padding: collapsed ? "16px 8px" : "20px 16px 16px", display: "flex", alignItems: "center", justifyContent: collapsed ? "center" : "space-between" }}>
          {!collapsed && (
            <div onClick={() => onNav("pipeline")} style={{ cursor: "pointer" }}>
              <div style={{ fontFamily: "'ZenSerif', serif", fontSize: 15, fontWeight: 700, color: "#e2e2e2", letterSpacing: "0.02em" }}>Luska Capital</div>
              <div style={{ fontSize: 10, color: "#3a3a3a", marginTop: 2 }}>by COSMOS</div>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: "#4a4a4a", fontSize: 14, padding: 4,
              display: "flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
            }}
            onMouseEnter={e => (e.currentTarget.style.color = "#aaa")}
            onMouseLeave={e => (e.currentTarget.style.color = "#4a4a4a")}
            title={collapsed ? "사이드바 열기" : "사이드바 닫기"}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: collapsed ? "4px 4px" : "4px 8px" }}>
          {NAV.map(n => {
            const active = page === n.key;
            return (
              <button key={n.key} onClick={() => onNav(n.key)}
                title={collapsed ? n.label : undefined}
                style={{
                  width: "100%",
                  textAlign: collapsed ? "center" : "left",
                  padding: collapsed ? "8px 0" : "7px 10px",
                  borderRadius: 6, border: "none", cursor: "pointer",
                  background: active ? "#1e1e1e" : "transparent",
                  color: active ? "#e2e2e2" : "#5a5a5a",
                  fontSize: collapsed ? 16 : 13,
                  fontWeight: active ? 500 : 400,
                  fontFamily: "'ZenSerif', 'Inter', sans-serif",
                  marginBottom: 2, display: "flex",
                  alignItems: "center",
                  gap: collapsed ? 0 : 8,
                  justifyContent: collapsed ? "center" : "flex-start",
                  transition: "all 0.1s",
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                }}
                onMouseEnter={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "#1a1a1a"; (e.currentTarget as HTMLElement).style.color = "#aaa"; }}}
                onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "#5a5a5a"; }}}
              >
                <span style={{ fontSize: collapsed ? 14 : 11, opacity: 0.7 }}>{n.icon}</span>
                {!collapsed && <span>{n.label}</span>}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
        {!collapsed && (
          <div style={{ padding: "12px 16px 16px", borderTop: "1px solid #1a1a1a" }}>
            <button onClick={onLogout}
              style={{ fontSize: 11, color: "#4a4a4a", background: "none", border: "none", padding: 0, cursor: "pointer" }}
              onMouseEnter={e => (e.currentTarget.style.color = "#e2e2e2")}
              onMouseLeave={e => (e.currentTarget.style.color = "#4a4a4a")}
            >
              Sign out
            </button>
          </div>
        )}
      </aside>

      {/* MAIN */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <AmbientBar />
        <div style={{ flex: 1, overflow: "auto" }}>
          {children}
        </div>
      </div>
    </div>
  );
}
