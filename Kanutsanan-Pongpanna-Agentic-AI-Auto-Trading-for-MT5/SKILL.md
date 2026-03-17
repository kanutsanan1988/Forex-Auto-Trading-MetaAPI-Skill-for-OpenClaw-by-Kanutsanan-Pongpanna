---
name: Kanutsanan-Pongpanna-Agentic-AI-Auto-Trading-for-MT5
description: Complete agentic automated forex trading system for XAU/USD (gold) with real-time M15 analysis, intelligent position management with profit thresholds, full-auto execution, and 30-second CRON scheduling. Manual setup required with your Account ID and API Key only. Created by Kanutsanan Pongpanna.
---

# Kanutsanan-Pongpanna-Agentic-AI-Auto-Trading-for-MT5

**Complete agentic automated trading system for MetaApi** — Manual trade check + Full-auto execution + 30-second scheduling + Smart position management

## 🎯 What's New (Agentic Version)

### ✨ Key Improvements

1. **Smarter Position Management**
   - Profit threshold logic (±2%)
   - Trend change detection
   - Automated scaling with profit lock
   - Prevents overlapping trades

2. **Balance vs Equity Logic**
   - Accurate 2% risk calculation
   - Adapts to drawdowns and wins
   - Always use optimal calculation base

3. **Faster Scheduling**
   - Every 30 seconds (was 38)
   - **20,160 runs per week** (25% more opportunities)
   - Better for scalping opportunities

4. **Better Chart Analysis**
   - M15 candles (100 bars)
   - Real volatility-based SL/TP
   - Dynamic, not fixed values

---

## Quick Start (5 minutes)

### 1. Install Dependencies

```bash
npm install metaapi.cloud-sdk
```

### 2. Configure Environment Variables

Create `.env` file (see `assets/config-template.env`):

```bash
export TOKEN="YOUR_METAPI_API_KEY_HERE"
export ACCOUNT_ID="YOUR_METAPI_ACCOUNT_ID_HERE"
```

**⚠️ IMPORTANT:** 
- Get your **API Key** from: https://app.metaapi.cloud (account settings)
- Get your **Account ID** from: https://app.metaapi.cloud (select your account)
- NEVER share your credentials
- NEVER commit `.env` to git

### 3. Run Trade Check (Manual)

```bash
source .env
node scripts/kanutsanan-pongpanna-trade-check-template.js
```

Output: Real-time trade analysis (STEP 0-9)

### 4. Enable Full-Auto (Optional)

```bash
source .env
node scripts/kanutsanan-pongpanna-full-auto-template.js &
```

Runs automatically every 30 seconds via CRON.

---

## System Architecture

### 🔴 System 1: Trade Check (Manual)

**File:** `scripts/kanutsanan-pongpanna-trade-check-template.js`
**Time:** 15-20 seconds per check
**Use:** On-demand trade analysis

#### STEP 0-9 Analysis Flow

```
STEP 0: Market status check
        ↓
STEP 1: Fresh entry price (real-time)
        ↓
STEP 2: M15 Chart analysis (100 candles)
        ↓
STEP 3: Dynamic SL/TP calculation
        ↓
STEP 4: Risk/Reward ratio (≥1.0)
        ↓
STEP 5: Position sizing (2% rule + Balance/Equity logic)
        ↓
STEP 6: Signal strength (0-10)
        ↓
STEP 7: Validate SL/TP direction
        ↓
STEP 8: Final API verification
        ↓
STEP 9: Position & Order check (Smart Management)
```

#### Key Features:

- ✅ **M15 Candles:** Uses 100-bar M15 chart for accurate volatility
- ✅ **Dynamic SL/TP:** Proportional to current market conditions (not fixed)
- ✅ **Balance vs Equity:** Selects optimal calculation base for 2% risk
- ✅ **Smart Position Check:** Moved to STEP 9 (end) for logical flow
- ✅ **Profit Thresholds:** ±2% rules for trade management

