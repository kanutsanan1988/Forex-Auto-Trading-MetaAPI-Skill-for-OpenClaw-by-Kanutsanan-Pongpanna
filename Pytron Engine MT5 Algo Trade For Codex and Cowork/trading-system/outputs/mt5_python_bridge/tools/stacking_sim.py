# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ประเมิน: ถ้าปล่อยให้มีไม้ซ้อนกันได้ N ไม้ (1, 2, 5, 10, ไม่จำกัด)
รีเพลย์ออเดอร์จริง 48 ชม. + ราคา M1 → วัดจำนวนไม้ที่ได้เทรด, net R, จุดต่ำสุดของ equity
"""
import json, io, datetime
import MetaTrader5 as mt5

rows = [json.loads(l) for l in io.open('work/auto_trader_audit.jsonl', encoding='utf-8') if l.strip()]
now = datetime.datetime.now(datetime.timezone.utc)

def age_h(t):
    try: return (now - datetime.datetime.fromisoformat(str(t).replace('Z', '+00:00'))).total_seconds() / 3600
    except Exception: return 9e9

orders = []
for e in rows:
    if e.get('event') != 'order_result' or age_h(e.get('time')) > 48: continue
    q = (e.get('result') or {}).get('request') or []
    if len(q) < 9: continue
    try: pr, sl, tp = float(q[5]), float(q[7]), float(q[8])
    except Exception: continue
    if not (pr > 0 and sl > 0 and tp > 0): continue
    side = 'buy' if sl < pr < tp else ('sell' if tp < pr < sl else None)
    if not side: continue
    try: t = datetime.datetime.fromisoformat(str(e['time']).replace('Z', '+00:00'))
    except Exception: continue
    orders.append((t, pr, sl, tp, side))

print("ออเดอร์ 48 ชม.ล่าสุด:", len(orders))
mt5.initialize()
margin_per = None
try:
    ti = mt5.symbol_info_tick('XAUUSD.sml')
    if ti: margin_per = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, 'XAUUSD.sml', 0.001, ti.ask)
except Exception: pass
trades = []
for t, pr, sl, tp, side in orders:
    r = mt5.copy_rates_range('XAUUSD.sml', mt5.TIMEFRAME_M1, t.replace(tzinfo=None),
                             (t + datetime.timedelta(hours=12)).replace(tzinfo=None))
    if r is None or len(r) < 3: continue
    risk = abs(pr - sl); rew = abs(tp - pr)
    exit_t, R = None, None
    for b in r[1:]:
        hi, lo = float(b['high']), float(b['low'])
        hs = lo <= sl if side == 'buy' else hi >= sl
        ht = hi >= tp if side == 'buy' else lo <= tp
        bt = datetime.datetime.fromtimestamp(b['time'], datetime.timezone.utc)
        if hs and ht: exit_t, R = bt, -1.0; break
        if hs: exit_t, R = bt, -1.0; break
        if ht: exit_t, R = bt, (rew / risk if risk else 0.0); break
    if exit_t is None:
        exit_t, R = t + datetime.timedelta(hours=12), 0.0
    trades.append((t, exit_t, R))
mt5.shutdown()
trades.sort()
print("คำนวณผลได้:", len(trades), "ไม้")
if margin_per: print("margin ต่อไม้ 0.001 lot ≈ $%.2f" % margin_per)

print("\n%-12s %7s %8s %7s %9s %10s %9s" % ("จำนวนไม้ซ้อน", "เทรดได้", "ข้ามไป", "win%", "net R", "R/ไม้", "จุดต่ำสุด"))
for cap in (1, 2, 5, 10, 999):
    live, taken, skipped = [], [], 0
    for t0, t1, R in trades:
        live = [x for x in live if x > t0]
        if len(live) < cap:
            live.append(t1); taken.append(R)
        else:
            skipped += 1
    net = sum(taken); w = sum(1 for x in taken if x > 0)
    cum = 0.0; low = 0.0
    for x in taken:
        cum += x; low = min(low, cum)
    label = "ไม่จำกัด" if cap == 999 else str(cap)
    print("%-12s %7d %8d %6.1f%% %+9.2f %+10.3f %+9.2f" % (
        label, len(taken), skipped, 100.0 * w / max(1, len(taken)), net, net / max(1, len(taken)), low))
