# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""Extract as-of shadow forecasts from frozen audit, never current-state backfill."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import statistics

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "inputs" / "auto_trader_audit.jsonl"
STRATEGIES = ("trend", "range", "mean_reversion", "breakout", "counter_trend", "breakout_reversal")
KEYS = [f"{s}_{side}" for s in STRATEGIES for side in ("buy", "sell")]


def distribution(values):
    values = sorted(float(v) for v in values if isinstance(v, (int, float)) and math.isfinite(v))
    return {"n": len(values), "distinct": len(set(values)), "min": min(values), "max": max(values),
            "mean": statistics.mean(values), "median": statistics.median(values)} if values else {"n": 0}


def stats(rows):
    r = [x["gross_r_multiple"] for x in rows]
    loss = -sum(v for v in r if v < 0)
    return {"n": len(r), "gross_r_sum": sum(r), "mean_gross_r": statistics.mean(r) if r else None,
            "wins": sum(v > 0 for v in r), "win_rate": sum(v > 0 for v in r) / len(r) if r else None,
            "gross_profit_factor": sum(v for v in r if v > 0) / loss if loss else None}


def key(o):
    return (o["strategy"], o["side"], o["regime"], o["opened_bar_time"])


cycles = []
for line_number, line in enumerate(SOURCE.read_text(encoding="utf-8-sig").splitlines(), 1):
    row = json.loads(line)
    if row.get("event") == "adaptive_shadow_cycle":
        row["line"] = line_number
        row["epoch"] = datetime.fromisoformat(row["time"]).timestamp()
        cycles.append(row)

opens = defaultdict(list)
closed_seen = set()
rows = []
duplicates = 0
unpaired = []
for cycle in cycles:
    # Runtime resolves existing positions before it opens new ones in the cycle.
    # Store the opening weighting probability (prepared before these closures).
    for outcome in cycle.get("shadow", {}).get("closed", []):
        unique = json.dumps(outcome, sort_keys=True, separators=(",", ":"))
        if unique in closed_seen:
            duplicates += 1
            continue
        closed_seen.add(unique)
        choices = [o for o in opens.get(key(outcome), []) if o["line"] < cycle["line"] and abs(o["position"]["entry"] - outcome["entry"]) < 1e-9]
        choice = choices[-1] if choices else None
        direction = f"{outcome['strategy']}_{outcome['side']}"
        elapsed = (outcome["closed_bar_time"] - outcome["opened_bar_time"]) / 60
        age = outcome.get("age")
        flags = []
        if choice is None:
            flags.append("opening_event_not_found")
        if elapsed <= 0:
            flags.append("same_or_earlier_bar_close")
        if age is None:
            flags.append("age_missing")
        elif age < elapsed:
            flags.append("unobserved_intervening_m1_bars")
        elif age > elapsed:
            flags.append("age_exceeds_elapsed_bars")
        if elapsed >= 180:
            flags.append("holding_interval_at_least_three_hours")
        opening = choice["position"] if choice else {}
        raw = opening.get("score_snapshot", {}).get(direction)
        weighted = opening.get("score")
        p = choice["probabilities"].get(direction) if choice else None
        if raw is None:
            flags.append("opening_raw_score_not_logged")
        if p is None:
            flags.append("opening_probability_not_logged")
        record = {
            "strategy": outcome["strategy"], "side": outcome["side"], "direction": direction, "regime": outcome["regime"],
            "opened_bar_time": outcome["opened_bar_time"], "closed_bar_time": outcome["closed_bar_time"],
            "opened_audit_time": choice["time"] if choice else None, "closed_audit_time": cycle["time"],
            "open_audit_line": choice["line"] if choice else None, "close_audit_line": cycle["line"],
            "entry": opening.get("entry"), "stop_distance": opening.get("stop_distance"), "reward_risk": opening.get("reward_risk"),
            "entry_raw_score": raw, "entry_weighted_score": weighted, "entry_probability": p,
            "probability_source": "same opening cycle weighting.probabilities prepared before outcome resolution" if p is not None else None,
            "gross_r_multiple": outcome["r_multiple"], "outcome_reason": outcome["reason"],
            "elapsed_m1_bars": elapsed, "age_analysis_cycles": age,
            "missing_observed_m1_bars_estimated": max(0, elapsed - age) if age is not None else None,
            "repeated_cycles_estimated": max(0, age - elapsed) if age is not None else None,
            "flags": flags,
            "entry_pair_unique": len(choices) == 1,
            "all_three_entry_fields_available": raw is not None and weighted is not None and p is not None,
            "observed_path_contiguous": elapsed > 0 and age == elapsed,
            "usable_forecast_pair": p is not None and weighted is not None and choice is not None and elapsed > 0,
            "strict_usable_pair": p is not None and weighted is not None and raw is not None and choice is not None and elapsed > 0 and age == elapsed,
        }
        rows.append(record)
        if choice is None:
            unpaired.append(record)
    for position in cycle.get("shadow", {}).get("opened", []):
        opens[key(position)].append({"position": position, "line": cycle["line"], "time": cycle["time"],
                                     "probabilities": cycle.get("weighting", {}).get("probabilities", {})})

