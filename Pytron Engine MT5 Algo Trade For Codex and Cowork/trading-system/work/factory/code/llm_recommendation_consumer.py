#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ระบบเทรดทองคำอัตโนมัติ (Gold Auto Trading System)
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna
#   Facebook: https://www.facebook.com/LoveMoneyTH
#   YouTube:  https://youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""LLM Recommendation Consumer — ใจกลางของ Auto-Improve Loop
อ่านคำแนะนำจาก LLM (ไฟล์ REC-*.json ใน research/recommendations/) → ตรวจสอบ
ความถูกต้อง (schema + safety) → apply ลง auto_config.json → รีสตาร์ทระบบเทรดด้วย
ค่าที่ปรับปรุงแล้ว — อัตโนมัติทั้งหมด โดยผู้ใช้ตั้งค่า auto_apply ได้

LLM-agnostic: ไฟล์คำแนะนำเป็น JSON มาตรฐาน — ไม่ผูกกับ provider/model ใด
ระบบที่นำไปใช้ต่อ ใช้ LLM ของตัวเองก็ได้ (เขียน REC-*.json แบบเดียวกัน)
"""
import os, json, subprocess, sys, datetime
from pathlib import Path
from runtime_support import project_root, current_mode, atomic_json, update_json, digest

def find_project_dir():
    return str(project_root())

proj = find_project_dir()
if not proj:
    raise SystemExit(0)

L = os.path.join(proj, "outputs", "mt5_python_bridge")
CFG = os.path.join(L, "auto_config.json")
REC_DIR = os.path.join(proj, "research", "recommendations")
APPLIED_DIR = os.path.join(REC_DIR, "applied")
os.makedirs(APPLIED_DIR, exist_ok=True)
AUDIT = os.path.join(proj, "work", "auto_trader_audit.jsonl")

def audit(event, **kw):
    rec = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": event, **kw}
    try:
        with open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass

# ---- 1. safety rules: ไม่อนุญาตให้ LLM แก้ final guarded keys ----
PROTECTED = {"live_enabled", "magic", "volume"}
ALLOWED_ACTIONS = {"set_gate", "set_probability_gate", "set_tpsl",
                   "set_weights", "toggle_strategy", "set_risk", "set_directional_weights"}
STRATEGIES = ("trend", "range", "mean_reversion", "counter_trend", "breakout", "breakout_reversal")
DIRECTIONAL_KEYS = {f"{s}_{sd}" for s in STRATEGIES for sd in ("buy", "sell")}

# ── ★ เกณฑ์การสร้าง TP/SL (รอบ 10 นาที/5 นาที มีสิทธิ์ปรับ — ภายในขอบเขตปลอดภัย) ──
TPSL_LIMITS = {
    "atr_stop_multiplier": (0.80, 2.00),   # SL โกลบอล = ATR x ค่านี้
    "min_reward_risk":     (1.20, 3.00),   # TP โกลบอล = R:R ขั้นต่ำ
    "_stop_atr":           (0.60, 2.50),   # SL ต่อกลยุทธ์
    "_reward_risk":        (1.20, 3.00),   # TP ต่อกลยุทธ์ (เช่น breakout_reward_risk)
}
TPSL_STRATEGY_KEYS = ("range_stop_atr", "mean_reversion_stop_atr", "breakout_stop_atr",
                      "counter_trend_stop_atr", "breakout_reversal_stop_atr",
                      "breakout_reward_risk")

def validate(rec: dict):
    """ตรวจ schema + safety ของคำแนะนำ LLM ก่อน apply"""
    if not isinstance(rec, dict):
        return False, "not a dict"
    if rec.get("schema") != "hermes-trading-recommendation-v1":
        return False, "schema mismatch (want hermes-trading-recommendation-v1)"
    if rec.get("auto_apply") is not True:
        return False, "auto_apply != true"
    if not isinstance(rec.get("changes"), list) or not rec["changes"]:
        return False, "changes must be a nonempty list"
    try:
        digest(rec)
    except (ValueError, TypeError):
        return False, "non-finite or unsupported values"
    for change in rec.get("changes", []):
        if not isinstance(change, dict):
            return False, "change not dict"
        act = change.get("action")
        if act not in ALLOWED_ACTIONS:
            return False, f"action '{act}' not allowed"
        if act == "set_gate":
            s = change.get("strategy"); side = change.get("side")
            lo = change.get("raw_low"); hi = change.get("raw_high")
            if s not in ("trend","range","mean_reversion","counter_trend","breakout","breakout_reversal"):
                return False, f"bad strategy {s}"
            if side not in ("buy","sell"):
                return False, f"bad side {side}"
            if not (isinstance(lo,(int,float)) and isinstance(hi,(int,float))):
                return False, "raw_low/raw_high must be numbers"
            if not (0.05 <= lo <= hi <= 1.0):
                return False, f"band invalid: low={lo} high={hi}"
        if act == "set_probability_gate":
            s = change.get("strategy"); side = change.get("side")
            lo = change.get("probability_low"); hi = change.get("probability_high")
            if s not in STRATEGIES:
                return False, f"bad strategy {s}"
            if side not in ("buy","sell"):
                return False, f"bad side {side}"
            if not (isinstance(lo,(int,float)) and isinstance(hi,(int,float))):
                return False, "probability_low/high must be numbers"
            if not (0.35 <= lo <= hi <= 0.95):
                return False, f"probability band invalid: low={lo} high={hi} (ต้องอยู่ 0.35-0.95)"
        if act == "set_tpsl":
            # ปรับ "เกณฑ์การสร้าง TP/SL": global = atr_stop_multiplier/min_reward_risk
            #                                    ต่อกลยุทธ์ = *_stop_atr / *_reward_risk
            s = change.get("strategy", "global")
            if s not in tuple(STRATEGIES) + ("global",):
                return False, f"bad strategy {s}"
            touched = False
            for k in ("atr_stop_multiplier", "min_reward_risk"):
                if k in change:
                    v = change.get(k); lim = TPSL_LIMITS[k]
                    if not isinstance(v,(int,float)) or not (lim[0] <= float(v) <= lim[1]):
                        return False, f"{k}={v} out of range [{lim[0]},{lim[1]}]"
                    touched = True
            for k in ("stop_atr", "reward_risk"):
                if k in change:
                    v = change.get(k)
                    lim = TPSL_LIMITS["_stop_atr"] if k == "stop_atr" else TPSL_LIMITS["_reward_risk"]
                    if not isinstance(v,(int,float)) or not (lim[0] <= float(v) <= lim[1]):
                        return False, f"{k}={v} out of range [{lim[0]},{lim[1]}]"
                    if s == "global":
                        return False, f"{k} ต้องระบุ strategy (global ใช้ atr_stop_multiplier/min_reward_risk)"
                    touched = True
            if "enforce_equal_tp_sl" in change and not isinstance(change["enforce_equal_tp_sl"], bool):
                return False, "enforce_equal_tp_sl must be bool"
            if not touched and "enforce_equal_tp_sl" not in change:
                return False, "set_tpsl: ไม่มีฟิลด์ที่จะปรับ"
        if act == "toggle_strategy":
            s = change.get("strategy"); v = change.get("enabled")
            if s not in ("trend","range","mean_reversion","counter_trend","breakout","breakout_reversal"):
                return False, f"bad strategy {s}"
            if not isinstance(v, bool):
                return False, "enabled must be bool"
            # ★ ห้ามปิดกั้นการเทรด (user rule): เปิดได้เท่านั้น — ลดความสำคัญใช้ set_weights แทน
            if v is False:
                return False, ("toggle_strategy enabled=false ถูกห้าม (ห้ามปิดกั้นการเทรด) — "
                               "ใช้ set_weights ลดน้ำหนักกลยุทธ์แทน (0.5-1.5)")
        if act == "set_weights":
            if not isinstance(change.get("strategy_weights"), dict):
                return False, "strategy_weights must be dict"
            for k, val in change["strategy_weights"].items():
                if k not in STRATEGIES:
                    return False, "unknown strategy weight key"
                if not isinstance(val,(int,float)) or not (0.5 <= val <= 1.5):
                    return False, f"weight {k}={val} out of [0.5,1.5]"
        if act == "set_directional_weights":
            dw = change.get("directional_weights")
            if not isinstance(dw, dict):
                return False, "directional_weights must be dict"
            for k, val in dw.items():
                if k not in DIRECTIONAL_KEYS:
                    return False, f"bad directional key {k}"
                if not isinstance(val, (int, float)) or not (0.5 <= val <= 1.5):
                    return False, f"directional weight {k}={val} out of [0.5,1.5]"
        if act == "set_risk":
            if not isinstance(change.get("max_risk_pct"),(int,float)) or not (0.5 <= change["max_risk_pct"] <= 15.0):
                return False, "max_risk_pct out of [0.5,15]"
        # ไม่ให้แก้ protected
        for p in PROTECTED:
            if p in change:
                return False, f"protected key {p}"
    return True, "ok"

def apply_recommendation(rec: dict, config=None):
    cfg = json.loads(json.dumps(config if config is not None else json.load(open(CFG, encoding="utf-8"))))
    sr = cfg["strategy_router"]
    gov = sr["bounded_live"]["governance"]
    for ch in rec.get("changes", []):
        act = ch.get("action")
        if act == "set_gate":
            g = gov.setdefault(ch["strategy"], {})
            g[f"raw_{ch['side']}"] = float(ch["raw_low"])
            g[f"raw_max_{ch['side']}"] = float(ch["raw_high"])
            g[f"weighted_{ch['side']}"] = float(ch["raw_low"])
            g[f"weighted_max_{ch['side']}"] = float(ch["raw_high"])
        elif act == "toggle_strategy":
            sr.setdefault("trade_enabled", {})[ch["strategy"]] = bool(ch["enabled"])
        elif act == "set_weights":
            sr.setdefault("strategy_weights", {}).update({k: float(v) for k, v in ch["strategy_weights"].items()})
        elif act == "set_directional_weights":
            sr.setdefault("directional_weights", {}).update({k: float(v) for k, v in ch["directional_weights"].items()})
        elif act == "set_probability_gate":
            g = gov.setdefault(ch["strategy"], {})
            g[f"probability_{ch['side']}"] = float(ch["probability_low"])
            g[f"probability_max_{ch['side']}"] = float(ch["probability_high"])
        elif act == "set_tpsl":
            # ★ เกณฑ์สร้าง TP/SL — มีผลทันทีหลัง hot reload (ไม่ต้องรีสตาร์ท)
            s = ch.get("strategy", "global")
            for k in ("atr_stop_multiplier", "min_reward_risk"):
                if k in ch:
                    cfg[k] = float(ch[k])
            if "enforce_equal_tp_sl" in ch:
                cfg["enforce_equal_tp_sl"] = bool(ch["enforce_equal_tp_sl"])
            if s != "global":
                if "stop_atr" in ch:
                    sr[f"{s}_stop_atr"] = float(ch["stop_atr"])
                if "reward_risk" in ch:
                    sr[f"{s}_reward_risk"] = float(ch["reward_risk"])
        elif act == "set_risk":
            cfg["max_risk_pct"] = float(ch["max_risk_pct"])
    return cfg

# ---- main ---- (ทำงานเฉพาะเมื่อรันเป็นสคริปต์ — import เพื่อทดสอบ validate() ได้)
def _main():
    from runtime_support import file_lock
    with file_lock(Path(proj) / "work/consumer.lock", timeout=1):
        return consume_once()

FAILED_RETEST_COOLDOWN_SECONDS = 6 * 3600   # คำแนะนำเดิมที่ "ไม่ผ่าน" แล้ว จะไม่ถูกทดสอบซ้ำก่อนเวลานี้


def pick_recommendation():
    """คำแนะนำที่ระบบใช้ = `latest_recommendation.json` **ไฟล์เดียวเท่านั้น**

    ★ เจ้าของระบบกำหนด (19 ก.ย. 2026): "ยึด latest_recommendation.json เป็นหลัก —
      ให้เขียนใส่ไฟล์นี้ ถ้าเปลี่ยนไปใช้ไฟล์อื่น ระบบข้อมูลภายในจะมีปัญหาอีก"

    ดังนั้นทุกฝ่าย (สคริปต์ภายใน และ บอท/agent) ต้องเขียนลงไฟล์นี้
    เพื่อให้มี "จุดส่งต่อ" จุดเดียว — กันข้อมูลภายในแตกเป็นสองทาง
    """
    p = Path(REC_DIR) / "latest_recommendation.json"
    return p if p.exists() else None


def consume_once():
    if (Path(proj) / "work/AUTO_TRADER_STOP").exists():
        print("System intentionally stopped; proposal retained, no apply")
        return
    p = pick_recommendation()
    if p is None:
        return
    rec = json.loads(p.read_text(encoding="utf-8"))
    mode = current_mode(proj)
    if (rec.get("mode_epoch") != mode.get("epoch") or rec.get("mode") != mode["mode"]
            or (mode["mode"] == "internal_only" and rec.get("uses_llm", True))):
        audit("recommendation_rejected", reason="stale or incompatible signal mode")
        return
    ok, err = validate(rec)
    if not ok:
        audit("recommendation_rejected", reason=err, source=Path(p).name)
        return
    cfg = json.loads(Path(CFG).read_text(encoding="utf-8"))
    rec_hash, cfg_hash = digest(rec), digest(cfg)
    applied_path = Path(REC_DIR) / "last_applied.json"
    if applied_path.exists() and json.loads(applied_path.read_text(encoding="utf-8")).get("rec_hash") == rec_hash:
        return
    # คำแนะนำเดิม (hash เดิม) ที่เคยทดสอบไม่ผ่าน → ไม่ทดสอบซ้ำถี่ (กันสแปม + กันโหลดจำลองซ้ำ)
    failed_path = Path(REC_DIR) / "last_failed.json"
    if failed_path.exists():
        try:
            prev = json.loads(failed_path.read_text(encoding="utf-8"))
            if prev.get("rec_hash") == rec_hash:
                age = (datetime.datetime.now(datetime.timezone.utc)
                       - datetime.datetime.fromisoformat(prev.get("ts", ""))).total_seconds()
                if 0 <= age < FAILED_RETEST_COOLDOWN_SECONDS:
                    audit("recommendation_retest_skipped", reason="identical proposal failed recently",
                          age_hours=round(age / 3600, 2), last_reason=prev.get("reason"))
                    return
        except Exception:
            pass
    run = Path(REC_DIR) / "evaluations" / (datetime.datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + __import__("uuid").uuid4().hex[:10])
    run.mkdir(parents=True)
    atomic_json(run / "recommendation.json", rec)
    atomic_json(run / "baseline.json", cfg)
    tester = Path(L) / "llm_recommendation_tester.py"
    args = [sys.executable, str(tester), "--rec", str(run / "recommendation.json"),
            "--config", str(run / "baseline.json"), "--verdict", str(run / "verdict.json")]
    try:
        tested = subprocess.run(args, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        audit("recommendation_blocked_by_test", reason="evaluation timeout")
        return
    if tested.stdout: print(tested.stdout.strip())
    vpath = run / "verdict.json"
    verdict = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else {}
    if (tested.returncode != 0 or verdict.get("status") != "passed"
            or verdict.get("rec_hash") != rec_hash or verdict.get("config_hash") != cfg_hash):
        # จำคำแนะนำที่ล้มเหลวไว้ (hash + เวลา + ตัวเลขเทียบ) → รอบถัดไปจะข้ามไปก่อน ไม่ทดสอบซ้ำถี่
        atomic_json(failed_path, {
            "rec_hash": rec_hash,
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "reason": verdict.get("reason", "invalid test result"),
            "base_total_r": (verdict.get("base") or {}).get("total_r"),
            "proposed_total_r": (verdict.get("proposed") or {}).get("total_r"),
            "base_trades": (verdict.get("base") or {}).get("trades"),
            "proposed_trades": (verdict.get("proposed") or {}).get("trades"),
        })
        audit("recommendation_blocked_by_test", reason=verdict.get("reason", "invalid test result"),
              base_total_r=(verdict.get("base") or {}).get("total_r"),
              proposed_total_r=(verdict.get("proposed") or {}).get("total_r"))
        return
    # Serialized compare-and-swap closes mode/config races and preserves the tested baseline.
    if (Path(proj) / "work/AUTO_TRADER_STOP").exists() or current_mode(proj) != mode:
        audit("recommendation_rejected", reason="mode changed or system stopped during test")
        return
    if not p.exists() or digest(json.loads(p.read_text(encoding="utf-8"))) != rec_hash:
        audit("recommendation_rejected", reason="proposal changed during evaluation")
        return
    from auto_trader import load_config
    def validated_apply(current):
        candidate = apply_recommendation(rec, current)
        load_config(candidate)
        return candidate
    update_json(CFG, validated_apply, expected_hash=cfg_hash)
    atomic_json(Path(APPLIED_DIR) / (run.name + ".json"), rec)
    # Keep pending file: exact hash de-dup prevents repeat; never delete a newer proposal.
    atomic_json(Path(REC_DIR) / "last_applied.json", {"rec_hash": rec_hash, "config_hash": cfg_hash})
    audit("recommendation_applied", changes=rec["changes"], mode=mode["mode"], evidence=str(run.name))
    print("Recommendation applied atomically; trader hot reloads, no restart or live authorization change")

if __name__ == "__main__":
    _main()
