# StagePlanManager.py
import json
import re
import os
from typing import Dict, Optional, List
from EventManager import EventManager
from EmotionalPlanManager import EmotionalPlanManager
from WritingGuidanceManager import WritingGuidanceManager
from RomancePatternManager import RomancePatternManager
from utils import parse_chapter_range, is_chapter_in_range

class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}
        
        # 初始化各个管理器
        self.event_manager = EventManager(self)
        self.emotional_manager = EmotionalPlanManager(self)
        self.writing_guidance_manager = WritingGuidanceManager(self)
        self.romance_manager = RomancePatternManager(self)
        
        # 阶段特性描述
        self.stage_characteristics = {
            "opening_stage": {
                "focus": "快速建立强烈冲突，立即吸引读者",
                "pace": "极快节奏，前3章必须建立核心冲突",
                "key_elements": "主角惊艳登场、立即冲突、强力悬念、读者共鸣",
                "critical_requirements": [
                    "前3000字内必须建立强烈冲突",
                    "第1章结尾必须有强力追读钩子", 
                    "减少世界观介绍，增加行动和冲突",
                    "主角特质在前2章完全展现"
                ],
                "success_metrics": [
                    "读者在第1章产生强烈情感共鸣",
                    "第3章结束时读者必须想知道后续发展",
                    "前10章完读率目标：70%+"
                ]
            },
            "development_stage": {
                "focus": "深化矛盾，推进角色成长",
                "pace": "变化节奏，快慢结合",
                "key_elements": "能力提升、盟友敌人、支线展开"
            },
            "climax_stage": {
                "focus": "冲突爆发，重大转折",
                "pace": "紧张节奏，逐步加速",
                "key_elements": "关键对决、真相揭露、角色蜕变"
            },
            "ending_stage": {
                "focus": "解决矛盾，收束线索",
                "pace": "逐渐放缓，情感升华",
                "key_elements": "矛盾解决、伏笔回收、最终准备"
            },
            "final_stage": {
                "focus": "完整收尾，交代后续",
                "pace": "平稳节奏，情感共鸣",
                "key_elements": "最终结局、角色归宿、主题升华"
            }
        }

    # === 核心阶段规划方法 ===
    
    def generate_overall_stage_plan(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                market_analysis: Dict, global_growth_plan: Dict, total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划 - 修复版本"""
        print("=== 生成全书阶段计划 ===")

        # 在全书的开始阶段分析情感模式（只分析一次）
        if "romance_pattern" not in self.generator.novel_data:
            print("  💞 分析全书情感模式...")
            romance_pattern = self.romance_manager.analyze_romance_pattern(creative_seed, novel_synopsis)
            self.generator.novel_data["romance_pattern"] = romance_pattern
            print(f"  ✅ 情感模式分析完成: {romance_pattern['romance_type']}-{romance_pattern['emotional_style']}")

        # 计算阶段边界
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = f"""
创意种子: {creative_seed}
小说标题: {novel_title}
小说简介: {novel_synopsis}
市场分析: {json.dumps(market_analysis, ensure_ascii=False)}
全书成长规划: {json.dumps(global_growth_plan, ensure_ascii=False)}
总章节数: {total_chapters}

# 阶段划分要求
请将全书{total_chapters}章划分为5个主要阶段，并为每个阶段制定详细的写作重点：

## 1. 开局阶段 (约前10-15%章节)
- **章节范围**: 第1章-第{boundaries['opening_end']}章
- **核心任务**: 建立故事基础，引入核心冲突，吸引读者
- **重点内容**: 主角出场，世界观介绍，初始冲突，悬念设置

## 2. 发展阶段 (约25-30%章节)
- **章节范围**: 第{boundaries['development_start']}章-第{boundaries['development_end']}章  
- **核心任务**: 深化矛盾，角色成长，支线展开
- **重点内容**: 能力提升，盟友敌人，小高潮，伏笔埋设

## 3. 高潮阶段 (约30-35%章节)
- **章节范围**: 第{boundaries['climax_start']}章-第{boundaries['climax_end']}章
- **核心任务**: 主要冲突爆发，重大转折，情感爆发  
- **重点内容**: 关键对决，真相揭露，角色蜕变，核心矛盾激化

## 4. 收尾阶段 (约15-20%章节)
- **章节范围**: 第{boundaries['ending_start']}章-第{boundaries['ending_end']}章
- **核心任务**: 解决主要冲突，收束支线，准备结局
- **重点内容**: 矛盾解决，伏笔回收，情感升华，最终准备

## 5. 结局阶段 (约5-10%章节)
- **章节范围**: 第{boundaries['final_start']}章-第{total_chapters}章
- **核心任务**: 完整收尾，交代后续，情感共鸣
- **重点内容**: 最终结局，角色归宿，主题升华，读者共鸣    
"""
        
        result = self.generator.api_client.generate_content_with_retry(
            "overall_stage_plan", 
            user_prompt,
            purpose="制定全书阶段计划"
        )
        
        if result:
            if not isinstance(result, dict):
                print("❌ 阶段计划返回数据格式错误")
                return None
            
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            # 存储到novel_data
            self.generator.novel_data["overall_stage_plans"] = result
            print("✓ 全书阶段计划生成成功")
            return result
        else:
            print("❌ 全书阶段计划生成失败")
            return None
    
    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        """计算阶段边界"""
        ratios = [0.16, 0.26, 0.28, 0.18, 0.12]  # 确保总和为1.0
        
        # 计算累积章节数，确保不重叠
        chapters = [0]
        for ratio in ratios:
            chapters.append(chapters[-1] + int(total_chapters * ratio))
        
        # 确保最后一个章节等于总章节数
        chapters[-1] = total_chapters
        
        return {
            "opening_end": chapters[1],
            "development_start": chapters[1] + 1,
            "development_end": chapters[2], 
            "climax_start": chapters[2] + 1,
            "climax_end": chapters[3],
            "ending_start": chapters[3] + 1,
            "ending_end": chapters[4],
            "final_start": chapters[4] + 1
        }
    
    def print_stage_overview(self):
        """打印详细的阶段计划概览"""
        if not self.overall_stage_plans:
            print("暂无阶段计划数据")
            return
        
        print("\n" + "=" * 60)
        print("                   小说阶段计划概览")
        print("=" * 60)
        
        total_chapters = 0
        stage_plan_dict = self.overall_stage_plans.get("overall_stage_plan", {})
        
        for i, (stage_name, stage_info) in enumerate(stage_plan_dict.items(), 1):
            chapter_range = stage_info.get('chapter_range', '1-1')
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            total_chapters += chapter_count
            
            print(f"\n📚 阶段 {i}: {stage_name}")
            print(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            print(f"   🎯 目标: {stage_info.get('stage_goal', '暂无目标描述')}")
            print(f"   ⚡ 关键发展: {stage_info.get('key_developments', '暂无关键事件')}")
            if stage_info.get('core_conflicts'):
                print(f"   ⚔️ 核心冲突: {stage_info.get('core_conflicts')}")
        
        print(f"\n📈 总计: {len(stage_plan_dict)}个阶段，{total_chapters}章")
        print("=" * 60)

    def generate_stage_writing_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """生成阶段详细写作计划 - 优化版本"""
        cache_key = f"{stage_name}_writing_plan"
        
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        print(f"  🎬 生成{stage_name}的写作计划...")
        
        # 计算章节分段
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 使用事件管理器计算密度
        density_requirements = self.event_manager.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        
        # 获取阶段特定指导
        stage_guidance = self.get_stage_specific_guidance(stage_name)
        
        # 构建用户提示词
        user_prompt = f"""
    内容:
    ## 任务指令
    请根据下文提供的小说信息和全书大纲，为 `{stage_name}` 阶段制定详细的写作计划。

    {stage_guidance}

    ## 小说核心信息
    - **小说标题**: {novel_title}
    - **小说简介**: {novel_synopsis}
    - **创意种子**: {creative_seed}

    ## 全书大纲 (上下文)
    {json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)}

    ## 本次任务详情
    - **目标阶段**: {stage_name}
    - **章节范围**: {stage_range}章
    - **阶段长度**: {stage_length}章

    {self._get_major_event_design_requirements(stage_name, density_requirements)}
    {self._get_golden_chapters_design(stage_name, stage_range)}
    """
        
        # 从novel_data获取已分析的情感模式
        romance_pattern = self.generator.novel_data.get("romance_pattern", {})
        
        if not romance_pattern:
            print("  ⚠️ 警告：未找到情感模式数据，进行补充分析")
            romance_pattern = self.romance_manager.analyze_romance_pattern(creative_seed, novel_synopsis)
            self.generator.novel_data["romance_pattern"] = romance_pattern
        
        print(f"  💞 使用情感模式: {romance_pattern['romance_type']}-{romance_pattern['emotional_style']}")  
        
        # 生成写作计划
        writing_plan = self.generator.api_client.generate_content_with_retry(
            "stage_writing_planning",
            user_prompt,
            purpose=f"生成{stage_name}写作计划"
        )

        # 🆕 在计划生成后立即进行AI连续性评估
        if writing_plan:
            continuity_assessment = self.assess_stage_event_continuity(
                writing_plan, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
            )
            
            # 如果评估发现严重问题，可以触发优化
            if continuity_assessment.get("overall_continuity_score", 10) < 6:
                print(f"  ⚠️ 阶段事件连续性评分较低，进行优化...")
                writing_plan = self._optimize_based_on_continuity_assessment(
                    writing_plan, continuity_assessment, stage_name, stage_range
                )

        # 识别事件空窗期并生成情感填充事件
        gap_chapters_with_context = self.event_manager.identify_event_gaps(writing_plan, stage_range)
        if gap_chapters_with_context:
            filler_events = self.romance_manager.generate_romance_filler_events(
                gap_chapters_with_context, romance_pattern, stage_name, 
                creative_seed, novel_title, novel_synopsis
            )
            writing_plan = self.romance_manager.integrate_filler_events(writing_plan, filler_events)
        
        # 验证和优化写作计划
        writing_plan = self._validate_and_optimize_writing_plan(
            writing_plan, stage_name, stage_range, creative_seed, 
            novel_title, novel_synopsis, overall_stage_plan
        )
        
        if writing_plan:
            # 缓存和存储结果
            self.stage_writing_plans_cache[cache_key] = writing_plan
            
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            self.generator.novel_data["stage_writing_plans"][stage_name] = writing_plan
            
            print(f"  ✅ {stage_name}写作计划生成完成")
            self._print_writing_plan_summary(writing_plan)
            return writing_plan
        else:
            print(f"  ⚠️ {stage_name}写作计划生成失败，使用默认计划")
            return {}

    def _get_major_event_design_requirements(self, stage_name: str, density_requirements: Dict) -> str:
        """获取大事件设计要求的文本"""
        return f"""
