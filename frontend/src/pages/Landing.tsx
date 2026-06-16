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
          <button onClick={onLogin} style={{
            padding: "8px 20px", fontSize: 10, letterSpacing: "0.15em",
            background: "transparent", color: C.gold,
            border: `1px solid ${C.gold}`, cursor: "pointer",
            fontFamily: "inherit",
            transition: "all 0.2s",
          }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = C.gold; (e.currentTarget as HTMLButtonElement).style.color = "#000"; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = "transparent"; (e.currentTarget as HTMLButtonElement).style.color = C.gold; }}>
            SIGN IN →
          </button>
        </div>
      </nav>

      {/* HERO */}
      <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", justifyContent: "center", padding: "0 48px", position: "relative", overflow: "hidden" }}>
        {/* Grid overlay */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: `linear-gradient(${C.border} 1px, transparent 1px), linear-gradient(90deg, ${C.border} 1px, transparent 1px)`,
          backgroundSize: "60px 60px", opacity: 0.3,
        }} />
        <div style={{ position: "relative", maxWidth: 800 }}>
          <div style={{ fontSize: 10, color: C.gold, letterSpacing: "0.3em", marginBottom: 24, fontWeight: 700 }}>
            PRIVATE CREDIT DIAGNOSTIC ENGINE
          </div>
          <h1 style={{
            fontSize: "clamp(32px, 5vw, 64px)", fontWeight: 700,
            lineHeight: 1.1, letterSpacing: "-0.02em",
            margin: "0 0 24px", color: C.text,
          }}>
            딜을 넣으면<br />
            <span style={{ color: C.gold }}>어디서 실패하는지</span><br />
            계산합니다.
          </h1>
          <p style={{ fontSize: 14, color: C.textS, lineHeight: 1.8, maxWidth: 560, marginBottom: 40 }}>
            COSMOS는 루스카 캐피탈 매니지먼트의 범용 프라이빗 크레딧 OS입니다.
            CRE, Corporate, Special Situations — 에셋클래스에 무관하게
            딜의 실패 차원을 진단하고 Gate를 도출합니다.
          </p>
          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={onLogin} style={{
              padding: "14px 32px", fontSize: 11, letterSpacing: "0.15em",
              background: C.gold, color: "#000", border: "none",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
              transition: "opacity 0.2s",
            }}
              onMouseEnter={e => (e.currentTarget.style.opacity = "0.85")}
              onMouseLeave={e => (e.currentTarget.style.opacity = "1")}>
              ACCESS COSMOS →
            </button>
            <button style={{
              padding: "14px 32px", fontSize: 11, letterSpacing: "0.15em",
              background: "transparent", color: C.textS,
              border: `1px solid ${C.border}`, cursor: "pointer", fontFamily: "inherit",
            }}>
              LEARN MORE
            </button>
          </div>
        </div>

        {/* Bottom stats */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
          borderTop: `1px solid ${C.border}`,
        }}>
          {STATS.map((s, i) => (
            <div key={i} style={{
              padding: "24px 48px",
              borderRight: i < 3 ? `1px solid ${C.border}` : "none",
            }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: C.gold, letterSpacing: "-0.02em", marginBottom: 4 }}>{s.value}</div>
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
  );
}
