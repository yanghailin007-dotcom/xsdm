from typing import Dict, List, Optional


class EventDrivenManager:
    """事件驱动管理器 - 使用阶段事件"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.event_system = {}
        
    def initialize_event_system(self):
        """初始化事件系统 - 从阶段计划中获取"""
        # 不立即初始化，等待阶段计划生成事件
        print("⏳ 事件系统将在阶段计划生成后初始化")
    
    def update_event_system(self):
        """更新事件系统 - 从阶段计划管理器获取最新事件"""
        stage_plan_manager = self.generator.stage_plan_manager
        if stage_plan_manager:
            self.event_system = stage_plan_manager.get_event_system()
            if self.event_system and (self.event_system.get("major_events") or self.event_system.get("big_events")):
                print("✓ 事件系统已从阶段计划更新")
                self.print_event_overview()
            else:
                print("⚠️ 事件系统暂无事件，使用默认事件结构")
                self._create_default_event_system()
        else:
            self._create_default_event_system()
    
    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件上下文 - 确保事件系统已更新"""
        # 确保事件系统是最新的
        if not self.event_system or (not self.event_system.get("major_events") and not self.event_system.get("big_events")):
            self.update_event_system()
        
        # 原有的逻辑保持不变...
        context = {
            "event_type": "normal",
            "event_info": None,
            "is_emotional_chapter": False,
            "is_foreshadowing_chapter": False,
            "event_chain": []
        }
        
        # 检查事件类型
        for event in self.event_system.get("events", []):
            if event["chapter"] == chapter_number:
                context.update({"event_type": "event", "event_info": event})
                break
                
        for event in self.event_system.get("big_events", []):
            if event["start_chapter"] <= chapter_number <= event["end_chapter"]:
                context.update({"event_type": "big_event", "event_info": event})
                break
                
        for event in self.event_system.get("major_events", []):
            if event["start_chapter"] <= chapter_number <= event["end_chapter"]:
                context.update({"event_type": "major_event", "event_info": event})
                break
        
        # 检查暗线章节
        context["is_emotional_chapter"] = chapter_number in self.event_system.get("emotional_chapters", [])
        context["is_foreshadowing_chapter"] = chapter_number in self.event_system.get("foreshadowing_chapters", [])
        context["event_chain"] = self._get_event_chain(chapter_number)
        
        return context
    
    
    def _create_default_event_system(self):
        """创建默认事件体系"""
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        self.event_system = {
            "overall_approach": "事件驱动主线，暗线穿插推进",
            "major_events": self._generate_default_major_events(total_chapters),
            "big_events": self._generate_default_big_events(total_chapters),
            "events": self._generate_default_events(total_chapters),
            "emotional_chapters": self._generate_emotional_chapters(total_chapters),
            "foreshadowing_chapters": self._generate_foreshadowing_chapters(total_chapters)
        }
        
    # 兼容性方法
    def get_current_major_event(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属的重大事件"""
        context = self.get_chapter_event_context(chapter_number)
        return context["event_info"] if context["event_type"] == "major_event" else None
    
    def get_event_progress(self, chapter_number: int, event: Dict) -> Dict:
        """获取事件进度"""
        return self._calculate_event_progress(chapter_number, event)
    
    def is_major_event_chapter(self, chapter_number: int) -> bool:
        """判断是否为重大事件章节"""
        context = self.get_chapter_event_context(chapter_number)
        return context["event_type"] == "major_event"
    
    def generate_major_event_prompt(self, chapter_number: int, event: Dict, progress: Dict) -> str:
        """生成重大事件专属提示词"""
        return self.generate_event_driven_prompt(chapter_number)

    def _generate_default_major_events(self, total_chapters: int) -> List[Dict]:
        """生成默认重大事件"""
        return [
            {
                "name": "开局觉醒",
                "type": "major_event",
                "start_chapter": 1,
                "end_chapter": 10,
                "duration": 10,
                "significance": "主角获得能力/系统，建立故事基础",
                "main_goal": "觉醒能力，建立初始目标",
                "sub_goals": ["引入核心设定", "建立主角动机", "展示初始能力"],
                "key_moments": ["能力觉醒时刻", "第一次使用能力", "确立目标"],
                "character_development": "从普通人到能力者的转变",
                "aftermath": "开启主线剧情",
                "prerequisite_events": []
            },
            {
                "name": "第一次重大挑战",
                "type": "major_event", 
                "start_chapter": 30,
                "end_chapter": 45,
                "duration": 15,
                "significance": "主角面临的第一次真正考验",
                "main_goal": "克服重大困难，证明实力",
                "sub_goals": ["提升能力等级", "获得重要盟友", "建立声望"],
                "key_moments": ["危机爆发", "关键决策", "突破极限"],
                "character_development": "从新手到战士的成长",
                "aftermath": "改变局势，开启新阶段",
                "prerequisite_events": ["前期积累"]
            }
        ]
    
    def _generate_default_big_events(self, total_chapters: int) -> List[Dict]:
        """生成默认大事件"""
        return [
            {
                "name": "初次实战",
                "type": "big_event",
                "start_chapter": 15,
                "end_chapter": 18, 
                "main_goal": "验证能力，积累经验",
                "connection_to_major": "为第一次重大挑战做准备",
                "role": "能力检验和角色成长"
            },
            {
                "name": "势力接触",
                "type": "big_event",
                "start_chapter": 22,
                "end_chapter": 25,
                "main_goal": "接触主要势力，建立关系",
                "connection_to_major": "为后续冲突铺垫", 
                "role": "世界观扩展和关系建立"
            }
        ]
    
    def _generate_default_events(self, total_chapters: int) -> List[Dict]:
        """生成默认事件"""
        event_chapters = [5, 12, 20, 28, 35, 42]
        return [
            {
                "name": f"事件{i+1}",
                "type": "event",
                "chapter": chapter,
                "goal": f"推进主线进度{i+1}",
                "connection_to_big": "支撑大事件发展",
                "outcome": "获得阶段性成果"
            }
            for i, chapter in enumerate(event_chapters)
        ]
    
    def _generate_emotional_chapters(self, total_chapters: int) -> List[int]:
        """生成感情线章节"""
        return [8, 17, 26, 33, 40]
    
    def _generate_foreshadowing_chapters(self, total_chapters: int) -> List[int]:
        """生成伏笔线章节"""
        return [6, 14, 23, 31, 38]
    
    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件上下文"""
        context = {
            "event_type": "normal",
            "event_info": None,
            "is_emotional_chapter": False,
            "is_foreshadowing_chapter": False,
            "event_chain": []
        }
        
        # 检查事件类型
        for event in self.event_system.get("events", []):
            if event["chapter"] == chapter_number:
                context.update({"event_type": "event", "event_info": event})
                break
                
        for event in self.event_system.get("big_events", []):
            if event["start_chapter"] <= chapter_number <= event["end_chapter"]:
                context.update({"event_type": "big_event", "event_info": event})
                break
                
        for event in self.event_system.get("major_events", []):
            if event["start_chapter"] <= chapter_number <= event["end_chapter"]:
                context.update({"event_type": "major_event", "event_info": event})
                break
        
        # 检查暗线章节
        context["is_emotional_chapter"] = chapter_number in self.event_system.get("emotional_chapters", [])
        context["is_foreshadowing_chapter"] = chapter_number in self.event_system.get("foreshadowing_chapters", [])
        context["event_chain"] = self._get_event_chain(chapter_number)
        
        return context
    
    def _get_event_chain(self, chapter_number: int) -> List[Dict]:
        """获取影响当前章节的事件链"""
        chain = []
        
        # 添加前置事件
        for event_type in ["events", "big_events", "major_events"]:
            for event in self.event_system.get(event_type, []):
                end_chapter = event.get("end_chapter", event.get("chapter", 0))
                if end_chapter < chapter_number:
                    chain.append({"type": event_type[:-1], "event": event})
        
        return chain
    
    def generate_event_driven_prompt(self, chapter_number: int) -> str:
        """生成事件驱动的提示词"""
        context = self.get_chapter_event_context(chapter_number)
        
        prompt_parts = ["\n\n# 🎯 事件驱动写作指导"]
        
        # 事件类型说明
        if context["event_type"] == "major_event":
            event_info = context["event_info"]
            progress = self._calculate_event_progress(chapter_number, event_info)
            prompt_parts.extend([
                f"## 重大事件进行中: {event_info['name']}",
                f"**当前进度**: {progress['current']}/{progress['total']}章 ({progress['stage']})",
                f"**主要目标**: {event_info['main_goal']}",
                f"**本阶段重点**: {self._get_major_event_stage_focus(progress['stage'], event_info)}",
                "**关键要求**: 保持事件连贯性，推进核心目标，确保角色同步成长"
            ])
        elif context["event_type"] == "big_event":
            event_info = context["event_info"]
            prompt_parts.extend([
                f"## 大事件: {event_info['name']}",
                f"**目标**: {event_info['main_goal']}",
                f"**作用**: {event_info['role']}",
                "**要求**: 承上启下，为重大事件做准备"
            ])
        elif context["event_type"] == "event":
            event_info = context["event_info"]
            prompt_parts.extend([
                f"## 事件: {event_info['name']}",
                f"**目标**: {event_info['goal']}",
                "**作用**: 推进主线进度"
            ])
        else:
            # 普通章节 - 检查暗线
            if context["is_emotional_chapter"]:
                prompt_parts.append("## 感情线推进章节\n重点发展角色关系和情感冲突")
            elif context["is_foreshadowing_chapter"]:
                prompt_parts.append("## 伏笔线推进章节\n重点埋设新伏笔或回收旧伏笔")
            else:
                prompt_parts.append("## 主线推进章节\n保持故事节奏，自然衔接前后事件")
        
        # 添加事件链上下文
        if context["event_chain"]:
            prompt_parts.append("\n## 事件链上下文:")
            for item in context["event_chain"][-3:]:  # 最近3个事件
                prompt_parts.append(f"- {item['type']}: {item['event']['name']}")
        
        return "\n".join(prompt_parts)
    
    def _calculate_event_progress(self, chapter_number: int, event: Dict) -> Dict:
        """计算事件进度"""
        total_chapters = event["end_chapter"] - event["start_chapter"] + 1
        current_progress = chapter_number - event["start_chapter"] + 1
        progress_ratio = current_progress / total_chapters
        
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
    
    def _get_major_event_stage_focus(self, stage: str, event: Dict) -> str:
        """获取重大事件各阶段的写作重点"""
        focus_map = {
            "开局阶段": f"建立{event['name']}的基础，引入核心冲突",
            "发展阶段": "深化矛盾，推进事件目标，角色成长",
            "高潮阶段": "冲突激化，关键转折，情感爆发", 
            "收尾阶段": "解决主要冲突，展示后果，铺垫后续"
        }
        return focus_map.get(stage, "推进事件发展")
    
    def print_event_overview(self):
        """打印事件体系概览"""
        print("\n📋 事件驱动体系概览:")
        
        print(f"🎯 重大事件 ({len(self.event_system.get('major_events', []))}个):")
        for event in self.event_system.get("major_events", []):
            print(f"  第{event['start_chapter']}-{event['end_chapter']}章: {event['name']}")
        
        print(f"🔥 大事件 ({len(self.event_system.get('big_events', []))}个):")
        for event in self.event_system.get("big_events", []):
            print(f"  第{event['start_chapter']}-{event['end_chapter']}章: {event['name']}")
        
        print(f"⚡ 事件 ({len(self.event_system.get('events', []))}个):")
        for event in self.event_system.get("events", []):
            print(f"  第{event['chapter']}章: {event['name']}")
        
        print(f"💕 感情线章节: {self.event_system.get('emotional_chapters', [])}")
        print(f"🔮 伏笔线章节: {self.event_system.get('foreshadowing_chapters', [])}")
