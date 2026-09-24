# Python Qaunt Trading + AI(LLM) Live Research
# Creator: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""Broker failure/partial-close regressions; every MT5 interaction is mocked."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import auto_trader as trader
import live_executor
import trade_guard


class PositionConfirmationTests(unittest.TestCase):
    def test_unknown_is_not_empty(self):
        with patch.object(trader.mt5, 'positions_get', return_value=None), self.assertRaises(RuntimeError):
            trader.checked_positions('TEST')

    def test_genuinely_empty_is_accepted(self):
        with patch.object(trader.mt5, 'positions_get', return_value=()):
            self.assertEqual(trader.checked_positions('TEST'), ())

    def test_pending_close_blocks_replacement(self):
        with patch.object(trader, 'checked_positions', return_value=(SimpleNamespace(ticket=7),)), \
             patch.object(trader.time, 'monotonic', side_effect=[0, 4]), patch.object(trader, 'audit'), \
             self.assertRaisesRegex(RuntimeError, 'pending'):
            trader.wait_for_closed_positions({'symbol': 'TEST'}, {7})

    def test_confirmed_close_preserves_other_positions(self):
        other = SimpleNamespace(ticket=8)
        with patch.object(trader, 'checked_positions', return_value=(other,)), patch.object(trader, 'audit'):
            self.assertEqual(trader.wait_for_closed_positions({'symbol': 'TEST'}, {7}), (other,))

    def test_manual_executor_rejects_unknown_positions(self):
        with patch.object(live_executor, 'connect', return_value=(None, None, None)), \
             patch.object(live_executor.mt5, 'symbol_info_tick', return_value=SimpleNamespace()), \
             patch.object(live_executor.mt5, 'positions_get', return_value=None), \
             self.assertRaisesRegex(RuntimeError, 'position state unavailable'):
            live_executor.validate({})

    def test_snapshot_does_not_report_unknown_as_zero_positions(self):
        with patch.object(trade_guard, 'connect', return_value=(None, None, None)), \
             patch.object(trade_guard.mt5, 'symbol_info_tick', return_value=None), \
             patch.object(trade_guard.mt5, 'positions_get', return_value=None), \
             self.assertRaisesRegex(RuntimeError, 'position state unavailable'):
            trade_guard.snapshot()

    def test_early_cut_waits_after_partial_success(self):
        cfg = {'symbol': 'TEST', 'magic': 42, 'deviation_points': 10, 'live_enabled': True}
        position = SimpleNamespace(ticket=7, symbol='TEST', magic=42,
            type=trader.mt5.POSITION_TYPE_BUY, profit=-1, volume=.01)
        result = SimpleNamespace(retcode=trader.mt5.TRADE_RETCODE_DONE_PARTIAL, _asdict=lambda: {'partial': True})
        with patch.object(trader, 'checked_positions', return_value=(position,)), \
             patch.object(trader.mt5, 'symbol_info_tick', return_value=SimpleNamespace(bid=1, ask=2)), \
             patch.object(trader.mt5, 'order_check', return_value=SimpleNamespace(retcode=0)), \
             patch.object(trader.mt5, 'order_send', return_value=result) as send, \
             patch.object(trader, 'audit'), \
             patch.object(trader, 'wait_for_closed_positions', side_effect=RuntimeError('pending')) as confirm:
            with self.assertRaisesRegex(RuntimeError, 'pending'):
                trader.early_cut_losing_positions(cfg, SimpleNamespace(trade_allowed=True),
                    SimpleNamespace(trade_allowed=True), {'side': 'sell'}, live=True)
            confirm.assert_called_once_with(cfg, {7})
            send.assert_called_once()


if __name__ == '__main__':
    unittest.main(verbosity=2)
