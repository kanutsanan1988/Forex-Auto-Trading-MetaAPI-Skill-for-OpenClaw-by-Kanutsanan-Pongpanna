<!-- Python Qaunt Trading + AI(LLM) Live Research | Creator: Kanutsanan Pongpanna | Settrade e-Open Account · MTS Gold Futures + MT5 -->

# Current-source review and known gaps

This report summarizes the included source inspected on 24 September 2026. It is not a backtest or profitability claim. The complete audit and research history is in `research/2026-09-24-current-system-reaudit.md`.

## Current architecture

- `outputs/mt5_python_bridge/auto_trader.py` owns the one-minute decision cycle, account/symbol connection, position lifecycle, risk gate, request construction, MT5 `order_check`, guarded `order_send`, and audit/state update.
- `strategy_engine.py` calculates market frames and six strategy agents (Trend, Range, Mean Reversion, Counter-Trend, Breakout, Breakout Reversal), each with Buy/Sell candidate metrics.
- `bounded_adaptive_research.py`, `adaptive_shadow.py`, and `auto_threshold.py` update future threshold/weight inputs from chart and closed-trade evidence; they do not prove prospective profitability.
- `live_executor.py` is a separate two-phase prepare/confirm entry route. It refuses new orders when a matching position already exists, validates volume, SL/TP direction, spread, risk and RR, and still needs explicit confirmation to execute.
- `choose_mode.py` keeps Python jobs active in both modes and gates registered AI jobs. Mode 2 is the default; provider flags remain separate.
- `agents/brief_mode2.md` and `agents/brief_admin.md` define the Agent roles. The primary Agent on each platform can load both briefs and act as coordinator/Hermes, Mode-2 bot, and Admin Bot; a CLI/scheduler adapter is separate.

## Position sequence observed

On each processing cycle the current source:

1. Connects and updates closed-trade/chart/adaptive state.
2. Analyzes signal direction and runs `early_cut_losing_positions`.
3. Evaluates profit exit, same-direction cut-loss, transition behavior, and opposite-direction signals.
4. Waits for closed positions to disappear from MT5 state before evaluating a replacement order.
5. Runs risk/permission checks and sends only after `order_check`, `live_enabled`, terminal permission, and account permission pass.

Known discrepancy: `manage_profitable_positions()` includes a “hedge cap” exception: if the opposite signal arrives while the old position is profitable and fewer than two positions exist, it may keep the old position and allow another. This conflicts with the owner's repeated instruction to close the old position on any opposite signal. Do not describe the current code as always closing on reversal.

## Structural setup conflict

`strategy_engine.decide_market()` emits structural eligibility as diagnostic information because factory `structural_mode` is `diagnostic_only`. An earlier owner requirement says a missing Structural setup must block a trade even if scores are high. This conflict is unresolved in source; the package preserves source behavior and marks it for owner review rather than silently modifying Live logic.

## External AI roles and providers

- Mode 1 is intended to gate all AI/LLM paths while keeping Python research alive.
- Mode 2 permits every connected AI integration, not only the signal bot and Admin Bot; individual provider switches still apply.
- Jev is optional. OpenRouter is the current source example adapter; this copy does not claim other provider adapters are implemented.
- A missing/invalid AI response must not become a trade signal or grant Live permission.

## MetaAPI scope

The Codex/Cowork/Cursor bundle uses the source's local MT5 path and does not include MetaAPI credentials or shim integration. A separate OpenClaw/Hermes/ClawHub/Manus bundle is being prepared only after a read-only SDK connection test; see the related research audit. Never distribute the user's `.env` or shared example token.
