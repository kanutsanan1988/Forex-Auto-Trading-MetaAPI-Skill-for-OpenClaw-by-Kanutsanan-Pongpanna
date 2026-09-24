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
"""metaapi_mt5_shim — ชั้นเชื่อม MetaAPI ที่ "เลียนแบบ API ของ MetaTrader5" ให้ทุกส่วนของระบบเทรดใช้ได้เหมือนต่อ MT5 จริง

เหตุผลที่ต้องมีชั้นนี้
---------------------
ระบบเทรดทั้งชุด (auto_trader · strategy_engine · market_analyzer · trade_guard · tools/*)
ถูกเขียนบน "สัญญา API ของแพ็กเกจ MetaTrader5" ถ้าเครื่องปลายทางไม่มี terminal MT5 (เช่น
Cowork/เซิร์ฟเวอร์ลินุกซ์ หรือผู้ใช้ที่ไม่มี Windows) ระบบจะรันไม่ได้เลย
ชั้นนี้ทำหน้าที่เป็น "อะแดปเตอร์" ให้ระบบเดิมทั้งชุดรันผ่านคลาวด์ MetaAPI ได้ **โดยไม่แก้โค้ดเทรดแม้แต่บรรทัดเดียว**

ความแม่นยำที่พิสูจน์ด้วยการทดลองจริง (2026-09-21)
------------------------------------------------
1. **เวลา (สำคัญที่สุด)** — MT5 คืนเวลาเป็น "นาฬิกาเซิร์ฟเวอร์ของโบรกเกอร์" (บัญชีทดสอบ = UTC+3)
   ส่วน MetaAPI คืนเวลาเป็น UTC จริง ถ้าไม่ชดเชย ระบบจะอ่าน tick/แท่งว่าย้อนหลัง 3 ชั่วโมง
   แล้ว `adaptive_shadow.health_check` จะตัดสินว่า "stale tick"/"stale bars" → บล็อกการเทรดทุกครั้งแบบเงียบ ๆ
   ชั้นนี้จึงแปลง label เวลาไป-กลับด้วยค่า offset ที่อ่านจาก `get_server_time()` จริงของบัญชี
   (ห้าม hardcode เด็ดขาด — แต่ละโบรกเกอร์ offset ไม่เท่ากัน และเปลี่ยนตาม DST)
2. **แท่งยังไม่ปิด** — MetaAPI `get_historical_candles()` คืนแท่งที่กำลังก่อตัวเป็นแท่งสุดท้าย
   เหมือน MT5 เป๊ะ (ทดสอบ 1m/5m/15m/1h แล้ว) จึงไม่ต้องประดิษฐ์แท่งเองและไม่ต้องเติมข้อมูลปลอม
3. **ขีดจำกัด 1000 แท่ง/ครั้ง** — ระบบขอถึง 3000 แท่ง (chart_bars) ชั้นนี้จึงโหลดแบบแบ่งหน้าให้อัตโนมัติ
4. **การตีความ datetime ขาเข้า** — MT5 ตีความ datetime ที่รับเข้าเป็น *label เวลา* เทียบกับแท่ง
   (aware → ใช้ค่า UTC instant · naive → ใช้เวลาท้องถิ่นเครื่อง) ทดลองยืนยันแล้วทั้งสองแบบ
   ชั้นนี้ใช้กติกาเดียวกัน (`int(dt.timestamp())`) เพื่อให้พฤติกรรมตรงกับ MT5 100%
5. **stdout ต้องสะอาด** — สคริปต์ระบบพ่น JSON ทาง stdout และ MetaAPI SDK พ่น log ทาง stdout
   ชั้นนี้จึงย้าย print ของ SDK ไป stderr ทั้งหมด เพื่อไม่ให้ JSON ของระบบเสียหาย

ความปลอดภัย
-----------
* อ่านคีย์จาก environment เท่านั้น: `METAAPI_TOKEN` · `METAAPI_ACCOUNT_ID`
  (ไม่มีการอ่านคีย์จากไฟล์ ไม่มีการเขียนคีย์ลงไฟล์ ไม่มีการพิมพ์ค่า secret ออกทาง output)
* **ไม่ deploy/undeploy บัญชีเอง** — ถ้าบัญชีไม่ใช่ DEPLOYED จะรายงานสถานะและปฏิเสธ
* `METAAPI_SHIM_READ_ONLY=1` → ปฏิเสธ `order_send` ทั้งหมด (ใช้ตรวจ/วิจัยโดยไม่มีความเสี่ยง)
* `METAAPI_SHIM_SYMBOL_OVERRIDE` → บังคับชื่อ symbol (เมื่อโบรกเกอร์ใช้ชื่อไม่เหมือนกัน)
* ไม่มี token/รหัสบัญชีฝังในไฟล์นี้ และไม่มีทางรั่วออกไปในข้อความ error

สัญญาโหมดของระบบ (ต้องคงไว้)
----------------------------
โหมด 1 `internal_only`      = เทรดด้วยสัญญาณภายใน (Python เท่านั้น) ไม่รัน AI Signal Bot / Admin Bot
โหมด 2 `internal_llm_join`  = เทรดร่วมสัญญาณ AI (บอทเช็คสัญญาณ + Admin Bot) — **เป็นค่าเริ่มต้นของระบบ**
ห้ามใช้ค่าตั้งต้นของชั้นนี้ไปเปิดโหมด/ปิด STOP/เปิด live แทนเจ้าของระบบ — ชั้นนี้เป็นเพียง "ประสาทสัมผัส" ไม่ใช่ "สมอง"
"""
from __future__ import annotations

import asyncio
import datetime as _dt
import math
import os
import sys
import threading
import time
import traceback
from collections import namedtuple

# ---------------------------------------------------------------------------
# ค่าคงที่ของ MT5 — คัดลอกจากแพ็กเกจ MetaTrader5 จริง (metatrader5 5.0.6090)
# ห้ามแก้ตัวเลข: โค้ดระบบเทรดเปรียบเทียบกับค่าพวกนี้ตรง ๆ
# ---------------------------------------------------------------------------
TIMEFRAME_M1 = 1
TIMEFRAME_M2 = 2
TIMEFRAME_M3 = 3
TIMEFRAME_M5 = 5
TIMEFRAME_M10 = 10
TIMEFRAME_M15 = 15
TIMEFRAME_M30 = 30
TIMEFRAME_H1 = 16385
TIMEFRAME_H4 = 16388
TIMEFRAME_D1 = 16408
TIMEFRAME_W1 = 32769
TIMEFRAME_MN1 = 49153

ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
ORDER_TYPE_BUY_LIMIT = 2
ORDER_TYPE_SELL_LIMIT = 3
ORDER_TYPE_BUY_STOP = 4
ORDER_TYPE_SELL_STOP = 5
ORDER_TYPE_CLOSE_BY = 8

POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1

DEAL_TYPE_BUY = 0
DEAL_TYPE_SELL = 1
DEAL_TYPE_BALANCE = 2

DEAL_ENTRY_IN = 0
DEAL_ENTRY_OUT = 1
DEAL_ENTRY_INOUT = 2
DEAL_ENTRY_OUT_BY = 3

TRADE_ACTION_DEAL = 1
TRADE_ACTION_PENDING = 5
TRADE_ACTION_SLTP = 6
TRADE_ACTION_MODIFY = 7
TRADE_ACTION_REMOVE = 8
TRADE_ACTION_CLOSE_BY = 10

ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2
ORDER_FILLING_BOC = 3

ORDER_TIME_GTC = 0
ORDER_TIME_DAY = 1

ORDER_STATE_STARTED = 0
ORDER_STATE_PLACED = 1
ORDER_STATE_CANCELED = 2
ORDER_STATE_PARTIAL = 3
ORDER_STATE_FILLED = 4
ORDER_STATE_REJECTED = 5

# โหมดการจับคู่ที่ symbol ยอมรับ (บิตมาสก์) — ค่าจริงจากแพ็กเกจ MetaTrader5
SYMBOL_FILLING_FOK = 1
SYMBOL_FILLING_IOC = 2
SYMBOL_FILLING_BOC = 4

SYMBOL_TRADE_MODE_DISABLED = 0
SYMBOL_TRADE_MODE_LONGONLY = 1
SYMBOL_TRADE_MODE_SHORTONLY = 2
SYMBOL_TRADE_MODE_CLOSEONLY = 3
SYMBOL_TRADE_MODE_FULL = 4

ACCOUNT_TRADE_MODE_DEMO = 0
ACCOUNT_TRADE_MODE_CONTEST = 1
ACCOUNT_TRADE_MODE_REAL = 2

TRADE_RETCODE_REQUOTE = 10004
TRADE_RETCODE_REJECT = 10006
TRADE_RETCODE_CANCEL = 10007
TRADE_RETCODE_PLACED = 10008
TRADE_RETCODE_DONE = 10009
TRADE_RETCODE_DONE_PARTIAL = 10010
TRADE_RETCODE_ERROR = 10011
TRADE_RETCODE_TIMEOUT = 10012
TRADE_RETCODE_INVALID = 10013
TRADE_RETCODE_INVALID_VOLUME = 10014
TRADE_RETCODE_INVALID_PRICE = 10015
TRADE_RETCODE_INVALID_STOPS = 10016
TRADE_RETCODE_TRADE_DISABLED = 10017
TRADE_RETCODE_MARKET_CLOSED = 10018
TRADE_RETCODE_NO_MONEY = 10019
TRADE_RETCODE_PRICE_CHANGED = 10020
TRADE_RETCODE_PRICE_OFF = 10021
TRADE_RETCODE_NO_CHANGES = 10025
TRADE_RETCODE_INVALID_FILL = 10030
TRADE_RETCODE_CONNECTION = 10031
TRADE_RETCODE_LIMIT_VOLUME = 10034
TRADE_RETCODE_INVALID_ORDER = 10035
TRADE_RETCODE_POSITION_CLOSED = 10036
TRADE_RETCODE_INVALID_CLOSE_VOLUME = 10038
TRADE_RETCODE_LIMIT_POSITIONS = 10040
TRADE_RETCODE_CLOSE_ONLY = 10044

