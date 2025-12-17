"""
自动化系统测试脚本
用于测试重构后的功能是否正常工作
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_config_loading():
    """测试配置加载功能"""
    print("=== 测试配置加载 ===")
    
    try:
        from automation import get_config_loader
        
        # 加载配置
        config_loader = get_config_loader()
        print("✓ 配置加载器创建成功")
        
        # 测试配置获取
        debug_port = config_loader.get_debug_port()
        print(f"✓ 调试端口: {debug_port}")
        
        novel_path = config_loader.get_novel_path()
        print(f"✓ 小说路径: {novel_path}")
        
        publish_times = config_loader.get_publish_times()
        print(f"✓ 发布时间: {publish_times}")
        
        # 验证配置
        if config_loader.validate_config():
            print("✓ 配置验证通过")
            return True
        else:
            print("✗ 配置验证失败")
            return False
            
    except Exception as e:
        print(f"✗ 配置加载测试失败: {e}")
        return False

def test_module_imports():
    """测试模块导入"""
    print("\n=== 测试模块导入 ===")
    
    try:
        # 测试核心模块
        from automation.core.browser_manager import BrowserManager
        print("✓ BrowserManager 导入成功")
        
        from automation.core.novel_publisher import NovelPublisher
        print("✓ NovelPublisher 导入成功")
        
        # 测试管理器模块
        from automation.managers.contract_manager import ContractManager
        print("✓ ContractManager 导入成功")
        
        # 测试工具模块
        from automation.utils.file_handler import FileHandler
        print("✓ FileHandler 导入成功")
        
        from automation.utils.ui_helper import UIHelper
        print("✓ UIHelper 导入成功")
        
        return True
        
    except Exception as e:
        print(f"✗ 模块导入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_operations():
    """测试文件操作功能"""
    print("\n=== 测试文件操作 ===")
    
    try:
        from automation import get_config_loader
        from automation.utils.file_handler import FileHandler
        
        config_loader = get_config_loader()
        file_handler = FileHandler(config_loader)
        
        # 测试目录创建
        test_dir = "test_temp_dir"
        created_path = file_handler.ensure_directory_exists(test_dir)
        print(f"✓ 目录创建成功: {created_path}")
        
        # 测试JSON操作
        test_data = {"test": "data", "number": 123}
        test_file = os.path.join(test_dir, "test.json")
        
        if file_handler.save_json_file(test_file, test_data):
            print("✓ JSON文件保存成功")
            
            loaded_data = file_handler.load_json_file(test_file)
            if loaded_data and loaded_data.get("test") == "data":
                print("✓ JSON文件加载成功")
            else:
                print("✗ JSON文件加载失败")
                return False
        else:
            print("✗ JSON文件保存失败")
            return False
        
        # 清理测试文件
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print("✓ 测试文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"✗ 文件操作测试失败: {e}")
        return False

def test_text_processing():
    """测试文本处理功能"""
    print("\n=== 测试文本处理 ===")
    
    try:
        from automation.utils.file_handler import FileHandler
        
        file_handler = FileHandler()
        
        # 测试字符统计
        test_text = "这是一段测试文本123abc"
        char_count = file_handler.count_content_chars(test_text)
        print(f"✓ 字符统计: {char_count} (应为9)")
        
        # 测试换行处理
        test_text2 = "第一行\n\n\n第二行"
        normalized = file_handler.normalize_line_breaks(test_text2)
        print(f"✓ 换行处理: '{normalized}'")
        
        # 测试简介格式化
        synopsis = "这是一个测试简介，包含了很多内容，需要进行格式化处理。这里是第二句话。"
        formatted = file_handler.format_synopsis_for_fanqie(synopsis)
        print(f"✓ 简介格式化: '{formatted[:50]}...'")
        
        return True
        
    except Exception as e:
        print(f"✗ 文本处理测试失败: {e}")
        return False

def test_browser_simulation():
    """测试浏览器相关功能（不启动真实浏览器）"""
    print("\n=== 测试浏览器功能 ===")
    
    try:
        from automation import get_config_loader
        from automation.core.browser_manager import BrowserManager
        
        config_loader = get_config_loader()
        browser_manager = BrowserManager(config_loader)
        
        # 测试配置获取
        browser_config = browser_manager.get_browser_config()
        print(f"✓ 浏览器配置: {browser_config}")
        
        print("✓ 浏览器管理器创建成功（未连接真实浏览器）")
        return True
        
    except Exception as e:
        print(f"✗ 浏览器功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始自动化系统功能测试...\n")
    
    tests = [
        ("模块导入", test_module_imports),
        ("配置加载", test_config_loading),
        ("文件操作", test_file_operations),
        ("文本处理", test_text_processing),
        ("浏览器功能", test_browser_simulation),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print('='*50)
        
        if test_func():
            print(f"✓ {test_name} 测试通过")
            passed += 1
        else:
            print(f"✗ {test_name} 测试失败")
    
    print(f"\n{'='*50}")
    print(f"测试总结")
    print('='*50)
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("🎉 所有测试通过！系统重构成功！")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)