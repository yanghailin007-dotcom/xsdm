"""
可恢复的小说生成管理器 - 支持中断后恢复
"""
import sys
import os
from pathlib import Path
from typing import Dict, Optional, Callable
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger
from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint, CheckpointRecoveryManager


class ResumableNovelGenerationManager:
    """可恢复的小说生成管理器"""
    
    def __init__(self, workspace_dir: Optional[Path] = None):
        """
        初始化管理器
        
        Args:
            workspace_dir: 工作目录，默认使用当前目录
        """
        self.workspace_dir = workspace_dir or Path.cwd()
        self.logger = get_logger("ResumableNovelManager")
        
        # 检查点恢复管理器
        self.recovery_manager = CheckpointRecoveryManager(self.workspace_dir)
        
        # 导入原有的管理器
        try:
            from web.managers.novel_manager import NovelGenerationManager
            self.base_manager = NovelGenerationManager()
        except Exception as e:
            self.logger.error(f"无法初始化基础管理器: {e}")
            self.base_manager = None
    
    def start_generation_with_resume(
        self,
        generation_params: Dict,
        resume_mode: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        启动生成任务（支持恢复模式）
        
        Args:
            generation_params: 生成参数
            resume_mode: 是否为恢复模式
            progress_callback: 进度回调函数
            
        Returns:
            任务ID
        """
        title = generation_params.get('title')
        username = generation_params.get('username')
        
        if not title:
            raise ValueError("小说标题不能为空")
        
        # 创建检查点管理器（传递 username 以使用正确的路径）
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir, username=username)
        
        # 检查是否可以恢复
        if resume_mode:
            if not checkpoint_mgr.can_resume():
                raise ValueError(f"任务 {title} 没有可用的检查点")
            
            checkpoint_data = checkpoint_mgr.load_checkpoint()
            if not checkpoint_data:
                raise ValueError("无法加载检查点")
            
            self.logger.info(f"恢复生成任务: {title}")
            
            # 使用恢复模式启动
            task_id = self._resume_generation(checkpoint_mgr, checkpoint_data, progress_callback)
        else:
            # 新任务：删除旧的检查点
            if checkpoint_mgr.can_resume():
                checkpoint_mgr.delete_checkpoint()
            
            # 创建初始检查点
            checkpoint_mgr.create_checkpoint(
                phase='phase_one',
                step='initialization',
                data={
                    'generation_params': generation_params,
                    'status': 'started'
                }
            )
            
            # 使用基础管理器启动
            if self.base_manager:
                task_id = self.base_manager.start_generation(generation_params)
            else:
                # 如果没有基础管理器，创建一个简单的任务ID
                task_id = f"task_{title}_{id(generation_params)}"
        
        return task_id
    
    def _resume_generation(
        self,
        checkpoint_mgr: GenerationCheckpoint,
        checkpoint_data: Dict,
        progress_callback: Optional[Callable]
    ) -> str:
        """
        从检查点恢复生成
        
        Args:
            checkpoint_mgr: 检查点管理器
            checkpoint_data: 检查点数据
            progress_callback: 进度回调
            
        Returns:
            任务ID
        """
        phase = checkpoint_data['phase']
        current_step = checkpoint_data['current_step']
        step_status = checkpoint_data.get('step_status', 'in_progress')
        saved_data = checkpoint_data.get('data', {})
        
        # 获取阶段信息
        phase_info = GenerationCheckpoint.PHASES.get(phase, {})
        steps = phase_info.get('steps', [])
        
        try:
            current_index = steps.index(current_step)
        except ValueError:
            current_index = 0
        
        # 根据步骤状态决定恢复策略
        if step_status == 'completed':
            # 步骤已完成，继续下一步
            next_step = steps[current_index + 1] if current_index + 1 < len(steps) else None
            if not next_step:
                raise ValueError("任务已经完成，无需恢复")
            
            task_id = f"resume_{checkpoint_mgr.novel_title}_{next_step}"
            
            # 标记下一步为 in_progress
            checkpoint_mgr.create_checkpoint(
                phase=phase,
                step=next_step,
                data={
                    **saved_data,
                    'last_step': current_step,
                    'resume_count': saved_data.get('resume_count', 0) + 1
                },
                step_status='in_progress'
            )
        elif step_status == 'failed':
            # 步骤失败，重试当前步骤
            task_id = f"retry_{checkpoint_mgr.novel_title}_{current_step}"
            
            # 保持当前步骤，状态改为 in_progress
            checkpoint_mgr.create_checkpoint(
                phase=phase,
                step=current_step,
                data={
                    **saved_data,
                    'retry_count': saved_data.get('retry_count', 0) + 1
                },
                step_status='in_progress'
            )
        else:
            # in_progress、pending 或其他状态，继续当前步骤
            # 不需要重新创建检查点，保持原有步骤和状态
            task_id = f"resume_{checkpoint_mgr.novel_title}_{current_step}"
            
            # 只有当状态不是 in_progress 时才更新
            if step_status != 'in_progress':
                checkpoint_mgr.create_checkpoint(
                    phase=phase,
                    step=current_step,
                    data={
                        **saved_data,
                        'resume_count': saved_data.get('resume_count', 0) + 1
                    },
                    step_status='in_progress'
                )
        
        # 通知进度
        if progress_callback:
            # 计算正确的步骤索引
            if step_status == 'completed':
                step_index = current_index + 1
                display_step = steps[current_index + 1]
            else:
                step_index = current_index
                display_step = current_step
            
            progress_info = {
                'task_id': task_id,
                'phase': phase,
                'current_step': display_step,
                'step_index': step_index,
                'total_steps': len(steps),
                'progress': round((step_index / len(steps)) * 100, 1),
                'is_resume': True,
                'step_status': step_status
            }
            progress_callback(progress_info)
        
        # 🔥 核心修复：实际启动生成任务
        if not self.base_manager:
            raise ValueError("基础管理器未初始化，无法执行恢复生成")
        
        # 从检查点数据中获取原始生成参数
        generation_params = saved_data.get('generation_params', {}).copy()
        
        # 确保有标题
        if not generation_params.get('title'):
            generation_params['title'] = checkpoint_mgr.novel_title
        
        # 添加恢复模式标记
        generation_params['is_resume_mode'] = True
        generation_params['resume_step'] = current_step
        generation_params['resume_phase'] = phase
        
        # 🔥 关键修复：恢复时必须设置 start_new=False，否则会导致从头开始
        generation_params['start_new'] = False
        
        # 🔥 关键修复：确保 creative_seed 存在
        # 如果 generation_params 中没有 creative_seed，尝试从其他地方获取
        if not generation_params.get('creative_seed'):
            # 尝试从 saved_data 的顶层获取
            if 'creative_seed' in saved_data:
                generation_params['creative_seed'] = saved_data['creative_seed']
            # 尝试从 selected_plan 获取
            elif 'selected_plan' in saved_data:
                generation_params['creative_seed'] = saved_data['selected_plan']
        
        # 🔥 如果还是没有 creative_seed，记录警告但不阻止恢复
        # 因为检查点中可能已经包含了必要的中间数据
        if not generation_params.get('creative_seed'):
            self.logger.warning(f"⚠️ 恢复任务时缺少 creative_seed，将从检查点继续")
            # 设置一个最小的配置以允许继续
            generation_params['creative_seed'] = {
                'resume_mode': True,
                'checkpoint_step': current_step,
                'checkpoint_phase': phase
            }
        
        # 使用基础管理器启动实际的生成任务
        actual_task_id = self.base_manager.start_generation(generation_params)
        
        return actual_task_id
    
    def get_resumable_tasks(self, username: str = None) -> list:
        """
        获取所有可恢复的任务列表
        
        Args:
            username: 用户名（可选），如果提供则只返回该用户的任务
            
        Returns:
            可恢复任务列表
        """
        return self.recovery_manager.find_resumable_tasks(username=username)
    
    def get_resume_info(self, title: str, username: str = None) -> Optional[Dict]:
        """
        获取特定任务的恢复信息
        支持通过创意标题或实际生成的书名查找
        
        Args:
            title: 小说标题（可以是创意标题或实际书名）
            username: 用户名（可选），用于定位用户隔离路径
            
        Returns:
            恢复信息字典
        """
        # 🔥 修复：首先尝试使用指定的用户名查找
        if username:
            checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir, username=username)
            if checkpoint_mgr.can_resume():
                return checkpoint_mgr.get_resume_info()
        
        # 如果直接匹配失败，遍历所有任务查找匹配的 creative_title
        all_tasks = self.get_resumable_tasks(username=username)
        for task in all_tasks:
            # 检查 creative_title 是否匹配
            if task.get('creative_title') == title:
                # 找到匹配的任务，使用实际的书名和用户名获取信息
                actual_title = task.get('novel_title')
                task_username = task.get('username')
                checkpoint_mgr = GenerationCheckpoint(actual_title, self.workspace_dir, username=task_username)
                if checkpoint_mgr.can_resume():
                    return checkpoint_mgr.get_resume_info()
            
            # 检查 novel_title 是否匹配
            if task.get('novel_title') == title:
                return task
        
        return None
    
    def delete_checkpoint(self, title: str, username: str = None) -> bool:
        """
        删除检查点（完成任务后调用）
        
        Args:
            title: 小说标题
            username: 用户名（可选），用于定位用户隔离路径
            
        Returns:
            是否成功删除
        """
        # 🔥 修复：先尝试查找任务获取用户名
        if not username:
            task_info = self.get_resume_info(title)
            if task_info:
                username = task_info.get('username')
        
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir, username=username)
        return checkpoint_mgr.delete_checkpoint()
    
    def update_checkpoint_data(self, title: str, phase: str, step: str, data: Dict, username: str = None) -> bool:
        """
        更新检查点数据
        
        Args:
            title: 小说标题
            phase: 生成阶段
            step: 当前步骤
            data: 要保存的数据
            username: 用户名（可选），用于定位用户隔离路径
            
        Returns:
            是否成功更新
        """
        # 🔥 修复：先尝试查找任务获取用户名
        if not username:
            task_info = self.get_resume_info(title)
            if task_info:
                username = task_info.get('username')
        
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir, username=username)
        
        # 加载现有检查点
        existing_data = checkpoint_mgr.load_checkpoint()
        if existing_data:
            # 合并数据
            merged_data = {**existing_data.get('data', {}), **data}
        else:
            merged_data = data
        
        return checkpoint_mgr.create_checkpoint(phase, step, merged_data)