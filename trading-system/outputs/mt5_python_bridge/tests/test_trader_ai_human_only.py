# -*- coding: utf-8 -*-
"""ด่านถาวร: AI ที่อยู่กับตัวเทรด = อำนาจเจ้าของระบบ (มนุษย์) เท่านั้น

คำสั่งเจ้าของระบบ 29 ก.ย. 2026:
  "ตั้งให้ AI ของตัวเทรดเป็น Jev ตัวเดียวเท่านั้น ... แล้วก็ปิดไว้
   ตัวนี้คำสั่งเปิดหรือปิดเป็นอำนาจเฉพาะของมนุษย์เท่านั้น"
  "ตัวเฝ้าเครดิตเปิดปิดได้เฉพาะ AI ตัวอื่นได้ทุกตัวครับ ยกเว้นตัวนี้"

ด่านนี้จะแดงทันทีถ้ามีใคร:
  • เปิดสวิตช์ AI ของตัวเทรดใน config
  • ทำให้ตัวเฝ้าเครดิตแตะสวิตช์ของตัวเทรด
  • ทำให้ตัวเทรดกลับไปเรียก OpenRouter dual agents
"""
import json
import sys
from pathlib import Path

BR = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (BR / name).read_text(encoding="utf-8")


def test_config_switch_is_off_and_human_only():
    cfg = json.loads(_read("auto_config.json"))
    t = cfg.get("trader_ai") or {}
    assert t.get("enabled") is False, "สวิตช์ AI ของตัวเทรดต้องปิดไว้ (เปิดได้เฉพาะเจ้าของระบบ)"
    assert t.get("human_only") is True, "ต้องระบุ human_only = True"
    assert t.get("provider") == "jev", "AI ของตัวเทรดต้องเป็น Jev เท่านั้น"


def test_module_disabled_by_default_even_without_config_key():
    """แม้ไม่มีคีย์ใน config เลย ต้องยังปิด — และต้องได้คำตัดสินใจจาก Python"""
    sys.path.insert(0, str(BR))
    import trader_ai  # noqa: E402

    pd = {"side": "sell", "strategy": "mean_reversion", "confidence": 0.61,
          "stop_distance": 4.2, "reward_risk": 1.4}
    r = trader_ai.run_trader_ai({}, {}, pd)
    assert r["enabled"] is False
    assert r["status"] == "disabled"
    assert r["provider"] == "jev"
    assert r["trade_decision"]["side"] == "sell", "ต้องใช้คำตัดสินใจจาก Python ต่อ"


def test_trader_ai_module_never_uses_openrouter():
    """ห้าม 'เรียกใช้' OpenRouter — คำอธิบายในคอมเมนต์ที่บอกว่าห้ามใช้ ไม่ผิด"""
    src = _read("trader_ai.py")
    assert "openrouter_agents" not in src, "โมดูล AI ของตัวเทรดห้ามนำเข้า openrouter_agents"
    assert "openrouter.ai" not in src, "โมดูล AI ของตัวเทรดห้ามเรียก URL ของ OpenRouter"


def test_credit_guard_cannot_touch_trader_ai():
    src = _read("tools/credit_guard.py")
    assert "HUMAN_ONLY_TRADER_AI" in src, "ต้องมีค่าคงที่ล็อกอำนาจมนุษย์"
    assert '"manage_trader_ai": True' not in src, "ค่าเริ่มต้นต้องไม่ใช่ True"
    assert "if False and" in src, "ประตูที่เปิด AI ให้ตัวเทรดต้องถูกล็อก"
    assert "trader_ai.enabled" not in src, "ตัวเฝ้าเครดิตห้ามอ้างถึงสวิตช์ของตัวเทรด"


def test_trader_never_calls_openrouter_dual_agents():
    for f in ("auto_trader.py", "market_analyzer.py"):
        src = _read(f)
        live = [l for l in src.splitlines()
                if "run_dual_agents(" in l
                and not l.strip().startswith("#")
                and "def run_dual_agents" not in l]
        assert not live, f"{f} ยังเรียก OpenRouter dual agents อยู่"
        assert "run_trader_ai(" in src, f"{f} ต้องเรียกชั้น AI ของตัวเทรด (Jev)"