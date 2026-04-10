# -*- coding: utf-8 -*-
"""
V2 六层架构 - 渲染器
将各层数据模型渲染为Markdown格式的提示词
"""

from typing import List, Dict, Any
from .models import (
    CoreSetting, TacticalPlanning, GenreTechniques, WritingStyle, AIConstraints, SelfCheck,
    EmotionPlan, AssemblyContext
)


class BaseRenderer:
    """基础渲染器"""
    
    def render(self, data: Any) -> str:
        """渲染为字符串"""
        raise NotImplementedError
    
    def _section_header(self, title: str, level: int = 2) -> str:
        """生成章节标题"""
        return f"{'#' * level} {title}"
    
    def _bullet_list(self, items: List[str]) -> str:
        """生成无序列表"""
        return "\n".join(f"- {item}" for item in items)
    
    def _numbered_list(self, items: List[str]) -> str:
        """生成有序列表"""
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))
    
    def _quote(self, text: str) -> str:
        """生成引用"""
        return f"> {text}"


# ==================== Layer 1 Renderer ====================

class CoreSettingRenderer(BaseRenderer):
    """Layer 1: 核心设定渲染器"""
    
    def render(self, setting: CoreSetting) -> str:
        """渲染核心设定"""
        lines = [
            self._section_header("【Layer 1】核心设定（宪法级，全文遵守）"),
            "",
            self._section_header("世界观", 3),
            setting.worldview.overview,
            "",
            self._section_header("核心规则", 3),
        ]
        
        for rule in setting.worldview.core_rules:
            lines.extend([f"- **{rule.rule}**：{rule.description}"])
        
        lines.extend([
            "",
            self._section_header("力量体系", 3),
            f"- 体系名称：{setting.worldview.power_system.name}",
            f"- 等级划分：{' → '.join(setting.worldview.power_system.levels)}",
            f"- 升级方式：{setting.worldview.power_system.upgrade_method}",
            f"- 当前等级：{setting.worldview.power_system.current_level}",
            "",
            self._section_header("金手指", 3),
            f"- 名称：{setting.golden_finger.name}",
            f"- 类型：{setting.golden_finger.type}",
            f"- 核心机制：{setting.golden_finger.core_mechanism}",
            f"- 当前等级：{setting.golden_finger.current_level}",
            f"- 当前能力：{setting.golden_finger.current_ability}",
            "",
            self._section_header("主角人设", 3),
            f"- 姓名：{setting.protagonist.name}",
            f"- 性格标签：{', '.join(setting.protagonist.personality_tags)}",
            f"- 核心动机：{setting.protagonist.core_motivation}",
            f"- 口头禅：{', '.join(setting.protagonist.catchphrases)}",
        ])
        
        if setting.protagonist.forbidden_behaviors:
            lines.extend([
                "",
                "**🚫 禁止行为**：",
                self._bullet_list(setting.protagonist.forbidden_behaviors)
            ])
        
        lines.extend([
            "",
            self._section_header("核心卖点", 3),
            setting.core_selling_point,
            "",
            self._section_header("爽点公式", 3),
            f"标准结构：{setting.burst_formula.pattern}",
        ])
        
        if setting.burst_formula.shock_hierarchy:
            lines.append("震惊层级：")
            for level in setting.burst_formula.shock_hierarchy:
                lines.append(f"- {level.get('name', '')}：{level.get('scope', '')}")
        
        return "\n".join(lines)


# ==================== Layer 2 Renderer ====================

