<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# 2026-09-13 — ปรับ "โครงสร้างการตั้งค่า" จากรอบ 10/5 นาที (36 ค่า + เกณฑ์ TP/SL) + Hot Reload

> งานวิจัยชิ้นนี้เขียนไว้เป็น **จุดเริ่มต้นสำหรับผู้ที่จะนำระบบไปพัฒนาต่อในวิถีของตนเอง**
> อ่านคู่กับ: `2026-09-12-architecture-llm-agnostic.md` (สถาปัตยกรรมรวม) · `2026-09-12-auto-threshold-design.md` (36 ค่า) · `references/structural-tuning-and-hot-reload.md` (คู่มือสกิล)

---

## 0. บทสรุป 1 นาที

| ประเด็น | คำตอบ |
|---|---|
| งานรอบ 10 นาที + 5 นาที ทำอะไรกับระบบ | ปรับ **โครงสร้างการตั้งค่า** = 36 ค่า (band) + เกณฑ์การสร้าง TP/SL |
| แตะออเดอร์ไหม | **ไม่** — ไม่ตั้งค่า order ตรงๆ ไม่เปิด/ปิดออเดอร์ ไม่แตะ live_enabled/magic/volume |
| ต้องรีสตาร์ทระบบไหม | **ไม่ต้อง** — มี **hot reload** ดึงค่าใหม่เข้า config ที่ใช้งานอยู่ทันที |
| มีด่านตรวจไหม | มี — ทุกการเปลี่ยนต้องผ่าน **Testing Gate** (schema → functional → performance/fallback) |
| กันค่ากระชากไหม | มี — **step cap** ต่อรอบ (band ≤0.06 · probability ≤0.01 · TP/SL ≤0.10) + cooldown 10 นาที/คีย์ |
| หลักฐานที่ใช้ตัดสิน | **ข้อมูลจริงจาก audit**: net expectancy, R-multiple (net ÷ risk_usd), percentile ของสกอร์ — **ไม่ใช้ winrate ตัดสิน** |

**ผลทดสอบจริงวันนี้:** แผน 36 ค่า → 6 strategy-side ขยับ · แผน TP/SL จาก **182 ไม้จริง** → 6 รายการ · REC 17 รายการผ่าน Testing Gate → apply จริง · validator ผ่าน · hot reload ทดสอบผ่าน

---

## 1. ปัญหาตั้งต้น (ทำไมต้องมีงานชิ้นนี้)

1. ระบบมี **36 ค่า** (band ของ 6 กลยุทธ์ × 2 ทิศทาง × 3 มิติ) ที่เป็น "ความยืดหยุ่น" ว่าแต่ละกลยุทธ์จะยอมรับสัญญาณแรงแค่ไหน
2. ผู้ใช้ต้องการให้ **งานรอบ 10 นาที และรอบ 5 นาที** มีอิทธิพลต่อค่าเหล่านี้ **อัตโนมัติ** และ **โดยไม่ต้องรีสตาร์ทระบบ**
3. เพิ่มเติม: ต้องมีทักษะ/imvel ปรับ **เกณฑ์การสร้าง TP และ SL** ได้ด้วย (ไม่ใช่แค่ band)
4. ตรวจแล้วพบว่า **ค่า 36 ค่าไม่เคยขยับเลย** ทั้งที่ตัวปรับ `auto_threshold` รันทุก cycle → ต้องหาสาเหตุและแก้ให้ "ขยับได้จริง"

