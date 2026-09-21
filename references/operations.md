<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH · youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# Operations — เดินระบบอย่างปลอดภัย (เส้นทาง MetaAPI)

> แพ็กนี้เริ่มที่สภาวะ **หยุด** — `work/AUTO_TRADER_STOP` มีอยู่ และ `live_enabled` = `false`
> ยังไม่มีการเทรดใด ๆ จนคุณตั้งค่าบัญชีของคุณเอง

## 1) ลำดับเปิดใช้งานครั้งแรก (ทำตามลำดับ ห้ามข้าม)

```bash
# 0) ติดตั้ง dependency
pip install -r outputs/mt5_python_bridge/requirements.txt
pip install metaapi-cloud-sdk

# 1) ตรวจแพ็กก่อนใช้
python scripts/verify_package.py

# 2) ตั้ง credential ใน environment (ห้ามใส่ในไฟล์ในแพ็ก)
export METAAPI_TOKEN="..."
export METAAPI_ACCOUNT_ID="..."

# 3) พิสูจน์ว่าสะพานต่อบัญชีคุณได้จริง (อ่านอย่างเดียว)
python scripts/metaapi_connect_check.py     # ต้องได้ connected_read_only

# 4) พิสูจน์ว่าระบบเทรดเดิมอ่านข้อมูลจริงผ่านสะพานได้
python scripts/metaapi_engine_smoke.py      # ต้องได้ engine_ok_read_only

# 5) ตรวจสุขภาพ/สถานะระบบ
python outputs/mt5_python_bridge/tools/health_check.py
python outputs/mt5_python_bridge/tools/system_status.py
```

`metaapi_engine_smoke.py` จะรายงาน symbol ที่ใช้ได้, digits, `volume_min/step`,
offset นาฬิกาโบรกเกอร์, ค่า ATR ของแต่ละกรอบเวลา และคำตัดสินของระบบ
**ถ้าขั้นที่ 3 หรือ 4 ไม่ผ่าน ให้หยุดตรงนั้นและแก้ก่อน** อย่าไปขั้นถัดไป

## 2) ตรวจค่าก่อนเทรดจริง (ทุกครั้งที่เริ่มใหม่)

| ต้องตรวจ | ทำไม |
|---|---|
| `symbol` ตรงกับโบรกของคุณ | ชื่อ symbol ต่างกันได้ (เช่น `XAUUSD` vs `XAUUSD.sml`) — ใช้ `METAAPI_SHIM_SYMBOL_OVERRIDE` ถ้าจำเป็น |
| `volume` ≥ `volume_min` และตรง `volume_step` | ส่งผิดแล้วถูกปฏิเสธ/เปิดผิดขนาด |
| `max_risk_pct`, `daily_loss_limit_pct` | เพดานความเสียหายของคุณเอง |
| `max_spread`, `deviation_points` | กัน slippage ในตลาดบาง |
| `magic` | กันไปยุ่งกับไม้ของระบบอื่น/คนอื่น |
| `live_enabled` | เปิดเมื่อพร้อมเท่านั้น |
| ไฟล์ `AUTO_TRADER_STOP` | ถ้ามี = ระบบหยุดทั้งหมด (ต้องตั้งใจลบ) |
| `METAAPI_SHIM_MARGIN_RATE` | เทียบ `order_calc_margin` กับโบรกคุณก่อนเชื่อตัวเลข |
| offset นาฬิกาโบรกเกอร์ | ถ้าผิด ระบบจะคิดว่า tick เก่า แล้วบล็อกเงียบ ๆ |

## 3) การหยุด (สำคัญสุด)

```bash
# หยุดทันที — สร้างไฟล์ kill switch
#   Windows: outputs\mt5_python_bridge\เทรด_หยุด.cmd
#   หรือสร้างไฟล์ trading-system/work/AUTO_TRADER_STOP เอง

# กลับมาเทรด (เมื่อตั้งใจแล้วเท่านั้น)
#   Windows: outputs\mt5_python_bridge\clear_kill_switch.ps1
```

**Kill switch สำคัญกว่า ทุกอย่าง** — บอท AI ห้ามลบ และสะพานก็ไม่ลบ
ถ้ามี STOP อยู่ การเปลี่ยนโหมด/คำแนะนำใด ๆ ไม่ทำให้ระบบกลับมาเทรด

## 4) เปิดเทรดจริง (เมื่อพร้อมจริง ๆ)

1. รัน `metaapi_connect_check.py` และ `metaapi_engine_smoke.py` ให้ผ่านก่อน
2. ตรวจตารางข้อ 2 ให้ครบ
3. **ปิด** read-only เมื่อต้องการให้ส่งออเดอร์ได้: `METAAPI_SHIM_READ_ONLY=0`
4. ตั้ง `live_enabled` = `true` **ด้วยความตั้งใจของคุณเอง**
5. ลบ `work/AUTO_TRADER_STOP`
6. เฝ้าดูรอบแรกด้วยตา

> แพ็กนี้ไม่แถม token และไม่เปิด live ให้ — และไม่ควรมีใครเปิดแทนคุณ

## 5) รอบอัตโนมัติ (OpenClaw / Hermes / Manus)

```bash
python agents/run_bot.py --role mode2     # รอบวิจัยโหมด 2
python agents/run_bot.py --role admin     # แอดมินบอท (ทุก 30 นาทีตามค่าโรงงาน)
python outputs/mt5_python_bridge/tools/health_check.py
```

ทุกการรันถูกบันทึกที่ `work/agent_runs.jsonl` — ตรวจย้อนได้เสมอว่าสมองตัวไหนทำอะไร เมื่อไร

## 6) เมื่อมีปัญหา

| อาการ | สาเหตุที่พบบ่อย |
|---|---|
| `metaapi_connect_check.py` → `blocked_not_deployed` | บัญชีไม่ใช่ `DEPLOYED` — ไป deploy ที่แดชบอร์ด MetaAPI เอง (สคริปต์ไม่ทำให้) |
| `failed` + token | token หมดอายุ/ผิด หรือ `METAAPI_ACCOUNT_ID` ไม่ใช่ UUID |
| `partial` | ต่อได้แต่บางการตรวจไม่ครบ — อ่านฟิลด์ที่ขาดก่อนเชื่อ |
| หา symbol ไม่เจอ | ชื่อ symbol ต่างจากโบรก — ตั้ง `METAAPI_SHIM_SYMBOL_OVERRIDE` |
| ระบบไม่ยอมเทรดเลยทั้งที่ดูดี | ตรวจ offset นาฬิกาโบรกเกอร์ (ถ้าผิดจะโดนตัดสินว่า tick เก่า) |
| `order_send` ถูกปฏิเสธ retcode 10017 | ยังอยู่ในโหมดอ่านอย่างเดียว — ตั้งใจหรือไม่? |

## 7) ก่อนแก้ระบบจริง

- ทดลองใน dry-run / shadow เสมอ
- ตรวจค่าโรงงานก่อนเปลี่ยน: `work/factory/config/auto_config.factory.json`
- คืนค่าโรงงานได้ทุกเมื่อ: `work/factory/restore_factory.py`
- ทุกการเปลี่ยนแปลงต้องตรวจย้อนได้
