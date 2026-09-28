<!-- Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna -->

# MetaAPI read-only validation — 2026-09-28

Creator: Kanutsanan Pongpanna  
Date: 2026-09-28 (Asia/Bangkok)  
Scope: read-only validation of the user-designated local MetaAPI credentials and the bundled Python engine path. This is not live-order certification.

## Result

- The local validation used credentials from the user-designated local `.env`; credential values were not printed or retained in this report or the package.
- SDK `29.1.1` account lookup, deployed-state confirmation, RPC synchronization, account/position/pending-order reads, and XAUUSD.sml symbol specification succeeded.
- The direct read-only check returned 20 M1 historical bars. The packaged engine smoke read 261 bars each for M1, M5, M15, and H1, built all four frames, and evaluated the Python strategy path.
- The distribution config had `live_enabled=false`; the shim reported read-only, and its local `order_send` guard blocked the safety probe before any broker order RPC.
- No deploy, undeploy, order, close, modify, or other trade RPC was called. Both checks returned successful read-only statuses.

## Interpretation and limits

This confirms the tested account/RPC and market-data read path on this Windows host. It does **not** certify order placement, fills, SL/TP handling, close confirmation, retries, or live position reconciliation. The distributable therefore remains Live-disabled and has `work/AUTO_TRADER_STOP` present.

No account UUID, broker login, token, balance, equity, quote, or raw candle price is included here. SDK diagnostics are redacted before display. Review source-news/data redistribution rights and privacy before publishing the complete research archive.

## Reproducibility boundary

The test used the bundled SDK `29.1.1` wheel and an isolated local Python validation environment. It exercised no broker trade RPC and did not certify a clean install on Linux/Cowork, OpenClaw, Hermes, ClawHub, or Manus. The evidence JSON is `metaapi/evidence/live-readonly-verify-20260928.json`.
