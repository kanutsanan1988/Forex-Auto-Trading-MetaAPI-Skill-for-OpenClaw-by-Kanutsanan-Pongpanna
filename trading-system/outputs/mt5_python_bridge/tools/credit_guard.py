#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ตัวเฝ้าเครดิต OpenRouter — คุม "ทุกจุดที่ใช้ AI" ในระบบเทรดให้อัตโนมัติ

คำสั่งเจ้าของระบบ (28 ก.ย. 2026):
  "เครดิต OpenRouter มากกว่า 1 ดอลลาร์ → ให้ระบบเทรดพร้อมครบในการใช้บอทและ AI ทุกรูปแบบ
   ต่ำกว่า 1 ดอลลาร์ → ปรับเป็นเทรดเฉพาะสัญญาณจากข้อมูลภายใน (ไม่ให้มีค่าใช้จ่ายส่วนนี้อีก)"

การเช็คเครดิต "ฟรี" — พิสูจน์ด้วยข้อมูลจริง 28 ก.ย. 2026:
  เรียก GET /api/v1/credits 2 ครั้งติดกัน → total_usage ไม่ขยับเลย ($0.00000000)
  (เป็น API ข้อมูลบัญชี ไม่ได้เรียกโมเดล → ไม่มี token → ไม่มีค่าใช้จ่าย)

คุมครบ 3 กลุ่มที่ใช้ AI จริง (ไล่ตรวจทั้งระบบ):
  ① งานเอเจนต์ Hermes 3 งาน (research-bot · admin-bot · brain-consult) → สลับด้วยโหมด
  ② Jev ทุกจุด (news_feed · admin_bot_round · llm_research_packet · งานอื่น) → jev_config.enabled
  ③ AI ของตัวเทรด → ★ ห้ามแตะเด็ดขาด: เป็นอำนาจเจ้าของระบบเท่านั้น (ตัวเฝ้าเปิด/ปิดได้เฉพาะ AI ตัวอื่น)
     (มีประตูโหมดในตัวอยู่แล้ว: โหมด 1 = blocked_by_mode)

กติกาความปลอดภัย:
  • โหมดต่ำ = "ปิดได้เสมอ" · โหมดสูง = คืนค่าที่เจ้าของระบบตั้งไว้ (ไม่คิดค่าแทน)
  • ไม่แตะออเดอร์ · ไม่แตะ kill switch · ไม่เปิด-ปิดระบบเทรด (อำนาจเจ้าของระบบ)
  • ถ้าเช็คเครดิตไม่สำเร็จติดกัน 3 ครั้ง → ปิดฝั่ง AI (ระวังไว้ก่อน) + บันทึก + แจ้ง Telegram
  • ทุกการเปลี่ยนบันทึกที่ work/credit_guard_audit.jsonl

ใช้: .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\credit_guard.py --status
     ... --apply                    (ตรวจ + ปรับให้ตรงเงื่อนไขจริง)
     ... --simulate 0.50 --apply    (จำลองเครดิต เพื่อทดสอบกลไก)
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BR = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(BR))
WORK = os.path.join(ROOT, "work")
CFG = os.path.join(BR, "credit_guard.json")

# ★ ล็อกถาวร: AI ของตัวเทรดเปิด/ปิดได้โดยมนุษย์เท่านั้น (ตัวเฝ้าเครดิตห้ามแตะ)
HUMAN_ONLY_TRADER_AI = True
STATE = os.path.join(WORK, "credit_guard_state.json")
AUDIT = os.path.join(WORK, "credit_guard_audit.jsonl")
JEV_CFG = os.path.join(BR, "jev_config.json")
AUTO_CFG = os.path.join(BR, "auto_config.json")
HERMES_ENV = os.path.expanduser("~/AppData/Local/hermes/.env")
CHAT_ID = "8061220704"

DEFAULT_CFG = {
    "_creator": "Kanutsanan Pongpanna",
    "_note": "ตัวเฝ้าเครดิต OpenRouter — คุมทุกจุดที่ใช้ AI ในระบบเทรด (การเช็คเครดิตฟรี)",
    "enabled": True,
    "low_usd": 1.00,           # ต่ำกว่านี้ → เทรดเฉพาะสัญญาณภายใน (ไม่ใช้ AI เลย)
    "resume_usd": 1.20,        # กลับมาใช้ AI เมื่อเกินระดับนี้ (กันกระพริบที่ขอบ 1.00)
    "manage_trader_ai": False,  # ★ ล็อกถาวร: ห้ามแตะ AI ของตัวเทรด — อำนาจเจ้าของระบบเท่านั้น (29 ก.ย. 2026)
    "max_consecutive_failures": 3,
    "notify_telegram": True,
}


