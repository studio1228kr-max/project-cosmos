import React from "react";
import AmbientBar from "./components/AmbientBar";

const NAV = [
  { key: "pipeline", label: "Deal Pipeline" },
  { key: "today",    label: "Today" },
  { key: "market",   label: "Market Scan" },
  { key: "intake",   label: "New Intake" },
  { key: "riskbook", label: "Risk Book" },
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
  return (
    <div style={{ display: "flex", height: "100vh", background: "#111", color: "#e2e2e2", fontFamily: "'ZenSerif', 'Inter', sans-serif", overflow: "hidden" }}>

      {/* SIDEBAR */}
      <aside style={{ width: 200, background: "#111", borderRight: "1px solid #222", display: "flex", flexDirection: "column", flexShrink: 0 }}>

        {/* Logo */}
        <div style={{ padding: "20px 16px 16px" }}>
          <div onClick={() => onNav("today")} style={{ fontFamily: "'ZenSerif', serif", fontSize: 16, fontWeight: 700, color: "#e2e2e2", letterSpacing: "0.02em", cursor: "pointer" }}>Luska Capital</div>
          <div style={{ fontSize: 11, color: "#4a4a4a", marginTop: 2 }}>by COSMOS</div>
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: "4px 8px" }}>
          {NAV.map(n => {
            const active = page === n.key;
            return (
              <button key={n.key} onClick={() => onNav(n.key)}
                style={{
                  width: "100%", textAlign: "left", padding: "7px 10px",
                  borderRadius: 6, border: "none", cursor: "pointer",
                  background: active ? "#222" : "transparent",
                  color: active ? "#e2e2e2" : "#6a6a6a",
                  fontSize: 13, fontWeight: active ? 500 : 400,
                  fontFamily: "'ZenSerif', 'Inter', sans-serif",
                  marginBottom: 1, display: "block",
                  transition: "all 0.1s",
                }}
                onMouseEnter={e => { if (!active) (e.currentTarget as HTMLElement).style.background = "#1a1a1a"; (e.currentTarget as HTMLElement).style.color = "#aaa"; }}
                onMouseLeave={e => { if (!active) { (e.currentTarget as HTMLElement).style.background = "transparent"; (e.currentTarget as HTMLElement).style.color = "#6a6a6a"; }}}
              >
                {n.label}
              </button>
            );
          })}
        </nav>

        {/* Footer */}
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
