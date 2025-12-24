"""
成长路线规划管理器
负责管理 global_growth_plan 和 stage_writing_plans 的存储与加载
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger
from src.config.path_config import path_config


class GrowthPlanManager:
    """成长路线规划管理器"""
    
    def __init__(self):
        self.logger = get_logger("GrowthPlanManager")
    
    def get_growth_plan_path(self, novel_title: str) -> str:
        """获取成长路线文件路径"""
        paths = path_config.get_project_paths(novel_title)
        safe_title = path_config.get_safe_title(novel_title)
        
        # 保存到 planning 目录
        growth_plan_path = Path(paths["planning_dir"]) / f"{safe_title}_成长路线.json"
        return str(growth_plan_path)
    
    def get_stage_writing_plans_path(self, novel_title: str) -> str:
        """获取写作计划文件路径"""
        paths = path_config.get_project_paths(novel_title)
        safe_title = path_config.get_safe_title(novel_title)

        # 直接保存到 planning 目录，去掉 writing_plans 子目录
        stage_plans_path = Path(paths["writing_plans_dir"]) / f"{safe_title}_写作计划.json"
        return str(stage_plans_path)
    
    def save_growth_plan(self, novel_title: str, growth_plan: Dict) -> bool:
        """保存成长路线到独立文件"""
        try:
            file_path = self.get_growth_plan_path(novel_title)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(growth_plan, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 成长路线已保存到独立文件: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存成长路线失败: {e}")
            return False
    
    def load_growth_plan(self, novel_title: str) -> Optional[Dict]:
        """从独立文件加载成长路线"""
        try:
            file_path = self.get_growth_plan_path(novel_title)
            
            if not os.path.exists(file_path):
                self.logger.info(f"⚠️ 成长路线文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                growth_plan = json.load(f)
            
            self.logger.info(f"✅ 成长路线已从独立文件加载")
            return growth_plan
        except Exception as e:
            self.logger.error(f"❌ 加载成长路线失败: {e}")
            return None
    
    def save_stage_writing_plans(self, novel_title: str, stage_plans: Dict) -> bool:
        """保存写作计划到独立文件"""
        try:
            file_path = self.get_stage_writing_plans_path(novel_title)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(stage_plans, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ 写作计划已保存到独立文件: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 保存写作计划失败: {e}")
            return False
    
    def load_stage_writing_plans(self, novel_title: str) -> Optional[Dict]:
        """从独立文件加载写作计划"""
        try:
            file_path = self.get_stage_writing_plans_path(novel_title)
            
            if not os.path.exists(file_path):
                self.logger.info(f"⚠️ 写作计划文件不存在: {file_path}")
                return None
            
            with open(file_path, 'r', encoding='utf-8') as f:
                stage_plans = json.load(f)
            
            self.logger.info(f"✅ 写作计划已从独立文件加载")
            return stage_plans
        except Exception as e:
            self.logger.error(f"❌ 加载写作计划失败: {e}")
            return None
    
    def migrate_growth_plan_from_project_info(self, novel_title: str, project_data: Dict) -> bool:
        """
        从项目信息中迁移成长路线和写作计划到独立文件
        
        Args:
            novel_title: 小说标题
            project_data: 项目数据(包含 global_growth_plan 和 stage_writing_plans)
        
        Returns:
            bool: 迁移是否成功
        """
        try:
            migration_success = True
            
            # 迁移 global_growth_plan
            growth_plan = project_data.get("global_growth_plan", {})
            if growth_plan:
                if self.save_growth_plan(novel_title, growth_plan):
                    self.logger.info(f"✅ global_growth_plan 已迁移到独立文件")
                    # 从原数据中移除
                    project_data.pop("global_growth_plan", None)
                else:
                    migration_success = False
            else:
                self.logger.info(f"⚠️ 项目数据中没有 global_growth_plan")
            
            # 迁移 stage_writing_plans
            stage_plans = project_data.get("stage_writing_plans", {})
            if stage_plans:
                if self.save_stage_writing_plans(novel_title, stage_plans):
                    self.logger.info(f"✅ stage_writing_plans 已迁移到独立文件")
                    # 从原数据中移除
                    project_data.pop("stage_writing_plans", None)
                else:
                    migration_success = False
            else:
                self.logger.info(f"⚠️ 项目数据中没有 stage_writing_plans")
            
            return migration_success
        except Exception as e:
            self.logger.error(f"❌ 迁移成长路线数据失败: {e}")
            return False
    
    def get_all_planning_files(self, novel_title: str) -> Dict[str, Optional[str]]:
        """获取所有规划文件的路径"""
        paths = path_config.get_project_paths(novel_title)
        safe_title = path_config.get_safe_title(novel_title)
        
        return {
            "global_growth_plan": self.get_growth_plan_path(novel_title),
            "stage_writing_plans": self.get_stage_writing_plans_path(novel_title),
            "overall_stage_plans": paths.get("overall_stage_plans"),
            "writing_style_guide": paths.get("writing_style_guide"),
        }
    
    def validate_planning_files(self, novel_title: str) -> Dict[str, bool]:
        """验证所有规划文件是否存在"""
        file_paths = self.get_all_planning_files(novel_title)
        
        validation_results = {}
        for file_type, file_path in file_paths.items():
            validation_results[file_type] = os.path.exists(file_path) if file_path else False
        
        return validation_results


# 全局实例
growth_plan_manager = GrowthPlanManager()