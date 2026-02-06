"""
VeO Prompt 生成服务
将中文故事描述转换为专业的英文 AI 视频提示词
"""
import json
import re
from typing import Dict, List, Optional
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent


class VeOPromptService:
    """VeO 提示词生成服务"""
    
    # VeO 优化的关键视觉元素
    VISUAL_ELEMENTS = {
        "lighting": [
            "golden hour lighting", "dim blue lighting", "warm candlelight",
            "harsh sunlight", "soft moonlight", "neon glow", "dramatic shadows",
            "backlit silhouette", "rim lighting", "diffuse ambient light"
        ],
        "camera_angles": [
            "wide shot", "medium shot", "close-up", "extreme close-up",
            "overhead shot", "low angle shot", "eye level shot",
            "dutch angle", "tracking shot", "static shot"
        ],
        "mood_colors": {
            "tense": "cool blue and grey tones",
            "romantic": "warm golden and pink tones",
            "mysterious": "deep purple and dark blue tones",
            "action": "high contrast with saturated colors",
            "peaceful": "soft pastel and natural tones",
            "horror": "desaturated with green tint"
        },
        "cinematic_styles": [
            "cinematic", "photorealistic", "8k resolution", "film grain",
            "anamorphic lens", "bokeh background", "shallow depth of field"
        ]
    }
    
    @classmethod
    def generate_prompt(cls, 
                       scene_title_cn: str,
                       scene_title_en: str,
                       story_beat_cn: str,
                       dialogues: List[Dict],
                       emotional_arc: str,
                       characters: List[Dict] = None) -> Dict[str, str]:
        """
        生成 VeO 优化的提示词（同时生成三种模式，供视频生成时选择）
        
        Returns:
            {
                "veo_prompt_standard": "标准模式英文",
                "veo_prompt_reference": "参考图模式英文", 
                "veo_prompt_frames": "首尾帧模式英文",
                "visual_description_standard": "标准模式中文",
                "visual_description_reference": "参考图模式中文",
                "visual_description_frames": "首尾帧模式中文",
                "image_prompt": "角色参考图提示词",
                "negative_prompt": "负面提示词",
                "metadata": {"解析出的关键元素"}
            }
        """
        # 构建基础提示词组件
        components = {
            "subject": cls._extract_subject(scene_title_cn, story_beat_cn, characters),
            "setting": cls._extract_setting(story_beat_cn),
            "action": cls._extract_action(story_beat_cn, dialogues),
            "lighting": cls._select_lighting(emotional_arc),
            "camera": cls._select_camera_angle(story_beat_cn),
            "style": cls._select_cinematic_style(emotional_arc),
            "mood": cls._extract_mood(emotional_arc)
        }
        
        # 🔥 同时生成三种模式的提示词
        # 1. 标准模式
        veo_prompt_standard = cls._build_veo_prompt(components)
        visual_description_standard = cls._build_visual_description_cn(components)
        
        # 2. 参考图模式
        veo_prompt_reference = cls._build_veo_prompt_with_reference(components)
        visual_description_reference = cls._build_visual_description_cn_with_reference(components)
        
        # 3. 首尾帧模式
        veo_prompt_frames = cls._build_veo_prompt_with_frames(components)
        visual_description_frames = cls._build_visual_description_cn_with_frames(components)
        
        # 构建角色参考图 Prompt
        image_prompt = cls._build_image_prompt(components)
        
        # 🔥 构建图片生成提示词（用于外部AI绘图软件）
        scene_image_prompt = cls._build_scene_image_prompt(components)
        character_image_prompt = cls._build_character_image_prompt(components)
        first_frame_prompt = cls._build_first_frame_prompt(components)
        last_frame_prompt = cls._build_last_frame_prompt(components)
        
        # 图片提示词中文描述
        scene_image_cn = cls._build_scene_image_prompt_cn(components)
        character_image_cn = cls._build_character_image_prompt_cn(components)
        first_frame_cn = cls._build_first_frame_prompt_cn(components)
        last_frame_cn = cls._build_last_frame_prompt_cn(components)
        
        # 负面提示词
        negative_prompt = cls._build_negative_prompt()
        
        return {
            # 🔥 三种模式的英文提示词（视频生成时根据用户选择使用）
            "veo_prompt_standard": veo_prompt_standard,
            "veo_prompt_reference": veo_prompt_reference,
            "veo_prompt_frames": veo_prompt_frames,
            # 🔥 三种模式的中文描述（UI展示时根据用户选择显示）
            "visual_description_standard": visual_description_standard,
            "visual_description_reference": visual_description_reference,
            "visual_description_frames": visual_description_frames,
            # 🔥 图片生成提示词（用于Midjourney/SD等）
            "image_prompts": {
                "scene": scene_image_prompt,
                "character": character_image_prompt,
                "first_frame": first_frame_prompt,
                "last_frame": last_frame_prompt
            },
            "image_prompts_cn": {
                "scene": scene_image_cn,
                "character": character_image_cn,
                "first_frame": first_frame_cn,
                "last_frame": last_frame_cn
            },
            # 其他数据
            "image_prompt": image_prompt,
            "negative_prompt": negative_prompt,
            "metadata": components,
            "original": {
                "title_cn": scene_title_cn,
                "title_en": scene_title_en,
                "story_beat": story_beat_cn
            }
        }
    
    @classmethod
    def _extract_subject(cls, title: str, story_beat: str, characters: List[Dict] = None) -> Dict:
        """提取主体信息"""
        # 默认主体
        subject = {
            "type": "character",
            "description": "young asian person",
            "count": 1
        }
        
        # 从标题和描述中提取角色名
        character_names = []
        if characters:
            for char in characters:
                name = char.get('name', '')
                if name and len(name) <= 4:  # 中文名通常1-4字
                    character_names.append(name)
        
        # 常见修仙角色特征映射
        role_keywords = {
            "长老": "elderly taoist master",
            "弟子": "young disciple",
            "掌门": "sect leader",
            "仙子": "female immortal",
            "魔尊": "demon lord",
            "凡人": "commoner",
            "少女": "young woman",
            "少年": "young man"
        }
        
        # 提取服装描述
        clothing_keywords = {
            "白衣": "white flowing robe",
            "青袍": "blue-green taoist robe",
            "红衣": "red battle robe",
            "紫衣": "purple noble robe",
            "黑衣": "black assassin outfit",
            "素白": "simple white linen robe"
        }
        
        clothing = "traditional chinese robe"
        for cn, en in clothing_keywords.items():
            if cn in title or cn in story_beat:
                clothing = en
                break
        
        subject["clothing"] = clothing
        
        # 提取表情/姿态
        emotion_keywords = {
            "愤怒": "furious expression",
            "绝望": "desperate look",
            "决绝": "determined expression",
            "冷漠": "cold indifferent expression",
            "恭敬": "respectful posture",
            "狂喜": "ecstatic expression",
            "震惊": "shocked expression"
        }
        
        expression = "neutral expression"
        for cn, en in emotion_keywords.items():
            if cn in title or cn in story_beat:
                expression = en
                break
        
        subject["expression"] = expression
        
        return subject
    
    @classmethod
    def _extract_setting(cls, story_beat: str) -> str:
        """提取场景/环境"""
        # 常见修仙场景映射
        setting_map = {
            "洞府": "ancient cultivation cave",
            "大殿": "grand palace hall",
            "药园": "spirit herb garden",
            "悬崖": "cliff edge with mist",
            "密室": "sealed stone chamber",
            "战场": "battlefield ruins",
            "山门": "mountain sect entrance",
            "竹林": "bamboo forest",
            "密室": "hidden chamber",
            "屋顶": "traditional rooftop at night",
            "石室": "stone meditation room",
            "广场": "vast training courtyard"
        }
        
        for cn, en in setting_map.items():
            if cn in story_beat:
                return en
        
        return "traditional chinese interior"  # 默认
    
    @classmethod
    def _extract_action(cls, story_beat: str, dialogues: List[Dict]) -> str:
        """提取动作"""
        # 常见动作映射
        action_map = {
            "跪": "kneeling",
            "站": "standing",
            "坐": "sitting cross-legged",
            "躺": "lying down injured",
            "飞": "levitating",
            "打": "in combat stance",
            "退": "retreating",
            "追": "chasing",
            "吐血": "coughing blood",
            "掐诀": "forming hand seals",
            "疗伤": "healing meditation"
        }
        
        for cn, en in action_map.items():
            if cn in story_beat:
                return en
        
        return "standing still"  # 默认
    
    @classmethod
    def _select_lighting(cls, emotional_arc: str) -> str:
        """根据情绪选择光线"""
        emotion_lower = emotional_arc.lower() if emotional_arc else ""
        
        if any(word in emotion_lower for word in ["绝望", "恐惧", "desper", "fear"]):
            return "dim blue lighting with harsh shadows"
        elif any(word in emotion_lower for word in ["愤怒", "战斗", "anger", "rage"]):
            return "dramatic red rim lighting"
        elif any(word in emotion_lower for word in ["狂喜", "希望", "hope", "ecstasy"]):
            return "warm golden hour lighting"
        elif any(word in emotion_lower for word in ["神秘", "神秘", "mysterious"]):
            return "soft purple ethereal glow"
        elif any(word in emotion_lower for word in ["冷酷", "无情", "cold", "ruthless"]):
            return "high contrast monochrome lighting"
        else:
            return "soft natural lighting"
    
    @classmethod
    def _select_camera_angle(cls, story_beat: str) -> str:
        """选择镜头角度"""
        if "俯视" in story_beat or "俯拍" in story_beat:
            return "overhead shot looking down"
        elif "仰视" in story_beat or "仰拍" in story_beat:
            return "low angle shot looking up"
        elif "特写" in story_beat or "面部" in story_beat:
            return "close-up portrait"
        elif "远景" in story_beat or "全景" in story_beat:
            return "wide establishing shot"
        elif "跟踪" in story_beat or "跟随" in story_beat:
            return "tracking shot"
        else:
            return "medium shot at eye level"
    
    @classmethod
    def _select_cinematic_style(cls, emotional_arc: str) -> str:
        """选择电影风格"""
        return "cinematic, photorealistic, 8k, highly detailed"
    
    @classmethod
    def _extract_mood(cls, emotional_arc: str) -> str:
        """提取氛围"""
        emotion_lower = emotional_arc.lower() if emotional_arc else ""
        
        mood_map = {
            "绝望": "desperate atmosphere",
            "恐惧": "tense suspenseful mood",
            "愤怒": "intense aggressive energy",
            "狂喜": "triumphant powerful aura",
            "神秘": "mysterious ethereal feeling",
            "冷酷": "cold calculating presence"
        }
        
        for cn, en in mood_map.items():
            if cn in emotion_lower:
                return en
        
        return "dramatic atmosphere"
    
    @classmethod
    def _build_veo_prompt(cls, components: Dict) -> str:
        """构建 VeO Prompt (英文 - 用于AI生成)"""
        subject = components["subject"]
        subject_desc = f"{subject.get('description', 'person')} wearing {subject.get('clothing', 'robe')}, {subject.get('expression', 'neutral')}"
        
        parts = [
            subject_desc,
            components["action"],
            f"in {components['setting']}",
            components["lighting"],
            components["camera"],
            components["style"],
            f"{components['mood']}, vertical 9:16 format"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_visual_description_cn(cls, components: Dict) -> str:
        """构建中文视觉描述 (用于前端展示给用户)"""
        # 英文到中文的映射
        clothing_map = {
            "white flowing robe": "飘逸白衣",
            "blue-green taoist robe": "青绿道袍", 
            "red battle robe": "红色战袍",
            "purple noble robe": "紫色华服",
            "black assassin outfit": "黑色劲装",
            "simple white linen robe": "素白长袍",
            "traditional chinese robe": "传统长袍"
        }
        
        setting_map = {
            "ancient cultivation cave": "古朴修炼洞府",
            "grand palace hall": "宏伟宗门大殿",
            "spirit herb garden": "灵药园",
            "cliff edge with mist": "云雾缭绕的悬崖边",
            "sealed stone chamber": "封闭石室",
            "battlefield ruins": "战场废墟",
            "mountain sect entrance": "山门前",
            "bamboo forest": "竹林",
            "hidden chamber": "密室",
            "traditional rooftop at night": "夜色中的屋顶",
            "stone meditation room": "石室静室",
            "vast training courtyard": "演武广场",
            "traditional chinese interior": "中式内景"
        }
        
        action_map = {
            "kneeling": "跪姿",
            "standing": "站立",
            "sitting cross-legged": "盘腿而坐",
            "lying down injured": "负伤倒地",
            "levitating": "悬浮空中",
            "in combat stance": "战斗姿态",
            "retreating": "后退",
            "chasing": "追击",
            "coughing blood": "咳血",
            "forming hand seals": "掐诀施法",
            "healing meditation": "疗伤冥想",
            "standing still": "静立"
        }
        
        expression_map = {
            "furious expression": "怒容满面",
            "desperate look": "神情绝望",
            "determined expression": "神色决然",
            "cold indifferent expression": "冷漠无情",
            "respectful posture": "恭敬姿态",
            "ecstatic expression": "狂喜神情",
            "shocked expression": "震惊神色",
            "weak but stubborn": "虚弱却倔强",
            "neutral expression": "神色平静"
        }
        
        camera_map = {
            "overhead shot looking down": "俯视镜头",
            "low angle shot looking up": "仰视镜头",
            "close-up portrait": "特写镜头",
            "wide establishing shot": "全景镜头",
            "tracking shot": "跟踪镜头",
            "medium shot at eye level": "中景平拍"
        }
        
        lighting_map = {
            "dim blue lighting with harsh shadows": "幽蓝冷光，阴影锐利",
            "dramatic red rim lighting": "戏剧性红色轮廓光",
            "warm golden hour lighting": "温暖金色夕阳光",
            "soft purple ethereal glow": "柔和紫色空灵光晕",
            "high contrast monochrome lighting": "高对比度单色光",
            "soft natural lighting": "柔和自然光"
        }
        
        subject = components["subject"]
        clothing = clothing_map.get(subject.get('clothing', ''), subject.get('clothing', '传统长袍'))
        expression = expression_map.get(subject.get('expression', ''), subject.get('expression', '神色平静'))
        
        parts = [
            f"人物：身着{clothing}，{expression}",
            f"动作：{action_map.get(components['action'], components['action'])}",
            f"场景：{setting_map.get(components['setting'], components['setting'])}",
            f"光线：{lighting_map.get(components['lighting'], components['lighting'])}",
            f"镜头：{camera_map.get(components['camera'], components['camera'])}",
            "画质：电影级，8K超清",
            f"氛围：{components['mood']}"
        ]
        
        return "；".join(parts)
    
    @classmethod
    def _build_image_prompt(cls, components: Dict) -> str:
        """构建角色参考图 Prompt"""
        subject = components["subject"]
        
        return f"{subject.get('description', 'asian person')}, {subject.get('clothing', 'traditional chinese robe')}, {subject.get('expression', 'neutral')}, character portrait, detailed face, {components['lighting']}, photorealistic, 8k"
    
    @classmethod
    def _build_negative_prompt(cls) -> str:
        """构建负面提示词"""
        return "blurry, low quality, distorted face, extra limbs, bad anatomy, watermark, text, cartoon, anime, painting, illustration"
    
    # ==================== 图片生成提示词构建 ====================
    
    @classmethod
    def _build_scene_image_prompt(cls, components: Dict) -> str:
        """
        构建场景图/背景图生成提示词（用于生成环境参考图）
        
        用途：
        - 作为视频生成的场景参考
        - 作为首帧/尾帧的背景层
        """
        parts = [
            "cinematic scene background",
            components["setting"],
            components["lighting"],
            components["style"],
            "highly detailed environment",
            "8k resolution",
            "no people",
            "no characters",
            "empty scene",
            "masterpiece",
            "best quality"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_character_image_prompt(cls, components: Dict) -> str:
        """
        构建角色图生成提示词（用于生成人物参考图）
        
        用途：
        - 作为视频生成的角色形象参考
        - 保持角色一致性
        """
        subject = components["subject"]
        
        parts = [
            "cinematic character portrait",
            subject.get("description", "young asian person"),
            subject.get("clothing", "traditional robe"),
            subject.get("expression", "neutral expression"),
            components["lighting"],
            components["style"],
            "highly detailed face",
            "8k resolution",
            "character reference",
            "masterpiece",
            "best quality",
            "upper body"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_first_frame_prompt(cls, components: Dict) -> str:
        """
        构建首帧图生成提示词（用于视频首帧）
        
        特点：
        - 完整构图（角色+场景）
        - 静态画面，适合作为视频起点
        """
        subject = components["subject"]
        
        parts = [
            "cinematic film frame",
            "movie screenshot",
            components["camera"],
            subject.get("description", "young asian person"),
            subject.get("clothing", "traditional robe"),
            f"in {components['setting']}",
            components["lighting"],
            components["style"],
            components["mood"],
            "still image",
            "frozen moment",
            "8k resolution",
            "masterpiece",
            "vertical 9:16 format"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_last_frame_prompt(cls, components: Dict) -> str:
        """
        构建尾帧图生成提示词（用于视频尾帧）
        
        特点：
        - 动作完成后的姿态
        - 可与首帧形成对比，展示变化
        """
        subject = components["subject"]
        
        # 根据动作推断结束姿态
        action_end_map = {
            "kneeling": "rising from kneeling, standing tall",
            "standing up slowly": "fully standing, steady posture",
            "levitating": "levitating in mid-air, hair flowing",
            "forming hand seals": "hands completing seal, energy burst",
            "retreating": "defensive stance, ready to counter",
            "chasing": "reaching forward, almost catching",
            "coughing blood": "wiping blood, determined look",
            "healing meditation": "aura glowing, fully healed"
        }
        
        action_end = action_end_map.get(
            components["action"], 
            f"completing {components['action']}"
        )
        
        parts = [
            "cinematic film frame",
            "movie screenshot",
            components["camera"],
            subject.get("description", "young asian person"),
            subject.get("clothing", "traditional robe"),
            action_end,
            f"in {components['setting']}",
            components["lighting"],
            components["style"],
            components["mood"],
            "action completed",
            "still image",
            "8k resolution",
            "masterpiece",
            "vertical 9:16 format"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_scene_image_prompt_cn(cls, components: Dict) -> str:
        """场景图中文描述"""
        return f"场景背景图：{components['setting']}，{components['lighting']}，无人物，高清8K"
    
    @classmethod
    def _build_character_image_prompt_cn(cls, components: Dict) -> str:
        """角色图中文描述"""
        subject = components["subject"]
        return f"角色形象图：{subject.get('description', '人物')}，{subject.get('clothing', '传统服饰')}，{components['lighting']}"
    
    @classmethod
    def _build_first_frame_prompt_cn(cls, components: Dict) -> str:
        """首帧图中文描述"""
        return f"首帧画面：{components['camera']}，{components['subject'].get('description', '人物')}，{components['setting']}，静态构图"
    
    @classmethod
    def _build_last_frame_prompt_cn(cls, components: Dict) -> str:
        """尾帧图中文描述"""
        return f"尾帧画面：动作完成后的姿态，{components['setting']}，与首帧形成对比"
    
    # ==================== 参考图模式提示词构建 ====================
    
    @classmethod
    def _build_veo_prompt_with_reference(cls, components: Dict) -> str:
        """
        构建带参考图的 VeO Prompt
        
        策略：
        - 弱化角色外貌描述（参考图已提供）
        - 强调动作、姿态变化
        - 强调场景环境和氛围
        - 强调光影效果
        """
        subject = components["subject"]
        
        # 简化角色描述，只保留服装和表情，不描述具体外貌
        subject_desc = f"character in {subject.get('clothing', 'traditional robe')}, {subject.get('expression', 'neutral')}"
        
        parts = [
            "character acting",  # 强调角色表演
            subject_desc,
            components["action"],  # 重点：动作
            f"in {components['setting']}",  # 重点：场景
            components["lighting"],  # 重点：光影
            f"dynamic {components['camera']}",  # 强调动态运镜
            components["style"],
            f"{components['mood']}, vertical 9:16 format, character reference image provided"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_visual_description_cn_with_reference(cls, components: Dict) -> str:
        """构建带参考图的中文视觉描述"""
        subject = components["subject"]
        
        clothing_map = {
            "white flowing robe": "白衣",
            "blue-green taoist robe": "青袍", 
            "red battle robe": "红袍",
            "purple noble robe": "紫袍",
            "black assassin outfit": "黑衣",
            "simple white linen robe": "素衣",
            "traditional chinese robe": "传统服饰"
        }
        
        action_map = {
            "kneeling": "跪姿",
            "standing": "站立",
            "sitting cross-legged": "盘坐",
            "lying down injured": "倒地",
            "levitating": "悬浮",
            "in combat stance": "战斗姿态",
            "retreating": "后退",
            "chasing": "追击",
            "coughing blood": "咳血",
            "forming hand seals": "掐诀",
            "healing meditation": "疗伤",
            "standing still": "静立"
        }
        
        setting_map = {
            "ancient cultivation cave": "修炼洞府",
            "grand palace hall": "宗门大殿",
            "spirit herb garden": "灵药园",
            "cliff edge with mist": "云雾悬崖",
            "sealed stone chamber": "密室",
            "battlefield ruins": "战场",
            "mountain sect entrance": "山门",
            "bamboo forest": "竹林",
            "hidden chamber": "暗室",
            "traditional rooftop at night": "屋顶",
            "stone meditation room": "静室",
            "vast training courtyard": "广场",
            "traditional chinese interior": "内景"
        }
        
        clothing = clothing_map.get(subject.get('clothing', ''), '传统服饰')
        
        parts = [
            f"【参考图角色】身着{clothing}",
            f"【动作】{action_map.get(components['action'], components['action'])}",
            f"【场景】{setting_map.get(components['setting'], components['setting'])}",
            f"【光线】{components['lighting']}",
            "【提示】使用角色参考图，保持人物一致性"
        ]
        
        return "；".join(parts)
    
    # ==================== 首尾帧模式提示词构建 ====================
    
    @classmethod
    def _build_veo_prompt_with_frames(cls, components: Dict) -> str:
        """
        构建首尾帧模式的 VeO Prompt
        
        策略：
        - 描述从首帧到尾帧的中间动态过程
        - 强调动作变化和运动轨迹
        - 强调时间流逝感
        """
        subject = components["subject"]
        
        # 构建动态描述
        action = components["action"]
        mood = components["mood"]
        
        # 根据动作类型添加动态关键词
        dynamic_keywords = {
            "kneeling": "gradually rising from kneeling position",
            "standing": "slight body movement and breathing",
            "levitating": "ascending into the air with flowing motion",
            "in combat stance": "dynamic combat movement and weapon swing",
            "retreating": "stepping back with defensive motion",
            "chasing": "rapid forward movement with motion blur",
            "coughing blood": "collapsing motion with blood splatter effect",
            "forming hand seals": "hand gestures with glowing energy trails"
        }
        
        dynamic_desc = dynamic_keywords.get(action, f"subtle {action} motion")
        
        parts = [
            "smooth video transition",
            "character maintaining consistent appearance",
            dynamic_desc,  # 重点：中间动态
            f"in {components['setting']}",
            components["lighting"],
            f"{components['camera']} with slight movement",
            components["style"],
            f"{mood} transitioning, vertical 9:16 format, first and last frame provided"
        ]
        
        return ", ".join(parts)
    
    @classmethod
    def _build_visual_description_cn_with_frames(cls, components: Dict) -> str:
        """构建首尾帧模式的中文视觉描述"""
        
        action_map = {
            "kneeling": "从跪姿缓缓起身",
            "standing": "静立，呼吸起伏",
            "levitating": "缓缓升空，衣袂飘动",
            "in combat stance": "战斗姿态，武器挥舞",
            "retreating": "后退防御，步伐移动",
            "chasing": "疾速追击，动作模糊",
            "coughing blood": "咳血倒地，动态效果",
            "forming hand seals": "手掐法诀，流光拖尾",
            "sitting cross-legged": "打坐调息，气息流转",
            "healing meditation": "疗伤运气，光芒流转"
        }
        
        action_cn = action_map.get(components['action'], components['action'])
        
        parts = [
            "【模式】首尾帧视频生成",
            f"【中间动态】{action_cn}",
            f"【场景】{components['setting']}",
            f"【光线】{components['lighting']}",
            "【提示】保持人物一致性，平滑过渡"
        ]
        
        return "；".join(parts)


# 便捷函数
def generate_veo_prompts_for_scenes(
    story_beats: Dict, 
    characters: List[Dict] = None,
    has_reference_image: bool = False,
    has_first_last_frame: bool = False
) -> List[Dict]:
    """
    为故事节拍中的所有场景生成 VeO Prompts（三种模式同时生成）
    
    Args:
        story_beats: 故事节拍数据 {scenes: [...]}
        characters: 角色列表
        has_reference_image: 是否有角色参考图（仅用于UI默认设置）
        has_first_last_frame: 是否使用首尾帧模式（仅用于UI默认设置）
        
    Returns:
        带三种 veo_prompt 的 shots 列表
    """
    scenes = story_beats.get('scenes', [])
    shots = []
    
    for idx, scene in enumerate(scenes, 1):
        # 🔥 同时生成三种提示词模式
        prompt_data = VeOPromptService.generate_prompt(
            scene_title_cn=scene.get('sceneTitleCn', f'场景{idx}'),
            scene_title_en=scene.get('sceneTitleEn', f'Scene {idx}'),
            story_beat_cn=scene.get('storyBeatCn', ''),
            dialogues=scene.get('dialogues', []),
            emotional_arc=scene.get('emotionalArc', ''),
            characters=characters
        )
        
        # 为每个对白创建一个镜头
        dialogues = scene.get('dialogues', [])
        if not dialogues:
            dialogues = [{'speaker': '无', 'lines': ''}]
        
        for dlg_idx, dlg in enumerate(dialogues, 1):
            shots.append({
                'id': f'shot_{idx}_{dlg_idx}',
                'scene_number': idx,
                'shot_number': dlg_idx,
                'scene_title': scene.get('sceneTitleCn', f'场景{idx}'),
                'shot_type': '中景',
                
                # 🔥 三种模式的英文提示词（视频生成时动态选择）
                'veo_prompt_standard': prompt_data['veo_prompt_standard'],
                'veo_prompt_reference': prompt_data['veo_prompt_reference'],
                'veo_prompt_frames': prompt_data['veo_prompt_frames'],
                
                # 🔥 三种模式的中文描述（UI展示时动态切换）
                'visual_description_standard': prompt_data['visual_description_standard'],
                'visual_description_reference': prompt_data['visual_description_reference'],
                'visual_description_frames': prompt_data['visual_description_frames'],
                
                # 默认使用哪种模式（基于用户在UI的选择）
                'preferred_mode': 'reference' if has_reference_image else ('frames' if has_first_last_frame else 'standard'),
                
                # 完整的视觉元素数据
                'visual_elements': {
                    '人物': prompt_data['metadata']['subject'],
                    '动作': prompt_data['metadata']['action'],
                    '场景': prompt_data['metadata']['setting'],
                    '光线': prompt_data['metadata']['lighting'],
                    '镜头': prompt_data['metadata']['camera'],
                    '情绪': prompt_data['metadata']['mood']
                },
                'image_prompt': prompt_data['image_prompt'],
                'negative_prompt': prompt_data['negative_prompt'],
                
                # 🔥 图片生成提示词（用于Midjourney/SD等外部软件）
                'image_prompts': prompt_data.get('image_prompts', {}),
                'image_prompts_cn': prompt_data.get('image_prompts_cn', {}),
                
                'dialogue': {
                    'speaker': dlg.get('speaker', '无'),
                    'lines': dlg.get('linesCn', dlg.get('lines', '')),
                    'lines_en': dlg.get('linesEn', ''),
                    'tone': dlg.get('toneCn', '')
                },
                'duration': scene.get('durationSeconds', 8),
                'emotional_arc': scene.get('emotionalArc', ''),
                'status': 'pending'
            })
    
    return shots
