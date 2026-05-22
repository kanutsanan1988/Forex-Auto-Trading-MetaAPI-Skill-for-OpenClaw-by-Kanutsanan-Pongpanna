#!/usr/bin/env python3
"""
=============================================================================
Kanutsanan Pongpanna AI Auto Trading - Trade Check v3.0
=============================================================================
ระบบเช็คเทรดแบบ Manual (ไฟล์นี้ใช้สำหรับคำสั่ง "เช็คเทรด")

คำสั่ง:
  python3 trade_check.py              - เช็คเทรด (วิเคราะห์กราฟ + AI 3 ตัว)
  python3 trade_check.py approve      - อนุมัติเทรดตามคำแนะนำ
  python3 trade_check.py status       - ดูสถานะระบบ + positions

กระบวนการทำงาน:
  1. ศึกษาทำความเข้าใจกระบวนการคำนวณ + ดูรายละเอียดกราฟ
  2. ดึงข้อมูลจาก 3 แหล่ง (MetaAPI, TradingView Scanner, TradingView Web)
  3. Dual Calculation System:
     - ชุดที่ 1: Mean-Reversion (เทรดเข้าหาจุดกลาง)
     - ชุดที่ 2: Trend-Following (เทรดตามเทรนด์)
  4. Agentic AI Parallel Processing (AI 3 ตัวทำงานพร้อมกัน)
  5. Coordinator Agent ตัดสินใจสุดท้าย
  6. แสดงคำแนะนำ + รอการอนุมัติจากผู้ใช้

เงื่อนไขการเทรด:
  - TP สูงสุด 5 points (เน้นกำไรเล็กแต่บ่อย)
  - SL คำนวณโดย AI (พิจารณา ATR, volatility, S/R levels)
  - Break-Even: ย้าย SL มาจุดเข้าเมื่อกำไร >= 50% ของ TP
  - Auto Lot Sizing (ใช้ margin ไม่เกิน 50%)
  - SKIP เมื่อไม่มั่นใจ (ดีกว่าเทรดแล้วขาดทุน)
  - ต้องมี strength >= 2/10 ถึงจะเทรด
  - Max 10 positions พร้อมกัน
  - ใช้ Gemini 3.5 Flash ผ่าน OpenRouter เป็นตัวประมวลผลหลัก

Trade Comment: "Kanutsanan Pongpanna AI Auto Trading"
=============================================================================
"""

import os
import sys
import json
import time
import requests
import urllib3
import re
import threading
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(SCRIPT_DIR, '.env'))
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =============================================================================
# CONFIGURATION
# =============================================================================
ACCOUNT_ID = os.environ.get("METAAPI_ACCOUNT_ID", "")
API_KEY = os.environ.get("METAAPI_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
AI_MODEL = os.environ.get("AI_MODEL", "google/gemini-3.5-flash")

REGION = "london"
BASE_URL = f"https://mt-client-api-v1.{REGION}.agiliumtrade.ai"
MARKET_DATA_URL = f"https://mt-market-data-client-api-v1.{REGION}.agiliumtrade.ai"
headers = {"auth-token": API_KEY, "Content-Type": "application/json"}

TRADINGVIEW_SCANNER_URL = "https://scanner.tradingview.com/cfd/scan"

# Trading Parameters
MAX_POSITIONS = 10
MAX_LOT = 0.1
MIN_LOT = 0.001
MAX_MARGIN_PERCENT = 50
TP_MAX = 5          # Maximum TP in points
MIN_STRENGTH = 2    # Minimum AI strength to trade

TRADE_COMMENT = "Kanutsanan Pongpanna AI Auto Trading"
LOG_FILE = os.path.join(SCRIPT_DIR, "auto_trade.log")

# State
last_recommendation = None

# =============================================================================
# DISPLAY HELPERS
# =============================================================================

def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_section(title):
    print(f"\n  --- {title} ---")

def log(msg):
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    log_msg = f"[{timestamp}] {msg}"
    print(f"  {log_msg}")
    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_msg + "\n")
    except:
        pass

# =============================================================================
# MARKET CHECK
# =============================================================================

def check_market_open():
    """Check if market is open (Not Saturday/Sunday)"""
    now = datetime.now(timezone.utc)
    if now.weekday() >= 5:
        return False
    return True

# =============================================================================
# DATA SOURCES - ดึงข้อมูลกราฟ real-time
# =============================================================================

