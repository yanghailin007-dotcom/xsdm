#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约服务诊断和修复工具
用于诊断和修复签约服务的状态问题
"""

import os
import sys
import json
import time
import signal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def check_service_status():
    """检查服务状态"""
    print("=" * 60)
    print("🔍 签约服务诊断工具")
    print("=" * 60)
    
    # 1. 检查状态文件
    print("\n1️⃣ 检查状态文件...")
    status_file = Path("logs/enhanced_contract_service_status.json")
    
    if status_file.exists():
        try:
            with open(status_file, 'r', encoding='utf-8') as f:
                status = json.load(f)
            print(f"   状态文件存在: {status_file}")
            print(f"   running: {status.get('running')}")
            print(f"   service_pid: {status.get('service_pid')}")
            
            # 检查进程是否存在
            pid = status.get('service_pid')
            if pid:
                if is_process_running(pid):
                    print(f"   ✅ 进程 {pid} 存在")
                else:
                    print(f"   ❌ 进程 {pid} 不存在（僵尸状态）")
                    return "zombie"
        except Exception as e:
            print(f"   ❌ 读取状态文件失败: {e}")
            return "error"
    else:
        print(f"   ℹ️ 状态文件不存在")
        return "no_file"
    
    return "ok"

def is_process_running(pid):
    """检查进程是否存在"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def cleanup_service_state():
    """清理服务状态"""
    print("\n2️⃣ 清理服务状态...")
    
    # 删除状态文件
    status_file = Path("logs/enhanced_contract_service_status.json")
    if status_file.exists():
        try:
            status_file.unlink()
            print(f"   ✅ 已删除状态文件: {status_file}")
        except Exception as e:
            print(f"   ❌ 删除状态文件失败: {e}")
            return False
    
    # 杀死可能残留的进程
    print("\n3️⃣ 检查并清理残留进程...")
    try:
        import subprocess
        # 查找可能的签约服务进程
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'enhanced_contract_service' in line.lower():
                    # 提取PID
                    parts = line.split(',')
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1].strip('"'))
                            print(f"   🔪 终止残留进程: {pid}")
                            os.kill(pid, signal.SIGTERM)
                            time.sleep(1)
                        except:
                            pass
    except:
        pass
    
    print("   ✅ 清理完成")
    return True

def restart_service():
    """重启服务"""
    print("\n4️⃣ 重启签约服务...")
    
    try:
        from Chrome.automation.services.enhanced_contract_service import enhanced_contract_client
        
        # 停止服务
        print("   停止现有服务...")
        enhanced_contract_client.stop_service()
        time.sleep(2)
        
        # 启动服务
        print("   启动新服务...")
        success = enhanced_contract_client.start_service()
        
        if success:
            print("   ✅ 服务启动成功")
            return True
        else:
            print("   ❌ 服务启动失败")
            return False
            
    except Exception as e:
        print(f"   ❌ 重启服务失败: {e}")
        return False

def verify_service():
    """验证服务状态"""
    print("\n5️⃣ 验证服务状态...")
    time.sleep(2)
    
    try:
        from Chrome.automation.services.enhanced_contract_service import enhanced_contract_client
        status = enhanced_contract_client.get_service_status()
        
        print(f"   running: {status.get('running')}")
        print(f"   process_running: {status.get('process_running')}")
        
        if status.get('running') and status.get('process_running'):
            print("   ✅ 服务状态正常")
            return True
        else:
            print("   ❌ 服务状态异常")
            return False
            
    except Exception as e:
        print(f"   ❌ 验证服务失败: {e}")
        return False

def main():
    """主函数"""
    print("\n🔧 开始诊断和修复签约服务...")
    
    # 1. 检查服务状态
    status = check_service_status()
    
    if status == "ok":
        print("\n✅ 服务状态正常，无需修复")
        return
    
    # 2. 清理状态
    if not cleanup_service_state():
        print("\n❌ 清理失败，无法继续")
        return
    
    # 3. 重启服务
    if not restart_service():
        print("\n❌ 重启失败")
        return
    
    # 4. 验证服务
    if verify_service():
        print("\n" + "=" * 60)
        print("✅ 修复完成！服务已恢复正常")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 修复失败，请检查日志")
        print("=" * 60)

if __name__ == "__main__":
    main()
