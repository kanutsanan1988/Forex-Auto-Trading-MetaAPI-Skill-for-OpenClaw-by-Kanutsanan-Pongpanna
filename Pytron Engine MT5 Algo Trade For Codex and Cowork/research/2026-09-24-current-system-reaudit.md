# Python Quant Trading + AI(LLM) Live Research — ทบทวนโครงสร้างระบบล่าสุด

ผู้สร้างระบบ: Kanutsanan Pongpanna — https://www.facebook.com/LoveMoneyTH  
วันที่ตรวจ: 24 กันยายน 2026 (เวลาไทย)  
ขอบเขต: ตรวจ source/config/ตารางงานและทดสอบแบบออฟไลน์; ไม่เชื่อมบัญชีซื้อขาย ไม่ส่งคำสั่ง และไม่แก้กฎการเทรด

> นิยามรุ่นที่เจ้าของระบุ: “Python Quant Trading + AI(LLM) Live Research” — Settrade e-Open Account / MTS Gold Futures + MT5. ข้อความเรื่องกฎหมายเป็นนิยามที่เจ้าของเสนอ ไม่ใช่ผลยืนยันทางกฎหมายหรือการรับรองกำไร

## ข้อกำหนดโหมดล่าสุดจากเจ้าของ

- **โหมด 1 — เทรดด้วยสัญญาณภายใน:** ระบบเทรดและงานวิจัย Python ทำงานได้ โดยไม่ใช้ AI/LLM ที่เชื่อมร่วมระบบ
- **โหมด 2 — เทรดร่วมสัญญาณ AI:** เปิดการทำงานร่วมกับ AI ทุกส่วนที่กำหนดให้เป็นส่วนหนึ่งของระบบ ไม่จำกัดเพียง AI Signal Bot โหมด 2 และ Admin Bot; เป็นค่าเริ่มต้น
- ทั้งสองโหมดใช้ Python engine, ตัวจัดการออเดอร์/Position และงานวิจัยภายในเดียวกัน ความต่างคือสิทธิ์และเส้นทาง AI ที่เปิดใช้งาน
- การเลือกโหมดต้องไม่ลบ Kill Switch, ไม่เพิ่มสิทธิ์ Live และไม่สั่งส่งออเดอร์
- “Hermes” คือบทบาท Agent หลักที่ประสานงาน ไม่ใช่ข้อกำหนดให้ใช้ผลิตภัณฑ์ Hermes; Codex ทำหน้าที่นี้ในงานปัจจุบัน และ Agent หลักของแพลตฟอร์มปลายทางทำหน้าที่เดียวกันในสำเนาแจกจ่ายได้
- Agent หลักตัวเดียวกันรับงานประสานงาน, บอทสัญญาณโหมด 2 และ Admin Bot ได้ตาม brief/สิทธิ์ ไม่บังคับแยก Agent สามตัว
- บทบาทข้ามแพลตฟอร์มไม่เท่ากับมี CLI/cron adapter ให้โดยอัตโนมัติ; ตัว scheduler/runner ต้องรองรับแพลตฟอร์มนั้นแยกต่างหาก
- Jev เป็นส่วนเสริมที่ไม่บังคับ: OpenRouter เป็น transport ตัวอย่างของ source ปัจจุบัน; สำเนาแจกจ่ายอาจเพิ่ม adapter อื่นตาม contract หรือปิด Jev ได้ และเมื่อไม่มี/เชื่อมไม่ได้ต้องปล่อยระบบ Python ทำงานต่อ

## สรุปผล

ชื่อโหมดและค่าเริ่มต้นตรงกับนิยามล่าสุดหลังปรับ source เฉพาะจุด: ตัวควบคุมจัดกลุ่มงาน Python กับ AI jobs แยกกัน, รวม `brain-consult` ในกลุ่ม AI และมี mode guard ใน OpenRouter, Jev และ Agent runner. โหมด 1 จึงกัน callsites เหล่านี้; โหมด 2 อนุญาตให้เรียก แต่ยังเคารพ `openrouter.enabled=false` และสวิตช์ราย provider ไม่ได้บังคับเปิดบริการที่ผู้ใช้ปิดไว้. ยังต้องตรวจ catalog ของ AI callsites และตัวตั้งเวลาจริงทั้งชุดก่อนรับรองว่าไม่มีทางเรียกหลุดจาก mode gate

