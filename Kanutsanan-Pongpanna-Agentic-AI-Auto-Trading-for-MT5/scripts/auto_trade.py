#!/usr/bin/env python3
"""
=============================================================================
Kanutsanan Pongpanna AI Auto Trading v5.0 - XAUUSD
=============================================================================
Self-Evolution + Dual Calculation + Agentic AI Parallel Processing

Features:
  - Dual Calculation: Mean-Reversion + Trend-Following
  - 3 AI Agents (parallel): Agent1(MR) + Agent2(TF) + Coordinator
  - Self-Evolution: เรียนรู้จากประวัติเทรด ปรับตัวเองอัตโนมัติ
  - Swing/Trend Auto-Switch: สลับ style ตามสภาพตลาด
  - AI-Calculated SL (ATR-based, ไม่ fix ค่าตายตัว)
  - TP max 5 pts
  - Break-Even Logic (ย้าย SL เมื่อกำไร >= 50% TP)
  - No max_tokens limit (ให้ AI ใช้เท่าที่ต้องการ)

CLI:
  python3 auto_trade.py              # Default: check + auto approve (systemd)
  python3 auto_trade.py check        # เช็คเทรด
  python3 auto_trade.py approve      # อนุมัติเทรด
  python3 auto_trade.py auto [N]     # เทรดอัตโนมัติทุก N นาที (default 5)
  python3 auto_trade.py stop         # หยุดเทรดอัตโนมัติ
  python3 auto_trade.py performance  # ดูผลงาน
  python3 auto_trade.py evolve       # รัน self-evolution analysis

Trade Comment: "Kanutsanan Pongpanna AI Auto Trading"
=============================================================================
"""
import requests
import json
import urllib3
import time
import os
import re
import sys
import threading
from datetime import datetime, timezone, timedelta

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURATION
# =============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "eaf88ee0-bc4f-4f70-86e6-e6333d6c4e4f")
API_KEY = os.environ.get("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJkMWExYjVjYzZjZDNmOGIzY2ViOTNjMTQxNGMwM2FmZCIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiZDFhMWI1Y2M2Y2QzZjhiM2NlYjkzYzE0MTRjMDNhZmQiLCJpYXQiOjE3NzgyMzU0ODF9.b_WWWKQoH2lUWMwpnFdlcU-qePQgcPfpR1t0F4w2drUe8h80n2awJGHR6sQglNU4IJoVz7Ec2RqKHuYLDIUyDwdLwNV_zwanlUYsmo2x_OLmLNBSw1Xzkdd7T9V-DHKE8bU6ams1VkTWhse_q_LlUSdqMG8RJYJpxaHmNynOvA1PCLTwsrVi4_JFnTPf3MKMLmO95bE9MkOyuAZ1d2282fdls9CsBcRhEUwddoANxCpHg0AcXcCotUrpyQgQfmaOkzpAFgjounx5ZzvoKGVjCmzD3gxnecaG4azZbNIJwlfbofcA7fqvL_1GU06fPxvWM5c7CrLnvIvdoNbTCrAP-9Fy3LNHiK1AtnmddMh3t0lzdyPpulyZL_DSAfk7ymTAdLqJf68knJIN7p33WImjJgcs9e8rPdZLOHmXwP-PYaPy7Qv4lG5iF7P73LwtQhQ_QCCGJIrClW6A04oCtM9v7iIHcnm8YZtNKNlBQTvJuC0TgwoKuu5rzy7Y5IoZLu0tiz_NF6AHcVCWcONfeLUg6voFPW-cQuxtf1jvD9jBEPnd3fAZyY1dWwArM5syT8zNu73_3mfoC249Q_45QEG45zmUVCaOJQ9h19Ax8nu8QOsERu5uLzvMrrHJwKGjOC6zpNMhnNxcyPH1inbqjCUw1loqWKzZEPLoQnF1I9oc9XQ")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "google/gemini-3.5-flash")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
MARKET_DATA_URL = f"https://mt-market-data-client-api-v1.{REGION}.agiliumtrade.ai"
headers = {"auth-token": API_KEY, "Content-Type": "application/json"}

TRADINGVIEW_SCANNER_URL = "https://scanner.tradingview.com/cfd/scan"
TRADE_COMMENT = "Kanutsanan Pongpanna AI Auto Trading"

# Trade Parameters
MAX_POSITIONS = 10
MAX_LOT = 0.1
MIN_LOT = 0.001
MAX_MARGIN_PERCENT = 50
TP_MAX = 5
LEVERAGE = 100

# Files
LOG_FILE = os.path.join(SCRIPT_DIR, "auto_trade.log")
MEMORY_FILE = os.path.join(SCRIPT_DIR, "trade_memory.json")

# Global state
auto_trade_running = False
auto_trade_thread = None
last_recommendation = None

# =============================================================================
# LOGGING
# =============================================================================
def log(msg):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass

