<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# 📌 SESSION-STATE — สถานะรวมระบบ (อ่านก่อนเริ่มทำงาน session ใหม่)

อัปเดตล่าสุด: 2026-09-14
ผู้ใช้: Kanutsanan — ตอบเป็นภาษาไทยเท่านั้น ✅
**ผู้สร้างระบบ: Kanutsanan Pongpanna** · Facebook: https://www.facebook.com/LoveMoneyTH · YouTube: https://youtube.com/@lovemoneythofficial *(เครดิตอยู่ในทุกไฟล์ของระบบ)*

## ⚡ สถานะปัจจุบัน (สำคัญ)
- **ระบบเทรด = เปิดอยู่ (LIVE)** — MT5 OANDA_Global-Live-1 login 7038798 · equity $13.78 · ไม่มี position ค้าง · kill switch: ไม่มี · cron: consumer 🟢 + trading-research 🟢 (โหมด 2) + trading-analytics ⏸️
- **รีสตาร์ทล่าสุด: 2026-09-14 20:58 ไทย** (โหลดโค้ดใหม่) — supervisor PID 10584 · trader PID 4680 · ใช้ `outputs/mt5_python_bridge/restart_auto_trader.cmd` (หรือ `hermes/scripts/restart_trader.py` เมื่อสั่งจากฝั่ง Hermes)
- 📅 **บันทึกงานวิจัยทุกวัน (ข้อกำหนดของเจ้าของระบบ):** งานวิจัยเชิงหัวข้อ `research/YYYY-MM-DD-*.md` + บันทึกรายวัน `research/daily/YYYY-MM-DD.md` (อัตโนมัติ · cron 23:50 · `daily_research_log.py`) — ดู `AGENTS.md` หัวข้อ "Daily research log"
- 📄 **งานวิจัยของวันนี้ (14 ก.ย.):** `research/2026-09-14-stage-order-and-band-flexibility.md` — ลำดับด่าน (ประตู net เป็นด่าน 1) · weighted ≠ raw (แก้บั๊ก mirror) · วิจัยความยืดหยุ่นด่าน 2 · กลไกถือกำไร 3 ข้อ
- ⚠️ โค้ดที่แก้ต้องรีสตาร์ท 1 ครั้ง · **ค่า** 36 ค่า + TP/SL hot-reload เองอัตโนมัติไม่ต้องรีสตาร์ท
- ตลาด XAUUSD: เปิด อาทิตย์ 22:00 UTC (05:00 ไทย จ.) → ศุกร์ 22:00 UTC
- เปิดทั้งระบบเมื่อพร้อม: `start_FULL_system.cmd` (อยู่ outputs/mt5_python_bridge/) — gateway + trader + cron 2 ตัว
- **v0.16 (14 ก.ย.) — ลำดับด่าน + weighted band จากคะแนนจริง:**
  - **ด่าน 1 = ประตู net ต่อกลยุทธ์-ทิศทาง** (`side_net_deferred_keys` ใน strategy_engine) → คัดคีย์ที่ net ล่าสุดติดลบออกก่อน (rolling อ่าน `work/side_net_ledger.json`, แคช 20 วิ)
  - **ด่าน 2 = คะแนน 36 ค่า** (raw/probability/weighted) → แล้วจึง "เรียงลำดับผู้รอด" ด้วยหลักการเดิม (probability → weighted) เพื่อเลือกตัวที่เทรด
  - log แยกชัด: diagnostics `stage="1_side_net"` + reason ต่อท้าย "· ประตู net ชะลอไว้ก่อน N คีย์"
  - **weighted band คำนวณจากคะแนน weighted จริง** (เดิม mirror raw ซึ่งผิดสเกล — วัดจริง weighted = raw × น้ำหนักกลยุทธ์ × น้ำหนักทิศทาง, เท่ากับ raw เพียง 22.9%)
  - จำลองจาก 957 รอบจริง (`hermes/scripts/gate_order_sim.py`): แบบใหม่เทรดได้ 80 รอบ vs เดิม 79 (กู้คืน 1 รอบ) และ **ไม่มีทางแย่กว่าเดิมเชิงโครงสร้าง**
  - 📄 งานวิจัยที่เกี่ยวข้อง: `research/2026-09-13-structural-tuning-from-rounds.md` · `research/band-plan-log.md`
