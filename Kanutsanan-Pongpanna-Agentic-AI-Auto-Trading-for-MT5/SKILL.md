---
name: Kanutsanan-Pongpanna-Agentic-AI-Auto-Trading-for-MT5
description: Complete agentic automated forex trading system for XAU/USD (gold) powered by OpenRouter AI (Gemini 2.5 Flash) and MetaAPI REST API. Features 3 data sources fallback, smart lot sizing, and full-auto execution via systemd timer. Created by Kanutsanan Pongpanna.
---

# Kanutsanan-Pongpanna-Agentic-AI-Auto-Trading-for-MT5

**Complete agentic automated trading system for MetaApi** — Python + OpenRouter AI + MetaAPI REST API + TradingView data sources.

## 🎯 What's New (Python + OpenRouter AI Version)

### ✨ Key Improvements
1. **AI-Powered Decision Making**
   - Uses OpenRouter API (model: `google/gemini-2.5-flash`) as the primary processor.
   - AI analyzes market data, calculates indicators, decides BUY/SELL/SKIP, and sets SL/TP.
   - AI Strength threshold: >= 6/10 to trade.
2. **Robust Data Sources (3 Fallbacks)**
   - MetaAPI candles (M15 + H1)
   - TradingView Scanner API
   - TradingView Web
   - **CRITICAL RULE:** If real-time chart data cannot be fetched from all sources, the system will NOT trade.
3. **Smart Lot Sizing**
   - Automatically calculated from free margin (max 50% usage).
   - Minimum lot: 0.001, Maximum lot: 0.1.
4. **Cloud Computer Standalone Support**
   - 💡 **PRO TIP TO SAVE CREDITS:** Users can purchase a Cloud Computer from Manus and have the Manus AI Agent write the entire system script to run independently on the Cloud Computer. This allows users to use API Keys from other, more cost-effective AI providers or from OpenRouter, giving you more choices and saving credits!
5. **Systemd Timer Scheduling**
   - Runs every 10 minutes automatically.
   - Trading hours: Monday 12:00 PM - Friday 24:00 PM (UTC+7).

---

## Quick Start (5 minutes)

### 1. Configure Environment Variables
Create `.env` file (see `assets/config-template.env`):
```bash
export METAAPI_TOKEN="YOUR_METAAPI_TOKEN_HERE"
export METAAPI_ACCOUNT_ID="YOUR_METAAPI_ACCOUNT_ID_HERE"
export OPENROUTER_API_KEY="YOUR_OPENROUTER_API_KEY_HERE"
```

**⚠️ IMPORTANT:** 
- Get your **MetaAPI Token** and **Account ID** from: https://app.metaapi.cloud
- Get your **OpenRouter API Key** from: https://openrouter.ai
- NEVER share your credentials
- NEVER commit `.env` to git

### 2. Setup and Run
```bash
# Run the setup script to install dependencies and configure cron/systemd
sudo bash scripts/setup.sh

# To check logs
python3 scripts/trade_log.py
```

---

## 🔍 Manual Trade Check (New Feature)

You can now run a manual check to see what the AI would do **without actually executing a trade**. This is useful for testing the AI's logic, checking current market conditions, and verifying your API keys.

```bash
# Run the manual trade check
python3 scripts/trade_check.py
```

The script will output the AI's analysis, including:
- Current Balance, Equity, and Free Margin
- Real-time price and spread
- AI Decision (BUY/SELL/SKIP)
- Signal Strength (1-10)
- Suggested Stop Loss (SL) and Take Profit (TP)
- The reason for the decision

---

## 🛡️ Approval & Safety Conditions

Before any trade is executed, the system strictly checks the following conditions:

1. **Market Hours:** Must be Monday 12:00 PM to Friday 24:00 PM (UTC+7).
2. **Data Availability:** Real-time chart data MUST be successfully fetched from at least one of the 3 sources (MetaAPI, TV Scanner, TV Web). **No data = No trade.**
3. **AI Strength:** The AI's confidence score must be **>= 6/10**.
4. **Margin Check:** The calculated lot size must require less than 50% of the available free margin.
5. **Valid Price:** Bid and Ask prices must be > 0, and spread must be > 0.

---

## 📊 Position Management Rules

- **Maximum Open Positions:** The system allows a maximum of **1 open position** at any given time.
- **Existing Positions:** If a position is already open, the system will **SKIP** trading until the current position is closed (either by hitting SL/TP or manual closure).
- **Risk/Reward:** The AI is instructed to ensure that Take Profit (TP) is never greater than Stop Loss (SL) in terms of points, enforcing a minimum 1:1 risk-to-reward ratio.

---

## 🏗️ Architecture Overview

### 🔴 System 1: Data Fetching & Analysis
**Time:** Every 10 minutes (via systemd timer)
**Flow:**
1. Check Market Open (Mon-Fri)
2. Fetch Account Info (Balance, Equity, Free Margin)
3. Check Existing Positions (Max 1 open position)
4. Fetch Current Price (Bid/Ask/Spread)
5. Fetch Real-time Chart Data (MetaAPI -> TV Scanner -> TV Web)
6. Send data to OpenRouter AI for analysis

### 🟢 System 2: AI Decision & Execution
**Flow:**
1. AI returns JSON decision (Action, Strength, SL, TP, Reason)
2. Validate Strength (>= 6/10)
3. Calculate Lot Size based on Free Margin
4. Execute Trade via MetaAPI REST API
5. Log results to `/var/log/auto_trade.log`

---

## Important Notes

### ✅ DO:
- Use environment variables for credentials (`.env` file)
- Monitor trading activity regularly via `trade_log.py`
- Keep account funded
- Review logs for errors

### ❌ DON'T:
- Hardcode credentials in scripts
- Share your API Keys or Account ID
- Commit `.env` to version control
- Run multiple instances simultaneously

---

## Support & Questions
Each file contains detailed comments explaining every step. 
Start with:
1. `scripts/auto_trade.py` - Main trading logic and AI integration
2. `scripts/trade_check.py` - Manual check without trading
3. `scripts/setup.sh` - Environment setup and scheduling
4. `scripts/trade_log.py` - Log viewer and summarizer

---

## Version History
| Version | Date | Changes |
|---------|------|---------|
| **3.0.0** | 2026-05-12 | ✨ Python rewrite, OpenRouter AI integration, 3 data sources, Cloud Computer support, Manual Trade Check |
| **2.0.0** | 2025-03-07 | ✨ Profit thresholds, Balance/Equity logic, 30-sec scheduling (Node.js) |

---
**Created by:** Kanutsanan Pongpanna
**Version:** Agentic AI Auto Trading for MT5 (Python + OpenRouter)
**Status:** Production Ready ✅
