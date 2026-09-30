# -*- coding: utf-8 -*-
"""tpsl_review.py — ตัวตรวจ TP/SL เป็นอันดับแรกเมื่อมีการขาดทุน (กติกาถาวร 30 ก.ย. 2026)

★ กติกาเจ้าของระบบ: "ถ้ามีการขาดทุนเกิดขึ้นก็ต้องไปดู TP และ SL ก่อนเป็นอันดับแรกเลยนะครับ
   ตั้งไว้เป็นกติกาถาวร" → เครื่องมือนี้ต้องถูกเรียกก่อนเครื่องมือวิเคราะห์อื่นทุกครั้งที่มีไม้แพ้

ตอบ 4 คำถาม:
  1) ไม้แพ้ชน SL เต็มระยะ หรือถูกตัดก่อน? (เทียบ |net| กับความเสี่ยงที่ตั้งไว้)
  2) SL ถูกตั้งกี่เท่าของ ATR และสเปรดกินไปกี่ % ของระยะ SL
  3) **การชน SL เป็น "การถูกเขี่ย" (whipsaw) หรือไม่** — ราคาไปถึง TP ในภายหลังหรือเปล่า
  4) อัตราชนะที่ต้องได้เพื่อเสมอทุน (จาก R:R จริง) เทียบกับอัตราชนะที่ทำได้จริง

อ่านจากบันทึกจริงเท่านั้น · ไม่ใช้ AI · ต้นทุน $0 · ไม่แก้ค่าใด ๆ
ใช้:  .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/tpsl_review.py --days 2
"""
import argparse
import collections
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def find_root():
    cur = HERE
    for _ in range(6):
        if os.path.exists(os.path.join(cur, 'work', 'auto_trader_audit.jsonl')):
            return cur
        cur = os.path.dirname(cur)
    raise SystemExit('ไม่พบบันทึก work/auto_trader_audit.jsonl')


ROOT = find_root()
AUDIT = os.path.join(ROOT, 'work', 'auto_trader_audit.jsonl')


def load(days):
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    orders, closed, prices = {}, [], []
    for ln in io.open(AUDIT, encoding='utf-8', errors='replace'):
        if not any(k in ln for k in ('"order_result"', '"position_closed"', '"no_trade"', '"skip"')):
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        try:
            t = dt.datetime.fromisoformat(str(d.get('time')).replace('Z', '+00:00'))
        except Exception:
            continue
        if t < cut:
            continue
        ev = d.get('event')
        a = d.get('analysis') or {}
        if ev == 'order_result' and d.get('ok'):
            r = d.get('result') or {}
            pid = r.get('order')
            if pid and a.get('sl') and a.get('tp'):
                orders[pid] = dict(a, t=t)
        elif ev == 'position_closed':
            closed.append(dict(d, t=t))
        # เส้นเวลาราคา: ทุกรอบที่ระบบอ่านราคา (มี entry = ราคาตลาดขณะนั้น)
        if a.get('entry') and a.get('sl'):
            prices.append((t, float(a['entry']), str(a.get('side') or '')))
    prices.sort()
    return orders, closed, prices


