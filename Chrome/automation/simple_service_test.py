#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
极简化的签约服务测试
逐步诊断问题
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"项目根目录: {project_root}")
print(f"Python路径: {sys.path[:3]}")  # 打印前3个路径

print("=" * 60)
print("🔍 签约服务极简诊断")
print("=" * 60)

# 1. 测试导入
print("\n1️⃣ 测试导入模块...")
try:
    from Chrome.automation.services.enhanced_contract_service import EnhancedContractService
    print("   ✅ 导入成功")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. 测试创建实例
print("\n2️⃣ 测试创建实例...")
try:
    service = EnhancedContractService()
    print("   ✅ 实例创建成功")
except Exception as e:
    print(f"   ❌ 实例创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 测试获取状态
print("\n3️⃣ 测试获取状态...")
try:
    status = service.get_status()
    print(f"   ✅ 状态获取成功")
    print(f"   running: {status.get('running')}")
    print(f"   service_pid: {status.get('service_pid')}")
except Exception as e:
    print(f"   ❌ 状态获取失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 测试队列创建
print("\n4️⃣ 测试队列创建...")
try:
    import multiprocessing
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    print(f"   ✅ 队列创建成功")
    print(f"   task_queue ID: {id(task_queue)}")
except Exception as e:
    print(f"   ❌ 队列创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 5. 测试主循环初始化
print("\n5️⃣ 测试主循环初始化...")
try:
    service.task_queue = task_queue
    service.result_queue = result_queue
    
    # 手动调用run_service的第一步
    service.running = True
    print("   ✅ running = True")
    
    service.update_status(service.get_status())
    print("   ✅ 状态已更新")
    
except Exception as e:
    print(f"   ❌ 主循环初始化失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ 所有测试通过！")
print("\n现在尝试手动运行主循环...")
print("按 Ctrl+C 停止\n")

# 手动运行主循环
try:
    service.run_service()
except KeyboardInterrupt:
    print("\n⏹ 用户中断")
except Exception as e:
    print(f"\n❌ 主循环异常: {e}")
    import traceback
    traceback.print_exc()
