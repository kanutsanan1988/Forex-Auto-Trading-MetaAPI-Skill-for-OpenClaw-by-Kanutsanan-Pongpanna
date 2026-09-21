<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH · youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# Architecture — สถาปัตยกรรมระบบ (เส้นทาง MetaAPI)

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
ในแพ็กนี้ "สมอง" คือ OpenClaw · Hermes · Manus AI หรือ agentic AI ตัวอื่นที่คุณใช้อยู่

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

- **ด่าน 1 — ก่อนเปิด:** ประตู net รายฝั่ง/ทิศทาง (คีย์ที่ net ล่าสุดติดลบถูกชะลอ) → แถบคะแนน 36 ค่า
- **ด่าน 2 — ไม้ที่เปิดอยู่:** จัดการก่อนเสมอ (TP/SL/ตัดขาดทุน/ปิดตามสัญญาณ)
- **ด่าน 3 — เทียบสองฝั่ง/ปิด/ยืนยัน:** เทียบฝั่งที่ผ่านด่าน 1+2 · ต้องยืนยันการปิดได้จริงก่อนเปิดไม้ใหม่

## 4) กลยุทธ์ 6 ตัว × 2 ฝั่ง = 12 คะแนน

`trend` · `range` · `mean_reversion` · `breakout` · `breakout_reversal` · `counter_trend`
แต่ละตัวให้คะแนนฝั่ง `buy` และ `sell` → รวมเป็น weighted score
**คะแนนดิบ ≠ probability ≠ weighted score** — อย่าสับสนสามสิ่งนี้

## 5) "สะพาน" MetaAPI — ชั้นที่ทำให้ไม่ต้องมีเทอร์มินัล MT5

```
        โค้ดเทรดเดิม (ไม่แก้แม้แต่บรรทัดเดียว)
                     │  import MetaTrader5 as mt5
                     ▼
        metaapi/metaapi_mt5_shim.py  ← เลียนแบบสัญญา API ของ MetaTrader5
                     │  MetaAPI RPC (คลาวด์)
                     ▼
              โบรกเกอร์ของคุณ (MT5)
```

ติดตั้งเป็น `MetaTrader5` แทนของจริงได้ 2 วิธี:

```python
import metaapi_mt5_shim as mt5            # วิธีตรง

# หรือให้โค้ดเดิม import MetaTrader5 ได้เลย:
import metaapi_mt5_shim
metaapi_mt5_shim.install_as_mt5()          # ตั้ง METAAPI_SHIM_AUTOLOAD=1 ก็ได้
```

### ฟังก์ชันที่สะพานรองรับ (ตรงกับสัญญาของ MetaTrader5)

`initialize` · `shutdown` · `version` · `last_error` · `terminal_info` · `account_info` ·
`symbol_select` · `symbol_info` · `symbol_info_tick` · `copy_rates_from_pos` ·
`copy_rates_from` · `copy_rates_range` · `positions_get` · `history_deals_get` ·
`history_orders_get` · `order_calc_profit` · `order_calc_margin` · `order_check` · `order_send`

### ตัวแปรสภาพแวดล้อมของสะพาน

| ตัวแปร | ใช้ทำอะไร |
|---|---|
| `METAAPI_TOKEN` | โทเคน MetaAPI ของคุณ (จำเป็น) — เก็บใน environment เท่านั้น |
| `METAAPI_ACCOUNT_ID` | UUID ของบัญชี MetaAPI (ไม่ใช่เลข login ของโบรกเกอร์) |
| `METAAPI_SHIM_READ_ONLY=1` | **ปฏิเสธ `order_send` ทั้งหมด** — ใช้ตรวจ/วิจัยอย่างปลอดภัย |
| `METAAPI_SHIM_SYMBOL_OVERRIDE` | บังคับชื่อ symbol (เมื่อโบรกเกอร์ใช้ชื่อต่างกัน) |
| `METAAPI_SYMBOL_ALIASES` | แผนที่ชื่อ symbol เพิ่มเติม |
| `METAAPI_SHIM_MARGIN_RATE` | ปรับอัตรามาร์จินให้ตรงโบรกเกอร์ของคุณ (ดู portability.md) |
| `METAAPI_SHIM_SERVER_UTC_OFFSET` | ตั้ง offset นาฬิกาโบรกเกอร์ด้วยมือ (ปกติสะพานอ่านเอง) |
| `METAAPI_SHIM_TIMEOUT` | เวลารอคำตอบจากคลาวด์ |
| `METAAPI_SHIM_VERBOSE` | พ่น log ของสะพานทาง stderr |
| `METAAPI_SHIM_AUTOLOAD` | ติดตั้งเป็น `MetaTrader5` อัตโนมัติ |

> **ลำดับความสำคัญที่ถูกต้อง:** ตั้ง `METAAPI_SHIM_READ_ONLY=1` **ก่อน** import สะพาน
> (สคริปต์ใน `scripts/` ทำแบบนี้ให้แล้ว) เพราะสถานะ read-only ถูกอ่านซ้ำสด ๆ ทุกครั้งที่ตรวจ

## 6) ความปลอดภัย: บังคับด้วยสคริปต์ ไม่ใช่ด้วยความไว้ใจ

| กรอบ | บังคับที่ไหน |
|---|---|
| ห้ามแตะ `live_enabled` · `magic` · `volume` · `symbol` | `consumer` + `admin_command` ปฏิเสธ |
| ห้ามสตาร์ท/หยุดตัวเทรด · ห้ามลบ kill switch | ไม่มีคำสั่งให้ทำ (เจ้าของระบบเท่านั้น) |
| สะพานห้าม deploy/undeploy บัญชีเอง | ในตัวสะพานเอง — บัญชีต้อง `DEPLOYED` อยู่ก่อน |
| สะพานโหมดอ่านอย่างเดียวห้ามส่งออเดอร์ | ในตัวสะพานเอง (retcode 10017) |
| คำแนะนำต้องผ่านประตูทดสอบ | Testing Gate ใน consumer |
| ต้องคืนค่าโรงงานได้เสมอ | `work/factory/` + `restore_factory.py` |
| ทุกการกระทำต้องตรวจย้อนได้ | `work/auto_trader_audit.jsonl` · `work/admin_bot_log.jsonl` · `work/agent_runs.jsonl` |

## 7) สัญญาการสื่อสารกับสมอง

เครื่องมือจริงที่สมองใช้:

- **ข้อมูลขาเข้า** (สมองอ่าน): `tools/llm_research_packet.py`, `news_feed.py`, `tools/admin_bot_round.py`
- **งานขาออก** (สมองเขียน): `tools/submit_recommendation.py`, `tools/admin_command.py`
- **สัญญาที่ผูกพัน**: `research/recommendations/CONTRACT.md` (สร้างจากโค้ดจริงด้วย `tools/rec_contract.py`)
