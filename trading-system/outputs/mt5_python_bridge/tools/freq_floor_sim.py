# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""จำลองการบังคับใช้ 'ความถี่ขั้นต่ำ' (min_orders_per_day) ด้วยข้อมูลจริง

เทียบ 3 กติกา:
  A) กติกาปัจจุบัน : ไม่มีออเดอร์เลย >= freq_relax_hours (12 ชม. ปฏิทิน)
  B) กติกาง่าย    : อัตราไม้/วัน (ปฏิทิน) < min_orders_per_day
  C) กติกาที่ถูก  : อัตราไม้/วัน **นับเฉพาะเวลาตลาดเปิด** < min_orders_per_day
     (กันปัญหา: สุดสัปดาห์ตลาดปิด -> อัตราต่ำเทียม -> ผ่อนประตูทิ้งเปล่า ๆ)

อ่านอย่างเดียว ไม่แก้ไฟล์ใด ๆ
"""
import datetime
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "outputs", "mt5_python_bridge"))
from market_clock import market_open  # noqa: E402

AUDIT = os.path.join(ROOT, "work", "auto_trader_audit.jsonl")
FREQ_RELAX_HOURS = 12.0
MIN_ORDERS_PER_DAY = 2.0
WINDOW_HOURS = 24.0          # หน้าต่างวัดอัตรา
MIN_OPEN_HOURS = 6.0         # ต้องมีเวลาตลาดเปิดอย่างน้อยเท่านี้จึงตัดสินใจ

rows = []
with io.open(AUDIT, encoding="utf-8") as fh:
    for line in fh:
        try:
            rows.append(json.loads(line))
        except Exception:
            pass


def parse(ts):
    try:
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


events = [(parse(r.get("time", "")), r) for r in rows]
events = [(t, r) for t, r in events if t]
events.sort(key=lambda x: x[0])
orders = [t for t, r in events if r.get("event") == "order_result" and r.get("ok")]
start, end = events[0][0], events[-1][0]

print("ช่วงข้อมูล: " + start.isoformat()[:19] + " -> " + end.isoformat()[:19])
print("ออเดอร์สำเร็จทั้งหมด: " + str(len(orders)))
print("")


def active_hours_between(t1, t2, step_min=15):
    """นับชั่วโมงที่ 'ระบบเทรดรันอยู่' (จาก event started/stopped) และตลาดเปิด"""
    if t2 <= t1:
        return 0.0
    step = datetime.timedelta(minutes=step_min)
    hours = 0.0
    t = t1
    while t < t2:
        if market_open(t) and trader_running_at(t):
            hours += step_min / 60.0
        t += step
    return hours


# สร้างไทม์ไลน์ started/stopped ของตัวเทรด
life = []
for t, r in events:
    ev = r.get("event")
    if ev == "started":
        life.append((t, True))
    elif ev == "stopped":
        life.append((t, False))
life.sort(key=lambda x: x[0])


def trader_running_at(t):
    state = None
    for ts, on in life:
        if ts <= t:
            state = on
        else:
            break
    if state is None:
        # ก่อน event แรก: เดาว่ารันอยู่ (ระบบมีข้อมูลเทรดแล้ว)
        return True
    return state


def open_hours_between(t1, t2, step_min=15):
    """นับชั่วโมงที่ตลาดเปิดระหว่าง t1..t2"""
    if t2 <= t1:
        return 0.0
    step = datetime.timedelta(minutes=step_min)
    hours = 0.0
    t = t1
    while t < t2:
        if market_open(t):
            hours += step_min / 60.0
        t += step
    return hours


# ตารางประเมิน: ทุก 1 ชั่วโมง ตลอดช่วงข้อมูล
grid = []
t = start + datetime.timedelta(hours=WINDOW_HOURS)
while t <= end:
    grid.append(t)
    t += datetime.timedelta(hours=1)

print("จุดประเมินทั้งหมด: " + str(len(grid)) + " จุด (ทุก 1 ชม.)")
print("")

fire_a = fire_b = fire_c = 0
open_hours_total = open_hours_between(start, end)
calendar_days = (end - start).total_seconds() / 86400.0
print("วันปฏิทิน: " + str(round(calendar_days, 1)) + " วัน | ชั่วโมงตลาดเปิด: " + str(round(open_hours_total, 1)) + " ชม.")
print("อัตราจริง: " + str(round(len(orders) / calendar_days, 1)) + " ไม้/วันปฏิทิน | "
      + str(round(len(orders) / max(open_hours_total / 24.0, 0.001), 1)) + " ไม้/วันตลาดเปิด")
print("")

for t in grid:
    w0 = t - datetime.timedelta(hours=WINDOW_HOURS)
    win_orders = [o for o in orders if w0 <= o <= t]
    open_h = active_hours_between(w0, t)

    # A) กติกาเดิม: ไม่มีออเดอร์เลย >= 12 ชม. (ปฏิทิน)
    last_order = max([o for o in orders if o <= t], default=None)
    silent_h = (t - last_order).total_seconds() / 3600.0 if last_order else 999.0
    if len(win_orders) == 0 and silent_h >= FREQ_RELAX_HOURS:
        fire_a += 1

    # B) อัตราไม้/วันปฏิทิน < ขั้นต่ำ
    rate_cal = len(win_orders) / (WINDOW_HOURS / 24.0)
    if rate_cal < MIN_ORDERS_PER_DAY:
        fire_b += 1

    # C) อัตราไม้/วัน "ตลาดเปิด + ระบบรัน" < ขั้นต่ำ (ต้องมีเวลาจริงพอ)
    if open_h >= MIN_OPEN_HOURS:
        rate_open = len(win_orders) / (open_h / 24.0)
        if rate_open < MIN_ORDERS_PER_DAY:
            fire_c += 1

print("=== ผลจำลอง: จำนวนจุดที่กติกาจะสั่งผ่อน band ===")
print("  A) กติกาปัจจุบัน (เงียบ 12 ชม. ปฏิทิน)      : " + str(fire_a) + " / " + str(len(grid)) + " จุด")
print("  B) อัตรา/วันปฏิทิน < " + str(MIN_ORDERS_PER_DAY) + "            : " + str(fire_b) + " / " + str(len(grid)) + " จุด")
print("  C) อัตรา/วันตลาดเปิด < " + str(MIN_ORDERS_PER_DAY) + " (เสนอ)     : " + str(fire_c) + " / " + str(len(grid)) + " จุด")
print("")

# วิเคราะห์รายวัน: วันไหนอัตราต่ำกว่าขั้นต่ำ
print("=== รายวัน (นับเฉพาะวันที่มี 'ตลาดเปิด + ระบบรัน' อย่างน้อย "
      + str(MIN_OPEN_HOURS) + " ชม.) ===")
low_days = 0
open_days = 0
day = start.date()
while day <= end.date():
    d0 = datetime.datetime.combine(day, datetime.time(0, 0), tzinfo=start.tzinfo)
    d1 = d0 + datetime.timedelta(days=1)
    n = len([o for o in orders if d0 <= o < d1])
    ah = active_hours_between(d0, d1)
    if ah >= MIN_OPEN_HOURS:
        open_days += 1
        rate = n / (ah / 24.0)
        flag = ""
        if rate < MIN_ORDERS_PER_DAY:
            flag = "  <-- ต่ำกว่าขั้นต่ำ"
            low_days += 1
        print("  " + str(day) + " : " + str(n).rjust(3) + " ไม้ | ระบบรัน+ตลาดเปิด "
              + str(round(ah, 1)).rjust(5) + " ชม. | " + str(round(rate, 1)).rjust(5) + " ไม้/วัน" + flag)
    day += datetime.timedelta(days=1)

print("")
print("สรุป: วันที่มีเวลาจริงเพียงพอ " + str(open_days) + " วัน · ในนั้นต่ำกว่าขั้นต่ำ "
      + str(low_days) + " วัน (" + str(round(100.0 * low_days / max(open_days, 1), 1)) + "%)")
