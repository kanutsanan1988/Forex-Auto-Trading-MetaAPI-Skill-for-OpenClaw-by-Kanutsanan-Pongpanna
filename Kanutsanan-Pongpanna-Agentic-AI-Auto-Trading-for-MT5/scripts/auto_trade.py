import requests
import json
import urllib3
import time
import os
import re
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# AUTO TRADE SYSTEM - OpenRouter AI Full Control
# =============================================================================
# OpenRouter AI ทำหน้าที่หลักทั้งหมด:
#   - วิเคราะห์ข้อมูลกราฟ
#   - คำนวณ indicators
#   - ตัดสินใจ BUY/SELL/SKIP
#   - กำหนด SL/TP
#
# CRITICAL RULE: NO REAL-TIME CHART DATA = NO TRADE
# ถ้าดึงข้อมูลกราฟ real-time ไม่ได้จากทุกแหล่ง -> ห้ามเทรดเด็ดขาด
# ต้องรายงานปัญหาและพยายามแก้ไขให้ดึงกราฟ real-time ได้
#
# แหล่งข้อมูลกราฟ (ได้จากแหล่งใดแหล่งหนึ่งก็เทรดได้):
#   1. MetaAPI candles (M15 + M5) - ข้อมูลดิบจากโบรกเกอร์
#   2. TradingView scanner API (https://scanner.tradingview.com/cfd/scan)
#   3. TradingView web page (https://www.tradingview.com/symbols/XAUUSD/?exchange=OANDA&utm_source=androidapp&utm_medium=share)
# ถ้าทั้ง 3 แหล่งไม่ทำงาน -> SKIP + รายงานปัญหา + แก้ไข
# =============================================================================

