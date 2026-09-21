<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->

<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# 🔬 งานวิจัย: Auto-Threshold (36 ค่า) + Market Hours

วันที่: 2026-09-12 08:40 (ตามไทย) — ตลาดปิดสุดสัปดาห์
ข้อมูลอ้างอิง: `auto-threshold-stats/latest.json` (15,358 records จากทุกการเช็คราย 1 นาทีของ python) + audit + งานวิจัยก่อนหน้า

---

## ส่วนที่ 1: วิเคราะห์ช่วงคะแนนจริง 36 ค่า (ข้อมูลสะสม)

### 1.1 ค่าเฉลี่ยของ raw score ต่อกลยุทธ์ (n=2,857/ตัวหลัก)
| strategy_side | mean raw | p25 | p50 | p75 | p90 | max | pass% ปัจจุบัน |
|---|---|---|---|---|---|---|---|
| trend_buy | 0.376 | 0.268 | 0.365 | 0.468 | 0.601 | 0.764 | 10.5% |
| trend_sell | 0.452 | 0.265 | 0.367 | 0.634 | 0.821 | 0.948 | 23.7% |
| range_buy | 0.183 | 0.087 | 0.170 | 0.249 | 0.347 | 0.713 | 10.6% |
| range_sell | 0.156 | 0.073 | 0.148 | 0.211 | 0.278 | 0.622 | 4.3% |
| mean_reversion_buy | 0.126 | 0.053 | 0.094 | 0.169 | 0.285 | 0.603 | 10.6% |
| mean_reversion_sell | 0.096 | 0.043 | 0.074 | 0.137 | 0.184 | 0.576 | 2.7% |
| counter_trend_buy | 0.262 | 0.129 | 0.240 | 0.382 | 0.485 | 0.813 | 22.6% |
| counter_trend_sell | 0.296 | 0.188 | 0.295 | 0.402 | 0.485 | 0.578 | 31.0% |
| breakout_buy | 0.932 | 0.914 | 0.958 | 0.978 | 0.987 | 0.999 | 42.3% |
| breakout_sell | 0.942 | 0.913 | 0.965 | 0.991 | 0.996 | 1.000 | 44.9% |
| breakout_reversal_buy | 0.813 | 0.776 | 0.821 | 0.827 | 0.840 | 0.926 | 92.6% |
| breakout_reversal_sell | 0.796 | 0.749 | 0.799 | 0.830 | 0.889 | 0.919 | 92.9% |

### 1.2 ข้อค้นพบสำคัญ (KEY INSIGHTS)
1. **3 กลุ่มสเกลชัดเจน:**
   - กลุ่ม "ต่ำ" (range/MR): mean 0.10-0.18 — สัญญาณอ่อนบ่อย ต้อง threshold ต่ำ
   - กลุ่ม "กลาง" (trend/CT): mean 0.26-0.45
   - กลุ่ม "สูง" (breakout/BR): mean 0.80-0.94 — สัญญาณ rare แต่ strong มาก
2. **pass% ต่างกันสุดขั้ว:** breakout_reversal 92.9% vs mean_reversion_sell 2.7% — threshold ปัจจุบัน**ล็อกสเกลไม่เท่ากัน** (BR หลวมเกินไป, MR_sell แน่นเกินไป)
3. **probability คงที่ 0.53-0.60** (ตั้ง manual ไว้) → ยังไม่ได้สะท้อน win-rate จริงจากประวัติ (ต้องปรับเมื่อข้อมูลพอ)
4. **weighted ≈ raw** (เพราะ weight=1.0) → ยังไม่ได้ใช้ประโยชน์ของ directional weight

---

## ส่วนที่ 2: ออกแบบระบบ Auto-Threshold (36 ค่า) — ตัวเลือก 3 แบบ

### แบบ A: Rolling Percentile (แนะนำเริ่มต้น ✅)
- **หลักการ:** ทุก N นาที คำนวณ percentile ของ raw/prob/weighted ต่อ strategy_side จากหน้าต่างเลื่อน (เช่น 500-1000 บันทึกล่าสุด)
- **สูตร:** threshold_low = p60, threshold_high = p90 ของแต่ละ metric (อัตโนมัติ)
- **ข้อดี:** ง่าย, robust, ใช้ข้อมูลจริงตรงๆ, ไม่ต้องเทรนโมเดล
- **ข้อเสีย:** ช้าเรียนรู้กับ regime ใหม่; percentile เป็นแค่ตำแหน่ง ไม่ใช่คุณภาพ

### แบบ B: Performance-Aware (ตามผลจริง) — ปรับเมื่อ win-rate
- **หลักการ:** ดู win-rate / expectancy ต่อ strategy_side แบบกลุ่ม score (bin 0-0.2, 0.2-0.4 ...)
- **สูตร:** threshold = จุดที่ expectancy เริ่มเป็นบวก (break-even score) จากกราฟข้อมูล
- **ข้อดี:** ตอบโจทย์ "สาเหตุกำไร/ขาดทุน" ตรงตัว; ปรับตามคุณภาพจริง
- **ข้อเสีย:** ต้องมี samples มากพอต่อ bin (บัญชี $12 ตอนนี้ยังน้อย)

