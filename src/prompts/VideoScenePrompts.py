"""
视频场景生成提示词生成器

用于从中级事件生成具体的、可视化的场景描述，
类似小说场景生成时的详细提示词。
"""

from typing import Dict, List
from src.utils.logger import get_logger


class VideoScenePrompts:
    """视频场景生成提示词"""
    
    def __init__(self):
        self.logger = get_logger("VideoScenePrompts")
    
    def generate_scene_prompt(self, medium_event: Dict, novel_data: Dict) -> str:
        """
        为单个中级事件生成详细的场景提示词
        
        Args:
            medium_event: 中级事件数据
            novel_data: 小说完整数据
            
        Returns:
            详细的场景生成提示词
        """
        event_name = medium_event.get("name", "未命名事件")
        event_description = medium_event.get("description", "")
        stage = medium_event.get("stage", "发展")
        
        # 提取角色信息
        characters = self._extract_relevant_characters(medium_event, novel_data)
        
        # 提取场景信息
        scene_info = self._extract_scene_info(medium_event, novel_data)
        
        # 提取视觉风格
        visual_style = self._extract_visual_style(novel_data)
        
        # 生成提示词
        prompt = f"""# 视频场景生成请求

## 事件信息
**事件名称**: {event_name}
**叙事阶段**: {stage}
**事件描述**: {event_description}

## 场景设定
**场景位置**: {scene_info.get('location', '待定')}
**环境氛围**: {scene_info.get('atmosphere', '根据情绪自动适配')}
**时间设定**: {scene_info.get('time', '根据剧情自动确定')}

## 角色信息
{self._format_characters(characters)}

## 视觉风格要求
**整体风格**: {visual_style.get('overall_style', '写实风格')}
**色彩基调**: {visual_style.get('color_palette', '根据情绪调整')}
**光影效果**: {visual_style.get('lighting', '自然光')}
**构图风格**: {visual_style.get('composition', '电影级构图')}

## 镜头设计要求
根据叙事阶段"【{stage}】"设计镜头序列：

### 起因阶段 (如果适用)
- 开场使用全景或大远景建立环境
- 镜头缓慢推近，营造渐进的紧张感
- 时长: 4-5秒/镜头
- 节奏: 缓慢，信息渐进释放

### 发展阶段 (如果适用)
- 使用中景和近景展示角色互动
- 镜头运动多样，保持视觉新鲜感
- 时长: 3-4秒/镜头
- 节奏: 明快，信息密集

### 高潮阶段 (如果适用)
- 大量使用特写和大特写强调关键细节
- 快速剪辑配合激烈运镜（手持、推拉、环绕）
- 时长: 2-6秒/镜头（变化幅度大）
- 节奏: 极快，情绪爆发
- 特效: 高潮时刻可使用慢动作突出决定性瞬间

### 结局阶段 (如果适用)
- 使用全景和中景展示结果
- 镜头缓慢拉远，释放情绪
- 时长: 4-5秒/镜头
- 节奏: 舒缓，留下余韵

## 关键视觉元素
请确保以下关键元素在场景中得到突出：
{self._format_key_elements(medium_event)}

## 音频同步设计
**背景音乐**: {self._generate_bgm_suggestion(stage)}
**音效重点**: {self._generate_sfx_suggestions(medium_event)}
**音频节奏**: 与镜头节奏完美匹配，{stage}阶段应体现"{self._get_audio_mood(stage)}"的听觉感受

## 生成要求
1. **视觉连贯性**: 所有镜头应共同构成一个完整的视觉叙事
2. **情绪递进**: 场景应体现{self._get_emotional_arc(medium_event)}的情感曲线
3. **细节丰富**: 环境细节、角色表情、动作细节都应清晰可见
4. **风格统一**: 整体风格与小说世界观保持一致
5. **可执行性**: 每个镜头的描述都应足够具体，可直接用于视频生成

## 输出格式
请为场景生成详细的分镜头脚本，每个镜头包含：
- 镜头编号
- 景别（全景/中景/近景/特写/大特写）
- 运镜方式
- 时长（秒）
- 详细的视觉描述（包含环境、角色、动作、情绪）
- 音频提示（背景音乐、音效、节奏）
- 生成提示词（用于AI视频生成的具体描述）
"""
        return prompt
    
    def _extract_relevant_characters(self, medium_event: Dict, novel_data: Dict) -> List[Dict]:
        """提取与事件相关的角色"""
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(self.logger)
        
        all_characters = event_extractor.extract_character_designs(novel_data)
        
        # 从事件描述中提取相关角色
        event_characters = medium_event.get("characters", "")
        relevant_characters = []
        
        for char in all_characters:
            char_name = char.get("name", "")
            if char_name in event_characters or not event_characters:
                relevant_characters.append(char)
        
        return relevant_characters
    
    def _extract_scene_info(self, medium_event: Dict, novel_data: Dict) -> Dict:
        """提取场景信息"""
        location = medium_event.get("location", "")
        emotion = medium_event.get("emotion", "")
        
        # 根据情绪推断环境氛围
        atmosphere_map = {
            "紧张": "压抑、紧凑的空间，光线偏暗",
            "激烈": "动态感强，可能有破坏痕迹",
            "温馨": "柔和光线，温暖色调",
            "悲壮": "宏大场景，悲怆氛围"
        }
        
        atmosphere = atmosphere_map.get(emotion, "根据剧情情绪自动适配")
        
        return {
            "location": location or "根据事件内容自动确定",
            "atmosphere": atmosphere,
            "time": "根据剧情自动确定"
        }
    
    def _extract_visual_style(self, novel_data: Dict) -> Dict:
        """提取视觉风格"""
        category = novel_data.get("category", "玄幻")
        
        style_map = {
            "玄幻": {
                "overall_style": "东方幻想风格，特效华丽",
                "color_palette": "金色、紫色、青色为主，仙气飘渺",
                "lighting": "法术光效，环境光柔和",
                "composition": "对称构图，大场景与小细节结合"
            },
            "武侠": {
                "overall_style": "古风写实，动作流畅",
                "color_palette": "自然色调，棕绿色为主",
                "lighting": "自然光，晨光夕照",
                "composition": "动态构图，强调动作线条"
            },
            "都市": {
                "overall_style": "现代写实",
                "color_palette": "城市色调，霓虹灯光",
                "lighting": "城市夜景灯光，室内照明",
                "composition": "现代构图，多视角"
            },
            "科幻": {
                "overall_style": "未来感，科技美学",
                "color_palette": "蓝白为主，金属质感",
                "lighting": "冷光，全息投影光效",
                "composition": "几何构图，科技感强"
            }
        }
        
        return style_map.get(category, style_map["玄幻"])
    
    def _format_characters(self, characters: List[Dict]) -> str:
        """格式化角色信息"""
        if not characters:
            return "暂无特定角色要求"
        
        char_lines = []
        for char in characters[:5]:  # 最多显示5个主要角色
            name = char.get("name", "未命名")
            role = char.get("role", "角色")
            appearance = char.get("appearance", char.get("living_characteristics", {}).get("physical_presence", "待定"))
            
            char_lines.append(f"- **{name}** ({role}): {appearance}")
        
        return "\n".join(char_lines)
    
    def _format_key_elements(self, medium_event: Dict) -> str:
        """格式化关键视觉元素"""
        elements = []
        
        # 从事件中提取关键元素
        if medium_event.get("key_action"):
            elements.append(f"关键动作: {medium_event['key_action']}")
        
        if medium_event.get("visual_highlight"):
            elements.append(f"视觉亮点: {medium_event['visual_highlight']}")
        
        if medium_event.get("emotional_focus"):
            elements.append(f"情绪焦点: {medium_event['emotional_focus']}")
        
        if not elements:
            elements.append("根据事件内容自动提取关键视觉元素")
        
        return "\n".join([f"  - {e}" for e in elements])
    
    def _generate_bgm_suggestion(self, stage: str) -> str:
        """生成背景音乐建议"""
        bgm_map = {
            "起因": "渐进式紧张音乐，缓慢增强",
            "发展": "节奏明快音乐，中等强度",
            "高潮": "紧张激烈音乐，高强度",
            "结局": "舒缓释放音乐，逐渐减弱"
        }
        return bgm_map.get(stage, "根据场景情绪调整")
    
    def _generate_sfx_suggestions(self, medium_event: Dict) -> str:
        """生成音效建议"""
        sfx_list = []
        
        # 根据事件类型添加音效
        if "战斗" in medium_event.get("name", ""):
            sfx_list.append("兵器碰撞声、冲击波音效")
        elif "对话" in medium_event.get("name", ""):
            sfx_list.append("环境音、轻微脚步声")
        else:
            sfx_list.append("根据场景动作添加相应音效")
        
        return "、".join(sfx_list)
    
    def _get_audio_mood(self, stage: str) -> str:
        """获取音频情绪"""
        mood_map = {
            "起因": "渐进，建立期待感",
            "发展": "明快，信息密集",
            "高潮": "激烈，情绪爆发",
            "结局": "舒缓，释放余韵"
        }
        return mood_map.get(stage, "中等")
    
    def _get_emotional_arc(self, medium_event: Dict) -> str:
        """获取情感弧线"""
        stage = medium_event.get("stage", "发展")
        
        arc_map = {
            "起因": "平静 → 好奇 → 紧张",
            "发展": "紧张 → 焦虑 → 升级",
            "高潮": "紧张 → 爆发 → 释放",
            "结局": "释放 → 平复 → 思考"
        }
        
        return arc_map.get(stage, "根据剧情自动调整")
    
    def generate_video_type_prompt(
        self, 
        selected_events: List[Dict],
        selected_characters: List[Dict],
        video_type: str,
        novel_data: Dict
    ) -> str:
        """
        生成视频类型级别的提示词
        
        Args:
            selected_events: 选中的事件列表
            selected_characters: 选中的角色列表
            video_type: 视频类型 (long_series/short_film/short_video)
            novel_data: 小说数据
            
        Returns:
            视频生成提示词
        """
        # 获取视频类型配置
        type_configs = {
            "long_series": {
                "name": "长篇剧集",
                "duration": "1-5分钟/集",
                "characteristics": "多集连续，每集完整但有关联，保留丰富的支线剧情，节奏张弛有度"
            },
            "short_film": {
                "name": "短片/动画电影",
                "duration": "3-10分钟",
                "characteristics": "精简情节，聚焦主线，节奏紧凑，视觉表现力强"
            },
            "short_video": {
                "name": "短视频系列",
                "duration": "30秒-1分钟",
                "characteristics": "极度精炼，只保留高光时刻，节奏极快，视觉冲击力强"
            }
        }
        
        config = type_configs.get(video_type, type_configs["long_series"])
        
        # 构建事件摘要
        events_summary = self._format_events_summary(selected_events)
        
        # 构建角色摘要
        characters_summary = self._format_characters_summary(selected_characters)
        
        # 生成提示词
        prompt = f"""# 视频生成请求

## 项目信息
**小说标题**: {novel_data.get('novel_title', '未命名')}
**视频类型**: {config['name']}
**目标时长**: {config['duration']}
**风格特点**: {config['characteristics']}

## 内容概览

### 选中事件 ({len(selected_events)}个)
{events_summary}

### 出场角色 ({len(selected_characters)}个)
{characters_summary}

## 生成要求

### 1. 分集策略 ({video_type})
根据视频类型"{config['name']}"的要求：

{self._get_episode_strategy(video_type, selected_events)}

### 2. 视觉风格
- 整体风格：{self._extract_visual_style(novel_data).get('overall_style', '写实')}
- 色彩基调：根据场景情绪动态调整
- 构图风格：电影级构图，注重视觉美感
- 特效要求：{self._get_vfx_requirements(novel_data)}

### 3. 节奏控制
- 开场：快速建立冲突，{self._get_opening_pace(video_type)}
- 发展：{self._get_development_pace(video_type)}
- 高潮：情绪爆发，{self._get_climax_pace(video_type)}
- 结尾：{self._get_ending_pace(video_type)}

### 4. 音频设计
- 背景音乐：根据场景情绪自动适配
- 音效：环境音、动作音效、情绪音效
- 音画同步：音频节奏与镜头节奏完美匹配

### 5. 质量标准
- **视觉连贯性**: 所有镜头风格统一，构成完整叙事
- **情绪传递**: 每个场景都应清晰传达目标情绪
- **细节丰富**: 环境、角色、动作细节清晰可见
- **可执行性**: 每个镜头描述具体，可直接用于AI生成

## 输出格式
请为每个选中事件生成详细的分镜头脚本，包含：
1. 事件编号和名称
2. 场景描述（环境、角色、情绪）
3. 镜头序列（5-15个镜头，根据事件重要性调整）
4. 每个镜头的详细描述（景别、运镜、时长、视觉内容）
5. 音频设计（背景音乐、音效、节奏）

每个镜头的生成提示词应具体到可以直接输入AI视频生成工具。
"""
        return prompt
    
    def _format_events_summary(self, events: List[Dict]) -> str:
        """格式化事件摘要"""
        if not events:
            return "暂无选中事件"
        
        lines = []
        for i, event in enumerate(events[:10], 1):  # 最多显示10个
            name = event.get("name", "未命名")
            stage = event.get("stage", "")
            desc = event.get("description", "")[:50]
            
            lines.append(f"{i}. **{name}** ({stage}): {desc}...")
        
        if len(events) > 10:
            lines.append(f"... 以及其他 {len(events) - 10} 个事件")
        
        return "\n".join(lines)
    
    def _format_characters_summary(self, characters: List[Dict]) -> str:
        """格式化角色摘要"""
        if not characters:
            return "暂无选中角色"
        
        lines = []
        for char in characters[:5]:  # 最多显示5个
            name = char.get("name", "未命名")
            role = char.get("role", "角色")
            lines.append(f"- **{name}** ({role})")
        
        if len(characters) > 5:
            lines.append(f"- 以及其他 {len(characters) - 5} 个角色")
        
        return "\n".join(lines)
    
    def _get_episode_strategy(self, video_type: str, events: List[Dict]) -> str:
        """获取分集策略"""
        if video_type == "long_series":
            return """**基于中级事件分集**:
- 每个中级事件独立成为一集
- 起因事件: 5个镜头，约2分钟
- 发展事件: 8个镜头，约3.5分钟  
- 高潮事件: 15个镜头，约7.5分钟（时长加倍）
- 结局事件: 4个镜头，约1.8分钟
- 按叙事顺序（起因→发展→高潮→结局）排列"""
        
        elif video_type == "short_film":
            return """**精简为单个作品**:
- 从所有事件中选择3-8个核心重大事件
- 每个事件5-7个镜头
- 总时长5-30分钟
- 删除支线，聚焦主线剧情"""
        
        elif video_type == "short_video":
            return """**极简短视频**:
- 每个重大事件 = 1个短视频
- 只保留高光时刻
- 5-7个快速镜头
- 前3秒必须有钩子
- 总时长30秒-1分钟"""
        
        return "根据内容自动调整"
    
    def _get_vfx_requirements(self, novel_data: Dict) -> str:
        """获取特效要求"""
        category = novel_data.get("category", "玄幻")
        
        vfx_map = {
            "玄幻": "法术特效、灵气光效、空间扭曲",
            "武侠": "动作特效、武器光效、速度线",
            "都市": "少量特效，偏向写实",
            "科幻": "全息投影、能量光效、科技特效"
        }
        
        return vfx_map.get(category, "根据场景需求添加")
    
    def _get_opening_pace(self, video_type: str) -> str:
        """获取开场节奏"""
        pace_map = {
            "long_series": "3-5分钟建立冲突",
            "short_film": "1-2分钟快速建立冲突",
            "short_video": "前3秒必须有钩子"
        }
        return pace_map.get(video_type, "快速建立")
    
    def _get_development_pace(self, video_type: str) -> str:
        """获取发展节奏"""
        pace_map = {
            "long_series": "多线并进，支线丰富",
            "short_film": "快速推进，无冗余",
            "short_video": "每秒都有信息，节奏极快"
        }
        return pace_map.get(video_type, "稳步推进")
    
    def _get_climax_pace(self, video_type: str) -> str:
        """获取高潮节奏"""
        pace_map = {
            "long_series": "情绪充分释放",
            "short_film": "高潮集中，情感爆发",
            "short_video": "连续冲击，极快节奏"
        }
        return pace_map.get(video_type, "情绪爆发")
    
    def _get_ending_pace(self, video_type: str) -> str:
        """获取结尾节奏"""
        pace_map = {
            "long_series": "为下集铺垫",
            "short_film": "简洁有力，可留白",
            "short_video": "意外反转或悬念"
        }
        return pace_map.get(video_type, "自然收尾")


# 创建全局实例
_video_scene_prompts_instance = None

def get_video_scene_prompts() -> VideoScenePrompts:
    """获取视频场景提示词实例（单例模式）"""
    global _video_scene_prompts_instance
    if _video_scene_prompts_instance is None:
        _video_scene_prompts_instance = VideoScenePrompts()
    return _video_scene_prompts_instance