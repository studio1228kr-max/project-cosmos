import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (DealExecution / ClosingPage 동일) ─────────────────────
const T = {
  bg: "#080C14",
  surface1: "#0D1826",
  warn: "#1A140A",
  gold: "#C9A84C",
  blue: "#4A90D9",        // AUTO / HEPHAESTUS
  green: "#2ACA70",
  yellow: "#F59E0B",
  red: "#FF5555",
  text: "#E2E8F0",
  muted: "#4A6080",
  border: "#1A2332",
  font: "'Goldman Sans', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};
const dash = (v: any) => (v === null || v === undefined || v === "") ? "—" : v;
const nowStr = () => new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };
const Tag = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 9, color, border: `1px solid ${color}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.06em" }}>{label}</span>
);
const SC: Record<string, string> = {
  정상: T.green, 완료: T.green, 정상납입: T.green, 이상없음: T.green, PASS: T.green,
  요주의: T.yellow, "SPECIAL MENTION": T.yellow, 위험: T.yellow, WARNING: T.yellow,
  고정: T.red, 회수의문: T.red, 위반: T.red, 연체: T.red, 감지: T.red, DANGER: T.red,
  대기: T.muted, 미착수: T.muted,
};
const sc = (s?: string) => SC[(s || "").toUpperCase()] || SC[s || ""] || T.muted;
const trendArrow = (t?: string) => t === "up" || t === "↑" ? "↑" : t === "down" || t === "↓" ? "↓" : "→";

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
const StepCard: React.FC<{ icon?: "done" | "active" | "pending"; title: string; tags?: React.ReactNode; right?: React.ReactNode; children?: React.ReactNode; blocked?: boolean }> =
  ({ icon = "pending", title, tags, right, children, blocked }) => (
    <div style={{
      padding: "14px 16px", borderBottom: `1px solid ${T.border}`,
      background: icon === "active" ? T.surface1 : "transparent",
      borderRadius: icon === "active" ? 6 : 0,
      opacity: blocked ? 0.35 : icon === "done" ? 0.75 : 1,
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <StepIcon kind={icon} />
        <span style={{ color: icon === "done" ? T.muted : T.text }}>{title}</span>
        {tags}
        {right && <span style={{ marginLeft: "auto" }}>{right}</span>}
      </div>
      {children && <div style={{ marginLeft: 30, marginTop: 8 }}>{children}</div>}
    </div>
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
const Cell = ({ k, v, color }: { k: string; v: any; color?: string }) => (
  <div style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
    <div style={{ fontSize: 9, color: T.muted }}>{k}</div>
    <div style={{ fontSize: 13, fontFamily: T.mono, color: color || (v != null ? T.text : T.muted), marginTop: 4 }}>{dash(v)}</div>
  </div>
);
const Pill = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 10, color, background: `${color}1A`, border: `1px solid ${color}44`, borderRadius: 3, padding: "2px 7px" }}>{label}</span>
);

const AUTO = <Tag label="AUTO" color={T.blue} />;
const HERMES = <Tag label="HERMES AUTO" color={T.blue} />;
const HEPH = <Tag label="HEPHAESTUS" color={T.blue} />;
const MOLIT = <Tag label="MOLIT" color={T.blue} />;

const WATCH_GRADES: [string, string][] = [
  ["정상", T.green], ["요주의", T.yellow], ["Special Mention", T.yellow], ["고정", T.red], ["회수의문", T.red],
];

export default function PortfolioPage({ deals = [] }: { deals?: any[] }) {
  const [selId, setSelId] = useState<string | null>(null);
  const [deal, setDeal] = useState<any>(null);
  const [payments, setPayments] = useState<any>({});
  const [fin, setFin] = useState<any>({});
  const [grade, setGrade] = useState<string | null>(null);
  const [lpNotify, setLpNotify] = useState(false);
  const [covenants, setCovenants] = useState<any[]>([]);
  const [conc, setConc] = useState<any>({});
  const [collateral, setCollateral] = useState<any>({});
  const [perfection, setPerfection] = useState<any[]>([]);
  const [reval, setReval] = useState<any>({});
  const [control, setControl] = useState<any>({});
  const [ate, setAte] = useState<any>({});
  const [recovery, setRecovery] = useState<any>({});
  // 우측 스냅샷 타임스탬프
  const [ts, setTs] = useState<Record<string, string>>({});
  const stamp = (k: string) => setTs(p => ({ ...p, [k]: nowStr() }));

  useEffect(() => { if (deals.length) setSelId(prev => prev || (deals[0].deal_code || String(deals[0].id))); }, [deals]);

  const loadHealth = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}/payments`).then(r => setPayments(r.data || {})).catch(() => setPayments({}));
    API.get(`/api/deals/${id}/financial-status`).then(r => setFin(r.data || {})).catch(() => setFin({}));
    stamp("health");
  }, []);
  const loadCovenants = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}/covenants`).then(r => setCovenants(r.data?.covenants || r.data || [])).catch(() => setCovenants([]));
    stamp("cov");
  }, []);
  const loadCollateral = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}/collateral`).then(r => setCollateral(r.data || {})).catch(() => setCollateral({}));
    API.get(`/api/deals/${id}/perfection`).then(r => setPerfection(r.data?.items || r.data || [])).catch(() => setPerfection([]));
    API.get(`/api/deals/${id}/revaluation`).then(r => setReval(r.data || {})).catch(() => setReval({}));
    stamp("col");
  }, []);

  const load = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}`).then(r => setDeal(r.data)).catch(() => setDeal(null));
    API.get(`/api/deals/${id}/watchlist`).then(r => { setGrade(r.data?.grade || null); setLpNotify(!!r.data?.lp_notify); }).catch(() => {});
    API.get(`/api/portfolio/concentration`).then(r => setConc(r.data || {})).catch(() => setConc({}));
    API.get(`/api/deals/${id}/control-account`).then(r => setControl(r.data || {})).catch(() => setControl({}));
    API.get(`/api/deals/${id}/ate-triggers`).then(r => setAte(r.data || {})).catch(() => setAte({}));
    API.get(`/api/deals/${id}/recovery-strategy`).then(r => setRecovery(r.data || {})).catch(() => setRecovery({}));
  }, []);
  useEffect(() => { load(selId); loadHealth(selId); loadCovenants(selId); loadCollateral(selId); }, [selId, load, loadHealth, loadCovenants, loadCollateral]);

  const listDeal = deals.find((d: any) => (d.deal_code || String(d.id)) === selId) || {};
  const D = { ...listDeal, ...(deal || {}) };

  const setWatch = (g: string) => {
    setGrade(g);
    if (g !== "정상") setLpNotify(true);
    if (selId) API.post(`/api/deals/${selId}/watchlist`, { grade: g }).catch(() => {});
  };
  const gradeColor = grade ? sc(grade) : T.muted;
  const isDefault = grade === "고정" || grade === "회수의문";
  const covViolation = covenants.some(c => sc(c.status) === T.red || c.breach);
  const ateDetected = ate?.detected || ate?.status === "감지";
  const overdue = payments?.overdue || payments?.dpd > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* ── 딜 헤더 ── */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>{dash(D.deal_name)}</span>
          <Tag label={D.deal_type || "DIRECT LENDING"} color={T.gold} />
          <Pill label="포트폴리오 편입" color={T.green} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>
            집행 {dash(D.exec_date)} · 경과 {dash(D.elapsed)} · 만기 D-{dash(D.maturity_dday)} · 담당 {dash(D.owner)}
          </span>
        </div>
      </div>

      {/* ── 본문 ── */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>

        {/* 좌측 */}
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 섹션 A */}
          <SectionHeader n="A" name="PORTFOLIO MONITORING" desc="원리금 · 재무 · Watchlist · Covenant · 회수" />

          {/* ① 원리금 납입 */}
          <StepCard icon={overdue ? "active" : "done"} title="① 원리금 납입 모니터링" tags={HERMES}
            right={overdue ? <Pill label="연체 발생" color={T.red} /> : <Pill label="정상 납입" color={T.green} />}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              <Cell k="납입일" v={payments.next_date} />
              <Cell k="납입 예정액" v={payments.next_amount} />
              <Cell k="연체 여부" v={overdue ? `연체 ${dash(payments.dpd)}일` : "없음"} color={overdue ? T.red : T.green} />
            </div>
            {overdue && <div style={{ marginTop: 10, padding: "8px 12px", background: "#1A0808", border: `1px solid ${T.red}44`, borderRadius: 4, fontSize: 11, color: T.red }}>⚠ 연체 발생 — 즉시 검토 필요</div>}
          </StepCard>

          {/* ② 재무 상태 */}
          <StepCard title="② 재무 상태 업데이트" tags={HERMES} right={<span style={{ fontSize: 9, color: T.muted }}>분기 자동 갱신</span>}>
            <Row k="DART 공시 변동" v={fin.dart} />
            <Row k="ECOS / KOSIS 매크로" v={fin.macro} />
          </StepCard>

          {/* ③ Watchlist 등급 */}
          <StepCard icon={isDefault ? "active" : "pending"} title="③ Watchlist 등급 관리"
            right={grade ? <Pill label={grade} color={gradeColor} /> : undefined}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {WATCH_GRADES.map(([g, c]) => {
                const on = grade === g;
                return (
                  <button key={g} onClick={() => setWatch(g)} style={{
                    flex: 1, minWidth: 70, padding: "8px 6px", fontSize: 11, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                    color: on ? "#080C14" : c, background: on ? c : "transparent", border: `1px solid ${c}`,
                  }}>{g}</button>
                );
              })}
            </div>
          </StepCard>

          {/* ④ Watchlist → LP 알림 */}
          <StepCard icon={lpNotify ? "active" : "pending"} title="④ Watchlist → LP 알림 규칙">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 11, color: T.muted }}>요주의 이상 시 LP 보고</span>
              <button onClick={() => setLpNotify(v => !v)} style={{
                marginLeft: "auto", padding: "5px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                color: lpNotify ? "#080C14" : T.muted, background: lpNotify ? T.gold : "transparent", border: `1px solid ${lpNotify ? T.gold : T.border}`,
              }}>{lpNotify ? "ON" : "OFF"}</button>
            </div>
            {lpNotify && <div style={{ marginTop: 8, fontSize: 10, color: T.blue }}>→ 6페이지 보고서 자동 반영</div>}
          </StepCard>

          {/* ⑤ Covenant 감시 */}
          <StepCard icon={covViolation ? "active" : "pending"} title="⑤ Covenant 감시" tags={AUTO}
            right={covViolation ? <Pill label="위반" color={T.red} /> : undefined}>
            {covenants.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                  <span>항목</span><span>현재값</span><span>기준</span><span>Headroom</span><span>Next Test</span>
                </div>
                {covenants.map((c: any, i: number) => {
                  const danger = sc(c.status) === T.red || c.breach;
                  const warn = c.headroom_warn || sc(c.status) === T.yellow;
                  const col = danger ? T.red : warn ? T.yellow : T.text;
                  return (
                    <div key={i} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono, color: col }}>
                      <span style={{ fontFamily: T.font }}>{dash(c.name)}</span>
                      <span>{dash(c.value)}</span><span>{dash(c.threshold)}</span>
                      <span>{dash(c.headroom)}</span><span>{dash(c.next_test)}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {covViolation && <button style={{ marginTop: 10, padding: "7px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.red, border: `1px solid ${T.red}`, borderRadius: 4 }}>Waiver 요청</button>}
          </StepCard>

          {/* ⑥ Restructuring */}
          <StepCard icon={covViolation ? "active" : "pending"} blocked={!covViolation} title="⑥ Restructuring 워크플로우">
            <div style={{ display: "flex", gap: 8 }}>
              {["만기 연장", "금리 조정", "워크아웃"].map(o => (
                <span key={o} style={{ flex: 1, textAlign: "center", padding: "8px", fontSize: 11, color: T.muted, border: `1px solid ${T.border}`, borderRadius: 4 }}>{o}</span>
              ))}
            </div>
          </StepCard>

          {/* ⑦ Portfolio 집중도 */}
          <StepCard title="⑦ Portfolio 집중도" tags={HEPH}>
            <div style={{ marginBottom: 10 }}>
              {(conc.sectors || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>섹터별 분포 —</div> : (conc.sectors || []).map((s: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0" }}>
                  <span style={{ fontSize: 10, width: 90, color: T.muted }}>{dash(s.name)}</span>
                  <div style={{ flex: 1, height: 6, background: T.border, borderRadius: 3, overflow: "hidden" }}>
                    <div style={{ width: `${s.pct || 0}%`, height: "100%", background: T.blue }} />
                  </div>
                  <span style={{ fontSize: 10, fontFamily: T.mono, color: T.text, width: 40, textAlign: "right" }}>{s.pct != null ? `${s.pct}%` : "—"}</span>
                </div>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <Cell k="LTV 분포" v={conc.ltv} /><Cell k="만기 Ladder" v={conc.maturity_ladder} /><Cell k="Vintage" v={conc.vintage} />
            </div>
          </StepCard>

          {/* ⑧ Lifecycle Story */}
          <StepCard title="⑧ Lifecycle Story" tags={AUTO}>
            <div style={{ display: "flex", alignItems: "center", gap: 4, flexWrap: "wrap" }}>
              {(D.lifecycle || ["SDD", "IC", "Closing", "집행", "현재"]).map((ev: any, i: number, arr: any[]) => {
                const cur = i === arr.length - 1;
                const name = typeof ev === "string" ? ev : ev?.name;
                return (
                  <React.Fragment key={i}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                      <span style={{ width: 9, height: 9, borderRadius: "50%", background: cur ? T.gold : T.green }} />
                      <span style={{ fontSize: 9, color: cur ? T.gold : T.muted }}>{dash(name)}</span>
                    </div>
                    {i < arr.length - 1 && <span style={{ flex: 1, minWidth: 16, height: 1, background: T.border }} />}
                  </React.Fragment>
                );
              })}
            </div>
            <div style={{ marginTop: 8, fontSize: 10, color: T.blue }}>→ 5/6페이지 성과 보고 자동 활용</div>
          </StepCard>

          {/* ⑨ 부실 → 회수 전략 */}
          <StepCard icon={isDefault ? "active" : "pending"} blocked={!isDefault} title="⑨ 부실 → 회수 전략">
            <div style={{ fontSize: 11, color: T.muted }}>Recovery Strategy Engine: {dash(recovery.recommendation)}</div>
          </StepCard>

          {/* ⑩ 회수 완료 */}
          <StepCard icon="pending" blocked={!isDefault} title="⑩ 회수 완료">
            <button disabled={!isDefault} style={{
              padding: "8px 14px", fontSize: 11, cursor: isDefault ? "pointer" : "default", fontFamily: T.font, borderRadius: 4,
              background: isDefault ? T.gold : "transparent", color: isDefault ? "#080C14" : T.muted, border: isDefault ? "none" : `1px solid ${T.border}`,
            }}>회수 완료 처리</button>
            <div style={{ marginTop: 8, fontSize: 10, color: T.blue }}>→ 8페이지 Recycling 업데이트 · 6페이지 LP 분배</div>
          </StepCard>

          {/* 섹션 B */}
          <SectionHeader n="B" name="COLLATERAL SERVICING" desc="담보 · Perfection · 재평가 · ATE · Margin Call" />

          {/* ⑪ 담보 적격성 */}
          <StepCard title="⑪ 담보 적격성 (Eligibility Rules)">
            {(collateral.items || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : (collateral.items || []).map((c: any, i: number) => (
              <Row key={i} k={dash(c.type)} v={c.haircut != null ? `Haircut ${c.haircut}%` : "—"} />
            ))}
          </StepCard>

          {/* ⑫ Perfection Status Tracker */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <StepIcon kind="pending" />
              <span>⑫ Perfection Status Tracker</span>
              {AUTO}
              <Refresh onClick={() => loadCollateral(selId)} ts={ts.col || ""} />
            </div>
            <div style={{ marginLeft: 30, marginTop: 8 }}>
              {(perfection.length ? perfection : [{ name: "등기 상태" }, { name: "선순위 지위" }, { name: "Control Account" }]).map((p: any, i: number) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 11, color: T.muted }}>{dash(p.name)}</span>
                  <span style={{ fontSize: 11, color: sc(p.status) }}>{dash(p.status)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* ⑬ Revaluation Calendar */}
          <StepCard title="⑬ Revaluation Calendar" tags={MOLIT}
            right={<span style={{ fontFamily: T.mono, fontSize: 12, color: T.text }}>LTV {dash(reval.ltv)} {trendArrow(reval.trend)}</span>}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 8 }}>
              <Cell k="다음 재평가" v={reval.next_date} /><Cell k="D-day" v={reval.dday != null ? `D-${reval.dday}` : "—"} />
            </div>
            <button style={{ padding: "7px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4 }}>재평가 트리거</button>
          </StepCard>

          {/* ⑭ Control Account / Cash Sweep */}
          <StepCard title="⑭ Control Account / Cash Sweep Monitor">
            <Row k="담보 연계 현금흐름" v={control.cash_flow} />
            <Row k="Sweep 잔액" v={control.balance} />
          </StepCard>

          {/* ⑮ ATE 트리거 */}
          <StepCard icon={ateDetected ? "active" : "pending"} title="⑮ ATE 트리거" tags={AUTO}
            right={ateDetected ? <Pill label="감지" color={T.yellow} /> : <Pill label="이상 없음" color={T.green} />}>
            {["경영진 교체", "평판 악화", "마진콜"].map(k => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.muted }}>{k}</span>
                <span style={{ fontSize: 11, color: ate?.[k] ? T.yellow : T.green }}>{ate?.[k] ? "감지" : "정상"}</span>
              </div>
            ))}
          </StepCard>

          {/* ⑯ Margin Call */}
          <StepCard icon={ateDetected ? "active" : "pending"} blocked={!ateDetected} title="⑯ Margin Call / 추가담보">
            <div style={{ display: "flex", gap: 8 }}>
              {["담보 대체", "Custody", "Escrow"].map(o => (
                <span key={o} style={{ flex: 1, textAlign: "center", padding: "8px", fontSize: 11, color: T.muted, border: `1px solid ${T.border}`, borderRadius: 4 }}>{o}</span>
              ))}
            </div>
          </StepCard>

          {/* ⑰ Release / 집행 이력 */}
          <StepCard icon="pending" blocked title="⑰ Release / 집행 이력">
            <div style={{ fontSize: 11, color: T.muted }}>담보 해제 · 강제집행 기록 —</div>
          </StepCard>
        </div>

        {/* 우측: Live Risk Snapshot (sticky) */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <span style={{ ...labelStyle, color: T.gold }}>Live Risk Snapshot</span>
          </div>

          {/* Deal Health */}
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={labelStyle}>Deal Health</span><Refresh onClick={() => loadHealth(selId)} ts={ts.health || ""} />
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
              <Pill label={grade || "—"} color={gradeColor} />
              <Pill label={isDefault ? "Danger" : grade && grade !== "정상" ? "Warning" : "Stable"} color={isDefault ? T.red : grade && grade !== "정상" ? T.yellow : T.green} />
            </div>
            <Row k="연체" v={overdue ? "연체" : "없음"} color={overdue ? T.red : T.green} />
            <Row k="DPD" v={payments.dpd} />
            <Row k="최근 납입" v={payments.last_date} />
            <Row k="30일 추세" v={payments.trend_30d} />
          </div>

          {/* Collateral */}
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={labelStyle}>Collateral</span><Refresh onClick={() => loadCollateral(selId)} ts={ts.col || ""} />
            </div>
            <Row k="LTV" v={reval.ltv != null ? `${reval.ltv} ${trendArrow(reval.trend)}` : null} />
            <Row k="Perfection" v={collateral.perfection} />
            <Row k="선순위" v={collateral.seniority} />
            <Row k="Control Account" v={control.status} />
            <Row k="Next Valuation" v={reval.next_date} />
          </div>

          {/* Covenants */}
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
              <span style={labelStyle}>Covenants</span><Refresh onClick={() => loadCovenants(selId)} ts={ts.cov || ""} />
            </div>
            <Row k="위반 여부" v={covViolation ? "위반" : "정상"} color={covViolation ? T.red : T.green} />
            <Row k="DSCR Headroom" v={covenants.find(c => /DSCR/i.test(c.name || ""))?.headroom} color={covenants.find(c => /DSCR/i.test(c.name || ""))?.headroom_warn ? T.yellow : undefined} />
            <Row k="Next Test" v={covenants[0]?.next_test} />
            <Row k="모니터링 항목" v={covenants.length || null} />
            <Row k="Waiver" v={covenants.some(c => c.waiver) ? "있음" : "없음"} />
          </div>

          {/* Recovery */}
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Recovery</span></div>
            <Row k="Restructuring" v={recovery.restructuring_status} />
            <Row k="Open Waiver" v={recovery.open_waiver} />
            <Row k="Legal Action" v={recovery.legal_action} />
          </div>

          {/* Portfolio Context */}
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Portfolio Context</span></div>
            <Row k="섹터 최대" v={conc.top_sector} />
            <Row k="펀드 평균 LTV 대비" v={conc.ltv_vs_avg} />
            <Row k="만기 버킷" v={conc.maturity_bucket} />
            <Row k="Concentration Impact" v={conc.impact} />
          </div>

          {/* Quick Actions */}
          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[
              ["Watchlist 등급 변경", T.gold], ["Covenant Waiver 요청", T.gold], ["담보 재평가 트리거", T.gold],
              ["Margin Call 생성", T.red], ["Recovery Review 시작", T.red], ["LP 보고 반영 (6P)", T.blue],
            ].map(([label, color]) => (
              <button key={label as string} style={{
                width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font,
                background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4,
              }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
