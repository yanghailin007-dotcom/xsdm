# EventDrivenManager.py
from typing import Dict, List, Optional
import re


class EventDrivenManager:
    """事件执行器 - 专注事件状态跟踪和章节事件上下文（事件执行）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.active_events = {}  # 修复：改为字典而不是列表
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
        print(f"\n🔍 [get_chapter_event_context] 开始获取第{chapter_number}章事件上下文")
        
        context = {
            "active_events": [],
            "event_progress": {},
            "event_tasks": [],
            "trigger_checkpoints": [],
            "event_chain_effects": []
        }
        
        # 打印活跃事件总数
        print(f"🔍 总活跃事件数量: {len(self.active_events)}")
        
        if not self.active_events:
            print("❌ 活跃事件字典为空，没有任何事件被激活")
            print(f"🔍 检查事件系统是否已初始化: {hasattr(self, 'active_events')}")
            return context
        
        # 获取当前活跃的事件
        active_count = 0
        for event_name, event_data in self.active_events.items():
            print(f"\n🔍 检查事件: {event_name}")
            print(f"   - 事件数据: {event_data}")
            
            is_active = self._is_event_active(chapter_number, event_data)
            print(f"   - 是否活跃: {is_active}")
            
            if is_active:
                active_count += 1
                print(f"   ✅ 事件 {event_name} 对第{chapter_number}章活跃")
                
                event_context = self._build_event_context(chapter_number, event_data)
                context["active_events"].append(event_context)
                print(f"   - 构建的事件上下文: {event_context.keys()}")
                
                # 计算事件进度
                progress = self._calculate_event_progress(chapter_number, event_data)
                context["event_progress"][event_name] = progress
                print(f"   - 事件进度: {progress}")
                
                # 生成事件任务
                tasks = self._generate_event_tasks(chapter_number, event_data, progress)
                context["event_tasks"].extend(tasks)
                print(f"   - 生成任务数量: {len(tasks)}")
            else:
                print(f"   ❌ 事件 {event_name} 对第{chapter_number}章不活跃")
        
        print(f"\n📊 第{chapter_number}章活跃事件统计: {active_count}个")
        
        # 检查触发条件
        trigger_checkpoints = self._check_event_triggers(chapter_number)
        context["trigger_checkpoints"] = trigger_checkpoints
        print(f"🔍 触发检查点数量: {len(trigger_checkpoints)}")
        
        # 计算事件链影响
        chain_effects = self._calculate_chain_effects(chapter_number)
        context["event_chain_effects"] = chain_effects
        print(f"🔍 事件链影响数量: {len(chain_effects)}")
        
        print(f"✅ [get_chapter_event_context] 第{chapter_number}章事件上下文获取完成")
        print(f"   - 活跃事件: {len(context['active_events'])}个")
        print(f"   - 事件任务: {len(context['event_tasks'])}个")
        print(f"   - 触发检查点: {len(context['trigger_checkpoints'])}个")
        print(f"   - 事件链影响: {len(context['event_chain_effects'])}个")
        
        return context

    def generate_event_execution_prompt(self, chapter_number: int) -> str:
        """生成事件执行指导提示词 - 修复版本"""
        event_context = self.get_chapter_event_context(chapter_number)
        
        if not event_context["active_events"] and not event_context["trigger_checkpoints"]:
            return "# 🎯 事件执行指导\n\n本章暂无特定事件执行任务。"
        
        prompt_parts = ["# 🎯 事件执行指导"]
        
        # 活跃事件指导
        if event_context["active_events"]:
            prompt_parts.append("## 活跃事件")
            
            for event in event_context["active_events"]:
                event_name = event.get("name", "未知事件")
                progress = event_context["event_progress"].get(event_name, {})
                
                # 修复：确保所有字段都有默认值
                prompt_parts.extend([
                    f"### {event_name}",
                    f"**目标**: {event.get('main_goal', '推进事件发展')}",
                    f"**当前重点**: {event.get('current_stage_focus', '推进事件发展')}",
                    f"**关键时刻**:"
                ])
                
                # 修复：正确处理关键时刻显示
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
        
        # 触发检查点
        if event_context["trigger_checkpoints"]:
            prompt_parts.append("## 事件触发检查点")
            for checkpoint in event_context["trigger_checkpoints"]:
                prompt_parts.append(f"- **{checkpoint.get('trigger', '未知触发')}**: {checkpoint.get('description', '未指定描述')}")
        
        # 事件链影响
        if event_context["event_chain_effects"]:
            prompt_parts.append("## 事件链影响")
            for effect in event_context["event_chain_effects"]:
                prompt_parts.append(f"- {effect.get('description', '未指定影响')} (源于: {effect.get('source_event', '未知事件')})")
        
        # 事件任务
        if event_context["event_tasks"]:
            prompt_parts.append("## 本章事件任务")
            for task in event_context["event_tasks"]:
                prompt_parts.append(f"- **{task.get('priority', '普通')}优先级**: {task.get('description', '未指定任务')}")
        
        return "\n".join(prompt_parts)

    def _initialize_active_events(self, event_system: Dict):
        """初始化活跃事件 - 修复字段缺失问题"""
        self.active_events.clear()
        
        # 添加重大事件 - 修复：确保所有必需字段都有默认值
        for event in event_system.get("major_events", []):
            event_name = event.get("name")
            if event_name:
                self.active_events[event_name] = {
                    "name": event_name,
                    "type": event.get("type", "major_event"),
                    "main_goal": event.get("main_goal", "推进故事发展"),
                    "goal": event.get("goal", event.get("main_goal", "推进故事发展")),  # 兼容字段
                    "start_chapter": event.get("start_chapter", 1),
                    "end_chapter": event.get("end_chapter", 10),
                    "key_moments": event.get("key_moments", []),
                    "character_roles": event.get("character_roles", {}),
                    "stage_focus": event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": event.get("start_chapter", 1),
                    "current_progress": 0
                }
        
        # 添加大事件
        for event in event_system.get("big_events", []):
            event_name = event.get("name")
            if event_name:
                self.active_events[event_name] = {
                    "name": event_name,
                    "type": event.get("type", "big_event"),
                    "main_goal": event.get("main_goal", "推进故事发展"),
                    "goal": event.get("goal", event.get("main_goal", "推进故事发展")),
                    "start_chapter": event.get("start_chapter", 1),
                    "end_chapter": event.get("end_chapter", 10),
                    "key_moments": event.get("key_moments", []),
                    "character_roles": event.get("character_roles", {}),
                    "stage_focus": event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": event.get("start_chapter", 1),
                    "current_progress": 0
                }
        
        # 添加普通事件
        for event in event_system.get("events", []):
            event_name = event.get("name")
            if event_name:
                self.active_events[event_name] = {
                    "name": event_name,
                    "type": event.get("type", "event"),
                    "main_goal": event.get("main_goal", "推进故事发展"),
                    "goal": event.get("goal", event.get("main_goal", "推进故事发展")),
                    "chapter": event.get("chapter", 1),
                    "key_moments": event.get("key_moments", []),
                    "character_roles": event.get("character_roles", {}),
                    "stage_focus": event.get("stage_focus", {}),
                    "status": "active",
                    "started_chapter": event.get("chapter", 1),
                    "current_progress": 0
                }
        
        print(f"✅ 初始化活跃事件完成: {len(self.active_events)}个事件")

    def _build_event_context(self, chapter_number: int, event_data: Dict) -> Dict:
        """构建事件上下文 - 修复字段缺失和关键时刻处理"""
        print(f"🔍 [_build_event_context] 开始构建事件上下文")
        print(f"   - 事件名称: {event_data.get('name')}")
        print(f"   - 事件类型: {event_data.get('type')}")
        
        progress = self._calculate_event_progress(chapter_number, event_data)
        
        # 修复：确保关键时刻是标准格式
        key_moments = []
        raw_moments = event_data.get("key_moments", [])
        print(f"   - 原始关键时刻: {raw_moments}")
        
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
                print(f"   - 转换字符串关键时刻: {moment} -> 第{moment_chapter}章")
            elif isinstance(moment, dict):
                # 确保字典格式完整
                key_moments.append({
                    "chapter": moment.get("chapter", chapter_number),
                    "description": moment.get("description", "未描述关键时刻"),
                    "preparation": moment.get("preparation", "正常推进")
                })
            else:
                print(f"   ⚠️ 忽略未知格式的关键时刻: {moment}")
        
        # 修复：处理不同类型事件的目标字段
        main_goal = event_data.get("main_goal")
        if not main_goal:
            # 对于普通事件，使用 goal 字段
            main_goal = event_data.get("goal", "推进事件发展")
            print(f"   - 使用备用目标字段: {main_goal}")
        
        # 获取当前阶段重点
        current_stage_focus = self._get_current_stage_focus(progress.get("stage", "开局阶段"), event_data)
        
        # 构建事件上下文
        event_context = {
            "name": event_data.get("name", "未知事件"),
            "type": event_data.get("type", "普通事件"),
            "main_goal": main_goal,
            "current_stage_focus": current_stage_focus,
            "key_moments": key_moments,  # 使用标准化后的关键时刻
            "character_roles": event_data.get("character_roles", {}),
            "progress": progress
        }
        
        print(f"✅ [_build_event_context] 事件上下文构建成功")
        print(f"   - 目标: {event_context.get('main_goal')}")
        print(f"   - 当前重点: {event_context.get('current_stage_focus')}")
        print(f"   - 关键时刻数量: {len(event_context.get('key_moments', []))}")
        
        return event_context

    def _calculate_event_progress(self, chapter_number: int, event_data: Dict) -> Dict:
        """计算事件进度 - 修复进度计算逻辑"""
        # 处理不同类型的事件
        if "start_chapter" in event_data and "end_chapter" in event_data:
            # 主要事件和大事件
            start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 1))
            end_chapter = event_data.get("end_chapter", chapter_number + 10)  # 默认10章跨度
            
            total_chapters = max(end_chapter - start_chapter + 1, 1)  # 防止除零
            current_progress = max(min(chapter_number - start_chapter + 1, total_chapters), 0)
            progress_ratio = current_progress / total_chapters if total_chapters > 0 else 0
            
            print(f"   - 多章事件进度: {current_progress}/{total_chapters} (比率: {progress_ratio:.2f})")
            
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data.get("chapter", 1)
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
            
            print(f"   - 单章事件进度: {current_progress}/{total_chapters}")
        else:
            # 默认处理
            current_progress = 1
            total_chapters = 1
            progress_ratio = 1
            print(f"   - 默认事件进度: {current_progress}/{total_chapters}")
        
        # 确定阶段 - 修复阶段判断逻辑
        if progress_ratio <= 0.3:
            stage = "开局阶段"
        elif progress_ratio <= 0.6:
            stage = "发展阶段"
        elif progress_ratio <= 0.9:
            stage = "高潮阶段"
        else:
            stage = "收尾阶段"
        
        print(f"   - 事件阶段: {stage} (进度比率: {progress_ratio:.2f})")
        
        return {
            "current": current_progress,
            "total": total_chapters,
            "ratio": progress_ratio,
            "stage": stage
        }

    def _get_current_stage_focus(self, stage: str, event_data: Dict) -> str:
        """获取当前阶段的执行重点 - 修复重点获取逻辑"""
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

    # 其他方法保持不变，但确保所有字典访问都使用.get()方法
    def _setup_event_triggers(self, event_system: Dict):
        """设置事件触发条件 - 支持新的事件结构"""
        self.event_triggers.clear()
        
        # 为所有类型的事件设置触发条件
        all_events = []
        all_events.extend(event_system.get("major_events", []))
        all_events.extend(event_system.get("big_events", []))
        all_events.extend(event_system.get("events", []))
        
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
            elif "start_chapter" in event or "chapter" in event:
                trigger_chapter = event.get("start_chapter", event.get("chapter"))
                if trigger_chapter:
                    self.event_triggers[event_name] = {
                        "condition": {
                            "type": "chapter",
                            "chapter": trigger_chapter
                        },
                        "event_data": event
                    }

    def _is_event_active(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否活跃 - 添加详细调试信息"""
        print(f"\n🔍 [_is_event_active] 检查事件活跃状态")
        print(f"   - 章节: {chapter_number}")
        print(f"   - 事件名称: {event_data.get('name')}")
        
        if event_data.get("status") != "active":
            print(f"   ❌ 事件状态不是active: {event_data.get('status')}")
            return False
        
        # 处理不同类型的事件
        if "start_chapter" in event_data and "end_chapter" in event_data:
            # 主要事件和大事件
            start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 0))
            end_chapter = event_data.get("end_chapter", chapter_number + 100)
            
            result = start_chapter <= chapter_number <= end_chapter
            print(f"   - 多章事件: {start_chapter}~{end_chapter}, 当前{chapter_number}, 活跃: {result}")
            return result
            
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data.get("chapter")
            result = chapter_number == event_chapter
            print(f"   - 单章事件: 第{event_chapter}章, 当前{chapter_number}, 活跃: {result}")
            return result
            
        else:
            # 默认处理
            start_chapter = event_data.get("started_chapter", 0)
            result = chapter_number >= start_chapter
            print(f"   - 默认事件: 开始{start_chapter}, 当前{chapter_number}, 活跃: {result}")
            return result

    def initialize_event_system(self):
        """初始化事件系统 - 修复版本：从当前正确阶段加载"""
        print("🎯 初始化事件系统...")
        
        novel_data = self.generator.novel_data
        
        # 获取当前章节
        current_chapter = len(novel_data["generated_chapters"]) + 1
        print(f"🔍 当前章节: {current_chapter}")
        
        # 方法1: 从当前章节所属的阶段加载事件系统
        current_stage = self._get_current_stage_from_plans(current_chapter)
        if current_stage:
            print(f"✅ 当前阶段: {current_stage}")
            
            # 从 stage_writing_plans 中提取当前阶段的事件系统
            if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
                if current_stage in novel_data["stage_writing_plans"]:
                    stage_data = novel_data["stage_writing_plans"][current_stage]
                    
                    # 修复：正确访问嵌套结构
                    if ("stage_writing_plan" in stage_data and 
                        "event_system" in stage_data["stage_writing_plan"]):
                        
                        event_system = stage_data["stage_writing_plan"]["event_system"]
                        print(f"✅ 从当前阶段 {current_stage} 加载事件系统")
                        print(f"   - 重大事件: {len(event_system.get('major_events', []))}个")
                        print(f"   - 大事件: {len(event_system.get('big_events', []))}个")
                        print(f"   - 普通事件: {len(event_system.get('events', []))}个")
                        
                        # 更新到事件执行器
                        self.update_from_stage_plan({"event_system": event_system})
                        return
                else:
                    print(f"⚠️ 当前阶段 {current_stage} 不在stage_writing_plans中")
        
        # 方法2: 如果找不到当前阶段，尝试从所有阶段中查找适合当前章节的事件
        print("🔍 尝试从所有阶段查找适合当前章节的事件...")
        if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
            for stage_name, stage_data in novel_data["stage_writing_plans"].items():
                # 检查这个阶段是否包含当前章节
                if self._is_chapter_in_stage(current_chapter, stage_data):
                    print(f"✅ 发现阶段 {stage_name} 包含第{current_chapter}章")
                    
                    # 修复：正确访问嵌套结构
                    if ("stage_writing_plan" in stage_data and 
                        "event_system" in stage_data["stage_writing_plan"]):
                        
                        event_system = stage_data["stage_writing_plan"]["event_system"]
                        print(f"✅ 从阶段 {stage_name} 加载事件系统")
                        print(f"   - 重大事件: {len(event_system.get('major_events', []))}个")
                        print(f"   - 大事件: {len(event_system.get('big_events', []))}个")
                        print(f"   - 普通事件: {len(event_system.get('events', []))}个")
                        
                        # 更新到事件执行器
                        self.update_from_stage_plan({"event_system": event_system})
                        return
        
        # 方法3: 如果还是找不到，使用第一个可用的阶段
        if "stage_writing_plans" in novel_data and novel_data["stage_writing_plans"]:
            first_stage = list(novel_data["stage_writing_plans"].keys())[0]
            stage_data = novel_data["stage_writing_plans"][first_stage]
            
            if ("stage_writing_plan" in stage_data and 
                "event_system" in stage_data["stage_writing_plan"]):
                
                event_system = stage_data["stage_writing_plan"]["event_system"]
                print(f"⚠️ 使用第一个可用阶段 {first_stage} 的事件系统")
                print(f"   - 重大事件: {len(event_system.get('major_events', []))}个")
                print(f"   - 大事件: {len(event_system.get('big_events', []))}个")
                print(f"   - 普通事件: {len(event_system.get('events', []))}个")
                
                # 更新到事件执行器
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
        
        # 从 global_growth_plan 中查找
        if "global_growth_plan" in novel_data and "stage_framework" in novel_data["global_growth_plan"]:
            stage_framework = novel_data["global_growth_plan"]["stage_framework"]
            for stage in stage_framework:
                chapter_range = stage.get("chapter_range", "")
                if self._is_chapter_in_range(chapter_number, chapter_range):
                    return stage.get("stage_name", "未知阶段")
        
        return "未知阶段"

    def _is_chapter_in_stage(self, chapter_number: int, stage_data: Dict) -> bool:
        """检查章节是否在阶段范围内"""
        # 从阶段数据中提取章节范围
        chapter_range = ""
        
        if "stage_writing_plan" in stage_data:
            # 嵌套结构
            writing_plan = stage_data["stage_writing_plan"]
            chapter_range = writing_plan.get("chapter_range", "")
        else:
            # 直接结构
            chapter_range = stage_data.get("chapter_range", "")
        
        return self._is_chapter_in_range(chapter_number, chapter_range)

    def _is_chapter_in_range(self, chapter_number: int, chapter_range: str) -> bool:
        """检查章节是否在范围内"""
        if not chapter_range:
            return False
        
        try:
            # 解析范围字符串，支持 "1-10", "1~10", "1至10" 等格式
            import re
            numbers = re.findall(r'\d+', chapter_range)
            if len(numbers) >= 2:
                start_chapter = int(numbers[0])
                end_chapter = int(numbers[1])
                return start_chapter <= chapter_number <= end_chapter
            elif len(numbers) == 1:
                # 如果是单章范围
                single_chapter = int(numbers[0])
                return chapter_number == single_chapter
        except Exception as e:
            print(f"❌ 解析章节范围失败: {chapter_range}, 错误: {e}")
        
        return False

    def get_chapter_event_context(self, chapter_number: int) -> Dict:
        """获取章节的事件执行上下文 - 确保使用正确阶段的事件"""
        print(f"\n🔍 [get_chapter_event_context] 开始获取第{chapter_number}章事件上下文")
        
        # 检查是否需要重新初始化事件系统（如果章节变化）
        current_chapter = getattr(self.generator, 'current_chapter', 1)
        if chapter_number != current_chapter:
            print(f"🔍 章节变化: {current_chapter} -> {chapter_number}，重新初始化事件系统")
            self.initialize_event_system()
        
        # 继续原有的逻辑...
        context = {
            "active_events": [],
            "event_progress": {},
            "event_tasks": [],
            "trigger_checkpoints": [],
            "event_chain_effects": []
        }
        
        # 打印活跃事件总数
        print(f"🔍 总活跃事件数量: {len(self.active_events)}")
        
        if not self.active_events:
            print("❌ 活跃事件字典为空，尝试重新初始化...")
            self.initialize_event_system()
            print(f"🔍 重新初始化后事件数量: {len(self.active_events)}")
        
        # 如果还是没有事件，创建回退事件
        if not self.active_events:
            print("❌ 仍然没有事件，创建回退事件")
            self._create_fallback_events(chapter_number)
            print(f"🔍 创建回退事件后数量: {len(self.active_events)}")
        
        # 获取当前活跃的事件
        active_count = 0
        for event_name, event_data in self.active_events.items():
            print(f"\n🔍 检查事件: {event_name}")
            
            is_active = self._is_event_active(chapter_number, event_data)
            print(f"   - 是否活跃: {is_active}")
            
            if is_active:
                active_count += 1
                print(f"   ✅ 事件 {event_name} 对第{chapter_number}章活跃")
                
                event_context = self._build_event_context(chapter_number, event_data)
                context["active_events"].append(event_context)
                
                # 计算事件进度
                progress = self._calculate_event_progress(chapter_number, event_data)
                context["event_progress"][event_name] = progress
                
                # 生成事件任务
                tasks = self._generate_event_tasks(chapter_number, event_data, progress)
                context["event_tasks"].extend(tasks)
        
        print(f"\n📊 第{chapter_number}章活跃事件统计: {active_count}个")
        
        # 检查触发条件
        trigger_checkpoints = self._check_event_triggers(chapter_number)
        context["trigger_checkpoints"] = trigger_checkpoints
        
        # 计算事件链影响
        chain_effects = self._calculate_chain_effects(chapter_number)
        context["event_chain_effects"] = chain_effects
        
        print(f"✅ [get_chapter_event_context] 第{chapter_number}章事件上下文获取完成")
        return context

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
            event_name = f"{stage.get('stage_name', '未知阶段')}核心事件"
            event_system["major_events"].append({
                "name": event_name,
                "type": "stage_core",
                "main_goal": stage.get("core_objectives", ["推进故事发展"])[0],
                "start_chapter": self._parse_chapter_start(stage.get("chapter_range", "1-1")),
                "end_chapter": self._parse_chapter_end(stage.get("chapter_range", "1-1")),
                "key_moments": [
                    {
                        "chapter": self._parse_chapter_start(stage.get("chapter_range", "1-1")) + 3,
                        "description": f"{stage.get('stage_name', '未知阶段')}关键发展",
                        "purpose": "推动事件进展"
                    }
                ]
            })
        
        self.update_from_stage_plan({"event_system": event_system})

    def _parse_chapter_start(self, chapter_range: str) -> int:
        """解析章节范围起始"""
        try:
            return int(chapter_range.split("-")[0])
        except:
            return 1

    def _parse_chapter_end(self, chapter_range: str) -> int:
        """解析章节范围结束"""
        try:
            parts = chapter_range.split("-")
            return int(parts[1]) if len(parts) > 1 else int(parts[0])
        except:
            return 10

    def _is_event_completed(self, chapter_number: int, event_data: Dict) -> bool:
        """检查事件是否完成 - 支持新的事件类型"""
        if event_data.get("status") != "active":
            return False
        
        # 处理不同类型的事件
        if "end_chapter" in event_data:
            # 主要事件和大事件
            end_chapter = event_data.get("end_chapter", chapter_number)
            return chapter_number >= end_chapter
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data.get("chapter")
            return chapter_number > event_chapter  # 在事件章节之后完成
        else:
            # 默认处理
            return False

    def _build_event_context(self, chapter_number: int, event_data: Dict) -> Dict:
        """构建事件上下文 - 修复关键时刻处理和字段缺失问题"""
        print(f"🔍 [_build_event_context] 开始构建事件上下文")
        print(f"   - 事件名称: {event_data.get('name')}")
        print(f"   - 事件类型: {event_data.get('type')}")
        
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
        
        # 修复：处理不同类型事件的目标字段
        main_goal = event_data.get("main_goal")
        if not main_goal:
            # 对于普通事件，使用 goal 字段
            main_goal = event_data.get("goal", "推进事件发展")
            print(f"   - 使用备用目标字段: {main_goal}")
        
        # 构建事件上下文
        event_context = {
            "name": event_data.get("name", "未知事件"),
            "type": event_data.get("type", "普通事件"),
            "main_goal": main_goal,
            "current_stage_focus": self._get_current_stage_focus(progress.get("stage", "开局阶段"), event_data),
            "key_moments": key_moments,  # 使用标准化后的关键时刻
            "character_roles": event_data.get("character_roles", {}),
            "progress": progress
        }
        
        print(f"✅ [_build_event_context] 事件上下文构建成功")
        print(f"   - 关键字段: main_goal={event_context.get('main_goal')}")
        print(f"   - 关键时刻数量: {len(event_context.get('key_moments', []))}")
        
        return event_context
    
    def _calculate_event_progress(self, chapter_number: int, event_data: Dict) -> Dict:
        """计算事件进度"""
        # 处理不同类型的事件
        if "start_chapter" in event_data and "end_chapter" in event_data:
            # 主要事件和大事件
            start_chapter = event_data.get("started_chapter", event_data.get("start_chapter", 1))
            end_chapter = event_data.get("end_chapter", chapter_number)
            
            total_chapters = max(end_chapter - start_chapter + 1, 1)  # 防止除零
            current_progress = max(chapter_number - start_chapter + 1, 0)
            progress_ratio = current_progress / total_chapters if total_chapters > 0 else 0
        elif "chapter" in event_data:
            # 普通事件（单章事件）
            event_chapter = event_data.get("chapter", 1)
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
        event_name = event_data.get("name", "未知事件")
        
        # 基于事件阶段生成任务
        current_stage = progress.get("stage", "开局阶段")
        if current_stage == "开局阶段":
            tasks.append({
                "event": event_name,
                "description": "建立事件基础设定和初始冲突",
                "priority": "high",
                "type": "setup"
            })
        elif current_stage == "发展阶段":
            tasks.append({
                "event": event_name,
                "description": "深化事件矛盾，推进核心目标",
                "priority": "high",
                "type": "development"
            })
        elif current_stage == "高潮阶段":
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
            if moment.get("chapter") == chapter_number:
                tasks.append({
                    "event": event_name,
                    "description": f"处理关键时刻: {moment.get('description', '未描述')}",
                    "priority": "critical",
                    "type": "key_moment"
                })
        
        return tasks

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

    def _complete_event(self, event_name: str, event_data: Dict, chapter_content: Dict) -> Dict:
        """完成事件处理"""
        completed_event = {
            "name": event_name,
            "type": event_data.get("type", "普通事件"),
            "completed_chapter": chapter_content.get("chapter_number", 0),
            "status": "completed",
            "outcomes": self._extract_event_outcomes(event_data, chapter_content),
            "aftermath_effects": event_data.get("aftermath", [])
        }
        
        # 移动到历史记录
        self.event_history.append(completed_event)
        if event_name in self.active_events:
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
        
        return outcomes if outcomes else ["事件顺利完成"]

    def _process_completion_triggers(self, completed_event: str):
        """处理事件完成触发"""
        for event_name, trigger_data in list(self.event_triggers.items()):
            condition = trigger_data.get("condition", {})
            if (condition.get("type") == "event_completion" and 
                condition.get("prerequisite_event") == completed_event):
                
                # 触发新事件
                event_data = trigger_data.get("event_data", {})
                self.active_events[event_name] = {
                    **event_data,
                    "status": "active",
                    "started_chapter": getattr(self.generator, 'current_chapter', 0) + 1,  # 下一章开始
                    "current_progress": 0
                }
                
                print(f"  🔄 事件'{completed_event}'完成，触发新事件: {event_name}")

    def _process_event_triggers(self, chapter_number: int, chapter_content: Dict) -> List[Dict]:
        """处理事件触发"""
        triggered_events = []
        
        for event_name, trigger_data in list(self.event_triggers.items()):
            if self._check_trigger_condition(trigger_data.get("condition", {}), chapter_number, chapter_content):
                event_data = trigger_data.get("event_data", {})
                
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
                    "trigger_condition": trigger_data.get("condition", {})
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
    
    def update_event_system(self):
        """更新事件系统 - 由NovelGenerator调用"""
        print("🔄 EventDrivenManager: 更新事件系统")
        
        # 清除所有活跃事件
        self.active_events.clear()
        print("  ✅ 已清除所有旧事件")
        
        # 事件系统会在NovelGenerator中通过add_event重新填充

    def add_event(self, name: str, event_type: str, start_chapter: int, description: str = "", impact_level: str = "medium"):
        """添加新事件 - 修复：适应字典结构"""
        event = {
            "name": name,
            "type": event_type,
            "start_chapter": start_chapter,
            "started_chapter": start_chapter,  # 添加兼容字段
            "description": description,
            "impact_level": impact_level,
            "status": "active",  # 修复：改为active
            "current_progress": 0,  # 修复：改为current_progress
            "key_moments": []
        }
        
        self.active_events[name] = event  # 修复：使用字典赋值而不是列表append
        print(f"  ✅ 添加事件: {name} (类型: {event_type}, 起始章节: {start_chapter})")