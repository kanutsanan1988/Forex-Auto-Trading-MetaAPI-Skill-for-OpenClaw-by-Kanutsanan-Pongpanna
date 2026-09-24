<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100% — owner-provided product identity, not verified legal advice
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  Creator: Kanutsanan Pongpanna — preserve this credit
-->

# Pytron Engine — MetaAPI MT5 Quant Trading

**Creator:** คณัสนันท์ พงษ์พันนา (Kanutsanan Pongpanna) · [Facebook](https://www.facebook.com/LoveMoneyTH) · [YouTube](https://youtube.com/@LoveMoneyTHOfficial)

> **A trader's style is personal.** Every trader has their own preferences, values, and path; few trade in exactly the same way. This open-code system is designed for each user to adapt to their own style. Users may ask their chosen AI agent to learn the structure, explain it in plain language, and customize project-owned code and settings to suit them. The system can be extended freely under the applicable licenses. Preserve creator credit and third-party notices.

> **Risk and legal notice:** no system can guarantee daily profit. The phrase “เทรดในไทยมีกฎหมายรองรับ 100%” is retained as the owner's product identity, not independent legal or regulatory verification. XAUUSD/MT5 is not automatically equivalent to Thai TFEX Gold Futures. Verify the actual broker, instrument, permissions, costs, taxes, and applicable rules yourself.

## Contents

- `trading-system/` — full Python trading engine, role briefs, tools, factory defaults, tests, and the complete project research archive.
- `metaapi/` — MetaAPI-to-MetaTrader5 compatibility bridge and offline tests.
- `vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl` — the MetaAPI SDK requested for this portable package. Its separate license is in `metaapi/METAAPI-SDK-LICENSE.txt`.
- `references/` — architecture, modes, operations, research, and portability notes.
- `scripts/` — package verification and read-only MetaAPI connection/engine checks.
- `QC/` — two independent, portable package-QC scripts.

The full system flow, source factory defaults, and 12 directional score/probability/weighted threshold bands are documented in [`trading-system/README.md`](trading-system/README.md). Read it before operating or adapting the system.

The research archive is included at the owner's request. It contains historical check/trade research inputs; inspect privacy and third-party source rights before uploading this ZIP publicly. Current credentials and live runtime state are excluded.

## Modes and Agent roles

| Mode | Meaning |
|---|---|
| `internal_only` — **เทรดด้วยสัญญาณภายใน** | Python engine and internal Python research only; all AI/LLM call sites are disabled. |
| `internal_llm_join` — **เทรดร่วมสัญญาณ AI** (default) | Same Python engine plus any AI integrations enabled and configured by the user. |

The main Agent supplied by the user's platform acts as the **Hermes/coordinator role**. That same Agent may also perform the Mode-2 signal-bot role and Admin Bot role by following their separate briefs. Hermes does not require installing a product named Hermes, and three separate agents are not required. Each provider still needs its own configuration and permission.

Jev is optional. OpenRouter is an example connection method, not a required dependency; users may connect Jev another way or run without Jev. Missing AI output must never be fabricated as a directional signal. Python remains the system's trading decision/execution path.

## Factory and distribution safety

The source factory values are recorded in `trading-system/work/factory/config/auto_config.factory.json` and explained in `trading-system/README.md`. Important distribution defaults:

| Setting | Included value |
|---|---|
| Default mode | `internal_llm_join` |
| `live_enabled` | `false` in the distribution copy |
| `work/AUTO_TRADER_STOP` | present — starts stopped |
| OpenRouter | disabled; no key or `.env` bundled |
| MetaAPI | read-only checks by default; no credentials bundled |

The **source factory** may differ from this safe distribution overlay. Values are records of the owner's snapshot, not recommended risk settings. Review the full table before use. Factory restore does not grant Live permission or remove the Kill Switch.

## MetaAPI setup and read-only validation

Use Python 3.8 or newer in a virtual environment. Install the bundled SDK wheel (do not install the native Windows-only `MetaTrader5` package for a MetaAPI deployment):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-metaapi.txt
python -m pip install vendor/metaapi_cloud_sdk-29.1.1-py3-none-any.whl
```

On Windows, activate `.venv\Scripts\Activate.ps1` instead. Store your own `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in a secret manager or process environment; never put them in chat, source, research, or a published `.env` file. The account must already be deployed by its owner; these checks never deploy or undeploy it.

```bash
python scripts/verify_package.py --deep
python scripts/metaapi_connect_check.py
python scripts/metaapi_engine_smoke.py
```

These checks only read account state, symbol specifications, and market bars. The connection report omits login, balances, equity, quotes, and account/position counts. The engine smoke follows the bundled Python market-frame and strategy-decision path while the local shim refuses its safety-probe order call. It does **not** send an order to MetaAPI.

### What was verified for this build

On 2026-09-24, from the Windows validation host, SDK `29.1.1` completed an authenticated read-only connection using the owner's local credential store: account lookup, deployed-state confirmation, RPC synchronization, account/position/order reads, symbol specification, and M1/M5/M15/H1 history. Credentials, account UUID, prices, balances, and equity are not included here. No deploy, undeploy, order, close, or modify RPC was called. See [`trading-system/research/2026-09-24-metaapi-readonly-validation.md`](trading-system/research/2026-09-24-metaapi-readonly-validation.md).

This confirms the tested read path only. **Live order execution and full position-lifecycle parity are not certified.** The package remains stopped and Live-disabled; do not remove the stop file or enable live trading based on this connection check.

For a MetaAPI host without native Windows MT5, the distribution copy supplies a small process-lock adapter for Windows/POSIX compatibility and installs NumPy for MT5-compatible bar arrays. These packaging changes do not alter Python strategy, risk, or routing decisions in the source snapshot.

The MetaAPI read-only integration was exercised on the Windows validation host. The POSIX lock branch and a complete install/run on Linux or another cloud host were not exercised in this build; treat that as a portability item still requiring validation.

## License boundaries

- Package skill wrapper and ClawHub metadata: **MIT-0** (`LICENSE`).
- Project-owned trading system and research code: **MIT** (`trading-system/LICENSE`).
- Bundled MetaAPI SDK: governed by the included `metaapi/METAAPI-SDK-LICENSE.txt`, not MIT/MIT-0. It may be used only under its applicable MetaAPI terms.
- All other third-party services/data remain subject to their owners' licenses and terms; see `THIRD-PARTY-NOTICES.md`.

## Before any real trading

Read `references/operations.md`, `references/portability.md`, and the current system review in `trading-system/docs/`. Inspect the exact broker symbol and costs, verify order/close behavior on a demo account, and make your own risk decision. A read-only MetaAPI pass does not authorize live use.
