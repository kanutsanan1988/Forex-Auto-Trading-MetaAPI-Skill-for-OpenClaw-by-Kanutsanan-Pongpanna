# STEP 0-9 Complete Guide (UPDATED - AGENTIC VERSION)

Trade analysis workflow with detailed explanations of each step - including M15 chart analysis, Balance vs Equity logic, and comprehensive position management.

## 📋 STEP ORDERING (FINAL)

The 9 steps have been reordered to improve logic flow (Position & Order check moved to END):

0. Market status
1. Fresh entry price
2. **M15 Chart analysis** (using M15 candles)
3. Dynamic SL/TP
4. Risk/Reward ratio
5. Position sizing (with Balance/Equity comparison)
6. Signal strength
7. SL/TP validation
8. Final API verification
9. **Position & Order check** (MOVED TO END)

---

## STEP 0: Market Status Check

**Purpose:** Verify market is open and API is responsive

**API Call:** `getSymbolPrice(SYMBOL)`

**What it does:**
- Fetches current bid/ask prices from broker
- Confirms market is trading
- Gets real-time data

**Example output:**
```
Bid: 5155.23
Ask: 5155.95
✅ Market is OPEN
```

---

## STEP 1: Fresh Entry Price

**Purpose:** Get the exact entry price to use for calculations

**Calculation:** `(bid + ask) / 2` = mid-price

**Important:**
- Fresh every cycle (not cached)
- Real-time from API
- Mid-point between bid/ask

**Example:**
```
Bid: 5155.23
Ask: 5155.95
Entry: 5155.59
```

---

## STEP 2: Chart Analysis (M15 CANDLES)

**Purpose:** Analyze M15 candles to understand volatility and trend

**API Call:** `getCandles(SYMBOL, '15m', {limit: 100})`

**What it calculates:**
- Support (lowest in M15 candles)
- Resistance (highest in M15 candles)
- Volatility = Resistance - Support
- Trend = which side of midpoint

**Why M15?**
- ✅ **More Responsive:** Captures current market conditions
- ✅ **Better Volatility:** Real-time support/resistance
- ✅ **Balanced:** Medium timeframe (1,500 mins = 25 hours of history with 100 bars)
- ✅ **Professional:** Standard for entry precision
- ✅ **100 Bars:** Provides sufficient historical context

**Candle Data Structure:**
```javascript
candles = await connection.getCandles(SYMBOL, '15m', {limit: 100});

Each candle contains:
- open: Opening price
- high: Highest price in the 15-minute period
- low: Lowest price in the 15-minute period
- close: Closing price
- time: Candle timestamp
```

**Example:**
```
M15 Candles: 100 bars analyzed
Support: 5039.78 (lowest high/low from all M15 candles)
Resistance: 5155.95 (highest high/low from all M15 candles)
Volatility: 116.17 points
Midpoint: 5097.86

Entry: 5155.59 (above midpoint)
Trend: UP 🟢
```

---

## STEP 3: Dynamic SL & TP Calculation

**Purpose:** Set stop loss and take profit dynamically based on volatility

**Formulas:**
```
SL Buffer = Volatility × 0.20 (20%)
TP Buffer = Volatility × 0.50 (50%)
```

**For SELL signal (Trend DOWN):**
```
SL = Entry + SL Buffer (above entry)
TP = Entry - TP Buffer (below entry)
```

**For BUY signal (Trend UP):**
```
SL = Entry - SL Buffer (below entry)
TP = Entry + TP Buffer (above entry)
```

**Why Dynamic?**
- Proportional to current market volatility
- Not fixed arbitrary values
- Adapts to market conditions automatically

**Example (SELL scenario):**
```
Entry: 5155.59
Volatility: 116.17 points

SL Buffer = 116.17 × 0.20 = 23.23 points
TP Buffer = 116.17 × 0.50 = 58.09 points

For SELL:
  SL = 5155.59 + 23.23 = 5178.82 ✅
  TP = 5155.59 - 58.09 = 5097.50 ✅

Result: SELL with 23.23 pts risk, 58.09 pts reward
```

---

## STEP 4: Risk/Reward Ratio

**Purpose:** Ensure trade has good reward relative to risk

**Calculation:**
```
Risk = |Entry - SL|
Reward = |TP - Entry|
R/R Ratio = Reward / Risk

Requirement: R/R >= 1.0 (reward must be >= risk)
```

**Example:**
```
Entry: 5155.59
SL: 5178.82
TP: 5097.50

Risk: 23.23 points
Reward: 58.09 points
R/R Ratio = 58.09 / 23.23 = 2.5 : 1 ✅

Interpretation: For every 1 point you risk, 
you can gain 2.5 points (EXCELLENT)
```