อีกจุดที่ต้องตัดสินใจก่อนจัดทำสำเนาแจกจ่ายคือ **Structural setup**: `strategy_engine.py` บันทึกการยืนยันเชิงโครงสร้างเป็นข้อมูลวินิจฉัยเท่านั้น และระบุชัดว่าไม่ใช้ veto คะแนน/Probability ที่ผ่านเกณฑ์ตัวเลขได้ ขณะที่ประวัติข้อกำหนดเจ้าของเคยย้ำว่าขาด structural setup ต้องไม่เทรด ความหมายนี้มีผลต่อ Live โดยตรง จึงไม่ควรอ้างว่าโค้ดปัจจุบันผ่านข้อกำหนดดังกล่าว

## โครงสร้างที่ตรวจพบ

1. **เส้นทางสัญญาณ Python/Production** — `auto_trader.py` ดึงกราฟ/ราคา, เรียก `strategy_engine.decide_market`, ตรวจสุขภาพตลาด, คำนวณคำสั่ง/ความเสี่ยง และเป็นผู้ส่งคำสั่ง MT5; วงรอบหลักตั้งทุก 60 วินาที การจัดการ Position อยู่ในรอบเดียวกันก่อน risk gate และคำสั่งเข้าใหม่
2. **ตัวสร้างสัญญาณ** — หก Agent: Trend, Range, Mean Reversion, Breakout, Counter-Trend และ Breakout Reversal; แยก Buy/Sell รวม 12 ทิศทาง มีคะแนนดิบ, Probability และคะแนนถ่วงน้ำหนัก; ใช้ side-net และเกณฑ์ bounded-live 36 ค่าเมื่อเปิดสวิตช์; หลังผ่านเกณฑ์ใช้ Top 4 จัดแรงกด Buy/Sell และมี Stage 3 ตรวจทิศทางสวน
3. **AI ในเส้นทางเทรด** — `auto_trader.analyze()` เรียกตัวประเมิน OpenRouter เสมอในระดับฟังก์ชัน แต่ `openrouter_agents.run_dual_agents()` ส่งผล Python ตรงเมื่อ `openrouter.enabled=false`; หากเปิด จะเพิ่มสัญญาณ AI และผู้ตัดสิน AI อีกชั้นหนึ่ง การเลือกโหมดไม่ได้แก้สวิตช์นี้
4. **AI/LLM งานวิจัย** — Hermes มี AI Signal Bot, Admin Bot และงาน `brain-consult`; Jev เป็น decision-model ที่ใช้ OpenRouter Alpha API และมีการเรียกจากชุดข้อมูลของ Mode 2/Admin; `interbot` เป็นการแลกเปลี่ยนคำตอบ/ข้อมูลระหว่างบทบาท ไม่ใช่ตัวส่งคำสั่ง MT5 ด้วยตัวเอง
5. **Python งานวิจัยภายใน** — `trading-analytics`, `llm-recommendation-consumer` และ `trading-daily-research-log` เป็นงานสคริปต์; Consumer สามารถรับคำแนะนำ Python ได้ ไม่ใช่การเรียก LLM โดยตัวมันเอง และไม่ควรปิดเมื่อเลือกโหมดภายใน

## ตรวจนิยามโหมดเทียบกับการควบคุมปัจจุบัน

