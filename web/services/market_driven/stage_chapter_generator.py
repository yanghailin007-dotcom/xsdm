"""
阶段式章节生成器
按题材特定的阶段性节奏批量生成
每个阶段创建一个独立对话会话

节奏参数从套路分析中获取：
- stage_climax_interval: 阶段性高潮间隔（如：30章/50章/100章）
- small_climax_interval: 小高潮间隔（如：3章）
- medium_climax_interval: 中高潮间隔（如：10章）
- large_climax_interval: 大高潮间隔（如：20章）
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class StageChapterGenerator:
    """
    阶段式章节生成器
    
    设计原则：
    1. 按题材特定的"阶段性节奏"划分（从套路分析获取）
    2. 每个阶段创建独立对话会话
    3. 会话system_prompt包含完整一阶段设定+本阶段详细规划
    
    阶段划分基于套路分析中的stage_rhythm：
    - stage_climax_chapters: 阶段性高潮章节列表
    - 如果没有提供，使用默认的30章周期
    
    示例（100章小说，默认30章周期）：
    - 阶段1：第1-30章 - 系统觉醒，第一次大高潮
    - 阶段2：第31-60章 - 快速发展，第二次大高潮  
    - 阶段3：第61-90章 - 终极对决，最大高潮
    - 阶段4：第91-100章 - 结局收尾
    """
    
    def __init__(self, api_client, novel_data: Dict, tropes: Dict):
        self.api_client = api_client
        # 确保 novel_data 是字典类型
        if isinstance(novel_data, list):
            import logging
            logging.warning(f"[StageChapterGenerator] novel_data 是列表类型，转换为字典")
            novel_data = novel_data[0] if novel_data else {}
        if not isinstance(novel_data, dict):
            import logging
            logging.warning(f"[StageChapterGenerator] novel_data 类型异常: {type(novel_data)}，使用空字典")
            novel_data = {}
        self.novel_data = novel_data
        self.tropes = tropes
        
        # 提取基本信息
        self.novel_title = novel_data.get('title', '未命名')
        self.total_chapters = novel_data.get('chapters', 100)
        
        # 生成器ID
        import uuid
        self.generator_id = f"STAGE-{uuid.uuid4().hex[:8].upper()}"
        
        # 当前会话
        self.current_session = None
        self.current_stage = None
        
    def calculate_stages(self) -> List[Dict]:
        """
        计算阶段划分 - 基于题材分析的阶段性节奏
        
        从套路分析中获取该题材特定的阶段性节奏：
        - stage_climax_interval: 阶段性大高潮间隔（如：30章/50章/100章）
        - stage_climax_chapters: 具体的阶段性高潮章节列表
        - stage_climax_types: 每个阶段性高潮的类型描述
        
        如果套路分析中没有节奏信息，则使用默认的30章周期。
        """
        stages = []
        
        # 从套路分析中获取阶段性节奏
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        stage_climax_chapters = stage_rhythm.get('stage_climax_chapters', [])
        stage_climax_types = stage_rhythm.get('stage_climax_types', [])
        stage_interval = stage_rhythm.get('stage_climax_interval', 30)
        
        # 如果有具体的阶段性高潮章节列表，按此划分
        if stage_climax_chapters and len(stage_climax_chapters) > 0:
            prev_ch = 0
            for i, climax_ch in enumerate(stage_climax_chapters):
                if climax_ch > self.total_chapters:
                    break
                    
                start_ch = prev_ch + 1
                end_ch = min(climax_ch, self.total_chapters)
                
                # 获取该阶段的高潮类型描述
                climax_type = stage_climax_types[i] if i < len(stage_climax_types) else f"第{i+1}次阶段性高潮"
                
                stages.append({
                    "stage_number": i + 1,
                    "name": self._get_stage_name(i, stage_rhythm),
                    "start_chapter": start_ch,
                    "end_chapter": end_ch,
                    "theme": self._get_stage_theme(i, stage_rhythm),
                    "climax_chapter": end_ch,
                    "climax_type": climax_type,
                    "outline": self._generate_stage_outline(start_ch, end_ch, stage_rhythm)
                })
                
                prev_ch = end_ch
            
            # 如果还有剩余章节，添加最终阶段
            if prev_ch < self.total_chapters:
                stages.append({
                    "stage_number": len(stages) + 1,
                    "name": "最终阶段：圆满落幕",
                    "start_chapter": prev_ch + 1,
                    "end_chapter": self.total_chapters,
                    "theme": "结局收尾，最终高潮",
                    "climax_chapter": self.total_chapters,
                    "climax_type": "最终大高潮",
                    "outline": self._generate_stage_outline(prev_ch + 1, self.total_chapters, stage_rhythm, is_final=True)
                })
        else:
            # 使用默认的阶段性节奏（每30章一个阶段）
            stages = self._calculate_default_stages(stage_interval)
        
        return stages
    
    def _calculate_default_stages(self, interval: int = 30) -> List[Dict]:
        """使用默认节奏计算阶段（当套路分析中没有节奏信息时）"""
        stages = []
        
        full_cycles = self.total_chapters // interval
        remainder = self.total_chapters % interval
        
        cycle_names = [
            "第一周期：崭露头角",
            "第二周期：快速发展", 
            "第三周期：声名鹊起",
            "第四周期：登顶巅峰"
        ]
        
        for i in range(full_cycles):
            start_ch = i * interval + 1
            end_ch = (i + 1) * interval
            
            stages.append({
                "stage_number": i + 1,
                "name": cycle_names[min(i, len(cycle_names) - 1)],
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "theme": self._get_cycle_theme(i),
                "climax_chapter": end_ch,
                "climax_type": f"第{i+1}次阶段性总结高潮",
                "outline": self._generate_stage_outline(start_ch, end_ch, {})
            })
        
        if remainder > 0:
            start_ch = full_cycles * interval + 1
            end_ch = self.total_chapters
            
            stages.append({
                "stage_number": full_cycles + 1,
                "name": "最终周期：圆满落幕",
                "start_chapter": start_ch,
                "end_chapter": end_ch,
                "theme": "结局收尾，最终高潮",
                "climax_chapter": end_ch,
                "climax_type": "最终大高潮",
                "outline": self._generate_stage_outline(start_ch, end_ch, {}, is_final=True)
            })
        
        return stages
    
    def _get_stage_name(self, stage_index: int, stage_rhythm: Dict) -> str:
        """获取阶段名称"""
        # 尝试从stage_rhythm中获取
        if 'stage_names' in stage_rhythm and stage_index < len(stage_rhythm['stage_names']):
            return stage_rhythm['stage_names'][stage_index]
        
        # 默认命名
        default_names = [
            "第一周期：崭露头角",
            "第二周期：快速发展", 
            "第三周期：声名鹊起",
            "第四周期：登顶巅峰"
        ]
        return default_names[min(stage_index, len(default_names) - 1)]
    
    def _get_stage_theme(self, stage_index: int, stage_rhythm: Dict) -> str:
        """获取阶段主题"""
        # 尝试从stage_rhythm中获取
        if 'stage_themes' in stage_rhythm and stage_index < len(stage_rhythm['stage_themes']):
            return stage_rhythm['stage_themes'][stage_index]
        
        # 根据早期/中期/后期返回不同主题
        early = stage_rhythm.get('early_stage', {})
        mid = stage_rhythm.get('mid_stage', {})
        late = stage_rhythm.get('late_stage', {})
        
        if stage_index == 0:
            return early.get('rhythm', '初入江湖，建立根基')
        elif stage_index == 1:
            return mid.get('rhythm', '快速发展，势力扩张')
        else:
            return late.get('rhythm', '登顶巅峰，制定规则')
    
    def _get_cycle_theme(self, cycle_index: int) -> str:
        """获取周期主题"""
        themes = [
            "初入江湖，建立根基",
            "快速发展，势力扩张",
            "名震一方，格局打开",
            "登顶巅峰，制定规则"
        ]
        return themes[min(cycle_index, len(themes) - 1)]
    
    def _generate_stage_outline(self, start: int, end: int, stage_rhythm: Dict, is_final: bool = False) -> List[Dict]:
        """
        生成阶段大纲 - 基于题材特定的阶段性节奏
        
        从stage_rhythm中获取该题材的节奏规律：
        - small_climax_interval: 小高潮间隔（默认3章）
        - medium_climax_interval: 中高潮间隔（默认10章）
        - large_climax_interval: 大高潮间隔（默认20章）
        """
        outline = []
        stage_length = end - start + 1
        
        # 获取节奏参数（带默认值）
        small_interval = stage_rhythm.get('small_climax_interval', 3)
        medium_interval = stage_rhythm.get('medium_climax_interval', 10)
        large_interval = stage_rhythm.get('large_climax_interval', 20)
        
        # 节奏标签映射
        rhythm_labels = stage_rhythm.get('rhythm_labels', {
            '3': '3章一小爽',
            '10': '10章一中爽',
            '20': '20章一大爽',
            '30': '阶段高潮'
        })
        
        for ch in range(start, end + 1):
            relative_ch = ch - start + 1  # 阶段内章节号
            
            # 章节1：开局
            if relative_ch == 1:
                outline.append({
                    "chapter": ch, 
                    "type": "开局", 
                    "emotion": "期待",
                    "event": "新阶段开始，设定目标",
                    "rhythm": "阶段开局"
                })
            # 大高潮（如第20章）
            elif relative_ch == large_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "大高潮", 
                    "emotion": "大爽快",
                    "event": "重大转折，实力飞跃",
                    "rhythm": rhythm_labels.get(str(large_interval), f"{large_interval}章一大爽")
                })
            # 中高潮（如第10章）
            elif relative_ch == medium_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "中高潮", 
                    "emotion": "爽快",
                    "event": "获得资源/身份升级",
                    "rhythm": rhythm_labels.get(str(medium_interval), f"{medium_interval}章一中爽")
                })
            # 小高潮（如第3章）
            elif relative_ch == small_interval:
                outline.append({
                    "chapter": ch, 
                    "type": "小高潮", 
                    "emotion": "小爽快",
                    "event": "第一次打脸，立威",
                    "rhythm": rhythm_labels.get(str(small_interval), f"{small_interval}章一小爽")
                })
            # 阶段最终章
            elif ch == end:
                if is_final:
                    outline.append({
                        "chapter": ch, 
                        "type": "最终高潮", 
                        "emotion": "爆发+满足",
                        "event": "最终决战，圆满结局",
                        "rhythm": "最终高潮"
                    })
                else:
                    outline.append({
                        "chapter": ch, 
                        "type": "阶段高潮", 
                        "emotion": "爆发+期待",
                        "event": "阶段性总结，开启新周期",
                        "rhythm": "阶段高潮"
                    })
            # 其他节奏点（如其他3的倍数）
            elif relative_ch % small_interval == 0:
                outline.append({
                    "chapter": ch, 
                    "type": "小爽点", 
                    "emotion": "爽快",
                    "event": "日常打脸/收获",
                    "rhythm": f"{small_interval}章节奏"
                })
            else:
                outline.append({
                    "chapter": ch, 
                    "type": "推进", 
                    "emotion": "期待",
                    "event": "剧情推进，蓄势",
                    "rhythm": "铺垫"
                })
        
        return outline
    

    
    def _get_outline_first_30(self) -> List[Dict]:
        """获取前30章大纲"""
        plan = self.novel_data.get('plan', {})
        return plan.get('outline_first_30', [])
    
    def _infer_stage_outline(self, start: int, end: int, stage_type: str) -> List[Dict]:
        """
        推断阶段大纲（基于套路模板）
        """
        outline = []
        
        # 节奏模板
        if stage_type == "承":
            # 发展阶段：每10章一个小高潮
            for ch in range(start, end + 1):
                pos = (ch - start) % 10
                if pos == 0:
                    outline.append({"chapter": ch, "type": "小高潮", "emotion": "爽快"})
                elif pos == 5:
                    outline.append({"chapter": ch, "type": "中高潮", "emotion": "震惊"})
                else:
                    outline.append({"chapter": ch, "type": "推进", "emotion": "期待"})
        
        elif stage_type == "转":
            # 高潮阶段：紧张升级
            for ch in range(start, end + 1):
                pos = (ch - start) % 10
                if pos == 0:
                    outline.append({"chapter": ch, "type": "大高潮", "emotion": "爆发"})
                else:
                    outline.append({"chapter": ch, "type": "紧张", "emotion": "危机"})
        
        else:  # 合
            # 结局阶段：满足收尾
            for ch in range(start, end + 1):
                if ch == end:
                    outline.append({"chapter": ch, "type": "结局", "emotion": "满足"})
                else:
                    outline.append({"chapter": ch, "type": "收尾", "emotion": "温馨"})
        
        return outline
    
    def generate_stage(self, stage: Dict, progress_callback=None) -> List[Dict]:
        """
        生成单个阶段的章节
        
        Args:
            stage: 阶段信息（包含start_chapter, end_chapter等）
            progress_callback: 进度回调(chapter_num, total)
        
        Returns:
            生成的章节列表
        """
        stage_num = stage['stage_number']
        start_ch = stage['start_chapter']
        end_ch = stage['end_chapter']
        total = end_ch - start_ch + 1
        
        logger.info(f"[阶段生成 {self.generator_id}] 开始生成阶段{stage_num}: 第{start_ch}-{end_ch}章 | {stage['name']}")
        
        # 创建新会话（每个阶段独立会话）
        self.current_stage = stage
        self.current_session = self._create_stage_session(stage)
        
        chapters = []
        prev_summary = ""
        
        for i, ch_num in enumerate(range(start_ch, end_ch + 1)):
            logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage_num} 第{ch_num}章 ({i+1}/{total})")
            
            try:
                chapter = self._generate_chapter_in_session(
                    chapter_num=ch_num,
                    stage=stage,
                    prev_summary=prev_summary
                )
                
                chapters.append(chapter)
                prev_summary = self._summarize_chapter(chapter)
                
                if progress_callback:
                    progress_callback(ch_num, self.total_chapters)
                
            except Exception as e:
                logger.error(f"[阶段生成 {self.generator_id}] 第{ch_num}章失败: {e}")
                chapters.append(self._create_error_chapter(ch_num, e))
        
        logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage_num}完成 | 成功: {len([c for c in chapters if c.get('word_count', 0) > 0])}/{total}")
        return chapters
    
    def _create_stage_session(self, stage: Dict) -> 'ConversationSession':
        """
        创建阶段会话
        system_prompt包含完整一阶段设定+本阶段详细规划
        """
        from src.core.APIClient import ConversationSession
        
        system_prompt = self._build_stage_system_prompt(stage)
        
        session = ConversationSession(
            api_client=self.api_client,
            system_prompt=system_prompt,
            provider="kimi",
            purpose_prefix=f"STAGE-{self.generator_id}-{stage['stage_number']}"
        )
        session.max_history = 50
        
        logger.info(f"[阶段生成 {self.generator_id}] 阶段{stage['stage_number']}会话创建 | 历史限制: 50")
        return session
    
    def _build_stage_system_prompt(self, stage: Dict) -> str:
        """
        构建阶段系统提示词
        包含：
        1. 完整一阶段设定（世界观、角色、成长路线）
        2. 本阶段详细规划（本阶段大纲、高潮设计）
        
        注意：使用从套路分析中提取的题材特定节奏参数
        """
        # 一阶段完整设定
        worldview = self.novel_data.get('core_worldview', {})
        faction_system = self.novel_data.get('faction_system', {})
        char_design = self.novel_data.get('character_design', {})
        growth_plan = self.novel_data.get('global_growth_plan', {})
        emotion_curve = self.novel_data.get('emotion_curve', [])
        
        # 本阶段规划
        stage_outline = stage.get('outline', [])
        
        # 获取主角当前阶段能力
        protagonist_current = self._get_protagonist_stage_status(stage)
        
        # 从套路分析中获取节奏参数
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        small_interval = stage_rhythm.get('small_climax_interval', 3)
        medium_interval = stage_rhythm.get('medium_climax_interval', 10)
        large_interval = stage_rhythm.get('large_climax_interval', 20)
        rhythm_description = stage_rhythm.get('description', '每30章一个完整周期')
        
        # 计算节奏节点
        small_climax = stage['start_chapter'] + small_interval - 1
        medium_climax = stage['start_chapter'] + medium_interval - 1
        large_climax = stage['start_chapter'] + large_interval - 1
        stage_climax = stage['end_chapter']
        
        return f"""# 角色：顶级网络小说作家

