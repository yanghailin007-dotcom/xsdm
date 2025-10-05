# EventDrivenManager.py
from typing import Dict, List, Optional
import re


class EventDrivenManager:
    """事件执行器 - 专注重大事件和大事件的状态跟踪和执行"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.active_events = {}  # 活跃的重大事件和大事件
        self.event_history = []  # 已完成的事件历史
        self.event_triggers = {}  # 事件触发条件
        
    def update_from_stage_plan(self, stage_writing_plan: Dict):
        """从阶段写作计划中加载事件系统 - 简化版本，只处理重大事件和大事件"""
        if not stage_writing_plan:
            return
        
        # 只处理重大事件和大事件
        event_system = stage_writing_plan.get("event_system", {})
        
        # 初始化活跃事件
        self._initialize_active_events(event_system)
        
        # 设置事件触发条件
        self._setup_event_triggers(event_system)
        
        print(f"✓ 事件执行器已从阶段计划更新: {len(self.active_events)}个活跃事件")

    def get_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文 - 统一入口方法"""
        return self.get_chapter_event_context(chapter_number)

    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文 - 专注重大事件和大事件"""
        context = {
            "active_events": [],
            "event_progress": {},
            "event_tasks": [],
            "trigger_checkpoints": [],
            "event_chain_effects": []
        }
        
        # 如果没有活跃事件，尝试初始化
        if not self.active_events:
            self.initialize_event_system()
        
        # 如果还是没有事件，创建回退事件
        if not self.active_events:
            self._create_fallback_events(chapter_number)
        
        # 获取当前活跃的事件
        active_count = 0
        for event_name, event_data in self.active_events.items():
            if self._is_event_active(chapter_number, event_data):
                active_count += 1
                
                event_context = self._build_event_context(chapter_number, event_data)
                context["active_events"].append(event_context)
                
                # 计算事件进度
                progress = self._calculate_event_progress(chapter_number, event_data)
                context["event_progress"][event_name] = progress
                
                # 生成事件任务
                tasks = self._generate_event_tasks(chapter_number, event_data, progress)
                context["event_tasks"].extend(tasks)
        
        # 检查触发条件
        trigger_checkpoints = self._check_event_triggers(chapter_number)
        context["trigger_checkpoints"] = trigger_checkpoints
        
        # 计算事件链影响
        chain_effects = self._calculate_chain_effects(chapter_number)
        context["event_chain_effects"] = chain_effects
        
        print(f"📊 第{chapter_number}章事件上下文: {active_count}个活跃事件, {len(context['event_tasks'])}个任务")
        
        return context

    def generate_event_execution_prompt(self, chapter_number: int) -> str:
        """生成事件执行指导提示词 - 专注重大事件和大事件"""
        event_context = self.get_chapter_event_context(chapter_number)
        
        if not event_context["active_events"] and not event_context["trigger_checkpoints"]:
            return "# 🎯 事件执行指导\n\n本章暂无特定事件执行任务。"
        
        prompt_parts = ["# 🎯 事件执行指导"]
        
        # 按事件类型分组
        major_events = [e for e in event_context["active_events"] if e["type"] == "major_event"]
        big_events = [e for e in event_context["active_events"] if e["type"] == "big_event"]
        
        # 重大事件指导
        if major_events:
            prompt_parts.append("## 🚨 重大事件")
            for event in major_events:
                event_name = event.get("name", "未知事件")
                progress = event_context["event_progress"].get(event_name, {})
                
                prompt_parts.extend([
                    f"### {event_name}",
                    f"**目标**: {event.get('main_goal', '推进故事发展')}",
                    f"**当前重点**: {event.get('current_stage_focus', '推进事件发展')}",
                    f"**进度**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                    f"**关键时刻**:"
                ])
                
                # 处理关键时刻显示
                key_moments = event.get('key_moments', [])
                if key_moments:
                    for moment in key_moments:
                        if isinstance(moment, dict):
                            desc = moment.get('description', '未描述')
                            chap = moment.get('chapter', '?')
                            prompt_parts.append(f"- 第{chap}章: {desc}")
                        else:
                            prompt_parts.append(f"- {moment}")
                else:
                    prompt_parts.append("- 暂无关键时刻")
                
                prompt_parts.append("")  # 空行分隔
        
        # 大事件指导
        if big_events:
            prompt_parts.append("## 🔥 大事件")
            for event in big_events:
                event_name = event.get("name", "未知事件")
                progress = event_context["event_progress"].get(event_name, {})
                
                prompt_parts.extend([
                    f"### {event_name}",
                    f"**目标**: {event.get('main_goal', '推进故事发展')}",
                    f"**当前重点**: {event.get('current_stage_focus', '推进事件发展')}",
                    f"**进度**: {progress.get('stage', '未知阶段')} ({progress.get('ratio', 0)*100:.0f}%)",
                    f"**关联重大事件**: {event.get('connection_to_major', '独立事件')}"
                ])
                
                prompt_parts.append("")  # 空行分隔
        
        # 触发检查点
        if event_context["trigger_checkpoints"]:
            prompt_parts.append("## ⏰ 事件触发检查点")
            for checkpoint in event_context["trigger_checkpoints"]:
                prompt_parts.append(f"- **{checkpoint.get('trigger', '未知触发')}**: {checkpoint.get('description', '未指定描述')}")
        
        # 事件链影响
        if event_context["event_chain_effects"]:
            prompt_parts.append("## 🔗 事件链影响")
            for effect in event_context["event_chain_effects"]:
                prompt_parts.append(f"- {effect.get('description', '未指定影响')} (源于: {effect.get('source_event', '未知事件')})")
        
        # 事件任务
        if event_context["event_tasks"]:
            prompt_parts.append("## ✅ 本章事件任务")
            for task in event_context["event_tasks"]:
                priority_icon = "🔴" if task.get('priority') == 'critical' else "🟡" if task.get('priority') == 'high' else "🟢"
                prompt_parts.append(f"- {priority_icon} **{task.get('priority', '普通')}优先级**: {task.get('description', '未指定任务')}")
        
        return "\n".join(prompt_parts)

    def _initialize_active_events(self, event_system: Dict):
        """初始化活跃事件 - 只处理重大事件和大事件"""
        self.active_events.clear()
        
        # 添加重大事件
        for event in event_system.get("major_events", []):
            event_name = event.get("name")
            if event_name:
                self.active_events[event_name] = {
                    "name": event_name,
                    "type": "major_event",
                    "main_goal": event.get("main_goal", "推进故事发展"),
                    "start_chapter": event.get("start_chapter", 1),
                    "end_chapter": event.get("end_chapter", 10),
                    "key_moments": event.get("key_moments", []),
                    "character_roles": event.get("character_roles", {}),
                    "stage_focus": event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": event.get("start_chapter", 1),
                    "current_progress": 0,
                    "significance": event.get("significance", "重大转折点")
                }
        
        # 添加大事件
        for event in event_system.get("big_events", []):
            event_name = event.get("name")
            if event_name:
                self.active_events[event_name] = {
                    "name": event_name,
                    "type": "big_event",
                    "main_goal": event.get("main_goal", "推进故事发展"),
                    "start_chapter": event.get("start_chapter", 1),
                    "end_chapter": event.get("end_chapter", 10),
                    "key_moments": event.get("key_moments", []),
                    "character_roles": event.get("character_roles", {}),
                    "stage_focus": event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": event.get("start_chapter", 1),
                    "current_progress": 0,
                    "connection_to_major": event.get("connection_to_major", "独立事件")
                }
        
        print(f"✅ 初始化活跃事件: {len([e for e in self.active_events.values() if e['type'] == 'major_event'])}个重大事件, "
              f"{len([e for e in self.active_events.values() if e['type'] == 'big_event'])}个大事件")

    def _build_event_context(self, chapter_number: int, event_data: Dict) -> Dict:
        """构建事件上下文 - 专注重大事件和大事件"""
        progress = self._calculate_event_progress(chapter_number, event_data)
        
        # 处理关键时刻
        key_moments = []
        raw_moments = event_data.get("key_moments", [])
        
        for moment in raw_moments:
            if isinstance(moment, str):
                # 转换字符串格式为字典格式
                chapter_match = re.search(r'第(\d+)章', moment)
                moment_chapter = int(chapter_match.group(1)) if chapter_match else chapter_number
                key_moments.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            elif isinstance(moment, dict):
                key_moments.append({
                    "chapter": moment.get("chapter", chapter_number),
                    "description": moment.get("description", "未描述关键时刻"),
                    "preparation": moment.get("preparation", "正常推进")
                })
        
        # 构建事件上下文
        event_context = {
            "name": event_data.get("name", "未知事件"),
            "type": event_data.get("type", "big_event"),
            "main_goal": event_data.get("main_goal", "推进故事发展"),
            "current_stage_focus": self._get_current_stage_focus(progress.get("stage", "开局阶段"), event_data),
            "key_moments": key_moments,
            "character_roles": event_data.get("character_roles", {}),
            "progress": progress
        }
        
        # 添加特定字段
        if event_data["type"] == "major_event":
            event_context["significance"] = event_data.get("significance", "重大转折点")
        elif event_data["type"] == "big_event":
            event_context["connection_to_major"] = event_data.get("connection_to_major", "独立事件")
        
        return event_context

    def _calculate_event_progress(self, chapter_number: int, event_data: Dict) -> Dict:
        """计算事件进度 - 专注多章事件"""
        start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 1))
        end_chapter = event_data.get("end_chapter", chapter_number + 10)
        
        total_chapters = max(end_chapter - start_chapter + 1, 1)
        current_progress = max(min(chapter_number - start_chapter + 1, total_chapters), 0)
        progress_ratio = current_progress / total_chapters if total_chapters > 0 else 0
        
        # 确定阶段
        if progress_ratio <= 0.3:
            stage = "开局阶段"
        elif progress_ratio <= 0.6:
            stage = "发展阶段"
        elif progress_ratio <= 0.9:
            stage = "高潮阶段"
        else:
            stage = "收尾阶段"
        
        return {
            "current": current_progress,
            "total": total_chapters,
            "ratio": progress_ratio,
            "stage": stage
        }

    def _get_current_stage_focus(self, stage: str, event_data: Dict) -> str:
        """获取当前阶段的执行重点"""
        # 优先使用事件自定义的重点
        stage_focus = event_data.get("stage_focus", {})
        if isinstance(stage_focus, dict):
            custom_focus = stage_focus.get(stage)
            if custom_focus:
                return custom_focus
        
        # 默认阶段重点映射
        focus_map = {
            "开局阶段": "建立事件基础，引入核心冲突",
            "发展阶段": "深化矛盾，推进事件目标", 
            "高潮阶段": "冲突激化，关键转折",
            "收尾阶段": "解决冲突，展示后果"
        }
        
        return focus_map.get(stage, "推进事件发展")

    def _setup_event_triggers(self, event_system: Dict):
        """设置事件触发条件 - 只处理重大事件和大事件"""
        self.event_triggers.clear()
        
        # 为重大事件和大事件设置触发条件
        all_events = []
        all_events.extend(event_system.get("major_events", []))
        all_events.extend(event_system.get("big_events", []))
        
        for event in all_events:
            event_name = event.get("name")
            if not event_name:
                continue
                
            # 检查是否有自定义触发条件
            trigger_condition = event.get("trigger_condition")
            if trigger_condition:
                self.event_triggers[event_name] = {
                    "condition": trigger_condition,
                    "event_data": event
                }
            # 如果没有明确触发条件，使用章节触发
            elif "start_chapter" in event:
                trigger_chapter = event.get("start_chapter")
                if trigger_chapter:
                    self.event_triggers[event_name] = {
                        "condition": {
                            "type": "chapter",
                            "chapter": trigger_chapter
                        },
                        "event_data": event
                    }

    def _is_event_active(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否活跃"""
        if event_data.get("status") != "active":
            return False
        
        # 重大事件和大事件都是多章事件
        start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 0))
        end_chapter = event_data.get("end_chapter", chapter_number + 100)
        
        return start_chapter <= chapter_number <= end_chapter

    def initialize_event_system(self):
        """初始化事件系统 - 从当前正确阶段加载重大事件和大事件"""
        print("🎯 初始化事件系统...")
        
        novel_data = self.generator.novel_data
        
        # 获取当前章节
        current_chapter = len(novel_data["generated_chapters"]) + 1
        
        # 从当前章节所属的阶段加载事件系统
        current_stage = self._get_current_stage_from_plans(current_chapter)
        if current_stage:
            print(f"✅ 当前阶段: {current_stage}")
            
            if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
                if current_stage in novel_data["stage_writing_plans"]:
                    stage_data = novel_data["stage_writing_plans"][current_stage]
                    
                    if ("stage_writing_plan" in stage_data and 
                        "event_system" in stage_data["stage_writing_plan"]):
                        
                        event_system = stage_data["stage_writing_plan"]["event_system"]
                        print(f"✅ 从当前阶段 {current_stage} 加载事件系统")
                        
                        # 更新到事件执行器
                        self.update_from_stage_plan({"event_system": event_system})
                        return
        
        # 如果找不到当前阶段，尝试从所有阶段中查找
        print("🔍 尝试从所有阶段查找适合当前章节的事件...")
        if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
            for stage_name, stage_data in novel_data["stage_writing_plans"].items():
                if self._is_chapter_in_stage(current_chapter, stage_data):
                    print(f"✅ 发现阶段 {stage_name} 包含第{current_chapter}章")
                    
                    if ("stage_writing_plan" in stage_data and 
                        "event_system" in stage_data["stage_writing_plan"]):
                        
                        event_system = stage_data["stage_writing_plan"]["event_system"]
                        print(f"✅ 从阶段 {stage_name} 加载事件系统")
                        
                        self.update_from_stage_plan({"event_system": event_system})
                        return
        
        # 如果还是找不到，使用第一个可用的阶段
        if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
            first_stage = list(novel_data["stage_writing_plans"].keys())[0]
            stage_data = novel_data["stage_writing_plans"][first_stage]
            
            if ("stage_writing_plan" in stage_data and 
                "event_system" in stage_data["stage_writing_plan"]):
                
                event_system = stage_data["stage_writing_plan"]["event_system"]
                print(f"⚠️ 使用第一个可用阶段 {first_stage} 的事件系统")
                
                self.update_from_stage_plan({"event_system": event_system})
                return
        
        print("⚠️ 没有可用的阶段写作计划或事件系统")
        # 创建回退事件确保系统能工作
        self._create_fallback_events(current_chapter)

    def _get_current_stage_from_plans(self, chapter_number: int) -> str:
        """从阶段计划中获取当前章节所属的阶段"""
        novel_data = self.generator.novel_data
        
        # 从 overall_stage_plans 中查找
        if "overall_stage_plans" in novel_data and "overall_stage_plan" in novel_data["overall_stage_plans"]:
            overall_plan = novel_data["overall_stage_plans"]["overall_stage_plan"]
            
            for stage_name, stage_info in overall_plan.items():
                chapter_range = stage_info.get("chapter_range", "")
                if self._is_chapter_in_range(chapter_number, chapter_range):
                    return stage_name
        
        # 从 stage_writing_plans 中推断
        if "stage_writing_plans" in novel_data:
            for stage_name, stage_data in novel_data["stage_writing_plans"].items():
                if self._is_chapter_in_stage(chapter_number, stage_data):
                    return stage_name
        
        return "未知阶段"

    def _is_chapter_in_stage(self, chapter_number: int, stage_data: Dict) -> bool:
        """检查章节是否在阶段范围内"""
        chapter_range = ""
        
        if "stage_writing_plan" in stage_data:
            writing_plan = stage_data["stage_writing_plan"]
            chapter_range = writing_plan.get("chapter_range", "")
        else:
            chapter_range = stage_data.get("chapter_range", "")
        
        return self._is_chapter_in_range(chapter_number, chapter_range)

    def _is_chapter_in_range(self, chapter_number: int, chapter_range: str) -> bool:
        """检查章节是否在范围内"""
        if not chapter_range:
            return False
        
        try:
            numbers = re.findall(r'\d+', chapter_range)
            if len(numbers) >= 2:
                start_chapter = int(numbers[0])
                end_chapter = int(numbers[1])
                return start_chapter <= chapter_number <= end_chapter
            elif len(numbers) == 1:
                single_chapter = int(numbers[0])
                return chapter_number == single_chapter
        except Exception as e:
            print(f"❌ 解析章节范围失败: {chapter_range}, 错误: {e}")
        
        return False

    def _generate_event_tasks(self, chapter_number: int, event_data: Dict, progress: Dict) -> List[Dict]:
        """生成事件执行任务"""
        tasks = []
        event_name = event_data.get("name", "未知事件")
        event_type = event_data.get("type", "big_event")
        
        # 基于事件阶段生成任务
        current_stage = progress.get("stage", "开局阶段")
        
        if current_stage == "开局阶段":
            tasks.append({
                "event": event_name,
                "description": f"建立{event_type}基础设定和初始冲突",
                "priority": "high",
                "type": "setup"
            })
        elif current_stage == "发展阶段":
            tasks.append({
                "event": event_name,
                "description": f"深化{event_type}矛盾，推进核心目标",
                "priority": "high",
                "type": "development"
            })
        elif current_stage == "高潮阶段":
            tasks.append({
                "event": event_name,
                "description": f"处理{event_type}高潮和关键转折",
                "priority": "critical",
                "type": "climax"
            })
        else:  # 收尾阶段
            tasks.append({
                "event": event_name,
                "description": f"解决{event_type}冲突，处理后续影响",
                "priority": "medium",
                "type": "resolution"
            })
        
        # 添加特定关键时刻的任务
        upcoming_moments = self._get_upcoming_key_moments(chapter_number, event_data)
        for moment in upcoming_moments:
            if moment.get("chapter") == chapter_number:
                tasks.append({
                    "event": event_name,
                    "description": f"处理关键时刻: {moment.get('description', '未描述')}",
                    "priority": "critical",
                    "type": "key_moment"
                })
        
        return tasks

    def _get_upcoming_key_moments(self, chapter_number: int, event_data: Dict) -> List[Dict]:
        """获取即将到来的关键时刻"""
        key_moments = event_data.get("key_moments", [])
        upcoming = []
        
        for moment in key_moments:
            if isinstance(moment, str):
                chapter_match = re.search(r'第(\d+)章', moment)
                if chapter_match:
                    moment_chapter = int(chapter_match.group(1))
                else:
                    moment_chapter = chapter_number + 1
                
                upcoming.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            
            elif isinstance(moment, dict):
                moment_chapter = moment.get("chapter", 0)
                if moment_chapter >= chapter_number and moment_chapter <= chapter_number + 3:
                    upcoming.append({
                        "chapter": moment_chapter,
                        "description": moment.get("description", ""),
                        "preparation": moment.get("preparation", "正常推进")
                    })
        
        return upcoming

    def _check_event_triggers(self, chapter_number: int) -> List[Dict]:
        """检查事件触发条件"""
        checkpoints = []
        
        for event_name, trigger_data in self.event_triggers.items():
            condition = trigger_data.get("condition", {})
            event_data = trigger_data.get("event_data", {})
            
            # 简单的章节触发检查
            if condition.get("type") == "chapter":
                trigger_chapter = condition.get("chapter", 0)
                if chapter_number == trigger_chapter:
                    checkpoints.append({
                        "trigger": f"章节触发: 第{chapter_number}章",
                        "description": f"可能触发事件: {event_name}",
                        "event": event_name,
                        "condition": condition
                    })
            
            # 前置事件完成触发
            elif condition.get("type") == "event_completion":
                prerequisite = condition.get("prerequisite_event")
                if self._is_prerequisite_met(prerequisite):
                    checkpoints.append({
                        "trigger": f"事件完成触发: {prerequisite}",
                        "description": f"可能触发事件: {event_name}",
                        "event": event_name,
                        "condition": condition
                    })
        
        return checkpoints

    def _is_prerequisite_met(self, prerequisite_event: str) -> bool:
        """检查前置事件条件是否满足"""
        for history_event in self.event_history:
            if history_event.get("name") == prerequisite_event and history_event.get("status") == "completed":
                return True
        return False

    def _calculate_chain_effects(self, chapter_number: int) -> List[Dict]:
        """计算事件链影响"""
        effects = []
        
        # 检查已完成事件对当前的影响
        for history_event in self.event_history[-5:]:  # 最近5个事件
            if history_event.get("aftermath_effects"):
                for effect in history_event["aftermath_effects"]:
                    if effect.get("duration", chapter_number) >= chapter_number:
                        effects.append({
                            "source_event": history_event.get("name", "未知事件"),
                            "description": effect.get("description", "未描述影响"),
                            "impact_level": effect.get("impact", "medium")
                        })
        
        return effects

    def _create_fallback_events(self, chapter_number: int):
        """创建回退事件 - 只创建重大事件和大事件"""
        print("🔄 创建回退事件...")
        
        # 创建一个重大事件
        major_event = {
            "name": "核心剧情推进",
            "type": "major_event",
            "main_goal": "推进主线故事发展",
            "start_chapter": max(1, chapter_number - 2),
            "end_chapter": chapter_number + 8,
            "key_moments": [
                f"第{chapter_number + 2}章: 关键发展点",
                f"第{chapter_number + 5}章: 重要转折"
            ],
            "status": "active",
            "started_chapter": max(1, chapter_number - 2),
            "current_progress": 0,
            "significance": "推动故事核心发展"
        }
        
        # 创建一个大事件
        big_event = {
            "name": "重要支线发展",
            "type": "big_event", 
            "main_goal": "发展支线情节",
            "start_chapter": chapter_number,
            "end_chapter": chapter_number + 5,
            "key_moments": [
                f"第{chapter_number + 1}章: 支线起始",
                f"第{chapter_number + 3}章: 支线发展"
            ],
            "status": "active",
            "started_chapter": chapter_number,
            "current_progress": 0,
            "connection_to_major": "补充主线情节"
        }
        
        self.active_events[major_event["name"]] = major_event
        self.active_events[big_event["name"]] = big_event
        
        print(f"✅ 创建回退事件完成: 1个重大事件, 1个大事件")

    def update_event_system(self):
        """更新事件系统 - 由NovelGenerator调用"""
        print("🔄 EventDrivenManager: 更新事件系统")
        self.active_events.clear()
        print("  ✅ 已清除所有旧事件")

    def add_event(self, name: str, event_type: str, start_chapter: int, description: str = "", impact_level: str = "medium"):
        """添加新事件 - 只支持重大事件和大事件"""
        if event_type not in ["major_event", "big_event"]:
            print(f"❌ 不支持的事件类型: {event_type} {name} {description}，只支持 major_event 和 big_event")
            return
            
        event = {
            "name": name,
            "type": event_type,
            "start_chapter": start_chapter,
            "started_chapter": start_chapter,
            "description": description,
            "impact_level": impact_level,
            "status": "active",
            "current_progress": 0,
            "key_moments": [],
            "main_goal": description or "推进故事发展"
        }
        
        # 设置默认结束章节
        if event_type == "major_event":
            event["end_chapter"] = start_chapter + 10
            event["significance"] = "重大转折点"
        else:  # big_event
            event["end_chapter"] = start_chapter + 5
            event["connection_to_major"] = "关联主线情节"
        
        self.active_events[name] = event
        print(f"  ✅ 添加{event_type}: {name} (起始章节: {start_chapter})")