# 🧳 นำระบบไปใช้บนเครื่องอื่น (Portable Setup)

> Python Qaunt Trading + AI(LLM) Live Research · อัพเดทใหญ่ระดับผู้ทรงภูมิปัญญา · เทรดในไทยมีกฎหมายรองรับ 100% · Settrade e-Open Account · MTS Gold Futures + MT5
> ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
> เอกสารนี้ตั้งขึ้นตามคำสั่งเจ้าของระบบ (23 ก.ย. 2026): *"ถ้าเครื่องที่นำไปใช้ต่อเชื่อมต่อกับ Jev ได้ด้วยวิธีไหนก็ตาม ก็ให้เชื่อมต่ออัตโนมัติ แต่ถ้าหาวิธีแล้วยังไงก็เชื่อมไม่ได้ ก็ให้ระบบทำงานได้โดยไม่ต้องมี Jev"*

---

## 1. หลักการ

ระบบนี้ออกแบบให้ **ย้ายเครื่องได้** ด้วยกติกา 2 ข้อ:

1. **เชื่อมต่อ Jev อัตโนมัติ** — เครื่องใหม่ไม่ต้องแก้โค้ด ระบบจะค้นหาคีย์เองทุกวิธีที่หาได้
2. **ทำงานได้โดยไม่ต้องมี Jev** — ถ้าหาไม่เจอ/ทดสอบไม่ผ่าน ระบบปิด Jev แล้วเดินต่อด้วย **กฎตัวเลขเดิม**
   (ประตู 36 ค่า · ด่าน 3 ชั้น · กระดานคะแนนกลยุทธ์) → **ไม่พัง ไม่หยุด ไม่ค้าง**

---

## 2. ขั้นตอนย้ายเครื่อง (5 นาที)

```bat
:: 1) คัดลอกโฟลเดอร์โปรเจกต์ทั้งชุดไปเครื่องใหม่  (ยกเว้นโฟลเดอร์ work\ — ดูข้อ 5)
:: 2) ตรวจความพร้อมของเครื่องนี้
python outputs\mt5_python_bridge\tools\portable_setup.py

:: 3) ถ้าต้องการให้ติดตั้งให้เลย (สร้าง .venv + ติดตั้งไลบรารี + เชื่อม Jev อัตโนมัติ)
python outputs\mt5_python_bridge\tools\portable_setup.py --apply

:: 4) ตรวจสุขภาพระบบ  → ควรผ่านครบ
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\full_audit.py
```

---

## 3. เส้นทางการเชื่อมต่อ Jev (เรียงตามลำดับที่ระบบค้นหา)

| ลำดับ | วิธี | ตัวอย่าง |
|---|---|---|
| 1 | ตัวแปรสภาพแวดล้อมของเครื่อง | `set JEV_API_KEY=...` (หรือ `JEV_KEY`) |
| 2 | ตัวแปรตามชื่อใน `jev_config.json` (`key_env_names`) | `OPENROUTER_API_KEY` ฯลฯ |
| 3 | ไฟล์คีย์บรรทัดเดียว | `work\jev_key.txt` · `keys\jev_key.txt` · `~\.jev_key` |
| 4 | ไฟล์ `.env` ทั่วไป | โปรเจกต์ · โฟลเดอร์แม่ · `~\.env` · โฟลเดอร์ของ Hermes |
| 5 | ตัวแปร `JEV_KEY_FILE` ชี้ไฟล์คีย์เอง | `set JEV_KEY_FILE=D:\keys\jev.txt` |

**ทดสอบ/ตั้งค่าเองด้วยคำสั่งเดียว:**

```bat
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev_connect.py --detect   :: ดูว่าพบจากทางไหน
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev_connect.py --setup    :: เชื่อมต่อ + บันทึกค่าจริง
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev_connect.py --setup --dry
```

- ผลลัพธ์ถูกบันทึกไว้ใน `jev_config.json` (`enabled` · `key_source` · `portable`) และบันทึกประวัติที่ `work\jev_connect_audit.jsonl`
- **ห้ามฝังคีย์ในโค้ด** — ระบบมีตัวตรวจความปลอดภัยใน `full_audit.py` ที่จะจับทันที (ผ่าน 38/38 เท่านั้น)
- เปลี่ยนปลายทาง API ได้ด้วย `JEV_BASE_URL` (ปกติใช้ค่าเดียวกับ `jev.py`)

---

## 4. ตรวจว่าตอนนี้ Jev ทำงานแบบไหนอยู่

```bat
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev.py --probe            :: ทดสอบยิงจริง 1 ครั้ง (~$0.000001)
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev.py --selftest         :: ทดสอบทุกพรีเซ็ต
.venv\Scripts\python.exe outputs\mt5_python_bridge\tools\jev_power.py --status     :: ระดับอำนาจของ Jev ในระบบเทรด
```

- **มี Jev** → ระบบใช้ความน่าจะเป็นที่สอบเทียบของ Jev เป็นข้อมูลประกอบ (และสิทธิ์เบรกตามระดับอำนาจ)
- **ไม่มี Jev** → ระบบรายงานชัดว่า *"ระบบทำงานต่อได้โดยไม่ต้องมี Jev"* แล้วใช้กฎตัวเลขเดิมทุกประการ

---

## 5. ⚠️ สิ่งที่ห้ามคัดลอกข้ามเครื่อง

| ห้ามคัดลอก | เหตุผล |
|---|---|
| `work\` ทั้งโฟลเดอร์ | มี state/lock/kill switch/audit/คำแนะนำค้างของเครื่องเดิม — จะชนกัน |
| `.venv\` | ไลบรารีผูกกับระบบปฏิบัติการ/เวอร์ชัน Python ของเครื่องเดิม — ให้สร้างใหม่ |
| `__pycache__\` · ไฟล์ `.bak_*` | ไม่จำเป็น และอาจสับสน |

**คัดลอกได้:** โค้ด (`outputs\` · `agents\` · `research\` · `tools\`) · ไฟล์ตั้งค่า (`.json`) · ค่าโรงงาน (`work\factory\`) · เอกสาร

---

## 6. กติกาที่คงอยู่ทุกเครื่อง (เจ้าของระบบกำหนด)

- **เปิด-ปิดระบบเทรด = อำนาจเจ้าของระบบเท่านั้น** (kill switch `work\AUTO_TRADER_STOP`)
- Jev **ลดความเสี่ยงได้เท่านั้น (ห้ามเพิ่ม)** · บันไดอำนาจเลื่อนขั้นด้วยหลักฐาน ≥30 เคส/กลุ่ม
- **ระบบกลางของ Hermes** (ตัวสมองเอง) แยกจากระบบเทรด: ที่นั่น Jev เป็นทั้งผู้ช่วยและผู้ตัดสินใจ
- คืนค่าโรงงานได้เสมอ: `work\factory\restore_factory.py --apply`