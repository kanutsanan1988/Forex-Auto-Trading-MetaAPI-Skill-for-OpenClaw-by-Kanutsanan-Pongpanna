# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
from __future__ import annotations

import json
from datetime import datetime, timezone

import MetaTrader5 as mt5  # noqa: E402


TERMINAL_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
SYMBOL = "XAUUSD.sml"


def masked_login(login: int) -> str:
    text = str(login)
    return "*" * max(0, len(text) - 3) + text[-3:]


def namedtuple_dict(value):
    return value._asdict() if value is not None else None


def main() -> int:
    if not mt5.initialize(path=TERMINAL_PATH):
        print(json.dumps({"ok": False, "stage": "initialize", "error": mt5.last_error()}, ensure_ascii=False))
        return 1

    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        symbol = mt5.symbol_info(SYMBOL)
        if symbol is None:
            print(json.dumps({"ok": False, "stage": "symbol_info", "error": mt5.last_error()}, ensure_ascii=False))
            return 2

        if not symbol.visible and not mt5.symbol_select(SYMBOL, True):
            print(json.dumps({"ok": False, "stage": "symbol_select", "error": mt5.last_error()}, ensure_ascii=False))
            return 3

        tick = mt5.symbol_info_tick(SYMBOL)
        frames = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
        }
        bars = {}
        for name, timeframe in frames.items():
            rates = mt5.copy_rates_from_pos(SYMBOL, timeframe, 0, 5)
            bars[name] = [] if rates is None else [
                {
                    "time": datetime.fromtimestamp(int(row["time"]), tz=timezone.utc).isoformat(),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "tick_volume": int(row["tick_volume"]),
                }
                for row in rates
            ]

        payload = {
            "ok": True,
            "terminal": {
                "connected": bool(terminal.connected),
                "trade_allowed": bool(terminal.trade_allowed),
                "path": terminal.path,
            },
            "account": None if account is None else {
                "login_masked": masked_login(account.login),
                "server": account.server,
                "currency": account.currency,
                "balance": account.balance,
                "equity": account.equity,
                "margin_free": account.margin_free,
                "trade_allowed": bool(account.trade_allowed),
            },
            "symbol": {
                "name": symbol.name,
                "description": symbol.description,
                "digits": symbol.digits,
                "point": symbol.point,
                "volume_min": symbol.volume_min,
                "volume_max": symbol.volume_max,
                "volume_step": symbol.volume_step,
                "trade_contract_size": symbol.trade_contract_size,
                "trade_tick_size": symbol.trade_tick_size,
                "trade_tick_value": symbol.trade_tick_value,
            },
            "tick": namedtuple_dict(tick),
            "bars": bars,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