# รหัสความสำเร็จที่ MetaAPI ใช้ตอบกลับ
_OK_NUMERIC = {0, TRADE_RETCODE_PLACED, TRADE_RETCODE_DONE, TRADE_RETCODE_DONE_PARTIAL, TRADE_RETCODE_NO_CHANGES}
_OK_STRING = {
    "ERR_NO_ERROR", "TRADE_RETCODE_PLACED", "TRADE_RETCODE_DONE",
    "TRADE_RETCODE_DONE_PARTIAL", "TRADE_RETCODE_NO_CHANGES", None, "",
}
# MetaAPI บอกชื่อ enum เป็นข้อความ ส่วนระบบเทรดใช้ตัวเลข
# เหตุผลของ position/order/deal — MetaAPI ส่งเป็นข้อความ, MT5 ใช้ตัวเลข
_POSITION_REASON_FROM_TEXT = {
    "POSITION_REASON_CLIENT": 0, "POSITION_REASON_EXPERT": 1, "POSITION_REASON_MOBILE": 2,
    "POSITION_REASON_WEB": 3, "POSITION_REASON_TP": 4, "POSITION_REASON_SL": 5, "POSITION_REASON_SO": 6,
}
_ORDER_REASON_FROM_TEXT = {
    "ORDER_REASON_CLIENT": 0, "ORDER_REASON_EXPERT": 1, "ORDER_REASON_MOBILE": 2, "ORDER_REASON_WEB": 3,
    "ORDER_REASON_SL": 4, "ORDER_REASON_TP": 5, "ORDER_REASON_SO": 6,
}
_DEAL_REASON_FROM_TEXT = {
    "DEAL_REASON_CLIENT": 0, "DEAL_REASON_EXPERT": 1, "DEAL_REASON_MOBILE": 2, "DEAL_REASON_WEB": 3,
    "DEAL_REASON_SL": 4, "DEAL_REASON_TP": 5, "DEAL_REASON_SO": 6,
}
_POSITION_TYPE_FROM_TEXT = {"POSITION_TYPE_BUY": POSITION_TYPE_BUY, "POSITION_TYPE_SELL": POSITION_TYPE_SELL}
_ORDER_TYPE_FROM_TEXT = {
    "ORDER_TYPE_BUY": ORDER_TYPE_BUY,
    "ORDER_TYPE_SELL": ORDER_TYPE_SELL,
    "ORDER_TYPE_BUY_LIMIT": ORDER_TYPE_BUY_LIMIT,
    "ORDER_TYPE_SELL_LIMIT": ORDER_TYPE_SELL_LIMIT,
    "ORDER_TYPE_BUY_STOP": ORDER_TYPE_BUY_STOP,
    "ORDER_TYPE_SELL_STOP": ORDER_TYPE_SELL_STOP,
}
_DEAL_ENTRY_FROM_TEXT = {
    "DEAL_ENTRY_IN": DEAL_ENTRY_IN,
    "DEAL_ENTRY_OUT": DEAL_ENTRY_OUT,
    "DEAL_ENTRY_INOUT": DEAL_ENTRY_INOUT,
    "DEAL_ENTRY_OUT_BY": DEAL_ENTRY_OUT_BY,
}
_DEAL_TYPE_FROM_TEXT = {"DEAL_TYPE_BUY": DEAL_TYPE_BUY, "DEAL_TYPE_SELL": DEAL_TYPE_SELL}
# Zeit: MT5 (label เวลา) → MetaAPI (UTC จริง)
_TF_TO_METAAPI = {
    TIMEFRAME_M1: ("1m", 60),
    TIMEFRAME_M2: ("2m", 120),
    TIMEFRAME_M3: ("3m", 180),
    TIMEFRAME_M5: ("5m", 300),
    TIMEFRAME_M10: ("10m", 600),
    TIMEFRAME_M15: ("15m", 900),
    TIMEFRAME_M30: ("30m", 1800),
    TIMEFRAME_H1: ("1h", 3600),
    TIMEFRAME_H4: ("4h", 14400),
    TIMEFRAME_D1: ("1d", 86400),
    TIMEFRAME_W1: ("1w", 604800),
}
_MAX_CANDLES_PER_REQUEST = 1000

