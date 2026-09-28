# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""สถานะระบบเทรดทองคำ — อ่านปั๊บเข้าใจปั๊บ (สำหรับผู้ดูแลระบบ)
ผู้สร้างระบบ: Kanutsanan Pongpanna — https://www.facebook.com/LoveMoneyTH
"""
import json, os, subprocess, datetime, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # ...\เทรดทองคำ
BR = ROOT / 'outputs' / 'mt5_python_bridge'
WORK = ROOT / 'work'
sys.path.insert(0, str(BR))
from runtime_support import MODE_TITLES
from choose_mode import JOBS, RESEARCH_JOB, ADMIN_JOB, BRAIN_CONSULT_JOB

def th(x): return x

def mode_info():
    try:
        d = json.loads((WORK / 'trading_mode.json').read_text(encoding='utf-8'))
        m = d.get('mode')
        if m not in MODE_TITLES:
            return 'โหมด: ไม่ถูกต้อง ต้องเลือกใหม่ (ไม่ถือเป็นโหมด 2 อัตโนมัติ)'
        n = '1' if m == 'internal_only' else '2'
        t = MODE_TITLES[m]
        return f"โหมด {n}: {t}"
    except Exception as exc:
        return f"โหมด: อ่านไม่ได้ ({exc})"

def trader_state():
    if (WORK / 'AUTO_TRADER_STOP').exists():
        return "⛔ หยุด (kill switch)", None
    try:
        rows = [l for l in (WORK / 'auto_trader_audit.jsonl').read_text(encoding='utf-8', errors='replace').splitlines() if l.strip()]
        last = json.loads(rows[-1])
        t = datetime.datetime.fromisoformat(str(last['time']).replace('Z', '+00:00'))
        age = (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 60
        return ("🟢 ทำงาน" if age < 3 else "🟡 ไม่มีการอัปเดต %.0f นาที" % age), age
    except Exception as exc:
        return f"❓ ตรวจไม่ได้ ({exc})", None

def jobs():
    exe = os.environ.get('HERMES_EXE') or str(Path(os.environ.get('LOCALAPPDATA', '')) / 'hermes' / 'hermes-agent' / 'venv' / 'Scripts' / 'hermes.exe')
    try:
        out = subprocess.run([exe, 'cron', 'list', '--all'], capture_output=True, text=True, timeout=60).stdout
    except Exception as exc:
        return f"อ่านตารางงานไม่ได้ ({exc})"
    lines = []
    cur = None; state = None
    for ln in out.splitlines():
        s = ln.strip()
        if '[' in s and ']' in s:
            state = s[s.index('[') + 1:s.index(']')]
        elif s.startswith('Name:'):
            cur = s.split(':', 1)[1].strip()
            if cur in JOBS:
                label = {RESEARCH_JOB: 'AI Signal Bot (10 นาที)',
                         ADMIN_JOB: 'AI Admin Bot (30 นาที)',
                         BRAIN_CONSULT_JOB: 'AI Brain Consult (30 นาที)',
                         'llm-recommendation-consumer': 'ตัวรับคำแนะนำ Python/AI (5 นาที)',
                         'trading-daily-research-log': 'Python บันทึกงานวิจัยรายวัน',
                         'trading-analytics': 'Python วิเคราะห์/วิจัยภายใน (10 นาที)'}[cur]
                mark = '🟢 ทำงาน' if state == 'active' else '⏸️ หยุด'
                lines.append(f"    {label:<32} {mark}")
            cur = None; state = None
    return "\n".join(lines) if lines else "    (ไม่พบงาน)"

def mt5_info():
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return "MT5: เชื่อมต่อไม่ได้"
        a = mt5.account_info(); pos = mt5.positions_get() or []
        s = f"MT5: เชื่อมต่อ ✓ | equity ${a.equity:.2f} | ไม้เปิด {len(pos)}"
        for p in pos:
            s += f"\n    #{p.ticket} {'BUY' if p.type == 0 else 'SELL'} {p.volume} @{p.price_open:.2f} กำไร ${p.profit:.2f}"
        mt5.shutdown()
        return s
    except Exception as exc:
        return f"MT5: ตรวจไม่ได้ ({exc})"

def last_events(n=3):
    out = []
    try:
        rows = [l for l in (WORK / 'auto_trader_audit.jsonl').read_text(encoding='utf-8', errors='replace').splitlines() if l.strip()]
        for l in rows[-400:][::-1]:
            e = json.loads(l)
            if e.get('event') in ('order_result', 'position_closed', 'no_trade'):
                tag = {'order_result': 'เข้าไม้', 'position_closed': 'ปิดไม้', 'no_trade': 'ไม่เทรด'}[e['event']]
                extra = ''
                if e['event'] == 'position_closed':
                    extra = f" net ${float(e.get('net') or 0):+.2f}"
                elif e['event'] == 'no_trade':
                    extra = ' — ' + str(e.get('reason') or '')[:70]
                out.append(f"    {str(e['time'])[11:19]} UTC  {tag}{extra}")
                if len(out) >= n:
                    break
    except Exception as exc:
        out.append(f"    อ่านไม่ได้ ({exc})")
    return "\n".join(out)

if __name__ == '__main__':
    st, _ = trader_state()
    print("=" * 58)
    print("  สถานะระบบเทรดทองคำ  |  " + datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))
    print("=" * 58)
    print(f"  {mode_info()}")
    print(f"  ตัวเทรด + audit: {st}")
    print(f"  {mt5_info()}")
    print("\n  งานอัตโนมัติ:")
    print(jobs())
    print("\n  เหตุการณ์ล่าสุด:")
    print(last_events())
    print("=" * 58)
