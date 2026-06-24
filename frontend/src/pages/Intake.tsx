import React, { useState } from "react";
import API from "../api";

const DEAL_TYPES = [
  { code: "DIRECT_LENDING", label: "직접 신규 여신" },
  { code: "DEBT_PURCHASE", label: "채권/대출채권 매입" },
  { code: "STRUCTURED_TRANCHE", label: "구조화 참여/트랜치" },
  { code: "DISTRESSED_SPECIAL", label: "부실/특수상황" },
  { code: "EQUITY_LINKED_CREDIT", label: "주식연계 신용" },
];

const POSTURES = [
  { code: "MIXED", label: "MIXED" },
  { code: "QUIET_ORIGINATION", label: "QUIET_ORIGINATION" },
  { code: "ADVERSARIAL", label: "ADVERSARIAL" },
  { code: "COOPERATIVE", label: "COOPERATIVE" },
];

const DD_TIERS = [
  { code: "SDD", label: "SDD · 스크리닝 (최소 증빙)" },
  { code: "CDD", label: "CDD · 표준 언더라이팅" },
  { code: "EDD", label: "EDD · 심화 (고위험/Control)" },
];

const SOURCE_TYPES = [
  { code: "NETWORK", label: "네트워크" },
  { code: "BROKER", label: "브로커" },
  { code: "BANK", label: "은행" },
  { code: "INBOUND", label: "인바운드" },
  { code: "DIRECT", label: "직접 소싱" },
  { code: "UNKNOWN", label: "미정" },
];

function genDealCode(): string {
  const year = new Date().getFullYear();
  const rand = Math.random().toString(36).substring(2, 8).toUpperCase();
  return `LSK-${year}-${rand}`;
}

const C = {
  bg: "#080C14", surface: "#0D1420", border: "#1A2638",
  gold: "#C9A84C", goldDim: "rgba(201,168,76,0.12)",
  text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", red: "#EF4444",
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 12px",
  background: C.bg, border: `1px solid ${C.border}`,
  borderRadius: 4, color: C.text, fontSize: 12,
  outline: "none", boxSizing: "border-box",
  fontFamily: "inherit",
};

const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
  <div>
    <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", marginBottom: 6, textTransform: "uppercase" }}>{label}</div>
    {children}
  </div>
);

