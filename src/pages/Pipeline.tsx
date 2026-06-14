import React, { useEffect, useState } from "react";
import API from "../api";
import { Deal } from "../types";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", goldDim: "rgba(201,168,76,0.12)",
  text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444", blue: "#3B82F6",
};

const STATUS_CFG: any = {
  INTAKE:    { color: "#8FA3BB", bg: "rgba(143,163,187,0.1)",  dot: "#8FA3BB",  label: "INTAKE"    },
  SCREENED:  { color: "#3B82F6", bg: "rgba(59,130,246,0.1)",   dot: "#3B82F6",  label: "SCREENED"  },
  WATCHLIST: { color: "#F59E0B", bg: "rgba(245,158,11,0.1)",   dot: "#F59E0B",  label: "WATCH"     },
  ADVANCE:   { color: "#22C55E", bg: "rgba(34,197,94,0.1)",    dot: "#22C55E",  label: "ADVANCE"   },
  REJECT:    { color: "#EF4444", bg: "rgba(239,68,68,0.1)",    dot: "#EF4444",  label: "REJECT"    },
};
const STATUSES = ["INTAKE","SCREENED","WATCHLIST","ADVANCE","REJECT"];

const Dot = ({ color }: { color: string }) => (
  <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }}/>
);

const StatusBadge = ({ status }: { status: string }) => {
  const cfg = STATUS_CFG[status] ?? STATUS_CFG.INTAKE;
  return (
    <>
    {deleteTarget && <DeleteModal dealName={deleteTarget.name} onConfirm={() => handleDelete(deleteTarget.id)} onCancel={() => setDeleteTarget(null)} />}
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px", borderRadius: 3, background: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 600, letterSpacing: "0.08em" }}>
      <Dot color={cfg.dot}/>{cfg.label}
    </span>
    </>
  );
};

const EvidenceBar = ({ count, total = 6 }: { count: number; total?: number }) => {
  const pct = Math.round((count / total) * 100);
  const color = count === total ? C.green : count > 0 ? C.amber : C.textDim;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 60, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2, transition: "width 0.3s" }}/>
      </div>
      <span style={{ fontSize: 10, color: C.textDim, fontVariantNumeric: "tabular-nums" }}>{count}/{total}</span>
    </div>
  );
};


function DeleteModal({ dealName, onConfirm, onCancel }: { dealName: string; onConfirm: () => void; onCancel: () => void }) {
  const [input, setInput] = React.useState("");
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 9999 }}>
      <div style={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: 10, padding: 32, width: 400 }}>
        <div style={{ fontSize: 16, fontWeight: 600, color: "#e2e2e2", marginBottom: 12 }}>딜 삭제</div>
        <div style={{ fontSize: 13, color: "#8a8a8a", marginBottom: 8 }}>
          <span style={{ color: "#e5534b" }}>{dealName}</span> 을 삭제합니다.
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

