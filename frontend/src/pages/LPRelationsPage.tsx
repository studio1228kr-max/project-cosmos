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
  완료: T.green, 생성완료: T.green, 답변완료: T.green, 수령확인: T.green, 진행중: T.yellow,
  미답변: T.yellow, NAV확정대기: T.yellow, "NAV 확정 대기": T.yellow, 발송대기: T.yellow, 미착수: T.muted,
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
function SectionHeader({ name, desc, tag }: { name: string; desc?: string; tag?: React.ReactNode }) {
  return (
    <div style={{ background: "#060A11", borderTop: "2px solid #1A2235", padding: "8px 16px", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ fontSize: 10, color: "#8A9BB5", letterSpacing: "0.08em" }}>{name}</span>
      {tag}
      {desc && <span style={{ fontSize: 8, color: "#3A4A62" }}>{desc}</span>}
    </div>
  );
}
const Block: React.FC<{ children: React.ReactNode; dim?: boolean }> = ({ children, dim }) => (
  <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, opacity: dim ? 0.35 : 1 }}>{children}</div>
);
const AUTO = <Tag label="AUTO" color={T.blue} />;
const TABS = ["Investor Reporting", "Capital Operations", "LP CRM", "Onboarding"];
const ONBOARD_STEPS = ["KYC/AML", "약정서", "계좌등록", "포탈권한"];

