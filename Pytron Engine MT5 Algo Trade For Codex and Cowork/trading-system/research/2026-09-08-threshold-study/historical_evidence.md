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
# Historical broker and audit evidence

Offline frozen inputs only; no live trading code imported and no order or API call performed.

Audit: 5,843 records from 2026-08-25T09:30:14.563856+00:00 to 2026-09-08T15:44:18.990730+00:00; 1,664 rows contain analysis, across 1,659 unique UTC minute buckets.
Broker: 548 total deals, 556 orders; 542 gold trade deals reconstruct 271 complete closed positions. Gold closed net = USD -37.37. Entry magic 8252026: 133 closed positions, USD +0.90.
Exact audit order-ID matching: 133 closed positions, USD +0.90. Successful audit entry events = 133; unique IDs = 133; matched IDs = 133.

Net includes all entry and exit deal profit, commission, swap and fee. Manual/unmatched history is not attributed to a strategy score. All amounts are USD from the frozen account history.

| Direction | Matched closed n | Net USD | Win rate | Raw score n | Weighted score n | Entry probability n |
|---|---:|---:|---:|---:|---:|---:|
| trend_buy | 1 | -0.49 | 0.0% | 1 | 1 | 0 |
| trend_sell | 27 | +0.25 | 70.4% | 26 | 26 | 0 |
| range_buy | 27 | -3.15 | 44.4% | 27 | 27 | 7 |
| range_sell | 20 | +0.43 | 70.0% | 20 | 20 | 9 |
| mean_reversion_buy | 18 | +1.03 | 72.2% | 18 | 18 | 17 |
| mean_reversion_sell | 25 | +0.97 | 64.0% | 25 | 25 | 24 |
| breakout_buy | 6 | +0.55 | 66.7% | 6 | 6 | 3 |
| breakout_sell | 3 | +0.47 | 66.7% | 3 | 3 | 0 |
| counter_trend_buy | 0 | +0.00 | — | 0 | 0 | 0 |
| counter_trend_sell | 0 | +0.00 | — | 0 | 0 | 0 |
| breakout_reversal_buy | 0 | +0.00 | — | 0 | 0 | 0 |
| breakout_reversal_sell | 0 | +0.00 | — | 0 | 0 | 0 |

Unclassified audit-matched positions: 4; these cannot supply per-direction threshold evidence.

Shadow outcomes are paper trades: 333 in retained state, 333 unique closures in the full audit, and 208 older router simulations. They are not additional broker executions.
Observed contamination: 0/333 retained outcomes close on or before their opening M1 bar; 5 have an age exceeding elapsed M1 bars. The last 400 score snapshots cover 400 unique bars (0 repeated records). Full-audit same/earlier-bar closures: 0.

The probability field is a smoothed direction win frequency from these simulated outcomes. It is not a demonstrated probability of profit for the current score. Score-conditional calibration, sparse-direction sample size, co-occurrence dependence, observation gaps, and per-row model version history remain insufficient for choosing 12 durable thresholds.

The JSON includes executed trade IDs, entry audit-line provenance, net component reconciliation, Wilson intervals, descriptive calibration, daily/schema coverage, probability freeze runs, and raw/weighted/probability threshold slices. Those slices only filter trades that historically executed. They do not estimate the outcome of rejected trades or of changing the full trading policy.