def get_candles_from_metaapi():
    """Source 1: ดึง candles ทุก timeframe จาก MetaAPI"""
    log("[Source 1: MetaAPI] Fetching all timeframes...")
    
    timeframes = {
        "1m": {"limit": 60, "label": "M1"},
        "5m": {"limit": 50, "label": "M5"},
        "15m": {"limit": 40, "label": "M15"},
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
                    log(f"  [MetaAPI] Got {len(data)} {config['label']} candles")
        except Exception as e:
            log(f"  [MetaAPI] {config['label']} error: {e}")
    
    if not all_data:
        return None
    
    text = "RAW CANDLE DATA (from MetaAPI broker - REAL-TIME):\n\n"
    for label, candles in all_data.items():
        text += f"{label} Candles (last {len(candles)}):\n"
        text += "Time | Open | High | Low | Close | Volume\n"
        for c in candles:
            text += f"{c.get('time','')} | {c.get('open',0)} | {c.get('high',0)} | {c.get('low',0)} | {c.get('close',0)} | {c.get('tickVolume',0)}\n"
        text += "\n"
    return text

def get_tradingview_scanner_data():
    """Source 2: ดึง technical indicators จาก TradingView scanner API"""
    log("[Source 2: TradingView Scanner] Fetching M5+M15+H1...")
    
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
        resp_m5 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_m5, timeout=10)
        resp_m15 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_m15, timeout=10)
        resp_h1 = requests.post(TRADINGVIEW_SCANNER_URL, json=payload_h1, timeout=10)
        
        results = {}
        
        if resp_m5.status_code == 200:
            data_m5 = resp_m5.json()
            if data_m5.get('totalCount', 0) > 0:
                results['M5'] = data_m5['data'][0]['d']
        
        if resp_m15.status_code == 200:
            data_m15 = resp_m15.json()
            if data_m15.get('totalCount', 0) > 0:
                results['M15'] = data_m15['data'][0]['d']
        
        if resp_h1.status_code == 200:
            data_h1 = resp_h1.json()
            if data_h1.get('totalCount', 0) > 0:
                results['H1'] = data_h1['data'][0]['d']
        
        if not results:
            return None
        
        tv_summary = "TradingView Scanner Data (OANDA:XAUUSD - REAL-TIME):\n\n"
        
        for tf, d in results.items():
            tv_summary += f"{tf} Timeframe:\n"
            tv_summary += f"- Recommend.All: {d[0]:.4f} (range -1 to +1, positive=BUY)\n"
            tv_summary += f"- Recommend.MA: {d[1]:.4f}\n"
            tv_summary += f"- Recommend.Oscillators: {d[2]:.4f}\n"
            tv_summary += f"- RSI(14): {d[3]:.2f}\n"
            tv_summary += f"- Stochastic K: {d[4]:.2f}\n"
            tv_summary += f"- Stochastic D: {d[5]:.2f}\n"
            tv_summary += f"- MACD: {d[6]:.4f}\n"
            tv_summary += f"- MACD Signal: {d[7]:.4f}\n"
            tv_summary += f"- EMA20: {d[8]:.3f}\n"
            tv_summary += f"- SMA20: {d[9]:.3f}\n"
            tv_summary += f"- EMA50: {d[10]:.3f}\n"
            tv_summary += f"- SMA50: {d[11]:.3f}\n"
            tv_summary += f"- Close: {d[12]}\n"
            tv_summary += f"- High: {d[13]}\n"
            tv_summary += f"- Low: {d[14]}\n"
            tv_summary += f"- ADX: {d[15]:.2f}\n"
            tv_summary += f"- Awesome Oscillator: {d[16]:.4f}\n"
            tv_summary += f"- CCI(20): {d[17]:.2f}\n"
            tv_summary += f"- ATR(14): {d[18]:.4f}\n\n"
        
        log("[TradingView Scanner] Data fetched successfully")
        return tv_summary
        
    except Exception as e:
        log(f"[TradingView Scanner] ERROR: {e}")
        return None

