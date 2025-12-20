#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说自动发布程序 - Legacy版本启动器
用于启动 legacy 版本的自动发布程序，解决相对导入问题
"""

import sys
import os
from pathlib import Path

# 设置控制台编码为UTF-8
if sys.platform == "win32":
    import locale
    try:
        # 尝试设置UTF-8编码
        os.system('chcp 65001 >nul 2>&1')
    except:
        pass

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 添加 Chrome automation 目录到 Python 路径
chrome_automation_path = Path(__file__).parent
sys.path.insert(0, str(chrome_automation_path))

def main():
    """主函数"""
    try:
        print("启动番茄小说自动发布程序 - Legacy版本")
        print("=" * 60)
        
        # 直接运行新的重构后发布程序
        import subprocess
        import sys
        import os
        
        print("成功加载重构后的发布模块")
        print("=" * 60)
        
        # 运行主程序 - 使用 -m 参数来支持相对导入
        try:
            # 切换到 Chrome/automation 目录
            automation_dir = os.path.dirname(__file__)
            result = subprocess.run([
                sys.executable, '-m', 'legacy.main_controller'
            ],
            cwd=automation_dir,
            capture_output=False,
            text=True)
            return result.returncode == 0
        except Exception as e:
            print(f"运行主程序时出错: {e}")
            return False
        
    except ImportError as e:
        print(f"导入错误: {e}")
        print("\n可能的解决方案:")
        print("1. 确保所有依赖模块都已安装")
        print("2. 检查 Python 路径设置")
        print("3. 尝试直接运行: python -m Chrome.automation.legacy.main_controller")
        print("4. 确保新的重构模块文件存在: Chrome/automation/legacy/main_controller.py")
        return False
        
    except Exception as e:
        print(f"运行错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n程序正常结束")
    else:
        print("\n程序异常结束")
        sys.exit(1)