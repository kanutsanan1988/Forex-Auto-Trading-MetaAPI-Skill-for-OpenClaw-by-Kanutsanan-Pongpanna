#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ซิงก์ 'คำสั่งงานบอท' (brief) จากงาน cron — แหล่งความจริงเดียว

เหตุผล: งานวิจัยโหมด 2 และแอดมินบอทมีคำสั่งงานอยู่ในงาน cron ของ Hermes
        แต่ agentic AI ตัวอื่น (OpenClaw · Manus · Codex · Claude Code · Cursor ฯลฯ)
        ไม่ได้อ่าน cron ของ Hermes → ต้องมีไฟล์คำสั่งงานกลางที่ทุกตัวอ่านได้
        ไฟล์นี้ทำให้ **คำสั่งงานมีแหล่งเดียว** (แก้ที่ cron แล้วซิงก์ — ไม่มีเพี้ยนสองทาง)

ใช้: python agents/sync_briefs.py
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JOBS = os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json")
MAP = [("trading-research-bot", "brief_mode2.md", "งานวิจัยโหมด 2 (บอทเป็นสมอง LLM)"),
       ("trading-admin-bot", "brief_admin.md", "แอดมินบอท (agent — วิวัฒน์ค่าต่างๆ + วิจัยข่าว + สั่งคำสั่งได้)")]

HEADER = """# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
<!-- สร้างอัตโนมัติจากงาน cron ของ Hermes — ห้ามแก้ไฟล์นี้โดยตรง
     แก้ที่คำสั่งงาน (cron) แล้วรัน: python agents/sync_briefs.py
     ไฟล์นี้ใช้โดย agentic AI ตัวอื่น (OpenClaw · Manus · Codex · Claude Code · Cursor · Goose ฯลฯ)
-->

# คำสั่งงาน: {title}

> ระบบเทรดทองคำ — 'ตัวถัง' คือสคริปต์ Python ที่แม่นยำอยู่แล้ว · 'สมอง' คือคุณ
> สัญญากลาง: คุณต้องทำได้ 2 อย่าง — (1) รันคำสั่ง shell (2) อ่าน/เขียนไฟล์
> สัญญาการสื่อสารฉบับเต็ม: research/recommendations/CONTRACT.md

"""


def main():
    if not os.path.exists(JOBS):
        print("ไม่พบไฟล์งาน cron:", JOBS)
        return 2
    jobs = json.loads(io.open(JOBS, encoding="utf-8").read())["jobs"]
    done = 0
    for prefix, out_name, title in MAP:
        job = next((j for j in jobs if str(j.get("name", "")).startswith(prefix)), None)
        if not job:
            print("  [SKIP] ไม่พบงาน:", prefix)
            continue
        prompt = (job.get("prompt") or "").strip()
        if not prompt:
            print("  [SKIP] งาน %s ไม่มีคำสั่งงาน" % prefix)
            continue
        out = os.path.join(HERE, out_name)
        io.open(out, "w", encoding="utf-8").write(HEADER.format(title=title) + prompt + "\n")
        done += 1
        print("  [OK] %s → %s (%d ตัวอักษร)" % (prefix, out_name, len(prompt)))
    print("\nซิงก์แล้ว %d ไฟล์" % done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