def get_tradingview_web_data():
    """Source 3: ดึงข้อมูลจากหน้าเว็บ TradingView (Daily + cross-timeframe)"""
    log("[Source 3: TradingView Web] Fetching Daily data...")
    
    try:
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
        
        resp = requests.post(TRADINGVIEW_SCANNER_URL, json=payload, timeout=10,
                           headers={'User-Agent': 'Mozilla/5.0'})
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get('totalCount', 0) > 0:
                d = data['data'][0]['d']
                text = f"""TradingView Web Data (OANDA:XAUUSD - REAL-TIME):

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
                
                log("[TradingView Web] Data fetched successfully")
                return text
        
        return None
        
    except Exception as e:
        log(f"[TradingView Web] ERROR: {e}")
        return None

def get_trade_history():
    """ดึงประวัติการเทรดล่าสุดจาก MetaAPI"""
    try:
        now = datetime.now(timezone.utc)
        start_time = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
        resp = requests.get(
            f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/history-deals",
            headers=headers, verify=False, timeout=10,
            params={"startTime": start_time}
        )
        if resp.status_code == 200:
            deals = resp.json()
            if isinstance(deals, list) and len(deals) > 0:
                text = "\nTRADE HISTORY (last 24 hours):\n"
                text += "Time | Type | Volume | Price | Profit | Comment\n"
                for d in deals[-30:]:
                    text += f"{d.get('time','')} | {d.get('type','')} | {d.get('volume','')} | {d.get('price','')} | {d.get('profit','')} | {d.get('comment','')}\n"
                return text
        return None
    except:
        return None

# =============================================================================
# AGENTIC AI PARALLEL PROCESSING
# =============================================================================
# ใช้ OpenRouter AI เป็นตัวประมวลผลแบบขนาน (Parallel Processing)
# - Agent 1: วิเคราะห์ชุดคำนวณที่ 1 (Mean-Reversion)
# - Agent 2: วิเคราะห์ชุดคำนวณที่ 2 (Trend-Following)
# - Agent 3 (Coordinator): รวมผลลัพธ์จาก Agent 1 & 2 แล้วตัดสินใจ
# =============================================================================

def call_openrouter(prompt, agent_name):
    """Call OpenRouter API with Gemini 3.5 Flash"""
    if not OPENROUTER_API_KEY:
        log(f"[{agent_name}] ERROR: No API key!")
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
                "temperature": 0.1,
                "max_tokens": 500
            },
            timeout=45
        )
        
        if resp.status_code != 200:
            log(f"[{agent_name}] ERROR: {resp.status_code} - {resp.text[:200]}")
            return None
        
        ai_response = resp.json()
        content = ai_response['choices'][0]['message']['content'].strip()
        
        # Parse JSON
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        
        json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group(0)
        
        result = json.loads(content)
        log(f"[{agent_name}] Result: {result.get('action', 'N/A')} | Confidence: {result.get('confidence', result.get('strength', 'N/A'))}")
        return result
        
    except json.JSONDecodeError:
        log(f"[{agent_name}] ERROR: Cannot parse JSON response")
        return None
    except Exception as e:
        log(f"[{agent_name}] ERROR: {e}")
        return None

def ai_agent_mean_reversion(market_data_text, bid, ask):
    """Agent 1: คำนวณชุดที่ 1 - Mean-Reversion (เทรดเข้าหาจุดกลาง)"""
    prompt = f"""You are Agent 1: Mean-Reversion Analyst for XAUUSD.

CURRENT PRICE: Bid={bid}, Ask={ask}, Entry={(bid+ask)/2:.3f}

{market_data_text}

YOUR TASK (Calculation Set 1 - Mean-Reversion):
1. Identify the BEST Support (S) and Resistance (R) levels from the chart data
2. Calculate MIDPOINT = (S + R) / 2
3. Determine direction:
   - If entry price > midpoint → SELL (price should revert down toward midpoint)
   - If entry price < midpoint → BUY (price should revert up toward midpoint)
4. Calculate TP = distance from entry to midpoint (cap at max 5 pts)
5. Calculate SL based on your analysis (consider volatility, ATR, nearby levels)
6. Check trend/momentum:
   - Rate trend strength 1-10
   - If your trade direction is OPPOSITE to the trend AND trend > 8/10 → DO NOT TRADE
7. This strategy works best during SWING/SIDEWAYS markets

Respond ONLY in this exact JSON format:
{{"can_trade": true/false, "action": "BUY"/"SELL"/"SKIP", "support": price, "resistance": price, "midpoint": price, "tp_points": 1-5, "sl_points": number, "trend_strength": 1-10, "trend_direction": "UP"/"DOWN"/"NEUTRAL", "confidence": 1-10, "reason": "brief explanation"}}"""

    return call_openrouter(prompt, "Agent1-MeanReversion")

def ai_agent_trend_following(market_data_text, bid, ask):
    """Agent 2: คำนวณชุดที่ 2 - Trend-Following (เทรดตามเทรนด์)"""
    prompt = f"""You are Agent 2: Trend-Following Analyst for XAUUSD.

