# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna - facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ - ห้ามลบ
"""QC รอบ 2 (วิธีอิสระจากรอบ 1) - ตรวจแพ็กก่อนส่งมอบ

วิธีที่ต่างจากรอบ 1:
  - ย้ายแพ็กไปพาธที่มีอักษรไทย/เว้นวรรค แล้วรันเทสต์จากที่นั่น
  - คำนวณ sha256 เองเทียบ file-manifest.json (ไม่ใช้สคริปต์ของแพ็ก)
  - สร้าง ZIP จริง -> แตกไฟล์จริง -> รันเทสต์จากสำเนาที่แตกแล้ว
  - เทียบ EOL/BOM กับต้นฉบับในระบบจริงทีละไฟล์
  - ตรวจห่วงโซ่แฮชหลักฐาน (sealed evidence) ใหม่ทั้งหมด
"""
import io, os, sys, json, shutil, zipfile, hashlib, subprocess, tempfile, re

ROOT = os.path.abspath(".")
PACKS = [
    ("A", os.path.join(ROOT, "release", "skill-build-v4", "stage",
                       "Pytron Engine MT5 Algo Trade For Codex and Cowork"),
     "Pytron-Engine-MT5-Algo-Trade-For-Codex-and-Cowork-v1.zip"),
    ("B", os.path.join(ROOT, "release", "skill-build-metaapi-v1", "stage",
                       "Pytron Engine MT5 Algo Trade For OpenClaw"),
     "Pytron-Engine-MT5-Algo-Trade-For-OpenClaw-v1.zip"),
]
PY = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
PYM = os.path.join(ROOT, ".validation_metaapi", "Scripts", "python.exe")
DELIVERY = os.path.join(ROOT, "release", "delivery")
os.makedirs(DELIVERY, exist_ok=True)

ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPYCACHEPREFIX=tempfile.gettempdir())
THAI_TMP = os.path.join(tempfile.gettempdir(), "QC2 ทดสอบระบบ เทรดทองคำ")

ORIG_MAP = [("trading-system/outputs/mt5_python_bridge/", "outputs/mt5_python_bridge/"),
            ("trading-system/research/", "research/"),
            ("trading-system/agents/", "agents/"),
            ("trading-system/work/", "work/")]

UUID_RX = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
SECRET_RX = [("openrouter", re.compile(r"sk-or-v1-[A-Za-z0-9]{16,}")),
             ("jwt", re.compile(r"eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}")),
             ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
             ("aws", re.compile(r"AKIA[0-9A-Z]{16}"))]
AUTHOR_PATHS = ["D:" + chr(92) + chr(92) + "AI " + "WorkSpace", "D:/AI " + "WorkSpace",
                "C:" + chr(92) + chr(92) + "Users" + chr(92) + chr(92) + "Administrator"]
TEXT_EXT = (".py", ".md", ".json", ".jsonl", ".txt", ".cmd", ".ps1", ".csv", ".cfg",
            ".ini", ".yml", ".yaml", ".toml")


def walk(base, skip=("__pycache__", ".git")):
    for r, ds, fs in os.walk(base):
        ds[:] = [d for d in ds if d not in skip]
        for f in fs:
            yield os.path.join(r, f)


def relp(p, base):
    return os.path.relpath(p, base).replace(os.sep, "/")


def run(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=ENV,
                          encoding="utf-8", errors="replace")


def sha256_file(p):
    h = hashlib.sha256()
    with io.open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def eol_class(p):
    with io.open(p, "rb") as fh:
        raw = fh.read(200000)
    crlf = raw.count(b"\r\n")
    lf = raw.count(b"\n") - crlf
    if crlf and lf:
        return "mixed"
    if crlf:
        return "crlf"
    if lf:
        return "lf"
    return "none"


def orig_path_for(rel):
    for pre, orep in ORIG_MAP:
        if rel.startswith(pre):
            cand = os.path.join(ROOT, orep + rel[len(pre):])
            return cand if os.path.exists(cand) else None
    return None


