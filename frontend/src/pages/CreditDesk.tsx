import React, { useEffect, useState, useCallback } from "react";
import API from "../api";
import DealExecution from "./DealExecution";

// ── 디자인 토큰 ──────────────────────────────────────────────
const T = {
  bg: "#080C14",
  gold: "#C9A84C",
  text: "#E2E8F0",
  muted: "#4A6080",
  border: "#1A2332",
  dim: "#1A2235",            // 대기 dot
  critical: "#EF4444",
  watch: "#F59E0B",
  monitor: "#3B82F6",
  blue: "#4A90D9",           // HEPHAESTUS
  green: "#22C55E",          // KRONOS
  okDot: "#1A5A3A",
  warnDot: "#FF4D4D",
  font: "'Goldman Sans', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};

const KEYFRAMES = `
@keyframes ping-anim{0%{transform:scale(1);opacity:.8}100%{transform:scale(3);opacity:0}}
@keyframes pulse-glow{0%,100%{box-shadow:0 0 0px #4A90D9}50%{box-shadow:0 0 12px #4A90D9cc}}
@keyframes cdgglow{0%,100%{box-shadow:0 0 0 0 rgba(34,197,94,.5)}50%{box-shadow:0 0 0 5px rgba(34,197,94,0)}}
@keyframes cdsweep{0%{transform:translateX(-130%)}100%{transform:translateX(230%)}}
@keyframes ticker{0%{transform:translateX(100%)}100%{transform:translateX(-100%)}}
.alert-strip{height:24px;background:#0F0A06;border-bottom:1px solid #3A2A0A;overflow:hidden;white-space:nowrap;display:flex;align-items:center}
.alert-track{display:inline-flex;align-items:center;gap:32px;white-space:nowrap;animation:ticker 20s linear infinite}
`;

const URG: Record<string, { label: string; color: string }> = {
  CRITICAL_72H: { label: "CRITICAL", color: T.critical },
  WATCH_2W: { label: "WATCH", color: T.watch },
  MONITOR: { label: "MONITOR", color: T.monitor },
};
const urgCfg = (u?: string) => URG[u || ""] || { label: u || "—", color: T.muted };
const zoneColor = (z?: string) => (z === "DISTRESS" ? T.critical : z === "GREY" ? T.watch : z === "SAFE" ? T.monitor : T.muted);

const fmtTime = (s?: string | null) => {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return "—";
  return d.toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
};
const fmtRel = (s?: string | null) => {
  if (!s) return "—";
  const d = new Date(s);
  if (isNaN(d.getTime())) return "—";
  const m = Math.floor((Date.now() - d.getTime()) / 60000);
  if (m < 1) return "방금";
  if (m < 60) return `${m}분 전`;
  if (m < 1440) return `${Math.floor(m / 60)}시간 전`;
  return `${Math.floor(m / 1440)}일 전`;
};
const fmtMacro = (m: any): string | null => {
  if (!m || m.value == null) return null;
  const u = m.unit === "%" ? "%" : m.unit ? ` ${m.unit}` : "";
  return `${m.value}${u}`;
};

interface Card {
  id: number;
  urgency?: string;
  entity?: string;
  entity_sub?: string;
  signal_type?: string;
  zone?: string | null;
  score?: number | null;
  data_asof?: string | null;
}

const go = (p: string) => { window.location.href = p; };

// Morning Brief 경량 마크다운 렌더 (## 헤더 / **볼드** / - 불릿)
const renderInline = (text: string): React.ReactNode =>
  text.split(/(\*\*[^*]+\*\*)/g).map((p, i) =>
    p.startsWith("**") && p.endsWith("**")
      ? <span key={i} style={{ color: T.text }}>{p.slice(2, -2)}</span>
      : <React.Fragment key={i}>{p}</React.Fragment>);
const renderBrief = (text: string): React.ReactNode =>
  text.split(/\r?\n/).map((line, i) => {
    const t = line.trim();
    if (!t) return <div key={i} style={{ height: 6 }} />;
    const h = t.match(/^(#{1,3})\s+(.*)/);
    if (h) return <div key={i} style={{ fontSize: 13, color: T.gold, margin: "10px 0 4px" }}>{renderInline(h[2])}</div>;
    const b = t.match(/^[-*]\s+(.*)/);
    if (b) return <div key={i} style={{ display: "flex", gap: 6, padding: "2px 0" }}><span style={{ color: T.muted }}>·</span><span>{renderInline(b[1])}</span></div>;
    return <div key={i} style={{ padding: "2px 0" }}>{renderInline(t)}</div>;
  });

// ── 에이전트 인디케이터 칩 (D-style) ──
function Agent({ name, kind, state }: { name: string; kind: "hermes" | "hephaestus" | "kronos"; state: string }) {
  const active = state === "active" || state === "scanning";

  // HERMES active: 골드 칩 + ping (core 6 / ring 10)
  if (kind === "hermes" && active) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 10px", background: "#C9A84C11", border: "1px solid #C9A84C22", borderRadius: 4 }}>
        <span style={{ position: "relative", width: 10, height: 10, display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ position: "absolute", width: 10, height: 10, borderRadius: "50%", border: "1px solid #C9A84C", animation: "ping-anim 1.5s ease-out infinite" }} />
          <span style={{ width: 4, height: 4, borderRadius: "50%", background: "#C9A84C" }} />
        </span>
        <span style={{ fontSize: 11, color: "#C9A84C", letterSpacing: "0.04em" }}>{name}</span>
        {state === "scanning" && <span style={{ fontSize: 9, color: T.muted }}>scanning…</span>}
      </div>
    );
  }
  // HEPHAESTUS active: 블루 칩 + pulse glow (dot 10)
  if (kind === "hephaestus" && active) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 10px", background: "#4A90D911", border: "1px solid #4A90D922", borderRadius: 4 }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#4A90D9", animation: "pulse-glow 1.8s ease-in-out infinite" }} />
        <span style={{ fontSize: 11, color: "#4A90D9", letterSpacing: "0.04em" }}>{name}</span>
      </div>
    );
  }
  // KRONOS active(가용 시): 그린 칩
  if (kind === "kronos" && active) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 10px", background: "#22C55E11", border: "1px solid #22C55E22", borderRadius: 4 }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#22C55E", animation: "cdgglow 1.8s ease-in-out infinite" }} />
        <span style={{ fontSize: 11, color: "#22C55E", letterSpacing: "0.04em" }}>{name}</span>
      </div>
    );
  }
  // idle: 배경 없음, static dot 6px #1A2235, 텍스트 #2A3A52
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 10px" }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#1A2235", display: "inline-block" }} />
      <span style={{ fontSize: 11, color: "#2A3A52", letterSpacing: "0.04em" }}>{name}</span>
    </div>
  );
}

