# สัญญาการสื่อสาร: บอท (agent) → สคริปต์ Python (consumer)

> ไฟล์นี้สร้างอัตโนมัติจากโค้ดจริงของ `llm_recommendation_consumer.py` (ห้ามแก้ด้วยมือ — รัน `tools/rec_contract.py` เพื่ออัปเดต)

## 1) เขียนที่ไหน
- **ไฟล์เดียวเท่านั้น:** `research/recommendations/latest_recommendation.json`
- ระบบจะคัดลอกของเดิมที่ยังไม่ถูกประมวลผลไปเก็บที่ `superseded/` ให้อัตโนมัติ (ไม่หาย)
- เขียนแบบ atomic เสมอ (ใช้ `runtime_support.write_recommendation` หรือเครื่องมือ `tools/submit_recommendation.py`)

## 2) ฟิลด์บังคับ (ถ้าไม่ครบ consumer จะปฏิเสธ)
| ฟิลด์ | ค่าที่ต้องเป็น | หมายเหตุ |
|---|---|---|
| `schema` | `"hermes-trading-recommendation-v1"` | ตรงเป๊ะ |
| `auto_apply` | **`true`** | ⚠️ ถ้าเป็น false consumer จะปฏิเสธทันที |
| `changes` | **ลิสต์ที่ไม่ว่าง** | ถ้าไม่มีอะไรจะปรับ = **อย่าส่ง** (ไม่ใช่ส่งลิสต์ว่าง) |
| `mode` | `"internal_llm_join"` | โหมดปัจจุบัน |
| `mode_epoch` | `"aed68edb0f5e4895ba30b0686daf2039"` | ⚠️ epoch ปัจจุบัน — ถ้าไม่ตรง consumer จะปฏิเสธ (กันคำแนะนำเก่าปน) |
| `uses_llm` | บอท = `true`; Python ภายใน = `false` | บอทใช้ submit_recommendation ได้เฉพาะโหมด 2; งาน Python ยังทำงานทั้งสองโหมด |
| `summary` | ข้อความสั้น | สรุปคำแนะนำ 1-2 ประโยค |
| `generated_at` | เวลา ISO | ใช้ตรวจย้อน |

## 3) action ที่อนุญาต + ฟิลด์ของแต่ละ action
| action | ฟิลด์ที่ต้องมี | ขอบเขตค่าที่อนุญาต |
|---|---|---|
| `set_gate` | `strategy` · `side` · `raw_low` · `raw_high` | strategy หนึ่งใน: trend · range · mean_reversion · counter_trend · breakout · breakout_reversal · side: buy/sell · `0.05 ≤ raw_low ≤ raw_high ≤ 1.0` |
| `set_probability_gate` | `strategy` · `side` · `probability_low` · `probability_high` | `0.35 ≤ low ≤ high ≤ 0.95` |
| `set_tpsl` | `strategy` (หรือ `global`) + อย่างน้อย 1 ฟิลด์ด้านล่าง | `atr_stop_multiplier` 0.8–2.0 · `min_reward_risk` 1.2–3.0 · `stop_atr` (ต้องระบุ strategy) 0.6–2.5 · `reward_risk` (ต้องระบุ strategy) 1.2–3.0 |
| `set_weights` | `strategy_weights` (dict: strategy → 0.5–1.5) | ปรับน้ำหนักกลยุทธ์ (ไม่ปิดกลยุทธ์) |
| `toggle_strategy` | `strategy` · `enabled` | ⚠️ `enabled=false` ถูกห้าม (ห้ามปิดกั้นการเทรด) — ใช้ `set_weights` แทน |
| `set_risk` | `max_risk_pct` | ปรับความเสี่ยงรวม (ในกรอบของระบบ) |
| `set_directional_weights` | `directional_weights` (dict: strategy_side → 0.5–1.5) | validator รับช่วงนี้; engine อาจจำกัดน้ำหนักที่ใช้จริงเพิ่มอีก |

## 4) ห้ามทำ
- ห้ามแตะคีย์ที่ระบบสงวนไว้: live_enabled, magic, volume
- ห้ามแก้โครงสร้างโค้ด · ห้ามสตาร์ท/หยุดตัวเทรด · ห้ามลบ kill switch
- ห้ามเขียนไฟล์ชื่ออื่นนอกจาก `latest_recommendation.json`
- ห้ามใส่ค่าที่ไม่ใช่ตัวเลขจำกัด (NaN/Infinity) — จะถูกปฏิเสธ

## 5) ขั้นตอนที่บอทต้องทำ (ทุกครั้ง)
1) เขียนคำแนะนำเป็นไฟล์ชั่วคราว (เช่น `work/_rec.json`)
2) **ตรวจก่อนส่ง** (บังคับ):
   ```bash
   .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/submit_recommendation.py --check work/_rec.json
   ```
3) ถ้าผ่าน → ส่งเข้าระบบ:
   ```bash
   .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/submit_recommendation.py --submit work/_rec.json --source bot
   ```
4) ถ้าไม่ผ่าน → แก้ตามเหตุผลที่ระบบบอก แล้วตรวจซ้ำ (ระบบจะบอกว่าผิดฟิลด์ไหน)

## 6) ตัวอย่างคำแนะนำที่ผ่าน (ขั้นต่ำ)
```json
{
  "schema": "hermes-trading-recommendation-v1",
  "auto_apply": true,
  "mode": "internal_llm_join",
  "mode_epoch": "aed68edb0f5e4895ba30b0686daf2039",
  "uses_llm": true,
  "llm_provider": "hermes-agent",
  "generated_at": "<เวลา ISO>",
  "summary": "ปรับเพดานบนของ trend_buy ให้สอดคล้องกับงานวิจัยข้อมูลภายใน",
  "changes": [
    {"action": "set_gate", "strategy": "trend", "side": "buy",
     "raw_low": 0.45, "raw_high": 0.80, "reason": "<เหตุผลอ้างตัวเลขจริง>"}
  ]
}
```

## 7) ระบบจะทำอะไรต่อ (บอทไม่ต้องทำ)
consumer (ทุก 5 นาที): ตรวจ schema/ความปลอดภัย → **ประตูทดสอบ (Testing Gate)** → apply ลง `auto_config.json` → บันทึกผลลง audit (`recommendation_applied` / `recommendation_rejected` / `recommendation_blocked_by_test`)
> ถ้าระบบปิดอยู่ (kill switch) คำแนะนำจะถูกเก็บไว้ ไม่ถูกนำไปใช้
