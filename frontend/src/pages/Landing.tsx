import React, { useState, useEffect } from "react";

const C = {
  bg:      "#09090b",
  surface: "#0f1012",
  border:  "#1c1e21",
  gold:    "#b8912a",
  goldDim: "#7a6020",
  text:    "#e8e6e0",
  textS:   "#6b6b6b",
  textSS:  "#3a3a3a",
};

const STATS = [
  { value: "5", label: "FAILURE DIMENSIONS" },
  { value: "12", label: "STRESS SCENARIOS" },
  { value: "∞", label: "ASSET CLASSES" },
  { value: "100%", label: "AUDIT TRAIL" },
];

const CAPABILITIES = [
  {
    num: "01",
    title: "Deal Failure Diagnostic Engine",
    desc: "딜을 넣으면 어디서 실패하는지 계산합니다. Evidence, Financial, Structural, Legal, Market — 5개 차원에서 독립적으로 진단하고 Gate를 도출합니다.",
  },
  {
    num: "02",
    title: "Stress Scenario Engine",
    desc: "Base부터 Historical Tail까지 12개 시나리오를 동시에 돌립니다. NOI 하락, 금리 상승, 담보가치 훼손, Combined — 어느 조건에서 딜이 깨지는지 정확히 보여줍니다.",
  },
  {
    num: "03",
    title: "Calculation Provenance",
    desc: "모든 숫자는 정책 버전, 증거 출처, 계산 일시와 함께 저장됩니다. LUSKA_GATE_V0_1 기준으로 산출된 결과는 변경 불가하며 감사 추적이 가능합니다.",
  },
  {
    num: "04",
    title: "Counterparty Refusal Cost",
    desc: "기존 대주가 거절하면, 신규 대주가 지연하면 — 각 카운터파티 입장에서 액션/비액션의 비용을 계산합니다. 협상 레버리지를 수치화합니다.",
  },
];

