<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# Pytron Engine MT5 Algo Trade — for OpenClaw · Hermes · clawhub.ai · Manus AI

> ### นิยามรุ่นใหม่ของระบบนี้
> **Python Qaunt Trading + AI(LLM) Live Research**
> **อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา**
> **เทรดในไทยมีกฎหมายรองรับ 100% · Settrade e-Open Account · MTS Gold Futures + MT5**
> <https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com>
>
> _คำว่า "เทรดในไทยมีกฎหมายรองรับ 100%" เป็นนิยามที่เจ้าของระบบกำหนดให้บันทึกกำกับไว้ในทุกไฟล์
> ไม่ใช่คำรับรองทางกฎหมายจากผู้สร้างหรือหน่วยงานใด_

**ผู้สร้างระบบ (Creator): คณัสนันท์ พงษ์พันนา — Kanutsanan Pongpanna**
Facebook <https://www.facebook.com/LoveMoneyTH> · YouTube <https://youtube.com/@lovemoneythofficial>

สกิลนี้บรรจุ **ระบบเทรดทองคำทั้งระบบ + คลังงานวิจัยทั้งหมด** และขับเคลื่อนผ่าน
**MetaAPI** จึงรันได้บนเครื่องที่ **ไม่มีเทอร์มินัล MT5 เลย** (ลินุกซ์ · คอนเทนเนอร์ · เครื่องของคนอื่น)

---

## ⚠️ สำเนาแจกจ่าย — อ่านก่อนใช้ (Distribution notice)

> **การเทรดของแต่ละคนมีสไตล์ มีค่านิยมชมชอบ และมีวิถีทางของใครของมัน
> ไม่ค่อยมีใครมีสไตล์ที่เหมือนกันนัก**
>
> ดังนั้นระบบนี้จึงถูกออกแบบมาให้ผู้ใช้ **ปรับแต่งระบบให้เข้ากับสไตล์การเทรดของตัวเองได้**
> ผู้นำไปใช้ทุกคนสามารถให้ AI ที่คุณใช้งานอยู่ **เรียนรู้โครงสร้าง อธิบายระบบนี้ให้เข้าใจง่าย
> และปรับแต่งระบบได้ทั้งหมดทุกส่วนตามอัธยาศัยของผู้ที่นำไปใช้งานได้แบบ 100%**
> เป็น **โค้ดระบบเปิด** สามารถ **พัฒนาต่อยอดได้อย่างไร้ขีดจำกัด**

- ไม่มีการรับประกันกำไร ไม่มีคำสัญญาผลตอบแทน ระบบเดิมเป็นผลงานวิจัยส่วนตัว
- แพ็กนี้ **เริ่มแบบหยุด (STOP) และไม่เปิดเทรดจริง** — ต้องตั้งค่าบัญชีของคุณเองก่อน
- แพ็กนี้ **ไม่มีคีย์/รหัส/โทเคนใด ๆ** ของผู้สร้าง และไม่มีสถานะการเทรดสดของผู้สร้าง
- เก็บเครดิตผู้สร้างไว้เสมอเมื่อเผยแพร่ต่อ (ดู [LICENSE](LICENSE))
- **สไตล์การเทรดเป็นเรื่องส่วนตัว** — ปรับพารามิเตอร์ทุกตัว แก้กลยุทธ์ เพิ่มกลยุทธ์ใหม่ได้ทั้งหมด

---

## 1) โครงสร้างระบบ (System structure)

