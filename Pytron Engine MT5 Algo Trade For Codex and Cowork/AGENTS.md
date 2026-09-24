<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  Python Qaunt Trading + AI(LLM) Live Research
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->

# 🤖 สมองเปลี่ยนได้ — คู่มือเชื่อม agentic AI ทุกตัวเข้ากับระบบเทรด

> **หลักคิดของเจ้าของระบบ:** “Hermes” หมายถึงบทบาท Agent หลักที่ประสานงานและทำงานตามสกิล
> ไม่ได้หมายความว่าต้องใช้ผลิตภัณฑ์ Hermes โดยเฉพาะ ในงานนี้ Codex ทำหน้าที่ดังกล่าวได้
> และในสำเนาแจกจ่าย Agent หลักของแพลตฟอร์มที่ผู้ใช้เลือกก็รับบทบาทเดียวกันได้

---

## 1) สถาปัตยกรรม: "ตัวถัง" กับ "สมอง"

### สัญญาโหมดล่าสุด (เจ้าของระบบ 20 ก.ย. 2026)

- โหมด 1 **เทรดด้วยสัญญาณภายใน** (`internal_only`): Python trading, งานวิจัยภายใน, ตัวปรับ และบันทึกประวัติทำงานครบ; ไม่รัน AI Signal Bot หรือ Admin Bot
- โหมด 2 **เทรดร่วมสัญญาณ AI** (`internal_llm_join`) เป็น **ค่าเริ่มต้น**: อนุญาตให้ AI/LLM ทุกส่วนที่เชื่อมในระบบทำงานร่วมกับ Python ไม่จำกัดแค่ Signal Bot และ Admin Bot
- โหมด 2 ไม่บังคับเปิดผู้ให้บริการหรือ API ที่ผู้ใช้ปิดไว้; ต้องเคารพสวิตช์และ credential ของแต่ละบริการ ส่วนโหมด 1 ต้องปิด/กัน AI ทุกจุดที่เชื่อมกับระบบเทรดและวิจัย
- ใช้ชื่อ/ค่าเริ่มต้นจาก `runtime_support.MODE_TITLES` / `DEFAULT_MODE`; อย่าสับสนเป็นโหมดปิดวิจัย/เปิดวิจัย และอย่าปิด `trading-analytics` ในโหมด 2
- ค่าเริ่มต้นไม่เปิด Live หรือยกเลิก STOP เอง หากมี STOP อยู่ งานทั้งหมดยังคงพักไว้ การเปลี่ยนโหมดไม่ให้สิทธิ์ส่งออเดอร์เพิ่ม
- บอทส่งคำแนะนำแบบ structured REC ผ่าน `submit_recommendation.py`; cron output parser อ่านเฉพาะงาน Python `trading-analytics` ไม่ใช้ชื่องาน `trading-research` รุ่นเก่า

**บทบาทกับแพลตฟอร์มเป็นคนละเรื่อง:** ในเครื่องต้นทาง ตัวตั้งเวลาเฉพาะที่อาจใช้ Hermes CLI/cron; นั่นเป็น adapter ของสภาพแวดล้อม ไม่ใช่ข้อบังคับของสกิล เมื่อเผยแพร่ไปใช้กับ Codex, Cowork, OpenClaw, Manus, Cursor หรือระบบอื่น ให้ Agent หลักของแพลตฟอร์มนั้นรับบทบาท “Hermes” โดยยึดสกิล สัญญาไฟล์ และขอบเขตสิทธิ์เดียวกัน การนำบทบาทนี้ไปใช้ไม่ได้แปลว่าตัวตั้งเวลา/CLI ของแพลตฟอร์มถูกติดตั้งหรือเชื่อมต่อให้อัตโนมัติ

**ใช้ Agent หลักตัวเดียวได้ครบสามบทบาท:** Agent หลักของแพลตฟอร์มเป็นผู้ประสานงาน (บทบาท “Hermes”), ทำงานตาม brief ของบอทสัญญาณโหมด 2 และทำงานตาม brief ของ Admin Bot ได้ โดยเปลี่ยนหน้าที่ตาม task/brief และสิทธิ์ ไม่ได้บังคับให้ติดตั้ง Agent หรือโมเดลแยกสามตัว; หากแพลตฟอร์มมี scheduler/runner เฉพาะจึงค่อยเพิ่ม adapter ให้เหมาะกับแพลตฟอร์มนั้น

**Jev เป็นส่วนเสริม ไม่ใช่ dependency บังคับ:** source ปัจจุบันใช้ OpenRouter เป็น adapter ตัวอย่างสำหรับ Jev; ผู้ใช้สำเนาแจกจ่ายจะเลือกใช้ adapter อื่นที่คืน contract เดียวกัน หรือปิด/ไม่ติดตั้ง Jev ได้ หากไม่มี key, provider ใช้งานไม่ได้, timeout หรือคำตอบผิดรูป ต้องคืนสถานะ Jev unavailable แล้วให้ Python/ระบบเดิมทำงานต่อ ห้ามตีความการไม่มี Jev เป็นสัญญาณ Buy/Sell หรือเหตุให้ระบบหยุดทั้งชุด

