import json
from typing import Dict, Optional


class StagePlanManager:
    """阶段计划管理器 - 集成事件管理"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.stage_plan = None
        self.stage_boundaries = {}
        self.current_stage_plans = {}  # 存储各阶段的详细计划
        self.event_system = {}  # 整合的事件系统
    
    def generate_overall_stage_plan(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划 - 修复版本"""
        print("=== 生成全书阶段计划 ===")
        
        # 计算阶段边界
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = f"""
    创意种子: {creative_seed}
    小说标题: {novel_title}
    小说简介: {novel_synopsis}
    市场分析: {json.dumps(market_analysis, ensure_ascii=False)}
    总章节数: {total_chapters}
    """
        
        # 添加阶段边界参数
        user_prompt += f"""
    开局阶段结束: 第{boundaries['opening_end']}章
    发展阶段开始: 第{boundaries['development_start']}章
    发展阶段结束: 第{boundaries['development_end']}章  
    高潮阶段开始: 第{boundaries['climax_start']}章
    高潮阶段结束: 第{boundaries['climax_end']}章
    收尾阶段开始: 第{boundaries['ending_start']}章
    收尾阶段结束: 第{boundaries['ending_end']}章
    结局阶段开始: 第{boundaries['final_start']}章
    """
        
        result = self.generator.api_client.generate_content_with_retry(
            "overall_stage_plan", 
            user_prompt,
            purpose="制定全书阶段计划"
        )
        
        if result:
            # 验证数据结构
            if not isinstance(result, dict):
                print("❌ 阶段计划返回数据格式错误")
                return None
                
            # 检查必要的键是否存在
            required_keys = ["overall_stage_plan"]
            missing_keys = [key for key in required_keys if key not in result]
            
            if missing_keys:
                print(f"⚠️  阶段计划数据缺少键: {missing_keys}")
                print(f"   实际返回的键: {list(result.keys())}")
                # 尝试使用第一个键作为阶段数据
                first_key = list(result.keys())[0] if result else None
                if first_key and isinstance(result[first_key], dict):
                    print(f"   使用第一个键作为阶段数据: {first_key}")
                    # 重新组织数据结构
                    result = {"overall_stage_plan": result[first_key]}
            
            self.stage_plan = result
            self.stage_boundaries = boundaries
            print("✓ 全书阶段计划生成成功")
            self.print_stage_overview()  # 调用修复后的方法
            return result
        else:
            print("❌ 全书阶段计划生成失败")
            return None
    
    def get_stage_plan_for_chapter(self, chapter_number: int) -> Optional[Dict]:
        """为当前章节生成阶段写作计划 - 包含事件设计"""
        if not self.stage_plan:
            return None
        
        current_stage = self.get_current_stage(chapter_number)
        
        # 如果已经生成过该阶段的计划，直接返回
        if current_stage in self.current_stage_plans:
            return self.current_stage_plans[current_stage]
        
        stage_progress = self.get_stage_progress(chapter_number)
        
        # 获取阶段信息
        stage_info = self.stage_plan.get(current_stage, {})
        if not stage_info:
            return None
        
        print(f"  📋 生成{current_stage}的详细写作计划（包含事件设计）...")
        
        user_prompt = f"""
全书阶段计划: {json.dumps(self.stage_plan, ensure_ascii=False)}
当前章节: 第{chapter_number}章
所属阶段: {current_stage}
阶段位置: {stage_progress}
阶段核心任务: {', '.join(stage_info.get('core_tasks', []))}
阶段重点内容: {', '.join(stage_info.get('key_content', []))}
阶段写作重点: {stage_info.get('writing_focus', '')}

# 阶段范围信息
阶段开始章节: {self.get_stage_start_chapter(current_stage)}
阶段结束章节: {self.get_stage_end_chapter(current_stage)}
阶段总章节数: {self.get_stage_total_chapters(current_stage)}
"""
        
        result = self.generator.api_client.generate_content_with_retry(
            "stage_writing_plan",
            user_prompt,
            purpose=f"制定{current_stage}详细写作计划"
        )
        
        if result:
            self.current_stage_plans[current_stage] = result
            
            # 新增：保存到 novel_data 中实现持久化
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            self.generator.novel_data["stage_writing_plans"][current_stage] = result
            
            print(f"  ✓ {current_stage}详细计划生成成功并已保存")
        
        return result

    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划"""
        current_stage = self.get_current_stage(chapter_number)
        
        # 首先尝试从 novel_data 中获取（持久化存储）
        if "stage_writing_plans" in self.generator.novel_data:
            stage_plans = self.generator.novel_data["stage_writing_plans"]
            if current_stage in stage_plans:
                # 同时更新内存缓存
                self.current_stage_plans[current_stage] = stage_plans[current_stage]
                return stage_plans[current_stage]
        
        # 如果 novel_data 中没有，尝试从内存缓存中获取
        if current_stage in self.current_stage_plans:
            return self.current_stage_plans[current_stage]
        
        # 如果都没有，生成新的计划
        return self.get_stage_plan_for_chapter(chapter_number)  

    def _integrate_stage_events(self, stage_name: str, stage_plan: Dict):
        """将阶段事件整合到全局事件系统"""
        if "stage_writing_plan" not in stage_plan:
            return
        
        event_system = stage_plan["stage_writing_plan"].get("event_system", {})
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        # 验证事件章节范围
        for event_type in ["major_events", "big_events", "events"]:
            for event in event_system.get(event_type, []):
                # 确保事件结束章节不超过总章节数
                if "end_chapter" in event:
                    event["end_chapter"] = min(event["end_chapter"], total_chapters)
        
        # 初始化事件系统
        if not self.event_system:
            self.event_system = {
                "overall_approach": "分阶段事件驱动",
                "major_events": [],
                "big_events": [],
                "events": [],
                "emotional_chapters": [],
                "foreshadowing_chapters": []
            }
        
        # 整合事件
        if "major_events" in event_system:
            self.event_system["major_events"].extend(event_system["major_events"])
        
        if "big_events" in event_system:
            self.event_system["big_events"].extend(event_system["big_events"])
        
        if "events" in event_system:
            self.event_system["events"].extend(event_system["events"])
        
        print(f"  🔄 已整合{stage_name}的事件到全局事件系统")
    
    def get_stage_start_chapter(self, stage_name: str) -> int:
        """获取阶段开始章节"""
        boundaries = self.stage_boundaries
        if stage_name == "opening_stage":
            return 1
        elif stage_name == "development_stage":
            return boundaries["development_start"]
        elif stage_name == "climax_stage":
            return boundaries["climax_start"]
        elif stage_name == "ending_stage":
            return boundaries["ending_start"]
        elif stage_name == "final_stage":
            return boundaries["final_start"]
        else:
            return 1
    
    def get_stage_end_chapter(self, stage_name: str) -> int:
        """获取阶段结束章节"""
        boundaries = self.stage_boundaries
        if stage_name == "opening_stage":
            return boundaries["opening_end"]
        elif stage_name == "development_stage":
            return boundaries["development_end"]
        elif stage_name == "climax_stage":
            return boundaries["climax_end"]
        elif stage_name == "ending_stage":
            return boundaries["ending_end"]
        elif stage_name == "final_stage":
            return self.generator.novel_data["current_progress"]["total_chapters"]
        else:
            return self.generator.novel_data["current_progress"]["total_chapters"]
    
    def get_stage_total_chapters(self, stage_name: str) -> int:
        """获取阶段总章节数"""
        start = self.get_stage_start_chapter(stage_name)
        end = self.get_stage_end_chapter(stage_name)
        return end - start + 1
    
    def get_event_system(self) -> Dict:
        """获取全局事件系统"""
        return self.event_system
    
    
    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        ratios = [0.12, 0.28, 0.32, 0.18, 0.10]  # 确保总和为1.0
        
        # 计算累积章节数，确保不重叠
        chapters = [0]
        for ratio in ratios:
            chapters.append(chapters[-1] + int(total_chapters * ratio))
        
        # 确保最后一个章节等于总章节数
        chapters[-1] = total_chapters
        
        return {
            "opening_end": chapters[1],
            "development_start": chapters[1] + 1,
            "development_end": chapters[2],
            "climax_start": chapters[2] + 1,
            "climax_end": chapters[3],
            "ending_start": chapters[3] + 1,
            "ending_end": chapters[4],
            "final_start": chapters[4] + 1
        }
    
    def get_current_stage(self, chapter_number: int) -> str:
        """获取当前章节所属阶段"""
        if not self.stage_boundaries:
            return "unknown"
        
        boundaries = self.stage_boundaries
        
        if chapter_number <= boundaries["opening_end"]:
            return "opening_stage"
        elif boundaries["development_start"] <= chapter_number <= boundaries["development_end"]:
            return "development_stage"
        elif boundaries["climax_start"] <= chapter_number <= boundaries["climax_end"]:
            return "climax_stage"
        elif boundaries["ending_start"] <= chapter_number <= boundaries["ending_end"]:
            return "ending_stage"
        elif chapter_number >= boundaries["final_start"]:
            return "final_stage"
        else:
            return "transition"
    
    def get_stage_progress(self, chapter_number: int) -> str:
        """获取在当前阶段中的进度"""
        stage = self.get_current_stage(chapter_number)
        boundaries = self.stage_boundaries
        
        if stage == "opening_stage":
            total = boundaries["opening_end"]
            current = chapter_number
            progress = current / total
        elif stage == "development_stage":
            total = boundaries["development_end"] - boundaries["development_start"] + 1
            current = chapter_number - boundaries["development_start"] + 1
            progress = current / total
        elif stage == "climax_stage":
            total = boundaries["climax_end"] - boundaries["climax_start"] + 1
            current = chapter_number - boundaries["climax_start"] + 1
            progress = current / total
        elif stage == "ending_stage":
            total = boundaries["ending_end"] - boundaries["ending_start"] + 1
            current = chapter_number - boundaries["ending_start"] + 1
            progress = current / total
        elif stage == "final_stage":
            total = self.generator.novel_data["current_progress"]["total_chapters"] - boundaries["final_start"] + 1
            current = chapter_number - boundaries["final_start"] + 1
            progress = current / total
        else:
            return "阶段过渡期"
        
        if progress <= 0.3:
            return "早期"
        elif progress <= 0.6:
            return "中期"
        elif progress <= 0.8:
            return "后期"
        else:
            return "末期"
    
    def print_stage_overview(self):
        """打印阶段概览 - 修复版本"""
        if not self.stage_plan:
            print("  ⚠️  阶段计划数据为空")
            return
        
        print("\n📊 全书阶段计划概览:")
        
        # 尝试不同的键名
        stage_data = None
        possible_keys = ["stage_plan", "overall_stage_plan", "stages"]
        
        for key in possible_keys:
            if key in self.stage_plan:
                stage_data = self.stage_plan[key]
                break
        
        if not stage_data:
            print("  ⚠️  未找到阶段计划数据，可用键:", list(self.stage_plan.keys()))
            return
        
        # 安全地遍历阶段数据
        try:
            for stage_name, stage_info in stage_data.items():
                chapter_range = stage_info.get('chapter_range', '未知范围')
                core_tasks = stage_info.get('core_tasks', [])
                writing_focus = stage_info.get('writing_focus', '')
                
                print(f"  {chapter_range}: {stage_name}")
                if core_tasks:
                    print(f"    核心任务: {', '.join(core_tasks)}")
                if writing_focus:
                    print(f"    写作重点: {writing_focus[:50]}...")
                print()  # 空行分隔
                    
        except Exception as e:
            print(f"  ❌ 打印阶段概览时出错: {e}")
            print(f"  stage_data 类型: {type(stage_data)}")
            if isinstance(stage_data, dict):
                print(f"  stage_data 键: {list(stage_data.keys())}")