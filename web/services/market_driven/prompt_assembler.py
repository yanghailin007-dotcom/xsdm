# -*- coding: utf-8 -*-
"""
提示词组装器 (PromptAssembler)

按照六层架构动态组装System Prompt
核心功能：根据题材动态加载对应的技法
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .genre_techniques_loader import (
    GenreTechniquesLoader, 
    load_genre_techniques,
    GenreTechniques
)

logger = logging.getLogger(__name__)


class PromptAssembler:
    """
    提示词组装器
    
    将六层内容动态组装成完整System Prompt：
    Layer 1: 核心设定
    Layer 2: 战术规划
    Layer 3: 题材技法 ⭐核心分离层
    Layer 4: 文风技法
    Layer 5: AI约束
    Layer 6: 自检清单
    """
    
    def __init__(self, genre: str):
        """
        初始化组装器
        
        Args:
            genre: 题材名称（如：国运文、神豪文）
        """
        self.genre = genre
        self.genre_loader = GenreTechniquesLoader()
        
        # 加载题材技法（Layer 3）
        try:
            self.genre_techniques = self.genre_loader.load(genre)
            logger.info(f"[PromptAssembler] 已加载题材技法: {genre}")
        except Exception as e:
            logger.error(f"[PromptAssembler] 加载题材技法失败: {e}")
            # 回退到通用
            self.genre_techniques = self.genre_loader.load("通用")
    
    def assemble(
        self,
        novel_title: str = "未命名",
        chapter_num: int = 0,
        protagonist_name: str = "主角",
        core_setting: Optional[Dict] = None,
        tactical_plan: Optional[Dict] = None,
        emotion_plan: Optional[Dict] = None,
        chapter_type: str = "打脸章"
    ) -> str:
        """
        组装完整System Prompt
        
        Args:
            novel_title: 小说标题
            chapter_num: 章节号
            protagonist_name: 主角名
            core_setting: 核心设定（Layer 1）
            tactical_plan: 战术规划（Layer 2）
            emotion_plan: 情绪规划（新网文节奏，替代emotion_curve）
            chapter_type: 章节类型（打脸章/收获章/危机章/揭秘章）
        
        Returns:
            完整的System Prompt字符串
        """
        # 如果没有提供情绪规划，根据章节类型生成
        if emotion_plan is None:
            emotion_plan = self._get_emotion_plan(chapter_type)
        
        sections = []
        
        # Layer 1: 核心设定
        if core_setting:
            sections.append(self._build_layer1_core_setting(core_setting))
        
        # Layer 2: 战术规划
        if tactical_plan:
            sections.append(self._build_layer2_tactical_plan(tactical_plan))
        
        # Layer 3: 题材技法 ⭐核心
        sections.append(self._build_layer3_genre_techniques())
        
        # Layer 4: 文风技法
        sections.append(self._build_layer4_writing_style())
        
        # Layer 5: AI约束 + 情绪曲线
        sections.append(self._build_layer5_ai_constraints(
            novel_title, chapter_num, protagonist_name, emotion_plan
        ))
        
        # Layer 6: 自检清单
        sections.append(self._build_layer6_self_check())
        
        return "\n\n".join(filter(None, sections))
    
    def _get_emotion_plan(self, chapter_type: str) -> Dict:
        """
        根据章节类型获取情绪规划
        
        Args:
            chapter_type: 章节类型（打脸章/收获章/危机章/揭秘章/过渡章）
        
        Returns:
            情绪规划字典
        """
        templates = {
            "打脸章": {
                "chapter_type": "打脸章",
                "curve": "虐(4)→急(7)→爽(9)→悬(7)",
                "breakdown": [
                    {"position": "0-300字", "emotion": "虐", "intensity": 4, "content": "反派嚣张，主角被看不起", "goal": "让读者感到憋屈，期待反转"},
                    {"position": "300-1500字", "emotion": "急", "intensity": 7, "content": "冲突爆发，主角展现实力", "goal": "紧张刺激，打脸过程"},
                    {"position": "1500-2000字", "emotion": "爽", "intensity": 9, "content": "反派被打脸，众人震惊", "goal": "爽感最大化"},
                    {"position": "2000-2200字", "emotion": "悬", "intensity": 7, "content": "新钩子出现", "goal": "让读者想看下章"},
                ]
            },
            "收获章": {
                "chapter_type": "收获章",
                "curve": "悬(7)→惊(8)→爽(10)→悬(7)",
                "breakdown": [
                    {"position": "0-300字", "emotion": "悬", "intensity": 7, "content": "面临挑战/考验"},
                    {"position": "300-1500字", "emotion": "惊", "intensity": 8, "content": "通过考验，获得奖励"},
                    {"position": "1500-2000字", "emotion": "爽", "intensity": 10, "content": "展示收获，震惊众人"},
                    {"position": "2000-2200字", "emotion": "悬", "intensity": 7, "content": "新目标/新挑战"},
                ]
            },
            "危机章": {
                "chapter_type": "危机章",
                "curve": "怕(8)→虐(5)→燃(10)→爽(8)",
                "breakdown": [
                    {"position": "0-300字", "emotion": "怕", "intensity": 8, "content": "危机降临，生死存亡"},
                    {"position": "300-1500字", "emotion": "虐", "intensity": 5, "content": "绝境挣扎，寻找生机"},
                    {"position": "1500-2000字", "emotion": "燃", "intensity": 10, "content": "逆转取胜，绝境重生"},
                    {"position": "2000-2200字", "emotion": "爽", "intensity": 8, "content": "胜利但留下隐患"},
                ]
            },
            "揭秘章": {
                "chapter_type": "揭秘章",
                "curve": "悬(8)→惊(7)→惊(9)→惊(10)→悬(9)",
                "breakdown": [
                    {"position": "0-300字", "emotion": "悬", "intensity": 8, "content": "悬念加深，谜团重重"},
                    {"position": "300-1500字", "emotion": "惊", "intensity": 7, "content": "逐步揭秘，层层反转"},
                    {"position": "1500-2000字", "emotion": "惊", "intensity": 10, "content": "核心真相揭露"},
                    {"position": "2000-2200字", "emotion": "悬", "intensity": 9, "content": "更大谜团出现"},
                ]
            },
            "过渡章": {
                "chapter_type": "过渡章",
                "curve": "悬(6)→平(5)→悬(7)",
                "note": "尽量缩短，不要过多过渡章",
                "breakdown": [
                    {"position": "0-1000字", "emotion": "悬", "intensity": 6, "content": "承接上文，新线索"},
                    {"position": "1000-1800字", "emotion": "平", "intensity": 5, "content": "信息补充，世界观展开"},
                    {"position": "1800-2000字", "emotion": "悬", "intensity": 7, "content": "强钩子，引出下章"},
                ]
            }
        }
        
        return templates.get(chapter_type, templates["打脸章"])
    
    def _build_layer1_core_setting(self, core_setting: Dict) -> str:
        """
        构建Layer 1: 核心设定
        """
        lines = [
            "# 【Layer 1】核心设定",
            "",
            "## 世界观",
            core_setting.get('worldview', '未设定'),
            "",
            "## 金手指",
            core_setting.get('golden_finger', '未设定'),
            "",
            "## 主角人设",
            core_setting.get('protagonist', '未设定'),
        ]
        return "\n".join(lines)
    
    def _build_layer2_tactical_plan(self, tactical_plan: Dict) -> str:
        """
        构建Layer 2: 战术规划
        """
        lines = [
            "# 【Layer 2】战术规划",
            "",
            f"## 本章类型: {tactical_plan.get('chapter_type', '未设定')}",
            f"## 战术企图: {tactical_plan.get('tactical_intent', '未设定')}",
            f"## 爽点设计: {tactical_plan.get('burst_design', '未设定')}",
        ]
        return "\n".join(lines)
    
    def _build_layer3_genre_techniques(self) -> str:
        """
        构建Layer 3: 题材技法 ⭐核心分离层
        
        这是题材分离的关键，根据genre动态生成不同的技法指导
        """
        gt = self.genre_techniques
        lines = [
            f"# 【Layer 3】题材技法 - {gt.genre}",
            "",
            f"> {gt.description}",
            "",
        ]
        
        # 1. 震惊铺展顺序
        shock_prog = gt.shock_progression
        if shock_prog:
            lines.extend([
                "## 震惊铺展顺序（严禁使用'第一层/第二层'标签）",
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
        
        # 2. 题材特定规则
        if gt.barrage_rules:
            # 国运文：弹幕规则
            br = gt.barrage_rules
            lines.extend([
                "## 弹幕规范（国运文核心）",
                f"- **数量要求**：每章至少{br.get('min_count', 8)}条",
                f"- **格式**：{br.get('format', '【ID：内容】')}",
                "",
                "### 弹幕模板",
            ])
            for template in br.get('templates', []):
                lines.extend([
                    f"**{template.get('type')}**（{template.get('emotion')}）",
                ])
                for ex in template.get('examples', [])[:2]:  # 只显示前2个示例
                    lines.append(f"- {ex}")
                lines.append("")
        
        if gt.money_rules:
            # 神豪文：金钱规则
            mr = gt.money_rules
            lines.extend([
                "## 金钱规范（神豪文核心）",
                f"- **精度**：{mr.get('precision', '精确到小数点后2位')}",
                f"- **禁止词汇**：{', '.join(mr.get('forbidden_words', [])[:5])}...",
                "",
                "### 正确示例",
            ])
            for ex in mr.get('examples', {}).get('correct', [])[:3]:
                lines.append(f"- ✅ {ex}")
            lines.append("")
        
        # 3. 系统提示音
        if gt.system_prompts:
            lines.extend([
                "## 系统提示音模板",
            ])
            for sp in gt.system_prompts:
                lines.append(f"**{sp.type}**：`{sp.template}`")
            lines.append("")
        
        # 4. 路人心理活动模板（神豪文）
        if gt.bystander_templates:
            lines.extend([
                "## 路人心理活动模板",
            ])
            for tmpl in gt.bystander_templates.get('templates', []):
                lines.append(f"- {tmpl.get('examples', [''])[0]}")
            lines.append("")
        
        # 5. 禁用元素（关键！）
        if gt.forbidden_elements.get('items'):
            lines.extend([
                "## 🚫 禁用元素（绝对不能出现）",
            ])
            for item in gt.forbidden_elements['items']:
                lines.extend([
                    f"**{item.element}** - {item.reason}",
                    f"- 示例：{', '.join(item.examples[:3])}",
                ])
            lines.append("")
        
        # 6. 必须元素（检查清单）
        if gt.required_elements.get('items'):
            lines.extend([
                "## ✅ 必须元素（检查清单）",
            ])
            for item in gt.required_elements['items']:
                severity_mark = {"critical": "🔴", "warning": "🟡", "recommended": "🟢"}.get(item.severity, "⚪")
                lines.append(f"{severity_mark} **{item.element}**：{item.check}")
            lines.append("")
        
        # 7. 对话占比达成方式
        da = gt.dialogue_achievement
        if da:
            lines.extend([
                f"## 对话占比达成方式（目标：{da.get('target', '≥50%')}）",
            ])
            for method in da.get('methods', []):
                lines.append(f"- {method.get('method')}（{method.get('weight', '未知权重')}）")
            lines.append("")
        
        return "\n".join(lines)
    
    def _build_layer4_writing_style(self) -> str:
        """
        构建Layer 4: 文风技法
        """
        lines = [
            "# 【Layer 4】文风技法 - 番茄快节奏爽文",
            "",
            "## 段落规范",
            "- 每段1-3行，多用换行",
            "- 平均长度30-50字",
            "- 手机优先排版",
            "",
            "## 句子规范",
            "- 短句(<10字)占比≥60%",
            "- 单句最长15字",
            "- 口语化表达",
            "",
            "## 对话规范",
            '- 对话占比≥50%，用引号""包裹',
            "- 一句一段",
            "",
            "## 节奏控制",
            "- 前300字必须有冲突/悬念",
            "- 每1000字一个小爽点",
            "- 章尾最后50字是钩子",
            "- 禁止连续200字无对话",
            "",
            "## 震惊流技法",
            "- 先写反应，后写原因",
            "- 层层递进，禁止跳级",
            "- 数字量化，拒绝模糊",
            "- 🚫 严禁使用'第一层震惊/第二层震惊'标签",
        ]
        return "\n".join(lines)
    
    def _build_layer5_ai_constraints(
        self,
        novel_title: str,
        chapter_num: int,
        protagonist_name: str,
        emotion_plan: Optional[Dict] = None
    ) -> str:
        """
        构建Layer 5: AI约束 + 情绪曲线（网文版）
        """
        # 默认使用打脸章情绪曲线
        if emotion_plan is None:
            emotion_plan = {
                "chapter_type": "打脸章",
                "curve": "虐(4)→急(7)→爽(9)→悬(7)",
                "breakdown": [
                    {"position": "0-300字", "emotion": "虐", "intensity": 4, "content": "反派嚣张，主角被看不起"},
                    {"position": "300-1500字", "emotion": "急", "intensity": 7, "content": "冲突爆发，主角展现实力"},
                    {"position": "1500-2000字", "emotion": "爽", "intensity": 9, "content": "反派被打脸，众人震惊"},
                    {"position": "2000-2200字", "emotion": "悬", "intensity": 7, "content": "新钩子出现"},
                ]
            }
        
        lines = [
            "# 【Layer 5】AI约束 + 情绪曲线",
            "",
            f"## 任务信息",
            f"- 小说标题：《{novel_title}》",
            f"- 章节号：第{chapter_num}章",
            f"- 主角名：{protagonist_name}",
            "",
            "## 情绪曲线（网文节奏）",
            f"- 本章类型：**{emotion_plan.get('chapter_type', '打脸章')}**",
            f"- 整体曲线：**{emotion_plan.get('curve', '虐(4)→急(7)→爽(9)→悬(7)')}**",
            "",
            "> ⚠️ **警告**：严禁使用传统的'起-承-转-合'节奏！",
            "> 网文节奏：前300字入戏，持续高爽，章尾钩子",
            "",
            "### 分段情绪要求",
        ]
        
        for segment in emotion_plan.get('breakdown', []):
            lines.extend([
                f"**{segment.get('position')}** - {segment.get('emotion')}（强度{segment.get('intensity')}）",
                f"- 内容：{segment.get('content')}",
            ])
            if segment.get('goal'):
                lines.append(f"- 目标：{segment.get('goal')}")
            lines.append("")
        
        lines.extend([
            "## 字数约束",
            "- 目标：2000-2500字",
            "- 最低：2000字",
            "- 最高：2500字",
            "",
            "## 输出格式",
            "必须按以下格式返回，使用 ---标题--- 和 ---正文--- 分隔：",
            "",
            "---标题---",
            "章节标题（8-14字，概括核心爽点，不要第X章前缀）",
            "---正文---",
            "章节正文内容（2000-2500字，直接写场景）",
            "",
            "## 格式规范",
            '- 角色对话：用引号""包裹',
            "- 系统提示/弹幕：用【】包裹",
            "- 段落：每段不超过3行",
            "",
            "## 🚫 禁止事项",
            "- 爽点回退（爽后突然压抑）",
            "- 预告欺诈（章尾预告不兑现）",
            "- 人设崩塌",
            "- 正文开头写'第X章'",
            "- 金额模糊（神豪文）/ 弹幕缺失（国运文）",
            "- 传统叙事节奏（起承转合）",
        ])
        return "\n".join(lines)
    
    def _build_layer6_self_check(self) -> str:
        """
        构建Layer 6: 自检清单
        """
        gt = self.genre_techniques
        
        lines = [
            "# 【Layer 6】自检清单（生成后必须检查）",
            "",
            "## 写前确认",
            "- [ ] 是否理解本章战术企图？",
            "- [ ] 情绪目标是否明确？",
            "",
            "## 格式检查",
            "- [ ] title和content字段都存在？",
            "- [ ] 字数在2000-2500之间？",
            "- [ ] 无'第X章'字样在正文开头？",
            "",
            "## 内容检查",
            "- [ ] 前300字有冲突/悬念？",
            "- [ ] 章尾有强钩子？",
            "- [ ] 对话占比≥50%？",
        ]
        
        # 添加题材特定检查点
        if gt.quality_checkpoints:
            lines.extend([
                "",
                f"## {gt.genre}专项检查",
            ])
            for checkpoint in gt.quality_checkpoints:
                severity = checkpoint.get('severity', 'warning')
                mark = {"critical": "🔴", "warning": "🟡"}.get(severity, "⚪")
                lines.append(f"- [ ] {mark} {checkpoint.get('point')}（{checkpoint.get('condition')}）")
        
        lines.extend([
            "",
            "## ⚠️ 重要",
            "**如果以上任何一项未通过，请重新生成！**",
        ])
        
        return "\n".join(lines)


# ==================== 快捷函数 ====================

def assemble_prompt(
    genre: str,
    novel_title: str = "未命名",
    chapter_num: int = 0,
    protagonist_name: str = "主角",
    chapter_type: str = "打脸章",
    **kwargs
) -> str:
    """
    快捷函数：组装提示词
    
    Args:
        genre: 题材名称
        novel_title: 小说标题
        chapter_num: 章节号
        protagonist_name: 主角名
        chapter_type: 章节类型（打脸章/收获章/危机章/揭秘章/过渡章）
        **kwargs: 其他参数
    
    Returns:
        完整的System Prompt
    """
    assembler = PromptAssembler(genre)
    return assembler.assemble(
        novel_title=novel_title,
        chapter_num=chapter_num,
        protagonist_name=protagonist_name,
        chapter_type=chapter_type,
        **kwargs
    )


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("测试提示词组装器 - 带网文情绪曲线")
    print("=" * 80)
    
    # 测试国运文 + 打脸章
    print("\n\n【测试1：国运文 + 打脸章】")
    print("-" * 80)
    assembler_gy = PromptAssembler("国运文")
    prompt_gy = assembler_gy.assemble(
        novel_title="开局扮演杀神白起",
        chapter_num=7,
        protagonist_name="苏辰",
        chapter_type="打脸章"
    )
    print(prompt_gy[:2500])
    print("...\n（已截断，完整长度:", len(prompt_gy), "字符）")
    
    # 测试神豪文 + 收获章
    print("\n\n【测试2：神豪文 + 收获章】")
    print("-" * 80)
    assembler_sh = PromptAssembler("神豪文")
    prompt_sh = assembler_sh.assemble(
        novel_title="开局消费百亿，我成了首富",
        chapter_num=7,
        protagonist_name="陈默",
        chapter_type="收获章"
    )
    print(prompt_sh[:2500])
    print("...\n（已截断，完整长度:", len(prompt_sh), "字符）")
    
    # 对比差异
    print("\n\n【差异对比】")
    print("-" * 80)
    print(f"国运文包含'弹幕': {'弹幕' in prompt_gy}")
    print(f"神豪文包含'弹幕': {'弹幕' in prompt_sh}")
    print(f"国运文包含'龙国观众': {'龙国观众' in prompt_gy}")
    print(f"神豪文包含'龙国观众': {'龙国观众' in prompt_sh}")
    print(f"国运文包含'返利': {'返利' in prompt_gy}")
    print(f"神豪文包含'返利': {'返利' in prompt_sh}")
    print(f"国运文包含'精确到分': {'精确到分' in prompt_gy}")
    print(f"神豪文包含'精确到分': {'精确到分' in prompt_sh}")
    
    # 检查情绪曲线
    print("\n\n【情绪曲线检查】")
    print("-" * 80)
    print(f"国运文(打脸章)包含'虐(4)→急(7)→爽(9)→悬(7)': {'虐(4)→急(7)→爽(9)→悬(7)' in prompt_gy}")
    print(f"神豪文(收获章)包含'悬(7)→惊(8)→爽(10)→悬(7)': {'悬(7)→惊(8)→爽(10)→悬(7)' in prompt_sh}")
    print(f"是否包含'起-承-转-合': {'起-承-转-合' in prompt_gy or '起-承-转-合' in prompt_sh}")
