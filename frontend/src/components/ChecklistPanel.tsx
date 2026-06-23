import { useState, useEffect } from 'react';

const API = 'https://project-cosmos-production.up.railway.app';

interface ChecklistItem {
  id: number;
  item_code: string;
  dd_level: string;
  section_code: string;
  section_name: string;
  item_label: string;
  status: string;
  kill_switch: boolean;
  auto_fillable: boolean;
  auto_source: string | null;
  gate_blocking: boolean;
}

const LEVELS = ['SDD', 'CDD', 'EDD'];

const levelLabel: Record<string, string> = {
  SDD: 'Simplified DD',
  CDD: 'Standard DD',
  EDD: 'Enhanced DD',
};

const statusColor: Record<string, string> = {
  PASS: '#16a34a',
  FAIL: '#dc2626',
  INCOMPLETE: '#d97706',
  PENDING: '#9ca3af',
  WAIVED: '#6366f1',
};

const statusLabel: Record<string, string> = {
  PASS: 'PASS',
  FAIL: 'FAIL',
  INCOMPLETE: 'INCOMPLETE',
  PENDING: '⚪ PENDING',
  WAIVED: 'WAIVED',
};

export default function ChecklistPanel({ dealCode }: { dealCode: string }) {
  const [level, setLevel] = useState('SDD');
  const [items, setItems] = useState<ChecklistItem[]>([]);
  const [gate, setGate] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const token = localStorage.getItem('token') || '';

  const fetchItems = async (lv: string) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/checklist/deal/${dealCode}?dd_level=${lv}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setItems([]);
    }
    setLoading(false);
  };

  const fetchGate = async (lv: string) => {
    try {
      const res = await fetch(`${API}/api/checklist/deal/${dealCode}/gate?dd_level=${lv}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await res.json();
      setGate(data);
    } catch (e) {}
  };

  useEffect(() => {
    fetchItems(level);
    fetchGate(level);
  }, [level, dealCode]);

  const updateStatus = async (item_code: string, status: string) => {
    await fetch(`${API}/api/checklist/deal/${dealCode}/${item_code}`, {
      method: 'PATCH',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    });
    fetchItems(level);
    fetchGate(level);
  };

  // 섹션별 그룹
  const sections: Record<string, ChecklistItem[]> = {};
  items.forEach(item => {
    const key = `${item.section_code}. ${item.section_name}`;
    if (!sections[key]) sections[key] = [];
    sections[key].push(item);
  });

  const gateColor = gate?.gate === 'PASS' ? '#16a34a' : gate?.gate === 'FAIL' ? '#dc2626' : '#d97706';

  return (
    <div style={{ padding: '0 0 40px' }}>
      {/* 레벨 탭 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        {LEVELS.map(lv => (
          <button key={lv} onClick={() => setLevel(lv)}
            style={{
              padding: '6px 16px', fontSize: 12, fontWeight: level === lv ? 700 : 400,
              background: level === lv ? '#111' : '#f5f5f5',
              color: level === lv ? '#fff' : '#555',
              border: 'none', borderRadius: 6, cursor: 'pointer'
            }}>
            {lv}
          </button>
        ))}
      </div>

      {/* 게이트 요약 */}
      {gate && (
        <div style={{ background: '#f9f9f9', border: '1px solid #e5e5e5', borderRadius: 8, padding: '12px 16px', marginBottom: 20, display: 'flex', gap: 24, alignItems: 'center' }}>
          <span style={{ fontWeight: 700, fontSize: 13, color: gateColor }}>{gate.gate}</span>
          <span style={{ fontSize: 12, color: '#666' }}>완료율 {gate.completion_pct}%</span>
          <span style={{ fontSize: 12, color: '#666' }}>{gate.done_items} / {gate.total_items} 항목</span>
          {gate.kill_triggered?.length > 0 && (
            <span style={{ fontSize: 12, color: '#dc2626' }}>⛔ Kill Switch {gate.kill_triggered.length}개</span>
          )}
        </div>
      )}

      {loading && <div style={{ color: '#999', fontSize: 13 }}>로딩 중...</div>}

      {/* 섹션별 체크리스트 */}
      {Object.entries(sections).map(([sectionName, sectionItems]) => (
        <div key={sectionName} style={{ marginBottom: 24 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#444', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {sectionName}
          </div>
          {sectionItems.map(item => (
            <div key={item.item_code} style={{
              display: 'flex', alignItems: 'center', gap: 12,
              padding: '8px 12px', marginBottom: 4,
              background: item.kill_switch ? '#fff5f5' : '#fff',
              border: `1px solid ${item.kill_switch ? '#fecaca' : '#f0f0f0'}`,
              borderRadius: 6
            }}>
              {item.kill_switch && <span style={{ fontSize: 10, color: '#dc2626' }}>⛔</span>}
              {item.auto_fillable && <span style={{ fontSize: 10, color: '#3b82f6' }} title={`자동: ${item.auto_source}`}>🔵</span>}
              <span style={{ flex: 1, fontSize: 13, color: '#222' }}>{item.item_label}</span>
              <select
                value={item.status || 'PENDING'}
                onChange={e => updateStatus(item.item_code, e.target.value)}
                style={{
                  fontSize: 11, padding: '2px 6px', borderRadius: 4,
                  border: '1px solid #ddd', background: '#fff',
                  color: statusColor[item.status] || '#9ca3af',
                  fontWeight: 600, cursor: 'pointer'
                }}>
                {['PENDING', 'PASS', 'FAIL', 'INCOMPLETE', 'WAIVED'].map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
