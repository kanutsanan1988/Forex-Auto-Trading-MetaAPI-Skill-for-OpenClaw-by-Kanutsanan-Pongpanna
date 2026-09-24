# MetaAPI read-only validation — 2026-09-24

Creator: Kanutsanan Pongpanna  
Date: 2026-09-24 (Asia/Bangkok)  
Scope: verify the current local MetaAPI credential pair and the bundled Python engine's read path. This is a read-only validation, not live-order certification.

## Result

- The local validation loaded credentials from the user-designated `.env` file after clearing inherited process-level MetaAPI variables in the isolated child process. Values were not printed or retained in this report.
- MetaAPI account lookup and deployed-state confirmation succeeded. The RPC connection synchronized successfully.
- Read-only account, open-position, and pending-order queries succeeded; symbol specifications were received.
- Historical bars were returned for M1, M5, M15, and H1 (320 bars requested/received per timeframe in the preflight harness).
- The distribution engine smoke then passed through the MetaAPI shim: 261 bars per timeframe, the current Python frame builder and strategy decision path, and a local read-only guard probe that blocked the shim's `order_send` call before any trade RPC.
- No deploy, undeploy, order-send, close-position, modify-position, or other trade RPC was called.
- The sanitized preflight status is `connected_read_only`; `integration_certified` remains `false` because no order-execution lifecycle was tested.

## Interpretation and limits

This supersedes the earlier same-day credential-retake note's unsuccessful result. The earlier failure was caused by a stale inherited process token taking precedence; clearing inherited variables allowed the `.env` pair to reach the intended account successfully. The first engine smoke also exposed two packaging integration requirements: the bar adapter must anchor MetaAPI history queries at the current UTC time when implementing MT5's "latest bars" call, and the MetaAPI host needs NumPy to build MT5-compatible structured bars. Both are addressed in the distribution copy; Python strategy, risk, and order-decision rules were not changed.

The successful read proves only the tested SDK/account/RPC and market-data read path. It does **not** prove that MetaAPI order requests, fills, SL/TP handling, close confirmation, retries, or live position reconciliation match native MT5 behavior. The distribution copy therefore remains stopped with Live disabled, and its docs must not describe real order execution as certified.

No account UUID, login, token, balances, equity, quotes, or raw candle prices are published in this record. The credential file remains local and must not be included in either distribution ZIP.

## Reproducibility boundary

The validation ran on the Windows host using the official `metaapi-cloud-sdk` Python SDK version `29.1.1`, NumPy `2.4.6` in an isolated validation environment, the distribution MetaAPI compatibility bridge, and an isolated read-only harness. The POSIX lock branch and a full install/run on Linux/cloud were not exercised. It did not execute the user-supplied example that can deploy accounts or place a sample order.

The current result is also captured in `release/metaapi-validation-local/preflight-result.json`; that local file is sanitized and must still be reviewed by the package secret scanner before redistribution.
