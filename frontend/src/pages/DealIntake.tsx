import React, { useState } from "react";
import API from "../api";

// ── 디자인 상수 ───────────────────────────────────────────────
const COLORS = {
  bg: "#0a0a0a",
  border: "#1c1c1c",
  borderHover: "#2a2a2a",
  borderActive: "#C9A84C",
  gold: "#C9A84C",
  textPrimary: "#d0d0d0",
  textMuted: "#555",
  textDim: "#3a3a3a",
  warnRed: "#fb7185",
  warnGold: "#C9A84C",
  success: "#4ade80",
};

const STEP_LABELS = ["BASIC", "DEAL TYPE", "THESIS", "MOTIVE", "PORTFOLIO FIT", "KILL"];

const CHANNELS = [
  { key: "직접 발굴", desc: "현장방문·등기분석·경매·콜드" },
  { key: "브로커", desc: "중개인 소개" },
  { key: "네트워크", desc: "지인·기존 관계 추천" },
  { key: "플랫폼", desc: "거래 플랫폼·마켓플레이스" },
  { key: "기타", desc: "그 외 경로" },
];

const DEAL_TYPES = [
  { code: "DIRECT_LENDING",      mono: "DL", name: "Direct Lending",      desc: "직접 신규 여신 · 차주 신용/사업성 DD",      sdd: "당일",  sddColor: "fast" },
  { code: "DEBT_PURCHASE",       mono: "DP", name: "Debt Purchase",       desc: "채권·대출채권 매입 · 채권 유효성 + 담보 DD", sdd: "당일",  sddColor: "fast" },
  { code: "STRUCTURED_TRANCHE",  mono: "ST", name: "Structured / Tranche", desc: "구조화 참여 · 워터폴 + 인터크레디터 DD",     sdd: "1일",   sddColor: "mid" },
  { code: "DISTRESSED_SPECIAL",  mono: "DS", name: "Distressed / Special", desc: "NPL·회생·경매 · 법적 집행가능성 + 회수경로", sdd: "1-2일", sddColor: "slow" },
  { code: "EQUITY_LINKED_CREDIT", mono: "EL", name: "Equity-Linked Credit", desc: "CB·BW·메자닌 · 기업가치 + 전환조건 DD",      sdd: "1일",   sddColor: "mid" },
];

const MOTIVES = [
  "유동성 확보 (긴급 자금)",
  "만기 도래 리파이낸싱",
  "손실 확정 회피",
  "규제 / 회계 압박",
  "사업 재편 / 엑싯",
  "기타",
];

const INFO_EDGES = ["단독", "제한적", "광범위"];

const SECTORS = ["부동산 담보", "기업 일반", "인프라 / 에너지", "소비자 / 리테일", "헬스케어", "기타"];

const TIERS = [
  { code: "T1", desc: "검증된 1군 상대방" },
  { code: "T2", desc: "거래 이력 보통" },
  { code: "T3", desc: "신규 / 미검증" },
];

const COMPLEXITIES = ["단순", "중간", "복잡"];

const DEFAULT_KILL_CRITERIA = [
  "담보 선순위 구조 확인 불가",
  "양도 / 이전 법적 불가 확인",
  "내부 목표 IRR 달성 불가 구조",
  "상대방 의도적 은폐 정황",
  "회수 경로 현실적으로 부재",
  "규제 / 법적 진입 불가",
];

const SDD_COLOR: Record<string, string> = { fast: COLORS.success, mid: COLORS.gold, slow: COLORS.warnRed };

// ── 폼 데이터 타입 ────────────────────────────────────────────
interface SourcingDetail {
  channel_key: string;
  discovery_path?: string;
  discovery_note?: string;
  discovery_date?: string;
  broker_name?: string;
  broker_company?: string;
  broker_contact?: string;
  broker_history?: string;
  broker_fee?: string;
  referrer_name?: string;
  referrer_org?: string;
  referrer_type?: string;
  exclusive_share?: boolean;
  platform_name?: string;
  platform_type?: string;
  etc_note?: string;
}

