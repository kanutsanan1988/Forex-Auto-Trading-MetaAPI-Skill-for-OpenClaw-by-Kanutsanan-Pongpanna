#!/usr/bin/env python3
"""
=============================================================================
Kanutsanan Pongpanna AI Auto Trading - Trade Log & Manual Check v3.0
=============================================================================
ระบบเช็คเทรดแบบ Manual + ดูประวัติการเทรด + จัดการ Positions

คำสั่ง:
  python3 trade_log.py                   - สรุปผลการเทรดวันนี้ + บัญชี + positions
  python3 trade_log.py check             - เช็คเทรด (ให้คำแนะนำ)
  python3 trade_log.py approve           - อนุมัติเทรดตามคำแนะนำ
  python3 trade_log.py auto [minutes]    - ตั้งเวลาเทรดอัตโนมัติ
  python3 trade_log.py stop              - ยกเลิกการตั้งเวลาเทรด
  python3 trade_log.py log [N]           - ดู log ล่าสุด N บรรทัด
  python3 trade_log.py positions         - ดู positions ที่เปิดอยู่
  python3 trade_log.py account           - ดูข้อมูลบัญชี
  python3 trade_log.py history [hours]   - ดูประวัติเทรด (default: 24h)
  python3 trade_log.py performance       - สรุปผลงานทั้งหมด
=============================================================================
Trade Comment: "Kanutsanan Pongpanna AI Auto Trading"
=============================================================================
"""

import os
import sys
import re
import json
import requests
import urllib3
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load env
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Config
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
API_KEY = os.environ.get("METAAPI_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
headers = {"auth-token": API_KEY, "Content-Type": "application/json"}

LOG_FILE = os.path.join(SCRIPT_DIR, "auto_trade.log")
TRADE_COMMENT = "Kanutsanan Pongpanna AI Auto Trading"

# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_section(title):
    print(f"\n  --- {title} ---")

def print_divider():
    print(f"  {'─' * 50}")

# =============================================================================
# LOG VIEWING
# =============================================================================

def view_logs(lines=50):
    """View the most recent log lines"""
    if not os.path.exists(LOG_FILE):
        print(f"  ⚠️  Log file not found: {LOG_FILE}")
        print(f"     ระบบยังไม่เคยทำงาน หรือ log ถูกลบไปแล้ว")
        return
    
    print_header(f"📋 Recent Logs (Last {lines} lines)")
    
    try:
        with open(LOG_FILE, 'r') as f:
            all_lines = f.readlines()
            if not all_lines:
                print("  (empty log)")
                return
            for line in all_lines[-lines:]:
                print(f"  {line.strip()}")
    except PermissionError:
        print(f"  ❌ Permission denied: {LOG_FILE}")

def summarize_today():
    """Summarize today's trading activity from logs"""
    if not os.path.exists(LOG_FILE):
        print_header("📊 Trading Summary (Today)")
        print("  ⚠️  No log file found. System hasn't run yet.")
        return
    
    today = datetime.now().strftime('%Y-%m-%d')
    print_header(f"📊 Trading Summary ({today})")
    
    trades = []
    errors = []
    skips = 0
    checks = 0
    
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if today in line:
                    if "TRADED:" in line or "TRADE EXECUTED" in line or "RESULT:" in line:
                        trades.append(line.strip())
                    elif "CRITICAL:" in line or "ERROR:" in line or "FAILED:" in line:
                        errors.append(line.strip())
                    elif "SKIP:" in line or "says SKIP" in line:
                        skips += 1
                    elif "CHECK TRADE" in line:
                        checks += 1
        
        print(f"  📈 Total Checks:  {checks}")
        print(f"  ✅ Total Trades:  {len(trades)}")
        print(f"  ⏭️  Total Skips:   {skips}")
        print(f"  ❌ Total Errors:  {len(errors)}")
        
        if trades:
            print_section("Executed Trades Today")
            for trade in trades[-10:]:
                # Extract meaningful part
                match = re.search(r'TRADED: (.*)', trade)
                if match:
                    print(f"    ✅ {match.group(1)}")
                elif "RESULT:" in trade:
                    match2 = re.search(r'RESULT: (.*)', trade)
                    if match2:
                        print(f"    ✅ {match2.group(1)}")
                elif "TRADE EXECUTED" in trade:
                    print(f"    ✅ {trade.split('] ')[-1] if '] ' in trade else trade}")
                else:
                    print(f"    ✅ {trade[-80:]}")
        
        if errors:
            print_section("Recent Errors (last 5)")
            for error in errors[-5:]:
                err_msg = error.split('] ')[-1] if '] ' in error else error
                print(f"    ❌ {err_msg[:80]}")
        
        if checks == 0 and len(trades) == 0:
            print("\n  💤 ไม่มีกิจกรรมใดๆ ในวันนี้")
        
    except PermissionError:
        print(f"  ❌ Permission denied: {LOG_FILE}")

# =============================================================================
# ACCOUNT & POSITIONS
# =============================================================================

def show_account():
    """Show account information"""
    print_header("💰 Account Information")
    
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                           headers=headers, verify=False, timeout=15)
        if resp.status_code != 200:
            error_msg = ""
            try:
                err = resp.json()
                error_msg = err.get('message', '')[:100]
            except:
                pass
            print(f"  ❌ API returned {resp.status_code}")
            if error_msg:
                print(f"     {error_msg}")
            if resp.status_code == 504:
                print("     💡 Account อาจยังไม่เชื่อมต่อกับ broker (ปกติสำหรับวันหยุด)")
            return None
        
        acc = resp.json()
        balance = acc.get('balance', 0)
        equity = acc.get('equity', 0)
        free_margin = acc.get('freeMargin', 0)
        margin = acc.get('margin', 0)
        leverage = acc.get('leverage', 0)
        pl = equity - balance
        
        print(f"  💵 Balance:     ${balance:.2f}")
        print(f"  📊 Equity:      ${equity:.2f}")
        print(f"  🆓 Free Margin: ${free_margin:.2f}")
        print(f"  🔒 Margin Used: ${margin:.2f}")
        print(f"  ⚡ Leverage:    1:{leverage}")
        print_divider()
        
        pl_emoji = "🟢" if pl >= 0 else "🔴"
        print(f"  {pl_emoji} Unrealized P/L: ${pl:.2f} ({pl/balance*100:.2f}%)" if balance > 0 else f"  {pl_emoji} Unrealized P/L: ${pl:.2f}")
        
        # Margin level
        if margin > 0:
            margin_level = (equity / margin) * 100
            ml_emoji = "🟢" if margin_level > 200 else ("🟡" if margin_level > 100 else "🔴")
            print(f"  {ml_emoji} Margin Level:   {margin_level:.1f}%")
        
        return acc
        
    except requests.exceptions.Timeout:
        print("  ❌ Connection timeout - broker อาจไม่ตอบสนอง")
        return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None

