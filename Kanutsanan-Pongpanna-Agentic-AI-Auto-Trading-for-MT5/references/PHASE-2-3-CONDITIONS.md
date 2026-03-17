# PHASE 2-3 Conditions - Approval & Execution

Complete guide to the 8 safety conditions (PHASE 2) and execution logic (PHASE 3).

---

## Overview

After trade analysis (PHASE 1: STEP 0-9), the system validates 8 safety conditions before execution.

```
PHASE 1: Trade Check (STEP 0-9)
  ├─ STEP 0-9: Full analysis (15-20 sec)
  └─ Output: Trade recommendation + Signal strength
       ↓
PHASE 2: Validate 8 Conditions
  ├─ Condition 1: Signal strength
  ├─ Condition 2: SL points
  ├─ Condition 3: Risk percentage
  ├─ Condition 4: R/R ratio
  ├─ Condition 5: Daily orders
  ├─ Condition 6: Daily loss
  ├─ Condition 7: Equity
  └─ Condition 8: Balance
       ↓
PHASE 3: Execute Trade (if ALL pass)
  ├─ Place order
  └─ Log execution
       ↓
PHASE 3B: Verification
  └─ Confirm trade status
```

---

## PHASE 2: 8 Safety Conditions

### Condition 1: Signal Strength

**Requirement:** Signal ≥ 4/10

```
Scale:
  0-3:   WEAK      ❌ (Skip)
  4-5:   MEDIUM    ⚠️  (Caution)
  6-10:  STRONG    ✅ (Good)

Calculation:
  Base: 4 points
  + 2 if R/R >= 1.5
  + 1 if Volatility > 50
  + 1 if Volatility > 100
  
  Total: Capped at 10
```

**Example:**
```
Base: 4
R/R 2.5 >= 1.5: +2 points
Volatility 116 > 50: +1 point
Volatility 116 > 100: +1 point

Total: 8/10 = STRONG ✅ PASS
```

---

### Condition 2: SL Points

**Requirement:** SL < 100 points

```
Purpose: Limit maximum risk per trade
Example Values:
  ✅ SL: 8 points → PASS
  ✅ SL: 50 points → PASS
  ✅ SL: 99 points → PASS
  ❌ SL: 100 points → FAIL (not less than)
  ❌ SL: 150 points → FAIL
```

**Why 100 points limit?**
- Prevents excessive risk
- Controls drawdown
- Maintains scalability

---

### Condition 3: Risk Percentage

**Requirement:** Risk = 2% per trade (automatic)

```
Calculation:
  Balance vs Equity: MAX(Balance, Equity)
  Risk Amount: Selected × 2%
  Lot Size: Risk Amount / SL Points

Example:
  Balance: $1,000
  Equity: $950
  Selected: $1,000 (higher)
  Risk: $1,000 × 2% = $20 ✅
```

**Status:** Always PASS (automatic 2% calculation)

---

### Condition 4: Risk/Reward Ratio

**Requirement:** R/R ≥ 1.0

```
Calculation:
  Risk: |Entry - SL|
  Reward: |TP - Entry|
  Ratio: Reward / Risk

Requirement: Reward >= Risk

Example 1: PASS
  Risk: 10 points
  Reward: 15 points
  Ratio: 1.5 ✅ (Good)

Example 2: PASS (Minimum)
  Risk: 10 points
  Reward: 10 points
  Ratio: 1.0 ✅ (Exactly break-even)

Example 3: FAIL
  Risk: 10 points
  Reward: 5 points
  Ratio: 0.5 ❌ (Risk > Reward)
```

---

### Condition 5: Daily Orders

**Requirement:** Orders < UNLIMITED

```
Status: Always PASS ✅

Explanation:
  - No daily trade limit
  - Can open unlimited trades per day
  - Limited only by other conditions
  
Old Version: < 100 trades/day
New Version: UNLIMITED
```

---

### Condition 6: Daily Loss Limit

**Requirement:** Loss > -20%

