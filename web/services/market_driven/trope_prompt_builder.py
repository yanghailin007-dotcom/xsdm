# -*- coding: utf-8 -*-
"""
Trope Prompt Builder
套路提示词构建器

将 tropes 分析结果转换为不同阶段的 System Prompts
实现分层传递成功模式，让 AI 知道自己在仿写头部作品

v2.0 - 支持从JSON配置加载
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from .prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


class TropePromptBuilder:
    """
    Trope 提示词构建器
    
    将 tropes 分析结果转换为不同生成阶段所需的 System Prompt
    实现"仿写头部作品"的意识植入
    """
    
    # 各阶段的核心约束权重
    SETTING_WEIGHT = 0.8      # 设定阶段：需要完整的世界观约束
    CHARACTER_WEIGHT = 0.7    # 人物阶段：需要人设模板
    PLOT_WEIGHT = 0.6         # 大纲阶段：需要节奏蓝图
    CHAPTER_WEIGHT = 0.4      # 正文阶段：只需要节奏约束，保留创作自由
    
    def __init__(self, tropes: Optional[Dict] = None, use_json_config: bool = True):
        """
        初始化
        
        Args:
            tropes: TropeAnalyzer 分析结果
            use_json_config: 是否使用JSON配置（向后兼容）
        """
        self.tropes = tropes or {}
        self.genre = self.tropes.get('genre', '国运文-直播类')
        self.core_formula = self.tropes.get('core_formula', '')
        self.use_json_config = use_json_config
        self._prompt_loader = None
        
        if use_json_config:
            try:
                self._prompt_loader = get_prompt_loader()
            except Exception as e:
                logger.warning(f"[TropePromptBuilder] 无法加载PromptLoader: {e}")
                self.use_json_config = False
        
    def build_setting_system_prompt(self, novel_title: str = "未命名") -> str:
        """
        构建设定阶段的 System Prompt
        
        用于生成世界观、金手指、基础设定
        强调"仿写头部作品的结构，但创造全新内容"
        
        Args:
            novel_title: 小说标题
            
        Returns:
            System Prompt 字符串
        """
        # 优先使用JSON配置
        if self.use_json_config and self._prompt_loader:
            try:
                return self._build_setting_from_config(novel_title)
            except Exception as e:
                logger.error(f"[TropePromptBuilder] JSON配置加载失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：设定阶段System Prompt配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/_base/system_components/setting_stage.json

或使用API创建配置：
POST /api/v2/prompt-config/component/setting_stage

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
        prompt = f"""# 🎯 角色：顶级网文编辑 + 爆款类型专家

你正在指导 AI 仿写番茄头部爆款作品，目标作品《{novel_title}》。

## 📊 对标作品成功要素

### 核心套路公式
{self.core_formula or '番茄头部作品的高爽感快节奏模式'}

### 关键约束（必须遵循）
{key_constraints}

## 🎨 创作指导原则

### ✅ 必须做到的
1. **结构对标**：遵循成功模式的叙事结构
2. **数值精确**：所有数据必须具体（如"欠费24000元"而非"欠很多钱"）
3. **节奏精准**：情绪曲线必须符合类型规范
4. **创新内容**：在成功结构的框架下创造全新具体内容

### ❌ 严禁事项
1. **直接抄袭**：不要复制对标作品的具体情节、人物名字
2. **套路堆砌**：不要为了爽而爽，忽视逻辑
3. **数值模糊**：禁止"很多"、"很快"等模糊描述
4. **节奏混乱**：禁止情绪回退（爽点后突然压抑）