# =============================================================================
# SELF-EVOLUTION SYSTEM (Trading Memory)
# =============================================================================
def load_trade_memory():
    """โหลด trading memory สำหรับ Self-Evolution"""
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {
        "version": "5.0",
        "total_trades": 0,
        "wins": 0,
        "losses": 0,
        "total_profit": 0.0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "best_patterns": [],
        "worst_patterns": [],
        "recent_trades": [],
        "market_regime_stats": {
            "trending": {"trades": 0, "wins": 0, "profit": 0.0},
            "ranging": {"trades": 0, "wins": 0, "profit": 0.0},
            "volatile": {"trades": 0, "wins": 0, "profit": 0.0}
        },
        "preferred_style": "AUTO",
        "preferred_direction": "NEUTRAL",
        "evolution_notes": [],
        "last_updated": ""
    }

def save_trade_memory(memory):
    """บันทึก trading memory"""
    try:
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except Exception as e:
        log(f"  [Memory] Save error: {e}")

def record_trade(signal, tp_pts, sl_pts, reason, data_source, market_regime="unknown"):
    """บันทึกเทรดที่เปิด"""
    memory = load_trade_memory()
    trade = {
        "time": datetime.now(timezone.utc).isoformat(),
        "signal": signal,
        "tp_pts": tp_pts,
        "sl_pts": sl_pts,
        "reason": reason[:100],
        "data_source": data_source,
        "market_regime": market_regime,
        "result": "pending"
    }
    memory["recent_trades"].append(trade)
    memory["recent_trades"] = memory["recent_trades"][-100:]
    memory["total_trades"] += 1
    save_trade_memory(memory)

def record_trade_result(profit):
    """บันทึกผลเทรด (เรียกจาก trade_log.py หรือ manual)"""
    memory = load_trade_memory()
    # Update last pending trade
    for t in reversed(memory["recent_trades"]):
        if t.get("result") == "pending":
            t["result"] = "win" if profit > 0 else "loss"
            t["profit"] = profit
            break
    
    memory["total_profit"] += profit
    if profit > 0:
        memory["wins"] += 1
        memory["best_patterns"].append({
            "signal": t.get("signal", "?"),
            "tp": t.get("tp_pts", 0),
            "regime": t.get("market_regime", "?"),
            "profit": profit
        })
        memory["best_patterns"] = memory["best_patterns"][-30:]
    else:
        memory["losses"] += 1
        memory["worst_patterns"].append({
            "signal": t.get("signal", "?"),
            "sl": t.get("sl_pts", 0),
            "regime": t.get("market_regime", "?"),
            "loss": profit
        })
        memory["worst_patterns"] = memory["worst_patterns"][-30:]
    
    # Update stats
    total = memory["wins"] + memory["losses"]
    memory["win_rate"] = round(memory["wins"] / total * 100, 1) if total > 0 else 0
    
    # Update regime stats
    regime = t.get("market_regime", "unknown")
    if regime in memory["market_regime_stats"]:
        memory["market_regime_stats"][regime]["trades"] += 1
        memory["market_regime_stats"][regime]["profit"] += profit
        if profit > 0:
            memory["market_regime_stats"][regime]["wins"] += 1
    
    # Auto-adjust preferred style
    regime_stats = memory["market_regime_stats"]
    best_regime = max(regime_stats.keys(), 
                      key=lambda k: regime_stats[k]["profit"] if regime_stats[k]["trades"] > 3 else -999)
    if regime_stats[best_regime]["trades"] > 3:
        if best_regime == "trending":
            memory["preferred_style"] = "TREND_FOLLOWING"
        elif best_regime == "ranging":
            memory["preferred_style"] = "MEAN_REVERSION"
        else:
            memory["preferred_style"] = "AUTO"
    
    # Preferred direction
    recent_wins = [t for t in memory["recent_trades"][-20:] if t.get("result") == "win"]
    if recent_wins:
        buy_wins = sum(1 for t in recent_wins if t["signal"] == "BUY")
        sell_wins = sum(1 for t in recent_wins if t["signal"] == "SELL")
        if buy_wins > sell_wins * 1.5:
            memory["preferred_direction"] = "BUY"
        elif sell_wins > buy_wins * 1.5:
            memory["preferred_direction"] = "SELL"
        else:
            memory["preferred_direction"] = "NEUTRAL"
    
    save_trade_memory(memory)
    log(f"  [Evolution] Recorded result: profit={profit} | Win rate: {memory['win_rate']}%")

def get_evolution_context():
    """สร้าง context จาก trading memory สำหรับส่งให้ AI"""
    memory = load_trade_memory()
    
    if memory["total_trades"] == 0:
        return "\nSELF-EVOLUTION: No trade history yet. Be aggressive - find trades!\n"
    
    ctx = f"""
SELF-EVOLUTION DATA ({memory['total_trades']} trades, {memory['win_rate']}% win rate):
- Total Profit: {memory['total_profit']:.2f} | Wins: {memory['wins']} | Losses: {memory['losses']}
- Preferred Style: {memory['preferred_style']}
- Preferred Direction: {memory['preferred_direction']}
- Market Regime Performance:
"""
    for regime, stats in memory["market_regime_stats"].items():
        if stats["trades"] > 0:
            wr = round(stats["wins"] / stats["trades"] * 100, 1)
            ctx += f"  {regime}: {stats['trades']} trades, {wr}% win, profit={stats['profit']:.2f}\n"
    
    if memory["best_patterns"]:
        ctx += "- WINNING PATTERNS (repeat these): "
        ctx += ", ".join([f"{p['signal']} TP{p['tp']} ({p['regime']})" for p in memory["best_patterns"][-5:]])
        ctx += "\n"
    
    if memory["worst_patterns"]:
        ctx += "- LOSING PATTERNS (AVOID): "
        ctx += ", ".join([f"{p['signal']} SL{p['sl']} ({p['regime']})" for p in memory["worst_patterns"][-5:]])
        ctx += "\n"
    
    recent = [t for t in memory["recent_trades"][-10:] if t.get("result") != "pending"]
    if recent:
        ctx += "- Recent results: " + ", ".join([
            f"{'W' if t['result']=='win' else 'L'} {t['signal']}" for t in recent[-5:]
        ]) + "\n"
    
    if memory.get("evolution_notes"):
        ctx += "- AI Notes: " + "; ".join(memory["evolution_notes"][-3:]) + "\n"
    
    return ctx

