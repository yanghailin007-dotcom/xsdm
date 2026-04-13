"""
Tomato Bestseller Tactical Session
番茄爆款细纲会话 - 三轮对话生成30章规划

三轮流程：
1. 第1轮：核心设定对齐（世界观+金手指+主角人设）
2. 第2轮：情绪爽点规划（情绪曲线+钩子+爽点）
3. 第3轮：角色出场规划（已有角色+新增角色）

作者: AI Assistant
版本: 3.0
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from .phase_one_loader import PhaseOneDataLoader, load_phase_one_data

logger = logging.getLogger(__name__)


class TomatoBestsellerTacticalSession:
    """
    番茄爆款细纲会话
    
    专为番茄小说爆款公式设计的三轮细纲规划：
    - 确保核心设定不丢失
    - 章章有钩子，情绪过山车
    - 角色受控，避免乱创
    """
    
    # 番茄爆款常量
    CHAPTERS_PER_BATCH = 30      # 每批次规划30章
    MAX_NEW_CHARACTERS = 2       # 每批次最多新增2个角色
    HOOK_TYPES = ["悬念", "危机", "反转", "震惊", "期待", "疑问"]
    EMOTION_TYPES = ["压抑", "紧张", "愤怒", "嘲讽", "反转", "小爽快", "大爽快", "震惊", "期待", "满足"]
    BEAT_TYPES = ["铺垫", "冲突", "反转", "渲染", "爽点", "伏笔", "过渡"]
    
    def __init__(
        self,
        session_id: str,
        start_chapter: int,
        end_chapter: int,
        project_path: Path,
        api_client=None,
        novel_title: str = "",
        emotion_curve: List[Dict] = None
    ):
        self.session_id = session_id
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        self.project_path = Path(project_path)
        self.api_client = api_client
        self.novel_title = novel_title
        self.emotion_curve = emotion_curve or []
        
        # 加载一阶段数据
        self.phase_one_data = load_phase_one_data(self.project_path)
        
        # 三轮输出缓存
        self.round1_result = None    # 核心设定对齐
        self.round2_result = None    # 情绪爽点规划
        self.round3_result = None    # 角色出场规划
        
        # 最终蓝图
        self.final_blueprint = None
        
        logger.info(f"[TomatoTacticalSession] 初始化: {session_id}, 第{start_chapter}-{end_chapter}章")
    
    def generate_blueprint(self) -> Dict:
        """
        执行三轮对话，生成完整战术蓝图
        
        Returns:
            Dict: 包含设定框架、情绪规划、角色规划的完整蓝图
        """
        logger.info(f"[TomatoTacticalSession] 开始三轮细纲规划")
        
        # 第1轮：核心设定对齐
        logger.info(f"[TomatoTacticalSession] 第1轮：核心设定对齐")
        self.round1_result = self._round_1_core_setting()
        
        # 第2轮：情绪爽点规划
        logger.info(f"[TomatoTacticalSession] 第2轮：情绪爽点规划")
        self.round2_result = self._round_2_emotion_planning()
        
        # 第3轮：角色出场规划
        logger.info(f"[TomatoTacticalSession] 第3轮：角色出场规划")
        self.round3_result = self._round_3_character_planning()
        
        # 合并输出
        self.final_blueprint = self._merge_blueprint()
        
        logger.info(f"[TomatoTacticalSession] 三轮规划完成，生成蓝图")
        return self.final_blueprint
    
    def _round_1_core_setting(self) -> Dict:
        """
        第1轮：核心设定对齐
        
        输入：世界观、金手指、主角人设、阶段目标
        输出：30章设定落地框架
        """
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认框架")
            return self._get_default_core_framework()
        
        # 构建第1轮提示词
        prompt = self._build_round1_prompt()
        system_prompt = self._get_round1_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round1_core_setting",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            result = self._parse_json_response(response)
            
            # 验证关键字段
            if not result.get('core_framework'):
                logger.warning("[TomatoTacticalSession] 第1轮输出缺少core_framework，使用默认")
                return self._get_default_core_framework()
            
            logger.info(f"[TomatoTacticalSession] 第1轮完成，获得设定框架")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第1轮失败: {e}")
            return self._get_default_core_framework()
    
    def _safe_dict(self, obj, path=""):
        """安全获取字典，非字典时返回空字典并记录警告"""
        if isinstance(obj, dict):
            return obj
        logger.warning(f"[TomatoTacticalSession] 期望dict但得到{type(obj).__name__} (路径: {path})，使用空字典")
        return {}
    
    def _build_round1_prompt(self) -> str:
        """构建第1轮提示词"""
        # 提取关键数据（带防御性处理）
        world = self._safe_dict(self.phase_one_data.get('world_setting', {}), 'world_setting')
        world_overview = self._safe_dict(world.get('world_overview', {}), 'world_setting.world_overview')
        power_system = self._safe_dict(world.get('power_system', {}), 'world_setting.power_system')
        
        char_design = self._safe_dict(self.phase_one_data.get('character_design', {}), 'character_design')
        protagonist = self._safe_dict(char_design.get('protagonist', {}), 'character_design.protagonist')
        
        stage_goal = self._get_current_stage_goal()
        progression = self.phase_one_data.get('progression_path', {})
        
        # 防御性处理：protagonist_growth 可能是 dict 或 list
        protagonist_growth = progression.get('protagonist_growth', {})
        if isinstance(protagonist_growth, dict):
            milestones = protagonist_growth.get('milestones', [])
        elif isinstance(protagonist_growth, list):
            # 如果是列表，直接使用作为 milestones
            milestones = protagonist_growth
        else:
            milestones = []
        
        # 使用format方法避免f-string问题
        prompt_template = """# 番茄爆款细纲规划 - 第1轮：核心设定对齐

