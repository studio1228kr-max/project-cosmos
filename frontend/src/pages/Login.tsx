import React, { useState } from "react";
import API from "../api";

export default function Login({ onLogin }: { onLogin: (t: string) => void }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
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

  const label: React.CSSProperties = { marginBottom: 6, fontSize: 10, color: "#4A5568", letterSpacing: "0.1em" };

  return (
    <div style={{ minHeight: "100vh", background: "#080C14", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "'Outfit', sans-serif" }}>
      <style>{`
        .login-input{ width:100%; background:#0D1421; border:1px solid #1A2332; color:#E2E8F0; padding:12px 14px; font-size:13px; outline:none; box-sizing:border-box; font-family:'Outfit',sans-serif; transition:border-color .15s; }
        .login-input::placeholder{ color:#4A5568; }
        .login-input:focus{ border-color:#C9A84C; }
      `}</style>

      {/* Logo */}
      <div style={{ marginBottom: 48, textAlign: "center" }}>
        <div style={{ fontSize: 11, letterSpacing: 6, color: "#C9A84C", fontWeight: 600, marginBottom: 6 }}>COSMOS</div>
        <div style={{ fontSize: 10, letterSpacing: 3, color: "#4A5568" }}>LUSKA CAPITAL MANAGEMENT</div>
      </div>

      {/* Form */}
      <div style={{ width: 360 }}>
        <div style={label}>EMAIL</div>
        <input
          type="email"
          className="login-input"
          placeholder="name@luskacapital.com"
          value={email}
          onChange={e => setEmail(e.target.value)}
          onKeyDown={e => e.key === "Enter" && submit()}
          style={{ marginBottom: 16 }}
        />

        <div style={label}>PASSWORD</div>
        <input
          type="password"
          className="login-input"
          placeholder="••••••••"
          value={pw}
          onChange={e => setPw(e.target.value)}
          onKeyDown={e => e.key === "Enter" && submit()}
          style={{ marginBottom: 24 }}
        />

        {err && <div style={{ color: "#EF4444", fontSize: 11, marginBottom: 16 }}>{err}</div>}

        <button
          onClick={submit}
          disabled={loading}
          style={{ width: "100%", background: loading ? "#111" : "#C9A84C", color: loading ? "#444" : "#000", border: "none", padding: "13px", fontSize: 11, letterSpacing: 3, cursor: loading ? "default" : "pointer", fontFamily: "'Outfit', sans-serif", fontWeight: 600 }}
        >
          {loading ? "AUTHENTICATING..." : "SIGN IN →"}
        </button>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 48, fontSize: 9, color: "#4A5568", letterSpacing: 1, textAlign: "center" }}>
        ● AUTHORIZED ACCESS ONLY · LUSKA CAPITAL MANAGEMENT INTERNAL
      </div>
    </div>
  );
}
