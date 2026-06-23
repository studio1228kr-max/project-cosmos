import { useState, useEffect } from 'react';

const API_BASE = 'https://project-cosmos-production.up.railway.app';

const C = {
  bg: '#0A0E14', surface: '#11161D', border: '#1E2630',
  text: '#E4E7EB', textMid: '#8B95A3', textDim: '#525C6B',
  amber: '#F0A93B', red: '#E5484D', green: '#2BC48A', blue: '#6FA8FF',
};

const DEAL_TYPE_LABEL: Record<string, string> = {
  DIRECT_LENDING: 'Direct Lending', DEBT_PURCHASE: 'Debt Purchase',
  STRUCTURED: 'Structured', DISTRESSED: 'Distressed', EQUITY_LINKED: 'Equity-Linked',
  NPL_PURCHASE: 'NPL Purchase', SECURED_CREDIT_ACQUISITION: 'Secured Credit',
  SPECIAL_SITUATIONS_CONTROL: 'Special Situations', BRIDGE_REFI: 'Bridge Refi',
  CAPEX_BRIDGE_NOTE: 'Capex Bridge',
};

function getDealActions(deal: any, dday: number | null): { action: string; cta: string; color: string }[] {
  const actions: { action: string; cta: string; color: string }[] = [];
  if (deal.final_gate === 'HOLD') actions.push({ action: 'HOLD 해제 조건 입력', cta: 'HOLD 해제', color: C.amber });
  if ((deal.evidence_total || 0) === 0) actions.push({ action: '실사 체크리스트 생성', cta: '체크리스트 시작', color: C.blue });
  if (dday !== null && dday < 30 && dday >= 0) actions.push({ action: `만기 ${dday}일 전 의사결정 등록`, cta: '딜 확인', color: C.red });
  if (dday !== null && dday < 0) actions.push({ action: '만기 초과 — 회수 조치 필요', cta: '딜 확인', color: C.red });
  return actions;
}

function DealCard({ deal, onClick }: { deal: any; onClick: () => void }) {
  const maturity = deal.maturity_date ? new Date(deal.maturity_date) : null;
  const dday = maturity && !isNaN(maturity.getTime()) ? Math.ceil((maturity.getTime() - Date.now()) / 86400000) : null;
  const exp = deal.exposure_amount;
  const ddColor = dday !== null && dday < 14 ? C.red : dday !== null && dday < 90 ? C.amber : C.textDim;
  const typeLabel = DEAL_TYPE_LABEL[deal.deal_type] || deal.deal_type || '—';
  const done = deal.evidence_completed || 0;
  const total = deal.evidence_total || 0;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  const barColor = pct === 0 ? C.textDim : pct < 50 ? C.amber : pct < 100 ? C.blue : C.green;
  const actions = getDealActions(deal, dday);
  const primaryAction = actions[0];

  return (
    <div onClick={onClick} style={{
      background: C.surface, border: `1px solid ${primaryAction ? C.amber : C.border}`,
      borderLeft: `3px solid ${primaryAction?.color || C.border}`,
      borderRadius: 8, padding: '14px 18px', cursor: 'pointer', marginBottom: 10,
    }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = '#2E3A4A')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = primaryAction ? C.amber : C.border)}>

      {/* 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 5 }}>
            {deal.deal_name || deal.deal_code}
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: '#1A2535', color: C.blue }}>{typeLabel}</span>
            {deal.final_gate && (
              <span style={{ fontSize: 10, padding: '2px 8px', borderRadius: 12, background: deal.final_gate === 'HOLD' ? '#2A1A00' : '#0A1F0A', color: deal.final_gate === 'HOLD' ? C.amber : C.green }}>{deal.final_gate}</span>
            )}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          {exp && <div style={{ fontSize: 13, color: C.text, fontWeight: 600 }}>{(exp / 100000000).toFixed(0)}억</div>}
          {dday !== null && (
            <div style={{ fontSize: 11, color: ddColor, marginTop: 2 }}>
              {dday < 0 ? `만기 D+${Math.abs(dday)}` : `만기 D-${dday}`}
            </div>
          )}
        </div>
      </div>

      {/* 진행바 */}
      <div style={{ marginBottom: 8 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: C.textDim }}>실사 체크리스트</span>
          <span style={{ fontSize: 11, color: C.textMid }}>{done}/{total} · {pct}%</span>
        </div>
        <div style={{ background: C.border, borderRadius: 4, height: 4 }}>
          <div style={{ width: `${pct}%`, height: '100%', background: barColor, borderRadius: 4 }} />
        </div>
      </div>

      {/* 막힌 이유 / 다음 액션 */}
      {primaryAction && (
        <div style={{ fontSize: 11, color: primaryAction.color, marginTop: 4 }}>
          → {primaryAction.action}
        </div>
      )}
      {pct === 0 && total === 0 && !primaryAction && (
        <div style={{ fontSize: 11, color: C.textDim, marginTop: 4 }}>
          Tip — 아직 체크리스트가 생성되지 않았습니다
        </div>
      )}
    </div>
  );
}

