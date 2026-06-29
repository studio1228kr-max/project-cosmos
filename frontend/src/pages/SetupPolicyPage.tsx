import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (동일) ─────────────────────
const T = {
  bg: "#080C14", surface1: "#0D1826", warn: "#1A140A",
  gold: "#C9A84C", blue: "#4A90D9", green: "#2ACA70", yellow: "#F59E0B", red: "#FF5555",
  text: "#E2E8F0", muted: "#4A6080", border: "#1A2332",
  font: "'Goldman Sans', sans-serif", mono: "'IBM Plex Mono', ui-monospace, monospace",
};
const dash = (v: any) => (v === null || v === undefined || v === "") ? "—" : v;
const nowStr = () => new Date().toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };
const EditBtn = () => (
  <button style={{ fontSize: 10, padding: "3px 10px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 3 }}>편집</button>
);
const AutoRef = ({ children }: { children: React.ReactNode }) => (
  <span style={{ fontSize: 9, color: T.blue }}>→ {children}</span>
);
function Toggle({ on, onClick }: { on: boolean; onClick?: () => void }) {
  return (
    <span onClick={onClick} style={{ width: 32, height: 16, borderRadius: 8, background: on ? T.gold : T.border, position: "relative", cursor: "pointer", flexShrink: 0, transition: "background .15s" }}>
      <span style={{ position: "absolute", top: 2, left: on ? 18 : 2, width: 12, height: 12, borderRadius: "50%", background: on ? "#080C14" : T.muted, transition: "left .15s" }} />
    </span>
  );
}
function SectionHeader({ name, desc, auto }: { name: string; desc?: string; auto?: React.ReactNode }) {
  return (
    <div style={{ background: "#060A11", borderTop: "2px solid #1A2235", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 10, color: "#8A9BB5", letterSpacing: "0.08em" }}>{name}</span>
      {desc && <span style={{ fontSize: 8, color: "#3A4A62" }}>{desc}</span>}
      {auto && <span style={{ marginLeft: "auto" }}>{auto}</span>}
    </div>
  );
}
const Block: React.FC<{ children: React.ReactNode; dim?: boolean }> = ({ children, dim }) => (
  <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, opacity: dim ? 0.35 : 1 }}>{children}</div>
);
const FieldRow = ({ k, v, edit = true, auto }: { k: string; v: any; edit?: boolean; auto?: React.ReactNode }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: `1px solid ${T.border}` }}>
    <span style={{ fontSize: 11, color: T.muted, width: 140 }}>{k}</span>
    <span style={{ fontSize: 12, fontFamily: T.mono, color: v != null ? T.text : T.muted, flex: 1 }}>{dash(v)}</span>
    {auto}
    {edit && <EditBtn />}
  </div>
);
const ListItem = ({ children, on, onToggle, toggle }: { children: React.ReactNode; on?: boolean; onToggle?: () => void; toggle?: boolean }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: `1px solid ${T.border}` }}>
    {toggle && <Toggle on={!!on} onClick={onToggle} />}
    <span style={{ fontSize: 12, color: on === false ? T.muted : T.text, flex: 1 }}>{children}</span>
  </div>
);
const TABS = ["Deal & Product", "Fund & Vehicle", "Counterparty", "Rules & Thresholds", "System"];
const DEAL_TYPES = ["Direct Lending", "Debt Purchase", "Structured", "Distressed", "Equity-Linked"];
const IC_SECTIONS = Array.from({ length: 11 }, (_, i) => `S${i + 1}`);

