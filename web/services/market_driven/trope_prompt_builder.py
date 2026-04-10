# -*- coding: utf-8 -*-
"""
Trope Prompt Builder
套路提示词构建器

将 tropes 分析结果转换为不同阶段的 System Prompts
所有提示词从 JSON 配置加载，无硬编码备用
"""

import json
import logging
from typing import Dict, List, Optional
from .prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


class TropePromptBuilder:
    """
    Trope 提示词构建器
    
    将 tropes 分析结果转换为不同生成阶段所需的 System Prompt
    所有提示词从 JSON 配置加载，无硬编码备用
    """
    
    def __init__(self, tropes: Optional[Dict] = None):
        """
        初始化
        
        Args:
            tropes: TropeAnalyzer 分析结果
        """
        self.tropes = tropes or {}
        # 默认使用通用题材，不再硬编码为国运文
        self.genre = self.tropes.get('genre', '未知题材')
        self.core_formula = self.tropes.get('core_formula', '')
        self._prompt_loader = get_prompt_loader()
        
    def build_setting_system_prompt(self, novel_title: str = "未命名") -> str:
        """构建设定阶段的 System Prompt"""
        return self._build_setting_from_config(novel_title)
    
    def _build_setting_from_config(self, novel_title: str) -> str:
        """从JSON配置构建设定阶段System Prompt"""
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
        """构建人物设定阶段的 System Prompt"""
        return self._build_character_from_config(protagonist_name)
    
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
        """构建大纲阶段的 System Prompt"""
        return self._build_plot_from_config(emotion_blueprint)
    
    def _build_plot_from_config(self, emotion_blueprint: Optional[Dict] = None) -> str:
        """从JSON配置构建大纲阶段System Prompt"""
        component = self._prompt_loader.get_component("plot_stage")
        if not component:
            raise ValueError("无法加载plot_stage组件")
        
        template = component.get("template", "")
        rhythm_tropes = self._extract_rhythm_tropes()
        
        # 根据题材类型提供默认阶段设定
        if "神豪" in self.genre:
            default_stages = {
                "items": [
                    {"index": 1, "name": "第一阶段：初露锋芒", "range": "0-30万字", "core": "系统激活+首次消费高潮", "appeals": "打脸+震惊+财富积累"},
                    {"index": 2, "name": "第二阶段：商业帝国", "range": "30-60万字", "core": "主角建立商业版图", "appeals": "震惊社交圈+碾压对手"},
                    {"index": 3, "name": "第三阶段：资本巅峰", "range": "60-90万字", "core": "主角影响行业格局", "appeals": "以一敌百+垄断地位"},
                    {"index": 4, "name": "后续阶段", "range": "90万字+", "core": "全球布局/跨界扩展", "appeals": "商业传奇+时代印记"}
                ]
            }
        elif "国运" in self.genre:
            default_stages = {
                "items": [
                    {"index": 1, "name": "第一阶段：主角崛起", "range": "0-30万字", "core": "快速升级+首次大高潮", "appeals": "打脸+震惊+国运提升"},
                    {"index": 2, "name": "第二阶段：龙国腾飞", "range": "30-60万字", "core": "主角成为龙国支柱", "appeals": "全球震惊+碾压他国"},
                    {"index": 3, "name": "第三阶段：全球争霸", "range": "60-90万字", "core": "主角影响世界格局", "appeals": "以一敌百+神话降临"},
                    {"index": 4, "name": "后续阶段", "range": "90万字+", "core": "宇宙/神界扩展", "appeals": "星空主宰+万族臣服"}
                ]
            }
        else:
            default_stages = {
                "items": [
                    {"index": 1, "name": "第一阶段：主角成长", "range": "0-30万字", "core": "能力觉醒+首次突破", "appeals": "打脸+震惊+实力提升"},
                    {"index": 2, "name": "第二阶段：建立势力", "range": "30-60万字", "core": "主角成为一方强者", "appeals": "震惊各界+碾压对手"},
                    {"index": 3, "name": "第三阶段：巅峰对决", "range": "60-90万字", "core": "主角影响世界格局", "appeals": "终极一战+成就传奇"},
                    {"index": 4, "name": "后续阶段", "range": "90万字+", "core": "更高维度扩展", "appeals": "开创纪元+万民敬仰"}
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
        """构建章节生成阶段的 System Prompt"""
        return self._build_chapter_from_config(
            novel_title, chapter_num, protagonist_name, emotion_arc
        )
    
    def _build_chapter_from_config(
        self, 
        novel_title: str = "未命名",
        chapter_num: int = 0,
        protagonist_name: str = "主角",
        emotion_arc: Optional[Dict] = None
    ) -> str:
        """从JSON配置构建章节生成阶段System Prompt - 支持多题材模板"""
        component = self._prompt_loader.get_component("chapter_stage")
        if not component:
            raise ValueError("无法加载chapter_stage组件，请检查 prompt_packages/_base/system_components/chapter_stage.json")
        
        # 获取题材类型对应的模板
        templates = component.get("templates", {})
        default_key = component.get("default_template", "通用")
        
        # 根据 genre 选择模板
        genre_key = self.genre if self.genre in templates else None
        if not genre_key:
            # 尝试模糊匹配
            if "国运" in self.genre and "国运文" in templates:
                genre_key = "国运文"
            elif "神豪" in self.genre and "神豪文" in templates:
                genre_key = "神豪文"
            else:
                genre_key = default_key
        
        template = templates.get(genre_key, templates.get(default_key, ""))
        
        # 兼容旧版单模板结构
        if not template:
            template = component.get("template", "")
        
        if not template:
            raise ValueError(f"无法加载chapter_stage模板，genre={self.genre}")
        
        logger.info(f"[TropePromptBuilder] 使用 {genre_key} 章节模板")
        
        rhythm_rules = self._extract_chapter_rhythm_rules()
        
        emotion_curve = emotion_arc.get('curve', '起-承-转-合') if emotion_arc else '根据章节位置合理设计'
        
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
            "chapter_num": chapter_num,
            "protagonist_name": protagonist_name,
            "emotion_curve": emotion_curve,
            "rhythm_rules": rhythm_rules,
            "emotion_hint": emotion_hint
        }
        
        return self._prompt_loader.render_template(template, variables)
    
    def _extract_setting_constraints(self) -> str:
        """提取设定阶段的关键约束"""
        constraints = []
        
        world_view = self.tropes.get('世界观设定', {})
        if world_view:
            core = world_view.get('核心设定', '')
            if core:
                constraints.append(f"世界观：{core}")
        
        golden_finger = self.tropes.get('金手指设计', {})
        if golden_finger:
            mechanism = golden_finger.get('机制', '')
            if mechanism:
                constraints.append(f"金手指：{mechanism}")
        
        rhythm = self.tropes.get('情绪节奏', {})
        if rhythm:
            pattern = rhythm.get('核心模式', '')
            if pattern:
                constraints.append(f"情绪节奏：{pattern}")
        
        burst = self.tropes.get('爽点公式', {})
        if burst:
            structure = burst.get('标准结构', '')
            if structure:
                constraints.append(f"爽点结构：{structure}")
        
        if not constraints:
            # 根据题材类型提供默认约束
            if "神豪" in self.genre:
                constraints = [
                    "世界观：都市背景+财富系统+阶层跃迁",
                    "金手指：花钱返利/签到奖励类系统",
                    "情绪节奏：快节奏+高爽感+密集钩子",
                    "爽点结构：被看不起→展现实力→震惊众人→收获尊重"
                ]
            elif "国运" in self.genre:
                constraints = [
                    "世界观：国运绑定+直播+异界禁地",
                    "金手指：扮演/召唤/具现类系统",
                    "情绪节奏：快节奏+高爽感+密集钩子",
                    "爽点结构：压抑→反转→3层震惊→收获"
                ]
            else:
                constraints = [
                    f"世界观：{self.genre}典型背景设定",
                    "金手指：符合题材特色的能力系统",
                    "情绪节奏：快节奏+高爽感+密集钩子",
                    "爽点结构：困境→突破→震惊→收获"
                ]
        
        return "\n".join([f"{i+1}. {c}" for i, c in enumerate(constraints[:5])])
    
    def _extract_character_tropes(self) -> str:
        """提取人设相关的 tropes"""
        character = self.tropes.get('人物塑造', {})
        
        tropes_list = []
        
        protagonist = character.get('主角模板', '')
        if protagonist:
            tropes_list.append(f"主角：{protagonist}")
        
        supporting = character.get('配角功能', '')
        if supporting:
            tropes_list.append(f"配角：{supporting}")
        
        villain = character.get('反派设计', '')
        if villain:
            tropes_list.append(f"反派：{villain}")
        
        if not tropes_list:
            # 根据题材类型提供默认人设
            if "神豪" in self.genre:
                tropes_list = [
                    "主角：获得财富系统+果断豪爽+阶层跃迁",
                    "配角：势利眼反派+美女秘书+商业对手",
                    "反派：有钱无德+被打脸+递进式登场"
                ]
            elif "国运" in self.genre:
                tropes_list = [
                    "主角：高天赋+冷静果断+守护龙国",
                    "配角：功能性+记忆点+服务主线",
                    "反派：有智商+有层次+递进式威胁"
                ]
            else:
                tropes_list = [
                    "主角：独特能力+坚定意志+成长型",
                    "配角：功能性+记忆点+服务主线",
                    "反派：有智商+有层次+递进式威胁"
                ]
        
        return "\n".join([f"- {t}" for t in tropes_list])
    
    def _extract_rhythm_tropes(self) -> str:
        """提取节奏相关的 tropes"""
        rhythm = self.tropes.get('情绪节奏', {})
        
        parts = []
        
        core = rhythm.get('核心模式', '')
        if core:
            parts.append(f"**核心模式**：{core}")
        
        ratio = rhythm.get('黄金比例', '')
        if ratio:
            parts.append(f"**黄金比例**：{ratio}")
        
        chapter = rhythm.get('章节节奏', '')
        if chapter:
            parts.append(f"**单章节奏**：{chapter}")
        
        if not parts:
            # 根据题材类型提供默认节奏
            if "神豪" in self.genre:
                parts = [
                    "**核心模式**：快节奏+密集爽点+消费即正义",
                    "**黄金比例**：70%爽+20%铺垫+10%危机",
                    "**单章节奏**：前300字冲突+中间密集爽点+章尾强钩子"
                ]
            elif "国运" in self.genre:
                parts = [
                    "**核心模式**：快节奏+密集爽点+国运升级",
                    "**黄金比例**：70%爽+20%铺垫+10%危机",
                    "**单章节奏**：前300字冲突+中间密集爽点+章尾强钩子"
                ]
            else:
                parts = [
                    "**核心模式**：快节奏+密集爽点+强钩子",
                    "**黄金比例**：70%爽+20%铺垫+10%危机",
                    "**单章节奏**：前300字冲突+中间密集爽点+章尾强钩子"
                ]
        
        return "\n".join(parts)
    
    def _extract_chapter_rhythm_rules(self) -> str:
        """提取章节写作的节奏规则"""
        from .style_loader import StyleLoader
        
        try:
            style_loader = StyleLoader()
            shock_flow = style_loader.load_style("shock_flow")
            
            if shock_flow:
                principles = shock_flow.get('core_principles', [])
                principles_text = "\n".join([f"- {p}" for p in principles])
                
                levels = shock_flow.get('levels', {})
                levels_desc = []
                
                sorted_levels = sorted(levels.items(), key=lambda x: x[1].get('order', 999))
                for level_id, level_info in sorted_levels:
                    name = level_info.get('name', level_id)
                    desc = level_info.get('description', '')
                    levels_desc.append(f"- {name}：{desc}")
                
                levels_text = "\n".join(levels_desc)
                
                word_count_guide = shock_flow.get('word_count_guide', {})
                total_range = word_count_guide.get('total', '600-1000字')
                
                return f"""{principles_text}

**震惊铺展顺序**（禁止写"第X层"标签）：
{levels_text}

**字数分配**：震惊部分占章节总字数 {total_range}"""
        
        except Exception as e:
            logger.warning(f"[TropePromptBuilder] 加载 shock_flow.json 失败: {e}")
        
        # 根据题材类型返回默认 rhythm rules
        if "国运" in self.genre:
            return """震惊铺展顺序（禁止写"第X层"标签）：
- 先写现场：当事人的表情、动作、内心反应
- 再写直播：弹幕停滞→爆炸，主播失态/造梗  
- 最后权威：专家/官方从质疑到震惊的递进

**弹幕格式要求**（国运文必填）：
- 弹幕用【】包裹，如：【龙国观众：卧槽！】
- 每章至少8-10条弹幕

**要求**：
- 小爽点：至少2层震惊
- 中爽点：必须3层震惊
- 大爽点：3层震惊+数据可视化+全球影响"""
        elif "神豪" in self.genre:
            return """震惊铺展顺序（禁止写"第X层"标签）：
- 先写现场：当事人的表情、动作、内心反应
- 再写围观：路人的议论、围观者的反应
- 最后权威：专家/上层人士从质疑到震惊的递进

**对话格式要求**（神豪文必填）：
- 角色对话用 "" 包裹
- 增加路人震惊台词，用 "" 包裹

**要求**：
- 小爽点：至少2层震惊
- 中爽点：必须3层震惊
- 大爽点：3层震惊+具体金额/数字+阶层跨越"""
        else:
            return """震惊铺展顺序（禁止写"第X层"标签）：
- 先写现场：当事人的表情、动作、内心反应
- 再写传播：旁观者的反应、消息扩散
- 最后权威：专家/上层从质疑到震惊的递进

**要求**：
- 小爽点：至少2层震惊
- 中爽点：必须3层震惊
- 大爽点：3层震惊+数据化呈现+广泛影响"""
    
    def build_compressed_tropes_summary(self, max_items: int = 5) -> str:
        """构建压缩版的 tropes 摘要"""
        key_points = []
        
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
    """工厂函数：创建 TropePromptBuilder 实例"""
    return TropePromptBuilder(tropes)
