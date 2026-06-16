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

  return (
    <div style={{ minHeight: "100vh", background: "#080C14", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "'IBM Plex Mono', monospace" }}>

      {/* Logo */}
      <div style={{ marginBottom: 48, textAlign: "center" }}>
        <div style={{ fontSize: 11, letterSpacing: 6, color: "#C9A84C", fontWeight: 500, marginBottom: 6 }}>COSMOS</div>
        <div style={{ fontSize: 10, letterSpacing: 3, color: "#2a2a2a" }}>LUSKA CAPITAL MANAGEMENT</div>
      </div>

      {/* Form */}
      <div style={{ width: 360 }}>
        <div style={{ marginBottom: 4, fontSize: 10, color: "#444", letterSpacing: 2 }}>EMAIL</div>
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          onKeyDown={e => e.key === "Enter" && submit()}
          style={{ width: "100%", background: "#0e1420", border: "1px solid #1a1f2e", color: "#fff", padding: "12px 14px", fontSize: 13, marginBottom: 16, outline: "none", boxSizing: "border-box" }}
        />

        <div style={{ marginBottom: 4, fontSize: 10, color: "#444", letterSpacing: 2 }}>PASSWORD</div>
        <input
          type="password"
          value={pw}
          onChange={e => setPw(e.target.value)}
          onKeyDown={e => e.key === "Enter" && submit()}
          style={{ width: "100%", background: "#0e1420", border: "1px solid #1a1f2e", color: "#fff", padding: "12px 14px", fontSize: 13, marginBottom: 24, outline: "none", boxSizing: "border-box" }}
        />

        {err && <div style={{ color: "#c0392b", fontSize: 11, marginBottom: 16 }}>{err}</div>}

        <button
          onClick={submit}
          disabled={loading}
          style={{ width: "100%", background: loading ? "#111" : "#C9A84C", color: loading ? "#444" : "#000", border: "none", padding: "13px", fontSize: 11, letterSpacing: 3, cursor: loading ? "default" : "pointer", fontFamily: "inherit", fontWeight: 600 }}
        >
          {loading ? "AUTHENTICATING..." : "SIGN IN →"}
        </button>
      </div>

      {/* Footer */}
      <div style={{ marginTop: 48, fontSize: 9, color: "#1e1e1e", letterSpacing: 1, textAlign: "center" }}>
        ● AUTHORIZED ACCESS ONLY · LUSKA CAPITAL MANAGEMENT INTERNAL
      </div>
    </div>
  );
}
