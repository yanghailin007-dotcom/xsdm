"""
生成检查点管理器 - 支持中断后恢复
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime
from src.utils.logger import get_logger


class GenerationCheckpoint:
    """生成检查点管理器"""
    
    # 生成阶段定义
    PHASES = {
        'phase_one': {
            'name': '第一阶段设定生成',
            'steps': [
                'worldview_generation',      # 世界观生成
                'character_generation',      # 角色生成
                'opening_stage_plan',        # 开篇阶段计划
                'development_stage_plan',    # 发展阶段计划
                'climax_stage_plan',        # 高潮阶段计划
                'ending_stage_plan',        # 结局阶段计划
                'quality_assessment',       # 质量评估
                'finalization'              # 最终整理
            ]
        },
        'phase_two': {
            'name': '第二阶段内容生成',
            'steps': [
                'chapter_1_10',             # 第1-10章
                'chapter_11_20',            # 第11-20章
                'chapter_21_30',            # 第21-30章
                # ... 可以根据总章节数动态生成
            ]
        }
    }
    
    def __init__(self, novel_title: str, workspace_dir: Path, logger_name: str = "GenerationCheckpoint"):
        """
        初始化检查点管理器
        
        Args:
            novel_title: 小说标题
            workspace_dir: 工作目录
            logger_name: 日志名称
        """
        self.novel_title = novel_title
        self.workspace_dir = workspace_dir
        self.logger = get_logger(logger_name)
        
        # 安全的文件名
        self.safe_title = self._sanitize_filename(novel_title)
        
        # 检查点文件路径
        self.checkpoint_dir = workspace_dir / "小说项目" / self.safe_title / ".generation"
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"
        self.backup_file = self.checkpoint_dir / "checkpoint_backup.json"
        
        # 确保目录存在
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def create_checkpoint(self, phase: str, step: str, data: Optional[Dict] = None) -> bool:
        """
        创建检查点
        
        Args:
            phase: 生成阶段 (phase_one/phase_two)
            step: 当前步骤
            data: 要保存的数据
            
        Returns:
            是否成功创建
        """
        try:
            checkpoint_data = {
                'novel_title': self.novel_title,
                'phase': phase,
                'current_step': step,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
            
            # 如果存在旧检查点，先备份
            if self.checkpoint_file.exists():
                try:
                    import shutil
                    shutil.copy2(self.checkpoint_file, self.backup_file)
                except Exception as e:
                    self.logger.warn(f"备份旧检查点失败: {e}")
            
            # 原子写入新检查点
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # 原子替换
            temp_file.replace(self.checkpoint_file)
            
            self.logger.info(f"✅ 检查点已保存: {phase} - {step}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 创建检查点失败: {e}")
            return False
    
    def load_checkpoint(self) -> Optional[Dict]:
        """
        加载检查点
        
        Returns:
            检查点数据，如果不存在返回None
        """
        try:
            if not self.checkpoint_file.exists():
                self.logger.info("没有找到检查点文件")
                return None
            
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            self.logger.info(f"✅ 成功加载检查点: {checkpoint_data.get('phase')} - {checkpoint_data.get('current_step')}")
            return checkpoint_data
            
        except Exception as e:
            self.logger.error(f"❌ 加载检查点失败: {e}")
            
            # 尝试加载备份
            if self.backup_file.exists():
                try:
                    with open(self.backup_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    self.logger.info("✅ 从备份恢复检查点")
                    return checkpoint_data
                except Exception as e2:
                    self.logger.error(f"❌ 从备份恢复也失败: {e2}")
            
            return None
    
    def get_resume_info(self) -> Optional[Dict]:
        """
        获取恢复信息（用于前端显示）
        
        Returns:
            恢复信息字典
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return None
        
        phase_info = self.PHASES.get(checkpoint['phase'], {})
        steps = phase_info.get('steps', [])
        current_index = steps.index(checkpoint['current_step']) if checkpoint['current_step'] in steps else 0
        
        return {
            'novel_title': checkpoint['novel_title'],
            'phase': checkpoint['phase'],
            'phase_name': phase_info.get('name', checkpoint['phase']),
            'current_step': checkpoint['current_step'],
            'current_step_index': current_index,
            'total_steps': len(steps),
            'completed_steps': current_index,
            'remaining_steps': len(steps) - current_index,
            'timestamp': checkpoint['timestamp'],
            'progress_percentage': round((current_index / len(steps)) * 100, 1) if steps else 0,
            'data': checkpoint.get('data', {})
        }
    
    def delete_checkpoint(self) -> bool:
        """
        删除检查点（任务完成后调用）
        
        Returns:
            是否成功删除
        """
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
            if self.backup_file.exists():
                self.backup_file.unlink()
            
            self.logger.info("✅ 检查点已删除")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 删除检查点失败: {e}")
            return False
    
    def can_resume(self) -> bool:
        """
        检查是否可以恢复
        
        Returns:
            是否有可用的检查点
        """
        return self.checkpoint_file.exists() or self.backup_file.exists()
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        safe = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']')).rstrip()
        return safe.replace(' ', '_')


