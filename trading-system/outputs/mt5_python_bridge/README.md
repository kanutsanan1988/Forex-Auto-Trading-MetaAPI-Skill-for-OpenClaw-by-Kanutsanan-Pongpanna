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
# MT5 Python Trading System

ระบบเชื่อม MetaTrader 5 สำหรับ `XAUUSD.sml` โดยใช้แท่งที่ปิดแล้วเท่านั้นและไม่เก็บรหัสผ่านไว้ในโปรเจกต์

## สถานะกลยุทธ์

- ใช้ M1 เป็น trigger โดย M5/M15/H1 เป็นข้อมูล regime และแนวโน้มยืนยัน
- มีกลุ่มสัญญาณ 2 กลุ่ม: Python เดิม และ OpenRouter ซึ่งวิเคราะห์ข้อมูลชุดเดียวกัน
- มี OpenRouter Judge เปรียบเทียบทั้งสองกลุ่มและตัดสินขั้นสุดท้ายก่อนส่งกลับให้ Python
- คำนวณคะแนน Buy/Sell แยกทุกกลยุทธ์ แล้วเลือกคะแนนสูงสุดจาก Agent ที่เปิดใช้งาน
- **เกณฑ์คะแนนเป็นรายกลยุทธ์** (`agent_score_thresholds` — ช่วงจริง 0.25–0.70 ตามกลยุทธ์ ไม่ใช่ค่าเดียว 0.42); เงื่อนไขย่อยและ M1 trigger เป็นข้อมูลวิเคราะห์ ไม่ใช่กำแพงเข้าเทรด
- ใช้แท่งที่ปิดแล้วเท่านั้น และยังผ่าน risk gate ทุกครั้งก่อนส่งคำสั่ง

## การวิเคราะห์แบบอ่านอย่างเดียว

```powershell
..\..\.venv\Scripts\python.exe market_analyzer.py
```

ผลลัพธ์แสดง regime, คะแนน Trend/Range/Breakout, ข้อเสนอของ Agent ทั้งหมด, เหตุผล no-trade และความเสี่ยงของสัญญาณ โดยไม่มี `order_send()`

## การทดสอบ

```powershell
..\..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\..\.venv\Scripts\python.exe strategy_backtest.py
```

## Fully automated trader

ค่าปัจจุบันอยู่ใน `auto_config.json`:

- Volume `0.001`
- ความเสี่ยงสูงสุดต่อออเดอร์ `8%` (ระบบปฏิเสธออเดอร์ถ้า volume ขั้นต่ำเกินเพดาน)
- ขาดทุนรายวันสูงสุด `20%` รวม projected loss ของออเดอร์ใหม่
- **แพ้ติดต่อกันสูงสุด: ปิดประตูนี้** (`max_consecutive_losses = 0` = ไม่หยุดจากจำนวนไม้แพ้ติดกัน — ใช้ "ประตู net ต่อฝั่ง" แทน)
- Cooldown `0` นาที; เมื่อ position เดิมปิด ระบบสามารถพิจารณาออเดอร์ใหม่ในแท่ง M1 ถัดไป
- ตรวจรอบ process ทุก `60` วินาที และใช้แท่งปิด M1 เป็น trigger โดย M5/M15/H1 ยังคงเป็นตัวกำหนด regime/ยืนยันแนวโน้ม
- Spread สูงสุด `0.6`
- **ถือไม้ได้สูงสุด 2 ไม้ต่อ symbol** (hedge cap) และมี broker-side SL/TP
- **R:R ขั้นต่ำ `1.3`** (TP ยาวกว่า SL อย่างน้อย 1.3 เท่า) · `enforce_equal_tp_sl = false` (โหมด 1:1 เป็น legacy ที่ปิดอยู่)
- ตรวจ position ก่อนวิเคราะห์เทรดทุก `60` วินาที และ **ปิดกำไรที่ 80% ของระยะ TP เมื่อไม่มีสัญญาณทางเดียวกัน** (`profit_exit.no_signal_tp_fraction = 0.8`) รวมถึงปิดเมื่อสัญญาณใหม่สวนทาง
- Magic number `8252026`; การนับแพ้ติดต่อกันกรองเฉพาะ symbol และ magic นี้