def run_evolution_analysis():
    """รัน Self-Evolution analysis - วิเคราะห์ประวัติและปรับกลยุทธ์"""
    memory = load_trade_memory()
    if memory["total_trades"] < 5:
        print("\n  Need at least 5 trades for evolution analysis.\n")
        return
    
    print("\n" + "=" * 50)
    print("  SELF-EVOLUTION ANALYSIS")
    print("=" * 50)
    print(f"  Total Trades: {memory['total_trades']}")
    print(f"  Win Rate: {memory['win_rate']}%")
    print(f"  Total Profit: {memory['total_profit']:.2f}")
    print(f"  Preferred Style: {memory['preferred_style']}")
    print(f"  Preferred Direction: {memory['preferred_direction']}")
    print(f"\n  Market Regime Performance:")
    for regime, stats in memory["market_regime_stats"].items():
        if stats["trades"] > 0:
            wr = round(stats["wins"] / stats["trades"] * 100, 1)
            print(f"    {regime}: {stats['trades']} trades, {wr}% win, profit={stats['profit']:.2f}")
    
    # Ask AI for evolution insights
    if OPENROUTER_API_KEY:
        prompt = f"""Analyze this trading history and give 3 specific improvement suggestions:
{json.dumps(memory['recent_trades'][-20:], indent=2)}

Win rate: {memory['win_rate']}%, Preferred style: {memory['preferred_style']}
Best patterns: {memory['best_patterns'][-5:]}
Worst patterns: {memory['worst_patterns'][-5:]}

Reply JSON: {{"insights": ["insight1", "insight2", "insight3"], "recommended_style": "TREND_FOLLOWING"/"MEAN_REVERSION"/"AUTO"}}"""
        
        result = call_openrouter(prompt, "Evolution")
        if result:
            insights = result.get("insights", [])
            if insights:
                memory["evolution_notes"] = insights[-5:]
                print(f"\n  AI Evolution Insights:")
                for i, note in enumerate(insights, 1):
                    print(f"    {i}. {note}")
            if result.get("recommended_style"):
                memory["preferred_style"] = result["recommended_style"]
                print(f"\n  Recommended Style: {result['recommended_style']}")
            save_trade_memory(memory)
    
    print("=" * 50 + "\n")

# =============================================================================
# MARKET CHECK
# =============================================================================
def check_market_open():
    """ตรวจสอบว่าตลาดเปิดหรือไม่"""
    now = datetime.now(timezone.utc)
    weekday = now.weekday()
    hour = now.hour
    
    # Saturday (5) and Sunday (6) = closed
    if weekday >= 5:
        return False
    # Friday after 22:00 UTC = closed
    if weekday == 4 and hour >= 22:
        return False
    return True