def _enum_int(value, mapping=None, default=0):
    """แปลงค่า enum ที่ MetaAPI ส่งมาเป็นตัวเลขแบบ MT5

    MetaAPI ส่ง enum เป็น "ข้อความ" (เช่น POSITION_TYPE_BUY / DEAL_ENTRY_OUT / POSITION_REASON_CLIENT)
    แต่โค้ดระบบเทรดเปรียบเทียบกับตัวเลขของ MT5 จึงต้องแปลงให้ตรง
    ตัวเลขที่ส่งมาตรง ๆ ก็รับได้ (ทนทั้งสองรูปแบบ) · ค่าที่ไม่รู้จัก → default (ห้ามเดา)
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if value is None:
        return default
    text_value = str(value).strip()
    if not text_value:
        return default
    if text_value.lstrip("+-").isdigit():
        return int(text_value)
    if mapping and text_value in mapping:
        return int(mapping[text_value])
    return default

# MetaAPI ส่ง enum ของ symbol เป็น "ข้อความ" ไม่ใช่ตัวเลข (ทดลองจริง 2026-09-21)
# ถ้าไม่แปลง ระบบจะได้ค่า 0 แล้วเข้าใจผิดว่า "เทรดไม่ได้" → ต้องแปลงให้ตรงกับ MT5
def _filling_mode_bits(value) -> int:
    """แปลง fillingModes ของ MetaAPI (list ของข้อความ) → บิตมาสก์แบบ MT5

    MT5 บอก "โหมดที่ symbol ยอมรับ" เป็นบิต (SYMBOL_FILLING_FOK=1, IOC=2)
    MetaAPI ส่งมาเป็น list เช่น ["ORDER_FILLING_FOK", "ORDER_FILLING_IOC"]
    ระบบเดิมอ่านค่านี้ไม่ได้ (MetaAPI ไม่มีฟิลด์ตรง ๆ) จึงประกอบให้ตรงความหมาย
    """
    if value is None:
        return 0
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return int(value)
    items = value if isinstance(value, (list, tuple, set)) else [value]
    bits = 0
    for item in items:
        bits |= int(_SYMBOL_FILLING_MODE_FROM_TEXT.get(str(item).strip(), 0))
    return bits


_SYMBOL_TRADE_MODE_FROM_TEXT = {
    "SYMBOL_TRADE_MODE_DISABLED": SYMBOL_TRADE_MODE_DISABLED,
    "SYMBOL_TRADE_MODE_LONGONLY": SYMBOL_TRADE_MODE_LONGONLY,
    "SYMBOL_TRADE_MODE_SHORTONLY": SYMBOL_TRADE_MODE_SHORTONLY,
    "SYMBOL_TRADE_MODE_CLOSEONLY": SYMBOL_TRADE_MODE_CLOSEONLY,
    "SYMBOL_TRADE_MODE_FULL": SYMBOL_TRADE_MODE_FULL,
}
_SYMBOL_CALC_MODE_FROM_TEXT = {
    "SYMBOL_CALC_MODE_FOREX": 0,
    "SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE": 1,
    "SYMBOL_CALC_MODE_FUTURES": 2,
    "SYMBOL_CALC_MODE_CFD": 3,
    "SYMBOL_CALC_MODE_CFDINDEX": 4,
    "SYMBOL_CALC_MODE_CFDLEVERAGE": 5,
    "SYMBOL_CALC_MODE_EXCH_STOCKS": 32,
    "SYMBOL_CALC_MODE_EXCH_FUTURES": 33,
}
_SYMBOL_SWAP_MODE_FROM_TEXT = {
    "SYMBOL_SWAP_MODE_DISABLED": 0, "SYMBOL_SWAP_MODE_POINTS": 1,
    "SYMBOL_SWAP_MODE_CURRENCY_SYMBOL": 2, "SYMBOL_SWAP_MODE_INTEREST_CURRENT": 3,
    "SYMBOL_SWAP_MODE_INTEREST_OPEN": 4, "SYMBOL_SWAP_MODE_REOPEN_CURRENT": 5,
    "SYMBOL_SWAP_MODE_REOPEN_BID": 6,
}
_SYMBOL_EXECUTION_MODE_FROM_TEXT = {
    "SYMBOL_TRADE_EXECUTION_REQUEST": 0, "SYMBOL_TRADE_EXECUTION_INSTANT": 1,
    "SYMBOL_TRADE_EXECUTION_MARKET": 2, "SYMBOL_TRADE_EXECUTION_EXCHANGE": 3,
}
_SYMBOL_FILLING_MODE_FROM_TEXT = {
    "SYMBOL_FILLING_FOK": SYMBOL_FILLING_FOK,
    "SYMBOL_FILLING_IOC": SYMBOL_FILLING_IOC,
    "ORDER_FILLING_FOK": SYMBOL_FILLING_FOK,
    "ORDER_FILLING_IOC": SYMBOL_FILLING_IOC,
}
_ACCOUNT_MARGIN_MODE_FROM_TEXT = {
    "ACCOUNT_MARGIN_MODE_RETAIL_NETTING": 0, "ACCOUNT_MARGIN_MODE_EXCHANGE": 1,
    "ACCOUNT_MARGIN_MODE_RETAIL_HEDGING": 2,
}
_ACCOUNT_TRADE_MODE_FROM_TEXT = {
    "ACCOUNT_TRADE_MODE_DEMO": ACCOUNT_TRADE_MODE_DEMO,
    "ACCOUNT_TRADE_MODE_CONTEST": ACCOUNT_TRADE_MODE_CONTEST,
    "ACCOUNT_TRADE_MODE_REAL": ACCOUNT_TRADE_MODE_REAL,
}


# dtype ของแท่ง — เหมือน MetaTrader5 ทุกตัวอักษร (ระบบใช้ row["time"], float(row["close"]), rates[-2]["time"])
_RATE_DTYPE = [
    ("time", "<i8"),
    ("open", "<f8"),
    ("high", "<f8"),
    ("low", "<f8"),
    ("close", "<f8"),
    ("tick_volume", "<u8"),
    ("spread", "<i4"),
    ("real_volume", "<u8"),
]

# ---------------------------------------------------------------------------
# โครงสร้างข้อมูล — ชื่อฟิลด์/ลำดับ ตรงกับแพ็กเกจ MetaTrader5 จริงทุกตัว
# (ดึงจากไฟล์ไบนารีของ metatrader5 5.0.6090 เพื่อให้โค้ดที่อ่านฟิลด์ทำงานเหมือนเดิม)
# ---------------------------------------------------------------------------
Tick = namedtuple("Tick", "time bid ask last volume time_msc flags volume_real")

TradePosition = namedtuple(
    "TradePosition",
    "ticket time time_msc time_update time_update_msc type magic identifier reason volume "
    "price_open sl tp price_current swap profit symbol comment external_id",
)

TradeDeal = namedtuple(
    "TradeDeal",
    "ticket order time time_msc type entry magic position_id reason volume price "
    "commission swap profit fee symbol comment external_id",
)

TradeOrder = namedtuple(
    "TradeOrder",
    "ticket time_setup time_setup_msc time_done time_done_msc time_expiration type type_time "
    "type_filling state magic position_id position_by_id reason volume_initial volume_current "
    "price_open sl tp price_current price_stoplimit symbol comment external_id",
)

OrderCheckResult = namedtuple(
    "OrderCheckResult", "retcode balance equity profit margin margin_free margin_level comment request"
)

OrderSendResult = namedtuple(
    "OrderSendResult",
    "retcode deal order volume price bid ask comment request_id retcode_external request",
)

TerminalInfo = namedtuple(
    "TerminalInfo",
    "community_account community_connection connected dlls_allowed trade_allowed tradeapi_disabled "
    "email_enabled ftp_enabled notifications_enabled mqid build maxbars codepage ping_last "
    "community_balance retransmission company name language path data_path commondata_path",
)

AccountInfo = namedtuple(
    "AccountInfo",
    "login trade_mode leverage limit_orders margin_so_mode trade_allowed trade_expert margin_mode "
    "currency_digits fifo_close balance credit profit equity margin margin_free margin_level "
    "margin_so_call margin_so_so margin_initial margin_maintenance assets liabilities "
    "commission_blocked name server currency company",
)

SymbolInfo = namedtuple(
    "SymbolInfo",
    "custom chart_mode select visible session_deals session_buy_orders session_sell_orders volume "
    "volumehigh volumelow time digits spread spread_float ticks_bookdepth trade_calc_mode trade_mode "
    "start_time expiration_time trade_stops_level trade_freeze_level trade_exemode swap_mode "
    "swap_rollover3days margin_hedged_use_leg expiration_mode filling_mode order_mode order_gtc_mode "
    "option_mode option_right bid bidhigh bidlow ask askhigh asklow last lasthigh lastlow volume_real "
    "volumehigh_real volumelow_real option_strike point trade_tick_value trade_tick_value_profit "
    "trade_tick_value_loss trade_tick_size trade_contract_size trade_accrued_interest trade_face_value "
    "trade_liquidity_rate volume_min volume_max volume_step volume_limit swap_long swap_short "
    "margin_initial margin_maintenance session_volume session_turnover session_interest "
    "session_buy_orders_volume session_sell_orders_volume session_open session_close session_aw "
    "session_price_settlement session_price_limit_min session_price_limit_max margin_hedged "
    "price_change price_volatility price_theoretical price_greeks_delta price_greeks_theta "
    "price_greeks_gamma price_greeks_vega price_greeks_rho price_greeks_omega price_sensitivity basis "
    "category currency_base currency_profit currency_margin bank description exchange formula isin "
    "name page path",
)


# ---------------------------------------------------------------------------
# การเชื่อมต่อ MetaAPI — ทำงานแบบ async จึงต้องมี event loop เบื้องหลัง
# ---------------------------------------------------------------------------
async def _call_sync(fn):
    """เรียกฟังก์ชัน synchronous ข้างใน coroutine เพื่อให้ได้ event loop ที่กำลังรัน"""
    return fn()


class _AsyncRail:
    """ราง async เบื้องหลัง: ให้ API แบบ synchronous ของ MT5 เรียก MetaAPI ที่เป็น async ได้"""

    def __init__(self) -> None:
        self._loop = None
        self._thread = None
        self._guard = threading.Lock()

    def _ensure(self):
        with self._guard:
            if self._loop is None or self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                self._thread = threading.Thread(
                    target=self._loop.run_forever, name="metaapi-rail", daemon=True
                )
                self._thread.start()
            return self._loop

    def run(self, coro, timeout: float | None = None):
        future = asyncio.run_coroutine_threadsafe(coro, self._ensure())
        return future.result(timeout)

    def run_in_loop(self, fn, timeout: float | None = None):
        """สร้างออบเจกต์ที่ต้องมี "event loop กำลังรัน" อยู่ (เช่น MetaApi())

        MetaApi.__init__ เรียก asyncio.create_task ภายใน จึงสร้างนอก loop ไม่ได้
        (ได้ RuntimeError: no running event loop) — ต้องสร้างในเธรดของรางนี้เท่านั้น
        """
        loop = self._ensure()
        return asyncio.run_coroutine_threadsafe(
            _call_sync(fn), loop).result(timeout)


def _route_sdk_logs_to_stderr() -> None:
    """ย้าย log ของ MetaAPI SDK ไป stderr

    เหตุผล: สคริปต์ของระบบพ่น JSON ทาง stdout (mt5_probe · market_analyzer · trade_guard · live_executor)
    ถ้า log ของ SDK ปนออก stdout เครื่องมืออ่าน JSON จะพังทันที
    """
    try:
        from metaapi_cloud_sdk import logger as sdk_logger
    except Exception:
        return

    def _log(self, level, msg, args=None, exc_info=None, extra=None, stack_info=None, stacklevel=None):
        try:
            if callable(msg):
                msg = msg()
            text = str(msg)
            if args:
                try:
                    text = text % args
                except Exception:
                    text = f"{text} {args}"
        except Exception:
            text = "<metaapi log>"
        try:
            sys.stderr.write(f"[metaapi] {level} {text}\n")
            sys.stderr.flush()
        except Exception:
            pass

    sdk_logger.NativeLogger._log = _log


def _pick(data: dict, *names, default=None):
    """อ่านค่าจาก dict ที่อาจใช้ชื่อคีย์ต่างสำเนียงกัน (MetaAPI camelCase / MT5 snake_case)

    เช่น มาร์จินว่างมีได้ทั้ง `freeMargin` (MetaAPI) และ `margin_free` (MT5)
    ถ้าดูผิดชื่อจะได้ 0 แล้วตัดสิน "เงินไม่พอ" ผิด — เคยเป็นบั๊กจริงมาแล้ว
    """
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return default


def _as_plain(obj) -> dict:
    """แปลงออบเจกต์ MetaAPI (dict / namedtuple / dataclass) เป็น dict ธรรมดา

    ⚠️ namedtuple ไม่มี __dict__ ที่ใช้ได้ (ได้แต่ _fields) จึงต้องเรียก _asdict()
    ก่อนเสมอ ไม่งั้นค่าอย่าง freeMargin จะกลายเป็น 0 แล้วตัดสิน "เงินไม่พอ" ผิด
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    asdict = getattr(obj, "_asdict", None)
    if callable(asdict):
        try:
            return dict(asdict())
        except Exception:
            pass
    if hasattr(obj, "__dict__") and getattr(obj, "__dict__"):
        return dict(getattr(obj, "__dict__"))
    try:
        return dict(obj)
    except Exception:
        return {}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on", "y")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except Exception:
        return default


def _alias_map() -> dict:
    """แผนที่ชื่อ symbol: รองรับกรณีโบรกเกอร์ตั้งชื่อไม่เหมือนกัน เช่น XAUUSD.sml → XAUUSD"""
    raw = os.environ.get("METAAPI_SYMBOL_ALIASES") or ""
    result = {}
    for piece in raw.replace(";", ",").split(","):
        piece = piece.strip()
        if "=" in piece:
            source, target = piece.split("=", 1)
            if source.strip() and target.strip():
                result[source.strip()] = target.strip()
    return result