## 任务
为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章的**设定落地框架**。
这是细纲规划的第一轮，重点是确保一阶段的核心设定在30章中得到正确贯彻。

---

## 一、世界观设定（必须严格遵守）

### 背景设定
{background}

### 核心概念
{core_concept}

### 基调风格
{tone}

---

## 二、金手指详细规则（必须严格遵守）

### 系统名称
{system_name}

### 核心机制
{shen_lang_exclusive}

### 等级体系
{level_standard}

### 当前阶段（{start_chapter}-{end_chapter}章）
{current_power_stage}

---

## 三、主角人设（必须严格遵守）

### 基本信息
- 姓名：{protagonist_name}
- 年龄：{protagonist_age}

### 性格特质
{traits}

### 身份定位
{identity}

### 成长弧线
{growth_arc}

### 独特标签
{unique_label}

---

## 四、阶段目标（必须达成）

### 当前阶段
{goal_id}: {goal_description}

### 关键交付物
{key_deliverables}

### 成功标准
{success_criteria}

---

## 五、升级里程碑（本章批应对齐）

{milestones}

---

## 六、输出要求

请输出JSON格式，包含以下内容：

```json
{{
  "core_framework": {{
    "world_building_chapters": [
      {{"chapter": 1, "focus": "世界观核心机制初次体现"}},
      {{"chapter": 4, "focus": "金手指中期能力展现"}}
    ],
    "golden_finger_progression": [
      {{"chapter_range": "1-10", "level": "初创级", "ability": "基础资金/资源获取，建立初步优势", "limitation": "资金规模小，影响力有限"}},
      {{"chapter_range": "11-20", "level": "扩张级", "ability": "区域资源整合，形成局部垄断或话语权", "limitation": "跨区域资源调动仍受限"}},
      {{"chapter_range": "21-30", "level": "掌控级", "ability": "产业链主导权，具备降维打击能力", "limitation": "全国性/全球性资本对抗仍存在风险"}}
    ],
    "protagonist_moments": [
      {{"chapter": 3, "trait": "核心特质A", "action": "在关键时刻展现主角独特能力", "purpose": "体现主角与众不同"}},
      {{"chapter": 8, "trait": "核心特质B", "action": "面对挑战时的标志性应对", "purpose": "强化主角人设标签"}},
      {{"chapter": 15, "trait": "核心特质C", "action": "在重要冲突中做出的选择", "purpose": "推进主角成长弧光"}}
    ],
    "goal_milestones": {{
      "milestone_1": {{"chapter": 3, "deliverable": "首个交付物", "emotion": "震惊反转"}},
      "milestone_2": {{"chapter": 15, "deliverable": "第二个交付物", "emotion": "大爽快"}},
      "milestone_3": {{"chapter": 20, "deliverable": "第三个交付物", "emotion": "期待升级"}}
    }},
    "key_constraints": [
      "金手指使用必须有触发条件和代价，不能随意使用",
      "主角必须保持人设一致性，不能有冲动降智行为",
      "每章必须体现世界观核心设定",
      "必须在指定章节完成阶段目标交付物",
      "严格遵循升级里程碑，不能提前获得后期能力"
    ]
  }}
}}
```

---

## 七、重要提醒

1. **这是第1轮**，重点是设定对齐，不是详细情节
2. **必须严格遵守**上述世界观、金手指、主角人设
3. **阶段目标必须达成**，3个关键交付物必须分配到具体章节
4. **升级节点必须对齐**，不能提前解锁后期能力
5. **约束条件必须列出**，供后续轮次参考

## 八、生成前自检清单（必须执行）

在输出JSON之前，你必须逐条自检并在心中确认全部通过。如果有任何一项不通过，必须修正后再输出：