# =============================================================================
# DATA SOURCES
# =============================================================================
def get_candles_from_metaapi():
    """Source 1: MetaAPI candles (M5 + M15 + H1)"""
    log("  [MetaAPI] Fetching candles...")
    timeframes = {
        "5m": {"limit": 30, "label": "M5"},
        "15m": {"limit": 30, "label": "M15"},
        "1h": {"limit": 24, "label": "H1"}
    }
    all_data = {}
    
    for tf, config in timeframes.items():
        try:
            resp = requests.get(
                f"{MARKET_DATA_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/{tf}/candles",
                headers=headers, verify=False, timeout=10,
                params={"limit": config["limit"]}
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 3:
                    all_data[config["label"]] = data
                    log(f"    Got {len(data)} {config['label']} candles")
        except Exception as e:
            log(f"    {config['label']} error: {e}")
    
    if not all_data:
        return None
    
    text = "CANDLE DATA (MetaAPI REAL-TIME from broker):\n"
    for label, candles in all_data.items():
        text += f"\n{label} Candles (last 15):\n"
        text += "Time | Open | High | Low | Close | Volume\n"
        for c in candles[-15:]:
            text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
    
    return text

def get_tradingview_data():
    """Source 2: TradingView Scanner API"""
    log("  [TradingView] Fetching indicators...")
    payloads = {
        "M5": {
            'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|5', 'RSI|5', 'MACD.macd|5', 'MACD.signal|5',
                       'EMA20|5', 'SMA20|5', 'EMA50|5', 'close|5', 'ATR|5', 'ADX|5',
                       'Stoch.K|5', 'CCI20|5', 'high|5', 'low|5']
        },
        "M15": {
            'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|15', 'RSI|15', 'MACD.macd|15', 'MACD.signal|15',
                       'EMA20|15', 'SMA20|15', 'EMA50|15', 'close|15', 'ATR|15', 'ADX|15',
                       'Stoch.K|15', 'CCI20|15', 'high|15', 'low|15']
        },
        "H1": {
            'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': ['Recommend.All|60', 'RSI|60', 'MACD.macd|60', 'MACD.signal|60',
                       'EMA20|60', 'SMA20|60', 'EMA50|60', 'close|60', 'ATR|60', 'ADX|60',
                       'Stoch.K|60', 'CCI20|60', 'high|60', 'low|60']
        }
    }
    
    try:
        results = {}
        for label, payload in payloads.items():
            resp = requests.post(TRADINGVIEW_SCANNER_URL, json=payload, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('totalCount', 0) > 0:
                    results[label] = data['data'][0]['d']
        
        if not results:
            return None
        
        text = "TradingView Scanner Data (REAL-TIME):\n"
        for tf, d in results.items():
            text += f"\n{tf}:\n"
            text += f"  Recommend.All: {d[0]:.4f} (range -1 to +1)\n"
            text += f"  RSI(14): {d[1]:.2f}\n"
            text += f"  MACD: {d[2]:.4f} | Signal: {d[3]:.4f}\n"
            text += f"  EMA20: {d[4]:.3f} | SMA20: {d[5]:.3f} | EMA50: {d[6]:.3f}\n"
            text += f"  Close: {d[7]} | ATR: {d[8]:.4f} | ADX: {d[9]:.2f}\n"
            text += f"  Stoch.K: {d[10]:.2f} | CCI: {d[11]:.2f}\n"
            text += f"  High: {d[12]} | Low: {d[13]}\n"
        
        return text
    except Exception as e:
        log(f"  [TradingView] ERROR: {e}")
        return None

# =============================================================================
# OPENROUTER AI CALL (No max_tokens!)
# =============================================================================
def call_openrouter(prompt, agent_name):
    """Call OpenRouter API - NO max_tokens limit"""
    if not OPENROUTER_API_KEY:
        log(f"  [{agent_name}] ERROR: No API key!")
        return None
    
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1
            },
            timeout=120
        )
        
        if resp.status_code != 200:
            log(f"  [{agent_name}] ERROR: {resp.status_code} - {resp.text[:150]}")
            return None
        
        ai_response = resp.json()
        message = ai_response['choices'][0]['message']
        content = message.get('content') or ''
        content = content.strip()
        
        # Handle reasoning models (Gemini 3.5 Flash may put answer in reasoning)
        if not content and message.get('reasoning'):
            reasoning = message.get('reasoning', '')
            json_match = re.search(r'\{[^{}]*\}', reasoning, re.DOTALL)
            if json_match:
                content = json_match.group(0)
        
        if not content:
            log(f"  [{agent_name}] Empty response")
            return None
        
        # Clean markdown
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        # Extract JSON
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        result = json.loads(content)
        log(f"  [{agent_name}] {result.get('action','?')} TP:{result.get('tp_points','?')} SL:{result.get('sl_points','?')} Str:{result.get('strength','?')}")
        return result
        
    except json.JSONDecodeError:
        log(f"  [{agent_name}] JSON parse error from: {content[:100] if 'content' in dir() else 'N/A'}")
        return None
    except Exception as e:
        log(f"  [{agent_name}] ERROR: {e}")
        return None

# =============================================================================
# AI AGENTS (Dual Calculation + Parallel)
# =============================================================================
def ai_agent_mean_reversion(market_data, bid, ask, evolution_ctx):
    """Agent 1: Mean-Reversion Analysis"""
    entry = (bid + ask) / 2
    prompt = f"""You are an expert XAUUSD Mean-Reversion scalper. Your PRIMARY GOAL is to FIND a profitable trade NOW.

CURRENT PRICE: Bid={bid}, Ask={ask}, Entry={entry:.3f}

{market_data}
{evolution_ctx}

MEAN-REVERSION STRATEGY:
1. Identify Support (S) and Resistance (R) levels from the data
2. Calculate Midpoint = (S + R) / 2
3. If price > midpoint → SELL toward midpoint (price will revert down)
4. If price < midpoint → BUY toward midpoint (price will revert up)
5. TP = distance to midpoint, capped at 5 pts. Even 1-2 pts is GOOD.
6. SL = Calculate based on ATR and structure (typically 3-10 pts)

CRITICAL RULES:
- You MUST find a trade. SKIP is NOT an option unless market is literally dead (zero volume/weekend).
- Small profits (1-2 pts) are PERFECTLY FINE. A 1pt win is better than SKIP.
- Do NOT counter-trend if momentum > 8/10 (in that case, trade WITH trend)
- If unsure, use smaller TP (1-2 pts) with tighter SL

Reply ONLY in this JSON format:
{{"action":"BUY"or"SELL","tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief reason","market_regime":"trending"or"ranging"or"volatile"}}"""
    return call_openrouter(prompt, "Agent1-MR")