CURRENT PRICE: Bid={bid}, Ask={ask}, Entry={(bid+ask)/2:.3f}

{market_data_text}

YOUR TASK (Calculation Set 2 - Trend-Following):
1. Identify the BEST Support (S) and Resistance (R) levels from the chart data
2. Check trend and momentum strength (rate 1-10)
3. If strong uptrend → BUY with TP = 5 pts
   If strong downtrend → SELL with TP = 5 pts
4. CRITICAL CHECK: Will the TP level be too close to S/R?
   - For BUY: if (entry + 5) is within 3 pts of Resistance → DO NOT TRADE
   - For SELL: if (entry - 5) is within 3 pts of Support → DO NOT TRADE
   - If TP level is far from S/R → OK to trade
5. Calculate SL based on your analysis (consider volatility, ATR, nearby levels)
6. This strategy works best when there's a CLEAR TREND with strong momentum

Respond ONLY in this exact JSON format:
{{"can_trade": true/false, "action": "BUY"/"SELL"/"SKIP", "support": price, "resistance": price, "tp_points": 5, "sl_points": number, "trend_strength": 1-10, "trend_direction": "UP"/"DOWN"/"NEUTRAL", "tp_near_sr": true/false, "confidence": 1-10, "reason": "brief explanation"}}"""

    return call_openrouter(prompt, "Agent2-TrendFollowing")

def ai_agent_coordinator(agent1_result, agent2_result, market_data_text, bid, ask):
    """Agent 3 (Coordinator): รวมผลลัพธ์จาก Agent 1 & 2 แล้วตัดสินใจสุดท้าย"""
    prompt = f"""You are the Coordinator Agent for XAUUSD trading. You received results from 2 parallel analysis agents.

CURRENT PRICE: Bid={bid}, Ask={ask}, Entry={(bid+ask)/2:.3f}

=== AGENT 1 RESULT (Mean-Reversion - trade toward midpoint) ===
{json.dumps(agent1_result, indent=2) if agent1_result else "FAILED - No result"}

=== AGENT 2 RESULT (Trend-Following - trade with momentum) ===
{json.dumps(agent2_result, indent=2) if agent2_result else "FAILED - No result"}

YOUR DECISION RULES:
1. If Set 1 can trade but Set 2 cannot → Use Set 1
2. If Set 1 cannot trade but Set 2 can → Use Set 2
3. If BOTH cannot trade → SKIP (do not trade)
4. If BOTH can trade:
   - If trend/momentum < 6/10 → You choose which set gives best quick profit
   - If trend/momentum >= 6/10 → Prefer Set 2 (trend-following)
   
IMPORTANT:
- Goal: Maximum profit with minimum loss risk
- TP must be 1-5 points (never exceed 5)
- SL: Use the value from the chosen agent's analysis
- Consider which setup has higher probability of hitting TP quickly
- Think deeply about market conditions before deciding

