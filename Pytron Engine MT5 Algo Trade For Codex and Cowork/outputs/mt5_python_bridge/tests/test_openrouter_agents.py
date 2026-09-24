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
import os
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BRIDGE = Path(__file__).resolve().parents[1]
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))

import auto_trader  # noqa: E402
import openrouter_agents as agents  # noqa: E402


PYTHON_DECISION = {
    "side": "buy",
    "strategy": "trend",
    "confidence": 0.8,
    "reason": "Python trend evidence",
    "stop_distance": 2.0,
    "reward_risk": 1.8,
    "regime": {"regime": "trend"},
    "candidates": [{
        "strategy": "trend", "side": "buy", "eligible": True,
        "trade_enabled": True, "confidence": 0.8,
        "stop_distance": 2.0, "reward_risk": 1.8,
    }],
}


class OpenRouterAgentTests(unittest.TestCase):
    def config(self, **changes):
        settings = {"enabled": True, "cache_seconds": 0, "judge_min_confidence": 0.55,
                    "fallback_to_python": True}
        settings.update(changes)
        return {"openrouter": settings}

    def test_nested_key_file_configuration_is_supported(self):
        with tempfile.TemporaryDirectory() as folder:
            key_file = Path(folder) / "key.txt"
            key_file.write_text("test-key", encoding="utf-8")
            config = {"openrouter": {"api_key_env": "TEST_OPENROUTER_KEY_NOT_SET",
                                     "api_key_file": str(key_file)}}
            with patch.dict(os.environ, {}, clear=False):
                self.assertEqual(agents.load_api_key(config), "test-key")

    def test_signal_schema_rejects_unknown_strategy(self):
        response = {"side": "buy", "strategy": "invented", "confidence": 0.8,
                    "reason": "x", "supporting_evidence": ["x"], "risks": ["x"]}
        with patch.object(agents, "_call", return_value=response):
            with self.assertRaises(agents.OpenRouterError):
                agents.get_signal(self.config(), {})

    def test_judge_must_match_selected_group_direction(self):
        response = {"decision": "sell", "selected_group": "python", "confidence": 0.8,
                    "reason": "x", "agreement": "disagree", "risks": ["x"]}
        with patch.object(agents, "_call", return_value=response):
            with self.assertRaises(agents.OpenRouterError):
                agents.judge(self.config(), {}, {"side": "buy"}, {"side": "sell"})

    def test_low_confidence_judge_is_forced_to_no_trade(self):
        signal = {"side": "buy", "strategy": "trend", "confidence": 0.7,
                  "reason": "x", "supporting_evidence": ["x"], "risks": ["x"]}
        judge = {"decision": "buy", "selected_group": "python", "confidence": 0.4,
                 "reason": "weak", "agreement": "agree", "risks": ["x"]}
        with patch.object(agents, "_ai_mode_allowed", return_value=(True, None)), \
             patch.object(agents, "get_signal", return_value=signal), \
             patch.object(agents, "judge", return_value=judge), \
             patch.object(agents, "_save_cache"):
            result = agents.run_dual_agents(self.config(), {}, copy.deepcopy(PYTHON_DECISION))
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["trade_decision"]["side"])
        self.assertEqual(result["judge"]["decision"], "no_trade")

    def test_agent_failure_falls_back_to_original_python_decision(self):
        with patch.object(agents, "_ai_mode_allowed", return_value=(True, None)), \
             patch.object(agents, "get_signal", side_effect=agents.OpenRouterError("offline")):
            result = agents.run_dual_agents(self.config(), {}, copy.deepcopy(PYTHON_DECISION))
        self.assertEqual(result["status"], "fallback_python")
        self.assertTrue(result["fallback"])
        self.assertEqual(result["trade_decision"]["side"], "buy")
        self.assertEqual(result["trade_decision"]["strategy"], "trend")

    def test_optional_strict_mode_remains_fail_closed(self):
        with patch.object(agents, "_ai_mode_allowed", return_value=(True, None)), \
             patch.object(agents, "get_signal", side_effect=agents.OpenRouterError("offline")):
            result = agents.run_dual_agents(
                self.config(fallback_to_python=False), {}, copy.deepcopy(PYTHON_DECISION)
            )
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["trade_decision"]["side"])

    def test_mode_one_blocks_openrouter_even_when_provider_is_enabled(self):
        with patch.object(agents, "_ai_mode_allowed", return_value=(False, "AI integrations are disabled in mode 1")), \
             patch.object(agents, "get_signal") as get_signal:
            result = agents.run_dual_agents(self.config(), {}, copy.deepcopy(PYTHON_DECISION))
        self.assertEqual(result["status"], "blocked_by_mode")
        self.assertFalse(result["enabled"])
        self.assertEqual(result["trade_decision"]["side"], "buy")
        get_signal.assert_not_called()

    def test_retry_recovers_from_one_connection_error(self):
        envelope = {"choices": [{"message": {"content": '{"status":"ok"}'}}]}

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return __import__("json").dumps(envelope).encode("utf-8")

        with patch.object(agents, "load_api_key", return_value="test-key"), \
             patch.object(agents.urllib.request, "urlopen",
                          side_effect=[urllib.error.URLError("temporary"), Response()]) as urlopen:
            result = agents._call(
                self.config(max_attempts=2, retry_delay_seconds=0), "Return JSON", {"test": True}
            )
        self.assertEqual(result, {"status": "ok"})
        self.assertEqual(urlopen.call_count, 2)

    def test_successful_result_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(agents, "_cache_path", return_value=Path(folder) / "cache.json"):
            expected = {"status": "ok", "cached": False, "trade_decision": {"side": "buy"}}
            agents._save_cache("abc", expected)
            loaded = agents._load_cache(self.config(cache_seconds=90), "abc")
        self.assertIsNotNone(loaded)
        self.assertTrue(loaded["cached"])
        self.assertEqual(loaded["trade_decision"]["side"], "buy")

    def test_openrouter_failure_preserves_existing_position(self):
        position = SimpleNamespace(ticket=123, magic=99)
        config = {"symbol": "XAUUSD", "magic": 99,
                  "profit_exit": {"enabled": True, "minimum_profit_usd": 0.0}}
        with patch.object(auto_trader.mt5, "positions_get", return_value=[position]), \
             patch.object(auto_trader.mt5, "order_check") as order_check, \
             patch.object(auto_trader, "audit") as audit:
            closed, suppress = auto_trader.manage_profitable_positions(
                config, live=True, terminal=SimpleNamespace(), account=SimpleNamespace(),
                desired_side=None, signal_reliable=False,
            )
        self.assertEqual(closed, set())
        self.assertFalse(suppress)
        order_check.assert_not_called()
        audit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
