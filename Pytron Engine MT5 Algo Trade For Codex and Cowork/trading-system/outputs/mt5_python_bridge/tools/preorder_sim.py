# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ประเมิน "ออเดอร์ล่วงหน้า": ถ้าไม่ยิง market ทันที แต่ตั้ง limit ที่ราคาดีกว่า แล้วรอ
วัด 3 อย่าง: (1) ได้ไม้จริงกี่ % (2) ผล R เมื่อได้ (3) ไม้ที่พลาดไป (opportunity cost)
อ้างอิงออเดอร์จริง + SL/TP จริง + ราคา M1
"""
import json, io, datetime
import MetaTrader5 as mt5

SYM = 'XAUUSD.sml'
AUDIT = 'work/auto_trader_audit.jsonl'
now = datetime.datetime.now(datetime.timezone.utc)
cut = now - datetime.timedelta(days=6)

orders = []
with io.open(AUDIT, encoding='utf-8', errors='ignore') as fh:
    for line in fh:
        if '"order_result"' not in line: continue
        try: e = json.loads(line)
        except Exception: continue
        q = (e.get('result') or {}).get('request') or []
        if len(q) < 9: continue
        try: pr, sl, tp = float(q[5]), float(q[7]), float(q[8])
        except Exception: continue
        if not (pr > 0 and sl > 0 and tp > 0): continue
        side = 'buy' if sl < pr < tp else ('sell' if tp < pr < sl else None)
        if not side: continue
        try: t = datetime.datetime.fromisoformat(str(e.get('time')).replace('Z', '+00:00'))
        except Exception: continue
        if t < cut: continue
        orders.append((t, pr, sl, tp, side))
print("ออเดอร์จริง 6 วัน:", len(orders))

mt5.initialize()
atr_cache = {}
def atr_at(t):
    key = t.strftime('%Y%m%d%H')
    if key in atr_cache: return atr_cache[key]
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M15, t - datetime.timedelta(hours=20), t)
    val = 5.0
    if r is not None and len(r) > 5:
        trs = [float(b['high']) - float(b['low']) for b in r[-14:]]
        val = sum(trs) / len(trs)
    atr_cache[key] = val
    return val

def walk(t0, side, entry, sl, tp, limit_min):
    """เดินราคา M1 หลังเวลา t0 ถึง limit_min นาที → คืน (filled, R)"""
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M1, t0.replace(tzinfo=None),
                             (t0 + datetime.timedelta(minutes=limit_min)).replace(tzinfo=None))
    if r is None or len(r) == 0: return False, 0.0
    return None, 0.0   # ใช้ใน main แทน

def simulate(t0, side, p0, sl, tp, offset, valid_min):
    """limit ที่ราคาดีกว่า offset → รอ valid_min นาที → ถ้าได้ เดินไม้ถึง SL/TP"""
    lim = p0 - offset if side == 'buy' else p0 + offset
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M1, t0.replace(tzinfo=None),
                             (t0 + datetime.timedelta(minutes=valid_min + 720)).replace(tzinfo=None))
    if r is None or len(r) < 2: return None, 0.0
    fill_idx = None
    for i, b in enumerate(r):
        lo, hi = float(b['low']), float(b['high'])
        if i * 1 < valid_min:
            if (side == 'buy' and lo <= lim) or (side == 'sell' and hi >= lim):
                fill_idx = i; break
    if fill_idx is None: return False, 0.0
    risk = abs(lim - sl); rew = abs(tp - lim)
    if risk <= 0: return False, 0.0
    for b in r[fill_idx + 1:]:
        lo, hi = float(b['low']), float(b['high'])
        hs = lo <= sl if side == 'buy' else hi >= sl
        ht = hi >= tp if side == 'buy' else lo <= tp
        if hs and ht: return True, -1.0
        if hs: return True, -1.0
        if ht: return True, rew / risk
    return True, 0.0

for off_frac, valid in ((0.25, 15), (0.5, 15), (0.5, 30)):
    filled = missed = 0; r_sum = 0.0
    for (t, p0, sl, tp, side) in orders:
        off = atr_at(t) * off_frac
        ok, R = simulate(t, side, p0, sl, tp, off, valid)
        if ok is None: continue
        if ok: filled += 1; r_sum += R
        else: missed += 1
    tot = filled + missed
    if not tot: continue
    print("\n=== limit ถอย %.2f×ATR · รอ %d นาที ===" % (off_frac, valid))
    print("  ได้ไม้ %d/%d (%.0f%%) | พลาด %d | net R ของไม้ที่ได้ %+.2f | R/ไม้ %+.3f" % (
        filled, tot, 100.0 * filled / tot, missed, r_sum, r_sum / max(1, filled)))
mt5.shutdown()

# อ้างอิง: ยิง market ทันที (ผลจริงจากออเดอร์)
print("\n=== อ้างอิง: ยิง market ทันที (แบบปัจจุบัน) ===")
mt5.initialize()
tot_r = 0.0; n = 0
for (t, p0, sl, tp, side) in orders:
    risk = abs(p0 - sl); rew = abs(tp - p0)
    if risk <= 0: continue
    ok, R = simulate(t, side, p0, sl, tp, 0.0, 1)
    if ok: tot_r += R; n += 1
print("  ไม้ %d | net R %+.2f | R/ไม้ %+.3f" % (n, tot_r, tot_r / max(1, n)))
mt5.shutdown()
