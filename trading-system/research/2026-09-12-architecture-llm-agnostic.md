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
# 🏗️ สถาปัตยกรรมระบบ: LLM-Agnostic Auto-Improve Trading System

วันที่: 2026-09-12 — ผู้ใช้ Kanutsanan (เจ้าของแนวคิด) + Hermes (ผู้ออกแบบ/implement)

## ภาพรวม 3 ชั้น (100% แยกส่วน)

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: PYTHON 100% — ระบบเทรด                          │
│ auto_trader.py + strategy_engine.py + market_clock.py +     │
│ auto_threshold.py + llm_recommendation_consumer.py          │
│ เทรดเอง ทุก 60 วิ, ปรับ threshold เอง, restart เอง         │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: PYTHON 100% — ระบบบันทึกข้อมูลวิจัย                 │
│ auto_trader_audit.jsonl (ทุกเหตุการณ์) + pl_attribution.py  │
│ + threshold_analysis.py + mech_profit_analysis.py           │
│ + at_vs_trade_research.py (เก็บสถิติวิเคราะห์อัตโนมัติ)      │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: LLM 100% — ระบบวิจัย/แนะนำ                          │
│ LLM (ตัวไหนก็ได้!) อ่านข้อมูลจาก Layer 1/2 → วิจัย →          │
│ เขียน research/ + เขียน REC (JSON มาตรฐาน) →                │
│ consumer (python) อ่าน REC → apply → restart อัตโนมัติ       │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 วงจร Auto-Improve (ทำงานเองทั้งหมด — ทดสอบก่อน apply เสมอ)
```
LLM วิจัย (ทุก 10 นาที)
   → เขียน research/<งาน>.md 📄
   → เขียน research/recommendations/latest_recommendation.json (schema มาตรฐาน)
TESTING GATE (ทุก 5 นาที, python — llm_recommendation_tester.py)
   → schema/safety validate (10 กฎ)
   → functional: unit tests 26 ตัว (ต้องผ่าน)
   → performance: backtest config ใหม่ vs ปัจจุบัน (total_r/PF/win-rate/drawdown)
       - ตลาดเปิด → backtest จริงบน M5 ล่าสุด
       - ตลาดปิด → fallback ประวัติ audit (win-rate ≥ 50%)
   → verdict: passed / failed / skipped
   → ผ่านเท่านั้น → consumer apply ลง auto_config.json + restart supervisor
   → ไม่ผ่าน → บล็อก ไม่แตะระบบ (LLM ต้องปรับคำแนะนำใหม่)
ระบบเทรดใหม่ (config ที่ปรับปรุง+ทดสอบแล้ว) ทำงานต่อทันที 🏁
```

## 🔑 LLM-Agnostic — ใช้ LLM ใครก็ได้
- ระบบไม่ผูกกับ provider/model ใด: LLM ทำหน้าที่แค่ "อ่านข้อมูล → วิจัย → เขียน REC"
- **REC schema** = JSON มาตรฐาน (`hermes-trading-recommendation-v1`) — LLM ตัวใด
  (OpenRouter/Anthropic/Claude/local llama/Gemini...) ที่อ่านไฟล์และเขียนตาม
  template ได้ ก็ขับระบบนี้ได้เหมือนกัน
- ผู้ใช้ที่นำระบบไปใช้: ตั้งค่า model/API key ของตัวเองใน config ของ Hermes
  เท่านั้น ไม่ต้องแก้โค้d

## 🗣️ กติกาเมื่อคนอื่นนำไปใช้ (ถามก่อน)
1. **ถามผู้ใช้ก่อนเปิดครั้งแรก:** "ให้เปิดงานวิจัยด้วย LLM ของคุณพร้อมเทรดด้วยหรือไม่?"
   - ตอบ "ไม่" → ระบบเทรดอย่างเดียว (Layer 1+2) ไม่มี LLM
   - ตอบ "ใช่" → เปิด Loop เต็ม (Layer 3)
2. **ถามก่อนเปิด live:** ยืนยันบัญชี/ความเสี่ยง (เช่นเดิม)

## ⚖️ Safety (LLM ยังไงก็ทำอะไรพลาดไม่ได้)
- PROTECTED: `live_enabled / magic / volume` — LLM แก้ไม่ได้
- action อนุญาตแค่: set_gate, set_weights, toggle_strategy, set_risk
- band ต้อง `0.05 ≤ low ≤ high ≤ 1.0` — invariant low≤high เสมอ
- max_risk_pct จำกัด [0.5, 15]
- ทุกคำแนะนำ: audit `recommendation_applied/rejected` + ย้ายไฟล์ไป applied/
  (ประวัติย้อนดูได้)

## 📦 ไฟล์สำคัญ
- `llm_recommendation_consumer.py` — apply + restart
- `research/recommendations/TEMPLATE.md` — schema สำหรับ LLM ตัวใดก็ได้
- `research/recommendations/applied/` — ประวัติคำแนะนำที่เคยใช้
- `start/stop_FULL_system.cmd` — เปิด/ปิดทั้งระบบ + ทุกงานวิจัยพร้อมกัน

## ✅ สถานะทดสอบ (2026-09-12)
- ทดสอบ REC จำลอง (test-local): apply trend_sell band → config เปลี่ยน → validator ✅ → restart ✅
- audit: started → market_closed (ล็อกตลาดปิด) → recommendation_restart ✅
- วงจรสมบูรณ์ พร้อมใช้งานจริงรอบเปิดตลาด