def main():
    ap = argparse.ArgumentParser(description='ตรวจ TP/SL ของไม้แพ้ (กติกาถาวร)')
    ap.add_argument('--days', type=float, default=2.0)
    ap.add_argument('--whipsaw-minutes', type=float, default=90.0,
                    help='ดูราคาต่อไปกี่นาทีหลังชน SL เพื่อตัดสินว่าเป็นการถูกเขี่ย')
    args = ap.parse_args()

    orders, closed, prices = load(args.days)
    rows = []
    for c in closed:
        o = orders.get(c.get('position_id'))
        if not o:
            continue
        ent, sl, tp = float(o['entry']), float(o['sl']), float(o['tp'])
        side = str(o.get('side'))
        sl_d, tp_d = abs(ent - sl), abs(tp - ent)
        risk = float(o.get('risk_usd') or 0)
        net = float(c.get('net') or 0)
        # ราคาหลังปิดไม้: ไปถึง TP หรือไม่ (สำหรับไม้แพ้)
        reached_tp = None
        if sl_d and tp_d:
            horizon = c['t'] + dt.timedelta(minutes=args.whipsaw_minutes)
            for t, p, s in prices:
                if t <= c['t'] or t > horizon:
                    continue
                if side == 'buy' and p >= tp:
                    reached_tp = t
                    break
                if side == 'sell' and p <= tp:
                    reached_tp = t
                    break
        rows.append({'o': o, 'net': net, 'risk': risk, 'sl_d': sl_d, 'tp_d': tp_d,
                     'side': side, 'strategy': o.get('strategy'), 'spread': float(o.get('spread') or 0),
                     'reached_tp': reached_tp, 't': c['t']})

    if not rows:
        print('ไม่พบไม้ที่ปิดพร้อมข้อมูลราคาเข้า/SL/TP ในช่วงที่เลือก')
        return

    print("═══ 1) กติกาถาวร: ตรวจ TP/SL ของไม้ที่ปิด (%g วันล่าสุด) ═══" % args.days)
    print("   ไม้ที่ตรวจได้: %d (ชนะ %d · แพ้ %d)" % (
        len(rows), sum(1 for r in rows if r['net'] > 0), sum(1 for r in rows if r['net'] < 0)))
    full_sl = [r for r in rows if r['net'] < 0 and r['risk'] and abs(r['net']) / r['risk'] > 0.85]
    cut_early = [r for r in rows if r['net'] < 0 and r['risk'] and abs(r['net']) / r['risk'] <= 0.85]
    print("   แพ้แบบชน SL เต็มระยะ: %d ไม้ · แพ้แบบถูกตัดก่อนถึง SL: %d ไม้" % (len(full_sl), len(cut_early)))

    print()
    print("═══ 2) ระยะ SL/TP ที่ตั้งจริง ═══")
    rr = [r['tp_d'] / r['sl_d'] for r in rows if r['sl_d']]
    spr = [100.0 * r['spread'] / r['sl_d'] for r in rows if r['sl_d']]
    print("   ระยะ SL = ค่าตั้ง × ATR(M5) — ค่าตั้งปัจจุบัน 1.20 (แอดมินบอทปรับได้ 0.80–2.00)")
    print("   R:R ที่ใช้จริง เฉลี่ย %.2f · สเปรดกิน %.1f%% ของระยะ SL (เฉลี่ย)" % (
        sum(rr) / len(rr) if rr else 0, sum(spr) / len(spr) if spr else 0))
    be = [1.0 / (1.0 + x) * 100.0 for x in rr]
    print("   → อัตราชนะที่ต้องได้เพื่อเสมอทุน (หลังหักสเปรด): %.1f%%" % (
        sum(be) / len(be) if be else 0))
    wins = [r for r in rows if r['net'] > 0]
    print("   → อัตราชนะที่ทำได้จริงในช่วงนี้: %.1f%%" % (100.0 * len(wins) / len(rows)))

    print()
    print("═══ 3) วินิจฉัยการชน SL: ถูกเขี่ย (whipsaw) หรือไม่ ═══")
    ws = [r for r in full_sl if r['reached_tp']]
    print("   ในไม้ที่ชน SL เต็มระยะ %d ไม้ → ราคาไปถึง TP ในภายหลัง (ภายใน %g นาที) = %d ไม้" % (
        len(full_sl), args.whipsaw_minutes, len(ws)))
    if full_sl:
        print("   ⇒ สัดส่วนถูกเขี่ย: %.0f%%" % (100.0 * len(ws) / len(full_sl)))
    for r in full_sl[-6:]:
        t = r['t'].astimezone(dt.timezone(dt.timedelta(hours=7))).strftime('%d/%m %H:%M')
        tag = ('ถึง TP ภายหลัง %s' % r['reached_tp'].astimezone(
            dt.timezone(dt.timedelta(hours=7))).strftime('%H:%M')) if r['reached_tp'] else 'ราคาไม่กลับไปถึง TP'
        print("     %s · %-4s %-12s SL %.2f จุด · สเปรด %.0f%% · net %+.2f → %s" % (
            t, r['side'], str(r['strategy'])[:12], r['sl_d'],
            100.0 * r['spread'] / r['sl_d'] if r['sl_d'] else 0, r['net'], tag))

    print()
    print("═══ 4) สรุปรายกลยุทธ์ (ใช้ตัดสิน TP/SL) ═══")
    by = collections.defaultdict(lambda: {'n': 0, 'w': 0, 'net': 0.0, 'full': 0, 'ws': 0})
    for r in rows:
        d = by[str(r['strategy'])]
        d['n'] += 1
        d['net'] += r['net']
        if r['net'] > 0:
            d['w'] += 1
        if r in full_sl:
            d['full'] += 1
            if r['reached_tp']:
                d['ws'] += 1
    for k, d in sorted(by.items(), key=lambda x: -x[1]['n']):
        print("   %-16s ไม้=%2d ชนะ=%.0f%% สุทธิ=%+.2f ชน-SLเต็ม=%d ถูกเขี่ย=%d" % (
            k, d['n'], 100.0 * d['w'] / d['n'], d['net'], d['full'], d['ws']))

    print()
    print("═══ 5) ข้อสรุป + สิ่งที่ต้องทำต่อ ═══")
    share = (100.0 * len(ws) / len(full_sl)) if full_sl else 0.0
    if share >= 50.0:
        print("   ⚠ SL ถูกเขี่ยสูง (%.0f%%) → ควรทดลองขยายระยะ SL (เช่น 1.20 → 1.50 × ATR)" % share)
        print("     และ/หรือ เพิ่ม R:R (ปัจจุบัน %.2f) — **ต้องจำลองก่อนเปิดใช้จริง**" % (sum(rr) / len(rr) if rr else 0))
    elif full_sl:
        print("   SL ถูกเขี่ยต่ำ (%.0f%%) → การแพ้เป็นไปตามทิศทางตลาด ไม่ใช่ระยะ SL แคบเกิน" % share)
    print("   ตรวจต่อ: ระยะ SL = 1.20×ATR · TP = 1.30×SL · สเปรด %.0f–%.0f%% ของระยะ SL กินกำไรจริง" % (
        min(spr) if spr else 0, max(spr) if spr else 0))


if __name__ == '__main__':
    main()
