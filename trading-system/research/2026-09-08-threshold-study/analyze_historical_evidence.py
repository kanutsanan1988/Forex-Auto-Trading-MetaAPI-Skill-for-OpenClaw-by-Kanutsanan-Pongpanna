# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Offline audit and broker-history reconciliation; reads frozen inputs only.

No trader modules, MetaTrader5, environment secrets, or network calls are used.
All broker IDs are used for exact joins, never a forward/nearest-outcome score join.
"""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
INPUT = HERE / "inputs"
STRATEGIES = ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")
KEYS = [f"{strategy}_{side}" for strategy in STRATEGIES for side in ("buy", "sell")]


def read(name):
    return json.loads((INPUT / name).read_text(encoding="utf-8-sig"))


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def distribution(values):
    values = sorted(float(x) for x in values if isinstance(x, (int, float)) and math.isfinite(x))
    if not values:
        return {"n": 0}
    return {"n": len(values), "unique": len(set(values)), "min": values[0], "median": statistics.median(values),
            "max": values[-1], "mean": statistics.mean(values)}


def wilson(wins, n):
    if not n:
        return None
    z = 1.959963984540054
    p = wins / n
    midpoint = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(midpoint - half, 6), round(midpoint + half, 6)]


def performance(rows, value="net_profit"):
    vals = [float(row[value]) for row in rows]
    wins = sum(x > 0 for x in vals)
    gain = sum(x for x in vals if x > 0)
    loss = -sum(x for x in vals if x < 0)
    return {"n": len(vals), "wins": wins, "losses": sum(x < 0 for x in vals), "flat": sum(x == 0 for x in vals),
            "net": round(sum(vals), 6), "mean": round(statistics.mean(vals), 6) if vals else None,
            "win_rate": wins / len(vals) if vals else None, "win_rate_wilson_95": wilson(wins, len(vals)),
            "profit_factor": gain / loss if loss else None,
            "profit_factor_null_reason": "no losses or no sample" if not loss else None}


def calibration(rows):
    values = [r for r in rows if r.get("entry_probability") is not None]
    if not values:
        return {"n": 0}
    p = [r["entry_probability"] for r in values]
    y = [float(r["net_profit"] > 0) for r in values]
    bins = []
    for lo, hi in [(0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, .8), (.8, 1.000001)]:
        rr = [r for r in values if lo <= r["entry_probability"] < hi]
        if rr:
            bins.append({"range": [lo, min(hi, 1)], **performance(rr), "mean_probability": statistics.mean(r["entry_probability"] for r in rr)})
    return {"n": len(values), "mean_probability": statistics.mean(p), "observed_win_rate": statistics.mean(y),
            "brier_score": statistics.mean((pp - yy) ** 2 for pp, yy in zip(p, y)), "bins": bins,
            "interpretation": "Descriptive performance of selected executed trades only; dependent small samples, changing policies and flawed shadow labels prevent validation of calibrated probabilities."}


audit = []
invalid = []
for i, line in enumerate((INPUT / "auto_trader_audit.jsonl").read_text(encoding="utf-8-sig").splitlines(), 1):
    try:
        row = json.loads(line)
        row["_line"] = i
        row["_epoch"] = stamp(row["time"])
        audit.append(row)
    except Exception as exc:
        invalid.append({"line": i, "error": str(exc)})
state = read("auto_trader_state.json")
deals = read("mt5_deals.json")
orders = read("mt5_orders.json")
config = read("config_sanitized.json")
manifest = read("manifest.json")
symbols = Counter(d["symbol"] for d in deals)
symbol = manifest["mt5"]["symbol"]
magic = config["magic"]
offset = round(manifest["mt5"]["observed_tick_minus_wall_seconds"] / 3600) * 3600
order_map = {o["ticket"]: o for o in orders}
event_counts = Counter(r["event"] for r in audit)
entry_events = defaultdict(list)
analysis_rows = []
latest_cycle = latest_adaptive = None
daily = defaultdict(lambda: {"events": Counter(), "analysis_rows": 0, "scored_rows": 0, "probability_vectors": set(), "minutes": set()})
cycles = []
for row in audit:
    event = row["event"]
    day = iso(row["_epoch"])[:10]
    daily[day]["events"][event] += 1
    if event == "adaptive_update":
        latest_adaptive = row
    if event == "adaptive_shadow_cycle":
        latest_cycle = row
        cycles.append(row)
        p = row.get("weighting", {}).get("probabilities", {})
        if p:
            daily[day]["probability_vectors"].add(json.dumps(p, sort_keys=True))
    analysis = row.get("analysis")
    if not isinstance(analysis, dict):
        continue
    router = analysis.get("router_decision") or {}
    strategy = analysis.get("strategy") or router.get("strategy")
    side = analysis.get("side") or router.get("side")
    key = f"{strategy}_{side}" if strategy and side else None
    raw = router.get("regime_scores", {}).get(key)
    candidates = router.get("candidates") or analysis.get("technical_candidates") or []
    candidate = next((c for c in candidates if c.get("strategy") == strategy), {})
    weighted = candidate.get(f"{side}_score")
    near_cycle = latest_cycle is not None and 0 <= row["_epoch"] - latest_cycle["_epoch"] <= 10
    probability = latest_cycle.get("weighting", {}).get("probabilities", {}).get(key) if near_cycle else None
    rec = {"line": row["_line"], "time": row["time"], "epoch": row["_epoch"], "event": event, "strategy": strategy,
           "side": side, "direction": key, "entry_raw_score": raw, "entry_weighted_score": weighted,
           "entry_probability": probability, "probability_source": "preceding cycle weighting within 10 seconds" if probability is not None else None,
           "probability_source_line": latest_cycle["_line"] if probability is not None else None,
           "probability_age_seconds": row["_epoch"] - latest_cycle["_epoch"] if probability is not None else None,
           "has_router": bool(router), "candidate_count": len(candidates),
           "all_raw_scores": {k: router.get("regime_scores", {}).get(k) for k in KEYS},
           "all_weighted_scores": {f"{c.get('strategy')}_{s}": c.get(f"{s}_score") for c in candidates for s in ("buy", "sell")},
           "all_probabilities": latest_cycle.get("weighting", {}).get("probabilities", {}) if near_cycle else {},
           "reason": row.get("reason") or router.get("reason")}
    if raw is not None and weighted is not None and near_cycle and latest_adaptive is not None:
        sw = latest_adaptive.get("strategy_weights", {}).get(strategy)
        dw = latest_cycle.get("weighting", {}).get("weights", {}).get(key)
        if sw is not None and dw is not None:
            rec["weight_product_difference"] = weighted - raw * sw * dw
    analysis_rows.append(rec)
    daily[day]["analysis_rows"] += 1
    daily[day]["scored_rows"] += any(v is not None for v in rec["all_raw_scores"].values())
    daily[day]["minutes"].add(int(row["_epoch"] // 60))
    if event == "order_result":
        rec["order_id"] = row.get("result", {}).get("order")
        rec["ok"] = row.get("ok")
        rec["retcode"] = row.get("result", {}).get("retcode")
        entry_events[rec["order_id"]].append(rec)

gold = [d for d in deals if d.get("symbol") == symbol and d.get("type") in (0, 1)]
position_groups = defaultdict(list)
for d in gold:
    position_groups[d["position_id"]].append(d)
positions = []
for pid, group in sorted(position_groups.items()):
    group.sort(key=lambda d: (d["time_msc"], d["ticket"]))
    entries = [d for d in group if d["entry"] == 0]
    exits = [d for d in group if d["entry"] in (1, 3)]
    exotic = [d for d in group if d["entry"] not in (0, 1, 3)]
    entry_volume = sum(d["volume"] for d in entries)
    exit_volume = sum(d["volume"] for d in exits)
    complete = bool(entries and exits) and not exotic and abs(entry_volume - exit_volume) < 1e-9
    first = entries[0] if entries else group[0]
    matches = [r for d in entries for r in entry_events.get(d["order"], []) if r["ok"]]
    matches.sort(key=lambda r: r["epoch"])
    match = matches[0] if matches else None
    strategy = match.get("strategy") if match else None
    strategy_source = "entry audit exact order ID" if strategy else None
    comments = [order_map.get(d["order"], {}).get("comment", "") for d in entries]
    if not strategy:
        inferred = [c.removeprefix("codex-") for c in comments if c.removeprefix("codex-") in STRATEGIES]
        if len(set(inferred)) == 1:
            strategy, strategy_source = inferred[0], "entry order comment"
    side = "buy" if first["type"] == 0 else "sell"
    components = {key: round(sum(float(d.get(key, 0)) for d in group), 8) for key in ("profit", "commission", "swap", "fee")}
    rec = {"position_id": pid, "entry_order_ids": sorted(set(d["order"] for d in entries)), "deal_ids": [d["ticket"] for d in group],
           "side": side, "strategy": strategy, "strategy_source": strategy_source,
           "direction": f"{strategy}_{side}" if strategy else None,
           "complete_closed": complete, "entry_volume": entry_volume, "exit_volume": exit_volume,
           "entry_broker_epoch": first["time"], "last_broker_epoch": group[-1]["time"],
           "entry_utc_estimated": iso(first["time"] - offset), "close_utc_estimated": iso(group[-1]["time"] - offset),
           "net_profit": round(sum(components.values()), 8), "components": components,
           "entry_magic": sorted(set(d["magic"] for d in entries)), "audit_matched": bool(match),
           "audit_match_lines": [r["line"] for r in matches],
           "entry_raw_score": match.get("entry_raw_score") if match else None,
           "entry_weighted_score": match.get("entry_weighted_score") if match else None,
           "entry_probability": match.get("entry_probability") if match else None,
           "probability_source_line": match.get("probability_source_line") if match else None,
           "score_audit_line": match["line"] if match else None,
           "audit_to_deal_seconds_estimated": first["time"] - offset - match["epoch"] if match else None,
           "entry_audit_time": match["time"] if match else None}
    positions.append(rec)
closed = [p for p in positions if p["complete_closed"]]
matched = [p for p in closed if p["audit_matched"]]
bot = [p for p in closed if magic in p["entry_magic"]]

thresholds = {}
by_direction = {}
for key in KEYS:
    selected = [p for p in matched if p["direction"] == key]
    all_named = [p for p in closed if p["direction"] == key]
    by_direction[key] = {"all_named_closed": performance(all_named), "audit_matched_closed": performance(selected),
                         "raw_score": distribution(p["entry_raw_score"] for p in selected),
                         "weighted_score": distribution(p["entry_weighted_score"] for p in selected),
                         "probability": distribution(p["entry_probability"] for p in selected), "calibration": calibration(selected)}
    thresholds[key] = {}
    for field, grid in [("entry_raw_score", [.2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8]),
                        ("entry_weighted_score", [.2, .25, .3, .35, .4, .45, .5, .55, .6, .65, .7, .75, .8]),
                        ("entry_probability", [.4, .45, .5, .55, .6, .65, .7, .75, .8])]:
        thresholds[key][field] = [{"threshold_at_least": t, **performance([p for p in selected if p.get(field) is not None and p[field] >= t])} for t in grid]

shadow = state.get("adaptive_shadow", {})
shadow_outcomes = shadow.get("outcomes", [])
snapshots = shadow.get("score_snapshots", [])
snapshot_times = Counter(x["bar_time"] for x in snapshots)
same_bar = [o for o in shadow_outcomes if o["closed_bar_time"] <= o["opened_bar_time"]]
age_mismatches = [o for o in shadow_outcomes if o.get("age", 0) * 60 > o["closed_bar_time"] - o["opened_bar_time"]]
audit_shadow_outcomes = [o for row in cycles for o in row.get("shadow", {}).get("closed", [])]
audit_shadow_opens = [o for row in cycles for o in row.get("shadow", {}).get("opened", [])]
signature = lambda o: (o["strategy"], o["side"], o["regime"], o.get("opened_bar_time"), o.get("closed_bar_time"), o.get("entry"))
outcome_counter = Counter(signature(o) for o in audit_shadow_outcomes)
unique_shadow = list({signature(o): o for o in audit_shadow_outcomes}.values())
probability_runs = []
for row in cycles:
    probabilities = row.get("weighting", {}).get("probabilities", {})
    if not probabilities:
        continue
    token = json.dumps(probabilities, sort_keys=True)
    if probability_runs and probability_runs[-1]["token"] == token:
        probability_runs[-1]["last_epoch"] = row["_epoch"]
        probability_runs[-1]["last_time"] = row["time"]
        probability_runs[-1]["cycles"] += 1
    else:
        probability_runs.append({"token": token, "first_time": row["time"], "last_time": row["time"], "first_epoch": row["_epoch"], "last_epoch": row["_epoch"], "cycles": 1, "probabilities": probabilities})
for run in probability_runs:
    run.pop("token")
    run["elapsed_hours"] = (run.pop("last_epoch") - run.pop("first_epoch")) / 3600

score_coverage = {}
for key in KEYS:
    score_coverage[key] = {"raw": distribution(r["all_raw_scores"].get(key) for r in analysis_rows),
                           "weighted": distribution(r["all_weighted_scores"].get(key) for r in analysis_rows),
                           "probability": distribution(r["all_probabilities"].get(key) for r in analysis_rows)}

period_signatures = defaultdict(list)
for row in analysis_rows:
    signature_key = f"router={row['has_router']};candidates={row['candidate_count']};raw={sum(v is not None for v in row['all_raw_scores'].values())};prob={len(row['all_probabilities'])}"
    period_signatures[signature_key].append(row)

for day, item in daily.items():
    item["unique_analysis_utc_minutes"] = len(item.pop("minutes"))
    item["unique_probability_vectors"] = len(item.pop("probability_vectors"))
    item["events"] = dict(item["events"])

gaps = sorted([(b["_epoch"] - a["_epoch"], a["time"], b["time"]) for a, b in zip(audit, audit[1:]) if b["_epoch"] - a["_epoch"] > 3600], reverse=True)
time_order_inversions = sum(b["_epoch"] < a["_epoch"] for a, b in zip(audit, audit[1:]))
successful = [r for values in entry_events.values() for r in values if r["ok"]]
entry_order_ids = {d["order"] for d in gold if d["entry"] == 0}
execution_match_ids = {r["order_id"] for r in successful} & entry_order_ids
schema_periods = {key: {"n": len(values), "first": values[0]["time"], "last": values[-1]["time"]} for key, values in period_signatures.items()}
router_outcomes = state.get("adaptive_router", {}).get("outcomes", {})
legacy_router = [o for values in router_outcomes.values() for o in values]
unknown_exits = [r for r in audit if r["event"] == "position_closed" and r.get("strategy") == "unknown"]
input_hashes = {name: hashlib.sha256((INPUT / name).read_bytes()).hexdigest() for name in ["auto_trader_audit.jsonl", "auto_trader_state.json", "mt5_deals.json", "mt5_orders.json"]}
report = {
    "method": {"read_only": True, "inputs_frozen": True, "input_sha256": input_hashes, "account_currency": manifest["mt5"]["currency"],
               "broker_epoch_minus_wall_seconds_estimated": offset,
               "join": "Gold DEAL_ENTRY_IN order ID equals successful audit order_result.result.order; outcomes grouped by position_id and all deal profit+commission+swap+fee summed. Complete only when in/out volume balances and no reversal entry type.",
               "score_source": "Logged entry router regime_scores direction = raw; candidate direction score = weighted. No score recomputed from future state.",
               "probability_source": "Only preceding adaptive_shadow_cycle.weighting.probabilities within 10 seconds, in file order, retained as entry-known probability. Current-state/future probabilities never backfilled.",
               "threshold_grid_interpretation": "Selected-trade descriptive slicing, not a policy backtest: rejected signals have no real outcome; a different entry threshold changes ranking, holding, future opportunities and exits. Do not optimize thresholds on this table.",
               "time_caution": "Server timestamps have observed about +3h offset; exact order-ID joins are independent of timezone assumptions. UTC deal display is estimated."},
    "audit": {"rows": len(audit), "invalid_rows": invalid, "first": audit[0]["time"], "last": audit[-1]["time"], "event_counts": dict(event_counts),
              "time_order_inversions": time_order_inversions, "gaps_over_one_hour": [{"hours": secs / 3600, "from": a, "to": b} for secs, a, b in gaps],
              "daily": dict(sorted(daily.items())), "analysis_rows": len(analysis_rows), "unique_analysis_utc_minutes": len({int(r['epoch'] // 60) for r in analysis_rows}),
              "schema_periods": schema_periods, "score_coverage": score_coverage,
              "logged_entry_order_events": len(successful), "successful_unique_entry_order_ids": len({r['order_id'] for r in successful}),
              "successful_order_ids_matched_to_deals": len(execution_match_ids), "successful_order_ids_unmatched": sorted({r['order_id'] for r in successful} - entry_order_ids),
              "failed_order_events": [r for values in entry_events.values() for r in values if not r["ok"]],
              "position_closed_unknown_strategy_count": len(unknown_exits),
              "score_formula_residual": distribution(abs(r["weight_product_difference"]) for r in analysis_rows if "weight_product_difference" in r)},
    "broker": {"all_deal_records": len(deals), "all_order_records": len(orders), "deal_symbols": dict(symbols),
               "gold_trade_deals": len(gold), "gold_deal_entry_types": dict(Counter(d["entry"] for d in gold)),
               "gold_deal_magic": dict(Counter(d["magic"] for d in gold)),
               "gold_unique_positions": len(positions), "gold_complete_closed": performance(closed),
               "bot_magic_complete_closed": performance(bot), "audit_matched_complete_closed": performance(matched),
               "unmatched_complete_closed": performance([p for p in closed if not p["audit_matched"]]),
               "incomplete_positions": [p for p in positions if not p["complete_closed"]],
               "net_components_all_gold_closed": {k: round(sum(p["components"][k] for p in closed), 8) for k in ("profit", "commission", "swap", "fee")},
               "audit_to_deal_seconds_estimated": distribution(p["audit_to_deal_seconds_estimated"] for p in matched),
               "unclassified_matched": performance([p for p in matched if not p["strategy"]]),
               "unclassified_bot": performance([p for p in bot if not p["strategy"]]),
               "overall_matched_calibration": calibration(matched)},
    "executed_by_direction": by_direction,
    "descriptive_threshold_slices": thresholds,
    "shadow": {"state_outcomes": len(shadow_outcomes), "state_open_positions": len(shadow.get("positions", {})),
               "outcome_units": "Simulated R, not USD or broker fills; no spread/commission/fee model in adaptive_shadow.py.",
               "state_per_direction": {key: performance([o for o in shadow_outcomes if f'{o["strategy"]}_{o["side"]}' == key], "r_multiple") for key in KEYS},
               "state_closed_same_or_earlier_bar": len(same_bar), "state_age_exceeds_elapsed_m1_bars": len(age_mismatches),
               "same_bar_examples": same_bar[:5], "state_score_snapshots": len(snapshots), "state_unique_snapshot_bars": len(snapshot_times),
               "state_duplicate_snapshot_records": sum(n - 1 for n in snapshot_times.values()), "state_max_snapshots_per_bar": max(snapshot_times.values(), default=0),
               "audit_open_records": len(audit_shadow_opens), "audit_closed_records": len(audit_shadow_outcomes), "audit_unique_closed_records": len(unique_shadow),
               "audit_duplicate_closed_records": sum(n - 1 for n in outcome_counter.values()),
               "audit_same_or_earlier_bar_closed": sum(o["closed_bar_time"] <= o["opened_bar_time"] for o in unique_shadow),
               "state_early_without_score_snapshot": sum(not o.get("score_snapshot") for o in shadow_outcomes),
               "state_last_probabilities": shadow.get("directional_probabilities", {}),
               "probability_vector_runs": sorted(probability_runs, key=lambda r: (r["elapsed_hours"], r["cycles"]), reverse=True)[:12],
               "distinct_preentry_probability_vectors": len({json.dumps(c.get("weighting", {}).get("probabilities", {}), sort_keys=True) for c in cycles if c.get("weighting", {}).get("probabilities")}),
               "legacy_router_simulated_outcomes": len(legacy_router), "legacy_router_strategy_counts": {k: len(v) for k, v in router_outcomes.items()},
               "legacy_router_first_open_epoch": min((o["opened_after_bar_time"] for o in legacy_router), default=None),
               "legacy_router_last_close_epoch": max((o["closed_bar_time"] for o in legacy_router), default=None),
               "adaptive_live_outcomes_counts": {k: len(v) for k, v in state.get("adaptive", {}).get("outcomes", {}).items()},
               "limitations": ["Repeated analysis of the same already-closed M1 bar can resolve a paper entry using that bar's pre-entry high/low and increments age again; same-bar counts directly quantify observed contamination.",
                               "Positions skipped over market gaps are resolved only against the later observed bar; intervening price paths are absent from the live shadow record.",
                               "Win probability is a smoothed marginal direction outcome frequency, not calibrated conditional P(win at a particular score). Sparse directions blend profit-factor/(1+profit-factor), which is not generally a win probability when reward and loss sizes differ.",
                               "Relation statistics count other directions' simulated outcomes when target scores co-occur; these are dependent observations and not target-direction trade successes.",
                               "Retained state is capped at 400 outcomes/snapshots and historical implementation/configuration changes are not version-tagged per observation."]},
    "matched_positions": matched,
    "all_gold_positions": positions,
}
(HERE / "historical_evidence.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

def money(v):
    return f"{v:+.2f}"

lines = ["# Historical broker and audit evidence", "", "Offline frozen inputs only; no live trading code imported and no order or API call performed.", "",
         f"Audit: {len(audit):,} records from {audit[0]['time']} to {audit[-1]['time']}; {len(analysis_rows):,} rows contain analysis, across {len({int(r['epoch'] // 60) for r in analysis_rows}):,} unique UTC minute buckets.",
         f"Broker: {len(deals)} total deals, {len(orders)} orders; {len(gold)} gold trade deals reconstruct {len(closed)} complete closed positions. Gold closed net = USD {money(sum(p['net_profit'] for p in closed))}. Entry magic {magic}: {len(bot)} closed positions, USD {money(sum(p['net_profit'] for p in bot))}.",
         f"Exact audit order-ID matching: {len(matched)} closed positions, USD {money(sum(p['net_profit'] for p in matched))}. Successful audit entry events = {len(successful)}; unique IDs = {len({r['order_id'] for r in successful})}; matched IDs = {len(execution_match_ids)}.", "",
         "Net includes all entry and exit deal profit, commission, swap and fee. Manual/unmatched history is not attributed to a strategy score. All amounts are USD from the frozen account history.", "",
         "| Direction | Matched closed n | Net USD | Win rate | Raw score n | Weighted score n | Entry probability n |", "|---|---:|---:|---:|---:|---:|---:|"]
for key, metrics in by_direction.items():
    p = metrics["audit_matched_closed"]
    wr = f"{p['win_rate']:.1%}" if p["n"] else "—"
    lines.append(f"| {key} | {p['n']} | {money(p['net'])} | {wr} | {metrics['raw_score']['n']} | {metrics['weighted_score']['n']} | {metrics['probability']['n']} |")
lines += ["", f"Unclassified audit-matched positions: {report['broker']['unclassified_matched']['n']}; these cannot supply per-direction threshold evidence.", "",
          f"Shadow outcomes are paper trades: {len(shadow_outcomes)} in retained state, {len(unique_shadow)} unique closures in the full audit, and {len(legacy_router)} older router simulations. They are not additional broker executions.",
          f"Observed contamination: {len(same_bar)}/{len(shadow_outcomes)} retained outcomes close on or before their opening M1 bar; {len(age_mismatches)} have an age exceeding elapsed M1 bars. The last {len(snapshots)} score snapshots cover {len(snapshot_times)} unique bars ({sum(n - 1 for n in snapshot_times.values())} repeated records). Full-audit same/earlier-bar closures: {report['shadow']['audit_same_or_earlier_bar_closed']}.", "",
          "The probability field is a smoothed direction win frequency from these simulated outcomes. It is not a demonstrated probability of profit for the current score. Score-conditional calibration, sparse-direction sample size, co-occurrence dependence, observation gaps, and per-row model version history remain insufficient for choosing 12 durable thresholds.", "",
          "The JSON includes executed trade IDs, entry audit-line provenance, net component reconciliation, Wilson intervals, descriptive calibration, daily/schema coverage, probability freeze runs, and raw/weighted/probability threshold slices. Those slices only filter trades that historically executed. They do not estimate the outcome of rejected trades or of changing the full trading policy."]
(HERE / "historical_evidence.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"audit": len(audit), "analysis_rows": len(analysis_rows), "closed_gold": performance(closed), "bot": performance(bot), "matched": performance(matched),
                  "matched_by_direction": {k: v["audit_matched_closed"] for k, v in by_direction.items()}, "same_bar": len(same_bar), "snapshot_unique": len(snapshot_times),
                  "calibration": calibration(matched), "schema_periods": schema_periods}, ensure_ascii=True, indent=2))
