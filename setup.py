#!/usr/bin/env python3
"""
=================================================================
大文娱系统 - 初始化安装脚本 (Setup Script)
=================================================================
一键完成：环境检查 → 检查pip → 安装依赖 → 启动服务

使用方法:
    第一次使用或环境有问题时运行:  python setup.py
    或直接双击运行 setup.py

功能:
    1. 检查 Python 环境（需要 Python 3.11+）
    2. 检查 pip 包管理器
    3. 安装所有项目依赖
    4. 启动 Web 服务
=================================================================
"""

import sys
import os
import subprocess
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except:
        pass

# 颜色定义
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header():
    """打印标题"""
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  大文娱系统 - 初始化安装{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}")
    print()

def print_step(step_num, total, message):
    """打印步骤"""
    print(f"{Colors.BLUE}[{step_num}/{total}]{Colors.RESET} {message}")

def print_ok(message):
    """打印成功信息"""
    print(f"  {Colors.GREEN}[OK]{Colors.RESET} {message}")

def print_warn(message):
    """打印警告信息"""
    print(f"  {Colors.YELLOW}[WARN]{Colors.RESET} {message}")

def print_error(message):
    """打印错误信息"""
    print(f"  {Colors.RED}[ERR]{Colors.RESET} {message}")

def get_python_executable():
    """获取 Python 可执行文件路径"""
    # 优先使用系统 Python (通过 bat 脚本传递或环境检测)
    if sys.executable and "python.exe" in sys.executable.lower():
        return sys.executable
    
    # 检查系统 Python
    try:
        result = subprocess.run(["python", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "python"
    except:
        pass
    
    # 尝试 py 启动器
    try:
        result = subprocess.run(["py", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            return "py"
    except:
        pass
    
    return None

def install_dependencies(project_dir, python_exe, step_num=3, total_steps=4):
    """安装项目依赖"""
    print_step(step_num, total_steps, "安装项目依赖...")
    
    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        print_error("找不到 requirements.txt")
        return False
    
    try:
        print("  正在安装依赖包 (可能需要几分钟)...")
        result = subprocess.run(
            [python_exe, "-m", "pip", "install", "-r", str(req_file), "--no-warn-script-location"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # 额外安装 Pillow
            subprocess.run([python_exe, "-m", "pip", "install", "Pillow", "--no-warn-script-location"],
                          capture_output=True)
            print_ok("依赖安装完成")
            return True
        else:
            print_error("依赖安装失败")
            print(result.stderr)
            return False
            
    except Exception as e:
        print_error(f"安装依赖时出错: {e}")
        return False

def check_and_fix_code(project_dir, python_exe):
    """检查并修复代码问题"""
    print("\n检查代码兼容性...")
    
    # 修复 veo_video_api.py 中的 f-string 问题
    veo_file = project_dir / "web" / "api" / "veo_video_api.py"
    if veo_file.exists():
        content = veo_file.read_text(encoding='utf-8')
        # 检查是否存在 f-string 中的反斜杠问题
        if 'f"/project-files/{str(relative_path).replace' in content:
            content = content.replace(
                'video_url = f"/project-files/{str(relative_path).replace(\'\\\\\', \'/\')}"',
                'path_str = str(relative_path).replace(\'\\\\\', \'/\')\n            video_url = f"/project-files/{path_str}"'
            )
            veo_file.write_text(content, encoding='utf-8')
            print_ok("已修复代码兼容性问题")

def start_service(project_dir, python_exe):
    """启动服务"""
    print(f"\n{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.GREEN}{Colors.BOLD}  初始化完成！正在启动服务...{Colors.RESET}")
    print(f"{Colors.GREEN}{'='*60}{Colors.RESET}\n")
    
    start_script = project_dir / "scripts" / "start_web_server.py"
    
    # 使用 os.system 启动，保持控制台窗口
    os.chdir(project_dir)
    os.system(f'"{python_exe}" "{start_script}"')

def main():
    """主函数"""
    print_header()
    
    project_dir = Path(__file__).parent
    total_steps = 4
    
    # 步骤 1: 检查环境
    print_step(1, total_steps, "检查运行环境...")
    python_exe = get_python_executable()
    
    if not python_exe:
        print_error("未找到 Python 环境")
        print()
        print("请通过以下方式安装 Python：")
        print()
        print("方法一（推荐）：从 Microsoft Store 安装")
        print("    1. 打开 Microsoft Store")
        print("    2. 搜索 'Python'")
        print("    3. 安装 Python 3.12 或更高版本")
        print()
        print("方法二：从官网下载安装包")
        print("    1. 访问 https://www.python.org/downloads/")
        print("    2. 下载 Python 3.12 或更高版本")
        print("    3. 安装时勾选 'Add Python to PATH'")
        print()
        print("安装完成后，重新运行此脚本。")
        input("\n按 Enter 键退出...")
        return
    
    print_ok(f"找到 Python: {python_exe}")
    
    # 步骤 2: 检查 pip
    print_step(2, total_steps, "检查 pip 包管理器...")
    try:
        result = subprocess.run([python_exe, "-m", "pip", "--version"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            print_ok(f"pip 已安装: {result.stdout.strip()}")
        else:
            print_error("pip 未安装")
            print("请重新安装 Python，并确保勾选 'Add Python to PATH'")
            input("\n按 Enter 键退出...")
            return
    except Exception as e:
        print_error(f"检查 pip 时出错: {e}")
        input("\n按 Enter 键退出...")
        return
    
    # 步骤 3: 安装依赖
    print_step(3, total_steps, "安装项目依赖...")
    if not install_dependencies(project_dir, python_exe):
        print_error("依赖安装失败")
        input("\n按 Enter 键退出...")
        return
    
    # 步骤 4: 检查并修复代码
    print_step(4, total_steps, "检查代码兼容性...")
    check_and_fix_code(project_dir, python_exe)
    print_ok("代码检查完成")
    
    # 启动服务
    start_service(project_dir, python_exe)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}用户取消操作{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}发生错误: {e}{Colors.RESET}")
        import traceback
        traceback.print_exc()
        input("\n按 Enter 键退出...")
