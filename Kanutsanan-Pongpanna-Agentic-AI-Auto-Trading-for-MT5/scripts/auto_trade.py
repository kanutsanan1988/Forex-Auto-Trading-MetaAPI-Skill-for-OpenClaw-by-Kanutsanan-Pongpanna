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
#   1. MetaAPI candles (M15 + H1) - ข้อมูลดิบจากโบรกเกอร์
#   2. TradingView scanner API (https://scanner.tradingview.com/cfd/scan)
#   3. TradingView web page (https://www.tradingview.com/symbols/XAUUSD/?exchange=OANDA&utm_source=androidapp&utm_medium=share)
# ถ้าทั้ง 3 แหล่งไม่ทำงาน -> SKIP + รายงานปัญหา + แก้ไข
# =============================================================================

# Configuration from Environment Variables
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
API_KEY = os.environ.get("METAAPI_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
MARKET_DATA_URL = f"https://mt-market-data-client-api-v1.{REGION}.agiliumtrade.ai"
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
    """Source 1: ดึง M15 และ H1 candles จาก MetaAPI"""
    log("  [Source 1: MetaAPI] Fetching candles...")
    candles_m15 = None
    candles_h1 = None
    
    try:
        resp = requests.get(
            f"{MARKET_DATA_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/15m/candles",
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
            f"{MARKET_DATA_URL}/users/current/accounts/{ACCOUNT_ID}/historical-market-data/symbols/XAUUSD.sml/timeframes/1h/candles",
            headers=headers, verify=False, timeout=10,
            params={"limit": 50}
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 5:
                candles_h1 = data
                log(f"  [MetaAPI] Got {len(candles_h1)} H1 candles")
    except Exception as e:
        log(f"  [MetaAPI] H1 error: {e}")
    
    if candles_m15 and len(candles_m15) > 10:
        text = "RAW CANDLE DATA (from MetaAPI broker - REAL-TIME):\n\n"
        text += "M15 Candles (last 30):\n"
        text += "Time | Open | High | Low | Close | Volume\n"
        for c in candles_m15[-30:]:
            text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
        if candles_h1:
            text += "\nH1 Candles (last 20):\n"
            text += "Time | Open | High | Low | Close | Volume\n"
            for c in candles_h1[-20:]:
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
    
    payload_h1 = {
        'symbols': {'tickers': ['OANDA:XAUUSD']},
        'columns': [
            'Recommend.All|60', 'Recommend.MA|60', 'Recommend.Other|60',
            'RSI|60', 'Stoch.K|60', 'Stoch.D|60',
            'MACD.macd|60', 'MACD.signal|60',
            'EMA20|60', 'SMA20|60', 'EMA50|60', 'SMA50|60',
            'close|60', 'high|60', 'low|60',
            'ADX|60', 'AO|60', 'CCI20|60', 'ATR|60'
        ]
    }
    
    try:
        resp_m15 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_m15, timeout=10)
        resp_h1 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_h1, timeout=10)
        
        if resp_m15.status_code != 200 or resp_h1.status_code != 200:
            log(f"  [TradingView Scanner] ERROR: M15={resp_m15.status_code}, H1={resp_h1.status_code}")
            return None
        
        data_m15 = resp_m15.json()
        data_h1 = resp_h1.json()
        
        if data_m15.get('totalCount', 0) == 0 or data_h1.get('totalCount', 0) == 0:
            log("  [TradingView Scanner] ERROR: No data returned")
            return None
        
        m15 = data_m15['data'][0]['d']
        h1 = data_h1['data'][0]['d']
        
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

H1 Timeframe:
- Recommend.All: {h1[0]:.4f}
- Recommend.MA: {h1[1]:.4f}
- Recommend.Oscillators: {h1[2]:.4f}
- RSI(14): {h1[3]:.2f}
- Stochastic K: {h1[4]:.2f}
- Stochastic D: {h1[5]:.2f}
- MACD: {h1[6]:.4f}
- MACD Signal: {h1[7]:.4f}
- EMA20: {h1[8]:.3f}
- SMA20: {h1[9]:.3f}
- EMA50: {h1[10]:.3f}
- SMA50: {h1[11]:.3f}
- Close: {h1[12]}
- High: {h1[13]}
- Low: {h1[14]}
- ADX: {h1[15]:.2f}
- Awesome Oscillator: {h1[16]:.4f}
- CCI(20): {h1[17]:.2f}
- ATR(14): {h1[18]:.4f}"""
        
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
                'Recommend.All|15', 'Recommend.All|60',
                'RSI|15', 'RSI|60',
                'ATR|15', 'ATR|60'
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
H1 Summary: Recommend.All={d[23]:.4f}, RSI={d[25]:.2f}, ATR={d[27]:.4f}"""
                
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

ANALYSIS STEPS (follow in order):
1. Calculate key indicators from the candle data: RSI(14), MACD, EMA20, EMA50, ATR(14) for M15
2. Determine H1 direction: Bullish / Bearish / Neutral
3. Identify current market structure: trending, ranging, or at extreme

ENTRY DECISION FRAMEWORK:
Apply these checks IN ORDER. Stop at the first match:

A) LATE ENTRY CHECK (do this FIRST):
   - If price is MORE than 1.5x ATR away from EMA20 on M15 -> SKIP (too extended, wait for pullback)
   - This prevents chasing moves that are about to reverse

