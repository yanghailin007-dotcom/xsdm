# -*- coding: utf-8 -*-
"""
V2 章节对话生成器

集成六层架构的章节生成流程

核心变化:
1. System Prompt = Layer 3 (题材技法) + Layer 4 (文风)
2. User Prompt = Layer 5 (AI约束+情绪曲线) + Layer 6 (自检) + 具体任务
3. 支持对话历史保持 Layer 1-2 (核心设定+战术规划)
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Iterator
from datetime import datetime

try:
    from .conversation_session_v2 import (
        LayeredConversationSession,
        LayeredSystemPrompt,
        LayeredUserPrompt
    )
except ImportError:
    from conversation_session_v2 import (
        LayeredConversationSession,
        LayeredSystemPrompt,
        LayeredUserPrompt
    )

logger = logging.getLogger(__name__)


class ChapterConversationV2:
    """
    V2 章节对话生成器
    
    整合六层架构的对话管理
    """
    
    def __init__(self, 
                 api_client: Any,
                 genre: str,
                 core_setting: str,
                 tactical_planning: str,
                 provider: str = "default",
                 temperature: float = 0.9,
                 writing_style: Dict = None):
        """
        初始化 V2 章节对话生成器
        
        Args:
            api_client: APIClient 实例
            genre: 题材名称（用于加载题材技法）
            core_setting: Layer 1 核心设定
            tactical_planning: Layer 2 战术规划
            provider: 模型提供商
            temperature: 温度参数
            writing_style: 写作风格配置（用于 Layer 4）
        """
        self.api_client = api_client
        self.genre = genre
        self.writing_style = writing_style
        
        # 加载各层内容
        self._load_layers(genre, core_setting, tactical_planning, writing_style)
        
        # 创建分层对话会话
        system_prompt = LayeredSystemPrompt(
            layer1_core_setting=self.layer1_content,
            layer2_tactical_planning=self.layer2_content,
            layer3_genre_techniques=self.layer3_content,
            layer4_writing_style=self.layer4_content
        )
        
        self.session = LayeredConversationSession(
            api_client=api_client,
            system_prompt=system_prompt,
            provider=provider,
            temperature=temperature,
            purpose_prefix=f"chapter_v2_{genre}",
            max_history=30  # 支持6章+总结，避免历史被截断
        )
        
        self.generated_chapters = []
        
        logger.info(f"[V2对话] 初始化完成 | 题材: {genre}")
    
    def _load_layers(self, genre: str, core_setting: str, tactical_planning: str, writing_style: Dict = None):
        """加载六层内容"""
        try:
            from .layer_loaders import GenreTechniquesLoader, AIConstraintsLoader, SelfCheckLoader
            from .renderers import GenreTechniquesRenderer, WritingStyleRenderer
        except ImportError:
            from layer_loaders import GenreTechniquesLoader, AIConstraintsLoader, SelfCheckLoader
            from renderers import GenreTechniquesRenderer, WritingStyleRenderer
        
        # Layer 1: 核心设定
        # 🔥 优化：保存完整圣经，但 system prompt 中只放精简锚点
        # 完整圣经将在批次第一章的 user prompt 中注入，后续章节通过对话历史保持
        self.core_setting_full = core_setting or ""
        self.layer1_content = self._extract_core_setting_anchor(core_setting)
        
        # Layer 2: 战术规划
        self.layer2_content = tactical_planning
        
        # Layer 3: 题材技法
        genre_loader = GenreTechniquesLoader()
        genre_data = genre_loader.load(genre)
        genre_renderer = GenreTechniquesRenderer()
        self.layer3_content = genre_renderer.render(genre_data)
        
        # Layer 4: 文风技法（优先使用传入的 writing_style）
        if writing_style:
            # 🔥 区分 dataclass（YAML加载）和 dict（前端/项目传入）
            if hasattr(writing_style, 'paragraph'):
                # dataclass 格式（如 WritingStyle）
                try:
                    style_renderer = WritingStyleRenderer()
                    self.layer4_content = style_renderer.render(writing_style)
                    logger.info(f"[V2对话] Layer 4 使用自定义文风(dataclass): {getattr(writing_style, 'name', '未命名')}")
                except Exception as e:
                    logger.warning(f"[V2对话] 渲染自定义文风失败，回退到默认: {e}")
                    self.layer4_content = self._get_default_writing_style()
            else:
                # dict 格式（前端/项目传入）
                try:
                    self.layer4_content = self._build_writing_style_from_config(writing_style)
                    logger.info(f"[V2对话] Layer 4 使用自定义文风(dict): {writing_style.get('name', writing_style.get('style_name', '未命名'))}")
                except Exception as e:
                    logger.warning(f"[V2对话] 构建自定义文风失败，回退到默认: {e}")
                    self.layer4_content = self._get_default_writing_style()
        else:
            self.layer4_content = self._get_default_writing_style()
        
        # Layer 5 & 6 将由每次调用时动态加载
        self.constraints_loader = AIConstraintsLoader()
        self.selfcheck_loader = SelfCheckLoader()
        
        logger.debug(f"[V2对话] Layer加载完成 | L3={len(self.layer3_content)} chars | L4={len(self.layer4_content)} chars")
    
    def _build_writing_style_from_config(self, writing_style: Dict) -> str:
        """
        从 dict 格式的 writing_style 构建 Layer 4 文风技法字符串
        兼容 project_info 格式 {style_id, style_name, style_config} 和 task 格式 {id, name, description}
        """
        # 统一提取配置
        if 'style_config' in writing_style:
            config = writing_style.get('style_config') or {}
            style_name = config.get('name') or config.get('style_name') or writing_style.get('style_name', '番茄快节奏爽文')
        else:
            config = writing_style or {}
            style_name = config.get('name') or config.get('style_name') or '番茄快节奏爽文'
        
        description = config.get('description', '快节奏、强情绪、强冲突')
        features = config.get('features', [])
        if isinstance(features, list) and features:
            features_str = '\n'.join([f"- {f}" for f in features[:5]])
        else:
            features_str = '- 快节奏叙事\n- 强情绪渲染\n- 高频冲突'
        
        taboos = config.get('taboos', [])
        if isinstance(taboos, list) and taboos:
            taboos_str = '\n'.join([f"- 禁止{t}" for t in taboos[:3]])
        else:
            taboos_str = '- 禁止注水\n- 禁止偏离主线'
        
        structure = config.get('structure_preference', {})
        if isinstance(structure, dict):
            chapter_length = structure.get('chapter_length', '3000-3500字')
            pacing = structure.get('pacing', '快节奏')
            cliffhanger = structure.get('cliffhanger', '章尾强钩子')
        else:
            chapter_length = '3000-3500字'
            pacing = '快节奏'
            cliffhanger = '章尾强钩子'
        
        return f"""### 【Layer 4】文风技法 - {style_name}