| ประเด็น | สิ่งที่พบใน source | ผลต่อข้อกำหนดล่าสุด |
|---|---|---|
| ชื่อ/ค่าเริ่มต้น | `runtime_support.DEFAULT_MODE = internal_llm_join`; title ไทยตรง; เมนู Enter เปล่าเลือก Mode 2 แต่ข้อความเมนูยังอธิบาย Mode 2 ว่ามีเพียง AI Signal Bot + Admin Bot | ชื่อ/ค่าเริ่มต้นผ่าน; คำอธิบายไม่ครบตามข้อกำหนดล่าสุด |
| งานที่ตัวควบคุมดูแล | `choose_mode.py` แยก Python jobs กับ AI jobs; AI tuple รวม Signal Bot, Admin Bot และ `brain-consult` | แก้ตัวควบคุมให้จัดการ AI jobs ที่ลงทะเบียนแล้ว; ยังต้องตรวจรายการให้ครบกับทุกจุดเรียก |
| `brain-consult` | เป็น AI job ที่ถูกเพิ่มใน `AI_JOBS`; mode 1 หยุด, mode 2 เปิดเมื่อไม่มี Kill Switch | อยู่ใน mode selection ตาม source ปัจจุบัน |
| `brain-consult-alert` | เปิดอยู่ แต่ `no_agent=true` และทำงานผ่าน probe/script | เป็นงานแจ้งเตือน/สคริปต์ ไม่ใช่การเรียก LLM ตามสถานะที่ตรวจ |
| OpenRouter สัญญาณเทรด | `auto_config.openrouter.enabled=false`; helper ปิดการเรียกจริงเมื่อค่านี้เป็น false; selector ไม่ผูกค่ากับโหมด | ตอนนี้ไม่เรียกจากเส้นทางนั้น แต่ Mode 1 ไม่มี guard ป้องกันกรณีค่านี้ถูกเปิดไว้ |
| Jev | `jev_config.enabled=true`; callsite ของข่าว/Admin จำกัด context เป็น Mode 2/Admin; แต่การตั้งค่าไม่ได้เปลี่ยนตามโหมด และ CLI/บริบท Hermes มีทางเรียกแยก | ควรรวมในแผนที่ AI และแยกงานทั่วไปออกจาก AI ที่ร่วม Production |
| Kill Switch | มี `work/AUTO_TRADER_STOP`; selector ไม่ resume cron เมื่อมีไฟล์นี้ | ปลอดภัยกว่าการเปิดระบบอัตโนมัติจากการเปลี่ยนโหมด แต่ไม่เท่ากับยืนยันว่า Live ทำงาน |

**นิยามบทบาทข้ามแพลตฟอร์ม:** “Hermes” เป็นบทบาท Agent หลัก ไม่ใช่ข้อกำหนดผลิตภัณฑ์; ตัวแทนในแต่ละแพลตฟอร์มใช้สกิล/contract เดียวกันได้ แต่ adapter สำหรับ scheduler/CLI ยังต้องมีและทดสอบแยกกัน

**Jev / provider portability:** source ปัจจุบัน hard-code OpenRouter Alpha Decisions transport ใน `tools/jev.py` และ `tools/jev_connect.py`; จึงรองรับ OpenRouter ในตัว ไม่ควรอ้างว่ามี adapter provider อื่นสำเร็จแล้ว ผู้ทำสำเนาสามารถต่อ provider ของตนผ่าน adapter ที่ทำให้ได้ผล contract เดียวกัน หรือปิด Jev ทั้งหมดได้ ผลเรียก Jev ถูกออกแบบให้ `ok:false`/`None` เมื่อปิดหรือ unavailable และ callers ของข่าว/แอดมินมีทางทำงานต่อ อย่างไรก็ดีต้องทดสอบกรณีไม่มี Jev แยกก่อนส่งมอบสำเนา

## จุดไม่ตรงกันที่ต้องแก้/ตัดสินใจก่อนบรรจุสำเนา

### 1. Structural setup กับคะแนน

ใน `strategy_engine.decide_market()` มี `structural_eligible` และ `structural_side` แต่ `structural_mode` เป็น `diagnostic_only`; เหตุผลเลือกผู้ชนะบอกว่า structural setup ไม่ได้ยับยั้งทิศทางที่ผ่านคะแนน/Probability โค้ดส่วนนี้สวนกับข้อกำหนดในประวัติที่ระบุว่า “ขาด Structural setup แม้คะแนนสูงก็ไม่เทรด” และทดสอบปัจจุบันมีกรณีที่จัดลำดับ Probability ก่อนการตรวจ strategy setup ด้วย ต้องกำหนด source-of-truth ก่อนปรับ Live/ทำสำเนา ไม่ควรแก้เกณฑ์นี้โดยเดา