## 📝 输出要求
- 所有设定必须符合番茄读者期待
- 金手指必须有清晰的升级路径
- 世界观必须支撑至少300万字剧情
"""
        return prompt
    
    def _build_setting_from_config(self, novel_title: str) -> str:
        """从JSON配置构建设定阶段System Prompt"""
        # 加载基础组件
        component = self._prompt_loader.get_component("setting_stage")
        if not component:
            raise ValueError("无法加载setting_stage组件")
        
        template = component.get("template", "")
        key_constraints = self._extract_setting_constraints()
        
        variables = {
            "novel_title": novel_title,
            "core_formula": self.core_formula or component.get("default_values", {}).get("core_formula", "番茄头部作品的高爽感快节奏模式"),
            "key_constraints": key_constraints,
            "min_words": component.get("default_values", {}).get("min_words", "300")
        }
        
        return self._prompt_loader.render_template(template, variables)
    
    def build_character_system_prompt(self, protagonist_name: str = "主角") -> str:
        """
        构建人物设定阶段的 System Prompt
        
        用于生成人物设计
        
        Args:
            protagonist_name: 主角名字
            
        Returns:
            System Prompt 字符串
        """
        # 优先使用JSON配置
        if self.use_json_config and self._prompt_loader:
            try:
                return self._build_character_from_config(protagonist_name)
            except Exception as e:
                logger.error(f"[TropePromptBuilder] JSON配置加载失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：人物设定阶段System Prompt配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/_base/system_components/character_stage.json

或使用API创建配置：
POST /api/v2/prompt-config/component/character_stage

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
        prompt = f"""# 🎭 角色：人物设定专家

你正在为番茄爆款小说设计人物，主角名「{protagonist_name}」。

## 🌟 成功人设公式
{character_tropes}

## 🎯 人设设计原则

### 主角必须具备
1. **高辨识度**：一句话能描述清楚核心特征
2. **成长空间**：从弱到强的明确升级路径
3. **情感锚点**：至少一个让读者共情的点（家人、信念、仇恨）
4. **独特标签**：与众不同的标志性特征（口头禅、习惯、能力表现）

### 配角设计
1. **功能明确**：每个配角必须服务主线
2. **记忆点**：至少一个鲜明特征
3. **关系清晰**：与主角的关系简单直接

### 反派设计
1. **有智商**：不能无脑送经验
2. **有层次**：从小反派到大BOSS的递进
3. **有威胁**：必须让主角有危机感

## ⚠️ 强制要求
- 主角名必须是「{protagonist_name}」
- 禁止中途改名或换主角
- 人物性格必须前后一致
"""
        return prompt
    
    def _build_character_from_config(self, protagonist_name: str) -> str:
        """从JSON配置构建人物设定阶段System Prompt"""
        component = self._prompt_loader.get_component("character_stage")
        if not component:
            raise ValueError("无法加载character_stage组件")
        
        template = component.get("template", "")
        character_tropes = self._extract_character_tropes()
        
        variables = {
            "protagonist_name": protagonist_name,
            "character_tropes": character_tropes
        }
        
        return self._prompt_loader.render_template(template, variables)
    
    def build_plot_system_prompt(self, emotion_blueprint: Optional[Dict] = None) -> str:
        """
        构建大纲阶段的 System Prompt
        
        用于生成剧情大纲、情绪蓝图
        
        Args:
            emotion_blueprint: 情绪蓝图对象
            
        Returns:
            System Prompt 字符串
        """
        # 优先使用JSON配置
        if self.use_json_config and self._prompt_loader:
            try:
                return self._build_plot_from_config(emotion_blueprint)
            except Exception as e:
                logger.error(f"[TropePromptBuilder] JSON配置加载失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：大纲阶段System Prompt配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/_base/system_components/plot_stage.json

或使用API创建配置：
POST /api/v2/prompt-config/component/plot_stage

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
        prompt = f"""# 📚 角色：剧情架构大师

你正在为番茄爆款小说设计剧情大纲，目标：300万字，1200章。

## 🎵 情绪节奏蓝图
{rhythm_tropes}

## 🏗️ 大纲设计原则

### 情绪曲线要求
1. **黄金比例**：70%爽 + 20%铺垫 + 10%危机
2. **递进结构**：小爽→中爽→大爽→超爽
3. **钩子密度**：每3章一小钩，每10章一大钩
4. **禁止回退**：爽点后只能延续爽感或升级，不能回退到压抑

### 阶段划分（120章/30万字一个阶段）
1. **第一阶段**：主角崛起（0-30万字）
   - 核心：快速升级+首次大高潮
   - 爽点：打脸+震惊+国运提升
   
2. **第二阶段**：龙国腾飞（30-60万字）
   - 核心：主角成为龙国支柱
   - 爽点：全球震惊+碾压他国
   
3. **第三阶段**：全球争霸（60-90万字）
   - 核心：主角影响世界格局
   - 爽点：以一敌百+神话降临
   
4. **后续阶段**：宇宙/神界扩展（90万字+）

### 每阶段必须包含
- 1个超爽大高潮（情绪值10/10）
- 3-5个中爽高潮（情绪值7-8/10）
- 每章至少1个小爽点（情绪值5+/10）