- **v0.15 (13 ก.ย.) — โหมดการเทรด 2 โหมด (ผู้ใช้เลือกเองตอนเริ่มใช้งาน):**
  - **โหมด 1 "เทรดด้วยสัญญาณภายใน"** — ไม่ใช้สัญญาณ LLM ของรอบ 10 นาทีเลย + ไม่เรียก LLM (ประหยัด) · cron `trading-analytics` (สคริปต์ล้วน) เปิด
  - **โหมด 2 "เทรดร่วมสัญญาณ AI (LLM)"** — ค่าเริ่มต้น · สัญญาณ LLM รวมกับสัญญาณภายใน 50:50 · cron `trading-research` เปิด
  - ทางเลือก: `choose_mode.cmd` (ดับเบิลคลิก) หรือให้ `start_FULL_system.cmd` เด้งเมนูอัตโนมัติถ้ายังไม่เคยเลือก · ค่าเก็บที่ `work/trading_mode.json` (นอก config)
  - จุดที่มีผลต่อการตัดสินใจ: `llm_signal_parser.trading_mode()` → ในโหมด 1 ทิ้งเสียง LLM (`sig_llm = None`) ใช้เฉพาะ [INTERNAL-SIGNAL]
  - `llm-recommendation-consumer` (5 นาที: ปรับ 36 ค่า + เกณฑ์ TP/SL) เปิดทั้งสองโหมด
  - 📄 งานวิจัย: `research/2026-09-13-trading-modes-internal-vs-llm.md`
- **v0.14 (13 ก.ย.) — รอบ 10/5 นาทีมีอิทธิพลต่อ "โครงสร้างการตั้งค่า" (36 ค่า + เกณฑ์ TP/SL) อัตโนมัติ ไม่แตะออเดอร์:**
  - `band_plan.py` (ในรอบ 10 นาที): จำลองตัวปรับตัวจริง (auto_threshold + net FIFO จาก order_result↔position_closed) → แผน 36 ค่า → `work/plan_band.json`
  - `tpsl_plan.py` (ในรอบ 10 นาที): R-multiple จริง (net ÷ risk_usd) ต่อกลยุทธ์ → แผนเกณฑ์ TP/SL → `work/plan_tpsl.json`
  - `plan_to_rec.py` (ในรอบ 5 นาที ก่อน consumer): แปลงแผน → REC (`set_gate` / `set_probability_gate` / `set_tpsl`) จำกัดก้าวต่อรอบ (band ≤0.06, probability ≤0.01, TP/SL ≤0.10) + cooldown 10 นาที/คีย์ + กันแผนเก่า >30 นาที
  - consumer + tester: เปิด action ใหม่ 2 ตัว (ขอบเขตปลอดภัย: probability 0.35–0.95, stop_atr 0.60–2.50, reward_risk/min_reward_risk 1.20–3.00)
  - `strategy_engine.py`: TP/SL อ่านค่าต่อกลยุทธ์จริง (`{strategy}_reward_risk`, `{strategy}_stop_atr`) ผ่าน `tpsl_stop_atr()` / `tpsl_reward_risk()`
  - `auto_threshold.py`: แก้ให้ปรับได้จริง (both_set fallback, รับ net จากรอบวิจัย, STEP CAP 0.06/รอบ, prob band ±0.01, invariant low ≤ high)
  - ★ **HOT RELOAD**: `auto_trader.hot_reload_config()` — `auto_config.json` เปลี่ยน → merge ค่าเข้า config ในหน่วยความจำทันที = **ไม่ต้องรีสตาร์ทระบบ** (REC ตั้ง `restart_after_apply=false`)
  - หลักฐานการทดสอบ: REC 17 รายการผ่าน Testing Gate → apply จริง (band ขยับ 0.06/รอบ · min_reward_risk 1.8→1.7 · breakout_reward_risk 2.0→1.9) และทดสอบ hot reload ผ่าน
  - 📄 **งานวิจัยฉบับเต็ม (สำหรับผู้พัฒนาต่อ): `research/2026-09-13-structural-tuning-from-rounds.md`**
  - 🔍 ตัวตรวจสุขภาพระบบรวม (อ่านอย่างเดียว): `%LOCALAPPDATA%\hermes\scripts\audit_full_system.py`