interface FormData {
  dealName: string;
  channel: string;
  sourcingDetail: SourcingDetail;
  referrer: string;
  dealType: string;
  thesis: string;
  targetIrr: string;
  motive: string;
  infoEdge: string;
  tier: string;
  sector: string;
  complexity: string;
  killCriteria: string[];
  icMemo: string;
}

const EMPTY: FormData = {
  dealName: "", channel: "", sourcingDetail: { channel_key: "" }, referrer: "",
  dealType: "", thesis: "", targetIrr: "", motive: "", infoEdge: "",
  tier: "", sector: "", complexity: "", killCriteria: [], icMemo: "",
};

const isStepValid = (step: number, f: FormData): boolean => {
  switch (step) {
    case 0: {
      const baseOk = f.dealName.trim() !== "" && f.channel !== "";
      if (f.channel === "기타") return baseOk && (f.sourcingDetail.etc_note?.trim() ?? "") !== "";
      return baseOk;
    }
    case 1: return f.dealType !== "";
    case 2: return f.thesis.trim() !== "";
    case 3: return f.motive !== "" && f.infoEdge !== "";
    case 4: return f.tier !== "" && f.sector !== "" && f.complexity !== "";
    case 5: return true;
    default: return false;
  }
};

// ── 공통 UI ───────────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  width: "100%", boxSizing: "border-box", padding: "9px 12px",
  background: COLORS.bg, border: `1px solid ${COLORS.border}`,
  borderRadius: 6, color: COLORS.textPrimary, fontSize: 13, outline: "none",
  fontFamily: "inherit",
};
const labelStyle: React.CSSProperties = {
  fontSize: 10, color: COLORS.textMuted, letterSpacing: "0.1em",
  textTransform: "uppercase", marginBottom: 6,
};
const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div style={{ marginBottom: 16 }}>
    <div style={labelStyle}>{label}</div>
    {children}
  </div>
);
const Warn = ({ text, color = COLORS.warnGold }: { text: string; color?: string }) => (
  <div style={{ fontSize: 11, color, marginTop: 8, display: "flex", gap: 6, alignItems: "center" }}>
    <span>⚠</span><span>{text}</span>
  </div>
);

// 선택 카드 (라디오형)
function Choice({ active, onClick, title, sub, right }: { active: boolean; onClick: () => void; title: string; sub?: string; right?: React.ReactNode }) {
  return (
    <button onClick={onClick} style={{
      width: "100%", textAlign: "left", display: "flex", alignItems: "center", gap: 12,
      padding: "11px 14px", marginBottom: 8, cursor: "pointer",
      background: active ? "rgba(201,168,76,0.08)" : "transparent",
      border: `1px solid ${active ? COLORS.borderActive : COLORS.border}`,
      borderRadius: 8, color: COLORS.textPrimary, fontFamily: "inherit",
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13, fontWeight: active ? 700 : 500 }}>{title}</div>
        {sub && <div style={{ fontSize: 11, color: COLORS.textMuted, marginTop: 2 }}>{sub}</div>}
      </div>
      {right}
    </button>
  );
}

// ── 메인 컴포넌트 ─────────────────────────────────────────────
export interface RegisteredDeal {
  dealId: number;
  dealCode: string;
  thesis: string;
  dealType: string;
  killCriteria: string[];
}

export interface IntakePrefill {
  deal_name?: string;
  deal_type?: string;
  thesis?: string;
  sourcing_channel?: string;
}

