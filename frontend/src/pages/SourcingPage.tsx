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
const urgColor = (u?: string) => { const x = (u || "").toUpperCase(); return x === "CRITICAL" ? T.red : x === "WATCH" ? T.gold : T.muted; };
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
const KEYFRAMES = `
@keyframes srcping { 0% { transform: scale(1); opacity: 0.8; } 70% { transform: scale(2.4); opacity: 0; } 100% { opacity: 0; } }
@keyframes srcsweep { 0% { transform: translateX(-100%); } 100% { transform: translateX(100%); } }
`;
const FUNNEL = ["Prospect", "Screening", "DD", "IC", "Closing"];

export default function SourcingPage({ deals = [] }: { deals?: any[] }) {
  const [agent, setAgent] = useState<any>({});
  const [preDeals, setPreDeals] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [sigEx, setSigEx] = useState<any[]>([]);
  const [pipeline, setPipeline] = useState<any[]>([]);
  const [channels, setChannels] = useState<any[]>([]);
  const [recycling, setRecycling] = useState<any>({});
  const [brokers, setBrokers] = useState<any[]>([]);
  const [rejected, setRejected] = useState<any[]>([]);
  const [lpCommit, setLpCommit] = useState<any[]>([]);
  const [compete, setCompete] = useState<any>({});
  const [openStage, setOpenStage] = useState<string | null>(null);
  const [ts, setTs] = useState<Record<string, string>>({ collect: nowStr() });
  const stamp = (k: string) => setTs(p => ({ ...p, [k]: nowStr() }));

  const loadAgent = useCallback(() => {
    API.get(`/api/sourcing/agent-status`).then(r => setAgent(r.data || {})).catch(() => setAgent({}));
    API.get(`/api/sourcing/pre-assembled-deals`).then(r => setPreDeals(r.data?.deals || r.data || [])).catch(() => setPreDeals([]));
    stamp("collect");
  }, []);
  const loadRecycling = useCallback(() => { API.get(`/api/sourcing/recycling-capital`).then(r => setRecycling(r.data || {})).catch(() => setRecycling({})); stamp("recyc"); }, []);
  const loadCompete = useCallback(() => { API.get(`/api/sourcing/competitive-monitor`).then(r => setCompete(r.data || {})).catch(() => setCompete({})); stamp("compete"); }, []);

  useEffect(() => {
    loadAgent(); loadRecycling(); loadCompete();
    API.get(`/api/sourcing/signals`).then(r => setSignals(r.data?.signals || r.data || [])).catch(() => setSignals([]));
    API.get(`/api/sourcing/signal-exceptions`).then(r => setSigEx(r.data?.items || r.data || [])).catch(() => setSigEx([]));
    API.get(`/api/sourcing/pipeline`).then(r => setPipeline(r.data?.stages || r.data || [])).catch(() => setPipeline([]));
    API.get(`/api/sourcing/channels`).then(r => setChannels(r.data?.items || r.data || [])).catch(() => setChannels([]));
    API.get(`/api/sourcing/broker-performance`).then(r => setBrokers(r.data?.items || r.data || [])).catch(() => setBrokers([]));
    API.get(`/api/sourcing/rejected-deals`).then(r => setRejected(r.data?.items || r.data || [])).catch(() => setRejected([]));
    API.get(`/api/sourcing/lp-commitments`).then(r => setLpCommit(r.data?.items || r.data || [])).catch(() => setLpCommit([]));
  }, [loadAgent, loadRecycling, loadCompete]);

  const agentStatus = agent.status || "Idle";
  const collecting = agentStatus === "Active";
  const stageOf = (name: string) => pipeline.find((p: any) => (p.stage || p.name) === name) || {};
  const brokerTop3 = [...brokers].sort((a, b) => (b.success_rate || 0) - (a.success_rate || 0)).slice(0, 3).map(b => b.name);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>
      <style>{KEYFRAMES}</style>

      {/* 헤더 */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>딜 소싱 &amp; 파이프라인</span>
          <Pill label={`HERMES ${agentStatus}`} color={collecting ? T.gold : T.muted} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>마지막 수집 {ts.collect} · 오늘 Pre-assembled {preDeals.length}건</span>
        </div>
      </div>

      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* ① HERMES Sourcing Agent */}
          <SectionHeader n="①" name="HERMES SOURCING AGENT" desc="새벽 04:00 KST 자동" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", background: T.surface1, borderRadius: 6, marginBottom: 12 }}>
              <span style={{ position: "relative", width: 12, height: 12, display: "inline-flex" }}>
                <span style={{ width: 12, height: 12, borderRadius: "50%", background: collecting ? T.gold : agentStatus === "Error" ? T.red : T.muted }} />
                {collecting && <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: T.gold, animation: "srcping 1.6s ease-out infinite" }} />}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, color: collecting ? T.gold : T.text }}>HERMES Agent · {agentStatus}</div>
                <div style={{ fontSize: 9, color: T.muted, fontFamily: T.mono }}>마지막 실행 {dash(agent.last_run || "04:00 KST")}</div>
              </div>
            </div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 8 }}>오늘 Pre-assembled Deals</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              {preDeals.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : preDeals.map((d: any, i: number) => (
                <div key={i} style={{ padding: "12px", border: `1px solid ${T.border}`, borderRadius: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 13, color: T.text, flex: 1 }}>{dash(d.borrower)}</span>
                    <Tag label={dash(d.deal_type)} color={T.gold} />
                  </div>
                  <div style={{ fontSize: 10, color: T.muted, marginTop: 6, fontFamily: T.mono }}>신호 {dash(d.score)} · {dash(d.channel)}</div>
                  <button style={{ marginTop: 8, width: "100%", padding: "6px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4 }}>2페이지 딜 등록 →</button>
                </div>
              ))}
            </div>
          </div>

          {/* ② Signal Room 전체 테이블 */}
          <SectionHeader n="②" name="SIGNAL ROOM" desc="읽기 전용" />
          <div style={{ position: "relative", overflow: "hidden" }}>
            {collecting && <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, overflow: "hidden", zIndex: 2 }}>
              <div style={{ width: "40%", height: "100%", background: `linear-gradient(90deg, transparent, ${T.gold}, transparent)`, animation: "srcsweep 4s linear infinite" }} />
            </div>}
            <div style={{ padding: "12px 16px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "0.8fr 1.2fr 1.6fr 0.8fr 0.6fr 0.8fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>URGENCY</span><span>ENTITY</span><span>SIGNAL</span><span>ZONE</span><span>SCORE</span><span>AS OF</span>
              </div>
              {signals.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : signals.map((s: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "0.8fr 1.2fr 1.6fr 0.8fr 0.6fr 0.8fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span style={{ color: urgColor(s.urgency), fontSize: 9 }}>{dash(s.urgency)}</span>
                  <span style={{ color: T.text }}>{dash(s.entity)}</span>
                  <span style={{ color: T.muted }}>{dash(s.signal)}</span>
                  <span style={{ color: T.muted, fontFamily: T.mono }}>{dash(s.zone)}</span>
                  <span style={{ color: T.text, fontFamily: T.mono }}>{dash(s.score)}</span>
                  <span style={{ color: T.muted, fontFamily: T.mono }}>{dash(s.as_of)}</span>
                </div>
              ))}
            </div>
          </div>
          {/* Sweep Exception Queue */}
          <div style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}`, background: T.warn }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Sweep Exception Queue</span></div>
            {sigEx.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>예외 없음</div> : sigEx.map((e: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.text, flex: 1 }}>{dash(e.raw)}</span>
                <span style={{ fontSize: 10, color: T.yellow }}>{dash(e.reason)}</span>
                <button style={{ fontSize: 10, padding: "3px 8px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>수동 분류</button>
              </div>
            ))}
          </div>

          {/* ③ 파이프라인 현황 */}
          <SectionHeader n="③" name="파이프라인 현황" desc="Stage Dwell Time" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", gap: 4 }}>
              {FUNNEL.map((st, i) => {
                const o = stageOf(st);
                const stall = (o.max_dwell || 0) >= 30;
                const on = openStage === st;
                return (
                  <div key={st} onClick={() => setOpenStage(on ? null : st)} style={{ flex: 1, cursor: "pointer" }}>
                    <div style={{ padding: "10px 8px", background: on ? T.surface1 : "transparent", border: `1px solid ${stall ? T.red : T.border}`, borderRadius: 4, textAlign: "center" }}>
                      <div style={{ fontSize: 9, color: T.muted }}>{st}</div>
                      <div style={{ fontSize: 16, fontFamily: T.mono, color: stall ? T.red : T.text, marginTop: 4 }}>{dash(o.count)}</div>
                      <div style={{ fontSize: 8, color: stall ? T.red : T.muted, marginTop: 2 }}>{stall ? "⚠ " : ""}{o.avg_dwell != null ? `${o.avg_dwell}일` : "—"}</div>
                    </div>
                    {i < FUNNEL.length - 1 && <div style={{ textAlign: "center", fontSize: 8, color: T.muted }}></div>}
                  </div>
                );
              })}
            </div>
            {openStage && (
              <div style={{ marginTop: 10, padding: "10px 12px", background: T.surface1, borderRadius: 6 }}>
                <div style={{ fontSize: 10, color: T.gold, marginBottom: 6 }}>{openStage} 딜 목록</div>
                {(stageOf(openStage).deals || []).length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : (stageOf(openStage).deals || []).map((d: any, i: number) => (
                  <Row key={i} k={dash(d.borrower || d.name)} v={d.dwell != null ? `${d.dwell}일` : null} color={d.dwell >= 30 ? T.red : undefined} />
                ))}
              </div>
            )}
          </div>

          {/* ④ 소싱 채널 관리 */}
          <SectionHeader n="④" name="소싱 채널 관리" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 0.8fr 1.4fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>채널</span><span>유입</span><span>성사율</span><span>최근 딜</span>
            </div>
            {channels.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : channels.map((c: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1.4fr 0.8fr 0.8fr 1.4fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono }}>
                <span style={{ fontFamily: T.font }}>{dash(c.name)}</span><span>{dash(c.inflow)}</span><span>{c.success_rate != null ? `${c.success_rate}%` : "—"}</span><span style={{ fontFamily: T.font, color: T.muted }}>{dash(c.last_deal)}</span>
              </div>
            ))}
          </div>

          {/* ⑤ Recycling 가용 자금 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 8, color: T.gold, fontFamily: T.mono }}>⑤</span>
              <span style={{ fontSize: 12 }}>Recycling 가용 자금</span>
              <span style={{ fontSize: 8, color: "#3A4A62" }}>4페이지 회수 자동 연동</span>
              <Refresh onClick={loadRecycling} ts={ts.recyc || ""} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr 1.4fr", gap: 10 }}>
              <div style={{ padding: "10px 12px", border: `1px solid ${T.gold}44`, borderRadius: 4 }}>
                <div style={{ fontSize: 9, color: T.muted }}>현재 가용액</div>
                <div style={{ fontSize: 16, fontFamily: T.mono, color: T.gold, marginTop: 4 }}>{dash(recycling.available)}</div>
              </div>
              <div style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
                <div style={{ fontSize: 9, color: T.muted }}>회수일</div>
                <div style={{ fontSize: 13, fontFamily: T.mono, color: T.text, marginTop: 4 }}>{dash(recycling.recovered_date)}</div>
              </div>
              <div style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
                <div style={{ fontSize: 9, color: T.muted }}>원천 딜</div>
                <div style={{ fontSize: 13, color: T.text, marginTop: 4 }}>{dash(recycling.source_deal)}</div>
              </div>
            </div>
          </div>

          {/* ⑥ 브로커 성과 추적 */}
          <SectionHeader n="⑥" name="브로커 성과 추적" desc="성사율 Top 3 강조" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr 0.8fr 0.8fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>이름</span><span>소개</span><span>성사</span><span>성사율</span><span>수수료</span>
            </div>
            {brokers.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : brokers.map((b: any, i: number) => {
              const top = brokerTop3.includes(b.name);
              return (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr 0.8fr 0.8fr 1fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, fontFamily: T.mono, color: top ? T.gold : T.text }}>
                  <span style={{ fontFamily: T.font }}>{top ? "★ " : ""}{dash(b.name)}</span><span>{dash(b.referrals)}</span><span>{dash(b.closed)}</span><span>{b.success_rate != null ? `${b.success_rate}%` : "—"}</span><span>{dash(b.fees)}</span>
                </div>
              );
            })}
          </div>

          {/* ⑦ 딜 거절 DB */}
          <SectionHeader n="⑦" name="딜 거절 DB" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr 1.4fr 0.8fr 1.2fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>차주</span><span>딜타입</span><span>거절사유</span><span>날짜</span><span>액션</span>
            </div>
            {rejected.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : rejected.map((r: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr 1.4fr 0.8fr 1.2fr", gap: 6, fontSize: 10, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                <span style={{ color: r.blacklist ? T.red : T.text }}>{r.blacklist ? "⛔ " : ""}{dash(r.borrower)}</span>
                <span style={{ color: T.muted }}>{dash(r.deal_type)}</span>
                <span style={{ color: T.muted }}>{dash(r.reason)}</span>
                <span style={{ color: T.muted, fontFamily: T.mono }}>{dash(r.date)}</span>
                <span style={{ display: "flex", gap: 4 }}>
                  <button style={{ fontSize: 9, padding: "2px 6px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.muted, border: `1px solid ${T.border}`, borderRadius: 3 }}>재검토</button>
                  <button style={{ fontSize: 9, padding: "2px 6px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.red, border: `1px solid ${T.red}44`, borderRadius: 3 }}>블랙리스트</button>
                </span>
              </div>
            ))}
          </div>

          {/* ⑧ LP 신규 약정 트래킹 */}
          <SectionHeader n="⑧" name="LP 신규 약정 트래킹" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 0.8fr 1fr", gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
              <span>기관</span><span>약정 의향</span><span>확인</span><span>담당자</span>
            </div>
            {lpCommit.length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : lpCommit.map((l: any, i: number) => (
              <div key={i} style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 0.8fr 1fr", gap: 6, fontSize: 11, padding: "6px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                <span>{dash(l.name)}</span><span style={{ fontFamily: T.mono }}>{dash(l.amount)}</span>
                <span style={{ color: l.confirmed ? T.green : T.yellow }}>{l.confirmed ? "확인" : "대기"}</span>
                <span style={{ color: T.muted }}>{dash(l.owner)}</span>
              </div>
            ))}
          </div>

          {/* ⑨ 경쟁 환경 모니터링 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <span style={{ fontSize: 8, color: T.gold, fontFamily: T.mono }}>⑨</span>
              <span style={{ fontSize: 12 }}>경쟁 환경 모니터링</span>
              <Tag label="Grok X Search" color={T.blue} />
              <Refresh onClick={loadCompete} ts={ts.compete || ""} />
            </div>
            <Row k="동일 섹터 경쟁 대주" v={compete.competitors} />
            <Row k="금리 변동" v={compete.rate_change} />
            <Row k="조건 변동" v={compete.term_change} />
          </div>
        </div>

        {/* 우측 sticky: Sourcing Dashboard */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}><span style={{ ...labelStyle, color: T.gold }}>Sourcing Dashboard</span></div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>오늘 Pre-assembled</span></div>
            <Row k="건수" v={preDeals.length || 0} color={T.gold} />
            <Row k="등록 대기" v={preDeals.filter((d: any) => !d.registered).length} />
            <Row k="등록 완료" v={preDeals.filter((d: any) => d.registered).length} color={T.green} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>HERMES 마지막 수집</span><Refresh onClick={loadAgent} ts={ts.collect || ""} /></div>
            <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}><span style={{ fontSize: 11, color: T.muted }}>상태</span><Pill label={agentStatus} color={collecting ? T.gold : T.muted} /></div>
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Signal Room Exceptions</span></div>
            <Row k="수동 확인 필요" v={sigEx.length || 0} color={sigEx.length ? T.yellow : T.green} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>파이프라인 단계별</span></div>
            {FUNNEL.map(st => { const o = stageOf(st); const stall = (o.max_dwell || 0) >= 30; return <Row key={st} k={st} v={o.count} color={stall ? T.red : undefined} />; })}
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}><span style={labelStyle}>Recycling 가용</span><Refresh onClick={loadRecycling} ts={ts.recyc || ""} /></div>
            <Row k="현재 금액" v={recycling.available} color={T.gold} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>브로커 Top 3</span></div>
            {brokerTop3.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : [...brokers].sort((a, b) => (b.success_rate || 0) - (a.success_rate || 0)).slice(0, 3).map((b: any, i: number) => (
              <Row key={i} k={`★ ${dash(b.name)}`} v={b.success_rate != null ? `${b.success_rate}%` : null} color={T.gold} />
            ))}
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[["HERMES 수동 실행", T.gold], ["Signal Exception 처리", T.gold], ["딜 수동 등록 +", T.text], ["브로커 성과 보고서", T.text], ["경쟁 환경 새로고침 ↻", T.text]].map(([label, color]) => (
              <button key={label as string} style={{ width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4 }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
