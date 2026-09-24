# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
"""ประเมินสถานการณ์: ด่าน 3 กติกาใหม่ (เจ้าของระบบ 15 ก.ย. 2026)
   1) ผู้ชนะ = ผ่านด่าน 1+2 ฝั่งที่ pressure สูงสุด
   2) เทียบฝั่งตรงข้ามของกลยุทธ์เดิม (probability, weighted):
        - ฝั่งนั้นผ่าน 36 ค่า → พลิกไปฝั่งนั้น (flip_same)
        - ไม่ผ่าน → หากลยุทธ์อื่นฝั่งนั้นที่ผ่าน 36 ค่า → เลือกดีสุด (flip_other)
        - ไม่มีเลย → ไม่เทรด (abstain)
   จำลองผลด้วยราคา M1 จริง · SL = stop_atr×ATR · TP = reward_risk×SL · ดูผล 12 ชม.
   หมายเหตุ: ประตู net สมมติแบบปัจจุบัน (ไม่สกัดคีย์) เพื่อวัดเส้นทางด่าน 3 อย่างเดียว"""
import json, io, datetime, collections
import MetaTrader5 as mt5

STOP = {"counter_trend":1.0,"mean_reversion":1.1,"breakout":1.25,"range":1.0,"trend":1.2,"breakout_reversal":1.0}
CFG = json.load(io.open('outputs/mt5_python_bridge/auto_config.json', encoding='utf-8'))
SR = CFG['strategy_router']
GOV = SR['bounded_live']['governance']
RR = float(SR.get('reward_risk') or SR.get('range_reward_risk') or 1.4)

def band36(st, sd, raw, pr, w):
    g = GOV.get(st) or {}
    def fk(k, d):
        v = g.get(k); return float(v) if isinstance(v, (int, float)) else d
    return (raw >= fk(f'raw_{sd}', 0) and raw <= fk(f'raw_max_{sd}', 1)
            and pr >= fk(f'probability_{sd}', 0) and pr <= fk(f'probability_max_{sd}', 1)
            and w >= fk(f'weighted_{sd}', 0) and w <= fk(f'weighted_max_{sd}', 1))

rounds = []
for l in io.open('work/auto_trader_audit.jsonl', encoding='utf-8'):
    try: e = json.loads(l)
    except Exception: continue
    d = ((e.get('analysis') or {}).get('router_decision') or {}).get('bounded_live_diagnostics') or []
    if not d: continue
    try: t = datetime.datetime.fromisoformat(str(e['time']).replace('Z', '+00:00'))
    except Exception: continue
    rounds.append((t, d))
rounds = rounds[-600:]
print("รอบที่รีเพลย์:", len(rounds), "|", str(rounds[0][0])[:16], "->", str(rounds[-1][0])[:16])

mt5.initialize()
def sim(t, st, sd, rr=RR):
    r = mt5.copy_rates_range('XAUUSD.sml', mt5.TIMEFRAME_M1, t.replace(tzinfo=None),
                             (t + datetime.timedelta(hours=12)).replace(tzinfo=None))
    if r is None or len(r) < 5: return None
    entry = float(r[0]['close'])
    tr = [abs(float(r[i]['high']) - float(r[i]['low'])) for i in range(1, min(21, len(r)))]
    atr = sum(tr) / len(tr) if tr else 1.0
    risk = atr * STOP.get(st, 1.0); rew = risk * rr
    sl, tp = (entry - risk, entry + rew) if sd == 'buy' else (entry + risk, entry - rew)
    for b in r[1:]:
        hi, lo = float(b['high']), float(b['low'])
        hs = lo <= sl if sd == 'buy' else hi >= sl
        ht = hi >= tp if sd == 'buy' else lo <= tp
        if hs and ht: return -1.0
        if hs: return -1.0
        if ht: return rr
    return None

tal = collections.defaultdict(lambda: dict(n=0, w=0, r=0.0))
dec = collections.Counter()
for t, d in rounds:
    ent = []
    for g in d:
        st, sd = g.get('strategy'), g.get('side')
        if not st or sd not in ('buy', 'sell'): continue
        raw = float(g.get('raw_score') or 0); pr = float(g.get('probability') or 0); w = float(g.get('weighted_score') or 0)
        ok36 = band36(st, sd, raw, pr, w)
        if ok36: ent.append((pr, w, sd, st))
    if not ent: continue
    ent.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top4 = ent[:4]
    bp = sum(p*s for p, s, sd, st in top4 if sd == 'buy'); sp = sum(p*s for p, s, sd, st in top4 if sd == 'sell')
    pref = 'buy' if bp > sp else ('sell' if sp > bp else max(top4, key=lambda x: x[1])[2])
    side_ent = [x for x in ent if x[2] == pref]
    if not side_ent: continue
    p_w, s_w, side_w, strat_w = side_ent[0]
    other = 'sell' if side_w == 'buy' else 'buy'
    o_in = [x for x in ent if x[2] == other and x[3] == strat_w]
    o_more = bool(o_in) and (o_in[0][0], o_in[0][1]) > (p_w, s_w)
    if not o_more:
        dec['keep'] += 1; continue
    if o_in:
        dec['flip_same'] += 1
        st, sd = strat_w, other; rr = RR
    else:
        alts = sorted([x for x in ent if x[2] == other and x[3] != strat_w], key=lambda x: (x[0], x[1]), reverse=True)
        if alts:
            dec['flip_other'] += 1
            st, sd = alts[0][3], other; rr = RR
        else:
            dec['abstain'] += 1; continue
    v = sim(t, st, sd, rr)
    if v is None: continue
    key = 'flip_same' if dec['flip_same'] else 'flip_other'
    for kk in (sd + '_' + st, sd + '_รวม', 'รวมทั้งหมด'):
        tal[kk]['n'] += 1; tal[kk]['r'] += v; tal[kk]['w'] += 1 if v > 0 else 0
mt5.shutdown()
print("\n=== ผลตัดสินตามกติกาด่าน 3 ใหม่ (600 รอบล่าสุด) ===")
for k in ('keep', 'flip_same', 'flip_other', 'abstain'):
    print("  %-11s %d รอบ" % (k, dec[k]))
print("\n=== ผลจำลอง (ราคาจริง M1) ===")
print("%-24s %5s %8s %10s %10s" % ("กลุ่ม", "n", "win%", "net R", "R/ไม้"))
for k in sorted(tal, key=lambda x: -tal[x]['n']):
    dd = tal[k]
    if dd['n'] >= 3:
        print("%-24s %5d %7.1f%% %+10.2f %+10.3f" % (k, dd['n'], 100.0*dd['w']/dd['n'], dd['r'], dd['r']/dd['n']))
