# -*- coding: utf-8 -*-
"""ชุดทดสอบ position_protection — ไม้ที่ไม่มี TP/SL ต้องได้ครบ · ไม้ที่มีอยู่แล้วห้ามแตะ"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import position_protection as pp  # noqa: E402


class Pos:
    def __init__(self, ticket, typ, price_open, sl=0.0, tp=0.0):
        self.ticket = ticket
        self.type = typ              # 0 = buy · 1 = sell
        self.price_open = price_open
        self.sl = sl
        self.tp = tp


class Res:
    def __init__(self, retcode=10009):
        self.retcode = retcode
        self.comment = "done"


class FakeMT5:
    TIMEFRAME_M5 = 5
    TRADE_ACTION_SLTP = 1
    TRADE_RETCODE_DONE = 10009

    def __init__(self, positions, ask=4000.0, bid=3999.0):
        self._pos = positions
        self.ask = ask
        self.bid = bid
        self.sent = []

    def positions_get(self, symbol=None):
        return self._pos

    def copy_rates_from_pos(self, symbol, tf, start, n):
        # ATR ≈ 4.0 (high 4002, low 3998, prev close 4000 ต่อแท่ง)
        return [[0, 4000.0, 4002.0, 3998.0, 4000.0, 1]] * 20

    def symbol_info(self, symbol):
        class S:
            trade_stops_level = 30
            point = 0.01
        return S()

    def symbol_info_tick(self, symbol):
        class T:
            pass
        t = T()
        t.ask, t.bid = self.ask, self.bid
        return t

    def order_send(self, req):
        self.sent.append(req)
        return Res()


def test_buy_without_sltp_gets_both():
    m = FakeMT5([Pos(1, 0, 4000.0)])
    out = pp.scan(m, "XAUUSD", {}, dry_run=False)
    assert len(out) == 1 and out[0]["action"] == "set" and out[0].get("ok") is True
    req = m.sent[0]
    assert req["sl"] < 4000.0 and req["tp"] > 4000.0, "buy: SL ต้องต่ำกว่า · TP ต้องสูงกว่าราคา"


def test_sell_without_sltp_gets_both():
    m = FakeMT5([Pos(2, 1, 4000.0)], ask=4001.0, bid=4000.0)
    out = pp.scan(m, "XAUUSD", {}, dry_run=False)
    assert out and out[0]["side"] == "sell"
    req = m.sent[0]
    assert req["sl"] > 4000.0 and req["tp"] < 4000.0, "sell: SL ต้องสูงกว่า · TP ต้องต่ำกว่าราคา"


def test_existing_sltp_untouched():
    m = FakeMT5([Pos(3, 0, 4000.0, sl=3990.0, tp=4020.0)])
    out = pp.scan(m, "XAUUSD", {}, dry_run=False)
    assert out == [] and m.sent == [], "ไม้ที่มี SL/TP อยู่แล้วห้ามแตะ"


def test_partial_missing_is_filled():
    m = FakeMT5([Pos(4, 0, 4000.0, sl=3990.0, tp=0.0)])
    out = pp.scan(m, "XAUUSD", {}, dry_run=False)
    assert len(out) == 1 and out[0]["had_sl"] is True and out[0]["had_tp"] is False
    assert m.sent[0]["sl"] == 3990.0, "SL เดิมต้องคงไว้ · เติมเฉพาะ TP ที่ขาด"


def test_dry_run_does_not_send():
    m = FakeMT5([Pos(5, 0, 4000.0)])
    out = pp.scan(m, "XAUUSD", {}, dry_run=True)
    assert out and out[0]["action"] == "would_set" and m.sent == []


def test_profit_position_locks_in():
    """ไม้ buy กำไรอยู่ → SL ต้องไม่ต่ำกว่าราคาเข้า (ล็อกกำไรบางส่วน)"""
    m = FakeMT5([Pos(6, 0, 3990.0)], ask=4010.0, bid=4009.0)
    out = pp.scan(m, "XAUUSD", {}, dry_run=False)
    assert out[0]["sl"] >= 3990.0, "ราคาเข้าต่ำกว่าปัจจุบัน → SL ควรผูกกับราคาปัจจุบัน (แคบกว่า/ล็อกกำไร)"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("  ✓ %s" % name)
    print("ผ่านทั้งหมด")