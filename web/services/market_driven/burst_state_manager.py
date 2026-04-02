# -*- coding: utf-8 -*-
"""
番茄爆款状态管理器
管理核心设定、动态状态、情绪节奏三层数据
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ProtagonistCore:
    """主角核心设定（不变）"""
    name: str
    age: int
    initial_identity: str
    core_personality: List[str]
    appearance_tags: List[str]


@dataclass
class NPCCore:
    """NPC核心设定（不变）"""
    name: str
    role: str
    identity: str
    core_trait: List[str]
    initial_relation: str
    fate: Optional[str] = None


@dataclass
class CoreIdentity:
    """核心设定（一成不变）"""
    protagonist: ProtagonistCore
    core_npcs: Dict[str, NPCCore]
    world_anchors: Dict[str, Any]


@dataclass
class ProtagonistCurrent:
    """主角当前状态（会变）"""
    cultivation_level: str = "凡人"
    current_wealth: int = 0
    current_job: str = ""
    current_location: str = ""
    known_identity: str = "隐藏"
    love_interest_progress: int = 0


@dataclass
class NPCState:
    """NPC动态状态"""
    current_relation: str
    current_location: str
    knows_mc_secret: bool = False
    status: str = "正常"
    shame_level: int = 0
    revenge_plan: Optional[str] = None


@dataclass
class DynamicState:
    """动态状态（每章更新）"""
    current_chapter: int = 0
    protagonist_current: ProtagonistCurrent = None
    npc_states: Dict[str, NPCState] = None
    key_numbers: Dict[str, Any] = None
    active_events: List[Dict] = None
    
    def __post_init__(self):
        if self.protagonist_current is None:
            self.protagonist_current = ProtagonistCurrent()
        if self.npc_states is None:
            self.npc_states = {}
        if self.key_numbers is None:
            self.key_numbers = {
                "system_level": 1,
                "revenge_count": 0,
                "shock_events": 0
            }
        if self.active_events is None:
            self.active_events = []


@dataclass
class EmotionRecord:
    """情绪记录"""
    ch: int
    emotion: str
    intensity: int


@dataclass
class ChapterEmotionPlan:
    """单章情绪规划"""
    ch: int
    type: str  # "收获", "铺垫", "打脸", "转折"
    target_emotion: str
    intensity: Optional[int] = None
    target_npc: Optional[str] = None
    scene: Optional[str] = None


@dataclass
class EmotionRhythm:
    """情绪节奏（写作指导）"""
    emotion_history: List[EmotionRecord]
    next_chapters: List[ChapterEmotionPlan]
    slap_schedule: Dict[int, Dict]  # 章节 -> 打脸规划


class BurstStateManager:
    """
    番茄爆款状态管理器
    管理三层数据：核心设定、动态状态、情绪节奏
    """
    
    def __init__(self, novel_title: str, base_path: str = "小说项目"):
        self.novel_title = novel_title
        self.project_path = Path(base_path) / novel_title
        self.project_path.mkdir(parents=True, exist_ok=True)
        
        # 三层数据
        self.core_identity: Optional[CoreIdentity] = None
        self.dynamic_state: Optional[DynamicState] = None
        self.emotion_rhythm: Optional[EmotionRhythm] = None
        
        # 加载或初始化
        self._load_or_init()
    
    def _load_or_init(self):
        """加载或初始化所有数据"""
        # 核心设定（必须存在，从plan生成）
        core_path = self.project_path / "core_identity.json"
        if core_path.exists():
            self._load_core_identity()
        else:
            logger.info(f"核心设定不存在，等待从plan生成: {self.novel_title}")
        
        # 动态状态（可初始化）
        dynamic_path = self.project_path / "dynamic_state.json"
        if dynamic_path.exists():
            self._load_dynamic_state()
        else:
            self.dynamic_state = DynamicState()
            self._save_dynamic_state()
        
        # 情绪节奏（可初始化）
        rhythm_path = self.project_path / "emotion_rhythm.json"
        if rhythm_path.exists():
            self._load_emotion_rhythm()
        else:
            self.emotion_rhythm = EmotionRhythm(
                emotion_history=[],
                next_chapters=[],
                slap_schedule={}
            )
            self._save_emotion_rhythm()
    
    def _load_core_identity(self):
        """加载核心设定"""
        path = self.project_path / "core_identity.json"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析主角
        p_data = data['protagonist']
        protagonist = ProtagonistCore(**p_data)
        
        # 解析NPC
        npcs = {}
        for name, npc_data in data['core_npcs'].items():
            npcs[name] = NPCCore(name=name, **npc_data)
        
        self.core_identity = CoreIdentity(
            protagonist=protagonist,
            core_npcs=npcs,
            world_anchors=data['world_anchors']
        )
        logger.info(f"已加载核心设定: 主角{protagonist.name}, {len(npcs)}个NPC")
    
    def _load_dynamic_state(self):
        """加载动态状态"""
        path = self.project_path / "dynamic_state.json"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析主角当前状态
        p_data = data.get('protagonist_current', {})
        protagonist_current = ProtagonistCurrent(**p_data)
        
        # 解析NPC状态
        npc_states = {}
        for name, npc_data in data.get('npc_states', {}).items():
            npc_states[name] = NPCState(**npc_data)
        
        self.dynamic_state = DynamicState(
            current_chapter=data.get('current_chapter', 0),
            protagonist_current=protagonist_current,
            npc_states=npc_states,
            key_numbers=data.get('key_numbers', {}),
            active_events=data.get('active_events', [])
        )
    
    def _load_emotion_rhythm(self):
        """加载情绪节奏"""
        path = self.project_path / "emotion_rhythm.json"
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 解析情绪历史
        history = [EmotionRecord(**r) for r in data.get('emotion_history', [])]
        
        # 解析下章规划
        next_chapters = [ChapterEmotionPlan(**p) for p in data.get('next_chapters', [])]
        
        self.emotion_rhythm = EmotionRhythm(
            emotion_history=history,
            next_chapters=next_chapters,
            slap_schedule=data.get('slap_schedule', {})
        )
    
    def _save_dynamic_state(self):
        """保存动态状态"""
        path = self.project_path / "dynamic_state.json"
        data = {
            "current_chapter": self.dynamic_state.current_chapter,
            "protagonist_current": asdict(self.dynamic_state.protagonist_current),
            "npc_states": {name: asdict(state) for name, state in self.dynamic_state.npc_states.items()},
            "key_numbers": self.dynamic_state.key_numbers,
            "active_events": self.dynamic_state.active_events
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _save_emotion_rhythm(self):
        """保存情绪节奏"""
        path = self.project_path / "emotion_rhythm.json"
        data = {
            "emotion_history": [asdict(r) for r in self.emotion_rhythm.emotion_history],
            "next_chapters": [asdict(p) for p in self.emotion_rhythm.next_chapters],
            "slap_schedule": self.emotion_rhythm.slap_schedule
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def init_from_plan(self, plan: Dict, tropes: Dict):
        """从plan和tropes初始化核心设定"""
        
        # 解析主角
        protagonist = ProtagonistCore(
            name=plan.get('protagonist_name', '主角'),
            age=plan.get('protagonist_age', 25),
            initial_identity=plan.get('protagonist_identity', '普通人'),
            core_personality=plan.get('protagonist_personality', ['隐忍', '护短']).split(',') if isinstance(plan.get('protagonist_personality'), str) else ['隐忍', '护短'],
            appearance_tags=plan.get('protagonist_appearance', ['平凡', '坚毅']).split(',') if isinstance(plan.get('protagonist_appearance'), str) else ['平凡', '坚毅']
        )
        
        # 解析NPC（从plan或tropes）
        npcs = {}
        if 'important_npcs' in plan:
            for npc_data in plan['important_npcs']:
                name = npc_data.get('name', 'NPC')
                npcs[name] = NPCCore(
                    name=name,
                    role=npc_data.get('role', '配角'),
                    identity=npc_data.get('identity', '未知'),
                    core_trait=npc_data.get('traits', ['普通']).split(',') if isinstance(npc_data.get('traits'), str) else ['普通'],
                    initial_relation=npc_data.get('relation', '陌生'),
                    fate=npc_data.get('fate')
                )
        
        # 世界观锚点
        world_anchors = {
            "current_year": plan.get('year', 2024),
            "main_city": plan.get('main_city', '东海市'),
            "power_system": tropes.get('power_system', '系统流'),
            "key_locations": plan.get('key_locations', ['市中心', '郊区']).split(',') if isinstance(plan.get('key_locations'), str) else ['市中心']
        }
        
        self.core_identity = CoreIdentity(
            protagonist=protagonist,
            core_npcs=npcs,
            world_anchors=world_anchors
        )
        
        # 保存核心设定
        self._save_core_identity()
        
        # 初始化动态状态
        self.dynamic_state.protagonist_current.current_location = world_anchors['main_city']
        self._save_dynamic_state()
        
        # 初始化情绪节奏
        self._init_emotion_rhythm_from_tropes(tropes)
        
        logger.info(f"已从plan初始化: 主角{protagonist.name}, {len(npcs)}个NPC")
    
    def _save_core_identity(self):
        """保存核心设定"""
        path = self.project_path / "core_identity.json"
        data = {
            "protagonist": asdict(self.core_identity.protagonist),
            "core_npcs": {name: asdict(npc) for name, npc in self.core_identity.core_npcs.items()},
            "world_anchors": self.core_identity.world_anchors
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _init_emotion_rhythm_from_tropes(self, tropes: Dict):
        """从tropes初始化情绪节奏"""
        # 解析爽点规划
        slap_schedule = {}
        if 'pacing' in tropes:
            pacing = tropes['pacing']
            # 从节奏安排生成爽点规划
            if 'first_face_slap' in pacing:
                ch = self._parse_chapter_number(pacing['first_face_slap'])
                slap_schedule[ch] = {"intensity": 5, "target": "初期反派", "scene": "未知"}
        
        # 生成前30章情绪规划
        next_chapters = []
        for ch in range(1, 31):
            if ch in slap_schedule:
                plan = ChapterEmotionPlan(
                    ch=ch,
                    type="打脸",
                    target_emotion="爽快",
                    intensity=slap_schedule[ch].get('intensity', 6),
                    target_npc=slap_schedule[ch].get('target'),
                    scene=slap_schedule[ch].get('scene')
                )
            elif ch == 1:
                plan = ChapterEmotionPlan(ch=ch, type="转折", target_emotion="压抑→希望", intensity=8)
            elif ch % 10 == 0:
                plan = ChapterEmotionPlan(ch=ch, type="大高潮", target_emotion="震惊", intensity=9)
            else:
                plan = ChapterEmotionPlan(ch=ch, type="推进", target_emotion="期待")
            
            next_chapters.append(plan)
        
        self.emotion_rhythm = EmotionRhythm(
            emotion_history=[],
            next_chapters=next_chapters,
            slap_schedule=slap_schedule
        )
        self._save_emotion_rhythm()
    
    def _parse_chapter_number(self, text: str) -> int:
        """从文本解析章节数"""
        import re
        match = re.search(r'(\d+)', str(text))
        return int(match.group(1)) if match else 5
    
    def update_after_chapter(self, chapter_num: int, chapter_data: Dict):
        """每章生成后更新状态"""
        
        # 验证并更新主角状态
        state_updates = chapter_data.get('state_updates', {})
        
        # 更新主角
        if 'protagonist' in state_updates:
            p_updates = state_updates['protagonist']
            for key, value in p_updates.items():
                if hasattr(self.dynamic_state.protagonist_current, key):
                    setattr(self.dynamic_state.protagonist_current, key, value)
        
        # 更新NPC
        if 'npcs' in state_updates:
            for name, npc_update in state_updates['npcs'].items():
                if name in self.dynamic_state.npc_states:
                    for key, value in npc_update.items():
                        if hasattr(self.dynamic_state.npc_states[name], key):
                            setattr(self.dynamic_state.npc_states[name], key, value)
                else:
                    # 新NPC
                    self.dynamic_state.npc_states[name] = NPCState(**npc_update)
        
        # 更新关键数字
        if 'key_numbers' in state_updates:
            self.dynamic_state.key_numbers.update(state_updates['key_numbers'])
        
        # 更新当前章节
        self.dynamic_state.current_chapter = chapter_num
        
        # 记录情绪结果
        emotion_result = chapter_data.get('emotion_result', {})
        if emotion_result:
            self.emotion_rhythm.emotion_history.append(EmotionRecord(
                ch=chapter_num,
                emotion=emotion_result.get('actual_emotion', '未知'),
                intensity=emotion_result.get('intensity', 5)
            ))
        
        # 更新下章规划（移除已完成的）
        self.emotion_rhythm.next_chapters = [
            p for p in self.emotion_rhythm.next_chapters if p.ch > chapter_num
        ]
        
        # 保存
        self._save_dynamic_state()
        self._save_emotion_rhythm()
        
        logger.info(f"已更新状态: 第{chapter_num}章完成, 主角{self.dynamic_state.protagonist_current.cultivation_level}")
    
    def build_system_prompt(self, for_chapter: int, 
                           emotion_beat: Optional[Dict] = None) -> str:
        """
        构建System Prompt（三层叠加）
        
        Args:
            for_chapter: 章节号
            emotion_beat: 可选，情绪节拍（从EmotionFlow传入）
        """
        if not self.core_identity:
            raise ValueError("核心设定未初始化")
        
        # 第一层：核心设定
        core_section = self._format_core_section()
        
        # 第二层：动态状态
        dynamic_section = self._format_dynamic_section()
        
        # 第三层：情绪规划（优先使用传入的emotion_beat）
        if emotion_beat:
            emotion_section = self._format_emotion_beat(emotion_beat)
        else:
            emotion_section = self._format_emotion_section(for_chapter)
        
        prompt = f"""【番茄爆款作家 - 系统模式】

