"""
多类型视频转换适配器 - 支持三种视频模式的统一架构

支持的视频类型：
1. 短片/动画电影（5-30分钟）
2. 长篇剧集（20-40分钟/集）
3. 短视频系列（1-3分钟）

核心设计理念：
- 每种类型有自己的转换策略
- 共享底层的事件解析逻辑
- 统一的输出接口（分镜头脚本）
"""

from typing import Dict, List, Optional, Any, Protocol
from abc import ABC, abstractmethod
import json
import sys
from pathlib import Path

from src.utils.logger import get_logger
from src.managers.EventExtractor import get_event_extractor

# 加载配置
def load_video_config():
    """加载视频生成配置"""
    try:
        from config.config import CONFIG
        return CONFIG.get("video_generation", {})
    except ImportError:
        # 如果无法导入，使用默认值
        return {
            "default_shot_duration": 8.0,
            "shot_duration": {
                "long_series": {
                    "起因": {"avg_duration": 8.0, "shots": 5, "episode_minutes": 0.67},
                    "发展": {"avg_duration": 8.0, "shots": 8, "episode_minutes": 1.07},
                    "高潮": {"avg_duration": 8.0, "shots": 15, "episode_minutes": 2.0},
                    "结局": {"avg_duration": 8.0, "shots": 4, "episode_minutes": 0.53}
                }
            }
        }


class VideoGenerationStrategy(ABC):
    """视频生成策略的抽象基类"""
    
    @abstractmethod
    def calculate_duration(self, content_unit: Any) -> Dict:
        """计算单个内容单元的时长"""
        pass
    
    @abstractmethod
    def allocate_content(self, all_events: List[Dict], total_units: int) -> List[Dict]:
        """将内容分配到各个单元（集/集/视频）"""
        pass
    
    @abstractmethod
    def generate_shot_sequence(self, event: Dict, context: Dict) -> List[Dict]:
        """生成镜头序列"""
        pass
    
    @abstractmethod
    def get_pacing_guidelines(self) -> Dict:
        """获取节奏指导"""
        pass


class ShortFilmStrategy(VideoGenerationStrategy):
    """
    短片/动画电影策略（5-30分钟）
    
    特点：
    - 单个完整故事
    - 精简情节，聚焦主线
    - 节奏紧凑，无冗余
    - 视觉表现力强
    """
    
    def __init__(self):
        self.logger = get_logger("ShortFilmStrategy")
    
    def calculate_duration(self, content_unit: Any) -> Dict:
        """
        短片时长计算：基于故事复杂度
        
        简单故事: 5-10分钟
        中等故事: 10-20分钟
        复杂故事: 20-30分钟
        """
        event_count = len(content_unit.get("major_events", []))
        
        if event_count <= 3:
            duration_range = (5, 10)
            complexity = "简单"
        elif event_count <= 6:
            duration_range = (10, 20)
            complexity = "中等"
        else:
            duration_range = (20, 30)
            complexity = "复杂"
        
        # 估算时长：每个重大事件约3-4分钟
        estimated_minutes = event_count * 3.5
        estimated_minutes = max(duration_range[0], min(duration_range[1], estimated_minutes))
        
        return {
            "duration_minutes": estimated_minutes,
            "duration_seconds": int(estimated_minutes * 60),
            "complexity": complexity,
            "duration_range": duration_range
        }
    
    def allocate_content(self, all_events: List[Dict], total_units: int = 1) -> List[Dict]:
        """
        短片内容分配：所有事件组成一个完整作品
        
        策略：
        1. 选择核心重大事件（3-8个）
        2. 按照叙事弧线排序（起承转合）
        3. 删除支线事件
        """
        self.logger.info(f"🎬 短片模式：从{len(all_events)}个事件中精选核心事件")
        
        # 1. 评估事件重要性
        scored_events = []
        for event in all_events:
            score = self._calculate_event_importance(event)
            scored_events.append((score, event))
        
        # 2. 排序并选择top事件
        scored_events.sort(key=lambda x: x[0], reverse=True)
        
        # 短片通常需要3-8个核心事件
        target_count = min(8, max(3, len(scored_events)))
        selected_events = [event for score, event in scored_events[:target_count]]
        
        # 3. 按章节重新排序（保持叙事顺序）
        selected_events.sort(key=lambda e: e.get("_start_chapter", 0))
        
        return [{
            "unit_number": 1,
            "unit_type": "短片",
            "major_events": selected_events,
            "estimated_duration_minutes": sum(
                self.calculate_duration({"major_events": [e]})["duration_minutes"]
                for e in selected_events
            )
        }]
    
    def _calculate_event_importance(self, event: Dict) -> float:
        """
        计算事件重要性（用于精选）
        
        评分因素：
        - 情感强度
        - 与主线相关性
        - 包含特殊情感事件
        - 在阶段中的角色（高潮/转折）
        """
        score = 0.0
        
        # 1. 情感强度
        emotional_intensity = event.get("emotional_intensity", "medium")
        intensity_scores = {"low": 1.0, "medium": 2.0, "high": 3.0}
        score += intensity_scores.get(emotional_intensity, 2.0)
        
        # 2. 阶段角色权重
        role = event.get("role_in_stage_arc", "")
        if "高潮" in role or "转折" in role:
            score += 3.0
        elif "开局" in role or "结局" in role:
            score += 2.0
        
        # 3. 包含特殊情感事件
        if event.get("special_emotional_events"):
            score += 2.0
        
        # 4. 事件复杂度（composition中的中级事件数量）
        composition = event.get("composition", {})
        medium_event_count = sum(len(events) for events in composition.values())
        score += min(medium_event_count * 0.3, 2.0)
        
        return score
    
    def generate_shot_sequence(self, event: Dict, context: Dict) -> List[Dict]:
        """
        短片镜头序列：更艺术化、电影化
        
        特点：
        - 更多视觉隐喻镜头
        - 更长的镜头时长
        - 强烈的视觉风格
        """
        shots = []
        
        event_name = event.get("name", "")
        emotional_focus = event.get("emotional_focus", "中等")
        
        # 1. 开场镜头（建立氛围）
        shots.append({
            "shot_number": 1,
            "shot_type": "全景",
            "camera_movement": "缓慢推近",
            "duration_seconds": 6,
            "description": f"开场：建立{event_name}的氛围和环境",
            "visual_focus": "环境氛围",
            "cinematic_note": "运用浅景深，突出主体"
        })
        
        # 2. 角色出场（中景）
        shots.append({
            "shot_number": 2,
            "shot_type": "中景",
            "camera_movement": "固定",
            "duration_seconds": 4,
            "description": "角色登场，建立关系",
            "visual_focus": "人物构图",
            "cinematic_note": "使用黄金分割构图"
        })
        
        # 3. 核心冲突（特写系列）
        shots.append({
            "shot_number": 3,
            "shot_type": "特写",
            "camera_movement": "缓慢推近",
            "duration_seconds": 5,
            "description": "聚焦核心冲突细节",
            "visual_focus": "关键细节",
            "cinematic_note": "眼神交流，微表情捕捉"
        })
        
        # 4. 高潮时刻（大特写+慢动作）
        shots.append({
            "shot_number": 4,
            "shot_type": "大特写",
            "camera_movement": "慢动作",
            "duration_seconds": 3,
            "description": "决定性瞬间的时间凝固",
            "visual_focus": "极致聚焦",
            "cinematic_note": "高速摄影，强调瞬间张力"
        })
        
        # 5. 收尾镜头（拉远）
        shots.append({
            "shot_number": 5,
            "shot_type": "全景",
            "camera_movement": "缓慢拉远",
            "duration_seconds": 5,
            "description": "事件结束，留下余韵",
            "visual_focus": "环境回归",
            "cinematic_note": "留白，给观众思考空间"
        })
        
        return shots
    
    def get_pacing_guidelines(self) -> Dict:
        """短片节奏指导"""
        return {
            "overall_pace": "紧凑有力，无冗余",
            "opening": "快速建立冲突（1-2分钟）",
            "development": "快速推进，每分钟都有信息量",
            "climax": "高潮集中，情感爆发",
            "ending": "简洁有力，可留白思考",
            "average_shot_duration": "3-6秒（长于短视频）",
            "editing_style": "叙事性剪辑，强调连贯性"
        }