def show_positions():
    """Show open positions with detailed info"""
    print_header("📈 Open Positions")
    
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                           headers=headers, verify=False, timeout=15)
        if resp.status_code != 200:
            print(f"  ❌ API returned {resp.status_code}")
            if resp.status_code == 504:
                print("     💡 Account อาจยังไม่เชื่อมต่อกับ broker")
            return None
        
        positions = resp.json()
        
        if not positions:
            print("  📭 No open positions")
            return []
        
        print(f"  Total: {len(positions)} position(s)\n")
        
        total_profit = 0
        total_volume = 0
        buys = 0
        sells = 0
        
        for i, p in enumerate(positions, 1):
            pos_type = "BUY" if "BUY" in p.get('type', '').upper() else "SELL"
            profit = p.get('profit', 0) or 0
            volume = p.get('volume', 0) or 0
            total_profit += profit
            total_volume += volume
            
            if pos_type == "BUY":
                buys += 1
            else:
                sells += 1
            
            emoji = "🟢" if profit >= 0 else "🔴"
            type_emoji = "📈" if pos_type == "BUY" else "📉"
            
            open_price = p.get('openPrice', 0)
            current_price = p.get('currentPrice', 0)
            sl = p.get('stopLoss', 0)
            tp = p.get('takeProfit', 0)
            comment = p.get('comment', '')
            open_time = p.get('time', '')
            
            print(f"  {emoji} #{i} {p.get('symbol','')} {type_emoji} {pos_type}")
            print(f"     Volume: {volume} | Open: {open_price} | Current: {current_price}")
            print(f"     SL: {sl} | TP: {tp}")
            print(f"     P/L: ${profit:.2f}")
            if comment:
                print(f"     Comment: {comment}")
            if open_time:
                print(f"     Opened: {open_time}")
            print()
        
        print_divider()
        total_emoji = "🟢" if total_profit >= 0 else "🔴"
        print(f"  {total_emoji} Total P/L: ${total_profit:.2f}")
        print(f"  📊 Total Volume: {total_volume:.3f}")
        print(f"  📈 Buys: {buys} | 📉 Sells: {sells}")
        
        return positions
        
    except requests.exceptions.Timeout:
        print("  ❌ Connection timeout")
        return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None