```
Pytron Engine MT5 Algo Trade For OpenClaw/
├── SKILL.md                     ← จุดเข้าใช้งานสำหรับ AI (OpenClaw · Hermes · clawhub · Manus)
├── README.md                    ← ไฟล์นี้: โครงสร้าง + ค่าโรงงานของตัวแปรเริ่มต้น
├── .clawhubignore               ← กติกาการเผยแพร่ขึ้น clawhub.ai (กันความลับ เก็บค่าโรงงาน)
├── trading-system/              ← ระบบเทรดทั้งหมด (ยกไปรันที่อื่นได้)
│   ├── outputs/mt5_python_bridge/   ← เครื่องยนต์เทรด (Python)
│   │   ├── auto_trader.py            ลูปหลัก: ตัดสินใจ → ส่งคำสั่ง → จัดการไม้ → บันทึก
│   │   ├── strategy_engine.py        12 คะแนนทิศทาง (trend/range/... × buy/sell)
│   │   ├── auto_threshold.py         ตัวปรับเกณฑ์/แถบ (band) อัตโนมัติ
│   │   ├── adaptive_shadow.py        ชั้นปรับตัวแบบเงา (ไม่แตะการเทรดจริง)
│   │   ├── bounded_adaptive_research.py  วิจัยปรับตัวแบบมีขอบเขต
│   │   ├── market_analyzer.py        วิเคราะห์ตลาด/ATR/เงินต่อจุด
│   │   ├── market_clock.py           นาฬิกาตลาด (เปิด/ปิด, ปลอดภัย)
│   │   ├── side_net.py               ด่านเน็ตรายฝั่ง (buy/sell)
│   │   ├── trade_guard.py            กรอบกันพลาดก่อนส่งคำสั่ง
│   │   ├── live_executor.py          ชั้นส่งคำสั่งจริง
│   │   ├── llm_recommendation_consumer.py  รับคำแนะนำ AI → ผ่านประตูทดสอบ → apply
│   │   ├── llm_recommendation_tester.py    ประตูทดสอบคำแนะนำ (Testing Gate)
│   │   ├── openrouter_agents.py      บอท AI ผ่าน OpenRouter (ปิดไว้เป็นค่าเริ่มต้น)
│   │   ├── news_feed.py              ข่าว/ข้อมูลประกอบการวิจัย
│   │   ├── runtime_support.py        โครงสร้างพื้นฐาน: root, ล็อกไฟล์, atomic JSON, โหมด
│   │   ├── strategy_backtest.py      ทดสอบย้อนหลัง
│   │   ├── mt5_probe.py              ตรวจบัญชี/symbol/สภาพเทอร์มินัล
│   │   ├── thai_astrology.py         ข้อมูลประกอบแบบไทย (ตามความเชื่อของเจ้าของระบบ)
│   │   ├── trade_window_analysis.py  วิเคราะห์ช่วงเวลาที่ควรเทรด
│   │   ├── tools/                    เครื่องมือ 27 ตัว (วิจัย · ตรวจสุขภาพ · แอดมิน · สัญญา)
│   │   ├── tests/                    ชุดทดสอบ 6 ไฟล์ (68 เทสต์)
│   │   └── *.cmd                     ตัวเรียกใช้งานแบบคลิกเดียว (Windows)
│   ├── agents/                  ← "สมอง" AI: registry + run_bot + briefs
│   │   ├── registry.json              ทะเบียนสมอง 15 ตัว + วิธีเรียกแบบ headless
│   │   ├── run_bot.py                 ตัวรันสมอง (role × brain)
│   │   ├── brief_mode2.md             คำสั่งงาน: รอบวิจัยโหมด 2
│   │   ├── brief_admin.md             คำสั่งงาน: แอดมินบอท
│   │   └── sync_briefs.py             ซิงก์คำสั่งงานจากแหล่งเดียว
│   ├── research/                ← คลังงานวิจัยทั้งหมด (ทุกไฟล์ ทุกช่วงเวลา)
│   └── work/factory/            ← ค่าโรงงาน + เครื่องมือคืนค่าโรงงาน
├── metaapi/                     ← สะพาน MetaAPI (รันได้โดยไม่ต้องมี MT5 ในเครื่อง)
│   ├── metaapi_mt5_shim.py           อะแดปเตอร์เลียนแบบ API MetaTrader5
│   ├── test_shim_offline.py          เทสต์ออฟไลน์ 22 ตัว
│   └── evidence/                     หลักฐานการเชื่อมต่อจริง (อ่านอย่างเดียว)
├── references/                  ← เอกสารอ้างอิงเชิงลึก
│   ├── architecture.md               สถาปัตยกรรม + การไหลของข้อมูล
│   ├── operations.md                 วิธีเดินระบบอย่างปลอดภัย
│   ├── portability.md                ย้ายเครื่อง · MetaAPI · ข้อจำกัดจริง
│   ├── research.md                   วิธีทำวิจัยต่อยอด
│   └── modes.md                      โหมด 1 / โหมด 2 อย่างละเอียด
├── scripts/
│   ├── verify_package.py             ตรวจความสมบูรณ์ + ตรวจว่าไม่มีความลับ
│   ├── metaapi_connect_check.py      ตรวจการเชื่อมต่อ MetaAPI (อ่านอย่างเดียว)
│   └── metaapi_engine_smoke.py       พิสูจน์ว่าเครื่องยนต์อ่านแท่งจริงผ่านสะพานได้
└── QC/                          ← ผลตรวจคุณภาพ 2 รอบก่อนส่งมอบ
```

