import React, { useEffect, useState } from "react";
import API from "../api";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444", blue: "#3B82F6",
};

const GATE_CFG: any = {
  ADVANCE:     { color: C.green, bg: "rgba(34,197,94,0.1)",  label: "ADVANCE" },
  RESTRUCTURE: { color: C.blue,  bg: "rgba(59,130,246,0.1)", label: "RESTRUCTURE" },
  HOLD:        { color: C.amber, bg: "rgba(245,158,11,0.1)", label: "HOLD" },
  REJECT:      { color: C.red,   bg: "rgba(239,68,68,0.1)",  label: "REJECT" },
};

const STAGE_LABELS: any = {
  INTAKE: "인테이크",
  LIVE_EXECUTION: "실행 중",
};

interface RiskBookDeal {
  id: number;
  deal_code: string;
  deal_name: string;
  deal_type: string;
  stage: string;
  asset_address?: string;
  asset_type?: string;
  borrower?: string;
  sponsor_owner?: string;
  current_lender?: string;
  proposed_lender?: string;
  maturity_date?: string;
  origination_posture?: string;
  is_test?: boolean;
  final_gate?: string | null;
  provisional_gate?: string | null;
  ic_ready?: boolean | null;
  hold_reasons?: string[] | null;
  required_actions?: string[] | null;
  evidence_total?: number;
  mandatory_total?: number;
  mandatory_done?: number;
}

interface DealTypeRow {
  deal_type_code: string;
  deal_type_label: string;
}

const Dot = ({ color }: { color: string }) => (
  <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }}/>
);

const GateBadge = ({ gate }: { gate?: string | null }) => {
  const cfg = gate ? (GATE_CFG[gate] ?? { color: C.textDim, bg: "rgba(255,255,255,0.06)", label: gate }) : { color: C.textDim, bg: "rgba(255,255,255,0.06)", label: "미산출" };
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "2px 8px", borderRadius: 3, background: cfg.bg, color: cfg.color, fontSize: 10, fontWeight: 600, letterSpacing: "0.08em" }}>
      <Dot color={cfg.color}/>{cfg.label}
    </span>
  );
};

const EvidenceBar = ({ done, total }: { done: number; total: number }) => {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const color = total === 0 ? C.textDim : done === total ? C.green : done > 0 ? C.amber : C.red;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ width: 60, height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color }}/>
      </div>
      <span style={{ fontSize: 10, color }}>{done}/{total}</span>
    </div>
  );
};

