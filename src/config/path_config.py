"""
小说项目路径配置统一管理
统一管理所有生成内容的存储路径，确保目录结构一致性
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List


class NovelPathConfig:
    """小说项目路径配置管理器"""
    
    def __init__(self):
        # 🔥 不再在初始化时固定base_dir，而是动态获取
        self._cached_base_dir = None
        self._cached_username = None
        self.templates_dir = Path("templates")
    
    def _get_base_dir(self, username: str = None) -> Path:
        """
        动态获取基础目录（支持用户隔离）
        
        Args:
            username: 可选，指定用户名。如果不提供，将动态获取当前登录用户
        
        Returns:
            用户隔离的基础目录路径
        """
        # 如果提供了用户名，直接使用
        if username:
            from web.utils.path_utils import get_user_novel_dir
            return get_user_novel_dir(username=username, create=True)
        
        # 尝试动态获取当前用户
        try:
            from web.utils.path_utils import get_user_novel_dir, get_current_username
            current_user = get_current_username()
            # 如果当前用户与缓存的不同，清除缓存
            if current_user != self._cached_username:
                self._cached_username = current_user
                self._cached_base_dir = None
            
            # 使用缓存或重新获取
            if self._cached_base_dir is None:
                self._cached_base_dir = get_user_novel_dir(username=current_user, create=True)
            
            return self._cached_base_dir
        except Exception:
            # 没有Flask上下文时使用默认路径
            return Path("小说项目")
        
    def get_safe_title(self, title: str) -> str:
        """生成安全的文件名 - 保留文件系统支持的字符（包括中文冒号和逗号）"""
        if not title:
            return "未命名小说"
        
        # 只移除文件系统真正不支持的字符：\ / * ? " < > |
        # 注意：保留中文冒号：、中文逗号，等字符
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", str(title))
        
        return safe_title
    
    def get_project_paths(self, novel_title: str, username: str = None) -> Dict[str, str]:
        """
        获取项目的所有路径配置
        
        Args:
            novel_title: 小说标题
            username: 可选，指定用户名。如果不提供，将使用当前登录用户
        
        Returns:
            项目路径字典
        """
        safe_title = self.get_safe_title(novel_title)
        base_dir = self._get_base_dir(username)
        project_dir = base_dir / safe_title
        
        materials_dir = project_dir / "materials"
        market_analysis_dir = materials_dir / "market_analysis"
        
        return {
            # 项目根目录
            "project_root": str(project_dir),
            
            # 核心数据目录
            # 修复：正确的项目信息文件路径应该是 项目目录/项目信息.json 或 项目目录/小说名_项目信息.json
            "project_info": str(project_dir / f"{safe_title}_项目信息.json"),
            # 为了兼容，也支持 project_info.json 作为标准名称
            "project_info_standard": str(project_dir / "project_info.json"),
            "novel_overview": str(project_dir / "novel_overview.json"),
            "writing_style_guide": str(project_dir / f"{safe_title}_writing_style_guide.json"),
            
            # 章节目录
            "chapters_dir": str(project_dir / "chapters"),
            "chapters_backup_dir": str(project_dir / "chapters_backup"),
            
            # 规划目录
            "planning_dir": str(project_dir / "planning"),
            "stage_plans_dir": str(project_dir / "planning" / "stage_plans"),
            "writing_plans_dir": str(project_dir / "planning"),
            "overall_stage_plans": str(project_dir / "planning" / "overall_stage_plans.json"),
            
            # 元素规划（元素登场时机由期待感系统统一管理）
            "element_schedule": str(project_dir / "planning" / "element_schedule.json"),
            "element_introduction": str(project_dir / "planning" / "element_introduction.json"),
            
            # 材料目录（包括角色设计）
            "materials_dir": str(materials_dir),
            "worldview_dir": str(materials_dir / "worldview"),
            "characters_dir": str(project_dir / "characters"),
            "character_design_file": str(project_dir / "characters" / f"{safe_title}_角色设计.json"),
            "market_analysis_dir": str(market_analysis_dir),
            "market_analysis": str(market_analysis_dir / "market_analysis.json"),
            "creative_brief": str(materials_dir / "creative_brief.json"),
            "ai_refined_brief": str(materials_dir / "ai_refined_brief.txt"),
            
            # 生成内容目录
            "generated_content_dir": str(project_dir / "generated_content"),
            "creative_brief_old": str(project_dir / "generated_content" / "creative_brief.txt"),
            
            # 质量和评估
            "quality_reports_dir": str(project_dir / "quality_reports"),
            "quality_assessments": str(project_dir / "quality_reports" / "quality_assessments.json"),
            
            # 角色发展表 - 运行时数据，存储在项目根目录
            "character_development": str(project_dir / "character_development.json"),
            
            # 世界状态管理
            "world_state": str(project_dir / "world_state.json"),
            "events_dir": str(project_dir / "events"),
            "relationships": str(project_dir / "relationships.json"),
            "mindset_dir": str(project_dir / "mindset"),
            
            # 阶段特定目录
            "stage_plan": str(project_dir / "stage_plan"),
            "stage_writing_plans": str(project_dir / "stage_writing_plans"),
            "generation_materials": str(project_dir / "生成材料"),
            "worldview_old": str(project_dir / "worldview"),
            "market_analysis_old": str(project_dir / "market_analysis"),
            
            # 导出和备份
            "exports_dir": str(project_dir / "exports"),
            "backup_dir": str(project_dir / "backup"),
            
            # 日志和临时文件
            "logs_dir": str(project_dir / "logs"),
            "temp_dir": str(project_dir / "temp"),
            
            # 材料索引
            "material_index": str(project_dir / f"{safe_title}_材料索引.json"),
            
            # 兼容性路径（支持旧版本）
            "legacy_chapters_dir": str(base_dir / f"{safe_title}_章节"),
            "legacy_project_info": str(base_dir / f"{safe_title}_项目信息.json"),
            "legacy_novel_overview": str(base_dir / f"{safe_title}_章节总览.json"),
            "legacy_element_introduction": str(base_dir / f"{safe_title}_元素引入计划.json"),
            "legacy_writing_style": str(base_dir / f"{safe_title}_写作风格指南.json")
        }
    
    def ensure_directories(self, novel_title: str, username: str = None) -> Dict[str, str]:
        """
        确保项目目录结构存在并返回路径
        
        Args:
            novel_title: 小说标题
            username: 可选，指定用户名。如果不提供，将使用当前登录用户
        """
        paths = self.get_project_paths(novel_title, username=username)
        
        # 创建所有必要的目录
        directories_to_create = [
            paths["project_root"],
            paths["chapters_dir"],
            paths["chapters_backup_dir"],
            paths["planning_dir"],
            paths["stage_plans_dir"],
            # writing_plans_dir 现在直接指向 planning_dir，无需单独创建
            paths["materials_dir"],
            paths["worldview_dir"],
            paths["characters_dir"],
            paths["market_analysis_dir"],  # 使用定义的 market_analysis_dir
            paths["generated_content_dir"],
            paths["quality_reports_dir"],
            paths["exports_dir"],
            paths["backup_dir"],
            paths["logs_dir"],
            paths["temp_dir"],
            paths["events_dir"],
            paths["mindset_dir"],
            paths["stage_plan"],
            paths["stage_writing_plans"],
            paths["generation_materials"]
        ]
        
        for directory in directories_to_create:
            os.makedirs(directory, exist_ok=True)
        
        return paths
    
    def get_chapter_file_path(self, novel_title: str, chapter_number: int, chapter_title: str = "", username: str = None) -> str:
        """获取章节文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_chapter_title = re.sub(r'[\\/*?:"<>|]', "_", chapter_title) if chapter_title else f"第{chapter_number}章"
        chapters_dir = Path(paths["chapters_dir"])
        return str(chapters_dir / f"第{chapter_number:03d}章_{safe_chapter_title}.json")
    
    def get_backup_path(self, novel_title: str, file_type: str, timestamp: str = "", username: str = None) -> str:
        """获取备份文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        backup_dir = Path(paths["backup_dir"])
        return str(backup_dir / f"{safe_title}_{file_type}_{timestamp}.json")
    
    def get_quality_data_path(self, novel_title: str, data_type: str, username: str = None) -> str:
        """获取质量数据文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        
        if data_type == "character_development":
            return paths["character_development"]
        elif data_type == "character_design":
            return paths["character_design_file"]
        elif data_type == "world_state":
            return paths["world_state"]
        elif data_type == "events":
            return str(Path(paths["events_dir"]) / f"{safe_title}_events.json")
        elif data_type == "relationships":
            return paths["relationships"]
        elif data_type == "quality_assessments":
            return paths["quality_assessments"]
        else:
            return str(Path(paths["quality_reports_dir"]) / f"{safe_title}_{data_type}.json")
    
    def get_mindset_path(self, novel_title: str, character_name: str, username: str = None) -> str:
        """获取角色心境文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        safe_character = "".join(c for c in character_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return str(Path(paths["mindset_dir"]) / f"{safe_title}_mindset_{safe_character}.json")
    
    def get_material_path(self, novel_title: str, material_type: str, timestamp: str = "", username: str = None) -> str:
        """获取材料文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if material_type == "worldview":
            return str(Path(paths["worldview_dir"]) / f"{safe_title}_世界观_{timestamp}.json")
        elif material_type == "characters":
            return paths["character_design_file"]
        elif material_type == "market_analysis":
            return paths["market_analysis"]
        elif material_type == "creative_brief":
            return paths["creative_brief"]
        else:
            return str(Path(paths["materials_dir"]) / f"{safe_title}_{material_type}_{timestamp}.json")
    
    def get_stage_plan_path(self, novel_title: str, stage_name: str, timestamp: str = "", username: str = None) -> str:
        """获取阶段计划文件路径（新版本）"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        safe_stage = "".join(c for c in stage_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return str(Path(paths["stage_plans_dir"]) / f"{safe_title}_{safe_stage}_plan_{timestamp}.json")
    
    def get_writing_plan_path(self, novel_title: str, stage_name: str, timestamp: str = "", username: str = None) -> str:
        """获取写作计划文件路径"""
        paths = self.get_project_paths(novel_title, username=username)
        safe_title = self.get_safe_title(novel_title)
        safe_stage = "".join(c for c in stage_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        if not timestamp:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return str(Path(paths["writing_plans_dir"]) / f"{safe_title}_{safe_stage}_writing_plan_{timestamp}.json")
    
    def check_legacy_files(self, novel_title: str, username: str = None) -> Dict[str, bool]:
        """检查是否存在旧版本文件"""
        paths = self.get_project_paths(novel_title, username=username)
        legacy_files = {}
        
        legacy_checks = [
            ("legacy_project_info", "项目信息文件"),
            ("legacy_chapters_dir", "章节目录"),
            ("legacy_novel_overview", "章节总览文件"),
            ("legacy_element_introduction", "元素引入计划文件"),
            ("legacy_writing_style", "写作风格指南文件")
        ]
        
        for path_key, description in legacy_checks:
            file_path = paths[path_key]
            if path_key.endswith("_dir"):
                legacy_files[description] = os.path.exists(file_path)
            else:
                legacy_files[description] = os.path.exists(file_path)
        
        return legacy_files
    
    def get_all_project_files(self, novel_title: str) -> Dict[str, List[str]]:
        """获取项目的所有文件列表"""
        paths = self.get_project_paths(novel_title)
        all_files = {
            "core_files": [],
            "chapter_files": [],
            "planning_files": [],
            "material_files": [],
            "quality_files": [],
            "backup_files": [],
            "export_files": [],
            "legacy_files": []
        }
        
        try:
            # 核心文件
            for file_key in ["project_info", "novel_overview", "writing_style_guide"]:
                if os.path.exists(paths[file_key]):
                    all_files["core_files"].append(paths[file_key])
            
            # 章节文件
            if os.path.exists(paths["chapters_dir"]):
                all_files["chapter_files"] = [str(f) for f in Path(paths["chapters_dir"]).glob("*.json")]
            
            # 规划文件
            if os.path.exists(paths["planning_dir"]):
                all_files["planning_files"] = [str(f) for f in Path(paths["planning_dir"]).rglob("*.json")]
            
            # 材料文件
            if os.path.exists(paths["materials_dir"]):
                all_files["material_files"] = [str(f) for f in Path(paths["materials_dir"]).rglob("*")]
            
            # 质量文件
            if os.path.exists(paths["quality_reports_dir"]):
                all_files["quality_files"] = [str(f) for f in Path(paths["quality_reports_dir"]).rglob("*.json")]
            
            # 事件文件
            if os.path.exists(paths["events_dir"]):
                all_files["quality_files"].extend([str(f) for f in Path(paths["events_dir"]).glob("*.json")])
            
            # 心境文件
            if os.path.exists(paths["mindset_dir"]):
                all_files["quality_files"].extend([str(f) for f in Path(paths["mindset_dir"]).glob("*.json")])
            
            # 备份文件
            if os.path.exists(paths["backup_dir"]):
                all_files["backup_files"] = [str(f) for f in Path(paths["backup_dir"]).glob("*.json")]
            
            # 导出文件
            if os.path.exists(paths["exports_dir"]):
                all_files["export_files"] = [str(f) for f in Path(paths["exports_dir"]).rglob("*")]
            
            # 旧版本文件
            for file_key in ["legacy_project_info", "legacy_novel_overview",
                           "legacy_element_introduction", "legacy_writing_style"]:
                if os.path.exists(paths[file_key]):
                    all_files["legacy_files"].append(paths[file_key])
            
            if os.path.exists(paths["legacy_chapters_dir"]):
                all_files["legacy_files"].extend([str(f) for f in Path(paths["legacy_chapters_dir"]).glob("*.json")])
            
        except Exception as e:
            print(f"获取项目文件列表时出错: {e}")
        
        return all_files
    
    def migrate_existing_files(self, novel_title: str) -> Dict[str, bool]:
        """迁移现有文件到新的目录结构"""
        safe_title = self.get_safe_title(novel_title)
        old_base = Path("小说项目")
        new_paths = self.ensure_directories(novel_title)
        
        migration_results = {}
        
        # 迁移项目信息文件
        old_project_info = old_base / f"{safe_title}_项目信息.json"
        if old_project_info.exists():
            try:
                import shutil
                shutil.move(str(old_project_info), new_paths["project_info"])
                migration_results["project_info"] = True
                print(f"✅ 迁移项目信息文件: {old_project_info} -> {new_paths['project_info']}")
            except Exception as e:
                migration_results["project_info"] = False
                print(f"❌ 迁移项目信息文件失败: {e}")
        else:
            migration_results["project_info"] = True  # 文件不存在，视为成功
        
        # 迁移章节目录
        old_chapters_dir = old_base / f"{safe_title}_章节"
        if old_chapters_dir.exists():
            try:
                import shutil
                if new_paths["chapters_dir"] != str(old_chapters_dir):
                    shutil.move(str(old_chapters_dir), new_paths["chapters_dir"])
                    migration_results["chapters"] = True
                    print(f"✅ 迁移章节目录: {old_chapters_dir} -> {new_paths['chapters_dir']}")
                else:
                    migration_results["chapters"] = True
            except Exception as e:
                migration_results["chapters"] = False
                print(f"❌ 迁移章节目录失败: {e}")
        else:
            migration_results["chapters"] = True
        
        # 迁移章节总览文件
        old_overview = old_base / f"{safe_title}_章节总览.json"
        if old_overview.exists():
            try:
                import shutil
                shutil.move(str(old_overview), new_paths["novel_overview"])
                migration_results["novel_overview"] = True
                print(f"✅ 迁移章节总览文件: {old_overview} -> {new_paths['novel_overview']}")
            except Exception as e:
                migration_results["novel_overview"] = False
                print(f"❌ 迁移章节总览文件失败: {e}")
        else:
            migration_results["novel_overview"] = True
        
        # 迁移写作风格指南
        old_style_guide = old_base / f"{safe_title}_写作风格指南.json"
        if old_style_guide.exists():
            try:
                import shutil
                shutil.move(str(old_style_guide), new_paths["writing_style_guide"])
                migration_results["writing_style_guide"] = True
                print(f"✅ 迁移写作风格指南: {old_style_guide} -> {new_paths['writing_style_guide']}")
            except Exception as e:
                migration_results["writing_style_guide"] = False
                print(f"❌ 迁移写作风格指南失败: {e}")
        else:
            migration_results["writing_style_guide"] = True
        
        return migration_results
    
    def get_path_summary(self, novel_title: str) -> str:
        """获取路径配置摘要"""
        paths = self.get_project_paths(novel_title)
        safe_title = self.get_safe_title(novel_title)
        
        summary = f"""
# 小说项目路径配置摘要
## 项目: {novel_title} (安全名称: {safe_title})

### 核心路径
- 项目根目录: {paths['project_root']}
- 项目信息: {paths['project_info']}
- 小说总览: {paths['novel_overview']}
- 写作风格指南: {paths['writing_style_guide']}
- 角色设计: {paths['character_design_file']}

### 内容目录
- 章节目录: {paths['chapters_dir']}
- 规划目录: {paths['planning_dir']}
- 材料目录: {paths['materials_dir']}
- 角色目录: {paths['characters_dir']}
- 市场分析: {paths['market_analysis']}

### 规划目录
- 阶段计划: {paths['stage_plans_dir']}
- 写作计划: {paths['writing_plans_dir']}
- 元素调度: {paths['element_schedule']}
- 元素引入: {paths['element_introduction']}

### 质量和管理
- 质量报告: {paths['quality_reports_dir']}
- 角色发展: {paths['character_development']}
- 导出目录: {paths['exports_dir']}
- 备份目录: {paths['backup_dir']}
- 日志目录: {paths['logs_dir']}
"""
        
        return summary


# 全局路径配置实例
path_config = NovelPathConfig()