### การไหลของข้อมูล (Data flow)

```
market_clock ─► strategy_engine (12 คะแนน) ─► auto_threshold (แถบ/เกณฑ์)
      │                                              │
      └─► market_analyzer ───────────────────────────┤
                                                     ▼
        side_net (ด่านฝั่ง) ─► trade_guard (กรอบกันพลาด) ─► live_executor
                                                     │
        ┌────────────────────────────────────────────┘
        ▼
   ประตู 3 ด่าน:  ด่าน 1 ตรวจก่อนเปิด · ด่าน 2 จัดการไม้ที่เปิดอยู่ · ด่าน 3 ปิด/ยืนยัน
        │
        ▼
   audit (ตรวจย้อนได้) · โรงงานสำรอง (คืนค่าได้) · kill switch (หยุดทันที)

   "สมอง" AI (โหมด 2):  brief_mode2.md / brief_admin.md
        └─► อ่าน packet ─► คิด ─► submit_recommendation.py / admin_command.py
                                      └─► ประตูทดสอบ (Testing Gate) ─► apply

   MetaAPI:  metaapi_mt5_shim  (เลียนแบบ MetaTrader5 — ระบบเทรดไม่ต้องแก้โค้ด)
```

---

## 2) ตารางค่าโรงงานของตัวแปรเริ่มต้น (Factory values of initial variables)

ค่าด้านล่างคือ **ค่าโรงงาน** ที่ปักหมุดไว้ที่ `trading-system/work/factory/config/auto_config.factory.json`
และคืนค่าได้ทุกเมื่อด้วย `restore_factory.py`

> **หมายเหตุสำคัญของแพ็กนี้:** ไฟล์ค่าที่แถมมาในแพ็กถูกตั้ง `live_enabled` เป็น `false`
> และวางไฟล์หยุด (`AUTO_TRADER_STOP`) ไว้ เพื่อให้ผู้รับเริ่มจากสภาวะปลอดภัย
> ส่วน **ค่าโรงงานจริงของผู้สร้างคือ `live_enabled = true`** (บันทึกไว้ตามจริงด้านล่าง)
> ผู้รับต้องเป็นผู้เปิดใช้งานเองบนบัญชีของตัวเอง

