# -*- coding: utf-8 -*-
"""ตรวจสุขภาพทั้งระบบ: โครงสร้าง + ความสะอาดของโค้ด + ความพร้อมรันจริง"""
import io, os, re, json, glob, subprocess, collections, datetime
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BR = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
PY = os.path.join(ROOT, '.venv', 'Scripts', 'python.exe')

def run(cmd, cwd=None, timeout=300):
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=timeout)
    return (r.stdout or '') + (r.stderr or '')

print('=' * 60)
print('1) COMPILE ทุกไฟล์โค้ด')
print('=' * 60)
bad = []
files = [f for f in glob.glob(os.path.join(BR, '**', '*.py'), recursive=True) if '__pycache__' not in f]
for f in files:
    try:
        compile(io.open(f, encoding='utf-8').read(), f, 'exec')
    except SyntaxError as exc:
        bad.append((f, exc))
print('ไฟล์:', len(files), '| ไม่ผ่าน:', len(bad))
for f, exc in bad:
    print('   ✗', os.path.relpath(f, ROOT), exc)

print()
print('=' * 60)
print('2) PYFLAKES (ความสะอาด)')
print('=' * 60)
out = run([PY, '-m', 'pyflakes'] + [os.path.join(BR, x) for x in os.listdir(BR) if x.endswith('.py')]
          + [os.path.join(BR, 'tools', x) for x in os.listdir(os.path.join(BR, 'tools')) if x.endswith('.py')])
lines = [l for l in out.splitlines() if l.strip()]
kinds = collections.Counter('ตัวแปรไม่ใช้' if 'never used' in l else
                            ('import ไม่ใช้' if 'imported but unused' in l else 'อื่น ๆ') for l in lines)
print('จุดที่พบ:', len(lines), dict(kinds))
for l in lines:
    if 'ตัวแปรไม่ใช้' not in l:
        print('   ⚠', l)

print()
print('=' * 60)
print('3) โครงสร้างโมดูล + การพึ่งพา')
print('=' * 60)
mods = {os.path.basename(f)[:-3] for f in files if os.path.dirname(f) == BR}
used = collections.Counter()
for f in files:
    if os.path.dirname(f) != BR:
        continue
    s = io.open(f, encoding='utf-8', errors='ignore').read()
    for m in mods:
        if m == os.path.basename(f)[:-3]:
            continue
        if re.search(r'(^|\n)\s*(from\s+%s\s+import|import\s+%s\b)' % (re.escape(m), re.escape(m)), s):
            used[m] += 1
orphan = sorted(m for m in mods if used[m] == 0)
print('โมดูล:', len(mods), '| ถูกอ้างถึง:', len([m for m in mods if used[m] > 0]))
print('ไม่ถูกอ้างถึง:', ', '.join(orphan) if orphan else 'ไม่มี ✓')
core = io.open(os.path.join(BR, 'auto_trader.py'), encoding='utf-8').read()
print('เทรดคอร์อ้าง LLM แบบมี fallback:', 'try:' in core and 'from openrouter_agents' in core)

print()
print('=' * 60)
print('4) ค่าตั้งสำคัญ (ต้องอยู่ครบหลังรีสตาร์ท)')
print('=' * 60)
cfg = json.load(io.open(os.path.join(BR, 'auto_config.json'), encoding='utf-8'))
checks = {
    'profit_exit.no_signal_tp_fraction': ('profit_exit', 'no_signal_tp_fraction'),
    'side_net_gate.max_age_hours': ('side_net_gate', 'max_age_hours'),
    'revenge_guard.cooldown_minutes': ('revenge_guard', 'cooldown_minutes'),
    'early_cut.enabled': ('early_cut', 'enabled'),
    'stage3.allow_net_deferred': ('strategy_router', 'bounded_live', 'stage3', 'allow_net_deferred'),
    'admin_bot.interval_minutes': ('admin_bot', 'interval_minutes'),
    'band_min_widths.raw': ('strategy_router', 'auto_threshold', 'band_min_widths', 'raw'),
    'window_records': ('strategy_router', 'auto_threshold', 'window_records'),
}
for label, path in checks.items():
    cur = cfg
    for p in path:
        cur = cur.get(p) if isinstance(cur, dict) else None
    print('   %-34s = %s' % (label, cur))

print()
print('=' * 60)
print('5) ไฟล์โรงงาน + ความสะอาดโฟลเดอร์')
print('=' * 60)
fac = os.path.join(ROOT, 'work', 'factory')
print('โรงงาน: config', os.path.exists(os.path.join(fac, 'config', 'auto_config.factory.json')),
      '| code', len(glob.glob(os.path.join(fac, 'code', '*.py'))), 'ไฟล์',
      '| cron', os.path.exists(os.path.join(fac, 'cron', 'jobs.snapshot.json')))
