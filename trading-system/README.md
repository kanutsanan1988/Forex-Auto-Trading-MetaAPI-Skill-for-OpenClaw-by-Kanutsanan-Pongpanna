<!-- Python Qaunt Trading + AI(LLM) Live Research | Creator: Kanutsanan Pongpanna | Settrade e-Open Account · MTS Gold Futures + MT5 | https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com -->

# Python Qaunt Trading + AI(LLM) Live Research

**อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา**  
Creator: **Kanutsanan Pongpanna** · [Facebook](https://www.facebook.com/LoveMoneyTH) · [YouTube](https://youtube.com/@LoveMoneyTHOfficial)  
Project identity: **Settrade e-Open Account · MTS Gold Futures + MT5** · [Settrade e-Open Account](https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com)

> “เทรดในไทยมีกฎหมายรองรับ 100%” เป็นข้อความนิยามผลิตภัณฑ์ที่เจ้าของเสนอ ไม่ใช่การตรวจรับรองทางกฎหมายหรือการกำกับดูแลโดยอิสระ และไม่ทำให้ XAUUSD.sml/MT5 เท่ากับสัญญา TFEX โดยอัตโนมัติ
>
> **สไตล์การเทรดเป็นของแต่ละคน:** ระบบเปิดให้ผู้ใช้อธิบาย ปรับแต่ง และพัฒนาส่วนที่เป็นโค้ดของโครงการให้ตรงกับความชอบของตนเองได้เต็มที่ โดยให้ AI ที่ผู้ใช้เลือกเรียนรู้โครงสร้างและช่วยอธิบายได้ ต้องรักษาเครดิตผู้สร้างและปฏิบัติตาม license ของไลบรารี/บริการภายนอก

## ขอบเขตและค่าเริ่มต้นความปลอดภัยของชุดแจกจ่าย

- แพ็กเกจนี้สร้างจาก source tree วันที่ **2026-09-30**: ระบบ Python/MT5, agents, docs, factory snapshot และ research archive ครบตามรายการที่รวมใน ZIP
- **ชุดแจกจ่ายเริ่มหยุดอยู่:** `work/AUTO_TRADER_STOP` มีอยู่ และ `live_enabled=false` ใน runtime และไฟล์ factory สำหรับการ restore
- โหมดเริ่มต้น `internal_llm_join` — **เทรดร่วมสัญญาณ AI** อนุญาตเฉพาะ AI integrations ที่ผู้ใช้ตั้งค่าและเปิดเอง; ไม่เปิด Live และไม่ลบ STOP
- OpenRouter, Jev และ OpenRouter credit guard ปิดไว้ในชุดแจกจ่ายจนกว่าผู้ใช้จะตั้งค่า credential/provider เอง; ไม่มี `.env`, DPAPI หรือ token รวมอยู่
- Python เป็นตัวคำนวณและควบคุมเส้นทางเทรด; Agent ไม่ได้สิทธิ์ส่งออเดอร์/เปิด Live/ลบ STOP ด้วยการเลือกโหมด
- ค่าความเสี่ยงใน factory เป็นภาพบันทึกจากระบบต้นทาง ไม่ใช่คำแนะนำและไม่รับประกันกำไรรายวัน

## สองโหมดและบทบาท Agent

| โหมด | ความหมาย |
|---|---|
| `internal_only` — **เทรดด้วยสัญญาณภายใน** | Python trading และงานวิจัยภายในทำงาน; AI/LLM callsites ที่เชื่อมกับระบบถูกกันตาม mode gate |
| `internal_llm_join` — **เทรดร่วมสัญญาณ AI** (ค่าเริ่มต้น) | ใช้ Python เหมือนเดิมและอนุญาตให้ AI integrations ทั้งหมดที่ผู้ใช้เปิดไว้มีส่วนร่วม ไม่ได้จำกัดแค่บอทโหมด 2 กับ Admin Bot |

Agent หลักของแพลตฟอร์มผู้ใช้รับบทบาทผู้ประสานงาน **“Hermes”** และสามารถรับ brief ของบอทโหมด 2 หรือ Admin Bot ได้ด้วย ไม่จำเป็นต้องใช้ผลิตภัณฑ์ Hermes หรือสร้าง Agent แยกสามตัว ระบบไม่ได้ติดตั้ง scheduler/CLI ของแพลตฟอร์มอื่นให้อัตโนมัติ

Jev เป็นส่วนเสริม: OpenRouter เป็นเพียงตัวอย่าง adapter; จะใช้วิธีอื่นหรือไม่ใช้ Jev ก็ได้ การไม่มี Jev ต้องไม่สร้างสัญญาณซื้อขายเทียมหรือหยุด Python engine

## โครงสร้างการทำงาน

```text
MT5 quotes / bars
  → market clock + market analyzer
  → Python strategy_engine: 6 Agents × Buy/Sell = 12 candidates
  → raw score + Probability + weighted score + bounded governance / side-net / Stage 3
  → ตรวจและจัดการ Position เดิมก่อนพิจารณา Position ใหม่
  → ปิดแล้วรอ MT5 ยืนยันสถานะ
  → risk / permission / request checks
  → Live-disabled + Kill Switch ในชุดนี้จึงไม่เปิดคำสั่งจริง
  → audit, research, adaptive threshold และบทเรียนสำหรับรอบถัดไป
```

มี 3 ชั้นหลัก: (1) Python trading (`auto_trader.py`, `strategy_engine.py`, `market_clock.py`, `live_executor.py`, `trade_guard.py`), (2) Python research/measurement/threshold tuning และ audit, (3) AI roles ที่ถูกเรียกผ่าน briefs และ REC/Admin interfaces ตามโหมดและสวิตช์รายบริการ

ระบบปัจจุบันมี 8 งานตาม factory schedule snapshot:

| Job | Schedule | Source snapshot |
|---|---|---|
| `llm-recommendation-consumer` | every 5m | True |
| `trading-analytics` | every 10m | True |
| `trading-daily-research-log` | every day at 23:50 | True |
| `trading-research-bot (10 นาที · บอทดูแล LLM)` | every 10m | True |
| `trading-admin-bot (30 นาที)` | every 30m | True |
| `brain-consult` | every 60m | True |
| `brain-consult-alert` | every 60m | True |
| `credit-guard-openrouter` | every 60m | True |
| `question-board-scanner` | every 10m | True |
| `human-behavior-research` | every 60m | True |

กำหนดการใน snapshot เป็นเจตนาการตั้งงานของเครื่องต้นทาง; ต้องติดตั้ง/แปลง adapter scheduler ให้เหมาะกับแพลตฟอร์มปลายทาง ไม่ได้ถ่ายโอน task ที่รันอยู่ให้โดยอัตโนมัติ

## Factory baseline จาก source snapshot (2026-09-30)

ค่าต่อไปนี้อ่านจาก `work/factory/config/auto_config.factory.json` และ configuration ที่เกี่ยวข้อง ส่วนไฟล์นั้นในแพ็กเกจถูกตั้งค่า safety overlay แล้ว; รายละเอียดเต็มทุกคีย์อยู่ใน JSON ที่แนบมา:

- Factory capture time: `2026-09-30`; see `work/factory/FACTORY_INFO.json` and full safe copy `work/factory/config/auto_config.factory.json`.
- `live_enabled`: source `True` → release **`false`**; `work/AUTO_TRADER_STOP` is present.
- `symbol` `XAUUSD.sml` · `volume` `0.001` · `magic` `8252026`.
- `poll_seconds` / `position_monitor_seconds`: `60` / `60`; cycle interval in seconds.
- `max_risk_pct` `8.0` · `daily_loss_limit_pct` `20.0` · `max_consecutive_losses` `0`.
- `min_reward_risk` `1.2` · `atr_stop_multiplier` `1.5` · `max_spread` `0.6` · `cooldown_minutes` `5`.
- `enforce_equal_tp_sl`: `False` · `profit_exit`: `{"enabled":true,"minimum_profit_usd":0.0,"no_signal_tp_fraction":0.8,"note":"ปิดกำไรเมื่อไม่มีสัญญาณทางเดียวกันที่ 80% ของระยะ TP (เจ้าของระบบกำหนด 15 ก.ย. 2026)"}`.
- Bounded governance: enabled `True`; source `owner_approved` `True` → release `false`; structural mode `diagnostic_only`.
- `agent_score_thresholds` (fallback when bounded-live is off): `{"trend":0.55,"range":0.3,"mean_reversion":0.25,"breakout":0.7,"counter_trend":0.35,"breakout_reversal":0.6}`.
- `strategy_weights`: `{"trend":0.85,"range":1.2,"mean_reversion":0.85,"counter_trend":0.95,"breakout":1.1,"breakout_reversal":1.0}`; `ranking_priority`: `weight`.
- `directional_probabilities`: `{"trend_buy":0.58,"trend_sell":0.58,"range_buy":0.53,"range_sell":0.53,"mean_reversion_buy":0.56,"mean_reversion_sell":0.56,"counter_trend_buy":0.58,"counter_trend_sell":0.58,"breakout_buy":0.6,"breakout_sell":0.6,"breakout_reversal_buy":0.6,"breakout_reversal_sell":0.6}`; full side-specific gates are below. Scores/probabilities are system metrics, not automatically calibrated real-world probabilities.
- `auto_threshold`: enabled `True`, mode `hybrid`, window `180` rounds, percentiles `60/90`, minimum samples `30`, minimum apply change `0.02`.
- `side_net_gate`: `{"enabled":true,"lookback_trades":3,"threshold":0.0,"min_samples":2,"note":"ด่านเน็ตดูเฉพาะไม้ที่ปิดภายใน 12 ชม. (ประเมินจากข้อมูลจริง 19 ก.ย. 2026)","max_age_hours":12}`.
- `early_cut`: `{"enabled":true,"only_losing":true,"note":"ตัดขาดทุนทันทีเมื่อไม้เดิมขาดทุน + ฝั่งตรงข้าม (สัญญาณเต็มรูป หรือ 'ทิศเอนของตลาด' จาก regime_scores/ผู้สมัครสัญญาณ) — ตัดได้ทุกระยะ ไม่จำกัดระยะถึง SL (เจ้าของระบบกำหนด 30 ก.ย. 2026) · ผลจำลองเดิม 6 วัน +2.39","use_lean":true,"lean_min_margin":0.1}`; `revenge_guard`: `{"enabled":true,"cooldown_minutes":15,"score_margin":0.05,"note":"กันการแก้แค้น: ไม้ขาดทุนฝั่งไหน ห้ามเข้าซ้ำภายใน 15 นาที เว้นแต่คะแนนแรงกว่าเดิม +0.05"}`.
- `stage3`: `{"enabled":true,"mode":"two_sides_compare","compare":"probability_and_weighted_score","min_history":2,"require_positive_net":true,"on_unqualified_opposite":"abstain","note":"ด่าน 3 (เจ้าของระบบ): เทียบสองฝั่งของกลยุทธ์ที่ผ่านด่าน 1+2 · ฝั่งตรงข้ามน่าสนใจกว่า+ผ่านเงื่อนไข = พลิกเทรด · ไม่ผ่าน = ไม่เทรด"}`.
- OpenRouter source enabled `False` → release disabled. Jev source factory is optional → disabled until configured. `credit_guard` source enabled `True` → release disabled until the user configures their own provider credentials; thresholds `1.0` / `1.2` USD; monitor job is in the schedule table.
- Current source research copied: **618 files**. The full archive is in `research/`.

### 36 ค่า governance แยกทิศทาง

ช่วง `[min, max]` ด้านล่างคือ raw-score / probability / weighted-score gates ตาม factory config ต่อ Buy/Sell ของแต่ละ Agent; auto-threshold อาจปรับค่าภายในกติกาเมื่อระบบทำงาน ข้อมูล Probability ยังไม่ถือว่าผ่าน calibration ทางสถิติหากไม่ได้ทดสอบแยก

| Agent direction | Raw score | Probability | Weighted score |
|---|---:|---:|---:|
| Trend Buy | `[0.486, 0.586]` | `[0.580, 0.850]` | `[0.416, 0.516]` |
| Trend Sell | `[0.403, 0.503]` | `[0.580, 0.850]` | `[0.325, 0.425]` |
| Range Buy | `[0.174, 0.389]` | `[0.530, 0.750]` | `[0.200, 0.444]` |
| Range Sell | `[0.374, 0.651]` | `[0.530, 0.750]` | `[0.430, 0.758]` |
| Mean Reversion Buy | `[0.149, 0.372]` | `[0.560, 0.750]` | `[0.119, 0.316]` |
| Mean Reversion Sell | `[0.302, 0.468]` | `[0.560, 0.750]` | `[0.257, 0.414]` |
| Counter Trend Buy | `[0.346, 0.457]` | `[0.580, 0.780]` | `[0.322, 0.434]` |
| Counter Trend Sell | `[0.511, 0.636]` | `[0.580, 0.780]` | `[0.485, 0.604]` |
| Breakout Buy | `[0.440, 0.540]` | `[0.600, 0.880]` | `[0.440, 0.540]` |
| Breakout Sell | `[0.440, 0.540]` | `[0.600, 0.880]` | `[0.440, 0.540]` |
| Breakout Reversal Buy | `[0.430, 0.530]` | `[0.600, 0.850]` | `[0.430, 0.530]` |
| Breakout Reversal Sell | `[0.430, 0.530]` | `[0.600, 0.850]` | `[0.430, 0.530]` |

> หมายเหตุ: `agent_score_thresholds` เป็น fallback เมื่อ bounded-live gate ไม่ทำงาน; ใน snapshot นี้ `bounded_live.enabled=true` จึงควรอ่าน 36 side-specific values ข้างบนร่วมกับโค้ด `strategy_engine.py` ไม่ควรสับสน threshold fallback กับเกณฑ์ runtime ทุกกรณี

## งานวิจัยและข้อจำกัด

โฟลเดอร์ `research/` บรรจุ **618 ไฟล์จาก source snapshot ล่าสุด** ทั้งบันทึกวิจัย ประวัติผล/ข้อเสนอ และข้อมูลประกอบระบบที่เก็บไว้ ผู้สร้างขอให้รวมประวัติไว้ด้วย; package pass จะตัด secret, machine paths, credential/account IDs และ runtime state ที่ไม่จำเป็น แต่คงข้อมูลวิจัยที่เหลือ ตรวจสิทธิ์แหล่งข่าวและความเป็นส่วนตัวก่อนเผยแพร่ต่อสาธารณะ

รายงาน review ใน `docs/ARCHIVED-SYSTEM-REVIEW-2026-09-24.md` เป็นหลักฐานการตรวจวันที่ระบุ ไม่ใช่การ audit อิสระของโค้ดที่เปลี่ยนวันที่ 28 ก.ย. 2026; ตรวจ source ปัจจุบันก่อนตัดสินใจเสมอ การเชื่อมต่ออ่านข้อมูล MetaAPI (หากใช้ชุด MetaAPI แยก) ไม่ใช่หลักฐานว่า Live order/position reconciliation ใช้ได้

## License, setup และผู้พัฒนาต่อ

- Source code ของโครงการ: MIT (`LICENSE`); third-party notices แยกต่างหาก
- โครงสร้างหลัก: `outputs/mt5_python_bridge/`, `agents/`, `docs/`, `research/`, `work/factory/`
- อ่าน `SKILL.md` และ `AGENTS.md` ก่อนพัฒนา; ใช้ brief ที่ตรงบทบาทใน `agents/` และรันทดสอบออฟไลน์จากสำเนา
- สร้าง virtual environment แล้วติดตั้ง dependency ตาม `outputs/mt5_python_bridge/requirements.txt`; ตรวจข้อกำหนด MT5/โบรกเกอร์/ไลบรารีและทดลองบน demo ก่อน
- อย่าใส่ secret ใน source, ZIP, research หรือแชต; ชุดนี้ไม่ได้อนุญาตให้เริ่ม Live และไม่รับรองกำไรหรือความถูกต้องทางกฎหมาย
