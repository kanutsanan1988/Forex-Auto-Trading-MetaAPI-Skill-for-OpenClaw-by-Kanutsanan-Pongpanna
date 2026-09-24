#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ช่องปรึกษาระหว่างบอท 2 ตัว (Inter-Bot Consultation) — "บอทคุยกัน/ปรึกษากันได้"

เจ้าของระบบกำหนด (23 ก.ย. 2026): "ผมหมายถึงบอททั้ง 2 ตัวคุยกันปรึกษากันได้นะครับ"

═══════════════════════════════════════════════════════════════════════════
ทำไมต้อง 'มีโครงสร้าง' ไม่ใช่แชทอิสระ (ประเมินจากข้อเท็จจริงของระบบนี้)
═══════════════════════════════════════════════════════════════════════════
1. **รอบไม่พร้อมกัน**: บอทโหมด 2 ทำงานทุก 10 นาที · แอดมินบอททุก 30 นาที
   → ถ้าคุยแบบรอคำตอบทันที รอบจะค้าง/ช้า ✗ ⇒ ใช้วิธี 'ฝากคำถาม–ตอบข้ามรอบ' (async)
2. **โควตา + อายุ**: จำกัดคำถามค้างต่อบอท (MAX_OPEN) และมีอายุ (TTL)
   → กันวนคุยกันเอง กันเปลือง และกันคำถามเก่าที่ไม่เกี่ยวนิ่งค้าง ✗⇒ ✓
3. **ตรวจย้อนกลับได้**: เก็บทุกอย่างในไฟล์ JSONL (asks/answers) — ใครถาม ใครตอบ เมื่อไร
4. **คำตอบไม่ใช่คำสั่ง**: บอทผู้ถามยังต้องใช้ "ตัวเลขจริง + Jev + ด่านความปลอดภัย" ตัดสินเอง
   (กติกาเจ้าของระบบ: ห้ามสมมติ · ห้ามเปลี่ยนโครงสร้างเอง · เงินจริงต้องยืนยัน)
5. **ห้ามปรึกษาเรื่องที่ต้องห้าม**: คีย์สงวน · ตัวเทรด · kill switch · โครงสร้างโค้ด (ตายตัว)
   ※ ยกเว้น **สมองหลัก (hermes)** = มีอำนาจเท่าเจ้าของระบบ (23 ก.ย. 2026) จึงไม่ติดตัวกันนี้

ใช้ (บอทเท่านั้น — ระบุบทบาทตัวเองเสมอ):
  ask    : python tools/interbot.py ask --from mode2 --to admin --topic freq \
             --question "ความถี่ 3.4 ไม้/วัน ถือว่าสูงเกินไปไหม" --payload '{"trades_per_day":3.4}'
  answer : python tools/interbot.py answer --from admin --ask-id <id> \
             --stance disagree --answer "ยังไม่ควรเพิ่มความถี่ เพราะ net/trade ยังลบ"
  inbox  : python tools/interbot.py inbox --role mode2     # คำถามที่รอฉันตอบ + คำตอบของฉัน
