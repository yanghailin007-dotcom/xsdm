# EventDrivenManager.py
from typing import Dict, List, Optional
import re


class EventDrivenManager:
    """事件执行器 - 专注事件状态跟踪和章节事件上下文（事件执行）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.active_events = {}  # 正在执行的事件
        self.event_history = []  # 已完成的事件历史
        self.event_triggers = {}  # 事件触发条件
        
    def update_from_stage_plan(self, stage_writing_plan: Dict):
        """从阶段写作计划中加载事件系统 - 修复版本"""
        if not stage_writing_plan:
            return
        
        # 修复：使用正确的字段名 "event_system"
        event_system = stage_writing_plan.get("event_system", {})
        
        # 初始化活跃事件
        self._initialize_active_events(event_system)
        
        # 设置事件触发条件
        self._setup_event_triggers(event_system)
        
        print(f"✓ 事件执行器已从阶段计划更新: {len(self.active_events)}个活跃事件")

    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文"""
        context = {
            "active_events": [],
            "event_progress": {},
            "event_tasks": [],
            "trigger_checkpoints": [],
            "event_chain_effects": []
        }
        
        # 获取当前活跃的事件
        for event_name, event_data in self.active_events.items():
            if self._is_event_active(chapter_number, event_data):
                event_context = self._build_event_context(chapter_number, event_data)
                context["active_events"].append(event_context)
                
                # 计算事件进度
                progress = self._calculate_event_progress(chapter_number, event_data)
                context["event_progress"][event_name] = progress
                
                # 生成事件任务
                tasks = self._generate_event_tasks(chapter_number, event_data, progress)
                context["event_tasks"].extend(tasks)
        
        # 检查触发条件
        context["trigger_checkpoints"] = self._check_event_triggers(chapter_number)
        
        # 计算事件链影响
        context["event_chain_effects"] = self._calculate_chain_effects(chapter_number)
        
        return context

    def process_chapter_events(self, chapter_number: int, chapter_content: Dict) -> Dict:
        """处理章节事件执行结果"""
        event_results = {
            "completed_events": [],
            "triggered_events": [],
            "character_effects": [],
            "faction_effects": [],
            "ability_effects": []
        }
        
        # 检查事件完成
        for event_name, event_data in list(self.active_events.items()):
            if self._is_event_completed(chapter_number, event_data):
                completed_event = self._complete_event(event_name, event_data, chapter_content)
                event_results["completed_events"].append(completed_event)
        
        # 处理事件触发
        triggered = self._process_event_triggers(chapter_number, chapter_content)
        event_results["triggered_events"].extend(triggered)
        
        # 计算事件影响
        effects = self._calculate_event_effects(chapter_number, chapter_content)
        event_results.update(effects)
        
        return event_results

    def generate_event_execution_prompt(self, chapter_number: int) -> str:
        """生成事件执行指导提示词"""
        event_context = self.get_chapter_event_context(chapter_number)
        
        if not event_context["active_events"] and not event_context["trigger_checkpoints"]:
            return "# 🎯 事件执行指导\n\n本章暂无特定事件执行任务。"
        
        prompt_parts = ["\n\n# 🎯 事件执行指导"]
        
        # 活跃事件指导
        if event_context["active_events"]:
            prompt_parts.append("## 活跃事件执行")
            
            for event in event_context["active_events"]:
                progress = event_context["event_progress"][event["name"]]
                prompt_parts.extend([
                    f"### {event['name']} ({progress['stage']})",
                    f"**事件目标**: {event['main_goal']}",
                    f"**当前进度**: {progress['current']}/{progress['total']}章",
                    f"**本章重点**: {event['current_stage_focus']}",
                    f"**关键任务**:"
                ])
                
                # 添加具体任务
                for task in event_context["event_tasks"]:
                    if task["event"] == event["name"]:
                        prompt_parts.append(f"- {task['description']} ({task['priority']}优先级)")
        
        # 触发检查点
        if event_context["trigger_checkpoints"]:
            prompt_parts.append("## 事件触发检查点")
            for checkpoint in event_context["trigger_checkpoints"]:
                prompt_parts.append(f"- **{checkpoint['trigger']}**: {checkpoint['description']}")
        
        # 事件链影响
        if event_context["event_chain_effects"]:
            prompt_parts.append("## 事件链影响")
            for effect in event_context["event_chain_effects"]:
                prompt_parts.append(f"- {effect['description']} (源于: {effect['source_event']})")
        
        return "\n".join(prompt_parts)

    def _initialize_active_events(self, event_system: Dict):
        """初始化活跃事件 - 支持新的事件结构"""
        self.active_events.clear()
        
        # 添加重大事件
        for event in event_system.get("major_events", []):
            self.active_events[event["name"]] = {
                **event,
                "status": "active",
                "started_chapter": event["start_chapter"],
                "current_progress": 0
            }
        
        # 添加大事件
        for event in event_system.get("big_events", []):
            self.active_events[event["name"]] = {
                **event,
                "status": "active",
                "started_chapter": event["start_chapter"],
                "current_progress": 0
            }
        
        # 添加普通事件
        for event in event_system.get("events", []):
            self.active_events[event["name"]] = {
                **event,
                "status": "active",
                "started_chapter": event["chapter"],  # 普通事件只有单章
                "current_progress": 0
            }

    def _setup_event_triggers(self, event_system: Dict):
        """设置事件触发条件 - 支持新的事件结构"""
        self.event_triggers.clear()
        
        # 为所有类型的事件设置触发条件
        all_events = []
        all_events.extend(event_system.get("major_events", []))
        all_events.extend(event_system.get("big_events", []))
        all_events.extend(event_system.get("events", []))
        
        for event in all_events:
            # 检查是否有自定义触发条件
            trigger_condition = event.get("trigger_condition")
            if trigger_condition:
                self.event_triggers[event["name"]] = {
                    "condition": trigger_condition,
                    "event_data": event
                }
            # 如果没有明确触发条件，使用章节触发
            elif "start_chapter" in event or "chapter" in event:
                trigger_chapter = event.get("start_chapter", event.get("chapter"))
                if trigger_chapter:
                    self.event_triggers[event["name"]] = {
                        "condition": {
                            "type": "chapter",
                            "chapter": trigger_chapter
                        },
                        "event_data": event
                    }

    def _is_event_active(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否活跃 - 支持新的事件类型"""
        if event_data["status"] != "active":
            return False
        
        # 处理不同类型的事件
        if "start_chapter" in event_data and "end_chapter" in event_data:
            # 主要事件和大事件
            start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 0))
            end_chapter = event_data.get("end_chapter", chapter_number + 100)
            return start_chapter <= chapter_number <= end_chapter
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data["chapter"]
            return chapter_number == event_chapter
        else:
            # 默认处理
            start_chapter = event_data.get("started_chapter", 0)
            return chapter_number >= start_chapter

    def get_context(self, chapter_number: int) -> Dict:
        """获取章节的事件上下文"""
        return self.get_chapter_event_context(chapter_number)
    
    def initialize_event_system(self):
        """初始化事件系统"""
        print("🎯 初始化事件系统...")
        
        # 从 novel_data 中获取事件系统数据
        novel_data = self.generator.novel_data
        
        # 如果有阶段写作计划，从中提取事件系统
        if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
            # 遍历所有阶段，寻找事件系统数据
            for stage_name, stage_data in novel_data["stage_writing_plans"].items():
                if "stage_writing_plan" in stage_data and "event_system" in stage_data["stage_writing_plan"]:
                    event_system = stage_data["stage_writing_plan"]["event_system"]
                    self.update_from_stage_plan({"event_system": event_system})
                    print(f"✅ 从{stage_name}阶段计划初始化事件系统: {len(self.active_events)}个活跃事件")
                    return
            
            # 如果没有找到事件系统，尝试从第一个阶段的写作计划中提取其他可用信息
            first_stage = next(iter(novel_data["stage_writing_plans"].values()))
            if first_stage and "stage_writing_plan" in first_stage:
                # 尝试从主要事件中提取
                if "event_system" in first_stage["stage_writing_plan"]:
                    event_system = first_stage["stage_writing_plan"]["event_system"]
                    self.update_from_stage_plan({"event_system": event_system})
                    print(f"✅ 从阶段计划初始化事件系统: {len(self.active_events)}个活跃事件")
                    return
        
        # 如果没有阶段计划，尝试从全局成长计划中提取
        if "global_growth_plan" in novel_data and novel_data["global_growth_plan"]:
            self._initialize_from_growth_plan(novel_data["global_growth_plan"])
            print(f"✅ 从成长计划初始化事件系统: {len(self.active_events)}个活跃事件")
            return
        
        print("⚠️ 没有可用的事件系统数据，事件系统保持为空")

    def _initialize_from_growth_plan(self, growth_plan: Dict):
        """从全局成长计划中初始化事件系统"""
        # 创建基础的事件系统结构
        event_system = {
            "major_events": [],
            "big_events": [],
            "events": []
        }
        
        # 从阶段框架中提取重大事件
        for stage in growth_plan.get("stage_framework", []):
            event_name = f"{stage['stage_name']}核心事件"
            event_system["major_events"].append({
                "name": event_name,
                "type": "stage_core",
                "main_goal": stage.get("core_objectives", ["推进故事发展"])[0],
                "start_chapter": self._parse_chapter_start(stage["chapter_range"]),
                "end_chapter": self._parse_chapter_end(stage["chapter_range"]),
                "key_moments": [
                    {
                        "chapter": self._parse_chapter_start(stage["chapter_range"]) + 3,
                        "description": f"{stage['stage_name']}关键发展",
                        "purpose": "推动事件进展"
                    }
                ]
            })
        
        self.update_from_stage_plan({"event_system": event_system})

    def _is_event_completed(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否完成 - 支持新的事件类型"""
        if event_data["status"] != "active":
            return False
        
        # 处理不同类型的事件
        if "end_chapter" in event_data:
            # 主要事件和大事件
            end_chapter = event_data.get("end_chapter", chapter_number)
            return chapter_number >= end_chapter
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data["chapter"]
            return chapter_number > event_chapter  # 在事件章节之后完成
        else:
            # 默认处理
            return False

    def _build_event_context(self, chapter_number: int, event_data: Dict) -> Dict:
        """构建事件上下文 - 修复关键时刻处理"""
        progress = self._calculate_event_progress(chapter_number, event_data)
        
        # 确保关键时刻是标准格式
        key_moments = []
        for moment in event_data.get("key_moments", []):
            if isinstance(moment, str):
                # 转换字符串格式为字典格式
                chapter_match = re.search(r'第(\d+)章', moment)
                moment_chapter = int(chapter_match.group(1)) if chapter_match else chapter_number
                key_moments.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            else:
                key_moments.append(moment)
        
        return {
            "name": event_data["name"],
            "type": event_data["type"],
            "main_goal": event_data["main_goal"],
            "current_stage_focus": self._get_current_stage_focus(progress["stage"], event_data),
            "key_moments": key_moments,  # 使用标准化后的关键时刻
            "character_roles": event_data.get("character_roles", {}),
            "progress": progress
        }
    
    def _calculate_event_progress(self, chapter_number: int, event_data: Dict) -> Dict:
        """计算事件进度"""
        # 处理不同类型的事件
        if "start_chapter" in event_data and "end_chapter" in event_data:
            # 主要事件和大事件
            start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 1))
            end_chapter = event_data.get("end_chapter", chapter_number)
            
            total_chapters = end_chapter - start_chapter + 1
            current_progress = chapter_number - start_chapter + 1
            progress_ratio = current_progress / total_chapters
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data["chapter"]
            if chapter_number < event_chapter:
                current_progress = 0
                total_chapters = 1
                progress_ratio = 0
            elif chapter_number == event_chapter:
                current_progress = 1
                total_chapters = 1
                progress_ratio = 1
            else:
                current_progress = 1
                total_chapters = 1
                progress_ratio = 1
        else:
            # 默认处理
            current_progress = 1
            total_chapters = 1
            progress_ratio = 1
        
        # 确定阶段
        if progress_ratio <= 0.3:
            stage = "开局阶段"
        elif progress_ratio <= 0.6:
            stage = "发展阶段"
        elif progress_ratio <= 0.8:
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
        focus_map = {
            "开局阶段": "建立事件基础，引入核心冲突",
            "发展阶段": "深化矛盾，推进事件目标",
            "高潮阶段": "冲突激化，关键转折",
            "收尾阶段": "解决冲突，展示后果"
        }
        
        # 优先使用事件自定义的重点
        custom_focus = event_data.get("stage_focus", {}).get(stage)
        if custom_focus:
            return custom_focus
        
        return focus_map.get(stage, "推进事件发展")

    def _get_upcoming_key_moments(self, chapter_number: int, event_data: Dict) -> List[Dict]:
        """获取即将到来的关键时刻 - 修复字符串格式处理"""
        key_moments = event_data.get("key_moments", [])
        upcoming = []
        
        for moment in key_moments:
            # 处理字符串格式的关键时刻（如你的示例数据）
            if isinstance(moment, str):
                # 从字符串中提取章节号
                chapter_match = re.search(r'第(\d+)章', moment)
                if chapter_match:
                    moment_chapter = int(chapter_match.group(1))
                else:
                    # 如果没有明确的章节号，使用默认逻辑
                    moment_chapter = chapter_number + 1
                
                # 创建标准化的关键时刻字典
                upcoming.append({
                    "chapter": moment_chapter,
                    "description": moment,
                    "preparation": "正常推进"
                })
            
            # 处理字典格式的关键时刻
            elif isinstance(moment, dict):
                moment_chapter = moment.get("chapter", 0)
                if moment_chapter >= chapter_number and moment_chapter <= chapter_number + 3:
                    upcoming.append({
                        "chapter": moment_chapter,
                        "description": moment.get("description", ""),
                        "preparation": moment.get("preparation", "正常推进")
                    })
        
        return upcoming

    def _generate_event_tasks(self, chapter_number: int, event_data: Dict, progress: Dict) -> List[Dict]:
        """生成事件执行任务"""
        tasks = []
        event_name = event_data["name"]
        
        # 基于事件阶段生成任务
        if progress["stage"] == "开局阶段":
            tasks.append({
                "event": event_name,
                "description": "建立事件基础设定和初始冲突",
                "priority": "high",
                "type": "setup"
            })
        elif progress["stage"] == "发展阶段":
            tasks.append({
                "event": event_name,
                "description": "深化事件矛盾，推进核心目标",
                "priority": "high",
                "type": "development"
            })
        elif progress["stage"] == "高潮阶段":
            tasks.append({
                "event": event_name,
                "description": "处理事件高潮和关键转折",
                "priority": "critical",
                "type": "climax"
            })
        else:  # 收尾阶段
            tasks.append({
                "event": event_name,
                "description": "解决事件冲突，处理后续影响",
                "priority": "medium",
                "type": "resolution"
            })
        
        # 添加特定关键时刻的任务
        upcoming_moments = self._get_upcoming_key_moments(chapter_number, event_data)
        for moment in upcoming_moments:
            if moment["chapter"] == chapter_number:
                tasks.append({
                    "event": event_name,
                    "description": f"处理关键时刻: {moment['description']}",
                    "priority": "critical",
                    "type": "key_moment"
                })
        
        return tasks

    def _check_event_triggers(self, chapter_number: int) -> List[Dict]:
        """检查事件触发条件"""
        checkpoints = []
        
        for event_name, trigger_data in self.event_triggers.items():
            condition = trigger_data["condition"]
            event_data = trigger_data["event_data"]
            
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
            if history_event["name"] == prerequisite_event and history_event["status"] == "completed":
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
                            "source_event": history_event["name"],
                            "description": effect["description"],
                            "impact_level": effect.get("impact", "medium")
                        })
        
        return effects

    def _complete_event(self, event_name: str, event_data: Dict, chapter_content: Dict) -> Dict:
        """完成事件处理"""
        completed_event = {
            "name": event_name,
            "type": event_data["type"],
            "completed_chapter": chapter_content["chapter_number"],
            "status": "completed",
            "outcomes": self._extract_event_outcomes(event_data, chapter_content),
            "aftermath_effects": event_data.get("aftermath", [])
        }
        
        # 移动到历史记录
        self.event_history.append(completed_event)
        del self.active_events[event_name]
        
        # 处理事件完成触发
        self._process_completion_triggers(event_name)
        
        return completed_event

    def _extract_event_outcomes(self, event_data: Dict, chapter_content: Dict) -> List[str]:
        """提取事件结果"""
        outcomes = []
        
        # 从事件数据中提取预期结果
        if "sub_goals" in event_data:
            outcomes.extend(event_data["sub_goals"])
        
        # 从章节内容中提取实际结果
        if "key_events" in chapter_content:
            outcomes.extend(chapter_content["key_events"])
        
        return outcomes

    def _process_completion_triggers(self, completed_event: str):
        """处理事件完成触发"""
        for event_name, trigger_data in list(self.event_triggers.items()):
            condition = trigger_data["condition"]
            if (condition.get("type") == "event_completion" and 
                condition.get("prerequisite_event") == completed_event):
                
                # 触发新事件
                event_data = trigger_data["event_data"]
                self.active_events[event_name] = {
                    **event_data,
                    "status": "active",
                    "started_chapter": self.generator.current_chapter + 1,  # 下一章开始
                    "current_progress": 0
                }
                
                print(f"  🔄 事件'{completed_event}'完成，触发新事件: {event_name}")

    def _process_event_triggers(self, chapter_number: int, chapter_content: Dict) -> List[Dict]:
        """处理事件触发"""
        triggered_events = []
        
        for event_name, trigger_data in list(self.event_triggers.items()):
            if self._check_trigger_condition(trigger_data["condition"], chapter_number, chapter_content):
                event_data = trigger_data["event_data"]
                
                # 激活事件
                self.active_events[event_name] = {
                    **event_data,
                    "status": "active",
                    "started_chapter": chapter_number,
                    "current_progress": 0
                }
                
                triggered_events.append({
                    "name": event_name,
                    "trigger_chapter": chapter_number,
                    "trigger_condition": trigger_data["condition"]
                })
                
                # 移除已触发的条件
                del self.event_triggers[event_name]
        
        return triggered_events

    def _check_trigger_condition(self, condition: Dict, chapter_number: int, chapter_content: Dict) -> bool:
        """检查触发条件是否满足"""
        condition_type = condition.get("type")
        
        if condition_type == "chapter":
            return chapter_number == condition.get("chapter", 0)
        
        elif condition_type == "content_based":
            # 基于章节内容的条件检查
            required_elements = condition.get("required_elements", [])
            return self._check_content_elements(required_elements, chapter_content)
        
        elif condition_type == "progress_based":
            # 基于故事进度的条件检查
            required_progress = condition.get("required_progress", {})
            return self._check_story_progress(required_progress)
        
        return False

    def _check_content_elements(self, required_elements: List[str], chapter_content: Dict) -> bool:
        """检查章节内容是否包含所需元素"""
        content_text = chapter_content.get("content", "")
        return all(element in content_text for element in required_elements)

    def _check_story_progress(self, required_progress: Dict) -> bool:
        """检查故事进度是否满足条件"""
        # 这里可以检查角色成长、势力发展等进度
        # 简化实现，总是返回True
        return True

    def _calculate_event_effects(self, chapter_number: int, chapter_content: Dict) -> Dict:
        """计算事件影响"""
        effects = {
            "character_effects": [],
            "faction_effects": [],
            "ability_effects": []
        }
        
        # 分析活跃事件对各方面的潜在影响
        for event_name, event_data in self.active_events.items():
            if self._is_event_active(chapter_number, event_data):
                # 角色影响
                if "character_development" in event_data:
                    effects["character_effects"].append({
                        "event": event_name,
                        "effect": event_data["character_development"],
                        "scope": "main_character"  # 或其他角色
                    })
                
                # 势力影响
                if "faction_impact" in event_data:
                    effects["faction_effects"].append({
                        "event": event_name,
                        "effect": event_data["faction_impact"],
                        "scope": "major_factions"
                    })
                
                # 能力影响
                if "ability_impact" in event_data:
                    effects["ability_effects"].append({
                        "event": event_name,
                        "effect": event_data["ability_impact"],
                        "scope": "main_character_abilities"
                    })
        
        return effects