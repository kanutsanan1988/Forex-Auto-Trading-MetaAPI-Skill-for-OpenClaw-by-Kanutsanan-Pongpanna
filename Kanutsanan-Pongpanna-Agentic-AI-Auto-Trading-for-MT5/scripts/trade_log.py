#!/usr/bin/env python3
"""
=============================================================================
Kanutsanan Pongpanna AI Auto Trading v5.1 - Trade Log
=============================================================================
คำสั่ง:
  python3 trade_log.py               - ดูประวัติการเทรด
  python3 trade_log.py positions     - ดู positions ปัจจุบัน
  python3 trade_log.py account       - ดูข้อมูลบัญชี
  python3 trade_log.py history [N]   - ดูประวัติ N รายการล่าสุด
  python3 trade_log.py update        - อัพเดทผลเทรดลง Self-Evolution
=============================================================================
"""
import os
import sys
import json
import subprocess
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "eaf88ee0-bc4f-4f70-86e6-e6333d6c4e4f")
API_KEY = os.environ.get("METAAPI_TOKEN", "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJfaWQiOiJkMWExYjVjYzZjZDNmOGIzY2ViOTNjMTQxNGMwM2FmZCIsImFjY2Vzc1J1bGVzIjpbeyJpZCI6InRyYWRpbmctYWNjb3VudC1tYW5hZ2VtZW50LWFwaSIsIm1ldGhvZHMiOlsidHJhZGluZy1hY2NvdW50LW1hbmFnZW1lbnQtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVzdC1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcnBjLWFwaSIsIm1ldGhvZHMiOlsibWV0YWFwaS1hcGk6d3M6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6Im1ldGFhcGktcmVhbC10aW1lLXN0cmVhbWluZy1hcGkiLCJtZXRob2RzIjpbIm1ldGFhcGktYXBpOndzOnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJtZXRhc3RhdHMtYXBpIiwibWV0aG9kcyI6WyJtZXRhc3RhdHMtYXBpOnJlc3Q6cHVibGljOio6KiJdLCJyb2xlcyI6WyJyZWFkZXIiLCJ3cml0ZXIiXSwicmVzb3VyY2VzIjpbIio6JFVTRVJfSUQkOioiXX0seyJpZCI6InJpc2stbWFuYWdlbWVudC1hcGkiLCJtZXRob2RzIjpbInJpc2stbWFuYWdlbWVudC1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoiY29weWZhY3RvcnktYXBpIiwibWV0aG9kcyI6WyJjb3B5ZmFjdG9yeS1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciIsIndyaXRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfSx7ImlkIjoibXQtbWFuYWdlci1hcGkiLCJtZXRob2RzIjpbIm10LW1hbmFnZXItYXBpOnJlc3Q6ZGVhbGluZzoqOioiLCJtdC1tYW5hZ2VyLWFwaTpyZXN0OnB1YmxpYzoqOioiXSwicm9sZXMiOlsicmVhZGVyIiwid3JpdGVyIl0sInJlc291cmNlcyI6WyIqOiRVU0VSX0lEJDoqIl19LHsiaWQiOiJiaWxsaW5nLWFwaSIsIm1ldGhvZHMiOlsiYmlsbGluZy1hcGk6cmVzdDpwdWJsaWM6KjoqIl0sInJvbGVzIjpbInJlYWRlciJdLCJyZXNvdXJjZXMiOlsiKjokVVNFUl9JRCQ6KiJdfV0sImlnbm9yZVJhdGVMaW1pdHMiOmZhbHNlLCJ0b2tlbklkIjoiMjAyMTAyMTMiLCJpbXBlcnNvbmF0ZWQiOmZhbHNlLCJyZWFsVXNlcklkIjoiZDFhMWI1Y2M2Y2QzZjhiM2NlYjkzYzE0MTRjMDNhZmQiLCJpYXQiOjE3NzgyMzU0ODF9.b_WWWKQoH2lUWMwpnFdlcU-qePQgcPfpR1t0F4w2drUe8h80n2awJGHR6sQglNU4IJoVz7Ec2RqKHuYLDIUyDwdLwNV_zwanlUYsmo2x_OLmLNBSw1Xzkdd7T9V-DHKE8bU6ams1VkTWhse_q_LlUSdqMG8RJYJpxaHmNynOvA1PCLTwsrVi4_JFnTPf3MKMLmO95bE9MkOyuAZ1d2282fdls9CsBcRhEUwddoANxCpHg0AcXcCotUrpyQgQfmaOkzpAFgjounx5ZzvoKGVjCmzD3gxnecaG4azZbNIJwlfbofcA7fqvL_1GU06fPxvWM5c7CrLnvIvdoNbTCrAP-9Fy3LNHiK1AtnmddMh3t0lzdyPpulyZL_DSAfk7ymTAdLqJf68knJIN7p33WImjJgcs9e8rPdZLOHmXwP-PYaPy7Qv4lG5iF7P73LwtQhQ_QCCGJIrClW6A04oCtM9v7iIHcnm8YZtNKNlBQTvJuC0TgwoKuu5rzy7Y5IoZLu0tiz_NF6AHcVCWcONfeLUg6voFPW-cQuxtf1jvD9jBEPnd3fAZyY1dWwArM5syT8zNu73_3mfoC249Q_45QEG45zmUVCaOJQ9h19Ax8nu8QOsERu5uLzvMrrHJwKGjOC6zpNMhnNxcyPH1inbqjCUw1loqWKzZEPLoQnF1I9oc9XQ")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
MEMORY_FILE = os.path.join(SCRIPT_DIR, "trade_memory.json")

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

