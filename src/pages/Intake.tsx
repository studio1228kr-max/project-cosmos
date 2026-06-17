import React, { useState } from "react";
import API from "../api";

type Props = {
  onSaved: () => void;
};

const FIELD_LABELS: Record<string, string> = {
  asset_name: "자산명",
  asset_address: "주소",
  creditor: "채권자",
  borrower: "차주",
  owner: "소유자",
  lien_rank: "담보순위",
  maturity: "만기",
  delinquency_status: "연체 상태",
  ltv: "LTV",
  dscr: "DSCR",
  current_balance: "채권잔액",
};

const EMPTY = {
  asset_name: "",
  asset_address: "",
  creditor: "",
  borrower: "",
  owner: "",
  lien_rank: "",
  maturity: "",
  delinquency_status: "",
  ltv: "",
  dscr: "",
  current_balance: "",
};

export default function Intake({ onSaved }: Props) {
  const [form, setForm] = useState({ ...EMPTY });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const set = (key: string, value: string) => setForm(f => ({ ...f, [key]: value }));

  const submit = async () => {
    if (!form.asset_name) {
      setError("자산명은 필수입니다.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await API.post("/deals", {
        deal_name: form.asset_name,
        status: "INTAKE",
        deal_record: { ...form },
      });
      setForm({ ...EMPTY });
      onSaved();
    } catch (e) {
      setError("저장 중 오류가 발생했습니다.");
    }
    setSaving(false);
  };

  const inp: React.CSSProperties = {
    width: "100%", boxSizing: "border-box", background: "#1a1a1a",
    border: "1px solid #2a2a2a", borderRadius: 6, padding: "8px 10px",
    fontSize: 13, color: "#e2e2e2", outline: "none",
    fontFamily: "'ZenSerif', 'Inter', sans-serif",
  };
  const lbl: React.CSSProperties = {
    fontSize: 11, color: "#6a6a6a", marginBottom: 4, display: "block",
  };

  return (
    <div style={{ maxWidth: 640, margin: "0 auto", padding: 32 }}>
      <div style={{ fontSize: 16, fontWeight: 600, color: "#e2e2e2", marginBottom: 4 }}>New Deal Intake</div>
      <div style={{ fontSize: 12, color: "#555", marginBottom: 24 }}>새 딜 정보를 입력하세요.</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        {Object.keys(EMPTY).map(key => (
          <div key={key} style={key === "asset_address" ? { gridColumn: "1 / -1" } : undefined}>
            <label style={lbl}>{FIELD_LABELS[key]}</label>
            <input
              style={inp}
              value={(form as any)[key]}
              onChange={e => set(key, e.target.value)}
            />
          </div>
        ))}
      </div>

      {error && <div style={{ fontSize: 12, color: "#e5534b", marginTop: 16 }}>{error}</div>}

      <button onClick={submit} disabled={saving}
        style={{
          marginTop: 24, padding: "9px 20px", background: "#C9A84C", color: "#111",
          border: "none", borderRadius: 6, fontSize: 13, fontWeight: 600,
          cursor: "pointer", fontFamily: "'ZenSerif', 'Inter', sans-serif",
        }}>
        {saving ? "저장 중..." : "딜 등록"}
      </button>
    </div>
  );
}
