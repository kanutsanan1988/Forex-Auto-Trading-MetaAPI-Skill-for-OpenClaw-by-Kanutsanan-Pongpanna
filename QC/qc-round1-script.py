import io, os, json, re, subprocess, fnmatch

ROOT = os.path.abspath(".")
B = os.path.join(ROOT, "release", "skill-build-metaapi-v1", "stage",
                 "Pytron Engine MT5 Algo Trade For OpenClaw")
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PYM = os.path.join(ROOT, ".validation_metaapi", "Scripts", "python.exe")

TEXT_EXT = (".py", ".md", ".json", ".jsonl", ".txt", ".cmd", ".ps1", ".env", ".csv",
            ".cfg", ".ini", ".yml", ".yaml", ".toml")
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
             "auto_trader_state.json", "auto_config.json.lock", "agent_runs.jsonl")
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


required = ["SKILL.md", "README.md", "LICENSE", "THIRD-PARTY-NOTICES.md", ".clawhubignore",
            "trading-system/outputs/mt5_python_bridge/auto_trader.py",
            "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
            "trading-system/agents/registry.json",
            "trading-system/research/README.md",
            "trading-system/research/SESSION-STATE.md",
            "trading-system/work/factory/restore_factory.py",
            "trading-system/work/AUTO_TRADER_STOP",
            "metaapi/metaapi_mt5_shim.py",
            "metaapi/test_shim_offline.py",
            "metaapi/evidence/live-readonly-verify-20260921.json",
            "references/architecture.md", "references/operations.md",
            "references/portability.md", "references/research.md", "references/modes.md",
            "scripts/verify_package.py",
            "scripts/metaapi_connect_check.py", "scripts/metaapi_engine_smoke.py"]
missing = [r for r in required if not os.path.exists(os.path.join(B, r))]
results.append(("โครงสร้างไฟล์บังคับครบ (แพ็ก B)", not missing, missing))

hits = []
for p in walk(B):
    if os.path.splitext(p)[1].lower() not in TEXT_EXT:
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for name, rx in SECRETS:
        m = rx.search(t)
        if m:
            hits.append((os.path.relpath(p, B), name, m.group(0)[:16]))
results.append(("ไม่มีความลับ/รหัส/UUID ค้างในแพ็ก", not hits, hits))

bad = [os.path.relpath(p, B) for p in walk(B) if os.path.basename(p) in FORBIDDEN]
results.append(("ไม่มีไฟล์สถานะสด/ความลับ", not bad, bad))

cfg = json.load(io.open(os.path.join(B, "trading-system/outputs/mt5_python_bridge/auto_config.json"),
                        encoding="utf-8"))
results.append(("live_enabled ปิดในแพ็กแจกจ่าย", cfg.get("live_enabled") is False, cfg.get("live_enabled")))
fac = json.load(io.open(os.path.join(B, "trading-system/work/factory/config/auto_config.factory.json"),
                        encoding="utf-8"))
results.append(("ค่าโรงงานเก็บครบ 29 คีย์", len(fac) == 29, f"{len(fac)} คีย์"))

code_bad = []
for p in walk(B):
    if os.path.splitext(p)[1].lower() not in (".py", ".cmd", ".ps1"):
        continue
    rel = os.path.relpath(p, B).replace("\\", "/")
    if rel == "scripts/verify_package.py":
        continue
    t = io.open(p, encoding="utf-8", errors="ignore").read()
    for b in AUTHOR_PATHS:
        if b in t:
            code_bad.append((rel, b))
results.append(("ไม่มี path ตายตัวของผู้สร้างในโค้ด", not code_bad, code_bad))

r = subprocess.run([PYM, "-m", "unittest", "test_shim_offline"],
                   cwd=os.path.join(B, "metaapi"), capture_output=True, text=True, env=NOBYTECODE, encoding="utf-8", errors="replace")
summary = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ shim ออฟไลน์ 22 ตัว (รันในสำเนาแจกจ่าย)", r.returncode == 0, summary))

r = subprocess.run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                   cwd=os.path.join(B, "trading-system/outputs/mt5_python_bridge"),
                   capture_output=True, text=True, env=NOBYTECODE, encoding="utf-8", errors="replace")
summary = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
results.append(("เทสต์ระบบเดิม 68 ตัว (รันในสำเนาแจกจ่าย)", r.returncode == 0, summary))

