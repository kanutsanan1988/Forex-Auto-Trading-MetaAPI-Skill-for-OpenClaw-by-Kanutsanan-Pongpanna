# -*- coding: utf-8 -*-
"""ตั้งค่าโรงงาน = สถานะระบบปัจจุบันทั้งชุด (ค่าตั้ง + โค้ด + งาน cron)
เรียกได้ทุกเมื่อที่เจ้าของระบบต้องการปักหมุดสถานะปัจจุบันเป็นค่าโรงงาน
"""
import io, os, json, glob, shutil, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BR = os.path.join(ROOT, 'outputs', 'mt5_python_bridge')
FAC = os.path.join(ROOT, 'work', 'factory')

# ★ เพิ่ม 19 ก.ย. 2026: สำรอง "ค่าโรงงานชุดเดิม" ก่อนปักหมุดทับ
#   (เดิมเขียนทับทันที → ถ้าปักหมุดผิดจังหวะ จะไม่มีทางกลับไปชุดเดิม)
_ARCHIVE_ROOT = os.path.join(ROOT, 'work', 'factory-archive')
try:
    if os.path.exists(os.path.join(FAC, 'FACTORY_INFO.json')):
        _stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        _dest = os.path.join(_ARCHIVE_ROOT, 'factory_' + _stamp)
        shutil.copytree(FAC, _dest)
        print('สำรองค่าโรงงานชุดเดิมไว้ที่:', _dest)
except Exception as _exc:
    print('คำเตือน: สำรองค่าโรงงานชุดเดิมไม่สำเร็จ:', _exc)

for sub in ('config', 'code', 'cron'):
    os.makedirs(os.path.join(FAC, sub), exist_ok=True)

# 1) ค่าตั้งปัจจุบัน
shutil.copy(os.path.join(BR, 'auto_config.json'), os.path.join(FAC, 'config', 'auto_config.factory.json'))

# ★ เพิ่ม 23 ก.ย. 2026: เก็บสวิตช์ Jev (TypeSafe System One) ด้วย
#   คืนค่าโรงงานแล้ว 'การตั้งค่า Jev' ต้องกลับมาครบเหมือนค่าโรงงาน
_jev_cfg = os.path.join(BR, 'jev_config.json')
if os.path.exists(_jev_cfg):
    shutil.copy(_jev_cfg, os.path.join(FAC, 'config', 'jev_config.factory.json'))
# ★ 23 ก.ย. 2026: บันไดอำนาจ Jev (jev_power.json) — คนละไฟล์กับสวิตช์ Jev
_jev_pwr = os.path.join(BR, 'jev_power.json')
if os.path.exists(_jev_pwr):
    shutil.copy(_jev_pwr, os.path.join(FAC, 'config', 'jev_power.factory.json'))

# 2) โค้ดปัจจุบันทั้งชุด (โมดูลหลัก + tools) — เก็บชื่อแบบแบน ไม่มีอักขระพิเศษ
n = 0
# ★ เพิ่ม 19 ก.ย. 2026: เก็บโฟลเดอร์ agents/ ด้วย (ชั้น 'สมอง' — brief/registry/runner)
#   หมายเหตุ: ไฟล์ใน agents/ ไม่ได้รันเป็นโมดูล แต่เป็นส่วนของระบบ → ต้องคืนค่าได้
_AG = os.path.join(ROOT, 'agents')
_patterns = [(os.path.join(BR, '*.py'), BR),
             (os.path.join(BR, 'tools', '*.py'), BR),
             (os.path.join(_AG, '*.py'), ROOT),
             (os.path.join(_AG, '*.json'), ROOT),
             (os.path.join(_AG, '*.md'), ROOT)]
for pattern, base in _patterns:
    for f in glob.glob(pattern):
        if '__pycache__' in f:
            continue
        rel = os.path.relpath(f, base)
        flat = rel.replace(os.sep, '_').replace('/', '_')
        shutil.copy(f, os.path.join(FAC, 'code', flat))
        n += 1

