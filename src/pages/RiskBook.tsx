import React, { useEffect, useState } from "react";

const BASE = "https://project-cosmos-production.up.railway.app";

const GATE_COLOR: Record<string, string> = {
  ADVANCE: "#22c55e", HOLD: "#f59e0b",
  RESTRUCTURE: "#f97316", REJECT: "#ef4444",
  PARTIAL: "#eab308", INSUFFICIENT: "#ef4444", COMPLETE: "#22c55e",
};
const CONF_COLOR: Record<string, string> = {
  HIGH: "#22c55e", MEDIUM: "#eab308", LOW: "#ef4444", UNVERIFIED: "#6a6a6a",
};

function GateBadge({ label, value }: { label: string; value: string }) {
  const col = GATE_COLOR[value] || "#6a6a6a";
  return (
    <div style={{ background: "#1a1a1a", border: `1px solid ${col}33`, borderRadius: 8, padding: "12px 18px", minWidth: 130 }}>
      <div style={{ fontSize: 10, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 16, fontWeight: 700, color: col }}>{value}</div>
    </div>
  );
}

function MetricCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ background: "#1a1a1a", border: "1px solid #222", borderRadius: 8, padding: "12px 16px", minWidth: 110 }}>
      <div style={{ fontSize: 10, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: "#e2e2e2" }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: "#6a6a6a", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function pct(v: number | null) { return v != null ? `${(v * 100).toFixed(1)}%` : "—"; }
function x2(v: number | null) { return v != null ? `${v.toFixed(2)}x` : "—"; }

export default function RiskBook() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${BASE}/api/risk-book/deals/LSK-2026-7003EE/summary`)
      .then(r => r.json())
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(String(e)); setLoading(false); });
  }, []);

  if (loading) return <div style={{ padding: 40, color: "#6a6a6a" }}>Loading Risk Book...</div>;
  if (error || !data?.deal) return <div style={{ padding: 40, color: "#ef4444" }}>Error: {error || "No data"}</div>;

  const { deal, financials: fin, gate, scenarios, evidence } = data;
  const mandatory = (scenarios || []).filter((s: any) => s.gate_weight === "MANDATORY");
  const tail = (scenarios || []).filter((s: any) => s.gate_weight === "INFORMATIONAL");

  return (
    <div style={{ padding: "28px 32px", fontFamily: "'ZenSerif','Inter',sans-serif", color: "#e2e2e2", maxWidth: 1100 }}>

      {/* Header */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, color: "#6a6a6a", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
          Risk Book · {deal.deal_code} · {deal.stage}
        </div>
        <div style={{ fontSize: 22, fontWeight: 700, color: "#e2e2e2" }}>{deal.deal_name}</div>
        <div style={{ fontSize: 12, color: "#6a6a6a", marginTop: 4 }}>
          {deal.asset_address} · {deal.borrower} · {deal.current_lender} → {deal.proposed_lender}
        </div>
      </div>

      {/* Gate Strip */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <GateBadge label="Final Gate" value={gate?.final_gate || "—"} />
        <GateBadge label="Provisional" value={gate?.provisional_gate || "—"} />
        <GateBadge label="Data Gate" value={gate?.data_gate || "—"} />
        <GateBadge label="Structural" value={gate?.structural_gate || "—"} />
        <div style={{ background: "#1a1a1a", border: "1px solid #222", borderRadius: 8, padding: "12px 18px" }}>
          <div style={{ fontSize: 10, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>IC Ready</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: gate?.ic_ready ? "#22c55e" : "#6a6a6a" }}>
            {gate?.ic_ready ? "YES" : "NO"}
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: "flex", gap: 12, marginBottom: 24, flexWrap: "wrap" }}>
        <MetricCard label="LTV Gross" value={pct(fin?.ltv_gross)} sub="담보가치 기준" />
        <MetricCard label="LTV Net" value={pct(fin?.ltv_net)} sub="NTS 압류 차감" />
        <MetricCard label="DSCR" value={x2(fin?.dscr)} sub="Base Case" />
        <MetricCard label="Debt Yield" value={pct(fin?.debt_yield)} sub="NOI / Loan" />
        <MetricCard label="Evidence" value={`${fin?.evidence_completeness ?? 0}%`} sub={gate?.data_gate} />
      </div>

      {/* Hold Reasons + Required Actions */}
      {gate?.hold_reasons?.length > 0 && (
        <div style={{ display: "flex", gap: 16, marginBottom: 24, flexWrap: "wrap" }}>
          <div style={{ flex: 1, minWidth: 280, background: "#1a1a1a", border: "1px solid #f59e0b33", borderRadius: 8, padding: "16px 18px" }}>
            <div style={{ fontSize: 11, color: "#f59e0b", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>Hold Reasons</div>
            {gate.hold_reasons.map((r: string, i: number) => (
              <div key={i} style={{ fontSize: 12, color: "#ccc", marginBottom: 6, display: "flex", gap: 8 }}>
                <span style={{ color: "#f59e0b" }}>·</span>{r}
              </div>
            ))}
          </div>
          <div style={{ flex: 1, minWidth: 280, background: "#1a1a1a", border: "1px solid #22222255", borderRadius: 8, padding: "16px 18px" }}>
            <div style={{ fontSize: 11, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>Required Actions</div>
            {(gate.required_actions || []).map((a: string, i: number) => (
              <div key={i} style={{ fontSize: 12, color: "#ccc", marginBottom: 6, display: "flex", gap: 8 }}>
                <span style={{ color: "#22c55e" }}>→</span>{a}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scenario Table - Mandatory */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 11, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          Stress Scenarios — Mandatory Gate
        </div>
        <div style={{ background: "#1a1a1a", border: "1px solid #222", borderRadius: 8, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #222" }}>
                {["Scenario","LTV","DSCR","Debt Yield","Gate","Breach"].map(h => (
                  <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "#6a6a6a", fontWeight: 500, fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase" }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mandatory.map((s: any, i: number) => {
                const gc = GATE_COLOR[s.scenario_gate] || "#6a6a6a";
                return (
                  <tr key={i} style={{ borderBottom: "1px solid #1e1e1e" }}>
                    <td style={{ padding: "9px 14px", color: "#ccc" }}>{s.scenario_id}</td>
                    <td style={{ padding: "9px 14px", color: "#ccc" }}>{pct(s.stressed_ltv_gross)}</td>
                    <td style={{ padding: "9px 14px", color: s.stressed_dscr < 1.0 ? "#ef4444" : "#ccc" }}>{x2(s.stressed_dscr)}</td>
                    <td style={{ padding: "9px 14px", color: "#ccc" }}>{pct(s.stressed_debt_yield)}</td>
                    <td style={{ padding: "9px 14px" }}><span style={{ color: gc, fontWeight: 600 }}>{s.scenario_gate}</span></td>
                    <td style={{ padding: "9px 14px", color: "#6a6a6a", fontSize: 11 }}>
                      {(s.breach_vector || []).join(", ") || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Evidence Panel */}
      {evidence?.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 11, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
            Evidence & Provenance
          </div>
          <div style={{ background: "#1a1a1a", border: "1px solid #222", borderRadius: 8, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #222" }}>
                  {["Type","Source","Status","Confidence","Distribution"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: "#6a6a6a", fontWeight: 500, fontSize: 10, letterSpacing: "0.06em", textTransform: "uppercase" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evidence.map((ev: any, i: number) => (
                  <tr key={i} style={{ borderBottom: "1px solid #1e1e1e" }}>
                    <td style={{ padding: "9px 14px", color: "#ccc" }}>{ev.evidence_type}</td>
                    <td style={{ padding: "9px 14px", color: "#6a6a6a" }}>{ev.source_system}</td>
                    <td style={{ padding: "9px 14px" }}>
                      <span style={{ color: ev.verification_status === "VERIFIED" ? "#22c55e" : ev.verification_status === "ESTIMATED" ? "#eab308" : "#6a6a6a" }}>
                        {ev.verification_status}
                      </span>
                    </td>
                    <td style={{ padding: "9px 14px" }}>
                      <span style={{ color: CONF_COLOR[ev.confidence_level] || "#6a6a6a" }}>{ev.confidence_level}</span>
                    </td>
                    <td style={{ padding: "9px 14px", color: "#6a6a6a", fontSize: 11 }}>{ev.distribution_level}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tail Warnings - Separated */}
      {tail.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 11, color: "#6a6a6a", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
            Tail Stress Warnings
            <span style={{ marginLeft: 8, color: "#4a4a4a", fontSize: 10, fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>
              — 정보성. Final Gate 미반영.
            </span>
          </div>
          <div style={{ background: "#111", border: "1px solid #2a2a2a", borderRadius: 8, padding: "14px 18px", display: "flex", gap: 16, flexWrap: "wrap" }}>
            {tail.map((s: any, i: number) => {
              const gc = GATE_COLOR[s.scenario_gate] || "#6a6a6a";
              return (
                <div key={i} style={{ background: "#1a1a1a", border: `1px solid ${gc}22`, borderRadius: 6, padding: "10px 14px", minWidth: 180 }}>
                  <div style={{ fontSize: 11, color: "#6a6a6a", marginBottom: 4 }}>{s.scenario_id}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: gc }}>{s.scenario_gate}</div>
                  <div style={{ fontSize: 10, color: "#4a4a4a", marginTop: 4 }}>
                    DSCR {x2(s.stressed_dscr)} · LTV {pct(s.stressed_ltv_gross)}
                  </div>
                </div>
              );
            })}
          </div>
          <div style={{ fontSize: 10, color: "#4a4a4a", marginTop: 6 }}>
            LUSKA_GATE_V0_1 정책상 Historical Tail Stress는 Gate 판정에 미반영. 자본 버퍼 참고용.
          </div>
        </div>
      )}

      {/* Footer */}
      <div style={{ fontSize: 10, color: "#333", marginTop: 8, borderTop: "1px solid #1a1a1a", paddingTop: 12 }}>
        COSMOS Risk Book · {deal.deal_code} · Policy: {gate?.policy_id} v{gate?.gate_version} · {new Date(gate?.created_at).toLocaleDateString("ko-KR")}
      </div>
    </div>
  );
}