class LongSeriesStrategy(VideoGenerationStrategy):
    """
    长篇剧集策略 - 基于中级事件分集
    
    特点：
    - 每个中级事件 = 一集视频
    - 保留完整的叙事结构
    - 节奏张弛有度，高潮部分时长加倍
    - 注重音频与视觉同步
    """
    
    def __init__(self):
        self.logger = get_logger("LongSeriesStrategy")
        
        # 加载视频配置
        video_config = load_video_config()
        default_duration = video_config.get("default_shot_duration", 8.0)
        series_config = video_config.get("shot_duration", {}).get("long_series", {})
        
        # 叙事阶段配置：从配置文件读取或使用默认值
        # 🔥 同时支持新旧两种格式的阶段名称
        self.stage_config = {
            # 新格式
            "起因": {
                "shots": series_config.get("起因", {}).get("shots", 5),
                "avg_duration": series_config.get("起因", {}).get("avg_duration", default_duration),
                "episode_minutes": series_config.get("起因", {}).get("episode_minutes", 0.67),
                "needs_opening": True,
                "needs_ending": False,
                "mood": "渐进，建立紧张感"
            },
            "发展": {
                "shots": series_config.get("发展", {}).get("shots", 8),
                "avg_duration": series_config.get("发展", {}).get("avg_duration", default_duration),
                "episode_minutes": series_config.get("发展", {}).get("episode_minutes", 1.07),
                "needs_opening": False,
                "needs_ending": False,
                "mood": "节奏加快，信息密集"
            },
            "高潮": {
                "shots": series_config.get("高潮", {}).get("shots", 15),
                "avg_duration": series_config.get("高潮", {}).get("avg_duration", default_duration),
                "episode_minutes": series_config.get("高潮", {}).get("episode_minutes", 2.0),
                "needs_opening": False,
                "needs_ending": True,
                "mood": "紧张激烈，情绪爆发"
            },
            "结局": {
                "shots": series_config.get("结局", {}).get("shots", 4),
                "avg_duration": series_config.get("结局", {}).get("avg_duration", default_duration),
                "episode_minutes": series_config.get("结局", {}).get("episode_minutes", 0.53),
                "needs_opening": False,
                "needs_ending": True,
                "mood": "舒缓释放，留下余韵"
            },
            # 旧格式 (起承转合) - 使用相同配置
            "起": {
                "shots": series_config.get("起", {}).get("shots", series_config.get("起因", {}).get("shots", 5)),
                "avg_duration": series_config.get("起", {}).get("avg_duration", series_config.get("起因", {}).get("avg_duration", default_duration)),
                "episode_minutes": series_config.get("起", {}).get("episode_minutes", series_config.get("起因", {}).get("episode_minutes", 0.67)),
                "needs_opening": True,
                "needs_ending": False,
                "mood": "渐进，建立紧张感"
            },
            "承": {
                "shots": series_config.get("承", {}).get("shots", series_config.get("发展", {}).get("shots", 8)),
                "avg_duration": series_config.get("承", {}).get("avg_duration", series_config.get("发展", {}).get("avg_duration", default_duration)),
                "episode_minutes": series_config.get("承", {}).get("episode_minutes", series_config.get("发展", {}).get("episode_minutes", 1.07)),
                "needs_opening": False,
                "needs_ending": False,
                "mood": "节奏加快，信息密集"
            },
            "转": {
                "shots": series_config.get("转", {}).get("shots", series_config.get("高潮", {}).get("shots", 15)),
                "avg_duration": series_config.get("转", {}).get("avg_duration", series_config.get("高潮", {}).get("avg_duration", default_duration)),
                "episode_minutes": series_config.get("转", {}).get("episode_minutes", series_config.get("高潮", {}).get("episode_minutes", 2.0)),
                "needs_opening": False,
                "needs_ending": True,
                "mood": "紧张激烈，情绪爆发"
            },
            "合": {
                "shots": series_config.get("合", {}).get("shots", series_config.get("结局", {}).get("shots", 4)),
                "avg_duration": series_config.get("合", {}).get("avg_duration", series_config.get("结局", {}).get("avg_duration", default_duration)),
                "episode_minutes": series_config.get("合", {}).get("episode_minutes", series_config.get("结局", {}).get("episode_minutes", 0.53)),
                "needs_opening": False,
                "needs_ending": True,
                "mood": "舒缓释放，留下余韵"
            }
        }
        
        self.logger.info(f"✅ 长剧集策略初始化完成，默认镜头时长: {default_duration}秒")
    
    def allocate_content(self, all_events: List[Dict], total_units: int = 0) -> List[Dict]:
        """
        基于中级事件分配分集
        
        策略：
        1. 从每个重大事件的 composition 中提取中级事件
        2. 每个中级事件独立成为一集
        3. 按叙事阶段（起因→发展→高潮→结局）排序
        
        Args:
            all_events: 所有重大事件列表
            total_units: 忽略此参数，自动计算
        
        Returns:
            分集列表
        """
        self.logger.info(f"📺 长剧集模式：从{len(all_events)}个重大事件中提取中级事件")
        
        episodes = []
        episode_number = 0
        total_chapters = 0
        
        # 遍历所有重大事件
        for major_event in all_events:
            major_event_name = major_event.get("name", "")
            chapter_range = major_event.get("chapter_range", "")
            
            # 记录章节范围用于计算总数
            try:
                from src.managers.StagePlanUtils import parse_chapter_range
                start_ch, end_ch = parse_chapter_range(chapter_range)
                total_chapters = max(total_chapters, end_ch)
            except:
                pass
            
            # 提取中级事件
            medium_events = self._extract_medium_events(major_event)
            
            # 为每个中级事件创建一集
            for medium_event in medium_events:
                episode_number += 1
                stage = medium_event.get("stage", "发展")
                
                episodes.append({
                    "episode_number": episode_number,
                    "unit_number": episode_number,  # 兼容原有字段
                    "unit_type": "分集",
                    
                    # 关联信息
                    "major_event_name": major_event_name,
                    "medium_event_name": medium_event.get("name", ""),
                    "stage": stage,
                    "chapter": medium_event.get("chapter", 0),
                    "chapter_range": chapter_range,
                    
                    # 内容
                    "major_event": major_event,
                    "medium_event": medium_event,
                    
                    # 时长估算（根据叙事阶段）
                    "estimated_duration_minutes": self.stage_config.get(stage, {}).get("episode_minutes", 3.0)
                })
        
        self.logger.info(f"✅ 分配完成：{len(episodes)} 集（覆盖约{total_chapters}章）")
        return episodes
    
    def _extract_medium_events(self, major_event: Dict) -> List[Dict]:
        """
        从重大事件的 composition 中提取中级事件
        
        支持多种叙事阶段的命名方式:
        - 新格式: 起因、发展、高潮、结局
        - 旧格式: 起、承、转、合
        
        Args:
            major_event: 重大事件字典
            
        Returns:
            中级事件列表
        """
        medium_events = []
        
        composition = major_event.get("composition", {})
        
        if not composition:
            self.logger.warn(f"  ⚠️ 重大事件'{major_event.get('name')}'没有composition字段")
            return medium_events
        
        # 🔥 支持多种叙事阶段的命名方式
        # 优先使用新格式，如果为空则尝试旧格式
        new_stage_order = ["起因", "发展", "高潮", "结局"]
        old_stage_order = ["起", "承", "转", "合"]
        
        # 检测使用哪种格式
        has_new_format = any(composition.get(stage) for stage in new_stage_order)
        has_old_format = any(composition.get(stage) for stage in old_stage_order)
        
        if has_new_format:
            stage_order = new_stage_order
            self.logger.debug(f"    📋 使用新格式: {new_stage_order}")
        elif has_old_format:
            stage_order = old_stage_order
            self.logger.debug(f"    📋 使用旧格式: {old_stage_order}")
        else:
            # 🔥 如果都没有，尝试提取所有非空键
            stage_order = list(composition.keys())
            if stage_order:
                self.logger.debug(f"    📋 使用动态格式: {stage_order}")
            else:
                self.logger.warn(f"    ⚠️ composition为空或无效: {list(composition.keys())}")
                return medium_events
        
        # 按叙事顺序提取
        for stage in stage_order:
            events = composition.get(stage, [])
            
            if not isinstance(events, list):
                self.logger.warn(f"    ⚠️ stage '{stage}' 的 events 不是列表: {type(events)}")
                continue
            
            if not events:
                continue
            
            self.logger.debug(f"    ✅ 从 '{stage}' 提取到 {len(events)} 个中级事件")
            
            for event in events:
                if isinstance(event, dict):
                    medium_events.append({
                        **event,
                        "stage": stage,
                        "parent_major_event": major_event.get("name")
                    })
                else:
                    self.logger.warn(f"    ⚠️ 事件不是字典类型: {type(event)}")
        
        self.logger.info(f"    📊 从'{major_event.get('name')}'提取了{len(medium_events)}个中级事件")
        return medium_events
    
    def calculate_duration(self, content_unit: Any) -> Dict:
        """
        计算分集时长：基于叙事阶段
        
        高潮部分时长加倍（7.5分钟），其他部分根据阶段调整
        """
        stage = content_unit.get("stage", "发展")
        config = self.stage_config.get(stage, self.stage_config["发展"])
        
        minutes = config.get("episode_minutes", 3.0)
        
        return {
            "duration_minutes": minutes,
            "duration_seconds": int(minutes * 60),
            "stage": stage,
            "shots_count": config.get("shots", 8)
        }
    
    def generate_shot_sequence(self, event: Dict, context: Dict) -> List[Dict]:
        """
        为中级事件生成镜头序列（包含完整音频设计）
        
        特点：
        - 根据叙事阶段确定镜头数量和节奏
        - 高潮部分镜头更多、时长更长
        - 每个镜头包含完整的音频同步设计
        """
        stage = context.get("stage", "发展")
        config = self.stage_config.get(stage, self.stage_config["发展"])
        
        shots = []
        shot_number = 0
        
        # 1. 开场镜头（如果需要）
        if config.get("needs_opening"):
            shot_number += 1
            shots.append(self._create_opening_shot(shot_number, event, context, stage))
        
        # 2. 主要镜头序列
        main_shots_count = config.get("shots", 8)
        for i in range(main_shots_count):
            shot_number += 1
            shots.append(self._create_main_shot(shot_number, i, event, context, stage))
        
        # 3. 结尾镜头
        if config.get("needs_ending"):
            shot_number += 1
            shots.append(self._create_ending_shot(shot_number, event, context, stage))
        
        return shots
    
    def _create_opening_shot(self, shot_number: int, event: Dict, context: Dict, stage: str) -> Dict:
        """创建开场镜头"""
        shot = {
            "shot_number": shot_number,
            "shot_type": "全景",
            "camera_movement": "缓慢推近",
            "duration_seconds": self.stage_config[stage]["avg_duration"] * 1.2,
            "description": f"开场：建立{event.get('name', '')}的氛围和环境",
            "visual_focus": "环境氛围",
            "scene_role": "opening"
        }
        shot["audio_design"] = self._generate_audio_design(shot, event, stage, "opening")
        return shot
    
    def _create_main_shot(self, shot_number: int, index: int,
                         event: Dict, context: Dict, stage: str) -> Dict:
        """创建主要镜头"""
        shot = {
            "shot_number": shot_number,
            "shot_type": self._select_shot_type(index, stage),
            "camera_movement": self._select_camera_movement(index, stage),
            "duration_seconds": self.stage_config[stage]["avg_duration"],
            "description": self._generate_shot_description(event, index, stage),
            "visual_focus": self._get_visual_focus(stage),
            "scene_role": "main"
        }
        shot["audio_design"] = self._generate_audio_design(shot, event, stage, "main")
        return shot
    
    def _create_ending_shot(self, shot_number: int, event: Dict, context: Dict, stage: str) -> Dict:
        """创建结尾镜头"""
        shot = {
            "shot_number": shot_number,
            "shot_type": "全景",
            "camera_movement": "缓慢拉远",
            "duration_seconds": self.stage_config[stage]["avg_duration"] * 0.8,
            "description": f"收尾：{event.get('name', '')}结束，留下余韵",
            "visual_focus": "环境回归",
            "scene_role": "ending"
        }
        shot["audio_design"] = self._generate_audio_design(shot, event, stage, "ending")
        return shot
    
    def _select_shot_type(self, index: int, stage: str) -> str:
        """根据位置和阶段选择景别"""
        shot_types = {
            "起因": ["全景", "中景", "近景", "中景", "特写"],
            "发展": ["中景", "近景", "近景", "特写", "近景", "中景", "特写", "中景"],
            "高潮": ["近景", "特写", "特写", "大特写", "特写", "近景", "特写", "大特写",
                    "特写", "近景", "特写", "大特写", "特写", "近景", "全景"],
            "结局": ["近景", "中景", "特写", "全景"]
        }
        types = shot_types.get(stage, shot_types["发展"])
        return types[index % len(types)]
    
    def _select_camera_movement(self, index: int, stage: str) -> str:
        """选择运镜方式"""
        if stage == "高潮":
            movements = ["快速推近", "手持晃动", "急速摇镜", "慢动作", "快速切换",
                        "环绕", "推近拉远", "固定", "快速推近", "跟随", "慢动作",
                        "大特写推", "急速摇", "拉远", "全景摇"]
        elif stage == "起因":
            movements = ["缓慢推近", "固定", "轻微平移", "缓慢摇镜", "固定"]
        else:
            movements = ["固定", "缓慢推近", "平移", "跟随", "缓慢拉远",
                        "环绕", "推近", "固定"]
        
        return movements[index % len(movements)]
    
    def _generate_shot_description(self, event: Dict, index: int, stage: str) -> str:
        """生成镜头描述"""
        event_name = event.get("name", "事件")
        
        descriptions = {
            "起因": [
                f"展示{event_name}的背景环境",
                f"引出{event_name}的起因",
                f"角色发现{event_name}的线索",
                f"场景逐步建立紧张感",
                f"为{event_name}做铺垫"
            ],
            "发展": [
                f"{event_name}逐步推进",
                f"角色在{event_name}中的行动",
                f"情节细节展开",
                f"角色反应和互动",
                f"信息逐步揭示",
                f"情节转折点",
                f"关键动作展示",
                f"为高潮做铺垫"
            ],
            "高潮": [
                f"{event_name}的关键时刻",
                f"紧张冲突达到顶点",
                f"角色面临抉择",
                f"情感爆发瞬间",
                f"动作激烈交锋",
                f"悬念揭晓时刻",
                f"决定性瞬间",
                f"极致紧张时刻",
                f"冲突白热化",
                f"情绪高潮点",
                f"转折性时刻",
                f"危机爆发",
                f"高光时刻",
                f"震撼瞬间",
                f"高潮延续"
            ],
            "结局": [
                f"{event_name}的结果展现",
                f"情绪逐渐平复",
                f"为后续埋下伏笔",
                f"留下思考空间"
            ]
        }
        
        desc_list = descriptions.get(stage, descriptions["发展"])
        return desc_list[index % len(desc_list)]
    
    def _get_visual_focus(self, stage: str) -> str:
        """获取视觉焦点"""
        focus_map = {
            "起因": "环境氛围和角色表情",
            "发展": "人物动作和情节推进",
            "高潮": "情感细节和关键动作",
            "结局": "整体画面和余韵"
        }
        return focus_map.get(stage, "人物和情节")
    
    def _generate_audio_design(self, shot: Dict, event: Dict, stage: str, role: str) -> Dict:
        """生成音频同步设计"""
        shot_type = shot["shot_type"]
        duration = shot["duration_seconds"]
        
        # 先生成各个音频组件
        bgm = self._generate_bgm_design(stage, role)
        sfx = self._generate_sound_effects(shot, stage, role)
        atmosphere = {
            "mood": self.stage_config[stage]["mood"],
            "transition": self._get_audio_transition(role),
            "intensity": self._get_audio_intensity(stage, role)
        }
        
        # 生成提示词(使用已经生成的组件)
        generation_prompt = self._generate_audio_prompt(shot, event, stage, role, bgm, sfx, atmosphere)
        
        audio_design = {
            "background_music": bgm,
            "sound_effects": sfx,
            "atmosphere": atmosphere,
            "generation_prompt": generation_prompt
        }
        
        return audio_design
    
    def _generate_bgm_design(self, stage: str, role: str) -> Dict:
        """生成背景音乐设计"""
        bgm_types = {
            "起因": {"type": "渐进式紧张音乐", "volume": "中低", "tempo": "缓慢"},
            "发展": {"type": "节奏明快音乐", "volume": "中", "tempo": "中等"},
            "高潮": {"type": "紧张激烈音乐", "volume": "高", "tempo": "快速"},
            "结局": {"type": "舒缓释放音乐", "volume": "中低", "tempo": "缓慢"}
        }
        
        base = bgm_types.get(stage, bgm_types["发展"])
        
        # 根据镜头角色调整
        if role == "opening":
            base["fade_in"] = "1.0秒淡入"
            base["prompt"] = f"{base['type']}，逐步增强，营造期待感"
        elif role == "ending":
            base["fade_out"] = "2.0秒淡出"
            base["prompt"] = f"{base['type']}，逐渐减弱，留下余韵"
        else:
            base["prompt"] = f"{base['type']}，{base['tempo']}节奏"
        
        return base
    
    def _generate_sound_effects(self, shot: Dict, stage: str, role: str) -> List[Dict]:
        """生成音效列表"""
        effects = []
        
        if stage == "高潮":
            effects.extend([
                {"effect": "心跳音效", "timing": "0s", "duration": "持续"},
                {"effect": "呼吸声", "timing": "0s", "duration": "持续"},
                {"effect": "环境静音后突然爆发", "timing": "2s", "duration": "0.5s"}
            ])
        elif stage == "起因":
            effects.append({"effect": "环境音（风声/脚步）", "timing": "0s", "duration": "持续"})
        elif stage == "发展":
            effects.append({"effect": "动作音效", "timing": "0s", "duration": "按需"})
        
        # 根据景别添加音效
        if shot["shot_type"] in ["特写", "大特写"]:
            effects.append({"effect": "细节音效放大", "timing": "0s", "duration": "持续"})
        
        return effects
    
    def _get_audio_transition(self, role: str) -> str:
        """获取音频过渡描述"""
        transitions = {
            "opening": "从静音渐入",
            "main": "保持连贯",
            "ending": "渐出至静音"
        }
        return transitions.get(role, "平滑过渡")
    
    def _get_audio_intensity(self, stage: str, role: str) -> str:
        """获取音频强度"""
        if stage == "高潮":
            return "极高 - 紧张激烈"
        elif stage == "起因":
            return "低 - 逐步上升"
        elif stage == "结局":
            return "中低 - 逐步下降"
        return "中 - 稳定持续"
    
    def _generate_audio_prompt(self, shot: Dict, event: Dict, stage: str, role: str,
                               bgm: Dict, sfx: List, atmosphere: Dict) -> str:
        """生成AI音频生成提示词"""
        
        sfx_list = "\n".join([f"  - {e['effect']}: {e['timing']}开始, {e['duration']}"
                              for e in sfx])
        
        prompt = f"""音频生成请求 - 镜头{shot['shot_number']} ({role})

【视觉信息】
描述：{shot['description']}
景别：{shot['shot_type']}
运镜：{shot['camera_movement']}
时长：{shot['duration_seconds']}秒

【音频要求】

1. 背景音乐（BGM）
   - 风格：{bgm['type']}
   - 音量：{bgm['volume']}
   - 节奏：{bgm.get('tempo', '中等')}
   - 淡入淡出：{bgm.get('fade_in', '无')} / {bgm.get('fade_out', '无')}
   - 提示词：{bgm['prompt']}

2. 音效（SFX）
{sfx_list if sfx_list else "  - 无特殊音效要求"}

3. 整体氛围
   - 情绪目标：{atmosphere['mood']}
   - 强度：{atmosphere['intensity']}
   - 过渡：{atmosphere['transition']}

【同步要求】
- 音频节奏与镜头节奏完美匹配
- 高潮时刻音量适当提升
- 音效在关键时刻突出

注意：生成时长{shot['duration_seconds']}秒的音频，与视频画面完美同步。"""
        
        return prompt
    
    def get_pacing_guidelines(self) -> Dict:
        """长剧集节奏指导"""
        return {
            "overall_pace": "张弛有度，有快有慢",
            "opening": "适度铺垫，3-5分钟建立冲突",
            "development": "多线并进，支线丰富",
            "climax": "高潮明确，情感充分释放",
            "ending": "收束当前剧情，为下集铺垫",
            "average_shot_duration": "3-5秒",
            "editing_style": "经典叙事剪辑"
        }