### สาเหตุที่ 36 ค่าไม่ขยับ (root causes — พบ 5 ข้อ)
| # | สาเหตุ | หลักฐาน | วิธีแก้ |
|---|---|---|---|
| 1 | `both_set` บังคับให้มี **per-side keys ครบ** (`raw_buy` + `raw_max_buy`) ไม่งั้น "ไม่ต้องปรับ" | โค้ดเดิม: `both_set = f"raw_{side}" in g and f"raw_max_{side}" in g` | เพิ่ม fallback: ถ้ามี `raw`/`raw_max` กลางก็ปรับได้ |
| 2 | net expectancy ในตัวเครื่องยนต์ว่างเปล่า เพราะ `position_closed.strategy = "unknown"` | audit: `position_closed` มีแค่ ticket/net/consecutive_losses | ป้อน `net_by_key` จากรอบวิจัย (คำนวณด้วย FIFO join) |
| 3 | `_touches` (churn guard) ไม่ถูก persist → หลังรีสตาร์ทตัวนับรีเซ็ต | โค้ด persist เขียนเฉพาะสำเนา config | เขียน `_touches` ลงสำเนาก่อน persist |
| 4 | ไม่มีทางปรับ **probability band** เลย (มีแต่ raw/weighted) | ไม่มีโค้ดเขียน `probability_{side}` | เพิ่มกฎ probability ±0.01 ต่อรอบ (net-first) |
| 5 | หากค่า low/high ไขว้กัน (low > high) ค่าใหม่จะถูก validator ปฏิเสธ | ไม่มี invariant clamp ที่เข้มพอ | เพิ่ม clamp `low ≤ high − 0.02` ทุกเส้นทาง |

---

## 2. หลักคิดสำคัญ (สำหรับผู้นำไปพัฒนาต่อ)

1. **แยก "โครงสร้างการตั้งค่า" ออกจาก "การเทรด"** — งานวิจัยรอบ 10/5 นาที ปรับได้เฉพาะ config ที่ใช้ *สร้าง* ออเดอร์ ไม่แตะออเดอร์ที่เปิดอยู่ และไม่ตั้งค่าออเดอร์ตรงๆ
2. **ทางเดียวที่แตะ config = REC** (`hermes-trading-recommendation-v1`) → ผ่าน Testing Gate → apply → hot reload → **ไม่มีการรีสตาร์ท**
3. **หลักฐานต้องเป็นเงิน ไม่ใช่ winrate** — ใช้ net expectancy และ R-multiple; winrate สูงแต่ R:R แย่ = ขาดทุนได้
4. **ปรับทีละก้าว (step cap) + cooldown + invariant** — ค่อย ๆ เข้าถึงเป้า ไม่กระชากค่าเดียว เพราะระบบเทรดเงินจริง
5. **ทุกการตัดสินใจต้องตรวจย้อนได้** — ทุกการเปลี่ยนเขียน audit + log วิจัย (`band-plan-log.md`, `tpsl-plan-log.md`)

---

## 3. สถาปัตยกรรมท่อ (ภาพรวม)

```
รอบ 10 นาที (cron: trading-research → research_analytics.py)
 ├─ news_research / astrology_step / internal_signal      ← บริบทตลาด + สัญญาณภายใน
 ├─ threshold_analysis                                     ← ตัวเลข 36 ค่า + pass%
 ├─ band_plan.py        → work/plan_band.json   (36 ค่า)   ← ★ ใหม่
 ├─ tpsl_plan.py        → work/plan_tpsl.json   (TP/SL)    ← ★ ใหม่
 ├─ pl_attribution / at_vs_trade / mech_profit / ranking
 └─ profit_anchor_guard                                    ← เฝ้าโซนกำไร (HWM)

รอบ 5 นาที (cron: llm-recommendation-consumer → llm_rec_consumer_runner.py)
 ├─ llm_signal_parser.py     ← คำตอบ LLM [TRADE-SIGNAL] → REC (set_directional_weights)
 ├─ plan_to_rec.py           ← ★ ใหม่: แผน → REC (set_gate / set_probability_gate / set_tpsl)
 │                             + step cap + cooldown + กันแผนเก่า >30 นาที + merge กับ REC ของ LLM
 └─ llm_recommendation_consumer.py
      → llm_recommendation_tester.py  (TESTING GATE: schema → functional → performance/fallback)
      → apply_recommendation()        (เขียน auto_config.json)
      → [trader ที่รันอยู่] hot_reload_config() → มีผลทันที ไม่ต้องรีสตาร์ท
```

---

## 4. "36 ค่า" คืออะไร (นิยามให้ชัด)

ต่อ 1 **strategy-side** (เช่น `trend_buy`) ใช้ 3 มิติ × 2 ขอบ = 6 ค่า

