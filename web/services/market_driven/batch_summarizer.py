# -*- coding: utf-8 -*-
"""
BatchSummarizer - 批次总结器
每6章生成一次总结报告，用于下一轮规划和状态跟踪
"""

import json
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class BatchSummarizer:
    """
    批次总结器
    
    功能：
    1. 分析每批次生成的章节内容
    2. 提取关键事件、角色状态、剧情进展
    3. 生成结构化总结报告
    4. 支持多批次总结合并
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def summarize_batch(
        self,
        chapters: List[Dict],
        stage_goal: Dict = None,
        previous_summary: Dict = None
    ) -> Dict:
        """
        总结批次内容
        
        Args:
            chapters: 章节数据列表
            stage_goal: 当前阶段目标
            previous_summary: 前序总结（用于累积）
            
        Returns:
            总结字典
        """
        if not chapters:
            return self._empty_summary()
        
        chapter_nums = [c.get('chapter_number', 0) for c in chapters]
        start_ch = min(chapter_nums)
        end_ch = max(chapter_nums)
        
        # 统计信息
        total_words = sum(c.get('word_count', 0) for c in chapters)
        avg_quality = sum(c.get('quality_score', 0) for c in chapters) / len(chapters) if chapters else 0
        
        # 收集提取信息
        all_new_chars = []
        all_char_changes = []
        all_hooks = []
        key_events = []
        
        for ch in chapters:
            extracted = ch.get('extracted_info', {})
            
            # 新角色
            new_chars = extracted.get('new_characters', [])
            for char in new_chars:
                if char not in all_new_chars:
                    all_new_chars.append(char)
            
            # 角色变化
            changes = extracted.get('character_changes', [])
            all_char_changes.extend(changes)
            
            # 钩子
            hooks = extracted.get('new_hooks', [])
            all_hooks.extend(hooks)
            
            # 关键事件
            key_event = extracted.get('key_event')
            if key_event:
                key_events.append({
                    **key_event,
                    "chapter": ch.get('chapter_number')
                })
        
        # 计算阶段目标进度
        goal_id = stage_goal.get('goal_id', 'G1') if stage_goal else 'G1'
        goal_name = stage_goal.get('name', '未知目标') if stage_goal else '未知'
        progress = self._calculate_goal_progress(chapters, stage_goal, previous_summary)
        
        summary = {
            "batch_range": f"{start_ch}-{end_ch}",
            "chapter_count": len(chapters),
            "total_words": total_words,
            "average_quality": round(avg_quality, 1),
            "generated_at": datetime.now().isoformat(),
            
            # 阶段目标进度
            "current_goal": {
                "goal_id": goal_id,
                "goal_name": goal_name,
                "progress_percent": progress
            },
            "goal_progress": {goal_id: f"{progress}%"},
            
            # 内容摘要
            "content": {
                "new_characters": all_new_chars,
                "new_characters_count": len(all_new_chars),
                "character_changes": all_char_changes,
                "character_changes_count": len(all_char_changes),
                "new_hooks": all_hooks,
                "hooks_count": len(all_hooks),
                "key_events": key_events,
                "key_events_count": len(key_events)
            },
            
            # 角色状态快照
            "character_state": self._extract_character_state(chapters),
            
            # 备注
            "notes": f"第{start_ch}-{end_ch}章批次总结完成"
        }
        
        logger.info(f"[BatchSummarizer] 批次总结完成: 第{start_ch}-{end_ch}章, "
                   f"新角色{len(all_new_chars)}人, 关键事件{len(key_events)}个, "
                   f"目标进度{progress}%")
        
        return summary
    
    def _empty_summary(self) -> Dict:
        """返回空总结"""
        return {
            "batch_range": "",
            "chapter_count": 0,
            "total_words": 0,
            "average_quality": 0,
            "current_goal": {"goal_id": "", "goal_name": "", "progress_percent": 0},
            "goal_progress": {},
            "content": {
                "new_characters": [],
                "new_characters_count": 0,
                "character_changes": [],
                "character_changes_count": 0,
                "new_hooks": [],
                "hooks_count": 0,
                "key_events": [],
                "key_events_count": 0
            },
            "character_state": {},
            "notes": "空总结"
        }
    
    def _calculate_goal_progress(
        self, 
        chapters: List[Dict], 
        stage_goal: Dict,
        previous_summary: Dict
    ) -> int:
        """
        计算阶段目标进度
        
        基于：
        1. 已生成章节数占总章节比例
        2. 关键事件完成情况
        3. 前序进度累积
        """
        if not chapters:
            return 0
        
        # 基础进度（基于章节数）
        chapter_nums = [c.get('chapter_number', 0) for c in chapters]
        max_ch = max(chapter_nums) if chapter_nums else 0
        
        # 估算该阶段覆盖的章节范围（假设每个阶段约30-50章）
        stage_estimate = 40  # 每阶段约40章
        base_progress = min(int(max_ch / stage_estimate * 100), 100)
        
        # 如果有前序总结，累积进度
        if previous_summary:
            prev_progress_str = previous_summary.get('goal_progress', {}).get(
                stage_goal.get('goal_id', 'G1'), '0%'
            )
            try:
                prev_progress = int(prev_progress_str.replace('%', ''))
                # 增量更新（每批约增加10-15%）
                progress = min(prev_progress + 10, base_progress)
            except:
                progress = base_progress
        else:
            progress = base_progress
        
        return min(progress, 100)
    
    def _extract_character_state(self, chapters: List[Dict]) -> Dict:
        """提取角色状态快照"""
        state = {
            "protagonist": {},
            "allies": [],
            "enemies": []
        }
        
        if not chapters:
            return state
        
        # 取最后一章的提取信息作为当前状态
        last_ch = chapters[-1]
        extracted = last_ch.get('extracted_info', {})
        
        # 从角色变化中提取主角状态
        char_changes = extracted.get('character_changes', [])
        for change in char_changes:
            # 假设第一个变化通常是主角
            state['protagonist'] = {
                "name": change.get('name', '主角'),
                "status": change.get('change', ''),
                "details": change.get('details', '')
            }
            break
        
        # 新角色分类
        new_chars = extracted.get('new_characters', [])
        for char in new_chars:
            role = char.get('role', '')
            char_info = {
                "name": char.get('name', ''),
                "role": role,
                "power_level": char.get('power_level', '')
            }
            
            if '敌' in role or '反' in role or 'villain' in role.lower():
                state['enemies'].append(char_info)
            elif '友' in role or '盟' in role or 'ally' in role.lower():
                state['allies'].append(char_info)
        
        return state
    
    def merge_summaries(self, old_summary: Dict, new_summary: Dict) -> Dict:
        """
        合并两个总结（累积多批次信息）
        
        Args:
            old_summary: 旧总结
            new_summary: 新总结
            
        Returns:
            合并后的总结
        """
        if not old_summary:
            return new_summary
        if not new_summary:
            return old_summary
        
        merged = old_summary.copy()
        
        # 更新批次范围
        old_range = old_summary.get('batch_range', '').split('-')
        new_range = new_summary.get('batch_range', '').split('-')
        
        if len(old_range) == 2 and len(new_range) == 2:
            try:
                start = min(int(old_range[0]), int(new_range[0]))
                end = max(int(old_range[1]), int(new_range[1]))
                merged['batch_range'] = f"{start}-{end}"
            except:
                merged['batch_range'] = new_summary.get('batch_range', '')
        
        # 累积统计
        merged['chapter_count'] = old_summary.get('chapter_count', 0) + new_summary.get('chapter_count', 0)
        merged['total_words'] = old_summary.get('total_words', 0) + new_summary.get('total_words', 0)
        
        # 平均质量（加权平均）
        old_count = old_summary.get('chapter_count', 0)
        new_count = new_summary.get('chapter_count', 0)
        total_count = old_count + new_count
        if total_count > 0:
            old_quality = old_summary.get('average_quality', 0) * old_count
            new_quality = new_summary.get('average_quality', 0) * new_count
            merged['average_quality'] = round((old_quality + new_quality) / total_count, 1)
        
        # 合并内容列表
        old_content = old_summary.get('content', {})
        new_content = new_summary.get('content', {})
        
        # 合并新角色（去重）
        all_chars = {c.get('name'): c for c in old_content.get('new_characters', [])}
        for char in new_content.get('new_characters', []):
            name = char.get('name')
            if name and name not in all_chars:
                all_chars[name] = char
        merged['content']['new_characters'] = list(all_chars.values())
        merged['content']['new_characters_count'] = len(all_chars)
        
        # 合并角色变化
        merged['content']['character_changes'] = (
            old_content.get('character_changes', []) + 
            new_content.get('character_changes', [])
        )
        merged['content']['character_changes_count'] = len(merged['content']['character_changes'])
        
        # 合并钩子
        merged['content']['new_hooks'] = (
            old_content.get('new_hooks', []) + 
            new_content.get('new_hooks', [])
        )
        merged['content']['hooks_count'] = len(merged['content']['new_hooks'])
        
        # 合并关键事件
        merged['content']['key_events'] = (
            old_content.get('key_events', []) + 
            new_content.get('key_events', [])
        )
        merged['content']['key_events_count'] = len(merged['content']['key_events'])
        
        # 合并进度（取最新）
        old_progress = old_summary.get('goal_progress', {})
        new_progress = new_summary.get('goal_progress', {})
        merged['goal_progress'] = {**old_progress, **new_progress}
        
        # 更新当前目标
        merged['current_goal'] = new_summary.get('current_goal', old_summary.get('current_goal', {}))
        
        # 更新时间
        merged['updated_at'] = datetime.now().isoformat()
        merged['notes'] = f"累积总结: 第{merged['batch_range']}章, 共{merged['chapter_count']}章"
        
        logger.info(f"[BatchSummarizer] 总结合并完成: 累积{merged['chapter_count']}章")
        
        return merged
