# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ทดสอบ: ถ้า "ให้สัญญาณที่ถูกประตู net สกัด" เข้าร่วมไม้ (เฉพาะสัญญาณแรง) จะได้หรือเสีย
import json, io, datetime, collections
import MetaTrader5 as mt5
STOP={"counter_trend":1.0,"mean_reversion":1.1,"breakout":1.25,"range":1.0,"trend":1.2,"breakout_reversal":1.0}
RR=1.4
cfg=json.load(io.open('outputs/mt5_python_bridge/auto_config.json',encoding='utf-8'))
gov=cfg['strategy_router']['bounded_live']['governance']
def band_ok(st,sd,raw,pr,w):
    g=gov.get(st) or {}
    def f(k,d):
        v=g.get(k); return float(v) if isinstance(v,(int,float)) else d
    return (raw>=f(f'raw_{sd}',0) and raw<=f(f'raw_max_{sd}',1) and pr>=f(f'probability_{sd}',0)
            and pr<=f(f'probability_max_{sd}',1) and w>=f(f'weighted_{sd}',0) and w<=f(f'weighted_max_{sd}',1))
sig=[]
for l in io.open('work/auto_trader_audit.jsonl',encoding='utf-8'):
    try: e=json.loads(l)
    except Exception: continue
    d=((e.get('analysis') or {}).get('router_decision') or {}).get('bounded_live_diagnostics') or []
    for g in d:
        if g.get('blocked_by')!='side_net_gate': continue
        st,sd=g.get('strategy'),g.get('side')
        raw=float(g.get('raw_score') or 0); pr=float(g.get('probability') or 0); w=float(g.get('weighted_score') or 0)
        if band_ok(st,sd,raw,pr,w):
            try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
            except Exception: continue
            sig.append((t,st,sd,raw,w))
print("สัญญาณที่ถูกประตู net สกัด (ทั้งประวัติ):", len(sig))
mt5.initialize()
def sim(t,st,sd):
    r0=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_M1,t.replace(tzinfo=None),(t+datetime.timedelta(minutes=3)).replace(tzinfo=None))
    if r0 is None or len(r0)==0: return None
    entry=float(r0[0]['close'])
    r=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_M1,t.replace(tzinfo=None),(t+datetime.timedelta(hours=12)).replace(tzinfo=None))
    if r is None or len(r)<3: return None
    tr=[abs(float(r[i]['high'])-float(r[i]['low'])) for i in range(1,min(20,len(r)))]
    atr=sum(tr)/len(tr) if tr else 1.0
    risk=atr*STOP.get(st,1.0); rew=risk*RR
    if sd=='buy': sl,tp=entry-risk,entry+rew
    else: sl,tp=entry+risk,entry-rew
    for b in r[1:]:
        hi,lo=float(b['high']),float(b['low'])
        hs=lo<=sl if sd=='buy' else hi>=sl
        ht=hi>=tp if sd=='buy' else lo<=tp
        if hs and ht: return -1.0
        if hs: return -1.0
        if ht: return RR
    return None
def h1t(t):
    f=(t-datetime.timedelta(hours=36)).replace(tzinfo=None)
    r=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_H1,f,t.replace(tzinfo=None))
    if r is None or len(r)<20: return None
    cl=[float(x['close']) for x in r][-20:]
    return 'up' if cl[-1]>sum(cl)/len(cl) else 'down'
res=collections.defaultdict(lambda: dict(n=0,w=0,r=0.0))
for t,st,sd,raw,w in sig:
    rr=sim(t,st,sd)
    if rr is None: continue
    tr=h1t(t)
    cd = (sd=='buy' and tr=='down') or (sd=='sell' and tr=='up')
    for key in ((st+'_'+sd), 'สวนแนวโน้ม' if cd else 'ตามแนวโน้ม', 'รวมทั้งหมด'):
        res[key]['n']+=1; res[key]['r']+=rr; res[key]['w']+= 1 if rr>0 else 0
mt5.shutdown()
print("\n%-24s %5s %8s %10s %10s" % ("กลุ่ม","n","win%","net R","R/ไม้"))
for k in list(res):
    d=res[k]
    if d['n']>=3: print("%-24s %5d %7.1f%% %+10.2f %+10.3f" % (k,d['n'],100.0*d['w']/d['n'],d['r'],d['r']/d['n']))
