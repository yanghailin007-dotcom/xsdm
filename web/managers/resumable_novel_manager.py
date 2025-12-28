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
        
        if not title:
            raise ValueError("小说标题不能为空")
        
        # 创建检查点管理器
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir)
        
        # 检查是否可以恢复
        if resume_mode:
            if not checkpoint_mgr.can_resume():
                raise ValueError(f"任务 {title} 没有可用的检查点")
            
            checkpoint_data = checkpoint_mgr.load_checkpoint()
            if not checkpoint_data:
                raise ValueError("无法加载检查点")
            
            self.logger.info(f"🔄 恢复生成任务: {title}")
            self.logger.info(f"   从步骤: {checkpoint_data['current_step']}")
            
            # 使用恢复模式启动
            task_id = self._resume_generation(checkpoint_mgr, checkpoint_data, progress_callback)
        else:
            # 新任务：删除旧的检查点
            if checkpoint_mgr.can_resume():
                self.logger.info(f"发现旧检查点，将被覆盖: {title}")
                checkpoint_mgr.delete_checkpoint()
            
            self.logger.info(f"🚀 启动新的生成任务: {title}")
            
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
        saved_data = checkpoint_data.get('data', {})
        
        # 获取阶段信息
        phase_info = GenerationCheckpoint.PHASES.get(phase, {})
        steps = phase_info.get('steps', [])
        
        try:
            current_index = steps.index(current_step)
        except ValueError:
            current_index = 0
        
        next_step = steps[current_index + 1] if current_index + 1 < len(steps) else None
        
        if not next_step:
            raise ValueError("任务已经完成，无需恢复")
        
        task_id = f"resume_{checkpoint_mgr.novel_title}_{next_step}"
        
        # 模拟恢复流程（实际应该调用相应的生成函数）
        self.logger.info(f"📝 恢复步骤: {next_step}")
        
        # 更新检查点
        checkpoint_mgr.create_checkpoint(
            phase=phase,
            step=next_step,
            data={
                **saved_data,
                'last_step': current_step,
                'resume_count': saved_data.get('resume_count', 0) + 1
            }
        )
        
        # 通知进度
        if progress_callback:
            progress_info = {
                'task_id': task_id,
                'phase': phase,
                'current_step': next_step,
                'step_index': current_index + 1,
                'total_steps': len(steps),
                'progress': round(((current_index + 1) / len(steps)) * 100, 1),
                'is_resume': True
            }
            progress_callback(progress_info)
        
        return task_id
    
    def get_resumable_tasks(self) -> list:
        """
        获取所有可恢复的任务列表
        
        Returns:
            可恢复任务列表
        """
        return self.recovery_manager.find_resumable_tasks()
    
    def get_resume_info(self, title: str) -> Optional[Dict]:
        """
        获取特定任务的恢复信息
        
        Args:
            title: 小说标题
            
        Returns:
            恢复信息字典
        """
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir)
        return checkpoint_mgr.get_resume_info()
    
    def delete_checkpoint(self, title: str) -> bool:
        """
        删除检查点（完成任务后调用）
        
        Args:
            title: 小说标题
            
        Returns:
            是否成功删除
        """
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir)
        return checkpoint_mgr.delete_checkpoint()
    
    def update_checkpoint_data(self, title: str, phase: str, step: str, data: Dict) -> bool:
        """
        更新检查点数据
        
        Args:
            title: 小说标题
            phase: 生成阶段
            step: 当前步骤
            data: 要保存的数据
            
        Returns:
            是否成功更新
        """
        checkpoint_mgr = GenerationCheckpoint(title, self.workspace_dir)
        
        # 加载现有检查点
        existing_data = checkpoint_mgr.load_checkpoint()
        if existing_data:
            # 合并数据
            merged_data = {**existing_data.get('data', {}), **data}
        else:
            merged_data = data
        
        return checkpoint_mgr.create_checkpoint(phase, step, merged_data)