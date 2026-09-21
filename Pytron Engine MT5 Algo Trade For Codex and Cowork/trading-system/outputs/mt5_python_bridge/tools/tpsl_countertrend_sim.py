# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# จำลอง TP/SL: "ไม้สวนทางตลาด" (ซื้อในขาลง / ขายในขาขึ้น) ควรตั้ง TP สั้นกว่า SL หรือไม่
# ข้อมูลจริง: audit (238 ออเดอร์) + ราคา M1/M15 จาก MT5 ย้อนหลัง
import json, io, datetime
import MetaTrader5 as mt5

STOP_ATR = {"counter_trend":1.0,"mean_reversion":1.1,"breakout":1.25,"range":1.0,
            "trend":1.2,"breakout_reversal":1.0}

def parse_orders(path):
    out=[]
    for l in io.open(path,encoding='utf-8'):
        try: e=json.loads(l)
        except Exception: continue
        if e.get('event')!='order_result': continue
        r=(e.get('result') or {})
        req=r.get('request') or []
        if len(req)<9: continue
        try:
            sym=req[3]; price=float(req[5]); sl=float(req[7]); tp=float(req[8])
        except Exception: continue
        comment=str(req[-1] or "")
        strat=comment.split('codex-')[-1].strip() or "unknown"
        if not (price>0 and sl>0 and tp>0): continue
        side = 'buy' if (sl<price<tp) else ('sell' if (tp<price<sl) else None)
        if not side: continue
        try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
        except Exception: continue
        out.append({"t":t,"sym":sym,"price":price,"sl":sl,"tp":tp,"strat":strat,"side":side})
    return out

def trend_at(sym, t):
    # ทิศทางตลาดตอนเข้าออเดอร์: EMA20 บน M15 (เทียบราคากับ EMA)
    f=(t-datetime.timedelta(hours=12)).replace(tzinfo=None); to=t.replace(tzinfo=None)
    r=mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, f, to)
    if r is None or len(r)<20: return None
    cl=[float(x['close']) for x in r][-20:]
    ema=sum(cl)/len(cl)
    return 'up' if cl[-1]>ema else 'down'

def simulate(sym, o, risk_mult, tp_ratio, horizon_h=12.0):
    """risk_mult = ระยะ SL (เท่า ATR), tp_ratio = TP คิดเป็นสัดส่วนของระยะ SL"""
    atr = abs(o['price']-o['sl'])/max(0.01, STOP_ATR.get(o['strat'],1.0))
    risk = atr*risk_mult; rew = risk*tp_ratio
    if o['side']=='buy': sl=o['price']-risk; tp=o['price']+rew
    else: sl=o['price']+risk; tp=o['price']-rew
    r=mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, o['t'].replace(tzinfo=None), (o['t']+datetime.timedelta(hours=horizon_h)).replace(tzinfo=None))
    if r is None or len(r)==0: return None
    for b in r:
        hi,lo=float(b['high']),float(b['low'])
        if o['side']=='buy':
            hit_sl = lo<=sl; hit_tp = hi>=tp
        else:
            hit_sl = hi>=sl; hit_tp = lo<=tp
        if hit_sl and hit_tp: return -1.0        # ชนทั้งคู่ในแท่งเดียว → ถือว่าแพ้ (อนุรักษ์นิยม)
        if hit_sl: return -1.0
        if hit_tp: return float(tp_ratio)
    return None

def main():
    if not mt5.initialize():
        print("MT5 ✗", mt5.last_error()); return
    orders=parse_orders('work/auto_trader_audit.jsonl')
    print("ออเดอร์ที่ใช้จำลองได้:", len(orders), "| ช่วง:", str(orders[0]['t'])[:16], "→", str(orders[-1]['t'])[:16])
    variants={"A_ปัจจุบัน (SL1.0/rrตามจริง)":None, "B_สวนทาง: SL1.4 TP0.6×SL":(1.4,0.6), "C_สวนทาง: SL1.2 TP0.8×SL":(1.2,0.8), "D_สวนทาง: SL1.0 TP0.6×SL":(1.0,0.6)}
    import collections
    res=collections.defaultdict(lambda: {"n":0,"w":0,"r":0.0,"cd":0})
    res_all=collections.defaultdict(lambda: {"n":0,"w":0,"r":0.0})
    for o in orders:
        tr=trend_at(o['sym'], o['t'])
        if tr is None: continue
        cd = (o['side']=='buy' and tr=='down') or (o['side']=='sell' and tr=='up')
        for name,v in variants.items():
            if v is None:
                r=simulate(o['sym'], o, STOP_ATR.get(o['strat'],1.0), abs(o['tp']-o['price'])/max(1e-9,abs(o['price']-o['sl'])))
            else:
                r=simulate(o['sym'], o, v[0], v[1])
            if r is None: continue
            tgt = res[(name,'สวนทาง' if cd else 'ตามทาง')] if True else None
            tgt["n"]+=1; tgt["r"]+=r
            if r>0: tgt["w"]+=1
            if cd: res_all[name]["n"]+=1; res_all[name]["r"]+=r; res_all[name]["w"]+= (1 if r>0 else 0)
    mt5.shutdown()
    print("\n=== ไม้ 'สวนทางตลาด' (ทุกกลยุทธ์) ===")
    print("%-28s %5s %7s %9s" % ("รูปแบบ","n","win%","net R"))
    for name in variants:
        d=res_all[name]
        if d['n']: print("%-28s %5d %6.1f%% %+9.2f  (R/ไม้ %+.3f)" % (name, d['n'], 100.0*d['w']/d['n'], d['r'], d['r']/d['n']))
    print("\n=== แยกตาม 'สวนทาง' vs 'ตามทาง' ===")
    print("%-28s %-9s %5s %7s %9s" % ("รูปแบบ","กลุ่ม","n","win%","net R"))
    for name in variants:
        for grp in ("สวนทาง","ตามทาง"):
            d=res[(name,grp)]
            if d['n']: print("%-28s %-9s %5d %6.1f%% %+9.2f" % (name,grp,d['n'],100.0*d['w']/d['n'],d['r']))

if __name__=="__main__":
    main()
