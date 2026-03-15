"""
阶段生成器 - 负责第一阶段和第二阶段的生成逻辑
从NovelGenerator中拆分出来，提高代码可维护性
"""

import json
import os
import re
import atexit
import signal
import weakref
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from src.utils.logger import get_logger

# 🔑 全局线程池监控（用于强制清理）
_global_executors = weakref.WeakSet()

def _cleanup_all_executors():
    """程序退出时清理所有线程池"""
    import logging
    logger = logging.getLogger("PhaseGenerator.cleanup")
    
    for executor in list(_global_executors):
        try:
            if hasattr(executor, 'shutdown'):
                logger.info(f"🚿 正在关闭线程池...")
                executor.shutdown(wait=False, cancel_futures=True)
                logger.info(f"✅ 线程池已关闭")
        except Exception as e:
            logger.warning(f"⚠️ 关闭线程池时出错: {e}")

# 注册程序退出时的清理函数
atexit.register(_cleanup_all_executors)

# 处理信号中断
if hasattr(signal, 'SIGINT'):
    def _signal_handler(signum, frame):
        import logging
        logger = logging.getLogger("PhaseGenerator.signal")
        logger.info(f"🔴 收到信号 {signum}，正在清理线程池...")
        _cleanup_all_executors()
        # 重新提出信号，让程序正常退出
        signal.default_int_handler(signum, frame)
    
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


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
    
    def _check_stop_requested(self, context: str = "") -> None:
        """🔥 检查是否被请求停止生成
        
        通过调用 generator 的停止检查回调来检测用户是否请求停止
        
        Args:
            context: 当前上下文描述，用于日志
            
        Raises:
            InterruptedError: 当停止标志被设置时
        """
        try:
            if hasattr(self.generator, '_stop_check_callback'):
                self.generator._stop_check_callback()
        except InterruptedError:
            self.logger.info(f"🛑 PhaseGenerator 生成被用户停止{' - ' + context if context else ''}")
            raise
        except Exception as e:
            self.logger.debug(f"停止检查失败: {e}")
    
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
                
                # 🔥 新增：保存检查点（关键步骤完成后）
                try:
                    # 只在主要步骤完成时保存检查点（步骤名称在 step_progress_map 中）
                    step_progress_map_keys = ['initialization', 'writing_style', 'market_analysis',
                                              'worldview', 'faction_system', 'character_design',
                                              'emotional_growth_planning', 'stage_plan', 'detailed_stage_plans',
                                              'supplementary_characters', 'expectation_mapping', 'system_init', 
                                              'saving', 'quality_assessment']
                    if stage_name in step_progress_map_keys:
                        # 获取小说标题
                        title = None
                        if hasattr(self.generator, 'creative_title'):
                            title = self.generator.creative_title
                        elif hasattr(self.generator, 'novel_data') and 'title' in self.generator.novel_data:
                            title = self.generator.novel_data['title']
                        
                        # 获取用户名（用于用户隔离路径）
                        username = None
                        if hasattr(self.generator, '_username'):
                            username = self.generator._username
                        elif hasattr(self.generator, 'novel_data') and 'username' in self.generator.novel_data:
                            username = self.generator.novel_data['username']
                        
                        # 🔥 修复：只在14个主要步骤更新检查点，避免子线程频繁写入导致文件锁冲突
                        MAIN_STEPS = [
                            'creative_refinement', 'fanfiction_detection', 'multiple_plans', 'plan_selection',
                            'foundation_planning', 'worldview_with_factions', 'character_design',
                            'emotional_growth_planning', 'stage_plan', 'detailed_stage_plans',
                            'supplementary_characters', 'expectation_mapping', 'system_init', 
                            'saving', 'quality_assessment'
                        ]
                        
                        if title and stage_name in MAIN_STEPS:
                            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
                            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
                            
                            # 判断步骤状态：completed 或 in_progress
                            step_status_str = 'in_progress'
                            if step_status and isinstance(step_status, dict):
                                # 如果当前步骤在 step_status 中标记为 completed，则使用 completed
                                if step_status.get(stage_name) in ['completed', 'done']:
                                    step_status_str = 'completed'
                            
                            try:
                                # 🔥 修复：保存完整的 novel_data 数据以便恢复
                                # 根据当前步骤，确定需要保存的关键数据
                                checkpoint_data = {
                                    'progress': progress,
                                    'message': message,
                                    'points_consumed': points_consumed,
                                    'step_status': step_status,
                                    # 保存完整的 novel_data 以便恢复时加载
                                    'novel_data_snapshot': self._prepare_data_for_checkpoint(self.generator.novel_data)
                                }
                                
                                checkpoint_mgr.create_checkpoint(
                                    phase='phase_one',
                                    step=stage_name,
                                    data=checkpoint_data,
                                    step_status=step_status_str
                                )
                                print(f"✅ 检查点已保存: {stage_name} (包含完整数据)")
                            except Exception as cp_e:
                                print(f"⚠️ 检查点保存失败（可能文件被占用）: {cp_e}")
                except Exception as checkpoint_error:
                    print(f"⚠️ 保存检查点失败: {checkpoint_error}")
                
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
            
            # 🔥 基于 13 个标准步骤的进度映射
            step_progress_map = {
                'initialization': 0,
                'writing_style': 8,
                'market_analysis': 15,
                'worldview': 23,
                'faction_system': 31,
                'character_design': 38,
                'emotional_growth_planning': 46,
                'stage_plan': 62,
                'detailed_stage_plans': 69,
                'supplementary_characters': 74,  # 新增：全书补充角色生成
                'expectation_mapping': 77,
                'system_init': 85,
                'saving': 92,
                'quality_assessment': 100
            }
            
            # 第一阶段：基础规划 (writing_style + market_analysis)
            update_step_status('writing_style', 'active', step_progress_map['writing_style'])
            if not self._generate_foundation_planning(update_step_status=update_step_status):
                error_msg = "基础规划生成失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('market_analysis', step_progress_map['market_analysis'], "基础规划完成",
                                     step_status={'writing_style': 'completed', 'market_analysis': 'completed'})
            
            # 第二阶段：世界观与角色设计 (worldview + faction_system + character_design)
            self.logger.info("🔥 即将进入第二阶段: _generate_worldview_and_characters")
            print("\n🔥 即将进入第二阶段: _generate_worldview_and_characters")
            update_step_status('worldview', 'active', step_progress_map['worldview'])
            result = self._generate_worldview_and_characters(update_step_status=update_step_status)
            self.logger.info(f"🔥 _generate_worldview_and_characters 返回: {result}")
            print(f"🔥 _generate_worldview_and_characters 返回: {result}")
            if not result:
                error_msg = "世界观与角色设计失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            self.logger.info("🔥 第二阶段完成，继续执行...")
            print("🔥 第二阶段完成，继续执行...")
            update_progress_callback('character_design', step_progress_map['character_design'], "角色设计完成",
                                     step_status={'worldview': 'completed', 'faction_system': 'completed', 
                                                 'character_design': 'completed'})
            
            # 第三阶段：全书规划 (emotional_growth_planning + stage_plan + detailed_stage_plans + expectation_mapping + system_init)
            self.logger.info("🔥 即将进入第三阶段: _generate_overall_planning")
            print("\n🔥 即将进入第三阶段: _generate_overall_planning")
            update_step_status('emotional_growth_planning', 'active', step_progress_map['emotional_growth_planning'])
            self.logger.info("✅ 已更新 emotional_growth_planning 状态为 active")
            print("✅ 已更新 emotional_growth_planning 状态为 active")
            if not self._generate_overall_planning(update_step_status=update_step_status):
                error_msg = "全书规划制定失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('system_init', step_progress_map['system_init'], "全书大纲制定完成",
                                     step_status={'emotional_growth_planning': 'completed',
                                                 'stage_plan': 'completed', 'detailed_stage_plans': 'completed',
                                                 'expectation_mapping': 'completed', 'system_init': 'completed'})
            
            # 第四阶段：保存结果
            update_step_status('saving', 'active', step_progress_map['saving'])
            if not self._prepare_content_generation(update_step_status=update_step_status):
                error_msg = "保存设定结果失败"
                print(f"❌ {error_msg}")
                notify_failure(error_msg)
                return False
            update_progress_callback('saving', step_progress_map['saving'], "设定结果保存完成",
                                     step_status={'saving': 'completed'})
            
            # 保存第一阶段结果
            update_progress_callback('saving', step_progress_map['saving'], "正在保存第一阶段结果...")
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

            # 🔥 新增：自动进行质量评估 (100%)
            update_step_status('quality_assessment', 'active', 100)
            update_progress_callback('quality_assessment', 100, "正在进行AI质量评估...",
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
            
            # 🔥 修复：构建最终步骤状态，添加 'completed' 标记
            final_step_status = {
                'writing_style': 'completed',
                'market_analysis': 'completed',
                'worldview': 'completed',
                'faction_system': 'completed',
                'character_design': 'completed',
                'emotional_growth_planning': 'completed',  # 合并：情绪蓝图 + 成长规划
                'stage_plan': 'completed',
                'detailed_stage_plans': 'completed',
                'supplementary_characters': 'completed',  # 🆕 全书补充角色生成
                'expectation_mapping': 'completed',
                'system_init': 'completed',
                'saving': 'completed',
                'quality_assessment': 'completed',
                'completed': 'completed'  # 🔥 添加完成标记，前端识别
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
        """
        生成基础规划 - 🔥 优化版本：合并写作风格和市场分析
        
        Args:
            update_step_status: 可选的步骤状态更新回调函数，用于实时更新前端进度
        """
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划（合并优化版）")
        print("="*60)
        
        # 🔥 优化：合并生成写作风格指南和市场分析
        print("📝 步骤6-7: 合并生成写作风格指南和市场分析...")
        self.generator.novel_data["current_progress"]["stage"] = "基础规划"
        if update_step_status:
            update_step_status('writing_style', 'active', 10)
        
        try:
            # 获取必要数据
            category = self.generator.novel_data.get("category", "未分类")
            creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
            selected_plan = self.generator.novel_data.get("selected_plan", {})
            novel_title = self.generator.novel_data.get("novel_title", "")
            novel_synopsis = self.generator.novel_data.get("novel_synopsis", "")
            
            # 调用合并生成方法
            foundation_result = self.generator.content_generator.generate_foundation_planning(
                creative_seed=creative_seed,
                category=category,
                selected_plan=selected_plan,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis
            )
            
            if foundation_result:
                # 提取写作风格指南
                writing_style = foundation_result.get('writing_style_guide', {})
                if writing_style:
                    self.generator.novel_data["writing_style_guide"] = writing_style
                    print("✅ 写作风格指南生成成功（合并）")
                    self.generator._save_writing_style_to_file(writing_style)
                else:
                    print("⚠️ 写作风格指南部分缺失，使用默认风格")
                    self.generator.novel_data["writing_style_guide"] = self._get_default_writing_style(category)
                
                # 提取市场分析
                market_analysis = foundation_result.get('market_analysis', {})
                if market_analysis:
                    self.generator.novel_data["market_analysis"] = market_analysis
                    print("✅ 市场分析生成成功（合并）")
                    # 保存到材料管理器
                    self.generator._save_material_to_manager("市场分析", market_analysis, creative_seed=creative_seed)
                else:
                    print("❌ 市场分析部分缺失")
                    return False
                
                # 两个步骤都完成
                if update_step_status:
                    update_step_status('writing_style', 'completed', 15)
                    update_step_status('market_analysis', 'completed', 25)
                
                print("✅ 基础规划合并生成完成")
                return True
            else:
                print("❌ 基础规划合并生成失败，尝试降级为分步生成...")
                # 🔥 降级方案：分别调用旧方法
                return self._generate_foundation_planning_fallback(update_step_status)
                
        except Exception as e:
            print(f"⚠️ 合并生成基础规划时出错: {e}")
            print("🔄 降级为分步生成...")
            return self._generate_foundation_planning_fallback(update_step_status)
    
    def _generate_foundation_planning_fallback(self, update_step_status=None) -> bool:
        """基础规划生成的降级方案（分步调用）"""
        print("📝 使用降级方案：分步生成写作风格和市场分析...")
        
        # 生成写作风格指南
        if update_step_status:
            update_step_status('writing_style', 'active', 10)
        
        if not self._generate_writing_style_guide():
            print("⚠️ 写作风格指南生成失败，使用默认风格")
        
        if update_step_status:
            update_step_status('writing_style', 'completed', 15)
        
        # 市场分析
        if update_step_status:
            update_step_status('market_analysis', 'active', 20)
        
        if not self._generate_market_analysis():
            return False
        
        if update_step_status:
            update_step_status('market_analysis', 'completed', 25)
        
        return True
    
    def _generate_worldview_and_characters(self, update_step_status=None) -> bool:
        """
        生成世界观、势力和角色设计 - 🔥 优化版本：合并世界观和势力系统
        """
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与势力系统设计（合并优化版）")
        print("="*60)
        
        # 🔥 优化：合并生成世界观和势力系统
        print("🌍 步骤8-9: 合并生成世界观与势力系统...")
        self.generator.novel_data["current_progress"]["stage"] = "世界观与势力系统"
        if update_step_status:
            update_step_status('worldview', 'active', 35)
        
        try:
            novel_title = self.generator.novel_data["novel_title"]
            novel_synopsis = self.generator.novel_data["novel_synopsis"]
            selected_plan = self.generator.novel_data["selected_plan"]
            market_analysis = self.generator.novel_data.get("market_analysis", {})
            
            # 调用合并生成方法
            worldview_result = self.generator.content_generator.generate_worldview_with_factions(
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                selected_plan=selected_plan,
                market_analysis=market_analysis
            )
            
            if worldview_result:
                # 提取世界观
                core_worldview = worldview_result.get('core_worldview', {})
                if core_worldview:
                    self.generator.novel_data["core_worldview"] = core_worldview
                    print("✅ 世界观构建完成（合并）")
                else:
                    print("❌ 世界观部分缺失")
                    return False
                
                # 提取势力系统
                faction_system = worldview_result.get('faction_system', {})
                if faction_system:
                    self.generator.novel_data["faction_system"] = faction_system
                    print("✅ 势力/阵营系统构建完成（合并）")
                    # 保存到材料管理器
                    self.generator._save_material_to_manager("势力系统", faction_system, novel_title=novel_title)
                else:
                    print("⚠️ 势力系统部分缺失，将使用默认设定")
                    self.generator.novel_data["faction_system"] = {
                        "factions": [],
                        "main_conflict": "待定",
                        "faction_power_balance": "待定",
                        "recommended_starting_faction": "待定"
                    }
                
                # 两个步骤都完成
                if update_step_status:
                    update_step_status('worldview', 'completed', 40)
                    update_step_status('faction_system', 'completed', 45)
                
                print("✅ 世界观与势力系统合并生成完成")
            else:
                print("❌ 世界观与势力系统合并生成失败，尝试降级为分步生成...")
                return self._generate_worldview_and_characters_fallback(update_step_status)
                
        except Exception as e:
            print(f"⚠️ 合并生成世界观与势力系统时出错: {e}")
            print("🔄 降级为分步生成...")
            return self._generate_worldview_and_characters_fallback(update_step_status)
        
        # 核心角色设计（现在可以基于势力系统） - 步骤10
        print("👤 步骤10: 设计核心角色 (主角/核心盟友/宿敌)")
        self.logger.info("🔥 即将调用 generate_character_design API...")
        print("🔥 即将调用 generate_character_design API...")
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
        self.logger.info("🔥 character_design 即将标记为 completed...")
        print("🔥 character_design 即将标记为 completed...")
        if update_step_status:
            update_step_status('character_design', 'completed', 55)
        self.logger.info("🔥 character_design 已标记 completed，即将返回 True")
        print("🔥 character_design 已标记 completed，即将返回 True")
        
        return True
    
    def _generate_overall_planning(self, update_step_status=None) -> bool:
        """生成全书规划"""
        self.logger.info("🔥 _generate_overall_planning 被调用!")
        print("\n" + "="*60)
        print("🔥 _generate_overall_planning 被调用!")
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 🔥 合并步骤：情绪蓝图 + 成长规划（步骤8-9合并）
        print("🎨📈 步骤8-9: 情绪蓝图与成长规划（合并生成）")
        self.generator.novel_data["current_progress"]["stage"] = "情绪蓝图与成长规划"
        if update_step_status:
            update_step_status('emotional_growth_planning', 'active', 60)
        
        if not self._generate_emotional_and_growth_plan(update_step_status):
            print("⚠️ 情绪蓝图与成长规划生成失败，使用基础框架")
            return False
        
        if update_step_status:
            update_step_status('emotional_growth_planning', 'completed', 70)
        
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
        
        if not self._generate_stage_writing_plans(update_step_status):
            print("❌ 生成阶段详细写作计划失败")
            return False
        
        if update_step_status:
            update_step_status('detailed_stage_plans', 'completed', 72)
        
        # 🆕 步骤14.5: 全书补充角色生成（新增独立步骤）
        print("👥 步骤14.5: 全书补充角色生成")
        self.generator.novel_data["current_progress"]["stage"] = "全书补充角色生成"
        if update_step_status:
            update_step_status('supplementary_characters', 'active', 74)
        
        try:
            creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
            overall_stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
            stage_plan_dict = overall_stage_plans.get("overall_stage_plan", {}) if overall_stage_plans else {}
            
            self.generator.stage_plan_manager._generate_all_supplementary_characters_batch(
                creative_seed=creative_seed,
                novel_title=self.generator.novel_data.get("novel_title", ""),
                novel_synopsis=self.generator.novel_data.get("novel_synopsis", ""),
                overall_stage_plan=stage_plan_dict,
                all_stages_writing_plans=self.generator.novel_data.get("stage_writing_plans", {})
            )
            print("✅ 全书补充角色生成完成")
        except Exception as e:
            print(f"⚠️ 全书补充角色生成失败: {e}，继续后续流程")
        
        if update_step_status:
            update_step_status('supplementary_characters', 'completed', 76)
        
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
    
    def _generate_worldview_and_characters_fallback(self, update_step_status=None) -> bool:
        """世界观与角色设计的降级方案（分步调用）"""
        print("🌍 使用降级方案：分步生成世界观和势力系统...")
        
        # 世界观构建
        if update_step_status:
            update_step_status('worldview', 'active', 35)
        
        if not self._generate_worldview():
            return False
        
        if update_step_status:
            update_step_status('worldview', 'completed', 40)
        
        # 势力/阵营系统构建
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
            self.generator._save_material_to_manager("势力系统", faction_system, novel_title=self.generator.novel_data["novel_title"])
        else:
            print("⚠️ 势力/阵营系统生成失败，将使用默认设定")
            self.generator.novel_data["faction_system"] = {
                "factions": [],
                "main_conflict": "待定",
                "faction_power_balance": "待定",
                "recommended_starting_faction": "待定"
            }
        
        if update_step_status:
            update_step_status('faction_system', 'completed', 45)
        
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
    
    def _generate_emotional_and_growth_plan(self, update_step_status=None) -> bool:
        """
        🔥 真正合并生成：情绪蓝图 + 成长规划（步骤8-9合并）
        
        真正合并为一个API调用，大幅减少API调用次数和时间
        """
        import logging
        logger = logging.getLogger("PhaseGenerator")
        
        self.logger.info("🔥🔥🔥 _generate_emotional_and_growth_plan 函数入口!")
        print("\n🔥🔥🔥 _generate_emotional_and_growth_plan 函数入口!")
        self.logger.info("="*60)
        self.logger.info("🎨📈 步骤8-9: 情绪蓝图与成长规划（真正合并为一个API调用）")
        self.logger.info("="*60)
        
        print("\n" + "="*60)
        print("🎨📈 步骤8-9: 情绪蓝图与成长规划（真正合并为一个API调用）")
        print("="*60)
        
        # 获取必要数据
        novel_title = self.generator.novel_data["novel_title"]
        novel_synopsis = self.generator.novel_data["novel_synopsis"]
        creative_seed = self.generator.novel_data.get("creative_seed") or self.generator.novel_data.get("selected_plan", {})
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        # 更新进度
        if update_step_status:
            update_step_status('emotional_growth_planning', 'active', 60)
        
        # 🔥 构建合并的提示词
        self.logger.info("🔨 构建合并提示词...")
        print("  🔨 构建合并提示词...")
        prompt = self._build_combined_emotional_and_growth_prompt(
            novel_title, novel_synopsis, creative_seed, total_chapters
        )
        self.logger.info(f"✅ 提示词构建完成，长度: {len(prompt)}")
        print(f"  ✅ 提示词构建完成，长度: {len(prompt)}")
        
        # 🔥 真正的单次API调用
        self.logger.info("🚀 调用AI生成合并的情绪蓝图与成长规划...")
        print("  🚀 调用AI生成合并的情绪蓝图与成长规划...")
        print(f"  ⏱️ 开始时间: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")
        
        # 🔥 检查API客户端
        if not hasattr(self.generator, 'api_client') or not self.generator.api_client:
            self.logger.error("❌ API客户端不存在")
            print("  ❌ API客户端不存在")
            return False
        self.logger.info(f"🔍 API客户端: {type(self.generator.api_client)}")
        print(f"  🔍 API客户端: {type(self.generator.api_client)}")
        
        # 🔥 检查提示词
        print(f"  🔍 提示词长度: {len(prompt) if prompt else 0}")
        
        result = None
        try:
            # 🔥 在API调用前检查停止标志
            self._check_stop_requested("情绪蓝图与成长规划生成前")
            print("  🚀 正在调用 generate_content_with_retry...")
            result = self.generator.api_client.generate_content_with_retry(
                "emotional_blueprint_generation",  # 使用正确的content_type
                prompt,
                purpose="合并生成情绪蓝图与成长规划"
            )
            # 🔥 API调用后也检查停止标志
            self._check_stop_requested("情绪蓝图与成长规划生成后")
            print(f"  ✅ generate_content_with_retry 返回了结果: {result is not None}")
        except Exception as e:
            print(f"  ❌ API调用异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print(f"  ⏱️ 结束时间: {__import__('datetime').datetime.now().strftime('%H:%M:%S')}")
        
        if not result:
            print("  ❌ 合并生成失败，API返回None")
            return False
        
        # 🔥 调试：打印返回结果类型和内容
        print(f"  🔍 API返回类型: {type(result)}")
        if isinstance(result, dict):
            print(f"  🔍 API返回键: {list(result.keys())}")
        
        # 更新进度
        if update_step_status:
            update_step_status('emotional_growth_planning', 'active', 65)
        
        # 🔥 解析结果并分别存储（处理字符串返回的情况）
        import json
        if isinstance(result, str):
            try:
                result = json.loads(result)
                print("  ✅ JSON字符串解析成功")
            except json.JSONDecodeError as e:
                print(f"  ❌ JSON解析失败: {e}")
                print(f"  ⚠️ 原始内容: {result[:200]}...")
                return False
        
        if not isinstance(result, dict):
            print(f"  ❌ 返回结果不是字典类型: {type(result)}")
            return False
        
        # 解析结果并分别存储
        emotional_blueprint = result.get("emotional_blueprint", {})
        global_growth_plan = result.get("global_growth_plan", {})
        
        # 存储情绪蓝图
        if emotional_blueprint:
            # 🔥 修复：同时存储到 novel_data 和 _ctx
            self.generator.novel_data["emotional_blueprint"] = emotional_blueprint
            if hasattr(self.generator, '_ctx'):
                self.generator._ctx["emotional_blueprint"] = emotional_blueprint
            print("  ✅ 情绪蓝图提取成功")
            # 保存到文件
            try:
                safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
                import json
                # 🔥 修复：优先从 generator 获取用户名，如果没有则尝试从 Flask 上下文获取
                username = getattr(self.generator, '_username', None)
                if not username:
                    try:
                        from flask import g
                        username = getattr(g, 'username', None)
                    except Exception:
                        pass
                if not username:
                    try:
                        from flask import session
                        username = session.get('username')
                    except Exception:
                        pass
                if not username:
                    username = 'anonymous'
                blueprint_path = f"小说项目/{username}/{novel_title}/{safe_title}_情绪蓝图.json"
                os.makedirs(os.path.dirname(blueprint_path), exist_ok=True)
                with open(blueprint_path, 'w', encoding='utf-8') as f:
                    json.dump(emotional_blueprint, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"  ⚠️ 保存情绪蓝图失败: {e}")
        
        # 存储成长规划
        if global_growth_plan:
            # 🔥 关键修复：同时存储到 novel_data 和 _ctx
            self.generator.novel_data["global_growth_plan"] = global_growth_plan
            if hasattr(self.generator, '_ctx'):
                self.generator._ctx["global_growth_plan"] = global_growth_plan
            # 同时设置到GlobalGrowthPlanner
            if hasattr(self.generator, 'global_growth_planner'):
                self.generator.global_growth_planner.global_growth_plan = global_growth_plan
            print("  ✅ 成长规划提取成功")
        
        # 只要其中一个成功就算成功
        if emotional_blueprint or global_growth_plan:
            print("✅ 情绪蓝图与成长规划合并生成完成（单次API调用）")
            if update_step_status:
                update_step_status('emotional_growth_planning', 'completed', 70)
            return True
        else:
            print("❌ 情绪蓝图与成长规划都生成失败")
            return False
    
    def _build_combined_emotional_and_growth_prompt(self, novel_title: str, novel_synopsis: str, creative_seed: dict, total_chapters: int) -> str:
        """构建合并的提示词：同时生成情绪蓝图和成长规划"""
        import logging
        logger = logging.getLogger("PhaseGenerator")
        
        self.logger.info(f"🔍 构建提示词... novel_title={novel_title}, creative_seed类型={type(creative_seed)}")
        print(f"  🔍 构建提示词...")
        print(f"  🔍 novel_title: {novel_title}")
        print(f"  🔍 creative_seed类型: {type(creative_seed)}")
        
        # 提取创意种子信息
        try:
            if isinstance(creative_seed, dict):
                original_selling_points = creative_seed.get("coreSellingPoints", "未提供核心卖点。")
                storyline = creative_seed.get("completeStoryline", {})
            else:
                original_selling_points = str(creative_seed)
                storyline = {}
                print(f"  ⚠️ creative_seed不是字典，转为字符串: {original_selling_points[:100]}...")
        except Exception as e:
            print(f"  ⚠️ 提取创意种子信息失败: {e}")
            original_selling_points = "未提供核心卖点。"
            storyline = {}
        
        return f"""# 角色：顶级网文策划专家

你的任务是为小说同时设计【情绪蓝图】和【成长规划】两部分内容。这是一次性输出两个相互关联的规划。

# 小说核心信息
*   **书名**: {novel_title}
*   **简介**: {novel_synopsis}
*   **核心卖点**: {original_selling_points}
*   **总章节数**: {total_chapters}

# 第一部分：情绪蓝图设计

## 任务
设计全书的情绪发展蓝图，规划读者在不同阶段应体验的核心情绪流。

## 输出要求
1. **核心情感光谱**: 提炼3-5个核心情绪关键词（如：复仇宣泄感、守护温情、兄弟情谊等）
2. **四段式情绪弧线**: 
   - 起(开局15%): 从什么情绪到什么情绪
   - 承(发展35%): 情绪如何深化和发展
   - 转(高潮30%): 情绪如何推向顶点
   - 合(结局20%): 情绪如何圆满收束
3. **关键情绪转折点**: 2-3个重要的情绪转折节点

# 第二部分：成长规划

## 任务
基于"起承转合"四段式结构，规划人物成长、势力发展和能力体系演进。

## 输出要求
1. **阶段框架**: 四个阶段的章节范围和核心目标
2. **人物成长弧线**: 主角在四阶段的关键成长节点
3. **势力发展**: 各方势力的演变规划
4. **能力体系演进**: 能力/等级的升级节奏

# 输出格式
你必须返回一个严格的JSON对象，包含两个顶层key：

```json
{{
    "emotional_blueprint": {{
        "overall_emotional_tone": "string (全书情感基调概括)",
        "emotional_spectrum": ["string", "string", "string"],
        "stage_emotional_arcs": {{
            "opening_stage": {{
                "description": "string",
                "start_emotion": "string", 
                "end_emotion": "string"
            }},
            "development_stage": {{...}},
            "climax_stage": {{...}},
            "ending_stage": {{...}}
        }},
        "key_emotional_turning_points": [
            {{"approx_chapter_percent": number, "description": "string"}}
        ]
    }},
    "global_growth_plan": {{
        "growth_stages": [
            {{"stage_name": "起(开局)", "chapter_range": "string", "core_objective": "string"}},
            {{"stage_name": "承(发展)", "chapter_range": "string", "core_objective": "string"}},
            {{"stage_name": "转(高潮)", "chapter_range": "string", "core_objective": "string"}},
            {{"stage_name": "合(结局)", "chapter_range": "string", "core_objective": "string"}}
        ],
        "ability_tree": {{
            "protagonist_arc": "string (主角成长主线)",
            "key_milestones": ["string", "string"]
        }},
        "realm_system": {{
            "name": "string (境界体系名称)",
            "overview": "string (体系概述)",
            "realms": [
                {{"name": "string (境界名称)", "description": "string (境界描述)"}}
            ]
        }},
        "resource_system": {{
            "early_resources": "string (初期资源获取方式)",
            "mid_resources": "string (中期资源获取方式)",
            "late_resources": "string (后期资源获取方式)"
        }}
    }}
}}
```

注意：确保两个部分相互协调，情绪高潮与成长高潮要同步。"""
    
    def _generate_stage_writing_plans(self, update_step_status=None) -> bool:
        """
        生成各阶段详细写作计划 - 🔥 优化版本：并行生成
        使用多线程并行生成4个阶段的详细计划，大幅缩短总时间
        """
        print("=== 步骤6: 生成各阶段详细写作计划（并行模式）===")
        
        overall_stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            stage_plan_container = overall_stage_plans
            stage_plan_dict = stage_plan_container["overall_stage_plan"]
            
            self.generator.novel_data["stage_writing_plans"] = {}
            
            # 🔥 优化：准备并行生成的任务列表
            import re
            stage_tasks = []
            
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                
                stage_tasks.append({
                    'stage_name': stage_name,
                    'stage_range': stage_range,
                    'creative_seed': self.generator.novel_data["creative_seed"],
                    'novel_title': self.generator.novel_data["novel_title"],
                    'novel_synopsis': self.generator.novel_data["novel_synopsis"],
                    'overall_stage_plan': stage_plan_dict
                })
            
            print(f"  🚀 启动并行生成：共 {len(stage_tasks)} 个阶段")
            print(f"  ⏱️  预计节省 {len(stage_tasks)-1} 倍时间")
            
            # 🔥 优化：先批量生成所有阶段的情绪计划（单次API调用）
            print("  💖 批量生成所有阶段的情绪计划...")
            emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
            stages_info = [{'stage_name': t['stage_name'], 'stage_range': t['stage_range']} for t in stage_tasks]
            all_stages_emotional_plans = self.generator.emotional_plan_manager.generate_all_stages_emotional_plan(
                stages_info, emotional_blueprint
            )
            print(f"  ✅ 成功生成 {len(all_stages_emotional_plans)} 个阶段的情绪计划")
            
            # 🚀 批量生成所有阶段的主龙骨（将 4 次 API 调用合并为 1 次）
            print("  🚀 批量生成所有阶段的主龙骨...")
            stages_config = []
            for task in stage_tasks:
                stage_name = task['stage_name']
                stage_range = task['stage_range']
                # 计算章节数量
                numbers = stage_range.split('-')
                stage_length = max(1, int(numbers[1]) - int(numbers[0]) + 1) if len(numbers) >= 2 else 3
                
                # 计算事件密度
                density = self.generator.stage_plan_manager.event_manager.calculate_optimal_event_density_by_stage(
                    stage_name, stage_length
                )
                
                stages_config.append({
                    'stage_name': stage_name,
                    'stage_range': stage_range,
                    'density_requirements': density,
                    'stage_emotional_plan': all_stages_emotional_plans.get(stage_name)
                })
            
            all_stages_skeletons = self.generator.stage_plan_manager.major_event_generator.generate_all_stages_skeletons_batch(
                stages_config=stages_config,
                creative_seed=self.generator.novel_data.get("creative_seed", {}),
                global_novel_data=self.generator.novel_data,
                overall_stage_plan=stage_plan_dict,
                novel_title=self.generator.novel_data.get("novel_title", "")
            )
            
            if all_stages_skeletons:
                total_events = sum(len(events) for events in all_stages_skeletons.values())
                print(f"  ✅ 批量生成主龙骨成功: {len(all_stages_skeletons)} 个阶段, {total_events} 个重大事件")
            else:
                print("  ⚠️ 批量生成主龙骨失败，将使用逐个生成模式")
                all_stages_skeletons = {}
            
            # 🔥 优化：使用线程池分两批并行生成（2+2）
            from concurrent.futures import as_completed, TimeoutError
            from src.utils.thread_pool_manager import ManagedThreadPool
            import threading
            import time
            
            def generate_single_stage(task):
                """生成单个阶段的包装函数（带详细日志）"""
                stage_name = task['stage_name']
                thread_id = threading.current_thread().name
                task_start_time = time.time()
                
                # 获取预生成的情绪计划和主龙骨
                pre_generated_emotional_plan = all_stages_emotional_plans.get(stage_name)
                pre_generated_skeletons = all_stages_skeletons.get(stage_name) if all_stages_skeletons else None
                
                print(f"\n  ┌─ 🔥 子线程启动 [{stage_name}] ──────────────────────")
                print(f"  │ 线程ID: {thread_id}")
                print(f"  │ 阶段范围: {task['stage_range']}")
                print(f"  │ 预生成主龙骨: {len(pre_generated_skeletons) if pre_generated_skeletons else 0} 个事件")
                print(f"  └─ 开始执行...")
                
                try:
                    # 🔥 跳过期待感映射生成（将在所有阶段完成后统一生成）
                    stage_plan = self.generator.stage_plan_manager.generate_stage_writing_plan(
                        stage_name=stage_name,
                        stage_range=task['stage_range'],
                        creative_seed=task['creative_seed'],
                        novel_title=task['novel_title'],
                        novel_synopsis=task['novel_synopsis'],
                        overall_stage_plan=task['overall_stage_plan'],
                        stage_emotional_plan=pre_generated_emotional_plan,
                        pre_generated_skeletons=pre_generated_skeletons,
                        skip_expectation_mapping=True
                    )
                    
                    duration = time.time() - task_start_time
                    
                    if stage_plan:
                        print(f"\n  ┌─ ✅ 子线程完成 [{stage_name}] ──────────────────────")
                        print(f"  │ 线程ID: {thread_id}")
                        print(f"  │ 总耗时: {duration:.1f}s")
                        if '_generation_metrics' in stage_plan:
                            metrics = stage_plan['_generation_metrics']
                            print(f"  │ API调用耗时: {metrics.get('duration_seconds', 0):.1f}s")
                        print(f"  └─ 成功返回")
                        return stage_name, stage_plan
                    else:
                        print(f"\n  ┌─ ❌ 子线程失败 [{stage_name}] ──────────────────────")
                        print(f"  │ 线程ID: {thread_id}")
                        print(f"  │ 耗时: {duration:.1f}s")
                        print(f"  │ 原因: 返回空结果")
                        print(f"  └─ 失败返回")
                        return stage_name, None
                        
                except Exception as e:
                    duration = time.time() - task_start_time
                    print(f"\n  ┌─ 💥 子线程异常 [{stage_name}] ──────────────────────")
                    print(f"  │ 线程ID: {thread_id}")
                    print(f"  │ 耗时: {duration:.1f}s")
                    print(f"  │ 异常: {str(e)[:100]}")
                    print(f"  └─ 异常返回")
                    return stage_name, None
            
            def run_batch(batch_tasks, batch_name, progress_offset):
                """执行一批任务（2个）"""
                if not batch_tasks:
                    return {}
                    
                stage_names = [t['stage_name'] for t in batch_tasks]
                print(f"\n{'='*60}")
                print(f"🔥 {batch_name}: {', '.join(stage_names)}")
                print(f"   启动 {len(batch_tasks)} 个子线程并行执行...")
                print(f"{'='*60}")
                
                batch_start = time.time()
                batch_results = {}
                completed_in_batch = 0
                
                with ManagedThreadPool(
                        max_workers=2,  # 每批2个线程
                        thread_name_prefix=f"StagePlan_{batch_name}",
                        timeout=300,
                        task_timeout=180
                    ) as executor:
                    # 提交本批任务
                    future_to_stage = {
                        executor.submit(generate_single_stage, task): task['stage_name'] 
                        for task in batch_tasks
                    }
                    
                    print(f"\n📤 [主线程] 已提交 {len(future_to_stage)} 个任务到线程池")
                    print(f"   等待子线程完成 (超时: 180s)...\n")
                    
                    # 收集结果
                    for future in as_completed(future_to_stage):
                        stage_name = future_to_stage[future]
                        try:
                            result_stage_name, stage_plan = future.result(timeout=180)
                            completed_in_batch += 1
                            
                            if stage_plan:
                                self.generator.novel_data["stage_writing_plans"][stage_name] = stage_plan
                                batch_results[stage_name] = stage_plan
                                print(f"\n📥 [主线程] [{completed_in_batch}/{len(batch_tasks)}] 成功: [{stage_name}]")
                            else:
                                print(f"\n⚠️  [主线程] [{completed_in_batch}/{len(batch_tasks)}] 失败: [{stage_name}] 返回空")
                            
                            # 更新进度
                            if update_step_status:
                                total_completed = len(self.generator.novel_data["stage_writing_plans"])
                                progress = 76 + int((total_completed / len(stage_tasks)) * 2)
                                update_step_status('detailed_stage_plans', 'active', progress)
                                
                        except Exception as e:
                            completed_in_batch += 1
                            print(f"\n💥 [主线程] [{completed_in_batch}/{len(batch_tasks)}] 异常: [{stage_name}] {str(e)[:80]}")
                            continue
                
                batch_duration = time.time() - batch_start
                print(f"\n{'='*60}")
                print(f"✅ {batch_name} 完成!")
                print(f"   成功: {len(batch_results)}/{len(batch_tasks)} 个阶段")
                print(f"   耗时: {batch_duration:.1f}s")
                print(f"{'='*60}")
                return batch_results
            
            # 🔥 优化：双队列流水线模式（队列内顺序，队列间并行）
            # 队列1: opening -> development (顺序)
            # 队列2: climax -> ending (顺序)
            # 两个队列并行执行，最大化CPU利用率
            parallel_start_time = time.time()
            stage_timings = {}
            
            from threading import Event, Lock, Semaphore
            
            # 定义队列完成事件
            queue1_ready = Event()  # 队列1可以开始下一个
            queue2_ready = Event()  # 队列2可以开始下一个
            
            # 存储结果
            results_lock = Lock()
            completed_stages = set()
            
            def run_queue1_tasks(tasks):
                """执行队列1：opening -> development (顺序)"""
                results = {}
                for task in tasks:
                    stage_name = task['stage_name']
                    print(f"🚀 [队列1] 开始: {stage_name}")
                    
                    result = generate_single_stage(task)
                    
                    if result and result[1]:
                        with results_lock:
                            self.generator.novel_data["stage_writing_plans"][result[0]] = result[1]
                            completed_stages.add(result[0])
                        results[result[0]] = result[1]
                        print(f"✅ [队列1] 完成: {result[0]}")
                        
                        # 更新进度
                        if update_step_status:
                            total_completed = len(completed_stages)
                            progress = 76 + int((total_completed / len(stage_tasks)) * 2)
                            update_step_status('detailed_stage_plans', 'active', progress)
                    else:
                        print(f"❌ [队列1] 失败: {stage_name}")
                
                queue1_ready.set()
                return results
            
            def run_queue2_tasks(tasks):
                """执行队列2：climax -> ending (顺序)"""
                results = {}
                for task in tasks:
                    stage_name = task['stage_name']
                    print(f"🚀 [队列2] 开始: {stage_name}")
                    
                    result = generate_single_stage(task)
                    
                    if result and result[1]:
                        with results_lock:
                            self.generator.novel_data["stage_writing_plans"][result[0]] = result[1]
                            completed_stages.add(result[0])
                        results[result[0]] = result[1]
                        print(f"✅ [队列2] 完成: {result[0]}")
                        
                        # 更新进度
                        if update_step_status:
                            total_completed = len(completed_stages)
                            progress = 76 + int((total_completed / len(stage_tasks)) * 2)
                            update_step_status('detailed_stage_plans', 'active', progress)
                    else:
                        print(f"❌ [队列2] 失败: {stage_name}")
                
                queue2_ready.set()
                return results
            
            # 准备队列任务
            task_map = {t['stage_name']: t for t in stage_tasks}
            
            queue1_tasks = []
            queue2_tasks = []
            
            # 队列1: opening -> development
            if 'opening_stage' in task_map:
                queue1_tasks.append(task_map['opening_stage'])
            if 'development_stage' in task_map:
                queue1_tasks.append(task_map['development_stage'])
            
            # 队列2: climax -> ending
            if 'climax_stage' in task_map:
                queue2_tasks.append(task_map['climax_stage'])
            if 'ending_stage' in task_map:
                queue2_tasks.append(task_map['ending_stage'])
            
            print(f"\n{'='*60}")
            print(f"🔥 双队列流水线执行")
            print(f"   队列1 [起→承]: {[t['stage_name'] for t in queue1_tasks]}")
            print(f"   队列2 [转→合]: {[t['stage_name'] for t in queue2_tasks]}")
            print(f"   说明: 队列内顺序执行，队列间并行")
            print(f"{'='*60}")
            
            # 并行启动两个队列
            queue1_results = {}
            queue2_results = {}
            
            with ManagedThreadPool(
                    max_workers=2,  # 两个队列并行
                    thread_name_prefix=f"StagePlan_Queue",
                    timeout=300,
                    task_timeout=180
                ) as executor:
                
                # 提交两个队列
                future_queue1 = executor.submit(run_queue1_tasks, queue1_tasks) if queue1_tasks else None
                future_queue2 = executor.submit(run_queue2_tasks, queue2_tasks) if queue2_tasks else None
                
                print(f"📤 [主线程] 已启动 2 个队列并行执行\n")
                
                # 等待两个队列完成
                if future_queue1:
                    try:
                        queue1_results = future_queue1.result(timeout=300)
                    except Exception as e:
                        print(f"💥 [队列1] 异常: {str(e)[:80]}")
                
                if future_queue2:
                    try:
                        queue2_results = future_queue2.result(timeout=300)
                    except Exception as e:
                        print(f"💥 [队列2] 异常: {str(e)[:80]}")
                
                print(f"\n✅ [主线程] 所有队列执行完成")
            
            # 收集所有耗时信息
            for stage_name, plan in self.generator.novel_data["stage_writing_plans"].items():
                if isinstance(plan, dict) and '_generation_metrics' in plan:
                    stage_timings[stage_name] = plan['_generation_metrics'].get('duration_seconds', 0)
            
            total_duration = time.time() - parallel_start_time
            
            # 🔥 打印性能分析报告
            print("\n" + "="*70)
            print("📊 并行生成完整报告 (2+2 分批)")
            print("="*70)
            
            if stage_timings:
                print(f"\n【批次执行顺序】")
                print(f"  第一批 [起+承]: opening_stage + development_stage")
                print(f"  第二批 [转+合]: climax_stage + ending_stage")
                
                print(f"\n【阶段总耗时排行】")
                sorted_stages = sorted(stage_timings.items(), key=lambda x: x[1], reverse=True)
                for i, (stage, duration) in enumerate(sorted_stages, 1):
                    bar = "█" * int(duration / 3)
                    print(f"  {i}. {stage:20s} {duration:5.1f}s {bar}")
                
                # 子步骤详情
                print(f"\n【各阶段子步骤详情】")
                for stage_name, plan in sorted(self.generator.novel_data["stage_writing_plans"].items(), 
                                               key=lambda x: x[1].get('_generation_metrics', {}).get('duration_seconds', 0), 
                                               reverse=True):
                    if isinstance(plan, dict) and '_generation_metrics' in plan:
                        metrics = plan['_generation_metrics']
                        print(f"\n  📋 {stage_name} (总耗时: {metrics.get('duration_seconds', 0):.1f}s)")
                        sub_timings = metrics.get('sub_step_timings', {})
                        if sub_timings:
                            for step, duration in sorted(sub_timings.items(), key=lambda x: x[1], reverse=True):
                                bar = "▓" * int(duration / 2)
                                print(f"      {step:20s} {duration:5.1f}s {bar}")
                        print(f"      {'─'*50}")
                
                avg_time = sum(stage_timings.values()) / len(stage_timings)
                max_time = max(stage_timings.values())
                print(f"\n【汇总统计】")
                print(f"  阶段平均耗时: {avg_time:.1f}s")
                print(f"  单阶段最长:   {max_time:.1f}s")
                print(f"  并行总耗时:   {total_duration:.1f}s")
                print(f"  理论加速比:   {(sum(stage_timings.values()) / total_duration):.1f}x")
                
                if max_time > avg_time * 1.5:
                    slowest_stage = sorted_stages[0][0]
                    print(f"\n  ⚠️  提示: {slowest_stage} 耗时明显高于平均，可考虑单独优化")
                    
            print("="*70)
            
            success_count = len(self.generator.novel_data["stage_writing_plans"])
            total_count = len(stage_tasks)
            
            if success_count > 0:
                print(f"\n✅ 阶段详细计划生成完成: {success_count}/{total_count} 个阶段")
                if success_count < total_count:
                    failed_stages = [t['stage_name'] for t in stage_tasks if t['stage_name'] not in self.generator.novel_data["stage_writing_plans"]]
                    print(f"  ⚠️  失败阶段: {', '.join(failed_stages)}")
                
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
        """为所有阶段生成并保存期待感映射 - 使用Enriched版本"""
        try:
            print("\n=== 步骤6.5: 生成期待感映射（Enriched版本） ===")
            
            # 🔥 使用新的Enriched期待感管理器
            from src.managers.ExpectationManager_enriched import (
                EnrichedExpectationManager, 
                generate_enriched_expectation_maps
            )
            
            # 获取API客户端
            api_client = getattr(self.generator, 'api_client', None)
            
            # 批量生成所有阶段的期待感映射
            stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
            
            if not stage_plans:
                print("⚠️ 没有找到阶段计划，跳过期待感映射生成")
                return
            
            print(f"🎯 开始为 {len(stage_plans)} 个阶段生成Enriched期待感映射...")
            
            all_expectation_maps = generate_enriched_expectation_maps(
                stage_plans=stage_plans,
                api_client=api_client
            )
            
            total_tagged = sum(len(m) for m in all_expectation_maps.values())
            print(f"✅ 期待感映射生成完成: {len(all_expectation_maps)} 个阶段, 共 {total_tagged} 个事件")
            
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
        
        # 🔥 获取用户名并确保传递到 novel_data
        username = getattr(self.generator, '_username', None)
        if username:
            self.generator.novel_data['_username'] = username
        
        paths = path_config.ensure_directories(self.generator.novel_data["novel_title"], username=username)
        
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
    
    def _prepare_data_for_checkpoint(self, data: dict) -> dict:
        """
        准备数据以便JSON序列化，处理不可序列化的类型（如 set）
        从 ResumeManager 复制的辅助方法
        """
        serializable_data = {}
        for key, value in data.items():
            if isinstance(value, set):
                # 将 set 转换为 list
                serializable_data[key] = list(value)
            elif isinstance(value, dict):
                # 递归处理字典
                serializable_data[key] = self._prepare_data_for_checkpoint(value)
            elif isinstance(value, (list, tuple)):
                # 处理列表中的元素
                serializable_data[key] = [
                    self._prepare_data_for_checkpoint(item) if isinstance(item, dict) else
                    list(item) if isinstance(item, set) else item
                    for item in value
                ]
            else:
                serializable_data[key] = value
        return serializable_data
    
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
            
            # 🔥 获取用户名用于用户隔离路径
            username = getattr(self.generator, '_username', None)
            
            # 使用统一路径配置系统创建目录结构
            paths = path_config.ensure_directories(self.generator.novel_data["novel_title"], username=username)
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
                data = self.generator.novel_data.get(key)
                # 🔥 修复：更严格的空值检查
                is_valid = False
                if data:
                    if isinstance(data, dict) and len(data) > 0:
                        # 检查是否有实质内容（不只是空结构）
                        has_content = any(
                            v for v in data.values() 
                            if v and (not isinstance(v, (dict, list)) or len(v) > 0)
                        )
                        if has_content:
                            is_valid = True
                        else:
                            print(f"⚠️ {key} 是空字典结构，跳过保存")
                    elif isinstance(data, list) and len(data) > 0:
                        is_valid = True
                    elif isinstance(data, str) and len(data.strip()) > 0:
                        is_valid = True
                
                if is_valid:
                    file_path = f"{products_dir}/{filename}"
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    products_mapping[key] = file_path
                    print(f"✅ {key}已保存: {file_path}")
                else:
                    print(f"⚠️ {key} 数据无效或为空，跳过保存")
            
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
            
            # 🔥 修复：使用标准的项目信息文件名 "项目信息.json"
            main_project_file = user_base_dir / safe_title / "项目信息.json"
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
            username = getattr(self.generator, '_username', None)
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title,
                username=username
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
            username = getattr(self.generator, '_username', None)
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title,
                username=username
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
            username = getattr(self.generator, '_username', None)
            from src.core.QualityAssessor import QualityAssessor
            self.generator.quality_assessor = QualityAssessor(
                api_client=self.generator.api_client,
                novel_title=novel_title,
                username=username
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
        
        # 🔥 确保用户名被传递到 novel_data
        if hasattr(self.generator, '_username') and self.generator._username:
            self.generator.novel_data['_username'] = self.generator._username
        
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
        对写作计划进行AI质量评估（一次性评估所有阶段）

        Returns:
            评估结果字典
        """
        try:
            # 🔥 修复：优先从 _ctx 获取阶段写作计划（实时数据）
            stage_writing_plans = self.generator._ctx.get("stage_writing_plans", {})
            if not stage_writing_plans:
                # 回退到 novel_data
                stage_writing_plans = self.generator.novel_data.get("stage_writing_plans", {})
            
            if not stage_writing_plans:
                print("⚠️ 没有写作计划，跳过评估")
                return None

            # 🔥 调试：打印阶段计划数据
            print(f"📊 开始AI质量评估（共 {len(stage_writing_plans)} 个阶段）...")
            for stage_name, plan in stage_writing_plans.items():
                if isinstance(plan, dict):
                    # 🔥 修复：处理嵌套结构
                    if "stage_writing_plan" in plan:
                        inner_plan = plan["stage_writing_plan"]
                        event_count = len(inner_plan.get("event_system", {}).get("major_events", []))
                    else:
                        event_count = len(plan.get("event_system", {}).get("major_events", []))
                    print(f"  - {stage_name}: {event_count} 个重大事件")

            # 🔥 使用 PlanQualityAssessor 进行 AI 评估
            from src.core.PlanQualityAssessor import PlanQualityAssessor
            
            # 获取 APIClient
            api_client = getattr(self.generator, 'api_client', None)
            if not api_client:
                print("⚠️ 未找到APIClient，使用基于规则的评估")
                return self._assess_writing_plan_quality_rule_based()
            
            # 创建评估器
            assessor = PlanQualityAssessor(api_client=api_client)
            
            # 🔥 合并所有阶段的计划为一个整体计划进行评估
            merged_plan = self._merge_stage_plans_for_assessment(stage_writing_plans)
            
            # 🔥 修复：直接使用内存数据评估，不创建临时文件
            # 获取项目目录
            from src.config.path_config import path_config
            username = getattr(self.generator, '_username', None)
            paths = path_config.get_project_paths(self.generator.novel_data["novel_title"], username=username)
            project_dir = Path(paths['project_root'])
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # 设置报告保存路径为项目目录下的标准文件名
            assessment_path = project_dir / "quality_assessment.json"
            
            # 执行AI评估 - 🔥 修改：直接使用数据对象，不创建临时文件
            result = assessor.assess_data(
                merged_plan, 
                use_deep_analysis=False, 
                skip_compression=True,
                report_save_path=assessment_path  # 指定报告保存路径到项目目录
            )
            
            # 读取保存的评估报告
            try:
                with open(assessment_path, 'r', encoding='utf-8') as f:
                    saved_report = json.load(f)
            except:
                saved_report = {}
            
            # 转换为字典格式（兼容现有UI）
            assessment_dict = {
                "overall_score": getattr(result, 'overall_score', None) or saved_report.get('overall_score', result.score if hasattr(result, 'score') else 0),
                "readiness": getattr(result, 'readiness', None) or saved_report.get('readiness', result.grade if hasattr(result, 'grade') else 'unknown'),
                "strengths": getattr(result, 'strengths', None) or saved_report.get('strengths', []),
                "issues": [
                    {
                        "category": issue.category,
                        "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
                        "location": issue.location,
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "auto_fixable": issue.auto_fixable
                    }
                    for issue in (getattr(result, 'issues', None) or saved_report.get('issues', []))
                ] if (getattr(result, 'issues', None) or saved_report.get('issues')) else [],
                "summary": getattr(result, 'summary', None) or saved_report.get('summary', ''),
                "assessment_time": datetime.now().isoformat(),
                "is_ai_assessment": True
            }
            
            print(f"✅ AI质量评估完成: {assessment_dict['overall_score']}分 ({assessment_dict['readiness']})")
            print(f"📄 评估报告已保存到: {assessment_path}")
            return assessment_dict

        except Exception as e:
            print(f"⚠️ AI质量评估失败: {e}，降级到规则评估")
            import traceback
            traceback.print_exc()
            return self._assess_writing_plan_quality_rule_based()
    
    def _merge_stage_plans_for_assessment(self, stage_writing_plans: Dict) -> Dict:
        """合并所有阶段的计划为一个整体计划用于评估"""
        # 🔥 优先从组装好的写作计划文件读取完整数据
        try:
            # 🔥 修复：使用正确的属性名 _username
            username = getattr(self.generator, '_username', None)
            novel_title = self.generator.novel_data.get("novel_title", "未命名")
            
            # 🔥 调试日志
            print(f"🔍 [质量评估] 尝试读取组装好的写作计划文件...")
            print(f"   - username: {username}")
            print(f"   - novel_title: {novel_title}")
            
            if not username:
                print(f"⚠️ [质量评估] username 为空，跳过文件读取")
                raise ValueError("username is None")
            
            # 构建安全文件名
            safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = "未命名"
            safe_title = safe_title.replace(' ', '_')
            
            # 🔥 优先读取组装好的写作计划文件 (planning 目录)
            planning_file = os.path.join("小说项目", username, safe_title, "planning", f"{safe_title}_写作计划.json")
            
            print(f"   - 组装文件路径: {planning_file}")
            print(f"   - 文件是否存在: {os.path.exists(planning_file)}")
            
            if os.path.exists(planning_file):
                with open(planning_file, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                print(f"✅ [质量评估] 成功读取组装好的写作计划，包含 {len(file_data)} 个阶段")
                
                merged = {
                    "novel_title": novel_title,
                    "total_stages": len(file_data),
                    "stages": []
                }
                
                for stage_name, stage_wrapper in file_data.items():
                    if not isinstance(stage_wrapper, dict):
                        continue
                    
                    # 获取 stage_writing_plan 内的实际数据
                    plan = stage_wrapper.get("stage_writing_plan", {})
                    
                    stage_info = {
                        "stage_name": stage_name,
                        "chapter_range": plan.get("chapter_range", ""),
                        "stage_overview": plan.get("stage_overview", ""),
                        "major_events": []
                    }
                    
                    # 提取重大事件
                    event_system = plan.get("event_system", {})
                    major_events = event_system.get("major_events", [])
                    print(f"   - {stage_name}: 找到 {len(major_events)} 个重大事件")
                    
                    for major in major_events:
                        event_info = {
                            "name": major.get("name", ""),
                            "main_goal": major.get("main_goal", ""),
                            "chapter_range": major.get("chapter_range", ""),
                            "core_conflict": major.get("core_conflict", ""),
                            "emotional_arc": major.get("emotional_arc_summary", ""),
                            "medium_events": []
                        }
                        
                        # 提取中级事件
                        composition = major.get("composition", {})
                        for phase, events in composition.items():
                            if isinstance(events, list):
                                for event in events:
                                    if isinstance(event, dict):
                                        event_info["medium_events"].append({
                                            "name": event.get("name", ""),
                                            "chapter_range": event.get("chapter_range", ""),
                                            "role": event.get("role", "")
                                        })
                        
                        stage_info["major_events"].append(event_info)
                    
                    merged["stages"].append(stage_info)
                
                print(f"✅ [质量评估] 成功解析组装好的写作计划")
                return merged
            else:
                print(f"⚠️ [质量评估] 组装好的写作计划文件不存在，尝试读取分散文件...")
                
            # 降级方案：读取分散的 plans 目录文件
            plans_dir = os.path.join("小说项目", username, safe_title, "plans")
            
            if not os.path.exists(plans_dir):
                print(f"⚠️ [质量评估] plans 目录也不存在，使用内存数据")
                raise FileNotFoundError(f"plans_dir not found: {plans_dir}")
            
            # 列出目录中的文件
            plan_files = [f for f in os.listdir(plans_dir) if f.endswith('_writing_plan.json')]
            print(f"   - 找到 {len(plan_files)} 个分散写作计划文件")
            
            if not plan_files:
                raise FileNotFoundError("No writing plan files found")
            
            merged = {
                "novel_title": novel_title,
                "total_stages": len(plan_files),
                "stages": []
            }
            
            for plan_file in plan_files:
                file_path = os.path.join(plans_dir, plan_file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                    
                    stage_name = plan_file.replace(f"{safe_title}_", "").replace("_writing_plan.json", "")
                    plan = file_data.get("stage_writing_plan", {})
                    
                    stage_info = {
                        "stage_name": stage_name,
                        "chapter_range": plan.get("chapter_range", ""),
                        "stage_overview": plan.get("stage_overview", ""),
                        "major_events": []
                    }
                    
                    event_system = plan.get("event_system", {})
                    major_events = event_system.get("major_events", [])
                    
                    for major in major_events:
                        event_info = {
                            "name": major.get("name", ""),
                            "main_goal": major.get("main_goal", ""),
                            "chapter_range": major.get("chapter_range", ""),
                            "core_conflict": major.get("core_conflict", ""),
                            "emotional_arc": major.get("emotional_arc_summary", ""),
                            "medium_events": []
                        }
                        
                        composition = major.get("composition", {})
                        for phase, events in composition.items():
                            if isinstance(events, list):
                                for event in events:
                                    if isinstance(event, dict):
                                        event_info["medium_events"].append({
                                            "name": event.get("name", ""),
                                            "chapter_range": event.get("chapter_range", ""),
                                            "role": event.get("role", "")
                                        })
                        
                        stage_info["major_events"].append(event_info)
                    
                    merged["stages"].append(stage_info)
                    
                except Exception as e:
                    print(f"     ⚠️ 读取文件失败: {e}")
                    continue
            
            print(f"✅ [质量评估] 成功从分散文件读取 {len(merged['stages'])} 个阶段")
            return merged
            
        except Exception as e:
            print(f"⚠️ 从文件读取写作计划失败: {e}，尝试使用内存数据")
        
        # 降级方案：使用传入的内存数据
        print(f"🔍 [质量评估] 使用内存数据...")
        print(f"   - stage_writing_plans 阶段数: {len(stage_writing_plans)}")
        
        # 🔥 调试：打印第一个阶段的结构
        if stage_writing_plans:
            first_stage = list(stage_writing_plans.values())[0]
            print(f"   - 第一个阶段类型: {type(first_stage)}")
            if isinstance(first_stage, dict):
                print(f"   - 第一个阶段键: {list(first_stage.keys())[:10]}")
                if 'stage_writing_plan' in first_stage:
                    swp = first_stage['stage_writing_plan']
                    print(f"   - stage_writing_plan 类型: {type(swp)}")
                    if isinstance(swp, dict):
                        print(f"   - stage_writing_plan 键: {list(swp.keys())[:10]}")
        
        merged = {
            "novel_title": self.generator.novel_data.get("novel_title", "未命名"),
            "total_stages": len(stage_writing_plans),
            "stages": []
        }
        
        for stage_name, plan in stage_writing_plans.items():
            if not isinstance(plan, dict):
                print(f"   ⚠️ {stage_name} 不是字典，跳过")
                continue
            
            # 🔥 修复：处理嵌套结构 stage_wrapper["stage_writing_plan"]
            if "stage_writing_plan" in plan:
                plan = plan["stage_writing_plan"]
                print(f"   ✓ {stage_name} 解包嵌套结构")
            
            stage_info = {
                "stage_name": stage_name,
                "chapter_range": plan.get("chapter_range", ""),
                "stage_overview": plan.get("stage_overview", ""),
                "major_events": []
            }
            
            # 提取重大事件
            event_system = plan.get("event_system", {})
            major_events = event_system.get("major_events", [])
            print(f"   - {stage_name}: 找到 {len(major_events)} 个重大事件")
            
            for major in major_events:
                event_info = {
                    "name": major.get("name", ""),
                    "main_goal": major.get("main_goal", ""),
                    "chapter_range": major.get("chapter_range", ""),
                    "core_conflict": major.get("core_conflict", ""),
                    "emotional_arc": major.get("emotional_arc_summary", ""),
                    "medium_events": []
                }
                
                # 提取中级事件
                composition = major.get("composition", {})
                for phase, events in composition.items():
                    if isinstance(events, list):
                        for event in events:
                            if isinstance(event, dict):
                                event_info["medium_events"].append({
                                    "name": event.get("name", ""),
                                    "chapter_range": event.get("chapter_range", ""),
                                    "role": event.get("role", "")
                                })
                
                stage_info["major_events"].append(event_info)
            
            merged["stages"].append(stage_info)
        
        return merged
    
    def _assess_writing_plan_quality_rule_based(self) -> Optional[Dict]:
        """基于规则的评估（降级方案）"""
        try:
            stage_writing_plans = self.generator.novel_data.get("stage_writing_plans", {})
            if not stage_writing_plans:
                return None

            # 统计各阶段的关键指标
            total_major_events = 0
            total_medium_events = 0
            
            for plan in stage_writing_plans.values():
                if not isinstance(plan, dict):
                    continue
                # 🔥 修复：处理嵌套结构
                if "stage_writing_plan" in plan:
                    plan = plan["stage_writing_plan"]
                event_system = plan.get("event_system", {})
                major_events = event_system.get("major_events", [])
                total_major_events += len(major_events)
                
                for major in major_events:
                    composition = major.get("composition", {})
                    for events in composition.values():
                        if isinstance(events, list):
                            total_medium_events += len(events)
            
            # 基于统计指标进行评分
            score = 70
            issues = []
            strengths = []
            
            if total_major_events >= 4:
                score += 10
                strengths.append(f"重大事件数量充足（{total_major_events}个）")
            else:
                score -= 5
                issues.append({
                    "category": "structure",
                    "severity": "medium",
                    "location": "overall",
                    "description": f"重大事件数量偏少（{total_major_events}个）",
                    "suggestion": "考虑增加关键剧情节点"
                })
            
            if score >= 80:
                readiness = "ready"
            elif score >= 60:
                readiness = "needs_review"
            else:
                readiness = "needs_revision"
            
            # 构建评估结果
            assessment_dict = {
                "overall_score": min(100, max(0, score)),
                "readiness": readiness,
                "strengths": strengths,
                "issues": issues,
                "summary": f"基于规则的评估：包含{len(stage_writing_plans)}个阶段，{total_major_events}个重大事件。",
                "is_ai_assessment": False,
                "assessment_time": datetime.now().isoformat()
            }
            
            # 🔥 修复：保存评估报告到项目目录
            try:
                from src.config.path_config import path_config
                username = getattr(self.generator, '_username', None)
                paths = path_config.get_project_paths(self.generator.novel_data["novel_title"], username=username)
                project_dir = Path(paths['project_root'])
                project_dir.mkdir(parents=True, exist_ok=True)
                
                assessment_path = project_dir / "quality_assessment.json"
                with open(assessment_path, 'w', encoding='utf-8') as f:
                    json.dump(assessment_dict, f, ensure_ascii=False, indent=2)
                
                print(f"📄 规则评估报告已保存到: {assessment_path}")
            except Exception as save_error:
                print(f"⚠️ 保存规则评估报告失败: {save_error}")
            
            return assessment_dict

        except Exception as e:
            print(f"❌ 规则评估失败: {e}")
            import traceback
            traceback.print_exc()
            return None