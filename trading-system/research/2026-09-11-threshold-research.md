<!--
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->
# งานวิจัย: กำหนด Threshold ที่เหมาะสมสำหรับระบบเทรดทองคำ (Quant Trading)

วันที่: 11 กันยายน 2026
โฟลเดอร์การศึกษา: `D:\AI WorkSpace\Codex WorkSpace\เทรดทองคำ`
เป้าหมาย: Quant trading ตามกระบวนการที่วางไว้ — หาช่วงคะแนน (threshold) ที่ควรใช้ให้ระบบเทรด
ขอบเขต: **ไม่ปรับเปลี่ยนโปรแกรม** — เสนอผลวิจัยให้พิจารณาก่อน

---

## 1. ภาพรวมระบบ (จากอ่านโค้ดจริง)

ระบบใช้ `strategy_engine.py` สร้าง **คะแนน 3 ชนิด** ต่อทิศทาง (Buy/Sell) ของทุกกลยุทธ์:

1. **Random Score (คะแนนดิบ)** — จาก `classify_regime()` → `scores` dict ในช่วง 0–1 ต่อ 12 ตัว:
   `trend_buy/sell, range_buy/sell, mean_reversion_buy/sell, counter_trend_buy/sell, breakout_buy/sell, breakout_reversal_buy/sell`
2. **Probability** — จาก `directional_probabilities.{strategy}_{side}` (default `0.5` ถ้าไม่ตั้ง)
3. **Weighted Score (หลังถ่วงน้ำหนัก)** — `raw × strategy_weight(∈[0.85,1.15]) × directional_weight(∈[0.90,1.10])` ตัดที่ 1.0

**Gate การตัดสินใจ** (`bounded_live.governance` ใน auto_config.json):
```
gate["passed"] = (raw_score >= raw_gate) AND (probability >= probability_gate) AND (weighted_score >= weighted_gate)
```
Gate ปัจจุบัน (ตั้งไว้ใน config):
| กลยุทธ์ | raw | probability | weighted |
|---|---|---|---|
| trend | 0.60 | 0.56 | 0.62 |
| range | 0.54 | 0.55 | 0.57 |
| mean_reversion | 0.50 | 0.57 | 0.54 |
| counter_trend | 0.46 | 0.61 | 0.50 |
| breakout | 0.72 | 0.58 | 0.70 |
| breakout_reversal | 0.66 | 0.62 | 0.65 |

หมายเหตุ: `agent_score_threshold` (select รอบ 2) = 0.42, มี per-strategy thresholds แยก (trend 0.5, range 0.22, MR 0.25, breakout 0.6, CT 0.55, BR 0.65)

---

## 2. ข้อมูลจริง (จาก `auto_trader_audit.jsonl` 13,281 records)

### 2.1 Raw score distribution (0–1) ต่อ strategy/side — ใช้กำหนดช่วง threshold
วิเคราะห์จาก score จริงที่ระบบเคยคำนวณ (n=2590 ต่อตัวหลัก, counter_trend/BR มี 1794):

| strategy_side | n | mean | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|---|
| trend_buy | 2590 | 0.378 | 0.272 | 0.369 | 0.468 | 0.601 | 0.764 |
| trend_sell | 2590 | 0.465 | 0.273 | 0.374 | 0.653 | 0.828 | 0.948 |
| range_buy | 2590 | 0.176 | 0.085 | 0.158 | 0.239 | 0.345 | 0.713 |
| range_sell | 2590 | 0.154 | 0.071 | 0.144 | 0.208 | 0.278 | 0.622 |
| mean_reversion_buy | 2590 | 0.121 | 0.050 | 0.091 | 0.163 | 0.269 | 0.603 |
| mean_reversion_sell | 2590 | 0.095 | 0.041 | 0.071 | 0.138 | 0.186 | 0.576 |
| counter_trend_buy | 1794 | 0.079 | 0.000 | 0.000 | 0.075 | 0.339 | 0.813 |
| counter_trend_sell | 1794 | 0.049 | 0.000 | 0.000 | 0.000 | 0.234 | 0.578 |
| breakout_buy | 2590 | 0.026 | 0.000 | 0.000 | 0.000 | 0.000 | 0.999 |
| breakout_sell | 2590 | 0.038 | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |
| breakout_reversal_buy | 1794 | 0.021 | 0.000 | 0.000 | 0.000 | 0.000 | 0.925 |
| breakout_reversal_sell | 1794 | 0.023 | 0.000 | 0.000 | 0.000 | 0.000 | 0.919 |