class ShortVideoStrategy(VideoGenerationStrategy):
    """
    短视频策略（1-3分钟）
    
    特点：
    - 极度精炼，只保留高光时刻
    - 节奏极快，3秒一钩子
    - 视觉冲击力强
    - 竖屏构图
    - 即时满足感
    """
    
    def __init__(self):
        self.logger = get_logger("ShortVideoStrategy")
    
    def calculate_duration(self, content_unit: Any) -> Dict:
        """
        短视频时长计算：1-3分钟
        
        极简内容，每个视频只包含1个核心时刻
        """
        return {
            "duration_minutes": 2,  # 平均2分钟
            "duration_seconds": 120,
            "format": "竖屏"
        }
    
    def allocate_content(self, all_events: List[Dict], total_units: int) -> List[Dict]:
        """
        短视频内容分配：每个重大事件 = 1个短视频
        
        策略：
        1. 每个重大事件独立成片
        2. 只保留事件的核心高潮部分
        3. 提炼最具冲击力的镜头
        """
        self.logger.info(f"📱 短视频模式：{len(all_events)}个事件转换为{len(all_events)}个短视频")
        
        videos = []
        for idx, event in enumerate(all_events, 1):
            videos.append({
                "unit_number": idx,
                "unit_type": "短视频",
                "major_events": [event],  # 单个事件
                "estimated_duration_minutes": 2,
                "format": "竖屏 9:16"
            })
        
        return videos
    
    def generate_shot_sequence(self, event: Dict, context: Dict) -> List[Dict]:
        """
        短视频镜头序列：极快节奏，强冲击
        
        特点：
        - 0.5-2秒的快速镜头
        - 大量转场特效
        - 字幕和音效配合
        - 前3秒必须有钩子
        """
        shots = []
        
        event_name = event.get("name", "")
        
        # 1. 黄金3秒钩子（必须有！）
        shots.append({
            "shot_number": 1,
            "shot_type": "大特写",
            "camera_movement": "快速推近",
            "duration_seconds": 2,
            "description": f"⚡ 钩子：{event_name}的最震撼瞬间",
            "visual_focus": "最强视觉冲击",
            "tiktok_note": "必须前3秒抓住眼球",
            "overlay_text": "震撼标题"
        })
        
        # 2. 快速背景铺垫（1秒）
        shots.append({
            "shot_number": 2,
            "shot_type": "全景",
            "camera_movement": "快速摇镜",
            "duration_seconds": 1,
            "description": "快速交代背景",
            "visual_focus": "场景快速扫过"
        })
        
        # 3. 核心高潮（多镜头快剪）
        for i in range(3):
            shots.append({
                "shot_number": 3 + i,
                "shot_type": ["特写", "近景", "中景"][i % 3],
                "camera_movement": "快速切换",
                "duration_seconds": 1.5,
                "description": f"高潮镜头 {i+1}",
                "visual_focus": "连续冲击",
                "transition": "闪白/划像"
            })
        
        # 4. 结尾反转/悬念（2秒）
        shots.append({
            "shot_number": 6,
            "shot_type": "大特写",
            "camera_movement": "慢动作",
            "duration_seconds": 2,
            "description": "结尾反转或悬念",
            "visual_focus": "意外或期待",
            "overlay_text": "关注看下集"
        })
        
        return shots
    
    def get_pacing_guidelines(self) -> Dict:
        """短视频节奏指导"""
        return {
            "overall_pace": "极速，无尿点",
            "opening": "前3秒必须有钩子",
            "development": "快速推进，每秒都有信息",
            "climax": "高潮密集，连续冲击",
            "ending": "意外反转或悬念",
            "average_shot_duration": "1-2秒",
            "editing_style": "快剪，大量转场",
            "platform_adaptation": {
                "抖音": "竖屏，快节奏，强BGM",
                "快手": "真实感，接地气",
                "视频号": "微信生态，社交属性"
            }
        }


