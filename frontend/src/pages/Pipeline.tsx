import React, { useEffect, useState, useRef } from "react";
import API from "../api";

const C = {
  bg: "#0A0E14", surface: "#11161D", surface2: "#161C26", border: "#1E2630",
  text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B",
  amber: "#F0A93B", red: "#E5484D", green: "#2BC48A", blue: "#4C8DFF",
};

const GATE_COLOR: any = { HOLD: C.amber, RESTRUCTURE: C.blue, ADVANCE: C.green, REJECT: C.red };

function DeleteModal({ dealName, onConfirm, onCancel }: { dealName: string; onConfirm: () => void; onCancel: () => void }) {
  const [input, setInput] = useState("");
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: 32, width: 420 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: C.red, marginBottom: 12 }}>딜 영구 삭제</div>
        <div style={{ fontSize: 13, color: C.textMid, marginBottom: 8 }}>
          <span style={{ color: C.red }}>{dealName}</span> 을 영구 삭제합니다.
        </div>
        <div style={{ fontSize: 11, color: C.textDim, marginBottom: 16 }}>
          확인하려면 <strong style={{ color: C.text }}>삭제하겠습니다</strong> 를 입력하세요.
        </div>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="삭제하겠습니다"
          style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 13, outline: "none", boxSizing: "border-box", marginBottom: 16, fontFamily: "inherit" }} />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onCancel} style={{ padding: "7px 16px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textMid, fontSize: 12, cursor: "pointer" }}>취소</button>
          <button onClick={onConfirm} disabled={input !== "삭제하겠습니다"}
            style={{ padding: "7px 16px", background: input === "삭제하겠습니다" ? C.red : C.surface2, border: "none", borderRadius: 4, color: "#fff", fontSize: 12, cursor: input === "삭제하겠습니다" ? "pointer" : "not-allowed" }}>
            삭제
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Pipeline({ onSelectDeal, initialDealCode }: { onSelectDeal?: (id: string) => void; initialDealCode?: string | null }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ code: string; name: string } | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const fetchDeals = async () => {
    setLoading(true);
    try { const r = await API.get("/api/risk-book/deals"); setDeals(r.data); } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchDeals(); }, []);

  useEffect(() => {
    if (initialDealCode && deals.length > 0) {
      const match = deals.find((d: any) => d.deal_code === initialDealCode);
      if (match) setSelected(match);
    }
  }, [initialDealCode, deals]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await API.delete(`/api/risk-book/deals/${deleteTarget.code}`);
      setDeleteTarget(null);
      if (selected?.deal_code === deleteTarget.code) setSelected(null);
      fetchDeals();
    } catch { alert("삭제 실패"); }
  };

  const gateColor = (g: string) => GATE_COLOR[g] || C.textDim;

  return (
    <>
      {deleteTarget && <DeleteModal dealName={deleteTarget.name} onConfirm={handleDelete} onCancel={() => setDeleteTarget(null)} />}
      <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", overflow: "hidden" }}>

        {/* 딜 목록 */}
        <div style={{ width: 280, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", overflow: "hidden", flexShrink: 0 }}>
          <div style={{ padding: "11px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.1em" }}>딜 목록</span>
            <span style={{ fontSize: 10, color: C.textDim }}>{deals.length} 전체</span>
          </div>
          <div style={{ flex: 1, overflow: "auto" }}>
            {loading ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>로딩 중...</div> :
              deals.length === 0 ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>딜 없음</div> :
              deals.map((d: any) => {
                const isSel = selected?.deal_code === d.deal_code;
                return (
                  <div key={d.deal_code} onClick={() => { setSelected(d); onSelectDeal?.(d.deal_code); }}
                    style={{
                      padding: "11px 16px", borderBottom: `1px solid ${C.border}`, cursor: "pointer",
                      background: isSel ? C.surface2 : "transparent",
                      borderLeft: isSel ? `2px solid ${gateColor(d.final_gate)}` : "2px solid transparent",
                    }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12, color: C.text, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 170 }}>{d.deal_name}</span>
                      <span style={{ fontSize: 10, color: gateColor(d.final_gate), fontWeight: 700 }}>{d.final_gate || "—"}</span>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <span style={{ fontSize: 10, color: C.textDim }}>{d.deal_code}{d.is_test ? " · TEST" : ""}</span>
                      <span style={{ fontSize: 10, color: (d.mandatory_done || 0) === (d.mandatory_total || 0) && (d.mandatory_total || 0) > 0 ? C.green : C.textDim }}>
                        {d.mandatory_done || 0}/{d.mandatory_total || 0}
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
            <div style={{ padding: "24px 28px", maxWidth: 880 }}>

              {/* 헤더 */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 18 }}>
                <div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: C.text, marginBottom: 4 }}>{selected.deal_name}</div>
                  <div style={{ fontSize: 11, color: C.textDim }}>
                    {selected.deal_code} · {selected.deal_type} · {selected.stage} · {selected.origination_posture}
                  </div>
                </div>
                <div ref={menuRef} style={{ position: "relative" }}>
                  <button onClick={() => setMenuOpen(v => !v)}
                    style={{ padding: "6px 10px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textMid, fontSize: 14, cursor: "pointer" }}>
                    ···
                  </button>
                  {menuOpen && (
                    <div style={{ position: "absolute", right: 0, top: 32, background: C.surface2, border: `1px solid ${C.border}`, borderRadius: 6, minWidth: 140, zIndex: 10 }}>
                      <div onClick={() => { setMenuOpen(false); setDeleteTarget({ code: selected.deal_code, name: selected.deal_name }); }}
                        style={{ padding: "9px 14px", fontSize: 12, color: C.red, cursor: "pointer" }}
                        onMouseEnter={e => (e.currentTarget.style.background = "rgba(229,72,77,0.1)")}
                        onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                        삭제
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Final Gate / Why / What changes this — 3분할 */}
              {selected.final_gate && (
                <div style={{ display: "grid", gridTemplateColumns: "120px 1fr 1fr", gap: 0, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, marginBottom: 16, overflow: "hidden" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "18px 8px", borderRight: `1px solid ${C.border}` }}>
                    <span style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.08em", marginBottom: 8 }}>최종 판정</span>
                    <span style={{ fontSize: 8, color: C.textDim, marginTop: 2 }}>이 딜이 진행 가능한지</span>
                    <span style={{ fontSize: 20, fontWeight: 800, color: gateColor(selected.final_gate) }}>{selected.final_gate}</span>
                  </div>

                  <div style={{ padding: "14px 16px", borderRight: `1px solid ${C.border}` }}>
                    <div style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.08em", marginBottom: 8 }}>왜 막혔나 (Why)</div>
                    {(selected.hold_reasons || []).length === 0 ? (
                      <div style={{ fontSize: 11, color: C.textDim }}>없음</div>
                    ) : (selected.hold_reasons || []).slice(0, 4).map((r: string, i: number) => (
                      <div key={i} style={{ fontSize: 12, color: C.textMid, marginBottom: 4, paddingLeft: 9, borderLeft: `2px solid ${C.red}` }}>{r}</div>
                    ))}
                  </div>

                  <div style={{ padding: "14px 16px" }}>
                    <div style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.08em", marginBottom: 8 }}>뭘 풀어야 하나 (What changes this)</div>
                    {(selected.required_actions || []).length === 0 ? (
                      <div style={{ fontSize: 11, color: C.textDim }}>없음</div>
                    ) : (selected.required_actions || []).slice(0, 4).map((r: string, i: number) => (
                      <div key={i} style={{ fontSize: 12, color: C.textMid, marginBottom: 4, paddingLeft: 9, borderLeft: `2px solid ${C.amber}` }}>{r}</div>
                    ))}
                    {selected.provisional_gate && (
                      <div style={{ marginTop: 10, fontSize: 11, color: C.textDim }}>
                        큐어 시 → <span style={{ color: gateColor(selected.provisional_gate), fontWeight: 700 }}>{selected.provisional_gate}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Deal Facts — 압축 2열 */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 16 }}>
                {[
                  ["자산 주소", selected.asset_address], ["자산 유형", selected.asset_class],
                  ["차주", selected.borrower], ["스폰서/소유자", selected.sponsor_owner],
                  ["현재 대주", selected.current_lender], ["제안 대주", selected.proposed_lender],
                  ["만기", selected.maturity_date],
                ].filter(([, v]) => v).map(([label, value]) => (
                  <div key={label as string} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 5, padding: "8px 12px" }}>
                    <div style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.05em", marginBottom: 2 }}>{label}</div>
                    <div style={{ fontSize: 12, color: C.text }}>{value}</div>
                  </div>
                ))}
              </div>

              {/* Evidence */}
              <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 5, padding: "10px 14px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em" }}>증빙 체크리스트</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: (selected.mandatory_done || 0) === (selected.mandatory_total || 0) && (selected.mandatory_total || 0) > 0 ? C.green : C.red }}>
                    {selected.mandatory_done || 0}/{selected.mandatory_total || 0}
                  </span>
                </div>
                <div style={{ height: 3, background: C.surface2, borderRadius: 2, marginTop: 6 }}>
                  <div style={{
                    width: `${((selected.mandatory_done || 0) / Math.max(selected.mandatory_total || 1, 1)) * 100}%`,
                    height: "100%", background: C.green, borderRadius: 2,
                  }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
