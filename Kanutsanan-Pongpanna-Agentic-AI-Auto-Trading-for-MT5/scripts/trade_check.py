#!/usr/bin/env python3
"""
=============================================================================
Kanutsanan Pongpanna AI Auto Trading v5.1 - Trade Check (Manual)
=============================================================================
Model: deepseek/deepseek-v3.2-exp (10x cheaper than Gemini, same quality)
Network: wget-based (fixes SSL timeout on Cloud Computer)

คำสั่ง:
  python3 trade_check.py              - เช็คเทรด
  python3 trade_check.py approve      - อนุมัติเทรด
  python3 trade_check.py status       - ดูสถานะระบบ

Trade Comment: "Kanutsanan Pongpanna AI Auto Trading"
=============================================================================
"""
import os
import sys
import json
import re
import subprocess
import threading
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# =============================================================================
# CONFIGURATION
# =============================================================================
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "eaf88ee0-bc4f-4f70-86e6-e6333d6c4e4f")
API_KEY = os.environ.get("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJkMWExYjVjYzZjZDNmOGIzY2ViOTNjMTQxNGMwM2FmZCIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiZDFhMWI1Y2M2Y2QzZjhiM2NlYjkzYzE0MTRjMDNhZmQiLCJpYXQiOjE3NzgyMzU0ODF9.b_WWWKQoH2lUWMwpnFdlcU-qePQgcPfpR1t0F4w2drUe8h80n2awJGHR6sQglNU4IJoVz7Ec2RqKHuYLDIUyDwdLwNV_zwanlUYsmo2x_OLmLNBSw1Xzkdd7T9V-DHKE8bU6ams1VkTWhse_q_LlUSdqMG8RJYJpxaHmNynOvA1PCLTwsrVi4_JFnTPf3MKMLmO95bE9MkOyuAZ1d2282fdls9CsBcRhEUwddoANxCpHg0AcXcCotUrpyQgQfmaOkzpAFgjounx5ZzvoKGVjCmzD3gxnecaG4azZbNIJwlfbofcA7fqvL_1GU06fPxvWM5c7CrLnvIvdoNbTCrAP-9Fy3LNHiK1AtnmddMh3t0lzdyPpulyZL_DSAfk7ymTAdLqJf68knJIN7p33WImjJgcs9e8rPdZLOHmXwP-PYaPy7Qv4lG5iF7P73LwtQhQ_QCCGJIrClW6A04oCtM9v7iIHcnm8YZtNKNlBQTvJuC0TgwoKuu5rzy7Y5IoZLu0tiz_NF6AHcVCWcONfeLUg6voFPW-cQuxtf1jvD9jBEPnd3fAZyY1dWwArM5syT8zNu73_3mfoC249Q_45QEG45zmUVCaOJQ9h19Ax8nu8QOsERu5uLzvMrrHJwKGjOC6zpNMhnNxcyPH1inbqjCUw1loqWKzZEPLoQnF1I9oc9XQ")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "deepseek/deepseek-v3.2-exp")
AI_MODEL_FALLBACK = "qwen/qwen3-next-80b-a3b-instruct"

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
MARKET_DATA_URL = f"https://mt-market-data-client-api-v1.{REGION}.agiliumtrade.ai"
TRADINGVIEW_SCANNER_URL = "https://scanner.tradingview.com/cfd/scan"
TRADE_COMMENT = "Kanutsanan Pongpanna AI Auto Trading"

MAX_POSITIONS = 10
MAX_LOT = 0.1
MIN_LOT = 0.001
MAX_MARGIN_PERCENT = 50
TP_MAX = 5
LEVERAGE = 100

LOG_FILE = os.path.join(SCRIPT_DIR, "auto_trade.log")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "trade_memory.json")
last_recommendation = None

# =============================================================================
# WGET-BASED HTTP CLIENT
# =============================================================================
def wget_get(url, extra_headers=None, timeout=15):
    cmd = ['wget', f'--timeout={timeout}', '--content-on-error', '-qO-']
    if extra_headers:
        for k, v in extra_headers.items():
            cmd.append(f'--header={k}: {v}')
    cmd.append(url)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except:
        return None

def wget_post(url, data, extra_headers=None, timeout=15):
    cmd = ['wget', f'--timeout={timeout}', '--content-on-error', '-qO-',
           '--header=Content-Type: application/json',
           f'--post-data={json.dumps(data)}']
    if extra_headers:
        for k, v in extra_headers.items():
            cmd.append(f'--header={k}: {v}')
    cmd.append(url)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout+5)
        if result.stdout:
            return json.loads(result.stdout)
        return None
    except:
        return None

