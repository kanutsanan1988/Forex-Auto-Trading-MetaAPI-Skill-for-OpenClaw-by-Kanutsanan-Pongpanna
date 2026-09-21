<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH · youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# Architecture — สถาปัตยกรรมระบบ

## 1) หลักคิด: "ตัวถัง" กับ "สมอง"

```
┌──────────────── ตัวถัง ( Deterministic ) ─────────────────┐
│ market_clock · strategy_engine · side_net · auto_threshold │
│ trade_guard · live_executor · auto_trader · consumer       │
│ ประตู 3 ด่าน · กรอบปลอดภัย · audit · โรงงาน · kill switch  │
└──────────────────────────┬────────────────────────────────┘
                           │  สัญญากลาง = ไฟล์ + คำสั่ง shell
                           │  (ตัวไหนทำ 2 อย่างนี้ได้ = เป็นสมองได้)
             ┌─────────────┴─────────────┐
             ▼                           ▼
   รอบวิจัยโหมด 2 (brief_mode2)   แอดมินบอท (brief_admin)
   อ่าน packet → คิด → ส่งคำแนะนำ   อ่านสถิติ → คิด → ปรับค่าตามกรอบ
```

**ตัวถังไม่รู้จักว่าสมองคือ AI ตัวไหน** → เปลี่ยนสมองได้โดยไม่แก้โค้ดเทรดแม้แต่บรรทัดเดียว

## 2) ลำดับการตัดสินใจ (Decision pipeline)

| ขั้น | ไฟล์ | ทำอะไร |
|---|---|---|
| 1 | `market_clock.py` | ตลาดเปิด/ปิด? ปลอดภัยพอที่จะทำงานไหม |
| 2 | `strategy_engine.py` | คำนวณ 12 คะแนน (6 กลยุทธ์ × buy/sell) + weighted score + probability |
| 3 | `auto_threshold.py` | แปลงคะแนนเป็น "แถบ/เกณฑ์" ที่ต้องผ่าน |
| 4 | `market_analyzer.py` | ATR, เงินต่อจุด, สภาพตลาด |
| 5 | `side_net.py` | ด่านเน็ตรายฝั่ง — ฝั่งที่กำลังแพ้ถูกห้ามเข้าซ้ำ |
| 6 | `trade_guard.py` | กรอบสุดท้ายก่อนส่ง: สเปรด, คูลดาวน์, กันแก้แค้น, ความเสี่ยง |
| 7 | `live_executor.py` | ส่งคำสั่งจริง (หรือ dry-run) |
| 8 | `auto_trader.py` | จัดการไม้ที่เปิดอยู่ (สำคัญกว่าไม้ใหม่เสมอ) + บันทึก audit |

## 3) ประตู 3 ด่าน

- **ด่าน 1 — ก่อนเปิด:** คะแนน/แถบ/ด่านเน็ต/กรอบความเสี่ยง
- **ด่าน 2 — ไม้ที่เปิดอยู่:** จัดการก่อนเสมอ (TP/SL/ตัดขาดทุน/ปิดตามสัญญาณ)
- **ด่าน 3 — ปิด/ยืนยัน:** ต้องยืนยันการปิดได้จริงก่อนเปิดไม้ใหม่

## 4) กลยุทธ์ 6 ตัว × 2 ฝั่ง = 12 คะแนน

`trend` · `range` · `mean_reversion` · `breakout` · `breakout_reversal` · `counter_trend`
แต่ละตัวให้คะแนนฝั่ง `buy` และ `sell` → รวมเป็น weighted score
**คะแนนดิบ ≠ probability ≠ weighted score** — อย่าสับสนสามสิ่งนี้

## 5) การไหลของข้อมูลกับสมอง AI

```
tools/llm_research_packet.py ──► (สมองอ่าน) ──► tools/submit_recommendation.py
                                                      │
                                          research/recommendations/*.json
                                                      │
                                    llm_recommendation_tester.py (ประตูทดสอบ)
                                                      │
                                    llm_recommendation_consumer.py (apply ในกรอบ)
```

สัญญาการสื่อสารสร้างจากโค้ดจริง: `python outputs/mt5_python_bridge/tools/rec_contract.py`

## 6) ความคงทนและตรวจย้อนได้

| กลไก | ที่ตั้ง |
|---|---|
| audit การเทรด | `work/auto_trader_audit.jsonl` (โรเทตด้วย `tools/rotate_audit.py`) |
| audit แอดมินบอท | `work/admin_bot_log.jsonl` |
| audit การรันสมอง | `work/agent_runs.jsonl` |
| ค่าโรงงาน | `work/factory/` + `restore_factory.py` |
| หยุดฉุกเฉิน | `work/AUTO_TRADER_STOP` |
| ล็อกกันชนกัน | `runtime_support.file_lock` + `*.lock` |

## 7) ชั้นเชื่อม MetaAPI

`metaapi/metaapi_mt5_shim.py` เลียนแบบ API ของ `MetaTrader5` ทั้งชุด (ฟังก์ชันระดับโมดูล,
namedtuple ตามชื่อฟิลด์จริง, dtype ของแท่งเทียน) เพื่อให้ระบบเดิมรันผ่านคลาวด์โดยไม่แก้โค้ด
รายละเอียดความแม่นยำและข้อจำกัดอยู่ใน [portability.md](portability.md)