class VideoAdapterManager:
    """
    多类型视频转换适配器（统一入口）
    
    支持三种视频模式的统一转换接口
    """
    
    # 视频类型映射
    STRATEGY_MAP = {
        "short_film": ShortFilmStrategy,
        "long_series": LongSeriesStrategy,
        "short_video": ShortVideoStrategy
    }
    
    def __init__(self, novel_generator):
        """
        初始化适配器
        
        Args:
            novel_generator: 小说生成器实例
        """
        self.generator = novel_generator
        self.logger = get_logger("VideoAdapterManager")
        
        # 当前使用的策略
        self.current_strategy: Optional[VideoGenerationStrategy] = None
        
        # 通用镜头库
        self.shot_library = self._init_shot_library()
    
    def _init_shot_library(self) -> Dict:
        """初始化镜头库（所有模式共享）"""
        return {
            "shot_types": {
                "全景": {"default_duration": 5, "purpose": "环境建立"},
                "中景": {"default_duration": 3, "purpose": "人物关系"},
                "近景": {"default_duration": 2, "purpose": "动作细节"},
                "特写": {"default_duration": 2, "purpose": "情绪表达"},
                "大特写": {"default_duration": 1.5, "purpose": "极致聚焦"}
            },
            "movements": {
                "推近": "紧张、聚焦",
                "拉远": "释放、总结",
                "摇镜": "转换、跟随",
                "跟拍": "沉浸、动态",
                "固定": "稳定、观察"
            }
        }
    
    def convert_to_video(
        self,
        novel_data: Dict,
        video_type: str,
        filtered_events: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict:
        """
        统一的视频转换接口
        
        Args:
            novel_data: 小说数据
            video_type: 视频类型
                      - "short_film": 短片/动画电影
                      - "long_series": 长篇剧集
                      - "short_video": 短视频系列
            filtered_events: 可选，预过滤的事件列表（如果提供，则不再提取所有事件）
            **kwargs: 其他参数（根据类型不同而不同）
        
        Returns:
            视频分镜头脚本
        """
        self.logger.info(f"🎬 开始转换为【{video_type}】模式...")
        
        # 1. 获取对应策略
        if video_type not in self.STRATEGY_MAP:
            raise ValueError(f"不支持的视频类型: {video_type}。支持的类型: {list(self.STRATEGY_MAP.keys())}")
        
        strategy_class = self.STRATEGY_MAP[video_type]
        self.current_strategy = strategy_class()
        
        # 2. 🔥 始终创建 event_extractor（用于后续提取角色）
        event_extractor = get_event_extractor(self.logger)
        
        # 3. 🔥 使用过滤后的事件列表或提取所有重大事件
        if filtered_events is not None:
            all_events = filtered_events
            self.logger.info(f"📊 使用预过滤的事件列表: {len(all_events)} 个事件")
        else:
            all_events = event_extractor.extract_all_major_events(novel_data)
            self.logger.info(f"📊 提取到 {len(all_events)} 个重大事件")
        
        # 4. 🔥 提取角色设计数据
        characters = event_extractor.extract_character_designs(novel_data)
        character_prompts = event_extractor.generate_character_prompts(characters)
        self.logger.info(f"👥 提取到 {len(characters)} 个角色设计")
        
        # 5. 计算单元数量（集数/视频数）
        total_units = kwargs.get("total_units")
        if not total_units:
            total_units = self._calculate_default_units(novel_data, video_type)
        
        # 6. 分配内容到各个单元
        if self.current_strategy is None:
            raise RuntimeError("策略未正确初始化")
        units = self.current_strategy.allocate_content(all_events, total_units)
        self.logger.info(f"✅ 分配完成：{len(units)} 个单元")
        
        # 7. 为每个单元生成分镜头
        for unit in units:
            unit["storyboard"] = self._generate_unit_storyboard(unit, novel_data)
        
        # 8. 生成整体风格指南
        style_guide = self._generate_style_guide(novel_data, video_type)
        
        # 9. 🔥 添加角色设计和剧照生成信息
        character_design_info = {
            "total_characters": len(characters),
            "characters": characters,
            "character_prompts": character_prompts,
            "generation_order": self._generate_character_generation_order(characters, all_events)
        }
        
        # 10. 组装最终结果
        result = {
            "video_type": video_type,
            "video_type_name": self._get_type_name(video_type),
            "series_info": self._generate_series_info(novel_data, units, video_type),
            "visual_style_guide": style_guide,
            "units": units,
            "character_design": character_design_info,
            "pacing_guidelines": self.current_strategy.get_pacing_guidelines() if self.current_strategy else {}
        }
        
        self.logger.info(f"✅ 转换完成：{video_type} 模式，{len(units)} 个单元")
        return result
    
    def _generate_character_generation_order(self, characters: List[Dict], events: List[Dict]) -> List[Dict]:
        """
        生成角色剧照生成顺序
        
        优先级：
        1. 主角（优先级最高）
        2. 在早期事件中出现的角色
        3. 重要配角
        4. 其他角色
        
        Args:
            characters: 角色列表
            events: 事件列表
            
        Returns:
            排序后的角色生成顺序列表
        """
        character_order = []
        
        # 为每个角色计算优先级分数
        for char in characters:
            name = char.get("name", "")
            role = char.get("role", "")
            
            score = 0
            
            # 基础分数：角色定位
            if "主角" in role:
                score += 100
            elif "重要配角" in role or "配角" in role:
                score += 50
            else:
                score += 10
            
            # 根据首次出现章节加分（越早出现分数越高）
            first_appearance = char.get("first_appearance_chapter", 999)
            if first_appearance > 0 and first_appearance < 999:
                score += max(0, 50 - first_appearance)
            
            # 根据在事件中出现的频率加分
            appearance_count = 0
            for event in events[:10]:  # 只检查前10个事件
                event_name = event.get("name", "")
                description = event.get("description", "")
                if name in event_name or name in description:
                    appearance_count += 1
            
            score += appearance_count * 5
            
            character_order.append({
                "character": char,
                "priority_score": score,
                "generation_order": 0  # 稍后设置
            })
        
        # 按优先级排序
        character_order.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # 设置生成顺序
        for idx, item in enumerate(character_order):
            item["generation_order"] = idx + 1
            item["recommended_prompt"] = item["character"].get("generation_prompt", "")
        
        self.logger.info(f"✅ 已生成 {len(character_order)} 个角色的剧照生成顺序")
        
        return character_order
    
    def _calculate_default_units(self, novel_data: Dict, video_type: str) -> int:
        """计算默认的单元数量"""
        total_chapters = novel_data.get("current_progress", {}).get("total_chapters", 200)
        
        if video_type == "short_film":
            return 1  # 短片就是1个
        elif video_type == "long_series":
            # 长剧集：每集约20章
            return max(1, total_chapters // 20)
        elif video_type == "short_video":
            # 短视频：每个重大事件1个视频
            stage_plans = novel_data.get("stage_writing_plans", {})
            total_events = 0
            for stage_data in stage_plans.values():
                plan = stage_data.get("stage_writing_plan", {})
                events = plan.get("event_system", {}).get("major_events", [])
                total_events += len(events)
            return total_events
        
        return 1
    
    def _generate_unit_storyboard(self, unit: Dict, novel_data: Dict) -> Dict:
        """为单个单元（分集）生成分镜头"""
        storyboard = {
            "unit_number": unit["unit_number"],
            "unit_type": unit["unit_type"],
            "total_scenes": 0,
            "scenes": []
        }
        
        # 对于长剧集模式，使用中级事件而不是重大事件
        if unit.get("unit_type") == "分集" and unit.get("medium_event"):
            # 使用中级事件生成场景
            medium_event = unit["medium_event"]
            scene = self._convert_medium_event_to_scene(medium_event, unit, novel_data)
            if scene:
                storyboard["scenes"].append(scene)
        else:
            # 原有逻辑：使用重大事件
            major_events = unit.get("major_events", [])
            for event_idx, event in enumerate(major_events, 1):
                scene = self._convert_event_to_scene(event, event_idx, novel_data)
                if scene:
                    storyboard["scenes"].append(scene)
        
        storyboard["total_scenes"] = len(storyboard["scenes"])
        
        # 计算总时长
        total_duration = sum(
            scene.get("estimated_duration_seconds", 0)
            for scene in storyboard["scenes"]
        )
        storyboard["total_duration_seconds"] = total_duration
        storyboard["total_duration_minutes"] = round(total_duration / 60, 1)
        
        return storyboard
    
    def _convert_medium_event_to_scene(
        self,
        medium_event: Dict,
        unit: Dict,
        novel_data: Dict
    ) -> Optional[Dict]:
        """将中级事件转换为场景"""
        event_name = medium_event.get("name", "未命名中级事件")
        stage = unit.get("stage", "发展")
        
        # 构建上下文，包含stage信息
        context = {
            "stage": stage,
            "unit": unit
        }
        
        # 使用当前策略生成镜头序列
        if self.current_strategy is None:
            self.logger.warn("策略未初始化，使用默认镜头序列")
            shot_sequence = self._generate_default_shots(medium_event)
        else:
            shot_sequence = self.current_strategy.generate_shot_sequence(medium_event, context)
        
        if not shot_sequence:
            return None
        
        # 计算场景时长
        scene_duration = sum(
            shot.get("duration_seconds", 0)
            for shot in shot_sequence
        )
        
        return {
            "scene_number": unit.get("episode_number", 1),
            "scene_title": event_name,
            "scene_description": medium_event.get("description", ""),
            "chapter": medium_event.get("chapter", 0),
            "stage": stage,
            "estimated_duration_seconds": scene_duration,
            "estimated_duration_minutes": round(scene_duration / 60, 1),
            "shot_sequence": shot_sequence,
            "audio_design": self._generate_audio_summary(shot_sequence, stage),
            "visual_notes": self._generate_visual_notes(medium_event)
        }
    
    def _generate_audio_summary(self, shot_sequence: List[Dict], stage: str) -> Dict:
        """生成场景级音频摘要"""
        bgm_style_map = {
            "起因": "渐进式紧张",
            "发展": "节奏明快",
            "高潮": "紧张激烈",
            "结局": "舒缓释放"
        }
        
        mood_map = {
            "起因": "渐进，建立紧张感",
            "发展": "节奏加快，信息密集",
            "高潮": "紧张激烈，情绪爆发",
            "结局": "舒缓释放，留下余韵"
        }
        
        # 获取情绪描述，使用固定的映射而不是依赖策略属性
        overall_mood = mood_map.get(stage, "中等")
        
        return {
            "overall_mood": overall_mood,
            "bgm_style": bgm_style_map.get(stage, "中等"),
            "total_shots": len(shot_sequence),
            "audio_prompts": [shot.get("audio_design", {}).get("generation_prompt", "")
                             for shot in shot_sequence if shot.get("audio_design")]
        }
    
    def _convert_event_to_scene(
        self,
        event: Dict,
        scene_number: int,
        novel_data: Dict
    ) -> Optional[Dict]:
        """将事件转换为场景"""
        event_name = event.get("name", "未命名事件")
        main_goal = event.get("main_goal", "")
        
        # 使用当前策略生成镜头序列
        if self.current_strategy is None:
            self.logger.warn("策略未初始化，使用默认镜头序列")
            shot_sequence = self._generate_default_shots(event)
        else:
            shot_sequence = self.current_strategy.generate_shot_sequence(event, novel_data)
        
        if not shot_sequence:
            return None
        
        # 计算场景时长
        scene_duration = sum(
            shot.get("duration_seconds", 0)
            for shot in shot_sequence
        )
        
        return {
            "scene_number": scene_number,
            "scene_title": event_name,
            "scene_description": main_goal,
            "chapter_range": event.get("chapter_range", ""),
            "estimated_duration_seconds": scene_duration,
            "estimated_duration_minutes": round(scene_duration / 60, 1),
            "shot_sequence": shot_sequence,
            "audio_design": self._generate_audio_design(event),
            "visual_notes": self._generate_visual_notes(event)
        }
    
    def _generate_audio_design(self, event: Dict) -> Dict:
        """生成音频设计"""
        return {
            "background_music": self._suggest_bgm(),
            "sound_effects": ["环境音", "动作音效"],
            "dialogue_rhythm": "自然流畅"
        }
    
    def _suggest_bgm(self) -> str:
        """建议背景音乐"""
        return "根据场景情绪调整"
    
    def _generate_visual_notes(self, event: Dict) -> Dict:
        """生成视觉备注"""
        return {
            "color_palette": "根据情绪调整",
            "lighting": "自然光",
            "composition_style": "经典构图"
        }
    
    def _generate_style_guide(self, novel_data: Dict, video_type: str) -> Dict:
        """生成风格指南"""
        category = novel_data.get("category", "未分类")
        
        base_guide = {
            "genre_style": self._get_genre_style(category),
            "overall_aesthetic": "根据视频类型调整"
        }
        
        # 根据类型添加特定指南
        if video_type == "short_film":
            base_guide["film_craft"] = "电影质感，艺术性强"
        elif video_type == "long_series":
            base_guide["series_craft"] = "电视剧质感，叙事完整"
        elif video_type == "short_video":
            base_guide["viral_elements"] = "病毒传播要素，强钩子"
        
        return base_guide
    
    def _get_genre_style(self, category: str) -> str:
        """获取类型风格"""
        styles = {
            "玄幻": "东方幻想，特效华丽",
            "武侠": "古风写实，动作流畅",
            "都市": "现代写实",
            "科幻": "未来感，科技美学"
        }
        return styles.get(category, "写实风格")
    
    def _generate_series_info(self, novel_data: Dict, units: List[Dict], video_type: str) -> Dict:
        """生成系列信息"""
        total_duration = sum(
            unit.get("storyboard", {}).get("total_duration_minutes", 0)
            for unit in units
        )
        
        return {
            "title": novel_data.get("novel_title", "未命名"),
            "total_units": len(units),
            "total_duration_minutes": round(total_duration, 1),
            "source_material": "novel",
            "genre": novel_data.get("category", "未分类"),
            "unit_type": units[0].get("unit_type", "未知") if units else "未知"
        }
    
    def _get_type_name(self, video_type: str) -> str:
        """获取类型中文名"""
        names = {
            "short_film": "短片/动画电影",
            "long_series": "长篇剧集",
            "short_video": "短视频系列"
        }
        return names.get(video_type, video_type)
    
    def _generate_default_shots(self, event: Dict) -> List[Dict]:
        """生成默认镜头序列（当策略未初始化时）"""
        return [
            {
                "shot_number": 1,
                "shot_type": "全景",
                "camera_movement": "固定",
                "duration_seconds": 3,
                "description": "场景建立",
                "visual_focus": "环境"
            },
            {
                "shot_number": 2,
                "shot_type": "中景",
                "camera_movement": "缓慢推近",
                "duration_seconds": 4,
                "description": "主要动作",
                "visual_focus": "人物"
            }
        ]