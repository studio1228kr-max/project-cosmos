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





export default function Landing({ onLogin }: { onLogin: () => void }) {
  const [scrolled, setScrolled] = useState(false);
  const [connectOpen, setConnectOpen] = useState(false);
  const [scamAlert, setScamAlert] = useState(true);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
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
        padding: isMobile ? "12px 20px" : "16px 48px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.2em", color: C.gold }}>Cosmos</span>
          <span style={{ fontSize: 10, color: C.textS, letterSpacing: "0.1em" }}>by LuskaCapitalManagement</span>
        </div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {!isMobile && ["Platform", "Capabilities", "About"].map(item => (
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
      <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", position: "relative", paddingTop: 72 }}>

        {/* LEFT */}
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center", padding: isMobile ? "40px 24px 80px" : "80px 64px 120px" }}>
          <div style={{ fontSize: 10, color: C.gold, letterSpacing: "0.3em", marginBottom: 32, fontWeight: 700, borderLeft: `2px solid ${C.gold}`, paddingLeft: 12 }}>
            PRIVATE CREDIT PORTFOLIO MANAGEMENT
          </div>
          <h1 style={{
            fontSize: isMobile ? "clamp(28px, 8vw, 40px)" : "clamp(28px, 3.5vw, 52px)", fontWeight: 700,
            lineHeight: 1.15, letterSpacing: "-0.01em",
            margin: "0 0 28px", color: C.text,
            fontFamily: "'ZenSerif', Georgia, serif",
          }}>
            The Operating System<br />
            for Korean <span style={{ color: C.gold }}>Private Credit.</span>
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
        {!isMobile && <div style={{
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
        </div>}


      </div>



      {/* DISCLAIMER + FOOTER */}
      <div style={{ borderTop: `1px solid ${C.border}`, padding: isMobile ? "24px 20px 16px" : "32px 80px 24px", background: C.surface }}>
        <div style={{ fontSize: 9, color: C.gold, letterSpacing: "0.2em", marginBottom: 20, fontWeight: 700 }}>DISCLAIMER</div>
        <div style={{ fontSize: 11, color: C.textSS, lineHeight: 1.9, maxWidth: 1200 }}>
          <p style={{ marginBottom: 16 }}>
            This material is provided for informational purposes only and should not be construed as investment advice, investment recommendation, solicitation, or an offer to buy or sell any securities or adopt any investment strategy. Opinions and information contained in this material are subject to change without notice.
          </p>
          <p style={{ marginBottom: 16 }}>
            This material is intended to provide general information regarding the COSMOS platform (Cosmos by LuskaCapitalManagement) and is designed to assist in understanding the Private Credit sector, including real estate, private credit, and private lending. We do not guarantee the accuracy or completeness of the information provided. Any investment decision should be based on independent professional advice and your own due diligence.
          </p>
          <p style={{ marginBottom: 16 }}>
            All risk analysis, return analysis, valuation, and other calculations provided through the Cosmos platform are based on assumptions, historical data, user inputs, and other factors, and are not a guarantee of future results. All graphs and screenshots are provided for illustrative purposes only.
          </p>
          <p style={{ marginBottom: 16 }}>
            The Cosmos platform is intended solely for institutional investors and qualified investors in the Republic of Korea. It is not intended for use by retail or individual investors. Users of the Cosmos platform bear full responsibility for their own investment decisions and compliance with all applicable laws and regulations. This material should not be interpreted as investment advice or a recommendation.
          </p>
          <p style={{ marginBottom: 24 }}>
            Cosmos reserves the right to modify or discontinue any features or services described in this material at any time without prior notice. This material is intended for distribution only within the Republic of Korea and is not intended for use or distribution in any other jurisdiction.
          </p>
        </div>
        <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 20 }}>
          <div style={{ fontSize: 10, color: C.textSS, letterSpacing: "0.08em" }}>
            © 2025 Cosmos by LuskaCapitalManagement. All Rights Reserved.
          </div>
        </div>
      </div>

      {scamAlert && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.92)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: isMobile ? "16px" : "40px",
        }}>
          <div style={{
            background: "#0f1012", border: "1px solid #b8912a",
            maxWidth: 560, width: "100%", padding: isMobile ? "28px 24px" : "40px 48px",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <span style={{ fontSize: 16 }}>⚠️</span>
              <span style={{ fontSize: 11, color: "#b8912a", letterSpacing: "0.2em", fontWeight: 700 }}>
                INVESTMENT SCAM WARNING
              </span>
            </div>
            <p style={{ fontSize: 13, color: "#e8e6e0", lineHeight: 1.9, marginBottom: 16 }}>
              LuskaCapitalManagement and COSMOS never solicit investments, offer consultations,
              or request money transfers from individual or retail investors.
            </p>
            <p style={{ fontSize: 13, color: "#6b6b6b", lineHeight: 1.9, marginBottom: 28 }}>
              Scams impersonating financial companies are on the rise. If you receive any suspicious
              contact pretending to be from COSMOS or our team, please ignore it and report immediately
              to the police (112) or Financial Supervisory Service (1332).
              We are not liable for any damages caused by such impersonation scams.
            </p>
            <button onClick={() => setScamAlert(false)} style={{
              width: "100%", padding: "14px", fontSize: 11, letterSpacing: "0.15em",
              background: "#b8912a", color: "#000", border: "none",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
            }}>
              I UNDERSTAND →
            </button>
          </div>
        </div>
      )}

      {modalOpen && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 500,
          background: "rgba(0,0,0,0.85)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "flex-start", justifyContent: "center",
          overflowY: "auto", padding: isMobile ? "16px 8px" : "40px 24px",
        }} onClick={e => { if (e.target === e.currentTarget) setModalOpen(false); }}>
          <div style={{
            background: "#0f1012", border: "1px solid #1c1e21",
            width: "100%", maxWidth: "100%", padding: isMobile ? "24px 20px" : "48px 80px",
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

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr 1fr", gap: isMobile ? 16 : 24, marginBottom: 24 }}>
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

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr 1fr", gap: isMobile ? 16 : 24, marginBottom: 32 }}>
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
              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 10 }}>
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
    </div>
  );
}
