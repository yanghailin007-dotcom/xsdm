# -*- coding: utf-8 -*-
"""
V2 六层架构 - 提示词组装引擎

按照六层架构动态组装System Prompt
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .models import (
    CoreSetting, TacticalPlanning, GenreTechniques, WritingStyle, 
    AIConstraints, SelfCheck, EmotionPlan, AssemblyContext,
    ChapterType
)
from .layer_loaders import (
    CoreSettingLoader, TacticalPlanningLoader, GenreTechniquesLoader,
    WritingStyleLoader, AIConstraintsLoader, SelfCheckLoader, get_loader
)
from .renderers import (
    CoreSettingRenderer, TacticalPlanningRenderer, GenreTechniquesRenderer,
    WritingStyleRenderer, AIConstraintsRenderer, SelfCheckRenderer, get_renderer
)

logger = logging.getLogger(__name__)


class PromptAssemblerV2:
    """
    V2 提示词组装器
    
    按照六层架构组装完整的System Prompt：
    Layer 1: 核心设定
    Layer 2: 战术规划
    Layer 3: 题材技法
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
        
        # 初始化各层Loader
        self.core_setting_loader = CoreSettingLoader()
        self.tactical_planning_loader = TacticalPlanningLoader()
        self.genre_techniques_loader = GenreTechniquesLoader()
        self.writing_style_loader = WritingStyleLoader()
        self.ai_constraints_loader = AIConstraintsLoader()
        self.self_check_loader = SelfCheckLoader()
        
        # 初始化各层Renderer
        self.core_setting_renderer = CoreSettingRenderer()
        self.tactical_planning_renderer = TacticalPlanningRenderer()
        self.genre_techniques_renderer = GenreTechniquesRenderer()
        self.writing_style_renderer = WritingStyleRenderer()
        self.ai_constraints_renderer = AIConstraintsRenderer()
        self.self_check_renderer = SelfCheckRenderer()
        
        # 预加载题材技法（Layer 3 需要genre参数）
        self.genre_techniques = self.genre_techniques_loader.load(genre)
        logger.info(f"[PromptAssemblerV2] 已加载题材技法: {genre}")
    
    def assemble(self, context: AssemblyContext) -> str:
        """
        组装完整System Prompt
        
        Args:
            context: 组装上下文
        
        Returns:
            完整的System Prompt字符串
        """
        sections = []
        
        # Layer 1: 核心设定
        if context.core_setting:
            layer1 = self._assemble_layer1(context.core_setting)
            sections.append(layer1)
            logger.debug("[PromptAssemblerV2] Layer 1 组装完成")
        
        # Layer 2: 战术规划
        if context.tactical_planning:
            layer2 = self._assemble_layer2(context.tactical_planning)
            sections.append(layer2)
            logger.debug("[PromptAssemblerV2] Layer 2 组装完成")
        
        # Layer 3: 题材技法
        layer3 = self._assemble_layer3()
        sections.append(layer3)
        logger.debug("[PromptAssemblerV2] Layer 3 组装完成")
        
        # Layer 4: 文风技法
        layer4 = self._assemble_layer4()
        sections.append(layer4)
        logger.debug("[PromptAssemblerV2] Layer 4 组装完成")
        
        # Layer 5: AI约束 + 情绪曲线
        layer5 = self._assemble_layer5(context)
        sections.append(layer5)
        logger.debug("[PromptAssemblerV2] Layer 5 组装完成")
        
        # Layer 6: 自检清单
        layer6 = self._assemble_layer6()
        sections.append(layer6)
        logger.debug("[PromptAssemblerV2] Layer 6 组装完成")
        
        result = "\n\n".join(filter(None, sections))
        logger.info(f"[PromptAssemblerV2] 组装完成，总长度: {len(result)} 字符")
        return result
    
    def _assemble_layer1(self, core_setting: CoreSetting) -> str:
        """组装Layer 1: 核心设定"""
        return self.core_setting_renderer.render(core_setting)
    
    def _assemble_layer2(self, tactical_planning: TacticalPlanning) -> str:
        """组装Layer 2: 战术规划"""
        return self.tactical_planning_renderer.render(tactical_planning)
    
    def _assemble_layer3(self) -> str:
        """组装Layer 3: 题材技法"""
        return self.genre_techniques_renderer.render(self.genre_techniques)
    
    def _assemble_layer4(self) -> str:
        """组装Layer 4: 文风技法"""
        writing_style = self.writing_style_loader.load()
        return self.writing_style_renderer.render(writing_style)
    
    def _assemble_layer5(self, context: AssemblyContext) -> str:
        """组装Layer 5: AI约束"""
        ai_constraints = self.ai_constraints_loader.load()
        
        # 如果没有提供情绪规划，根据章节类型生成
        if context.emotion_plan is None:
            context.emotion_plan = self._generate_emotion_plan(context.chapter_type)
        
        # 构建Layer 5上下文
        layer5_context = {
            'novel_title': context.novel_title,
            'chapter_num': context.chapter_num,
            'protagonist_name': context.protagonist_name,
            'emotion_plan': context.emotion_plan
        }
        
        return self.ai_constraints_renderer.render(ai_constraints, layer5_context)
    
    def _assemble_layer6(self) -> str:
        """组装Layer 6: 自检清单"""
        self_check = self.self_check_loader.load()
        return self.self_check_renderer.render(self_check, self.genre)
    
    def _generate_emotion_plan(self, chapter_type: str) -> EmotionPlan:
        """
        根据章节类型生成情绪规划
        
        Args:
            chapter_type: 章节类型
        
        Returns:
            情绪规划
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
                "breakdown": [
                    {"position": "0-1000字", "emotion": "悬", "intensity": 6, "content": "承接上文，新线索"},
                    {"position": "1000-1800字", "emotion": "平", "intensity": 5, "content": "信息补充，世界观展开"},
                    {"position": "1800-2000字", "emotion": "悬", "intensity": 7, "content": "强钩子，引出下章"},
                ]
            }
        }
        
        template = templates.get(chapter_type, templates["打脸章"])
        return EmotionPlan(
            chapter_type=template["chapter_type"],
            curve=template["curve"],
            breakdown=template["breakdown"]
        )
    
    def assemble_layer(self, layer_num: int, context: AssemblyContext) -> str:
        """
        组装指定层
        
        Args:
            layer_num: 层号 (1-6)
            context: 组装上下文
        
        Returns:
            该层的Markdown字符串
        """
        if layer_num == 1 and context.core_setting:
            return self._assemble_layer1(context.core_setting)
        elif layer_num == 2 and context.tactical_planning:
            return self._assemble_layer2(context.tactical_planning)
        elif layer_num == 3:
            return self._assemble_layer3()
        elif layer_num == 4:
            return self._assemble_layer4()
        elif layer_num == 5:
            return self._assemble_layer5(context)
        elif layer_num == 6:
            return self._assemble_layer6()
        else:
            raise ValueError(f"无效的层号: {layer_num}")


# ==================== 快捷函数 ====================

def assemble_prompt_v2(
    genre: str,
    novel_title: str = "未命名",
    chapter_num: int = 0,
    protagonist_name: str = "主角",
    chapter_type: str = "打脸章",
    core_setting: Optional[CoreSetting] = None,
    tactical_planning: Optional[TacticalPlanning] = None,
    emotion_plan: Optional[EmotionPlan] = None
) -> str:
    """
    快捷函数：组装提示词（V2）
    
    Args:
        genre: 题材名称
        novel_title: 小说标题
        chapter_num: 章节号
        protagonist_name: 主角名
        chapter_type: 章节类型
        core_setting: 核心设定（可选）
        tactical_planning: 战术规划（可选）
        emotion_plan: 情绪规划（可选）
    
    Returns:
        完整的System Prompt
    """
    assembler = PromptAssemblerV2(genre)
    
    context = AssemblyContext(
        novel_title=novel_title,
        chapter_num=chapter_num,
        protagonist_name=protagonist_name,
        chapter_type=chapter_type,
        core_setting=core_setting,
        tactical_planning=tactical_planning,
        emotion_plan=emotion_plan
    )
    
    return assembler.assemble(context)


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("测试 V2 提示词组装器")
    print("=" * 80)
    
    # 测试国运文+打脸章
    print("\n\n【测试：国运文 + 打脸章】")
    print("-" * 80)
    
    assembler = PromptAssemblerV2("国运文")
    
    context = AssemblyContext(
        novel_title="开局扮演杀神白起",
        chapter_num=7,
        protagonist_name="苏辰",
        chapter_type="打脸章"
    )
    
    prompt = assembler.assemble(context)
    
    # 输出前2000字符
    print(prompt[:2000])
    print("...")
    print(f"\n总长度: {len(prompt)} 字符")
    
    # 验证关键内容
    print("\n验证:")
    print(f"- 包含 Layer 1 标题: {'【Layer 1】核心设定' in prompt}")
    print(f"- 包含 Layer 3 标题: {'【Layer 3】题材技法' in prompt}")
    print(f"- 包含情绪曲线: {'虐(4)→急(7)→爽(9)→悬(7)' in prompt}")
    print(f"- 包含自检清单: {'【Layer 6】自检清单' in prompt}")
