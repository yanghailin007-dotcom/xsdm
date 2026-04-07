"""
风格注入器
将风格特征转换为Prompt写作指令
"""

from typing import List, Dict

from .database import StyleProfile, StyleFingerprint


class StyleInjector:
    """风格注入器"""
    
    # 句式指令模板
    SENTENCE_TEMPLATES = {
        'short_heavy': {
            'threshold': 0.5,
            'instruction': """
【句式要求 - 短句为主】
- 短句（<10字）占比约50%，营造快节奏感
- 频繁使用破碎句制造停顿和冲击："他愣住了。" "不可能！"
- 避免连续两个以上长句（>40字）
- 关键情绪点必须用短句收尾
"""
        },
        'balanced': {
            'threshold': 0.3,
            'instruction': """
【句式要求 - 长短交错】
- 短句占比约30%，长句占比约20%，中间长度占50%
- 长短句交替使用，形成节奏变化
- 描写场景可用长句，对话动作用短句
- 每3-5句变换一次句长
"""
        },
        'long_heavy': {
            'threshold': 0.1,
            'instruction': """
【句式要求 - 长句为主】
- 允许使用复杂长句进行细腻描写
- 句子间逻辑紧密，层层递进
- 适当使用从句和修饰语营造氛围
- 对话也可使用完整长句
"""
        }
    }
    
    # 对话指令模板
    DIALOGUE_TEMPLATES = {
        'high': {
            'threshold': 0.4,
            'instruction': """
【对话要求 - 高对话占比】
- 对话占比40%以上，推动情节主要靠对话
- 对话要口语化、生活化，避免书面语
- 多使用语气词：啊、呢、吧、嘛
- 对话中穿插动作和表情，不要干巴巴对话
- 适当使用方言和网络用语增强真实感
"""
        },
        'medium': {
            'threshold': 0.25,
            'instruction': """
【对话要求 - 平衡型】
- 对话占比25-30%，叙述与对话并重
- 对话自然流畅，符合人物身份
- 重要信息通过对话传达，背景用叙述
"""
        },
        'low': {
            'threshold': 0.0,
            'instruction': """
【对话要求 - 低对话占比】
- 对话占比<20%，以叙述和心理描写为主
- 对话精炼，每句都有信息量
- 多用叙述和心理活动推动情节
"""
        }
    }
    
    # 感官描写指令
    SENSORY_TEMPLATES = {
        'high': {
            'threshold': 0.04,
            'instruction': """
【感官描写要求 - 高密度】
- 每200字至少包含1处感官描写
- 视觉、听觉、触觉、嗅觉、味觉都要涉及
- 描写要具体：不是"很香"而是"红烧肉混着八角桂皮的香气"
- 通过感官细节营造氛围和代入感
"""
        },
        'medium': {
            'threshold': 0.02,
            'instruction': """
【感官描写要求 - 适中】
- 重要场景必须有感官描写
- 以视觉为主，适当加入听觉和触觉
- 用感官细节增强关键情节的感染力
"""
        }
    }
    
    def generate_prompt(self, profile: StyleProfile) -> str:
        """
        生成风格Prompt指令
        
        Args:
            profile: 风格档案
            
        Returns:
            完整的风格写作指令
        """
        fp = profile.fingerprint
        sections = []
        
        # 1. 风格概述
        sections.append(self._generate_overview(profile))
        
        # 2. 句式指令
        sections.append(self._generate_sentence_instruction(fp))
        
        # 3. 对话指令
        sections.append(self._generate_dialogue_instruction(fp))
        
        # 4. 感官指令
        sections.append(self._generate_sensory_instruction(fp))
        
        # 5. 节奏指令
        sections.append(self._generate_rhythm_instruction(fp))
        
        # 6. 词汇偏好
        sections.append(self._generate_vocabulary_instruction(fp))
        
        # 7. 情感表达
        sections.append(self._generate_emotion_instruction(fp))
        
        # 8. 示例（如果有）
        if profile.key_features:
            sections.append(self._generate_examples(profile))
        
        return '\n\n'.join(sections)
    
    def generate_mixed_prompt(self, profiles: List[StyleProfile], weights: List[float]) -> str:
        """
        生成混合风格的Prompt
        
        例如：70%热血 + 30%幽默
        """
        if len(profiles) != len(weights):
            raise ValueError("profiles和weights长度必须相同")
        
        if len(profiles) == 1:
            return self.generate_prompt(profiles[0])
        
        sections = []
        
        # 混合概述
        mix_desc = ' + '.join([f"{p.title}({w*100:.0f}%)" for p, w in zip(profiles, weights)])
        sections.append(f"【混合风格】{mix_desc}")
        sections.append("请融合以下风格特点进行创作：\n")
        
        # 每个风格的简要指令
        for i, (profile, weight) in enumerate(zip(profiles, weights)):
            if weight < 0.1:  # 权重太小的跳过
                continue
            
            sections.append(f"--- 风格{i+1}: {profile.title} ({weight*100:.0f}%) ---")
            sections.append(self._generate_brief_instruction(profile))
        
        # 混合规则
        sections.append(self._generate_mix_rules(profiles, weights))
        
        return '\n\n'.join(sections)
    
    def _generate_overview(self, profile: StyleProfile) -> str:
        """生成风格概述"""
        lines = [f"【文风设定】{profile.title}风格"]
        
        if profile.description:
            lines.append(f"风格描述：{profile.description}")
        
        if profile.genre:
            lines.append(f"题材：{profile.genre}")
        
        if profile.tone_tags:
            lines.append(f"腔调：{', '.join(profile.tone_tags)}")
        
        if profile.pace:
            lines.append(f"节奏：{profile.pace}")
        
        return '\n'.join(lines)
    
    def _generate_sentence_instruction(self, fp: StyleFingerprint) -> str:
        """生成句式指令"""
        short_ratio = fp.short_sentence_ratio
        
        if short_ratio >= self.SENTENCE_TEMPLATES['short_heavy']['threshold']:
            return self.SENTENCE_TEMPLATES['short_heavy']['instruction']
        elif short_ratio >= self.SENTENCE_TEMPLATES['balanced']['threshold']:
            return self.SENTENCE_TEMPLATES['balanced']['instruction']
        else:
            return self.SENTENCE_TEMPLATES['long_heavy']['instruction']
    
    def _generate_dialogue_instruction(self, fp: StyleFingerprint) -> str:
        """生成对话指令"""
        dialogue_ratio = fp.dialogue_ratio
        
        if dialogue_ratio >= self.DIALOGUE_TEMPLATES['high']['threshold']:
            return self.DIALOGUE_TEMPLATES['high']['instruction']
        elif dialogue_ratio >= self.DIALOGUE_TEMPLATES['medium']['threshold']:
            return self.DIALOGUE_TEMPLATES['medium']['instruction']
        else:
            return self.DIALOGUE_TEMPLATES['low']['instruction']
    
    def _generate_sensory_instruction(self, fp: StyleFingerprint) -> str:
        """生成感官指令"""
        sensory = fp.sensory_density
        
        if sensory >= self.SENSORY_TEMPLATES['high']['threshold']:
            return self.SENSORY_TEMPLATES['high']['instruction']
        else:
            return self.SENSORY_TEMPLATES['medium']['instruction']
    
    def _generate_rhythm_instruction(self, fp: StyleFingerprint) -> str:
        """生成节奏指令"""
        lines = ["【节奏控制】"]
        
        # 过渡词使用
        if fp.transition_word_ratio < 0.01:
            lines.append("- 减少过渡词使用，多用硬切制造节奏感")
        
        # 硬切比例
        if fp.hard_cut_ratio > 0.3:
            lines.append("- 场景切换要干脆，不要过多铺垫")
        
        # 破碎句
        if fp.fragment_ratio > 0.15:
            lines.append("- 大量使用破碎句制造冲击和停顿")
        
        # 感叹句
        if fp.exclamation_ratio > 0.15:
            lines.append("- 频繁使用感叹句增强情绪")
        
        return '\n'.join(lines)
    
    def _generate_vocabulary_instruction(self, fp: StyleFingerprint) -> str:
        """生成词汇指令"""
        lines = ["【词汇偏好】"]
        
        if fp.colloquialism_density > 0.03:
            lines.append("- 使用口语化词汇和网络用语")
        
        if fp.filler_word_density > 0.02:
            lines.append("- 对话中多使用语气词：啊、呢、吧、嘛")
        
        if fp.unique_word_ratio > 0.4:
            lines.append("- 词汇丰富多样，避免重复")
        
        if fp.showing_ratio > 0.7:
            lines.append("- 用动作和环境展示情绪，少用直接陈述")
        
        return '\n'.join(lines) if len(lines) > 1 else ""
    
    def _generate_emotion_instruction(self, fp: StyleFingerprint) -> str:
        """生成情感表达指令"""
        lines = ["【情感表达】"]
        
        if fp.emotion_word_density > 0.02:
            lines.append("- 情绪表达直接强烈")
        else:
            lines.append("- 情绪内敛，多用暗示")
        
        return '\n'.join(lines)
    
    def _generate_examples(self, profile: StyleProfile) -> str:
        """生成示例"""
        if not profile.key_features:
            return ""
        
        lines = ["【风格特征关键词】"]
        lines.extend([f"- {feat}" for feat in profile.key_features[:5]])
        
        return '\n'.join(lines)
    
    def _generate_brief_instruction(self, profile: StyleProfile) -> str:
        """生成简要指令（用于混合）"""
        fp = profile.fingerprint
        features = []
        
        if fp.short_sentence_ratio > 0.4:
            features.append("短句多")
        if fp.dialogue_ratio > 0.35:
            features.append("对话密集")
        if fp.sensory_density > 0.04:
            features.append("感官描写丰富")
        if fp.colloquialism_density > 0.03:
            features.append("口语化")
        if fp.fragment_ratio > 0.15:
            features.append("破碎句多")
        
        desc = profile.description or f"{'/'.join(profile.tone_tags)}风格"
        
        return f"{desc} - 特征：{', '.join(features) if features else '详见完整风格档案'}"
    
    def _generate_mix_rules(self, profiles: List[StyleProfile], weights: List[float]) -> str:
        """生成混合规则"""
        lines = ["【混合规则】"]
        lines.append("- 主风格（权重最高）决定整体基调和节奏")
        lines.append("- 次要风格在细节处体现，如对话方式、描写手法")
        lines.append("- 如果风格冲突，以主风格为准")
        lines.append("- 确保混合后的风格统一协调，不生硬拼接")
        
        return '\n'.join(lines)
