"""
自动化发布系统启动脚本
整合浏览器管理、小说发布和签约管理功能
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入自动化模块
from automation import (
    ConfigLoader, get_config_loader, reload_config,
    BrowserManager, NovelPublisher, ContractManager
)


class AutomationSystem:
    """自动化系统主类"""
    
    def __init__(self):
        """初始化自动化系统"""
        print("=== 番茄小说自动化发布系统 ===")
        print("正在初始化系统...")
        
        # 加载配置
        try:
            self.config_loader = get_config_loader()
            if not self.config_loader.validate_config():
                print("✗ 配置文件验证失败，请检查配置")
                return
            print("✓ 配置文件加载成功")
        except Exception as e:
            print(f"✗ 配置文件加载失败: {e}")
            print("使用默认配置继续...")
            self.config_loader = ConfigLoader()
        
        # 初始化各个管理器
        self.browser_manager = BrowserManager(self.config_loader)
        self.novel_publisher = NovelPublisher(self.config_loader)
        self.contract_manager = ContractManager(self.config_loader)
        
        # 确保目录存在
        self._ensure_directories()
        
        print("✓ 系统初始化完成")
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.config_loader.get_novel_path(),
            self.config_loader.get_published_path(),
            "logs"
        ]
        
        for directory in directories:
            self.config_loader.ensure_directory_exists(directory)
    
    def run_scan_cycle(self) -> bool:
        """
        运行主扫描循环
        
        Returns:
            是否处理了任何小说项目
        """
        print(f"\n{'=' * 60}")
        print(f"开始扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print('=' * 60)
        
        # 连接浏览器
        playwright, browser, page, context = self.browser_manager.connect_to_browser()
        if not browser:
            print("浏览器连接失败，等待下次扫描")
            return False
        
        try:
            # 清理多余页面
            self.browser_manager.cleanup_extra_pages(context)
            
            # 导航到番茄小说首页
            if not self.browser_manager.navigate_to_fanqie_homepage(page):
                print("导航到番茄小说首页失败")
                return False
            
            # 导航到作家专区
            writer_page = self.browser_manager.navigate_to_writer_platform(page, context)
            if not writer_page:
                print("导航到作家专区失败")
                return False
            
            # 处理小说发布
            success_count = self._process_novel_projects(writer_page)
            
            # 处理签约管理
            print("\n开始处理签约管理...")
            contract_success = self.contract_manager.check_and_handle_contract_management(writer_page)
            
            # 处理作品推荐
            print("\n开始处理作品推荐...")
            recommendation_success = self.contract_manager.check_and_handle_recommendations(writer_page)
            
            # 关闭作家专区页面
            writer_page.close()
            
            print(f"\n{'=' * 60}")
            print(f"扫描完成！")
            print(f"小说项目处理: {success_count}")
            print(f"签约管理处理: {'成功' if contract_success else '无处理'}")
            print(f"作品推荐处理: {'成功' if recommendation_success else '无处理'}")
            print('=' * 60)
            
            return success_count > 0 or contract_success or recommendation_success
            
        except Exception as e:
            print(f"扫描过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            # 清理浏览器连接
            self.browser_manager.close_browser()
    
    def _process_novel_projects(self, page) -> int:
        """
        处理小说项目
        
        Args:
            page: 页面对象
            
        Returns:
            成功处理的项目数量
        """
        novel_path = self.config_loader.get_novel_path()
        json_suffix = self.config_loader.get('paths.required_json_suffix', '项目信息.json')
        
        # 获取小说项目文件
        json_files = self.novel_publisher.file_handler.list_json_files(novel_path, json_suffix)
        if not json_files:
            print(f"在目录 '{novel_path}' 中未找到小说项目文件")
            print(f"请确保您的JSON文件命名以 '{json_suffix}' 结尾")
            return 0
        
        print(f"找到 {len(json_files)} 个小说项目")
        
        # 处理每个小说项目
        success_count = 0
        for file_index, json_file in enumerate(json_files):
            print(f"\n{'=' * 50}")
            print(f"处理第 {file_index + 1} 个小说项目")
            
            try:
                if self.novel_publisher.publish_novel(page, json_file):
                    success_count += 1
            except Exception as e:
                print(f"处理小说项目时出错: {e}")
                continue
        
        return success_count
    
    def run_continuous_mode(self):
        """运行连续扫描模式"""
        scan_interval = self.config_loader.get_scan_interval()
        scan_count = 0
        
        print(f"程序将每 {scan_interval} 秒自动扫描一次")
        print("按 Ctrl+C 退出程序")
        
        try:
            while True:
                scan_count += 1
                print(f"\n{'=' * 60}")
                print(f"开始第 {scan_count} 次扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print('=' * 60)
                
                try:
                    self.run_scan_cycle()
                except Exception as e:
                    print(f"扫描过程中发生错误: {e}")
                
                # 等待下一次扫描
                print(f"\n[{datetime.now()}] 等待下一次扫描... ({scan_interval} 秒后)")
                time.sleep(scan_interval)
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断，退出...")
        except Exception as e:
            print(f"\n程序发生未知错误: {e}")
    
    def run_single_scan(self):
        """运行单次扫描"""
        try:
            return self.run_scan_cycle()
        except Exception as e:
            print(f"单次扫描失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='番茄小说自动化发布系统')
    parser.add_argument('--mode', choices=['single', 'continuous'], default='continuous',
                       help='运行模式: single(单次扫描) 或 continuous(连续扫描)')
    parser.add_argument('--config', help='配置文件目录路径')
    
    args = parser.parse_args()
    
    # 重新加载配置（如果指定了配置目录）
    if args.config:
        reload_config(args.config)
    
    # 创建并运行自动化系统
    try:
        automation_system = AutomationSystem()
        
        if args.mode == 'single':
            print("运行单次扫描模式")
            success = automation_system.run_single_scan()
            sys.exit(0 if success else 1)
        else:
            print("运行连续扫描模式")
            automation_system.run_continuous_mode()
            
    except Exception as e:
        print(f"系统启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()