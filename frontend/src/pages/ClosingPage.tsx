import React, { useEffect, useState, useCallback } from "react";
import API from "../api";

// ── 디자인 시스템 (DealExecution과 동일) ─────────────────────
const T = {
  bg: "#080C14",
  surface1: "#0D1826",
  warn: "#1A140A",        // bg-warning
  gold: "#C9A84C",
  blue: "#4A90D9",        // HEPHAESTUS
  purple: "#9A5ADA",      // K&C
  green: "#2ACA70",
  red: "#FF5555",
  watch: "#F59E0B",
  text: "#E2E8F0",
  muted: "#4A6080",
  border: "#1A2332",
  font: "'Goldman Sans', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};
const dash = (v: any) => (v === null || v === undefined || v === "") ? "—" : v;
const SC: Record<string, string> = {
  PASS: T.green, DONE: T.green, COMPLETE: T.green, 완료: T.green, RECEIVED: T.green, 수령: T.green,
  ACTIVE: T.gold, PROGRESS: T.gold, 진행중: T.gold, REVIEW: T.gold, 검토중: T.gold,
  PENDING: T.muted, WAIT: T.muted, 대기: T.muted, 미착수: T.muted, 요청전: T.muted,
  MISSING: T.red, 미수령: T.red, EXCEPTION: T.watch, 예외승인: T.watch,
};
const sc = (s?: string) => SC[(s || "").toUpperCase()] || SC[s || ""] || T.muted;
const nowStr = () => new Date().toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

const labelStyle: React.CSSProperties = { fontSize: 10, color: T.muted, letterSpacing: "0.1em", textTransform: "uppercase" };
const Tag = ({ label, color }: { label: string; color: string }) => (
  <span style={{ fontSize: 9, color, border: `1px solid ${color}44`, borderRadius: 3, padding: "1px 6px", letterSpacing: "0.06em" }}>{label}</span>
);
const Badge = ({ status, big }: { status?: string; big?: boolean }) => {
  if (!status) return <span style={{ color: T.muted }}>—</span>;
  const c = sc(status);
  return <span style={{ fontSize: big ? 13 : 10, color: c, background: `${c}1A`, border: `1px solid ${c}44`, borderRadius: 3, padding: "2px 7px", whiteSpace: "nowrap" }}>{status}</span>;
};
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
const StepCard: React.FC<{ icon: "done" | "active" | "pending"; title: string; tags?: React.ReactNode; badge?: string; children?: React.ReactNode; blocked?: boolean }> =
  ({ icon, title, tags, badge, children, blocked }) => (
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
        {badge && <span style={{ marginLeft: "auto" }}><Badge status={badge} /></span>}
      </div>
      {children && <div style={{ marginLeft: 30, marginTop: 8 }}>{children}</div>}
    </div>
  );
const Refresh = ({ onClick, ts }: { onClick: () => void; ts: string }) => (
  <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
    {ts && <span style={{ fontSize: 9, color: T.muted, fontFamily: T.mono }}>{ts}</span>}
    <span onClick={onClick} style={{ fontSize: 10, color: T.muted, cursor: "pointer" }}>↻</span>
  </span>
);

const KC = <Tag label="K&C" color={T.purple} />;
const HEPH = <Tag label="HEPHAESTUS" color={T.blue} />;

export default function ClosingPage({ deals = [] }: { deals?: any[] }) {
  const [selId, setSelId] = useState<string | null>(null);
  const [deal, setDeal] = useState<any>(null);
  const [vote, setVote] = useState<string | null>(null);
  const [term, setTerm] = useState<any>({});
  const [dd, setDd] = useState<any>({});
  const [docs, setDocs] = useState<any[]>([]);
  const [cp, setCp] = useState<any>({});
  const [exit, setExit] = useState<any>({});
  const [executed, setExecuted] = useState(false);
  const [docTs, setDocTs] = useState("");
  const [cpTs, setCpTs] = useState("");

  useEffect(() => { if (deals.length) setSelId(prev => prev || (deals[0].deal_code || String(deals[0].id))); }, [deals]);

  const fetchDocs = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}/documents`).then(r => setDocs(r.data?.documents || r.data || [])).catch(() => setDocs([]));
    setDocTs(nowStr());
  }, []);
  const fetchCp = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}/cp-status`).then(r => setCp(r.data || {})).catch(() => setCp({}));
    setCpTs(nowStr());
  }, []);

  const load = useCallback((id: string | null) => {
    if (!id) return;
    API.get(`/api/deals/${id}`).then(r => setDeal(r.data)).catch(() => setDeal(null));
    API.get(`/api/deals/${id}/ic-vote`).then(r => setVote(r.data?.vote || null)).catch(() => {});
    API.get(`/api/deals/${id}/term-sheet`).then(r => setTerm(r.data || {})).catch(() => setTerm({}));
    API.get(`/api/deals/${id}/confirmatory-dd`).then(r => setDd(r.data || {})).catch(() => setDd({}));
    API.get(`/api/deals/${id}/exit-recommendation`).then(r => setExit(r.data || {})).catch(() => setExit({}));
  }, []);
  useEffect(() => { load(selId); fetchDocs(selId); fetchCp(selId); }, [selId, load, fetchDocs, fetchCp]);

  const listDeal = deals.find((d: any) => (d.deal_code || String(d.id)) === selId) || {};
  const D = { ...listDeal, ...(deal || {}) };

  // 진행률 (14단계)
  const ddDone = ["financial", "legal", "tax", "operational"].filter(k => sc(dd[k]?.status) === T.green).length;
  const doneCount = (vote ? 1 : 0) + (term.status ? 1 : 0) + ddDone + (executed ? 4 : 0);
  const progressPct = Math.round((Math.min(doneCount, 14) / 14) * 100);

  const submitVote = (v: string) => {
    setVote(v);
    if (selId) API.post(`/api/deals/${selId}/ic-vote`, { vote: v }).catch(() => {});
  };

  // 문서 / CP 카운트
  const docMissing = docs.filter(d => sc(d.status) === T.red).length;
  const CP_ITEMS = ["인허가", "담보 등기", "보험", "LP 자금 확약서"];
  const cpState = (k: string) => cp?.[k] || cp?.items?.[k] || null;
  const cpUnmet = CP_ITEMS.filter(k => sc(cpState(k)) !== T.green).length;
  const exceptions: any[] = cp?.exceptions || exit?.exceptions || [];
  const cpIcon = (s?: string) => { const c = sc(s); return c === T.green ? "✓" : c === T.gold ? "→" : c === T.watch ? "⚠" : "○"; };

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0, fontFamily: T.font, fontWeight: 400, color: T.text, background: T.bg }}>

      {/* ── 딜 헤더 ── */}
      <div style={{ padding: "14px 20px", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 16 }}>{dash(D.deal_name)}</span>
          <Tag label={D.deal_type || "DIRECT LENDING"} color={T.gold} />
          <Tag label="IC 조건부 승인" color={T.watch} />
          <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted, fontFamily: T.mono }}>경과 {dash(D.elapsed)} · 담당 {dash(D.owner)}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 12 }}>
          <div style={{ flex: 1, display: "flex", gap: 2 }}>
            {Array.from({ length: 14 }).map((_, i) => (
              <div key={i} style={{ flex: 1, height: 4, borderRadius: 2, background: i < doneCount ? T.gold : T.border }} />
            ))}
          </div>
          <span style={{ fontSize: 11, color: T.muted, fontFamily: T.mono, minWidth: 72 }}>{progressPct}% · Closing</span>
        </div>
      </div>

      {/* ── 본문: 좌 파이프라인 + 우 Closing Tracker ── */}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>

        {/* 좌측 */}
        <div style={{ flex: 1, minWidth: 0, overflowY: "auto" }}>

          {/* 01 IC VOTING */}
          <SectionHeader n="01" name="IC VOTING" desc="승인 · 조건부 · 부결" />
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 10 }}><span style={labelStyle}>IC Voting Record</span></div>
            <div style={{ display: "flex", gap: 8 }}>
              {[["승인", T.green], ["조건부 승인", T.gold], ["부결", T.red]].map(([label, color]) => {
                const on = vote === label;
                return (
                  <button key={label as string} onClick={() => submitVote(label as string)} style={{
                    flex: 1, padding: "10px", fontSize: 12, cursor: "pointer", fontFamily: T.font, borderRadius: 4,
                    color: on ? "#080C14" : (color as string), background: on ? (color as string) : "transparent", border: `1px solid ${color as string}`,
                  }}>{label}</button>
                );
              })}
            </div>
            {vote === "조건부 승인" && (
              <div style={{ marginTop: 12, padding: "12px 14px", background: T.surface1, borderLeft: `2px solid ${T.gold}`, borderRadius: 6 }}>
                <div style={{ fontSize: 10, color: T.gold, marginBottom: 8 }}>Carve-out 조건</div>
                {(D.carve_out || ["—", "—", "—", "—"]).slice(0, 4).map((c: any, i: number) => (
                  <div key={i} style={{ display: "flex", gap: 8, padding: "4px 0" }}>
                    <span style={{ fontFamily: T.mono, fontSize: 11, color: T.gold }}>C{i + 1}</span>
                    <span style={{ fontSize: 12, color: T.muted }}>{typeof c === "string" ? c : (c.text || "—")}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 02 TERM SHEET & LOI */}
          <SectionHeader n="02" name="TERM SHEET & LOI" desc="조건 협상 · 제안서" />
          <StepCard icon={term.status ? "done" : "active"} title="① Term Sheet 작성" badge={term.status || "작성 중"}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 10 }}>
              {[["금리", term.rate], ["LTV", term.ltv], ["만기", term.maturity]].map(([k, v]) => (
                <div key={k as string} style={{ padding: "10px 12px", border: `1px solid ${T.border}`, borderRadius: 4 }}>
                  <div style={{ fontSize: 9, color: T.muted }}>{k}</div>
                  <div style={{ fontSize: 13, fontFamily: T.mono, color: v != null ? T.text : T.muted, marginTop: 4 }}>{v != null ? v : "협상 중"}</div>
                </div>
              ))}
            </div>
          </StepCard>
          <StepCard icon={term.status ? "active" : "pending"} blocked={!term.status} title="② LOI 체결" badge={term.loi_status || (term.status ? "발송 대기" : "Term Sheet 완료 후")}>
            <div style={{ fontSize: 11, color: T.muted }}>제안서 발송 → 차주 수락 확인</div>
          </StepCard>

          {/* 03 CONFIRMATORY DD */}
          <SectionHeader n="03" name="CONFIRMATORY DD" desc="Financial · Legal · Tax · Operational" />
          {[["③ Financial DD", "financial", KC], ["④ Legal DD", "legal", KC], ["⑤ Tax DD", "tax", null], ["⑥ Operational DD", "operational", null]].map(([title, key, tag], i) => {
            const st = dd[key as string] || {};
            const done = sc(st.status) === T.green;
            const active = i === 0 && !done;
            return (
              <StepCard key={key as string} icon={done ? "done" : active ? "active" : "pending"} blocked={!done && !active} title={title as string} tags={tag as any} badge={st.status || (active ? "진행 중" : "대기")}>
                {active && (
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <div style={{ flex: 1, height: 3, background: T.border, borderRadius: 2, overflow: "hidden" }}>
                      <div style={{ width: `${st.progress != null ? st.progress : 0}%`, height: "100%", background: T.gold }} />
                    </div>
                    <span style={{ fontFamily: T.mono, fontSize: 11, color: T.gold }}>{st.progress != null ? `${st.progress}%` : "—"}</span>
                  </div>
                )}
              </StepCard>
            );
          })}

          {/* 04 INSURANCE & SPA */}
          <SectionHeader n="04" name="INSURANCE & SPA" desc="보험 게이트 · SPA 체결" />
          <StepCard icon="pending" title="⑦ Insurance 게이트" badge={dd.insurance?.status || "대기"}>
            {["Key Man", "담보물 화재", "건설공사"].map(k => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.muted }}>{k}</span>
                <Badge status={dd.insurance?.[k]} />
              </div>
            ))}
          </StepCard>
          <StepCard icon="pending" blocked title="⑧ SPA 계약 체결" tags={KC} badge={dd.spa?.status || "대기"}>
            <div style={{ fontSize: 11, color: T.muted }}>carve-out 조건 반영 확인</div>
          </StepCard>

          {/* 05 CP & CLOSING */}
          <SectionHeader n="05" name="CP & CLOSING" desc="CP · 등기 · 자금조달 · 집행" />
          <StepCard icon="pending" title="⑨ CP 체크리스트 게이트" badge={`${CP_ITEMS.length - cpUnmet}/${CP_ITEMS.length}`}>
            {CP_ITEMS.map(k => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.muted }}>{k}</span>
                <span style={{ fontFamily: T.mono, color: sc(cpState(k)) }}>{cpIcon(cpState(k))}</span>
              </div>
            ))}
            <button style={{ marginTop: 10, padding: "7px 12px", fontSize: 11, cursor: "pointer", fontFamily: T.font, background: "transparent", color: T.gold, border: `1px solid ${T.gold}`, borderRadius: 4 }}>Flow of Funds Memo 생성</button>
          </StepCard>
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}`, background: T.warn }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
              <StepIcon kind="pending" />
              <span>⑩ Closing Exceptions Log</span>
              <span style={{ marginLeft: "auto", fontSize: 9, color: T.watch }}>→ 7페이지 자동 연결</span>
            </div>
            <div style={{ marginLeft: 30 }}>
              <input placeholder="예외 승인 케이스 입력…" style={{ width: "100%", boxSizing: "border-box", background: "#0A0805", border: `1px solid ${T.border}`, borderRadius: 4, color: T.text, padding: "8px 10px", fontSize: 12, outline: "none", fontFamily: T.font }} />
            </div>
          </div>
          <StepCard icon="pending" blocked title="⑪ 담보 설정 + 등기 완료">
            <div style={{ fontSize: 11, color: T.muted }}>등기부등본 검증 · 선순위 확인</div>
          </StepCard>
          <StepCard icon="pending" blocked title="⑫ 자금 조달 3단계">
            {["Capital Call Notice 발송", "자금 수령 확인", "Drawdown Notice 발송"].map(s => (
              <div key={s} style={{ display: "flex", justifyContent: "space-between", padding: "4px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.muted }}>{s}</span><span style={{ color: T.muted }}>—</span>
              </div>
            ))}
          </StepCard>
          <StepCard icon="pending" title="⑬ 엑시트 경로 추천" tags={HEPH} badge={exit.status || "AUTO"}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {[exit.recommended, ...(exit.alternatives || [])].slice(0, 4).concat(["—", "—", "—", "—"]).slice(0, 4).map((e: any, i: number) => (
                <div key={i} style={{ padding: "10px 12px", borderRadius: 4, border: i === 0 ? `1px solid ${T.gold}` : `1px solid ${T.border}` }}>
                  <div style={{ fontSize: 8, color: i === 0 ? T.gold : T.muted }}>{i === 0 ? "추천" : `대안 ${i}`}</div>
                  <div style={{ fontSize: 12, color: T.text, marginTop: 4 }}>{dash(typeof e === "string" ? e : e?.name)}</div>
                </div>
              ))}
            </div>
          </StepCard>
          <StepCard icon={executed ? "done" : "pending"} blocked={!executed && cpUnmet > 0} title="⑭ 자금 집행" badge={executed ? "완료" : (cpUnmet > 0 ? "CP 충족 후" : "집행 대기")}>
            <button disabled={cpUnmet > 0 || executed} onClick={() => setExecuted(true)} style={{
              padding: "8px 14px", fontSize: 11, cursor: cpUnmet > 0 || executed ? "default" : "pointer", fontFamily: T.font, borderRadius: 4,
              background: cpUnmet === 0 && !executed ? T.gold : "transparent", color: cpUnmet === 0 && !executed ? "#080C14" : T.muted, border: cpUnmet === 0 && !executed ? "none" : `1px solid ${T.border}`,
            }}>{executed ? "집행 완료 ✓" : "집행 완료"}</button>
          </StepCard>
          <StepCard icon={executed ? "done" : "pending"} blocked={!executed} title="⑮ Deal Status 자동 전환">
            {executed ? (
              <div style={{ fontSize: 11, color: T.green, lineHeight: 1.8 }}>
                Active → Portfolio<br />· 4페이지 편입 트리거 · 5페이지 회계 가동 · 6페이지 LP 보고 가동<br />· Closing Binder 자동 생성
              </div>
            ) : <div style={{ fontSize: 11, color: T.muted }}>집행 완료 시 Active → Portfolio 전환</div>}
          </StepCard>
        </div>

        {/* 우측: Closing Tracker (sticky) */}
        <div style={{ width: 280, flexShrink: 0, borderLeft: `1px solid ${T.border}`, overflowY: "auto", position: "sticky", top: 0, alignSelf: "flex-start", maxHeight: "100%" }}>
          {/* Confirmatory DD 서류 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
              <span style={labelStyle}>Confirmatory DD 서류</span>
              <Refresh onClick={() => fetchDocs(selId)} ts={docTs} />
            </div>
            {docs.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>—</div> : docs.map((d: any, i: number) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: sc(d.status) }} />
                <span style={{ fontSize: 11 }}>{dash(d.name || d.doc_name)}</span>
                <span style={{ marginLeft: "auto", fontSize: 10, color: sc(d.status) }}>{dash(d.status)}</span>
              </div>
            ))}
          </div>
          {/* CP 충족 현황 */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
              <span style={labelStyle}>CP 충족 현황</span>
              <Refresh onClick={() => fetchCp(selId)} ts={cpTs} />
            </div>
            {CP_ITEMS.map(k => (
              <div key={k} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontFamily: T.mono, color: sc(cpState(k)) }}>{cpIcon(cpState(k))}</span>
                <span style={{ fontSize: 11 }}>{k}</span>
                <span style={{ marginLeft: "auto", fontSize: 10, color: T.muted }}>{dash(cpState(k))}</span>
              </div>
            ))}
          </div>
          {/* Exceptions Log */}
          <div style={{ padding: "14px 16px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ marginBottom: 10 }}><span style={labelStyle}>Exceptions Log</span></div>
            {exceptions.length === 0 ? <div style={{ fontSize: 11, color: T.muted }}>예외 없음</div> : exceptions.map((e: any, i: number) => (
              <div key={i} style={{ padding: "5px 0", borderBottom: `1px solid ${T.border}` }}>
                <span style={{ fontSize: 11, color: T.watch }}>⚠ {dash(typeof e === "string" ? e : e?.text)}</span>
                <div style={{ fontSize: 9, color: T.muted, marginTop: 2 }}>→ 7페이지 자동 연결</div>
              </div>
            ))}
          </div>
          {/* 하단 요약 */}
          <div style={{ padding: "14px 16px" }}>
            <div style={{ padding: "10px 12px", background: T.warn, border: `1px solid ${T.watch}44`, borderRadius: 6, fontSize: 11, color: T.watch, lineHeight: 1.8 }}>
              CP 미충족 {cpUnmet}건<br />예외 승인 {exceptions.length}건<br />DD 서류 미수령 {docMissing}건
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