# =============================================================================
# HELPERS
# =============================================================================
def log(msg):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    log_msg = f"[{timestamp}] {msg}"
    print(f"  {log_msg}")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass

def check_market_open():
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    if now.weekday() == 4 and now.hour >= 22:
        return False
    return True

# =============================================================================
# SELF-EVOLUTION
# =============================================================================
def load_trade_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"version": "5.1", "total_trades": 0, "wins": 0, "losses": 0,
            "total_profit": 0.0, "win_rate": 0.0, "best_patterns": [],
            "worst_patterns": [], "recent_trades": [],
            "market_regime_stats": {"trending": {"trades": 0, "wins": 0, "profit": 0.0},
                "ranging": {"trades": 0, "wins": 0, "profit": 0.0},
                "volatile": {"trades": 0, "wins": 0, "profit": 0.0}},
            "preferred_style": "AUTO", "preferred_direction": "NEUTRAL",
            "evolution_notes": [], "last_updated": ""}

def save_trade_memory(memory):
    try:
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except:
        pass

def record_trade(signal, tp_pts, sl_pts, reason, data_source, market_regime="unknown"):
    memory = load_trade_memory()
    memory["recent_trades"].append({
        "time": datetime.now(timezone.utc).isoformat(),
        "signal": signal, "tp_pts": tp_pts, "sl_pts": sl_pts,
        "reason": reason[:100], "data_source": data_source,
        "market_regime": market_regime, "result": "pending"})
    memory["recent_trades"] = memory["recent_trades"][-100:]
    memory["total_trades"] += 1
    save_trade_memory(memory)

def get_evolution_context():
    memory = load_trade_memory()
    if memory["total_trades"] == 0:
        return "\nSELF-EVOLUTION: No history yet. Trade aggressively!\n"
    ctx = f"\nSELF-EVOLUTION ({memory['total_trades']} trades, {memory['win_rate']}% win):\n"
    ctx += f"- Style: {memory['preferred_style']} | Direction: {memory['preferred_direction']}\n"
    if memory["best_patterns"]:
        ctx += "- Winners: " + ", ".join([f"{p['signal']} TP{p['tp']}" for p in memory["best_patterns"][-3:]]) + "\n"
    if memory["worst_patterns"]:
        ctx += "- Losers (avoid): " + ", ".join([f"{p['signal']} SL{p['sl']}" for p in memory["worst_patterns"][-3:]]) + "\n"
    return ctx

# =============================================================================
# DATA SOURCES
# =============================================================================
def get_candles_from_metaapi():
    log("[MetaAPI] Fetching candles...")
    meta_headers = {"auth-token": API_KEY}
    timeframes = {"5m": {"limit": 30, "label": "M5"}, "15m": {"limit": 30, "label": "M15"}, "1h": {"limit": 24, "label": "H1"}}
    all_data = {}
    for tf, config in timeframes.items():
        url = f"{MARKET_DATA_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/{tf}/candles?limit={config['limit']}"
        data = wget_get(url, extra_headers=meta_headers, timeout=10)
        if data and isinstance(data, list) and len(data) > 3:
            all_data[config["label"]] = data
            log(f"  Got {len(data)} {config['label']} candles")
    if not all_data:
        return None
    text = "CANDLE DATA (MetaAPI REAL-TIME):\n"
    for label, candles in all_data.items():
        text += f"\n{label} (last 15):\nTime | Open | High | Low | Close | Vol\n"
        for c in candles[-15:]:
            text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
    return text

def get_tradingview_data():
    log("[TradingView] Fetching...")
    payloads = {
        "M5": {'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|5', 'RSI|5', 'MACD.macd|5', 'MACD.signal|5', 'EMA20|5', 'SMA20|5', 'EMA50|5', 'close|5', 'ATR|5', 'ADX|5', 'Stoch.K|5', 'CCI20|5', 'high|5', 'low|5']},
        "M15": {'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|15', 'RSI|15', 'MACD.macd|15', 'MACD.signal|15', 'EMA20|15', 'SMA20|15', 'EMA50|15', 'close|15', 'ATR|15', 'ADX|15', 'Stoch.K|15', 'CCI20|15', 'high|15', 'low|15']},
        "H1": {'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|60', 'RSI|60', 'MACD.macd|60', 'MACD.signal|60', 'EMA20|60', 'SMA20|60', 'EMA50|60', 'close|60', 'ATR|60', 'ADX|60', 'Stoch.K|60', 'CCI20|60', 'high|60', 'low|60']}
    }
    try:
        results = {}
        for label, payload in payloads.items():
            data = wget_post(TRADINGVIEW_SCANNER_URL, payload, timeout=10)
            if data and data.get('totalCount', 0) > 0:
                results[label] = data['data'][0]['d']
        if not results:
            return None
        text = "TradingView Scanner (REAL-TIME):\n"
        for tf, d in results.items():
            text += f"\n{tf}:\n"
            text += f"  Rec={d[0]:.3f} RSI={d[1]:.1f} MACD={d[2]:.4f}/{d[3]:.4f}\n"
            text += f"  EMA20={d[4]:.2f} SMA20={d[5]:.2f} EMA50={d[6]:.2f}\n"
            text += f"  Close={d[7]} ATR={d[8]:.3f} ADX={d[9]:.1f}\n"
            text += f"  Stoch={d[10]:.1f} CCI={d[11]:.1f} H={d[12]} L={d[13]}\n"
        return text
    except:
        return None

