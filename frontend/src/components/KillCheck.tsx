import React, { useState, useEffect } from "react";
import API from "../api";

// ── 질문 정의 ─────────────────────────────────────────────────
interface Question { id: string; text: string; killLabel: string; isThesisKey?: boolean; }

const COMMON_QUESTIONS: Question[] = [
  { id: "q1", text: "정보 제공 의사?", killLabel: "정보 제공 거부" },
  { id: "q2", text: "IRR 구조 가능?", killLabel: "IRR 달성 불가" },
  { id: "q3", text: "양도 가능?", killLabel: "양도 불가" },
  { id: "q4", text: "규제 위반 없음?", killLabel: "규제 위반 가능성" },
];

const TYPE_QUESTIONS: Record<string, Question[]> = {
  DIRECT_LENDING: [
    { id: "dl1", text: "법인 존속 확인?", killLabel: "법인 폐업/휴업" },
    { id: "dl2", text: "상환 재원 존재?", killLabel: "상환 재원 전무" },
    { id: "dl3", text: "자금 목적 설명 가능?", killLabel: "자금 목적 불명" },
  ],
  DEBT_PURCHASE: [
    { id: "dp1", text: "채권 원인 설명 가능?", killLabel: "채권 원인 불명" },
    { id: "dp2", text: "매도자 채권 연결?", killLabel: "채권 연결 불가" },
    { id: "dp3", text: "담보 존재 확인?", killLabel: "담보 미확인", isThesisKey: true },
  ],
  STRUCTURED_TRANCHE: [
    { id: "st1", text: "트랜치 순위 확인?", killLabel: "트랜치 순위 불가" },
    { id: "st2", text: "워터폴 구조 존재?", killLabel: "워터폴 없음+후순위" },
    { id: "st3", text: "Cashflow 원천 설명?", killLabel: "Cashflow 설명 불가" },
  ],
  DISTRESSED_SPECIAL: [
    { id: "ds1", text: "채권 존재 확인?", killLabel: "채권 존재 불가" },
    { id: "ds2", text: "파산 종결 아님?", killLabel: "파산 종결+배당 완료" },
    { id: "ds3", text: "회수 경로 존재?", killLabel: "회수 경로 전무", isThesisKey: true },
  ],
  EQUITY_LINKED_CREDIT: [
    { id: "el1", text: "전환조건 존재?", killLabel: "전환조건 전무" },
    { id: "el2", text: "Refixing Floor 있음?", killLabel: "Refixing Floor 없음" },
    { id: "el3", text: "하방 보호 존재?", killLabel: "하방 보호 전무", isThesisKey: true },
  ],
};

const COLORS = {
  bg: "#0d0d0d", border: "#1e1e1e", gold: "#C9A84C",
  text: "#d0d0d0", muted: "#555", dim: "#3a3a3a",
  green: "#4ade80", red: "#fb7185",
};

export interface KillCheckProps {
  dealId: number;
  dealCode: string;
  thesis: string;
  thesisType?: string;
  dealType: string;
  declaredKillCriteria: string[];
  onPass: (dealCode: string) => void;
  onDrop: () => void;
  onClose: () => void;
}

