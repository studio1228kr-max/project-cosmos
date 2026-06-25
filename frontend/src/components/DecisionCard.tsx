import React from "react";

const STATE_CONFIG: Record<string, { label: string; color: string }> = {
  PENDING: { label: "DECISION PENDING", color: "#C9A84C" },
  PASS: { label: "GATE PASS", color: "#4ade80" },
  HOLD: { label: "GATE HOLD", color: "#fb7185" },
  FAIL: { label: "GATE FAIL", color: "#fb7185" },
};

const CHIP_STYLE: Record<string, { border: string; text: string }> = {
  pass: { border: "rgba(74,222,128,.2)", text: "#4ade80" },
  warn: { border: "rgba(201,168,76,.2)", text: "#C9A84C" },
  fail: { border: "rgba(251,113,133,.2)", text: "#fb7185" },
};

export interface GateChip { label: string; value: string; status: "pass" | "warn" | "fail"; }

interface Props {
  gateStatus: "PENDING" | "PASS" | "HOLD" | "FAIL";
  thesis: string;
  blockers: string[];
  chips: GateChip[];
  canRequestGate: boolean;
  requesting: boolean;
  onRequestGate: () => void;
}

export default function DecisionCard({ gateStatus, thesis, blockers, chips, canRequestGate, requesting, onRequestGate }: Props) {
  const st = STATE_CONFIG[gateStatus] || STATE_CONFIG.PENDING;
  return (
    <div style={{ background: "#0f0f0f", border: `1px solid ${st.color}33`, borderLeft: `3px solid ${st.color}`, borderRadius: 12, padding: "18px 20px", marginBottom: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 800, letterSpacing: "0.12em", color: st.color, marginBottom: 12 }}>{st.label}</div>

      <div style={{ fontSize: 9, color: "#555", letterSpacing: "0.1em", marginBottom: 4 }}>THESIS</div>
      <div style={{ fontSize: 13, color: "#d0d0d0", lineHeight: 1.5, marginBottom: 14 }}>{thesis || "—"}</div>

      {blockers.length > 0 && (
        <div style={{ marginBottom: 14 }}>
          <div style={{ fontSize: 9, color: "#555", letterSpacing: "0.1em", marginBottom: 6 }}>막힌 항목 {blockers.length}</div>
          {blockers.map((b, i) => (
            <div key={i} style={{ fontSize: 12, color: "#fb7185", padding: "4px 0", display: "flex", gap: 8 }}>
              <span>→</span><span>{b}</span>
            </div>
          ))}
        </div>
      )}

      <button disabled={!canRequestGate || requesting} onClick={onRequestGate} style={{
        width: "100%", padding: "10px", borderRadius: 8, border: "none", fontSize: 12, fontWeight: 700,
        background: canRequestGate && !requesting ? "#C9A84C" : "#1c1c1c",
        color: canRequestGate && !requesting ? "#000" : "#555",
        cursor: canRequestGate && !requesting ? "pointer" : "not-allowed", marginBottom: 14,
      }}>{requesting ? "판정 중..." : "Gate 판정 요청 →"}</button>

      <div style={{ display: "flex", gap: 8 }}>
        {chips.map((c, i) => {
          const cs = CHIP_STYLE[c.status];
          return (
            <div key={i} style={{ flex: 1, padding: "8px 10px", borderRadius: 8, border: `1px solid ${cs.border}`, textAlign: "center" }}>
              <div style={{ fontSize: 9, color: "#555", marginBottom: 3 }}>{c.label}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: cs.text }}>{c.value}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