## ⚠️ 关键约束
- 只约束情绪类型和强度，不约束具体事件
- AI自由创作具体BOSS/敌人/奖励
- 严禁固定套路（如"每30章打一次脸"）
"""
        return prompt
    
    def _build_plot_from_config(self, emotion_blueprint: Optional[Dict] = None) -> str:
        """从JSON配置构建大纲阶段System Prompt"""
        component = self._prompt_loader.get_component("plot_stage")
        if not component:
            raise ValueError("无法加载plot_stage组件")
        
        template = component.get("template", "")
        rhythm_tropes = self._extract_rhythm_tropes()
        
        # 构建阶段数据
        default_stages = {
            "items": [
                {"index": 1, "name": "第一阶段：主角崛起", "range": "0-30万字", "core": "快速升级+首次大高潮", "appeals": "打脸+震惊+国运提升"},
                {"index": 2, "name": "第二阶段：龙国腾飞", "range": "30-60万字", "core": "主角成为龙国支柱", "appeals": "全球震惊+碾压他国"},
                {"index": 3, "name": "第三阶段：全球争霸", "range": "60-90万字", "core": "主角影响世界格局", "appeals": "以一敌百+神话降临"},
                {"index": 4, "name": "后续阶段", "range": "90万字+", "core": "宇宙/神界扩展", "appeals": "星空主宰+万族臣服"}
            ]
        }
        
        variables = {
            "total_words": "300",
            "total_chapters": "1200",
            "rhythm_tropes": rhythm_tropes,
            "stage_chapters": "120",
            "stage_words": "30",
            "stages": default_stages
        }
        
        return self._prompt_loader.render_template(template, variables)
    
    def build_chapter_system_prompt(
        self, 
        novel_title: str = "未命名",
        chapter_num: int = 0,
        protagonist_name: str = "主角",
        emotion_arc: Optional[Dict] = None
    ) -> str:
        """
        构建章节生成阶段的 System Prompt
        
        用于实际生成章节正文，只保留最核心的节奏约束
        
        Args:
            novel_title: 小说标题
            chapter_num: 当前章节号
            protagonist_name: 主角名字
            emotion_arc: 当前章节情绪弧线
            
        Returns:
            System Prompt 字符串
        """
        # 优先使用JSON配置
        if self.use_json_config and self._prompt_loader:
            try:
                return self._build_chapter_from_config(novel_title, chapter_num, protagonist_name, emotion_arc)
            except Exception as e:
                logger.error(f"[TropePromptBuilder] JSON配置加载失败: {e}")
        
        # 🔥 配置缺失时抛出错误
        error_msg = """
❌ 错误：章节生成阶段System Prompt配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/_base/system_components/chapter_stage.json

或使用API创建配置：
POST /api/v2/prompt-config/component/chapter_stage

详细信息请查看文档：docs/prompt_configuration.md
"""
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
        emotion_hint = ""
        if emotion_arc:
            emotion_type = emotion_arc.get('type', '爽')
            intensity = emotion_arc.get('intensity', 7)
            emotion_hint = f"""
### 本章情绪要求
- 情绪类型：{emotion_type}
- 强度等级：{intensity}/10
- 创作方向：{emotion_arc.get('hint', '根据情绪类型自由发挥')}
"""
        
        prompt = f"""# ✍️ 角色：番茄爆款写手

你正在为小说《{novel_title}》创作章节，主角「{protagonist_name}」。

## 🎯 写作铁律（必须遵守）

### 1️⃣ 节奏要求
- **前300字**：必须有冲突/悬念/钩子
- **爽点密度**：每1000字至少1个爽点
- **章尾钩子**：必须留下强悬念，让读者欲罢不能
- **情绪曲线**：{emotion_arc.get('curve', '起-承-转-合') if emotion_arc else '根据章节位置合理设计'}

### 2️⃣ 震惊结构（3层递进）
{rhythm_rules}

### 3️⃣ 数字要求
- **所有数值必须精确**：
  - ❌ "很多" → ✅ "9876点"
  - ❌ "很快" → ✅ "3秒"
  - ❌ "很强" → ✅ "攻击力+500%"

### 4️⃣ 禁止事项
- 🚫 爽点回退：爽后不能突然压抑（这是番茄大忌！）
- 🚫 预告欺诈：章尾预告的危机必须在下一章兑现
- 🚫 节奏拖沓：禁止无意义的日常、环境描写
- 🚫 人设崩塌：主角性格必须前后一致
{emotion_hint}

