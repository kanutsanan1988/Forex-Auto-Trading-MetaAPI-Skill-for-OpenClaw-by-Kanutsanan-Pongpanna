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
"""ตรวจการเชื่อมต่อ MetaAPI แบบอ่านอย่างเดียว (read-only connection check)

ใช้:  python3 scripts/metaapi_connect_check.py [--json]

จุดประสงค์: พิสูจน์ว่า "บัญชีของคุณ" เชื่อมได้จริงก่อนไปขั้นถัดไป

หลักความปลอดภัยที่บังคับในไฟล์นี้
  1. อ่าน credential จาก environment เท่านั้น (`METAAPI_TOKEN`, `METAAPI_ACCOUNT_ID`)
     — ไม่มีการอ่าน/เขียนคีย์ลงไฟล์ ไม่มีการพิมพ์ค่า secret ออกทาง output
  2. **ไม่ deploy / ไม่ undeploy บัญชี** — ถ้าบัญชีไม่ใช่ DEPLOYED จะรายงานแล้วหยุด
     (การ deploy กินค่าใช้จ่ายและเปลี่ยนสถานะบัญชี ต้องเป็นเจ้าของบัญชีตัดสินใจเอง)
  3. **ไม่ส่งคำสั่งเทรด** — ไม่เรียก order_send/close/modify ใด ๆ ทั้งสิ้น
  4. ข้อความ error จาก SDK ไม่ถูกพิมพ์ทั้งก้อน (SDK อาจสะท้อน identifier กลับมา)
     พิมพ์เฉพาะชนิดของ exception

ผลลัพธ์: JSON ที่ไม่มีข้อมูลลับ (login ถูกมาสก์, ไม่มี token)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone

TIMEOUT = 240


def _mask(value) -> str:
    text = str(value or "")
    if len(text) <= 3:
        return "*" * len(text)
    return "*" * (len(text) - 3) + text[-3:]


def _need(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(json.dumps({
            "status": "blocked_missing_credentials",
            "missing": [name],
            "how_to_fix": f'set {name} in your environment (never in a file in this package)',
        }, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    return value


async def _run(symbol: str) -> dict:
    from metaapi_cloud_sdk import MetaApi

    token = _need("METAAPI_TOKEN")
    account_id = _need("METAAPI_ACCOUNT_ID")

    result: dict = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "read_only": True,
        "order_send_called": False,
        "deploy_called": False,
        "undeploy_called": False,
    }
    api = MetaApi(token)
    connection = None
    try:
        account = await asyncio.wait_for(
            api.metatrader_account_api.get_account(account_id), 60)
        result["account_state"] = getattr(account, "state", None)
        result["account_type"] = getattr(account, "type", None)
        result["login_masked"] = _mask(getattr(account, "login", ""))

        if result["account_state"] != "DEPLOYED":
            result["status"] = "blocked_not_deployed"
            result["note"] = ("This check never deploys or undeploys an account. "
                              "Deploy it yourself in the MetaAPI dashboard, then re-run.")
            return result

        await asyncio.wait_for(account.wait_connected(), TIMEOUT)
        result["broker_connected"] = True

        connection = account.get_rpc_connection()
        await asyncio.wait_for(connection.connect(), TIMEOUT)
        await asyncio.wait_for(connection.wait_synchronized(), TIMEOUT)
        result["synchronized"] = True

        info = await asyncio.wait_for(connection.get_account_information(), 60)
        if info:
            result["account_information_received"] = True
            result["currency"] = info.get("currency")
            result["leverage"] = info.get("leverage")
            result["balance"] = info.get("balance")
            result["equity"] = info.get("equity")
            result["trade_allowed"] = bool(info.get("tradeAllowed"))

        positions = await asyncio.wait_for(connection.get_positions(), 60)
        orders = await asyncio.wait_for(connection.get_orders(), 60)
        result["positions_count"] = len(positions or [])
        result["orders_count"] = len(orders or [])

        server_time = await asyncio.wait_for(connection.get_server_time(), 60)
        result["server_time_utc"] = str((server_time or {}).get("time"))

        # หา symbol ที่ใช้ได้จริงในบัญชีนี้ (ชื่อ symbol ต่างกันได้ในแต่ละโบรกเกอร์)
        candidates = list(dict.fromkeys([symbol, "XAUUSD", "XAUUSD.sml", "GOLD"]))
        symbols: dict = {}
        for name in candidates:
            try:
                spec = await asyncio.wait_for(
                    connection.get_symbol_specification(name), 45)
                symbols[name] = ({
                    "digits": spec.get("digits"),
                    "minVolume": spec.get("minVolume"),
                    "maxVolume": spec.get("maxVolume"),
                    "volumeStep": spec.get("volumeStep"),
                    "contractSize": spec.get("contractSize"),
                    "tickSize": spec.get("tickSize"),
                } if spec else None)
            except Exception:
                symbols[name] = None
        result["symbols"] = symbols
        resolved = next((s for s in symbols if symbols[s]), None)
        result["resolved_symbol"] = resolved

        if resolved:
            tick = await asyncio.wait_for(connection.get_symbol_price(resolved), 60)
            if tick:
                result["tick"] = {"bid": tick.get("bid"), "ask": tick.get("ask")}
            try:
                # SDK signature: get_historical_candles(symbol, timeframe, start_time, limit)
                from_time = datetime.now(timezone.utc) - timedelta(days=1)
                bars = await asyncio.wait_for(
                    account.get_historical_candles(resolved, "1m", from_time, 20), 90)
                result["candles_1m_count"] = len(bars) if bars else 0
            except Exception as exc:
                result["candles_1m_count"] = f"error:{type(exc).__name__}"

        ok = bool(result.get("synchronized")
                  and result.get("account_information_received")
                  and resolved)
        result["status"] = "connected_read_only" if ok else "partial"
        if not ok:
            result["note"] = ("Connected but some checks did not complete - inspect the "
                              "fields above before trusting this account.")
        return result
    except Exception as exc:
        return {
            "status": "failed",
            "error_type": type(exc).__name__,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "read_only": True,
            "order_send_called": False,
            "deploy_called": False,
            "hint": ("Check that the token is current and that METAAPI_ACCOUNT_ID is the "
                     "MetaAPI account UUID (not the broker login). Error text is not "
                     "printed verbatim because SDK errors can echo identifiers."),
        }
    finally:
        try:
            if connection:
                await connection.close()
        except Exception:
            pass
        try:
            api.close()
        except Exception:
            pass


def main() -> int:
    ap = argparse.ArgumentParser(
        description="MetaAPI read-only connection check for Pytron Engine")
    ap.add_argument("--symbol", default=os.environ.get("METAAPI_SYMBOL") or "XAUUSD.sml",
                    help="symbol to resolve (default: XAUUSD.sml)")
    ap.add_argument("--json", action="store_true",
                    help="print JSON only (no human summary)")
    args = ap.parse_args()

    result = asyncio.run(asyncio.wait_for(_run(args.symbol), TIMEOUT + 120))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    if not args.json:
        print()
        print("=" * 68)
        print("MetaAPI read-only connection check")
        print("=" * 68)
        status = result.get("status")
        print("status        :", status)
        if status == "connected_read_only":
            print("resolved symbol:", result.get("resolved_symbol"))
            print("equity        :", result.get("equity"), result.get("currency"))
            print("positions     :", result.get("positions_count"))
            print("No order was sent. No account was deployed or undeployed.")
        else:
            print("note          :", result.get("note") or result.get("hint"))
        print("=" * 68)

    return 0 if result.get("status") == "connected_read_only" else 2


if __name__ == "__main__":
    sys.exit(main())
