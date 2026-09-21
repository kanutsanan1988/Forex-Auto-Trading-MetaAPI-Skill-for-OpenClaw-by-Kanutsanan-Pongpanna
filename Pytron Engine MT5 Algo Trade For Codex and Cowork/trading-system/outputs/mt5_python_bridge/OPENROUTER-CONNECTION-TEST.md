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
# OpenRouter Connection Test Reference

บันทึกนี้ใช้เป็นหลักฐานและแนวทางตรวจสอบการเชื่อมต่อ OpenRouter ก่อนเปิดระบบเทรดจริง
ไม่มี API key, เลขบัญชี MT5 หรือข้อมูลลับถูกบันทึกไว้ในเอกสารนี้

## ผลทดสอบที่ยืนยันแล้ว

- วันที่ทดสอบ: 29 สิงหาคม 2026 (Asia/Bangkok)
- โมเดล: `deepseek/deepseek-v4-flash-0731`
- API key จากไฟล์ DPAPI: อ่านได้
- DPAPI fallback เมื่อไม่มี environment key: ทดสอบผ่าน โดยไม่แสดง secret
- ทดสอบเรียก OpenRouter จริงโดยปิด environment key และใช้ DPAPI เท่านั้น: สำเร็จใน 1.81 วินาที
- การเชื่อมต่อ OpenRouter HTTPS API: สำเร็จ
- เวลาตอบกลับ connectivity test: 2.41 วินาที
- Signal Agent schema test: สำเร็จ
- เวลาตอบกลับ Signal Agent: 13.18 วินาที
- ข้อมูลที่ใช้ใน schema test: ข้อมูลจำลอง ไม่ใช่ตลาดจริง
- MT5 และ `order_send()`: ไม่ถูกเรียก

ผล Signal Agent ที่ได้รับในการทดสอบ:

```text
side: buy
strategy: trend
confidence: 0.65
reason_present: true
supporting_evidence_count: 4
risks_count: 3
```

หมายเหตุ: ping ครั้งแรกเชื่อมต่อสำเร็จแต่โมเดลคืนชื่อฟิลด์ JSON ไม่ตรงคำสั่ง
จึงใช้ Signal Agent schema test เป็นเกณฑ์ยืนยันการใช้งานจริง ซึ่งผ่านการตรวจรูปแบบครบถ้วน

## วิธีทดสอบซ้ำก่อนใช้งานจริง

รันจากโฟลเดอร์ `outputs\mt5_python_bridge`:

```powershell
..\..\.venv\Scripts\python.exe test_openrouter_connection.py
```

หากต้องการตรวจเฉพาะ API/key/model โดยลดจำนวน token และไม่ทดสอบ Signal Agent:

```powershell
..\..\.venv\Scripts\python.exe test_openrouter_connection.py --connection-only
```

สคริปต์ต้องรายงานค่าต่อไปนี้ก่อนถือว่าพร้อม:

```text
ok: true
model: deepseek/deepseek-v4-flash-0731
api_key_available: true
connection.ok: true
signal_schema.ok: true
mt5_used: false
order_sent: false
```

## เกณฑ์ก่อนเปิด Auto Trader

1. รัน connection test ให้ผ่าน
2. ตรวจว่า model ตรงกับ `deepseek/deepseek-v4-flash-0731`
3. รัน `auto_trader.py --once` แบบไม่ใส่ `--live`
4. ตรวจ `work\auto_trader_audit.jsonl` ว่ามี `dual_agent_result` และไม่มี error
5. ตรวจ Python signal, OpenRouter signal และ Judge decision
6. เปิด live เฉพาะเมื่อ risk gate, spread, SL/TP และ permission ของ MT5 ถูกต้อง

## การวิเคราะห์ข้อผิดพลาด

- `api_key_available: false`: ตรวจ environment `OPENROUTER_API_KEY` หรือไฟล์ DPAPI ตาม `auto_config.json`
- HTTP 401/403: key ไม่ถูกต้อง หมดอายุ หรือไม่มีสิทธิ์
- HTTP 402: เครดิต OpenRouter ไม่เพียงพอ
- HTTP 429: rate limit; รอแล้วทดสอบใหม่
- timeout/5xx: OpenRouter หรือ provider ไม่พร้อม ระบบจะ retry แบบจำกัด แล้ว fallback ไป Python เดิม
- `WinError 10013`: firewall/sandbox บล็อก outbound HTTPS ไม่ใช่ข้อผิดพลาดของกลยุทธ์
- invalid JSON/schema: โมเดลตอบไม่ตรงรูปแบบ ระบบจะ fallback ไป Python เดิม

เมื่อเกิด fallback ให้ตรวจ audit event `dual_agent_result` ซึ่งต้องมี
`status: fallback_python`, `fallback: true` และสาเหตุใน `error` ผลเทรดในรอบนั้น
จะมาจาก Python Agents/Router เดิมและยังต้องผ่าน risk gate กับ `order_check()` ทุกครั้ง

การเรียก API ในระบบนี้มาจาก Python ไป OpenRouter โดยตรง ไม่ผ่าน OpenAI SDK
และไม่ใช้เครดิต OpenAI API ส่วนการทดสอบและการเทรดที่เรียก OpenRouter จะใช้เครดิตของ OpenRouter
ตามจำนวน token ที่ส่งและรับจริง
