# -*- coding: utf-8 -*-
"""
Prompt模板生成器
基于爆款反向工程分析结果，生成高质量的创作Prompt

v2.0 - 支持从JSON配置加载
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class PromptTemplateGenerator:
    """
    Prompt模板生成器
    
    基于BestsellerAnalyzer的分析结果，生成每个步骤的高质量Prompt
    支持从JSON配置文件加载模板
    """
    
    def __init__(self, bestseller_analysis: Dict, use_json_config: bool = True):
        """
        初始化，传入爆款分析结果
        
        Args:
            bestseller_analysis: BestsellerAnalyzer.analyze_genre() 的返回结果
            use_json_config: 是否使用JSON配置（向后兼容）
        """
        self.analysis = bestseller_analysis
        self.genre = bestseller_analysis.get("genre", "未知题材")
        self.use_json_config = use_json_config
        self._step_templates = None
        
        if use_json_config:
            self._load_step_templates()
    
    def _load_step_templates(self):
        """从JSON加载步骤模板配置"""
        try:
            template_file = Path(__file__).parent.parent.parent.parent / \
                "prompt_packages" / "default" / "market_driven" / "steps" / "step_templates.json"
            
            if template_file.exists():
                with open(template_file, 'r', encoding='utf-8') as f:
                    self._step_templates = json.load(f)
                logger.info("[PromptTemplateGenerator] 成功加载步骤模板配置")
            else:
                logger.warning(f"[PromptTemplateGenerator] 模板文件不存在: {template_file}")
                self._step_templates = None
        except Exception as e:
            logger.error(f"[PromptTemplateGenerator] 加载模板配置失败: {e}")
            self._step_templates = None
    
    def _render_template(self, template_key: str, variables: Dict) -> Optional[str]:
        """
        从JSON配置渲染模板
        
        Args:
            template_key: 模板键名，如 "step_1_plan"
            variables: 模板变量字典
            
        Returns:
            渲染后的模板字符串，失败返回None
        """
        if not self._step_templates:
            return None
        
        template_config = self._step_templates.get(template_key)
        if not template_config:
            return None
        
        template = template_config.get("template", "")
        if not template:
            return None
        
        # 简单的变量替换
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value) if value is not None else "")
        
        return result
    
    def generate_step1_plan_prompt(self, title: str, protagonist_name: str, 
                                   selected_plot: Dict, tropes: Dict) -> str:
        """
        生成步骤1（完整方案）的Prompt
        
        基于爆款公式，要求AI生成符合市场规律的内容
        """
        # 🔥 优先使用JSON配置
        if self.use_json_config and self._step_templates:
            try:
                prompt = self._generate_step1_from_config(title, protagonist_name, selected_plot)
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[PromptTemplateGenerator] 步骤1 JSON配置渲染失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：步骤1提示词模板配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/steps/step_templates.json

或使用API创建配置：
POST /api/v2/prompt-config/step_1_plan

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _old_generate_step1_hardcoded(self, title: str, protagonist_name: str, selected_plot: Dict) -> str:
        """旧的硬编码fallback（保留用于参考）"""
        formula = self.analysis.get("genre_formula", "")
        opening = self.analysis.get("opening_3_chapters", {})
        ch1 = opening.get("chapter_1", {})
        ch2 = opening.get("chapter_2", {})
        ch3 = opening.get("chapter_3", {})
        gf_formula = self.analysis.get("golden_finger_formula", {})
        
        plot_detail = selected_plot.get("detail", "") if selected_plot else ""
        
        # 🔥 安全构建禁忌列表，避免f-string嵌套问题
        taboos = self.analysis.get("taboos", [])
        taboo_list_str = "\n".join(["- " + taboo for taboo in taboos])
        
        return f"""# 角色：顶级网文策划专家（基于市场爆款公式创作）

你正在为一部"{self.genre}"题材的网络小说创作方案。

## 🎯 该题材的爆款公式
{formula}

