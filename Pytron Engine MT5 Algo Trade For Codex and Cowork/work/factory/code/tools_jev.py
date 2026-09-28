#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""Jev Decision Engine — โมเดลตัดสินใจแบบพิมพ์ (TypeSafe System One) สำหรับระบบเทรดทองคำ

เจ้าของระบบกำหนด (23 ก.ย. 2026):
  "ส่วนไหนที่สามารถใช้ jev ai ช่วยงานได้ก็ใช้ได้นะครับ ดำเนินการตั้งค่าได้เลยครับ"
  "ใช้คีย์ open router ตัวเดียวกันกับที่คุณใช้อยู่"

═══════════════════════════════════════════════════════════════════════════
Jev คืออะไร (สรุปจากการศึกษาจริง — docs.typesafe.ai; OpenRouter เป็น adapter ตัวอย่าง)
═══════════════════════════════════════════════════════════════════════════
• Jev ≠ โมเดลสร้างข้อความ และ ≠ agent — มันคือ **โมเดลตัดสินใจแบบมีโครงสร้าง** (System One)
  ส่ง `state` (ข้อความ/ออบเจ็กต์/อาร์เรย์) + ชุด `questions` แบบมีชนิด → คืน `answers`
  เป็น **ความน่าจะเป็นที่สอบเทียบแล้ว** ⇒ โค้ดเราคุม workflow เอง ไม่ต้องแกะข้อความ
• คำถาม 3 ชนิด:
    noul   = ใช่/ไม่ใช่      → noul: 0..1            (ไม่มีความน่าจะเป็นรายตัวเลือก)
    choice = เลือกจากตัวเลือกที่เรากำหนด → choice + probabilities + confidence (0..1)
    score  = ให้คะแนนตามระดับที่เรากำหนด   → score (ถ่วงน้ำหนัก) + legend + probabilities + confidence
• เร็ว (~0.1-0.3 วิ) · ถูก ($0.042/ล้านโทเคนขาเข้า · ขาออกฟรี) · context 32K
• random คำถามในคำขอเดียวกันทำงานขนานกัน → ถามหลายข้อพร้อมกันคุ้มที่สุด
• ออกแบบให้: งานที่ตัดสินได้ด้วยโค้ด = ทำในโค้ด · ให้ Jev เฉพาะ "ดุลยพินิจเชิงสามัญสำนึก"
  กับข้อมูลไม่มีโครงสร้าง · แล้วรวมผลในโค้ด (composite) · และใช้ `confidence` เพื่อ "ไม่เดา"

═══════════════════════════════════════════════════════════════════════════
ใช้ในระบบนี้ตรงไหน (บอททั้ง 2 ตัว + สคริปต์)
═══════════════════════════════════════════════════════════════════════════
  news        → ให้คะแนนข่าวแบบสอบเทียบ (แทน/เสริมการับคีย์เวิร์ด) — โหมด 2 + แอดมินบอท
  rec-check   → ตรวจคำแนะนำของบอทก่อนใช้จริง: ตรงหลักฐานไหม · เป็นการไล่ราคาไหม · เลขตรงไหม
  admin-safety→ ตรวจการปรับค่าของแอดมินบอทก่อนบันทึก: อยู่ในเจตนาระบบไหม · เสี่ยงขึ้นไหม
  regime      → จัดภาวะตลาด (trend/range/choppy) + ความแข็งของแนวโน้ม

**หลักการ:** Jev เป็น "ผู้ช่วยตัดสินใจ" ไม่ใช่ dependency บังคับ — OpenRouter เป็นวิธีเชื่อมต่อของ source นี้
ผู้ใช้สำเนาสามารถแทน adapter หรือปิด Jev ได้ · ถ้าเรียกไม่สำเร็จ = คืน ok:false แล้วระบบเดิมทำงานต่อ
(fail-safe ทุกทาง)

CLI:
  python tools/jev.py --probe                          # ทดสอบการเชื่อมต่อ
  python tools/jev.py --selftest                        # ทดสอบทุกพรีเซ็ต
  python tools/jev.py --preset news --state s.json      # ใช้พรีเซ็ตกับข้อมูลจริง
  python tools/jev.py --questions q.json --state s.json # คำถามกำหนดเอง
  python tools/jev.py --show-preset news                # ดูคำถามของพรีเซ็ต
