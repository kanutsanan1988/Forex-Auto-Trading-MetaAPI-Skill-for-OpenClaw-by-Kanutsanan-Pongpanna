# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ต่อจาก tpsl_countertrend_sim: แยกเทรนด์ด้วย H1 + ทดสอบ TP หลายระดับ (เฉพาะไม้สวนทาง)
import json, io, datetime, collections
import MetaTrader5 as mt5
STOP_ATR={"counter_trend":1.0,"mean_reversion":1.1,"breakout":1.25,"range":1.0,"trend":1.2,"breakout_reversal":1.0}
def orders(path):
    out=[]
    for l in io.open(path,encoding='utf-8'):
        try: e=json.loads(l)
        except Exception: continue
        if e.get('event')!='order_result': continue
        r=e.get('result') or {}; q=r.get('request') or []
        if len(q)<9: continue
        try: sym=q[3]; pr=float(q[5]); sl=float(q[7]); tp=float(q[8])
        except Exception: continue
        if not(pr>0 and sl>0 and tp>0): continue
        side='buy' if sl<pr<tp else ('sell' if tp<pr<sl else None)
        if not side: continue
        try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
        except Exception: continue
        out.append(dict(t=t,sym=sym,price=pr,sl=sl,tp=tp,strat=(str(q[-1]).split('codex-')[-1] or 'unknown'),side=side))
    return out
def trend(sym,t,tf,n=20):
    f=(t-datetime.timedelta(hours=36)).replace(tzinfo=None); to=t.replace(tzinfo=None)
    r=mt5.copy_rates_range(sym,tf,f,to)
    if r is None or len(r)<n: return None
    cl=[float(x['close']) for x in r][-n:]
    return 'up' if cl[-1]>sum(cl)/len(cl) else 'down'
def sim(o,risk_mult,tp_ratio,h=12.0):
    atr=abs(o['price']-o['sl'])/max(.01,STOP_ATR.get(o['strat'],1.0))
    risk=atr*risk_mult; rew=risk*tp_ratio
    sl=o['price']-risk if o['side']=='buy' else o['price']+risk
    tp=o['price']+rew if o['side']=='buy' else o['price']-rew
    r=mt5.copy_rates_range(o['sym'],mt5.TIMEFRAME_M1,o['t'].replace(tzinfo=None),(o['t']+datetime.timedelta(hours=h)).replace(tzinfo=None))
    if r is None or len(r)==0: return None
    for b in r:
        hi,lo=float(b['high']),float(b['low'])
        hs = lo<=sl if o['side']=='buy' else hi>=sl
        ht = hi>=tp if o['side']=='buy' else lo<=tp
        if hs and ht: return -1.0
        if hs: return -1.0
        if ht: return float(tp_ratio)
    return None
mt5.initialize(); os_=orders('work/auto_trader_audit.jsonl')
res=collections.defaultdict(lambda: dict(n=0,w=0,r=0.0))
pers=collections.defaultdict(lambda: dict(n=0,r=0.0,w=0))
for o in os_:
    t1=trend(o['sym'],o['t'],mt5.TIMEFRAME_H1)
    if t1 is None: continue
    cd=(o['side']=='buy' and t1=='down') or (o['side']=='sell' and t1=='up')
    if not cd: continue
    pers[o['strat']]['n']+=1
    for risk_mult,tp_ratio,label in (( STOP_ATR.get(o['strat'],1.0), abs(o['tp']-o['price'])/max(1e-9,abs(o['price']-o['sl'])), 'A_จริง'),
                                     (STOP_ATR.get(o['strat'],1.0),0.5,'TP0.5R'),(STOP_ATR.get(o['strat'],1.0),0.8,'TP0.8R'),
                                     (STOP_ATR.get(o['strat'],1.0),1.0,'TP1.0R'),(STOP_ATR.get(o['strat'],1.0),1.4,'TP1.4R'),
                                     (1.4,0.6,'SL1.4/TP0.84R')):
        v=sim(o,risk_mult,tp_ratio)
        if v is None: continue
        res[label]['n']+=1; res[label]['r']+=v; res[label]['w']+=1 if v>0 else 0
        if label=='A_จริง':
            pers[o['strat']]['r']+=v; pers[o['strat']]['w']+=1 if v>0 else 0
mt5.shutdown()
print("=== ไม้สวนทางเทรนด์ H1: เทียบระดับ TP (SL เท่าเดิม) ===")
print("%-16s %5s %7s %10s %10s" % ("รูปแบบ","n","win%","net R","R/ไม้"))
for k in ('A_จริง','TP0.5R','TP0.8R','TP1.0R','TP1.4R','SL1.4/TP0.84R'):
    d=res[k]
    if d['n']: print("%-16s %5d %6.1f%% %+10.2f %+10.3f" % (k,d['n'],100.0*d['w']/d['n'],d['r'],d['r']/d['n']))
print("\n=== ไม้สวนทาง แยกตามกลยุทธ์ (ผลจริง) ===")
for k,d in sorted(pers.items(), key=lambda x:-x[1]['n']):
    if d['n']: print("  %-18s n=%-4d win=%.0f%%  net R=%+.2f" % (k,d['n'],100.0*d['w']/d['n'],d['r']))
