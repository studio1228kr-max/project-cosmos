import React, { useState, useEffect, useCallback } from "react";
import API from "../api";

interface Props {
  dealId: number;
  onClose: () => void;
}

const SECTION_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11"];
const SECTION_TITLE: Record<string, string> = {
  S1: "S1 · Executive Summary", S2: "S2 · Thesis & Catalyst", S3: "S3 · Borrower 개요",
  S4: "S4 · SDD 요약", S5: "S5 · 재무 분석", S6: "S6 · 신호 & 시퀀스",
  S7: "S7 · Narrative Gate", S8: "S8 · 위험 및 경감 방안", S9: "S9 · 딜 구조 제안",
  S10: "S10 · 판단 의견", S11: "S11 · Audit Trail",
};

export default function IcMemoModal({ dealId, onClose }: Props) {
  const [memo, setMemo] = useState<any>(null);
  const [unlock, setUnlock] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [s10, setS10] = useState("");
  const [s10Rec, setS10Rec] = useState("");
  const [s9Vals, setS9Vals] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    API.get(`/api/deals/${dealId}/ic-memo`)
      .then(r => {
        setMemo(r.data.memo);
        setUnlock(r.data.unlock);
        if (r.data.memo) {
          setS10(r.data.memo.s10_user_input || "");
          setS10Rec(r.data.memo.s10_recommendation || "");
          setS9Vals(r.data.memo.s9_user_input || {});
        }
      })
      .catch(() => { setMemo(null); setUnlock(null); })
      .finally(() => setLoading(false));
  }, [dealId]);

  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true);
    try { await API.post(`/api/deals/${dealId}/ic-memo/generate`, {}); load(); }
    catch (e: any) {
      const d = e?.response?.data?.detail;
      if (e?.response?.status === 423 && d?.unlock) { setUnlock(d.unlock); }
      else alert(typeof d === "string" ? d : "생성 실패");
    }
    setGenerating(false);
  };

  const saveInputs = async () => {
    setSaving(true);
    try {
      await API.patch(`/api/deals/${dealId}/ic-memo`, {
        s9_user_input: s9Vals, s10_user_input: s10 || null, s10_recommendation: s10Rec || null,
      });
      load();
    } catch { /* noop */ }
    setSaving(false);
  };

  const sections = memo?.sections || {};
  const s9terms: any[] = memo?.s9_terms || [];
  const gate = memo?.gate_result || unlock?.gate_result;
  const generated = !!memo;

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.8)", zIndex: 90, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 760, maxWidth: "96vw", maxHeight: "94vh", display: "flex", flexDirection: "column", background: "#0a0a0a", border: "1px solid #1e1e1e", borderRadius: 14, overflow: "hidden", color: "#d0d0d0", fontFamily: "Inter, sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "14px 20px", borderBottom: "1px solid #1e1e1e" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#C9A84C" }}>IC Memo</span>
          {gate && (
            <span style={{ fontSize: 10, fontWeight: 700, padding: "2px 10px", borderRadius: 12,
              color: gate === "CONFIRMED" ? "#4ade80" : gate === "BROKEN" ? "#fb7185" : "#C9A84C",
              background: gate === "CONFIRMED" ? "rgba(74,222,128,0.12)" : gate === "BROKEN" ? "rgba(251,113,133,0.12)" : "rgba(201,168,76,0.12)" }}>
              GATE {gate}
            </span>
          )}
          <div style={{ flex: 1 }} />
          {generated && (
            <button onClick={generate} disabled={generating} style={{ background: "transparent", border: "1px solid #1e1e1e", color: "#8B95A3", borderRadius: 6, padding: "5px 12px", fontSize: 11, cursor: "pointer" }}>
              {generating ? "재생성 중…" : "↻ 재생성"}
            </button>
          )}
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: "#555", fontSize: 18, cursor: "pointer" }}>×</button>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: "18px 22px" }}>
          {loading ? (
            <div style={{ color: "#525C6B", fontSize: 13 }}>로딩 중…</div>
          ) : (
            <>
              {/* WEAK Gate 배너 */}
              {gate === "WEAK" && (
                <div style={{ background: "rgba(201,168,76,0.08)", border: "1px solid rgba(201,168,76,0.4)", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 11, color: "#C9A84C" }}>
                  ⚠ [WEAK GATE] Narrative Gate 지지 증빙 부족 — IC 제출 전 핵심 증빙 보강을 권장합니다.
                </div>
              )}

              {/* 잠금 조건 */}
              {unlock && (
                <div style={{ background: "#11161D", border: "1px solid #1E2630", borderRadius: 8, padding: "12px 16px", marginBottom: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: unlock.unlocked ? "#4ade80" : "#fb7185", marginBottom: 8 }}>
                    {unlock.unlocked ? "🔓 잠금 해제 — 생성 가능" : "🔒 잠금 — 조건 미충족"}
                  </div>
                  {unlock.conditions.map((c: any) => (
                    <div key={c.key} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, padding: "3px 0" }}>
                      <span style={{ color: c.passed ? "#4ade80" : "#fb7185" }}>{c.passed ? "✓" : "✗"}</span>
                      <span style={{ flex: 1, color: c.passed ? "#8B95A3" : "#d0d0d0" }}>{c.label}</span>
                      <span style={{ color: "#525C6B", fontSize: 10 }}>{c.detail}</span>
                    </div>
                  ))}
                  {!generated && (
                    <button onClick={generate} disabled={generating || !unlock.unlocked}
                      style={{ marginTop: 10, width: "100%", background: unlock.unlocked ? "#C9A84C" : "transparent", border: "1px solid #C9A84C", color: unlock.unlocked ? "#0a0a0a" : "#555", borderRadius: 6, padding: "8px", fontSize: 12, fontWeight: 700, cursor: unlock.unlocked && !generating ? "pointer" : "not-allowed", opacity: generating ? 0.6 : 1 }}>
                      {generating ? "Claude 생성 중…" : unlock.unlocked ? "⚡ IC Memo 생성 (Claude)" : "조건 충족 후 생성 가능"}
                    </button>
                  )}
                </div>
              )}

              {/* 섹션 렌더 */}
              {generated && SECTION_ORDER.map(key => {
                if (key === "S9") {
                  return (
                    <div key={key} style={{ marginBottom: 18 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#C9A84C", marginBottom: 8 }}>{SECTION_TITLE.S9}</div>
                      <div style={{ fontSize: 10, color: "#f59e0b", marginBottom: 8 }}>자동 생성 불가 — 민우 입력 필요 (숫자 공란)</div>
                      {s9terms.map((t: any) => (
                        <div key={t.label} style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                          <span style={{ width: 170, fontSize: 11, color: "#8B95A3" }}>{t.label}</span>
                          <input value={s9Vals[t.label] || ""} onChange={e => setS9Vals(v => ({ ...v, [t.label]: e.target.value }))}
                            placeholder="입력 필요"
                            style={{ flex: 1, background: "#0d0d0d", border: "1px solid #1e1e1e", color: "#d0d0d0", fontSize: 11, padding: "6px 8px", borderRadius: 6 }} />
                        </div>
                      ))}
                    </div>
                  );
                }
                if (key === "S10") {
                  return (
                    <div key={key} style={{ marginBottom: 18 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#C9A84C", marginBottom: 8 }}>{SECTION_TITLE.S10}</div>
                      <div style={{ fontSize: 10, color: "#f59e0b", marginBottom: 8 }}>민우 직접 작성 (Claude 생성 금지)</div>
                      <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                        {["PROMOTE", "CONDITIONAL", "HOLD"].map(r => (
                          <button key={r} onClick={() => setS10Rec(r)} style={{
                            flex: 1, padding: "6px", borderRadius: 6, fontSize: 11, fontWeight: s10Rec === r ? 700 : 500,
                            border: `1px solid ${s10Rec === r ? "#C9A84C" : "#1e1e1e"}`,
                            background: s10Rec === r ? "rgba(201,168,76,0.1)" : "transparent",
                            color: s10Rec === r ? "#C9A84C" : "#8B95A3", cursor: "pointer",
                          }}>{r}</button>
                        ))}
                      </div>
                      <textarea value={s10} onChange={e => setS10(e.target.value)} rows={4} placeholder="Promote / Conditional / Hold 사유 작성"
                        style={{ width: "100%", boxSizing: "border-box", background: "#0d0d0d", border: "1px solid #1e1e1e", color: "#d0d0d0", fontSize: 11, padding: "8px", borderRadius: 6, resize: "vertical" }} />
                      <button onClick={saveInputs} disabled={saving}
                        style={{ marginTop: 8, background: "#C9A84C", border: "none", color: "#0a0a0a", borderRadius: 6, padding: "7px 16px", fontSize: 11, fontWeight: 700, cursor: "pointer", opacity: saving ? 0.6 : 1 }}>
                        {saving ? "저장 중…" : "S9·S10 저장"}
                      </button>
                    </div>
                  );
                }
                const body = sections[key];
                if (!body) return null;
                return (
                  <div key={key} style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: "#C9A84C", marginBottom: 6 }}>{SECTION_TITLE[key]}</div>
                    <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontFamily: "inherit", fontSize: 11.5, lineHeight: 1.6, color: "#c8ccd2", margin: 0 }}>{String(body)}</pre>
                  </div>
                );
              })}

              {generated && (
                <div style={{ fontSize: 10, color: "#3a3a3a", marginTop: 8 }}>
                  prompt_version {memo.prompt_version} · {memo.model} · {new Date(memo.generated_at).toLocaleString()}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