□ **金手指名称检查**：系统名称必须严格等于"{system_name}"，禁止出现任何其他系统名（如"弹幕干涉系统"等）
□ **数值自洽检查**：升级规则中的数字必须能用简单数学验证（如"每消费100万升1级"则消费1000万必须对应LV10，不能写LV20）
□ **主角名锁定**：主角姓名必须严格等于"{protagonist_name}"，禁止改名
□ **约束具体性**：key_constraints中的每条约束必须具体可检查，禁止出现"尽量""适当"等模糊词
"""
        
        # 🔥 动态提取系统/金手指名称，避免硬编码
        # 注意：金手指名称必须从 golden_finger 数据中取，power_system 是力量体系不是系统名
        system_name = (
            self.phase_one_data.get('golden_finger', {}).get('basic_info', {}).get('name')
            or self.phase_one_data.get('golden_finger', {}).get('name')
            or power_system.get('name')
            or '核心金手指系统'
        )
        
        format_params = {
            'novel_title': self.novel_title,
            'start_chapter': self.start_chapter,
            'end_chapter': self.end_chapter,
            'system_name': system_name,
            'background': world_overview.get('background', '未设定'),
            'core_concept': world_overview.get('core_concept', '未设定'),
            'tone': world_overview.get('tone', '未设定'),
            'shen_lang_exclusive': power_system.get('shen_lang_exclusive', '未设定'),
            'level_standard': power_system.get('level_standard', '未设定'),
            'current_power_stage': self._get_current_power_stage(),
            'protagonist_name': protagonist.get('name', '主角'),
            'protagonist_age': protagonist.get('age', '未知'),
            'traits': self._format_list(protagonist.get('traits', [])),
            'identity': protagonist.get('identity', '未设定'),
            'growth_arc': protagonist.get('growth_arc', '未设定'),
            'unique_label': protagonist.get('unique_label', '未设定'),
            'goal_id': stage_goal.get('goal_id', 'G?'),
            'goal_description': stage_goal.get('description', '未设定'),
            'key_deliverables': self._format_list(stage_goal.get('key_deliverables', [])),
            'success_criteria': stage_goal.get('success_criteria', '未设定'),
            'milestones': self._format_milestones(milestones)
        }
        
        return prompt_template.format(**format_params)
    
    def _get_round1_system_prompt(self) -> str:
        """第1轮系统提示词"""
        return """你是专业的番茄小说细纲规划师，负责核心设定对齐。

你的任务：
1. 确保世界观设定在30章中得到正确体现
2. 规划金手指的递进式展现（从弱到强）
3. 设计体现主角人设的关键时刻
4. 将阶段目标分解到具体章节
5. 列出所有必须遵守的设定约束

输出要求：
- 必须是JSON格式
- 重点在"框架"而非详细情节
- 所有设定必须与输入一致，不能篡改
- 约束条件要具体可检查"""
    
    def _round_2_emotion_planning(self) -> Dict:
        """
        第2轮：情绪爽点规划（核心层）
        
        输入：第1轮输出 + 情绪曲线 + 爆款公式
        输出：30章详细情绪设计
        """
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认情绪规划")
            return self._get_default_emotion_plan()
        
        prompt = self._build_round2_prompt()
        system_prompt = self._get_round2_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round2_emotion_planning",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.75
            )
            
            result = self._parse_json_response(response)
            
            if not result.get('chapters'):
                logger.warning("[TomatoTacticalSession] 第2轮输出缺少chapters，使用默认")
                return self._get_default_emotion_plan()
            
            # 验证每章都有钩子
            self._validate_hooks(result.get('chapters', []))
            
            logger.info(f"[TomatoTacticalSession] 第2轮完成，规划{len(result.get('chapters', []))}章")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第2轮失败: {e}")
            return self._get_default_emotion_plan()
    
    def _build_round2_prompt(self) -> str:
        """构建第2轮提示词 - 使用format方法避免f-string解析问题"""
        # 获取第1轮输出
        round1 = self.round1_result.get('core_framework', {}) if self.round1_result else {}
        
        # 获取情绪蓝图中的高潮节点
        emotion_blueprint = self._safe_dict(self.phase_one_data.get('emotional_blueprint', {}), 'emotional_blueprint')
        climax_moments = emotion_blueprint.get('climax_moments', [])
        
        # 🔥 fallback：如果情绪蓝图没有高潮节点，从 emotion_curve 自动推导（intensity>=9视为高潮）
        if not climax_moments and self.emotion_curve:
            climax_moments = [
                f"第{e.get('chapter')}章-{e.get('emotion', '高潮')}"
                for e in self.emotion_curve
                if e.get('intensity', 0) >= 9
            ]
        
        # 过滤出本章批内的高潮节点
        batch_climax = [c for c in climax_moments 
                       if self.start_chapter <= self._parse_chapter_num(c) <= self.end_chapter]
        
        # 获取情绪曲线（如果有）
        emotion_curve_text = ""
        if self.emotion_curve:
            relevant = [e for e in self.emotion_curve 
                       if self.start_chapter <= e.get('chapter', 0) <= self.end_chapter]
            emotion_curve_text = "\n".join([
                f"第{e.get('chapter')}章: {e.get('emotion', '')} (强度{e.get('intensity', 5)})"
                for e in relevant[:10]
            ])
        
        # 准备所有需要插入的变量
        world_building = self._format_simple_list(round1.get('world_building_chapters', []))
        golden_finger = self._format_simple_list(round1.get('golden_finger_progression', []))
        protagonist_moments = self._format_simple_list(round1.get('protagonist_moments', []))
        goal_milestones = json.dumps(round1.get('goal_milestones', {}), ensure_ascii=False, indent=2)
        key_constraints = self._format_list(round1.get('key_constraints', []))
        batch_climax_str = self._format_list(batch_climax)
        batch_climax_raw = ', '.join(str(c) for c in batch_climax) if batch_climax else '无'
        emotion_text = emotion_curve_text or '未提供详细曲线'
        
        # 使用format方法而不是f-string
        prompt_template = """# 番茄爆款细纲规划 - 第2轮：情绪爽点规划【核心轮】