class TacticalPlanningRenderer(BaseRenderer):
    """Layer 2: 战术规划渲染器"""
    
    def render(self, planning: TacticalPlanning) -> str:
        """渲染战术规划"""
        chapter = planning.current_chapter
        
        lines = [
            self._section_header("【Layer 2】战术规划（批次级，本章执行）"),
            "",
            self._section_header("阶段信息", 3),
            f"- 阶段：{planning.current_stage.stage_name}（{planning.current_stage.chapter_range}）",
            f"- 核心任务：{planning.current_stage.core_mission}",
            "",
            self._section_header("本章规划", 3),
            f"- 章节号：第{chapter.chapter_num}章",
            f"- 类型：{chapter.chapter_type}",
            "",
            self._section_header("战术企图", 3),
        ]
        
        intent = chapter.tactical_intent
        if intent:
            lines.append(f"- 主要目标：{intent.get('primary_goal', '')}")
            emotion_target = intent.get('emotion_target', {})
            lines.append(f"- 情绪目标：{emotion_target.get('type', '')}（强度{emotion_target.get('intensity', '')}）")
        
        lines.extend([
            "",
            self._section_header("爽点设计", 3),
            f"- 打脸对象：{chapter.burst_design.target}",
            f"- 打脸方式：{chapter.burst_design.method}",
        ])
        
        if chapter.burst_design.rewards:
            lines.append("- 收获奖励：")
            for reward in chapter.burst_design.rewards:
                lines.append(f"  - {reward.get('type', '')}：{reward.get('content', '')}")
        
        lines.extend([
            "",
            self._section_header("钩子设计", 3),
            f"- 类型：{chapter.hook_design.type}",
            f"- 内容：{chapter.hook_design.content}",
        ])
        
        return "\n".join(lines)


# ==================== Layer 3 Renderer ====================

class GenreTechniquesRenderer(BaseRenderer):
    """Layer 3: 题材技法渲染器"""
    
    def render(self, techniques: GenreTechniques) -> str:
        """渲染题材技法"""
        lines = [
            self._section_header(f"【Layer 3】题材技法 - {techniques.genre}"),
            "",
            self._quote(techniques.description),
            "",
        ]
        
        # 震惊铺展顺序
        shock_prog = techniques.shock_progression
        if shock_prog:
            lines.extend([
                self._section_header("震惊铺展顺序（严禁使用'第一层/第二层'标签）", 3),
                f"_{shock_prog.get('description', '')}_",
                "",
            ])
            
            for step in shock_prog.get('steps', []):
                lines.extend([
                    f"**{step.get('order')}. {step.get('name')}**",
                    f"- 内容：{step.get('content')}",
                    f"- 格式：{step.get('format')}",
                ])
                if step.get('examples'):
                    lines.append(f"- 示例：{step['examples'][0]}")
                lines.append("")
        
        # 系统提示音
        if techniques.system_prompts:
            lines.extend([
                self._section_header("系统提示音模板", 3),
            ])
            for sp in techniques.system_prompts:
                lines.append(f"**{sp.type}**：`{sp.template}`")
            lines.append("")
        
        # 禁用元素
        if techniques.forbidden_elements:
            lines.extend([
                self._section_header("🚫 禁用元素（绝对不能出现）", 3),
            ])
            for fe in techniques.forbidden_elements:
                lines.extend([
                    f"**{fe.element}** - {fe.reason}",
                    f"- 示例：{', '.join(fe.examples[:3])}",
                ])
            lines.append("")
        
        # 必须元素
        if techniques.required_elements:
            lines.extend([
                self._section_header("✅ 必须元素（检查清单）", 3),
            ])
            for re in techniques.required_elements:
                severity_mark = {"critical": "🔴", "warning": "🟡", "recommended": "🟢"}.get(re.severity, "⚪")
                lines.append(f"{severity_mark} **{re.element}**：{re.check}")
            lines.append("")
        
        # 对话达成方式
        if techniques.dialogue_achievement:
            lines.extend([
                self._section_header("对话占比达成方式", 3),
            ])
            for dm in techniques.dialogue_achievement:
                lines.append(f"- {dm.method}（{dm.weight}）")
            lines.append("")
        
        return "\n".join(lines)


# ==================== Layer 4 Renderer ====================

