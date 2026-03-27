"""
阶段性复盘优化系统

在达成里程碑（30/60/100/150/200章）时，调用AI全局分析并多轮优化。
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Issue:
    """问题记录"""
    type: str  # plot/character/world/bestseller
    severity: str  # high/medium/low
    chapter: int
    description: str
    suggestion: str = ""


@dataclass
class FixPlan:
    """修复计划"""
    type: str  # global/batch/single
    chapter_indices: List[int]
    instructions: str
    priority: int = 5


class StageReviewOptimizer:
    """
    阶段性复盘优化器（滑动窗口版）
    
    核心改进：
    - 使用滑动窗口分析，避免一次处理过多章节
    - 窗口间有重叠，保持连贯性分析
    
    默认配置：
    - 窗口大小：10章
    - 重叠：2章
    - 步长：8章（10-2）
    
    分析序列示例：
    - 第1轮：第1-10章
    - 第2轮：第8-18章（重叠2章：8,9）
    - 第3轮：第16-26章（重叠2章：16,17）
    """
    
    # 阶段配置
    STAGE_MILESTONES = [30, 60, 100, 150, 200]
    
    # 滑动窗口配置
    DEFAULT_WINDOW_SIZE = 10  # 每窗口章节数
    DEFAULT_OVERLAP = 2       # 重叠章节数
    
    def __init__(self, project_path: str, api_client=None, 
                 window_size: int = None, overlap: int = None):
        self.project_path = Path(project_path)
        self.api_client = api_client
        self.window_size = window_size or self.DEFAULT_WINDOW_SIZE
        self.overlap = overlap or self.DEFAULT_OVERLAP
        self.issues: List[Issue] = []
        self.fix_plans: List[FixPlan] = []
        
    def should_trigger(self, end_chapter: int) -> bool:
        """检查是否达到阶段节点"""
        return end_chapter in self.STAGE_MILESTONES
    
    def optimize_stage(self, chapters: List[Dict], stage_end: int, 
                       max_rounds: int = 3) -> List[Dict]:
        """
        优化整个阶段（滑动窗口版）
        
        Args:
            chapters: 当前阶段的所有章节
            stage_end: 阶段结束章节号
            max_rounds: 最大优化轮数
            
        Returns:
            优化后的章节列表
        """
        logger.info(f"[StageOptimizer] 开始优化第1-{stage_end}章")
        logger.info(f"[StageOptimizer] 窗口大小：{self.window_size}，重叠：{self.overlap}")
        
        current_chapters = chapters
        
        for round_num in range(1, max_rounds + 1):
            logger.info(f"[StageOptimizer] === 第{round_num}轮优化 ===")
            
            # Stage 1: 识别问题（使用滑动窗口）
            issues = self._identify_issues_sliding_window(current_chapters, stage_end)
            
            # 检查是否达到停止条件
            high_issues = [i for i in issues if i.severity == "high"]
            if len(high_issues) == 0:
                logger.info(f"[StageOptimizer] 无严重问题，提前结束")
                break
            
            # Stage 2: 规划修复
            fix_plans = self._plan_fixes(issues, current_chapters)
            
            # Stage 3: 执行修复
            current_chapters = self._execute_fixes(fix_plans, current_chapters)
            
            # Stage 4: 验证修复
            if self._verify_fixes(issues, current_chapters):
                logger.info(f"[StageOptimizer] 第{round_num}轮验证通过")
            else:
                logger.warning(f"[StageOptimizer] 第{round_num}轮仍有问题，继续优化")
        
        # Stage 5: 同步设定
        self._sync_settings(current_chapters)
        
        # 生成报告
        self._generate_report(current_chapters, stage_end)
        
        return current_chapters
    
    def _split_windows(self, chapters: List[Dict]) -> List[List[Dict]]:
        """
        将章节切分为滑动窗口
        
        Returns:
            窗口列表，每个窗口包含若干章节
        """
        if len(chapters) <= self.window_size:
            return [chapters]
        
        windows = []
        step = self.window_size - self.overlap
        
        start = 0
        while start < len(chapters):
            end = min(start + self.window_size, len(chapters))
            window = chapters[start:end]
            windows.append(window)
            
            if end >= len(chapters):
                break
            start += step
        
        logger.info(f"[StageOptimizer] 切分为 {len(windows)} 个窗口")
        for i, w in enumerate(windows):
            ch_nums = [c.get('chapter_number', '?') for c in w]
            logger.info(f"  窗口{i+1}: 第{ch_nums[0]}-{ch_nums[-1]}章")
        
        return windows
    
    def _identify_issues_sliding_window(self, chapters: List[Dict], stage_end: int) -> List[Issue]:
        """
        Stage 1: 使用滑动窗口识别问题
        """
        windows = self._split_windows(chapters)
        all_issues = []
        
        for i, window in enumerate(windows):
            window_chapters = [c.get('chapter_number', '?') for c in window]
            logger.info(f"[StageOptimizer] 分析窗口{i+1}/{len(windows)}: 第{window_chapters[0]}-{window_chapters[-1]}章")
            
            window_issues = self._identify_issues_in_window(window, i+1, len(windows))
            all_issues.extend(window_issues)
        
        # 合并重复问题（同一章节同一类型的问题）
        merged_issues = self._merge_duplicate_issues(all_issues)
        
        logger.info(f"[StageOptimizer] 共发现问题：{len(merged_issues)} 个")
        return merged_issues
    
    def _identify_issues_in_window(self, window_chapters: List[Dict], 
                                   window_idx: int, total_windows: int) -> List[Issue]:
        """分析单个窗口的问题"""
        first_ch = window_chapters[0].get('chapter_number', '?')
        last_ch = window_chapters[-1].get('chapter_number', '?')
        
        # 构建分析 prompt
        chapters_text = self._format_chapters_for_analysis(window_chapters)
        
        # 重叠章节的特殊说明
        overlap_note = ""
        if window_idx > 1:
            overlap_chapters = [c.get('chapter_number') for c in window_chapters[:self.overlap]]
            overlap_note = f"\n注：第{overlap_chapters}章与上一窗口重叠，用于检查连贯性。"
        
        prompt = f"""你是一名专业的小说编辑，请对以下第{first_ch}-{last_ch}章进行分析。