> {description}

#### 【Layer 4.1】风格特征
{features_str}

#### 【Layer 4.2】结构要求
- **单章长度**：{chapter_length}
- **叙事节奏**：{pacing}
- **收尾方式**：{cliffhanger}

#### 【Layer 4.3】段落规范
- 每段3-4行，多用换行
- 平均长度50-80字
- 手机优先排版

#### 【Layer 4.4】句子规范
- 短句(<10字)占比≥40%
- 单句最长25字
- 口语化表达，减少形容词

#### 【Layer 4.5】对话规范
- 对话占比≥40%，用引号包裹
- 一句一段，对话后接动作/反应
- 禁止连续150字无对话

#### 【Layer 4.6】震惊流技法
- 先写反应，后写原因
- 层层递进，禁止跳级
- 数字量化，拒绝模糊
- 🚫 严禁使用'第一层/第二层'标签

#### 【Layer 4.7】创作禁忌
{taboos_str}
"""
    
    def _extract_core_setting_anchor(self, core_setting: str, max_chars: int = 600) -> str:
        """从完整核心设定中提取精简锚点，用于 System Prompt"""
        if not core_setting:
            return ""
        anchor = core_setting[:max_chars].strip()
        return (
            f"{anchor}\n\n"
            f"[提示：完整核心设定圣经已在本批次第一章的生成指令中详细给出，"
            f"后续章节生成请严格遵循对话历史中的完整设定。]"
        )
    
    def generate_chapter(self,
                        chapter_number: int,
                        chapter_title: str,
                        outline_summary: str,
                        chapter_type: str = "打脸章",
                        emotion_config: Optional[Dict] = None,
                        custom_constraints: Optional[str] = None,
                        custom_selfcheck: Optional[str] = None,
                        current_plan: Optional[Dict] = None,
                        prev_plan: Optional[Dict] = None,
                        next_plan: Optional[Dict] = None,
                        stream: bool = False,
                        is_batch_start: bool = False) -> Optional[str]:
        """
        生成单个章节
        
        Args:
            chapter_number: 章节号
            chapter_title: 章节标题
            outline_summary: 本章概要
            chapter_type: 章节类型 (打脸章/收获章/危机章/铺垫章/爆发章)
            emotion_config: 情绪曲线配置（可选，默认根据 chapter_type）
            custom_constraints: 自定义AI约束（可选）
            custom_selfcheck: 自定义自检清单（可选）
            stream: 是否流式输出
            
        Returns:
            生成的章节内容
        """
        # 构建 Layer 5 (AI约束 + 情绪曲线)
        if custom_constraints:
            layer5_content = custom_constraints
        else:
            constraints = self.constraints_loader.load()
            layer5_content = self._format_constraints(constraints, chapter_number)
        
        # 添加情绪曲线
        if emotion_config:
            emotion_curve = self._format_emotion_curve_custom(emotion_config)
        else:
            emotion_curve = self._get_emotion_curve(chapter_type)
        
        layer5_content = f"{layer5_content}\n\n{emotion_curve}"
        
        # 构建 Layer 6 (自检清单) - 默认自检 + 自定义战术自检合并
        base_selfcheck = self._format_selfcheck(self.selfcheck_loader.load())
        if custom_selfcheck:
            layer6_content = f"{base_selfcheck}\n\n### 战术规划执行自检清单（输出前必须逐项确认）\n\n{custom_selfcheck}"
        else:
            layer6_content = base_selfcheck
        
        # 构建任务指令（注入上一章+本章+下一章详细战术规划）
        task_instruction = self._build_task_instruction(
            chapter_number=chapter_number,
            chapter_title=chapter_title,
            outline_summary=outline_summary,
            current_plan=current_plan,
            prev_plan=prev_plan,
            next_plan=next_plan
        )
        
        # 🔥 批次首次生成时，在任务指令前注入完整核心设定圣经
        # 后续章节通过对话历史保持记忆，避免每章都重复传递 3500 字 system prompt
        if is_batch_start and self.core_setting_full:
            task_instruction = (
                f"【核心设定圣经 - 本批次必须严格遵守】\n\n"
                f"{self.core_setting_full}\n\n"
                f"{'='*60}\n"
                f"{task_instruction}"
            )
            logger.info(f"[V2对话] 第{chapter_number}章为批次首章，已注入完整核心设定圣经 ({len(self.core_setting_full)} 字)")
        
        # 组合 User Prompt
        user_prompt = LayeredUserPrompt(
            layer5_ai_constraints=layer5_content,
            layer6_self_check=layer6_content,
            task_instruction=task_instruction
        )
        
        logger.info(f"[V2对话] 生成第{chapter_number}章 | 类型: {chapter_type} | User Prompt: {len(user_prompt.combine())} chars")
        
        # 发送消息
        if stream:
            return self.session.send_message_stream(
                user_prompt=user_prompt,
                purpose=f"chapter_{chapter_number}"
            )
        else:
            response = self.session.send_message(
                user_prompt=user_prompt,
                purpose=f"chapter_{chapter_number}"
            )
            
            if response:
                self.generated_chapters.append({
                    "chapter": chapter_number,
                    "title": chapter_title,
                    "type": chapter_type,
                    "content_length": len(response)
                })
            
            return response
    
    def generate_batch_summary(self, start_chapter: int, end_chapter: int) -> Optional[str]:
        """
        在当前对话会话中生成批次总结
        
        利用对话历史中的完整上下文，让 AI 直接总结已生成章节的进展。
        
        Args:
            start_chapter: 起始章节
            end_chapter: 结束章节
            
        Returns:
            JSON 格式的批次总结字符串
        """
        summary_prompt = f"""你现在需要为【第{start_chapter}-{end_chapter}章】生成批次总结。