- **v0.13 (13 ก.ย.)**: รวม 2 งาน 10 นาทีเป็น cron เดียว (`trading-research` = script วิเคราะห์ → ป้อน LLM → REC → รายงาน) + gateway auto-check ใน start + แก้ consumer ไม่ให้สตาร์ทเทรดเองตอนระบบปิด
- **v0.12 (13 ก.ย.)**: รวม profit-anchor-guard เข้า runner เดียวกัน
- ปิด: `stop_FULL_system.cmd`

## 🏗️ สถาปัตยกรรม (3 ชั้น)
1. **เทรดд python 100%**: auto_trader.py + strategy_engine.py + market_clock.py + auto_threshold.py
2. **บันทึกข้อมูล python 100%**: audit.jsonl + script วิจัย 5 ตัว
3. **วิจัย LLM 100% (LLM-agnostic)**: research-loop + REC pipeline (llm_recommendation_consumer+tester) + โหราศาสตร์ไทย

## 🔄 วงจร Auto-Improve
LLM วิจัย (10 นาที) + แผนโครงสร้าง (band_plan 36 ค่า · tpsl_plan เกณฑ์ TP/SL) → `plan_to_rec` (รอบ 5 นาที) → REC → TESTING GATE (schema→functional→performance→fallback) → ผ่าน? apply → **hot reload (ไม่รีสตาร์ท)** : บล็อก

## 📊 ธreshold 36 ค่า (per-side, auto_threshold ปรับเอง)
| strategy | raw buy | raw sell | prob | weight |
|---|---|---|---|---|
| trend | [0.52, 0.78] | [0.60, 0.88] | 0.58 | 0.85 |
| range | [0.22, 0.40] | [0.22, 0.40] | 0.53 | 1.20 |
| mean_reversion | [0.30, 0.48] | [0.30, 0.48] | 0.56 | 0.85 |
| counter_trend | [0.35, 0.58] | [0.35, 0.58] | 0.58 | 0.95 |
| breakout | [0.68, 0.95] | [0.68, 0.95] | 0.60 | 1.10 |
| breakout_reversal | [0.60, 0.90] | [0.60, 0.90] | 0.60 | 1.00 |
- **ranking_priority = weight** (เลือกอัตโนมัติจาก net expectancy ต่อ trade)
- enumerate risk: max 8%/order, daily 20%, spread ≤0.6, volume 0.001, magic 8252026, SL/TP dynamic, hedge ≤2

## 🗂️ งานวิจัย (research/)
- 2026-09-12-architecture-llm-agnostic.md — สถาปัตยกรรมเต็ม
- 2026-09-12-auto-threshold-design.md + v2-reversal-safe.md — 36 ค่า + band health
- 2026-09-12-mechanism-profit-analysis.md — กลไก↔P/L (range +$1.57 ดีสุด, trend -$2.74 แย่สุด)
- 2026-09-12-ranking-prob-vs-weight.md — ranking (weight ชนะ)
- 2026-09-12-do-prob-weight-need-bands.md — prob/weight ไม่ต้อง band
- 2026-09-11-live-research-log.md — log ต่อเนื่อง
- auto-threshold-stats/ — สถิติ 36 ค่า (ทุก 10 นาที)
- recommendations/ — REC มาตรฐาน + applied/ ประวัติ
- collaboration-history.md — ประวัติการคุย/ทำงาน