Respond ONLY in this exact JSON format:
{{"action": "BUY"/"SELL"/"SKIP", "chosen_set": 1/2, "tp_points": 1-5, "sl_points": number, "strength": 1-10, "reason": "which set chosen and why, S/R levels, midpoint"}}"""

    return call_openrouter(prompt, "Agent3-Coordinator")

def run_parallel_analysis(market_data_text, bid, ask):
    """Run Agent 1 and Agent 2 in parallel using threads"""
    log("[Parallel Processing] Starting Agent 1 (Mean-Reversion) and Agent 2 (Trend-Following)...")
    
    results = {}
    
    def run_agent1():
        results['agent1'] = ai_agent_mean_reversion(market_data_text, bid, ask)
    
    def run_agent2():
        results['agent2'] = ai_agent_trend_following(market_data_text, bid, ask)
    
    t1 = threading.Thread(target=run_agent1)
    t2 = threading.Thread(target=run_agent2)
    
    t1.start()
    t2.start()
    
    t1.join(timeout=60)
    t2.join(timeout=60)
    
    agent1_result = results.get('agent1')
    agent2_result = results.get('agent2')
    
    log(f"[Parallel Processing] Agent 1: {'OK' if agent1_result else 'FAILED'}")
    log(f"[Parallel Processing] Agent 2: {'OK' if agent2_result else 'FAILED'}")
    
    # Agent 3: Coordinator makes final decision
    log("[Parallel Processing] Agent 3 (Coordinator) making final decision...")
    final_decision = ai_agent_coordinator(agent1_result, agent2_result, market_data_text, bid, ask)
    
    return final_decision

# =============================================================================
# BREAK-EVEN LOGIC
# =============================================================================

def check_and_apply_breakeven(positions):
    """Check all positions and apply break-even if profit >= 50% of TP distance"""
    for p in positions:
        pos_type = p.get('type', '')
        pos_profit = p.get('profit', 0)
        pos_open = p.get('openPrice', 0)
        pos_sl = p.get('stopLoss', 0)
        pos_tp = p.get('takeProfit', 0)
        pos_id = p.get('id', '')
        
        if not (pos_open and pos_tp and pos_sl):
            continue
        
        if pos_type == 'POSITION_TYPE_BUY':
            tp_distance = pos_tp - pos_open
            current_sl_distance = pos_open - pos_sl
        else:
            tp_distance = pos_open - pos_tp
            current_sl_distance = pos_sl - pos_open
        
        if tp_distance > 0 and current_sl_distance > 0.01:
            half_tp = tp_distance * 0.5
            if pos_profit > 0 and pos_profit >= half_tp * 0.001 * 100:
                new_sl = pos_open
                log(f"[Break-Even] Position {pos_id}: Moving SL to {new_sl}")
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
                        log(f"[Break-Even] SUCCESS: SL moved to {new_sl}")
                    else:
                        log(f"[Break-Even] FAILED: {resp_mod.status_code}")
                except Exception as e:
                    log(f"[Break-Even] ERROR: {e}")

# =============================================================================
# MAIN TRADE CHECK LOGIC
# =============================================================================

def check_trade():
    """
    เช็คเทรด - วิเคราะห์ตลาดและให้คำแนะนำ
    กระบวนการ:
    1. ศึกษากระบวนการคำนวณ + ดูรายละเอียดกราฟ
    2. Dual Calculation (Mean-Reversion + Trend-Following)
    3. Agentic AI Parallel Processing (3 Agents)
    4. ตัดสินใจสุดท้ายโดย Coordinator Agent
    """
    global last_recommendation
    
    print_header("🔍 เช็คเทรด - Kanutsanan Pongpanna AI Auto Trading")
    print("  📊 Dual Calculation + Agentic AI Parallel Processing")
    print(f"  🤖 AI Model: {AI_MODEL}")
    print(f"  ⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    
    log("=" * 60)
    log("CHECK TRADE - Kanutsanan Pongpanna AI Auto Trading")
    log("=" * 60)
    
    # Validate credentials
    if not ACCOUNT_ID or not API_KEY or not OPENROUTER_API_KEY:
        print("  ❌ Missing API keys!")
        return {"status": "ERROR", "message": "Missing API keys"}
    
    # Check market
    if not check_market_open():
        print("  ⏸️  ตลาดปิด (วันหยุดสุดสัปดาห์)")
        return {"status": "SKIP", "message": "Market closed (Weekend)"}
    
    # Step 1: Account info
    print_section("Step 1: Account Info")
    try:
        resp_acc = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                               headers=headers, verify=False, timeout=15)
        if resp_acc.status_code != 200:
            print(f"  ❌ Account API error: {resp_acc.status_code}")
            if resp_acc.status_code == 504:
                print("  💡 Account อาจยังไม่เชื่อมต่อกับ broker")
            return {"status": "ERROR", "message": f"Account API error: {resp_acc.status_code}"}
        acc = resp_acc.json()
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        return {"status": "ERROR", "message": f"Connection failed: {e}"}
    
    balance = acc.get('balance', 0)
    equity = acc.get('equity', 0)
    free_margin = acc.get('freeMargin', 0)
    print(f"  💵 Balance: ${balance:.2f} | Equity: ${equity:.2f} | Free Margin: ${free_margin:.2f}")
    
    # Step 2: Check positions & Break-Even
    print_section("Step 2: Positions & Break-Even")
    positions = []
    try:
        resp_pos = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                               headers=headers, verify=False, timeout=10)
        positions = resp_pos.json() if resp_pos.status_code == 200 else []
        
        if positions:
            print(f"  📈 Open positions: {len(positions)}/{MAX_POSITIONS}")
            for p in positions:
                profit = p.get('profit', 0)
                emoji = "🟢" if profit >= 0 else "🔴"
                print(f"    {emoji} {p.get('symbol')} {p.get('type','')} Vol:{p.get('volume')} P/L:{profit}")
            
            check_and_apply_breakeven(positions)
            
            if len(positions) >= MAX_POSITIONS:
                print(f"  ⚠️  Max positions reached ({len(positions)}/{MAX_POSITIONS})")
                return {"status": "SKIP", "message": f"Max positions reached ({len(positions)}/{MAX_POSITIONS})"}
        else:
            print(f"  📭 No open positions (0/{MAX_POSITIONS})")
    except Exception as e:
        print(f"  ⚠️  Positions check error: {e}")
    
    # Step 3: Current price
    print_section("Step 3: Current Price")
    try:
        resp_price = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/symbols/XAUUSD.sml/current-price",
                                 headers=headers, verify=False, timeout=10)
        if resp_price.status_code != 200:
            print(f"  ❌ Price API error: {resp_price.status_code}")
            return {"status": "ERROR", "message": f"Price API error: {resp_price.status_code}"}
        
        price = resp_price.json()
        bid = price.get('bid', 0)
        ask = price.get('ask', 0)
        spread = round(ask - bid, 3)
        entry = (bid + ask) / 2
        print(f"  💰 Bid: {bid} | Ask: {ask} | Spread: {spread}")
        print(f"  🎯 Entry Price: {entry:.3f}")
        
        if spread <= 0 or bid <= 0:
            print("  ❌ Market closed or invalid price")
            return {"status": "SKIP", "message": "Market closed or invalid price"}
    except Exception as e:
        print(f"  ❌ Price fetch failed: {e}")
        return {"status": "ERROR", "message": f"Price fetch failed: {e}"}
    
    # Step 4: Get real-time chart data
    print_section("Step 4: Fetching Real-Time Chart Data (3 Sources)")
    market_data = None
    data_source = None
    
    market_data = get_candles_from_metaapi()
    if market_data:
        data_source = "MetaAPI"
    
    if not market_data:
        market_data = get_tradingview_scanner_data()
        if market_data:
            data_source = "TradingView Scanner"
    
    if not market_data:
        market_data = get_tradingview_web_data()
        if market_data:
            data_source = "TradingView Web"
    
    if not market_data:
        print("  ❌ All 3 data sources failed!")
        return {"status": "SKIP", "message": "NO REALTIME DATA: All 3 sources failed!"}
    
    print(f"  ✅ Data source: {data_source}")
    
    # Add trade history for context
    trade_history = get_trade_history()
    if trade_history:
        market_data += "\n" + trade_history
        print("  ✅ Trade history added for context")
    
    # Step 5: Agentic AI Parallel Processing
    print_section("Step 5: Agentic AI Parallel Processing (3 Agents)")
    print("  🤖 Agent 1: Mean-Reversion Analysis...")
    print("  🤖 Agent 2: Trend-Following Analysis...")
    print("  ⏳ กรุณารอสักครู่ (AI กำลังวิเคราะห์แบบขนาน)...")
    print()
    
    ai_decision = run_parallel_analysis(market_data, bid, ask)
    
    if not ai_decision:
        print("  ❌ AI analysis failed")
        return {"status": "SKIP", "message": "AI analysis failed (all agents)"}
    
    signal = ai_decision.get('action', 'SKIP')
    strength = ai_decision.get('strength', 0)
    tp_pts = ai_decision.get('tp_points', 5)
    sl_pts = ai_decision.get('sl_points', 100)
    chosen_set = ai_decision.get('chosen_set', 0)
    reason = ai_decision.get('reason', '')
    
    # Validate TP
    tp_pts = max(1, min(TP_MAX, int(tp_pts))) if isinstance(tp_pts, (int, float)) else TP_MAX
    
    print_section("Step 6: Final Decision")
    
    if signal == "SKIP" or signal is None:
        print(f"  ⏭️  AI says SKIP")
        print(f"  📝 Reason: {reason}")
        return {"status": "SKIP", "message": f"AI says SKIP - {reason}", "ai_decision": ai_decision}
    
    if strength < MIN_STRENGTH:
        print(f"  ⏭️  Weak signal ({strength}/10 < {MIN_STRENGTH})")
        print(f"  📝 Reason: {reason}")
        return {"status": "SKIP", "message": f"Very weak {signal} ({strength}/10) - {reason}", "ai_decision": ai_decision}
    
    # Calculate trade parameters
    if signal == "SELL":
        sl_price = round(entry + sl_pts, 3)
        tp_price = round(entry - tp_pts, 3)
        action_type = "ORDER_TYPE_SELL"
    else:
        sl_price = round(entry - sl_pts, 3)
        tp_price = round(entry + tp_pts, 3)
        action_type = "ORDER_TYPE_BUY"
    
    # Auto lot size
    leverage = 100
    max_margin_use = free_margin * (MAX_MARGIN_PERCENT / 100)
    raw_lot = max_margin_use / (entry / leverage * 1000)
    lot = max(MIN_LOT, round(int(raw_lot * 1000) * 0.001, 3))
    lot = min(lot, MAX_LOT)
    margin_needed = round(entry * lot / leverage, 2)
    
    if free_margin < margin_needed or lot < MIN_LOT:
        print(f"  ❌ Insufficient margin (need {margin_needed}, have {free_margin})")
        return {"status": "SKIP", "message": f"Insufficient margin"}
    
    # Build recommendation
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
    
    # Display recommendation
    print()
    print("  " + "=" * 50)
    print("  📊 TRADE RECOMMENDATION")
    print("  " + "=" * 50)
    signal_emoji = "📈" if signal == "BUY" else "📉"
    print(f"  {signal_emoji} Signal:      {signal}")
    print(f"  🎯 Entry:       {entry:.3f}")
    print(f"  🛑 Stop Loss:   {sl_price} ({sl_pts} pts)")
    print(f"  ✅ Take Profit: {tp_price} ({tp_pts} pts)")
    print(f"  📦 Lot Size:    {lot}")
    print(f"  💰 Margin:      ${margin_needed}")
    print(f"  💪 Strength:    {strength}/10")
    print(f"  🔢 Calc Set:    {chosen_set} ({'Mean-Reversion' if chosen_set == 1 else 'Trend-Following'})")
    print(f"  📡 Data Source: {data_source}")
    print(f"  📝 Reason:      {reason}")
    print("  " + "-" * 50)
    print(f"  💵 Balance: ${balance:.2f} | Equity: ${equity:.2f} | Free: ${free_margin:.2f}")
    print("  " + "=" * 50)
    print()
    print("  💡 คำสั่งถัดไป:")
    print("     python3 trade_check.py approve    (อนุมัติเทรดนี้)")
    print()
    
    return recommendation

# =============================================================================
# APPROVE TRADE
# =============================================================================

def approve_trade():
    """อนุมัติเทรด - ส่งคำสั่งซื้อขายตามคำแนะนำ"""
    global last_recommendation
    
    if not last_recommendation or last_recommendation.get('status') != 'READY':
        print_header("❌ ไม่มีคำแนะนำที่รอการอนุมัติ")
        print("  💡 กรุณารัน 'python3 trade_check.py' ก่อน")
        print()
        return {"status": "ERROR", "message": "No valid recommendation. Run check first."}
    
    rec = last_recommendation
    
    print_header("✅ อนุมัติเทรด - Kanutsanan Pongpanna AI Auto Trading")
    print(f"  📋 กำลังส่งคำสั่ง:")
    print(f"     Signal: {rec['signal']} | Lot: {rec['lot']} | Entry: {rec['entry']}")
    print(f"     SL: {rec['sl']} | TP: {rec['tp']}")
    print()
    
    log("=" * 60)
    log("APPROVE TRADE - Executing order...")
    log("=" * 60)
    
    trade_payload = {
        "actionType": rec['action_type'],
        "symbol": "XAUUSD.sml",
        "volume": rec['lot'],
        "stopLoss": rec['sl'],
        "takeProfit": rec['tp'],
        "comment": f"{TRADE_COMMENT} Set{rec.get('chosen_set',0)} Str{rec.get('strength',0)}"
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
            
            log(f"RESULT: {status} | Order: {order_id}")
            last_recommendation = None
            
            print("  " + "=" * 50)
            print("  ✅ TRADE EXECUTED SUCCESSFULLY!")
            print("  " + "=" * 50)
            print(f"  📋 Order ID: {order_id}")
            print(f"  📊 Status:   {status}")
            print(f"  📈 {rec['signal']} {rec['lot']}lot @{rec['entry']:.3f}")
            print(f"  🛑 SL: {rec['sl']} | ✅ TP: {rec['tp']}")
            print("  " + "=" * 50)
            print()
            
            return {
                "status": "TRADED",
                "message": f"{rec['signal']} {rec['lot']}lot @{rec['entry']:.3f} SL:{rec['sl']} TP:{rec['tp']}",
                "order_id": order_id,
                "string_code": status
            }
        else:
            log(f"FAILED: {resp_trade.status_code} - {resp_trade.text[:200]}")
            print(f"  ❌ Trade rejected: {resp_trade.status_code}")
            print(f"  📝 {resp_trade.text[:100]}")
            return {"status": "FAILED", "message": f"Trade rejected: {resp_trade.status_code}"}
    except Exception as e:
        log(f"[Trade] ERROR: {e}")
        print(f"  ❌ ERROR: {e}")
        return {"status": "FAILED", "message": f"Exception: {e}"}

# =============================================================================
# QUICK STATUS
# =============================================================================

def show_status():
    """Show quick system status"""
    print_header("⚡ สถานะระบบ - Kanutsanan Pongpanna AI Auto Trading")
    
    # Check timer
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', 'auto-trade.timer'], 
                              capture_output=True, text=True, timeout=5)
        timer_status = result.stdout.strip()
        timer_emoji = "🟢" if timer_status == "active" else "🔴"
        print(f"  {timer_emoji} Auto-Trade Timer: {timer_status}")
    except:
        print(f"  ⚪ Auto-Trade Timer: unknown")
    
    # Check API
    try:
        resp = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/account-information",
                           headers=headers, verify=False, timeout=10)
        if resp.status_code == 200:
            acc = resp.json()
            print(f"  🟢 MetaAPI: Connected")
            print(f"     Balance: ${acc.get('balance', 0):.2f} | Equity: ${acc.get('equity', 0):.2f}")
        else:
            print(f"  🔴 MetaAPI: Error {resp.status_code}")
    except:
        print(f"  🔴 MetaAPI: Timeout/Failed")
    
    # Check positions
    try:
        resp_pos = requests.get(f"{BASE_URL}/users/current/accounts/{ACCOUNT_ID}/positions",
                               headers=headers, verify=False, timeout=10)
        if resp_pos.status_code == 200:
            positions = resp_pos.json()
            if positions:
                total_pl = sum(p.get('profit', 0) for p in positions)
                pl_emoji = "🟢" if total_pl >= 0 else "🔴"
                print(f"  📈 Open Positions: {len(positions)}")
                print(f"  {pl_emoji} Total P/L: ${total_pl:.2f}")
            else:
                print(f"  📭 Open Positions: 0")
    except:
        pass
    
    # Check OpenRouter
    if OPENROUTER_API_KEY:
        print(f"  🟢 OpenRouter: Configured ({AI_MODEL})")
    else:
        print(f"  🔴 OpenRouter: Missing API Key!")
    
    # Last recommendation
    if last_recommendation:
        print(f"\n  📋 Pending Recommendation: {last_recommendation.get('signal')} (Set {last_recommendation.get('chosen_set')})")
    
    print()

# =============================================================================
# MAIN
# =============================================================================

def main():
    if len(sys.argv) < 2:
        # Default: check trade
        check_trade()
        return
    
    command = sys.argv[1].lower()
    
    if command in ['check', 'เช็คเทรด', 'เช็ค', 'c']:
        check_trade()
    
    elif command in ['approve', 'อนุมัติเทรด', 'อนุมัติ', 'a']:
        approve_trade()
    
    elif command in ['status', 'สถานะ', 's']:
        show_status()
    
    else:
        print("""
  Kanutsanan Pongpanna AI Auto Trading - Trade Check v3.0
  
  Usage: python3 trade_check.py [command]
  
  Commands:
    (none)             เช็คเทรด (default)
    check              เช็คเทรด - วิเคราะห์กราฟ + AI 3 ตัว
    approve            อนุมัติเทรดตามคำแนะนำ
    status             ดูสถานะระบบ + positions
    
  Examples:
    python3 trade_check.py              # เช็คเทรด
    python3 trade_check.py approve      # อนุมัติเทรด
    python3 trade_check.py status       # ดูสถานะ
        """)

if __name__ == "__main__":
    main()