| ตัวแปร | ค่าโรงงาน | ชนิด |
|---|---|---|
| `live_enabled` | true | ค่าเดี่ยว |
| `symbol` | "XAUUSD.sml" | ค่าเดี่ยว |
| `volume` | 0.001 | ค่าเดี่ยว |
| `max_risk_pct` | 8.0 | ค่าเดี่ยว |
| `daily_loss_limit_pct` | 20.0 | ค่าเดี่ยว |
| `max_consecutive_losses` | 0 | ค่าเดี่ยว |
| `min_reward_risk` | 1.3 | ค่าเดี่ยว |
| `enforce_equal_tp_sl` | false | ค่าเดี่ยว |
| `atr_stop_multiplier` | 1.2 | ค่าเดี่ยว |
| `trigger_timeframe` | "M1" | ค่าเดี่ยว |
| `m1_trigger` | buy_rsi_min=42.0; buy_rsi_max=68.0; sell_rsi_min=32.0; sell_rsi_max=58.0; min_close_location=0.55 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `legacy_trend` | required_votes=2; require_h1_alignment=false; buy_rsi_min=40.0; buy_rsi_max=70.0; sell_rsi_min=30.0; sell_rsi_max=60.0 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `strategy_router` | enabled=true; mode="technical_only"; trade_enabled={"trend": true, "range": true, "mean_reversion": true, "breakout": true, "counter_trend": true, "breakout_reversal": true}; agent_score_threshold=0.42; agent_score_thresholds={"trend": 0.55, "range": 0.3, "mean_reversion": 0.25, "breakout": 0.7, "counter_trend": 0.35, "breakout_reversal": 0.6}; adaptive={"enabled": false, "min_samples": 12, "disable_profit_factor": 0.85, "enable_profit_factor": 1.05, "max_disabled": 2, "reenable_hours": 12.0, "chart_bootstrap": true, "chart_bars": 3000, "shadow_enabled": false, "shadow_min_score": 0.2, "shadow_max_hold_bars": 60, "shadow_history_limit": 400, "decay_half_life": 40, "probability_min_samples": 8, "relation_signal_floor": 0.2}; bounded_live={"enabled": true, "owner_approved": true, "structural_mode": "diagnostic_only", "governance": {"trend": {"raw": 0.471, "probability": 0.58, "weighted": 0.471, "raw_max": 0.53, "probability_max": 0.85, "weighted_max": 0.53, "raw_buy": 0.422, "raw_max_buy": 0.522, "weighted_buy": 0.422, "weighted_max_buy": 0.522, "raw_sell": 0.43, "raw_max_sell": 0.53, "weighted_sell": 0.43, "weighted_max_sell": 0.53, "probability_sell": 0.58, "probability_max_sell": 0.85, "probability_buy": 0.58, "probability_max_buy": 0.85}, "range": {"raw": 0.238, "probability": 0.53, "weighted": 0.238, "raw_max": 0.332, "probability_max": 0.75, "weighted_max": 0.332, "raw_buy": 0.43, "raw_max_buy": 0.53, "weighted_buy": 0.43, "weighted_max_buy": 0.53, "raw_sell": 0.439, "raw_max_sell": 0.539, "weighted_sell": 0.439, "weighted_max_sell": 0.539, "probability_buy": 0.53, "probability_max_buy": 0.75, "probability_sell": 0.53, "probability_max_sell": 0.75}, "mean_reversion": {"raw": 0.12, "probability": 0.56, "weighted": 0.12, "raw_max": 0.212, "probability_max": 0.75, "weighted_max": 0.212, "raw_buy": 0.43, "raw_max_buy": 0.53, "weighted_buy": 0.43, "weighted_max_buy": 0.53, "raw_sell": 0.43, "raw_max_sell": 0.53, "weighted_sell": 0.43, "weighted_max_sell": 0.53, "probability_buy": 0.56, "probability_max_buy": 0.75, "probability_sell": 0.56, "probability_max_sell": 0.75}, "counter_trend": {"raw": 0.35, "probability": 0.58, "weighted": 0.38, "raw_max": 0.58, "probability_max": 0.78, "weighted_max": 0.6, "raw_buy": 0.43, "raw_max_buy": 0.53, "weighted_buy": 0.43, "weighted_max_buy": 0.53, "probability_buy": 0.58, "probability_max_buy": 0.78, "raw_sell": 0.43, "raw_max_sell": 0.53, "weighted_sell": 0.43, "weighted_max_sell": 0.53, "probability_sell": 0.58, "probability_max_sell": 0.78}, "breakout": {"raw": 0.7, "probability": 0.6, "weighted": 0.72, "raw_max": 0.95, "probability_max": 0.88, "weighted_max": 0.95, "raw_buy": 0.44, "raw_max_buy": 0.54, "weighted_buy": 0.44, "weighted_max_buy": 0.54, "raw_sell": 0.44, "raw_max_sell": 0.54, "weighted_sell": 0.44, "weighted_max_sell": 0.54, "probability_buy": 0.6, "probability_max_buy": 0.88, "probability_sell": 0.6, "probability_max_sell": 0.88}, "breakout_reversal": {"raw": 0.6, "probability": 0.6, "weighted": 0.63, "raw_max": 0.9, "probability_max": 0.85, "weighted_max": 0.9, "raw_buy": 0.43, "raw_max_buy": 0.53, "weighted_buy": 0.43, "weighted_max_buy": 0.53, "probability_buy": 0.6, "probability_max_buy": 0.85, "raw_sell": 0.43, "raw_max_sell": 0.53, "weighted_sell": 0.43, "weighted_max_sell": 0.53, "probability_sell": 0.6, "probability_max_sell": 0.85}}, "counter_direction": {"enabled": true, "margin": 0.05, "note": "ไม้สวนแนวโน้ม H1 ต้องมี raw/prob/weighted สูงกว่าปกติ 0.05 · ยกพื้นไม่เกิน 80% ของความกว้าง band → ไม่มีทางประตูตัน"}, "stage3": {"allow_net_deferred": true, "note": "ด่าน 3: ตัวเลือกสำรองคิดจาก 36 ค่า (ไม่ต้องผ่านประตู net) — เจ้าของระบบ 15 ก.ย. 2026"}}; trend_adx_min=22.0 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `max_spread` | 0.6 | ค่าเดี่ยว |
| `deviation_points` | 50 | ค่าเดี่ยว |
| `cooldown_minutes` | 0 | ค่าเดี่ยว |
| `poll_seconds` | 60 | ค่าเดี่ยว |
| `position_monitor_seconds` | 60 | ค่าเดี่ยว |
| `profit_exit` | enabled=true; minimum_profit_usd=0.0; no_signal_tp_fraction=0.8; note="ปิดกำไรเมื่อไม่มีสัญญาณทางเดียวกันที่ 80% ของระยะ TP (เจ้าของระบบกำหนด 15 ก.ย. 2026)" | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `openrouter` | enabled=false; api_key_env="OPENROUTER_API_KEY"; api_key_file="work/openrouter_api_key.machine.dpapi"; timeout_seconds=30; max_attempts=1; retry_delay_seconds=1.0; cache_seconds=90; judge_min_confidence=0.55 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `bounded_adaptive_research` | enabled=true; mode="shadow_only"; apply_to_live=false; required_safe_er=0.1; max_conflict=0.7; min_pressure_margin=0.05 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `reconnect_seconds` | 10 | ค่าเดี่ยว |
| `magic` | 8252026 | ค่าเดี่ยว |
| `side_net_gate` | enabled=true; lookback_trades=3; threshold=0.0; min_samples=2; note="ด่านเน็ตดูเฉพาะไม้ที่ปิดภายใน 12 ชม. (ประเมินจากข้อมูลจริง 19 ก.ย. 2026)"; max_age_hours=12 | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `_creator` | name="Kanutsanan Pongpanna"; facebook="https://www.facebook.com/LoveMoneyTH"; youtube="https://youtube.com/@lovemoneythofficial"; note="ผู้สร้างระบบ — โปรดเก็บเครดิตไว้ในทุกส่วนของระบบ" | กลุ่มค่า (เครดิตผู้สร้าง — ห้ามลบ) |
| `stage3` | enabled=true; mode="two_sides_compare"; compare="probability_and_weighted_score"; min_history=2; require_positive_net=true; on_unqualified_opposite="abstain"; note="ด่าน 3 (เจ้าของระบบ): เทียบสองฝั่งของกลยุทธ์ที่ผ่านด่าน 1+2 · ฝั่งตรงข้ามน่าสนใจกว่า+ผ่านเงื่อนไข = พลิกเทรด · ไม่ผ่าน = ไม่เทรด" | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `revenge_guard` | enabled=true; cooldown_minutes=15; score_margin=0.05; note="กันการแก้แค้น: ไม้ขาดทุนฝั่งไหน ห้ามเข้าซ้ำภายใน 15 นาที เว้นแต่คะแนนแรงกว่าเดิม +0.05" | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `early_cut` | enabled=true; only_losing=true; note="ตัดขาดทุนทันทีเมื่อไม้เดิมขาดทุน + สัญญาณใหม่สวนทาง (ผลจำลอง +2.39 ต่อ 6 วัน)" | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |
| `admin_bot` | enabled=true; interval_minutes=30; mode="apply"; note="บอท AI ดูแลทุก 30 นาที (เจ้าของระบบกำหนด 19 ก.ย. 2026) — ปรับค่าต่างๆ และโครงสร้างในกรอบปลอดภัย + rollback อัตโนมัติ"; bounds_note="กรอบความปลอดภัยอยู่ใน tools/admin_bot_round.py (BOUNDS)" | กลุ่มค่า (ปรับได้ทั้งกลุ่ม) |

