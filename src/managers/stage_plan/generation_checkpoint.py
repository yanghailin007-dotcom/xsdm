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
    
    # 生成阶段定义 - 与 PhaseGenerator 完全匹配
    # 🔥 扩展：添加子步骤信息用于详细进度显示
    PHASES = {
        'phase_one': {
            'name': '第一阶段设定生成',
            # 🔥 修复：与 novel_manager 的14个标准步骤严格对齐
            'steps': [
                'creative_refinement',      # 0. 创意精炼
                'fanfiction_detection',     # 1. 同人检测
                'multiple_plans',           # 2. 生成多个方案
                'plan_selection',           # 3. 选择最佳方案
                'foundation_planning',      # 4. 基础规划（写作风格+市场分析）
                'worldview_with_factions',  # 5. 世界观与势力系统
                'character_design',         # 6. 核心角色设计
                'emotional_growth_planning', # 7. 情绪蓝图与成长规划
                'stage_plan',               # 8. 全书阶段计划
                'detailed_stage_plans',     # 9. 阶段详细计划
                'supplementary_characters', # 10. 全书补充角色（基于各阶段需求统筹生成）
                'expectation_mapping',      # 11. 期待感映射
                'system_init',              # 12. 系统初始化
                'saving',                   # 13. 保存设定结果
                'quality_assessment'        # 14. AI质量评估
            ],
            # 🔥 新增：子步骤定义（用于详细UI显示）- 与14个标准步骤对齐
            'sub_steps': {
                'creative_refinement': [
                    ('parse_creative_seed', '解析创意种子'),
                    ('refine_prompt', '精炼为AI指令')
                ],
                'fanfiction_detection': [
                    ('detect_fanfiction', '同人小说检测'),
                    ('originality_check', '原创性检查')
                ],
                'multiple_plans': [
                    ('generate_variants', '生成多个创意方案')
                ],
                'plan_selection': [
                    ('evaluate_plans', '评估方案质量'),
                    ('select_best', '选择最佳方案')
                ],
                'foundation_planning': [
                    ('writing_style', '写作风格指南'),
                    ('market_analysis', '市场分析与卖点提炼')
                ],
                'worldview_with_factions': [
                    ('worldview', '核心世界观构建'),
                    ('faction_system', '势力/阵营系统构建')
                ],
                'character_design': [
                    ('core_characters', '核心角色设计（主角/盟友/宿敌）')
                ],
                'emotional_growth_planning': [
                    ('emotional_blueprint', '生成全书情绪蓝图'),
                    ('growth_plan', '生成全书全局成长规划')
                ],
                'stage_plan': [
                    ('overall_stage_plan', '制定全书阶段计划')
                ],
                'detailed_stage_plans': [
                    ('stage_emotional_plan', '阶段情绪计划'),
                    ('major_event_skeletons', '顶层设计注入-主龙骨'),
                    ('event_decomposition', '解剖重大事件为中型事件'),
                    ('goal_coherence_assessment', '阶段目标层级一致性评估'),
                    ('continuity_assessment', '阶段事件连续性评估'),
                    ('continuity_optimization', '阶段事件连续性优化'),
                    ('character_inference', '阶段角色推断')
                ],
                'supplementary_characters': [
                    ('analyze_stage_needs', '分析各阶段角色需求'),
                    ('batch_generate', '批量生成全书补充角色'),
                    ('integrate_characters', '整合补充角色到角色库')
                ],
                'expectation_mapping': [
                    ('expectation_mapping', '期待感地图生成'),
                    ('expectation_integration', '期待感整合')
                ],
                'system_init': [
                    ('world_state_init', '世界状态初始化'),
                    ('relationship_init', '关系网初始化')
                ],
                'saving': [
                    ('save_materials', '保存材料'),
                    ('save_plans', '保存写作计划')
                ],
                'quality_assessment': [
                    ('plan_assessment', '写作计划质量评估'),
                    ('readiness_check', '就绪检查')
                ]
            },
            # 🔥 新增：子步骤进度权重（每个主步骤内部分配100%）
            'sub_step_weights': {
                'detailed_stage_plans': {
                    'stage_emotional_plan': 10,
                    'major_event_skeletons': 15,
                    'event_decomposition': 30,
                    'goal_coherence_assessment': 10,
                    'continuity_assessment': 10,
                    'continuity_optimization': 10,
                    'character_inference': 10,
                    'supporting_characters': 5
                }
            },
            # 🔥 新增：基于实际日志的API调用统计（用于预估点数和耗时）
            'api_call_estimates': {
                'initialization': {'calls': 2, 'time_min': 2, 'time_max': 5},  # 创意精炼+同人检测
                'writing_style': {'calls': 1, 'time_min': 1, 'time_max': 3},
                'market_analysis': {'calls': 3, 'time_min': 3, 'time_max': 6},  # 市场分析+质量评估+新鲜度
                'worldview': {'calls': 3, 'time_min': 3, 'time_max': 6},  # 世界观+质量评估+新鲜度
                'faction_system': {'calls': 1, 'time_min': 1, 'time_max': 3},
                'character_design': {'calls': 1, 'time_min': 1, 'time_max': 3},
                'emotional_growth_planning': {'calls': 2, 'time_min': 2, 'time_max': 4},  # 情感蓝图 + 成长规划
                'stage_plan': {'calls': 1, 'time_min': 1, 'time_max': 2},
                # detailed_stage_plans 是动态的，按阶段计算
                'detailed_stage_plans_per_stage': {
                    'calls': 8,  # 情绪计划+主龙骨+4-7个事件解剖+2个评估+优化+角色推断（不含补充角色）
                    'time_min': 15, 
                    'time_max': 30
                },
                'supplementary_characters': {'calls': 1, 'time_min': 2, 'time_max': 4},  # 一次性批量生成全书补充角色
                'expectation_mapping': {'calls': 1, 'time_min': 1, 'time_max': 2},
                'system_init': {'calls': 1, 'time_min': 1, 'time_max': 2},
                'saving': {'calls': 0, 'time_min': 1, 'time_max': 2},  # 本地操作
                'quality_assessment': {'calls': 1, 'time_min': 2, 'time_max': 5}
            }
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
                'username': self.username,  # 🔥 保存用户名，用于恢复时定位正确的路径
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
            
            # 原子写入新检查点（带重试机制）
            # 🔥 修复：使用唯一的临时文件名避免多线程冲突
            import time
            import shutil
            import threading
            temp_file = self.checkpoint_file.with_suffix(f'.tmp_{threading.current_thread().ident}_{int(time.time()*1000)}')
            self.logger.debug(f"临时文件: {temp_file}")
            
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                    f.flush()  # 确保数据写入磁盘
                    os.fsync(f.fileno())  # 强制同步到磁盘
            except Exception as e:
                self.logger.error(f"写入临时文件失败: {e}")
                raise
            
            # 🔥 修复：添加重试机制处理 Windows 文件锁和文件不存在问题
            max_retries = 5
            move_success = False
            for attempt in range(max_retries):
                try:
                    # 验证临时文件存在
                    if not temp_file.exists():
                        # 🔥 修复：如果临时文件不存在，重新创建它
                        self.logger.warning(f"临时文件不存在，重新创建: {temp_file}")
                        with open(temp_file, 'w', encoding='utf-8') as f:
                            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                            f.flush()
                            os.fsync(f.fileno())
                    
                    # Windows 上 replace 可能失败，使用 copy + delete 作为备选
                    if self.checkpoint_file.exists():
                        try:
                            self.checkpoint_file.unlink()
                        except PermissionError:
                            # 如果文件被占用，尝试重命名后删除
                            old_file = self.checkpoint_file.with_suffix('.old')
                            os.rename(str(self.checkpoint_file), str(old_file))
                            old_file.unlink(missing_ok=True)
                    
                    shutil.move(str(temp_file), str(self.checkpoint_file))
                    move_success = True
                    break
                    
                except (PermissionError, FileNotFoundError) as e:
                    if attempt < max_retries - 1:
                        self.logger.warning(f"⚠️ 文件操作失败，等待重试 ({attempt+1}/{max_retries}): {e}")
                        time.sleep(0.2 * (attempt + 1))  # 递增延迟
                    else:
                        # 最后一次尝试直接使用 rename
                        try:
                            if temp_file.exists():
                                os.rename(str(temp_file), str(self.checkpoint_file))
                                move_success = True
                            else:
                                # 最终回退：直接写入目标文件
                                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                                    json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
                                move_success = True
                            break
                        except Exception as e2:
                            self.logger.error(f"最终尝试失败: {e2}")
                            raise
            
            # 清理临时文件
            finally:
                try:
                    if temp_file.exists():
                        temp_file.unlink(missing_ok=True)
                except Exception as e:
                    self.logger.debug(f"清理临时文件失败: {e}")
            
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
        current_step = checkpoint['current_step']
        current_index = steps.index(current_step) if current_step in steps else 0
        
        # 🔥 修复：计算完成的步骤数
        # 如果当前步骤状态是 completed，则完成步骤数 = 当前索引 + 1
        # 否则，完成步骤数 = 当前索引（假设之前的步骤都已完成）
        step_status = checkpoint.get('step_status', 'unknown')
        if step_status == 'completed':
            completed_steps = current_index + 1
        else:
            completed_steps = current_index
        
        return {
            'novel_title': checkpoint['novel_title'],
            'phase': checkpoint['phase'],
            'phase_name': phase_info.get('name', checkpoint['phase']),
            'current_step': current_step,
            'current_step_index': current_index,
            'total_steps': len(steps),
            'completed_steps': completed_steps,
            'remaining_steps': len(steps) - completed_steps,
            'timestamp': checkpoint['timestamp'],
            'progress_percentage': round((completed_steps / len(steps)) * 100, 1) if steps else 0,
            'data': checkpoint.get('data', {})
        }
    
    @staticmethod
    def calculate_phase_one_estimate(total_chapters: int = 200) -> Dict:
        """
        计算第一阶段预估的点数和耗时
        
        Args:
            total_chapters: 总章节数，用于计算阶段数
            
        Returns:
            预估信息字典
        """
        phase_one = GenerationCheckpoint.PHASES['phase_one']
        estimates = phase_one['api_call_estimates']
        
        # 计算阶段数（默认每阶段约30章）
        estimated_stages = max(3, total_chapters // 30)
        
        total_calls = 0
        total_time_min = 0
        total_time_max = 0
        
        breakdown = {}
        
        for step, info in estimates.items():
            if step == 'detailed_stage_plans_per_stage':
                # 动态计算多个阶段的详细计划
                calls = info['calls'] * estimated_stages
                time_min = info['time_min'] * estimated_stages
                time_max = info['time_max'] * estimated_stages
                breakdown['detailed_stage_plans'] = {
                    'calls': calls,
                    'time_min': time_min,
                    'time_max': time_max,
                    'note': f'按 {estimated_stages} 个阶段计算'
                }
            else:
                calls = info['calls']
                time_min = info['time_min']
                time_max = info['time_max']
                breakdown[step] = {
                    'calls': calls,
                    'time_min': time_min,
                    'time_max': time_max
                }
            
            total_calls += calls
            total_time_min += time_min
            total_time_max += time_max
        
        # 添加缓冲
        buffer_calls = int(total_calls * 0.1)  # 10% 缓冲
        total_calls += buffer_calls
        
        return {
            'total_api_calls': total_calls,
            'estimated_points': total_calls,  # 每调用1点
            'estimated_time_min': total_time_min,
            'estimated_time_max': total_time_max,
            'estimated_time_formatted': f"{total_time_min}-{total_time_max} 分钟",
            'breakdown': breakdown,
            'note': f'基于 {estimated_stages} 个阶段预估，实际消耗可能因复杂度而异'
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
    
    def find_resumable_tasks(self, username: str = None) -> List[Dict]:
        """
        查找所有可以恢复的任务
        
        Args:
            username: 用户名（可选），如果提供则只查找该用户的项目
            
        Returns:
            可恢复任务列表，每个任务包含novel_title和creative_title用于匹配
        """
        resumable_tasks = []
        projects_dir = self.workspace_dir / "小说项目"
        
        if not projects_dir.exists():
            self.logger.warning(f"⚠️ 项目目录不存在: {projects_dir}")
            return resumable_tasks
        
        self.logger.info(f"🔍 开始扫描项目目录查找检查点...")
        if username:
            self.logger.info(f"  👤 指定用户: {username}")
        
        total_dirs = 0
        with_checkpoint = 0
        
        # 🔥 修复：支持用户隔离路径结构
        # 扫描路径列表：(项目目录, 用户名)
        scan_paths = []
        
        if username:
            # 如果指定了用户名，只扫描该用户的目录
            user_dir = projects_dir / username
            if user_dir.exists():
                scan_paths = [(project_dir, username) for project_dir in user_dir.iterdir() if project_dir.is_dir()]
        else:
            # 未指定用户名，扫描所有位置
            # 1. 首先扫描旧的非用户隔离路径（向后兼容）
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir() and not (project_dir / ".generation").exists() and project_dir.name != ".generation":
                    # 这可能是用户目录，跳过（会在下面扫描）
                    # 或者是一个没有检查点的旧项目目录
                    checkpoint_file = project_dir / ".generation" / "checkpoint.json"
                    if checkpoint_file.exists():
                        scan_paths.append((project_dir, None))
            
            # 2. 扫描用户隔离路径：小说项目/用户名/小说名/
            for user_dir in projects_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                # 检查这是否是一个用户目录（包含小说项目子目录）
                for project_dir in user_dir.iterdir():
                    if project_dir.is_dir():
                        scan_paths.append((project_dir, user_dir.name))
        
        self.logger.info(f"  📂 发现 {len(scan_paths)} 个项目目录需要检查")
        
        for project_dir, project_username in scan_paths:
            total_dirs += 1
            checkpoint_file = project_dir / ".generation" / "checkpoint.json"
            
            # 只有当 checkpoint.json 文件真正存在时才认为有检查点
            if checkpoint_file.exists() and checkpoint_file.is_file():
                with_checkpoint += 1
                self.logger.info(f"  📁 发现检查点: {project_dir.name} (用户: {project_username or 'unknown'})")
                
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        checkpoint_data = json.load(f)
                    
                    novel_title = checkpoint_data.get('novel_title', 'Unknown')
                    creative_title = checkpoint_data.get('creative_title', novel_title)
                    creative_seed_id = checkpoint_data.get('creative_seed_id')
                    checkpoint_username = checkpoint_data.get('username', project_username)
                    
                    self.logger.info(f"    novel_title: {novel_title}")
                    self.logger.info(f"    creative_title: {creative_title}")
                    self.logger.info(f"    username: {checkpoint_username}")
                    
                    # 使用原始目录名创建检查点管理器，传入正确的用户名
                    checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir, username=checkpoint_username)
                    # 强制使用实际存在的目录路径
                    checkpoint_mgr.checkpoint_dir = project_dir / ".generation"
                    checkpoint_mgr.checkpoint_file = checkpoint_file
                    
                    resume_info = checkpoint_mgr.get_resume_info()
                    
                    if resume_info:
                        # 添加映射信息，支持多种方式查找
                        resume_info['creative_title'] = creative_title
                        resume_info['creative_seed_id'] = creative_seed_id
                        resume_info['directory_name'] = project_dir.name
                        resume_info['username'] = checkpoint_username
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
                self.logger.debug(f"  📁 没有检查点文件: {project_dir.name}")
        
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
    
    def prepare_resume(self, novel_title: str, username: str = None) -> Optional[GenerationCheckpoint]:
        """
        准备恢复任务
        
        Args:
            novel_title: 要恢复的小说标题
            username: 用户名（可选），用于定位用户隔离路径下的检查点
            
        Returns:
            检查点管理器实例
        """
        # 🔥 修复：首先尝试使用指定的用户名查找
        if username:
            checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir, username=username)
            if checkpoint_mgr.can_resume():
                self.current_checkpoint = checkpoint_mgr
                self.logger.info(f"✅ 在用户 {username} 的路径下找到检查点: {novel_title}")
                return checkpoint_mgr
        
        # 如果没有指定用户名，或指定用户名下没有找到，尝试从所有可恢复任务中查找
        all_tasks = self.find_resumable_tasks()
        for task in all_tasks:
            if task.get('novel_title') == novel_title or task.get('creative_title') == novel_title:
                task_username = task.get('username')
                checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir, username=task_username)
                if checkpoint_mgr.can_resume():
                    self.current_checkpoint = checkpoint_mgr
                    self.logger.info(f"✅ 找到检查点: {novel_title} (用户: {task_username or 'unknown'})")
                    return checkpoint_mgr
        
        # 最后尝试不使用用户名（向后兼容旧路径）
        checkpoint_mgr = GenerationCheckpoint(novel_title, self.workspace_dir, username=None)
        if checkpoint_mgr.can_resume():
            self.current_checkpoint = checkpoint_mgr
            self.logger.info(f"✅ 在旧路径下找到检查点: {novel_title}")
            return checkpoint_mgr
        
        self.logger.warning(f"任务 {novel_title} 没有可用的检查点")
        return None
    
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