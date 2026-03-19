"""
计划持久化 - 负责阶段计划的保存和加载
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional
from src.utils.logger import get_logger


class StagePlanPersistence:
    """阶段计划持久化管理器"""
    
    def __init__(self, plans_dir_or_getter, novel_data_getter, logger_name: str = "StagePlanPersistence"):
        """
        初始化持久化管理器
        
        Args:
            plans_dir_or_getter: 计划保存的基础目录，或获取基础目录的函数
            novel_data_getter: 获取小说数据的函数
            logger_name: 日志名称
        """
        self._plans_dir = None
        self._plans_dir_getter = None
        
        # 支持传入路径或获取路径的函数
        if callable(plans_dir_or_getter):
            self._plans_dir_getter = plans_dir_or_getter
        else:
            self._plans_dir = plans_dir_or_getter
            
        self.get_novel_data = novel_data_getter
        self.logger = get_logger(logger_name)
    
    @property
    def plans_dir(self) -> Path:
        """动态获取 plans_dir"""
        if self._plans_dir_getter:
            return self._plans_dir_getter()
        return self._plans_dir
    
    def save_plan_to_file(self, stage_name: str, plan_data: Dict) -> Optional[Path]:
        """
        将阶段计划保存到JSON文件
        
        Args:
            stage_name: 阶段名称
            plan_data: 计划数据
            
        Returns:
            保存的文件路径，失败返回None
        """
        # 1. 规范化数据结构
        if "stage_writing_plan" in plan_data and isinstance(plan_data["stage_writing_plan"], dict):
            plan_content = plan_data["stage_writing_plan"]
            self.logger.info(f"  💾 (日志) 保存: 检测到 'stage_writing_plan' 包装器，使用其内部数据。")
        else:
            plan_content = plan_data
            self.logger.info(f"  💾 (日志) 保存: 未检测到 'stage_writing_plan' 包装器，直接使用传入数据。")
        
        # 2. 获取小说标题
        novel_data = self.get_novel_data()
        novel_title = novel_data.get("novel_title", "unknown")
        self.logger.info(f"  💾 (日志) 从计划数据中提取到的小说标题为: '{novel_title}'")
        
        if novel_title == "unknown":
            self.logger.warning(f"  ⚠️ 警告：无法从计划数据中提取到有效的小说标题，文件名将使用 'unknown'。")
        
        # 3. 构建小说项目目录路径
        safe_title = self._sanitize_filename(novel_title)
        novel_project_dir = self.plans_dir / safe_title
        plans_dir = novel_project_dir / "plans"
        
        # 4. 构建文件路径
        file_path = plans_dir / f"{safe_title}_{stage_name}_writing_plan.json"
        
        # 5. 准备要写入文件的数据
        if "stage_writing_plan" in plan_data:
            data_to_write = plan_data
        else:
            data_to_write = {"stage_writing_plan": plan_content}
        
        # 6. 执行保存操作（原子写入）
        try:
            os.makedirs(plans_dir, exist_ok=True)
            temp_path = file_path.with_suffix('.tmp')
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_write, f, ensure_ascii=False, indent=4)
            
            # 原子替换
            try:
                temp_path.replace(file_path)
            except Exception:
                os.replace(str(temp_path), str(file_path))
            
            self.logger.info(f"  💾 阶段计划已成功保存到: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"  ❌ 保存计划文件 '{file_path}' 失败: {e}")
            return None
    
    def load_plan_from_file(self, stage_name: str) -> Optional[Dict]:
        """
        从文件加载阶段计划
        
        Args:
            stage_name: 阶段名称
            
        Returns:
            加载的计划数据，失败返回None
        """
        self.logger.info(f"\n📂 (日志) 开始加载阶段 '{stage_name}' 的计划文件...")
        
        # 策略 1: 尝试使用标准命名约定加载
        self.logger.info(f"  - (1/2) 尝试使用标准命名约定加载...")
        
        novel_data = self.get_novel_data()
        novel_title = novel_data.get("novel_title", "unknown")
        self.logger.info(f"    - 用于构建路径的小说标题: '{novel_title}'")
        
        if novel_title == "unknown":
            self.logger.warning(f"    - ⚠️ 警告: 小说标题为 'unknown'，可能导致无法找到正确文件。")
        
        safe_title = self._sanitize_filename(novel_title)
        novel_project_dir = self.plans_dir / safe_title
        plans_dir = novel_project_dir / "plans"
        
        # 🔥 修复：如果 stage_name 不包含 '_stage'，尝试添加 '_stage' 后缀
        # 因为实际保存的文件名可能是 '{title}_opening_stage_writing_plan.json'
        # 但传入的 stage_name 可能是 'opening'
        if not stage_name.endswith("_stage"):
            stage_name_with_suffix = f"{stage_name}_stage"
        else:
            stage_name_with_suffix = stage_name
        
        # 尝试多种命名格式
        possible_filenames = [
            f"{safe_title}_{stage_name}_writing_plan.json",
            f"{safe_title}_{stage_name}_stage_writing_plan.json",
            f"{safe_title}_{stage_name_with_suffix}_writing_plan.json",
            f"{safe_title}_{stage_name_with_suffix}_stage_writing_plan.json"
        ]
        
        for filename in possible_filenames:
            expected_file_path = plans_dir / filename
            self.logger.info(f"    - 正在检查路径: {expected_file_path}")
            
            if expected_file_path.exists():
                try:
                    # 检查文件大小
                    if expected_file_path.stat().st_size == 0:
                        self.logger.error(f"    - ❌ 警告：文件 '{expected_file_path}' 为空（0字节），将被忽略。")
                        continue
                    
                    with open(expected_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.logger.info(f"    - ✅ 成功加载并解析文件: {filename}")
                        return data
                        
                except json.JSONDecodeError as e:
                    self.logger.error(f"    - ❌ 文件 '{expected_file_path}' 存在但JSON格式已损坏，解析失败: {e}")
                    continue
                except IOError as e:
                    self.logger.error(f"    - ❌ 文件 '{expected_file_path}' 存在但读取时发生IO错误: {e}")
                    continue
            else:
                self.logger.info(f"    - ℹ️ 文件未找到: {filename}")
        
        self.logger.info(f"    - ℹ️ 标准路径文件未找到（已尝试所有命名格式）。")
        
        # 策略 2: 尝试使用 novel_data 中记录的旧路径加载
        self.logger.info(f"  - (2/2) 尝试使用 novel_data 中的记录路径加载 (作为回退)...")
        
        path_info = novel_data.get("stage_writing_plans", {}).get(stage_name, {})
        if "path" in path_info and path_info["path"]:
            fallback_path_str = path_info["path"]
            fallback_file_path = Path(fallback_path_str)
            
            if not fallback_file_path.is_absolute():
                project_path = novel_data.get("project_path", Path.cwd())
                fallback_file_path = project_path / fallback_file_path
            
            self.logger.info(f"    - 在 novel_data 中找到记录路径: {fallback_file_path}")
            
            if fallback_file_path.exists():
                try:
                    if fallback_file_path.stat().st_size == 0:
                        self.logger.error(f"    - ❌ 警告：回退路径文件 '{fallback_file_path}' 为空，将被忽略。")
                        return None
                    
                    with open(fallback_file_path, 'r', encoding='utf-8') as f:
                        self.logger.info(f"    - ✅ 成功加载回退路径的文件。")
                        return json.load(f)
                        
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.error(f"    - ❌ 回退路径文件 '{fallback_file_path}' 存在但加载或解析失败: {e}")
                    return None
            else:
                self.logger.info(f"    - ℹ️ 回退路径文件未找到。")
        else:
            self.logger.info(f"    - ℹ️ 在 novel_data 中未找到 '{stage_name}' 的记录路径。")
        
        # 如果所有策略都失败
        self.logger.warning(f"  ⚠️ (日志) 加载失败: 未能从任何已知位置找到或加载 '{stage_name}' 的计划文件。")
        return None
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符，但保留中文标点符号（包括逗号）"""
        # 保留字母数字、空格、常用符号以及中文标点（包括逗号）
        safe = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']', '，', ',')).rstrip()
        return safe.replace(' ', '_')