**ข้อสังเกตสำคัญ:** คะแนนดิบของแต่ละกลยุทธ์มีสเกลธรรมชาติต่างกันมาก —
- Trend สูง (median ~0.37) เพราะ component เป็น factor รวมที่ค่อนข้างสูงกว่าศูนย์เสมอ
- Range/MR ต่ำ (median 0.09–0.16) เพราะถูกคูณ `range_score` ที่มักเล็ก
- Counter-trend/Breakout/BR มักเป็น **0** เกือบตลอด (ต้องเกิด pattern หายากก่อน → score>0) แต่เมื่อเกิดจริงจะพุ่งสูงมาก (max 0.8–1.0)

**จึงต้องใช้ threshold แยกต่อกลยุทธ์ ไม่ใช่ค่าเดียว**

### 2.2 Gate ผ่านจริง (eligible counts) — เพื่อดูความยาก
จาก audit:
| strategy_side | จำนวนครั้งที่ผ่าน | หมายเหตุ |
|---|---|---|
| trend_sell | 54 | ผ่านบ่อยสุด |
| range_sell | 52 | |
| counter_trend_buy | 51 | |
| range_buy | 45 | |
| breakout_reversal_buy | 44 | |
| breakout_reversal_sell | 41 | |
| mean_reversion_sell | 40 | |
| counter_trend_sell | 40 | |
| mean_reversion_buy | 39 | |
| trend_buy | 11 | น้อยมาก |
| breakout_sell | 11 | |
| breakout_buy | 9 | |

### 2.3 Root cause: ทำไมเทรดยากมาก

| ปัจจัย | จำนวน | ชัดเจน |
|---|---|---|
| `no_trade` โดยรวม | 2911 | เหตุหลัก |
| `position already open` | 1160 | มี position ค้างเกือบตลอด → block |
| `bounded-live: no Agent passed raw/probability/weighted gates` | 459 | **gate ด้าน code** |
| `same-direction signal` | 373 | ถ้ามี position ทิศเดียวกัน block |
| `no multi-timeframe signal` | 160 | |
| candidates raw≥0.42 **แต่ ineligible** | 1453 | score ผ่าน threshold **แต่ entry-filter ปฏิเสธ** |

**เหตุผลหลัก 3 กลุ่ม (จาก 1453 ครั้งที่ raw≥0.42 ถูกปฏิเสธ):**
- 608 `trend_sell` — "no fresh M5 pullback-resumption cross with valid RSI"
- 421 `trend (None)` — "market regime is not a confirmed trend"
- 192 `trend_buy` — "no fresh M5 pullback-resumption cross with valid RSI"
- 143 breakout (sell/buy) — "breakout strength, volume or higher-timeframe confirmation failed"
- 51 counter_trend — "exhaustion reversal is not confirmed"

**(KEY) ปัญหา gate แบบเงียบที่ทำให้แทบไม่เทรดเลย:**
ใน `decide_market()` (strategy_engine.py ~line 869, 887): `probability` อ่านจาก
`directional_probabilities.get(f"{strategy}_{side}", 0.5)` → **default = 0.5**
แต่ `bounded_live.governance.probability_gate` ตั้งไว้ที่ **0.55–0.62**
→ `probability (0.5) >= probability_gate (0.55+)` = **False ทุกครั้งที่ไม่ได้ตั้ง probability จริง**

และ `auto_config.json` **ไม่มี** `directional_probabilities` / `directional_weights` ค่า (มีแต่ governance gates)
→ ระบบจะ `no_trade` เกือบทุกครั้งเพราะ probability gate ไม่ผ่าน — **คือเหตุผลหลักที่เทรดยากมาก**

