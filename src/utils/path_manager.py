"""
路径管理器 - 统一管理小说项目的所有文件路径操作
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from src.config.path_config import path_config
from src.utils.logger import get_logger


class PathManager:
    """路径管理器 - 统一管理小说项目的所有文件路径操作"""
    
    def __init__(self):
        self.logger = get_logger("PathManager")
        self.path_config = path_config
    
    def initialize_project_structure(self, novel_title: str) -> Dict[str, str]:
        """初始化项目目录结构"""
        try:
            paths = self.path_config.ensure_directories(novel_title)
            self.logger.info(f"✅ 项目目录结构初始化完成: {novel_title}")
            return paths
        except Exception as e:
            self.logger.error(f"❌ 初始化项目目录结构失败: {e}")
            return {}
    
    def save_project_info(self, novel_title: str, project_data: Dict, username: str = None) -> bool:
        """
        保存项目信息文件
        
        Args:
            novel_title: 小说标题
            project_data: 项目数据
            username: 用户名（可选），用于用户隔离路径
        """
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(paths["project_info"]), exist_ok=True)
            
            with open(paths["project_info"], 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 项目信息已保存: {paths['project_info']}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存项目信息失败: {e}")
            return False
    
    def load_project_info(self, novel_title: str, username: str = None) -> Optional[Dict]:
        """
        加载项目信息文件 - 支持多种路径格式
        
        Args:
            novel_title: 小说标题
            username: 用户名（可选），用于用户隔离路径
        """
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            
            # 🔥 修复：尝试多个可能的路径（新的标准路径优先）
            possible_paths = [
                paths["project_info"],  # 小说项目/小说名/项目信息.json (新标准)
                paths.get("project_info_legacy", ""),  # 小说项目/小说名/小说名_项目信息.json (旧版本)
                paths["legacy_project_info"],  # 小说项目/小说名_项目信息.json (旧路径)
            ]
            
            project_data = None
            loaded_path = None
            
            for path in possible_paths:
                if path and os.path.exists(path):
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)
                        loaded_path = path
                        break
                    except Exception as e:
                        self.logger.info(f"⚠️ 尝试加载 {path} 失败: {e}")
                        continue
            
            if project_data:
                self.logger.info(f"✅ 项目信息已加载: {loaded_path}")
                return project_data
            else:
                self.logger.info(f"⚠️ 项目信息文件不存在，已尝试路径: {possible_paths}")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ 加载项目信息失败: {e}")
            return None
    
    def save_chapter(self, novel_title: str, chapter_number: int, chapter_data: Dict, username: str = None) -> bool:
        """保存章节文件"""
        try:
            chapter_path = self.path_config.get_chapter_file_path(novel_title, chapter_number, chapter_data.get("chapter_title", ""), username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(chapter_path), exist_ok=True)
            
            with open(chapter_path, 'w', encoding='utf-8') as f:
                json.dump(chapter_data, f, ensure_ascii=False, indent=2)
            
            # 转换为绝对路径以便显示
            abs_path = os.path.abspath(chapter_path)
            self.logger.info(f"✅ 章节已保存: 第{chapter_number}章 -> {abs_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存章节失败: 第{chapter_number}章 - {e}")
            return False
    
    def load_chapter(self, novel_title: str, chapter_number: int, username: str = None) -> Optional[Dict]:
        """加载章节文件"""
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            chapters_dir = Path(paths["chapters_dir"])
            
            # 查找章节文件
            chapter_file = None
            for file_path in chapters_dir.glob(f"第{chapter_number:03d}章_*.json"):
                chapter_file = file_path
                break
            
            if not chapter_file:
                self.logger.info(f"⚠️ 章节文件不存在: 第{chapter_number}章")
                return None
            
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
            
            self.logger.info(f"✅ 章节已加载: 第{chapter_number}章 <- {chapter_file}")
            return chapter_data
        except Exception as e:
            self.logger.error(f"❌ 加载章节失败: 第{chapter_number}章 - {e}")
            return None
    
    def get_all_chapters(self, novel_title: str, username: str = None) -> Dict[int, Dict]:
        """获取所有章节"""
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            chapters_dir = Path(paths["chapters_dir"])
            
            if not chapters_dir.exists():
                return {}
            
            chapters = {}
            for chapter_file in chapters_dir.glob("第*章_*.json"):
                try:
                    # 解析章节号
                    match = chapter_file.stem.split('_')[0]  # 提取 "第XXX章" 部分
                    if match.startswith("第") and match.endswith("章"):
                        chapter_num = int(match[1:-1])
                        
                        with open(chapter_file, 'r', encoding='utf-8') as f:
                            chapter_data = json.load(f)
                            chapters[chapter_num] = chapter_data
                except Exception as e:
                    self.logger.info(f"⚠️ 加载章节文件失败: {chapter_file} - {e}")
                    continue
            
            self.logger.info(f"✅ 已加载 {len(chapters)} 个章节")
            return chapters
        except Exception as e:
            self.logger.error(f"❌ 获取所有章节失败: {e}")
            return {}
    
    def save_stage_plan(self, novel_title: str, stage_name: str, stage_data: Dict, username: str = None) -> bool:
        """保存阶段计划"""
        try:
            stage_path = self.path_config.get_stage_plan_path(novel_title, stage_name, username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(stage_path), exist_ok=True)
            
            with open(stage_path, 'w', encoding='utf-8') as f:
                json.dump(stage_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 阶段计划已保存: {stage_name} -> {stage_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存阶段计划失败: {stage_name} - {e}")
            return False
    
    def load_stage_plan(self, novel_title: str, stage_name: str, username: str = None) -> Optional[Dict]:
        """加载阶段计划"""
        try:
            stage_path = self.path_config.get_stage_plan_path(novel_title, stage_name, username=username)
            
            if not os.path.exists(stage_path):
                self.logger.info(f"⚠️ 阶段计划文件不存在: {stage_name}")
                return None
            
            with open(stage_path, 'r', encoding='utf-8') as f:
                stage_data = json.load(f)
            
            self.logger.info(f"✅ 阶段计划已加载: {stage_name} <- {stage_path}")
            return stage_data
        except Exception as e:
            self.logger.error(f"❌ 加载阶段计划失败: {stage_name} - {e}")
            return None
    
    def save_writing_style_guide(self, novel_title: str, style_data: Dict, username: str = None) -> bool:
        """
        保存写作风格指南
        
        Args:
            novel_title: 小说标题
            style_data: 写作风格数据
            username: 可选，指定用户名。如果不提供，将使用当前登录用户
        """
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            file_path = paths["writing_style_guide"]
            
            # 🔥 关键修复：确保目录存在
            dir_path = os.path.dirname(file_path)
            os.makedirs(dir_path, exist_ok=True)
            
            # 🔥 添加详细调试日志
            self.logger.info(f"📝 正在保存写作风格指南到: {file_path}")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(style_data, f, ensure_ascii=False, indent=2)
            
            # 验证文件是否真的写入
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                self.logger.info(f"✅ 写作风格指南已保存: {file_path} ({file_size} bytes)")
                return True
            else:
                self.logger.error(f"❌ 文件写入后未找到: {file_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ 保存写作风格指南失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def load_writing_style_guide(self, novel_title: str, username: str = None) -> Optional[Dict]:
        """加载写作风格指南"""
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            file_path = paths["writing_style_guide"]
            
            self.logger.info(f"🔍 尝试加载写作风格指南: {file_path}")
            
            if not os.path.exists(file_path):
                self.logger.info(f"⚠️ 写作风格指南文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                style_data = json.load(f)
            
            self.logger.info(f"✅ 写作风格指南已加载: {file_path}")
            return style_data
        except Exception as e:
            self.logger.error(f"❌ 加载写作风格指南失败: {e}")
            return None
    
    def save_novel_overview(self, novel_title: str, overview_data: Dict, username: str = None) -> bool:
        """保存小说总览"""
        try:
            paths = self.path_config.get_project_paths(novel_title, username=username)
            
            with open(paths["novel_overview"], 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 小说总览已保存: {paths['novel_overview']}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存小说总览失败: {e}")
            return False
    
    def create_backup(self, novel_title: str, file_type: str, data: Dict) -> Optional[str]:
        """创建备份文件"""
        try:
            backup_path = self.path_config.get_backup_path(novel_title, file_type)
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 备份已创建: {file_type} -> {backup_path}")
            return backup_path
        except Exception as e:
            self.logger.error(f"❌ 创建备份失败: {file_type} - {e}")
            return None
    
    def save_quality_data(self, novel_title: str, data_type: str, data: Dict, username: str = None) -> bool:
        """保存质量数据"""
        try:
            quality_path = self.path_config.get_quality_data_path(novel_title, data_type, username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(quality_path), exist_ok=True)
            
            with open(quality_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 质量数据已保存: {data_type} -> {quality_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存质量数据失败: {data_type} - {e}")
            return False
    
    def load_quality_data(self, novel_title: str, data_type: str, username: str = None) -> Optional[Dict]:
        """加载质量数据"""
        try:
            quality_path = self.path_config.get_quality_data_path(novel_title, data_type, username=username)
            
            if not os.path.exists(quality_path):
                self.logger.info(f"⚠️ 质量数据文件不存在: {data_type}")
                return None
            
            with open(quality_path, 'r', encoding='utf-8') as f:
                quality_data = json.load(f)
            
            self.logger.info(f"✅ 质量数据已加载: {data_type} <- {quality_path}")
            return quality_data
        except Exception as e:
            self.logger.error(f"❌ 加载质量数据失败: {data_type} - {e}")
            return None
    
    def save_mindset_data(self, novel_title: str, character_name: str, mindset_data: Dict) -> bool:
        """保存角色心境数据"""
        try:
            mindset_path = self.path_config.get_mindset_path(novel_title, character_name)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(mindset_path), exist_ok=True)
            
            with open(mindset_path, 'w', encoding='utf-8') as f:
                json.dump(mindset_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 角色心境数据已保存: {character_name} -> {mindset_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存角色心境数据失败: {character_name} - {e}")
            return False
    
    def load_mindset_data(self, novel_title: str, character_name: str) -> Optional[Dict]:
        """加载角色心境数据"""
        try:
            mindset_path = self.path_config.get_mindset_path(novel_title, character_name)
            
            if not os.path.exists(mindset_path):
                self.logger.info(f"⚠️ 角色心境数据文件不存在: {character_name}")
                return None
            
            with open(mindset_path, 'r', encoding='utf-8') as f:
                mindset_data = json.load(f)
            
            self.logger.info(f"✅ 角色心境数据已加载: {character_name} <- {mindset_path}")
            return mindset_data
        except Exception as e:
            self.logger.error(f"❌ 加载角色心境数据失败: {character_name} - {e}")
            return None
    
    def save_material_data(self, novel_title: str, material_type: str, data: Dict, timestamp: str = "", username: str = None) -> bool:
        """保存材料数据"""
        try:
            material_path = self.path_config.get_material_path(novel_title, material_type, timestamp, username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(material_path), exist_ok=True)
            
            with open(material_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 材料数据已保存: {material_type} -> {material_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存材料数据失败: {material_type} - {e}")
            return False
    
    def load_material_data(self, novel_title: str, material_type: str, timestamp: str = "", username: str = None) -> Optional[Dict]:
        """加载材料数据"""
        try:
            material_path = self.path_config.get_material_path(novel_title, material_type, timestamp, username=username)
            
            if not os.path.exists(material_path):
                self.logger.info(f"⚠️ 材料数据文件不存在: {material_type}")
                return None
            
            with open(material_path, 'r', encoding='utf-8') as f:
                material_data = json.load(f)
            
            self.logger.info(f"✅ 材料数据已加载: {material_type} <- {material_path}")
            return material_data
        except Exception as e:
            self.logger.error(f"❌ 加载材料数据失败: {material_type} - {e}")
            return None
    
    def save_world_state(self, novel_title: str, world_state_data: Dict, username: str = None) -> bool:
        """保存世界状态数据"""
        return self.save_quality_data(novel_title, "world_state", world_state_data, username=username)
    
    def load_world_state(self, novel_title: str, username: str = None) -> Optional[Dict]:
        """加载世界状态数据"""
        return self.load_quality_data(novel_title, "world_state", username=username)
    
    def save_events_data(self, novel_title: str, events_data: List[Dict], username: str = None) -> bool:
        """保存事件数据"""
        try:
            events_path = self.path_config.get_quality_data_path(novel_title, "events", username=username)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(events_path), exist_ok=True)
            
            with open(events_path, 'w', encoding='utf-8') as f:
                json.dump(events_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 事件数据已保存: {len(events_data)}个事件 -> {events_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存事件数据失败: {e}")
            return False
    
    def load_events_data(self, novel_title: str, username: str = None) -> Optional[List[Dict]]:
        """加载事件数据"""
        try:
            events_path = self.path_config.get_quality_data_path(novel_title, "events", username=username)
            
            if not os.path.exists(events_path):
                self.logger.info(f"⚠️ 事件数据文件不存在")
                return []
            
            with open(events_path, 'r', encoding='utf-8') as f:
                events_data = json.load(f)
            
            self.logger.info(f"✅ 事件数据已加载: {len(events_data)}个事件 <- {events_path}")
            return events_data
        except Exception as e:
            self.logger.error(f"❌ 加载事件数据失败: {e}")
            return []
    
    def save_relationships_data(self, novel_title: str, relationships_data: Dict, username: str = None) -> bool:
        """保存关系数据"""
        return self.save_quality_data(novel_title, "relationships", relationships_data, username=username)
    
    def load_relationships_data(self, novel_title: str, username: str = None) -> Optional[Dict]:
        """加载关系数据"""
        return self.load_quality_data(novel_title, "relationships", username=username)
    
    def check_legacy_files(self, novel_title: str) -> Dict[str, bool]:
        """检查旧版本文件"""
        return self.path_config.check_legacy_files(novel_title)
    
    def get_all_project_files(self, novel_title: str) -> Dict[str, List[str]]:
        """获取项目所有文件"""
        return self.path_config.get_all_project_files(novel_title)
    
    def migrate_legacy_files(self, novel_title: str) -> Dict[str, bool]:
        """迁移旧版本文件到新结构"""
        try:
            migration_results = {}
            legacy_files = self.check_legacy_files(novel_title)
            paths = self.path_config.get_project_paths(novel_title)
            
            # 迁移项目信息文件
            if legacy_files.get("项目信息文件", False):
                old_path = paths["legacy_project_info"]
                new_path = paths["project_info"]
                if os.path.exists(old_path) and not os.path.exists(new_path):
                    import shutil
                    shutil.move(old_path, new_path)
                    migration_results["project_info"] = True
                    self.logger.info(f"✅ 迁移项目信息文件: {old_path} -> {new_path}")
                else:
                    migration_results["project_info"] = True
            
            # 迁移章节目录
            if legacy_files.get("章节目录", False):
                old_chapters_dir = paths["legacy_chapters_dir"]
                new_chapters_dir = paths["chapters_dir"]
                if os.path.exists(old_chapters_dir) and not os.path.exists(new_chapters_dir):
                    import shutil
                    shutil.move(old_chapters_dir, new_chapters_dir)
                    migration_results["chapters"] = True
                    self.logger.info(f"✅ 迁移章节目录: {old_chapters_dir} -> {new_chapters_dir}")
                else:
                    migration_results["chapters"] = True
            
            # 迁移其他文件
            file_mappings = [
                ("章节总览文件", "legacy_novel_overview", "novel_overview"),
                ("元素引入计划文件", "legacy_element_introduction", "element_introduction"),
                ("写作风格指南文件", "legacy_writing_style", "writing_style_guide")
            ]
            
            for file_desc, legacy_key, new_key in file_mappings:
                if legacy_files.get(file_desc, False):
                    old_path = paths[legacy_key]
                    new_path = paths[new_key]
                    if os.path.exists(old_path) and not os.path.exists(new_path):
                        import shutil
                        shutil.move(old_path, new_path)
                        migration_results[new_key] = True
                        self.logger.info(f"✅ 迁移{file_desc}: {old_path} -> {new_path}")
                    else:
                        migration_results[new_key] = True
            
            self.logger.info(f"✅ 旧版本文件迁移完成: {novel_title}")
            return migration_results
            
        except Exception as e:
            self.logger.error(f"❌ 迁移旧版本文件失败: {novel_title} - {e}")
            return {}
    
    def migrate_project(self, novel_title: str) -> bool:
        """迁移项目到新的目录结构"""
        try:
            migration_results = self.path_config.migrate_existing_files(novel_title)
            
            # 检查迁移结果
            failed_migrations = [k for k, v in migration_results.items() if not v]
            
            if failed_migrations:
                self.logger.info(f"⚠️ 部分文件迁移失败: {failed_migrations}")
                return False
            
            self.logger.info(f"✅ 项目迁移完成: {novel_title}")
            
            # 显示路径摘要
            summary = self.path_config.get_path_summary(novel_title)
            self.logger.info(f"📋 新的路径配置:\n{summary}")
            
            return True
        except Exception as e:
            self.logger.error(f"❌ 项目迁移失败: {e}")
            return False
    
    def get_project_statistics(self, novel_title: str) -> Dict:
        """获取项目统计信息"""
        try:
            paths = self.path_config.get_project_paths(novel_title)
            
            stats = {
                "project_exists": os.path.exists(paths["project_root"]),
                "total_files": 0,
                "total_size": 0,
                "file_counts": {
                    "chapters": 0,
                    "plans": 0,
                    "materials": 0,
                    "backups": 0
                }
            }
            
            if not stats["project_exists"]:
                return stats
            
            # 统计文件数量和大小
            for root_dir, dir_names, filenames in os.walk(paths["project_root"]):
                for filename in filenames:
                    if filename.endswith('.json'):
                        file_path = os.path.join(root_dir, filename)
                        stats["total_files"] += 1
                        stats["total_size"] += os.path.getsize(file_path)
                        
                        # 分类统计
                        if "chapters" in file_path:
                            stats["file_counts"]["chapters"] += 1
                        elif "planning" in file_path:
                            stats["file_counts"]["plans"] += 1
                        elif "materials" in file_path:
                            stats["file_counts"]["materials"] += 1
                        elif "backup" in file_path:
                            stats["file_counts"]["backups"] += 1
            
            return stats
        except Exception as e:
            self.logger.error(f"❌ 获取项目统计失败: {e}")
            return {"error": str(e)}


# 全局路径管理器实例
path_manager = PathManager()