# -*- coding: utf-8 -*-
"""
Hierarchical Planner
分层规划管理器

整合战略层和战术层，提供统一的规划接口
"""

import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .strategic_planner import StrategicPlanner
from .tactical_planner import TacticalPlanner
from .config import get_config

logger = logging.getLogger(__name__)


class HierarchicalPlanner:
    """
    分层规划管理器
    
    架构：
    - 战略层：一次性规划200章骨架（关键转折点、成长阶段、悬念链）
    - 战术层：每30章滚动规划详细情绪曲线
    - 执行层：每6章批量生成正文
    
    使用方式：
    1. 初始化时创建战略框架
    2. 每批次生成前调用战术规划
    3. 根据实际效果动态调整
    """
    
    def __init__(
        self,
        genre: str,
        novel_title: str,
        protagonist_name: str,
        api_client=None,
        project_path: Path = None,
        total_chapters: int = None,
        target_words: int = None
    ):
        """
        初始化分层规划器
        
        Args:
            genre: 题材
            novel_title: 书名
            protagonist_name: 主角名
            api_client: API客户端
            project_path: 项目路径
            total_chapters: 总章节数（默认从配置读取）
            target_words: 目标字数（默认从配置读取）
        """
        self.genre = genre
        self.novel_title = novel_title
        self.protagonist_name = protagonist_name
        self.api_client = api_client
        self.project_path = project_path
        
        # 加载配置
        config = get_config(genre)
        self.total_chapters = total_chapters or config["chapters"]
        self.target_words = target_words or config["target_words"]
        self.tactical_window = config["planning"]["tactical_window"]
        self.tactical_overlap = config["planning"]["tactical_overlap"]
        
        # 初始化规划器
        self.strategic_planner = StrategicPlanner(api_client)
        self.tactical_planner = None  # 延迟初始化（需要strategic_framework）
        
        # 状态
        self.strategic_framework = None
        self.current_tactical_plan = None
        self.generated_chapters_count = 0
        
        logger.info(f"[HierarchicalPlanner] 初始化: {novel_title} ({self.total_chapters}章)")
    
    def initialize(self) -> Dict:
        """
        初始化战略框架
        
        Returns:
            战略框架
        """
        logger.info("[HierarchicalPlanner] 创建战略框架...")
        
        self.strategic_framework = self.strategic_planner.create_strategic_framework(
            genre=self.genre,
            novel_title=self.novel_title,
            protagonist_name=self.protagonist_name,
            total_chapters=self.total_chapters,
            target_words=self.target_words
        )
        
        # 初始化战术规划器
        self.tactical_planner = TacticalPlanner(
            api_client=self.api_client,
            strategic_framework=self.strategic_framework,
            project_path=self.project_path
        )
        
        logger.info("[HierarchicalPlanner] 战略框架创建完成")
        return self.strategic_framework
    
    def get_next_batch_plan(self, batch_size: int = 6) -> Tuple[Dict, Dict]:
        """
        获取下一批次的规划
        
        Args:
            batch_size: 批次大小（默认6章）
            
        Returns:
            (tactical_plan, strategic_context)
            - tactical_plan: 战术规划（详细情绪曲线）
            - strategic_context: 战略上下文（当前阶段信息等）
        """
        if not self.strategic_framework:
            raise RuntimeError("必须先调用initialize()初始化战略框架")
        
        # 计算批次范围
        start_ch = self.generated_chapters_count + 1
        end_ch = min(start_ch + batch_size - 1, self.total_chapters)
        
        # 检查是否需要新的战术规划（每30章或首次）
        if self._need_new_tactical_plan(start_ch):
            logger.info(f"[HierarchicalPlanner] 规划第{start_ch}-{start_ch + self.tactical_window - 1}章战术...")
            
            # 获取前一阶段摘要
            previous_summary = self._get_previous_summary()
            
            # 生成战术规划
            self.current_tactical_plan = self.tactical_planner.plan_next_batch(
                start_chapter=start_ch,
                end_chapter=min(start_ch + self.tactical_window - 1, self.total_chapters),
                novel_title=self.novel_title,
                protagonist_name=self.protagonist_name,
                previous_summary=previous_summary
            )
        
        # 提取当前批次的战术
        batch_tactical = self._extract_batch_tactical(
            self.current_tactical_plan, start_ch, end_ch
        )
        
        # 获取战略上下文
        strategic_context = self._get_strategic_context(start_ch)
        
        return batch_tactical, strategic_context
    
    def update_progress(self, generated_chapters: List[Dict]):
        """
        更新生成进度
        
        Args:
            generated_chapters: 已生成的章节列表
        """
        count = len(generated_chapters)
        self.generated_chapters_count += count
        
        # 更新战术规划器
        if self.tactical_planner:
            self.tactical_planner.update_generated_chapters(generated_chapters)
        
        logger.info(f"[HierarchicalPlanner] 进度更新: {self.generated_chapters_count}/{self.total_chapters}章")
    
    def _need_new_tactical_plan(self, start_ch: int) -> bool:
        """判断是否需要新的战术规划"""
        if not self.current_tactical_plan:
            return True
        
        # 检查当前规划是否还能覆盖后续批次
        batch_info = self.current_tactical_plan.get("batch_info", {})
        planned_end = batch_info.get("end_chapter", 0)
        
        # 如果当前批次超出已规划范围，需要新规划
        return start_ch + 5 > planned_end  # 预留5章缓冲
    
    def _get_previous_summary(self) -> str:
        """获取前一阶段的摘要"""
        if self.generated_chapters_count == 0:
            return ""
        
        # 简化摘要：返回最近几章的关键信息
        recent = self.tactical_planner.generated_chapters[-5:] if self.tactical_planner else []
        if not recent:
            return ""
        
        summaries = []
        for ch in recent:
            summaries.append(f"第{ch.get('chapter_number')}章: {ch.get('emotion', '未知')}({ch.get('intensity', 0)})")
        
        return "; ".join(summaries)
    
    def _extract_batch_tactical(self, tactical_plan: Dict, start: int, end: int) -> Dict:
        """从战术规划中提取指定批次的内容"""
        all_chapters = tactical_plan.get("chapters", [])
        batch_chapters = [
            ch for ch in all_chapters 
            if start <= ch.get("chapter_number", 0) <= end
        ]
        
        return {
            "batch_info": {
                "start_chapter": start,
                "end_chapter": end,
                "stage": tactical_plan.get("batch_info", {}).get("stage", "未知")
            },
            "chapters": batch_chapters
        }
    
    def _get_strategic_context(self, current_ch: int) -> Dict:
        """获取战略上下文"""
        if not self.strategic_framework:
            return {}
        
        # 当前阶段
        current_stage = {}
        for stage in self.strategic_framework.get("growth_stages", []):
            range_str = stage.get("range", "")
            try:
                s, e = map(int, range_str.replace("章", "").split("-"))
                if s <= current_ch <= e:
                    current_stage = stage
                    break
            except:
                continue
        
        # 下一个里程碑
        next_milestone = None
        for ms in self.strategic_framework.get("milestones", []):
            if ms.get("chapter", 0) > current_ch:
                next_milestone = ms
                break
        
        # 整体进度
        progress = (current_ch / self.total_chapters) * 100
        
        return {
            "current_stage": current_stage,
            "next_milestone": next_milestone,
            "overall_progress": round(progress, 1),
            "remaining_chapters": self.total_chapters - current_ch + 1
        }
    
    def get_progress(self) -> Dict:
        """获取当前进度信息"""
        return {
            "total_chapters": self.total_chapters,
            "generated_chapters": self.generated_chapters_count,
            "remaining_chapters": self.total_chapters - self.generated_chapters_count,
            "progress_percent": round((self.generated_chapters_count / self.total_chapters) * 100, 1),
            "current_stage": self._get_strategic_context(self.generated_chapters_count).get("current_stage", {}),
            "next_milestone": self._get_strategic_context(self.generated_chapters_count).get("next_milestone")
        }


# 便捷函数
def create_hierarchical_planner(
    genre: str,
    novel_title: str,
    protagonist_name: str,
    api_client=None,
    project_path: Path = None
) -> HierarchicalPlanner:
    """便捷函数：创建分层规划器"""
    planner = HierarchicalPlanner(
        genre, novel_title, protagonist_name,
        api_client, project_path
    )
    planner.initialize()
    return planner