class MetaApiMt5Shim:
    """ตัวเชื่อมเดียวที่ถือการเชื่อมต่อ MetaAPI และให้ API เหมือนแพ็กเกจ MetaTrader5

    ใช้ `import metaapi_mt5_shim as mt5` แทน `import MetaTrader5 as mt5`
    (หรือตั้ง `METAAPI_SHIM_AUTOLOAD=1` ให้ตัวติดตั้งสำเร็จรูปทำ alias ให้อัตโนมัติ)
    """

    def __init__(self) -> None:
        self._rail = _AsyncRail()
        self._api = None
        self._account = None
        self._conn = None
        self._account_id = ""
        self._connected = False
        self._last_error = (0, "no error")
        self._terminal = None
        self._account_info_cache = None
        self._server_offset_seconds = None
        self._ticks_cache = {}
        self._alias = _alias_map()
        self.read_only = _env_flag("METAAPI_SHIM_READ_ONLY", False)
        self.timeout_seconds = _env_float("METAAPI_SHIM_TIMEOUT", 120.0)
        self._log = _env_flag("METAAPI_SHIM_VERBOSE", False)

    # ------------------------------------------------------------------
    # เครื่องมือภายใน
    # ------------------------------------------------------------------
    def _say(self, message: str) -> None:
        if self._log:
            sys.stderr.write(f"[shim] {message}\n")
            sys.stderr.flush()

    def _set_error(self, code: int, message: str) -> None:
        self._last_error = (int(code), str(message))
        self._say(f"error {code}: {message}")

    def _credentials(self) -> tuple[str, str]:
        token = os.environ.get("METAAPI_TOKEN")
        account_id = os.environ.get("METAAPI_ACCOUNT_ID")
        missing = [name for name, value in
                   (("METAAPI_TOKEN", token), ("METAAPI_ACCOUNT_ID", account_id)) if not value]
        if missing:
            raise RuntimeError(
                "Missing MetaAPI credential(s): " + ", ".join(missing)
                + " - ตั้งค่าใน environment เท่านั้น (ห้ามเขียนลงไฟล์หรือส่งต่อให้ผู้อื่น)"
            )
        return token, account_id

    def _symbol_for_broker(self, symbol: str | None) -> str:
        """ชื่อ symbol ฝั่งโบรกเกอร์ (รองรับ alias และการบังคับด้วย env)"""
        name = str(symbol or "")
        forced = os.environ.get("METAAPI_SHIM_SYMBOL_OVERRIDE")
        if forced:
            return forced
        return self._alias.get(name, name)

    def _refresh_offset(self) -> int:
        """อ่าน offset ระหว่าง "นาฬิกาเซิร์ฟเวอร์โบรก" กับ UTC จาก get_server_time() จริง

        MT5 ให้เวลาเป็นนาฬิกาโบรกเกอร์ ส่วน MetaAPI ให้ UTC ดังนั้นต้องมีค่านี้เพื่อแปลงไป-กลับ
        ห้าม hardcode — offset ต่างกันตามโบรกเกอร์และเปลี่ยนตาม DST (ทดลองจริง: บัญชีนี้ = +3 ชม.)
        """
        if self._server_offset_seconds is not None:
            return self._server_offset_seconds
        forced = os.environ.get("METAAPI_SHIM_SERVER_UTC_OFFSET")
        if forced:
            hours = float(forced)
            self._server_offset_seconds = int(round(hours * 3600.0))
            return self._server_offset_seconds
        try:
            raw = self._rail.run(self._conn.get_server_time(), self.timeout_seconds)
            data = _as_plain(raw)
            server_dt = data.get("time")
            broker_text = str(data.get("brokerTime") or "")
            if isinstance(server_dt, _dt.datetime) and broker_text:
                broker_dt = _dt.datetime.strptime(broker_text.strip()[:19], "%Y-%m-%d %H:%M:%S")
                if server_dt.tzinfo is None:
                    server_dt = server_dt.replace(tzinfo=_dt.timezone.utc)
                delta = (broker_dt - server_dt.astimezone(_dt.timezone.utc).replace(tzinfo=None))
                offset = int(round(delta.total_seconds() / 900.0)) * 900   # ปัดเป็น 15 นาที
                if -43200 <= offset <= 50400:
                    self._server_offset_seconds = offset
                    self._say(f"server offset = {offset} วินาที ({offset / 3600.0:+.2f} ชม.)")
                    return offset
        except Exception as exc:
            self._say(f"อ่าน server offset ไม่ได้ ({type(exc).__name__}); ใช้ UTC เป็นฐาน")
        self._server_offset_seconds = 0
        return 0

    def _label_number(self, value: object) -> float:
        """แปลงค่าที่ส่งเข้ามาเป็น "เลข label เวลา" แบบเดียวกับที่ MT5 ใช้

        MT5 ตีความ datetime ที่ naive เป็นเวลาท้องถิ่นของเครื่อง และ aware เป็นค่าสัมบูรณ์
        ทดลองยืนยันกับ MT5 จริงแล้วทั้งสองแบบ (2026-09-21) จึงต้องคงกติกานี้ไว้ให้เหมือน
        """
        if isinstance(value, _dt.datetime):
            return float(value.timestamp())     # naive → local · aware → absolute (Python จัดการให้)
        return float(value)

    def _query_instant(self, value: object) -> _dt.datetime:
        """เลข label (นาฬิกาโบรกเกอร์) → เวลาจริง UTC สำหรับส่งให้ MetaAPI

        label = UTC จริง + offset  →  UTC จริง = label - offset
        ต้องคืนค่าเป็น aware-UTC เท่านั้น เพราะ SDK จะ astimezone(utc) ให้ (naive จะถูกตีเป็นเวลาท้องถิ่น)
        """
        seconds = self._label_number(value) - self._refresh_offset()
        return _dt.datetime.fromtimestamp(seconds, _dt.timezone.utc)

    # ------------------------------------------------------------------
    # วัฏจักรชีวิตของการเชื่อมต่อ
    # ------------------------------------------------------------------
    def initialize(self, path=None, login=None, password=None, server=None, timeout=None, portable=False, **kwargs):
        """เปิดเส้นทาง MetaAPI (แทนการเปิด terminal MT5)

        รับ `path`/`login`/`password`/`server` ไว้เพื่อให้โค้ดเดิมที่ส่ง `path=TERMINAL` เรียกได้
        โดยไม่ต้องแก้โค้ด — ค่าเหล่านี้ไม่ถูกใช้ (MetaAPI เชื่อมผ่านคลาวด์)
        """
        if self._connected:
            return True
        try:
            _route_sdk_logs_to_stderr()
            from metaapi_cloud_sdk import MetaApi

            token, account_id = self._credentials()
            self._account_id = account_id
            # MetaApi() ต้องถูกสร้าง "ในราง" เพราะ __init__ เรียก asyncio.create_task
            self._api = self._rail.run_in_loop(lambda: MetaApi(token), 60.0)
            self._account = self._rail.run(
                self._api.metatrader_account_api.get_account(account_id), 90.0)

            state = str(getattr(self._account, "state", "") or "")
            if state != "DEPLOYED":
                # ห้าม deploy เอง: การ deploy เปลี่ยนสถานะบัญชีจริงและกินค่าใช้จ่าย
                self._set_error(
                    1001,
                    f'MetaAPI account state is "{state}" (ต้องเป็น DEPLOYED). '
                    "ชั้นนี้ไม่ deploy ให้เอง — เจ้าของบัญชีต้องเปิดเองในแดชบอร์ด MetaAPI",
                )
                return False

            self._rail.run(self._account.wait_connected(), self.timeout_seconds + 180.0)
            self._conn = self._account.get_rpc_connection()
            self._rail.run(self._conn.connect(), self.timeout_seconds + 180.0)
            self._rail.run(self._conn.wait_synchronized(), self.timeout_seconds + 180.0)

            self._account_info_cache = self._rail.run(
                self._conn.get_account_information(), self.timeout_seconds)
            info = self._account_info_cache or {}
            info_dict = _as_plain(info)

            self._terminal = TerminalInfo(
                community_account=False, community_connection=False,
                connected=True,
                dlls_allowed=False,
                trade_allowed=bool(info_dict.get("tradeAllowed", False)),
                tradeapi_disabled=False, email_enabled=False, ftp_enabled=False,
                notifications_enabled=False, mqid=False, build=0, maxbars=0, codepage=65001,
                ping_last=0, community_balance=0.0, retransmission=0,
                company=str(info_dict.get("broker") or "MetaAPI"),
                name=str(info_dict.get("server") or "MetaAPI"),
                language="", path="metaapi-cloud", data_path="metaapi-cloud",
                commondata_path="metaapi-cloud",
            )
            self._refresh_offset()
            self._connected = True
            self._set_error(1, "MetaAPI connection established")
            self._say(f"เชื่อม MetaAPI สำเร็จ (account state={state})")
            return True
        except Exception as exc:
            self._set_error(1000, f"initialize failed: {type(exc).__name__}: {exc}")
            self._safe_close()
            return False

    def _safe_close(self) -> None:
        try:
            if self._conn is not None:
                self._rail.run(self._conn.close(), 30.0)
        except Exception:
            pass
        try:
            if self._api is not None:
                # close() ก็เรียก asyncio.create_task ภายใน → ต้องปิดในราง
                self._rail.run_in_loop(self._api.close, 30.0)
        except Exception:
            pass
        self._conn = None
        self._account = None
        self._api = None
        self._connected = False

    def shutdown(self):
        """ปิดการเชื่อมต่อ (คืนค่า None เหมือน MT5)"""
        self._safe_close()
        self._account_info_cache = None
        self._server_offset_seconds = None
        self._ticks_cache = {}
        return None

    def version(self):
        try:
            from metaapi_cloud_sdk import MetaApi  # noqa: F401
            return (5, 0, "metaapi")
        except Exception:
            return (5, 0, "unknown")

    def last_error(self):
        return self._last_error

    def _require_connection(self):
        if not self._connected or self._conn is None:
            raise RuntimeError("MetaAPI is not initialized - เรียก initialize() ก่อน")

    # ------------------------------------------------------------------
    # ข้อมูลบัญชีและเทอร์มินัล
    # ------------------------------------------------------------------
    def terminal_info(self):
        if not self._connected:
            self._set_error(1002, "terminal_info called before initialize")
            return None
        return self._terminal

    def account_info(self):
        try:
            self._require_connection()
            info = self._rail.run(
                self._conn.get_account_information(), self.timeout_seconds)
            self._account_info_cache = info
            data = _as_plain(info)
            self._set_error(1, "ok")
            return AccountInfo(
                login=int(data.get("login") or 0),
                trade_mode=_enum_int(data.get("type") or data.get("tradeMode"),
                                      _ACCOUNT_TRADE_MODE_FROM_TEXT, ACCOUNT_TRADE_MODE_REAL),
                leverage=int(data.get("leverage") or 0),
                limit_orders=0,
                margin_so_mode=0,
                trade_allowed=bool(data.get("tradeAllowed", False)),
                trade_expert=bool(data.get("tradeAllowed", False)),
                margin_mode=_enum_int(data.get("marginMode"),
                                       _ACCOUNT_MARGIN_MODE_FROM_TEXT, 0),
                currency_digits=2,
                fifo_close=False,
                balance=float(data.get("balance") or 0.0),
                credit=float(data.get("credit") or 0.0),
                profit=round(float(data.get("equity") or 0.0) - float(data.get("balance") or 0.0), 8),
                equity=float(data.get("equity") or 0.0),
                margin=float(data.get("margin") or 0.0),
                margin_free=float(data.get("freeMargin") or 0.0),
                margin_level=float(data.get("marginLevel") or 0.0),
                margin_so_call=0.0, margin_so_so=0.0, margin_initial=0.0, margin_maintenance=0.0,
                assets=0.0, liabilities=0.0, commission_blocked=0.0,
                name=str(data.get("name") or ""),
                server=str(data.get("server") or ""),
                currency=str(data.get("currency") or "USD"),
                company=str(data.get("broker") or ""),
            )
        except Exception as exc:
            self._set_error(1002, f"account_info failed: {type(exc).__name__}: {exc}")
            return None

    # ------------------------------------------------------------------
    # symbol
    # ------------------------------------------------------------------
    def symbol_select(self, symbol, enable=True):
        """MetaAPI ไม่มีแนวคิด "เลือก symbol ใน Market Watch" — ถือว่าเลือกแล้วเสมอ"""
        try:
            self._require_connection()
            self._set_error(1, "ok")
            return True
        except Exception as exc:
            self._set_error(1002, f"symbol_select failed: {type(exc).__name__}: {exc}")
            return False

    def symbol_info(self, symbol):
        try:
            self._require_connection()
            broker_symbol = self._symbol_for_broker(symbol)
            spec = self._rail.run(
                self._conn.get_symbol_specification(broker_symbol), self.timeout_seconds)
            data = _as_plain(spec)
            if not data:
                self._set_error(4301, f"symbol not found: {symbol}")
                return None
            tick_size = float(data.get("tickSize") or 0.0)
            digits = int(data.get("digits") or 0)
            # MetaAPI ไม่ส่ง tick value มาในสเปก symbol — ต้องถามราคาสด (profitTickValue)
            # ถ้าปล่อยเป็น 0.0 ระบบจะคำนวณเงินต่อจุด (dollars_per_price_unit) ผิดเป็นศูนย์
            tick_value_live = 0.0
            tick_value_loss_live = 0.0
            try:
                live = _as_plain(self._rail.run(
                    self._conn.get_symbol_price(broker_symbol, keep_subscription=True),
                    self.timeout_seconds))
                tick_value_live = float(live.get("profitTickValue") or 0.0)
                tick_value_loss_live = float(live.get("lossTickValue") or 0.0)
            except Exception:
                pass
            point = float(data.get("point") or (tick_size if tick_size > 0 else 10 ** (-digits if digits else 0)))
            self._set_error(1, "ok")
            return SymbolInfo(
                custom=False, chart_mode=0, select=True, visible=True,
                session_deals=0, session_buy_orders=0, session_sell_orders=0, volume=0,
                volumehigh=0, volumelow=0, time=0, digits=digits,
                spread=0, spread_float=True, ticks_bookdepth=0,
                trade_calc_mode=_enum_int(data.get("priceCalculationMode"),
                                          _SYMBOL_CALC_MODE_FROM_TEXT, 0),
                trade_mode=_enum_int(data.get("tradeMode"), _SYMBOL_TRADE_MODE_FROM_TEXT, 0),
                start_time=0, expiration_time=0,
                trade_stops_level=int(data.get("stopsLevel") or 0),
                trade_freeze_level=int(data.get("freezeLevel") or 0),
                trade_exemode=_enum_int(data.get("executionMode"),
                                        _SYMBOL_EXECUTION_MODE_FROM_TEXT, 0),
                swap_mode=_enum_int(data.get("swapMode"), _SYMBOL_SWAP_MODE_FROM_TEXT, 0),
                swap_rollover3days=0, margin_hedged_use_leg=False,
                expiration_mode=0,
                filling_mode=_filling_mode_bits(data.get("fillingModes")),
                order_mode=0, order_gtc_mode=0,
                option_mode=0, option_right=0,
                bid=0.0, bidhigh=0.0, bidlow=0.0, ask=0.0, askhigh=0.0, asklow=0.0,
                last=0.0, lasthigh=0.0, lastlow=0.0, volume_real=0.0,
                volumehigh_real=0.0, volumelow_real=0.0, option_strike=0.0,
                point=point,
                trade_tick_value=tick_value_live or tick_value_loss_live,
                trade_tick_value_profit=tick_value_live,
                trade_tick_value_loss=tick_value_loss_live,
                trade_tick_size=tick_size,
                trade_contract_size=float(data.get("contractSize") or 0.0),
                trade_accrued_interest=0.0, trade_face_value=0.0, trade_liquidity_rate=0.0,
                volume_min=float(data.get("minVolume") or 0.0),
                volume_max=float(data.get("maxVolume") or 0.0),
                volume_step=float(data.get("volumeStep") or 0.0),
                volume_limit=0.0,
                swap_long=float(data.get("swapLong") or 0.0),
                swap_short=float(data.get("swapShort") or 0.0),
                margin_initial=float(data.get("initialMargin") or 0.0),
                margin_maintenance=float(data.get("maintenanceMargin") or 0.0),
                session_volume=0, session_turnover=0.0, session_interest=0.0,
                session_buy_orders_volume=0, session_sell_orders_volume=0,
                session_open=0.0, session_close=0.0, session_aw=0.0,
                session_price_settlement=0.0, session_price_limit_min=0.0, session_price_limit_max=0.0,
                margin_hedged=0.0, price_change=0.0, price_volatility=0.0, price_theoretical=0.0,
                price_greeks_delta=0.0, price_greeks_theta=0.0, price_greeks_gamma=0.0,
                price_greeks_vega=0.0, price_greeks_rho=0.0, price_greeks_omega=0.0,
                price_sensitivity=0.0, basis=0.0,
                category=str(data.get("category") or ""),
                currency_base=str(data.get("baseCurrency") or ""),
                currency_profit=str(data.get("profitCurrency") or ""),
                currency_margin=str(data.get("marginCurrency") or ""),
                bank="", description=str(data.get("description") or ""),
                exchange="", formula="", isin="",
                name=str(data.get("symbol") or broker_symbol),
                page="", path=str(data.get("path") or ""),
            )
        except Exception as exc:
            self._set_error(4301, f"symbol_info failed: {type(exc).__name__}: {exc}")
            return None

    def symbol_info_tick(self, symbol):
        """tick ล่าสุด — คืนเวลาเป็น label เซิร์ฟเวอร์เหมือน MT5 (สำคัญต่อ health_check)"""
        try:
            self._require_connection()
            broker_symbol = self._symbol_for_broker(symbol)
            price = self._rail.run(
                self._conn.get_symbol_price(broker_symbol, keep_subscription=True),
                self.timeout_seconds)
            data = _as_plain(price)
            if not data or data.get("bid") is None:
                self._set_error(4302, f"no tick for {symbol}")
                return None
            offset = self._refresh_offset()
            stamp = data.get("time")
            if isinstance(stamp, _dt.datetime):
                seconds = stamp.timestamp() if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc).timestamp()
            elif stamp is not None:
                seconds = float(stamp)
            else:
                seconds = time.time()
            label = int(seconds + offset)
            self._set_error(1, "ok")
            return Tick(time=label, bid=float(data["bid"]), ask=float(data["ask"]),
                        last=float(data.get("last") or 0.0), volume=int(data.get("volume") or 0),
                        time_msc=label * 1000, flags=0, volume_real=float(data.get("volume") or 0.0))
        except Exception as exc:
            self._set_error(4302, f"symbol_info_tick failed: {type(exc).__name__}: {exc}")
            return None

    # ------------------------------------------------------------------
    # แท่งราคา (rates) — คืน numpy structured array เหมือน MetaTrader5 ทุกประการ
    # ------------------------------------------------------------------
    def _dtype(self):
        import numpy
        return numpy.dtype(_RATE_DTYPE)

    def _candles_to_array(self, candles, timeframe):
        """แปลงแท่งจาก MetaAPI → numpy array แบบ MT5

        * `time` = label เวลาเซิร์ฟเวอร์ (บวก offset ที่อ่านจากบัญชีจริง) เหมือน MT5
        * เรียงเก่า → ใหม่ เหมือน MT5
        * แท่งสุดท้ายอาจยังไม่ปิด เหมือน MT5 (พิสูจน์แล้วทั้ง 1m/5m/15m/1h)
        """
        import numpy
        if not candles:
            return numpy.empty(0, dtype=self._dtype())
        tf_seconds = _TF_TO_METAAPI.get(timeframe, (None, 60))[1]
        offset = self._refresh_offset()
        rows = []
        for candle in candles:
            data = _as_plain(candle)
            stamp = data.get("time")
            if isinstance(stamp, _dt.datetime):
                seconds = stamp.timestamp() if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc).timestamp()
            elif stamp is not None:
                seconds = float(stamp)
            else:
                continue
            rows.append((
                int(round(seconds)) + offset,
                float(data.get("open") or 0.0),
                float(data.get("high") or 0.0),
                float(data.get("low") or 0.0),
                float(data.get("close") or 0.0),
                int(data.get("tickVolume") or 0),
                int(round(float(data.get("spread") or 0.0))),   # MetaAPI นับเป็น point แล้ว (เท่ากับ MT5)
                int(float(data.get("volume") or 0.0)),
            ))
        rows.sort(key=lambda row: row[0])
        return numpy.array(rows, dtype=self._dtype())

    def _fetch_candles(self, timeframe, symbol, start_utc, limit):
        """โหลดแท่งย้อนหลังจาก MetaAPI (จำกัด 1000/ครั้ง จึงแบ่งหน้าให้อัตโนมัติ)"""
        tf_name = _TF_TO_METAAPI.get(timeframe, (None, None))[0]
        if tf_name is None:
            raise ValueError(f"unsupported timeframe: {timeframe}")
        broker_symbol = self._symbol_for_broker(symbol)
        collected = []
        # MetaAPI historical-candle queries require a time anchor; unlike the
        # tick-history API, `None` does not mean "latest candles". For MT5's
        # copy_rates_from_pos contract, anchor at now and page backward.
        cursor = start_utc or _dt.datetime.now(_dt.timezone.utc)
        while len(collected) < limit:
            want = min(_MAX_CANDLES_PER_REQUEST, limit - len(collected))
            batch = self._rail.run(
                self._account.get_historical_candles(broker_symbol, tf_name, cursor, want),
                self.timeout_seconds + 60.0)
            if not batch:
                break
            collected = list(batch) + collected
            if len(batch) < want:
                break
            first = batch[0]
            data = _as_plain(first)
            stamp = data.get("time")
            if isinstance(stamp, _dt.datetime):
                cursor = stamp if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc)
            else:
                break
            cursor = cursor - _dt.timedelta(seconds=1)
        return collected[-limit:] if limit and len(collected) > limit else collected

    def copy_rates_from_pos(self, symbol, timeframe, start, count):
        """คืน `count` แท่งล่าสุด (เริ่มที่ index `start` นับจากแท่งล่าสุด) เหมือน MT5"""
        try:
            self._require_connection()
            if count is None or int(count) <= 0:
                self._set_error(4401, "invalid count")
                return None
            need = int(start) + int(count)
            candles = self._fetch_candles(timeframe, symbol, None, need)
            if not candles:
                self._set_error(4401, "no candles returned")
                return None
            array = self._candles_to_array(candles, timeframe)
            if len(array) < need:
                # ข้อมูลไม่พอจริง — บอกความจริง ห้ามเติมแท่งปลอม
                self._set_error(4401, f"only {len(array)} candles available, requested {need}")
                return None
            end = len(array) - int(start)
            self._set_error(1, "ok")
            return array[end - int(count):end].copy()
        except Exception as exc:
            self._set_error(4401, f"copy_rates_from_pos failed: {type(exc).__name__}: {exc}")
            return None

    def copy_rates_from(self, symbol, timeframe, date_from, count):
        """คืนแท่งตั้งแต่ `date_from` ขึ้นไป (จำกัด `count`) เหมือน MT5"""
        try:
            self._require_connection()
            start_utc = self._query_instant(date_from)
            candles = self._fetch_candles(timeframe, symbol, start_utc, int(count))
            if not candles:
                self._set_error(4401, "no candles returned")
                return None
            array = self._candles_to_array(candles, timeframe)
            self._set_error(1, "ok")
            return array
        except Exception as exc:
            self._set_error(4401, f"copy_rates_from failed: {type(exc).__name__}: {exc}")
            return None

    def copy_rates_range(self, symbol, timeframe, date_from, date_to):
        """คืนแท่งในช่วงเวลา (label แบบ MT5) เหมือน MT5"""
        try:
            self._require_connection()
            start_utc = self._query_instant(date_from)
            end_utc = self._query_instant(date_to)
            tf_seconds = _TF_TO_METAAPI.get(timeframe, (None, 60))[1]
            span = max(1, int((end_utc - start_utc).total_seconds() / tf_seconds) + 3)
            needed = min(max(span, 64), 20000)
            candles = self._fetch_candles(timeframe, symbol, end_utc, needed)
            if not candles:
                self._set_error(4401, "no candles returned")
                return None
            array = self._candles_to_array(candles, timeframe)
            if len(array) == 0:
                self._set_error(4401, "no candles in range")
                return None
            low = int(self._label_number(date_from))
            high = int(self._label_number(date_to))
            selected = array[(array["time"] >= low) & (array["time"] <= high)]
            self._set_error(1, "ok")
            return selected.copy()
        except Exception as exc:
            self._set_error(4401, f"copy_rates_range failed: {type(exc).__name__}: {exc}")
            return None

    # ------------------------------------------------------------------
    # สถานะไม้และประวัติดีล
    # ------------------------------------------------------------------
    def positions_get(self, symbol=None, ticket=None, group=None):
        """คืนไม้ที่เปิดอยู่ — คืน `None` เมื่อ "อ่านไม่ได้" (ห้ามคืนลิสต์ว่างแทนความล้มเหลว)

        กติกาความปลอดภัยของระบบ: query ล้มเหลว = สถานะไม่รู้ ห้ามตีความเป็นศูนย์ไม้
        """
        try:
            self._require_connection()
            raw = self._rail.run(self._conn.get_positions(), self.timeout_seconds)
            offset = self._refresh_offset()
            wanted = self._symbol_for_broker(symbol) if symbol else None
            rows = []
            for item in raw or []:
                data = _as_plain(item)
                stamp = data.get("time")
                if isinstance(stamp, _dt.datetime):
                    seconds = stamp.timestamp() if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc).timestamp()
                else:
                    seconds = float(stamp or 0)
                rows.append(TradePosition(
                    ticket=int(data.get("id") or 0),
                    time=int(round(seconds)) + offset,
                    time_msc=int(round(seconds * 1000)) + offset * 1000,
                    time_update=int(round(seconds)) + offset,
                    time_update_msc=int(round(seconds * 1000)) + offset * 1000,
                    type=_enum_int(data.get("type"), _POSITION_TYPE_FROM_TEXT, -1),
                    magic=int(data.get("magic") or 0),
                    identifier=int(data.get("id") or 0),
                    reason=_enum_int(data.get("reason"), _POSITION_REASON_FROM_TEXT, 0),
                    volume=float(data.get("volume") or 0.0),
                    price_open=float(data.get("openPrice") or 0.0),
                    sl=float(data.get("stopLoss") or 0.0),
                    tp=float(data.get("takeProfit") or 0.0),
                    price_current=float(data.get("currentPrice") or 0.0),
                    swap=float(data.get("swap") or 0.0),
                    profit=float(data.get("profit") or 0.0),
                    symbol=str(data.get("symbol") or ""),
                    comment=str(data.get("comment") or ""),
                    external_id=str(data.get("clientId") or ""),
                ))
            if ticket is not None:
                rows = [row for row in rows if row.ticket == int(ticket)]
            elif wanted:
                rows = [row for row in rows if row.symbol == wanted]
            self._set_error(1, "ok")
            return rows
        except Exception as exc:
            # คืน None (ไม่ใช่ []) เพื่อให้ระบบรู้ว่า "สถานะไม่รู้" และระงับการเปิดไม้ใหม่
            self._set_error(4501, f"positions_get failed: {type(exc).__name__}: {exc}")
            return None

    def history_deals_get(self, date_from, date_to, group=None, position=None, ticket=None):
        """คืนดีลในช่วงเวลา — คืน `None` เมื่ออ่านไม่ได้, คืน `()` เมื่อไม่มีดีล (เหมือน MT5)"""
        try:
            self._require_connection()
            start = self._query_instant(date_from)
            end = self._query_instant(date_to)
            offset = self._refresh_offset()
            collected = []
            page_from = 0
            while True:
                chunk = self._rail.run(
                    self._conn.get_deals_by_time_range(start, end, page_from, _MAX_CANDLES_PER_REQUEST),
                    self.timeout_seconds)
                deals = (chunk or {}).get("deals") if isinstance(chunk, dict) else getattr(chunk, "deals", None)
                if not deals:
                    break
                collected.extend(deals)
                if len(deals) < _MAX_CANDLES_PER_REQUEST:
                    break
                page_from += len(deals)
                if page_from > 20000:
                    break
            rows = []
            for item in collected:
                data = _as_plain(item)
                stamp = data.get("time")
                if isinstance(stamp, _dt.datetime):
                    seconds = stamp.timestamp() if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc).timestamp()
                else:
                    seconds = float(stamp or 0)
                rows.append(TradeDeal(
                    ticket=int(data.get("id") or 0),
                    order=int(data.get("orderId") or 0),
                    time=int(round(seconds)) + offset,
                    time_msc=int(round(seconds * 1000)) + offset * 1000,
                    type=_enum_int(data.get("type"), _DEAL_TYPE_FROM_TEXT, -1),
                    entry=_enum_int(data.get("entryType"), _DEAL_ENTRY_FROM_TEXT, -1),
                    magic=int(data.get("magic") or 0),
                    position_id=int(data.get("positionId") or 0),
                    reason=_enum_int(data.get("reason"), _DEAL_REASON_FROM_TEXT, 0),
                    volume=float(data.get("volume") or 0.0),
                    price=float(data.get("price") or 0.0),
                    commission=float(data.get("commission") or 0.0),
                    swap=float(data.get("swap") or 0.0),
                    profit=float(data.get("profit") or 0.0),
                    fee=float(data.get("fee") or 0.0),   # ระบบอ่าน deal.fee ใน refresh_closed_trade_state
                    symbol=str(data.get("symbol") or ""),
                    comment=str(data.get("comment") or ""),
                    external_id=str(data.get("clientId") or ""),
                ))
            rows.sort(key=lambda row: row.ticket)
            if position is not None:
                rows = [row for row in rows if row.position_id == int(position)]
            self._set_error(1, "ok")
            return tuple(rows)
        except Exception as exc:
            self._set_error(4502, f"history_deals_get failed: {type(exc).__name__}: {exc}")
            return None

    def history_orders_get(self, date_from=None, date_to=None, group=None, position=None, ticket=None):
        """คำสั่งซื้อขายในประวัติ — ระบบหลักยังไม่ใช้ แต่มีไว้ให้เครื่องมือเพิ่มเติมเรียกได้"""
        try:
            self._require_connection()
            start = self._query_instant(date_from)
            end = self._query_instant(date_to)
            offset = self._refresh_offset()
            chunk = self._rail.run(
                self._conn.get_history_orders_by_time_range(start, end, 0, _MAX_CANDLES_PER_REQUEST),
                self.timeout_seconds)
            orders = (chunk or {}).get("historyOrders") if isinstance(chunk, dict) else getattr(chunk, "historyOrders", None)
            rows = []
            for item in orders or []:
                data = _as_plain(item)
                stamp = data.get("time")
                if isinstance(stamp, _dt.datetime):
                    seconds = stamp.timestamp() if stamp.tzinfo else stamp.replace(tzinfo=_dt.timezone.utc).timestamp()
                else:
                    seconds = float(stamp or 0)
                rows.append(TradeOrder(
                    ticket=int(data.get("id") or 0),
                    time_setup=int(round(seconds)) + offset,
                    time_setup_msc=int(round(seconds * 1000)) + offset * 1000,
                    time_done=int(round(seconds)) + offset,
                    time_done_msc=0, time_expiration=0,
                    type=_enum_int(data.get("type"), _ORDER_TYPE_FROM_TEXT, -1),
                    type_time=ORDER_TIME_GTC, type_filling=ORDER_FILLING_FOK,
                    state=int(data.get("state") or 0),
                    magic=int(data.get("magic") or 0),
                    position_id=int(data.get("positionId") or 0), position_by_id=0,
                    reason=_enum_int(data.get("reason"), _ORDER_REASON_FROM_TEXT, 0),
                    volume_initial=float(data.get("volume") or 0.0),
                    volume_current=float(data.get("currentVolume") or 0.0),
                    price_open=float(data.get("openPrice") or 0.0),
                    sl=float(data.get("stopLoss") or 0.0),
                    tp=float(data.get("takeProfit") or 0.0),
                    price_current=float(data.get("currentPrice") or 0.0),
                    price_stoplimit=float(data.get("stopLimitPrice") or 0.0),
                    symbol=str(data.get("symbol") or ""),
                    comment=str(data.get("comment") or ""),
                    external_id=str(data.get("clientId") or ""),
                ))
            if position is not None:
                rows = [row for row in rows if row.position_id == int(position)]
            self._set_error(1, "ok")
            return tuple(rows)
        except Exception as exc:
            self._set_error(4503, f"history_orders_get failed: {type(exc).__name__}: {exc}")
            return None

    # ------------------------------------------------------------------
    # คำนวณความเสี่ยง/มาร์จิน
    # ------------------------------------------------------------------
    def _quote_prices(self, symbol):
        """ราคา bid/ask ปัจจุบัน (ใช้คำนวณ profit/margin แบบเดียวกับ MT5)"""
        broker_symbol = self._symbol_for_broker(symbol)
        price = self._rail.run(
            self._conn.get_symbol_price(broker_symbol, keep_subscription=True), self.timeout_seconds)
        data = _as_plain(price)
        bid = float(data.get("bid") or 0.0)
        ask = float(data.get("ask") or 0.0)
        tick_value = float(data.get("profitTickValue") or 0.0)
        return bid, ask, tick_value

    def order_calc_profit(self, action, symbol, volume, price_open, price_close):
        """กำไร/ขาดทุนที่คาดหมาย (ใช้สูตร tick value ของ MT5 เอง)

        MT5: profit = (Δprice / trade_tick_size) * trade_tick_value * volume
        MetaAPI ไม่มี API นี้ จึงคำนวณจากค่า tick ที่บัญชีรายงานจริง (ไม่ใช้ค่าคงที่เดา)
        หมายเหตุ: คืนค่าลบเมื่อขาดทุน เหมือน MT5 → ระบบจึงใช้ abs() ต่อ
        """
        try:
            self._require_connection()
            if action not in (ORDER_TYPE_BUY, ORDER_TYPE_SELL):
                self._set_error(6, "unsupported order type for profit calculation")
                return None
            spec = self.symbol_info(symbol)
            if spec is None:
                return None
            _, _, live_tick_value = self._quote_prices(symbol)
            tick_value = live_tick_value or float(spec.trade_tick_value or 0.0)
            tick_size = float(spec.trade_tick_size or 0.0)
            if tick_value <= 0 or tick_size <= 0 or float(volume) <= 0:
                self._set_error(6, "insufficient symbol data for profit calculation")
                return None
            delta = float(price_close) - float(price_open)
            if action == ORDER_TYPE_SELL:
                delta = -delta
            result = (delta / tick_size) * tick_value * float(volume)
            self._set_error(1, "ok")
            return float(result)
        except Exception as exc:
            self._set_error(6, f"order_calc_profit failed: {type(exc).__name__}: {exc}")
            return None

    def order_calc_margin(self, action, symbol, volume, price):
        """มาร์จินที่ต้องใช้

        ค่าเริ่มต้นใช้ `calculate_margin()` ของ MetaAPI (แม่นสุดเพราะเป็นฝ่ายที่ส่งคำสั่งจริง)

        ⚠️ พบส่วนต่างจริง (2026-09-21): MT5 terminal ของบัญชีนี้คิดมาร์จินทอง 0.001 lot ≈ 0.48 USD
        แต่ MetaAPI คิด ≈ 4.35 USD (notional/leverage) — ต่างกัน ~9 เท่า
        ค่าของ MetaAPI สูงกว่า = อนุรักษ์นิยมกว่า = ปลอดภัยกว่า (ไม่เปิดไม้เกินกำลัง)
        ผู้ใช้ที่รู้เรตมาร์จินจริงของโบรกตัวเอง ตั้ง `METAAPI_SHIM_MARGIN_RATE` (สัดส่วนของ notional)
        เพื่อให้ตรงกับโบรกได้ เช่น 0.0011 → margin = volume × contract × price × 0.0011
        """
        try:
            self._require_connection()
            if action not in (ORDER_TYPE_BUY, ORDER_TYPE_SELL):
                self._set_error(6, "unsupported order type for margin calculation")
                return None
            forced_rate = os.environ.get("METAAPI_SHIM_MARGIN_RATE")
            if forced_rate:
                spec_rate = self.symbol_info(symbol)
                if spec_rate is None:
                    return None
                notional = float(volume) * float(spec_rate.trade_contract_size or 0.0) * float(price)
                margin_rate = notional * float(forced_rate)
                self._set_error(1, "ok (margin rate override)")
                return float(margin_rate)
            broker_symbol = self._symbol_for_broker(symbol)
            order = {
                "symbol": broker_symbol,
                "type": "ORDER_TYPE_BUY" if action == ORDER_TYPE_BUY else "ORDER_TYPE_SELL",
                "volume": float(volume),
                "openPrice": float(price),
            }
            raw = self._rail.run(self._conn.calculate_margin(order), self.timeout_seconds)
            # SDK บางเวอร์ชันคืน dict ({"margin": 4.35}) ไม่ใช่ตัวเลขตรง ๆ — รองรับทั้งสองแบบ
            data = _as_plain(raw)
            value = _pick(data, "margin", "value", default=None)
            if value is None:
                value = raw
            margin = float(value)
            self._set_error(1, "ok")
            return margin
        except Exception as exc:
            self._set_error(6, f"order_calc_margin failed: {type(exc).__name__}: {exc}")
            return None

    # ------------------------------------------------------------------
    # ตรวจคำสั่งก่อนส่ง (order_check) — MetaAPI ไม่มี จึงจำลองแบบเดียวกับที่ MT5 ตรวจ
    # ------------------------------------------------------------------
    def order_check(self, request):
        """ตรวจคำสั่งโดยไม่ส่งจริง — ระบบใช้เป็นประตูก่อนยิงออเดอร์ทุกลำดับ

        retcode = 0 → ผ่าน (เหมือน MT5) · nonzero → ไม่ผ่าน
        การตรวจที่ทำ: symbol/volume/step/bid-ask/SL-TP ด้านถูก/RR/มาร์จินพอ
        (ไม่ตรวจ "ไม้ซ้ำ" เพราะผู้เรียกเป็นผู้ตัดสินใจ — ตัวเทรดมีประตูของตัวเองอยู่แล้ว)
        """
        try:
            self._require_connection()
            entry_request = request if isinstance(request, dict) else {}
            symbol = str(entry_request.get("symbol") or "")
            volume = float(entry_request.get("volume") or 0.0)
            order_type_raw = entry_request.get("type")
            order_type = int(order_type_raw) if order_type_raw is not None else -1
            price = float(entry_request.get("price") or 0.0)
            sl = float(entry_request.get("sl") or 0.0)
            tp = float(entry_request.get("tp") or 0.0)

            info = self._account_info_cache
            if info is None:
                # ต้องเป็นข้อมูลสด: ถ้าใช้ค่าเริ่มต้น 0.0 จะตัดสิน "เงินไม่พอ" ผิด
                fresh = self.account_info()
                info = fresh if fresh is not None else {}
            data = _as_plain(info)
            balance = float(_pick(data, "balance", default=0.0) or 0.0)
            equity = float(_pick(data, "equity", default=0.0) or 0.0)
            free_margin = float(_pick(data, "freeMargin", "margin_free", default=0.0) or 0.0)
            if free_margin <= 0.0:
                # fallback: บาง snapshot ให้มาแค่ margin → ประมาณจาก equity - margin
                used = _pick(data, "margin", "margin_so_call", default=0.0)
                try:
                    used_value = float(used or 0.0)
                except Exception:
                    used_value = 0.0
                if equity > 0.0:
                    free_margin = max(equity - used_value, 0.0)

            spec = self.symbol_info(symbol)
            if spec is None:
                return self._check_result(TRADE_RETCODE_INVALID, balance, equity,
                                          "symbol not found", entry_request)

            minimum = float(spec.volume_min or 0.0)
            maximum = float(spec.volume_max or 0.0)
            step = float(spec.volume_step or 0.0)
            if volume <= 0 or volume < minimum or (maximum > 0 and volume > maximum):
                return self._check_result(TRADE_RETCODE_INVALID_VOLUME, balance, equity,
                                          f"volume {volume} outside [{minimum}, {maximum}]", entry_request)
            if step > 0:
                units = (volume - minimum) / step
                if not math.isclose(units, round(units), abs_tol=1e-8):
                    return self._check_result(TRADE_RETCODE_INVALID_VOLUME, balance, equity,
                                              f"volume {volume} not aligned to step {step}", entry_request)

            bid, ask, _ = self._quote_prices(symbol)
            if bid <= 0 or ask <= 0:
                return self._check_result(TRADE_RETCODE_PRICE_OFF, balance, equity,
                                          "no current quote", entry_request)
            if order_type not in (ORDER_TYPE_BUY, ORDER_TYPE_SELL):
                return self._check_result(TRADE_RETCODE_INVALID, balance, equity,
                                          f"unsupported order type {order_type}", entry_request)
            if order_type == ORDER_TYPE_BUY and not (sl < price < tp):
                return self._check_result(TRADE_RETCODE_INVALID_STOPS, balance, equity,
                                          "BUY requires SL < price < TP", entry_request)
            if order_type == ORDER_TYPE_SELL and not (tp < price < sl):
                return self._check_result(TRADE_RETCODE_INVALID_STOPS, balance, equity,
                                          "SELL requires TP < price < SL", entry_request)
            if order_type not in (ORDER_TYPE_BUY, ORDER_TYPE_SELL):
                return self._check_result(TRADE_RETCODE_INVALID, balance, equity,
                                          f"unsupported order type {order_type}", entry_request)

            margin = self.order_calc_margin(order_type, symbol, volume, price)
            margin_value = float(margin) if margin is not None else 0.0
            if margin is not None and margin_value > free_margin:
                return self._check_result(TRADE_RETCODE_NO_MONEY, balance, equity,
                                          f"margin {margin_value:.2f} exceeds free margin {free_margin:.2f}",
                                          entry_request, margin=margin_value)
            level = 0.0
            if margin_value > 0:
                level = (equity / margin_value) * 100.0
            return OrderCheckResult(
                retcode=0, balance=balance, equity=equity, profit=0.0,
                margin=margin_value, margin_free=free_margin - margin_value, margin_level=level,
                comment="Done", request=entry_request,
            )
        except Exception as exc:
            self._set_error(4701, f"order_check failed: {type(exc).__name__}: {exc}")
            return None

    def _check_result(self, retcode, balance, equity, comment, request, margin=0.0):
        return OrderCheckResult(
            retcode=int(retcode), balance=float(balance), equity=float(equity), profit=0.0,
            margin=float(margin), margin_free=float(balance), margin_level=0.0,
            comment=str(comment), request=request,
        )

    # ------------------------------------------------------------------
    # ส่งคำสั่งจริง (order_send)
    # ------------------------------------------------------------------
    def _trade_response_to_result(self, response, request):
        data = _as_plain(response)
        numeric = int(data.get("numericCode") or 0)
        string_code = data.get("stringCode")
        if numeric in _OK_NUMERIC or (string_code in _OK_STRING and numeric == 0):
            retcode = numeric if numeric in (TRADE_RETCODE_PLACED, TRADE_RETCODE_DONE, TRADE_RETCODE_DONE_PARTIAL) else TRADE_RETCODE_DONE
        else:
            retcode = numeric or TRADE_RETCODE_ERROR
        order_id = int(data.get("orderId") or 0)
        position_id = int(data.get("positionId") or 0)
        if position_id == 0:
            position_id = order_id
        return OrderSendResult(
            retcode=retcode,
            deal=position_id,   # MT5: เลขดีลที่เปิดไม้ (ระบบนำไปใช้เป็นกุญแจปิดไม้)
            order=position_id,  # ★ ระบบเก็บ result.order เป็น position id ใน state["open_positions"]
            volume=float(request.get("volume") or 0.0),
            price=float(request.get("price") or 0.0),
            bid=0.0, ask=0.0,
            comment=str(data.get("message") or string_code or ""),
            request_id=0, retcode_external=0, request=request,
        )

    def _send_market_order(self, request):
        symbol = str(request["symbol"])
        volume = float(request["volume"])
        order_type = int(request["type"])
        sl = float(request.get("sl") or 0.0)
        tp = float(request.get("tp") or 0.0)
        magic = request.get("magic")
        comment = str(request.get("comment") or "")
        deviation = int(request.get("deviation") or 0)
        options = {
            "comment": comment,
            "clientId": str(request.get("clientId") or f"shim-{int(time.time() * 1000)}"),
            "slippage": deviation,
        }
        if magic not in (None, 0):
            options["magic"] = str(int(magic))   # MetaAPI รับ magic เป็นข้อความ (ทดลองยืนยันแล้ว)
        broker_symbol = self._symbol_for_broker(symbol)
        if order_type == ORDER_TYPE_BUY:
            response = self._rail.run(
                self._conn.create_market_buy_order(broker_symbol, volume, sl or None, tp or None, options),
                self.timeout_seconds)
        else:
            response = self._rail.run(
                self._conn.create_market_sell_order(broker_symbol, volume, sl or None, tp or None, options),
                self.timeout_seconds)
        return self._trade_response_to_result(response, request)

    def _send_close_order(self, request):
        """ปิดไม้ด้วย MetaAPI close_position (ใช้ position id เป็นกุญแจ)"""
        position_id = str(int(request["position"]))
        comment = str(request.get("comment") or "")
        magic = request.get("magic")
        options = {
            "comment": comment,
            "clientId": str(request.get("clientId") or f"shim-close-{int(time.time() * 1000)}"),
            "slippage": int(request.get("deviation") or 0),
        }
        if magic not in (None, 0):
            options["magic"] = str(int(magic))
        response = self._rail.run(
            self._conn.close_position(position_id, options), self.timeout_seconds)
        return self._trade_response_to_result(response, request)

    def order_send(self, request):
        """ส่งคำสั่งจริง — ปฏิเสธทันทีถ้าอยู่ในโหมดอ่านอย่างเดียว

        โหมดอ่านอย่างเดียว (METAAPI_SHIM_READ_ONLY=1) ใช้สำหรับตรวจ/วิจัย/ทดสอบ
        โดยไม่มีความเสี่ยงต่อเงินจริง — ปฏิเสธทุกคำสั่งที่เปลี่ยนสถานะบัญชี
        อ่านค่าจาก environment สดทุกครั้ง: กันกรณีตั้ง env หลังจาก import แล้วคำสั่งยังหลุด
        """
        try:
            self._require_connection()
            entry_request = request if isinstance(request, dict) else {}
            if self.read_only or _env_flag("METAAPI_SHIM_READ_ONLY", False):
                self._set_error(4751, "read-only mode: order_send refused")
                return OrderSendResult(
                    retcode=TRADE_RETCODE_TRADE_DISABLED, deal=0, order=0,
                    volume=float(entry_request.get("volume") or 0.0),
                    price=float(entry_request.get("price") or 0.0), bid=0.0, ask=0.0,
                    comment="read-only mode: order_send refused", request_id=0,
                    retcode_external=0, request=entry_request,
                )
            action_raw = entry_request.get("action")
            action = int(action_raw) if action_raw is not None else TRADE_ACTION_DEAL
            self._set_error(1, "ok")
            if action == TRADE_ACTION_DEAL and entry_request.get("position"):
                return self._send_close_order(entry_request)
            return self._send_market_order(entry_request)
        except Exception as exc:
            self._set_error(4702, f"order_send failed: {type(exc).__name__}: {exc}")
            return OrderSendResult(
                retcode=TRADE_RETCODE_ERROR, deal=0, order=0,
                volume=float((request or {}).get("volume") or 0.0),
                price=float((request or {}).get("price") or 0.0), bid=0.0, ask=0.0,
                comment=f"{type(exc).__name__}: {exc}", request_id=0,
                retcode_external=0, request=request,
            )


