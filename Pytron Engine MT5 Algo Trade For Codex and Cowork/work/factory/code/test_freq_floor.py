#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ทดสอบ FREQUENCY FLOOR ใน apply_adaptive_gates (ห้ามปิดกั้นการเทรด)
รัน: PYTHONUTF8=1 python test_freq_floor.py
"""
import sys, os, time, types, copy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# stub MetaTrader5 (ไม่ต้องต่อ terminal เพื่อทดสอบ logic)
if "MetaTrader5" not in sys.modules:
    try:
        import importlib
        importlib.import_module("MetaTrader5")   # ทดสอบว่าติดตั้งไพแพ็กเกจจริงได้ (ถ้าไม่ได้ ใช้สตับด้านล่าง)
    except Exception:
        m = types.ModuleType("MetaTrader5")
        m.TRADE_ACTION_DEAL = 1
        sys.modules["MetaTrader5"] = m

import auto_trader  # noqa

# ★ แก้ 19 ก.ย. 2026: เทสต์ต้องไม่เขียน audit ของระบบจริง
#   (เดิม apply_adaptive_gates เขียน adaptive_update/adaptive_reenable ลง
#    work/auto_trader_audit.jsonl ทำให้ข้อมูลจริงปนเปื้อน)
auto_trader.audit = lambda *a, **k: None      # ปิดการเขียน audit ในเทสต์นี้

STRATS = ["trend", "range", "mean_reversion", "counter_trend", "breakout", "breakout_reversal"]
FAIL = []


def base_cfg(adaptive_over=None):
    adaptive = {"enabled": True, "min_samples": 3, "disable_profit_factor": 0.85,
                "enable_profit_factor": 1.05, "max_disabled": 2, "reenable_hours": 12.0}
    adaptive.update(adaptive_over or {})
    return {"strategy_router": {"adaptive": adaptive, "trade_enabled": {s: True for s in STRATS},
                                "strategy_weights": {s: 1.0 for s in STRATS}}}


def mk_state(outcomes=None, gates=None, off_since=None):
    st = {"adaptive": {"outcomes": outcomes or {}, "gates": gates or {}, "gate_off_since": off_since or {}}}
    return st


def check(name, cond, extra=""):
    print(("✅ " if cond else "❌ ") + name + ((" — " + extra) if extra else ""))
    if not cond:
        FAIL.append(name)


# ── กรณี 1: 4 กลยุทธ์ pf ต่ำ (ควรถูกปิดได้ไม่เกิน max_disabled=2) ──
losing = {"trend": [-1.0, -1.0, -1.0, -1.0], "range": [-1.0, -1.0, -1.0, -1.0],
          "counter_trend": [-1.0, -1.0, -1.0, -1.0], "mean_reversion": [-1.0, -1.0, -1.0, -1.0]}
cfg = base_cfg()
state = mk_state(outcomes=losing)
out = auto_trader.apply_adaptive_gates(copy.deepcopy(cfg), state)
te = out["strategy_router"]["trade_enabled"]
off = [s for s in STRATS if not te[s]]
check("ปิดได้ไม่เกิน max_disabled (2)", len(off) <= 2, f"ปิด={off}")
check("ยังมีกลยุทธ์เปิดเทรดเสมอ", any(te.values()), str(te))

# ── กรณี 2: ปิดมานานเกิน reenable_hours → เปิดคืนอัตโนมัติ ──
old_ts = time.time() - 13 * 3600
cfg2 = base_cfg()
state2 = mk_state(outcomes={},
                  gates={s: False for s in STRATS},
                  off_since={s: old_ts for s in STRATS})
# ให้ 3 ตัวถูกปิดอยู่ (gate False) และ enabled ในคอนฟิก = False
for s in STRATS[:3]:
    cfg2["strategy_router"]["trade_enabled"][s] = False
out2 = auto_trader.apply_adaptive_gates(copy.deepcopy(cfg2), state2)
te2 = out2["strategy_router"]["trade_enabled"]
check("ปิดมานาน > 12 ชม. → เปิดคืนทั้งหมด", all(te2[s] for s in STRATS[:3]), str({s: te2[s] for s in STRATS[:3]}))
check("gate_off_since ถูกล้างเมื่อเปิดคืน", len(state2["adaptive"]["gate_off_since"]) == 0,
      str(state2["adaptive"]["gate_off_since"]))

# ── กรณี 3: เพิ่งปิด (ยังไม่ถึง 12 ชม.) → ต้องยังปิดอยู่ (ไม่เปิดมั่ว) ──
cfg3 = base_cfg()
cfg3["strategy_router"]["trade_enabled"]["trend"] = False
state3 = mk_state(outcomes={}, gates={"trend": False}, off_since={"trend": time.time() - 60})
out3 = auto_trader.apply_adaptive_gates(copy.deepcopy(cfg3), state3)
check("เพิ่งปิด 1 นาที → ยังปิดอยู่", out3["strategy_router"]["trade_enabled"]["trend"] is False)
check("จับเวลา off_since ถูกเก็บ", "trend" in state3["adaptive"]["gate_off_since"])

# ── กรณี 4: adaptive ปิด (enabled=false) → ไม่แตะอะไรเลย ──
cfg4 = base_cfg({"enabled": False})
cfg4["strategy_router"]["trade_enabled"]["range"] = False
state4 = mk_state()
out4 = auto_trader.apply_adaptive_gates(copy.deepcopy(cfg4), state4)
check("adaptive ปิด → คงค่าเดิม (range ยังปิดตามที่ผู้ใช้ตั้ง)", out4["strategy_router"]["trade_enabled"]["range"] is False)
check("adaptive ปิด → ไม่สร้าง gate_off_since", not state4["adaptive"].get("gate_off_since"))

# ── กรณี 5: REC (LLM) พยายามปิดกลยุทธ์ → ต้องถูก reject ──
try:
    import llm_recommendation_consumer as cons
    base = {"schema": "hermes-trading-recommendation-v1", "auto_apply": True, "summary": "test"}
    off = {**base, "changes": [{"action": "toggle_strategy", "strategy": "trend", "enabled": False}]}
    ok, msg = cons.validate(off)
    check("REC ปิดกลยุทธ์ → reject (ห้ามปิดกั้นการเทรด)", ok is False and "ปิดกั้น" in msg, msg)
    on = {**base, "changes": [{"action": "toggle_strategy", "strategy": "trend", "enabled": True}]}
    ok2, msg2 = cons.validate(on)
    check("REC เปิดกลยุทธ์ → ผ่าน", ok2 is True, msg2)
    w = {**base, "changes": [{"action": "set_weights", "strategy_weights": {"trend": 0.7}}]}
    ok3, msg3 = cons.validate(w)
    check("REC ลดน้ำหนัก (set_weights) → ผ่าน", ok3 is True, msg3)
except Exception as e:
    check("consumer validate ใช้งานได้", False, repr(e))

print("\n" + ("🎉 ผ่านทั้งหมด" if not FAIL else f"⚠️ ล้มเหลว: {FAIL}"))
sys.exit(1 if FAIL else 0)