## 📖 基于Top10爆款的开局公式

### 第1章公式（必须严格遵循）
- **开篇场景**：{ch1.get("scene", "深夜/极端天气/主角困境场景")}
- **主角困境**：{ch1.get("protagonist_situation", "具体数字+多重打击")}
- **系统触发**：{ch1.get("system_trigger", "绝望之际触发")}
- **章尾钩子**：{ch1.get("hook", "悬念型钩子")}
- **情绪曲线**：{ch1.get("emotion_curve", "压抑→绝望→希望")}
- **字数**：{ch1.get("word_count", "2500-2800")}字

### 第2章公式
- **场景**：{ch2.get("scene", "第一次使用系统")}
- **第一次收获**：{ch2.get("reward", "具体数值奖励")}
- **周围人反应**：{ch2.get("reactions", "路人→反派→震惊")}
- **章尾钩子**：{ch2.get("hook", "引出新的冲突")}
- **字数**：{ch2.get("word_count", "2500-2800")}字

### 第3章公式
- **打脸场景**：{ch3.get("scene", "4S店/高档餐厅/同学会")}
- **反派类型**：{ch3.get("antagonist", "势利眼销售/前女友/宝马男")}
- **反转设计**：{ch3.get("plot", "被嘲讽→展现实力→反派后悔")}
- **章尾钩子**：{ch3.get("hook", "更大人物出现/新冲突")}
- **字数**：{ch3.get("word_count", "2800-3000")}字

## 💰 金手指数值公式
- **初始奖励**：{gf_formula.get("initial_reward", "等效价值100万")}
- **成长曲线**：{gf_formula.get("growth_curve", "前期快中期慢后期极慢")}
- **限制条件**：{gf_formula.get("limitations", "次数限制+冷却时间")}

## 🎯 用户最终选择（必须严格遵循）
- **书名**：{title}
- **主角名**：{protagonist_name}
- **剧情路线**：
```
{plot_detail}
```

## 📝 你需要生成

### 1. 标题确认
确认使用用户确定的书名（验证是否符合15字以内、有冲击力）

### 2. 开局3章详细剧本（必须严格遵循上述公式）
每章必须包含：
- **场景设定**：具体到时间、地点、环境
- **人物动作**：主角做了什么？说了什么？
- **对话设计**：短对话推动剧情，每句不超过20字
- **心理描写**：最多1-2句，体现情绪变化
- **系统交互**：金手指如何触发、如何表现
- **章尾钩子**：必须让读者想看下一章

### 3. 金手指细化（基于公式）
- **初始数值**：具体数字
- **升级公式**：每级需要XX点，提升XX%
- **限制设计**：冷却/次数/副作用

### 4. 主角人设
基于爆款人设公式：
{json.dumps(self.analysis.get("character_formula", {}).get("protagonist", {}), ensure_ascii=False)}

### 5. 前30章大纲（遵循节奏公式）
基于：
- 小爽点：每3章一个（{self.analysis.get("climax_formula", {}).get("small_climax", {}).get("types", ["收获", "打脸"])}）
- 中爽点：每10章一个（{self.analysis.get("climax_formula", {}).get("medium_climax", {}).get("types", ["升级", "曝光"])}）
- 大爽点：每30章一个（{self.analysis.get("climax_formula", {}).get("large_climax", {}).get("types", ["总结", "新地图"])}）

## ⚠️ 写作禁忌（绝对不能犯）
{taboo_list_str}