class WritingStyleRenderer(BaseRenderer):
    """Layer 4: 文风技法渲染器"""
    
    def render(self, style: WritingStyle) -> str:
        """渲染文风技法"""
        return f"""{self._section_header("【Layer 4】文风技法 - 番茄快节奏爽文")}

{self._section_header("段落规范", 3)}
- 每段{style.paragraph.max_lines}行，多用换行
- 平均长度{style.paragraph.avg_length}
- 手机优先排版

{self._section_header("句子规范", 3)}
- 短句(<10字)占比≥{int(style.sentence.short_ratio * 100)}%
- 单句最长{style.sentence.max_length}字
- 口语化表达

{self._section_header("对话规范", 3)}
- 对话占比≥{int(style.dialogue.ratio * 100)}%，用引号{style.dialogue.format}包裹
- 一句一段

{self._section_header("节奏控制", 3)}
- 前300字必须有冲突/悬念
- 每1000字一个小爽点
- 章尾最后50字是钩子
- 禁止连续{style.pacing.no_dialogue_limit}字无对话

{self._section_header("震惊流技法", 3)}
- 先写反应，后写原因
- 层层递进，禁止跳级
- 数字量化，拒绝模糊
- 🚫 严禁使用'第一层/第二层'标签

{self._section_header("情绪控制", 3)}
- 一章内情绪转变至少{style.emotion_control.transitions_per_chapter}次
- 高潮部分情绪强度≥{style.emotion_control.climax_intensity}/10
- 爽后不能突然压抑
"""
    
    def render_default(self) -> str:
        """渲染默认文风配置（番茄快节奏爽文）"""
        return f"""{self._section_header("【Layer 4】文风技法 - 番茄快节奏爽文")}

{self._section_header("段落规范", 3)}
- 每段3-4行，多用换行
- 平均长度50-80字
- 手机优先排版

{self._section_header("句子规范", 3)}
- 短句(<10字)占比≥40%
- 单句最长25字
- 口语化表达

{self._section_header("对话规范", 3)}
- 对话占比≥50%，用引号""包裹
- 一句一段

{self._section_header("节奏控制", 3)}
- 前300字必须有冲突/悬念
- 每1000字一个小爽点
- 章尾最后50字是钩子
- 禁止连续200字无对话

{self._section_header("震惊流技法", 3)}
- 先写反应，后写原因
- 层层递进，禁止跳级
- 数字量化，拒绝模糊
- 🚫 严禁使用'第一层/第二层'标签

{self._section_header("情绪控制", 3)}
- 一章内情绪转变至少2次
- 高潮部分情绪强度≥8/10
- 爽后不能突然压抑
"""


# ==================== Layer 5 Renderer ====================

