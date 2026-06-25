import React, { useState } from "react";
import API from "../api";

const OBS_TYPES = ["현장관찰", "경영진태도", "직원인터뷰", "간접신호", "문서외정황"];
const SEVERITIES = ["INFO", "WATCH", "REVIEW", "CRITICAL", "FATAL"];
const SEV_COLOR: Record<string, string> = {
  INFO: "#555", WATCH: "#888", REVIEW: "#C9A84C", CRITICAL: "#fb7185", FATAL: "#fb7185",
};

interface Props {
  dealId: number;
  observations: any[];
  onAdded: () => void;
}

export default function ObservationPanel({ dealId, observations, onAdded }: Props) {
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ obs_type: OBS_TYPES[0], severity: "INFO", obs_text: "" });
  const [saving, setSaving] = useState(false);

  const critical = observations.filter(o => o.severity === "CRITICAL" || o.severity === "FATAL").length;

  const submit = async () => {
    if (!form.obs_text.trim()) return;
    setSaving(true);
    try {
      await API.post("/deals/observation", { deal_id: dealId, ...form });
      setForm({ obs_type: OBS_TYPES[0], severity: "INFO", obs_text: "" });
      setOpen(false);
      onAdded();
    } catch { /* noop */ }
    setSaving(false);
  };

  const sel: React.CSSProperties = { background: "#0d0d0d", border: "1px solid #1e1e1e", color: "#d0d0d0", padding: "6px 10px", fontSize: 12, borderRadius: 6 };

  return (
    <div style={{ background: "#11161D", border: "1px solid #1E2630", borderRadius: 8, padding: "12px 16px", marginBottom: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 12, color: "#d0d0d0", fontWeight: 600 }}>현장관찰</span>
        <span style={{ fontSize: 11, color: "#8B95A3" }}>· {observations.length}건</span>
        {critical > 0 && <span style={{ fontSize: 11, color: "#fb7185" }}>· CRITICAL {critical}</span>}
        <div style={{ flex: 1 }} />
        <button onClick={() => setOpen(o => !o)} style={{ background: "transparent", border: "1px solid #C9A84C", color: "#C9A84C", borderRadius: 6, padding: "4px 12px", fontSize: 11, cursor: "pointer" }}>
          {open ? "닫기" : "+ 추가"}
        </button>
      </div>

      {open && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ display: "flex", gap: 8 }}>
            <select value={form.obs_type} onChange={e => setForm({ ...form, obs_type: e.target.value })} style={{ ...sel, flex: 1, cursor: "pointer" }}>
              {OBS_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={form.severity} onChange={e => setForm({ ...form, severity: e.target.value })} style={{ ...sel, flex: 1, cursor: "pointer", color: SEV_COLOR[form.severity] }}>
              {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <textarea value={form.obs_text} onChange={e => setForm({ ...form, obs_text: e.target.value })} rows={3}
            placeholder="관찰 내용" style={{ ...sel, width: "100%", boxSizing: "border-box", resize: "vertical" }} />
          <button disabled={saving || !form.obs_text.trim()} onClick={submit} style={{
            alignSelf: "flex-end", background: form.obs_text.trim() ? "#C9A84C" : "#1c1c1c",
            color: form.obs_text.trim() ? "#000" : "#555", border: "none", borderRadius: 6, padding: "6px 16px",
            fontSize: 12, fontWeight: 700, cursor: form.obs_text.trim() ? "pointer" : "not-allowed",
          }}>{saving ? "저장 중..." : "추가"}</button>
        </div>
      )}

      {observations.length > 0 && (
        <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 6 }}>
          {observations.map(o => (
            <div key={o.id} style={{ display: "flex", gap: 8, alignItems: "baseline", fontSize: 12 }}>
              <span style={{ fontSize: 10, color: SEV_COLOR[o.severity] || "#555", fontWeight: 700, minWidth: 56 }}>{o.severity}</span>
              <span style={{ fontSize: 10, color: "#525C6B", minWidth: 64 }}>{o.obs_type}</span>
              <span style={{ flex: 1, color: "#d0d0d0" }}>{o.obs_text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
