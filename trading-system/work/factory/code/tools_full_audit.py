#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ตรวจสุขภาพระบบเทรดทองคำทั้งระบบ (รอบครอบทุกมุมมอง) — รันซ้ำได้ทุกครั้ง

ใช้:
  python tools/full_audit.py            # ตรวจทั้งหมด + สรุปผล
  python tools/full_audit.py --verbose  # แสดงรายละเอียดทุกข้อ

ออกแบบตามคำสั่งเจ้าของระบบ: "ตรวจสอบโค้ดทั้งหมด ความสะอาด และการทำงานทุกมุมมอง"
ครอบคลุม: ความสะอาดโค้ด · โครงสร้าง · ความปลอดภัย · ข้อมูล · โรงงาน · ชั้นสมอง (agent) ·
          สัญญาการสื่อสาร · เทสต์ · สถานะระบบ
"""
import ast
import glob
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BR))
PY = sys.executable
VERBOSE = "--verbose" in sys.argv

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    mark = "✓" if ok else "✗"
    print("  [%s] %-46s %s" % (mark, name, detail if (VERBOSE or not ok) else ""))
    return ok


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd or ROOT, timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def py_files():
    out = []
    for pat in (os.path.join(BR, "*.py"), os.path.join(BR, "tools", "*.py"),
                os.path.join(ROOT, "agents", "*.py")):
        out += [f for f in glob.glob(pat) if "__pycache__" not in f]
    return out


def main():
    print("=" * 78)
    print("  ตรวจสุขภาพระบบเทรดทองคำ — รอบครอบทุกมุมมอง")
    print("  โฟลเดอร์:", ROOT)
    print("=" * 78)

    # ── 1) ความสะอาดโค้ด ──
    print("\n【1】 ความสะอาดของโค้ด")
    rc, out = run([PY, "-m", "compileall", "-q", BR, os.path.join(ROOT, "agents")])
    check("compile ทุกไฟล์", rc == 0, "" if rc == 0 else out[-200:])
    files = py_files()
    rc, out = run([PY, "-m", "pyflakes"] + files)
    n_pf = len([l for l in out.splitlines() if l.strip()])
    check("pyflakes (ต้อง 0)", n_pf == 0, "พบ %d จุด" % n_pf if n_pf else "%d ไฟล์" % len(files))
    # bare except (ตรวจจาก AST — ตัดคอมเมนต์/docstring ออก)
    bare = []
    for f in files:
        try:
            tree = ast.parse(io.open(f, encoding="utf-8").read())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                bare.append("%s:%d" % (os.path.basename(f), node.lineno))
    check("bare except (ต้อง 0)", len(bare) == 0, ", ".join(bare[:4]))

    # ── 2) โครงสร้าง ──
    print("\n【2】 โครงสร้างระบบ")
    need = {"outputs/mt5_python_bridge": "ชั้นเครื่องยนต์เทรด",
            "work/factory": "ชั้นคืนค่าโรงงาน",
            "agents": "ชั้นสมอง (agent)",
            "research": "ชั้นงานวิจัย",
            "work": "ชั้นข้อมูลรันจริง"}
    for p, label in need.items():
        check("มี %s (%s)" % (p, label), os.path.isdir(os.path.join(ROOT, p)))
    check("มี README.md", os.path.isfile(os.path.join(ROOT, "README.md")))
    check("มี AGENTS.md (คู่มือสมอง)", os.path.isfile(os.path.join(ROOT, "AGENTS.md")))

    # ── 3) ความปลอดภัย ──
    print("\n【3】 ความปลอดภัย (เงินจริง)")
    sec_pat = ("OPENROUTER_API_KEY", "sk-or-v1-", "password=", "api_key =")
    hits = []
    for f in files:
        # ★ ข้ามเครื่องมือตรวจตัวเอง — ในไฟล์นี้มีคำค้นเป็นสตริง (จะจับตัวเองเป็น false positive)
        if os.path.basename(f) == "full_audit.py":
            continue
        try:
            txt = io.open(f, encoding="utf-8").read()
        except Exception:
            continue
        for pat in sec_pat:
            if pat in txt and "os.environ" not in txt.split(pat)[0][-60:]:
                hits.append("%s:%s" % (os.path.basename(f), pat))
    check("ไม่มี credential ฝังในโค้ด", len(hits) == 0, ", ".join(hits[:3]))
    kill = os.path.join(ROOT, "work", "AUTO_TRADER_STOP")
    check("kill switch ทำงาน", os.path.exists(kill), "สถานะ: %s" % ("ปิดระบบอยู่" if os.path.exists(kill) else "เปิดระบบอยู่"))
    # consumer ต้องไม่ล้าง kill switch
    cs = io.open(os.path.join(BR, "llm_recommendation_consumer.py"), encoding="utf-8").read()
    check("consumer ไม่ล้าง kill switch", "clear_kill_switch" not in cs or "False" in cs.split("clear_kill_switch")[0][-200:])
    cfg = json.loads(io.open(os.path.join(BR, "auto_config.json"), encoding="utf-8").read())
    risk = cfg.get("max_risk_pct")
    check("max_risk_pct อยู่ในกรอบ ≤ 8.0", isinstance(risk, (int, float)) and risk <= 8.0, "ค่าจริง: %s" % risk)

    # ── 4) ไฟล์ปุ่มและสคริปต์ Windows ──
    print("\n【4】 ไฟล์ปุ่ม (.cmd) และสคริปต์ (.ps1)")
    cmds = glob.glob(os.path.join(BR, "*.cmd"))
    bad = []
    for f in cmds:
        txt = io.open(f, encoding="utf-8", errors="replace").read()
        if any(ord(c) < 9 or (13 < ord(c) < 32) for c in txt):
            bad.append(os.path.basename(f))
    check("ปุ่ม %d ตัว ไม่มีอักขระควบคุม" % len(cmds), len(bad) == 0, ", ".join(bad[:3]))
    ps1 = glob.glob(os.path.join(BR, "*.ps1"))
    nobom = []
    for f in ps1:
        with open(f, "rb") as fh:
            if fh.read(3) != b"\xef\xbb\xbf":
                nobom.append(os.path.basename(f))
    check(".ps1 ทั้ง %d ไฟล์มี BOM (กันไทยเพี้ยน)" % len(ps1), len(nobom) == 0, ", ".join(nobom[:3]))

    # ── 5) โรงงาน ──
    print("\n【5】 โรงงาน (ค่าเริ่มแรก + คืนค่าได้)")
    fac_code = os.path.join(ROOT, "work", "factory", "code")
    fac_cfg = os.path.join(ROOT, "work", "factory", "config", "auto_config.factory.json")
    n_fac = len(os.listdir(fac_code)) if os.path.isdir(fac_code) else 0
    check("โรงงานมีโค้ด %d ไฟล์" % n_fac, n_fac > 40)
    check("โรงงานมี config", os.path.isfile(fac_cfg))
    check("โรงงานมี agents/ (ชั้นสมอง)", any(f.startswith("agents_") for f in os.listdir(fac_code)))
    if os.path.isfile(fac_cfg):
        fcfg = json.loads(io.open(fac_cfg, encoding="utf-8").read())
        diff = [k for k in fcfg if isinstance(fcfg[k], (int, float)) and
                isinstance(cfg.get(k), (int, float)) and abs(float(fcfg[k]) - float(cfg[k])) > 1e-9]
        check("ค่า config ปัจจุบัน = โรงงาน", len(diff) == 0, "ต่าง: " + ", ".join(diff[:4]))

    # ── 6) ชั้นสมอง (agent) ──
    print("\n【6】 ชั้นสมอง (agentic AI — เปลี่ยนสมองได้)")
    reg_p = os.path.join(ROOT, "agents", "registry.json")
    ok_reg = False
    if os.path.isfile(reg_p):
        try:
            reg = json.loads(io.open(reg_p, encoding="utf-8").read())
            ok_reg = len(reg.get("agents", [])) >= 10
        except Exception:
            pass
    check("ทะเบียนสมองอ่านได้ (≥10 ตัว)", ok_reg)
    check("มี brief_mode2.md", os.path.isfile(os.path.join(ROOT, "agents", "brief_mode2.md")))
    check("มี brief_admin.md", os.path.isfile(os.path.join(ROOT, "agents", "brief_admin.md")))
    rc, out = run([PY, os.path.join(ROOT, "agents", "run_bot.py"), "--list"])
    check("run_bot.py --list ทำงาน", rc == 0 and "Hermes" in out)
    # brief ต้องตรงกับงาน cron (แหล่งเดียว)
    try:
        jobs = json.loads(io.open(os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json"),
                                  encoding="utf-8").read())["jobs"]
        for prefix, bf in (("trading-research-bot", "brief_mode2.md"), ("trading-admin-bot", "brief_admin.md")):
            j = next((x for x in jobs if str(x.get("name", "")).startswith(prefix)), None)
            brief = io.open(os.path.join(ROOT, "agents", bf), encoding="utf-8").read()
            same = bool(j) and (j.get("prompt") or "").strip()[:200] in brief
            check("brief %s ตรงกับงาน cron" % bf, same)
    except Exception as exc:
        check("เทียบ brief กับ cron", False, str(exc)[:80])

    # ── 7) สัญญาการสื่อสาร ──
    print("\n【7】 สัญญาการสื่อสาร agent ↔ สคริปต์ Python")
    cp = os.path.join(ROOT, "research", "recommendations", "CONTRACT.md")
    check("มี CONTRACT.md", os.path.isfile(cp))
    rc, out = run([PY, os.path.join(HERE, "rec_contract.py"), "--print"])
    cur_epoch = ""
    try:
        m = json.loads(io.open(os.path.join(ROOT, "work", "trading_mode.json"), encoding="utf-8").read())
        cur_epoch = m.get("epoch", "")
    except Exception:
        pass
    check("สัญญาแสดง epoch ปัจจุบันถูก", cur_epoch and cur_epoch in out)
    for tool in ("submit_recommendation.py", "admin_command.py"):
        check("มีเครื่องมือ %s" % tool, os.path.isfile(os.path.join(HERE, tool)))
    rc, out = run([PY, os.path.join(HERE, "admin_command.py"), "--list"])
    check("admin_command.py --list ทำงาน", rc == 0 and "set_value" in out)
    # ทดสอบว่าปฏิเสธจริง
    rc, _ = run([PY, os.path.join(HERE, "admin_command.py"), "--run", "set_value",
                 "--key", "live_enabled", "--value", "1", "--why", "audit"])
    check("admin_command ปฏิเสธคีย์สงวน", rc != 0)

    # ── 8) เทสต์ ──
    print("\n【8】 เทสต์")
    for t in ("test_freq_floor_enforce.py", "test_freq_floor.py"):
        p = os.path.join(BR, t)
        if os.path.isfile(p):
            rc, out = run([PY, p])
            tail = [l for l in out.splitlines() if "ผ่าน" in l or "FAIL" in l or "failed" in l.lower()]
            check(t, rc == 0, tail[-1][:60] if tail else "")

    # ── 9) สถานะระบบ ──
    print("\n【9】 สถานะระบบ")
    try:
        jobs = json.loads(io.open(os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json"),
                                  encoding="utf-8").read())["jobs"]
        check("งาน cron ครบ 7 งาน", len(jobs) == 7)
        agents_jobs = [j for j in jobs if not j.get("no_agent")]
        check("งานแบบ agent 3 งาน (โหมด 2 + แอดมินบอท + ที่ปรึกษาสมองหลัก)", len(agents_jobs) == 3)
    except Exception as exc:
        check("อ่านงาน cron", False, str(exc)[:60])
    rc, out = run([PY, os.path.join(BR, "tools", "system_status.py")], cwd=ROOT)
    check("system_status.py ทำงาน", rc == 0)
    # audit ต้องไม่มีข้อมูลทดสอบปน
    ap = os.path.join(ROOT, "work", "auto_trader_audit.jsonl")
    if os.path.isfile(ap):
        with io.open(ap, encoding="utf-8", errors="replace") as fh:
            fh.seek(max(0, os.path.getsize(ap) - 20000))
            tail = fh.read()
        check("audit ไม่มีข้อมูลทดสอบปน", "ทดสอบ" not in tail and "TEST" not in tail)

    # ── สรุป ──
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print("\n" + "=" * 78)
    print("  สรุป: ผ่าน %d/%d" % (passed, total))
    if passed < total:
        print("  ไม่ผ่าน:")
        for n, ok, d in RESULTS:
            if not ok:
                print("    ✗", n, "—", d)
    print("=" * 78)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