---

## 3. ข้อเสนอ Threshold ที่แนะนำ (หลักการ)

อ้างอิงจาก: (a) distribution จริง, (b) แนวคิดว่า threshold ควรกรองส่วน tail บนเท่านั้น (ตัด noise), (c) แยกสเกลต่อกลยุทธ์

### 3.1 Raw Score (คะแนนดิบ) — ควรเทรดเมื่อ ≥ ค่านี้
| กลยุทธ์/ทิศ | ผ่านได้เมื่อ raw ≥ | เหตุผล |
|---|---|---|
| trend_buy | 0.55 | median 0.37, p90 0.60 |
| trend_sell | 0.55 | median 0.37, p90 0.83 |
| range_buy | 0.30 | median 0.16, p90 0.35 |
| range_sell | 0.30 | median 0.14, p90 0.28 |
| mean_reversion_buy | 0.25 | median 0.09, p90 0.27 |
| mean_reversion_sell | 0.25 | median 0.07, p90 0.19 |
| counter_trend_buy | 0.35 | p75 0.075, p90 0.34, สูงเมื่อเกิด |
| counter_trend_sell | 0.35 | |
| breakout_buy | 0.70 | ปกติ 0, แต่เมื่อเกิดสูง |
| breakout_sell | 0.70 | |
| breakout_reversal_buy | 0.60 | หายาก, ต้องการ high conv |
| breakout_reversal_sell | 0.60 | |

*(หมายเหตุ: showdown ยังใช้ `structural eligible` = technical entry-filter ปัจจุบันกำแพงหลัก; raw threshold ควรตั้งให้ต่ำพอที่เมื่อ pattern จริงเกิดจะผ่าน)*

### 3.2 Probability — ควรเทรดเมื่อ ≥
- ปกติควรอยู่ **0.55–0.65** ต่อตัว แต่**ต้องมี directional_probabilities จริง** (ตั้งใน config) ไม่อย่างนั้นใช้ default 0.5 ทำให้ไม่มีทางผ่าน gate 0.55+
- ข้อเสนอ: ตั้ง `directional_probabilities` ให้สมจริง (เช่น trend 0.60, range 0.55, MR 0.58, breakout 0.62, CT 0.60, BR 0.62) และ**ตั้ง probability_gate ให้ต่ำกว่าค่าที่ตั้ง 0.02–0.05** เสมอ

### 3.3 Weighted (หลังถ่วงน้ำหนัก) — ควรเทรดเมื่อ ≥
- ตั้งให้น้อยกว่า raw เล็กน้อย (เพราะ weight มีล่าง 0.85–0.90 ทำให้ weighted < raw โดยธรรมชาติ)
- ข้อเสนอ: `weighted_gate ≈ raw_gate × 1.0–1.10`
  - trend 0.60, range 0.33, MR 0.27, CT 0.38, breakout 0.72, BR 0.63

---

## 4. ข้อแนะนำแก้ไข (ยังไม่ลงมือ — เสนอพิจารณา)

ลำดับความสำคัญที่เห็นควรแก้:
1. **ตั้ง `directional_probabilities` จริงใน auto_config.json** — แก้ root cause หลัก (ตอนนี้ default 0.5 < gate 0.55+ → แทบไม่เทรด)
2. **ตรวจสอบ/ผ่อน M5 pullback-resumption cross gate** ของ Trend — เป็นตัว block สูงสุด (608+192=800 ครั้ง) อาจให้ทางเลือก humid เมื่อ score สูงมาก
3. **ผ่อน `position already open` cooldown** — 1160 ครั้งถูก block เพราะมีpositionเดียวค้างตลอด (cooldown=0,profit_exit min $0) — พิจารณาให้เข้ามือใหม่เฉพาะเมื่อหลุด position จริง หรือปรับ profit_exit
4. **ตั้ง threshold ตามตาราง §3 (แยกต่อกลยุทธ์/ทิศ)** — แทนค่าเดี่ยว 0.42