# =============================================================================
# TRADE HISTORY FROM API
# =============================================================================

def show_history(hours=24):
    """Show trade history from MetaAPI"""
    print_header(f"📜 Trade History (Last {hours} hours)")
    
    try:
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        resp = requests.get(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/history-deals",
            headers=headers, verify=False, timeout=15,
            params={"startTime": start_time}
        )
        
        if resp.status_code != 200:
            print(f"  ❌ API returned {resp.status_code}")
            if resp.status_code == 504:
                print("     💡 Account อาจยังไม่เชื่อมต่อกับ broker")
            return
        
        deals = resp.json()
        if not isinstance(deals, list) or len(deals) == 0:
            print("  📭 No deals found in this period")
            return
        
        total_profit = 0
        wins = 0
        losses = 0
        breakeven = 0
        
        for d in deals:
            profit = d.get('profit', 0) or 0
            if profit > 0:
                wins += 1
            elif profit < 0:
                losses += 1
            else:
                breakeven += 1
            total_profit += profit
        
        total_trades = wins + losses
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        print(f"  📊 Total Deals: {len(deals)}")
        print(f"  ✅ Wins: {wins} | ❌ Losses: {losses} | ➖ Break-even: {breakeven}")
        print(f"  🎯 Win Rate: {win_rate:.1f}%")
        
        pl_emoji = "🟢" if total_profit >= 0 else "🔴"
        print(f"  {pl_emoji} Total P/L: ${total_profit:.2f}")
        
        if wins > 0:
            avg_win = sum(d.get('profit', 0) for d in deals if d.get('profit', 0) > 0) / wins
            print(f"  📈 Avg Win: ${avg_win:.2f}")
        if losses > 0:
            avg_loss = sum(d.get('profit', 0) for d in deals if d.get('profit', 0) < 0) / losses
            print(f"  📉 Avg Loss: ${avg_loss:.2f}")
        
        print_section("Recent Deals (last 15)")
        for d in deals[-15:]:
            profit = d.get('profit', 0) or 0
            emoji = "🟢" if profit > 0 else ("🔴" if profit < 0 else "➖")
            deal_type = d.get('type', '')
            symbol = d.get('symbol', '')
            volume = d.get('volume', '')
            price = d.get('price', '')
            deal_time = d.get('time', '')[:19] if d.get('time') else ''
            comment = d.get('comment', '')
            
            print(f"    {emoji} {deal_time} | {symbol} {deal_type} | Vol:{volume} | Price:{price} | P/L:${profit:.2f}")
            if comment and TRADE_COMMENT[:10] in comment:
                print(f"       🤖 {comment}")
            
    except requests.exceptions.Timeout:
        print("  ❌ Connection timeout")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

# =============================================================================
# PERFORMANCE REPORT
# =============================================================================

