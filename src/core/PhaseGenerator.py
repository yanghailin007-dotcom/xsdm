"""
阶段生成器 - 负责第一阶段和第二阶段的生成逻辑
从NovelGenerator中拆分出来，提高代码可维护性
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from src.utils.logger import get_logger


class PhaseGenerator:
    """
    阶段生成器 - 处理第一阶段设定生成和第二阶段章节内容生成
    """
    
    def __init__(self, novel_generator):
        """
        初始化阶段生成器
        
        Args:
            novel_generator: NovelGenerator实例，用于访问其属性和方法
        """
        self.generator = novel_generator
        self.logger = get_logger("PhaseGenerator")
    
    # ==================== 第一阶段生成方法 ====================
    
    def generate_phase_one_preparations(self) -> bool:
        """
        第一阶段准备工作：执行到"第一章生成前"的所有步骤
        不包含实际的章节内容生成
        """
        def update_progress_callback(stage_name: str, progress: int, message: Optional[str] = None, 
                                      step_status: Dict = None, points_consumed: int = None):
            """更新第一阶段进度的回调函数 - 支持详细步骤状态和点数消耗"""
            try:
                # 获取API调用消耗的点数
                if points_consumed is None and hasattr(self.generator, 'get_api_points_consumed'):
                    points_consumed = self.generator.get_api_points_consumed()
                
                # 通过事件总线发布进度更新事件
                if hasattr(self.generator, 'event_bus'):
                    event_data = {
                        'stage': stage_name,
                        'progress': progress,
                        'message': message or f"正在执行: {stage_name}",
                        'points_consumed': points_consumed
                    }
                    if step_status:
                        event_data['step_status'] = step_status
                    self.generator.event_bus.publish('phase_one.progress', event_data)
                
                # 如果在管理器中运行，尝试更新任务状态
                if hasattr(self.generator, '_update_task_status_callback'):
                    task_id = getattr(self.generator, '_current_task_id', None)
                    if task_id and callable(self.generator._update_task_status_callback):
                        # 构建步骤状态字典
                        current_step_status = step_status or {stage_name: 'active'}
                        self.generator._update_task_status_callback(
                            task_id, 'generating', progress, None,
                            current_step=stage_name,
                            step_status=current_step_status,
                            points_consumed=points_consumed
                        )
                
                # 更新内部状态
                if hasattr(self.generator, 'novel_data') and 'current_progress' in self.generator.novel_data:
                    self.generator.novel_data['current_progress']['stage'] = stage_name
                    
            except Exception as callback_error:
                print(f"⚠️ 进度更新回调失败: {callback_error}")
        
        def update_step_status(step_name: str, status: str, progress: int = None):
            """更新特定步骤的状态"""
            try:
                points_consumed = self.generator.get_api_points_consumed() if hasattr(self.generator, 'get_api_points_consumed') else 0
                step_status = {step_name: status}
                
                if hasattr(self.generator, 'event_bus'):
                    self.generator.event_bus.publish('phase_one.step_status', {
                        'step': step_name,
                        'status': status,
                        'progress': progress,
                        'points_consumed': points_consumed
                    })
                
                if hasattr(self.generator, '_update_task_status_callback'):
                    task_id = getattr(self.generator, '_current_task_id', None)
                    if task_id and callable(self.generator._update_task_status_callback):
                        self.generator._update_task_status_callback(
                            task_id, 'generating', progress or 0, None,
                            current_step=step_name,
                            step_status=step_status,
                            points_consumed=points_consumed
                        )
            except Exception as e:
                print(f"⚠️ 步骤状态更新失败: {e}")
        
        def notify_failure(error_msg: str):
            """通知任务失败"""
            try:
                if hasattr(self.generator, '_update_task_status_callback'):
                    task_id = getattr(self.generator, '_current_task_id', None)
                    if task_id and callable(self.generator._update_task_status_callback):
                        self.generator._update_task_status_callback(task_id, 'failed', 0, error_msg)
            except Exception as callback_error:
                print(f"⚠️ 失败通知回调失败: {callback_error}")
        
        try:
            print("开始第一阶段准备工作...")
            
            # 第一阶段：基础规划 (10-30%)
            # 传递步骤状态更新回调给 _generate_foundation_planning
            if not self._generate_foundation_planning(update_step_status=update_step_status):
                error_msg = "基础规划生成失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('planning', 30, "基础规划完成",
                                     step_status={'writing_style': 'completed', 'market_analysis': 'completed'})
            
            # 第二阶段：世界观与角色设计 (30-55%)
            if not self._generate_worldview_and_characters(update_step_status=update_step_status):
                error_msg = "世界观与角色设计失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('character_design', 55, "角色设计完成",
                                     step_status={'worldview': 'completed', 'faction_system': 'completed', 
                                                 'character_design': 'completed'})
            
            # 第三阶段：全书规划 (55-80%)
            if not self._generate_overall_planning(update_step_status=update_step_status):
                error_msg = "全书规划制定失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('story_outline', 80, "全书大纲制定完成",
                                     step_status={'emotional_blueprint': 'completed', 'growth_plan': 'completed',
                                                 'stage_plan': 'completed', 'detailed_stage_plans': 'completed',
                                                 'expectation_mapping': 'completed', 'system_init': 'completed'})
            
            # 第四阶段：保存结果 (80-90%)
            if not self._prepare_content_generation(update_step_status=update_step_status):
                error_msg = "保存设定结果失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('saving', 90, "设定结果保存完成",
                                     step_status={'saving': 'completed'})
            
            # 保存第一阶段结果 (90-95%)
            update_progress_callback('validation', 92, "正在保存第一阶段结果...")
            try:
                save_success = self._save_phase_one_result()
                if not save_success:
                    print("⚠️ 项目信息文件保存失败，但第一阶段核心内容已完成")
            except Exception as save_error:
                print(f"⚠️ 保存第一阶段结果时出现警告: {str(save_error)}")
                print("⚠️ 项目信息文件保存失败，但第一阶段核心内容已完成")
            
            print(f"\n🎉 第一阶段设定生成完成！")
            print("✅ 已完成：基础规划、世界观构建、角色设计、全书规划")
            print("📝 下一步：可以继续第二阶段的章节内容生成")

            # 🔥 新增：自动进行质量评估 (95-100%)
            update_step_status('quality_assessment', 'active', 95)
            update_progress_callback('assessment', 95, "正在进行AI质量评估...",
                                     step_status={'quality_assessment': 'active'})
            print("\n" + "="*60)
            print("📊 正在进行写作计划AI质量评估...")
            print("="*60)
            assessment_result = self._assess_writing_plan_quality()
            if assessment_result:
                self.generator.novel_data["quality_assessment"] = assessment_result
                print(f"✅ 评估完成！得分: {assessment_result.get('overall_score', 0)}/100")
                print(f"   状态: {assessment_result.get('readiness', 'unknown')}")
                issue_count = len(assessment_result.get('issues', []))
                if issue_count > 0:
                    print(f"   发现 {issue_count} 个问题，详见评估报告")
                else:
                    print("   未发现问题")
            else:
                print("⚠️ 评估失败，但不影响后续流程")

            # 完成所有步骤
            update_step_status('quality_assessment', 'completed', 100)
            
            # 构建最终步骤状态 - 所有步骤都完成
            final_step_status = {
                'writing_style': 'completed',
                'market_analysis': 'completed',
                'worldview': 'completed',
                'faction_system': 'completed',
                'character_design': 'completed',
                'emotional_blueprint': 'completed',
                'growth_plan': 'completed',
                'stage_plan': 'completed',
                'detailed_stage_plans': 'completed',
                'expectation_mapping': 'completed',
                'system_init': 'completed',
                'saving': 'completed',
                'quality_assessment': 'completed'
            }
            
            update_progress_callback('completed', 100, "第一阶段设定生成完成",
                                     step_status=final_step_status)
            return True

        except Exception as e:
            error_msg = f"第一阶段准备工作发生异常: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            notify_failure(error_msg)
            return False
    
    def _generate_foundation_planning(self, update_step_status=None) -> bool:
        """生成基础规划
        
        Args:
            update_step_status: 可选的步骤状态更新回调函数，用于实时更新前端进度
        """
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划")
        print("="*60)
        
        # 生成写作风格指南 - 在真正开始生成时才标记为 active
        print("📝 步骤6: 写作风格制定")
        self.generator.novel_data["current_progress"]["stage"] = "写作风格制定"
        if update_step_status:
            update_step_status('writing_style', 'active', 10)
        
        if not self._generate_writing_style_guide():
            print("⚠️ 写作风格指南生成失败，使用默认风格")
        
        # 写作风格完成后标记为 completed
        if update_step_status:
            update_step_status('writing_style', 'completed', 15)
        
        # 市场分析 - 在真正开始时才标记为 active
        print("📊 步骤7: 市场分析")
        self.generator.novel_data["current_progress"]["stage"] = "市场分析"
        if update_step_status:
            update_step_status('market_analysis', 'active', 20)
        
        if not self._generate_market_analysis():
            return False
        
        # 市场分析完成后标记为 completed
        if update_step_status:
            update_step_status('market_analysis', 'completed', 25)
        
        return True
    
    def _generate_worldview_and_characters(self, update_step_status=None) -> bool:
        """生成世界观、势力和角色设计"""
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与势力系统设计")
        print("="*60)
        
        # 世界观构建 - 步骤8
        print("🌍 步骤8: 世界观构建")
        self.generator.novel_data["current_progress"]["stage"] = "世界观构建"
        if update_step_status:
            update_step_status('worldview', 'active', 35)
        
        if not self._generate_worldview():
            return False
        
        if update_step_status:
            update_step_status('worldview', 'completed', 40)
        
        # 【新增】势力/阵营系统构建 - 步骤9
        print("⚔️ 步骤9: 构建势力/阵营系统")
        self.generator.novel_data["current_progress"]["stage"] = "势力系统设计"
        if update_step_status:
            update_step_status('faction_system', 'active', 42)
        
        faction_system = self.generator.content_generator.generate_faction_system(
            novel_title=self.generator.novel_data["novel_title"],
            core_worldview=self.generator.novel_data.get("core_worldview", {}),
            selected_plan=self.generator.novel_data["selected_plan"],
            market_analysis=self.generator.novel_data.get("market_analysis", {})
        )
        
        if faction_system:
            self.generator.novel_data["faction_system"] = faction_system
            print("✅ 势力/阵营系统构建完成")
            # 保存到材料管理器
            self.generator._save_material_to_manager("势力系统", faction_system, novel_title=self.generator.novel_data["novel_title"])
        else:
            print("⚠️ 势力/阵营系统生成失败，将使用默认设定")
            # 创建一个基础的势力系统结构，确保后续流程不会出错
            self.generator.novel_data["faction_system"] = {
                "factions": [],
                "main_conflict": "待定",
                "faction_power_balance": "待定",
                "recommended_starting_faction": "待定"
            }
        
        # 势力系统完成
        if update_step_status:
            update_step_status('faction_system', 'completed', 45)
        
        # 核心角色设计（现在可以基于势力系统） - 步骤10
        print("👤 步骤10: 设计核心角色 (主角/核心盟友/宿敌)")
        self.generator.novel_data["current_progress"]["stage"] = "核心角色设计"
        if update_step_status:
            update_step_status('character_design', 'active', 48)
        
        core_characters = self.generator.content_generator.generate_character_design(
            novel_title=self.generator.novel_data["novel_title"],
            core_worldview=self.generator.novel_data.get("core_worldview", {}),
            selected_plan=self.generator.novel_data["selected_plan"],
            market_analysis=self.generator.novel_data.get("market_analysis", {}),
            design_level="core",
            global_growth_plan=self.generator.novel_data.get("global_growth_plan"),
            overall_stage_plans=self.generator.novel_data.get("overall_stage_plans"),
            custom_main_character_name=getattr(self.generator, 'custom_main_character_name', None) or ""
        )
        
        if not core_characters:
            print("❌ 核心角色设计失败，终止生成")
            return False
        
        # 持久化核心角色数据
        print("=== 步骤 4.5: 持久化核心角色数据 ===")
        
        # 检查 quality_assessor 是否已初始化
        if self.generator.quality_assessor is not None:
            self.generator.quality_assessor.persist_initial_character_designs(
                novel_title=self.generator.novel_data["novel_title"],
                character_design=core_characters
            )
        else:
            # 如果还没有初始化，使用临时保存
            print("⚠️ 质量评估器尚未初始化，将延迟持久化")
        
        self.generator.novel_data["character_design"] = core_characters
        print("✅ 核心角色设计完成，已建立角色基础库。")
        
        # 角色设计完成
        if update_step_status:
            update_step_status('character_design', 'completed', 55)
        
        return True
    
    def _generate_overall_planning(self, update_step_status=None) -> bool:
        """生成全书规划"""
        print("\n" + "="*60)
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 生成情绪蓝图 - 步骤11
        print("🎨 步骤11: 情绪蓝图规划")
        self.generator.novel_data["current_progress"]["stage"] = "情绪蓝图规划"
        if update_step_status:
            update_step_status('emotional_blueprint', 'active', 60)
        
        if not self.generator.emotional_blueprint_manager.generate_emotional_blueprint(
            self.generator.novel_data["novel_title"],
            self.generator.novel_data["novel_synopsis"],
            self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
        ):
            print("❌ 情绪蓝图生成失败，无法进行后续情绪引导。")
            return False
        
        if update_step_status:
            update_step_status('emotional_blueprint', 'completed', 65)
        
        # 全局成长规划 - 步骤12
        print("📈 步骤12: 成长规划")
        self.generator.novel_data["current_progress"]["stage"] = "成长规划"
        if update_step_status:
            update_step_status('growth_plan', 'active', 68)
        
        if not self._generate_global_growth_plan():
            print("⚠️ 全局成长规划生成失败，使用基础框架")
        
        if update_step_status:
            update_step_status('growth_plan', 'completed', 70)
        
        # 生成全书阶段计划 - 步骤13
        print("🗓️ 步骤13: 阶段计划")
        self.generator.novel_data["current_progress"]["stage"] = "阶段计划"
        if update_step_status:
            update_step_status('stage_plan', 'active', 72)
        
        creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        overall_stage_plans = self.generator.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self.generator.novel_data["novel_title"],
            self.generator.novel_data["novel_synopsis"],
            self.generator.novel_data.get("market_analysis", {}),
            self.generator.novel_data.get("global_growth_plan", {}),
            self.generator.novel_data.get("emotional_blueprint", {}),
            total_chapters
        )
        
        self.generator.novel_data["overall_stage_plans"] = overall_stage_plans
        
        if not overall_stage_plans:
            print("⚠️ 全书阶段计划生成失败，使用默认阶段划分")
        
        if update_step_status:
            update_step_status('stage_plan', 'completed', 75)
        
        # 生成阶段详细写作计划 - 步骤14
        print("📋 步骤14: 阶段详细计划")
        self.generator.novel_data["current_progress"]["stage"] = "阶段详细计划"
        if update_step_status:
            update_step_status('detailed_stage_plans', 'active', 76)
        
        if not self._generate_stage_writing_plans():
            print("❌ 生成阶段详细写作计划失败")
            return False
        
        if update_step_status:
            update_step_status('detailed_stage_plans', 'completed', 78)
        
        # 元素登场时机已由期待感系统管理 - 步骤15
        print("🎯 步骤15: 期待感映射")
        self.generator.novel_data["current_progress"]["stage"] = "期待感映射"
        if update_step_status:
            update_step_status('expectation_mapping', 'active', 79)
        
        print("✅ 元素登场时机由期待感系统统一管理")
        
        if update_step_status:
            update_step_status('expectation_mapping', 'completed', 80)
        
        # 初始化系统 - 步骤16
        print("⚙️ 步骤16: 系统初始化")
        self.generator.novel_data["current_progress"]["stage"] = "系统初始化"
        if update_step_status:
            update_step_status('system_init', 'active', 82)
        
        self._initialize_systems()
        
        if update_step_status:
            update_step_status('system_init', 'completed', 85)
        
        return True
    
    def _prepare_content_generation(self, update_step_status=None) -> bool:
        """准备内容生成"""
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 保存结果 - 步骤17
        print("💾 步骤17: 保存设定结果")
        self.generator.novel_data["current_progress"]["stage"] = "保存设定结果"
        if update_step_status:
            update_step_status('saving', 'active', 87)
        
        # 创建项目目录和保存初始进度
        self._initialize_project()
        
        if update_step_status:
            update_step_status('saving', 'completed', 90)
        
        return True
    
    def _generate_writing_style_guide(self) -> bool:
        """生成写作风格指南"""
        print("=== 步骤1.5: 生成写作风格指南 ===")
        
        # 🔥 先获取 category，确保即使在异常时也能使用
        category = self.generator.novel_data.get("category", "未分类")
        
        try:
            # 🔥 安全获取 creative_seed，如果不存在则使用 selected_plan
            creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
            selected_plan = self.generator.novel_data.get("selected_plan", {})
            market_analysis = self.generator.novel_data.get("market_analysis", {})
            
            writing_style = self.generator.content_generator.generate_writing_style_guide(
                creative_seed, category, selected_plan, market_analysis
            )
            
            if writing_style:
                self.generator.novel_data["writing_style_guide"] = writing_style
                print("✅ 写作风格指南生成完成")
                self.generator._save_writing_style_to_file(writing_style)
                return True
            else:
                print("⚠️ 写作风格指南生成失败，使用默认风格")
                self.generator.novel_data["writing_style_guide"] = self._get_default_writing_style(category)
                return True
                
        except Exception as e:
            print(f"⚠️ 生成写作风格指南时出错: {e}")
            self.generator.novel_data["writing_style_guide"] = self._get_default_writing_style(category)
            return True
    
    def _generate_market_analysis(self) -> bool:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        # 🔥 安全获取 creative_seed
        creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
        selected_plan = self.generator.novel_data.get("selected_plan", {})
        
        market_analysis = self.generator.content_generator.generate_market_analysis(creative_seed, selected_plan)
        
        self.generator.novel_data["market_analysis"] = market_analysis
        
        if not market_analysis:
            print("  ❌ 市场分析失败，终止生成")
            return False
        
        print("  ✅ 市场分析完成")
        
        # 保存到材料管理器
        self.generator._save_material_to_manager("市场分析", market_analysis, creative_seed=creative_seed)
        return True
    
    def _generate_worldview(self) -> bool:
        """生成世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        core_worldview = self.generator.content_generator.generate_core_worldview(
            self.generator.novel_data["novel_title"],
            self.generator.novel_data["novel_synopsis"],
            self.generator.novel_data["selected_plan"],
            self.generator.novel_data.get("market_analysis", {})
        )
        
        self.generator.novel_data["core_worldview"] = core_worldview
        
        if not core_worldview:
            print("❌ 世界观构建失败，终止生成")
            return False
        
        print("✅ 世界观构建完成")
        
        # 保存到材料管理器
        self.generator._save_material_to_manager("世界观", core_worldview, novel_title=self.generator.novel_data["novel_title"])
        return True
    
    def _generate_global_growth_plan(self) -> bool:
        """生成全局成长规划"""
        print("=== 步骤5: 制定全书成长规划框架 ===")
        
        try:
            self.generator.novel_data["global_growth_plan"] = self.generator.global_growth_planner.generate_global_growth_plan()
            
            if self.generator.novel_data["global_growth_plan"]:
                print("✅ 全书成长规划框架制定完成")
                return True
            else:
                print("❌ 全书成长规划生成失败，使用基础框架")
                return False
                
        except Exception as e:
            print(f"⚠️ 全局成长规划器出错: {e}，使用基础框架")
            return False
    
    def _generate_stage_writing_plans(self) -> bool:
        """生成各阶段详细写作计划"""
        print("=== 步骤6: 生成各阶段详细写作计划 ===")
        
        overall_stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            stage_plan_container = overall_stage_plans
            stage_plan_dict = stage_plan_container["overall_stage_plan"]
            
            self.generator.novel_data["stage_writing_plans"] = {}
            
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                
                print(f"  📋 生成 {stage_name} 的详细写作计划...")
                print(f"  📋 章节范围: {stage_range}")
                
                stage_plan = self.generator.stage_plan_manager.generate_stage_writing_plan(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=self.generator.novel_data["creative_seed"],
                    novel_title=self.generator.novel_data["novel_title"],
                    novel_synopsis=self.generator.novel_data["novel_synopsis"],
                    overall_stage_plan=stage_plan_dict
                )
                
                if stage_plan:
                    self.generator.novel_data["stage_writing_plans"][stage_name] = stage_plan
                    print(f"  ✅ {stage_name} 详细计划生成成功")
                else:
                    print(f"  ❌ {stage_name} 详细计划生成失败")
            
            success_count = len(self.generator.novel_data["stage_writing_plans"])
            if success_count > 0:
                print(f"✅ 阶段详细计划生成完成: {success_count}/{len(stage_plan_dict)} 个阶段")
                
                # 🔥 新增：为每个阶段生成并保存期待感映射
                self._generate_and_save_expectation_maps()
                
                self.generator._save_material_to_manager("阶段计划", self.generator.novel_data["stage_writing_plans"], total_stages=success_count)
                return True
            else:
                print("❌ 所有阶段详细计划生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 生成阶段详细写作计划时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ElementTimingPlanner已移除，元素登场时机由期待感系统统一管理
    
    def _generate_and_save_expectation_maps(self):
        """为所有阶段生成并保存期待感映射"""
        try:
            print("\n=== 步骤6.5: 生成期待感映射 ===")
            
            from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator
            
            # 创建期待感管理器
            expectation_manager = ExpectationManager()
            expectation_integrator = ExpectationIntegrator(expectation_manager)
            
            all_expectation_maps = {}
            total_tagged = 0
            
            # 遍历所有阶段
            for stage_name, stage_plan in self.generator.novel_data["stage_writing_plans"].items():
                stage_writing_plan = stage_plan.get("stage_writing_plan", {})
                major_events = stage_writing_plan.get("event_system", {}).get("major_events", [])
                
                if not major_events:
                    print(f"  ⚠️ {stage_name} 没有重大事件，跳过")
                    continue
                
                print(f"  📋 为 {stage_name} 的 {len(major_events)} 个事件生成期待感...")
                
                # 为该阶段的每个事件生成期待感标签
                stage_tagged = 0
                for event in major_events:
                    try:
                        event_name = event.get("name", "未命名事件")
                        # 🔥 修复：确保事件有id字段，如果没有则生成一个
                        event_id = event.get("id")
                        if not event_id:
                            event_id = f"event_{event_name}"
                            # 将生成的id添加到事件对象中，确保后续访问时使用相同的id
                            event["id"] = event_id
                        
                        # 使用自动选择期待类型（从API复用）
                        from web.api.phase_generation_api import select_expectation_type
                        exp_type = select_expectation_type(event)
                        
                        # 解析章节范围
                        chapter_range = event.get("chapter_range", "1-10")
                        try:
                            from src.managers.StagePlanUtils import parse_chapter_range
                            start_ch, end_ch = parse_chapter_range(chapter_range)
                            target_ch = max(start_ch + 3, end_ch)
                        except:
                            target_ch = end_ch
                            start_ch = 1
                        
                        # 种植期待
                        exp_id = expectation_manager.tag_event_with_expectation(
                            event_id=event_id,
                            expectation_type=exp_type,
                            planting_chapter=start_ch,
                            description=f"{event_name}: {event.get('main_goal', '')[:80]}...",
                            target_chapter=target_ch
                        )
                        
                        stage_tagged += 1
                    except Exception as e:
                        print(f"    ❌ 为事件 '{event.get('name')}' 生成期待感失败: {e}")
                        continue
                
                total_tagged += stage_tagged
                print(f"    ✅ {stage_name} 成功标记 {stage_tagged} 个事件")
                
                # 导出该阶段的期待感映射
                expectation_map = expectation_manager.export_expectation_map()
                
                # 清空管理器，为下一阶段准备
                expectation_manager = ExpectationManager()
                expectation_integrator = ExpectationIntegrator(expectation_manager)
                
                # 保存到阶段计划中
                all_expectation_maps[stage_name] = expectation_map
            
            # 将所有期待感映射保存到stage_writing_plans中
            if all_expectation_maps:
                for stage_name, expectation_map in all_expectation_maps.items():
                    if stage_name in self.generator.novel_data["stage_writing_plans"]:
                        stage_plan = self.generator.novel_data["stage_writing_plans"][stage_name]
                        if "stage_writing_plan" not in stage_plan:
                            stage_plan["stage_writing_plan"] = {}
                        stage_plan["stage_writing_plan"]["expectation_map"] = expectation_map
                
                print(f"✅ 期待感映射生成完成: {len(all_expectation_maps)} 个阶段, 共 {total_tagged} 个事件")
            else:
                print("⚠️ 未生成任何期待感映射")
            
        except Exception as e:
            print(f"❌ 生成期待感映射时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _initialize_systems(self):
        """初始化各种系统"""
        print("=== 步骤7: 初始化系统 ===")
        
        if self.generator.novel_data["overall_stage_plans"]:
            self.generator.event_driven_manager.initialize_event_system()
            print("✅ 事件系统初始化完成")
        
        if self.generator.novel_data["character_design"]:
            self.generator.initialize_expectation_elements()
            print("✅ 期待感管理系统已就绪")
        
        print("✅ 第一阶段详细写作计划已生成")
    
    def _initialize_project(self):
        """初始化项目"""
        import re
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.generator.novel_data["novel_title"])
        import os
        
        # 使用新的路径配置系统
        from src.config.path_config import path_config
        paths = path_config.ensure_directories(self.generator.novel_data["novel_title"])
        
        print(f"✅ 项目目录已创建: {paths['project_root']}")
        print(f"📁 章节目录: {paths['chapters_dir']}")
        
        self.generator.project_manager.save_project_progress(self.generator.novel_data)
        print("✅ 项目初始进度已保存")
    
    def _get_default_writing_style(self, category: str) -> Dict:
        """根据分类获取默认的写作风格"""
        return {
            "core_style": "语言流畅自然，情节推进合理",
            "language_features": ["表达清晰", "描写生动", "节奏适中"],
            "narrative_pace": "稳步推进，高潮适当",
            "dialogue_style": "符合人物身份，自然流畅",
            "description_focus": ["情节推进", "人物刻画", "环境描写"],
            "emotional_tone": "情感真实，有感染力",
            "chapter_structure": "章节完整，衔接自然",
            "important_notes": ["保持风格一致性", "注意情节逻辑", "强化读者代入感"]
        }
    
    def _save_phase_one_result(self):
        """保存第一阶段结果到统一路径配置系统"""
        try:
            import re
            from src.config.path_config import path_config
            
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.generator.novel_data["novel_title"])
            
            print(f"🔧 原始标题: {self.generator.novel_data['novel_title']}")
            print(f"🔧 安全标题: {safe_title}")
            
            # 检查novel_data
            missing_fields = []
            required_fields = ['novel_title', 'novel_synopsis', 'category', 'current_progress']
            for field in required_fields:
                if field not in self.generator.novel_data or not self.generator.novel_data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"❌ 缺少必需字段: {missing_fields}")
                return False
            
            # 使用统一路径配置系统创建目录结构
            paths = path_config.ensure_directories(self.generator.novel_data["novel_title"])
            print(f"✅ 项目目录已创建: {paths['project_root']}")
            
            # 不再创建单独的第一阶段目录，所有文件统一保存到主项目目录
            # 产物文件将保存到materials/目录的子目录中
            products_dir = f"{paths['materials_dir']}/phase_one_products"
            os.makedirs(products_dir, exist_ok=True)
            print(f"📁 产物目录: {products_dir}")
            
            # 保存各个产物
            products_mapping = {}
            
            # 1. 市场分析
            if "market_analysis" in self.generator.novel_data and self.generator.novel_data["market_analysis"]:
                market_file = paths["market_analysis"]
                os.makedirs(os.path.dirname(market_file), exist_ok=True)
                with open(market_file, 'w', encoding='utf-8') as f:
                    json.dump(self.generator.novel_data["market_analysis"], f, ensure_ascii=False, indent=2)
                products_mapping["market_analysis"] = market_file
                print(f"✅ 市场分析已保存: {market_file}")
            
            # 2. 世界观设定
            if "core_worldview" in self.generator.novel_data and self.generator.novel_data["core_worldview"]:
                worldview_dir = paths["worldview_dir"]
                os.makedirs(worldview_dir, exist_ok=True)
                worldview_file = os.path.join(worldview_dir, f"{safe_title}_世界观.json")
                with open(worldview_file, 'w', encoding='utf-8') as f:
                    json.dump(self.generator.novel_data["core_worldview"], f, ensure_ascii=False, indent=2)
                products_mapping["core_worldview"] = worldview_file
                print(f"✅ 世界观设定已保存: {worldview_file}")
            
            # 2.5. 势力/阵营系统
            if "faction_system" in self.generator.novel_data and self.generator.novel_data["faction_system"]:
                worldview_dir = paths["worldview_dir"]
                os.makedirs(worldview_dir, exist_ok=True)
                faction_file = os.path.join(worldview_dir, f"{safe_title}_势力系统.json")
                with open(faction_file, 'w', encoding='utf-8') as f:
                    json.dump(self.generator.novel_data["faction_system"], f, ensure_ascii=False, indent=2)
                products_mapping["faction_system"] = faction_file
                print(f"✅ 势力/阵营系统已保存: {faction_file}")  # 🔥 修复：日志现在正确显示.json扩展名
            
            # 3. 角色设计
            if "character_design" in self.generator.novel_data and self.generator.novel_data["character_design"]:
                character_file = paths["character_design_file"]
                os.makedirs(os.path.dirname(character_file), exist_ok=True)
                with open(character_file, 'w', encoding='utf-8') as f:
                    json.dump(self.generator.novel_data["character_design"], f, ensure_ascii=False, indent=2)
                products_mapping["character_design"] = character_file
                print(f"✅ 角色设计已保存: {character_file}")
            
            # 4-9. 其他产物
            product_mappings = [
                ("global_growth_plan", f"{safe_title}_成长路线.json"),
                ("overall_stage_plans", f"{safe_title}_阶段计划.json"),
                ("stage_writing_plans", f"{safe_title}_写作计划.json"),
                # 元素时机规划已移除，由期待感系统管理
                ("writing_style_guide", f"{safe_title}_写作风格.json"),
                ("emotional_blueprint", f"{safe_title}_情绪蓝图.json")
            ]
            
            for key, filename in product_mappings:
                if key in self.generator.novel_data and self.generator.novel_data[key]:
                    file_path = f"{products_dir}/{filename}"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(self.generator.novel_data[key], f, ensure_ascii=False, indent=2)
                    products_mapping[key] = file_path
                    print(f"✅ {key}已保存: {file_path}")
            
            # 创建第一阶段索引文件（保存到主项目materials目录）
            phase_one_index = {
                "novel_title": self.generator.novel_data["novel_title"],
                "novel_synopsis": self.generator.novel_data["novel_synopsis"],
                "category": self.generator.novel_data.get("category", "未分类"),
                "total_chapters": self.generator.novel_data["current_progress"]["total_chapters"],
                "creative_seed": self.generator.novel_data["creative_seed"],
                "selected_plan": self.generator.novel_data["selected_plan"],
                "products_mapping": products_mapping,
                "is_phase_one_completed": True,
                "phase_one_completed_at": datetime.now().isoformat(),
                "next_phase": "second_phase_content_generation"
            }
            
            # 保存第一阶段索引文件到materials目录
            phase_one_index_file = f"{paths['materials_dir']}/{safe_title}_第一阶段索引.json"
            with open(phase_one_index_file, 'w', encoding='utf-8') as f:
                json.dump(phase_one_index, f, ensure_ascii=False, indent=2)
            print(f"✅ 第一阶段索引文件已保存: {phase_one_index_file}")
            
            # 同时保存为主项目信息文件（使用用户隔离路径）
            # 获取用户隔离基础路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                username = getattr(self.generator, '_username', None)
                user_base_dir = get_user_novel_dir(username=username, create=True)
            except Exception:
                user_base_dir = Path("小说项目")
            
            main_project_file = user_base_dir / safe_title / f"{safe_title}_项目信息.json"
            # 确保目录存在
            os.makedirs(os.path.dirname(str(main_project_file)), exist_ok=True)
            project_info = {
                "novel_title": self.generator.novel_data["novel_title"],
                "novel_synopsis": self.generator.novel_data["novel_synopsis"],
                "category": self.generator.novel_data.get("category", "未分类"),
                "total_chapters": self.generator.novel_data["current_progress"]["total_chapters"],
                "creative_seed": self.generator.novel_data["creative_seed"],
                "selected_plan": self.generator.novel_data["selected_plan"],
                "phase_one_index_file": phase_one_index_file,
                "products_mapping": products_mapping,
                "is_phase_one_completed": True,
                "phase_one_completed_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            with open(main_project_file, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, ensure_ascii=False, indent=2)
            print(f"✅ 项目信息已保存: {main_project_file}")
            
            print(f"🎉 第一阶段结果保存完成！(已保存为{len(products_mapping)}个单独文件)")
            
            # 删除临时文件（包括用户隔离路径下的）
            try:
                import glob
                from pathlib import Path
                
                temp_files = []
                # 清理根目录下的临时文件（兼容旧路径）
                temp_files_pattern = os.path.join("小说项目", "未定稿创意_*_Refined_AI_Brief.txt")
                temp_files.extend(glob.glob(temp_files_pattern))
                
                # 清理用户隔离路径下的临时文件
                try:
                    from web.utils.path_utils import get_user_novel_dir
                    user_dir = get_user_novel_dir(create=False)
                    if user_dir.exists():
                        user_pattern = os.path.join(user_dir, "未定稿创意_*_Refined_AI_Brief.txt")
                        temp_files.extend(glob.glob(user_pattern))
                except Exception:
                    pass  # 如果没有 Flask 上下文，忽略用户路径
                
                if temp_files:
                    print(f"🗑️  找到 {len(temp_files)} 个临时文件，准备删除...")
                    for temp_file in temp_files:
                        try:
                            os.remove(temp_file)
                            print(f"✅  已删除临时文件: {temp_file}")
                        except Exception as e:
                            print(f"⚠️  删除临时文件失败: {temp_file}, 错误: {e}")
                else:
                    print("ℹ️  未找到临时文件需要删除")
                    
            except Exception as e:
                print(f"⚠️  清理临时文件过程出错: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ 保存第一阶段结果失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    # ==================== 第二阶段生成方法 ====================
    
    def generate_phase_two(self, phase_one_result_file: str, from_chapter: int = 1, chapters_to_generate: Optional[int] = None) -> bool:
        """
        第二阶段生成：基于第一阶段结果生成章节内容
        
        Args:
            phase_one_result_file: 第一阶段结果文件路径
            from_chapter: 起始章节
            chapters_to_generate: 要生成的章节数量
            
        Returns:
            是否成功
        """
        try:
            print("[START] 开始第二阶段章节生成...")
            
            # 从统一的项目目录结构加载
            import re
            from src.config.path_config import path_config
            
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", phase_one_result_file.replace("_第一阶段设定.json", "").replace("\\", "/"))
            paths = path_config.get_project_paths(safe_title)
            products_dir = f"{paths['materials_dir']}/phase_one_products"
            
            print(f"🔍 检查统一产物目录: {products_dir}")
            
            if os.path.exists(products_dir):
                # 使用统一的文件结构：从单独文件读取
                print("📂 使用统一的文件结构，从单独文件读取产物...")
                return self._load_phase_two_from_unified_structure(products_dir, safe_title, paths, from_chapter, chapters_to_generate)
            else:
                # 兼容旧的文件结构
                print("📋 兼容旧的文件结构，尝试从索引文件读取产物...")
                return self._load_phase_two_from_index_file(phase_one_result_file, from_chapter, chapters_to_generate)
            
        except Exception as e:
            print(f"❌ 第二阶段生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_phase_two_from_unified_structure(self, products_dir: str, safe_title: str, paths: dict, from_chapter: int, chapters_to_generate: Optional[int] = None) -> bool:
        """从统一的项目目录结构加载第二阶段数据"""
        try:
            products_mapping = {}
            
            # 首先读取第一阶段索引文件获取基础信息
            phase_one_index_file = f"{paths['materials_dir']}/{safe_title}_第一阶段索引.json"
            phase_one_index = {}
            
            if os.path.exists(phase_one_index_file):
                with open(phase_one_index_file, 'r', encoding='utf-8') as f:
                    phase_one_index = json.load(f)
                print(f"✅ 已加载第一阶段索引文件")
            else:
                print(f"⚠️ 第一阶段索引文件不存在: {phase_one_index_file}")
            
            # 读取各个产物文件（从统一的项目目录）
            product_files = {
                "market_analysis": f"{paths['market_analysis']}",
                "core_worldview": f"{paths['worldview_dir']}/{safe_title}_世界观.json",
                "faction_system": f"{paths['worldview_dir']}/{safe_title}_势力系统.json",
                "character_design": paths["character_design_file"],
                "global_growth_plan": f"{products_dir}/{safe_title}_成长路线.json",
                "overall_stage_plans": f"{products_dir}/{safe_title}_阶段计划.json",
                "stage_writing_plans": f"{products_dir}/{safe_title}_写作计划.json",
                "writing_style_guide": f"{products_dir}/{safe_title}_写作风格.json",
                "emotional_blueprint": f"{products_dir}/{safe_title}_情绪蓝图.json"
            }
            
            for product_name, file_path in product_files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        products_mapping[product_name] = json.load(f)
                    print(f"✅ 已加载产物: {product_name}")
                else:
                    print(f"⚠️ 产物文件不存在: {product_name} - {file_path}")
            
            # 从索引文件或使用默认值获取基础信息
            total_chapters = phase_one_index.get("total_chapters", 200) if phase_one_index else 200
            
            # 构建小说数据
            self.generator.novel_data = {
                "novel_title": phase_one_index.get("novel_title", safe_title) if phase_one_index else safe_title,
                "novel_synopsis": phase_one_index.get("novel_synopsis", "") if phase_one_index else "",
                "category": phase_one_index.get("category", "未分类") if phase_one_index else "未分类",
                "total_chapters": total_chapters,
                "creative_seed": phase_one_index.get("creative_seed", {}) if phase_one_index else {},
                "selected_plan": phase_one_index.get("selected_plan", {}) if phase_one_index else {},
                "writing_style_guide": products_mapping.get("writing_style_guide", {}),
                "market_analysis": products_mapping.get("market_analysis", {}),
                "core_worldview": products_mapping.get("core_worldview", {}),
                "faction_system": products_mapping.get("faction_system", {}),
                "character_design": products_mapping.get("character_design", {}),
                "global_growth_plan": products_mapping.get("global_growth_plan", {}),
                "overall_stage_plans": products_mapping.get("overall_stage_plans", {}),
                "stage_writing_plans": products_mapping.get("stage_writing_plans", {}),
                "emotional_blueprint": products_mapping.get("emotional_blueprint", {}),
                "current_progress": {
                    "completed_chapters": 0,
                    "total_chapters": total_chapters,
                    "stage": "第二阶段章节生成",
                    "current_stage": "第二阶段",
                    "current_batch": 0,
                    "start_time": datetime.now().isoformat()
                },
                "generated_chapters": {},
                "used_chapter_titles": set(),
                "previous_chapter_endings": {},
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            # 初始化质量评估器
            novel_title = self.generator.novel_data['novel_title']
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title
            )
            self.generator.content_generator.quality_assessor = self.generator.quality_assessor
            print(f"✅ 质量评估器已初始化: {novel_title}")
            
            print(f"📚 小说标题: {self.generator.novel_data['novel_title']}")
            print(f"📝 简介: {self.generator.novel_data['novel_synopsis'][:100] if self.generator.novel_data['novel_synopsis'] else '无'}...")
            print(f"🏷️ 分类: {self.generator.novel_data['category']}")
            print(f"📊 总章节数: {self.generator.novel_data['total_chapters']}")
            
            # 确定要生成的章节数
            total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
            if chapters_to_generate:
                total_chapters = min(from_chapter + chapters_to_generate - 1, total_chapters)
            
            print(f"📚 从第{from_chapter}章生成到第{total_chapters}章")
            
            # 执行章节生成
            return self._generate_all_chapters(total_chapters, start_chapter=from_chapter)
            
        except Exception as e:
            print(f"❌ 从统一结构加载第二阶段数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_phase_two_from_separate_files(self, phase_one_dir: str, safe_title: str, from_chapter: int, chapters_to_generate: Optional[int] = None) -> bool:
        """从单独的产物文件加载第二阶段数据"""
        try:
            products_dir = f"{phase_one_dir}/产物"
            products_mapping = {}
            
            # 首先读取第一阶段索引文件获取基础信息
            phase_one_index_file = f"{phase_one_dir}/{safe_title}_第一阶段索引.json"
            phase_one_index = {}
            
            if os.path.exists(phase_one_index_file):
                with open(phase_one_index_file, 'r', encoding='utf-8') as f:
                    phase_one_index = json.load(f)
                print(f"✅ 已加载第一阶段索引文件")
            else:
                print(f"⚠️ 第一阶段索引文件不存在: {phase_one_index_file}")
            
            # 读取各个产物文件
            product_files = {
                "market_analysis": f"{products_dir}/{safe_title}_市场分析.json",
                "core_worldview": f"{products_dir}/{safe_title}_世界观设定.json",
                "character_design": f"{products_dir}/{safe_title}_角色设计.json",
                "global_growth_plan": f"{products_dir}/{safe_title}_成长路线.json",
                "overall_stage_plans": f"{products_dir}/{safe_title}_阶段计划.json",
                "stage_writing_plans": f"{products_dir}/{safe_title}_写作计划.json",
                # 元素时机规划已移除，由期待感系统管理
                "writing_style_guide": f"{products_dir}/{safe_title}_写作风格.json",
                "emotional_blueprint": f"{products_dir}/{safe_title}_情绪蓝图.json"
            }
            
            for product_name, file_path in product_files.items():
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        products_mapping[product_name] = json.load(f)
                    print(f"✅ 已加载产物: {product_name}")
                else:
                    print(f"⚠️ 产物文件不存在: {product_name}")
            
            # 从索引文件获取基础信息
            total_chapters = phase_one_index.get("total_chapters", 200)
            
            # 构建小说数据
            self.generator.novel_data = {
                "novel_title": phase_one_index.get("novel_title", safe_title),
                "novel_synopsis": phase_one_index.get("novel_synopsis", ""),
                "category": phase_one_index.get("category", "未分类"),
                "total_chapters": total_chapters,
                "creative_seed": phase_one_index.get("creative_seed", {}),
                "selected_plan": phase_one_index.get("selected_plan", {}),
                "writing_style_guide": products_mapping.get("writing_style_guide", {}),
                "market_analysis": products_mapping.get("market_analysis", {}),
                "core_worldview": products_mapping.get("core_worldview", {}),
                "character_design": products_mapping.get("character_design", {}),
                "global_growth_plan": products_mapping.get("global_growth_plan", {}),
                "overall_stage_plans": products_mapping.get("overall_stage_plans", {}),
                "stage_writing_plans": products_mapping.get("stage_writing_plans", {}),
                # 元素时机规划已移除，由期待感系统管理
                "emotional_blueprint": products_mapping.get("emotional_blueprint", {}),
                "current_progress": {
                    "completed_chapters": 0,
                    "total_chapters": total_chapters,
                    "stage": "第二阶段章节生成",
                    "current_stage": "第二阶段",
                    "current_batch": 0,
                    "start_time": datetime.now().isoformat()
                },
                "generated_chapters": {},
                "used_chapter_titles": set(),
                "previous_chapter_endings": {},
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            # 初始化质量评估器
            novel_title = self.generator.novel_data['novel_title']
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title
            )
            self.generator.content_generator.quality_assessor = self.generator.quality_assessor
            print(f"✅ 质量评估器已初始化: {novel_title}")
            
            print(f"📚 小说标题: {self.generator.novel_data['novel_title']}")
            print(f"📝 简介: {self.generator.novel_data['novel_synopsis'][:100] if self.generator.novel_data['novel_synopsis'] else '无'}...")
            print(f"🏷️ 分类: {self.generator.novel_data['category']}")
            print(f"📊 总章节数: {self.generator.novel_data['total_chapters']}")
            
            # 确定要生成的章节数
            total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
            if chapters_to_generate:
                total_chapters = min(from_chapter + chapters_to_generate - 1, total_chapters)
            
            print(f"📚 从第{from_chapter}章生成到第{total_chapters}章")
            
            # 执行章节生成
            return self._generate_all_chapters(total_chapters, start_chapter=from_chapter)
            
        except Exception as e:
            print(f"❌ 从单独文件加载第二阶段数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_phase_two_from_index_file(self, phase_one_result_file: str, from_chapter: int, chapters_to_generate: Optional[int] = None) -> bool:
        """从索引文件加载第二阶段数据（兼容旧版本）"""
        try:
            if not os.path.exists(phase_one_result_file):
                print(f"❌ 第一阶段索引文件不存在: {phase_one_result_file}")
                return False
            
            with open(phase_one_result_file, 'r', encoding='utf-8') as f:
                phase_one_index = json.load(f)
            
            # 检查是否有products_mapping
            if "products_mapping" not in phase_one_index:
                print("❌ 第一阶段索引文件中缺少products_mapping，使用旧的数据结构")
                return self._load_phase_two_from_old_format(phase_one_index, from_chapter, chapters_to_generate)
            
            products_mapping = phase_one_index["products_mapping"]
            
            # 从单独的产物文件加载
            products_dir = os.path.dirname(phase_one_result_file)
            loaded_data = {}
            
            for product_name, file_path in products_mapping.items():
                full_path = os.path.join(products_dir, "产物", os.path.basename(file_path))
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        loaded_data[product_name] = json.load(f)
                    print(f"✅ 已加载产物: {product_name}")
                else:
                    print(f"⚠️ 产物文件不存在: {product_name}")
            
            # 初始化质量评估器
            novel_title = phase_one_index["novel_title"]
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title
            )
            self.generator.content_generator.quality_assessor = self.generator.quality_assessor
            print(f"✅ 质量评估器已初始化: {novel_title}")
            
            # 构建小说数据
            self.generator.novel_data = {
                "novel_title": phase_one_index["novel_title"],
                "novel_synopsis": phase_one_index["novel_synopsis"],
                "category": phase_one_index.get("category", "未分类"),
                "total_chapters": phase_one_index.get("total_chapters", 200),
                "creative_seed": phase_one_index["creative_seed"],
                "selected_plan": phase_one_index["selected_plan"],
                "writing_style_guide": loaded_data.get("writing_style_guide", {}),
                "market_analysis": loaded_data.get("market_analysis", {}),
                "core_worldview": loaded_data.get("core_worldview", {}),
                "character_design": loaded_data.get("character_design", {}),
                "global_growth_plan": loaded_data.get("global_growth_plan", {}),
                "overall_stage_plans": loaded_data.get("overall_stage_plans", {}),
                "stage_writing_plans": loaded_data.get("stage_writing_plans", {}),
                # 元素时机规划已移除，由期待感系统管理
                "emotional_blueprint": loaded_data.get("emotional_blueprint", {}),
                "current_progress": {
                    "completed_chapters": 0,
                    "total_chapters": phase_one_index.get("total_chapters", 200),
                    "stage": "第二阶段章节生成",
                    "current_stage": "第二阶段",
                    "current_batch": 0,
                    "start_time": datetime.now().isoformat()
                },
                "generated_chapters": {},
                "used_chapter_titles": set(),
                "previous_chapter_endings": {},
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            # 确定要生成的章节数
            total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
            if chapters_to_generate:
                total_chapters = min(from_chapter + chapters_to_generate - 1, total_chapters)
            
            print(f"📚 从第{from_chapter}章生成到第{total_chapters}章")
            
            # 执行章节生成
            return self._generate_all_chapters(total_chapters, start_chapter=from_chapter)
            
        except Exception as e:
            print(f"❌ 从索引文件加载第二阶段数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _load_phase_two_from_old_format(self, phase_one_result: Dict, from_chapter: int, chapters_to_generate: Optional[int] = None) -> bool:
        """从旧格式加载第二阶段数据（兼容性处理）"""
        try:
            # 初始化质量评估器
            novel_title = phase_one_result.get("novel_title", "未命名小说")
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title
            )
            self.generator.content_generator.quality_assessor = self.generator.quality_assessor
            print(f"✅ 质量评估器已初始化: {novel_title}")
            
            # 直接从phase_one_result中读取数据
            self.generator.novel_data = {
                "novel_title": phase_one_result.get("novel_title", "未命名小说"),
                "novel_synopsis": phase_one_result.get("novel_synopsis", ""),
                "category": phase_one_result.get("category", "未分类"),
                "total_chapters": phase_one_result.get("total_chapters", 200),
                "creative_seed": phase_one_result.get("creative_seed", {}),
                "selected_plan": phase_one_result.get("selected_plan", {}),
                "writing_style_guide": phase_one_result.get("writing_style_guide", {}),
                "market_analysis": phase_one_result.get("market_analysis", {}),
                "core_worldview": phase_one_result.get("core_worldview", {}),
                "character_design": phase_one_result.get("character_design", {}),
                "global_growth_plan": phase_one_result.get("global_growth_plan", {}),
                "overall_stage_plans": phase_one_result.get("overall_stage_plans", {}),
                "stage_writing_plans": phase_one_result.get("stage_writing_plans", {}),
                # 元素时机规划已移除，由期待感系统管理
                "current_progress": {
                    "completed_chapters": 0,
                    "total_chapters": phase_one_result.get("total_chapters", 200),
                    "stage": "第二阶段章节生成",
                    "current_stage": "第二阶段",
                    "current_batch": 0,
                    "start_time": datetime.now().isoformat()
                },
                "generated_chapters": {},
                "used_chapter_titles": set(),
                "previous_chapter_endings": {},
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            # 确定要生成的章节数
            total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
            if chapters_to_generate:
                total_chapters = min(from_chapter + chapters_to_generate - 1, total_chapters)
            
            print(f"📚 从第{from_chapter}章生成到第{total_chapters}章")
            
            # 执行章节生成
            return self._generate_all_chapters(total_chapters, start_chapter=from_chapter)
            
        except Exception as e:
            print(f"❌ 从旧格式加载第二阶段数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_all_chapters(self, total_chapters: int, start_chapter: int = 1) -> bool:
        """生成所有章节内容"""
        print("\n" + "="*60)
        print("📖 第五阶段：章节内容生成")
        print("="*60)
        
        print(f"开始生成第{start_chapter}-{total_chapters}章小说内容...")
        print("基于选定方案和创作方向进行创作")
        print("每章生成后将进行质量评估和优化")
        print("特别优化章节衔接，确保情节连贯性")
        print("🤖 新增AI痕迹检测和消除功能")
        print("每章将单独保存为包含质量评估的JSON文件")
        print("这个过程可能需要较长时间，请耐心等待...")
        print("提示: 按Ctrl+C可以安全中断，下次可继续生成")
        
        # 对于大规模生成，使用更小的批次
        import time
        actual_chapters_per_batch = min(3, self.generator.config.get("defaults", {}).get("chapters_per_batch", 3))
        
        for batch_start in range(start_chapter, total_chapters + 1, actual_chapters_per_batch):
            batch_end = min(batch_start + actual_chapters_per_batch - 1, total_chapters)
            self.generator.novel_data["current_progress"]["current_batch"] += 1
            
            print(f"\n批次{self.generator.novel_data['current_progress']['current_batch']}: 第{batch_start}-{batch_end}章")
            
            if not self._generate_chapters_batch(batch_start, batch_end):
                print(f"❌ 批次{self.generator.novel_data['current_progress']['current_batch']}生成失败")
                continue_gen = input("是否继续生成后续章节？(y/n): ").lower()
                if continue_gen != 'y':
                    break
            
            # 批次间延迟
            batch_delay = 2 if total_chapters > 100 else 2
            if batch_end < total_chapters:
                print(f"等待{batch_delay}秒后继续下一批次...")
                time.sleep(batch_delay)
        
        return self._finalize_generation()
    
    def _generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """批量生成章节"""
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                print(f"\n📖 开始生成第{chapter_num}章...")
                
                # 调用第二阶段进度回调（如果有）
                if hasattr(self.generator, '_phase_two_progress_callback') and callable(self.generator._phase_two_progress_callback):
                    try:
                        self.generator._phase_two_progress_callback(chapter_num, "generating")
                    except Exception as callback_error:
                        print(f"⚠️ 进度回调失败: {callback_error}")
                
                # 1. 准备生成上下文
                context = self._prepare_generation_context(chapter_num)
                
                if context is None:
                    print(f"❌ 第{chapter_num}章生成上下文为None，跳过该章")
                    continue
                
                # 2. 委托给ContentGenerator生成内容
                print(f"🔄 调用ContentGenerator生成第{chapter_num}章内容...")
                chapter_result = self.generator.content_generator.generate_chapter_content_for_novel(
                    chapter_num, self.generator.novel_data, context
                )

                if not chapter_result:
                    print(f"❌ 第{chapter_num}章内容生成失败")
                    continue

                # 3. 发布生成完成事件
                self.generator.event_bus.publish('chapter.generated', {
                    'chapter_number': chapter_num,
                    'result': chapter_result,
                    'context': context
                })

                # 4. 调用第二阶段进度回调
                if hasattr(self.generator, '_phase_two_progress_callback') and callable(self.generator._phase_two_progress_callback):
                    try:
                        chapter_data = {
                            "status": "completed",
                            "chapter_title": chapter_result.get('chapter_title', f"第{chapter_num}章"),
                            "word_count": chapter_result.get('word_count', len(chapter_result.get('content', ''))),
                            "error": None
                        }
                        self.generator._phase_two_progress_callback(chapter_num, "completed", chapter_data)
                    except Exception as callback_error:
                        print(f"⚠️ 进度回调失败: {callback_error}")

                print(f"✅ 第{chapter_num}章生成完成: {chapter_result.get('chapter_title', '未知标题')}")
                
            except Exception as e:
                error_msg = f"生成第{chapter_num}章时出错: {e}"
                print(f"❌ {error_msg}")
                
                self.generator.event_bus.publish('error.occurred', {
                    'type': 'generation_failed',
                    'chapter': chapter_num,
                    'error': str(e)
                })
        
        return True
    
    def _prepare_generation_context(self, chapter_num: int):
        """准备生成上下文"""
        try:
            print(f"🔍 开始准备第{chapter_num}章生成上下文...")
            
            # 初始化所有上下文变量
            event_context = {}
            foreshadowing_context = {}
            growth_context = {}
            stage_plan = {}
            
            # 获取各个管理器的上下文
            print(f"  📊 获取事件上下文...")
            if hasattr(self.generator, 'event_driven_manager') and hasattr(self.generator.event_driven_manager, 'get_context'):
                try:
                    event_context = self.generator.event_driven_manager.get_context(chapter_num)
                    print(f"    ✅ 事件上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取事件上下文失败: {e}")
                    event_context = {}
            
            print(f"  🎭 获取期待感上下文...")
            if hasattr(self.generator, 'expectation_manager') and hasattr(self.generator.expectation_manager, 'pre_generation_check'):
                try:
                    expectation_constraints = self.generator.expectation_manager.pre_generation_check(
                        chapter_num,
                        event_context
                    )
                    foreshadowing_context = {
                        "expectation_constraints": expectation_constraints,
                        "active_expectations": len([
                            e for e in self.generator.expectation_manager.expectations.values()
                            if e.status.value in ["planted", "fermenting"]
                        ])
                    }
                    print(f"    ✅ 期待感上下文获取成功: {len(expectation_constraints)}个约束")
                except Exception as e:
                    print(f"    ⚠️ 获取期待感上下文失败: {e}")
                    foreshadowing_context = {}
            
            print(f"  📈 获取成长规划上下文...")
            if hasattr(self.generator, 'global_growth_planner') and hasattr(self.generator.global_growth_planner, 'get_context'):
                try:
                    growth_context = self.generator.global_growth_planner.get_context(chapter_num)
                    print(f"    ✅ 成长规划上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取成长规划上下文失败: {e}")
                    growth_context = {}
            
            print(f"  🎯 获取阶段计划...")
            if hasattr(self.generator, 'stage_plan_manager'):
                try:
                    stage_plan = self.generator.stage_plan_manager.get_stage_plan_for_chapter(chapter_num) or {}
                    print(f"    ✅ 阶段计划获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取阶段计划失败: {e}")
                    stage_plan = {}
            
            # 检查novel_data
            print(f"  📚 检查novel_data...")
            if not hasattr(self.generator, 'novel_data') or not self.generator.novel_data:
                print(f"    ⚠️ novel_data不存在或为空，创建基础结构")
                self.generator._initialize_data_structures()
            
            total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
            print(f"    ✅ novel_data存在, 总章节数: {total_chapters}")
            
            from src.core.Contexts import GenerationContext
            context = GenerationContext(
                chapter_number=chapter_num,
                total_chapters=total_chapters,
                novel_data=self.generator.novel_data,
                stage_plan=stage_plan,
                event_context=event_context,
                foreshadowing_context=foreshadowing_context,
                growth_context=growth_context
            )
            
            print(f"  ✅ 第{chapter_num}章上下文准备完成")
            
            return context
            
        except Exception as e:
            print(f"❌ 准备生成上下文失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回基础上下文
            print(f"🔄 返回基础上下文作为备选...")
            try:
                from src.core.Contexts import GenerationContext
                base_context = GenerationContext(
                    chapter_number=chapter_num,
                    total_chapters=self.generator.novel_data.get("current_progress", {}).get("total_chapters", 30) if hasattr(self.generator, 'novel_data') and self.generator.novel_data else 30,
                    novel_data=self.generator.novel_data if hasattr(self.generator, 'novel_data') else {},
                    stage_plan={},
                    event_context={},
                    foreshadowing_context={},
                    growth_context={}
                )
                return base_context
            except Exception as base_error:
                print(f"❌ 创建基础上下文也失败: {base_error}")
                return None
    
    def _finalize_generation(self) -> bool:
        """完成生成过程"""
        self.generator.novel_data["current_progress"]["stage"] = "完成"
        
        # 保存最终进度和导出总览
        self.generator.project_manager.save_project_progress(self.generator.novel_data)
        self.generator.project_manager.export_novel_overview(self.generator.novel_data)
        
        # 生成小说封面
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        completed_chapters = self.generator.novel_data["current_progress"]["completed_chapters"]
        
        if completed_chapters >= total_chapters:
            print("\n" + "="*60)
            print("🎨 最后一步：生成小说封面")
            print("="*60)
            self.generator.novel_data["current_progress"]["stage"] = "封面生成"
            if not self._generate_novel_cover():
                print("⚠️ 封面生成失败，项目已完成但无封面。")
        else:
            print(f"\n⚠️ 当前已完成 {completed_chapters}/{total_chapters} 章，封面将在所有章节生成完成后生成。")
        
        # 材料管理器导出功能
        if self.generator.material_manager:
            print("\n" + "="*60)
            print("📦 正在生成材料包...")
            print("="*60)
            
            try:
                bundle_result = self.generator.material_manager.create_material_bundle(
                    bundle_name="完整生成材料",
                    material_types=[],
                    time_range=("", ""),
                    include_metadata=True
                )
                
                if isinstance(bundle_result, dict) and bundle_result.get("success"):
                    print(f"✅ 完整材料包生成成功: {bundle_result.get('bundle_name')}")
                    print(f"📁 包含材料数量: {bundle_result.get('total_materials', 0)}个")
                    print(f"📍 保存路径: {bundle_result.get('bundle_path')}")
                else:
                    print(f"⚠️ 材料包生成失败")
                
                manifest = self.generator.material_manager.generate_material_manifest()
                if manifest:
                    print(f"✅ 材料清单生成成功")
                    print(f"📊 材料统计: {manifest.get('total_materials', 0)}个材料")
                    print(f"📂 材料类别: {len(manifest.get('material_categories', {}))}类")
                
                statistics = self.generator.material_manager.get_material_statistics()
                if statistics:
                    print(f"✅ 材料统计完成")
                    print(f"📈 总材料数: {statistics.get('total_materials', 0)}个")
                    print(f"💾 总大小: {statistics.get('total_size', 0)}字节")
                    print(f"📋 材料类型: {len(statistics.get('by_type', {}))}种")
                    
            except Exception as e:
                print(f"❌ 材料导出过程出错: {e}")
        
        print("\n🎉 小说生成完成！")
        self.generator._print_generation_summary()
        return True
    
    def _generate_novel_cover(self) -> bool:
        """生成小说封面"""
        author_name = "北莽王庭的达延"
        
        result = self.generator.cover_generator.generate_novel_cover(
            self.generator.novel_data.get("novel_title", ""),
            self.generator.novel_data.get("novel_synopsis", ""),
            self.generator.novel_data.get("category", "未分类"),
            author_name
        )
        
        if result.get("success"):
            self.generator.novel_data["cover_image"] = result.get("local_path")
            self.generator.novel_data["cover_generated"] = True
            return True
        else:
            return False

    # ==================== 质量评估方法 ====================

    def _assess_writing_plan_quality(self) -> Optional[Dict]:
        """
        对写作计划进行AI质量评估

        Returns:
            评估结果字典，包含:
            - overall_score: 总体评分
            - readiness: 准备状态 (ready/needs_review/needs_revision)
            - strengths: 优点列表
            - issues: 问题列表
            - summary: 总结
            - token_saved: 节省的token数
        """
        try:
            # 导入评估器
            from src.core.PlanQualityAssessor import PlanQualityAssessor
            from pathlib import Path
            import re

            # 获取API密钥
            api_key = None
            if hasattr(self.generator, 'api_client'):
                api_key = getattr(self.generator.api_client, 'api_key', None)

            # 检查是否有写作计划
            stage_writing_plans = self.generator.novel_data.get("stage_writing_plans", {})
            if not stage_writing_plans:
                print("⚠️ 没有写作计划，跳过评估")
                return None

            # 获取opening_stage的写作计划路径
            novel_title = self.generator.novel_data.get("novel_title", "")
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)

            # 获取用户隔离基础路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                username = getattr(self.generator, '_username', None)
                user_base_dir = get_user_novel_dir(username=username, create=False)
            except Exception:
                user_base_dir = Path("小说项目")

            # 构建写作计划文件路径（用户隔离路径优先）
            plan_path = user_base_dir / safe_title / "plans" / f"{safe_title}_opening_stage_writing_plan.json"
            
            if not plan_path.exists():
                # 兼容旧路径
                plan_path = Path(f"小说项目/{safe_title}/plans/{safe_title}_opening_stage_writing_plan.json")
                if not plan_path.exists():
                    print(f"⚠️ 写作计划文件不存在: {plan_path}")
                    return None

            print(f"📋 评估文件: {plan_path}")

            # 创建评估器
            assessor = PlanQualityAssessor(api_key=api_key)

            # 进行评估（如果配置了API则使用AI深度分析）
            use_ai = api_key is not None
            result = assessor.assess(plan_path, use_deep_analysis=use_ai)

            # 转换为字典格式返回
            return {
                "overall_score": result.overall_score,
                "readiness": result.readiness,
                "strengths": result.strengths,
                "issues": [
                    {
                        "category": i.category,
                        "severity": i.severity.value,
                        "location": i.location,
                        "description": i.description,
                        "suggestion": i.suggestion,
                        "auto_fixable": i.auto_fixable
                    }
                    for i in result.issues
                ],
                "summary": result.summary,
                "token_saved": result.token_saved,
                "plan_file": str(plan_path),
                "assessment_time": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"❌ 写作计划评估失败: {e}")
            import traceback
            traceback.print_exc()
            return None