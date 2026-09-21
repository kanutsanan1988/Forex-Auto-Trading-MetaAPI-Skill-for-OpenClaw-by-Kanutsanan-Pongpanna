# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""เทสต์ offline ของ metaapi_mt5_shim — ไม่ต่อเน็ต ไม่ใช้คีย์ ไม่ส่งออเดอร์

จุดที่ต้องพิสูจน์ (เพราะถ้าผิดจะพังเงียบตอนเทรดจริง):
  1. แปลงเวลา: label เซิร์ฟเวอร์ ↔ UTC ไป-กลับได้ค่าเดิม (นี่คือจุดตายของระบบ)
  2. แท่ง: คืน numpy array แบบ MT5 (index ด้วยชื่อได้, len(), [:-1], rates[-2]["time"])
  3. ดีล: ต้องมี fee (refresh_closed_trade_state อ่าน net = profit+commission+swap+fee)
  4. order_send: response ของ MetaAPI → .order/.deal ต้องเป็น position id (state["open_positions"])
  5. positions_get: ล้มเหลว → None (ห้ามคืน [] ให้ระบบเข้าใจผิดว่าไม่มีไม้)
  6. order_check: ตรวจ volume step / SL-TP ด้านถูก / มาร์จินไม่พอ
  7. read_only: order_send ถูกปฏิเสธ
  8. query ล้มเหลว → None (ไม่คืน 0) — กติกา "unknown" ของระบบ
