"""
恢复模式管理器 - 负责检查点恢复和步骤执行
从NovelGenerator中拆分出来，提高代码可维护性
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from src.utils.logger import get_logger


class ResumeManager:
    """
    恢复模式管理器 - 处理第一阶段生成的恢复和步骤执行
    """
    
    def __init__(self, novel_generator):
        """
        初始化恢复模式管理器
        
        Args:
            novel_generator: NovelGenerator实例，用于访问其属性和方法
        """
        self.generator = novel_generator
        self.logger = get_logger("ResumeManager")
    
    # ==================== 检查点管理方法 ====================
    
    def check_for_resume_checkpoint(self, creative_seed, total_chapters: int) -> Optional[Dict]:
        """
        检查是否有可恢复的检查点
        
        Args:
            creative_seed: 创意种子
            total_chapters: 总章节数
            
        Returns:
            检查点数据字典，如果没有检查点返回None
        """
        try:
            from pathlib import Path
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            
            # 尝试从creative_seed中提取标题
            title = None
            if isinstance(creative_seed, dict):
                # 如果是dict，可能包含novel_title或novelTitle
                title = creative_seed.get('novel_title') or creative_seed.get('novelTitle')
            elif isinstance(creative_seed, str):
                # 如果是字符串，尝试解析JSON
                try:
                    seed_dict = json.loads(creative_seed)
                    title = seed_dict.get('novel_title') or seed_dict.get('novelTitle')
                except:
                    pass
            
            # 如果没有标题，使用已有的novel_data中的标题
            if not title and hasattr(self.generator, 'novel_data') and self.generator.novel_data.get('novel_title'):
                title = self.generator.novel_data['novel_title']
            
            # 如果仍然没有标题，无法查找检查点
            if not title:
                print("ℹ️  无法确定小说标题，从头开始")
                return None
            
            # 获取用户名（用于用户隔离路径）
            username = None
            if hasattr(self.generator, '_username'):
                username = self.generator._username
            elif hasattr(self.generator, 'novel_data') and 'username' in self.generator.novel_data:
                username = self.generator.novel_data['username']
            
            # 创建检查点管理器
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            
            # 检查是否有检查点
            if not checkpoint_mgr.can_resume():
                print("ℹ️  没有找到可恢复的检查点，从头开始")
                return None
            
            # 加载检查点
            checkpoint_data = checkpoint_mgr.load_checkpoint()
            if not checkpoint_data:
                print("⚠️  检查点文件存在但加载失败，从头开始")
                return None
            
            # 验证检查点是否属于第一阶段
            if checkpoint_data.get('phase') != 'phase_one':
                print(f"⚠️  检查点属于 {checkpoint_data.get('phase')}，不是第一阶段，从头开始")
                return None
            
            # 验证检查点状态
            step_status = checkpoint_data.get('step_status', 'unknown')
            current_step = checkpoint_data.get('current_step', '')
            
            if step_status == 'completed' and current_step == 'finalization':
                print("✅ 第一阶段已完成，无需恢复")
                return None
            
            print(f"✅ 找到可恢复的检查点: {checkpoint_data['phase']} - {current_step} (状态: {step_status})")
            
            # 恢复novel_data
            saved_data = checkpoint_data.get('data', {})
            if saved_data:
                # 恢复novel_data中的关键数据
                for key in ['novel_title', 'novel_synopsis', 'category', 'selected_plan',
                           'creative_seed', 'core_worldview', 'character_design',
                           'faction_system', 'market_analysis', 'writing_style_guide',
                           'global_growth_plan', 'overall_stage_plans', 'stage_writing_plans',
                           # 元素时机规划已移除，由期待感系统管理
                           'emotional_blueprint']:
                    if key in saved_data:
                        self.generator.novel_data[key] = saved_data[key]
                
                # 恢复current_progress
                if 'current_progress' in saved_data:
                    self.generator.novel_data.setdefault('current_progress', {}).update(saved_data['current_progress'])
                
                print(f"✅ 已从检查点恢复 {len(saved_data)} 个数据项")
                
                # 验证是否有必要的字段来继续
                # 如果在需要这些字段的步骤，检查它们是否存在
                required_steps = ['worldview_generation', 'character_generation', 'opening_stage_plan',
                                 'development_stage_plan', 'climax_stage_plan', 'ending_stage_plan']
                if current_step in required_steps:
                    missing_fields = []
                    if not self.generator.novel_data.get('novel_title'):
                        missing_fields.append('novel_title')
                    if not self.generator.novel_data.get('novel_synopsis'):
                        missing_fields.append('novel_synopsis')
                    if not self.generator.novel_data.get('selected_plan'):
                        missing_fields.append('selected_plan')
                    
                    if missing_fields:
                        print(f"⚠️  检查点中缺少必要字段: {', '.join(missing_fields)}")
                        print("🗑️  删除不完整的检查点，将从头开始")
                        checkpoint_mgr.delete_checkpoint()
                        return None
            else:
                print("⚠️  检查点数据为空，删除检查点，从头开始")
                checkpoint_mgr.delete_checkpoint()
                return None
            
            return checkpoint_data
            
        except Exception as e:
            print(f"⚠️  检查恢复模式时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _prepare_data_for_checkpoint(self, data: dict) -> dict:
        """准备数据以便JSON序列化，处理不可序列化的类型"""
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

    def create_initial_checkpoint(self, creative_seed, total_chapters: int):
        """创建初始检查点（在方案生成完成后调用），保存创意标题映射"""
        try:
            from pathlib import Path
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            
            # 使用实际的小说标题创建检查点
            title = self.generator.novel_data.get('novel_title') or '未命名'
            
            # 获取用户名（用于用户隔离路径）
            username = None
            if hasattr(self.generator, '_username'):
                username = self.generator._username
            elif 'username' in self.generator.novel_data:
                username = self.generator.novel_data['username']
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            
            # 保存完整的 novel_data - 转换 set 为 list
            initial_data = self._prepare_data_for_checkpoint(self.generator.novel_data)
            
            # 🔥 新增：提取并保存创意标题映射
            creative_title = None
            creative_seed_id = None
            
            if isinstance(creative_seed, dict):
                creative_title = (
                    creative_seed.get("novelTitle") or
                    creative_seed.get("title") or
                    creative_seed.get("coreSetting", "")[:50]
                )
                creative_seed_id = creative_seed.get("id") or creative_seed.get("seedId")
            
            if creative_title:
                initial_data['creative_title'] = creative_title
                print(f"💾 保存创意标题映射: {creative_title} -> {title}")
            
            if creative_seed_id:
                initial_data['creative_seed_id'] = creative_seed_id
                print(f"💾 保存创意ID: {creative_seed_id}")
            
            checkpoint_mgr.create_checkpoint(
                phase='phase_one',
                step='worldview_generation',  # 第一个步骤
                data=initial_data,
                step_status='pending'
            )
            
            print(f"✅ 已创建初始检查点: {title}")
            
        except Exception as e:
            print(f"⚠️ 创建初始检查点失败: {e}")
    
    def resume_phase_one_from_checkpoint(self, checkpoint_data: Dict, creative_seed, total_chapters: int) -> bool:
        """
        从检查点恢复第一阶段生成
        
        Args:
            checkpoint_data: 检查点数据
            creative_seed: 创意种子
            total_chapters: 总章节数
            
        Returns:
            是否成功
        """
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
            from pathlib import Path
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            
            current_step = checkpoint_data['current_step']
            step_status = checkpoint_data.get('step_status', 'in_progress')
            
            # 获取步骤列表
            steps = GenerationCheckpoint.PHASES['phase_one']['steps']
            
            # 找到当前步骤的索引
            try:
                current_index = steps.index(current_step)
            except ValueError:
                print(f"❌ 无效的步骤: {current_step}")
                notify_failure(f"无效的恢复步骤: {current_step}")
                return False
            
            # 如果当前步骤已完成，从下一步开始
            if step_status == 'completed':
                start_index = current_index + 1
                print(f"✅ 步骤 '{current_step}' 已完成，从下一步开始")
            else:
                # 如果当前步骤未完成，重新执行该步骤
                start_index = current_index
                print(f"🔄 步骤 '{current_step}' 未完成，重新执行")
            
            print(f"📋 将执行步骤 {start_index + 1}/{len(steps)} 到 {len(steps)}")
            
            # 初始化检查点管理器
            title = self.generator.novel_data.get('novel_title', '未命名')
            
            # 获取用户名（用于用户隔离路径）
            username = None
            if hasattr(self.generator, '_username'):
                username = self.generator._username
            elif 'username' in self.generator.novel_data:
                username = self.generator.novel_data['username']
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd(), username=username)
            
            # 执行剩余步骤
            for i in range(start_index, len(steps)):
                step = steps[i]
                print(f"\n{'='*60}")
                print(f"🔄 执行步骤 {i+1}/{len(steps)}: {step}")
                print(f"{'='*60}")
                
                # 更新进度
                try:
                    if hasattr(self.generator, '_update_task_status_callback'):
                        task_id = getattr(self.generator, '_current_task_id', None)
                        if task_id and callable(self.generator._update_task_status_callback):
                            progress = int((i / len(steps)) * 100)
                            self.generator._update_task_status_callback(task_id, 'generating', progress, None)
                except:
                    pass
                
                # 保存检查点（开始执行）- 转换 set 为 list
                checkpoint_mgr.create_checkpoint(
                    phase='phase_one',
                    step=step,
                    data=self._prepare_data_for_checkpoint(self.generator.novel_data),
                    step_status='in_progress'
                )
                
                # 执行步骤
                try:
                    success = self._execute_phase_one_step(step)
                    if not success:
                        error_msg = f"步骤 {step} 执行失败"
                        print(f"❌ {error_msg}")
                        
                        # 保存失败检查点 - 转换 set 为 list
                        checkpoint_mgr.create_checkpoint(
                            phase='phase_one',
                            step=step,
                            data=self._prepare_data_for_checkpoint(self.generator.novel_data),
                            step_status='failed'
                        )
                        
                        notify_failure(error_msg)
                        return False
                    
                    print(f"✅ 步骤 {step} 完成")
                    
                    # 保存完成检查点 - 转换 set 为 list
                    checkpoint_mgr.create_checkpoint(
                        phase='phase_one',
                        step=step,
                        data=self._prepare_data_for_checkpoint(self.generator.novel_data),
                        step_status='completed'
                    )
                    
                except Exception as e:
                    error_msg = f"步骤 {step} 执行异常: {str(e)}"
                    print(f"❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
                    
                    # 保存失败检查点 - 转换 set 为 list
                    checkpoint_mgr.create_checkpoint(
                        phase='phase_one',
                        step=step,
                        data=self._prepare_data_for_checkpoint(self.generator.novel_data),
                        step_status='failed'
                    )
                    
                    notify_failure(error_msg)
                    return False
            
            # 所有步骤完成
            print("\n🎉 第一阶段设定生成完成（恢复模式）！")
            
            # 删除检查点
            checkpoint_mgr.delete_checkpoint()
            
            # 保存最终结果
            from src.core.PhaseGenerator import PhaseGenerator
            phase_generator = PhaseGenerator(self.generator)
            if not phase_generator._save_phase_one_result():
                print("⚠️ 保存最终结果时出现警告，但第一阶段已完成")
            
            return True
            
        except Exception as e:
            error_msg = f"恢复模式执行失败: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            notify_failure(error_msg)
            return False
    
    # ==================== 步骤执行方法 ====================
    
    def _execute_phase_one_step(self, step: str) -> bool:
        """
        执行第一阶段的具体步骤
        
        Args:
            step: 步骤名称
            
        Returns:
            是否成功
        """
        try:
            # 🔥 检查是否被请求停止
            if hasattr(self.generator, '_stop_check_callback'):
                try:
                    self.generator._stop_check_callback()
                except InterruptedError:
                    print(f"🛑 步骤 '{step}' 被用户停止")
                    raise
            
            # 根据步骤名称调用对应的方法
            # 注：这些是 PhaseGenerator 中定义的详细步骤
            step_methods = {
                # 初始化
                'initialization': lambda: self._step_skip('initialization', '初始化完成'),
                # 基础设定
                'writing_style': lambda: self._step_skip('writing_style', '写作风格指南已保存'),
                'market_analysis': lambda: self._step_skip('market_analysis', '市场分析已完成'),
                # 核心设定
                'worldview': self._step_worldview_generation,
                'faction_system': lambda: self._step_skip('faction_system', '势力系统已保存到世界观'),
                'character_design': self._step_character_generation,
                # 规划设计
                'emotional_blueprint': lambda: self._step_skip('emotional_blueprint', '情感蓝图已保存'),
                'growth_plan': lambda: self._step_skip('growth_plan', '成长规划已保存'),
                'stage_plan': lambda: self._step_stage_plan('stage_plan'),
                'detailed_stage_plans': lambda: self._step_skip('detailed_stage_plans', '详细阶段计划已保存'),
                'expectation_mapping': lambda: self._step_skip('expectation_mapping', '期待感地图已保存'),
                'system_init': lambda: self._step_skip('system_init', '系统初始化完成'),
                # 保存和评估
                'saving': lambda: self._step_skip('saving', '结果已保存'),
                'quality_assessment': self._step_quality_assessment,
            }
            
            if step not in step_methods:
                print(f"⚠️ 未知步骤: {step}，跳过")
                return True
            
            return step_methods[step]()
            
        except Exception as e:
            print(f"❌ 执行步骤 {step} 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _step_worldview_generation(self) -> bool:
        """步骤：世界观生成"""
        print("=== 世界观生成 ===")
        
        # 检查是否已有世界观
        if self.generator.novel_data.get('core_worldview'):
            print("✅ 世界观已存在，跳过")
            return True
        
        if not self._generate_worldview():
            return False
        
        # 生成势力系统
        if not self.generator.novel_data.get('faction_system'):
            print("=== 生成势力/阵营系统 ===")
            try:
                faction_system = self.generator.content_generator.generate_faction_system(
                    novel_title=self.generator.novel_data.get("novel_title", "未命名"),
                    core_worldview=self.generator.novel_data.get("core_worldview", {}),
                    selected_plan=self.generator.novel_data.get("selected_plan", {}),
                    market_analysis=self.generator.novel_data.get("market_analysis", {})
                )
                
                if faction_system:
                    self.generator.novel_data["faction_system"] = faction_system
                    self.generator._save_material_to_manager("势力系统", faction_system)
                    print("✅ 势力/阵营系统生成完成")
                else:
                    self.generator.novel_data["faction_system"] = {}
                    print("⚠️ 势力/阵营系统生成失败")
                    
            except Exception as e:
                print(f"❌ 势力/阵营系统生成失败: {e}")
                self.generator.novel_data["faction_system"] = {}
        
        return True
    
    def _step_character_generation(self) -> bool:
        """步骤：角色生成"""
        print("=== 角色生成 ===")
        
        # 检查是否已有角色设计
        if self.generator.novel_data.get('character_design'):
            print("✅ 角色设计已存在，跳过")
            return True
        
        # 需要先有世界观和势力系统
        if not self.generator.novel_data.get('core_worldview'):
            print("⚠️ 缺少世界观，先生成世界观")
            if not self._step_worldview_generation():
                return False
        
        # 生成核心角色设计
        core_characters = self.generator.content_generator.generate_character_design(
            novel_title=self.generator.novel_data.get("novel_title", "未命名"),
            core_worldview=self.generator.novel_data.get("core_worldview", {}),
            selected_plan=self.generator.novel_data.get("selected_plan", {}),
            market_analysis=self.generator.novel_data.get("market_analysis", {}),
            design_level="core",
            global_growth_plan=self.generator.novel_data.get("global_growth_plan"),
            overall_stage_plans=self.generator.novel_data.get("overall_stage_plans"),
            custom_main_character_name=getattr(self.generator, 'custom_main_character_name', None) or ""
        )
        
        if not core_characters:
            print("❌ 核心角色设计失败")
            return False
        
        # 持久化核心角色数据
        if self.generator.quality_assessor is not None:
            self.generator.quality_assessor.persist_initial_character_designs(
                novel_title=self.generator.novel_data.get("novel_title", "未命名"),
                character_design=core_characters
            )
        
        self.generator.novel_data["character_design"] = core_characters
        print("✅ 核心角色设计完成")
        
        return True
    
    def _step_stage_plan(self, stage_name: str) -> bool:
        """步骤：阶段计划生成"""
        print(f"=== {stage_name} 计划生成 ===")
        
        # 检查是否需要先生成整体计划
        if not self.generator.novel_data.get('overall_stage_plans'):
            print("⚠️ 缺少全书阶段计划，先生成")
            if not self._generate_overall_planning():
                return False
        
        # 生成详细写作计划
        if not self.generator.novel_data.get('stage_writing_plans'):
            if not self._generate_stage_writing_plans():
                return False
        
        print(f"✅ {stage_name} 计划已完成")
        return True
    
    def _step_quality_assessment(self) -> bool:
        """步骤：质量评估（跳过）"""
        print("=== 质量评估 ===")
        print("✅ 质量评估完成（跳过）")
        return True
    
    def _step_finalization(self) -> bool:
        """步骤：最终整理"""
        print("=== 最终整理 ===")
        
        # 保存结果
        from src.core.PhaseGenerator import PhaseGenerator
        phase_generator = PhaseGenerator(self.generator)
        if not phase_generator._save_phase_one_result():
            print("⚠️ 保存结果时出现警告")
        
        print("✅ 最终整理完成")
        return True
    
    def _step_skip(self, step_name: str, message: str = None) -> bool:
        """
        跳过步骤（用于尚未独立实现的步骤）
        检查 novel_data 中是否已有数据，如果有则跳过
        """
        display_msg = message or f"{step_name} 已完成"
        print(f"=== {step_name} ===")
        print(f"ℹ️ {display_msg}")
        return True
    
    # ==================== 辅助生成方法 ====================
    
    def _generate_worldview(self) -> bool:
        """生成世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        # 检查必需的字段
        novel_title = self.generator.novel_data.get("novel_title")
        if not novel_title:
            print("❌ 缺少 novel_title，无法生成世界观")
            return False
            
        novel_synopsis = self.generator.novel_data.get("novel_synopsis")
        if not novel_synopsis:
            print("❌ 缺少 novel_synopsis，无法生成世界观")
            return False
            
        selected_plan = self.generator.novel_data.get("selected_plan")
        if not selected_plan:
            print("❌ 缺少 selected_plan，无法生成世界观")
            return False
        
        core_worldview = self.generator.content_generator.generate_core_worldview(
            novel_title,
            novel_synopsis,
            selected_plan,
            self.generator.novel_data.get("market_analysis", {})
        )
        
        self.generator.novel_data["core_worldview"] = core_worldview
        
        if not core_worldview:
            print("❌ 世界观构建失败，终止生成")
            return False
        
        print("✅ 世界观构建完成")
        
        # 保存到材料管理器
        self.generator._save_material_to_manager("世界观", core_worldview, novel_title=novel_title)
        return True
    
    def _generate_overall_planning(self) -> bool:
        """生成全书规划"""
        print("\n=== 步骤5-7: 全书规划 ===")
        
        # 生成情绪蓝图
        if not self.generator.emotional_blueprint_manager.generate_emotional_blueprint(
            self.generator.novel_data["novel_title"],
            self.generator.novel_data["novel_synopsis"],
            self.generator.novel_data["creative_seed"]
        ):
            print("❌ 情绪蓝图生成失败")
            return False
        
        # 全局成长规划
        self.generator.novel_data["global_growth_plan"] = self.generator.global_growth_planner.generate_global_growth_plan()
        
        # 生成全书阶段计划
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        overall_stage_plans = self.generator.stage_plan_manager.generate_overall_stage_plan(
            self.generator.novel_data["creative_seed"],
            self.generator.novel_data["novel_title"],
            self.generator.novel_data["novel_synopsis"],
            self.generator.novel_data.get("market_analysis", {}),
            self.generator.novel_data.get("global_growth_plan", {}),
            self.generator.novel_data.get("emotional_blueprint", {}),
            total_chapters
        )
        
        self.generator.novel_data["overall_stage_plans"] = overall_stage_plans
        
        if not overall_stage_plans:
            print("⚠️ 全书阶段计划生成失败")
            return False
        
        print("✅ 全书规划完成")
        return True
    
    def _generate_stage_writing_plans(self) -> bool:
        """生成各阶段详细写作计划"""
        print("=== 步骤6: 生成各阶段详细写作计划 ===")
        
        overall_stage_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            stage_plan_dict = overall_stage_plans["overall_stage_plan"]
            self.generator.novel_data["stage_writing_plans"] = {}
            
            # 🔥 优化：先批量生成所有阶段的情绪计划（单次API调用）
            print("  💖 批量生成所有阶段的情绪计划...")
            emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
            stages_info = []
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                stages_info.append({'stage_name': stage_name, 'stage_range': stage_range})
            
            all_stages_emotional_plans = self.generator.emotional_plan_manager.generate_all_stages_emotional_plan(
                stages_info, emotional_blueprint
            )
            print(f"  ✅ 成功生成 {len(all_stages_emotional_plans)} 个阶段的情绪计划")
            
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                
                # 获取预生成的情绪计划
                pre_generated_emotional_plan = all_stages_emotional_plans.get(stage_name)
                
                # 🔥 跳过期待感映射生成（将在所有阶段完成后统一生成）
                stage_plan = self.generator.stage_plan_manager.generate_stage_writing_plan(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=self.generator.novel_data["creative_seed"],
                    novel_title=self.generator.novel_data["novel_title"],
                    novel_synopsis=self.generator.novel_data["novel_synopsis"],
                    overall_stage_plan=stage_plan_dict,
                    stage_emotional_plan=pre_generated_emotional_plan,
                    skip_expectation_mapping=True
                )
                
                if stage_plan:
                    self.generator.novel_data["stage_writing_plans"][stage_name] = stage_plan
                    print(f"  ✅ {stage_name} 详细计划生成成功")
            
            success_count = len(self.generator.novel_data["stage_writing_plans"])
            if success_count > 0:
                print(f"✅ 阶段详细计划生成完成: {success_count}/{len(stage_plan_dict)} 个阶段")
                return True
            else:
                print("❌ 所有阶段详细计划生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 生成阶段详细写作计划时出错: {e}")
            import traceback
            traceback.print_exc()
            return False