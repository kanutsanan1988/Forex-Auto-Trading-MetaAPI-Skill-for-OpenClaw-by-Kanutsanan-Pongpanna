<!-- Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna. Settrade e-Open Account · MTS Gold Futures + MT5. https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com -->

# Portability and MetaAPI compatibility

## Scope

The engine uses the MetaTrader5 Python API. On a host without an installed MT5 terminal, `metaapi/metaapi_mt5_shim.py` provides a compatibility layer backed by MetaAPI. It is an adapter, not a strategy agent. Use Python 3.8+ and the SDK wheel included in `vendor/`; do not install the native, Windows-specific `MetaTrader5` package for a MetaAPI host.

## Tested read-only path

On 2026-09-24, from the Windows validation host, the bundled MetaAPI SDK `29.1.1` and compatibility shim passed an authenticated read-only check against the configured MetaAPI account. The check confirmed account lookup/deployed state, RPC synchronization, account/positions/orders reads, symbol specification, and M1/M5/M15/H1 history. The full engine smoke harness built the engine's market frames and ran its Python decision function with the shim in read-only mode. A Linux/cloud-host installation was not exercised in this build; the POSIX lock branch remains unverified here.

No account UUID, login, credentials, balances, equity, quote, or raw candle price is published in the evidence. No deploy, undeploy, order, close, or modify RPC was called. The report status is `connected_read_only`; the integration remains **not certified for live order execution**. See `trading-system/research/2026-09-24-metaapi-readonly-validation.md`.

## Known API differences and limits

| Area | Compatibility behavior / limit |
|---|---|
| Credentials | Read from `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in the process environment. Never commit or print them. |
| Account state | Connection checks require the account to already be deployed by its owner. The bridge/checks never deploy or undeploy. |
| Read-only control | `METAAPI_SHIM_READ_ONLY=1` rejects order-send locally before a trade RPC. Keep it enabled for connection checks and research. |
| Market Watch | MetaAPI has no MT5 Market Watch state; `symbol_select` compatibility is a no-op. |
| `order_check` | Simulated locally from symbol/volume/price/SL/TP/margin data; not an authoritative broker pre-check. |
| Spread/specification | Some broker-specific fields are not supplied with MT5 semantics; inspect the adapter and validate against a demo account before any execution. |
| Margin / time / historical bars | Conversion and pagination are implemented in the shim, but broker-specific behavior and historical-bar alignment still require verification for each account/instrument. |
| Live execution lifecycle | No real order-send, fill, SL/TP modification, close confirmation, ambiguous-send retry, or reconciliation was tested in this release. Do not treat read validation as trade validation. |
| Current engine portability | The distribution includes a copy of the current engine. Review `trading-system/docs/CURRENT-SYSTEM-REVIEW.md` for source-level discrepancies before enabling any real execution. |

## Safe setup on another machine

1. Verify the ZIP and copy `trading-system/` to a user-owned writable folder; do not run from a skill cache directory.
2. Create a virtual environment, install `requirements-metaapi.txt`, then install `vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl`.
3. Set `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` through that machine's own secret store/environment. No `.env` or credentials are included.
4. Run `scripts/verify_package.py --deep`, then `scripts/metaapi_connect_check.py`, then `scripts/metaapi_engine_smoke.py`.
5. Keep `work/AUTO_TRADER_STOP` present and `live_enabled=false` until the account owner independently approves and validates a full execution lifecycle on an appropriate demo environment.

## AI/platform compatibility

The platform's main Agent can play the Hermes/coordinator role and can take the Mode-2 or Admin Bot role from its corresponding brief. This does not require the Hermes product or separate headless CLIs. OpenClaw, Manus, Codex, Cowork, Cursor, and other platforms can use the documented role contracts where their own file/shell permissions allow. Jev/OpenRouter are optional integrations; missing AI connectivity must not be treated as a trade signal.
