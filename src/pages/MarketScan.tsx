import React, { useState } from "react";
import API from "../api";

const C = {
  bg: "#080C14", surface: "#0D1420", border: "#1A2638",
  gold: "#C9A84C", goldDim: "rgba(201,168,76,0.12)",
  text: "#E2E8F0", textDim: "#5A7190", textMid: "#8FA3BB",
  green: "#22C55E", amber: "#F59E0B", red: "#EF4444",
};

const PC: any = {
  P0: { color: C.red, bg: "rgba(239,68,68,0.1)", label: "즉시확인" },
  P1: { color: C.amber, bg: "rgba(245,158,11,0.1)", label: "검토필요" },
  P2: { color: C.textDim, bg: "rgba(90,113,144,0.1)", label: "참고" },
};

export default function MarketScan() {
  const [days, setDays] = useState(1);
  const [loading, setLoading] = useState(false);
  const [dartData, setDartData] = useState<any>(null);
  const [onbidData, setOnbidData] = useState<any>(null);
  const [molitData, setMolitData] = useState<any>(null);
  const [sending, setSending] = useState<string | null>(null);

  const fullScan = async () => {
    setLoading(true);
    setDartData(null); setOnbidData(null); setMolitData(null);
    try {
      const [dart, onbid, molit] = await Promise.allSettled([
        API.get(`/dart/scan?days=${days}`),
        API.get(`/assets/onbid/search?keyword=강남`),
        API.get(`/assets/11680/transaction`),
      ]);
      if (dart.status === "fulfilled") setDartData(dart.value.data);
      if (onbid.status === "fulfilled") setOnbidData(onbid.value.data);
      if (molit.status === "fulfilled") setMolitData(molit.value.data);
    } catch (e) {}
    setLoading(false);
  };

  const intake = async (hit: any) => {
    const key = hit.corp_name || hit.deal_id || "x";
    setSending(key);
    try {
      await API.post("/deals/analyze", {
        source: `DART — ${hit.corp_name}`,
        raw_input: `법인명: ${hit.corp_name}\n공시: ${hit.report_title}\n일자: ${hit.disclosed_at}\nURL: ${hit.dart_url}\n신호: ${(hit.signals||[]).map((s:any)=>s.keyword).join(", ")}\n스코어: ${hit.score}`
      });
      alert(`✓ ${hit.corp_name} — INTAKE 등록`);
    } catch { alert("등록 실패"); }
    setSending(null);
  };

  const SectionHeader = ({ label, count, color }: any) => (
    <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "28px 0 14px" }}>
      <span style={{ fontSize: 10, letterSpacing: "0.14em", color: color || C.gold, fontWeight: 700 }}>{label}</span>
      {count !== undefined && <span style={{ fontSize: 10, color: C.textDim }}>({count}건)</span>}
      <div style={{ flex: 1, height: 1, background: C.border }} />
    </div>
  );

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.text, fontFamily: "'IBM Plex Mono', monospace", padding: 24 }}>
      {/* 헤더 */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 10, color: C.textDim, letterSpacing: "0.12em", marginBottom: 4 }}>LUSKA CAPITAL — COSMOS</div>
        <div style={{ fontSize: 20, fontWeight: 700, color: C.gold }}>DEAL SOURCING</div>
        <div style={{ fontSize: 10, color: C.textDim, marginTop: 4 }}>DART · OnBid · MOLIT 통합 마켓 스캔</div>
      </div>

      {/* 컨트롤 */}
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 8 }}>
        {[1,3,7].map(d => (
          <button key={d} onClick={() => setDays(d)}
            style={{ padding: "6px 14px", border: `1px solid ${days===d ? C.gold : C.border}`, background: days===d ? C.goldDim : "transparent", color: days===d ? C.gold : C.textDim, cursor: "pointer", fontSize: 11, borderRadius: 4 }}>
            {d}일
          </button>
        ))}
        <button onClick={fullScan} disabled={loading}
          style={{ marginLeft: "auto", padding: "10px 28px", background: loading ? C.border : C.gold, color: "#0a0a0f", border: "none", cursor: loading ? "not-allowed" : "pointer", fontWeight: 700, fontSize: 13, borderRadius: 4 }}>
          {loading ? "스캔 중..." : "▶ FULL SCAN"}
        </button>
      </div>

      {/* 요약 카드 */}
      {dartData && (
        <div style={{ display: "flex", gap: 10, marginBottom: 4 }}>
          {[
            { label: "DART 스캔", val: dartData.total_scanned },
            { label: "TOTAL HITS", val: dartData.summary?.total_hits },
            { label: "P0 즉시확인", val: dartData.summary?.P0, color: C.red },
            { label: "P1 검토필요", val: dartData.summary?.P1, color: C.amber },
          ].map(item => (
            <div key={item.label} style={{ flex: 1, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 14px" }}>
              <div style={{ fontSize: 9, color: C.textDim, marginBottom: 3 }}>{item.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: item.color || C.text }}>{item.val ?? "-"}</div>
            </div>
          ))}
        </div>
      )}
      {dartData && <div style={{ fontSize: 9, color: C.textDim, marginBottom: 4 }}>스캔: {new Date(dartData.scanned_at).toLocaleString("ko-KR")} · {days}일</div>}

      {/* ━━ DART 섹션 ━━ */}
      {dartData && (
        <>
          <SectionHeader label="DART 공시" count={dartData.summary?.total_hits} color={C.red} />
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["우선","법인명","공시일","공시제목","신호","스코어",""].map(h => (
                  <th key={h} style={{ padding: "6px 10px", color: C.textDim, textAlign: "left", fontWeight: 400, fontSize: 9 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(dartData.hits || []).map((hit: any, i: number) => {
                const pc = PC[hit.priority] || PC.P2;
                return (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td style={{ padding: "9px 10px" }}>
                      <span style={{ background: pc.bg, color: pc.color, padding: "2px 7px", borderRadius: 3, fontSize: 9 }}>{hit.priority}</span>
                    </td>
                    <td style={{ padding: "9px 10px", fontWeight: 600 }}>{hit.corp_name}</td>
                    <td style={{ padding: "9px 10px", color: C.textDim, fontSize: 10 }}>{hit.disclosed_at?.slice(0,10)}</td>
                    <td style={{ padding: "9px 10px" }}>
                      <a href={hit.dart_url} target="_blank" rel="noreferrer" style={{ color: C.text, textDecoration: "none" }}>
                        {hit.report_title?.replace("주요사항보고서","").replace(/[()]/g,"").slice(0,30)}
                      </a>
                    </td>
                    <td style={{ padding: "9px 10px", fontSize: 10, color: C.amber }}>
                      {(hit.signals||[]).slice(0,2).map((s:any)=>s.keyword).join(" · ")}
                    </td>
                    <td style={{ padding: "9px 10px", color: pc.color, fontWeight: 700 }}>{hit.score}</td>
                    <td style={{ padding: "9px 10px" }}>
                      <button onClick={() => intake(hit)} disabled={sending === hit.corp_name}
                        style={{ padding: "3px 9px", background: C.goldDim, color: C.gold, border: `1px solid ${C.gold}`, cursor: "pointer", fontSize: 9, borderRadius: 3 }}>
                        INTAKE
                      </button>
                    </td>
                  </tr>
                );
              })}
              {(dartData.hits || []).length === 0 && (
                <tr><td colSpan={7} style={{ padding: 20, color: C.textDim, fontSize: 11, textAlign: "center" }}>신호 없음</td></tr>
              )}
            </tbody>
          </table>
        </>
      )}

      {/* ━━ OnBid 섹션 ━━ */}
      {onbidData && (
        <>
          <SectionHeader label="OnBid 공매" color={C.amber} />
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: 14, fontSize: 11, color: C.textMid }}>
            {onbidData.error ? (
              <span style={{ color: C.textDim }}>연동 오류: {onbidData.error}</span>
            ) : onbidData.raw ? (
              <span style={{ color: C.textDim }}>API 응답: {onbidData.raw}</span>
            ) : (
              <pre style={{ margin: 0, overflow: "auto", maxHeight: 200 }}>{JSON.stringify(onbidData, null, 2)}</pre>
            )}
          </div>
        </>
      )}

      {/* ━━ MOLIT 섹션 ━━ */}
      {molitData && (
        <>
          <SectionHeader label="MOLIT 실거래 (강남구)" color={C.green} />
          <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, padding: 14, fontSize: 11, color: C.textMid }}>
            {molitData.error ? (
              <span style={{ color: C.textDim }}>연동 오류: {molitData.error}</span>
            ) : (
              <pre style={{ margin: 0, overflow: "auto", maxHeight: 200 }}>{JSON.stringify(molitData, null, 2)}</pre>
            )}
          </div>
        </>
      )}

      {!dartData && !loading && (
        <div style={{ textAlign: "center", color: C.textDim, fontSize: 12, marginTop: 60 }}>
          FULL SCAN을 눌러 DART · OnBid · MOLIT 동시 스캔
        </div>
      )}
    </div>
  );
}
