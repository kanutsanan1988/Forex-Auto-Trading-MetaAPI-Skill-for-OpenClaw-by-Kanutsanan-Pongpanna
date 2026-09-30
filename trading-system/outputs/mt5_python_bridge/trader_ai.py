# -*- coding: utf-8 -*-
"""trader_ai.py — ชั้น AI ของ "ตัวเทรด" = Jev เท่านั้น (เจ้าของระบบสั่ง 29 ก.ย. 2026)

คำสั่งเจ้าของระบบ (29 ก.ย. 2026):
  "ตั้งให้ AI ของตัวเทรดเป็น Jev ตัวเดียวเท่านั้น ทำระบบให้มันเข้ากันได้กับตัวเทรด
   แล้วก็ปิดไว้ ตัวนี้คำสั่งเปิดหรือปิดเป็นอำนาจเฉพาะของมนุษย์เท่านั้น"

หลักการของไฟล์นี้:
  1) ใช้ "โมดูล Jev ที่มีอยู่" (tools/jev.py) — ให้โมดูลจัดการค้นหา/เชื่อมต่อ/provider/คีย์เอง
     ห้ามตัดสินใจแทนโมดูล (ห้ามฮาร์ดโค้ดรุ่น/ที่อยู่/คีย์)
  2) ปิดไว้เป็นค่าเริ่มต้น (trader_ai.enabled = false)
  3) เปิด/ปิด = อำนาจเจ้าของระบบเท่านั้น — ห้ามระบบเปิดเอง ห้ามตัวเฝ้าเครดิตแตะ
  4) ตัวเทรด "ไม่เรียก OpenRouter dual agents" อีก (เส้นทางเดิมถูกถอดออกจากจุดเรียก)
  5) ค่าที่ใช้ส่งคำสั่ง (SL/TP/ขนาด) ต้องคำนวณจาก Python เสมอ — Jev ทำหน้าที่ได้แค่
     "ยืนยัน/ยับยั้ง" ทิศทาง ไม่สร้างค่าออกคำสั่งเอง (fail-closed)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

PRESET_DEFAULT = "regime"
CONTEXT_DEFAULT = "mode2"


def _cfg(config: dict) -> dict:
    return dict(config.get("trader_ai") or {})


def _disabled(python_decision: dict, reason: str, **extra) -> dict:
    out = {"enabled": False, "status": "disabled", "provider": "jev",
           "reason": reason, "trade_decision": python_decision}
    out.update(extra)
    return out


def _build_state(frames: dict, python_decision: dict) -> dict:
    """ประกอบข้อมูลให้ Jev: ใช้ features/regime ที่ตัวเทรดคำนวณเอง + ราคาล่าสุด"""
    reg = python_decision.get("regime") or {}
    prices = []
    try:
        for key in ("h1", "m15", "m5"):
            rows = (frames or {}).get(key) or []
            if rows:
                prices = [float(r[-1] if isinstance(r, (list, tuple)) else r) for r in rows[-60:]]
                break
    except Exception:
        prices = []
    return {
        "features": reg if isinstance(reg, dict) else {"value": reg},
        "prices": prices,
        "decision": {k: python_decision.get(k) for k in
                     ("side", "strategy", "confidence", "reason", "stop_distance", "reward_risk")},
        "note": "ข้อมูลจากตัวเทรด (regime/features ที่คำนวณในเครื่อง) ไม่ใช่ข้อมูลภายนอก",
    }


def run_trader_ai(config: dict, frames: dict, python_decision: dict) -> dict:
    """คืน dict รูปเดียวกับ run_dual_agents เดิม เพื่อให้ตัวเทรดใช้ต่อได้ทันที

    เปิดใช้งานจริงเฉพาะเมื่อ config['trader_ai']['enabled'] = true (เจ้าของระบบเปิดเอง)
    """
    cfg = _cfg(config)
    if not bool(cfg.get("enabled", False)):
        return _disabled(python_decision,
                         "trader AI (Jev) ปิดอยู่ — เปิด/ปิดเป็นอำนาจเจ้าของระบบเท่านั้น",
                         human_only=True, preset=str(cfg.get("preset") or PRESET_DEFAULT))

    try:
        import jev  # โมดูล Jev ของระบบ (จัดการค้นหา/เชื่อมต่อ/provider เอง)
    except Exception as exc:  # pragma: no cover
        return _disabled(python_decision, "นำเข้าโมดูล Jev ไม่ได้: %s" % exc,
                         fallback=True, error=str(exc))

    preset = str(cfg.get("preset") or PRESET_DEFAULT)
    context = str(cfg.get("context") or CONTEXT_DEFAULT)
    state = _build_state(frames, python_decision)

    try:
        answers = jev.ask_preset(preset, state, context=context)
        derived = {}
        try:
            derived = jev.derive(preset, answers) or {}
        except Exception:
            derived = {}
    except Exception as exc:
        return _disabled(python_decision, "Jev ตอบไม่ได้: %s" % exc, fallback=True, error=str(exc))

    # ── ตีความผลของ Jev เป็นการ "ยืนยัน/ยับยั้ง" เท่านั้น (ไม่สร้างค่าออกคำสั่ง) ──
    def _pick(answers, derived, key):
        if isinstance(derived, dict) and key in derived:
            return derived[key]
        if isinstance(answers, dict) and key in answers:
            v = answers[key]
            if isinstance(v, dict):
                for kk in ("value", "answer", "choice", "score", "result"):
                    if kk in v:
                        return v[kk]
            return v
        return None

    regime = str(_pick(answers, derived, "regime") or "").lower()
    side = str(python_decision.get("side") or "").lower()
    veto = False
    veto_reason = ""

    if bool(cfg.get("veto_against_clear_trend", True)) and side in ("buy", "sell"):
        if regime == "trend_up" and side == "sell":
            veto, veto_reason = True, "Jev: ตลาดแนวโน้มขึ้นชัด — ยับยั้งฝั่ง sell"
        elif regime == "trend_down" and side == "buy":
            veto, veto_reason = True, "Jev: ตลาดแนวโน้มลงชัด — ยับยั้งฝั่ง buy"

    if veto:
        blocked = dict(python_decision)
        blocked.update(side=None, strategy=None, confidence=0.0, stop_distance=None,
                       reward_risk=None, reason="trader AI (Jev) veto: " + veto_reason)
        return {"enabled": True, "status": "ok", "provider": "jev", "preset": preset,
                "context": context, "regime": regime, "derived": derived, "answers": answers,
                "veto": True, "veto_reason": veto_reason, "trade_decision": blocked}

    return {"enabled": True, "status": "ok", "provider": "jev", "preset": preset,
            "context": context, "regime": regime, "derived": derived, "answers": answers,
            "veto": False, "trade_decision": python_decision}


def main() -> int:
    """ตรวจสถานะ (ไม่เรียก AI): ใช้ได้กับสคริปต์ตรวจ/QC"""
    here = Path.cwd()
    cfg_file = None
    for cand in (here / "auto_config.json", HERE / "auto_config.json",
                 Path(r"<PROJECT_ROOT>\outputs\mt5_python_bridge\auto_config.json")):
        if cand.exists():
            cfg_file = cand
            break
    out = {"provider": "jev", "enabled": None, "human_only": True, "preset": PRESET_DEFAULT}
    if cfg_file:
        try:
            cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
            t = cfg.get("trader_ai") or {}
            out.update(enabled=bool(t.get("enabled", False)),
                       preset=str(t.get("preset") or PRESET_DEFAULT),
                       human_only=bool(t.get("human_only", True)),
                       note="เปิด/ปิดเป็นอำนาจเจ้าของระบบเท่านั้น")
        except Exception as exc:
            out["error"] = str(exc)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())