---

## STEP 5: Position Sizing (2% Risk Rule + Balance/Equity Logic)

**Purpose:** Calculate correct lot size for 2% risk per trade with Balance/Equity comparison

### 5.1: Balance vs Equity Selection

**Logic:**
```javascript
const balance = accountInfo.balance;      // Total account value
const equity = accountInfo.equity;        // Current account value with open P&L

// NEW: Use Balance if higher, else use Equity
const baseAmount = balance > equity ? balance : equity;
const riskAmount = baseAmount * 0.02;
```

**Why this matters?**
- When you have a LOSING position: Equity < Balance
- When you have a WINNING position: Equity > Balance
- **Always use the HIGHER value** to ensure 2% risk calculation is accurate
- This prevents aggressive lot sizing during drawdown

**Example 1: After losing trade**
```
Balance: $1,000 (your actual capital)
Equity: $950 (with -$50 loss)
Selected: $1,000 ✅ (higher value)
Risk: $1,000 × 2% = $20
```

**Example 2: After winning trade**
```
Balance: $1,000
Equity: $1,050 (with +$50 profit)
Selected: $1,050 ✅ (higher value)
Risk: $1,050 × 2% = $21
```

### 5.2: Lot Size Calculation

**Formula:**
```
Selected Amount = MAX(Balance, Equity)
Risk Amount = Selected Amount × 2%
Lot Size = Risk Amount / SL Points

Round DOWN to valid broker lot size
Minimum: 0.001 lot
```

**Complete Example:**
```
Balance: $0.28
Equity: $0.27 (has small loss)
Selected: $0.28 (higher) ✅

Risk Percentage: 2%
Risk Amount: $0.28 × 0.02 = $0.0056

SL Points (from STEP 3): 23.23
Calculated Lot: $0.0056 / 23.23 = 0.000241

Valid Lot Options: [0.001, 0.01, 0.02, ...]
Selected Lot: 0.001 (round down to minimum) ✅
```

---

## STEP 6: Signal Strength (0-10 Scale)

**Purpose:** Score the quality of the trade signal

**Scoring System:**
```
Base Score: 4 points
+ 2 if R/R >= 1.5 (excellent reward ratio)
+ 1 if Volatility > 50 points (moderate volatility)
+ 1 if Volatility > 100 points (high volatility)

Total: 0-10 points (capped at 10)
```

**Interpretation Guide:**
```
0-3: WEAK       (Skip this trade - too risky)
4-5: MEDIUM     (Trade with caution)
6-10: STRONG    (Good quality signal)
```

**Example:**
```
Base: 4 points

Check conditions:
  ✓ R/R ratio is 2.5 >= 1.5 → Add 2 points
  ✓ Volatility is 116 > 50 → Add 1 point
  ✓ Volatility is 116 > 100 → Add 1 point

Total Score: 4 + 2 + 1 + 1 = 8/10 = STRONG ✅

Decision: This is a HIGH QUALITY signal, proceed with trade
```

---

## STEP 7: Validate SL/TP Direction

**Purpose:** Ensure stop loss and take profit are on correct sides

**For BUY signals:**
```
Requirement: SL < Entry < TP
(Stop loss below entry, take profit above)

Example:
  SL: 5155.00  ← Below
  Entry: 5155.59  ← Middle
  TP: 5156.00  ← Above
  ✅ VALID
```

**For SELL signals:**
```
Requirement: TP < Entry < SL
(Take profit below entry, stop loss above)

Example:
  TP: 5154.00  ← Below
  Entry: 5155.59  ← Middle
  SL: 5156.00  ← Above
  ✅ VALID
```

---

## STEP 8: Final API Verification

**Purpose:** Confirm all data came from MetaApi, no external sources

**Verification Checklist:**
```
✅ Entry price: from getSymbolPrice()
✅ M15 Volatility: from getCandles('15m')
✅ Account info: from getAccountInformation()
✅ Position data: from getPositions()
✅ Order data: from getOrders()

✅ NO external API calls
✅ NO cached prices
✅ NO hardcoded values
```

---

## STEP 9: Position & Order Check (MOVED TO END)

**Purpose:** Smart management of existing orders/positions with 2% profit threshold

### 9.1: No Old Position/Order (READY STATE)

```
Condition: positions == 0 AND orders == 0

Status: ✅ CLEAR
Action: CAN_CREATE_NEW
Reason: No existing trades to manage
```

---

### 9.2: Position Open, SAME Trend