## 任务
为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章的**详细情绪设计**。
这是三轮中**最重要的一轮**，直接决定读者是否追读。

---

## 一、第1轮输出：设定框架（必须遵守）

### 世界观落地节点
{world_building}

### 金手指升级路线
{golden_finger}

### 主角人设高光时刻
{protagonist_moments}

### 阶段目标里程碑
{goal_milestones}

### 设定约束（绝对不能违反）
{key_constraints}

---

## 二、番茄爆款情绪公式（必须遵循）

### 黄金三章公式
- 第1章：极端压抑(9) - 主角被踩在泥里，读者憋屈想反击
- 第2章：持续嘲讽(8) - 反派疯狂嘲讽，读者愤怒积累  
- 第3章：强势反转(9) - 主角打脸，读者爽感爆发

### 小循环公式（每3-5章）
铺垫(6) → 冲突(7) → 爽点(8) → 渲染(7) → 新伏笔(6)

### 大高潮公式（每10章）
紧张(7) → 冲突升级(8) → 第一波爽(8) → 第二波爽(9) → 巅峰(10)

### 章尾钩子类型
- 悬念：提出新问题（"那个神秘人是谁？"）
- 危机：突然的危险（"一把刀架在了脖子上"）
- 反转：出乎意料（"没想到背后的黑手竟是他"）
- 震惊：颠覆认知（"原来一切都是假的"）
- 期待：预告即将发生（"明天就是决战之日"）

---

## 三、一阶段情绪设计（参考）

### 高潮节点（本章批内）
{batch_climax_str}

### 情绪曲线（前10章）
{emotion_text}

---

## 四、输出要求

请输出第{start_chapter}-{end_chapter}章的详细设计，JSON格式：

```json
{{
  "chapters": [
    {{
      "chapter_number": {start_chapter},
      "emotion": "压抑",
      "intensity": 9,
      "emotion_type": "绝望/愤怒/期待/爽快/震惊/满足",
      "beat_type": "铺垫/冲突/反转/渲染/爽点/伏笔",
      
      "event": "主要事件简述（100字内，必须体现设定）",
      "satisfaction_point": "本章爽点（可无，但不能连续2章无爽点）",
      "face_slapping": "打脸元素（如有）：反派嚣张→主角反转→反派崩溃",
      
      "hook_type": "悬念/危机/反转/震惊/期待",
      "hook_content": "章尾钩子内容（50字内，必须让读者想点下一章）",
      
      "goal_alignment": "如何推进阶段目标",
      "character_highlight": "哪个角色本章高光",
      "constraints": "本章必须遵守的设定约束"
    }}
  ],
  "emotion_analysis": {{
    "pattern": "开局爆发型/递进高潮型/蓄力积累型",
    "variance_score": "情绪起伏评分（1-10）",
    "satisfaction_distribution": "爽点分布说明",
    "hook_distribution": "钩子类型统计",
    "expected_retention": "预估追读率"
  }}
}}
```

---

## 五、番茄爆款硬性要求（必须遵守）

1. **章章有钩子**：每章最后50字必须是钩子，让读者忍不住点下一章
2. **不能连续2章无爽点**：最多隔1章必须有爽点交付
3. **打脸必须爽**：反派先嚣张→主角反转→反派崩溃，三层结构
4. **情绪有起伏**：相邻章情绪强度差必须≥1，不能平铺直叙
5. **高潮节点要对齐**：{batch_climax_raw} 必须是情绪巅峰
6. **设定不能丢**：每章必须体现世界观核心设定或金手指运用

---

## 六、生成前自检清单（必须执行）

在输出JSON之前，你必须逐条自检并在心中确认全部通过。如果有任何一项不通过，必须修正后再输出：

□ **数值-能力匹配检查**：每章的消费规模/能力展现必须与当前等级匹配（严禁前期章出现后期能力，如第3章消费 billion 级）
□ **钩子检查**：每章必须有非空的hook_content，且长度控制在50字以内
□ **爽点分布检查**：检查是否存在连续2章satisfaction_point为空的情况，如有必须调整
□ **情绪起伏检查**：相邻章的intensity差值必须≥1，如有平铺必须调整
□ **高潮对齐检查**：高潮节点{batch_climax_raw}对应章节的intensity必须是本章批内最高或接近最高（≥8）
□ **书名-设定对齐检查**：如果书名含"双倍返利"，则正文金手指规则不能写成"百倍返利"或其他倍数

