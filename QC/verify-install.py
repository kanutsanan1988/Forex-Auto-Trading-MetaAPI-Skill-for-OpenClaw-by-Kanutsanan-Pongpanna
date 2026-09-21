# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna - facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ - ห้ามลบ
"""ตรวจแพ็กด้วยตัวเอง (portable QC) - รันได้จากในโฟลเดอร์แพ็กนี้

ใช้:  python QC/verify-install.py          (ตรวจอย่างเร็ว)
      python QC/verify-install.py --full   (เพิ่มการแฮชทุกไฟล์เทียบ file-manifest.json)

ตรวจเฉพาะ stdlib - ไม่ต้องติดตั้งอะไรเพิ่ม และไม่เชื่อมต่อเครือข่าย
ไม่ส่งออเดอร์ ไม่แตะบัญชี ไม่เขียนไฟล์ใด ๆ ในแพ็ก
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PACKAGE = os.path.dirname(HERE)
PY = sys.executable

TEXT_EXT = (".py", ".md", ".json", ".jsonl", ".txt", ".cmd", ".ps1", ".csv",
            ".cfg", ".ini", ".yml", ".yaml", ".toml")
UUID_RX = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SECRETS = [
    ("openrouter_key", re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}")),
    ("jwt_token", re.compile(r"eyJhbGciOiJ[A-Za-z0-9_.\-]{60,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
]
AUTHOR_PATHS = ["D:" + chr(92) + chr(92) + "AI " + "WorkSpace",
                "D:/AI " + "WorkSpace",
                "C:" + chr(92) + chr(92) + "Users" + chr(92) + chr(92) + "Administrator"]
BANNER_BITS = ["Python Qaunt Trading + AI(LLM) Live Research",
               "\u0e1c\u0e39\u0e49\u0e17\u0e23\u0e07\u0e20\u0e39\u0e21\u0e34\u0e1b\u0e31\u0e0d\u0e0d\u0e32",
               "Kanutsanan Pongpanna"]

IS_OPENCLAW = os.path.exists(os.path.join(PACKAGE, ".clawhubignore"))
LABEL = "OpenClaw/Hermes/clawhub/Manus" if IS_OPENCLAW else "Codex/Cowork/Cursor"

REQUIRED = ["SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
            "file-manifest.json", "QC/qc-round1.json",
            "trading-system/outputs/mt5_python_bridge/auto_trader.py",
            "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
            "trading-system/outputs/mt5_python_bridge/auto_config.json",
            "trading-system/agents/registry.json",
            "trading-system/research/README.md",
            "trading-system/research/CREDIT-NOTE.md",
            "trading-system/work/factory/restore_factory.py",
            "trading-system/work/factory/config/auto_config.factory.json",
            "trading-system/work/AUTO_TRADER_STOP",
            "metaapi/metaapi_mt5_shim.py",
            "metaapi/test_shim_offline.py",
            "references/architecture.md", "references/operations.md",
            "references/portability.md", "references/research.md", "references/modes.md",
            "scripts/verify_package.py"]
if IS_OPENCLAW:
    REQUIRED += ["scripts/metaapi_connect_check.py", "scripts/metaapi_engine_smoke.py"]

FORBIDDEN = (".env", ".env.local", "auto_trader.lock", "consumer.lock",
             "openrouter_api_key.machine.dpapi", "auto_trader_audit.jsonl",
             "auto_trader_state.json", "auto_config.json.lock", "agent_runs.jsonl")

results = []


def walk(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            yield os.path.join(root, fn)


def read(rel):
    return io.open(os.path.join(PACKAGE, rel), encoding="utf-8", errors="ignore").read()


def run(args, cwd=None):
    # แคชไบต์โค้ดชี้ไปที่โฟลเดอร์ชั่วคราวของระบบ - ไม่ทิ้งไฟล์ในแพ็ก
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
               PYTHONPYCACHEPREFIX=tempfile.gettempdir())
    return subprocess.run(args, cwd=cwd or PACKAGE, capture_output=True, text=True,
                          env=env, encoding="utf-8", errors="replace")


# 1) โครงสร้าง
missing = [r for r in REQUIRED if not os.path.exists(os.path.join(PACKAGE, r))]
results.append(("ไฟล์บังคับครบ", not missing, missing))

# 2) ไม่มีความลับ
hits = []
for p in walk(PACKAGE):
    if os.path.splitext(p)[1].lower() not in TEXT_EXT:
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for name, rx in SECRETS:
        if rx.search(t):
            hits.append((os.path.relpath(p, PACKAGE), name))
results.append(("ไม่พบคีย์/ความลับในแพ็ก", not hits, hits[:5]))

# 3) ไม่มีไฟล์สถานะสด
bad = [os.path.relpath(p, PACKAGE) for p in walk(PACKAGE) if os.path.basename(p) in FORBIDDEN]
results.append(("ไม่มีไฟล์สถานะสด/ความลับ", not bad, bad[:5]))

# 4) live ปิด
cfg = json.load(io.open(os.path.join(PACKAGE, "trading-system/outputs/mt5_python_bridge/auto_config.json"),
                        encoding="utf-8"))
results.append(("live_enabled = false (เริ่มที่สภาวะหยุด)", cfg.get("live_enabled") is False, cfg.get("live_enabled")))

# 5) ค่าโรงงาน 29 คีย์
fac = json.load(io.open(os.path.join(PACKAGE, "trading-system/work/factory/config/auto_config.factory.json"),
                        encoding="utf-8"))
results.append(("ค่าโรงงานครบ 29 คีย์", len(fac) == 29, "%d คีย์" % len(fac)))

# 6) ไม่มี path ผู้สร้างในโค้ด
code_bad = []
for p in walk(PACKAGE):
    if os.path.splitext(p)[1].lower() not in (".py", ".cmd", ".ps1"):
        continue
    rel = os.path.relpath(p, PACKAGE).replace("\\", "/")
    if rel == "scripts/verify_package.py":
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for b in AUTHOR_PATHS:
        if b in t:
            code_bad.append((rel, b))
results.append(("ไม่พบ path เครื่องผู้สร้างในโค้ด", not code_bad, code_bad[:5]))

# 7) เทสต์ shim ออฟไลน์
r = run([PY, "-m", "unittest", "test_shim_offline"], cwd=os.path.join(PACKAGE, "metaapi"))
lines = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ shim ออฟไลน์ผ่าน", r.returncode == 0, lines))

# 8) เทสต์ระบบเทรด
r = run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=os.path.join(PACKAGE, "trading-system/outputs/mt5_python_bridge"))
lines = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ระบบเทรดผ่าน", r.returncode == 0, lines))

# 9) import โมดูลหลัก + ชื่อโหมด
r = run([PY, "-c",
         "import sys; sys.path.insert(0,'.');"
         "import runtime_support, strategy_engine, auto_trader, market_clock, trade_guard,"
         " side_net, auto_threshold, market_analyzer, live_executor, adaptive_shadow;"
         "from runtime_support import MODE_TITLES, DEFAULT_MODE;"
         "print('default_mode=' + DEFAULT_MODE);"
         "print('mode1=' + MODE_TITLES['internal_only']);"
         "print('mode2=' + MODE_TITLES['internal_llm_join'])"],
        cwd=os.path.join(PACKAGE, "trading-system/outputs/mt5_python_bridge"))
results.append(("โมดูลหลัก import ได้ + ชื่อโหมด 2 โหมดถูกต้อง", r.returncode == 0,
                (r.stdout or r.stderr).strip()[-200:]))

# 10) คลังงานวิจัย
rn = sum(len(f) for _, _, f in os.walk(os.path.join(PACKAGE, "trading-system/research")))
results.append(("คลังงานวิจัยครบ (>=550 ไฟล์)", rn >= 550, "%d ไฟล์" % rn))

# 11) นิยามรุ่นใหม่ + เครดิต
files_to_check = ["SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
                  "scripts/verify_package.py", "trading-system/research/CREDIT-NOTE.md",
                  "trading-system/outputs/mt5_python_bridge/auto_trader.py",
                  "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
                  "metaapi/metaapi_mt5_shim.py", "references/architecture.md",
                  "references/modes.md", "references/portability.md",
                  "references/operations.md", "references/research.md",
                  "trading-system/agents/registry.json"]
if IS_OPENCLAW:
    files_to_check += [".clawhubignore"]
banner_bad = []
for rel in files_to_check:
    p = os.path.join(PACKAGE, rel)
    if not os.path.exists(p):
        banner_bad.append((rel, "missing"))
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for bit in BANNER_BITS:
        if bit not in t:
            banner_bad.append((rel, bit[:24]))
results.append(("นิยามรุ่นใหม่ + เครดิตผู้สร้าง ครบในไฟล์สําคัญ", not banner_bad, banner_bad[:5]))

# 12) คําชี้แจงการแจกจ่าย
need = ["ปรับแต่งระบบให้เข้ากับสไตล์การเทรดของตัวเอง", "100%", "โค้ดระบบเปิด", "ไร้ขีดจำกัด"]
miss = []
for rel in ("README.md", "SKILL.md"):
    t = read(rel)
    miss += [(rel, x) for x in need if x not in t]
results.append(("คําชี้แจงการแจกจ่าย (ปรับแต่งได้ 100% / โค้ดเปิด)", not miss, miss[:5]))

# 13) SKILL.md เริ่มด้วย frontmatter ที่ถูกต้อง
skill = read("SKILL.md")
lines = skill.split("\n")
fm_bad = []
if not skill.lstrip("\ufeff").startswith("---"):
    fm_bad.append("does not start with ---")
else:
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        fm_bad.append("no closing ---")
    else:
        blob = "\n".join(lines[1:end])
        if "name:" not in blob:
            fm_bad.append("no name:")
        if "description:" not in blob:
            fm_bad.append("no description:")
        if IS_OPENCLAW:
            for k in ("openclaw:", "METAAPI_TOKEN", "METAAPI_ACCOUNT_ID", "primaryEnv"):
                if k not in blob:
                    fm_bad.append("missing " + k)
results.append(("SKILL.md frontmatter ถูกต้อง" + (" + คีย์ clawhub ครบ" if IS_OPENCLAW else ""),
                not fm_bad, fm_bad))

# 14) ไม่มีไฟล์ขยะ/แคช
junk = []
for p in walk(PACKAGE):
    rel = os.path.relpath(p, PACKAGE)
    b = os.path.basename(p)
    if "__pycache__" in rel or b.lower().endswith((".pyc", ".pyo", ".bak", ".tmp", ".orig", ".rej")):
        junk.append(rel)
results.append(("ไม่มีไฟล์ขยะ/แคชค้างในแพ็ก", not junk, junk[:5]))

# 15) manifest ตรงกับไฟล์จริง (เทียบชื่อ)
mf = json.load(io.open(os.path.join(PACKAGE, "file-manifest.json"), encoding="utf-8"))
actual = set()
for p in walk(PACKAGE):
    actual.add(os.path.relpath(p, PACKAGE).replace(os.sep, "/"))
listed = set(mf.get("sha256", {}))
mismatch = []
if listed != (actual - {"file-manifest.json"}):
    mismatch.append({"missing": sorted((actual - {"file-manifest.json"}) - listed)[:3],
                     "extra": sorted(listed - actual)[:3]})
if mf.get("package") != os.path.basename(PACKAGE):
    mismatch.append({"package": mf.get("package")})
results.append(("file-manifest.json ครอบทุกไฟล์จริง", not mismatch, mismatch))

# 16) --full: เทียบแฮชจริงทุกไฟล์
if "--full" in sys.argv:
    hash_bad = []
    for rel in sorted(listed):
        p = os.path.join(PACKAGE, rel.replace("/", os.sep))
        if not os.path.exists(p):
            hash_bad.append((rel, "missing"))
            continue
        with io.open(p, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != mf["sha256"][rel]:
            hash_bad.append((rel, "sha256 differs"))
        if len(hash_bad) >= 5:
            break
    results.append(("sha256 ของทุกไฟล์ตรงกับ manifest (ตรวจ %d ไฟล์)" % len(listed),
                    not hash_bad, hash_bad))

ok = sum(1 for _, p, _ in results if p)
print("=" * 74)
print("ตรวจแพ็กด้วยตัวเอง: Pytron Engine MT5 Algo Trade")
print("เป้าหมาย: %s   |   โฟลเดอร์: %s" % (LABEL, os.path.basename(PACKAGE)))
print("=" * 74)
for name, passed, detail in results:
    print(("  [PASS] " if passed else "  [FAIL] ") + name + ("" if passed else "  -> " + str(detail)[:200]))
print("\nสรุป: %d/%d ผ่าน" % (ok, len(results)))
print("ผลลัพธ์:", "ผ่าน - พร้อมใช้" if ok == len(results) else "ไม่ผ่าน - ตรวจรายการ [FAIL] ด้านบน")
sys.exit(0 if ok == len(results) else 1)
