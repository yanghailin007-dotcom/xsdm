"""
验证部署包是否包含所有必要的UI资源
"""
import zipfile
from pathlib import Path

def verify_deploy_package():
    """验证部署包内容"""
    base_dir = Path(__file__).parent.parent.parent
    package_file = base_dir / 'deploy_package.zip'
    
    if not package_file.exists():
        print(f"❌ 部署包不存在: {package_file}")
        return False
    
    print("=" * 60)
    print("验证部署包内容")
    print("=" * 60)
    print(f"部署包: {package_file}")
    print(f"包大小: {package_file.stat().st_size / 1024 / 1024:.2f} MB")
    print()
    
    with zipfile.ZipFile(package_file, 'r') as zipf:
        all_files = zipf.namelist()
        total_files = len(all_files)
        
        # 关键UI资源检查
        ui_checks = {
            'web/templates/': ('HTML模板', ['phase-two-generation.html', 'phase-one-setup.html', 'chapter-view.html', 'video-studio.html']),
            'web/static/css/': ('CSS样式', ['style.css', 'phase-two-generation.css', 'video-studio.css']),
            'web/static/js/': ('JavaScript文件', ['phase-two-generation.js', 'phase-one-setup.js', 'video-studio.js']),
            'web/api/': ('API接口', ['phase_generation_api.py', 'video_generation_api.py', 'character_api.py']),
            'web/managers/': ('管理器', ['novel_manager.py']),
            'web/routes/': ('路由', []),
            'web/services/': ('服务', []),
            'src/core/': ('核心模块', ['ContentGenerator.py', 'ProjectManager.py']),
            'src/managers/': ('管理器模块', ['VideoGenerationManager.py']),
            'src/prompts/': ('提示词模块', ['Prompts.py', 'VideoScenePrompts.py']),
            'config/': ('配置文件', ['config.py', 'videoconfig.py']),
            'web/wsgi.py': ('WSGI入口', []),
        }
        
        all_passed = True
        missing_critical = []
        
        print("检查关键UI资源:")
        for path, (desc, critical_files) in ui_checks.items():
            files = [f for f in all_files if f.startswith(path)]
            
            if not files:
                print(f"  ❌ {desc}: 未找到任何文件！")
                all_passed = False
                missing_critical.append(desc)
            else:
                # 检查关键文件
                missing_files = []
                for critical_file in critical_files:
                    if not any(f.endswith(critical_file) for f in files):
                        missing_files.append(critical_file)
                
                if missing_files:
                    print(f"  ⚠️  {desc}: 找到 {len(files)} 个文件，但缺少关键文件:")
                    for mf in missing_files:
                        print(f"     - {mf}")
                    all_passed = False
                else:
                    print(f"  ✅ {desc}: {len(files)} 个文件（包含所有关键文件）")
        
        print()
        print("=" * 60)
        print("统计信息")
        print("=" * 60)
        print(f"总文件数: {total_files}")
        
        # 按类型统计
        html_files = [f for f in all_files if f.endswith('.html')]
        css_files = [f for f in all_files if f.endswith('.css')]
        js_files = [f for f in all_files if f.endswith('.js')]
        py_files = [f for f in all_files if f.endswith('.py')]
        
        print(f"  - HTML文件: {len(html_files)}")
        print(f"  - CSS文件: {len(css_files)}")
        print(f"  - JavaScript文件: {len(js_files)}")
        print(f"  - Python文件: {len(py_files)}")
        print()
        
        if all_passed:
            print("✅ 验证通过！部署包包含所有必要的UI资源。")
            return True
        else:
            print("❌ 验证失败！缺少以下关键资源:")
            for item in missing_critical:
                print(f"  - {item}")
            return False

if __name__ == '__main__':
    try:
        success = verify_deploy_package()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)