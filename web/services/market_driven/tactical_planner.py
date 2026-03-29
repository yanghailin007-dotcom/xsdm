"""
Tactical Planner
战术层规划器

每30章滚动规划详细情绪曲线
基于已生成内容动态调整，与阶段目标对齐
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class TacticalPlanner:
    """
    战术层规划器
    
    职责：
    1. 每30章详细规划情绪曲线
    2. 基于前序总结动态调整
    3. 与阶段目标对齐
    4. 保证章节间连贯性
    """
    
    DEFAULT_WINDOW = 30      # 每次规划30章
    
    def __init__(
        self, 
        api_client=None,
        project_path: Path = None
    ):
        self.api_client = api_client
        self.project_path = project_path
        self.generated_chapters = []  # 已生成章节记录
        
    def plan_next_batch(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,           # ← 新增：当前阶段目标
        previous_summary: Dict = None,  # ← 新增：前序总结
        emotion_curve: List[Dict] = None,  # ← 新增：一阶段情绪曲线（200章）
        bestseller_analysis: Dict = None   # ← 新增：爆款分析数据
    ) -> Dict:
        """
        规划下一批章节
        
        Args:
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            novel_title: 书名
            protagonist_name: 主角名
            stage_goal: 当前阶段目标（来自WorldBuilder）
            previous_summary: 前序批次总结
            emotion_curve: 一阶段生成的200章情绪曲线（用于确保战术规划符合爆款设计）
            bestseller_analysis: 爆款分析数据（钩子公式、爽点模式等）
            
        Returns:
            战术规划字典
        """
        logger.info(f"[TacticalPlanner] 规划第{start_chapter}-{end_chapter}章 | 阶段目标: {stage_goal.get('goal_id', 'Unknown')}")
        
        # 🔥 提取当前窗口对应的一阶段情绪设计
        window_emotion_design = []
        if emotion_curve:
            window_emotion_design = [
                point for point in emotion_curve 
                if start_chapter <= point.get('chapter', 0) <= end_chapter
            ]
            logger.info(f"[TacticalPlanner] 加载窗口情绪设计: {len(window_emotion_design)}章")
        
        # 生成战术规划
        if self.api_client:
            tactical_plan = self._generate_with_ai(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_goal, previous_summary,
                window_emotion_design, bestseller_analysis
            )
        else:
            tactical_plan = self._generate_from_template(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_goal, previous_summary,
                window_emotion_design, bestseller_analysis
            )
        
        return tactical_plan
    
    def _generate_with_ai(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> Dict:
        """使用AI生成战术规划"""
        
        # 构建提示词
        prompt = self._build_tactical_prompt(
            start_chapter, end_chapter,
            novel_title, protagonist_name,
            stage_goal, previous_summary,
            window_emotion_design, bestseller_analysis
        )
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_planning",
                user_prompt=prompt,
                temperature=0.7,
                purpose="生成战术规划"
            )
            
            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                return json.loads(response)
        except Exception as e:
            logger.warning(f"AI战术规划生成失败: {e}，使用模板")
        
        return self._generate_from_template(
            start_chapter, end_chapter,
            novel_title, protagonist_name,
            stage_goal, previous_summary
        )
    
    def _build_tactical_prompt(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> str:
        """构建战术规划提示词"""
        
        # 前序总结部分
        summary_text = ""
        if previous_summary:
            summary_text = f"""
## 前序总结（必须承接）

### 已发生关键事件
{chr(10).join([f"- 第{e.get('chapter', '?')}章: {e.get('event', '')}" for e in previous_summary.get('completed_events', [])[:5]])}

### 角色当前状态
- 主角扮演度: {previous_summary.get('character_states', {}).get('protagonist', {}).get('扮演度', '未知')}
- 主角已解锁能力: {', '.join(previous_summary.get('character_states', {}).get('protagonist', {}).get('新技能', []))}
- 队友态度: {previous_summary.get('character_states', {}).get('ally', {}).get('态度', '未知')}

### 待回收伏笔（必须优先处理）
{chr(10).join([f"- [{h.get('priority', 'medium')}] 第{h.get('chapter', '?')}章埋下: {h.get('content', '')}" for h in previous_summary.get('pending_hooks', [])[:3]])}