def load_trade_memory():
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"total_trades": 0, "wins": 0, "losses": 0, "win_rate": 0,
            "total_profit": 0, "recent_trades": [], "market_regime_stats": {},
            "preferred_style": "AUTO", "preferred_direction": "NEUTRAL"}

def save_trade_memory(memory):
    try:
        memory["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f, indent=2)
    except:
        pass

def show_account():
    meta_headers = {"auth-token": API_KEY}
    print("\n" + "=" * 60)
    print("  ACCOUNT INFO")
    print("=" * 60)
    acc = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                   extra_headers=meta_headers, timeout=10)
    if acc:
        print(f"  Balance:     ${acc.get('balance', 0)}")
        print(f"  Equity:      ${acc.get('equity', 0)}")
        print(f"  Free Margin: ${acc.get('freeMargin', 0)}")
        print(f"  Margin:      ${acc.get('margin', 0)}")
        print(f"  Leverage:    1:{acc.get('leverage', 0)}")
    else:
        print("  ERROR: Cannot connect")
    print("=" * 60 + "\n")

def show_positions():
    meta_headers = {"auth-token": API_KEY}
    print("\n" + "=" * 60)
    print("  OPEN POSITIONS")
    print("=" * 60)
    positions = wget_get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                        extra_headers=meta_headers, timeout=10)
    if positions and isinstance(positions, list):
        if not positions:
            print("  No open positions.")
        else:
            total_profit = 0
            for p in positions:
                profit = p.get('profit', 0)
                total_profit += profit
                ptype = "BUY" if "BUY" in p.get('type', '') else "SELL"
                print(f"  {p.get('symbol','')} {ptype} {p.get('volume',0)}lot")
                print(f"    Open: {p.get('openPrice',0)} | SL: {p.get('stopLoss',0)} | TP: {p.get('takeProfit',0)}")
                print(f"    P/L: ${profit:.2f} | Comment: {p.get('comment','')}")
                print()
            print(f"  Total P/L: ${total_profit:.2f} | Count: {len(positions)}")
    else:
        print("  ERROR: Cannot get positions")
    print("=" * 60 + "\n")

def show_history(limit=20):
    meta_headers = {"auth-token": API_KEY}
    print("\n" + "=" * 60)
    print(f"  TRADE HISTORY (last {limit})")
    print("=" * 60)
    
    start_time = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S.000')
    end_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.000')
    url = f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/history-deals/time/{start_time}/{end_time}"
    
    deals = wget_get(url, extra_headers=meta_headers, timeout=15)
    if deals and isinstance(deals, list):
        trade_deals = [d for d in deals if d.get('profit', 0) != 0]
        trade_deals = trade_deals[-limit:]
        total_profit = 0
        wins = losses = 0
        
        for d in trade_deals:
            profit = d.get('profit', 0) + d.get('commission', 0) + d.get('swap', 0)
            total_profit += profit
            if profit > 0: wins += 1
            elif profit < 0: losses += 1
            deal_type = "BUY" if "BUY" in d.get('type', '') else "SELL"
            time_str = d.get('time', '')[:19]
            print(f"  {time_str} | {d.get('symbol','')} {deal_type} {d.get('volume',0)}lot | P/L: ${profit:.2f}")
        
        print(f"\n  Summary: {len(trade_deals)} trades | {wins}W/{losses}L | Total: ${total_profit:.2f}")
        if wins + losses > 0:
            print(f"  Win Rate: {wins/(wins+losses)*100:.1f}%")
    else:
        print("  No deals or connection error")
    
    memory = load_trade_memory()
    if memory["total_trades"] > 0:
        print(f"\n  Self-Evolution Memory:")
        print(f"  Total: {memory['total_trades']} | Win: {memory['win_rate']}% | Profit: {memory['total_profit']:.2f}")
    print("=" * 60 + "\n")

def update_results():
    """อัพเดทผลเทรดจาก MetaAPI ลง Self-Evolution"""
    meta_headers = {"auth-token": API_KEY}
    print("\n  Updating trade results...")
    memory = load_trade_memory()
    
    start_time = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S.000')
    end_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.000')
    url = f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/history-deals/time/{start_time}/{end_time}"
    
    deals = wget_get(url, extra_headers=meta_headers, timeout=15)
    if deals and isinstance(deals, list):
        closed = [d for d in deals if d.get('profit', 0) != 0 and d.get('entryType') == 'DEAL_ENTRY_OUT']
        updated = 0
        for deal in closed[-20:]:
            profit = deal.get('profit', 0) + deal.get('commission', 0) + deal.get('swap', 0)
            for t in memory.get("recent_trades", []):
                if t.get("result") == "pending":
                    t["result"] = "win" if profit > 0 else "loss"
                    t["profit"] = profit
                    if profit > 0: memory["wins"] += 1
                    else: memory["losses"] += 1
                    memory["total_profit"] += profit
                    updated += 1
                    break
        
        if memory["wins"] + memory["losses"] > 0:
            memory["win_rate"] = round(memory["wins"] / (memory["wins"] + memory["losses"]) * 100, 1)
        save_trade_memory(memory)
        print(f"  Updated {updated} results. Win: {memory['win_rate']}%")
    else:
        print("  ERROR: Cannot get deals")
    print()

if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "history"
    
    if cmd in ['history', 'ประวัติ', 'log']:
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        show_history(limit)
    elif cmd in ['positions', 'pos']:
        show_positions()
    elif cmd in ['account', 'acc']:
        show_account()
    elif cmd in ['update', 'อัพเดท']:
        update_results()
    else:
        print("""
  Trade Log v5.1 Commands:
    history [N]  ดูประวัติ
    positions    ดู positions
    account      ดูบัญชี
    update       อัพเดทผลเทรด
        """)
