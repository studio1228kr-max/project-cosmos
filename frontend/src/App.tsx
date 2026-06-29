import React, { useState, useEffect, useRef } from "react";
import Spinner from "./components/Spinner";
import Login from "./pages/Login";
import Landing from "./pages/Landing";
import DealIntake, { RegisteredDeal } from "./pages/DealIntake";
import KillCheck from "./components/KillCheck";
import API from "./api";
import Layout from "./Layout";
import Pipeline from "./pages/Pipeline";
import MarketScan from "./pages/MarketScan";
import SignalRoom from "./pages/SignalRoom";
import RiskBook from "./pages/RiskBook";
import EvidenceChecklist from "./pages/EvidenceChecklist";
import CreditDesk from "./pages/CreditDesk";
import DealExecution from "./pages/DealExecution";
import ClosingPage from "./pages/ClosingPage";
import PortfolioPage from "./pages/PortfolioPage";
import FundAccountingPage from "./pages/FundAccountingPage";
import LPRelationsPage from "./pages/LPRelationsPage";
import RiskCompliancePage from "./pages/RiskCompliancePage";
import SourcingPage from "./pages/SourcingPage";

const STATUS_COLOR: any = { INTAKE: "#888", SCREENED: "#185FA5", WATCHLIST: "#854F0B", ADVANCE: "#3B6D11", REJECT: "#A32D2D" };
const STATUS_BG: any = { INTAKE: "#F1EFE8", SCREENED: "#E6F1FB", WATCHLIST: "#FAEEDA", ADVANCE: "#EAF3DE", REJECT: "#FCEBEB" };
const STATUSES = ["INTAKE","SCREENED","WATCHLIST","ADVANCE","REJECT"];
const HK_LABELS: any = { tax_risk:"국세/지방세", tenant_risk:"임차인", possessory_lien:"유치권", trust_structure:"신탁구조", litigation:"소송", building_violation:"건축위반" };