class AIConstraintsRenderer(BaseRenderer):
    """Layer 5: AI约束渲染器"""
    
    def render(self, constraints: AIConstraints, context: Dict[str, Any]) -> str:
        """渲染AI约束"""
        lines = [
            self._section_header("【Layer 5】AI约束 + 情绪曲线"),
            "",
            self._section_header("任务信息", 3),
            f"- 小说标题：《{context.get('novel_title', '未命名')}》",
            f"- 章节号：第{context.get('chapter_num', 0)}章",
            f"- 主角名：{context.get('protagonist_name', '主角')}",
        ]
        
        # 情绪曲线
        emotion_plan = context.get('emotion_plan')
        if emotion_plan:
            lines.extend([
                "",
                self._section_header("情绪曲线（网文节奏）", 3),
                f"- 本章类型：**{emotion_plan.chapter_type}**",
                f"- 整体曲线：**{emotion_plan.curve}**",
                "",
                "> ⚠️ **警告**：严禁使用传统的'起-承-转-合'节奏！",
                "> 网文节奏：前300字入戏，持续高爽，章尾钩子",
                "",
                self._section_header("分段情绪要求", 3),
            ])
            
            for segment in emotion_plan.breakdown:
                lines.extend([
                    f"**{segment.get('position')}** - {segment.get('emotion')}（强度{segment.get('intensity')}）",
                    f"- 内容：{segment.get('content')}",
                ])
                if segment.get('goal'):
                    lines.append(f"- 目标：{segment.get('goal')}")
                lines.append("")
        
        lines.extend([
            self._section_header("字数约束", 3),
            f"- 目标：{constraints.word_count.target}字",
            f"- 最低：{constraints.word_count.min}字",
            f"- 最高：{constraints.word_count.max}字",
            "",
            self._section_header("输出格式", 3),
            "必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：",
            "",
            "---标题---",
            "章节标题（8-14字，概括核心爽点，不要第X章前缀）",
            "",
            "---正文---",
            "章节正文内容（2000-2500字，直接写场景）",
            "",
            self._section_header("格式规范", 3),
            f"- 角色对话：用引号{constraints.format_rules.dialogue_wrapper}包裹",
            f"- 系统提示/弹幕：用{constraints.format_rules.system_wrapper}包裹",
            f"- 段落：每段不超过{constraints.format_rules.paragraph_max_lines}行",
            "",
            self._section_header("🚫 禁止事项", 3),
            "- 爽点回退（爽后突然压抑）",
            "- 预告欺诈（章尾预告不兑现）",
            "- 人设崩塌",
            "- 正文开头写'第X章'",
            "- 严禁使用'起-承-转-合'节奏",
        ])
        
        return "\n".join(lines)


# ==================== Layer 6 Renderer ====================

class SelfCheckRenderer(BaseRenderer):
    """Layer 6: 自检清单渲染器"""
    
    def render(self, self_check: SelfCheck, genre: str) -> str:
        """渲染自检清单"""
        lines = [
            self._section_header("【Layer 6】自检清单（生成后必须完成）"),
            "",
        ]
        
        # 写前自检
        if self_check.pre_writing:
            lines.extend([
                self._section_header("写前确认", 3),
            ])
            for item in self_check.pre_writing:
                mark = "🔴" if item.critical else "⚪"
                lines.append(f"- [ ] {mark} {item.item}")
            lines.append("")
        
        # 格式检查
        if self_check.post_writing_format:
            lines.extend([
                self._section_header("格式检查", 3),
            ])
            for item in self_check.post_writing_format:
                severity_mark = {"critical": "🔴", "warning": "🟡"}.get(item.severity, "⚪")
                lines.append(f"- [ ] {severity_mark} {item.item}")
            lines.append("")
        
        # 内容检查
        if self_check.post_writing_content:
            lines.extend([
                self._section_header("内容检查", 3),
            ])
            for item in self_check.post_writing_content:
                severity_mark = {"critical": "🔴", "warning": "🟡"}.get(item.severity, "⚪")
                lines.append(f"- [ ] {severity_mark} {item.item}")
            lines.append("")
        
        lines.extend([
            "",
            "## ⚠️ 重要",
            "**如果以上任何一项未通过，必须重新生成！**",
        ])
        
        return "\n".join(lines)


# ==================== 渲染器工厂 ====================

_renderers: Dict[str, BaseRenderer] = {}

def get_renderer(renderer_type: str) -> BaseRenderer:
    """获取渲染器实例（单例）"""
    global _renderers
    if renderer_type not in _renderers:
        renderer_map = {
            'core_setting': CoreSettingRenderer,
            'tactical_planning': TacticalPlanningRenderer,
            'genre_techniques': GenreTechniquesRenderer,
            'writing_style': WritingStyleRenderer,
            'ai_constraints': AIConstraintsRenderer,
            'self_check': SelfCheckRenderer
        }
        renderer_class = renderer_map.get(renderer_type)
        if renderer_class:
            _renderers[renderer_type] = renderer_class()
        else:
            raise ValueError(f"未知的渲染器类型: {renderer_type}")
    return _renderers[renderer_type]
