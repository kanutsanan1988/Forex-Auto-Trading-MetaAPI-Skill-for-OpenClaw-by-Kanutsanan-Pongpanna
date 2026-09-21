#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""รัน 'สมอง' (agentic AI ตัวไหนก็ได้) ให้ทำงานบอทของระบบเทรดทองคำ

แนวคิดของเจ้าของระบบ (19 ก.ย. 2026):
  "ตัว agent ทั้ง 2 ตัว คือบอทที่ทำงานหลัก — ถ้าใช้ Hermes ก็ Hermes เองเป็นบอทของทั้งสองชุด
   ในทำนองเดียวกันต้องใช้ได้กับ agentic AI ตัวอื่น ๆ ด้วย (OpenClaw · Manus · Codex · Cowork ·
   Claude Code · Cursor ฯลฯ) — เราต้องทำระบบให้เข้ากับทุกตัวได้"

หลักการ: **ระบบเทรดเป็น 'ตัวถัง' · agent เป็น 'สมอง'** — สัญญากลางคือ "ไฟล์ + คำสั่ง shell"
          ตัวไหนทำสองอย่างนี้ได้ ก็เป็นบอทของระบบได้ทันที

ใช้:
  python agents/run_bot.py --list                     # ดูสมองทั้งหมด + ตัวไหนติดตั้งแล้ว
  python agents/run_bot.py --role mode2               # ให้สมองเริ่มต้นทำงานรอบวิจัยโหมด 2
  python agents/run_bot.py --role admin --brain codex # เลือกสมองเอง
  python agents/run_bot.py --role admin --dry-run     # ดูคำสั่งที่จะรัน (ไม่รันจริง)
