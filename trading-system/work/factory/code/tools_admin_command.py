#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""คำสั่งที่ 'แอดมินบอท (agent)' สั่งระบบได้ — จุดเดียวที่บอทคุยกับสคริปต์ Python

เจ้าของระบบกำหนด (19 ก.ย. 2026):
  • "ระบบ admin bot intelligence automate skills ทั้งระบบเป็น agent"
  • "ในระบบของ admin bot อาจจะไม่ใช่แค่คำแนะนำ — อาจจะเป็นคำสั่งเลยจาก agent"
  • "บอทต้องรู้ทุกครั้งว่าต้องสื่อสารกับ python script ยังไง — ต้องมีระบบทำให้บอทรู้"

หลักการ: บอทไม่ต้องเดาคำสั่ง — รัน `--list` เพื่อดูรายการที่อนุญาตพร้อมขอบเขต
         และทุกคำสั่งถูกตรวจ + บันทึก log ทุกครั้ง

ใช้:
  python tools/admin_command.py --list                       # ดูคำสั่งที่อนุญาตทั้งหมด
  python tools/admin_command.py --run set_value --key <key> --value <v> --why "<เหตุผล>"
  python tools/admin_command.py --run admin_round --apply    # รันรอบแอดมิน (ปรับจริงในกรอบ)
  python tools/admin_command.py --run rollback_last          # คืนค่า config จากสำรองล่าสุด
  python tools/admin_command.py --run restore_factory --why "<เหตุผล>"
  python tools/admin_command.py --run simulation --tool net_age_sim
  python tools/admin_command.py --run job --action pause --name "trading-analytics"
  python tools/admin_command.py --run news_research
  python tools/admin_command.py --run history --hours 24