const Icon = ({ d, size=18 }: { d: string; size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round">
    <path d={d}/>
  </svg>
);

const ICONS: any = {
  pipeline: "M2 2h6v6H2zM10 2h6v6h-6zM2 10h6v6H2zM10 10h6v6h-6z",
  intake: "M9 2v14M2 9h14",
  legal: "M4 2h10a1 1 0 011 1v12a1 1 0 01-1 1H4a1 1 0 01-1-1V3a1 1 0 011-1zM6 6h6M6 9h6M6 12h4",
  evidence: "M9 2a7 7 0 100 14A7 7 0 009 2zM9 6v3l2 2",
  bank: "M2 7l7-5 7 5M4 8v6M9 8v6M14 8v6M2 14h14",
  ic: "M9 2a4 4 0 100 8 4 4 0 000-8zM3 16c0-3.3 2.7-6 6-6s6 2.7 6 6",
  logout: "M11 2h4a1 1 0 011 1v12a1 1 0 01-1 1h-4M7 13l-4-4 4-4M3 9h9",
};


// ============================================================
// EVIDENCE PANEL
// ============================================================
const DOC_LABELS: Record<string, string> = {
  registry: "등기사항증명서",
  building_ledger: "건물대장",
  debt_balance: "채권잔액확인서",
  tax_clearance: "납세완납증명서",
  lease_status: "임대차현황",
  appraisal: "감정평가서",
};
const STATUS_BADGE: Record<string, {bg: string; color: string; label: string}> = {
  CONFIRMED: { bg: "#EAF3DE", color: "#3B6D11", label: "확보" },
  MISSING: { bg: "#FFF1F0", color: "#F5222D", label: "미확보" },
  UNVERIFIABLE: { bg: "#F5F5F5", color: "#888", label: "확인불가" },
};

function EvidencePanel({ dealId }: { dealId: string }) {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<string|null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    API.get(`/deals/${dealId}/evidence`).then(r => { setItems(r.data); setLoading(false); });
  };
  useEffect(() => { load(); }, [dealId]);

  const update = async (docType: string, status: string) => {
    setSaving(true);
    await API.post(`/deals/${dealId}/evidence`, {
      doc_type: docType, doc_status: status, note: editing === docType ? note : "", uploaded_by: "GP"
    });
    setEditing(null);
    setNote("");
    setSaving(false);
    load();
  };

  if (loading) return <Spinner filter="none" style={{ padding: 24 }} />;

  const confirmed = items.filter(i => i.doc_status === "CONFIRMED").length;

  return (
    <div style={{ padding: 20 }}>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600 }}>Evidence Gate</div>
          <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{confirmed}/6 문서 확보</div>
        </div>
        <div style={{ padding: "4px 12px", borderRadius: 20, fontSize: 11, fontWeight: 600,
          background: confirmed >= 6 ? "#EAF3DE" : confirmed > 0 ? "#FFFBE6" : "#FFF1F0",
          color: confirmed >= 6 ? "#3B6D11" : confirmed > 0 ? "#854F0B" : "#F5222D" }}>
          {confirmed >= 6 ? "READY" : confirmed > 0 ? "PARTIAL" : "MISSING"}
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {items.map((item: any) => {
          const badge = STATUS_BADGE[item.doc_status] || STATUS_BADGE.MISSING;
          return (
            <div key={item.doc_type} style={{ background: "#FAFAFA", border: "1px solid #eee", borderRadius: 8, padding: "12px 14px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: editing === item.doc_type ? 10 : 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{DOC_LABELS[item.doc_type] || item.doc_type}</span>
                  <span style={{ fontSize: 10, padding: "1px 8px", borderRadius: 10, background: badge.bg, color: badge.color, fontWeight: 600 }}>{badge.label}</span>
                </div>
                <div style={{ display: "flex", gap: 4 }}>
                  <button onClick={() => update(item.doc_type, "CONFIRMED")} disabled={saving}
                    style={{ padding: "3px 10px", fontSize: 10, border: "1px solid #3B6D11", borderRadius: 6, background: item.doc_status==="CONFIRMED"?"#EAF3DE":"#fff", color: "#3B6D11", cursor: "pointer" }}>확보</button>
                  <button onClick={() => update(item.doc_type, "MISSING")} disabled={saving}
                    style={{ padding: "3px 10px", fontSize: 10, border: "1px solid #F5222D", borderRadius: 6, background: item.doc_status==="MISSING"?"#FFF1F0":"#fff", color: "#F5222D", cursor: "pointer" }}>미확보</button>
                  <button onClick={() => { setEditing(editing===item.doc_type?null:item.doc_type); setNote(item.note||""); }}
                    style={{ padding: "3px 10px", fontSize: 10, border: "1px solid #ddd", borderRadius: 6, background: "#fff", color: "#888", cursor: "pointer" }}>메모</button>
                </div>
              </div>
              {editing === item.doc_type && (
                <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
                  <input value={note} onChange={e => setNote(e.target.value)} placeholder="메모 입력..."
                    style={{ flex: 1, padding: "5px 10px", fontSize: 11, border: "1px solid #ddd", borderRadius: 6, outline: "none" }} />
                  <button onClick={() => update(item.doc_type, item.doc_status)} disabled={saving}
                    style={{ padding: "5px 12px", fontSize: 11, background: "#000", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>저장</button>
                </div>
              )}
              {item.note && editing !== item.doc_type && (
                <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>📝 {item.note}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DealPanel({ dealId, onClose }: { dealId: string; onClose: () => void }) {
  const [deal, setDeal] = useState<any>(null);
  const [tab, setTab] = useState("record");
  const [status, setStatus] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [showMemo, setShowMemo] = useState(false);
  const [memo, setMemo] = useState("");
  const [generating, setGenerating] = useState(false);

  const generateMemo = async () => {
    setGenerating(true);
    setMemo("");
    try {
      const res = await API.post(`/deals/${dealId}/ic_memo`);
      setMemo(res.data.memo || "생성 실패");
    } catch(e) {
      setMemo("생성 중 오류가 발생했습니다.");
    }
    setGenerating(false);
  };

  useEffect(() => {
    setTab("record");
    setShowMemo(false);
    setMemo("");
    API.get(`/deals/${dealId}`).then(r => { setDeal(r.data); setStatus(r.data.status); });
  }, [dealId]);

  if (!deal) return <Spinner filter="none" style={{ padding: 32 }} />;

  if (showMemo) {
    if (!generating && !memo) generateMemo();
    return (
      <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
        onClick={e => { if (e.target === e.currentTarget) setShowMemo(false); }}>
        <div style={{ background: "#fff", borderRadius: 12, width: 680, maxHeight: "85vh", display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 24px 60px rgba(0,0,0,0.3)" }}>
          <div style={{ padding: "20px 28px 16px", borderBottom: "0.5px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
            <div>
              <div style={{ fontSize: 10, color: "#bbb", letterSpacing: 0.5, marginBottom: 2 }}>◈ LUSKA CAPITAL MANAGEMENT</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>IC Memo Draft</div>
              <div style={{ fontSize: 11, color: "#888", marginTop: 2 }}>{deal?.deal_record?.asset_name}</div>
            </div>
            <button onClick={() => setShowMemo(false)} style={{ background: "none", border: "none", fontSize: 20, color: "#bbb", cursor: "pointer" }}>×</button>
          </div>
          <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
            {generating ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "center", paddingTop: 60 }}>
                <Spinner filter="none" label="IC Memo 생성 중" />
                <div style={{ fontSize: 11, color: "#bbb" }}>루스카 Canon 기준 적용 중</div>
              </div>
            ) : (
              <div style={{ fontSize: 13, color: "#222", lineHeight: 1.9 }}>
                {memo.split("\n").filter((l:string) => l.trim()).map((line:string, i:number) => (
                  <p key={i} style={{ margin: line.startsWith("[") ? "16px 0 4px" : "0 0 6px", fontWeight: line.startsWith("[") ? 600 : 400, color: line.startsWith("[") ? "#000" : "#333" }}>{line}</p>
                ))}
              </div>
            )}
          </div>
          {!generating && memo && (
            <div style={{ padding: "14px 28px", borderTop: "0.5px solid #eee", display: "flex", gap: 8, flexShrink: 0 }}>
              <button onClick={() => navigator.clipboard.writeText(memo)}
                style={{ flex: 1, padding: "9px", background: "#f5f5f5", color: "#333", border: "0.5px solid #ddd", borderRadius: 7, fontSize: 12, cursor: "pointer" }}>
                복사
              </button>
              <button onClick={() => setShowMemo(false)}
                style={{ padding: "9px 20px", background: "#000", color: "#fff", border: "none", borderRadius: 7, fontSize: 12, cursor: "pointer" }}>
                닫기
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }
  const rec = deal.deal_record || {};
  const hk = rec.hard_kill || {};
  const criticalCount = Object.values(hk).filter((v: any) => (v||"").toLowerCase().includes("critical")).length;
  const unknownCount = Object.values(hk).filter((v: any) => (v||"").toLowerCase().includes("unknown")).length;

  const hkColor = (v: string) => {
    const l = (v||"").toLowerCase();
    if (l.includes("critical")) return { c: "#A32D2D", bg: "#FCEBEB", label: "RED" };
    if (l.includes("unknown")) return { c: "#854F0B", bg: "#FAEEDA", label: "AMBER" };
    if (l.includes("clear") || l === "green") return { c: "#3B6D11", bg: "#EAF3DE", label: "GREEN" };
    return { c: "#888", bg: "#F5F5F5", label: "TBC" };
  };

  const saveStatus = async () => {
    if (!reason) { setMsg("Reason 필수"); return; }
    setSaving(true);
    await API.patch(`/deals/${dealId}/status`, { status, reason, action_tag: "", next_action: "" });
    const r = await API.get(`/deals/${dealId}`);
    setDeal(r.data); setMsg("완료"); setSaving(false);
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", overflow: "hidden", background: "#FAFAF8" }}>
      <div style={{ padding: "16px 20px 0", background: "#fff", borderBottom: "0.5px solid #eee", flexShrink: 0 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
          <div>
            <div style={{ fontSize: 9, color: "#bbb", fontFamily: "monospace", marginBottom: 2 }}>{deal.id}</div>
            <div style={{ fontSize: 18, fontWeight: 600, letterSpacing: -0.3 }}>{rec.asset_name || "—"}</div>
            <div style={{ fontSize: 11, color: "#888", marginTop: 1 }}>{rec.asset_address}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ background: STATUS_BG[deal.status], color: STATUS_COLOR[deal.status], padding: "2px 8px", borderRadius: 20, fontSize: 11, fontWeight: 600 }}>{deal.status}</span>
            {(deal.status === "SCREENED" || deal.status === "ADVANCE") && (
              <button onClick={() => setShowMemo(true)}
                style={{ padding: "3px 10px", background: "#000", color: "#fff", border: "none", borderRadius: 6, fontSize: 10, fontWeight: 500, cursor: "pointer" }}>
                IC Memo →
              </button>
            )}
            <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "#bbb", fontSize: 16, lineHeight: 1, padding: "2px 4px" }}>×</button>
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 6, marginBottom: 12 }}>
          {[
            ["DSCR", (rec.dscr||"—").split("(")[0].trim().slice(0,8), false],
            ["채권잔액", rec.current_balance||"—", false],
            ["Hard Kill", `${criticalCount}RED / ${unknownCount}AMB`, criticalCount>0],
            ["Missing", `${(rec.missing_data||[]).length}개`, (rec.missing_data||[]).length>0]
          ].map(([l,v,alert]:any) => (
            <div key={l} style={{ background: alert?"#FFF8F0":"#F7F7F5", borderRadius: 6, padding: "6px 8px", border: alert?"0.5px solid #FAC775":"0.5px solid transparent" }}>
              <div style={{ fontSize: 10, color: "#999", marginBottom: 2 }}>{l}</div>
              <div style={{ fontSize: 13, fontWeight: 600, color: alert?"#854F0B":"#000" }}>{v}</div>
            </div>
          ))}
        </div>

        <div style={{ display: "flex" }}>
          {[["record","레코드"],["evidence","Evidence"],["hardkill","Hard Kill"],["recovery","Recovery"],["diligence","Diligence"],["status","상태"],["history","이력"],["contact","컨택로그"]].map(([t,label]) => (
            <div key={t} onClick={() => setTab(t)} style={{ padding: "8px 14px", fontSize: 12, cursor: "pointer", borderBottom: tab===t?"2px solid #000":"2px solid transparent", fontWeight: tab===t?600:400, color: tab===t?"#000":"#999" }}>{label}</div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, overflow: "auto", padding: "14px 20px" }}>
        {rec.luska_verdict && (
          <div style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderLeft: "3px solid #111", borderRadius: "0 7px 7px 0", padding: "10px 12px", marginBottom: 14 }}>
            <div style={{ fontSize: 10, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 6 }}>◈ LUSKA VERDICT</div>
            <div style={{ fontSize: 12, color: "#222", lineHeight: 1.7 }}>{rec.luska_verdict}</div>
            {rec.next_action && <div style={{ fontSize: 11, color: "#3B6D11", marginTop: 6 }}>→ {rec.next_action}</div>}
            {rec.initial_routing && <div style={{ fontSize: 11, color: "#185FA5", marginTop: 4 }}>↝ {rec.initial_routing}</div>}
          </div>
        )}

        {tab === "record" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <div>
              <div style={{ fontSize: 9, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 8 }}>기본 정보</div>
              {[["채권자","creditor"],["차주","borrower"],["소유자","owner"],["담보순위","lien_rank"],["만기","maturity"],["연체","delinquency_status"],["LTV","ltv"]].map(([label,key]:any) => (
                <div key={key} style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "0.5px solid #f0f0f0", fontSize: 12 }}>
                  <span style={{ color: "#888" }}>{label}</span>
                  <span style={{ fontWeight: 500, color: rec[key]?.toLowerCase?.().startsWith("unknown")?"#ccc":"#000", maxWidth: 160, textAlign: "right" }}>{rec[key]||"—"}</span>
                </div>
              ))}
            </div>
            <div>
              <div style={{ fontSize: 9, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 8 }}>Control & Evidence</div>
              <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>Control Lever</div>
              <div style={{ fontSize: 11, background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 6, padding: "7px 9px", marginBottom: 12, lineHeight: 1.5 }}>{rec.control_lever||"Unknown"}</div>
              {(rec.evidence_gaps||[]).length > 0 && <>
                <div style={{ fontSize: 10, color: "#666", marginBottom: 5 }}>Evidence Gaps</div>
                {rec.evidence_gaps.map((g:string,i:number) => <div key={i} style={{ fontSize: 10, color: "#854F0B", padding: "2px 0" }}>⚠ {g}</div>)}
              </>}
            </div>
          </div>
        )}

        {tab === "evidence" && <EvidencePanel dealId={dealId} />}

        {tab === "hardkill" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
              {Object.entries(hk).map(([k,v]:any) => {
                const { c, bg, label } = hkColor(v);
                return (
                  <div key={k} style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 8, padding: "10px 12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 600 }}>{HK_LABELS[k]||k}</span>
                      <span style={{ fontSize: 8, fontWeight: 700, color: c, background: bg, padding: "2px 6px", borderRadius: 8 }}>{label}</span>
                    </div>
                    <div style={{ fontSize: 11, color: "#666", lineHeight: 1.6 }}>{v}</div>
                  </div>
                );
              })}
            </div>
            {(rec.missing_data||[]).length > 0 && (
              <div style={{ background: "#FAEEDA", border: "0.5px solid #FAC775", borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "#854F0B", marginBottom: 6 }}>Missing Data ({rec.missing_data.length}개)</div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3 }}>
                  {rec.missing_data.map((m:string) => <div key={m} style={{ fontSize: 10, color: "#854F0B" }}>⚠ {m}</div>)}
                </div>
              </div>
            )}
          </div>
        )}

        {tab === "recovery" && (
          <div>
            {(rec.recovery_paths||[]).length === 0 ? <div style={{ color: "#bbb", fontSize: 12 }}>없음</div> :
              rec.recovery_paths.map((p:string,i:number) => (
                <div key={i} style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 8, padding: "10px 12px", marginBottom: 7, display: "flex", gap: 10 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#e0e0e0", minWidth: 22 }}>0{i+1}</div>
                  <div style={{ fontSize: 11, color: "#333", lineHeight: 1.6 }}>{p}</div>
                </div>
              ))
            }
          </div>
        )}

        {tab === "diligence" && (
          <div>
            <div style={{ fontSize: 10, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 12 }}>DILIGENCE LOG</div>
            {["현장실사","등기부등본","건축물대장","감정평가서","임대차현황","국세완납증명"].map((item, i) => (
              <div key={i} style={{ background: "#fff", border: "0.5px solid #e5e5e5", borderRadius: 7, padding: "10px 14px", marginBottom: 6, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ fontSize: 12, fontWeight: 500 }}>{item}</div>
                <span style={{ fontSize: 9, color: "#888", background: "#F5F5F5", padding: "2px 8px", borderRadius: 8, fontWeight: 600 }}>미수령</span>
              </div>
            ))}
          </div>
        )}

        {tab === "status" && (
          <div style={{ maxWidth: 380 }}>
            <div style={{ marginBottom: 10 }}>
              <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>새 상태</div>
              <select value={status} onChange={e => setStatus(e.target.value)} style={{ width: "100%", padding: "7px 10px", border: "0.5px solid #ddd", borderRadius: 6, fontSize: 12, outline: "none" }}>
                {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 10, color: "#666", marginBottom: 4 }}>Decision Reason ★</div>
              <textarea value={reason} onChange={e => setReason(e.target.value)} placeholder="판단 근거를 기록하세요."
                style={{ width: "100%", height: 80, padding: "7px 10px", border: "0.5px solid #ddd", borderRadius: 6, fontSize: 11, outline: "none", resize: "vertical", fontFamily: "inherit", boxSizing: "border-box" }} />
            </div>
            {msg && <div style={{ fontSize: 10, color: "#3B6D11", marginBottom: 8 }}>{msg}</div>}
            <button onClick={saveStatus} disabled={saving} style={{ padding: "8px 18px", background: "#000", color: "#fff", border: "none", borderRadius: 6, fontSize: 11, fontWeight: 500, cursor: "pointer" }}>
              {saving ? "저장 중..." : "저장"}
            </button>
          </div>
        )}

        {tab === "history" && (
          <div>
            {[...(deal.status_history||[])].reverse().map((h:any,i:number) => (
              <div key={i} style={{ borderLeft: "2px solid #e5e5e5", paddingLeft: 12, marginBottom: 14 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 2 }}>
                  <span style={{ background: STATUS_BG[h.status], color: STATUS_COLOR[h.status], padding: "1px 7px", borderRadius: 10, fontSize: 9, fontWeight: 600 }}>{h.status}</span>
                  <span style={{ fontSize: 9, color: "#bbb" }}>{h.timestamp?.slice(0,16).replace("T"," ")}</span>
                </div>
                <div style={{ fontSize: 11, color: "#444" }}>{h.reason}</div>
              </div>
            ))}
          </div>
        )}
        {tab === "contact" && (
          <ContactLog dealId={dealId} />
        )}
      </div>
    </div>
  );
}

function ActivityPanel({ dealId, deals }: { dealId: string; deals: any[] }) {
  const [deal, setDeal] = React.useState<any>(null);
  const [mode, setMode] = React.useState<"snapshot"|"memo">("snapshot");
  const [memo, setMemo] = React.useState("");
  const [generating, setGenerating] = React.useState(false);

  React.useEffect(() => {
    setMode("snapshot");
    setMemo("");
    API.get(`/deals/${dealId}`).then(r => setDeal(r.data));
  }, [dealId]);

  const d = deals.find(x => x.id === dealId);
  if (!d) return null;

  const STATUS_COLOR: any = { INTAKE: "#888", SCREENED: "#185FA5", WATCHLIST: "#854F0B", ADVANCE: "#3B6D11", REJECT: "#A32D2D" };
  const STATUS_BG: any = { INTAKE: "#F1EFE8", SCREENED: "#E6F1FB", WATCHLIST: "#FAEEDA", ADVANCE: "#EAF3DE", REJECT: "#FCEBEB" };

  const history = deal?.status_history || [];
  const rec = deal?.deal_record || {};

  const generateMemo = async () => {
    setGenerating(true);
    setMode("memo");
    setMemo("");
    try {
      const res = await API.post(`/deals/${dealId}/ic_memo`);
      setMemo(res.data.memo || "생성 실패");
    } catch(e) {
      setMemo("생성 중 오류가 발생했습니다.");
    }
    setGenerating(false);
  };

  if (mode === "memo") return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.6)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
      onClick={e => { if (e.target === e.currentTarget) setMode("snapshot"); }}>
      <div style={{ background: "#fff", borderRadius: 12, width: 640, maxHeight: "80vh", display: "flex", flexDirection: "column", overflow: "hidden", boxShadow: "0 24px 60px rgba(0,0,0,0.3)" }}>
        {/* Header */}
        <div style={{ padding: "20px 28px 16px", borderBottom: "0.5px solid #eee", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
          <div>
            <div style={{ fontSize: 11, color: "#bbb", letterSpacing: 0.5, marginBottom: 2 }}>◈ LUSKA CAPITAL MANAGEMENT</div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>IC Memo Draft</div>
          </div>
          <button onClick={() => setMode("snapshot")} style={{ background: "none", border: "none", fontSize: 18, color: "#bbb", cursor: "pointer", lineHeight: 1 }}>×</button>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflow: "auto", padding: "24px 28px" }}>
          {generating ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, alignItems: "center", paddingTop: 60 }}>
              <Spinner filter="none" label="IC Memo 생성 중" />
              <div style={{ fontSize: 11, color: "#bbb" }}>루스카 Canon 기준 적용</div>
            </div>
          ) : (
            <div style={{ fontSize: 13, color: "#222", lineHeight: 2, whiteSpace: "pre-wrap" }}>
              {memo.split("[").join("\n\n[").trim()}
            </div>
          )}
        </div>

        {/* Footer */}
        {!generating && memo && (
          <div style={{ padding: "14px 28px", borderTop: "0.5px solid #eee", display: "flex", gap: 8, flexShrink: 0 }}>
            <button onClick={() => navigator.clipboard.writeText(memo)}
              style={{ flex: 1, padding: "9px", background: "#f5f5f5", color: "#333", border: "0.5px solid #ddd", borderRadius: 7, fontSize: 12, cursor: "pointer" }}>
              복사
            </button>
            <button onClick={() => setMode("snapshot")}
              style={{ padding: "9px 20px", background: "#000", color: "#fff", border: "none", borderRadius: 7, fontSize: 12, cursor: "pointer" }}>
              닫기
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div style={{ padding: "16px 14px", height: "100%", overflow: "auto", display: "flex", flexDirection: "column", gap: 16 }}>

      <div>
        <div style={{ fontSize: 9, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 10 }}>DEAL SNAPSHOT</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          {[
            ["Stage", <span style={{ background: STATUS_BG[d.status], color: STATUS_COLOR[d.status], padding: "1px 7px", borderRadius: 10, fontSize: 9, fontWeight: 600 }}>{d.status}</span>],
            ["Evidence", <span style={{ fontSize: 10, color: d.missing_count>0?"#854F0B":"#3B6D11" }}>{d.missing_count>0?`Gap ${d.missing_count}`:"OK"}</span>],
            ["채권자", <span style={{ fontSize: 10, color: "#444" }}>{d.creditor||"—"}</span>],
            ["잔액", <span style={{ fontSize: 10, color: "#444" }}>{d.current_balance||"—"}</span>],
          ].map(([label, val]: any) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "5px 0", borderBottom: "0.5px solid #f5f5f5" }}>
              <span style={{ fontSize: 9, color: "#bbb" }}>{label}</span>
              {val}
            </div>
          ))}
        </div>
      </div>

      {rec.next_action && (
        <div>
          <div style={{ fontSize: 9, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 8 }}>NEXT ACTION</div>
          <div style={{ fontSize: 10, color: "#333", lineHeight: 1.6, background: "#F7F7F5", borderRadius: 6, padding: "8px 10px", borderLeft: "2px solid #3B6D11" }}>
            {(rec.next_action||"").slice(0,80)}{(rec.next_action||"").length > 80 ? "..." : ""}
          </div>
        </div>
      )}

      <div>
        <div style={{ fontSize: 9, color: "#999", fontWeight: 600, letterSpacing: 0.5, marginBottom: 10 }}>RECENT ACTIVITY</div>
        {[...history].reverse().slice(0, 5).map((h: any, i: number) => (
          <div key={i} style={{ paddingBottom: 10, marginBottom: 10, borderBottom: "0.5px solid #f5f5f5" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 3 }}>
              <span style={{ background: STATUS_BG[h.status], color: STATUS_COLOR[h.status], padding: "1px 6px", borderRadius: 8, fontSize: 8, fontWeight: 600 }}>{h.status}</span>
              <span style={{ fontSize: 8, color: "#ddd" }}>{h.timestamp?.slice(5,16).replace("T"," ")}</span>
            </div>
            <div style={{ fontSize: 10, color: "#888", lineHeight: 1.5 }}>{h.reason}</div>
          </div>
        ))}
        {history.length === 0 && <div style={{ fontSize: 10, color: "#ddd" }}>이력 없음</div>}
      </div>

      {(d.status === "SCREENED" || d.status === "ADVANCE") && (
        <div style={{ marginTop: "auto" }}>
          <button onClick={generateMemo}
            style={{ width: "100%", padding: "8px", background: "#000", color: "#fff", border: "none", borderRadius: 6, fontSize: 11, fontWeight: 600, cursor: "pointer" }}>
            Generate IC Memo →
          </button>
        </div>
      )}
    </div>
  );
}


