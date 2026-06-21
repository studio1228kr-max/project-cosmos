import React, { useEffect, useState } from "react";
import axios from "axios";

const API = "https://project-cosmos-production.up.railway.app";


const C = {
  bg:       "#090a0b",
  surface:  "#0f1012",
  surface2: "#141618",
  border:   "#1c1e21",
  gold:     "#b8912a",
  goldDim:  "#7a6020",
  text:     "#e8e6e0",
  textS:    "#6b6b6b",
  textSS:   "#3a3a3a",
  critical: "#c0392b",
  moderate: "#d4851a",
  clear:    "#27ae60",
  deferred: "#3a3a3a",
};

const TAG = ({ label, color, bg }: { label: string; color: string; bg: string }) => (
  <span style={{
    display: "inline-block", padding: "2px 8px", fontSize: 10,
    fontFamily: "monospace", letterSpacing: "0.12em", fontWeight: 700,
    color, background: bg, border: `1px solid ${color}30`,
  }}>{label}</span>
);

const GATE_COLOR: Record<string, string> = {
  HOLD: C.critical, RESTRUCTURE: C.moderate, ADVANCE: C.clear, REJECT: C.critical,
};

const SEV_COLOR: Record<string, string> = {
  CRITICAL: C.critical, MODERATE: C.moderate, DEFERRED: C.deferred, CLEAR: C.clear,
};

