# -*- coding: utf-8 -*-
"""ระบบ "admin bot agent intelligence automate skill" — รอบแอดมินวิวัฒน์ตัวเอง

เจ้าของระบบกำหนด (19 ก.ย. 2026):
  • ให้บอท AI (เช่น Hermes) ดูแลเป็นรอบ — เลือกได้ 30 นาที / 1 ชั่วโมง
  • วิวัฒน์ได้ทั้ง "ค่าต่างๆ" และ "โครงสร้างของสกิล" — ภายใต้กรอบปลอดภัยที่ตั้งไว้
  • ต้องมีค่าโรงงานสำรองกดคืนได้ทุกเมื่อ (work/factory/) + คืนค่าเดิมอัตโนมัติถ้าผลแย่ลง

ใช้:
  python admin_bot_round.py                      → โหมดแนะนำ (advisory)
  python admin_bot_round.py --apply              → ปรับค่าจริง (กรอบค่า)
  python admin_bot_round.py --apply --allow-structure   → ปรับได้ทั้งค่าและโครงสร้าง
  python admin_bot_round.py --interval 30        → ตั้งรอบดูแล 30 นาที
"""
import io, os, sys, json, glob, datetime, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ★ เขียนไฟล์แบบ atomic (แก้ 19 ก.ย. 2026): เดิม json.dump(io.open(...)) เขียนทับตรง ๆ
#   ถ้าโปรเซสตายกลางคัน ไฟล์ config ที่ระบบกำลังใช้จะถูกตัดครึ่ง
_BRIDGE = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
if _BRIDGE not in sys.path:
    sys.path.insert(0, _BRIDGE)
try:
    from runtime_support import atomic_json as _atomic_json
except Exception:
    _atomic_json = None

# ★ เพิ่ม 19 ก.ย. 2026 (เจ้าของระบบกำหนด): แอดมินบอทต้องประมวลผล 'ข่าวล่าสุด' ร่วมด้วย
try:
    import news_feed
except Exception:
    news_feed = None


def interbot_box(role='admin'):
    """★ เพิ่ม 23 ก.ย. 2026: กล่องปรึกษาระหว่างบอท (ฝากคำถาม–ตอบข้ามรอบ)"""
    try:
        import interbot
        return {'text': interbot.digest(role), 'stats': interbot.stats()}
    except Exception as exc:
        return {'text': 'กล่องปรึกษาใช้งานไม่ได้: %s' % exc}


def other_bot_state():
    """★ เพิ่ม 23 ก.ย. 2026: บอทอีกตัว (โหมด 2) — สิ่งที่เพิ่งเสนอ/ถูกนำไปใช้ (ให้ 2 บอท 'รู้เห็นกัน')"""
    out = {}
    base = os.path.join(ROOT, 'research', 'recommendations')
    for name, key in (('latest_recommendation.json', 'latest'),
                      ('last_applied.json', 'applied'),
                      ('last_failed.json', 'failed')):
        try:
            out[key] = json.load(io.open(os.path.join(base, name), encoding='utf-8'))
        except Exception:
            out[key] = None
    return out


def recent_rounds(limit=3):
    """★ เพิ่ม 23 ก.ย. 2026: ความจำข้ามรอบของแอดมินบอท — รอบก่อน ๆ ทำอะไรไปแล้ว
    (อ่านจาก log ของตัวเอง ไม่ใช่จากบทสนทนา)"""
    out = []
    try:
        rows = [json.loads(l) for l in io.open(LOG, encoding='utf-8') if l.strip()]
    except Exception:
        return out
    for r in rows[-int(limit):]:
        ch = r.get('changes') or []
        jev = (r.get('jev') or {})
        dv = (jev.get('values') or {}).get('derived') or {}
        ds = (jev.get('structure') or {}).get('derived') or {}
        out.append({
            'time': r.get('time'), 'mode': r.get('mode'),
            'changes': [{'key': c.get('key'), 'from': c.get('from'), 'to': c.get('to')} for c in ch],
            'jev_values': ('ผ่าน' if dv.get('safe') else 'ทบทวน') if dv else None,
            'jev_structure': ('ผ่าน' if ds.get('safe') else 'ทบทวน') if ds else None,
        })
    return out


def _write_json(path, value):
    """เขียน JSON แบบ atomic ถ้ามี runtime_support ไม่งั้น fallback พร้อมปิดไฟล์"""
    if _atomic_json is not None:
        _atomic_json(path, value)
        return
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(value, fh, ensure_ascii=False, indent=2)
BR = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
CFG = os.path.join(BR, 'auto_config.json')
WORK = os.path.join(ROOT, 'work')
AUDIT = os.path.join(WORK, 'auto_trader_audit.jsonl')
LOG = os.path.join(WORK, 'admin_bot_log.jsonl')
PLAN = os.path.join(WORK, 'admin_bot_plan.json')
STATE = os.path.join(WORK, 'admin_bot_state.json')

