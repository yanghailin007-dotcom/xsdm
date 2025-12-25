#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动签约使用示例
演示如何使用新增的自动签约功能
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Chrome.automation.api.contract_api import contract_api
from Chrome.automation.services.enhanced_contract_service import enhanced_contract_client


def print_separator(title=""):
    """打印分隔符"""
    print("\n" + "=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)


def example_get_enabled_users():
    """示例1: 获取所有启用的用户配置"""
    print_separator("示例1: 获取启用的用户配置")
    
    result = contract_api.get_enabled_users()
    
    if result["success"]:
        print(f"\n✓ 找到 {result['count']} 个启用的用户:")
        for user in result["users"]:
            print(f"\n  用户ID: {user['user_id']}")
            print(f"  姓名: {user['name']}")
            contact_info = user['contact_info']
            print(f"  手机: {contact_info.get('phone', 'N/A')}")
            print(f"  邮箱: {contact_info.get('email', 'N/A')}")
    else:
        print(f"\n✗ 获取用户列表失败: {result.get('error')}")


def example_get_contractable_novels():
    """示例2: 获取可签约的小说列表"""
    print_separator("示例2: 获取可签约的小说列表")
    
    # 确保服务已启动
    if not enhanced_contract_client.is_service_running():
        print("\n正在启动签约服务...")
        start_result = enhanced_contract_client.start_service()
        if not start_result:
            print("✗ 签约服务启动失败")
            return
        print("✓ 签约服务启动成功")
    
    # 提交获取小说列表任务
    print("\n正在获取可签约小说列表...")
    result = contract_api.get_contractable_novels()
    
    if result["success"]:
        task_id = result["task_id"]
        print(f"✓ 任务已提交，任务ID: {task_id}")
        print("\n等待结果...")
        
        # 获取任务结果
        task_result = contract_api.get_task_status(task_id)
        print(f"任务状态: {task_result}")
    else:
        print(f"✗ 获取小说列表失败: {result.get('error')}")


def example_auto_sign_novel():
    """示例3: 自动签约小说"""
    print_separator("示例3: 自动签约小说")
    
    # 确保服务已启动
    if not enhanced_contract_client.is_service_running():
        print("\n正在启动签约服务...")
        enhanced_contract_client.start_service()
    
    # 这里需要用户输入小说标题和用户ID
    print("\n请提供以下信息:")
    novel_title = input("  小说标题: ").strip()
    user_id = input("  用户ID (如: user1, user2): ").strip()
    
    if not novel_title or not user_id:
        print("\n✗ 小说标题和用户ID不能为空")
        return
    
    # 提交自动签约任务
    print(f"\n正在为《{novel_title}》使用用户 {user_id} 进行签约...")
    result = contract_api.submit_auto_sign_task(novel_title, user_id)
    
    if result["success"]:
        task_id = result["task_id"]
        print(f"✓ 签约任务已提交，任务ID: {task_id}")
        print(f"\n{result['message']}")
        
        # 注意: 实际签约需要一些时间，可以通过get_task_status查询结果
        print("\n提示: 使用 get_task_status('{task_id}') 查询签约结果".format(task_id=task_id))
    else:
        print(f"\n✗ 提交签约任务失败: {result.get('error')}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  番茄自动签约功能使用示例")
    print("=" * 60)
    
    print("\n请选择要执行的操作:")
    print("  1. 获取启用的用户配置")
    print("  2. 获取可签约的小说列表")
    print("  3. 自动签约小说")
    print("  0. 退出")
    
    while True:
        choice = input("\n请输入选项 (0-3): ").strip()
        
        if choice == "0":
            print("\n退出程序")
            break
        elif choice == "1":
            example_get_enabled_users()
        elif choice == "2":
            example_get_contractable_novels()
        elif choice == "3":
            example_auto_sign_novel()
        else:
            print("\n无效的选项，请重新输入")


if __name__ == "__main__":
    main()