export default function RiskBook() {
  const [deals, setDeals] = useState<any[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("token") || "";
    axios.get(`${API}/api/risk-book/deals`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { setDeals(r.data); if (r.data.length > 0) setSelected(r.data[0].deal_code); })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selected) return;
    setLoading(true);
    const token = localStorage.getItem("token") || "";
    axios.get(`${API}/api/risk-book/deals/${selected}/summary`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => { setData(r.data); setLoading(false); })
      .catch(() => setLoading(false));
  }, [selected]);

  const [riskCard, setRiskCard] = useState<any>(null);

  useEffect(() => {
    if (!selected) return;
    const token = localStorage.getItem("token") || "";
    axios.get(`${API}/api/risk-book/deals/${selected}/risk-card`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => setRiskCard(r.data))
      .catch(() => setRiskCard(null));
  }, [selected]);

  const deal = data?.deal;
  const gate = data?.gate;
  const scenarios = data?.scenarios || [];
  const fin = data?.financials;

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text, fontFamily: "'IBM Plex Mono', 'Courier New', monospace" }}>

      {/* TOP BAR */}
      <div style={{ borderBottom: `1px solid ${C.border}`, padding: "12px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", background: C.surface }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <span style={{ fontSize: 10, letterSpacing: "0.2em", color: C.gold, fontWeight: 700 }}>COSMOS</span>
          <span style={{ color: C.border }}>|</span>
          <span style={{ fontSize: 10, letterSpacing: "0.15em", color: C.textS }}>DIAGNOSTIC ENGINE</span>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          {deals.map(d => (
            <button key={d.deal_code} onClick={() => setSelected(d.deal_code)}
              style={{
                padding: "4px 12px", fontSize: 10, letterSpacing: "0.1em",
                background: selected === d.deal_code ? C.gold : "transparent",
                color: selected === d.deal_code ? "#000" : C.textS,
                border: `1px solid ${selected === d.deal_code ? C.gold : C.border}`,
                cursor: "pointer", fontFamily: "inherit",
              }}>
              {d.deal_code}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div style={{ padding: 64, textAlign: "center", color: C.textS, fontSize: 11, letterSpacing: "0.15em" }}>
          LOADING DIAGNOSTIC DATA...
        </div>
      )}

      {!loading && deal && (
        <div style={{ padding: "0 32px 48px" }}>

          {/* DEAL HEADER */}
          <div style={{ padding: "24px 0 20px", borderBottom: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 10, color: C.textS, letterSpacing: "0.15em", marginBottom: 6 }}>
              {deal.deal_code} · {deal.asset_type} · {deal.stage}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: "0.05em", color: C.text, marginBottom: 4 }}>
              {deal.deal_name}
            </div>
            <div style={{ fontSize: 11, color: C.textS }}>
              {deal.asset_address} · {deal.borrower} · {deal.current_lender} → {deal.proposed_lender}
            </div>
          </div>

          {/* DECISION STRIP */}
          {riskCard && (
            <div style={{ margin: "20px 0 4px", border: `1px solid ${riskCard.gate_result === "HOLD" ? C.critical : C.border}`, background: C.surface }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 16px", borderBottom: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 9, color: C.textS, letterSpacing: "0.15em" }}>COSMOS GATE ENGINE</div>
                <div style={{
                  fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", padding: "2px 10px",
                  color: riskCard.gate_result === "HOLD" ? C.critical : C.clear,
                  border: `1px solid ${riskCard.gate_result === "HOLD" ? C.critical : C.clear}30`,
                  background: riskCard.gate_result === "HOLD" ? "#c0392b18" : "#27ae6018",
                }}>{riskCard.gate_result}</div>
              </div>
              <div style={{ padding: "10px 16px" }}>
                {(riskCard.gate_reasons || []).map((r: any, i: number) => (
                  <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 9, color: SEV_COLOR[r.severity] || C.textS, letterSpacing: "0.1em", minWidth: 60 }}>{r.severity}</span>
                    <span style={{ fontSize: 10, color: C.text, letterSpacing: "0.05em" }}>{r.label}</span>
                  </div>
                ))}
                {riskCard.diagnostic_summary && (
                  <div style={{ marginTop: 8, paddingTop: 8, borderTop: `1px solid ${C.border}`, display: "flex", gap: 16 }}>
                    <span style={{ fontSize: 9, color: C.textS }}>CRITICAL <span style={{ color: C.critical }}>{riskCard.diagnostic_summary.critical_count}</span></span>
                    <span style={{ fontSize: 9, color: C.textS }}>MODERATE <span style={{ color: C.moderate }}>{riskCard.diagnostic_summary.moderate_count}</span></span>
                    {riskCard.calculated_at && <span style={{ fontSize: 9, color: C.textSS }}>{riskCard.calculated_at.slice(0,16)}</span>}
                  </div>
                )}
              </div>
            </div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 1, margin: "1px 0", background: C.border }}>
            {[
              { label: "DECISION", value: gate?.final_gate, color: GATE_COLOR[gate?.final_gate] || C.gold },
              { label: "REC. PATH", value: gate?.provisional_gate || "—", color: GATE_COLOR[gate?.provisional_gate] || C.textS },
              { label: "EVIDENCE", value: gate?.data_gate, color: gate?.data_gate === "COMPLETE" ? C.clear : gate?.data_gate === "PARTIAL" ? C.moderate : C.critical },
              { label: "STRUCTURE", value: gate?.structural_gate, color: GATE_COLOR[gate?.structural_gate] || C.textS },
              { label: "IC READY", value: gate?.ic_ready ? "YES" : "NO", color: gate?.ic_ready ? C.clear : C.critical },
              { label: "EVIDENCE %", value: `${deal.evidence_completeness?.toFixed(0)}%`, color: C.text },
            ].map((item, i) => (
              <div key={i} style={{ background: C.surface, padding: "16px 20px" }}>
                <div style={{ fontSize: 9, color: C.textS, letterSpacing: "0.15em", marginBottom: 8 }}>{item.label}</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: item.color, letterSpacing: "0.08em" }}>{item.value}</div>
              </div>
            ))}
          </div>

          {/* CORE METRICS */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, marginBottom: 1, background: C.border }}>
            {[
              { label: "LTV GROSS", value: `${((deal.ltv_gross || 0) * 100).toFixed(1)}%`, sub: "담보가치 기준" },
              { label: "LTV NET", value: fin ? `${((fin.loan_amount / (fin.collateral_value_base - (fin.nts_seizure_amount || 0))) * 100).toFixed(1)}%` : "—", sub: "NTS 압류 차감" },
              { label: "BASE DSCR", value: `${(deal.dscr || 0).toFixed(2)}x`, sub: "NOI / Annual Interest" },
              { label: "DEBT YIELD", value: `${((deal.debt_yield || 0) * 100).toFixed(1)}%`, sub: "NOI / Loan Amount" },
            ].map((m, i) => (
              <div key={i} style={{ background: C.surface2, padding: "14px 20px" }}>
                <div style={{ fontSize: 9, color: C.textS, letterSpacing: "0.15em", marginBottom: 6 }}>{m.label}</div>
                <div style={{ fontSize: 20, fontWeight: 700, color: C.gold, letterSpacing: "0.03em" }}>{m.value}</div>
                <div style={{ fontSize: 9, color: C.textSS, marginTop: 4 }}>{m.sub}</div>
              </div>
            ))}
          </div>

          {/* FAILURE MAP + SCENARIOS */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 24 }}>

            {/* FAILURE MAP */}
            <div>
              <div style={{ fontSize: 9, color: C.gold, letterSpacing: "0.2em", marginBottom: 12, fontWeight: 700 }}>
                FAILURE MAP
              </div>
              <div style={{ border: `1px solid ${C.border}` }}>
                {/* Header */}
                <div style={{ display: "grid", gridTemplateColumns: "80px 1fr 80px", background: C.surface, padding: "8px 16px", borderBottom: `1px solid ${C.border}` }}>
                  {["DOMAIN", "ISSUE", "SEVERITY"].map(h => (
                    <div key={h} style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.15em" }}>{h}</div>
                  ))}
                </div>

                {gate?.hold_reasons?.length > 0 ? gate.hold_reasons.map((reason: string, i: number) => {
                  const isEv = reason.includes("담보") || reason.includes("감정");
                  const isStr = reason.includes("1순위") || reason.includes("등기") || reason.includes("NTS");
                  const isFin = reason.includes("DSCR") || reason.includes("LTV");
                  const domain = isEv ? "EVIDENCE" : isStr ? "STRUCTURAL" : isFin ? "FINANCIAL" : "LEGAL";
                  const sev = i < 2 ? "CRITICAL" : "MODERATE";
                  return (
                    <div key={i} style={{
                      display: "grid", gridTemplateColumns: "80px 1fr 80px",
                      padding: "12px 16px", borderBottom: `1px solid ${C.border}`,
                      background: i % 2 === 0 ? C.bg : C.surface,
                    }}>
                      <div style={{ fontSize: 9, color: SEV_COLOR[sev], letterSpacing: "0.1em", fontWeight: 700 }}>{domain}</div>
                      <div style={{ fontSize: 11, color: C.text, paddingRight: 16 }}>{reason}</div>
                      <div>
                        <TAG label={sev} color={SEV_COLOR[sev]} bg={`${SEV_COLOR[sev]}15`} />
                      </div>
                    </div>
                  );
                }) : (
                  <div style={{ padding: "20px 16px", fontSize: 11, color: C.textS }}>No failures detected.</div>
                )}

                {gate?.required_actions?.length > 0 && (
                  <>
                    <div style={{ padding: "8px 16px", background: C.surface, borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}>
                      <span style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.15em" }}>CURE ACTIONS</span>
                    </div>
                    {gate.required_actions.map((action: string, i: number) => (
                      <div key={i} style={{
                        padding: "10px 16px", borderBottom: `1px solid ${C.border}`,
                        background: i % 2 === 0 ? C.bg : C.surface,
                        display: "flex", gap: 8, alignItems: "flex-start",
                      }}>
                        <span style={{ color: C.gold, fontSize: 10, flexShrink: 0 }}>→</span>
                        <span style={{ fontSize: 11, color: C.textS }}>{action}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>

            {/* SCENARIO STRESS TABLE */}
            <div>
              <div style={{ fontSize: 9, color: C.gold, letterSpacing: "0.2em", marginBottom: 12, fontWeight: 700 }}>
                SCENARIO STRESS — FAIL MAP
              </div>
              <div style={{ border: `1px solid ${C.border}` }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 60px 60px 60px 80px", background: C.surface, padding: "8px 16px", borderBottom: `1px solid ${C.border}` }}>
                  {["SCENARIO", "LTV", "DSCR", "DY", "RESULT"].map(h => (
                    <div key={h} style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.12em" }}>{h}</div>
                  ))}
                </div>
                {scenarios.filter((s: any) => s.gate_weight !== "INFORMATIONAL").map((s: any, i: number) => (
                  <div key={i} style={{
                    display: "grid", gridTemplateColumns: "1fr 60px 60px 60px 80px",
                    padding: "10px 16px", borderBottom: `1px solid ${C.border}`,
                    background: i % 2 === 0 ? C.bg : C.surface,
                  }}>
                    <div style={{ fontSize: 10, color: C.textS, letterSpacing: "0.08em" }}>{s.scenario_id}</div>
                    <div style={{ fontSize: 11, color: C.text }}>{s.stressed_ltv_gross ? `${(s.stressed_ltv_gross * 100).toFixed(1)}%` : "—"}</div>
                    <div style={{ fontSize: 11, color: s.stressed_dscr < 1.0 ? C.critical : C.text }}>
                      {s.stressed_dscr ? `${s.stressed_dscr.toFixed(2)}x` : "—"}
                    </div>
                    <div style={{ fontSize: 11, color: C.text }}>{s.stressed_debt_yield ? `${(s.stressed_debt_yield * 100).toFixed(1)}%` : "—"}</div>
                    <div>
                      <TAG
                        label={s.scenario_gate}
                        color={GATE_COLOR[s.scenario_gate] || C.textS}
                        bg={`${GATE_COLOR[s.scenario_gate] || C.textS}15`}
                      />
                    </div>
                  </div>
                ))}

                {/* Tail scenarios */}
                {scenarios.filter((s: any) => s.gate_weight === "INFORMATIONAL").length > 0 && (
                  <>
                    <div style={{ padding: "8px 16px", background: C.surface, borderTop: `1px solid ${C.border}`, borderBottom: `1px solid ${C.border}` }}>
                      <span style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.12em" }}>HISTORICAL TAIL — INFORMATIONAL ONLY · NOT GATE-DETERMINATIVE</span>
                    </div>
                    {scenarios.filter((s: any) => s.gate_weight === "INFORMATIONAL").map((s: any, i: number) => (
                      <div key={i} style={{
                        display: "grid", gridTemplateColumns: "1fr 60px 60px 60px 80px",
                        padding: "10px 16px", borderBottom: `1px solid ${C.border}`,
                        background: C.bg, opacity: 0.6,
                      }}>
                        <div style={{ fontSize: 10, color: C.textSS, letterSpacing: "0.08em" }}>{s.scenario_id}</div>
                        <div style={{ fontSize: 11, color: C.textSS }}>—</div>
                        <div style={{ fontSize: 11, color: C.textSS }}>—</div>
                        <div style={{ fontSize: 11, color: C.textSS }}>—</div>
                        <div style={{ fontSize: 10, color: C.textSS }}>{s.scenario_gate}</div>
                      </div>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* FOOTER */}
          <div style={{ marginTop: 32, paddingTop: 16, borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between" }}>
            <span style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.12em" }}>
              COSMOS DIAGNOSTIC ENGINE · {deal.deal_code} · POLICY: {gate?.policy_id} v{gate?.gate_version}
            </span>
            <span style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.12em" }}>
              {gate?.created_at ? new Date(gate.created_at).toLocaleDateString("ko-KR") : "—"} · LUSKA CAPITAL MANAGEMENT
            </span>
          </div>

        </div>
      )}
    </div>
  );
}