"""
import argparse
import datetime
import io
import json
import os
import shlex
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'outputs', 'mt5_python_bridge'))
from runtime_support import require_ai_mode
REG = os.path.join(HERE, "registry.json")
LOG = os.path.join(ROOT, "work", "agent_runs.jsonl")
BRIEFS = {"mode2": os.path.join(HERE, "brief_mode2.md"),
          "admin": os.path.join(HERE, "brief_admin.md")}


def load_registry():
    return json.loads(io.open(REG, encoding="utf-8").read())


def find_exe(cands):
    for c in cands:
        p = shutil.which(c)
        if p:
            return p
    return None


def available(reg):
    out = []
    for a in reg["agents"]:
        exe = find_exe(a.get("detect") or []) if a.get("detect") else None
        out.append((a, exe))
    return out


def log(event, **kw):
    rec = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "source": "run_bot", "event": event, **kw}
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def cmd_list(reg):
    print("=== สมอง (agentic AI) ที่ระบบรองรับ ===")
    print("%-14s %-32s %-12s %s" % ("id", "ชื่อ", "ติดตั้ง", "สถานะ"))
    print("-" * 78)
    for a, exe in available(reg):
        mark = "✓ มี" if exe else "— ไม่มี"
        print("%-14s %-32s %-12s %s" % (a["id"], a["name"][:32], mark, a.get("status", "")))
    print("")
    print("เพิ่มสมองใหม่: แก้ agents/registry.json (ไม่ต้องแตะโค้ดระบบเทรด)")
    print("คำสั่งงาน (brief): agents/brief_mode2.md · agents/brief_admin.md")
    return 0


def build_brief_text(role):
    """สร้างข้อความคำสั่งงาน = ไฟล์ brief + ที่อยู่ไฟล์ที่ต้องอ่าน"""
    path = BRIEFS[role]
    if not os.path.exists(path):
        return None
    body = io.open(path, encoding="utf-8").read()
    header = ("# คำสั่งงานบอท (%s)\n\n"
              "คุณคือ 'สมอง' ของระบบเทรดทองคำ — ระบบเทรดเป็นตัวถังที่แม่นยำอยู่แล้ว "
              "หน้าที่คุณคือคิด วิเคราะห์ และสั่งงานผ่านสคริปต์ Python ตามสัญญาที่ระบุ\n\n"
              "โฟลเดอร์ระบบ: %s\n\n---\n\n" % (role, ROOT))
    return header + body


def run(role, brain_id, dry):
    if not dry:
        try:
            require_ai_mode(ROOT)
        except (ValueError, OSError) as exc:
            print('ไม่เรียก AI Agent Bot: %s' % exc)
            return 9
    reg = load_registry()
    if not brain_id:
        # เลือกตัวแรกที่ติดตั้ง + สถานะ default ก่อน
        for a, exe in available(reg):
            if exe and a.get("status") == "default":
                brain_id, brain, exe_path = a["id"], a, exe
                break
        else:
            for a, exe in available(reg):
                if exe and a.get("run"):
                    brain_id, brain, exe_path = a["id"], a, exe
                    break
            else:
                print("ไม่พบสมองที่ติดตั้งในเครื่อง — ดูรายการด้วย --list")
                return 2
    else:
        brain = next((a for a in reg["agents"] if a["id"] == brain_id), None)
        if not brain:
            print("ไม่รู้จักสมอง '%s' — ดูรายการด้วย --list" % brain_id)
            return 3
        exe_path = find_exe(brain.get("detect") or []) if brain.get("detect") else None
        if not exe_path:
            if brain.get("status") == "desktop":
                # สมองแบบ desktop (เช่น Claude Cowork) — ไม่มี CLI ให้เรียก ต้องใช้วิธีชี้โฟลเดอร์
                print("สมอง '%s' เป็นแบบ desktop (ไม่มี CLI ให้เรียกอัตโนมัติ)" % brain_id)
                print("  วิธีใช้: เปิดโฟลเดอร์ระบบ %s ในตัว agent แล้วสั่งงานด้วยไฟล์:" % ROOT)
                print("     -", BRIEFS[role])
                print("     - research/recommendations/CONTRACT.md (สัญญาการสื่อสารกับสคริปต์)")
                print("  หมายเหตุ:", brain.get("notes", "-"))
                return 0
            print("สมอง '%s' ยังไม่ติดตั้งในเครื่องนี้" % brain_id)
            print("  วิธีติดตั้ง:", brain.get("install", "-"))
            return 4

    text = build_brief_text(role)
    if not text:
        print("ไม่พบไฟล์คำสั่งงาน:", BRIEFS[role])
        return 5

    tpl = brain.get("run") or []
    if not tpl:
        print("สมอง '%s' ไม่มีคำสั่งรันอัตโนมัติ (อาจเป็นแบบ desktop) — ดูหมายเหตุ:" % brain_id)
        print("  " + str(brain.get("notes", "")))
        print("  ใช้วิธี: เปิดโฟลเดอร์ %s แล้วสั่งงานด้วยไฟล์ %s" % (ROOT, BRIEFS[role]))
        return 6

    cmd = [exe_path if i == 0 else part
           for i, part in enumerate([p.replace("{{brief_text}}", text)
                                     .replace("{{brief}}", BRIEFS[role]) for p in tpl])]

    print("สมอง:", brain["name"], "(%s)" % brain_id)
    print("รอบ:", role, "| คำสั่งงาน:", len(text), "ตัวอักษร")
    if dry:
        print("\n[dry-run] คำสั่งที่จะรัน (ตัดข้อความยาว):")
        print("  " + shlex.join(cmd)[:300] + " ...")
        return 0

    log("agent_run_start", role=role, brain=brain_id, cmd_len=len(text))
    print("กำลังรัน... (สมองอาจใช้เวลาหลายนาที)")
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=3600)
        out = ((r.stdout or "") + (r.stderr or "")).strip()
        print(out[-3000:] if out else "(ไม่มีผลลัพธ์)")
        log("agent_run_end", role=role, brain=brain_id, rc=r.returncode)
        return r.returncode
    except subprocess.TimeoutExpired:
        log("agent_run_timeout", role=role, brain=brain_id)
        print("หมดเวลา (1 ชม.) — สมองทำงานไม่จบ")
        return 7
    except Exception as exc:
        log("agent_run_error", role=role, brain=brain_id, error=str(exc))
        print("รันไม่สำเร็จ:", exc)
        return 8


def main():
    ap = argparse.ArgumentParser(description="รันสมอง (agentic AI) ให้ทำงานบอทของระบบเทรด")
    ap.add_argument("--list", action="store_true", help="ดูสมองทั้งหมด + ตัวที่ติดตั้งแล้ว")
    ap.add_argument("--role", choices=["mode2", "admin"], help="รอบงาน: mode2 = วิจัยโหมด 2 · admin = แอดมินบอท")
    ap.add_argument("--brain", help="id ของสมอง (ดูจาก --list) — ไม่ใส่ = ใช้ตัวเริ่มต้นที่ติดตั้ง")
    ap.add_argument("--dry-run", action="store_true", help="ดูคำสั่งที่จะรัน ไม่รันจริง")
    a = ap.parse_args()
    reg = load_registry()
    if a.list or not a.role:
        return cmd_list(reg)
    return run(a.role, a.brain, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