# 3) งาน cron ปัจจุบัน
# ★ แก้ 19 ก.ย. 2026: ค่าโรงงานต้องบันทึก "สถานะที่ตั้งใจ" ของงาน ไม่ใช่สถานะชั่วคราว
#   (ตอนปักหมุดระบบอาจปิดอยู่ → snapshot เดิมจึงบันทึกทุกงานเป็น enabled=false)
#   เจ้าของระบบกำหนด: งานวิจัย 10 นาที (ภายใน) · งานวิจัย 10 นาที (บอท+LLM) · แอดมินบอท 30 นาที = เปิด
FACTORY_JOB_STATE = {
    'trading-analytics': True,                              # งานวิจัย 10 นาที ข้อมูลภายใน
    'trading-research-bot (10 นาที · บอทดูแล LLM)': True,    # งานวิจัย 10 นาทีจากบอท (สมอง LLM)
    'trading-admin-bot (30 นาที)': True,                    # แอดมินบอท วิวัฒนาการระบบ ทุก 30 นาที
    # ★ เพิ่ม 19 ก.ย. 2026: สองงานนี้เป็นส่วนของระบบปกติ (ต้องเปิด) — เดิมไม่ระบุ
    #   ทำให้ค่าโรงงานจดจำสถานะ "พักชั่วคราว" ของเจ้าของระบบกลายเป็นค่าโรงงาน ✗
    'llm-recommendation-consumer': True,                    # ตัวรับคำแนะนำ (5 นาที) — จำเป็นต่อวงจร
    'trading-daily-research-log': True,                     # บันทึกงานวิจัยรายวัน (23:50)
}
jp = os.path.expandvars(r'%LOCALAPPDATA%\hermes\cron\jobs.json')
snap = []
try:
    cron = json.load(io.open(jp, encoding='utf-8'))
    for j in cron.get('jobs', []):
        name = j.get('name')
        enabled = j.get('enabled')
        note = None
        if name in FACTORY_JOB_STATE:
            enabled = FACTORY_JOB_STATE[name]
            note = 'ค่าโรงงานกำหนดให้เปิด (ไม่ขึ้นกับสถานะตอนปักหมุด)'
        snap.append({
            'name': name,
            'schedule': (j.get('schedule') or {}).get('display'),
            'script': j.get('script'),
            'no_agent': j.get('no_agent'),
            # ★ เพิ่ม 19 ก.ย. 2026: เก็บค่าของ "สมอง" ด้วย (ไม่งั้นคืนค่าโรงงานแล้วสมองหาย)
            'skills': j.get('skills'),
            'workdir': j.get('workdir'),
            'provider': j.get('provider_snapshot') or j.get('provider'),
            'model': j.get('model_snapshot') or j.get('model'),
            'enabled': enabled,
            'factory_note': note,
        })
    io.open(os.path.join(FAC, 'cron', 'jobs.snapshot.json'), 'w', encoding='utf-8').write(
        json.dumps(snap, ensure_ascii=False, indent=2))
except Exception as exc:
    print('อ่าน cron ไม่ได้:', exc)

info = {
    'created': datetime.datetime.now().isoformat(timespec='seconds'),
    'note': 'ค่าโรงงาน = สถานะระบบปัจจุบันทั้งชุด (เจ้าของระบบสั่งตั้งใหม่ 19 ก.ย. 2026)',
    'config_source': 'auto_config.json (ค่าปัจจุบัน)',
    'code_files': n,
    'cron_jobs': len(snap),
    'factory_settings': {
        'งานวิจัย 10 นาทีข้อมูลภายใน': 'เปิด (trading-analytics)',
        'งานวิจัย 10 นาทีจากบอท (สมอง LLM)': 'เปิด (trading-research-bot)',
        'admin bot': 'ทุก 30 นาที เปิด (trading-admin-bot)',
        'งานเดิมที่ต่อ LLM ตรง': 'ลบออกแล้ว',
    },
    'restore': 'python work/factory/restore_factory.py --apply [--code]',
}
io.open(os.path.join(FAC, 'FACTORY_INFO.json'), 'w', encoding='utf-8').write(
    json.dumps(info, ensure_ascii=False, indent=2))

print('✅ ตั้งค่าโรงงานใหม่ = สถานะปัจจุบัน')
print('   ค่าตั้ง:', os.path.getsize(os.path.join(FAC, 'config', 'auto_config.factory.json')), 'bytes')
print('   โค้ด:', n, 'ไฟล์ | งาน cron:', len(snap), 'งาน')
for c in snap:
    print('     - %-40s %-14s enabled=%s' % (c['name'], c['schedule'], c['enabled']))
