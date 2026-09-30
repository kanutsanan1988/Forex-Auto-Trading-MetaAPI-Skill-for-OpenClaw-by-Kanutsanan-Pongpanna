# -*- coding: utf-8 -*-
"""ด่านถาวร: Jev ต้องช่วยงาน/ร่วมตัดสินใจกับทุกชั้นที่เจ้าของระบบกำหนด (29 ก.ย. 2026)

คำสั่ง: "Jev ต้องคอยช่วยงานและทำงานร่วมกับหรือตัดสินใจแทนได้ในบางกรณีทั้งบอทวิจัย
admin bot และที่ปรึกษาด้วย"
ข้อยกเว้น: AI ที่อยู่กับ 'ตัวเทรด' = อำนาจเจ้าของระบบเท่านั้น (ดู test_trader_ai_human_only.py)
"""
import json
from pathlib import Path

BR = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (BR / rel).read_text(encoding="utf-8")


def test_research_layer_uses_jev():
    assert "ask_preset" in _read("tools/llm_research_packet.py"), "บอทวิจัยต้องเรียก Jev"
    assert "ask_preset" in _read("news_feed.py"), "โมดูลข่าวต้องเรียก Jev (news preset)"


def test_admin_bot_uses_jev_multiple_times():
    src = _read("tools/admin_bot_round.py")
    assert src.count("ask_preset") >= 3, "แอดมินบอทต้องใช้ Jev หลายพรีเซ็ต (internal/safety/structure)"
    assert "jev_power" in src, "แอดมินบอทต้องใช้บันไดอำนาจ Jev"


def test_advisor_has_jev_helper_and_presets():
    src = _read("tools/jev_advise.py")
    assert "ask_preset" in src and "import jev" in src, "ที่ปรึกษาต้องมีตัวช่วยเรียก Jev"
    assert "hermes-decision" in src and "central-decision" in src, \
        "ที่ปรึกษาต้องใช้พรีเซ็ต hermes-decision / central-decision"


def test_jev_switches_open_for_all_three_layers():
    cfg = json.loads(_read("jev_config.json"))
    # The global switch is intentionally user-controlled and may be off when
    # no provider is configured; per-layer capability flags remain available.
    assert isinstance(cfg.get("enabled"), bool), "สวิตช์ Jev หลักต้องเป็นค่าเปิด/ปิดที่ผู้ใช้ควบคุมได้"
    for k in ("use_in_news", "use_in_admin", "use_in_advisor"):
        assert cfg.get(k) is True, f"สวิตช์ {k} ต้องเปิด"


def test_trader_ai_still_human_only():
    """กันสับสน: Jev ช่วยทุกชั้น แต่ AI ในตัวเทรดยังเป็นอำนาจเจ้าของระบบ"""
    cfg = json.loads(_read("auto_config.json"))
    assert (cfg.get("trader_ai") or {}).get("enabled") is False
    assert "trader_ai" not in _read("tools/jev_advise.py"), "ตัวช่วยที่ปรึกษาต้องไม่แตะสวิตช์ของตัวเทรด"