```
┌─────────────────────────── ระบบเทรดทองคำ (ตัวถัง — แม่นยำ ตายตัว) ───────────────────────────┐
│  market_clock · strategy_engine · side_net · auto_trader · auto_threshold · consumer        │
│  ประตู 3 ด่าน · กรอบปลอดภัย · audit · โรงงานสำรอง · kill switch                              │
└───────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                            │  สัญญากลาง = ไฟล์ + คำสั่ง shell
                                            │  (ตัวไหนทำได้ 2 อย่างนี้ = เป็นบอทได้)
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
        ┌───────────────────────┐                       ┌───────────────────────┐
        │  สมอง (agentic AI)   │                       │  สมอง (agentic AI)   │
        │  รอบวิจัยโหมด 2       │                       │  แอดมินบอท            │
        │  brief_mode2.md       │                       │  brief_admin.md       │
        └───────────────────────┘                       └───────────────────────┘
           อ่าน packet → คิด → เขียนคำแนะนำ                 อ่านสถิติ → คิด → ปรับค่า/สั่งคำสั่ง
           → submit_recommendation.py                      → admin_command.py
```

**ระบบเทรดไม่รู้จักว่า "สมอง" คือตัวไหน** — สื่อสารกันผ่าน:
1. **ไฟล์คำสั่งงาน** (`agents/brief_mode2.md` · `agents/brief_admin.md`)
2. **ข้อมูลจากสคริปต์** (`tools/llm_research_packet.py` · `news_feed.py` · `admin_bot_round.py`)
3. **เครื่องมือส่งงานกลับ** (`tools/submit_recommendation.py` · `tools/admin_command.py`)
4. **สัญญาการสื่อสาร** (`research/recommendations/CONTRACT.md` — สร้างจากโค้ดจริงอัตโนมัติ)

> ✅ เปลี่ยนสมองได้ทุกเมื่อโดย **ไม่ต้องแก้โค้ดระบบเทรดแม้แต่บรรทัดเดียว**

---

## 2) วิธีใช้ (3 คำสั่ง)

```bash
# 1) ดูว่ามีสมองตัวไหนติดตั้งในเครื่องนี้แล้ว
.venv\Scripts\python.exe agents\run_bot.py --list

# 2) ให้สมองเริ่มต้นทำงาน (ไม่ระบุ --brain = ใช้ตัวที่ติดตั้ง + เป็นค่าเริ่มต้น)
.venv\Scripts\python.exe agents\run_bot.py --role mode2      # รอบวิจัยโหมด 2
.venv\Scripts\python.exe agents\run_bot.py --role admin      # รอบแอดมินบอท

# 3) เลือกสมองเอง / ทดลองก่อน
.venv\Scripts\python.exe agents\run_bot.py --role admin --brain codex
.venv\Scripts\python.exe agents\run_bot.py --role admin --dry-run
```

**ซิงก์คำสั่งงาน** (เมื่อแก้คำสั่งงานในงาน cron แล้วต้องการให้สมองตัวอื่นเห็นด้วย):
```bash
.venv\Scripts\python.exe agents\sync_briefs.py
```

---

## 3) ตารางความเข้ากันได้ (ตรวจสดจากเครื่องนี้)

| สมอง | สถานะ | คำสั่ง headless | ติดตั้ง |
|---|---|---|---|
| **Agent หลัก (บทบาท Hermes)** | เลือกตามแพลตฟอร์ม | CLI/เครื่องมือของ Agent ที่ติดตั้ง หรือใช้งานแบบ desktop | ไม่ผูกกับผลิตภัณฑ์ Hermes |
| OpenClaw | ✅ รองรับ | `openclaw "<คำสั่งงาน>"` | github.com/openclaw/openclaw |
| Manus AI | ✅ รองรับ | `manus-cli task create --prompt "…"` | `pip install manus-cli` + MANUS_API_KEY |
| OpenAI Codex CLI | ✅ รองรับ | `codex exec "<คำสั่งงาน>"` | `npm i -g @openai/codex` |
| Claude Code | ✅ รองรับ | `claude -p "<คำสั่งงาน>"` | `npm i -g @anthropic-ai/claude-code` |
| Cursor CLI | ✅ รองรับ | `cursor-agent -p "<คำสั่งงาน>"` | cursor.com/cli |
| **Claude Cowork** | 🖥️ แบบ desktop | — (ชี้โฟลเดอร์ระบบ + ใช้ไฟล์ brief) | claude.com/product/cowork |
| Gemini CLI | ✅ รองรับ | `gemini -p "<คำสั่งงาน>"` | `npm i -g @google/gemini-cli` |
| Aider | ✅ รองรับ | `aider --message "…" --yes` | `pip install aider-chat` |
| Goose (Block) | ✅ รองรับ | `goose run -t "<คำสั่งงาน>"` | block.github.io/goose |
| GitHub Copilot CLI | ✅ รองรับ | `copilot -p "<คำสั่งงาน>"` | `npm i -g @github/copilot` |
| Cline | ✅ รองรับ | `cline -p "<คำสั่งงาน>"` | github.com/cline/cline |
| Kiro CLI (AWS) | ✅ รองรับ | `kiro -p "<คำสั่งงาน>"` | kiro.dev |
| OpenHands | ✅ รองรับ | `openhands --task "…"` | `pip install openhands-ai` |
| **ตัวอื่นในตลาด (120+)** | ➕ เพิ่มเองได้ | ใส่ใน `registry.json` | github.com/bradAGI/awesome-cli-coding-agents |