// ── 메인 ─────────────────────────────────────────────────────
export default function CreditDesk({ onLogout }: { onLogout?: () => void }) {
  const [cards, setCards] = useState<Card[]>([]);
  const [brief, setBrief] = useState<any>(null);
  const [deals, setDeals] = useState<any[]>([]);
  const [macro, setMacro] = useState<any>({});
  const [cosmosUp, setCosmosUp] = useState<boolean | null>(null);
  const [agents, setAgents] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("creditdesk");

  const load = useCallback(() => {
    Promise.all([
      API.get("/api/signals/room").then(r => r.data?.signals || []).catch(() => []),
      API.get("/api/brief/today").then(r => r.data?.brief || null).catch(() => null),
      API.get("/api/risk-book/deals").then(r => r.data || []).catch(() => []),
      API.get("/api/macro/latest").then(r => r.data?.macro || {}).catch(() => ({})),
      API.get("/health").then(() => true).catch(() => false),
    ]).then(([sig, br, dl, mc, up]) => {
      setCards(sig); setBrief(br); setDeals(dl); setMacro(mc); setCosmosUp(up); setLoading(false);
    });
  }, []);
  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i); }, [load]);

  // 에이전트 상태 — GET /api/system/status 5초 폴링 (없으면 데이터 흐름으로 추론)
  useEffect(() => {
    const poll = () => API.get("/api/system/status").then(r => setAgents(r.data || {})).catch(() => {});
    poll();
    const i = setInterval(poll, 5000);
    return () => clearInterval(i);
  }, []);

  const lastSignalAt = cards.map(c => c.data_asof).filter(Boolean).sort().slice(-1)[0] || null;
  const hermesUp = Boolean(brief?.model) || cards.length > 0;
  const lastScan = lastSignalAt || brief?.run_date || null;
  const cnt = (u: string) => cards.filter(c => c.urgency === u).length;
  const stats = brief?.stats || {};

  // 에이전트/시스템 상태
  const hermesState = agents.hermes || (hermesUp ? "active" : "idle");
  const hephState = agents.hephaestus || "idle";
  const kronosState = agents.kronos || "idle";
  const scanning = hermesState === "scanning";
  const cosmosOk = cosmosUp !== false;
  const hermesOk = hermesState !== "idle" || hermesUp;
  const hephOk = hephState !== "down";

  const sorted = [...cards].sort((a, b) => {
    const order: any = { CRITICAL_72H: 0, WATCH_2W: 1, MONITOR: 2 };
    const d = (order[a.urgency || ""] ?? 3) - (order[b.urgency || ""] ?? 3);
    return d !== 0 ? d : (b.score || 0) - (a.score || 0);
  });

  const holdDeals = deals.filter((d: any) => d.final_gate === "HOLD");
  const macroRows: [string, any][] = [
    ["기준금리", macro.BASE_RATE],
    ["크레딧 스프레드", macro.CREDIT_SPREAD],
    ["제조업 BSI", macro.BSI_MANUFACTURING],
  ];

  const ALERTS: { t: string; c: string }[] = [
    { t: "▲ RAS: 부동산 PF 익스포저 90% 도달 — 한도 점검 필요", c: T.watch },
    { t: "|", c: T.muted },
    { t: "● AML: STR 1건 자동 초안 생성됨 — 7페이지 확인", c: T.blue },
    { t: "|", c: T.muted },
    { t: "▲ Stress Test: 금리 +200bp — 포트폴리오 ECL +18%", c: T.watch },
    { t: "|", c: T.muted },
    { t: "● Compliance: FSC 정기보고 D-7", c: T.blue },
  ];

  const kpis = [
    { label: "SIGNALS", value: String(cards.length), color: cnt("CRITICAL_72H") > 0 ? T.critical : T.text },
    { label: "BASE RATE", value: fmtMacro(macro.BASE_RATE) || "—", color: macro.BASE_RATE?.value != null ? T.text : T.muted },
    { label: "SPREAD", value: fmtMacro(macro.CREDIT_SPREAD) || "—", color: macro.CREDIT_SPREAD?.value != null ? T.text : T.muted },
    { label: "BSI MFG", value: fmtMacro(macro.BSI_MANUFACTURING) || "—", color: macro.BSI_MANUFACTURING?.value != null ? T.text : T.muted },
    { label: "DEALS", value: String(deals.length), color: T.text },
    { label: "포트폴리오", value: "—", color: T.muted },
  ];

  const TABS = [
    { id: "creditdesk", label: "Credit Desk" },
    { id: "deals", label: "Deals" },
    { id: "dd", label: "DD" },
    { id: "portfolio", label: "Portfolio" },
  ];

  const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };

  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", display: "flex", flexDirection: "column", fontFamily: T.font, fontWeight: 400, fontSize: 12 }}>
      <style>{KEYFRAMES}</style>

      {/* ── 1. 탑바 (기존 유지) ── */}
      <div style={{ height: 54, flexShrink: 0, borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", padding: "0 20px", position: "sticky", top: 0, background: T.bg, zIndex: 20 }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
          <img src="/logo.png" width={24} height={24} alt="Cosmos" style={{ filter: "invert(1) sepia(1) saturate(2) hue-rotate(5deg) brightness(0.9)" }} />
          <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: "0.06em", color: T.gold }}>COSMOS</span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {TABS.map(t => {
            const active = t.id === activeTab;
            return (
              <div key={t.id} onClick={() => setActiveTab(t.id)}
                style={{ padding: "8px 16px", cursor: "pointer", fontSize: 13, color: active ? T.text : T.muted, borderBottom: active ? `2px solid ${T.gold}` : "2px solid transparent" }}>
                {t.label}
              </div>
            );
          })}
        </div>
        <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 12 }}>
          <button onClick={() => go("/app?nav=intake")}
            onMouseEnter={e => (e.currentTarget.style.background = "#C9A84C11")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            style={{ padding: "8px 15px", background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4, fontSize: 12, cursor: "pointer", fontFamily: T.font }}>+ New Deal</button>
          <span onClick={onLogout} title="로그아웃" style={{ fontSize: 17, color: T.muted, cursor: "pointer", lineHeight: 1 }}>⏻</span>
        </div>
      </div>

      {/* ── Alert Strip (최상단 티커) ── */}
      <div className="alert-strip">
        <div className="alert-track">
          {ALERTS.map((a, i) => (
            <span key={i} style={{ fontSize: 11, color: a.c }}>{a.t}</span>
          ))}
        </div>
      </div>

      {/* ── 에이전트 상태 바 ── */}
      <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "8px 20px", borderBottom: `1px solid ${T.border}` }}>
        <span style={labelStyle}>Agents</span>
        <Agent name="HERMES" kind="hermes" state={hermesState} />
        <Agent name="HEPHAESTUS" kind="hephaestus" state={hephState} />
        <Agent name="KRONOS" kind="kronos" state={kronosState} />
        <span style={{ marginLeft: "auto", fontSize: 9, color: "#2A3A52" }}>Last sync · {fmtRel(lastScan)}</span>
      </div>

      {/* ── Credit Desk 탭 ── */}
      {activeTab === "creditdesk" && (
        <>
          {/* 3. KPI 바 (한 줄, 32px) */}
          <div style={{ height: 32, flexShrink: 0, display: "flex", alignItems: "stretch", borderBottom: `1px solid ${T.border}`, overflowX: "auto" }}>
            {kpis.map(k => (
              <span key={k.label} style={{ display: "inline-flex", alignItems: "center", gap: 6, whiteSpace: "nowrap", flexShrink: 0, padding: "0 14px", borderRight: "1px solid #0F1824" }}>
                <span style={{ fontSize: 10, color: T.muted, whiteSpace: "nowrap" }}>{k.label}</span>
                <span style={{ fontFamily: T.mono, color: k.color, whiteSpace: "nowrap" }}>{k.value}</span>
              </span>
            ))}
            <span style={{ marginLeft: "auto", alignSelf: "center", fontSize: 10, color: T.muted, whiteSpace: "nowrap", flexShrink: 0, paddingRight: 14 }}>auto-refresh 60s</span>
          </div>

          {/* 4. Signal Room 테이블 */}
          <div style={{ position: "relative", overflow: "hidden", borderBottom: `1px solid ${T.border}` }}>
            {scanning && (
              <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 1 }}>
                <div style={{ position: "absolute", top: 0, bottom: 0, width: "30%", background: "linear-gradient(90deg, transparent, rgba(201,168,76,0.12), transparent)", animation: "cdsweep 4s linear infinite" }} />
              </div>
            )}
            <div style={{ padding: "10px 20px 4px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={labelStyle}>Signal Room</span>
              <span style={{ fontSize: 10, color: T.muted }}>{cards.length} signals</span>
            </div>

            {loading ? (
              <div style={{ padding: "48px 20px", textAlign: "center", color: T.muted, fontSize: 12 }}>데이터 불러오는 중…</div>
            ) : sorted.length === 0 ? (
              <div style={{ padding: "56px 20px", textAlign: "center" }}>
                <div style={{ color: T.text, fontSize: 13 }}>신호 없음</div>
                <div style={{ color: T.muted, fontSize: 11, marginTop: 6 }}>HERMES가 첫 수집을 완료하면 자동으로 채워집니다.</div>
              </div>
            ) : (
              <div style={{ overflowX: "auto", padding: "0 8px 8px" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ color: T.muted, textAlign: "left" }}>
                      {["Urgency", "Entity", "Signal", "Zone", "Score", "As of"].map((h, i) => (
                        <th key={i} style={{ padding: "7px 12px", fontSize: 10, fontWeight: 400, letterSpacing: "0.06em", textTransform: "uppercase", borderBottom: `1px solid ${T.border}`, whiteSpace: "nowrap" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sorted.map(c => {
                      const u = urgCfg(c.urgency);
                      const score = c.score || 0;
                      return (
                        <tr key={c.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                          <td style={{ padding: "9px 12px" }}>
                            <span style={{ fontSize: 10, color: u.color, background: `${u.color}1A`, border: `1px solid ${u.color}44`, borderRadius: 3, padding: "2px 7px", whiteSpace: "nowrap" }}>{u.label}</span>
                          </td>
                          <td style={{ padding: "9px 12px", minWidth: 160 }}>
                            <div style={{ color: T.text }}>{c.entity || "—"}</div>
                            <div style={{ fontFamily: T.mono, color: T.muted, fontSize: 10, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 220 }}>{c.entity_sub || "—"}</div>
                          </td>
                          <td style={{ padding: "9px 12px", color: T.text, whiteSpace: "nowrap" }}>{c.signal_type || "—"}</td>
                          <td style={{ padding: "9px 12px" }}>
                            {c.zone ? <span style={{ fontSize: 10, color: zoneColor(c.zone), background: `${zoneColor(c.zone)}1A`, border: `1px solid ${zoneColor(c.zone)}44`, borderRadius: 3, padding: "2px 7px", whiteSpace: "nowrap" }}>{c.zone}</span> : <span style={{ color: T.muted }}>—</span>}
                          </td>
                          <td style={{ padding: "9px 12px", minWidth: 110 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <span style={{ fontFamily: T.mono, color: u.color, minWidth: 22 }}>{score}</span>
                              <div style={{ flex: 1, height: 3, background: T.border, borderRadius: 2, overflow: "hidden", minWidth: 48 }}>
                                <div style={{ width: `${Math.min(100, score)}%`, height: "100%", background: u.color }} />
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: "9px 12px", fontFamily: T.mono, fontSize: 11, color: T.muted, whiteSpace: "nowrap" }}>{fmtTime(c.data_asof)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* 5. 하단 — Morning Brief (좌) + Macro Monitor (우) */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 240px" }}>
            <section style={{ padding: "14px 20px", borderRight: `1px solid ${T.border}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <span style={{ ...labelStyle, borderLeft: `2px solid ${T.gold}`, paddingLeft: 8 }}>Morning Brief</span>
                {brief?.run_date && <span style={{ fontSize: 10, color: T.muted }}>{brief.run_date}</span>}
              </div>
              {brief?.brief_text ? (
                <div style={{ fontSize: 12, color: T.text, lineHeight: 1.7, maxHeight: 220, overflow: "auto" }}>{renderBrief(brief.brief_text)}</div>
              ) : (
                <div style={{ fontSize: 12, color: T.muted }}>오늘 브리핑 없음 — 매일 04:00 KST 자동 생성됩니다.</div>
              )}
              {brief && (
                <div style={{ display: "flex", gap: 12, marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.border}`, fontFamily: T.mono, fontSize: 10, color: T.muted }}>
                  <span style={{ color: T.critical }}>C {stats.critical_count ?? brief.critical_count ?? 0}</span>
                  <span style={{ color: T.watch }}>W {stats.watch_count ?? brief.watch_count ?? 0}</span>
                  <span style={{ color: T.monitor }}>M {stats.monitor_count ?? brief.monitor_count ?? 0}</span>
                  {brief.model && <span style={{ marginLeft: "auto" }}>{brief.model}</span>}
                </div>
              )}
            </section>
            <section style={{ padding: "14px 20px" }}>
              <div style={{ marginBottom: 10 }}><span style={labelStyle}>Macro Monitor</span></div>
              {macroRows.map(([k, m]) => {
                const v = fmtMacro(m);
                return (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: `1px solid ${T.border}` }}>
                    <div>
                      <div style={{ color: T.text }}>{k}</div>
                      <div style={{ fontSize: 10, color: T.muted }}>{m?.as_of || "연동 대기"}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontFamily: T.mono, color: v ? T.text : T.muted }}>{v || "—"}</span>
                      {m?.delta_mom != null && <div style={{ fontFamily: T.mono, fontSize: 10, color: m.delta_mom >= 0 ? T.green : T.critical }}>{m.delta_mom >= 0 ? "▲" : "▼"} {Math.abs(m.delta_mom)}</div>}
                    </div>
                  </div>
                );
              })}
            </section>
          </div>
        </>
      )}

      {/* ── Deals 탭 — Deal Execution ── */}
      {activeTab === "deals" && <DealExecution deals={deals} />}

      {/* ── DD 탭 ── */}
      {activeTab === "dd" && (
        <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}` }}>
          <div style={{ marginBottom: 10 }}><span style={labelStyle}>Covenant Monitor</span></div>
          {holdDeals.length === 0 ? (
            <div style={{ fontSize: 12, color: T.muted }}>위반/조건 미달 없음</div>
          ) : holdDeals.map((d: any) => (
            <div key={d.deal_code} style={{ padding: "8px 0", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ color: T.text }}>{d.deal_name}</span>
                <span style={{ fontSize: 10, color: T.watch, border: `1px solid ${T.watch}44`, borderRadius: 3, padding: "2px 7px" }}>HOLD</span>
              </div>
              {(d.hold_reasons || [])[0] && <div style={{ fontSize: 11, color: T.muted, marginTop: 3, borderLeft: `2px solid ${T.watch}`, paddingLeft: 6 }}>{(d.hold_reasons || [])[0]}</div>}
            </div>
          ))}
        </div>
      )}

      {/* ── Portfolio 탭 ── */}
      {activeTab === "portfolio" && (
        <div style={{ padding: "56px 20px", textAlign: "center", borderBottom: `1px solid ${T.border}` }}>
          <div style={{ fontSize: 13, color: T.text }}>Risk Monitor</div>
          <div style={{ fontSize: 12, color: T.muted, marginTop: 8 }}>포트폴리오 리스크 데이터 연동 대기 — 클로징된 딜이 편입되면 표시됩니다.</div>
        </div>
      )}

      {/* ── 6. 푸터 — 시스템 상태 ── */}
      <div style={{ marginTop: "auto", height: 22, flexShrink: 0, display: "flex", alignItems: "center", gap: 16, padding: "0 20px", borderTop: `1px solid ${T.border}`, fontSize: 10, color: T.muted }}>
        {([["COSMOS", cosmosOk], ["HERMES", hermesOk], ["HEPHAESTUS", hephOk]] as [string, boolean][]).map(([n, ok]) => (
          <span key={n} style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: ok ? T.okDot : T.warnDot }} />{n}
          </span>
        ))}
        <span style={{ marginLeft: "auto" }}>LuskaCapitalManagement · cosmos.luskacapital.com</span>
      </div>
    </div>
  );
}
