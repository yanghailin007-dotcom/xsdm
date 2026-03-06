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
    
    def __init__(self, novel_title: str, workspace_dir: Path, logger_name: str = "GenerationCheckpoint", username: str = None):
        """
        初始化检查点管理器
        
        Args:
            novel_title: 小说标题（原始标题，用于存储和显示）
            workspace_dir: 工作目录
            logger_name: 日志名称
            username: 用户名（可选），如果提供则使用 小说项目/用户名/小说名/.generation 结构
        """
        self.novel_title = novel_title
        self.workspace_dir = workspace_dir
        self.logger = get_logger(logger_name)
        self.username = username
        
        # 使用原始标题构建路径，只移除文件系统不支持的字符
        # 保留中文和其他合法字符，使目录名更可读
        self.safe_title = self._sanitize_filename(novel_title)
        
        # 检查点文件路径 - 如果提供了用户名，使用 小说项目/用户名/小说名/.generation 结构
        if username:
            self.checkpoint_dir = workspace_dir / "小说项目" / username / self.safe_title / ".generation"
        else:
            # 向后兼容：使用旧的路径结构
            self.checkpoint_dir = workspace_dir / "小说项目" / self.safe_title / ".generation"
        self.checkpoint_file = self.checkpoint_dir / "checkpoint.json"
        self.backup_file = self.checkpoint_dir / "checkpoint_backup.json"
    
    def create_checkpoint(self, phase: str, step: str, data: Optional[Dict] = None, step_status: str = "in_progress") -> bool:
        """
        创建检查点
        
        Args:
            phase: 生成阶段 (phase_one/phase_two)
            step: 当前步骤
            data: 要保存的数据
            step_status: 步骤状态 (pending/in_progress/completed/failed)
            
        Returns:
            是否成功创建
        """
        try:
            # 添加更详细的日志
            self.logger.info(f"准备创建检查点: {phase} - {step}")
            
            # 确保目录存在
            os.makedirs(self.checkpoint_dir, exist_ok=True)
            self.logger.debug(f"检查点目录: {self.checkpoint_dir}")
            
            checkpoint_data = {
                'novel_title': self.novel_title,
                'creative_title': data.get('creative_title', self.novel_title) if data else self.novel_title,  # 保存原始创意标题
                'creative_seed_id': data.get('creative_seed_id') if data else None,  # 保存创意ID
                'phase': phase,
                'current_step': step,
                'step_status': step_status,
                'timestamp': datetime.now().isoformat(),
                'data': data or {}
            }
            
            # 确保目录存在并记录
            os.makedirs(self.checkpoint_dir, exist_ok=True)
            self.logger.debug(f"检查点目录: {self.checkpoint_dir}")
            
            # 如果存在旧检查点，先备份
            if self.checkpoint_file.exists():
                try:
                    import shutil
                    shutil.copy2(self.checkpoint_file, self.backup_file)
                except Exception as e:
                    self.logger.warning(f"备份旧检查点失败: {e}")
            
            # 原子写入新检查点
            temp_file = self.checkpoint_file.with_suffix('.tmp')
            self.logger.debug(f"临时文件: {temp_file}")
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            # 原子替换
            temp_file.replace(self.checkpoint_file)
            
            # 验证文件创建成功
            if not self.checkpoint_file.exists():
                raise FileNotFoundError(f"检查点文件创建失败: {self.checkpoint_file}")
            
            self.logger.info(f"✅ 检查点已保存: {phase} - {step} ({self.checkpoint_file})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 创建检查点失败: {e}")
            import traceback
            self.logger.error(f"错误堆栈: {traceback.format_exc()}")
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
        # 保留更多字符，包括逗号
        safe = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']', ',')).rstrip()
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
            可恢复任务列表，每个任务包含novel_title和creative_title用于匹配
        """
        resumable_tasks = []
        projects_dir = self.workspace_dir / "小说项目"
        
        if not projects_dir.exists():
            self.logger.warning(f"⚠️ 项目目录不存在: {projects_dir}")
            return resumable_tasks
        
        self.logger.info(f"🔍 开始扫描项目目录查找检查点...")
        total_dirs = 0
        with_checkpoint = 0
        
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            total_dirs += 1
            checkpoint_file = project_dir / ".generation" / "checkpoint.json"
            
            # 只有当 checkpoint.json 文件真正存在时才认为有检查点
            if checkpoint_file.exists() and checkpoint_file.is_file():
                self.logger.info(f"  📁 发现检查点: {project_dir.name}")
                
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    
                    novel_title = checkpoint_data.get('novel_title', 'Unknown')
                    creative_title = checkpoint_data.get('creative_title', novel_title)
                    creative_seed_id = checkpoint_data.get('creative_seed_id')
                    
                    self.logger.info(f"    novel_title: {novel_title}")
                    self.logger.info(f"    creative_title: {creative_title}")
                    
                    # 使用原始目录名创建检查点管理器，确保能找到文件
                    checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir)
                    # 强制使用实际存在的目录路径
                    checkpoint_mgr.checkpoint_dir = project_dir / ".generation"
                    checkpoint_mgr.checkpoint_file = checkpoint_file
                    
                    resume_info = checkpoint_mgr.get_resume_info()
                    
                    if resume_info:
                        # 添加映射信息，支持多种方式查找
                        resume_info['creative_title'] = creative_title
                        resume_info['creative_seed_id'] = creative_seed_id
                        resume_info['directory_name'] = project_dir.name
                        resumable_tasks.append(resume_info)
                        self.logger.info(f"    ✅ 成功添加到任务列表")
                    else:
                        self.logger.warning(f"    ⚠️ get_resume_info() 返回 None")
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"    ❌ JSON解析失败: {project_dir.name}")
                    self.logger.error(f"       错误: {e}")
                    # 尝试修复JSON文件
                    self._try_fix_checkpoint_json(checkpoint_file)
                except Exception as e:
                    self.logger.error(f"    ❌ 读取检查点失败 {project_dir.name}: {e}")
            else:
                self.logger.info(f"  📁 没有检查点文件")
        
        self.logger.info(f"🎯 扫描完成: {total_dirs} 个目录，{with_checkpoint} 个有检查点，{len(resumable_tasks)} 个可用任务")
        
        # 打印所有找到的任务
        for task in resumable_tasks:
            self.logger.info(f"  📋 {task.get('creative_title', task.get('novel_title'))}")
        
        return resumable_tasks
    
    def _try_fix_checkpoint_json(self, checkpoint_file: Path):
        """尝试修复损坏的JSON文件"""
        try:
            import re
            
            self.logger.error(f"    🔧 尝试修复JSON文件: {checkpoint_file}")
            
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找问题：可能是引号没有正确转义
            # 尝试修复常见的JSON问题
            # 这里只是记录日志，实际修复需要更复杂的逻辑
            self.logger.error(f"    JSON内容预览（前200字符）: {content[:200]}")
            
        except Exception as e:
            self.logger.error(f"    修复JSON失败: {e}")
    
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
            self.logger.warning(f"任务 {novel_title} 没有可用的检查点")
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