# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""จำลอง "ระบบตัดขาดทุนใหม่" ที่เจ้าของระบบเสนอ
กติกา: ไม้เดิมกำลังขาดทุน + สัญญาณใหม่ (รอบถัดไป) ชี้ "สวนทางไม้เดิม" (ทิศที่ไม้เดิมขาดทุนเพิ่ม)
       → ตัดขาดทุนทันที แล้วเช็คเทรดใหม่
วัด: ถ้าตัดที่จังหวะสัญญาณสวนทางครั้งแรก เทียบกับผลจริง (ที่ปล่อยไปถึง SL/cut-loss)
"""
import json, io, datetime, collections
import MetaTrader5 as mt5

SYM = 'XAUUSD.sml'
USD_PER_UNIT = 0.10          # 0.001 lot ทองคำ: ราคาเคลื่อน $1 = $0.10
AUDIT = 'work/auto_trader_audit.jsonl'

# ---------- 1) รอบตัดสินใจจาก audit (เอาเฉพาะช่วง 6 วันล่าสุด) ----------
cut = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6)
rounds = []
with io.open(AUDIT, encoding='utf-8', errors='ignore') as fh:
    for line in fh:
        if '"event"' not in line: continue
        try: e = json.loads(line)
        except Exception: continue
        ev = e.get('event')
        if ev not in ('order_result', 'no_trade', 'dry_run_signal'): continue
        try: t = datetime.datetime.fromisoformat(str(e.get('time')).replace('Z', '+00:00'))
        except Exception: continue
        if t < cut: continue
        a = e.get('analysis') or {}
        side = a.get('side') or (a.get('router_decision') or {}).get('side')
        if side in ('buy', 'sell'):
            rounds.append((t, side))
rounds.sort()
print("รอบตัดสินใจ 6 วัน:", len(rounds))

# ---------- 2) ไม้จริงที่ปิดแล้ว ----------
mt5.initialize()
deals = mt5.history_deals_get(datetime.datetime.now() - datetime.timedelta(days=6),
                              datetime.datetime.now() + datetime.timedelta(days=1)) or []
by_pos = collections.defaultdict(dict)
for d in deals:
    if d.symbol != SYM: continue
    if d.entry == 0: by_pos[d.position_id]['in'] = d
    elif d.entry == 1: by_pos[d.position_id]['out'] = d

def price_at(t):
    r = mt5.copy_rates_range(SYM, mt5.TIMEFRAME_M1, t - datetime.timedelta(minutes=1), t + datetime.timedelta(minutes=2))
    if r is None or len(r) == 0: return None
    return float(r[-1]['close'])

rows = []
for pid, v in by_pos.items():
    if 'in' not in v or 'out' not in v: continue
    i, o = v['in'], v['out']
    t0 = datetime.datetime.fromtimestamp(i.time, datetime.timezone.utc)
    side = 'buy' if i.type == 0 else 'sell'
    net = float(o.profit + o.commission + o.swap + o.fee)
    rows.append(dict(t0=t0, side=side, p0=float(i.price), net=net, t1=datetime.datetime.fromtimestamp(o.time, datetime.timezone.utc)))
mt5.shutdown()
print("ไม้จริงที่ปิด:", len(rows))

# ---------- 3) หาจังหวะ "สัญญาณสวนทางครั้งแรก" ของแต่ละไม้ ----------
opp = {'buy': 'sell', 'sell': 'buy'}
mt5.initialize()
res = []
for r in rows:
    t_sig = None
    for (t, side) in rounds:
        if t <= r['t0'] or t > r['t1']: continue
        if side == opp[r['side']]:
            t_sig = t; break
    if t_sig is None: continue
    p2 = price_at(t_sig)
    if p2 is None: continue
    early = (p2 - r['p0']) * USD_PER_UNIT * (1 if r['side'] == 'buy' else -1) - 0.03  # หัก spread
    res.append(dict(early=early, real=r['net'], side=r['side'], t0=r['t0'], dur=(t_sig - r['t0']).total_seconds() / 60))
mt5.shutdown()

print("\n=== ผลจำลอง: ตัดขาดทุนเมื่อเจอสัญญาณสวนทางครั้งแรก ===")
print("%-18s %-5s %9s %9s %8s" % ("เวลาเข้า", "ฝั่ง", "ตัดเร็ว $", "ผลจริง $", "นาทีถึงสัญญาณ"))
for x in sorted(res, key=lambda z: z['t0'])[-12:]:
    print("%-18s %-5s %+9.2f %+9.2f %8.0f" % (x['t0'].strftime('%d/%m %H:%M'), x['side'], x['early'], x['real'], x['dur']))

loss = [x for x in res if x['real'] < 0]
allx = res
print("\n=== สรุป ===")
if loss:
    print("ไม้ที่ขาดทุนจริง %d ไม้: ผลจริง %+.2f | ตัดเร็ว %+.2f → ต่าง %+.2f" % (
        len(loss), sum(x['real'] for x in loss), sum(x['early'] for x in loss),
        sum(x['early'] for x in loss) - sum(x['real'] for x in loss)))
if allx:
    print("ทั้งชุด %d ไม้: ผลจริง %+.2f | ตัดเร็ว %+.2f → ต่าง %+.2f" % (
        len(allx), sum(x['real'] for x in allx), sum(x['early'] for x in allx),
        sum(x['early'] for x in allx) - sum(x['real'] for x in allx)))
win = [x for x in res if x['real'] > 0]
if win:
    print("(ไม้ที่กำไรจริง %d ไม้: ผลจริง %+.2f | ถ้าตัดเร็ว %+.2f → ต่าง %+.2f)" % (
        len(win), sum(x['real'] for x in win), sum(x['early'] for x in win),
        sum(x['early'] for x in win) - sum(x['real'] for x in win)))
