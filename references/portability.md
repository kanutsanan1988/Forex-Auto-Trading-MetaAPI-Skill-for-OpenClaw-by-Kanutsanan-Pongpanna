<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH · youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# Portability — ย้ายเครื่อง · MetaAPI · ข้อจำกัดจริง

## 1) ทำไมต้องมีสะพาน MetaAPI

ระบบเทรดทั้งชุดเขียนบนสัญญา API ของแพ็กเกจ `MetaTrader5` ซึ่งต้องมี **เทอร์มินัล MT5
บน Windows** อยู่จริงในเครื่อง ถ้าเครื่องปลายทางไม่มี (ลินุกซ์ เซิร์ฟเวอร์ คอนเทนเนอร์
หรือเครื่องของคนอื่น) ระบบจะรันไม่ได้เลย

`metaapi/metaapi_mt5_shim.py` แก้ปัญหานี้โดย **เลียนแบบสัญญา API ของ MetaTrader5**
แล้วส่งงานไปที่คลาวด์ MetaAPI แทน → โค้ดเทรดเดิมรันได้ **โดยไม่แก้แม้แต่บรรทัดเดียว**

## 2) หลักฐานการเชื่อมต่อจริง (21 ก.ย. 2026)

ไฟล์ใน `metaapi/evidence/`:

| ไฟล์ | พิสูจน์อะไร |
|---|---|
| `live-readonly-verify-20260921.json` | เชื่อมต่อจริงได้ · อ่านบัญชี/symbol/tick/แท่งครบ · `order_send` ถูกบล็อก (retcode 10017) · `order_send_called: false` |
| `preflight-readonly-20260921.json` | สถานะบัญชีก่อนเริ่ม (`DEPLOYED`) · ไม่มีการ deploy/undeploy · login ถูกมาสก์ |
| `forming-bar-probe-20260921.json` | MetaAPI คืน **แท่งที่ยังไม่ปิด** เป็นแท่งสุดท้ายเหมือน MT5 เป๊ะ (ทดสอบ 1m/5m/15m/1h) |

ตัวเลขที่ยืนยันได้จากหลักฐาน: equity 10.44 USD · leverage 100 · symbol `XAUUSD.sml`
(digits 3 · volume_min 0.001 · volume_step 0.001 · contract_size 100 · tick_size 0.001) ·
offset นาฬิกาโบรกเกอร์ 10,800 วินาที (UTC+3) · แท่ง M1/M5/H1 ครบ 300 แท่ง

**ยืนยันแล้วว่าไม่มีออเดอร์หลุด** — positions 0 · orders 0 · balance ไม่เปลี่ยน

## 3) ความต่างที่ต้องรู้ (บอกตามตรง)

| เรื่อง | ความจริง |
|---|---|
| เวลาของ MT5 | เป็นนาฬิกาเซิร์ฟเวอร์โบรก = UTC+3 สำหรับบัญชีที่ทดสอบ — สะพานอ่านจาก `get_server_time()` จริงและปัดเป็น 15 นาที **ห้าม hardcode** เพราะแต่ละโบรกต่างกันและเปลี่ยนตาม DST |
| datetime ขาเข้า | MT5 ตีความ aware = เวลาสัมบูรณ์, naive = เวลาท้องถิ่นเครื่อง → สะพานใช้กติกาเดียวกัน |
| แท่งที่ยังไม่ปิด | MetaAPI คืนเป็นแท่งสุดท้ายเหมือน MT5 เป๊ะ (ทดสอบทุก TF) |
| dtype ของแท่ง | ตรงกับ MetaTrader5 ทุกตัว: `time i8, open/high/low/close f8, tick_volume u8, spread i4, real_volume u8` |
| ฟิลด์ของ position/deal/order | ดึงชื่อฟิลด์จริงจากไบนารี `metatrader5 5.0.6090` แล้วทำ namedtuple ตรงกัน |
| enum | MetaAPI ส่งชื่อ enum เป็น **ข้อความ** → สะพานแปลงเป็นตัวเลขแบบ MT5 |
| tick value | MetaAPI ไม่ให้มาในสเปก symbol → สะพานถามราคาสด (`profitTickValue`) |
| `calculate_margin` | SDK คืน dict `{'margin': ...}` ไม่ใช่ตัวเลข → สะพานรองรับทั้งสองแบบ |
| log ของ SDK | SDK พ่น log ทาง stdout → สะพานย้ายไป stderr เพื่อไม่ให้ JSON ของระบบพัง |
| ขีดจำกัดแท่ง | MetaAPI ให้ ~1000 แท่ง/ครั้ง แต่ระบบขอ 3000 → สะพานโหลดแบบแบ่งหน้าให้อัตโนมัติ |