## ✅ 输出格式
返回严格合法的JSON（所有字符串值必须用英文双引号 `"` 包裹，禁止单引号，禁止任何字段值不加引号）：
{{
  "title": "书名",
  "recommended_title": "推荐书名（如果原标题合适则与title相同）",
  "core_conflict": "核心冲突描述（主角面临的主要矛盾和挑战）",
  "worldview": "世界观概述（世界背景、规则、力量体系）",
  "opening_design": {{
    "chapter_1": {{"scene": "", "action": "", "dialogue": [], "hook": ""}},
    "chapter_2": {{"scene": "", "action": "", "dialogue": [], "hook": ""}},
    "chapter_3": {{"scene": "", "action": "", "dialogue": [], "hook": ""}}
  }},
  "golden_finger": {{"initial": "", "upgrade_formula": "", "limitations": ""}},
  "protagonist": {{"name": "", "traits": [], "growth_arc": ""}}
}}

**警告**：
1. 不要返回 `outline_first_30` 字段
2. 所有字符串值必须加英文双引号 `"`
3. 禁止在JSON末尾或数组/对象最后一个元素后加逗号
4. 只返回JSON，不要其他说明。"""
    
    def _generate_step1_from_config(self, title: str, protagonist_name: str, selected_plot: Dict) -> Optional[str]:
        """从JSON配置生成步骤1 Prompt"""
        formula = self.analysis.get("genre_formula", "")
        opening = self.analysis.get("opening_3_chapters", {})
        ch1 = opening.get("chapter_1", {})
        ch2 = opening.get("chapter_2", {})
        ch3 = opening.get("chapter_3", {})
        gf_formula = self.analysis.get("golden_finger_formula", {})
        plot_detail = selected_plot.get("detail", "") if selected_plot else ""
        taboos = self.analysis.get("taboos", [])
        taboo_list_str = "\n".join(["- " + taboo for taboo in taboos])
        
        # 构建变量字典
        variables = {
            "genre": self.genre,
            "formula": formula,
            "ch1_scene": ch1.get("scene", "深夜/极端天气/主角困境场景"),
            "ch1_protagonist_situation": ch1.get("protagonist_situation", "具体数字+多重打击"),
            "ch1_system_trigger": ch1.get("system_trigger", "绝望之际触发"),
            "ch1_hook": ch1.get("hook", "悬念型钩子"),
            "ch1_emotion_curve": ch1.get("emotion_curve", "压抑→绝望→希望"),
            "ch1_word_count": ch1.get("word_count", "2500-2800"),
            "ch2_scene": ch2.get("scene", "第一次使用系统"),
            "ch2_reward": ch2.get("reward", "具体数值奖励"),
            "ch2_reactions": ch2.get("reactions", "路人→反派→震惊"),
            "ch2_hook": ch2.get("hook", "引出新的冲突"),
            "ch2_word_count": ch2.get("word_count", "2500-2800"),
            "ch3_scene": ch3.get("scene", "4S店/高档餐厅/同学会"),
            "ch3_antagonist": ch3.get("antagonist", "势利眼销售/前女友/宝马男"),
            "ch3_plot": ch3.get("plot", "被嘲讽→展现实力→反派后悔"),
            "ch3_hook": ch3.get("hook", "更大人物出现/新冲突"),
            "ch3_word_count": ch3.get("word_count", "2800-3000"),
            "gf_initial_reward": gf_formula.get("initial_reward", "等效价值100万"),
            "gf_growth_curve": gf_formula.get("growth_curve", "前期快中期慢后期极慢"),
            "gf_limitations": gf_formula.get("limitations", "次数限制+冷却时间"),
            "title": title,
            "protagonist_name": protagonist_name,
            "plot_detail": plot_detail,
            "character_formula": json.dumps(self.analysis.get("character_formula", {}).get("protagonist", {}), ensure_ascii=False),
            "small_climax_types": str(self.analysis.get("climax_formula", {}).get("small_climax", {}).get("types", ["收获", "打脸"])),
            "medium_climax_types": str(self.analysis.get("climax_formula", {}).get("medium_climax", {}).get("types", ["升级", "曝光"])),
            "large_climax_types": str(self.analysis.get("climax_formula", {}).get("large_climax", {}).get("types", ["总结", "新地图"])),
            "taboo_list": taboo_list_str
        }
        
        return self._render_template("step_1_plan", variables)
    
    def generate_step2_worldview_prompt(self, existing_worldview: Dict = None, total_chapters: int = 100) -> str:
        """生成步骤2（世界观）的Prompt"""
        # 🔥 优先使用JSON配置
        if self.use_json_config and self._step_templates:
            try:
                prompt = self._generate_step2_from_config(total_chapters)
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[PromptTemplateGenerator] 步骤2 JSON配置渲染失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：步骤2提示词模板配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/steps/step_templates.json

或使用API创建配置：
POST /api/v2/prompt-config/step_2_worldview
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _generate_step2_from_config(self, total_chapters: int = 100) -> Optional[str]:
        """从JSON配置生成步骤2 Prompt"""
        early_end = max(10, total_chapters // 3)
        mid_end = max(early_end + 10, total_chapters * 2 // 3)
        
        variables = {
            "antagonist_formula": json.dumps(self.analysis.get("character_formula", {}).get("antagonists", {}), ensure_ascii=False),
            "early_end": str(early_end),
            "early_antagonist": self.analysis.get("character_formula", {}).get("antagonists", {}).get("early", "势利眼小人物"),
            "mid_start": str(early_end + 1),
            "mid_end": str(mid_end),
            "mid_antagonist": self.analysis.get("character_formula", {}).get("antagonists", {}).get("mid", "富二代、地方势力"),
            "late_start": str(mid_end + 1),
            "late_antagonist": self.analysis.get("character_formula", {}).get("antagonists", {}).get("late", "国际势力、隐藏大佬")
        }
        
        return self._render_template("step_2_worldview", variables)
    
    def generate_step3_characters_prompt(self, protagonist_name: str) -> str:
        """生成步骤3（角色设计）的Prompt"""
        # 🔥 优先使用JSON配置
        if self.use_json_config and self._step_templates:
            try:
                prompt = self._generate_step3_from_config(protagonist_name)
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[PromptTemplateGenerator] 步骤3 JSON配置渲染失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：步骤3提示词模板配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/steps/step_templates.json

或使用API创建配置：
POST /api/v2/prompt-config/step_3_characters
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _generate_step3_from_config(self, protagonist_name: str) -> Optional[str]:
        """从JSON配置生成步骤3 Prompt"""
        char_formula = self.analysis.get("character_formula", {})
        
        supporting_roles = char_formula.get("supporting", [])
        supporting_text = "\n".join([f"- {s}" for s in supporting_roles]) if supporting_roles else "- 捧哏型队友\n- 女主/感情线\n- 传声筒型军官\n- 对比转变型小弟"
        
        protagonist_template = char_formula.get("protagonist", {})
        protagonist_json = json.dumps(protagonist_template, ensure_ascii=False) if protagonist_template else '{"archetype": "隐忍型爱国青年", "traits": ["杀伐果断", "极度护短", "低调装逼"]}'
        
        variables = {
            "protagonist_name": protagonist_name,
            "protagonist_template": protagonist_json,
            "supporting_roles": supporting_text
        }
        
        return self._render_template("step_3_characters", variables)
    
    def generate_step4_growth_prompt(self, total_chapters: int = 100) -> str:
        """生成步骤4（成长路线）的Prompt"""
        # 🔥 优先使用JSON配置
        if self.use_json_config and self._step_templates:
            try:
                prompt = self._generate_step4_from_config(total_chapters)
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[PromptTemplateGenerator] 步骤4 JSON配置渲染失败: {e}")
        
        error_msg = """
