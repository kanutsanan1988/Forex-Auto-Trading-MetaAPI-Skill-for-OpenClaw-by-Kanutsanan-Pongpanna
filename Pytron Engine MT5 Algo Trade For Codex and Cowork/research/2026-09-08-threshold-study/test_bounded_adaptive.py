# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
BRIDGE = ROOT / "outputs" / "mt5_python_bridge"
sys.path.insert(0, str(BRIDGE))

import bounded_adaptive_research as bar
import auto_trader as at
import strategy_engine as se


def config():
    data = json.loads((BRIDGE / "auto_config.json").read_text(encoding="utf-8"))
    data["strategy_router"]["directional_probabilities"] = {key: .60 for key in bar.KEYS}
    data["strategy_router"]["directional_weights"] = {key: 1.0 for key in bar.KEYS}
    data["strategy_router"]["strategy_weights"] = {family: 1.0 for family in bar.FAMILIES}
    return data


def agent(name, eligible=False, side=None):
    return {"strategy": name, "eligible": eligible, "side": side, "confidence": 0.0,
            "stop_distance": None, "reward_risk": None, "reason": "synthetic"}


class BoundedAdaptiveTests(unittest.TestCase):
    def test_wait_is_interrupted_immediately_by_kill_switch(self):
        with patch.object(at, "STOP_FILE") as stop_file:
            stop_file.exists.return_value = True
            self.assertFalse(at.interruptible_wait(60.0))

    def test_research_observer_cannot_apply_to_live(self):
        with self.assertRaises(ValueError):
            bar.validate_settings({"mode": "shadow_only", "apply_to_live": True})

    def test_shadow_snapshot_does_not_change_production_decision(self):
        cfg = config()
        scores = {key: 0.0 for key in bar.KEYS}
        scores["trend_buy"] = .65
        candidates = [agent(family, family == "trend", "buy" if family == "trend" else None)
                      for family in bar.FAMILIES]
        candidates[0].update(raw_buy_score=.65, raw_sell_score=0.0, buy_score=.65, sell_score=0.0)
        decision = {"side": "buy", "strategy": "trend", "confidence": .65,
                    "regime": {"regime": "trend", "scores": scores}, "candidates": candidates}
        analysis = {"technical_decision": decision, "spread": .20,
                    "stop_distance": 2.0, "frames": {"M5": {"atr14": 2.0}}}
        state = {"adaptive_shadow": {"outcomes": []}}
        before = copy.deepcopy(decision)
        snapshot = bar.evaluate_shadow(cfg, state, analysis, {"closed": []})
        self.assertEqual(decision, before)
        self.assertTrue(snapshot["production_decision_unchanged"])
        self.assertFalse(snapshot["apply_to_live"])

    def test_live_requires_all_three_numerical_agent_gates(self):
        cfg = config()
        scores = {key: 0.0 for key in bar.KEYS}
        scores["trend_buy"] = .65
        regime = {"regime": "trend", "direction": "buy", "scores": scores}
        stubs = [agent(family, family == "trend", "buy" if family == "trend" else None)
                 for family in ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")]
        funcs = ("trend_agent", "range_agent", "mean_reversion_agent", "breakout_agent", "counter_trend_agent", "breakout_reversal_agent")
        patches = [patch.object(se, name, return_value=value) for name, value in zip(funcs, stubs)]
        for item in patches: item.start()
        try:
            with patch.object(se, "classify_regime", return_value=regime):
                result = se.decide_market({"M5": {"atr14": 2.0}}, cfg)
        finally:
            for item in reversed(patches): item.stop()
        self.assertEqual((result["strategy"], result["side"]), ("trend", "buy"))
        self.assertTrue(result["bounded_live"])
        passed = [row for row in result["bounded_live_diagnostics"] if row["passed"]]
        self.assertEqual([(x["strategy"], x["side"]) for x in passed], [("trend", "buy")])

    def test_structural_failure_is_diagnostic_only(self):
        cfg = config()
        scores = {key: 0.0 for key in bar.KEYS}
        scores["trend_buy"] = .90
        regime = {"regime": "trend", "direction": "buy", "scores": scores}
        stubs = [agent(family, False, None) for family in
                 ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")]
        funcs = ("trend_agent", "range_agent", "mean_reversion_agent", "breakout_agent", "counter_trend_agent", "breakout_reversal_agent")
        patches = [patch.object(se, name, return_value=value) for name, value in zip(funcs, stubs)]
        for item in patches: item.start()
        try:
            with patch.object(se, "classify_regime", return_value=regime):
                result = se.decide_market({"M5": {"atr14": 2.0}}, cfg)
        finally:
            for item in reversed(patches): item.stop()
        self.assertEqual((result["strategy"], result["side"]), ("trend", "buy"))
        passed = [row for row in result["bounded_live_diagnostics"] if row["passed"]]
        self.assertEqual([(x["strategy"], x["side"]) for x in passed], [("trend", "buy")])
        self.assertFalse(passed[0]["structural_confirmed"])
        self.assertEqual(passed[0]["structural_mode"], "diagnostic_only")


if __name__ == "__main__":
    unittest.main()
