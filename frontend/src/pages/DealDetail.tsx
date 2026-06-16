import React, { useEffect, useState } from 'react';
import API from '../api';
import { DealDetail as DD } from '../types';

const STATUS_COLOR: any = { INTAKE: '#888', SCREENED: '#185FA5', WATCHLIST: '#854F0B', ADVANCE: '#3B6D11', REJECT: '#A32D2D' };
const STATUS_BG: any = { INTAKE: '#F1EFE8', SCREENED: '#E6F1FB', WATCHLIST: '#FAEEDA', ADVANCE: '#EAF3DE', REJECT: '#FCEBEB' };
const STATUSES = ['INTAKE','SCREENED','WATCHLIST','ADVANCE','REJECT'];

const HK_COLOR = (v: string) => {
  const l = (v||'').toLowerCase();
  if (l.includes('critical') || l.startsWith('red')) return { color: '#A32D2D', bg: '#FCEBEB', label: 'CRITICAL' };
  if (l.includes('amber') || l.includes('unknown')) return { color: '#854F0B', bg: '#FAEEDA', label: 'UNKNOWN' };
  if (l === 'green' || l.includes('clear')) return { color: '#3B6D11', bg: '#EAF3DE', label: 'CLEAR' };
  return { color: '#888', bg: '#F5F5F5', label: 'TBC' };
};

const HK_LABELS: any = {
  tax_risk: '국세/지방세 우선권',
  tenant_risk: '임차인 리스크',
  possessory_lien: '유치권/점유',
  trust_structure: '신탁 구조',
  litigation: '소송/분쟁',
  building_violation: '건축법 위반'
};