**Scenario:** Old position is BUY and new signal is also BUY (or both SELL)

#### 9.2.1: Same Trend + Lotsize ≤ Old

```
Condition: oldTrend == newTrend AND newLot <= oldLot

Status: ✅ NO_ACTION
Reason: Keep existing position as is
Action: Do not create new trade, monitor existing position
```

**Example:**
```
Old position: BUY 0.01 lot
New signal: BUY (same trend) with 0.005 lot (smaller)

Action: KEEP old position ✅
Don't create new trade
```

---

#### 9.2.2: Same Trend + Lotsize > Old + Profit ≥ 2%

```
Condition: oldTrend == newTrend AND newLot > oldLot AND profitPercent >= 2%

Status: ✅ CLOSE_OLD_CREATE_NEW
Reason: Lotsize increased AND profit reached threshold
Action: 
  1. Close old position (take the 2% profit)
  2. Create new trade with larger lot
```

**Example:**
```
Old position: BUY 0.001 lot (profit: +$0.03 = +2.5%)
New signal: BUY (same trend) with 0.01 lot (larger)

Current P&L check: +2.5% >= 2% ✅ YES

Action: ✅ CLOSE old + CREATE new ✅
Benefits:
  - Lock in the 2% profit
  - Scale up to larger lot
  - Continue in same direction
```

---

#### 9.2.3: Same Trend + Lotsize > Old + Profit < 2%

```
Condition: oldTrend == newTrend AND newLot > oldLot AND profitPercent < 2%

Status: ⏸️ WAIT_FOR_PROFIT_THRESHOLD
Reason: Profit not at 2% threshold yet
Action: Keep existing position, don't create new trade
Monitor: Check again next cycle
```

**Example:**
```
Old position: BUY 0.001 lot (profit: +$0.01 = +0.5%)
New signal: BUY (same trend) with 0.01 lot (larger)

Current P&L check: +0.5% < 2% ❌ NO

Action: ⏸️ WAIT
Wait until profit reaches 2%, then close and scale up
```

---

### 9.3: Position Open, TREND CHANGED

**Scenario:** Old position is BUY but new signal is SELL (or vice versa)

#### 9.3.1: Trend Changed + Loss ≥ 2%

```
Condition: oldTrend != newTrend AND profitPercent <= -2%

Status: ✅ CLOSE_OLD_TREND_CHANGE_LOSS
Reason: Trend reversed AND hit loss threshold
Action:
  1. Close old position (cut loss at -2%)
  2. Create new trade in new direction
```

**Example:**
```
Old position: BUY 0.001 lot (loss: -$0.03 = -2.5%)
New signal: SELL (opposite trend)

Current P&L check: -2.5% <= -2% ✅ YES

Action: ✅ CLOSE old + CREATE new ✅
Benefits:
  - Cut loss at controlled -2% threshold
  - Switch to new trend direction
  - Minimize further damage
```

---

#### 9.3.2: Trend Changed + Profit ≥ 2%

```
Condition: oldTrend != newTrend AND profitPercent >= 2%

Status: ✅ CLOSE_OLD_TREND_CHANGE_PROFIT
Reason: Trend reversed but we're still profitable
Action:
  1. Close old position (take the 2% profit)
  2. Create new trade in new direction
```

**Example:**
```
Old position: BUY 0.001 lot (profit: +$0.04 = +3%)
New signal: SELL (opposite trend)

Current P&L check: +3% >= 2% ✅ YES

Action: ✅ CLOSE old + CREATE new ✅
Benefits:
  - Lock in 3% profit
  - Switch to new trend direction
  - Best-case scenario (profitable reversal)
```

---

#### 9.3.3: Trend Changed + |P&L| < 2%

```
Condition: oldTrend != newTrend AND -2% < profitPercent < 2%

Status: ⏸️ WAIT_FOR_THRESHOLD
Reason: Trend reversed but P&L hasn't reached ±2% threshold
Action: Keep existing position, don't create new trade
Monitor: Check again next cycle
```

**Example:**
```
Old position: BUY 0.001 lot (P&L: -0.5%)
New signal: SELL (opposite trend)

Current P&L check: -0.5% is between -2% and +2% ❌ NO

Action: ⏸️ WAIT
Wait until either:
  - Loss reaches -2% (then cut loss + reverse)
  - Profit reaches +2% (then take profit + reverse)
```

---

### 9.4: Pending Order (No Position)

```
Condition: positions == 0 AND orders > 0

Status: ⏸️ WAIT_PENDING_ORDER
Reason: Order is pending execution
Action: Don't create additional orders
Monitor: Wait for order to execute or expire
```

