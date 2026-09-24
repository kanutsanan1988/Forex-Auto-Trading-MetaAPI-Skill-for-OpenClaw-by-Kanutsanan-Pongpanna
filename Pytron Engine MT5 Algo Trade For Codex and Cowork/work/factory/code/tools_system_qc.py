#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ชุดตรวจคุณภาพระบบ (QC) — 2 รอบ (เจ้าของระบบสั่ง 23 ก.ย. 2026: "QC ระบบ 2 รอบ")

รอบที่ 1 · โครงสร้าง + ความปลอดภัย  (ตรวจอย่างเดียว ไม่แตะระบบ)
  audit 38 ข้อ · เทียบโรงงาน · compile ทุกไฟล์ · pyflakes · kill switch · cron · สกิล · ไฟล์ปุ่ม
รอบที่ 2 · การทำงานจริง (functional)
  Jev probe + selftest ทุกพรีเซ็ต · ตัวเชื่อมต่อพกพา · บันไดอำนาจ · กระดานคะแนน ·
  กล่องปรึกษา · รอบแอดมิน (advisory) · แพ็กเกจวิจัยโหมด 2 · วิเคราะห์ข้อมูลภายใน

ความปลอดภัยของตัว QC เอง:
  • รันรอบแอดมินแบบ advisory เท่านั้น (ไม่ใช้ --apply) → ไม่แก้ค่าเทรด · ไม่ลบ kill switch
  • ไม่แตะคีย์สงวน · ไม่ส่งออเดอร์ · ไม่เปิด/ปิดระบบเทรด
  • บันทึกผลทุกรอบที่ work/qc_log.jsonl (เทียบรอบก่อนหน้าได้)

ใช้: .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\system_qc.py            # ทั้ง 2 รอบ
     ... --round 1 | --round 2                                                     # เฉพาะรอบเดียว
     ... --label "หลังแก้ไข X"                                                     # กำกับรอบ
