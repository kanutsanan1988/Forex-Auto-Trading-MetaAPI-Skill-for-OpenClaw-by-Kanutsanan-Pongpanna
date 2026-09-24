<!-- Python Qaunt Trading + AI(LLM) Live Research | Creator: Kanutsanan Pongpanna | Settrade e-Open Account · MTS Gold Futures + MT5 -->

# Install and validate this copy

## Skill usage

The skill is the root `SKILL.md`. Codex gets a project-local entry point at `.agents/skills/pytron-mt5-quant-trading/SKILL.md`; Cursor gets `.cursor/skills/pytron-mt5-quant-trading/SKILL.md`. Cowork can read the root skill from the selected project folder or use the product's current import flow. Do not assume an Agent role automatically installs a platform or scheduler.

## Python/MT5 source

This source path targets a Windows host with MetaTrader 5 installed and a broker-compatible terminal/symbol. The package is shipped stopped and not Live-enabled.

1. Review `LICENSE`, `THIRD-PARTY-NOTICES.md`, and broker/product availability.
2. Create a private virtual environment and install dependencies from `outputs/mt5_python_bridge/requirements.txt`.
3. Confirm the broker symbol and volume constraints before changing config. `XAUUSD.sml` and `0.001` are source defaults, not portable assumptions.
4. Keep `live_enabled=false` and `work/AUTO_TRADER_STOP` present during review.
5. Run offline tests only. Do not use test utilities that send orders against a live account.
6. If a future owner-authorized test requires a broker, use demo/read-only access first. Store secrets outside tracked files and never paste them into an Agent conversation.

## Factory restore

`work/factory/restore_factory.py` has dry-run behavior by default. This distribution has a safety overlay: Live is disabled, OpenRouter is off, Jev has no credential configured, and STOP is included. Factory restore is not a request or authorization to start trading.