> **ปรับเอกสารให้ตรงกับค่าจริงใน `auto_config.json` เมื่อ 19 ก.ย. 2026** — ค่าก่อนหน้านี้ในเอกสาร (แพ้ติดกัน 5 · หนึ่ง position · TP ≤ SL · ปิดที่กำไร $0.00 · คะแนน 0.42) ไม่ตรงกับ config ที่ใช้จริง

ทดสอบหนึ่งรอบโดยไม่ส่งคำสั่ง:

```powershell
..\..\.venv\Scripts\python.exe auto_trader.py --once
```

เริ่ม ดูสถานะ หยุด และล้าง Kill Switch:

```powershell
.\start_auto_trader.ps1
.\status_auto_trader.ps1
.\stop_auto_trader.ps1
.\clear_kill_switch.ps1
```

Supervisor เปิด Python ใหม่เมื่อหยุดผิดปกติ มี Singleton Lock ป้องกันการรันซ้ำ และบันทึก audit แบบ JSONL ที่ `..\..\work\auto_trader_audit.jsonl`

## Dual-agent Decision System

กลุ่มที่ 1 ใช้ Python Agents/Router เดิมทั้งหมด ส่วนกลุ่มที่ 2 เรียก OpenRouter โดยตรงผ่าน
HTTPS ด้วยโมเดล `deepseek/deepseek-v4-flash-0731` เท่านั้น จากนั้น OpenRouter Judge
จะพิจารณาสัญญาณและเหตุผลของทั้งสองกลุ่ม หาก Judge เห็นว่าหลักฐานไม่ชัดเจนจะเป็น
`no_trade` แต่ถ้า OpenRouter เชื่อมต่อไม่ได้, timeout, เครดิตหมด หรือ schema ไม่ผ่าน
ระบบจะ fallback ไปใช้ Python Agents/Router เดิมทันทีตาม `fallback_to_python: true`

- Retry ความผิดพลาดชั่วคราวแบบจำกัดตาม `max_attempts`
- Cache ผลสำเร็จของข้อมูลแท่งเดียวกันตาม `cache_seconds` เพื่อลดการเรียกและเครดิตซ้ำหลัง restart
- Judge ที่ confidence ต่ำกว่า `judge_min_confidence` จะถูกปรับเป็น `no_trade`
- คำตอบต้องผ่าน schema และทิศทางต้องตรงกับ signal group ที่ Judge เลือก
- Audit แยกสถานะ `ok`, `fallback_python` และ `error` เพื่อย้อนตรวจแหล่งที่มาของทุกการตัดสินใจ

Python เป็นผู้คำนวณ Entry, SL, TP, Volume และ Risk ก่อนส่งคำสั่งไป MT5 เสมอ
OpenRouter ไม่มีสิทธิ์เรียก MT5 หรือส่งคำสั่ง

การเรียก OpenRouter ใช้ `urllib` ใน Python โดยตรง ไม่ผ่าน OpenAI SDK และไม่ใช้เครดิต OpenAI
ตั้งค่า key ได้ผ่าน environment `OPENROUTER_API_KEY` หรือไฟล์ DPAPI ที่ `api_key_file`
ใน `auto_config.json` (ไฟล์ key ไม่ถูกเขียนลง audit)

ทดสอบการเชื่อมต่อและ Signal Agent โดยไม่เรียก MT5:

```powershell
..\..\.venv\Scripts\python.exe test_openrouter_connection.py
```

รายละเอียดผลทดสอบและแนวทางตรวจสอบก่อนเปิดใช้งานจริงอยู่ใน
`OPENROUTER-CONNECTION-TEST.md`

## พฤติกรรมอัตโนมัติ

ใน Technical-only Mode ระบบตรวจ position/spread/cooldown/risk/daily-loss และ `order_check` ทุกครั้ง การผ่านตัวกรองไม่ได้รับประกันกำไร และค่าความเสี่ยง 8% ต่อออเดอร์ยังถือว่าสูงมาก