你正在为小说《{self.novel_title}》生成【{stage['name']}】的章节内容。
这是第{stage['stage_number']}阶段（第{stage['start_chapter']}-{stage['end_chapter']}章）。

---

## 📚 【一阶段完整设定 - 必须严格遵循】

### 世界观设定
```json
{json.dumps(worldview, ensure_ascii=False, indent=2)}
```

### 势力系统
```json
{json.dumps(faction_system, ensure_ascii=False, indent=2)}
```

### 角色设计
```json
{json.dumps(char_design, ensure_ascii=False, indent=2)}
```

### 成长路线
```json
{json.dumps(growth_plan, ensure_ascii=False, indent=2)}
```

---

## 🎯 【本阶段详细规划 - 第{stage['stage_number']}阶段】

### 阶段信息
- **阶段名称**：{stage['name']}
- **章节范围**：第{stage['start_chapter']}-{stage['end_chapter']}章
- **阶段目标**：{stage['theme']}
- **阶段高潮**：第{stage['climax_chapter']}章 - {stage['climax_type']}

### 题材节奏规律
- **节奏描述**：{rhythm_description}
- **小高潮间隔**：每{small_interval}章
- **中高潮间隔**：每{medium_interval}章
- **大高潮间隔**：每{large_interval}章

### 主角当前状态
```json
{json.dumps(protagonist_current, ensure_ascii=False, indent=2)}
```

