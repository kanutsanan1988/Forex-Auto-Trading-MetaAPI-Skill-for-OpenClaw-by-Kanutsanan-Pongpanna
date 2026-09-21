# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""งานวิจัยข่าวทองคำ (News Research) — **โมดูลกลางของโปรเจกต์** (19 ก.ย. 2026)

ออกแบบตามที่เจ้าของระบบกำหนด:
  • **เรียกโมดูลนี้เมื่อไร ก็ทำงานวิจัยข่าวให้ครบวงจรในครั้งนั้น** (ไม่ต้องเรียกหลายคำสั่ง)
  • งานวิจัย 10 นาทีโหมด 2 + แอดมินบอท ประมวลผลข่าวล่าสุดด้วย
  • ทำงานง่าย ราบรื่น ประหยัดที่สุด: ดึงข่าวจริงไม่ถี่กว่า `REFRESH_MINUTES` (ค่าเริ่มต้น 5 นาที)
    ครั้งต่อไปที่เรียกจะอ่านจากคลังในเครื่องทันที (ไม่ยิงเน็ตซ้ำ)

วงจรในตัว (เรียกฟังก์ชันเดียวจบ):
    refresh()  →  ดึง RSS → ให้คะแนนผลกระทบต่อทอง → เก็บคลัง (dedupe) →
                  วิเคราะห์ (ธีมมหภาค + ทิศทางสุทธิ + ระดับความระวัง) →
                  เขียน research/news-log.md + research/news-research-<วันที่>.md
    digest()   →  refresh() แล้วคืนข้อความสั้นสำหรับป้อนบอท/แอดมินบอท
    note()     →  refresh() แล้วคืนบันทึกวิจัยฉบับเต็ม

