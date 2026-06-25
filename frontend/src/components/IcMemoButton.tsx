import React from "react";

interface Props {
  sddPct: number;
  cddPct: number;
  onOpen: () => void;
}

export default function IcMemoButton({ sddPct, cddPct, onOpen }: Props) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 0", borderTop: "1px solid #1E2630" }}>
      <button onClick={onOpen} style={{ background: "transparent", border: "1px solid #C9A84C", color: "#C9A84C", borderRadius: 6, padding: "8px 18px", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
        IC 메모 작성
      </button>
      <span style={{ fontSize: 11, color: "#8B95A3" }}>SDD {sddPct}% · CDD {cddPct}%</span>
    </div>
  );
}
