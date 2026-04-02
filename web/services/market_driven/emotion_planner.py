# -*- coding: utf-8 -*-
"""
动态情绪规划器
支持：
1. 全书大框架规划（粗粒度）
2. 批次细规划（10章为单位，动态调整）
3. 单章微调（实时偏差补偿）
4. 爆款情绪曲线仿写
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class EmotionPoint:
    """情绪点"""
    ch: int
    emotion: str  # 压抑/期待/爽快/震惊/满足...
    intensity: int  # 1-10
    event_type: str  # 系统觉醒/第一次打脸/大高潮...
    hook_type: Optional[str] = None  # 悬念/期待/震惊
    

@dataclass
class ArcFramework:
    """剧情阶段框架"""
    arc_name: str  # 起/承/转/合
    start_ch: int
    end_ch: int
    emotion_target: str
    major_slaps: List[int]  # 大爽点章节
    arc_goal: str


@dataclass
class ChapterEmotionPlan:
    """单章情绪规划"""
    ch: int
    type: str  # 铺垫/推进/打脸/大高潮/过渡
    target_emotion: str
    intensity: int
    scene: Optional[str] = None
    target_npc: Optional[str] = None
    adjustment_note: Optional[str] = None  # 调整原因
    

@dataclass
class BatchPlan:
    """批次规划（10章）"""
    batch_id: int
    start_ch: int
    end_ch: int
    arc_name: str
    chapter_plans: Dict[int, ChapterEmotionPlan]  # ch -> plan
    transition_note: str  # 与下一批次衔接说明


@dataclass
class EmotionDeviation:
    """情绪偏差记录"""
    ch: int
    expected_emotion: str
    expected_intensity: int
    actual_emotion: str
    actual_intensity: int
    intensity_diff: int
    emotion_mismatch: bool
    adjustment_made: List[Dict]  # 做了哪些调整


class DynamicEmotionPlanner:
    """动态情绪规划器"""
    
    # 预设的情绪曲线模板
    EMOTION_TEMPLATES = {
        "神豪文-花钱返利类": {
            "pattern_name": "神豪文经典节奏",
            "curve": [
                {"ch": 1, "emotion": "压抑→震惊", "intensity": 8, "event": "系统觉醒"},
                {"ch": 2, "emotion": "好奇→期待", "intensity": 6, "event": "初试系统"},
                {"ch": 3, "emotion": "爽快", "intensity": 6, "event": "第一次花钱打脸"},
                {"ch": 5, "emotion": "爽快", "intensity": 7, "event": "第一次大打脸"},
                {"ch": 8, "emotion": "震惊", "intensity": 8, "event": "身份小曝光"},
                {"ch": 10, "emotion": "大爽快", "intensity": 8, "event": "阶段性总结"},
                {"ch": 15, "emotion": "震惊", "intensity": 9, "event": "拍卖会大场面"},
                {"ch": 20, "emotion": "大爽快", "intensity": 9, "event": "身份中曝光"},
                {"ch": 28, "emotion": "震惊", "intensity": 9, "event": "第一阶段高潮"},
                {"ch": 30, "emotion": "满足→期待", "intensity": 8, "event": "总结+新目标"},
            ],
            "rules": [
                "第1章必须压抑到极点然后系统觉醒",
                "第3章必须第一次打脸（小）",
                "第5章必须第一次大打脸",
                "每10章一个身份升级",
                "每3-5章一个小爽点"
            ]
        },
        "国运文-直播类": {
            "pattern_name": "国运文经典节奏",
            "curve": [
                {"ch": 1, "emotion": "紧张→希望", "intensity": 8, "event": "被选召"},
                {"ch": 2, "emotion": "期待→爽快", "intensity": 7, "event": "首次扮演"},
                {"ch": 3, "emotion": "震惊", "intensity": 8, "event": "全国震惊"},
                {"ch": 5, "emotion": "爽快", "intensity": 7, "event": "首次击杀"},
                {"ch": 8, "emotion": "震惊", "intensity": 8, "event": "具现奖励"},
                {"ch": 10, "emotion": "大爽快", "intensity": 9, "event": "首层禁地BOSS战"},
                {"ch": 15, "emotion": "震惊", "intensity": 9, "event": "全国直播高潮"},
            ],
            "rules": [
                "第1章必须被选召+绑定系统",
                "第2章必须首次展示能力",
                "第3章必须全国震惊",
                "直播弹幕反应必须分层描写",
                "国运具现必须有全国反应"
            ]
        }
    }
    
    def __init__(self, novel_title: str, base_path: str = "小说项目"):
        self.novel_title = novel_title
        self.project_path = Path(base_path) / novel_title
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # 三层数据
        self.master_framework: Optional[Dict] = None  # 全书大框架
        self.current_batch_plan: Optional[BatchPlan] = None  # 当前批次规划
        self.emotion_history: List[EmotionPoint] = []  # 实际情绪历史
        self.deviation_records: List[EmotionDeviation] = []  # 偏差记录
        
        # 加载或初始化
        self._load_or_init()
    
    def _load_or_init(self):
        """加载或初始化"""
        framework_path = self.project_path / "emotion_framework.json"
        if framework_path.exists():
            with open(framework_path, 'r', encoding='utf-8') as f:
                self.master_framework = json.load(f)
            logger.info(f"已加载情绪框架: {self.master_framework.get('total_chapters')}章")
    
    def init_master_framework(self, total_chapters: int, tropes: Dict, 
                              template_key: Optional[str] = None):
        """
        初始化全书大框架
        
        Args:
            total_chapters: 总章节数
            tropes: 套路分析
            template_key: 情绪模板key（如"神豪文-花钱返利类"）
        """
        # 如果使用模板
        if template_key and template_key in self.EMOTION_TEMPLATES:
            template = self.EMOTION_TEMPLATES[template_key]
            self.master_framework = self._scale_template_to_chapters(
                template, total_chapters
            )
        else:
            # 基于套路生成框架
            self.master_framework = self._generate_framework_from_tropes(
                total_chapters, tropes
            )
        
        # 保存
        self._save_framework()
        logger.info(f"已初始化情绪框架: {total_chapters}章")
    
    def _scale_template_to_chapters(self, template: Dict, total_chapters: int) -> Dict:
        """按比例缩放模板到目标章节数"""
        template_curve = template['curve']
        template_max_ch = max(p['ch'] for p in template_curve)
        
        scale_factor = total_chapters / template_max_ch
        
        arcs = []
        arc_definitions = [
            ("起-系统觉醒", 0.1, "压抑→希望→小爽"),
            ("承-快速升级", 0.3, "持续爽快+期待"),
            ("转-大高潮", 0.4, "震惊+满足"),
            ("合-终极之战", 0.2, "终极爽快+圆满")
        ]
        
        current_ch = 1
        for arc_name, ratio, emotion in arc_definitions:
            arc_chapters = int(total_chapters * ratio)
            start_ch = current_ch
            end_ch = min(current_ch + arc_chapters - 1, total_chapters)
            
            # 缩放大爽点位置
            major_slaps = []
            for point in template_curve:
                scaled_ch = int(point['ch'] * scale_factor)
                if start_ch <= scaled_ch <= end_ch and point['intensity'] >= 8:
                    major_slaps.append(scaled_ch)
            
            arcs.append({
                "arc_name": arc_name,
                "start_ch": start_ch,
                "end_ch": end_ch,
                "emotion_target": emotion,
                "major_slaps": sorted(set(major_slaps)),
                "arc_goal": f"{arc_name}阶段目标"
            })
            
            current_ch = end_ch + 1
        
        return {
            "total_chapters": total_chapters,
            "template_source": template['pattern_name'],
            "arcs": arcs,
            "scaled_curve": [
                {
                    "ch": int(p['ch'] * scale_factor),
                    "emotion": p['emotion'],
                    "intensity": p['intensity'],
                    "event": p['event']
                }
                for p in template_curve
            ]
        }
    
    def _generate_framework_from_tropes(self, total_chapters: int, tropes: Dict) -> Dict:
        """基于套路生成框架"""
        # 默认分4个阶段
        arc_ratios = [0.1, 0.3, 0.4, 0.2]
        arc_names = ["起-系统觉醒", "承-快速发展", "转-大高潮", "合-结局"]
        arc_emotions = ["压抑→希望", "爽快+期待", "震惊+满足", "圆满"]
        
        arcs = []
        current_ch = 1
        
        for i, (name, ratio, emotion) in enumerate(zip(arc_names, arc_ratios, arc_emotions)):
            arc_chapters = int(total_chapters * ratio)
            start_ch = current_ch
            end_ch = min(current_ch + arc_chapters - 1, total_chapters)
            
            # 大爽点分布
            major_slaps = []
            if i == 0:  # 起
                major_slaps = [start_ch + 2, end_ch]
            elif i == 1:  # 承
                major_slaps = [start_ch + 5, start_ch + 10, end_ch - 2]
            elif i == 2:  # 转
                major_slaps = [start_ch + 5, start_ch + 15, end_ch - 5]
            else:  # 合
                major_slaps = [end_ch - 5, end_ch]
            
            arcs.append({
                "arc_name": name,
                "start_ch": start_ch,
                "end_ch": end_ch,
                "emotion_target": emotion,
                "major_slaps": [ch for ch in major_slaps if start_ch <= ch <= end_ch],
                "arc_goal": f"{name}阶段目标"
            })
            
            current_ch = end_ch + 1
        
        return {
            "total_chapters": total_chapters,
            "template_source": "基于套路生成",
            "arcs": arcs,
            "scaled_curve": []
        }
    
    def plan_next_batch(self, batch_start: int, batch_size: int = 10) -> BatchPlan:
        """
        规划下一批次
        在批次开始前调用
        """
        if not self.master_framework:
            raise ValueError("主框架未初始化")
        
        batch_end = min(batch_start + batch_size - 1, 
                       self.master_framework['total_chapters'])
        
        # 获取当前阶段
        arc_info = self._get_arc_for_chapter(batch_start)
        
        # 分析前一批次偏差
        deviation_adjustment = self._analyze_previous_batch(batch_start - 1)
        
        # 生成批次规划
        chapter_plans = {}
        for ch in range(batch_start, batch_end + 1):
            plan = self._generate_chapter_plan(ch, arc_info, deviation_adjustment)
            chapter_plans[ch] = plan
        
        # 检查是否需要补偿前一批次的偏差
        if deviation_adjustment:
            self._apply_compensation(chapter_plans, deviation_adjustment)
        
        batch_plan = BatchPlan(
            batch_id=(batch_start - 1) // batch_size + 1,
            start_ch=batch_start,
            end_ch=batch_end,
            arc_name=arc_info['arc_name'],
            chapter_plans=chapter_plans,
            transition_note=f"衔接下一阶段"
        )
        
        self.current_batch_plan = batch_plan
        logger.info(f"已规划批次{batch_plan.batch_id}: {batch_start}-{batch_end}章")
        return batch_plan
    
    def _get_arc_for_chapter(self, ch: int) -> Dict:
        """获取章节所属阶段"""
        for arc in self.master_framework['arcs']:
            if arc['start_ch'] <= ch <= arc['end_ch']:
                return arc
        return self.master_framework['arcs'][-1]  # 默认最后阶段
    
    def _analyze_previous_batch(self, last_ch: int) -> Optional[Dict]:
        """分析前一批次的偏差"""
        if not self.deviation_records:
            return None
        
        # 获取最近一批次的偏差
        recent_deviations = [d for d in self.deviation_records if d.ch > last_ch - 10]
        
        if not recent_deviations:
            return None
        
        # 计算平均偏差
        avg_intensity_diff = sum(d.intensity_diff for d in recent_deviations) / len(recent_deviations)
        
        return {
            "avg_intensity_diff": avg_intensity_diff,
            "count": len(recent_deviations),
            "has_mismatch": any(d.emotion_mismatch for d in recent_deviations)
        }
    
    def _generate_chapter_plan(self, ch: int, arc_info: Dict, 
                               deviation: Optional[Dict]) -> ChapterEmotionPlan:
        """生成单章情绪规划"""
        
        # 基于阶段和是否为爽点章确定基础规划
        if ch in arc_info['major_slaps']:
            base_type = "大高潮" if arc_info['arc_name'] in ["转-大高潮", "合-结局"] else "爽点"
            base_intensity = 8
        elif (ch - 1) % 5 == 0:  # 每5章一个小爽点
            base_type = "打脸"
            base_intensity = 6
        elif (ch - 1) % 3 == 0:  # 每3章一个推进
            base_type = "推进"
            base_intensity = 5
        else:
            base_type = "铺垫"
            base_intensity = 4
        
        # 情绪类型
        emotion_map = {
            "起-系统觉醒": "压抑→希望" if ch == arc_info['start_ch'] else "期待",
            "承-快速发展": "爽快" if base_type in ["打脸", "爽点"] else "期待",
            "转-大高潮": "震惊" if base_type == "大高潮" else "期待",
            "合-结局": "满足" if ch == arc_info['end_ch'] else "期待"
        }
        
        return ChapterEmotionPlan(
            ch=ch,
            type=base_type,
            target_emotion=emotion_map.get(arc_info['arc_name'], "期待"),
            intensity=base_intensity
        )
    
    def _apply_compensation(self, chapter_plans: Dict, deviation: Dict):
        """应用偏差补偿"""
        if deviation['avg_intensity_diff'] < -1.5:
            # 前一批次偏弱，加强本批次前3章
            logger.info(f"前一批次情绪偏弱({deviation['avg_intensity_diff']:.1f})，加强本批次")
            for i, ch in enumerate(sorted(chapter_plans.keys())[:3]):
                plan = chapter_plans[ch]
                plan.intensity = min(10, plan.intensity + 1)
                plan.adjustment_note = f"补偿前批次强度不足"
    
    def record_actual_emotion(self, ch: int, actual: Dict):
        """
        记录实际情绪
        每章生成后调用
        """
        # 获取本章规划
        planned = None
        if self.current_batch_plan and ch in self.current_batch_plan.chapter_plans:
            planned = self.current_batch_plan.chapter_plans[ch]
        
        if planned:
            # 计算偏差
            intensity_diff = actual.get('intensity', 5) - planned.intensity
            emotion_mismatch = actual.get('emotion') != planned.target_emotion
            
            deviation = EmotionDeviation(
                ch=ch,
                expected_emotion=planned.target_emotion,
                expected_intensity=planned.intensity,
                actual_emotion=actual.get('emotion', '未知'),
                actual_intensity=actual.get('intensity', 5),
                intensity_diff=intensity_diff,
                emotion_mismatch=emotion_mismatch,
                adjustment_made=[]
            )
            
            self.deviation_records.append(deviation)
            
            # 如果偏差大，调整后续
            if abs(intensity_diff) >= 2 or emotion_mismatch:
                self._adjust_following_chapters(ch, deviation)
        
        # 记录情绪历史
        self.emotion_history.append(EmotionPoint(
            ch=ch,
            emotion=actual.get('emotion', '未知'),
            intensity=actual.get('intensity', 5),
            event_type=actual.get('event_type', '普通'),
            hook_type=actual.get('hook_type')
        ))
    
    def _adjust_following_chapters(self, ch: int, deviation: EmotionDeviation):
        """调整后续章节规划"""
        if not self.current_batch_plan:
            return
        
        adjustments = []
        
        # 强度偏差补偿
        if deviation.intensity_diff < -2:
            # 本章偏弱，加强下1-2章
            for offset in [1, 2]:
                next_ch = ch + offset
                if next_ch in self.current_batch_plan.chapter_plans:
                    plan = self.current_batch_plan.chapter_plans[next_ch]
                    old_intensity = plan.intensity
                    plan.intensity = min(10, plan.intensity + 1)
                    plan.adjustment_note = f"补偿{ch}章强度不足"
                    adjustments.append({
                        "ch": next_ch,
                        "change": f"强度 {old_intensity}→{plan.intensity}"
                    })
        
        elif deviation.intensity_diff > 2:
            # 本章偏强，下章缓冲
            next_ch = ch + 1
            if next_ch in self.current_batch_plan.chapter_plans:
                plan = self.current_batch_plan.chapter_plans[next_ch]
                if plan.type == "打脸":
                    plan.type = "铺垫"
                    plan.adjustment_note = f"承接{ch}章高强度后的缓冲"
                    adjustments.append({
                        "ch": next_ch,
                        "change": "类型 打脸→铺垫"
                    })
        
        deviation.adjustment_made = adjustments
        if adjustments:
            logger.info(f"已调整后续章节: {[a['ch'] for a in adjustments]}")
    
    def get_chapter_emotion_target(self, ch: int) -> Optional[ChapterEmotionPlan]:
        """获取单章情绪目标"""
        if self.current_batch_plan and ch in self.current_batch_plan.chapter_plans:
            return self.current_batch_plan.chapter_plans[ch]
        return None
    
    def get_emotion_summary(self) -> Dict:
        """获取情绪生成摘要"""
        if not self.emotion_history:
            return {"status": "未开始生成"}
        
        total_chapters = len(self.emotion_history)
        avg_intensity = sum(p.intensity for p in self.emotion_history) / total_chapters
        
        slap_chapters = [p for p in self.emotion_history if p.intensity >= 7]
        
        return {
            "total_generated": total_chapters,
            "average_intensity": round(avg_intensity, 1),
            "high_intensity_chapters": len(slap_chapters),
            "slap_distribution": [p.ch for p in slap_chapters],
            "deviation_count": len(self.deviation_records),
            "avg_deviation": sum(abs(d.intensity_diff) for d in self.deviation_records) / len(self.deviation_records) if self.deviation_records else 0
        }
    
    def _save_framework(self):
        """保存框架"""
        path = self.project_path / "emotion_framework.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.master_framework, f, ensure_ascii=False, indent=2)


# 便捷函数
def create_emotion_planner(novel_title: str, total_chapters: int, 
                           genre: str, tropes: Dict) -> DynamicEmotionPlanner:
    """创建并初始化情绪规划器"""
    planner = DynamicEmotionPlanner(novel_title)
    
    # 映射genre到模板
    template_map = {
        "神豪文-花钱返利类": "神豪文-花钱返利类",
        "神豪文-签到奖励类": "神豪文-花钱返利类",  # 复用
        "国运文-直播类": "国运文-直播类",
        "国运文-禁地探险类": "国运文-直播类"  # 复用
    }
    
    template_key = template_map.get(genre)
    
    planner.init_master_framework(
        total_chapters=total_chapters,
        tropes=tropes,
        template_key=template_key
    )
    
    return planner