แหล่งข่าว: investing.com RSS 3 ฟีด (commodities · markets · macro)
ที่มาเดิมของตรรกะ: สคริปต์นอกโปรเจกต์ — ย้ายมารวมที่เดียวเพื่อไม่ให้มีโค้ดซ้ำ
"""
import datetime
import html
import io
import json
import os
import re
import ssl
import sys
import urllib.request

BR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(BR))
RESEARCH = os.path.join(ROOT, "research")
LOG = os.path.join(RESEARCH, "news-log.md")
STORE = os.path.join(ROOT, "work", "news_cache.json")
# ★ ประวัติงานวิจัยข่าว (โครงสร้าง JSONL) — บอทดึงไปประมวลผลได้ เลือกช่วงเวลาเองได้
HISTORY = os.path.join(ROOT, "work", "news_research_history.jsonl")

# ── ตั้งค่าหลัก (แก้ที่นี่ที่เดียว) ──
REFRESH_MINUTES = 5        # ดึงข่าวจริงได้ไม่ถี่กว่านี้ (ครั้งอื่นอ่านจากคลัง)
KEEP_HOURS = 48            # เก็บข่าวในคลังย้อนหลังกี่ชั่วโมง
DIGEST_HOURS = 12          # ช่วงเวลาที่ใช้สรุป/วิเคราะห์
MIN_SCORE = 2              # คะแนนผลกระทบขั้นต่ำที่จะถือว่า "กระทบทอง"

FEEDS = {
    "commodities": "https://www.investing.com/rss/news_25.rss",
    "markets": "https://www.investing.com/rss/news_1.rss",
    "macro": "https://www.investing.com/rss/news_14.rss",
}

KEYWORDS = {
    "fed": 3, "fomc": 3, "rate hike": 3, "rate cut": 3, "interest rate": 2,
    "cpi": 3, "inflation": 2, "pce": 2, "payroll": 2, "gdp": 1,
    "oil": 1, "crude": 1, "dollar": 2, "usd": 2, "dxy": 2, "dollar index": 3,
    "gold": 2, "xau": 2, "bullion": 2, "safe haven": 2, "treasury": 2, "yield": 3,
    "recession": 2, "geopolit": 3, "war": 3, "sanction": 2, "houthi": 2,
    "russia": 2, "china": 1, "stimulus": 2, "crisis": 2, "ecb": 1, "beige": 1,
}
BULL = ["safe haven", "recession", "rate cut", "geopolit", "war", "crisis", "stimulus", "inflation"]
BEAR = ["rate hike", "strong dollar", "hawkish", "taper", "yield", "dollar up", "fed hike"]

THEMES = {
    "ดอกเบี้ย/Fed": (["fed", "fomc", "rate hike", "rate cut", "interest rate", "hawkish", "taper"],
                     "ขึ้น=กดทอง · ลด=หนุนทอง"),
    "เงินเฟ้อ": (["cpi", "inflation", "pce"], "สูง=หนุนทอง (กันเงินเฟ้อ)"),
    "ค่าเงินดอลลาร์": (["dollar", "usd", "dxy", "dollar index"], "ดอลล์แข็ง=กดทอง · อ่อน=หนุนทอง"),
    "พันธบัตร/ยีลด์": (["treasury", "yield"], "ยีลด์ขึ้น=กดทอง · ลง=หนุนทอง"),
    "ภูมิรัฐศาสตร์": (["geopolit", "war", "sanction", "houthi", "russia", "crisis"], "ตึงเครียด=หนุนทอง"),
    "พลังงาน": (["oil", "crude"], "น้ำมันขึ้น=แรงกดเงินเฟ้อ=หนุนทองทางอ้อม"),
    "เศรษฐกิจมหภาค": (["recession", "gdp", "payroll", "stimulus", "china", "ecb"], "อ่อนแอ=หนุนทอง"),
}


# ────────────────────────────── เครื่องมือพื้นฐาน ──────────────────────────────

def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse_ts(value):
    try:
        dt = datetime.datetime.fromisoformat(str(value))
        return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)
    except Exception:
        return None


def fetch(url, timeout=20):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.read().decode("utf-8", errors="ignore")


def parse_titles(rss_txt):
    titles = re.findall(r"<title>(.*?)</title>", rss_txt)
    return [html.unescape(t).strip() for t in titles[1:]]


def _hit(low, kw):
    """จับคีย์เวิร์ดแบบคำเต็ม — กันจับผิดเช่น 'war' ไปโดน 'Warren'"""
    if " " in kw or "-" in kw:
        return kw in low
    return re.search(r"\b" + re.escape(kw) + r"\b", low) is not None


def score(text):
    low = text.lower()
    return (sum(w for kw, w in KEYWORDS.items() if _hit(low, kw)),
            sum(1 for b in BULL if _hit(low, b)),
            sum(1 for b in BEAR if _hit(low, b)))


def bias_of(bull, bear):
    return "BULL" if bull > bear else ("BEAR" if bear > bull else "NEUTRAL")


def _load_store():
    try:
        data = json.load(io.open(STORE, encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"items": [], "known": []}


def _save_store(data):
    try:
        os.makedirs(os.path.dirname(STORE), exist_ok=True)
        tmp = STORE + ".tmp"
        with io.open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, STORE)
    except Exception:
        pass


# ────────────────────────────── เก็บข่าว ──────────────────────────────

def _fetch_new(timeout=20):
    store = _load_store()
    known = set(store.get("known") or [])
    fresh, errors = [], []
    stamp = _now().isoformat()
    for name, url in FEEDS.items():
        try:
            titles = parse_titles(fetch(url, timeout=timeout))
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue
        for title in titles:
            s, bull, bear = score(title)
            if s < MIN_SCORE or len(title) <= 30:
                continue
            key = title[:90]
            if key in known:
                continue
            known.add(key)
            fresh.append({"ts": stamp, "source": name, "title": title,
                          "score": s, "bias": bias_of(bull, bear)})
    cut = (_now() - datetime.timedelta(hours=KEEP_HOURS)).isoformat()
    store["items"] = [it for it in (store.get("items") or []) if str(it.get("ts", "")) >= cut] + fresh
    store["known"] = list(known)[-800:]
    store["last_run"] = stamp
    _save_store(store)
    return fresh, errors


def recent(max_items=10, hours=DIGEST_HOURS, min_score=MIN_SCORE):
    """ข่าวเด่นล่าสุดในคลัง (อ่านอย่างเดียว ไม่ยิงเน็ต) — เรียงตามคะแนนผลกระทบ"""
    cut = (_now() - datetime.timedelta(hours=hours)).isoformat()
    items = [it for it in (_load_store().get("items") or [])
             if str(it.get("ts", "")) >= cut and int(it.get("score") or 0) >= min_score]
    items.sort(key=lambda x: -int(x.get("score") or 0))
    return items[:max_items]


# ────────────────────────────── วิเคราะห์เชิงวิจัย ──────────────────────────────

def themes(items):
    """จัดกลุ่มเป็นธีมมหภาค → {ธีม: {count, score, bull, bear, note}} เรียงตามคะแนนรวม"""
    out = {}
    for name, (kws, note) in THEMES.items():
        hit = [it for it in items if any(_hit(str(it.get("title", "")).lower(), k) for k in kws)]
        if not hit:
            continue
        out[name] = {"count": len(hit),
                     "score": sum(int(i.get("score") or 0) for i in hit),
                     "bull": sum(1 for i in hit if i.get("bias") == "BULL"),
                     "bear": sum(1 for i in hit if i.get("bias") == "BEAR"),
                     "note": note}
    return dict(sorted(out.items(), key=lambda kv: -kv[1]["score"]))


def bias_summary(items):
    """สรุปทิศทางสุทธิ (ถ่วงด้วยคะแนนผลกระทบ) + ระดับความระวัง"""
    bull = sum(int(i.get("score") or 0) for i in items if i.get("bias") == "BULL")
    bear = sum(int(i.get("score") or 0) for i in items if i.get("bias") == "BEAR")
    total = bull + bear
    if total == 0:
        return {"bias": "NEUTRAL", "bull": 0, "bear": 0, "ratio": 0.0, "caution": "ปกติ",
                "text": "ข่าวไม่มีทิศทางชัด"}
    ratio = (bull - bear) / float(total)
    if ratio >= 0.5:
        bias, caution = "BULL", "ปกติ (ข่าวหนุนทอง)"
    elif ratio <= -0.5:
        bias, caution = "BEAR", "ระวัง (ข่าวกดทอง)"
    else:
        bias, caution = "MIXED", "ปกติ (ข่าวสองทาง)"
    return {"bias": bias, "bull": bull, "bear": bear, "ratio": round(ratio, 2), "caution": caution,
            "text": f"ข่าวเอียง{'หนุน' if ratio > 0 else 'กด'}ทอง "
                    f"(สัดส่วน {ratio:+.2f} · คะแนนหนุน {bull} / กด {bear})"}


def _build_note(items, errors, hours=DIGEST_HOURS):
    stamp = _now().astimezone().strftime("%Y-%m-%d %H:%M")
    lines = [f"## {stamp} — งานวิจัยข่าวทองคำ (investing.com RSS · {hours} ชม.)", ""]
    if not items:
        lines.append("- ไม่มีข่าวกระทบทองในช่วงนี้ (หรือดึงข่าวไม่ได้)")
        if errors:
            lines.append(f"- หมายเหตุ: {'; '.join(errors)}")
        return "\n".join(lines)
    summ = bias_summary(items)
    lines.append(f"**สรุปทิศทาง:** {summ['text']} → ระดับความระวัง: **{summ['caution']}**")
    lines.append("")
    lines.append("**ธีมมหภาคที่เด่น (เรียงตามคะแนนผลกระทบ):**")
    for name, info in themes(items).items():
        lines.append(f"- **{name}** — {info['count']} ข่าว · คะแนนรวม {info['score']} "
                     f"(หนุน {info['bull']} / กด {info['bear']}) · {info['note']}")
    lines.append("")
    lines.append("**ข่าวเด่น:**")
    for it in items:
        mark = {"BULL": "🟢", "BEAR": "🔴"}.get(str(it.get("bias")), "⚪")
        lines.append(f"- {mark} [{it.get('score')}] ({it.get('source')}) {it.get('title')}")
    if errors:
        lines += ["", f"*หมายเหตุ: บางฟีดดึงไม่ได้ — {'; '.join(errors)}*"]
    return "\n".join(lines)


def _append_history(summary, themes_map, items, errors):
    """บันทึกงานวิจัยข่าวลงประวัติ (JSONL) — หนึ่งบรรทัด = หนึ่งรอบวิจัย"""
    rec = {
        "ts": _now().isoformat(timespec="seconds"),
        "summary": summary,
        "themes": themes_map,
        "items": [{"title": it.get("title"), "score": it.get("score"),
                   "bias": it.get("bias"), "source": it.get("source")} for it in items],
        "errors": errors or [],
    }
    try:
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with io.open(HISTORY, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def history(hours=24, since=None, until=None, max_records=40, max_items=8):
    """**ดึงประวัติงานวิจัยข่าวตามช่วงเวลาที่ต้องการ** (ให้บอทเลือกเองได้)

    hours        : ย้อนหลังกี่ชั่วโมงจากตอนนี้ (ใช้เมื่อไม่ระบุ since/until)
    since/until  : ระบุช่วงเวลาเอง (ISO string เช่น '2026-09-18T00:00:00+00:00')
    → คืน {'records': [...], 'text': 'ข้อความสรุปสำหรับป้อนบอท'}
    """
    now = _now()
    try:
        t_end = _parse_ts(until) or now
    except Exception:
        t_end = now
    t_start = _parse_ts(since) if since else (t_end - datetime.timedelta(hours=float(hours or 24)))
    if t_start is None:
        t_start = t_end - datetime.timedelta(hours=24)
    rows = []
    try:
        if os.path.exists(HISTORY):
            for line in io.open(HISTORY, encoding="utf-8"):
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                ts = _parse_ts(rec.get("ts"))
                if ts and t_start <= ts <= t_end:
                    rows.append(rec)
    except Exception:
        pass
    rows = rows[-int(max_records):]
    if not rows:
        return {"records": [], "text": "ประวัติงานวิจัยข่าว: ไม่มีข้อมูลในช่วง %s → %s"
                % (t_start.astimezone().strftime("%Y-%m-%d %H:%M"),
                   t_end.astimezone().strftime("%Y-%m-%d %H:%M"))}

    # รวมภาพรวมของทั้งช่วง (ธีมสะสม + ทิศทางล่าสุด)
    theme_total = {}
    for rec in rows:
        for name, info in (rec.get("themes") or {}).items():
            t = theme_total.setdefault(name, {"count": 0, "score": 0, "bull": 0, "bear": 0})
            t["count"] += int(info.get("count") or 0)
            t["score"] += int(info.get("score") or 0)
            t["bull"] += int(info.get("bull") or 0)
            t["bear"] += int(info.get("bear") or 0)
    last = rows[-1].get("summary") or {}
    lines = ["ประวัติงานวิจัยข่าวทองคำ — %s → %s (%d รอบวิจัย)"
             % (t_start.astimezone().strftime("%Y-%m-%d %H:%M"),
                t_end.astimezone().strftime("%Y-%m-%d %H:%M"), len(rows))]
    lines.append("  ทิศทางล่าสุด: %s → ระวัง: %s" % (last.get("text", "-"), last.get("caution", "-")))
    if theme_total:
        top = sorted(theme_total.items(), key=lambda kv: -kv[1]["score"])[:5]
        lines.append("  ธีมสะสมตลอดช่วง: " + " · ".join(
            f"{k}({v['count']} ข่าว/คะแนน {v['score']})" for k, v in top))
    # ข่าวเด่นสะสม (ไม่ซ้ำหัวข้อ)
    seen, picks = set(), []
    for rec in reversed(rows):
        for it in rec.get("items") or []:
            key = str(it.get("title"))[:80]
            if key in seen:
                continue
            seen.add(key)
            picks.append(it)
            if len(picks) >= max_items:
                break
        if len(picks) >= max_items:
            break
    if picks:
        lines.append("  ข่าวเด่นสะสม:")
        for it in picks:
            mark = {"BULL": "🟢", "BEAR": "🔴"}.get(str(it.get("bias")), "⚪")
            lines.append(f"    {mark} [{it.get('score')}] ({it.get('source')}) {it.get('title')}")
    return {"records": rows, "text": "\n".join(lines)}


def save_research(text, author="bot", headline=None):
    """**ให้บอท (สมอง LLM) บันทึกงานวิจัยข่าวของตัวเอง**

    เจ้าของระบบกำหนด (19 ก.ย. 2026): "ให้ตัวบอท (สมอง LLM) เป็นผู้วิจัยและบันทึกวิจัยเอง"
    → โมดูลนี้ทำหน้าที่แค่ 'เตรียมข้อมูลข่าว' ส่วนการวิเคราะห์/สรุป/บันทึก เป็นงานของบอท
    → ฟังก์ชันนี้คือช่องทางให้บอทเขียนผลวิจัยของตัวเองลงระบบ

    text     : เนื้อหางานวิจัยที่บอทเขียน (markdown)
    author   : ผู้วิจัย เช่น 'mode2' (งานวิจัย 10 นาทีโหมด 2) หรือ 'admin_bot'
    headline : หัวข้อสั้น (ไม่ใส่ก็ได้)
    → เขียน research/news-research-<วันที่>.md + บันทึกประวัติ (author = บอท)
    """
    stamp = _now().astimezone().strftime("%Y-%m-%d %H:%M")
    title = headline or f"งานวิจัยข่าวโดยบอท ({author})"
    block = f"### {stamp} — {title}\n\n{str(text).strip()}\n"
    written = []
    try:
        os.makedirs(RESEARCH, exist_ok=True)
        day = _now().astimezone().strftime("%Y-%m-%d")
        daily = os.path.join(RESEARCH, f"news-research-{day}.md")
        if not os.path.exists(daily):
            with io.open(daily, "w", encoding="utf-8") as fh:
                fh.write(f"# งานวิจัยข่าวทองคำ — {day}\n\n> ระบบเทรดทองคำอัตโนมัติ · "
                         f"ข้อมูลจาก `outputs/mt5_python_bridge/news_feed.py` · วิเคราะห์โดยบอท\n")
        with io.open(daily, "a", encoding="utf-8") as fh:
            fh.write("\n" + block)
        written.append(daily)
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\n" + block)
        written.append(LOG)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "written": written}
    # บันทึกประวัติ (ระบุว่าเป็นงานวิจัยที่ 'บอท' เขียน ไม่ใช่สคริปต์)
    try:
        items = recent(max_items=12, hours=DIGEST_HOURS)
        rec = {
            "ts": _now().isoformat(timespec="seconds"),
            "author": author,
            "headline": title,
            "research": str(text).strip()[:6000],
            "data_snapshot": {
                "summary": bias_summary(items),
                "themes": themes(items),
                "items": [{"title": it.get("title"), "score": it.get("score"),
                           "bias": it.get("bias"), "source": it.get("source")} for it in items],
            },
        }
        os.makedirs(os.path.dirname(HISTORY), exist_ok=True)
        with io.open(HISTORY, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return {"ok": True, "written": written, "author": author}


def _write_note(note):
    try:
        os.makedirs(RESEARCH, exist_ok=True)
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write("\n" + note + "\n")
        day = _now().astimezone().strftime("%Y-%m-%d")
        daily = os.path.join(RESEARCH, f"news-research-{day}.md")
        if not os.path.exists(daily):
            with io.open(daily, "w", encoding="utf-8") as fh:
                fh.write(f"# งานวิจัยข่าวทองคำ — {day}\n\n> ระบบเทรดทองคำอัตโนมัติ · เขียนอัตโนมัติโดย "
                         f"`outputs/mt5_python_bridge/news_feed.py`\n")
        with io.open(daily, "a", encoding="utf-8") as fh:
            fh.write("\n" + note + "\n")
    except Exception:
        pass


# ────────────────────────────── จุดเรียกใช้หลัก (ครบวงจร) ──────────────────────────────

def refresh(force=False, hours=DIGEST_HOURS, timeout=20):
    """**เรียกฟังก์ชันนี้ = ทำงานวิจัยข่าวครบวงจร**

    ดึงข่าว → ให้คะแนน → เก็บคลัง → วิเคราะห์ → เขียนไฟล์วิจัย
    เรียกบ่อยแค่ไหนก็ได้: จะดึงเน็ตจริงไม่ถี่กว่า REFRESH_MINUTES (ครั้งอื่นตอบทันทีจากคลัง)
    → คืน {'ok', 'skipped', 'new_items', 'items', 'note', 'errors'}
    """
    store = _load_store()
    last = _parse_ts(store.get("last_run"))
    if not force and last is not None:
        age = (_now() - last).total_seconds()
        if age < REFRESH_MINUTES * 60:
            items = recent(max_items=10, hours=hours)
            return {"ok": True, "skipped": True, "age_seconds": round(age, 1),
                    "new_items": 0, "items": items,
                    "note": _build_note(items, [], hours), "errors": []}
    fresh, errors = _fetch_new(timeout=timeout)
    items = recent(max_items=10, hours=hours)
    note = _build_note(items, errors, hours)
    _write_note(note)
    # ★ บันทึกเป็นประวัติงานวิจัย (ให้บอทดึงไปประมวลผลภายหลังได้)
    _append_history(bias_summary(items), themes(items), items, errors)
    return {"ok": True, "skipped": False, "new_items": len(fresh), "items": items,
            "note": note, "errors": errors}


def digest(max_items=12, hours=DIGEST_HOURS, timeout=20):
    """**ข้อมูลข่าวสำหรับป้อนบอท** (วัตถุดิบ + สถิติตั้งต้น — ไม่ใช่บทสรุปวิจัย)

    เจ้าของระบบกำหนด: บอท (สมอง LLM) เป็นผู้ 'วิจัยและสรุปเอง' — ฟังก์ชันนี้จึงให้
    ข้อมูลดิบ + สถิติเชิงกล (ธีม/สัดส่วน) เพื่อให้บอทใช้ประกอบการคิด แล้วบอทเขียน
    งานวิจัยของตัวเองผ่าน save_research()
    """
    state = refresh(hours=hours, timeout=timeout)
    items = state["items"][:max_items]
    if not items:
        line = f"ข่าว: ยังไม่มีข่าวกระทบทองในช่วง {hours} ชม. (หรือดึงข่าวไม่ได้)"
        return line + (f" | หมายเหตุ: {'; '.join(state['errors'])}" if state["errors"] else "")
    summ = bias_summary(items)
    lines = [f"ข่าวล่าสุดกระทบทองคำ (investing.com · {hours} ชม. · {summ['text']} · ระวัง: {summ['caution']})"]
    th = themes(items)
    if th:
        lines.append("  ธีมเด่น: " + " · ".join(f"{k}({v['count']})" for k, v in list(th.items())[:3]))
    for it in items:
        mark = {"BULL": "🟢", "BEAR": "🔴"}.get(str(it.get("bias")), "⚪")
        lines.append(f"  {mark} [{it.get('score')}] ({it.get('source')}) {it.get('title')}")
    if state["errors"]:
        lines.append(f"  (หมายเหตุ: บางฟีดดึงไม่ได้ — {'; '.join(state['errors'])})")
    return "\n".join(lines)


def note(hours=DIGEST_HOURS, timeout=20):
    """บันทึกวิจัยฉบับเต็ม (เรียกแล้วได้งานวิจัยข่าวด้วยในตัว)"""
    return refresh(hours=hours, timeout=timeout)["note"]


def run_once(hours=DIGEST_HOURS):
    """โหมดสคริปต์ cron — เทียบเท่า refresh(force=True) + คืนรายการข่าวใหม่"""
    store = _load_store()
    known_before = len(store.get("known") or [])
    state = refresh(force=True, hours=hours)
    after = len((_load_store().get("known") or []))
    return {"new_count": max(0, after - known_before), "items": state["items"],
            "note": state["note"], "errors": state["errors"]}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="งานวิจัยข่าวทองคำ (เรียกครั้งเดียวได้ครบวงจร)")
    ap.add_argument("--history", action="store_true", help="ดูประวัติงานวิจัยข่าว (ไม่ดึงข่าวใหม่)")
    ap.add_argument("--hours", type=float, default=24.0, help="ประวัติย้อนหลังกี่ชั่วโมง (ค่าเริ่มต้น 24)")
    ap.add_argument("--since", default=None, help="เริ่มช่วง (ISO) เช่น 2026-09-18T00:00:00+00:00")
    ap.add_argument("--until", default=None, help="สิ้นสุดช่วง (ISO)")
    ap.add_argument("--max-records", type=int, default=40, help="จำนวนรอบวิจัยสูงสุดที่จะดึง")
    ap.add_argument("--digest", action="store_true", help="ดูข้อมูลข่าวสำหรับบอท (ดึงข่าวใหม่ถ้าถึงรอบ)")
    ap.add_argument("--save-research", default=None,
                    help="ให้บอทบันทึกงานวิจัยของตัวเอง (ระบุชื่อไฟล์ .md หรือ - สำหรับ stdin)")
    ap.add_argument("--author", default="bot", help="ผู้วิจัย: mode2 | admin_bot | อื่น ๆ")
    a = ap.parse_args()

    if a.save_research is not None:
        if a.save_research == "-":
            text = sys.stdin.read()
        else:
            text = io.open(a.save_research, encoding="utf-8").read()
        res = save_research(text, author=a.author)
        print(("บันทึกงานวิจัยข่าวของบอทเรียบร้อย (%s) -> %s"
               % (a.author, ", ".join(res.get("written") or []))) if res.get("ok")
              else ("บันทึกไม่สำเร็จ: %s" % res.get("error")))
    elif a.history:
        print(history(hours=a.hours, since=a.since, until=a.until, max_records=a.max_records)["text"])
    elif a.digest:
        print(digest(hours=a.hours))
    else:
        result = run_once()
        print("📰 [News] งานวิจัยข่าวทองคำ — ข่าวใหม่ %d รายการ" % result["new_count"])
        print("")
        print(result["note"])
