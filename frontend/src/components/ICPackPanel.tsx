import React, { useEffect, useState, useCallback } from 'react';
import API from '../api';

const REC_COLOR: any = {
  승인: { bg: '#EAF3DE', color: '#3B6D11' },
  CONDITIONAL_승인: { bg: '#FFF8E6', color: '#854F0B' },
  보류: { bg: '#F1EFE8', color: '#888' },
  부결: { bg: '#FCEBEB', color: '#A32D2D' },
  상정: { bg: '#E6F1FB', color: '#185FA5' },
};
const REC_LABEL: any = {
  승인: '승인', CONDITIONAL_승인: 'CONDITIONAL 승인',
  보류: '보류', 부결: '부결', 상정: '상정',
};
const REC_OPTIONS = ['승인','CONDITIONAL_승인','보류','부결','상정'];

export default function ICPackPanel({ dealCode }: { dealCode: string }) {
  const [pack, setPack] = useState<any>(null);
  const [irr, setIrr] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<any>({});
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchPack = useCallback(async () => {
    setLoading(true);
    try {
      const r = await API.get(`/api/ic-pack/${dealCode}`);
      setPack(r.data);
      setForm({
        preliminary_view: r.data.preliminary_view || '',
        failure_summary: r.data.failure_summary || '',
        counterparty_summary: r.data.counterparty_summary || '',
        valuation_notes: r.data.valuation_notes || '',
        principal_loss_band: r.data.principal_loss_band || '',
        recommendation: r.data.recommendation || '',
        conditions: r.data.conditions || [],
        key_risks: r.data.key_risks || [],
      });
      const ids = r.data.irr_result_ids || {};
      const irr데이터: any = {};
      for (const scenario of Object.keys(ids)) {
        try {
          const ir = await API.get(`/risk-book/deals/${dealCode}/irr?scenario=${scenario}`);
          irr데이터[scenario] = ir.data;
        } catch {}
      }
      setIrr(irr데이터);
    } catch (e: any) {
      if (e?.response?.status === 404) setPack(null);
    } finally { setLoading(false); }
  }, [dealCode]);

  useEffect(() => { fetchPack(); }, [fetchPack]);

  const createPack = async () => {
    setCreating(true);
    try { await API.post(`/api/ic-pack/${dealCode}/create`, {}); await fetchPack(); }
    catch {} finally { setCreating(false); }
  };

  const upd = (k: string, v: any) => { setForm((f: any) => ({ ...f, [k]: v })); setDirty(true); setSaveMsg(''); };

  const save = async () => {
    setSaving(true);
    try { await API.patch(`/api/ic-pack/${dealCode}`, form); setSaveMsg('저장 완료'); setDirty(false); await fetchPack(); }
    catch { setSaveMsg('저장 실패'); } finally { setSaving(false); }
  };

  if (loading) return <div style={{color:'#999',fontSize:13,padding:20}}>불러오는 중...</div>;

  if (!pack) return (
    <div style={{textAlign:'center',padding:40}}>
      <div style={{fontSize:13,color:'#999',marginBottom:16}}>IC Pack이 아직 없습니다.</div>
      <button onClick={createPack} disabled={creating}
        style={{padding:'10px 24px',background:'#000',color:'#fff',border:'none',borderRadius:8,fontSize:13,cursor:'pointer'}}>
        {creating ? '생성 중...' : 'IC Pack 생성'}
      </button>
    </div>
  );

  const rec = form.recommendation;
  const recStyle = REC_COLOR[rec] || {bg:'#F5F5F5',color:'#888'};
  const condOver = (form.conditions||[]).length > 5;

  const S = (label: string) => (
    <div style={{fontSize:10,color:'#bbb',fontWeight:600,letterSpacing:1,marginBottom:8}}>{label}</div>
  );
  const card = (children: any) => (
    <div style={{background:'#fff',border:'0.5px solid #e5e5e5',borderRadius:10,padding:'16px 20px',marginBottom:14}}>{children}</div>
  );
  const ta = (val: string, key: string, ph: string, h=80) => (
    <textarea value={val} onChange={e=>upd(key,e.target.value)} placeholder={ph}
      style={{width:'100%',height:h,padding:'9px 12px',border:'0.5px solid #ddd',borderRadius:8,fontSize:13,outline:'none',resize:'vertical',fontFamily:'inherit',boxSizing:'border-box'}} />
  );

  return (
    <div style={{maxWidth:860}}>
      {card(<>
        {S('섹션 0 — IC 커버 / 게이트 현황')}
        <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12}}>
          {[['상태',pack.status],['게이트',pack.gate_status||'—'],['데이터',pack.data_status||'—'],['모델',pack.model_status||'—']].map(([l,v])=>(
            <div key={l}><div style={{fontSize:10,color:'#bbb',marginBottom:3}}>{l}</div><div style={{fontSize:13,fontWeight:500}}>{v}</div></div>
          ))}
        </div>
        <div style={{marginTop:10,fontSize:11,color:'#bbb'}}>업데이트: {pack.updated_at?.slice(0,16).replace('T',' ')}</div>
      </>)}

      {card(<>
        {S('섹션 1 — IC 권고안')}
        <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:12}}>
          <select value={rec} onChange={e=>upd('recommendation',e.target.value)}
            style={{padding:'8px 12px',border:'0.5px solid #ddd',borderRadius:8,fontSize:13,outline:'none'}}>
            <option value=''>— 미선택 —</option>
            {REC_OPTIONS.map(o=><option key={o} value={o}>{REC_LABEL[o]}</option>)}
          </select>
          {rec && <span style={{background:recStyle.bg,color:recStyle.color,padding:'4px 14px',borderRadius:20,fontSize:12,fontWeight:600}}>{REC_LABEL[rec]}</span>}
        </div>
        <div style={{fontSize:11,color:'#bbb',marginBottom:6}}>초기 검토 의견</div>
        {ta(form.preliminary_view,'preliminary_view','본건은 선순위 담보부 크레딧으로서...')}
      </>)}

      {card(<>
        {S('섹션 3 — IRR 시나리오')}
        <table style={{width:'100%',borderCollapse:'collapse',fontSize:12}}>
          <thead><tr style={{borderBottom:'0.5px solid #e5e5e5'}}>
            {['시나리오','IRR','MOIC','NPV(억)','DSCR avg','DSCR min','이자합계(억)'].map(h=>(
              <th key={h} style={{padding:'6px 8px',textAlign:'left',color:'#bbb',fontWeight:500}}>{h}</th>
            ))}
          </tr></thead>
          <tbody>
            {['DOWNSIDE','BASE','EXTENSION'].map(s=>{
              const d=irr[s];
              const c=s==='DOWNSIDE'?'#A32D2D':s==='EXTENSION'?'#185FA5':'#000';
              return <tr key={s} style={{borderBottom:'0.5px solid #f5f5f5'}}>
                <td style={{padding:'8px 8px',fontWeight:600,color:c}}>{s}</td>
                <td style={{padding:'8px 8px'}}>{d?`${d.lender_irr_pct}%`:'—'}</td>
                <td style={{padding:'8px 8px'}}>{d?`${d.lender_moic}x`:'—'}</td>
                <td style={{padding:'8px 8px'}}>{d?d.npv_eok:'—'}</td>
                <td style={{padding:'8px 8px',color:d?.dscr_avg<1.0?'#A32D2D':'#3B6D11'}}>{d?d.dscr_avg:'—'}</td>
                <td style={{padding:'8px 8px',color:d?.dscr_min<1.0?'#A32D2D':'#3B6D11'}}>{d?d.dscr_min:'—'}</td>
                <td style={{padding:'8px 8px'}}>{d?d.total_interest_eok:'—'}</td>
              </tr>;
            })}
          </tbody>
        </table>
        <div style={{marginTop:8,fontSize:10,color:'#bbb',fontStyle:'italic'}}>※ 약정 현금흐름 기준. 디폴트 워터폴 미반영.</div>
      </>)}

      {card(<>{S('섹션 4 — 실패 진단  ⚠ INTERNAL')}{ta(form.failure_summary,'failure_summary','NOI가 15% 하락하고 금리가 100bp 상승할 경우...',100)}</>)}
      {card(<>{S('섹션 5 — COUNTERPARTY CONDUCT  ⚠ INTERNAL')}{ta(form.counterparty_summary,'counterparty_summary','차주 자료 제공 태도, 협상 레버리지...')}</>)}
      {card(<>
        {S('섹션 6 — VALUATION & COLLATERAL CUSHION')}
        {ta(form.valuation_notes,'valuation_notes','감정가 근거, AVM haircut, 밸류업 시나리오...')}
      </>)}
      {card(<>
        {S('섹션 7 — EXIT & RECOVERY')}
        <div style={{fontSize:11,color:'#bbb',marginBottom:6}}>원금 손실 범위</div>
        <input value={form.principal_loss_band} onChange={e=>upd('principal_loss_band',e.target.value)}
          placeholder='예: refi 불가 + 20% price drop 시 원금 손실 10–20% 구간'
          style={{width:'100%',padding:'9px 12px',border:'0.5px solid #ddd',borderRadius:8,fontSize:13,outline:'none',boxSizing:'border-box'}} />
      </>)}

      {card(<>
        {S('섹션 9 — CONDITIONS')}
        {condOver && <div style={{background:'#FAEEDA',border:'0.5px solid #FAC775',borderRadius:6,padding:'8px 12px',fontSize:12,color:'#854F0B',marginBottom:10}}>⚠ 조건 5개 초과 — 저장 시 보류로 자동 격하</div>}
        {(form.conditions||[]).map((c: string,i: number)=>(
          <div key={i} style={{display:'flex',gap:8,marginBottom:8}}>
            <input value={c} onChange={e=>{const a=[...(form.conditions||[])];a[i]=e.target.value;upd('conditions',a);}}
              placeholder={`조건 ${i+1}`} style={{flex:1,padding:'8px 12px',border:'0.5px solid #ddd',borderRadius:8,fontSize:13,outline:'none'}} />
            <button onClick={()=>upd('conditions',(form.conditions||[]).filter((_:any,j:number)=>j!==i))}
              style={{padding:'0 12px',background:'none',border:'0.5px solid #ddd',borderRadius:8,fontSize:16,cursor:'pointer',color:'#bbb'}}>×</button>
          </div>
        ))}
        <button onClick={()=>upd('conditions',[...(form.conditions||[]),''])}
          style={{fontSize:12,color:'#666',background:'none',border:'0.5px solid #ddd',borderRadius:6,padding:'6px 14px',cursor:'pointer'}}>+ 조건 추가</button>
      </>)}

      {dirty && (
        <div style={{position:'sticky',bottom:24,background:'#fff',border:'0.5px solid #e5e5e5',borderRadius:10,padding:'12px 20px',display:'flex',alignItems:'center',justifyContent:'space-between',boxShadow:'0 4px 20px rgba(0,0,0,0.08)'}}>
          <span style={{fontSize:12,color:'#888'}}>저장되지 않은 변경사항</span>
          <div style={{display:'flex',gap:10,alignItems:'center'}}>
            {saveMsg && <span style={{fontSize:12,color:saveMsg.includes('실패')?'#A32D2D':'#3B6D11'}}>{saveMsg}</span>}
            <button onClick={save} disabled={saving}
              style={{padding:'8px 20px',background:'#000',color:'#fff',border:'none',borderRadius:8,fontSize:13,cursor:'pointer'}}>
              {saving?'저장 중...':'저장'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