class CheckpointRecoveryManager:
    """检查点恢复管理器 - 协调恢复流程"""
    
    def __init__(self, workspace_dir: Path):
        """
        初始化恢复管理器
        
        Args:
            workspace_dir: 工作目录
        """
        self.workspace_dir = workspace_dir
        self.logger = get_logger("CheckpointRecoveryManager")
        self.current_checkpoint: Optional[GenerationCheckpoint] = None
    
    def find_resumable_tasks(self) -> List[Dict]:
        """
        查找所有可以恢复的任务
        
        Returns:
            可恢复任务列表
        """
        resumable_tasks = []
        projects_dir = self.workspace_dir / "小说项目"
        
        if not projects_dir.exists():
            return resumable_tasks
        
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            checkpoint_file = project_dir / ".generation" / "checkpoint.json"
            # 只有当 checkpoint.json 文件真正存在时才认为有检查点
            if checkpoint_file.exists() and checkpoint_file.is_file():
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    
                    novel_title = checkpoint_data.get('novel_title', 'Unknown')
                    checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir)
                    resume_info = checkpoint_mgr.get_resume_info()
                    
                    if resume_info:
                        resumable_tasks.append(resume_info)
                        
                except Exception as e:
                    self.logger.warn(f"读取检查点失败 {project_dir}: {e}")
        
        return resumable_tasks
    
    def prepare_resume(self, novel_title: str) -> Optional[GenerationCheckpoint]:
        """
        准备恢复任务
        
        Args:
            novel_title: 要恢复的小说标题
            
        Returns:
            检查点管理器实例
        """
        checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir)
        
        if not checkpoint_mgr.can_resume():
            self.logger.warn(f"任务 {novel_title} 没有可用的检查点")
            return None
        
        self.current_checkpoint = checkpoint_mgr
        return checkpoint_mgr
    
    def resume_from_checkpoint(self, novel_title: str, generation_callback):
        """
        从检查点恢复生成
        
        Args:
            novel_title: 小说标题
            generation_callback: 生成回调函数，接收 (checkpoint_data, start_step)
        """
        checkpoint_mgr = self.prepare_resume(novel_title)
        if not checkpoint_mgr:
            return False
        
        checkpoint_data = checkpoint_mgr.load_checkpoint()
        if not checkpoint_data:
            return False
        
        phase = checkpoint_data['phase']
        current_step = checkpoint_data['current_step']
        
        # 找到下一步
        phase_info = GenerationCheckpoint.PHASES.get(phase, {})
        steps = phase_info.get('steps', [])
        current_index = steps.index(current_step) if current_step in steps else 0
        next_step = steps[current_index + 1] if current_index + 1 < len(steps) else None
        
        if not next_step:
            self.logger.info("任务已经完成，无需恢复")
            return False
        
        self.logger.info(f"🔄 从检查点恢复: {phase} - {next_step}")
        
        # 调用生成回调
        try:
            generation_callback(checkpoint_data, next_step)
            return True
        except Exception as e:
            self.logger.error(f"恢复生成失败: {e}")
            return False