---

### 9.5: Multiple Positions/Orders (ERROR)

```
Condition: Any abnormal state (>1 position OR >1 order combination)

Status: ❌ ERROR_ABNORMAL_STATE
Reason: System violation (should only have 1 position max)
Action: STOP - Manual review required
```

---

## STEP 9 Summary Table

| Scenario | Condition | Action | Reason |
|----------|-----------|--------|--------|
| **Ready** | 0 pos, 0 ord | ✅ CREATE | Clear to trade |
| **Same Trend, No Change** | Same trend, lot ≤ old | ❌ WAIT | Keep position |
| **Same Trend, Scale Up (Profit)** | Same trend, lot > old, P≥2% | ✅ CLOSE+CREATE | Profit threshold met |
| **Same Trend, Scale Up (No Profit)** | Same trend, lot > old, P<2% | ❌ WAIT | Wait for profit |
| **Trend Reverse, Loss** | Different trend, P≤-2% | ✅ CLOSE+CREATE | Cut loss at threshold |
| **Trend Reverse, Profit** | Different trend, P≥2% | ✅ CLOSE+CREATE | Lock profit |
| **Trend Reverse, Threshold** | Different trend, \|P\|<2% | ❌ WAIT | Wait for threshold |
| **Pending Order** | 0 pos, 1+ ord | ❌ WAIT | Wait for execution |
| **Abnormal State** | Multiple pos/ord | ❌ STOP | Manual review |

---

## Complete Example Walkthrough

```
╔══════════════════════════════════════════════════════════════╗
║           COMPLETE TRADE CHECK - STEP 0-9                     ║
╚══════════════════════════════════════════════════════════════╝

STEP 0: Market Status
  ✅ Bid: 5155.23, Ask: 5155.95 (OPEN)

STEP 1: Fresh Entry Price
  → Entry = (5155.23 + 5155.95) / 2 = 5155.59

STEP 2: M15 Chart Analysis (100 bars)
  → Support: 5039.78
  → Resistance: 5155.95
  → Volatility: 116.17 points
  → Trend: DOWN (entry below midpoint) 🔴

STEP 3: Dynamic SL/TP Calculation
  → SL Buffer: 116.17 × 0.20 = 23.23
  → TP Buffer: 116.17 × 0.50 = 58.09
  → For SELL: SL = 5178.82, TP = 5097.50

STEP 4: Risk/Reward Ratio
  → Risk: 23.23, Reward: 58.09
  → R/R = 2.5 : 1 ✅

STEP 5: Position Sizing (2% Risk)
  → Balance: $0.28, Equity: $0.27
  → Selected: $0.28 (higher) ✅
  → Risk Amount: $0.0056
  → Calculated Lot: 0.000241 → 0.001 lot

STEP 6: Signal Strength
  → Base: 4 + R/R bonus: 2 + Volatility: 2 = 8/10 = STRONG ✅

STEP 7: Validate SL/TP Direction
  → SELL: TP(5097.50) < Entry(5155.59) < SL(5178.82) ✅

STEP 8: Final API Verification
  → All data from MetaApi ✅

STEP 9: Position & Order Check
  → Current: 0 positions, 0 orders
  → Status: CLEAR ✅
  → Action: CAN_CREATE_NEW

╔══════════════════════════════════════════════════════════════╗
║                   FINAL RECOMMENDATION                        ║
╚══════════════════════════════════════════════════════════════╝

✅ TRADE READY: STRONG SELL

  Signal: SELL (8/10 - STRONG)
  Entry: 5155.59
  SL: 5178.82 (+23.23 points)
  TP: 5097.50 (-58.09 points)
  Lot Size: 0.001
  R/R Ratio: 2.5 : 1
  
  Action: ✅ CREATE NEW TRADE NOW

═══════════════════════════════════════════════════════════════
```

---

## Key Improvements Summary

| Aspect | Change | Benefit |
|--------|--------|---------|
| **STEP Order** | Position check moved to END | Logical flow (analysis first) |
| **Chart Analysis** | M15 candles (100 bars) | Better volatility + trend |
| **Balance Logic** | Use MAX(Balance, Equity) | Accurate 2% risk calculation |
| **Position Check** | 9 detailed conditions | Smart trade management |
| **Trend Change** | ±2% profit threshold | Controlled risk management |
| **Lot Scaling** | Scale only with profit lock | Protect capital |

---

## Credits

**System Design:** Kanutsanan Pongpanna
**Latest Version:** Agentic AI Auto Trading for MT5
**Last Updated:** 2025-03-07

