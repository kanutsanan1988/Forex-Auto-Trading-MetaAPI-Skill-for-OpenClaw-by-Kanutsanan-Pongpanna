---
name: pytron-engine-mt5-algo-trade
description: Use the Python XAUUSD quant engine and research with MetaAPI for MT5, including six agents, directional metrics, and read-only validation.
license: MIT-0
metadata:
  openclaw:
    requires:
      env:
        - METAAPI_TOKEN
        - METAAPI_ACCOUNT_ID
      bins:
        - python3
    primaryEnv: METAAPI_TOKEN
    emoji: "🏅"
    homepage: https://github.com/kanutsanan1988/Forex-Auto-Trading-MetaAPI-Skill-for-OpenClaw-by-Kanutsanan-Pongpanna
---

<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100% — owner-provided product identity, not legal verification
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  Creator: Kanutsanan Pongpanna — preserve this credit
-->

# Pytron Engine MT5 Algo Trade

Use this skill to inspect, explain, research, or carefully adapt the bundled Python quant-trading system. The package includes the complete current source snapshot, its research history, a MetaAPI compatibility bridge, the MetaAPI Python SDK wheel, offline tests, and read-only validation tools.

## First principles

- The user's platform Agent is the **Hermes/coordinator role**. The same Agent may also take the Mode-2 signal-bot and Admin Bot roles by following `trading-system/agents/brief_mode2.md` and `trading-system/agents/brief_admin.md`. Do not assume separate Agent products or CLI tools exist.
- Mode 1 (`internal_only`) uses the Python engine and internal research without AI/LLM call sites. Mode 2 (`internal_llm_join`) is the default and permits all user-configured AI integrations, subject to each provider's own switch and credentials.
- Jev is optional. OpenRouter is one example, not required. If Jev is unavailable, continue without it; never invent a signal.
- Python owns trading decisions and MT5 execution controls. An Agent may inspect and recommend within its role, but it must not bypass Python guardrails, send broker orders, clear the Kill Switch, or grant itself Live permission.
- Different traders have different styles. Explain the system clearly and help each user customize project-owned code/settings to their preferences. Preserve creator credit and all third-party license notices.
- Never promise daily profit or describe the owner's Thailand/legal product phrase as independently verified legal advice.

## Safe startup procedure

1. Read `README.md`, then `trading-system/README.md` for the system flow and exact factory values.
2. Confirm `trading-system/work/AUTO_TRADER_STOP` is present and distribution `live_enabled` is `false`. Never remove or override either during inspection.
3. For MetaAPI, install `requirements-metaapi.txt` and the bundled SDK wheel from `vendor/`. Do not install the Windows-native `MetaTrader5` package on a MetaAPI host.
4. Keep `METAAPI_TOKEN` and `METAAPI_ACCOUNT_ID` in the user's own secret manager/environment. Do not print, echo, log, copy, or publish them.
5. Run `python scripts/verify_package.py --deep`, then `python scripts/metaapi_connect_check.py`, then `python scripts/metaapi_engine_smoke.py`. These are read-only checks. A connection/read pass is not live-order certification.
6. Before suggesting a code change, inspect current code, tests, factory values, `trading-system/docs/CURRENT-SYSTEM-REVIEW.md`, and the latest research status. Separate observed behavior from owner requirements and research hypotheses. Do not change live decision rules unless the owner explicitly asks.

## Current system map

`trading-system/outputs/mt5_python_bridge/auto_trader.py` orchestrates the one-minute cycle and position management. `strategy_engine.py` scores six Python strategy agents in Buy/Sell directions (12 candidates), each with raw score, probability, and weighted score. Routing and configured gates choose a candidate or abstain. Existing-position management precedes new order processing. Audit/state and adaptive research record outcomes for later cycles. Mode-2/Admin Agent roles use the briefs and constrained recommendation/admin interfaces under `trading-system/agents/` and `tools/`.

The MetaAPI bridge in `metaapi/metaapi_mt5_shim.py` adapts the MetaTrader5 Python API for the bundled engine. It does not own strategy logic. Read `references/portability.md` for tested API differences and unsupported behavior.

## Commands

```bash
python scripts/verify_package.py --deep
python scripts/metaapi_connect_check.py
python scripts/metaapi_engine_smoke.py
python -m unittest metaapi.test_shim_offline
```

The bundled system begins stopped with Live disabled. Do not turn on trading as part of setup or research. Never assume a read-only pass certifies order sends, fills, stops, closes, or live reconciliation.

## Research workflow

All source research is under `trading-system/research/`. Start with its `README.md`, `SESSION-STATE.md`, and the latest dated review. Preserve historical artifacts; add new dated append-only findings that identify data scope, method, result, limitations, and any decision explicitly left to the owner. Prevent look-ahead leakage and keep research recommendations separate from Production decisions unless an authorized, tested release process is explicitly requested.
