# -*- coding: utf-8 -*-
"""mgmt_diagnosis.py — ตัววินิจฉัย "การจัดการไม้ระหว่างถือ" (ปิดกำไร · ตัดขาดทุน)

ตอบคำถาม: ตัวปิดกำไร/ตัดขาดทุนทำงานจริงไหม? ถ้าทำไม่งั้นติดอะไร? และเสียโอกาสเท่าไร?
อ่านจากบันทึกจริงเท่านั้น (ไม่ใช้ AI · ต้นทุน $0 · อ่านอย่างเดียว ไม่แก้ค่า)

วิธีใช้:
    .venv/Scripts/python.exe outputs/mt5_python_bridge/tools/mgmt_diagnosis.py --hours 48

เหตุการณ์ที่อ่าน:
  · profit_exit_hold                     → tp_progress (ความคืบหน้าถึง TP ต่อไม้)
  · same_direction_cut_loss_evaluation   → loss_to_sl / status / cut_score
  · position_closed                      → net USD + กลยุทธ์
  · order_result.analysis                → ราคาเข้า/SL/TP + risk_usd (ใช้แปลงเป็น USD)

★ บทเรียนถาวร 30 ก.ย. 2026: ท่อส่งการจัดการทำงานครบ — ที่ขาดคือ "กฎ" ไม่ใช่ "กลไก"
   (ไม่มี break-even / trailing / profit-lock · cut_score ต้อง ≥0.60 ซึ่งแทบไม่เกิดจริง)
"""
import argparse
import collections
import datetime as dt
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def find_root():
    """หารากโปรเจกต์ (ที่มี work/auto_trader_audit.jsonl) โดยเดินขึ้นทีละชั้น"""
    cur = HERE
    for _ in range(6):
        cand = os.path.join(cur, 'work', 'auto_trader_audit.jsonl')
        if os.path.exists(cand):
            return cur, cand
        cur = os.path.dirname(cur)
    raise SystemExit('ไม่พบบันทึก work/auto_trader_audit.jsonl')


ROOT, AUDIT = find_root()
WANT = ('"profit_exit_hold"', 'same_direction_cut_loss_evaluation',
        '"position_closed"', '"order_result"')


def collect(hours):
    cut = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=hours)
    peak, closed, entry = {}, {}, {}
    for ln in io.open(AUDIT, encoding='utf-8', errors='replace'):
        if not any(k in ln for k in WANT):
            continue
        try:
            d = json.loads(ln)
        except Exception:
            continue
        try:
            t = dt.datetime.fromisoformat(str(d.get('time')).replace('Z', '+00:00'))
        except Exception:
            continue
        if t < cut:
            continue
        ev = d.get('event')
        if ev == 'profit_exit_hold':
            r = peak.setdefault(d.get('ticket'), {'max_tp': 0.0, 'max_l2sl': 0.0,
                                                  'checks': 0, 'reasons': collections.Counter()})
            r['checks'] += 1
            r['max_tp'] = max(r['max_tp'], float(d.get('tp_progress') or 0.0))
            r['reasons'][d.get('reason', '')] += 1
        elif ev == 'same_direction_cut_loss_evaluation':
            r = peak.setdefault(d.get('ticket'), {'max_tp': 0.0, 'max_l2sl': 0.0,
                                                  'checks': 0, 'reasons': collections.Counter()})
            r['max_l2sl'] = max(r['max_l2sl'], float(d.get('loss_to_sl') or 0.0))
            r['cut_status'] = max(int(d.get('status') or 0), r.get('cut_status', 0))
            r['sample'] = {'L': d.get('loss_to_sl'), 'C': d.get('signal_confidence'),
                           'R': d.get('reward_risk'), 'cut': d.get('cut_score')}
        elif ev == 'position_closed':
            closed[d.get('position_id')] = d
        elif ev == 'order_result':
            a = (d.get('result') or {}).get('analysis') or d.get('analysis') or {}
            oid = (d.get('result') or {}).get('order')
            if oid and a.get('risk_usd') is not None:
                entry[oid] = a
    return peak, closed, entry


