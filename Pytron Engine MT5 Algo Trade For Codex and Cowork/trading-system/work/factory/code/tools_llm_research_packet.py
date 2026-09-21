# -*- coding: utf-8 -*-
# Python Qaunt Trading + AI(LLM) Live Research
# อัพเดทใหญ่เพิ่มความฉลาดและความรอบคอบเข้าสู่ระดับผู้ทรงภูมิปัญญา
# เทรดในไทยมีกฎหมายรองรับ 100%
# Settrade e-Open Account · MTS Gold Futures + MT5
# https://oacc.settrade.com/e-open-account/landing?brokerId=060&openExternalBrowser=1&utm_source=chatgpt.com
# ผู้สร้างระบบ (Creator): Kanutsanan Pongpanna — facebook.com/LoveMoneyTH / youtube.com/@lovemoneythofficial
# โปรดเก็บเครดิตผู้สร้างไว้ในทุกไฟล์และทุกส่วนของระบบ — ห้ามลบ
"""ชุดข้อมูลวิจัย 10 นาที (ส่วน LLM) — แบบ "บอทดูแล LLM เป็นสมองอีกชั้น"

แนวคิด (เจ้าของระบบกำหนด 19 ก.ย. 2026):
  • เดิม: สคริปต์ต่อ OpenRouter ตรง ๆ
  • ใหม่: สคริปต์นี้ "เตรียมข้อมูล" เท่านั้น (ไม่เรียก LLM เลย)
          → บอท AI (Hermes / Codex / Claude Code / Cursor ฯลฯ) เป็นผู้อ่านแล้วใช้ LLM เป็นสมอง
          → บอทเขียนคำแนะนำตาม schema hermes-trading-recommendation-v1
          → ตัว consumer (ทุก 5 นาที) นำไปใช้กับระบบเทรดตามกรอบที่อนุญาต

ใช้:
  python llm_research_packet.py           → สร้างชุดข้อมูล + สรุปให้บอทอ่าน
  python llm_research_packet.py --print   → พิมพ์ชุดข้อมูลล่าสุดเป็นข้อความ
"""
import io, os, sys, json, glob, datetime, collections

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BR = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
WORK = os.path.join(ROOT, 'work')
INBOX = os.path.join(WORK, 'llm_research', 'inbox')
AUDIT = os.path.join(WORK, 'auto_trader_audit.jsonl')
CFG = os.path.join(BR, 'auto_config.json')
OUT = os.path.join(ROOT, 'research', 'recommendations')

# ★ เพิ่ม 19 ก.ย. 2026: งานวิจัย 10 นาทีโหมด 2 ต้องประมวลผล 'ข่าวล่าสุด' ด้วย
if BR not in sys.path:
    sys.path.insert(0, BR)
try:
    import news_feed
