import React, { useState } from "react";
import API from "../api";

const GOLD = "#C9A84C";

const Eye = ({ off }: { off: boolean }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#4A5568" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
    <circle cx="12" cy="12" r="3" />
    {off && <line x1="3" y1="3" x2="21" y2="21" />}
  </svg>
);

export default function Login({ onLogin }: { onLogin: (t: string) => void }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!email || !pw) { setErr("Enter email and password."); return; }
    setLoading(true); setErr("");
    try {
      const form = new URLSearchParams();
      form.append("username", email);
      form.append("password", pw);
      const res = await API.post("/token", form);
      onLogin(res.data.access_token);
    } catch {
      setErr("Invalid email or password.");
    }
    setLoading(false);
  };

  const labelRow: React.CSSProperties = { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 };
  const label: React.CSSProperties = { fontSize: 13, fontWeight: 500, color: "#94A3B8" };

  return (
    <div style={{
      minHeight: "100vh",
      background: "radial-gradient(circle at 85% 10%, rgba(201,168,76,0.12) 0%, transparent 55%), radial-gradient(circle at 15% 90%, rgba(201,168,76,0.06) 0%, transparent 40%), #050505",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: "'Inter', sans-serif", color: "#E2E8F0", padding: 24, position: "relative",
    }}>
      <style>{`
        .login-input{ width:100%; background:#141414; border:1px solid #2A2A2A; border-radius:8px; color:#E2E8F0; padding:13px 14px; font-size:14px; outline:none; box-sizing:border-box; font-family:'Inter',sans-serif; transition:border-color .15s; }
        .login-input::placeholder{ color:#4A5568; }
        .login-input:focus{ border-color:${GOLD}; }
      `}</style>

      <div style={{ width: 400, maxWidth: "100%" }}>

        {/* Logo */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 22 }}>
          {/* 흰색 로고면 invert(0) 유지 / 검은 로고를 흰색으로 보이게 하려면 invert(1) */}
          <img src="/logo.png" width={64} height={64} alt="COSMOS" style={{ filter: "invert(0)" }} />
        </div>

        {/* Heading */}
        <h1 style={{ textAlign: "center", fontSize: 26, fontWeight: 600, letterSpacing: "-0.01em", margin: 0 }}>Log in to COSMOS</h1>
        <p style={{ textAlign: "center", fontSize: 13, fontWeight: 300, color: "#64748B", margin: "8px 0 36px" }}>Luska Capital Management</p>

        {/* Email */}
        <div style={{ marginBottom: 18 }}>
          <div style={labelRow}><span style={label}>Email</span></div>
          <input
            type="email"
            className="login-input"
            placeholder="name@luskacapital.com"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onKeyDown={e => e.key === "Enter" && submit()}
          />
        </div>

        {/* Password */}
        <div style={{ marginBottom: 22 }}>
          <div style={labelRow}>
            <span style={label}>Password</span>
            <span style={{ fontSize: 12, fontWeight: 500, color: "#64748B", cursor: "pointer" }}>Forgot your password?</span>
          </div>
          <div style={{ position: "relative" }}>
            <input
              type={show ? "text" : "password"}
              className="login-input"
              placeholder="••••••••••"
              value={pw}
              onChange={e => setPw(e.target.value)}
              onKeyDown={e => e.key === "Enter" && submit()}
              style={{ paddingRight: 44 }}
            />
            <span onClick={() => setShow(s => !s)} title={show ? "Hide" : "Show"}
              style={{ position: "absolute", right: 14, top: "50%", transform: "translateY(-50%)", cursor: "pointer", display: "flex" }}>
              <Eye off={!show} />
            </span>
          </div>
        </div>

        {err && <div style={{ color: "#EF4444", fontSize: 12, marginBottom: 16 }}>{err}</div>}

        {/* Sign in */}
        <button
          onClick={submit}
          disabled={loading}
          style={{
            width: "100%", background: loading ? "#3a341f" : GOLD, color: loading ? "#8a7d52" : "#050505",
            border: "none", borderRadius: 8, padding: "13px", fontSize: 14, fontWeight: 600,
            cursor: loading ? "default" : "pointer", fontFamily: "'Inter', sans-serif", letterSpacing: "0.01em",
          }}>
          {loading ? "Authenticating…" : "Sign In"}
        </button>

        {/* Footer */}
        <div style={{ marginTop: 40, textAlign: "center", fontSize: 11, color: "#3F4756", letterSpacing: "0.03em" }}>
          Authorized access only · Luska Capital Management Internal
        </div>
      </div>
    </div>
  );
}
