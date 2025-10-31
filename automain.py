"""主程序入口"""
import NovelGenerator
from config import CONFIG
import shutil
import os
import json
import time

# 首先导入 utils 来启用全局时间戳
import utils
# 现在所有 print 都会自动带时间戳

class SimpleCreativeManager:
    """简化版创意管理器"""
    
    def __init__(self, creative_file="novel_ideas.txt"):
        self.creative_file = creative_file
        self.creative_data = []
        self.current_index = 0
        self.load_creatives()
    
    def load_creatives(self):
        """加载创意数据"""
        try:
            with open(self.creative_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.creative_data = data.get("creativeWorks", [])
            print(f"✅ 加载了 {len(self.creative_data)} 个创意")
        except Exception as e:
            print(f"❌ 加载创意文件失败: {e}")
            self.creative_data = []
    
    def get_current_creative(self):
        """获取当前创意并组合成一句话"""
        if not self.creative_data:
            return None
        
        creative = self.creative_data[self.current_index]
        
        # 组合成一句话创意
        core_setting = creative.get('coreSetting', '')
        core_selling = creative.get('coreSellingPoints', '')
        story_opening = creative.get('completeStoryline', {}).get('opening', '')
        
        # 提取核心设定中的关键词
        keywords = core_setting.split('+')[0] if '+' in core_setting else core_setting
        combined_creative = f"{keywords}，{core_selling}，{story_opening}"
        
        return combined_creative
    
    def mark_completed_and_move(self):
        """标记当前创意完成并移动到下一个"""
        if not self.creative_data:
            return False
        
        try:
            # 移除当前创意
            completed_creative = self.creative_data.pop(self.current_index)
            
            # 如果列表空了，重置索引
            if self.current_index >= len(self.creative_data) and self.creative_data:
                self.current_index = 0
            
            # 保存更新后的数据
            with open(self.creative_file, 'w', encoding='utf-8') as f:
                json.dump({"creativeWorks": self.creative_data}, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已完成并移除创意: {completed_creative.get('coreSetting', '')[:30]}...")
            print(f"   剩余创意: {len(self.creative_data)} 个")
            return True
            
        except Exception as e:
            print(f"❌ 移除创意失败: {e}")
            return False
    
    def has_more_creatives(self):
        """检查是否还有更多创意"""
        return len(self.creative_data) > 0
    
    def get_progress(self):
        """获取进度信息"""
        return f"[{self.current_index + 1}/{len(self.creative_data) + self.current_index}]"

def main():
    """主函数"""
    generator = NovelGenerator.NovelGenerator(CONFIG)
    creative_manager = SimpleCreativeManager()
    
    # 检查API密钥
    if not any(CONFIG["api_keys"].values()):
        print("❌❌❌❌ 请先设置API密钥")
        return
    
    print("🤖🤖🤖🤖 番茄小说智能生成器（全自动连续创作版）")
    print("="*50)
    print("模式: 全自动连续创作，直到创意用完")
    print("流程: 自动读取创意 → 自动生成 → 自动备份 → 自动移除 → 继续下一个")
    print("="*50)
    
    try:
        # 检查创意文件
        if not creative_manager.creative_data:
            print("❌ 创意文件为空，请先添加创意")
            return
        
        # 连续创作循环
        while creative_manager.has_more_creatives():
            # 获取当前创意
            creative_seed = creative_manager.get_current_creative()
            progress = creative_manager.get_progress()
            print(f"\n🎯 开始处理创意 {progress}: {creative_seed}")
            
            # 查找相关项目
            existing_projects = generator.project_manager.find_existing_projects(creative_seed)
            
            if existing_projects:
                print(f"📚 找到{len(existing_projects)}个相关项目，自动选择最新项目继续")
                # 继续最新项目
                selected_project = existing_projects[0]
                if generator.load_project_data(selected_project["filename"]):
                    # 自动进行完整性检查
                    integrity_report = generator.project_manager.validate_chapter_integrity(generator.novel_data)
                    print(f"📊 章节完整性报告: 完成度 {integrity_report['completion_rate']}%")
                    
                    if integrity_report['missing_chapters']:
                        print(f"❗ 缺失章节: {integrity_report['missing_chapters']}")
                    
                    # 全自动模式使用默认章节数
                    total_chapters = generator.novel_data['current_progress']['total_chapters']
                    print(f"📖 自动继续生成，总章节数: {total_chapters}")
                    
                    success = generator.resume_generation(total_chapters)
                else:
                    print("加载项目失败，自动创建新项目")
                    success = start_new_project(generator, creative_seed)
            else:
                print("未找到相关项目，自动创建新项目")
                success = start_new_project(generator, creative_seed)
            
            if success:
                generator.print_generation_summary()
                generator.print_foundation_quality_report()
                
                # 自动备份项目
                auto_backup_project(generator.novel_data["novel_title"])
                
                print(f"🎉 创意 {progress} 完成！")
                
                # 标记完成并移动到下一个创意
                creative_manager.mark_completed_and_move()
                
                # 如果不是最后一个创意，等待一下再继续
                if creative_manager.has_more_creatives():
                    print("\n⏳ 准备处理下一个创意，3秒后继续...")
                    time.sleep(3)
            else:
                print(f"❌ 创意 {progress} 生成失败，跳过此创意")
                # 即使失败也移动到下一个创意
                creative_manager.mark_completed_and_move()
        
        print("\n🎊🎊🎊 所有创意已完成！ 🎊🎊🎊")
        print("全自动连续创作流程结束")
            
    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在保存进度...")
        generator.project_manager.save_project_progress(generator.novel_data)
        print("进度已保存，可以安全退出。")
        return


def start_new_project(generator, creative_seed):
    """开始新项目 - 全自动版本"""
    # 全自动模式使用默认章节数
    total_chapters = CONFIG['defaults']['total_chapters']
    print(f"📖 自动设置总章节数: {total_chapters}")
    
    print(f"开始创建新项目并生成{total_chapters}章小说...")
    print("🎯 全自动模式运行中...")
    print("✓ 自动创意选择")
    print("✓ 自动章节规划") 
    print("✓ 自动质量评估")
    print("✓ 自动备份管理")
    
    return generator.full_auto_generation(creative_seed, total_chapters)


def auto_backup_project(novel_title):
    """自动备份项目"""
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
                    shutil.rmtree(target_path)
                shutil.copytree(source_path, target_path)
            else:
                # 如果是文件，使用copy2
                shutil.copy2(source_path, target_path)
            
            copied_count += 1
        except Exception as e:
            print(f"❌ 复制文件失败 {filename}: {e}")
    
    # 记录复制操作
    try:
        log_file = os.path.join(target_base, "复制记录.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 自动复制: {novel_title} ({copied_count}个文件)\n")
    except Exception:
        pass
    
    print(f"✅ 自动备份完成: {copied_count}个文件")
    return True


if __name__ == "__main__":
    main()