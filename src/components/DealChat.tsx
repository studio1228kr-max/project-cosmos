import React, { useState, useRef, useEffect } from "react";
import API from "../api";

const C = {
  bg: "#080C14", surface: "#0D1420", border: "#1A2638",
  gold: "#C9A84C", text: "#E2E8F0", textDim: "#5A7190",
};

interface Msg { role: "user"|"assistant"; content: string; }

export default function DealChat({ dealId, dealName }: { dealId: string; dealName: string }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { role: "user", content: input };
    setMsgs(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await API.post(`/deals/${dealId}/chat`, {
        message: input,
        history: msgs
      });
      setMsgs(prev => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch {
      setMsgs(prev => [...prev, { role: "assistant", content: "오류가 발생했습니다." }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", background: C.bg, fontFamily: "Inter, sans-serif" }}>
      {/* 헤더 */}
      <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.gold }} />
        <span style={{ fontSize: 11, color: C.gold, fontWeight: 600, letterSpacing: "0.08em" }}>LUSKA AI</span>
        <span style={{ fontSize: 11, color: C.textDim, marginLeft: 4 }}>— {dealName}</span>
      </div>

      {/* 메시지 영역 */}
      <div style={{ flex: 1, overflow: "auto", padding: "16px" }}>
        {msgs.length === 0 && (
          <div style={{ color: C.textDim, fontSize: 12, textAlign: "center", marginTop: 40 }}>
            딜에 대해 자유롭게 질문하세요.<br/>
            <span style={{ fontSize: 11, opacity: 0.6 }}>IC Memo 작성, 리스크 분석, 구조화 의견</span>
          </div>
        )}
        {msgs.map((m, i) => (
          <div key={i} style={{ marginBottom: 16, display: "flex", flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
            <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4 }}>
              {m.role === "user" ? "나" : "LUSKA AI"}
            </div>
            <div style={{
              maxWidth: "80%", padding: "10px 14px", borderRadius: m.role === "user" ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
              background: m.role === "user" ? "rgba(201,168,76,0.15)" : C.surface,
              border: `1px solid ${m.role === "user" ? "rgba(201,168,76,0.3)" : C.border}`,
              color: C.text, fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap"
            }}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ display: "flex", alignItems: "flex-start", marginBottom: 16 }}>
            <div style={{ padding: "10px 14px", borderRadius: "12px 12px 12px 2px", background: C.surface, border: `1px solid ${C.border}`, color: C.textDim, fontSize: 13 }}>
              분석 중...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력창 */}
      <div style={{ padding: "12px 16px", borderTop: `1px solid ${C.border}`, display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="딜에 대해 질문하세요..."
          style={{ flex: 1, padding: "8px 12px", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 13, outline: "none" }}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{ padding: "8px 16px", background: input.trim() && !loading ? C.gold : "#333", border: "none", borderRadius: 6, color: "#000", fontSize: 13, fontWeight: 600, cursor: input.trim() && !loading ? "pointer" : "not-allowed" }}
        >전송</button>
      </div>
    </div>
  );
}
