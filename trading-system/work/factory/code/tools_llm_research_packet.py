# -*- coding: utf-8 -*-
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



def jev_marks(recent=None, internal=None, cfg=None):
    """★ Jev (TypeSafe System One · 23 ก.ย. 2026): ประเมินแบบสอบเทียบให้บอทโหมด 2 ใช้ประกอบดุลยพินิจ

    Jev = โมเดลตัดสินใจแบบพิมพ์ (ไม่สร้างข้อความ) — ตอบเป็นความน่าจะเป็นที่สอบเทียบแล้ว
    เจ้าของระบบกำหนด: "ส่วนไหนที่สามารถใช้ jev ai ช่วยงานได้ก็ใช้ได้"
    """
    try:
        tools_dir = os.path.join(BR, 'tools')
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import jev
        out = {'model': jev.load_config().get('model'), 'context': 'mode2'}
        # (1) ข่าวภายนอก
        if news_feed is not None:
            d = news_feed.jev_analysis(context='mode2')
            if d:
                out['news'] = d
        # (2) ข้อมูลสัญญาณภายใน — เจ้าของระบบกำหนด: Jev ดูแล 'ข้อมูลภายใน' ด้วย ไม่ใช่แค่ข่าว
        ats = (internal or {}).get('auto_threshold_stats') or {}
        mechs = ats.get('mechanisms') or ats.get('by_mechanism') or ats.get('mechanism_stats') or {}
        state = {
            'performance': dict(recent or {}),
            'settings': current_values(cfg or {}),
            'mechanisms': [{'name': k, 'note': 'กลไกในระบบ (จากสถิติภายใน)'} for k in list(mechs)[:8]],
            'news_digest': (out.get('news') or {}).get('direction') or '',
            'other_bot': other_bot(3),
        }
        r = jev.ask_preset('internal', state, context='mode2')
        if r.get('ok'):
            out['internal'] = {'derived': r.get('derived'),
                               'summary': jev._summary(r.get('answers') or {}),
                               'latency_ms': r.get('latency_ms')}
        out['how_to_use'] = (
            "Jev ใช้เพิ่มได้เองตามดุลยพินิจของบอท (พรีเซ็ต: news · rec-check · admin-safety · regime)\n"
            "  .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\jev.py --preset rec-check --state <state.json>\n"
            "  .venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\jev.py --selftest\n"
            "  -> ใช้ตรวจคำแนะนำก่อนส่ง: 'ตรงหลักฐานไหม · เป็นการไล่ราคาไหม · ตัวเลขตรงไหม' (derived.pass/warnings)\n"
            "  -> ข้อมูลภายใน (derived.healthy/watch/next_action) · ข่าว (derived.news_score/direction)\n"
            "  (Jev ทำงานเฉพาะกับบอทโหมด 2 และแอดมินบอท — สคริปต์อื่นเรียกไม่ได้)"
        )
        return out
    except Exception as exc:
        return 'Jev ใช้งานไม่ได้: %s' % exc


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


def interbot_digest(role='mode2'):
    """★ เพิ่ม 23 ก.ย. 2026: กล่องปรึกษาระหว่างบอท 2 ตัว (ฝากคำถาม–ตอบข้ามรอบ)

    เจ้าของระบบกำหนด: "บอททั้ง 2 ตัวคุยกันปรึกษากันได้"
    ออกแบบเป็น async + มีโครงสร้าง เพราะรอบของ 2 บอทไม่พร้อมกัน (10 นาที / 30 นาที)
    """
    try:
        tools_dir = os.path.join(BR, 'tools')
        if tools_dir not in sys.path:
            sys.path.insert(0, tools_dir)
        import interbot
        exe = '.venv\\Scripts\\python.exe outputs\\mt5_python_bridge\\tools\\interbot.py'
        return {
            'text': interbot.digest(role),
            'stats': interbot.stats(),
            'how_to_use': (
                'ถามบอทอีกตัว (ฝากไว้ — รอบถัดไปของอีกฝ่ายจะเห็น):\n  ' + exe +
                ' ask --from mode2 --to admin --topic <หัวข้อ> --question <คำถาม> [--payload {...}]\n'
                'ตอบคำถามที่ค้างอยู่:\n  ' + exe +
                ' answer --from mode2 --ask-id <id> --stance agree|disagree|unsure|need_more_data '
                '--answer <เหตุผล + ตัวเลขจริง>\n'
                'กติกา: คำตอบ = ข้อมูลประกอบเท่านั้น · ใช้ตัวเลขจริงตัดสินเอง · ห้ามแตะคีย์สงวน/ตัวเทรด/kill switch'
            ),
        }
    except Exception as exc:
        return {'text': 'กล่องปรึกษาใช้งานไม่ได้: %s' % exc}


