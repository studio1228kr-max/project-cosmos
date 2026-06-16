import React, { useEffect, useState } from "react";
import API from "../api";
import { Deal } from "../types";
import DealChat from "../components/DealChat";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444", blue: "#3B82F6",
};

const STATUS_CFG: any = {
  INTAKE:    { color: "#8FA3BB", bg: "rgba(143,163,187,0.1)", dot: "#8FA3BB", label: "INTAKE" },
  SCREENED:  { color: "#3B82F6", bg: "rgba(59,130,246,0.1)",  dot: "#3B82F6", label: "SCREENED" },
  WATCHLIST: { color: "#F59E0B", bg: "rgba(245,158,11,0.1)",  dot: "#F59E0B", label: "WATCH" },
  ADVANCE:   { color: "#22C55E", bg: "rgba(34,197,94,0.1)",   dot: "#22C55E", label: "ADVANCE" },
  REJECT:    { color: "#EF4444", bg: "rgba(239,68,68,0.1)",   dot: "#EF4444", label: "REJECT" },
};
const STATUSES = ["INTAKE","SCREENED","WATCHLIST","ADVANCE","REJECT"];

const Dot = ({ color }: { color: string }) => (
  <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }}/>
);

const StatusBadge = ({ status }: { status: string }) => {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.INTAKE;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px", borderRadius: 3, background: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 600, letterSpacing: "0.08em" }}>
      <Dot color={cfg.dot}/>{cfg.label}
    </span>
  );
};

const EvidenceBar = ({ count, total = 6 }: { count: number; total?: number }) => {
  const pct = Math.round((count / total) * 100);
  const color = count === total ? C.green : count > 0 ? C.amber : C.textDim;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 60, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color }}/>
      </div>
      <span style={{ fontSize: 10, color }}>{count}/{total}</span>
    </div>
  );
};

function DeleteModal({ dealName, onConfirm, onCancel }: { dealName: string; onConfirm: () => void; onCancel: () => void }) {
  const [input, setInput] = useState("");
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.75)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
      <div style={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: 10, padding: 32, width: 420 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "#e2e2e2", marginBottom: 12 }}>딜 삭제</div>
        <div style={{ fontSize: 13, color: "#8a8a8a", marginBottom: 8 }}>
          <span style={{ color: "#e5534b" }}>{dealName}</span> 을 영구 삭제합니다.
        </div>
        <div style={{ fontSize: 12, color: "#6a6a6a", marginBottom: 16 }}>
          확인하려면 <strong style={{ color: "#e2e2e2" }}>삭제하겠습니다</strong> 를 입력하세요.
        </div>
        <input value={input} onChange={e => setInput(e.target.value)} placeholder="삭제하겠습니다"
          style={{ width: "100%", padding: "8px 12px", background: "#111", border: "1px solid #333", borderRadius: 6, color: "#e2e2e2", fontSize: 13, outline: "none", boxSizing: "border-box", marginBottom: 16 }}/>
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onCancel} style={{ padding: "7px 16px", background: "transparent", border: "1px solid #333", borderRadius: 6, color: "#8a8a8a", fontSize: 13, cursor: "pointer" }}>취소</button>
          <button onClick={onConfirm} disabled={input !== "삭제하겠습니다"}
            style={{ padding: "7px 16px", background: input === "삭제하겠습니다" ? "#e5534b" : "#333", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, cursor: input === "삭제하겠습니다" ? "pointer" : "not-allowed" }}>삭제</button>
        </div>
      </div>
    </div>
  );
}

