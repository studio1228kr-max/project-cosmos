import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (CreditDesk와 동일) ───────────────────────
const T = {
  bg: "#080C14",
  gold: "#C9A84C",
  blue: "#4A90D9",
  green: "#2ACA70",
  red: "#FF5555",
  orange: "#FF8833",
  text: "#E2E8F0",
  muted: "#4A6080",
  border: "#1A2332",
  font: "'Goldman Sans', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};

const dash = (v: any) => (v === null || v === undefined || v === "" ? "—" : v);

// 상태 → 색상
const STATUS_COLOR: Record<string, string> = {
  PASS: T.green, DONE: T.green, COMPLETE: T.green, CONFIRMED: T.green, OK: T.green,
  FLAG: T.orange, WEAK: T.orange, HOLD: T.orange, WARN: T.orange,
  BLOCK: T.red, KILL: T.red, BROKEN: T.red, FAIL: T.red,
  PENDING: T.muted, IDLE: T.muted, WAIT: T.muted, "대기": T.muted,
};
const sc = (s?: string) => STATUS_COLOR[(s || "").toUpperCase()] || T.muted;

const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };

const Badge = ({ status, big }: { status?: string; big?: boolean }) => {
  if (!status) return <span style={{ color: T.muted }}>—</span>;
  const c = sc(status);
  return (
    <span style={{
      fontSize: big ? 13 : 10, color: c, background: `${c}1A`, border: `1px solid ${c}44`,
      borderRadius: 3, padding: big ? "3px 10px" : "2px 7px", letterSpacing: big ? "2px" : "0.04em", whiteSpace: "nowrap",
    }}>{status}</span>
  );
};

