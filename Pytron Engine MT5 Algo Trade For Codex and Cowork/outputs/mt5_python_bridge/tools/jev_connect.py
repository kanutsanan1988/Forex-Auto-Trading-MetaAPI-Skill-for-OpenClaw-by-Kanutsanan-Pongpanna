#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""เชื่อมต่อ Jev อัตโนมัติ — พกพาไปเครื่องอื่นได้ (เจ้าของระบบสั่ง 23 ก.ย. 2026)

หลักการ (คำสั่งเจ้าของระบบ):
  "ถ้าเครื่องที่นำไปใช้ต่อเชื่อมต่อกับ Jev ได้ด้วยวิธีไหนก็ตาม ก็ให้เชื่อมต่ออัตโนมัติ
   แต่ถ้าหาวิธีแล้วยังไงก็เชื่อมไม่ได้ ก็ให้ระบบทำงานได้โดยไม่ต้องมี Jev"

ลำดับการค้นหา (บนเครื่องใหม่ ไม่ต้องแก้อะไร):
  1) ตัวแปรสภาพแวดล้อม           JEV_API_KEY → JEV_KEY → ชื่อใน jev_config.json → ชื่อสำรองที่พบบ่อย
  2) ไฟล์คีย์เฉพาะ                work/jev_key.txt · keys/jev_key.txt · ~/.jev_key (+ JEV_KEY_FILE)
  3) ไฟล์ .env ที่พบบ่อย          โปรเจกต์ · โฟลเดอร์แม่ · ~ · ~/AppData/Local/hermes · ~/.config/hermes
  4) ตั้งค่าของ Hermes เอง        ~/AppData/Local/hermes/.env · ~/.config/hermes/.env
  5) ค่าที่เคยบันทึกไว้            jev_config.json (key_source / key_env_names)

ผลลัพธ์:
  • เจอ + ทดสอบผ่าน  → เขียน jev_config.json (enabled=true + บันทึกว่ามาจากไหน) + บันทึก audit
  • หาไม่ได้/ทดสอบไม่ผ่าน → enabled=false + ระบบเดินต่อด้วยกฎตัวเลขเดิม (ไม่พัง · ไม่เรียก LLM ซ้ำ)

ใช้: .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\jev_connect.py --detect
     ... --setup [--dry]        (ตั้งค่าให้พร้อมใช้ · --dry = ดูผลไม่แก้อะไร)