def ai_agent_trend_following(market_data, bid, ask, evolution_ctx):
    """Agent 2: Trend-Following Analysis"""
    entry = (bid + ask) / 2
    prompt = f"""You are an expert XAUUSD Trend-Following scalper. Your PRIMARY GOAL is to FIND a profitable trade NOW.

CURRENT PRICE: Bid={bid}, Ask={ask}, Entry={entry:.3f}

{market_data}
{evolution_ctx}

TREND-FOLLOWING STRATEGY:
1. Identify trend from EMA20/EMA50/MACD/ADX
2. Uptrend (EMA20 > EMA50, MACD positive) → BUY
3. Downtrend (EMA20 < EMA50, MACD negative) → SELL
4. TP = 1-5 pts based on momentum (ADX strength)
5. SL = ATR-based, placed beyond recent swing high/low
6. Do NOT trade if TP would hit a major S/R level before reaching target

CRITICAL RULES:
- You MUST find a trade. SKIP is NOT an option unless market is literally dead.
- Even weak trends give 1-2 pts profit. TRADE IT.
- If ADX < 20 (weak trend), use smaller TP (1-2 pts)
- If ADX > 25 (strong trend), use larger TP (3-5 pts)

Reply ONLY in this JSON format:
{{"action":"BUY"or"SELL","tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief reason","market_regime":"trending"or"ranging"or"volatile"}}"""
    return call_openrouter(prompt, "Agent2-TF")

def ai_agent_coordinator(a1_result, a2_result, market_data, bid, ask, evolution_ctx):
    """Agent 3: Coordinator - Final Decision"""
    entry = (bid + ask) / 2
    prompt = f"""You are the FINAL decision maker for XAUUSD trading. You MUST decide BUY or SELL.

CURRENT PRICE: Entry={entry:.3f}

AGENT 1 (Mean-Reversion): {json.dumps(a1_result) if a1_result else "FAILED"}
AGENT 2 (Trend-Following): {json.dumps(a2_result) if a2_result else "FAILED"}

{evolution_ctx}

YOUR DECISION RULES:
- If both agents agree on direction → Use that direction (higher confidence)
- If they disagree → Pick the one with higher strength AND better reason
- If one failed → Use the other
- If both failed → Analyze the market data yourself and decide
- SKIP is FORBIDDEN unless market is completely dead (weekend/zero volume)
- Small profit (1-2 pts) is ALWAYS better than SKIP
- SL must be reasonable (ATR-based, 3-10 pts)

Reply ONLY in this JSON format:
{{"action":"BUY"or"SELL","chosen_set":1or2,"tp_points":1-5,"sl_points":3-10,"strength":1-10,"reason":"brief reason","market_regime":"trending"or"ranging"or"volatile"}}"""
    return call_openrouter(prompt, "Coordinator")

# =============================================================================
# PARALLEL EXECUTION
# =============================================================================
def run_parallel_analysis(market_data, bid, ask):
    """Run Agent 1 + Agent 2 in parallel, then Coordinator if needed"""
    evolution_ctx = get_evolution_context()
    log("  [Parallel] Starting Agent1(MR) + Agent2(TF)...")
    
    results = {}
    
    def run_a1():
        results['a1'] = ai_agent_mean_reversion(market_data, bid, ask, evolution_ctx)
    
    def run_a2():
        results['a2'] = ai_agent_trend_following(market_data, bid, ask, evolution_ctx)
    
    t1 = threading.Thread(target=run_a1)
    t2 = threading.Thread(target=run_a2)
    t1.start()
    t2.start()
    t1.join(timeout=90)
    t2.join(timeout=90)
    
    a1 = results.get('a1')
    a2 = results.get('a2')
    
    log(f"  [Parallel] Agent1: {'OK' if a1 else 'FAIL'} | Agent2: {'OK' if a2 else 'FAIL'}")
    
    # If both agree, skip Coordinator (save tokens)
    if a1 and a2:
        a1_action = a1.get('action', '')
        a2_action = a2.get('action', '')
        
        if a1_action == a2_action and a1_action in ['BUY', 'SELL']:
            a1_str = a1.get('strength', 0)
            a2_str = a2.get('strength', 0)
            chosen = a1 if a1_str >= a2_str else a2
            chosen['chosen_set'] = 1 if a1_str >= a2_str else 2
            log(f"  [Parallel] Both agree: {a1_action} - skip Coordinator (save tokens)")
            return chosen
    
    # Need Coordinator
    log("  [Parallel] Calling Coordinator...")
    final = ai_agent_coordinator(a1, a2, market_data, bid, ask, evolution_ctx)
    
    if final:
        return final
    
    # Fallback: use whatever we have
    if a1 and a1.get('action') in ['BUY', 'SELL']:
        a1['chosen_set'] = 1
        return a1
    if a2 and a2.get('action') in ['BUY', 'SELL']:
        a2['chosen_set'] = 2
        return a2
    
    return None