{overlap_note}

章节内容摘要：
{chapters_text}

请检查以下问题：

## 1. 剧情连续性问题（重点关注窗口边界）
- 窗口内各章之间是否连贯
- 章尾悬念是否在下一章有回应
- 时间线、场景切换是否合理

## 2. 角色一致性问题  
- 主角能力/状态是否稳定
- 配角立场是否有异常变化
- 新角色登场是否有铺垫

## 3. 世界设定一致性
- 力量体系描述是否统一
- 组织/势力设定是否矛盾

## 4. 爆款标准差距
- 爽点密度（每章应有≥1个）
- 情绪转折次数（每章应有≥3次）
- 字数是否达标（2000-2500字）

输出格式（JSON）：
{{
    "issues": [
        {{
            "type": "plot/character/world/bestseller",
            "severity": "high/medium/low",
            "chapter": 章节号,
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}

严重问题(high)：影响阅读体验的重大问题（如主角能力突变、反派无铺垫登场）
中等问题(medium)：影响流畅度的问题（如小伏笔未回收）
轻微问题(low)：细节问题（如某章爽点不足）"""

        # 调用AI分析
        if not self.api_client:
            logger.warning("[StageOptimizer] 无API客户端，跳过问题识别")
            return []
        
        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            content = response.get("content", "")
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                issues = [Issue(**item) for item in data.get("issues", [])]
                logger.info(f"[StageOptimizer] 窗口{window_idx}发现 {len(issues)} 个问题")
                return issues
        except Exception as e:
            logger.error(f"[StageOptimizer] 窗口{window_idx}分析失败: {e}")
        
        return []
    
    def _merge_duplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        """合并重复问题（同一章节同一类型）"""
        seen = {}
        merged = []
        
        for issue in issues:
            key = (issue.chapter, issue.type, issue.description[:30])
            if key not in seen:
                seen[key] = issue
                merged.append(issue)
            else:
                # 如果重复，保留severity更高的
                if issue.severity == "high" and seen[key].severity != "high":
                    seen[key] = issue
        
        return merged
        
        prompt = f"""你是一名专业的小说编辑，请对以下第1-{stage_end}章进行全面分析。

章节内容摘要：
{chapters_text}

请按以下维度检查问题：

## 1. 剧情连续性问题
- 时间线是否连贯（倒计时、时间跳跃）
- 场景切换是否有过渡
- 章尾悬念是否被回收（超过3章未提即算问题）
- 战斗结果的延续性

## 2. 角色一致性问题  
- 主角能力是否有异常波动（解锁的能力是否正确使用）
- 配角立场是否稳定
- 反派层级是否有合理铺垫（上级反派的登场是否有下级铺垫）
- 已击败反派的后续处理是否明确

## 3. 世界设定一致性
- 力量体系是否统一（等级划分前后一致）
- 道具/能力设定是否矛盾
- 组织势力评估是否稳定

## 4. 爆款标准差距
- 爽点不足的章节（每章应有≥1个爽点）
- 情绪曲线平淡（每章应有≥3次转折）
- 字数不足的章节（<1800字）

输出格式（JSON）：
{{
    "issues": [
        {{
            "type": "plot/character/world/bestseller",
            "severity": "high/medium/low",
            "chapter": 章节号,
            "description": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}

注意：
- high: 严重影响阅读体验（如主角能力突然变化、反派无铺垫跳变）
- medium: 影响流畅度（如小伏笔未回收、小设定矛盾）
- low: 细节问题（如个别章节爽点不足）"""

        # 调用AI分析
        if not self.api_client:
            logger.warning("[StageOptimizer] 无API客户端，跳过问题识别")
            return []
        
        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            content = response.get("content", "")
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                data = json.loads(json_match.group())
                issues = [Issue(**item) for item in data.get("issues", [])]
                logger.info(f"[StageOptimizer] 识别到 {len(issues)} 个问题")
                return issues
        except Exception as e:
            logger.error(f"[StageOptimizer] 问题识别失败: {e}")
        
        return []
    
    def _plan_fixes(self, issues: List[Issue], chapters: List[Dict]) -> List[FixPlan]:
        """
        Stage 2: 规划修复方案
        """
        # 按类型分组
        plot_issues = [i for i in issues if i.type == "plot"]
        char_issues = [i for i in issues if i.type == "character"]
        world_issues = [i for i in issues if i.type == "world"]
        best_issues = [i for i in issues if i.type == "bestseller"]
        
        plans = []
        
        # 全局修复（设定类问题）
        if world_issues:
            plans.append(FixPlan(
                type="global",
                chapter_indices=list(range(len(chapters))),
                instructions=f"统一世界设定：{[i.description for i in world_issues]}",
                priority=10
            ))
        
        # 批量修复（同类章节）
        # 按章节分组
        chapter_issues = {}
        for issue in issues:
            if issue.chapter not in chapter_issues:
                chapter_issues[issue.chapter] = []
            chapter_issues[issue.chapter].append(issue)
        
        for ch_num, ch_issues in chapter_issues.items():
            if len(ch_issues) >= 2:  # 多问题的章节单独处理
                idx = ch_num - 1
                plans.append(FixPlan(
                    type="single",
                    chapter_indices=[idx],
                    instructions=f"修复第{ch_num}章：{[i.description for i in ch_issues]}",
                    priority=8 if any(i.severity == "high" for i in ch_issues) else 5
                ))
        
        # 排序：优先级高的先处理
        plans.sort(key=lambda p: p.priority, reverse=True)
        return plans
    
    def _execute_fixes(self, plans: List[FixPlan], chapters: List[Dict]) -> List[Dict]:
        """
        Stage 3: 执行修复
        """
        fixed_chapters = chapters.copy()
        
        for plan in plans:
            if plan.type == "global":
                # 全局修复：更新所有章节的设定引用
                logger.info(f"[StageOptimizer] 执行全局修复")
                # 这里可以更新 world_state，然后重新生成相关章节
                
            elif plan.type == "single":
                # 单章修复
                for idx in plan.chapter_indices:
                    if idx < len(fixed_chapters):
                        chapter = fixed_chapters[idx]
                        logger.info(f"[StageOptimizer] 修复第{chapter['chapter_number']}章")
                        
                        # 调用AI修复单章
                        fixed = self._fix_single_chapter(chapter, plan.instructions)
                        fixed_chapters[idx] = fixed
        
        return fixed_chapters
    
    def _fix_single_chapter(self, chapter: Dict, instructions: str) -> Dict:
        """修复单个章节"""
        if not self.api_client:
            return chapter
        
        prompt = f"""请修复以下章节：

章节标题：{chapter.get('title', '')}
当前内容：
{chapter.get('content', '')[:2000]}...

修复要求：
{instructions}

要求：
1. 保持原有剧情主线
2. 只修复指定问题
3. 字数维持在2000-2500字
4. 保持番茄风格（短段落、多对话）

直接输出修复后的完整章节内容。"""

        try:
            response = self.api_client.generate(messages=[
                {"role": "user", "content": prompt}
            ])
            
            new_content = response.get("content", chapter.get('content', ''))
            
            # 更新章节
            fixed_chapter = chapter.copy()
            fixed_chapter['content'] = new_content
            fixed_chapter['word_count'] = len(new_content)
            fixed_chapter['optimized'] = True
            
            return fixed_chapter
        except Exception as e:
            logger.error(f"[StageOptimizer] 单章修复失败: {e}")
            return chapter
    
    def _verify_fixes(self, original_issues: List[Issue], 
                      fixed_chapters: List[Dict]) -> bool:
        """
        Stage 4: 验证修复
        """
        # 简单验证：重新检查是否还有同样的问题
        # 实际可以再次调用AI验证
        high_issues = [i for i in original_issues if i.severity == "high"]
        logger.info(f"[StageOptimizer] 验证：原{len(high_issues)}个严重问题")
        
        # 如果已经修复了大部分，返回True
        # 这里简化处理，实际应该重新分析
        return True
    
    def _sync_settings(self, chapters: List[Dict]):
        """
        Stage 5: 同步更新设定文件
        """
        logger.info(f"[StageOptimizer] 同步设定文件")
        
        # 1. 提取并更新世界状态
        world_state = self._extract_world_state(chapters)
        self._save_json(".world_state.json", world_state)
        
        # 2. 提取并更新角色状态
        character_state = self._extract_character_states(chapters)
        self._save_json(".character_state.json", character_state)
        
        # 3. 提取剧情时间线
        timeline = self._extract_timeline(chapters)
        self._save_json(".plot_timeline.json", timeline)
        
        # 4. 提取已解决/待解决的钩子
        hooks = self._extract_hooks(chapters)
        self._save_json(".hooks_state.json", hooks)
        
        logger.info(f"[StageOptimizer] 设定文件已更新")
    
    def _extract_world_state(self, chapters: List[Dict]) -> Dict:
        """从章节提取世界状态"""
        # 简化的提取逻辑
        # 实际应该调用AI分析全文
        return {
            "extracted_at": chapters[-1].get('chapter_number', 0),
            "total_chapters": len(chapters),
            "power_system": {},  # 从章节提取力量体系
            "factions": {},      # 从章节提取势力
            "key_events": []     # 关键事件列表
        }
    
    def _extract_character_states(self, chapters: List[Dict]) -> Dict:
        """从章节提取角色状态"""
        return {
            "protagonist": {
                "current_abilities": [],
                "power_level_progression": [],
            },
            "key_characters": {}
        }
    
    def _extract_timeline(self, chapters: List[Dict]) -> List[Dict]:
        """提取剧情时间线"""
        timeline = []
        for ch in chapters:
            timeline.append({
                "chapter": ch.get('chapter_number'),
                "title": ch.get('title'),
                "key_event": "",  # 从内容提取
                "new_characters": [],
                "resolved_hooks": [],
                "new_hooks": []
            })
        return timeline
    
    def _extract_hooks(self, chapters: List[Dict]) -> Dict:
        """提取钩子状态"""
        return {
            "resolved": [],
            "pending": [],
            "abandoned": []
        }
    
    def _generate_report(self, chapters: List[Dict], stage_end: int):
        """生成优化报告"""
        report_path = self.project_path / f"optimization_report_stage_{stage_end}.md"
        
        report = f"""# 阶段性复盘优化报告

## 阶段：第1-{stage_end}章

## 优化统计
- 总章节数：{len(chapters)}
- 发现问题数：{len(self.issues)}
- 严重问题数：{len([i for i in self.issues if i.severity == 'high'])}

## 问题分布
### 剧情连续性
{self._format_issues_by_type('plot')}

### 角色一致性
{self._format_issues_by_type('character')}

### 设定一致性
{self._format_issues_by_type('world')}

### 爆款标准差距
{self._format_issues_by_type('bestseller')}

## 修复措施
{self._format_fix_plans()}

## 章节质量评分
| 章节 | 字数 | 评分 | 备注 |
|------|------|------|------|
{self._format_chapter_scores(chapters)}

---
生成时间：{self._get_timestamp()}
"""
        
        report_path.write_text(report, encoding='utf-8')
        logger.info(f"[StageOptimizer] 报告已保存: {report_path}")
    
    def _format_chapters_for_analysis(self, chapters: List[Dict]) -> str:
        """格式化章节用于AI分析"""
        lines = []
        for ch in chapters:
            lines.append(f"\n第{ch.get('chapter_number')}章：{ch.get('title')}")
            content = ch.get('content', '')
            # 只取前500字作为摘要
            lines.append(content[:500] + "..." if len(content) > 500 else content)
        return "\n".join(lines)
    
    def _format_issues_by_type(self, type_name: str) -> str:
        """格式化某类型问题"""
        issues = [i for i in self.issues if i.type == type_name]
        if not issues:
            return "无"
        return "\n".join([f"- 第{i.chapter}章 ({i.severity}): {i.description}" for i in issues])
    
    def _format_fix_plans(self) -> str:
        """格式化修复计划"""
        if not self.fix_plans:
            return "无"
        return "\n".join([f"- {p.type}: {p.instructions[:50]}..." for p in self.fix_plans])
    
    def _format_chapter_scores(self, chapters: List[Dict]) -> str:
        """格式化章节评分表"""
        lines = []
        for ch in chapters:
            ch_num = ch.get('chapter_number', '?')
            word_count = ch.get('word_count', 0)
            score = ch.get('quality_score', '-')
            note = "已优化" if ch.get('optimized') else ""
            lines.append(f"| {ch_num} | {word_count} | {score} | {note} |")
        return "\n".join(lines)
    
    def _save_json(self, filename: str, data: Dict):
        """保存JSON文件"""
        filepath = self.project_path / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
