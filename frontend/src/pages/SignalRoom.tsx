import { useState, useEffect, useCallback } from "react";
import Spinner from "../components/Spinner";
import API from "../api";
import SignalCard, { Signal, parseReasons } from "../components/SignalCard";
import DealIntake, { RegisteredDeal, IntakePrefill } from "./DealIntake";

const C = {
  bg: "#0A0E14", surface: "#11161D", border: "#1E2630",
  text: "#E4E7EB", textMid: "#8B95A3", textDim: "#525C6B",
  gold: "#C9A84C", red: "#fb7185", green: "#2BC48A",
};

const FILTERS = [
  { key: "all", label: "전체" },
  { key: "dl", label: "DL" },
  { key: "dp", label: "DP" },
  { key: "ds", label: "DS" },
  { key: "el", label: "EL" },
  { key: "st", label: "ST" },
  { key: "critical", label: "긴급만" },
  { key: "multi", label: "교차확인" },
];

const TYPE_MAP: Record<string, string> = {
  dl: "DIRECT_LENDING", dp: "DEBT_PURCHASE", ds: "DISTRESSED_SPECIAL",
  el: "EQUITY_LINKED_CREDIT", st: "STRUCTURED_TRANCHE",
};

export default function SignalRoom({ onDealRegistered }: { onDealRegistered: (deal: RegisteredDeal) => void }) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [filter, setFilter] = useState("all");
  const [intakePrefill, setIntakePrefill] = useState<IntakePrefill | null>(null);
  const [processing, setProcessing] = useState<number | null>(null);
  const [notice, setNotice] = useState<any>(null);

  const load = useCallback(() => {
    setLoading(true); setErr("");
    API.get("/api/signals")
      .then(r => setSignals(Array.isArray(r.data.signals) ? r.data.signals : []))
      .catch(e => setErr(e?.response?.data?.detail || "조회 실패"))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  // [딜로 등록 →] 전체 자동화 체인: 딜 등록 → Kill Check → SDD AUTO → Narrative Gate → IC Memo
  const handleConvert = (s: Signal) => {
    setProcessing(s.id); setErr(""); setNotice(null);
    API.post(`/api/signals/${s.id}/auto-source`)
      .then(r => { setNotice(r.data); load(); })
      .catch(e => setErr(e?.response?.data?.detail || "자동 소싱 실패"))
      .finally(() => setProcessing(null));
  };
  const handleDismiss = (id: number) => {
    API.patch(`/api/signals/${id}/status`, { status: "DISMISSED" })
      .then(() => setSignals(prev => prev.filter(s => s.id !== id)))
      .catch(() => {});
  };
  const handleWatch = (id: number) => {
    API.patch(`/api/signals/${id}/status`, { status: "WATCHING" })
      .then(() => setSignals(prev => prev.map(s => s.id === id ? { ...s, status: "WATCHING" } : s)))
      .catch(() => {});
  };

  const active = signals.filter(s => s.status !== "DISMISSED");
  const stats = {
    total: active.length,
    critical: active.filter(s => s.urgency === "CRITICAL_72H").length,
    watch: active.filter(s => s.urgency === "WATCH_2W").length,
    converted: signals.filter(s => s.status === "CONVERTED").length,
  };

  const filtered = active.filter(s => {
    if (filter === "all") return true;
    if (filter === "critical") return s.urgency === "CRITICAL_72H";
    if (filter === "multi") return parseReasons(s.reason_summary).length >= 2;
    return s.suggested_deal_type === TYPE_MAP[filter];
  });

  const Stat = ({ label, value, color }: { label: string; value: number; color?: string }) => (
    <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "12px 18px", flex: 1 }}>
      <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.08em", marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: color || C.text }}>{value}</div>
    </div>
  );

  return (
    <div style={{ flex: 1, overflow: "auto", background: C.bg, color: C.text, fontFamily: "Inter, sans-serif", padding: "32px 40px" }}>
      <div style={{ maxWidth: 1000, margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <div style={{ fontSize: 11, color: C.textDim, letterSpacing: "0.12em", marginBottom: 4 }}>COSMOS / SIGNAL ROOM</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>자동 소싱 신호</div>
          </div>
          <button onClick={load} style={{ padding: "7px 16px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textMid, fontSize: 12, cursor: "pointer" }}>↻ 새로고침</button>
        </div>

        {/* 자동 소싱 체인 결과 알림 */}
        {notice && (
          <div style={{ background: notice.memo_ready ? "rgba(43,196,138,0.08)" : "rgba(201,168,76,0.08)",
            border: `1px solid ${notice.memo_ready ? "rgba(43,196,138,0.4)" : "rgba(201,168,76,0.4)"}`,
            borderRadius: 8, padding: "14px 18px", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 14 }}>{notice.memo_ready ? "✅" : "⚠️"}</span>
              <span style={{ fontSize: 13, fontWeight: 700, color: notice.memo_ready ? C.green : C.gold }}>{notice.notification}</span>
              <div style={{ flex: 1 }} />
              <span style={{ fontSize: 11, color: C.textMid }}>{notice.deal_code}</span>
              <button onClick={() => setNotice(null)} style={{ background: "transparent", border: "none", color: C.textDim, fontSize: 16, cursor: "pointer" }}>×</button>
            </div>
            {notice.chain && (
              <div style={{ display: "flex", gap: 14, marginTop: 10, fontSize: 11, color: C.textMid, flexWrap: "wrap" }}>
                <span>Kill Check: <b style={{ color: notice.kill_check === "PASS" ? C.green : C.red }}>{notice.kill_check}</b></span>
                {notice.chain.sdd_auto && <span>SDD AUTO: <b style={{ color: C.text }}>{notice.chain.sdd_auto.filled}채움 / {notice.chain.sdd_auto.na} NA</b></span>}
                {notice.chain.narrative_gate && <span>Gate: <b style={{ color: notice.chain.narrative_gate.result === "CONFIRMED" ? C.green : notice.chain.narrative_gate.result === "BROKEN" ? C.red : C.gold }}>{notice.chain.narrative_gate.result}</b></span>}
                {notice.chain.ic_memo && <span>IC Memo: <b style={{ color: notice.chain.ic_memo.locked ? C.gold : C.green }}>{notice.chain.ic_memo.locked ? "잠금" : "초안 생성"}</b></span>}
              </div>
            )}
            <div style={{ fontSize: 10, color: C.textDim, marginTop: 8 }}>Dashboard에서 딜을 열어 S9 구조 숫자·S10 판단 의견을 입력하세요.</div>
          </div>
        )}

        {/* 통계 */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
          <Stat label="전체 신호" value={stats.total} />
          <Stat label="긴급 (72h)" value={stats.critical} color={C.red} />
          <Stat label="주목 (2w)" value={stats.watch} color={C.gold} />
          <Stat label="딜 전환" value={stats.converted} color={C.green} />
        </div>

        {/* 필터 탭 */}
        <div style={{ display: "flex", gap: 6, marginBottom: 20, flexWrap: "wrap" }}>
          {FILTERS.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)} style={{
              padding: "5px 14px", borderRadius: 6, fontSize: 12, cursor: "pointer",
              background: filter === f.key ? C.gold : "transparent",
              color: filter === f.key ? "#0A0E14" : C.textMid,
              border: `1px solid ${filter === f.key ? C.gold : C.border}`,
              fontWeight: filter === f.key ? 700 : 500,
            }}>{f.label}</button>
          ))}
        </div>

        {err && <div style={{ fontSize: 12, color: C.red, marginBottom: 12 }}>{err}</div>}
        {loading ? (
          <Spinner style={{ padding: 40 }} />
        ) : filtered.length === 0 ? (
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "48px 24px", textAlign: "center" }}>
            <div style={{ fontSize: 14, color: C.textDim }}>{active.length === 0 ? "신규 신호 없음" : "필터에 해당하는 신호 없음"}</div>
            {active.length === 0 && <div style={{ fontSize: 11, color: C.textDim, marginTop: 6 }}>data-pipeline scan이 신호를 수집하면 여기에 표시됩니다</div>}
          </div>
        ) : (
          filtered.map(s => (
            <SignalCard key={s.id} signal={s}
              processing={processing === s.id}
              onConvert={() => handleConvert(s)}
              onWatch={() => handleWatch(s.id)}
              onDismiss={() => handleDismiss(s.id)} />
          ))
        )}
      </div>

      {/* DealIntake 오버레이 (Signal Room 위) */}
      {intakePrefill && (
        <DealIntake
          prefill={intakePrefill}
          onClose={() => setIntakePrefill(null)}
          onRegistered={(deal) => { setIntakePrefill(null); onDealRegistered(deal); }}
        />
      )}
    </div>
  );
}
