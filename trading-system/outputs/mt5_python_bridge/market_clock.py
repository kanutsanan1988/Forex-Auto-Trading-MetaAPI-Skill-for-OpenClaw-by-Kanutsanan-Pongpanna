# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Market Clock for XAUUSD (gold) — ห้ามเทรดตอนตลาดปิด

★ แก้ 19 ก.ย. 2026 (เจ้าของระบบอนุมัติ): เดิมใช้ตารางเวลาเดียวตลอดปี = เวลามาตรฐานสหรัฐฯ
  ทำให้ช่วงที่สหรัฐฯ ใช้ DST (มี.ค.–พ.ย.) ระบบเข้าใจเวลาผิดไป 1 ชั่วโมง
  (คิดว่าตลาดเปิด 22:00 UTC ทั้งที่จริงเปิด 22:00 เฉพาะช่วง DST · ช่วงเวลามาตรฐานเปิด 23:00)

ตารางจริงของทองคำ (CME/COMEX · 18:00 ET เปิด อาทิตย์ → 17:00 ET ปิดศุกร์ · พักวันละ 60 นาทีที่ 17:00 ET):
  • ใช้ DST (EDT, UTC-4): เปิด 22:00 UTC · พัก 21:00–22:00 UTC · ปิดศุกร์ 21:00 UTC
  • เวลามาตรฐาน (EST, UTC-5): เปิด 23:00 UTC · พัก 22:00–23:00 UTC · ปิดศุกร์ 22:00 UTC

หมายเหตุ: ถ้าต้องการยึดเวลาจากโบรกเกอร์จริง ให้เทียบกับแท่ง M1 ของ symbol
(ตอนตรวจยังดึงประวัติไม่ได้เพราะตลาดปิด — ถ้ามีประวัติแล้วควรตรวจซ้ำ)
"""
import datetime

OPEN_HOUR_UTC = 22    # ค่าเริ่มต้น/อ้างอิงเดิม (ช่วง DST)
CLOSE_HOUR_UTC = 22   # ค่าเดิม (ช่วงเวลามาตรฐาน) — ดู market_hours() สำหรับค่าที่ใช้จริง


def _nth_sunday(year: int, month: int, n: int) -> datetime.date:
    """อาทิตย์ที่ n ของเดือน"""
    d = datetime.date(year, month, 1)
    offset = (6 - d.weekday()) % 7          # Mon=0 … Sun=6
    return d + datetime.timedelta(days=offset + 7 * (n - 1))


def us_dst_active(now_utc: datetime.datetime | None = None) -> bool:
    """สหรัฐฯ ใช้ DST อยู่ไหม (เริ่มอาทิตย์ที่ 2 มี.ค. 07:00 UTC · สิ้นสุดอาทิตย์ที่ 1 พ.ย. 06:00 UTC)"""
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    y = now.year
    start = datetime.datetime.combine(_nth_sunday(y, 3, 2), datetime.time(7, 0),
                                      tzinfo=datetime.timezone.utc)
    end = datetime.datetime.combine(_nth_sunday(y, 11, 1), datetime.time(6, 0),
                                    tzinfo=datetime.timezone.utc)
    return start <= now < end


def market_hours(now_utc: datetime.datetime | None = None) -> tuple[int, int]:
    """→ (ชั่วโมงเปิด UTC ของวันอาทิตย์, ชั่วโมงพัก/ปิด UTC)

    DST:  (22, 21)  ·  เวลามาตรฐาน: (23, 22)
    """
    if us_dst_active(now_utc):
        return 22, 21
    return 23, 22


def market_open(now_utc: datetime.datetime | None = None) -> bool:
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    wd = now.weekday()  # 0=Mon ... 6=Sun
    hour = now.hour
    open_hour, break_hour = market_hours(now)
    if wd == 5:      # วันเสาร์: ปิดทั้งวัน
        return False
    if wd == 6:      # วันอาทิตย์: เปิดตั้งแต่ open_hour UTC
        return hour >= open_hour
    if wd == 4 and hour >= break_hour:   # วันศุกร์: ปิดตั้งแต่ break_hour UTC
        return False
    if hour == break_hour:   # พักรายวัน 60 นาที (จ.–พฤ.)
        return False
    return True


def next_open_delta(now_utc: datetime.datetime | None = None) -> float:
    """วินาทีจนกว่าตลาดจะเปิด (ใช้ sleep ยาวๆ ตอนปิดได้)"""
    now = now_utc or datetime.datetime.now(datetime.timezone.utc)
    if market_open(now):
        return 0.0
    # Session boundaries are on whole hours. Preserve neither the current minute
    # nor seconds, otherwise e.g. 21:37 incorrectly waits until 22:37, not 22:00.
    n = now.replace(minute=0, second=0, microsecond=0)
    for _ in range(8 * 24):  # มองไปสูงสุด 8 วัน
        n = n + datetime.timedelta(hours=1)
        if market_open(n):
            return (n - now).total_seconds()
    return 24 * 3600.0


if __name__ == "__main__":
    now = datetime.datetime.now(datetime.timezone.utc)
    print("now UTC:", now.isoformat())
    print("US DST active:", us_dst_active(now))
    print("market_hours (open, break):", market_hours(now))
    print("market_open:", market_open(now))
    print("next_open_delta hours:", round(next_open_delta(now) / 3600.0, 2))