r = subprocess.run([PY, "-c",
    "import sys; sys.path.insert(0,'.');"
    "import runtime_support, strategy_engine, auto_trader, market_clock, trade_guard,"
    " side_net, auto_threshold, market_analyzer, live_executor, adaptive_shadow;"
    "from runtime_support import MODE_TITLES, DEFAULT_MODE;"
    "print('default_mode=' + DEFAULT_MODE);"
    "print('mode1_title=' + MODE_TITLES['internal_only']);"
    "print('mode2_title=' + MODE_TITLES['internal_llm_join'])"],
    cwd=os.path.join(B, "trading-system/outputs/mt5_python_bridge"),
    capture_output=True, text=True, env=NOBYTECODE, encoding="utf-8", errors="replace")
results.append(("โมดูลหลัก import ได้ + ชื่อโหมดถูกต้อง", r.returncode == 0,
                (r.stdout or r.stderr).strip()[-220:]))

rn = sum(len(f) for _, _, f in os.walk(os.path.join(B, "trading-system/research")))
results.append(("คลังงานวิจัยครบ (>=550 ไฟล์)", rn >= 550, f"{rn} ไฟล์"))

r = subprocess.run([PYM, "-m", "py_compile",
                    "scripts/verify_package.py", "scripts/metaapi_connect_check.py",
                    "scripts/metaapi_engine_smoke.py",
                    "metaapi/metaapi_mt5_shim.py", "metaapi/test_shim_offline.py"],
                   cwd=B, capture_output=True, text=True, env=NOBYTECODE, encoding="utf-8", errors="replace")
results.append(("สคริปต์ทั้ง 5 ของแพ็ก compile ผ่าน", r.returncode == 0, r.stderr.strip()[-200:]))

BANNER_BITS = ["Python Qaunt Trading + AI(LLM) Live Research",
               "ผู้ทรงภูมิปัญญา",
               "Kanutsanan Pongpanna"]
banner_bad = []
for rel in ("SKILL.md", "README.md", "scripts/verify_package.py",
            "scripts/metaapi_connect_check.py", "scripts/metaapi_engine_smoke.py",
            "trading-system/outputs/mt5_python_bridge/auto_trader.py",
            "trading-system/outputs/mt5_python_bridge/strategy_engine.py",
            "metaapi/metaapi_mt5_shim.py",
            "references/architecture.md", "references/modes.md",
            "references/portability.md", "references/operations.md",
            "references/research.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
            ".clawhubignore", "trading-system/agents/registry.json"):
    t = io.open(os.path.join(B, rel), encoding="utf-8", errors="ignore").read()
    for bit in BANNER_BITS:
        if bit not in t:
            banner_bad.append((rel, bit))
results.append(("นิยามรุ่นใหม่ + เครดิต ครบในไฟล์สำคัญแพ็ก B", not banner_bad, banner_bad))

need = ["ปรับแต่งระบบให้เข้ากับสไตล์การเทรดของตัวเอง", "100%", "โค้ดระบบเปิด", "ไร้ขีดจำกัด"]
miss = []
for rel in ("README.md", "SKILL.md"):
    t = io.open(os.path.join(B, rel), encoding="utf-8").read()
    miss += [(rel, x) for x in need if x not in t]
results.append(("คำชี้แจงแจกจ่ายครบใน README + SKILL", not miss, miss))

junk = []
for p in walk(B):
    b = os.path.basename(p)
    rel = os.path.relpath(p, B)
    if "__pycache__" in rel or b.lower().endswith((".pyc", ".pyo", ".bak", ".tmp", ".orig", ".rej")):
        junk.append(rel)
    elif b.startswith("auto_config.json.bak"):
        junk.append(rel)
results.append(("ไม่มีไฟล์สำรอง/แคช ค้างในแพ็ก", not junk, junk[:8]))

legal_missing = [n for n in ("LICENSE", "THIRD-PARTY-NOTICES.md")
                 if not os.path.exists(os.path.join(B, n))]
results.append(("LICENSE + THIRD-PARTY-NOTICES อยู่ในแพ็ก", not legal_missing, legal_missing))

mf = json.load(io.open(os.path.join(B, "file-manifest.json"), encoding="utf-8"))
actual = set()
for bp, bd, bf in os.walk(B):
    bd[:] = [d for d in bd if d not in ("__pycache__", ".git")]
    for f in bf:
        actual.add(os.path.relpath(os.path.join(bp, f), B).replace(os.sep, "/"))
listed = set(mf.get("sha256", {}))
manifest_bad = []
if listed != (actual - {"file-manifest.json"}):
    manifest_bad.append({"missing": sorted((actual - {"file-manifest.json"}) - listed)[:5],
                         "extra": sorted(listed - actual)[:5]})
if "file-manifest.json" in listed:
    manifest_bad.append({"self_referenced": True})
if mf.get("package") != os.path.basename(B):
    manifest_bad.append({"package_name": mf.get("package")})
