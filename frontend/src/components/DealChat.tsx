import React, { useState, useRef, useEffect } from "react";
import API from "../api";


const stripMarkdown = (text: string) =>
  text
    .replace(/#{1,6}\s+/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/_{1,2}(.+?)_{1,2}/g, "$1")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/`(.+?)`/g, "$1")
    .replace(/^[-*]\s+/gm, "")
    .replace(/^---+$/gm, "")
    .trim();

const C = {
  bg: "#080C14",
  surface: "#0D1420",
  surfaceHover: "#111827",
  border: "#1A2638",
  borderLight: "#243044",
  gold: "#C9A84C",
  goldDim: "rgba(201,168,76,0.12)",
  goldBorder: "rgba(201,168,76,0.25)",
  text: "#E2E8F0",
  textDim: "#4A6380",
  textMid: "#8BA3BE",
};

interface Msg { role: "user" | "assistant"; content: string; }

export default function DealChat({ dealId, dealName }: { dealId: string; dealName: string }) {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const userMsg: Msg = { role: "user", content: input };
    setMsgs(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    try {
      const res = await API.post(`/deals/${dealId}/chat`, { message: input, history: msgs });
      setMsgs(prev => [...prev, { role: "assistant", content: stripMarkdown(res.data.reply) }]);
    } catch {
      setMsgs(prev => [...prev, { role: "assistant", content: "API 오류. 재시도하십시오." }]);
    }
    setLoading(false);
  };

  const QUICK = [
    "현재 딜 LTV 및 안전마진 분석",
    "IC Memo 초안 작성",
    "주요 리스크 요인 열거",
    "선순위 구조화 의견",
  ];

  return (
    <div style={{
      display: "flex", flexDirection: "column", height: "100%",
      background: C.bg, fontFamily: "'Inter', 'Apple SD Gothic Neo', sans-serif",
    }}>

      {/* 헤더 */}
      <div style={{
        padding: "14px 28px", borderBottom: `1px solid ${C.border}`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: C.surface,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 28, height: 28, borderRadius: 4,
            background: C.goldDim, border: `1px solid ${C.goldBorder}`,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{ width: 8, height: 8, borderRadius: 1, background: C.gold }} />
          </div>
          <div>
            <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.12em", color: C.gold }}>COSMOS INTELLIGENCE</div>
            <div style={{ fontSize: 11, color: C.textDim, marginTop: 1 }}>{dealName}</div>
          </div>
        </div>
        <div style={{
          fontSize: 10, color: C.textDim, letterSpacing: "0.06em",
          padding: "3px 8px", border: `1px solid ${C.border}`, borderRadius: 3,
        }}>
          LUSKA CAPITAL — RESTRICTED
        </div>
      </div>

      {/* 메시지 영역 */}
      <div style={{ flex: 1, overflow: "auto", padding: "28px 28px 16px" }}>

        {msgs.length === 0 && (
          <div style={{ maxWidth: 680, margin: "0 auto" }}>
            <div style={{
              padding: "24px 28px", border: `1px solid ${C.border}`,
              borderLeft: `3px solid ${C.gold}`, background: C.surface,
              marginBottom: 28,
            }}>
              <div style={{ fontSize: 11, color: C.gold, fontWeight: 600, letterSpacing: "0.1em", marginBottom: 10 }}>
                DEAL INTELLIGENCE ACTIVE
              </div>
              <div style={{ fontSize: 13, color: C.textMid, lineHeight: 1.7 }}>
                딜 데이터를 기반으로 신용 분석, IC Memo 작성, 구조화 의견을 제공합니다.<br />
                딜 데이터가 미입력된 경우 필요 항목을 명시합니다.
              </div>
            </div>

            <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", marginBottom: 12 }}>
              QUICK QUERIES
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              {QUICK.map((q, i) => (
                <button key={i} onClick={() => { setInput(q); inputRef.current?.focus(); }}
                  style={{
                    padding: "12px 16px", background: C.surface,
                    border: `1px solid ${C.border}`, borderRadius: 4,
                    color: C.textMid, fontSize: 12, textAlign: "left", cursor: "pointer",
                    lineHeight: 1.4, transition: "border-color 0.15s",
                  }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = C.borderLight)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = C.border)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div style={{ maxWidth: 680, margin: "0 auto" }}>
          {msgs.map((m, i) => (
            <div key={i} style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 10, color: m.role === "user" ? C.gold : C.textDim,
                letterSpacing: "0.08em", fontWeight: 600, marginBottom: 6,
                textAlign: m.role === "user" ? "right" : "left",
              }}>
                {m.role === "user" ? "ANALYST" : "COSMOS"}
              </div>
              <div style={{
                padding: "14px 18px",
                background: m.role === "user" ? C.goldDim : C.surface,
                border: `1px solid ${m.role === "user" ? C.goldBorder : C.border}`,
                borderRadius: 4,
                color: C.text, fontSize: 13, lineHeight: 1.75,
                whiteSpace: "pre-wrap",
                marginLeft: m.role === "user" ? "20%" : 0,
                marginRight: m.role === "user" ? 0 : "20%",
              }}>
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", fontWeight: 600, marginBottom: 6 }}>
                COSMOS
              </div>
              <div style={{
                padding: "14px 18px", background: C.surface,
                border: `1px solid ${C.border}`, borderRadius: 4,
                color: C.textDim, fontSize: 13, marginRight: "20%",
              }}>
                <span style={{ animation: "pulse 1.5s infinite" }}>분석 중</span>
                <span style={{ color: C.gold }}> ···</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* 입력창 */}
      <div style={{ padding: "16px 28px", borderTop: `1px solid ${C.border}`, background: C.surface }}>
        <div style={{ maxWidth: 680, margin: "0 auto", display: "flex", gap: 10, alignItems: "flex-end" }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="질의 입력 (Shift+Enter: 줄바꿈)"
            rows={2}
            style={{
              flex: 1, padding: "10px 14px",
              background: C.bg, border: `1px solid ${C.border}`,
              borderRadius: 4, color: C.text, fontSize: 13,
              outline: "none", resize: "none", lineHeight: 1.6,
              fontFamily: "inherit",
            }}
          />
          <button
            onClick={send}
            disabled={loading || !input.trim()}
            style={{
              padding: "10px 22px", height: 42,
              background: input.trim() && !loading ? C.gold : "#1A2638",
              border: "none", borderRadius: 4,
              color: input.trim() && !loading ? "#000" : C.textDim,
              fontSize: 12, fontWeight: 700, letterSpacing: "0.06em",
              cursor: input.trim() && !loading ? "pointer" : "not-allowed",
              whiteSpace: "nowrap",
            }}
          >
            SEND
          </button>
        </div>
        <div style={{ maxWidth: 680, margin: "6px auto 0", fontSize: 10, color: C.textDim }}>
          Luska Capital Management — Internal Use Only
        </div>
      </div>
    </div>
  );
}