---

## 七、参考示例

第1章（压抑9）：
- 事件：主角陷入债务危机/职场困境，被前女友/富二代当众羞辱，陷入绝境
- 爽点：无（压抑开局）
- 钩子：主角的手机突然弹出一条系统提示，嘴角闪过一抹意味深长的笑

第3章（反转9）：
- 事件：反派带人上门逼债/羞辱，主角用第一笔系统返利/资源完成强势反击
- 爽点：首次展现金手指，用钱或商业手段碾压对手
- 打脸：反派从嘲讽到震惊到崩溃
- 钩子：反派的靠山打来电话，语气恭敬："沈先生，手下不懂事，您多担待。"
"""
        
        return prompt_template.format(
            novel_title=self.novel_title,
            start_chapter=self.start_chapter,
            end_chapter=self.end_chapter,
            world_building=world_building,
            golden_finger=golden_finger,
            protagonist_moments=protagonist_moments,
            goal_milestones=goal_milestones,
            key_constraints=key_constraints,
            batch_climax_str=batch_climax_str,
            batch_climax_raw=batch_climax_raw,
            emotion_text=emotion_text
        )
    
    def _get_round2_system_prompt(self) -> str:
        """第2轮系统提示词"""
        return """你是番茄小说爆款情绪设计专家。

你的任务：
1. 设计30章情绪曲线，确保章章有起伏
2. 每章必须有章尾钩子（50字内）
3. 规划爽点分布（每3章小爽点，每10章大爽点）
4. 设计打脸节奏（三层结构：嚣张→反转→崩溃）
5. 确保设定约束得到遵守

番茄爆款核心：
- 黄金三章：压抑→嘲讽→反转
- 小循环：铺垫→冲突→爽点→渲染→伏笔
- 大高潮：递进式爽感，3层震惊链

输出要求：
- 必须是JSON格式
- 每章必须包含hook_content
- 情绪必须有起伏，不能连续2章同强度
- 爽点不能连续缺席2章"""
    
    def _round_3_character_planning(self) -> Dict:
        """
        第3轮：角色出场规划
        
        输入：前两轮输出 + 角色设计.json
        输出：角色出场表 + 新增角色规划
        """
        # 加载已有角色
        loader = PhaseOneDataLoader(self.project_path)
        existing_chars = loader.get_character_list()
        
        if not self.api_client:
            logger.warning("[TomatoTacticalSession] 无API客户端，使用默认角色规划")
            return self._get_default_character_plan(existing_chars)
        
        prompt = self._build_round3_prompt(existing_chars)
        system_prompt = self._get_round3_system_prompt()
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_round3_character_planning",
                user_prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7
            )
            
            result = self._parse_json_response(response)
            
            if not result.get('character_plan'):
                logger.warning("[TomatoTacticalSession] 第3轮输出缺少character_plan，使用默认")
                return self._get_default_character_plan(existing_chars)
            
            # 验证新角色数量
            new_chars = result.get('character_plan', {}).get('new_characters', [])
            if len(new_chars) > self.MAX_NEW_CHARACTERS:
                logger.warning(f"[TomatoTacticalSession] 新角色过多({len(new_chars)})，限制为{self.MAX_NEW_CHARACTERS}")
                result['character_plan']['new_characters'] = new_chars[:self.MAX_NEW_CHARACTERS]
            
            logger.info(f"[TomatoTacticalSession] 第3轮完成，规划{len(existing_chars)}个已有角色+{len(new_chars)}个新角色")
            return result
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 第3轮失败: {e}")
            return self._get_default_character_plan(existing_chars)
    
    def _build_round3_prompt(self, existing_chars: List[Dict]) -> str:
        """构建第3轮提示词"""
        # 格式化已有角色
        chars_text = "\n".join([
            f"- {c.get('name')} ({c.get('type')}): {c.get('role')} - 特质: {', '.join(c.get('traits', [])[:3])}"
            for c in existing_chars[:20]
        ])
        
        # 获取第2轮章节规划
        chapters = self.round2_result.get('chapters', []) if self.round2_result else []
        chapters_summary = "\n".join([
            f"第{c.get('chapter_number')}章: {c.get('event', '')[:50]}... 情绪:{c.get('emotion')}{c.get('intensity')}"
            for c in chapters[:15]
        ])
        
        prompt_template = """# 番茄爆款细纲规划 - 第3轮：角色出场规划

## 任务
基于前2轮的情节规划，为每章分配角色出场。

---

## 一、已有角色列表（优先使用）

{chars_text}

**重要原则**：已有角色必须优先使用，避免遗忘！

---

## 二、前2轮情节规划（本章批前15章）

{chapters_summary}

---

## 三、角色分类规则

1. **核心角色**（每章必出场）：主角及其核心伙伴（如有）
2. **重要配角**（关键章出场）：盟友、反派等
3. **次要配角**（按需出场）：NPC、解说员等
4. **新角色**（谨慎新增）：30章最多新增2个，需说明理由