## ⚙️ cron 2 ตัว (เปิด/ปิดพร้อมระบบ)
**trading-research**(**10นม** = script research_analytics.py [ข่าว+36ค่า+P/L+AT-vs-Trade+กลไก↔net+ranking+Profit-Anchor Guard] → ป้อนให้ LLM วิเคราะห์→เขียน REC→รายงาน) · **llm-recommendation-consumer**(5นม ทดสอบ+apply+hot reload)
- **คาบ 10 นาที = โหมดรอบเดียวจบ (ปรับ 13 ก.ย. 18:30):** เหตุที่เดิมตั้ง 20 นาที — วัดจริงรอบ 13 ก.ย. 16:22 พบ LLM ใช้ **14.5 นาที/รอบ** (22 API calls, context โตถึง 160k tokens) เพราะมัวอ่านไฟล์/รัน terminal ทั้งที่คำสั่งห้าม → แก้ 4 อย่าง: (1) ฝังเทมเพลต REC + ค่าจริง (max_risk_pct 8.0 / min_reward_risk 1.8 / กลยุทธ์ 6 ตัว) ในคำสั่ง = ข้อมูลครบ ไม่ต้องอ่านอะไรเลย (2) จำกัด `enabled_toolsets=["file"]` เท่านั้น (ไม่มี terminal/web/browser) (3) ห้ามอ่านไฟล์-ค้นหา-terminal เด็ดขาด + เป้า **≤2 การเรียกโมเดล** (4) append log ใช้ marker `<!-- END-OF-LOG -->` ท้ายไฟล์ (patch ต่อท้ายได้โดยไม่ต้องอ่าน) → เป้ารอบ 1-2 นาที
- **รายงานที่ต้องการ (สำคัญ):** ทิศทาง **ซื้อ / ขาย / กลาง** + **น้ำหนัก XX%** (แปลงเป็นค่าน้ำหนัก config = XX/100×1.5 ช่วง 0.5-1.5) — ไม่ต้องรายงานยาว · ใช้ 3 แหล่งตัดสิน: **ตัวเลขจาก script + ข่าว + ดูดวง** (โหราศาสตร์ไทยในตัว LLM — ปัจจัยรอง ~0.3-0.4; ไม่มีสคริปต์ดูดวงในระบบ) · ถ้าข้อมูลไม่ครบ → **ไม่เขียนไฟล์ ไม่ถามต่อ** ใช้ข้อมูลภายใน (rule-based) จบในรอบเดียว
- ⚠️ รอบวิจัยอาจหายได้: 13 ก.ย. 18:08 เจอ LLM ถูก route ไป `opencode-free/deepseek-v4-flash-free` แล้วล้มเหลว HTTP 400 'Model is unavailable' (fallback ถูกข้ามเพราะชี้ backend เดียวกัน) — ถ้าเกิดบ่อยให้ pin model ของ cron เป็น `deepseek/deepseek-v4.1-flash` (openrouter)
- ℹ️ CLI `hermes cron list` บนเครื่องนี้ไม่เห็นงาน (อ่านคนละ home) — ใช้เครื่องมือ cronjob (action=list/update) หรืออ่าน `%LOCALAPPDATA%\hermes\cron\jobs.json` แทน

### 🔧 ระบบแปลงคำตอบ LLM อัตโนมัติ (v0.14 — 13 ก.ย. เย็น)
- **รูปแบบคำตอบตายตัว (บังคับ):** LLM ตอบบล็อกนี้เสมอ →
  `[TRADE-SIGNAL]` / `DIRECTION=BUY|SELL|NEUTRAL` / `WEIGHT=0-100` / `ASTRO=…` / `NOTE=…` / `[/TRADE-SIGNAL]`
  — LLM **ไม่ต้องใช้เครื่องมือเลย (0 tool calls = 1 API call/รอบ)** เพราะข้อมูลครบ + ระบบเขียนไฟล์ให้เอง
- **`scripts/llm_signal_parser.py` (signal_bridge)**: อ่าน output รอบล่าสุด → parse **ทั้งสองเสียง** → รวมด้วยน้ำหนักเท่ากัน `avg = (คะแนน LLM + คะแนนภายใน)/2` (ไม่มีเสียงไหนเป็นหลัก/รอง) → REC action **`set_directional_weights`** (รองรับทั้ง `llm_recommendation_consumer.py` + `llm_recommendation_tester.py`) → `research/recommendations/latest_recommendation.json` → consumer (5 นาที) → TESTING GATE → apply
  - ถ้ามีเสียงเดียว (อีกเสียงสื่อสารไม่ได้/ไม่รู้เรื่อง) → **ใช้เสียงนั้นเต็มศักดิ์ ไม่ลดทอน** · ไม่มีทั้งสองเสียง → ไม่ปรับอะไร (บันทึกที่ `research/llm-signal-log.md`)