# Configuration from Environment Variables
# IMPORTANT: API keys are loaded from .env file. NEVER hardcode them in this script!
# DO NOT commit .env file to version control.
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
API_KEY = os.environ.get("METAAPI_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
headers = {"auth-token": API_KEY, "Content-Type": "application/json"}

TRADINGVIEW_WEB_URL = "https://www.tradingview.com/symbols/XAUUSD/?exchange=OANDA&utm_source=androidapp&utm_medium=share"
TRADINGVIEW_SCANNER_URL = "https://scanner.tradingview.com/cfd/scan"

LOG_FILE = "/var/log/auto_trade.log"

def log(msg):
    global LOG_FILE
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    log_msg = f"[{timestamp}] {msg}"
    print(log_msg)
    
    # Also write to log file if possible
    try:
        # Create directory if it doesn't exist (might need sudo, so we fallback to local if it fails)
        log_dir = os.path.dirname(LOG_FILE)
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except PermissionError:
                # Fallback to local directory if no permission for /var/log
                LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_trade.log")
        
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except Exception as e:
        print(f"[{timestamp}] Warning: Could not write to log file {LOG_FILE}: {e}")

def check_market_open():
    """Check if market is open (Not Saturday/Sunday)"""
    now = datetime.now(timezone.utc)
    # 5 = Saturday, 6 = Sunday
    if now.weekday() >= 5:
        return False
    return True

# =============================================================================
# DATA SOURCES - ดึงข้อมูลกราฟ real-time
# =============================================================================

def get_candles_from_metaapi():
    """Source 1: ดึง M15 และ M5 candles จาก MetaAPI"""
    log("  [Source 1: MetaAPI] Fetching candles...")
    candles_m15 = None
    candles_m5 = None
    
    try:
        resp = requests.get(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/15m/candles",
            headers=headers, verify=False, timeout=10,
            params={"limit": 100}
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 10:
                candles_m15 = data
                log(f"  [MetaAPI] Got {len(candles_m15)} M15 candles")
    except Exception as e:
        log(f"  [MetaAPI] M15 error: {e}")
    
    try:
        resp = requests.get(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/5m/candles",
            headers=headers, verify=False, timeout=10,
            params={"limit": 50}
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 5:
                candles_m5 = data
                log(f"  [MetaAPI] Got {len(candles_m5)} M5 candles")
    except Exception as e:
        log(f"  [MetaAPI] M5 error: {e}")
    
    if candles_m15 and len(candles_m15) > 10:
        text = "RAW CANDLE DATA (from MetaAPI broker - REAL-TIME):\n\n"
        text += "M15 Candles (last 30):\n"
        text += "Time | Open | High | Low | Close | Volume\n"
        for c in candles_m15[-30:]:
            text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
        if candles_m5:
            text += "\nM5 Candles (last 20):\n"
            text += "Time | Open | High | Low | Close | Volume\n"
            for c in candles_m5[-20:]:
                text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
        return text
    return None

def get_tradingview_scanner_data():
    """Source 2: ดึง technical indicators จาก TradingView scanner API"""
    log("  [Source 2: TradingView Scanner API] Fetching...")
    
    payload_m15 = {
        'symbols': {'tickers': ['OANDA:XAUUSD']},
        'columns': [
            'Recommend.All|15', 'Recommend.MA|15', 'Recommend.Other|15',
            'RSI|15', 'Stoch.K|15', 'Stoch.D|15',
            'MACD.macd|15', 'MACD.signal|15',
            'EMA20|15', 'SMA20|15', 'EMA50|15', 'SMA50|15',
            'close|15', 'high|15', 'low|15',
            'ADX|15', 'AO|15', 'CCI20|15', 'ATR|15'
        ]
    }
    
    payload_m5 = {
        'symbols': {'tickers': ['OANDA:XAUUSD']},
        'columns': [
            'Recommend.All|5', 'Recommend.MA|5', 'Recommend.Other|5',
            'RSI|5', 'Stoch.K|5', 'Stoch.D|5',
            'MACD.macd|5', 'MACD.signal|5',
            'EMA20|5', 'SMA20|5', 'EMA50|5', 'SMA50|5',
            'close|5', 'high|5', 'low|5',
            'ADX|5', 'AO|5', 'CCI20|5', 'ATR|5'
        ]
    }
    
    try:
        resp_m15 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_m15, timeout=10)
        resp_m5 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_m5, timeout=10)
        
        if resp_m15.status_code != 200 or resp_m5.status_code != 200:
            log(f"  [TradingView Scanner] ERROR: M15={resp_m15.status_code}, M5={resp_m5.status_code}")
            return None
        
        data_m15 = resp_m15.json()
        data_m5 = resp_m5.json()
        
        if data_m15.get('totalCount', 0) == 0 or data_m5.get('totalCount', 0) == 0:
            log("  [TradingView Scanner] ERROR: No data returned")
            return None
        
        m15 = data_m15['data'][0]['d']
        m5 = data_m5['data'][0]['d']
        
        tv_summary = f"""TradingView Scanner Data (OANDA:XAUUSD - REAL-TIME):

M15 Timeframe:
- Recommend.All: {m15[0]:.4f} (range -1 to +1, positive=BUY)
- Recommend.MA: {m15[1]:.4f}
- Recommend.Oscillators: {m15[2]:.4f}
- RSI(14): {m15[3]:.2f}
- Stochastic K: {m15[4]:.2f}
- Stochastic D: {m15[5]:.2f}
- MACD: {m15[6]:.4f}
- MACD Signal: {m15[7]:.4f}
- EMA20: {m15[8]:.3f}
- SMA20: {m15[9]:.3f}
- EMA50: {m15[10]:.3f}
- SMA50: {m15[11]:.3f}
- Close: {m15[12]}
- High: {m15[13]}
- Low: {m15[14]}
- ADX: {m15[15]:.2f}
- Awesome Oscillator: {m15[16]:.4f}
- CCI(20): {m15[17]:.2f}
- ATR(14): {m15[18]:.4f}

M5 Timeframe:
- Recommend.All: {m5[0]:.4f}
- Recommend.MA: {m5[1]:.4f}
- Recommend.Oscillators: {m5[2]:.4f}
- RSI(14): {m5[3]:.2f}
- Stochastic K: {m5[4]:.2f}
- Stochastic D: {m5[5]:.2f}
- MACD: {m5[6]:.4f}
- MACD Signal: {m5[7]:.4f}
- EMA20: {m5[8]:.3f}
- SMA20: {m5[9]:.3f}
- EMA50: {m5[10]:.3f}
- SMA50: {m5[11]:.3f}
- Close: {m5[12]}
- High: {m5[13]}
- Low: {m5[14]}
- ADX: {m5[15]:.2f}
- Awesome Oscillator: {m5[16]:.4f}
- CCI(20): {m5[17]:.2f}
- ATR(14): {m5[18]:.4f}"""
        
        log("  [TradingView Scanner] Data fetched successfully")
        return tv_summary
        
    except Exception as e:
        log(f"  [TradingView Scanner] ERROR: {e}")
        return None

def get_tradingview_web_data():
    """Source 3: ดึงข้อมูลจากหน้าเว็บ TradingView โดยตรง"""
    log(f"  [Source 3: TradingView Web] Fetching from {TRADINGVIEW_WEB_URL}...")
    
    try:
        # ใช้ TradingView mini API ที่ embed ในหน้าเว็บ
        ta_url = "https://scanner.tradingview.com/cfd/scan"
        
        payload = {
            'symbols': {'tickers': ['OANDA:XAUUSD']},
            'columns': [
                'Recommend.All', 'Recommend.MA', 'Recommend.Other',
                'RSI', 'Stoch.K', 'Stoch.D',
                'MACD.macd', 'MACD.signal',
                'EMA20', 'SMA20', 'EMA50', 'SMA50',
                'close', 'high', 'low', 'open',
                'ADX', 'AO', 'CCI20', 'ATR',
                'BB.upper', 'BB.lower',
                'Recommend.All|15', 'Recommend.All|5',
                'RSI|15', 'RSI|5',
                'ATR|15', 'ATR|5'
            ]
        }
        
        resp = requests.post(ta_url, json=payload, timeout=10,
                           headers={'User-Agent': 'Mozilla/5.0'})
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('totalCount', 0) > 0:
                d = data['data'][0]['d']
                text = f"""TradingView Web Data (OANDA:XAUUSD - REAL-TIME):
Source: {TRADINGVIEW_WEB_URL}

Daily/Default Timeframe:
- Recommend.All: {d[0]:.4f}
- Recommend.MA: {d[1]:.4f}
- Recommend.Oscillators: {d[2]:.4f}
- RSI(14): {d[3]:.2f}
- Stochastic K: {d[4]:.2f}
- Stochastic D: {d[5]:.2f}
- MACD: {d[6]:.4f}
- MACD Signal: {d[7]:.4f}
- EMA20: {d[8]:.3f}
- SMA20: {d[9]:.3f}
- EMA50: {d[10]:.3f}
- SMA50: {d[11]:.3f}
- Close: {d[12]}
- High: {d[13]}
- Low: {d[14]}
- Open: {d[15]}
- ADX: {d[16]:.2f}
- Awesome Oscillator: {d[17]:.4f}
- CCI(20): {d[18]:.2f}
- ATR(14): {d[19]:.4f}
- Bollinger Upper: {d[20]:.3f}
- Bollinger Lower: {d[21]:.3f}

M15 Summary: Recommend.All={d[22]:.4f}, RSI={d[24]:.2f}, ATR={d[26]:.4f}
M5 Summary: Recommend.All={d[23]:.4f}, RSI={d[25]:.2f}, ATR={d[27]:.4f}"""
                
                log("  [TradingView Web] Data fetched successfully")
                return text
        
        log(f"  [TradingView Web] ERROR: status={resp.status_code}")
        return None
        
    except Exception as e:
        log(f"  [TradingView Web] ERROR: {e}")
        return None

# =============================================================================
# OpenRouter AI - ตัวประมวลผลหลัก (ทำทุกอย่าง)
# =============================================================================

def ask_openrouter_ai(market_data_text, bid, ask, balance, free_margin):
    """
    OpenRouter AI ทำทุกอย่าง:
    - วิเคราะห์ข้อมูลกราฟ
    - คำนวณ/ยืนยัน indicators
    - ตัดสินใจ BUY/SELL/SKIP
    - กำหนด SL/TP
    """
    if not OPENROUTER_API_KEY:
        log("  [OpenRouter] ERROR: No API key!")
        return None
    
    log("  [OpenRouter] Sending data to AI for full analysis...")
    
    prompt = f"""You are an expert XAUUSD (Gold) scalping trader. Analyze ALL market data below and give a trading decision.

CURRENT PRICE:
- Bid: {bid}
- Ask: {ask}
- Spread: {round(ask - bid, 3)}

ACCOUNT:
- Balance: {balance} USD
- Free Margin: {free_margin} USD
- Lot: Auto-calculated (50% of free margin max)
- Leverage: 1:100

{market_data_text}

YOUR TASK:
1. Analyze all indicators and price action
2. Determine M15 trend direction and M5 trend alignment
3. Check for high-probability scalping entry
4. Set appropriate SL/TP (SL = ~20% of M15 ATR, TP <= SL)

RULES:
1. SL = approximately 20% of M15 ATR
2. TP cannot exceed SL (risk:reward minimum 1:1)
3. Only trade if signal strength >= 6/10
4. Both M15 and M5 must align
5. SKIP if market is ranging/choppy/no clear direction

Respond ONLY in this exact JSON format (no markdown, no explanation):
{{"action": "BUY" or "SELL" or "SKIP", "strength": 1-10, "sl_points": number, "tp_points": number, "reason": "brief reason in English"}}"""

    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-3.1-flash-lite",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300
            },
            timeout=30
        )
        
        if resp.status_code != 200:
            log(f"  [OpenRouter] ERROR: {resp.status_code} - {resp.text[:200]}")
            return None
        
        ai_response = resp.json()
        content = ai_response['choices'][0]['message']['content'].strip()
        
        # Parse JSON
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        ai_decision = json.loads(content)
        
        # Handle both old and new format
        signal = ai_decision.get('action', ai_decision.get('signal', 'SKIP'))
        strength = ai_decision.get('strength', 0)
        sl_pts = ai_decision.get('sl_points', ai_decision.get('sl_pts', 0))
        tp_pts = ai_decision.get('tp_points', ai_decision.get('tp_pts', 0))
        reason = ai_decision.get('reason', '')
        
        log(f"  [AI] Decision: {signal} | Strength: {strength}/10")
        log(f"  [AI] SL: {sl_pts} pts | TP: {tp_pts} pts")
        log(f"  [AI] Reason: {reason}")
        
        return {
            "signal": signal,
            "strength": strength,
            "sl_pts": sl_pts,
            "tp_pts": tp_pts,
            "reason": reason
        }
        
    except json.JSONDecodeError:
        log(f"  [OpenRouter] ERROR: Cannot parse response: {content[:200]}")
        return None
    except Exception as e:
        log(f"  [OpenRouter] ERROR: {e}")
        return None

