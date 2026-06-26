import React, { useState } from "react";
import API from "../api";

const BTN_W = 52; // 확정 디자인: 액션 버튼 너비 고정

const STATUS_COLOR: Record<string, string> = {
  PENDING: "#525C6B", RECEIVED: "#C9A84C", VERIFIED: "#4ade80", REVIEW: "#fb7185", NA: "#3a3a3a",
};

const STALE_MS = 183 * 24 * 60 * 60 * 1000; // 6개월

// data_as_of(자동 채움 시각) → "[자동] DART 2025-12-31" + 6개월 경과 시 amber 경고
function autoMeta(it: any): { label: string; stale: boolean } | null {
  if (!it.data_source || !it.data_as_of) return null;
  const d = new Date(it.data_as_of);
  if (isNaN(d.getTime())) return null;
  const stale = Date.now() - d.getTime() > STALE_MS;
  return { label: `[자동] ${it.data_source} ${d.toISOString().slice(0, 10)}`, stale };
}

interface Props {
  items: any[];      // 현재 티어 deal_checklist_item 행
  onUpdate: () => void;
}

const actionBtn = (label: string, enabled: boolean, onClick?: () => void): React.CSSProperties => ({
  width: BTN_W, padding: "4px 0", borderRadius: 5, fontSize: 10, fontWeight: 600, textAlign: "center",
  border: `1px solid ${enabled ? "#C9A84C" : "#1e1e1e"}`,
  background: "transparent", color: enabled ? "#C9A84C" : "#444",
  cursor: enabled ? "pointer" : "not-allowed",
});

export default function SddChecklistPanel({ items, onUpdate }: Props) {
  const [open, setOpen] = useState(false);
  const done = items.filter(i => i.status === "VERIFIED" || i.status === "RECEIVED").length;

  const patch = async (item_id: number, status: string, value_text?: string) => {
    try {
      await API.patch("/deals/checklist/item", { item_id, status, value_text: value_text ?? null, file_url: null });
      onUpdate();
    } catch { /* noop */ }
  };

  const renderAction = (it: any) => {
    const completed = it.status === "VERIFIED" || it.status === "RECEIVED";
    if (completed) return <button style={actionBtn("보기", true)} onClick={() => alert(it.value_text || "완료됨")}>보기</button>;
    switch (it.item_type) {
      case "AUTO":
        return <button style={actionBtn("완료", false)} disabled>완료</button>;
      case "DOC":
        return <button style={actionBtn("업로드", true)} onClick={() => patch(it.id, "RECEIVED")}>업로드</button>;
      case "MANUAL":
        return <button style={actionBtn("입력", true)} onClick={() => { const v = window.prompt("값 입력"); if (v != null) patch(it.id, "RECEIVED", v); }}>입력</button>;
      case "RULE":
        // Phase 2: 엔진 미연결 — 계산 대기 표시만
        return <button style={actionBtn("대기", false)} disabled title="계산 엔진 연결 후 자동화 예정">대기</button>;
      default:
        return null;
    }
  };

  return (
    <div style={{ background: "#11161D", border: "1px solid #1E2630", borderRadius: 8, marginBottom: 16 }}>
      <div onClick={() => setOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 10, padding: "12px 16px", cursor: "pointer" }}>
        <span style={{ fontSize: 12, color: "#d0d0d0", fontWeight: 600 }}>SDD 체크리스트</span>
        <span style={{ fontSize: 11, color: "#8B95A3" }}>· {done}/{items.length}</span>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: 12, color: "#525C6B" }}>{open ? "▾" : "▸"}</span>
      </div>

      {open && (
        <div style={{ padding: "0 16px 12px" }}>
          {items.length === 0 ? (
            <div style={{ fontSize: 11, color: "#525C6B", padding: "8px 0" }}>항목 없음 — 템플릿 시드 대기 (Phase 2)</div>
          ) : items.map(it => {
            const meta = autoMeta(it);
            return (
            <div key={it.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 0", borderTop: "1px solid #161c24" }}>
              <span style={{ width: 7, height: 7, borderRadius: "50%", background: STATUS_COLOR[it.status] || "#525C6B", flexShrink: 0 }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <span style={{ fontSize: 12, color: "#d0d0d0" }}>{it.item_name}</span>
                {meta && (
                  <div style={{ fontSize: 9, marginTop: 2, color: meta.stale ? "#f59e0b" : "#5b6470" }}>
                    {meta.label}{meta.stale ? " · ⚠ 6개월 경과, 재확인 요구" : ""}
                    {it.value_text ? ` · ${it.value_text}` : ""}
                  </div>
                )}
              </div>
              {it.item_type === "RULE" && (
                <span style={{ fontSize: 9, color: "#fb7185", border: "1px solid rgba(251,113,133,.2)", borderRadius: 4, padding: "1px 6px" }}>엔진 미연결</span>
              )}
              <span style={{ fontSize: 9, color: "#525C6B", minWidth: 48, textAlign: "right" }}>
                {it.item_type === "RULE" && !(it.status === "VERIFIED" || it.status === "RECEIVED") ? "계산 대기" : it.status}
              </span>
              {renderAction(it)}
            </div>
          );})}
        </div>
      )}
    </div>
  );
}