- **🧭 สัญญาณภายใน = อีกหนึ่งเสียงที่มีศักดิ์เท่าเทียม LLM (ไม่ใช่ตัวสำรอง):** step `internal_signal.py` คำนวณทิศทาง+น้ำหนักจากหลักฐานภายในล้วน —
  `score = 0.45×แรงซื้อ/ขาย (audit buy_pressure−sell_pressure) + 0.35×ความเอนของ engine (router_decision 24 ชม.) + 0.20×ดูดวง` ·
  ทิศทาง BUY/SELL เมื่อ |score| > 0.15 · น้ำหนัก = 50+40×|score| (สูงสุด 90) · **ถ้า rolling net (20 ออเดอร์) ยังติดลบ → ลดความแรง 20%** (net-first prudence) · ส่งออกเป็นบล็อก `[INTERNAL-SIGNAL]` คู่กับ `[TRADE-SIGNAL]` ของ LLM
  - LLM ไม่เห็นสัญญาณภายใน (คงความเป็นอิสระของสองเสียง แล้วค่อยรวมที่ตัว bridge) — ระบุในคำสั่ง cron แล้วว่าอีกเสียงมีศักดิ์เท่ากัน
- **แปลงน้ำหนัก:** `1.0 ± (WEIGHT-50)/50×0.10` → ช่วง 0.90-1.10 (ตรงกับที่ `strategy_engine` clamp เมื่อ bounded_live เปิด: `direction_low/high = 0.90/1.10`)
- **กัน churn:** เขียน REC เมื่อ "ทิศทางพลิก" หรือ "น้ำหนักเปลี่ยน ≥10" และห่างจากครั้งก่อน ≥30 นาที · NEUTRAL = คืนสมดุล 1.0 ทุกตัว · trail อยู่ที่ `research/llm-signal-log.md`
- **ดูดวง (โหรทายหนู + เลข 7 ตัว 9 ฐาน):** เพิ่ม step `astrology_step.py` เข้า STEPS ใน `research_analytics.py` → เรียก `outputs/mt5_python_bridge/thai_astrology.py` ป้อนสัญญาณ (ทิศทาง+strength) ให้ LLM ทุกรอบ
- **ข่าว:** investing.com RSS commodities/markets/macro กรองเฉพาะข่าวที่มีนัยต่อ XAUUSD (news_research.py เดิม — เปลี่ยนชื่อหัวข้อเป็น "ข่าวทองคำล่าสุด")
- **เทสต์:** `scripts/test_llm_signal_parser.py` (unit + integration: parse → REC → consumer.validate → กัน churn → ลบไฟล์ทดสอบเอง) ผ่านทั้งหมด · unit tests โปรเจกต์ 26/26 ผ่าน

## 🚨 ข้อสำคัญ: gateway ต้องรัน (ไม่งั้น cron ไม่ยิง)
- ตรวจ: `hermes gateway status` · เปิด: `hermes gateway start` (ติดตั้ง auto-start แล้ว: task `Hermes_Gateway`)
- task เก่า `HermesGateway` ถูก **disable** แล้ว (กันเปิด gateway ซ้ำ 2 ตัว)
- `start_FULL_system.cmd` เช็ค+เปิด gateway ให้อัตโนมัติทุกครั้งที่เปิดระบบ

## 🔍 ผลตรวจโครงสร้าง (13 ก.ย. — ตรวจอัตโนมัติ)
- cron 2 งาน ↔ start/stop_FULL_system.cmd ตรงกันทั้งไฟล์ ✅
- ไฟล์ runner research_analytics.py เรียก 7 step มีครบ ✅ · ไฟล์ระบบหลัก 9/9 ✅ · ไฟล์วิจัย/กลไกใน scripts 9/9 ✅
- governance: 36 ค่า = raw/weighted 24 (per-side) + probability/probability_max 12 (ค่ากลางใช้ร่วมสองฝั่ง
  — engine fallback `probability_buy` → `probability`; ตามผลวิจัย "prob/weight ไม่ต้องมี band" จึงถูกต้อง ไม่ใช่ค่าขาด) ✅
