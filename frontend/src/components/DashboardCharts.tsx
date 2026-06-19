import React, { useEffect, useState } from "react";
import API from "../api";

const C = {
  bg: "#0A0E14",
  surface: "#11161D",
  border: "#1E2630",
  text: "#E4E7EB",
  textMid: "#8B95A3",
  textDim: "#525C6B",
  amber: "#F0A93B",
  red: "#E5484D",
  green: "#2BC48A",
  blue: "#4C8DFF",
};

export default function DashboardCharts() {
  const [deals, setDeals] = useState<any[]>([]);
  const [actions, setActions] = useState<any>({ summary: { P0: 0, P1: 0, total: 0 } });
  const [dartSignals, setDartSignals] = useState<any>(null);
  const [newsSignals, setNewsSignals] = useState<any>(null);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  const fetchAll = async () => {
    try {
      const [d, a] = await Promise.all([API.get("/api/risk-book/deals"), API.get("/api/risk-book/today")]);
      setDeals(d.data); setActions(a.data); setLastUpdate(new Date());
    } catch {}
  };
  const fetchDart = async () => { try { const r = await API.get("/dart/scan?days=1"); setDartSignals(r.data); } catch {} };
  const fetchNews = async () => { try { const r = await API.get("/api/sourcing/naver-news"); setNewsSignals(r.data); } catch {} };

  useEffect(() => {
    fetchAll(); fetchDart(); fetchNews();
    const i1 = setInterval(fetchAll, 15000);
    const i2 = setInterval(fetchDart, 300000);
    const i3 = setInterval(fetchNews, 300000);
    return () => { clearInterval(i1); clearInterval(i2); clearInterval(i3); };
  }, []);

  const total = deals.length;
  const liveCount = deals.filter((d: any) => !d.is_test).length;
  const holdCount = deals.filter((d: any) => d.final_gate === "HOLD").length;
  const urgent = actions.summary?.P0 || 0;

  const dartHits = dartSignals?.hits || [];
  const p0 = dartHits.filter((h: any) => h.priority === "P0").length;
  const p1 = dartHits.filter((h: any) => h.priority === "P1").length;
  const newsTotal = newsSignals?.total ?? null;

  const Chip = ({ label, value, color }: { label: string; value: any; color?: string }) => (
    <div style={{ display: "flex", alignItems: "baseline", gap: 5 }}>
      <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em" }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 700, color: color || C.text, fontFamily: "'IBM Plex Mono', monospace" }}>{value}</span>
    </div>
  );

  return (
    <div style={{
      background: C.surface, borderBottom: `1px solid ${C.border}`,
      padding: "9px 18px", display: "flex", alignItems: "center", gap: 28,
      fontFamily: "'IBM Plex Mono', monospace", overflowX: "auto", height: 40,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.green }} />
        <span style={{ fontSize: 10, color: C.textMid, letterSpacing: "0.08em" }}>LIVE</span>
      </div>

      <div style={{ width: 1, height: 16, background: C.border }} />

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 9, fontWeight: 700, color: C.bg, background: C.red, padding: "1px 5px", borderRadius: 2 }}>HARD</span>
        <span style={{ fontSize: 12, color: p0 > 0 ? C.red : C.textMid, fontWeight: 700 }}>P0 {p0}</span>
        <span style={{ fontSize: 12, color: p1 > 0 ? C.amber : C.textMid, fontWeight: 700 }}>P1 {p1}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 9, fontWeight: 700, color: C.bg, background: C.blue, padding: "1px 5px", borderRadius: 2 }}>SOFT</span>
        <span style={{ fontSize: 12, color: C.textMid }}>{newsTotal === null ? "…" : `${newsTotal}건`}</span>
      </div>

      <div style={{ width: 1, height: 16, background: C.border }} />

      <Chip label="TOTAL" value={total} />
      <Chip label="LIVE" value={liveCount} color={C.green} />
      <Chip label="HOLD" value={holdCount} color={holdCount > 0 ? C.amber : C.textMid} />
      <Chip label="URGENT" value={urgent} color={urgent > 0 ? C.red : C.textMid} />

      <div style={{ flex: 1 }} />

      <span style={{ fontSize: 10, color: C.textDim }}>
        {lastUpdate.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} 업데이트
      </span>
    </div>
  );
}
