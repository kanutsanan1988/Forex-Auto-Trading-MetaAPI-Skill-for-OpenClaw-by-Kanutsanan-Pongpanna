<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# ภาคผนวก: Live-Reload Auto-Threshold + ระบบเปิด/ปิดพร้อมวิจัย

วันที่: 2026-09-12 09:50 ต่อจาก `2026-09-12-auto-threshold-v2-reversal-safe.md`

## 1. ค่าที่ปรับระหว่างเทรด ใช้ได้ทันที (ไม่ต้อง restart) — ยืนยันด้วยการทดสอบ
- main loop เรียก `apply_auto_threshold_side(config)` **ทุก cycle (60 วิ)** ก่อน `process_bar`
- reassign config ในหน่วยความจำ → `decide_market` อ่าน `raw_{side}/raw_max_{side}` จาก dict ที่ถูก mutate ทันที (พิสูจน์ว่าไม่มี `open()`/`json.load` ใน decide_market)
- ⇒ ค่า 36 ตัวที่ปรับตอนนี้ มีผลกับรอบเทรดถัดไปทันที ลดศูนย์ restart ระหว่างวัน

## 2. ปิด/restart = ค่าล่าสุดเป็นค่าเริ่มต้นครั้งหน้า
- ทุกครั้งที่ auto_threshold ปรับค่า → **persist ลง auto_config.json ทันที** (พร้อม audit `auto_threshold_persisted`)
- เปิดระบบครั้งหน้า `load_config()` อ่านค่าล่าสุด = ค่าเริ่มต้นต่อเนื่อง (ไม่กลับไปค่าเดิม)

## 3. เปิด/ปิดระบบเทรด = เปิด/ปิดระบบบันทึกวิจัยพร้อมกัน
- `start_FULL_system.cmd` → start_auto_trader + resume cron: auto-threshold-research, pl-attribution, trading-research-loop
- `stop_FULL_system.cmd` → stop_auto_trader + pause cron ทั้ง 3
- (cron 3 ตัวถูกสร้างใหม่แล้ว: jobs 1c97fe0ad38a / 5093d3ab475a / 9de5c45717a8)

## 4. สถานะปัจจุบัน
- auto_threshold.enabled = true (mode hybrid, window 1000, min_samples 30, deadband 0.02, churn 3600s)
- per-side key 1 ตัวที่ถูกปรับแล้ว: trend_buy [0.244, 0.361] — ตัวอื่นอยู่ใน band (ไม่ขยับ = ฉลาด)
- ตลาดปิด (เสาร์) → ระบบยังไม่เปิด live; เปิดพร้อมเปิดตลาดอาทิตย์ 22:00 UTC