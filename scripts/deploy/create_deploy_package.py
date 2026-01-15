"""
创建部署包脚本
确保所有UI资源文件都被正确打包
"""
import os
import zipfile
from pathlib import Path

def should_exclude(file_path, base_dir):
    """判断文件是否应该被排除"""
    exclude_dirs = {
        '__pycache__',
        '.git',
        'logs',
        'generated_images',
        'temp_fanqie_upload',
        '小说项目',
        'Chrome',
        'knowledge_base',
        'ai_enhanced_settings',
        'fusion_settings',
        'deploy_logs',
        'chapter_failures',
        '.pytest_cache',
        'node_modules',
        'venv',
        'env',
        '.venv'
    }
    
    exclude_patterns = {
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        'test_*.py',
        '*.db',
        '*.log',
        '.env*'
    }
    
    # 检查相对路径
    rel_path = file_path.relative_to(base_dir)
    parts = rel_path.parts
    
    # 检查是否在排除的目录中
    for part in parts:
        if part in exclude_dirs:
            return True
    
    # 检查文件名模式
    filename = file_path.name
    for pattern in exclude_patterns:
        if filename.startswith(pattern.replace('*', '')) or pattern in str(filename):
            if pattern.startswith('test_'):
                if filename.startswith('test_'):
                    return True
            elif pattern.startswith('*.'):
                if filename.endswith(pattern.replace('*', '')):
                    return True
            elif pattern in filename:
                return True
    
    return False

def create_deploy_package():
    """创建部署包"""
    base_dir = Path(__file__).parent.parent.parent  # 项目根目录
    output_file = base_dir / 'deploy_package.zip'
    
    # 需要包含的目录和文件
    include_paths = [
        'src',
        'web',
        'config',
        'requirements.txt',
        'web/wsgi.py'
    ]
    
    print("=" * 60)
    print("创建部署包")
    print("=" * 60)
    print(f"项目根目录: {base_dir}")
    print(f"输出文件: {output_file}")
    print()
    
    # 统计信息
    total_files = 0
    excluded_files = 0
    included_dirs = set()
    
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for include_path in include_paths:
            full_path = base_dir / include_path
            
            if not full_path.exists():
                print(f"⚠️  警告: 路径不存在 - {include_path}")
                continue
            
            if full_path.is_file():
                # 单个文件
                if should_exclude(full_path, base_dir):
                    excluded_files += 1
                    print(f"  ❌ 排除文件: {include_path}")
                else:
                    arcname = include_path.replace('\\', '/')
                    zipf.write(full_path, arcname)
                    total_files += 1
                    print(f"  ✅ 添加文件: {include_path}")
            elif full_path.is_dir():
                # 目录，递归处理
                print(f"\n📁 处理目录: {include_path}")
                dir_count = 0
                for root, dirs, files in os.walk(full_path):
                    root_path = Path(root)
                    
                    # 移除__pycache__等目录
                    dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git']]
                    
                    for file in files:
                        file_path = root_path / file
                        rel_path = file_path.relative_to(base_dir)
                        arcname = str(rel_path).replace('\\', '/')
                        
                        if should_exclude(file_path, base_dir):
                            excluded_files += 1
                            dir_count += 1
                            if dir_count <= 5:  # 只显示前5个排除的文件
                                print(f"  ❌ 排除: {arcname}")
                        else:
                            zipf.write(file_path, arcname)
                            total_files += 1
                            dir_count += 1
                            included_dirs.add(include_path)
                            if dir_count <= 5:  # 只显示前5个包含的文件
                                print(f"  ✅ 添加: {arcname}")
                
                if dir_count > 10:
                    print(f"  ... (共处理 {dir_count} 个文件)")
    
    print()
    print("=" * 60)
    print("✅ 部署包创建完成")
    print("=" * 60)
    print(f"总文件数: {total_files}")
    print(f"排除文件: {excluded_files}")
    print(f"包含目录: {len(included_dirs)}")
    print(f"包大小: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"输出路径: {output_file}")
    print()
    
    # 验证关键UI资源是否包含
    print("验证关键UI资源:")
    with zipfile.ZipFile(output_file, 'r') as zipf:
        ui_checks = [
            ('web/templates/', 'HTML模板'),
            ('web/static/css/', 'CSS样式'),
            ('web/static/js/', 'JavaScript文件'),
            ('web/api/', 'API接口'),
            ('web/managers/', '管理器'),
            ('src/', '源代码'),
        ]
        
        for path, desc in ui_checks:
            files = [f for f in zipf.namelist() if f.startswith(path)]
            if files:
                print(f"  ✅ {desc}: {len(files)} 个文件")
            else:
                print(f"  ❌ {desc}: 未找到！")
    
    print()

if __name__ == '__main__':
    try:
        create_deploy_package()
        print("✅ 部署包创建成功！")
    except Exception as e:
        print(f"❌ 创建部署包失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)