{core_section}

{dynamic_section}

{emotion_section}

=== 输出要求 ===
1. 主角名字必须是"{self.core_identity.protagonist.name}"，不能变
2. NPC姓名和身份必须符合"核心设定"
3. 主角当前状态必须从"动态状态"开始，不能倒退
4. 按照"本章情绪规划"的节奏写
5. 章尾必须有钩子

=== 输出JSON格式 ===
{{
  "consistency_check": {{
    "protagonist_name_correct": true/false,
    "npc_names_correct": true/false,
    "numbers_consistent": true/false
  }},
  "chapter_title": "第{for_chapter}章 XXX",
  "content": "正文内容（2000-3000字）",
  "state_updates": {{
    "protagonist": {{"cultivation_level": "...", "current_wealth": ...}},
    "npcs": {{"NPC名": {{"current_relation": "..."}}}},
    "key_numbers": {{"system_level": ...}}
  }},
  "emotion_result": {{
    "actual_emotion": "实际达成的情绪",
    "intensity": 1-10,
    "hook": "章尾钩子"
  }}
}}"""
        return prompt
    
    def _format_core_section(self) -> str:
        """格式化核心设定部分"""
        p = self.core_identity.protagonist
        npcs = self.core_identity.core_npcs
        world = self.core_identity.world_anchors
        
        npc_lines = []
        for name, npc in npcs.items():
            npc_lines.append(f"- {name}: {npc.role}, {npc.identity}, 初始关系{npc.initial_relation}")
        
        return f"""=== 【核心设定】（绝对不能变）===
