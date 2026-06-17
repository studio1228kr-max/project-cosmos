import React from "react";
import AmbientBar from "./components/AmbientBar";
import SidebarNav from "./components/Sidebar/SidebarNav";

type Props = {
  activePath: string;
  onNavigate: (path: string) => void;
  userEmail?: string;
  onLogout: () => void;
  children: React.ReactNode;
  dealCount?: number;
};

export default function Layout({ activePath, onNavigate, onLogout, children }: Props) {
  return (
    <div style={{ display: "flex", height: "100vh", background: "#111", color: "#e2e2e2", fontFamily: "'ZenSerif', 'Inter', sans-serif", overflow: "hidden" }}>

      {/* SIDEBAR */}
      <aside style={{ background: "#111", borderRight: "1px solid #222", display: "flex", flexDirection: "column", flexShrink: 0 }}>
        <SidebarNav activePath={activePath} onNavigate={onNavigate} />
        <div style={{ padding: "12px 16px 16px", borderTop: "1px solid #1e1e1e" }}>
          <button onClick={onLogout}
            style={{ fontSize: 12, color: "#6a6a6a", background: "none", border: "none", padding: 0, cursor: "pointer" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#e2e2e2")}
            onMouseLeave={e => (e.currentTarget.style.color = "#6a6a6a")}
          >
            Sign out
          </button>
        </div>
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
