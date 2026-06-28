import React, { useEffect, useState } from "react";
import Spinner from "../components/Spinner";
import API from "../api";

const C = {
  bg: "#0A0E14", surface: "#11161D", surface2: "#161C26", border: "#1E2630",
  text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B",
  amber: "#F0A93B", red: "#E5484D", green: "#2BC48A", blue: "#4C8DFF",
};

type FeedItem = { time: string; source: "DART" | "NAVER"; text: string; link?: string };

export default function MarketScan() {
  const [dartData, setDartData] = useState<any>(null);
  const [newsData, setNewsData] = useState<any>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [justActed, setJustActed] = useState<Set<number>>(new Set());

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [d, n, c] = await Promise.all([
        API.get("/dart/scan?days=1"),
        API.get("/api/sourcing/naver-news"),
        API.get("/api/sourcing/candidates"),
      ]);
      setDartData(d.data); setNewsData(n.data); setCandidates(c.data?.candidates || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchAll(); const i = setInterval(fetchAll, 60000); return () => clearInterval(i); }, []);

  const act = async (id: number, decision: string) => {
    try {
      await API.patch(`/api/sourcing/candidates/${id}/decision`, { decision });
      setCandidates(prev => prev.map(c => c.id === id ? { ...c, decision } : c));
      setJustActed(prev => new Set(prev).add(id));
      setTimeout(() => {
        setJustActed(prev => { const next = new Set(prev); next.delete(id); return next; });
      }, 5000);
    } catch { alert("처리 실패"); }
  };

  // Collection Feed 구성
  const feed: FeedItem[] = [];
  (dartData?.hits || []).forEach((h: any) => {
    feed.push({ time: h.disclosed_at || "", source: "DART", text: `[${h.priority}] ${h.corp_name} — ${h.report_title}`, link: h.dart_url });
  });
  (newsData?.items || []).slice(0, 15).forEach((it: any) => {
    feed.push({ time: it.pub_date || "", source: "NAVER", text: it.title, link: it.link });
  });
  feed.sort((a, b) => (b.time > a.time ? 1 : -1));

  const triageList = candidates.filter(c => ["PENDING", "MANUAL_REVIEW", "AUTO_CREATE_DEAL"].includes(c.decision) || justActed.has(c.id));

  const dartCount = dartData?.hits?.length || 0;
  const newsCount = newsData?.total || 0;
  const allHealthy = dartData !== null && newsData !== null;

  return (
    <div style={{ height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", display: "flex", flexDirection: "column" }}>

      {/* 상태 바 */}
      <div style={{ padding: "10px 18px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 14, fontFamily: "'IBM Plex Mono', monospace" }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: allHealthy ? C.green : C.amber }} />
        <span style={{ fontSize: 11, color: C.textMid }}>
          {allHealthy ? "핵심 피드 정상" : "피드 확인 중"} · 공시 {dartCount}건 · 뉴스 {newsCount}건 · triage 대기 {triageList.length}건
        </span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 10, color: C.textDim }}>Signal Room — 공시·뉴스 신호를 모아 triage하는 공간</span>
      </div>

      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>

        {/* 좌측: Collection Feed */}
        <div style={{ flex: 1.4, borderRight: `1px solid ${C.border}`, overflow: "auto", padding: "14px 18px" }}>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 10 }}>수집 피드 — 뭐가 들어왔나</div>
          {loading ? <Spinner /> :
            feed.length === 0 ? <div style={{ fontSize: 12, color: C.textDim }}>오늘 수집된 신호 없음</div> :
            feed.map((item, i) => (
              <a key={i} href={item.link} target="_blank" rel="noreferrer" style={{ textDecoration: "none" }}>
                <div style={{ display: "flex", gap: 10, padding: "7px 0", borderBottom: `1px solid ${C.border}`, alignItems: "baseline" }}>
                  <span style={{ fontSize: 9, fontWeight: 700, color: C.bg, background: item.source === "DART" ? C.red : C.blue, padding: "1px 5px", borderRadius: 2, flexShrink: 0 }}>
                    {item.source === "DART" ? "공시" : "뉴스"}
                  </span>
                  <span style={{ fontSize: 12, color: C.textMid, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.text}</span>
                </div>
              </a>
            ))}
        </div>

        {/* 우측: Triage 대상 */}
        <div style={{ flex: 1, overflow: "auto", padding: "14px 18px" }}>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 10 }}>Triage 대상 — 지금 판단할 신호</div>
          {triageList.length === 0 ? (
            <div style={{ fontSize: 12, color: C.textDim }}>처리할 신호 없음</div>
          ) : triageList.map((c: any) => {
            const done = justActed.has(c.id);
            return (
            <div key={c.id} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 14px", marginBottom: 10, opacity: done ? 0.6 : 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 13, fontWeight: 600 }}>{c.corp_name}</span>
                <span style={{ fontSize: 10, fontWeight: 700, color: c.priority === "P0" ? C.red : C.amber }}>{c.priority}</span>
              </div>
              <div style={{ fontSize: 11, color: C.textDim, marginBottom: 10 }}>{c.decision_explanation}</div>
              {done ? (
                <div style={{ fontSize: 11, color: c.decision === "PROMOTED" ? C.green : c.decision === "REJECTED" ? C.red : C.textMid }}>
                  {c.decision === "PROMOTED" ? `등록됨 — Intake에서 "${c.corp_name}" 으로 딜 생성하세요` : c.decision === "WATCHLIST" ? "보류 처리됨" : "폐기됨"}
                </div>
              ) : (
                <div style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => act(c.id, "PROMOTED")}
                    style={{ flex: 1, padding: "6px 0", background: C.green, border: "none", borderRadius: 4, color: C.bg, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
                    등록
                  </button>
                  <button onClick={() => act(c.id, "WATCHLIST")}
                    style={{ flex: 1, padding: "6px 0", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textMid, fontSize: 11, cursor: "pointer" }}>
                    보류
                  </button>
                  <button onClick={() => act(c.id, "REJECTED")}
                    style={{ flex: 1, padding: "6px 0", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.red, fontSize: 11, cursor: "pointer" }}>
                    폐기
                  </button>
                </div>
              )}
            </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