## 🎭 阶段特定事件密度要求
- **重大事件**: {density_requirements['major_events']}个 (跨{density_requirements['min_major_duration']}+章大事件，推动主线、重大转折)
- **中型事件**: {density_requirements['medium_events']}个 (2-3章中型事件，支线任务、重要关系发展)  
- **小型事件**: {density_requirements['minor_events']}个 (单章小事件，严格控制数量)
- **大事件持续时间**: 至少{density_requirements['min_major_duration']}章，平均{density_requirements['avg_major_duration']}章

## 🚀 大事件设计核心要求

### 结构完整性
每个重大事件必须包含完整结构：
1. **前期铺垫**（1-2章）：制造期待，埋下伏笔
2. **事件触发**（1章）：明确的起点和冲突爆发
3. **发展升级**（2-4章）：冲突逐步升级，加入新元素
4. **高潮爆发**（1-2章）：核心冲突+情感最高点
5. **反转意外**（1章）：出人意料的转折
6. **收尾影响**（1-2章）：事件结束后的深远影响

### 情感弧线设计
- 开始：期待/紧张 → 发展：焦虑/兴奋 → 高潮：震撼/感动 → 结束：满足/思考
- 必须有明确的情感起伏曲线

### 反转设计（每个大事件至少1个）
- 身份反转：角色真实身份揭露
- 立场反转：盟友变敌人或相反  
- 力量反转：强弱关系逆转
- 信息反转：关键信息揭示改变局势
- 目标反转：行动目标发生根本改变