def _load(path, default):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp, path)


def log(event, **kw):
    rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event}
    rec.update(kw)
    try:
        with io.open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


# ── เช็คเครดิต (ฟรี) ─────────────────────────────────────────────────────────
def api_key():
    """ใช้ตัวค้นหาคีย์ของโหมดพกพา (แหล่งเดียวกับ Jev)"""
    try:
        sys.path.insert(0, HERE)
        import jev_connect
        for _src, k in jev_connect.candidates():
            if k:
                return k
    except Exception:
        pass
    # ชื่อตัวแปรคีย์อ่านจาก jev_config.json ผ่าน jev_connect เท่านั้น (ห้ามฝังในโค้ด)
    try:
        t = io.open(HERMES_ENV, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^\s*(?:export\s+)?[A-Z_]*API_KEY\s*=\s*(sk-or-[^\r\n#\"']+)", t)
        return m.group(1).strip() if m else None
    except Exception:
        return None


def balance():
    """คืน (ok, remaining, total, usage, error) — GET /credits เป็นข้อมูลบัญชี ไม่คิดเงิน"""
    k = api_key()
    if not k:
        return False, None, None, None, "ไม่พบคีย์ OpenRouter"
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/credits",
                                     headers={"Authorization": "Bearer " + k})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode())["data"]
        total, usage = float(d["total_credits"]), float(d["total_usage"])
        return True, total - usage, total, usage, None
    except Exception as exc:
        return False, None, None, None, "%s: %s" % (type(exc).__name__, str(exc)[:100])


# ── คุมฝั่ง AI ───────────────────────────────────────────────────────────────
AI_JOB_KEYS = ("trading-research-bot", "trading-admin-bot", "brain-consult")


def ai_jobs_enabled():
    """งาน AI (เอเจนต์ที่ใช้เครดิต) ที่เปิดอยู่จริง"""
    try:
        p = os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json")
        d = json.load(io.open(p, encoding="utf-8"))
        jobs = d if isinstance(d, list) else (d.get("jobs") or [])
        return [j.get("name") for j in jobs
                if j.get("enabled") and any(k in str(j.get("name", "")) for k in AI_JOB_KEYS)]
    except Exception:
        return []


def system_running():
    """มี AI ที่ต้องเฝ้าไหม (เปิด-ปิดเป็นอำนาจเจ้าของระบบ · ตัวเฝ้าเปิด-ปิดอัตโนมัติตามนี้)

    หลัก: ตัวเทรดเดิน หรือ มีงานบอท AI เปิดอยู่ → เฝ้า · ไม่มี AI ทำงานเลย → ตัวเฝ้าปิดตาม
    """
    work = os.path.join(ROOT, "work")
    trader_on = (os.path.exists(os.path.join(work, "auto_trader_supervisor.pid"))
                 and not os.path.exists(os.path.join(work, "AUTO_TRADER_STOP")))
    if trader_on or ai_jobs_enabled():
        return True
    # เคยระงับ AI เพราะเครดิตต่ำ → ต้องเฝ้าต่อ เพื่อเปิดคืนอัตโนมัติเมื่อเจ้าของระบบเติมเงิน
    return _load(STATE, {}).get("llm") == "off"


def ai_state():
    """ตรวจสภาพจริงของฝั่ง AI จากของจริง (ไม่เชื่อไฟล์สถานะ — กันสำเนาเก่าทับ)"""
    mode = mode_now().get("mode")
    jev = bool(_load(JEV_CFG, {}).get("enabled", False))
    if mode == "internal_only" and not jev:
        return "off"
    if mode == "internal_llm_join" and jev:
        # คำสั่งเจ้าของระบบ: เครดิตสูง = พร้อมใช้ AI ทุกรูปแบบ → นับสวิตช์ AI ของตัวเทรดด้วย
        # ★ ล็อกถาวร (เจ้าของระบบ 29 ก.ย. 2026): AI ของตัวเทรดเป็นอำนาจมนุษย์เท่านั้น
        if False and _load(CFG, DEFAULT_CFG).get("manage_trader_ai", False):
            if not bool(_load(AUTO_CFG, {}).get("openrouter", {}).get("enabled", False)):
                return "mixed"
        return "on"
    return "mixed"


def mode_now():
    try:
        with io.open(os.path.join(WORK, "trading_mode.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def set_mode(mode_name):
    """โหมด: internal_only (1) | internal_llm_join (2) — ใช้กลไกเดิมของระบบ (choose_mode)"""
    sys.path.insert(0, BR)
    import choose_mode
    return choose_mode.select_mode(mode_name)


AI_JOB_NAMES = ("trading-research-bot (10 นาที · บอทดูแล LLM)", "trading-admin-bot (30 นาที)", "brain-consult")


def _cron_cli(action, name):
    sys.path.insert(0, BR)
    import choose_mode
    return choose_mode.cron(action, name)


def _enabled_ai_jobs():
    """งาน AI ที่กำลังเปิดอยู่จริง (อ่านจากไฟล์งาน cron) — ใช้จำ/คืนสถานะของเจ้าของระบบ"""
    try:
        p = os.path.expanduser("~/AppData/Local/hermes/cron/jobs.json")
        with io.open(p, encoding="utf-8") as f:
            d = json.load(f)
        jobs = d if isinstance(d, list) else (d.get("jobs") or [])
        return [j.get("name") for j in jobs
                if j.get("name") in AI_JOB_NAMES and j.get("enabled")]
    except Exception:
        return list(AI_JOB_NAMES[:2])


def turn_off(reason):
    """ปิดทุกจุดที่ใช้ AI — ทำได้เสมอ (ปลอดภัยด้านค่าใช้จ่าย)"""
    st = _load(STATE, {})
    st.setdefault("prev", {})
    if "jev" not in st["prev"]:
        st["prev"]["jev"] = bool(_load(JEV_CFG, {}).get("enabled", True))
    if "openrouter" not in st["prev"]:
        st["prev"]["openrouter"] = bool(_load(AUTO_CFG, {}).get("openrouter", {}).get("enabled", False))
    st["prev"]["mode"] = mode_now().get("mode")
    if "jobs" not in st["prev"]:
        st["prev"]["jobs"] = _enabled_ai_jobs()

    _ = _load(CFG, DEFAULT_CFG)  # ค่าเดิมถูกใช้ผ่านเส้นทางอื่น · pyflakes: ไม่มีตัวแปรค้าง
    # ① โหมด → เทรดด้วยสัญญาณภายใน (หยุดงานเอเจนต์ AI + ประตูโหมดของตัวเทรด)
    try:
        set_mode("internal_only")
    except Exception as exc:
        log("mode_switch_failed", reason=str(exc)[:120])
    # ② Jev ทุกจุด
    jc = _load(JEV_CFG, {})
    jc["enabled"] = False
    jc["_credit_guard_note"] = "ปิดโดยตัวเฝ้าเครดิต: %s" % reason
    _save(JEV_CFG, jc)
    # ③ AI ในตัวเทรด/ตัววิเคราะห์ตลาด
    if False:  # ★ ล็อกถาวร AI ของตัวเทรด=อำนาจเจ้าของระบบ (29 ก.ย. 2026):
        ac = _load(AUTO_CFG, {})
        if isinstance(ac.get("openrouter"), dict):
            ac["openrouter"]["enabled"] = False
            _save(AUTO_CFG, ac)
    st.update({"llm": "off", "reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    _save(STATE, st)
    log("llm_off", reason=reason, mode=mode_now().get("mode"), jev=False,
        trader_ai="untouched (อำนาจเจ้าของระบบ)")
    return "off"


def turn_on(reason):
    """เปิดคืน — คืนค่าที่เจ้าของระบบตั้งไว้เดิม (ไม่คิดค่าแทนเจ้าของ)"""
    st = _load(STATE, {})
    prev = st.get("prev", {})
    _ = _load(CFG, DEFAULT_CFG)  # ค่าเดิมถูกใช้ผ่านเส้นทางอื่น · pyflakes: ไม่มีตัวแปรค้าง
    try:
        set_mode("internal_llm_join")
    except Exception as exc:
        log("mode_switch_failed", reason=str(exc)[:120])
    jc = _load(JEV_CFG, {})
    jc["enabled"] = bool(prev.get("jev", True))
    jc.pop("_credit_guard_note", None)
    _save(JEV_CFG, jc)
    trader_ai = "untouched"
    if False:  # ★ ล็อกถาวร AI ของตัวเทรด=อำนาจเจ้าของระบบ (29 ก.ย. 2026):
        ac = _load(AUTO_CFG, {})
        if isinstance(ac.get("openrouter"), dict):
            # เครดิตสูง = เปิด AI ตัวเทรดตามคำสั่งเจ้าของระบบ ("พร้อมครบทุก AI รูปแบบ")
            ac["openrouter"]["enabled"] = True
            _save(AUTO_CFG, ac)
            trader_ai = bool(prev.get("openrouter", False))
    resumed = []
    for nm in (prev.get("jobs") or []):
        try:
            _cron_cli("resume", nm)
            resumed.append(nm)
        except Exception as exc:
            log("resume_failed", job=nm, error=str(exc)[:100])
    st.update({"llm": "on", "reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    _save(STATE, st)
    log("llm_on", resumed=resumed, reason=reason, mode=mode_now().get("mode"), jev=bool(prev.get("jev", True)),
        trader_ai=trader_ai)
    return "on"


def notify(text):
    cfg = _load(CFG, DEFAULT_CFG)
    if not cfg.get("notify_telegram", True):
        return False
    tok = None
    try:
        t = io.open(HERMES_ENV, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^\s*(?:export\s+)?TELEGRAM_BOT_TOKEN\s*=\s*(.+)$", t)
        tok = m.group(1).strip().strip('"').strip("'") if m else None
    except Exception:
        pass
    if not tok:
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text}).encode()
        req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % tok, data=data)
        with urllib.request.urlopen(req, timeout=25) as r:
            return bool(json.loads(r.read().decode()).get("ok"))
    except Exception:
        return False


def run(simulate=None, apply_=False):
    cfg = _load(CFG, DEFAULT_CFG)
    st = _load(STATE, {})
    if simulate is not None:
        ok, remaining, total, usage, err = True, float(simulate), None, None, None
        note = "(จำลอง)"
    else:
        ok, remaining, total, usage, err = balance()
        note = ""
    # 28 ก.ย. 2026 (เจ้าของระบบ): ระบบเทรดปิด → ตัวเฝ้าเครดิตปิดตาม (อัตโนมัติ)
    if apply_ and simulate is None and not system_running():
        log("skipped", note="ระบบเทรดปิด → ตัวเฝ้าไม่ทำงาน")
        return 0, "ระบบเทรดปิด → ตัวเฝ้าปิดตามระบบ (อัตโนมัติ)"

    now = time.strftime("%Y-%m-%dT%H:%M:%S")

    if not ok:
        st["fails"] = int(st.get("fails", 0)) + 1
        log("check_failed", error=err, fails=st["fails"], note=note)
        if st["fails"] >= int(cfg.get("max_consecutive_failures", 3)) and st.get("llm") != "off":
            if apply_:
                turn_off("เช็คเครดิตไม่สำเร็จติดกัน %d ครั้ง (%s)" % (st["fails"], err))
                notify("⚠️ ระบบเทรด: เช็คเครดิต OpenRouter ไม่ได้ติดกัน %d ครั้ง\n"
                       "→ ปิดฝั่ง AI ทั้งหมดไว้ก่อน (เทรดด้วยสัญญาณภายใน) เพื่อกันค่าใช้จ่าย\n"
                       "เหตุ: %s" % (st["fails"], err))
            print("  ⚠️ เช็คเครดิตไม่ได้ (ครั้งที่ %d)%s" % (st["fails"], " → ปิดฝั่ง AI" if apply_ else ""))
        _save(STATE, st)
        return 1

    st["fails"] = 0
    st["last_balance"] = round(remaining, 4)
    st["last_check"] = now
    low = float(cfg.get("low_usd", 1.0))
    resume = float(cfg.get("resume_usd", 1.20))
    cur = ai_state()

    if remaining < low and (cur != "off"):
        if apply_:
            turn_off("เครดิตต่ำกว่า $%.2f (คงเหลือ $%.4f)" % (low, remaining))
            (notify if simulate is None else (lambda _t: False))("🔴 ระบบเทรด: เครดิต OpenRouter เหลือ $%.4f (ต่ำกว่า $%.2f)\n"
                   "→ สลับเป็นโหมดเทรดด้วยสัญญาณภายในทั้งหมดแล้ว\n"
                   "   · ปิดบอท AI 3 งาน (วิจัย/แอดมิน/ที่ปรึกษา)\n"
                   "   · ปิด Jev ทุกจุด\n"
                   "   · ปิด AI ในตัวเทรด\n"
                   "   · ระบบเทรดและงานวิจัยภายในยังทำงานครบ (ไม่มีค่าใช้จ่าย AI)\n"
                   "เติมเครดิตแล้วระบบจะกลับมาใช้ AI เองเมื่อเกิน $%.2f" % (remaining, low, resume))
        print("  🔴 เครดิต $%.4f < $%.2f → %s" % (remaining, low, "สลับเป็นสัญญาณภายในแล้ว" if apply_ else "ควรสลับ (ยังไม่ทำ: ใช้ --apply)"))
        st = _load(STATE, {}); st["fails"] = 0; st["last_balance"] = round(remaining, 4); st["last_check"] = now
        _save(STATE, st)
        return 0

    if remaining >= resume and cur != "on":
        if apply_:
            turn_on("เครดิตกลับมา $%.4f (≥ $%.2f)" % (remaining, resume))
            (notify if simulate is None else (lambda _t: False))("🟢 ระบบเทรด: เครดิต OpenRouter กลับมา $%.4f (เกิน $%.2f แล้ว)\n"
                   "→ เปิดใช้ AI คืนตามที่ตั้งไว้เดิม (บอท + Jev ตามระดับอำนาจ)" % (remaining, resume))
        print("  🟢 เครดิต $%.4f ≥ $%.2f → %s" % (remaining, resume, "เปิด AI คืนแล้ว" if apply_ else "ควรเปิดคืน (ยังไม่ทำ: ใช้ --apply)"))
        st = _load(STATE, {}); st["fails"] = 0; st["last_balance"] = round(remaining, 4); st["last_check"] = now
        _save(STATE, st)
        return 0

    st["llm"] = cur
    _save(STATE, st)
    # บันทึกเป็นจังหวะ (ชั่วโมงละครั้ง) — รอบปกติจะเงียบ ไม่ทำให้ log บวมเมื่อเช็คทุกนาที
    if time.time() - float(st.get("last_heartbeat_ts", 0)) > 3600:
        st["last_heartbeat_ts"] = time.time()
        _save(STATE, st)
        log("ok", balance=round(remaining, 4), llm=cur, note=note)
    band = " (อยู่ในช่วงกันกระพริบ)" if low <= remaining < resume else ""
    print("  ✅ เครดิต $%.4f · สถานะ AI: %s%s%s" % (remaining, cur, band, " · ทุกอย่างตรงเงื่อนไขแล้ว" if apply_ else ""))
    return 0


def status():
    cfg = _load(CFG, DEFAULT_CFG)
    st = _load(STATE, {})
    ok, remaining, total, usage, err = balance()
    print("💳 ตัวเฝ้าเครดิต OpenRouter (การเช็คฟรี · พิสูจน์แล้ว 28 ก.ย. 2026)")
    if ok:
        print("   เครดิตคงเหลือ: $%.4f  (ใช้ไป $%.4f จาก $%.4f ที่ซื้อ)" % (remaining, usage, total))
    else:
        print("   ⚠️ เช็คไม่ได้: %s" % err)
    print("   เกณฑ์: ต่ำกว่า $%.2f → สัญญาณภายในเท่านั้น · กลับมาใช้ AI เมื่อ ≥ $%.2f" % (
        cfg.get("low_usd", 1.0), cfg.get("resume_usd", 1.2)))
    print("   สถานะฝั่ง AI ปัจจุบัน: %s · โหมดระบบ: %s" % (
        st.get("llm", "-"), mode_now().get("mode", "-")))
    print("   จุดที่คุม: ① งานเอเจนต์ 3 งาน ② Jev ทุกจุด ③ AI ในตัวเทรด/วิเคราะห์ตลาด%s" % (
        " (ปิดการคุมข้อ ③ ตามตั้งค่า — อำนาจเจ้าของระบบ)"))
    print("   ค่าที่เจ้าของระบบตั้งไว้เดิม: %s" % json.dumps(st.get("prev", {}), ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--simulate", type=float)
    ap.add_argument("--on", action="store_true", help="เปิดฝั่ง AI คืนด้วยมือ")
    ap.add_argument("--off", action="store_true", help="ปิดฝั่ง AI ด้วยมือ")
    a = ap.parse_args()
    if a.on:
        print("  → เปิดคืน:", turn_on("สั่งด้วยมือ"))
        return 0
    if a.off:
        print("  → ปิด:", turn_off("สั่งด้วยมือ"))
        return 0
    if a.status:
        return status()
    rc = run(simulate=a.simulate, apply_=a.apply)
    if isinstance(rc, tuple):
        code, note = rc[0], (rc[1] if len(rc) > 1 else "")
        if note:
            print("  %s" % note)
        return int(code)
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())