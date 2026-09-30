# -*- coding: utf-8 -*-
"""loss_analysis.py — ตัววิเคราะห์สาเหตุการขาดทุน (ถาวร · ไม่ใช้ AI · $0)

คำสั่งของเจ้าของระบบ (29 ก.ย. 2026): "เวลารันที่ปรึกษาทุกครั้งต้องเช็คสาเหตุการขาดทุนด้วย
ถ้ามีไม้ขาดทุนระหว่างช่วงที่รัน + หาวิธีแก้ไข"
→ สคริปต์นี้คือเครื่องยนต์ของหน้าที่นั้น: วิเคราะห์ไม้ขาดทุน "ตั้งแต่รอบที่แล้วจนถึงตอนนี้"
   แล้วสรุปสาเหตุ + เสนอวิธีแก้ (ไม่แก้เอง) + เขียนรายงานรายรอบไว้ที่ work/loss_reports/

ใช้:  python tools/loss_analysis.py            # วิเคราะห์รอบใหม่ (จำช่วงด้วย state)
      python tools/loss_analysis.py --hours 24 # วิเคราะห์ย้อนหลัง 24 ชม. (ไม่แตะ state)
      python tools/loss_analysis.py --json     # ส่งออก JSON สำหรับให้บอทชั้นบนอ่าน
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.dirname(HERE)
PROJECT = os.path.dirname(os.path.dirname(BRIDGE))
WORK = os.path.join(PROJECT, "work")
STATE_FILE = os.path.join(WORK, "loss_analysis_state.json")
REPORT_DIR = os.path.join(WORK, "loss_reports")
CONFIG_FILE = os.path.join(BRIDGE, "auto_config.json")

REASON = {}
try:
    import MetaTrader5 as mt5
    REASON = {
        mt5.DEAL_REASON_CLIENT: "สั่งมือ",
        mt5.DEAL_REASON_MOBILE: "มือถือ",
        mt5.DEAL_REASON_WEB: "เว็บ",
        mt5.DEAL_REASON_EXPERT: "ระบบอัตโนมัติปิดเอง",
        mt5.DEAL_REASON_SL: "ชน SL",
        mt5.DEAL_REASON_TP: "ชน TP",
        mt5.DEAL_REASON_SO: "Stop Out",
    }
except Exception:
    mt5 = None


def load_config() -> dict:
    try:
        with io.open(CONFIG_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def load_state() -> dict:
    try:
        with io.open(STATE_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        os.makedirs(WORK, exist_ok=True)
        with io.open(STATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _head_time(path: str, start: int):
    """เวลา (epoch) ของบรรทัดแรกที่อ่านได้หลังตำแหน่ง start — ใช้หาขอบหน้าต่างสแกน"""
    try:
        with io.open(path, "rb") as fh:
            fh.seek(start)
            head = fh.read(64 * 1024).decode("utf-8", "replace")
        lines = head.splitlines()
        if start > 0 and lines:
            lines = lines[1:]           # บรรทัดแรกอาจถูกตัดกลางคัน — ข้าม
        for ln in lines[:12]:
            if not ln.strip():
                continue
            try:
                t = json.loads(ln).get("time")
            except Exception:
                continue
            if t:
                try:
                    return dt.datetime.fromisoformat(str(t).replace("Z", "+00:00")).timestamp()
                except Exception:
                    return None
    except Exception:
        return None
    return None


def tail_audit_events(event_names, since_ts, max_bytes=512 * 1024, hard_cap=96 * 1024 * 1024) -> int:
    """นับเหตุการณ์ในบันทึก โดยขยายหน้าต่างจากท้ายไฟล์แบบปรับได้จนถึงเวลา since_ts

    ★ แก้ 30 ก.ย. 2026 (ที่ปรึกษา): เดิมอ่านท้ายไฟล์คงที่ 512KB — เมื่อบรรทัดเหตุการณ์
    ยาวขึ้นมาก (dual_agent/skip มี payload ใหญ่) หน้าต่างนี้ครอบเพียงไม่กี่นาที
    ทำให้ตัวเลข armed/blocked ขาดหายและรายงานตีความผิด (เช่น 'ติดอาวุธ 0 ครั้ง'
    ทั้งที่บันทึกเต็มมี 14 ครั้ง) — จึงขยายหน้าต่าง ×4 จนกว่าหัวหน้าต่างจะเก่ากว่า since_ts
    (เพดาน hard_cap กันอ่านหนักเกิน)
    """
    path = os.path.join(WORK, "auto_trader_audit.jsonl")
    if not os.path.exists(path):
        return 0
    needles = [str(e) for e in event_names]
    count = 0
    try:
        size = os.path.getsize(path)
        win = max_bytes if since_ts else hard_cap
        start = max(0, size - win)
        while since_ts and start > 0 and win < hard_cap:
            t0 = _head_time(path, start)
            if t0 is not None and t0 <= since_ts:
                break
            win *= 4
            start = max(0, size - win)
        with io.open(path, "rb") as fh:
            fh.seek(start)
            tail = fh.read().decode("utf-8", "replace")
        for line in tail.splitlines():
            if not any(n in line for n in needles):
                continue
            try:
                data = json.loads(line)
            except Exception:
                continue
            ts = data.get("time") or ""
            if since_ts:
                try:
                    when = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                except Exception:
                    continue
                if when.timestamp() < since_ts:
                    continue
            count += 1
    except Exception:
        return count
    return count


def collect_trades(since_ts: float):
    """คืนรายการไม้ที่ปิดแล้ว (เข้าคู่ in/out ผ่าน position_id)"""
    if mt5 is None or not mt5.initialize():
        return None
    try:
        frm = dt.datetime.fromtimestamp(since_ts) - dt.timedelta(hours=1)
        to = dt.datetime.now() + dt.timedelta(hours=1)
        deals = mt5.history_deals_get(frm, to) or []
        opens, trades = {}, []
        for d in deals:
            if d.entry == 0:
                opens[d.position_id] = d
        for d in deals:
            if d.entry != 1:
                continue
            o = opens.get(d.position_id)
            if not o:
                continue
            if d.time < since_ts:
                continue
            trades.append({
                "open_time": dt.datetime.fromtimestamp(o.time),
                "close_time": dt.datetime.fromtimestamp(d.time),
                "side": "SELL" if o.type == 1 else "BUY",
                "lots": o.volume,
                "open_price": o.price,
                "close_price": d.price,
                "profit": d.profit + d.swap + d.commission + o.swap + o.commission,
                "reason": REASON.get(d.reason, "อื่น(%s)" % d.reason),
                "minutes": int((d.time - o.time) / 60),
            })
        trades.sort(key=lambda t: t["close_time"])
        return trades
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def analyse(trades, config) -> dict:
    wins = [t for t in trades if t["profit"] > 0]
    losses = [t for t in trades if t["profit"] <= 0]
    out = {
        "total": len(trades),
        "wins": len(wins), "win_sum": sum(t["profit"] for t in wins),
        "losses": len(losses), "loss_sum": sum(t["profit"] for t in losses),
        "net": sum(t["profit"] for t in trades),
        "loss_list": losses,
    }

    # รูปแบบ 1: เข้าไม้ใหม่เร็วแค่ไหนหลังขาดทุน (เทียบกับกติกากันแก้แค้น)
    rg = (config.get("revenge_guard") or {})
    cooldown = float(rg.get("cooldown_minutes") or 15)
    fast = []
    for i, t in enumerate(trades):
        if t["profit"] > 0 or i + 1 >= len(trades):
            continue
        nxt = trades[i + 1]
        gap = (nxt["open_time"] - t["close_time"]).total_seconds() / 60.0
        if 0 <= gap <= cooldown:
            fast.append({"after": t["close_time"], "gap_min": round(gap, 1),
                         "side": nxt["side"], "cooldown_setting": cooldown})
    out["fast_reentry"] = fast

    # รูปแบบ 2: ขาดทุนติดกันเป็นชุด
    runs, cur = [], []
    for t in trades:
        if t["profit"] <= 0:
            cur.append(t)
        else:
            if len(cur) >= 3:
                runs.append(cur)
            cur = []
    if len(cur) >= 3:
        runs.append(cur)
    out["loss_runs"] = [{"count": len(r), "sum": sum(x["profit"] for x in r),
                         "start": r[0]["open_time"], "end": r[-1]["close_time"]} for r in runs]
    out["max_consecutive_losses_setting"] = config.get("max_consecutive_losses")

    # รูปแบบ 3: ไม้ที่ถูกตัดเร็วผิดปกติ
    out["fast_sl"] = [{"time": t["open_time"], "minutes": t["minutes"], "profit": t["profit"]}
                      for t in losses if t["minutes"] <= 5]

    # รูปแบบ 4: ฝั่งและช่วงเวลา
    out["sides"] = {}
    for t in trades:
        key = t["side"]
        s = out["sides"].setdefault(key, {"win": 0, "loss": 0, "net": 0.0})
        s["net"] += t["profit"]
        s["win" if t["profit"] > 0 else "loss"] += 1
    out["loss_hours"] = {}
    for t in losses:
        h = t["open_time"].strftime("%H")
        out["loss_hours"][h] = out["loss_hours"].get(h, 0) + 1
    return out


def build_fixes(a, config) -> list:
    """เสนอวิธีแก้จากหลักฐานจริง (ไม่แก้เอง)"""
    fixes = []
    if a["fast_reentry"]:
        fixes.append(
            "เข้าไม้ใหม่เร็วหลังขาดทุน %d ครั้ง (เร็วสุด %.1f นาที) แต่กติกากันแก้แค้นตั้งไว้ %.0f นาที → "
            "ตรวจว่ากลไกกันแก้แค้น 'ติดอาวุธ' จริงไหม (ดู event revenge_armed ในบันทึก)" % (
                len(a["fast_reentry"]),
                min(x["gap_min"] for x in a["fast_reentry"]),
                a["fast_reentry"][0]["cooldown_setting"],
            ))
    if a["loss_runs"]:
        setting = a["max_consecutive_losses_setting"]
        avoid = sum(r["sum"] for r in a["loss_runs"])
        fixes.append(
            "มีชุดขาดทุนติดกัน %d ชุด (รวม %.2f USD, แย่สุด %d ไม้) แต่ max_consecutive_losses=%s → "
            "ถ้าเปิดเป็น 3 จะหยุดพักหลังแพ้ติดกัน 3 ไม้ ลดความเสียหายชุดใหญ่ได้" % (
                len(a["loss_runs"]), avoid, max(r["count"] for r in a["loss_runs"]), setting))
    if a["fast_sl"]:
        fixes.append(
            "มีไม้ถูกตัดใน ≤5 นาที %d ไม้ (เร็วสุด %d นาที) → พิจารณาช่วงเวลาที่ผันผวนสูง "
            "หรือเพิ่มตัวกรองความผันผวนก่อนเข้า" % (len(a["fast_sl"]),
                                                   min(x["minutes"] for x in a["fast_sl"])))
    sides = a["sides"]
    if len(sides) == 1:
        only = list(sides)[0]
        fixes.append(
            "เทรดฝั่งเดียว 100%% (%s) → ถ้าตลาดกลับทิศจะขาดทุนต่อเนื่อง ควรทบทวนว่าทำไมฝั่งตรงข้ามผ่านประตูไม่ได้" % only)
    if not fixes:
        fixes.append("ไม่พบรูปแบบผิดปกติในรอบนี้ — รักษาค่าตั้งเดิมไว้")
    return fixes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=0, help="วิเคราะห์ย้อนหลังกี่ชั่วโมง (ไม่แตะ state)")
    ap.add_argument("--json", action="store_true", help="ส่งออก JSON")
    args = ap.parse_args()

    state = load_state()
    now = dt.datetime.now()
    if args.hours:
        since = now.timestamp() - args.hours * 3600
        label = "ย้อนหลัง %.0f ชม." % args.hours
    else:
        since = float(state.get("last_run_ts") or (now.timestamp() - 24 * 3600))
        label = "ตั้งแต่รอบที่แล้ว (%s)" % state.get("last_run_label", "เริ่มต้น")

    config = load_config()
    trades = collect_trades(since)
    if trades is None:
        print("MT5 ไม่พร้อม — ข้ามการวิเคราะห์รอบนี้")
        return 2

    a = analyse(trades, config)
    a["armed_events"] = tail_audit_events(["revenge_armed"], since)
    a["blocked_events"] = tail_audit_events(["revenge guard", "revenge_guard", "revenge_blocked"], since)
    fixes = build_fixes(a, config)

    lines = []
    lines.append("══ วิเคราะห์สาเหตุการขาดทุน (%s) ══" % label)
    lines.append("ไม้ที่ปิด: %d · ชนะ %d (+%.2f) · แพ้ %d (%.2f) · สุทธิ %+.2f USD" % (
        a["total"], a["wins"], a["win_sum"], a["losses"], a["loss_sum"], a["net"]))
    if a["sides"]:
        lines.append("แยกฝั่ง: " + " · ".join(
            "%s ชนะ%d/แพ้%d สุทธิ%+.2f" % (k, v["win"], v["loss"], v["net"])
            for k, v in a["sides"].items()))
    lines.append("กลไกกันแก้แค้น: ติดอาวุธ %d ครั้ง · บล็อก %d ครั้ง (ช่วงนี้)" % (
        a["armed_events"], a["blocked_events"]))
    if a["losses"]:
        lines.append("ไม้ขาดทุนล่าสุด %d ไม้:" % min(len(a["loss_list"]), 5))
        for t in a["loss_list"][-5:]:
            lines.append("  · %s %s→%s (%d นาที) %+.2f [%s]" % (
                t["side"], t["open_time"].strftime("%d/%m %H:%M"),
                t["close_time"].strftime("%H:%M"), t["minutes"], t["profit"], t["reason"]))
    lines.append("")
    lines.append("สาเหตุที่พบ + วิธีแก้ที่เสนอ:")
    for i, f in enumerate(fixes, 1):
        lines.append("  %d) %s" % (i, f))

    report = "\n".join(lines)
    print(report)

    try:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, now.strftime("%Y-%m-%d_%H%M") + ".md")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
    except Exception:
        pass

    if args.json:
        print(json.dumps({k: v for k, v in a.items() if k != "loss_list"}, ensure_ascii=False,
                         default=str, indent=2))

    if not args.hours:
        state["last_run_ts"] = now.timestamp()
        state["last_run_label"] = now.strftime("%d/%m %H:%M")
        state["last_report"] = {"total": a["total"], "losses": a["losses"], "net": round(a["net"], 2)}
        save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())