def show_performance():
    """Show overall performance report from log file"""
    print_header("🏆 Performance Report - Kanutsanan Pongpanna AI Auto Trading")
    
    if not os.path.exists(LOG_FILE):
        print("  ⚠️  No log file found")
        return
    
    total_trades = 0
    total_skips = 0
    total_checks = 0
    total_errors = 0
    trade_results = []
    daily_stats = {}
    
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if "CHECK TRADE" in line:
                    total_checks += 1
                    # Extract date
                    match = re.match(r'\[(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date = match.group(1)
                        if date not in daily_stats:
                            daily_stats[date] = {'checks': 0, 'trades': 0, 'skips': 0}
                        daily_stats[date]['checks'] += 1
                
                elif "TRADED:" in line or "TRADE EXECUTED" in line or ("RESULT:" in line and "TRADE_DONE" in line):
                    total_trades += 1
                    match = re.match(r'\[(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date = match.group(1)
                        if date not in daily_stats:
                            daily_stats[date] = {'checks': 0, 'trades': 0, 'skips': 0}
                        daily_stats[date]['trades'] += 1
                
                elif "SKIP:" in line or "says SKIP" in line:
                    total_skips += 1
                    match = re.match(r'\[(\d{4}-\d{2}-\d{2})', line)
                    if match:
                        date = match.group(1)
                        if date not in daily_stats:
                            daily_stats[date] = {'checks': 0, 'trades': 0, 'skips': 0}
                        daily_stats[date]['skips'] += 1
                
                elif "ERROR:" in line or "FAILED:" in line:
                    total_errors += 1
        
        print(f"  📊 Total Checks:    {total_checks}")
        print(f"  ✅ Total Trades:    {total_trades}")
        print(f"  ⏭️  Total Skips:     {total_skips}")
        print(f"  ❌ Total Errors:    {total_errors}")
        
        if total_checks > 0:
            trade_rate = (total_trades / total_checks) * 100
            print(f"  🎯 Trade Rate:      {trade_rate:.1f}% (trades/checks)")
        
        if daily_stats:
            print_section("Daily Breakdown (last 7 days)")
            sorted_dates = sorted(daily_stats.keys(), reverse=True)[:7]
            print(f"    {'Date':<12} {'Checks':<8} {'Trades':<8} {'Skips':<8}")
            print(f"    {'─'*12} {'─'*8} {'─'*8} {'─'*8}")
            for date in sorted_dates:
                d = daily_stats[date]
                print(f"    {date:<12} {d['checks']:<8} {d['trades']:<8} {d['skips']:<8}")
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

# =============================================================================
# MANUAL TRADE CHECK (uses auto_trade module)
# =============================================================================

def manual_check():
    """Run manual trade check using the auto_trade module"""
    print_header("🔍 Manual Trade Check - Kanutsanan Pongpanna AI Auto Trading")
    print("  🔄 Running Dual Calculation + Agentic AI Parallel Processing...")
    print("  ⏳ กรุณารอสักครู่ (กำลังวิเคราะห์ข้อมูลจาก 3 แหล่ง + AI 3 ตัว)...")
    print()
    
    try:
        # Import from auto_trade
        sys.path.insert(0, SCRIPT_DIR)
        from auto_trade import check_trade, print_recommendation
        
        rec = check_trade()
        print_recommendation(rec)
        
        if rec.get('status') == 'READY':
            print("  💡 คำสั่งถัดไป:")
            print("     python3 trade_log.py approve    (อนุมัติเทรดนี้)")
            print("     python3 auto_trade.py approve   (อนุมัติเทรดนี้)")
            print()
        
        return rec
        
    except ImportError as e:
        print(f"  ❌ Cannot import auto_trade module: {e}")
        print(f"  💡 Make sure auto_trade.py is in: {SCRIPT_DIR}")
        return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None

def manual_approve():
    """Approve the last trade recommendation"""
    print_header("✅ Approve Trade - Kanutsanan Pongpanna AI Auto Trading")
    
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from auto_trade import approve_trade, last_recommendation, print_recommendation
        
        if not last_recommendation or last_recommendation.get('status') != 'READY':
            print("  ❌ ไม่มีคำแนะนำที่รอการอนุมัติ")
            print("  💡 กรุณารัน 'python3 trade_log.py check' ก่อน")
            print()
            return None
        
        print(f"  📋 กำลังอนุมัติ:")
        print(f"     Signal: {last_recommendation['signal']}")
        print(f"     Lot:    {last_recommendation['lot']}")
        print(f"     Entry:  {last_recommendation['entry']}")
        print(f"     SL:     {last_recommendation['sl']}")
        print(f"     TP:     {last_recommendation['tp']}")
        print()
        
        result = approve_trade()
        print_recommendation(result)
        return result
        
    except ImportError as e:
        print(f"  ❌ Cannot import auto_trade module: {e}")
        return None
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return None

def manual_auto_trade(interval_minutes=5):
    """Start auto trade from trade_log"""
    print_header(f"🤖 Auto Trade - Every {interval_minutes} minutes")
    
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from auto_trade import start_auto_trade, auto_trade_running
        import time as time_module
        
        result = start_auto_trade(interval_minutes)
        print(f"  {result['message']}")
        print()
        print("  กด Ctrl+C เพื่อหยุด")
        print()
        
        try:
            while True:
                time_module.sleep(1)
        except KeyboardInterrupt:
            from auto_trade import stop_auto_trade
            stop_auto_trade()
            print("\n  ⏹️  Auto trade stopped by user.\n")
    
    except ImportError as e:
        print(f"  ❌ Cannot import auto_trade module: {e}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

def manual_stop():
    """Stop auto trade"""
    print_header("⏹️  Stop Auto Trade")
    
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from auto_trade import stop_auto_trade
        
        result = stop_auto_trade()
        print(f"  {result['message']}")
        print()
    except ImportError as e:
        print(f"  ❌ Cannot import auto_trade module: {e}")
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

# =============================================================================
# QUICK STATUS
# =============================================================================

def quick_status():
    """Show quick system status"""
    print_header("⚡ Quick Status - Kanutsanan Pongpanna AI Auto Trading")
    
    # Check if auto-trade timer is active
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', 'auto-trade.timer'], 
                              capture_output=True, text=True, timeout=5)
        timer_status = result.stdout.strip()
        timer_emoji = "🟢" if timer_status == "active" else "🔴"
        print(f"  {timer_emoji} Auto-Trade Timer: {timer_status}")
    except:
        print(f"  ⚪ Auto-Trade Timer: unknown")
    
    # Check API connectivity
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                           headers=headers, verify=False, timeout=5)
        if resp.status_code == 200:
            print(f"  🟢 MetaAPI Connection: OK")
            acc = resp.json()
            print(f"     Balance: ${acc.get('balance', 0):.2f} | Equity: ${acc.get('equity', 0):.2f}")
        else:
            print(f"  🔴 MetaAPI Connection: Error {resp.status_code}")
    except:
        print(f"  🔴 MetaAPI Connection: Timeout/Failed")
    
    # Check OpenRouter
    if OPENROUTER_API_KEY:
        print(f"  🟢 OpenRouter API Key: Configured")
    else:
        print(f"  🔴 OpenRouter API Key: Missing!")
    
    # Last log entry
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1].strip()
                    print(f"\n  📋 Last log: {last_line[:80]}")
        except:
            pass
    
    print()

# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        # Default: show summary + account + positions + quick status
        quick_status()
        summarize_today()
        show_account()
        show_positions()
        print("\n  ─── คำสั่งที่ใช้ได้ ───")
        print()
        print("    python3 trade_log.py check        - เช็คเทรด (คำแนะนำ)")
        print("    python3 trade_log.py approve       - อนุมัติเทรด")
        print("    python3 trade_log.py auto [N]      - ตั้งเวลาเทรดอัตโนมัติ (N นาที)")
        print("    python3 trade_log.py stop           - ยกเลิกการตั้งเวลาเทรด")
        print("    python3 trade_log.py log [N]        - ดู log (default: 50 lines)")
        print("    python3 trade_log.py positions      - ดู positions")
        print("    python3 trade_log.py account        - ดูข้อมูลบัญชี")
        print("    python3 trade_log.py history [H]    - ดูประวัติ (default: 24 hours)")
        print("    python3 trade_log.py performance    - สรุปผลงาน")
        print("    python3 trade_log.py status         - สถานะระบบ")
        print()
        return
    
    command = sys.argv[1].lower()
    
    # เช็คเทรด
    if command in ['check', 'เช็คเทรด', 'เช็ค', 'c']:
        manual_check()
    
    # อนุมัติเทรด
    elif command in ['approve', 'อนุมัติเทรด', 'อนุมัติ', 'a']:
        manual_approve()
    
    # ตั้งเวลาเทรดอัตโนมัติ
    elif command in ['auto', 'ตั้งเวลาเทรดอัตโนมัติ', 'ตั้งเวลา']:
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        manual_auto_trade(interval)
    
    # ยกเลิกการตั้งเวลาเทรด
    elif command in ['stop', 'ยกเลิกการตั้งเวลาเทรด', 'ยกเลิก', 'หยุด']:
        manual_stop()
    
    # ดู log
    elif command in ['log', 'logs', 'l']:
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        view_logs(lines)
    
    # ดู positions
    elif command in ['positions', 'pos', 'p']:
        show_positions()
    
    # ดูข้อมูลบัญชี
    elif command in ['account', 'acc']:
        show_account()
    
    # ดูประวัติเทรด
    elif command in ['history', 'hist', 'h']:
        hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
        show_history(hours)
    
    # สรุปผลงาน
    elif command in ['performance', 'perf', 'report']:
        show_performance()
    
    # สถานะระบบ
    elif command in ['status', 'สถานะ']:
        quick_status()
    
    # สรุปวันนี้
    elif command in ['summary', 's', '--summary', '-s', 'today']:
        summarize_today()
    
    # ถ้าเป็นตัวเลข = ดู log N บรรทัด
    elif command.isdigit():
        view_logs(int(command))
    
    else:
        print(f"\n  ❓ Unknown command: {command}")
        print("  💡 Run without arguments for help.\n")

if __name__ == "__main__":
    main()
