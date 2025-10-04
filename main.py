"""主程序入口"""
import NovelGenerator
from config import CONFIG

# 首先导入 utils 来启用全局时间戳
import utils
# 现在所有 print 都会自动带时间戳

def main():
    """主函数"""
    generator = NovelGenerator.NovelGenerator(CONFIG)
    
    # 检查API密钥
    if not any(CONFIG["api_keys"].values()):
        print("❌❌ 请先设置API密钥")
        return
    
    print("🤖🤖 番茄小说智能生成器（优化版本）")
    print("="*50)
    print("特点: 优化生成速度，智能跳过优化，缓存机制")
    print("功能: 全自动小说生成，质量评估，AI痕迹检测")
    print("架构: APIClient, ContentGenerator, QualityAssessor, ProjectManager")
    print("="*50)
    
    try:
        # 检查是否有现有项目
        creative_seed = input("请输入小说创意种子（如：末世重生带系统、霸总追妻火葬场）: ").strip()
        if not creative_seed:
            creative_seed = "都市异能系统流"
            print(f"使用默认创意: {creative_seed}")
        
        # 查找相关项目
        existing_projects = generator.project_manager.find_existing_projects(creative_seed)
        
        if existing_projects:
            print(f"\n📚📚 找到{len(existing_projects)}个相关项目:")
            for i, project in enumerate(existing_projects, 1):
                print(f"  {i}. {project['title']} ({project['completed_chapters']}/{project['total_chapters']}章) - {project['stage']}")
            
            choice = input("\n请选择: (1)继续现有项目 (2)创建新项目 (3)查看所有项目: ").strip()
            
            if choice == "1" and existing_projects:
                # 继续最新项目
                selected_project = existing_projects[0]
                if generator.load_project_data(selected_project["filename"]):
                    try:
                        total_chapters = int(input(f"请输入总章节数 (当前{generator.novel_data['current_progress']['total_chapters']}章, 默认保持不变): ") or generator.novel_data['current_progress']['total_chapters'])
                    except ValueError:
                        total_chapters = generator.novel_data['current_progress']['total_chapters']
                    
                    success = generator.resume_generation(total_chapters)
                else:
                    print("加载项目失败，创建新项目")
                    success = start_new_project(generator, creative_seed)
            
            elif choice == "2":
                success = start_new_project(generator, creative_seed)
                
            elif choice == "3":
                # 显示所有项目
                all_projects = generator.project_manager.find_existing_projects()
                print(f"\n📚📚 所有项目 ({len(all_projects)}个):")
                for i, project in enumerate(all_projects, 1):
                    print(f"  {i}. {project['title']} ({project['completed_chapters']}/{project['total_chapters']}章) - {project['stage']}")
                
                project_choice = input("选择要继续的项目编号 (回车创建新项目): ").strip()
                if project_choice.isdigit() and 1 <= int(project_choice) <= len(all_projects):
                    selected_project = all_projects[int(project_choice) - 1]
                    if generator.load_project_data(selected_project["filename"]):
                        try:
                            total_chapters = int(input(f"请输入总章节数 (当前{generator.novel_data['current_progress']['total_chapters']}章, 默认保持不变): ") or generator.novel_data['current_progress']['total_chapters'])
                        except ValueError:
                            total_chapters = generator.novel_data['current_progress']['total_chapters']
                        
                        success = generator.resume_generation(total_chapters)
                    else:
                        success = start_new_project(generator, creative_seed)
                else:
                    success = start_new_project(generator, creative_seed)
            else:
                success = start_new_project(generator, creative_seed)
        else:
            success = start_new_project(generator, creative_seed)
        
        if success:
            generator.print_generation_summary()

            # 添加基础内容质量报告
            generator.print_foundation_quality_report()
            
            # 询问是否查看内容
            view_content = input("\n是否查看生成的小说内容？(y/n): ").lower() == 'y'
            if view_content and generator.novel_data["generated_chapters"]:
                # 显示第一章和第二章的衔接情况
                if 1 in generator.novel_data["generated_chapters"] and 2 in generator.novel_data["generated_chapters"]:
                    chap1 = generator.novel_data["generated_chapters"][1]
                    chap2 = generator.novel_data["generated_chapters"][2]
                    
                    print(f"\n第一章结尾预览:")
                    chap1_content = chap1['content']
                    if len(chap1_content) > 300:
                        print(chap1_content[-300:])
                    else:
                        print(chap1_content)
                    
                    print(f"\n第二章开头预览:")
                    chap2_content = chap2['content']
                    if len(chap2_content) > 300:
                        print(chap2_content[:300])
                    else:
                        print(chap2_content)
                    
                    connection = chap2.get("connection_to_previous", "")
                    if connection:
                        print(f"\n衔接说明: {connection}")
        else:
            print("❌❌ 小说生成过程中出现错误")
            
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在保存进度...")
        generator.project_manager.save_project_progress(generator.novel_data)
        print("进度已保存，可以安全退出。")
        return


def start_new_project(generator, creative_seed):
    """开始新项目"""
    try:
        total_chapters = int(input(f"请输入总章节数 (默认{CONFIG['defaults']['total_chapters']}): ") or CONFIG['defaults']['total_chapters'])
    except ValueError:
        total_chapters = CONFIG['defaults']['total_chapters']
        print(f"使用默认章节数: {total_chapters}")
    
    # 大规模生成警告
    if total_chapters > 100:
        print(f"\n⚠️  警告: 即将生成{total_chapters}章小说，这可能需要很长时间")
        print("建议: 可以先生成较少章节测试效果")
        confirm = input("确定要继续吗？(y/n): ").lower()
        if confirm != 'y':
            print("已取消生成")
            return False
    
    print(f"\n开始创建新项目并生成{total_chapters}章小说...")
    print("优化版本特点:")
    print("✓ 智能API调用优化，减少等待时间")
    print("✓ 快速质量评估，智能跳过优化")
    print("✓ 缓存机制，避免重复计算")
    print("✓ AI痕迹检测和消除")
    print("首先将基于番茄小说流量趋势为您提供三套方案")
    print("请选择您喜欢的方案后，系统将自动开始创作")
    
    return generator.full_auto_generation(creative_seed, total_chapters)


if __name__ == "__main__":
    main()