"""
import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BRIDGE = os.path.dirname(HERE)                     # outputs/mt5_python_bridge
ROOT = os.path.dirname(os.path.dirname(BRIDGE))    # โฟลเดอร์ระบบเทรดทองคำ (แก้ 23 ก.ย. 2026: เดิมขึ้นมาไม่ครบชั้น)
if BRIDGE not in sys.path:
    sys.path.insert(0, BRIDGE)
from runtime_support import require_ai_mode
WORK = os.path.join(ROOT, "work")
AUDIT = os.path.join(WORK, "jev_audit.jsonl")
CFG = os.path.join(BRIDGE, "jev_config.json")

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "~typesafe/jev-latest"

# AI ที่อยู่ในวงจรเทรดใช้ได้เฉพาะโหมด 2; Hermes กลางเป็นผู้ช่วยทั่วไปแยกจากการตัดสินใจเทรด
ALLOWED_CONTEXTS = ("mode2", "admin", "hermes", "hermes-trade")
#   mode2 / admin / hermes-trade = AI ที่ร่วมกับระบบเทรด (ต้องผ่าน require_ai_mode)
#   hermes        = ระบบกลางของ Hermes (ไม่สั่ง/ตัดสินใจออเดอร์)
TRADING_CONTEXTS = ("mode2", "admin", "hermes-trade")
CONTEXT_MANUAL = "manual"          # CLI/ทดสอบด้วยมือ (ไม่ใช่การทำงานประจำของระบบ)
CONTEXT_LABEL = {"hermes": "ระบบกลางของ Hermes (Jev = ผู้ช่วย + ผู้ตัดสินใจ)", "hermes-trade": "สมองหลักในระบบเทรด (Jev = ผู้ช่วย + บันไดอำนาจ)", "mode2": "บอทโหมด 2 (วิจัย 10 นาที)", "admin": "แอดมินบอท (รอบ 30 นาที)",
                 "manual": "ทดสอบด้วยมือ (CLI)"}
INPUT_PRICE_PER_M = 0.042                          # USD / 1M input tokens (ราคา ณ 23 ก.ย. 2026)

DEFAULT_CONFIG = {
    "enabled": True,
    "model": DEFAULT_MODEL,
    "timeout_seconds": 60,
    "max_attempts": 3,
    "use_in_news": True,
    "use_in_admin": True,
    "use_in_rec_check": True,
    "audit": True,
}

# ── ที่เก็บคีย์: ใช้คีย์ OpenRouter ตัวเดียวกับที่ Hermes (สมองบอท) ใช้ ─────────
KEY_SOURCES = [
    ("env", None),
    ("project .env", os.path.join(ROOT, ".env")),
    ("hermes .env (คีย์ที่สมองใช้)", os.path.expanduser("~/AppData/Local/hermes/.env")),
]


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(CFG):
            with io.open(CFG, encoding="utf-8") as source:
                cfg.update(json.load(source))
    except Exception:
        pass
    if os.environ.get("JEV_ENABLED", "").strip() in ("0", "false", "no"):
        cfg["enabled"] = False
    return cfg


def _read_key_from(path):
    """อ่านคีย์จากไฟล์ .env — ใช้ 'ชื่อตัวแปร' จาก jev_config.json (ห้ามมีชื่อ credential ในโค้ด)"""
    names = tuple(load_config().get("key_env_names") or [])
    if not names:
        return None
    try:
        for line in io.open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            name, val = line.split("=", 1)
            if name.strip() in names:
                val = val.strip().strip('"').strip("'")
                if val:
                    return val
    except Exception:
        pass
    return None


def _env_names():
    """ชื่อตัวแปรสภาพแวดล้อมที่ Jev รับ — อ่านจาก jev_config.json (ไม่มีชื่อ credential ในโค้ด)"""
    return tuple(load_config().get("key_env_names") or [])


_AUTO = {}          # ★ แคชผลการเชื่อมต่ออัตโนมัติต่อโปรเซส (โหมดพกพา)


def _auto_key():
    """เครื่องใหม่: ค้นหาทุกวิธีผ่าน jev_connect (ทดสอบจริงครั้งเดียวต่อโปรเซส)"""
    if "key" in _AUTO:
        return _AUTO["key"]
    try:
        import jev_connect
        res = jev_connect.resolve(try_probe=True, verbose=False)
        _AUTO["key"] = res.get("key") if res.get("ok") else None
        _AUTO["source"] = res.get("source")
        _AUTO["note"] = res.get("note")
        jev_connect.log("auto_use", ok=bool(res.get("ok")), source=res.get("source"), note=res.get("note"))
    except Exception as exc:
        _AUTO["key"] = None
        _AUTO["note"] = str(exc)[:80]
    return _AUTO["key"]


def api_key():
    """คีย์: ตัวแปรสภาพแวดล้อม → .env โปรเจกต์ → .env ของ Hermes → ★ เชื่อมต่ออัตโนมัติ (เครื่องใหม่)"""
    for nm in _env_names():
        v = os.environ.get(nm, "").strip()
        if v:
            return v
    for label, path in KEY_SOURCES[1:]:
        if path and os.path.exists(path):
            k = _read_key_from(path)
            if k:
                return k
    # ★ 23 ก.ย. 2026 (โหมดพกพา): เครื่องอื่นอาจเก็บคีย์ที่ทางอื่น → ให้ตัวเชื่อมต่ออัตโนมัติค้นหาวิธีทั้งหมด
    #   ถ้าหาไม่ได้จริง → คืน None แล้วผู้เรียกจะข้าม Jev ไปใช้กฎตัวเลขเดิม (ระบบไม่หยุด)
    return _auto_key()


def key_source_label():
    for nm in _env_names():
        if os.environ.get(nm, "").strip():
            return "env (ตัวแปรสภาพแวดล้อมของเครื่อง)"
    for label, path in KEY_SOURCES[1:]:
        if path and os.path.exists(path) and _read_key_from(path):
            return label
    if _AUTO.get("key"):
        return "เชื่อมต่ออัตโนมัติ (portable): %s" % (_AUTO.get("source") or "-")
    if _AUTO.get("note"):
        return "ไม่พบ (ลองอัตโนมัติแล้ว: %s)" % _AUTO.get("note")
    return "ไม่พบ"


# ── ตัวสร้างคำถาม (typed questions) ───────────────────────────────────────────
def noul(instructions, criteria=None):
    """คำถามใช่/ไม่ใช่ → คืนความน่าจะเป็น 0(ไม่)..1(ใช่)"""
    q = {"type": "noul", "instructions": instructions}
    if criteria:
        q["criteria"] = criteria
    return q


def choice(instructions, criteria):
    """เลือกจากตัวเลือกที่กำหนด → choice + probabilities + confidence"""
    return {"type": "choice", "instructions": instructions,
            "criteria": {k: v for k, v in criteria.items()}}


def score(instructions, criteria):
    """ให้คะแนนตามระดับที่เรียงไว้ (อย่างน้อย 2 ระดับ) → score + legend + confidence"""
    return {"type": "score", "instructions": instructions, "criteria": list(criteria)}


# ── พรีเซ็ตคำถามประจำโดเมน (งานของบอท 2 ตัว) ─────────────────────────────────
PRESETS = {}


def _preset(name, doc, build):
    PRESETS[name] = {"doc": doc, "build": build}


_preset("news", "ประเมินข่าว: ทิศทางผลต่อทอง · ความหนักแน่น · ถูก price-in แล้วหรือยัง", lambda s: {
    "news_net_up": noul(
        {"question": "ผลสุทธิของ `news` จะดันราคาทองคำ **ขึ้น** ในช่วง 12-24 ชั่วโมงข้างหน้าใช่หรือไม่",
         "inspect": "`news`",
         "focus": "ชั่งเฉพาะข่าวที่ให้มาเท่านั้น ห้ามใช้ความรู้สึกหรือข่าวที่ไม่ได้ให้",
         "compare": ["`news`", "`gold`"]},
        {"true": {"what": "แรงกดดันสุทธิเป็นบวกต่อราคาทอง", "examples": ["Fed ส่งสัญญาณผ่อนคลาย", "ความเสี่ยงภูมิรัฐศาสตร์เพิ่ม", "ดอลลาร์อ่อน"]},
         "false": {"what": "แรงกดดันสุทธิเป็นลบหรือเป็นกลาง", "examples": ["bond yield สูงขึ้น", "Fed เข้มงวดขึ้น", "ข่าวไม่มีนัยต่อทอง"]}}),
    "pressure": choice(
        {"question": "`news` กดดันราคาทองไปทางไหน", "inspect": "`news`"},
        {"up": "หนุนทองขึ้น", "down": "กดทองลง", "neutral": "สองทาง/ไม่มีนัยชัด"}),
    "conviction": score(
        {"question": "ความหนักแน่นของสัญญาณจาก `news` อยู่ระดับใด",
         "focus": "ประเมินจากความชัดและความแรงของข่าว ไม่ใช่จำนวนข่าว"},
        ["ไม่มีนัย (noise)", "เบา", "ปานกลาง", "หนัก", "หนักมาก (ชัดและแรง)"]),
    "already_priced": noul(
        {"question": "ผลกระทบของ `news` ถูกสะท้อนในราคา `gold.price` ไปมากแล้วใช่หรือไม่",
         "compare": ["`news`", "`gold`"]},
        {"true": "ราคาขยับตามข่าวไปแล้วเกือบหมด", "false": "ราคายังไม่ขยับตามข่าวนี้"}),
    "catalyst_today": noul(
        {"question": "`news` มีเหตุการณ์กำหนดเวลา/ผลกระทบสูงต่อทองใน 12 ชั่วโมงข้างหน้าใช่หรือไม่",
         "inspect": "`news`"},
        {"true": "มีตัวขับชัดเจนที่รู้เวลา", "false": "ไม่มีกำหนดการชัดในกรอบนี้"}),
    "dominant_theme": choice(
        {"question": "ธีมหลักที่ครอบ `news` ชุดนี้คืออะไร", "inspect": "`news`"},
        {"fed_rates": "นโยบาย Fed / ดอกเบี้ย / เงินเฟ้อ", "usd": "ค่าเงินดอลลาร์ / ดัชนีดอลลาร์",
         "geopolitics": "ภูมิรัฐศาสตร์ / สงคราม / วิกฤต", "flows": "ความต้องการ/ETFs/ธนาคารกลาง",
         "other": "อื่น ๆ หรือปะปนกันจนไม่ชัด"}),
})


_preset("rec-check", "ตรวจคำแนะนำของบอทก่อนใช้จริง (ตรงหลักฐาน · ไม่ไล่ราคา · เลขตรง)", lambda s: {
    "follows_evidence": noul(
        {"question": "`proposal` สอดคล้องกับตัวเลขใน `evidence` จริงหรือไม่",
         "compare": ["`proposal`", "`evidence`"],
         "focus": "ทิศทาง/ขนาดของข้อเสนอต้องตามมาจากตัวเลข ไม่ใช่ความเห็นลอย ๆ"},
        {"true": {"what": "ข้อเสนอเป็นผลที่ตามมาจากหลักฐานที่ให้มา"},
         "false": {"what": "ข้อเสนอขัดหรือไม่เกี่ยวกับหลักฐาน", "not_for": "ข้อเสนอที่หลักฐานสนับสนุนบางส่วน"}}),
    "is_chasing": noul(
        {"question": "การเข้าออเดอร์ตาม `proposal` เป็นการ **ไล่ราคาที่วิ่งไปไกลแล้ว** ใช่หรือไม่",
         "compare": ["`proposal`", "`market`"],
         "focus": "ดูว่าราคาวิ่งไปแล้วมากเทียบ ATR/กรอบล่าสุดหรือยัง"},
        {"true": {"what": "เข้าไล่หลังราคาวิ่งไปแล้วมาก (เสี่ยงยอดกลับ)", "examples": ["ราคาวิ่งเกิน ~1 ATR ในทิศเดียวกันก่อนเข้า"]},
         "false": {"what": "เข้าที่จุดที่ยังไม่ยืด (ไม่ใช่การไล่ราคา)"}}),
    "text_matches_numbers": noul(
        {"question": "ตัวเลขทุกตัวที่อ้างใน `proposal.reason` ปรากฏจริงใน `evidence` ใช่หรือไม่",
         "compare": ["`proposal`", "`evidence`"]},
        {"true": {"what": "เลขที่อ้างตรงกับหลักฐานทั้งหมด"},
         "false": {"what": "มีเลขที่อ้างแต่ไม่มีในหลักฐาน หรือค่าต่างกัน", "not_for": "การปัดเศษหรือการเทียบสัดส่วนที่ถูกต้อง"}}),
    "biggest_risk": choice(
        {"question": "ความเสี่ยงหลักที่สุดของ `proposal` ในตอนนี้คืออะไร",
         "compare": ["`proposal`", "`market`", "`news_digest`"]},
        {"reversal": "ยอดกลับของราคา", "news_shock": "ข่าวกระแทกสวนทาง", "volatility": "ผันผวนกว้างผิดปกติ",
         "liquidity": "สภาพคล่อง/สเปรดกว้าง", "overfit": "ตั้งค่าจากข้อมูลอดีตมากเกิน (overfit)"}),
    "robustness": score(
        {"question": "`proposal` ทนทานต่อความคลาดเคลื่อนแค่ไหน (ไม่ใช่แค่ผ่านอดีต)",
         "compare": ["`proposal`", "`evidence`"]},
        ["เปราะบางมาก", "เปราะบาง", "พอใช้", "ทนทาน", "ทนทานสูง"]),
})


_preset("admin-safety", "ตรวจการปรับค่าของแอดมินบอทก่อนบันทึก (เจตนาระบบ · ความเสี่ยง · ข่าว)", lambda s: {
    "within_intent": noul(
        {"question": "การเปลี่ยน `proposal` ยังอยู่ใน **เจตนาของระบบ** (net เป็นบวก · ความถี่พอเหมาะ · ไม่เพิ่มความเสี่ยงแบบทบต้น) ใช่หรือไม่",
         "compare": ["`proposal`", "`envelope`", "`performance`"]},
        {"true": {"what": "ยังอยู่ในทิศทางที่ระบบออกแบบไว้"},
         "false": {"what": "ออกนอกเจตนา หรือไปเพิ่มความเสี่ยงแบบทบต้น", "examples": ["เพิ่มขนาดเมื่อขาดทุน", "ถี่จนค่าธรรมเนียมกินกำไร"]}}),
    "raises_drawdown_risk": noul(
        {"question": "การเปลี่ยนนี้ทำให้ **ความเสี่ยงขาดทุนต่อเนื่องเพิ่มขึ้น** ใช่หรือไม่",
         "compare": ["`proposal`", "`performance`"]},
        {"true": {"what": "มีโอกาสทำให้ drawdown ลึกขึ้น", "examples": ["คลายตัวกรองที่มีผลจริง", "เพิ่มความถี่โดยที่ net/trade ยังลบ"]},
         "false": {"what": "ไม่เพิ่มความเสี่ยงการขาดทุนต่อเนื่อง"}}),
    "driven_by_noise": noul(
        {"question": "การเปลี่ยนนี้มาจาก **สัญญาณรบกวนระยะสั้น** มากกว่ารูปแบบที่ยั่งยืน ใช่หรือไม่",
         "compare": ["`proposal`", "`performance`"]},
        {"true": "ได้แรงจูงใจจากผลไม่กี่ไม้/ไม่กี่วัน", "false": "ได้แรงจูงใจจากรูปแบบที่เห็นซ้ำในหลายช่วง"}),
    "conflicts_with_news": noul(
        {"question": "การเปลี่ยนนี้สวนทางกับข่าวล่าสุดที่มีนัยต่อทอง ใช่หรือไม่",
         "compare": ["`proposal`", "`news_digest`"]},
        {"true": "สวนทางข่าวชัดเจน", "false": "สอดคล้องหรือเป็นกลางต่อข่าว"}),
    "risk_level": score(
        {"question": "ระดับความเสี่ยงของการเปลี่ยนนี้เมื่อเทียบกับค่าปัจจุบัน",
         "compare": ["`proposal`", "`envelope`"]},
        ["ต่ำมาก (แทบไม่มีผล)", "ต่ำ", "ปานกลาง", "สูง", "สูงมาก (ควรให้มนุษย์ยืนยัน)"]),
    "next_lever": choice(
        {"question": "ถ้าจะขยับต่อ ควรดูที่ 'ค่า' ตัวไหนก่อน",
         "compare": ["`proposal`", "`performance`", "`candidates`"]},
        {"__from_state__": None}),   # เติมจาก state['candidates'] ถ้ามี
})


_preset("internal", "ประเมิน 'ข้อมูลสัญญาณภายใน' (net · ความถี่ · กลไก · โซนกำไร) — คู่กับข่าวภายนอก", lambda s: {
    "in_profit_zone": noul(
        {"question": "ข้อมูลสัญญาณภายในชี้ว่า ระบบกำลังอยู่ใน **โซนทำกำไร** (net เฉลี่ยต่อไม้เป็นบวก) ใช่หรือไม่",
         "compare": ["`performance`", "`equity`"],
         "focus": "ดู net เฉลี่ยต่อไม้และระยะห่างจากจุดสูงสุด (HWM) ไม่ใช่ win rate อย่างเดียว"},
        {"true": {"what": "net เฉลี่ยต่อไม้เป็นบวกชัด", "examples": ["net/trade > 0 ต่อเนื่อง", "ระยะต่ำกว่า HWM แคบ"]},
         "false": {"what": "net เฉลี่ยต่อไม้เป็นลบหรือแกว่งรอบศูนย์", "examples": ["net/trade < 0", "ห่าง HWM กว้างขึ้น"]}}),
    "frequency_ok": noul(
        {"question": "ความถี่การเทรดตอนนี้ **เหมาะสมกับโซนกำไร** ใช่หรือไม่ (ไม่ถี่จนค่าธรรมเนียมกินกำไร)",
         "compare": ["`performance`", "`settings`"]},
        {"true": "ความถี่อยู่ในกรอบที่ net ยังเป็นบวก", "false": "ถี่เกินไปจน net/trade ติดลบ หรือเงียบจนไม่ได้เก็บโอกาส"}),
    "edge_durable": noul(
        {"question": "ขอบได้เปรียบที่เห็นเป็น **รูปแบบที่ยั่งยืน** มากกว่าความผันผวนชั่วคราว ใช่หรือไม่",
         "compare": ["`performance`", "`history`"],
         "focus": "ดูว่าตัวเลขดี/แย่ซ้ำในหลายช่วงหรือไม่"},
        {"true": "เห็นรูปแบบซ้ำในหลายช่วงเวลา", "false": "มาจากผลไม้ไม่กี่ไม้/ไม่กี่วัน"}),
    "main_leak": choice(
        {"question": "ตัวที่ **รั่วกำไร** มากที่สุดในข้อมูลภายในตอนนี้คืออะไร",
         "compare": ["`performance`", "`mechanisms`", "`settings`"]},
        {"__from_state__": None}),
    "setup_quality": score(
        {"question": "คุณภาพการตั้งค่าปัจจุบันเมื่อดูจากข้อมูลภายใน (ไม่ใช่ความรู้สึก)",
         "compare": ["`performance`", "`settings`", "`news_digest`"]},
        ["แย่ (ควรหยุดทบทวน)", "ต่ำ", "พอใช้", "ดี", "ดีมาก (รักษาไว้)"]),
    "next_action": choice(
        {"question": "ข้อมูลภายในชี้ว่าควรทำอะไรต่อ",
         "compare": ["`performance`", "`mechanisms`", "`news_digest`"]},
        {"add_weight": "เพิ่มน้ำหนัก/ผ่อนตัวกรอง (net ดี · ความถี่ต่ำกว่าเป้า)",
         "cut_weight": "ลดน้ำหนัก/เพิ่มตัวกรอง (net ลบ · ขาดทุนซ้ำ)",
         "fix_mechanism": "ซ่อมกลไกที่รั่วเป็นตัว ๆ", "hold": "คงไว้ (ยังไม่มีหลักฐานพอให้ขยับ)"}),
})

_preset("admin-structure", "ประเมิน 'การวิวัฒน์โครงสร้าง' ของแอดมินบอท (กรอบ · เจตนาระบบ · คืนค่าได้)", lambda s: {
    "within_structure_envelope": noul(
        {"question": "การขยับ `proposal` ยังอยู่ใน **กรอบโครงสร้าง** ที่กำหนดไว้ (STRUCTURE_BOUNDS/กรอบค่าที่อนุญาต) ใช่หรือไม่",
         "compare": ["`proposal`", "`structure_envelope`"]},
        {"true": "อยู่ในกรอบที่กำหนดทั้งหมด", "false": {"what": "ออกนอกกรอบ", "examples": ["แตะคีย์สงวน", "แก้โครงสร้างโค้ด/ตัวเทรด/kill switch"]}}),
    "preserves_design": noul(
        {"question": "การขยับนี้ **คงเจตนาเดิมของระบบ** ไว้ครบ (ด่าน net → 36 ค่า → เทียบสองฝั่ง · ไม่ทบความเสี่ยง) ใช่หรือไม่",
         "compare": ["`proposal`", "`design`"]},
        {"true": "ดุลของด่านเดิมยังอยู่ครบ", "false": "ทำให้ด่านใดด่านหนึ่งอ่อนลงจนเปลี่ยนเจตนาระบบ"}),
    "reversible": noul(
        {"question": "ยัง **คืนค่าโรงงานกลับได้เสมอ** หลังการขยับนี้ ใช่หรือไม่", "compare": ["`proposal`", "`structure_envelope`"]},
        {"true": "ย้อนกลับได้ด้วยค่าโรงงานสำรอง", "false": "มีผลที่ไม่สามารถย้อนกลับได้"}),
    "structure_risk": score(
        {"question": "ระดับความเสี่ยงของการขยับ 'โครงสร้าง' ครั้งนี้", "compare": ["`proposal`", "`performance`"]},
        ["ต่ำมาก", "ต่ำ", "ปานกลาง", "สูง", "สูงมาก (ควรให้มนุษย์ยืนยัน)"]),
    "evolve_area": choice(
        {"question": "ถ้าจะวิวัฒน์โครงสร้าง ควรเริ่มที่ส่วนไหนก่อน", "compare": ["`performance`", "`areas`"]},
        {"__from_state__": None}),
    "evidence_enough": noul(
        {"question": "มี **หลักฐานจากข้อมูลจริงเพียงพอ** ให้ขยับโครงสร้างแล้วใช่หรือไม่",
         "compare": ["`performance`", "`history`"]},
        {"true": {"what": "มีหลายช่วงข้อมูลสนับสนุน", "not_for": "ผ่านเพราะผลไม่กี่ไม้"},
         "false": "หลักฐานยังบางเกินกว่าจะขยับโครงสร้าง"}),
})

_preset("hermes-decision", "ตัวช่วยดุลยพินิจของสมองหลัก (hermes) ก่อนตัดสินใจ/อนุมัติในระบบเทรด", lambda s: {
    "approve": noul(
        {"question": "การตัดสินใจนี้ **ควรอนุมัติ/ลงมือ** หรือไม่ (ยึดเป้าหมายสูงสุด = ทำกำไรให้ได้มากที่สุด)",
         "compare": ["`intent`", "`evidence`", "`proposal`", "`risk`"]},
        {"true": "หลักฐานจริงชัด · อยู่ในเจตนาระบบ · กำไร/ความเสี่ยงสมเหตุสมผล",
         "false": "หลักฐานไม่พอ หรือเสี่ยง/ขัดกติกาเจ้าของระบบ"}),
    "evidence_enough": noul(
        {"question": "หลักฐานที่มี (ตัวเลขจริงจากระบบ) **พอต่อการตัดสินใจ** แล้วหรือยัง",
         "compare": ["`evidence`"]},
        {"true": "มีตัวเลขจริงรองรับพอ", "false": "ยังต้องเก็บข้อมูลเพิ่ม"}),
    "within_intent": noul(
        {"question": "การตัดสินใจนี้ **อยู่ในเจตนาระบบและกติกาเจ้าของระบบ** (ด่าน 3 ชั้น · ห้ามสมมติ · คืนค่าได้) หรือไม่",
         "compare": ["`intent`", "`proposal`"]},
        {"true": "อยู่ในเจตนาระบบ", "false": "ออกนอกเจตนา/ขัดกติกา"}),
    "profit_aligned": noul(
        {"question": "สิ่งนี้ **ทำให้ระบบทำกำไรได้มากขึ้นจริง** (ไม่ใช่แค่ดูดี/ถี่ขึ้น) หรือไม่",
         "compare": ["`proposal`", "`evidence`"]},
        {"true": "มีเหตุผลเชิงกำไรชัด", "false": "ยังไม่ชัด/ไม่เกี่ยวกำไร"}),
    "severe_risk": noul(
        {"question": "มีความเสี่ยง **ร้ายแรงที่ยังไม่ได้จัดการ** (เสียเงินจริง · ระบบพัง · คืนค่าไม่ได้) หรือไม่",
         "compare": ["`proposal`", "`risk`"]},
        {"true": "มี · ต้องจัดการก่อน", "false": "ไม่มี/คุมได้"}),
    "next_action": choice(
        {"question": "ก้าวถัดไปที่เหมาะที่สุด",
         "compare": ["`approve`", "`evidence_enough`", "`severe_risk`"]},
        {"proceed": "ลงมือได้เลย", "stage": "ทำแบบขั้นบันได (จำลอง → ผลเล็ก → ขยาย)",
         "hold": "ชะลอและเก็บหลักฐานเพิ่ม", "rollback_first": "เตรียมทางคืนค่าก่อน"}),
})


_preset("central-decision", "ระบบกลางของ Hermes: Jev เป็นทั้งผู้ช่วยและผู้ตัดสินใจ (เจ้าของระบบมอบอำนาจ)", lambda s: {
    "right_approach": noul(
        {"question": "แนวทางที่เสนอมา **เป็นทางที่ถูกต้องที่สุด** สำหรับงานนี้หรือไม่",
         "compare": ["`task`", "`context`", "`options`"]},
        {"true": "เป็นทางที่ถูกต้อง/เหมาะที่สุด", "false": "ยังไม่ใช่ทางที่ดีที่สุด"}),
    "safer_alternative": noul(
        {"question": "มีทางเลือกอื่นที่ **ปลอดภัยกว่าหรือดีกว่า** ซึ่งควรเลือกแทนหรือไม่",
         "compare": ["`options`", "`context`"]},
        {"true": "มี · ควรเปลี่ยนไปทางนั้น", "false": "ไม่มี · ทางนี้ดีแล้ว"}),
    "safe_to_act": noul(
        {"question": "การลงมือตามแนวทางนี้ **ปลอดภัย** (ไม่ทำลายระบบ ข้อมูล หรือความสามารถกู้คืน) หรือไม่",
         "compare": ["`task`", "`context`", "`risk`"]},
        {"true": "ปลอดภัย/กู้คืนได้", "false": "ไม่ปลอดภัย ต้องป้องกันก่อน"}),
    "ready_now": noul(
        {"question": "พร้อมลงมือ **เดี๋ยวนี้** หรือยัง (ข้อมูลครบ · ไม่ต้องรออะไรเพิ่ม)",
         "compare": ["`context`", "`risk`"]},
        {"true": "พร้อมลงมือ", "false": "ยังไม่พร้อม"}),
    "decision": choice(
        {"question": "คำตัดสิน: ควรทำอะไร",
         "compare": ["`right_approach`", "`safer_alternative`", "`safe_to_act`", "`ready_now`"]},
        {"do": "ลงมือตามแนวทางนี้", "do_better": "เปลี่ยนไปทางเลือกที่ดีกว่า",
         "prepare": "เตรียมความปลอดภัย/สำรองก่อนแล้วค่อยทำ", "hold": "ชะลอ รอข้อมูลเพิ่ม",
         "escalate_owner": "เรื่องนี้ต้องให้เจ้าของระบบตัดสิน"}),
})


_preset("regime", "จัดภาวะตลาด: แนวโน้ม/กรอบ/สับสน + ความแข็งของแนวโน้ม", lambda s: {
    "regime": choice(
        {"question": "ภาวะตลาดจาก `features` ตอนนี้เป็นแบบใด", "inspect": "`features`", "compare": ["`features`", "`prices`"]},
        {"trend_up": "แนวโน้มขึ้นชัด", "trend_down": "แนวโน้มลงชัด", "range": "แกว่งในกรอบกว้าง",
         "choppy": "สับสน/ไร้ทิศทาง ความผันผวนไม่สม่ำเสมอ"}),
    "trend_strength": score(
        {"question": "ความแข็งของแนวโน้มอยู่ระดับใด", "inspect": "`features`"},
        ["ไม่มีแนวโน้ม", "อ่อน", "ปานกลาง", "แข็ง", "แข็งมาก"]),
    "suitable_for_trend_following": noul(
        {"question": "ภาวะนี้เหมาะกับการเทรดตามแนวโน้มหรือไม่", "compare": ["`features`", "`prices`"]},
        {"true": "มีแนวโน้มพอให้ตามได้", "false": "แกว่ง/สับสนเกินกว่าจะตามแนวโน้ม"}),
})


# ── ตัวเรียก API ──────────────────────────────────────────────────────────────
def _post(payload, timeout):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key(),
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/kanutsanan/thai-gold-trading-system",
                 "X-Title": "Thai Gold Trading System (Jev decision gate)"},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def ask(state, questions, model=None, timeout=None, max_attempts=None, preset="custom", context=None):
    """ถาม Jev — คืน dict เสมอ (ไม่โยน exception): {ok, answers, usage, latency_ms, error}

    fail-safe: ถ้าเรียกไม่ได้ (คีย์หาย/เน็ตล่ม/quota) → {"ok": False, ...} แล้วผู้เรียกใช้ทางเดิมต่อ
    """
    cfg = load_config()
    out = {"ok": False, "preset": preset, "context": context, "answers": {}, "derived": {},
           "usage": {}, "latency_ms": 0, "error": None, "model": model or cfg["model"]}
    # AI ที่อยู่ในวงจรเทรดต้องผ่าน mode 2 และไม่มี Kill Switch ก่อนเรียก API
    if context not in ALLOWED_CONTEXTS and context != CONTEXT_MANUAL:
        out["error"] = ("Jev ทำงานกับ mode2 / admin / hermes-trade / hermes — ต้องระบุ context "
                        "ของผู้เรียก ไม่เปิดให้ส่วนกลางเรียกเอง")
        return out
    if context in TRADING_CONTEXTS:
        try:
            require_ai_mode()
        except Exception as exc:
            out["error"] = "AI integration blocked by trading mode or Kill Switch: %s" % exc
            return out
    if not cfg.get("enabled", True):
        out["error"] = "ปิดใช้งานอยู่ (jev_config.json enabled=false)"
        return out
    key = api_key()
    if not key:
        out["error"] = ("ไม่พบคีย์สำหรับ Jev — ระบบทำงานต่อได้โดยไม่ต้องมี Jev (ใช้กฎตัวเลขเดิม) · "
                        "เครื่องใหม่: รัน tools/jev_connect.py --setup เพื่อเชื่อมต่ออัตโนมัติ")
        return out
    timeout = timeout or cfg.get("timeout_seconds", 60)
    attempts = max_attempts or cfg.get("max_attempts", 3)
    payload = {"model": out["model"], "state": state, "questions": questions}

    t0 = time.time()
    for i in range(attempts):
        try:
            data = _post(payload, timeout)
            out["ok"] = True
            out["answers"] = data.get("answers", {}) or {}
            out["usage"] = data.get("usage", {}) or {}
            out["model"] = data.get("model", out["model"])
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
            out["error"] = "HTTP %s: %s" % (e.code, body)
            if e.code in (429, 529, 500, 502, 503) and i < attempts - 1:
                time.sleep(min(2 ** i, 8))
                continue
            break
        except Exception as e:
            out["error"] = "%s: %s" % (type(e).__name__, e)
            if i < attempts - 1:
                time.sleep(min(2 ** i, 8))
                continue
            break
    out["latency_ms"] = int((time.time() - t0) * 1000)
    if cfg.get("audit", True):
        _audit(out)
    return out


def _audit(out):
    try:
        os.makedirs(WORK, exist_ok=True)
        it = out.get("usage", {}) or {}
        inp = int(it.get("input_tokens") or 0)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "preset": out.get("preset"), "context": out.get("context"), "ok": out.get("ok"), "derived": out.get("derived"),
               "latency_ms": out.get("latency_ms"),
               "input_tokens": inp, "output_tokens": int(it.get("output_tokens") or 0),
               "cost_usd": round(inp * INPUT_PRICE_PER_M / 1e6, 8),
               "model": out.get("model"), "error": out.get("error"),
               "summary": _summary(out.get("answers") or {})}
        with io.open(AUDIT, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _summary(answers):
    """สรุปอ่านง่าย: noul→ทศนิยม 2 ตำแหน่ง · choice→ตัวที่เลือก(+ความมั่นใจ) · score→คะแนน(+ความมั่นใจ)"""
    s = {}
    for k, a in answers.items():
        if not isinstance(a, dict):
            continue
        t = a.get("type")
        if t == "noul":
            s[k] = round(float(a.get("noul") or 0), 2)
        elif t == "choice":
            s[k] = "%s(%.2f)" % (a.get("choice"), float(a.get("confidence") or 0))
        elif t == "score":
            s[k] = "%.2f(%.2f)" % (float(a.get("score") or 0), float(a.get("confidence") or 0))
    return s


# ── อ่านผลแบบปลอดภัย (ไม่พังเวลาคำตอบไม่ครบ) ─────────────────────────────────
def N(answers, key, default=0.5):
    """ค่าความน่าจะเป็นของคำถาม noul (0..1)"""
    a = answers.get(key) or {}
    try:
        return float(a.get("noul"))
    except Exception:
        return default


def C(answers, key, default=None):
    a = answers.get(key) or {}
    return a.get("choice", default)


def CONF(answers, key, default=0.0):
    a = answers.get(key) or {}
    try:
        return float(a.get("confidence"))
    except Exception:
        return default


def S(answers, key, default=0.0):
    a = answers.get(key) or {}
    try:
        return float(a.get("score"))
    except Exception:
        return default


# ── ค่าประกอบที่โค้ดคำนวณเอง (composite — โค้ดคุมการรวมผล) ────────────────────
def derive(preset, answers):
    """รวมคำตอบหลายข้อเป็นสัญญาณใช้งานได้จริง (โค้ดเป็นเจ้าของการรวมผล)"""
    d = {}
    if not answers:
        return d
    if preset == "news":
        # คะแนนข่าว -1(กดทอง) .. +1(หนุนทอง) — สอบเทียบด้วยความน่าจะเป็น + ความหนักแน่น
        nup = N(answers, "news_net_up")
        conv = S(answers, "conviction") / 4.0
        priced = N(answers, "already_priced")
        d["news_score"] = round((nup - 0.5) * 2.0 * max(conv, 0.15) * (1.0 - 0.5 * priced), 3)
        d["direction"] = C(answers, "pressure", "neutral")
        d["conviction"] = round(conv, 2)
        d["already_priced"] = round(priced, 2)
        d["catalyst_today"] = N(answers, "catalyst_today") >= 0.5
        d["theme"] = C(answers, "dominant_theme", "other")
        d["low_confidence"] = CONF(answers, "pressure") < 0.45 or CONF(answers, "conviction") < 0.45
    elif preset == "rec-check":
        d["follows_evidence"] = N(answers, "follows_evidence")
        d["is_chasing"] = N(answers, "is_chasing")
        d["text_matches_numbers"] = N(answers, "text_matches_numbers")
        d["biggest_risk"] = C(answers, "biggest_risk", "unknown")
        d["robustness"] = round(S(answers, "robustness") / 4.0, 2)
        # ผ่านการตรวจหรือไม่ (เกณฑ์ระวัง — โค้ดเป็นคนตัดสิน ไม่ใช่โมเดล)
        d["pass"] = (d["follows_evidence"] >= 0.60 and d["is_chasing"] <= 0.40
                     and d["text_matches_numbers"] >= 0.70)
        if "conflicts_with_admin" in answers:
            d["conflicts_with_admin"] = N(answers, "conflicts_with_admin")
            if d["conflicts_with_admin"] > 0.60:
                d["warnings"].append("ขัดกับสิ่งที่แอดมินบอทเพิ่งปรับ")
                d["pass"] = False
        d["warnings"] = ([w for w, cond in
                          (("ไม่ตรงหลักฐาน", d["follows_evidence"] < 0.60),
                           ("เข้าลักษณะไล่ราคา", d["is_chasing"] > 0.40),
                           ("ตัวเลขไม่ตรงหลักฐาน", d["text_matches_numbers"] < 0.70),
                           ("ความทนทานต่ำ", d["robustness"] < 0.5)) if cond] or [])
    elif preset == "hermes-decision":
        d["approve"] = N(answers, "approve")
        d["evidence_enough"] = N(answers, "evidence_enough")
        d["within_intent"] = N(answers, "within_intent", 1.0)
        d["profit_aligned"] = N(answers, "profit_aligned", 0.5)
        d["severe_risk"] = N(answers, "severe_risk", 0.5)
        d["next_action"] = C(answers, "next_action", "hold")
        d["decision"] = ("proceed" if (d["approve"] >= 0.70 and d["evidence_enough"] >= 0.60
                                       and d["within_intent"] >= 0.80 and d["severe_risk"] <= 0.30)
                         else ("stage" if d["approve"] >= 0.50 else "hold"))
        if d["severe_risk"] > 0.50:
            d["decision"] = "rollback_first"
        d["reasons"] = [r for r, cond in (
            ("หลักฐานยังไม่พอ", d["evidence_enough"] < 0.60),
            ("ออกนอกเจตนา/ขัดกติกาเจ้าของระบบ", d["within_intent"] < 0.80),
            ("ยังไม่ชัดว่าเพิ่มกำไร", d["profit_aligned"] < 0.50),
            ("มีความเสี่ยงร้ายแรงที่ยังไม่จัดการ", d["severe_risk"] > 0.50),
            ("ควรทำแบบขั้นบันได", d["decision"] == "stage"),
        ) if cond]
        d["advice"] = {"proceed": "ลงมือได้ (ตามดุลยพินิจของสมองหลัก)",
                       "stage": "ทำแบบขั้นบันได: จำลอง → ผลเล็ก → ขยาย",
                       "hold": "ชะลอ + เก็บหลักฐานจริงเพิ่ม",
                       "rollback_first": "เตรียมทางคืนค่า/สำรองก่อนลงมือ"}.get(d["decision"], d["decision"])
    elif preset == "central-decision":
        d["right_approach"] = N(answers, "right_approach")
        d["safer_alternative"] = N(answers, "safer_alternative")
        d["safe_to_act"] = N(answers, "safe_to_act")
        d["ready_now"] = N(answers, "ready_now")
        d["decision"] = C(answers, "decision", "hold")
        # ★ Jev เป็นผู้ตัดสินใจในระบบกลาง: ยืนยันชัดเมื่อไร ให้มีผลเลย
        d["decide_now"] = bool(d["decision"] == "do" and d["safe_to_act"] >= 0.70
                               and d["ready_now"] >= 0.60 and d["safer_alternative"] <= 0.40)
        d["reasons"] = [r for r, cond in (
            ("มีทางเลือกที่ดีกว่า", d["safer_alternative"] > 0.40),
            ("ยังไม่ปลอดภัยพอ", d["safe_to_act"] < 0.70),
            ("ยังไม่พร้อมลงมือ", d["ready_now"] < 0.60),
            ("แนวทางยังไม่ใช่ทางที่ดีที่สุด", d["right_approach"] < 0.50),
        ) if cond]
        d["advice"] = {"do": "ลงมือได้ (คำตัดสินของ Jev)",
                       "do_better": "เปลี่ยนไปทางเลือกที่ดีกว่า",
                       "prepare": "เตรียมความปลอดภัย/สำรองก่อน",
                       "hold": "ชะลอ รอข้อมูลเพิ่ม",
                       "escalate_owner": "ต้องให้เจ้าของระบบตัดสิน"}.get(d["decision"], d["decision"])
    elif preset == "admin-safety":
        d["within_intent"] = N(answers, "within_intent")
        d["raises_drawdown_risk"] = N(answers, "raises_drawdown_risk")
        d["driven_by_noise"] = N(answers, "driven_by_noise")
        d["conflicts_with_news"] = N(answers, "conflicts_with_news")
        d["risk_level"] = round(S(answers, "risk_level") / 4.0, 2)
        d["next_lever"] = C(answers, "next_lever")
        d["safe"] = (d["within_intent"] >= 0.70 and d["raises_drawdown_risk"] <= 0.40
                     and d["driven_by_noise"] <= 0.50)
        d["review_needed"] = (not d["safe"]) or d["risk_level"] >= 0.75
        if "conflicts_with_other_bot" in answers:
            d["conflicts_with_other_bot"] = N(answers, "conflicts_with_other_bot")
            if d["conflicts_with_other_bot"] > 0.60:
                d["reasons"].append("ขัดกับสิ่งที่บอทอีกตัว (โหมด 2) เพิ่งเสนอ")
                d["review_needed"] = True
        d["reasons"] = ([r for r, cond in
                         (("ออกนอกเจตนาระบบ", d["within_intent"] < 0.70),
                          ("เพิ่มความเสี่ยงขาดทุนต่อเนื่อง", d["raises_drawdown_risk"] > 0.40),
                          ("ได้แรงจูงใจจากสัญญาณรบกวน", d["driven_by_noise"] > 0.50),
                          ("สวนทางข่าวล่าสุด", d["conflicts_with_news"] > 0.60),
                          ("ความเสี่ยงสูง", d["risk_level"] >= 0.75)) if cond] or [])
    elif preset == "internal":
        d["in_profit_zone"] = N(answers, "in_profit_zone")
        d["frequency_ok"] = N(answers, "frequency_ok")
        d["edge_durable"] = N(answers, "edge_durable")
        d["main_leak"] = C(answers, "main_leak")
        d["setup_quality"] = round(S(answers, "setup_quality") / 4.0, 2)
        d["next_action"] = C(answers, "next_action", "hold")
        d["healthy"] = (d["in_profit_zone"] >= 0.60 and d["frequency_ok"] >= 0.60
                        and d["edge_durable"] >= 0.50)
        d["watch"] = [w for w, cond in
                      (("ยังไม่เข้าโซนกำไร", d["in_profit_zone"] < 0.60),
                       ("ความถี่ไม่เหมาะกับโซนกำไร", d["frequency_ok"] < 0.60),
                       ("ขอบได้เปรียบอาจไม่ยั่งยืน", d["edge_durable"] < 0.50),
                       ("คุณภาพการตั้งค่าต่ำ", d["setup_quality"] < 0.50)) if cond]
        d["low_confidence"] = CONF(answers, "main_leak") < 0.40 or CONF(answers, "next_action") < 0.40
    elif preset == "admin-structure":
        d["within_structure_envelope"] = N(answers, "within_structure_envelope")
        d["preserves_design"] = N(answers, "preserves_design")
        d["reversible"] = N(answers, "reversible")
        d["evidence_enough"] = N(answers, "evidence_enough")
        d["structure_risk"] = round(S(answers, "structure_risk") / 4.0, 2)
        d["evolve_area"] = C(answers, "evolve_area")
        d["safe"] = (d["within_structure_envelope"] >= 0.75 and d["preserves_design"] >= 0.70
                     and d["reversible"] >= 0.80 and d["evidence_enough"] >= 0.60)
        d["review_needed"] = (not d["safe"]) or d["structure_risk"] >= 0.75
        d["reasons"] = [r for r, cond in
                        (("ออกนอกกรอบโครงสร้าง", d["within_structure_envelope"] < 0.75),
                         ("ทำให้เจตนาระบบเปลี่ยน", d["preserves_design"] < 0.70),
                         ("ย้อนกลับได้ไม่แน่ใจ", d["reversible"] < 0.80),
                         ("หลักฐานยังไม่พอ", d["evidence_enough"] < 0.60),
                         ("ความเสี่ยงสูง", d["structure_risk"] >= 0.75)) if cond]
    elif preset == "regime":
        d["regime"] = C(answers, "regime", "unknown")
        d["trend_strength"] = round(S(answers, "trend_strength") / 4.0, 2)
        d["suitable_for_trend_following"] = N(answers, "suitable_for_trend_following") >= 0.5
        d["low_confidence"] = CONF(answers, "regime") < 0.45
    return d


def ask_preset(preset, state, model=None, timeout=None, context=None):
    """เรียกพรีเซ็ต — คืนผลพร้อม derived (fail-safe) · ต้องระบุ context ของบอท"""
    if preset not in PRESETS:
        return {"ok": False, "preset": preset, "context": context,
                "error": "ไม่รู้จักพรีเซ็ตนี้: %s" % preset, "answers": {}, "derived": {}}
    questions = PRESETS[preset]["build"](state)
    # ★ เพิ่ม 23 ก.ย. 2026 (เจ้าของระบบ: "ให้บอท 2 ตัวคุยกัน/ปรึกษากันได้"): ถามเรื่อง 'ขัดกันเอง'
    #   เฉพาะเมื่อมีข้อมูลของบอทอีกตัวใน state (ถ้าไม่มี = ไม่ถาม — ไม่ใส่คำตอบปลอม)
    if preset == "admin-safety" and isinstance(state, dict) and state.get("other_bot"):
        questions["conflicts_with_other_bot"] = noul(
            {"question": "การเปลี่ยนนี้ **ขัดกับสิ่งที่บอทอีกตัว (โหมด 2) เพิ่งเสนอหรือเพิ่งถูกนำไปใช้** ใช่หรือไม่",
             "compare": ["`proposal`", "`other_bot`"],
             "focus": "ดูว่าไปทางเดียวกันหรือสวนกัน · และค่าที่อีกบอทปรับไปแล้ว"},
            {"true": {"what": "สวนทางกันชัด — เช่นอีกฝั่งเพิ่งลดค่าที่รอบนี้จะเพิ่ม",
                      "examples": ["อีกบอทเพิ่งลดความถี่ แต่รอบนี้จะเพิ่มความถี่"]},
             "false": "สอดคล้องหรือไม่เกี่ยวข้องกัน"})
    if preset == "rec-check" and isinstance(state, dict) and state.get("other_bot"):
        questions["conflicts_with_admin"] = noul(
            {"question": "คำแนะนำนี้ **ขัดกับสิ่งที่แอดมินบอทเพิ่งปรับไป** ในรอบหลัง ๆ ใช่หรือไม่",
             "compare": ["`proposal`", "`other_bot`"],
             "focus": "ดูว่ารอบล่าสุดของแอดมินบอทขยับไปทางเดียวกันหรือสวนกัน"},
            {"true": "สวนทางกับที่แอดมินบอทเพิ่งปรับ", "false": "ไปทางเดียวกันหรือไม่เกี่ยวข้อง"})

    # พรีเซ็ตที่ต้องดึงตัวเลือกจาก state (กลไก/ส่วนโครงสร้าง/คันโยกจริงในระบบ)
    if preset == "internal":
        mechs = state.get("mechanisms") if isinstance(state, dict) else None
        if not mechs:
            questions.pop("main_leak", None)
        else:
            opts = {}
            for m in list(mechs)[:8]:
                name = m.get("name") if isinstance(m, dict) else str(m)
                note = (m.get("note") if isinstance(m, dict) else "") or "กลไกในระบบ"
                opts[str(name)] = str(note)
            questions["main_leak"] = choice(
                {"question": "ตัวที่ **รั่วกำไร** มากที่สุดในข้อมูลภายในตอนนี้คืออะไร",
                 "compare": ["`performance`", "`mechanisms`", "`settings`"]}, opts)
    if preset == "admin-structure":
        areas = state.get("areas") if isinstance(state, dict) else None
        if not areas:
            questions.pop("evolve_area", None)
        else:
            opts = {}
            for a in list(areas)[:8]:
                name = a.get("name") if isinstance(a, dict) else str(a)
                note = (a.get("note") if isinstance(a, dict) else "") or "ส่วนโครงสร้าง"
                opts[str(name)] = str(note)
            questions["evolve_area"] = choice(
                {"question": "ถ้าจะวิวัฒน์โครงสร้าง ควรเริ่มที่ส่วนไหนก่อน",
                 "compare": ["`performance`", "`areas`"]}, opts)
    if preset == "admin-safety":
        cands = state.get("candidates") if isinstance(state, dict) else None
        if not cands:
            questions.pop("next_lever", None)
        else:
            opts = {}
            for c in list(cands)[:8]:
                name = c.get("name") if isinstance(c, dict) else str(c)
                note = (c.get("note") if isinstance(c, dict) else "") or "ค่าเดียวกับที่เสนอ"
                opts[str(name)] = str(note)
            questions["next_lever"] = choice(
                {"question": "ถ้าจะขยับต่อ ควรดูที่ 'ค่า' ตัวไหนก่อน",
                 "compare": ["`proposal`", "`performance`", "`candidates`"]}, opts)
    out = ask(state, questions, model=model, timeout=timeout, preset=preset, context=context)
    out["derived"] = derive(preset, out.get("answers") or {}) if out.get("ok") else {}
    return out


# ── ตัวอย่าง state (ใช้ตอนทดสอบ) ─────────────────────────────────────────────
SAMPLE_STATES = {
    "news": {
        "news": [
            {"headline": "Fed officials signal fewer rate cuts as inflation stays sticky", "source": "Reuters"},
            {"headline": "Gold ETF inflows hit six-month high as investors seek safety", "source": "Bloomberg"},
            {"headline": "Dollar index edges up ahead of key jobs report", "source": "investing.com"},
        ],
        "gold": {"price": 3672.5, "atr14": 18.4, "change_pct_24h": 0.6},
    },
    "rec-check": {
        "proposal": {"action": "set_gate", "name": "side_net_gate", "from": 0.0, "to": -2.0,
                     "reason": "net เฉลี่ยต่อไม้ยังลบ (-1.8) และความถี่สูงกว่าเป้า 1.4 เท่า"},
        "evidence": {"net_avg_per_trade": -1.8, "trades_per_day": 3.4, "target_freq_per_day": 2.4,
                     "hwm_gap_pct": 3.1, "top_loss_mechanism": "reversal"},
        "market": {"price": 3672.5, "atr14": 18.4, "move_last_2h_atr": 1.3, "range_high": 3681.0, "range_low": 3648.6},
        "news_digest": "ข่าวเอียงกดทอง (สัดส่วน -0.36) · Fed เข้มขึ้นเล็กน้อย · ETF ไหลเข้า",
        "other_bot": {"rounds": [{"time": "2026-09-23T04:55", "mode": "advisory",
                                  "changes": [{"key": "side_net_gate.max_age_hours", "to": 6}]}]},
    },
    "admin-safety": {
        "proposal": {"param": "atr_stop_multiplier", "from": 1.6, "to": 1.9,
                     "reason": "ลดการถูกตัดขาดทุนจากความผันผวนชั่วคราว"},
        "envelope": {"allowed": ["atr_stop_multiplier", "profit_exit", "side_net_gate"],
                     "reserved": ["volume", "live_enabled", "max_risk_pct"], "max_step_pct": 25},
        "performance": {"net_avg_per_trade": -1.8, "trades_per_day": 3.4, "stopout_rate": 0.42,
                        "hwm_gap_pct": 3.1, "window_days": 14, "trades_in_window": 38},
        "news_digest": "ข่าวเอียงกดทอง (สัดส่วน -0.36) · ผันผวนสูงขึ้น",
        "other_bot": {"latest": {"changes": [{"key": "profit_exit.no_signal_tp_fraction", "to": 0.45}]},
                      "note": "บอทโหมด 2 เพิ่งเสนอผ่อนการออกทำกำไร"},
        "candidates": [{"name": "profit_exit", "note": "การออกทำกำไรยังเร็วเกิน"},
                       {"name": "side_net_gate", "note": "ประตู net ฝั่งตรงข้ามยังหลวม"},
                       {"name": "atr_stop_multiplier", "note": "SL แคบเกินไปในตลาดผันผวน"}],
    },
    "internal": {
        "performance": {"net_avg_per_trade": -1.8, "trades_per_day": 3.4, "target_freq_per_day": 2.4,
                        "win_rate": 41.2, "avg_win": 2.1, "avg_loss": -1.6, "hwm_gap_pct": 3.1,
                        "window_days": 14, "stopout_rate": 0.42},
        "equity": {"equity": 10.44, "balance": 10.44, "hwm": 10.78},
        "settings": {"atr_stop_multiplier": 1.2, "min_reward_risk": 1.4, "max_risk_pct": 8.0,
                     "side_net_gate": {"enabled": True}, "early_cut": {"enabled": True}},
        "mechanisms": [{"name": "reversal_stopout", "note": "ถูกตัดขาดทุนตอนราคาย้อนกลับ"},
                       {"name": "late_entry", "note": "เข้าช้าเพราะรอสัญญาณยืนยัน"},
                       {"name": "tp_too_early", "note": "ออกทำกำไรเร็วเกิน"}],
        "news_digest": "ข่าวเอียงกดทอง (สัดส่วน -1.00) · Fed เข้มขึ้น · ดอลลาร์แข็ง",
    },
    "admin-structure": {
        "proposal": {"param": "strategy_router.auto_threshold.window_records", "from": 240, "to": 300,
                     "reason": "หน้าต่างข้อมูลสั้นเกินทำให้ค่าแกว่ง"},
        "structure_envelope": {"allowed": ["strategy_router.adaptive.disable_profit_factor",
                                           "strategy_router.adaptive.min_samples",
                                           "strategy_router.auto_threshold.window_records",
                                           "strategy_router.auto_threshold.band_min_widths.raw",
                                           "atr_stop_multiplier", "min_reward_risk", "max_risk_pct",
                                           "early_cut.enabled", "revenge_guard.enabled"],
                               "factory_backup": "work/factory/ (คืนค่าได้ด้วย restore_factory.py)"},
        "design": {"gates": ["ด่าน 1 ประตู net ต่อกลยุทธ์-ทิศทาง", "ด่าน 2 36 ค่า p25-p90",
                             "ด่าน 3 เทียบสองฝั่ง (ไม่เกี่ยวกับประตู net)"],
                   "rule": "งานที่ใช้ LLM ต้องให้บอทเป็นผู้ดูแล · ห้ามแตะคีย์สงวน/ตัวเทรด/kill switch/โครงสร้างโค้ด"},
        "performance": {"net_avg_per_trade": -1.8, "trades_per_day": 3.4, "window_days": 30, "trades_in_window": 38},
        "history": {"windows_seen": 3, "consistent": False},
        "areas": [{"name": "auto_threshold (36 ค่า)", "note": "หน้าต่างเรียนรู้/ความกว้าง band"},
                  {"name": "strategy_router (เราเตอร์กลยุทธ์)", "note": "เกณฑ์เลือกกลยุทธ์/น้ำหนัก"},
                  {"name": "gate (ด่าน net/ประตู)", "note": "ประตู net และการเทียบสองฝั่ง"},
                  {"name": "guards (กันแก้แค้น/ตัดขาดทุน)", "note": "ความไวของกลไกป้องกัน"},
                  {"name": "exits (TP/SL/profit_exit)", "note": "เกณฑ์ออกทำกำไร/ตัดขาดทุน"}],
    },
    "regime": {
        "features": {"ema20_ema50_gap_atr": 0.35, "adx14": 18.2, "atr14": 18.4,
                     "range_last_20_bars_atr": 5.1, "higher_highs": False, "lower_lows": False},
        "prices": [3665.0, 3668.2, 3666.1, 3670.4, 3672.0, 3669.5, 3671.8, 3674.2, 3672.5],
    },
    # ★ 23 ก.ย. 2026: พรีเซ็ตของสมองหลัก (ระบบกลาง = Jev ตัดสินใจได้ · hermes-trade = บันไดอำนาจ)
    "hermes-decision": {"proposal": "เปิดระบบเทรดคืนแบบเฝ้าดู 30 ไม้แรก", "evidence": "ไม้จริง 0 ไม้หลังชั้นวิวัฒนาการ",
                        "intent": "ระบบต้องปรับตัว/วิวัฒน์ได้และทำกำไรราบรื่น", "risk": "เปิดแล้วระบบยังไม่ถูกพิสูจน์"},
    "central-decision": {"task": "จัดโครงสร้างสกิล/เครื่องมือของ Hermes ใหม่ให้ค้นหาง่ายขึ้น",
                         "context": "Hermes central: งานกลาง ไม่เกี่ยวกับระบบเทรด",
                         "options": ["A: รวมสกิลซ้ำเข้าด้วยกัน", "B: คงเดิม แยกเป็นเอกสารอ้างอิง"],
                         "risk": "ย้ายไฟล์ผิดอาจทำให้สกิลเรียกไม่เจอ · มีการสำรองก่อนเสมอ"},
}


def probe():
    """ทดสอบการเชื่อมต่อด้วยคำถามจริง 1 ข้อ"""
    return ask_preset("news", {"news": [{"headline": "Gold steadies as traders weigh Fed policy outlook", "source": "test"}],
                               "gold": {"price": 3672.5, "atr14": 18.4}},
                      context=CONTEXT_MANUAL)


# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args or "--help" in args:
        print(__doc__)
        print("คีย์ที่ใช้: %s" % key_source_label())
        print("พรีเซ็ต: %s" % ", ".join(PRESETS))
        print("บริบทที่อนุญาต (เจ้าของระบบกำหนด): mode2 · admin · hermes (ระบบกลาง) · hermes-trade (สมองหลักในระบบเทรด)")
        print("  --context mode2|admin|hermes|hermes-trade|manual  (manual = ทดสอบด้วยมือ)")
        return 0

    def val(flag, default=None):
        return args[args.index(flag) + 1] if flag in args and len(args) > args.index(flag) + 1 else default

    # ★ บริบทของบอท (mode2 / admin) — CLI ใช้ 'manual' เป็นค่าเริ่มต้น
    ctx = val("--context", CONTEXT_MANUAL)

    if "--probe" in args:
        r = probe()
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    if "--selftest" in args:
        total_ok = 0
        for name in PRESETS:
            r = ask_preset(name, SAMPLE_STATES[name].copy() if isinstance(SAMPLE_STATES[name], dict) else {},
                           context=ctx)
            total_ok += 1 if r.get("ok") else 0
            print("── %-13s %s  %sms  tokens=%s" % (
                name, "✓" if r.get("ok") else "✗ " + str(r.get("error")),
                r.get("latency_ms"), (r.get("usage") or {}).get("input_tokens")))
            if r.get("ok"):
                print("   derived: %s" % json.dumps(r.get("derived"), ensure_ascii=False))
        print("\nผลรวม: %d/%d พรีเซ็ตเรียกได้" % (total_ok, len(PRESETS)))
        return 0 if total_ok == len(PRESETS) else 1

    if "--show-preset" in args:
        name = val("--show-preset")
        print(json.dumps(PRESETS[name]["build"](SAMPLE_STATES[name]), ensure_ascii=False, indent=2))
        return 0

    if "--preset" in args:
        name = val("--preset")
        state_path = val("--state")
        state = json.load(io.open(state_path, encoding="utf-8")) if state_path else SAMPLE_STATES.get(name, {})
        r = ask_preset(name, state, context=ctx)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    if "--questions" in args:
        q_path, s_path = val("--questions"), val("--state")
        questions = json.load(io.open(q_path, encoding="utf-8"))
        state = json.load(io.open(s_path, encoding="utf-8")) if s_path else ""
        r = ask(state, questions, context=ctx)
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0 if r.get("ok") else 1

    print("ไม่รู้จักคำสั่ง — ใช้ --help")
    return 2


if __name__ == "__main__":
    sys.exit(main())
