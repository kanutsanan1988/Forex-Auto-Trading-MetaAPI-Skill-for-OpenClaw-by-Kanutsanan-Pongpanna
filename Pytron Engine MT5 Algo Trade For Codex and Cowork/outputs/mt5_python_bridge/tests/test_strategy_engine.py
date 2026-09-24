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
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BRIDGE = Path(__file__).resolve().parents[1]
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

from auto_trader import risk_gate  # noqa: E402
import strategy_engine  # noqa: E402
from strategy_engine import classify_regime, decide_market  # noqa: E402


CONFIG = {
    "atr_stop_multiplier": 1.2,
    "min_reward_risk": 1.8,
    "max_spread": 0.6,
    "max_risk_pct": 8.0,
    "daily_loss_limit_pct": 20.0,
    "max_consecutive_losses": 5,
    "cooldown_minutes": 10,
    "strategy_router": {
        "enabled": True,
        "minimum_confidence": 0.74,
        "trend_adx_min": 25.0,
        "trend_regime_min_score": 0.68,
        "range_adx_max": 21.0,
        "range_regime_min_score": 0.65,
        "range_edge_fraction": 0.15,
        "range_rsi_buy_max": 36.0,
        "range_rsi_sell_min": 64.0,
        "range_stop_atr": 1.0,
        "mean_reversion_entry_z": 1.9,
        "mean_reversion_stop_atr": 1.1,
        "breakout_regime_min_score": 0.78,
        "breakout_buffer_atr": 0.08,
        "breakout_min_body_atr": 0.65,
        "breakout_volume_ratio_min": 1.3,
        "breakout_stop_atr": 1.25,
        "breakout_reward_risk": 2.0,
    },
}


def frame(**changes):
    result = {
        "trend": "neutral",
        "adx14": 15.0,
        "efficiency20": 0.20,
        "ema21_slope_atr": 0.0,
        "choppiness14": 60.0,
        "atr14": 5.0,
        "rsi14": 50.0,
        "previous_rsi14": 50.0,
        "last_closed": 100.0,
        "previous_close": 99.8,
        "ema9": 100.0,
        "previous_ema9": 100.0,
        "prior_high_20": 105.0,
        "prior_low_20": 95.0,
        "prior_high_20_before_previous": 105.0,
        "prior_low_20_before_previous": 95.0,
        "range_position_20": 0.5,
        "previous_range_position_20": 0.5,
        "bollinger_zscore20": 0.0,
        "previous_bollinger_zscore20": 0.0,
        "volume_ratio20": 1.0,
        "previous_volume_ratio20": 1.0,
        "body_atr": 0.2,
        "previous_body_atr": 0.2,
        "close_location": 0.5,
        "previous_close_location": 0.5,
        "candle_direction": "neutral",
    }
    result.update(changes)
    return result


