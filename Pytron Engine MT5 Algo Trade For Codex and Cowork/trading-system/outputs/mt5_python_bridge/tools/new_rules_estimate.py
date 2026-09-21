# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ประมาณสถานการณ์: รีเพลย์รอบจริงด้วย "กติกาใหม่"
#   หน้าต่าง 180 · prob=p25 ตามค่าจริง · พื้นความกว้าง 0.10 · ยกพื้นไม้สวนแนวโน้ม +0.05
import json, io, datetime, collections
import MetaTrader5 as mt5
WIN=180; MINW=0.10; STEP=0.06; MARGIN=0.05

def rows(p):
    for l in io.open(p,encoding='utf-8'):
        try: yield json.loads(l)
        except Exception: pass

recs=[]
for e in rows('work/auto_trader_audit.jsonl'):
    d=((e.get('analysis') or {}).get('router_decision') or {}).get('bounded_live_diagnostics') or []
    if not d: continue
    try: t=datetime.datetime.fromisoformat(str(e['time']).replace('Z','+00:00'))
    except Exception: continue
    ent={}
    for g in d:
        if g.get('stage')=='1_side_net': continue
        k=f"{g.get('strategy')}_{g.get('side')}"
        ent[k]=dict(raw=float(g.get('raw_score') or 0), prob=float(g.get('probability') or 0),
                    w=float(g.get('weighted_score') or 0), passed=bool(g.get('passed')))
    deferred={f"{g.get('strategy')}_{g.get('side')}" for g in d if g.get('blocked_by')=='side_net_gate'}
    recs.append((t,ent,deferred))
print("รอบที่รีเพลย์:", len(recs), "|", str(recs[0][0])[:16], "→", str(recs[-1][0])[:16])

mt5.initialize()
tcache={}
def h1(t):
    key=t.strftime('%Y-%m-%d %H')
    if key in tcache: return tcache[key]
    f=(t-datetime.timedelta(hours=36)).replace(tzinfo=None)
    r=mt5.copy_rates_range('XAUUSD.sml',mt5.TIMEFRAME_H1,f,t.replace(tzinfo=None))
    v=None
    if r is not None and len(r)>=20:
        cl=[float(x['close']) for x in r][-20:]
        v='up' if cl[-1]>sum(cl)/len(cl) else 'down'
    tcache[key]=v; return v

hist=collections.defaultdict(list)
lo={}; hi={}; plo={}; wlo={}; whi={}
new=0; old=0; both=0; n=0; byhour=collections.Counter(); new_only=0
for t,ent,defr in recs:
    n+=1
    tr=h1(t)
    ok_new=False; ok_old=False
    for k,v in ent.items():
        h=hist[k]
        h.append(v)
        hw=h[-WIN-1:-1]
        if len(hw)>=30:
            s=sorted(x['raw'] for x in hw)
            pl=lambda q: s[min(len(s)-1,int(q*(len(s)-1)))]
            tgt_lo, tgt_hi = pl(0.60), max(pl(0.90), pl(0.60)+MINW)
            sw=sorted(x['w'] for x in hw); pw=lambda q: sw[min(len(sw)-1,int(q*(len(sw)-1)))]
            tgt_wlo, tgt_whi = pw(0.60), max(pw(0.90), pw(0.60)+MINW)
            sp=sorted(x['prob'] for x in hw); tgt_p=max(0.50,min(0.90,sp[int(0.25*(len(sp)-1))]))
            for store,tgt in ((lo,tgt_lo),(hi,tgt_hi),(wlo,tgt_wlo),(whi,tgt_whi),(plo,tgt_p)):
                cur=store.get(k,tgt); store[k]=max(cur-STEP,min(cur+STEP,tgt))
        if k not in lo: continue
        cd = bool(tr) and ((k.endswith('_buy') and tr=='down') or (k.endswith('_sell') and tr=='up'))
        g_raw = lo[k]+(min(MARGIN,0.8*(hi[k]-lo[k])) if cd else 0.0)
        g_p   = plo[k]+(min(MARGIN,0.8*(0.90-plo[k])) if cd else 0.0)
        g_w   = wlo[k]+(min(MARGIN,0.8*(whi[k]-wlo[k])) if cd else 0.0)
        if (v['raw']>=g_raw and v['prob']>=g_p and v['w']>=g_w
                and v['raw']<=hi[k] and v['w']<=whi[k] and k not in defr):
            ok_new=True
        if v['passed']: ok_old=True
    if ok_new: new+=1; byhour[t.hour]+=1
    if ok_old: old+=1
    if ok_new and ok_old: both+=1
    if ok_new and not ok_old: new_only+=1
mt5.shutdown()
print("\n=== ประมาณสถานการณ์ (รอบเดียวกัน · เทียบกติกาเดิมกับใหม่) ===")
print("  กติกาเดิม (ที่ระบบใช้จริง): เทรดได้ %d รอบ = %.1f%%  ≈ %.0f รอบ/วัน" % (old,100.0*old/n,1440.0*old/n))
print("  กติกาใหม่ (ที่เพิ่งตั้ง):    เทรดได้ %d รอบ = %.1f%%  ≈ %.0f รอบ/วัน" % (new,100.0*new/n,1440.0*new/n))
print("  ตรงกัน: %d รอบ · ใหม่เพิ่มขึ้น: %d รอบ (%.1f เท่า)" % (both,new_only,(new/max(1,old))))
print("  ชั่วโมง UTC ที่เทรดได้ (กติกาใหม่):", dict(sorted(byhour.items())))