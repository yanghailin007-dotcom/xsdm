"""主程序入口"""
import sys
import os
import io
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

import shutil
import json
import time
from datetime import datetime

# 修复编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config.config import CONFIG
from src.utils.logger import get_logger
from src.utils.seed_utils import ensure_seed_dict
from src.core.NovelGenerator import NovelGenerator

class SimpleCreativeManager:
    """简化版创意管理器"""
    
    def __init__(self, creative_file="novel_ideas.txt"):
        self.logger = get_logger("SimpleCreativeManager")
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
            self.logger.info(f"✅ 加载了 {len(self.creative_data)} 个创意")
        except Exception as e:
            self.logger.info(f"❌ 加载创意文件失败: {e}")
            self.creative_data = []
    
    def get_current_creative(self):
        """获取当前创意字典对象"""
        if not self.creative_data:
            return None
        
        creative = self.creative_data[self.current_index]
        
        # 返回完整的创意字典，而不是组合字符串
        return creative

    def mark_completed_and_move(self):
        """标记当前创意完成并移动到下一个"""
        if not self.creative_data:
            return False
        
        # 检查是否处于测试模式（从配置读取，不再使用环境变量）
        try:
            from config.config import CONFIG
            use_mock_api = CONFIG.get('test_mode', {}).get('use_mock_api', False)
        except ImportError:
            use_mock_api = False
            
        if use_mock_api:
            # 测试模式：只移动指针，不删除数据
            self.current_index = (self.current_index + 1) % len(self.creative_data)
            self.logger.info(f"🧪 [测试模式] 创意已标记完成但保留在文件中")
            return True
        
        try:
            # 非测试模式：真正删除创意
            completed_creative = self.creative_data.pop(self.current_index)
            
            # 如果列表空了，重置索引
            if self.current_index >= len(self.creative_data) and self.creative_data:
                self.current_index = 0
            
            # 保存更新后的数据
            with open(self.creative_file, 'w', encoding='utf-8') as f:
                json.dump({"creativeWorks": self.creative_data}, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 已完成并移除创意: {completed_creative.get('coreSetting', '')[:30]}...")
            self.logger.info(f"   剩余创意: {len(self.creative_data)} 个")
            return True
            
        except Exception as e:
            self.logger.info(f"❌ 移除创意失败: {e}")
            return False
    
    def has_more_creatives(self):
        """检查是否还有更多创意"""
        return len(self.creative_data) > 0
    
    def get_progress(self):
        """获取进度信息"""
        total = len(self.creative_data) + self.current_index
        # 修复：这里的逻辑应该是已处理+当前数 
        processed = self.current_index
        remaining = len(self.creative_data)
        return f"[{processed + 1}/{processed + remaining}]" if remaining > 0 else "[完成]"

def main():
    """主函数"""
    # 修复：添加logger初始化
    logger = get_logger("automain")
    
    generator = NovelGenerator(CONFIG)
    
    # 构建创意文件路径
    creative_file_path = str(BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt")
    creative_manager = SimpleCreativeManager(creative_file_path)
    
    # 检查API密钥
    if not any(CONFIG["api_keys"].values()):
        logger.info("❌❌❌❌ 请先设置API密钥")
        return
    
    logger.info("🤖🤖🤖🤖 番茄小说智能生成器（全自动连续创作版）")
    logger.info("="*50)
    logger.info("模式: 全自动连续创作，直到创意用完")
    logger.info("流程: 自动读取创意 → 自动生成 → 自动备份 → 自动移除 → 继续下一个")
    logger.info("="*50)
    
    try:
        # 检查创意文件
        if not creative_manager.creative_data:
            logger.info("❌ 创意文件为空，请先添加创意")
            return
        
        # 连续创作循环
        while creative_manager.has_more_creatives():
            # 获取当前创意
            creative_seed = creative_manager.get_current_creative()
            # 防御性归一化：确保creative_seed为dict
            if creative_seed is not None:
                creative_seed = ensure_seed_dict(creative_seed)
            progress = creative_manager.get_progress()
            if creative_seed:
                core_setting = creative_seed.get('coreSetting', '未知创意')[:50]  # 只显示前50个字符
                logger.info(f"\n🎯 开始处理创意 {progress}: {core_setting}...")
            else:
                logger.info(f"\n🎯 开始处理创意 {progress}: 无创意数据")
            
            # 从创意字典中提取核心设定作为搜索关键词
            if creative_seed and isinstance(creative_seed, dict):
                search_keyword = creative_seed.get('coreSetting', '')[:50]  # 使用核心设定作为搜索关键词
            else:
                search_keyword = str(creative_seed)[:50] if creative_seed else ""

            existing_projects = generator.project_manager.find_existing_projects(search_keyword)
            
            if existing_projects:
                logger.info(f"📚 找到{len(existing_projects)}个相关项目，自动选择最新项目继续")
                # 继续最新项目
                selected_project = existing_projects[0]
                if generator.load_project_data(selected_project["filename"]):
                    # 自动进行完整性检查
                    integrity_report = generator.project_manager.validate_chapter_integrity(generator.novel_data)
                    logger.info(f"📊 章节完整性报告: 完成度 {integrity_report['completion_rate']}%")
                    
                    if integrity_report['missing_chapters']:
                        logger.info(f"❗ 缺失章节: {integrity_report['missing_chapters']}")
                    
                    # 全自动模式使用默认章节数
                    total_chapters = generator.novel_data['current_progress']['total_chapters']
                    logger.info(f"📖 自动继续生成，总章节数: {total_chapters}")
                    
                    success = generator.resume_generation(total_chapters)
                else:
                    logger.info("加载项目失败，自动创建新项目")
                    success = start_new_project(generator, creative_seed, logger)
            else:
                logger.info("未找到相关项目，自动创建新项目")
                success = start_new_project(generator, creative_seed, logger)
            
            if success:
                generator.print_generation_summary()
                generator.print_foundation_quality_report()
                
                # 自动备份项目
                auto_backup_project(generator.novel_data["novel_title"], logger)
                
                logger.info(f"🎉 创意 {progress} 完成！")
                
                # 标记完成并移动到下一个创意
                creative_manager.mark_completed_and_move()
                
                # 如果不是最后一个创意，等待一下再继续
                if creative_manager.has_more_creatives():
                    logger.info("\n⏳ 准备处理下一个创意，3秒后继续...")
                    time.sleep(3)
            else:
                logger.info(f"❌ 创意 {progress} 生成失败，跳过此创意")
                # 即使失败也移动到下一个创意
                creative_manager.mark_completed_and_move()
        
        logger.info("\n🎊🎊🎊 所有创意已完成！ 🎊🎊🎊")
        logger.info("全自动连续创作流程结束")
            
    except KeyboardInterrupt:
        logger.info("\n\n收到中断信号，正在保存进度...")
        generator.project_manager.save_project_progress(generator.novel_data)
        logger.info("进度已保存，可以安全退出。")
        return


def start_new_project(generator, creative_seed, logger):
    """开始新项目 - 全自动版本"""
    # 全自动模式使用默认章节数
    total_chapters = CONFIG['defaults']['total_chapters']
    logger.info(f"📖 自动设置总章节数: {total_chapters}")
    
    logger.info(f"开始创建新项目并生成{total_chapters}章小说...")
    logger.info("🎯 全自动模式运行中...")
    logger.info("✓ 自动创意选择")
    logger.info("✓ 自动章节规划") 
    logger.info("✓ 自动质量评估")
    logger.info("✓ 自动备份管理")
    
    return generator.full_auto_generation(creative_seed, total_chapters)


def auto_backup_project(novel_title, logger):
    """自动备份项目"""
    import re
    
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
    source_dir = "小说项目"
    target_base = r"C:\work1.0\Chrome\小说项目"
    
    # 检查源目录是否存在
    if not os.path.exists(source_dir):
        logger.info(f"❌ 源目录不存在: {source_dir}")
        return False
    
    # 创建目标目录
    try:
        os.makedirs(target_base, exist_ok=True)
    except Exception as e:
        logger.info(f"❌ 创建目标目录失败: {e}")
        return False
    
    # 查找与当前小说相关的所有文件
    project_files = []
    for filename in os.listdir(source_dir):
        if safe_title in filename:
            project_files.append(filename)
    
    if not project_files:
        logger.info(f"❌ 未找到与小说 '{novel_title}' 相关的项目文件")
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
            logger.info(f"❌ 复制文件失败 {filename}: {e}")
    
    # 记录复制操作
    try:
        log_file = os.path.join(target_base, "复制记录.txt")
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 自动复制: {novel_title} ({copied_count}个文件)\n")
    except Exception:
        pass
    
    logger.info(f"✅ 自动备份完成: {copied_count}个文件")
    return True


if __name__ == "__main__":
    main()