print('ไฟล์ .bak ค้างใน bridge:', len(glob.glob(os.path.join(BR, '*.bak*'))))
print('__pycache__ ในโปรเจกต์:', len([d for d in glob.glob(os.path.join(ROOT, '**', '__pycache__'), recursive=True)
                                      if '.venv' not in d]))
print('ปุ่มใช้งาน:', len(glob.glob(os.path.join(BR, '*.cmd'))), 'ปุ่ม')
print('สคริปต์ใน tools:', len(glob.glob(os.path.join(BR, 'tools', '*.py'))), 'ไฟล์')

print()
print('=' * 60)
print('6) งาน cron + ประตูโหมด (บทบาท 2 โหมด)')
print('=' * 60)
try:
    jp = os.path.expandvars(r'%LOCALAPPDATA%\hermes\cron\jobs.json')
    jobs = json.load(io.open(jp, encoding='utf-8')).get('jobs', [])
    for j in jobs:
        print('   %-42s %-14s enabled=%-5s script=%s%s' % (
            j.get('name'), (j.get('schedule') or {}).get('display'), j.get('enabled'),
            j.get('script') or '-', (' | monitor=' + j['monitor_script']) if j.get('monitor_script') else ''))
except Exception as exc:
    print('   อ่าน cron ไม่ได้:', exc)
try:
    m = json.load(io.open(os.path.join(ROOT, 'work', 'trading_mode.json'), encoding='utf-8'))
    print('   โหมดปัจจุบัน:', m.get('mode'), '| epoch:', str(m.get('epoch'))[:8])
except Exception:
    print('   อ่านโหมดไม่ได้')
gate = os.path.join(os.path.expandvars(r'%LOCALAPPDATA%'), 'hermes', 'scripts', 'research_bot_gate.py')
print('   ประตูโหมด:', 'มี ✓' if os.path.exists(gate) else 'ไม่มี ✗')

print()
print('=' * 60)
print('7) สายงานวิจัย 10 นาที (ทำงานร่วมกัน 2 แหล่ง)')
print('=' * 60)
pk = sorted(glob.glob(os.path.join(ROOT, 'work', 'llm_research', 'inbox', 'packet_*.json')))
if pk:
    d = json.load(io.open(pk[-1], encoding='utf-8'))
    ir = d.get('internal_research') or {}
    print('   ชุดข้อมูลล่าสุด:', os.path.basename(pk[-1]))
    print('   มีข้อมูลภายใน:', 'auto_threshold_stats' in ir and bool(ir.get('auto_threshold_stats')),
          '| รายงานภายใน:', len(ir.get('internal_report_tail') or ''), 'ตัวอักษร')
    print('   มี bot_loop:', bool(d.get('bot_loop')), '| จำนวนคำถาม:', len(d.get('asks') or []))
for f in ('work/plan_band.json', 'work/plan_tpsl.json', 'work/tpsl_tuning_state.json'):
    p = os.path.join(ROOT, f)
    if os.path.exists(p):
        age = (datetime.datetime.now().timestamp() - os.path.getmtime(p)) / 60
        print('   %-30s อัปเดต %.0f นาทีที่แล้ว' % (os.path.basename(f), age))

print()
print('=' * 60)
print('8) การรันจริง (ตัวเทรด + error)')
print('=' * 60)
try:
    out = run(['powershell', '-NoProfile', '-Command',
               "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
               "Where-Object { $_.CommandLine -like '*auto_trader.py*' } | "
               "ForEach-Object { $_.ProcessId }"])
    pids = [x.strip() for x in out.split() if x.strip().isdigit()]
    print('   ตัวเทรดรันอยู่:', ('PID ' + ', '.join(pids)) if pids else 'ไม่พบ ✗')
except Exception as exc:
    print('   ตรวจโปรเซสไม่ได้:', exc)
try:
    rows = []
    with io.open(os.path.join(ROOT, 'work', 'auto_trader_audit.jsonl'), encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if '"event"' in line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    now = datetime.datetime.now(datetime.timezone.utc)
    err = 0
    for e in rows[-800:]:
        if e.get('event') == 'recoverable_error':
            try:
                age = (now - datetime.datetime.fromisoformat(str(e.get('time')).replace('Z', '+00:00'))).total_seconds() / 60
                if age <= 120:
                    err += 1
            except Exception:
                pass
    print('   error 2 ชม.ล่าสุด:', err)
    if rows:
        print('   event ล่าสุด:', rows[-1].get('event'), str(rows[-1].get('time'))[11:19])
except Exception as exc:
    print('   อ่าน audit ไม่ได้:', exc)