## 4) ส่วนต่างมาร์จิน — เรื่องที่ต้องเข้าใจให้ถูก

บัญชีที่ทดสอบ: MT5 คิด ~0.48 USD ต่อ 0.001 lot แต่ MetaAPI คิด ~4.35 USD
(คิดจาก notional/leverage) ต่างกันจริง ~9 เท่า

**ค่าของ MetaAPI สูงกว่า = อนุรักษ์นิยมกว่า = ปลอดภัยกว่า** (ระบบจะคิดว่าใช้มาร์จินมากกว่าจริง
จึงไม่เปิดไม้เกินตัว) ถ้าต้องการให้ตรงกับโบรกของคุณ ให้ตั้ง `METAAPI_SHIM_MARGIN_RATE`

> อย่าเพิ่งตกใจกับตัวเลขนี้ — บัญชีทดสอบมีทุนเพียง ~10 USD และเปิดไม้จิ๋ว 0.001 lot
> ให้ทดสอบกับบัญชีจริงของคุณเองแล้วเทียบ `order_calc_margin` กับ MT5 ก่อนตัดสินใจ

## 5) ข้อจำกัดจริงของสะพาน

- **hosted / ลินุกซ์ ไม่มีเทอร์มินัล MT5 ของ Windows** → ใช้เส้นทาง MetaAPI (คือจุดประสงค์ของแพ็กนี้)
- **MetaAPI ต้องมีบัญชีและโทเคนของคุณเอง** แพ็กนี้ไม่แถม
- `symbol_select` ไม่มีใน MetaAPI → no-op คืน True (MetaAPI ไม่มีแนวคิด Market Watch)
- `order_check` ไม่มีใน MetaAPI → สะพานจำลองการตรวจ (symbol/volume/step/SL-TP ด้านถูก/มาร์จิน)
- **ห้ามให้สะพาน deploy/undeploy บัญชีเอง** — ต้องเป็น `DEPLOYED` อยู่แล้ว
  ถ้าไม่ใช่ สะพานจะรายงานและคืน False (ไม่เปลี่ยนสถานะบัญชีและไม่กินค่าใช้จ่าย)
- สเปรดในสเปก symbol ของ MetaAPI เป็น 0 → ห้ามใช้ตัดสินใจ ให้ใช้ราคาสดหรือข้อมูลจริง
- การเชื่อมต่อครั้งแรกของ dedicated server อาจใช้เวลาได้ถึง ~3 นาที

## 6) ย้ายไปเครื่องอื่น — เช็กลิสต์

1. คัดลอก `trading-system/` **ออกจาก** โฟลเดอร์สกิล ไปยังที่ที่เขียนได้
2. ตั้ง `TRADING_PROJECT_ROOT` ถ้าไม่ได้คงโครง `outputs/mt5_python_bridge/` ไว้
3. ติดตั้ง `pip install -r outputs/mt5_python_bridge/requirements.txt` และ `metaapi-cloud-sdk`
4. ตั้ง `METAAPI_TOKEN` / `METAAPI_ACCOUNT_ID` ใน environment ของเครื่องนั้น
5. รัน `scripts/metaapi_connect_check.py` → ต้องได้ `connected_read_only`
6. รัน `scripts/metaapi_engine_smoke.py` → ต้องได้ `engine_ok_read_only`
7. อ่าน `references/operations.md` ก่อนเปิดใช้งานจริง

## 7) ความเข้ากันได้ของ "สมอง"

| สมอง | คำสั่ง headless | เกณฑ์ |
|---|---|---|
| **OpenClaw** | `openclaw "<brief>"` | รัน shell + อ่าน/เขียนไฟล์ |
| **Hermes Agent** | `hermes -z "<brief>"` | เช่นเดียวกัน |
| **Manus AI** | `manus-cli task create --prompt "<brief>"` | เช่นเดียวกัน |
| Codex CLI | `codex exec "<brief>"` | เช่นเดียวกัน |
| Claude Code | `claude -p "<brief>"` | เช่นเดียวกัน |
| Cursor CLI | `cursor-agent -p "<brief>"` | เช่นเดียวกัน |
| Claude Cowork | เปิดโฟลเดอร์ + ใช้ไฟล์ brief | แบบ desktop |
| Gemini / Aider / Goose / Copilot / Cline / Kiro / OpenHands | ดู `agents/registry.json` | เช่นเดียวกัน |

**เกณฑ์เดียว:** สมองต้องรันคำสั่ง shell และอ่าน/เขียนไฟล์ได้ → agentic AI แทบทุกตัวผ่าน
เพิ่มสมองใหม่ = เพิ่มบล็อกเดียวใน `agents/registry.json`
