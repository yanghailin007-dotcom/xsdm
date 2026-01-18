#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的签约服务测试脚本
用于诊断服务启动和崩溃问题
"""

import os
import sys
import json
import time
import multiprocessing
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_service_startup():
    """测试服务启动"""
    print("=" * 60)
    print("🔍 签约服务启动诊断测试")
    print("=" * 60)
    
    # 创建队列
    task_queue = multiprocessing.Queue()
    result_queue = multiprocessing.Queue()
    
    print("\n1️⃣ 创建队列...")
    print(f"   task_queue ID: {id(task_queue)}")
    print(f"   result_queue ID: {id(result_queue)}")
    
    # 测试队列通信
    print("\n2️⃣ 测试队列通信...")
    test_task = {
        "task_id": "test_001",
        "task_type": "get_novels_list",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(f"   发送测试任务到队列...")
    task_queue.put(test_task)
    print("   ✅ 任务已发送")
    
    # 尝试从队列获取
    print("\n3️⃣ 尝试从队列接收任务...")
    try:
        received_task = task_queue.get(timeout=5)
        print(f"   ✅ 成功接收任务: {received_task}")
    except Exception as e:
        print(f"   ❌ 接收任务失败: {e}")
        return False
    
    # 导入服务模块
    print("\n4️⃣ 导入服务模块...")
    try:
        from Chrome.automation.services.enhanced_contract_service import EnhancedContractService
        print("   ✅ 服务模块导入成功")
    except Exception as e:
        print(f"   ❌ 服务模块导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 创建服务实例
    print("\n5️⃣ 创建服务实例...")
    try:
        service = EnhancedContractService()
        print("   ✅ 服务实例创建成功")
    except Exception as e:
        print(f"   ❌ 服务实例创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 设置队列
    print("\n6️⃣ 设置服务队列...")
    service.task_queue = task_queue
    service.result_queue = result_queue
    print(f"   服务task_queue ID: {id(service.task_queue)}")
    print(f"   服务result_queue ID: {id(service.result_queue)}")
    
    # 检查队列是否相同
    print("\n7️⃣ 检查队列一致性...")
    if id(service.task_queue) == id(task_queue):
        print("   ✅ task_queue 是同一个队列")
    else:
        print(f"   ❌ task_queue 不是同一个队列!")
        print(f"      Web端队列ID: {id(task_queue)}")
        print(f"      服务端队列ID: {id(service.task_queue)}")
        return False
    
    # 测试服务初始化
    print("\n8️⃣ 测试服务初始化...")
    try:
        status = service.get_status()
        print(f"   服务状态: {status}")
    except Exception as e:
        print(f"   ❌ 获取服务状态失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 尝试处理任务
    print("\n9️⃣ 尝试处理测试任务...")
    try:
        result = service.process_contract_task(test_task)
        print(f"   处理结果: {result}")
    except Exception as e:
        print(f"   ❌ 处理任务失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ 所有测试通过！")
    return True

def test_direct_process_start():
    """测试直接启动独立进程"""
    print("\n10️⃣ 测试直接启动独立进程...")
    
    try:
        from Chrome.automation.services.enhanced_contract_service import EnhancedContractServiceClient
        
        client = EnhancedContractServiceClient()
        
        print("   启动服务...")
        success = client.start_service()
        
        if success:
            print(f"   ✅ 服务启动成功")
            print(f"   进程ID: {client.service_process.pid if client.service_process else 'N/A'}")
            
            # 等待一下
            time.sleep(2)
            
            # 检查进程状态
            if client.service_process and client.service_process.is_alive():
                print("   ✅ 服务进程运行中")
                
                # 提交测试任务
                print("   提交测试任务...")
                task_id = client.submit_task("get_novels_list")
                print(f"   ✅ 任务已提交，ID: {task_id}")
                
                # 等待结果
                print("   等待任务结果（最多30秒）...")
                result = client.get_task_result(task_id, timeout=30)
                
                if result:
                    print(f"   ✅ 获取到结果: {result}")
                else:
                    print("   ⚠️ 30秒内没有获取到结果")
            else:
                print("   ❌ 服务进程未运行")
                print(f"      进程是否存在: {client.service_process.is_alive()}")
                if client.service_process:
                    print(f"      退出代码: {client.service_process.exitcode}")
            
            # 停止服务
            print("   停止服务...")
            client.stop_service()
            
            return True
        else:
            print("   ❌ 服务启动失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔧 开始诊断签约服务启动问题...")
    print("\n请确保:")
    print("1. Chrome浏览器已启动并开启远程调试（端口9988）")
    print("2. 已登录番茄小说作家平台\n")
    
    # 运行测试
    if not test_service_startup():
        print("\n❌ 基础测试失败，无法继续")
        sys.exit(1)
    
    if not test_direct_process_start():
        print("\n❌ 进程启动测试失败")
        sys.exit(1)
    
    print("\n✅ 所有测试完成！如果看到这里，说明基础功能正常")
    print("请检查服务进程是否还在运行")
    
    input("\n按回车键退出...")