rows.sort(key=lambda r: (r["opened_bar_time"], r["open_audit_line"] or 0, r["direction"]))
unique_bars = sorted({r["opened_bar_time"] for r in rows})
cut1 = unique_bars[int(len(unique_bars) * .6)]
cut2 = unique_bars[int(len(unique_bars) * .8)]


def split(row):
    return "train" if row["opened_bar_time"] < cut1 else "validation" if row["opened_bar_time"] < cut2 else "test"


for row in rows:
    row["split"] = split(row)
    boundary = cut1 if row["split"] == "train" else cut2 if row["split"] == "validation" else None
    row["purged_crossing_split"] = boundary is not None and row["closed_bar_time"] >= boundary

by_direction = {}
for direction in KEYS:
    rr = [r for r in rows if r["direction"] == direction]
    with_p = [r for r in rr if r["usable_forecast_pair"]]
    strict = [r for r in rr if r["strict_usable_pair"]]
    calibration = {}
    for name, sample in (("paired_all_paths", with_p), ("paired_contiguous_paths", strict)):
        calibration[name] = {"n": len(sample),
                             "mean_probability": statistics.mean(r["entry_probability"] for r in sample) if sample else None,
                             "observed_win_rate": sum(r["gross_r_multiple"] > 0 for r in sample) / len(sample) if sample else None,
                             "brier_score": statistics.mean((r["entry_probability"] - float(r["gross_r_multiple"] > 0)) ** 2 for r in sample) if sample else None}
    by_direction[direction] = {"all_closed": stats(rr), "opening_event_pairs": sum(r["entry_pair_unique"] for r in rr),
                               "all_three_entry_fields_available": sum(r["all_three_entry_fields_available"] for r in rr),
                               "usable_forecast_pairs": len(with_p), "strict_usable_pairs": len(strict),
                               "flags": dict(Counter(flag for r in rr for flag in r["flags"])),
                               "entry_raw_score": distribution(r["entry_raw_score"] for r in rr),
                               "entry_weighted_score": distribution(r["entry_weighted_score"] for r in rr),
                               "entry_probability": distribution(r["entry_probability"] for r in rr),
                               "calibration": calibration,
                               "splits": {part: stats([r for r in with_p if r["split"] == part and not r["purged_crossing_split"]]) for part in ("train", "validation", "test")}}

