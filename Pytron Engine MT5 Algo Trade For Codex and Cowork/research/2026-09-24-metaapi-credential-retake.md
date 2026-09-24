# MetaAPI validation retake after credential rotation

Creator: Kanutsanan Pongpanna  
Date: 2026-09-24 (Asia/Bangkok)  
Scope: credential-source diagnosis and read-only MetaAPI preflight only. No account changes or trading requests.

## Latest user-provided SDK sample

- The separately supplied `example.py` reads `TOKEN` and `ACCOUNT_ID` from environment variables; unlike the earlier ZIP snapshot, this current file did not contain a hard-coded JWT when inspected.
- The example is still not a read-only validation script: on its normal path it may deploy an account, prints account and trading-history payloads, submits `create_limit_buy_order()` for GBPUSD, and may undeploy afterward. It was inspected but never executed.
- `requirements.txt` requests `metaapi-cloud-sdk>=28.0.0`. The isolated local validation environment currently reports SDK `29.1.1`.
- The MetaApi SDK has its own license/terms, distinct from this project’s MIT license. Any vendored SDK copy must preserve the SDK license and applicable MetaApi terms; do not label the SDK as MIT merely because the host project is MIT.

## Credential-source finding

Only presence/equality checks were emitted; token and account-ID values were never printed or added to this report.

- The validation `.env` contains non-empty token and account-ID entries.
- The process environment also contains both entries; the process token does not equal the `.env` token, while the process account ID equals the `.env` account ID. The preflight reader gives process environment precedence over `.env`.
- The first preflight, with process precedence, ended at account lookup with `UnauthorizedException`.
- A second preflight ran after removing only the three MetaAPI variables from that child process, so the script loaded `.env`. The MetaApi WebSocket reached both configured region replicas, but the configured `get_account()` call returned `NotFoundException`. No RPC account, position, or order data was read after that failure.
- No `deploy`, `undeploy`, `order_send`, `create_limit_buy_order`, or close-position method was called.

## Gate and next action

The latest post-rotation preflight is not a successful account connection. A stale process-level token is demonstrably overriding the local file for normal launches; after bypassing that override, the token/account-ID pair from `.env` still does not resolve the configured account. Confirm that the token and account ID belong together in MetaApi and remove or update the stale process-level token before repeating the same read-only check. Do not build or claim a verified MetaAPI-to-trader integration until `get_account`, deployed-state confirmation, RPC synchronization, account/position/order reads, symbol specifications, and closed-bar history checks all pass without any trade call.

## References

- Official Python SDK: https://github.com/metaapi/metaapi-python-sdk
- SDK license: https://github.com/metaapi/metaapi-python-sdk/blob/main/LICENSE
- Official client documentation: https://metaapi.cloud/docs/client/