【重要区分】
- 本次总结的对象是：**你刚才生成的第{start_chapter}-{end_chapter}章正文**。
- 如果对话历史开头包含"上一批次剧情状态"的内容，那是**上一批次的总结**，仅作剧情承接参考，**不要**把它纳入本次总结的 completed_events、pending_hooks、character_changes 或 world_changes 中。

【总结要求】
1. 只提取第{start_chapter}-{end_chapter}章内实际发生的事件、角色变化、世界变化、埋下的钩子。
2. completed_events 中的 chapter 字段必须严格落在 {start_chapter}-{end_chapter} 范围内。
3. pending_hooks 必须是第{start_chapter}-{end_chapter}章中明确埋下、但尚未解决的情节悬念。
4. resolved_hooks 必须是第{start_chapter}-{end_chapter}章中明确解决掉的旧钩子。
5. new_characters 必须是第{start_chapter}-{end_chapter}章中**首次登场**的有名角色（不要重复写之前已经登场的角色）。
6. character_changes 必须包含主角和关键配角在这几章里发生的状态、能力、立场、心态变化。
7. world_changes 必须包含系统升级、势力更迭、道具获得、规则变化等世界观层面的变动。

请严格按以下 JSON 格式输出（只输出 JSON，不要任何额外说明）：
{{
  "summary_text": "一句话总结这批章节的核心进展",
  "completed_events": [
    {{"chapter": 章节号, "event": "完成的事件", "significance": "high/medium/low"}}
  ],
  "character_states": {{
    "protagonist": {{"name": "主角名", "status": "当前状态/等级", "progress": "进度百分比或能力层级", "new_skills": []}},
    "new_characters": [
      {{"name": "新角色名", "role": "core/major/minor/enemy", "description": "简要人设", "introduced_chapter": 章节号}}
    ],
    "character_changes": [
      {{"name": "角色名", "change": "变化类型", "details": "具体变化描述", "chapter": 章节号}}
    ]
  }},
  "pending_hooks": [
    {{"chapter": 埋下章节, "content": "钩子内容", "priority": "high/medium/low"}}
  ],
  "resolved_hooks": [
    {{"chapter": 解决章节, "content": "已解决的钩子内容"}}
  ],
  "world_changes": [
    {{"type": "力量体系/势力/道具/规则", "description": "变化描述", "chapter": 章节号}}
  ],
  "plot_direction": "下一批应该推进的方向建议（50字以内）",
  "stage_progress_assessment": "阶段目标完成度评估(0-100)及原因"
}}
"""
        try:
            response = self.session.send_message(
                user_prompt=summary_prompt,
                purpose=f"batch_summary_{start_chapter}_{end_chapter}"
            )
            logger.info(f"[V2对话] 批次总结生成成功 ({len(response) if response else 0}字)")
            return response
        except Exception as e:
            logger.error(f"[V2对话] 批次总结生成失败: {e}")
            return None
    
    def _get_default_writing_style(self) -> str:
        """获取默认文风技法"""
        return """### 【Layer 4】文风技法 - 番茄快节奏爽文