【主角】
- 姓名：{p.name}
- 年龄：{p.age}
- 初始身份：{p.initial_identity}
- 外貌：{', '.join(p.appearance_tags)}
- 性格：{', '.join(p.core_personality)} ⚠️ 绝对不能崩！

【重要人物】（姓名身份不能错）
{chr(10).join(npc_lines)}

【世界观锚点】
- 时间：{world.get('current_year', '2024')}
- 主舞台：{world.get('main_city', '东海市')}
- 力量体系：{world.get('power_system', '系统流')}"""
    
    def _format_dynamic_section(self) -> str:
        """格式化动态状态部分"""
        pc = self.dynamic_state.protagonist_current
        
        npc_lines = []
        for name, npc in self.dynamic_state.npc_states.items():
            npc_lines.append(f"- {name}: 关系{npc.current_relation}, 状态{npc.status}, 在{npc.current_location}")
        
        event_lines = []
        for event in self.dynamic_state.active_events:
            event_lines.append(f"- {event.get('name')}: 进度{event.get('progress')}, 截止第{event.get('deadline_ch')}章")
        
        return f"""=== 【当前状态】（必须从这个状态开始写）===
【主角当前】
- 实力：{pc.cultivation_level}
- 资产：{pc.current_wealth:,}元
- 职业：{pc.current_job or '无'}
- 位置：{pc.current_location}
- 身份暴露度：{pc.known_identity}
- 感情线进度：{pc.love_interest_progress}%

