import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import DecisionCard, { GateChip } from "../components/DecisionCard";
import ObservationPanel from "../components/ObservationPanel";
import SddChecklistPanel from "../components/SddChecklistPanel";
import IcMemoButton from "../components/IcMemoButton";
import IcMemoModal from "../components/IcMemoModal";

const TIERS = ["SDD", "CDD", "EDD"] as const;
type Tier = typeof TIERS[number];

const DONE_STATUSES = ["VERIFIED", "RECEIVED"];

function tierPct(items: any[], tier: Tier): number {
  const list = items.filter(i => i.dd_tier === tier);
  if (list.length === 0) return 0;
  const done = list.filter(i => DONE_STATUSES.includes(i.status)).length;
  return Math.round((done / list.length) * 100);
}

interface Props {
  dealId: number;
  onClose: () => void;
}

export default function SddDealDetail({ dealId, onClose }: Props) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tier, setTier] = useState<Tier>("SDD");
  const [requesting, setRequesting] = useState(false);
  const [narrative, setNarrative] = useState<any>(null);
  const [selThesis, setSelThesis] = useState<string>("");
  const [gateRunning, setGateRunning] = useState(false);
  const [autoRunning, setAutoRunning] = useState(false);
  const [icMemoOpen, setIcMemoOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    API.get(`/deals/${dealId}/detail`)
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [dealId]);

  const loadNarrative = useCallback(() => {
    API.get(`/api/deals/${dealId}/narrative-gate`)
      .then(r => {
        setNarrative(r.data);
        const cur = r.data.current_thesis_type || r.data.available_thesis_types?.[0]?.thesis_type || "";
        setSelThesis(prev => prev || cur);
      })
      .catch(() => {});
  }, [dealId]);

  useEffect(() => { load(); loadNarrative(); }, [load, loadNarrative]);

  const deal = data?.deal;
  const checklist: any[] = data?.checklist || [];
  const observations: any[] = data?.observations || [];
  const latestGate = data?.latest_gate;

  const sddPct = tierPct(checklist, "SDD");
  const cddPct = tierPct(checklist, "CDD");
  const activePct = tierPct(checklist, tier);
  const tierItems = checklist.filter(i => i.dd_tier === tier);

  // SDD AUTO 품질 — data_as_of 6개월 경과 / NOT_AVAILABLE 다수
  const STALE_MS = 183 * 24 * 60 * 60 * 1000;
  const sddItems = checklist.filter(i => i.dd_tier === "SDD");
  const staleCount = sddItems.filter(i => i.data_as_of && (Date.now() - new Date(i.data_as_of).getTime() > STALE_MS)).length;
  const naCount = sddItems.filter(i => i.item_status === "NOT_AVAILABLE").length;
  const autoFilled = sddItems.some(i => i.data_source);

  const autoPopulate = async () => {
    setAutoRunning(true);
    try { await API.post(`/api/deals/${dealId}/sdd/auto-populate`, {}); load(); loadNarrative(); }
    catch (e: any) { alert(e?.response?.data?.detail || "자동 채움 실패 — corp_code(DART) 미등록일 수 있음"); }
    setAutoRunning(false);
  };

  const rfCount = observations.filter(o => o.severity === "CRITICAL" || o.severity === "FATAL").length;
  const blockers = tierItems.filter(i => i.status === "PENDING" || i.status === "REVIEW").map(i => i.item_name).slice(0, 3);

  let gateStatus: "PENDING" | "PASS" | "HOLD" | "FAIL" = "PENDING";
  if (latestGate?.final_gate === "PASS") gateStatus = "PASS";
  else if (latestGate?.final_gate === "HOLD") gateStatus = "HOLD";
  else if (latestGate?.final_gate === "FAIL") gateStatus = "FAIL";

  const ng = narrative?.latest;
  const ngResult: string | undefined = ng?.gate_result;
  const ngChip: "pass" | "warn" | "fail" = ngResult === "CONFIRMED" ? "pass" : ngResult === "BROKEN" ? "fail" : "warn";
  const chips: GateChip[] = [
    { label: "체크리스트", value: `${activePct}%`, status: activePct >= 80 ? "pass" : activePct >= 50 ? "warn" : "fail" },
    { label: "Red Flag", value: rfCount > 0 ? "CRITICAL" : "CLEAR", status: rfCount > 0 ? "fail" : "pass" },
    { label: "Narrative", value: ngResult || "PENDING", status: ngChip },
  ];
  const canRequestGate = blockers.length === 0 && rfCount === 0;

  const isCddUnlocked = deal?.stage === "CDD" || deal?.stage === "EDD";
  const isEddUnlocked = deal?.stage === "EDD";
  const tierLocked = (t: Tier) => (t === "CDD" && !isCddUnlocked) || (t === "EDD" && !isEddUnlocked);

  const requestGate = async () => {
    setRequesting(true);
    try { await API.post("/deals/gate/request", { deal_id: dealId, dd_tier: tier }); load(); }
    catch { /* noop */ }
    setRequesting(false);
  };

  const runGate = async (thesis?: string) => {
    const t = thesis || selThesis;
    if (!t) return;
    setGateRunning(true);
    try { await API.post(`/api/deals/${dealId}/narrative-gate`, { thesis_type: t }); loadNarrative(); }
    catch { /* noop */ }
    setGateRunning(false);
  };

  // WEAK 확인: 미확인 핵심 증빙을 CONFIRMED 처리 후 재평가
  const confirmMissing = async () => {
    const missing = ng?.missing_evidence || [];
    setGateRunning(true);
    try {
      for (const m of missing) {
        const it = checklist.find((i: any) => i.item_code === m.item_code);
        if (it) await API.patch("/deals/checklist/item", { item_id: it.id, status: it.status, item_status: "CONFIRMED" });
      }
      await API.post(`/api/deals/${dealId}/narrative-gate`, { thesis_type: selThesis });
      loadNarrative(); load();
    } catch { /* noop */ }
    setGateRunning(false);
  };

  const selectTier = (t: Tier) => {
    if (tierLocked(t)) {
      alert(t === "CDD" ? "SDD Gate PASS 후 열립니다" : "IC 메모 외부 제출 후 열립니다");
      return;
    }
    setTier(t);
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 70, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 680, maxWidth: "94vw", maxHeight: "92vh", display: "flex", flexDirection: "column", background: "#0a0a0a", border: "1px solid #1e1e1e", borderRadius: 14, overflow: "hidden", color: "#d0d0d0", fontFamily: "Inter, sans-serif" }}>
        {/* Nav */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 20px", borderBottom: "1px solid #1e1e1e" }}>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#555", fontSize: 16, cursor: "pointer" }}>←</button>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#C9A84C", fontFamily: "'IBM Plex Mono', monospace" }}>{deal?.deal_code || "…"}</span>
          <div style={{ flex: 1 }} />
          <button onClick={autoPopulate} disabled={autoRunning}
            style={{ background: autoRunning ? "transparent" : "rgba(201,168,76,0.1)", border: "1px solid #C9A84C", color: "#C9A84C", borderRadius: 6, padding: "4px 12px", fontSize: 11, fontWeight: 700, cursor: autoRunning ? "default" : "pointer", opacity: autoRunning ? 0.6 : 1 }}>
            {autoRunning ? "채우는 중…" : "⚡ 자동 채움"}
          </button>
          <button onClick={load} style={{ background: "transparent", border: "1px solid #1e1e1e", color: "#8B95A3", borderRadius: 6, padding: "4px 12px", fontSize: 11, cursor: "pointer" }}>↻ 자동반영</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "18px 20px" }}>
          {loading && !deal ? (
            <div style={{ color: "#525C6B", fontSize: 13, padding: 20 }}>로딩 중...</div>
          ) : !deal ? (
            <div style={{ color: "#fb7185", fontSize: 13, padding: 20 }}>딜을 불러올 수 없습니다.</div>
          ) : (
            <>
              <DecisionCard gateStatus={gateStatus} thesis={deal.thesis} blockers={blockers}
                chips={chips} canRequestGate={canRequestGate} requesting={requesting} onRequestGate={requestGate} />

              {/* 딜 클로징 + 티어 탭 */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: "#525C6B" }}>딜 클로징</span>
                  <span style={{ fontSize: 11, color: "#8B95A3" }}>{activePct}%</span>
                </div>
                <div style={{ background: "#1E2630", borderRadius: 4, height: 4, marginBottom: 10 }}>
                  <div style={{ width: `${activePct}%`, height: "100%", background: activePct >= 80 ? "#4ade80" : "#C9A84C", borderRadius: 4 }} />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  {TIERS.map(t => {
                    const locked = tierLocked(t);
                    const active = tier === t;
                    return (
                      <button key={t} onClick={() => selectTier(t)} style={{
                        flex: 1, padding: "8px", borderRadius: 6, fontSize: 11, fontWeight: active ? 700 : 500,
                        border: `1px solid ${active ? "#C9A84C" : "#1e1e1e"}`,
                        background: active ? "rgba(201,168,76,0.08)" : "transparent",
                        color: locked ? "#3a3a3a" : active ? "#C9A84C" : "#8B95A3",
                        cursor: locked ? "not-allowed" : "pointer",
                      }}>{t}{locked ? " 🔒" : ""}</button>
                    );
                  })}
                </div>
              </div>

              {/* Narrative Gate */}
              <div style={{ background: "#11161D", border: "1px solid #1E2630", borderRadius: 8, padding: "14px 16px", marginBottom: 16 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: "#d0d0d0" }}>Narrative Gate</span>
                  {ngResult && (
                    <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 10px", borderRadius: 12,
                      color: ngResult === "CONFIRMED" ? "#4ade80" : ngResult === "BROKEN" ? "#fb7185" : "#C9A84C",
                      background: ngResult === "CONFIRMED" ? "rgba(74,222,128,0.12)" : ngResult === "BROKEN" ? "rgba(251,113,133,0.12)" : "rgba(201,168,76,0.12)" }}>{ngResult}</span>
                  )}
                  <div style={{ flex: 1 }} />
                  <select value={selThesis} onChange={e => setSelThesis(e.target.value)}
                    style={{ background: "#0d0d0d", border: "1px solid #1e1e1e", color: "#d0d0d0", fontSize: 11, padding: "5px 8px", borderRadius: 6, cursor: "pointer" }}>
                    {(narrative?.available_thesis_types || []).map((t: any) => <option key={t.thesis_type} value={t.thesis_type}>{t.label}</option>)}
                  </select>
                  <button onClick={() => runGate()} disabled={gateRunning || !selThesis}
                    style={{ background: "#C9A84C", border: "none", borderRadius: 6, color: "#0a0a0a", fontSize: 11, fontWeight: 700, padding: "6px 14px", cursor: gateRunning ? "default" : "pointer", opacity: gateRunning ? 0.6 : 1 }}>
                    {gateRunning ? "평가 중..." : "Gate 평가"}
                  </button>
                </div>
                {ng ? (
                  <div>
                    <div style={{ fontSize: 12, color: "#8B95A3", marginBottom: 6 }}>{ng.auto_reason}</div>
                    <div style={{ fontSize: 11, color: "#525C6B", marginBottom: 8 }}>지지 증빙 확정 {ng.supported_count}건 · thesis: {ng.thesis_type}</div>
                    {ng.missing_evidence?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <span style={{ fontSize: 10, color: "#525C6B" }}>미확인: </span>
                        {ng.missing_evidence.map((m: any, i: number) => (
                          <span key={i} style={{ fontSize: 10, color: "#C9A84C", border: "1px solid rgba(201,168,76,0.25)", borderRadius: 4, padding: "1px 6px", marginRight: 4, display: "inline-block", marginBottom: 4 }}>{m.item_name}</span>
                        ))}
                      </div>
                    )}
                    {ng.contradicted_items?.length > 0 && (
                      <div style={{ marginBottom: 8 }}>
                        <span style={{ fontSize: 10, color: "#fb7185" }}>⛔ 반박: </span>
                        {ng.contradicted_items.map((c: any, i: number) => (
                          <span key={i} style={{ fontSize: 10, color: "#fb7185", border: "1px solid rgba(251,113,133,0.25)", borderRadius: 4, padding: "1px 6px", marginRight: 4, display: "inline-block", marginBottom: 4 }}>{c.item_name}</span>
                        ))}
                      </div>
                    )}
                    {ngResult === "WEAK" && (
                      <button onClick={confirmMissing} disabled={gateRunning}
                        style={{ background: "transparent", border: "1px solid #C9A84C", color: "#C9A84C", borderRadius: 6, fontSize: 11, fontWeight: 600, padding: "6px 14px", cursor: "pointer" }}>
                        미확인 증빙 확인 후 재평가
                      </button>
                    )}
                    {ngResult === "BROKEN" && (
                      <div style={{ fontSize: 11, color: "#fb7185", marginTop: 4 }}>⚠ Thesis 성립 불가 — 위에서 thesis를 변경(재작성)하고 [Gate 평가]를 다시 실행하세요.</div>
                    )}
                  </div>
                ) : (
                  <div style={{ fontSize: 11, color: "#525C6B" }}>아직 미평가 — thesis 선택 후 [Gate 평가] 실행</div>
                )}
              </div>

              <ObservationPanel dealId={dealId} observations={observations} onAdded={load} />

              {/* SDD AUTO 품질 배너 */}
              {tier === "SDD" && staleCount > 0 && (
                <div style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.35)", borderRadius: 8, padding: "10px 14px", marginBottom: 12, fontSize: 11, color: "#f59e0b" }}>
                  ⚠ 자동 데이터 {staleCount}건이 6개월 이상 경과 — IC 전 재확인이 요구됩니다.
                </div>
              )}
              {tier === "SDD" && naCount >= 3 && (
                <div style={{ background: "rgba(251,113,133,0.07)", border: "1px solid rgba(251,113,133,0.3)", borderRadius: 8, padding: "10px 14px", marginBottom: 12, fontSize: 11, color: "#fb7185" }}>
                  ⚠ 정보 미확인(NOT_AVAILABLE) 항목 {naCount}건 — IC 전 재검토를 권장합니다.
                </div>
              )}
              {tier === "SDD" && !autoFilled && (
                <div style={{ background: "rgba(201,168,76,0.05)", border: "1px dashed rgba(201,168,76,0.3)", borderRadius: 8, padding: "10px 14px", marginBottom: 12, fontSize: 11, color: "#8B95A3" }}>
                  상단 [⚡ 자동 채움]으로 DART 기반 AUTO 항목을 일괄 채울 수 있습니다.
                </div>
              )}

              <SddChecklistPanel items={tierItems} onUpdate={load} />
              <IcMemoButton sddPct={sddPct} cddPct={cddPct} onOpen={() => setIcMemoOpen(true)} />
              {icMemoOpen && <IcMemoModal dealId={dealId} onClose={() => { setIcMemoOpen(false); load(); }} />}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
