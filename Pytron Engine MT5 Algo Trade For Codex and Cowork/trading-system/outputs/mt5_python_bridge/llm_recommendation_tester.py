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
"""Bound recommendation evaluation. No history-winrate shortcut, no order operations."""
import argparse, json, math, os
from pathlib import Path
from runtime_support import atomic_json, digest
from llm_recommendation_consumer import validate, apply_recommendation

def compare_results(base, proposed):
    a, b = base.get('all'), proposed.get('all')
    if not isinstance(a, dict) or not isinstance(b, dict):
        return {'status':'failed', 'reason':'backtest metrics schema mismatch'}
    required = ('trades', 'total_r', 'max_drawdown_r')
    if any(type(m.get(k)) not in (int,float) or not math.isfinite(m[k]) for m in (a,b) for k in required):
        return {'status':'failed', 'reason':'missing/non-finite metrics'}
    if a['trades'] <= 0 or b['trades'] <= 0:
        return {'status':'skipped', 'reason':'insufficient simulated trades in one comparison arm'}
    good = b['total_r'] >= a['total_r'] and b['max_drawdown_r'] <= a['max_drawdown_r']
    ap, bp = a.get('profit_factor'), b.get('profit_factor')
    if ap is not None:
        if bp is None:
            good = good and b.get('losses') == 0 and b.get('wins',0) > 0
        else:
            good = good and math.isfinite(bp) and bp >= ap
    return {'status':'passed' if good else 'failed', 'reason':'same-snapshot bar simulation comparison',
            'base':a,'proposed':b, 'improved':good and b['total_r'] > a['total_r'],
            'limitations':'Approximate M5 simulation; not a full M1/position lifecycle replay or a guarantee of future profit'}

def evaluate(rec, cfg):
    ok, reason = validate(rec)
    if not ok: return {'status':'failed','stage':'schema','reason':reason}
    candidate = apply_recommendation(rec, cfg)
    from auto_trader import load_config
    load_config(candidate)
    import strategy_backtest as sb
    from unittest.mock import patch
    terminal = os.environ.get('MT5_TERMINAL_PATH', sb.TERMINAL)
    if not sb.mt5.initialize(path=terminal):
        return {'status':'skipped','stage':'data','reason':'MT5 historical connection unavailable'}
    try:
        account = sb.mt5.account_info()
        symbol = sb.mt5.symbol_info(cfg['symbol'])
        if account is None or symbol is None:
            return {'status':'skipped','stage':'data','reason':'Account/symbol data unavailable'}
        bars = min(12000, max(800, int(rec.get('test_bars',800))))
        loader = sb.load_closed_rates
        cache = {}
        def frozen(symbol_name, timeframe, count):
            key = (symbol_name,timeframe,count)
            if key not in cache: cache[key] = loader(*key).copy()
            return cache[key].copy()
        with patch.object(sb, 'load_closed_rates', frozen), patch.object(sb.mt5, 'account_info', return_value=account), patch.object(sb.mt5, 'symbol_info', return_value=symbol):
            args = dict(bars=bars, spread=float(cfg['max_spread']), max_hold_bars=24)
            base = sb.run_backtest(cfg, **args)
            proposed = sb.run_backtest(candidate, **args)
        verdict = compare_results(base, proposed)
        verdict['stage'] = 'performance'
        return verdict
    finally: sb.mt5.shutdown()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rec', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--verdict', required=True)
    a = p.parse_args()
    rec = json.loads(Path(a.rec).read_text(encoding='utf-8'))
    cfg = json.loads(Path(a.config).read_text(encoding='utf-8'))
    try: verdict = evaluate(rec,cfg)
    except Exception as exc: verdict = {'status':'failed','stage':'evaluation','reason':str(exc)}
    verdict.update(rec_hash=digest(rec), config_hash=digest(cfg))
    atomic_json(a.verdict, verdict)
    print('Testing Gate: ' + verdict['status'] + ' — ' + verdict.get('reason',''))
    return 0
if __name__ == '__main__': raise SystemExit(main())
