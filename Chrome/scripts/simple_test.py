"""
简化的系统测试脚本
避免依赖问题，专注于核心功能测试
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
        # 直接导入配置加载器
        sys.path.insert(0, str(project_root / "Chrome" / "automation" / "utils"))
        from config_loader import ConfigLoader
        
        # 加载配置
        config_loader = ConfigLoader()
        print("配置加载器创建成功")
        
        # 测试配置获取
        debug_port = config_loader.get_debug_port()
        print(f"调试端口: {debug_port}")
        
        novel_path = config_loader.get_novel_path()
        print(f"小说路径: {novel_path}")
        
        publish_times = config_loader.get_publish_times()
        print(f"发布时间: {publish_times}")
        
        # 验证配置
        if config_loader.validate_config():
            print("配置验证通过")
            return True
        else:
            print("配置验证失败")
            return False
            
    except Exception as e:
        print(f"配置加载测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_file_operations():
    """测试文件操作功能"""
    print("\n=== 测试文件操作 ===")
    
    try:
        sys.path.insert(0, str(project_root / "Chrome" / "automation" / "utils"))
        from file_handler import FileHandler
        
        file_handler = FileHandler()
        
        # 测试目录创建
        test_dir = "test_temp_dir"
        created_path = file_handler.ensure_directory_exists(test_dir)
        print(f"目录创建成功: {created_path}")
        
        # 测试JSON操作
        test_data = {"test": "data", "number": 123}
        test_file = os.path.join(test_dir, "test.json")
        
        if file_handler.save_json_file(test_file, test_data):
            print("JSON文件保存成功")
            
            loaded_data = file_handler.load_json_file(test_file)
            if loaded_data and loaded_data.get("test") == "data":
                print("JSON文件加载成功")
            else:
                print("JSON文件加载失败")
                return False
        else:
            print("JSON文件保存失败")
            return False
        
        # 清理测试文件
        import shutil
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            print("测试文件清理完成")
        
        return True
        
    except Exception as e:
        print(f"文件操作测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_directory_structure():
    """测试目录结构"""
    print("\n=== 测试目录结构 ===")
    
    try:
        chrome_dir = project_root / "Chrome"
        
        # 检查关键目录
        required_dirs = [
            "automation",
            "automation/core", 
            "automation/managers",
            "automation/utils",
            "config",
            "scripts",
            "docs"
        ]
        
        for dir_name in required_dirs:
            dir_path = chrome_dir / dir_name
            if dir_path.exists():
                print(f"目录存在: {dir_name}")
            else:
                print(f"目录缺失: {dir_name}")
                return False
        
        # 检查关键文件
        required_files = [
            "automation/utils/config_loader.py",
            "automation/utils/file_handler.py", 
            "automation/utils/ui_helper.py",
            "config/automation_config.yaml",
            "scripts/start_automation.py",
            "README.md"
        ]
        
        for file_name in required_files:
            file_path = chrome_dir / file_name
            if file_path.exists():
                print(f"文件存在: {file_name}")
            else:
                print(f"文件缺失: {file_name}")
                return False
        
        print("目录结构检查通过")
        return True
        
    except Exception as e:
        print(f"目录结构测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始简化功能测试...\n")
    
    tests = [
        ("目录结构", test_directory_structure),
        ("配置加载", test_config_loading), 
        ("文件操作", test_file_operations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"测试: {test_name}")
        print('='*50)
        
        if test_func():
            print(f"{test_name} 测试通过")
            passed += 1
        else:
            print(f"{test_name} 测试失败")
    
    print(f"\n{'='*50}")
    print(f"测试总结")
    print('='*50)
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")
    
    if passed == total:
        print("所有核心测试通过！系统重构成功！")
        return True
    else:
        print("部分测试失败，请检查相关功能")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)