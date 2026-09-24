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
"""User-selected signal mode; internal research remains active in both modes."""
import argparse, os, shutil, subprocess, uuid
from pathlib import Path
from runtime_support import (atomic_json, current_mode, file_lock, project_root,
                             update_json, DEFAULT_MODE, MODE_TITLES)
MODES = {'1': 'internal_only', '2': 'internal_llm_join'}
TITLES = MODE_TITLES
PYTHON_JOBS = (
    'trading-analytics',
    'llm-recommendation-consumer',
    'trading-daily-research-log',
)
RESEARCH_JOB = 'trading-research-bot (10 นาที · บอทดูแล LLM)'
ADMIN_JOB = 'trading-admin-bot (30 นาที)'
BRAIN_CONSULT_JOB = 'brain-consult'
AI_JOBS = (RESEARCH_JOB, ADMIN_JOB, BRAIN_CONSULT_JOB)
JOBS = PYTHON_JOBS + AI_JOBS

def hermes_executable():
    home = Path(os.environ.get('HERMES_HOME', Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'hermes'))
    exe = os.environ.get('HERMES_EXE') or shutil.which('hermes') or str(home / 'hermes-agent/venv/Scripts/hermes.exe')
    if not Path(exe).is_file(): raise RuntimeError('Configure HERMES_EXE first')
    return exe

def cron(action, name):
    r = subprocess.run([hermes_executable(), 'cron', action, name], capture_output=True, text=True, timeout=45)
    if r.returncode: raise RuntimeError(f'Cron {action} {name} failed (exit {r.returncode})')

def pause_all():
    errors = []
    for name in JOBS:
        try: cron('pause', name)
        except Exception as exc: errors.append(str(exc))
    if errors: raise RuntimeError('; '.join(errors))

def resume_selected(mode):
    if mode not in TITLES:
        raise ValueError('Unknown trading mode; no jobs changed')
    try:
        # Both modes retain all Python-only work. Every registered AI job follows
        # the selected mode; adding an AI cron requires adding it to AI_JOBS here.
        for name in AI_JOBS:
            cron('pause', name)
        for name in PYTHON_JOBS:
            cron('resume', name)
        if mode == DEFAULT_MODE:
            for name in AI_JOBS:
                cron('resume', name)
    except Exception as exc:
        try:
            pause_all()
        except Exception as cleanup:
            raise RuntimeError(f'Mode activation failed: {exc}; pause failed: {cleanup}') from exc
        raise

def select_mode(mode, root=None):
    if mode not in TITLES:
        raise ValueError('Unknown trading mode; no state changed')
    root = Path(root or project_root())
    with file_lock(root / 'work/research-cycle.lock'):
        try: previous = current_mode(root)
        except (ValueError, OSError): previous = {}
        pause_all()
        if previous.get('mode') != mode:
            # A merged historical multiplier cannot be decomposed. Reset ONLY these
            # multipliers; internal strategy weights, bands and TP/SL are preserved.
            def reset_signal(cfg):
                cfg['strategy_router']['directional_weights'] = {
                    f'{s}_{d}': 1.0 for s in ('trend', 'range', 'mean_reversion',
                    'counter_trend', 'breakout', 'breakout_reversal') for d in ('buy', 'sell')}
                return cfg
            update_json(root / 'outputs/mt5_python_bridge/auto_config.json', reset_signal)
        data = {'mode': mode, 'epoch': uuid.uuid4().hex, 'title': TITLES[mode]}
        atomic_json(root / 'work/trading_mode.json', data)
        # Old proposals kept for audit; consumer rejects their old mode epoch.
        if not (root / 'work/AUTO_TRADER_STOP').exists(): resume_selected(mode)
    return data

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--set', choices=list(MODES) + list(TITLES))
    p.add_argument('--print-mode', action='store_true')
    p.add_argument('--status', action='store_true')
    p.add_argument('--pause-all', action='store_true')
    p.add_argument('--resume', action='store_true')
    a = p.parse_args()
    if a.pause_all:
        pause_all()
        return 0
    if a.print_mode or a.status or a.resume:
        data = current_mode()
        if a.resume:
            if (project_root() / 'work/AUTO_TRADER_STOP').exists(): raise RuntimeError('Kill switch present')
            resume_selected(data['mode'])
        print(data['mode'] if a.print_mode else TITLES[data['mode']])
        return 0
    value = a.set
    if not value:
        print('1. เทรดด้วยสัญญาณภายใน (ระบบเทรดและวิจัยภายใน Python; ไม่ใช้ AI)\n'
              '2. เทรดร่วมสัญญาณ AI (Python + AI ทุกส่วนที่เชื่อมกับระบบ; ค่าเริ่มต้น)\n'
              '0. ยกเลิก')
        try: value = input('เลือก 1 หรือ 2 [Enter = 2]: ').strip() or DEFAULT_MODE
        except EOFError: return 2
        if value == '0': return 2
    mode = MODES.get(value, value)
    if mode not in TITLES: raise ValueError('Select 1 or 2 explicitly')
    select_mode(mode)
    print(TITLES[mode] + ' — Python research remains enabled; AI integrations follow the selected mode')
    return 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except Exception as exc:
        print(f'Mode operation failed: {exc}')
        raise SystemExit(1)
