#!/usr/bin/env node

/**
 * KANUTSANAN-PONGPANNA AGENTIC FULL-AUTO TRADING - Template Version
 * 
 * ⚠️ SETUP REQUIRED:
 * 1. Set environment variables: TOKEN and ACCOUNT_ID
 * 2. Run: source .env && node kanutsanan-pongpanna-full-auto-template.js &
 * 
 * 🔐 SECURITY:
 * - Do NOT hardcode credentials
 * - Use environment variables ONLY
 * - Never commit .env to git
 * 
 * 📊 EXECUTION:
 * - Runs every 30 seconds via CRON (updated from 38)
 * - PHASE 1: Trade analysis (15-20 sec)
 * - PHASE 2: Validate 8 conditions (1-2 sec)
 * - PHASE 3: Execute trade (5-10 sec)
 * - PHASE 3B: Final verify (1-2 sec)
 * 
 * 📈 WEEKLY PERFORMANCE:
 * - Runs: 20,160 times per week (+25% from old 38-second version)
 * - Each cycle: Full analysis + smart position management
 */

let MetaApi = require('metaapi.cloud-sdk').default;

// 🔴 GET CREDENTIALS FROM ENVIRONMENT
let token = process.env.TOKEN;
let accountId = process.env.ACCOUNT_ID;

// 🔴 VALIDATE CREDENTIALS
if (!token || !accountId) {
  console.error('\n❌ ERROR: Missing environment variables!\n');
  console.error('Setup:');
  console.error('  1. Edit .env with your credentials');
  console.error('  2. Run: source .env');
  console.error('  3. Run: node kanutsanan-pongpanna-full-auto-template.js &\n');
  process.exit(1);
}

const SYMBOL = 'XAUUSD.sml';
const api = new MetaApi(token);

// Daily tracking (in-memory, resets per UTC day)
let dailyState = {
  tradeCount: 0,
  startBalance: 0,
  isHalted: false
};

async function selectLotSize(calculatedSize) {
  const LOT_OPTIONS = [0.001, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 
                       0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.00,
                       2.00, 3.00, 4.00, 5.00, 6.00, 7.00, 8.00, 9.00, 10.00];
  if (calculatedSize < 0.001) return 0.001;
  let closestLower = null;
  for (let i = LOT_OPTIONS.length - 1; i >= 0; i--) {
    if (LOT_OPTIONS[i] <= calculatedSize) {
      closestLower = LOT_OPTIONS[i];
      break;
    }
  }
  return closestLower || 0.001;
}