export default function Intake({ onSaved }: { onSaved: () => void }) {
  const [dealCode] = useState(genDealCode());
  const [dealName, setDealName] = useState("");
  const [dealType, setDealType] = useState("DIRECT_LENDING");
  const [posture, setPosture] = useState("MIXED");
  const [ddTier, setDdTier] = useState("CDD");
  const [sourceType, setSourceType] = useState("UNKNOWN");
  const [sourceNote, setSourceNote] = useState("");
  const [maturityDate, setMaturityDate] = useState("");
  const [exposureAmount, setExposureAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const [confirming, setConfirming] = useState(false);

  const dday = (() => {
    if (!maturityDate) return null;
    const d = new Date(maturityDate);
    if (isNaN(d.getTime())) return null;
    return Math.ceil((d.getTime() - Date.now()) / 86400000);
  })();

  const dealTypeLabel = DEAL_TYPES.find(d => d.code === dealType)?.label || dealType;

  const requestRegister = () => {
    if (!dealName.trim()) { setErr("딜명을 입력하세요"); return; }
    setErr("");
    setConfirming(true);
  };

  const submit = async () => {
    setLoading(true); setErr("");
    try {
      await API.post("/api/risk-book/deals", {
        deal_code: dealCode,
        deal_name: dealName.trim(),
        deal_type: dealType,
        asset_class: "CRE",
        module_code: "CRE_SECURED_CREDIT",
        origination_posture: posture,
        dd_tier: ddTier,
        source_type: sourceType,
        source_replicability: "UNKNOWN",
        source_note: sourceNote.trim() || null,
        is_test: false,
        maturity_date: maturityDate || null,
        exposure_amount: exposureAmount ? Math.round(parseFloat(exposureAmount) * 100000000) : null,
      });
      setDone(true);
      setConfirming(false);
    } catch (e: any) {
      setErr(e.response?.data?.detail || "저장 실패");
      setConfirming(false);
    }
    setLoading(false);
  };

  if (done) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: C.bg, color: C.text, height: "100%" }}>
        <div style={{ fontSize: 10, color: C.green, letterSpacing: "0.14em", marginBottom: 12 }}>DEAL REGISTERED</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: C.text, marginBottom: 6 }}>{dealName}</div>
        <div style={{ fontSize: 11, color: C.textDim, marginBottom: 32 }}>{dealCode} · stage: INTAKE</div>
        <button onClick={onSaved}
          style={{ padding: "10px 28px", background: C.gold, color: "#000", border: "none", borderRadius: 4, fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
          Pipeline에서 확인
        </button>
      </div>
    );
  }

  if (confirming) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: C.bg, color: C.text, height: "100%" }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.14em", marginBottom: 16 }}>이렇게 대시보드를 생성하시겠습니까?</div>
        <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.gold}`, borderRadius: 4, padding: "20px 28px", marginBottom: 28, minWidth: 320 }}>
          <div style={{ fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 8 }}>{dealName}</div>
          <div style={{ fontSize: 12, color: C.textMid, marginBottom: 4 }}>{dealTypeLabel} · {ddTier}</div>
          <div style={{ fontSize: 11, color: C.textDim, fontFamily: "'IBM Plex Mono', monospace" }}>
            {dealCode}
            {exposureAmount ? ` · 익스포저 ${parseFloat(exposureAmount).toFixed(1)}억` : ""}
            {dday !== null ? ` · 만기 D-${dday}` : ""}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={() => setConfirming(false)} disabled={loading}
            style={{ padding: "10px 28px", background: "transparent", color: C.textMid, border: `1px solid ${C.border}`, borderRadius: 4, fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
            취소
          </button>
          <button onClick={submit} disabled={loading}
            style={{ padding: "10px 28px", background: loading ? C.border : C.gold, color: "#000", border: "none", borderRadius: 4, fontSize: 12, fontWeight: 700, cursor: loading ? "not-allowed" : "pointer" }}>
            {loading ? "생성 중..." : "생성하기"}
          </button>
        </div>
        {err && (
          <div style={{ fontSize: 11, color: C.red, marginTop: 16 }}>{err}</div>
        )}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: "auto", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", padding: "32px 40px" }}>
      <div style={{ maxWidth: 640, margin: "0 auto" }}>
        <div style={{ marginBottom: 32 }}>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.12em", marginBottom: 4 }}>COSMOS / DEAL INTAKE</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: C.text }}>New Deal Registration</div>
        </div>

        <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${C.gold}`, borderRadius: 4, padding: "10px 14px", marginBottom: 28 }}>
          <div style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.1em", marginBottom: 3 }}>DEAL CODE (자동 생성)</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: C.gold, letterSpacing: "0.06em" }}>{dealCode}</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <Field label="딜명 *">
            <input value={dealName} onChange={e => setDealName(e.target.value)}
              placeholder="예: 봉은사로 455 신한 선순위 크레딧"
              style={inputStyle} />
          </Field>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Field label="딜 타입 *">
              <select value={dealType} onChange={e => setDealType(e.target.value)}
                style={{ ...inputStyle, cursor: "pointer" }}>
                {DEAL_TYPES.map(d => <option key={d.code} value={d.code}>{d.label}</option>)}
              </select>
            </Field>
            <Field label="Origination Posture">
              <select value={posture} onChange={e => setPosture(e.target.value)}
                style={{ ...inputStyle, cursor: "pointer" }}>
                {POSTURES.map(p => <option key={p.code} value={p.code}>{p.label}</option>)}
              </select>
            </Field>
          </div>

          <Field label="실사 등급 (DD Tier) *">
            <select value={ddTier} onChange={e => setDdTier(e.target.value)}
              style={{ ...inputStyle, cursor: "pointer" }}>
              {DD_TIERS.map(t => <option key={t.code} value={t.code}>{t.label}</option>)}
            </select>
            <div style={{ fontSize: 10, color: C.textDim, marginTop: 6 }}>
              상위 등급일수록 체크리스트가 누적 확장됩니다 (EDD ⊇ CDD ⊇ SDD)
            </div>
          </Field>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Field label="소싱 채널">
              <select value={sourceType} onChange={e => setSourceType(e.target.value)}
                style={{ ...inputStyle, cursor: "pointer" }}>
                {SOURCE_TYPES.map(s => <option key={s.code} value={s.code}>{s.label}</option>)}
              </select>
            </Field>
            <Field label="소개자 / 출처">
              <input value={sourceNote} onChange={e => setSourceNote(e.target.value)}
                placeholder="예: 신한은행 강남지점 김XX"
                style={inputStyle} />
            </Field>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Field label="만기일">
              <input type="date" value={maturityDate} onChange={e => setMaturityDate(e.target.value)}
                style={inputStyle} />
            </Field>
            <Field label="익스포저 금액 (억원)">
              <input type="number" step="0.1" value={exposureAmount} onChange={e => setExposureAmount(e.target.value)}
                placeholder="예: 90"
                style={inputStyle} />
            </Field>
          </div>

          {err && (
            <div style={{ fontSize: 11, color: C.red, background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.2)", borderRadius: 4, padding: "8px 12px" }}>
              {err}
            </div>
          )}

          <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
            <button onClick={requestRegister}
              style={{ padding: "10px 28px", background: C.gold, color: "#000", border: "none", borderRadius: 4, fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
              Register Deal
            </button>
          </div>

          <div style={{ fontSize: 10, color: C.textDim }}>
            등록 후 Pipeline → Evidence Checklist에서 DD 항목 진행
          </div>
        </div>
      </div>
    </div>
  );
}