❌ 错误：步骤4提示词模板配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/steps/step_templates.json

或使用API创建配置：
POST /api/v2/prompt-config/step_4_growth
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _generate_step4_from_config(self, total_chapters: int = 100) -> Optional[str]:
        """从JSON配置生成步骤4 Prompt"""
        m1 = max(5, total_chapters // 10)
        m2 = max(15, total_chapters // 3)
        m3 = max(25, total_chapters // 2)
        m4 = max(50, total_chapters * 3 // 4)
        
        variables = {
            "growth_curve": self.analysis.get("golden_finger_formula", {}).get("growth_curve", ""),
            "m1": str(m1),
            "m2": str(m2),
            "m3": str(m3),
            "m4": str(m4)
        }
        
        return self._render_template("step_4_growth", variables)
    
    def generate_step5_emotion_prompt(self, total_chapters: int) -> str:
        """生成步骤5（情绪曲线）的Prompt"""
        # 🔥 优先使用JSON配置
        if self.use_json_config and self._step_templates:
            try:
                prompt = self._generate_step5_from_config(total_chapters)
                if prompt:
                    return prompt
            except Exception as e:
                logger.warning(f"[PromptTemplateGenerator] 步骤5 JSON配置渲染失败: {e}")
        
        error_msg = """
❌ 错误：步骤5提示词模板配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/steps/step_templates.json

或使用API创建配置：
POST /api/v2/prompt-config/step_5_emotion
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def _generate_step5_from_config(self, total_chapters: int) -> Optional[str]:
        """从JSON配置生成步骤5 Prompt"""
        emotion = self.analysis.get("emotion_formula", {})
        climax = self.analysis.get("climax_formula", {})
        
        hook_types = emotion.get("hook_types", ["悬念型", "爽点型", "期待型", "震惊型"])
        hook_list_str = "\n".join([f"{i+1}. {hook_type}" for i, hook_type in enumerate(hook_types)])
        
        small_types = climax.get("small_climax", {}).get("types", ["打脸", "收获", "装逼", "震惊", "情感满足"])
        medium_types = climax.get("medium_climax", {}).get("types", ["升级", "身份曝光", "资源获取", "势力扩张"])
        large_types = climax.get("large_climax", {}).get("types", ["阶段性胜利", "全网曝光", "新地图开启", "终极反转"])
        
        variables = {
            "total_chapters": str(total_chapters),
            "emotion_cycle": emotion.get("cycle", "压抑2章→爆发1章→巩固1章→期待1章"),
            "hook_types": hook_list_str,
            "small_types": ", ".join(small_types),
            "medium_types": ", ".join(medium_types),
            "large_types": ", ".join(large_types)
        }
        
        return self._render_template("step_5_emotion", variables)
    
    def get_writing_style_guide(self) -> str:
        """获取写作风格指南"""
        techniques = self.analysis.get("writing_techniques", [])
        # 🔥 安全构建技巧列表，避免f-string嵌套问题
        tech_list_str = "\n".join([f"{i+1}. {tech}" for i, tech in enumerate(techniques)])
        
        taboos = self.analysis.get("taboos", [])
        taboo_list_str = "\n".join([f"- {taboo}" for taboo in taboos])
        
        return f"""# 📝 写作风格指南（基于Top10爆款）

## 写作技巧
{tech_list_str}

## 节奏控制
- 短段落：每段不超过2行
- 多对话：对话占比60%以上
- 快节奏：减少描写，增加行动
- 强对比：突出主角前后变化

## 禁忌
{taboo_list_str}
"""


# 便捷函数
def create_prompt_templates(bestseller_analysis: Dict) -> PromptTemplateGenerator:
    """基于爆款分析创建Prompt模板生成器"""
    return PromptTemplateGenerator(bestseller_analysis)


if __name__ == "__main__":
    # 测试
    from bestseller_analyzer import analyze_bestseller_formula
    
    analysis = analyze_bestseller_formula("神豪文-花钱返利类")
    generator = create_prompt_templates(analysis)
    
    print("=" * 50)
    print("步骤1 Prompt示例：")
    print("=" * 50)
    prompt = generator.generate_step1_plan_prompt(
        title="开局物价贬值百万倍",
        protagonist_name="李明",
        selected_plot={"detail": "稳健发育流路线详情..."},
        tropes={}
    )
    print(prompt[:1500] + "...")
