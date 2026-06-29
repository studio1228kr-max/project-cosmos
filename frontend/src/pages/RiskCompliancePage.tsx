import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (동일) ─────────────────────
const T = {
  bg: "#080C14", surface1: "#0D1826", warn: "#1A140A", danger: "#1A0808",
  gold: "#C9A84C", blue: "#4A90D9", green: "#2ACA70", yellow: "#F59E0B", red: "#FF5555",
  text: "#E2E8F0", muted: "#4A6080", border: "#1A2332",
  font: "'Goldman Sans', sans-serif", mono: "'IBM Plex Mono', ui-monospace, monospace",
};
const dash = (v: any) => (v === null || v === undefined || v === "") ? "—" : v;
const nowStr = () => new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };
const trendArrow = (t?: string) => t === "up" || t === "↑" ? "↑" : t === "down" || t === "↓" ? "↓" : "→";
const SC: Record<string, string> = {
  ACTIVE: T.green, 정상: T.green, OK: T.green, 적용: T.green, 제출완료: T.green, 완료: T.green, ONLINE: T.green,
  WATCH: T.yellow, 경고: T.yellow, 대기: T.yellow, PENDING: T.yellow, DEGRADED: T.yellow, 미승인: T.yellow,
  CRITICAL: T.red, 위반: T.red, 초과: T.red, 미제출: T.red, DOWN: T.red, DEPRECATED: T.muted,
};
const sc = (s?: string) => SC[(s || "").toUpperCase()] || SC[s || ""] || T.muted;
const Tag = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 9, color, border: `1px solid ${color}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.06em" }}>{label}</span>
);
const Pill = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 10, color, background: `${color}1A`, border: `1px solid ${color}44`, borderRadius: 3, padding: "2px 7px" }}>{label}</span>
);
const Refresh = ({ onClick, ts }: { onClick: () => void; ts: string }) => (
  <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
    {ts && <span style={{ fontSize: 9, color: T.muted, fontFamily: T.mono }}>{ts}</span>}
    <span onClick={onClick} style={{ fontSize: 9, color: T.muted, cursor: "pointer" }}>↻</span>
  </span>
);
const Row = ({ k, v, color }: { k: string; v: any; color?: string }) => (
  <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}>
    <span style={{ fontSize: 11, color: T.muted }}>{k}</span>
    <span style={{ fontSize: 11, color: color || T.text, fontFamily: T.mono }}>{dash(v)}</span>
  </div>
);
const Cell = ({ k, v, sub, color }: { k: string; v: any; sub?: any; color?: string }) => (
  <div style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
    <div style={{ fontSize: 9, color: T.muted }}>{k}</div>
    <div style={{ fontSize: 13, fontFamily: T.mono, color: color || (v != null ? T.text : T.muted), marginTop: 4 }}>{dash(v)}</div>
    {sub && <div style={{ fontSize: 9, color: T.muted, marginTop: 2 }}>{sub}</div>}
  </div>
);
function SectionHeader({ n, name, desc, tag }: { n: string; name: string; desc?: string; tag?: React.ReactNode }) {
  return (
    <div style={{ background: "#060A11", borderTop: "2px solid #1A2235", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 8, color: T.gold, fontFamily: T.mono }}>{n}</span>
      <span style={{ fontSize: 10, color: "#8A9BB5", letterSpacing: "0.08em" }}>{name}</span>
      {tag}
      {desc && <span style={{ fontSize: 8, color: "#3A4A62" }}>{desc}</span>}
    </div>
  );
}
const Block: React.FC<{ children: React.ReactNode; warn?: boolean; danger?: boolean; dim?: boolean }> = ({ children, warn, danger, dim }) => (
  <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, background: danger ? T.danger : warn ? T.warn : "transparent", opacity: dim ? 0.35 : 1 }}>{children}</div>
);
const UsageBar = ({ pct }: { pct: number }) => {
  const c = pct >= 100 ? T.red : pct >= 90 ? T.yellow : T.green;
  return (
    <div style={{ flex: 1, height: 6, background: T.border, borderRadius: 3, overflow: "hidden" }}>
      <div style={{ width: `${Math.min(pct, 100)}%`, height: "100%", background: c }} />
    </div>
  );
};
const AUTO = <Tag label="AUTO" color={T.blue} />;
const HEPH = <Tag label="HEPHAESTUS AUTO" color={T.blue} />;
const LINEAGE_TABS = ["Sourcing", "Inference", "Prompt", "Report"];

export default function RiskCompliancePage({ deals = [] }: { deals?: any[] }) {
  const [pf, setPf] = useState<any>({});
  const [stress, setStress] = useState<any>({});
  const [regScen, setRegScen] = useState<any[]>([]);
  const [ras, setRas] = useState<any[]>([]);
  const [coi, setCoi] = useState<any[]>([]);
  const [cal, setCal] = useState<any[]>([]);
  const [aml, setAml] = useState<any>({});
  const [regRep, setRegRep] = useState<any[]>([]);
  const [lineage, setLineage] = useState<any>({});
  const [transLog, setTransLog] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [override, setOverride] = useState<any[]>([]);
  const [binder, setBinder] = useState<any[]>([]);
  const [rbac, setRbac] = useState<any[]>([]);
  const [reviewRules, setReviewRules] = useState<any[]>([]);
  const [policyLog, setPolicyLog] = useState<any[]>([]);
  const [exAging, setExAging] = useState<any[]>([]);
  const [sla, setSla] = useState<any[]>([]);
  const [bcp, setBcp] = useState<any>({});
  const [lineageTab, setLineageTab] = useState(0);
  const [ts, setTs] = useState<Record<string, string>>({ scan: nowStr() });
  const stamp = (k: string) => setTs(p => ({ ...p, [k]: nowStr() }));

  const loadPf = useCallback(() => { API.get(`/api/risk/portfolio-dashboard`).then(r => setPf(r.data || {})).catch(() => setPf({})); stamp("pf"); }, []);
  const loadRas = useCallback(() => { API.get(`/api/risk/ras-status`).then(r => setRas(r.data?.items || r.data || [])).catch(() => setRas([])); stamp("ras"); }, []);
  const loadStress = useCallback(() => { API.get(`/api/risk/stress-test`).then(r => setStress(r.data || {})).catch(() => setStress({})); stamp("stress"); }, []);

  useEffect(() => {
    loadPf(); loadRas(); loadStress();
    API.get(`/api/risk/regulatory-scenarios`).then(r => setRegScen(r.data?.items || r.data || [])).catch(() => setRegScen([]));
    API.get(`/api/risk/coi-registry`).then(r => setCoi(r.data?.items || r.data || [])).catch(() => setCoi([]));
    API.get(`/api/risk/compliance-calendar`).then(r => setCal(r.data?.items || r.data || [])).catch(() => setCal([]));
    API.get(`/api/risk/aml-status`).then(r => setAml(r.data || {})).catch(() => setAml({}));
    API.get(`/api/risk/regulatory-reports`).then(r => setRegRep(r.data?.items || r.data || [])).catch(() => setRegRep([]));
    API.get(`/api/governance/data-lineage`).then(r => setLineage(r.data || {})).catch(() => setLineage({}));
    API.get(`/api/governance/transformation-log`).then(r => setTransLog(r.data?.items || r.data || [])).catch(() => setTransLog([]));
    API.get(`/api/governance/model-registry`).then(r => setModels(r.data?.items || r.data || [])).catch(() => setModels([]));
    API.get(`/api/governance/override-log`).then(r => setOverride(r.data?.items || r.data || [])).catch(() => setOverride([]));
    API.get(`/api/governance/evidence-binder`).then(r => setBinder(r.data?.items || r.data || [])).catch(() => setBinder([]));
    API.get(`/api/governance/rbac`).then(r => setRbac(r.data?.items || r.data || [])).catch(() => setRbac([]));
    API.get(`/api/governance/review-rules`).then(r => setReviewRules(r.data?.items || r.data || [])).catch(() => setReviewRules([]));
    API.get(`/api/governance/policy-log`).then(r => setPolicyLog(r.data?.items || r.data || [])).catch(() => setPolicyLog([]));
    API.get(`/api/governance/exception-aging`).then(r => setExAging(r.data?.items || r.data || [])).catch(() => setExAging([]));
    API.get(`/api/governance/sla-monitor`).then(r => setSla(r.data?.items || r.data || [])).catch(() => setSla([]));
    API.get(`/api/governance/bcp-status`).then(r => setBcp(r.data || {})).catch(() => setBcp({}));
  }, [loadPf, loadRas, loadStress]);

  const agingColor = (d?: number) => d == null ? T.muted : d > 30 ? T.red : d >= 7 ? T.yellow : T.muted;
  const PF_CARDS = [["섹터집중도", pf.sector], ["LTV분포", pf.ltv], ["만기Ladder", pf.maturity], ["Vintage", pf.vintage]];
  const STRESS_ROWS = [["금리 상승 +200bp", stress.rate], ["담보가치 하락 -20%", stress.collateral], ["연체율 상승 +5%", stress.default_rate]];
  const bcpStatus = bcp.status || "Online";

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* 헤더 */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>Risk &amp; Compliance</span>
          <Pill label="상시 가동" color={T.red} /><Tag label="전사 통제실" color={T.gold} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>● Alert Strip 피드 연결 · 마지막 스캔 {ts.scan}</span>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 섹션 A */}
          <SectionHeader n="A" name="RISK CONTROLS" desc="포트폴리오 · 스트레스 · RAS · AML" />

          {/* ① 펀드 레벨 리스크 대시보드 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12 }}>① 펀드 레벨 리스크 대시보드</span>{HEPH}
              <Refresh onClick={loadPf} ts={ts.pf || ""} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 10 }}>
              {PF_CARDS.map(([k, v]) => {
                const o = (v as any) || {};
                const breach = o.usage != null && o.usage >= 90;
                return <Cell key={k as string} k={k as string} v={o.value != null ? `${o.value} ${trendArrow(o.trend)}` : null}
                  sub={o.usage != null ? <span style={{ color: breach ? T.red : T.muted }}>{breach ? "⚠ " : ""}임계치 {o.usage}%</span> : "임계치 —"}
                  color={breach ? T.red : undefined} />;
              })}
            </div>
          </div>

          {/* ② Stress Test */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12 }}>② Stress Test</span>{HEPH}
              <Refresh onClick={loadStress} ts={ts.stress || ""} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>시나리오</span><span>ECL 변화</span><span>NAV 변화</span><span>상태</span>
            </div>
            {STRESS_ROWS.map(([k, v]) => {
              const o = (v as any) || {};
              return (
                <div key={k as string} style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 0.8fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span>{k}</span>
                  <span style={{ fontFamily: T.mono, color: T.red }}>{dash(o.ecl)}</span>
                  <span style={{ fontFamily: T.mono, color: T.red }}>{dash(o.nav)}</span>
                  <span><Pill label={o.status || "—"} color={sc(o.status)} /></span>
                </div>
              );
            })}
            <div style={{ fontSize: 9, color: T.muted, marginTop: 8 }}>마지막 실행 {dash(stress.last_run)} · <span style={{ color: T.gold, cursor: "pointer" }}>재실행</span></div>
          </div>

          {/* ③ Regulatory Scenario Library */}
          <Block>
            <SectionHeader n="③" name="REGULATORY SCENARIO LIBRARY" desc="금감원 · 공제회 · FSC" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 10 }}>
              {(regScen.length ? regScen : [{ name: "금감원" }, { name: "공제회" }, { name: "FSC" }]).map((s: any, i: number) => (
                <div key={i} style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
                  <div style={{ fontSize: 12, color: T.text }}>{dash(s.name)}</div>
                  <div style={{ fontSize: 9, color: s.applied ? T.green : T.muted, marginTop: 4 }}>{s.applied ? "적용" : "미적용"}</div>
                  <div style={{ fontSize: 9, color: T.muted, marginTop: 2 }}>검토 {dash(s.last_review)}</div>
                </div>
              ))}
            </div>
          </Block>

          {/* ④ RAS 대비 현황 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 12 }}>④ RAS 대비 현황</span>
              <Refresh onClick={loadRas} ts={ts.ras || ""} />
            </div>
            {ras.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : ras.map((r: any, i: number) => {
              const u = r.usage || 0;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, width: 130, color: T.muted }}>{dash(r.name)}</span>
                  <UsageBar pct={u} />
                  <span style={{ fontSize: 10, fontFamily: T.mono, width: 80, textAlign: "right", color: u >= 100 ? T.red : u >= 90 ? T.yellow : T.text }}>{dash(r.current)}/{dash(r.limit)} {u ? `${u}%` : ""}</span>
                </div>
              );
            })}
          </div>

          {/* ⑤ COI 레지스트리 */}
          <Block>
            <SectionHeader n="⑤" name="COI 레지스트리" />
            <div style={{ display: "grid", gridTemplateColumns: "0.8fr 1fr 1fr 1fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>구분</span><span>이름</span><span>관계</span><span>등록일</span><span>갱신일</span>
            </div>
            {coi.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : coi.map((c: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "0.8fr 1fr 1fr 1fr 1fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, color: c.stale ? T.yellow : T.text }}>
                <span><Tag label={dash(c.category)} color={T.muted} /></span><span>{dash(c.name)}</span><span>{dash(c.relation)}</span><span style={{ fontFamily: T.mono }}>{dash(c.registered)}</span><span style={{ fontFamily: T.mono }}>{c.stale ? "⚠ " : ""}{dash(c.renewed)}</span>
              </div>
            ))}
            <button style={{ marginTop: 10, padding: "6px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 4 }}>+ 신규 등록</button>
          </Block>

          {/* ⑥ Compliance 캘린더 */}
          <Block>
            <SectionHeader n="⑥" name="COMPLIANCE 캘린더" desc="FSC · FIU STR · 외감" />
            <div style={{ marginTop: 8 }}>
              {(cal.length ? cal : [{ name: "FSC 정기보고" }, { name: "FIU STR" }, { name: "외감 일정" }]).map((c: any, i: number) => {
                const dd = c.dday;
                const col = dd != null && dd < 0 ? T.red : dd != null && dd <= 7 ? T.gold : T.muted;
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                    <span style={{ fontSize: 11, flex: 1 }}>{dash(c.name)}</span>
                    <span style={{ fontSize: 10, color: T.muted }}>{dash(c.org)}</span>
                    <span style={{ fontSize: 10, fontFamily: T.mono, color: T.muted }}>{dash(c.due)}</span>
                    <span style={{ fontSize: 11, fontFamily: T.mono, color: col, width: 50, textAlign: "right" }}>{dd != null ? `D${dd >= 0 ? "-" : "+"}${Math.abs(dd)}` : "—"}</span>
                  </div>
                );
              })}
            </div>
          </Block>

          {/* ⑦ AML / CTF 모니터링 */}
          <Block danger={aml.overdue}>
            <SectionHeader n="⑦" name="AML / CTF 모니터링" tag={AUTO} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginTop: 10 }}>
              <Cell k="STR 생성" v={aml.generated} /><Cell k="제출완료" v={aml.submitted} color={T.green} />
              <Cell k="기한내 제출" v={aml.on_time != null ? (aml.on_time ? "예" : "아니오") : null} color={aml.overdue ? T.red : T.green} />
            </div>
            {aml.overdue && <div style={{ marginTop: 8, fontSize: 11, color: T.red }}>⚠ STR 미제출 기한 초과 → 1페이지 Alert</div>}
          </Block>

          {/* ⑧ 규제 보고 패키지 */}
          <Block>
            <SectionHeader n="⑧" name="규제 보고 패키지" desc="FSC · 금감원 자동 양식" />
            <div style={{ marginTop: 8 }}>
              {(regRep.length ? regRep : [{ name: "FSC 보고양식" }, { name: "금감원 보고양식" }]).map((r: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, flex: 1 }}>{dash(r.name)}</span>
                  <span style={{ fontSize: 10, color: T.muted }}>{dash(r.recipient)}</span>
                  <span style={{ fontSize: 10, fontFamily: T.mono, color: T.muted }}>{dash(r.due)}</span>
                  <button style={{ fontSize: 10, padding: "3px 8px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>생성</button>
                </div>
              ))}
            </div>
          </Block>

          {/* 섹션 B */}
          <SectionHeader n="B" name="AI GOVERNANCE" desc="Lineage · 모델 · Override · Evidence" />

          {/* ⑨ Data Lineage */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 12, marginBottom: 10 }}>⑨ Data Lineage</div>
            <div style={{ display: "flex", gap: 4, marginBottom: 10 }}>
              {LINEAGE_TABS.map((t, i) => (
                <button key={t} onClick={() => setLineageTab(i)} style={{
                  padding: "5px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                  color: lineageTab === i ? "#080C14" : T.muted, background: lineageTab === i ? T.gold : "transparent", border: `1px solid ${lineageTab === i ? T.gold : T.border}`,
                }}>{t}</button>
              ))}
            </div>
            <div style={{ background: T.surface1, borderRadius: 6, padding: "12px 14px", fontFamily: T.mono, fontSize: 11, color: T.muted, lineHeight: 1.9 }}>
              {(() => {
                const L = lineage[LINEAGE_TABS[lineageTab].toLowerCase()] || {};
                if (lineageTab === 0) return <>신호 ID {dash(L.signal_id)}<br />└ 원천 {dash(L.source)} (DART/ECOS)<br />　└ 전처리 {dash(L.preprocess)}<br />　　└ 모델 input {dash(L.model_input)}</>;
                if (lineageTab === 1) return <>모델 {dash(L.model)} v{dash(L.version)}<br />└ input feature {dash(L.feature)}<br />　└ output {dash(L.output)}<br />실행일 {dash(L.run_date)}</>;
                if (lineageTab === 2) return <>프롬프트 v{dash(L.prompt_version)}<br />└ 컨텍스트 {dash(L.context)}<br />　└ response {dash(L.response)}<br />토큰수 {dash(L.tokens)}</>;
                return <>NAV 계산근거 {dash(L.nav_basis)}<br />└ LP 보고 숫자 {dash(L.lp_number)}</>;
              })()}
            </div>
          </div>

          {/* ⑩ Transformation Log */}
          <Block>
            <SectionHeader n="⑩" name="TRANSFORMATION LOG" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>데이터</span><span>변환 전</span><span>변환 후</span><span>사유/실행자</span><span>일시</span>
            </div>
            {transLog.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : transLog.map((t: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr 0.8fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono }}>
                <span style={{ fontFamily: T.font }}>{dash(t.name)}</span><span>{dash(t.before)}</span><span>{dash(t.after)}</span><span>{dash(t.reason)}/{dash(t.actor)}</span><span>{dash(t.at)}</span>
              </div>
            ))}
          </Block>

          {/* ⑪ Model Registry */}
          <Block>
            <SectionHeader n="⑪" name="MODEL REGISTRY & VERSIONING" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 10 }}>
              {(models.length ? models : [{ name: "Merton KMV" }, { name: "ECL" }, { name: "Concentration" }, { name: "Sourcing Agent" }]).map((m: any, i: number) => (
                <div key={i} style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, color: T.text, flex: 1 }}>{dash(m.name)}</span>
                    <Pill label={m.status || "Active"} color={sc(m.status || "Active")} />
                  </div>
                  <div style={{ fontSize: 9, color: T.muted, marginTop: 4, fontFamily: T.mono }}>v{dash(m.version)} · 배포 {dash(m.deployed)} · 실행 {dash(m.last_run)}</div>
                </div>
              ))}
            </div>
          </Block>

          {/* ⑫ Human Override Log */}
          <Block>
            <SectionHeader n="⑫" name="HUMAN OVERRIDE LOG" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 0.8fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>AI 결과</span><span>수정값</span><span>사유</span><span>승인자</span><span>일시</span>
            </div>
            {override.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : override.map((o: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 0.8fr 0.8fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono, color: o.unapproved ? T.yellow : T.text }}>
                <span>{dash(o.ai_value)}</span><span>{dash(o.human_value)}</span><span style={{ fontFamily: T.font }}>{dash(o.reason)}</span><span>{o.unapproved ? "⚠ 미승인" : dash(o.approver)}</span><span>{dash(o.at)}</span>
              </div>
            ))}
          </Block>

          {/* ⑬ Evidence Binder */}
          <Block>
            <SectionHeader n="⑬" name="AI OUTPUT EVIDENCE BINDER" />
            <div style={{ marginTop: 8 }}>
              {(binder.length ? binder : [{ name: "IC Memo 초안" }, { name: "Stress Test 결과" }, { name: "LP 보고 초안" }]).map((b: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, flex: 1 }}>{dash(b.name)}</span>
                  <span style={{ fontSize: 9, color: T.muted, fontFamily: T.mono }}>{dash(b.created)} · 프롬프트 v{dash(b.prompt_version)}</span>
                  <button style={{ fontSize: 10, padding: "3px 8px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>다운로드</button>
                </div>
              ))}
            </div>
          </Block>

          {/* 섹션 C */}
          <SectionHeader n="C" name="OPS GOVERNANCE" desc="RBAC · 4-eyes · Exception · SLA · BCP" />

          {/* ⑭ RBAC */}
          <Block>
            <SectionHeader n="⑭" name="RBAC (역할별 접근 통제)" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>역할</span><span>접근 페이지</span><span>편집권한</span><span>마지막 접속</span>
            </div>
            {(rbac.length ? rbac : [{ role: "GP" }, { role: "외부법무" }, { role: "회계" }, { role: "IR" }]).map((r: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr 1fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ color: T.text }}>{dash(r.role)}</span><span style={{ color: T.muted }}>{dash(r.pages)}</span><span style={{ color: T.muted }}>{dash(r.edit)}</span><span style={{ fontFamily: T.mono, color: T.muted }}>{dash(r.last_login)}</span>
              </div>
            ))}
          </Block>

          {/* ⑮ 4-eyes Review Rules */}
          <Block>
            <SectionHeader n="⑮" name="4-EYES REVIEW RULES" />
            <div style={{ marginTop: 8 }}>
              {(reviewRules.length ? reviewRules : [{ action: "자금 집행" }, { action: "Override 승인" }]).map((r: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, flex: 1 }}>{dash(r.action)}</span>
                  <span style={{ fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(r.threshold)}</span>
                  <span style={{ fontSize: 10, color: r.two_man ? T.gold : T.muted }}>{r.two_man ? "2인 승인" : "단독"}</span>
                  {r.pending > 0 && <Pill label={`대기 ${r.pending}`} color={T.red} />}
                </div>
              ))}
            </div>
          </Block>

          {/* ⑯ Policy Change Log */}
          <Block>
            <SectionHeader n="⑯" name="POLICY CHANGE LOG" />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 0.8fr 0.8fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>정책</span><span>변경 전</span><span>변경 후</span><span>변경자</span><span>일시</span><span>승인자</span>
            </div>
            {policyLog.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : policyLog.map((p: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 0.8fr 0.8fr 0.8fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono }}>
                <span style={{ fontFamily: T.font }}>{dash(p.name)}</span><span>{dash(p.before)}</span><span>{dash(p.after)}</span><span>{dash(p.actor)}</span><span>{dash(p.at)}</span><span>{dash(p.approver)}</span>
              </div>
            ))}
          </Block>

          {/* ⑰ Exception Aging Dashboard */}
          <Block warn>
            <SectionHeader n="⑰" name="EXCEPTION AGING DASHBOARD" desc="전사 · 3페이지 Closing 포함" />
            <div style={{ display: "grid", gridTemplateColumns: "0.9fr 1.4fr 0.8fr 0.6fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "10px 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>출처</span><span>내용</span><span>발생일</span><span>경과</span><span>상태</span>
            </div>
            {exAging.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : exAging.map((e: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "0.9fr 1.4fr 0.8fr 0.6fr 0.8fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                <span><Tag label={dash(e.source)} color={T.muted} /></span>
                <span style={{ color: T.text }}>{dash(e.detail)}</span>
                <span style={{ fontFamily: T.mono, color: T.muted }}>{dash(e.opened)}</span>
                <span style={{ fontFamily: T.mono, color: agingColor(e.days) }}>{e.days != null ? `${e.days}일` : "—"}</span>
                <span><Pill label={e.status || "—"} color={sc(e.status)} /></span>
              </div>
            ))}
          </Block>

          {/* ⑱ SLA Monitor */}
          <Block>
            <SectionHeader n="⑱" name="SLA MONITOR" />
            <div style={{ marginTop: 8 }}>
              {(sla.length ? sla : [{ name: "DD 지연" }, { name: "LP 응답" }, { name: "Covenant 미수령" }, { name: "STR 제출 기한" }, { name: "FSC 보고 D-day" }]).map((s: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, flex: 1 }}>{dash(s.name)}</span>
                  <span style={{ fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(s.threshold)}</span>
                  <span style={{ fontSize: 10, fontFamily: T.mono, color: s.breach ? T.red : T.green }}>{s.breach ? "⚠ 위반" : dash(s.current) }</span>
                </div>
              ))}
            </div>
          </Block>

          {/* ⑲ BCP / Fallback Mode */}
          <Block warn={bcpStatus === "Degraded"} danger={bcpStatus === "Down"}>
            <SectionHeader n="⑲" name="BUSINESS CONTINUITY / FALLBACK MODE" />
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 10 }}>
              <span style={{ fontSize: 11, color: T.muted }}>HERMES 상태</span>
              <Pill label={bcpStatus} color={sc(bcpStatus)} />
              {bcpStatus === "Down" && <button style={{ marginLeft: "auto", padding: "6px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: T.red, color: "#fff", border: "none", borderRadius: 4 }}>수동 입력 모드 활성화</button>}
            </div>
            {bcp.fallback_history && <div style={{ fontSize: 9, color: T.muted, marginTop: 8 }}>Fallback 이력: {dash(bcp.fallback_history)}</div>}
          </Block>
        </div>

        {/* 우측 sticky: Risk Command Center */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}><span style={{ ...labelStyle, color: T.gold }}>Risk Command Center</span></div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>RAS 상태</span><Refresh onClick={loadRas} ts={ts.ras || ""} /></div>
            {ras.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : ras.map((r: any, i: number) => {
              const u = r.usage || 0;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 0" }}>
                  <span style={{ fontSize: 10, width: 70, color: u >= 90 ? T.red : T.muted }}>{dash(r.name)}</span>
                  <UsageBar pct={u} />
                  <span style={{ fontSize: 9, fontFamily: T.mono, width: 32, textAlign: "right", color: u >= 90 ? T.red : T.text }}>{u}%</span>
                </div>
              );
            })}
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Stress Test 최근</span></div>
            <Row k="금리" v={stress.rate?.nav} color={T.red} /><Row k="담보" v={stress.collateral?.nav} color={T.red} /><Row k="연체" v={stress.default_rate?.nav} color={T.red} />
            <div style={{ fontSize: 9, color: T.muted, marginTop: 4 }}>실행 {dash(stress.last_run)}</div>
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Compliance D-day</span></div>
            <Row k="FSC 보고" v={cal.find((c: any) => /FSC/i.test(c.name || ""))?.dday} />
            <Row k="STR 제출" v={aml.dday} />
            <Row k="외감" v={cal.find((c: any) => /외감/i.test(c.name || ""))?.dday} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>STR Filing</span></div>
            <Row k="생성" v={aml.generated} /><Row k="제출완료" v={aml.submitted} color={T.green} /><Row k="기한내" v={aml.on_time != null ? (aml.on_time ? "예" : "아니오") : null} color={aml.overdue ? T.red : undefined} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Model 버전</span></div>
            {(models.length ? models : [{ name: "Merton" }, { name: "ECL" }, { name: "Concentration" }, { name: "Sourcing" }]).map((m: any, i: number) => (
              <Row key={i} k={dash(m.name)} v={m.version ? `v${m.version}` : null} />
            ))}
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Exception 미처리</span></div>
            <Row k="전체" v={exAging.length || 0} />
            <Row k="7~30일" v={exAging.filter((e: any) => e.days >= 7 && e.days <= 30).length} color={T.yellow} />
            <Row k="30일 초과" v={exAging.filter((e: any) => e.days > 30).length} color={T.red} />
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[["Stress Test 실행", T.gold], ["STR 초안 생성", T.gold], ["규제 보고 패키지", T.text], ["Fallback Mode 활성화", T.red], ["Exception Review", T.text]].map(([label, color]) => (
              <button key={label as string} style={{ width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4 }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
