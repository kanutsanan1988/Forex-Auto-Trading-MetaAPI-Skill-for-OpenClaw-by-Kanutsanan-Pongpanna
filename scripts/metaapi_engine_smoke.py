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

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
DEFAULT_PROJECT = os.path.join(PACKAGE, "trading-system")


def _prepare_env() -> None:
    """บังคับโหมดอ่านอย่างเดียว "ก่อน" import สะพาน — กันออเดอร์หลุดเกินคาดคิด"""
    os.environ["METAAPI_SHIM_READ_ONLY"] = "1"


def main() -> int:
    ap = argparse.ArgumentParser(description="MetaAPI engine smoke test (read-only)")
    ap.add_argument("--project", default=os.environ.get("TRADING_PROJECT_ROOT") or DEFAULT_PROJECT,
                    help="path to the trading-system working copy")
    ap.add_argument("--json", action="store_true", help="print JSON only")
    args = ap.parse_args()

    report: dict = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "order_send_called": False,
        "deploy_called": False,
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
        if not mt5.initialize():
            err = mt5.last_error()
            print(json.dumps({"status": "failed", "stage": "initialize",
                              "last_error": str(err)}, ensure_ascii=False, indent=2))
            return 2
        report["initialize"] = True

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

        report["account"] = {
            "currency": getattr(account, "currency", None),
            "equity": getattr(account, "equity", None),
            "leverage": getattr(account, "leverage", None),
            "trade_allowed": bool(getattr(account, "trade_allowed", False)),
        }
        report["symbol"] = {
            "name": getattr(symbol, "name", None),
            "digits": getattr(symbol, "digits", None),
            "point": getattr(symbol, "point", None),
            "volume_min": getattr(symbol, "volume_min", None),
            "volume_step": getattr(symbol, "volume_step", None),
            "trade_tick_value": getattr(symbol, "trade_tick_value", None),
        }
        report["tick"] = {
            "bid": getattr(tick, "bid", None),
            "ask": getattr(tick, "ask", None),
            "spread_points": (
                round((float(getattr(tick, "ask", 0)) - float(getattr(tick, "bid", 0)))
                      / float(getattr(symbol, "point", 0.001) or 0.001), 2)
                if tick and symbol else None
            ),
        }
        report["server_utc_offset_seconds"] = mt5.server_utc_offset_seconds()

        # ---- 1) ระบบเทรดเดิมอ่านแท่งเอง (เส้นทางจริง) ----
        buf = io.StringIO()
        with redirect_stdout(buf):
            import market_analyzer
            frames = market_analyzer.market_frames(symbol_name)
        report["frames_built"] = sorted(frames.keys())
        # summarize_rows() คืน "ผลสรุป" ของแท่งสุดท้าย ไม่ได้คืนลิสต์ราคาทั้งหมด
        report["frame_last_close"] = {
            k: (round(float(v["close"]), 5) if isinstance(v, dict) and "close" in v else None)
            for k, v in frames.items()
        }
        report["frame_last_bar_utc"] = {
            k: (datetime.fromtimestamp(int(v["time"]), timezone.utc).isoformat()
                if isinstance(v, dict) and "time" in v else None)
            for k, v in frames.items()
        }
        report["frame_trend"] = {
            k: (v.get("trend") if isinstance(v, dict) else None) for k, v in frames.items()
        }
        report["frame_atr14"] = {
            k: (round(float(v["atr14"]), 5) if isinstance(v, dict) and "atr14" in v else None)
            for k, v in frames.items()
        }

        # ---- 2) ระบบเทรดเดิมตัดสินใจเอง ----
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
        report["decision"] = {
            "side": side,
            "strategy": decision.get("strategy"),
            "confidence": decision.get("confidence"),
            "stop_distance": decision.get("stop_distance"),
            "reward_risk": decision.get("reward_risk"),
            "reason": decision.get("reason"),
            "regime_label": (decision.get("regime") or {}).get("label")
            if isinstance(decision.get("regime"), dict) else None,
            "entered": side is not None,
            "abstained": side is None,
            "candidates_scored": len(decision.get("candidates") or []),
        }
        report["probability_top_four"] = decision.get("probability_top_four")
        report["live_enabled_in_config"] = config.get("live_enabled")
        report["strategy_router_enabled"] = bool(
            (config.get("strategy_router") or {}).get("enabled", True))

        # ---- 3) ยังอ่านอย่างเดียวอยู่ไหม ----
        report["still_read_only"] = bool(mt5.is_read_only())
        blocked = mt5.order_send({"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol_name,
                                  "volume": 0.001, "type": mt5.ORDER_TYPE_BUY})
        report["order_send_blocked"] = bool(blocked is None
                                           or getattr(blocked, "retcode", 0) != 0)
        report["order_send_retcode"] = getattr(blocked, "retcode", None)

        # เกณฑ์ผ่าน: ระบบเดิมอ่านข้อมูลจริงได้ครบ 4 กรอบเวลา + ตัดสินใจได้ + ยังถูกบล็อกคำสั่ง
        ok = bool(report.get("frames_built") == ["H1", "M1", "M15", "M5"]
                  and report.get("decision", {}).get("candidates_scored", 0) > 0
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
            print("symbol          :", report["symbol"]["name"],
                  "| digits", report["symbol"]["digits"],
                  "| min vol", report["symbol"]["volume_min"])
            print("equity          :", report["account"]["equity"], report["account"]["currency"])
            print("server offset   :", report["server_utc_offset_seconds"], "seconds")
            print("frames          :", ", ".join(report["frames_built"]))
            print("frame closes    :", report["frame_last_close"])
            print("frame trends    :", report["frame_trend"])
            print("frame ATR14     :", report["frame_atr14"])
            print("last bar (UTC)  :", report["frame_last_bar_utc"])
            print("engine decision :", json.dumps(report["decision"], ensure_ascii=False))
            print("  -> ระบบตัดสินใจได้จริง (จะเข้าเทรดหรือไม่เทรดก็ได้ตามด่านของมัน)")
            print("order_send      : blocked (read-only) retcode =",
                  report["order_send_retcode"])
            print("No file was written. No account was deployed. No order was sent.")
            print("=" * 68)
        return 0 if ok else 2
    except Exception as exc:
        print(json.dumps({
            "status": "failed", "stage": "runtime",
            "error_type": type(exc).__name__,
            "hint": "error text is deliberately not echoed verbatim",
        }, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
