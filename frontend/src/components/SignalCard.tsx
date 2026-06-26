import React from "react";

export interface Signal {
  id: number;
  external_signal_id: number;
  entity_name: string;
  entity_id: string | null;
  signal_type: string;
  aggregate_score: number;
  suggested_deal_type: string | null;
  urgency: "CRITICAL_72H" | "WATCH_2W" | "MONITOR";
  thesis_suggestion: string | null;
  reason_summary: string | null;
  status: "NEW" | "WATCHING" | "CONVERTED" | "DISMISSED";
  created_at: string;
}

export interface ReasonCode { code: string; points: number; }

// 다크 테미널 톤에 맞춘 urgency 색 (dot=accent, badge=translucent)
export const URGENCY_CONFIG: Record<string, { label: string; dot: string; text: string; bg: string }> = {
  CRITICAL_72H: { label: "긴급 72h", dot: "#E24B4A", text: "#fb7185", bg: "rgba(226,75,74,0.12)" },
  WATCH_2W:     { label: "주목 2w",  dot: "#BA7517", text: "#C9A84C", bg: "rgba(186,117,23,0.14)" },
  MONITOR:      { label: "모니터",   dot: "#888780", text: "#8B95A3", bg: "rgba(136,135,128,0.12)" },
};

export const DEAL_TYPE_LABELS: Record<string, string> = {
  DIRECT_LENDING: "DIRECT LENDING",
  DEBT_PURCHASE: "DEBT PURCHASE",
  STRUCTURED_TRANCHE: "STRUCTURED",
  DISTRESSED_SPECIAL: "DISTRESSED",
  EQUITY_LINKED_CREDIT: "EQUITY-LINKED",
};

export function parseReasons(raw: string | null): ReasonCode[] {
  if (!raw) return [];
  try {
    const p = typeof raw === "string" ? JSON.parse(raw) : raw;
    return Array.isArray(p) ? p : [];
  } catch { return []; }
}

const C = { surface: "#11161D", border: "#1E2630", text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B", gold: "#C9A84C", blue: "#6FA8FF" };

interface Props {
  signal: Signal;
  onConvert: () => void;
  onDismiss: () => void;
  onWatch: () => void;
  processing?: boolean;
}

export default function SignalCard({ signal, onConvert, onDismiss, onWatch, processing }: Props) {
  const u = URGENCY_CONFIG[signal.urgency] || URGENCY_CONFIG.MONITOR;
  const reasons = parseReasons(signal.reason_summary);
  const dtLabel = signal.suggested_deal_type
    ? (DEAL_TYPE_LABELS[signal.suggested_deal_type] || signal.suggested_deal_type)
    : null;

  return (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${u.dot}`, borderRadius: 8, padding: "16px 20px", marginBottom: 12 }}>
      {/* 상단: 법인명 + urgency + 점수 */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ width: 8, height: 8, borderRadius: "50%", background: u.dot, flexShrink: 0 }} />
          <span style={{ fontSize: 15, fontWeight: 700, color: C.text }}>{signal.entity_name || "—"}</span>
          <span style={{ fontSize: 10, fontWeight: 700, color: u.text, background: u.bg, padding: "2px 9px", borderRadius: 12, letterSpacing: "0.06em" }}>{u.label}</span>
        </div>
        <span style={{ fontSize: 13, fontWeight: 700, color: u.text, background: u.bg, padding: "3px 12px", borderRadius: 12 }}>{signal.aggregate_score ?? 0}점</span>
      </div>

      {/* 소스 태그 */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: reasons.length || signal.thesis_suggestion ? 10 : 0 }}>
        {signal.signal_type && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: "#1A2535", color: C.blue }}>{signal.signal_type}</span>}
        {signal.entity_id && <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, background: "#161c24", color: C.textDim }}>{signal.entity_id}</span>}
      </div>

      {/* reason codes */}
      {reasons.length > 0 && (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
          {reasons.map((r, i) => {
            const hot = r.points >= 30;
            return (
              <span key={i} style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, color: hot ? "#fb7185" : C.gold, border: `1px solid ${hot ? "rgba(251,113,133,0.3)" : "rgba(201,168,76,0.3)"}` }}>
                {r.code.replace(/_/g, " ")} +{r.points}
              </span>
            );
          })}
        </div>
      )}

      {/* thesis */}
      {signal.thesis_suggestion && (
        <div style={{ marginBottom: 12, display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
          <span style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.1em" }}>THESIS</span>
          <span style={{ fontSize: 12, color: C.text, lineHeight: 1.5, flex: 1, minWidth: 200 }}>{signal.thesis_suggestion}</span>
          {dtLabel && <span style={{ fontSize: 10, fontWeight: 700, color: C.gold, background: "rgba(201,168,76,0.12)", padding: "2px 8px", borderRadius: 10 }}>{dtLabel}</span>}
        </div>
      )}

      {/* 액션 */}
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onConvert} disabled={processing}
          style={{ padding: "7px 16px", background: processing ? "transparent" : C.gold, border: `1px solid ${C.gold}`, borderRadius: 6, color: processing ? C.gold : "#0A0E14", fontSize: 12, fontWeight: 700, cursor: processing ? "default" : "pointer", opacity: processing ? 0.7 : 1 }}>
          {processing ? "자동 소싱 중…" : "딜로 등록 →"}
        </button>
        <button onClick={onWatch} disabled={signal.status === "WATCHING" || processing}
          style={{ padding: "7px 14px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: signal.status === "WATCHING" ? C.textDim : C.textMid, fontSize: 12, cursor: signal.status === "WATCHING" ? "default" : "pointer" }}>
          {signal.status === "WATCHING" ? "Watching" : "Watch"}
        </button>
        <button onClick={onDismiss} style={{ padding: "7px 14px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textMid, fontSize: 12, cursor: "pointer" }}>Dismiss</button>
      </div>
    </div>
  );
}
