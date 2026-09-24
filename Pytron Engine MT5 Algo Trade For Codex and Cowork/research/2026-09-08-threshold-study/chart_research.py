# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Offline threshold research over immutable MT5 bars. No MT5 import or live writes.

Primary: all available M5 entries, closed M5/M15/H1 inputs, next open execution,
one position per direction, fixed ATR SL / RR TP, 60-minute horizon.
60/20/20 chronological train/validation/test. No labels cross segment boundaries.
Raw-score intervals are hypotheses; static exits do not replicate the live lifecycle.
"""
from pathlib import Path
from datetime import datetime, timezone
import sys, json, math, time
import numpy as np

HERE = Path(__file__).resolve().parent
INPUT = HERE / 'inputs'
sys.path.insert(0, str(INPUT / 'code'))
sys.dont_write_bytecode = True
from strategy_engine import summarize_rows, classify_regime

FAMILIES = ('trend','range','mean_reversion','counter_trend','breakout','breakout_reversal')
KEYS = tuple(f'{f}_{s}' for f in FAMILIES for s in ('buy','sell'))
FACTORS = np.repeat([1.2,1.,1.1,1.,1.25,1.],2)
RR = np.repeat([1.8,1.8,1.8,1.8,2.,1.8],2)
CONFIG = json.loads((INPUT/'config_sanitized.json').read_text(encoding='utf-8'))
POINT = json.loads((INPUT/'symbol_spec.json').read_text())['point']

def utc(t):
    return datetime.fromtimestamp(int(t), timezone.utc).isoformat()

def write(name, obj):
    (HERE/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def features():
    target=HERE/'chart_features.npz'
    if target.exists():
        return dict(np.load(target,allow_pickle=False))
    bars={f:np.load(INPUT/f'bars_{f}.npy',allow_pickle=False) for f in ('M5','M15','H1')}
    rows={f:[{k:float(r[k]) for k in r.dtype.names} for r in a] for f,a in bars.items()}
    caches={'M15':{},'H1':{}}
    idxs=[]; scores=[]; atrs=[]; regimes=[]
    started=time.monotonic()
    for i in range(259,len(bars['M5'])-1):
        now=int(bars['M5'][i]['time'])+300
        ix={f:int(np.searchsorted(bars[f]['time']+sec,now,side='right')-1) for f,sec in (('M15',900),('H1',3600))}
        if min(ix.values())<259:
            continue
        fs={'M5':summarize_rows(rows['M5'][i-259:i+1])}
        for f,j in ix.items():
            if j not in caches[f]:
                caches[f][j]=summarize_rows(rows[f][j-259:j+1])
            fs[f]=caches[f][j]
        reg=classify_regime(fs,CONFIG)
        idxs.append(i+1); scores.append([reg['scores'][k] for k in KEYS]); atrs.append(fs['M5']['atr14']); regimes.append(reg['regime'])
        if i%5000==0:
            print('features',i,'/',len(bars['M5']),'seconds',round(time.monotonic()-started),flush=True)
    out={'entry_index':np.array(idxs),'score':np.array(scores),'atr':np.array(atrs),'regime':np.array(regimes),'keys':np.array(KEYS)}
    np.savez_compressed(target,**out)
    return out

def mapped_inputs(tf, feat):
    bars=np.load(INPUT/f'bars_{tf}.npy',allow_pickle=False)
    if tf=='M5':
        return bars,feat['entry_index'],feat['score'],feat['atr']
    m5=np.load(INPUT/'bars_M5.npy',allow_pickle=False)
    source_times=m5[feat['entry_index']-1]['time']+300
    # At an M1 opening, only previous fully closed M5 and higher frames are used.
    mapped=np.searchsorted(source_times,bars['time'],side='right')-1
    valid=np.flatnonzero(mapped>=0)
    return bars,valid,feat['score'][mapped[valid]],feat['atr'][mapped[valid]]

def simulate(tf,feat,horizon=60,spread_floor=0.,slippage=0.):
    bars,idx,score,atr=mapped_inputs(tf,feat)
    sec=60 if tf=='M1' else 300
    hold=int(horizon*60/sec)
    nt=len(idx); ns=len(KEYS)
    returns=np.full((nt,ns),np.nan); exits=np.full((nt,ns),-1,dtype=np.int64); types=np.zeros((nt,ns),dtype=np.int8)
    spread=np.maximum(bars['spread']*POINT,spread_floor)
    # Exclude windows with a missing bar, weekend or rollover rather than invent prices.
    gaps=np.r_[0,np.cumsum(np.diff(bars['time'])!=sec)]
    good=(idx+hold<=len(bars)) & (spread[idx]<=float(CONFIG['max_spread'])) & (atr>0)
    ids=np.flatnonzero(good)
    ids=ids[(gaps[idx[ids]+hold-1]-gaps[idx[ids]])==0]
    entry_t=bars[idx]['time'].astype(np.int64)
    both_count=0
    for j,key in enumerate(KEYS):
        buy=key.endswith('_buy')
        sign=1 if buy else -1
        ii=ids[score[ids,j]>0]
        eidx=idx[ii]
        stop=atr[ii]*FACTORS[j]
        entry=bars[eidx]['open']+(spread[eidx] if buy else 0)+sign*slippage
        sl=entry-sign*stop; tp=entry+sign*stop*RR[j]
        unresolved=np.ones(len(ii),dtype=bool)
        for k in range(hold):
            active=np.flatnonzero(unresolved)
            if not len(active): break
            at=eidx[active]+k
            lo=bars[at]['low']+(0 if buy else spread[at])
            hi=bars[at]['high']+(0 if buy else spread[at])
            op=bars[at]['open']+(0 if buy else spread[at])
            stop_hit=lo<=sl[active] if buy else hi>=sl[active]
            tp_hit=hi>=tp[active] if buy else lo<=tp[active]
            both_count+=int(np.sum(stop_hit & tp_hit))
            hit=stop_hit|tp_hit
            a=active[hit]
            if len(a):
                # Gaps through stop execute at worse open; limit targets fill at target.
                stop_price=np.minimum(op[hit],sl[a]) if buy else np.maximum(op[hit],sl[a])
                price=np.where(stop_hit[hit],stop_price,tp[a])-sign*slippage
                returns[ii[a],j]=sign*(price-entry[a])/stop[a]
                exits[ii[a],j]=bars[eidx[a]+k]['time']+sec
                types[ii[a],j]=np.where(stop_hit[hit],1,2)
                unresolved[a]=False
        a=np.flatnonzero(unresolved)
        if len(a):
            at=eidx[a]+hold-1
            price=bars[at]['close']+(0 if buy else spread[at])-sign*slippage
            returns[ii[a],j]=sign*(price-entry[a])/stop[a]
            exits[ii[a],j]=bars[at]['time']+sec
            types[ii[a],j]=3
    return {'time':entry_t,'score':score,'atr':atr,'r':returns,'exit':exits,'exit_type':types,'both_hits':both_count,'valid_windows':len(ids),'spread':spread[idx]}

def select_trades(data,j,lo,hi,start,end):
    s=data['score'][:,j]; t=data['time']; e=data['exit'][:,j]; r=data['r'][:,j]
    valid=np.isfinite(r)&(s>=lo-1e-12)&((s<hi-1e-12) if hi<1 else (s<=1))&(s>0)&(t>=start)&(e<=end)
    picks=[]; free=-1
    for i in np.flatnonzero(valid):
        if t[i]>=free:
            picks.append(i);free=e[i]
    return np.array(picks,dtype=int)

def metrics(data,j,picks,start,end,bootstrap=False):
    r=data['r'][picks,j]; n=len(r)
    win=r[r>0];loss=r[r<0]
    trade_days=np.unique(data['time'][(data['time']>=start)&(data['time']<end)]//86400)
    daily=np.zeros(len(trade_days))
    if n and len(trade_days):
        np.add.at(daily,np.searchsorted(trade_days,data['time'][picks]//86400),r)
    equity=np.r_[0,np.cumsum(r)]
    avg=float(np.mean(r)) if n else None
    mean=float(daily.mean()) if len(daily) else 0.
    se=float(daily.std(ddof=1)/math.sqrt(len(daily))) if len(daily)>1 else 0.
    out={'n':n,'days_with_trades':len(np.unique(data['time'][picks]//86400)),'available_days':len(daily),'sum_r':float(r.sum()),'mean_r':avg,
         'win_rate':float((r>0).mean()) if n else None,'pf':float(win.sum()/-loss.sum()) if len(loss) else None,
         'max_drawdown_r':float((np.maximum.accumulate(equity)-equity).max()),'mean_daily_r':mean,'daily_se':se,
         'selection_lcb':mean-1.645*se,'average_win_r':float(win.mean()) if len(win) else None,'average_loss_r':float(-loss.mean()) if len(loss) else None,
         'timeouts':int((data['exit_type'][picks,j]==3).sum())}
    if len(win) and len(loss):out['empirical_break_even_p']=float(-loss.mean()/(win.mean()-loss.mean()))
    if bootstrap and n and len(daily)>=5:
        # Five consecutive trading-day circular blocks; retain days with zero trades.
        rng=np.random.default_rng(20260908+j)
        sampled=[]
        for _ in range(2000):
            starts=rng.integers(0,len(daily),size=math.ceil(len(daily)/5))
            ix=((starts[:,None]+np.arange(5))%len(daily)).ravel()[:len(daily)]
            sampled.append(float(daily[ix].mean()))
        out['daily_r_block_bootstrap_ci95']=[float(x) for x in np.quantile(sampled,[.025,.975])]
        out['daily_r_familywise_lower_12']=float(np.quantile(sampled,.05/12))
    return out

def intervals():
    # Registered before observing outcomes: 55 decile intervals plus 10 additional half-decile lower bounds.
    return sorted(set([(round(i/10,2),round(j/10,2)) for i in range(10) for j in range(i+1,11)]+
                      [(round(i/20,2),1.) for i in range(1,20)]))

def evaluate(feat):
    base=simulate('M5',feat)
    start=int(base['time'][0]);end=int(base['time'][-1])+300
    split1=int(start+.6*(end-start));split2=int(start+.8*(end-start))
    periods=[(start,split1),(split1,split2),(split2,end)]
    grid=intervals();summary={'keys':KEYS,'base':{'timeframe':'M5','hold_minutes':60,'rr':RR.tolist(),'stop_factors':FACTORS.tolist(),'entry':'next bar open, bid/ask spread','spread':'historical bars spread * point','max_entry_spread':CONFIG['max_spread'],'same_bar':'SL first','only_continuous_windows':True,'no_dynamic_position_exits':True,'no_historical_risk_equity_filter':True,'commission_swap':0},
                             'split_source_epoch':periods,'split_labels_source_clock':[[utc(a),utc(b)] for a,b in periods],
                             'search_intervals_per_direction':len(grid),'search_total_primary':len(grid)*12,'directions':{},'both_hit_scenarios':base['both_hits'],'valid_windows':base['valid_windows']}
    all_grid={}
    selected={}
    for j,key in enumerate(KEYS):
        rows=[]
        for lo,hi in grid:
            train=metrics(base,j,select_trades(base,j,lo,hi,*periods[0]),*periods[0])
            val=metrics(base,j,select_trades(base,j,lo,hi,*periods[1]),*periods[1])
            rows.append({'lower':lo,'upper':hi,'train':train,'validation':val})
        # Training preselects at most five candidates. Validation chooses only within these.
        train_ok=[x for x in rows if x['train']['n']>=60 and x['train']['days_with_trades']>=15]
        top5=sorted(train_ok,key=lambda x:x['train']['selection_lcb'],reverse=True)[:5]
        acceptable=[x for x in top5 if x['train']['mean_r']>0 and x['validation']['n']>=20 and x['validation']['days_with_trades']>=8 and x['validation']['mean_r']>0]
        choice=max(acceptable,key=lambda x:x['validation']['selection_lcb']) if acceptable else (top5[0] if top5 else max(rows,key=lambda x:x['train']['n']))
        chosen=dict(choice)
        chosen['development_qualified']=bool(acceptable)
        lo,hi=choice['lower'],choice['upper']; selected[key]=(lo,hi)
        picks=select_trades(base,j,lo,hi,*periods[2])
        chosen['test']=metrics(base,j,picks,*periods[2],bootstrap=True)
        threshold=CONFIG['strategy_router']['agent_score_thresholds'][key.rsplit('_',1)[0]]
        chosen['current_number_applied_to_raw_for_comparison_only']=threshold
        chosen['baseline_test']=metrics(base,j,select_trades(base,j,threshold,1.,*periods[2]),*periods[2])
        chosen['score_percentiles']=[float(x) for x in np.quantile(base['score'][:,j],[0,.25,.5,.75,.9,.99,1])]
        chosen['nonzero_signals']=int((base['score'][:,j]>0).sum())
        chosen['neighbours']=[]
        for x in rows:
            if abs(x['lower']-lo)+abs(x['upper']-hi)<=.100001:
                chosen['neighbours'].append({'lower':x['lower'],'upper':x['upper'],'test':metrics(base,j,select_trades(base,j,x['lower'],x['upper'],*periods[2]),*periods[2])})
        # Selection by past-only expanding windows; never use test block to select that block's interval.
        chosen['walk_forward']=[]
        for f in range(4):
            a=int(start+(.4+.15*f)*(end-start));b=int(start+(.55+.15*f)*(end-start))
            training=[]
            for l,u in grid:
                m=metrics(base,j,select_trades(base,j,l,u,start,a),start,a)
                if m['n']>=60 and m['days_with_trades']>=15: training.append((m['selection_lcb'],l,u,m))
            if not training: continue
            _,l,u,m=max(training,key=lambda x:x[0])
            test=metrics(base,j,select_trades(base,j,l,u,a,b),a,b)
            chosen['walk_forward'].append({'lower':l,'upper':u,'train_selection_lcb':m['selection_lcb'],'test':test,'period':[utc(a),utc(b)]})
        summary['directions'][key]=chosen;all_grid[key]=rows
        print('selected',key,lo,hi,'dev',bool(acceptable),'test',chosen['test']['n'],round(chosen['test']['sum_r'],2),flush=True)
    write('raw_threshold_grid.json',all_grid)
    write('chart_results.json',summary)
    np.savez_compressed(HERE/'chart_outcomes_M5_base.npz',**{k:v for k,v in base.items() if isinstance(v,np.ndarray)})
    # Re-evaluate fixed choices under execution/horizon sensitivity; no retuning.
    for name,tf,h,fl,sl in [('M5_cost_stress','M5',60,.4,.05),('M5_180min','M5',180,0.,0.),('M1_60min','M1',60,0.,0.),('M1_cost_stress','M1',60,.4,.05)]:
        data=simulate(tf,feat,h,fl,sl)
        a=max(split2,int(data['time'][0]));b=end
        for j,key in enumerate(KEYS):
            l,u=selected[key]
            m=metrics(data,j,select_trades(data,j,l,u,a,b),a,b,bootstrap=True)
            summary['directions'][key].setdefault('sensitivity',{})[name]=m
        print('sensitivity done',name,flush=True)
    # Observed interval behavior; no assumption that higher score means higher profitability.
    summary['score_deciles']={}
    for j,key in enumerate(KEYS):
        summary['score_deciles'][key]=[{'lower':i/10,'upper':(i+1)/10,'test':metrics(base,j,select_trades(base,j,i/10,(i+1)/10,*periods[2]),*periods[2])} for i in range(10)]
    write('chart_results.json',summary)

def sanity():
    # Mechanics: probability ranges, next-close alignment checked separately by metadata.
    assert len(KEYS)==12 and len(intervals())==65
    assert (FACTORS>0).all() and (RR>0).all()

if __name__=='__main__':
    sanity()
    f=features()
    print('feature rows',len(f['entry_index']),flush=True)
    evaluate(f)