// ============================================================
// COSMOS Today View — Action-first Home
// ============================================================

const PRIORITY_CONFIG: Record<string, {dot: string; label: string; bg: string}> = {
  P0: { dot: "#F5222D", label: "긴급", bg: "#FFF1F0" },
  P1: { dot: "#FA8C16", label: "처리 필요", bg: "#FFFBE6" },
  P2: { dot: "#52C41A", label: "준비 완료", bg: "#F6FFED" },
};
const CTA_LABELS: Record<string, string> = {
  ic_memo: "IC Memo 생성 →", evidence: "Evidence 확인 →",
  deal: "딜 열기 →", underwriting: "Underwriting 실행 →",
};
function TodayView({ onNavigateDeal, fullWidth }: { onNavigateDeal: (id: string, action?: string) => void; fullWidth?: boolean }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [meaningful, setMeaningful] = useState<any[]>([]);
  const [marketRead, setMarketRead] = useState<{ text: string; updated_at: string | null }>({ text: "", updated_at: null });
  const [marketDraft, setMarketDraft] = useState("");
  const [editingMarket, setEditingMarket] = useState(false);
  const [feed, setFeed] = useState<{ time: string; source: string; text: string; link?: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [newSinceCount, setNewSinceCount] = useState(0);
  const [newSinceExample, setNewSinceExample] = useState<string | null>(null);
  const [scores, setScores] = useState<any>({ activity_score: 0, activity_breakdown: {}, health_score: 100, health_breakdown: {} });
  const [expanded, setExpanded] = useState(false);
  const [selectedDealCode, setSelectedDealCode] = useState<string | null>(null);
  const lastCheckRef = useRef<Date | null>(null);
  const hasSetLastCheck = useRef(false);

  const load = () => {
    Promise.all([
      API.get("/api/risk-book/deals").catch(() => ({ data: [] })),
      API.get("/api/dashboard/meaningful-changes").catch(() => ({ data: [] })),
      API.get("/api/dashboard/market-read").catch(() => ({ data: { text: "", updated_at: null } })),
      API.get("/dart/scan?days=1").catch(() => ({ data: { hits: [] } })),
      API.get("/api/sourcing/naver-news").catch(() => ({ data: { items: [] } })),
      API.get("/api/dashboard/scores").catch(() => ({ data: { activity_score: 0, activity_breakdown: {}, health_score: 100, health_breakdown: {} } })),
    ]).then(([d, m, mr, dart, news, sc]) => {
      setDeals(d.data || []);
      setMeaningful(m.data || []);
      setMarketRead(mr.data || { text: "", updated_at: null });
      setMarketDraft(mr.data?.text || "");
      setScores(sc.data || { activity_score: 0, activity_breakdown: {}, health_score: 100, health_breakdown: {} });

      const decodeHtml = (t: string) => (t || "").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/<[^>]*>/g, "");

      const f: any[] = [];
      (dart.data?.hits || []).slice(0, 6).forEach((h: any) =>
        f.push({ time: h.disclosed_at || "", source: "공시", text: `[${h.priority}] ${h.corp_name} — ${h.report_title}`, link: h.dart_url })
      );
      (news.data?.items || []).slice(0, 6).forEach((it: any) =>
        f.push({ time: it.pub_date || "", source: "뉴스", text: decodeHtml(it.title), link: it.link })
      );
      f.sort((a, b) => (b.time > a.time ? 1 : -1));
      setFeed(f);

      if (!hasSetLastCheck.current) {
        const stored = localStorage.getItem("cosmos_last_check_ts");
        lastCheckRef.current = stored ? new Date(stored) : null;
        localStorage.setItem("cosmos_last_check_ts", new Date().toISOString());
        hasSetLastCheck.current = true;
      }
      let newCount = 0;
      let example: string | null = null;
      if (lastCheckRef.current) {
        f.forEach(item => {
          const d = new Date(item.time);
          if (!isNaN(d.getTime()) && d > lastCheckRef.current!) {
            newCount++;
            if (!example) example = `${item.source} — ${item.text}`;
          }
        });
      }
      setNewSinceCount(newCount);
      setNewSinceExample(example);

      setLoading(false);
    }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); const i = setInterval(load, 60000); return () => clearInterval(i); }, []);

  const saveMarketRead = async () => {
    try {
      await API.put("/api/dashboard/market-read", { text: marketDraft });
      setMarketRead({ text: marketDraft, updated_at: new Date().toISOString() });
      setEditingMarket(false);
    } catch {}
  };

  const removeMeaningful = async (id: number) => {
    try { await API.delete(`/api/dashboard/meaningful-changes/${id}`); setMeaningful(prev => prev.filter(m => m.id !== id)); } catch {}
  };

  const dateStr = new Date().toLocaleDateString("ko-KR", { month: "long", day: "numeric", weekday: "short" });

  const holdDeals = deals.filter((d: any) => d.final_gate === "HOLD");
  const repDeal = holdDeals[0] || deals[0];
  const selDeal = deals.find((d: any) => d.deal_code === selectedDealCode) || repDeal;
  const topReason = repDeal?.hold_reasons?.[0];
  const topAction = repDeal?.required_actions?.[0] || repDeal?.hold_reasons?.[1];
  const expAmt = repDeal?.exposure_amount;
  const maturity = repDeal?.maturity_date ? new Date(repDeal.maturity_date) : null;
  const dday = maturity && !isNaN(maturity.getTime()) ? Math.ceil((maturity.getTime() - Date.now()) / 86400000) : null;

  if (loading) return <Spinner filter="none" style={{ padding: 48 }} />;

  const C = { surface: "#11161D", border: "#1E2630", text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B", amber: "#F0A93B", red: "#E5484D", green: "#2BC48A" };

  return (
    <div style={{ width: "100%", display: "flex", padding: "10px 0", boxSizing: "border-box" as const }}>

      {/* 좌측 — 항상 보이는 고정 패널 */}
      <div style={{ width: expanded ? 360 : "50%", flexShrink: 0, padding: "0 32px", boxSizing: "border-box" as const }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: C.textDim }}>COSMOS / TODAY — {dateStr}</div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <button onClick={() => onNavigateDeal("sourcing", "sourcing")}
              style={{ padding: "5px 14px", background: C.surface, border: `1px solid ${C.border}`, borderRadius: 20, color: "#6FA8FF", fontSize: 11, cursor: "pointer" }}>
              Signal Room에서 신호 처리하기
            </button>
            <span onClick={() => setExpanded((v: boolean) => !v)} style={{ fontSize: 18, color: C.textDim, cursor: "pointer" }}>
              {expanded ? "<" : ">"}
            </span>
          </div>
        </div>

        {deals.map((d: any) => {
          const dExp = d.exposure_amount;
          const dMaturity = d.maturity_date ? new Date(d.maturity_date) : null;
          const dDday = dMaturity && !isNaN(dMaturity.getTime()) ? Math.ceil((dMaturity.getTime() - Date.now()) / 86400000) : null;
          return (
            <div key={d.deal_code} onClick={() => { setSelectedDealCode(d.deal_code); setExpanded(true); }}
              style={{ marginBottom: 18, cursor: "pointer" }}>
              <div style={{ fontSize: 13, color: C.text, marginBottom: 10, fontFamily: "'IBM Plex Mono', monospace" }}>
                {d.deal_name}
                {dExp ? ` · 익스포저 ${(dExp / 100000000).toFixed(1)}억` : ""}
                {dDday !== null ? ` · 만기 D-${dDday}` : ""}
              </div>
              <div style={{ display: "flex", gap: 20, justifyContent: "flex-start", alignItems: "center" }}>
                <ScoreGauge label="활동 점수" value={scores.activity_score} max={50} color={C.green} />
                <ScoreGauge label="진행 건강도" value={scores.health_score} max={100} color={scores.health_score < 60 ? C.red : scores.health_score < 80 ? C.amber : C.green} />
              </div>
            </div>
          );
        })}
      </div>

      {expanded && (
      <div style={{ flex: 1, minWidth: 0, padding: "0 32px", boxSizing: "border-box" as const, borderLeft: `1px solid ${C.border}`, overflow: "auto" }}>

      {/* 선택한 딜 진단 — 활동점수 치트시트 대신 실제 딜 막힘 사유/필요조치 표시 */}
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 10, marginBottom: 14 }}>
        <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 14px", minWidth: 0, overflow: "hidden" }}>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 8, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {selDeal ? `${selDeal.deal_name} — 왜 막혔나` : "왜 막혔나"}
          </div>
          {(!selDeal || (selDeal.hold_reasons || []).length === 0) ? (
            <div style={{ fontSize: 12, color: C.textDim }}>막힌 사유 없음</div>
          ) : (selDeal.hold_reasons as string[]).map((r: string, i: number) => (
            <div key={i} style={{ fontSize: 12, color: C.text, borderLeft: `2px solid ${C.red}`, paddingLeft: 8, marginBottom: 6 }}>{r}</div>
          ))}
        </div>

        <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 14px", minWidth: 0, overflow: "hidden" }}>
          <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 8 }}>뭘 풀어야 하나</div>
          {(!selDeal || (selDeal.required_actions || []).length === 0) ? (
            <div style={{ fontSize: 12, color: C.textDim }}>필요 조치 없음</div>
          ) : (selDeal.required_actions as string[]).map((a: string, i: number) => (
            <div key={i} style={{ fontSize: 12, color: C.text, marginBottom: 6 }}>{a}</div>
          ))}
        </div>
      </div>

      {/* My Priority Today */}
      <div style={{
        background: C.surface, border: `1px solid ${topDealColor(holdDeals.length, C)}`,
        borderLeft: `4px solid ${holdDeals.length > 0 ? C.amber : C.green}`, borderRadius: 6,
        padding: "18px 20px", marginBottom: 12,
      }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", marginBottom: 10 }}>MY PRIORITY TODAY</div>
        {holdDeals.length > 0 ? (
          <>
            <div style={{ fontSize: 16, fontWeight: 700, color: C.text, marginBottom: 6 }}>
              {repDeal.deal_name} — {topReason}
            </div>
            {topAction && <div style={{ fontSize: 13, color: C.textMid, marginBottom: 12 }}>{topAction}</div>}
            <button onClick={() => onNavigateDeal(repDeal.deal_code, "pipeline")}
              style={{ padding: "7px 16px", background: C.amber, border: "none", borderRadius: 4, color: "#0A0E14", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
              딜 상세 보기
            </button>
          </>
        ) : (
          <div style={{ fontSize: 14, color: C.green }}>오늘 우선 처리할 이슈 없음</div>
        )}
      </div>

      {/* Blockers / At Risk */}
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 16px", marginBottom: 10 }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 6 }}>BLOCKERS / AT RISK</div>
        {holdDeals.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim }}>막힌 딜 없음</div>
        ) : (
          <div style={{ fontSize: 13, color: C.text }}>{holdDeals.length}건이 <strong>{topReason}</strong>로 막힘</div>
        )}
      </div>

      {/* Since Last Check */}
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 16px", marginBottom: 10 }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 6 }}>SINCE LAST CHECK</div>
        {newSinceCount === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim }}>마지막 확인 이후 새 외부 신호 없음</div>
        ) : (
          <div style={{ fontSize: 12, color: C.text }}>새 외부 신호 {newSinceCount}건 감지 — {newSinceExample}</div>
        )}
      </div>

      {/* Worth Reading Now */}
      <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "12px 16px", marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.06em", marginBottom: 6 }}>WORTH READING NOW</div>
        {meaningful.length === 0 ? (
          <div style={{ fontSize: 11, color: C.textDim }}>Signal Room에서 ★ 표시한 항목이 여기 모입니다</div>
        ) : meaningful.map((m: any) => (
          <div key={m.id} style={{ marginBottom: 8 }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              {m.source_link ? (
                <a href={m.source_link} target="_blank" rel="noreferrer" style={{ fontSize: 12, color: C.text, fontWeight: 600, textDecoration: "underline", textDecorationColor: C.textDim }}>{m.title}</a>
              ) : (
                <span style={{ fontSize: 12, color: C.text, fontWeight: 600 }}>{m.title}</span>
              )}
              <span onClick={() => removeMeaningful(m.id)} style={{ fontSize: 11, color: C.textDim, cursor: "pointer" }}>×</span>
            </div>
            {m.note && <div style={{ fontSize: 11, color: C.textMid, marginTop: 2 }}>{m.note}</div>}
          </div>
        ))}
      </div>

      {/* Market Read + Live Feed — 하단, 작게 */}
      <div style={{ borderTop: `1px solid ${C.border}`, paddingTop: 14 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ fontSize: 9, color: C.textDim, letterSpacing: "0.06em" }}>MARKET READ</span>
          <span onClick={() => setEditingMarket(v => !v)} style={{ fontSize: 10, color: C.textMid, cursor: "pointer" }}>{editingMarket ? "취소" : "수정"}</span>
        </div>
        {editingMarket ? (
          <>
            <textarea value={marketDraft} onChange={e => setMarketDraft(e.target.value)} rows={3}
              style={{ width: "100%", background: "#0A0E14", border: `1px solid ${C.border}`, borderRadius: 4, color: C.text, fontSize: 12, padding: 8, boxSizing: "border-box", fontFamily: "inherit", resize: "vertical" }} />
            <button onClick={saveMarketRead} style={{ marginTop: 6, padding: "5px 12px", background: C.green, border: "none", borderRadius: 4, color: "#0A0E14", fontSize: 11, fontWeight: 600, cursor: "pointer" }}>저장</button>
          </>
        ) : (
          <div style={{ fontSize: 11, color: marketRead.text ? C.textMid : C.textDim, marginBottom: 12 }}>
            {marketRead.text || "오늘 시장 판단을 입력하세요"}
          </div>
        )}

      </div>

      <div style={{ marginTop: 20, display: "flex", gap: 8 }}>
        <button onClick={() => onNavigateDeal("new", "intake")} style={{ padding: "5px 12px", background: "transparent", color: "#666", border: "1px solid #222", borderRadius: 0, fontSize: 9, cursor: "pointer", fontFamily: "'ZenSerif', 'IBM Plex Mono', monospace", letterSpacing: "0.08em" }}>+ New Deal</button>
        <button onClick={() => onNavigateDeal("pipeline", "pipeline")} style={{ padding: "5px 12px", background: "transparent", color: "#444", border: "1px solid #1A1A1A", borderRadius: 0, fontSize: 9, cursor: "pointer", fontFamily: "'ZenSerif', 'IBM Plex Mono', monospace", letterSpacing: "0.08em" }}>Pipeline 전체 보기</button>
      </div>

      </div>
      )}
    </div>
  );
}


