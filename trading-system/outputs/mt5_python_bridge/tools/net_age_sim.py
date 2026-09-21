# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""จำลอง: ด่านเน็ตอายุ 6 / 12 / 24 ชม. — เทียบว่าแบบไหนปลดคีย์ได้เท่าไร และคุ้มเสี่ยงไหม
ข้อมูลจริง: work/side_net_ledger.json (ผลไม้แยกตามคีย์ + เวลา) + audit (เหตุการณ์ประตูเน็ต)
"""
import json, io, os, datetime, collections

LEDGER = 'work/side_net_ledger.json'
rows = [json.loads(l) for l in io.open('work/auto_trader_audit.jsonl', encoding='utf-8') if l.strip()]
now = datetime.datetime.now(datetime.timezone.utc)

led = json.load(io.open(LEDGER, encoding='utf-8')) if os.path.exists(LEDGER) else {}
keys = led.get('keys') or led
if isinstance(keys, dict) and 'keys' in keys: keys = keys['keys']
print("คีย์ในสมุดบัญชี:", len(keys) if hasattr(keys, '__len__') else 0)

def parse_t(v):
    if not v: return None
    try: return datetime.datetime.fromisoformat(str(v).replace('Z', '+00:00'))
    except Exception: return None

def entry_age_h(e):
    t = parse_t(e.get('time') or e.get('ts') or e.get('closed_at'))
    if t is None: return 9e9
    if t.tzinfo is None: t = t.replace(tzinfo=datetime.timezone.utc)
    return (now - t).total_seconds() / 3600

stat = {}
for k, v in (keys.items() if isinstance(keys, dict) else []):
    entries = v.get('trades') or v.get('entries') or []
    if not isinstance(entries, list) or not entries:
        # โครงสร้างแบบง่าย: net เดี่ยว + keys_time
        n = float(v.get('net') or 0) if isinstance(v, dict) else 0.0
        stat[k] = {a: (n if (v.get('keys_time') and entry_age_h({'time': v['keys_time']}) <= a) else None)
                   for a in (6, 12, 24)} if isinstance(v, dict) else {6: None, 12: None, 24: None}
        continue
    for a in (6, 12, 24):
        s = sum(float(e.get('net') or 0) for e in entries if entry_age_h(e) <= a)
        stat.setdefault(k, {})[a] = s

print("\n%-24s %10s %10s %10s" % ("คีย์", "อายุ 6 ชม.", "อายุ 12 ชม.", "อายุ 24 ชม."))
freed = collections.Counter()
for k in sorted(stat)[:14]:
    d = stat[k]
    row = []
    for a in (6, 12, 24):
        v = d.get(a)
        row.append("  ปลด ✓" if (v is not None and v >= 0) else ("  บล็อก ✗" if v is not None else "   -"))
        if v is not None and v >= 0: freed[a] += 1
    print("%-24s %10s %10s %10s" % (k[:24], row[0], row[1], row[2]))

print("\n=== สรุป: จำนวนคีย์ที่ 'ผ่าน' ประตูเน็ต ===")
for a in (6, 12, 24):
    print("  อายุ %2d ชม. → ผ่าน %d คีย์" % (a, freed[a]))

# เหตุการณ์ประตูเน็ตจาก audit
net_ev = [e for e in rows if 'net' in str(e.get('event', '')).lower()]
print("\nเหตุการณ์เกี่ยวกับประตูเน็ตใน audit:", len(net_ev))
c = collections.Counter(e.get('event') for e in net_ev)
for k, v in c.most_common(6): print("   ", k, v)