# =============================================================================
# BREAK-EVEN LOGIC
# =============================================================================
def check_and_apply_breakeven(positions):
    """Apply break-even when profit >= 50% of TP distance"""
    for p in positions:
        pos_type = p.get('type', '')
        pos_open = p.get('openPrice', 0)
        pos_sl = p.get('stopLoss', 0)
        pos_tp = p.get('takeProfit', 0)
        pos_id = p.get('id', '')
        current_price = p.get('currentPrice', 0)
        
        if not (pos_open and pos_tp and pos_id):
            continue
        
        # Already at break-even?
        if pos_type == 'POSITION_TYPE_BUY' and pos_sl >= pos_open:
            continue
        if pos_type == 'POSITION_TYPE_SELL' and pos_sl > 0 and pos_sl <= pos_open:
            continue
        
        if pos_type == 'POSITION_TYPE_BUY':
            tp_distance = pos_tp - pos_open
            current_profit = current_price - pos_open if current_price else 0
            if tp_distance > 0 and current_profit >= tp_distance * 0.5:
                # Move SL to entry
                try:
                    requests.post(
                        f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
                        headers=headers, json={
                            "actionType": "POSITION_MODIFY",
                            "positionId": pos_id,
                            "stopLoss": pos_open,
                            "takeProfit": pos_tp
                        }, verify=False, timeout=10
                    )
                    log(f"  [BE] BUY position {pos_id}: SL moved to {pos_open}")
                except:
                    pass
        
        elif pos_type == 'POSITION_TYPE_SELL':
            tp_distance = pos_open - pos_tp
            current_profit = pos_open - current_price if current_price else 0
            if tp_distance > 0 and current_profit >= tp_distance * 0.5:
                try:
                    requests.post(
                        f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
                        headers=headers, json={
                            "actionType": "POSITION_MODIFY",
                            "positionId": pos_id,
                            "stopLoss": pos_open,
                            "takeProfit": pos_tp
                        }, verify=False, timeout=10
                    )
                    log(f"  [BE] SELL position {pos_id}: SL moved to {pos_open}")
                except:
                    pass