"""
import argparse
import datetime
import glob
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BR))
sys.path.insert(0, BR)

LOG = os.path.join(ROOT, "work", "admin_bot_log.jsonl")
CFG = os.path.join(BR, "auto_config.json")
PY = sys.executable

# ── คำสั่งที่อนุญาต (พร้อมขอบเขต) — บอทอ่านจาก --list ──
COMMANDS = {
    "set_value": {
        "desc": "ปรับ 'ค่าต่างๆ' ใน auto_config.json ภายในกรอบปลอดภัยของแอดมินบอท",
        "args": {"--key": "ชื่อคีย์ (ดู --list-keys)", "--value": "ค่าตัวเลขใหม่", "--why": "เหตุผล (บังคับ)"},
        "writes": "auto_config.json (atomic + สำรองก่อนเขียน)",
    },
    "list_keys": {
        "desc": "ดูคีย์ที่ปรับได้ทั้งหมด + ขอบเขตต่ำสุด/สูงสุด",
        "args": {},
        "writes": "-",
    },
    "admin_round": {
        "desc": "รันรอบแอดมิน (กฎวิวัฒน์จากสถิติจริง + rollback อัตโนมัติถ้าผลแย่ลง)",
        "args": {"--apply": "ใส่เพื่อปรับจริง (ไม่ใส่ = โหมดแนะนำ)"},
        "writes": "auto_config.json (ถ้า --apply)",
    },
    "rollback_last": {
        "desc": "คืนค่า auto_config.json จากไฟล์สำรองล่าสุดของแอดมินบอท",
        "args": {},
        "writes": "auto_config.json",
    },
    "restore_factory": {
        "desc": "คืนค่าโรงงานทั้งชุด (config + โค้ด + cron) — ใช้เมื่อระบบเพี้ยน",
        "args": {"--why": "เหตุผล (บังคับ)"},
        "writes": "config + โค้ด (ตามค่าโรงงาน)",
    },
    "simulation": {
        "desc": "รันสคริปต์จำลอง (อ่านอย่างเดียว) เพื่อหาหลักฐานก่อนเสนอ",
        "args": {"--tool": "ชื่อไฟล์ใน tools/ ที่ลงท้าย _sim.py"},
        "writes": "-",
    },
    "job": {
        "desc": "พัก/เปิดงานวิจัย (ห้ามแตะ consumer และห้ามแตะตัวเทรด)",
        "args": {"--action": "pause|resume", "--name": "ชื่องานวิจัย"},
        "writes": "สถานะ cron",
    },
    "news_research": {
        "desc": "ดึงข้อมูลข่าวล่าสุด + สถิติตั้งต้น (บอทเป็นผู้วิเคราะห์เอง)",
        "args": {"--history": "ใส่เพื่อดูประวัติงานวิจัยข่าวแทน", "--hours": "ช่วงประวัติ (ชม.)"},
        "writes": "work/news_cache.json · research/news-research-*.md",
    },
    "verify_market_hours": {
        "desc": "เทียบเวลาตลาดของระบบกับแท่งจริงของโบรกเกอร์",
        "args": {},
        "writes": "-",
    },
}

# คีย์ที่ 'ห้าม' แตะเด็ดขาด (ความปลอดภัยของเงินจริง + สิทธิ์เจ้าของระบบ)
FORBIDDEN_KEYS = ("live_enabled", "magic", "volume", "symbol")
FORBIDDEN_JOBS = ("llm-recommendation-consumer",)
FORBIDDEN_ACTIONS = (
    "start/stop ตัวเทรด (auto_trader) — เจ้าของระบบเท่านั้นที่สั่งได้",
    "ลบ/แก้ work/AUTO_TRADER_STOP (kill switch) — เจ้าของระบบเท่านั้น",
    "แก้โครงสร้างโค้ด (.py) — ทำได้แค่ปรับค่าต่างๆ ในกรอบ",
    "รันคำสั่ง shell อะไรก็ได้ — ให้ใช้คำสั่งในรายการนี้เท่านั้น",
)


def log(event, **kw):
    rec = {"time": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "source": "admin_command", "event": event, **kw}
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def bounds():
    """ดึงกรอบค่าจากแอดมินบอท (แหล่งเดียว — ไม่ให้มีกรอบซ้ำสองที่)"""
    sys.path.insert(0, HERE)
    import admin_bot_round as AB
    b = dict(AB.BOUNDS)
    b.update(AB.STRUCTURE_BOUNDS)
    return b


def get_path(cfg, key):
    cur = cfg
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_path(cfg, key, value):
    parts = key.split(".")
    cur = cfg
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value
    return cfg


def cmd_list_keys():
    b = bounds()
    print("คีย์ที่แอดมินบอทปรับได้ (%d คีย์):" % len(b))
    for k in sorted(b):
        lo, hi = b[k]
        print("  %-58s %s .. %s" % (k, lo, hi))
    print("")
    print("ห้ามแตะเด็ดขาด:", ", ".join(FORBIDDEN_KEYS))


def cmd_set_value(key, value, why):
    if not why:
        print("ปฏิเสธ: ต้องระบุ --why (เหตุผล) ทุกครั้ง")
        return 2
    if key in FORBIDDEN_KEYS or any(key.endswith("." + f) for f in FORBIDDEN_KEYS):
        print("ปฏิเสธ: คีย์ '%s' เป็นคีย์สงวน (ห้ามแตะ)" % key)
        return 3
    b = bounds()
    if key not in b:
        print("ปฏิเสธ: คีย์ '%s' ไม่อยู่ในกรอบที่อนุญาต — ดูรายการด้วย --run list_keys" % key)
        return 4
    lo, hi = b[key]
    try:
        v = float(value)
    except Exception:
        print("ปฏิเสธ: ค่าต้องเป็นตัวเลข")
        return 5
    if not (lo <= v <= hi):
        print("ปฏิเสธ: ค่า %s อยู่นอกกรอบ [%s, %s]" % (v, lo, hi))
        return 6
    from runtime_support import atomic_json
    cfg = json.loads(io.open(CFG, encoding="utf-8").read())
    cur = get_path(cfg, key)
    if cur is not None and abs(float(cur) - v) < 1e-9:
        print("ไม่มีการเปลี่ยนแปลง (ค่าเดิม = %s)" % cur)
        return 0
    shutil.copy(CFG, CFG + ".bak_admincmd_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    set_path(cfg, key, v)
    atomic_json(CFG, cfg)
    log("admin_command_set_value", key=key, **{"from": cur, "to": v}, why=why)
    print("ปรับแล้ว: %s : %s -> %s (กรอบ %s..%s)" % (key, cur, v, lo, hi))
    return 0


def cmd_admin_round(apply_):
    args = [PY, os.path.join(HERE, "admin_bot_round.py")]
    if apply_:
        args += ["--apply", "--allow-structure"]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    print((r.stdout or "") + (r.stderr or ""))
    log("admin_command_round", apply=bool(apply_), rc=r.returncode)
    return r.returncode


def cmd_rollback_last():
    baks = sorted(glob.glob(CFG + ".bak_adminbot_*") + glob.glob(CFG + ".bak_admincmd_*"))
    if not baks:
        print("ไม่มีไฟล์สำรองให้คืนค่า")
        return 2
    shutil.copy(CFG, CFG + ".bak_before_rollback_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
    shutil.copy(baks[-1], CFG)
    log("admin_command_rollback", restored_from=os.path.basename(baks[-1]))
    print("คืนค่า config จากสำรองล่าสุดแล้ว:", os.path.basename(baks[-1]))
    return 0


def cmd_restore_factory(why):
    if not why:
        print("ปฏิเสธ: restore_factory ต้องระบุ --why")
        return 2
    r = subprocess.run([PY, os.path.join(ROOT, "work", "factory", "restore_factory.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    print((r.stdout or "") + (r.stderr or ""))
    log("admin_command_restore_factory", why=why, rc=r.returncode)
    return r.returncode


def cmd_simulation(tool):
    if not tool or not tool.endswith("_sim.py"):
        print("ปฏิเสธ: อนุญาตเฉพาะไฟล์ *_sim.py ใน tools/")
        return 2
    path = os.path.join(HERE, tool)
    if not os.path.exists(path):
        print("ไม่พบเครื่องมือ:", tool)
        return 3
    r = subprocess.run([PY, path], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900, cwd=ROOT)
    print(((r.stdout or "") + (r.stderr or ""))[-4000:])
    log("admin_command_simulation", tool=tool, rc=r.returncode)
    return r.returncode


def cmd_job(action, name):
    if not action or action not in ("pause", "resume"):
        print("ปฏิเสธ: --action ต้องเป็น pause หรือ resume")
        return 2
    if not name:
        print("ปฏิเสธ: ต้องระบุ --name")
        return 3
    if any(f in name for f in FORBIDDEN_JOBS):
        print("ปฏิเสธ: ห้ามแตะงาน '%s' (จำเป็นต่อวงจรระบบ)" % name)
        return 4
    if "admin" in name.lower() and action == "pause":
        print("ปฏิเสธ: ห้ามพักงานแอดมินบอทเอง")
        return 5
    hermes = os.path.expanduser("~/AppData/Local/hermes/hermes-agent/venv/Scripts/hermes.exe")
    r = subprocess.run([hermes, "cron", action, name], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=120)
    print((r.stdout or r.stderr or "").strip()[:300])
    log("admin_command_job", action=action, name=name, rc=r.returncode)
    return r.returncode


def cmd_news_research(history, hours):
    args = [PY, os.path.join(BR, "news_feed.py")]
    if history:
        args += ["--history", "--hours", str(hours or 24)]
    else:
        args += ["--digest"]
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    print((r.stdout or "") + (r.stderr or ""))
    log("admin_command_news", history=bool(history), hours=hours)
    return r.returncode


def cmd_verify_market_hours():
    r = subprocess.run([PY, os.path.join(HERE, "verify_market_hours.py")], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=600)
    print((r.stdout or "") + (r.stderr or ""))
    log("admin_command_verify_hours", rc=r.returncode)
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description="คำสั่งที่แอดมินบอท (agent) สั่งระบบได้")
    ap.add_argument("--list", action="store_true", help="ดูคำสั่งที่อนุญาตทั้งหมด")
    ap.add_argument("--run", choices=sorted(COMMANDS), help="ชื่อคำสั่ง")
    ap.add_argument("--key"); ap.add_argument("--value"); ap.add_argument("--why")
    ap.add_argument("--apply", action="store_true"); ap.add_argument("--tool")
    ap.add_argument("--action"); ap.add_argument("--name")
    ap.add_argument("--history", action="store_true"); ap.add_argument("--hours", type=float, default=24.0)
    a = ap.parse_args()

    if a.list or not a.run:
        print("=== คำสั่งที่แอดมินบอท (agent) ใช้ได้ ===")
        for name, info in COMMANDS.items():
            print("\n• %s — %s" % (name, info["desc"]))
            for k, v in (info["args"] or {}).items():
                print("    %s : %s" % (k, v))
            print("    เขียนไฟล์: %s" % info["writes"])
        print("\n=== ห้ามทำเด็ดขาด ===")
        for f in FORBIDDEN_ACTIONS:
            print("  ✗ " + f)
        print("\nหมายเหตุ: ทุกคำสั่งถูกบันทึกที่ work/admin_bot_log.jsonl")
        return 0

    if a.run == "set_value":
        return cmd_set_value(a.key, a.value, a.why)
    if a.run == "list_keys":
        cmd_list_keys(); return 0
    if a.run == "admin_round":
        return cmd_admin_round(a.apply)
    if a.run == "rollback_last":
        return cmd_rollback_last()
    if a.run == "restore_factory":
        return cmd_restore_factory(a.why)
    if a.run == "simulation":
        return cmd_simulation(a.tool)
    if a.run == "job":
        return cmd_job(a.action, a.name)
    if a.run == "news_research":
        return cmd_news_research(a.history, a.hours)
    if a.run == "verify_market_hours":
        return cmd_verify_market_hours()
    return 0


if __name__ == "__main__":
    sys.exit(main())
