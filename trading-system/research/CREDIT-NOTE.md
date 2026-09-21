<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->

# CREDIT-NOTE — ข้อความนิยามรุ่นใหม่ และ "ชุดไฟล์ที่ซีลด้วยแฮช"

> เอกสารนี้มีไว้เพื่อ **รักษาความจริงของหลักฐานย้อนหลัง** ของระบบ
> อ่านคู่กับ `research/recommendations/CONTRACT.md` (สัญญาการสื่อสารที่สร้างจากโค้ดจริง)

## 1) ข้อความนิยามรุ่นใหม่ (พิมพ์อยู่ในทุกไฟล์ของชุดแจกจ่าย)

```
Python Qaunt Trading + AI(LLM) Live Research
อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
เทรดในไทยมีกฎหมายรองรับ 100%
Settrade e-Open Account · MTS Gold Futures + MT5
https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
```

รูปแบบที่ใช้กับแต่ละชนิดไฟล์

| ชนิดไฟล์ | รูปแบบ |
|---|---|
| `.py` | คอมเมนต์ `#` ต่อจากบรรทัด `# -*- coding: utf-8 -*-` (และหลัง shebang ถ้ามี) |
| `.md` | HTML comment `<!-- ... -->` ไว้บนสุดของไฟล์ (ยกเว้น `SKILL.md` — ดูข้อ 3) |
| `.json` (object) | คีย์แรกชื่อ `_credit` เก็บข้อความ 7 บรรทัดรวมเป็นบรรทัดเดียว |
| `.json` (array) | ใส่คีย์ไม่ได้ → ใช้เอกสารนี้กำกับแทน (ดูข้อ 4) |
| `.cmd` | คอมเมนต์ `REM` (ต่อจาก `@echo off` ถ้ามี) |
| `.ps1` | คอมเมนต์ `#` ต่อจาก UTF-8 BOM |

## 2) ทำไม `auto_config.json` และ `auto_config.factory.json` ไม่มีคีย์ `_credit`

ไฟล์ค่าตั้งทั้งสองต้องคง **29 คีย์** ตามที่ตัวตรวจของระบบและตัวคืนค่าโรงงานกำหนด
(`work/factory/restore_factory.py`, `tools/compare_factory.py`)
จึงเก็บนิยามรุ่นใหม่ไว้ในคีย์เดิม `_creator.definition` แทนการเพิ่มคีย์ใหม่
→ ตัวเลข 29 คีย์ไม่เปลี่ยน และ `compare_factory` ยังเทียบระบบกับโรงงานได้ตามเดิม

## 3) ทำไม `SKILL.md` จึงเริ่มด้วย `---` ไม่ใช่คอมเมนต์เครดิต

ตัวโหลดสกิลของ Codex / Cowork / Cursor อ่าน **frontmatter** ที่ต้องอยู่ต้นไฟล์
จึงวาง `---` เป็นบรรทัดแรก แล้ววางบล็อกเครดิตไว้ **ต่อท้าย frontmatter** ทันที
ข้อความนิยามรุ่นใหม่ยังอยู่ครบในไฟล์ — เพียงย้ายตำแหน่งให้ตัวโหลดอ่านออก

## 4) ชุดไฟล์ที่ซีลด้วยแฮช — แก้ไม่ได้ (โดยเจตนา)

`llm_recommendation_consumer.py` คำนวณแฮชของคำแนะนำและค่าตั้ง แล้วตรวจซ้ำกับค่าที่บันทึกไว้
ในทุกโฟลเดอร์ของ `research/recommendations/evaluations/`:

```python
digest(v) = sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False))
```

- `evaluations/*/recommendation.json` — ซีลด้วย `verdict.json → rec_hash`
- `evaluations/*/baseline.json` — ซีลด้วย `verdict.json → config_hash`
- `applied/*.json` (28 ไฟล์ที่ตรงกับ `rec_hash`) — สำเนาคำแนะนำที่ระบบ "ใช้งานจริงแล้ว"

**ถ้าเติมคีย์ `_credit` ลงในไฟล์เหล่านี้แม้แต่คีย์เดียว การตรวจย้อนหลัง 328 รายการจะพังทันที**
(consumer จะตอบ `recommendation_rejected: proposal changed during evaluation`)

