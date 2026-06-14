import React, { useState } from "react";
import API from "../api";

export default function Login({ onLogin }: { onLogin: (t: string) => void }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!email || !pw) { setErr("이메일과 비밀번호를 입력하세요"); return; }
    setLoading(true); setErr("");
    try {
      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", pw);
      const res = await API.post("/token", form);
      onLogin(res.data.access_token);
    } catch {
      setErr("이메일 또는 비밀번호가 올바르지 않습니다");
    }
    setLoading(false);
  };

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>

      {/* Left Panel */}
      <div style={{ width: "52%", background: "#0a0a0a", padding: "48px 52px", display: "flex", flexDirection: "column", justifyContent: "space-between", position: "relative", overflow: "hidden" }}>

        {/* Background circles */}
        <div style={{ position: "absolute", top: -80, right: -80, width: 320, height: 320, borderRadius: "50%", border: "0.5px solid #181818" }} />
        <div style={{ position: "absolute", top: -30, right: -30, width: 200, height: 200, borderRadius: "50%", border: "0.5px solid #1e1e1e" }} />
        <div style={{ position: "absolute", bottom: -100, left: -60, width: 280, height: 280, borderRadius: "50%", border: "0.5px solid #141414" }} />

        {/* Logo */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <img src="/luska-logo.png" alt="LuskaSeoul" style={{ height: 36, filter: "invert(1)", marginBottom: 10 }} />
          <div style={{ fontSize: 11, color: "#3a3a3a", letterSpacing: 2, fontWeight: 500 }}>COSMOS · CREDIT OPERATING SYSTEM</div>
        </div>

        {/* Center text */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ fontSize: 32, fontWeight: 600, color: "#fff", lineHeight: 1.25, letterSpacing: -0.8, marginBottom: 16 }}>
            Special Situations<br/>Deal Intelligence
          </div>
          <div style={{ fontSize: 13, color: "#555", lineHeight: 1.8, maxWidth: 320 }}>
            루스카 캐피탈 매니지먼트의 특수상황 크레딧 딜 분석<br/>및 실행 운영 플랫폼
          </div>

          <div style={{ marginTop: 32, display: "flex", gap: 8 }}>
            {["Deal Triage", "Hard Kill Analysis", "Legal Workstream", "Bank Routing"].map(tag => (
              <span key={tag} style={{ border: "0.5px solid #222", borderRadius: 4, padding: "4px 10px", fontSize: 10, color: "#444" }}>{tag}</span>
            ))}
          </div>
        </div>

        {/* Bottom */}
        <div style={{ position: "relative", zIndex: 1 }}>
          <div style={{ width: 32, height: 0.5, background: "#2a2a2a", marginBottom: 12 }} />
          <div style={{ fontSize: 10, color: "#333" }}>Luska Capital Management · Internal Only · v0.1</div>
        </div>
      </div>

      {/* Right Panel */}
      <div style={{ flex: 1, background: "#fafafa", display: "flex", alignItems: "center", justifyContent: "center", padding: "48px" }}>
        <div style={{ width: "100%", maxWidth: 360 }}>

          {/* Access badge */}
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 28 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#3B6D11" }} />
            <span style={{ fontSize: 11, color: "#888", letterSpacing: 0.3 }}>Authorized Access Only</span>
          </div>

          <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: -0.4, marginBottom: 6 }}>로그인</div>
          <div style={{ fontSize: 13, color: "#999", marginBottom: 32 }}>COSMOS 내부 접속 계정으로 로그인하세요</div>

          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 11, color: "#666", marginBottom: 6, fontWeight: 500 }}>이메일</div>
            <input
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder=""
              style={{ width: "100%", padding: "10px 14px", border: "0.5px solid #ddd", borderRadius: 8, fontSize: 13, outline: "none", background: "#fff", boxSizing: "border-box", color: "#000" }}
              onFocus={e => e.target.style.borderColor = "#999"}
              onBlur={e => e.target.style.borderColor = "#ddd"}
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: "#666", marginBottom: 6, fontWeight: 500 }}>비밀번호</div>
            <input
              type="password"
              value={pw}
              onChange={e => setPw(e.target.value)}
              onKeyDown={e => e.key === "Enter" && submit()}
              placeholder=""
              style={{ width: "100%", padding: "10px 14px", border: "0.5px solid #ddd", borderRadius: 8, fontSize: 13, outline: "none", background: "#fff", boxSizing: "border-box", color: "#000" }}
              onFocus={e => e.target.style.borderColor = "#999"}
              onBlur={e => e.target.style.borderColor = "#ddd"}
            />
          </div>

          {err && (
            <div style={{ fontSize: 12, color: "#A32D2D", marginBottom: 16, padding: "8px 12px", background: "#FCEBEB", borderRadius: 6 }}>
              {err}
            </div>
          )}

          <button
            onClick={submit}
            disabled={loading}
            style={{ width: "100%", padding: "11px", background: "#0a0a0a", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1, letterSpacing: 0.2 }}>
            {loading ? "로그인 중..." : "로그인 →"}
          </button>

          <div style={{ width: "100%", height: 0.5, background: "#eee", margin: "24px 0" }} />

          <div style={{ fontSize: 10, color: "#bbb", lineHeight: 1.7 }}>
            본 시스템은 루스카 캐피탈 매니지먼트 내부 인가 사용자 전용입니다.<br/>
            무단 접속 시도는 기록되며 법적 제재를 받을 수 있습니다.
          </div>
        </div>
      </div>
    </div>
  );
}