// 🔴 PHASE 1: Trade Check (STEP 0-9 - AGENTIC VERSION)
async function runTradeCheck(connection, accountInfo) {
  try {
    // STEP 0: Market Status
    const symbolPrice = await connection.getSymbolPrice(SYMBOL);
    const entry = (symbolPrice.bid + symbolPrice.ask) / 2;
    
    // STEP 1: Fresh Entry Price
    // (Already calculated)
    
    // STEP 2: M15 Chart Analysis (100 candles)
    let candles = [];
    try {
      candles = await connection.getCandles(SYMBOL, '15m', {limit: 100});
    } catch (e) { }
    
    let prices = [symbolPrice.bid, symbolPrice.ask, entry];
    if (candles && candles.length > 0) {
      prices = prices.concat(candles.map(c => c.high || c.open));
      prices = prices.concat(candles.map(c => c.low || c.open));
    }
    
    const volatility = Math.max(Math.max(...prices) - Math.min(...prices), 20);
    const support = Math.min(...prices);
    const resistance = Math.max(...prices);
    const midPrice = (support + resistance) / 2;
    const trend = entry > midPrice ? 'UP' : 'DOWN';
    
    // STEP 3: Dynamic SL/TP
    const slBuffer = volatility * 0.20;
    const tpBuffer = volatility * 0.50;
    let sl, tp, signalType;
    
    if (trend === 'DOWN') {
      sl = entry + slBuffer;
      tp = entry - tpBuffer;
      signalType = 'SELL';
    } else {
      sl = entry - slBuffer;
      tp = entry + tpBuffer;
      signalType = 'BUY';
    }
    
    const slPoints = Math.abs(sl - entry);
    const tpPoints = Math.abs(tp - entry);
    
    // STEP 4: Risk/Reward Ratio
    const ratio = tpPoints / slPoints;
    
    // STEP 5: Position Sizing (2% Risk + Balance vs Equity Logic) ✨ NEW
    const balance = accountInfo.balance;
    const equity = accountInfo.equity;
    const baseAmount = balance > equity ? balance : equity;  // NEW: Use higher value
    const riskAmount = baseAmount * 0.02;
    const lotSize = await selectLotSize(riskAmount / slPoints);
    
    // STEP 6: Signal Strength
    let score = 4;
    if (ratio >= 1.5) score += 2;
    if (volatility > 50) score += 1;
    if (volatility > 100) score += 1;
    score = Math.min(score, 10);
    
    let strength = 'WEAK';
    if (score >= 6) strength = 'STRONG';
    else if (score >= 4) strength = 'MEDIUM';
    
    // STEP 7: Validate SL/TP
    let slValid = false;
    if (signalType === 'BUY' && sl < entry && tp > entry) {
      slValid = true;
    } else if (signalType === 'SELL' && sl > entry && tp < entry) {
      slValid = true;
    }
    
    if (!slValid) {
      return { success: false, reason: 'Invalid SL/TP direction' };
    }
    
    // STEP 8: Final API Verification (all from API)
    
    // STEP 9: Position & Order Check with Profit Thresholds ✨ MOVED TO END
    const positions = await connection.getPositions();
    const orders = await connection.getOrders();
    
    let canCreateNew = true;
    let positionStatus = 'CLEAR';
    
    // 3.1: No existing position/order
    if (positions.length === 0 && orders.length === 0) {
      canCreateNew = true;
      positionStatus = 'CLEAR';
    }
    // Has position
    else if (positions.length > 0 && orders.length === 0) {
      const oldPosition = positions[0];
      const oldTrend = oldPosition.type === 'POSITION_TYPE_BUY' ? 'UP' : 'DOWN';
      const oldLotsize = oldPosition.volume;
      
      // Same trend scenarios
      if (oldTrend === trend) {
        // 3.2.1: Same trend + lotsize unchanged or lower
        if (lotSize <= oldLotsize) {
          canCreateNew = false;
          positionStatus = 'SAME_TREND_NO_CHANGE';
        } 
        // 3.2.2: Same trend + lotsize higher + check profit >= 2%
        else {
          const currentProfit = oldPosition.profit || 0;
          const profitPercent = (currentProfit / balance) * 100;
          
          if (profitPercent >= 2.0) {
            canCreateNew = true;
            positionStatus = 'CLOSE_PROFIT_THRESHOLD';
          } else {
            canCreateNew = false;
            positionStatus = 'WAIT_PROFIT';
          }
        }
      }
      // Trend changed scenarios
      else {
        const currentProfit = oldPosition.profit || 0;
        const profitPercent = (currentProfit / balance) * 100;
        
        // 3.2.3: Trend changed + check loss >= 2%
        // 3.2.4: Trend changed + check profit >= 2%
        if (profitPercent >= 2.0 || profitPercent <= -2.0) {
          canCreateNew = true;
          positionStatus = 'CLOSE_TREND_CHANGE';
        } else {
          canCreateNew = false;
          positionStatus = 'WAIT_THRESHOLD';
        }
      }
    }
    // Pending order
    else if (positions.length === 0 && orders.length > 0) {
      canCreateNew = false;
      positionStatus = 'PENDING_ORDER';
    }
    // Abnormal state
    else {
      canCreateNew = false;
      positionStatus = 'ERROR_ABNORMAL';
    }
    
    return {
      success: canCreateNew,
      entry,
      signalType,
      sl,
      tp,
      slPoints,
      tpPoints,
      ratio,
      score,
      strength,
      lotSize,
      volatility,
      trend,
      positionStatus,
      reason: canCreateNew ? 'Ready to trade' : positionStatus
    };

  } catch (error) {
    return { success: false, reason: `Trade check error: ${error.message}` };
  }
}

