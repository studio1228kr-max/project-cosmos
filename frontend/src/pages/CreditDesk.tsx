import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 토큰 ──────────────────────────────────────────────
// 골드(#C9A84C)는 4곳만: 로고 / 활성 사이드바 border / Primary 버튼 / Morning Brief border-left
const T = {
  bg: "#080C14",
  card: "#0D1421",
  cardHi: "#0E1420",
  gold: "#C9A84C",
  text: "#E2E8F0",
  muted: "#4A6080",
  border: "#1A2332",
  critical: "#EF4444",
  watch: "#F59E0B",
  monitor: "#3B82F6",
  green: "#22C55E",
  font: "'Satoshi', sans-serif",            // 본문 전체
  mono: "'IBM Plex Mono', ui-monospace, monospace", // 숫자/코드값만
};

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
  z_score?: number | null;
  icr?: number | null;
  zone?: string | null;
  score?: number | null;
  suggested_deal_type?: string | null;
  thesis?: string | null;
  data_asof?: string | null;
}

const go = (p: string) => { window.location.href = p; };

// ── 빌딩블록 ─────────────────────────────────────────────────
const Panel: React.FC<{ title: string; right?: React.ReactNode; goldLeft?: boolean; children: React.ReactNode; style?: React.CSSProperties; id?: string }> = ({ title, right, goldLeft, children, style, id }) => (
  <div id={id} style={{
    background: T.card, border: `1px solid ${T.border}`,
    borderLeft: goldLeft ? `3px solid ${T.gold}` : `1px solid ${T.border}`,
    borderRadius: 4, padding: "12px 14px", display: "flex", flexDirection: "column", minWidth: 0, ...style,
  }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
      <span style={{ fontSize: 10, fontWeight: 600, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>{title}</span>
      {right}
    </div>
    {children}
  </div>
);

const Tag: React.FC<{ color: string; children: React.ReactNode }> = ({ color, children }) => (
  <span style={{ fontSize: 9, fontWeight: 600, color, background: `${color}1A`, border: `1px solid ${color}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.04em", whiteSpace: "nowrap" }}>{children}</span>
);

const Sk: React.FC<{ w?: number | string; h: number; r?: number; style?: React.CSSProperties }> = ({ w = "100%", h, r = 4, style }) => (
  <div style={{ width: w, height: h, borderRadius: r, background: T.cardHi, animation: "cdpulse 1.3s ease-in-out infinite", ...style }} />
);

// ── 스켈레톤 화면 ────────────────────────────────────────────
function Skeleton() {
  return (
    <div style={{ flex: 1, minWidth: 0, padding: "16px 20px 44px", display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 4, padding: "11px 13px" }}>
            <Sk w={70} h={8} /><Sk w={48} h={22} style={{ marginTop: 8 }} /><Sk w={40} h={8} style={{ marginTop: 8 }} />
          </div>
        ))}
      </div>
      <div style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 4, padding: "12px 14px" }}>
        <Sk w={120} h={9} style={{ marginBottom: 14 }} />
        {Array.from({ length: 5 }).map((_, i) => <Sk key={i} h={14} style={{ marginBottom: 9 }} />)}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.3fr", gap: 12 }}>
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{ background: T.card, border: `1px solid ${T.border}`, borderRadius: 4, padding: "12px 14px" }}>
            <Sk w={90} h={9} style={{ marginBottom: 12 }} />
            {Array.from({ length: 4 }).map((__, j) => <Sk key={j} h={12} style={{ marginBottom: 8 }} />)}
          </div>
        ))}
      </div>
    </div>
  );
}

const KEYFRAMES = "@keyframes cdpulse{0%,100%{opacity:0.5}50%{opacity:1}}";

// ── 메인 ─────────────────────────────────────────────────────
export default function CreditDesk({ onLogout }: { onLogout?: () => void }) {
  const [cards, setCards] = useState<Card[]>([]);
  const [brief, setBrief] = useState<any>(null);
  const [deals, setDeals] = useState<any[]>([]);
  const [macro, setMacro] = useState<any>({});
  const [cosmosUp, setCosmosUp] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeNav, setActiveNav] = useState("creditdesk");

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

  // HERMES 상태: COSMOS에 별도 프록시가 없어 데이터 흐름으로 추론
  const lastSignalAt = cards.map(c => c.data_asof).filter(Boolean).sort().slice(-1)[0] || null;
  const hermesUp = Boolean(brief?.model) || cards.length > 0;
  const lastScan = lastSignalAt || brief?.run_date || null;

  const cnt = (u: string) => cards.filter(c => c.urgency === u).length;
  const stats = brief?.stats || {};

  const metricVal = (m: any) => fmtMacro(m);
  const metrics = [
    { label: "ACTIVE SIGNALS", value: String(cards.length), sub: `${cnt("CRITICAL_72H")} critical`, color: cnt("CRITICAL_72H") > 0 ? T.critical : T.text, top: "#EF4444" },
    { label: "BASE RATE", value: metricVal(macro.BASE_RATE) || "—", sub: macro.BASE_RATE?.as_of || "연동 대기", color: macro.BASE_RATE?.value != null ? T.text : T.muted, top: "#10B981" },
    { label: "CREDIT SPREAD", value: metricVal(macro.CREDIT_SPREAD) || "—", sub: macro.CREDIT_SPREAD?.as_of || "연동 대기", color: macro.CREDIT_SPREAD?.value != null ? T.text : T.muted, top: "#C9A84C" },
    { label: "BSI MFG", value: metricVal(macro.BSI_MANUFACTURING) || "—", sub: macro.BSI_MANUFACTURING?.as_of || "연동 대기", color: macro.BSI_MANUFACTURING?.value != null ? T.text : T.muted, top: "#F59E0B" },
    { label: "DEALS", value: String(deals.length), sub: `${deals.filter((d: any) => d.final_gate === "HOLD").length} hold`, color: T.text, top: "#3B82F6" },
    { label: "LAST SCAN", value: fmtRel(lastScan), sub: hermesUp ? "HERMES live" : "대기", color: hermesUp ? T.monitor : T.muted, top: "#4A5568" },
  ];

  const holdDeals = deals.filter((d: any) => d.final_gate === "HOLD");
  const macroRows: [string, string, any][] = [
    ["기준금리", "Base Rate", macro.BASE_RATE],
    ["크레딧 스프레드", "Credit Spread", macro.CREDIT_SPREAD],
    ["제조업 BSI", "BSI Manufacturing", macro.BSI_MANUFACTURING],
  ];

  const NAV: { id: string; label: string; items: { id: string; label: string; scroll?: string; to?: string }[] }[] = [
    { id: "today", label: "TODAY", items: [
      { id: "creditdesk", label: "Credit Desk", scroll: "cd-top" },
      { id: "triage", label: "Morning Triage", scroll: "cd-brief" },
      { id: "signalroom", label: "Signal Room", scroll: "cd-signals" },
    ] },
    { id: "deal", label: "DEAL", items: [
      { id: "pipeline", label: "Pipeline", to: "/" },
      { id: "register", label: "Register", to: "/" },
    ] },
    { id: "dd", label: "DUE DILIGENCE", items: [
      { id: "sdd", label: "SDD", to: "/" },
      { id: "icmemo", label: "IC Memo", to: "/" },
      { id: "covenant", label: "Covenant Monitor", scroll: "cd-covenant" },
    ] },
    { id: "portfolio", label: "PORTFOLIO", items: [
      { id: "risk", label: "Risk Monitor", to: "/" },
    ] },
  ];
  const handleNav = (item: { id: string; scroll?: string; to?: string }) => {
    setActiveNav(item.id);
    if (item.scroll) document.getElementById(item.scroll)?.scrollIntoView({ behavior: "smooth", block: "start" });
    else if (item.to) go(item.to);
  };

  return (
    <div style={{ background: T.bg, color: T.text, minHeight: "100vh", display: "flex", fontFamily: T.font, fontWeight: 450, fontSize: 12 }}>
      <style>{KEYFRAMES}</style>

      {/* ── 사이드바 172px ── */}
      <div style={{ width: 172, flexShrink: 0, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", position: "sticky", top: 0, height: "100vh" }}>
        <div style={{ padding: "18px 16px 22px" }}>
          <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: "0.12em", color: T.gold }}>COSMOS</div>
          <div style={{ fontSize: 9, color: T.muted, letterSpacing: "0.18em", marginTop: 2 }}>CREDIT DESK</div>
        </div>
        <div style={{ flex: 1, overflow: "auto" }}>
          {NAV.map(group => (
            <div key={group.id} style={{ marginBottom: 6 }}>
              <div style={{ padding: "12px 16px 4px", fontSize: 9, fontWeight: 600, color: T.muted, letterSpacing: "0.12em" }}>{group.label}</div>
              {group.items.map(item => {
                const active = item.id === activeNav;
                return (
                  <div key={item.id}
                    onClick={() => handleNav(item)}
                    style={{
                      padding: "7px 16px 7px 22px", cursor: "pointer", fontSize: 12, fontWeight: 500,
                      color: active ? T.text : T.muted,
                      borderLeft: active ? `2px solid ${T.gold}` : "2px solid transparent",
                      background: active ? T.cardHi : "transparent",
                    }}>
                    {item.label}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        <div onClick={onLogout} style={{ padding: "12px 16px", fontSize: 11, color: T.muted, cursor: "pointer", borderTop: `1px solid ${T.border}` }}>↩ Logout</div>
      </div>

      {/* ── 메인 ── */}
      {loading ? <Skeleton /> : (
        <div id="cd-top" style={{ flex: 1, minWidth: 0, padding: "16px 20px 44px", display: "flex", flexDirection: "column", gap: 14 }}>

          {/* 상단: 메트릭 6 */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 10 }}>
            {metrics.map(m => (
              <div key={m.label} style={{ background: T.card, border: "none", borderTop: `2px solid ${m.top}`, borderRadius: 4, padding: "11px 13px" }}>
                <div style={{ fontSize: 9, color: T.muted, letterSpacing: "0.08em" }}>{m.label}</div>
                <div style={{ fontFamily: T.mono, fontSize: 22, fontWeight: 700, color: m.color, marginTop: 5, lineHeight: 1 }}>{m.value}</div>
                <div style={{ fontSize: 9, color: T.muted, marginTop: 5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{m.sub}</div>
              </div>
            ))}
          </div>

          {/* 중단: Signal Room 테이블 */}
          <Panel id="cd-signals" title="Signal Room" right={<span style={{ fontSize: 9, color: T.muted }}>{cards.length} signals · auto-refresh 60s</span>}>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                <thead>
                  <tr style={{ color: T.muted, fontSize: 9, letterSpacing: "0.06em", textAlign: "left" }}>
                    {["URGENCY", "ENTITY", "SIGNAL", "Z-SCORE", "ZONE", "ICR", "DEAL TYPE", "SCORE", "AS OF", ""].map((h, i) => (
                      <th key={i} style={{ padding: "6px 10px", fontWeight: 500, borderBottom: `1px solid ${T.border}`, whiteSpace: "nowrap" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cards.length === 0 && (
                    <tr><td colSpan={10} style={{ padding: "22px 10px", color: T.muted, textAlign: "center" }}>활성 신호 없음</td></tr>
                  )}
                  {cards.map(c => {
                    const u = urgCfg(c.urgency);
                    const score = c.score || 0;
                    return (
                      <tr key={c.id} style={{ borderBottom: `1px solid ${T.border}` }}>
                        <td style={{ padding: "9px 10px" }}><Tag color={u.color}>{u.label}</Tag></td>
                        <td style={{ padding: "9px 10px", minWidth: 150 }}>
                          <div style={{ fontFamily: T.font, fontWeight: 600, color: T.text }}>{c.entity || "—"}</div>
                          <div style={{ fontFamily: T.mono, color: T.muted, fontSize: 9, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>{c.entity_sub || "—"}</div>
                        </td>
                        <td style={{ padding: "9px 10px", color: T.text, whiteSpace: "nowrap" }}>{c.signal_type || "—"}</td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontWeight: 700, color: c.z_score != null ? T.text : T.muted }}>{c.z_score != null ? Number(c.z_score).toFixed(2) : "—"}</td>
                        <td style={{ padding: "9px 10px" }}>{c.zone ? <Tag color={zoneColor(c.zone)}>{c.zone}</Tag> : <span style={{ color: T.muted }}>—</span>}</td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, fontWeight: 700, color: c.icr != null ? T.text : T.muted }}>{c.icr != null ? `${Number(c.icr).toFixed(2)}x` : "—"}</td>
                        <td style={{ padding: "9px 10px", color: T.text, whiteSpace: "nowrap" }}>{c.suggested_deal_type || "—"}</td>
                        <td style={{ padding: "9px 10px", minWidth: 92 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                            <span style={{ fontFamily: T.mono, color: u.color, fontWeight: 700, minWidth: 22 }}>{score}</span>
                            <div style={{ flex: 1, height: 4, background: T.border, borderRadius: 2, overflow: "hidden", minWidth: 40 }}>
                              <div style={{ width: `${Math.min(100, score)}%`, height: "100%", background: u.color }} />
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: "9px 10px", fontFamily: T.mono, color: T.muted, whiteSpace: "nowrap" }}>{fmtTime(c.data_asof)}</td>
                        <td style={{ padding: "9px 10px" }}>
                          <span onClick={() => go("/")} style={{ color: T.monitor, cursor: "pointer", whiteSpace: "nowrap" }}>처리 →</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* 하단: 3컬럼 + 우측 패널 */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1.3fr", gap: 12, alignItems: "start" }}>

            {/* Deal Pipeline */}
            <Panel title="Deal Pipeline">
              <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 10 }}>
                <span style={{ fontFamily: T.mono, fontSize: 24, fontWeight: 700, color: T.text }}>{deals.length}</span>
                <span style={{ fontSize: 10, color: T.muted }}>active deals</span>
              </div>
              {deals.length === 0 ? (
                <div style={{ fontSize: 11, color: T.muted }}>등록된 딜 없음</div>
              ) : deals.slice(0, 5).map((d: any) => (
                <div key={d.deal_code} onClick={() => go("/")} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: `1px solid ${T.border}`, cursor: "pointer" }}>
                  <span style={{ color: T.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 120 }}>{d.deal_name}</span>
                  <Tag color={d.final_gate === "HOLD" ? T.watch : d.final_gate === "PASS" ? T.monitor : T.muted}>{d.final_gate || "—"}</Tag>
                </div>
              ))}
            </Panel>

            {/* Covenant Monitor — HOLD 딜의 차단 사유 */}
            <Panel id="cd-covenant" title="Covenant Monitor">
              {holdDeals.length === 0 ? (
                <div style={{ fontSize: 11, color: T.muted }}>위반/조건 미달 없음</div>
              ) : holdDeals.slice(0, 5).map((d: any) => (
                <div key={d.deal_code} style={{ padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ color: T.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 110 }}>{d.deal_name}</span>
                    <Tag color={T.watch}>HOLD</Tag>
                  </div>
                  {(d.hold_reasons || [])[0] && <div style={{ fontSize: 9, color: T.muted, marginTop: 3, borderLeft: `2px solid ${T.watch}`, paddingLeft: 6 }}>{(d.hold_reasons || [])[0]}</div>}
                </div>
              ))}
            </Panel>

            {/* Macro Monitor — normalized_macro_series 실데이터 */}
            <Panel title="Macro Monitor">
              {macroRows.map(([k, sub, m]) => {
                const v = fmtMacro(m);
                return (
                  <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: `1px solid ${T.border}` }}>
                    <div>
                      <div style={{ color: T.text }}>{k}</div>
                      <div style={{ fontSize: 9, color: T.muted }}>{m?.as_of || sub}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontFamily: T.mono, fontWeight: 700, color: v ? T.text : T.muted }}>{v || "—"}</span>
                      {m?.delta_mom != null && <div style={{ fontFamily: T.mono, fontSize: 9, color: m.delta_mom >= 0 ? T.green : T.critical }}>{m.delta_mom >= 0 ? "▲" : "▼"} {Math.abs(m.delta_mom)}</div>}
                    </div>
                  </div>
                );
              })}
              <div style={{ fontSize: 9, color: T.muted, marginTop: 8 }}>ECOS 일간 적재 · 미적재 지표는 연동 대기</div>
            </Panel>

            {/* 우측 패널: Morning Brief + Quick Actions */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <Panel id="cd-brief" title="Morning Brief" goldLeft right={brief?.run_date ? <span style={{ fontSize: 9, color: T.muted }}>{brief.run_date}</span> : undefined}>
                {brief?.brief_text ? (
                  <div style={{ fontSize: 11, color: T.text, lineHeight: 1.7, whiteSpace: "pre-wrap", maxHeight: 220, overflow: "auto" }}>{brief.brief_text}</div>
                ) : (
                  <div style={{ fontSize: 11, color: T.muted }}>오늘 브리핑 생성 중…<div style={{ fontSize: 9, marginTop: 4 }}>매일 04:00 KST 자동 생성</div></div>
                )}
                {brief && (
                  <div style={{ display: "flex", gap: 12, marginTop: 10, paddingTop: 10, borderTop: `1px solid ${T.border}`, fontFamily: T.mono, fontSize: 9, color: T.muted }}>
                    <span style={{ color: T.critical }}>C {stats.critical_count ?? brief.critical_count ?? 0}</span>
                    <span style={{ color: T.watch }}>W {stats.watch_count ?? brief.watch_count ?? 0}</span>
                    <span style={{ color: T.monitor }}>M {stats.monitor_count ?? brief.monitor_count ?? 0}</span>
                    {brief.model && <span style={{ marginLeft: "auto" }}>{brief.model}</span>}
                  </div>
                )}
              </Panel>

              <Panel title="Quick Actions">
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <button onClick={() => go("/")} style={{ padding: "9px 12px", background: T.gold, color: "#0A0E14", border: "none", borderRadius: 4, fontSize: 11, fontWeight: 600, cursor: "pointer", fontFamily: T.font, textAlign: "left" }}>+ New Deal</button>
                  {[["Signal Room", "/"], ["Pipeline", "/"], ["Risk Book", "/"]].map(([label, to]) => (
                    <button key={label} onClick={() => go(to)} style={{ padding: "9px 12px", background: "transparent", color: T.text, border: `1px solid ${T.border}`, borderRadius: 4, fontSize: 11, cursor: "pointer", fontFamily: T.font, textAlign: "left" }}>{label} →</button>
                  ))}
                </div>
              </Panel>
            </div>
          </div>
        </div>
      )}

      {/* ── 하단 상태바 ── */}
      <div style={{ position: "fixed", bottom: 0, left: 172, right: 0, height: 28, background: T.card, borderTop: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 18, padding: "0 18px", fontSize: 10, color: T.muted, zIndex: 10 }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: hermesUp ? T.green : T.muted }} />
          HERMES {hermesUp ? "connected" : "idle"}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: cosmosUp ? T.green : cosmosUp === false ? T.critical : T.muted }} />
          COSMOS {cosmosUp ? "connected" : cosmosUp === false ? "down" : "…"}
        </span>
        <span style={{ marginLeft: "auto" }}>LAST SCAN · <span style={{ fontFamily: T.mono }}>{fmtTime(lastScan)} ({fmtRel(lastScan)})</span></span>
      </div>
    </div>
  );
}
