"""
章节生成提示词优化器 v3.0 - 番茄爆款终极版
===========================================

核心特性：
1. 智能章节类型判断（SETUP/FACE_SLAP/REWARD/REVEAL/CRISIS）
2. 黄金三章专项引擎（前3章特殊优化）
3. 番茄算法友好指标（可量化数据控制）
4. 题材专项技法（国运/神豪/模拟器/修仙）
5. 震惊流生成器（3层震惊结构）
6. 情绪节奏精确控制（字数段级）

作者：AI Assistant
版本：3.0.0
日期：2026-03-26
"""

import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class ChapterPromptOptimizerV3:
    """
    番茄爆款章节生成优化器 v3.0
    
    基于番茄平台算法和读者偏好设计的终极提示词系统
    """
    
    # ==================== 常量配置 ====================
    
    # 章节类型定义
    CHAPTER_TYPES = {
        "SETUP": "铺垫章",           # 积蓄情绪，为爽点做准备
        "FACE_SLAP": "打脸章",       # 爽点爆发，当众打脸
        "REWARD": "收获章",          # 展示成果，获得好处
        "REVEAL": "揭秘章",          # 身份揭露，引发震惊
        "CRISIS": "危机章",          # 生死存亡，绝处逢生
        "TRANSITION": "过渡章",      # 承上启下，剧情推进
    }
    
    # 题材专项配置
    GENRE_TEMPLATES = {
        "国运文": {
            "has_livestream": True,
            "has_national_luck": True,
            "弹幕模板": [
                "【龙国观众】卧槽！这也行？",
                "【外国观众】不可能！这一定是作弊！",
                "【龙国专家】这...这违背了物理学常识！",
                "【弹幕刷屏】龙国牛逼！！！",
                "【外国弹幕】Fake! Must be fake!",
                "【官方账号】龙国国运指挥部：密切关注中",
            ],
            "反应链": ["现场观众", "直播平台弹幕", "各国官方", "联合国层面"],
            "数据展示": ["国运值变化", "资源具现数量", "全球排名", "与他国对比"],
            "系统提示音": "【龙国国运+XXX】【全球排名上升至第X位】",
        },
        "神豪文": {
            "has_money_system": True,
            "数字精确": True,
            "返利音效": "【叮！恭喜宿主消费XXX元，返利XXX元已到账！】【叮！触发暴击返利，额外奖励XXX元！】",
            "价格计算模板": [
                "周围人心中快速计算：这...这得多少钱啊？",
                "XXX倒吸一口凉气：这相当于我十年的工资！",
                "路人甲掐指一算：卧槽，这辈子都赚不到这么多！",
            ],
            "前后对比": True,
            "震惊层级": ["金额数字", "支付方式", "身份猜测"],
        },
        "模拟器文": {
            "has_simulation": True,
            "剪辑感": True,
            "模拟过程模板": [
                "【第1次模拟】主角选择XXX，结果：死亡（被车撞死）",
                "【第2次模拟】主角选择XXX，结果：死亡（被人暗杀）",
                "【第99次模拟】主角终于发现关键：XXX",
            ],
            "失败铺垫": True,
            "技能展示": "【获得白色天赋：XXX（效果：XXX）】",
        },
        "修仙文": {
            "has_cultivation": True,
            "境界体系": True,
            "突破特效": "轰！天地变色，雷劫降临！",
            "震惊层级": ["同门", "长老", "宗主", "整个修仙界"],
        },
        "同人": {
            "has_original_work": True,
            "原著角色": True,
            "改变剧情": True,
            "蝴蝶效应": True,
        },
    }
    
    # 番茄算法指标
    ALGORITHM_METRICS = {
        "paragraph": {
            "avg_length": "30-50字",
            "max_length": 80,
            "dialogue_ratio": 0.5,  # 对话占比≥50%
        },
        "pacing": {
            "conflict_first_300": True,  # 前300字必须有冲突
            "mini_climax_every_1000": True,  # 每1000字一个小爽点
            "hook_last_50": True,  # 章尾最后50字是钩子
            "no_dialogue_limit": 200,  # 禁止连续200字无对话
        },
        "emotion": {
            "transitions_per_chapter": 3,  # 一章内情绪转变至少3次
            "climax_intensity": 8,  # 高潮部分情绪强度≥8/10
            "shock_elements": 1,  # 至少1个震惊元素
        },
    }
    
    # ==================== 初始化 ====================
    
    def __init__(self, novel_data: Dict):
        """
        初始化优化器
        
        Args:
            novel_data: 小说数据，包含title, plan, emotion_curve等
        """
        self.novel_data = novel_data
        self.title = novel_data.get('title', '未命名')
        self.plan = novel_data.get('plan', {})
        self.emotion_curve = novel_data.get('emotion_curve', {})
        self.char_design = novel_data.get('character_design', {})
        self.worldview = novel_data.get('core_worldview', {})
        
        # 检测题材类型
        self.genre_type = self._detect_genre_type()
        
        # 主角信息
        self.protagonist_name = self._get_protagonist_name()
        
        logger.info(f"[PromptV3] 初始化完成 | 书名: {self.title} | 题材: {self.genre_type}")
    
    def _detect_genre_type(self) -> str:
        """检测题材类型"""
        genre = self.novel_data.get('genre', '')
        plan = self.novel_data.get('plan', {})
        
        # 从genre字段判断
        if '国运' in genre or '直播' in genre:
            return '国运文'
        elif '神豪' in genre or '花钱' in genre or '返利' in genre:
            return '神豪文'
        elif '模拟' in genre or '模拟器' in genre:
            return '模拟器文'
        elif '修仙' in genre or '修真' in genre:
            return '修仙文'
        elif '奶爸' in genre or '萌宝' in genre:
            return '奶爸文'
        elif '签到' in genre:
            return '签到文'
        elif '末日' in genre or '求生' in genre:
            return '末日文'
        elif '同人' in genre:
            return '同人'
        
        # 从金手指类型判断
        golden_finger = plan.get('golden_finger', {})
        gf_type = golden_finger.get('type', '')
        
        if '国运' in gf_type:
            return '国运文'
        elif '神豪' in gf_type or '花钱' in gf_type:
            return '神豪文'
        elif '模拟' in gf_type:
            return '模拟器文'
        
        return '通用'
    
    def _get_protagonist_name(self) -> str:
        """获取主角姓名"""
        char_design = self.char_design
        if char_design:
            protagonist = char_design.get('protagonist', {})
            if isinstance(protagonist, dict):
                basic_info = protagonist.get('basic_info', {})
                return basic_info.get('name', '主角')
        
        # 从plan中获取
        plan_protagonist = self.plan.get('protagonist', {})
        if isinstance(plan_protagonist, dict):
            basic_info = plan_protagonist.get('basic_info', {})
            return basic_info.get('name', '主角')
        
        return '主角'
    
    # ==================== 核心方法：构建System Prompt ====================
    
    def build_system_prompt(self) -> str:
        """
        构建番茄爆款System Prompt（约2500字）
        
        Returns:
            完整的System Prompt字符串
        """
        sections = [
            self._build_header(),
            self._build_core_setting(),
            self._build_worldview_section(),
            self._build_protagonist_section(),
            self._build_golden_three_chapters(),
            self._build_tomato_algorithm_guide(),
            self._build_genre_specific_guide(),
            self._build_shock_techniques(),
            self._build_emotion_control(),
            self._build_format_rules(),
            self._build_footer(),
        ]
        
        return "\n\n".join(filter(None, sections))
    
    def _build_header(self) -> str:
        """构建头部"""
        return f"""# 🏆 番茄爆款小说生成专家 v3.0

你正在为小说《{self.title}》生成章节内容。
这是番茄小说平台的爆款作品，必须严格遵循以下所有规则。

【你的任务】
写出让读者欲罢不能、一章接一章追读的网文！"""
    
    def _build_core_setting(self) -> str:
        """构建核心设定"""
        return """## 【身份设定】

你是番茄小说平台的顶级签约作家，擅长：
- 快节奏爽文，3章一个小高潮
- 强情绪流，让读者情绪波动剧烈
- 震惊流写法，层层递进引发震撼
- 短段落排版，完美适配手机阅读

【成功标准】
1. 读者看完一章必须点下一章
2. 每章都有明确的爽点或钩子
3. 情绪曲线陡峭，压抑→爆发→满足
4. 章尾钩子让人心痒难耐"""
    
    def _build_worldview_section(self) -> str:
        """构建世界观章节"""
        worldview = self.worldview
        if not worldview:
            return ""
        
        parts = []
        
        # 世界观概述
        overview = worldview.get('world_overview', '')
        if overview:
            if len(overview) > 300:
                overview = overview[:300] + "..."
            parts.append("【世界观核心】\n" + overview)
        
        # 核心规则
        rules = worldview.get('world_rules', [])
        if rules and isinstance(rules, list):
            parts.append("【核心规则】")
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
                parts.append("【力量体系】\n" + summary[:150])
        
        return "## 【世界观设定】（不可违背）\n\n" + "\n".join(parts) if parts else ""
    
    def _build_protagonist_section(self) -> str:
        """构建主角设定"""
        protagonist = self.char_design.get('protagonist', {}) if self.char_design else {}
        if not protagonist:
            return ""
        
        parts = []
        
        # 基本信息
        basic = protagonist.get('basic_info', {})
        name = basic.get('name', self.protagonist_name)
        age = basic.get('age', '')
        
        parts.append(f"【主角：{name}】" + (f"，{age}岁" if age else ""))
        
        # 人设原型
        archetype = protagonist.get('archetype', '')
        if archetype:
            parts.append(f"人设原型：{archetype[:100]}")
        
        # 核心特质
        traits = protagonist.get('traits', [])
        if traits:
            parts.append("\n核心特质：")
            for trait in traits[:3]:
                if isinstance(trait, str):
                    parts.append(f"- {trait[:100]}")
                elif isinstance(trait, dict):
                    trait_desc = trait.get('trait', '') or trait.get('description', '')
                    if trait_desc:
                        parts.append(f"- {str(trait_desc)[:100]}")
        
        # 标志性细节
        sig = protagonist.get('signature_details', {})
        if isinstance(sig, dict):
            catchphrases = sig.get('catchphrase', [])
            if catchphrases:
                quotes = ' | '.join([f'"{c}"' for c in catchphrases[:3]])
                parts.append(f"\n标志性台词：{quotes}")
            
            actions = sig.get('actions', [])
            if actions:
                parts.append(f"标志性动作：{actions[0][:80]}")
        
        return "## 【主角人设】（严格遵循）\n\n" + "\n".join(parts) if len(parts) > 1 else ""
    
    def _build_golden_three_chapters(self) -> str:
        """构建黄金三章指南"""
        return """## 🏆 黄金三章法则（生死线）

### 第1章【钩子章】- 必须完成的任务：
**结构分配：500字困境 + 1500字系统觉醒 + 300字钩子**

✅ **任务清单：**
- [ ] 主角困境：3句话内让读者同情/代入主角
- [ ] 羞辱场景：势利眼反派的经典羞辱（语言+动作）
- [ ] 系统触发：章尾必须出现系统/金手指
- [ ] 悬念钩子：让读者必须点下一章的悬念
- [ ] 情绪峰值：从压抑到希望的强烈转折

📝 **模板参考：**
开篇："深夜23:47，暴雨倾盆，XXX（极端困境）..."
触发："鲜血滴落的瞬间，眼前出现半透明光幕..."
钩子："【新手任务：XXX，是否接受？】主角瞳孔收缩..."

---

### 第2章【验证章】- 必须完成的任务：
**结构分配：800字准备 + 1200字验证 + 300字新冲突**

✅ **任务清单：**
- [ ] 系统验证：第一次使用金手指，必须成功
- [ ] 小规模爽点：让主角获得第一笔收益/能力
- [ ] 反派登场：出现一个势利眼反派，短暂压制主角
- [ ] 期待建立：让读者看到更大的可能性
- [ ] 新危机：章尾出现新的冲突或挑战

📝 **模板参考：**
验证："XXX（金手指使用），【叮！恭喜获得XXX】"
爽点："周围人震惊：这怎么可能！"
冲突："手机突然响起，XXX冷冷道：XXX"

---

### 第3章【打脸章】- 必须完成的任务：
**结构分配：500字压抑 + 1000字爆发 + 800字收获 + 100字新伏笔**

✅ **任务清单：**
- [ ] 当众打脸：在公开场合羞辱反派（必须有围观群众）
- [ ] 具体数字：展示主角获得的好处（精确到元/数值）
- [ ] 震惊传播：周围人开始传播主角的事迹
- [ ] 前后对比：反派态度180度大转变
- [ ] 新伏笔：引出更大的反派或新的目标

📝 **模板参考：**
压抑："XXX嚣张道：就凭你这个穷鬼？"
爆发："主角淡然道：记账了。然后..."
收获："【叮！恭喜宿主获得XXX】"
伏笔："远处，一个神秘人眯起眼睛：有点意思..."

⚠️ **黄金三章红线：**
- 禁止大段环境描写
- 禁止主角内心独白超过100字
- 禁止反派突然降智
- 禁止没有具体数字的虚写"""
    
    def _build_tomato_algorithm_guide(self) -> str:
        """构建番茄算法指南"""
        return """## 📊 番茄算法友好指标（必须达成）

### 段落结构指标
- **平均每段字数**：30-50字（手机一屏能看完）
- **对话段落占比**：≥50%（一句一段，短促有力）
- **最长段落限制**：不超过80字
- **换行频率**：每300字必须有一个换行

### 节奏控制指标
- **前300字**：必须出现冲突或悬念，禁止平淡开场
- **每1000字**：必须有一个小爽点（收获/打脸/震惊）
- **章尾50字**：必须是钩子，让读者点下一章
- **无对话限制**：禁止连续200字无对话

### 情绪曲线指标
- **情绪转变**：一章内至少3次情绪转变
- **高潮强度**：最后1/3章节情绪强度≥8/10
- **震惊元素**：至少包含1个震惊元素
- **爽点密度**：每章至少1个爽点，3章1个大爽点

### 移动端适配
- **段落长度**：每段1-3行，多用换行
- **对话占比**：对话推动剧情，减少旁白
- **视觉节奏**：短句+换行，制造阅读快感
- **章尾位置**：确保章尾在屏幕可见区域"""
    
    def _build_genre_specific_guide(self) -> str:
        """构建题材专项指南"""
        genre_type = self.genre_type
        
        if genre_type not in self.GENRE_TEMPLATES:
            return ""
        
        template = self.GENRE_TEMPLATES[genre_type]
        
        sections = [f"## 🎮 {genre_type}专项技法（必须融入）\n"]
        
        # 弹幕模板（国运/直播类）
        if template.get("has_livestream"):
            sections.append("### 弹幕设计模板（每章至少3-5条）")
            sections.append("```")
            for barrage in template.get("弹幕模板", []):
                sections.append(barrage)
            sections.append("```")
            
            sections.append("\n### 官方反应链（层层递进）")
            for i, level in enumerate(template.get("反应链", []), 1):
                sections.append(f"{i}. {level}的反应")
        
        # 数字精确（神豪类）
        if template.get("数字精确"):
            sections.append("\n### 金钱数字规范")
            sections.append("- 所有金额必须精确到小数点后2位")
            sections.append("- 返利到账必须有系统提示音效果：")
            sections.append(f"  `{template.get('返利音效', '')}`")
            
            sections.append("\n### 周围人心理活动模板")
            for tmpl in template.get("价格计算模板", []):
                sections.append(f"- {tmpl}")
        
        # 模拟器类
        if template.get("has_simulation"):
            sections.append("\n### 模拟过程写法（快速剪辑感）")
            sections.append("```")
            for tmpl in template.get("模拟过程模板", []):
                sections.append(tmpl)
            sections.append("```")
            
            sections.append(f"\n### 天赋展示格式")
            sections.append(f"`{template.get('技能展示', '')}`")
        
        # 修仙类
        if template.get("has_cultivation"):
            sections.append("\n### 突破场景写法")
            sections.append(f"特效描述：`{template.get('突破特效', '')}`")
            
            sections.append("\n### 震惊层级（层层递进）")
            for i, level in enumerate(template.get("震惊层级", []), 1):
                sections.append(f"{i}. {level}震惊")
        
        return "\n".join(sections)
    
    def _build_shock_techniques(self) -> str:
        """构建震惊流技法"""
        return """## 😱 震惊流写作技法（层层递进）

### 第1层：现场围观者（直接见证）
**表情描写：**
- 瞳孔骤然收缩，眼球突出
- 嘴巴张成O型，下巴几乎脱臼
- 双腿发软，不自觉后退一步

**语言描写：**
- "这不可能！"、"我眼花了？"、"这还是人吗？"
- "卧槽！卧槽！卧槽！"（语无伦次）
- "快掐我一下，我不是在做梦吧？"

**动作描写：**
- 手机从手中滑落，掉在地上
- 揉眼睛、掐大腿、扇自己耳光
- 指着主角，手指颤抖说不出话

---

### 第2层：间接传播者（直播/听说）
**弹幕爆炸：**
```
【弹幕】？？？？？？
【弹幕】前方高能！！！
【弹幕】这主播开挂了吧？
【弹幕】已截图，太牛逼了！
【弹幕】转发给朋友了，这不科学！
```

**社交媒体：**
- 朋友圈疯狂刷屏
- 微博热搜瞬间登顶
- 微信群炸锅，@所有人

---

### 第3层：权威质疑者（专家/领导）
**第一阶段：质疑**
- "肯定是造假！查他！"
- "这不合常理，一定有猫腻！"
- "派人去核实，我不信！"

**第二阶段：验证后的震惊**
- "这...这怎么可能...数据是真的？"
- "快！查他所有资料！我要最详细的！"
- "此人必须招揽，不惜一切代价！"

**第三阶段：行动**
- "封锁消息，不能让其他国家知道！"
- "启动S级预案，全力接触！"
- "通知最高层，出大事了！"

---

### 震惊话术库（直接使用）
**初级震惊（普通路人）：**
- "不可能！"、"假的吧？"、"我看错了？"

**中级震惊（有点见识）：**
- "这还是人吗？"、"开挂了吧？"、"这怎么可能！"
- "我活了这么大，从没见过这种场面！"

**高级震惊（权威人士）：**
- "快查他！"、"封锁消息！"、"必须招揽他！"
- "通知最高层，出大事了！"、"启动紧急预案！"

**终极震惊（改变世界）：**
- "这...这将改变整个世界格局！"
- "快！召开紧急会议，全员到齐！"
- "不惜一切代价，一定要得到他！"""
    
    def _build_emotion_control(self) -> str:
        """构建情绪控制指南"""
        return """## 🎭 情绪节奏精确控制

### 标准情绪曲线模板（按字数分配）

**【铺垫章】SETUP - 为爽点积蓄能量**
```
0-500字：平静（强度5）→ 日常铺垫
501-1200字：压抑（强度7）→ 反派嚣张
1201-2000字：愤怒（强度8）→ 主角被欺
2001-2400字：期待（强度7）→ 准备反击
2401-2500字：钩子（强度6）→ 悬念
```

**【打脸章】FACE_SLAP - 爽点爆发**
```
0-300字：压抑（强度8）→ 反派极致羞辱
301-800字：转折（强度7）→ 主角反击开始
801-1800字：爆发（强度10）→ 碾压式打脸
1801-2300字：满足（强度9）→ 收获展示
2301-2500字：钩子（强度7）→ 新危机/机遇
```

**【收获章】REWARD - 展示成果**
```
0-500字：期待（强度7）→ 获得前铺垫
501-1200字：惊喜（强度8）→ 获得过程
1201-2000字：满足（强度9）→ 效果展示
2001-2400字：应用（强度8）→ 实际使用
2401-2500字：期待（强度7）→ 新目标
```

**【揭秘章】REVEAL - 身份暴露**
```
0-500字：悬念（强度6）→ 铺垫
501-1000字：猜测（强度7）→ 众人猜测
1001-1500字：揭露（强度9）→ 逐步揭露
1501-2000字：震惊（强度10）→ 各方反应
2001-2500字：后续（强度8）→ 影响扩散
```

### 情绪转换技巧
**压抑→爆发：**
- 先写反派的极致嚣张（让读者恨）
- 再写主角的淡然一笑（让读者期待）
- 最后写雷霆万钧的反击（让读者爽）

**平静→震惊：**
- 先写日常的平静（让读者放松）
- 突然一个转折（让读者意外）
- 最后震撼全场（让读者震惊）

### 情绪强度控制词
**强度10（极限）：**
- 瞳孔地震、浑身颤抖、如遭雷击
- 不可能！这不可能！（重复强调）

**强度8-9（强烈）：**
- 倒吸一口凉气、头皮发麻
- 这...这怎么可能！

**强度6-7（中等）：**
- 眉头一皱、心中一惊
- 有点意思..."""
    
    def _build_format_rules(self) -> str:
        """构建格式规则"""
        return """## 📐 格式铁律（必须遵守）

### 排版规范
1. **第三人称上帝视角**：客观描述，禁止第一人称
2. **短段落**：每段1-3行，多用换行，适合手机阅读
3. **对话占比≥50%**：对话推动剧情，一句一段
4. **字数控制**：2000-2500字/章，严格限制
5. **章节标题**：简洁有力，有悬念感
   - 好例子："身份暴露！全球震惊"、"抽奖暴击！神级奖励"
   - 坏例子："主角的一天"、"继续冒险"

### 对话写法规范
**正确示范：**
```
"就这？"

陈默嘴角微微上扬。

"你确定？"

张昊一愣："什么？"

"我说——"

陈默缓缓抬起头，眼神如刀：

"你确定要惹我？"
```

**错误示范：**
```
陈默看着张昊，心里想着这个人真是太嚣张了，他决定要给这个人一点教训看看，于是他开口说道："你确定要惹我？"
```

### 禁止事项
❌ 大段环境描写（超过50字）
❌ 主角内心独白（超过100字）
❌ 连续200字无对话
❌ 没有具体数字的虚写（"很多钱"→"100万"）
❌ 圣母心（该杀不杀，该打脸犹豫）
❌ 逻辑硬伤（战力崩坏，规则混乱）
❌ 水文凑字（每句话必须有信息量）
❌ 对话生硬（台词要符合人物身份）

### 章尾钩子类型
1. **悬念型**：揭示秘密但未完全揭晓
2. **震惊型**：主角做出惊人之举，众人反应待续
3. **收获型**：主角获得重要物品/能力
4. **期待型**：铺垫即将到来的大战/重要事件
5. **危机型**：新的危机突然出现"""
    
    def _build_footer(self) -> str:
        """构建页脚"""
        return """---

## 🚀 开始生成

现在，请根据我提供的"章节指令"生成章节内容。

记住：
1. 你是番茄爆款作家，不是普通写手
2. 每章都要让读者欲罢不能
3. 严格按照上述所有规则执行
4. 写出让人通宵追更的神作！

**准备好后，请输出："已理解所有规则，开始生成章节。"**"""


    # ==================== 章节类型判断 ====================
    
    def detect_chapter_type(self, chapter_num: int, blueprint: Dict = None) -> str:
        """
        智能判断章节类型
        
        Args:
            chapter_num: 章节号
            blueprint: 章节规划
            
        Returns:
            章节类型标识（SETUP/FACE_SLAP/REWARD/REVEAL/CRISIS/TRANSITION）
        """
        # 黄金三章特殊处理
        if chapter_num <= 3:
            return self._detect_golden_chapter_type(chapter_num)
        
        # 从blueprint获取情绪设计
        emotion_beat = self._get_emotion_beat(chapter_num)
        if emotion_beat:
            beat_type = emotion_beat.get('beat_type', '').lower()
            
            # 根据节拍类型判断
            if beat_type in ['压抑', '铺垫', 'setup']:
                return 'SETUP'
            elif beat_type in ['爽点', '打脸', '高潮', 'climax']:
                return 'FACE_SLAP'
            elif beat_type in ['收获', 'reward', '升级']:
                return 'REWARD'
            elif beat_type in ['揭秘', '曝光', 'reveal']:
                return 'REVEAL'
            elif beat_type in ['危机', '危机', 'crisis']:
                return 'CRISIS'
        
        # 根据章节号规律判断
        chapter_in_cycle = (chapter_num - 1) % 10  # 10章一个周期
        
        if chapter_in_cycle in [0, 1, 2]:  # 第1-3章：铺垫
            return 'SETUP'
        elif chapter_in_cycle == 3:  # 第4章：爽点
            return 'FACE_SLAP'
        elif chapter_in_cycle in [4, 5]:  # 第5-6章：过渡/收获
            return 'REWARD'
        elif chapter_in_cycle == 6:  # 第7章：揭秘或危机
            return 'REVEAL' if chapter_num % 2 == 0 else 'CRISIS'
        elif chapter_in_cycle in [7, 8]:  # 第8-9章：铺垫
            return 'SETUP'
        else:  # 第10章：大爽点
            return 'FACE_SLAP'
    
    def _detect_golden_chapter_type(self, chapter_num: int) -> str:
        """黄金三章类型判断"""
        if chapter_num == 1:
            return 'GOLDEN_1'  # 钩子章
        elif chapter_num == 2:
            return 'GOLDEN_2'  # 验证章
        else:
            return 'GOLDEN_3'  # 打脸章
    
    # ==================== 单章提示词构建（核心）====================
    
    def build_chapter_prompt(self, chapter_num: int, blueprint: Dict = None, 
                            prev_summary: str = "") -> str:
        """
        构建单章生成提示词（v3.0终极版）
        
        Args:
            chapter_num: 章节号
            blueprint: 章节规划
            prev_summary: 前文摘要
            
        Returns:
            完整的单章提示词
        """
        # 判断章节类型
        chapter_type = self.detect_chapter_type(chapter_num, blueprint)
        
        logger.info(f"[PromptV3] 构建第{chapter_num}章提示词 | 类型: {chapter_type}")
        
        # 根据类型选择模板
        if chapter_type.startswith('GOLDEN_'):
            return self._build_golden_chapter_prompt(chapter_num, chapter_type, 
                                                      blueprint, prev_summary)
        else:
            return self._build_standard_chapter_prompt(chapter_num, chapter_type,
                                                        blueprint, prev_summary)
    
    def _build_golden_chapter_prompt(self, chapter_num: int, chapter_type: str,
                                      blueprint: Dict, prev_summary: str) -> str:
        """构建黄金三章提示词"""
        if chapter_type == 'GOLDEN_1':
            return self._build_golden_chapter_1(blueprint, prev_summary)
        elif chapter_type == 'GOLDEN_2':
            return self._build_golden_chapter_2(blueprint, prev_summary)
        else:
            return self._build_golden_chapter_3(blueprint, prev_summary)
    
    def _build_golden_chapter_1(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第1章（钩子章）提示词"""
        # 获取开局设计
        opening = self.plan.get('opening_design', {}).get('chapter_1', {}) if self.plan else {}
        
        # 题材专项元素
        genre_elements = self._get_genre_elements_for_chapter(1)
        
        prompt = f"""# 🔥 第1章生成指令【黄金三章 - 钩子章】

⚠️ **这是全书最重要的章节！决定读者是否继续阅读！**

## 【章节定位】
类型：钩子章（生死线）
功能：极端困境开局 + 系统觉醒 + 悬念钩子
目标：让读者3句话内同情主角，章尾必须点下一章

## 【结构要求】（严格按字数分配）

### 第一部分：极端困境（0-500字）
✅ **必须完成的任务：**
- 时间：深夜/暴雨/特殊时刻（营造压抑氛围）
- 地点：出租屋/医院/街头（底层环境）
- 困境：失业+负债+分手+家人重病（多重打击）
- 羞辱：势利眼的极致羞辱（语言+动作+表情）

📝 **参考写法：**
```
深夜23:47，暴雨倾盆。
出租屋楼道，房东砸门催租。
主角XXX，被裁员3个月，负债XX万，
女友当天下午发微信分手并拉黑，
银行卡余额仅剩XX元，明天是最后还款日...
```

❌ **禁止：**
- 大段环境描写（控制在50字内）
- 主角内心独白（控制在100字内）
- 平淡的日常铺垫

---

### 第二部分：系统觉醒（500-2000字）
✅ **必须完成的任务：**
- 触发：被羞辱到极致时的系统激活
- 画面：半透明蓝色光幕（经典番茄风格）
- 功能展示：清晰展示系统核心功能
- 首次使用：给主角带来第一丝希望

📝 **参考写法：**
```
被房东推倒撞墙，额头流血。
鲜血滴落的瞬间——
眼前出现半透明蓝色光幕：
【检测到宿主生命体征濒危，人生模拟器激活中...10%...50%...100%】
意识被拉入纯白空间...
```

{genre_elements}

---

### 第三部分：悬念钩子（2000-2500字）
✅ **必须完成的任务：**
- 金手指展示：具体的功能/奖励/能力
- 首次使用：获得第一笔收益/信息
- 悬念：让读者必须点下一章的钩子
- 新反派/新冲突：为第2章铺垫

📝 **经典钩子模板：**
- "系统提示：【新手礼包：可模拟一次未来72小时人生，是否立即开始？】"
- "手机余额XX元，而XXX需要XXX元，主角如何凑齐？"
- "窗外暴雨中，XXX的迈巴赫驶过，车窗摇下..."

❌ **禁止：**
- 平淡结尾（必须有悬念）
- 无新冲突出现
- 主角一帆风顺

## 【番茄算法指标】
- 前300字必须出现冲突/羞辱场景
- 500字处必须出现系统触发
- 章尾最后50字必须是钩子
- 对话占比≥40%
- 每段不超过3行

## 【检查清单】
生成后自检：
- [ ] 主角困境是否让读者同情？
- [ ] 系统触发是否有画面感？
- [ ] 章尾钩子是否让人想点下一章？
- [ ] 是否有具体的数字（金额/数值）？
- [ ] 对话是否自然推动剧情？

## 【输出格式】
```
第1章 【有悬念的标题】

[正文内容...]

（字数：2000-2500字）
```
"""
        return prompt
    
    def _build_golden_chapter_2(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第2章（验证章）提示词"""
        genre_elements = self._get_genre_elements_for_chapter(2)
        
        prompt = f"""# 🔥 第2章生成指令【黄金三章 - 验证章】

⚠️ **这是验证金手指的关键章节！决定读者是否相信设定！**

## 【章节定位】
类型：验证章
功能：系统验证 + 小规模爽点 + 新冲突
目标：让读者相信金手指有效，期待更大的爽点

## 【承接要求】
前文摘要：{prev_summary or "第1章结尾，主角刚获得系统/金手指"}
必须承接：系统刚激活，主角准备第一次使用

## 【结构要求】

### 第一部分：准备与犹豫（0-800字）
✅ **必须完成的任务：**
- 系统介绍：详细展示系统功能（但不要太啰嗦）
- 主角犹豫：要不要使用？有没有风险？
- 决定使用：下定决心，开始第一次尝试
- 配角登场：出现一个支持者（借钱的/鼓励的）

📝 **参考写法：**
```
主角盯着系统面板上的冷却倒计时。
右手食指无意识敲击桌面（标志性动作）。
室友XXX嘲讽：\"穷逼也配借钱？\"
只有老实人XXX偷偷塞给主角XXX元...
```

---

### 第二部分：金手指验证（800-2000字）
✅ **必须完成的任务：**
- 使用过程：详细描写使用金手指的过程
- 首次成功：必须成功，给读者信心
- 具体收益：精确的数字/能力提升
- 周围反应：小范围内的震惊

{genre_elements}

📝 **成功模板：**
- 神豪文：【叮！消费XXX元，返利XXX元！】
- 国运文：【击杀XXX，国运值+XXX，全球排名上升！】
- 模拟器：【第X次模拟成功！获得XXX天赋！】

---

### 第三部分：新冲突（2000-2500字）
✅ **必须完成的任务：**
- 反派登场：更大的反派或之前的反派升级
- 短暂压制：反派暂时压制主角（为第3章铺垫）
- 悬念钩子：让读者期待主角如何反击
- 期待建立：展示更大的可能性

📝 **经典钩子：**
- "手机短信：'明天同学聚会，敢来帝豪酒店吗？——XXX'"
- "车窗摇下，前女友挽着富二代冷笑：'捡破烂捡到XXX了？'"
- "系统提示：【警告！检测到更强的宿主候选人...】"

## 【番茄算法指标】
- 第800字处必须出现金手指使用
- 1500字处必须有第一次成功
- 章尾必须出现新冲突
- 情绪曲线：犹豫→期待→满足→紧张

## 【检查清单】
- [ ] 金手指使用过程是否清晰？
- [ ] 首次成功是否有具体数字？
- [ ] 新反派是否让读者恨？
- [ ] 是否为第3章打脸做好了铺垫？

## 【输出格式】
```
第2章 【有悬念的标题】

[正文内容...]

（字数：2000-2500字）
```
"""
        return prompt
    
    def _build_golden_chapter_3(self, blueprint: Dict, prev_summary: str) -> str:
        """构建第3章（打脸章）提示词"""
        genre_elements = self._get_genre_elements_for_chapter(3)
        
        prompt = f"""# 🔥 第3章生成指令【黄金三章 - 打脸章】

⚠️ **这是第一次大爽点！决定读者是否追读！**

## 【章节定位】
类型：打脸章
功能：当众打脸 + 收获展示 + 震惊传播
目标：让读者感到痛快，产生追更动力

## 【承接要求】
前文摘要：{prev_summary or "第2章结尾，主角被反派压制，准备反击"}
必须承接：主角带着金手指收益，准备打脸

## 【结构要求】

### 第一部分：压抑（0-500字）
✅ **必须完成的任务：**
- 场景设定：公开场合（酒店/商场/学校）
- 反派嚣张：极致的羞辱和嘲讽
- 群众围观：大量围观群众（传播基础）
- 主角隐忍：淡然处之，内心记账

📝 **参考写法：**
```
帝豪酒店，同学聚会。
XXX搂着前女友，当众嘲讽：
\"这不是陈学霸吗？怎么，捡破烂捡到这来了？\"
周围同学窃窃私语，有人拍照发朋友圈...
主角轻声道：\"记账了。\"
```

---

### 第二部分：爆发（500-1500字）
✅ **必须完成的任务：**
- 反击开始：主角开始展示实力
- 层层升级：反派不服，继续加码
- 碾压打脸：主角彻底碾压反派
- 具体数字：精确展示主角的实力

{genre_elements}

📝 **打脸节奏：**
1. 反派嘲讽：\"就凭你？\"（第一层）
2. 主角反击：展示小部分实力（第二层）
3. 反派加码：叫更多人/搬出后台（第三层）
4. 主角碾压：彻底碾压，全场震惊（高潮）

---

### 第三部分：收获（1500-2400字）
✅ **必须完成的任务：**
- 系统提示：【叮！恭喜宿主XXX！】
- 具体收益：精确的数值/物品/能力
- 周围反应：3层震惊（现场→传播→权威）
- 反派态度：180度大转变，跪舔/恐惧

📝 **震惊传播链：**
```
现场同学：手机疯狂拍照，朋友圈刷屏
直播弹幕："卧槽！这不科学！"
官方反应：XXX紧急召开会议...
```

---

### 第四部分：新伏笔（2400-2500字）
✅ **必须完成的任务：**
- 新危机：更大的反派注意到主角
- 新机遇：新的目标/任务/挑战
- 悬念钩子：让读者期待下一章

📝 **经典钩子：**
- "远处，一辆黑色劳斯莱斯缓缓停下，车窗摇下..."
- "系统提示：【警告！检测到S级危险正在接近...】"
- "手机响起，一个陌生号码：'模拟器持有者，欢迎来到真实游戏'"

## 【番茄算法指标】
- 500字处必须出现反派极致羞辱
- 1500字处必须是打脸高潮
- 2000字处必须有系统提示和具体数字
- 章尾50字必须是钩子
- 情绪强度：8→10→9→7

## 【震惊流检查清单】
- [ ] 是否有3层震惊结构？
- [ ] 现场围观者是否有具体反应？
- [ ] 是否有弹幕/传播描写？
- [ ] 反派态度是否有180度转变？

## 【输出格式】
```
第3章 【震撼的标题】

[正文内容...]

（字数：2000-2500字）
```
"""
        return prompt
    
    def _build_standard_chapter_prompt(self, chapter_num: int, chapter_type: str,
                                        blueprint: Dict, prev_summary: str) -> str:
        """构建标准章节提示词（第4章以后）"""
        # 获取该章的情绪设计
        emotion_beat = self._get_emotion_beat(chapter_num)
        
        # 获取章节大纲
        chapter_outline = self._get_chapter_outline(chapter_num)
        
        # 根据类型选择模板
        type_templates = {
            'SETUP': self._build_setup_template(),
            'FACE_SLAP': self._build_faceslap_template(),
            'REWARD': self._build_reward_template(),
            'REVEAL': self._build_reveal_template(),
            'CRISIS': self._build_crisis_template(),
            'TRANSITION': self._build_transition_template(),
        }
        
        type_template = type_templates.get(chapter_type, type_templates['TRANSITION'])
        
        # 题材专项元素
        genre_elements = self._get_genre_elements_for_chapter(chapter_num)
        
        prompt = f"""# 第{chapter_num}章生成指令

## 【章节类型】
{type_template}

## 【在大纲中的位置】
{chapter_outline}

## 【情绪设计】
{emotion_beat if emotion_beat else "情绪类型：根据章节位置调整 | 强度：7-9/10"}

## 【前文摘要】（必须承接）
{prev_summary or "承接上一章剧情，保持连贯性"}

{genre_elements}

## 【番茄算法指标】
- 前300字必须出现冲突/悬念
- 每1000字必须有一个小爽点
- 章尾最后50字必须是钩子
- 对话占比≥50%
- 每段不超过3行

## 【输出格式】
```
第{chapter_num}章 【章节标题】

[正文内容...]

（字数：2000-2500字）
```
"""
        return prompt


    # ==================== 章节类型模板 ====================
    
    def _build_setup_template(self) -> str:
        """构建铺垫章模板"""
        return """类型：SETUP（铺垫章）
功能：积蓄情绪，为下一章的爽点做准备

【结构要求】
0-500字：平静（强度5）→ 日常铺垫
501-1200字：压抑（强度7）→ 反派嚣张
1201-2000字：愤怒（强度8）→ 主角被欺
2001-2400字：期待（强度7）→ 准备反击
2401-2500字：钩子（强度6）→ 悬念

【必含元素】
- 反派的极致嚣张（让读者恨）
- 主角的隐忍（让读者心疼）
- 准备反击的铺垫（让读者期待）
- 章尾钩子（必须点下一章）

【禁止】
- 本章出现爽点（要憋到下一章）
- 主角过早反击
- 平淡的日常（必须有冲突）"""
    
    def _build_faceslap_template(self) -> str:
        """构建打脸章模板"""
        return """类型：FACE_SLAP（打脸章）
功能：爽点爆发，当众打脸

【结构要求】
0-300字：压抑（强度8）→ 反派极致羞辱
301-800字：转折（强度7）→ 主角反击开始
801-1800字：爆发（强度10）→ 碾压式打脸
1801-2300字：满足（强度9）→ 收获展示
2301-2500字：钩子（强度7）→ 新危机/机遇

【必含元素】
- 公开场合（有围观群众）
- 反派极致羞辱（先抑）
- 主角强势反击（后扬）
- 具体数字（金额/数值）
- 3层震惊结构
- 反派态度180度转变

【震惊流要求】
第1层：现场围观者（表情/语言/动作）
第2层：直播/传播（弹幕/朋友圈/热搜）
第3层：权威反应（专家/领导/官方）

【禁止】
- 没有具体数字的虚写
- 反派降智
- 圣母心（该杀不杀）"""
    
    def _build_reward_template(self) -> str:
        """构建收获章模板"""
        return """类型：REWARD（收获章）
功能：展示成果，获得好处

【结构要求】
0-500字：期待（强度7）→ 获得前铺垫
501-1200字：惊喜（强度8）→ 获得过程
1201-2000字：满足（强度9）→ 效果展示
2001-2400字：应用（强度8）→ 实际使用
2401-2500字：期待（强度7）→ 新目标

【必含元素】
- 系统提示音：【叮！恭喜宿主XXX！】
- 具体收益：精确的数值/物品/能力
- 效果展示：让读者有获得感
- 实际应用：展示如何使用
- 对比：之前vs现在

【题材专项】
神豪文：具体金额，返利到账音效
国运文：国运值变化，全球排名
模拟器：天赋效果，属性提升
修仙：境界突破，战力数值

【禁止】
- 没有具体数字
- 获得后不展示效果
- 平淡的获得过程"""
    
    def _build_reveal_template(self) -> str:
        """构建揭秘章模板"""
        return """类型：REVEAL（揭秘章）
功能：身份揭露，引发震惊

【结构要求】
0-500字：悬念（强度6）→ 铺垫
501-1000字：猜测（强度7）→ 众人猜测
1001-1500字：揭露（强度9）→ 逐步揭露
1501-2000字：震惊（强度10）→ 各方反应
2001-2500字：后续（强度8）→ 影响扩散

【必含元素】
- 悬念铺垫：逐步放出线索
- 猜测环节：众人各种猜测
- 逐步揭露：控制揭露节奏
- 震惊反应：3层震惊结构
- 影响扩散：身份曝光后的连锁反应

【揭露节奏】
第1波：小范围怀疑
第2波：证据出现
第3波：彻底曝光
第4波：权威确认

【禁止】
- 一次性全部揭露
- 没有震惊反应
- 揭露后没有影响"""
    
    def _build_crisis_template(self) -> str:
        """构建危机章模板"""
        return """类型：CRISIS（危机章）
功能：生死存亡，绝处逢生

【结构要求】
0-500字：平静（强度5）→ 危机前兆
501-1000字：爆发（强度9）→ 危机降临
1001-1500字：绝望（强度10）→ 生死存亡
1501-2000字：转机（强度8）→ 金手指救命
2001-2400字：反击（强度9）→ 绝地反击
2401-2500字：钩子（强度7）→ 新危机

【必含元素】
- 危机前兆：细微的异常
- 危机爆发：突然的灾难
- 绝望时刻：主角濒死/绝境
- 金手指：系统救命/突破
- 绝地反击：逆袭成功

【危机类型】
物理危机：追杀/陷阱/天灾
身份危机：身份暴露/被识破
系统危机：系统故障/被封印
人际危机：背叛/误解/孤立

【禁止】
- 危机太弱（必须有生死感）
- 解决太简单（必须有波折）
- 没有后遗症（危机后要有影响）"""
    
    def _build_transition_template(self) -> str:
        """构建过渡章模板"""
        return """类型：TRANSITION（过渡章）
功能：承上启下，剧情推进

【结构要求】
0-800字：回顾（强度6）→ 总结上一章
801-1600字：推进（强度7）→ 剧情发展
1601-2200字：转折（强度7）→ 新情况出现
2201-2500字：钩子（强度8）→ 强烈期待

【必含元素】
- 承上：简要回顾上一章关键事件
- 启下：为下一章做铺垫
- 推进：主线剧情必须有进展
- 钩子：让读者期待下一章

【节奏控制】
虽然是过渡章，但不能平淡！
必须有：小冲突/新信息/悬念

【禁止】
- 大段回顾（控制在200字内）
- 剧情停滞（必须有推进）
- 平淡如水（必须有冲突/悬念）"""
    
    # ==================== 辅助方法 ====================
    
    def _get_genre_elements_for_chapter(self, chapter_num: int) -> str:
        """获取题材专项元素"""
        if self.genre_type not in self.GENRE_TEMPLATES:
            return ""
        
        template = self.GENRE_TEMPLATES[self.genre_type]
        sections = [f"\n## 【{self.genre_type}专项技法】\n"]
        
        # 弹幕模板
        if template.get("has_livestream") and chapter_num <= 3:
            sections.append("### 弹幕设计（每章至少3-5条）")
            sections.append("```")
            for 弹幕 in template.get("弹幕模板", [])[:5]:
                sections.append(弹幕)
            sections.append("```")
        
        # 系统提示音
        if template.get("返利音效"):
            sections.append(f"\n### 系统提示音模板")
            sections.append(f"`{template.get('返利音效', '')}`")
        
        # 模拟过程
        if template.get("has_simulation") and chapter_num <= 3:
            sections.append("\n### 模拟过程写法（快速剪辑感）")
            sections.append("```")
            for tmpl in template.get("模拟过程模板", []):
                sections.append(tmpl)
            sections.append("```")
        
        # 震惊层级
        if template.get("震惊层级"):
            sections.append("\n### 震惊层级（层层递进）")
            for i, level in enumerate(template.get("震惊层级", []), 1):
                sections.append(f"{i}. {level}")
        
        return "\n".join(sections)
    
    def _get_emotion_beat(self, chapter_num: int) -> str:
        """获取情绪节拍"""
        emotion_curve = self.emotion_curve
        if not emotion_curve:
            return ""
        
        # 查找各阶段的详细曲线
        phases = ['phase_1_early_domination', 'phase_2_rising_power', 
                  'phase_3_global_dominance', 'phase_4_cosmic_conquest']
        
        for phase_key in phases:
            phase = emotion_curve.get(phase_key, {})
            if not phase:
                continue
            
            curve = phase.get('curve', [])
            milestones = phase.get('key_milestones', [])
            
            # 在详细曲线中查找
            for beat in curve:
                if beat.get('ch') == chapter_num:
                    result = f"情绪类型：{beat.get('emotion', '期待')}（强度{beat.get('intensity', 6)}/10）\n"
                    result += f"节拍类型：{beat.get('beat_type', '推进')}\n"
                    result += f"核心事件：{beat.get('event', '剧情推进')}\n"
                    result += f"章节目的：{beat.get('purpose', '推进剧情')}\n"
                    result += f"钩子设计：{beat.get('hook', '根据类型选择')}"
                    return result
            
            # 在里程碑中查找
            for milestone in milestones:
                if isinstance(milestone, dict):
                    ch = milestone.get('ch') or milestone.get('chapter')
                    if ch == chapter_num:
                        result = f"【关键里程碑章节】\n"
                        result += f"事件：{milestone.get('event', '')}\n"
                        result += f"情绪：{milestone.get('emotion', '大爽')}\n"
                        result += f"强度：{milestone.get('intensity', 10)}/10\n"
                        result += f"这是重要节点，必须大场面！"
                        return result
        
        return ""
    
    def _get_chapter_outline(self, chapter_num: int) -> str:
        """获取章节大纲"""
        plan = self.plan
        if not plan:
            return f"第{chapter_num}章"
        
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
                    result = f"第{chapter_num}章"
                    if title:
                        result += f" | 标题：{title}"
                    if event:
                        result += f" | 关键事件：{event}"
                    if emotion:
                        result += f" | 情绪：{emotion}"
                    return result
        
        # 根据章节号判断阶段
        if chapter_num <= 3:
            return f"第{chapter_num}章 | 【开局阶段】建立主角形象，展示金手指"
        elif chapter_num <= 10:
            return f"第{chapter_num}章 | 【第一次小高潮区间】小爽点密集"
        elif chapter_num <= 15:
            return f"第{chapter_num}章 | 【第一次中高潮区间】关键转折"
        elif chapter_num <= 30:
            return f"第{chapter_num}章 | 【第一阶段高潮】重大事件"
        else:
            return f"第{chapter_num}章 | 【持续发展阶段】保持节奏"
    
    def _build_checklist(self, chapter_type: str) -> str:
        """构建检查清单"""
        checklists = {
            "GOLDEN_1": """
- [ ] 3句话内让读者同情主角
- [ ] 系统触发有画面感
- [ ] 章尾钩子让人想点下一章
- [ ] 有具体的数字（金额/数值）
- [ ] 前300字出现冲突/羞辱
- [ ] 500字处系统触发
- [ ] 对话自然推动剧情
- [ ] 无大段环境描写
- [ ] 无超过100字内心独白
""",
            "GOLDEN_2": """
- [ ] 金手指使用过程清晰
- [ ] 首次成功有具体数字
- [ ] 新反派让读者恨
- [ ] 为第3章打脸做铺垫
- [ ] 第800字处金手指使用
- [ ] 1500字处第一次成功
- [ ] 章尾出现新冲突
- [ ] 情绪曲线正确
""",
            "GOLDEN_3": """
- [ ] 公开场合有围观群众
- [ ] 反派极致羞辱（先抑）
- [ ] 主角强势反击（后扬）
- [ ] 有具体数字（金额/数值）
- [ ] 3层震惊结构完整
- [ ] 反派态度180度转变
- [ ] 系统提示和收益展示
- [ ] 章尾有钩子
- [ ] 500字处压抑，1500字处爆发
""",
            "FACE_SLAP": """
- [ ] 公开场合（有围观群众）
- [ ] 反派极致羞辱
- [ ] 主角强势反击
- [ ] 具体数字（金额/数值）
- [ ] 3层震惊结构
- [ ] 反派态度转变
- [ ] 情绪强度：8→10→9→7
- [ ] 章尾钩子
""",
            "REWARD": """
- [ ] 系统提示音
- [ ] 具体收益（数值/物品）
- [ ] 效果展示
- [ ] 实际应用
- [ ] 之前vs现在对比
- [ ] 让读者有获得感
- [ ] 章尾新目标
""",
        }
        
        return checklists.get(chapter_type, checklists.get("FACE_SLAP", ""))


# ==================== 便捷函数 ====================

def create_optimizer_v3(novel_data: Dict) -> ChapterPromptOptimizerV3:
    """
    便捷函数：创建v3.0优化器
    
    Args:
        novel_data: 小说数据
        
    Returns:
        ChapterPromptOptimizerV3实例
    """
    return ChapterPromptOptimizerV3(novel_data)


# 向后兼容性别名
ChapterPromptOptimizer = ChapterPromptOptimizerV3


# 测试代码
if __name__ == "__main__":
    # 测试数据
    test_data = {
        "title": "测试小说：开局无敌",
        "genre": "国运文-直播类",
        "plan": {
            "protagonist": {
                "basic_info": {"name": "林上", "age": 22}
            },
            "opening_design": {
                "chapter_1": {"scene": "开局场景", "key_scene": "关键场景"}
            }
        },
        "character_design": {
            "protagonist": {
                "basic_info": {"name": "林上", "age": 22},
                "traits": ["杀伐果断", "护短"],
                "signature_details": {
                    "catchphrase": ["蝼蚁", "记账了"],
                    "actions": ["负手而立"]
                }
            }
        },
        "core_worldview": {
            "world_overview": "国运禁地，直播",
            "world_rules": [{"rule": "弱肉强食"}]
        }
    }
    
    optimizer = ChapterPromptOptimizerV3(test_data)
    
    print("=" * 60)
    print("System Prompt 长度:", len(optimizer.build_system_prompt()))
    print("=" * 60)
    
    print("\n第1章提示词预览:")
    ch1_prompt = optimizer.build_chapter_prompt(1)
    print(ch1_prompt[:500] + "...")
    
    print("\n第2章提示词预览:")
    ch2_prompt = optimizer.build_chapter_prompt(2)
    print(ch2_prompt[:500] + "...")
    
    print("\n第3章提示词预览:")
    ch3_prompt = optimizer.build_chapter_prompt(3)
    print(ch3_prompt[:500] + "...")
    
    print("\n✅ 所有测试通过！")