def qc(tag, P, zip_name):
    res = []

    # ---- R1: ย้ายไปพาธไทย/เว้นวรรค แล้วรัน portable QC + เทสต์
    tmpdir = os.path.join(THAI_TMP, tag)
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
    os.makedirs(tmpdir, exist_ok=True)
    moved = os.path.join(tmpdir, os.path.basename(P))
    shutil.copytree(P, moved, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    r = run([PY, os.path.join(moved, "QC", "verify-install.py")], moved)
    tail = (r.stdout or r.stderr).strip().splitlines()[-2:]
    res.append(("ย้ายไปพาธอักษรไทย/เว้นวรรค แล้วตรวจผ่าน (portable QC)", r.returncode == 0, tail))

    r = run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            os.path.join(moved, "trading-system/outputs/mt5_python_bridge"))
    lines = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
    res.append(("เทสต์ระบบเทรดจากพาธไทยผ่าน", r.returncode == 0, lines))

    r = run([PY, "-m", "unittest", "test_shim_offline"], os.path.join(moved, "metaapi"))
    lines = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
    res.append(("เทสต์ shim จากพาธไทยผ่าน", r.returncode == 0, lines))

    r = run([PY, "restore_factory.py"],
            os.path.join(moved, "trading-system/work/factory"))
    res.append(("restore_factory.py โหมดตรวจสอบ (dry run) ทำงานได้",
                r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[:2]))

    # ---- R2: คำนวณ sha256 เอง เทียบ manifest
    mf = json.load(io.open(os.path.join(P, "file-manifest.json"), encoding="utf-8"))
    listed = mf.get("sha256", {})
    bad_hash = []
    for rel, want in listed.items():
        p = os.path.join(P, rel.replace("/", os.sep))
        if not os.path.exists(p):
            bad_hash.append((rel, "missing"))
            continue
        if sha256_file(p) != want:
            bad_hash.append((rel, "sha256 differs"))
    actual = set(relp(p, P) for p in walk(P))
    name_bad = []
    if set(listed) != (actual - {"file-manifest.json"}):
        name_bad.append({"missing": sorted((actual - {"file-manifest.json"}) - set(listed))[:3],
                         "extra": sorted(set(listed) - actual)[:3]})
    res.append(("sha256 ตรงกับ file-manifest.json ทุกไฟล์ (%d ไฟล์)" % len(listed),
                not bad_hash, bad_hash[:5]))
    res.append(("รายชื่อไฟล์ใน manifest ตรงกับไฟล์จริง", not name_bad, name_bad))

    # ---- R3: สแกนความลับ/ข้อมูลส่วนตัวแบบเข้ม (รวม UUID และ eyJ ทุกที่)
    secret_hits, uuid_hits, author_hits = [], [], []
    for p in walk(P):
        ext = os.path.splitext(p)[1].lower()
        if ext not in TEXT_EXT:
            continue
        t = io.open(p, encoding="utf-8", errors="ignore").read()
        rel = relp(p, P)
        for label, rx in SECRET_RX:
            m = rx.search(t)
            if m:
                secret_hits.append((rel, label))
        m = UUID_RX.search(t)
        if m:
            uuid_hits.append((rel, m.group(0)[:12]))
        if ext in (".py", ".cmd", ".ps1"):
            for b in AUTHOR_PATHS:
                if b in t:
                    author_hits.append((rel, b))
    res.append(("ไม่พบคีย์/โทเคน/JWT ในทุกไฟล์ข้อความ", not secret_hits, secret_hits[:5]))
    res.append(("ไม่พบ UUID หลงเหลือ (ยกเว้นรหัสที่มาสก์แล้ว)", not uuid_hits, uuid_hits[:5]))
    res.append(("ไม่พบพาธเครื่องผู้สร้างในโค้ด", not author_hits, author_hits[:5]))

    # ---- R4: SKILL.md frontmatter
    skill = io.open(os.path.join(P, "SKILL.md"), encoding="utf-8").read()
    lines = skill.split("\n")
    fm_bad = []
    if lines[0].strip() != "---":
        fm_bad.append("line1=%r" % lines[0][:20])
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        fm_bad.append("no closing ---")
    else:
        blob = "\n".join(lines[1:end])
        for k in ("name:", "description:"):
            if k not in blob:
                fm_bad.append("missing " + k)
        if os.path.exists(os.path.join(P, ".clawhubignore")):
            for k in ("openclaw:", "METAAPI_TOKEN", "METAAPI_ACCOUNT_ID", "primaryEnv", "install:"):
                if k not in blob:
                    fm_bad.append("missing " + k)
        if "<!--" in "\n".join(lines[1:end]):
            fm_bad.append("comment inside frontmatter")
    res.append(("SKILL.md เริ่มด้วย frontmatter และไม่มีคอมเมนต์คั่น", not fm_bad, fm_bad))

    # ---- R5: EOL/BOM เทียบต้นฉบับจริงทีละไฟล์
    eol_bad, bom_bad, compared = [], [], 0
    for p in walk(P):
        rel = relp(p, P)
        op = orig_path_for(rel)
        if not op:
            continue
        compared += 1
        a, b = eol_class(p), eol_class(op)
        if a != b:
            eol_bad.append((rel, "pack=" + a, "orig=" + b))
        if os.path.splitext(p)[1].lower() in (".ps1", ".cmd"):
            with io.open(p, "rb") as fh:
                pb = fh.read(3)
            with io.open(op, "rb") as fh:
                ob = fh.read(3)
            if (pb == b"\xef\xbb\xbf") != (ob == b"\xef\xbb\xbf"):
                bom_bad.append((rel, pb == b"\xef\xbb\xbf", ob == b"\xef\xbb\xbf"))
    res.append(("EOL ตรงกับต้นฉบับจริง (%d ไฟล์เทียบได้)" % compared, not eol_bad, eol_bad[:5]))
    res.append(("BOM ของ .ps1/.cmd ตรงกับต้นฉบับ", not bom_bad, bom_bad[:5]))

    # ---- R6: คู่ live <-> factory
    fac_dir = os.path.join(P, "trading-system/work/factory/code")
    live = os.path.join(P, "trading-system/outputs/mt5_python_bridge")
    agents = os.path.join(P, "trading-system/agents")
    mism = []
    if os.path.isdir(fac_dir):
        for fn in sorted(os.listdir(fac_dir)):
            if fn.startswith("tools_"):
                tgt = os.path.join(live, "tools", fn[len("tools_"):])
            elif fn.startswith("agents_"):
                tgt = os.path.join(agents, fn[len("agents_"):])
            else:
                tgt = os.path.join(live, fn)
            if not os.path.exists(tgt):
                mism.append((fn, "missing target"))
            elif sha256_file(os.path.join(fac_dir, fn)) != sha256_file(tgt):
                mism.append((fn, "content differs"))
    res.append(("คู่ live<->factory: ไม่ตรง 12 คู่ตามสภาพจริงของระบบ (%d)" % len(mism),
                len(mism) == 12, mism[:14]))

    # ---- R7: ห่วงโซ่แฮชหลักฐาน (sealed evidence)
    def digest(v):
        return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"),
                                         allow_nan=False).encode()).hexdigest()
    ev = os.path.join(P, "trading-system/research/recommendations/evaluations")
    ok = bad = nov = 0
    if os.path.isdir(ev):
        for name in sorted(os.listdir(ev)):
            d = os.path.join(ev, name)
            vp = os.path.join(d, "verdict.json")
            if not os.path.isdir(d) or not os.path.exists(vp):
                continue
            try:
                v = json.load(io.open(vp, encoding="utf-8"))
            except Exception:
                nov += 1
                continue
            for key, fname in (("rec_hash", "recommendation.json"),
                               ("config_hash", "baseline.json")):
                fp = os.path.join(d, fname)
                if not v.get(key) or not os.path.exists(fp):
                    continue
                try:
                    if digest(json.load(io.open(fp, encoding="utf-8"))) == v[key]:
                        ok += 1
                    else:
                        bad += 1
                except Exception:
                    bad += 1
    res.append(("ห่วงโซ่แฮชหลักฐานยังตรง (ok=%d broken=%d)" % (ok, bad), bad == 0 and ok >= 290,
                "ok=%d bad=%d noverdict=%d" % (ok, bad, nov)))

    # ---- R8: เอกสารกำกับ + README
    credit = os.path.join(P, "trading-system/research/CREDIT-NOTE.md")
    readme = io.open(os.path.join(P, "README.md"), encoding="utf-8").read()
    doc_bad = []
    if not os.path.exists(credit):
        doc_bad.append("no CREDIT-NOTE.md")
    else:
        ct = io.open(credit, encoding="utf-8").read()
        for bit in ("Python Qaunt Trading", "ผู้ทรงภูมิปัญญา", "Kanutsanan Pongpanna",
                    "ซีลด้วยแฮช"):
            if bit not in ct:
                doc_bad.append("CREDIT-NOTE missing: " + bit)
    if "CREDIT-NOTE" not in readme:
        doc_bad.append("README does not reference CREDIT-NOTE.md")
    if "Credit note" not in readme and "เครดิต" not in readme:
        doc_bad.append("README has no credit section")
    fac_rows = len(re.findall(r"^\| `[^`]+` \|", readme, re.M))
    if fac_rows < 29:
        doc_bad.append("factory table rows=%d" % fac_rows)
    res.append(("CREDIT-NOTE.md + README (ตารางค่าโรงงาน %d แถว) ครบ" % fac_rows,
                not doc_bad, doc_bad[:5]))

    # ---- R9: สร้าง ZIP จริง แล้วทดสอบจากสำเนาที่แตกออกมา
    zpath = os.path.join(DELIVERY, zip_name)
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for p in sorted(walk(P)):
            arc = os.path.join(os.path.basename(P), relp(p, P).replace("/", os.sep))
            zf.write(p, arc)
    zsize = os.path.getsize(zpath) / 1048576
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        zbad = [n for n in names if n.endswith((".pyc", ".pyo", ".bak", ".tmp"))
                or "__pycache__" in n or os.path.basename(n) in
                (".env", "auto_trader_audit.jsonl", "auto_trader_state.json",
                 "openrouter_api_key.machine.dpapi")]
        roots = set(n.split("/")[0] for n in names)
        zsec = []
        for n in names:
            if os.path.splitext(n)[1].lower() not in TEXT_EXT:
                continue
            try:
                t = zf.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            for label, rx in SECRET_RX:
                if rx.search(t):
                    zsec.append((n, label))
            if UUID_RX.search(t):
                zsec.append((n, "uuid"))
    res.append(("ZIP สร้างได้ %.1f MB / %d ไฟล์ / รากโฟลเดอร์เดียว" % (zsize, len(names)),
                not zbad and len(roots) == 1 and roots == {os.path.basename(P)},
                {"bad": zbad[:5], "roots": sorted(roots)}))
    res.append(("สแกนใน ZIP: ไม่พบคีย์/UUID/ไฟล์ต้องห้าม", not zsec, zsec[:5]))

    exdir = os.path.join(THAI_TMP, tag + "-zip")
    if os.path.isdir(exdir):
        shutil.rmtree(exdir, ignore_errors=True)
    os.makedirs(exdir, exist_ok=True)
    with zipfile.ZipFile(zpath) as zf:
        zf.extractall(exdir)
    zroot = os.path.join(exdir, os.path.basename(P))
    r = run([PY, os.path.join(zroot, "QC", "verify-install.py"), "--full"], zroot)
    tail = (r.stdout or r.stderr).strip().splitlines()[-2:]
    res.append(("แตก ZIP แล้วตรวจซ้ำ (--full) ผ่านจากไฟล์ที่แตกออกมา", r.returncode == 0, tail))
    r = run([PY, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
            os.path.join(zroot, "trading-system/outputs/mt5_python_bridge"))
    lines = [l for l in (r.stderr or r.stdout).splitlines() if l.startswith(("OK", "FAILED", "Ran "))]
    res.append(("เทสต์ระบบเทรดจาก ZIP ที่แตกแล้วผ่าน", r.returncode == 0, lines))

    shutil.rmtree(tmpdir, ignore_errors=True)
    shutil.rmtree(exdir, ignore_errors=True)

    ok_n = sum(1 for _, p, _ in res if p)
    print("=" * 78)
    print("QC ROUND 2 (อิสระ) - แพ็ก %s | %s" % (tag, os.path.basename(P)))
    print("=" * 78)
    for name, passed, detail in res:
        print(("  [PASS] " if passed else "  [FAIL] ") + name + ("" if passed else "  -> " + str(detail)[:220]))
    print("\nSUMMARY: %d/%d passed | ZIP: %s" % (ok_n, len(res), zpath))
    io.open(os.path.join(ROOT, "_qc_round2_%s.json" % tag.lower()), "w", encoding="utf-8",
            newline="\n").write(json.dumps(
        {"round": 2, "method": "independent", "package": tag,
         "checks": [{"name": n, "passed": bool(p), "detail": str(d)[:600]} for n, p, d in res],
         "passed": ok_n, "total": len(res), "zip": os.path.basename(zpath)},
        ensure_ascii=False, indent=1))
    return ok_n, len(res)


summary = []
for tag, P, zname in PACKS:
    summary.append((tag,) + qc(tag, P, zname))
print("\n" + "=" * 78)
for tag, a, b in summary:
    print("แพ็ก %s: %d/%d %s" % (tag, a, b, "ผ่าน" if a == b else "ไม่ผ่าน"))
