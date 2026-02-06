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
        生成 VeO 优化的提示词
        
        Returns:
            {
                "veo_prompt": "英文画面描述 (用于视频生成)",
                "image_prompt": "英文图片描述 (用于角色参考图生成)",
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
        
        # 构建 VeO Prompt (英文，简洁，视觉化 - 用于AI生成)
        veo_prompt = cls._build_veo_prompt(components)
        
        # 构建中文视觉描述 (用于前端展示给用户)
        visual_description_cn = cls._build_visual_description_cn(components)
        
        # 构建角色参考图 Prompt
        image_prompt = cls._build_image_prompt(components)
        
        # 负面提示词
        negative_prompt = cls._build_negative_prompt()
        
        return {
            "veo_prompt": veo_prompt,  # 英文 - 传递给AI
            "visual_description_cn": visual_description_cn,  # 中文 - 展示给用户
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


# 便捷函数
def generate_veo_prompts_for_scenes(story_beats: Dict, characters: List[Dict] = None) -> List[Dict]:
    """
    为故事节拍中的所有场景生成 VeO Prompts
    
    Args:
        story_beats: 故事节拍数据 {scenes: [...]}
        characters: 角色列表
        
    Returns:
        带 veo_prompt 的 shots 列表
    """
    scenes = story_beats.get('scenes', [])
    shots = []
    
    for idx, scene in enumerate(scenes, 1):
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
                # 英文 - 传递给AI视频生成
                'veo_prompt': prompt_data['veo_prompt'],
                # 中文 - 展示给用户看
                'visual_description': prompt_data['visual_description_cn'],
                # 详细的视觉元素（中文）
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
