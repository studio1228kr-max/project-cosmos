import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (CreditDesk와 동일) ───────────────────────
const T = {
  bg: "#080C14",
  surface1: "#0D1826",
  gold: "#C9A84C",
  blue: "#4A90D9",        // AUTO
  purple: "#8B5CF6",      // HEPHAESTUS
  green: "#2ACA70",
  red: "#FF5555",
  orange: "#FF8833",
  watch: "#F59E0B",
  text: "#E2E8F0",
  muted: "#4A6080",
  dim: "#2A3A52",
  border: "#1A2332",
  font: "'Goldman Sans', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};

const dash = (v: any) => (v === null || v === undefined || v === "") ? "—" : v;

const STATUS_COLOR: Record<string, string> = {
  PASS: T.green, DONE: T.green, COMPLETE: T.green, CONFIRMED: T.green, OK: T.green, 완료: T.green,
  FLAG: T.orange, WEAK: T.orange, HOLD: T.orange, WARN: T.orange,
  BLOCK: T.red, KILL: T.red, BROKEN: T.red, FAIL: T.red, CRITICAL: T.red,
  PENDING: T.muted, IDLE: T.muted, WAIT: T.muted, 대기: T.muted,
};
const sc = (s?: string) => STATUS_COLOR[(s || "").toUpperCase()] || STATUS_COLOR[s || ""] || T.muted;

const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };

const Badge = ({ status, big }: { status?: string; big?: boolean }) => {
  if (!status) return <span style={{ color: T.muted }}>—</span>;
  const c = sc(status);
  return <span style={{ fontSize: big ? 13 : 10, color: c, background: `${c}1A`, border: `1px solid ${c}44`, borderRadius: 3, padding: big ? "3px 10px" : "2px 7px", letterSpacing: big ? "2px" : "0.04em", whiteSpace: "nowrap" }}>{status}</span>;
};
const Tag = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 9, color, border: `1px solid ${color}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.06em" }}>{label}</span>
);

function StepIcon({ kind }: { kind: "done" | "active" | "pending" }) {
  const map = { done: [T.green, "✓"], active: [T.gold, "→"], pending: [T.muted, "•"] } as const;
  const [c, g] = map[kind];
  return <span style={{ width: 20, height: 20, flexShrink: 0, borderRadius: "50%", border: `1px solid ${c}55`, color: c, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{g}</span>;
}

function SectionHeader({ n, name, desc }: { n: string; name: string; desc: string }) {
  return (
    <div style={{ background: "#060A11", borderTop: "2px solid #1A2235", padding: "8px 16px", display: "flex", alignItems: "baseline", gap: 8 }}>
      <span style={{ fontSize: 8, color: T.gold, fontFamily: T.mono }}>{n}</span>
      <span style={{ fontSize: 10, color: "#8A9BB5", letterSpacing: "0.08em" }}>{name}</span>
      <span style={{ fontSize: 8, color: "#3A4A62" }}>{desc}</span>
    </div>
  );
}

export default function DealExecution({ deals = [] }: { deals?: any[] }) {
  const [selId, setSelId] = useState<string | null>(null);
  const [deal, setDeal] = useState<any>(null);
  const [gates, setGates] = useState<any>({});
  const [docs, setDocs] = useState<any[]>([]);
  const [irr, setIrr] = useState<any>({});
  const [narrative, setNarrative] = useState<any>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState("ALL");

  // 딜 리스트 진입 시 첫 딜 자동 선택 (단일 딜 실행 뷰)
  useEffect(() => { if (deals.length) setSelId(prev => prev || (deals[0].deal_code || String(deals[0].id))); }, [deals]);

  const load = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}`).then(r => setDeal(r.data)).catch(() => setDeal(null));
    API.get(`/api/deals/${id}/gates`).then(r => setGates(r.data || {})).catch(() => setGates({}));
    API.get(`/api/deals/${id}/documents`).then(r => setDocs(r.data?.documents || r.data || [])).catch(() => setDocs([]));
    API.get(`/api/deals/${id}/irr`).then(r => setIrr(r.data || {})).catch(() => setIrr({}));
    API.get(`/api/deals/${id}/narrative`).then(r => setNarrative(r.data || null)).catch(() => setNarrative(null));
    API.get(`/api/deals/${id}/qualitative-tasks`).then(r => setTasks(r.data?.tasks || r.data || [])).catch(() => setTasks([]));
  }, []);
  useEffect(() => { load(selId); }, [selId, load]);

  const listDeal = deals.find((d: any) => (d.deal_code || String(d.id)) === selId) || {};
  const D = { ...listDeal, ...(deal || {}) };
  const g = (k: string) => gates?.[k] || {};
  const solo = D.source_replicability || (D.is_solo ? "단독딜" : null);
  const irrCell = (k: string) => irr?.[k]?.value ?? irr?.[k] ?? null;

  // 진행률 (Pre-IC 9단계)
  const STEP_KEYS = ["coi", "kill", "esg", "sdd", "valuation", "cdd", "irr", "merton", "narrative"];
  const doneCount = 1 + STEP_KEYS.filter(k => sc(g(k).status) === T.green).length; // 1 = 딜 등록
  const progressPct = Math.round((Math.min(doneCount, 9) / 9) * 100);

  // 문서 카운트
  const has = (d: any, ...keys: string[]) => keys.some(k => (d.status || "").toUpperCase().includes(k));
  const recv = docs.filter(d => has(d, "RECEIV", "DONE", "수령")).length;
  const review = docs.filter(d => has(d, "REVIEW", "검토")).length;
  const missing = docs.filter(d => has(d, "MISSING", "PENDING", "미수령")).length;

  // 정성 태스크
  const LV_ORDER: any = { CRITICAL: 0, WATCH: 1, OPTIONAL: 2 };
  const lv = (t: any) => (t.level || "OPTIONAL").toUpperCase();
  const isDone = (t: any) => completed.has(String(t.id ?? t.title));
  const toggle = (t: any) => {
    const key = String(t.id ?? t.title);
    setCompleted(prev => { const n = new Set(prev); n.has(key) ? n.delete(key) : n.add(key); return n; });
  };
  const filtered = tasks
    .filter(t => filter === "ALL" || (filter === "CRITICAL" ? lv(t) === "CRITICAL" : (t.source || "").toUpperCase() === filter.toUpperCase()))
    .sort((a, b) => (LV_ORDER[lv(a)] ?? 3) - (LV_ORDER[lv(b)] ?? 3));
  const criticalOpen = tasks.filter(t => lv(t) === "CRITICAL" && !isDone(t)).length;
  const icEnabled = criticalOpen === 0;

  const QualBadge = ({ source, critical }: { source: string; critical?: boolean }) => {
    const hasCrit = critical || tasks.some(t => (t.source || "").toUpperCase() === source.toUpperCase() && lv(t) === "CRITICAL" && !isDone(t));
    const c = hasCrit ? T.red : T.muted;
    const n = tasks.filter(t => (t.source || "").toUpperCase() === source.toUpperCase()).length;
    return <span onClick={() => setFilter(source)} style={{ fontSize: 9, color: c, border: `1px solid ${c}44`, borderRadius: 3, padding: "1px 6px", cursor: "pointer", marginTop: 6, display: "inline-block" }}>정성 {source}{n ? ` · ${n}` : ""}</span>;
  };

  const StepCard = ({ icon, title, tags, badge, children, dimmed, blocked }: {
    icon: "done" | "active" | "pending"; title: string; tags?: React.ReactNode; badge?: string;
    children?: React.ReactNode; dimmed?: boolean; blocked?: boolean;
  }) => (
    <div style={{
      padding: "14px 16px", borderBottom: `1px solid ${T.border}`,
      background: icon === "active" ? T.surface1 : "transparent",
      borderRadius: icon === "active" ? 6 : 0,
      opacity: blocked ? 0.35 : 1,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <StepIcon kind={icon} />
        <span style={{ color: dimmed ? T.muted : T.text }}>{title}</span>
        {tags}
        {badge && <span style={{ marginLeft: "auto" }}><Badge status={badge} /></span>}
      </div>
      {children && <div style={{ marginLeft: 30, marginTop: 6 }}>{children}</div>}
    </div>
  );

  const AUTO = <Tag label="AUTO" color={T.blue} />;
  const HEPH = <Tag label="HEPHAESTUS" color={T.purple} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* ── 딜 헤더 (상단 고정) ── */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>{dash(D.deal_name)}</span>
          <Tag label={D.deal_type || "DIRECT LENDING"} color={T.gold} />
          {solo && <Tag label={solo} color={T.blue} />}
          <Tag label="CDD-lite 진행중" color={T.watch} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>
            경과 {dash(gates?.elapsed)} · 담당 {dash(D.owner || gates?.owner)}
          </span>
        </div>
        {/* 진행률 바 (Pre-IC 9단계) */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
          <div style={{ flex: 1, display: "flex", gap: 3 }}>
            {Array.from({ length: 9 }).map((_, i) => (
              <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i < doneCount ? T.gold : T.border }} />
            ))}
          </div>
          <span style={{ fontSize: 11, color: T.muted, fontFamily: T.mono, minWidth: 64 }}>{progressPct}% · Pre-IC</span>
        </div>
      </div>

      {/* ── 본문: 좌 파이프라인 + 우 Qualitative Queue ── */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>

        {/* 좌측: 정량 파이프라인 */}
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 01 INTAKE & GATING */}
          <SectionHeader n="01" name="INTAKE & GATING" desc="딜 등록 · COI · Kill · ESG" />
          <StepCard icon="done" dimmed title="① 딜 등록" badge="완료" />
          <StepCard icon={sc(g("coi").status) === T.green ? "done" : "pending"} dimmed={sc(g("coi").status) === T.green} title="② COI 체크" tags={AUTO} badge={g("coi").status || "—"} />
          <StepCard icon={sc(g("kill").status) === T.green ? "done" : "pending"} dimmed={sc(g("kill").status) === T.green} title="③ Kill Check" tags={AUTO} badge={g("kill").status || "—"} />
          <StepCard icon={sc(g("esg").status) === T.green ? "done" : "pending"} title="④ ESG 스크리닝" tags={AUTO} badge={g("esg").status || "—"}>
            {sc(g("esg").status) === T.orange && <QualBadge source="ESG" />}
          </StepCard>

          {/* 02 DILIGENCE */}
          <SectionHeader n="02" name="DILIGENCE" desc="SDD · Valuation · CDD-lite" />
          <StepCard icon={sc(g("sdd").status) === T.green ? "done" : "pending"} title="⑤ SDD" tags={HEPH} badge={g("sdd").status || "—"}>
            <QualBadge source="SDD" />
          </StepCard>
          <StepCard icon={sc(g("valuation").status) === T.green ? "done" : "pending"} dimmed={sc(g("valuation").status) === T.green} title="⑥ Valuation Gate" badge={g("valuation").status || "—"}>
            <div style={{ fontSize: 11, color: T.muted, fontFamily: T.mono }}>LTV {g("valuation").ltv != null ? `${g("valuation").ltv}%` : "—"}</div>
          </StepCard>
          <StepCard icon="active" title="⑦ CDD-lite (Core DD)" badge={g("cdd").status || "진행 중"}>
            <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.6 }}>IC Memo 초안 생성에 충분한 수준까지만 진행</div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
              <div style={{ flex: 1, height: 3, background: T.border, borderRadius: 2, overflow: "hidden" }}>
                <div style={{ width: `${g("cdd").progress != null ? g("cdd").progress : 0}%`, height: "100%", background: T.gold }} />
              </div>
              <span style={{ fontFamily: T.mono, fontSize: 11, color: T.gold }}>{g("cdd").progress != null ? `${g("cdd").progress}%` : "—"}</span>
            </div>
            <div><QualBadge source="CDD" /></div>
            {/* Document Tracker */}
            <div style={{ marginTop: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
                <span style={labelStyle}>Document Tracker</span>
                <span style={{ marginLeft: "auto", fontSize: 10, fontFamily: T.mono }}>
                  <span style={{ color: T.green }}>수령 {recv}</span> · <span style={{ color: T.orange }}>검토중 {review}</span> · <span style={{ color: T.muted }}>미수령 {missing}</span>
                </span>
              </div>
              {docs.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : docs.map((doc: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: sc(doc.status) }} />
                  <span style={{ fontSize: 12 }}>{dash(doc.name || doc.doc_name)}</span>
                  <span style={{ marginLeft: "auto" }}><Badge status={doc.status} /></span>
                </div>
              ))}
            </div>
          </StepCard>

          {/* 03 ANALYSIS & ENGINE */}
          <SectionHeader n="03" name="ANALYSIS & ENGINE" desc="IRR · Merton · ECL · Narrative" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 12 }}><span style={labelStyle}>IRR Scenario Pack</span></div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              {[["Base", "base", T.green], ["Downside", "downside", T.gold], ["Severe", "severe", T.red]].map(([name, key, color]) => {
                const v = irrCell(key as string);
                return (
                  <div key={key as string} style={{ padding: "12px 14px", borderBottom: `2px solid ${color as string}` }}>
                    <div style={{ fontSize: 7, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>{name}</div>
                    <div style={{ fontSize: 13, fontFamily: T.mono, color: color as string, marginTop: 6 }}>{v != null ? `${v}%` : "—"}</div>
                    <div style={{ fontSize: 7, color: T.muted, marginTop: 6 }}>{dash(irr?.[key as string]?.note)}</div>
                  </div>
                );
              })}
            </div>
          </div>
          <StepCard icon="pending" blocked title="Merton KMV" tags={HEPH} badge={g("merton").status || "CDD 완료 후 대기"} />
          <StepCard icon="pending" blocked title="ECL / IFRS9" tags={HEPH} badge={g("ecl").status || "대기"} />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span>Narrative Gate</span>
              <span style={{ marginLeft: "auto" }}><Badge status={narrative?.result || narrative?.status} big /></span>
            </div>
            <QualBadge source="Narrative" />
          </div>

          {/* 04 IC MEMO 초안 */}
          <SectionHeader n="04" name="IC MEMO 초안" desc="생성 대기 · S1~S8" />
          <div style={{ padding: "14px 16px" }}>
            <div style={{ border: `1px dashed ${T.border}`, borderRadius: 6, padding: "14px 16px" }}>
              <div style={{ fontSize: 11, color: T.muted, marginBottom: 10 }}>IC Memo 초안 생성 대기</div>
              {["S1 거래 개요", "S2 차주/스폰서", "S3 담보/구조", "S4 상환재원", "S5 재무분석", "S6 시나리오", "S7 리스크", "S8 권고"].map((s, i) => {
                const filled = (D.ic_memo_sections || {})[`s${i + 1}`];
                const written = i < 4 && filled !== undefined ? filled : (i < 4 ? null : null);
                return (
                  <div key={s} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                    <span style={{ fontSize: 11, color: i < 4 ? T.text : T.muted }}>{s}</span>
                    <span style={{ fontSize: 11, color: written ? T.green : T.muted, fontFamily: T.mono }}>{written ? "작성됨" : "—"}</span>
                  </div>
                );
              })}
            </div>

            {criticalOpen > 0 && (
              <div style={{ marginTop: 12, padding: "10px 14px", background: "#1A0A0A", border: `1px solid ${T.red}44`, borderRadius: 6 }}>
                <span style={{ fontSize: 11, color: T.red }}>⚠ CRITICAL 정성 태스크 {criticalOpen}건 미해소 — IC 제출 불가</span>
              </div>
            )}

            <button
              disabled={!icEnabled}
              onClick={() => { if (icEnabled) document.getElementById("page-3")?.scrollIntoView({ behavior: "smooth" }); }}
              style={{
                width: "100%", marginTop: 12, padding: "12px", fontSize: 13, fontFamily: T.font, borderRadius: 4,
                cursor: icEnabled ? "pointer" : "default",
                background: icEnabled ? T.gold : "transparent",
                color: icEnabled ? "#080C14" : T.muted,
                border: icEnabled ? "none" : `1px solid ${T.border}`,
              }}>
              {icEnabled ? "IC 제출 →" : "CRITICAL 해소 후 제출 가능"}
            </button>
          </div>
        </div>

        {/* 우측: Qualitative Queue (sticky) */}
        <div style={{ width: 300, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 8 }}>
            <span style={labelStyle}>Qualitative Queue</span>
            <span style={{ marginLeft: "auto", fontSize: 11, fontFamily: T.mono, color: T.muted }}>{tasks.filter(t => !isDone(t)).length}/{tasks.length}</span>
          </div>
          {/* 필터 */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "10px 16px", borderBottom: `1px solid ${T.border}` }}>
            {["ALL", "CRITICAL", "CDD", "SDD", "ESG", "Narrative"].map(f => {
              const on = filter === f;
              return (
                <span key={f} onClick={() => setFilter(f)} style={{
                  fontSize: 10, cursor: "pointer", padding: "3px 8px", borderRadius: 3,
                  color: on ? "#080C14" : T.muted, background: on ? T.gold : "transparent", border: `1px solid ${on ? T.gold : T.border}`,
                }}>{f === "ALL" ? "전체" : f}</span>
              );
            })}
          </div>
          {/* 태스크 카드 */}
          <div style={{ padding: "4px 0" }}>
            {filtered.length === 0 ? (
              <div style={{ padding: "24px 16px", textAlign: "center", fontSize: 11, color: T.muted }}>정성 태스크 없음</div>
            ) : filtered.map((t: any, i: number) => {
              const level = lv(t);
              const lc = level === "CRITICAL" ? T.red : level === "WATCH" ? T.watch : T.muted;
              const done = isDone(t);
              return (
                <div key={t.id ?? i} style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}`, opacity: done ? 0.5 : 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <Tag label={level} color={lc} />
                    <span style={{ fontSize: 10, color: T.muted }}>{dash(t.source)}</span>
                  </div>
                  <div style={{ fontSize: 12, color: T.text, marginTop: 6, lineHeight: 1.6 }}>{dash(t.title || t.desc)}</div>
                  {t.action && <div style={{ fontSize: 10, color: T.muted, marginTop: 4 }}>{t.action}</div>}
                  <button onClick={() => toggle(t)} style={{
                    marginTop: 8, padding: "4px 10px", fontSize: 10, cursor: "pointer", borderRadius: 3, fontFamily: T.font,
                    color: done ? T.green : T.muted, background: "transparent", border: `1px solid ${done ? T.green : T.border}`,
                  }}>{done ? "완료 ✓" : "진행 중"}</button>
                </div>
              );
            })}
          </div>
          {/* 하단 요약 */}
          <div style={{ padding: "14px 16px" }}>
            {criticalOpen > 0 ? (
              <div style={{ padding: "10px 12px", background: "#1A0A0A", border: `1px solid ${T.red}44`, borderRadius: 6, fontSize: 11, color: T.red }}>
                CRITICAL 미완료 {criticalOpen}건
              </div>
            ) : (
              <div style={{ padding: "10px 12px", background: "#0A1A10", border: `1px solid ${T.green}44`, borderRadius: 6, fontSize: 11, color: T.green }}>
                CRITICAL 전부 완료 ✓
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