### 阶段目标完成度
{previous_summary.get('goal_progress', {}).get(stage_goal.get('goal_id', ''), '未知')}
"""
        else:
            summary_text = "## 前序总结\n这是开局第一批，无前置内容。"
        
        # 🔥 构建爆款设计参考部分
        bestseller_ref = ""
        if window_emotion_design or bestseller_analysis:
            bestseller_parts = ["## 爆款设计参考（必须遵循）\n"]
            
            # 添加窗口情绪设计
            if window_emotion_design:
                bestseller_parts.append("### 一阶段情绪曲线设计（本窗口）")
                bestseller_parts.append("以下是一阶段生成的爆款对齐情绪设计，必须严格遵循：")
                for point in window_emotion_design[:10]:  # 最多显示10章
                    ch = point.get('chapter', '?')
                    emotion = point.get('emotion', '?')
                    intensity = point.get('intensity', '?')
                    bestseller_parts.append(f"- 第{ch}章: {emotion} (强度{intensity})")
                if len(window_emotion_design) > 10:
                    bestseller_parts.append(f"- ... 共{len(window_emotion_design)}章")
                bestseller_parts.append("")
            
            # 添加爆款公式参考
            if bestseller_analysis:
                bs_formula = bestseller_analysis.get('genre_formula', '')
                if bs_formula:
                    bestseller_parts.append(f"### 爆款题材公式\n{bs_formula}\n")
                
                # 添加爆款钩子公式
                bs_hook = bestseller_analysis.get('hook_formula', '')
                if bs_hook:
                    bestseller_parts.append(f"### 爆款钩子公式\n{bs_hook}\n")
                
                # 添加爆款爽点模式
                bs_climax = bestseller_analysis.get('climax_patterns', [])
                if bs_climax:
                    bestseller_parts.append("### 爆款爽点模式")
                    for pattern in bs_climax[:3]:
                        bestseller_parts.append(f"- {pattern}")
                    bestseller_parts.append("")
            
            bestseller_parts.append("⚠️ **重要**: 以上爆款设计优先于固定模板，如果与下面的'情绪循环公式'冲突，以这里的设计为准！")
            bestseller_ref = "\n".join(bestseller_parts)
        
        return f"""# 角色：战术规划师

为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章详细战术。

## 基本信息（必须遵守）
- 书名: {novel_title}
- 主角名: {protagonist_name} ⚠️ 所有事件必须围绕此主角名展开，绝对禁止更换主角名

{bestseller_ref}

## 阶段目标（核心约束）
目标ID: {stage_goal.get('goal_id', 'G1')}
目标描述: {stage_goal.get('description', '')}
成功标准: {stage_goal.get('success_criteria', '')}
关键交付物: {', '.join(stage_goal.get('key_deliverables', []))}

{summary_text}

## 规划要求

### 情绪循环公式（严格5章循环）
**注意**: 如果上面的"爆款设计参考"中定义了不同的情绪设计，以爆款设计为准！

第1章: 压抑(强度7-8) - {protagonist_name}被质疑/遇到强大敌人
第2章: 嘲讽升级(强度8-9) - 反派嚣张/弹幕全网黑
第3章: 反转爆发(强度8-9) - {protagonist_name}展现实力，开始反击
第4章: 震惊渲染(强度7-8) - 全网刷屏/反派跪地
第5章: 期待铺垫(强度6-7) - 新地图/新能力线索

### 阶段目标对齐（重要！）
- 本批次所有章节必须服务于阶段目标
- 不要提前消耗后续阶段的关键交付物
- 如果阶段目标要求"首次展现实力"，本批次必须包含这个事件
- 如果阶段目标要求"解锁技能"，本批次必须铺垫并最终解锁

### 伏笔回收
优先回收前序总结中的"待回收伏笔"，按优先级处理。

## 输出格式
JSON格式，包含chapters数组，每个元素:
{{
  "chapter_number": 章节号,
  "emotion": "情绪类型(压抑/紧张/小爽快/大爽快/震惊/期待)",
  "intensity": 强度(1-10),
  "beat_type": "节拍类型(Setup/Confrontation/Reversal/Rendering/Foreshadowing)",
  "event": "主要事件简述",
  "purpose": "本章目的（如何服务于阶段目标）",
  "hook_type": "钩子类型",
  "hook_content": "章尾钩子内容",
  "stage_goal_alignment": "如何推进阶段目标"
}}

