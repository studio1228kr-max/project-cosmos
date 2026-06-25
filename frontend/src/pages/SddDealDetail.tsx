import React, { useState, useEffect, useCallback } from "react";
import API from "../api";
import DecisionCard, { GateChip } from "../components/DecisionCard";
import ObservationPanel from "../components/ObservationPanel";
import SddChecklistPanel from "../components/SddChecklistPanel";
import IcMemoButton from "../components/IcMemoButton";

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

  const load = useCallback(() => {
    setLoading(true);
    API.get(`/deals/${dealId}/detail`)
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [dealId]);

  useEffect(() => { load(); }, [load]);

  const deal = data?.deal;
  const checklist: any[] = data?.checklist || [];
  const observations: any[] = data?.observations || [];
  const latestGate = data?.latest_gate;

  const sddPct = tierPct(checklist, "SDD");
  const cddPct = tierPct(checklist, "CDD");
  const activePct = tierPct(checklist, tier);
  const tierItems = checklist.filter(i => i.dd_tier === tier);

  const rfCount = observations.filter(o => o.severity === "CRITICAL" || o.severity === "FATAL").length;
  const blockers = tierItems.filter(i => i.status === "PENDING" || i.status === "REVIEW").map(i => i.item_name).slice(0, 3);

  let gateStatus: "PENDING" | "PASS" | "HOLD" | "FAIL" = "PENDING";
  if (latestGate?.final_gate === "PASS") gateStatus = "PASS";
  else if (latestGate?.final_gate === "HOLD") gateStatus = "HOLD";
  else if (latestGate?.final_gate === "FAIL") gateStatus = "FAIL";

  const chips: GateChip[] = [
    { label: "체크리스트", value: `${activePct}%`, status: activePct >= 80 ? "pass" : activePct >= 50 ? "warn" : "fail" },
    { label: "Red Flag", value: rfCount > 0 ? "CRITICAL" : "CLEAR", status: rfCount > 0 ? "fail" : "pass" },
    { label: "Narrative", value: "PENDING", status: "warn" },
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

              <ObservationPanel dealId={dealId} observations={observations} onAdded={load} />
              <SddChecklistPanel items={tierItems} onUpdate={load} />
              <IcMemoButton sddPct={sddPct} cddPct={cddPct} onOpen={() => alert("IC 메모 작성 — 외부 투심위 제출 포맷 자동생성은 Phase 2")} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
