import React, { useState } from "react";
import Login from "./Login";

export default function Landing() {
  const [showLogin, setShowLogin] = useState(false);

  if (showLogin) return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={e => { if (e.target === e.currentTarget) setShowLogin(false); }}>
      <div style={{ position: "relative", width: 880, maxHeight: "90vh", borderRadius: 16, overflow: "hidden", boxShadow: "0 40px 80px rgba(0,0,0,0.5)" }}>
      <button onClick={() => setShowLogin(false)} style={{ position: "absolute", top: 16, right: 16, zIndex: 10, background: "rgba(0,0,0,0.5)", border: "none", color: "#fff", width: 28, height: 28, borderRadius: "50%", cursor: "pointer", fontSize: 16, display: "flex", alignItems: "center", justifyContent: "center" }}>×</button>
        <Login onLogin={t => { localStorage.setItem("token", t); window.location.reload(); }} />
      </div>
    </div>
  );

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif", background: "#0a0a0a", color: "#fff", minHeight: "100vh" }}>

      {/* Top Nav */}
      <nav style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, background: "#0a0a0a", borderBottom: "0.5px solid #1a1a1a", padding: "0 48px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 32 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <img src="/luska-logo.png" alt="Luska" style={{ height: 22, filter: "invert(1)", objectFit: "contain" }} />
            <span style={{ fontSize: 11, color: "#444", letterSpacing: 1 }}>COSMOS</span>
          </div>
          <div style={{ display: "flex", gap: 28 }}>
            {["플랫폼", "주요 기능", "회사 소개"].map(item => (
              <span key={item} style={{ fontSize: 13, color: "#666", cursor: "pointer" }}>{item}</span>
            ))}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button onClick={() => setShowLogin(true)}
            style={{ padding: "7px 20px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontSize: 13, fontWeight: 600, cursor: "pointer", letterSpacing: 0.2 }}>
            Connect →
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <section style={{ paddingTop: 56, minHeight: "100vh", display: "flex", alignItems: "center" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", padding: "80px 48px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80, alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 11, color: "#555", letterSpacing: 2, marginBottom: 20, fontWeight: 500 }}>루스카 캐피탈 매니지먼트®</div>
            <h1 style={{ fontSize: 52, fontWeight: 700, lineHeight: 1.15, letterSpacing: -1.5, margin: "0 0 24px" }}>
              COSMOS:<br/>딜 판단의<br/>운영 언어
            </h1>
            <p style={{ fontSize: 15, color: "#888", lineHeight: 1.8, marginBottom: 16, maxWidth: 480 }}>
              특수상황 크레딧 딜을 위한 새로운 운영 기술 시대에 오신 것을 환영합니다.
            </p>
            <p style={{ fontSize: 14, color: "#666", lineHeight: 1.8, marginBottom: 16, maxWidth: 480 }}>
              오늘날 기관 투자자는 개별 딜 단위의 감(感)이 아니라, 증거·리스크·회수 가능성을 한 화면에서 통합해 보는 체계를 필요로 합니다.
            </p>
            <p style={{ fontSize: 14, color: "#555", lineHeight: 1.8, marginBottom: 40, maxWidth: 480 }}>
              COSMOS 플랫폼과 이를 사용하는 크레딧 팀은 이러한 목표를 달성하고, 더 통제된 딜 운영 문화를 가능하게 합니다.
            </p>
            <button onClick={() => setShowLogin(true)}
              style={{ padding: "12px 28px", background: "none", color: "#fff", border: "1px solid #333", borderRadius: 6, fontSize: 14, cursor: "pointer", letterSpacing: 0.3 }}>
              Connect →
            </button>
          </div>

          {/* Hero Visual - Logo based */}
          <div style={{ position: "relative", height: 520, display: "flex", alignItems: "center", justifyContent: "center" }}>
            {/* Globe background */}
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", overflow: "hidden", borderRadius: 16 }}>
              <img src="/globe.webp" alt="" style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.6, filter: "brightness(0.5) contrast(1.2)" }} />
              <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at center, transparent 30%, #0a0a0a 80%)" }} />
            </div>

            {/* Center logo */}
            <div style={{ position: "relative", zIndex: 2, textAlign: "center" }}>
              <div style={{ width: 120, height: 120, borderRadius: "50%", background: "#111", border: "0.5px solid #2a2a2a", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 24px" }}>
                <img src="/luska-logo.png" alt="Luska" style={{ width: 72, height: 36, objectFit: "contain", filter: "invert(1)", opacity: 0.85 }} />
              </div>
              <div style={{ fontSize: 13, color: "#444", letterSpacing: 3, marginBottom: 8 }}>COSMOS</div>
              <div style={{ fontSize: 11, color: "#333", letterSpacing: 1 }}>by Luska Capital Management</div>

              {/* Floating badges */}
              {[
                { top: -160, left: -120, text: "Hard Kill Analysis", sub: "6-axis screening" },
                { top: -160, right: -120, text: "Evidence Gate", sub: "Document control" },
                { top: 80, left: -140, text: "Recovery Path", sub: "Scenario mapping" },
                { top: 80, right: -140, text: "Bank Routing", sub: "Credit box fit" },
              ].map((b, i) => (
                <div key={i} style={{ position: "absolute", ...b, background: "#0f0f0f", border: "0.5px solid #222", borderRadius: 8, padding: "10px 14px", whiteSpace: "nowrap", textAlign: "left" }}>
                  <div style={{ fontSize: 11, color: "#888", fontWeight: 500 }}>{b.text}</div>
                  <div style={{ fontSize: 9, color: "#444", marginTop: 2 }}>{b.sub}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 전체 딜 운영 */}
      <section style={{ borderTop: "0.5px solid #1a1a1a", padding: "80px 48px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <h2 style={{ fontSize: 32, fontWeight: 600, letterSpacing: -0.8, marginBottom: 20 }}>전체 딜 운영 그림</h2>
          <p style={{ fontSize: 15, color: "#666", lineHeight: 1.9, maxWidth: 720, marginBottom: 16 }}>
            COSMOS는 공통 데이터 언어를 통해 딜 판단 프로세스를 통합하는 운영 플랫폼입니다. 딜 인입부터 Hard Kill, Control Point, Evidence, Recovery Path까지를 하나의 Deal ID 아래에서 연결해, 사람에 따라 달라지지 않는 기준과 기록을 남기도록 설계되었습니다.
          </p>
          <p style={{ fontSize: 14, color: "#555", lineHeight: 1.9, maxWidth: 720 }}>
            COSMOS 위에서 팀은 개별 딜 메모를 넘어, 파이프라인 전체의 상태·리스크·회수 경로를 한눈에 파악할 수 있고, 시간이 지날수록 운영 노하우가 데이터로 축적되는 구조를 갖게 됩니다.
          </p>
        </div>
      </section>

      {/* 주요 이점 */}
      <section style={{ background: "#060606", borderTop: "0.5px solid #1a1a1a", padding: "80px 48px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <div style={{ display: "inline-block", background: "#8B7340", padding: "10px 20px", marginBottom: 60 }}>
            <span style={{ fontSize: 14, fontWeight: 600 }}>주요 이점</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 60 }}>
            {[
              {
                n: "01",
                title: "딜 판단의 언어를 통일하세요.",
                body: "COSMOS는 Hard Kill, Control, Evidence, Recovery Path라는 네 개의 축을 중심으로 딜을 정의합니다. Intake, 법률 의견, 실사 결과, 은행 협의 내용과 IC 결론이 모두 이 언어 위에 쌓이기 때문에, 누구든 동일한 기준으로 딜을 읽고 토론할 수 있습니다."
              },
              {
                n: "02",
                title: "딜 운영 생태계가 한 흐름으로 이어집니다.",
                body: "COSMOS는 루스카 내부 팀뿐 아니라, 법무법인, 평가사, 은행 등 외부 파트너와의 커뮤니케이션을 하나의 Deal Record 흐름 안에 고정하는 것을 목표로 합니다. 메신저·메일·파일 서버에 흩어져 있던 결정적 증거와 논의가 Deal ID에 귀속되면서, 사후적으로도 판단의 근거를 추적할 수 있습니다."
              },
              {
                n: "03",
                title: "시장과 딜 속도의 변화에 맞춰 설계되었습니다.",
                body: "특수상황 크레딧 딜은 타임라인이 촉박하고, 정보 비대칭이 큽니다. COSMOS는 Evidence Gate, Hard Kill 트리거, Recovery Path 시나리오를 미리 코드화해 두어, 새로운 딜이 들어올 때마다 같은 루틴으로 빠르게 걸러내고, 집중해야 할 딜에만 시간을 쓰도록 설계되어 있습니다."
              }
            ].map(({ n, title, body }) => (
              <div key={n}>
                <div style={{ fontSize: 56, fontWeight: 800, color: "#1e1e1e", marginBottom: 16, lineHeight: 1 }}>{n}<span style={{ color: "#8B7340" }}>.</span></div>
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 14, lineHeight: 1.4 }}>{title}</div>
                <div style={{ fontSize: 13, color: "#666", lineHeight: 1.9 }}>{body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* COSMOS 기술 */}
      <section style={{ borderTop: "0.5px solid #1a1a1a", padding: "80px 48px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <h2 style={{ fontSize: 24, fontWeight: 600, marginBottom: 48, color: "#888" }}>COSMOS 기술</h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 80 }}>
            {[
              {
                icon: "⬛",
                title: "안정적인 기반.",
                body: "COSMOS는 루스카 캐피탈 매니지먼트의 실제 딜 케이스와 체크리스트를 토대로 설계된 내부 운영 OS입니다. 목표는 화려한 UI가 아니라, Gate 규칙과 기록이 절대 흐트러지지 않는 안정적인 워크플로우 엔진입니다.",
                link: "더 알아보기"
              },
              {
                icon: "◎",
                title: "개방형 확장.",
                body: "COSMOS는 향후 은행별 크레딧 박스, 시장 데이터, 경매·임대료 통계 등 외부 데이터를 단계적으로 연결할 수 있도록 설계되어 있습니다. 내부 팀은 COSMOS 위에서 IC 메모 자동 생성, 포트폴리오 리스크 뷰 등 기능을 계속 얹어가며 루스카 고유의 딜 운영 문화를 소프트웨어로 고정해 나갑니다.",
                link: "로드맵 살펴보기"
              }
            ].map(({ icon, title, body, link }) => (
              <div key={title} style={{ display: "flex", gap: 24 }}>
                <div style={{ fontSize: 28, color: "#185FA5", flexShrink: 0, marginTop: 4 }}>{icon}</div>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 12 }}>{title}</div>
                  <div style={{ fontSize: 13, color: "#666", lineHeight: 1.9, marginBottom: 16 }}>{body}</div>
                  <div style={{ fontSize: 12, color: "#555", cursor: "pointer" }}>› {link}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: "0.5px solid #1a1a1a", padding: "32px 48px" }}>
        <div style={{ maxWidth: 1200, margin: "0 auto", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <img src="/luska-logo.png" alt="Luska" style={{ height: 18, filter: "invert(1)", opacity: 0.4, marginBottom: 12 }} />
            <div style={{ fontSize: 11, color: "#333", lineHeight: 1.8, maxWidth: 600 }}>
              본 플랫폼은 루스카 캐피탈 매니지먼트 내부 인가 사용자 전용입니다. 본 시스템의 분석 결과는 투자 자문이 아니며, 최종 투자 판단의 책임은 사용자에게 있습니다. 무단 접속 시도는 기록되며 법적 제재를 받을 수 있습니다.
            </div>
          </div>
          <button onClick={() => setShowLogin(true)}
            style={{ padding: "8px 20px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer", whiteSpace: "nowrap" }}>
            Connect →
          </button>
        </div>
        <div style={{ maxWidth: 1200, margin: "20px auto 0", paddingTop: 20, borderTop: "0.5px solid #1a1a1a", fontSize: 11, color: "#333" }}>
          ©2026 Luska Capital Management. All rights reserved. COSMOS는 루스카 캐피탈 매니지먼트의 내부 운영 플랫폼입니다.
        </div>
      </footer>
    </div>
  );
}
