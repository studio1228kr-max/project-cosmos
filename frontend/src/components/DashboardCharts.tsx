import React, { useEffect, useState, useRef } from "react";
import API from "../api";

const C = {
  bg: "#000", bg1: "#0A0A0A", bg2: "#111", border: "#222", border2: "#2A2A2A",
  gold: "#C9A84C", text: "#E8E8E8", text2: "#999", text3: "#555",
  green: "#00C87A", red: "#FF4444", amber: "#F59E0B", blue: "#4499FF",
};

const GATE_CFG: any = {
  HOLD:        { c: "#F59E0B", label: "HOLD" },
  RESTRUCTURE: { c: "#4499FF", label: "RESTR" },
  ADVANCE:     { c: "#00C87A", label: "ADV" },
  REJECT:      { c: "#FF4444", label: "REJ" },
};
const GATE_ORDER = ["HOLD", "RESTRUCTURE", "ADVANCE", "REJECT"];

function Ticker({ value, prev }: { value: number; prev: number }) {
  const up = value > prev;
  const same = value === prev;
  return (
    <span style={{ color: same ? C.text : up ? C.green : C.red, fontFamily: "'ZenSerif', 'IBM Plex Mono', monospace", fontWeight: 700 }}>
      {value}
    </span>
  );
}

export default function DashboardCharts() {
  const [deals, setDeals] = useState<any[]>([]);
  const [actions, setActions] = useState<any>({ summary: { P0: 0, P1: 0, P2: 0, total: 0 } });
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const prevDeals = useRef(0);
  const prevActions = useRef(0);

  const fetchData = async () => {
    try {
      const [d, a] = await Promise.all([API.get("/api/risk-book/deals"), API.get("/api/risk-book/today")]);
      prevDeals.current = deals.length;
      prevActions.current = actions.summary?.total || 0;
      setDeals(d.data); setActions(a.data); setLastUpdate(new Date());
    } catch {}
  };

  useEffect(() => { fetchData(); const iv = setInterval(fetchData, 10000); return () => clearInterval(iv); }, []);

  const gateCounts = GATE_ORDER.map(g => ({ g, count: deals.filter(d => d.final_gate === g).length }));

  const urgent = actions.summary?.P0 || 0;
  const total = deals.length;
  const liveCount = deals.filter(d => !d.is_test).length;

  const evidenceData = deals.slice(0, 6).map(d => {
    const name = (d.deal_name || "Unknown").slice(0, 14);
    const mandTotal = d.mandatory_total ?? 0;
    const mandDone = d.mandatory_done ?? 0;
    const pct = mandTotal > 0 ? Math.round((mandDone / mandTotal) * 100) : 0;
    return { name, mandDone, mandTotal, pct };
  });

  const row = (label: string, value: any, color = C.text) => (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "3px 0", borderBottom: "1px solid #111" }}>
      <span style={{ color: C.text3, fontSize: 10, letterSpacing: "0.05em" }}>{label}</span>
      <span style={{ color, fontSize: 11, fontWeight: 600, fontFamily: "'ZenSerif', 'IBM Plex Mono', monospace" }}>{value}</span>
    </div>
  );

  return (
    <div style={{ background: C.bg1, borderBottom: "1px solid #222", padding: "10px 16px", display: "flex", gap: 0, fontFamily: "'ZenSerif', 'IBM Plex Mono', monospace" }}>

      {/* BLOCK 1: DEAL METRICS */}
      <div style={{ minWidth: 160, paddingRight: 20, borderRight: "1px solid #222" }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6, textTransform: "uppercase" }}>DEAL METRICS</div>
        {row("TOTAL", <Ticker value={total} prev={prevDeals.current}/>, C.gold)}
        {row("URGENT", <Ticker value={urgent} prev={prevActions.current}/>, urgent > 0 ? C.red : C.text)}
        {row("LIVE", liveCount, C.blue)}
        {row("ACTIONS", actions.summary?.total || 0, C.amber)}
      </div>

      {/* BLOCK 2: GATE STATUS */}
      <div style={{ minWidth: 200, padding: "0 20px", borderRight: "1px solid #222" }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>GATE STATUS</div>
        {gateCounts.map(({ g, count }) => {
          const cfg = GATE_CFG[g];
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={g} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0" }}>
              <span style={{ color: cfg.c, fontSize: 9, width: 36, fontWeight: 600 }}>{cfg.label}</span>
              <div style={{ flex: 1, height: 2, background: "#1A1A1A" }}>
                <div style={{ width: `${pct}%`, height: "100%", background: cfg.c, transition: "width 0.5s" }}/>
              </div>
              <span style={{ color: C.text2, fontSize: 10, width: 20, textAlign: "right" }}>{count}</span>
            </div>
          );
        })}
      </div>

      {/* BLOCK 3: EVIDENCE */}
      <div style={{ minWidth: 260, padding: "0 20px", borderRight: "1px solid #222" }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>EVIDENCE COVERAGE (MANDATORY)</div>
        {evidenceData.map((d, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "2px 0" }}>
            <span style={{ color: C.text3, fontSize: 9, width: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.name}</span>
            <div style={{ flex: 1, height: 2, background: "#1A1A1A" }}>
              <div style={{ width: `${d.pct}%`, height: "100%", background: d.pct === 100 ? C.green : d.pct > 0 ? C.amber : "#333" }}/>
            </div>
            <span style={{ color: d.mandDone === d.mandTotal && d.mandTotal > 0 ? C.green : C.text2, fontSize: 10, width: 28, textAlign: "right" }}>{d.mandDone}/{d.mandTotal}</span>
          </div>
        ))}
      </div>

      {/* BLOCK 4: SYSTEM */}
      <div style={{ flex: 1, paddingLeft: 20 }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>SYSTEM</div>
        <div style={{ fontSize: 9, color: C.text3 }}>LAST UPDATE</div>
        <div style={{ fontSize: 11, color: C.text2, fontWeight: 600 }}>{lastUpdate.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</div>
        <div style={{ marginTop: 8, fontSize: 9, color: C.text3 }}>COSMOS DEAL OS</div>
        <div style={{ fontSize: 9, color: "#333" }}>v2.0 · LUSKA CAPITAL</div>
        <div style={{ marginTop: 8 }}>
          <span className="pulse-dot" style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: C.green, marginRight: 5, verticalAlign: "middle" }}/>
          <span style={{ fontSize: 9, color: C.green }}>LIVE</span>
        </div>
      </div>
    </div>
  );
}