export default function Landing({ onLogin }: { onLogin: () => void }) {
  const [scrolled, setScrolled] = useState(false);
  const [connectOpen, setConnectOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", email: "", role: "", message: "", interests: [] as string[] });

  const INTERESTS = [
    "Overall Private Credit Portfolio Management",
    "Integrated Management of Real Estate, Private Credit & Private Lending",
    "Portfolio Risk Management & Attribution Analysis",
    "Credit Risk Analysis & Current Expected Credit Loss (CECL)",
    "Illiquid Asset Valuation & Performance Measurement",
    "Deal Execution & Asset Acquisition Management",
    "Compliance & Regulatory Reporting",
    "Operations Efficiency (Capital Call, Distribution, Commitment Tracking)",
    "Data Integration & Cloud Management",
    "Investment Accounting (ABOR) & Official Performance Management (PBOR)",
    "Private Markets Dedicated Analytics",
    "Climate & ESG Risk Analysis",
    "Asset Management Tools & Workflow",
    "Other (Please specify)",
  ];

  const toggleInterest = (item: string) => {
    setForm(f => ({
      ...f,
      interests: f.interests.includes(item)
        ? f.interests.filter(i => i !== item)
        : [...f.interests, item]
    }));
  };

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div style={{ background: C.bg, color: C.text, fontFamily: "'IBM Plex Mono', 'Courier New', monospace", minHeight: "100vh" }}>

      {/* NAV */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0, zIndex: 100,
        background: scrolled ? `${C.bg}f0` : "transparent",
        borderBottom: scrolled ? `1px solid ${C.border}` : "none",
        backdropFilter: scrolled ? "blur(12px)" : "none",
        transition: "all 0.3s",
        padding: "16px 48px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.2em", color: C.gold }}>COSMOS</span>
          <span style={{ fontSize: 10, color: C.textS, letterSpacing: "0.1em" }}>by Luska Capital Management</span>
        </div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {["Platform", "Capabilities", "About"].map(item => (
            <span key={item} style={{ fontSize: 11, color: C.textS, letterSpacing: "0.1em", cursor: "pointer" }}
              onMouseEnter={e => (e.currentTarget.style.color = C.text)}
              onMouseLeave={e => (e.currentTarget.style.color = C.textS)}>
              {item}
            </span>
          ))}
          <div style={{ position: "relative" }}>
            <button onClick={() => setConnectOpen(!connectOpen)} style={{
              padding: "8px 20px", fontSize: 10, letterSpacing: "0.15em",
              background: "transparent", color: C.gold,
              border: `1px solid ${C.gold}`, cursor: "pointer",
              fontFamily: "inherit", display: "flex", alignItems: "center", gap: 8,
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = C.gold; (e.currentTarget as HTMLButtonElement).style.color = "#000"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = C.gold; }}>
              Connect {connectOpen ? "∧" : "∨"}
            </button>
            {connectOpen && (
              <div style={{
                position: "absolute", top: "calc(100% + 4px)", right: 0,
                background: C.surface, border: `1px solid ${C.border}`,
                minWidth: 200, zIndex: 200,
              }}>
                <button onClick={onLogin} style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  width: "100%", padding: "14px 20px", fontSize: 11,
                  letterSpacing: "0.1em", background: "transparent",
                  color: C.text, border: "none", cursor: "pointer",
                  fontFamily: "inherit", textAlign: "left",
                }}
                  onMouseEnter={e => (e.currentTarget.style.background = C.border)}
                  onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                  COSMOS Client Log In <span style={{ color: C.gold }}>›</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* HERO */}
      <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr 1fr", position: "relative", paddingTop: 72 }}>

        {/* LEFT */}
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: "80px 64px 120px" }}>
          <div style={{ fontSize: 10, color: C.gold, letterSpacing: "0.3em", marginBottom: 32, fontWeight: 700, borderLeft: `2px solid ${C.gold}`, paddingLeft: 12 }}>
            PRIVATE CREDIT PORTFOLIO MANAGEMENT
          </div>
          <h1 style={{
            fontSize: "clamp(28px, 3.5vw, 52px)", fontWeight: 700,
            lineHeight: 1.15, letterSpacing: "-0.01em",
            margin: "0 0 28px", color: C.text,
            fontFamily: "'ZenSerif', Georgia, serif",
          }}>
            The Operating System<br />
            for Korean<br />
            <span style={{ color: C.gold }}>Private Credit.</span>
          </h1>
          <p style={{ fontSize: 13, color: C.textS, lineHeight: 1.9, maxWidth: 480, marginBottom: 16 }}>
            In alternative investments such as real estate, private credit, and private lending,
            risk management and stable return generation are among the most important priorities.
          </p>
          <p style={{ fontSize: 13, color: C.textS, lineHeight: 1.9, maxWidth: 480, marginBottom: 48 }}>
            The LCM by COSMOS platform supports domestic institutional investors in transparently
            and systematically managing their overall Private Credit portfolios.
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button onClick={() => setModalOpen(true)} style={{
              padding: "14px 32px", fontSize: 11, letterSpacing: "0.15em",
              background: C.gold, color: "#000", border: "none",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
            }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "0.8")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "1")}>
              LEARN MORE →
            </button>
          </div>
        </div>

        {/* RIGHT — image placeholder */}
        <div style={{
          background: C.surface,
          borderLeft: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", justifyContent: "center",
          position: "relative", overflow: "hidden", minHeight: "100vh",
        }}>
          {/* Grid pattern */}
          <div style={{
            position: "absolute", inset: 0,
            backgroundImage: `linear-gradient(${C.border} 1px, transparent 1px), linear-gradient(90deg, ${C.border} 1px, transparent 1px)`,
            backgroundSize: "40px 40px",
          }} />
          <div style={{ position: "relative", textAlign: "center" }}>
            <div style={{ fontSize: 10, color: C.textSS, letterSpacing: "0.2em" }}>IMAGE PENDING</div>
          </div>
        </div>

        {/* Bottom stats bar */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
          borderTop: `1px solid ${C.border}`,
          background: `${C.bg}e0`, backdropFilter: "blur(8px)",
        }}>
          {STATS.map((s, i) => (
            <div key={i} style={{
              padding: "20px 48px",
              borderRight: i < 3 ? `1px solid ${C.border}` : "none",
            }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.gold, letterSpacing: "-0.02em", marginBottom: 4 }}>{s.value}</div>
              <div style={{ fontSize: 9, color: C.textS, letterSpacing: "0.15em" }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* CAPABILITIES */}
      <div style={{ padding: "80px 48px", borderTop: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 9, color: C.gold, letterSpacing: "0.3em", marginBottom: 48, fontWeight: 700 }}>CORE CAPABILITIES</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1, background: C.border }}>
          {CAPABILITIES.map((cap, i) => (
            <div key={i} style={{ background: C.bg, padding: "40px 48px" }}>
              <div style={{ fontSize: 11, color: C.goldDim, letterSpacing: "0.2em", marginBottom: 16, fontWeight: 700 }}>{cap.num}</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: C.text, marginBottom: 16, letterSpacing: "0.02em" }}>{cap.title}</div>
              <div style={{ fontSize: 12, color: C.textS, lineHeight: 1.8 }}>{cap.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* POLICY BADGE */}
      <div style={{ padding: "80px 48px", borderTop: `1px solid ${C.border}`, textAlign: "center" }}>
        <div style={{ fontSize: 9, color: C.textSS, letterSpacing: "0.2em", marginBottom: 24 }}>CALCULATION STANDARD</div>
        <div style={{ fontSize: 48, fontWeight: 700, color: C.border, letterSpacing: "0.05em", marginBottom: 24 }}>
          LUSKA_GATE_V0_1
        </div>
        <p style={{ fontSize: 12, color: C.textS, maxWidth: 560, margin: "0 auto 40px", lineHeight: 1.8 }}>
          모든 Gate 판정은 정책 버전과 함께 저장됩니다.
          숫자를 보는 것으로는 부족합니다 — 그 숫자가 어떤 정책으로 언제 계산됐는지가 중요합니다.
        </p>
        <button onClick={onLogin} style={{
          padding: "14px 40px", fontSize: 11, letterSpacing: "0.2em",
          background: "transparent", color: C.gold,
          border: `1px solid ${C.gold}`, cursor: "pointer", fontFamily: "inherit",
        }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = C.gold; (e.currentTarget as HTMLButtonElement).style.color = "#000"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = C.gold; }}>
          REQUEST ACCESS →
        </button>
      </div>

      {/* FOOTER */}
      <div style={{ padding: "32px 48px", borderTop: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: 10, color: C.textSS, letterSpacing: "0.1em" }}>
          © 2026 LUSKA CAPITAL MANAGEMENT · COSMOS PRIVATE CREDIT OS
        </div>
        <div style={{ fontSize: 10, color: C.textSS, letterSpacing: "0.1em" }}>
          PARNAS TOWER 29F · GANGNAM · SEOUL
        </div>
      </div>

    </div>

      {modalOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 500,
          background: "rgba(0,0,0,0.85)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "flex-start", justifyContent: "center",
          overflowY: "auto", padding: "40px 24px",
        }} onClick={e => { if (e.target === e.currentTarget) setModalOpen(false); }}>
          <div style={{
            background: "#0f1012", border: "1px solid #1c1e21",
            width: "100%", maxWidth: 800, padding: "48px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 40 }}>
              <div>
                <div style={{ fontSize: 10, color: "#b8912a", letterSpacing: "0.2em", marginBottom: 12 }}>COSMOS BY LUSKA CAPITAL</div>
                <h2 style={{ fontSize: 22, fontWeight: 700, color: "#e8e6e0", margin: 0 }}>
                  Get in touch to learn more about COSMOS
                </h2>
              </div>
              <button onClick={() => setModalOpen(false)} style={{
                background: "none", border: "none", color: "#6b6b6b",
                fontSize: 20, cursor: "pointer", padding: 4,
              }}>✕</button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24, marginBottom: 24 }}>
              {[
                { label: "First Name *", key: "name", placeholder: "" },
                { label: "Company Name *", key: "company", placeholder: "" },
                { label: "Business Email *", key: "email", placeholder: "" },
              ].map(field => (
                <div key={field.key}>
                  <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 8 }}>{field.label}</div>
                  <input
                    value={(form as any)[field.key]}
                    onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                    style={{
                      width: "100%", padding: "8px 0", fontSize: 13,
                      background: "transparent", border: "none",
                      borderBottom: "1px solid #1c1e21", color: "#e8e6e0",
                      fontFamily: "inherit", outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24, marginBottom: 32 }}>
              <div>
                <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 8 }}>Phone Number *</div>
                <input style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "transparent", border: "none", borderBottom: "1px solid #1c1e21", color: "#e8e6e0", fontFamily: "inherit", outline: "none", boxSizing: "border-box" }} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 8 }}>Organization Type *</div>
                <select style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "#0f1012", border: "none", borderBottom: "1px solid #1c1e21", color: "#e8e6e0", fontFamily: "inherit", outline: "none" }}>
                  <option value="">Select</option>
                  <option>Pension Fund</option>
                  <option>Insurance Company</option>
                  <option>Asset Manager</option>
                  <option>Securities Firm</option>
                  <option>Bank</option>
                  <option>Other</option>
                </select>
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 8 }}>Primary Role *</div>
                <select
                  value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "#0f1012", border: "none", borderBottom: "1px solid #1c1e21", color: "#e8e6e0", fontFamily: "inherit", outline: "none" }}>
                  <option value="">Select</option>
                  <option>CIO / CRO</option>
                  <option>Portfolio Manager</option>
                  <option>Credit Analyst</option>
                  <option>IR / BD</option>
                  <option>Other</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 16 }}>Areas of Interest (Select all that apply)</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {INTERESTS.map(item => (
                  <label key={item} style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer" }}
                    onClick={() => toggleInterest(item)}>
                    <div style={{
                      width: 14, height: 14, flexShrink: 0, marginTop: 2,
                      border: `1px solid ${form.interests.includes(item) ? "#b8912a" : "#1c1e21"}`,
                      background: form.interests.includes(item) ? "#b8912a" : "transparent",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      {form.interests.includes(item) && <span style={{ fontSize: 9, color: "#000", fontWeight: 700 }}>✓</span>}
                    </div>
                    <span style={{ fontSize: 11, color: "#6b6b6b", lineHeight: 1.5 }}>{item}</span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 11, color: "#e8e6e0", fontWeight: 700, marginBottom: 8 }}>How can we help you?</div>
              <textarea
                value={form.message}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                rows={4}
                style={{
                  width: "100%", padding: 12, fontSize: 13,
                  background: "#090a0b", border: "1px solid #1c1e21",
                  color: "#e8e6e0", fontFamily: "inherit", outline: "none",
                  resize: "vertical", boxSizing: "border-box",
                }}
              />
            </div>

            <button style={{
              padding: "14px 40px", fontSize: 11, letterSpacing: "0.15em",
              background: "#b8912a", color: "#000", border: "none",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
            }}>SUBMIT →</button>
          </div>
        </div>
      )}
  );
}