def other_bot(limit=3):
    """★ เพิ่ม 23 ก.ย. 2026: บอทอีกตัว (แอดมินบอท) — รอบหลัง ๆ ที่ปรับค่าจริง (ให้ 2 บอท 'รู้เห็นกัน')"""
    out = {'rounds': [], 'note': 'รอบของแอดมินบอท (ผู้วิวัฒน์ค่า/โครงสร้าง) — ดูไม่ให้เสนอสวนกันเอง'}
    try:
        rows = [json.loads(l) for l in io.open(os.path.join(WORK, 'admin_bot_log.jsonl'),
                                               encoding='utf-8') if l.strip()]
    except Exception:
        rows = []
    for r in rows[-int(limit):]:
        jev = r.get('jev') or {}
        out['rounds'].append({
            'time': r.get('time'), 'mode': r.get('mode'),
            'changes': [{'key': c.get('key'), 'from': c.get('from'), 'to': c.get('to')}
                        for c in (r.get('changes') or [])],
            'jev_values_safe': ((jev.get('values') or {}).get('derived') or {}).get('safe'),
            'jev_structure_safe': ((jev.get('structure') or {}).get('derived') or {}).get('safe'),
        })
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
    recent_stats = scan(3)
    internal_block = internal_research()
    packet = {
        'schema': 'hermes-trading-research-packet-v1',
        'created': now_utc().isoformat(timespec='seconds'),
        'system': {'equity': eq, 'balance': bal, 'open_positions': npos},
        'recent': recent_stats,
        'settings_now': current_values(cfg),
        # ★ ทำงานร่วมกัน: ผลงานวิจัย 10 นาทีจาก 'ข้อมูลภายใน' ต้องอยู่ในชุดข้อมูลของบอทเสมอ
        'internal_research': internal_block,
        # ★ เพิ่ม 23 ก.ย. 2026 (เจ้าของระบบถามเรื่อง 'ความจำข้ามรอบ'): ปิดวงจร —
        #   บอทต้องเห็น 'สิ่งที่ตัวเองเสนอรอบก่อน' + 'ผลที่เกิดขึ้นจริง' ก่อนเสนอรอบใหม่
        #   (latest = รอบล่าสุดที่เขียน · applied = ที่ระบบนำไปใช้แล้ว · failed = ที่ใช้ไม่ได้)
        'last_recommendation': last_recommendation(),
        # ★ เพิ่ม 23 ก.ย. 2026: กล่องปรึกษาระหว่างบอท (เจ้าของระบบ: "บอททั้ง 2 ตัวคุยกันปรึกษากันได้")
        'interbot': interbot_digest('mode2'),
        'other_bot': other_bot(3),
        'round_memory': {
            'ไฟล์ความจำข้ามรอบ (อ่านเพิ่มได้เอง)': {
                'คำแนะนำล่าสุด/ผลการใช้งาน': 'research/recommendations/latest_recommendation.json · last_applied.json · last_failed.json',
                'ประวัติงานวิจัยข่าว': 'work/news_research_history.jsonl',
                'ชุดข้อมูลรอบก่อน ๆ ของบอท': 'work/llm_research/inbox/packet_*.json (40 รอบล่าสุด)',
                'บันทึกการร่วมงาน Jev': 'work/jev_audit.jsonl',
            },
            'หลักการ': ('บอทแต่ละรอบเป็น "รอบใหม่" ที่จำได้จาก (1) ผลรอบก่อนของตัวเอง '
                        '(ความต่อเนื่องข้ามรอบของงาน cron) (2) ไฟล์ความจำในระบบ (3) ตัวเลขจริงจาก audit — '
                        'ไม่ใช่จากบทสนทนา'),
        },
        # ★ เพิ่ม 19 ก.ย. 2026 (เจ้าของระบบกำหนด): งานวิจัย 10 นาทีโหมด 2 ต้องประมวลผล 'ข่าวล่าสุด' ด้วย
        'news': (news_feed.digest(max_items=8, hours=12, jev_context='mode2')
                 if news_feed else 'ข่าว: โมดูล news_feed ใช้งานไม่ได้'),
        # ★ เพิ่ม 23 ก.ย. 2026: ผลประเมินแบบสอบเทียบด้วย Jev (ข่าว) ให้บอทใช้ประกอบดุลยพินิจ
        'jev': jev_marks(recent_stats, internal_block, cfg),
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