# =============================================================================
# MAIN TRADING LOGIC
# =============================================================================

def check_and_trade():
    log("=" * 60)
    log("AUTO TRADE (OpenRouter AI - Full Control)")
    log("=" * 60)
    
    # Check if credentials are set
    if not ACCOUNT_ID or not API_KEY or not OPENROUTER_API_KEY:
        error_msg = "ERROR: Missing required environment variables (METAAPI_ACCOUNT_ID, METAAPI_TOKEN, OPENROUTER_API_KEY)"
        log(error_msg)
        return error_msg
        
    # Check if market is open
    if not check_market_open():
        log("Market is closed (Weekend). Skipping trade.")
        return "SKIP: Market closed (Weekend)"
    
    # Step 1: Account info
    log("Step 1: Account info...")
    try:
        resp_acc = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                               headers=headers, verify=False, timeout=10)
        if resp_acc.status_code != 200:
            return f"ERROR: Account API {resp_acc.status_code}"
        acc = resp_acc.json()
    except Exception as e:
        return f"ERROR: Connection failed - {e}"
    
    balance = acc.get('balance', 0)
    equity = acc.get('equity', 0)
    free_margin = acc.get('freeMargin', 0)
    log(f"  Balance: {balance} | Equity: {equity} | Free Margin: {free_margin}")
    
    # Step 2: Check positions
    log("Step 2: Positions...")
    try:
        resp_pos = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                               headers=headers, verify=False, timeout=10)
        positions = resp_pos.json() if resp_pos.status_code == 200 else []
        
        if positions:
            for p in positions:
                log(f"  -> {p.get('symbol')} {p.get('type')} Vol:{p.get('volume')} P/L:{p.get('profit')}")
            return "SKIP: Position already open"
    except Exception as e:
        log(f"  [Positions] ERROR: {e}")
        # Continue anyway, might be able to trade
    
    # Step 3: Current price
    log("Step 3: Price...")
    try:
        resp_price = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/symbols/XAUUSD.sml/current-price",
                                 headers=headers, verify=False, timeout=10)
        if resp_price.status_code != 200:
            return f"ERROR: Price API {resp_price.status_code}"
        
        price = resp_price.json()
        bid = price.get('bid', 0)
        ask = price.get('ask', 0)
        spread = round(ask - bid, 3)
        entry = (bid + ask) / 2
        log(f"  Bid: {bid} | Ask: {ask} | Spread: {spread}")
        
        if spread <= 0 or bid <= 0:
            return "SKIP: Market closed or invalid price"
    except Exception as e:
        return f"ERROR: Price fetch failed - {e}"
    
    # Step 4: Get real-time chart data (try 3 sources)
    log("Step 4: Fetching real-time chart data...")
    market_data = None
    data_source = None
    
    # Source 1: MetaAPI candles
    market_data = get_candles_from_metaapi()
    if market_data:
        data_source = "MetaAPI"
    
    # Source 2: TradingView scanner API
    if not market_data:
        market_data = get_tradingview_scanner_data()
        if market_data:
            data_source = "TradingView Scanner"
    
    # Source 3: TradingView web page
    if not market_data:
        market_data = get_tradingview_web_data()
        if market_data:
            data_source = "TradingView Web"
    
    # CRITICAL: No data = No trade
    if not market_data:
        error = ("NO_REALTIME_DATA: All 3 sources failed!\n"
                 "  1. MetaAPI candles: FAILED\n"
                 "  2. TradingView Scanner (https://scanner.tradingview.com/cfd/scan): FAILED\n"
                 f"  3. TradingView Web ({TRADINGVIEW_WEB_URL}): FAILED\n"
                 "  FIX NEEDED: Check network, API keys, and endpoints")
        log(f"  CRITICAL: {error}")
        return f"SKIP: {error}"
    
    log(f"  Data source: {data_source}")
    
    # Step 5: OpenRouter AI analyzes and decides (ALL processing here)
    log("Step 5: OpenRouter AI analysis...")
    ai_decision = ask_openrouter_ai(market_data, bid, ask, balance, free_margin)
    
    if not ai_decision:
        return "SKIP: AI unavailable"
    
    signal = ai_decision['signal']
    strength = ai_decision['strength']
    sl_pts = ai_decision['sl_pts']
    tp_pts = ai_decision['tp_pts']
    
    # Enforce TP <= SL
    if tp_pts > sl_pts:
        tp_pts = sl_pts
    
    # Enforce TP tiered cap
    if tp_pts > 10:
        tp_pts = 5
    elif tp_pts > 5:
        tp_pts = 2.5
    elif tp_pts > 2.5:
        tp_pts = 1
    
    # Check signal
    if signal == "SKIP" or signal is None:
        return f"SKIP: AI says SKIP - {ai_decision.get('reason', '')}"
    
    if strength < 6:
        return f"SKIP: Weak {signal} ({strength}/10) - {ai_decision.get('reason', '')}"
    
    # Step 6: Calculate SL/TP prices
    if signal == "SELL":
        sl = round(entry + sl_pts, 3)
        tp = round(entry - tp_pts, 3)
        action_type = "ORDER_TYPE_SELL"
    else:
        sl = round(entry - sl_pts, 3)
        tp = round(entry + tp_pts, 3)
        action_type = "ORDER_TYPE_BUY"
    
    # Step 7: Auto lot size
    leverage = 100
    max_margin_use = free_margin * 0.5
    raw_lot = max_margin_use / (entry / leverage * 1000)
    lot = max(0.001, round(int(raw_lot * 1000) * 0.001, 3))
    lot = min(lot, 0.1)
    margin_needed = round(entry * lot / leverage, 2)
    
    if free_margin < margin_needed or lot < 0.001:
        return f"SKIP: Insufficient margin (need {margin_needed}, have {free_margin})"
    
    log(f"  {signal} {lot} lot | SL:{sl} TP:{tp} | Margin:{margin_needed}")
    
    # Step 8: Execute trade
    log(f"Step 6: Executing {signal}...")
    trade_payload = {
        "actionType": action_type,
        "symbol": "XAUUSD.sml",
        "volume": lot,
        "stopLoss": sl,
        "takeProfit": tp,
        "comment": "OpenRouter AI Trade"
    }
    
    try:
        resp_trade = requests.post(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
            headers=headers, json=trade_payload, verify=False, timeout=15
        )
        
        if resp_trade.status_code == 200:
            result = resp_trade.json()
            order_id = result.get('orderId', 'N/A')
            status = result.get('stringCode', 'UNKNOWN')
            log(f"  RESULT: {status} | Order: {order_id}")
            
            time.sleep(2)
            resp_acc2 = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                                    headers=headers, verify=False, timeout=10)
            if resp_acc2.status_code == 200:
                acc2 = resp_acc2.json()
                log(f"  Balance: {acc2.get('balance')} | Equity: {acc2.get('equity')} | Free: {acc2.get('freeMargin')}")
            
            return f"TRADED: {signal} {lot}lot @{entry:.3f} SL:{sl} TP:{tp} Order:{order_id} Str:{strength}/10 Src:{data_source}"
        else:
            log(f"  FAILED: {resp_trade.status_code} - {resp_trade.text[:200]}")
            return f"FAILED: {resp_trade.status_code} - {resp_trade.text[:100]}"
    except Exception as e:
        log(f"  [Trade] ERROR: {e}")
        return f"FAILED: Exception during trade execution - {e}"

# =============================================================================
# RUN
# =============================================================================
if __name__ == "__main__":
    try:
        result = check_and_trade()
        log(f"\nRESULT: {result}")
        log("=" * 60)
    except Exception as e:
        log(f"CRITICAL ERROR: {e}")
        log("=" * 60)
        sys.exit(1)