except Exception:
    news_feed = None


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def scan(hours=3):
    cut = now_utc() - datetime.timedelta(hours=hours)
    closed, rounds, blocks, signals = [], 0, collections.Counter(), collections.Counter()
    with io.open(AUDIT, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if '"event"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            try:
                t = datetime.datetime.fromisoformat(str(e.get('time')).replace('Z', '+00:00'))
            except Exception:
                continue
            if t < cut:
                continue
            ev = e.get('event')
            if ev == 'position_closed':
                closed.append({'net': float(e.get('net') or 0), 'strategy': e.get('strategy')})
            elif ev == 'no_trade':
                rounds += 1
                d = e.get('diagnostics') or {}
                for key in ('blocked_by', 'reason'):
                    v = d.get(key) or e.get('reason')
                    if isinstance(v, str) and v:
                        blocks[v[:60]] += 1
            elif ev == 'order_result':
                a = e.get('analysis') or {}
                if a.get('strategy'):
                    signals['%s/%s' % (a.get('strategy'), a.get('side'))] += 1
    wins = [c['net'] for c in closed if c['net'] > 0]
    losses = [c['net'] for c in closed if c['net'] < 0]
    return {
        'window_hours': hours,
        'trades': len(closed), 'net': round(sum(c['net'] for c in closed), 3),
        'win_rate': round(100.0 * len(wins) / len(closed), 1) if closed else 0.0,
        'avg_win': round(sum(wins) / len(wins), 3) if wins else 0.0,
        'avg_loss': round(sum(losses) / len(losses), 3) if losses else 0.0,
        'by_strategy': dict(collections.Counter(c['strategy'] for c in closed if c['strategy'])),
        'no_trade_rounds': rounds,
        'top_blocks': dict(blocks.most_common(5)),
        'signals_seen': dict(signals.most_common(8)),
    }


def equity():
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            a = mt5.account_info()
            pos = mt5.positions_get() or []
            mt5.shutdown()
            return (float(a.equity), float(a.balance), len(pos)) if a else (None, None, None)
    except Exception:
        pass
    return (None, None, None)


def current_values(cfg):
    def g(path, default=None):
        cur = cfg
        for part in path.split('.'):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur
    return {
        'profit_exit.no_signal_tp_fraction': g('profit_exit.no_signal_tp_fraction'),
        'side_net_gate.max_age_hours': g('side_net_gate.max_age_hours'),
        'revenge_guard': g('revenge_guard'),
        'early_cut': g('early_cut'),
        'min_reward_risk': g('min_reward_risk'),
        'max_risk_pct': g('max_risk_pct'),
        'band_min_widths': g('strategy_router.auto_threshold.band_min_widths'),
        'window_records': g('strategy_router.auto_threshold.window_records'),
        'trading_mode': g('trading_mode') or 'internal_only',
    }


def internal_research():
    """★ ดึงผลงานวิจัย 10 นาที 'ข้อมูลภายใน' มาร่วมในชุดข้อมูลของบอท (ทำงานร่วมกัน)"""
    out = {}
    try:
        stats = json.load(io.open(os.path.join(ROOT, 'research', 'auto-threshold-stats', 'latest.json'), encoding='utf-8'))
        out['auto_threshold_stats'] = stats
    except Exception:
        out['auto_threshold_stats'] = None
    try:
        logp = os.path.join(ROOT, 'research', 'consolidated-research-log.md')
        txt = io.open(logp, encoding='utf-8', errors='ignore').read()
        out['internal_report_tail'] = txt[-1800:]
    except Exception:
        out['internal_report_tail'] = None
    return out


def last_recommendation():
    """คำแนะนำล่าสุดจากบอท (ปิดวงจร: บอทเห็นสิ่งที่ตัวเองเพิ่งเสนอ + สิ่งที่ถูกนำไปใช้จริง)"""
    out = {}
    for name, key in (('latest_recommendation.json', 'latest'), ('last_applied.json', 'applied'),
                      ('last_failed.json', 'failed')):
        try:
            out[key] = json.load(io.open(os.path.join(OUT, name), encoding='utf-8'))
        except Exception:
            out[key] = None
    return out


def main():
    if '--print' in sys.argv:
        files = sorted(glob.glob(os.path.join(INBOX, 'packet_*.json')))
        if not files:
            print('ยังไม่มีชุดข้อมูล — รันโดยไม่ใส่ --print เพื่อสร้าง')
            return
        print(io.open(files[-1], encoding='utf-8').read())
        return
    cfg = {}
    try:
        cfg = json.load(io.open(CFG, encoding='utf-8'))
    except Exception:
        pass
    eq, bal, npos = equity()
    packet = {
        'schema': 'hermes-trading-research-packet-v1',
        'created': now_utc().isoformat(timespec='seconds'),
        'system': {'equity': eq, 'balance': bal, 'open_positions': npos},
        'recent': scan(3),
        'settings_now': current_values(cfg),
        # ★ ทำงานร่วมกัน: ผลงานวิจัย 10 นาทีจาก 'ข้อมูลภายใน' ต้องอยู่ในชุดข้อมูลของบอทเสมอ
        'internal_research': internal_research(),
        # ★ เพิ่ม 19 ก.ย. 2026 (เจ้าของระบบกำหนด): งานวิจัย 10 นาทีโหมด 2 ต้องประมวลผล 'ข่าวล่าสุด' ด้วย
        'news': (news_feed.digest(max_items=8, hours=12) if news_feed else 'ข่าว: โมดูล news_feed ใช้งานไม่ได้'),
        # ★ ประวัติงานวิจัยข่าว: บอทเป็นผู้เลือกว่าจะดึงช่วงใดมาประมวลผลร่วมกับข่าวปัจจุบัน
        'news_history_hint': (
            """ประวัติงานวิจัยข่าวเก็บที่ work/news_research_history.jsonl (JSONL · 1 บรรทัด = 1 รอบวิจัย)
ดึงช่วงใดก็ได้ตามดุลพินิจของบอท:
  .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\news_feed.py --history --hours <N>
  .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\news_feed.py --history --since <ISO> --until <ISO>
คำตอบมี: ทิศทางล่าสุด · ธีมสะสมตลอดช่วง · ข่าวเด่นสะสม (ไม่ซ้ำหัวข้อ)"""
            if news_feed else 'ข่าว: โมดูล news_feed ใช้งานไม่ได้'),
        'asks': [
            'ระบบควรปรับค่าอะไรเพื่อทำกำไรดีขึ้นในจังหวะนี้ (อ้างตัวเลขจริง)',
            'มีกลไกไหนที่ทำให้พลาดโอกาสหรือขาดทุนซ้ำ ๆ หรือไม่',
            'ข้อเสนอต้องอยู่ในกรอบปลอดภัย (ค่าต่างๆ ไม่แตะโครงสร้างโค้ด)',
            'ต้องอ้างอิงผลงานวิจัยข้อมูลภายใน (internal_research) ร่วมกับตัวเลขจาก audit เสมอ',
            'ต้องพิจารณาข่าวล่าสุด (news) ด้วย — ข่าวมหภาค/ดอกเบี้ย/ดอลลาร์/ภูมิรัฐศาสตร์ มีผลกับทองคำ',
            'ประวัติงานวิจัยข่าวมีให้ดึงได้ (news_history_hint) — จะดึงช่วงไหนมาประมวลผลร่วมกับข่าวปัจจุบันหรือไม่ ขึ้นกับดุลพินิจของบอท',
            'ถ้าข้อเสนอก่อนหน้าถูกนำไปใช้แล้ว ให้บอกว่าผลเป็นอย่างไร (ดู bot_loop)',
        ],
        'goal': (
                'เป้าหมายสูงสุด (เจ้าของระบบกำหนด): ทำกำไรสูงสุด ให้ได้เร็วและมากที่สุด — '
                'ทำทุกวิถีทางภายในกรอบปลอดภัย · ตัดสิ่งที่ไม่ทำกำไร · เพิ่มน้ำหนักสิ่งที่ทำกำไร · '
                'ใช้ตัวเลขจริงเป็นหลักฐานทุกครั้ง (ห้ามเดา) · ห้ามแตะคีย์สงวน/ตัวเทรด/kill switch/โครงสร้างโค้ด'
            ),
            'output_contract': {
            'schema': 'hermes-trading-recommendation-v1',
            # ★ เจ้าของระบบกำหนด 19 ก.ย. 2026: เขียนลงไฟล์นี้ไฟล์เดียว (consumer อ่านไฟล์นี้)
            'write_to': 'research/recommendations/latest_recommendation.json',
            'note': 'บอทเป็นผู้เขียน (ใช้ LLM เป็นสมอง) — consumer ทุก 5 นาทีจะนำไปใช้',
        },
    }
    os.makedirs(INBOX, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    stamp = now_utc().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(INBOX, 'packet_%s.json' % stamp)
    io.open(path, 'w', encoding='utf-8').write(json.dumps(packet, ensure_ascii=False, indent=2))
    # เก็บย้อนหลังไม่เกิน 40 ไฟล์
    files = sorted(glob.glob(os.path.join(INBOX, 'packet_*.json')))
    for old in files[:-40]:
        try:
            os.remove(old)
        except Exception:
            pass
    r = packet['recent']
    print('=== ชุดข้อมูลวิจัย 10 นาที (บอทดูแล) ===')
    print('ไฟล์:', os.path.relpath(path, ROOT))
    print('3 ชม.ล่าสุด: ไม้ %d | win %.1f%% | net $%+.2f | เฉลี่ยชนะ $%+.3f / แพ้ $%+.3f' % (
        r['trades'], r['win_rate'], r['net'], r['avg_win'], r['avg_loss']))
    print('รอบไม่เทรด: %d | equity $%s | ไม้เปิด %s' % (r['no_trade_rounds'], eq, npos))
    print('บอทอ่านไฟล์นี้ → คิดด้วย LLM ของบอท → เขียนคำแนะนำลง research/recommendations/')


if __name__ == '__main__':
    main()