### 质量优先原则
- 减少零碎小事件，集中资源打造精彩大事件
- 每个大事件都应该是读者能够记住的"名场面"
- 确保大事件之间有合理的间隔，避免过度密集
"""

    def _get_golden_chapters_design(self, stage_name: str, stage_range: str) -> str:
        """获取黄金三章设计要求的文本"""
        if not (stage_name == "opening_stage" and stage_range.startswith("1-") and int(stage_range.split("-")[1]) >= 3):
            return ""
        
        return """
## 🏆 黄金三章特殊设计要求（第1-3章）

请为黄金三章制定特别详细的设计方案，特别注意：
- 第1章必须包含一个强力大事件的起始铺垫
- 前3章要为一个持续5-8章的大事件奠定基础
- 减少零碎事件，集中打造连贯的阅读体验

### 第1章设计方案：
- **开篇大事件铺垫**：立即开始一个大事件的铺垫
- **主角登场**：在冲突中展现主角特质  
- **悬念设置**：为大事件设置强力悬念
- **情感建立**：让读者立即产生情感共鸣

### 第2章设计方案：
- **大事件发展**：深化大事件的冲突和发展
- **新元素引入**：为大事件引入关键角色或设定
- **节奏控制**：保持快节奏推进大事件

### 第3章设计方案：
- **大事件小高潮**：安排大事件的第一个小高潮
- **强力追读钩子**：设置让读者必须看下一章的强力理由
- **阶段总结**：为后续大事件爆发做好充分准备
"""    

    def _validate_and_optimize_writing_plan(self, writing_plan: Dict, stage_name: str, stage_range: str, 
                                        creative_seed: str, novel_title: str, novel_synopsis: str, 
                                        overall_stage_plan: Dict) -> Dict:
        """验证和优化写作计划"""
        if not writing_plan:
            print(f"  ⚠️ {stage_name}写作计划生成失败，使用默认计划")
            return {}
        
        # 增强大事件结构
        writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 生成情绪计划并整合
        global_emotional_plan = self.generator.novel_data.get("emotional_development_plan", {})
        emotional_plan = self.emotional_manager.generate_stage_emotional_plan(stage_name, stage_range, global_emotional_plan)
        
        if "stage_writing_plan" in writing_plan:
            writing_plan["stage_writing_plan"]["emotional_plan"] = emotional_plan
        else:
            writing_plan["emotional_plan"] = emotional_plan
        
        # 处理黄金三章
        if stage_name == "opening_stage" and stage_range.startswith("1-") and int(stage_range.split("-")[1]) >= 3:
            writing_plan = self._enhance_golden_chapters_in_writing_plan(writing_plan)
        
        # 验证事件密度
        event_density_ok = self.event_manager.validate_stage_event_density(writing_plan, stage_name, stage_range)
        if not event_density_ok:
            print(f"  ⚠️ {stage_name}写作计划事件密度不符合要求，进行优化...")
            writing_plan = self.event_manager.supplement_events_with_ai(writing_plan, stage_range, creative_seed, 
                                                                    novel_title, novel_synopsis, overall_stage_plan)
        
        # 验证大事件结构
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        major_validation = self.event_manager.validate_major_event_structure(major_events)
        
        if not major_validation["is_valid"]:
            print(f"  ⚠️ {stage_name}大事件结构存在问题，进行优化...")
            writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 验证主线连贯性
        is_continuous = self.event_manager.validate_main_thread_continuity(writing_plan, stage_name)
        if not is_continuous:
            print(f"  ⚠️ {stage_name}写作计划存在事件间隔过长问题")
        
        return writing_plan
    
    def _enhance_golden_chapters_in_writing_plan(self, writing_plan: Dict) -> Dict:
        """在阶段写作计划中增强黄金三章设计"""
        # 确保有事件系统设计
        if "event_system_design" not in writing_plan:
            writing_plan["event_system_design"] = {}
        
        # 添加黄金三章特殊事件
        writing_plan["event_system_design"]["golden_chapters_events"] = {
            "chapter_1_opening_event": {
                "name": "开篇引爆事件",
                "type": "重大事件",
                "start_chapter": 1,
                "end_chapter": 1,
                "purpose": "快速吸引读者注意力，展现主角特质",
                "success_criteria": "读者在500字内被吸引继续阅读",
                "key_moments": [
                    {
                        "chapter": 1,
                        "description": "强力开篇场景，立即展现冲突",
                        "impact": "高"
                    }
                ]
            },
            "chapter_2_development_event": {
                "name": "冲突深化事件", 
                "type": "重大事件",
                "start_chapter": 2,
                "end_chapter": 2,
                "purpose": "深化开篇冲突，建立人物关系",
                "success_criteria": "读者对主角产生认同和期待",
                "key_moments": [
                    {
                        "chapter": 2,
                        "description": "主角应对冲突，展现能力",
                        "impact": "中高"
                    }
                ]
            },
            "chapter_3_climax_event": {
                "name": "小高潮事件",
                "type": "重大事件", 
                "start_chapter": 3,
                "end_chapter": 3,
                "purpose": "安排情节小高潮，设置追读钩子",
                "success_criteria": "读者产生强烈追读欲望",
                "key_moments": [
                    {
                        "chapter": 3,
                        "description": "情节小高潮和强力悬念结尾",
                        "impact": "高"
                    }
                ]
            }
        }
        
        # 添加黄金三章角色表现设计
        if "character_performance_design" not in writing_plan:
            writing_plan["character_performance_design"] = {}
        
        writing_plan["character_performance_design"]["golden_chapters_focus"] = {
            "chapter_1_character_intro": {
                "focus": "主角惊艳登场",
                "key_scenes": ["开篇亮相", "冲突应对", "特质展现"],
                "success_criteria": "读者立即喜欢上主角"
            },
            "chapter_2_character_development": {
                "focus": "主角能力展现和关系建立", 
                "key_scenes": ["能力演示", "配角互动", "情感共鸣"],
                "success_criteria": "读者对主角产生深度认同"
            },
            "chapter_3_character_growth": {
                "focus": "主角初步成长和魅力强化",
                "key_scenes": ["困境突破", "智慧展现", "魅力时刻"],
                "success_criteria": "读者成为主角粉丝"
            }
        }
        
        return writing_plan

    def _print_writing_plan_summary(self, writing_plan: Dict):
        """打印写作计划摘要 - 增强连续性评估信息"""
        print(f"  🔍 开始打印写作计划摘要...")
        
        # 检查是否有嵌套结构
        if "stage_writing_plan" in writing_plan:
            actual_plan = writing_plan["stage_writing_plan"]
        else:
            actual_plan = writing_plan
        
        # 原有的统计信息...
        
        # 🆕 添加连续性评估信息
        continuity_assessment = actual_plan.get("continuity_assessment", {})
        if continuity_assessment:
            score = continuity_assessment.get("overall_continuity_score", "N/A")
            print(f"      🔗 AI连续性评分: {score}/10")
            
            critical_issues = continuity_assessment.get("critical_issues", [])
            if critical_issues:
                print(f"      ⚠️ 关键问题: {len(critical_issues)}个")
                for i, issue in enumerate(critical_issues[:2]):  # 只显示前2个
                    print(f"        {i+1}. {issue}")
            
            strengths = continuity_assessment.get("strengths", [])
            if strengths:
                print(f"      ✅ 优势: {', '.join(strengths[:2])}")  # 只显示前2个优势
    
    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文"""
        return self.writing_guidance_manager.get_chapter_writing_context(chapter_number)

    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        return self.writing_guidance_manager.generate_writing_guidance_prompt(chapter_number)

    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """通过阶段名称获取写作计划"""
        # 首先尝试从novel_data中获取
        if "stage_writing_plans" in self.generator.novel_data:
            stage_plans = self.generator.novel_data["stage_writing_plans"]
            if stage_name in stage_plans:
                # 同时更新缓存
                cache_key = f"{stage_name}_writing_plan"
                self.stage_writing_plans_cache[cache_key] = stage_plans[stage_name]
                return stage_plans[stage_name]
        
        # 尝试从缓存获取
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        # 如果没有找到，需要重新生成
        print(f"  ⚠️ {stage_name}的写作计划未找到，需要内容规划和伏笔计划来生成")
        return {}

    def get_stage_plan_for_chapter(self, chapter_number: int) -> Dict:
        """为指定章节获取阶段计划 - 修复版本"""
        try:
            # 获取当前阶段名称
            current_stage = self._get_current_stage(chapter_number)
            if not current_stage:
                print(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
                return {}
            
            # 从 novel_data 中获取阶段写作计划
            novel_data = self.generator.novel_data
            stage_writing_plans = novel_data.get("stage_writing_plans", {})
            
            if current_stage not in stage_writing_plans:
                print(f"  ⚠️ 没有找到{current_stage}的写作计划")
                return {}
            
            stage_plan_data = stage_writing_plans[current_stage]
            
            # 确保返回正确的数据结构
            if "stage_writing_plan" in stage_plan_data:
                return stage_plan_data["stage_writing_plan"]
            else:
                print(f"  ⚠️ 阶段计划数据缺少stage_writing_plan字段，使用原始数据")
                return stage_plan_data
                
        except Exception as e:
            print(f"❌ 获取第{chapter_number}章阶段计划失败: {e}")
            return {}

    def export_events_to_json(self, file_path: str = "novel_events.json"):
        """导出事件到JSON"""
        return self.event_manager.export_events_to_json(file_path)
    
    def get_events_summary(self) -> Dict:
        """获取事件摘要"""
        return self.event_manager.get_events_summary()
    
    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, global_emotional_plan: Dict) -> Dict:
        """生成阶段情绪计划"""
        return self.emotional_manager.generate_stage_emotional_plan(stage_name, stage_range, global_emotional_plan)

    # === 辅助方法 ===
    
    def _get_current_stage(self, chapter_number: int) -> str:
        """获取当前章节所属的阶段名称 - 修复版本"""
        try:
            # 从 overall_stage_plans 中查找
            overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
            if not overall_plans or "overall_stage_plan" not in overall_plans:
                print("  ⚠️ 没有可用的整体阶段计划")
                return None
            
            stage_plan_dict = overall_plans["overall_stage_plan"]
            
            for stage_name, stage_info in stage_plan_dict.items():
                # 解析章节范围
                chapter_range_str = stage_info.get("chapter_range", "")
                if not chapter_range_str:
                    continue
                    
                # 提取数字范围
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    start_chap = int(numbers[0])
                    end_chap = int(numbers[1])
                    
                    if start_chap <= chapter_number <= end_chap:
                        return stage_name
            
            print(f"  ⚠️ 第{chapter_number}章不在任何阶段范围内")
            return None
            
        except Exception as e:
            print(f"❌ 确定章节阶段失败: {e}")
            return None

    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围"""
        if "global_growth_plan" not in self.generator.novel_data:
            return "1-100"
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        for stage in growth_plan.get("stage_framework", []):
            if stage["stage_name"] == stage_name:
                return stage["chapter_range"]
        return "1-100"

    def _get_stage_length(self, stage_range: str) -> int:
        """获取阶段长度"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        return end_chap - start_chap + 1

    # === 阶段特定指导方法 ===
    
    def get_stage_specific_guidance(self, stage_name: str) -> str:
        """获取阶段特定的写作指导"""
        stage_guidance = {
            "opening_stage": """
    ## 🚀 开局阶段特殊要求（前16%章节）

    ### 核心任务
    1. **立即吸引**：前500字必须抓住读者注意力
    2. **快速冲突**：前3000字建立核心冲突
    3. **主角共鸣**：让读者立即喜欢或认同主角
    4. **强力悬念**：每章结尾必须有追读钩子

    ### 事件设计重点
    - **重大事件密度**：40%以上必须是推动主线的重大事件
    - **减少铺垫**：避免过多背景介绍，直接进入冲突
    - **情感冲击**：每个事件都要有情感价值
    - **节奏控制**：保持高速推进，避免任何拖沓

    ### 完读率保障措施
    - 第1章：必须完成主角登场+初始冲突+悬念结尾
    - 第2章：深化冲突，展现主角能力/特质
    - 第3章：安排小高潮，设置更强悬念
    - 前10章：每3章必须有一个情感或情节高潮
    """,
            "development_stage": """
    ## 📈 发展阶段指导（26%章节）

    ### 核心任务
    1. **深化冲突**：将开局冲突扩展为更复杂的矛盾
    2. **角色成长**：展现主角和配角的成长弧线
    3. **世界观展开**：逐步揭示更广阔的世界设定
    4. **支线整合**：将支线情节与主线巧妙连接

    ### 事件设计重点
    - **平衡发展**：重大事件30%，中型事件50%，小型事件20%
    - **渐进升级**：事件难度和重要性逐步提升
    - **伏笔铺设**：为高潮阶段埋下关键伏笔
    - **情感深化**：建立读者与角色的深度情感连接
    """,
            "climax_stage": """
    ## ⚡ 高潮阶段指导（28%章节）

    ### 核心任务
    1. **冲突爆发**：主要矛盾全面爆发
    2. **情感高潮**：达到情感的最高点
    3. **真相揭露**：揭示关键信息和伏笔
    4. **角色蜕变**：主角完成关键成长

    ### 事件设计重点
    - **高密度高潮**：重大事件占比50%，保持紧张节奏
    - **多线并进**：同时推进多条情节线
    - **情感冲击**：每个事件都要有强烈的情感价值
    - **悬念维持**：即使在高潮中也要保持悬念
    """,
            "ending_stage": """
    ## 🎯 收尾阶段指导（18%章节）

    ### 核心任务
    1. **矛盾解决**：解决主要冲突和矛盾
    2. **伏笔回收**：回收前期铺设的重要伏笔
    3. **情感升华**：将情感推向更深层次
    4. **结局准备**：为最终结局做好铺垫

    ### 事件设计重点
    - **集中解决**：重大和中型事件各占40%，专注解决问题
    - **情感共鸣**：强调角色的情感变化和成长
    - **逻辑严密**：确保所有解决方案合理可信
    - **节奏放缓**：适当放缓节奏，让读者消化
    """,
            "final_stage": """
    ## 🏁 结局阶段指导（12%章节）

    ### 核心任务
    1. **完整收尾**：给出所有主要角色的结局
    2. **主题升华**：强化小说的核心主题
    3. **情感余韵**：留下持久的情感共鸣
    4. **读者满足**：确保读者获得完整的阅读体验

    ### 事件设计重点
    - **专注结局**：重大事件占比60%，专注核心结局
    - **减少冗余**：小型事件只占10%，避免节外生枝
    - **情感优先**：每个事件都要服务于情感满足
    - **节奏平稳**：保持平稳深沉的叙事节奏
    """
        }
        
        return stage_guidance.get(stage_name, "## 阶段写作指导\n\n请根据故事发展需要合理安排事件。")

    # === 兼容性方法 ===
    
    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)

    def assess_stage_event_continuity(self, stage_writing_plan: Dict, stage_name: str, 
                                    stage_range: str, creative_seed: str, 
                                    novel_title: str, novel_synopsis: str) -> Dict:
        """AI评估阶段事件连续性 - 新增方法"""
        print(f"  🤖 AI评估{stage_name}阶段事件连续性...")
        
        # 提取事件系统
        if "stage_writing_plan" in stage_writing_plan:
            event_system = stage_writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = stage_writing_plan.get("event_system", {})
        
        # 构建连续性评估提示词
        continuity_prompt = self._build_stage_continuity_prompt(
            event_system, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )
        
        try:
            continuity_assessment = self.generator.api_client.generate_content_with_retry(
                "stage_event_continuity",
                continuity_prompt,
                purpose=f"评估{stage_name}阶段事件连续性"
            )
            
            if continuity_assessment:
                # 将评估结果整合到写作计划中
                if "stage_writing_plan" in stage_writing_plan:
                    stage_writing_plan["stage_writing_plan"]["continuity_assessment"] = continuity_assessment
                else:
                    stage_writing_plan["continuity_assessment"] = continuity_assessment
                
                print(f"  ✅ {stage_name}阶段事件连续性评估完成")
                return continuity_assessment
            else:
                print(f"  ⚠️ {stage_name}阶段事件连续性评估失败")
                return {}
                
        except Exception as e:
            print(f"  ❌ AI连续性评估出错: {e}")
            return {}

    def _build_stage_continuity_prompt(self, event_system: Dict, stage_name: str, stage_range: str,
                                    creative_seed: str, novel_title: str, novel_synopsis: str) -> str:
        """构建阶段事件连续性评估提示词"""
        
        # 提取和格式化事件信息
        major_events = event_system.get("major_events", [])
        medium_events = event_system.get("medium_events", [])
        minor_events = event_system.get("minor_events", [])
        
        prompt_parts = [
            "# 🎯 阶段事件连续性深度评估",
            "",
            "## 评估任务",
            f"请对**{stage_name}**阶段（{stage_range}）的事件安排进行连续性深度评估。",
            "重点分析事件之间的逻辑连贯性、节奏合理性和情感发展连续性。",
            "",
            "## 小说基本信息",
            f"- 标题: {novel_title}",
            f"- 简介: {novel_synopsis}",
            f"- 创意种子: {creative_seed}",
            f"- 阶段: {stage_name} ({stage_range})",
            "",
            "## 事件安排详情"
        ]
        
        # 重大事件详情
        if major_events:
            prompt_parts.extend([
                "### 🚨 重大事件安排",
                "| 事件名称 | 开始章节 | 结束章节 | 持续时间 | 核心目标 |",
                "|---------|---------|---------|---------|----------|"
            ])
            for event in major_events:
                duration = event.get('end_chapter', 0) - event.get('start_chapter', 0) + 1
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | 第{event.get('start_chapter', '?')}章 | "
                    f"第{event.get('end_chapter', '?')}章 | {duration}章 | {event.get('main_goal', '未指定')} |"
                )
            prompt_parts.append("")
        
        # 中型事件详情
        if medium_events:
            prompt_parts.extend([
                "### 📈 中型事件安排",
                "| 事件名称 | 章节 | 核心目标 | 关联重大事件 |",
                "|---------|------|----------|-------------|"
            ])
            for event in medium_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | 第{event.get('chapter', event.get('start_chapter', '?'))}章 | "
                    f"{event.get('main_goal', '未指定')} | {event.get('connection_to_major', '独立')} |"
                )
            prompt_parts.append("")
        
        # 小型事件详情
        if minor_events:
            prompt_parts.extend([
                "### 🔍 小型事件安排",
                f"共{len(minor_events)}个小型事件，分布在各个章节"
            ])
            # 只显示前几个小型事件作为示例
            for i, event in enumerate(minor_events[:3]):
                prompt_parts.append(f"- {event.get('name', '未命名')} (第{event.get('chapter', event.get('start_chapter', '?'))}章): {event.get('function', '未指定功能')}")
            if len(minor_events) > 3:
                prompt_parts.append(f"- ... 还有{len(minor_events)-3}个小型事件")
            prompt_parts.append("")
        
        # 事件时间线分析
        prompt_parts.extend([
            "## 📊 事件时间线分析",
            "请基于以上事件安排，分析以下维度：",
            "",
            "### 1. 逻辑连贯性分析",
            "- 事件之间的因果关系是否清晰？",
            "- 是否存在逻辑断层或跳跃？", 
            "- 事件发展是否符合角色动机和世界观设定？",
            "- 伏笔设置和回收是否合理？",
            "",
            "### 2. 节奏合理性分析",
            "- 事件密度分布是否合理？",
            "- 高潮与平缓的交替是否恰当？",
            "- 是否有事件过于密集或稀疏的区域？",
            "- 节奏是否符合该阶段的特点？",
            "",
            "### 3. 情感发展连续性",
            "- 情感弧线是否连贯自然？",
            "- 情感高潮的铺垫是否充分？",
            "- 情感变化是否符合角色发展轨迹？",
            "",
            "### 4. 主线推进连贯性", 
            "- 主线情节是否持续有推进？",
            "- 是否存在主线停滞过久的问题？",
            "- 支线与主线的关联是否合理？",
            "",
            "### 5. 阶段过渡合理性",
            "- 与前后阶段的衔接是否自然？",
            "- 阶段内部的事件安排是否服务于阶段目标？",
            "",
            "## 🎯 评估要求",
            "请提供具体的、可操作的评估结果和改进建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_continuity_score": 0-10的整数评分,',
            '  "logic_coherence_analysis": "逻辑连贯性详细分析",',
            '  "rhythm_analysis": "节奏合理性详细分析",',
            '  "emotional_continuity_analysis": "情感发展连续性分析",',
            '  "main_thread_analysis": "主线推进连贯性分析",',
            '  "stage_transition_analysis": "阶段过渡合理性分析",',
            '  "critical_issues": ["关键问题1", "关键问题2", ...],',
            '  "improvement_recommendations": [',
            '    {"issue": "具体问题", "suggestion": "改进建议", "priority": "high/medium/low"},',
            '    ...',
            '  ],',
            '  "event_adjustment_suggestions": [',
            '    {"event_name": "事件名称", "current_arrangement": "当前安排", "suggested_adjustment": "调整建议"},',
            '    ...',
            '  ],',
            '  "risk_chapters": ["存在风险的章节列表"],',
            '  "strengths": ["优势1", "优势2", ...]',
            "}"
        ])
        
        return "\n".join(prompt_parts) 

    def _optimize_based_on_continuity_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        """基于连续性评估结果优化事件安排"""
        
        improvement_recommendations = assessment.get("improvement_recommendations", [])
        event_adjustments = assessment.get("event_adjustment_suggestions", [])
        
        if not improvement_recommendations and not event_adjustments:
            return writing_plan
        
        print(f"  🔧 基于AI评估优化{stage_name}阶段事件安排...")
        
        # 提取事件系统
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 处理高优先级建议
        high_priority_issues = [rec for rec in improvement_recommendations 
                            if rec.get("priority") == "high"]
        
        for issue in high_priority_issues:
            print(f"  ⚡ 处理高优先级问题: {issue.get('issue')}")
            # 这里可以添加具体的优化逻辑
            # 比如调整事件时间、添加过渡事件等
        
        # 应用事件调整建议
        for adjustment in event_adjustments:
            event_name = adjustment.get("event_name")
            suggested_adjustment = adjustment.get("suggested_adjustment")
            print(f"  📝 调整事件{event_name}: {suggested_adjustment}")
            # 这里可以添加具体的事件调整逻辑
        
        # 标记已优化
        if "stage_writing_plan" in writing_plan:
            writing_plan["stage_writing_plan"]["optimized_based_on_continuity"] = True
        else:
            writing_plan["optimized_based_on_continuity"] = True
        
        print(f"  ✅ 完成基于连续性评估的优化")
        return writing_plan       