```
Calculation:
  Daily Loss % = (Current Balance - Start Balance) / Start Balance

Thresholds:
  ✅ Loss: -5% → PASS (within limit)
  ✅ Loss: -15% → PASS (within limit)
  ✅ Loss: -19.9% → PASS (just under limit)
  ❌ Loss: -20% → FAIL (at limit, halt)
  ❌ Loss: -25% → FAIL (exceeded limit)

Purpose: Circuit breaker
  - Protects account from ruin
  - Stops trading when losses mount
  - Prevents emotional trading
```

**Example Scenario:**

```
Start of Day:
  Balance: $1,000

During Day:
  Trade 1: -$50 (Loss: -5%)
  Trade 2: -$80 (Total Loss: -13%)
  Trade 3: -$60 (Total Loss: -19%)
  → Still trading allowed ✅

If Loss hits -20%:
  → Trading halts automatically ❌
  → Resume next day
```

---

### Condition 7: Equity Requirement

**Requirement:** Equity > $0.10

```
Definition:
  Equity = Balance + P&L from open positions

Purpose:
  - Ensure margin available
  - Prevent liquidation
  - Minimum capital threshold

Example 1: PASS
  Balance: $100
  Open P&L: -$50
  Equity: $50 ✅ (> $0.10)

Example 2: FAIL
  Balance: $0.15
  Open P&L: -$0.10
  Equity: $0.05 ❌ (< $0.10)
```

---

### Condition 8: Balance Requirement

**Requirement:** Balance > $0.05

```
Definition:
  Balance = Account capital (before P&L)

Purpose:
  - Minimum account size
  - Prevent micro-trading edge cases
  - Ensure feasible lot sizes

Example 1: PASS
  Balance: $100 ✅ (> $0.05)
  → Can trade

Example 2: PASS
  Balance: $0.10 ✅ (> $0.05)
  → Can trade

Example 3: FAIL
  Balance: $0.03 ❌ (< $0.05)
  → Cannot trade (too small)
```

---

## PHASE 2 Summary Table

| # | Condition | Requirement | Type | Purpose |
|---|-----------|-------------|------|---------|
| 1 | Signal | ≥ 4/10 | Quality | Trade strength |
| 2 | SL Points | < 100 | Risk | Limit per trade |
| 3 | Risk % | = 2% | Automatic | Consistent sizing |
| 4 | R/R | ≥ 1.0 | Ratio | Reward vs Risk |
| 5 | Orders | UNLIMITED | Daily | No cap |
| 6 | Loss | > -20% | Circuit Breaker | Daily max loss |
| 7 | Equity | > $0.10 | Minimum | Margin available |
| 8 | Balance | > $0.05 | Minimum | Account size |

---

## PHASE 2 Decision Logic

```
FOR EACH CONDITION:
  IF condition.value MEETS requirement:
    Set condition.pass = TRUE
  ELSE:
    Set condition.pass = FALSE

IF ALL 8 conditions.pass == TRUE:
  → ALL_CONDITIONS_MET = TRUE
  → Proceed to PHASE 3 (Execution)
ELSE:
  → ALL_CONDITIONS_MET = FALSE
  → SKIP trade (output reason)
  → Wait for next cycle
```

---

## PHASE 3: Execute Trade

If ALL conditions pass:

```
Order Parameters:
  - Symbol: XAUUSD.sml
  - Type: BUY_LIMIT or SELL_LIMIT
  - Volume (Lot): From STEP 5 calculation
  - Entry Price: From STEP 1
  - Stop Loss: From STEP 3
  - Take Profit: From STEP 3
  - Comment: "KanutsananPongpanna Auto Trade"

Execution:
  → Create order via MetaApi
  → Log to file
  → Send notification (optional)
```

---

## PHASE 3B: Verification

After execution:

```
Verify:
  - Position created? (Check positions list)
  - Order executed? (Check orders list)
  - Correct lot size?
  - Correct SL/TP?

Log Results:
  - Timestamp
  - Trade details
  - Status (success/failed)
  - Next action
```

