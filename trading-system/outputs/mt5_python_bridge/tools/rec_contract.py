#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""สัญญาการสื่อสารระหว่าง 'บอท (agent)' กับ 'สคริปต์ Python' — สร้างจากโค้ดจริง

เจ้าของระบบกำหนด (19 ก.ย. 2026):
  "บอทต้องรู้ทุกครั้งเมื่อสื่อสารกับ python script ว่าต้องสื่อสารกันแบบไหน
   ต้องมีระบบทำให้บอทรู้ข้อนี้"

หลักการ: **สัญญาต้องถูกสร้างจากโค้ดจริงของ consumer** (ไม่ใช่เขียนมือ)
→ ถ้าโค้ดเปลี่ยน (เพิ่ม action/เปลี่ยนขอบเขต) สัญญาจะเปลี่ยนตามทันที ไม่มีทางหลุดจากความจริง

ใช้:
  python tools/rec_contract.py            → พิมพ์สัญญา + เขียน research/recommendations/CONTRACT.md
  python tools/rec_contract.py --print    → พิมพ์อย่างเดียว
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
sys.path.insert(0, BR)

import llm_recommendation_consumer as C  # noqa: E402
from runtime_support import current_mode, project_root  # noqa: E402


def build_contract():
    """สร้างข้อความสัญญาการสื่อสาร (ภาษาไทย) จากค่าจริงในโค้ด"""
    root = project_root()
    try:
        mode = current_mode(root)
    except Exception:
        mode = {"mode": "?", "epoch": "?"}
    rec_dir = "research/recommendations"
    lim = C.TPSL_LIMITS
    strat_list = " · ".join(C.STRATEGIES)

    lines = [
        "# สัญญาการสื่อสาร: บอท (agent) → สคริปต์ Python (consumer)",
        "",
        "> ไฟล์นี้สร้างอัตโนมัติจากโค้ดจริงของ `llm_recommendation_consumer.py` "
        "(ห้ามแก้ด้วยมือ — รัน `tools/rec_contract.py` เพื่ออัปเดต)",
        "",
        "## 1) เขียนที่ไหน",
        f"- **ไฟล์เดียวเท่านั้น:** `{rec_dir}/latest_recommendation.json`",
        "- ระบบจะคัดลอกของเดิมที่ยังไม่ถูกประมวลผลไปเก็บที่ `superseded/` ให้อัตโนมัติ (ไม่หาย)",
        "- เขียนแบบ atomic เสมอ (ใช้ `runtime_support.write_recommendation` หรือเครื่องมือ `tools/submit_recommendation.py`)",
        "",
        "## 2) ฟิลด์บังคับ (ถ้าไม่ครบ consumer จะปฏิเสธ)",
        "| ฟิลด์ | ค่าที่ต้องเป็น | หมายเหตุ |",
        "|---|---|---|",
        "| `schema` | `\"hermes-trading-recommendation-v1\"` | ตรงเป๊ะ |",
        "| `auto_apply` | **`true`** | ⚠️ ถ้าเป็น false consumer จะปฏิเสธทันที |",
        "| `changes` | **ลิสต์ที่ไม่ว่าง** | ถ้าไม่มีอะไรจะปรับ = **อย่าส่ง** (ไม่ใช่ส่งลิสต์ว่าง) |",
        "| `mode` | `\"{}\"` | โหมดปัจจุบัน |".format(mode.get("mode")),
        "| `mode_epoch` | `\"{}\"` | ⚠️ epoch ปัจจุบัน — ถ้าไม่ตรง consumer จะปฏิเสธ (กันคำแนะนำเก่าปน) |".format(mode.get("epoch")),
        "| `uses_llm` | บอท = `true`; Python ภายใน = `false` | บอทใช้ submit_recommendation ได้เฉพาะโหมด 2; งาน Python ยังทำงานทั้งสองโหมด |",
        "| `summary` | ข้อความสั้น | สรุปคำแนะนำ 1-2 ประโยค |",
        "| `generated_at` | เวลา ISO | ใช้ตรวจย้อน |",
        "",
        "## 3) action ที่อนุญาต + ฟิลด์ของแต่ละ action",
        "| action | ฟิลด์ที่ต้องมี | ขอบเขตค่าที่อนุญาต |",
        "|---|---|---|",
        "| `set_gate` | `strategy` · `side` · `raw_low` · `raw_high` | strategy หนึ่งใน: " + strat_list
        + " · side: buy/sell · `0.05 ≤ raw_low ≤ raw_high ≤ 1.0` |",
        "| `set_probability_gate` | `strategy` · `side` · `probability_low` · `probability_high` | `0.35 ≤ low ≤ high ≤ 0.95` |",
        "| `set_tpsl` | `strategy` (หรือ `global`) + อย่างน้อย 1 ฟิลด์ด้านล่าง | `atr_stop_multiplier` {}–{} · `min_reward_risk` {}–{} · `stop_atr` (ต้องระบุ strategy) {}–{} · `reward_risk` (ต้องระบุ strategy) {}–{} |".format(
            lim["atr_stop_multiplier"][0], lim["atr_stop_multiplier"][1],
            lim["min_reward_risk"][0], lim["min_reward_risk"][1],
            lim["_stop_atr"][0], lim["_stop_atr"][1],
            lim["_reward_risk"][0], lim["_reward_risk"][1]),
        "| `set_weights` | `strategy_weights` (dict: strategy → 0.5–1.5) | ปรับน้ำหนักกลยุทธ์ (ไม่ปิดกลยุทธ์) |",
        "| `toggle_strategy` | `strategy` · `enabled` | ⚠️ `enabled=false` ถูกห้าม (ห้ามปิดกั้นการเทรด) — ใช้ `set_weights` แทน |",
        "| `set_risk` | `max_risk_pct` | ปรับความเสี่ยงรวม (ในกรอบของระบบ) |",
        "| `set_directional_weights` | `directional_weights` (dict: strategy_side → 0.5–1.5) | validator รับช่วงนี้; engine อาจจำกัดน้ำหนักที่ใช้จริงเพิ่มอีก |",
        "",
        "## 4) ห้ามทำ",
        "- ห้ามแตะคีย์ที่ระบบสงวนไว้: " + ", ".join(sorted(C.PROTECTED)),
        "- ห้ามแก้โครงสร้างโค้ด · ห้ามสตาร์ท/หยุดตัวเทรด · ห้ามลบ kill switch",
        "- ห้ามเขียนไฟล์ชื่ออื่นนอกจาก `latest_recommendation.json`",
        "- ห้ามใส่ค่าที่ไม่ใช่ตัวเลขจำกัด (NaN/Infinity) — จะถูกปฏิเสธ",
        "",
        "## 5) ขั้นตอนที่บอทต้องทำ (ทุกครั้ง)",
        "1) เขียนคำแนะนำเป็นไฟล์ชั่วคราว (เช่น `work/_rec.json`)",
        "2) **ตรวจก่อนส่ง** (บังคับ):",
        "   ```bash",
        "   .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/submit_recommendation.py --check work/_rec.json",
        "   ```",
        "3) ถ้าผ่าน → ส่งเข้าระบบ:",
        "   ```bash",
        "   .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/submit_recommendation.py --submit work/_rec.json --source bot",
        "   ```",
        "4) ถ้าไม่ผ่าน → แก้ตามเหตุผลที่ระบบบอก แล้วตรวจซ้ำ (ระบบจะบอกว่าผิดฟิลด์ไหน)",
        "",
        "## 6) ตัวอย่างคำแนะนำที่ผ่าน (ขั้นต่ำ)",
        "```json",
        "{",
        '  "schema": "hermes-trading-recommendation-v1",',
        '  "auto_apply": true,',
        '  "mode": "' + str(mode.get("mode")) + '",',
        '  "mode_epoch": "' + str(mode.get("epoch")) + '",',
        '  "uses_llm": true,',
        '  "llm_provider": "hermes-agent",',
        '  "generated_at": "<เวลา ISO>",',
        '  "summary": "ปรับเพดานบนของ trend_buy ให้สอดคล้องกับงานวิจัยข้อมูลภายใน",',
        '  "changes": [',
        '    {"action": "set_gate", "strategy": "trend", "side": "buy",',
        '     "raw_low": 0.45, "raw_high": 0.80, "reason": "<เหตุผลอ้างตัวเลขจริง>"}',
        "  ]",
        "}",
        "```",
        "",
        "## 7) ระบบจะทำอะไรต่อ (บอทไม่ต้องทำ)",
        "consumer (ทุก 5 นาที): ตรวจ schema/ความปลอดภัย → **ประตูทดสอบ (Testing Gate)** → "
        "apply ลง `auto_config.json` → บันทึกผลลง audit (`recommendation_applied` / "
        "`recommendation_rejected` / `recommendation_blocked_by_test`)",
        "> ถ้าระบบปิดอยู่ (kill switch) คำแนะนำจะถูกเก็บไว้ ไม่ถูกนำไปใช้",
    ]
    return "\n".join(lines)


def main():
    text = build_contract()
    if "--print" not in sys.argv:
        out = os.path.join(project_root(), "research", "recommendations", "CONTRACT.md")
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            io.open(out, "w", encoding="utf-8").write(text + "\n")
            print("เขียนสัญญาแล้ว:", out)
            print("")
        except Exception as exc:
            print("เขียนไฟล์ไม่ได้:", exc)
    print(text)


if __name__ == "__main__":
    main()