# =============================================================================
# AI CALL (wget-based, No max_tokens!)
# =============================================================================
def call_openrouter(prompt, agent_name, model=None):
    if not OPENROUTER_API_KEY:
        return None
    if model is None:
        model = AI_MODEL
    
    payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.1}
    ai_headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    
    try:
        data = wget_post("https://openrouter.ai/api/v1/chat/completions",
                        payload, extra_headers=ai_headers, timeout=120)
        
        if not data:
            if model != AI_MODEL_FALLBACK:
                return call_openrouter(prompt, agent_name, model=AI_MODEL_FALLBACK)
            return None
        
        if 'error' in data:
            log(f"[{agent_name}] Error: {data['error'].get('message','')[:80]}")
            if model != AI_MODEL_FALLBACK:
                return call_openrouter(prompt, agent_name, model=AI_MODEL_FALLBACK)
            return None
        
        message = data['choices'][0]['message']
        content = message.get('content') or ''
        content = content.strip()
        
        if not content and message.get('reasoning'):
            json_match = re.search(r'\{[^{}]*\}', message.get('reasoning', ''), re.DOTALL)
            if json_match:
                content = json_match.group(0)
        if not content:
            return None
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        result = json.loads(content)
        log(f"[{agent_name}] {result.get('action','?')} Str:{result.get('strength','?')}")
        return result
    except:
        return None

# =============================================================================
# AI AGENTS (Parallel)
# =============================================================================
def run_parallel_analysis(market_data, bid, ask):
    evolution_ctx = get_evolution_context()
    entry = (bid + ask) / 2
    results = {}
    
    def agent1():
        prompt = f"""You are a XAUUSD Mean-Reversion scalper. FIND a profitable trade NOW.
PRICE: Bid={bid} Ask={ask} Entry={entry:.3f}
{market_data}
{evolution_ctx}
STRATEGY: Find S/R midpoint. Price > mid = SELL, Price < mid = BUY. TP 1-5pts. SL=ATR-based.
You MUST trade. SKIP only if market is dead. Even 1pt profit is good.
Reply ONLY JSON: {{"action":"BUY"/"SELL","tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief","market_regime":"trending"/"ranging"/"volatile"}}"""
        results['a1'] = call_openrouter(prompt, "Agent1-MR")
    
    def agent2():
        prompt = f"""You are a XAUUSD Trend-Following scalper. FIND a profitable trade NOW.
PRICE: Bid={bid} Ask={ask} Entry={entry:.3f}
{market_data}
{evolution_ctx}
STRATEGY: Follow EMA/MACD/ADX. Uptrend=BUY, Downtrend=SELL. TP 1-5pts. SL=ATR-based.
You MUST trade. SKIP only if market is dead. Even weak trends give 1-2pts.
Reply ONLY JSON: {{"action":"BUY"/"SELL","tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief","market_regime":"trending"/"ranging"/"volatile"}}"""
        results['a2'] = call_openrouter(prompt, "Agent2-TF")
    
    t1 = threading.Thread(target=agent1)
    t2 = threading.Thread(target=agent2)
    t1.start(); t2.start()
    t1.join(timeout=130); t2.join(timeout=130)
    
    a1 = results.get('a1')
    a2 = results.get('a2')
    
    if a1 and a2:
        if a1.get('action') == a2.get('action') and a1.get('action') in ['BUY', 'SELL']:
            chosen = a1 if a1.get('strength', 0) >= a2.get('strength', 0) else a2
            chosen['chosen_set'] = 1 if a1.get('strength', 0) >= a2.get('strength', 0) else 2
            return chosen
    
    if a1 or a2:
        prompt = f"""FINAL DECISION for XAUUSD. You MUST decide BUY or SELL.
Agent1(MR): {json.dumps(a1) if a1 else 'FAILED'}
Agent2(TF): {json.dumps(a2) if a2 else 'FAILED'}
{evolution_ctx}
Pick the better signal. SKIP is FORBIDDEN. Small profit > no trade.
Reply ONLY JSON: {{"action":"BUY"/"SELL","chosen_set":1/2,"tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief","market_regime":"trending"/"ranging"/"volatile"}}"""
        final = call_openrouter(prompt, "Coordinator")
        if final:
            return final
    
    if a1 and a1.get('action') in ['BUY', 'SELL']:
        a1['chosen_set'] = 1; return a1
    if a2 and a2.get('action') in ['BUY', 'SELL']:
        a2['chosen_set'] = 2; return a2
    return None