export default function SetupPolicyPage({ deals = [] }: { deals?: any[] }) {
  const [tab, setTab] = useState(0);
  const [dealTypes, setDealTypes] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any>({});
  const [gates, setGates] = useState<any>({});
  const [fund, setFund] = useState<any>({});
  const [feeRules, setFeeRules] = useState<any>({});
  const [collateral, setCollateral] = useState<any[]>([]);
  const [ras, setRas] = useState<any[]>([]);
  const [covLib, setCovLib] = useState<any[]>([]);
  const [sla, setSla] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [changeLog, setChangeLog] = useState<any[]>([]);
  // 로컬 토글 상태
  const [typeOn, setTypeOn] = useState<Record<string, boolean>>(Object.fromEntries(DEAL_TYPES.map(t => [t, true])));
  const [icOn, setIcOn] = useState<Record<string, boolean>>(Object.fromEntries(IC_SECTIONS.map(s => [s, true])));
  const [feeBasis, setFeeBasis] = useState<"commitment" | "nav">("commitment");
  const [sources, setSources] = useState<Record<string, boolean>>({ DART: true, ECOS: true, KOSIS: true, "Grok X": true });
  const lastEdit = nowStr();

  const load = useCallback(() => {
    API.get(`/api/setup/deal-types`).then(r => setDealTypes(r.data?.items || r.data || [])).catch(() => setDealTypes([]));
    API.get(`/api/setup/policy-templates`).then(r => setTemplates(r.data || {})).catch(() => setTemplates({}));
    API.get(`/api/setup/gate-thresholds`).then(r => setGates(r.data || {})).catch(() => setGates({}));
    API.get(`/api/setup/fund-structure`).then(r => setFund(r.data || {})).catch(() => setFund({}));
    API.get(`/api/setup/fee-rules`).then(r => setFeeRules(r.data || {})).catch(() => setFeeRules({}));
    API.get(`/api/setup/collateral-master`).then(r => setCollateral(r.data?.items || r.data || [])).catch(() => setCollateral([]));
    API.get(`/api/setup/ras-limits`).then(r => setRas(r.data?.items || r.data || [])).catch(() => setRas([]));
    API.get(`/api/setup/covenant-library`).then(r => setCovLib(r.data?.items || r.data || [])).catch(() => setCovLib([]));
    API.get(`/api/setup/sla-rules`).then(r => setSla(r.data?.items || r.data || [])).catch(() => setSla([]));
    API.get(`/api/setup/user-roles`).then(r => setRoles(r.data?.items || r.data || [])).catch(() => setRoles([]));
    API.get(`/api/governance/policy-log`).then(r => setChangeLog(r.data?.items || r.data || [])).catch(() => setChangeLog([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const tmplItems = (type: string) => (templates[type] || templates[type?.toLowerCase()] || []);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* 헤더 */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>Setup &amp; Policy</span>
          <span style={{ fontSize: 9, color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3, padding: "1px 6px" }}>기준정보 중앙관리</span>
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>마지막 수정 {lastEdit} · <span style={{ color: T.blue }}>변경 시 전 페이지 자동 반영</span></span>
        </div>
      </div>

      {/* 탭 바 */}
      <div style={{ display: "flex", borderBottom: `1px solid ${T.border}`, flexShrink: 0, padding: "0 12px" }}>
        {TABS.map((t, i) => (
          <button key={t} onClick={() => setTab(i)} style={{
            padding: "10px 14px", fontSize: 12, cursor: "pointer", fontFamily: T.font, background: "transparent", border: "none",
            color: tab === i ? T.gold : T.muted, borderBottom: tab === i ? `2px solid ${T.gold}` : "2px solid transparent",
          }}>{t}</button>
        ))}
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 탭1: Deal & Product */}
          {tab === 0 && <>
            <SectionHeader name="딜 타입 MASTER" desc="5개 타입" />
            <Block>
              {(dealTypes.length ? dealTypes.map((d: any) => d.name) : DEAL_TYPES).map((name: string) => (
                <div key={name} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: `1px solid ${T.border}` }}>
                  <Toggle on={typeOn[name] ?? true} onClick={() => setTypeOn(s => ({ ...s, [name]: !(s[name] ?? true) }))} />
                  <span style={{ fontSize: 12, color: (typeOn[name] ?? true) ? T.text : T.muted, flex: 1 }}>{name}</span>
                  <EditBtn />
                </div>
              ))}
            </Block>
            <SectionHeader name="POLICY TEMPLATE 관리" auto={<AutoRef>2페이지 자동 반영</AutoRef>} />
            <Block>
              {DEAL_TYPES.filter(t => typeOn[t]).map(type => (
                <div key={type} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 10, color: T.gold, marginBottom: 4 }}>{type}</div>
                  {(tmplItems(type).length ? tmplItems(type) : ["체크리스트 항목 —"]).map((it: any, i: number) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                      <span style={{ fontSize: 11, color: T.muted, flex: 1 }}>· {typeof it === "string" ? it : dash(it.name)}</span>
                      <span style={{ fontSize: 10, color: T.muted, cursor: "pointer" }}>↑↓ ✕</span>
                    </div>
                  ))}
                  <button style={{ marginTop: 4, fontSize: 10, padding: "3px 10px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>+ 항목 추가</button>
                </div>
              ))}
            </Block>
            <SectionHeader name="게이트 기준값" />
            <Block>
              <FieldRow k="LTV 한도" v={gates.ltv_limit} />
              <FieldRow k="DSCR 최소" v={gates.dscr_min} />
              <FieldRow k="IRR 기준" v={gates.irr_min} />
              <FieldRow k="Narrative 기준" v={gates.narrative_min} />
            </Block>
            <SectionHeader name="IC MEMO 섹션 구성" desc="S1~S11 · 타입별 커스텀" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                {IC_SECTIONS.map(s => (
                  <div key={s} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0" }}>
                    <Toggle on={icOn[s]} onClick={() => setIcOn(st => ({ ...st, [s]: !st[s] }))} />
                    <span style={{ fontSize: 11, color: icOn[s] ? T.text : T.muted }}>{s}</span>
                  </div>
                ))}
              </div>
            </Block>
          </>}

          {/* 탭2: Fund & Vehicle */}
          {tab === 1 && <>
            <SectionHeader name="펀드 구조 정의" />
            <Block>
              <FieldRow k="펀드명" v={fund.name} />
              <FieldRow k="설립일" v={fund.inception} />
              <FieldRow k="만기" v={fund.maturity} />
              <FieldRow k="전략" v={fund.strategy} />
              <FieldRow k="통화" v={fund.currency} />
            </Block>
            <SectionHeader name="SPC 템플릿" desc="딜바이딜 표준 구조" />
            <Block>
              <FieldRow k="등기 형태" v={fund.spc_form} />
              <FieldRow k="자본금 기준" v={fund.spc_capital} />
            </Block>
            <SectionHeader name="FEE & WATERFALL RULES" auto={<AutoRef>5페이지 자동 반영</AutoRef>} />
            <Block>
              <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.muted, width: 140 }}>Management Fee</span>
                <div style={{ display: "flex", gap: 6, flex: 1 }}>
                  {([["commitment", "약정액 기준"], ["nav", "운용액 기준"]] as const).map(([k, label]) => (
                    <button key={k} onClick={() => setFeeBasis(k)} style={{
                      padding: "5px 10px", fontSize: 11, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                      color: feeBasis === k ? "#080C14" : T.muted, background: feeBasis === k ? T.gold : "transparent", border: `1px solid ${feeBasis === k ? T.gold : T.border}`,
                    }}>{label}</button>
                  ))}
                </div>
              </div>
              <FieldRow k="Hurdle Rate" v={feeRules.hurdle} />
              <FieldRow k="Carry %" v={feeRules.carry} />
              <FieldRow k="Catch-up" v={feeRules.catchup} />
            </Block>
            <SectionHeader name="LPA 기준 RECYCLING 조건" />
            <Block>
              <FieldRow k="재투자 가능 조건" v={fund.recycling_condition} />
              <FieldRow k="기간 제한" v={fund.recycling_period} />
            </Block>
          </>}

          {/* 탭3: Counterparty */}
          {tab === 2 && <>
            <SectionHeader name="LP 기관 템플릿" />
            <Block>
              <FieldRow k="표준 약정서" v={fund.lp_agreement_template} />
              <FieldRow k="KYC 요구사항" v={fund.kyc_requirements} />
            </Block>
            <SectionHeader name="브로커 마스터" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 1fr 0.6fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>브로커</span><span>수수료율</span><span>계약 기간</span><span></span>
              </div>
              {(fund.brokers || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : (fund.brokers || []).map((b: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 1fr 0.6fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center", fontFamily: T.mono }}>
                  <span style={{ fontFamily: T.font }}>{dash(b.name)}</span><span>{dash(b.fee_rate)}</span><span>{dash(b.contract)}</span><EditBtn />
                </div>
              ))}
              <button style={{ marginTop: 8, fontSize: 10, padding: "3px 10px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>+ 브로커 등록</button>
            </Block>
            <SectionHeader name="담보 유형 MASTER" desc="Haircut · Margining Framework" auto={<AutoRef>4페이지 자동 반영</AutoRef>} />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1.6fr 0.8fr 1.4fr 0.6fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>담보 유형</span><span>Haircut</span><span>Margining</span><span></span>
              </div>
              {(collateral.length ? collateral : [{ type: "부동산" }, { type: "유가증권" }, { type: "매출채권" }]).map((c: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.6fr 0.8fr 1.4fr 0.6fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span>{dash(c.type)}</span>
                  <span style={{ fontFamily: T.mono }}>{c.haircut != null ? `${c.haircut}%` : "—"}</span>
                  <span style={{ fontFamily: T.mono, color: T.muted }}>{dash(c.margining)}</span><EditBtn />
                </div>
              ))}
            </Block>
          </>}

          {/* 탭4: Rules & Thresholds */}
          {tab === 3 && <>
            <SectionHeader name="RAS 한도 설정" auto={<AutoRef>7페이지 RAS 자동 반영</AutoRef>} />
            <Block>
              {(ras.length ? ras : [{ name: "섹터 집중도" }, { name: "단일 차주 한도" }, { name: "평균 LTV" }]).map((r: any, i: number) => (
                <FieldRow key={i} k={dash(r.name)} v={r.limit} />
              ))}
            </Block>
            <SectionHeader name="ALERT 임계치" desc="1페이지 Alert 발동 기준" />
            <Block>
              <FieldRow k="DSCR" v={gates.alert_dscr} />
              <FieldRow k="LTV" v={gates.alert_ltv} />
              <FieldRow k="연체" v={gates.alert_overdue} />
              <FieldRow k="집중도" v={gates.alert_concentration} />
            </Block>
            <SectionHeader name="COVENANT LIBRARY" desc="딜 등록 시 타입별 자동 로딩" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 0.6fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>Covenant</span><span>기준값</span><span>테스트 주기</span><span></span>
              </div>
              {(covLib.length ? covLib : [{ name: "DSCR 유지" }, { name: "Net Leverage" }, { name: "Min Liquidity" }]).map((c: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr 1fr 0.6fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span>{dash(c.name)}</span>
                  <span style={{ fontFamily: T.mono }}>{dash(c.threshold)}</span>
                  <span style={{ fontFamily: T.mono, color: T.muted }}>{dash(c.frequency)}</span><EditBtn />
                </div>
              ))}
              <div style={{ marginTop: 6, fontSize: 9, color: T.blue }}>→ 3/4페이지 Covenant 항목 반영</div>
            </Block>
            <SectionHeader name="SLA 기준 기한" auto={<AutoRef>7페이지 SLA Monitor 자동 반영</AutoRef>} />
            <Block>
              {(sla.length ? sla : [{ name: "DD 완료 기한" }, { name: "LP 응답 기한" }, { name: "STR 제출 기한" }, { name: "FSC 보고 기한" }]).map((s: any, i: number) => (
                <FieldRow key={i} k={dash(s.name)} v={s.threshold} />
              ))}
            </Block>
            <SectionHeader name="4-EYES 승인 기준" />
            <Block>
              <FieldRow k="금액 기준" v={gates.four_eyes_amount} />
              <div style={{ fontSize: 10, color: T.muted, marginTop: 6 }}>적용 대상: 자금 집행 · Override 승인 · Waiver 승인</div>
            </Block>
          </>}

          {/* 탭5: System */}
          {tab === 4 && <>
            <SectionHeader name="USER ROLES & APPROVAL MATRIX" auto={<AutoRef>7페이지 RBAC 자동 반영</AutoRef>} />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr 1fr 0.6fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>역할</span><span>접근 페이지</span><span>편집 권한</span><span>승인 권한</span><span></span>
              </div>
              {(roles.length ? roles : [{ role: "GP" }, { role: "외부법무" }, { role: "회계" }, { role: "IR" }]).map((r: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1fr 1.4fr 1fr 1fr 0.6fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span style={{ color: T.text }}>{dash(r.role)}</span>
                  <span style={{ color: T.muted }}>{dash(r.pages)}</span>
                  <span style={{ color: T.muted }}>{dash(r.edit)}</span>
                  <span style={{ color: T.muted }}>{dash(r.approve)}</span><EditBtn />
                </div>
              ))}
            </Block>
            <SectionHeader name="보고서 템플릿" />
            <Block>
              <FieldRow k="QR 보고서 포맷" v={fund.qr_template} />
              <FieldRow k="LP별 커스텀" v={fund.lp_custom_template} />
              <FieldRow k="감사 보고서 포맷" v={fund.audit_template} />
            </Block>
            <SectionHeader name="AI 모델 파라미터 기본값" desc="변경은 7페이지 Model Registry에서" />
            <Block dim>
              {["Merton KMV", "ECL", "Concentration", "Sourcing Agent"].map(m => (
                <FieldRow key={m} k={m} v={null} edit={false} />
              ))}
            </Block>
            <SectionHeader name="HERMES 수집 스케줄" />
            <Block>
              <FieldRow k="자동 실행 시각" v={fund.hermes_schedule || "04:00 KST"} />
              <div style={{ marginTop: 8, fontSize: 10, color: T.muted, marginBottom: 4 }}>수집 대상 소스</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                {Object.keys(sources).map(s => (
                  <div key={s} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0" }}>
                    <Toggle on={sources[s]} onClick={() => setSources(st => ({ ...st, [s]: !st[s] }))} />
                    <span style={{ fontSize: 11, color: sources[s] ? T.text : T.muted }}>{s}</span>
                  </div>
                ))}
              </div>
            </Block>
          </>}
        </div>

        {/* 우측 sticky: Change Log */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}><span style={{ ...labelStyle, color: T.gold }}>Change Log</span></div>

          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>최근 변경 이력</span><span style={{ fontSize: 8, color: T.muted, marginLeft: 6 }}>7P Policy Log 연동</span></div>
            {changeLog.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : changeLog.slice(0, 8).map((c: any, i: number) => (
              <div key={i} style={{ padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ fontSize: 11, color: T.text }}>{dash(c.name)}</span>
                  <span style={{ fontSize: 9, color: T.muted, fontFamily: T.mono }}>{dash(c.at)}</span>
                </div>
                <div style={{ fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(c.before)} → {dash(c.after)}</div>
                <div style={{ fontSize: 9, color: T.muted }}>{dash(c.actor)}</div>
              </div>
            ))}
          </div>

          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>영향 받는 페이지</span></div>
            <div style={{ fontSize: 10, color: T.muted, lineHeight: 1.8 }}>
              <div>· Deal Template → <span style={{ color: T.blue }}>2P</span></div>
              <div>· RAS 임계치 → <span style={{ color: T.blue }}>1P · 7P</span></div>
              <div>· Covenant Library → <span style={{ color: T.blue }}>3P · 4P</span></div>
              <div>· Fee Rules → <span style={{ color: T.blue }}>5P</span></div>
              <div>· User Roles → <span style={{ color: T.blue }}>7P</span></div>
              <div>· 모든 변경 → <span style={{ color: T.blue }}>7P Policy Log</span></div>
            </div>
          </div>

          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[["전체 설정 Export (JSON)", T.gold], ["설정 Import", T.text], ["기본값 복원", T.text], ["변경 이력 전체 (7P)", T.blue]].map(([label, color]) => (
              <button key={label as string} style={{ width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4 }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
