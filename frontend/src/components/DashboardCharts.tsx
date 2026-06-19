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

  const Chip = ({ label, value, color, title }: { label: string; value: any; color?: string; title?: string }) => (
    <div title={title} style={{ display: "flex", alignItems: "baseline", gap: 5, cursor: title ? "help" : "default" }}>
      <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.02em" }}>{label}</span>
      <span style={{ fontSize: 14, fontWeight: 700, color: color || C.text, fontFamily: "'IBM Plex Mono', monospace" }}>{value}</span>
    </div>
  );

  return (
    <div style={{
      background: C.surface, borderBottom: `1px solid ${C.border}`,
      padding: "9px 18px", display: "flex", alignItems: "center", gap: 26,
      fontFamily: "'IBM Plex Mono', monospace", overflowX: "auto", height: 40,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }} title="시스템이 정상 작동 중">
        <span style={{ width: 5, height: 5, borderRadius: "50%", background: C.green }} />
        <span style={{ fontSize: 10, color: C.textMid }}>운영중</span>
      </div>

      <div style={{ width: 1, height: 16, background: C.border }} />

      <div style={{ display: "flex", alignItems: "center", gap: 8 }} title="공시(DART) 기반 부실 신호 — 확정 정보">
        <span style={{ fontSize: 9, fontWeight: 700, color: C.bg, background: C.red, padding: "1px 5px", borderRadius: 2 }}>공시</span>
        <span style={{ fontSize: 12, color: p0 > 0 ? C.red : C.textMid, fontWeight: 700 }}>긴급 {p0}</span>
        <span style={{ fontSize: 12, color: p1 > 0 ? C.amber : C.textMid, fontWeight: 700 }}>주의 {p1}</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 8 }} title="뉴스 기반 선행 신호 — 참고용, 검증 필요">
        <span style={{ fontSize: 9, fontWeight: 700, color: C.bg, background: C.blue, padding: "1px 5px", borderRadius: 2 }}>뉴스</span>
        <span style={{ fontSize: 12, color: C.textMid }}>{newsTotal === null ? "…" : `${newsTotal}건`}</span>
      </div>

      <div style={{ width: 1, height: 16, background: C.border }} />

      <Chip label="전체 딜" value={total} title="등록된 딜 총 개수" />
      <Chip label="진행중" value={liveCount} color={C.green} title="테스트 제외, 실제 진행 중인 딜" />
      <Chip label="보류" value={holdCount} color={holdCount > 0 ? C.amber : C.textMid} title="HOLD 상태인 딜 — 조건 미충족" />
      <Chip label="긴급조치" value={urgent} color={urgent > 0 ? C.red : C.textMid} title="오늘 안에 확인해야 할 항목" />

      <div style={{ flex: 1 }} />

      <span style={{ fontSize: 10, color: C.textDim }}>
        {lastUpdate.toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })} 기준
      </span>
    </div>
  );
}