#### 段落规范
- 每段3-4行，多用换行
- 平均长度50-80字
- 手机优先排版

#### 句子规范
- 短句(<10字)占比≥40%
- 单句最长25字
- 口语化表达

#### 对话规范
- 对话占比≥30%，用引号""包裹
- 一句一段

#### 节奏控制
- 前300字必须有冲突/悬念
- 每1000字一个小爽点
- 章尾最后50字是钩子
- 禁止连续200字无对话

#### 叙事视角（强制）
- **必须采用第三人称上帝视角**
- 禁止第一人称「我」、第二人称「你」、日记体、书信体
- 主角名字直接使用，禁止连续用「他」超过3次而不提名字

#### 震惊流技法
- 先写反应，后写原因
- 层层递进，禁止跳级
- 数字量化，拒绝模糊
- 严禁使用'第一层/第二层'标签

#### 情绪控制
- 一章内情绪转变至少2次
- 高潮部分情绪强度≥8/10
- 爽后不能突然压抑
"""
    
    def _get_emotion_curve(self, chapter_type: str) -> str:
        """获取情绪曲线文本"""
        # 内置情绪曲线模板
        emotion_templates = {
            "打脸章": {
                "curve": "虐(4)→急(7)→爽(9)→悬(7)",
                "breakdown": [
                    {"position": "0-20%", "emotion": "虐", "intensity": 4, "technique": "铺垫压抑场景"},
                    {"position": "20-50%", "emotion": "急", "intensity": 7, "technique": "冲突升级"},
                    {"position": "50-80%", "emotion": "爽", "intensity": 9, "technique": "主角反击高潮"},
                    {"position": "80-100%", "emotion": "悬", "intensity": 7, "technique": "结尾留钩子"},
                ]
            },
            "爆发章": {
                "curve": "蓄(3)→爆(10)→收(5)",
                "breakdown": [
                    {"position": "0-30%", "emotion": "蓄势", "intensity": 3, "technique": "铺垫积累"},
                    {"position": "30-70%", "emotion": "爆发", "intensity": 10, "technique": "全力释放高潮"},
                    {"position": "70-100%", "emotion": "收尾", "intensity": 5, "technique": "结果展示+悬念"},
                ]
            },
            "收获章": {
                "curve": "争(6)→得(8)→惊(7)",
                "breakdown": [
                    {"position": "0-30%", "emotion": "争夺", "intensity": 6, "technique": "多方竞争"},
                    {"position": "30-70%", "emotion": "获得", "intensity": 8, "technique": "主角得到宝物"},
                    {"position": "70-100%", "emotion": "震惊", "intensity": 7, "technique": "众人反应"},
                ]
            },
            "危机章": {
                "curve": "安(3)→危(8)→逃(6)",
                "breakdown": [
                    {"position": "0-20%", "emotion": "安稳", "intensity": 3, "technique": "平静开局"},
                    {"position": "20-60%", "emotion": "危机", "intensity": 8, "technique": "突发危机"},
                    {"position": "60-100%", "emotion": "逃脱", "intensity": 6, "technique": "惊险脱身"},
                ]
            },
            "铺垫章": {
                "curve": "平(4)→伏(5)→引(6)",
                "breakdown": [
                    {"position": "0-40%", "emotion": "平静", "intensity": 4, "technique": "日常描写"},
                    {"position": "40-80%", "emotion": "伏笔", "intensity": 5, "technique": "埋设线索"},
                    {"position": "80-100%", "emotion": "引子", "intensity": 6, "technique": "引出下文"},
                ]
            },
        }
        
        data = emotion_templates.get(chapter_type, emotion_templates["打脸章"])
        
        lines = ["### 情绪节奏规划"]
        lines.append(f"章节类型: {chapter_type}")
        lines.append(f"曲线: {data['curve']}")
        lines.append("")
        lines.append("情绪点位:")
        for point in data['breakdown']:
            lines.append(f"  - {point['position']}: {point['emotion']} ({point['intensity']}分) - {point['technique']}")
        
        return "\n".join(lines)
    
    def _format_constraints(self, constraints, chapter_number: int) -> str:
        """格式化AI约束"""
        lines = ["### AI约束"]
        
        # 处理 dataclass 类型
        if hasattr(constraints, 'word_count'):
            wc = constraints.word_count
            lines.append(f"字数要求: {wc.min}-{wc.max}字 (目标{wc.target}字)")
        
        if hasattr(constraints, 'format_rules') and constraints.format_rules:
            fmt = constraints.format_rules
            lines.append(f"格式: 对话使用{fmt.dialogue_wrapper}包裹, 系统提示使用{fmt.system_wrapper}包裹")
        
        if hasattr(constraints, 'forbidden') and constraints.forbidden:
            forbidden_items = [f["description"] for f in constraints.forbidden if isinstance(f, dict)]
            if forbidden_items:
                lines.append(f"禁止: {', '.join(forbidden_items[:3])}")
        
        # 追加固定约束（Layer 5 关键项，避免过于单薄）
        lines.extend([
            "段落: 每段3-4行，多用换行，平均长度50-80字",
            "对话: 对话占比≥30%，用引号\"\"包裹，一句一段",
            "节奏: 短句(<10字)占比≥40%，单句最长25字",
            "结尾: 章尾必须留钩子（悬念/转折/期待），位于最后50字内"
        ])
        
        return "\n".join(lines)
    
    def _format_emotion_curve_custom(self, config: Dict) -> str:
        """格式化自定义情绪曲线"""
        lines = ["### 情绪节奏规划"]
        emotion = config.get("emotion")
        intensity = config.get("intensity")
        emotion_type = config.get("emotion_type")
        if emotion or intensity is not None:
            lines.append(f"核心情绪: {emotion or '待定'} (强度: {intensity if intensity is not None else 5}/10)")
        if emotion_type:
            lines.append(f"情绪类型: {emotion_type}")
        lines.append(f"章节类型: {config.get('type', '自定义')}")
        if "curve" in config:
            lines.append(f"曲线: {config['curve']}")
        if "points" in config:
            lines.append("情绪点位:")
            for p in config["points"]:
                lines.append(f"  - {p}")
        return "\n".join(lines)
    
    def _format_selfcheck(self, selfcheck) -> str:
        """格式化自检清单"""
        lines = ["### 自检清单（输出前逐项确认）"]
        
        # 处理 dataclass 类型
        all_items = []
        
        if hasattr(selfcheck, 'pre_writing') and selfcheck.pre_writing:
            lines.append("\n【写作前】")
            for item in selfcheck.pre_writing[:3]:  # 最多3项
                all_items.append(item.item if hasattr(item, 'item') else str(item))
                lines.append(f"□ {all_items[-1]}")
        
        if hasattr(selfcheck, 'post_writing_content') and selfcheck.post_writing_content:
            lines.append("\n【写作后-内容检查】")
            for item in selfcheck.post_writing_content[:3]:
                all_items.append(item.item if hasattr(item, 'item') else str(item))
                lines.append(f"□ {all_items[-1]}")
        
        if hasattr(selfcheck, 'post_writing_genre') and selfcheck.post_writing_genre:
            lines.append("\n【写作后-题材检查】")
            for item in selfcheck.post_writing_genre[:3]:
                all_items.append(item.item if hasattr(item, 'item') else str(item))
                lines.append(f"□ {all_items[-1]}")
        
        return "\n".join(lines)
    
    def _build_task_instruction(self, 
                               chapter_number: int,
                               chapter_title: str,
                               outline_summary: str,
                               current_plan: Optional[Dict] = None,
                               prev_plan: Optional[Dict] = None,
                               next_plan: Optional[Dict] = None) -> str:
        """构建任务指令（章节标题由AI生成，不预传入）"""
        lines = [
            "=" * 60,
            f"【任务】生成第 {chapter_number} 章",
            "=" * 60,
            "【本章概要】",
            outline_summary,
            "",
        ]
        
        # 上一章战术规划（承接）
        if prev_plan:
            lines.extend([
                "【上一章承接】",
                f"- 事件: {prev_plan.get('event', '')}",
                f"- 遗留钩子: {prev_plan.get('hook_content', '')}",
                "",
            ])
        
        # 本章详细战术指令
        if current_plan:
            lines.extend([
                "【本章战术指令 - 必须逐条执行】",
                f"1. 核心事件: {current_plan.get('event', '')}",
            ])
            sp = current_plan.get('satisfaction_point')
            if sp:
                lines.append(f"2. 爽点交付: {sp}")
            fp = current_plan.get('face_slapping')
            if fp and isinstance(fp, dict):
                lines.append(f"3. 打脸路径: 目标={fp.get('target','')}, 方式={fp.get('method','')}, 震惊层级={fp.get('shock_level','')}")
            elif fp:
                lines.append(f"3. 打脸路径: {fp}")
            lines.extend([
                f"4. 情绪目标: {current_plan.get('emotion', '期待')} (强度{current_plan.get('intensity', 5)})",
                f"5. 钩子落点: 章尾50字内必须出现与 \"{current_plan.get('hook_content', '')}\" 相关的悬念",
                f"6. 系统提示音插入点: {current_plan.get('system_prompt_moment', '在主角获得返利/奖励时插入')}",
                "",
            ])
        
        # 下一章预告（用于指导本章结尾钩子）
        if next_plan:
            lines.extend([
                "【下一章预告 - 本章结尾必须为下文埋钩】",
                f"- 核心事件: {next_plan.get('event', '')}",
                f"- 情绪承接: {next_plan.get('emotion', '期待')} (强度{next_plan.get('intensity', 5)})",
                "",
            ])
        
        lines.extend([
            "【前章生成状态】",
        ])
        
        # 添加上一章概要（如果有）
        if self.generated_chapters:
            last = self.generated_chapters[-1]
            lines.append(f"第{last['chapter']}章《{last['title']}》已生成 ({last['content_length']} 字)")
        elif prev_plan:
            prev_num = prev_plan.get('chapter_number', chapter_number - 1)
            prev_title = prev_plan.get('chapter_title', '') or '（未知标题）'
            lines.append(f"第{prev_num}章《{prev_title}》已生成")
        else:
            lines.append("本章为小说开篇第一章")
        
        lines.extend([
            "",
            "【输出要求 - 违反任何一条都会导致内容被丢弃】",
            "1. 字数必须严格控制在 2000-2500 字之间（绝对禁止超过2500字）",
            "2. 严格遵循上述情绪曲线规划",
            "3. 使用指定的题材技法和文风",
            "4. 确保自检清单全部通过",
            "5. 只输出章节正文，不要输出大纲或分析",
            "6. 必须严格使用第三人称上帝视角，禁止任何第一人称叙述",
            "7. 【硬规则】章节最后 1-3 段必须是钩子，总字数≤60 字。钩子句出现后必须立即停止，禁止继续写进屋、对话、解释或心理活动",
            "8. 【硬规则】严禁输出「下一章预告」「本章完」「未完待续」等任何非正文内容",
            "9. 【字数自救】如果生成到 2100 字仍未收尾，立即删除所有环境描写和路人重复反应，只保留 1 句核心动作 + 钩子句",
            "",
            "【强制输出格式 - 必须严格遵守】",
            "必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：",
            "",
            "---标题---",
            "章节标题（8-14字，概括核心爽点，不要'第X章'前缀）",
            "",
            "---正文---",
            "章节正文内容（2000-2500字，直接写场景）",
            "",
            "⚠️ 警告：",
            "- 标题必须放在 ---标题--- 后面",
            "- 正文必须放在 ---正文--- 后面",
            "- 禁止只返回纯文本",
            "- 正文开头禁止写'第X章：XXX'",
            "",
            "【字数控制技巧】",
            "- 如果剧情包含多个场景，优先压缩环境描写和心理独白，保留核心冲突和对话",
            "- 每个场景用对话直接推进，删除不必要的神态/动作铺陈",
            "- 系统提示保持简洁，不要连续出现多个长段落",
            "- 如果预估会超过2500字，请在高潮后迅速收尾，把后续悬念留到下一章",
            "",
            "请开始生成章节内容（必须在2000-2500字之间）：",
        ])
        
        return "\n".join(lines)
    
    def refresh_session(self):
        """刷新会话（保持 System Prompt，清空对话历史）"""
        self.session.clear_history(keep_system=True)
        logger.info("[V2对话] 会话已刷新")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计"""
        stats = self.session.get_stats()
        stats["generated_chapters"] = len(self.generated_chapters)
        stats["genre"] = self.genre
        return stats