"""
import argparse
import subprocess
import sys
import time
import os
import io
import json

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BR))
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable
WORK = os.path.join(ROOT, "work")
QLOG = os.path.join(WORK, "qc_log.jsonl")
T = os.path.join(HERE)


def run(args, timeout=300, env_extra=None):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    if env_extra:
        env.update(env_extra)
    try:
        p = subprocess.run([PY] + args, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, ((p.stdout or "") + (p.stderr or ""))
    except subprocess.TimeoutExpired as exc:
        return 124, ("TIMEOUT %ss: %s" % (timeout, (exc.stdout or b"")[:200]))
    except Exception as exc:
        return 1, "%s: %s" % (type(exc).__name__, exc)


ROUND1 = []
ROUND2 = []


def item(round_no, name, fn, note=""):
    (ROUND1 if round_no == 1 else ROUND2).append((name, fn, note))


# ── รอบที่ 1 ─────────────────────────────────────────────────────────────────
def q_audit():
    rc, out = run([os.path.join(T, "full_audit.py")], timeout=420)
    m = [l for l in out.splitlines() if "สรุป" in l]
    ok = rc == 0 and any("38/38" in l or "ผ่าน 38" in l for l in m)
    return ok, (m[-1].strip() if m else out.strip()[:80])


def q_factory():
    rc, out = run([os.path.join(T, "compare_factory.py")], timeout=300)
    ok = rc == 0 and "ตรงกับค่าโรงงานทุกด้าน" in out
    line = [l for l in out.splitlines() if l.strip().startswith("สรุป")]
    note = line[-1].replace("สรุป:", "").strip() if line else "?"
    if not ok:
        diff = [l.strip() for l in out.splitlines() if "เนื้อหาต่าง" in l or "หายจากโรงงาน" in l]
        note = " · ".join(diff[:2]) if diff else note
    return ok, note[:90]


def q_compile():
    bad = []
    n = 0
    for dp, _, fs in os.walk(BR):
        if "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith(".py"):
                n += 1
                rc, out = run(["-m", "py_compile", os.path.join(dp, f)], timeout=60)
                if rc != 0:
                    bad.append(f)
    return not bad, "%d ไฟล์%s" % (n, "" if not bad else " · พัง: " + ", ".join(bad[:3]))


def q_pyflakes():
    bad, n = [], 0
    for dp, _, fs in os.walk(BR):
        if "__pycache__" in dp:
            continue
        for f in fs:
            if f.endswith(".py"):
                n += 1
                rc, out = run(["-m", "pyflakes", os.path.join(dp, f)], timeout=60)
                if rc != 0:
                    bad.append("%s(%d)" % (f, len([l for l in out.splitlines() if l.strip()])))
    return not bad, "%d ไฟล์%s" % (n, "" if not bad else " · " + ", ".join(bad[:4]))


def q_safety():
    kill = os.path.exists(os.path.join(WORK, "AUTO_TRADER_STOP"))
    live = os.path.exists(os.path.join(WORK, "live_enabled"))
    cfg = json.load(io.open(os.path.join(BR, "auto_config.json"), encoding="utf-8"))
    risk = cfg.get("max_risk_pct")
    ok = kill and (not str(cfg.get("live_trading", "")).lower() in ("true", "1", "yes"))
    return ok, "kill switch=%s · live flag=%s · live_trading=%s · max_risk_pct=%s" % (
        kill, live, cfg.get("live_trading", "-"), risk)


def q_cron():
    p = os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json")
    try:
        d = json.load(io.open(p, encoding="utf-8"))
        jobs = d if isinstance(d, list) else (d.get("jobs") or [])
        names = [j.get("name") for j in jobs]
        paused = [j.get("name") for j in jobs if j.get("paused")]
        trade = [n for n in names if n and ("trad" in n or "llm-rec" in n)]
        return len(jobs) >= 6, "%d งาน · ระบบเทรด %d · พักอยู่: %s" % (
            len(jobs), len(trade), ", ".join(paused) or "ไม่มี")
    except Exception as exc:
        return False, str(exc)[:80]


def q_buttons():
    need = ["start_FULL_system.cmd", "stop_FULL_system.cmd", "start_auto_trader.ps1"]
    miss = [f for f in need if not os.path.exists(os.path.join(BR, f))]
    return not miss, ("ครบ %d ไฟล์" % len(need)) if not miss else "ขาด: " + ", ".join(miss)


# ── รอบที่ 2 ─────────────────────────────────────────────────────────────────
def q_jev_probe():
    rc, out = run([os.path.join(T, "jev.py"), "--probe"], timeout=180)
    ok = '"ok": true' in out
    ms = [l for l in out.splitlines() if "latency_ms" in l]
    return ok, ("ตอบใน %s" % (ms[0].split(":")[1].strip() if ms else "?")) if ok else out.strip()[-90:]


def q_jev_selftest():
    rc, out = run([os.path.join(T, "jev.py"), "--selftest"], timeout=420)
    line = [l for l in out.splitlines() if "ผลรวม" in l]
    ok = bool(line) and "8/8" in line[0]
    return ok, (line[0].strip() if line else out.strip()[-90:])


def q_connect():
    rc, out = run([os.path.join(T, "jev_connect.py"), "--setup", "--dry"], timeout=300)
    ok = ("✅" in out) or ("⚠️" in out)          # ไม่ว่าจะต่อได้หรือไม่ได้ ต้องอยู่ในเส้นทางที่ถูกต้อง
    return ok, ("เชื่อมต่อได้ (ทดสอบยิงจริง)" if "✅" in out else "ต่อไม่ได้ → ปิด Jev และเดินต่อ (ถูกต้อง)")


def q_power():
    rc, out = run([os.path.join(T, "jev_power.py"), "--status"], timeout=300)
    line = [l for l in out.splitlines() if "บันไดอำนาจ" in l]
    ev = [l for l in out.splitlines() if "สถานะหลักฐาน" in l]
    ok = bool(line) and bool(ev)
    return ok, ("%s · %s" % (line[0].split("—")[-1].strip() if line else "?", ev[0].split(":")[-1].strip() if ev else "?")) if ok else out.strip()[-90:]


def q_scoreboard():
    rc, out = run([os.path.join(T, "strategy_scoreboard.py"), "--compact"], timeout=300)
    ok = rc == 0 and out.strip()
    return ok, (out.strip().splitlines()[0][:70] if ok else out.strip()[-90:])


def q_interbot():
    rc, out = run([os.path.join(T, "interbot.py"), "stats"], timeout=180)
    ok = rc == 0 and out.strip()
    first = [l for l in out.splitlines() if l.strip()]
    return ok, (first[0].strip()[:70] if first else "-")


def q_admin_round():
    rc, out = run([os.path.join(T, "admin_bot_round.py")], timeout=420)      # advisory เท่านั้น
    ok = rc == 0 and "รอบแอดมิน" in out
    return ok, ("รอบแอดมินจบครบ (โหมด advisory)" if ok else out.strip()[-100:])


def q_packet():
    rc, out = run([os.path.join(T, "llm_research_packet.py")], timeout=300)
    ok = rc == 0 and "packet_" in out
    return ok, ("สร้างแพ็กเกจวิจัยสำเร็จ" if ok else out.strip()[-90:])


def q_analytics():
    # สคริปต์งานวิเคราะห์ข้อมูลภายในอยู่ฝั่ง Hermes (ตัวรัน cron) — มีสำรองในโฟลเดอร์ tools
    cand = [os.path.expanduser("~/AppData/Local/hermes/scripts/research_analytics.py"),
            os.path.join(T, "research_analytics.py")]
    path = next((p for p in cand if os.path.exists(p)), None)
    if not path:
        return False, "ไม่พบสคริปต์วิเคราะห์ (ตรวจ 2 ที่แล้ว)"
    rc, out = run([path], timeout=420)
    ok = rc == 0 and ("กระดานคะแนน" in out or "วิเคราะห" in out)
    return ok, ("วิเคราะห์ภายในจบครบ (มีกระดานคะแนน)" if ok else out.strip()[-90:])


item(1, "ตรวจครบ 38 ข้อ (full audit)", q_audit)
item(1, "ตรงกับค่าโรงงาน (factory)", q_factory)
item(1, "ทุกไฟล์ compile ผ่าน", q_compile)
item(1, "pyflakes สะอาดทุกไฟล์", q_pyflakes)
item(1, "ความปลอดภัยเงินจริง (kill switch)", q_safety)
item(1, "งาน cron ครบ/สถานะถูกต้อง", q_cron)
item(1, "ไฟล์ปุ่มเปิด-ปิดครบ", q_buttons)
item(2, "Jev ตอบได้ (probe)", q_jev_probe)
item(2, "Jev ทุกพรีเซ็ต (8 ตัว)", q_jev_selftest)
item(2, "เส้นทางเชื่อมต่อพกพา", q_connect)
item(2, "บันไดอำนาจ Jev", q_power)
item(2, "กระดานคะแนนกลยุทธ์", q_scoreboard)
item(2, "กล่องปรึกษาระหว่างบอท", q_interbot)
item(2, "รอบแอดมินบอท (advisory)", q_admin_round)
item(2, "แพ็กเกจวิจัยโหมด 2", q_packet)
item(2, "วิเคราะห์ข้อมูลภายใน", q_analytics)


def run_round(no, label=""):
    items = ROUND1 if no == 1 else ROUND2
    title = "รอบที่ 1 · โครงสร้าง + ความปลอดภัย" if no == 1 else "รอบที่ 2 · การทำงานจริง"
    print("\n" + "=" * 78)
    print("  🧪 QC %s%s" % (title, (" — %s" % label) if label else ""))
    print("=" * 78)
    res, t0 = [], time.time()
    for name, fn, _ in items:
        s = time.time()
        try:
            ok, note = fn()
        except Exception as exc:
            ok, note = False, "%s: %s" % (type(exc).__name__, str(exc)[:70])
        dt = time.time() - s
        res.append({"name": name, "ok": bool(ok), "note": note, "seconds": round(dt, 1)})
        print("  %s %-34s %5.1f วิ  %s" % ("✓" if ok else "✗", name, dt, note))
    passed = sum(1 for r in res if r["ok"])
    print("  ── รอบ %d: ผ่าน %d/%d (%.1f วิ)" % (no, passed, len(res), time.time() - t0))
    return {"round": no, "label": label, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "passed": passed, "total": len(res), "items": res}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, choices=(1, 2))
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    rounds = [a.round] if a.round else [1, 2]
    out = [run_round(r, a.label) for r in rounds]
    tot = sum(r["passed"] for r in out)
    n = sum(r["total"] for r in out)
    print("\n  📋 สรุป QC: ผ่าน %d/%d" % (tot, n))
    failed = [i["name"] for r in out for i in r["items"] if not i["ok"]]
    if failed:
        print("  ⚠️ ไม่ผ่าน: %s" % " · ".join(failed))
    try:
        os.makedirs(WORK, exist_ok=True)
        with io.open(QLOG, "a", encoding="utf-8") as f:
            for r in out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return 0 if tot == n else 1


if __name__ == "__main__":
    sys.exit(main())