export default function DealIntake({ onClose, onRegistered, prefill }: { onClose: () => void; onRegistered: (deal: RegisteredDeal) => void; prefill?: IntakePrefill }) {
  const [step, setStep] = useState(0);
  const [f, setF] = useState<FormData>(() => {
    if (!prefill) return EMPTY;
    const dt = DEAL_TYPES.some(d => d.code === prefill.deal_type) ? (prefill.deal_type as string) : "";
    return {
      ...EMPTY,
      dealName: prefill.deal_name || "",
      dealType: dt,
      thesis: prefill.thesis || "",
      channel: "기타",  // Signal Room 자동소싱 → 기타 채널 + 출처 메모
      sourcingDetail: { channel_key: "기타", etc_note: `자동소싱 (Signal Room${prefill.sourcing_channel ? ` · ${prefill.sourcing_channel}` : ""})` },
    };
  });
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const set = (patch: Partial<FormData>) => setF(p => ({ ...p, ...patch }));
  const setSD = (patch: Partial<SourcingDetail>) => setF(p => ({ ...p, sourcingDetail: { ...p.sourcingDetail, ...patch } }));

  // 채널 선택 → channel_key 동기화 + 자동 연동(info_edge 기본값)
  const selectChannel = (key: string) => {
    const patch: Partial<FormData> = { channel: key };
    if (key === "직접 발굴") patch.infoEdge = f.infoEdge || "단독";
    if (key === "플랫폼") patch.infoEdge = f.infoEdge || "광범위";
    setF(p => ({ ...p, ...patch, sourcingDetail: { ...p.sourcingDetail, channel_key: key } }));
  };

  // 네트워크 독점공유 → info_edge 단독 자동 태그
  const toggleExclusive = (v: boolean) => {
    setF(p => ({
      ...p,
      sourcingDetail: { ...p.sourcingDetail, exclusive_share: v },
      infoEdge: v ? "단독" : p.infoEdge,
    }));
  };

  const toggleKill = (kc: string) => {
    set({ killCriteria: f.killCriteria.includes(kc) ? f.killCriteria.filter(x => x !== kc) : [...f.killCriteria, kc] });
  };

  const submit = async () => {
    setLoading(true); setErr("");
    try {
      const r = await API.post("/deals/register", {
        deal_name: f.dealName,
        deal_type: f.dealType,
        sourcing_channel: f.channel,
        sourcing_detail: { ...f.sourcingDetail, channel_key: f.channel },
        referrer: f.referrer || null,
        thesis: f.thesis,
        target_irr: f.targetIrr || null,
        counterparty_motive: f.motive,
        info_edge: f.infoEdge,
        counterparty_tier: f.tier,
        sector: f.sector,
        complexity: f.complexity,
        kill_criteria: f.killCriteria,
        ic_memo: f.icMemo || null,
      });
      onRegistered({
        dealId: r.data.deal_id,
        dealCode: r.data.deal_code,
        thesis: f.thesis,
        dealType: f.dealType,
        killCriteria: f.killCriteria,
      });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "등록 실패");
    }
    setLoading(false);
  };

  const valid = isStepValid(step, f);
  const brokerNewWarn = f.channel === "브로커" && f.sourcingDetail.broker_history === "new";

  // ── 오버레이 래퍼 ──
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}
      onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 560, maxHeight: "88vh", display: "flex", flexDirection: "column",
        background: COLORS.bg, border: `1px solid ${COLORS.border}`, borderRadius: 12,
        color: COLORS.textPrimary, fontFamily: "'Goldman Sans', sans-serif", overflow: "hidden",
      }}>
            {/* Nav */}
            <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 20px", borderBottom: `1px solid ${COLORS.border}` }}>
              <button onClick={() => (step === 0 ? onClose() : setStep(step - 1))}
                style={{ background: "transparent", border: "none", color: COLORS.textMuted, fontSize: 16, cursor: "pointer" }}>←</button>
              <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", color: COLORS.gold }}>
                {String(step + 1).padStart(2, "0")} · {STEP_LABELS[step]}
              </div>
              <div style={{ flex: 1 }} />
              <button onClick={onClose} style={{ background: "transparent", border: "none", color: COLORS.textDim, fontSize: 14, cursor: "pointer" }}>✕</button>
            </div>

            {/* StepBar */}
            <div style={{ display: "flex", gap: 4, padding: "12px 20px 0" }}>
              {STEP_LABELS.map((_, i) => (
                <div key={i} style={{ flex: 1, height: 3, borderRadius: 2, background: i <= step ? COLORS.gold : COLORS.border }} />
              ))}
            </div>

            {/* Body */}
            <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
              {step === 0 && (
                <div>
                  <Field label="딜명 *">
                    <input value={f.dealName} onChange={e => set({ dealName: e.target.value })}
                      placeholder="예: 봉은사로 455 선순위 크레딧" style={inputStyle} />
                  </Field>
                  <div style={labelStyle}>소싱 채널 *</div>
                  {CHANNELS.map(c => (
                    <div key={c.key}>
                      <Choice active={f.channel === c.key} onClick={() => selectChannel(c.key)} title={c.key} sub={c.desc} />
                      {f.channel === c.key && (
                        <div style={{ padding: "4px 4px 12px 14px", borderLeft: `1px solid ${COLORS.border}`, marginLeft: 6, marginBottom: 8 }}>
                          {c.key === "직접 발굴" && (
                            <>
                              <Field label="발굴 경로">
                                <select value={f.sourcingDetail.discovery_path || ""} onChange={e => setSD({ discovery_path: e.target.value })} style={{ ...inputStyle, cursor: "pointer" }}>
                                  <option value="">선택</option>
                                  {["현장방문", "등기분석", "경매", "콜드", "기타"].map(o => <option key={o} value={o}>{o}</option>)}
                                </select>
                              </Field>
                              <Field label="메모"><input value={f.sourcingDetail.discovery_note || ""} onChange={e => setSD({ discovery_note: e.target.value })} style={inputStyle} /></Field>
                              <Field label="발굴일"><input type="date" value={f.sourcingDetail.discovery_date || ""} onChange={e => setSD({ discovery_date: e.target.value })} style={inputStyle} /></Field>
                            </>
                          )}
                          {c.key === "브로커" && (
                            <>
                              <Field label="브로커명"><input value={f.sourcingDetail.broker_name || ""} onChange={e => setSD({ broker_name: e.target.value })} style={inputStyle} /></Field>
                              <Field label="소속"><input value={f.sourcingDetail.broker_company || ""} onChange={e => setSD({ broker_company: e.target.value })} style={inputStyle} /></Field>
                              <Field label="연락처"><input value={f.sourcingDetail.broker_contact || ""} onChange={e => setSD({ broker_contact: e.target.value })} style={inputStyle} /></Field>
                              <Field label="거래 이력">
                                <select value={f.sourcingDetail.broker_history || ""} onChange={e => setSD({ broker_history: e.target.value })} style={{ ...inputStyle, cursor: "pointer" }}>
                                  <option value="">선택</option>
                                  <option value="verified">기존 검증됨</option>
                                  <option value="new">신규</option>
                                </select>
                              </Field>
                              <Field label="수수료">
                                <select value={f.sourcingDetail.broker_fee || ""} onChange={e => setSD({ broker_fee: e.target.value })} style={{ ...inputStyle, cursor: "pointer" }}>
                                  <option value="">선택</option>
                                  {["있음", "없음", "미정"].map(o => <option key={o} value={o}>{o}</option>)}
                                </select>
                              </Field>
                              {brokerNewWarn && <Warn text="신규 브로커 — Step 4 Tier T3 권장" />}
                            </>
                          )}
                          {c.key === "네트워크" && (
                            <>
                              <Field label="추천인"><input value={f.sourcingDetail.referrer_name || ""} onChange={e => setSD({ referrer_name: e.target.value })} style={inputStyle} /></Field>
                              <Field label="소속"><input value={f.sourcingDetail.referrer_org || ""} onChange={e => setSD({ referrer_org: e.target.value })} style={inputStyle} /></Field>
                              <Field label="관계 유형"><input value={f.sourcingDetail.referrer_type || ""} onChange={e => setSD({ referrer_type: e.target.value })} style={inputStyle} /></Field>
                              <label style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 12, color: COLORS.textPrimary, cursor: "pointer", marginTop: 4 }}>
                                <input type="checkbox" checked={!!f.sourcingDetail.exclusive_share} onChange={e => toggleExclusive(e.target.checked)} />
                                독점 공유 (단독 정보)
                              </label>
                            </>
                          )}
                          {c.key === "플랫폼" && (
                            <>
                              <Field label="플랫폼명"><input value={f.sourcingDetail.platform_name || ""} onChange={e => setSD({ platform_name: e.target.value })} style={inputStyle} /></Field>
                              <Field label="플랫폼 유형"><input value={f.sourcingDetail.platform_type || ""} onChange={e => setSD({ platform_type: e.target.value })} style={inputStyle} /></Field>
                              <Warn text="플랫폼 소싱 — 정보우위 '광범위' (경쟁 노출 높음)" color={COLORS.warnRed} />
                            </>
                          )}
                          {c.key === "기타" && (
                            <Field label="경로 설명 *"><input value={f.sourcingDetail.etc_note || ""} onChange={e => setSD({ etc_note: e.target.value })} placeholder="소싱 경로를 입력" style={inputStyle} /></Field>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {step === 1 && (
                <div>
                  {DEAL_TYPES.map(t => (
                    <Choice key={t.code} active={f.dealType === t.code} onClick={() => set({ dealType: t.code })}
                      title={`${t.name}`} sub={t.desc}
                      right={<div style={{ textAlign: "right" }}>
                        <div style={{ fontSize: 10, color: COLORS.textDim, fontFamily: "monospace" }}>{t.mono}</div>
                        <div style={{ fontSize: 10, color: SDD_COLOR[t.sddColor] }}>SDD {t.sdd}</div>
                      </div>} />
                  ))}
                </div>
              )}

              {step === 2 && (
                <div>
                  <Field label="투자 논거 (Thesis) *">
                    <textarea value={f.thesis} onChange={e => set({ thesis: e.target.value })} rows={5}
                      placeholder="왜 이 딜인가? 핵심 엣지와 수익 구조." style={{ ...inputStyle, resize: "vertical" }} />
                  </Field>
                  <Field label="목표 IRR">
                    <input value={f.targetIrr} onChange={e => set({ targetIrr: e.target.value })} placeholder="예: 15-18%" style={inputStyle} />
                  </Field>
                </div>
              )}

              {step === 3 && (
                <div>
                  <div style={labelStyle}>상대방 동기 *</div>
                  {MOTIVES.map(m => <Choice key={m} active={f.motive === m} onClick={() => set({ motive: m })} title={m} />)}
                  <div style={{ ...labelStyle, marginTop: 16 }}>정보 우위 *</div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {INFO_EDGES.map(ie => (
                      <button key={ie} onClick={() => set({ infoEdge: ie })} style={{
                        flex: 1, padding: "10px", cursor: "pointer", borderRadius: 8, fontSize: 13,
                        background: f.infoEdge === ie ? "rgba(201,168,76,0.08)" : "transparent",
                        border: `1px solid ${f.infoEdge === ie ? COLORS.borderActive : COLORS.border}`,
                        color: COLORS.textPrimary, fontWeight: f.infoEdge === ie ? 700 : 500, fontFamily: "inherit",
                      }}>{ie}</button>
                    ))}
                  </div>
                  {f.infoEdge === "광범위" && <Warn text="정보우위 낮음 — 경쟁 입찰 가능성" color={COLORS.warnRed} />}
                </div>
              )}

              {step === 4 && (
                <div>
                  <div style={labelStyle}>상대방 Tier *</div>
                  {TIERS.map(t => <Choice key={t.code} active={f.tier === t.code} onClick={() => set({ tier: t.code })} title={t.code} sub={t.desc} />)}
                  {f.tier === "T3" && <Warn text="T3 — SDD 강도 상향 권장" />}
                  <div style={{ ...labelStyle, marginTop: 16 }}>섹터 *</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {SECTORS.map(s => (
                      <button key={s} onClick={() => set({ sector: s })} style={{
                        padding: "8px 12px", cursor: "pointer", borderRadius: 8, fontSize: 12,
                        background: f.sector === s ? "rgba(201,168,76,0.08)" : "transparent",
                        border: `1px solid ${f.sector === s ? COLORS.borderActive : COLORS.border}`,
                        color: COLORS.textPrimary, fontWeight: f.sector === s ? 700 : 500, fontFamily: "inherit",
                      }}>{s}</button>
                    ))}
                  </div>
                  {f.sector === "부동산 담보" && <Warn text="부동산 담보 집중도 확인 필요 (정밀 계산 Phase 2)" />}
                  <div style={{ ...labelStyle, marginTop: 16 }}>복잡도 *</div>
                  <div style={{ display: "flex", gap: 8 }}>
                    {COMPLEXITIES.map(c => (
                      <button key={c} onClick={() => set({ complexity: c })} style={{
                        flex: 1, padding: "10px", cursor: "pointer", borderRadius: 8, fontSize: 13,
                        background: f.complexity === c ? "rgba(201,168,76,0.08)" : "transparent",
                        border: `1px solid ${f.complexity === c ? COLORS.borderActive : COLORS.border}`,
                        color: COLORS.textPrimary, fontWeight: f.complexity === c ? 700 : 500, fontFamily: "inherit",
                      }}>{c}</button>
                    ))}
                  </div>
                  {f.complexity === "복잡" && <Warn text="복잡 구조 — Complexity Premium 반영 필요" />}
                </div>
              )}

              {step === 5 && (
                <div>
                  <div style={labelStyle}>Kill Criteria (선택)</div>
                  {DEFAULT_KILL_CRITERIA.map(kc => (
                    <label key={kc} style={{ display: "flex", gap: 10, alignItems: "center", padding: "9px 12px", marginBottom: 6, cursor: "pointer",
                      border: `1px solid ${f.killCriteria.includes(kc) ? COLORS.borderActive : COLORS.border}`, borderRadius: 8, fontSize: 12 }}>
                      <input type="checkbox" checked={f.killCriteria.includes(kc)} onChange={() => toggleKill(kc)} />
                      {kc}
                    </label>
                  ))}
                  <Field label="추가 Kill 기준 (직접 입력, 줄바꿈 구분)">
                    <textarea rows={3} style={{ ...inputStyle, resize: "vertical" }}
                      placeholder="한 줄에 하나씩"
                      onChange={e => {
                        const customs = e.target.value.split("\n").map(s => s.trim()).filter(Boolean);
                        const base = f.killCriteria.filter(k => DEFAULT_KILL_CRITERIA.includes(k));
                        set({ killCriteria: [...base, ...customs] });
                      }} />
                  </Field>
                  <Field label="IC 메모 (선택)">
                    <textarea value={f.icMemo} onChange={e => set({ icMemo: e.target.value })} rows={3} style={{ ...inputStyle, resize: "vertical" }} />
                  </Field>
                </div>
              )}
            </div>

            {/* CTA */}
            <div style={{ padding: "14px 24px", borderTop: `1px solid ${COLORS.border}` }}>
              {err && <div style={{ fontSize: 12, color: COLORS.warnRed, marginBottom: 10 }}>{err}</div>}
              {step < 5 ? (
                <button disabled={!valid} onClick={() => setStep(step + 1)} style={ctaStyle(valid)}>NEXT →</button>
              ) : (
                <button disabled={loading} onClick={submit} style={ctaStyle(!loading)}>{loading ? "등록 중..." : "REGISTER →"}</button>
              )}
            </div>
      </div>
    </div>
  );
}

const ctaStyle = (enabled: boolean): React.CSSProperties => ({
  width: "100%", padding: "12px", borderRadius: 8, border: "none",
  background: enabled ? COLORS.gold : COLORS.border,
  color: enabled ? "#000" : COLORS.textMuted,
  fontSize: 13, fontWeight: 700, letterSpacing: "0.08em",
  cursor: enabled ? "pointer" : "not-allowed", fontFamily: "inherit",
});
