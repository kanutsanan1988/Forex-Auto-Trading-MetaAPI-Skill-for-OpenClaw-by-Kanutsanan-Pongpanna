# -*- coding: utf-8 -*-
"""question_board.py — กระดานคำถามไม้ขาดทุน (บอทตั้งคำถาม · ที่ปรึกษาแก้)

คำสั่งเจ้าของระบบ (29 ก.ย. 2026):
  "ถ้ามีไม้ขาดทุนระหว่างการเทรด ให้แอดมินบอทกับบอทงานวิจัย 10 นาทีเป็นคนตั้งคำถาม
   ไว้ในกระดานคำถาม เพื่อให้ที่ปรึกษาสามารถแก้ไขได้"

หน้าที่:
  --scan [--asker admin|research]  : บอทเรียกทุกรอบ — วิเคราะห์ไม้ขาดทุนแล้วตั้งคำถามเข้าบoard
  --list [--open]                  : ดูคำถาม (ค่าเริ่มต้น = ทั้งหมด · --open = ที่ยังไม่ตอบ)
  --answer <id> --text "..." [--fixed] : ที่ปรึกษาตอบ/ระบุวิธีแก้ (ที่ปรึกษา = Hermes/สมองหลัก)
  --stats                          : สรุปจำนวน

ไฟล์: work/question_board.jsonl (ฐานข้อมูล) + work/question_board.md (อ่านง่าย)
ไม่มีค่าใช้จ่าย AI (สคริปต์ล้วน) · ใช้ข้อมูล MT5 จริงเท่านั้น
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # outputs/mt5_python_bridge
SYSTEM_ROOT = os.path.dirname(os.path.dirname(ROOT))   # เทรดทองคำ
WORK = os.path.join(SYSTEM_ROOT, "work")
BOARD = os.path.join(WORK, "question_board.jsonl")
BOARD_MD = os.path.join(WORK, "question_board.md")

ASKERS = {"admin": "แอดมินบอท (30 นาที)", "research": "บอทงานวิจัย (10 นาที)",
          "advisor": "ที่ปรึกษา (สมองหลัก)"}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load() -> list[dict]:
    if not os.path.exists(BOARD):
        return []
    out = []
    with io.open(BOARD, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                continue
    return out


def append(entry: dict) -> None:
    os.makedirs(WORK, exist_ok=True)
    with io.open(BOARD, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    render_md()


def render_md() -> None:
    rows = load()
    openn = [r for r in rows if r.get("status") == "open"]
    lines = ["# กระดานคำถามไม้ขาดทุน (บอทตั้งคำถาม · ที่ปรึกษาแก้)", "",
             "_อัปเดต: %s · คำถามทั้งหมด %d · ยังไม่ตอบ %d_" % (_now(), len(rows), len(openn)), ""]
    if openn:
        lines += ["## ยังไม่ตอบ (%d)" % len(openn), ""]
        for r in openn:
            lines += ["### [%s] %s — โดย %s" % (r.get("id"), r.get("title"), r.get("asker_label")),
                      "- เวลา: %s" % r.get("time"),
                      "- หลักฐาน: %s" % r.get("evidence", "-"),
                      "- คำถาม: %s" % r.get("question"),
                      "- ตัวเลข: `%s`" % json.dumps(r.get("facts") or {}, ensure_ascii=False), ""]
    answered = [r for r in rows if r.get("status") == "answered"]
    if answered:
        lines += ["## ตอบแล้ว/แก้แล้ว (%d)" % len(answered), ""]
        for r in answered[-20:]:
            lines += ["- [%s] %s → **%s**%s" % (
                r.get("id"), r.get("title"),
                (r.get("answer") or "")[:200],
                "  _(แก้แล้ว %s)_" % (r.get("answered_time") or "") if r.get("fixed") else ""), ]
            lines += [""]
    with io.open(BOARD_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def _qid(kind: str, key: str) -> str:
    return "%s-%s" % (kind, hashlib.sha1(key.encode("utf-8")).hexdigest()[:6])


def _exists(qid: str) -> bool:
    return any(r.get("id") == qid for r in load())


def post(kind: str, key: str, title: str, question: str, evidence: str,
         facts: dict, asker: str = "research") -> str | None:
    qid = _qid(kind, key)
    if _exists(qid):
        return None
    entry = {
        "id": qid, "time": _now(), "status": "open", "kind": kind,
        "title": title, "question": question, "evidence": evidence, "facts": facts,
        "asker": asker, "asker_label": ASKERS.get(asker, asker),
        "answer": None, "answered_by": None, "answered_time": None, "fixed": False,
    }
    append(entry)
    return qid


def scan(asker: str = "research", hours: float = 12.0, min_loss: float = 0.30) -> list[str]:
    """วิเคราะห์ไม้ขาดทุนจริง แล้วตั้งคำถามเข้าบoard (ไม่ซ้ำ)"""
    sys.path.insert(0, HERE)
    created: list[str] = []
    try:
        import loss_analysis as LA  # type: ignore
    except Exception as exc:
        print("  ⚠️ นำเข้าเครื่องมือวิเคราะห์ไม่ได้:", exc)
        return created

    since = time.time() - float(hours) * 3600.0
    try:
        trades = LA.collect_trades(since) or []
        a = LA.analyse(trades, LA.load_config())
    except Exception as exc:
        print("  ⚠️ วิเคราะห์ไม่สำเร็จ:", exc)
        return created

    # ── แปลงผลวิเคราะห์จริง → รูปแบบที่กระดานใช้ ─────────────────────
    raw_losses = a.get("loss_list") or []
    losses = [{
        "ticket": t["open_time"].strftime("%H:%M"),
        "time": t["close_time"].strftime("%Y-%m-%dT%H:%M:%S"),
        "side": "sell" if t["side"] == "SELL" else "buy",
        "profit": float(t["profit"]), "minutes": float(t["minutes"]),
        "entry": float(t["open_price"]), "close": float(t["close_price"]),
        "sl": 0.0, "tp": 0.0, "close_reason": t.get("reason") or "-",
    } for t in raw_losses]

    # ชุดขาดทุนติดกัน (≥2 ไม้) คำนวณเองจากลำดับไม้จริง
    clusters, cur = [], []
    for t in trades:
        if float(t["profit"]) <= 0:
            cur.append(t)
        else:
            if len(cur) >= 2:
                clusters.append(cur)
            cur = []
    if len(cur) >= 2:
        clusters.append(cur)
    cluster_view = [{
        "sum": sum(float(x["profit"]) for x in c),
        "items": [{"ticket": c[0]["open_time"].strftime("%H:%M"),
                   "side": "sell" if c[0]["side"] == "SELL" else "buy",
                   "time": x["close_time"].strftime("%Y-%m-%dT%H:%M:%S")} for x in c],
    } for c in clusters]

    # ฝั่งกันแก้แค้น: ติดอาวุธกี่ครั้ง + เข้าใหม่เร็วแค่ไหน
    try:
        armed = LA.tail_audit_events(["revenge_armed"], since)
    except Exception:
        armed = 0
    rg = (LA.load_config().get("revenge_guard") or {})
    guard = {
        "armed": armed if isinstance(armed, int) else 0,
        "cooldown_minutes": float(rg.get("cooldown_minutes") or 15),
        "re_entries": [{
            "after": (x["after"].strftime("%Y-%m-%dT%H:%M:%S") if hasattr(x["after"], "strftime") else str(x["after"])),
            "gap_min": float(x.get("gap_min") or 0.0),
        } for x in (a.get("fast_reentry") or [])],
    }
    report = {"losses": losses, "clusters": cluster_view, "guard": guard,
              "total_trades": a.get("total"), "net": a.get("net")}

    losses = report.get("losses") or []
    if not losses:
        print("  ✓ ไม่มีไม้ขาดทุนในช่วง %.0f ชม. — ไม่ตั้งคำถาม" % hours)
        return created

    total = sum(float(x.get("profit") or 0.0) for x in losses)
    print("  พบไม้ขาดทุน %d ไม้ รวม %.2f USD" % (len(losses), total))

    # ── คำถาม 1: ชุดขาดทุนติดกัน (≥2 ไม้) ───────────────────────────
    for cluster in (report.get("clusters") or []):
        items = cluster.get("items") or []
        if len(items) < 2 or abs(float(cluster.get("sum") or 0.0)) < min_loss:
            continue
        first, last = items[0], items[-1]
        key = "%s|%s" % (first.get("time"), last.get("time"))
        qid = post(
            "cluster", key,
            "ขาดทุนติดกัน %d ไม้ (−%.2f USD)" % (len(items), abs(float(cluster.get("sum") or 0.0))),
            "ทำไมระบบยอมเข้าไม้ %d ครั้งติดกันในช่วงนี้ ทั้งที่ขาดทุนสะสมแล้ว? "
            "มีกลไกใดควรหยุดก่อนไม้ที่ %d หรือไม่ และถ้าควร มีเกณฑ์อะไรที่แม่นพอจะไม่ตัดสัญญาณดีทิ้ง?"
            % (len(items), len(items)),
            "ไม้ที่ %s–%s · ฝั่ง %s · ปิด %s · รวม %.2f USD" % (
                items[0].get("ticket"), items[-1].get("ticket"), first.get("side"),
                "%s → %s" % (first.get("time", "")[11:16], last.get("time", "")[11:16]),
                float(cluster.get("sum") or 0.0)),
            {"ไม้": len(items), "รวม USD": round(float(cluster.get("sum") or 0.0), 2),
             "ฝั่ง": first.get("side"), "ช่วง": "%s-%s" % (first.get("time", "")[11:16], last.get("time", "")[11:16])},
            asker=asker)
        if qid:
            created.append(qid)

    # ── คำถาม 2: ปิดเร็วผิดปกติ (≤5 นาที) ────────────────────────────
    fast = [x for x in losses if float(x.get("minutes") or 0.0) <= 5.0
            and abs(float(x.get("profit") or 0.0)) >= min_loss]
    for x in fast[:3]:
        key = str(x.get("ticket"))
        qid = post(
            "fast_sl", key,
            "ไม้ %s ถูกปิดใน %.0f นาที (−%.2f USD)" % (x.get("ticket"), float(x.get("minutes") or 0), abs(float(x.get("profit") or 0.0))),
            "ทำไมไม้ %s ฝั่ง %s ถูกตัดขาดทุนภายใน %.0f นาที? "
            "SL สั้น/ไกลเกินไปเทียบกับความผันผวนจริงหรือไม่ ควรใช้ ATR กี่เท่าในสภาวะแบบนี้? "
            "(เทียบกับบันทึกการตัดสินใจของรอบนั้นด้วย)"
            % (x.get("ticket"), x.get("side"), float(x.get("minutes") or 0)),
            "เข้า %.2f · ปิด %.2f · ถือ %.0f นาที · ปิดโดย %s" % (
                float(x.get("entry") or 0), float(x.get("close") or 0),
                float(x.get("minutes") or 0), x.get("close_reason") or "-"),
            {"นาทีที่ถือ": round(float(x.get("minutes") or 0), 1), "ขาดทุน USD": round(float(x.get("profit") or 0), 2),
             "ฝั่ง": x.get("side"), "ชั่วโมง": (x.get("time") or "")[11:16]},
            asker=asker)
        if qid:
            created.append(qid)

    # ── คำถาม 3: เข้าไม้ใหม่เร็วหลังขาดทุน / กันแก้แค้นผิดปกติ ─────────
    g = report.get("guard") or {}
    re_entries = g.get("re_entries") or []
    if re_entries:
        quick = [r for r in re_entries if float(r.get("gap_min") or 99) < 15.0]
        key = "revenge|%s" % (quick[0].get("after") if quick else "none")   # ★ คงที่: ใช้เวลาการเข้าใหม่ครั้งแรก
        qid = post(
            "revenge", key,
            "เข้าไม้ใหม่ใน %.1f นาทีหลังขาดทุน (%d ครั้งเร็วเกินกำหนด)" % (
                float(quick[0].get("gap_min") or 0) if quick else 0.0, len(quick)),
            "ทำไมยังมีการเข้าไม้ใหม่เร็วภายใน 15 นาทีหลังขาดทุน %d ครั้ง (เร็วสุด %.1f นาที)? "
            "กันแก้แค่นติดอาวุธ %s ครั้ง — ถ้า 0 ครั้งคือบั๊ก ถ้ามีแต่ยังผ่านได้ เกณฑ์คะแนนต้องเข้มขึ้นแค่ไหน?"
            % (len(quick), float(quick[0].get("gap_min") or 0) if quick else 0.0,
               g.get("armed") if g.get("armed") is not None else "ไม่ทราบ"),
            "ช่วงวิเคราะห์ %.0f ชม. · ไม้ขาดทุน %d ไม้ · เข้าใหม่เร็ว %d ครั้ง" % (
                hours, len(losses), len(quick)),
            {"เข้าใหม่เร็ว (นาที)": [round(float(r.get("gap_min") or 0), 1) for r in quick[:5]],
             "armed": g.get("armed"), "cooldown นาที": g.get("cooldown_minutes")},
            asker=asker)
        if qid:
            created.append(qid)

    # ── คำถาม 4: ฝั่งเดียว 100% (ถ้าขาดทุนทั้งหมดฝั่งเดียว) ────────────
    sides = {}
    for x in losses:
        sides[str(x.get("side"))] = sides.get(str(x.get("side")), 0) + 1
    if len(sides) == 1 and len(losses) >= 5:
        only = list(sides)[0]
        key = "side-%s-%s" % (only, (losses[0].get("time") or "")[:10])     # ★ คงที่: ฝั่ง + วันแรกที่พบ
        qid = post(
            "one_side", key,
            "ไม้ขาดทุน %d ไม้เป็นฝั่ง %s ทั้งหมด" % (len(losses), only),
            "ทำไมไม้ขาดทุนทั้งหมดเป็นฝั่ง %s (จาก %d ไม้)? "
            "ฝั่งตรงข้ามไม่ผ่าน 36 ค่าจริงเพราะตลาดเป็นทิศเดียว หรือเกณฑ์ฝั่งตรงข้ามตึงเกินไป? "
            "ต้องมีมาตรการกันขาดทุนต่อเนื่องเมื่อตลาดกลับทิศหรือไม่?" % (only, len(losses)),
            "รวมขาดทุน %.2f USD · ช่วง %.0f ชม." % (total, hours),
            {"ฝั่ง": sides, "รวมขาดทุน USD": round(total, 2)}, asker=asker)
        if qid:
            created.append(qid)

    return created


def show(only_open: bool = False) -> None:
    rows = load()
    if only_open:
        rows = [r for r in rows if r.get("status") == "open"]
    if not rows:
        print("  (ไม่มีคำถาม%s)" % (" ที่ยังไม่ตอบ" if only_open else ""))
        return
    for r in rows:
        mark = "○" if r.get("status") == "open" else "●"
        print("  %s [%s] %s" % (mark, r.get("id"), r.get("title")))
        print("      ตั้งโดย %s · %s" % (r.get("asker_label"), r.get("time")))
        if r.get("status") == "open":
            print("      ถาม: %s" % (r.get("question") or "")[:160])
        else:
            print("      ตอบ: %s%s" % ((r.get("answer") or "")[:160],
                                       "  [แก้แล้ว]" if r.get("fixed") else ""))


def answer(qid: str, text: str, fixed: bool = False) -> int:
    rows = load()
    hit = None
    for r in rows:
        if r.get("id") == qid:
            hit = r
            break
    if hit is None:
        print("  ✗ ไม่พบคำถาม %s" % qid)
        return 2
    hit["status"] = "answered"
    hit["answer"] = text
    hit["answered_by"] = ASKERS["advisor"]
    hit["answered_time"] = _now()
    hit["fixed"] = bool(fixed)
    with io.open(BOARD, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    render_md()
    print("  ✓ ตอบแล้ว [%s]%s" % (qid, " · ระบุว่าแก้แล้ว" if fixed else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="กระดานคำถามไม้ขาดทุน")
    ap.add_argument("--scan", action="store_true", help="บอทเรียก: วิเคราะห์ไม้ขาดทุนแล้วตั้งคำถาม")
    ap.add_argument("--list", action="store_true", help="แสดงคำถามทั้งหมด")
    ap.add_argument("--open", action="store_true", help="แสดงเฉพาะที่ยังไม่ตอบ")
    ap.add_argument("--answer", metavar="ID", help="ตอบคำถามรหัสนี้")
    ap.add_argument("--text", default="", help="ข้อความคำตอบ/วิธีแก้")
    ap.add_argument("--fixed", action="store_true", help="ระบุว่าแก้ไขแล้ว")
    ap.add_argument("--stats", action="store_true", help="สรุปจำนวน")
    ap.add_argument("--asker", default="research", choices=["admin", "research"], help="ใครเป็นคนตั้งคำถามรอบนี้")
    ap.add_argument("--hours", type=float, default=12.0, help="ย้อนหลังกี่ชั่วโมง (ค่าเริ่มต้น 12)")
    args = ap.parse_args()

    if args.answer:
        return answer(args.answer, args.text or "(ที่ปรึกษาตอบ)", args.fixed)

    if args.scan:
        print("📋 สแกนไม้ขาดทุน → ตั้งคำถามเข้าบoard (ผู้ถาม: %s)" % ASKERS.get(args.asker))
        made = scan(asker=args.asker, hours=args.hours)
        print("  ตั้งคำถามใหม่ %d ข้อ" % len(made))
        for q in made:
            print("   + %s" % q)
        return 0

    if args.stats:
        rows = load()
        o = sum(1 for r in rows if r.get("status") == "open")
        f = sum(1 for r in rows if r.get("fixed"))
        print("  คำถามทั้งหมด %d · ยังไม่ตอบ %d · แก้แล้ว %d" % (len(rows), o, f))
        return 0

    show(only_open=args.open)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())