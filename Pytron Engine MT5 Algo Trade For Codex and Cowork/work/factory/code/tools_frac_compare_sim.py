# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# เทียบระดับ "ปิดกำไรเมื่อไม่มีสัญญาณ" 0.5 / 0.8 / 1.0 (ถึง TP) — ออเดอร์จริง 24 ชม. ราคา M1
import json, io, datetime, collections
import MetaTrader5 as mt5
rows=[json.loads(l) for l in io.open('work/auto_trader_audit.jsonl',encoding='utf-8') if l.strip()]
now=datetime.datetime.now(datetime.timezone.utc)
def age(t):
    try: return (now-datetime.datetime.fromisoformat(str(t).replace('Z','+00:00'))).total_seconds()/3600
    except Exception: return 9e9
orders=[]
for e in rows:
    if e.get('event')!='order_result' or age(e.get('time'))>24: continue
    q=(e.get('result') or {}).get('request') or []
    if len(q)<9: continue
    try: pr,sl,tp=float(q[5]),float(q[7]),float(q[8])
    except Exception: continue
    if not (pr>0 and sl>0 and tp>0): continue
    side='buy' if sl<pr<tp else ('sell' if tp<pr<sl else None)
    if not side: continue
    try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
    except Exception: continue
    orders.append((t,pr,sl,tp,side))
mt5.initialize()
res=collections.defaultdict(lambda: dict(n=0,w=0,r=0.0))
for t,pr,sl,tp,side in orders:
    r=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_M1,t.replace(tzinfo=None),(t+datetime.timedelta(hours=12)).replace(tzinfo=None))
    if r is None or len(r)<3: continue
    risk=abs(pr-sl); rew=abs(tp-pr)
    for frac in (0.5,0.8,1.0):
        target = pr + frac*rew if side=='buy' else pr - frac*rew
        out=None
        for b in r[1:]:
            hi,lo=float(b['high']),float(b['low'])
            hs=lo<=sl if side=='buy' else hi>=sl
            ht=hi>=target if side=='buy' else lo<=target
            if hs and ht: out=-1.0; break
            if hs: out=-1.0; break
            if ht: out=frac*(rew/risk); break
        if out is None: continue
        d=res[frac]; d['n']+=1; d['r']+=out; d['w']+=1 if out>0 else 0
mt5.shutdown()
print("\n=== เทียบระดับปิดกำไร (ออเดอร์จริง 24 ชม.) ===")
print("%-28s %5s %8s %10s %10s" % ("ระดับปิดกำไร","n","win%","net R","R/ไม้"))
for frac in (0.5,0.8,1.0):
    d=res[frac]
    if d['n']: print("%-28s %5d %7.1f%% %+10.2f %+10.3f" % ("%.0f%% ของระยะ TP" % (frac*100), d['n'], 100.0*d['w']/d['n'], d['r'], d['r']/d['n']))
