<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# ภาคผนวก: Auto-Threshold v2 — "ฉลาดจริง" (ปรับเฉพาะตัวที่ควรปรับ)

วันที่: 2026-09-12 09:30 ต่อจาก `2026-09-12-auto-threshold-design.md`

## กติกา "ปรับเฉพาะตัวที่ต้องปรับจริงๆ" (implement แล้ว)
1. **ข้อมูลไม่พอ → ไม่ยุ่ง** — ต้องมี samples ≥ 30 (ต่อ strategy_side) ถึงจะคิด
2. **อยู่ใน band ที่แนะนำแล้ว → ข้าม** — deviation < deadband (0.02) = ไม่ขยับ
3. **churn guard รายตัว** — แต่ละ key (36 ตัว) มี last_update แยก; ปรับถี่กว่า 1 ชม. ไม่ได้
4. **performance-aware** — มี closed trades ≥ 8 ตัว → ใช้ win-rate:
   - win-rate < 0.40 → ยก low ขึ้น (กรองสัญญาณแย่)
   - win-rate > 0.55 → ลด low ลง (เปิดรับสัญญาณดี)
5. **Reversal-risk (ขอบบน)** — ตามที่ user เน้น: คะแนนสูงเกินไปเสี่ยงกลับตัว
   - ถ้า win-rate ต่ำ + high band สูง → **ลด raw_max ลง** (ห้ามเทรดตอนสุดขั้ว)
6. **โปร่งใส** — ทุกการปรับ เขียน `auto_threshold_update` audit {key, from, to, reason}

## ผลการรันจริง (ข้อมูล 15k+ records)
- ปรับจริงแค่ตัวที่ deviate: trend_buy → [0.244, 0.361]
- ตัวอื่น (range/MR/breakout/BR/trend_sell/CT) อยู่ band → ข้าม ไม่แตะ
- = "ตัวไหนขยับก็ปรับตัวนั้น" ตรงตามที่ user กำหนด

## โครงสร้าง 36 ค่า per-side ใน auto_config.json
- `raw_buy / raw_sell / weighted_buy / weighted_sell / probability_buy / probability_sell`
- + `raw_max_buy / raw_max_sell / ...` (ขอบบน anti-reversal)
- strategy_engine ใช้ per-side ก่อน fallback strategy-level

## ยังต้องเฝ้าดู (research ต่อเนื่อง)
- เมื่อตลาดเปิดคืนนี้ → สะสมผลจริง → ดูว่า threshold ที่ปรับแล้ว improve win-rate ไหม
- ปรับแต่ง p60/p90 เมื่อมีข้อมูลมากขึ้น (อาจเป็น p65/p92)
- เก็บ distribution per-side ยาวนานขึ้นเพื่อความมั่นใจ (ขอบบน anti-reversal ต้องใช้ trade จริงในโซนสูง)