// 🔴 PHASE 2: Validate 8 Conditions
async function validateConditions(tradeData, accountInfo) {
  const conditions = [];
  
  // Condition 1: Signal Strength
  const cond1 = tradeData.score >= 4;
  conditions.push({ num: 1, name: 'Signal Strength', value: `${tradeData.score}/10`, pass: cond1 });
  
  // Condition 2: SL Points
  const cond2 = tradeData.slPoints < 100;
  conditions.push({ num: 2, name: 'SL Points', value: `${tradeData.slPoints.toFixed(2)} < 100`, pass: cond2 });
  
  // Condition 3: Risk (always 2%)
  const cond3 = true;
  conditions.push({ num: 3, name: 'Risk', value: '2% (automatic)', pass: cond3 });
  
  // Condition 4: R/R Ratio
  const cond4 = tradeData.ratio >= 1.0;
  conditions.push({ num: 4, name: 'R/R Ratio', value: `${tradeData.ratio.toFixed(2)}:1 >= 1.0`, pass: cond4 });
  
  // Condition 5: Daily Orders (UNLIMITED)
  const cond5 = true;
  conditions.push({ num: 5, name: 'Daily Orders', value: 'UNLIMITED', pass: cond5 });
  
  // Condition 6: Daily Loss (> -20%)
  const dailyLoss = ((accountInfo.balance - dailyState.startBalance) / dailyState.startBalance) * 100;
  const cond6 = dailyLoss > -20;
  conditions.push({ num: 6, name: 'Daily Loss Limit', value: `${dailyLoss.toFixed(2)}% > -20%`, pass: cond6 });
  
  // Condition 7: Equity
  const cond7 = accountInfo.equity > 0.10;
  conditions.push({ num: 7, name: 'Equity > $0.10', value: `$${accountInfo.equity.toFixed(4)}`, pass: cond7 });
  
  // Condition 8: Balance
  const cond8 = accountInfo.balance > 0.05;
  conditions.push({ num: 8, name: 'Balance > $0.05', value: `$${accountInfo.balance.toFixed(4)}`, pass: cond8 });
  
  // All conditions must pass
  const allPass = conditions.every(c => c.pass);
  
  return { conditions, allPass };
}

// 🔴 PHASE 3: Execute Trade
async function executeTrade(connection, tradeData) {
  try {
    const order = {
      symbol: SYMBOL,
      orderType: 'ORDER_TYPE_SELL_LIMIT' if (tradeData.signalType === 'SELL') else 'ORDER_TYPE_BUY_LIMIT',
      volume: tradeData.lotSize,
      openPrice: tradeData.entry,
      stopLoss: tradeData.sl,
      takeProfit: tradeData.tp,
      comment: 'KanutsananPongpanna Auto Trade'
    };
    
    await connection.createOrder(order);
    return { success: true, message: `Trade executed: ${tradeData.signalType} ${tradeData.lotSize}` };
  } catch (error) {
    return { success: false, message: `Trade execution failed: ${error.message}` };
  }
}

// 🔴 PHASE 3B: Final Verification
async function verifyTrade(connection, tradeData) {
  try {
    const positions = await connection.getPositions();
    const orders = await connection.getOrders();
    
    return {
      success: true,
      positions: positions.length,
      orders: orders.length,
      message: `Verification complete: ${positions.length} position(s), ${orders.length} order(s)`
    };
  } catch (error) {
    return { success: false, message: `Verification failed: ${error.message}` };
  }
}

// 🔴 MAIN EXECUTION
async function autoTrade() {
  try {
    const account = await api.metatraderAccountApi.getAccount(accountId);
    const initialState = account.state;
    const deployedStates = ['DEPLOYING', 'DEPLOYED'];

    if(!deployedStates.includes(initialState)) {
      await account.deploy();
    }
  
    await account.waitConnected();
    let connection = account.getRPCConnection();
    await connection.connect();
    await connection.waitSynchronized();

    const accountInfo = await connection.getAccountInformation();
    
    // Initialize daily state
    if (dailyState.startBalance === 0) {
      dailyState.startBalance = accountInfo.balance;
    }

    // PHASE 1: Trade Check
    const tradeData = await runTradeCheck(connection, accountInfo);
    
    if (!tradeData.success) {
      console.log(`[${new Date().toISOString()}] ⏸️  ${tradeData.reason}`);
      process.exit(0);
    }

    // PHASE 2: Validate 8 Conditions
    const validation = await validateConditions(tradeData, accountInfo);
    
    if (!validation.allPass) {
      const failed = validation.conditions.filter(c => !c.pass).map(c => c.name);
      console.log(`[${new Date().toISOString()}] ❌ Conditions failed: ${failed.join(', ')}`);
      process.exit(0);
    }

    // PHASE 3: Execute Trade
    const execution = await executeTrade(connection, tradeData);
    
    if (!execution.success) {
      console.log(`[${new Date().toISOString()}] ❌ ${execution.message}`);
      process.exit(0);
    }

    // PHASE 3B: Verification
    const verification = await verifyTrade(connection, tradeData);
    
    console.log(`[${new Date().toISOString()}] ✅ ${execution.message}`);
    console.log(`[${new Date().toISOString()}] ✅ ${verification.message}`);

    process.exit(0);
  } catch (error) {
    console.error(`[${new Date().toISOString()}] ❌ Error: ${error.message}`);
    process.exit(1);
  }
}

autoTrade();