# ==================== 便捷创建函数 ====================

def create_chapter_conversation_v2(
    api_client: Any,
    novel_state: Dict[str, Any]
) -> ChapterConversationV2:
    """
    从小说状态创建 V2 章节对话生成器
    
    Args:
        api_client: APIClient 实例
        novel_state: 小说状态字典，包含 genre, core_setting, tactical_planning 等
    
    Returns:
        ChapterConversationV2 实例
    """
    genre = novel_state.get("genre", "通用")
    core_setting = novel_state.get("core_setting", "")
    tactical_planning = novel_state.get("tactical_planning", "")
    
    # 如果没有战术规划，尝试从其他字段构建
    if not tactical_planning:
        tactical_parts = []
        if "current_phase" in novel_state:
            tactical_parts.append(f"当前阶段: {novel_state['current_phase']}")
        if "phase_goals" in novel_state:
            tactical_parts.append(f"阶段目标: {novel_state['phase_goals']}")
        tactical_planning = "\n".join(tactical_parts)
    
    return ChapterConversationV2(
        api_client=api_client,
        genre=genre,
        core_setting=core_setting,
        tactical_planning=tactical_planning,
        provider=novel_state.get("provider", "default"),
        temperature=novel_state.get("temperature", 0.9)
    )


# ==================== 测试 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("测试 V2 章节对话生成器")
    print("=" * 80)
    
    # 测试数据
    test_genre = "都市逆袭-神豪流"
    test_core = "主角获得百倍消费返利系统，从平凡走向巅峰"
    test_tactical = "第一阶段：获得系统，初次展现实力"
    
    # 模拟 APIClient
    class MockAPIClient:
        default_provider = "kimi"
        
        def _call_with_messages(self, messages, **kwargs):
            return "【模拟响应】这是生成的章节内容..."
    
    api_client = MockAPIClient()
    
    # 创建对话生成器
    try:
        conversation = ChapterConversationV2(
            api_client=api_client,
            genre=test_genre,
            core_setting=test_core,
            tactical_planning=test_tactical
        )
        
        print(f"[OK] 对话生成器创建成功")
        print(f"  - 题材: {conversation.genre}")
        print(f"  - Layer 3 长度: {len(conversation.layer3_content)} 字符")
        print(f"  - Layer 4 长度: {len(conversation.layer4_content)} 字符")
        
        # 测试生成章节
        print("\n测试生成章节...")
        result = conversation.generate_chapter(
            chapter_number=1,
            chapter_title="初入禁地",
            outline_summary="主角觉醒酒剑仙模板，进入禁地",
            chapter_type="爆发章"
        )
        print(f"[OK] 第1章生成完成: {len(result) if result else 0} 字符")
        
        # 显示统计
        stats = conversation.get_session_stats()
        print(f"\n会话统计:")
        print(f"  - 对话轮数: {stats['turn_count']}")
        print(f"  - 生成章节数: {stats['generated_chapters']}")
        
    except Exception as e:
        print(f"[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