| มิติ | คีย์ใน `strategy_router.bounded_live.governance[strategy]` | ความหมาย | ใช้งานที่ไหน |
|---|---|---|---|
| raw band | `raw_{side}` (low), `raw_max_{side}` (high) | ช่วงคะแนนดิบที่ยอมรับ — ต่ำเกิน/สูงเกิน = ปัดตก (สูงสุดขั้วเสี่ยงกลับตัว) | `strategy_engine.decide_market` gate |
| probability band | `probability_{side}`, `probability_max_{side}` | เกณฑ์ความน่าจะเป็นของทิศทางนั้น | gate เทียบกับ `directional_probabilities[key]` |
| weighted band | `weighted_{side}`, `weighted_max_{side}` | คะแนนถ่วงน้ำหนัก (สเกล 0–1) | จัดอันดับ/เลือกกลยุทธ์ |

รวม 6 กลยุทธ์ × 2 ทิศทาง × 3 มิติ × 2 ขอบ = **72 ช่อง แต่คิดเป็น "36 ค่า" ในความหมายของผู้ใช้** (12 strategy-side × 3 มิติ) — ตัวปรับในเครื่องยนต์เขียน raw และ weighted พร้อมกันเสมอ (`weighted = raw`) เพื่อไม่ให้สเกลแตก

**สูตรคะแนน (สรุป):** `score = Σ (น้ำหนักปัจจัย × ปัจจัย) × directional_weight` แล้วผ่าน gate → ถ้าอยู่นอก band = `no_trade`/`skip` พร้อมเหตุผลใน audit

---

## 5. เกณฑ์การสร้าง TP/SL (โครงสร้าง)

```
stop_distance = ATR14(M5) × {strategy}_stop_atr          (fallback: atr_stop_multiplier)
TP distance   = stop_distance × reward_risk              ({strategy}_reward_risk, fallback min_reward_risk)
```

| คีย์ | ค่าเริ่มต้น | ขอบเขตปลอดภัย (validator) |
|---|---|---|
| `atr_stop_multiplier` (SL โกลบอล) | 1.2 | 0.80 – 2.00 |
| `min_reward_risk` (TP โกลบอล) | 1.7 | 1.20 – 3.00 |
| `{strategy}_stop_atr` (trend/range/mean_reversion/breakout/counter_trend/breakout_reversal) | 1.0–1.25 | 0.60 – 2.50 |
| `{strategy}_reward_risk` | 1.7–1.9 | 1.20 – 3.00 |
| `enforce_equal_tp_sl` | False | bool |

**โค้ดที่แตะ:** `strategy_engine.tpsl_stop_atr()` / `tpsl_reward_risk()` — จุดเรียก 12 แห่ง (trend/range/mean_reversion/breakout/counter_trend/breakout_reversal + router-level + legacy fallback)
> เดิม: เฉพาะ `breakout` เท่านั้นที่มี R:R ของตัวเอง กลยุทธ์อื่นใช้ค่าโกลบอล → จึงปรับ TP ต่อกลยุทธ์ไม่ได้ งานนี้เปิดทางให้ครบทุกกลยุทธ์

---

## 6. กติกาการปรับ (rules + หลักฐาน)

### 6.1 Band (36 ค่า) — `band_plan.py` + `auto_threshold.py`
1. นับสกอร์จริงจาก audit → `p60` (low) และ `p90` (high) ต่อ strategy-side
2. **net-first blend:** คำนวณ net expectancy ต่อ strategy-side (FIFO join `order_result.analysis` ↔ `position_closed.net`)
   - `net/ไม้ < floor` → กรองเข้มขึ้น (low +0.05, high −0.04)
   - `net/ไม้ > เป้า` → ผ่อนรับ (low −0.03)
3. **probability band:** net ติดลบ → `probability_{side}` +0.01 (สูงสุด 0.75) · net ดี → −0.01 (ต่ำสุด 0.50)
4. **step cap:** ปรับได้ไม่เกิน **0.06 ต่อรอบ/ฝั่ง** (`auto_threshold.max_step`) + band-health monitor (relax 0.02 / tighten 0.03)
5. **churn guard:** ไม่แตะคีย์เดิมถี่เกิน (เครื่องยนต์) · cooldown 600 วิ (ท่อ REC)
6. **invariant:** `0.05 ≤ low ≤ high ≤ 1.0` และ `high − low ≥ 0.02`

