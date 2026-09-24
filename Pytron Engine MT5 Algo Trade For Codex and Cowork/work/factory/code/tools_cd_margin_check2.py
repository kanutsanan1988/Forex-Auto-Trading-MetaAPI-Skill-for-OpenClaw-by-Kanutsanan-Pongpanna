# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ: Kanutsanan Pongpanna — facebook.com/LoveMoneyTH
# ตรวจ: ยกพื้นไม้สวนแนวโน้ม (+0.05) ทำให้ "รอบที่เทรดได้" หายไปไหม — ใช้ band ปัจจุบัน + คะแนนจริง
import json, io, datetime
import MetaTrader5 as mt5
MARGIN=0.05
cfg=json.load(io.open('outputs/mt5_python_bridge/auto_config.json',encoding='utf-8'))
gov=cfg['strategy_router']['bounded_live']['governance']
cd_cfg=cfg['strategy_router']['bounded_live'].get('counter_direction') or {}
MARGIN=float(cd_cfg.get('margin',0.05)); ON=bool(cd_cfg.get('enabled',False))
print("counter_direction:", ON, "margin", MARGIN)
def band(st,side):
    g=gov.get(st) or {}
    def f(k,d): 
        v=g.get(k); return float(v) if isinstance(v,(int,float)) else d
    return f(f'raw_{side}',0), f(f'raw_max_{side}',1), f(f'probability_{side}',0), f(f'probability_max_{side}',1), f(f'weighted_{side}',0), f(f'weighted_max_{side}',1)
rounds=[]
for l in io.open('work/auto_trader_audit.jsonl',encoding='utf-8'):
    try: e=json.loads(l)
    except Exception: continue
    d=((e.get('analysis') or {}).get('router_decision') or {}).get('bounded_live_diagnostics') or []
    if d: rounds.append((e.get('time'),d))
rounds=rounds[-300:]
mt5.initialize()
def h1(sym,t):
    f=(t-datetime.timedelta(hours=36)).replace(tzinfo=None)
    r=mt5.copy_rates_range(sym,mt5.TIMEFRAME_H1,f,t.replace(tzinfo=None))
    if r is None or len(r)<20: return None
    cl=[float(x['close']) for x in r][-20:]
    return 'up' if cl[-1]>sum(cl)/len(cl) else 'down'
before=after=0; cd_before=cd_after=0; cd_n=0; tot_n=0
for t,d in rounds:
    try: tt=datetime.datetime.fromisoformat(str(t).replace('Z','+00:00'))
    except Exception: continue
    tr=h1('XAUUSD.sml',tt)
    if tr is None: continue
    okb=oka=False
    for g in d:
        if g.get('stage')=='1_side_net': continue
        st=g.get('strategy'); sd=g.get('side')
        if not st or sd not in ('buy','sell'): continue
        rlo,rhi,plo,phi,wlo,whi=band(st,sd)
        raw=float(g.get('raw_score') or 0); pr=float(g.get('probability') or 0); w=float(g.get('weighted_score') or 0)
        b = (raw>=rlo and pr>=plo and w>=wlo and raw<=rhi and pr<=phi and w<=whi)
        is_cd=(sd=='buy' and tr=='down') or (sd=='sell' and tr=='up')
        def eff(lo,hi):
            return lo+min(MARGIN,0.8*(hi-lo)) if hi>lo else lo+MARGIN
        a = b and (not is_cd or (raw>=eff(rlo,rhi) and pr>=eff(plo,phi) and w>=eff(wlo,whi)))
        tot_n+=1
        if is_cd: cd_n+=1
        okb = okb or b; oka = oka or a
        if is_cd:
            cd_before += 1 if b else 0; cd_after += 1 if a else 0
    before += 1 if okb else 0; after += 1 if oka else 0
mt5.shutdown()
n=len(rounds)
print("\n=== %d รอบล่าสุด ===" % n)
print("  รอบที่มีคีย์ผ่าน (เทรดได้): ก่อน %d รอบ → ยกพื้นแล้ว %d รอบ  (หาย %d รอบ)" % (before, after, before-after))
print("  คีย์สวนแนวโน้มที่ผ่าน: ก่อน %d/%d → หลัง %d/%d" % (cd_before, cd_n, cd_after, cd_n))