export default function Pipeline({ onSelectDeal }: { onSelectDeal: (id: string) => void }) {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [hovered, setHovered] = useState<string | null>(null);

  useEffect(() => {
    API.get("/deals").then(r => { setDeals(r.data); setLoading(false); });
  }, []);

  const counts: any = { ALL: deals.length };
  STATUSES.forEach(s => counts[s] = deals.filter(d => d.status === s).length);
  const filtered = filter === "ALL" ? deals : deals.filter(d => d.status === filter);

  const totalExposure = deals.reduce((sum, d) => {
    const bal = parseFloat(String(d.current_balance).replace(/[^0-9.]/g, "")) || 0;
    return sum + bal;
  }, 0);

  return (
    <div>
      {/* KPI Strip */}
      <div style={{ display: "flex", gap: 12, marginBottom: 28 }}>
        {[
          { label: "TOTAL DEALS", value: deals.length, unit: "" },
          { label: "SCREENED", value: counts.SCREENED ?? 0, unit: "" },
          { label: "ADVANCE", value: counts.ADVANCE ?? 0, unit: "" },
          { label: "WATCHLIST", value: counts.WATCHLIST ?? 0, unit: "" },
        ].map(kpi => (
          <div key={kpi.label} style={{ flex: 1, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "14px 18px" }}>
            <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.1em", marginBottom: 6 }}>{kpi.label}</div>
            <div style={{ fontSize: 24, fontWeight: 600, color: C.text, fontVariantNumeric: "tabular-nums" }}>{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: 0, marginBottom: 16, borderBottom: `1px solid ${C.border}` }}>
        {["ALL", ...STATUSES].map(s => {
          const active = filter === s;
          const cfg = STATUS_CFG[s];
          return (
            <button key={s} onClick={() => setFilter(s)}
              style={{ padding: "8px 16px", background: "transparent", border: "none", borderBottom: active ? `2px solid ${cfg?.color ?? C.gold}` : "2px solid transparent", color: active ? (cfg?.color ?? C.gold) : C.textDim, fontSize: 11, fontWeight: active ? 600 : 400, cursor: "pointer", letterSpacing: "0.08em", marginBottom: -1, transition: "all 0.15s" }}>
              {s} {counts[s] !== undefined && <span style={{ opacity: 0.6, marginLeft: 4 }}>{counts[s]}</span>}
            </button>
          );
        })}
      </div>

      {/* Table */}
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, overflow: "hidden" }}>
        {/* Table Header */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 1fr 1fr 0.8fr 0.8fr", padding: "10px 18px", borderBottom: `1px solid ${C.border}`, background: C.surface2 }}>
          {["ASSET / DEAL ID", "CREDITOR", "EXPOSURE", "STATUS", "EVIDENCE", "DSCR"].map(h => (
            <div key={h} style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.1em", fontWeight: 600 }}>{h}</div>
          ))}
        </div>

        {loading && (
          <div style={{ padding: "40px 18px", color: C.textDim, fontSize: 12, textAlign: "center" }}>Loading...</div>
        )}

        {!loading && filtered.length === 0 && (
          <div style={{ padding: "40px 18px", color: C.textDim, fontSize: 12, textAlign: "center" }}>No deals found</div>
        )}

        {!loading && filtered.map((deal, i) => {
          const isHover = hovered === deal.id;
          const evCount = typeof (deal as any).evidence_confirmed === "number" ? (deal as any).evidence_confirmed : 0;
          return (
            <div key={deal.id}
              onClick={() => onSelectDeal(deal.id)}
              onMouseEnter={() => setHovered(deal.id)}
              onMouseLeave={() => setHovered(null)}
              style={{ display: "grid", gridTemplateColumns: "2fr 1.2fr 1fr 1fr 0.8fr 0.8fr", padding: "13px 18px", borderBottom: i < filtered.length - 1 ? `1px solid ${C.border}` : "none", cursor: "pointer", background: isHover ? "rgba(201,168,76,0.04)" : "transparent", transition: "background 0.1s" }}>

              {/* Asset */}
              <div>
                <div style={{ fontSize: 13, fontWeight: 500, color: C.text, marginBottom: 3 }}>{deal.asset_name || "—"}</div>
                <div style={{ fontSize: 10, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: "0.04em" }}>{deal.id}</div>
              </div>

              {/* Creditor */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: C.textMid }}>{deal.creditor || "—"}</span>
              </div>

              {/* Exposure */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: C.text, fontVariantNumeric: "tabular-nums" }}>
                  {deal.current_balance && deal.current_balance !== "Unknown" ? deal.current_balance : "—"}
                </span>
              </div>

              {/* Status */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <StatusBadge status={deal.status}/>
              </div>

              {/* Evidence */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <EvidenceBar count={deal.missing_count !== undefined ? Math.max(0, 6 - (deal.missing_count || 0)) : 0}/>
              </div>

              {/* DSCR */}
              <div style={{ display: "flex", alignItems: "center" }}>
                <span style={{ fontSize: 12, color: C.textMid, fontVariantNumeric: "tabular-nums" }}>
                  {(deal as any).dscr || "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: 10, fontSize: 10, color: C.textDim, textAlign: "right" }}>
        COSMOS v0.1 · {filtered.length} records
      </div>
    </div>
  );
}