export default function KillCheck({ dealId, dealCode, thesis, dealType, declaredKillCriteria, onPass, onDrop, onClose }: KillCheckProps) {
  const declaredQs: Question[] = declaredKillCriteria.map((c, i) => ({ id: `decl_${i}`, text: `${c} — 해당 없음?`, killLabel: c }));
  const typeQs = TYPE_QUESTIONS[dealType] || [];

  const sections: { title: string; tag: string; qs: Question[] }[] = [
    { title: "공통 점검", tag: "Blue Owl", qs: COMMON_QUESTIONS },
    ...(declaredQs.length ? [{ title: "등록 시 선언 Kill", tag: "Oaktree", qs: declaredQs }] : []),
    { title: "Thesis 핵심 점검", tag: "Ares", qs: typeQs },
  ];
  const allQs = sections.flatMap(s => s.qs);

  const [answers, setAnswers] = useState<Record<string, "y" | "n">>({});
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [sec, setSec] = useState(0);

  // 타이머 (Apollo: 5분 목표 count-up)
  useEffect(() => {
    const t = setInterval(() => setSec(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const mmss = `${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}`;

  const answer = (id: string, yn: "y" | "n") => setAnswers(p => ({ ...p, [id]: yn }));

  const drops = allQs.filter(q => answers[q.id] === "n").map(q => q.killLabel);
  const canPass = drops.length === 0;

  const submit = async (result: "PASS" | "DROP") => {
    setLoading(true); setErr("");
    try {
      await API.post("/deals/kill-check", { deal_id: dealId, result, drop_reasons: drops });
      if (result === "PASS") onPass(dealCode); else onDrop();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "처리 실패");
      setLoading(false);
    }
  };

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", zIndex: 60, display: "flex", alignItems: "center", justifyContent: "center" }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{ width: 480, maxWidth: "90vw", maxHeight: "88vh", display: "flex", flexDirection: "column", background: COLORS.bg, border: `0.5px solid ${COLORS.border}`, borderRadius: 14, overflow: "hidden", color: COLORS.text, fontFamily: "Inter, sans-serif" }}>
        {/* Nav */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "16px 20px", borderBottom: `1px solid ${COLORS.border}` }}>
          <button onClick={onClose} style={{ background: "transparent", border: "none", color: COLORS.muted, fontSize: 16, cursor: "pointer" }}>←</button>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.1em", color: COLORS.red }}>KILL CHECK</div>
          <div style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: COLORS.muted, fontFamily: "monospace" }}>⏱ {mmss} / 05:00</span>
          <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 10, border: `1px solid ${canPass ? "rgba(74,222,128,.3)" : "rgba(251,113,133,.3)"}`, color: canPass ? COLORS.green : COLORS.red }}>
            {canPass ? "CLEAR" : `DROP ${drops.length}`}
          </span>
        </div>

        {/* Thesis strip (Oaktree) */}
        <div style={{ padding: "10px 20px", borderBottom: `1px solid ${COLORS.border}`, background: "rgba(201,168,76,0.04)" }}>
          <div style={{ fontSize: 9, color: COLORS.muted, letterSpacing: "0.1em", marginBottom: 3 }}>{dealCode} · 선언 THESIS</div>
          <div style={{ fontSize: 12, color: COLORS.text, lineHeight: 1.5 }}>{thesis || "—"}</div>
        </div>

        {/* QA list */}
        <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>
          {sections.map(s => (
            <div key={s.title} style={{ marginBottom: 18 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                <span style={{ fontSize: 10, color: COLORS.muted, letterSpacing: "0.08em", textTransform: "uppercase" }}>{s.title}</span>
                <span style={{ fontSize: 9, color: COLORS.dim }}>{s.tag}</span>
              </div>
              {s.qs.map(q => {
                const a = answers[q.id];
                return (
                  <div key={q.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0" }}>
                    <span style={{ flex: 1, fontSize: 13, color: q.isThesisKey ? COLORS.red : COLORS.text }}>
                      {q.isThesisKey && "★ "}{q.text}
                    </span>
                    <button onClick={() => answer(q.id, "y")} style={ynStyle(a === "y", "y")}>Y</button>
                    <button onClick={() => answer(q.id, "n")} style={ynStyle(a === "n", "n")}>N</button>
                  </div>
                );
              })}
            </div>
          ))}
        </div>

        {/* Drop warn */}
        {drops.length > 0 && (
          <div style={{ padding: "10px 20px", borderTop: `1px solid ${COLORS.border}`, background: "rgba(251,113,133,0.06)" }}>
            <div style={{ fontSize: 11, color: COLORS.red }}>⚠ Drop 사유 {drops.length}건: {drops.join(" · ")}</div>
          </div>
        )}

        {/* CTA */}
        <div style={{ padding: "14px 20px", borderTop: `1px solid ${COLORS.border}`, display: "flex", gap: 10 }}>
          {err && <div style={{ fontSize: 11, color: COLORS.red, alignSelf: "center" }}>{err}</div>}
          <button disabled={!canPass || loading} onClick={() => submit("PASS")} style={{
            flex: 1, padding: "12px", borderRadius: 8, border: "none", fontSize: 13, fontWeight: 700,
            background: canPass && !loading ? COLORS.gold : COLORS.border,
            color: canPass && !loading ? "#000" : COLORS.muted,
            cursor: canPass && !loading ? "pointer" : "not-allowed",
          }}>{loading ? "처리 중..." : "Kill 없음 — SDD 시작 →"}</button>
          <button disabled={loading} onClick={() => submit("DROP")} style={{
            padding: "12px 18px", borderRadius: 8, border: `1px solid ${COLORS.red}`, background: "transparent",
            color: COLORS.red, fontSize: 13, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
          }}>Drop</button>
        </div>
      </div>
    </div>
  );
}

const ynStyle = (active: boolean, kind: "y" | "n"): React.CSSProperties => {
  const base: React.CSSProperties = { padding: "5px 12px", borderRadius: 6, fontSize: 11, fontWeight: 700, cursor: "pointer", border: "0.5px solid #1a1a1a", background: "transparent", color: "#555" };
  if (!active) return base;
  if (kind === "y") return { ...base, borderColor: "rgba(74,222,128,.3)", color: "#4ade80", background: "rgba(74,222,128,.06)" };
  return { ...base, borderColor: "rgba(251,113,133,.3)", color: "#fb7185", background: "rgba(251,113,133,.06)" };
};