# ---------- กรอบที่ 1: "ค่าต่างๆ" ----------
BOUNDS = {
    'profit_exit.no_signal_tp_fraction': (0.5, 0.95),
    'side_net_gate.max_age_hours': (4.0, 24.0),
    'revenge_guard.cooldown_minutes': (5.0, 45.0),
    'revenge_guard.score_margin': (0.02, 0.15),
    'cooldown_minutes': (0.0, 20.0),
}

# ---------- กรอบที่ 2: "โครงสร้างของสกิล" (ค่าตัวเลข/เปิด-ปิด ของกลไกเดิม) ----------
STRUCTURE_BOUNDS = {
    'strategy_router.adaptive.disable_profit_factor': (0.70, 1.00),
    'strategy_router.adaptive.min_samples': (8.0, 30.0),
    'strategy_router.auto_threshold.window_records': (120.0, 400.0),
    'strategy_router.auto_threshold.band_min_widths.raw': (0.06, 0.20),
    'strategy_router.auto_threshold.band_min_widths.probability': (0.06, 0.20),
    'strategy_router.auto_threshold.band_min_widths.weighted': (0.06, 0.20),
    'atr_stop_multiplier': (0.80, 2.00),
    'min_reward_risk': (1.00, 2.00),
    # ★ 19 ก.ย. 2026: เพดานเดิม 2.00 ต่ำกว่าค่าจริงของเจ้าของระบบ (8.0)
    #   → บอทจะ 'ลดความเสี่ยง' ผิดเจตนาเมื่อ apply · ตั้งเพดาน = ค่าที่เจ้าของกำหนด
    'max_risk_pct': (0.20, 8.00),
    'early_cut.enabled': (0.0, 1.0),
    'revenge_guard.enabled': (0.0, 1.0),
}

# เพดานกันเจ็บ: ปรับแล้วผลแย่ลงเกินนี้ → คืนค่าเดิมอัตโนมัติ
ROLLBACK_DRAWDOWN_USD = 1.50


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def load_json(p, default):
    try:
        return json.load(io.open(p, encoding='utf-8'))
    except Exception:
        return default


def equity_now():
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            a = mt5.account_info()
            mt5.shutdown()
            return float(a.equity) if a else None
    except Exception:
        pass
    return None


def gather(hours=24):
    rows = []
    cut = now_utc() - datetime.timedelta(hours=hours)
    with io.open(AUDIT, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if '"event"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get('event') not in ('position_closed', 'no_trade', 'order_result', 'revenge_armed',
                                      'early_cut', 'profit_exit_result', 'close_ticker', 'admin_bot'):
                continue
            try:
                t = datetime.datetime.fromisoformat(str(e.get('time')).replace('Z', '+00:00'))
            except Exception:
                continue
            if t < cut:
                continue
            rows.append(e)
    closed = [float(e.get('net') or 0) for e in rows if e.get('event') == 'position_closed']
    wins = [n for n in closed if n > 0]
    losses = [n for n in closed if n < 0]
    return {
        'hours': hours, 'trades': len(closed),
        'win_rate': (100.0 * len(wins) / len(closed)) if closed else 0.0,
        'net': sum(closed),
        'avg_win': (sum(wins) / len(wins)) if wins else 0.0,
        'avg_loss': (sum(losses) / len(losses)) if losses else 0.0,
        'no_trade_rounds': sum(1 for e in rows if e.get('event') == 'no_trade'),
        'revenge_armed': sum(1 for e in rows if e.get('event') == 'revenge_armed'),
        'early_cut': sum(1 for e in rows if e.get('event') == 'early_cut'),
        'close_ticker': sum(1 for e in rows if e.get('event') == 'close_ticker'),
    }