export default function Dashboard({ onNavigateDeal }: { onNavigateDeal: (id: string, action?: string) => void }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token') || '';
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetch(`${API_BASE}/api/risk-book/deals`, { headers })
      .then(r => r.json())
      .then(data => { setDeals(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const dateStr = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' });

  // 우선순위 액션 생성
  const priorityActions: { dealName: string; dealCode: string; action: string; color: string }[] = [];
  deals.forEach(deal => {
    const maturity = deal.maturity_date ? new Date(deal.maturity_date) : null;
    const dday = maturity && !isNaN(maturity.getTime()) ? Math.ceil((maturity.getTime() - Date.now()) / 86400000) : null;
    const actions = getDealActions(deal, dday);
    actions.forEach(a => priorityActions.push({ dealName: deal.deal_name || deal.deal_code, dealCode: deal.deal_code, action: a.action, color: a.color }));
  });

  if (loading) return <div style={{ padding: 48, color: C.textDim, fontSize: 13 }}>로딩 중...</div>;

  return (
    <div style={{ width: '100%', maxWidth: 1400, margin: '0 auto', padding: '24px 40px', boxSizing: 'border-box' }}>

      {/* 상단 헤더 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 28 }}>
        <div>
          <div style={{ fontSize: 11, color: C.textDim, marginBottom: 4 }}>COSMOS / TODAY</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: C.text }}>{dateStr}</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={() => onNavigateDeal('new', 'intake')}
            style={{ padding: '8px 20px', background: C.amber, border: 'none', borderRadius: 6, color: '#0A0E14', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
            + 딜 등록
          </button>
          <button onClick={() => onNavigateDeal('pipeline', 'pipeline')}
            style={{ padding: '8px 20px', background: 'transparent', border: `1px solid ${C.border}`, borderRadius: 6, color: C.textMid, fontSize: 13, cursor: 'pointer' }}>
            파이프라인 전체
          </button>
        </div>
      </div>

      {/* 2컬럼 */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: 24 }}>

        {/* 좌측: 딜 카드 */}
        <div>
          <div style={{ fontSize: 11, color: C.textDim, letterSpacing: '0.08em', marginBottom: 12 }}>딜 현황</div>
          {deals.length === 0 ? (
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: '40px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: C.textDim, marginBottom: 12 }}>등록된 딜 없음</div>
              <button onClick={() => onNavigateDeal('new', 'intake')}
                style={{ padding: '8px 20px', background: C.amber, border: 'none', borderRadius: 6, color: '#0A0E14', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                첫 딜 등록하기
              </button>
            </div>
          ) : deals.map(deal => (
            <DealCard key={deal.deal_code} deal={deal} onClick={() => onNavigateDeal(deal.deal_code, 'pipeline')} />
          ))}
        </div>

        {/* 우측: 우선순위 액션 */}
        <div>
          <div style={{ fontSize: 11, color: C.textDim, letterSpacing: '0.08em', marginBottom: 12 }}>우선순위 액션</div>

          {priorityActions.length === 0 ? (
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: '20px', textAlign: 'center' }}>
              <div style={{ fontSize: 13, color: C.green }}>✓ 오늘 긴급 액션 없음</div>
            </div>
          ) : (
            priorityActions.slice(0, 6).map((item, i) => (
              <div key={i} onClick={() => onNavigateDeal(item.dealCode, 'pipeline')}
                style={{ background: C.surface, border: `1px solid ${C.border}`, borderLeft: `3px solid ${item.color}`, borderRadius: 8, padding: '12px 16px', marginBottom: 8, cursor: 'pointer' }}>
                <div style={{ fontSize: 11, color: C.textDim, marginBottom: 3 }}>{item.dealName}</div>
                <div style={{ fontSize: 13, color: item.color, fontWeight: 500 }}>{item.action}</div>
              </div>
            ))
          )}

          {/* 빠른 이동 */}
          <div style={{ marginTop: 20 }}>
            <div style={{ fontSize: 11, color: C.textDim, letterSpacing: '0.08em', marginBottom: 10 }}>빠른 이동</div>
            {[
              { label: '딜 소싱 / Signal Room', action: 'sourcing' },
              { label: '증빙 체크리스트', action: 'evidence' },
            ].map(item => (
              <div key={item.action} onClick={() => onNavigateDeal(item.action, item.action)}
                style={{ padding: '10px 14px', marginBottom: 8, background: C.surface, border: `1px solid ${C.border}`, borderRadius: 6, cursor: 'pointer', fontSize: 12, color: C.textMid }}>
                {item.label} →
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