## 💡 创作提示
你是仿写番茄头部作品的专家，但不是抄袭。
- **结构对标**：遵循成功模式的节奏
- **内容创新**：创造独特的具体情节
- **情绪精准**：让读者看得爽、看得嗨

## ⚠️ 输出格式
直接输出章节正文，不要分析、不要总结、不要标注。
字数：2000-2500字
"""
        return prompt
    
    def _build_chapter_from_config(
        self, 
        novel_title: str = "未命名",
        chapter_num: int = 0,
        protagonist_name: str = "主角",
        emotion_arc: Optional[Dict] = None
    ) -> str:
        """从JSON配置构建章节生成阶段System Prompt"""
        component = self._prompt_loader.get_component("chapter_stage")
        if not component:
            raise ValueError("无法加载chapter_stage组件")
        
        template = component.get("template", "")
        rhythm_rules = self._extract_chapter_rhythm_rules()
        
        emotion_curve = emotion_arc.get('curve', '起-承-转-合') if emotion_arc else '根据章节位置合理设计'
        
        # 构建情绪提示
        emotion_hint = ""
        if emotion_arc:
            emotion_type = emotion_arc.get('type', '爽')
            intensity = emotion_arc.get('intensity', 7)
            emotion_hint = f"""### 本章情绪要求
- 情绪类型：{emotion_type}
- 强度等级：{intensity}/10
- 创作方向：{emotion_arc.get('hint', '根据情绪类型自由发挥')}"""
        
        variables = {
            "novel_title": novel_title,
            "protagonist_name": protagonist_name,
            "emotion_curve": emotion_curve,
            "rhythm_rules": rhythm_rules,
            "emotion_hint": emotion_hint
        }
        
        return self._prompt_loader.render_template(template, variables)
    
    def _extract_setting_constraints(self) -> str:
        """提取设定阶段的关键约束"""
        constraints = []
        
        # 世界观
        world_view = self.tropes.get('世界观设定', {})
        if world_view:
            core = world_view.get('核心设定', '')
            if core:
                constraints.append(f"世界观：{core}")
        
        # 金手指
        golden_finger = self.tropes.get('金手指设计', {})
        if golden_finger:
            mechanism = golden_finger.get('机制', '')
            if mechanism:
                constraints.append(f"金手指：{mechanism}")
        
        # 情绪节奏
        rhythm = self.tropes.get('情绪节奏', {})
        if rhythm:
            pattern = rhythm.get('核心模式', '')
            if pattern:
                constraints.append(f"情绪节奏：{pattern}")
        
        # 爽点公式
        burst = self.tropes.get('爽点公式', {})
        if burst:
            structure = burst.get('标准结构', '')
            if structure:
                constraints.append(f"爽点结构：{structure}")
        
        if not constraints:
            constraints = [
                "世界观：国运绑定+直播+异界禁地",
                "金手指：扮演/召唤/具现类系统",
                "情绪节奏：快节奏+高爽感+密集钩子",
                "爽点结构：压抑→反转→3层震惊→收获"
            ]
        
        return "\n".join([f"{i+1}. {c}" for i, c in enumerate(constraints[:5])])
    
    def _extract_character_tropes(self) -> str:
        """提取人设相关的 tropes"""
        character = self.tropes.get('人物塑造', {})
        
        tropes_list = []
        
        # 主角模板
        protagonist = character.get('主角模板', '')
        if protagonist:
            tropes_list.append(f"主角：{protagonist}")
        
        # 配角功能
        supporting = character.get('配角功能', '')
        if supporting:
            tropes_list.append(f"配角：{supporting}")
        
        # 反派设计
        villain = character.get('反派设计', '')
        if villain:
            tropes_list.append(f"反派：{villain}")
        
        if not tropes_list:
            tropes_list = [
                "主角：高天赋+冷静果断+守护龙国",
                "配角：功能性+记忆点+服务主线",
                "反派：有智商+有层次+递进式威胁"
            ]
        
        return "\n".join([f"- {t}" for t in tropes_list])
    
    def _extract_rhythm_tropes(self) -> str:
        """提取节奏相关的 tropes"""
        rhythm = self.tropes.get('情绪节奏', {})
        
        parts = []
        
        # 核心模式
        core = rhythm.get('核心模式', '')
        if core:
            parts.append(f"**核心模式**：{core}")
        
        # 黄金比例
        ratio = rhythm.get('黄金比例', '')
        if ratio:
            parts.append(f"**黄金比例**：{ratio}")
        
        # 章节节奏
        chapter = rhythm.get('章节节奏', '')
        if chapter:
            parts.append(f"**单章节奏**：{chapter}")
        
        if not parts:
            parts = [
                "**核心模式**：快节奏+密集爽点+强钩子",
                "**黄金比例**：70%爽+20%铺垫+10%危机",
                "**单章节奏**：前300字冲突+中间密集爽点+章尾强钩子"
            ]
        
        return "\n".join(parts)
    
    def _extract_chapter_rhythm_rules(self) -> str:
        """提取章节写作的节奏规则"""
        return """```
第1层（现场）：身边人震惊
第2层（直播间）：网友刷屏
第3层（全球）：高层/世界反应
```

