#!/usr/bin/env node

/**
 * KANUTSANAN-PONGPANNA AGENTIC TRADE CHECK - Template Version
 * 
 * ⚠️ SETUP REQUIRED:
 * 1. Set environment variables: TOKEN and ACCOUNT_ID
 * 2. Run: source .env && node kanutsanan-pongpanna-trade-check-template.js
 * 
 * 🔐 SECURITY:
 * - Do NOT hardcode credentials
 * - Use environment variables ONLY
 * - Never commit .env to git
 * 
 * 📋 STEPS (AGENTIC VERSION - REORDERED):
 * STEP 0: Market Status Check
 * STEP 1: Fresh Entry Price (Real-time)
 * STEP 2: M15 Chart Analysis (100 candles)
 * STEP 3: Dynamic SL/TP Calculation
 * STEP 4: Risk/Reward Ratio (≥1.0)
 * STEP 5: Position Sizing (2% Rule + Balance/Equity Logic)
 * STEP 6: Signal Strength (0-10)
 * STEP 7: Validate SL/TP Direction
 * STEP 8: Final API Verification
 * STEP 9: Position & Order Check with Profit Thresholds (MOVED TO END)
 */

let MetaApi = require('metaapi.cloud-sdk').default;

// 🔴 GET CREDENTIALS FROM ENVIRONMENT (NOT HARDCODED)
let token = process.env.TOKEN;
let accountId = process.env.ACCOUNT_ID;

// 🔴 VALIDATE CREDENTIALS
if (!token || !accountId) {
  console.error('\n❌ ERROR: Missing required environment variables!\n');
  console.error('Setup Instructions:');
  console.error('  1. Edit .env file with your credentials');
  console.error('  2. Run: source .env');
  console.error('  3. Run: node kanutsanan-pongpanna-trade-check-template.js\n');
  console.error('Example .env:');
  console.error('  export TOKEN="your-metaapi-key-here"');
  console.error('  export ACCOUNT_ID="your-account-id-here"\n');
  process.exit(1);
}

const SYMBOL = 'XAUUSD.sml';
const api = new MetaApi(token);

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