ด้วยเหตุนี้ชุดแจกจ่ายนี้จึง **เว้นไฟล์ซีลไว้ตามเดิมทุกไบต์** และแสดงนิยามรุ่นใหม่/เครดิตผู้สร้าง
ผ่านเอกสารฉบับนี้ + `README.md` + `SKILL.md` + ไฟล์อื่นในโฟลเดอร์เดียวกันแทน

## 5) ไฟล์ JSON ที่เป็น "ลิสต์" (ใส่คีย์ไม่ได้)

| ไฟล์ | เหตุผล |
|---|---|
| `research/2026-09-08-threshold-study/inputs/mt5_deals.json` | ข้อมูลดิบจากโบรกเกอร์ (array ของดีล) — ต้องคงรูปเดิมเพื่อการวิเคราะห์ซ้ำ |
| `research/2026-09-08-threshold-study/inputs/mt5_orders.json` | ข้อมูลดิบจากโบรกเกอร์ (array ของออร์เดอร์) — ต้องคงรูปเดิม |
| `work/factory/cron/jobs.snapshot.json` | สแนปช็อตงานตั้งเวลา (array) — ตัวเทียบโรงงานอ่านเป็นรายการ |

## 6) เครดิตผู้สร้าง

ระบบนี้สร้างโดย **คณัสนันท์ พงษ์พันนา (Kanutsanan Pongpanna)**
Facebook <https://www.facebook.com/LoveMoneyTH> · YouTube <https://youtube.com/@lovemoneythofficial>

โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ

## 7) ไฟล์ที่ไม่นำเข้าแพ็ก (โดยเจตนา) และวิธีเอาไปเอง

ระบบนี้ **ไม่** แถมไฟล์ 2 ชนิดที่เป็น "สถานะสด/บันทึกจริงของบัญชี" เพราะเป็นข้อมูลส่วนตัวของเจ้าของระบบ
และเป็นไฟล์ที่ตัวตรวจแพ็กจัดเป็นไฟล์ต้องห้ามโดยเจตนา:

| ไฟล์ | เหตุผลที่กันออก |
|---|---|
| `work/auto_trader_audit.jsonl` | บันทึกการทำงานจริงของบัญชี (ปัจจุบัน ~91 MB) — มีข้อมูลบัญชีและพฤติกรรมเทรดจริง |
| `work/auto_trader_state.json` | สถานะสดของระบบ (equity, position, น้ำหนักกลยุทธ์) — ระบบเขียนทับเองทุกครั้งที่รัน |
| `research/2026-09-08-threshold-study/inputs/auto_trader_audit.jsonl` | สแนปช็อตงานวิจัยชุดเดียวกัน (8 ก.ย. 2026) — มี `account_hash` ของบัญชีเจ้าของระบบ |
| `research/2026-09-08-threshold-study/inputs/auto_trader_state.json` | สแนปช็อตงานวิจัยชุดเดียวกัน — มี `account_hash` ของบัญชีเจ้าของระบบ |

**ตัวระบบไม่พึ่งพาไฟล์เหล่านี้ในการทำงาน** — `auto_trader.py` สร้าง `work/auto_trader_state.json`
ขึ้นใหม่เองเมื่อเริ่มรันครั้งแรก และเขียนบันทึกใหม่ที่ `work/auto_trader_audit.jsonl`
(ดูเส้นทางได้ใน `runtime_support.py` / `auto_trader.py`)

ถ้าต้องการให้ประวัติย้อนหลังของ **คุณ** เริ่มนับจากของเดิม: คัดลอกไฟล์จากเครื่องเดิมมาวางที่
`trading-system/work/auto_trader_audit.jsonl` ก่อนเปิดระบบครั้งแรก — ระบบจะเขียนต่อจากเดิม

ส่วนสแนปช็อตงานวิจัย 8 ก.ย. 2026 (สำหรับทำวิจัยซ้ำ): คัดลอกมาไว้ที่
`trading-system/research/2026-09-08-threshold-study/inputs/` ด้วยชื่อไฟล์เดิม
สคริปต์ `collect_inputs.py` และรายงานผลในโฟลเดอร์นั้นอ้างถึงชื่อไฟล์เหล่านี้อยู่แล้ว