### 6.2 TP/SL — `tpsl_plan.py`
หลักฐาน: **R-multiple จริง = `net ÷ risk_usd`** (`order_result.analysis.risk_usd` มีบันทึกอยู่แล้ว) ต้องมี n ≥ 8 ต่อกลยุทธ์

| กฎ | เงื่อนไข | การปรับ |
|---|---|---|
| TP ไกลเกิน | ไม้ชนะได้ R < 55% ของเป้า (และชนะ ≥ 3 ครั้ง) | `reward_risk` −0.10 |
| SL ถูกตอด | winrate < 0.40 แต่ชนะได้ R ตามเป้า | `stop_atr` +0.10 |
| SL กว้างเกินจำเป็น | winrate ≥ 0.55 และขาดทุนเฉลี่ย < 0.85R | `stop_atr` −0.05 |
| โกลบอล | ไม้ชนะเฉลี่ยรวม < 55% ของ `min_reward_risk` (n ≥ 20) | `min_reward_risk` −0.10 |

churn guard 30 นาที/คีย์ · เขียน log ที่ `research/tpsl-plan-log.md`

---

## 7. ★ Hot Reload — หัวใจของ "ไม่ต้องรีสตาร์ท"

**ปัญหา:** `strategy_engine.decide_market` อ่านค่า band จาก **dict ในหน่วยความจำ** → ถ้าเขียนไฟล์ config อย่างเดียว **ค่าจะไม่มีผลจนกว่าจะรีสตาร์ท** (นี่คือเหตุผลที่ "apply แล้วแต่ค่าไม่เปลี่ยน" ในอดีต)

**วิธีแก้:** `auto_trader.hot_reload_config(config, tracker)`
- เทียบ `(mtime_ns, size)` ของ `auto_config.json` ทุก cycle ก่อนเรียก `apply_auto_threshold`
- ถ้าไฟล์เปลี่ยน → merge เฉพาะ **ค่าที่ปรับได้**: `governance` (band ทั้งชุด), `trade_enabled`, `strategy_weights`, `directional_weights`, `directional_probabilities`, `ranking_priority`, `{strategy}_stop_atr`, `{strategy}_reward_risk`, `atr_stop_multiplier`, `min_reward_risk`, `enforce_equal_tp_sl`, `max_risk_pct`, `daily_loss_limit_pct`, `max_consecutive_losses`
- **ไม่แตะ** `live_enabled` / `magic` / `volume` (ค่าป้องกัน) — เส้นทาง REC ก็ห้ามแตะเช่นกัน
- เขียน audit event: `config_hot_reload` (สำเร็จ) / `config_hot_reload_error`

REC จากท่อนี้ตั้ง `restart_after_apply: false` เสมอ → **ระบบไม่รีสตาร์ท**

---

## 8. หลักฐานการทดสอบ (ตัวเลขจริง 13 ก.ย. 2026)

| การทดสอบ | ผล |
|---|---|
| แผน 36 ค่า (`band_plan.py`) | **6 strategy-side ควรขยับ** เช่น `trend_buy` raw 0.52→0.46 (net −$1.09, n=1) · `mean_reversion_sell` 0.30→0.24 (net +$0.199, n=19) |
| แผน TP/SL (`tpsl_plan.py`) | **182 ไม้จริง**: breakout ชนะได้ 0.32R (เป้า 2.0R) · trend 0.41R (1.8R) · mean_reversion 0.61R · range 0.70R → ลดเป้าทีละ 0.10 |
| ท่อ REC (`plan_to_rec.py`) | REC **17 รายการ** (set_gate 6 + set_probability_gate 5 + set_tpsl 6), `restart_after_apply=false` |
| Testing Gate | ✅ ผ่าน (ตลาดปิด → fallback ประวัติ: win-rate 63.8%, n=186) |
| apply จริง | `min_reward_risk` 1.8→1.7 · `breakout_reward_risk` 2.0→1.9 · band ขยับ ±0.06 · เพิ่ม `{strategy}_reward_risk` 4 ตัว |
| validator (`load_config`) หลัง apply | ✅ ผ่าน · `live_enabled/magic/volume` ไม่ถูกแตะ |
| **hot reload** | ✅ ไฟล์เปลี่ยน → ค่าในหน่วยความจำเปลี่ยนทันที · เรียกซ้ำโดยไฟล์เดิม = ไม่ทำอะไร (idempotent) |
| invariant band ทั้งชุด | ✅ `0.05 ≤ low ≤ high ≤ 1.0` ทุกค่า |

