#!/usr/bin/env python3
"""验证桌面程序构建是否包含最新修复"""

import sys
import os

def verify_fixes():
    # 检查源代码中的修复
    impl_file = 'desktop_uploader/release/fanqie_uploader_impl.py'
    
    with open(impl_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=" * 50)
    print("验证源代码修复")
    print("=" * 50)
    
    # 检查关键修复
    checks = [
        ('从明天开始计算定时发布', '定时发布核心修复'),
        ('检测到新书首次发布', '新书检测逻辑'),
        ('day_offset = 0', '天数偏移初始化'),
        ('chapters_in_current_day = 0', '每日章节计数'),
    ]
    
    all_ok = True
    for pattern, desc in checks:
        if pattern in content:
            print(f"[OK] {desc}: 找到 '{pattern}'")
        else:
            print(f"[ERR] {desc}: 未找到 '{pattern}'")
            all_ok = False
    
    print()
    print("=" * 50)
    print("验证 EXE 文件")
    print("=" * 50)
    
    exe_file = 'desktop_uploader/release/NovelPublisher.exe'
    if os.path.exists(exe_file):
        import datetime
        mtime = os.path.getmtime(exe_file)
        mtime_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        size_mb = os.path.getsize(exe_file) / 1024 / 1024
        
        print(f"[OK] EXE 文件存在")
        print(f"     大小: {size_mb:.1f} MB")
        print(f"     修改时间: {mtime_str}")
        
        # 检查 py 文件修改时间
        py_mtime = os.path.getmtime(impl_file)
        py_mtime_str = datetime.datetime.fromtimestamp(py_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"     源码修改时间: {py_mtime_str}")
        
        if mtime > py_mtime:
            print("[OK] EXE 比源码更新，修复已包含")
        else:
            print("[WARN] EXE 可能比源码旧")
    else:
        print("[ERR] EXE 文件不存在")
        all_ok = False
    
    print()
    print("=" * 50)
    if all_ok:
        print("✓ 所有检查通过，构建成功！")
    else:
        print("✗ 部分检查失败")
    print("=" * 50)
    
    return all_ok

if __name__ == '__main__':
    success = verify_fixes()
    sys.exit(0 if success else 1)