export default function LPRelationsPage({ deals = [] }: { deals?: any[] }) {
  const [tab, setTab] = useState(0);
  const [prefs, setPrefs] = useState<any>({});
  const [qr, setQr] = useState<any[]>([]);
  const [capital, setCapital] = useState<any[]>([]);
  const [calls, setCalls] = useState<any[]>([]);
  const [irLogs, setIrLogs] = useState<any[]>([]);
  const [selLp, setSelLp] = useState<string | null>(null);
  const [ts, setTs] = useState<Record<string, string>>({});
  const stamp = (k: string) => setTs(p => ({ ...p, [k]: nowStr() }));

  const loadAll = useCallback(() => {
    API.get(`/api/lp/preferences`).then(r => setPrefs(r.data || {})).catch(() => setPrefs({}));
    API.get(`/api/lp/qr-reports`).then(r => setQr(r.data?.reports || r.data || [])).catch(() => setQr([]));
    API.get(`/api/lp/capital-accounts`).then(r => setCapital(r.data?.accounts || r.data || [])).catch(() => setCapital([]));
    API.get(`/api/lp/capital-calls`).then(r => setCalls(r.data?.calls || r.data || [])).catch(() => setCalls([]));
    API.get(`/api/lp/ir-logs`).then(r => setIrLogs(r.data?.logs || r.data || [])).catch(() => setIrLogs([]));
    stamp("all");
  }, []);
  useEffect(() => { loadAll(); }, [loadAll]);

  const lpCount = capital.length || prefs.lp_count || 0;
  const totalCommit = prefs.total_commitment;
  const unanswered = irLogs.filter((l: any) => sc(l.status) === T.yellow).length;
  const matches: any[] = prefs.matches || prefs.recommendations || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* 헤더 */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>LP 관계 &amp; 투자자 보고</span>
          <Tag label="딜바이딜 SPC" color={T.gold} /><Tag label="2026 Q2" color={T.blue} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>참여기관 {lpCount || "—"}곳 · 분기 NAV 확정 대기</span>
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

          {/* 탭1: Investor Reporting */}
          {tab === 0 && <>
            <SectionHeader name="QR 보고서" tag={AUTO} desc="NAV 확정 시 자동 생성" />
            <Block>
              {qr.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : qr.map((q: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 12, color: T.text, flex: 1 }}>{dash(q.name)}</span>
                  <Pill label={q.status || "NAV 확정 대기"} color={sc(q.status || "NAV 확정 대기")} />
                  <button style={{ fontSize: 10, padding: "3px 8px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.muted, border: `1px solid ${T.border}`, borderRadius: 3 }}>미리보기</button>
                </div>
              ))}
            </Block>
            <Block dim>
              <SectionHeader name="연간 감사 보고서 배포" desc="연 1회" />
              <div style={{ fontSize: 11, color: T.muted, paddingTop: 8 }}>준비 중</div>
            </Block>
            <SectionHeader name="LP PREFERENCE ENGINE 딜 매칭" />
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ background: `${T.gold}12`, border: `1px solid ${T.gold}44`, borderRadius: 6, padding: "12px 14px" }}>
                {matches.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>추천 —</div> : matches.slice(0, 3).map((m: any, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: i < 2 ? `1px solid ${T.gold}22` : "none" }}>
                    <span style={{ fontFamily: T.mono, fontSize: 13, color: T.gold }}>{i + 1}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 12, color: T.text }}>{dash(m.name)}</div>
                      <div style={{ fontSize: 10, color: T.muted }}>{dash(m.reason)}</div>
                    </div>
                    <span style={{ fontFamily: T.mono, fontSize: 12, color: T.gold }}>{dash(m.score)}</span>
                  </div>
                ))}
              </div>
            </div>
          </>}

          {/* 탭2: Capital Operations */}
          {tab === 1 && <>
            <SectionHeader name="CAPITAL CALL NOTICE" tag={AUTO} />
            <Block>
              {calls.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : calls.map((c: any, i: number) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: `1px solid ${T.border}` }}>
                  <span style={{ fontSize: 12, color: T.text, flex: 1 }}>{dash(c.name)}</span>
                  <span style={{ fontSize: 11, fontFamily: T.mono, color: T.text }}>{dash(c.amount)}</span>
                  <Pill label={c.status || "발송 대기"} color={sc(c.status || "발송대기")} />
                  <button style={{ fontSize: 10, padding: "3px 8px", cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}44`, borderRadius: 3 }}>발송</button>
                </div>
              ))}
            </Block>
            <Block dim>
              <SectionHeader name="DISTRIBUTION NOTICE" desc="회수 완료 후" />
              <div style={{ fontSize: 11, color: T.muted, paddingTop: 8 }}>회수 완료 시 활성화</div>
            </Block>
            <SectionHeader name="LP 개별 CAPITAL ACCOUNT STATEMENT" />
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
          </>}

          {/* 탭3: LP CRM */}
          {tab === 2 && <>
            <SectionHeader name="LP 기관" />
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {(prefs.lps || capital).map((lp: any, i: number) => {
                  const id = lp.name || String(i);
                  const on = selLp === id;
                  return (
                    <div key={i} onClick={() => setSelLp(on ? null : id)} style={{ padding: "12px", borderRadius: 6, cursor: "pointer", border: on ? `1px solid ${T.gold}` : `1px solid ${T.border}`, background: on ? T.surface1 : "transparent" }}>
                      <div style={{ fontSize: 13, color: T.text }}>{dash(lp.name)}</div>
                      <div style={{ fontSize: 10, color: T.muted, marginTop: 2 }}>{dash(lp.type)} · 약정 {dash(lp.commitment)}</div>
                      <div style={{ marginTop: 6 }}>{lp.pref_type && <Tag label={lp.pref_type} color={T.gold} />}</div>
                    </div>
                  );
                })}
                <div style={{ padding: "12px", borderRadius: 6, border: `1px dashed ${T.border}`, color: T.muted, fontSize: 11, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>+ 기관 추가</div>
              </div>
            </div>
            <SectionHeader name="LP IR LOG" />
            <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
              {irLogs.map((l: any, i: number) => (
                <div key={i} style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 6, marginBottom: 8 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 12, color: T.text }}>{dash(l.name)}</span>
                    <span style={{ fontSize: 10, color: T.muted }}>{dash(l.contact)} · {dash(l.date)}</span>
                    <span style={{ marginLeft: "auto" }}><Pill label={l.status || "미답변"} color={sc(l.status || "미답변")} /></span>
                  </div>
                  <div style={{ fontSize: 11, color: T.muted, marginTop: 6 }}>{dash(l.question)}</div>
                </div>
              ))}
              <div style={{ padding: "10px", borderRadius: 6, border: `1px dashed ${T.border}`, color: T.muted, fontSize: 11, textAlign: "center", cursor: "pointer" }}>+ 커뮤니케이션 기록</div>
            </div>
            <Block dim>
              <SectionHeader name="LP 포탈 업데이트" desc="준비 중" />
              <div style={{ fontSize: 11, color: T.muted, paddingTop: 8 }}>준비 중</div>
            </Block>
          </>}

          {/* 탭4: Onboarding */}
          {tab === 3 && <>
            <SectionHeader name="LP ONBOARDING / 변경 관리" />
            <Block>
              <div style={{ display: "grid", gridTemplateColumns: `1.4fr repeat(${ONBOARD_STEPS.length}, 1fr)`, gap: 6, fontSize: 8, color: T.muted, padding: "0 0 6px", borderBottom: `1px solid ${T.border}` }}>
                <span>기관</span>{ONBOARD_STEPS.map(s => <span key={s}>{s}</span>)}
              </div>
              {(prefs.lps || capital).length === 0 ? <div style={{ fontSize: 11, color: T.muted, paddingTop: 6 }}>—</div> : (prefs.lps || capital).map((lp: any, i: number) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: `1.4fr repeat(${ONBOARD_STEPS.length}, 1fr)`, gap: 6, padding: "8px 0", borderBottom: `1px solid ${T.border}`, alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: T.text }}>{dash(lp.name)}</span>
                  {ONBOARD_STEPS.map(s => {
                    const st = (lp.onboarding || {})[s];
                    const c = st === "완료" ? T.green : st === "진행중" ? T.yellow : T.muted;
                    return <span key={s} style={{ fontSize: 14, color: c }}>{st === "완료" ? "●" : st === "진행중" ? "◐" : "○"}</span>;
                  })}
                </div>
              ))}
              <div style={{ display: "flex", gap: 12, marginTop: 10, fontSize: 9, color: T.muted }}>
                <span style={{ color: T.green }}>● 완료</span><span style={{ color: T.yellow }}>◐ 진행중</span><span>○ 미착수</span>
              </div>
            </Block>
          </>}
        </div>

        {/* 우측 sticky: LP Dashboard */}
        <div style={{ width: 260, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center" }}><span style={{ ...labelStyle, color: T.gold }}>LP Dashboard</span><Refresh onClick={loadAll} ts={ts.all || ""} /></div>
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>참여기관 현황</span></div>
            <Row k="등록기관" v={lpCount || null} /><Row k="총약정" v={totalCommit} /><Row k="집행액" v={prefs.called} /><Row k="수취액" v={prefs.received} /><Row k="잔여" v={prefs.remaining} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>이번 분기 할 일</span></div>
            <Row k="QR 생성" v={qr.filter((q: any) => sc(q.status) !== T.green).length} color={T.yellow} />
            <Row k="IR 미답변" v={unanswered} color={unanswered ? T.yellow : T.green} />
            <Row k="Capital Call" v={calls.filter((c: any) => sc(c.status) !== T.green).length} />
            <Row k="Distribution" v={prefs.distributions_pending} />
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>딜 매칭 추천</span></div>
            {matches.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : matches.slice(0, 3).map((m: any, i: number) => (
              <Row key={i} k={dash(m.name)} v={m.score} color={T.gold} />
            ))}
          </div>
          <div style={{ padding: "12px 14px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>IR 현황</span></div>
            <Row k="미답변" v={unanswered} color={unanswered ? T.yellow : T.green} />
            <Row k="후속조치" v={irLogs.filter((l: any) => l.followup).length} />
            <Row k="최근컨택" v={irLogs[0]?.date} />
          </div>
          <div style={{ padding: "12px 14px" }}>
            <div style={{ marginBottom: 8 }}><span style={labelStyle}>Quick Actions</span></div>
            {[["QR 보고서", T.gold], ["IR 답변", T.gold], ["LP 등록", T.text], ["Capital Call", T.text], ["Distribution", T.text], ["감사 보고서", T.text]].map(([label, color]) => (
              <button key={label as string} style={{ width: "100%", textAlign: "left", padding: "8px 10px", marginBottom: 6, fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: color as string, border: `1px solid ${color as string}44`, borderRadius: 4 }}>{label}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