### 本阶段节奏大纲（必须严格执行）
```json
{json.dumps(stage_outline, ensure_ascii=False, indent=2)}
```

---

## ✍️ 【爆款节奏写作规范 - 严格遵循{small_interval}-{medium_interval}-{large_interval}节奏】

### 固定高潮节点（不可更改）
1. **第{small_climax}章**：小高潮（打脸反派）💥
2. **第{medium_climax}章**：中高潮（资源/身份）💥💥
3. **第{large_climax}章**：大高潮（升级/转折）💥💥💥
4. **第{stage_climax}章**：阶段高潮（阶段性总结）🔥🔥🔥

### 写作要求
1. **每章2000-2500字**
2. **番茄风格**：短段落、多对话、快节奏
3. **情绪控制**：严格按照大纲的情绪设计
4. **节奏把控**：
   - 每{small_interval}章至少一次小爽点（打脸/收获）
   - 第{medium_interval}章必须达到中高潮
   - 第{large_interval}章必须达到大高潮
   - 第{stage_climax}章必须达到阶段高潮
5. **承上启下**：每章结尾必须留钩子

### 爽点设计原则
- **{small_interval}章节奏**：打脸→收获→装逼
- **{medium_interval}章节奏**：升级→震惊→新目标
- **{large_interval}章节奏**：转折→飞跃→新高度
- **阶段节奏**：总结→爆发→新阶段

