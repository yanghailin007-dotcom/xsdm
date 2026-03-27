# -*- coding: utf-8 -*-
"""
Tactical Planner
战术层规划器

每30章滚动规划详细情绪曲线
基于已生成内容动态调整
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
    2. 基于已生成内容动态调整
    3. 确保与战略框架一致
    4. 保证章节间连贯性
    
    滚动窗口机制：
    - 每次规划30章
    - 与前一批重叠5章（保证连贯）
    - 基于实际生成效果调整后续
    """
    
    DEFAULT_WINDOW = 30      # 每次规划30章
    DEFAULT_OVERLAP = 5      # 重叠5章
    
    def __init__(
        self, 
        api_client=None,
        strategic_framework: Dict = None,
        project_path: Path = None
    ):
        self.api_client = api_client
        self.strategic_framework = strategic_framework or {}
        self.project_path = project_path
        self.generated_chapters = []  # 已生成章节记录
        
    def plan_next_batch(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        previous_summary: str = ""
    ) -> Dict:
        """
        规划下一批章节（默认30章）
        
        Args:
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            novel_title: 书名
            protagonist_name: 主角名
            previous_summary: 前一阶段摘要
            
        Returns:
            战术规划字典
        """
        logger.info(f"[TacticalPlanner] 规划第{start_chapter}-{end_chapter}章")
        
        # 1. 分析已生成内容（如果有）
        analysis = self._analyze_generated_content()
        
        # 2. 确定当前所处战略阶段
        stage_info = self._get_current_stage(start_chapter)
        
        # 3. 检查是否有里程碑需要覆盖
        milestones = self._get_milestones_in_range(start_chapter, end_chapter)
        
        # 4. 生成战术规划
        if self.api_client:
            tactical_plan = self._generate_with_ai(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_info, milestones,
                analysis, previous_summary
            )
        else:
            tactical_plan = self._generate_from_template(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_info, milestones
            )
        
        # 5. 验证与战略框架的一致性
        if self.strategic_framework:
            issues = self._validate_against_strategic(
                tactical_plan, start_chapter, end_chapter
            )
            if issues:
                logger.warning(f"[TacticalPlanner] 战术规划与战略框架有偏差: {issues}")
                # 自动修正
                tactical_plan = self._auto_fix(tactical_plan, issues)
        
        return tactical_plan
    
    def _generate_with_ai(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_info: Dict,
        milestones: List[Dict],
        analysis: Dict,
        previous_summary: str
    ) -> Dict:
        """使用AI生成战术规划"""
        
        # 构建提示词
        prompt = self._build_tactical_prompt(
            start_chapter, end_chapter,
            novel_title, protagonist_name,
            stage_info, milestones,
            analysis, previous_summary
        )
        
        try:
            response = self.api_client.generate_content(
                content_type="tactical_planning",
                user_prompt=prompt,
                temperature=0.7
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
            stage_info, milestones
        )
    
    def _build_tactical_prompt(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_info: Dict,
        milestones: List[Dict],
        analysis: Dict,
        previous_summary: str
    ) -> str:
        """构建战术规划提示词"""
        
        # 里程碑信息
        milestones_text = ""
        if milestones:
            milestones_text = "\n".join([
                f"- 第{ms['chapter']}章: {ms['type']} - {ms.get('description', '')}"
                for ms in milestones
            ])
        else:
            milestones_text = "本阶段无关键转折点"
        
        # 前一阶段分析
        analysis_text = ""
        if analysis.get("actual_emotions"):
            analysis_text = f"""
## 前一阶段实际效果分析
- 平均情绪强度: {analysis.get('avg_intensity', 'N/A')}
- 读者反馈趋势: {analysis.get('trend', 'N/A')}
- 需要调整: {', '.join(analysis.get('adjustments', []))}
"""
        
        return f"""# 角色：战术规划师

为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章的详细情绪曲线。

## 战略背景
- 当前阶段: {stage_info.get('title', '未知')}
- 主角身份: {stage_info.get('identity', '未知')}
- 力量等级: {stage_info.get('power_level', '未知')}
- 阶段目标: {stage_info.get('core_ability', '未知')}

## 需要覆盖的关键事件
{milestones_text}

## 前一阶段摘要
{previous_summary or "本阶段为开局"}
{analysis_text}

## 规划要求

### 情绪循环公式（严格5章循环）
第1章: 压抑(强度7-8) - 主角被质疑/遇到强大敌人/国内出现危机
第2章: 嘲讽升级(强度8-9) - 反派极度嚣张/弹幕全网黑/现实人物落井下石
第3章: 反转爆发(强度8-9) - 主角展现实力，开始反击
第4章: 震惊渲染(强度7-8) - 全网刷屏666/反派跪地求饶/国家获得巨大利益
第5章: 期待铺垫(强度6-7) - 新地图开启/更强敌人出现/主角获得新能力线索

### 章尾钩子轮替
1. 悬念型: "那道黑影究竟是..."
2. 爽点型: "恭喜宿主获得XXX"
3. 期待型: "明日开启：诸神竞技场"
4. 震惊型: "他...他竟然斩断了时空！"

### 强度控制
- 小爽点(每3章): 强度7
- 中爽点(每10章): 强度8-9
- 大爽点(每30章): 强度10
- 缓冲章(爽点后1-2章): 强度5-6

## 输出格式
JSON格式，包含chapters数组，每个元素:
{{
  "chapter_number": 章节号,
  "emotion": "情绪类型(压抑/紧张/小爽快/大爽快/震惊/期待)",
  "intensity": 强度(1-10),
  "beat_type": "节拍类型(Setup/Confrontation/Reversal/Rendering/Foreshadowing)",
  "event": "主要事件简述",
  "purpose": "本章目的",
  "hook_type": "钩子类型(悬念型/爽点型/期待型/震惊型)",
  "hook_content": "章尾钩子内容"
}}

只输出JSON，不要其他说明。"""
    
    def _generate_from_template(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_info: Dict,
        milestones: List[Dict]
    ) -> Dict:
        """从模板生成战术规划（简化版，实际应使用AI）"""
        
        chapters = []
        
        # 基础情绪循环
        emotion_cycle = [
            ("压抑", 8, "Setup"),
            ("紧张", 8, "Confrontation"),
            ("小爽快", 8, "Reversal"),
            ("震惊", 7, "Rendering"),
            ("期待", 6, "Foreshadowing")
        ]
        
        # 钩子类型轮替
        hook_types = ["悬念型", "爽点型", "期待型", "震惊型"]
        
        for ch_num in range(start_chapter, end_chapter + 1):
            # 确定当前循环位置
            cycle_pos = (ch_num - 1) % 5
            emotion, intensity, beat_type = emotion_cycle[cycle_pos]
            
            # 检查是否是里程碑章节
            is_milestone = any(ms["chapter"] == ch_num for ms in milestones)
            if is_milestone:
                intensity = 10  # 里程碑章节强制强度10
                emotion = "大爽快"
            
            # 每10章一个中高潮
            if ch_num % 10 == 0 and not is_milestone:
                intensity = 9
                emotion = "大爽快"
            
            chapters.append({
                "chapter_number": ch_num,
                "emotion": emotion,
                "intensity": intensity,
                "beat_type": beat_type,
                "event": self._generate_event_description(ch_num, emotion, stage_info),
                "purpose": self._generate_purpose(ch_num, emotion),
                "hook_type": hook_types[(ch_num - 1) % 4],
                "hook_content": f"第{ch_num}章的悬念钩子...",
                "is_key_event": is_milestone or ch_num % 10 == 0
            })
        
        return {
            "batch_info": {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "total_chapters": end_chapter - start_chapter + 1,
                "stage": stage_info.get("title", "未知"),
                "planned_at": datetime.now().isoformat()
            },
            "chapters": chapters,
            "milestones_covered": [ms["chapter"] for ms in milestones]
        }
    
    def _generate_event_description(self, ch_num: int, emotion: str, stage_info: Dict) -> str:
        """生成事件描述（简化版）"""
        templates = {
            "压抑": "主角遭遇危机/被质疑/陷入困境",
            "紧张": "反派施压/冲突升级/生死关头",
            "小爽快": "主角反击/打脸反派/获得小收获",
            "大爽快": "重大打脸/实力震惊全场/国家获益",
            "震惊": "全网震惊/各方反应/影响扩大",
            "期待": "新线索出现/悬念铺垫/期待升级"
        }
        return templates.get(emotion, "剧情推进")
    
    def _generate_purpose(self, ch_num: int, emotion: str) -> str:
        """生成章节目的"""
        purposes = {
            "压抑": "建立冲突，让读者产生期待",
            "紧张": "升级冲突，制造危机感",
            "小爽快": "首次打脸，建立爽感",
            "大爽快": "高潮打脸，最大化爽感",
            "震惊": "渲染效果，扩大影响",
            "期待": "铺垫后续，建立新期待"
        }
        return purposes.get(emotion, "推进剧情")
    
    def _analyze_generated_content(self) -> Dict:
        """分析已生成内容的效果"""
        if not self.generated_chapters:
            return {}
        
        # 计算实际情绪强度
        intensities = [ch.get("intensity", 5) for ch in self.generated_chapters]
        avg_intensity = sum(intensities) / len(intensities) if intensities else 0
        
        # 分析趋势
        trend = "稳定"
        if len(intensities) >= 3:
            if intensities[-1] > intensities[0]:
                trend = "上升"
            elif intensities[-1] < intensities[0]:
                trend = "下降"
        
        return {
            "avg_intensity": round(avg_intensity, 2),
            "trend": trend,
            "adjustments": []  # 需要调整的项
        }
    
    def _get_current_stage(self, chapter: int) -> Dict:
        """获取当前所处战略阶段"""
        stages = self.strategic_framework.get("growth_stages", [])
        for stage in stages:
            range_str = stage.get("range", "")
            try:
                s, e = map(int, range_str.replace("章", "").split("-"))
                if s <= chapter <= e:
                    return stage
            except:
                continue
        return {}
    
    def _get_milestones_in_range(self, start: int, end: int) -> List[Dict]:
        """获取指定范围内的里程碑"""
        milestones = self.strategic_framework.get("milestones", [])
        return [ms for ms in milestones if start <= ms.get("chapter", 0) <= end]
    
    def _validate_against_strategic(
        self, tactical_plan: Dict, start: int, end: int
    ) -> List[str]:
        """验证战术规划是否符合战略框架"""
        issues = []
        
        # 检查里程碑覆盖
        milestones = self._get_milestones_in_range(start, end)
        for ms in milestones:
            ms_ch = ms["chapter"]
            if not any(ch.get("chapter_number") == ms_ch and ch.get("intensity", 0) >= 9 
                      for ch in tactical_plan.get("chapters", [])):
                issues.append(f"第{ms_ch}章里程碑强度不足")
        
        return issues
    
    def _auto_fix(self, tactical_plan: Dict, issues: List[str]) -> Dict:
        """自动修正战术规划"""
        chapters = tactical_plan.get("chapters", [])
        
        for issue in issues:
            if "强度不足" in issue:
                # 提取章节号
                import re
                match = re.search(r"第(\d+)章", issue)
                if match:
                    ch_num = int(match.group(1))
                    for ch in chapters:
                        if ch.get("chapter_number") == ch_num:
                            ch["intensity"] = 10
                            ch["emotion"] = "大爽快"
                            ch["is_key_event"] = True
        
        tactical_plan["chapters"] = chapters
        tactical_plan["auto_fixed"] = True
        return tactical_plan
    
    def update_generated_chapters(self, chapters: List[Dict]):
        """更新已生成章节记录"""
        self.generated_chapters.extend(chapters)
        
        # 保存到项目目录（用于后续分析）
        if self.project_path:
            self._save_generation_history()
    
    def _save_generation_history(self):
        """保存生成历史"""
        if not self.project_path:
            return
        
        history_file = self.project_path / "generation_history.json"
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "generated_chapters": self.generated_chapters,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存生成历史失败: {e}")


# 便捷函数
def create_tactical_plan(
    start_chapter: int,
    end_chapter: int,
    novel_title: str,
    protagonist_name: str,
    strategic_framework: Dict = None,
    api_client = None,
    previous_summary: str = ""
) -> Dict:
    """便捷函数：创建战术规划"""
    planner = TacticalPlanner(api_client, strategic_framework)
    return planner.plan_next_batch(
        start_chapter, end_chapter,
        novel_title, protagonist_name,
        previous_summary
    )