function topDealColor(holdCount: number, C: any) {
  return holdCount > 0 ? C.amber : C.border;
}

function ScoreGauge({ label, value, max, color }: { label: string; value: number; max: number; color: string }) {
  const pct = Math.min(1, Math.max(0, value / max));
  const r = 30, circ = 2 * Math.PI * r;
  const offset = circ * (1 - pct);
  return (
    <div style={{ textAlign: "center" }}>
      <svg width={76} height={76} viewBox="0 0 76 76">
        <circle cx={38} cy={38} r={r} fill="none" stroke="#1E2630" strokeWidth={6} />
        <circle cx={38} cy={38} r={r} fill="none" stroke={color} strokeWidth={6}
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 38 38)" style={{ transition: "stroke-dashoffset 0.4s ease" }} />
        <text x={38} y={35} textAnchor="middle" fontSize={16} fontWeight={700} fill="#E4E7EB">{value}</text>
        <text x={38} y={47} textAnchor="middle" fontSize={7} fill="#525C6B">점</text>
      </svg>
      <div style={{ fontSize: 9, color: "#8B95A3", marginTop: 1 }}>{label}</div>
    </div>
  );
}


function MainApp({ onLogout }: { onLogout: () => void }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [selectedId, setSelectedId] = useState<string|null>(null);
  const [selectedTab, setSelectedTab] = useState<string|undefined>(undefined);
  const [currentView, setCurrentView] = useState<"today"|"pipeline">("pipeline");
  const [filter, setFilter] = useState("ALL");
  const [nav, setNav] = useState("pipeline");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [killCheckDeal, setKillCheckDeal] = useState<RegisteredDeal | null>(null);
  const [dashKey, setDashKey] = useState(0);

  const loadDeals = () => {
    setLoading(true);
    API.get("/api/risk-book/deals").then(r => { setDeals(r.data); setLoading(false); });
  };

  useEffect(() => { loadDeals(); }, []);

  // Credit Desk(/dashboard)에서 /app?nav=intake|pipeline|signalroom 등으로 진입 시 해당 화면 오픈
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("nav");
    if (!p) return;
    if (p === "pipeline") { setNav("pipeline"); setCurrentView("pipeline"); }
    else { setNav(p); }
  }, []);

  const needsIC = deals.filter(d => d.status === "SCREENED" || d.status === "ADVANCE").length;
  const hardKillRed = deals.filter(d => d.missing_count === 0 && d.status !== "REJECT").length;
  const evidenceMissing = deals.filter(d => d.missing_count > 0).length;
  const bankFollowUp = deals.filter(d => d.status === "WATCHLIST").length;

  const filtered = filter === "ALL" ? deals : deals.filter(d => d.status === filter);

  const navItems = [
    { id: "pipeline", icon: ICONS.pipeline, label: "Pipeline" },
    { id: "intake", icon: ICONS.intake, label: "Deal Intake" },
  ];
  const comingSoon = [
    { id: "legal", icon: ICONS.legal, label: "Legal Workstream" },
    { id: "evidence", icon: ICONS.evidence, label: "Evidence Register" },
    { id: "bank", icon: ICONS.bank, label: "Bank Routing" },
    { id: "ic", icon: ICONS.ic, label: "IC Memo" },
  ];

  const activePage = nav === "intake" ? "intake" : nav === "sourcing" ? "market" : nav === "signalroom" ? "signalroom" : nav === "diagnostic" ? "diagnostic" : nav === "evidence" ? "evidence" : currentView;
  return (
    <Layout page={activePage} onNav={(p: string) => { if (p==="creditdesk"){ window.location.href="/dashboard"; return; } if (p==="intake"){setNav("intake");}else if (p==="market"){setNav("sourcing");}else if (p==="signalroom"){setNav("signalroom");}else if (p==="diagnostic"){setNav("diagnostic");}else if (p==="riskbook"){setNav("diagnostic");}else if (p==="evidence"){setNav("evidence");}else if (p==="today"){setNav("pipeline");setCurrentView("pipeline");}else if (p==="pipeline"){setNav("pipeline");setCurrentView("pipeline");}else{setNav("pipeline");setCurrentView("pipeline");} }} onLogout={onLogout} dealCount={deals.length} userEmail="gp@luska.kr" onCollapsedChange={setSidebarCollapsed}>
      <div style={{ display:"flex", height:"100%", overflow:"hidden" }}>
        {nav === "evidence" ? (
            <EvidenceChecklist />
          ) : nav === "diagnostic" ? (
            <RiskBook />
          ) : nav === "sourcing" ? (
            <MarketScan />
          ) : nav === "signalroom" ? (
            <SignalRoom onDealRegistered={(deal) => { setKillCheckDeal(deal); setNav("pipeline"); setCurrentView("pipeline"); }} />
          ) : nav === "intake" ? (
          <DealIntake
            onClose={() => setNav("pipeline")}
            onRegistered={(deal) => { setKillCheckDeal(deal); setNav("pipeline"); setCurrentView("pipeline"); }}
          />
        ) : (
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            <div style={{ flex: 1, overflow: "hidden" }}>
              <Pipeline onSelectDeal={() => {}} initialDealCode={selectedId} initialTab={selectedTab} />
            </div>
          </div>
        )}
      </div>
      {killCheckDeal && (
        <KillCheck
          dealId={killCheckDeal.dealId}
          dealCode={killCheckDeal.dealCode}
          thesis={killCheckDeal.thesis}
          thesisType={killCheckDeal.dealType}
          dealType={killCheckDeal.dealType}
          declaredKillCriteria={killCheckDeal.killCriteria}
          onPass={() => { setKillCheckDeal(null); setDashKey(k => k + 1); setCurrentView("pipeline"); loadDeals(); }}
          onDrop={() => setKillCheckDeal(null)}
          onClose={() => setKillCheckDeal(null)}
        />
      )}
    </Layout>
  );
}

