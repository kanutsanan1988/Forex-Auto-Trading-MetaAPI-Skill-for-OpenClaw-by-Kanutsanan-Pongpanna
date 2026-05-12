#!/usr/bin/env python3
import os
import sys
import re
from datetime import datetime

LOG_FILE = "/var/log/auto_trade.log"

def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def view_logs(lines=50):
    """View the most recent log lines"""
    global LOG_FILE
    if not os.path.exists(LOG_FILE):
        # Try local fallback
        local_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_trade.log")
        if os.path.exists(local_log):
            LOG_FILE = local_log
        else:
            print(f"Log file not found at {LOG_FILE} or {local_log}")
            return

    print_header(f"Recent Logs (Last {lines} lines)")
    
    try:
        with open(LOG_FILE, 'r') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print(line.strip())
    except PermissionError:
        print(f"Permission denied to read {LOG_FILE}. Try running with sudo.")

def summarize_today():
    """Summarize today's trading activity"""
    global LOG_FILE
    if not os.path.exists(LOG_FILE):
        # Try local fallback
        local_log = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_trade.log")
        if os.path.exists(local_log):
            LOG_FILE = local_log
        else:
            print(f"Log file not found at {LOG_FILE}")
            return

    today = datetime.now().strftime('%Y-%m-%d')
    print_header(f"Today's Summary ({today})")
    
    trades = []
    errors = []
    skips = 0
    
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                if today in line:
                    if "TRADED:" in line:
                        trades.append(line.strip())
                    elif "CRITICAL:" in line or "ERROR:" in line or "FAILED:" in line:
                        errors.append(line.strip())
                    elif "SKIP:" in line:
                        skips += 1
                        
        print(f"Total Trades Executed: {len(trades)}")
        print(f"Total Skips: {skips}")
        print(f"Total Errors: {len(errors)}")
        
        if trades:
            print("\n--- Executed Trades ---")
            for trade in trades:
                # Extract just the trade info
                match = re.search(r'TRADED: (.*)', trade)
                if match:
                    print(f"- {match.group(1)}")
                else:
                    print(f"- {trade}")
                    
        if errors:
            print("\n--- Recent Errors ---")
            for error in errors[-5:]: # Show last 5 errors
                print(f"- {error}")
                
    except PermissionError:
        print(f"Permission denied to read {LOG_FILE}. Try running with sudo.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--summary" or sys.argv[1] == "-s":
            summarize_today()
        elif sys.argv[1].isdigit():
            view_logs(int(sys.argv[1]))
        else:
            print("Usage: python3 trade_log.py [lines|--summary]")
            print("  lines: Number of recent log lines to show (default: 50)")
            print("  --summary, -s: Show today's trading summary")
    else:
        summarize_today()
        print("\nTip: Run 'python3 trade_log.py 100' to see the last 100 log lines.")