**เกณฑ์เข้ากันได้:** สมองต้องทำได้ 2 อย่าง — (1) รันคำสั่ง shell (2) อ่าน/เขียนไฟล์
→ agentic AI แทบทุกตัวในตลาดทำได้ทั้งสองอย่าง จึงเข้ากับระบบเราได้ทั้งหมด

---

## 4) เพิ่มสมองตัวใหม่ (ไม่ต้องแตะโค้ดระบบเทรด)

แก้ `agents/registry.json` เพิ่มบล็อกเดียว:
```json
{
  "id": "ชื่อย่อ",
  "name": "ชื่อเต็ม",
  "status": "supported",
  "detect": ["ชื่อคำสั่งในเครื่อง"],
  "run": ["ชื่อคำสั่ง", "{{brief_text}}"],
  "notes": "หมายเหตุ",
  "install": "วิธีติดตั้ง"
}
```
`{{brief_text}}` = ข้อความคำสั่งงานเต็ม · `{{brief}}` = ที่อยู่ไฟล์คำสั่งงาน

---

## 5) ความปลอดภัย (ใช้กับทุกสมองเหมือนกัน)

ระบบบังคับด้วย **สคริปต์** ไม่ใช่ด้วยความไว้ใจ — สมองตัวไหนก็ฝ่ากรอบไม่ได้:

| กรอบ | บังคับที่ไหน |
|---|---|
| ห้ามแตะ `live_enabled` · `magic` · `volume` · `symbol` | `consumer` + `admin_command` ปฏิเสธ |
| ห้ามสตาร์ท/หยุดตัวเทรด · ห้ามลบ kill switch | ไม่มีคำสั่งให้ทำ (เจ้าของระบบเท่านั้น) |
| ห้ามแก้โครงสร้างโค้ด | ระบบอนุญาตแค่ "ปรับค่าต่างๆ" ในกรอบตัวเลข |
| ค่าต้องอยู่ในกรอบ | `BOUNDS`/`STRUCTURE_BOUNDS` ของแอดมินบอท + ตรวจก่อนเขียนทุกครั้ง |
| คำแนะนำต้องผ่านประตูทดสอบ | Testing Gate ใน consumer (ทดสอบก่อน apply) |
| ต้องคืนค่าโรงงานได้เสมอ | `work/factory/` + `restore_factory.py` (ปักหมุดทุกครั้งที่ระบบเปลี่ยน) |
| ทุกการกระทำต้องตรวจย้อนได้ | `work/auto_trader_audit.jsonl` · `work/admin_bot_log.jsonl` · `work/agent_runs.jsonl` |

---

## 6) หมายเหตุสำหรับผู้พัฒนาต่อ

- **ไฟล์คำสั่งงานมีแหล่งเดียวใน runtime ต้นทาง** — ปัจจุบันซิงก์จากงาน cron ของ Hermes แล้วรัน `agents/sync_briefs.py`; แพ็กเกจข้ามแพลตฟอร์มให้ใช้ Agent หลักของแพลตฟอร์มปลายทางตามบทบาทเดียวกัน
  (ห้ามแก้ `brief_*.md` โดยตรง — จะถูกเขียนทับ)
- **สัญญาการสื่อสารสร้างจากโค้ดจริง** — รัน `tools/rec_contract.py` เมื่อแก้โค้ด consumer
- **งาน cron ของเครื่องต้นทางใช้ Hermes adapter ในสภาพแวดล้อมนี้** — ถ้าต้องการให้งานตั้งเวลาใช้ Agent/adapter ตัวอื่น:
  เปลี่ยนงานนั้นเป็นงานแบบ shell ที่เรียก `agents\run_bot.py --role <mode2|admin> --brain <id>`
- **ผลการรันทุกครั้ง** ถูกบันทึกที่ `work/agent_runs.jsonl` (ตรวจย้อนได้ว่าสมองตัวไหนทำอะไร เมื่อไร)
