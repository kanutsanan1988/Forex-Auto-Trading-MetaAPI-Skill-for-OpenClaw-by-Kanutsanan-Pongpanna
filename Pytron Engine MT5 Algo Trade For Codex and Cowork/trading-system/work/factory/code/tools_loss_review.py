# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ตรวจออเดอร์ขาดทุนย้อนหลัง (ไม่เกิน 10 ไม้) + แยก "สวนแนวโน้ม/ตามแนวโน้ม" + หาช่วงขาดทุนติดกัน"""
import datetime, collections
import MetaTrader5 as mt5

mt5.initialize()
SYM = 'XAUUSD.sml'
to = datetime.datetime.now() + datetime.timedelta(days=1)
frm = datetime.datetime.now() - datetime.timedelta(days=5)
deals = mt5.history_deals_get(frm, to) or []
by_pos = collections.defaultdict(dict)
for d in deals:
    if d.symbol != SYM: continue
    if d.entry == 0: by_pos[d.position_id]['in'] = d
    elif d.entry == 1: by_pos[d.position_id]['out'] = d

def trend_at(t):
    """แนวโน้ม H1 ก่อนเข้าไม้: ดูราคาย้อนหลัง 6 ชม. จาก M15"""
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M15, t - datetime.timedelta(hours=6), t)
    if r is None or len(r) < 4: return '?'
    chg = float(r[-1]['close']) - float(r[0]['close'])
    if chg > 3: return 'ขึ้น'
    if chg < -3: return 'ลง'
    return 'ออกข้าง'

rows = []
for pid, v in by_pos.items():
    if 'in' not in v or 'out' not in v: continue
    i, o = v['in'], v['out']
    t_in = datetime.datetime.fromtimestamp(i.time)
    side = 'BUY' if i.type == 0 else 'SELL'
    tr = trend_at(t_in)
    counter = (side == 'BUY' and tr == 'ลง') or (side == 'SELL' and tr == 'ขึ้น')
    rows.append(dict(t=t_in, side=side, trend=tr, counter=counter, net=o.profit,
                     price_in=i.price, price_out=o.price, comment=(i.comment or '').strip()[:22],
                     dur=int((o.time - i.time) / 60)))
rows.sort(key=lambda x: x['t'])
print("ไม้ปิดใน 48 ชม.:", len(rows), "| รวม net $%+.2f" % sum(r['net'] for r in rows))

loss = [r for r in rows if r['net'] < 0]
print("\n=== ออเดอร์ขาดทุน 10 ไม้ล่าสุด ===")
print("%-16s %-5s %-7s %-8s %9s %9s %8s %6s %s" % ("เวลาเข้า", "ฝั่ง", "แนวโน้ม", "ประเภท", "เข้า", "ออก", "net $", "นาที", "กลยุทธ์"))
for r in loss[-10:]:
    print("%-16s %-5s %-7s %-8s %9.2f %9.2f %+8.2f %6d %s" % (
        r['t'].strftime('%d/%m %H:%M'), r['side'], r['trend'],
        'สวน' if r['counter'] else 'ตาม', r['price_in'], r['price_out'], r['net'], r['dur'], r['comment']))

c = [r for r in rows if r['counter']]
w = [r for r in rows if not r['counter']]
print("\n=== สรุป: สวนแนวโน้ม vs ตามแนวโน้ม (48 ชม.) ===")
for name, g in (("สวนแนวโน้ม", c), ("ตามแนวโน้ม", w)):
    if not g: continue
    win = sum(1 for r in g if r['net'] > 0)
    print("%-10s n=%2d  win=%4.1f%%  net $%+7.2f  เฉลี่ย $%+.3f/ไม้" % (
        name, len(g), 100.0 * win / len(g), sum(r['net'] for r in g), sum(r['net'] for r in g) / len(g)))

print("\n=== ช่วงขาดทุนติดกัน (streak) ===")
st = 0; best = 0; runs = []
for r in rows:
    if r['net'] < 0:
        st += 1; best = max(best, st)
    else:
        if st >= 2: runs.append((st, r['t']))
        st = 0
if st >= 2: runs.append((st, None))
print("ขาดทุนติดกันสูงสุด:", best, "ไม้ | ช่วงที่ติดกัน ≥2:", len(runs), "ครั้ง")
mt5.shutdown()
