# -*- coding: utf-8 -*-
"""
Strategic Planner
战略层规划器

一次性规划整部小说的战略框架（200章/50万字）
只定骨架，不定血肉
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StrategicPlanner:
    """
    战略层规划器
    
    职责：
    1. 规划关键转折点（里程碑）
    2. 确定主角成长路线
    3. 定义情绪节奏的大周期
    4. 确保200章不崩
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        
    def create_strategic_framework(
        self, 
        genre: str,
        novel_title: str,
        protagonist_name: str,
        total_chapters: int = 200,
        target_words: int = 500000
    ) -> Dict:
        """
        创建战略框架
        
        Args:
            genre: 题材
            novel_title: 书名
            protagonist_name: 主角名
            total_chapters: 总章节数
            target_words: 目标字数
            
        Returns:
            战略框架字典
        """
        logger.info(f"[StrategicPlanner] 创建战略框架: {novel_title} ({total_chapters}章)")
        
        # 如果API可用，使用AI生成；否则使用模板
        if self.api_client:
            return self._generate_with_ai(
                genre, novel_title, protagonist_name, 
                total_chapters, target_words
            )
        else:
            return self._generate_from_template(
                genre, novel_title, protagonist_name,
                total_chapters, target_words
            )
    
    def _generate_with_ai(
        self, genre: str, novel_title: str, protagonist_name: str,
        total_chapters: int, target_words: int
    ) -> Dict:
        """使用AI生成战略框架"""
        
        prompt = f"""# 角色：战略架构师

你为番茄爆款小说《{novel_title}》制定200章战略框架。

## 基本要求
- 总章节：{total_chapters}章
- 总字数：{target_words}字
- 题材：{genre}
- 主角：{protagonist_name}

## 需要规划的内容

### 1. 关键转折点（5-6个）
每个转折点包含：
- 章节位置
- 类型（身份曝光/地图切换/力量质变/文明跃迁/终极揭秘）
- 情绪基调
- 必须完成的目标

### 2. 主角成长阶段（4-5个）
每个阶段包含：
- 章节范围
- 身份称号
- 力量等级
- 核心能力
- 主要对手

### 3. 情绪大周期
- 整体情绪走向
- 高潮分布
- 缓冲区域

### 4. 核心悬念链
- 主线悬念（贯穿全书）
- 阶段悬念（每50章左右揭晓一个）

## 输出格式
JSON格式，包含：
- milestones: 转折点列表
- growth_stages: 成长阶段
- emotion_arc: 情绪大周期
- suspense_chain: 悬念链
- strategic_notes: 战略备注

只输出JSON，不要其他说明。"""

        try:
            response = self.api_client.generate_content(
                content_type="strategic_planning",
                user_prompt=prompt,
                temperature=0.5
            )
            
            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                return json.loads(response)
        except Exception as e:
            logger.warning(f"AI战略框架生成失败: {e}，使用模板")
        
        return self._generate_from_template(
            genre, novel_title, protagonist_name,
            total_chapters, target_words
        )
    
    def _generate_from_template(
        self, genre: str, novel_title: str, protagonist_name: str,
        total_chapters: int, target_words: int
    ) -> Dict:
        """从模板生成战略框架（国运文专用）"""
        
        return {
            "novel_title": novel_title,
            "protagonist_name": protagonist_name,
            "total_chapters": total_chapters,
            "target_words": target_words,
            "genre": genre,
            "milestones": [
                {
                    "chapter": 30,
                    "type": "身份跃迁",
                    "mood": "从被看不起到被崇拜",
                    "description": f"主角首次展现实力，获得'国运之子'称号，龙国排名登顶",
                    "must_achieve": ["实力震惊全球", "国家获得实质利益", "身份得到官方认可"]
                },
                {
                    "chapter": 60,
                    "type": "中高潮",
                    "mood": "领袖气质确立",
                    "description": "第一次国战，主角组建龙国联盟，对抗西方联盟",
                    "must_achieve": ["组建联盟", "击败敌国联军", "获得战略级资源"]
                },
                {
                    "chapter": 100,
                    "type": "大高潮",
                    "mood": "全球第一",
                    "description": "主角成为全球第一选手，解锁双模板融合能力",
                    "must_achieve": ["战力全球第一", "解锁新能力", "开启新地图"]
                },
                {
                    "chapter": 150,
                    "type": "文明跃迁",
                    "mood": "星际接触",
                    "description": "星际文明接触，地球晋级星际文明，主角成为地球代表",
                    "must_achieve": ["接触外星文明", "地球晋级", "主角成为代言"]
                },
                {
                    "chapter": 200,
                    "type": "终极揭秘",
                    "mood": "真相大白",
                    "description": "终极揭秘，主角成为星空主宰，掌控万界",
                    "must_achieve": ["揭秘禁地真相", "主角成为主宰", "圆满结局"]
                }
            ],
            "growth_stages": [
                {
                    "range": "1-30章",
                    "title": "崛起期",
                    "identity": "国运之子",
                    "power_level": "S级",
                    "core_ability": "单模板熟练",
                    "main_antagonist": "国内黑粉+小国选手"
                },
                {
                    "range": "31-60章",
                    "title": "扩张期",
                    "identity": "联盟领袖",
                    "power_level": "SS级",
                    "core_ability": "双模板切换",
                    "main_antagonist": "西方联盟"
                },
                {
                    "range": "61-100章",
                    "title": "称霸期",
                    "identity": "全球第一",
                    "power_level": "SSS级",
                    "core_ability": "双模板融合",
                    "main_antagonist": "隐藏势力"
                },
                {
                    "range": "101-150章",
                    "title": "星际期",
                    "identity": "地球代表",
                    "power_level": "星际级",
                    "core_ability": "法则掌控",
                    "main_antagonist": "外星文明"
                },
                {
                    "range": "151-200章",
                    "title": "主宰期",
                    "identity": "星空主宰",
                    "power_level": "神级",
                    "core_ability": "万界臣服",
                    "main_antagonist": "终极BOSS"
                }
            ],
            "emotion_arc": {
                "overall": "压抑→爆发→升华→圆满",
                "climax_distribution": "30/60/100/150/200章",
                "buffer_zones": ["31-35章", "61-65章", "101-105章", "151-155章"],
                "intensity_curve": [7, 8, 9, 10, 9]  # 五个阶段平均强度
            },
            "suspense_chain": {
                "main_suspense": "禁地的真相是什么？主角的身世之谜",
                "stage_suspenses": [
                    {"chapter": 30, "reveal": "系统的真正来源"},
                    {"chapter": 60, "reveal": "禁地背后的势力"},
                    {"chapter": 100, "reveal": "主角身世之谜"},
                    {"chapter": 150, "reveal": "星际文明的意图"},
                    {"chapter": 200, "reveal": "终极真相"}
                ]
            },
            "strategic_notes": [
                "前30章重点：建立爽点节奏，让读者入坑",
                "30-60章重点：提升格局，从个人到国家",
                "60-100章重点：全球争霸，民族情绪共振",
                "100-150章重点：文明跃迁，开阔世界观",
                "150-200章重点：圆满收官，所有悬念揭晓"
            ]
        }
    
    def validate_tactical_plan(
        self, 
        strategic_framework: Dict,
        tactical_plan: Dict,
        start_chapter: int,
        end_chapter: int
    ) -> List[str]:
        """
        验证战术规划是否符合战略框架
        
        Args:
            strategic_framework: 战略框架
            tactical_plan: 战术规划（30章详细规划）
            start_chapter: 起始章节
            end_chapter: 结束章节
            
        Returns:
            问题列表，如果为空则表示符合
        """
        issues = []
        
        # 1. 检查是否覆盖了关键的里程碑
        milestones = strategic_framework.get("milestones", [])
        for ms in milestones:
            ms_ch = ms["chapter"]
            if start_chapter <= ms_ch <= end_chapter:
                # 检查战术规划中是否有对应安排
                if not self._has_milestone_coverage(tactical_plan, ms_ch):
                    issues.append(f"第{ms_ch}章是关键转折点'{ms['type']}'，但战术规划未充分体现")
        
        # 2. 检查情绪强度是否符合战略
        expected_intensity = self._get_expected_intensity(
            strategic_framework, start_chapter, end_chapter
        )
        actual_intensity = self._calculate_avg_intensity(tactical_plan)
        
        if abs(actual_intensity - expected_intensity) > 1.5:
            issues.append(f"情绪强度偏差过大：期望{expected_intensity}，实际{actual_intensity}")
        
        return issues
    
    def _has_milestone_coverage(self, tactical_plan: Dict, chapter: int) -> bool:
        """检查战术规划是否覆盖了指定章节的关键事件"""
        chapters = tactical_plan.get("chapters", [])
        for ch in chapters:
            if ch.get("chapter_number") == chapter:
                return ch.get("is_key_event", False) or ch.get("intensity", 0) >= 9
        return False
    
    def _get_expected_intensity(
        self, framework: Dict, start: int, end: int
    ) -> float:
        """获取指定章节范围的期望情绪强度"""
        stages = framework.get("growth_stages", [])
        for stage in stages:
            range_str = stage["range"]
            s, e = map(int, range_str.replace("章", "").split("-"))
            if s <= start <= e or s <= end <= e:
                # 根据阶段返回期望强度
                if "崛起" in stage["title"]:
                    return 7.5
                elif "扩张" in stage["title"]:
                    return 8.0
                elif "称霸" in stage["title"]:
                    return 8.5
                elif "星际" in stage["title"]:
                    return 9.0
                elif "主宰" in stage["title"]:
                    return 9.5
        return 7.0
    
    def _calculate_avg_intensity(self, tactical_plan: Dict) -> float:
        """计算战术规划的平均情绪强度"""
        chapters = tactical_plan.get("chapters", [])
        if not chapters:
            return 0.0
        return sum(ch.get("intensity", 5) for ch in chapters) / len(chapters)


# 便捷函数
def create_strategic_framework(
    genre: str,
    novel_title: str,
    protagonist_name: str,
    api_client=None,
    total_chapters: int = 200
) -> Dict:
    """便捷函数：创建战略框架"""
    planner = StrategicPlanner(api_client)
    return planner.create_strategic_framework(
        genre, novel_title, protagonist_name, total_chapters
    )
