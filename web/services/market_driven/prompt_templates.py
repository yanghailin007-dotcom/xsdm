# -*- coding: utf-8 -*-
"""
Prompt模板生成器
基于爆款反向工程分析结果，生成高质量的创作Prompt
"""

import json
from typing import Dict, List
from datetime import datetime


class PromptTemplateGenerator:
    """
    Prompt模板生成器
    
    基于BestsellerAnalyzer的分析结果，生成每个步骤的高质量Prompt
    """
    
    def __init__(self, bestseller_analysis: Dict):
        """
        初始化，传入爆款分析结果
        
        Args:
            bestseller_analysis: BestsellerAnalyzer.analyze_genre() 的返回结果
        """
        self.analysis = bestseller_analysis
        self.genre = bestseller_analysis.get("genre", "未知题材")
    
    def generate_step1_plan_prompt(self, title: str, protagonist_name: str, 
                                   selected_plot: Dict, tropes: Dict) -> str:
        """
        生成步骤1（完整方案）的Prompt
        
        基于爆款公式，要求AI生成符合市场规律的内容
        """
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
    
    def generate_step2_worldview_prompt(self, existing_worldview: Dict = None, total_chapters: int = 100) -> str:
        """生成步骤2（世界观）的Prompt"""
        early_end = max(10, total_chapters // 3)
        mid_end = max(early_end + 10, total_chapters * 2 // 3)
        return f"""# 角色：世界观架构师（基于爆款公式）

基于步骤1确定的题材、主角、金手指，生成完整的世界观。

## 🌍 该题材的世界观公式
{json.dumps(self.analysis.get("character_formula", {}).get("antagonists", {}), ensure_ascii=False)}

## 🎯 势力系统设计公式
必须包含3个对立势力：
1. **早期敌对势力**（1-{early_end}章）：{self.analysis.get("character_formula", {}).get("antagonists", {}).get("early", "势利眼小人物")}
2. **中期敌对势力**（{early_end + 1}-{mid_end}章）：{self.analysis.get("character_formula", {}).get("antagonists", {}).get("mid", "富二代、地方势力")}
3. **后期敌对势力**（{mid_end + 1}章+）：{self.analysis.get("character_formula", {}).get("antagonists", {}).get("late", "国际势力、隐藏大佬")}

## 🏛️ 社会规则设计（必须有利于装逼打脸）
- 阶层划分：如何体现等级差异？
- 资源分布：稀有资源如何获取？
- 认可机制：如何获得社会地位？

## 🗺️ 地图升级规划
- 第一地图（1-{early_end}章）：本地场景
- 第二地图（{early_end + 1}-{mid_end}章）：省城/区域
- 第三地图（{mid_end + 1}章+）：全国/全球

## ✅ 输出格式
JSON格式，包含：world_overview, power_system, social_structure, factions, world_rules, key_locations
"""
    
    def generate_step3_characters_prompt(self, protagonist_name: str) -> str:
        """生成步骤3（角色设计）的Prompt"""
        char_formula = self.analysis.get("character_formula", {})
        
        # 安全获取配角列表
        supporting_roles = char_formula.get("supporting", [])
        supporting_text = "\n".join([f"- {s}" for s in supporting_roles]) if supporting_roles else "- 捧哏型队友\n- 女主/感情线\n- 传声筒型军官\n- 对比转变型小弟"
        
        # 安全获取主角人设
        protagonist_template = char_formula.get("protagonist", {})
        protagonist_json = json.dumps(protagonist_template, ensure_ascii=False) if protagonist_template else '{"archetype": "隐忍型爱国青年", "traits": ["杀伐果断", "极度护短", "低调装逼"]}'
        
        return f"""# 角色：角色设计师（基于爆款人设公式）

基于已确定的世界观和主角人设，设计完整角色阵容。

## ⚠️ 强制要求（违反将导致生成失败）
1. **主角姓名必须使用用户指定的**：{protagonist_name}
2. **禁止**给主角起其他名字或别名
3. **禁止**在 protagonist.name 中使用其他值
4. 如果违反以上任何一条，生成将被视为失败

## 👤 主角人设公式（仅作为人设参考，姓名必须用上面指定的）
{protagonist_json}

## 👥 配角功能定位公式
{supporting_text}

## 😈 反派设计公式
每个反派必须：
1. **让读者恨**：通过什么行为让读者恨得牙痒痒？
2. **有层次感**：不是单纯坏，而是有动机
3. **打脸爽快**：被打脸时的反应要有层次（不屑→震惊→后悔→恐惧）

## ✅ 输出格式
返回JSON格式，必须包含以下字段：
{{
  "protagonist": {{"name": "{protagonist_name}", "age": 25, "traits": [...], ...}},
  "core_allies": [{{"name": "...", "role": "..."}}],
  "main_antagonists": {{"early_stage": [...], "mid_stage": [...], "late_stage": [...]}},
  "supporting_roles": [...]
}}

** 重要：protagonist.name 必须是 "{protagonist_name}"，禁止用其他名字！**
** 不要返回null，必须返回有效的JSON对象！**
"""
    
    def generate_step4_growth_prompt(self, total_chapters: int = 100) -> str:
        """生成步骤4（成长路线）的Prompt"""
        m1 = max(5, total_chapters // 10)
        m2 = max(15, total_chapters // 3)
        m3 = max(25, total_chapters // 2)
        m4 = max(50, total_chapters * 3 // 4)
        return f"""# 角色：成长路线规划师（基于爆款升级公式）

基于前30章大纲，规划主角成长里程碑。

## 📈 成长公式
{self.analysis.get("golden_finger_formula", {}).get("growth_curve", "")}

## 🎯 成长维度
1. **能力成长**：数值提升、新技能解锁
2. **身份成长**：社会地位、财富等级
3. **关系成长**：从被看不起到被巴结

## 📊 里程碑设计
- 第{m1}章：第一次身份跃迁
- 第{m2}章：阶段性身份曝光
- 第{m3}章：进入更高圈子
- 第{m4}章：成为一方霸主

## ✅ 输出格式
JSON格式：protagonist_growth, ability_system_progression, key_relationships_development
"""
    
    def generate_step5_emotion_prompt(self, total_chapters: int) -> str:
        """生成步骤5（情绪曲线）的Prompt"""
        emotion = self.analysis.get("emotion_formula", {})
        
        # 🔥 安全构建钩子列表，避免f-string嵌套问题
        hook_types = emotion.get("hook_types", ["悬念型", "爽点型", "期待型", "震惊型"])
        hook_list_str = "\n".join([f"{i+1}. {hook_type}" for i, hook_type in enumerate(hook_types)])
        
        return f"""# 角色：情绪曲线设计师（基于爆款节奏公式）

设计{total_chapters}章的情绪曲线，严格遵循爆款情绪公式。

## 🎭 情绪循环公式
{emotion.get("cycle", "压抑2章→爆发1章→巩固1章→期待1章")}

## 🪝 章尾钩子轮替
{hook_list_str}

## 📈 强度控制
- 小爽点（每3章）：强度7
- 中爽点（每10章）：强度8-9
- 大爽点（每30章）：强度10
- 缓冲章（爽点后1-2章）：强度5-6

## 🎨 情绪类型库
震惊、期待、小爽快、大爽快、紧张、愤怒、满足

## ✅ 输出格式
**严格要求**：
1. 必须返回**完整的{total_chapters}章**，每章都要有数据！
2. 不能只返回里程碑章节（如1, 10, 20...），必须每章都有
3. curve数组长度必须等于总章数
4. 每个元素包含：ch(章节号), emotion(情绪类型), intensity(1-10), beat_type(节奏类型), event(事件), purpose(目的)

**错误示例（会被拒绝）**：
```json
{{"curve": [{{"ch":1,...}}, {{"ch":10,...}}, {{"ch":20,...}}]}}  // 只返回了3章
```

**正确示例**：
```json
{{"curve": [{{"ch":1,...}}, {{"ch":2,...}}, {{"ch":3,...}}, ...]}}  // 完整的{total_chapters}章
```
"""
    
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
