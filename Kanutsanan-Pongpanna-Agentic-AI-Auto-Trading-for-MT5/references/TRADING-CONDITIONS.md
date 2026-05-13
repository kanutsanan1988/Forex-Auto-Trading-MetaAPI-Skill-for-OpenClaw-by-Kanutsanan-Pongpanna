# Trading Conditions & Safety Rules

This document outlines the strict conditions and safety rules that the **Agentic AI Auto Trading System** follows before executing any trade. These rules are hardcoded into the system to protect your capital and ensure trades are only taken under optimal conditions.

## 1. Market Hours
The system will only trade during specific hours to avoid weekend gaps and low liquidity periods.
- **Trading Days:** Monday to Friday
- **Trading Hours:** 12:00 PM to 24:00 PM (UTC+7)
- **Weekend Rule:** The system will automatically **SKIP** all trades on Saturday and Sunday.
- **Execution Interval:** Every **5 minutes** via systemd timer (auto-start on boot)

## 2. Data Availability (The "No Data = No Trade" Rule)
The system relies on real-time data to make informed decisions. It uses a 3-tier fallback system to fetch data:
1. **MetaAPI Candles:** M15 and H1 timeframes directly from the broker.
2. **TradingView Scanner API:** Technical indicators and recommendations for M15 and H1.
3. **TradingView Web:** Fallback scraping of TradingView's web interface.

**CRITICAL RULE:** If the system fails to fetch data from **ALL 3 sources**, it will abort the trading cycle and log a `NO_REALTIME_DATA` error. It will **never** trade blind.

## 3. AI Confidence Threshold
The OpenRouter AI (Gemini 3.1 Flash Lite) analyzes the market data and returns a decision (BUY/SELL/SKIP) along with a "Strength" score from 1 to 10.
- **Minimum Strength:** The AI's strength score must be **>= 6/10**.
- If the score is 5 or below, the system will **SKIP** the trade, even if the AI suggests a BUY or SELL.

## 4. Timeframe Alignment (H1 Directional Filter)

The system uses **M15 (15-minute)** as the primary decision timeframe and **H1 (1-hour)** as a directional filter.

- **H1 Bullish** → only allow BUY (no SELL)
- **H1 Bearish** → only allow SELL (no BUY)
- **H1 Neutral/Ranging** → allow both BUY and SELL based on M15
- M15 provides the primary entry timing and signal.

## 5. Position Management
To prevent over-exposure, the system strictly limits the number of concurrent trades.
- **Max Open Positions:** 5
- The system can hold up to 5 positions simultaneously. If 5 positions are already open, the system will **SKIP** the current cycle.
- Every cycle, the system checks all open positions for Break-Even opportunities, regardless of whether a new trade is opened.

## 6. Smart Lot Sizing & Margin Checks
The system dynamically calculates the lot size based on your available free margin, ensuring you never over-leverage.
- **Max Margin Usage:** 50% of Free Margin.
- **Minimum Lot Size:** 0.001
- **Maximum Lot Size:** 0.1
- **Margin Check:** Before executing, the system verifies that the calculated lot size requires less margin than what is currently available. If insufficient, it will **SKIP**.

## 7. Risk Management (SL/TP)
The AI is responsible for suggesting Stop Loss (SL) and Take Profit (TP) levels based on market volatility (ATR).
- **SL Calculation:** Approximately 20% of the M15 ATR.
- **TP <= SL Enforcement:** TP cannot exceed SL (minimum 1:1 risk-to-reward ratio).
- **TP Tiered Cap (applied after TP <= SL):**
  - If TP > 10 pts → TP is set to 5 pts
  - If TP > 5 pts (but ≤ 10) → TP is set to 2.5 pts
  - If TP > 2.5 pts (but ≤ 5) → TP is set to 1 pt
  - If TP ≤ 2.5 pts → TP remains unchanged

## 8. Late Entry Prevention (Anti-Reversal Trap)

The system includes 4 critical checks to prevent entering trades near reversal points ("Late Entry" problem):

### 8.1 RSI Extreme Filter
- If RSI > 70 → **DO NOT BUY** (overbought, price likely to reverse down)
- If RSI < 30 → **DO NOT SELL** (oversold, price likely to reverse up)
- RSI between 40-60 is ideal for trend-following entries

### 8.2 Divergence Check
- **Bearish Divergence:** Price makes higher high but RSI/MACD makes lower high → DO NOT BUY
- **Bullish Divergence:** Price makes lower low but RSI/MACD makes higher low → DO NOT SELL
- If divergence detected, either SKIP or consider Reversal trade

### 8.3 Reversal Strategy
When strong reversal signals are present, the system can trade AGAINST the exhausted trend:
- Requires at least 2 of: RSI divergence, reversal candle pattern (hammer, shooting star, engulfing), key level rejection
- Reversal trades use tighter SL (closer to reversal point)

### 8.4 Pullback Entry (Preferred Method)
- DO NOT enter when price has moved far from EMA20/EMA50
- If price is more than 1.5x ATR away from EMA20 → **SKIP** (too extended)
- Ideal entry: price pulls back to EMA20/EMA50, then shows continuation signal

### Entry Priority
1. **Pullback to EMA + trend continuation** (BEST - lowest risk)
2. **Reversal at extreme with multiple confirmations** (GOOD)
3. **Breakout with follow-through** (OK - verify not false breakout)
4. **Chasing extended move** (NEVER - causes Late Entry losses)

## 9. Break-Even Logic
When an open position reaches profit >= 50% of the TP distance, the system automatically moves the SL to the entry price (break-even). This protects profitable trades from turning into losses.

## 10. Price Validity
Before sending the order to the broker, the system checks the current Bid/Ask prices.
- **Valid Price:** Bid and Ask must be > 0.
- **Valid Spread:** The spread (Ask - Bid) must be > 0.
- If the price is invalid (e.g., market closed, broker disconnected), the system will **SKIP**.
