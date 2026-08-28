---
name: kanatsanan-metaapi-trading
description: Connect Kanatsanan's guarded MT4/MT5 trading workflow to a user's MetaAPI account for market analysis, monitoring, and explicitly authorized order execution.
metadata:
  openclaw:
    requires:
      env:
        - METAAPI_TOKEN
        - METAAPI_ACCOUNT_ID
      bins:
        - python3
    primaryEnv: METAAPI_TOKEN
    envVars:
      - name: METAAPI_TOKEN
        required: true
        description: MetaAPI API token. Keep it in the local OpenClaw secret store or environment; never put it in SKILL.md.
      - name: METAAPI_ACCOUNT_ID
        required: true
        description: MetaAPI trading account UUID.
    install:
      - kind: uv
        package: metaapi-cloud-sdk
        bins: [python3]
    emoji: "📈"
    homepage: https://metaapi.cloud/
---

# Kanatsanan MetaAPI Trading

Use `scripts/metaapi_trading.py` as the only execution entrypoint. It connects to the MetaAPI RPC API using `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID`, deploys/waits for the account only when needed, and emits JSON suitable for OpenClaw to summarize.

## Commands

Run from this skill directory:

```bash
python3 scripts/metaapi_trading.py status
python3 scripts/metaapi_trading.py snapshot --symbol XAUUSD
python3 scripts/metaapi_trading.py candles --symbol XAUUSD --timeframe M5 --limit 300
python3 scripts/metaapi_trading.py analyze --symbol XAUUSD
python3 scripts/metaapi_trading.py positions
python3 scripts/metaapi_trading.py orders
python3 scripts/metaapi_trading.py history --days 30
```

`analyze` uses the bundled Kanatsanan multi-timeframe strategy engine on closed M1/M5/M15/H1 candles. It is read-only and must be preferred before any order operation. Analysis, backtest-like inspection, and status output are not profit guarantees or financial advice.

## Live trading boundary

- Read-only commands never send orders.
- Never ask the user to paste the token into chat or write it into a file tracked by Git. The user supplies it through the local environment/secret manager. The MetaAPI account credential configuration page is `https://app.metaapi.cloud/configure-trading-account-credentials/<ACCOUNT_ID>`.
- Treat `METAAPI_ACCOUNT_ID` as an opaque UUID; do not confuse it with the broker login.
- Before a live order, show symbol, side, volume, entry, stop loss, take profit, spread, account equity, and the risk checks, then obtain an explicit current-turn confirmation.
- `trade` and `loop --live` require both `--live` and `--confirm-live`; without them they perform a dry run and never send an order.
- Stop or disable live trading immediately when the user asks. Do not silently change account, symbol, volume, stop-loss, take-profit, or risk limits.
- Do not claim that the system is guaranteed, autonomous without supervision, or suitable as financial advice. MetaAPI and broker costs/limits remain the user's responsibility.

## One-shot and loop automation

Use `once` for one guarded analysis/execution cycle. Use `loop` only after the user explicitly asks for ongoing automation and has confirmed the exact account, symbol, volume, risk limits, and live mode. Default is dry-run:

```bash
python3 scripts/metaapi_trading.py once --symbol XAUUSD --volume 0.01
python3 scripts/metaapi_trading.py loop --symbol XAUUSD --interval 60
python3 scripts/metaapi_trading.py loop --symbol XAUUSD --interval 60 --live --confirm-live
```

The loop skips a new entry when a position already exists for the symbol, rejects excessive spread, requires a strategy decision with stop-loss/take-profit, and rechecks account trade permission immediately before sending. It is intentionally a one-position-per-symbol guard, not a promise of unattended risk management.

## Extending the skill

The strategy code is local to this bundle and may be edited by the skill owner. Preserve the JSON interface, closed-candle rule, explicit live confirmation, and credential isolation when changing it. Test changes with:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
python3 scripts/metaapi_trading.py --help
```

For ClawHub publishing, from the parent directory run `clawhub skill publish ./kanatsanan-metaapi-trading --slug kanatsanan-metaapi-trading --version 1.0.0`. Review the security scan before sharing the published slug.