### 2. README/สำเนาเก่าไม่ใช่ source ล่าสุด

README หลักระบุทบทวนโหมดวันที่ 20 ก.ย. และระบุชุดงานหลัก 5 งาน; สภาพแวดล้อม Hermes ปัจจุบันมี 7 งาน รวม `brain-consult` และ `brain-consult-alert` นอกจากนี้ ZIP เดิมลงวันที่ 21 ก.ย. และ stage ของ skill เก่าขาดไฟล์ Jev ใหม่ จึงห้ามใช้เป็นหลักฐานว่าสะท้อน source วันที่ 23 ก.ย. แล้ว สำเนาทั้งสองชุดต้องสร้างใหม่จาก source ที่ตรวจรอบนี้ และมี manifest บอกเวอร์ชัน/วันที่ฐานข้อมูลอย่างชัดเจน

### 3. MetaAPI สำหรับสำเนา OpenClaw/Hermes/ClawHub/Manus

ใน source ปัจจุบันของ `outputs/mt5_python_bridge` ไม่พบ adapter MetaAPI; เส้นทาง Production อิง MT5 local terminal. พบหลักฐานเชื่อมต่อ MetaAPI แบบ read-only ใน stage เก่าวันที่ 21 ก.ย. (สถานะ `connected_read_only`, ไม่เรียก `order_send`) แต่หลักฐานนั้นไม่พิสูจน์ว่า shim ทำงานร่วมกับ source วันที่ 23 ก.ย. ได้ครบ จึงต้องตรวจ adapter, สัญญา API/คำสั่งทุกจุด และทดสอบเชื่อมต่อ read-only ใหม่บนเวอร์ชันที่จะบรรจุ ก่อนทำ ZIP ชุดที่สอง ห้ามนำข้อมูลบัญชีหรือ credential จริงใส่แพ็กเกจ

## สถานะเครื่องขณะตรวจ (24 ก.ย. 2026)

- โหมดที่บันทึก: `internal_llm_join` / เทรดร่วมสัญญาณ AI
- Kill Switch: **มีอยู่**; `live_enabled=true` เป็นเพียงค่า config ไม่ได้ลบ stop และไม่ได้ยืนยันว่ามีการส่งคำสั่ง
- OpenRouter core flag: `false`; Jev config: `enabled=true` (ไม่พิมพ์ค่า key หรือ credential)
- Audit ล่าสุดที่มีในไฟล์: `stopped` วันที่ 19 ก.ย. 2026 เหตุผล Kill Switch — ไม่มีหลักฐานใน audit นี้ให้ยืนยันว่าระบบเทรดกำลังทำงาน ณ เวลาตรวจ
- Hermes ณ เวลาตรวจ: งาน Python 3 งาน, Signal Bot, Admin Bot และ `brain-consult` ปิด; `brain-consult-alert` เปิดแต่เป็น `no_agent=true`
- การตรวจนี้ไม่เปิด/ล้าง Kill Switch และไม่ส่ง/ปิดออเดอร์; ทดสอบ MetaAPI read-only แล้ว แต่บัญชีปฏิเสธ auth token ปัจจุบัน จึงยังไม่ยืนยันการเชื่อมต่อสำเร็จ

## การทดสอบออฟไลน์

