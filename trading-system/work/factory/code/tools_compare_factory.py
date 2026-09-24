#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""เทียบ "ระบบปัจจุบัน" กับ "ค่าโรงงาน" — บอกทุกความต่าง (อ่านอย่างเดียว ไม่แก้อะไร)

ใช้: python tools/compare_factory.py
"""
import glob
import hashlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BR))
FAC = os.path.join(ROOT, "work", "factory")
JOBS = os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json")


def flat(d, pre=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(flat(v, pre + k + "."))
        else:
            out[pre + k] = v
    return out


def code_pairs():
    """คืน (ที่อยู่จริง, ชื่อแบนในโรงงาน) — ต้องตรงกับวิธีตั้งชื่อของ set_factory.py"""
    pairs = []
    for f in glob.glob(os.path.join(BR, "*.py")) + glob.glob(os.path.join(BR, "tools", "*.py")):
        if "__pycache__" in f:
            continue
        rel = os.path.relpath(f, BR)
        pairs.append((f, rel.replace(os.sep, "_").replace("/", "_")))
    for ext in ("*.py", "*.json", "*.md"):
        for f in glob.glob(os.path.join(ROOT, "agents", ext)):
            pairs.append((f, "agents_" + os.path.basename(f)))
    return pairs


def main():
    problems = []
    print("=" * 74)
    print("  เทียบระบบปัจจุบัน กับ ค่าโรงงาน")
    print("=" * 74)

    # 1) ค่าตั้ง
    cur = json.loads(io.open(os.path.join(BR, "auto_config.json"), encoding="utf-8").read())
    fcfg = json.loads(io.open(os.path.join(FAC, "config", "auto_config.factory.json"), encoding="utf-8").read())
    fc, ff = flat(cur), flat(fcfg)
    diff = sorted(k for k in set(fc) | set(ff) if fc.get(k) != ff.get(k))
    print("\n1) ค่าตั้ง (%d คีย์)" % len(fc))
    if diff:
        print("   ✗ ต่าง %d คีย์: %s" % (len(diff), ", ".join(diff[:6])))
        problems.append("ค่าตั้งต่าง %d" % len(diff))
    else:
        print("   ✓ เหมือนโรงงานทุกค่า")

    # 2) ไฟล์โค้ด
    print("\n2) ไฟล์โค้ด")
    fac_dir = os.path.join(FAC, "code")
    fac_files = set(os.listdir(fac_dir))
    missing, changed = [], []
    pairs = code_pairs()
    for src, name in pairs:
        if name not in fac_files:
            missing.append(name)
            continue
        a = hashlib.md5(open(src, "rb").read()).hexdigest()
        b = hashlib.md5(open(os.path.join(fac_dir, name), "rb").read()).hexdigest()
        if a != b:
            changed.append(name)
    extra = sorted(fac_files - {n for _, n in pairs})
    print("   ตรวจ %d ไฟล์ · ในโรงงาน %d" % (len(pairs), len(fac_files)))
    for label, lst in (("หายจากโรงงาน", missing), ("เนื้อหาต่าง", changed), ("เกินในโรงงาน", extra)):
        print("   %s %s%d %s" % ("✓" if not lst else "✗", label + ": ", len(lst),
                                 "" if not lst else "→ " + ", ".join(lst[:5])))
    if missing or changed:
        problems.append("ไฟล์โค้ดไม่ตรง %d" % (len(missing) + len(changed)))

    # 3) งาน cron
    print("\n3) งาน cron")
    try:
        snap = json.loads(io.open(os.path.join(FAC, "cron", "jobs.snapshot.json"), encoding="utf-8").read())
        live = json.loads(io.open(JOBS, encoding="utf-8").read())["jobs"]
        live_by = {j.get("name"): j for j in live}
        s_diff, e_diff = [], []
        for s in snap:
            j = live_by.get(s.get("name"))
            if not j:
                s_diff.append("หาย: %s" % s.get("name"))
                continue
            if j.get("script") != s.get("script") or bool(j.get("no_agent")) != bool(s.get("no_agent")):
                s_diff.append("ชนิดงานต่าง: %s" % str(s.get("name"))[:34])
            if bool(j.get("enabled")) != bool(s.get("enabled")):
                e_diff.append("%s (จริง=%s โรงงาน=%s)" % (str(s.get("name"))[:30], j.get("enabled"), s.get("enabled")))
        print("   โครงสร้าง/ชนิดงาน: %s" % ("✓ เหมือนโรงงาน" if not s_diff else "✗ " + "; ".join(s_diff[:4])))
        print("   สถานะเปิด-ปิด: %s" % ("✓ เหมือนโรงงาน" if not e_diff else "ต่าง %d งาน (คำสั่งหยุดของเจ้าของระบบ = ตั้งใจ)" % len(e_diff)))
        for e in e_diff:
            print("     -", e)
        if s_diff:
            problems.append("โครงสร้าง cron ไม่ตรง")
    except Exception as exc:
        print("   ✗ เทียบไม่ได้:", exc)
        problems.append("เทียบ cron ไม่ได้")

    # 4) โหมด
    mode = json.loads(io.open(os.path.join(ROOT, "work", "trading_mode.json"), encoding="utf-8").read())
    print("\n4) โหมดระบบ: %s (epoch %s)" % (mode.get("mode"), str(mode.get("epoch"))[:8]))

    # สรุป
    print("\n" + "=" * 74)
    if problems:
        print("  สรุป: มีความต่าง ✗ → %s" % " · ".join(problems))
    else:
        print("  สรุป: ระบบปัจจุบันตรงกับค่าโรงงานทุกด้าน ✓")
    print("=" * 74)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
