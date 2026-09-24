<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# งานวิจัย: probability และ weight ควรเป็นคะแนนช่วง (band) ด้วยหรือไม่?

วันที่: 2026-09-12 — ตอบคำถาม user + ข้อมูลจริงจาก audit

## คำนิยาม "36 ก้อนข้อมูล"
36 = 12 strategy-side (6 strategies × buy/sell) × 3 metric (raw, probability, weighted)
แต่ละก้อน = ช่วงคะแนน [low, high] ที่บอกว่า "คะแนนเท่าไหร่ถึงจะเทรดได้"
(และช่วงนี้ auto_threshold ปรับเองอัตโนมัติตามประวัติ)

## ข้อมูลจริง (จาก audit 5,409 prob + 31,044 weight samples)
- **Probability** ที่เกิดจริง: min 0.250 | p25 0.429 | median 0.489 | p75 0.530 | max 0.600
- **Weight** (shadow cycles): min 0.830 | max 1.244 | median 0.997

## วิเคราะห์: prob ควรเป็น band ไหม?

### ความหมายของแต่ละ metric (สำคัญมาก)
| metric | แปลว่าอะไร | ยิ่งสูง = ? | เหมาะเป็น band? |
|---|---|---|---|
| **raw score** | ความแข็งแรงของสัญญาณจาก indicators | สูง = strong แต่ **สูงเกินไป = overbought/overextended → เสี่ยงกลับตัว** | ✅ **ใช่** — ต้อง band (ทั้งล่าง-บน) เพราะมี reversal risk |
| **probability** | ความน่าจะเป็นชนะโดยประมาณ (win-rate) | **สูง = ดีเสมอ** (ความน่าจะเป็นชนะ 60% ดีกว่า 50% เสมอ) | ⚠️ **ล่างอย่างเดียว** — ไม่มีเหตุผลที่ prob 0.70 แล้วไม่ควรเทรด (มันดีกว่า 0.55) |
| **weight** | น้ำหนักความเชื่อ (ตัวคูณ 0.85-1.25) | สูง = เอียงไปทางกลยุทธ์นั้น | ❌ **ไม่ใช่คะแนน** — เป็นตัวถ่วงน้ำหนัก ไม่ใช่ความแข็งแรงสัญญาณ |

### สรุปหลัก quant:
1. **raw → ต้องเป็น band** (เหตุผลเดิม: reversal risk ที่ขอบบน) ✅
2. **probability → ควรเป็น *lower bound อย่างเดียว* (≥ gate)** — เพราะความน่าจะเป็นชนะไม่มี "ดีเกินไป"
   - ข้อยกเว้นเล็กน้อย: ถ้า prob สูงเกินจริง (เช่น >0.85) อาจเป็น overfit จากข้อมูลน้อย — ตั้ง upper ที่ 0.85 เผื่อกันเท่านั้น (แต่ไม่ใช่เหตุผลตลาด)
   - ข้อมูลจริง median 0.49 — เกทล่าง 0.53-0.60 พอดีกับความเป็นจริง
3. **weight → ควรเป็น *ค่าเดียว + clamp* (0.85-1.25)** ไม่ใช่ band:
   - เพราะ weight คือน้ำหนัก (multiplier) — ไม่มี "low/high" ในตัวเอง
   - ที่ถูกคือ: clamp ช่วงปลอดภัย + auto_adjust จาก performance (มีอยู่แล้วใน adaptive_shadow)
   - ตอนนี้ config มี weight เป็นค่าเดียวอยู่แล้ว ✅ (trend 0.85, range 1.20 ...)

## ข้อเสนอ (ปรับระบบ)
1. **คง**: raw = band [low, max] (36 ตัว) — auto_threshold ปรับอัตโนมัติ ✅ มีแล้ว
2. **prob = lower+upper เล็กน้อย**: ให้ upper 0.85 กัน overfit แต่ไม่ใช่ตัวกรองหลัก
   - เพิ่ม `probability_max` ทุก strategy = 0.85 (มีอยู่บางตัวแล้ว 0.75-0.88)
3. **weight = ค่าเดียว ± clamp** (0.85-1.25) — ระบบมีอยู่แล้ว — ไม่เป็น band
4. **เอกสารชัดเจน**: 36 ก้อนของ raw เป็น band, prob เป็น threshold 2 ด้าน(กัน overfit),
   weight เป็น multiplier — ทั้งหมด auto_threshold ปรับเอง

## คำตอบสั้น
- raw: **จำเป็นเป็น band** ✅
- probability: **ไม่จำเป็นเป็น band** — ใช้ lower bound (≥ gate) + upper กัน overfit เฉยๆ
- weight: **ไม่ใช่คะแนน** — เป็นตัวคูณ ใช้ค่าเดียว + clamp

ถ้าจะ "บังคับ 36 ก้อนให้เป็น band หมด" จะทำให้ prob 0.70 (ดีมาก) ถูก block เพราะเกิน upper — ผิดหลักสถิติ quant ครับ