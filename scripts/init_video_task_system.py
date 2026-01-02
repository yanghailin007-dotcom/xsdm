"""
视频任务管理系统初始化脚本

功能：
- 创建必要的目录结构
- 验证所有依赖是否安装
- 提供安装指导
"""

import os
import sys
from pathlib import Path


def create_directories():
    """创建必要的目录结构"""
    print("📁 创建目录结构...")
    
    directories = [
        "src/models",
        "src/schedulers",
        "src/workers",
        "src/websocket",
        "web/api",
        "web/templates",
        "web/static/css",
        "web/static/js",
        "视频项目",
        "generated_videos"
    ]
    
    for directory in directories:
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}/")
    
    print("✅ 目录结构创建完成\n")


def check_dependencies():
    """检查依赖包"""
    print("🔍 检查依赖包...")
    
    required_packages = {
        'flask': 'Flask web框架',
        'flask-socketio': 'WebSocket支持（可选）',
        'asyncio': '异步支持',
        'pathlib': '路径处理'
    }
    
    missing_packages = []
    
    for package, description in required_packages.items():
        try:
            __import__(package)
            print(f"  ✅ {package} - {description}")
        except ImportError:
            print(f"  ❌ {package} - {description} (未安装)")
            if package not in ['flask-socketio']:  # WebSocket是可选的
                missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
    else:
        print("\n✅ 所有必需依赖已安装\n")
    
    return missing_packages


def create_init_files():
    """创建__init__.py文件"""
    print("📝 创建__init__.py文件...")
    
    init_dirs = [
        "src/models",
        "src/schedulers",
        "src/workers",
        "src/websocket"
    ]
    
    for dir_path in init_dirs:
        init_file = Path(dir_path) / "__init__.py"
        if not init_file.exists():
            init_file.write_text('"""模块初始化文件"""\n')
            print(f"  ✅ {init_file}")
    
    print("✅ __init__.py文件创建完成\n")


def check_existing_files():
    """检查已创建的文件"""
    print("🔍 验证核心文件...")
    
    files = [
        ("src/models/video_task_models.py", "视频任务数据模型"),
        ("src/schedulers/video_task_scheduler.py", "任务调度器"),
        ("src/workers/video_worker.py", "视频Worker"),
        ("web/api/video_task_api.py", "任务管理API"),
        ("web/templates/video-task-manager.html", "任务管理页面"),
        ("web/static/css/video-task-manager.css", "样式文件"),
        ("web/static/js/video-task-manager.js", "前端脚本"),
        ("src/websocket/video_progress_ws.py", "WebSocket服务")
    ]
    
    all_exist = True
    for file_path, description in files:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path} - {description}")
        else:
            print(f"  ❌ {file_path} - {description} (未找到)")
            all_exist = False
    
    if all_exist:
        print("\n✅ 所有核心文件已创建\n")
    else:
        print("\n⚠️  部分文件缺失\n")
    
    return all_exist


def print_next_steps():
    """打印后续步骤"""
    print("=" * 60)
    print("🎉 视频任务管理系统初始化完成！")
    print("=" * 60)
    print()
    print("📋 后续步骤:")
    print()
    print("1. 注册API路由")
    print("   在 web/__init__.py 或 web服务器文件中添加:")
    print("   ```python")
    print("   from web.api.video_task_api import register_video_task_routes")
    print("   register_video_task_routes(app)")
    print("   ```")
    print()
    print("2. 添加路由")
    print("   在 web服务器中添加:")
    print("   ```python")
    print("   @app.route('/video-task-manager')")
    print("   def video_task_manager_page():")
    print("       return render_template('video-task-manager.html')")
    print("   ```")
    print()
    print("3. 安装可选依赖（推荐）")
    print("   ```bash")
    print("   pip install flask-socketio")
    print("   ```")
    print()
    print("4. 启动服务器")
    print("   访问: http://localhost:5000/video-task-manager")
    print()
    print("5. 使用系统")
    print("   - 在左侧配置镜头参数")
    print("   - 添加镜头到任务")
    print("   - 创建并启动任务")
    print("   - 实时查看生成进度")
    print()
    print("=" * 60)


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 视频任务管理系统初始化")
    print("=" * 60)
    print()
    
    # 创建目录
    create_directories()
    
    # 创建__init__.py文件
    create_init_files()
    
    # 检查依赖
    missing = check_dependencies()
    
    if missing:
        print("⚠️  请先安装缺失的依赖，然后重新运行此脚本")
        return
    
    # 验证文件
    all_exist = check_existing_files()
    
    if all_exist:
        print_next_steps()
    else:
        print("⚠️  请确保所有核心文件都已创建")


if __name__ == "__main__":
    main()