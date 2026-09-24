# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""พิสูจน์ว่า "ระบบเทรดเดิม" อ่านข้อมูลจริงผ่าน MetaAPI ได้ครบวงจร

ใช้:  python3 scripts/metaapi_engine_smoke.py [--project <ที่อยู่ trading-system>] [--json]

สิ่งที่ทำ (อ่านอย่างเดียวทั้งหมด)
  1. เปิดสะพาน MetaAPI แทน MT5 (`import metaapi_mt5_shim as mt5`)
  2. ยืนยันว่า equity / symbol / เวลาเซิร์ฟเวอร์ ตรงกัน
  3. ดึงแท่งปิด M1/M5/M15/H1 แล้วสร้าง frames ด้วยโค้ดระบบจริง
  4. รัน strategy_engine.decide_market กับ frames จริง → ได้คำตัดสินของระบบ
  5. ยืนยันว่ายังเป็น read-only และไม่ได้ส่งคำสั่งใด ๆ

ทำไมต้องมีสคริปต์นี้
--------------------
การ "เชื่อมต่อได้" ยังไม่พอ — ต้องพิสูจน์ว่า **ระบบเทรดเดิม** อ่านข้อมูลผ่านสะพานได้จริง
ถ้าสะพานแปลงเวลา/แท่งผิด ระบบจะคิดว่า tick เก่า แล้วบล็อกการเทรดเงียบ ๆ
สคริปต์นี้จึงเดินผ่านเส้นทางจริงของระบบ ไม่ใช่แค่ต่อ API ได้

ไม่มีการเขียนไฟล์ใด ๆ และไม่มีการส่งคำสั่งเทรด
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
DEFAULT_PROJECT = os.path.join(PACKAGE, "trading-system")


def _prepare_env() -> None:
    """บังคับโหมดอ่านอย่างเดียว "ก่อน" import สะพาน — กันออเดอร์หลุดเกินคาดคิด"""
    os.environ["METAAPI_SHIM_READ_ONLY"] = "1"


def _safe_error_kind(value) -> str:
    """Map adapter errors to a small allowlist; never echo raw SDK text."""
    text = str(value or "").lower()
    for kind in ("TimeoutError", "NotFoundException", "UnauthorizedException",
                 "ValidationException", "InvalidArgumentException", "ConnectionError",
                 "TypeError", "AttributeError", "RuntimeError"):
        if kind.lower() in text:
            return kind
    if "no candles" in text or "no history" in text:
        return "NoHistoryAvailable"
    if "only " in text and " candles available" in text:
        return "InsufficientHistory"
    return "UnclassifiedAdapterError"