---

## 四、输出要求

JSON格式（示例结构，角色名使用已有角色或合理新创）：

```json
{{
  "character_plan": {{
    "core_characters": [
      {{"name": "主角名", "appearance": "每章必出场", "highlight_chapters": [3,8,15,20,30]}},
      {{"name": "核心伙伴", "appearance": "每章必出场", "highlight_chapters": [3,11,19,24,30]}}
    ],
    "major_characters": [
      {{
        "name": "重要反派A",
        "first_chapter": 2,
        "key_chapters": [2,8,15],
        "purpose": "早期打脸对象",
        "arc": "从嘲讽到恐惧到失败"
      }}
    ],
    "minor_characters": [
      {{"name": "解说员", "first_chapter": 1, "role": "世界观解说"}}
    ],
    "new_characters": [
      {{
        "name": "新反派XXX",
        "first_chapter": 28,
        "purpose": "中期反派铺垫",
        "reason": "剧情需要引入新势力"
      }}
    ],
    "chapter_assignments": [
      {{
        "chapter": {start_chapter},
        "core": ["主角名"],
        "major": [],
        "minor": ["解说员"],
        "notes": "通过解说员引入世界观设定"
      }}
    ],
    "constraints": [
      "禁止创造未规划的有名新角色（路人可用通称）",
      "已有角色优先使用，避免遗忘",
      "新角色必须有完整弧光和后续安排",
      "核心角色每章必须出场"
    ]
  }}
}}

---

## 五、生成前自检清单（必须执行）

在输出JSON之前，你必须逐条自检并在心中确认全部通过。如果有任何一项不通过，必须修正后再输出：

□ **角色名一致性检查**：所有已有角色名字必须与输入列表完全一致，禁止改名、禁止拼写差异
□ **新角色管控检查**：chapter_assignments中出现的所有有名角色，必须已在"已有角色列表"或"new_characters"中声明，禁止临时创造
□ **主角出场检查**：主角必须在每一章的core列表中
□ **反派弧线检查**：重要反派（如前女友、前期富二代）的key_chapters必须覆盖其从登场到落败的完整弧线，不能突然消失
□ **新角色数量检查**：new_characters数量必须≤2个，超过必须删除
"""
        return prompt_template.format(
            chars_text=chars_text,
            chapters_summary=chapters_summary,
            start_chapter=self.start_chapter
        )
    
    def _get_round3_system_prompt(self) -> str:
        """第3轮系统提示词"""
        return """你是角色规划专家，负责为30章分配角色出场。

原则：
1. 优先使用已有角色，避免创造新角色
2. 主角每章必须出场，核心盟友尽量每章出场
3. 重要配角在关键章节高光
4. 新角色30章最多2个，必须有充分理由
5. 为每章分配具体的角色出场

输出要求：
- 必须是JSON格式
- chapter_assignments必须包含每章的角色分配
- new_characters不能超过2个"""
    
    def _merge_blueprint(self) -> Dict:
        """合并三轮输出为最终蓝图"""
        # 获取各轮数据
        round1 = self.round1_result or {}
        round2 = self.round2_result or {}
        round3 = self.round3_result or {}
        
        # 获取章节列表
        chapters = round2.get('chapters', [])
        character_plan = round3.get('character_plan', {})
        
        # 为每章添加角色分配
        chapter_assignments = character_plan.get('chapter_assignments', [])
        assignments_map = {a.get('chapter'): a for a in chapter_assignments}
        
        for chapter in chapters:
            ch_num = chapter.get('chapter_number')
            if ch_num in assignments_map:
                chapter['assigned_characters'] = {
                    'core': assignments_map[ch_num].get('core', []),
                    'major': assignments_map[ch_num].get('major', []),
                    'minor': assignments_map[ch_num].get('minor', [])
                }
            else:
                # 默认分配：从已有角色中提取核心角色，不硬编码
                existing_chars = character_plan.get('existing_characters', [])
                protagonist = next((c for c in existing_chars if c.get('type') == 'protagonist'), None)
                core_chars = [protagonist.get('name')] if protagonist else []
                
                # 添加重要盟友（最多1个）
                allies = [c.get('name') for c in existing_chars if c.get('type') == 'ally'][:1]
                core_chars.extend(allies)
                
                chapter['assigned_characters'] = {
                    'core': core_chars,
                    'major': [],
                    'minor': []
                }
        
        # 构建最终蓝图
        blueprint = {
            'metadata': {
                'session_id': self.session_id,
                'range': f'{self.start_chapter}-{self.end_chapter}',
                'generated_at': datetime.now().isoformat(),
                'rounds_completed': 3,
                'novel_title': self.novel_title
            },
            'core_setting': round1.get('core_framework', {}),
            'chapters': chapters,
            'character_plan': character_plan,
            'emotion_analysis': round2.get('emotion_analysis', {}),
            'summary': {
                'total_chapters': len(chapters),
                'total_satisfaction_points': len([c for c in chapters if c.get('satisfaction_point')]),
                'total_face_slapping': len([c for c in chapters if c.get('face_slapping')]),
                'new_characters_introduced': len(character_plan.get('new_characters', [])),
                'goal_milestones_achieved': len(round1.get('core_framework', {}).get('goal_milestones', {}))
            }
        }
        
        # 🔥 保存新角色到角色设计文件
        self._save_new_characters_to_design(character_plan.get('new_characters', []))
        
        return blueprint
    
    def _save_new_characters_to_design(self, new_characters: List[Dict]) -> None:
        """
        将新角色保存到角色设计.json文件
        
        Args:
            new_characters: 新角色列表
        """
        if not new_characters or not self.project_path:
            return
        
        try:
            import json
            from pathlib import Path
            
            # 角色设计文件路径
            char_design_path = Path(self.project_path) / "phase_one_products" / "角色设计.json"
            
            if not char_design_path.exists():
                logger.warning(f"[TomatoTacticalSession] 角色设计文件不存在: {char_design_path}")
                return
            
            # 读取现有角色设计
            with open(char_design_path, 'r', encoding='utf-8') as f:
                char_design = json.load(f)
            
            # 确保有 supporting_roles 字段
            if 'supporting_roles' not in char_design:
                char_design['supporting_roles'] = []
            
            if not isinstance(char_design['supporting_roles'], list):
                char_design['supporting_roles'] = []
            
            # 获取现有角色名（避免重复）
            existing_names = set()
            for key in ['protagonist', 'core_allies', 'main_antagonists', 'supporting_roles']:
                if key in char_design:
                    if key == 'protagonist' and isinstance(char_design[key], dict):
                        existing_names.add(char_design[key].get('name', ''))
                    elif isinstance(char_design[key], list):
                        for item in char_design[key]:
                            if isinstance(item, dict):
                                existing_names.add(item.get('name', ''))
                    elif isinstance(char_design[key], dict):
                        for stage, villains in char_design[key].items():
                            if isinstance(villains, list):
                                for v in villains:
                                    if isinstance(v, dict):
                                        existing_names.add(v.get('name', ''))
            
            # 添加新角色到 supporting_roles
            added_count = 0
            for char in new_characters:
                if not isinstance(char, dict):
                    continue
                
                char_name = char.get('name', '')
                if not char_name or char_name in existing_names:
                    continue
                
                # 构建角色数据
                char_data = {
                    'name': char_name,
                    'role': char.get('role', '配角'),
                    'identity': char.get('description', ''),
                    'traits': char.get('traits', []),
                    'first_appearance': char.get('first_chapter', char.get('intro_chapter', 0)),
                    'source': 'tactical_planning',
                    'created_at': datetime.now().isoformat(),
                    'notes': f'由战术规划生成，第{char.get("first_chapter", char.get("intro_chapter", 0))}章出场'
                }
                
                char_design['supporting_roles'].append(char_data)
                existing_names.add(char_name)
                added_count += 1
                logger.info(f"[TomatoTacticalSession] 新角色添加到角色设计: {char_name}")
            
            # 保存回文件
            if added_count > 0:
                with open(char_design_path, 'w', encoding='utf-8') as f:
                    json.dump(char_design, f, ensure_ascii=False, indent=2)
                logger.info(f"[TomatoTacticalSession] 角色设计文件已更新: 新增{added_count}个角色")
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] 保存新角色失败: {e}")
    
    # ========== 辅助方法 ==========
    
    def _parse_json_response(self, response) -> Dict:
        """解析API返回的JSON"""
        try:
            if isinstance(response, dict):
                return response
            
            text = str(response)
            # 尝试提取JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            
            logger.warning("[TomatoTacticalSession] 无法从响应中提取JSON")
            return {}
            
        except Exception as e:
            logger.error(f"[TomatoTacticalSession] JSON解析失败: {e}")
            return {}
    
    def _get_current_stage_goal(self) -> Dict:
        """获取当前阶段目标"""
        loader = PhaseOneDataLoader(self.project_path)
        return loader.get_current_stage_goal(self.start_chapter) or {}
    
    def _get_current_power_stage(self) -> str:
        """获取当前能力阶段描述"""
        try:
            progression = self.phase_one_data.get('progression_path', {})
            ability = progression.get('ability_system_progression', {})
            
            # 🔥 防御性处理：确保是字典类型
            early = ability.get('early_stage', {}) if isinstance(ability, dict) else {}
            if isinstance(early, str):
                early = {'mechanics': early, 'description': early}
            
            if self.start_chapter <= 30:
                mechanics = early.get('mechanics', '基础阶段') if isinstance(early, dict) else str(early) or '基础阶段'
                return f"1-30级（早期）: {mechanics}"
            
            mid = ability.get('mid_stage', {}) if isinstance(ability, dict) else {}
            if isinstance(mid, str):
                mid = {'mechanics': mid, 'description': mid}
            
            if self.start_chapter <= 80:
                mechanics = mid.get('mechanics', '成长阶段') if isinstance(mid, dict) else str(mid) or '成长阶段'
                return f"31-80级（中期）: {mechanics}"
            
            return "81级+（后期）: 巅峰阶段"
        except Exception as e:
            logger.warning(f"[_get_current_power_stage] 获取能力阶段失败: {e}")
            return "能力成长阶段"
    
    def _format_list(self, items: List) -> str:
        """格式化列表为字符串"""
        if not items:
            return "- 无"
        return "\n".join([f"- {item}" for item in items])
    
    def _format_simple_list(self, items: List) -> str:
        """格式化简单列表"""
        if not items:
            return "无"
        return "\n".join([str(item) for item in items[:10]])
    
    def _format_milestones(self, milestones: List[Dict]) -> str:
        """格式化里程碑"""
        if not milestones:
            return "- 无"
        return "\n".join([
            f"- 第{m.get('chapter', '?')}: {m.get('event', '')[:50]}"
            for m in milestones
        ])
    
    def _parse_chapter_num(self, chapter_str) -> int:
        """解析章节号"""
        try:
            if isinstance(chapter_str, int):
                return chapter_str
            if isinstance(chapter_str, str):
                # 提取数字
                nums = re.findall(r'\d+', chapter_str)
                return int(nums[0]) if nums else 0
            return 0
        except:
            return 0
    
    def _validate_hooks(self, chapters: List[Dict]):
        """验证每章都有钩子"""
        for ch in chapters:
            ch_num = ch.get('chapter_number', '?')
            if not ch.get('hook_content'):
                logger.warning(f"[TomatoTacticalSession] 第{ch_num}章缺少钩子！")
    
    # ========== 默认输出 ==========
    
    def _get_default_core_framework(self) -> Dict:
        """获取默认核心框架"""
        return {
            'core_framework': {
                'world_building_chapters': [],
                'golden_finger_progression': [],
                'protagonist_moments': [],
                'goal_milestones': {},
                'key_constraints': ['使用默认框架，约束较少']
            }
        }
    
    def _get_default_emotion_plan(self) -> Dict:
        """获取默认情绪规划"""
        chapters = []
        for i in range(self.start_chapter, self.end_chapter + 1):
            chapters.append({
                'chapter_number': i,
                'emotion': '期待',
                'intensity': 7,
                'event': f'第{i}章事件（默认规划）',
                'hook_content': '章尾钩子（默认规划）',
                'assigned_characters': {'core': ['主角', '同伴'], 'major': [], 'minor': []}
            })
        return {'chapters': chapters}
    
    def _get_default_character_plan(self, existing_chars: List[Dict]) -> Dict:
        """获取默认角色规划（基于已有角色，无硬编码）"""
        # 从已有角色中提取主角作为核心
        protagonist = next((c for c in existing_chars if c.get('type') == 'protagonist'), None)
        core = [protagonist.get('name')] if protagonist else []
        
        # 提取盟友和反派作为主要角色
        major = [c.get('name') for c in existing_chars if c.get('type') in ['ally', 'villain']][:5]
        
        chapter_assignments = []
        for i in range(self.start_chapter, self.end_chapter + 1):
            chapter_assignments.append({
                'chapter': i,
                'core': core,
                'major': major if i % 5 == 0 else [],  # 每5章出一次重要配角
                'minor': []
            })
        
        return {
            'character_plan': {
                'core_characters': [{'name': '主角'}, {'name': '同伴'}],
                'major_characters': [],
                'minor_characters': [],
                'new_characters': [],
                'chapter_assignments': chapter_assignments,
                'constraints': ['使用默认规划']
            }
        }


# ========== 全局会话管理 ==========

_sessions: Dict[str, TomatoBestsellerTacticalSession] = {}

def create_tactical_session(
    project_path: Path,
    api_client=None,
    start_chapter: int = 1,
    end_chapter: int = 30,
    novel_title: str = "",
    emotion_curve: List[Dict] = None
) -> TomatoBestsellerTacticalSession:
    """
    创建新的番茄爆款细纲会话
    
    Args:
        project_path: 项目路径
        api_client: API客户端
        start_chapter: 开始章节
        end_chapter: 结束章节
        novel_title: 小说标题
        emotion_curve: 情绪曲线数据
    
    Returns:
        TomatoBestsellerTacticalSession: 细纲会话实例
    """
    session_id = f"TAC-{start_chapter}-{end_chapter}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    session = TomatoBestsellerTacticalSession(
        session_id=session_id,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        project_path=project_path,
        api_client=api_client,
        novel_title=novel_title,
        emotion_curve=emotion_curve
    )
    
    _sessions[session_id] = session
    logger.info(f"[TomatoTacticalSession] 创建会话: {session_id}")
    
    return session

def get_tactical_session(session_id: str) -> Optional[TomatoBestsellerTacticalSession]:
    """获取已创建的会话"""
    return _sessions.get(session_id)