**ตัวปรับค่าได้เอง (ทั้งชุด):** ค่าทั้ง 29 คีย์ข้างบนปรับได้ทั้งหมดผ่าน
`tools/admin_command.py` (ในกรอบ `BOUNDS`) หรือแก้ไฟล์โดยตรง — และคืนค่าโรงงานได้เสมอ

---

## 3) โหมดการเทรด 2 โหมด

| โหมด | คีย์ | ทำงานอะไร | ค่าเริ่มต้น |
|---|---|---|---|
| **1 · เทรดด้วยสัญญาณภายใน** | `internal_only` | สคริปต์ Python ล้วน + งานวิจัยภายใน + ตัวปรับ + บันทึกประวัติครบ | — |
| **2 · เทรดร่วมสัญญาณ AI** | `internal_llm_join` | เหมือนโหมด 1 ทุกส่วน **เพิ่ม** บอทเช็คสัญญาณโหมด 2 และ Admin Bot | ✅ **ค่าเริ่มต้น** |

- ใช้ชื่อ/ค่าเริ่มต้นจาก `runtime_support.MODE_TITLES` / `DEFAULT_MODE` — อย่าเดา
- งานวิจัยภายในและตัวปรับทำงาน **ทั้งสองโหมด** — โหมด 1 ตัดเฉพาะบอท AI ไม่ได้ตัดงานวิจัย
- โหมด 1 จะปฏิเสธคำแนะนำจาก AI Agent Bot เสมอ
- การเปลี่ยนโหมดไม่ให้สิทธิ์ส่งออเดอร์เพิ่ม และไม่ยกเลิก kill switch