# =============================================================================
# MAIN TRADE CHECK
# =============================================================================
def check_trade():
    """วิเคราะห์ตลาดและตัดสินใจเทรด"""
    global last_recommendation
    
    log("=" * 60)
    log("TRADE CHECK - Kanutsanan Pongpanna AI v5.0 (Self-Evolution)")
    log("=" * 60)
    
    # Market open?
    if not check_market_open():
        return {"status": "SKIP", "message": "Market closed (Weekend/Holiday)"}
    
    # API keys?
    if not ACCOUNT_ID or not API_KEY or not OPENROUTER_API_KEY:
        return {"status": "ERROR", "message": "Missing API keys"}
    
    # Account info
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                           headers=headers, verify=False, timeout=10)
        if resp.status_code != 200:
            return {"status": "ERROR", "message": f"Account API: {resp.status_code}"}
        acc = resp.json()
    except Exception as e:
        return {"status": "ERROR", "message": f"Connection: {e}"}
    
    balance = acc.get('balance', 0)
    equity = acc.get('equity', 0)
    free_margin = acc.get('freeMargin', 0)
    log(f"  Balance:{balance} Equity:{equity} Free:{free_margin}")
    
    # Positions & Break-Even
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                           headers=headers, verify=False, timeout=10)
        positions = resp.json() if resp.status_code == 200 else []
        if positions:
            log(f"  Positions: {len(positions)}/{MAX_POSITIONS}")
            check_and_apply_breakeven(positions)
            if len(positions) >= MAX_POSITIONS:
                return {"status": "SKIP", "message": f"Max positions reached ({MAX_POSITIONS})"}
    except:
        positions = []
    
    # Current price
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/symbols/XAUUSD.sml/current-price",
                           headers=headers, verify=False, timeout=10)
        if resp.status_code != 200:
            return {"status": "ERROR", "message": f"Price API: {resp.status_code}"}
        price = resp.json()
        bid = price.get('bid', 0)
        ask = price.get('ask', 0)
        spread = round(ask - bid, 3)
        entry = (bid + ask) / 2
        log(f"  Bid:{bid} Ask:{ask} Spread:{spread}")
        if spread <= 0 or bid <= 0:
            return {"status": "SKIP", "message": "Market closed (invalid price)"}
    except Exception as e:
        return {"status": "ERROR", "message": f"Price: {e}"}
    
    # Get market data (try MetaAPI first, then TradingView)
    log("  Fetching market data...")
    market_data = get_candles_from_metaapi()
    data_source = "MetaAPI"
    
    if not market_data:
        market_data = get_tradingview_data()
        data_source = "TradingView"
    
    if not market_data:
        return {"status": "SKIP", "message": "No market data from any source"}
    
    log(f"  Data source: {data_source}")
    
    # AI Parallel Analysis
    log("  AI Analysis (Dual Calculation + Parallel)...")
    ai_decision = run_parallel_analysis(market_data, bid, ask)
    
    if not ai_decision:
        return {"status": "SKIP", "message": "All AI agents failed"}
    
    signal = ai_decision.get('action', 'SKIP')
    strength = ai_decision.get('strength', 5)
    tp_pts = ai_decision.get('tp_points', 3)
    sl_pts = ai_decision.get('sl_points', 5)
    chosen_set = ai_decision.get('chosen_set', 0)
    reason = ai_decision.get('reason', '')
    market_regime = ai_decision.get('market_regime', 'unknown')
    
    # Validate parameters
    tp_pts = max(1, min(TP_MAX, int(tp_pts))) if isinstance(tp_pts, (int, float)) else 3
    sl_pts = max(2, min(15, int(sl_pts))) if isinstance(sl_pts, (int, float)) else 5
    
    if signal not in ['BUY', 'SELL']:
        return {"status": "SKIP", "message": f"AI decision: {signal} - {reason}"}
    
    # Calculate prices
    if signal == "SELL":
        sl_price = round(entry + sl_pts, 3)
        tp_price = round(entry - tp_pts, 3)
        action_type = "ORDER_TYPE_SELL"
    else:
        sl_price = round(entry - sl_pts, 3)
        tp_price = round(entry + tp_pts, 3)
        action_type = "ORDER_TYPE_BUY"
    
    # Auto lot sizing
    max_margin_use = free_margin * (MAX_MARGIN_PERCENT / 100)
    raw_lot = max_margin_use / (entry / LEVERAGE * 1000)
    lot = max(MIN_LOT, round(int(raw_lot * 1000) * 0.001, 3))
    lot = min(lot, MAX_LOT)
    margin_needed = round(entry * lot / LEVERAGE, 2)
    
    if free_margin < margin_needed or lot < MIN_LOT:
        return {"status": "SKIP", "message": f"Insufficient margin ({free_margin} < {margin_needed})"}
    
    recommendation = {
        "status": "READY",
        "signal": signal,
        "action_type": action_type,
        "lot": lot,
        "entry": round(entry, 3),
        "sl": sl_price,
        "tp": tp_price,
        "sl_pts": sl_pts,
        "tp_pts": tp_pts,
        "strength": strength,
        "chosen_set": chosen_set,
        "reason": reason,
        "market_regime": market_regime,
        "data_source": data_source,
        "balance": balance,
        "equity": equity,
        "free_margin": free_margin,
        "margin_needed": margin_needed,
        "bid": bid,
        "ask": ask,
        "spread": spread,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    last_recommendation = recommendation
    log(f"  READY: {signal} {lot}lot @{entry:.3f} SL:{sl_price} TP:{tp_price} Str:{strength}/10 [{market_regime}]")
    return recommendation

# =============================================================================
# APPROVE / EXECUTE TRADE
# =============================================================================
def approve_trade(rec=None):
    """Execute the trade"""
    global last_recommendation
    
    if rec is None:
        rec = last_recommendation
    
    if not rec or rec.get('status') != 'READY':
        return {"status": "ERROR", "message": "No pending recommendation"}
    
    comment = f"{TRADE_COMMENT} Set{rec.get('chosen_set',0)} Str{rec.get('strength',0)}"
    
    try:
        resp = requests.post(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
            headers=headers,
            json={
                "actionType": rec['action_type'],
                "symbol": "XAUUSD.sml",
                "volume": rec['lot'],
                "stopLoss": rec['sl'],
                "takeProfit": rec['tp'],
                "comment": comment
            },
            verify=False, timeout=15
        )
        
        if resp.status_code == 200:
            result = resp.json()
            order_id = result.get('orderId', 'N/A')
            status = result.get('stringCode', 'OK')
            
            # Record trade in memory
            record_trade(
                rec['signal'], rec['tp_pts'], rec['sl_pts'],
                rec['reason'], rec['data_source'], rec.get('market_regime', 'unknown')
            )
            
            last_recommendation = None
            log(f"  TRADED! {rec['signal']} {rec['lot']}lot Order:{order_id} Status:{status}")
            
            return {
                "status": "TRADED",
                "message": f"{rec['signal']} {rec['lot']}lot @{rec['entry']:.3f} SL:{rec['sl']} TP:{rec['tp']}",
                "order_id": order_id,
                "string_code": status
            }
        else:
            log(f"  FAILED: {resp.status_code} - {resp.text[:150]}")
            return {"status": "FAILED", "message": f"Broker rejected: {resp.status_code} - {resp.text[:100]}"}
    except Exception as e:
        return {"status": "FAILED", "message": f"Error: {e}"}

# =============================================================================
# AUTO TRADE LOOP
# =============================================================================
def auto_trade_loop(interval_minutes=5):
    """เทรดอัตโนมัติ"""
    global auto_trade_running
    log(f"[AUTO] Started - every {interval_minutes} min")
    
    while auto_trade_running:
        try:
            rec = check_trade()
            if rec.get('status') == 'READY':
                log("[AUTO] Signal found! Executing...")
                result = approve_trade(rec)
                log(f"[AUTO] Result: {result.get('status')}: {result.get('message','')}")
            else:
                log(f"[AUTO] {rec.get('status')}: {rec.get('message','')}")
        except Exception as e:
            log(f"[AUTO] ERROR: {e}")
        
        # Wait interval (check every second for stop signal)
        for _ in range(int(interval_minutes * 60)):
            if not auto_trade_running:
                break
            time.sleep(1)
    
    log("[AUTO] Stopped")

def start_auto_trade(interval_minutes=5):
    global auto_trade_running, auto_trade_thread
    if auto_trade_running:
        return {"status": "INFO", "message": "Already running"}
    auto_trade_running = True
    auto_trade_thread = threading.Thread(target=auto_trade_loop, args=(interval_minutes,), daemon=True)
    auto_trade_thread.start()
    return {"status": "STARTED", "message": f"Auto trade started (every {interval_minutes} min)"}

def stop_auto_trade():
    global auto_trade_running, auto_trade_thread
    if not auto_trade_running:
        return {"status": "INFO", "message": "Not running"}
    auto_trade_running = False
    if auto_trade_thread:
        auto_trade_thread.join(timeout=10)
        auto_trade_thread = None
    return {"status": "STOPPED", "message": "Auto trade stopped"}

# =============================================================================
# CLI
# =============================================================================
def print_result(rec):
    print("\n" + "=" * 55)
    status = rec.get('status', '')
    if status == 'READY':
        print(f"  SIGNAL: {rec['signal']} | Strength: {rec['strength']}/10")
        print(f"  Entry: {rec['entry']:.3f}")
        print(f"  TP: {rec['tp']} (+{rec['tp_pts']} pts)")
        print(f"  SL: {rec['sl']} (-{rec['sl_pts']} pts)")
        print(f"  Lot: {rec['lot']} | Margin: {rec['margin_needed']}")
        print(f"  Regime: {rec.get('market_regime','?')} | Set: {rec['chosen_set']}")
        print(f"  Reason: {rec['reason']}")
        print(f"  Source: {rec['data_source']}")
        print(f"\n  Execute: python3 auto_trade.py approve")
    elif status == 'TRADED':
        print(f"  EXECUTED: {rec['message']}")
        print(f"  Order: {rec.get('order_id','N/A')}")
    elif status == 'SKIP':
        print(f"  SKIP: {rec['message']}")
    elif status == 'ERROR':
        print(f"  ERROR: {rec['message']}")
    elif status == 'FAILED':
        print(f"  FAILED: {rec['message']}")
    print("=" * 55 + "\n")

def show_performance():
    memory = load_trade_memory()
    print("\n" + "=" * 55)
    print("  PERFORMANCE - Self-Evolution System v5.0")
    print("=" * 55)
    print(f"  Total Trades: {memory['total_trades']}")
    print(f"  Win Rate: {memory['win_rate']}% ({memory['wins']}W / {memory['losses']}L)")
    print(f"  Total Profit: {memory['total_profit']:.2f}")
    print(f"  Preferred Style: {memory['preferred_style']}")
    print(f"  Preferred Direction: {memory['preferred_direction']}")
    print(f"\n  Market Regime Stats:")
    for regime, stats in memory["market_regime_stats"].items():
        if stats["trades"] > 0:
            wr = round(stats["wins"] / stats["trades"] * 100, 1)
            print(f"    {regime}: {stats['trades']} trades, {wr}% win, profit={stats['profit']:.2f}")
    if memory.get("evolution_notes"):
        print(f"\n  Evolution Notes:")
        for note in memory["evolution_notes"][-3:]:
            print(f"    - {note}")
    print("=" * 55 + "\n")

def main():
    if len(sys.argv) < 2:
        # Default: check + auto approve (for systemd timer)
        rec = check_trade()
        if rec.get('status') == 'READY':
            result = approve_trade(rec)
            print_result(result)
        else:
            print_result(rec)
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd in ['check', 'เช็คเทรด', 'เช็ค']:
        rec = check_trade()
        print_result(rec)
    
    elif cmd in ['approve', 'อนุมัติเทรด', 'อนุมัติ']:
        if last_recommendation and last_recommendation.get('status') == 'READY':
            result = approve_trade()
            print_result(result)
        else:
            print("\n  No pending recommendation. Run 'check' first.\n")
    
    elif cmd in ['auto', 'ตั้งเวลาเทรดอัตโนมัติ', 'ตั้งเวลา']:
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        result = start_auto_trade(interval)
        print(f"\n  {result['message']}\n")
        try:
            while auto_trade_running:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_auto_trade()
            print("\n  Stopped by user.\n")
    
    elif cmd in ['stop', 'ยกเลิกการตั้งเวลาเทรด', 'ยกเลิก', 'หยุด']:
        result = stop_auto_trade()
        print(f"\n  {result['message']}\n")
    
    elif cmd in ['performance', 'ผลงาน', 'perf']:
        show_performance()
    
    elif cmd in ['evolve', 'evolution', 'วิวัฒนาการ']:
        run_evolution_analysis()
    
    else:
        print("""
  Kanutsanan Pongpanna AI Auto Trading v5.0
  
  Usage: python3 auto_trade.py [command]
  
  Commands:
    check        เช็คเทรด (วิเคราะห์ + AI)
    approve      อนุมัติเทรด (execute)
    auto [N]     เทรดอัตโนมัติทุก N นาที (default 5)
    stop         หยุดเทรดอัตโนมัติ
    performance  ดูผลงาน Self-Learning
    evolve       รัน Self-Evolution analysis
        """)

if __name__ == "__main__":
    main()