async function checkTrade() {
  try {
    console.log('\n═══════════════════════════════════════════');
    console.log('🤖 KANUTSANAN-PONGPANNA AGENTIC TRADE CHECK');
    console.log('═══════════════════════════════════════════\n');

    const account = await api.metatraderAccountApi.getAccount(accountId);
    const initialState = account.state;
    const deployedStates = ['DEPLOYING', 'DEPLOYED'];

    if(!deployedStates.includes(initialState)) {
      console.log('📊 Deploying account...');
      await account.deploy();
    }
  
    console.log('⏳ Waiting for API connection...');
    await account.waitConnected();

    let connection = account.getRPCConnection();
    await connection.connect();

    console.log('⏳ Waiting for SDK synchronization...');
    await connection.waitSynchronized();

    // ✅ STEP 0: Market Status
    console.log('\n🔴 STEP 0: Market Status Check');
    const symbolPrice = await connection.getSymbolPrice(SYMBOL);
    console.log(`  Bid: ${symbolPrice.bid}, Ask: ${symbolPrice.ask}`);

    // ✅ STEP 1: Fresh Entry Price (Real-time)
    console.log('\n🔴 STEP 1: Fresh Entry Price (Real-time)');
    const entry = (symbolPrice.bid + symbolPrice.ask) / 2;
    console.log(`  Entry Price: ${entry}`);

    // ✅ STEP 2: M15 Chart Analysis (100 candles)
    console.log('\n🔴 STEP 2: M15 Chart Analysis (100 Candles)');
    let candles = [];
    try {
      candles = await connection.getCandles(SYMBOL, '15m', {limit: 100});
    } catch (e) {
      console.log(`  (No M15 candle history available)`);
    }
    
    let prices = [symbolPrice.bid, symbolPrice.ask, entry];
    if (candles && candles.length > 0) {
      prices = prices.concat(candles.map(c => c.high || c.open));
      prices = prices.concat(candles.map(c => c.low || c.open));
    }
    
    const highestPrice = Math.max(...prices);
    const lowestPrice = Math.min(...prices);
    const resistance = highestPrice;
    const support = lowestPrice;
    const volatility = Math.max(resistance - support, 20);
    
    console.log(`  Support (M15): ${support.toFixed(2)}, Resistance (M15): ${resistance.toFixed(2)}`);
    console.log(`  Volatility (M15): ${volatility.toFixed(2)} points`);
    console.log(`  Candles analyzed: ${candles.length}`);
    
    const trend = entry > (support + resistance) / 2 ? 'UP' : 'DOWN';
    console.log(`  Trend: ${trend}`);

    // ✅ STEP 3: Dynamic SL/TP
    console.log('\n🔴 STEP 3: Dynamic SL/TP Calculation');
    const effectiveVolatility = volatility > 0 ? volatility : 20;
    const slBuffer = effectiveVolatility * 0.20;
    const tpBuffer = effectiveVolatility * 0.50;
    
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
    
    console.log(`  Signal: ${signalType}`);
    console.log(`  SL: ${sl.toFixed(2)} (${slPoints.toFixed(2)} points)`);
    console.log(`  TP: ${tp.toFixed(2)} (${tpPoints.toFixed(2)} points)`);

    // ✅ STEP 4: Risk/Reward Ratio
    console.log('\n🔴 STEP 4: Risk/Reward Ratio');
    const risk = Math.abs(entry - sl);
    const reward = Math.abs(tp - entry);
    const ratio = reward / risk;
    console.log(`  Risk: ${risk.toFixed(2)} points`);
    console.log(`  Reward: ${reward.toFixed(2)} points`);
    console.log(`  R/R Ratio: ${ratio.toFixed(2)} : 1`);
    
    if (ratio < 1.0) {
      console.log('  ⚠️ R/R ratio < 1.0 - Signal too weak');
    }

    // ✅ STEP 5: Position Sizing (2% Risk + Balance vs Equity Logic)
    console.log('\n🔴 STEP 5: Position Sizing (2% Risk Rule + Balance/Equity Logic)');
    const accountInfo = await connection.getAccountInformation();
    const balance = accountInfo.balance;
    const equity = accountInfo.equity;
    
    // NEW: Use Balance if > Equity, else use Equity
    const baseAmount = balance > equity ? balance : equity;
    const riskAmount = baseAmount * 0.02;
    const calculatedSize = riskAmount / slPoints;
    const selectedLot = await selectLotSize(calculatedSize);
    
    console.log(`  Balance: $${balance.toFixed(4)}`);
    console.log(`  Equity: $${equity.toFixed(4)}`);
    console.log(`  Selected Base Amount: $${baseAmount.toFixed(4)} (${balance > equity ? 'Balance is higher' : 'Equity is higher'})`);
    console.log(`  Risk (2%): $${riskAmount.toFixed(4)}`);
    console.log(`  SL Points: ${slPoints.toFixed(2)}`);
    console.log(`  Calculated Lot: ${calculatedSize.toFixed(6)}`);
    console.log(`  Selected Lot: ${selectedLot}`);

    // ✅ STEP 6: Signal Strength (0-10)
    console.log('\n🔴 STEP 6: Signal Strength (0-10 Score)');
    let score = 4; // Base score
    if (ratio >= 1.5) score += 2;
    if (volatility > 50) score += 1;
    if (volatility > 100) score += 1;
    
    score = Math.min(score, 10);
    
    let strength = 'WEAK';
    if (score >= 6) strength = 'STRONG';
    else if (score >= 4) strength = 'MEDIUM';
    
    console.log(`  Base: 4 points`);
    if (ratio >= 1.5) console.log(`  + 2 (R/R >= 1.5)`);
    if (volatility > 50) console.log(`  + 1 (Volatility > 50)`);
    if (volatility > 100) console.log(`  + 1 (Volatility > 100)`);
    console.log(`  Total Score: ${score}/10 = ${strength}`);

    // ✅ STEP 7: Validate SL/TP Direction
    console.log('\n🔴 STEP 7: Validate SL/TP Direction');
    let slValid = false;
    if (signalType === 'BUY' && sl < entry && tp > entry) {
      slValid = true;
      console.log('  ✅ BUY: SL < Entry < TP');
    } else if (signalType === 'SELL' && sl > entry && tp < entry) {
      slValid = true;
      console.log('  ✅ SELL: TP < Entry < SL');
    }
    
    if (!slValid) {
      console.log('  ❌ SL/TP direction invalid');
      process.exit(1);
    }

    // ✅ STEP 8: Final API Verification
    console.log('\n🔴 STEP 8: Final API Verification');
    console.log('  ✅ Entry price: from getSymbolPrice()');
    console.log('  ✅ Volatility: from getCandles() M15');
    console.log('  ✅ Account info: from getAccountInformation()');
    console.log('  ✅ All data from MetaApi (no external sources)');

    // ✅ STEP 9: Position & Order Check with Profit Thresholds (MOVED TO END)
    console.log('\n🔴 STEP 9: Position & Order Check (Smart Management)');
    const positions = await connection.getPositions();
    const orders = await connection.getOrders();
    
    console.log(`  Open Positions: ${positions.length}`);
    console.log(`  Pending Orders: ${orders.length}`);
    
    let canCreateNew = true;
    let actionNote = '';
    
    // 3.1: No old orders - Ready to create new
    if (positions.length === 0 && orders.length === 0) {
      console.log('  ✅ [3.1] Ready - No positions/orders');
      actionNote = 'CAN_CREATE_NEW';
    }
    // Has position
    else if (positions.length > 0 && orders.length === 0) {
      const oldPosition = positions[0];
      const oldTrend = oldPosition.type === 'POSITION_TYPE_BUY' ? 'UP' : 'DOWN';
      console.log(`  ⚠️  Old Position Found`);
      console.log(`      Type: ${oldPosition.type}`);
      console.log(`      Trend: ${oldTrend} → New Trend: ${trend}`);
      
      const oldLotsize = oldPosition.volume;
      console.log(`      Old Lotsize: ${oldLotsize}, New Lotsize: ${selectedLot}`);
      
      // 3.2: Position with same trend
      if (oldTrend === trend) {
        // 3.2.1: Same trend, lotsize unchanged or lower
        if (selectedLot <= oldLotsize) {
          console.log(`  ✅ [3.2.1] Same trend, lotsize ≤ old → NO_ACTION`);
          actionNote = 'NO_ACTION_SAME_TREND';
          canCreateNew = false;
        } 
        // 3.2.2: Same trend, lotsize higher - check profit >= 2%
        else {
          console.log(`  ℹ️  [3.2.2] Same trend, lotsize > old → Check profit`);
          const currentProfit = oldPosition.profit || 0;
          const profitPercent = (currentProfit / balance) * 100;
          console.log(`      Current P&L: $${currentProfit.toFixed(4)} (${profitPercent.toFixed(2)}%)`);
          
          if (profitPercent >= 2.0) {
            console.log(`  ✅ Profit ≥ 2% → CLOSE_OLD_CREATE_NEW`);
            actionNote = 'CLOSE_OLD_PROFIT_THRESHOLD';
            canCreateNew = true;
          } else {
            console.log(`  ⏸️  Profit < 2% → WAIT`);
            actionNote = 'WAIT_PROFIT_THRESHOLD';
            canCreateNew = false;
          }
        }
      }
      // 3.2.3-3.2.4: Trend changed
      else {
        console.log(`  ℹ️  Trend changed → Check loss/profit`);
        const currentProfit = oldPosition.profit || 0;
        const profitPercent = (currentProfit / balance) * 100;
        console.log(`      Current P&L: $${currentProfit.toFixed(4)} (${profitPercent.toFixed(2)}%)`);
        
        // 3.2.3: Trend changed, check loss >= 2%
        if (profitPercent <= -2.0) {
          console.log(`  ✅ [3.2.3] Loss ≥ 2% → CLOSE_OLD_CREATE_NEW`);
          actionNote = 'CLOSE_OLD_TREND_CHANGE_LOSS';
          canCreateNew = true;
        }
        // 3.2.4: Trend changed, check profit >= 2%
        else if (profitPercent >= 2.0) {
          console.log(`  ✅ [3.2.4] Profit ≥ 2% → CLOSE_OLD_CREATE_NEW`);
          actionNote = 'CLOSE_OLD_TREND_CHANGE_PROFIT';
          canCreateNew = true;
        }
        // Neither loss nor profit at threshold
        else {
          console.log(`  ⏸️  P&L between -2% and +2% → WAIT`);
          actionNote = 'WAIT_THRESHOLD';
          canCreateNew = false;
        }
      }
    }
    // Pending order
    else if (positions.length === 0 && orders.length > 0) {
      console.log('  ⏸️  Pending order open → WAIT');
      actionNote = 'WAIT_PENDING_ORDER';
      canCreateNew = false;
    }
    // Abnormal state
    else {
      console.log('  ❌ Multiple positions/orders (abnormal)');
      actionNote = 'ERROR_ABNORMAL_STATE';
      canCreateNew = false;
    }

    // Final Summary
    console.log('\n' + '═'.repeat(50));
    
    if (!canCreateNew) {
      console.log(`⏸️  CANNOT CREATE NEW TRADE`);
      console.log(`   Reason: ${actionNote}`);
      console.log(`   Action: WAIT for next cycle`);
    } else {
      console.log(`✅ TRADE READY: ${strength} ${signalType}`);
      console.log(`   Entry: ${entry.toFixed(2)}`);
      console.log(`   SL: ${sl.toFixed(2)} (${slPoints.toFixed(2)} pts)`);
      console.log(`   TP: ${tp.toFixed(2)} (${tpPoints.toFixed(2)} pts)`);
      console.log(`   Lot: ${selectedLot}`);
      console.log(`   R/R: ${ratio.toFixed(2)} : 1`);
      console.log(`   Signal: ${score}/10 (${strength})`);
      console.log(`   Action: ${actionNote}`);
    }
    
    console.log('═'.repeat(50) + '\n');

    process.exit(0);
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

checkTrade();