---

## 4) ความปลอดภัยและความซื่อสัตย์

- **ห้ามสัญญากำไร** — ผลทดสอบย้อนหลังคือหลักฐาน ไม่ใช่หลักประกัน
- **ข้อมูลไม่ครบ = ไม่รู้ (unknown)** ไม่ใช่ 0 ไม้ — `positions_get` คืน `None` เมื่อ query ล้มเหลว
- **ปิดไม่ยืนยัน ห้ามเปิดใหม่** และ **ห้าม retry คำสั่งที่สถานะกำกวม**
- ใช้แท่งที่ปิดแล้วเท่านั้น · เคารพ `magic`/เจ้าของ symbol
- คำแนะนำต้องผ่าน **ประตูทดสอบ** ก่อนถูกนำไปใช้
- **kill switch สำคัญที่สุด** — ห้ามลบ ห้ามข้าม
- แอดมินบอทแตะได้แค่ "ค่าตัวเลขในกรอบ" เท่านั้น — ห้ามแตะ `live_enabled`, `magic`, `volume`, `symbol` และห้ามแก้โครงสร้างโค้ด
- **สะพาน MetaAPI เป็นชั้นรับความรู้สึก ไม่ใช่สมอง** — ห้าม deploy/undeploy บัญชีเอง และโหมดอ่านอย่างเดียวต้องปฏิเสธ `order_send` ทุกครั้ง
- แพ็กนี้ไม่มีคีย์ส่วนตัว — ให้เก็บคีย์ของ **คุณ** ไว้ใน environment เท่านั้น