- `outputs/mt5_python_bridge/tests/test_mode_contract.py`: 25 tests, ผ่าน 22, ข้าม 3 (ไม่มี external research scripts ใน test workspace); การรันครั้งแรกติด CP1252 ตอนพิมพ์ภาษาไทย จากนั้นแก้ policy UTF-8 ใน source และรันตรงโดยไม่ตั้ง environment ชั่วคราว ได้ผลผ่าน
- `outputs/mt5_python_bridge/tests/test_strategy_engine.py`: 13 tests ผ่าน
- `release/skill-build-v4/.../metaapi/test_shim_offline.py`: 22 tests ผ่านโดยใช้ fake connection; ไม่ต่อเครือข่าย/บัญชีจริง และเป็นหลักฐานของ adapter รุ่นเก่าเท่านั้น
- ทดสอบเชื่อม MetaAPI จริงแบบ `METAAPI_SHIM_READ_ONLY=1` วันที่ 24 ก.ย. 2026: `initialize()` ล้มเหลวเพราะ MetaAPI ตอบกลับ unauthorized/invalid auth token; ไม่เรียก `order_send` และไม่แสดง credential ในรายงาน ชุดแจกจ่ายที่กำหนดให้เชื่อม MetaAPI จึงยังติด gate จนกว่าจะทดสอบใหม่ด้วย credential ที่ใช้ได้
- ZIP ตัวอย่าง MetaAPI ที่ผู้ใช้แนบมี JWT ฝังใน `example.py` และมีโค้ด `account.deploy()` กับการส่ง pending order; ตรวจเฉพาะเนื้อหาโดยไม่รัน, ไม่ใช้ token, ไม่นำ token/โค้ดสั่งเทรดไปใส่สำเนาแจกจ่าย
- Token ที่ฝังในตัวอย่างไม่ตรงกับ token ปัจจุบันที่ตั้งในเครื่อง; อย่างไรก็ดี token ในไฟล์แนบควรถูกเพิกถอน/หมุนใหม่ เพราะปรากฏในไฟล์ที่แชร์และมีสิทธิ์เขียนตาม claim ในตัวอย่าง
- ทดสอบ MetaAPI SDK โดยตรงด้วยตัวแปรปัจจุบันแบบ read-only: `get_account()` ถูกปฏิเสธที่ขั้น account lookup ด้วย `UnauthorizedException`; ไม่เรียก `deploy`, `create_limit_buy_order` หรือ `order_send`
- หลังผู้ใช้เปลี่ยน credential ใน `release/metaapi-validation-local/.env` ทดสอบ SDK แบบ read-only สำเร็จ: `get_account`, account state, RPC synchronization, account/position/order reads ผ่าน; ยังต้องพิสูจน์ MT5 shim กับ source ล่าสุด
- การทดสอบข้างต้นเป็น unit/regression tests เท่านั้น ไม่ใช่การทดสอบเชื่อมต่อ MetaAPI/MT5, Live orders หรือผลกำไร

## การแก้ไขในรอบตรวจนี้

แก้ encoding ของโปรเจกต์ให้เป็น UTF-8 ถาวรใน `runtime_support.configure_utf8_stdio()` พร้อม regression test; และปรับการควบคุม AI-mode ให้รวม AI cron ที่ลงทะเบียน, กัน OpenRouter/Jev/Agent runner ในโหมด 1, และให้โหมด 2 อนุญาตโดยยังเคารพสวิตช์ provider. ไม่มีการเปิด OpenRouter, แก้กฎกลยุทธ์, ความเสี่ยง, TP/SL, Live permission หรือ Kill Switch

## งานถัดไปในสายส่งมอบ

1. ทำ inventory ใหม่ของ source, factory defaults, research corpus และระบบ AI ทั้งหมด; แยก owner source ออกจาก archive/test fixtures
2. ตรวจ AI callsites, cron/CLI, การส่ง REC และ scheduler adapters ให้ครบ; ยืนยันว่า Mode 1 = Python-only และ Mode 2 อนุญาต AI integrations ตามการตั้งค่าผู้ใช้ โดย Agent หลักเป็นบทบาทที่แพลตฟอร์มใดก็รับได้
3. ตกลง/ทดสอบความหมาย Structural setup ก่อนปรับ production gate
4. พิสูจน์ MetaAPI adapter กับ source ล่าสุดใน read-only mode; ยังไม่ส่งคำสั่งซื้อขาย
5. สร้าง ZIP Codex/Cowork/Cursor และ ZIP OpenClaw/Hermes/ClawHub/Manus แยกกัน แล้วทำ QC สองรอบต่อ ZIP: ตรวจ manifest/secret exclusion/README and factory values และติดตั้งทดสอบใน temporary directory โดยไม่เปิด Live
