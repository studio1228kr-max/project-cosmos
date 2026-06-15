import React, { useState } from "react";
import API from "../api";

const C = {
  bg: "#080C14", surface: "#0D1420", surface2: "#131D2E", border: "#1A2638",
  gold: "#C9A84C", goldDim: "rgba(201,168,76,0.12)",
  text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444", blue: "#3B82F6",
};

const PRIORITY_CFG: any = {
  P0: { color: C.red, bg: "rgba(239,68,68,0.1)", label: "즉시확인" },
  P1: { color: C.amber, bg: "rgba(245,158,11,0.1)", label: "검토필요" },
  P2: { color: C.textDim, bg: "rgba(90,113,144,0.1)", label: "참고" },
};

type TabType = "dart" | "onbid" | "molit";

export default function MarketScan({ onCreateDeal }: { onCreateDeal?: (corp: string, title: string) => void }) {
  const [tab, setTab] = useState<TabType>("dart");
  const [dartResult, setDartResult] = useState<any>(null);
  const [onbidResult, setOnbidResult] = useState<any>(null);
  const [molitResult, setMolitResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(1);
  const [onbidKeyword, setOnbidKeyword] = useState("강남");
  const [molitAddr, setMolitAddr] = useState("11680"); // 강남구 법정동코드
  const [sending, setSending] = useState<string | null>(null);

  const scanDart = async () => {
    setLoading(true);
    try {
      const r = await API.get(`/dart/scan?days=${days}`);
      setDartResult(r.data);
    } catch (e: any) { alert("DART 스캔 오류: " + e.message); }
    setLoading(false);
  };

  const scanOnbid = async () => {
    setLoading(true);
    try {
      const r = await API.get(`/assets/onbid/search?keyword=${encodeURIComponent(onbidKeyword)}`);
      setOnbidResult(r.data);
    } catch (e: any) { alert("온비드 오류: " + e.message); }
    setLoading(false);
  };

  const scanMolit = async () => {
    setLoading(true);
    try {
      const r = await API.get(`/assets/${encodeURIComponent(molitAddr)}/transaction`);
      setMolitResult(r.data);
    } catch (e: any) { alert("MOLIT 오류: " + e.message); }
    setLoading(false);
  };

  const sendToIntake = async (hit: any) => {
    setSending(hit.deal_id || hit.bidNtcNo || "temp");
    try {
      const rawInput = hit.enriched_input ||
        `법인명: ${hit.corp_name || hit.gdsDscrptn || "-"}\n공시/물건: ${hit.report_title || hit.gdsCd || "-"}\n소스: ${hit.dart_url || "OnBid"}\n신호: ${(hit.signals || []).map((s: any) => s.keyword).join(", ")}\n스코어: ${hit.score || "-"}`;
      await API.post("/deals/analyze", {
        source: hit.corp_name ? `DART — ${hit.corp_name}` : `OnBid — ${hit.gdsDscrptn || "물건"}`,
        raw_input: rawInput
      });
      alert(`✓ Pipeline INTAKE 등록됨`);
    } catch (e: any) { alert("등록 오류: " + e.message); }
    setSending(null);
  };

  const tabBtn = (id: TabType, label: string, badge?: string) => (
    <button onClick={() => setTab(id)} style={{
      padding: "8px 16px", border: "none", cursor: "pointer", fontFamily: "inherit",
      fontSize: 12, letterSpacing: "0.06em",
      background: tab === id ? C.gold : "transparent",
      color: tab === id ? "#0a0a0f" : C.textDim,
      borderBottom: tab === id ? `2px solid ${C.gold}` : "2px solid transparent",
    }}>{label}{badge && <span style={{ marginLeft: 6, background: C.red, color: "#fff", borderRadius: 3, padding: "1px 5px", fontSize: 10 }}>{badge}</span>}</button>
  );

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text, fontFamily: "'IBM Plex Mono', monospace" }}>
      {/* 헤더 */}
      <div style={{ padding: "20px 24px 0", borderBottom: `1px solid ${C.border}` }}>
        <div style={{ fontSize: 11, color: C.textDim, letterSpacing: "0.12em", marginBottom: 4 }}>LUSKA CAPITAL</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: C.gold, marginBottom: 16 }}>DEAL SOURCING</div>
        <div style={{ display: "flex", gap: 0 }}>
          {tabBtn("dart", "DART 공시")}
          {tabBtn("onbid", "OnBid 공매")}
          {tabBtn("molit", "MOLIT 실거래")}
        </div>
      </div>

      <div style={{ padding: 24 }}>

        {/* DART 탭 */}
        {tab === "dart" && (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
              {[1,3,7].map(d => (
                <button key={d} onClick={() => setDays(d)}
                  style={{ padding: "6px 14px", border: `1px solid ${days===d ? C.gold : C.border}`, background: days===d ? C.goldDim : "transparent", color: days===d ? C.gold : C.textDim, cursor: "pointer", fontSize: 11, borderRadius: 4 }}>
                  {d}일
                </button>
              ))}
              <button onClick={scanDart} disabled={loading}
                style={{ marginLeft: "auto", padding: "8px 20px", background: C.gold, color: "#0a0a0f", border: "none", cursor: "pointer", fontWeight: 700, fontSize: 12, borderRadius: 4 }}>
                {loading ? "스캔 중..." : "▶ SCAN"}
              </button>
            </div>

            {dartResult && (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginBottom: 20 }}>
                  {[
                    { label: "SCANNED", val: dartResult.total_scanned || 0 },
                    { label: "TOTAL HITS", val: dartResult.summary?.total_hits || 0 },
                    { label: "P0 즉시확인", val: dartResult.summary?.P0 || 0, color: C.red },
                    { label: "P1 검토필요", val: dartResult.summary?.P1 || 0, color: C.amber },
                  ].map(item => (
                    <div key={item.label} style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: "12px 16px" }}>
                      <div style={{ fontSize: 10, color: C.textDim, marginBottom: 4 }}>{item.label}</div>
                      <div style={{ fontSize: 22, fontWeight: 700, color: item.color || C.text }}>{item.val}</div>
                    </div>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: C.textDim, marginBottom: 16 }}>
                  스캔 시각: {new Date(dartResult.scanned_at).toLocaleString("ko-KR")} · 최근 {days}일
                </div>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                      {["우선순위","법인명","공시일","공시제목","신호","스코어","액션"].map(h => (
                        <th key={h} style={{ padding: "8px 12px", color: C.textDim, textAlign: "left", fontWeight: 400, fontSize: 10 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(dartResult.hits || []).map((hit: any, i: number) => {
                      const pc = PRIORITY_CFG[hit.priority] || PRIORITY_CFG.P2;
                      return (
                        <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}>
                          <td style={{ padding: "10px 12px" }}>
                            <span style={{ background: pc.bg, color: pc.color, padding: "2px 8px", borderRadius: 3, fontSize: 10 }}>{hit.priority}</span>
                          </td>
                          <td style={{ padding: "10px 12px", fontWeight: 600 }}>{hit.corp_name}</td>
                          <td style={{ padding: "10px 12px", color: C.textDim, fontSize: 10 }}>{hit.disclosed_at?.slice(0,10)}</td>
                          <td style={{ padding: "10px 12px" }}>
                            <a href={hit.dart_url} target="_blank" rel="noreferrer" style={{ color: C.text, textDecoration: "none" }}>{hit.report_title?.slice(0,40)}</a>
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 10, color: C.amber }}>
                            {(hit.signals||[]).slice(0,3).map((s:any)=>s.keyword).join(", ")}
                          </td>
                          <td style={{ padding: "10px 12px", color: pc.color, fontWeight: 700 }}>{hit.score}</td>
                          <td style={{ padding: "10px 12px" }}>
                            <button onClick={() => sendToIntake(hit)} disabled={sending === hit.deal_id}
                              style={{ padding: "4px 10px", background: C.goldDim, color: C.gold, border: `1px solid ${C.gold}`, cursor: "pointer", fontSize: 10, borderRadius: 3 }}>
                              INTAKE
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}

        {/* OnBid 탭 */}
        {tab === "onbid" && (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
              <input value={onbidKeyword} onChange={e => setOnbidKeyword(e.target.value)}
                placeholder="지역명 입력 (강남, 성수, 여의도...)"
                style={{ flex: 1, background: C.surface, border: `1px solid ${C.border}`, color: C.text, padding: "8px 12px", fontSize: 12, borderRadius: 4 }} />
              <button onClick={scanOnbid} disabled={loading}
                style={{ padding: "8px 20px", background: C.gold, color: "#0a0a0f", border: "none", cursor: "pointer", fontWeight: 700, fontSize: 12, borderRadius: 4 }}>
                {loading ? "조회 중..." : "▶ 조회"}
              </button>
            </div>
            {onbidResult && (
              <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16 }}>
                <pre style={{ fontSize: 11, color: C.textMid, overflow: "auto", maxHeight: 400 }}>
                  {JSON.stringify(onbidResult, null, 2)}
                </pre>
              </div>
            )}
            {!onbidResult && (
              <div style={{ color: C.textDim, fontSize: 12, padding: 40, textAlign: "center" }}>
                지역명으로 공매 물건을 조회하세요.<br/>
                <span style={{ fontSize: 10, color: C.textDim, marginTop: 8, display: "block" }}>온비드 공공데이터 연동</span>
              </div>
            )}
          </div>
        )}

        {/* MOLIT 탭 */}
        {tab === "molit" && (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 20, alignItems: "center" }}>
              <select value={molitAddr} onChange={e => setMolitAddr(e.target.value)}
                style={{ background: C.surface, border: `1px solid ${C.border}`, color: C.text, padding: "8px 12px", fontSize: 12, borderRadius: 4 }}>
                <option value="11680">강남구</option>
                <option value="11650">서초구</option>
                <option value="11710">송파구</option>
                <option value="11440">마포구</option>
                <option value="11590">동작구</option>
                <option value="11230">성동구</option>
                <option value="11110">종로구</option>
                <option value="11140">중구</option>
              </select>
              <button onClick={scanMolit} disabled={loading}
                style={{ padding: "8px 20px", background: C.gold, color: "#0a0a0f", border: "none", cursor: "pointer", fontWeight: 700, fontSize: 12, borderRadius: 4 }}>
                {loading ? "조회 중..." : "▶ 조회"}
              </button>
            </div>
            {molitResult && (
              <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: 16 }}>
                <pre style={{ fontSize: 11, color: C.textMid, overflow: "auto", maxHeight: 400 }}>
                  {JSON.stringify(molitResult, null, 2)}
                </pre>
              </div>
            )}
            {!molitResult && (
              <div style={{ color: C.textDim, fontSize: 12, padding: 40, textAlign: "center" }}>
                구별 상업용 부동산 실거래가를 조회하세요.<br/>
                <span style={{ fontSize: 10, color: C.textDim, marginTop: 8, display: "block" }}>국토부 실거래가 공개시스템 연동</span>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