---

## 5) เริ่มใช้งาน

```bash
python3 scripts/verify_package.py           # 1) ตรวจความสมบูรณ์ + ไม่มีความลับ
#                                          2) ติดตั้งสำเนาทำงาน (ดู SKILL.md หัวข้อ 2)
export METAAPI_TOKEN="..."                  # โทเคนของคุณ (เก็บใน env เท่านั้น)
export METAAPI_ACCOUNT_ID="..."             # UUID บัญชี MetaAPI (ไม่ใช่เลข login โบรกเกอร์)
python3 scripts/metaapi_connect_check.py    # 3) ตรวจว่าถึงบัญชีของคุณจริง (อ่านอย่างเดียว)
python3 scripts/metaapi_engine_smoke.py     # 4) พิสูจน์ว่าเครื่องยนต์อ่านแท่งจริงได้
```

จากนั้นอ่าน [references/operations.md](references/operations.md) ก่อนเปิดใช้งานจริงเสมอ

---

## 6) ความเข้ากันได้ (Portability)

| สภาพแวดล้อม | เส้นทาง | สถานะ |
|---|---|---|
| ไม่มีเทอร์มินัล MT5 (ลินุกซ์/คลาวด์/คอนเทนเนอร์/เครื่องคนอื่น) | `metaapi/` (สะพาน MetaAPI) | ✅ ทดสอบเชื่อมต่อจริง อ่านอย่างเดียว 21 ก.ย. 2026 |
| Windows + MT5 terminal | `import MetaTrader5` ตามปกติ | ✅ ทางที่ทดสอบกับระบบเดิมครบ 68 เทสต์ |
| OpenClaw · Hermes · Manus · clawhub.ai | อ่าน `SKILL.md` + `agents/registry.json` | ✅ |

ข้อจำกัดจริงที่บันทึกไว้ตามตรง (ดู [references/portability.md](references/portability.md)):
เวลาจากเซิร์ฟเวอร์ MetaAPI ต่างจาก UTC ตามเขตเวลาโบรกเกอร์ (ตัวอย่างที่ทดสอบ = +10800 วินาที)
· อัตรามาร์จินของ MetaAPI ต่างจาก MT5 (ปรับได้ด้วย `METAAPI_SHIM_MARGIN_RATE`)
· ไม่มี Market Watch · `order_check` ถูกจำลอง · ไม่มี deploy/undeploy
· MetaAPI **ต้องมีบัญชี + โทเคนของคุณเอง** — แพ็กนี้ไม่แถมและไม่ฝัง credential ของผู้ใด
· ค่าใช้จ่าย MetaAPI/โบรกเกอร์/VPS/ข้อมูล เป็นความรับผิดชอบของผู้ใช้เอง

---

## 7) งานวิจัย — ทำต่อยอดได้

คลังงานวิจัยทั้งหมดอยู่ใน `trading-system/research/` เริ่มที่
[`research/README.md`](trading-system/research/README.md) และ
[`research/SESSION-STATE.md`](trading-system/research/SESSION-STATE.md)
อ่านวิธีทำวิจัยต่อใน [references/research.md](references/research.md)

> หมายเหตุความเป็นส่วนตัว: ในไฟล์งานวิจัยบางไฟล์ เลขบัญชีโบรกเกอร์ถูก **มาสก์**
> (`****798`) และ path เครื่องของผู้สร้างถูกแทนด้วย MACHINE-PLACEHOLDER แล้ว

---

## 8) การเผยแพร่ขึ้น clawhub.ai

`.clawhubignore` ถูกปรับให้ **ค่าโรงงานและไฟล์หยุดถูกเผยแพร่** แต่ credential และสถานะสดไม่ขึ้น