"""
import argparse
import datetime
import io
import json
import os
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BRIDGE))
DIR = os.path.join(ROOT, "work", "interbot")
ASKS = os.path.join(DIR, "asks.jsonl")
ANSWERS = os.path.join(DIR, "answers.jsonl")

ROLES = ("mode2", "admin", "hermes")   # hermes = สมองหลัก (เจ้าของระบบให้บอททั้ง 2 ปรึกษาได้)
ROLE_NAMES = {"mode2": "บอทโหมด 2", "admin": "แอดมินบอท", "hermes": "สมองหลัก (Hermes)"}
STANCES = ("agree", "disagree", "unsure", "need_more_data")
TOPICS_MAX = 60
MAX_OPEN = 3                 # คำถามค้างสูงสุดต่อบอท (กันคุยวน/เปลือง)
TTL_HOURS = 6                # คำถามเก่ากว่านี้ = หมดอายุ (ไม่ค้างนิ่ง)
FORBIDDEN = ("kill switch", "kill_switch", "live_enabled", "volume", "magic",
             "โครงสร้างโค้ด", "ตัวเทรด", "AUTO_TRADER_STOP")


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _load(path):
    out = []
    try:
        for line in io.open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _append(path, rec):
    os.makedirs(DIR, exist_ok=True)
    with io.open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _age_hours(ts):
    try:
        t = datetime.datetime.fromisoformat(str(ts))
        if t.tzinfo is None:
            t = t.replace(tzinfo=datetime.timezone.utc)
        return (_now() - t).total_seconds() / 3600.0
    except Exception:
        return 999.0


def clean_text(t, cap=1200, role=None):
    """ตรวจคำต้องห้าม — ยกเว้นสมองหลัก (hermes) ซึ่งมีอำนาจเท่าเจ้าของระบบ (23 ก.ย. 2026)"""
    t = str(t or "").strip()
    if role == "hermes":
        return t[:cap]
    for bad in FORBIDDEN:
        if bad.lower() in t.lower():
            raise ValueError("ห้ามปรึกษาเรื่อง '%s' (คีย์สงวน/ตัวเทรด/kill switch/โครงสร้างโค้ด)" % bad)
    return t[:cap]


def open_asks(from_role=None):
    """คำถามที่ยังไม่ถูกตอบและยังไม่หมดอายุ"""
    answered = {a.get("ask_id") for a in _load(ANSWERS)}
    out = []
    for a in _load(ASKS):
        if a.get("id") in answered:
            continue
        if _age_hours(a.get("ts")) > TTL_HOURS:
            continue
        if from_role and a.get("from") != from_role:
            continue
        out.append(a)
    return out


def unread_answers(role):
    """คำตอบของคำถามที่ 'ฉัน' ถาม และยังไม่ได้อ่าน"""
    mine = {a.get("id"): a for a in _load(ASKS) if a.get("from") == role}
    out = []
    for ans in _load(ANSWERS):
        a = mine.get(ans.get("ask_id"))
        if not a:
            continue
        if ans.get("ack_" + role):
            continue
        out.append({"ask": a, "answer": ans})
    return out


def ask(from_role, to_role, topic, question, payload=None, priority="normal"):
    if from_role not in ROLES or to_role not in ROLES or from_role == to_role:
        raise ValueError("บทบาทต้องเป็น mode2/admin/hermes และต้องไม่ใช่ตัวเอง")
    if priority not in ("normal", "high"):
        priority = "normal"
    pend = [a for a in open_asks(from_role=from_role)]
    if len(pend) >= MAX_OPEN:
        raise ValueError("มีคำถามค้างอยู่ %d ข้อ (เพดาน %d) — รอคำตอบก่อนหรือใช้คำตอบที่มี"
                         % (len(pend), MAX_OPEN))
    # กันถามซ้ำเรื่องเดิม
    for a in pend:
        if str(a.get("topic")) == str(topic):
            raise ValueError("มีคำถามเรื่อง '%s' ค้างอยู่แล้ว (id=%s)" % (topic, a.get("id")))
    rec = {"id": uuid.uuid4().hex[:12], "ts": _now().isoformat(timespec="seconds"),
           "from": from_role, "to": to_role, "topic": clean_text(topic, TOPICS_MAX, role=from_role),
           "question": clean_text(question, role=from_role), "payload": payload or {},
           "priority": priority, "status": "open"}
    _append(ASKS, rec)
    return rec


def answer(from_role, ask_id, stance, text, evidence=None):
    if from_role not in ROLES:
        raise ValueError("บทบาทต้องเป็น mode2/admin")
    target = None
    for a in _load(ASKS):
        if a.get("id") == ask_id:
            target = a
            break
    if not target:
        raise ValueError("ไม่พบคำถาม id=%s" % ask_id)
    if target.get("to") != from_role:
        raise ValueError("คำถามนี้ส่งถึง '%s' ไม่ใช่ '%s'" % (target.get("to"), from_role))
    for a in _load(ANSWERS):
        if a.get("ask_id") == ask_id:
            raise ValueError("คำถามนี้ถูกตอบไปแล้ว")
    if stance not in STANCES:
        raise ValueError("stance ต้องเป็นหนึ่งใน: %s" % ", ".join(STANCES))
    payload = {
        "ask_id": ask_id, "ts": _now().isoformat(timespec="seconds"), "from": from_role,
        "stance": stance, "answer": clean_text(text, 1500, role=from_role), "evidence": evidence or {},
        "reply_hours": round(_age_hours(target.get("ts")), 2),
    }
    _append(ANSWERS, payload)
    return payload


def digest(role, max_items=3):
    """ข้อความให้บอทอ่านในรอบของตัวเอง (คำถามที่รอตอบ + คำตอบของคำถามที่ตัวเองถาม)"""
    lines = []
    pend = [a for a in open_asks() if a.get("to") == role]
    pend.sort(key=lambda a: (a.get("priority") != "high", a.get("ts") or ""))
    if pend:
        lines.append("คำถามจากบอทอีกตัวที่รอคำตอบ (%d ข้อ · ตอบด้วย: interbot.py answer --from %s --ask-id <id> --stance agree|disagree|unsure|need_more_data --answer \"...\")" % (len(pend), role))
        for a in pend[:max_items]:
            lines.append("  • id=%s [%s→%s · %s] %s | ข้อมูล: %s"
                         % (a.get("id"), a.get("from"), a.get("to"), a.get("priority"),
                            a.get("question"), json.dumps(a.get("payload") or {}, ensure_ascii=False)[:200]))
    un = unread_answers(role)
    if un:
        lines.append("คำตอบของคำถามที่คุณเคยถาม (%d ข้อ — นำไปใช้ประกอบดุลยพินิจ แล้วใช้ตัวเลขจริงยืนยัน)" % len(un))
        for u in un[:max_items]:
            ans = u["answer"]
            lines.append("  • [%s] %s → stance=%s · \"%s\" (ตอบใน %.2f ชม.)"
                         % (u["ask"].get("topic"), u["ask"].get("question")[:120],
                            ans.get("stance"), str(ans.get("answer"))[:200], ans.get("reply_hours") or 0))
    if not lines:
        return "การปรึกษาระหว่างบอท: ไม่มีคำถามค้าง/คำตอบใหม่"
    lines.append("กติกา: คำตอบ = ข้อมูลประกอบเท่านั้น · ให้ใช้ตัวเลขจริง + Jev + กรอบปลอดภัยตัดสินเอง · ห้ามแตะคีย์สงวน/ตัวเทรด/kill switch")
    return "\n".join(lines)


def ack(role, ask_id):
    """ทำเครื่องหมายว่าอ่านคำตอบแล้ว (เก็บในไฟล์ answers เป็นบรรทัดใหม่)"""
    rec = {"ask_id": ask_id, "ts": _now().isoformat(timespec="seconds"), "ack": role}
    os.makedirs(DIR, exist_ok=True)
    with io.open(ANSWERS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def _label(role):
    """ชื่ออ่านง่ายของบทบาท"""
    return ROLE_NAMES.get(role, role)


def stats():
    asks = _load(ASKS)
    answers = [a for a in _load(ANSWERS) if a.get("stance")]
    return {"asks_total": len(asks), "answers_total": len(answers),
            "open_now": len(open_asks()), "ttl_hours": TTL_HOURS, "max_open_per_bot": MAX_OPEN}


def main():
    ap = argparse.ArgumentParser(description="ช่องปรึกษาระหว่างบอท 2 ตัว (มีโครงสร้าง · async)")
    sub = ap.add_subparsers(dest="cmd")

    a1 = sub.add_parser("ask", help="ฝากคำถามถึงบอทอีกตัว")
    a1.add_argument("--from", dest="frm", required=True, choices=ROLES)
    a1.add_argument("--to", required=True, choices=ROLES)
    a1.add_argument("--topic", required=True)
    a1.add_argument("--question", required=True)
    a1.add_argument("--payload", default=None, help="JSON ของข้อมูลประกอบ")
    a1.add_argument("--priority", default="normal", choices=("normal", "high"))

    a2 = sub.add_parser("answer", help="ตอบคำถามของบอทอีกตัว")
    a2.add_argument("--from", dest="frm", required=True, choices=ROLES)
    a2.add_argument("--ask-id", required=True)
    a2.add_argument("--stance", required=True, choices=STANCES)
    a2.add_argument("--answer", required=True)
    a2.add_argument("--evidence", default=None, help="JSON ของหลักฐาน (ตัวเลขจริง)")

    a3 = sub.add_parser("inbox", help="ดูคำถามที่รอตอบ + คำตอบของฉัน")
    a3.add_argument("--role", required=True, choices=ROLES)

    sub.add_parser("stats", help="สถิติการปรึกษา")

    args = ap.parse_args()
    try:
        if args.cmd == "ask":
            rec = ask(args.frm, args.to, args.topic, args.question,
                      json.loads(args.payload) if args.payload else None, args.priority)
            print(json.dumps(rec, ensure_ascii=False, indent=2))
        elif args.cmd == "answer":
            rec = answer(args.frm, args.ask_id, args.stance, args.answer,
                         json.loads(args.evidence) if args.evidence else None)
            print(json.dumps(rec, ensure_ascii=False, indent=2))
        elif args.cmd == "inbox":
            print(digest(args.role))
        elif args.cmd == "stats":
            print(json.dumps(stats(), ensure_ascii=False, indent=2))
        else:
            ap.print_help()
    except Exception as exc:
        print("ผิดพลาด: %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())