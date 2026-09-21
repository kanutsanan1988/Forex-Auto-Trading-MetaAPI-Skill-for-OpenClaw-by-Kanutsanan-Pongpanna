---
name: pytron-engine-mt5-algo-trade
description: "Operate the bundled Python gold (XAUUSD) quant trading engine over MetaAPI — twelve directional strategy scores, threshold bands, position lifecycle, guard gates, AI Signal Bot and Admin Bot brains, plus the full research archive. Ships stopped, not live, with no credentials. Use for this engine and its research; never as generic investment advice."
license: See LICENSE in this package. Creator credit must be preserved.
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
        description: "MetaAPI API token. Put it in your own secret store or environment. Never paste it into chat and never commit it to Git."
      - name: METAAPI_ACCOUNT_ID
        required: true
        description: "MetaAPI trading-account UUID (an opaque UUID, NOT the broker login number)."
    install:
      - kind: uv
        package: metaapi-cloud-sdk
        bins: [python3]
    emoji: "🏅"
    homepage: https://github.com/kanutsanan1988/Forex-Auto-Trading-MetaAPI-Skill-for-OpenClaw-by-Kanutsanan-Pongpanna
---

<!--
  Python Qaunt Trading + AI(LLM) Live Research
  อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
  เทรดในไทยมีกฎหมายรองรับ 100%
  Settrade e-Open Account · MTS Gold Futures + MT5
  https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
  ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
  ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
    Facebook: https://www.facebook.com/LoveMoneyTH
    YouTube:  https://youtube.com/@lovemoneythofficial
  โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
-->

# Pytron Engine — MT5 Algo Trade (OpenClaw · Hermes · clawhub.ai · Manus AI)