def get_path(cfg, dotted):
    cur = cfg
    for part in dotted.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def set_path(cfg, dotted, value):
    parts = dotted.split('.')
    cur = cfg
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def recommend(cfg, stats, news_summary=None):
    """กฎวิวัฒน์ — อ้างผลจริง 24 ชม. (ค่าต่างๆ + โครงสร้าง) + ข่าวล่าสุด

    news_summary: ผลจาก news_feed.bias_summary() — ถ้าข่าว 'กดทอง' ชัด จะงดข้อเสนอที่
    'ผ่อนความระวัง' ทั้งหมด (ไม่ลดพื้นประตู · ไม่เพิ่มระยะ SL · ไม่ลดอายุความจำประตู)
    """
    out = []
    news_bear = bool(news_summary) and str((news_summary or {}).get('bias')) == 'BEAR'
    frac = float(get_path(cfg, 'profit_exit.no_signal_tp_fraction') or 0.8)
    if stats['trades'] >= 5 and stats['net'] < 0 and abs(stats['avg_loss']) > stats['avg_win']:
        out.append(('profit_exit.no_signal_tp_fraction', round(min(0.95, frac + 0.05), 3),
                    'ไม้แพ้ใหญ่กว่าไม้ชนะ → ให้ไม้วิ่งยาวขึ้น'))
    age = float(get_path(cfg, 'side_net_gate.max_age_hours') or 12)
    if stats['no_trade_rounds'] > max(20, 3 * stats['trades']) and age > 4:
        out.append(('side_net_gate.max_age_hours', round(max(4.0, age - 2), 1),
                    'รอบไม่เทรดเยอะ → ลดอายุความจำประตูเน็ต'))
    if stats['revenge_armed'] >= 3:
        cd = float(get_path(cfg, 'revenge_guard.cooldown_minutes') or 15)
        out.append(('revenge_guard.cooldown_minutes', round(min(45.0, cd + 5), 1),
                    'ตั้งกันแก้แค้นหลายครั้ง → ยืดเวลาพัก'))
    wr = stats['win_rate']
    if stats['trades'] >= 8 and wr < 55.0:
        win_rec = float(get_path(cfg, 'strategy_router.auto_threshold.window_records') or 180)
        out.append(('strategy_router.auto_threshold.window_records', round(max(120.0, win_rec - 20), 1),
                    'win rate ต่ำ → ให้ตัวปรับประตูไวขึ้น (หน้าต่างสั้นลง)'))
    if stats['trades'] >= 8 and wr >= 60.0 and abs(stats['avg_loss']) > stats['avg_win']:
        rr = float(get_path(cfg, 'min_reward_risk') or 1.4)
        out.append(('min_reward_risk', round(min(2.0, rr + 0.1), 2),
                    'win rate ดีแต่ไม้แพ้ใหญ่ → เพิ่มสัดส่วนกำไรต่อความเสี่ยง'))

    # ── ★ ขยาย 19 ก.ย. 2026: ใช้คีย์ที่ประกาศกรอบไว้ครบ (เดิมเสนอได้จริงแค่ 5 จาก 11) ──
    #   ทุกข้ออ้างสถิติจริง 24 ชม. และอยู่ในกรอบ STRUCTURE_BOUNDS เสมอ

    # (1) atr_stop_multiplier — โดนตัดบ่อย (win ต่ำ + ขาดทุนเฉลี่ย ≈ เต็ม SL) → ขยาย SL ขึ้นเล็กน้อย
    if stats['trades'] >= 8 and wr < 50.0 and stats['avg_loss'] < 0:
        atr = float(get_path(cfg, 'atr_stop_multiplier') or 1.2)
        out.append(('atr_stop_multiplier', round(min(2.0, atr + 0.1), 2),
                    'win ต่ำ + ไม้แพ้เต็มระยะ → ให้ SL กว้างขึ้นเล็กน้อยกันโดนเขี่ย'))
    # และทางกลับกัน: ขาดทุนเฉลี่ยเล็กมากแต่ยังแพ้บ่อย → SL แคบเกินไปก็ไม่ดี · ลดลงช้า ๆ เมื่อกำไรดี
    if stats['trades'] >= 12 and wr >= 65.0 and stats['net'] > 0:
        atr = float(get_path(cfg, 'atr_stop_multiplier') or 1.2)
        out.append(('atr_stop_multiplier', round(max(0.8, atr - 0.05), 2),
                    'กำไรดีต่อเนื่อง → ลดระยะ SL ลงเล็กน้อยเพื่อเพิ่ม R'))

    # (2) พื้นความกว้าง band — รอบไม่เทรดเยอะ = ประตูตึงเกิน → ลดพื้น (ไม่ต่ำกว่า 0.06)
    if stats['no_trade_rounds'] > max(30, 4 * stats['trades']):
        for dim in ('raw', 'probability', 'weighted'):
            key = f'strategy_router.auto_threshold.band_min_widths.{dim}'
            cur = float(get_path(cfg, key) or 0.10)
            out.append((key, round(max(0.06, cur - 0.01), 3),
                        'รอบไม่เทรดเยอะ → ลดพื้นความกว้าง band เพื่อให้มีสัญญาณผ่าน'))
    # และทางกลับกัน: เทรดถี่แต่ win ต่ำ → ยกพื้นขึ้น (กรองเข้มขึ้น ไม่เกิน 0.20)
    if stats['trades'] >= 12 and wr < 50.0:
        for dim in ('raw', 'probability', 'weighted'):
            key = f'strategy_router.auto_threshold.band_min_widths.{dim}'
            cur = float(get_path(cfg, key) or 0.10)
            out.append((key, round(min(0.20, cur + 0.01), 3),
                        'เทรดถี่แต่ win ต่ำ → ยกพื้นความกว้าง band ให้คัดสัญญาณเข้มขึ้น'))

    # (3) adaptive.min_samples — ข้อมูลน้อย + ผลแย่ → เพิ่มจำนวนตัวอย่างก่อนปรับ (ระวังขึ้น)
    if stats['trades'] >= 10 and stats['net'] < 0:
        ms = float(get_path(cfg, 'strategy_router.adaptive.min_samples') or 12)
        out.append(('strategy_router.adaptive.min_samples', round(min(30.0, ms + 2), 1),
                    'ผลสุทธิเป็นลบ → ต้องมีตัวอย่างมากขึ้นก่อนให้ชั้นปรับตัวเปลี่ยนค่า'))
    # ข้อมูลเยอะ + ผลดี → ลดจำนวนตัวอย่างลงให้ปรับตัวไวขึ้น
    if stats['trades'] >= 25 and stats['net'] > 0 and wr >= 60.0:
        ms = float(get_path(cfg, 'strategy_router.adaptive.min_samples') or 12)
        out.append(('strategy_router.adaptive.min_samples', round(max(8.0, ms - 2), 1),
                    'เทรดเยอะและผลดี → ให้ชั้นปรับตัวตอบสนองเร็วขึ้น'))

    # (4) adaptive.disable_profit_factor — ผลรวมเป็นลบ → เข้มขึ้น (เข้าใกล้ 1.0 = ปิด adaptive ง่ายขึ้น)
    if stats['trades'] >= 10 and stats['net'] < 0:
        pf = float(get_path(cfg, 'strategy_router.adaptive.disable_profit_factor') or 0.85)
        out.append(('strategy_router.adaptive.disable_profit_factor', round(min(1.0, pf + 0.02), 2),
                    'ผลสุทธิเป็นลบ → เพิ่มความระวังต่อชั้นปรับตัว (ปิดเมื่อหลักฐานอ่อน)'))

    # (5) early_cut.enabled — ถ้าปิดอยู่ และมีไม้แพ้สะสมชัด → เปิดกลับ (กลไกนี้มีผลจำลอง +$2.39)
    ec = get_path(cfg, 'early_cut.enabled')
    if ec is False and stats['trades'] >= 6 and stats['net'] < 0 and stats['no_trade_rounds'] > 20:
        out.append(('early_cut.enabled', True,
                    'ปิด early_cut อยู่แต่ผลสุทธิเป็นลบ → เปิดกลับ (ผลจำลอง +$2.39/6 วัน)'))

    # (6) revenge_guard.enabled — ถ้าปิดอยู่ และพบการเข้าไม้ซ้ำฝั่งที่เพิ่งแพ้ → เปิดกลับ
    rg = get_path(cfg, 'revenge_guard.enabled')
    if rg is False and stats['revenge_armed'] >= 2:
        out.append(('revenge_guard.enabled', True,
                    'ปิดกันแก้แค้นอยู่แต่พบการตั้งซ้ำฝั่งที่แพ้ → เปิดกลับ'))

    # ★ ข่าวกดทองชัด → งดข้อเสนอที่ 'ผ่อนความระวัง' (กันระบบผ่อนประตูผิดจังหวะข่าว)
    if news_bear:
        loosening = (
            'strategy_router.auto_threshold.band_min_widths.raw',
            'strategy_router.auto_threshold.band_min_widths.probability',
            'strategy_router.auto_threshold.band_min_widths.weighted',
            'atr_stop_multiplier',
            'side_net_gate.max_age_hours',
        )
        kept, dropped = [], []
        for item in out:
            (dropped if item[0] in loosening else kept).append(item)
        if dropped:
            out = kept
            out.append(('__news_note__', 0, 'ข่าวกดทอง (BEAR) → งดผ่อนความระวัง %d ข้อเสนอ' % len(dropped)))
    return out