// ── 단일 스크롤 스냅 데크 (1~8페이지) ──────────────────────
const DECK_TABS = [
  { id: "page-1", label: "Credit Desk" },
  { id: "page-2", label: "Deals" },
  { id: "page-3", label: "DD" },
  { id: "page-4", label: "Portfolio" },
];
function ScrollDeck({ onLogout }: { onLogout: () => void }) {
  const D = { bg: "#080C14", gold: "#C9A84C", border: "#1A2332", text: "#E2E8F0", muted: "#4A6080" };
  const TOPBAR_H = 88; // Alert(24) + 탑바(36) + 에이전트바(28)
  const [active, setActive] = useState("page-1");
  const [deals, setDeals] = useState<any[]>([]);
  const deckRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    API.get("/api/risk-book/deals").then(r => setDeals(r.data || [])).catch(() => setDeals([]));
  }, []);

  useEffect(() => {
    const root = deckRef.current;
    if (!root) return;
    const obs = new IntersectionObserver(
      entries => entries.forEach(e => { if (e.isIntersecting) setActive(e.target.id); }),
      { root, threshold: 0.5 }
    );
    DECK_TABS.forEach(t => { const el = document.getElementById(t.id); if (el) obs.observe(el); });
    return () => obs.disconnect();
  }, []);

  const go = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  const sec: React.CSSProperties = { minHeight: "100vh", scrollSnapAlign: "start", overflowY: "auto" };
  const ph: React.CSSProperties = { ...sec, background: D.bg, display: "flex", alignItems: "center", justifyContent: "center", color: "#1A2235", fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" };

  return (
    <>
      {/* 고정 탑바 */}
      <div style={{ position: "fixed", top: 0, left: 0, right: 0, zIndex: 100, height: 54, background: D.bg, borderBottom: `1px solid ${D.border}`, display: "flex", alignItems: "center", padding: "0 20px", fontFamily: "'Goldman Sans', sans-serif" }}>
        <div style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
          <img src="/logo.png" width={24} height={24} alt="Cosmos" style={{ filter: "invert(1) sepia(1) saturate(2) hue-rotate(5deg) brightness(0.9)" }} />
          <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: "0.06em", color: D.gold }}>COSMOS</span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {DECK_TABS.map(t => {
            const on = t.id === active;
            return (
              <div key={t.id} onClick={() => go(t.id)} style={{ padding: "8px 16px", cursor: "pointer", fontSize: 13, color: on ? D.text : D.muted, borderBottom: on ? `2px solid ${D.gold}` : "2px solid transparent" }}>{t.label}</div>
            );
          })}
        </div>
        <div style={{ flex: 1, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 12 }}>
          <button onClick={() => { window.location.href = "/app?nav=intake"; }} style={{ padding: "8px 15px", background: "transparent", color: D.gold, border: `1px solid ${D.gold}`, borderRadius: 4, fontSize: 12, cursor: "pointer", fontFamily: "inherit" }}>+ New Deal</button>
          <span onClick={onLogout} title="로그아웃" style={{ fontSize: 17, color: D.muted, cursor: "pointer", lineHeight: 1 }}>⏻</span>
        </div>
      </div>

      {/* 스크롤 스냅 컨테이너 */}
      <div ref={deckRef} style={{ height: "100vh", overflowY: "scroll", scrollSnapType: "y mandatory", scrollBehavior: "smooth", background: D.bg }}>
        <section id="page-1" style={{ ...sec, paddingTop: TOPBAR_H }}><CreditDesk onLogout={onLogout} /></section>
        <section id="page-2" style={{ ...sec, display: "flex", flexDirection: "column" }}><DealExecution deals={deals} /></section>
        <section id="page-3" style={{ ...sec, display: "flex", flexDirection: "column" }}><ClosingPage deals={deals} /></section>
        <section id="page-4" style={{ ...sec, display: "flex", flexDirection: "column" }}><PortfolioPage deals={deals} /></section>
        <section id="page-5" style={{ ...sec, display: "flex", flexDirection: "column" }}><FundAccountingPage deals={deals} /></section>
        <section id="page-6" style={{ ...sec, display: "flex", flexDirection: "column" }}><LPRelationsPage deals={deals} /></section>
        <section id="page-7" style={{ ...sec, display: "flex", flexDirection: "column" }}><RiskCompliancePage deals={deals} /></section>
        <section id="page-8" style={{ ...sec, display: "flex", flexDirection: "column" }}><SourcingPage deals={deals} /></section>
      </div>
    </>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken("");
  };

  if (!token) {
    if (window.location.pathname === "/login") {
      // 로그인 직후 Credit Desk(/dashboard)로 진입
      return <Login onLogin={(t) => { localStorage.setItem("token", t); setToken(t); window.location.href = "/dashboard"; }} />;
    }
    return <Landing onLogin={() => { window.location.href = "/login"; }} />;
  }
  // 레거시 딜 워크플로우(인테이크/파이프라인/실사/시그널룸/리스크북)는 /app 에서
  if (window.location.pathname.startsWith("/app")) {
    return <MainApp onLogout={handleLogout} />;
  }
  // 루트 / 및 /dashboard → 단일 스크롤 스냅 데크 (1~8페이지)
  return <ScrollDeck onLogout={handleLogout} />;
}

