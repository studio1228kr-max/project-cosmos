import { useState, useRef, useEffect } from "react";
import API from "../api";

const BG = "#111";
const PANEL = "#161616";
const BORDER = "#1e1e1e";
const TEXT = "#e2e2e2";
const TEXT_DIM = "#5a5a5a";
const GOLD = "#C9A84C";
const RED = "#A32D2D";
const GREEN = "#00C87A";

const STATUS_COLOR: Record<string, string> = {
  미확보: RED, 수령: "#F59E0B", 검증완료: GREEN, 면제: "#4499FF",
};

export default function EvidenceChecklist() {
  const [dealCode, setDealCode] = useState("");
  const [checklist, setChecklist] = useState<any[]>([]);
  const [gateResult, setGateResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const [newDeal, setNewDeal] = useState({ deal_code: "", deal_name: "", deal_type: "", asset_class: "CRE" });
  const [dealTypes, setDealTypes] = useState<any[]>([]);
  const [actionTypes, setActionTypes] = useState<string[]>([]);

  const [gc, setGc] = useState({ action_type: "", audience: "", document_type: "", confidence: "", holder: "", text: "" });
  const [gcResult, setGcResult] = useState<any>(null);

  const [users, setUsers] = useState<any[]>([]);
  const [waiveModal, setWaiveModal] = useState<any>(null);
  const [waiveForm, setWaiveForm] = useState({ reason: "", approved_by: "", expires: "" });

  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const searchTimeout = useRef<any>(null);

  const searchDeals = (q: string) => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => {
      API.get("/api/risk-book/deals/search", { params: { q } })
        .then(r => { setSuggestions(r.data.results); setShowSuggestions(true); setHighlightIndex(-1); })
        .catch(() => {});
    }, 200);
  };

  const selectSuggestion = (code: string) => {
    setDealCode(code); setShowSuggestions(false); setHighlightIndex(-1); loadChecklist(code);
  };

  const loadDealTypes = () => {
    API.get("/api/risk-book/deal-types")
      .then(r => setDealTypes(r.data))
      .catch(e => console.error("deal-types fetch failed:", e?.response?.status, e?.response?.data || e.message));
  };

  const loadActionTypes = () => {
    API.get("/api/risk-book/action-types")
      .then(r => setActionTypes(r.data.results))
      .catch(e => console.error("action-types fetch failed:", e?.response?.status, e?.response?.data || e.message));
  };

  const loadUsers = () => {
    API.get("/api/users").then(r => setUsers(r.data.results)).catch(() => {});
  };

  useEffect(() => {
    loadDealTypes();
    loadActionTypes();
    loadUsers();
  }, []);

  const loadChecklist = (code: string) => {
    setLoading(true); setErr("");
    API.get(`/api/risk-book/deals/${code}/checklist`)
      .then(r => { setChecklist(r.data.checklist); setDealCode(code); setLoading(false); })
      .catch(e => { setErr(e?.response?.data?.detail || "조회 실패"); setLoading(false); });
  };

  const updateStatus = (item: any, status: string) => {
    if (status === "면제") {
      setWaiveModal(item);
      setWaiveForm({ reason: "", approved_by: "", expires: "" });
      return;
    }
    API.patch(`/api/risk-book/deals/${dealCode}/checklist/${item.evidence_item_code}`, { status })
      .then(() => loadChecklist(dealCode));
  };

  const confirmWaive = () => {
    if (!waiveModal || !waiveForm.reason || !waiveForm.approved_by || !waiveForm.expires) return;
    API.patch(`/api/risk-book/deals/${dealCode}/checklist/${waiveModal.evidence_item_code}`, {
      status: "면제", waiver_reason: waiveForm.reason, waived_by: waiveForm.approved_by, waiver_expires_at: waiveForm.expires,
    }).then(() => { setWaiveModal(null); loadChecklist(dealCode); });
  };

  const createDeal = () => {
    if (!newDeal.deal_code || !newDeal.deal_name || !newDeal.deal_type) return;
    API.post("/api/risk-book/deals", { ...newDeal, is_test: false })
      .then(r => { loadChecklist(r.data.deal_code); })
      .catch(e => setErr(e?.response?.data?.detail || "등록 실패"));
  };

  const runGateCheck = () => {
    if (!dealCode || !gc.action_type) return;
    API.post("/api/risk-book/gate-check", { deal_code: dealCode, ...gc })
      .then(r => setGcResult(r.data))
      .catch(e => setGcResult({ result: "ERROR", note: e?.response?.data?.detail }));
  };

  return (
    <div style={{ flex: 1, overflow: "auto", background: BG, color: TEXT, padding: 24, fontFamily: "'ZenSerif', 'Inter', sans-serif" }}>
      <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>증빙 체크리스트 & 게이트 점검</div>
      <div style={{ fontSize: 11, color: TEXT_DIM, marginBottom: 20 }}>딜 코드 입력 후 조회 → 체크리스트 확인 → 게이트 점검</div>

      {/* 딜 조회 / 신규등록 */}
      <div style={{ display: "flex", gap: 16, marginBottom: 20 }}>
        <div style={{ background: PANEL, border: `1px solid ${BORDER}`, padding: 16, flex: 1 }}>
          <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 8, letterSpacing: "0.1em" }}>딜 조회</div>
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <input
                value={dealCode}
                onChange={e => { setDealCode(e.target.value); searchDeals(e.target.value); }}
                onFocus={() => searchDeals(dealCode)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                onKeyDown={e => {
                  if (showSuggestions && suggestions.length > 0) {
                    if (e.key === "ArrowDown") { e.preventDefault(); setHighlightIndex(i => (i + 1) % suggestions.length); return; }
                    if (e.key === "ArrowUp") { e.preventDefault(); setHighlightIndex(i => (i - 1 + suggestions.length) % suggestions.length); return; }
                    if (e.key === "Escape") { setShowSuggestions(false); return; }
                    if (e.key === "Enter" && highlightIndex >= 0 && highlightIndex < suggestions.length) {
                      e.preventDefault(); selectSuggestion(suggestions[highlightIndex].deal_code); return;
                    }
                  }
                  if (e.key === "Enter") { setShowSuggestions(false); loadChecklist(dealCode); }
                }}
                placeholder="deal_code (예: LSK-2026-7003EE)"
                style={{ width: "100%", boxSizing: "border-box", background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }} />
              {showSuggestions && suggestions.length > 0 && (
                <div style={{ position: "absolute", top: "100%", left: 0, right: 0, background: "#0d0d0d", border: `1px solid ${BORDER}`, zIndex: 10, maxHeight: 240, overflowY: "auto" }}>
                  {suggestions.map((s: any, idx: number) => (
                    <div key={s.deal_code}
                      onMouseDown={() => selectSuggestion(s.deal_code)}
                      onMouseEnter={() => setHighlightIndex(idx)}
                      style={{ padding: "8px 10px", fontSize: 12, cursor: "pointer", borderBottom: `1px solid ${BORDER}`, background: idx === highlightIndex ? "#1a1a1a" : "transparent" }}>
                      <span style={{ color: GOLD }}>{s.deal_code}</span>
                      <span style={{ color: TEXT_DIM, marginLeft: 8 }}>{s.deal_name}{s.stage ? ` · ${s.stage}` : ""}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <button onClick={() => { setShowSuggestions(false); loadChecklist(dealCode); }} style={{ background: "transparent", border: `1px solid ${GOLD}`, color: GOLD, padding: "6px 14px", fontSize: 11, cursor: "pointer" }}>조회</button>
          </div>
        </div>

        <div style={{ background: PANEL, border: `1px solid ${BORDER}`, padding: 16, flex: 1 }}>
          <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 8, letterSpacing: "0.1em" }}>신규 딜 등록</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            <input value={newDeal.deal_code} onChange={e => setNewDeal({ ...newDeal, deal_code: e.target.value })} placeholder="deal_code"
              style={{ flex: 1, minWidth: 100, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }} />
            <input value={newDeal.deal_name} onChange={e => setNewDeal({ ...newDeal, deal_name: e.target.value })} placeholder="deal_name"
              style={{ flex: 1, minWidth: 100, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }} />
            <select value={newDeal.deal_type} onChange={e => setNewDeal({ ...newDeal, deal_type: e.target.value })} onFocus={loadDealTypes}
              style={{ background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }}>
              <option value="">딜 유형 선택</option>
              {dealTypes.map((dt: any) => <option key={dt.deal_type_code} value={dt.deal_type_code}>{dt.deal_type_code}</option>)}
            </select>
            <button onClick={createDeal} style={{ background: "transparent", border: `1px solid ${GREEN}`, color: GREEN, padding: "6px 14px", fontSize: 11, cursor: "pointer" }}>등록</button>
          </div>
        </div>
      </div>

      {err && <div style={{ color: RED, fontSize: 12, marginBottom: 12 }}>{err}</div>}
      {loading && <div style={{ color: TEXT_DIM, fontSize: 12 }}>로딩중...</div>}

      {checklist.length > 0 && (
        <div style={{ background: PANEL, border: `1px solid ${BORDER}`, marginBottom: 20 }}>
          <div style={{ padding: "10px 16px", borderBottom: `1px solid ${BORDER}`, fontSize: 11, letterSpacing: "0.1em", color: TEXT_DIM }}>
            {dealCode} — 체크리스트 ({checklist.length})
          </div>
          {checklist.map((item: any) => (
            <div key={item.evidence_item_code} style={{ padding: "8px 16px", borderBottom: `1px solid #161616` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12 }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: STATUS_COLOR[item.status] || TEXT_DIM, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{item.evidence_item_label || item.evidence_item_code}</span>
                <span style={{ fontSize: 10, color: TEXT_DIM }}>{item.requirement_level}</span>
                <select value={item.status} onChange={e => updateStatus(item, e.target.value)}
                  style={{ background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, fontSize: 11, padding: "3px 6px" }}>
                  <option value="미확보">미확보</option>
                  <option value="수령">수령</option>
                  <option value="검증완료">검증완료</option>
                  <option value="면제">면제</option>
                </select>
              </div>
              {item.status === "면제" && (
                <div style={{ fontSize: 10, color: TEXT_DIM, marginTop: 4, paddingLeft: 18 }}>
                  승인: {item.waived_by || "-"} · 처리: {item.performed_by || "-"} · 만료: {item.waiver_expires_at || "-"}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {waiveModal && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50 }}>
          <div style={{ background: PANEL, border: `1px solid ${BORDER}`, padding: 20, width: 360 }}>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12 }}>면제 — {waiveModal.evidence_item_label || waiveModal.evidence_item_code}</div>
            <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 4 }}>Waiver 사유</div>
            <input value={waiveForm.reason} onChange={e => setWaiveForm({ ...waiveForm, reason: e.target.value })}
              style={{ width: "100%", boxSizing: "border-box", background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12, marginBottom: 10 }} />
            <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 4 }}>승인자</div>
            <select value={waiveForm.approved_by} onChange={e => setWaiveForm({ ...waiveForm, approved_by: e.target.value })}
              style={{ width: "100%", boxSizing: "border-box", background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12, marginBottom: 10 }}>
              <option value="">승인자 선택</option>
              {users.map((u: any) => <option key={u.email} value={u.email}>{u.email} ({u.role})</option>)}
            </select>
            <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 4 }}>만료일</div>
            <input type="date" value={waiveForm.expires} onChange={e => setWaiveForm({ ...waiveForm, expires: e.target.value })}
              style={{ width: "100%", boxSizing: "border-box", background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12, marginBottom: 14 }} />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={() => setWaiveModal(null)} style={{ background: "transparent", border: `1px solid ${BORDER}`, color: TEXT_DIM, padding: "6px 14px", fontSize: 11, cursor: "pointer" }}>취소</button>
              <button onClick={confirmWaive} style={{ background: "transparent", border: `1px solid ${GOLD}`, color: GOLD, padding: "6px 14px", fontSize: 11, cursor: "pointer" }}>확정</button>
            </div>
          </div>
        </div>
      )}

      {dealCode && (
        <div style={{ background: PANEL, border: `1px solid ${BORDER}`, padding: 16 }}>
          <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 10, letterSpacing: "0.1em" }}>게이트 점검 — {dealCode}</div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
            <select value={gc.action_type} onChange={e => setGc({ ...gc, action_type: e.target.value })} onFocus={loadActionTypes}
              style={{ flex: 1, minWidth: 160, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }}>
              <option value="">액션 유형 선택</option>
              {actionTypes.map((a: string) => <option key={a} value={a}>{a}</option>)}
            </select>
            <select value={gc.audience} onChange={e => setGc({ ...gc, audience: e.target.value })}
              style={{ flex: 1, minWidth: 100, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }}>
              <option value="">대상 선택</option>
              <option value="내부">내부</option>
              <option value="SECURITIES_PI">SECURITIES_PI</option>
              <option value="BANK">BANK</option>
              <option value="LEGAL">LEGAL</option>
            </select>
            <select value={gc.confidence} onChange={e => setGc({ ...gc, confidence: e.target.value })}
              style={{ flex: 1, minWidth: 100, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }}>
              <option value="">신뢰도 선택</option>
              <option value="낮음">낮음</option>
              <option value="중간">중간</option>
              <option value="높음">높음</option>
            </select>
            <select value={gc.holder} onChange={e => setGc({ ...gc, holder: e.target.value })}
              style={{ flex: 1, minWidth: 120, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }}>
              <option value="">보유자 선택</option>
              <option value="제3자">제3자</option>
              <option value="LUSKA_SPC">LUSKA_SPC</option>
            </select>
            <input value={gc.text} onChange={e => setGc({ ...gc, text: e.target.value })} placeholder="검증할 문장"
              style={{ flex: 2, minWidth: 200, background: "#0d0d0d", border: `1px solid ${BORDER}`, color: TEXT, padding: "6px 10px", fontSize: 12 }} />
            <button onClick={runGateCheck} style={{ background: "transparent", border: `1px solid ${GOLD}`, color: GOLD, padding: "6px 14px", fontSize: 11, cursor: "pointer" }}>게이트 체크 실행</button>
          </div>
          {gcResult && (
            <div style={{ borderTop: `1px solid ${BORDER}`, paddingTop: 10, fontSize: 12 }}>
              <div style={{ fontWeight: 700, color: gcResult.result === "BLOCK" ? RED : gcResult.result === "허용" ? GREEN : "#F59E0B", marginBottom: 6 }}>
                {gcResult.result}
              </div>
              {gcResult.gate && <div style={{ color: TEXT_DIM }}>GATE: {gcResult.gate.status} — {gcResult.gate.note}</div>}
              {gcResult.financial && <div style={{ color: TEXT_DIM }}>FIN: {gcResult.financial.note}</div>}
              {gcResult.control && <div style={{ color: TEXT_DIM }}>CTRL: {gcResult.control.note}</div>}
              {gcResult.conditions?.length > 0 && (
                <ul style={{ marginTop: 6, paddingLeft: 18 }}>
                  {gcResult.conditions.map((c: string, i: number) => <li key={i} style={{ color: "#F59E0B" }}>{c}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