只输出JSON，不要其他说明。"""
    
    def _generate_from_template(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> Dict:
        """从模板生成战术规划（使用一阶段情绪设计）"""
        
        chapters = []
        num_chapters = end_chapter - start_chapter + 1
        
        # 根据阶段目标确定基调
        goal_id = stage_goal.get('goal_id', 'G1')
        
        # 🔥 构建一阶段情绪设计的查找字典
        emotion_lookup = {}
        if window_emotion_design:
            for point in window_emotion_design:
                ch = point.get('chapter', 0)
                emotion_lookup[ch] = point
        
        for i in range(num_chapters):
            ch_num = start_chapter + i
            
            # 🔥 优先使用一阶段情绪设计（如果存在）
            if ch_num in emotion_lookup:
                point = emotion_lookup[ch_num]
                emotion = point.get('emotion', '期待')
                intensity = point.get('intensity', 6)
                # 根据情绪推断beat_type
                beat_type = self._emotion_to_beat_type(emotion)
            else:
                # 使用基础5章循环
                cycle_pos = i % 5
                if cycle_pos == 0:
                    emotion = "压抑"
                    intensity = 7
                    beat_type = "Setup"
                elif cycle_pos == 1:
                    emotion = "紧张"
                    intensity = 8
                    beat_type = "Confrontation"
                elif cycle_pos == 2:
                    emotion = "小爽快"
                    intensity = 8
                    beat_type = "Reversal"
                elif cycle_pos == 3:
                    emotion = "震惊"
                    intensity = 7
                    beat_type = "Rendering"
                else:
                    emotion = "期待"
                    intensity = 6
                    beat_type = "Foreshadowing"
            
            # 根据阶段目标调整事件（传入主角名确保一致性）
            event = self._generate_event_for_goal(ch_num, goal_id, i, protagonist_name)
            
            # 确定钩子类型（如果是期待情绪，用悬念型；其他用爽点型）
            hook_type = "悬念型" if emotion in ["期待", " Foreshadowing"] else "爽点型"
            
            chapters.append({
                "chapter_number": ch_num,
                "emotion": emotion,
                "intensity": intensity,
                "beat_type": beat_type,
                "event": event,
                "purpose": f"推进{goal_id}阶段目标",
                "hook_type": hook_type,
                "hook_content": f"第{ch_num}章章尾钩子...",
                "stage_goal_alignment": f"服务于{goal_id}"
            })
        
        return {
            "batch_info": {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "stage_goal_id": goal_id,
                "stage_goal_description": stage_goal.get('description', '')
            },
            "chapters": chapters
        }
    
    def _generate_event_for_goal(self, ch_num: int, goal_id: str, index: int, protagonist_name: str = "主角") -> str:
        """根据阶段目标生成事件"""
        
        # 使用传入的主角名替换"主角"
        p = protagonist_name
        
        events_map = {
            'G1': [  # establish形象
                f"{p}醉酒状态被选中进入禁地",
                f"外媒嘲讽大夏选手{p}是酒鬼",
                f"{p}随手一指秒杀凶兽",
                f"直播间观众震惊于{p}实力",
                f"{p}发现禁地灵酒线索"
            ],
            'G2': [  # 解锁酒神咒
                f"{p}收集上古灵酒配方",
                f"{p}遭遇强敌陷入苦战",
                f"{p}触发酒神传承试炼",
                f"{p}领悟酒神咒雏形",
                f"{p}首次用酒神咒斩杀伪神"
            ],
            'G3': [  # 诸神黄昏
                f"{p}突破禁地外围屏障",
                f"{p}遭遇异界文明先锋",
                f"{p}发现诸神黄昏遗迹",
                f"{p}与高魔文明初次交锋",
                f"{p}建立跨位面盟友"
            ],
            'G4': [  # 揭露真相
                f"{p}发现国运游戏监控痕迹",
                f"{p}遭遇高维文明使者",
                f"{p}揭露游戏真相",
                f"{p}联合其他觉醒者",
                f"{p}向高维意志挥剑"
            ]
        }
        
        events = events_map.get(goal_id, [f"{p}推进剧情"] * 5)
        return events[index % len(events)]
    
    def update_generated_chapters(self, chapters: List[Dict]):
        """更新已生成章节记录"""
        self.generated_chapters.extend(chapters)
        logger.info(f"[TacticalPlanner] 已更新生成记录: {len(self.generated_chapters)}章")
    
    def _emotion_to_beat_type(self, emotion: str) -> str:
        """根据情绪类型推断节拍类型"""
        emotion_beat_map = {
            "压抑": "Setup",
            "紧张": "Confrontation",
            "嘲讽": "Confrontation",
            "质疑": "Confrontation",
            "小爽快": "Reversal",
            "反转": "Reversal",
            "爆发": "Reversal",
            "反击": "Reversal",
            "震惊": "Rendering",
            "震撼": "Rendering",
            "期待": "Foreshadowing",
            "铺垫": "Foreshadowing",
            "绝望": "Crisis",
            "危机": "Crisis"
        }
        return emotion_beat_map.get(emotion, "Transition")


# 便捷函数
def create_tactical_plan(
    start_chapter: int,
    end_chapter: int,
    novel_title: str,
    protagonist_name: str,
    stage_goal: Dict,
    previous_summary: Optional[Dict] = None,
    api_client=None
) -> Dict:
    """便捷函数：创建战术规划"""
    planner = TacticalPlanner(api_client)
    return planner.plan_next_batch(
        start_chapter, end_chapter,
        novel_title, protagonist_name,
        stage_goal, previous_summary
    )