def main():
    ap = argparse.ArgumentParser(description='วินิจฉัยการจัดการไม้ (ปิดกำไร/ตัดขาดทุน)')
    ap.add_argument('--hours', type=float, default=48.0, help='ย้อนหลังกี่ชั่วโมง (ค่าเริ่มต้น 48)')
    args = ap.parse_args()

    peak, closed, entry = collect(args.hours)
    rows = []
    for k, v in peak.items():
        cl = closed.get(k) or {}
        rows.append({'pos': k, 'checks': v['checks'], 'max_tp': round(v['max_tp'], 3),
                     'max_l2sl': round(v['max_l2sl'], 3), 'cut_status': v.get('cut_status', 0),
                     'net': cl.get('net'), 'strategy': cl.get('strategy'),
                     'side': cl.get('side'), 'a': entry.get(k),
                     'reasons': v['reasons'], 'sample': v.get('sample')})

    print("═══ 1) ภาพรวมการจัดการไม้ (%g ชม. ล่าสุด) ═══" % args.hours)
    print("  ไม้ที่มีร่องรอยการจัดการ : %d" % len(rows))
    print("  ไม้ที่ปิดแล้วในหน้าต่างนี้ : %d" % len(closed))
    st = collections.Counter(r['cut_status'] for r in rows)
    print("  ผลประเมินตัดขาดทุน (สูงสุดต่อไม้) : %s   [3 = สั่งตัดจริง]" % dict(sorted(st.items())))
    print("  ไม้ที่ถูกล็อกกำไร/ปิดจากกำไร : %d" % sum(1 for r in rows if r['max_tp'] > 0))

    print()
    print("═══ 2) ปิดกำไร — ไม้ที่ขึ้นไปถึงแล้วปล่อยไหลกลับ ═══")
    give = [r for r in rows if r['max_tp'] >= 0.30 and r['net'] is not None and r['net'] <= 0.10]
    print("  ไม้ที่ถึง ≥30%% ของระยะ TP แต่จบที่กำไร ≤0.10 : %d ไม้" % len(give))
    back = 0.0
    for r in give:
        est = ''
        if r['a']:
            tp_usd = float(r['a'].get('risk_usd') or 0) * 1.3
            est = ' · กำไรที่ปล่อยไป ≈ %.2f USD (โซน %.0f%% ของ TP)' % (r['max_tp'] * tp_usd, r['max_tp'] * 100)
        print("    pos %-9s สูงสุด %.0f%% ของ TP · จบ net=%s%s" % (r['pos'], r['max_tp'] * 100, r['net'], est))
        if r['net'] is not None:
            back += abs(r['net'])
    print("  รวมเงินที่คืนกลับตลาด (ค่าจริง net กลุ่มนี้) : %.2f USD" % back)

    print()
    print("═══ 3) ตัดขาดทุน — ไม้ที่ลากไปจนสุดทางโดยไม่ถูกตัด ═══")
    rode = [r for r in rows if r['max_l2sl'] >= 0.50]
    print("  ลากเกิน 50%% ของระยะ SL : %d ไม้" % len(rode))
    hard = [r for r in rode if r['max_l2sl'] >= 0.85]
    print("  ลากเกิน 85%% (เกือบชน SL เต็ม) : %d ไม้" % len(hard))
    save = 0.0
    for r in hard:
        if r['a']:
            risk = float(r['a'].get('risk_usd') or 0)
            save += risk * (1.0 - 0.65)
            print("    pos %-9s l2sl=%.2f · net=%s · risk=%.2f USD · %s → ตัดที่ 65%% ประหยัด ≈ %.2f USD"
                  % (r['pos'], r['max_l2sl'], r['net'], risk, r['strategy'], risk * 0.35))
        else:
            print("    pos %-9s l2sl=%.2f · net=%s · %s" % (r['pos'], r['max_l2sl'], r['net'], r['strategy']))
    print("  ประมาณการที่ประหยัดได้ถ้าตัดที่ 65%% ของระยะ : %.2f USD" % save)

    print()
    print("═══ 4) สถิติรายกลยุทธ์ (ให้แอดมินบอทใช้ตัดสิน TP/SL) ═══")
    by = {}
    for r in rows:
        cl = closed.get(r['pos'])
        if not cl:
            continue
        d = by.setdefault(str(r['strategy'] or 'unknown'),
                          {'trades': 0, 'wins': 0, 'net': 0.0, 'ws': [], 'ls': [],
                           'rode': 0, 'gave': 0})
        net = float(cl.get('net') or 0)
        d['trades'] += 1
        d['net'] += net
        (d['ws'] if net > 0 else d['ls']).append(net)
        if net > 0:
            d['wins'] += 1
        elif r['max_l2sl'] >= 0.85:
            d['rode'] += 1
        if r['max_tp'] >= 0.5 and net <= 0:
            d['gave'] += 1
    for k, d in sorted(by.items(), key=lambda x: -x[1]['trades']):
        aw = (sum(d['ws']) / len(d['ws'])) if d['ws'] else 0.0
        al = (sum(d['ls']) / len(d['ls'])) if d['ls'] else 0.0
        print("  %-18s ไม้=%2d ชนะ=%.0f%% สุทธิ=%+.2f เฉลี่ยชนะ=%.2f เฉลี่ยแพ้=%.2f ลากถึงSL=%d คืนกำไร=%d"
              % (k, d['trades'], 100.0 * d['wins'] / d['trades'], d['net'], aw, al, d['rode'], d['gave']))

    print()
    print("═══ 5) เกณฑ์ตัดขาดทุนที่ใช้จริง ═══")
    print("  cut_score = 0.55·L + 0.30·C + 0.15·R   → ต้อง ≥ 0.60 จึงสั่งตัด")
    s = next((r['sample'] for r in rows if r.get('sample')), None)
    if s:
        print("  ตัวอย่างจริง: L=%s C=%s R=%s → cut=%s" % (s['L'], s['C'], s['R'], s['cut']))
    print("  ⇒ ต้องมีระยะขาดทุนสูง + ความมั่นใจสูง + R:R สูงพร้อมกัน — เป็นเหตุผลที่สั่งตัดได้น้อยครั้ง")
    print()
    print("  สรุป: ท่อส่งการจัดการดี · ช่องว่างคือ 'กฎ' — ไม่มี break-even / trailing / profit-lock")


if __name__ == '__main__':
    main()
