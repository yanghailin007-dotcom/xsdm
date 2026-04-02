"""
章节生成提示词优化器 v2.0
平衡精简与完整性
"""

import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ChapterPromptOptimizer:
    """
    章节生成提示词优化器 v2.0
    
    核心理念：
    - System Prompt: 1500-2000字，包含跨章节不变的核心设定
    - 每章Prompt: 动态注入变化信息
    - 目标：既不过于臃肿，也不丢失关键信息
    """
    
    def __init__(self, novel_data: Dict):
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            import logging
            logging.warning(f"[PromptOptimizer] novel_data 是列表类型，转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            import logging
            logging.warning(f"[PromptOptimizer] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.plan = novel_data.get('plan', {})
        self.emotion_curve = novel_data.get('emotion_curve', {})
        self.char_design = novel_data.get('character_design', {})
        self.worldview = novel_data.get('core_worldview', {})
        
    # ==================== System Prompt 构建 ====================
    
    def build_system_prompt(self) -> str:
        """
        构建平衡的系统提示词（目标1500-2000字）
        包含：世界观、主角、盟友、反派、金手指、开局场景、节奏公式
        """
        sections = [
            ("世界观", self._build_worldview_section()),
            ("主角人设", self._build_protagonist_section()),
            ("核心盟友", self._build_allies_section()),
            ("反派阵营", self._build_antagonists_section()),
            ("金手指系统", self._build_golden_finger_section()),
            ("开局场景", self._build_opening_scene_section()),
            ("节奏公式", self._build_rhythm_section()),
        ]
        
        content_parts = []
        for title, section_content in sections:
            if section_content:
                content_parts.append("## 【" + title + "】\n" + section_content)
        
        content = "\n\n".join(content_parts)
        
        title = self.novel_data.get('title', '未命名')
        
        return """# 角色设定：顶级网络小说作家

你正在为小说《""" + title + """》生成章节内容。
以下是小说的核心设定，必须在所有章节中严格遵循。

""" + content + """

---

## 【番茄爆款风格指南】（核心灵魂）

### 🎯 番茄平台核心特点
1. **强情绪流**：每章必须有情绪高低起伏，让读者情绪波动
2. **高互动感**：善用弹幕、观众反应、网友热议，增强代入感
3. **快节奏叙事**：不做大段铺垫，爽点密集，3-5章一个小高潮
4. **强人设标签**：主角性格鲜明，有记忆点（霸道/冷静/杀伐果断/护短）

### 🔥 爆款写作技法
5. **开篇抓人**：每章前300字必须有冲突或悬念，不能平淡
6. **对话推进**：用对话代替旁白，每句对话都要推动剧情或塑造人物
7. **短句冲击**：多用短句、断句，制造紧张感和节奏感
8. **五感描写**：视觉+听觉为主，配合环境氛围（不要长篇描写）
9. **弹幕互动**（如适用）：
   - 插入网友/观众的实时反应和评论
   - 用【弹幕】或（网友：...）形式体现
   - 观众反应要夸张、真实、多样

### ⚡ 爽点设计公式
10. **装逼打脸**：先抑后扬，让反派嚣张，再让主角强势碾压
11. **震惊流**：主角做出超出预期的行为，引起周围人震惊
12. **收获展示**：主角获得宝物/能力后，要展示效果，让读者有获得感
13. **身份揭露**：主角隐藏身份逐步揭露，每次揭露都要引起轰动
14. **守护/复仇**：为守护重要之人或复仇而爆发，情绪拉满

### 🎭 情绪节奏控制
15. **情绪递进**：一章内情绪要有层次（平静→紧张→爆发→释放）
16. **章尾钩子类型**：
    - 悬念型：揭示一个秘密但未完全揭晓
    - 震惊型：主角做出惊人之举，众人反应待续
    - 收获型：主角获得重要物品/能力
    - 期待型：铺垫即将到来的大战/重要事件

### ❌ 番茄文大忌
- 大段环境描写或心理独白
- 圣母心（该杀不杀，该打脸犹豫）
- 逻辑硬伤（战力崩坏，规则混乱）
- 水文凑字（每句话必须有信息量）
- 对话生硬（台词要符合人物身份和性格）

---

## 【格式铁律】

### 排版规范（必须遵守）
1. **第三人称上帝视角**：客观描述，禁止第一人称
2. **短段落**：每段1-3行，多用换行，适合手机阅读
3. **对话占比≥40%**：对话推动剧情，对话要自然有张力
4. **字数2000-2500字/章**：严格控制
5. **正文格式**：直接写正文，不要加"第X章"标题

### 内容红线
6. **人设一致**：主角性格、能力值、台词风格必须前后一致
7. **承上启下**：必须承接前文剧情，不能跳过大事件
8. **禁止套路重复**：同样的打脸套路不能连续使用

---

## 【返回格式 - 必须严格遵守】

你必须返回**JSON格式**，不要返回纯文本或其他格式：

```json
{
  "title": "章节标题（8-14字，概括核心爽点，绝对不要包含'第X章'字样）",
  "content": "正文内容（2000-2500字，直接写场景和剧情，绝对禁止在开头写'第X章：XXX'这样的标题）"
}
```

⚠️ **重要警告**：
- `content`字段必须**直接以正文开头**，不能包含任何章节标题
- `title`字段只放标题文字，**不要**加"第X章"前缀
- 系统会自动将title和content组合展示，你不需要在content中重复标题

❌ 错误的content示例：
```
第5章：九幽冥蛇，死亡绿洲的阴影！

暗紫色的雾气在脚下翻滚...
```

✅ 正确的content示例：
```
暗紫色的雾气在脚下翻滚，苏辰与白清雪落地时...
```

---

现在开始生成章节。每章我会提供详细的"章节指令"，包含场景、情绪、角色状态等。
每章都必须严格遵循以上【番茄爆款风格指南】，写出让人欲罢不能的网文！
"""
    
    def _build_worldview_section(self) -> str:
        """构建世界观章节"""
        worldview = self.worldview
        if not worldview:
            return """国运禁地直播流：
- 全球100个国家各选1名选手进入禁地
- 选手表现直接关系国家资源奖励/惩罚
- 全球实时直播，弹幕互动
- 禁地内击杀生物可具现资源到现实

力量体系：F-SSS级禁地生物，对应不同实力层次"""
        
        parts = []
        
        # 世界观概述
        overview = worldview.get('world_overview', '')
        if overview:
            if len(overview) > 300:
                overview = overview[:300] + "..."
            parts.append(overview)
        
        # 核心规则
        rules = worldview.get('world_rules', [])
        if rules and isinstance(rules, list):
            parts.append("核心规则：")
            for rule in rules[:3]:
                if isinstance(rule, dict):
                    rule_text = rule.get('rule', '') or rule.get('description', '') or str(rule)
                    parts.append("- " + str(rule_text))
                elif isinstance(rule, str):
                    parts.append("- " + rule[:50])
        
        # 力量体系
        power = worldview.get('power_system', {})
        if isinstance(power, dict):
            summary = power.get('summary', '')
            if summary:
                parts.append("\n力量体系：" + summary[:150])
        
        return "\n".join(parts) if parts else "国运禁地直播流"
    
    def _build_protagonist_section(self) -> str:
        """构建主角人设章节"""
        protagonist = self.char_design.get('protagonist', {}) if self.char_design else {}
        if not protagonist:
            return "主角信息待补充"
        
        parts = []
        
        # 基本信息
        basic = protagonist.get('basic_info', {})
        name = basic.get('name', '主角')
        age = basic.get('age', '')
        former = basic.get('former_identity', '')
        current = basic.get('current_identity', '')
        
        header = "【" + name + "】"
        if age:
            header += "，" + str(age) + "岁"
        parts.append(header)
        
        if former:
            parts.append("- 前身份：" + former[:80])
        if current:
            parts.append("- 现身份：" + current[:80])
        
        # 人设原型
        archetype = protagonist.get('archetype', '')
        if archetype:
            parts.append("\n人设原型：" + archetype[:150])
        
        # 核心特质（详细版）
        traits = protagonist.get('traits', [])
        if traits:
            parts.append("\n核心特质：")
            for trait in traits[:3]:
                if isinstance(trait, str):
                    parts.append("- " + trait[:100])
                elif isinstance(trait, dict):
                    # Handle dict format: {'trait': '描述', 'performance': '表现'}
                    trait_desc = trait.get('trait', '') or trait.get('description', '')
                    if trait_desc:
                        parts.append("- " + str(trait_desc)[:100])
        
        # 标志性细节
        sig = protagonist.get('signature_details', {})
        if isinstance(sig, dict):
            catchphrases = sig.get('catchphrase', [])
            if catchphrases:
                quotes = ' | '.join(['"' + str(c) + '"' for c in catchphrases[:3]])
                parts.append("\n标志性台词：" + quotes)
            
            actions = sig.get('actions', [])
            if actions:
                parts.append("标志性动作：" + actions[0][:80])
        
        # 心理核心
        psych = protagonist.get('psychology', {})
        if isinstance(psych, dict):
            motivation = psych.get('motivation', '')
            if motivation:
                parts.append("\n核心动机：" + motivation[:100])
        
        return "\n".join(parts)
    
    def _build_allies_section(self) -> str:
        """构建核心盟友章节"""
        allies = self.char_design.get('core_allies', []) if self.char_design else []
        if not allies:
            return "暂无核心盟友"
        
        parts = []
        parts.append("主角团队（按重要性排序）：")
        
        for i, ally in enumerate(allies[:4], 1):
            if not isinstance(ally, dict):
                continue
            
            name = ally.get('name', '盟友' + str(i))
            role = ally.get('role', '')
            function = ally.get('function', '')
            
            desc = str(i) + ". 【" + name + "】"
            if role:
                desc += "（" + role + "）"
            if function:
                desc += "\n   作用：" + function[:100]
            
            # 典型台词
            lines = ally.get('typical_lines', [])
            if lines and isinstance(lines, list):
                desc += "\n   台词风格：\"" + lines[0][:40] + "...\""
            
            parts.append(desc)
        
        return "\n\n".join(parts)
    
    def _build_antagonists_section(self) -> str:
        """构建反派阵营章节"""
        antagonists = self.char_design.get('main_antagonists', {}) if self.char_design else {}
        if not antagonists:
            return "反派信息待补充"
        
        parts = []
        parts.append("（按出场阶段排序）")
        
        # 前期反派
        early = antagonists.get('early_stage', [])
        if early and isinstance(early, list):
            parts.append("\n【前期反派】（第1-30章）")
            for enemy in early[:3]:
                if isinstance(enemy, dict):
                    name = enemy.get('name', '未知')
                    hate = enemy.get('hate_point', '')
                    fate = enemy.get('fate', '')
                    line = "- " + name + "："
                    if hate:
                        line += hate[:80]
                    line += " -> "
                    if fate:
                        line += fate[:60]
                    else:
                        line += "被主角击杀"
                    parts.append(line)
        
        # 中期反派
        mid = antagonists.get('mid_stage', [])
        if mid and isinstance(mid, list):
            parts.append("\n【中期反派】（第30-100章）")
            for enemy in mid[:2]:
                if isinstance(enemy, dict):
                    name = enemy.get('name', '未知')
                    identity = enemy.get('identity', '')
                    line = "- " + name + "："
                    if identity:
                        line += identity[:80]
                    else:
                        line += "强力敌人"
                    parts.append(line)
        
        # 后期反派
        late = antagonists.get('late_stage', [])
        if late and isinstance(late, list):
            parts.append("\n【后期反派】（第100章+）")
            for enemy in late[:2]:
                if isinstance(enemy, dict):
                    name = enemy.get('name', '未知')
                    identity = enemy.get('identity', '')
                    line = "- " + name + "："
                    if identity:
                        line += identity[:80]
                    else:
                        line += "终极BOSS"
                    parts.append(line)
        
        return "\n".join(parts)
    
    def _build_golden_finger_section(self) -> str:
        """构建金手指章节"""
        plan = self.plan
        if not plan:
            return "系统流：扮演诸天角色获得能力"
        
        gf = plan.get('golden_finger', {})
        if not gf:
            return "系统流：扮演诸天角色获得能力"
        
        parts = []
        
        # 类型
        gf_type = gf.get('type', '诸天扮演系统')
        parts.append("类型：" + gf_type)
        
        # 初始奖励
        initial = gf.get('initial_reward', '')
        if initial:
            parts.append("初始：" + initial)
        
        # 成长曲线
        growth = gf.get('growth_curve', '')
        if growth:
            parts.append("成长：" + growth)
        
        # 升级方式
        upgrade = gf.get('upgrade', '')
        if upgrade:
            parts.append("升级：" + upgrade[:150])
        
        # 限制条件
        limitation = gf.get('limitation', '')
        if limitation:
            parts.append("限制：" + limitation[:150])
        
        return "\n".join(parts)
    
    def _build_opening_scene_section(self) -> str:
        """构建开局场景章节（前3章场景参考）"""
        plan = self.plan
        if not plan:
            return "开局场景根据剧情自然展开"
        
        opening = plan.get('opening_design', {})
        if not opening:
            return "开局场景根据剧情自然展开"
        
        parts = []
        parts.append("（前3章场景设定，后续章节继承此风格）")
        
        for ch_num in [1, 2, 3]:
            ch_key = 'chapter_' + str(ch_num)
            if ch_key in opening:
                ch_design = opening[ch_key]
                scene = ch_design.get('scene', '')
                action = ch_design.get('action', '')
                
                if scene or action:
                    parts.append("\n第" + str(ch_num) + "章：")
                    if scene:
                        parts.append("场景：" + scene[:150])
                    if action:
                        parts.append("行动：" + action[:150])
        
        return "\n".join(parts)
    
    def _build_rhythm_section(self) -> str:
        """构建节奏公式章节"""
        emotion_curve = self.emotion_curve
        
        parts = []
        
        # 节奏模式
        rhythm = emotion_curve.get('rhythm_pattern', {}) if emotion_curve else {}
        if rhythm:
            micro = rhythm.get('micro_cycle', '3章一循环')
            small = rhythm.get('small_climax', '3章一爽点')
            medium = rhythm.get('medium_climax', '10章一中爽')
            large = rhythm.get('large_climax', '30章一大爽')
            
            parts.append("微循环：" + micro)
            parts.append("爽点节奏：" + small + " | " + medium + " | " + large)
        else:
            parts.append("3章一爽点 | 10章一中爽 | 30章一大爽 | 100章阶段高潮")
        
        # 钩子轮换
        hooks = emotion_curve.get('hook_rotation', {}) if emotion_curve else {}
        if hooks:
            types = hooks.get('chapter_ending_types', {})
            if types:
                parts.append("\n钩子类型：")
                for hook_type, desc in list(types.items())[:3]:
                    parts.append("- " + hook_type + "：" + desc[:60])
        
        return "\n".join(parts)
    
    # ==================== 单章提示词构建（保持详细）====================
    
    def build_chapter_prompt(self, chapter_num: int, blueprint: Dict, 
                            prev_summary: str = "") -> str:
        """构建详细的单章生成提示词"""
        # 获取该章在大纲中的位置
        chapter_outline = self._get_chapter_outline(chapter_num)
        
        # 获取该章的情绪设计
        emotion_design = self._get_emotion_design(chapter_num)
        
        # 获取角色当前状态
        character_states = self._get_character_states(chapter_num)
        
        # 获取场景设定
        scene_setup = self._get_scene_setup(chapter_num)
        
        # 构建提示词
        lines = [
            "# 第" + str(chapter_num) + "章生成指令",
            "",
            "## 【在大纲中的位置】",
            chapter_outline,
            "",
            "## 【情绪设计】（必须严格遵循）",
            emotion_design,
            "",
            "## 【角色当前状态】",
            character_states,
            "",
            "## 【场景设定】",
            scene_setup,
        ]
        
        if prev_summary:
            lines.extend([
                "",
                "## 【前文摘要】（必须承接）",
                prev_summary,
            ])
        
        lines.extend([
            "",
            "## 【本章要求】",
            self._build_chapter_requirements(chapter_num, emotion_design),
            "",
            "## 【输出格式 - 必须严格遵守】",
            "",
            "你必须返回JSON格式，如下：",
            "",
            '{',
            '  "title": "章节标题（8-14字，概括核心爽点，不要加第X章前缀）",',
            '  "content": "正文内容（2000-2500字，直接写场景，绝对禁止在开头写第X章标题）"',
            '}',
            "",
            "⚠️ 格式警告：",
            "- content字段必须直接以正文开头，不能以第X章：XXX开头",
            "- title字段只放标题文字，不要加第X章前缀",
            "- 系统会自动组合展示，你不需要在content中重复标题",
            "",
            "内容要求：",
            "- 不要写第X章标题",
            "- 字数：2000-2500字",
            "- 分段：短段落，每段≤3行",
            "- 对话：占比≥40%，推动剧情",
            "- 钩子：章尾必须有钩子",
        ])
        
        return "\n".join(lines)
    
    def _get_chapter_outline(self, chapter_num: int) -> str:
        """获取该章在大纲中的位置"""
        plan = self.plan
        if not plan:
            return "第" + str(chapter_num) + "章"
        
        # 获取前30章大纲
        outline = plan.get('outline_first_30', [])
        
        # 查找该章
        for item in outline:
            if isinstance(item, dict):
                ch = item.get('chapter', item.get('ch', 0))
                if ch == chapter_num:
                    title = item.get('title', '')
                    event = item.get('event', item.get('key_event', ''))
                    emotion = item.get('emotion', '')
                    result = "第" + str(chapter_num) + "章"
                    if title:
                        result += " | 标题：" + title
                    if event:
                        result += " | 关键事件：" + event
                    if emotion:
                        result += " | 情绪：" + emotion
                    return result
        
        # 根据章节号判断阶段
        if chapter_num <= 3:
            return "第" + str(chapter_num) + "章 | 【开局阶段】建立主角形象，展示金手指"
        elif chapter_num <= 10:
            return "第" + str(chapter_num) + "章 | 【第一次小高潮区间】小爽点密集"
        elif chapter_num <= 15:
            return "第" + str(chapter_num) + "章 | 【第一次中高潮区间】碾压国家代表队"
        elif chapter_num <= 30:
            return "第" + str(chapter_num) + "章 | 【第一阶段高潮】通关首层禁地，全球震惊"
        else:
            return "第" + str(chapter_num) + "章 | 【持续发展阶段】"
    
    def _get_emotion_design(self, chapter_num: int) -> str:
        """获取该章的详细情绪设计"""
        emotion_curve = self.emotion_curve
        
        # 查找各阶段的详细曲线
        phases = ['phase_1_early_domination', 'phase_2_rising_power', 
                  'phase_3_global_dominance', 'phase_4_cosmic_conquest']
        
        for phase_key in phases:
            phase = emotion_curve.get(phase_key, {}) if emotion_curve else {}
            if not phase:
                continue
            
            curve = phase.get('curve', [])
            milestones = phase.get('key_milestones', [])
            
            # 在详细曲线中查找
            for beat in curve:
                if beat.get('ch') == chapter_num:
                    result = "情绪类型：" + beat.get('emotion', '期待') + "（强度" + str(beat.get('intensity', 6)) + "/10）\n"
                    result += "节拍类型：" + beat.get('beat_type', '推进') + "\n"
                    result += "核心事件：" + beat.get('event', '剧情推进') + "\n"
                    result += "章节目的：" + beat.get('purpose', '推进剧情') + "\n"
                    result += "钩子设计：" + beat.get('hook', '根据类型选择')
                    return result
            
            # 在里程碑中查找
            for milestone in milestones:
                if isinstance(milestone, dict):
                    ch = milestone.get('ch') or milestone.get('chapter')
                    if ch == chapter_num:
                        result = "【关键里程碑章节】\n"
                        result += "事件：" + milestone.get('event', '') + "\n"
                        result += "情绪：" + milestone.get('emotion', '大爽') + "\n"
                        result += "强度：" + str(milestone.get('intensity', 10)) + "/10\n"
                        result += "这是重要节点，必须大场面！"
                        return result
        
        # 没找到详细设计，返回默认
        return "情绪类型：根据章节位置调整 | 强度：6-8/10 | 必须有小爽点或钩子"
    
    def _get_character_states(self, chapter_num: int) -> str:
        """获取角色当前状态"""
        char_design = self.char_design
        protagonist = char_design.get('protagonist', {}) if char_design else {}
        
        name = "主角"
        if protagonist:
            basic = protagonist.get('basic_info', {})
            name = basic.get('name', '主角')
        
        # 根据章节号推断主角能力进度
        if chapter_num <= 3:
            ability = "初始阶段，刚获得系统，扮演度1-5%"
            mindset = "困惑->觉醒->初次尝试"
        elif chapter_num <= 10:
            ability = "快速成长，扮演度10-30%，碾压F-E级敌人"
            mindset = "自信建立，开始展现强势"
        elif chapter_num <= 20:
            ability = "中期阶段，扮演度30-50%，碾压D-C级"
            mindset = "无敌气质初显，龙国代表意识觉醒"
        elif chapter_num <= 30:
            ability = "阶段性巅峰，扮演度50%+，完全体降临"
            mindset = "全球级强者心态，为龙国而战"
        elif chapter_num <= 100:
            ability = "持续成长，解锁多个角色形态"
            mindset = "民族英雄，守护龙国"
        else:
            ability = "诸天级存在"
            mindset = "俯视众生，唯我独尊"
        
        return "主角[" + name + "]当前状态：\n- 能力进度：" + ability + "\n- 心理状态：" + mindset + "\n- 当前目标：根据章节剧情推进"
    
    def _get_scene_setup(self, chapter_num: int) -> str:
        """获取场景设定"""
        # 获取开局设计中的场景
        plan = self.plan
        if plan and chapter_num <= 3:
            opening = plan.get('opening_design', {})
            ch_key = 'chapter_' + str(chapter_num)
            if ch_key in opening:
                ch_design = opening[ch_key]
                scene = ch_design.get('scene', '')
                if scene:
                    return "【开局场景】" + scene[:250]
        
        # 默认场景描述
        return "【第" + str(chapter_num) + "章场景】根据剧情推进自然转换，注意：\n1. 场景描写简洁，不要大段环境描写\n2. 重点在人物行动、对话、心理\n3. 通过细节体现世界设定"
    
    def _build_chapter_requirements(self, chapter_num: int, emotion_design: str) -> str:
        """构建本章要求"""
        requirements = [
            "1. 字数：2000-2500字（严格限制）",
            "2. 分段：短段落，每段不超过3行，多用换行",
            "3. 对话：占比>=40%，对话推动剧情，少用旁白",
            "4. 情绪：严格按照【情绪设计】执行，整章保持指定情绪",
            "5. 爽点：本章必须包含至少一个爽点（装逼/收获/打脸/震惊）",
            "6. 钩子：章尾必须有钩子，让读者想看下一章",
        ]
        
        # 根据章节号添加特殊要求
        if chapter_num == 1:
            requirements.append("7. 【首章特殊】必须包含：主角困境->系统觉醒->首次金手指使用->全球直播震惊")
        elif chapter_num == 2:
            requirements.append("7. 【第2章特殊】展示系统功能，建立敌对关系，为第3章打脸铺垫")
        elif chapter_num == 3:
            requirements.append("7. 【第3章特殊】第一次正式装逼打脸，建立无敌形象，章尾大钩子")
        elif chapter_num % 3 == 0 and chapter_num <= 30:
            requirements.append("7. 【小高潮章-" + str(chapter_num) + "】爽点爆发，碾压敌人，弹幕震惊")
        elif chapter_num % 10 == 0:
            requirements.append("7. 【中高潮章-" + str(chapter_num) + "】大场面，大收获，全球震动，龙国高层反应")
        elif chapter_num == 30:
            requirements.append("7. 【阶段高潮章】通关首层禁地，完全体降临，全球各国紧急会议，主角封将")
        
        return "\n".join(requirements)


# ==================== 便捷函数 ====================

def create_optimized_chapter_prompt(novel_data: Dict, chapter_num: int, 
                                    blueprint: Dict = None, 
                                    prev_summary: str = "") -> tuple:
    """
    创建优化的章节生成提示词
    
    Returns:
        (system_prompt, chapter_prompt) 元组
    """
    optimizer = ChapterPromptOptimizer(novel_data)
    
    system_prompt = optimizer.build_system_prompt()
    chapter_prompt = optimizer.build_chapter_prompt(chapter_num, blueprint or {}, prev_summary)
    
    return system_prompt, chapter_prompt
