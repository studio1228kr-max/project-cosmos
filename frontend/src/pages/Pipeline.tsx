import React, { useEffect, useState } from "react";
import API from "../api";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444",
};

const GATE_CFG: any = {
  HOLD:        { color: "#F59E0B", label: "HOLD" },
  RESTRUCTURE: { color: "#3B82F6", label: "RESTR" },
  ADVANCE:     { color: "#22C55E", label: "ADV" },
  REJECT:      { color: "#EF4444", label: "REJ" },
};

function DeleteModal({ dealName, onConfirm, onCancel }: { dealName: string; onConfirm: () => void; onCancel: () => void }) {
  const [input, setInput] = useState("");
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
      <div style={{ background: "#0D1420", border: "1px solid #333", borderRadius: 8, padding: 32, width: 420 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: C.red, marginBottom: 12 }}>딜 영구 삭제</div>
        <div style={{ fontSize: 13, color: C.textMid, marginBottom: 8 }}>
          <span style={{ color: C.red }}>{dealName}</span> 을 영구 삭제합니다.
        </div>
        <div style={{ fontSize: 11, color: C.textDim, marginBottom: 16 }}>
          확인하려면 <strong style={{ color: C.text }}>삭제하겠습니다</strong> 를 입력하세요.
        </div>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="삭제하겠습니다"
          style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 13, outline: "none", boxSizing: "border-box", marginBottom: 16, fontFamily: "inherit" }}/>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onCancel} style={{ padding: "7px 16px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textDim, fontSize: 12, cursor: "pointer" }}>취소</button>
          <button onClick={onConfirm} disabled={input !== "삭제하겠습니다"}
            style={{ padding: "7px 16px", background: input === "삭제하겠습니다" ? C.red : "#1A2638", border: "none", borderRadius: 4, color: "#fff", fontSize: 12, cursor: input === "삭제하겠습니다" ? "pointer" : "not-allowed" }}>
            삭제
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Pipeline({ onSelectDeal }: { onSelectDeal?: (id: string) => void }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [deleteTarget, setDeleteTarget] = useState<{code: string; name: string} | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetch = async () => {
    setLoading(true);
    try { const r = await API.get("/api/risk-book/deals"); setDeals(r.data); } catch {}
    setLoading(false);
  };

  useEffect(() => { fetch(); }, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await API.delete(`/api/risk-book/deals/${deleteTarget.code}`);
      setDeleteTarget(null);
      if (selected?.deal_code === deleteTarget.code) setSelected(null);
      fetch();
    } catch { alert("삭제 실패"); }
    setDeleting(false);
  };

  const gateColor = (g: string) => GATE_CFG[g]?.color || C.textDim;

  return (
    <>
      {deleteTarget && (
        <DeleteModal
          dealName={deleteTarget.name}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
      <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", overflow: "hidden" }}>

        {/* 딜 목록 */}
        <div style={{ width: 300, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0 }}>
          <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.12em" }}>DEAL PIPELINE</span>
            <span style={{ fontSize: 10, color: C.textDim }}>{deals.length} TOTAL</span>
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>
            {loading ? (
              <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>로딩 중...</div>
            ) : deals.length === 0 ? (
              <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>딜 없음</div>
            ) : deals.map((d: any) => {
              const isSelected = selected?.deal_code === d.deal_code;
              return (
                <div key={d.deal_code} onClick={() => { setSelected(d); onSelectDeal?.(d.deal_code); }}
                  style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, cursor: "pointer",
                    background: isSelected ? C.surface2 : "transparent",
                    borderLeft: isSelected ? `2px solid ${C.gold}` : "2px solid transparent" }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = C.surface; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: C.text, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 180 }}>
                      {d.deal_name}
                    </span>
                    <span style={{ fontSize: 10, color: gateColor(d.final_gate), fontWeight: 600, letterSpacing: "0.06em" }}>
                      {d.final_gate || "—"}
                    </span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 10, color: C.textDim }}>{d.deal_code}{d.is_test ? " · TEST" : ""}</span>
                    <span style={{ fontSize: 10, color: (d.mandatory_done||0) === (d.mandatory_total||0) && (d.mandatory_total||0) > 0 ? C.green : C.textDim }}>
                      {d.mandatory_done||0}/{d.mandatory_total||0}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 딜 상세 */}
        <div style={{ flex: 1, overflow: "auto" }}>
          {!selected ? (
            <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: C.textDim, fontSize: 13 }}>
              딜을 선택하면 상세 정보를 볼 수 있습니다
            </div>
          ) : (
            <div style={{ padding: 28, maxWidth: 760 }}>
              {/* 헤더 */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                <div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 4 }}>{selected.deal_name}</div>
                  <div style={{ fontSize: 11, color: C.textDim }}>
                    {selected.deal_code} · {selected.deal_type} · {selected.stage} · {selected.origination_posture}
                  </div>
                </div>
                <button onClick={() => setDeleteTarget({ code: selected.deal_code, name: selected.deal_name })}
                  style={{ padding: "6px 14px", background: "transparent", border: `1px solid ${C.red}`, borderRadius: 4, color: C.red, fontSize: 11, cursor: "pointer" }}
                  onMouseEnter={e => e.currentTarget.style.background = "rgba(239,68,68,0.1)"}
                  onMouseLeave={e => e.currentTarget.style.background = "transparent"}>
                  삭제
                </button>
              </div>

              {/* 게이트 판정 */}
              {selected.final_gate && (
                <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "16px 20px", marginBottom: 16 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                    <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.1em" }}>게이트 판정</span>
                    {selected.provisional_gate && (
                      <span style={{ fontSize: 11, color: C.textMid }}>
                        큐어 시 → <span style={{ color: gateColor(selected.provisional_gate), fontWeight: 600 }}>● {selected.provisional_gate}</span>
                      </span>
                    )}
                  </div>
                  {(selected.hold_reasons || []).length > 0 && (
                    <div style={{ marginBottom: 10 }}>
                      <div style={{ fontSize: 10, color: C.red, marginBottom: 6 }}>막힌 이유</div>
                      {(selected.hold_reasons || []).map((r: string, i: number) => (
                        <div key={i} style={{ fontSize: 12, color: C.textMid, borderLeft: `2px solid ${C.red}`, paddingLeft: 10, marginBottom: 4 }}>{r}</div>
                      ))}
                    </div>
                  )}
                  {(selected.required_actions || []).length > 0 && (
                    <div>
                      <div style={{ fontSize: 10, color: C.amber, marginBottom: 6 }}>필요 조치</div>
                      {(selected.required_actions || []).map((r: string, i: number) => (
                        <div key={i} style={{ fontSize: 12, color: C.textMid, borderLeft: `2px solid ${C.amber}`, paddingLeft: 10, marginBottom: 4 }}>{r}</div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 딜 정보 */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
                {[
                  ["자산 주소", selected.asset_address],
                  ["자산 유형", selected.asset_class],
                  ["차주", selected.borrower],
                  ["스폰서/소유자", selected.sponsor_owner],
                  ["현재 대주", selected.current_lender],
                  ["제안 대주", selected.proposed_lender],
                  ["만기", selected.maturity_date],
                ].filter(([, v]) => v).map(([label, value]) => (
                  <div key={label as string} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 14px" }}>
                    <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
                    <div style={{ fontSize: 13, color: C.text }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Evidence */}
              <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 16px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em" }}>EVIDENCE CHECKLIST</span>
                  <span style={{ fontSize: 11, color: (selected.mandatory_done||0) === (selected.mandatory_total||0) && (selected.mandatory_total||0) > 0 ? C.green : C.red, fontWeight: 600 }}>
                    {selected.mandatory_done||0}/{selected.mandatory_total||0}
                  </span>
                </div>
                <div style={{ fontSize: 10, color: C.textDim, marginTop: 4 }}>MANDATORY 항목 기준</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
