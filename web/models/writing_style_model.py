# -*- coding: utf-8 -*-
"""
文风数据模型
管理写作风格的存储和检索
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

class WritingStyleModel:
    """文风数据模型"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'writing_styles')
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 预设文风存储路径
        self.preset_dir = self.data_dir / 'presets'
        self.preset_dir.mkdir(exist_ok=True)
        
        # 用户文风存储路径
        self.user_dir = self.data_dir / 'user_styles'
        self.user_dir.mkdir(exist_ok=True)
        
        # 初始化预设文风
        self._init_preset_styles()
    
    def _init_preset_styles(self):
        """初始化预设文风"""
        # 番茄轻快节奏风
        fanqie_style = {
            "style_id": "fanqie_light_fast_v1",
            "style_name": "番茄轻快节奏风",
            "style_name_en": "Fanqie Light Fast",
            "description": "轻松幽默、快节奏、适合爽文的写作风格",
            "category": ["urban", "fantasy", "superpower"],
            "is_preset": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "author": "system",
            "usage_count": 0,
            "rating": 4.8,
            
            "dna": {
                "opening": {
                    "type": "ps_interaction",
                    "templates": [
                        "ps：（大脑寄存处！）",
                        "（梦到什么写什么！）",
                        "（本文又名：《{alternative_title}》）"
                    ],
                    "required": True
                },
                "environment": {
                    "pattern": "concise",
                    "max_sentences": 3,
                    "style": "四字短语或短句",
                    "example": ["炎炎夏日，骄阳当空。", "深秋时节，寒风萧瑟。"]
                },
                "character_tagging": {
                    "features_count": 3,
                    "include_action": True,
                    "humor_level": "high",
                    "description": "人物出场带鲜明标签，外貌+动作+特征"
                },
                "dialogue": {
                    "style": "colloquial",
                    "max_length": 20,
                    "slang_enabled": True,
                    "slang_keywords": ["卧槽", "狗带", "牛逼", "绝了", "我日"],
                    "punctuation": "口语化，可用省略号表示停顿"
                },
                "pacing": {
                    "turning_point_every": 300,
                    "climax_every": 500,
                    "paragraph_max_lines": 3,
                    "description": "300字一小转，500字一爽点"
                },
                "humor": {
                    "frequency": "every_500_words",
                    "types": ["contrast", "exaggeration", "life_scene"],
                    "description": "每500字植入幽默梗"
                },
                "sentence_structure": {
                    "primary": "short",
                    "mix_ratio": {"short": 0.7, "medium": 0.25, "long": 0.05},
                    "description": "短句为主，长短结合"
                },
                "narrative_voice": {
                    "type": "first_person",
                    "personality": "casual",
                    "insertions": ["吐槽", "回忆", "即时反应"],
                    "description": "第一人称，带个人记忆和偏好"
                }
            },
            
            "system_prompt_addon": """你是一位擅长轻松爽文风格的网文作者。

【写作要求】
1. 开篇必须包含PS互动段落，风格自嘲幽默
2. 环境描写简洁，3句话内进入剧情
3. 人物出场带2-3个鲜明标签（外貌+动作+特征）
4. 对话使用网络口语，自然不做作
5. 严格遵循300字一转折、500字一爽点的节奏
6. 段落不超过3行，适合手机阅读
7. 每500字植入1个幽默梗，类型可以是反差、夸张或生活梗
8. 第一人称叙述，加入个人记忆和即时反应
9. 情感克制，通过细节让读者感受

【禁用】
- 书面语、长句堆砌、过度描写的环境
- 过于礼貌的对话
- 情感过度外放或解释

【示例风格】
ps：（大脑寄存处！）

炎炎夏日，骄阳当空。

一个身着标配教师制服，带着圆形眼镜的地中海老头站在讲台上...
""",
            
            "example_paragraph": "ps：（大脑寄存处！）\n\n炎炎夏日，骄阳当空。\n\n鸟儿在歌唱，夏蝉在鸣叫，树叶随着微风沙沙作响。\n\n大夏，临疆省，临安市。\n\n临安市市一中高三（1）班。\n\n一个身着标配教师制服，带着圆形眼镜的地中海老头站在讲台上。",
            
            "suitable_genres": ["都市", "异能", "爽文", "轻小说"],
            "suitable_platforms": ["番茄小说", "起点"],
            "word_count_range": {"min": 2000, "max": 3000},
            "chapter_structure": "快节奏，短段落，强冲突"
        }
        
        # 标准流畅风
        standard_style = {
            "style_id": "standard_flow_v1",
            "style_name": "标准流畅风",
            "style_name_en": "Standard Flow",
            "description": "中规中矩、叙事清晰、适用范围广的标准写作风格",
            "category": ["all"],
            "is_preset": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "author": "system",
            "usage_count": 0,
            "rating": 4.5,
            
            "dna": {
                "opening": {
                    "type": "direct",
                    "templates": ["直接进入故事"],
                    "required": False
                },
                "environment": {
                    "pattern": "balanced",
                    "max_sentences": 5,
                    "style": "适中描写",
                    "example": ["深秋的江城带着一丝凉意，梧桐叶随风飘落。"]
                },
                "character_tagging": {
                    "features_count": 2,
                    "include_action": True,
                    "humor_level": "medium",
                    "description": "人物出场有基本描写"
                },
                "dialogue": {
                    "style": "natural",
                    "max_length": 30,
                    "slang_enabled": False,
                    "slang_keywords": [],
                    "punctuation": "规范"
                },
                "pacing": {
                    "turning_point_every": 500,
                    "climax_every": 1000,
                    "paragraph_max_lines": 5,
                    "description": "中等节奏"
                },
                "humor": {
                    "frequency": "optional",
                    "types": ["subtle"],
                    "description": "适度幽默"
                },
                "sentence_structure": {
                    "primary": "medium",
                    "mix_ratio": {"short": 0.3, "medium": 0.5, "long": 0.2},
                    "description": "长短句结合"
                },
                "narrative_voice": {
                    "type": "third_person",
                    "personality": "neutral",
                    "insertions": [],
                    "description": "第三人称客观叙述"
                }
            },
            
            "system_prompt_addon": "你是一位经验丰富的网文作者，擅长标准流畅的叙事风格。写作要求：叙事清晰，逻辑连贯，描写适中，对话自然，节奏平稳。",
            
            "example_paragraph": "深秋的江城带着一丝凉意。\n\n林凡站在教室门口，看着窗外飘落的梧桐叶，心中思绪万千。明天就是觉醒测试了，全校都在紧张准备，而他还不知道自己的命运将会如何。",
            
            "suitable_genres": ["全类型"],
            "suitable_platforms": ["所有平台"],
            "word_count_range": {"min": 2000, "max": 4000},
            "chapter_structure": "标准叙事结构"
        }
        
        # 保存预设文风
        self._save_style(fanqie_style, is_preset=True)
        self._save_style(standard_style, is_preset=True)
    
    def _save_style(self, style_data: Dict, is_preset: bool = False):
        """保存文风"""
        style_id = style_data.get("style_id")
        if not style_id:
            return False
        
        if is_preset:
            file_path = self.preset_dir / f"{style_id}.json"
        else:
            file_path = self.user_dir / f"{style_id}.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(style_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存文风失败: {e}")
            return False
    
    def get_style(self, style_id: str) -> Optional[Dict]:
        """获取文风"""
        # 先查找预设
        file_path = self.preset_dir / f"{style_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 再查找用户文风
        file_path = self.user_dir / f"{style_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    def get_all_presets(self) -> List[Dict]:
        """获取所有预设文风"""
        presets = []
        for file_path in self.preset_dir.glob("*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                presets.append(json.load(f))
        return sorted(presets, key=lambda x: x.get("rating", 0), reverse=True)
    
    def get_all_user_styles(self, user_id: str = None) -> List[Dict]:
        """获取用户文风"""
        styles = []
        for file_path in self.user_dir.glob("*.json"):
            with open(file_path, 'r', encoding='utf-8') as f:
                style = json.load(f)
                if user_id is None or style.get("user_id") == user_id:
                    styles.append(style)
        return sorted(styles, key=lambda x: x.get("updated_at", ""), reverse=True)
    
    def create_user_style(self, style_data: Dict, user_id: str = None) -> str:
        """创建用户文风"""
        import uuid
        style_id = f"user_{uuid.uuid4().hex[:8]}"
        style_data["style_id"] = style_id
        style_data["is_preset"] = False
        style_data["user_id"] = user_id
        style_data["created_at"] = datetime.now().isoformat()
        style_data["updated_at"] = datetime.now().isoformat()
        style_data["usage_count"] = 0
        style_data["rating"] = 0
        
        self._save_style(style_data, is_preset=False)
        return style_id
    
    def update_style(self, style_id: str, updates: Dict) -> bool:
        """更新文风"""
        style = self.get_style(style_id)
        if not style:
            return False
        
        # 不能修改预设文风的核心内容
        if style.get("is_preset"):
            allowed_fields = ["usage_count", "rating"]
            updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        style.update(updates)
        style["updated_at"] = datetime.now().isoformat()
        
        is_preset = style.get("is_preset", False)
        return self._save_style(style, is_preset=is_preset)
    
    def delete_style(self, style_id: str) -> bool:
        """删除文风（只能删除用户文风）"""
        style = self.get_style(style_id)
        if not style or style.get("is_preset"):
            return False
        
        file_path = self.user_dir / f"{style_id}.json"
        try:
            file_path.unlink()
            return True
        except Exception:
            return False
    
    def get_recommended_styles(self, genre: str = None) -> List[Dict]:
        """获取推荐文风"""
        presets = self.get_all_presets()
        
        if genre:
            # 根据题材筛选
            filtered = []
            for style in presets:
                suitable_genres = style.get("suitable_genres", [])
                if genre in suitable_genres or "all" in suitable_genres:
                    filtered.append(style)
            return filtered
        
        return presets
    
    # ========== 用户文风订阅管理 ==========
    
    def _get_user_subscriptions_file(self, user_id: str) -> Path:
        """获取用户订阅文件路径"""
        return self.user_dir / f"subscriptions_{user_id}.json"
    
    def get_user_subscribed_styles(self, user_id: str = None) -> List[str]:
        """获取用户订阅的文风ID列表"""
        if not user_id:
            return []
        
        file_path = self._get_user_subscriptions_file(user_id)
        if not file_path.exists():
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("subscribed_styles", [])
        except Exception:
            return []
    
    def subscribe_style(self, user_id: str, style_id: str) -> bool:
        """订阅文风"""
        if not user_id or not style_id:
            return False
        
        file_path = self._get_user_subscriptions_file(user_id)
        
        # 读取现有订阅
        subscribed = self.get_user_subscribed_styles(user_id)
        
        # 如果已订阅则返回True
        if style_id in subscribed:
            return True
        
        # 添加新订阅
        subscribed.append(style_id)
        
        # 保存
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "user_id": user_id,
                    "subscribed_styles": subscribed,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存订阅失败: {e}")
            return False
    
    def unsubscribe_style(self, user_id: str, style_id: str) -> bool:
        """取消订阅文风"""
        if not user_id or not style_id:
            return False
        
        file_path = self._get_user_subscriptions_file(user_id)
        
        # 读取现有订阅
        subscribed = self.get_user_subscribed_styles(user_id)
        
        # 如果没有订阅则返回True
        if style_id not in subscribed:
            return True
        
        # 移除订阅
        subscribed.remove(style_id)
        
        # 保存
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "user_id": user_id,
                    "subscribed_styles": subscribed,
                    "updated_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存订阅失败: {e}")
            return False
    
    def is_style_subscribed(self, user_id: str, style_id: str) -> bool:
        """检查用户是否已订阅该文风"""
        if not user_id:
            return False
        subscribed = self.get_user_subscribed_styles(user_id)
        return style_id in subscribed


# 全局实例
_style_model = None

def get_writing_style_model() -> WritingStyleModel:
    """获取文风模型实例"""
    global _style_model
    if _style_model is None:
        _style_model = WritingStyleModel()
    return _style_model
