<!-- Python Qaunt Trading + AI(LLM) Live Research — Creator: Kanutsanan Pongpanna | Settrade e-Open Account · MTS Gold Futures + MT5 | https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com -->

# Python Quant Trading + AI(LLM) Live Research

**Portable research and trading-system skill for Codex, Cowork, Cursor, and compatible Agent platforms**  
Creator: **Kanutsanan Pongpanna** · [Facebook](https://www.facebook.com/LoveMoneyTH) · [YouTube](https://youtube.com/@lovemoneythofficial)

> **Owner's system identity:** “Python Qaunt Trading + AI(LLM) Live Research — อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา · Settrade e-Open Account · MTS Gold Futures + MT5.” The owner-provided phrase “เทรดในไทยมีกฎหมายรองรับ 100%” is retained as a project identity statement, not independent legal advice or a verified regulatory conclusion. Verify the instrument, broker, product, and applicable rules for your own use.

## Design for different trading styles

Every trader has their own preferences, values, and way of trading; few styles are identical. This system is intentionally customizable. The Agent using it can learn the code structure, explain the workflow in plain language, and help users modify all project-owned parts to fit their own style. The project code is open under MIT and may be extended; external packages, brokers, platforms, and data remain subject to their own terms and licenses. Preserve creator attribution and `LICENSE`.

No trading system can guarantee a profit every day. The included factory settings are a record of the owner's system configuration, not recommended risk levels, investment advice, or a promise of returns.

## Important safety defaults in this distribution copy

- The default mode is **Mode 2 — เทรดร่วมสัญญาณ AI** (`internal_llm_join`). It permits connected AI roles while respecting each provider's separate switch.
- The distribution copy is **not Live-enabled**: `live_enabled=false`.
- `work/AUTO_TRADER_STOP` is present. Do not remove it or enable Live unless the owner explicitly authorizes that action after local setup and testing.
- OpenRouter is disabled and no API keys or `.env` files are included. Jev remains enabled as an optional integration switch, but no credential is bundled; without a user-provided key it fails safely as unavailable.
- No orders, account identifiers, or credentials are included. Do not put credentials into source files or research artifacts.
- Factory restore in this copy restores the safe overlay, not the original machine's permission to trade.

## One platform Agent can serve all three roles

The main Agent available in each user's platform takes the **Hermes** role (coordinator). That same Agent can also act as the **Mode-2 signal bot** and the **Admin Bot**, loading the matching role brief and following its task-specific boundaries. Separate Agent products or three independent bots are not required. “Hermes” names the role; it does not require installing the Hermes product. A platform-specific scheduler/CLI integration is a separate adapter and is not assumed to exist merely because the role is portable.

| Role | Primary source of instructions | Authority boundary |
|---|---|---|
| Coordinator / Hermes role | `SKILL.md`, `AGENTS.md` | Inspect, explain, route, and report; do not infer Live permission |
| Mode-2 signal bot | `agents/brief_mode2.md` | Produce the defined analysis/recommendation; never submit MT5 orders |
| Admin Bot | `agents/brief_admin.md` | Use only allowed admin commands; cannot grant Live permission or clear STOP on its own |

## Trading modes

| Mode | What remains active | AI access |
|---|---|---|
| **1 — เทรดด้วยสัญญาณภายใน** (`internal_only`) | Python trading + internal Python research | All connected AI/LLM callsites must be blocked |
| **2 — เทรดร่วมสัญญาณ AI** (`internal_llm_join`) — default | Same Python trading and research | All connected AI integrations are allowed, not only Mode-2 bot/Admin Bot; each provider's own switch and credentials still control whether it actually runs |

Mode 2 is permission for configured AI integrations to participate, not forced provider activation. Python remains the trading decision/execution path in this source. Jev is optional; the current project contains an OpenRouter example adapter, not a ready-made set of arbitrary provider adapters. If Jev is unavailable, continue without Jev and never invent a directional signal from its absence.

## System structure and processing flow

```text
MT5 market/account data
        ↓
market clock + market analyzer + closed-bar frames
        ↓
6 Python strategy agents × Buy/Sell = 12 directional candidates
        ↓
raw score + probability + weighted score
        ↓
bounded governance / ranking / side-net / Stage-3 routing
        ↓
analyze current position and run cut-loss/profit-exit/reversal management
        ↓
wait for broker position state to confirm closures
        ↓
risk/permission checks → request build → MT5 order_check → send only if Live is enabled
        ↓
audit/state → adaptive shadow research and threshold update for a later cycle
```

1. `auto_trader.py` runs on the configured cycle (factory: 60 seconds), connects to MT5, refreshes closed-trade state, and prepares chart/adaptive inputs.
2. `strategy_engine.py` builds trend/range/volatility summaries and six independent strategy agents: Trend, Range, Mean Reversion, Counter-Trend, Breakout, Breakout Reversal. Each has Buy/Sell signals and raw, probability, and weighted metrics.
3. Strategy routing applies configured enable flags, score/probability/weighted bounds, directional and strategy weights, probability ranking, side-net/Stage-3 logic, and records decision evidence. These metrics are not statistically calibrated probabilities unless independently validated as such.
4. In the same cycle, `auto_trader.py` evaluates the existing position before deciding whether a new order may proceed; if a close is sent, it waits for MT5's position state before continuing. The current source also has a profitable-opposite-signal hedge exception; see the known discrepancy below.
5. New orders require the risk gate, a constructed SL/TP request, `order_check`, Live configuration, and terminal/account permission. `live_executor.py` is a separate two-phase prepare/confirm execution path. The default distribution copy disables Live and keeps STOP present.
6. `bounded_adaptive_research.py`, `adaptive_shadow.py`, and `auto_threshold.py` record/review candidates and adapt thresholds for future cycles. Research/adaptation is not evidence of future profit and must avoid look-ahead bias.
7. The Mode-2 signal bot and Admin Bot pass through briefs/recommendation/admin contracts. They are Agent roles and do not themselves replace Python execution controls.

### Source discrepancies to review before enabling Live

- **Structural setup:** factory `structural_mode` is `diagnostic_only`. The current Python source can allow a score/probability-qualified candidate without structural setup, while an earlier owner requirement says structural setup must be present. Packaging does not alter this production rule.
- **Opposite-direction positions:** current code may keep an already-profitable old position and allow a second hedge if fewer than two positions are open. This conflicts with the owner's repeated request to close the old position on any opposite signal. The distribution does not silently change this behavior.
- These are disclosed source conflicts, not claims that the behavior is correct. Review `docs/CURRENT-SYSTEM-REVIEW.md` before any Live use.

## Factory defaults captured from the source snapshot

Source factory snapshot: `work/factory/config/auto_config.factory.json`, created 2026-09-23. Values below are exact defaults from that snapshot except where marked as a distribution safety overlay. They are not recommendations.

| Variable | Source factory | Distribution copy |
|---|---:|---:|
| `live_enabled` | `true` | **`false`** (safety overlay) |
| `symbol` | `XAUUSD.sml` | `XAUUSD.sml` (verify broker symbol) |
| `volume` | `0.001` | `0.001` (verify broker minimum/step) |
| `magic` | `8252026` | `8252026` |
| `poll_seconds` / `position_monitor_seconds` | `60 / 60` | `60 / 60` |
| `max_risk_pct` / `daily_loss_limit_pct` | `8.0 / 20.0` | `8.0 / 20.0` (high; review before any Live use) |
| `max_spread` | `0.6` | `0.6` |
| `cooldown_minutes` / `max_consecutive_losses` | `0 / 0` | `0 / 0` |
| `atr_stop_multiplier` / `min_reward_risk` | `1.2 / 1.3` | `1.2 / 1.3` |
| `enforce_equal_tp_sl` | `false` | `false` |
| profit exit (`enabled`, `minimum_profit_usd`, `no_signal_tp_fraction`) | `true`, `$0.00`, `0.8` | same |
| early cut (`enabled`, `only_losing`) | `true`, `true` | same |
| revenge guard (`enabled`, `cooldown_minutes`, `score_margin`) | `true`, `15`, `0.05` | same |
| `strategy_router.bounded_live.structural_mode` | `diagnostic_only` | same; known discrepancy above |
| `openrouter.enabled` | `false` | **`false`**; no key file included |
| Jev | `enabled=true` in source snapshot | `enabled=true`; optional, with no credential or machine-local key path bundled |
| default mode | `internal_llm_join` | `internal_llm_join` |
| kill switch | source machine state | `work/AUTO_TRADER_STOP` is present |

### Directional governance bands (12 directions × raw/probability/weighted)

Each cell is the configured `[minimum, maximum]` interval in the source factory's directional governance. The copy preserves these bands; any automatic updates from market/trade history remain runtime behavior.

| Candidate | Raw score | Probability | Weighted score |
|---|---:|---:|---:|
| Trend Buy | `[0.422, 0.522]` | `[0.58, 0.85]` | `[0.422, 0.522]` |
| Trend Sell | `[0.430, 0.530]` | `[0.58, 0.85]` | `[0.430, 0.530]` |
| Range Buy | `[0.430, 0.530]` | `[0.53, 0.75]` | `[0.430, 0.530]` |
| Range Sell | `[0.439, 0.539]` | `[0.53, 0.75]` | `[0.439, 0.539]` |
| Mean Reversion Buy | `[0.430, 0.530]` | `[0.56, 0.75]` | `[0.430, 0.530]` |
| Mean Reversion Sell | `[0.430, 0.530]` | `[0.56, 0.75]` | `[0.430, 0.530]` |
| Counter-Trend Buy | `[0.430, 0.530]` | `[0.58, 0.78]` | `[0.430, 0.530]` |
| Counter-Trend Sell | `[0.430, 0.530]` | `[0.58, 0.78]` | `[0.430, 0.530]` |
| Breakout Buy | `[0.440, 0.540]` | `[0.60, 0.88]` | `[0.440, 0.540]` |
| Breakout Sell | `[0.440, 0.540]` | `[0.60, 0.88]` | `[0.440, 0.540]` |
| Breakout Reversal Buy | `[0.430, 0.530]` | `[0.60, 0.85]` | `[0.430, 0.530]` |
| Breakout Reversal Sell | `[0.430, 0.530]` | `[0.60, 0.85]` | `[0.430, 0.530]` |

Other source factory strategy weights: Trend `0.85`, Range `1.20`, Mean Reversion `0.85`, Counter-Trend `0.95`, Breakout `1.10`, Breakout Reversal `1.00`; directional weights begin at `1.0`; `ranking_priority=weight`. Automatic threshold defaults include hybrid mode, 180 records, 60th/90th percentiles, 30 minimum samples per strategy, 0.02 minimum change, and minimum band width 0.10. See the bundled JSON for the full schema and per-strategy stop/reward settings.

## Bundle contents

- `outputs/mt5_python_bridge/`: current Python/MT5 bridge, strategy, trading, risk, audit, mode, Jev, and tests.
- `agents/`: Mode-2 and Admin role briefs, runner, and registry.
- `research/`: **complete project research archive**, including current audit notes and historical investigations.
- `docs/`, `AGENTS.md`, `BRANDING.md`, `คู่มือผู้ดูแลระบบ.md`: operational/project context.
- `work/factory/`: factory restore tool and source factory configuration/code snapshot, sanitized for this distribution.
- `.agents/skills/pytron-mt5-quant-trading/SKILL.md`: project-local Agent skill entry point.
- `.cursor/skills/pytron-mt5-quant-trading/SKILL.md`: Cursor entry point mirroring the portable root skill.

This package includes all 567 current research files. To make the archive portable and safer for public distribution, machine-specific absolute workspace/home paths in text research notes are normalized to `<PROJECT_ROOT>` / `<USER_HOME>` placeholders; research filenames and substantive history are preserved. It does not include `.env` files, DPAPI keys, account logs, positions, trade-history runtime logs, local cron definitions, caches, or virtual environments.

## Use in Codex, Cowork, Cursor

This bundle includes the root `SKILL.md`, a project-local `.agents/skills/` entry point, and Cursor's `.cursor/skills/` entry point. Cowork can use the root instructions in the selected project folder or the product's current skill-import workflow. Product availability, upload method, and workspace policy can differ; the primary Agent can also read `SKILL.md` directly from this project directory.

This is a full project-and-research distribution, not a single hosted skill upload. OpenAI's hosted Skills API currently limits a skill version to 500 files, while this complete archive contains more than that; install the project locally and use its project-local entry point rather than uploading this entire ZIP as one hosted skill. See the [official Skills guide](https://developers.openai.com/api/docs/guides/tools-skills) for the current product-specific limits.

To understand or research the system, start with `SKILL.md`, then `AGENTS.md`, then `docs/CURRENT-SYSTEM-REVIEW.md`; follow the relevant `agents/` brief only for that role.

## Local setup and safe validation

1. Use a dedicated Windows machine with MT5 and a demo account. Verify the broker's symbol, contract size, minimum volume, and volume step.
2. Create a private Python virtual environment and install the requirements listed in `outputs/mt5_python_bridge/requirements.txt`. Review third-party licenses first.
3. Keep secrets in local environment variables or a private secret store; never in a tracked file. No `.env` is included.
4. Run the offline unit tests from this folder before connecting to a broker.
5. Keep `live_enabled=false` and `work/AUTO_TRADER_STOP` present for initial verification. A mode switch does not grant execution rights.
6. Test broker reads on demo, then test strategy and position behavior without sending orders. A Live deployment needs an explicit, separate owner decision after all known discrepancies are resolved.

The source identity mentions Settrade e-Open Account / MTS Gold Futures + MT5. This packaged source snapshot is configured for the broker-specific symbol `XAUUSD.sml`; it does not establish a connection to Settrade, MTS, TFEX, or MetaAPI.

## License and risk notice

Project-owned source is MIT-licensed; external components remain under their own terms in `THIRD-PARTY-NOTICES.md`. This is software and research material, not investment advice, not a promise of daily profit, and not a legal opinion. The user is responsible for broker/product eligibility, configuration, and all trading outcomes.
