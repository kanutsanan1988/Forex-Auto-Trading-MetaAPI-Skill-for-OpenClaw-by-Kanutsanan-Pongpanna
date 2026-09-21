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
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from adaptive_shadow import health_check, prepare_cycle, update_after_analysis


def config():
    return {
        "strategy_router": {
            "adaptive": {
                "shadow_enabled": True, "shadow_min_score": 0.2,
                "shadow_max_hold_bars": 2, "shadow_history_limit": 400,
                "decay_half_life": 40,
            }
        }
    }


class AdaptiveShadowTests(unittest.TestCase):
    def test_shadow_opens_and_resolves_without_real_order(self):
        state = {}
        decision = {
            "regime": {"regime": "trend"},
            "candidates": [{"strategy": "trend", "buy_score": 0.8, "sell_score": 0.1}],
        }
        frames = {"M1": {"time": 100, "open": 100, "high": 101, "low": 99, "close": 100}, "M5": {"atr14": 2}}
        first = update_after_analysis(state, decision, frames, config())
        self.assertEqual(first["open_count"], 1)
        frames["M1"].update(time=160, high=103, low=100, close=102)
        second = update_after_analysis(state, decision, frames, config())
        self.assertTrue(second["closed"])
        self.assertEqual(second["closed"][0]["reason"], "tp")

    def test_walk_forward_weight_is_directional_and_bounded(self):
        outcomes = []
        for index in range(16):
            outcomes.append({"strategy": "trend", "side": "buy", "regime": "trend", "r_multiple": 1.0, "closed_bar_time": index})
        state = {"adaptive_shadow": {"version": 2, "positions": {}, "outcomes": outcomes, "last_regime": "trend"}}
        updated, summary = prepare_cycle(config(), state)
        weight = updated["strategy_router"]["directional_weights"]["trend_buy"]
        self.assertGreater(weight, 1.0)
        self.assertLessEqual(weight, 1.25)
        self.assertTrue(summary["metrics"]["trend"]["buy"]["validated"])

    def test_health_check_blocks_stale_tick(self):
        frame = {"time": 990, "open": 1, "high": 2, "low": 1, "close": 1.5, "atr14": 0.1}
        frames = {name: dict(frame) for name in ("M1", "M5", "M15", "H1")}
        ok, reasons = health_check(frames, SimpleNamespace(ask=2, bid=1.9, time=1), 1.0, 1000)
        self.assertFalse(ok)
        self.assertIn("stale tick", reasons)

    def test_probability_model_produces_all_twelve_weights(self):
        state = {}
        decision = {"regime": {"regime": "trend", "scores": {"trend_sell": 0.8}}, "candidates": [{"strategy": "trend", "sell_score": 0.8}]}
        frames = {"M1": {"time": 100, "open": 100, "high": 100, "low": 100, "close": 100}, "M5": {"atr14": 2}}
        result = update_after_analysis(state, decision, frames, config())
        self.assertEqual(len(state["adaptive_shadow"]["probability_weights"]), 12)
        self.assertIn("probability_metrics", result)


if __name__ == "__main__":
    unittest.main()
