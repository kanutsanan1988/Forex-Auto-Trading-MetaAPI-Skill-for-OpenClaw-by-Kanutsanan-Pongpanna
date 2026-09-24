<!-- Python Qaunt Trading + AI(LLM) Live Research | Creator: Kanutsanan Pongpanna | Settrade e-Open Account · MTS Gold Futures + MT5 -->

# Portable role mapping

## Principle

“Hermes” describes the primary Agent's coordinating role; it is not an instruction to install a particular product. On every destination platform, use the main Agent already available there. That same Agent performs the Mode-2 signal-bot and Admin Bot roles by loading a role-specific brief and following its narrower permissions.

## Run roles with one Agent

1. **Coordinator / Hermes role:** read `SKILL.md`, `AGENTS.md`, and current audit. Establish whether the request is read-only, research, or code work. Keep sources and observed state separate.
2. **Mode-2 signal-bot role:** when asked to produce the signal/recommendation, load `agents/brief_mode2.md`, read its evidence packet/contract, produce the expected schema, and report uncertainty. Do not send an order.
3. **Admin Bot role:** when asked to check or administer, load `agents/brief_admin.md`, check the allowed-action contract and current STOP/mode state, and make only changes explicitly permitted by the user and code policy. Never enable Live or clear STOP as an inferred step.

These roles can be invoked manually by the platform's primary Agent. For automatic recurrence, the user must set up a supported platform scheduler/runner and verify its credentials, logs, and failure behavior. A CLI command or cron from the source computer is not portable proof.

## Role boundary table

| Operation | Coordinator | Mode-2 signal role | Admin role |
|---|---|---|---|
| Read code/research/status | Yes | Only relevant packet | Yes |
| Produce signal analysis | Route/verify | Yes, per brief | No |
| Send MT5 order | No | No | No |
| Change ordinary allowed settings | Only explicit user request | No | Only through allowlisted command + testing gate |
| Enable Live / remove Kill Switch | Never infer | No | No, requires explicit owner authority |
| OpenRouter/Jev provider enablement | Only explicit user request | No | Never infer |

## Platform adaptation

For Codex, Cowork, Cursor, OpenClaw, Hermes, Manus, or a later Agent product, attach/read the root `SKILL.md` and this project directory. Keep the same role names and contracts; add a platform adapter only for invocation/scheduling and test it independently. The Agent product used at runtime may be called something else entirely.
