# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ตรวจ: ถ้า "ปล่อยไม้วิ่งจนถึง TP หรือ SL" (ไม่ปิดกำไรที่ 1/10 TP) ผลเป็นอย่างไร — ข้อมูลจริง 24 ชม.
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
    r=e.get('result') or {}; q=r.get('request') or []
    if len(q)<9: continue
    try: pr=float(q[5]); sl=float(q[7]); tp=float(q[8])
    except Exception: continue
    if not (pr>0 and sl>0 and tp>0): continue
    try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
    except Exception: continue
    side='buy' if sl<pr<tp else ('sell' if tp<pr<sl else None)
    if not side: continue
    strat=(str(q[-1]).split('codex-')[-1] or '?')
    orders.append((t,pr,sl,tp,side,strat))
print("ออเดอร์ 24 ชม.ล่าสุด:", len(orders))
mt5.initialize()
def sim(o):
    _t,pr,sl,tp,side,strat=o
    r=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_M1,t.replace(tzinfo=None),(t+datetime.timedelta(hours=12)).replace(tzinfo=None))
    if r is None or len(r)<3: return None
    risk=abs(pr-sl); rew=abs(tp-pr)
    for b in r[1:]:
        hi,lo=float(b['high']),float(b['low'])
        hs=lo<=sl if side=='buy' else hi>=sl
        ht=hi>=tp if side=='buy' else lo<=tp
        if hs and ht: return -1.0
        if hs: return -1.0
        if ht: return (rew/risk if risk else 0.0)
    return None
tot=0.0; n=0; bystrat=collections.defaultdict(lambda:[0,0.0]); byside=collections.defaultdict(lambda:[0,0.0])
for o in orders:
    R=sim(o)
    if R is None: continue
    tot+=R; n+=1
    bystrat[o[5]][0]+=1; bystrat[o[5]][1]+=R
    byside[o[4]][0]+=1; byside[o[4]][1]+=R
mt5.shutdown()
print("\n=== 'ปล่อยไม้วิ่งจนถึง TP/SL' (24 ชม.ล่าสุด) ===")
print("  n=%d | net %+.2f R | R/ไม้ %+.3f" % (n,tot,tot/max(1,n)))
for k,(c,r) in sorted(bystrat.items(), key=lambda x:-x[1][0]):
    print("    %-18s n=%-3d net %+6.2f R (R/ไม้ %+.3f)" % (k,c,r,r/max(1,c)))
for k,(c,r) in byside.items():
    print("    ฝั่ง %-4s        n=%-3d net %+6.2f R" % (k,c,r))
print("\nของจริง 24 ชม.: -$1.29 (≈ -2.6R ที่ไม้ 0.001 lot · ความเสี่ยง ~$0.50/ไม้)")
