import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';

const API = process.env.REACT_APP_API_URL || 'https://project-cosmos-production.up.railway.app';

const CHANNELS = ['전화', '이메일', '대면', '카카오톡', '문자'];
const DIRECTIONS = ['인바운드', '아웃바운드'];
const COUNTERPARTIES = ['신한은행', '경남은행', '김앤장', '패스트파이브', '증권사 PI', '공제회', '기타'];

export default function ContactLog() {
  const { dealId } = useParams<{ dealId: string }>();
  const [logs, setLogs] = useState<any[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    contact_date: new Date().toISOString().slice(0, 10),
    contact_time: new Date().toTimeString().slice(0, 5),
    channel: '전화',
    counterparty: '',
    direction: '인바운드',
    outcome: '',
    summary: '',
    next_action: '',
    next_action_date: '',
    sensitivity: 'NORMAL',
  });

  const token = localStorage.getItem('token');
  const headers = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' };

  useEffect(() => {
    if (!dealId) return;
    fetch(`${API}/deals/${dealId}/contact-log`, { headers })
      .then(r => r.json()).then(setLogs).catch(() => {});
  }, [dealId]);

  const handleSubmit = async () => {
    if (!form.counterparty || !form.outcome) return alert('카운터파티와 결과는 필수입니다');
    setSaving(true);
    try {
      const r = await fetch(`${API}/deals/${dealId}/contact-log`, {
        method: 'POST', headers, body: JSON.stringify(form)
      });
      const data = await r.json();
      setLogs([data, ...logs]);
      setShowForm(false);
      setForm(f => ({ ...f, summary: '', outcome: '', next_action: '', counterparty: '' }));
    } catch (e) { alert('저장 실패'); }
    setSaving(false);
  };

  return (
    <div style={{ padding: '24px', maxWidth: '800px', margin: '0 auto', color: '#e2e8f0' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 600 }}>Contact Log — {dealId}</h2>
        <button onClick={() => setShowForm(!showForm)}
          style={{ background: '#d4af37', color: '#0a0a0f', padding: '8px 16px', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
          + 통화/접촉 기록
        </button>
      </div>

      {showForm && (
        <div style={{ background: '#1a1a2e', border: '1px solid #2d2d44', borderRadius: '8px', padding: '20px', marginBottom: '24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>날짜</label>
              <input type="date" value={form.contact_date}
                onChange={e => setForm(f => ({ ...f, contact_date: e.target.value }))}
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>시간</label>
              <input type="time" value={form.contact_time}
                onChange={e => setForm(f => ({ ...f, contact_time: e.target.value }))}
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>채널</label>
              <select value={form.channel} onChange={e => setForm(f => ({ ...f, channel: e.target.value }))}
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }}>
                {CHANNELS.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>방향</label>
              <select value={form.direction} onChange={e => setForm(f => ({ ...f, direction: e.target.value }))}
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }}>
                {DIRECTIONS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div style={{ gridColumn: 'span 2' }}>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>카운터파티 *</label>
              <input list="counterparty-list" value={form.counterparty}
                onChange={e => setForm(f => ({ ...f, counterparty: e.target.value }))}
                placeholder="신한은행, 경남은행, 패스트파이브..."
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
              <datalist id="counterparty-list">{COUNTERPARTIES.map(c => <option key={c} value={c} />)}</datalist>
            </div>
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>결과 요약 *</label>
            <input value={form.outcome} onChange={e => setForm(f => ({ ...f, outcome: e.target.value }))}
              placeholder="채권잔액 116억 구두 확인, 신탁원부 요청..."
              style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>상세 내용</label>
            <textarea value={form.summary} onChange={e => setForm(f => ({ ...f, summary: e.target.value }))}
              rows={3} placeholder="통화 상세 내용..."
              style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px', resize: 'vertical' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>다음 액션</label>
              <input value={form.next_action} onChange={e => setForm(f => ({ ...f, next_action: e.target.value }))}
                placeholder="신탁원부 수령, 감정평가 요청..."
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
            </div>
            <div>
              <label style={{ fontSize: '12px', color: '#94a3b8', display: 'block', marginBottom: '4px' }}>액션 기한</label>
              <input type="date" value={form.next_action_date}
                onChange={e => setForm(f => ({ ...f, next_action_date: e.target.value }))}
                style={{ width: '100%', background: '#0a0a0f', border: '1px solid #2d2d44', color: '#e2e8f0', padding: '8px', borderRadius: '4px' }} />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleSubmit} disabled={saving}
              style={{ background: '#d4af37', color: '#0a0a0f', padding: '10px 20px', borderRadius: '6px', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
              {saving ? '저장 중...' : '저장'}
            </button>
            <button onClick={() => setShowForm(false)}
              style={{ background: 'transparent', color: '#94a3b8', padding: '10px 20px', borderRadius: '6px', border: '1px solid #2d2d44', cursor: 'pointer' }}>
              취소
            </button>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {logs.length === 0 && <div style={{ color: '#64748b', textAlign: 'center', padding: '40px' }}>기록 없음</div>}
        {logs.map((log: any) => (
          <div key={log.id} style={{ background: '#1a1a2e', border: '1px solid #2d2d44', borderRadius: '8px', padding: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#d4af37' }}>{log.counterparty}</span>
              <span style={{ fontSize: '12px', color: '#64748b' }}>{log.contact_date} {log.contact_time}</span>
            </div>
            <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>
              [{log.direction}] {log.channel} — {log.outcome}
            </div>
            {log.summary && <div style={{ fontSize: '13px', color: '#cbd5e1', marginTop: '8px' }}>{log.summary}</div>}
            {log.next_action && (
              <div style={{ marginTop: '8px', padding: '8px', background: '#0a0a0f', borderRadius: '4px', fontSize: '12px', color: '#fbbf24' }}>
                → {log.next_action} {log.next_action_date && `(${log.next_action_date})`}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