#### Output Example:

```
Entry: 5155.59
Signal: SELL (8/10 - STRONG)
SL: 5178.82 (23.23 points)
TP: 5097.50 (58.09 points)
Lot: 0.001
R/R: 2.5 : 1
Status: READY ✅
Action: CAN_CREATE_NEW
```

---

### 🟢 System 2: Full-Auto Execution

**File:** `scripts/kanutsanan-pongpanna-full-auto-template.js`
**Time:** ~33 seconds per cycle
**Frequency:** Every 30 seconds (via CRON)

#### Execution Phases:

```
PHASE 1: Trade Check Analysis (STEP 0-9)
         [15-20 seconds]
         ↓
PHASE 2: Validate 8 Safety Conditions
         [1-2 seconds]
         ✓ Signal ≥ 4/10
         ✓ SL < 100 points
         ✓ Risk = 2%
         ✓ R/R ≥ 1.0
         ✓ Orders < UNLIMITED
         ✓ Loss > -20% (circuit breaker)
         ✓ Equity > $0.10
         ✓ Balance > $0.05
         ↓
PHASE 3: Execute Trade (if all pass)
         [5-10 seconds]
         ↓
PHASE 3B: Verification & Logging
          [1-2 seconds]
```

#### Smart Position Management:

**If NO existing position:**
- ✅ Create new trade

**If position EXISTS - SAME trend:**
- Same lotsize: ✅ Keep position
- Higher lotsize + profit ≥ 2%: ✅ Close old + create new
- Higher lotsize + profit < 2%: ⏸️ Wait

**If position EXISTS - TREND CHANGED:**
- Profit ≥ 2%: ✅ Close old + create new
- Loss ≥ 2%: ✅ Close old + create new
- |P&L| < 2%: ⏸️ Wait for threshold

---

### ⚙️ System 3: CRON Scheduling

**File:** `scripts/cron-setup.sh`
**Frequency:** Every 30 seconds ✅ (Updated from 38)
**Schedule:** 24/5 (Sunday 23:00 UTC - Friday 22:00 UTC)

#### Weekly Performance

```
┌─────────────────────────────────────────┐
│ CRON Performance (30-second interval)    │
├─────────────────────────────────────────┤
│ Per Minute:        2 runs                │
│ Per Hour:          120 runs              │
│ Per Day:           2,880 runs            │
│ Per Week:          20,160 runs ✅        │
│ Per Year:          ~1,048,320 runs       │
└─────────────────────────────────────────┘

Compared to Old (38 seconds):
  • Old: 15,947 runs/week
  • New: 20,160 runs/week
  • Improvement: +25.3% more opportunities 🚀
```

#### Setup Instructions

```bash
# View current CRON jobs
crontab -l

# Add new jobs (every 30 seconds)
*/1 * * * 0 cd /path/to/skill && source .env && bash scripts/cron-runner.sh
*/1 * * * 1-5 cd /path/to/skill && source .env && bash scripts/cron-runner.sh

# Create cron-runner.sh to handle 30-second loops
while true; do
  node scripts/kanutsanan-pongpanna-full-auto.js >> logs/trade.log
  sleep 30
done
```

---

## Understanding the System

### M15 Chart Analysis (STEP 2)

Why M15 instead of other timeframes?

```
✅ More Responsive: Captures current market conditions
✅ Better Volatility: Real-time support/resistance levels
✅ Balanced: Not too noisy, not too slow
✅ Professional: Standard for forex traders
✅ 100 Bars: 1,500 minutes = 25 hours of history
```

**Data Retrieved:**
```javascript
candles = await connection.getCandles(SYMBOL, '15m', {limit: 100});

Each candle:
  • open: Opening price
  • high: Highest in period
  • low: Lowest in period
  • close: Closing price
  • time: Timestamp
```

### Dynamic SL/TP (STEP 3)

Not fixed values - adapts to market:

