import React, { useEffect, useState, useRef } from "react";
import API from "../api";

const C = {
  bg: "#000", bg1: "#0A0A0A", bg2: "#111", border: "#222",
  gold: "#C9A84C", text: "#E8E8E8", text2: "#999", text3: "#555",
  green: "#00C87A", red: "#FF4444", amber: "#F59E0B", blue: "#4499FF",
};

const GATE_CFG: any = {
  HOLD:        { c: "#F59E0B", label: "HOLD" },
  RESTRUCTURE: { c: "#4499FF", label: "RESTR" },
  ADVANCE:     { c: "#00C87A", label: "ADV" },
  REJECT:      { c: "#FF4444", label: "REJ" },
};

function Ticker({ value, prev }: { value: number; prev: number }) {
  const up = value > prev; const same = value === prev;
  return <span style={{ color: same ? C.text : up ? C.green : C.red, fontFamily: "'IBM Plex Mono', monospace", fontWeight: 700 }}>{value}</span>;
}

export default function DashboardCharts() {
  const [deals, setDeals] = useState<any[]>([]);
  const [actions, setActions] = useState<any>({ summary: { P0: 0, P1: 0, P2: 0, total: 0 } });
  const [dartSignals, setDartSignals] = useState<any>(null);
  const [newsSignals, setNewsSignals] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const prevDeals = useRef(0);
  const prevActions = useRef(0);

  const fetchData = async () => {
    try {
      const [d, a] = await Promise.all([
        API.get("/api/risk-book/deals"),
        API.get("/api/risk-book/today"),
      ]);
      prevDeals.current = deals.length;
      prevActions.current = actions.summary?.total || 0;
      setDeals(d.data); setActions(a.data); setLastUpdate(new Date());
    } catch {}
  };

  const fetchDart = async () => {
    try {
      const r = await API.get("/dart/scan?days=1");
      setDartSignals(r.data);
    } catch {}
  };

  const fetchNews = async () => {
    try {
      const r = await API.get("/api/sourcing/naver-news");
      setNewsSignals(r.data);
    } catch {}
  };

  useEffect(() => {
    fetchData(); fetchDart(); fetchNews();
    const iv1 = setInterval(fetchData, 10000);
    const iv2 = setInterval(fetchDart, 300000); // 5분
    const iv3 = setInterval(fetchNews, 300000); // 5분
    return () => { clearInterval(iv1); clearInterval(iv2); clearInterval(iv3); };
  }, []);

  const gateCounts = ["HOLD","RESTRUCTURE","ADVANCE","REJECT"].map(g => ({
    g, count: deals.filter(d => d.final_gate === g).length
  }));
  const urgent = actions.summary?.P0 || 0;
  const total = deals.length;
  const liveCount = deals.filter((d: any) => !d.is_test).length;
  const dartHits = dartSignals?.hits || [];
  const p0hits = dartHits.filter((h: any) => h.priority === "P0");
  const p1hits = dartHits.filter((h: any) => h.priority === "P1");

  return (
    <div style={{ background: C.bg1, borderBottom: `1px solid ${C.border}`, padding: "10px 16px", display: "flex", gap: 0, fontFamily: "'IBM Plex Mono', monospace", overflowX: "auto" }}>

      {/* BLOCK 1: DART 신호 */}
      <div style={{ minWidth: 220, paddingRight: 20, borderRight: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>DART EWS TODAY</div>
        {dartSignals === null ? (
          <div style={{ fontSize: 9, color: C.text3 }}>로딩 중...</div>
        ) : dartHits.length === 0 ? (
          <div style={{ fontSize: 9, color: C.text3 }}>신호 없음</div>
        ) : (
          <>
            <div style={{ display: "flex", gap: 12, marginBottom: 6 }}>
              <div>
                <span style={{ fontSize: 9, color: C.text3 }}>P0 </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: p0hits.length > 0 ? C.red : C.text3 }}>{p0hits.length}</span>
              </div>
              <div>
                <span style={{ fontSize: 9, color: C.text3 }}>P1 </span>
                <span style={{ fontSize: 13, fontWeight: 700, color: p1hits.length > 0 ? C.amber : C.text3 }}>{p1hits.length}</span>
              </div>
              <div>
                <span style={{ fontSize: 9, color: C.text3 }}>SCANNED </span>
                <span style={{ fontSize: 11, color: C.text2 }}>{dartSignals.total_scanned}</span>
              </div>
            </div>
            {dartHits.slice(0, 3).map((h: any, i: number) => (
              <div key={i} style={{ fontSize: 9, color: h.priority === "P0" ? C.red : C.amber, marginBottom: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>
                <a href={h.dart_url} target="_blank" rel="noreferrer" style={{ color: "inherit", textDecoration: "none" }}>
                  [{h.priority}] {h.corp_name}
                </a>
              </div>
            ))}
          </>
        )}
      </div>

      {/* BLOCK 2: DEAL METRICS */}
      <div style={{ minWidth: 140, padding: "0 20px", borderRight: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>DEAL METRICS</div>
        {[
          ["TOTAL", <Ticker value={total} prev={prevDeals.current}/>, C.gold],
          ["LIVE",  liveCount, C.green],
          ["URGENT", <Ticker value={urgent} prev={prevActions.current}/>, urgent > 0 ? C.red : C.text],
          ["ACTIONS", actions.summary?.total || 0, C.amber],
        ].map(([label, val, color]: any) => (
          <div key={label as string} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", borderBottom: `1px solid #111` }}>
            <span style={{ fontSize: 10, color: C.text3 }}>{label}</span>
            <span style={{ fontSize: 11, fontWeight: 600, color }}>{val}</span>
          </div>
        ))}
      </div>

      {/* BLOCK 3: GATE STATUS */}
      <div style={{ minWidth: 160, padding: "0 20px", borderRight: `1px solid ${C.border}` }}>
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
              <span style={{ color: C.text2, fontSize: 10, width: 16, textAlign: "right" }}>{count}</span>
            </div>
          );
        })}
      </div>

      {/* BLOCK 4: SYSTEM */}
      <div style={{ flex: 1, paddingLeft: 20 }}>
        <div style={{ fontSize: 9, color: C.text3, letterSpacing: "0.15em", marginBottom: 6 }}>SYSTEM</div>
        <div style={{ fontSize: 9, color: C.text3 }}>LAST UPDATE</div>
        <div style={{ fontSize: 11, color: C.text2, fontWeight: 600 }}>{lastUpdate.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</div>
        <div style={{ marginTop: 8, fontSize: 9, color: C.text3 }}>COSMOS DEAL OS</div>
        <div style={{ fontSize: 9, color: "#333" }}>v2.1 · LUSKA CAPITAL</div>
        <div style={{ marginTop: 8 }}>
          <span style={{ display: "inline-block", width: 5, height: 5, borderRadius: "50%", background: C.green, marginRight: 5, verticalAlign: "middle" }}/>
          <span style={{ fontSize: 9, color: C.green }}>LIVE</span>
        </div>
      </div>
    </div>
  );
}