// ═══════════════════════════════════════════════════════
// ContactLog Component
// ═══════════════════════════════════════════════════════
const CH_ICON: Record<string,string> = { CALL:"📞", EMAIL:"📧", MEETING:"🤝", VISIT:"🏢", KKT:"💬" };
const OUTCOME_OPTIONS: Record<string,string[]> = {
  CALL:["CONNECTED","VOICEMAIL","NO_ANSWER"],
  EMAIL:["REPLIED","BOUNCED","SENT"],
  MEETING:["COMPLETED","CANCELLED","RESCHEDULED"],
  VISIT:["COMPLETED","NO_SHOW"],
  KKT:["REPLIED","READ","SENT"],
};
const OUTCOME_COLOR: Record<string,string> = {
  CONNECTED:"#22c55e",REPLIED:"#22c55e",COMPLETED:"#22c55e",
  VOICEMAIL:"#f59e0b",SENT:"#f59e0b",READ:"#f59e0b",
  NO_ANSWER:"#ef4444",BOUNCED:"#ef4444",CANCELLED:"#ef4444",NO_SHOW:"#ef4444",
  RESCHEDULED:"#8b5cf6",
};
interface CLEntry {
  id:number; deal_id:string; contact_date:string; contact_time?:string;
  channel:string; counterparty:string; direction:string; outcome:string;
  summary?:string; next_action?:string; next_action_date?:string;
  sensitivity:string; created_by:string; created_at:string;
}
const CL_EMPTY = {
  contact_date:new Date().toISOString().slice(0,10), contact_time:"",
  channel:"CALL", counterparty:"", direction:"OUTBOUND", outcome:"CONNECTED",
  summary:"", next_action:"", next_action_date:"", sensitivity:"NORMAL",
};
function ContactLog({ dealId }:{ dealId:string }) {
  const token = localStorage.getItem("token") || "";
  const [logs, setLogs] = React.useState<CLEntry[]>([]);
  const [showForm, setShowForm] = React.useState(false);
  const [form, setForm] = React.useState({...CL_EMPTY});
  const [editId, setEditId] = React.useState<number|null>(null);
  const [expanded, setExpanded] = React.useState<number|null>(null);
  const [saving, setSaving] = React.useState(false);

  const load = () => {
    API.get(`/deals/${dealId}/contact-log`).then(r=>setLogs(r.data)).catch(e=>console.error('ContactLog error:', e));
  }
  React.useEffect(()=>{ load(); },[dealId]);

  const save = async () => {
    if (!form.counterparty||!form.contact_date) return;
    setSaving(true);
    const url = editId?`/deals/${dealId}/contact-log/${editId}`:`/deals/${dealId}/contact-log`;
    editId ? await API.put(url, form) : await API.post(url, {...form, deal_id:dealId});
    setSaving(false); setShowForm(false); setEditId(null); setForm({...CL_EMPTY}); load();
  };
  const del = async (id:number) => {
    if (!window.confirm("삭제할까요?")) return;
    await API.delete(`/deals/${dealId}/contact-log/${id}`);
    load();
  };
  const startEdit = (e:CLEntry) => {
    setForm({contact_date:e.contact_date,contact_time:e.contact_time||"",channel:e.channel,
      counterparty:e.counterparty,direction:e.direction,outcome:e.outcome,
      summary:e.summary||"",next_action:e.next_action||"",
      next_action_date:e.next_action_date||"",sensitivity:e.sensitivity});
    setEditId(e.id); setShowForm(true);
  };
  const inp:React.CSSProperties={width:"100%",boxSizing:"border-box",background:"#f9fafb",
    border:"1px solid #e5e7eb",borderRadius:5,padding:"5px 8px",fontSize:12};
  const lbl:React.CSSProperties={fontSize:11,color:"#6b7280",marginBottom:2,display:"block"};
  const btn=(bg:string,color="white"):React.CSSProperties=>
    ({background:bg,color,border:"none",borderRadius:5,padding:"5px 12px",fontSize:12,cursor:"pointer"});
  return (
    <div style={{padding:12}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:10}}>
        <span style={{fontSize:13,fontWeight:700}}>📋 Counterparty Engagement Log</span>
        <button style={btn("#111")} onClick={()=>{setForm({...CL_EMPTY});setEditId(null);setShowForm(!showForm);}}>+ New Entry</button>
      </div>
      {showForm&&(
        <div style={{background:"#f0f9ff",border:"1px solid #bae6fd",borderRadius:8,padding:12,marginBottom:12}}>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr 1fr",gap:8,marginBottom:8}}>
            <div><label style={lbl}>날짜</label><input style={inp} type="date" value={form.contact_date} onChange={e=>setForm({...form,contact_date:e.target.value})} /></div>
            <div><label style={lbl}>시간</label><input style={inp} type="time" value={form.contact_time} onChange={e=>setForm({...form,contact_time:e.target.value})} /></div>
            <div><label style={lbl}>채널</label>
              <select style={inp} value={form.channel} onChange={e=>setForm({...form,channel:e.target.value,outcome:(OUTCOME_OPTIONS[e.target.value]||[])[0]||""})}>
                {["CALL","EMAIL","MEETING","VISIT","KKT"].map(c=><option key={c}>{c}</option>)}
              </select>
            </div>
            <div><label style={lbl}>방향</label>
              <select style={inp} value={form.direction} onChange={e=>setForm({...form,direction:e.target.value})}>
                <option>OUTBOUND</option><option>INBOUND</option>
              </select>
            </div>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr 1fr",gap:8,marginBottom:8}}>
            <div><label style={lbl}>상대방</label><input style={inp} placeholder="신한은행 강남중앙지점 ○○○ 팀장" value={form.counterparty} onChange={e=>setForm({...form,counterparty:e.target.value})} /></div>
            <div><label style={lbl}>결과</label>
              <select style={inp} value={form.outcome} onChange={e=>setForm({...form,outcome:e.target.value})}>
                {(OUTCOME_OPTIONS[form.channel]||[]).map(o=><option key={o}>{o}</option>)}
              </select>
            </div>
            <div><label style={lbl}>민감도</label>
              <select style={inp} value={form.sensitivity} onChange={e=>setForm({...form,sensitivity:e.target.value})}>
                <option>NORMAL</option><option>CONFIDENTIAL</option>
              </select>
            </div>
          </div>
          <div style={{marginBottom:8}}>
            <label style={lbl}>내용 요약</label>
            <textarea style={{...inp,minHeight:60,resize:"vertical"}} placeholder="통화/미팅 주요 내용..." value={form.summary} onChange={e=>setForm({...form,summary:e.target.value})} />
          </div>
          <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:8,marginBottom:10}}>
            <div><label style={lbl}>후속 액션</label><input style={inp} placeholder="재콜, 자료 발송 등..." value={form.next_action} onChange={e=>setForm({...form,next_action:e.target.value})} /></div>
            <div><label style={lbl}>예정일</label><input style={inp} type="date" value={form.next_action_date} onChange={e=>setForm({...form,next_action_date:e.target.value})} /></div>
          </div>
          <div style={{display:"flex",gap:8,justifyContent:"flex-end"}}>
            <button style={btn("#e5e7eb","#374151")} onClick={()=>{setShowForm(false);setEditId(null);}}>취소</button>
            <button style={btn("#2563eb")} onClick={save} disabled={saving}>{saving?"저장중...":editId?"수정 저장":"기록 저장"}</button>
          </div>
        </div>
      )}
      {logs.length===0&&<div style={{textAlign:"center",color:"#9ca3af",padding:24,fontSize:12}}>등록된 컨택 기록이 없습니다.</div>}
      {logs.map(log=>(
        <div key={log.id} style={{border:"1px solid #e5e7eb",borderRadius:7,marginBottom:6,overflow:"hidden"}}>
          <div style={{display:"flex",alignItems:"center",gap:8,padding:"8px 12px",cursor:"pointer",background:"#fff"}}
               onClick={()=>setExpanded(expanded===log.id?null:log.id)}>
            <span style={{fontSize:16}}>{CH_ICON[log.channel]||"📌"}</span>
            <span style={{fontSize:11,color:"#6b7280",minWidth:88}}>{log.contact_date}{log.contact_time?` ${log.contact_time}`:""}</span>
            <span style={{fontSize:12,fontWeight:600,flex:1}}>{log.counterparty}</span>
            <span style={{fontSize:10,background:log.direction==="OUTBOUND"?"#eff6ff":"#f5f3ff",
              color:log.direction==="OUTBOUND"?"#2563eb":"#7c3aed",
              border:`1px solid ${log.direction==="OUTBOUND"?"#bfdbfe":"#ddd6fe"}`,
              borderRadius:4,padding:"1px 6px"}}>{log.direction}</span>
            <span style={{fontSize:10,background:(OUTCOME_COLOR[log.outcome]||"#94a3b8")+"22",
              color:OUTCOME_COLOR[log.outcome]||"#94a3b8",
              border:`1px solid ${OUTCOME_COLOR[log.outcome]||"#94a3b8"}55`,
              borderRadius:4,padding:"1px 6px",fontWeight:600}}>{log.outcome}</span>
            {log.sensitivity==="CONFIDENTIAL"&&<span style={{fontSize:11}}>🔒</span>}
            <button style={{background:"none",border:"none",cursor:"pointer",fontSize:12}} onClick={ev=>{ev.stopPropagation();startEdit(log);}}>✏️</button>
            <button style={{background:"none",border:"none",cursor:"pointer",fontSize:12}} onClick={ev=>{ev.stopPropagation();del(log.id);}}>🗑</button>
          </div>
          {expanded===log.id&&(
            <div style={{padding:"8px 12px 10px",borderTop:"1px solid #f1f5f9",background:"#fafafa"}}>
              {log.summary&&<><div style={{fontSize:10,color:"#6b7280",marginBottom:3}}>내용 요약</div><div style={{fontSize:12,lineHeight:1.6,marginBottom:6}}>{log.summary}</div></>}
              {log.next_action&&<><div style={{fontSize:10,color:"#6b7280",marginBottom:3}}>후속 액션</div>
                <div style={{fontSize:12}}>{log.next_action}{log.next_action_date&&<span style={{color:"#d97706",marginLeft:8}}>→ {log.next_action_date}</span>}</div></>}
              <div style={{fontSize:10,color:"#d1d5db",marginTop:8}}>기록: {log.created_at} · {log.created_by}</div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default App;