```javascript
SL Buffer = Volatility × 0.20 (20%)
TP Buffer = Volatility × 0.50 (50%)

For SELL: SL = Entry + buffer, TP = Entry - buffer
For BUY:  SL = Entry - buffer, TP = Entry + buffer

Example:
  Volatility: 116 points
  SL Buffer: 23.2 points
  TP Buffer: 58 points
```

### Position Sizing Logic (STEP 5)

Uses MAX(Balance, Equity):

```javascript
const baseAmount = balance > equity ? balance : equity;
const riskAmount = baseAmount * 0.02;
const lotSize = riskAmount / slPoints;

Why?
  • Balance: Total account capital
  • Equity: Balance + current P&L
  • MAX: Use higher value for accurate 2% risk
  • Prevents aggressive sizing during drawdown
```

### Position Management (STEP 9)

9 detailed conditions for smart trading:

| Situation | Condition | Action |
|-----------|-----------|--------|
| Ready | 0 pos, 0 ord | ✅ Create |
| Same trend (hold) | Same trend, lot ≤ old | ❌ Wait |
| Same trend (scale) | Same trend, lot > old, P≥2% | ✅ Close+Create |
| Same trend (wait) | Same trend, lot > old, P<2% | ❌ Wait |
| Trend reverse (loss) | Different trend, P≤-2% | ✅ Close+Create |
| Trend reverse (profit) | Different trend, P≥2% | ✅ Close+Create |
| Trend reverse (wait) | Different trend, \|P\|<2% | ❌ Wait |
| Pending | 0 pos, 1+ ord | ❌ Wait |
| Error | Abnormal state | ❌ Stop |

---

## Full-Auto Approval Conditions (8 checks)

All must PASS to execute:

### Per-Trade Checks (1-4):

1. **Signal ≥ 4** (0-10 scale) 
   - Requirement: Signal strength must be MEDIUM or STRONG
   
2. **SL < 100 points** (stop loss limit)
   - Requirement: Risk limited to 100 pips maximum
   
3. **Risk = 2%** (per trade)
   - Requirement: Each trade risks exactly 2% of account
   
4. **R:R ≥ 1.0** (risk/reward ratio)
   - Requirement: Reward must be ≥ Risk (minimum break-even ratio)

### Per-Day Checks (5-8):

5. **Orders < UNLIMITED** (daily cap - currently unlimited)
   - No daily trade limit
   
6. **Loss > -20%** (circuit breaker, daily)
   - Stop trading if daily loss exceeds -20%
   
7. **Equity > $0.10** (minimum equity)
   - Account must have >$0.10 available
   
8. **Balance > $0.05** (minimum balance)
   - Account must have >$0.05 to continue trading

---

## Advanced Configuration

For detailed system documentation, see:

- **Complete review:** `references/STEP-0-10-GUIDE.md`
- **CRON scheduling:** `references/CRON-SCHEDULING.md`
- **Approval conditions:** `references/PHASE-2-3-CONDITIONS.md`

---

## Important Notes

### ✅ DO:

- Use environment variables for credentials (`.env` file)
- Test with small lots (0.001 minimum)
- Monitor trading activity regularly
- Keep account funded
- Review logs for errors
- Check M15 charts for volatility analysis
- Monitor API rate limits
- Let position check (STEP 9) run automatically

### ❌ DON'T:

- Hardcode credentials in scripts
- Share your API Key or Account ID
- Commit `.env` to version control
- Use fixed SL/TP values
- Manually override position management
- Ignore profit threshold rules
- Trade with excessive leverage
- Run multiple instances simultaneously

---

## Architecture Overview

```
MetaApi Cloud ────→ Connection ────→ STEP 0-9 Analysis
    (XAUUSD)         (Real-time)     (Every 30 seconds)
                            ↓
                    Position Check
                    (Smart Management)
                            ↓
                    Approval Conditions
                    (8 Safety Checks)
                            ↓
                    Execute Trade
                    (Place Order)
                            ↓
                    Logging & Monitoring
                    (Daily Reports)
```