class StrategyEngineTests(unittest.TestCase):
    def test_router_exposes_twelve_directional_scores(self):
        frames = {"M1": frame(), "M5": frame(), "M15": frame(), "H1": frame()}
        scores = classify_regime(frames, CONFIG)["scores"]
        directional = [key for key in scores if key.endswith("_buy") or key.endswith("_sell")]
        self.assertEqual(len(directional), 12)

    def test_failed_up_breakout_creates_sell_reversal_score(self):
        m5 = frame(
            previous_close=106.0, last_closed=104.0,
            prior_high_20_before_previous=105.0, candle_direction="bearish",
            close_location=0.25, previous_rsi14=72.0, rsi14=64.0,
            bollinger_zscore20=1.7, previous_bollinger_zscore20=2.1,
        )
        frames = {"M1": frame(), "M5": m5, "M15": frame(), "H1": frame()}
        decision = decide_market(frames, CONFIG)
        candidate = next(c for c in decision["candidates"] if c["strategy"] == "breakout_reversal")
        self.assertGreater(candidate["sell_score"], 0.0)
        self.assertTrue(candidate["eligible"])

    def _router_candidate(self, strategy, *, eligible=False, side=None, cross=False, setup=False):
        return {
            "strategy": strategy,
            "eligible": eligible,
            "side": side,
            "confidence": 0.0,
            "strength": 0.0,
            "buy_score": 0.0,
            "sell_score": 0.0,
            "reason": "test candidate",
            "stop_distance": 5.0,
            "reward_risk": 1.0,
            "pullback_resumption_cross": cross,
            "entry_checks_without_cross": setup,
        }

    def _trend_fallback_decision(self, range_buy, range_sell):
        config = copy.deepcopy(CONFIG)
        config["strategy_router"].update(
            agent_score_threshold=0.42,
            trend_opposite_runner_min_score=0.20,
        )
        regime = {
            "regime": "trend",
            "scores": {
                "trend_buy": 0.10, "trend_sell": 0.80,
                "range_buy": range_buy, "range_sell": range_sell,
                "mean_reversion_buy": 0.05, "mean_reversion_sell": 0.04,
                "breakout_buy": 0.0, "breakout_sell": 0.0,
            },
        }
        trend = self._router_candidate("trend", side="sell", cross=False)
        range_candidate = self._router_candidate("range")
        mean_reversion = self._router_candidate("mean_reversion")
        breakout = self._router_candidate("breakout")
        with (
            patch.object(strategy_engine, "classify_regime", return_value=regime),
            patch.object(strategy_engine, "trend_agent", return_value=trend),
            patch.object(strategy_engine, "range_agent", return_value=range_candidate),
            patch.object(strategy_engine, "mean_reversion_agent", return_value=mean_reversion),
            patch.object(strategy_engine, "breakout_agent", return_value=breakout),
        ):
            return strategy_engine.decide_market({"M5": {"atr14": 5.0}}, config)

    def test_score_threshold_allows_trend_without_cross(self):
        decision = self._trend_fallback_decision(range_buy=0.30, range_sell=0.10)
        self.assertEqual(decision["side"], "sell")

    def test_score_threshold_uses_probability_rank_before_strategy_checks(self):
        decision = self._trend_fallback_decision(range_buy=0.10, range_sell=0.30)
        self.assertEqual(decision["side"], "sell")

    def test_trend_score_inside_bypass_band_skips_only_m5_cross(self):
        config = copy.deepcopy(CONFIG)
        config["strategy_router"].update(
            agent_score_threshold=0.42,
            trend_cross_bypass_min_score=0.0,
            trend_cross_bypass_max_score=0.544,
        )
        regime = {
            "regime": "trend",
            "scores": {
                "trend_buy": 0.10, "trend_sell": 0.544,
                "range_buy": 0.08, "range_sell": 0.30,
                "mean_reversion_buy": 0.05, "mean_reversion_sell": 0.04,
                "breakout_buy": 0.0, "breakout_sell": 0.0,
            },
        }
        trend = self._router_candidate("trend", side="sell", cross=False, setup=True)
        with (
            patch.object(strategy_engine, "classify_regime", return_value=regime),
            patch.object(strategy_engine, "trend_agent", return_value=trend),
            patch.object(strategy_engine, "range_agent", return_value=self._router_candidate("range")),
            patch.object(strategy_engine, "mean_reversion_agent", return_value=self._router_candidate("mean_reversion")),
            patch.object(strategy_engine, "breakout_agent", return_value=self._router_candidate("breakout")),
        ):
            decision = strategy_engine.decide_market({"M5": {"atr14": 5.0}}, config)
        self.assertEqual(decision["strategy"], "trend")
        self.assertEqual(decision["side"], "sell")
        self.assertIn("passed score threshold", decision["reason"])

    def test_legacy_mode_uses_m5_m15_h1_without_router(self):
        config = copy.deepcopy(CONFIG)
        config["strategy_router"]["enabled"] = False
        frames = {
            "M5": frame(trend="bearish", rsi14=48.0),
            "M15": frame(trend="bearish"),
            "H1": frame(trend="bullish"),
        }
        decision = decide_market(frames, config)
        self.assertEqual(decision["side"], "sell")
        self.assertEqual(decision["strategy"], "trend_legacy")
        self.assertFalse(decision["router_enabled"])
        self.assertEqual(
            decision["regime"]["evidence"]["timeframe_trends"],
            {"M5": "bearish", "M15": "bearish", "H1": "bullish"},
        )

    def test_trend_regime_routes_to_trend_agent(self):
        frames = {
            "M5": frame(trend="bullish", adx14=28.0, efficiency20=0.62,
                        ema21_slope_atr=0.12, rsi14=55.0, last_closed=100.5,
                        candle_direction="bullish", close_location=0.75,
                        body_atr=0.3, volume_ratio20=1.0),
            "M15": frame(trend="bullish", adx14=31.0, efficiency20=0.70,
                         ema21_slope_atr=0.14),
            "H1": frame(trend="bullish", adx14=29.0, efficiency20=0.66,
                        ema21_slope_atr=0.10),
        }
        decision = decide_market(frames, CONFIG)
        self.assertEqual(decision["regime"]["regime"], "trend")
        self.assertEqual(decision["strategy"], "trend")
        self.assertEqual(decision["side"], "buy")

    def test_range_regime_waits_in_middle_of_range(self):
        frames = {name: frame() for name in ("M5", "M15", "H1")}
        decision = decide_market(frames, CONFIG)
        self.assertEqual(decision["regime"]["regime"], "range")
        self.assertIsNone(decision["side"])

    def test_range_and_mean_reversion_buy_at_lower_extreme(self):
        frames = {name: frame() for name in ("M5", "M15", "H1")}
        frames["M5"].update(
            previous_range_position_20=0.06, range_position_20=0.08,
            previous_rsi14=31.0, rsi14=34.0,
            previous_bollinger_zscore20=-2.1, bollinger_zscore20=-1.7,
            candle_direction="bullish", close_location=0.7,
        )
        decision = decide_market(frames, CONFIG)
        self.assertEqual(decision["regime"]["regime"], "range")
        self.assertEqual(decision["side"], "buy")
        self.assertIn(decision["strategy"], {"range", "mean_reversion"})

    def test_breakout_has_priority_over_trend(self):
        frames = {
            "M5": frame(trend="bullish", adx14=27.0, efficiency20=0.65,
                        ema21_slope_atr=0.12, rsi14=64.0, previous_close=106.0,
                        last_closed=106.4, prior_high_20_before_previous=105.0,
                        prior_high_20=106.2, previous_body_atr=0.8,
                        previous_volume_ratio20=1.5, previous_close_location=0.9,
                        close_location=0.7, candle_direction="bullish"),
            "M15": frame(trend="bullish", adx14=29.0, efficiency20=0.70,
                         ema21_slope_atr=0.13),
            "H1": frame(trend="bullish", adx14=28.0, efficiency20=0.60,
                        ema21_slope_atr=0.10),
        }
        decision = decide_market(frames, CONFIG)
        self.assertEqual(decision["regime"]["regime"], "breakout")
        self.assertEqual(decision["strategy"], "breakout")
        self.assertEqual(decision["side"], "buy")

    def test_transition_rejects_unclear_market(self):
        frames = {name: frame(adx14=21.0, choppiness14=44.0, efficiency20=0.45)
                  for name in ("M5", "M15", "H1")}
        regime = classify_regime(frames, CONFIG)
        decision = decide_market(frames, CONFIG)
        self.assertEqual(regime["regime"], "transition")
        self.assertIsNone(decision["side"])

    def test_validation_lock_keeps_agent_analysis_but_blocks_order_direction(self):
        config = copy.deepcopy(CONFIG)
        config["strategy_router"]["trade_enabled"] = {
            "trend": False,
            "range": False,
            "mean_reversion": False,
            "breakout": False,
        }
        frames = {
            "M5": frame(
                trend="bullish", adx14=28.0, efficiency20=0.62,
                ema21_slope_atr=0.12, rsi14=55.0, last_closed=100.5,
                candle_direction="bullish", close_location=0.75,
                body_atr=0.3, volume_ratio20=1.0,
            ),
            "M15": frame(trend="bullish", adx14=31.0, efficiency20=0.70,
                         ema21_slope_atr=0.14),
            "H1": frame(trend="bullish", adx14=29.0, efficiency20=0.66,
                        ema21_slope_atr=0.10),
        }
        decision = decide_market(frames, config)
        trend = next(candidate for candidate in decision["candidates"] if candidate["strategy"] == "trend")
        self.assertTrue(trend["eligible"])
        self.assertFalse(trend["trade_enabled"])
        self.assertIsNone(decision["side"])
        self.assertIn("validation-locked", decision["reason"])

    def test_daily_limit_checks_projected_stop_loss(self):
        config = copy.deepcopy(CONFIG)
        state = {
            "day_start_equity": 100.0,
            "consecutive_losses": 0,
            "last_trade_time": 0,
        }
        account = SimpleNamespace(equity=85.0)
        analysis = {
            "side": "buy",
            "spread": 0.2,
            "risk_pct": 5.0,
            "risk_usd": 5.0,
            "decision": {"reason": "candidate"},
        }
        allowed, reason = risk_gate(config, state, account, analysis)
        self.assertTrue(allowed)
        self.assertEqual(reason, "passed")
        analysis["risk_usd"] = 5.01
        allowed, reason = risk_gate(config, state, account, analysis)
        self.assertFalse(allowed)
        self.assertEqual(reason, "projected daily loss limit exceeded")


if __name__ == "__main__":
    unittest.main()
