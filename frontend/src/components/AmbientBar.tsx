import React, { useEffect, useState } from "react";
import Spinner from "./Spinner";
import { getAmbient } from "../api";

const LEVEL_COLOR: Record<string, string> = {
  "붐빔": "#e5534b", "약간붐빔": "#e8a838", "보통": "#C9A84C",
  "여유": "#4caf7d", "N/A": "#333",
};

export default function AmbientBar() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    const fetch_ = async () => { try { setData(await getAmbient()); } catch {} };
    fetch_();
    const id = setInterval(fetch_, 5 * 60 * 1000);
    return () => clearInterval(id);
  }, []);

  if (!data) return (
    <div style={{ height: 36, background: "#111", borderBottom: "1px solid #1e1e1e", display: "flex", alignItems: "center", padding: "0 20px" }}>
      <Spinner filter="none" size={16} style={{ padding: 0 }} />
    </div>
  );

  const w = data.pressure?.weather || {};
  const heat = data.heat || {};
  const alertCount = data.alert_count || 0;
  const ts = data.timestamp ? data.timestamp.slice(11, 16) : "";

  return (
    <div style={{ height: 36, background: "#111", borderBottom: "1px solid #1e1e1e", display: "flex", alignItems: "center", padding: "0 20px", gap: 20, fontSize: 12 }}>

      <span style={{ color: "#4a4a4a", fontSize: 11 }}>{ts}</span>

      <span style={{ color: "#C9A84C", fontWeight: 500 }}>{w.temp || "—"}</span>

      <span style={{ color: "#2a2a2a" }}>·</span>

      <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
        {Object.entries(heat).map(([zone, info]: [string, any]) => (
          <span key={zone} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: LEVEL_COLOR[info.level] || "#333", display: "inline-block" }}/>
            <span style={{ color: "#6a6a6a", fontSize: 11 }}>{zone}</span>
          </span>
        ))}
      </span>

      <span style={{ color: "#2a2a2a" }}>·</span>

      <span style={{ fontSize: 11, color: alertCount > 0 ? "#e5534b" : "#4caf7d", fontWeight: 500 }}>
        {alertCount > 0 ? `${alertCount} alerts` : "Markets normal"}
      </span>

      <span style={{ marginLeft: "auto", fontSize: 11, color: "#4a4a4a" }}>
        USD/KRW {data.pressure?.rates?.USD_KRW || "—"}
      </span>
    </div>
  );
}