---

## ⚠️ 【重要规则】

1. **节奏不可更改**：必须严格按照{small_interval}-{medium_interval}-{large_interval}的节奏节点设计剧情
2. **高潮必须到位**：每个高潮节点必须有对应的爽点事件
3. **情绪曲线**：严格按照情绪设计，不能偏离
4. **阶段衔接**：第{stage['end_chapter']}章结尾要为下一阶段做铺垫

等待第{stage['start_chapter']}章指令...
"""
    
    def _get_protagonist_stage_status(self, stage: Dict) -> Dict:
        """获取主角当前阶段状态 - 基于周期升级"""
        stage_num = stage['stage_number']
        
        # 从套路分析中获取节奏参数
        stage_rhythm = self.tropes.get('stage_rhythm', {})
        small_interval = stage_rhythm.get('small_climax_interval', 3)
        medium_interval = stage_rhythm.get('medium_climax_interval', 10)
        large_interval = stage_rhythm.get('large_climax_interval', 20)
        
        # 根据周期返回对应能力状态
        ability_levels = [
            "初入江湖，小有所成",
            "一方豪杰，声名鹊起", 
            "名震一方，实力强横",
            "天下闻名，无敌之姿"
        ]
        
        growth_goals = [
            "完成第一阶段目标，建立根基",
            "完成第二阶段目标，势力扩张",
            "完成第三阶段目标，格局打开",
            "完成最终阶段，登顶巅峰"
        ]
        
        # 计算节奏节点
        small_climax = stage['start_chapter'] + small_interval - 1
        medium_climax = stage['start_chapter'] + medium_interval - 1
        large_climax = stage['start_chapter'] + large_interval - 1
        
        return {
            "current_stage": f"第{stage_num}阶段",
            "ability_level": ability_levels[min(stage_num - 1, 3)],
            "stage_goal": growth_goals[min(stage_num - 1, 3)],
            "milestones": [
                f"第{stage['start_chapter']}章：阶段开始，设定目标",
                f"第{small_climax}章：第一次小高潮（打脸）",
                f"第{medium_climax}章：第一次中高潮（资源）",
                f"第{large_climax}章：第一次大高潮（升级）",
                f"第{stage['end_chapter']}章：阶段性总结高潮"
            ]
        }
    
    def _generate_chapter_in_session(self, chapter_num: int, stage: Dict, prev_summary: str) -> Dict:
        """在会话中生成单章"""
        # 获取本章大纲
        chapter_outline = self._get_chapter_outline(chapter_num, stage)
        
        # 构建提示词
        prompt = self._build_chapter_prompt(chapter_num, stage, chapter_outline, prev_summary)
        
        # 发送消息
        logger.info(f"[阶段生成 {self.generator_id}] 发送第{chapter_num}章提示词 | 历史: {len(self.current_session.messages)}条")
        response = self.current_session.send_message(prompt, temperature=0.7)
        logger.info(f"[阶段生成 {self.generator_id}] 接收第{chapter_num}章响应 | 轮次: {self.current_session.turn_count}")
        
        content = response if isinstance(response, str) else str(response)
        
        return {
            "chapter_number": chapter_num,
            "title": self._extract_title(content, chapter_outline),
            "content": content,
            "word_count": len(content),
            "stage": stage['stage_number'],
            "generated_at": datetime.now().isoformat()
        }
    
    def _get_chapter_outline(self, chapter_num: int, stage: Dict) -> Dict:
        """获取本章大纲"""
        for item in stage.get('outline', []):
            if item.get('chapter') == chapter_num:
                return item
        return {"chapter": chapter_num, "type": "推进", "emotion": "期待"}
    
    def _build_chapter_prompt(self, chapter_num: int, stage: Dict, outline: Dict, prev_summary: str) -> str:
        """构建章节提示词"""
        relative_ch = chapter_num - stage['start_chapter'] + 1  # 周期内章节号
        
        parts = [
            f"请生成第{chapter_num}章（第{stage['stage_number']}周期 第{relative_ch}章）。",
            "",
            f"## 本章定位",
            f"- 所在周期：{stage['name']}",
            f"- 章节类型：{outline.get('type', '推进')}",
            f"- 情绪要求：{outline.get('emotion', '期待')}",
        ]
        
        # 添加节奏标记
        if outline.get('rhythm'):
            parts.append(f"- 节奏节点：{outline['rhythm']}")
        
        # 添加事件描述（如果有）
        if outline.get('event'):
            parts.append(f"- 核心事件：{outline['event']}")
        parts.append("")
        
        # 距离高潮的提示
        climax_ch = stage['end_chapter']
        chapters_to_climax = climax_ch - chapter_num
        
        if chapter_num == climax_ch:
            parts.append(f"🔥 **【周期高潮】本章必须达到：{stage['climax_type']}**")
            parts.append(f"🔥 **这是本周期的终极高潮，必须爽到极致！**")
            parts.append("")
        elif chapters_to_climax == 5:
            parts.append(f"⚠️ **距离周期高潮还有5章，开始密集铺垫！**")
            parts.append("")
        elif chapters_to_climax == 10:
            parts.append(f"📈 **进入冲刺阶段，为周期高潮做最后准备！**")
            parts.append("")
        elif outline.get('type') == '小高潮':
            parts.append("💥 **【3章节点】本章是小高潮，必须有打脸/收获爽点！**")
            parts.append("")
        elif outline.get('type') == '中高潮':
            parts.append("💥💥 **【10章节点】本章是中高潮，必须有重大收获/身份升级！**")
            parts.append("")
        elif outline.get('type') == '大高潮':
            parts.append("💥💥💥 **【20章节点】本章是大高潮，必须有重大转折/实力飞跃！**")
            parts.append("")
        
        if prev_summary:
            parts.extend([
                "## 前文摘要（必须承接）",
                prev_summary[:300] + "...",
                ""
            ])
        
        parts.extend([
            "## 写作要求",
            f"1. 字数2000-2500字",
            f"2. 情绪严格遵循：{outline.get('emotion', '期待')}",
            f"3. 承接上文，推动剧情",
            f"4. 结尾留钩子",
            "",
            "直接输出章节正文。"
        ])
        
        return "\n".join(parts)
    
    def _extract_title(self, content: str, outline: Dict) -> str:
        """提取标题"""
        lines = content.strip().split('\n')
        if lines:
            first = lines[0].strip()
            if '第' in first and '章' in first:
                return first
        return f"第{outline.get('chapter', 0)}章"
    
    def _summarize_chapter(self, chapter: Dict) -> str:
        """章节摘要"""
        content = chapter.get('content', '')
        return content[:200] + "..." if len(content) > 200 else content
    
    def _create_error_chapter(self, chapter_num: int, error: Exception) -> Dict:
        """创建错误章节记录"""
        return {
            "chapter_number": chapter_num,
            "title": f"第{chapter_num}章（生成失败）",
            "content": f"生成失败: {str(error)}",
            "word_count": 0,
            "error": str(error)
        }


# 便捷函数
def generate_by_stages(api_client, novel_data: Dict, tropes: Dict,
                       progress_callback=None) -> Dict[int, List[Dict]]:
    """
    按阶段生成所有章节
    
    Returns:
        Dict[阶段号, 章节列表]
    """
    generator = StageChapterGenerator(api_client, novel_data, tropes)
    
    # 计算阶段
    stages = generator.calculate_stages()
    logger.info(f"[阶段生成] 共划分{len(stages)}个阶段")
    
    # 逐个阶段生成
    all_chapters = {}
    for stage in stages:
        chapters = generator.generate_stage(stage, progress_callback)
        all_chapters[stage['stage_number']] = chapters
    
    return all_chapters