# Each candidate threshold is chosen exclusively from training outcomes.
# Validation and final test are reported once. No full-sample winning threshold.
sweep = {}
for direction in KEYS:
    sweep[direction] = {}
    for field, grid in (("entry_weighted_score", [x / 100 for x in range(20, 91, 5)]),
                        ("entry_probability", [x / 100 for x in range(35, 86, 5)])):
        rr = [r for r in rows if r["direction"] == direction and r.get(field) is not None and r["entry_pair_unique"]
              and r["elapsed_m1_bars"] > 0 and not r["purged_crossing_split"]]
        table = []
        for threshold in grid:
            candidate = {"threshold_at_least": threshold}
            for part in ("train", "validation", "test"):
                candidate[part] = stats([r for r in rr if r["split"] == part and r[field] >= threshold])
            table.append(candidate)
        sufficient_train = [c for c in table if c["train"]["n"] >= 20]
        choice = max(sufficient_train, key=lambda c: (c["train"]["mean_gross_r"], c["train"]["n"], -c["threshold_at_least"])) if sufficient_train else None
        reasons = []
        if choice is None:
            reasons.append("No training threshold has at least 20 outcomes")
        else:
            for part in ("validation", "test"):
                if choice[part]["n"] < 8:
                    reasons.append(f"{part} has fewer than 8 selected outcomes")
                elif choice[part]["mean_gross_r"] <= 0:
                    reasons.append(f"{part} average gross R is not positive")
        sweep[direction][field] = {"train_selected_candidate": choice, "evidence_status": "insufficient" if reasons else "descriptive_candidate_only",
                                   "reasons": reasons, "table": table,
                                   "deployment_status": "not validated: simulated dependent and sometimes missing-path labels; gross returns omit live spread/fees and exit-policy effects"}

output = {
    "source": str(SOURCE), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "source_kind": "audit_only",
    "method": {"matching": "strategy + side + regime + opened_bar_time and equal entry price; closing audit line must follow opening line; exact identical closure payloads deduplicated",
               "entry_fields": "raw from opening score_snapshot[direction], weighted from opening score, probability from opening cycle weighting.probabilities[direction]; no state or future backfill",
               "returns": "Gross simulated R, not executable net P&L; no spread, swap, fee or slippage debit available in these labels",
               "probability_timing": "weighting is logged in same cycle but prepared before update_after_analysis resolves old outcomes and opens new positions; this matches the probability already used for the associated analysis",
               "gaps": "age counts analysis calls. elapsed bars greater than age suggests intervening M1 OHLC paths were not observed. It also counts closed-market minutes; neither can safely be treated as complete execution path.",
               "strict_usable": "Unique matched open; raw, weighted, and prior probability present; positive elapsed bars; age exactly equals elapsed M1 bars. This reduces path ambiguity but does not validate reward or current code policy.",
               "split": "60/20/20 of unique opening-bar timestamps, common boundaries for all directions. Outcomes crossing a split boundary are purged from that earlier split. No overlap purging among simultaneous strategies, so observations remain dependent.",
               "sweep": "Training-only lower-bound selection maximizing mean gross R at n>=20, then fixed candidate evaluated on validation/test requiring n>=8 each. These are modest exploratory gates, not adequate production validation."},
    "counts": {"audit_cycles": len(cycles), "open_records": sum(len(v) for v in opens.values()), "deduplicated_closed": len(rows),
               "identical_duplicate_closures_removed": duplicates, "unpaired_closures": len(unpaired),
               "nonunique_open_key_closures": sum(not r["entry_pair_unique"] for r in rows),
               "all_three_fields": sum(r["all_three_entry_fields_available"] for r in rows),
               "usable_forecast_pairs": sum(r["usable_forecast_pair"] for r in rows),
               "strict_usable_pairs": sum(r["strict_usable_pair"] for r in rows),
               "same_or_earlier_bar": sum(r["elapsed_m1_bars"] <= 0 for r in rows),
               "flags": dict(Counter(flag for r in rows for flag in r["flags"])),
               "purged_crossing_split": sum(r["purged_crossing_split"] for r in rows)},
    "split_boundaries_broker_epoch": {"validation_start": cut1, "test_start": cut2},
    "per_direction": by_direction,
    "descriptive_chronological_sweeps": sweep,
    "entry_outcomes": rows,
}
(HERE / "shadow_entry_outcomes.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"counts": output["counts"], "directions": {k: {"n": v["all_closed"]["n"], "p_pairs": v["usable_forecast_pairs"], "strict": v["strict_usable_pairs"], "p": v["entry_probability"], "splits": {s: v["splits"][s]["n"] for s in ("train", "validation", "test")}} for k, v in by_direction.items()}, "sweep_status": {k: {f: v["evidence_status"] for f, v in d.items()} for k, d in sweep.items()}}, indent=2))
