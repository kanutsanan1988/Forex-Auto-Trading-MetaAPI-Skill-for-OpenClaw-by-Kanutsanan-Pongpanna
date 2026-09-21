# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Read-only research collection. Never imports the trader or sends orders."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import time
import numpy as np
import MetaTrader5 as mt5

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INPUT = HERE / 'inputs'
INPUT.mkdir(exist_ok=True)
CODE = INPUT / 'code'
CODE.mkdir(exist_ok=True)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(name, value):
    (INPUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding='utf-8')

manifest = {'collected_at_utc': datetime.now(timezone.utc).isoformat(), 'files': [], 'order_sent': False}
for source in sorted(ROOT.rglob('*')):
    rel = source.relative_to(ROOT)
    if any(part in {'.venv', '.validation_deps', '__pycache__', 'research', '.git'} for part in rel.parts):
        continue
    if not source.is_file() or source.name == '.env' or source.suffix in {'.dpapi', '.lock', '.pid'}:
        continue
    data = source.read_bytes()
    manifest['files'].append({'path': str(rel), 'size': len(data), 'sha256': digest(data)})

for name in ('auto_trader_audit.jsonl', 'auto_trader_state.json', 'backtest_trade_frequency_latest.json'):
    source = ROOT / 'work' / name
    if not source.exists():
        continue
    for attempt in range(3):
        data = source.read_bytes()
        if name.endswith('.jsonl'):
            data = data[:data.rfind(b'\n') + 1]
            break
        try:
            json.loads(data)
            break
        except json.JSONDecodeError:
            if attempt == 2:
                raise
            time.sleep(.1)
    (INPUT / name).write_bytes(data)
    manifest.setdefault('snapshots', {})[name] = {'size': len(data), 'sha256': digest(data)}

source_code = ROOT / 'outputs' / 'mt5_python_bridge'
for source in source_code.glob('*.py'):
    data = source.read_bytes()
    (CODE / source.name).write_bytes(data)
    manifest.setdefault('runtime_hashes', {})[source.name] = digest(data)
config_bytes = (source_code / 'auto_config.json').read_bytes()
manifest['config_sha256'] = digest(config_bytes)
config = json.loads(config_bytes.decode('utf-8-sig'))
def redact(obj):
    if isinstance(obj, dict):
        return {k: ('[REDACTED]' if any(s in k.lower() for s in ('password', 'api_key', 'token', 'secret', 'login')) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj
save('config_sanitized.json', redact(config))
manifest['available_libraries'] = {x: importlib.util.find_spec(x) is not None for x in ('numpy', 'scipy', 'pandas', 'sklearn', 'matplotlib')}

if not mt5.initialize(path=r'C:\Program Files\MetaTrader 5\terminal64.exe', timeout=20000):
    manifest['mt5_error'] = str(mt5.last_error())
else:
    try:
        symbol = config.get('symbol', 'XAUUSD.sml')
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        manifest['mt5'] = {'symbol': symbol, 'connected': getattr(terminal, 'connected', None), 'maxbars': getattr(terminal, 'maxbars', None),
                           'tick_server_epoch': getattr(tick, 'time', None), 'machine_utc_epoch': int(time.time()),
                           'observed_tick_minus_wall_seconds': None if tick is None else int(tick.time-time.time()),
                           'currency': getattr(account, 'currency', None), 'balance': getattr(account, 'balance', None),
                           'equity': getattr(account, 'equity', None)}
        save('symbol_spec.json', {} if info is None else {k: getattr(info,k) for k in ('name','point','digits','trade_tick_size','trade_tick_value','trade_contract_size','volume_min','volume_step','spread','trade_stops_level')})
        bars = {}
        for name, frame, requested in [('M1',mt5.TIMEFRAME_M1,100000),('M5',mt5.TIMEFRAME_M5,60000),('M15',mt5.TIMEFRAME_M15,25000),('H1',mt5.TIMEFRAME_H1,10000)]:
            data = None
            attempts = []
            for count in dict.fromkeys([requested, min(requested, 99999), min(requested,50000), min(requested,20000),10000,5000]):
                data = mt5.copy_rates_from_pos(symbol,frame,0,count)
                attempts.append({'requested':count,'returned':None if data is None else len(data),'error':str(mt5.last_error())})
                if data is not None and len(data)>300:
                    break
            if data is not None:
                # Discard newest bar, regardless of current wall-clock/server offset.
                data=data[:-1]
                np.save(INPUT/f'bars_{name}.npy',data,allow_pickle=False)
            bars[name]={'attempts':attempts,'count':0 if data is None else len(data),'first_epoch':None if data is None or not len(data) else int(data[0]['time']), 'last_epoch':None if data is None or not len(data) else int(data[-1]['time'])}
        manifest['bars']=bars
        end=datetime.now(timezone.utc)+timedelta(days=2)
        start=end-timedelta(days=367)
        deals=mt5.history_deals_get(start,end)
        orders=mt5.history_orders_get(start,end)
        save('mt5_deals.json', None if deals is None else [d._asdict() for d in deals])
        save('mt5_orders.json', None if orders is None else [o._asdict() for o in orders])
        manifest['history']={'start_utc':start.isoformat(),'end_utc':end.isoformat(),'deal_count':None if deals is None else len(deals),'order_count':None if orders is None else len(orders),'error':str(mt5.last_error())}
    finally:
        mt5.shutdown()
save('manifest.json',manifest)
print(json.dumps({k:v for k,v in manifest.items() if k not in {'files','runtime_hashes'}},ensure_ascii=False,indent=2))
