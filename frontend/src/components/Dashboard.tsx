import { useState, useEffect } from 'react';
import PipelineCard from './DealCard';
import SddDealDetail from '../pages/SddDealDetail';

const API_BASE = 'https://project-cosmos-production.up.railway.app';

const C = {
  bg: '#0A0E14', surface: '#11161D', border: '#1E2630',
  text: '#E4E7EB', textMid: '#8B95A3', textDim: '#525C6B',
  amber: '#F0A93B', red: '#E5484D', green: '#2BC48A', blue: '#6FA8FF',
};

function getDealActions(deal: any, dday: number | null): { action: string; cta: string; color: string; tab: string }[] {
  const actions: { action: string; cta: string; color: string; tab: string }[] = [];
  if (deal.final_gate === 'HOLD') actions.push({ action: 'HOLD 해제 조건 입력', cta: 'HOLD 해제', color: C.amber, tab: 'status' });
  if ((deal.evidence_total || 0) === 0) actions.push({ action: '실사 체크리스트 생성', cta: '체크리스트 시작', color: C.blue, tab: 'checklist' });
  if (dday !== null && dday < 30 && dday >= 0) actions.push({ action: `만기 ${dday}일 전 의사결정 등록`, cta: '딜 확인', color: C.red, tab: 'status' });
  if (dday !== null && dday < 0) actions.push({ action: '만기 초과 — 회수 조치 필요', cta: '딜 확인', color: C.red, tab: 'status' });
  return actions;
}


export default function Dashboard({ onNavigateDeal }: { onNavigateDeal: (id: string, action?: string) => void }) {
  const [deals, setDeals] = useState<any[]>([]);
  const [pipelineDeals, setPipelineDeals] = useState<any[]>([]);
  const [detailDealId, setDetailDealId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const token = localStorage.getItem('token') || '';
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    // 우측 우선순위 액션용 (전체 risk-book 딜)
    fetch(`${API_BASE}/api/risk-book/deals`, { headers })
      .then(r => r.json())
      .then(data => { setDeals(Array.isArray(data) ? data : []); setLoading(false); })
      .catch(() => setLoading(false));
    // 좌측 카드용 (Kill Check PASS 딜)
    fetch(`${API_BASE}/deals/dashboard`, { headers })
      .then(r => r.json())
      .then(data => setPipelineDeals(Array.isArray(data?.deals) ? data.deals : []))
      .catch(() => {});
  }, []);

  const dateStr = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' });

  // 우선순위 액션 생성
  const priorityActions: { dealName: string; dealCode: string; action: string; color: string; tab: string }[] = [];
  deals.forEach(deal => {
    const maturity = deal.maturity_date ? new Date(deal.maturity_date) : null;
    const dday = maturity && !isNaN(maturity.getTime()) ? Math.ceil((maturity.getTime() - Date.now()) / 86400000) : null;
    const actions = getDealActions(deal, dday);
    actions.forEach(a => priorityActions.push({ dealName: deal.deal_name || deal.deal_code, dealCode: deal.deal_code, action: a.action, color: a.color, tab: a.tab }));
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
          {pipelineDeals.length === 0 ? (
            <div style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: 8, padding: '40px 24px', textAlign: 'center' }}>
              <div style={{ fontSize: 14, color: C.textDim, marginBottom: 12 }}>등록된 딜 없음</div>
              <button onClick={() => onNavigateDeal('new', 'intake')}
                style={{ padding: '8px 20px', background: C.amber, border: 'none', borderRadius: 6, color: '#0A0E14', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
                첫 딜 등록하기
              </button>
            </div>
          ) : pipelineDeals.map(deal => (
            <PipelineCard
              key={deal.deal_code}
              dealCode={deal.deal_code}
              dealType={deal.deal_type}
              thesis={deal.thesis}
              stage={deal.stage}
              closingPct={0}
              onView={() => setDetailDealId(deal.id)}
            />
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
              <div key={i} onClick={() => onNavigateDeal(item.dealCode, item.tab)}
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
      {detailDealId && (
        <SddDealDetail dealId={detailDealId} onClose={() => setDetailDealId(null)} />
      )}
    </div>
  );
}
