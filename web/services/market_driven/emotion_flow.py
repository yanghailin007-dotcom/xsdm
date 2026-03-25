# -*- coding: utf-8 -*-
"""
情绪流管理器 - 纯情绪曲线，无传统结构

番茄爆款的核心：
- 情绪心电图：持续高低起伏，没有真正的"过渡"
- 每章都有用：要么爽、要么期待、要么钩子
- 节奏：压抑(低)→爽(高)→冷却(中)→更爽(更高)→震惊(顶)→钩子(吊)
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmotionBeat:
    """情绪节拍"""
    ch: int
    emotion: str  # 压抑/期待/爽快/震惊/满足/好奇/紧张...
    intensity: int  # 1-10
    beat_type: str  # 钩子/爽点/收获/震惊/铺垫/反转
    purpose: str  # 这章的作用：制造悬念/打脸/升级/埋下伏笔...
    

class EmotionFlow:
    """
    情绪流 - 像心电图一样的连续情绪曲线
    没有"起承转合"，只有情绪的起伏
    """
    
    # 爆款情绪模板（心电图模式）
    # X轴：章节，Y轴：情绪强度
    TEMPLATES = {
        "神豪文-经典": {
            "name": "神豪文情绪心电图",
            "total_ch": 100,
            # 每一章的情绪定义：[章节, 情绪类型, 强度, 节拍类型, 作用]
            "beats": [
                # 第一波：压抑→小爽（第1-5章）
                [1, "压抑", 9, "钩子", "绝望开局，让读者代入"],
                [2, "希望", 6, "转折", "系统出现，点燃希望"],
                [3, "爽快", 6, "爽点", "第一次花钱打脸"],
                [4, "期待", 5, "钩子", "新目标出现"],
                [5, "爽快", 7, "爽点", "第一次大打脸，身份小提升"],
                
                # 第二波：冷却→更大爽（第6-10章）
                [6, "期待", 5, "铺垫", "新场景引入"],
                [7, "好奇", 4, "钩子", "神秘人物出现"],
                [8, "爽快", 7, "爽点", "中级打脸"],
                [9, "震惊", 8, "震惊", "身份初步暴露"],
                [10, "期待", 6, "钩子", "大场面预告"],
                
                # 第三波：大高潮（第11-15章）
                [11, "紧张", 7, "铺垫", "大场面开启"],
                [12, "爽快", 7, "推进", "一路装逼"],
                [13, "爽快", 8, "爽点", "连续打脸"],
                [14, "震惊", 8, "震惊", "全场震惊"],
                [15, "大爽快", 9, "高潮", "阶段性大高潮"],
                
                # 第四波：升级后的新生活（第16-20章）
                [16, "满足", 6, "收获", "享受成果"],
                [17, "期待", 5, "钩子", "更大舞台开启"],
                [18, "爽快", 7, "爽点", "新圈子打脸"],
                [19, "震惊", 8, "震惊", "新身份曝光"],
                [20, "期待", 6, "钩子", "引出中期BOSS"],
                
                # 中期：循环模式
                # 21-30：重复 铺垫→爽→震惊→钩子的节奏
                # 每5章一个小循环
                [21, "压抑", 5, "铺垫", "遇到更强对手"],
                [22, "期待", 6, "推进", "准备反击"],
                [23, "爽快", 7, "爽点", "打脸"],
                [24, "震惊", 8, "震惊", "实力展示"],
                [25, "期待", 6, "钩子", "更大冲突预告"],
                
                [26, "紧张", 5, "铺垫", "对手反击"],
                [27, "爽快", 7, "爽点", "化解并反击"],
                [28, "爽快", 8, "爽点", "连续打脸"],
                [29, "震惊", 9, "震惊", "震惊全场"],
                [30, "大爽快", 9, "高潮", "中期大高潮"],
                
                # 后续...按此模式循环，但强度递增
            ],
            "rules": [
                "不能连续3章低于强度6（会流失读者）",
                "每5章必须有一个强度≥8的章节",
                "大高潮后必须有1章冷却（强度5-6）",
                "章章有钩子，或爽点，或期待",
                "情绪只能跳跃1-2级，不能压抑直接大爽快"
            ]
        },
        
        "国运文-经典": {
            "name": "国运文情绪心电图",
            "total_ch": 100,
            "beats": [
                [1, "紧张", 8, "钩子", "被选召，全国关注"],
                [2, "期待", 7, "转折", "绑定系统，获得能力"],
                [3, "爽快", 8, "爽点", "首次展示，全国震惊"],
                [4, "期待", 6, "钩子", "新禁地挑战"],
                [5, "爽快", 7, "爽点", "首杀，具现奖励"],
                
                [6, "紧张", 6, "铺垫", "他国选手挑衅"],
                [7, "爽快", 7, "爽点", "反击打脸"],
                [8, "震惊", 8, "震惊", "全球震惊"],
                [9, "期待", 6, "钩子", "BOSS战预告"],
                [10, "大爽快", 9, "高潮", "首层BOSS战"],
                
                # 后续每10章一个大循环
            ],
            "rules": [
                "直播弹幕必须每章都有（分层反应）",
                "国运具现必须有全国反应",
                "每章必须有震惊元素",
                "外国选手必须是反派",
            ]
        }
    }
    
    def __init__(self, novel_title: str, base_path: str = "小说项目"):
        self.novel_title = novel_title
        self.project_path = Path(base_path) / novel_title
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        self.total_chapters = 0
        self.emotion_curve: List[EmotionBeat] = []
        self.actual_emotions: Dict[int, Dict] = {}  # 实际生成的情绪
        
    def init_from_template(self, template_key: str, total_chapters: int):
        """从模板初始化情绪曲线"""
        if template_key not in self.TEMPLATES:
            raise ValueError(f"未知模板: {template_key}")
        
        template = self.TEMPLATES[template_key]
        self.total_chapters = total_chapters
        
        # 获取模板beats
        template_beats = template["beats"]
        template_max_ch = max(b[0] for b in template_beats)
        
        # 按比例缩放
        scale = total_chapters / template_max_ch
        
        self.emotion_curve = []
        used_chapters = set()
        
        for beat in template_beats:
            ch = int(beat[0] * scale)
            if ch < 1:
                ch = 1
            if ch > total_chapters:
                ch = total_chapters
            
            # 避免重复章节
            while ch in used_chapters and ch < total_chapters:
                ch += 1
            
            used_chapters.add(ch)
            
            self.emotion_curve.append(EmotionBeat(
                ch=ch,
                emotion=beat[1],
                intensity=beat[2],
                beat_type=beat[3],
                purpose=beat[4]
            ))
        
        # 填充缺失的章节
        self._fill_missing_chapters(total_chapters)
        
        logger.info(f"已初始化情绪曲线: {total_chapters}章, 模板{template_key}")
        self._save_curve()
    
    def _fill_missing_chapters(self, total_chapters: int):
        """填充模板未定义的章节"""
        existing_chs = {b.ch for b in self.emotion_curve}
        
        for ch in range(1, total_chapters + 1):
            if ch not in existing_chs:
                # 根据前后章节插值
                prev_beat = self._find_prev_beat(ch)
                next_beat = self._find_next_beat(ch)
                
                if prev_beat and next_beat:
                    # 中间章节：过渡
                    self.emotion_curve.append(EmotionBeat(
                        ch=ch,
                        emotion="期待",
                        intensity=5,
                        beat_type="铺垫",
                        purpose="承上启下"
                    ))
                elif prev_beat:
                    # 后面没有定义：延续模式
                    self.emotion_curve.append(EmotionBeat(
                        ch=ch,
                        emotion="期待",
                        intensity=5,
                        beat_type="推进",
                        purpose="推进剧情"
                    ))
                else:
                    # 前面没有：默认
                    self.emotion_curve.append(EmotionBeat(
                        ch=ch,
                        emotion="期待",
                        intensity=5,
                        beat_type="推进",
                        purpose="剧情推进"
                    ))
        
        # 按章节排序
        self.emotion_curve.sort(key=lambda x: x.ch)
    
    def _find_prev_beat(self, ch: int) -> Optional[EmotionBeat]:
        """找到前一章的节拍"""
        for beat in reversed(self.emotion_curve):
            if beat.ch < ch:
                return beat
        return None
    
    def _find_next_beat(self, ch: int) -> Optional[EmotionBeat]:
        """找到后一章的节拍"""
        for beat in self.emotion_curve:
            if beat.ch > ch:
                return beat
        return None
    
    def get_beat(self, ch: int) -> Optional[EmotionBeat]:
        """获取指定章节的节拍"""
        for beat in self.emotion_curve:
            if beat.ch == ch:
                return beat
        return None
    
    def record_actual(self, ch: int, emotion: str, intensity: int, note: str = ""):
        """记录实际生成的情绪"""
        self.actual_emotions[ch] = {
            "emotion": emotion,
            "intensity": intensity,
            "note": note,
            "timestamp": datetime.now().isoformat()
        }
        
        # 检查偏差
        beat = self.get_beat(ch)
        if beat:
            diff = intensity - beat.intensity
            if abs(diff) >= 2:
                logger.warning(f"第{ch}章情绪偏差: 预期{beat.intensity}, 实际{intensity}, 差{diff}")
                self._adjust_next_beats(ch, diff)
    
    def _adjust_next_beats(self, current_ch: int, diff: int):
        """调整后续节拍"""
        # 如果本章偏弱，加强后续1-2章
        # 如果本章偏强，后续适当降低
        adjust_count = 0
        for beat in self.emotion_curve:
            if beat.ch > current_ch and adjust_count < 2:
                old_intensity = beat.intensity
                if diff < 0:  # 偏弱
                    beat.intensity = min(10, beat.intensity + 1)
                else:  # 偏强
                    beat.intensity = max(3, beat.intensity - 1)
                
                if beat.intensity != old_intensity:
                    logger.info(f"调整第{beat.ch}章: 强度 {old_intensity}→{beat.intensity}")
                    adjust_count += 1
    
    def check_continuous_low(self, window: int = 3) -> List[int]:
        """检查是否有连续低强度章节"""
        low_chapters = []
        
        for i in range(len(self.emotion_curve) - window + 1):
            window_beats = self.emotion_curve[i:i+window]
            intensities = [b.intensity for b in window_beats]
            
            if all(i < 6 for i in intensities):
                low_chapters.append(window_beats[0].ch)
                logger.warning(f"警告：第{window_beats[0].ch}-{window_beats[-1].ch}章连续低强度!")
        
        return low_chapters
    
    def get_curve_visualization(self) -> str:
        """获取情绪曲线可视化（文本）"""
        lines = ["情绪心电图:"]
        lines.append("章数 | 情绪    | 强度 | 类型 | 作用")
        lines.append("-" * 50)
        
        for beat in self.emotion_curve[:20]:  # 只显示前20章
            actual = self.actual_emotions.get(beat.ch, {})
            actual_str = f"(实{actual.get('intensity', '-')})" if actual else ""
            lines.append(f"{beat.ch:3d}  | {beat.emotion:8s} | {beat.intensity:2d}   | {beat.beat_type:4s} | {beat.purpose[:20]}{actual_str}")
        
        return "\n".join(lines)
    
    def get_next_n_beats(self, start_ch: int, n: int = 5) -> List[EmotionBeat]:
        """获取接下来N章的节拍"""
        result = []
        for beat in self.emotion_curve:
            if beat.ch >= start_ch and len(result) < n:
                result.append(beat)
        return result
    
    def _save_curve(self):
        """保存情绪曲线"""
        path = self.project_path / "emotion_flow.json"
        data = {
            "total_chapters": self.total_chapters,
            "curve": [
                {
                    "ch": b.ch,
                    "emotion": b.emotion,
                    "intensity": b.intensity,
                    "beat_type": b.beat_type,
                    "purpose": b.purpose
                }
                for b in self.emotion_curve
            ],
            "actual_emotions": self.actual_emotions
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_curve(self):
        """加载情绪曲线"""
        path = self.project_path / "emotion_flow.json"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.total_chapters = data.get("total_chapters", 0)
            self.emotion_curve = [
                EmotionBeat(
                    ch=b["ch"],
                    emotion=b["emotion"],
                    intensity=b["intensity"],
                    beat_type=b["beat_type"],
                    purpose=b["purpose"]
                )
                for b in data.get("curve", [])
            ]
            self.actual_emotions = data.get("actual_emotions", {})
    
    def load_from_phase_one(self, phase_one_products: Dict):
        """
        从一阶段产物加载AI生成的情绪曲线
        优先使用AI生成的个性化曲线
        """
        if "emotion_curve" in phase_one_products:
            curve_data = phase_one_products["emotion_curve"]
            
            self.emotion_curve = []
            for item in curve_data:
                self.emotion_curve.append(EmotionBeat(
                    ch=item.get("ch", 0),
                    emotion=item.get("emotion", "期待"),
                    intensity=item.get("intensity", 5),
                    beat_type=item.get("beat_type", "推进"),
                    purpose=item.get("purpose", "剧情推进")
                ))
            
            if self.emotion_curve:
                self.total_chapters = max(b.ch for b in self.emotion_curve)
                self._save_curve()
                logger.info(f"已从一阶段产物加载AI生成的情绪曲线: {len(self.emotion_curve)}章")
                return True
        
        return False


# 便捷函数
def create_emotion_flow(novel_title: str, genre: str, total_chapters: int,
                       phase_one_products: Optional[Dict] = None) -> EmotionFlow:
    """
    创建情绪流
    
    优先级：
    1. 如果提供了一阶段产物且有emotion_curve，使用AI生成的个性化曲线
    2. 否则使用固定模板
    """
    flow = EmotionFlow(novel_title)
    
    # 优先从一阶段产物加载AI生成的曲线
    if phase_one_products:
        loaded = flow.load_from_phase_one(phase_one_products)
        if loaded:
            return flow
        else:
            logger.info("一阶段产物中没有AI生成的情绪曲线，使用固定模板")
    
    # 使用固定模板
    template_map = {
        "神豪文-花钱返利类": "神豪文-经典",
        "神豪文-签到奖励类": "神豪文-经典",
        "国运文-直播类": "国运文-经典",
        "国运文-禁地探险类": "国运文-经典",
    }
    
    template_key = template_map.get(genre, "神豪文-经典")
    flow.init_from_template(template_key, total_chapters)
    
    return flow
