# -*- coding: utf-8 -*-
"""คืนค่าโรงงาน (Factory Reset) — เหมือนโทรศัพท์รีเซ็ตกลับค่าตั้งต้น
ใช้เมื่อบอทแอดมินปรับค่าจนระบบมั่ว: คืนทั้ง "ค่าตั้ง" และ "โค้ด" กลับชุดติดตั้งเดิม

วิธีใช้:
    python restore_factory.py            → แสดงข้อมูลชุดโรงงาน (dry run)
    python restore_factory.py --apply    → คืนค่าจริง (สำรองของปัจจุบันไว้ก่อนเสมอ)
    python restore_factory.py --apply --code   → คืนค่าทั้ง config และโค้ด
"""
import io, os, sys, json, shutil, datetime, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BR = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
FAC = os.path.join(ROOT, 'work', 'factory')
CONFIG = os.path.join(BR, 'auto_config.json')

def stamp():
    return datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

def main():
    apply_ = '--apply' in sys.argv
    do_code = '--code' in sys.argv
    info = json.load(io.open(os.path.join(FAC, 'FACTORY_INFO.json'), encoding='utf-8'))
    print('ชุดโรงงานสร้างเมื่อ:', info['created'])
    print('ค่าตั้งโรงงานจาก:', info['config_source'], '| โค้ดโรงงาน:', info['code_files'], 'ไฟล์')
    print('ค่าปัจจุบัน:', CONFIG)
    if not apply_:
        print('\n(โหมดตรวจสอบ — ยังไม่เปลี่ยนอะไร ใส่ --apply เพื่อคืนค่าจริง)')
        return
    # Owner-only restore remains stopped; never restore a saved permission grant.
    if not os.path.isfile(os.path.join(ROOT, 'work', 'AUTO_TRADER_STOP')):
        raise RuntimeError('Stop the system before factory restore')
    for name in ('auto_trader.pid', 'auto_trader_supervisor.pid'):
        if os.path.exists(os.path.join(ROOT, 'work', name)):
            raise RuntimeError('Confirm trader/supervisor have stopped before factory restore')
    sys.path.insert(0, BR)
    from runtime_support import update_json
    with io.open(os.path.join(FAC, 'config', 'auto_config.factory.json'), encoding='utf-8') as fh:
        factory_config = json.load(fh)
    if not isinstance(factory_config, dict):
        raise ValueError('Invalid factory configuration')

    # ★ เพิ่ม 23 ก.ย. 2026: คืนสวิตช์ Jev (TypeSafe System One) — สำรองของเดิมก่อนเสมอ
    _jev_fac = os.path.join(FAC, 'config', 'jev_config.factory.json')
    _jev_live = os.path.join(BR, 'jev_config.json')
    if os.path.exists(_jev_fac):
        if os.path.exists(_jev_live):
            shutil.copy(_jev_live, _jev_live + '.bak_before_factory_' + stamp())
        shutil.copy(_jev_fac, _jev_live)
        print('คืนค่าสวิตช์ Jev แล้ว:', os.path.basename(_jev_live))
    # ★ 23 ก.ย. 2026: คืนค่าบันไดอำนาจ Jev (jev_power.json) — แยกจากสวิตช์ Jev
    _pwr_fac = os.path.join(FAC, 'config', 'jev_power.factory.json')
    _pwr_live = os.path.join(BR, 'jev_power.json')
    if os.path.exists(_pwr_fac):
        if os.path.exists(_pwr_live):
            shutil.copy(_pwr_live, _pwr_live + '.bak_before_factory_' + stamp())
        shutil.copy(_pwr_fac, _pwr_live)
        print('คืนค่าบันไดอำนาจ Jev แล้ว:', os.path.basename(_pwr_live))
    # สำรองของปัจจุบันก่อนเสมอ
    bak = CONFIG + '.bak_before_factory_' + stamp()
    shutil.copy(CONFIG, bak)
    print('สำรองค่าปัจจุบันไว้:', os.path.basename(bak))
    def restore(current):
        candidate = dict(factory_config)
        for key in ('live_enabled', 'magic', 'volume', 'symbol'):
            if key in current:
                candidate[key] = current[key]
            else:
                candidate.pop(key, None)
        return candidate
    update_json(CONFIG, restore)
    print('✅ คืนค่าตั้งโรงงานแล้ว')
    if do_code:
        # ★ แก้ 19 ก.ย. 2026: ชื่อไฟล์ในโรงงานเป็นแบบแบน (tools_foo.py) — เดิมคืนไปที่ BR ตรง ๆ
        #   ทำให้ไฟล์ tools_* ไปโผล่ผิดที่ (BR/tools_foo.py) และไม่ได้คืนของจริงให้ BR/tools/
        #   → คำนวณที่อยู่จริงกลับจากชื่อแบน
        def _target(fname):
            if fname.startswith('tools_'):
                return os.path.join(BR, 'tools', fname[len('tools_'):])
            if fname.startswith('agents_'):
                return os.path.join(ROOT, 'agents', fname[len('agents_'):])
            return os.path.join(BR, fname)

        for f in os.listdir(os.path.join(FAC, 'code')):
            tgt = _target(f)
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            if os.path.exists(tgt):
                shutil.copy(tgt, tgt + '.bak_before_factory_' + stamp())
            shutil.copy(os.path.join(FAC, 'code', f), tgt)
            print('  ✅ คืนโค้ด:', f, '→', os.path.relpath(tgt, ROOT))
    # ล็อกให้ตัวเทรดอ่านค่าใหม่
    print('\nระบบจะอ่านค่าใหม่ภายในรอบถัดไป (hot reload) — ถ้าคืนโค้ดต้องรีสตาร์ทตัวเทรด')

if __name__ == '__main__':
    main()