---

## 9. Pitfalls ที่เจอจริง (บันทึกไว้กันพลาดซ้ำ)

1. **ต้องมี hot reload** — `decide_market` อ่าน dict ในหน่วยความจำ; เขียนไฟล์อย่างเดียวไม่มีผลจนรีสตาร์ท
2. `position_closed.strategy` = `unknown` เกือบทั้งหมด → net ในเครื่องยนต์ว่าง → ต้องป้อนจากรอบวิจัย
3. `both_set` (per-side override) ถ้าบังคับเฉพาะ per-side → กลยุทธ์ที่มีแค่ `raw`/`raw_max` กลางปรับไม่ได้เลย
4. ค่า low/high ไขว้กัน → REC ถูก validator ปฏิเสธ (`band invalid`) ต้อง clamp `low ≤ high − 0.02`
5. สคริปต์เขียน JSON ที่ใช้ path ไทย/UTF-8 → ต้อง `PYTHONUTF8=1` และระวัง `io` ไม่ได้ import
6. consumer ต้องลบ `PYTHONPATH`/`PYTHONHOME` ก่อน spawn venv ไม่งั้น numpy พัง → Testing Gate บล็อกทุก REC
7. `ticket` ของ order ≠ ticket ของ position (join ไม่ได้) → ต้อง FIFO ตามเวลา
8. `hermes cron list` ซ่อนงานที่ paused — ต้องอ่าน `jobs.json` ตรงๆ หรือ `--all`
9. govemance ห้ามเก็บ state (`baseline`, `_touches`) — validator จำกัดคีย์ → เก็บใน `strategy_router.auto_threshold` แทน

---

## 10. คำสั่งตรวจซ้ำ (ทำได้ทันที)

```bash
export PYTHONUTF8=1; cd "D:/AI WorkSpace/Codex WorkSpace/เทรดทองคำ"
python "$LOCALAPPDATA/hermes/scripts/band_plan.py"     # แผน 36 ค่า
python "$LOCALAPPDATA/hermes/scripts/tpsl_plan.py"     # แผน TP/SL
rm -f work/plan_rec_state.json                          # เคลียร์ cooldown เวลาทดสอบเท่านั้น
python "$LOCALAPPDATA/hermes/scripts/plan_to_rec.py"   # แผน → REC
python "$LOCALAPPDATA/hermes/scripts/llm_rec_consumer_runner.py"   # รอบ 5 นาทีเต็ม (gate + apply)
python "$LOCALAPPDATA/hermes/scripts/audit_full_system.py"         # ตรวจสุขภาพระบบรวม (อ่านอย่างเดียว)
```

---

## 11. แนวทางพัฒนาต่อ (สำหรับผู้สานต่อ)

**ต่อยอดได้ทันที (ข้อมูลมีอยู่แล้ว)**
- บันทึก **MFE/MAE** ต่อไม้ใน `position_closed` → ตัดสิน TP ได้แม่นขึ้น (ตอนนี้ใช้ R-multiple จริงซึ่งยังหยาบ)
- **per-side TP/SL** (buy/sell แยกกัน) — ปัจจุบัน TP/SL แยกระดับกลยุทธ์ ไม่แยกทิศทาง
- ใช้ `router_decision.confidence` ใน audit เป็นตัวแปรเสริมในการเลือก band
- เพิ่ม **regime-conditioned band** (trend/range regime → คนละ band)

