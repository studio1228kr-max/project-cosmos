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
const nowStr = () => new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };
const SC: Record<string, string> = {
  완료: T.green, FINAL: T.green, SYNCED: T.green, 동기화: T.green, 해소: T.green,
  "UNDER REVIEW": T.yellow, 검토중: T.yellow, PENDING: T.yellow, 대기: T.yellow, "대기 중": T.yellow, DRAFT: T.muted,
  미해소: T.red, BREAK: T.red, 불일치: T.red,
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
const Cell = ({ k, v, color }: { k: string; v: any; color?: string }) => (
  <div style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
    <div style={{ fontSize: 9, color: T.muted }}>{k}</div>
    <div style={{ fontSize: 13, fontFamily: T.mono, color: color || (v != null ? T.text : T.muted), marginTop: 4 }}>{dash(v)}</div>
  </div>
);
function SectionHeader({ name, desc, tag }: { name: string; desc?: string; tag?: React.ReactNode }) {
  return (
    <div style={{ background: "#060A11", borderTop: "2px solid #1A2235", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 10, color: "#8A9BB5", letterSpacing: "0.08em" }}>{name}</span>
      {tag}
      {desc && <span style={{ fontSize: 8, color: "#3A4A62" }}>{desc}</span>}
    </div>
  );
}
const Block: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>{children}</div>
);
const AUTO = <Tag label="AUTO" color={T.blue} />;
const HEPH = <Tag label="HEPHAESTUS AUTO" color={T.blue} />;
const TABS = ["Fund Close", "NAV·P&L", "Capital Accounts", "Subledger", "Tax·Audit"];