def _jp_level():
    try:
        import jev_power
        return jev_power.level()
    except Exception:
        return None


def main():
    args = sys.argv[1:]
    apply_ = '--apply' in args
    # Guard the direct entry point too, before broker/news calls or any rollback.
    from runtime_support import require_ai_mode, digest
    from admin_config import apply_values, restore_values
    if apply_:
        require_ai_mode(ROOT)
    allow_structure = '--allow-structure' in args
    interval = 60
    if '--interval' in args:
        try:
            interval = int(args[args.index('--interval') + 1])
        except Exception:
            interval = 60
    bounds = dict(BOUNDS)
    if allow_structure:
        bounds.update(STRUCTURE_BOUNDS)

    cfg = load_json(CFG, {})
    stats = gather(24)
    # ★ งานวิจัยข่าว (เรียกโมดูลข่าว = ได้งานวิจัยข่าวครบวงจรในตัว)
    news_state, news_summary = None, None
    news_history_text = None
    try:
        if news_feed is not None:
            news_state = news_feed.refresh()
            news_summary = news_feed.bias_summary(news_state.get('items') or [])
            # ★ ประวัติงานวิจัยข่าว (ช่วงสั้น) ให้รอบแอดมินเห็นแนวโน้ม — ดึงช่วงอื่นได้ตามต้องการ
            news_history_text = news_feed.history(hours=24, max_records=20)['text']
    except Exception as _exc:
        news_state = {'errors': [str(_exc)], 'items': []}
    prev = load_json(STATE, {})
    rolled = None

    # ---- คืนค่าเดิมอัตโนมัติ ถ้าผลหลังปรับครั้งล่าสุดแย่ลงเกินเพดาน ----
    try:
        prev_apply, prev_eq = prev.get('last_apply'), prev.get('equity_at_apply')
        if apply_ and prev_apply and prev_eq and prev.get('config_hash') == digest(cfg):
            t_prev = datetime.datetime.fromisoformat(prev_apply)
            if (now_utc() - t_prev).total_seconds() < 6 * 3600:
                eq = equity_now()
                if eq is not None and (eq - float(prev_eq)) < -ROLLBACK_DRAWDOWN_USD:
                    baks = sorted(glob.glob(CFG + '.bak_adminbot_*'), key=os.path.getmtime)
                    if baks:
                        with io.open(baks[-1], encoding='utf-8') as fh:
                            previous_config = json.load(fh)
                        cfg, _ = restore_values(CFG, previous_config, bounds,
                                                root=ROOT, expected_hash=digest(cfg))
                        rolled = os.path.basename(baks[-1])
                        io.open(LOG, 'a', encoding='utf-8').write(json.dumps(
                            {'time': now_utc().isoformat(timespec='seconds'), 'mode': 'rollback',
                             'reason': 'ผลแย่ลงเกิน %.2f USD หลังปรับครั้งล่าสุด' % ROLLBACK_DRAWDOWN_USD,
                             'restored_from': rolled, 'equity_now': eq, 'equity_at_apply': prev_eq},
                            ensure_ascii=False) + '\n')
                        cfg = load_json(CFG, {})
                        prev = {}
    except Exception as exc:
        raise RuntimeError('Admin rollback failed; no further apply attempted') from exc

    plan = recommend(cfg, stats, news_summary=news_summary)
    safe = []
    news_notes = []
    for key, val, why in plan:
        if key == '__news_note__':
            news_notes.append(why)
            continue
        lo, hi = bounds.get(key, (None, None))
        if lo is None:
            continue
        val = max(lo, min(hi, float(val)))
        cur = get_path(cfg, key)
        if cur is None or abs(float(cur) - val) < 1e-9:
            continue
        safe.append((key, val, float(cur), why))

    # ★ Jev (TypeSafe System One) — ทำงาน 'พร้อมกับบอท' เท่านั้น (เจ้าของระบบกำหนด 23 ก.ย. 2026)
    #   ดูแลครบ 4 ด้าน: ข้อมูลสัญญาณภายใน · ข่าวภายนอก · ค่าต่างๆ · โครงสร้างต่างๆ
    #   เป็นคำแนะนำให้บอทตัดสินใจ — กรอบปลอดภัย + คืนค่าเดิมอัตโนมัติยังเป็นตัวบังคับจริง
    jev_all = None
    try:
        import jev as _jev
        if _jev.load_config().get('use_in_admin', True):
            jctx = 'admin'
            jev_all = {}
            news_txt = (news_summary.get('text') if isinstance(news_summary, dict)
                        else str(news_summary or ''))
            # (1) ข่าวภายนอก
            if news_feed is not None:
                try:
                    jn = news_feed.jev_analysis(context=jctx)
                    if jn:
                        jev_all['news'] = jn
                except Exception:
                    pass
            # (2) ข้อมูลสัญญาณภายใน
            try:
                st_in = {'performance': stats, 'news_digest': news_txt,
                         'equity': {'equity': equity_now()}}
                ri = _jev.ask_preset('internal', st_in, context=jctx)
                if ri.get('ok'):
                    jev_all['internal'] = {'derived': ri.get('derived') or {},
                                           'summary': _jev._summary(ri.get('answers') or {}),
                                           'latency_ms': ri.get('latency_ms')}
            except Exception:
                pass
            # (3) ค่าต่างๆ (เฉพาะเมื่อมีข้อเสนอปรับ)
            if safe:
                changed = [k for k, _v, _c, _w in safe]
                st_v = {
                    'proposal': [{'param': k, 'from': c, 'to': v, 'reason': w} for k, v, c, w in safe],
                    'other_bot': other_bot_state(),
                    'envelope': {'allowed': sorted(bounds.keys()),
                                 'note': 'กรอบปลอดภัยของแอดมินบอท (ห้ามออกนอกกรอบนี้)',
                                 'reserved_note': 'คีย์สงวน/โครงสร้างโค้ด/ตัวเทรด/kill switch = ห้ามแตะ'},
                    'performance': stats,
                    'news_digest': news_txt,
                    'candidates': [{'name': k, 'note': 'ค่าที่อยู่ในกรอบและยังไม่ถูกปรับรอบนี้'}
                                   for k in sorted(bounds.keys()) if k not in changed][:8],
                }
                r = _jev.ask_preset('admin-safety', st_v, context=jctx)
                jev_all['values'] = {'ok': bool(r.get('ok')), 'derived': r.get('derived') or {},
                                     'latency_ms': r.get('latency_ms'), 'error': r.get('error'),
                                     'summary': _jev._summary(r.get('answers') or {})}
            # (4) โครงสร้างต่างๆ (เมื่อเปิดให้วิวัฒน์โครงสร้าง)
            if allow_structure:
                st_s = {
                    'proposal': [{'param': k, 'from': c, 'to': v, 'reason': w} for k, v, c, w in safe]
                                or [{'param': '(ยังไม่มีข้อเสนอรอบนี้)', 'reason': 'ประเมินกรอบโครงสร้างรวม'}],
                    'structure_envelope': {'allowed': sorted(STRUCTURE_BOUNDS.keys()),
                                           'factory_backup': 'work/factory/ (restore_factory.py)'},
                    'design': {'gates': ['ด่าน 1 ประตู net ต่อกลยุทธ์-ทิศทาง (ฝั่งตรงข้ามกลยุทธ์เดิมไม่ต้องผ่าน)',
                                         'ด่าน 2 คะแนน 36 ค่า (p25-p90 · ความกว้างขั้นต่ำ raw/probability/weighted)',
                                         'ด่าน 3 เทียบสองฝั่ง (ไม่เกี่ยวกับประตู net)'],
                               'rules': ['งานที่ใช้ LLM ต้องให้บอทเป็นผู้ดูแล ไม่ต่อ LLM ตรง',
                                         'ห้ามแตะคีย์สงวน/ตัวเทรด/kill switch/โครงสร้างโค้ด',
                                         'ต้องคืนค่าโรงงานได้เสมอ']},
                    'performance': stats,
                    'news_digest': news_txt,
                    'history': {'note': 'ใช้ตัวเลขจริงจาก audit — ไม่มีข้อมูลหลายช่วงให้ดู'},
                    'areas': [{'name': 'auto_threshold (36 ค่า)', 'note': 'หน้าต่างเรียนรู้ · ความกว้าง band ขั้นต่ำ'},
                              {'name': 'strategy_router (เราเตอร์กลยุทธ์)', 'note': 'เกณฑ์เลือกกลยุทธ์/น้ำหนัก'},
                              {'name': 'gate (ประตู net · เทียบสองฝั่ง)', 'note': 'ด่าน 1 และด่าน 3'},
                              {'name': 'guards (กันแก้แค้น/ตัดขาดทุน)', 'note': 'ความไวของกลไกป้องกัน'},
                              {'name': 'exits (TP/SL/profit_exit)', 'note': 'เกณฑ์ออกทำกำไร/ตัดขาดทุน'}],
                }
                rs = _jev.ask_preset('admin-structure', st_s, context=jctx)
                jev_all['structure'] = {'ok': bool(rs.get('ok')), 'derived': rs.get('derived') or {},
                                        'latency_ms': rs.get('latency_ms'), 'error': rs.get('error'),
                                        'summary': _jev._summary(rs.get('answers') or {})}
    except Exception as exc:
        jev_all = {'error': str(exc)[:200]}

    stamp = now_utc().isoformat(timespec='seconds')
    prev_rounds = recent_rounds(3)
    other_bot = other_bot_state()
    # ★ บันไดอำนาจ Jev (23 ก.ย. 2026 · เจ้าของระบบอนุมัติ "เส้นทางสู่อำนาจเต็ม"):
    #   ระดับ ≥1 = Jev มีสิทธิ์เบรก (ลดความเสี่ยงได้เท่านั้น · ห้ามเพิ่ม)
    veto = None
    try:
        import jev_power as _jp
        if apply_ and safe and _jp.can('veto'):
            _dv = ((jev_all or {}).get('values') or {}).get('derived') or {}
            _ds = ((jev_all or {}).get('structure') or {}).get('derived') or {}
            _bad = []
            if _dv and _dv.get('safe') is False:
                _bad.append('ค่าต่างๆ')
            if _ds and _ds.get('safe') is False:
                _bad.append('โครงสร้าง')
            if _bad:
                veto = _bad
                _jp.log('veto', scope=_bad,
                        jev_values={k: _dv.get(k) for k in
                                    ('within_intent', 'raises_drawdown_risk', 'driven_by_noise', 'risk_level')},
                        jev_structure={k: _ds.get(k) for k in
                                       ('within_bounds', 'within_intent', 'restorable', 'evidence_enough', 'risk_level')})
                print('⛔ Jev ใช้สิทธิ์เบรก (ระดับ %d): %s ไม่ผ่านการตรวจ → งดปรับรอบนี้'
                      % (_jp.level(), ' + '.join(_bad)))
    except Exception as _vexc:
        veto = None
        print('   (บันไดอำนาจ Jev ใช้งานไม่ได้: %s)' % str(_vexc)[:60])

    record = {'time': stamp, 'mode': 'apply' if apply_ else 'advisory',
              'interval_minutes': interval, 'structure_allowed': allow_structure,
              'stats': stats,
              'news': {'summary': news_summary, 'items': (news_state or {}).get('items') or [],
                       'history_24h': news_history_text,
                       'errors': (news_state or {}).get('errors') or []},
              'changes': [{'key': k, 'from': c, 'to': v, 'why': w} for k, v, c, w in safe if k != '__news_note__'],
              'jev': jev_all,
              # ★ ความจำข้ามรอบ: รอบก่อน ๆ ของตัวเอง (ทำอะไรไป · Jev ว่าอย่างไร)
              'previous_rounds': prev_rounds,
              'other_bot': other_bot,
              'interbot': interbot_box('admin'), 'jev_veto': veto, 'jev_power_level': _jp_level()}
    io.open(LOG, 'a', encoding='utf-8').write(json.dumps(record, ensure_ascii=False) + '\n')
    io.open(PLAN, 'w', encoding='utf-8').write(json.dumps(record, ensure_ascii=False, indent=2))

    eq_now = equity_now()
    keep = {'interval_minutes': interval, 'last_round': stamp, 'mode': record['mode']}
    if apply_ and safe and not veto:
        cfg, committed = apply_values(CFG, {k: v for k, v, _c, _w in safe}, bounds,
                                      root=ROOT, expected_hash=digest(cfg), label='adminbot')
        keep['last_apply'] = stamp
        keep['equity_at_apply'] = eq_now
        keep['config_hash'] = digest(cfg)
    else:
        keep['last_apply'] = prev.get('last_apply')
        keep['equity_at_apply'] = prev.get('equity_at_apply')
        keep['config_hash'] = prev.get('config_hash')
    _write_json(STATE, keep)

    print('=== รอบแอดมิน (%s) รอบละ %d นาที | โครงสร้าง: %s ===' % (
        record['mode'], interval, 'เปิดให้วิวัฒน์' if allow_structure else 'ปิด'))
    print('ไม้ปิด 24 ชม.: %d | win %.1f%% | net $%+.2f | เฉลี่ยชนะ $%+.3f / แพ้ $%+.3f' % (
        stats['trades'], stats['win_rate'], stats['net'], stats['avg_win'], stats['avg_loss']))
    print('รอบไม่เทรด: %d | กันแก้แค้น: %d | ตัดขาดทุนใหม่: %d | ticker ปิดไม้: %d' % (
        stats['no_trade_rounds'], stats['revenge_armed'], stats['early_cut'], stats['close_ticker']))
    if news_summary:
        print('ข่าวล่าสุด: %s → ระวัง: %s' % (news_summary.get('text'), news_summary.get('caution')))
    if rolled:
        print('⚠️ คืนค่าเดิมอัตโนมัติ (ผลแย่ลงเกินเพดาน): %s' % rolled)
    if jev_all and not jev_all.get('error'):
        print('── Jev (ทำงานกับบอทเท่านั้น · ครบ 4 ด้าน) ──')
        di = (jev_all.get('internal') or {}).get('derived') or {}
        if di:
            print('   ข้อมูลภายใน: %s | net โซนกำไร %.2f · ความถี่เหมาะ %.2f · ขอบยั่งยืน %.2f · '
                  'คุณภาพการตั้งค่า %.2f · ควรทำ: %s'
                  % ('✅ สุขภาพดี' if di.get('healthy') else '⚠️ ต้องจับตา',
                     float(di.get('in_profit_zone') or 0), float(di.get('frequency_ok') or 0),
                     float(di.get('edge_durable') or 0), float(di.get('setup_quality') or 0),
                     di.get('next_action')))
            if di.get('watch'):
                print('      จับตา: %s' % ' · '.join(di['watch']))
            if di.get('main_leak'):
                print('      ซึมรั่วหลัก: %s' % di['main_leak'])
        dn = jev_all.get('news') or {}
        if dn:
            print('   ข่าวภายนอก: ทิศทาง %s · คะแนน %+.2f · หนักแน่น %.2f · price-in %.2f'
                  % (dn.get('direction'), float(dn.get('news_score') or 0),
                     float(dn.get('conviction') or 0), float(dn.get('already_priced') or 0)))
        dv = (jev_all.get('values') or {}).get('derived') or {}
        if dv:
            print('   ค่าต่างๆ: %s | ในเจตนาระบบ %.2f · เสี่ยงขาดทุนต่อเนื่อง %.2f · จากสัญญาณรบกวน %.2f · ระดับเสี่ยง %.2f'
                  % ('✅ ปลอดภัย' if dv.get('safe') else '⚠️ ควรทบทวน',
                     float(dv.get('within_intent') or 0), float(dv.get('raises_drawdown_risk') or 0),
                     float(dv.get('driven_by_noise') or 0), float(dv.get('risk_level') or 0)))
            if dv.get('reasons'):
                print('      เหตุผล: %s' % ' · '.join(dv['reasons']))
            if dv.get('next_lever'):
                print('      คันโยกที่ควรดูก่อน: %s' % dv['next_lever'])
        ds = (jev_all.get('structure') or {}).get('derived') or {}
        if ds:
            print('   โครงสร้าง: %s | ในกรอบ %.2f · คงเจตนาระบบ %.2f · คืนค่าได้ %.2f · หลักฐานพอ %.2f · เสี่ยง %.2f'
                  % ('✅ ปลอดภัย' if ds.get('safe') else '⚠️ ควรทบทวน',
                     float(ds.get('within_structure_envelope') or 0),
                     float(ds.get('preserves_design') or 0), float(ds.get('reversible') or 0),
                     float(ds.get('evidence_enough') or 0), float(ds.get('structure_risk') or 0)))
            if ds.get('reasons'):
                print('      เหตุผล: %s' % ' · '.join(ds['reasons']))
            if ds.get('evolve_area'):
                print('      ส่วนที่ควรพิจารณาก่อน: %s' % ds['evolve_area'])
    _ib = interbot_box('admin')
    if _ib.get('text'):
        print('── กล่องปรึกษาระหว่างบอท ──')
        for _ln in str(_ib['text']).splitlines()[:6]:
            print('   %s' % _ln)
    _ob = (other_bot or {}).get('latest') or (other_bot or {}).get('applied')
    if _ob:
        _ch = _ob.get('changes') or []
        print('── บอทอีกตัว (โหมด 2) เพิ่งเสนอ: %s | %s' % (
            str(_ob.get('created') or _ob.get('time') or '')[:16],
            ', '.join('%s=%s' % (c.get('key'), c.get('to')) for c in _ch[:3]) or 'ไม่มีการเปลี่ยน'))
    if prev_rounds:
        # ★ เพิ่ม 23 ก.ย. 2026: กระดานคะแนนกลยุทธ์ — วัดว่าการปรับตัว/วิวัฒนาการ 'ได้ผลจริง' ไหม
        #   (เจ้าของระบบ: กำไรที่ราบรื่นและยั่งยืนขึ้นกับความสามารถปรับตัว/วิวัฒนาการของระบบ)
        try:
            _sc = os.path.join(BR, 'tools', 'strategy_scoreboard.py')
            _r = subprocess.run([sys.executable, _sc], capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=180, cwd=ROOT)
            _txt = (_r.stdout or '').strip()
            if _txt:
                print('── กระดานคะแนนกลยุทธ์ (กำไรจริง — ใช้ตัดสินวิวัฒนาการ) ──')
                for _ln in _txt.splitlines()[:16]:
                    print('   %s' % _ln)
                print('   → กลยุทธ์ net ติดลบ+PF<0.85 ควรถูกกด · หน้าต่างล่าสุดดีขึ้น = การปรับตัวได้ผล ✓')
        except Exception as _exc:
            print('── กระดานคะแนนกลยุทธ์: ใช้งานไม่ได้ (%s)' % str(_exc)[:70])
        print('── รอบก่อน ๆ ของตัวเอง (ความจำข้ามรอบ) ──')
        for r in prev_rounds:
            ch = r.get('changes') or []
            txt = ('ปรับ %d ค่า: %s' % (len(ch), ', '.join('%s→%s' % (c['key'], c['to']) for c in ch[:3]))) if ch \
                else 'ไม่มีการปรับค่า'
            jv = []
            if r.get('jev_values'):
                jv.append('ค่า:' + r['jev_values'])
            if r.get('jev_structure'):
                jv.append('โครงสร้าง:' + r['jev_structure'])
            print('   %s [%s] %s%s' % (r.get('time', '')[:16], r.get('mode'), txt,
                                       (' | Jev ' + ' · '.join(jv)) if jv else ''))
    if not safe:
        print('ไม่มีการปรับค่า (ค่าปัจจุบันอยู่ในเกณฑ์ดีแล้ว)')
    for n in news_notes:
        print('  ⓘ %s' % n)
    for k, v, c, w in safe:
        print('  %s: %s → %s  (%s)%s' % (k, c, v, w, ' [ปรับแล้ว]' if apply_ else ' [รออนุมัติ]'))
    if not apply_:
        print('\n(โหมดแนะนำ — ใส่ --apply เพื่อปรับจริง / เพิ่ม --allow-structure เพื่อวิวัฒน์โครงสร้าง)')


if __name__ == '__main__':
    main()
