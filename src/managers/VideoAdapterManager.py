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

from src.utils.logger import get_logger


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
    长篇剧集策略（20-40分钟/集）
    
    特点：
    - 多集连续，每集完整但有关联
    - 保留丰富的支线剧情
    - 节奏张弛有度
    - 注重角色发展
    """
    
    def __init__(self):
        self.logger = get_logger("LongSeriesStrategy")
    
    def calculate_duration(self, content_unit: Any) -> Dict:
        """
        长剧集时长计算：基于章节数量
        
        每集约覆盖15-25章（假设每章1.5-2分钟）
        """
        chapter_range = content_unit.get("chapter_range", "1-10")
        try:
            from src.managers.StagePlanUtils import parse_chapter_range
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
        except:
            chapter_count = 10
        
        # 每章约1.8分钟视频
        estimated_minutes = chapter_count * 1.8
        
        # 限制在20-40分钟范围
        estimated_minutes = max(20, min(40, estimated_minutes))
        
        return {
            "duration_minutes": int(estimated_minutes),
            "duration_seconds": int(estimated_minutes * 60),
            "chapter_coverage": chapter_count
        }
    
    def allocate_content(self, all_events: List[Dict], total_units: int = 0) -> List[Dict]:
        """
        长剧集内容分配：按章节范围均匀分配
        
        策略：
        1. 计算每集应该覆盖的章节数
        2. 将事件按章节范围分配到各集
        3. 确保每集有3-5个重大事件
        """
        self.logger.info(f"📺 长剧集模式：{len(all_events)}个事件分配")
        
        if not total_units:
            # 自动计算集数：每集约20章
            total_chapters = max((e.get("_end_chapter", 0) for e in all_events), default=200)
            total_units = max(1, total_chapters // 20)
        
        self.logger.info(f"  分配到 {total_units} 集")
        
        chapters_per_episode = total_chapters // total_units
        
        episodes = []
        for ep_num in range(1, total_units + 1):
            start_chapter = (ep_num - 1) * chapters_per_episode + 1
            end_chapter = min(ep_num * chapters_per_episode, total_chapters)
            
            # 找到属于本集的事件
            episode_events = [
                e for e in all_events
                if not (e["_end_chapter"] < start_chapter or e["_start_chapter"] > end_chapter)
            ]
            
            episodes.append({
                "unit_number": ep_num,
                "unit_type": "剧集",
                "chapter_range": f"{start_chapter}-{end_chapter}",
                "major_events": episode_events,
                "estimated_duration_minutes": 30  # 默认30分钟
            })
        
        return episodes
    
    def generate_shot_sequence(self, event: Dict, context: Dict) -> List[Dict]:
        """
        长剧集镜头序列：标准叙事节奏
        
        特点：
        - 完整的叙事结构
        - 适中的镜头时长
        - 平衡的对白和动作
        """
        shots = []
        
        # 1. 场景建立
        shots.append({
            "shot_number": 1,
            "shot_type": "全景",
            "camera_movement": "固定",
            "duration_seconds": 3,
            "description": "场景环境建立",
            "visual_focus": "场景设定"
        })
        
        # 2. 角色站位
        shots.append({
            "shot_number": 2,
            "shot_type": "中景",
            "camera_movement": "缓慢推近",
            "duration_seconds": 4,
            "description": "角色关系和站位",
            "visual_focus": "人物构图"
        })
        
        # 3. 主要动作/对白
        shots.append({
            "shot_number": 3,
            "shot_type": "近景",
            "camera_movement": "固定/轻微移动",
            "duration_seconds": 5,
            "description": "主要情节推进",
            "visual_focus": "人物动作和对白"
        })
        
        # 4. 细节强调
        shots.append({
            "shot_number": 4,
            "shot_type": "特写",
            "camera_movement": "固定",
            "duration_seconds": 2,
            "description": "关键细节或表情",
            "visual_focus": "重要细节"
        })
        
        return shots
    
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
        
        # 2. 提取所有重大事件
        all_events = self._extract_all_major_events(novel_data)
        self.logger.info(f"📊 提取到 {len(all_events)} 个重大事件")
        
        # 3. 计算单元数量（集数/视频数）
        total_units = kwargs.get("total_units")
        if not total_units:
            total_units = self._calculate_default_units(novel_data, video_type)
        
        # 4. 分配内容到各个单元
        if self.current_strategy is None:
            raise RuntimeError("策略未正确初始化")
        units = self.current_strategy.allocate_content(all_events, total_units)
        self.logger.info(f"✅ 分配完成：{len(units)} 个单元")
        
        # 5. 为每个单元生成分镜头
        for unit in units:
            unit["storyboard"] = self._generate_unit_storyboard(unit, novel_data)
        
        # 6. 生成整体风格指南
        style_guide = self._generate_style_guide(novel_data, video_type)
        
        # 7. 组装最终结果
        result = {
            "video_type": video_type,
            "video_type_name": self._get_type_name(video_type),
            "series_info": self._generate_series_info(novel_data, units, video_type),
            "visual_style_guide": style_guide,
            "units": units,
            "pacing_guidelines": self.current_strategy.get_pacing_guidelines() if self.current_strategy else {}
        }
        
        self.logger.info(f"✅ 转换完成：{video_type} 模式，{len(units)} 个单元")
        return result
    
    def _extract_all_major_events(self, novel_data: Dict) -> List[Dict]:
        """提取所有重大事件"""
        all_events = []
        
        stage_plans = novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_data in stage_plans.items():
            plan = stage_data.get("stage_writing_plan", {})
            events = plan.get("event_system", {}).get("major_events", [])
            
            for event in events:
                event["_stage"] = stage_name
                chapter_range = event.get("chapter_range", "1-10")
                try:
                    from src.managers.StagePlanUtils import parse_chapter_range
                    start_ch, end_ch = parse_chapter_range(chapter_range)
                    event["_start_chapter"] = start_ch
                    event["_end_chapter"] = end_ch
                except:
                    event["_start_chapter"] = 1
                    event["_end_chapter"] = 10
                
                all_events.append(event)
        
        all_events.sort(key=lambda x: x["_start_chapter"])
        return all_events
    
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
        """为单个单元生成分镜头"""
        storyboard = {
            "unit_number": unit["unit_number"],
            "unit_type": unit["unit_type"],
            "total_scenes": 0,
            "scenes": []
        }
        
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