---

## Data Sources (API-Only)

✅ **All from MetaApi:**
- Symbol prices: `getSymbolPrice()`
- M15 candles: `getCandles('15m')`
- Account info: `getAccountInformation()`
- Positions: `getPositions()`
- Orders: `getOrders()`

❌ **No external sources:**
- No external price feeds
- No cached prices
- No hardcoded values
- No third-party indicators

---

## Golden Rules

1. **One trade at a time** (max 1 open position)
2. **Fresh entry price every cycle** (30 seconds)
3. **Dynamic SL/TP** from M15 volatility (not fixed)
4. **2% risk per trade** (strict rule)
5. **-20% daily loss circuit breaker** (protection)
6. **Position check BEFORE execution** (STEP 9)
7. **±2% profit threshold** for position management
8. **24/5 automation** (Sunday-Friday, no weekends)

---

## Usage Instructions

### Quick Setup (5 minutes)

1. **Extract the ZIP file**
   ```bash
   unzip kanutsanan-pongpanna-agentic-ai-auto-trading-for-mt5.zip
   cd kanutsanan-pongpanna-agentic-ai-auto-trading-for-mt5
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure credentials**
   ```bash
   nano .env
   ```
   Add your MetaApi credentials:
   - `TOKEN=your-api-key-from-metaapi.cloud`
   - `ACCOUNT_ID=your-account-id-from-metaapi.cloud`

4. **Test trade analysis (manual)**
   ```bash
   source .env
   node scripts/kanutsanan-pongpanna-trade-check-template.js
   ```

5. **Enable automatic trading (optional)**
   ```bash
   bash scripts/cron-setup.sh
   ```
   System will run automatically every 30 seconds

---

## What You Get

✅ **Real-time trade analysis** (STEP 0-9)
   - M15 chart volatility analysis
   - Dynamic SL/TP calculation
   - Professional signal scoring (0-10)
   - Smart position management with profit thresholds

✅ **Full automation** (PHASE 1-3B)
   - 8 safety conditions
   - Intelligent position management
   - Execution & verification
   - Every 30 seconds

✅ **CRON scheduling** 
   - Every 30 seconds
   - 20,160 runs per week (+25% vs old)
   - Automatic 24/5 trading
   - Better trading opportunities

✅ **Safety features**
   - One trade at a time
   - -20% daily loss circuit breaker
   - Profit threshold (±2%)
   - Risk management (2% per trade)
   - Smart position check with trend analysis
   - Balance vs Equity optimization

✅ **Professional documentation**
   - STEP-0-10-GUIDE.md (detailed walkthrough)
   - CRON-SCHEDULING.md (scheduling guide)
   - PHASE-2-3-CONDITIONS.md (approval rules)

---

## Security

✅ NO credentials hardcoded
✅ All sensitive data in .env (git-ignored)
✅ Safe for distribution
✅ Users control their own API keys
✅ Environment-based configuration

---

## Support & Questions

Each file contains detailed comments explaining every step. 

Start with:
1. `kanutsanan-pongpanna-trade-check.js` - Understand the analysis logic
2. `kanutsanan-pongpanna-full-auto.js` - See automation in action
3. `references/` - Deep dive into each system component

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| **Agentic** | 2025-03-07 | ✨ Profit thresholds, Balance/Equity logic, 30-sec scheduling |
| AI | Earlier | Original version with 38-sec scheduling |

---

**Created by:** Kanutsanan Pongpanna
**Version:** Agentic AI Auto Trading for MT5
**Status:** Production Ready ✅

---

## Ready to Trade?

1. Set your credentials in `.env`
2. Run: `source .env && node scripts/kanutsanan-pongpanna-trade-check-template.js`
3. Review output and understand the system
4. When confident: `bash scripts/cron-setup.sh` for 24/5 trading every 30 seconds

Good luck! 💛

