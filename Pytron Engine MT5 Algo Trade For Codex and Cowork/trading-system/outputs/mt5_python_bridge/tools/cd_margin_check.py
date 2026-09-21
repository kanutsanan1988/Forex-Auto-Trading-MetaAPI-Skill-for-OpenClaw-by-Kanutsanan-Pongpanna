# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ตรวจผลของ "ยกพื้นไม้สวนแนวโน้ม" กับข้อมูลจริง: จะตันไหม + ตัดไม้แย่กี่ไม้
import json, io, datetime, collections
import MetaTrader5 as mt5
MARGIN=0.05
def rows(p):
    for l in io.open(p,encoding='utf-8'):
        try: yield json.loads(l)
        except Exception: pass
def h1_trend(sym,t):
    f=(t-datetime.timedelta(hours=36)).replace(tzinfo=None)
    r=mt5.copy_rates_range(sym,mt5.TIMEFRAME_H1,f,t.replace(tzinfo=None))
    if r is None or len(r)<20: return None
    cl=[float(x['close']) for x in r][-20:]
    return 'up' if cl[-1]>sum(cl)/len(cl) else 'down'
mt5.initialize()
# ผ่าน/ไม่ผ่านแบบเดิม vs แบบยกพื้น (เฉพาะรอบที่มีคีย์ผ่านอยู่แล้ว = รอบที่เทรดได้)
rounds=[]; orders=[]
for e in rows('work/auto_trader_audit.jsonl'):
    d=((e.get('analysis') or {}).get('router_decision') or {}).get('bounded_live_diagnostics') or []
    if d: rounds.append((e.get('time'),d))
    if e.get('event')=='order_result':
        r=(e.get('result') or {}); q=r.get('request') or []
        if len(q)>=9 and float(q[5])>0 and float(q[7])>0: orders.append((e.get('time'), q[3], float(q[5]), float(q[7]), str(q[-1])))
print("รอบ:",len(rounds),"| ออเดอร์:",len(orders))
blocked=0; cd_orders=0; cnt=collections.Counter()
for t,sym,price,sl,cm in orders:
    try: tt=datetime.datetime.fromisoformat(str(t).replace('Z','+00:00'))
    except Exception: continue
    tr=h1_trend(sym,tt)
    if tr is None: continue
    side='buy' if cm else None
    # หารอบตัดสินก่อน/ใกล้เวลา order
    cand=[d for (rt,d) in rounds if str(rt)<=str(t)]
    if not cand: continue
    d=cand[-1]
    pas=[g for g in d if g.get('passed')]
    if not pas: continue
    g=pas[0]
    sd=g.get('side'); st=str(g.get('strategy') or '')
    is_cd=(sd=='buy' and tr=='down') or (sd=='sell' and tr=='up')
    if not is_cd: continue
    cd_orders+=1
    raw=float(g.get('raw_score') or 0); pr=float(g.get('probability') or 0); w=float(g.get('weighted_score') or 0)
    def eff(lo,hi):
        lo=float(lo or 0); hi=float(hi) if isinstance(hi,(int,float)) else None
        if hi is not None and hi>lo: return lo+min(MARGIN,0.8*(hi-lo))
        return lo+MARGIN
    lo_r=eff(g.get('raw_gate'),g.get('raw_gate_max')); lo_p=eff(g.get('probability_gate'),g.get('probability_gate_max')); lo_w=eff(g.get('weighted_gate'),g.get('weighted_gate_max'))
    ok = raw>=lo_r and pr>=lo_p and w>=lo_w
    cnt['ผ่านต่อ' if ok else 'ถูกตัด']+=1
    if not ok: blocked+=1
print("\n=== ไม้สวนแนวโน้ม H1 (จากออเดอร์จริง) ===")
print("  ตรวจได้ %d ไม้ → ยกพื้นแล้ว 'ถูกตัด' %d ไม้ · 'ยังผ่าน' %d ไม้" % (cd_orders, blocked, cnt['ผ่านต่อ']))
print("  (ไม่ตัน: ยังมีไม้ผ่าน %.0f%%)" % (100.0*cnt['ผ่านต่อ']/max(1,cd_orders)))
# ผ่าน/ไม่ผ่านทั้งระบบ แบบเดิม vs ยกพื้น (จากรอบจริง)
tot=0; pass0=0; pass1=0; cd_tot=0; cd0=0; cd1=0
for t,d in rounds[-250:]:
    try: tt=datetime.datetime.fromisoformat(str(t).replace('Z','+00:00'))
    except Exception: continue
    tr=h1_trend('XAUUSD.sml',tt)
    if tr is None: continue
    for g in d:
        if g.get('stage')=='1_side_net': continue
        sd=g.get('side'); raw=float(g.get('raw_score') or 0); pr=float(g.get('probability') or 0); w=float(g.get('weighted_score') or 0)
        def p0():
            lo_r=float(g.get('raw_gate') or 0); lo_p=float(g.get('probability_gate') or 0); lo_w=float(g.get('weighted_gate') or 0)
            hr=g.get('raw_gate_max'); hp=g.get('probability_gate_max'); hw=g.get('weighted_gate_max')
            return raw>=lo_r and pr>=lo_p and w>=lo_w and (hr is None or raw<=hr) and (hp is None or pr<=hp) and (hw is None or w<=hw)
        def eff(lo,hi):
            lo=float(lo or 0); hi=float(hi) if isinstance(hi,(int,float)) else None
            if hi is not None and hi>lo: return lo+min(MARGIN,0.8*(hi-lo))
            return lo+MARGIN
        is_cd=(sd=='buy' and tr=='down') or (sd=='sell' and tr=='up')
        a=p0(); b=a and raw>=eff(g.get('raw_gate'),g.get('raw_gate_max')) and pr>=eff(g.get('probability_gate'),g.get('probability_gate_max')) and w>=eff(g.get('weighted_gate'),g.get('weighted_gate_max'))
        tot+=1; pass0+=1 if a else 0; pass1+=1 if b else 0
        if is_cd:
            cd_tot+=1; cd0+=1 if a else 0; cd1+=1 if b else 0
mt5.shutdown()
print("\n=== อัตราผ่านประตู (250 รอบล่าสุด · ทุกคีย์) ===")
print("  ทั้งหมด: ก่อน %.1f%% → หลังยกพื้น %.1f%%" % (100.0*pass0/max(1,tot),100.0*pass1/max(1,tot)))
print("  เฉพาะสวนแนวโน้ม: ก่อน %.1f%% → หลัง %.1f%% (%d/%d → %d/%d)" % (100.0*cd0/max(1,cd_tot),100.0*cd1/max(1,cd_tot),cd0,cd_tot,cd1,cd_tot))