- trade_enabled เปิดครบ 6 กลยุทธ์ · net-first keys + FREQ FLOOR keys อยู่ใน config ✅
- adaptive.enabled = **false** ใน config (ปิดโดยการตั้งค่าเดิม) — logic กันปิดกั้นทำงานทันทีเมื่อเปิด
- **ผลตรวจ 13 ก.ย. 18:49 (`scripts/audit_system.py` — ตรวจซ้ำได้ทุกเมื่อ):** โมดูลหลัก 10/10 · ขั้นวิจัย 8 ขั้น (เพิ่ม astrology) · syntax 36/36 ไฟล์ผ่าน · unit tests โปรเจกต์ 26/26 · cron 2 งาน ↔ start/stop_FULL_system.cmd ตรงกัน ✅ · supervisor log ไม่มี fatal/crash (exit=0 ล่าสุด 12 ก.ย. 13:06) · process Hermes 2 ชุด (gateway + serve, launcher+worker) ไม่ซ้ำ · MT5 terminal เปิดอยู่ 1 ตัว · kill switch = หยุดโดยเจตนา 12 ก.ย. 13:06
- **ความสุขุม (prudence) 13 ก.ย.:** risk 8% / RR 1.8 · trade_enabled 6/6 · `strategy_router.adaptive.enabled=false` (threshold ถูกแก้จากวิจัยเท่านั้น) · strategy_weights 0.85-1.2 (ในช่วง 0.5-1.5) · directional_weights 12/12 = 1.0 (สมดุล) · governance 68 ค่าตัวเลข · churn_guard 3600s · live_enabled True / magic 8252026 / volume 0.001

## 🎯 กลไกเข้าหาโซน Net Profit (v0.11)
- **net-first ทุกตัว**: auto_threshold / ranking / AT-vs-Trade / P/L ใช้ net expectancy (USD/trade) เป็นตัวตัดสิน — winrate เป็นแค่ข้อมูลรายงาน
- **FREQUENCY FLOOR (ห้ามปิดกั้นการเทรด)**: เงียบ ≥12 ชม.→ผ่อน band; ออเดอร์<5→ห้าม tighten; lockout 24 ชม.→คืน baseline
- **adaptive gate**: ปิดกลยุทธ์พร้อมกัน ≤2 ตัว + ปิด ≥12 ชม. → เปิดคืนอัตโนมัติ (audit adaptive_reenable); **REC ห้าม toggle_strategy=false** (ใช้ set_weights)
- ทดสอบกลไกกันปิดกั้น: `outputs/mt5_python_bridge/test_freq_floor.py` (11 เคส ผ่านหมด)
- **Profit-Anchor Guard**: snapshot ค่าที่ทำ HWM → คืนค่าอัตโนมัติเมื่อหลุดโซน (hot reload) + คืน trade_enabled=ON เสมอ
- เป้า: net/trade > $0.02 = ผ่อนรับสัญญาณเพิ่ม | net/trade < 0 = กรองเข้ม

## 🔑 Key ลับ
- ระบบหลักใช้ .env (OPENROUTER_API_KEY) + DPAPI file (work/openrouter_api_key.machine.dpapi)
- user เพิ่งตั้ง System Environment Variables ใหม่ (variable name/value) — session ใหม่ต้องถามชื่อ var ถ้าจะให้โค้dอ่านจาก env

## 📝 ข้อควรจำ (กฎ user)
- รายงาน Telegram ภาษาไทยทุกครั้งเมื่อ LLM วิจัย (แม้ idle)
- งานวิจัยทั้งหมดอยู่ใน research/ เท่านั้น
- RAM 4GB น้อย — งานหนักตรวจ RAM; numpy บางครั้ง import fail (testing gate แก้ให้ไม่ block แล้ว)
- ใช้ PYTHONUTF8=1 ทุกครั้งที่รัน python (path ไทย)