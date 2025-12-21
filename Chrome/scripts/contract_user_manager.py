#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
签约用户管理脚本
用于管理和切换签约用户配置
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from Chrome.automation.utils.config_loader import ConfigLoader, get_config_loader
from Chrome.automation.managers.contract_manager import ContractManager


class ContractUserManager:
    """签约用户管理器"""
    
    def __init__(self):
        """初始化用户管理器"""
        self.config_loader = get_config_loader()
        self.contract_manager = ContractManager(self.config_loader)
    
    def show_menu(self):
        """显示主菜单"""
        print("\n" + "="*50)
        print("           签约用户管理系统")
        print("="*50)
        print("1. 列出所有签约用户")
        print("2. 查看当前用户信息")
        print("3. 切换签约用户")
        print("4. 验证当前用户配置")
        print("5. 启用/禁用用户")
        print("6. 添加新用户")
        print("7. 退出系统")
        print("="*50)
    
    def list_users(self):
        """列出所有用户"""
        print("\n📋 用户列表:")
        self.contract_manager.list_users()
    
    def show_current_user(self):
        """显示当前用户信息"""
        print("\n👤 当前用户信息:")
        current_user = self.contract_manager.get_current_user_info()
        
        if not current_user:
            print("❌ 无法获取当前用户信息")
            return
        
        print(f"用户ID: {current_user['user_id']}")
        print(f"用户名: {current_user['name']}")
        print(f"状态: {'✅ 启用' if current_user['enabled'] else '❌ 禁用'}")
        
        contact_info = current_user.get('contact_info', {})
        print("\n📞 联系信息:")
        print(f"  手机: {contact_info.get('phone', '未设置')}")
        print(f"  邮箱: {contact_info.get('email', '未设置')}")
        print(f"  QQ: {contact_info.get('qq', '未设置')}")
        print(f"  银行卡: {contact_info.get('bank_account', '未设置')}")
        print(f"  银行支行: {contact_info.get('bank_branch', '未设置')}")
        
        address = contact_info.get('address', {})
        print(f"  地址: {address.get('province', '')} {address.get('city', '')} {address.get('detail', '')}")
    
    def switch_user(self):
        """切换用户"""
        print("\n🔄 切换签约用户")
        
        # 获取所有启用的用户
        enabled_users = self.config_loader.get_enabled_contract_users()
        
        if not enabled_users:
            print("❌ 没有启用的用户可选")
            return
        
        print("可用用户:")
        user_list = list(enabled_users.keys())
        for i, user_id in enumerate(user_list, 1):
            user_name = enabled_users[user_id].get('name', user_id)
            current = " (当前)" if user_id == self.config_loader.get_current_contract_user() else ""
            print(f"{i}. {user_id} - {user_name}{current}")
        
        try:
            choice = input("\n请选择用户 (输入数字): ").strip()
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(user_list):
                    selected_user = user_list[index]
                    if self.contract_manager.switch_user(selected_user):
                        print(f"✅ 已切换到用户: {enabled_users[selected_user].get('name', selected_user)}")
                    else:
                        print("❌ 切换用户失败")
                else:
                    print("❌ 无效的选择")
            else:
                print("❌ 请输入有效数字")
        except KeyboardInterrupt:
            print("\n\n操作已取消")
        except Exception as e:
            print(f"❌ 切换用户时出错: {e}")
    
    def validate_current_user(self):
        """验证当前用户配置"""
        print("\n🔍 验证当前用户配置")
        
        if self.contract_manager.validate_current_user():
            print("✅ 当前用户配置有效")
        else:
            print("❌ 当前用户配置无效")
    
    def toggle_user_status(self):
        """启用/禁用用户"""
        print("\n⚙️ 启用/禁用用户")
        
        all_users = self.config_loader.get_all_contract_users()
        if not all_users:
            print("❌ 没有找到用户配置")
            return
        
        print("用户列表:")
        user_list = list(all_users.keys())
        for i, user_id in enumerate(user_list, 1):
            user_name = all_users[user_id].get('name', user_id)
            enabled = all_users[user_id].get('enabled', False)
            status = "✅ 启用" if enabled else "❌ 禁用"
            print(f"{i}. {user_id} - {user_name} ({status})")
        
        try:
            choice = input("\n请选择用户 (输入数字): ").strip()
            if choice.isdigit():
                index = int(choice) - 1
                if 0 <= index < len(user_list):
                    selected_user = user_list[index]
                    current_status = all_users[selected_user].get('enabled', False)
                    
                    # 切换状态
                    new_status = not current_status
                    self.config_loader.config['contract']['users'][selected_user]['enabled'] = new_status
                    
                    status_text = "启用" if new_status else "禁用"
                    print(f"✅ 已{status_text}用户: {all_users[selected_user].get('name', selected_user)}")
                else:
                    print("❌ 无效的选择")
            else:
                print("❌ 请输入有效数字")
        except KeyboardInterrupt:
            print("\n\n操作已取消")
        except Exception as e:
            print(f"❌ 操作时出错: {e}")
    
    def add_new_user(self):
        """添加新用户"""
        print("\n➕ 添加新用户")
        
        try:
            user_id = input("请输入用户ID (如: user4): ").strip()
            if not user_id:
                print("❌ 用户ID不能为空")
                return
            
            # 检查用户是否已存在
            existing_users = self.config_loader.get_all_contract_users()
            if user_id in existing_users:
                print(f"❌ 用户 {user_id} 已存在")
                return
            
            name = input("请输入用户名: ").strip()
            phone = input("请输入手机号: ").strip()
            email = input("请输入邮箱: ").strip()
            qq = input("请输入QQ号: ").strip()
            bank_account = input("请输入银行卡号: ").strip()
            bank_branch = input("请输入银行支行: ").strip()
            province = input("请输入省份: ").strip()
            city = input("请输入城市: ").strip()
            detail = input("请输入详细地址: ").strip()
            
            # 创建新用户配置
            new_user_config = {
                'name': name,
                'enabled': True,
                'contact_info': {
                    'phone': phone,
                    'email': email,
                    'qq': qq,
                    'bank_account': bank_account,
                    'bank_branch': bank_branch,
                    'address': {
                        'province': province,
                        'city': city,
                        'detail': detail
                    }
                }
            }
            
            # 添加到配置中
            self.config_loader.config['contract']['users'][user_id] = new_user_config
            
            print(f"✅ 已添加新用户: {name} ({user_id})")
            
        except KeyboardInterrupt:
            print("\n\n操作已取消")
        except Exception as e:
            print(f"❌ 添加用户时出错: {e}")
    
    def run(self):
        """运行主程序"""
        print("🎉 欢迎使用签约用户管理系统!")
        
        while True:
            try:
                self.show_menu()
                choice = input("\n请选择操作 (1-7): ").strip()
                
                if choice == '1':
                    self.list_users()
                elif choice == '2':
                    self.show_current_user()
                elif choice == '3':
                    self.switch_user()
                elif choice == '4':
                    self.validate_current_user()
                elif choice == '5':
                    self.toggle_user_status()
                elif choice == '6':
                    self.add_new_user()
                elif choice == '7':
                    print("\n👋 感谢使用签约用户管理系统!")
                    break
                else:
                    print("❌ 无效的选择，请输入 1-7")
                
                input("\n按回车键继续...")
                
            except KeyboardInterrupt:
                print("\n\n👋 程序已退出")
                break
            except Exception as e:
                print(f"❌ 程序出错: {e}")
                input("\n按回车键继续...")


def main():
    """主函数"""
    manager = ContractUserManager()
    manager.run()


if __name__ == "__main__":
    main()