This skill bundles a complete, portable gold-trading engine plus its entire research
history, and drives it through **MetaAPI** so it can run on a machine that has **no
MT5 terminal at all** (Linux server, container, someone else's computer).

Everything here is **open code**: read it, explain it, retune it, extend it.

> **Trading style is personal.** Every trader has their own style, preferences, and
> path — almost nobody trades the same way. This system is built so you can adapt
> **every** part of it to your own style. Hand this whole folder to your AI, let it
> learn the structure, explain it in plain language, and re-tune anything you like.
> **100% adjustable · fully open code · unlimited further development.**

Author / Creator: **คณัสนันท์ พงษ์พันนา (Kanutsanan Pongpanna)**
Facebook <https://www.facebook.com/LoveMoneyTH> · YouTube <https://youtube.com/@lovemoneythofficial>

> **คำชี้แจงสำเนาแจกจ่าย:** การเทรดของแต่ละคนมีสไตล์ มีค่านิยมชมชอบ และมีวิถีทางของใครของมัน
> ไม่ค่อยมีใครมีสไตล์ที่เหมือนกันนัก ดังนั้นระบบนี้จึงถูกออกแบบมาให้ผู้ใช้
> **ปรับแต่งระบบให้เข้ากับสไตล์การเทรดของตัวเองได้** ผู้นำไปใช้ทุกคนสามารถให้ AI ที่คุณใช้งานอยู่
> เรียนรู้โครงสร้าง อธิบายระบบนี้ให้เข้าใจง่าย และปรับแต่งระบบได้ทั้งหมดทุกส่วนตามอัธยาศัย
> ของผู้ที่นำไปใช้งานได้แบบ **100%** เป็น **โค้ดระบบเปิด** สามารถ **พัฒนาต่อยอดได้อย่างไร้ขีดจำกัด**

---

## 1) What you received

```
trading-system/                  ← the complete engine (Python) + tools + tests
  outputs/mt5_python_bridge/         the trading engine and its 27 tools / 68 tests
  agents/                            "brain" registry + run_bot.py + job briefs
  research/                          the complete research archive (all history)
  work/factory/                      factory defaults + restore tooling
  work/AUTO_TRADER_STOP              kill switch — shipped PRESENT (system starts stopped)
metaapi/                         ← MetaAPI bridge + evidence of a verified live read
  metaapi_mt5_shim.py                adapter that impersonates the MetaTrader5 API
  test_shim_offline.py               22 offline tests
  evidence/                          live read-only verification (2026-09-21)
references/                      ← architecture · operations · portability · research · modes
scripts/
  verify_package.py                  integrity + secret scan (run this first)
  metaapi_connect_check.py           read-only MetaAPI connection check (your own account)
  metaapi_engine_smoke.py            prove the engine reads real bars through the bridge
.clawhubignore                   ← publish rules for clawhub.ai
README.md                        ← system structure + factory values of initial variables
```

Read [README.md](README.md) for the system map and the **factory table of initial
variable values**, then [references/architecture.md](references/architecture.md).

## 2) Install — and never trade inside the skill folder

1. `python3 scripts/verify_package.py` (add `--deep` to hash every file).
2. Copy `trading-system/` **out** of the skill into a writable working directory,
   e.g. `~/gold-trading/`. The engine writes state, audit logs and the kill switch;
   keep that out of the skill folder so re-publishing stays clean.
3. Set `TRADING_PROJECT_ROOT` to that folder if you did not keep the exact
   `outputs/mt5_python_bridge/` layout. The engine resolves paths from the project
   root and honours this variable first.
4. `pip install -r outputs/mt5_python_bridge/requirements.txt` and
   `pip install metaapi-cloud-sdk` (or use the `uv` entry in the frontmatter above).

**This package starts STOPPED and not live.** `live_enabled` is shipped `false` and
`trading-system/work/AUTO_TRADER_STOP` is present. Nothing trades until *you* decide so
on *your* account.

## 3) MetaAPI: verify the connection before anything else

Credentials come from the **environment only** — this package contains no token and no
account id, and the scripts never write them to disk:

```bash
export METAAPI_TOKEN="..."        # your token
export METAAPI_ACCOUNT_ID="..."   # your MetaAPI account UUID (not the broker login)
```

Then, in order:

```bash
python3 scripts/metaapi_connect_check.py    # read-only: is the account reachable?
python3 scripts/metaapi_engine_smoke.py     # read-only: does the ENGINE read real bars?
```

Both refuse to send orders. Both need the account to already be **DEPLOYED** — they
will report and stop rather than deploy or undeploy anything on your behalf.

The bridge is used exactly like the real package:

```python
import metaapi_mt5_shim as mt5     # instead of: import MetaTrader5 as mt5
```

Verified read-only against a live account on **2026-09-21** — evidence in
`metaapi/evidence/`. See [references/portability.md](references/portability.md) for the
honest list of differences (time offset, margin rate, no Market Watch, simulated
`order_check`, no deploy/undeploy).

**Hosted Linux / container / no Windows terminal:** that is the whole point of this
package — use the MetaAPI bridge. This skill does not claim native MT5 terminal access
from a hosted environment.

## 4) Two trading modes (default = mode 2)

| Mode | Key | What runs |
|---|---|---|
| 1 · Internal signals | `internal_only` | Python only — engine, internal research, tuner, full history. No AI bots. |
| 2 · Join AI signals | `internal_llm_join` | Same Python core **plus** the Mode-2 signal-check bot and the Admin Bot. |

Mode 2 is the **default**. Internal research and tuning stay active in both modes —
mode 1 removes the AI bots, not the research. Names and defaults come from
`runtime_support.MODE_TITLES` / `DEFAULT_MODE`; read them from the code, do not guess.

See [references/modes.md](references/modes.md).

## 5) "Changeable brain" — OpenClaw, Hermes, Manus, or anything else

The engine never knows *which* AI it is talking to. Brains talk to it through files and
shell commands only, so swapping the brain needs **zero** changes to trading code:

- Job briefs: `agents/brief_mode2.md`, `agents/brief_admin.md`
- Data in: `tools/llm_research_packet.py`, `news_feed.py`, `tools/admin_bot_round.py`
- Work back out: `tools/submit_recommendation.py`, `tools/admin_command.py`
- Contract: `research/recommendations/CONTRACT.md` (generated from real code)

```bash
python3 agents/run_bot.py --list          # which brains exist on this machine
python3 agents/run_bot.py --role mode2    # Mode-2 research round
python3 agents/run_bot.py --role admin    # Admin Bot round
python3 agents/sync_briefs.py             # re-sync briefs after editing
```

`agents/registry.json` already ships headless recipes for **OpenClaw**
(`openclaw "<brief>"`), **Hermes** (`hermes -z "<brief>"`), **Manus AI**
(`manus-cli task create --prompt "<brief>"`) and fourteen more. Add another with a
single JSON block (`{{brief_text}}` = full brief text, `{{brief}}` = brief file path).

**Qualification is two abilities only:** run a shell command, and read/write files.
Nearly every agentic AI on the market can do both — which is why it fits here.

## 6) Automated rounds from OpenClaw / Hermes / Manus

Any scheduler that can run a shell command can drive the engine — cron, systemd timer,
Hermes cron jobs, OpenClaw tasks, or a Manus task prompt:

```bash
python3 agents/run_bot.py --role admin                  # Admin Bot, every 30 min
python3 trading-system/outputs/mt5_python_bridge/tools/health_check.py
python3 trading-system/outputs/mt5_python_bridge/tools/system_status.py
```

Every run is recorded in `work/agent_runs.jsonl`, so you can always audit which brain
did what and when. When a bot suggests a change it goes through
`tools/submit_recommendation.py`, then the consumer's **Testing Gate** before anything
is applied.

**Security is enforced by scripts, not by trust** — no brain can bypass the guardrails:

| Guardrail | Enforced by |
|---|---|
| Never touch `live_enabled` · `magic` · `volume` · `symbol` | `consumer` + `admin_command` refuse |
| Never start/stop the trader, never delete the kill switch | no command exists (owner only) |
| Never rewrite code structure | only bounded numeric values may change |
| Values must stay inside bounds | Admin Bot `BOUNDS` + checked on every write |
| Recommendations must pass testing | Testing Gate in the consumer |
| Always restorable to factory | `work/factory/` + `restore_factory.py` |
| Everything auditable | `work/*.jsonl` audit trails |

## 7) Invariants this skill must teach (do not violate)

- Closed bars only; higher timeframes timestamp-aligned.
- **A failed query means UNKNOWN — never "zero positions".** `positions_get` returns
  `None` on failure, deliberately.
- Never open a replacement position until the close is *confirmed*. A timeout means
  wait — it does not mean success.
- Never blindly retry an order whose state is ambiguous (duplicate-order risk).
- Respect `magic` and symbol ownership; never touch another user's positions.
- Recommendations must pass the Testing Gate in the consumer before being applied.
- Mode 1 must never run AI Agent Bots; the Admin Bot must not allow it.
- **The kill switch outranks everything.** Do not delete or bypass it.
- The Admin Bot may tune values inside numeric bounds; it may **never** touch
  `live_enabled`, `magic`, `volume`, or `symbol`, and may not edit code structure.
- The MetaAPI bridge is a *sensory layer*, not a brain: it must never deploy accounts,
  and in read-only mode it must refuse every `order_send`.

## 8) Honesty rules for whoever uses this skill

- **No profit promises.** Backtests and simulations are evidence, not guarantees.
- Never present a single passing backtest as proof of profitability.
- The phrase "เทรดในไทยมีกฎหมายรองรับ 100%" is the **owner's own framing of this
  system** and is recorded in every file as such — it is not a legal opinion or an
  assurance by the author or by any authority. Settrade e-Open Account and MTS Gold
  Futures are **separate** channels with their own rules; a foreign-broker `XAUUSD` is
  not automatically the TFEX Gold Futures contract.
- Do not fabricate market data. When bars are missing, raise or return `None` — never
  synthesise candles.
- MetaAPI, broker, VPS and data costs and limits are the user's own responsibility.

## 9) Publishing to clawhub.ai

`.clawhubignore` is tuned so the factory defaults and the kill switch **are** published
while credentials and live state never are. Note deliberately that a blanket `work/`
rule would delete `trading-system/work/factory/` and `AUTO_TRADER_STOP` and leave the
published skill broken.

```bash
clawhub skill publish ./Pytron-Engine-MT5-Algo-Trade-For-OpenClaw \
  --slug pytron-engine-mt5-algo-trade --version 1.0.0
```

## 10) Start here

```bash
python3 scripts/verify_package.py            # 1. integrity + safety
#                                            # 2. install a working copy (section 2)
export METAAPI_TOKEN=... METAAPI_ACCOUNT_ID=...
python3 scripts/metaapi_connect_check.py     # 3. prove the bridge reaches YOUR account
python3 scripts/metaapi_engine_smoke.py      # 4. prove the ENGINE reads real bars
```

Then read [references/operations.md](references/operations.md) before enabling anything.