【NPC当前状态】
{chr(10).join(npc_lines) if npc_lines else "- 无重要NPC"}

【关键数字】（不能倒退）
- 系统等级：Lv{self.dynamic_state.key_numbers.get('system_level', 1)}
- 打脸次数：{self.dynamic_state.key_numbers.get('revenge_count', 0)}次
- 震惊事件：{self.dynamic_state.key_numbers.get('shock_events', 0)}次

【进行中事件】（必须推进）
{chr(10).join(event_lines) if event_lines else "- 无"}"""
    
    def _format_emotion_section(self, chapter_num: int) -> str:
        """格式化情绪规划部分"""
        # 找到本章规划
        chapter_plan = None
        for plan in self.emotion_rhythm.next_chapters:
            if plan.ch == chapter_num:
                chapter_plan = plan
                break
        
        if not chapter_plan:
            # 默认规划
            chapter_plan = ChapterEmotionPlan(
                ch=chapter_num,
                type="推进",
                target_emotion="期待"
            )
        
        # 查找是否 scheduled slap
        slap_info = self.emotion_rhythm.slap_schedule.get(chapter_num, {})
        
        # 最近情绪历史
        recent_history = self.emotion_rhythm.emotion_history[-3:] if self.emotion_rhythm.emotion_history else []
        history_lines = [f"- 第{r.ch}章: {r.emotion}(强度{r.intensity})" for r in recent_history]
        
        return f"""=== 【本章情绪规划】===