# =============================================================================
# MAIN CHECK
# =============================================================================
def check_trade():
    global last_recommendation
    meta_headers = {"auth-token": API_KEY}
    
    print("\n" + "=" * 60)
    print(f"  TRADE CHECK - AI v5.1 (DeepSeek V3.2 | 10x cheaper)")
    print("  " + datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'))
    print("=" * 60)
    
    if not check_market_open():
        print("\n  Market CLOSED\n"); return None
    if not OPENROUTER_API_KEY:
        print("\n  ERROR: Missing OPENROUTER_API_KEY\n"); return None
    
    acc = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                   extra_headers=meta_headers, timeout=10)
    if not acc:
        print("\n  ERROR: Cannot connect to MetaAPI\n"); return None
    
    balance = acc.get('balance', 0)
    equity = acc.get('equity', 0)
    free_margin = acc.get('freeMargin', 0)
    print(f"\n  Account: Balance=${balance} Equity=${equity} Free=${free_margin}")
    
    positions = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                        extra_headers=meta_headers, timeout=10)
    if positions and isinstance(positions, list):
        print(f"  Positions: {len(positions)}/{MAX_POSITIONS}")
        for p in positions:
            print(f"    {p.get('type','')} {p.get('volume',0)}lot P/L:{p.get('profit',0)}")
        if len(positions) >= MAX_POSITIONS:
            print("  Max positions!\n"); return None
    
    price = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/symbols/XAUUSD.sml/current-price",
                    extra_headers=meta_headers, timeout=10)
    if not price:
        print("\n  ERROR: Cannot get price\n"); return None
    
    bid = price.get('bid', 0)
    ask = price.get('ask', 0)
    spread = round(ask - bid, 3)
    entry = (bid + ask) / 2
    print(f"  Price: Bid={bid} Ask={ask} Spread={spread}")
    
    if spread <= 0 or bid <= 0:
        print("\n  Market closed\n"); return None
    
    print("\n  Fetching market data...")
    market_data = get_candles_from_metaapi()
    data_source = "MetaAPI"
    if not market_data:
        market_data = get_tradingview_data()
        data_source = "TradingView"
    if not market_data:
        print("  ERROR: No data\n"); return None
    
    print(f"  AI Analysis (Dual Calc + Parallel | {AI_MODEL})...")
    ai_decision = run_parallel_analysis(market_data, bid, ask)
    
    if not ai_decision:
        print("  AI: No decision\n"); return None
    
    signal = ai_decision.get('action', 'SKIP')
    if signal not in ['BUY', 'SELL']:
        print(f"  AI: {signal} - {ai_decision.get('reason','')}\n"); return None
    
    strength = ai_decision.get('strength', 5)
    tp_pts = max(1, min(TP_MAX, int(ai_decision.get('tp_points', 3))))
    sl_pts = max(2, min(15, int(ai_decision.get('sl_points', 5))))
    market_regime = ai_decision.get('market_regime', 'unknown')
    reason = ai_decision.get('reason', '')
    
    if signal == "SELL":
        sl_price = round(entry + sl_pts, 3)
        tp_price = round(entry - tp_pts, 3)
        action_type = "ORDER_TYPE_SELL"
    else:
        sl_price = round(entry - sl_pts, 3)
        tp_price = round(entry + tp_pts, 3)
        action_type = "ORDER_TYPE_BUY"
    
    max_margin_use = free_margin * (MAX_MARGIN_PERCENT / 100)
    raw_lot = max_margin_use / (entry / LEVERAGE * 1000)
    lot = max(MIN_LOT, round(int(raw_lot * 1000) * 0.001, 3))
    lot = min(lot, MAX_LOT)
    
    recommendation = {
        "signal": signal, "lot": lot, "entry": round(entry, 3),
        "sl": sl_price, "tp": tp_price, "sl_pts": sl_pts, "tp_pts": tp_pts,
        "strength": strength, "reason": reason, "data_source": data_source,
        "chosen_set": ai_decision.get('chosen_set', 0),
        "market_regime": market_regime, "action_type": action_type
    }
    last_recommendation = recommendation
    
    print(f"\n{'='*60}")
    print(f"  RECOMMENDATION: {signal} | Strength: {strength}/10")
    print(f"  Entry: {entry:.3f}")
    print(f"  TP: {tp_price} (+{tp_pts} pts)")
    print(f"  SL: {sl_price} (-{sl_pts} pts)")
    print(f"  Lot: {lot}")
    print(f"  Regime: {market_regime} | Set: {ai_decision.get('chosen_set', '?')}")
    print(f"  Reason: {reason}")
    print(f"  Source: {data_source} | Model: {AI_MODEL}")
    print(f"{'='*60}")
    print(f"\n  To execute: python3 trade_check.py approve\n")
    return recommendation

