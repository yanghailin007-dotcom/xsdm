"""主程序入口"""
import NovelGenerator
from config import CONFIG
import shutil
import os

# 首先导入 utils 来启用全局时间戳
import utils
# 现在所有 print 都会自动带时间戳

def main():
    """主函数"""
    generator = NovelGenerator.NovelGenerator(CONFIG)
    # 检查API密钥
    if not any(CONFIG["api_keys"].values()):
        print("❌❌❌❌ 请先设置API密钥")
        return
    
    print("🤖🤖🤖🤖 番茄小说智能生成器（优化版本）")
    print("="*50)
    print("特点: 优化生成速度，智能跳过优化，缓存机制")
    print("功能: 全自动小说生成，质量评估，AI痕迹检测")
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
            print(f"\n📚📚📚📚 找到{len(existing_projects)}个相关项目:")
            for i, project in enumerate(existing_projects, 1):
                print(f"  {i}. {project['title']} ({project['completed_chapters']}/{project['total_chapters']}章) - {project['stage']}")
            
            choice = input("\n请选择: (1)继续现有项目 (2)创建新项目 (3)查看所有项目: ").strip()
            
            if choice == "1" and existing_projects:
                # 继续最新项目
                selected_project = existing_projects[0]
                if generator.load_project_data(selected_project["filename"]):
                    # 🆕🆕🆕 先进行完整性检查
                    integrity_report = generator.project_manager.validate_chapter_integrity(generator.novel_data)
                    print(f"\n📊📊 章节完整性报告:")
                    print(f"  预期章节: 1-{integrity_report['expected_total']} (共{integrity_report['expected_total']}章)")
                    print(f"  实际文件: {integrity_report['actual_files']}章")
                    print(f"  内存数据: {integrity_report['memory_chapters']}章")
                    print(f"  完成度: {integrity_report['completion_rate']}%")
                    
                    if integrity_report['missing_chapters']:
                        print(f"  ❗❗ 缺失章节: {integrity_report['missing_chapters']}")
                    
                    if integrity_report['memory_but_no_file']:
                        print(f"  💾💾 需重新保存: {integrity_report['memory_but_no_file']}")
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
                print(f"\n📚📚📚📚 所有项目 ({len(all_projects)}个):")
                for i, project in enumerate(all_projects, 1):
                    print(f"  {i}. {project['title']} ({project['completed_chapters']}/{project['total_chapters']}章) - {project['stage']}")
                
                project_choice = input("选择要继续的项目编号 (回车创建新项目): ").strip()
                if project_choice.isdigit() and 1 <= int(project_choice) <= len(all_projects):
                    selected_project = all_projects[int(project_choice) - 1]
                    if generator.load_project_data(selected_project["filename"]):
                        # 🆕🆕🆕 先进行完整性检查
                        integrity_report = generator.project_manager.validate_chapter_integrity(generator.novel_data)
                        print(f"\n📊📊 章节完整性报告:")
                        print(f"  预期章节: 1-{integrity_report['expected_total']} (共{integrity_report['expected_total']}章)")
                        print(f"  实际文件: {integrity_report['actual_files']}章")
                        print(f"  内存数据: {integrity_report['memory_chapters']}章")
                        print(f"  完成度: {integrity_report['completion_rate']}%")
                        
                        if integrity_report['missing_chapters']:
                            print(f"  ❗❗ 缺失章节: {integrity_report['missing_chapters']}")
                        
                        if integrity_report['memory_but_no_file']:
                            print(f"  💾💾 需重新保存: {integrity_report['memory_but_no_file']}")
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
            
            # 🆕🆕🆕 新增：复制项目到指定目录
            copy_project_to_target(generator.novel_data["novel_title"])
            
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
            print("❌❌❌❌ 小说生成过程中出现错误")
            
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
        confirm = input("确定要继续吗？(y/n): 默认y").lower()
        if confirm == 'n':
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


def copy_project_to_target(novel_title):
    import re
    from datetime import datetime
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
    source_dir = "小说项目"
    target_base = r"C:\work1.0\Chrome\小说项目"
    
    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        print(f"❌ 源目录不存在: {source_dir}")
        return False
    
    # 创建目标目录
    try:
        os.makedirs(target_base, exist_ok=True)
        print(f"✅ 目标目录已创建/存在: {target_base}")
    except Exception as e:
        print(f"❌ 创建目标目录失败: {e}")
        return False
    
    # 查找与当前小说相关的所有文件
    project_files = []
    for filename in os.listdir(source_dir):
        if safe_title in filename:
            project_files.append(filename)
    
    if not project_files:
        print(f"❌ 未找到与小说 '{novel_title}' 相关的项目文件")
        return False
    
    # 复制文件
    copied_count = 0
    for filename in project_files:
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_base, filename)
        
        try:
            if os.path.isdir(source_path):
                # 如果是目录，使用copytree
                if os.path.exists(target_path):
                    # 如果目标目录已存在，先删除
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
            else:
                # 如果是文件，使用copy2
                shutil.copy2(source_path, target_path)
            
            copied_count += 1
            print(f"✅ 已复制: {filename}")
            
        except Exception as e:
            print(f"❌ 复制文件失败 {filename}: {e}")
    
    # 记录复制操作
    try:
        log_file = os.path.join(target_base, "复制记录.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 复制小说: {novel_title} ({copied_count}个文件)\n")
    except Exception as e:
        print(f"⚠️  写入复制记录失败: {e}")
    
    print(f"🎯 项目复制完成: {copied_count}个文件已复制到 {target_base}")
    return True


if __name__ == "__main__":
    main()