B) RSI EXTREME + DIVERGENCE CHECK:
   - Calculate RSI from M15 candles
   - If RSI > 70 and you're considering BUY -> check for bearish divergence (price higher high, RSI lower high)
     * If divergence found -> consider REVERSAL SELL instead (see section D)
     * If no divergence but RSI > 70 -> SKIP (overbought, don't chase)
   - If RSI < 30 and you're considering SELL -> check for bullish divergence (price lower low, RSI higher low)
     * If divergence found -> consider REVERSAL BUY instead (see section D)
     * If no divergence but RSI < 30 -> SKIP (oversold, don't chase)

C) TREND-FOLLOWING ENTRY (preferred - Pullback method):
   - H1 DIRECTIONAL FILTER applies here:
     * H1 Bullish -> only BUY
     * H1 Bearish -> only SELL
     * H1 Neutral -> BUY or SELL based on M15
   - IDEAL: Price has pulled back to near EMA20/EMA50 on M15
   - RSI should be between 35-65 (not at extremes)
   - Look for: bounce candle off EMA + momentum resuming in trend direction
   - FALSE BREAKOUT CHECK: If price just broke a key level, verify with:
     * No long rejection wick on breakout candle
     * Volume not declining on breakout
     * Next candle confirms (closes beyond the level)

D) REVERSAL ENTRY (when trend is exhausted):
   - H1 DIRECTIONAL FILTER DOES NOT APPLY to reversal trades
   - ONLY enter reversal when AT LEAST 2 of these 3 conditions are met:
     1. RSI divergence (bearish or bullish)
     2. Reversal candlestick pattern (hammer, shooting star, engulfing, pin bar)
     3. Price at key support/resistance level with rejection wick
   - Reversal trades use TIGHTER SL (closer to the extreme point)
   - Example: H1 is Bullish but M15 shows bearish divergence + shooting star at resistance -> SELL is allowed as reversal

ENTRY PRIORITY (best to worst):
1. Pullback to EMA + trend continuation (BEST - lowest risk)
2. Reversal at extreme with 2+ confirmations (GOOD - H1 filter exempt)
3. Breakout with follow-through confirmation (OK)
4. Chasing extended move far from EMA (NEVER - always SKIP)

RULES:
1. SL = approximately 20% of M15 ATR
2. TP will be capped by the system: TP>10->5, TP>5->2.5, TP>2.5->1. Set your ideal TP but know it will be reduced
3. TP cannot exceed SL (risk:reward minimum 1:1)
4. Only trade if signal strength >= 6/10
5. SKIP if market is ranging/choppy/no clear direction
6. For reversal trades: mark reason as "REVERSAL: ..." so the system knows

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
        
        MAX_POSITIONS = 5
        
        if positions:
            log(f"  Open positions: {len(positions)}/{MAX_POSITIONS}")
            for p in positions:
                pos_type = p.get('type', '')
                pos_profit = p.get('profit', 0)
                pos_open = p.get('openPrice', 0)
                pos_sl = p.get('stopLoss', 0)
                pos_tp = p.get('takeProfit', 0)
                pos_id = p.get('id', '')
                log(f"  -> {p.get('symbol')} {pos_type} Vol:{p.get('volume')} P/L:{pos_profit} Open:{pos_open} SL:{pos_sl} TP:{pos_tp}")
                
                # Break-Even Logic: move SL to entry when profit >= 50% of TP distance
                if pos_open and pos_tp and pos_sl:
                    if pos_type == 'POSITION_TYPE_BUY':
                        tp_distance = pos_tp - pos_open
                        current_sl_distance = pos_open - pos_sl
                    else:  # SELL
                        tp_distance = pos_open - pos_tp
                        current_sl_distance = pos_sl - pos_open
                    
                    # Only move SL if not already at break-even and profit >= 50% of TP
                    if tp_distance > 0 and current_sl_distance > 0.01:
                        half_tp = tp_distance * 0.5
                        if pos_profit > 0 and pos_profit >= half_tp * 0.001 * 100:
                            # Move SL to entry price (break-even)
                            new_sl = pos_open
                            log(f"  [Break-Even] Profit {pos_profit} >= 50% TP distance. Moving SL to entry {new_sl}")
                            try:
                                modify_payload = {
                                    "actionType": "POSITION_MODIFY",
                                    "positionId": str(pos_id),
                                    "stopLoss": new_sl,
                                    "takeProfit": pos_tp
                                }
                                resp_mod = requests.post(
                                    f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/trade",
                                    headers=headers, json=modify_payload, verify=False, timeout=15
                                )
                                if resp_mod.status_code == 200:
                                    log(f"  [Break-Even] SL moved to {new_sl} (break-even) SUCCESS")
                                else:
                                    log(f"  [Break-Even] FAILED: {resp_mod.status_code} - {resp_mod.text[:200]}")
                            except Exception as be_err:
                                log(f"  [Break-Even] ERROR: {be_err}")
                        else:
                            log(f"  [Break-Even] Profit {pos_profit} < 50% TP distance. Waiting...")
            
            # Check if max positions reached
            if len(positions) >= MAX_POSITIONS:
                return f"SKIP: Max positions reached ({len(positions)}/{MAX_POSITIONS}) (break-even checked)"
            else:
                log(f"  Can open {MAX_POSITIONS - len(positions)} more position(s)")
        else:
            log(f"  No open positions (0/{MAX_POSITIONS})")
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