**ข้อควรระวังถ้าจะแก้กติกา**
- อย่าลด **Testing Gate** หรือ **step cap** จนระบบสั่น (ค่าจะแกว่งทุก 5 นาที = เสีย spread ฟรี)
- อย่าให้ท่อ REC เขียน `live_enabled`/`magic`/`volume` เด็ดขาด (ผู้ใช้ต้องเป็นคนเปิด-ปิดเท่านั้น)
- ถ้าจะเพิ่ม action ใหม่ใน REC → ต้องเพิ่มใน **ทั้ง consumer และ tester** (ALLOWED + validate + apply) ไม่งั้นถูกบล็อก
- ก่อนเปิดใช้จริงทุกครั้ง: ตรวจ `AutoTrading` ของ terminal เปิด (ไม่งั้น `retcode=10027`), spread ≤ `max_spread`, และตลาดเปิด (`market_clock.market_open()`)

---

## 12. ผลตรวจสุขภาพระบบ (13 ก.ย. 2026 เวลาไทย)

**โครงสร้าง:** ✅ ครบทั้ง 3 ชั้น (เทรด python · บันทึก/สถิติ python · วิจัย LLM) — ไฟล์หลัก 10 ไฟล์ + สคริปต์ start/stop + venv ครบ · ขั้นงานรอบ 10 นาที 11 ขั้นทำงานได้ทุกตัว (รัน `verify_research_steps.py` แล้วคืนค่า config เดิมครบ 27 ไฟล์)

**การเทรด:** audit 15,473 แถว · 24 ชม.ล่าสุดไม่มี error เลย (`fatal`/`recoverable_error` = 0) · ออเดอร์สำเร็จรวม 213 ไม้ · ปิดแล้ว 186 ไม้ net **−$1.23** (win-rate 60.8%, เฉลี่ย −$0.007/ไม้ — แทบเสมอตัว) · ไม้แย่สุด −$1.09 / ดีสุด +$1.16

**ประเด็นที่ต้องจัดการก่อนเปิดเทรด (ผู้ใช้เป็นคนสั่ง)**
1. 🔴 **MT5 AutoTrading ปิดอยู่** → ถ้าเปิดระบบตอนนี้ `order_send` จะโดน `retcode=10027` ต้องกดปุ่มเขียวใน terminal ก่อน
2. 🟡 **มี 1 position ค้างอยู่**: SELL 0.001 @ 4347.775 (เปิด 12 ก.ย. 06:52) ราคาปัจจุบัน 4350.555 = **−$0.28** — มี SL 4351.643 / TP 4340.869 ครบ (ป้องกันความเสี่ยงแล้ว) ต้องตัดสินใจว่าจะถือต่อหรือปิดเอง
3. 🟡 **`max_consecutive_losses = 0` = ปิดการใช้งาน** (โค้ดเช็ค `> 0` เท่านั้น) — ที่ผ่านมาเคยแพ้ติดกันสูงสุด 6 ไม้ ถ้าต้องการเบรกอัตโนมัติต้องตั้ง > 0
4. 🟡 **net expectancy ยังติดลบเล็กน้อย** (−$0.007/ไม้) — ตรงกับผล `at_vs_trade` (72 ชม.: −$0.040/ไม้, "โซนหลวม ควร tighten") ซึ่งเป็นเหตุผลที่ท่อปรับ band/TP-SL นี้มีอยู่: ให้มันค่อย ๆ tighten ฝั่งที่ net ติดลบ
5. ℹ️ cron ทั้ง 2 งาน (10 นาที/5 นาที) **ยัง paused** ตามที่ผู้ใช้สั่ง — พอรัน `start_FULL_system.cmd` ท่อนี้จะเริ่มทำงานอัตโนมัติ (ปรับไม่เกิน step cap ต่อรอบ)
6. ℹ️ ขณะตรวจตลาดปิดอยู่ (spread ที่เห็น 2.33 เป็นค่าตลาดปิด) — ต้องดู spread ใหม่ตอนตลาดเปิด (เกณฑ์ `max_spread = 0.6`)

**สรุป:** โครงสร้างครบ ทำงานราบรื่น ไม่มี error 24 ชม. และกลไกป้องกันความเสี่ยง (SL/TP ต่อออเดอร์, เพดาน risk, spread gate, hedge cap, market clock, kill switch) ทำงานครบ — ความสุขุมของระบบยังต้องพึ่งพาการ tighten ค่า band/TP-SL ซึ่งท่อใหม่นี้ทำหน้าที่นั้นแบบอัตโนมัติ