# ---------------------------------------------------------------------------
# อินสแตนซ์เดียวใช้ร่วมกันทั้งโปรเซส (เหมือนสไตล์การเรียก mt5.xxx ของระบบเดิม)
# ---------------------------------------------------------------------------
_SINGLETON = MetaApiMt5Shim()


def _bind_api() -> None:
    """ผูกฟังก์ชันของอินสแตนซ์ออกเป็นฟังก์ชันระดับโมดูล เพื่อให้ `shim.initialize()` เหมือน `mt5.initialize()`"""
    for name in (
        "initialize", "shutdown", "version", "last_error", "terminal_info", "account_info",
        "symbol_select", "symbol_info", "symbol_info_tick",
        "copy_rates_from_pos", "copy_rates_from", "copy_rates_range",
        "positions_get", "history_deals_get", "history_orders_get",
        "order_calc_profit", "order_calc_margin", "order_check", "order_send",
    ):
        globals()[name] = getattr(_SINGLETON, name)


_bind_api()


def server_utc_offset_seconds():
    """offset ของนาฬิกาโบรกเกอร์เทียบ UTC (มีไว้ให้เครื่องมือตรวจ/วินิจฉัยอ่านได้)"""
    return _SINGLETON._refresh_offset()


def is_read_only() -> bool:
    """สถานะอ่านอย่างเดียวของตัวเชื่อม (อ่าน env สด เพื่อไม่ให้ตั้งค่าหลัง import แล้วพลาด)"""
    return bool(_SINGLETON.read_only or _env_flag("METAAPI_SHIM_READ_ONLY", False))


def install_as_mt5() -> None:
    """ติดตั้งเป็น `MetaTrader5` ใน sys.modules เพื่อให้โค้ดเดิม `import MetaTrader5 as mt5` ใช้ชั้นนี้ทันที

    ใช้เมื่อตั้ง `METAAPI_SHIM_AUTOLOAD=1` หรือเรียกเองก่อน import โมดูลของระบบเทรด
    """
    sys.modules.setdefault("MetaTrader5", sys.modules[__name__])
