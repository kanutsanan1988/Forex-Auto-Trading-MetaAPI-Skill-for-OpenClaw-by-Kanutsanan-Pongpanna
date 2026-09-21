import io, os, json, re, subprocess, sys

ROOT = os.path.abspath(".")
A = os.path.join(ROOT, "release", "skill-build-v4", "stage",
                 "Pytron Engine MT5 Algo Trade For Codex and Cowork")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PYM = os.path.join(ROOT, ".validation_metaapi", "Scripts", "python.exe")

TEXT_EXT = (".py", ".md", ".json", ".jsonl", ".txt", ".cmd", ".ps1", ".env", ".csv")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SECRETS = [
    ("openrouter_key", re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}")),
    ("jwt_token", re.compile(r"eyJhbGciOiJ[A-Za-z0-9_.\-]{60,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("account_uuid", UUID),
]
FORBIDDEN = (".env", ".env.local", "auto_trader.lock", "consumer.lock",
             "openrouter_api_key.machine.dpapi", "auto_trader_audit.jsonl",
             "auto_trader_state.json", "auto_config.json.lock")
AUTHOR_PATHS = ["D:" + chr(92) + chr(92) + "AI " + "WorkSpace",
                "D:" + "/AI " + "WorkSpace",
                "C:" + chr(92) + chr(92) + "Users" + chr(92) + chr(92) + "Administrator"]

_PYC_OUT = os.path.join(os.path.abspath("."), "_pyc_out")
os.makedirs(_PYC_OUT, exist_ok=True)
NOBYTECODE = dict(os.environ, PYTHONDONTWRITEBYTECODE="1",
                  PYTHONPYCACHEPREFIX=_PYC_OUT)


results = []


def walk(base):
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git")]
        for fn in files:
            yield os.path.join(root, fn)


# QC1 โครงสร้าง
required = ["SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
            "trading-system/outputs/mt5_python_bridge/auto_trader.py",
            "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
            "trading-system/agents/registry.json",
            "trading-system/research/README.md",
            "trading-system/research/SESSION-STATE.md",
            "trading-system/work/factory/restore_factory.py",
            "trading-system/work/AUTO_TRADER_STOP",
            "metaapi/metaapi_mt5_shim.py",
            "metaapi/evidence/live-readonly-verify-20260921.json",
            "references/architecture.md", "references/operations.md",
            "references/portability.md", "references/research.md", "references/modes.md",
            "scripts/verify_package.py"]
missing = [r for r in required if not os.path.exists(os.path.join(A, r))]
results.append(("โครงสร้างไฟล์บังคับครบ", not missing, missing))

# QC2 ไม่มีความลับ
hits = []
for p in walk(A):
    if os.path.splitext(p)[1].lower() not in TEXT_EXT:
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for name, rx in SECRETS:
        m = rx.search(t)
        if m:
            hits.append((os.path.relpath(p, A), name, m.group(0)[:16]))
results.append(("ไม่มีความลับ/รหัสค้างในแพ็ก", not hits, hits))

# QC3 ไม่มีไฟล์ต้องห้าม
bad = [os.path.relpath(p, A) for p in walk(A) if os.path.basename(p) in FORBIDDEN]
results.append(("ไม่มีไฟล์สถานะสด/ความลับ", not bad, bad))

# QC4 live ปิด
cfg = json.load(io.open(os.path.join(A, "trading-system/outputs/mt5_python_bridge/auto_config.json"),
                        encoding="utf-8"))
results.append(("live_enabled ปิดในแพ็กแจกจ่าย", cfg.get("live_enabled") is False, cfg.get("live_enabled")))
results.append(("ค่าโรงงานเก็บครบ 29 คีย์",
                len(json.load(io.open(os.path.join(A, "trading-system/work/factory/config/auto_config.factory.json"),
                                      encoding="utf-8"))) == 29, "ok"))

# QC5 ไม่มี path ตายตัวในโค้ด (ยกเว้นตัวตรวจเอง)
code_bad = []
for p in walk(A):
    if os.path.splitext(p)[1].lower() not in (".py", ".cmd", ".ps1"):
        continue
    rel = os.path.relpath(p, A).replace("\\", "/")
    if rel == "scripts/verify_package.py":
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for b in AUTHOR_PATHS:
        if b in t:
            code_bad.append((rel, b))
results.append(("ไม่มี path ตายตัวของผู้สร้างในโค้ด", not code_bad, code_bad))

# QC6 เทสต์ shim ออฟไลน์ (สำเนาแจกจ่าย)
r = subprocess.run([PYM, "-m", "unittest", "test_shim_offline"],
                   cwd=os.path.join(A, "metaapi"), capture_output=True, text=True, env=NOBYTECODE, encoding='utf-8', errors='replace')
summary = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ shim ออฟไลน์ 22 ตัว (รันในสำเนาแจกจ่าย)", r.returncode == 0, summary))

# QC7 เทสต์ระบบเดิม 68 ตัว
r = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                   cwd=os.path.join(A, "trading-system/outputs/mt5_python_bridge"),
                   capture_output=True, text=True, env=NOBYTECODE, encoding='utf-8', errors='replace')
summary = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ระบบเดิม 68 ตัว (รันในสำเนาแจกจ่าย)", r.returncode == 0, summary))

# QC8 import โมดูลหลัก
r = subprocess.run([PY, "-c",
    "import sys; sys.path.insert(0,'.');"
    "import runtime_support, strategy_engine, auto_trader, market_clock, trade_guard,"
    " side_net, auto_threshold, market_analyzer, live_executor, adaptive_shadow;"
    "from runtime_support import MODE_TITLES, DEFAULT_MODE;"
    "print('default_mode=' + DEFAULT_MODE);"
    "print('mode1_title=' + MODE_TITLES['internal_only']);"
    "print('mode2_title=' + MODE_TITLES['internal_llm_join'])"],
    cwd=os.path.join(A, "trading-system/outputs/mt5_python_bridge"), capture_output=True, text=True, env=NOBYTECODE, encoding='utf-8', errors='replace')
results.append(("โมดูลหลัก import ได้ + ชื่อโหมดถูกต้อง", r.returncode == 0,
                (r.stdout or r.stderr).strip()[-220:]))

# QC9 research ครบ
rn = sum(len(f) for _, _, f in os.walk(os.path.join(A, "trading-system/research")))
results.append(("คลังงานวิจัยครบ (>=550 ไฟล์)", rn >= 550, f"{rn} ไฟล์"))

# QC10 shim compile
r = subprocess.run([PYM, "-m", "py_compile", "metaapi_mt5_shim.py", "test_shim_offline.py"],
                   cwd=os.path.join(A, "metaapi"), capture_output=True, text=True, env=NOBYTECODE, encoding='utf-8', errors='replace')
results.append(("shim + เทสต์ compile ผ่าน", r.returncode == 0, r.stderr.strip()[-150:]))

# QC11 ข้อความนิยามรุ่นใหม่ + เครดิต อยู่ในไฟล์สำคัญ
BANNER_BITS = ["Python Qaunt Trading + AI(LLM) Live Research",
               "ผู้ทรงภูมิปัญญา",
               "Kanutsanan Pongpanna"]
banner_bad = []
for rel in ("SKILL.md", "README.md", "scripts/verify_package.py",
            "trading-system/outputs/mt5_python_bridge/auto_trader.py",
            "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
            "metaapi/metaapi_mt5_shim.py",
            "references/architecture.md", "references/modes.md"):
    t = io.open(os.path.join(A, rel), encoding="utf-8", errors="ignore").read()
    for bit in BANNER_BITS:
        if bit not in t:
            banner_bad.append((rel, bit))
results.append(("นิยามรุ่นใหม่ + เครดิต ครบในไฟล์สำคัญ", not banner_bad, banner_bad))

# QC12 คำชี้แจงแจกจ่าย (ปรับแต่งได้ 100% / โค้ดเปิด)
readme = io.open(os.path.join(A, "README.md"), encoding="utf-8").read()
need = ["ปรับแต่งระบบให้เข้ากับสไตล์การเทรดของตัวเอง",
        "100%", "โค้ดระบบเปิด", "ไร้ขีดจำกัด"]
miss = [x for x in need if x not in readme]
results.append(("คำชี้แจงแจกจ่ายครบใน README", not miss, miss))

# ---- เพิ่มในรอบ QC1 (แก้): ชั้นตรวจที่ของเดิมมองไม่เห็น ----
# QC13 ไม่มี __pycache__ / .bak / patch / debug / fix
junk = []
for p in walk(A):
    b = os.path.basename(p)
    rel = os.path.relpath(p, A)
    if "__pycache__" in rel or b.lower().endswith((".pyc", ".pyo", ".bak", ".tmp")):
        junk.append(rel)
    elif b.startswith("auto_config.json.bak"):
        junk.append(rel)
results.append(("ไม่มีไฟล์สำรอง/แคช/patch ค้างในแพ็ก", not junk, junk[:8]))

# QC14 LICENSE + THIRD-PARTY-NOTICES อยู่ในแพ็กจริง
legal_missing = [n for n in ("LICENSE", "THIRD-PARTY-NOTICES.md")
                 if not os.path.exists(os.path.join(A, n))]
results.append(("LICENSE + THIRD-PARTY-NOTICES อยู่ในแพ็ก", not legal_missing, legal_missing))

# QC15 manifest ครอบทุกไฟล์จริง และไม่แฮชตัวเอง
import json as _json
mf = _json.load(io.open(os.path.join(A, "file-manifest.json"), encoding="utf-8"))
actual = set()
for bp, bd, bf in os.walk(A):
    bd[:] = [d for d in bd if d not in ("__pycache__", ".git")]
    for f in bf:
        actual.add(os.path.relpath(os.path.join(bp, f), A).replace(os.sep, "/"))
listed = set(mf.get("sha256", {}))
excluded = {"file-manifest.json"}
manifest_bad = []
if listed != (actual - excluded):
    missing = sorted((actual - excluded) - listed)[:5]
    extra_e = sorted(listed - actual)[:5]
    manifest_bad.append({"missing": missing, "extra": extra_e})
if "file-manifest.json" in listed:
    manifest_bad.append({"self_referenced": True})
results.append(("manifest ครอบทุกไฟล์จริง และไม่แฮชตัวเอง", not manifest_bad, manifest_bad))

ok = sum(1 for _, p, _ in results if p)
print("=" * 74)
print("QC ROUND 1 (rev2) - Pytron Engine MT5 Algo Trade (Codex/Cowork/Cursor)")
print("=" * 74)
for name, passed, detail in results:
    print(("  [PASS] " if passed else "  [FAIL] ") + name + ("" if passed else f"  -> {str(detail)[:300]}"))
print(f"\nSUMMARY: {ok}/{len(results)} passed")
io.open(os.path.join(ROOT, "_qc_round1_a.json"), "w", encoding="utf-8").write(_json.dumps(
    {"round": 1, "revision": 2, "package": "A",
     "checks": [{"name": n, "passed": bool(p), "detail": str(d)[:500]} for n, p, d in results],
     "passed": ok, "total": len(results)}, ensure_ascii=False, indent=1))