export default function DealDetail({ dealId, onBack }: { dealId: string; onBack: () => void }) {
  const [deal, setDeal] = useState<DD | null>(null);
  const [tab, setTab] = useState('overview');
  const [newStatus, setNewStatus] = useState('');
  const [reason, setReason] = useState('');
  const [actionTag, setActionTag] = useState('');
  const [nextAction, setNextAction] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    API.get(`/deals/${dealId}`).then(r => { setDeal(r.data); setNewStatus(r.data.status); });
  }, [dealId]);

  const saveStatus = async () => {
    if (!reason) { setMsg('Decision Reason 필수'); return; }
    setSaving(true);
    await API.patch(`/deals/${dealId}/status`, { status: newStatus, reason, action_tag: actionTag, next_action: nextAction });
    const r = await API.get(`/deals/${dealId}`);
    setDeal(r.data); setMsg('완료'); setSaving(false);
  };

  if (!deal) return <div style={{ padding: 40, color: '#999', fontSize: 13 }}>불러오는 중...</div>;
  const rec = deal.deal_record || {};
  const hk = rec.hard_kill || {};

  const criticalCount = Object.values(hk).filter((v: any) => (v||'').toLowerCase().includes('critical')).length;
  const unknownCount = Object.values(hk).filter((v: any) => (v||'').toLowerCase().includes('unknown')).length;

  return (
    <div style={{ padding: '28px 36px', maxWidth: 960 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 24 }}>
        <button onClick={onBack} style={{ background: 'none', border: '0.5px solid #ddd', borderRadius: 6, padding: '5px 12px', fontSize: 12, cursor: 'pointer', color: '#666', marginTop: 4 }}>← 뒤로</button>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, color: '#bbb', marginBottom: 4, fontFamily: 'monospace' }}>{deal.id}</div>
          <div style={{ fontSize: 20, fontWeight: 600, letterSpacing: -0.3 }}>{rec.asset_name || '—'}</div>
          <div style={{ fontSize: 13, color: '#888', marginTop: 3 }}>{rec.asset_address}</div>
        </div>
        <span style={{ background: STATUS_BG[deal.status], color: STATUS_COLOR[deal.status], padding: '4px 12px', borderRadius: 20, fontSize: 11, fontWeight: 600 }}>
          {deal.status}
        </span>
      </div>

      {/* KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'DSCR', value: rec.dscr || 'Unknown', alert: rec.dscr && parseFloat(rec.dscr) < 1.0 },
          { label: '채권 잔액', value: rec.current_balance || 'Unknown', alert: false },
          { label: 'Hard Kill Critical', value: `${criticalCount}개`, alert: criticalCount > 0 },
          { label: 'Missing Data', value: `${(rec.missing_data||[]).length}개`, alert: (rec.missing_data||[]).length > 0 },
        ].map(({ label, value, alert }) => (
          <div key={label} style={{ background: alert ? '#FAFAF7' : '#fff', border: `0.5px solid ${alert ? '#FAC775' : '#e5e5e5'}`, borderRadius: 10, padding: '14px 16px' }}>
            <div style={{ fontSize: 11, color: '#999', marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 16, fontWeight: 600, color: alert ? '#854F0B' : '#000' }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Verdict Block */}
      {rec.luska_verdict && (
        <div style={{ background: '#F7F7F5', border: '0.5px solid #e0e0e0', borderRadius: 10, padding: '16px 20px', marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: '#999', marginBottom: 8, fontWeight: 600, letterSpacing: 0.5 }}>◈ LUSKA VERDICT</div>
          <div style={{ fontSize: 13, color: '#222', lineHeight: 1.6 }}>{rec.luska_verdict}</div>
          {rec.initial_routing && (
            <div style={{ marginTop: 10, fontSize: 12, color: '#185FA5' }}>
              <span style={{ color: '#999' }}>Routing: </span>{rec.initial_routing}
            </div>
          )}
          {rec.next_action && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#3B6D11' }}>
              <span style={{ color: '#999' }}>Next Action: </span>{rec.next_action}
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '0.5px solid #e5e5e5', marginBottom: 24 }}>
        {[['overview','딜 레코드'],['hardkill','Hard Kill'],['recovery','Recovery'],['status','상태 변경'],['history','이력']].map(([t,label]) => (
          <div key={t} onClick={() => setTab(t)}
            style={{ padding: '8px 16px', fontSize: 13, cursor: 'pointer', borderBottom: tab===t ? '2px solid #000' : '2px solid transparent', fontWeight: tab===t ? 600 : 400, color: tab===t ? '#000' : '#888' }}>
            {label}
          </div>
        ))}
      </div>

      {/* Tab: 딜 레코드 */}
      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
          <div>
            <div style={{ fontSize: 11, color: '#999', fontWeight: 600, letterSpacing: 0.5, marginBottom: 12 }}>기본 정보</div>
            {[['자산 유형','asset_type'],['채권자','creditor'],['차주','borrower'],['소유자','owner'],['담보순위','lien_rank'],['만기','maturity'],['연체','delinquency_status'],['LTV','ltv']].map(([label,key]) => (
              <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '0.5px solid #f0f0f0', fontSize: 13 }}>
                <span style={{ color: '#888' }}>{label}</span>
                <span style={{ fontWeight: 500, maxWidth: 200, textAlign: 'right', color: rec[key]?.toLowerCase?.().startsWith('unknown') ? '#bbb' : '#000' }}>{rec[key] || 'Unknown'}</span>
              </div>
            ))}
          </div>
          <div>
            <div style={{ fontSize: 11, color: '#999', fontWeight: 600, letterSpacing: 0.5, marginBottom: 12 }}>Control & Evidence</div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Control Lever</div>
            <div style={{ fontSize: 13, marginBottom: 16, padding: '10px 12px', background: '#F7F7F5', borderRadius: 8 }}>{rec.control_lever || 'Unknown'}</div>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Distress Signal</div>
            <div style={{ fontSize: 13, marginBottom: 16, padding: '10px 12px', background: '#F7F7F5', borderRadius: 8 }}>{rec.distress_signal || 'Unknown'}</div>
            {(rec.evidence_gaps||[]).length > 0 && (
              <>
                <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Evidence Gaps</div>
                {rec.evidence_gaps.map((g: string, i: number) => (
                  <div key={i} style={{ fontSize: 12, color: '#854F0B', padding: '3px 0' }}>⚠ {g}</div>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Tab: Hard Kill */}
      {tab === 'hardkill' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20 }}>
            {Object.entries(hk).map(([k, v]: any) => {
              const { color, bg, label } = HK_COLOR(v);
              return (
                <div key={k} style={{ background: '#fff', border: '0.5px solid #e5e5e5', borderRadius: 10, padding: '14px 16px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{HK_LABELS[k] || k}</div>
                    <span style={{ background: bg, color, padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 600 }}>{label}</span>
                  </div>
                  <div style={{ fontSize: 12, color: '#666', lineHeight: 1.5 }}>{v}</div>
                </div>
              );
            })}
          </div>
          {(rec.missing_data||[]).length > 0 && (
            <div style={{ background: '#FAEEDA', border: '0.5px solid #FAC775', borderRadius: 10, padding: '14px 16px' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#854F0B', marginBottom: 8 }}>Missing Data ({rec.missing_data.length}개)</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                {rec.missing_data.map((m: string) => <div key={m} style={{ fontSize: 12, color: '#854F0B' }}>⚠ {m}</div>)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab: Recovery */}
      {tab === 'recovery' && (
        <div>
          <div style={{ fontSize: 11, color: '#999', fontWeight: 600, letterSpacing: 0.5, marginBottom: 16 }}>RECOVERY PATHS</div>
          {(rec.recovery_paths||[]).length === 0 ? (
            <div style={{ color: '#bbb', fontSize: 13 }}>Recovery Path 없음</div>
          ) : (
            rec.recovery_paths.map((p: string, i: number) => (
              <div key={i} style={{ background: '#fff', border: '0.5px solid #e5e5e5', borderRadius: 10, padding: '14px 16px', marginBottom: 10, display: 'flex', gap: 12 }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: '#e5e5e5', minWidth: 28 }}>0{i+1}</div>
                <div style={{ fontSize: 13, color: '#333', lineHeight: 1.6 }}>{p}</div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Tab: 상태 변경 */}
      {tab === 'status' && (
        <div style={{ maxWidth: 480 }}>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>새 상태</div>
            <select value={newStatus} onChange={e => setNewStatus(e.target.value)}
              style={{ width: '100%', padding: '9px 12px', border: '0.5px solid #ddd', borderRadius: 8, fontSize: 13, outline: 'none' }}>
              {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Action Tag</div>
            <input value={actionTag} onChange={e => setActionTag(e.target.value)} placeholder="예: Bank routing candidate"
              style={{ width: '100%', padding: '9px 12px', border: '0.5px solid #ddd', borderRadius: 8, fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: 14 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Next Action</div>
            <input value={nextAction} onChange={e => setNextAction(e.target.value)} placeholder="예: 국세 체납 여부 확인 요청"
              style={{ width: '100%', padding: '9px 12px', border: '0.5px solid #ddd', borderRadius: 8, fontSize: 13, outline: 'none', boxSizing: 'border-box' }} />
          </div>
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>Decision Reason ★</div>
            <textarea value={reason} onChange={e => setReason(e.target.value)} placeholder="판단 근거를 기록하세요."
              style={{ width: '100%', height: 100, padding: '9px 12px', border: '0.5px solid #ddd', borderRadius: 8, fontSize: 13, outline: 'none', resize: 'vertical', fontFamily: 'inherit', boxSizing: 'border-box' }} />
          </div>
          {msg && <div style={{ fontSize: 12, color: '#3B6D11', marginBottom: 12 }}>{msg}</div>}
          <button onClick={saveStatus} disabled={saving}
            style={{ padding: '10px 24px', background: '#000', color: '#fff', border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 500, cursor: 'pointer' }}>
            {saving ? '저장 중...' : '상태 변경 저장'}
          </button>
        </div>
      )}

      {/* Tab: 이력 */}
      {tab === 'history' && (
        <div>
          {[...(deal.status_history||[])].reverse().map((h: any, i: number) => (
            <div key={i} style={{ borderLeft: '2px solid #e5e5e5', paddingLeft: 16, marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                <span style={{ background: STATUS_BG[h.status], color: STATUS_COLOR[h.status], padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 }}>{h.status}</span>
                <span style={{ fontSize: 11, color: '#bbb' }}>{h.timestamp?.slice(0,16).replace('T',' ')}</span>
              </div>
              <div style={{ fontSize: 13, color: '#444' }}>{h.reason}</div>
              {h.changed_by && <div style={{ fontSize: 11, color: '#bbb', marginTop: 3 }}>{h.changed_by}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
