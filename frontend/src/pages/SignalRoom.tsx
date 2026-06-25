import { useState, useEffect, useCallback } from "react";
import API from "../api";

export interface SignalPrefill {
  deal_name: string;
  deal_type: string;
  thesis: string;
  sourcing_channel: string;
}

const C = {
  bg: "#0A0E14", surface: "#11161D", border: "#1E2630",
  text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B",
  gold: "#C9A84C", red: "#E5484D", green: "#2BC48A", blue: "#6FA8FF",
};

const URGENCY: Record<string, { label: string; color: string; bg: string }> = {
  CRITICAL_72H: { label: "CRITICAL · 72H", color: "#fb7185", bg: "rgba(229,72,77,0.10)" },
  WATCH_2W: { label: "WATCH · 2W", color: "#C9A84C", bg: "rgba(201,168,76,0.10)" },
  MONITOR: { label: "MONITOR", color: "#8B95A3", bg: "rgba(139,149,163,0.08)" },
};

const DEAL_TYPE_LABEL: Record<string, string> = {
  DIRECT_LENDING: "Direct Lending", DEBT_PURCHASE: "Debt Purchase",
  STRUCTURED_TRANCHE: "Structured Tranche", DISTRESSED_SPECIAL: "Distressed/Special",
  EQUITY_LINKED_CREDIT: "Equity-Linked Credit",
};

function parseReasons(raw: any): { code: string; points?: number }[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  try { const p = JSON.parse(raw); return Array.isArray(p) ? p : []; } catch { return []; }
}

export default function SignalRoom({ onConvert }: { onConvert: (p: SignalPrefill) => void }) {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [converting, setConverting] = useState<number | null>(null);

  const load = useCallback(() => {
    setLoading(true); setErr("");
    API.get("/api/signals")
      .then(r => setSignals(Array.isArray(r.data.signals) ? r.data.signals : []))
      .catch(e => setErr(e?.response?.data?.detail || "조회 실패"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const convert = (id: number) => {
    setConverting(id);
    API.post(`/api/signals/${id}/convert`)
      .then(r => onConvert(r.data.prefill))
      .catch(e => setErr(e?.response?.data?.detail || "전환 실패"))
      .finally(() => setConverting(null));
  };

  return (
    <div style={{ flex: 1, overflow: "auto", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", padding: "32px 40px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
          <div>
            <div style={{ fontSize: 11, color: C.textDim, letterSpacing: "0.12em", marginBottom: 4 }}>COSMOS / SIGNAL ROOM</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>자동 소싱 신호</div>
          </div>
          <button onClick={load} style={{ padding: "7px 16px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textMid, fontSize: 12, cursor: "pointer" }}>↻ 새로고침</button>
        </div>
        <div style={{ fontSize: 11, color: C.textDim, marginBottom: 24 }}>data-pipeline 스코어링 신호 · 긴급도→점수 순 · NEW 상태만</div>

        {err && <div style={{ fontSize: 12, color: C.red, marginBottom: 12 }}>{err}</div>}
        {loading ? (
          <div style={{ color: C.textDim, fontSize: 13, padding: 40 }}>로딩 중...</div>
        ) : signals.length === 0 ? (
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: 14, color: C.textDim }}>신규 신호 없음</div>
            <div style={{ fontSize: 11, color: C.textDim, marginTop: 6 }}>data-pipeline scan이 신호를 수집하면 여기에 표시됩니다</div>
          </div>
        ) : (
          signals.map(s => {
            const u = URGENCY[s.urgency] || URGENCY.MONITOR;
            const reasons = parseReasons(s.reason_summary);
            const dtLabel = s.suggested_deal_type ? (DEAL_TYPE_LABEL[s.suggested_deal_type] || s.suggested_deal_type) : null;
            return (
              <div key={s.id} style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${u.color}`, borderRadius: 8, padding: "16px 20px", marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: u.color, background: u.bg, padding: "2px 10px", borderRadius: 12, letterSpacing: "0.06em" }}>{u.label}</span>
                      <span style={{ fontSize: 15, fontWeight: 700 }}>{s.entity_name || "—"}</span>
                      <span style={{ fontSize: 11, color: C.textDim }}>점수 {s.aggregate_score ?? 0}</span>
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
                      {s.signal_type && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: "#1A2535", color: C.blue }}>{s.signal_type}</span>}
                      {dtLabel && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: "rgba(201,168,76,0.12)", color: C.gold }}>제안: {dtLabel}</span>}
                    </div>
                    {s.thesis_suggestion && <div style={{ fontSize: 12, color: C.text, lineHeight: 1.5, marginBottom: 8 }}>{s.thesis_suggestion}</div>}
                    {reasons.length > 0 && (
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                        {reasons.map((rc, i) => (
                          <span key={i} style={{ fontSize: 10, color: C.textMid, border: `1px solid ${C.border}`, borderRadius: 4, padding: "1px 6px" }}>
                            {rc.code}{rc.points != null ? ` +${rc.points}` : ""}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button disabled={converting === s.id} onClick={() => convert(s.id)}
                    style={{ marginLeft: 16, padding: "7px 16px", background: C.gold, border: "none", borderRadius: 6, color: "#0A0E14", fontSize: 12, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap", opacity: converting === s.id ? 0.6 : 1 }}>
                    {converting === s.id ? "전환 중..." : "딜로 전환 →"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