"""
from __future__ import annotations

import datetime as dt
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import metaapi_mt5_shim as shim   # noqa: E402

OFFSET = 10800   # +3 ชม. (ค่าที่ทดลองได้จริงกับบัญชีนี้)


def make_instance():
    inst = shim.MetaApiMt5Shim()
    inst._connected = True
    inst._server_offset_seconds = OFFSET
    return inst


class FakeConnection:
    def __init__(self, *, fail=None):
        self.fail = set(fail or [])
        self.closed = []
        self.sent = []

    def _maybe(self, name):
        if name in self.fail:
            raise RuntimeError(f"forced failure: {name}")

    async def get_symbol_specification(self, symbol):
        self._maybe("spec")
        return {"symbol": symbol, "tickSize": 0.001, "minVolume": 0.001, "maxVolume": 30,
                "volumeStep": 0.001, "contractSize": 100, "digits": 3, "point": 0.001,
                "tradeMode": 4, "stopsLevel": 0, "freezeLevel": 0, "profitCurrency": "USD"}

    async def get_symbol_price(self, symbol, keep_subscription=False):
        self._maybe("price")
        return {"symbol": symbol, "bid": 4369.965, "ask": 4370.305,
                "profitTickValue": 0.1, "time": dt.datetime(2026, 9, 21, 0, 36, 40, tzinfo=dt.timezone.utc)}

    async def calculate_margin(self, order):
        self._maybe("margin")
        return 0.48

    async def get_account_information(self):
        self._maybe("account")
        return {"balance": 10.44, "equity": 10.44, "freeMargin": 9.96, "margin": 0.48,
                "leverage": 100, "currency": "USD", "tradeAllowed": True, "login": 99979798}

    async def get_positions(self):
        self._maybe("positions")
        return [{"id": "5551", "type": "POSITION_TYPE_BUY", "symbol": "XAUUSD.sml", "magic": "8252026",
                 "time": dt.datetime(2026, 9, 21, 0, 20, 0, tzinfo=dt.timezone.utc),
                 "openPrice": 4360.0, "currentPrice": 4369.9, "stopLoss": 4359.0, "takeProfit": 4372.0,
                 "volume": 0.001, "profit": 0.99, "swap": 0.0, "comment": "codex-trend",
                 "clientId": "abc123", "reason": "POSITION_REASON_CLIENT"}]

    async def get_deals_by_time_range(self, start, end, offset=0, limit=1000):
        self._maybe("deals")
        return {"deals": [{"id": "9001", "orderId": "8001", "positionId": "5551",
                           "type": "DEAL_TYPE_SELL", "entryType": "DEAL_ENTRY_OUT",
                           "symbol": "XAUUSD.sml", "magic": "8252026",
                           "time": dt.datetime(2026, 9, 21, 1, 0, 0, tzinfo=dt.timezone.utc),
                           "volume": 0.001, "price": 4370.0, "commission": -0.01, "swap": 0.0,
                           "profit": 1.0, "fee": 0.0, "comment": "codex-trend"}]}

    async def create_market_buy_order(self, symbol, volume, stop_loss=None, take_profit=None, options=None):
        self._maybe("buy")
        self.sent.append(("buy", symbol, volume, stop_loss, take_profit, options))
        return {"numericCode": 10009, "stringCode": "TRADE_RETCODE_DONE",
                "message": "Done", "orderId": "7007", "positionId": "7007"}

    async def close_position(self, position_id, options=None):
        self._maybe("close")
        self.sent.append(("close", position_id, options))
        return {"numericCode": 10009, "stringCode": "TRADE_RETCODE_DONE",
                "message": "Done", "orderId": "7008", "positionId": "7007"}


class TestTimeConversion(unittest.TestCase):
    def test_label_round_trip(self):
        inst = make_instance()
        label = 1789977000                      # เวลาที่ MT5 รายงาน (นาฬิกาโบรก +3)
        instant = inst._query_instant(label)
        self.assertEqual(instant.timestamp(), label - OFFSET,
                         "label เซิร์ฟเวอร์ - offset = เวลา UTC จริง")
        self.assertEqual(instant.tzinfo, dt.timezone.utc, "ต้องคืน aware-UTC เสมอ")
        back = int(instant.timestamp()) + OFFSET
        self.assertEqual(back, label, "แปลงไป-กลับต้องได้ค่าเดิม")

    def test_naive_datetime_is_local_and_aware_is_absolute(self):
        inst = make_instance()
        naive = dt.datetime(2026, 9, 21, 7, 0, 0)
        aware = dt.datetime(2026, 9, 21, 7, 0, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(inst._label_number(naive), naive.timestamp())
        self.assertEqual(inst._query_instant(aware), aware - dt.timedelta(seconds=OFFSET))

    def test_offset_is_never_hardcoded_zero_when_configured(self):
        inst = make_instance()
        self.assertEqual(inst._refresh_offset(), OFFSET)


class TestRates(unittest.TestCase):
    def test_candles_become_mt5_style_array(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        candles = [
            {"time": dt.datetime(2026, 9, 21, 0, 30, tzinfo=dt.timezone.utc), "open": 1.0, "high": 2.0,
             "low": 0.5, "close": 1.5, "tickVolume": 10, "spread": 30, "volume": 0},
            {"time": dt.datetime(2026, 9, 21, 0, 31, tzinfo=dt.timezone.utc), "open": 1.5, "high": 2.5,
             "low": 1.0, "close": 2.0, "tickVolume": 12, "spread": 30, "volume": 0},
        ]
        arr = inst._candles_to_array(candles, shim.TIMEFRAME_M1)
        self.assertEqual(len(arr), 2)
        self.assertEqual(arr[-1]["time"] - arr[0]["time"], 60, "แท่งต้องห่างกัน 1 นาที")
        self.assertEqual(float(arr[-1]["close"]), 2.0)
        self.assertEqual(float(arr[-2]["close"]), 1.5, "เรียงเก่า→ใหม่ เหมือน MT5")
        self.assertEqual(int(arr[-1]["spread"]), 30, "spread ต้องเป็น point ตรงกับ MT5")
        self.assertEqual(arr[-1]["time"], int(candles[-1]["time"].timestamp()) + OFFSET,
                         "เวลาแท่งต้องเป็น label เซิร์ฟเวอร์ เหมือน MT5")
        sliced = arr[:-1]
        self.assertEqual(len(sliced), 1, "ระบบใช้ arr[:-1] ตัดแท่งที่ยังไม่ปิด")

    def test_no_candles_returns_empty_not_fake(self):
        inst = make_instance()
        arr = inst._candles_to_array([], shim.TIMEFRAME_M5)
        self.assertEqual(len(arr), 0, "ห้ามสร้างแท่งปลอม")


class TestPositionsAndDeals(unittest.TestCase):
    def test_positions_fields_match_consumer(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        rows = inst.positions_get(symbol="XAUUSD.sml")
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p.ticket, 5551)
        self.assertEqual(p.type, shim.POSITION_TYPE_BUY)
        self.assertEqual(p.magic, 8252026)
        self.assertEqual(p.symbol, "XAUUSD.sml")
        self.assertEqual(p.volume, 0.001)
        self.assertEqual(p.price_open, 4360.0)
        self.assertEqual(p.price_current, 4369.9)
        self.assertEqual(p.sl, 4359.0)
        self.assertEqual(p.tp, 4372.0)
        self.assertEqual(p.comment, "codex-trend")
        expected_label = int(dt.datetime(2026, 9, 21, 0, 20, 0,
                                          tzinfo=dt.timezone.utc).timestamp()) + OFFSET
        self.assertEqual(p.time, expected_label,
                         "position time ต้องเป็น label เซิร์ฟเวอร์ (UTC จริง + offset)")
        self.assertGreater(p.time, 1789977000 - 86400 * 365,
                           "ต้องไม่ใช่เวลาหมุนกลับเป็นยุคอื่น")

    def test_positions_query_failure_returns_none(self):
        inst = make_instance()
        inst._conn = FakeConnection(fail=["positions"])
        self.assertIsNone(inst.positions_get(symbol="XAUUSD.sml"),
                          "query ล้มเหลวต้องเป็น None (สถานะไม่รู้) ห้ามเป็น []")

    def test_full_symbol_mapping_via_alias(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        inst._alias = {"XAUUSD": "XAUUSD.sml"}
        rows = inst.positions_get(symbol="XAUUSD")
        self.assertEqual(len(rows), 1)

    def test_deal_has_fee_and_entry(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        rows = inst.history_deals_get(dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc),
                                      dt.datetime(2026, 9, 22, tzinfo=dt.timezone.utc))
        self.assertEqual(len(rows), 1)
        d = rows[0]
        self.assertEqual(d.entry, shim.DEAL_ENTRY_OUT)
        self.assertEqual(d.magic, 8252026)
        self.assertEqual(d.position_id, 5551)
        self.assertEqual(d.fee, 0.0)
        net = d.profit + d.commission + d.swap + d.fee
        self.assertEqual(net, 0.99, "net ต้องคำนวณได้เหมือนเดิม")

    def test_deals_empty_returns_empty_tuple(self):
        inst = make_instance()
        fake = FakeConnection()
        fake.get_deals_by_time_range = lambda *a, **k: _async_value({"deals": []})
        inst._conn = fake
        rows = inst.history_deals_get(dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc),
                                      dt.datetime(2026, 9, 22, tzinfo=dt.timezone.utc))
        self.assertEqual(rows, (), "ไม่มีดีล = ลิสต์ว่าง (ต่างจาก query ล้มเหลว)")


async def _async_value(value):
    return value


class TestOrderFlow(unittest.TestCase):
    def test_order_send_returns_position_id_in_order_and_deal(self):
        inst = make_instance()
        fake = FakeConnection()
        inst._conn = fake
        request = {"action": shim.TRADE_ACTION_DEAL, "symbol": "XAUUSD.sml", "volume": 0.001,
                   "type": shim.ORDER_TYPE_BUY, "price": 4370.305, "sl": 4369.0, "tp": 4373.0,
                   "deviation": 50, "magic": 8252026, "comment": "codex-trend",
                   "type_time": shim.ORDER_TIME_GTC, "type_filling": shim.ORDER_FILLING_FOK}
        result = inst.order_send(request)
        self.assertEqual(result.retcode, shim.TRADE_RETCODE_DONE)
        self.assertEqual(result.order, 7007, "result.order ต้องเป็น position id (state['open_positions'])")
        self.assertEqual(result.deal, 7007)
        self.assertEqual(fake.sent[0][0], "buy")
        self.assertEqual(fake.sent[0][5]["magic"], "8252026", "MetaAPI รับ magic เป็นข้อความ")
        self.assertEqual(fake.sent[0][5]["slippage"], 50)

    def test_close_position_uses_position_key(self):
        inst = make_instance()
        fake = FakeConnection()
        inst._conn = fake
        request = {"action": shim.TRADE_ACTION_DEAL, "position": 5551, "symbol": "XAUUSD.sml",
                   "volume": 0.001, "type": shim.ORDER_TYPE_SELL, "price": 4369.965,
                   "deviation": 50, "magic": 8252026, "comment": "codex-profit-exit"}
        result = inst.order_send(request)
        self.assertEqual(result.retcode, shim.TRADE_RETCODE_DONE)
        self.assertEqual(fake.sent[0][0], "close")
        self.assertEqual(fake.sent[0][1], "5551")

    def test_read_only_refuses_order_send(self):
        inst = make_instance()
        fake = FakeConnection()
        inst._conn = fake
        inst.read_only = True
        result = inst.order_send({"action": shim.TRADE_ACTION_DEAL, "symbol": "XAUUSD.sml",
                                 "volume": 0.001, "type": shim.ORDER_TYPE_BUY, "price": 4370.0,
                                 "sl": 4369.0, "tp": 4373.0})
        self.assertEqual(result.retcode, shim.TRADE_RETCODE_TRADE_DISABLED)
        self.assertEqual(len(fake.sent), 0, "ห้ามมีคำสั่งออกไปจริงในโหมดอ่านอย่างเดียว")

    def test_order_check_validates_volume_step(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        bad = {"action": shim.TRADE_ACTION_DEAL, "symbol": "XAUUSD.sml", "volume": 0.0015,
               "type": shim.ORDER_TYPE_BUY, "price": 4370.305, "sl": 4369.0, "tp": 4373.0}
        result = inst.order_check(bad)
        self.assertEqual(result.retcode, shim.TRADE_RETCODE_INVALID_VOLUME)

    def test_order_check_validates_stops_side(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        wrong = {"action": shim.TRADE_ACTION_DEAL, "symbol": "XAUUSD.sml", "volume": 0.001,
                 "type": shim.ORDER_TYPE_BUY, "price": 4370.305, "sl": 4375.0, "tp": 4373.0}
        result = inst.order_check(wrong)
        self.assertEqual(result.retcode, shim.TRADE_RETCODE_INVALID_STOPS)

    def test_order_check_passes_valid_order(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        good = {"action": shim.TRADE_ACTION_DEAL, "symbol": "XAUUSD.sml", "volume": 0.001,
                "type": shim.ORDER_TYPE_BUY, "price": 4370.305, "sl": 4369.0, "tp": 4373.0}
        result = inst.order_check(good)
        self.assertEqual(result.retcode, 0)
        self.assertIsInstance(result._asdict(), dict, "ต้องมี _asdict() ให้ระบบใช้")

    def test_order_calc_profit_matches_mt5_formula(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        value = inst.order_calc_profit(shim.ORDER_TYPE_BUY, "XAUUSD.sml", 0.001, 4370.305, 4369.0)
        # (|Δ| / tick_size) * tick_value * volume = (1.305/0.001)*0.1*0.001 = 0.1305 → ขาดทุน
        self.assertAlmostEqual(value, -0.1305, places=4)
        sell = inst.order_calc_profit(shim.ORDER_TYPE_SELL, "XAUUSD.sml", 0.001, 4370.305, 4369.0)
        self.assertAlmostEqual(sell, 0.1305, places=4)

    def test_symbol_info_carries_fields_consumer_reads(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        info = inst.symbol_info("XAUUSD.sml")
        for field in ("name", "digits", "point", "visible", "volume_min", "volume_max",
                      "volume_step", "trade_tick_size", "trade_contract_size"):
            self.assertTrue(hasattr(info, field), f"ต้องมีฟิลด์ {field}")

    def test_tick_carries_label_time_for_health_check(self):
        inst = make_instance()
        inst._conn = FakeConnection()
        tick = inst.symbol_info_tick("XAUUSD.sml")
        self.assertEqual(tick.bid, 4369.965)
        self.assertEqual(tick.ask, 4370.305)
        expected = int(dt.datetime(2026, 9, 21, 0, 36, 40, tzinfo=dt.timezone.utc).timestamp()) + OFFSET
        self.assertEqual(tick.time, expected)


class TestExports(unittest.TestCase):
    def test_module_level_api_is_bound(self):
        for name in ("initialize", "shutdown", "symbol_info", "symbol_info_tick", "copy_rates_from_pos",
                     "copy_rates_range", "positions_get", "history_deals_get", "order_check",
                     "order_send", "order_calc_profit", "order_calc_margin", "last_error"):
            self.assertTrue(callable(getattr(shim, name)), f"ต้องมี {name} ระดับโมดูล")

    def test_constants_match_mt5(self):
        self.assertEqual(shim.TIMEFRAME_H1, 16385)
        self.assertEqual(shim.TIMEFRAME_M1, 1)
        self.assertEqual(shim.ORDER_TYPE_BUY, 0)
        self.assertEqual(shim.POSITION_TYPE_SELL, 1)
        self.assertEqual(shim.DEAL_ENTRY_OUT, 1)
        self.assertEqual(shim.TRADE_RETCODE_DONE, 10009)
        self.assertEqual(shim.TRADE_ACTION_DEAL, 1)
        self.assertEqual(shim.ORDER_FILLING_FOK, 0)

    def test_no_secret_is_embedded(self):
        import pathlib
        text = pathlib.Path(shim.__file__).read_text(encoding="utf-8")
        self.assertNotIn("eyJhbGciOiJSUzUxMiIs", text, "ห้ามมี token ฝังในไฟล์")
        # ห้ามมี UUID ของบัญชีฝังในไฟล์ — ตรวจจาก "รูปแบบ" ไม่ใช่ค่าจริง
        # (จงใจไม่เขียนค่าจริงลงในเทสต์ เพื่อไม่ให้ค่าจริงหลุดไปกับชุดแจกจ่าย)
        self.assertIsNone(
            re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text),
            "ห้ามมี account id (UUID) ฝังในไฟล์")


if __name__ == "__main__":
    unittest.main(verbosity=2)
