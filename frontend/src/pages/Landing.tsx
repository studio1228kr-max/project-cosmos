import React, { useState, useEffect } from "react";

const C = {
  bg:      "#FFFFFF",
  surface: "#F4F8FC",
  border:  "#D9E4EF",
  gold:    "#1D4F77",
  goldDim: "#0E3450",
  text:    "#15213D",
  textS:   "#5A6B85",
  textSS:  "#8FA3BB",
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
  const [privacyOpen, setPrivacyOpen] = useState(false);
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
    <div style={{ background: C.bg, color: C.text, fontFamily: "'Inter', sans-serif", minHeight: "100vh" }}>

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
          {!isMobile && <span style={{ fontSize: 10, color: C.textS, letterSpacing: "0.1em" }}>by Luska Capital Management</span>}
        </div>
        <div style={{ display: "flex", gap: 32, alignItems: "center" }}>
          {!isMobile && ["Platform", "Capabilities", "About"].map(item => (
            <span key={item} style={{ fontSize: 11, fontWeight: 400, color: C.textS, letterSpacing: "0.05em", cursor: "pointer" }}
              onMouseEnter={e => (e.currentTarget.style.color = C.text)}
              onMouseLeave={e => (e.currentTarget.style.color = C.textS)}>
              {item}
            </span>
          ))}
          {!isMobile && <div style={{ position: "relative" }}>
            <button onClick={() => setConnectOpen(!connectOpen)} style={{
              padding: "8px 20px", fontSize: 10, letterSpacing: "0.15em",
              background: "transparent", color: C.gold,
              border: `1px solid ${C.gold}`, cursor: "pointer",
              fontFamily: "inherit", display: "flex", alignItems: "center", gap: 8,
            }}
              onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = C.gold; (e.currentTarget as HTMLButtonElement).style.color = "#fff"; }}
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
                  Cosmos Client Log In <span style={{ color: C.gold }}>›</span>
                </button>
              </div>
            )}
          </div>}
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
            lineHeight: 1.15, letterSpacing: "-0.02em",
            margin: "0 0 28px", color: C.text,
            fontFamily: "'Inter', sans-serif",
          }}>
            The Operating System<br />
            for Korean <span style={{ color: C.gold }}>Private Credit.</span>
          </h1>
          <p style={{ fontSize: 13, fontWeight: 300, color: "#64748B", lineHeight: 1.9, maxWidth: 480, marginBottom: 16 }}>
            In alternative investments such as real estate, private credit, and private lending,
            risk management and stable return generation are among the most important priorities.
          </p>
          <p style={{ fontSize: 13, fontWeight: 300, color: "#64748B", lineHeight: 1.9, maxWidth: 480, marginBottom: 48 }}>
            The LCM by Cosmos platform supports domestic institutional investors in transparently
            and systematically managing their overall Private Credit portfolios.
          </p>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button onClick={() => setModalOpen(true)} style={{
              padding: "14px 32px", fontSize: 11, letterSpacing: "0.15em",
              background: C.gold, color: "#fff", border: "none",
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



      {/* 3-CARD CAPABILITIES SECTION */}
      <div style={{ background: "#080C14", padding: isMobile ? "60px 24px" : "100px 80px", borderTop: "1px solid #1a2535" }}>
        <div style={{ textAlign: "center", marginBottom: isMobile ? 48 : 72 }}>
          <div style={{ fontSize: 10, color: "#4A7FA5", letterSpacing: "0.3em", marginBottom: 16, fontWeight: 700 }}>PLATFORM CAPABILITIES</div>
          <h2 style={{ fontSize: isMobile ? 24 : 32, fontWeight: 700, color: "#FFFFFF", margin: 0, fontFamily: "'Inter', sans-serif", letterSpacing: "-0.01em" }}>
            Built for the Full Deal Lifecycle
          </h2>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr 1fr", gap: 24, maxWidth: 1100, margin: "0 auto" }}>
          {[
            {
              icon: (
                <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
                  <circle cx="14" cy="14" r="9" stroke="#4A7FA5" strokeWidth="1.5"/>
                  <line x1="21" y1="21" x2="32" y2="32" stroke="#4A7FA5" strokeWidth="1.5" strokeLinecap="round"/>
                  <circle cx="14" cy="14" r="4" stroke="#4A7FA5" strokeWidth="1"/>
                </svg>
              ),
              title: "Origination",
              sub: "Surface relevant opportunities and track pipeline momentum.",
            },
            {
              icon: (
                <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
                  <rect x="4" y="16" width="28" height="1.5" fill="#4A7FA5"/>
                  <rect x="10" y="8" width="1.5" height="20" fill="#4A7FA5"/>
                  <rect x="24.5" y="8" width="1.5" height="20" fill="#4A7FA5"/>
                  <rect x="7" y="24" width="6" height="1.5" fill="#4A7FA5"/>
                  <rect x="23" y="10" width="6" height="1.5" fill="#4A7FA5"/>
                </svg>
              ),
              title: "Underwriting",
              sub: "Transform raw deal evidence into structured underwriting judgment.",
            },
            {
              icon: (
                <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
                  <polyline points="4,24 10,16 16,20 22,10 28,14 34,8" stroke="#4A7FA5" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
                  <line x1="4" y1="28" x2="34" y2="28" stroke="#1a2535" strokeWidth="1"/>
                </svg>
              ),
              title: "Monitoring",
              sub: "Track portfolio risk, covenant signals, and execution drift over time.",
            },
          ].map(({ icon, title, sub }) => (
            <div key={title} style={{
              border: "1px solid #1e3048",
              padding: isMobile ? "40px 28px" : "52px 44px",
              background: "rgba(255,255,255,0.02)",
              transition: "border-color 0.2s",
              display: "flex", flexDirection: "column",
            }}
              onMouseEnter={e => (e.currentTarget.style.borderColor = "#4A7FA5")}
              onMouseLeave={e => (e.currentTarget.style.borderColor = "#1e3048")}>
              <div style={{ marginBottom: 32 }}>{icon}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#FFFFFF", marginBottom: 16, fontFamily: "'Inter', sans-serif", letterSpacing: "0.01em" }}>{title}</div>
              <div style={{ fontSize: 13, color: "#7A9ABF", lineHeight: 1.9, fontFamily: "'Inter', sans-serif" }}>{sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ACCESS STRIP */}
      <div style={{ background: "#0E1E2E", borderTop: "1px solid #1e3a52", borderBottom: "1px solid #1e3a52", padding: isMobile ? "20px 24px" : "20px 80px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 16 }}>
        <span style={{ fontSize: 12, color: "#8FA3BB", letterSpacing: "0.05em", fontFamily: "'Inter', sans-serif" }}>
          Cosmos is available to institutional investors by invitation only.
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button onClick={onLogin} style={{ padding: "8px 20px", fontSize: 10, letterSpacing: "0.15em", background: "#1D4F77", color: "#fff", border: "none", cursor: "pointer", fontFamily: "inherit", fontWeight: 700 }}>
            INVESTOR LOGIN
          </button>
          <span style={{ fontSize: 10, color: "#4A7FA5", letterSpacing: "0.1em", cursor: "pointer", textDecoration: "underline", fontFamily: "inherit" }} onClick={() => setModalOpen(true)}>
            Request Access
          </span>
        </div>
      </div>

      {/* POSITIONING BADGES */}
      <div style={{ background: "#F4F8FC", borderBottom: "1px solid #D9E4EF", padding: isMobile ? "20px 24px" : "20px 80px", display: "flex", alignItems: "center", gap: isMobile ? 16 : 40, flexWrap: "wrap" }}>
        {["Institutional Only", "Korea-Focused", "Private Credit Native"].map(badge => (
          <div key={badge} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 4, height: 4, background: "#1D4F77", borderRadius: "50%" }} />
            <span style={{ fontSize: 11, color: "#1D4F77", letterSpacing: "0.12em", fontWeight: 700, fontFamily: "'Inter', sans-serif" }}>{badge}</span>
          </div>
        ))}
      </div>

      {/* PHILOSOPHY */}
      <div style={{ background: "#FFFFFF", borderBottom: "1px solid #D9E4EF", padding: isMobile ? "48px 24px" : "64px 80px", textAlign: "center" }}>
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          <p style={{ fontSize: isMobile ? 18 : 22, fontWeight: 700, color: "#15213D", lineHeight: 1.5, marginBottom: 16, fontFamily: "'Inter', sans-serif", letterSpacing: "-0.01em" }}>
            We believe private credit requires disciplined evidence, not optimism.
          </p>
          <p style={{ fontSize: 12, color: "#5A6B85", lineHeight: 1.9, fontFamily: "'Inter', sans-serif" }}>
            Built for downside-first underwriting, structured diligence, and active risk monitoring.
          </p>
        </div>
      </div>

      {/* DISCLAIMER + FOOTER */}
      <div style={{ borderTop: `1px solid ${C.border}`, padding: isMobile ? "24px 20px 16px" : "32px 80px 24px", background: C.surface }}>
        <div style={{ fontSize: 9, color: C.gold, letterSpacing: "0.2em", marginBottom: 20, fontWeight: 700 }}>DISCLAIMER</div>
        <div style={{ fontSize: 11, color: C.textSS, lineHeight: 1.9, maxWidth: 1200 }}>
          <p style={{ marginBottom: 16 }}>
            This material is provided for informational purposes only and should not be construed as investment advice, investment recommendation, solicitation, or an offer to buy or sell any securities or adopt any investment strategy. Opinions and information contained in this material are subject to change without notice.
          </p>
          <p style={{ marginBottom: 16 }}>
            This material is intended to provide general information regarding the Cosmos platform (Cosmos by Luska Capital Management) and is designed to assist in understanding the Private Credit sector, including real estate, private credit, and private lending. We do not guarantee the accuracy or completeness of the information provided. Any investment decision should be based on independent professional advice and your own due diligence.
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
            © 2025 Cosmos by Luska Capital Management. All Rights Reserved.
            <span style={{ margin: "0 12px", color: C.border }}>|</span>
            <span style={{ cursor: "pointer", textDecoration: "underline" }}
              onClick={() => setPrivacyOpen(true)}>
              개인정보 처리방침
            </span>
          </div>
        </div>
      </div>

      {privacyOpen && (
        <div style={{ position:"fixed", inset:0, zIndex:600, background:"rgba(0,0,0,0.85)", backdropFilter:"blur(4px)", display:"flex", alignItems:"flex-start", justifyContent:"center", overflowY:"auto", padding: isMobile ? "16px 8px" : "40px 24px" }} onClick={e => { if(e.target===e.currentTarget) setPrivacyOpen(false); }}>
          <div style={{ background:"#fff", maxWidth:720, width:"100%", padding: isMobile ? "28px 20px" : "48px 56px", fontFamily:"'Inter', sans-serif" }}>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:32 }}>
              <div>
                <div style={{ fontSize:10, color:"#1D4F77", letterSpacing:"0.2em", fontWeight:700, marginBottom:8 }}>LUSKA CAPITAL MANAGEMENT</div>
                <div style={{ fontSize:20, fontWeight:700, color:"#15213D" }}>개인정보 처리방침</div>
              </div>
              <button onClick={() => setPrivacyOpen(false)} style={{ background:"none", border:"none", fontSize:20, cursor:"pointer", color:"#888" }}>✕</button>
            </div>
            {[
              { title:"1. 개인정보 수집·이용 목적", body:`· Cosmos 플랫폼 회원 가입, 본인 확인 및 계정 관리
· 플랫폼 서비스 제공, 딜 파이프라인·리포트·알림 등 핵심 기능 운영
· 문의·상담 응대 및 서비스 관련 공지사항 전달
· 서비스 품질 개선을 위한 이용 통계 분석 (익명·가명 정보 기준)
목적 변경 시 사전 동의 후 처리합니다.` },
              { title:"2. 수집 항목", body:`[필수] 이름, 직함, 소속(회사명), 직장 이메일, 비밀번호, 로그인 기록(IP, 접속 일시)
[선택] 직통 전화번호, 모바일 번호, 관심 투자 분야, 문의 내용
쿠키·유사 기술 사용 시 별도 쿠키 안내/동의 배너에서 고지합니다.` },
              { title:"3. 보유·이용 기간", body:`· 회원 탈퇴 시 또는 서비스 종료 시까지 보유·이용
· 관련 법령에 따른 별도 보관:
  - 계약·거래 관련 기록: 5년
  - 소비자 불만·분쟁 처리 기록: 3년
  - 전자금융 거래 기록: 5년
  - 접속 기록: 3개월
보유 기간 만료 또는 처리 목적 달성 시 지체 없이 파기합니다.` },
              { title:"4. 제3자 제공 여부", body:`원칙적으로 이용자의 개인정보를 제3자에게 제공하지 않습니다.
예외: 이용자 사전 동의 / 법령에 특별한 규정 / 생명·신체·재산의 급박한 위험 방지 / 특정 개인을 식별할 수 없는 형태의 통계·연구 목적
제공이 필요한 경우 제공받는 자·목적·항목·보유 기간을 별도 안내 후 동의를 받습니다.` },
              { title:"5. 처리 위탁", body:`현재 회사는 개인정보 처리 업무를 외부에 위탁하고 있지 않습니다.
위탁이 발생하는 경우 수탁자·위탁 업무 내용을 본 방침에 공개하고, 위탁계약 시 기술적·관리적 보호조치를 의무화합니다.` },
              { title:"6. 정보주체의 권리·의무", body:`이용자는 언제든지 다음 권리를 행사할 수 있습니다.
· 개인정보 열람(조회) 요구
· 개인정보 정정·삭제 요구
· 개인정보 처리 정지 요구
계정 설정 또는 이메일(privacy@luskacapital.com)을 통해 요청하시면 지체 없이 처리합니다.
이용자는 자신의 개인정보를 최신 상태로 유지할 책임이 있으며, 타인의 개인정보를 무단 수집·이용·제공하여서는 안 됩니다.` },
              { title:"7. 개인정보 보호책임자", body:`성명: 루스카캐피탈매니지먼트 유한책임회사
직책: 개인정보 보호책임자
이메일: privacy@luskacapital.com
주소: 서울특별시 강남구 테헤란로 521, 파르나스 타워 29층
개인정보 보호 관련 문의·불만·피해 구제는 위 연락처로 문의하시면 지체 없이 답변드립니다.` },
            ].map(({ title, body }) => (
              <div key={title} style={{ marginBottom:28 }}>
                <div style={{ fontSize:12, fontWeight:700, color:"#1D4F77", marginBottom:10, letterSpacing:"0.05em" }}>{title}</div>
                <div style={{ fontSize:12, color:"#444", lineHeight:2, whiteSpace:"pre-line" }}>{body}</div>
              </div>
            ))}
            <div style={{ borderTop:"1px solid #e5e5e5", paddingTop:20, fontSize:11, color:"#999", marginTop:8 }}>
              본 방침은 2025년 1월 1일부터 시행됩니다. 변경 시 웹사이트 공지사항을 통해 안내합니다.
            </div>
          </div>
        </div>
      )}

      {scamAlert && (
        <div style={{
          position: "fixed", inset: 0, zIndex: 1000,
          background: "rgba(0,0,0,0.92)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: isMobile ? "16px" : "40px",
        }}>
          <div style={{
            background: "#080C14", border: "1px solid #1A2332", borderRadius: 8,
            maxWidth: 560, width: "100%", padding: isMobile ? "28px 24px" : "40px 48px", color: "#E2E8F0",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#C9A84C" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span style={{ fontSize: 11, color: "#C9A84C", letterSpacing: "0.2em", fontWeight: 700 }}>
                INVESTMENT SCAM WARNING
              </span>
            </div>
            <p style={{ fontSize: 13, color: "#E2E8F0", lineHeight: 1.9, marginBottom: 16 }}>
              Luska Capital Management and Cosmos never solicit investments, offer consultations,
              or request money transfers from individual or retail investors.
            </p>
            <p style={{ fontSize: 13, color: "#94A3B8", lineHeight: 1.9, marginBottom: 28 }}>
              Scams impersonating financial companies are on the rise. If you receive any suspicious
              contact pretending to be from Cosmos or our team, please ignore it and report immediately
              to the police (112) or Financial Supervisory Service (1332).
              We are not liable for any damages caused by such impersonation scams.
            </p>
            <button onClick={() => setScamAlert(false)} style={{
              width: "100%", padding: "14px", fontSize: 12, letterSpacing: "0.05em",
              background: "#C9A84C", color: "#080C14", border: "none", borderRadius: 8,
              cursor: "pointer", fontFamily: "inherit", fontWeight: 600,
            }}>
              I understand →
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
            background: "#FFFFFF", border: "1px solid #D9E4EF",
            width: "100%", maxWidth: "100%", padding: isMobile ? "24px 20px" : "48px 80px",
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 40 }}>
              <div>
                <div style={{ fontSize: 10, color: "#1D4F77", letterSpacing: "0.2em", marginBottom: 12 }}>Cosmos BY LUSKA CAPITAL</div>
                <h2 style={{ fontSize: 22, fontWeight: 700, color: "#15213D", margin: 0 }}>
                  Get in touch to learn more about Cosmos
                </h2>
              </div>
              <button onClick={() => setModalOpen(false)} style={{
                background: "none", border: "none", color: "#5A6B85",
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
                  <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 8 }}>{field.label}</div>
                  <input
                    value={(form as any)[field.key]}
                    onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
                    style={{
                      width: "100%", padding: "8px 0", fontSize: 13,
                      background: "transparent", border: "none",
                      borderBottom: "1px solid #D9E4EF", color: "#15213D",
                      fontFamily: "inherit", outline: "none", boxSizing: "border-box",
                    }}
                  />
                </div>
              ))}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr 1fr", gap: isMobile ? 16 : 24, marginBottom: 32 }}>
              <div>
                <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 8 }}>Phone Number *</div>
                <input style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "transparent", border: "none", borderBottom: "1px solid #D9E4EF", color: "#15213D", fontFamily: "inherit", outline: "none", boxSizing: "border-box" }} />
              </div>
              <div>
                <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 8 }}>Organization Type *</div>
                <select style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "#FFFFFF", border: "none", borderBottom: "1px solid #D9E4EF", color: "#15213D", fontFamily: "inherit", outline: "none" }}>
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
                <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 8 }}>Primary Role *</div>
                <select
                  value={form.role}
                  onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
                  style={{ width: "100%", padding: "8px 0", fontSize: 13, background: "#FFFFFF", border: "none", borderBottom: "1px solid #D9E4EF", color: "#15213D", fontFamily: "inherit", outline: "none" }}>
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
              <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 16 }}>Areas of Interest (Select all that apply)</div>
              <div style={{ display: "grid", gridTemplateColumns: isMobile ? "1fr" : "1fr 1fr", gap: 10 }}>
                {INTERESTS.map(item => (
                  <label key={item} style={{ display: "flex", alignItems: "flex-start", gap: 10, cursor: "pointer" }}
                    onClick={() => toggleInterest(item)}>
                    <div style={{
                      width: 14, height: 14, flexShrink: 0, marginTop: 2,
                      border: `1px solid ${form.interests.includes(item) ? "#1D4F77" : "#D9E4EF"}`,
                      background: form.interests.includes(item) ? "#1D4F77" : "transparent",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      {form.interests.includes(item) && <span style={{ fontSize: 9, color: "#fff", fontWeight: 700 }}>✓</span>}
                    </div>
                    <span style={{ fontSize: 11, color: "#5A6B85", lineHeight: 1.5 }}>{item}</span>
                  </label>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: 32 }}>
              <div style={{ fontSize: 11, color: "#15213D", fontWeight: 700, marginBottom: 8 }}>How can we help you?</div>
              <textarea
                value={form.message}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                rows={4}
                style={{
                  width: "100%", padding: 12, fontSize: 13,
                  background: "#F4F8FC", border: "1px solid #D9E4EF",
                  color: "#15213D", fontFamily: "inherit", outline: "none",
                  resize: "vertical", boxSizing: "border-box",
                }}
              />
            </div>

            <button style={{
              padding: "14px 40px", fontSize: 11, letterSpacing: "0.15em",
              background: "#1D4F77", color: "#fff", border: "none",
              cursor: "pointer", fontFamily: "inherit", fontWeight: 700,
            }}>SUBMIT →</button>
          </div>
        </div>
      )}
    </div>
  );
}
