# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Admin permission and transaction regressions; temporary files/mocks only."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BR))
sys.path.insert(0, str(BR / 'tools'))
import runtime_support as rs
import admin_config as ac
import admin_command as cmd
import admin_bot_round as ab


class AdminConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='admin-offline-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'config.json'
        self.cfg = {'live_enabled': False, 'symbol': 'TEST', 'magic': 42, 'volume': .01,
                    'cooldown_minutes': 5.0, 'early_cut': {'enabled': False},
                    'count': 10, 'unrelated': {'value': 'current'}}
        self.bounds = {'cooldown_minutes': (0, 20), 'early_cut.enabled': (0, 1), 'count': (1, 30)}
        rs.atomic_json(self.path, self.cfg)
        rs.atomic_json(self.root / 'work/trading_mode.json', {'mode': 'internal_llm_join', 'epoch': 'test'})

    def apply(self, values, **kwargs):
        return ac.apply_values(self.path, values, self.bounds, root=self.root, **kwargs)

    def test_restore_preserves_reserved_and_unrelated(self):
        old = dict(self.cfg, live_enabled=True, magic=999, volume=5, symbol='WRONG',
                   cooldown_minutes=2.0, unrelated={'value': 'old'})
        cfg, changes = ac.restore_values(self.path, old, self.bounds, root=self.root)
        self.assertEqual(cfg['cooldown_minutes'], 2.0)
        for key in ('live_enabled', 'magic', 'volume', 'symbol', 'unrelated'):
            self.assertEqual(cfg[key], self.cfg[key])
        self.assertEqual(len(changes), 1)

    def test_protected_even_if_accidentally_allowlisted(self):
        self.bounds['volume'] = (0, 5)
        with self.assertRaises(ValueError): self.apply({'volume': 1})
        self.assertEqual(json.loads(self.path.read_text()), self.cfg)

    def test_reject_invalid_values_atomically(self):
        for values in ({'cooldown_minutes': float('nan')}, {'count': 10.5},
                       {'early_cut.enabled': .5}, {'cooldown_minutes': 21},
                       {'unknown': 1}, {'cooldown_minutes': 2, 'count': 100}):
            with self.subTest(values=values):
                with self.assertRaises(ValueError): self.apply(values)
                self.assertEqual(json.loads(self.path.read_text()), self.cfg)
        self.assertEqual(list(self.root.glob('config.json.bak*')), [])

    def test_bool_and_integer_types_preserved(self):
        cfg, _ = self.apply({'early_cut.enabled': 1.0, 'count': 12.0})
        self.assertIs(cfg['early_cut']['enabled'], True)
        self.assertIs(type(cfg['count']), int)

    def test_stale_baseline_rejected_without_lost_update(self):
        baseline = rs.digest(self.cfg)
        rs.update_json(self.path, lambda c: dict(c, volume=.02))
        with self.assertRaises(ValueError): self.apply({'cooldown_minutes': 3}, expected_hash=baseline)
        self.assertEqual(json.loads(self.path.read_text())['volume'], .02)

    def test_backup_names_do_not_collide(self):
        self.apply({'cooldown_minutes': 4})
        self.apply({'cooldown_minutes': 3})
        backups = list(self.root.glob('config.json.bak_admincmd_*'))
        self.assertEqual(len(backups), 2)
        self.assertEqual({json.loads(p.read_text())['cooldown_minutes'] for p in backups}, {4, 5})

    def test_mode_and_stop_block_direct_transactions(self):
        rs.atomic_json(self.root / 'work/trading_mode.json', {'mode': 'internal_only'})
        with self.assertRaises(ValueError): self.apply({'cooldown_minutes': 2})
        rs.atomic_json(self.root / 'work/trading_mode.json', {'mode': 'internal_llm_join'})
        (self.root / 'work/AUTO_TRADER_STOP').touch()
        with self.assertRaises(ValueError): self.apply({'cooldown_minutes': 2})

    def test_direct_admin_apply_guard_precedes_external_calls(self):
        (self.root / 'work/AUTO_TRADER_STOP').touch()
        with patch.object(ab, 'ROOT', str(self.root)), patch.object(sys, 'argv', ['admin', '--apply']), \
             patch.object(ab, 'gather') as gather, patch.object(ab, 'equity_now') as eq:
            with self.assertRaises(ValueError): ab.main()
            gather.assert_not_called()
            eq.assert_not_called()

    def test_advisory_does_not_rollback_or_change_config(self):
        stats = dict(trades=10, win_rate=50, net=-5, avg_win=.1, avg_loss=-1,
                     no_trade_rounds=50, revenge_armed=0, early_cut=0, close_ticker=0)
        prev = {'last_apply': ab.now_utc().isoformat(), 'equity_at_apply': 100,
                'config_hash': rs.digest(self.cfg)}
        rs.atomic_json(self.root / 'state.json', prev)
        rs.atomic_json(str(self.path) + '.bak_adminbot_recent', dict(self.cfg, live_enabled=True))
        with patch.multiple(ab, ROOT=str(self.root), CFG=str(self.path),
                            STATE=str(self.root / 'state.json'), LOG=str(self.root / 'log.jsonl'),
                            PLAN=str(self.root / 'plan.json'), news_feed=None), \
             patch.object(ab, 'gather', return_value=stats), patch.object(ab, 'equity_now', return_value=90), \
             patch.object(sys, 'argv', ['admin']), contextlib.redirect_stdout(io.StringIO()):
            ab.main()
        self.assertEqual(json.loads(self.path.read_text()), self.cfg)

    def test_latest_backup_is_by_mtime(self):
        older = Path(str(self.path) + '.bak_admincmd_zzz')
        newer = Path(str(self.path) + '.bak_adminbot_aaa')
        rs.atomic_json(older, dict(self.cfg, cooldown_minutes=1.0))
        rs.atomic_json(newer, dict(self.cfg, cooldown_minutes=3.0))
        os.utime(older, (100, 100)); os.utime(newer, (200, 200))
        with patch.multiple(cmd, CFG=str(self.path), ROOT=str(self.root)), \
             patch.object(cmd, 'bounds', return_value=self.bounds), patch.object(cmd, 'log'), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cmd.cmd_rollback_last(), 0)
        self.assertEqual(json.loads(self.path.read_text())['cooldown_minutes'], 3)

    def test_simulation_and_job_scope(self):
        with patch.object(cmd.subprocess, 'run') as run, contextlib.redirect_stdout(io.StringIO()):
            for value in ('../other_sim.py', '..\\other_sim.py', 'C:\\other_sim.py', '/other_sim.py'):
                self.assertNotEqual(cmd.cmd_simulation(value), 0)
            self.assertNotEqual(cmd.cmd_job('resume', 'unrelated-user-job'), 0)
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