### แบบ C: Hybrid Auto-Threshold (เต็มรูปแบบ — เป้าหมายสุดท้าย ✅)
ผสม A+B + วงรอบปิด:
1. **เลื่อน percentile** (A) ตั้งขอบล่าง/บนเริ่มต้น
2. **กลุ่ม win-rate** (B) ปรับให้ threshold ขยับขึ้นเมื่อ win-rate ต่ำ (กรองสัญญาณแย่), ขยับลงเมื่อสัญญาณดี
3. **ฮิสเทอรีซิส + deadband** ป้องกันแกว่ง: เปลี่ยน threshold เฉพาะเมื่อเปลี่ยน > 0.02 และมี samples ≥ 30 ต่อกลยุทธ์
4. **ลง audit + research log** ทุกครั้งที่ threshold เปลี่ยน (โปร่งใส)
5. **killer guard:** ไม่เปิดเทรดдถ้า threshold เปลี่ยนเร็วเกิน (churn guard) — ป้องกัน overfit

**โครงสร้าง config ที่เสนอ (auto_config.json):**
```json
"auto_threshold": {
  "enabled": false,            // เปิดเมื่อ user อนุมัติ
  "mode": "hybrid",            // percentile | performance | hybrid
  "window_records": 1000,      // หน้าต่างเลื่อน
  "low_percentile": 60,
  "high_percentile": 90,
  "min_samples_per_strategy": 30,
  "min_change_to_apply": 0.02,
  "deadband": 0.02,
  "churn_guard_seconds": 3600
}
```

---

## ส่วนที่ 3: Market Hours XAUUSD (โปรแกรมเข้า python)

### 3.1 เวลาจริง (ยืนยันจาก MT5 tick)
- ตลาดทองคำ (XAUUSD) **ปิดสุดสัปดาห์**: ตั้งแต่ศุกร์ ~22:00 UTC (05:00 ตามไทย) จนถึง อาทิตย์ 22:00 UTC (05:00 ตามไทยวันจันทร์)
- **เปิด**: อาทิตย์ 22:00 UTC → ศุกร์ 22:00 UTC (5 วัน)
- ปิดพักกลางวันรายวัน: 21:00-22:00 UTC (04:00-05:00 ตามไทย)
- ยืนยันล่าสุด: tick 23:58 UTC ศุกร์, บาร์ M5 สุดท้าย 23:55 UTC, 01:39 UTC เสาร์ ไม่มีข้อมูล = ปิด

### 3.2 การโปรแกรมเข้าระบบ (ข้อเสนอ)
เพิ่มใน `auto_trader.py` (ฟังก์ชัน `market_open()`):
```python
def market_open(now_utc=None):
    now = now_utc or datetime.now(timezone.utc)
    wd = now.weekday()  # 0=Mon..6=Sun
    if wd == 5 or wd == 6:        # Sat/Sun
        if wd == 6:               # Sun: opens 22:00 UTC
            return now.hour >= 22
        return False              # Sat always closed
    if now.hour == 21:            # daily 21:00-22:00 UTC break
        return False
    return True
```
- ใช้ที่จุดเริ่ม loop: ถ้าตลาดปิด → sleep แล้วข้าม (ไม่ส่งคำสั่ง ไม่วิเคราะห์)
- เขียน audit event `market_closed` ทุก 10 นาทีตอนปิด (รู้ว่าระบบยังอยู่ แต่ไม่เทรดเพราะตลาดปิด)
- กันการส่งคำสั่งตอน spread กว้างตอนเปิดใหม่ (อาทิตย์ 22:00 UTC) — เช็ค spread gate เดิมช่วยอยู่แล้ว

### 3.3 เหตุผลสำคัญ
- ตอนนี้ระบบพยายามวิเคราะห์/เทรดตลอด 24/7 แม้ตลาดปิด → เสีย resource, ส่งคำสั่งติดไม่ได้, spread/quote ค้างจากคืนศุกร์
- การล็อก market hours = เทรดเฉพาะตอนมีราคาจริง + ลด error/เปลือง

---

## ส่วนที่ 4: คำแนะนำการนำไปใช้ (ลำดับ)
1. **โปรแกรม market hours** (3.2) — ทำได้ทันที ปลอดภัย กันเทรดตอนตลาดปิด
2. **เปิด auto_threshold แบบ A (percentile)** ก่อน — ง่าย ใช้ข้อมูลสะสม 15k records ได้ทันที
3. สะสมผล 2-4 สัปดาห์ แล้วเลื่อนเป็น **แบบ C hybrid** (เมื่อ win-rate samples เพียงพอ)
4. ทุกการเปลี่ยน threshold ต้อง: audit + เขียน research log + รายงาน user ผ่าน Telegram

**ข้อควรระวัง:** auto-threshold ต้องไม่แกว่งเร็วเกิน (overfit) — ใช้ deadband + min_samples + churn guard เสมอ; เงินจริงต้องยืนยันก่อนเปิดทุกครั้ง