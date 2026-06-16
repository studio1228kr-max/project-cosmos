import React, { useState } from "react";
import API from "../api";

const EVIDENCE_ITEMS = [
  { id: "registry", label: "등기부등본", desc: "담보순위·가압류·신탁 구조 확인" },
  { id: "building", label: "건축물대장", desc: "불법증축·용도·면적 확인" },
  { id: "claim", label: "채권잔액확인서", desc: "실제 잔액·이자율·만기 확인" },
  { id: "tax", label: "국세/지방세 완납증명서", desc: "세금 우선권 체크" },
  { id: "lease", label: "임대차현황", desc: "DSCR 계산용 임차인 정보" },
  { id: "appraisal", label: "감정평가서 또는 공시지가", desc: "LTV 계산" },
];

export default function Intake({ onSaved }: { onSaved: () => void }) {
  const [source, setSource] = useState("");
  const [raw, setRaw] = useState("");
  const [evidence, setEvidence] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState("");

  const toggleEvidence = (id: string) => {
    setEvidence(prev => prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]);
  };

  const coverage = evidence.length;
  const analysisLevel = coverage === 0 ? "Intake Only" : coverage <= 2 ? "Triage" : coverage <= 4 ? "Triage+" : "Underwriting";
  const levelColor = coverage === 0 ? "#888" : coverage <= 2 ? "#854F0B" : coverage <= 4 ? "#185FA5" : "#3B6D11";

  const analyze = async () => {
    if (!source || !raw) { setErr("소개자와 딜 설명을 입력하세요"); return; }
    setLoading(true); setErr("");
    try {
      const res = await API.post("/deals/analyze", { source, raw_input: raw });
      setResult(res.data);
    } catch (e: any) {
      setErr(e.response?.data?.detail || "분석 실패");
    }
    setLoading(false);
  };

  const hkColor = (v: string) => {
    const l = (v||"").toLowerCase();
    if (l.includes("critical")) return "#A32D2D";
    if (l.includes("unknown")) return "#854F0B";
    return "#888";
  };

  return (
    <div style={{ padding: "28px 36px", maxWidth: 860, fontFamily: "-apple-system, BlinkMacSystemFont, sans-serif" }}>
      <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: -0.3, marginBottom: 4 }}>Deal Intake</div>
      <div style={{ fontSize: 12, color: "#999", marginBottom: 28 }}>딜 정보 입력 → COSMOS Triage → Pipeline 저장</div>

      {/* Evidence Gate */}
      <div style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 10, padding: "16px 20px", marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div style={{ fontSize: 12, fontWeight: 600 }}>Evidence Gate</div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 11, color: "#999" }}>Coverage {coverage}/6</span>
            <span style={{ fontSize: 11, fontWeight: 600, color: levelColor, background: levelColor+"18", padding: "2px 10px", borderRadius: 10 }}>
              {analysisLevel}
            </span>
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {EVIDENCE_ITEMS.map(item => (
            <div key={item.id} onClick={() => toggleEvidence(item.id)}
              style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 12px", borderRadius: 7, border: evidence.includes(item.id) ? "0.5px solid #3B6D11" : "0.5px solid #eee", background: evidence.includes(item.id) ? "#EAF3DE" : "#FAFAFA", cursor: "pointer" }}>
              <div style={{ width: 16, height: 16, borderRadius: 4, border: evidence.includes(item.id) ? "none" : "1.5px solid #ddd", background: evidence.includes(item.id) ? "#3B6D11" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {evidence.includes(item.id) && <span style={{ color: "#fff", fontSize: 10, fontWeight: 700 }}>✓</span>}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 500, color: evidence.includes(item.id) ? "#3B6D11" : "#333" }}>{item.label}</div>
                <div style={{ fontSize: 10, color: "#999", marginTop: 1 }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
        {coverage < 6 && (
          <div style={{ marginTop: 10, fontSize: 11, color: "#854F0B", background: "#FAEEDA", borderRadius: 6, padding: "6px 10px" }}>
            ⚠ Underwriting 분석은 6개 문서 충족 시 가능합니다. 현재 Run Triage만 활성화됩니다.
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        <div>
          <div style={{ fontSize: 11, color: "#666", marginBottom: 5, fontWeight: 500 }}>소개자 / 출처</div>
          <input value={source} onChange={e => setSource(e.target.value)}
            placeholder="예: 신한은행 강남지점 / 브로커 김XX"
            style={{ width: "100%", padding: "9px 12px", border: "0.5px solid #ddd", borderRadius: 8, fontSize: 13, outline: "none", boxSizing: "border-box" }} />
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: "#666", marginBottom: 5, fontWeight: 500 }}>딜 설명</div>
        <textarea value={raw} onChange={e => setRaw(e.target.value)}
          placeholder="카톡, 이메일, 브로커 메시지 그대로 붙여넣기..."
          style={{ width: "100%", height: 140, padding: "10px 12px", border: "0.5px solid #ddd", borderRadius: 8, fontSize: 13, outline: "none", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }} />
      </div>

      {err && <div style={{ fontSize: 12, color: "#A32D2D", background: "#FCEBEB", padding: "8px 12px", borderRadius: 6, marginBottom: 12 }}>{err}</div>}

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={analyze} disabled={loading}
          style={{ padding: "10px 24px", background: "#000", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.6 : 1 }}>
          {loading ? "Triage 실행 중..." : "Run Triage"}
        </button>
        <button disabled
          style={{ padding: "10px 24px", background: "#f5f5f5", color: "#ccc", border: "0.5px solid #eee", borderRadius: 8, fontSize: 13, cursor: "not-allowed" }}>
          Run Underwriting
        </button>
      </div>

      {/* Result */}
      {result && (
        <div style={{ marginTop: 32 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Triage 결과 — {result.deal_id}</div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 16 }}>
            {[["자산명", result.record.asset_name], ["채권자", result.record.creditor], ["잔액", result.record.current_balance], ["DSCR", result.record.dscr]].map(([label, val]:any) => (
              <div key={label} style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontSize: 10, color: "#999", marginBottom: 3 }}>{label}</div>
                <div style={{ fontSize: 12, fontWeight: 500 }}>{val || "Unknown"}</div>
              </div>
            ))}
          </div>

          {/* Verdict */}
          {result.record.luska_verdict && (
            <div style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderLeft: "3px solid #111", borderRadius: "0 8px 8px 0", padding: "12px 14px", marginBottom: 16 }}>
              <div style={{ fontSize: 10, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 5 }}>◈ LUSKA VERDICT</div>
              <div style={{ fontSize: 12, color: "#222", lineHeight: 1.6 }}>{result.record.luska_verdict}</div>
              {result.record.next_action && <div style={{ fontSize: 11, color: "#3B6D11", marginTop: 6 }}>→ {result.record.next_action}</div>}
            </div>
          )}

          {/* Hard Kill */}
          <div style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 8, padding: "14px 16px", marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 10 }}>Hard Kill 판정</div>
            {Object.entries(result.record.hard_kill || {}).map(([k, v]: any) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "0.5px solid #f5f5f5", fontSize: 12 }}>
                <span style={{ color: "#666" }}>{k}</span>
                <span style={{ color: hkColor(v), fontWeight: 500, maxWidth: 400, textAlign: "right" }}>{v}</span>
              </div>
            ))}
          </div>

          {(result.record.missing_data || []).length > 0 && (
            <div style={{ background: "#FAEEDA", border: "0.5px solid #FAC775", borderRadius: 8, padding: "12px 14px", marginBottom: 16 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: "#854F0B", marginBottom: 6 }}>Missing Data ({result.record.missing_data.length}개)</div>
              {result.record.missing_data.map((m: string) => <div key={m} style={{ fontSize: 11, color: "#854F0B" }}>⚠ {m}</div>)}
            </div>
          )}

          <div style={{ fontSize: 12, color: "#666", marginBottom: 16 }}>
            Analysis Level: <strong style={{ color: levelColor }}>{analysisLevel}</strong> · 
            MinData: <strong style={{ color: result.record.minimum_data_passed ? "#3B6D11" : "#A32D2D" }}>
              {result.record.minimum_data_score}/8 {result.record.minimum_data_passed ? "Pass ✓" : "Fail ✗"}
            </strong> · 
            상태: <strong>{result.status}</strong>
          </div>

          <button onClick={onSaved}
            style={{ padding: "10px 24px", background: "#000", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: "pointer" }}>
            Pipeline에서 확인
          </button>
        </div>
      )}
    </div>
  );
}
