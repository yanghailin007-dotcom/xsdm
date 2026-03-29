# -*- coding: utf-8 -*-
"""
情绪曲线生成器
基于AI分析，为每本书生成个性化的情绪曲线
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmotionBeat:
    """情绪节拍"""
    ch: int
    emotion: str
    intensity: int
    beat_type: str
    event: str  # 关键事件
    purpose: str  # 这章的作用


class EmotionCurveGenerator:
    """
    情绪曲线生成器
    调用AI，基于题材和套路生成个性化的情绪曲线
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def generate_curve(self, genre: str, tropes: Dict, plan: Dict, 
                       total_chapters: int) -> List[EmotionBeat]:
        """
        生成情绪曲线
        
        Args:
            genre: 题材
            tropes: 套路分析
            plan: 方案
            total_chapters: 总章节数
            
        Returns:
            情绪节拍列表
        """
        logger.info(f"[EmotionCurveGenerator] 开始生成情绪曲线: {genre}, {total_chapters}章")
        
        if not self.api_client:
            logger.warning("APIClient不可用，使用默认模板")
            return self._get_default_curve(total_chapters, genre)
        
        # 构建Prompt
        prompt = self._build_curve_prompt(genre, tropes, plan, total_chapters)
        
        try:
            # 调用AI生成
            response = self.api_client.generate_content_with_retry(
                content_type="emotion_curve_design",
                user_prompt=prompt,
                temperature=0.7,
                purpose=f"生成{genre}情绪曲线"
            )
            
            if response:
                # 解析情绪曲线
                curve = self._parse_curve_response(response, total_chapters)
                logger.info(f"成功生成情绪曲线: {len(curve)}个节拍")
                return curve
            else:
                logger.warning("AI返回空，使用默认模板")
                return self._get_default_curve(total_chapters, genre)
                
        except Exception as e:
            logger.error(f"生成情绪曲线失败: {e}")
            return self._get_default_curve(total_chapters, genre)
    
    def _build_curve_prompt(self, genre: str, tropes: Dict, plan: Dict, 
                           total_chapters: int) -> str:
        """构建情绪曲线生成Prompt"""
        
        # 提取关键信息
        core_formula = tropes.get('core_formula', '未知套路')
        pacing = tropes.get('pacing', {})
        protagonist = plan.get('protagonist', {})
        
        return f"""【任务】
为一部{genre}小说设计情绪曲线（心电图模式）。

【输入信息】
题材：{genre}
核心套路：{core_formula}
总章节数：{total_chapters}章
主角：{protagonist.get('name', '主角')}，{protagonist.get('initial_identity', '普通人')}

【关键节拍要求】
基于套路分析，以下章节必须有特定情绪：
- 第1章：必须是"压抑→震惊"（绝望开局+系统觉醒）
- 第3章左右：必须有"爽快"（第一次打脸）
- 第8-10章：必须有"震惊"（身份小曝光）
- 第15章左右：必须有"大爽快"（第一次大高潮）
- 第30章：必须有"满足→期待"（阶段总结+新目标）

【情绪类型】
可选：压抑、紧张、希望、好奇、期待、爽快、震惊、满足

【节拍类型】
- 钩子：章尾悬念，必须看下一章
- 爽点：打脸/收获/升级
- 震惊：身份曝光/大场面
- 转折：剧情反转
- 铺垫：为爽点做准备（强度不能太低）

【设计原则】
1. 像心电图一样起伏，不能平
2. 不能连续3章强度低于6
3. 每3-5章必须有一个爽点或震惊
4. 大高潮(9)后必须有1章缓冲(5-6)
5. 章章有钩子或爽点或期待

【输出格式】
返回JSON数组，每个元素是一个节拍：
{{
  "curve": [
    {{"ch": 1, "emotion": "压抑", "intensity": 9, "beat_type": "钩子", "event": "被羞辱，负债百万", "purpose": "绝望开局，让读者代入"}},
    {{"ch": 2, "emotion": "希望", "intensity": 6, "beat_type": "转折", "event": "系统觉醒", "purpose": "点燃希望"}},
    {{"ch": 3, "emotion": "爽快", "intensity": 6, "beat_type": "爽点", "event": "第一次花钱打脸", "purpose": "初步验证系统"}},
    ...
  ]
}}

注意：
- 必须覆盖全部{total_chapters}章
- intensity范围1-10
- 根据题材特点个性化设计
- 不要套用固定模板"""
    
    def _parse_curve_response(self, response, total_chapters: int) -> List[EmotionBeat]:
        """解析AI返回的情绪曲线"""
        beats = []
        
        if isinstance(response, dict):
            curve_data = response.get('curve', [])
        elif isinstance(response, str):
            try:
                import json
                data = json.loads(response)
                curve_data = data.get('curve', [])
            except:
                logger.warning("无法解析JSON响应")
                return self._get_default_curve(total_chapters, "默认")
        else:
            return self._get_default_curve(total_chapters, "默认")
        
        for item in curve_data:
            try:
                beat = EmotionBeat(
                    ch=int(item.get('ch', 0)),
                    emotion=item.get('emotion', '期待'),
                    intensity=int(item.get('intensity', 5)),
                    beat_type=item.get('beat_type', '推进'),
                    event=item.get('event', ''),
                    purpose=item.get('purpose', '')
                )
                beats.append(beat)
            except Exception as e:
                logger.warning(f"解析节拍失败: {e}")
                continue
        
        # 排序并填充缺失
        beats.sort(key=lambda x: x.ch)
        beats = self._fill_missing_chapters(beats, total_chapters)
        
        # 验证规则
        self._validate_curve(beats)
        
        return beats
    
    def _fill_missing_chapters(self, beats: List[EmotionBeat], 
                               total_chapters: int) -> List[EmotionBeat]:
        """填充缺失的章节"""
        existing_chs = {b.ch for b in beats}
        
        for ch in range(1, total_chapters + 1):
            if ch not in existing_chs:
                # 找到前后章节插值
                prev = self._find_prev(beats, ch)
                next_b = self._find_next(beats, ch)
                
                if prev and next_b:
                    # 中间章节：取平均
                    intensity = (prev.intensity + next_b.intensity) // 2
                    emotion = "期待" if intensity < 7 else "爽快"
                elif prev:
                    # 后面没有：延续
                    intensity = max(4, prev.intensity - 1)
                    emotion = "期待"
                else:
                    intensity = 5
                    emotion = "期待"
                
                beats.append(EmotionBeat(
                    ch=ch,
                    emotion=emotion,
                    intensity=intensity,
                    beat_type="推进",
                    event="",
                    purpose="剧情推进"
                ))
        
        beats.sort(key=lambda x: x.ch)
        return beats
    
    def _find_prev(self, beats: List[EmotionBeat], ch: int) -> Optional[EmotionBeat]:
        """找到前一个节拍"""
        for b in reversed(beats):
            if b.ch < ch:
                return b
        return None
    
    def _find_next(self, beats: List[EmotionBeat], ch: int) -> Optional[EmotionBeat]:
        """找到后一个节拍"""
        for b in beats:
            if b.ch > ch:
                return b
        return None
    
    def _validate_curve(self, beats: List[EmotionBeat]):
        """验证情绪曲线是否符合规则"""
        # 检查连续低强度
        for i in range(len(beats) - 2):
            if beats[i].intensity < 6 and beats[i+1].intensity < 6 and beats[i+2].intensity < 6:
                logger.warning(f"警告：第{beats[i].ch}-{beats[i+2].ch}章连续低强度")
        
        # 检查第1章
        if beats and beats[0].ch == 1:
            if beats[0].intensity < 8:
                logger.warning("第1章强度偏低，建议加强")
        
        logger.info(f"情绪曲线验证完成: {len(beats)}章")
    
    def _get_default_curve(self, total_chapters: int, genre: str) -> List[EmotionBeat]:
        """获取默认情绪曲线（备用）"""
        logger.info(f"使用默认情绪曲线: {genre}, {total_chapters}章")
        
        beats = []
        
        # 前30章使用固定模板
        template = [
            (1, "压抑", 9, "钩子", "被羞辱，绝望开局"),
            (2, "希望", 6, "转折", "系统觉醒"),
            (3, "爽快", 6, "爽点", "第一次打脸"),
            (4, "期待", 5, "钩子", "新目标"),
            (5, "爽快", 7, "爽点", "大打脸"),
            (6, "期待", 5, "铺垫", "新场景"),
            (7, "好奇", 4, "钩子", "神秘人物"),
            (8, "爽快", 7, "爽点", "中级打脸"),
            (9, "震惊", 8, "震惊", "身份曝光"),
            (10, "期待", 6, "钩子", "大场面预告"),
            (11, "紧张", 7, "铺垫", "大场面开启"),
            (12, "爽快", 7, "推进", "一路装逼"),
            (13, "爽快", 8, "爽点", "连续打脸"),
            (14, "震惊", 8, "震惊", "全场震惊"),
            (15, "大爽快", 9, "高潮", "阶段性大高潮"),
            (16, "满足", 6, "收获", "享受成果"),
            (17, "期待", 5, "钩子", "更大舞台"),
            (18, "爽快", 7, "爽点", "新圈子打脸"),
            (19, "震惊", 8, "震惊", "新身份曝光"),
            (20, "期待", 6, "钩子", "中期BOSS出现"),
            (21, "压抑", 5, "铺垫", "遇到更强对手"),
            (22, "期待", 6, "推进", "准备反击"),
            (23, "爽快", 7, "爽点", "打脸"),
            (24, "震惊", 8, "震惊", "实力展示"),
            (25, "期待", 6, "钩子", "更大冲突预告"),
            (26, "紧张", 5, "铺垫", "对手反击"),
            (27, "爽快", 7, "爽点", "化解并反击"),
            (28, "爽快", 8, "爽点", "连续打脸"),
            (29, "震惊", 9, "震惊", "震惊全场"),
            (30, "大爽快", 9, "高潮", "中期大高潮"),
        ]
        
        for ch, emotion, intensity, beat_type, event in template:
            if ch <= total_chapters:
                beats.append(EmotionBeat(
                    ch=ch, emotion=emotion, intensity=intensity,
                    beat_type=beat_type, event=event,
                    purpose="默认模板"
                ))
        
        # 填充剩余章节
        beats = self._fill_missing_chapters(beats, total_chapters)
        
        return beats
    
    def save_curve(self, curve: List[EmotionBeat], novel_title: str, 
                   base_path: str = "小说项目"):
        """保存情绪曲线"""
        path = Path(base_path) / novel_title / "emotion_curve_ai.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "generated_by": "AI",
            "timestamp": datetime.now().isoformat(),
            "curve": [
                {
                    "ch": b.ch,
                    "emotion": b.emotion,
                    "intensity": b.intensity,
                    "beat_type": b.beat_type,
                    "event": b.event,
                    "purpose": b.purpose
                }
                for b in curve
            ]
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"情绪曲线已保存: {path}")


# 便捷函数
def generate_emotion_curve_for_novel(api_client, genre: str, tropes: Dict, 
                                     plan: Dict, total_chapters: int,
                                     novel_title: str) -> List[EmotionBeat]:
    """为小说生成情绪曲线并保存"""
    generator = EmotionCurveGenerator(api_client)
    curve = generator.generate_curve(genre, tropes, plan, total_chapters)
    generator.save_curve(curve, novel_title)
    return curve
