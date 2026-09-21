# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Offline regression tests: no scheduler, broker, bot or live orders are called."""
import datetime as dt
import ast
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BR))
import choose_mode as modes
import runtime_support as support
import market_clock


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ModeContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='mode-contract-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {'TRADING_PROJECT_ROOT': str(self.root)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config = self.root / 'outputs/mt5_python_bridge/auto_config.json'
        support.atomic_json(self.config, {'live_enabled': False,
            'strategy_router': {'directional_weights': {'trend_buy': 1.05},
                                'strategy_weights': {'trend': 1.2}}})
        self.mode('internal_llm_join')

    def mode(self, value):
        support.atomic_json(self.root / 'work/trading_mode.json',
            {'mode': value, 'epoch': 'test-epoch', 'title': support.MODE_TITLES.get(value, value)})

    def test_internal_keeps_all_python_and_disables_both_bots(self):
        with patch.object(modes, 'cron') as cron:
            modes.resume_selected('internal_only')
        actions = [c.args for c in cron.call_args_list]
        self.assertEqual({n for a, n in actions if a == 'resume'},
            {'trading-analytics', 'llm-recommendation-consumer', 'trading-daily-research-log'})
        self.assertEqual({n for a, n in actions if a == 'pause'}, {modes.RESEARCH_JOB, modes.ADMIN_JOB})

    def test_ai_keeps_python_and_enables_both_bots(self):
        with patch.object(modes, 'cron') as cron:
            modes.resume_selected('internal_llm_join')
        self.assertEqual({c.args[1] for c in cron.call_args_list if c.args[0] == 'resume'}, set(modes.JOBS))

    def test_bad_mode_has_no_scheduler_side_effect(self):
        with patch.object(modes, 'cron') as cron, self.assertRaises(ValueError):
            modes.resume_selected('bad-mode')
        cron.assert_not_called()

    def test_partial_activation_pauses_every_job(self):
        seen = []
        def fake(action, name):
            seen.append((action, name))
            if action == 'resume' and name == modes.ADMIN_JOB:
                raise RuntimeError('simulated scheduler failure')
        with patch.object(modes, 'cron', side_effect=fake), self.assertRaises(RuntimeError):
            modes.resume_selected('internal_llm_join')
        self.assertEqual(seen[-len(modes.JOBS):], [('pause', n) for n in modes.JOBS])

    def test_select_while_stopped_does_not_resume_or_change_live_permission(self):
        stop = self.root / 'work/AUTO_TRADER_STOP'
        stop.touch()
        with patch.object(modes, 'pause_all'), patch.object(modes, 'resume_selected') as resume:
            result = modes.select_mode('internal_only', self.root)
        resume.assert_not_called()
        self.assertTrue(stop.exists())
        self.assertNotEqual(result['epoch'], 'test-epoch')
        cfg = json.loads(self.config.read_text(encoding='utf-8'))
        self.assertFalse(cfg['live_enabled'])
        self.assertEqual(cfg['strategy_router']['strategy_weights'], {'trend': 1.2})
        self.assertEqual(len(cfg['strategy_router']['directional_weights']), 12)

    def test_default_enter_selects_ai_mode_without_starting(self):
        with patch.object(sys, 'argv', ['choose_mode.py']), patch('builtins.input', return_value=''), \
             patch.object(modes, 'select_mode') as select:
            self.assertEqual(modes.main(), 0)
        select.assert_called_once_with('internal_llm_join')

    def test_default_mode_names(self):
        self.assertEqual(support.DEFAULT_MODE, 'internal_llm_join')
        self.assertEqual(support.MODE_TITLES['internal_llm_join'], 'เทรดร่วมสัญญาณ AI')
        self.assertEqual(support.MODE_TITLES['internal_only'], 'เทรดด้วยสัญญาณภายใน')

    def test_ai_guard_blocks_mode1(self):
        self.mode('internal_only')
        with self.assertRaisesRegex(ValueError, 'mode 1'):
            support.require_ai_mode(self.root)

    def test_ai_guard_blocks_stop(self):
        (self.root / 'work/AUTO_TRADER_STOP').touch()
        with self.assertRaisesRegex(ValueError, 'Kill switch'):
            support.require_ai_mode(self.root)

    def test_ai_guard_accepts_valid_mode2(self):
        self.assertEqual(support.require_ai_mode(self.root)['mode'], 'internal_llm_join')

    def test_unknown_mode_does_not_silently_enable_ai(self):
        self.mode('bad-mode')
        with self.assertRaises(ValueError):
            support.require_ai_mode(self.root)

    def test_run_bot_guard_prevents_process_launch(self):
        bot = load_module('test_run_bot_guard', BR.parents[1] / 'agents/run_bot.py')
        with patch.object(bot, 'ROOT', str(self.root)), patch.object(bot, 'load_registry') as registry, \
             patch.object(bot.subprocess, 'run') as launch:
            self.mode('internal_only')
            self.assertEqual(bot.run('admin', 'test', False), 9)
        registry.assert_not_called()
        launch.assert_not_called()

    def test_admin_mutation_blocked_in_mode1(self):
        admin = load_module('test_admin_guard', BR / 'tools/admin_command.py')
        self.mode('internal_only')
        with patch.object(admin, 'ROOT', str(self.root)), patch.object(admin, 'cmd_set_value') as mutate, \
             patch.object(sys, 'argv', ['admin_command.py', '--run', 'set_value', '--key', 'x', '--value', '1']):
            self.assertEqual(admin.main(), 10)
        mutate.assert_not_called()

    def test_bot_submission_rejected_in_mode1(self):
        submit = load_module('test_submit_mode', BR / 'tools/submit_recommendation.py')
        self.mode('internal_only')
        path = self.root / 'proposal.json'
        support.atomic_json(path, self.valid_rec())
        with patch.object(submit, 'write_recommendation') as write:
            self.assertEqual(submit.submit(str(path)), 2)
        write.assert_not_called()

    def valid_rec(self):
        return {'schema': 'hermes-trading-recommendation-v1', 'auto_apply': True,
                'changes': [{'action': 'set_weights', 'strategy_weights': {'trend': 1.0}}]}

    def test_bot_submission_mode2_metadata(self):
        submit = load_module('test_submit_valid', BR / 'tools/submit_recommendation.py')
        path = self.root / 'proposal.json'
        support.atomic_json(path, self.valid_rec())
        rec = submit.validated_record(str(path))
        self.assertTrue(rec['uses_llm'])
        self.assertEqual(rec['mode_epoch'], 'test-epoch')

    def test_non_object_and_stale_proposal_rejected(self):
        submit = load_module('test_submit_invalid', BR / 'tools/submit_recommendation.py')
        path = self.root / 'proposal.json'
        for rec in ([], {**self.valid_rec(), 'mode_epoch': 'stale'},
                    {**self.valid_rec(), 'uses_llm': False}):
            with self.subTest(rec=rec):
                support.atomic_json(path, rec)
                self.assertFalse(submit.check(str(path))[0])

    def test_mailbox_same_second_archives_never_collide(self):
        path = self.root / 'research/recommendations/latest_recommendation.json'
        with patch.object(support.time, 'strftime', return_value='fixed-time'):
            for i in range(5):
                support.write_recommendation(path, {'i': i})
        files = list((path.parent / 'superseded').glob('*.json'))
        self.assertEqual(len(files), 4)
        self.assertEqual({json.loads(f.read_text(encoding='utf-8'))['i'] for f in files}, set(range(4)))

    def test_archive_failure_preserves_original(self):
        path = self.root / 'research/recommendations/latest_recommendation.json'
        support.atomic_json(path, {'original': True})
        with patch.object(support, 'atomic_json', side_effect=OSError('disk full')), self.assertRaises(OSError):
            support.write_recommendation(path, {'replacement': True})
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), {'original': True})

    def test_internal_writer_defers_until_ai_proposal_processed(self):
        path = self.root / 'research/recommendations/latest_recommendation.json'
        bot = {'uses_llm': True, 'mode': 'internal_llm_join', 'mode_epoch': 'test-epoch'}
        internal = {**bot, 'uses_llm': False}
        support.atomic_json(path, bot)
        self.assertIsNone(support.write_recommendation(path, internal, defer_if_pending_llm=True))
        self.assertEqual(json.loads(path.read_text(encoding='utf-8')), bot)
        support.atomic_json(path.parent / 'last_applied.json', {'rec_hash': support.digest(bot)})
        self.assertIsNotNone(support.write_recommendation(path, internal, defer_if_pending_llm=True))

    def test_parser_uses_python_job_in_both_modes_and_submits_internal_rec(self):
        scripts = Path(os.environ.get('TRADING_RESEARCH_SCRIPTS', BR.parents[1] / 'research_scripts'))
        if not (scripts / 'llm_signal_parser.py').exists():
            self.skipTest('Optional external research scripts are not installed in this test workspace')
        with patch.object(sys, 'path', [str(scripts)] + sys.path):
            parser = load_module('test_internal_parser', scripts / 'llm_signal_parser.py')
        hermes = self.root / 'scheduler-fixture'
        support.atomic_json(hermes / 'cron/jobs.json', {'jobs': [
            {'id': 'python-test', 'name': 'trading-analytics'},
            {'id': 'ai-test', 'name': modes.RESEARCH_JOB}]})
        output = hermes / 'cron/output/python-test/result.md'
        output.parent.mkdir(parents=True)
        output.write_text('[INTERNAL-SIGNAL]\nDIRECTION=BUY\nWEIGHT=90\n[/INTERNAL-SIGNAL]\n'
                          '[TRADE-SIGNAL]\nDIRECTION=SELL\nWEIGHT=99\n[/TRADE-SIGNAL]', encoding='utf-8')
        with patch.object(parser, 'hermes_home', return_value=str(hermes)):
            for name in ('internal_only', 'internal_llm_join'):
                self.mode(name)
                self.assertEqual(Path(parser.newest_output()), output)
            parser.main()
        rec = json.loads((self.root / 'research/recommendations/latest_recommendation.json').read_text(encoding='utf-8'))
        self.assertIs(rec['uses_llm'], False)
        self.assertGreater(rec['changes'][0]['directional_weights']['trend_buy'], 1)

    def research_scripts(self):
        scripts = Path(os.environ.get('TRADING_RESEARCH_SCRIPTS', BR.parents[1] / 'research_scripts'))
        if not (scripts / 'research_support.py').exists():
            self.skipTest('External research scripts not installed')
        return scripts

    def test_scheduler_gate_blocks_mode1_and_stop_but_runs_mode2(self):
        scripts = self.research_scripts()
        with patch.object(sys, 'path', [str(scripts)] + sys.path):
            gate = load_module('test_bot_gate', scripts / 'research_bot_gate.py')
        for mode, stopped, code in [('internal_only', False, 3), ('internal_llm_join', True, 3),
                                    ('internal_llm_join', False, 0)]:
            with self.subTest(mode=mode, stopped=stopped), contextlib.redirect_stdout(io.StringIO()):
                self.mode(mode)
                stop = self.root / 'work/AUTO_TRADER_STOP'
                if stopped:
                    stop.touch()
                elif stop.exists():
                    stop.unlink()
                self.assertEqual(gate.main(), code)

    def test_migrated_root_resolvers_use_selected_project(self):
        scripts = self.research_scripts()
        checked = 0
        for file in scripts.glob('*.py'):
            functions = [n for n in ast.parse(file.read_text(encoding='utf-8-sig')).body
                if isinstance(n, ast.FunctionDef) and n.name == 'find_project_dir']
            if not functions:
                continue
            # Execute ONLY the resolver function, never research script top-level code.
            namespace = {'project_root': lambda: self.root}
            code = compile(ast.Module(body=functions, type_ignores=[]), str(file), 'exec')
            with patch.object(sys, 'path', [str(scripts)] + sys.path):
                exec(code, namespace)
                self.assertEqual(Path(namespace['find_project_dir']()).resolve(), self.root.resolve())
            checked += 1
        self.assertGreaterEqual(checked, 24)

    def test_market_reopens_at_whole_hour(self):
        for value in ('2026-09-21T21:37:00+00:00', '2026-11-02T22:37:00+00:00'):
            with self.subTest(date=value):
                self.assertEqual(market_clock.next_open_delta(dt.datetime.fromisoformat(value)), 23 * 60)

    def test_weekend_reopens_at_exact_sunday_boundary(self):
        now = dt.datetime.fromisoformat('2026-09-18T21:37:12+00:00')
        target = dt.datetime.fromisoformat('2026-09-20T22:00:00+00:00')
        self.assertEqual(market_clock.next_open_delta(now), (target-now).total_seconds())


if __name__ == '__main__':
    unittest.main(verbosity=2)