```bash
clawhub skill publish ./Pytron-Engine-MT5-Algo-Trade-For-OpenClaw --slug pytron-engine-mt5-algo-trade --version 1.0.0
```

> **ข้อควรระวังที่บันทึกไว้:** กฎ `work/` ลอย ๆ จะลบ `trading-system/work/factory/`
> และ `trading-system/work/AUTO_TRADER_STOP` จนสกิลที่เผยแพร่พัง — และ glob แบบ
> `work/*.json` คร่อมเครื่องหมาย `/` ได้ จึงต้องระบุชื่อไฟล์สถานะตรง ๆ

---

## 8) การตรวจสอบก่อนส่งมอบ (QC evidence)

แพ็กนี้ผ่านการตรวจ 2 รอบ ด้วยวิธีที่ต่างกัน และเก็บหลักฐานไว้ให้ตรวจซ้ำได้:

| รอบ | วิธี | ผล |
|---|---|---|
| รอบ 1 | สคริปต์ตรวจของเจ้าของระบบ (21 หัวข้อ: โครงสร้าง · ความลับ · เทสต์ · ค่าโรงงาน · frontmatter ของ clawhub · `.clawhubignore` · สคริปต์ MetaAPI) | 21/21 ผ่าน |
| รอบ 2 | วิธีอิสระจากรอบ 1 (ย้ายไปพาธอักษรไทย · คำนวณ sha256 เอง · เทียบ EOL/BOM กับต้นฉบับ · ห่วงโซ่แฮชหลักฐาน · สร้าง ZIP จริงแล้วทดสอบจาก ZIP) | 19/19 ผ่าน |

หลักฐานอยู่ในโฟลเดอร์ `QC/`:

- `qc-round1.json` · `qc-round1-script.py` — ผลและสคริปต์รอบ 1
- `qc-round2.json` · `qc-round2-script.py` — ผลและสคริปต์รอบ 2
- `verify-install.py` — **สคริปต์ตรวจที่คุณรันเองได้** (ใช้เฉพาะ stdlib ไม่ต้องติดตั้งอะไร)

```bash
python QC/verify-install.py          # ตรวจอย่างเร็ว
python QC/verify-install.py --full   # เทียบ sha256 ทุกไฟล์กับ file-manifest.json
```

## 9) ความสมบูรณ์ของหลักฐานย้อนหลัง

- `file-manifest.json` เก็บ sha256 ของทุกไฟล์ในแพ็ก (ยกเว้นตัวมันเอง) — ใช้ `--full` ตรวจได้
- ห่วงโซ่แฮชหลักฐานใน `research/recommendations/evaluations/` ตรวจซ้ำแล้ว **ok=300 broken=0**
- คู่ `work/factory/code/` กับโค้ดจริง **ไม่ตรง 12 คู่** — เป็นสภาพจริงของระบบตั้งแต่ต้น ไม่ใช่ความเสียหายจากแพ็กนี้
- การทดสอบ MetaAPI 21 ก.ย. 2026 เป็นแบบ **อ่านอย่างเดียว** (`order_send` ถูกบล็อก retcode 10017)
  หลักฐานอยู่ใน `metaapi/evidence/` — เลขบัญชีโบรกเกอร์ถูกมาสก์

## Credit note and hash-sealed evidence

- `trading-system/research/CREDIT-NOTE.md` explains where the seven-line banner and
  creator credit live in every file type, why `auto_config.json` keeps exactly 29 keys,
  why `SKILL.md` must start with its `---` frontmatter, and why the 328 hash-sealed
  evidence files under `research/recommendations/` are shipped byte-for-byte unchanged.
- Editing a sealed file breaks the verification chain the consumer re-checks on every
  proposal, so treat those files as read-only history.

## เครดิตและสัญญาอนุญาต

ระบบนี้สร้างโดย **คณัสนันท์ พงษ์พันนา (Kanutsanan Pongpanna)** — โปรดเก็บเครดิตไว้ในทุกไฟล์
ดู [LICENSE](LICENSE) และ [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)
