import React from "react";

const C = {
  surface: "#11161D", border: "#1E2630",
  text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B",
  gold: "#C9A84C", green: "#4ade80",
};

const DEAL_TYPE_LABEL: Record<string, string> = {
  DIRECT_LENDING: "Direct Lending",
  DEBT_PURCHASE: "Debt Purchase",
  STRUCTURED_TRANCHE: "Structured Tranche",
  DISTRESSED_SPECIAL: "Distressed/Special",
  EQUITY_LINKED_CREDIT: "Equity-Linked Credit",
};

const barColor = (pct: number) => (pct >= 80 ? C.green : C.gold);

const statusText = (stage: string, pct: number) => {
  if (stage === "SDD" && pct === 0) return "Kill Check PASS · SDD 대기";
  if (stage === "SDD") return `SDD ${pct}%`;
  if (stage === "CDD") return `CDD ${pct}%`;
  if (stage === "EDD") return `EDD ${pct}%`;
  return stage;
};

export interface DealCardProps {
  dealCode: string;
  dealType: string;
  thesis?: string;
  stage: string;
  closingPct: number;
  onView: () => void;
}

export default function DealCard({ dealCode, dealType, thesis, stage, closingPct, onView }: DealCardProps) {
  const pct = Math.max(0, Math.min(100, closingPct || 0));
  const typeLabel = DEAL_TYPE_LABEL[dealType] || dealType || "—";
  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "14px 18px", marginBottom: 10 }}>
      {/* 헤더 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.text, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.04em" }}>{dealCode}</div>
          <div style={{ marginTop: 5, display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 12, background: "#1A2535", color: "#6FA8FF" }}>{typeLabel}</span>
          </div>
          {thesis && <div style={{ fontSize: 11, color: C.textDim, marginTop: 6, maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{thesis}</div>}
        </div>
        <button onClick={onView} style={{ padding: "5px 14px", background: "transparent", border: `1px solid ${C.gold}`, borderRadius: 6, color: C.gold, fontSize: 11, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>보기</button>
      </div>

      {/* 클로징 진행바 */}
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: C.textDim }}>딜 클로징</span>
        <span style={{ fontSize: 11, color: C.textMid }}>{pct}%</span>
      </div>
      <div style={{ background: C.border, borderRadius: 4, height: 4, marginBottom: 8 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: barColor(pct), borderRadius: 4 }} />
      </div>
      <div style={{ fontSize: 11, color: C.textMid }}>{statusText(stage, pct)}</div>
    </div>
  );
}