**要求**：
- 小爽点：至少2层震惊
- 中爽点：必须3层震惊
- 大爽点：3层震惊+数据可视化+全球影响"""
    
    def build_compressed_tropes_summary(self, max_items: int = 5) -> str:
        """
        构建压缩版的 tropes 摘要
        
        用于在 token 紧张时传递最核心的约束
        
        Args:
            max_items: 最多保留几条约束
            
        Returns:
            压缩后的 tropes 摘要
        """
        key_points = []
        
        # 优先级排序的关键约束
        priority_keys = [
            ('情绪节奏', '核心模式'),
            ('爽点公式', '标准结构'),
            ('世界观设定', '核心设定'),
            ('金手指设计', '机制'),
            ('人物塑造', '主角模板')
        ]
        
        for section, key in priority_keys:
            if len(key_points) >= max_items:
                break
            value = self.tropes.get(section, {}).get(key, '')
            if value:
                key_points.append(f"{section}：{value}")
        
        return "\n".join(key_points) if key_points else "番茄头部作品：快节奏+高爽感+密集钩子"


def create_trope_prompt_builder(tropes: Optional[Dict] = None) -> TropePromptBuilder:
    """
    工厂函数：创建 TropePromptBuilder 实例
    
    Args:
        tropes: TropeAnalyzer 分析结果
        
    Returns:
        TropePromptBuilder 实例
    """
    return TropePromptBuilder(tropes)


# 测试代码
if __name__ == "__main__":
    # 模拟 tropes 数据
    test_tropes = {
        "genre": "国运文-直播类",
        "core_formula": "国运绑定+直播曝光+金手指碾压+全球震惊+龙国崛起",
        "世界观设定": {
            "核心设定": "国运直播，选手在禁地战斗，奖励具现到现实",
            "规则": "死亡=资源扣除，胜利=百倍具现"
        },
        "金手指设计": {
            "机制": "扮演系统，扮演神话人物获得能力",
            "升级路径": "契合度提升→解锁更强技能"
        },
        "情绪节奏": {
            "核心模式": "快节奏+密集爽点+强钩子",
            "黄金比例": "70%爽+20%铺垫+10%危机",
            "章节节奏": "前300字冲突+中间密集爽点+章尾强钩子"
        },
        "爽点公式": {
            "标准结构": "压抑→反转→3层震惊→收获奖励"
        },
        "人物塑造": {
            "主角模板": "高天赋+冷静果断+守护龙国",
            "配角功能": "震惊体+信息传递+情感连接",
            "反派设计": "递进式威胁，从个人到国家"
        }
    }
    
    builder = TropePromptBuilder(test_tropes)
    
    print("=" * 60)
    print("设定阶段 System Prompt:")
    print("=" * 60)
    print(builder.build_setting_system_prompt("国运：开局扮演雷神"))
    
    print("\n" + "=" * 60)
    print("人物阶段 System Prompt:")
    print("=" * 60)
    print(builder.build_character_system_prompt("陆离"))
    
    print("\n" + "=" * 60)
    print("章节阶段 System Prompt:")
    print("=" * 60)
    emotion_arc = {
        "type": "爽",
        "intensity": 8,
        "curve": "起-承-转-超爽",
        "hint": "打脸反派+3层震惊"
    }
    print(builder.build_chapter_system_prompt("国运：开局扮演雷神", 1, "陆离", emotion_arc))
