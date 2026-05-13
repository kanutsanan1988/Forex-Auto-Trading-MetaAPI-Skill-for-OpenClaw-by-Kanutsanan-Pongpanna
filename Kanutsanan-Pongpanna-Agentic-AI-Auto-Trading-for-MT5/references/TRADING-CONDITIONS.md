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

## 4. Timeframe Alignment

The system uses **M15 (15-minute) and H1 (5-minute)** timeframes for analysis. Both timeframes must show aligned signals before a trade is executed.

- M15 provides the primary trend direction.
- H1 provides precise entry timing confirmation.
- If M15 and H1 signals conflict, the system will **SKIP**.

## 5. Position Management
To prevent over-exposure, the system strictly limits the number of concurrent trades.
- **Max Open Positions:** 1
- If there is already an open position (regardless of whether it's in profit or loss), the system will **SKIP** the current cycle and wait for the position to close (via SL, TP, or manual intervention).

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

## 8. Price Validity
Before sending the order to the broker, the system checks the current Bid/Ask prices.
- **Valid Price:** Bid and Ask must be > 0.
- **Valid Spread:** The spread (Ask - Bid) must be > 0.
- If the price is invalid (e.g., market closed, broker disconnected), the system will **SKIP**.