export default function FundAccountingPage({ deals = [] }: { deals?: any[] }) {
  const [tab, setTab] = useState(0);
  const [nav, setNav] = useState<any>({});
  const [pnl, setPnl] = useState<any>({});
  const [waterfall, setWaterfall] = useState<any>({});
  const [capital, setCapital] = useState<any[]>([]);
  const [loanEvents, setLoanEvents] = useState<any[]>([]);
  const [recon, setRecon] = useState<any>({});
  const [breaks, setBreaks] = useState<any[]>([]);
  const [gl, setGl] = useState<any[]>([]);
  const [lock, setLock] = useState<{ month: boolean; quarter: boolean }>({ month: false, quarter: false });
  const [ts, setTs] = useState<Record<string, string>>({});
  const stamp = (k: string) => setTs(p => ({ ...p, [k]: nowStr() }));

  const loadNav = useCallback(() => {
    API.get(`/api/fund/nav`).then(r => setNav(r.data || {})).catch(() => setNav({}));
    API.get(`/api/fund/pnl`).then(r => setPnl(r.data || {})).catch(() => setPnl({}));
    stamp("nav");
  }, []);
  const loadRecon = useCallback(() => {
    API.get(`/api/fund/reconciliation`).then(r => setRecon(r.data || {})).catch(() => setRecon({}));
    API.get(`/api/fund/reconciliation-breaks`).then(r => setBreaks(r.data?.breaks || r.data || [])).catch(() => setBreaks([]));
    API.get(`/api/fund/gl-status`).then(r => setGl(r.data?.items || r.data || [])).catch(() => setGl([]));
    stamp("recon");
  }, []);
  useEffect(() => {
    loadNav(); loadRecon();
    API.get(`/api/fund/waterfall`).then(r => setWaterfall(r.data || {})).catch(() => setWaterfall({}));
    API.get(`/api/fund/capital-accounts`).then(r => setCapital(r.data?.accounts || r.data || [])).catch(() => setCapital([]));
    API.get(`/api/fund/loan-events`).then(r => setLoanEvents(r.data?.events || r.data || [])).catch(() => setLoanEvents([]));
    stamp("close");
  }, [loadNav, loadRecon]);

  const navStatus = nav.status || "Draft";
  const variance = nav.variance;
  const varianceFlag = nav.variance_pct != null && Math.abs(nav.variance_pct) > 0;
  const breakDot = (days?: number) => days == null ? T.muted : days > 7 ? T.red : days >= 3 ? T.yellow : T.muted;

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* 헤더 */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>{dash(nav.fund_name || "COSMOS Fund I")}</span>
          <Tag label="딜바이딜 구조" color={T.gold} /><Tag label="2026 Q2" color={T.blue} /><Pill label="Close 진행 중" color={T.yellow} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>기준일 2026.06.30 · 분기말 D-1</span>
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

      {/* 본문 */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 탭1: Fund Close */}
          {tab === 0 && <>
            <SectionHeader name="SIGN-OFF 현황" />
            <Block>
              {[["Preparer (COSMOS 자동)", "완료"], ["Reviewer", "대기 중"], ["GP Sign-off (민우)", "대기 중"]].map(([k, s]) => (
                <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 12, color: T.text }}>{k}</span><Pill label={s} color={sc(s)} />
                </div>
              ))}
            </Block>
            <SectionHeader name="CUT-OFF CONTROL" />
            <Block>
              <div style={{ display: "flex", gap: 10 }}>
                {(["month", "quarter"] as const).map(p => (
                  <button key={p} onClick={() => setLock(l => ({ ...l, [p]: !l[p] }))} style={{
                    flex: 1, padding: "10px", fontSize: 12, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                    color: lock[p] ? "#080C14" : T.gold, background: lock[p] ? T.gold : "transparent", border: `1px solid ${T.gold}`,
                  }}>{lock[p] ? "🔒 " : ""}{p === "month" ? "월말 잠금" : "분기말 잠금"}</button>
                ))}
              </div>
            </Block>
            <SectionHeader name="CLOSE 체크리스트" />
            <Block>
              {[["GL Bridge Synced", nav.gl_synced], ["Reconciliation Breaks 해소", breaks.length === 0], ["NAV 검산 완료", navStatus === "Final"]].map(([k, ok]) => (
                <div key={k as string} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 12, color: T.muted }}>{k}</span>
                  <span style={{ fontSize: 12, color: ok ? T.green : T.yellow }}>{ok ? "✓ 완료" : "→ 대기"}</span>
                </div>
              ))}
            </Block>
          </>}

          {/* 탭2: NAV·P&L */}
          {tab === 1 && <>
            <SectionHeader name="NAV 계산" tag={AUTO} />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
                <Cell k="Official NAV" v={nav.official} /><Cell k="Shadow NAV" v={nav.shadow} />
                <Cell k="Variance" v={variance} color={varianceFlag ? T.red : T.green} />
              </div>
              <Pill label={navStatus} color={sc(navStatus)} />
            </Block>
            <SectionHeader name="SHADOW NAV CHECK" />
            <Block>
              <Row k="Variance 금액" v={variance} color={varianceFlag ? T.red : undefined} />
              <Row k="Variance %" v={nav.variance_pct != null ? `${nav.variance_pct}%` : null} color={varianceFlag ? T.red : undefined} />
              {varianceFlag && <div style={{ marginTop: 8, padding: "8px 12px", background: "#1A0808", border: `1px solid ${T.red}44`, borderRadius: 4, fontSize: 11, color: T.red }}>⚠ 불일치 자동 플래그</div>}
            </Block>
            <SectionHeader name="NAV 변경 AUDIT TRAIL" />
            <Block>
              {(nav.audit_trail || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : (nav.audit_trail || []).map((a: any, i: number) => (
                <Row key={i} k={dash(a.date)} v={dash(a.change)} />
              ))}
            </Block>
            <SectionHeader name="FUND-LEVEL P&L" tag={AUTO} />
            <Block>
              {[["이자수익", pnl.interest], ["수수료수익", pnl.fees], ["실현손익", pnl.realized], ["평가손익", pnl.unrealized], ["합계", pnl.total]].map(([k, v], i, arr) => (
                <Row key={k as string} k={k as string} v={v} color={i === arr.length - 1 ? T.gold : undefined} />
              ))}
            </Block>
            <SectionHeader name="WATERFALL 계산" />
            <Block>
              {[["Return of Capital", waterfall.roc, T.blue], ["Preferred Return", waterfall.pref, T.green], ["Carry", waterfall.carry, T.gold]].map(([k, v, c]) => (
                <div key={k as string} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                  <span style={{ fontSize: 10, width: 120, color: T.muted }}>{k}</span>
                  <div style={{ flex: 1, height: 6, background: T.border, borderRadius: 3, overflow: "hidden" }}>
                    <div style={{ width: `${(v as any)?.pct || 0}%`, height: "100%", background: c as string }} />
                  </div>
                  <span style={{ fontSize: 10, fontFamily: T.mono, width: 60, textAlign: "right" }}>{dash((v as any)?.amount)}</span>
                </div>
              ))}
            </Block>
          </>}

          {/* 탭3: Capital Accounts */}
          {tab === 2 && <>
            <SectionHeader name="LP별 CAPITAL ACCOUNT" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>기관</span><span>출자액</span><span>수취액</span><span>잔여</span>
              </div>
              {capital.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : capital.map((c: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono }}>
                  <span style={{ fontFamily: T.font }}>{dash(c.name)}</span><span>{dash(c.commitment)}</span><span>{dash(c.received)}</span><span>{dash(c.remaining)}</span>
                </div>
              ))}
            </Block>
            <SectionHeader name="CASH FLOW 예측" tag={HEPH} />
            <Block><Row k="향후 12개월 예측" v={waterfall.cashflow_forecast} /></Block>
            <SectionHeader name="MANAGEMENT FEE 자동 계산" />
            <Block>
              <Row k="분기 수수료" v={pnl.mgmt_fee} />
              <button style={{ marginTop: 10, padding: "7px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4 }}>인보이스 생성</button>
            </Block>
            <div style={{ padding: "14px 16px", opacity: 0.35 }}>
              <SectionHeader name="MULTI-VEHICLE" desc="단일 vehicle" />
              <div style={{ fontSize: 11, color: T.muted, paddingTop: 8 }}>해당 없음</div>
            </div>
          </>}

          {/* 탭4: Subledger */}
          {tab === 3 && <>
            <SectionHeader name="LOAN EVENT POSTING" tag={<Tag label="AUTO · 100%" color={T.blue} />} />
            <Block>
              {loanEvents.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : loanEvents.map((e: any, i: number) => (
                <div key={i} style={{ display: "flex", gap: 8, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                  <Tag label={dash(e.type)} color={T.blue} />
                  <span style={{ fontSize: 11, color: T.text }}>{dash(e.detail)}</span>
                  <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>{dash(e.date)}</span>
                </div>
              ))}
            </Block>
            <SectionHeader name="INTEREST ACCRUAL / EIR" tag={AUTO} />
            <Block><Row k="누적 이자" v={pnl.accrued_interest} /><Row k="EIR" v={pnl.eir} /></Block>
            <SectionHeader name="POSITION & CASH RECONCILIATION" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Cell k="Cash Match %" v={recon.cash_match != null ? `${recon.cash_match}%` : null} color={recon.cash_match === 100 ? T.green : T.yellow} />
                <Cell k="Position Match %" v={recon.position_match != null ? `${recon.position_match}%` : null} color={recon.position_match === 100 ? T.green : T.yellow} />
              </div>
            </Block>
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, background: T.warn }}>
              <div style={{ marginBottom: 8 }}><span style={labelStyle}>Exception Reconciliation Queue</span></div>
              {breaks.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>예외 없음</div> : breaks.map((b: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: breakDot(b.days), flexShrink: 0 }} />
                  <span style={{ fontSize: 11, color: T.text }}>{dash(b.detail)}</span>
                  <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>{b.days != null ? `${b.days}일` : "—"}</span>
                </div>
              ))}
            </div>
            <SectionHeader name="GL POSTING BRIDGE" />
            <Block>
              {(gl.length ? gl : [{ name: "Loan Events" }, { name: "Interest Accrual" }, { name: "Fee Posting" }, { name: "Cash Entries" }]).map((g: any, i: number) => {
                const synced = (g.status || "").toLowerCase() === "synced" || g.synced;
                return (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                    <span style={{ fontSize: 11, color: T.muted }}>{dash(g.name)}</span>
                    <span style={{ fontSize: 11, color: synced ? T.green : T.yellow }}>{synced ? "Synced" : "Pending"}</span>
                  </div>
                );
              })}
            </Block>
          </>}

          {/* 탭5: Tax·Audit */}
          {tab === 4 && <>
            <SectionHeader name="세무 처리" />
            <Block>
              <Row k="이자소득 원천징수" v={nav.tax_withholding} />
              <Row k="비과세 여부" v={nav.tax_exempt} />
              <Row k="신고 준비" v={nav.tax_filing} />
            </Block>
            <SectionHeader name="외부 감사 연동" desc="연 1회" />
            <Block>
              <button style={{ padding: "8px 14px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4 }}>감사 자료 패키지 생성</button>
            </Block>
          </>}
        </div>

        {/* 우측 sticky: NAV & Ledger Snapshot */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}><span style={{ ...labelStyle, color: T.gold }}>NAV & Ledger Snapshot</span></div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>NAV Status</span><Refresh onClick={loadNav} ts={ts.nav || ""} /></div>
            <Row k="Variance" v={variance} color={varianceFlag ? T.red : T.green} />
            <Row k="NAV" v={nav.official} />
            <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}><span style={{ fontSize: 11, color: T.muted }}>Status</span><Pill label={navStatus} color={sc(navStatus)} /></div>
            <Row k="Strike Date" v={nav.strike_date} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>P&L Bridge</span></div>
            <Row k="이자수익" v={pnl.interest} /><Row k="수수료" v={pnl.fees} /><Row k="실현" v={pnl.realized} /><Row k="평가" v={pnl.unrealized} /><Row k="합계" v={pnl.total} color={T.gold} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>Close Calendar</span><Refresh onClick={() => stamp("cal")} ts={ts.cal || ""} /></div>
            <Row k="Month-end" v={lock.month ? "🔒 잠김" : "Open"} color={lock.month ? T.green : T.muted} />
            <Row k="Quarter-end" v={lock.quarter ? "🔒 잠김" : "Open"} color={lock.quarter ? T.green : T.muted} />
            <Row k="Period Status" v="Close 진행 중" />
            <Row k="Sign-off" v="1/3" />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>Reconciliation</span><Refresh onClick={loadRecon} ts={ts.recon || ""} /></div>
            <Row k="Total Breaks" v={breaks.length || 0} color={breaks.length ? T.red : T.green} />
            <Row k=">7일" v={breaks.filter((b: any) => b.days > 7).length} />
            <Row k=">30일" v={breaks.filter((b: any) => b.days > 30).length} />
            <Row k="Cash%" v={recon.cash_match != null ? `${recon.cash_match}%` : null} />
            <Row k="Position%" v={recon.position_match != null ? `${recon.position_match}%` : null} />
            <Row k="GL" v={gl.every((g: any) => g.synced || (g.status || "").toLowerCase() === "synced") && gl.length ? "Synced" : "Pending"} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Capital & Liquidity</span></div>
            <Row k="Unfunded" v={waterfall.unfunded} /><Row k="Distributable" v={waterfall.distributable} /><Row k="Recycling" v={waterfall.recycling} /><Row k="Next Call" v={waterfall.next_call} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Subledger Integrity</span></div>
            <Row k="Loan Events %" v="100%" color={T.green} /><Row k="Accrual" v={pnl.eir ? "OK" : "—"} /><Row k="GL Bridge" v={gl.length ? "활성" : "—"} />
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[["NAV 계산", T.gold], ["Shadow 검산", T.gold], ["Fee 청구", T.text], ["감사 자료", T.text], ["Cut-off 잠금", T.red], ["Recon Review", T.text]].map(([label, color]) => (
              <button key={label as string} style={{ width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4 }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