export default function Pipeline({ onSelectDeal }: { onSelectDeal?: (dealCode: string) => void }) {
  const [deals, setDeals] = useState<RiskBookDeal[]>([]);
  const [dealTypes, setDealTypes] = useState<DealTypeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("ALL");
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [listOpen, setListOpen] = useState(true);

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const r = await API.get("/api/risk-book/deals");
      setDeals(r.data);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    fetchDeals();
    API.get("/api/risk-book/deal-types").then(r => setDealTypes(r.data)).catch(() => {});
  }, []);

  const selectDeal = (code: string) => {
    onSelectDeal?.(code);
    setSelectedCode(code);
    setListOpen(false);
    setSummaryLoading(true);
    API.get(`/api/risk-book/deals/${code}/summary`)
      .catch(() => null)
      .finally(() => setSummaryLoading(false));
  };

  const stages = Array.from(new Set(deals.map(d => d.stage).filter(Boolean)));
  const filtered = filter === "ALL" ? deals : deals.filter(d => d.stage === filter);
  const total = deals.length;
  const stageCounts: any = {};
  stages.forEach(s => { stageCounts[s] = deals.filter(d => d.stage === s).length; });

  const typeLabel = (code: string) => dealTypes.find(t => t.deal_type_code === code)?.deal_type_label || code;
  const selectedDeal = deals.find(d => d.deal_code === selectedCode);

  return (
    <div style={{ display: "flex", height: "100%", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", overflow: "hidden" }}>

      <div style={{
        width: listOpen ? 300 : 0, minWidth: listOpen ? 300 : 0,
        transition: "width 0.2s ease, min-width 0.2s ease",
        borderRight: listOpen ? `1px solid ${C.border}` : "none",
        overflow: "hidden", display: "flex", flexDirection: "column", flexShrink: 0,
      }}>
        <div style={{ padding: "10px 12px", borderBottom: `1px solid ${C.border}`, display: "flex", gap: 4, flexWrap: "wrap" }}>
          <button onClick={() => setFilter("ALL")}
            style={{ padding: "2px 7px", borderRadius: 3, border: "none", cursor: "pointer", fontSize: 10, fontWeight: 600,
              background: filter === "ALL" ? "rgba(201,168,76,0.15)" : "transparent",
              color: filter === "ALL" ? C.gold : C.textDim }}>
            ALL {total}
          </button>
          {stages.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              style={{ padding: "2px 7px", borderRadius: 3, border: "none", cursor: "pointer", fontSize: 10, fontWeight: 600, whiteSpace: "nowrap",
                background: filter === s ? "rgba(201,168,76,0.15)" : "transparent",
                color: filter === s ? C.gold : C.textDim }}>
              {STAGE_LABELS[s] || s} {stageCounts[s]}
            </button>
          ))}
        </div>
        <div style={{ flex: 1, overflow: "auto" }}>
          {loading ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>로딩 중...</div>
          : filtered.length === 0 ? <div style={{ padding: 20, color: C.textDim, fontSize: 12 }}>딜 없음</div>
          : filtered.map(d => {
            const isSelected = selectedCode === d.deal_code;
            return (
              <div key={d.deal_code} onClick={() => selectDeal(d.deal_code)}
                style={{ padding: "10px 14px", borderBottom: `1px solid ${C.border}`, cursor: "pointer",
                  background: isSelected ? C.surface2 : "transparent",
                  borderLeft: isSelected ? `2px solid ${C.gold}` : "2px solid transparent" }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = C.surface; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = "transparent"; }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                  <span style={{ fontSize: 12, color: C.text, fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 150 }}>
                    {d.deal_name}
                  </span>
                  <GateBadge gate={d.final_gate} />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: C.textDim, display: "flex", gap: 6, alignItems: "center" }}>
                    {d.deal_code}
                    {d.is_test && <span style={{ color: C.amber, border: `1px solid ${C.amber}`, borderRadius: 2, padding: "0 4px", fontSize: 9 }}>TEST</span>}
                  </span>
                  <EvidenceBar done={d.mandatory_done ?? 0} total={d.mandatory_total ?? 0} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <button onClick={() => setListOpen(o => !o)}
        style={{ width: 20, background: C.surface2, border: "none", borderRight: `1px solid ${C.border}`,
          color: C.textDim, cursor: "pointer", fontSize: 10, flexShrink: 0,
          display: "flex", alignItems: "center", justifyContent: "center" }}>
        {listOpen ? "‹" : "›"}
      </button>

      <div style={{ flex: 1, overflow: "auto" }}>
        {!selectedDeal ? (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", color: C.textDim, fontSize: 13 }}>
            딜을 선택하면 상세 정보를 볼 수 있습니다
          </div>
        ) : (
          <div style={{ padding: 24, maxWidth: 900 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <button onClick={() => { setSelectedCode(null); setListOpen(true); }}
                style={{ background: "transparent", border: `1px solid ${C.border}`, borderRadius: 4, color: C.textDim, fontSize: 11, padding: "3px 10px", cursor: "pointer" }}>
                ← 목록
              </button>
              <span style={{ fontSize: 16, fontWeight: 600, color: C.text }}>{selectedDeal.deal_name}</span>
              <GateBadge gate={selectedDeal.final_gate} />
            </div>
            <div style={{ fontSize: 11, color: C.textDim, marginBottom: 20 }}>
              {selectedDeal.deal_code} · {typeLabel(selectedDeal.deal_type)} · {STAGE_LABELS[selectedDeal.stage] || selectedDeal.stage}
              {selectedDeal.origination_posture && ` · ${selectedDeal.origination_posture}`}
              {selectedDeal.is_test && <span style={{ color: C.amber, marginLeft: 8 }}>TEST FIXTURE</span>}
            </div>

            {summaryLoading ? (
              <div style={{ color: C.textDim, fontSize: 12 }}>불러오는 중...</div>
            ) : (
              <>
                {selectedDeal.final_gate && (
                  <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: 16, marginBottom: 16 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                      <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", textTransform: "uppercase" }}>게이트 판정</div>
                      {selectedDeal.provisional_gate && selectedDeal.provisional_gate !== selectedDeal.final_gate && (
                        <div style={{ fontSize: 11, color: C.textMid, display: "flex", gap: 6, alignItems: "center" }}>
                          큐어 시 → <GateBadge gate={selectedDeal.provisional_gate} />
                        </div>
                      )}
                    </div>
                    {(selectedDeal.hold_reasons?.length ?? 0) > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 11, color: C.red, fontWeight: 600, marginBottom: 6 }}>막힌 이유</div>
                        {selectedDeal.hold_reasons!.map((r, i) => (
                          <div key={i} style={{ fontSize: 12, color: C.textMid, marginBottom: 4, paddingLeft: 10, borderLeft: `2px solid ${C.red}` }}>{r}</div>
                        ))}
                      </div>
                    )}
                    {(selectedDeal.required_actions?.length ?? 0) > 0 && (
                      <div>
                        <div style={{ fontSize: 11, color: C.gold, fontWeight: 600, marginBottom: 6 }}>필요 조치</div>
                        {selectedDeal.required_actions!.map((r, i) => (
                          <div key={i} style={{ fontSize: 12, color: C.textMid, marginBottom: 4, paddingLeft: 10, borderLeft: `2px solid ${C.gold}` }}>{r}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
                  {[
                    ["자산 주소", selectedDeal.asset_address],
                    ["자산 유형", selectedDeal.asset_type],
                    ["차주", selectedDeal.borrower],
                    ["스폰서/소유자", selectedDeal.sponsor_owner],
                    ["현재 대주", selectedDeal.current_lender],
                    ["제안 대주", selectedDeal.proposed_lender],
                    ["만기", selectedDeal.maturity_date],
                  ].map(([label, value]) => (
                    <div key={label as string} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 14px" }}>
                      <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4, letterSpacing: "0.06em", textTransform: "uppercase" }}>{label}</div>
                      <div style={{ fontSize: 13, color: value ? C.text : C.textDim, fontWeight: value ? 500 : 400 }}>{value || "미입력"}</div>
                    </div>
                  ))}
                </div>

                <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div>
                    <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 }}>Evidence Checklist</div>
                    <EvidenceBar done={selectedDeal.mandatory_done ?? 0} total={selectedDeal.mandatory_total ?? 0} />
                  </div>
                  <span style={{ fontSize: 11, color: C.textDim }}>MANDATORY 항목 기준</span>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