const AutoTag = ({ by = "AUTO" }: { by?: string }) => (
  <span style={{ fontSize: 9, color: T.blue, border: `1px solid ${T.blue}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.06em" }}>{by}</span>
);

const Divider = ({ children }: { children: React.ReactNode }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "18px 0 12px" }}>
    <span style={{ fontSize: 10, color: T.muted, letterSpacing: "0.08em", whiteSpace: "nowrap" }}>{children}</span>
    <span style={{ flex: 1, height: 1, background: T.border }} />
  </div>
);

// 스텝 카드 아이콘: done=초록체크 / active=골드화살표 / flag=오렌지느낌표 / pending=회색
function StepIcon({ kind }: { kind: "done" | "active" | "flag" | "pending" | "block" }) {
  const map = { done: [T.green, "✓"], active: [T.gold, "→"], flag: [T.orange, "!"], block: [T.red, "×"], pending: [T.muted, "•"] } as const;
  const [c, g] = map[kind];
  return <span style={{ width: 20, height: 20, flexShrink: 0, borderRadius: "50%", border: `1px solid ${c}55`, color: c, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{g}</span>;
}

function StepCard({ icon, title, auto, badge, desc, meta, active, blocked, action }: {
  icon: "done" | "active" | "flag" | "pending" | "block"; title: string; auto?: string; badge?: string;
  desc?: string; meta?: string; active?: boolean; blocked?: boolean; action?: React.ReactNode;
}) {
  return (
    <div style={{
      padding: "14px 16px", borderBottom: `1px solid ${T.border}`,
      background: active ? "#0D1826" : "transparent",
      opacity: blocked ? 0.38 : 1,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <StepIcon kind={icon} />
        <span style={{ color: T.text }}>{title}</span>
        {auto && <AutoTag by={auto} />}
        <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10 }}>
          {badge && <Badge status={badge} />}
          {action}
        </span>
      </div>
      {(desc || meta) && (
        <div style={{ marginLeft: 30, marginTop: 6 }}>
          {desc && <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.6 }}>{desc}</div>}
          {meta && <div style={{ fontSize: 10, color: T.muted, marginTop: 4, fontFamily: T.mono }}>{meta}</div>}
        </div>
      )}
    </div>
  );
}

const TABS = [
  { id: "intake", n: "01", label: "Intake & Gating" },
  { id: "diligence", n: "02", label: "Diligence" },
  { id: "analysis", n: "03", label: "Analysis" },
  { id: "evidence", n: "04", label: "Evidence" },
  { id: "icpack", n: "05", label: "IC Pack" },
];

export default function DealExecution({ deals = [] }: { deals?: any[] }) {
  const [selId, setSelId] = useState<string | null>(null);
  const [active, setActive] = useState("intake");
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const [deal, setDeal] = useState<any>(null);
  const [gates, setGates] = useState<any>({});
  const [docs, setDocs] = useState<any[]>([]);
  const [irr, setIrr] = useState<any>({});
  const [narrative, setNarrative] = useState<any>(null);
  const [activity, setActivity] = useState<any[]>([]);
  const [vote, setVote] = useState<string | null>(null);

  useEffect(() => {
    if (!selId && deals.length) setSelId(deals[0].deal_code || String(deals[0].id));
  }, [deals, selId]);

  const load = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}`).then(r => setDeal(r.data)).catch(() => setDeal(null));
    API.get(`/api/deals/${id}/gates`).then(r => setGates(r.data || {})).catch(() => setGates({}));
    API.get(`/api/deals/${id}/documents`).then(r => setDocs(r.data?.documents || r.data || [])).catch(() => setDocs([]));
    API.get(`/api/deals/${id}/irr`).then(r => setIrr(r.data || {})).catch(() => setIrr({}));
    API.get(`/api/deals/${id}/narrative`).then(r => setNarrative(r.data || null)).catch(() => setNarrative(null));
    API.get(`/api/deals/${id}/activity`).then(r => setActivity(r.data?.activity || r.data || [])).catch(() => setActivity([]));
  }, []);
  useEffect(() => { load(selId); }, [selId, load]);

  // 스크롤 위치로 현재 섹션 감지 → 푸터 탭 active
  useEffect(() => {
    const root = scrollRef.current;
    if (!root) return;
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id); }),
      { root, threshold: 0, rootMargin: "0px 0px -65% 0px" }
    );
    TABS.forEach(t => { const el = document.getElementById(t.id); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, [selId]);

  const goSection = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });

  const listDeal = deals.find((d: any) => (d.deal_code || String(d.id)) === selId) || {};
  const D = { ...listDeal, ...(deal || {}) };

  const g = (k: string) => gates?.[k] || {};
  const progress = D.progress ?? gates?.progress ?? null;
  const solo = D.source_replicability || D.competition || (D.is_solo ? "단독" : null);

  // 문서 카운트
  const docCount = (s: string) => docs.filter((d: any) => (d.status || "").toUpperCase().includes(s)).length;
  const recv = docs.filter((d: any) => ["RECEIVED", "수령", "DONE"].some(x => (d.status || "").toUpperCase().includes(x.toUpperCase()))).length;
  const review = docs.filter((d: any) => ["REVIEW", "검토"].some(x => (d.status || "").toUpperCase().includes(x.toUpperCase()))).length;
  const missing = docs.filter((d: any) => ["MISSING", "미수령", "PENDING"].some(x => (d.status || "").toUpperCase().includes(x.toUpperCase()))).length;

  const irrCell = (key: string) => irr?.[key]?.value ?? irr?.[key] ?? null;

  return (
    <div style={{ display: "flex", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text }}>

      {/* ── 좌측: 활성 딜 리스트 ── */}
      <div style={{ width: 200, flexShrink: 0, borderRight: `1px solid ${T.border}`, overflowY: "auto" }}>
        <div style={{ padding: "12px 16px 6px", ...labelStyle }}>Active Deals</div>
        {deals.length === 0 ? (
          <div style={{ padding: "16px", fontSize: 11, color: T.muted }}>등록된 딜 없음</div>
        ) : deals.map((d: any) => {
          const id = d.deal_code || String(d.id);
          const active = id === selId;
          return (
            <div key={id} onClick={() => setSelId(id)} style={{
              padding: "10px 16px", cursor: "pointer", borderBottom: `1px solid ${T.border}`,
              borderLeft: active ? `2px solid ${T.gold}` : "2px solid transparent",
              background: active ? "#0D1826" : "transparent",
            }}>
              <div style={{ fontSize: 12, color: active ? T.text : T.muted, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{dash(d.deal_name)}</div>
              <div style={{ fontSize: 9, color: T.muted, marginTop: 3, fontFamily: T.mono }}>{dash(d.deal_code)}</div>
            </div>
          );
        })}
      </div>

      {/* ── 메인 ── */}
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* 딜 헤더 (고정) */}
        <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 16, color: T.text }}>{dash(D.deal_name)}</span>
            {D.deal_type && <span style={{ fontSize: 10, color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3, padding: "2px 8px" }}>{D.deal_type}</span>}
            {solo && <span style={{ fontSize: 10, color: T.blue, border: `1px solid ${T.blue}44`, borderRadius: 3, padding: "2px 8px" }}>{solo}</span>}
            <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(D.created_at ? String(D.created_at).slice(0, 10) : null)}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
            <div style={{ flex: 1, height: 4, background: T.border, borderRadius: 2, overflow: "hidden" }}>
              <div style={{ width: `${progress != null ? Math.min(100, progress) : 0}%`, height: "100%", background: T.gold }} />
            </div>
            <span style={{ fontSize: 11, color: T.muted, fontFamily: T.mono, minWidth: 36 }}>{progress != null ? `${progress}%` : "—"}</span>
          </div>
        </div>

        {/* 세로 스크롤 컨텐츠 (5개 섹션) */}
        <div ref={scrollRef} style={{ flex: 1, overflowY: "auto" }}>

          {/* ── 01 Intake & Gating ── */}
          <section id="intake">
            <SectionHeader n="01" name="INTAKE & GATING" desc="딜 등록 · COI · Kill · ESG" />
            <StepCard icon="done" title="① 딜 등록" badge="DONE"
              desc={`딜타입 ${dash(D.deal_type)} · ${dash(solo)}`} meta={D.created_at ? `등록 ${String(D.created_at).slice(0, 16).replace("T", " ")}` : undefined} />
            <StepCard icon={g("coi").status ? (sc(g("coi").status) === T.red ? "block" : sc(g("coi").status) === T.orange ? "flag" : "done") : "pending"}
              title="② COI 체크" auto="AUTO" badge={g("coi").status || "—"}
              desc={dash(g("coi").detail)} meta={g("coi").ran_at ? `${String(g("coi").ran_at).slice(0, 16).replace("T", " ")} · ${dash(g("coi").ran_by || "SYSTEM")}` : undefined} />
            <StepCard icon={g("kill").status ? (sc(g("kill").status) === T.red ? "block" : sc(g("kill").status) === T.orange ? "flag" : "done") : "pending"}
              title="③ Kill Check" auto="AUTO" badge={g("kill").status || "—"}
              desc={dash(g("kill").detail)} meta={g("kill").ran_at ? `${String(g("kill").ran_at).slice(0, 16).replace("T", " ")} · ${dash(g("kill").ran_by || "SYSTEM")}` : undefined} />
            <StepCard icon={g("esg").status ? (sc(g("esg").status) === T.orange ? "flag" : "done") : "pending"}
              title="④ ESG 스크리닝" auto="AUTO" badge={g("esg").status || "—"}
              desc={dash(g("esg").detail)} meta={g("esg").ran_at ? `${String(g("esg").ran_at).slice(0, 16).replace("T", " ")} · ${dash(g("esg").ran_by || "SYSTEM")}` : undefined} />
          </section>

          {/* ── 02 Diligence ── */}
          <section id="diligence">
            <SectionHeader n="02" name="DILIGENCE" desc="SDD · Valuation · CDD · 문서" />
            <StepCard icon={g("sdd").status ? "done" : "pending"} title="⑤ SDD" auto="HERMES" badge={g("sdd").status || "—"} desc={dash(g("sdd").detail)} />
            <StepCard icon={g("valuation").status ? "done" : "pending"} title="⑥ Valuation Gate" badge={g("valuation").status || "—"}
              desc={g("valuation").ltv != null ? `LTV ${g("valuation").ltv}%` : dash(g("valuation").detail)} />
            <StepCard icon={g("cdd").status ? (sc(g("cdd").status) === T.green ? "done" : "active") : "active"} title="⑦ CDD (정량)" badge={g("cdd").status || "진행 중"} active
              desc={dash(g("cdd").detail)}
              action={g("cdd").progress != null ? <span style={{ fontFamily: T.mono, fontSize: 11, color: T.gold }}>{g("cdd").progress}%</span> : undefined} />
            {/* Document Tracker */}
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10 }}>
                <span style={labelStyle}>Document Tracker</span>
                <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>
                  <span style={{ color: T.green }}>수령 {recv}</span> · <span style={{ color: T.orange }}>검토중 {review}</span> · <span style={{ color: T.muted }}>미수령 {missing}</span>
                </span>
              </div>
              {docs.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : docs.map((doc: any, i: number) => {
                const c = sc(doc.status);
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: c }} />
                    <span style={{ fontSize: 12, color: T.text }}>{dash(doc.name || doc.doc_name)}</span>
                    <span style={{ marginLeft: "auto" }}><Badge status={doc.status} /></span>
                  </div>
                );
              })}
            </div>
            <StepCard icon="block" title="⑧ EDD" badge="BLOCK" blocked desc="CDD 완료 후 진행 가능" />
            <Divider>정성 실사 2.5 · CDD PASS 후 병행</Divider>
            <div style={{ padding: "0 16px 16px", opacity: 0.38 }}>
              <div style={{ fontSize: 11, color: T.muted }}>정성 실사 항목 — CDD PASS 후 활성화</div>
            </div>
          </section>

          {/* ── 03 Analysis ── */}
          <section id="analysis">
            <SectionHeader n="03" name="ANALYSIS" desc="IRR · Merton · ECL · Narrative" />
            {/* IRR Scenario Pack */}
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
            <StepCard icon={g("merton").status ? "done" : "pending"} title="Merton KMV" auto="HEPHAESTUS" badge={g("merton").status || "대기"}
              desc={`PD ${dash(g("merton").pd)} · DD ${dash(g("merton").dd)}`} />
            <StepCard icon={g("ecl").status ? "done" : "pending"} title="ECL / IFRS9" auto="HEPHAESTUS" badge={g("ecl").status || "대기"} desc={dash(g("ecl").detail)} />
            {/* Narrative Gate */}
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ color: T.text }}>Narrative Gate</span>
              <span style={{ marginLeft: "auto" }}><Badge status={narrative?.result || narrative?.status} big /></span>
            </div>
          </section>

          {/* ── 04 Evidence ── */}
          <section id="evidence">
            <SectionHeader n="04" name="EVIDENCE" desc="근거 · Override · Activity" />
            {[["COI", "coi"], ["Kill Check", "kill"], ["ESG", "esg"]].map(([title, key]) => {
              const gg = g(key);
              return (
                <div key={key} style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}` }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ color: T.text }}>{title}</span>
                    <span style={{ marginLeft: "auto" }}><Badge status={gg.status} /></span>
                  </div>
                  <div style={{ fontSize: 11, color: T.muted, marginTop: 6, lineHeight: 1.6 }}>{dash(gg.detail)}</div>
                  {gg.source && <div style={{ fontSize: 10, color: T.muted, marginTop: 4, fontFamily: T.mono }}>출처: {gg.source}</div>}
                </div>
              );
            })}
            <Divider>예외 &amp; Override</Divider>
            <div style={{ margin: "0 16px 16px", padding: "12px 14px", background: "#0D0A08", borderBottom: `1px solid ${T.border}` }}>
              {(gates?.overrides || []).length === 0 ? (
                <div style={{ fontSize: 11, color: T.muted }}>Override 없음</div>
              ) : (gates.overrides as any[]).map((o, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 0" }}>
                  <span style={{ fontSize: 10, color: T.orange, border: `1px solid ${T.orange}44`, borderRadius: 3, padding: "2px 7px" }}>OVERRIDE</span>
                  <span style={{ fontSize: 11, color: T.text }}>{dash(o.detail)}</span>
                </div>
              ))}
            </div>
            <Divider>Activity Feed</Divider>
            <div style={{ padding: "0 16px 16px" }}>
              {activity.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : activity.map((a: any, i: number) => (
                <div key={i} style={{ display: "flex", gap: 12, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ minWidth: 32, fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(a.time ? String(a.time).slice(11, 16) : null)}</span>
                  <span style={{ fontSize: 11, color: T.muted }}>{dash(a.text || a.message)}</span>
                </div>
              ))}
            </div>
          </section>

          {/* ── 05 IC Pack ── */}
          <section id="icpack">
            <SectionHeader n="05" name="IC PACK" desc="Memo · Risks · Voting · Carry-forward" />
            {/* IC Memo 초안 */}
            <div style={{ margin: "14px 16px", padding: "14px 16px", background: "#0A0F1A", borderLeft: `2px solid #C9A84C33` }}>
              <div style={{ marginBottom: 8 }}><span style={labelStyle}>IC Memo 초안</span></div>
              <div style={{ fontSize: 12, color: T.text, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{dash(D.ic_memo || D.memo)}</div>
            </div>
            {/* Key Risks */}
            <div style={{ padding: "0 16px 14px" }}>
              <div style={{ marginBottom: 8 }}><span style={labelStyle}>Key Risks</span></div>
              {(D.key_risks || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : (D.key_risks as any[]).map((r, i) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "5px 0" }}>
                  <span style={{ width: 6, height: 6, borderRadius: "50%", background: T.red, marginTop: 5, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: T.text, lineHeight: 1.6 }}>{typeof r === "string" ? r : r.text}</span>
                </div>
              ))}
            </div>
            {/* IC Voting */}
            <div style={{ padding: "14px 16px", borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
              <div style={{ marginBottom: 10 }}><span style={labelStyle}>IC Voting</span></div>
              <div style={{ display: "flex", gap: 8 }}>
                {[["승인", T.green], ["조건부승인", T.gold], ["부결", T.red]].map(([label, color]) => {
                  const on = vote === label;
                  return (
                    <button key={label as string} onClick={() => setVote(label as string)} style={{
                      flex: 1, padding: "10px", fontSize: 12, cursor: "pointer", fontFamily: T.font,
                      color: on ? "#080C14" : (color as string), background: on ? (color as string) : "transparent",
                      border: `1px solid ${color as string}`, borderRadius: 4,
                    }}>{label}</button>
                  );
                })}
              </div>
            </div>
            {/* Carry-forward */}
            <div style={{ padding: "14px 16px" }}>
              <div style={{ marginBottom: 8 }}><span style={labelStyle}>Carry-forward</span></div>
              {(D.carry_forward || ["—", "—", "—", "—"]).slice(0, 4).map((c: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 10, padding: "5px 0" }}>
                  <span style={{ fontFamily: T.mono, fontSize: 11, color: T.gold, flexShrink: 0 }}>C{i + 1}</span>
                  <span style={{ fontSize: 12, color: T.muted, lineHeight: 1.6 }}>{typeof c === "string" ? c : (c.text || "—")}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* 푸터 탭바 (하단 고정) */}
        <div style={{ flexShrink: 0, display: "flex", borderTop: `1px solid ${T.border}`, background: T.bg }}>
          {TABS.map(t => {
            const on = t.id === active;
            return (
              <button key={t.id} onClick={() => goSection(t.id)} style={{
                flex: 1, padding: "10px 8px", cursor: "pointer", background: on ? "#0D1826" : "transparent",
                border: "none", borderTop: on ? `2px solid ${T.gold}` : "2px solid transparent",
                display: "flex", alignItems: "baseline", justifyContent: "center", gap: 6, fontFamily: T.font,
              }}>
                <span style={{ fontFamily: T.mono, fontSize: 11, color: on ? T.gold : T.muted }}>{t.n}</span>
                <span style={{ fontSize: 11, color: on ? T.text : T.muted, whiteSpace: "nowrap" }}>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 우측 고정 패널 ── */}
      <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", padding: "0 0 20px", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
        <PanelSection title="딜 현황">
          <Row k="진행률" v={progress != null ? `${progress}%` : "—"} mono />
          <Row k="현재 단계" v={dash(D.stage)} />
          <Row k="자동 대기" v={dash(gates?.auto_pending)} mono />
          <Row k="경과" v={dash(gates?.elapsed)} mono />
          <Row k="마감" v={dash(D.maturity_date ? String(D.maturity_date).slice(0, 10) : null)} mono />
        </PanelSection>
        <PanelSection title="게이트 요약">
          {[["COI", "coi"], ["Kill", "kill"], ["ESG", "esg"], ["SDD", "sdd"], ["CDD", "cdd"], ["Narrative", null]].map(([label, key]) => (
            <div key={label as string} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
              <span style={{ fontSize: 11, color: T.muted }}>{label}</span>
              <Badge status={key ? g(key as string).status : (narrative?.result || narrative?.status)} />
            </div>
          ))}
        </PanelSection>
        <PanelSection title="문서">
          <Row k="수령" v={String(recv)} mono color={T.green} />
          <Row k="검토중" v={String(review)} mono color={T.orange} />
          <Row k="미수령" v={String(missing)} mono color={T.muted} />
        </PanelSection>
        <PanelSection title="IRR">
          <Row k="Base" v={irrCell("base") != null ? `${irrCell("base")}%` : "—"} mono color={T.green} />
          <Row k="Downside" v={irrCell("downside") != null ? `${irrCell("downside")}%` : "—"} mono color={T.gold} />
          <Row k="Severe" v={irrCell("severe") != null ? `${irrCell("severe")}%` : "—"} mono color={T.red} />
        </PanelSection>
        <PanelSection title="범례">
          {[["완료", T.green], ["진행중", T.gold], ["자동", T.blue], ["FLAG", T.orange], ["대기", T.muted]].map(([l, c]) => (
            <div key={l as string} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: c as string }} />
              <span style={{ fontSize: 11, color: T.muted }}>{l}</span>
            </div>
          ))}
        </PanelSection>
      </div>
    </div>
  );
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

function PanelSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
      <div style={{ marginBottom: 10, fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" }}>{title}</div>
      {children}
    </div>
  );
}
function Row({ k, v, mono, color }: { k: string; v: string; mono?: boolean; color?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", padding: "4px 0" }}>
      <span style={{ fontSize: 11, color: T.muted }}>{k}</span>
      <span style={{ fontSize: 12, color: color || T.text, fontFamily: mono ? T.mono : T.font }}>{v}</span>
    </div>
  );
}