【最近情绪轨迹】
{chr(10).join(history_lines) if history_lines else "- 无前文"}

【第{chapter_num}章规划】
- 类型：{chapter_plan.type}
- 目标情绪：{chapter_plan.target_emotion}
- 强度要求：{chapter_plan.intensity or '中等'}/10
{f"- 打脸目标：{chapter_plan.target_npc}" if chapter_plan.target_npc else ""}
{f"- 场景：{chapter_plan.scene}" if chapter_plan.scene else ""}

【节奏要求】
- 铺垫≤20%，快速进入正题
- 冲突/高潮60%，详细描写
- 章尾必须有钩子（悬念/期待）"""
    
    def _format_emotion_beat(self, beat: Dict) -> str:
        """格式化情绪节拍（从EmotionFlow传入）"""
        return f"""=== 【本章情绪节拍】===
【情绪目标】
- 情绪类型：{beat.get('emotion', '期待')}
- 强度要求：{beat.get('intensity', 5)}/10
- 节拍类型：{beat.get('beat_type', '推进')}
- 关键事件：{beat.get('event', '剧情推进')}
- 本章作用：{beat.get('purpose', '推动剧情')}

【节奏要求】
- 严格按照"{beat.get('emotion', '期待')}"的情绪写
- 强度必须达到{beat.get('intensity', 5)}/10
- 关键事件：{beat.get('event', '完成剧情任务')}
- 章尾必须有钩子"""
    
    def get_state_for_session_switch(self) -> Dict:
        """获取会话切换时需要的状态"""
        return {
            "core_identity": {
                "protagonist": asdict(self.core_identity.protagonist),
                "core_npcs": {name: asdict(npc) for name, npc in self.core_identity.core_npcs.items()},
                "world_anchors": self.core_identity.world_anchors
            },
            "dynamic_state": {
                "current_chapter": self.dynamic_state.current_chapter,
                "protagonist_current": asdict(self.dynamic_state.protagonist_current),
                "npc_states": {name: asdict(state) for name, state in self.dynamic_state.npc_states.items()},
                "key_numbers": self.dynamic_state.key_numbers,
                "active_events": self.dynamic_state.active_events
            },
            "recent_emotions": [asdict(r) for r in self.emotion_rhythm.emotion_history[-3:]],
            "next_plan": [asdict(p) for p in self.emotion_rhythm.next_chapters[:3]]
        }