results.append(("manifest ครอบทุกไฟล์จริง + ชื่อแพ็กถูก", not manifest_bad, manifest_bad))

r = subprocess.run([PYM, os.path.join(ROOT, "_qc", "fm_probe_b.py"), B],
                   capture_output=True, text=True, env=NOBYTECODE, encoding="utf-8", errors="replace")
results.append(("SKILL.md frontmatter ผ่าน YAML จริง + คีย์ clawhub ครบ",
                r.returncode == 0, (r.stdout or r.stderr).strip()[-300:]))

lines = [l.strip() for l in io.open(os.path.join(B, ".clawhubignore"), encoding="utf-8").read().splitlines()]
pats = [l for l in lines if l and not l.startswith("#")]
MUST_KEEP = [
    "trading-system/work/factory/config/auto_config.factory.json",
    "trading-system/work/factory/restore_factory.py",
    "trading-system/work/AUTO_TRADER_STOP",
    "trading-system/outputs/mt5_python_bridge/auto_config.json",
    "SKILL.md", "README.md", "LICENSE", "file-manifest.json",
    "metaapi/evidence/live-readonly-verify-20260921.json",
]
MUST_DROP = [
    "trading-system/work/auto_trader_audit.jsonl",
    "trading-system/work/auto_trader_state.json",
    "trading-system/work/openrouter_api_key.machine.dpapi",
    "trading-system/outputs/mt5_python_bridge/auto_config.json.lock",
    "trading-system/outputs/mt5_python_bridge/tools/__pycache__/x.pyc",
    "foo/.env",
]


def ignored(rel):
    for pat in pats:
        p = pat.lstrip("/")
        if p.endswith("/"):
            d = p.rstrip("/")
            if rel == d or rel.startswith(d + "/"):
                return pat
            continue
        if fnmatch.fnmatchcase(rel, p) or fnmatch.fnmatchcase(os.path.basename(rel), p):
            return pat
    return None


keep_fail = [(r_, ignored(r_)) for r_ in MUST_KEEP if ignored(r_)]
drop_fail = [r_ for r_ in MUST_DROP if not ignored(r_)]
results.append((".clawhubignore: เก็บของสำคัญ / กันความลับ ถูกต้อง",
                not keep_fail and not drop_fail, {"keep_fail": keep_fail, "drop_fail": drop_fail}))

rm = io.open(os.path.join(B, "README.md"), encoding="utf-8").read()
rows = [l for l in rm.splitlines() if l.startswith("| `")]
tab_ok = len(rows) == 29
sec_ok = all(x in rm for x in ("MetaAPI", "ค่าโรงงาน", "OpenClaw", "kill switch"))
results.append(("README: ตารางค่าโรงงาน 29 แถว + หัวข้อครบ", tab_ok and sec_ok,
                {"rows": len(rows), "sections": sec_ok}))

mbad = []
for rel in ("scripts/metaapi_connect_check.py", "scripts/metaapi_engine_smoke.py",
            "metaapi/metaapi_mt5_shim.py"):
    t = io.open(os.path.join(B, rel), encoding="utf-8").read()
    if "os.environ" not in t and "os.getenv" not in t:
        mbad.append((rel, "no env read"))
    if "order_send" not in t:
        mbad.append((rel, "no order_send guard visible"))
results.append(("สคริปต์ MetaAPI อ่านคีย์จาก environment + มีการอ้าง order_send",
                not mbad, mbad))

ev = io.open(os.path.join(B, "metaapi/evidence/live-readonly-verify-20260921.json"),
             encoding="utf-8").read()
mask_ok = "****798" in ev and "7038798" not in ev
results.append(("หลักฐานมาสก์เลขบัญชีโบรกเกอร์", mask_ok, "****798 present" if mask_ok else "check"))

ok = sum(1 for _, p, _ in results if p)
print("=" * 78)
print("QC ROUND 1 - Pytron Engine MT5 Algo Trade (OpenClaw/Hermes/clawhub/Manus)")
print("=" * 78)
for name, passed, detail in results:
    print(("  [PASS] " if passed else "  [FAIL] ") + name + ("" if passed else f"  -> {str(detail)[:400]}"))
print(f"\nSUMMARY: {ok}/{len(results)} passed")
io.open(os.path.join(ROOT, "_qc_round1_b.json"), "w", encoding="utf-8").write(json.dumps(
    {"round": 1, "revision": 1, "package": "B",
     "checks": [{"name": n, "passed": bool(p), "detail": str(d)[:500]} for n, p, d in results],
     "passed": ok, "total": len(results)}, ensure_ascii=False, indent=1))