---

## Complete Approval Flow Example

```
═══════════════════════════════════════════════════════════

PHASE 1 RESULT:
  Signal: SELL (8/10 - STRONG)
  Entry: 5155.59
  SL: 5178.82 (23.23 points)
  TP: 5097.50 (58.09 points)
  Lot: 0.001
  R/R: 2.5 : 1

───────────────────────────────────────────────────────────
PHASE 2: CONDITION VALIDATION
───────────────────────────────────────────────────────────

Condition 1: Signal Strength
  Value: 8/10
  Requirement: ≥ 4/10
  Result: ✅ PASS

Condition 2: SL Points
  Value: 23.23 points
  Requirement: < 100
  Result: ✅ PASS

Condition 3: Risk Percentage
  Value: 2% (automatic)
  Requirement: = 2%
  Result: ✅ PASS

Condition 4: R/R Ratio
  Value: 2.5 : 1
  Requirement: ≥ 1.0
  Result: ✅ PASS

Condition 5: Daily Orders
  Value: UNLIMITED
  Requirement: < UNLIMITED
  Result: ✅ PASS

Condition 6: Daily Loss
  Value: -5% (today's loss)
  Requirement: > -20%
  Result: ✅ PASS

Condition 7: Equity
  Value: $0.28
  Requirement: > $0.10
  Result: ✅ PASS

Condition 8: Balance
  Value: $0.28
  Requirement: > $0.05
  Result: ✅ PASS

───────────────────────────────────────────────────────────
APPROVAL SUMMARY
───────────────────────────────────────────────────────────

Conditions Met: 8 / 8 ✅

Status: ALL PASS

Decision: → EXECUTE TRADE

───────────────────────────────────────────────────────────
PHASE 3: EXECUTION
───────────────────────────────────────────────────────────

Creating Order:
  • Symbol: XAUUSD.sml
  • Type: SELL_LIMIT
  • Entry: 5155.59
  • SL: 5178.82
  • TP: 5097.50
  • Volume: 0.001 lot

Status: ✅ EXECUTED
Message: Order #123456 created

───────────────────────────────────────────────────────────
PHASE 3B: VERIFICATION
───────────────────────────────────────────────────────────

Position Status:
  • Open Positions: 1 ✅
  • Pending Orders: 0 ✅
  • Verification: SUCCESS ✅

═══════════════════════════════════════════════════════════
```

---

## Failure Examples

### Example 1: Signal Too Weak

```
PHASE 1:
  Signal: 3/10 (WEAK)
  
PHASE 2:
  Condition 1: Signal ≥ 4/10
  Value: 3/10
  Result: ❌ FAIL

Decision: SKIP TRADE
Reason: Insufficient signal strength
```

---

### Example 2: Daily Loss Exceeded

```
PHASE 1:
  ✅ All STEP 0-9 analysis looks good

PHASE 2:
  Condition 6: Loss > -20%
  Today's Loss: -22%
  Result: ❌ FAIL

Decision: HALT TRADING
Reason: Daily loss limit exceeded (-22% > -20%)
Action: Resume trading next day
```

---

### Example 3: Insufficient Balance

```
PHASE 1:
  ✅ Analysis complete
  Lot Size: 0.001
  Risk: 2%

PHASE 2:
  Condition 8: Balance > $0.05
  Current Balance: $0.02
  Result: ❌ FAIL

Decision: SKIP TRADE
Reason: Insufficient balance ($0.02 < $0.05)
Action: Deposit funds to continue trading
```

---

## Summary

- **PHASE 2:** Validates ALL 8 conditions must pass
- **PHASE 3:** Executes only if ALL conditions pass
- **PHASE 3B:** Verifies execution completed
- **Safety:** Any single failure stops the trade

---

**Created by:** Kanutsanan Pongpanna
**Version:** Agentic AI Auto Trading for MT5
**Last Updated:** 2025-03-07