def main() -> int:
    ap = argparse.ArgumentParser(description="MetaAPI engine smoke test (read-only)")
    ap.add_argument("--project", default=os.environ.get("TRADING_PROJECT_ROOT") or DEFAULT_PROJECT,
                    help="path to the trading-system working copy")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args()

    report: dict = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "broker_order_send_called": False,
        "read_only_guard_probe_called": False,
        "deploy_called": False,
        "undeploy_called": False,
    }

    bridge = os.path.join(PACKAGE, "metaapi")
    if not os.path.isdir(bridge):
        print(json.dumps({"status": "failed", "error": "metaapi/ folder not found"},
                         ensure_ascii=False, indent=2))
        return 2
    sys.path.insert(0, bridge)

    engine = os.path.join(args.project, "outputs", "mt5_python_bridge")
    if not os.path.isdir(engine):
        print(json.dumps({
            "status": "failed",
            "error": f"engine not found at {engine}",
            "hint": "copy trading-system/ out of the skill first, then pass --project",
        }, ensure_ascii=False, indent=2))
        return 2
    sys.path.insert(0, engine)

    _prepare_env()

    stderr_note = io.StringIO()
    current_stage = "import_bridge"
    try:
        import metaapi_mt5_shim as mt5
    except Exception as exc:
        print(json.dumps({"status": "failed", "stage": "import_bridge",
                          "error_type": type(exc).__name__,
                          "hint": "pip install metaapi-cloud-sdk"}, ensure_ascii=False, indent=2))
        return 2

    report["bridge_read_only"] = bool(mt5.is_read_only())
    if not report["bridge_read_only"]:
        print(json.dumps({"status": "failed", "stage": "safety",
                          "error": "METAAPI_SHIM_READ_ONLY did not take effect"},
                         ensure_ascii=False, indent=2))
        return 2

    # ให้ระบบเทรดเดิม import MetaTrader5 ได้ตามปกติ แต่ได้สะพานแทน
    mt5.install_as_mt5()

    try:
        current_stage = "initialize"
        if not mt5.initialize():
            err = mt5.last_error()
            print(json.dumps({"status": "failed", "stage": "initialize",
                              "last_error": str(err)}, ensure_ascii=False, indent=2))
            return 2
        report["initialize"] = True

        current_stage = "read_snapshot"
        account = mt5.account_info()
        symbol_name = os.environ.get("METAAPI_SYMBOL") or "XAUUSD.sml"
        symbol = mt5.symbol_info(symbol_name)
        tick = mt5.symbol_info_tick(symbol_name)

        if account is None or symbol is None or tick is None:
            print(json.dumps({
                "status": "failed", "stage": "snapshot",
                "account": account is not None, "symbol": symbol is not None,
                "tick": tick is not None,
                "hint": "check the symbol name for YOUR broker (METAAPI_SHIM_SYMBOL_OVERRIDE / METAAPI_SYMBOL)",
            }, ensure_ascii=False, indent=2))
            return 2

        # Output only presence checks. Do not print private account values or live quotes.
        report["account_info_received"] = account is not None
        report["symbol_info_received"] = symbol is not None
        report["tick_received"] = tick is not None

        # ---- 1) ระบบเทรดเดิมอ่านแท่งเอง (เส้นทางจริง) ----
        current_stage = "market_frames"
        timeframes = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1,
        }
        report["history_bar_counts"] = {}
        report["history_error_kinds"] = {}
        for label, timeframe in timeframes.items():
            rows = mt5.copy_rates_from_pos(symbol_name, timeframe, 0, 261)
            report["history_bar_counts"][label] = len(rows) if rows is not None else 0
            if rows is None:
                report["history_error_kinds"][label] = _safe_error_kind(mt5.last_error())
        buf = io.StringIO()
        with redirect_stdout(buf):
            import market_analyzer
            frames = market_analyzer.market_frames(symbol_name)
        report["frames_built"] = sorted(frames.keys())
        # summarize_rows() คืน "ผลสรุป" ของแท่งสุดท้าย ไม่ได้คืนลิสต์ราคาทั้งหมด
        report["frames_received"] = len(frames)

        # ---- 2) ระบบเทรดเดิมตัดสินใจเอง ----
        current_stage = "strategy_decision"
        import strategy_engine
        config_path = os.path.join(engine, "auto_config.json")
        config = json.loads(io.open(config_path, encoding="utf-8").read())
        with redirect_stdout(buf):
            decision = strategy_engine.decide_market(frames, config)

        # รูปแบบคำตัดสินจริงของ decide_market():
        #   เข้าเทรด → {"side": "buy"/"sell", "strategy": ..., "confidence": ...,
        #               "stop_distance": ..., "reward_risk": ..., "reason": ...}
        #   ไม่เทรด  → {"side": None, "strategy": None/ชื่อที่ถูกสกัด, "confidence": 0.0,
        #               "reason": ...}  ← การ "ไม่เทรด" เป็นผลลัพธ์ที่ถูกต้อง ไม่ใช่ความล้มเหลว
        side = decision.get("side")
        report["decision_evaluated"] = isinstance(decision, dict)
        report["decision_has_direction"] = side is not None
        report["candidates_scored"] = len(decision.get("candidates") or [])
        report["live_enabled_in_config"] = config.get("live_enabled")
        report["strategy_router_enabled"] = bool(
            (config.get("strategy_router") or {}).get("enabled", True))

        # ---- 3) ยังอ่านอย่างเดียวอยู่ไหม ----
        current_stage = "read_only_guard_probe"
        report["still_read_only"] = bool(mt5.is_read_only())
        # Probe only the local shim's guard. In read-only mode this returns before any trade RPC.
        report["read_only_guard_probe_called"] = True
        blocked = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol_name,
                                  "volume": 0.001, "type": mt5.ORDER_TYPE_BUY})
        report["order_send_blocked"] = bool(blocked is None
                                           or getattr(blocked, "retcode", 0) != 0)

        # เกณฑ์ผ่าน: ระบบเดิมอ่านข้อมูลจริงได้ครบ 4 กรอบเวลา + ตัดสินใจได้ + ยังถูกบล็อกคำสั่ง
        ok = bool(report.get("frames_built") == ["H1", "M1", "M15", "M5"]
                  and report.get("decision_evaluated") is True
                  and report.get("candidates_scored", 0) > 0
                  and report.get("still_read_only") is True
                  and report.get("order_send_blocked") is True)
        report["status"] = "engine_ok_read_only" if ok else "partial"

        try:
            mt5.shutdown()
        except Exception:
            pass

        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        if not args.json:
            print()
            print("=" * 68)
            print("MetaAPI + engine smoke test (read-only)")
            print("=" * 68)
            print("status          :", report["status"])
            print("frames          :", ", ".join(report["frames_built"]))
            print("candidates scored:", report["candidates_scored"])
            print("decision evaluated; directional result withheld from this report")
            print("read-only guard probe: blocked locally; no broker order RPC was called")
            print("No file was written. No account was deployed. No order was sent.")
            print("=" * 68)
        return 0 if ok else 2
    except Exception as exc:
        last_error = mt5.last_error()
        print(json.dumps({
            "status": "failed", "stage": current_stage,
            "error_type": type(exc).__name__,
            "history_bar_counts": report.get("history_bar_counts"),
            "history_error_kinds": report.get("history_error_kinds"),
            "last_error_code": (last_error[0]
                                if isinstance(last_error, tuple) and last_error else None),
            "hint": "error text is deliberately not echoed verbatim",
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