export default function Pipeline({ onSelectDeal }: { onSelectDeal?: (id: string) => void }) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<{id: string; name: string} | null>(null);
  const [selectedDeal, setSelectedDeal] = useState<{id: string; name: string} | null>(null);
  const [listOpen, setListOpen] = useState(true);

  const fetchDeals = async () => {
    setLoading(true);
    try { const r = await API.get("/deals"); setDeals(r.data); } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchDeals(); }, []);

  const handleDelete = async (id: string) => {
    try {
      await API.delete(`/deals/${id}`);
      setDeleteTarget(null);
      if (selectedDeal?.id === id) setSelectedDeal(null);
      fetchDeals();
    } catch { alert("삭제 실패"); }
  };

  const selectDeal = (id: string, name: string) => {
    onSelectDeal?.(id);
    setSelectedDeal({ id, name });
    setListOpen(false); // 딜 선택시 리스트 자동 접힘
  };

  const filtered = filter === "ALL" ? deals : deals.filter(d => d.status === filter);
  const total = deals.length;
  const statusCounts: any = {};
  STATUSES.forEach(s => { statusCounts[s] = deals.filter(d => d.status === s).length; });

  return (
    <>
      {deleteTarget && <DeleteModal dealName={deleteTarget.name} onConfirm={() => handleDelete(deleteTarget.id)} onCancel={() => setDeleteTarget(null)} />}
      <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", overflow: "hidden" }}>

        {/* 딜 리스트 패널 - 슬라이드 토글 */}
        <div style={{
          width: listOpen ? 280 : 0,
          minWidth: listOpen ? 280 : 0,
          transition: "width 0.2s ease, min-width 0.2s ease",
          borderRight: listOpen ? `1px solid ${C.border}` : "none",
          overflow: "hidden",
          display: "flex", flexDirection: "column",
          flexShrink: 0,
        }}>
          {/* 필터 */}
          <div style={{ padding: "10px 12px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 4, flexWrap: "wrap" }}>
            {["ALL", ...STATUSES].map(s => (
              <button key={s} onClick={() => setFilter(s)}
                style={{ padding: "2px 7px", borderRadius: 3, border: "none", cursor: "pointer", fontSize: 10, fontWeight: 600, whiteSpace: "nowrap",
                  background: filter === s ? (STATUS_CFG[s]?.bg || "rgba(201,168,76,0.15)") : "transparent",
                  color: filter === s ? (STATUS_CFG[s]?.color || C.gold) : C.textDim }}>
                {s === "ALL" ? `ALL ${total}` : `${STATUS_CFG[s]?.label} ${statusCounts[s]}`}
              </button>
            ))}
          </div>
          {/* 리스트 */}
          <div style={{ flex: 1, overflow: "auto" }}>
            {loading ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>로딩 중...</div>
            : filtered.length === 0 ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>딜 없음</div>
            : filtered.map(d => {
              const rec = d.deal_record ? (typeof d.deal_record === "string" ? JSON.parse(d.deal_record) : d.deal_record) : {};
              const name = rec.asset_name || "Unknown";
              const isSelected = selectedDeal?.id === d.id;
              return (
                <div key={d.id} onClick={() => selectDeal(d.id, name)}
                  style={{ padding: "10px 14px", borderBottom: `1px solid ${C.border}`, cursor: "pointer",
                    background: isSelected ? C.surface2 : "transparent",
                    borderLeft: isSelected ? `2px solid ${C.gold}` : "2px solid transparent" }}
                  onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = C.surface; }}
                  onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                    <span style={{ fontSize: 12, color: C.text, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 140 }}>{name}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <StatusBadge status={d.status} />
                      <button onClick={e => { e.stopPropagation(); setDeleteTarget({ id: d.id, name }); }}
                        style={{ background: "transparent", border: "none", color: C.textDim, cursor: "pointer", fontSize: 13, padding: "0 2px" }}
                        onMouseEnter={e => (e.currentTarget.style.color = C.red)}
                        onMouseLeave={e => (e.currentTarget.style.color = C.textDim)}>✕</button>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <span style={{ fontSize: 10, color: C.textDim }}>{rec.creditor || "—"}</span>
                    <EvidenceBar count={d.evidence_count ?? 0} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 토글 버튼 */}
        <button onClick={() => setListOpen(o => !o)}
          style={{ width: 20, background: C.surface2, border: "none", borderRight: `1px solid ${C.border}`,
            color: C.textDim, cursor: "pointer", fontSize: 10, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center" }}>
          {listOpen ? "‹" : "›"}
        </button>

        {/* 메인 영역 */}
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          {selectedDeal ? (
            <>
              {/* 딜 상세 */}
              <div style={{ flex: "0 0 55%", borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                <div style={{ padding: "10px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 10 }}>
                  <button onClick={() => { setSelectedDeal(null); setListOpen(true); }}
                    style={{ background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textDim, fontSize: 11, padding: "3px 10px", cursor: "pointer" }}>
                    ← 목록
                  </button>
                  <span style={{ fontSize: 13, color: C.text, fontWeight: 600, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{selectedDeal.name}</span>
                  <StatusBadge status={deals.find(d => d.id === selectedDeal.id)?.status || "INTAKE"} />
                </div>
                <div style={{ flex: 1, overflow: "auto", padding: 20 }}>
                  {(() => {
                    const deal = deals.find(d => d.id === selectedDeal.id);
                    if (!deal) return null;
                    const rec = deal.deal_record ? (typeof deal.deal_record === "string" ? JSON.parse(deal.deal_record) : deal.deal_record) : {};
                    return (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                        {[
                          ["채권자", rec.creditor],
                          ["차주", rec.borrower],
                          ["자산주소", rec.asset_address],
                          ["채권금액", rec.loan_amount],
                          ["감정가", rec.asset_valuation],
                          ["LTV", rec.ltv],
                          ["만기", rec.maturity_date],
                          ["연체상태", rec.delinquency_status],
                          ["담보순위", rec.lien_priority],
                          ["소유자", rec.owner_identity],
                        ].map(([label, value]) => (
                          <div key={label as string} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 14px" }}>
                            <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>{label}</div>
                            <div style={{ fontSize: 13, color: value ? C.text : C.textDim, fontWeight: value ? 500 : 400 }}>{value || "미입력"}</div>
                          </div>
                        ))}
                      </div>
                    );
                  })()}
                </div>
              </div>
              {/* LUSKA AI */}
              <div style={{ flex: "0 0 45%", overflow: "hidden" }}>
                <DealChat dealId={selectedDeal.id} dealName={selectedDeal.name} />
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: C.textDim, fontSize: 13 }}>
              딜을 선택하면 LUSKA AI와 함께 분석할 수 있습니다
            </div>
          )}
        </div>
      </div>
    </>
  );
}