# =============================================================================
# APPROVE
# =============================================================================
def approve_trade():
    global last_recommendation
    if not last_recommendation:
        print("\n  No pending recommendation. Run 'check' first.\n"); return
    
    rec = last_recommendation
    meta_headers = {"auth-token": API_KEY}
    comment = f"{TRADE_COMMENT} Set{rec.get('chosen_set',0)} Str{rec.get('strength',0)}"
    
    print(f"\n  Executing: {rec['signal']} {rec['lot']}lot @{rec['entry']}...")
    
    result = wget_post(
        f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
        {"actionType": rec['action_type'], "symbol": "XAUUSD.sml",
         "volume": rec['lot'], "stopLoss": rec['sl'],
         "takeProfit": rec['tp'], "comment": comment},
        extra_headers=meta_headers, timeout=15
    )
    
    if result and 'error' not in result:
        print(f"\n  TRADED! Order: {result.get('orderId', 'N/A')}")
        record_trade(rec['signal'], rec['tp_pts'], rec['sl_pts'],
                    rec['reason'], rec['data_source'], rec.get('market_regime', 'unknown'))
        last_recommendation = None
    else:
        err = result.get('error', {}).get('message', 'Unknown') if result else 'No response'
        print(f"\n  FAILED: {err}")

# =============================================================================
# STATUS
# =============================================================================
def check_status():
    meta_headers = {"auth-token": API_KEY}
    ai_headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    
    print("\n" + "=" * 60)
    print(f"  SYSTEM STATUS - AI v5.1 (DeepSeek V3.2)")
    print("=" * 60)
    
    acc = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                   extra_headers=meta_headers, timeout=10)
    if acc:
        print(f"\n  MetaAPI: Connected")
        print(f"  Balance: ${acc.get('balance',0)} | Equity: ${acc.get('equity',0)}")
    else:
        print(f"\n  MetaAPI: Connection failed")
    
    key_info = wget_get("https://openrouter.ai/api/v1/auth/key", extra_headers=ai_headers, timeout=10)
    if key_info and 'data' in key_info:
        usage = key_info['data'].get('usage', 0)
        limit = key_info['data'].get('limit')
        remaining = (limit - usage) if limit else "unlimited"
        print(f"  OpenRouter: OK | Usage: ${usage:.4f} | Remaining: {remaining}")
    else:
        print(f"  OpenRouter: Connection failed")
    
    print(f"  Model: {AI_MODEL}")
    print(f"  Fallback: {AI_MODEL_FALLBACK}")
    
    memory = load_trade_memory()
    print(f"  Trades: {memory['total_trades']} | Win: {memory['win_rate']}%")
    print(f"  Style: {memory['preferred_style']} | Direction: {memory['preferred_direction']}")
    print("=" * 60 + "\n")

# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "check"
    
    if cmd in ['check', 'เช็คเทรด', 'เช็ค']:
        check_trade()
    elif cmd in ['approve', 'อนุมัติเทรด', 'อนุมัติ']:
        approve_trade()
    elif cmd in ['status', 'สถานะ']:
        check_status()
    else:
        print(f"""
  Kanutsanan Pongpanna AI Auto Trading v5.1 - Trade Check
  Model: {AI_MODEL} (10x cheaper than Gemini)
  
  Commands:
    check     เช็คเทรด (วิเคราะห์ + AI)
    approve   อนุมัติเทรด
    status    ดูสถานะระบบ
        """)
