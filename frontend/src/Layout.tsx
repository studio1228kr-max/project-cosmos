import React, { useState } from "react";
import AmbientBar from "./components/AmbientBar";
import SidebarNav from "./components/Sidebar/SidebarNav";

type Props = {
  page: string;
  onNav: (p: string) => void;
  userEmail?: string;
  onLogout: () => void;
  children: React.ReactNode;
  dealCount?: number;
  onCollapsedChange?: (collapsed: boolean) => void;
};

export default function Layout({ page, onNav, userEmail, onLogout, children, dealCount = 0, onCollapsedChange }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    onCollapsedChange?.(next);
  };

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
            <div onClick={() => onNav("today")} style={{ cursor: "pointer" }}>
              <div style={{ fontFamily: "'ZenSerif', serif", fontSize: 15, fontWeight: 700, color: "#e2e2e2", letterSpacing: "0.02em" }}>Luska Capital</div>
              <div style={{ fontSize: 10, color: "#3a3a3a", marginTop: 2 }}>by COSMOS</div>
            </div>
          )}
          <button
            onClick={toggleCollapsed}
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
        <SidebarNav activePath={page} onNavigate={onNav} collapsed={collapsed} />

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
