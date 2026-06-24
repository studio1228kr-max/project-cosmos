import { useState, useEffect, useCallback } from 'react';
import API from '../api';

interface ChecklistItem {
  id: number;
  evidence_item_code: string;
  evidence_item_label: string | null;
  requirement_level: string;
  gate_blocking: boolean;
  status: string;
  dd_tier: string;
  tier_label: string;
  waived_by: string | null;
  waiver_expires_at: string | null;
}

interface Counts {
  total: number;
  done: number;
  mandatory_total: number;
  mandatory_done: number;
}

const LEVELS = ['SDD', 'CDD', 'EDD'];

const levelLabel: Record<string, string> = {
  SDD: 'Simplified DD',
  CDD: 'Standard DD',
  EDD: 'Enhanced DD',
};

// 인라인 상태 변경 (면제는 증빙 체크리스트 페이지의 Waiver 모달에서 처리)
const STATUS_OPTIONS = [
  { code: 'MISSING', label: '미확보' },
  { code: 'RECEIVED', label: '수령' },
  { code: 'VERIFIED', label: '검증완료' },
];

const statusColor: Record<string, string> = {
  MISSING: '#dc2626',
  RECEIVED: '#d97706',
  VERIFIED: '#16a34a',
  WAIVED: '#6366f1',
};

const EMPTY_COUNTS: Counts = { total: 0, done: 0, mandatory_total: 0, mandatory_done: 0 };

export default function ChecklistPanel({ dealCode }: { dealCode: string }) {
  const [level, setLevel] = useState('');
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [counts, setCounts] = useState<Counts>(EMPTY_COUNTS);
  const [loading, setLoading] = useState(false);

  const load = useCallback((tier?: string) => {
    setLoading(true);
    const qs = tier ? `?dd_tier=${tier}` : '';
    API.get(`/api/risk-book/deals/${dealCode}/checklist${qs}`)
      .then(r => {
        setItems(Array.isArray(r.data.checklist) ? r.data.checklist : []);
        setCounts(r.data.counts || EMPTY_COUNTS);
        setLevel(r.data.dd_tier || tier || 'CDD');
      })
      .catch(() => { setItems([]); setCounts(EMPTY_COUNTS); })
      .finally(() => setLoading(false));
  }, [dealCode]);

  // 최초 진입: 딜의 현재 티어로 로드 (탭도 그 티어로 활성화)
  useEffect(() => { load(); }, [load]);

  const selectLevel = (lv: string) => { setLevel(lv); load(lv); };

  const updateStatus = (code: string, status: string) => {
    API.patch(`/api/risk-book/deals/${dealCode}/checklist/${code}`, { status })
      .then(() => load(level))
      .catch(() => {});
  };

  // 티어별 그룹
  const groups: Record<string, ChecklistItem[]> = {};
  items.forEach(item => {
    const key = `${item.dd_tier} · ${item.tier_label || levelLabel[item.dd_tier] || ''}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  });

  const pct = counts.mandatory_total > 0
    ? Math.round((counts.mandatory_done / counts.mandatory_total) * 100)
    : 0;

  return (
    <div style={{ padding: '0 0 40px' }}>
      {/* 티어 탭 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {LEVELS.map(lv => (
          <button key={lv} onClick={() => selectLevel(lv)}
            style={{
              padding: '6px 16px', fontSize: 12, fontWeight: level === lv ? 700 : 400,
              background: level === lv ? '#111' : '#f5f5f5',
              color: level === lv ? '#fff' : '#555',
              border: 'none', borderRadius: 6, cursor: 'pointer'
            }}
            title={levelLabel[lv]}>
            {lv}
          </button>
        ))}
      </div>

      {/* 카운트 요약 (0/0 버그 자리) */}
      <div style={{ background: '#f9f9f9', border: '1px solid #e5e5e5', borderRadius: 8, padding: '12px 16px', marginBottom: 20, display: 'flex', gap: 24, alignItems: 'center' }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: pct === 100 ? '#16a34a' : '#d97706' }}>
          필수 {counts.mandatory_done} / {counts.mandatory_total}
        </span>
        <span style={{ fontSize: 12, color: '#666' }}>완료율 {pct}%</span>
        <span style={{ fontSize: 12, color: '#666' }}>전체 {counts.done} / {counts.total} 항목</span>
        <span style={{ fontSize: 11, color: '#999' }}>티어 {level}</span>
      </div>

      {loading && <div style={{ color: '#999', fontSize: 13 }}>로딩 중...</div>}
      {!loading && items.length === 0 && (
        <div style={{ color: '#999', fontSize: 13 }}>이 티어에 해당하는 체크리스트 항목이 없습니다.</div>
      )}

      {/* 티어별 항목 */}
      {Object.entries(groups).map(([groupName, groupItems]) => (
        <div key={groupName} style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#444', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {groupName}
          </div>
          {groupItems.map(item => (
            <div key={item.evidence_item_code} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '8px 12px', marginBottom: 4,
              background: item.gate_blocking ? '#fff5f5' : '#fff',
              border: `1px solid ${item.gate_blocking ? '#fecaca' : '#f0f0f0'}`,
              borderRadius: 6
            }}>
              {item.gate_blocking && <span style={{ fontSize: 10, color: '#dc2626' }} title="게이트 차단 항목">⛔</span>}
              <span style={{ flex: 1, fontSize: 13, color: '#222' }}>
                {item.evidence_item_label || item.evidence_item_code}
              </span>
              <span style={{ fontSize: 10, color: '#999' }}>{item.requirement_level}</span>
              {item.status === 'WAIVED' ? (
                <span style={{ fontSize: 11, fontWeight: 600, color: statusColor.WAIVED }}
                  title={`승인: ${item.waived_by || '-'} · 만료: ${item.waiver_expires_at || '-'}`}>
                  면제
                </span>
              ) : (
                <select
                  value={item.status}
                  onChange={e => updateStatus(item.evidence_item_code, e.target.value)}
                  style={{
                    fontSize: 11, padding: '2px 6px', borderRadius: 4,
                    border: '1px solid #ddd', background: '#fff',
                    color: statusColor[item.status] || '#9ca3af',
                    fontWeight: 600, cursor: 'pointer'
                  }}>
                  {STATUS_OPTIONS.map(s => (
                    <option key={s.code} value={s.code}>{s.label}</option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