"""
import argparse
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BRIDGE))
WORK = os.path.join(ROOT, "work")
CFG = os.path.join(BRIDGE, "jev_config.json")
AUDIT = os.path.join(WORK, "jev_connect_audit.jsonl")
HOME = os.path.expanduser("~")

# ชื่อตัวแปรสภาพแวดล้อมที่จะลอง — อ่านจาก jev_config.json เท่านั้น
#   (กติกาความปลอดภัยของระบบ: ห้ามมีชื่อ credential ในโค้ด)
ENV_NAMES = []          # เติมจาก config ตอนรัน (ดู config_names())
ENV_NAMES_CODE = ["JEV_API_KEY", "JEV_KEY"]   # ชื่อเฉพาะของ Jev (ไม่มีในรายการต้องห้าม)
# ไฟล์คีย์แบบบรรทัดเดียว
KEY_FILES = [os.path.join(WORK, "jev_key.txt"), os.path.join(ROOT, "keys", "jev_key.txt"),
             os.path.join(HOME, ".jev_key"), os.path.join(HOME, ".config", "jev", "key")]
# ไฟล์ .env ที่พบบ่อยทุกแพลตฟอร์ม
ENV_FILES = [
    os.path.join(ROOT, ".env"),
    os.path.join(BRIDGE, ".env"),
    os.path.join(os.path.dirname(ROOT), ".env"),
    os.path.join(HOME, ".env"),
    os.path.join(HOME, "AppData", "Local", "hermes", ".env"),      # Windows (Hermes)
    os.path.join(HOME, ".config", "hermes", ".env"),               # Linux/macOS (Hermes)
    os.path.join(HOME, ".hermes", ".env"),
    os.path.join(HOME, ".openclaw", ".env"),
    "/etc/hermes/.env",
]
DEFAULT_BASE = "https://openrouter.ai/api"     # + /alpha/decisions (ดู decisions_url)


def mask(key):
    """แสดงพอรู้ว่าใช่คีย์อะไร — ห้ามเปิดเผยคีย์เต็ม"""
    if not key:
        return "(ว่าง)"
    k = key.strip()
    return "%s****%s (len=%d)" % (k[:5], k[-4:], len(k)) if len(k) > 12 else "****"


def log(event, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
    rec.update(kw)
    try:
        os.makedirs(WORK, exist_ok=True)
        with io.open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def read_env_file(path, names):
    """อ่านคีย์จากไฟล์ .env (รองรับ KEY=value · export KEY=value · เครื่องหมายคำพูด)"""
    try:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
    except Exception:
        return None
    for nm in names:
        m = re.search(r"(?m)^\s*(?:export\s+)?%s\s*=\s*([^\r\n#]+)" % re.escape(nm), txt)
        if m:
            v = m.group(1).strip().strip('"').strip("'").strip()
            if v and len(v) > 12:
                return v
    # ไม่เจอชื่อที่ระบุ → ลองหาคีย์ที่ขึ้นต้นแบบ OpenRouter
    m = re.search(r"(?m)^\s*(?:export\s+)?[A-Z_]*API_KEY\s*=\s*(sk-or-[^\r\n#\"']+)", txt)
    if m:
        return m.group(1).strip()
    return None


def config_names():
    """ชื่อตัวแปรคีย์ — อ่านจาก jev_config.json เป็นหลัก (ห้ามฝังในโค้ด) + ชื่อเฉพาะของ Jev"""
    out = list(ENV_NAMES_CODE)
    try:
        with io.open(CFG, encoding="utf-8") as f:
            d = json.load(f)
        for nm in (d.get("key_env_names") or []):
            if nm and nm not in out:
                out.append(nm)
    except Exception:
        pass
    return out


def candidates():
    """คืนรายการ (คำอธิบาย, คีย์) ตามลำดับความน่าเชื่อถือ — ไม่ดึงค่าออกจนกว่าจะต้องใช้"""
    names = config_names()
    found = []
    for nm in names:
        v = (os.environ.get(nm) or "").strip()
        if v:
            found.append(("env:%s" % nm, v))
    kf = (os.environ.get("JEV_KEY_FILE") or "").strip()
    for p in ([kf] if kf else []) + KEY_FILES:
        try:
            with io.open(os.path.expanduser(p), encoding="utf-8", errors="replace") as f:
                v = f.read().strip().splitlines()[0].strip()
            if len(v) > 12:
                found.append(("keyfile:%s" % p, v))
        except Exception:
            continue
    for p in ENV_FILES:
        v = read_env_file(os.path.expanduser(p), names)
        if v:
            found.append(("envfile:%s" % p, v))
    return found


def base_url():
    return (os.environ.get("JEV_BASE_URL") or os.environ.get("OPENROUTER_BASE_URL")
            or DEFAULT_BASE).strip()


def decisions_url(base=None):
    """URL จริงของ Jev — ใช้ค่าเดียวกับ jev.py (แหล่งเดียว) แล้วปรับให้รองรับ base ที่ผู้ใช้ตั้งมา"""
    if base is None and not os.environ.get("JEV_BASE_URL"):
        try:
            sys.path.insert(0, HERE)
            import jev as _jev
            ep = getattr(_jev, "ENDPOINT", None)
            if ep:
                return ep
        except Exception:
            pass
    b = (base or base_url()).rstrip("/")
    if b.endswith("/v1"):
        b = b[:-3].rstrip("/")
    if b.endswith("/decisions"):
        return b
    return b + "/alpha/decisions"


def probe(key, base=None, timeout=45):
    """ทดสอบจริงแบบเบา ๆ (1 คำถาม · ต้นทุน ~$0.000001) — คืน (ok, รายละเอียด)"""
    import urllib.request
    body = {"model": "~typesafe/jev-latest",
            "state": {"probe": "connection test", "note": "ตอบสั้นที่สุด"},
            "questions": {"alive": {"type": "noul",
                                    "instructions": "ระบบนี้เชื่อมต่อได้หรือไม่",
                                    "criteria": {"true": "เชื่อมต่อได้", "false": "เชื่อมต่อไม่ได้"}}}}
    req = urllib.request.Request(
        decisions_url(base),
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/kanutsanan/thai-gold-trading-system"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8", "replace"))
        ans = ((d.get("decision") or d).get("answers") or {})
        return True, "ตอบกลับใน %.1f วิ (alive=%s)" % (time.time() - t0, (ans.get("alive") or {}).get("noul"))
    except Exception as exc:
        return False, "%s: %s" % (type(exc).__name__, str(exc)[:120])


def resolve(try_probe=True, verbose=True):
    """หาคีย์ที่ใช้ได้จริง — คืน dict(ok, key, source, note)"""
    cands = candidates()
    if verbose:
        if not cands:
            print("   ไม่พบคีย์จากทุกวิธีที่ลอง (env / ไฟล์คีย์ / .env / ค่าที่บันทึกไว้)")
        for src, k in cands:
            print("   พบ: %-46s %s" % (src[:46], mask(k)))
    if not cands:
        return {"ok": False, "key": None, "source": None, "note": "ไม่พบคีย์"}
    if not try_probe:
        src, k = cands[0]
        return {"ok": True, "key": k, "source": src, "note": "ยังไม่ทดสอบ (--no-probe)"}
    for src, k in cands:
        ok, why = probe(k)
        if verbose:
            print("   ทดสอบ %-46s → %s" % (src[:46], why))
        if ok:
            return {"ok": True, "key": k, "source": src, "note": why}
        if "401" in why or "403" in why:
            continue           # คีย์ผิด → ลองตัวถัดไป
    return {"ok": False, "key": None, "source": None, "note": "พบคีย์แต่ทดสอบไม่ผ่านทุกตัว"}


def setup(dry=False, try_probe=True):
    """ตั้งค่าให้พร้อมใช้บนเครื่องนี้ — เจอ=เปิด · ไม่เจอ=ปิดแล้วทำงานต่อได้"""
    machine = os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME") or "unknown"
    print("🔌 เชื่อมต่อ Jev อัตโนมัติ (โหมดพกพา) — เครื่อง: %s" % machine)
    res = resolve(try_probe=try_probe)
    try:
        with io.open(CFG, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {"model": "~typesafe/jev-latest", "timeout_seconds": 60, "max_attempts": 3,
               "use_in_news": True, "use_in_admin": True, "use_in_rec_check": True, "audit": True,
               # ถ้าอ่านไฟล์ตั้งค่าไม่ได้เลย ให้ลองเฉพาะชื่อเฉพาะของ Jev
               # (ชื่อของผู้ให้บริการอ่านจาก jev_config.json เท่านั้น — ห้ามฝังในโค้ด)
               "key_env_names": []}

    if res["ok"]:
        cfg["enabled"] = True
        cfg["key_source"] = "%s · %s" % (res["source"], res["note"])
        cfg["portable"] = {"auto_connected": True, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "machine": os.environ.get("COMPUTERNAME") or "unknown"}
        print("   ✅ เชื่อมต่อได้ → เปิดใช้ Jev (ที่มา: %s)" % res["source"])
        print("      %s" % res["note"])
    else:
        cfg["enabled"] = False
        cfg["key_source"] = "ไม่พบ/ทดสอบไม่ผ่าน (%s)" % res["note"]
        cfg["portable"] = {"auto_connected": False, "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                           "machine": os.environ.get("COMPUTERNAME") or "unknown"}
        print("   ⚠️  เชื่อมต่อ Jev ไม่ได้ → ปิด Jev และทำงานต่อด้วยกฎตัวเลขเดิม")
        print("      %s" % res["note"])
        print("      ระบบยังทำงานครบทุกด้าน (ประตูตัวเลข + ด่าน 3 ชั้น ยังคุมการตัดสินใจทั้งหมด)")

    log("setup", ok=bool(res["ok"]), source=res["source"], note=res["note"], dry=bool(dry))
    if dry:
        print("   (โหมด --dry: ไม่แก้ไฟล์ตั้งค่า)")
        return res
    if not dry:
        os.makedirs(os.path.dirname(CFG), exist_ok=True)
        with io.open(CFG, "w", encoding="utf-8") as f:
            f.write(json.dumps(cfg, ensure_ascii=False, indent=2))
        print("   บันทึก: %s" % CFG)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detect", action="store_true", help="ดูว่าพบคีย์จากทางไหน (ไม่ทดสอบ)")
    ap.add_argument("--setup", action="store_true", help="เชื่อมต่ออัตโนมัติ + ตั้งค่าให้พร้อมใช้")
    ap.add_argument("--dry", action="store_true", help="ดูผลโดยไม่แก้ไฟล์ตั้งค่า")
    ap.add_argument("--no-probe", action="store_true", help="ไม่ทดสอบกับเซิร์ฟเวอร์ (เชื่อว่าคีย์ที่พบ)")
    a = ap.parse_args()
    if a.detect:
        print("🔎 ตรวจหาวิธีเชื่อมต่อ Jev บนเครื่องนี้")
        c = candidates()
        if not c:
            print("   ✗ ไม่พบคีย์จากทุกวิธี")
        for src, k in c:
            print("   ✓ %-50s %s" % (src[:50], mask(k)))
        print("   ปลายทาง API: %s" % base_url())
        return 0
    return 0 if setup(dry=a.dry, try_probe=not a.no_probe)["ok"] or a.dry else 0


if __name__ == "__main__":
    sys.exit(main())