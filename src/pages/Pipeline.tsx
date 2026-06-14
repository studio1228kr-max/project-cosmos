import React, { useEffect, useState } from "react";
import API from "../api";
import DealChat from "../components/DealChat";
import { Deal } from "../types";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", goldDim: "rgba(201,168,76,0.12)",
  text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
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
      <span style={{ fontSize: 10, color, fontVariantNumeric: "tabular-nums" }}>{count}/{total}</span>
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
          확인하려면 아래에 <strong style={{ color: "#e2e2e2" }}>삭제하겠습니다</strong> 를 입력하세요.
        </div>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="삭제하겠습니다"
          style={{ width: "100%", padding: "8px 12px", background: "#111", border: "1px solid #333", borderRadius: 6, color: "#e2e2e2", fontSize: 13, outline: "none", boxSizing: "border-box", marginBottom: 16 }}
        />
        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
          <button onClick={onCancel} style={{ padding: "7px 16px", background: "transparent", border: "1px solid #333", borderRadius: 6, color: "#8a8a8a", fontSize: 13, cursor: "pointer" }}>취소</button>
          <button
            onClick={onConfirm}
            disabled={input !== "삭제하겠습니다"}
            style={{ padding: "7px 16px", background: input === "삭제하겠습니다" ? "#e5534b" : "#333", border: "none", borderRadius: 6, color: "#fff", fontSize: 13, cursor: input === "삭제하겠습니다" ? "pointer" : "not-allowed" }}
          >삭제</button>
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

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const r = await API.get("/deals");
      setDeals(r.data);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchDeals(); }, []);

  const handleDelete = async (id: string) => {
    try {
      await API.delete(`/deals/${id}`);
      setDeleteTarget(null);
      fetchDeals();
    } catch (e) {
      alert("삭제 실패");
    }
  };

  const filtered = filter === "ALL" ? deals : deals.filter(d => d.status === filter);
  const total = deals.length;

  const statusCounts: any = {};
  STATUSES.forEach(s => { statusCounts[s] = deals.filter(d => d.status === s).length; });

  return (
    <>
      {deleteTarget && (
        <DeleteModal
          dealName={deleteTarget.name}
          onConfirm={() => handleDelete(deleteTarget.id)}
          onCancel={() => setDeleteTarget(null)}
        />
      )}
      <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif" }}>
        {/* LEFT: Filter + List */}
        <div style={{ width: 280, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column" }}>
          {/* Filter tabs */}
          <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 6, flexWrap: "wrap" }}>
            {["ALL", ...STATUSES].map(s => (
              <button key={s} onClick={() => setFilter(s)}
                style={{ padding: "3px 8px", borderRadius: 3, border: "none", cursor: "pointer", fontSize: 10, fontWeight: 600,
                  background: filter === s ? (STATUS_CFG[s]?.bg || "rgba(201,168,76,0.15)") : "transparent",
                  color: filter === s ? (STATUS_CFG[s]?.color || C.gold) : C.textDim }}>
                {s === "ALL" ? `ALL ${total}` : `${STATUS_CFG[s]?.label} ${statusCounts[s]}`}
              </button>
            ))}
          </div>
          {/* Deal list */}
          <div style={{ flex: 1, overflow: "auto" }}>
            {loading ? (
              <div style={{ padding: 24, color: C.textDim, fontSize: 12 }}>로딩 중...</div>
            ) : filtered.length === 0 ? (
              <div style={{ padding: 24, color: C.textDim, fontSize: 12 }}>딜 없음</div>
            ) : filtered.map(d => {
              const rec = d.deal_record ? (typeof d.deal_record === "string" ? JSON.parse(d.deal_record) : d.deal_record) : {};
              const name = rec.asset_name || d.deal_name || "Unknown";
              const cfg = STATUS_CFG[d.status] ?? STATUS_CFG.INTAKE;
              return (
                <div key={d.id}
                  onClick={() => { onSelectDeal?.(d.id); setSelectedDeal({ id: d.id, name }); }}
                  style={{ padding: "10px 14px", borderBottom: `1px solid ${C.border}`, cursor: "pointer" }}
                  onMouseEnter={e => (e.currentTarget.style.background = C.surface)}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                    <span style={{ fontSize: 12, color: C.text, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>{name}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
                      <StatusBadge status={d.status} />
                      <button
                        onClick={e => { e.stopPropagation(); setDeleteTarget({ id: d.id, name }); }}
                        style={{ background: "transparent", border: "none", color: C.textDim, cursor: "pointer", fontSize: 13, padding: "0 2px", lineHeight: 1 }}
                        onMouseEnter={e => (e.currentTarget.style.color = C.red)}
                        onMouseLeave={e => (e.currentTarget.style.color = C.textDim)}
                      >✕</button>
                    </div>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: 10, color: C.textDim }}>{rec.creditor || "—"}</span>
                    <EvidenceBar count={d.evidence_count ?? 0} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        {/* RIGHT: Deal Chat */}
        <div style={{ flex: 1, overflow: "hidden" }}>
          {selectedDeal ? (
            <DealChat dealId={selectedDeal.id} dealName={selectedDeal.name} />
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: C.textDim, fontSize: 13 }}>
              딜을 선택하면 LUSKA AI와 대화할 수 있습니다
            </div>
          )}
        </div>
      </div>
    </>
  );
}
