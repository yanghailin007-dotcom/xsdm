"""小说生成器主类 - 专注流程控制"""

import os
import json
import signal
import sys
import re
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any

import APIClient
import ContentGenerator
from Contexts import GenerationContext
import ElementTimingPlanner
import EventBus
import EventDrivenManager
import ForeshadowingManager
import GlobalGrowthPlanner
import ProjectManager
import QualityAssessor
import StagePlanManager
from Prompts import Prompts

class NovelGenerator:
    def __init__(self, config):
        self.config = config
        self.Prompts = Prompts
        self.api_client = APIClient.APIClient(config)
        self.event_bus = EventBus.EventBus()
        self.quality_assessor = QualityAssessor.QualityAssessor(self.api_client)  # 修复属性名
        self.novel_data = {}  # 初始化空数据结构
        
        # 确保先初始化novel_data结构
        self._initialize_novel_data_structure()

        self._initialize_managers()
        self._setup_event_handlers()

        # 设置中断信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def _initialize_managers(self):
        """初始化各管理器，明确依赖关系"""
        # 核心管理器
        self.content_generator = ContentGenerator.ContentGenerator(
            novel_generator=self, 
            api_client=self.api_client,
            config=self.config,
            event_bus=self.event_bus,
            quality_assessor=self.quality_assessor
        )
        
        self.project_manager = ProjectManager.ProjectManager()

        self.event_driven_manager = EventDrivenManager.EventDrivenManager(novel_generator=self)
        self.foreshadowing_manager = ForeshadowingManager.ForeshadowingManager(novel_generator=self)
        self.global_growth_planner = GlobalGrowthPlanner.GlobalGrowthPlanner(novel_generator=self)
        self.stage_plan_manager = StagePlanManager.StagePlanManager(novel_generator=self)
        
        # 新增：元素时机规划器
        self.element_timing_planner = ElementTimingPlanner.ElementTimingPlanner(novel_generator=self)
        
        # 设置依赖关系
        self.element_timing_planner.set_foreshadowing_manager(self.foreshadowing_manager)
        self.element_timing_planner.set_project_manager(self.project_manager)
        self.foreshadowing_manager.set_element_timing_planner(self.element_timing_planner)

        completed_chapters = len(self.novel_data.get("generated_chapters", {}))
        self.foreshadowing_manager.set_current_chapter(completed_chapters)
    
    def _setup_event_handlers(self):
        """设置事件处理器 - 补充完整的事件处理"""
        # 章节生成事件
        self.event_bus.subscribe('chapter.generated', self._on_chapter_generated)
        self.event_bus.subscribe('chapter.assessed', self._on_chapter_assessed)
        
        # 阶段计划事件
        self.event_bus.subscribe('stage.plan.ready', self._on_stage_plan_ready)
        self.event_bus.subscribe('stage.plan.ensure', self._on_stage_plan_ensure)
        
        # 错误处理事件
        self.event_bus.subscribe('error.occurred', self._on_error_occurred)
        
        # 系统准备事件
        self.event_bus.subscribe('foreshadowing.prepare', self._on_foreshadowing_prepare)
        self.event_bus.subscribe('event.prepare', self._on_event_prepare)
        self.event_bus.subscribe('growth.prepare', self._on_growth_prepare)
    
    # 添加缺失的事件处理方法
    def _on_chapter_generated(self, data):
        """处理章节生成完成事件"""
        chapter_number = data.get('chapter_number')
        result = data.get('result')
        print(f"✅ 第{chapter_number}章生成完成: {result.get('chapter_title', '未知标题')}")
        
        # 更新novel_data
        if chapter_number and result:
            self.novel_data.setdefault("generated_chapters", {})[chapter_number] = result
            self.novel_data["current_progress"]["completed_chapters"] = len(self.novel_data["generated_chapters"])
            
            # 保存章节
            self.project_manager.save_single_chapter(
                self.novel_data["novel_title"], 
                chapter_number, 
                result
            )
    
    def _on_chapter_assessed(self, data):
        """处理章节评估完成事件"""
        chapter_number = data.get('chapter_number')
        assessment = data.get('assessment')
        print(f"📊 第{chapter_number}章质量评估完成: {assessment.get('overall_score', 0):.1f}分")
    
    def _on_stage_plan_ready(self, data):
        """处理阶段计划就绪事件"""
        stage_plan = data.get('stage_plan')
        print(f"📋 阶段计划就绪: {len(stage_plan)}个阶段")
    
    def _on_stage_plan_ensure(self, data):
        """处理确保阶段计划事件"""
        chapter_number = data.get('chapter_number')
        context = data.get('context')
        print(f"🔍 确保第{chapter_number}章阶段计划")
        
        # 修复：直接调用阶段计划管理器，而不是再次触发ensure
        try:
            stage_plan = self._get_stage_plan(chapter_number)
            if not stage_plan:
                print(f"  ⚠️ 第{chapter_number}章阶段计划为空，尝试生成...")
                # 调用阶段计划管理器生成计划
                stage_plan = self.stage_plan_manager.get_stage_plan_for_chapter(chapter_number)
            
            print(f"  ✅ 第{chapter_number}章阶段计划处理完成")
            return stage_plan
        except Exception as e:
            print(f"  ❌ 处理第{chapter_number}章阶段计划时出错: {e}")
            return {}
    
    def _on_error_occurred(self, data):
        """处理错误事件"""
        error_type = data.get('type')
        chapter = data.get('chapter', '未知')
        message = data.get('message') or data.get('error', '未知错误')
        print(f"❌ 错误({error_type}) 第{chapter}章: {message}")
    
    def _on_foreshadowing_prepare(self, data):
        """处理伏笔准备事件"""
        context = data.get('context')
        print(f"🎭 准备伏笔上下文")
    
    def _on_event_prepare(self, data):
        """处理事件准备事件"""
        context = data.get('context')
        print(f"🎯 准备事件上下文")
    
    def _on_growth_prepare(self, data):
        """处理成长规划准备事件"""
        context = data.get('context')
        print(f"📈 准备成长规划上下文")
    
    def _get_stage_plan(self, chapter_number: int) -> Dict:
        """获取章节的阶段计划"""
        try:
            if hasattr(self, 'stage_plan_manager'):
                return self.stage_plan_manager.get_stage_plan_for_chapter(chapter_number)
        except Exception as e:
            print(f"获取第{chapter_number}章阶段计划失败: {e}")
        return {}
    
    def _get_cached_stage_plan(self, chapter_number: int) -> Dict:
        """获取缓存的阶段计划"""
        # 简化实现，实际应该从缓存或novel_data中获取
        return self._get_stage_plan(chapter_number)

    # 其他现有方法保持不变...
    def signal_handler(self, signum, frame):
        """处理中断信号"""
        print(f"\n\n收到中断信号，正在保存进度...")
        self.project_manager.save_project_progress(self.novel_data)
        print("进度已保存，可以安全退出。")
        sys.exit(0)
    
    def present_plan_to_user(self, plan_data: Dict) -> Dict:
        """向用户展示单一方案"""
        print("\n" + "="*60)
        print("📚 基于您的创意种子，为您生成完整小说方案")
        print("="*60)
        
        # 安全访问 plan_data 的键
        title = plan_data.get('title', '未知标题')
        synopsis = plan_data.get('synopsis', '暂无简介')
        core_direction = plan_data.get('core_direction', '暂无核心方向')
        target_audience = plan_data.get('target_audience', '暂无目标读者')
        competitive_advantage = plan_data.get('competitive_advantage', '暂无竞争优势')
        
        print(f"🎯 为您生成的方案:")
        print(f"   书名: 《{title}》")
        print(f"   简介: {synopsis}")
        print(f"   核心方向: {core_direction}")
        print(f"   目标读者: {target_audience}")
        print(f"   竞争优势: {competitive_advantage}")
        print("=" * 60)
        
        print(f"✓ 已确定方案: 《{title}》")
        print(f"  核心创作方向: {core_direction}")
        return plan_data
    
    
    def load_chapter_content(self, chapter_number: int) -> Optional[Dict]:
        """加载指定章节的完整内容"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        chapter_dir = f"小说项目/{safe_title}_章节"
        
        if not os.path.exists(chapter_dir):
            return None
            
        for filename in os.listdir(chapter_dir):
            if filename.startswith(f"第{chapter_number:03d}章_"):
                try:
                    with open(f"{chapter_dir}/{filename}", 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    print(f"加载第{chapter_number}章内容失败: {e}")
                    return None
        return None

    def choose_category(self):
        """让用户选择小说分类"""
        categories = [
            "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武",
            "悬疑灵异", "悬疑脑洞", "抗战谍战", "历史古代", "历史脑洞",
            "都市种田", "都市脑洞", "都市日常", "玄幻脑洞", "战神赘婿",
            "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
        ]
        
        print("\n📚 请选择小说分类:")
        for i, category in enumerate(categories, 1):
            print(f"  {i:2d}. {category}")
        
        while True:
            try:
                choice = input(f"请输入分类编号 (1-{len(categories)}): ").strip()
                if not choice:
                    choice = 1
                    print("使用默认分类: 西方奇幻")
                    break
                
                choice = int(choice)
                if 1 <= choice <= len(categories):
                    break
                else:
                    print(f"请输入 1-{len(categories)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
        
        selected_category = categories[choice - 1]
        self.novel_data["category"] = selected_category
        print(f"  ✓ 已选择分类: {selected_category}")

    def load_project_data(self, filename: str) -> bool:
        """加载项目数据"""
        try:
            data = self.project_manager.load_project(filename)
            if not data:
                return False
                
            # 检查必要的键是否存在
            if "novel_info" not in data:
                print("⚠️ 项目数据缺少novel_info键，尝试从其他字段构建...")
                data["novel_info"] = {
                    "title": data.get("novel_title", "未知标题"),
                    "synopsis": data.get("novel_synopsis", ""),
                    "creative_seed": data.get("creative_seed", ""),
                    "selected_plan": data.get("selected_plan", ""),
                    "category": data.get("category", "未分类")
                }

            print(f"📋 加载的数据结构:")
            print(f"  - novel_title: {data.get('novel_title', '未设置')}")
            print(f"  - novel_synopsis: {data.get('novel_synopsis', '未设置')[:50]}...")
            print(f"  - generated_chapters: {len(data.get('generated_chapters', {}))}章")
            print(f"  - current_progress: {data.get('current_progress', {})}")
            
            # 补全缺失字段
            required_fields = {
                "previous_chapter_endings": {},
                "used_chapter_titles": set(),
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            for field, default_value in required_fields.items():
                if field not in data:
                    print(f"  ⚠️  补全缺失字段: {field}")
                    data[field] = default_value
            
            # 同步数据到self.novel_data
            import copy
            self.novel_data = copy.deepcopy(data)
            
            # 设置恢复模式标志
            self.novel_data["is_resuming"] = True
            self.novel_data["resume_data"] = copy.deepcopy(data)
            
            # 为了向后兼容，设置独立的属性
            self.novel_title = self.novel_data["novel_title"]
            self.novel_synopsis = self.novel_data["novel_synopsis"]
            self.creative_seed = self.novel_data.get("creative_seed", "")
            self.selected_plan = self.novel_data.get("selected_plan", {})
            
            # 修复进度信息
            self.current_progress = self.novel_data.get("current_progress", {
                "completed_chapters": 0,
                "total_chapters": 0,
                "stage": "大纲阶段",
                "current_stage": "第一阶段"
            })

            self.ensure_stage_plan_for_chapter(len(self.novel_data["generated_chapters"]) + 1)

            # 如果进度信息为空但实际有章节，自动修复
            if (self.current_progress["total_chapters"] == 0 and 
                "generated_chapters" in self.novel_data and 
                self.novel_data["generated_chapters"]):
                
                max_chapter = max(self.novel_data["generated_chapters"].keys())
                self.current_progress["total_chapters"] = max_chapter
                self.current_progress["completed_chapters"] = len(self.novel_data["generated_chapters"])
                self.current_progress["stage"] = "写作中"
                print(f"🔄 生成器层面修复进度: {len(self.novel_data['generated_chapters'])}/{max_chapter}章")
            
            if "element_timing_plan" not in data and self.project_manager:
                # 尝试从单独的文件加载
                timing_plan = self.project_manager.load_element_timing_plan(data["novel_title"])
                if timing_plan:
                    data["element_timing_plan"] = timing_plan
                    print("  ✅ 从单独文件加载元素时机规划")
            
            # 同步数据到self.novel_data
            import copy
            self.novel_data = copy.deepcopy(data)
            
            # 初始化元素时机规划器
            if hasattr(self, 'element_timing_planner'):
                if "element_timing_plan" in self.novel_data:
                    self.element_timing_planner.element_timing_plan = self.novel_data["element_timing_plan"]
                    # 重新注册到伏笔管理器
                    self.element_timing_planner._register_elements_to_foreshadowing(
                        self.novel_data["element_timing_plan"]
                    )
                    print("  ✅ 元素时机规划已恢复并重新注册")

            # 加载其他数据
            self.market_analysis = self.novel_data.get("market_analysis", {})
            self.overall_stage_plans = self.novel_data.get("overall_stage_plans", {})
            self.stage_writing_plans = self.novel_data.get("stage_writing_plans", {})
            self.core_worldview = self.novel_data.get("core_worldview", {})
            self.character_design = self.novel_data.get("character_design", {})
            self.generated_chapters = self.novel_data.get("generated_chapters", {})
            self.plot_progression = self.novel_data.get("plot_progression", [])
            self.quality_statistics = self.novel_data.get("quality_statistics", {})
            
            # 初始化阶段计划管理器
            self._initialize_stage_plan_manager()

            self._initialize_systems()
            
            print(f"✅ 项目数据加载完成: {self.novel_title}")
            print(f"🔍 最终验证 - novel_data状态:")
            print(f"  - novel_title: {self.novel_data.get('novel_title')}")
            print(f"  - completed_chapters: {self.novel_data['current_progress'].get('completed_chapters')}")
            print(f"  - total_chapters: {self.novel_data['current_progress'].get('total_chapters')}")
            print(f"  - previous_chapter_endings: {len(self.novel_data.get('previous_chapter_endings', {}))}项")
            print(f"  - used_chapter_titles: {len(self.novel_data.get('used_chapter_titles', set()))}个")
            
            return True
            
        except KeyError as e:
            print(f"❌ 项目数据格式错误，缺少必要字段: {e}")
            import traceback
            traceback.print_exc()
            return False
        except Exception as e:
            print(f"❌ 加载项目数据失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _initialize_stage_plan_manager(self):
        """初始化阶段计划管理器"""
        try:
            if self.stage_writing_plans:
                current_stage = self.current_progress.get("current_stage", "opening_stage")
                available_stages = list(self.stage_writing_plans.keys())
                print(f"📋 可用写作阶段: {available_stages}")
                
                if current_stage not in self.stage_writing_plans:
                    current_stage = available_stages[0]
                    print(f"⚠️ 指定阶段 '{self.current_progress.get('current_stage')}' 不存在，使用第一个可用阶段: {current_stage}")
                
                self.stage_plan_manager.overall_stage_plans = self.overall_stage_plans
                self.stage_plan_manager.stage_boundaries = self.stage_plan_manager.calculate_stage_boundaries(self.current_progress['total_chapters'])
                
                current_stage_data = self.stage_writing_plans[current_stage]
                if "stage_writing_plan" in current_stage_data:
                    writing_plan = current_stage_data["stage_writing_plan"]
                    print(f"   - 当前阶段概述: {writing_plan.get('stage_overview', '无')[:100]}...")
                    print(f"   - 包含目标: {len(writing_plan.get('targets', {}))} 个")
                    print(f"   - 包含事件: {len(writing_plan.get('event_system', {}))} 个系统")
            else:
                print("⚠️ 没有可用的写作计划，阶段计划管理器保持为空")
                
        except Exception as e:
            print(f"❌ 初始化阶段计划管理器失败: {e}")
            import traceback
            traceback.print_exc()
     
    def resume_generation(self, total_chapters: int = None) -> bool:
        """继续生成小说"""
        print("   继续生成小说...")
        
        if total_chapters and total_chapters > self.novel_data["current_progress"]["total_chapters"]:
            print(f"更新总章节数: {self.novel_data['current_progress']['total_chapters']} -> {total_chapters}")
            self.novel_data["current_progress"]["total_chapters"] = total_chapters
        
        # 确定从哪一章开始继续
        start_chapter = self.novel_data["current_progress"]["completed_chapters"] + 1
        if start_chapter > self.novel_data["current_progress"]["total_chapters"]:
            print("所有章节已完成，无需继续生成")
            return True
        
        print(f"  从第{start_chapter}章开始继续生成...")
        
        # 直接开始生成章节内容
        chapters_per_batch = min(3, self.config["defaults"]["chapters_per_batch"])
        
        for batch_start in range(start_chapter, self.novel_data["current_progress"]["total_chapters"] + 1, chapters_per_batch):
            batch_end = min(batch_start + chapters_per_batch - 1, self.novel_data["current_progress"]["total_chapters"])
            self.novel_data["current_progress"]["current_batch"] += 1
            
            print(f"\n批次{self.novel_data['current_progress']['current_batch']}: 第{batch_start}-{batch_end}章")
            
            if not self.generate_chapters_batch(batch_start, batch_end):
                print(f"批次{self.novel_data['current_progress']['current_batch']}生成失败")
                continue_gen = input("是否继续生成后续章节？(y/n): ").lower()
                if continue_gen != 'y':
                    break
            
            # 批次间延迟
            batch_delay = 10 if self.novel_data["current_progress"]["total_chapters"] > 100 else 5
            print(f"等待{batch_delay}秒后继续下一批次...")
            time.sleep(batch_delay)
        
        self.novel_data["current_progress"]["stage"] = "完成"
        
        # 保存最终进度和导出总览
        self.project_manager.save_project_progress(self.novel_data)
        self.project_manager.export_novel_overview(self.novel_data)
        
        print("🎉 小说生成完成！")
        return True
    
    def full_auto_generation(self, creative_seed: str, total_chapters: int = None):
        """全自动生成完整小说 - 重新梳理的清晰流程"""
        print("🚀 开始全自动小说生成...")
        print(f"创意种子: {creative_seed}")
        
        if total_chapters is None:
            total_chapters = self.config["defaults"]["total_chapters"]
        
        # 确保 novel_data 有正确的结构
        self._initialize_novel_data_structure()
        
        # 记录创意种子和基础设置
        self.novel_data["creative_seed"] = creative_seed
        self.novel_data["current_progress"]["total_chapters"] = total_chapters
        self.novel_data["current_progress"]["start_time"] = datetime.now().isoformat()
        self.novel_data["current_progress"]["stage"] = "开始"
        self.novel_data["current_progress"]["completed_chapters"] = 0
        self.novel_data["current_progress"]["current_batch"] = 0

        # 如果是续写模式，跳过前期规划步骤
        if self.novel_data.get("is_resuming", False):
            print("📖 检测到续写模式，跳过前期规划步骤...")
            return self._resume_content_generation(total_chapters)
        
        # ==================== 第一阶段：基础规划 ====================
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划")
        print("="*60)
        
        # 步骤1: 用户输入（仅选择分类）
        self._get_user_inputs()
        
        # 步骤2: 生成单一方案
        self.novel_data["current_progress"]["stage"] = "方案生成"
        if not self._generate_and_select_plan(creative_seed):
            return False
        
        # 步骤3: 市场分析
        self.novel_data["current_progress"]["stage"] = "市场分析" 
        if not self._generate_market_analysis(creative_seed):
            return False
        
        # ==================== 第二阶段：世界观与角色 ====================
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与角色设计")
        print("="*60)
        
        # 步骤4: 世界观构建
        self.novel_data["current_progress"]["stage"] = "世界观构建"
        if not self._generate_worldview():
            return False
        
        # 步骤5: 角色设计
        self.novel_data["current_progress"]["stage"] = "角色设计"
        if not self._generate_character_design():
            return False
        
        # ==================== 第三阶段：全书规划 ====================
        print("\n" + "="*60)
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 步骤6: 生成全书阶段计划
        self.novel_data["current_progress"]["stage"] = "阶段计划"
        if not self._generate_overall_stage_plan(creative_seed, total_chapters):
            print("⚠️  全书阶段计划生成失败，使用默认阶段划分")
        
        self.novel_data["current_progress"]["stage"] = "阶段详细计划"
        if not self._generate_stage_writing_plans(
            creative_seed=creative_seed,
            novel_title=self.novel_data["novel_title"],
            novel_synopsis=self.novel_data["novel_synopsis"],
            overall_stage_plans=self.novel_data["overall_stage_plans"]  # 传递完整的 overall_stage_plans
        ):
            print("❌ 生成阶段详细写作计划失败")
            return False

        # 步骤7: 全局成长规划（人物成长、势力发展、物品升级）
        self.novel_data["current_progress"]["stage"] = "成长规划"
        if not self._generate_global_growth_plan(creative_seed, total_chapters):
            print("⚠️  全局成长规划生成失败，使用基础框架")

        self.novel_data["current_progress"]["stage"] = "元素时机规划"
        if not self._generate_element_timing_plan(creative_seed, total_chapters):
            print("⚠️  元素登场时机规划生成失败，使用基础时机")   

        # 步骤8: 初始化系统
        self.novel_data["current_progress"]["stage"] = "系统初始化"
        self._initialize_systems()
        
        # ==================== 第四阶段：内容生成准备 ====================
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 步骤9: 创建项目目录和保存初始进度
        self.novel_data["current_progress"]["stage"] = "项目初始化"
        self._initialize_project()
        
        # ==================== 第五阶段：章节内容生成 ====================
        return self._generate_all_chapters(total_chapters)

    def _generate_element_timing_plan(self, creative_seed: str, total_chapters: int) -> bool:
        """生成元素登场时机规划"""
        print("=== 步骤7.5: 制定元素登场时机规划 ===")
        
        try:
            # 确保有全局成长计划
            if not self.novel_data.get("global_growth_plan"):
                print("  ⚠️ 没有全局成长计划，无法生成元素时机规划")
                return False
            
            timing_plan = self.element_timing_planner.generate_element_timing_plan(
                self.novel_data["global_growth_plan"]
            )
            
            if timing_plan:
                self.novel_data["element_timing_plan"] = timing_plan
                print("✅ 元素登场时机规划制定完成并已保存")
                return True
            else:
                print("❌ 元素登场时机规划生成失败")
                return False
                
        except Exception as e:
            print(f"⚠️  元素时机规划器出错: {e}")
            return False

    def _evaluate_plan_quality(self, plan_data: Dict, category: str, creative_seed: str) -> bool:
        """使用AI评价方案质量，特别是书名和简介"""
        print("\n🔍 正在使用AI评价方案质量...")
        
        title = plan_data.get('title', '')
        synopsis = plan_data.get('synopsis', '')
        core_direction = plan_data.get('core_direction', '')
        
        # 构建评价提示词
        evaluation_prompt = f"""
    请对以下小说方案进行专业评价：

    【小说分类】{category}
    【创意种子】{creative_seed}

    【方案内容】
    书名：《{title}》
    简介：{synopsis}
    核心方向：{core_direction}

    """
        
        try:
            # 调用AI进行评价
            evaluation_result = self.api_client.generate_content_with_retry(
                "plan_quality_evaluation",  # 需要在config中添加这个提示词
                evaluation_prompt,
                purpose="方案质量评价"
            )
            
            if not evaluation_result:
                print("⚠️ AI评价失败，默认通过方案")
                return True
            
            # 解析评价结果
            overall_score = evaluation_result.get("overall_score", 0)
            recommendation = evaluation_result.get("recommendation", False)
            quality_verdict = evaluation_result.get("quality_verdict", "未知")
            
            print(f"📊 AI评价结果:")
            print(f"  总体评分: {overall_score:.1f}/10分")
            print(f"  质量判定: {quality_verdict}")
            print(f"  推荐使用: {'是' if recommendation else '否'}")
            
            # 显示详细评价
            title_eval = evaluation_result.get("title_evaluation", {})
            synopsis_eval = evaluation_result.get("synopsis_evaluation", {})
            
            if title_eval:
                print(f"  📖 书名评价: {title_eval.get('score', 0):.1f}分")
                if title_eval.get('strengths'):
                    print(f"    优点: {', '.join(title_eval['strengths'])}")
                if title_eval.get('weaknesses'):
                    print(f"    缺点: {', '.join(title_eval['weaknesses'])}")
            
            if synopsis_eval:
                print(f"  📝 简介评价: {synopsis_eval.get('score', 0):.1f}分")
                if synopsis_eval.get('strengths'):
                    print(f"    优点: {', '.join(synopsis_eval['strengths'])}")
                if synopsis_eval.get('weaknesses'):
                    print(f"    缺点: {', '.join(synopsis_eval['weaknesses'])}")
            
            # 决定是否通过
            if overall_score >= 8.0 and recommendation:
                print("✅ 方案质量评价通过")
                return True
            else:
                print("❌ 方案质量评价不通过")
                return False
                
        except Exception as e:
            print(f"⚠️ AI评价过程中出错: {e}，默认通过方案")
            return True

    def _generate_and_select_plan(self, creative_seed: str) -> bool:
        """生成并选择单一方案 - 自动根据分类生成主角和方案"""
        print("=== 步骤1: 基于创意种子和分类生成小说方案 ===")
        
        # 获取分类信息
        category = self.novel_data.get("category", "未分类")
        print(f"  ✓ 使用分类: {category}")
        
        # 最大重试次数
        max_retries = 3
        for attempt in range(max_retries):
            print(f"\n🔄 第{attempt + 1}次尝试生成方案...")
            
            # 生成单一方案（自动包含主角名字生成）
            plan_data = self.content_generator.generate_single_plan(creative_seed, category)
            if not plan_data:
                print("❌ 方案生成失败")
                if attempt < max_retries - 1:
                    print("  准备重试...")
                    continue
                else:
                    print("❌ 方案生成失败，终止生成")
                    return False
            
            # 对方案进行AI质量评价
            if self._evaluate_plan_quality(plan_data, category, creative_seed):
                # 方案通过评价
                self.novel_data["selected_plan"] = self._present_auto_generated_plan(plan_data)
                if not self.novel_data["selected_plan"]:
                    print("❌ 方案处理失败")
                    continue
                
                # 设置选定方案的小说标题和简介
                self.novel_data["novel_title"] = self.novel_data["selected_plan"]["title"]
                self.novel_data["novel_synopsis"] = self.novel_data["selected_plan"]["synopsis"]
                
                print(f"✅ 已自动生成并通过质量评价的方案: 《{self.novel_data['novel_title']}》")
                return True
            else:
                print(f"❌ 第{attempt + 1}次生成的方案未通过质量评价")
                if attempt < max_retries - 1:
                    print("  重新生成方案...")
                    continue
        
        print("❌ 所有方案生成尝试均未通过质量评价，终止生成")
        return False

    def _present_auto_generated_plan(self, plan_data: Dict) -> Dict:
        """展示自动生成的单一方案"""
        print("\n" + "="*60)
        print("📚 基于您的创意种子和分类，已生成完整小说方案")
        print("="*60)
        
        # 安全访问 plan_data 的键
        title = plan_data.get('title', '未知标题')
        synopsis = plan_data.get('synopsis', '暂无简介')
        core_direction = plan_data.get('core_direction', '暂无核心方向')
        target_audience = plan_data.get('target_audience', '暂无目标读者')
        competitive_advantage = plan_data.get('competitive_advantage', '暂无竞争优势')
        
        print(f"🎯 为您生成的方案:")
        print(f"   书名: 《{title}》")
        print(f"   简介: {synopsis}")
        print(f"   核心方向: {core_direction}")
        print(f"   目标读者: {target_audience}")
        print(f"   竞争优势: {competitive_advantage}")
        print("=" * 60)
        
        # 显示生成的主角名字
        if self.content_generator.custom_main_character_name:
            print(f"👤 自动生成主角: {self.content_generator.custom_main_character_name}")
        
        print("✓ 方案已确定，开始后续生成流程...")
        return plan_data

    def _initialize_novel_data_structure(self):
        """初始化 novel_data 数据结构"""
        if not hasattr(self, 'novel_data') or not self.novel_data:
            self.novel_data = {}
        
        # 确保所有必要的键都存在
        required_keys = {
            "current_progress": {
                "completed_chapters": 0,
                "total_chapters": 0,
                "stage": "未开始",
                "current_stage": "第一阶段",
                "current_batch": 0,
                "start_time": None
            },
            "generated_chapters": {},
            "used_chapter_titles": set(),
            "previous_chapter_endings": {},
            "plot_progression": [],
            "chapter_quality_records": {},
            "optimization_history": {},
            "is_resuming": False,
            "resume_data": None,
            "market_analysis": {},
            "overall_stage_plans": {},
            "stage_writing_plans": {},
            "core_worldview": {},
            "character_design": {},
            "global_growth_plan": {},
            "quality_statistics": {}
        }
        
        for key, default_value in required_keys.items():
            if key not in self.novel_data:
                self.novel_data[key] = default_value
            elif key == "current_progress" and isinstance(default_value, dict):
                # 确保 current_progress 中的所有子键都存在
                for sub_key, sub_default in default_value.items():
                    if sub_key not in self.novel_data[key]:
                        self.novel_data[key][sub_key] = sub_default
                    
    def _get_user_inputs(self):
        """获取用户输入（仅选择分类）"""
        self.choose_category()

    def _generate_market_analysis(self, creative_seed: str) -> bool:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        self.novel_data["market_analysis"] = self.content_generator.generate_market_analysis(
            creative_seed, self.novel_data["selected_plan"])
        
        if not self.novel_data["market_analysis"]:
            print("  ❌ 市场分析失败，终止生成")
            return False
        
        print("  ✅ 市场分析完成")
        return True

    def _generate_worldview(self) -> bool:
        """生成世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        self.novel_data["core_worldview"] = self.content_generator.generate_core_worldview(
            self.novel_data["novel_title"], 
            self.novel_data["novel_synopsis"], 
            self.novel_data["selected_plan"], 
            self.novel_data.get("market_analysis", {})
        )
        
        if not self.novel_data["core_worldview"]:
            print("❌ 世界观构建失败，终止生成")
            return False
        
        print("✅ 世界观构建完成")
        return True

    def _generate_character_design(self) -> bool:
        """生成角色设计"""
        print("=== 步骤4: 设计主要角色 ===")
        
        self.novel_data["character_design"] = self.content_generator.generate_character_design(
            self.novel_data["novel_title"], 
            self.novel_data["core_worldview"], 
            self.novel_data["selected_plan"], 
            self.novel_data.get("market_analysis", {})
        )
        
        if not self.novel_data["character_design"]:
            print("❌ 角色设计失败，终止生成")
            return False
        
        print("✅ 角色设计完成")
        return True
    
    def _generate_stage_writing_plans(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                    overall_stage_plans: Dict) -> bool:
        """为每个阶段生成详细的写作计划 - 修正版本"""
        print("=== 步骤6: 生成各阶段详细写作计划 ===")
        
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            # 使用 overall_stage_plans 中的阶段定义
            stage_plan_container = overall_stage_plans  # 外层容器
            stage_plan_dict = stage_plan_container["overall_stage_plan"]  # 核心阶段字典
            
            # 为每个阶段生成详细写作计划
            self.novel_data["stage_writing_plans"] = {}
            
            for stage_name, stage_info in stage_plan_dict.items():
                # 提取章节范围字符串，例如 "第1章-第3章" -> "1-3"
                chapter_range_str = stage_info["chapter_range"]
                
                # 将中文章节范围转换为数字范围
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    # 如果解析失败，使用默认范围
                    stage_range = "1-3"
                
                print(f"  📋 生成 {stage_name} 的详细写作计划...")
                print(f"  📋 章节范围: {stage_range}")
                
                # 调用 StagePlanManager 的方法生成详细计划
                stage_plan = self.stage_plan_manager.generate_stage_writing_plan(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=creative_seed,
                    novel_title=novel_title,
                    novel_synopsis=novel_synopsis,
                    overall_stage_plan=stage_plan_dict  # 传递完整的 overall_stage_plans
                )
                
                if stage_plan:
                    self.novel_data["stage_writing_plans"][stage_name] = stage_plan
                    print(f"  ✅ {stage_name} 详细计划生成成功")
                else:
                    print(f"  ❌ {stage_name} 详细计划生成失败")
            
            # 检查是否至少有一个阶段的计划生成成功
            success_count = len(self.novel_data["stage_writing_plans"])
            if success_count > 0:
                print(f"✅ 阶段详细计划生成完成: {success_count}/{len(stage_plan_dict)} 个阶段")
                return True
            else:
                print("❌ 所有阶段详细计划生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 生成阶段详细写作计划时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _generate_overall_stage_plan(self, creative_seed: str, total_chapters: int) -> bool:
        """生成全书阶段计划"""
        print("=== 步骤5: 生成全书阶段计划 ===")
        
        self.novel_data["overall_stage_plans"] = self.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data.get("market_analysis", {}),
            total_chapters
        )
        
        if self.novel_data["overall_stage_plans"]:
            print("✅ 全书阶段计划生成成功")
            return True
        else:
            return False

    def _generate_global_growth_plan(self, creative_seed: str, total_chapters: int) -> bool:
        """生成全局成长规划 - 精简分层版本"""
        print("=== 步骤6: 制定全书成长规划框架 ===")
        
        try:
            self.novel_data["global_growth_plan"] = self.global_growth_planner.generate_global_growth_plan()
            
            if self.novel_data["global_growth_plan"]:
                print("✅ 全书成长规划框架制定完成")
                return True
            else:
                print("❌ 全局成长规划生成失败，使用基础框架")
                return False
                
        except Exception as e:
            print(f"⚠️  全局成长规划器出错: {e}，使用基础框架")
            return False

    def _initialize_systems(self):
        """初始化各种系统"""
        print("=== 步骤7: 初始化系统 ===")
        
        # 初始化事件体系
        if self.novel_data["overall_stage_plans"]:
            self.event_driven_manager.initialize_event_system()
            print("✅ 事件系统初始化完成")
        
        # 初始化伏笔管理系统
        if self.novel_data["character_design"]:
            self.initialize_foreshadowing_elements()
            print("✅ 伏笔管理系统初始化完成")
        
        print("✅ 第一阶段详细写作计划已生成")

    def _initialize_project(self):
        """初始化项目"""
        # 创建项目目录
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        os.makedirs(f"小说项目/{safe_title}_章节", exist_ok=True)
        
        # 保存初始进度
        self.project_manager.save_project_progress(self.novel_data)
        print("✅ 项目初始进度已保存")

    def _generate_all_chapters(self, total_chapters: int) -> bool:
        """生成所有章节内容"""
        print("\n" + "="*60)
        print("📖 第五阶段：章节内容生成")
        print("="*60)
        
        start_chapter = 1
        print(f"开始生成第{start_chapter}-{total_chapters}章小说内容...")
        print("基于选定方案和创作方向进行创作")
        print("每章生成后将进行质量评估和优化")
        print("特别优化章节衔接，确保情节连贯性")
        print("🤖 新增AI痕迹检测和消除功能")
        print("每章将单独保存为包含质量评估的JSON文件")
        print("这个过程可能需要较长时间，请耐心等待...")
        print("提示: 按Ctrl+C可以安全中断，下次可继续生成")
        
        # 对于大规模生成，使用更小的批次
        actual_chapters_per_batch = min(3, self.config["defaults"]["chapters_per_batch"])
        
        for batch_start in range(start_chapter, total_chapters + 1, actual_chapters_per_batch):
            batch_end = min(batch_start + actual_chapters_per_batch - 1, total_chapters)
            self.novel_data["current_progress"]["current_batch"] += 1
            
            print(f"\n批次{self.novel_data['current_progress']['current_batch']}: 第{batch_start}-{batch_end}章")
            
            if not self.generate_chapters_batch(batch_start, batch_end):
                print(f"❌ 批次{self.novel_data['current_progress']['current_batch']}生成失败")
                continue_gen = input("是否继续生成后续章节？(y/n): ").lower()
                if continue_gen != 'y':
                    break
            
            # 批次间延迟
            batch_delay = 10 if total_chapters > 100 else 5
            if batch_end < total_chapters:
                print(f"等待{batch_delay}秒后继续下一批次...")
                time.sleep(batch_delay)
        
        return self._finalize_generation()

    def _resume_content_generation(self, total_chapters: int) -> bool:
        """续写模式的内容生成"""
        print("🔄 续写模式：直接开始内容生成...")
        
        # 确定起始章节
        start_chapter = self.novel_data["current_progress"]["completed_chapters"] + 1
        if start_chapter > total_chapters:
            print("✅ 所有章节已完成，无需继续生成")
            return True
        
        print(f"从第{start_chapter}章开始继续生成...")
        return self._generate_all_chapters(total_chapters)

    def _finalize_generation(self) -> bool:
        """完成生成过程"""
        self.novel_data["current_progress"]["stage"] = "完成"
        
        # 保存最终进度和导出总览
        self.project_manager.save_project_progress(self.novel_data)
        self.project_manager.export_novel_overview(self.novel_data)
        
        print("\n🎉 小说生成完成！")
        self._print_generation_summary()
        return True

    def generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """批量生成章节 - 修复版本，确保正确处理上下文"""
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                print(f"\n📖 开始生成第{chapter_num}章...")
                
                # 1. 准备生成上下文
                context = self._prepare_generation_context(chapter_num)
                
                # 确保上下文不为None
                if context is None:
                    print(f"❌ 第{chapter_num}章生成上下文为None，跳过该章")
                    self.event_bus.publish('error.occurred', {
                        'type': 'context_none',
                        'chapter': chapter_num,
                        'message': '生成上下文为None'
                    })
                    continue
                
                # 验证上下文
                if not hasattr(context, 'validate'):
                    print(f"❌ 第{chapter_num}章上下文缺少validate方法，跳过该章")
                    self.event_bus.publish('error.occurred', {
                        'type': 'context_invalid',
                        'chapter': chapter_num,
                        'message': '上下文对象无效，缺少validate方法'
                    })
                    continue
                
                # 执行验证
                is_valid, validation_message = context.validate()
                if not is_valid:
                    print(f"⚠️ 第{chapter_num}章上下文验证失败: {validation_message}")
                    # 不立即跳过，尝试使用这个上下文
                
                # 2. 通过事件总线协调各模块准备
                preparation_result = self._coordinate_chapter_preparation(context)
                if not preparation_result['success']:
                    print(f"⚠️ 第{chapter_num}章准备阶段失败，但继续尝试生成")
                
                # 3. 委托给ContentGenerator生成内容
                print(f"🔄 调用ContentGenerator生成第{chapter_num}章内容...")
                chapter_result = self.content_generator.generate_chapter_content_for_novel(chapter_num, self.novel_data, context)
                
                if not chapter_result:
                    print(f"❌ 第{chapter_num}章内容生成失败")
                    self.event_bus.publish('error.occurred', {
                        'type': 'generation_failed',
                        'chapter': chapter_num,
                        'message': 'ContentGenerator返回空结果'
                    })
                    continue
                
                # 4. 发布生成完成事件
                self.event_bus.publish('chapter.generated', {
                    'chapter_number': chapter_num,
                    'result': chapter_result,
                    'context': context
                })
                
                print(f"✅ 第{chapter_num}章生成完成: {chapter_result.get('chapter_title', '未知标题')}")
                
            except Exception as e:
                error_msg = f"生成第{chapter_num}章时出错: {e}"
                print(f"❌ {error_msg}")
                import traceback
                traceback.print_exc()
                
                self.event_bus.publish('error.occurred', {
                    'type': 'generation_failed',
                    'chapter': chapter_num,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                })
        
        return True

    def _prepare_generation_context(self, chapter_num: int) -> GenerationContext:
        """准备生成上下文 - 修复版本，确保返回有效的上下文对象"""
        try:
            print(f"🔍 开始准备第{chapter_num}章生成上下文...")
            
            # 获取各个管理器的上下文
            print(f"  📊 获取事件上下文...")
            event_context = {}
            if hasattr(self, 'event_driven_manager') and hasattr(self.event_driven_manager, 'get_context'):
                try:
                    event_context = self.event_driven_manager.get_context(chapter_num)
                    print(f"    ✅ 事件上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取事件上下文失败: {e}")
                    event_context = {}
            
                print(f"  🎭 获取伏笔上下文...")
                foreshadowing_context = {}
                if hasattr(self, 'foreshadowing_manager') and hasattr(self.foreshadowing_manager, 'get_context'):
                    try:
                        foreshadowing_context = self.foreshadowing_manager.get_context(chapter_num)
                        print(f"    ✅ 伏笔上下文获取成功")
                        print(f"    📊 伏笔上下文内容:")
                        print(f"      - 引入元素: {len(foreshadowing_context.get('elements_to_introduce', []))}")
                        print(f"      - 发展元素: {len(foreshadowing_context.get('elements_to_develop', []))}")
                        print(f"      - 焦点: {foreshadowing_context.get('foreshadowing_focus', '无')}")
                        
                        # 打印具体的元素信息
                        for i, elem in enumerate(foreshadowing_context.get('elements_to_introduce', [])[:3]):
                            print(f"        🆕 引入{i+1}: {elem.get('name', '未知')}")
                        for i, elem in enumerate(foreshadowing_context.get('elements_to_develop', [])[:3]):
                            print(f"        📈 发展{i+1}: {elem.get('name', '未知')}")
                            
                    except Exception as e:
                        print(f"    ⚠️ 获取伏笔上下文失败: {e}")
                        import traceback
                        traceback.print_exc()
                        foreshadowing_context = {}
            
            print(f"  📈 获取成长规划上下文...")
            growth_context = {}
            if hasattr(self, 'global_growth_planner') and hasattr(self.global_growth_planner, 'get_context'):
                try:
                    growth_context = self.global_growth_planner.get_context(chapter_num)
                    print(f"    ✅ 成长规划上下文获取成功: {type(growth_context)}, 长度: {len(str(growth_context))}")
                except Exception as e:
                    print(f"    ⚠️ 获取成长规划上下文失败: {e}")
                    growth_context = {}
            
            print(f"  🎯 获取阶段计划...")
            stage_plan = {}
            if hasattr(self, 'ensure_stage_plan_for_chapter'):
                try:
                    stage_plan = self.ensure_stage_plan_for_chapter(chapter_num) or {}
                    print(f"    ✅ 阶段计划获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取阶段计划失败: {e}")
                    stage_plan = {}
            
            # 检查novel_data
            print(f"  📚 检查novel_data...")
            if not hasattr(self, 'novel_data') or not self.novel_data:
                print(f"    ⚠️ novel_data不存在或为空，创建基础结构")
                self._initialize_novel_data_structure()
            
            total_chapters = self.novel_data["current_progress"]["total_chapters"]
            print(f"    ✅ novel_data存在, 总章节数: {total_chapters}")
            
            # 生成事件和伏笔指导，并存储到novel_data中供ContentGenerator使用
            print(f"  🎯 生成事件和伏笔指导...")
            try:
                event_guidance = self.event_driven_manager.generate_event_execution_prompt(chapter_num)
                foreshadowing_guidance = self.foreshadowing_manager.generate_foreshadowing_prompt(chapter_num)
                
                # 存储到临时字段中，供ContentGenerator使用
                self.novel_data['_current_chapter_guidance'] = {
                    'event_guidance': event_guidance,
                    'foreshadowing_guidance': foreshadowing_guidance
                }
                print(f"    ✅ 事件和伏笔指导已生成并存储")
            except Exception as e:
                print(f"    ⚠️ 生成事件/伏笔指导失败: {e}")
                self.novel_data['_current_chapter_guidance'] = {}
            
            # 创建 GenerationContext 实例
            print(f"  🏗️ 创建GenerationContext实例...")
            context = GenerationContext(
                chapter_number=chapter_num,
                total_chapters=total_chapters,
                novel_data=self.novel_data,
                stage_plan=stage_plan,
                event_context=event_context,
                foreshadowing_context=foreshadowing_context,
                growth_context=growth_context
            )
            
            # 为上下文添加 generator 引用
            context.generator = self
            
            # 验证上下文
            print(f"  ✅ 第{chapter_num}章上下文创建成功，开始验证...")
            is_valid, validation_message = context.validate()
            if not is_valid:
                print(f"  ⚠️ 上下文验证警告: {validation_message}")
            else:
                print(f"  ✅ 上下文验证通过")
            
            print(f"  ✅ 第{chapter_num}章上下文准备完成")
            
            return context
            
        except Exception as e:
            print(f"❌ 准备生成上下文失败: {e}")
            import traceback
            traceback.print_exc()
            
            # 返回基础上下文，确保不会返回None
            print(f"🔄 返回基础上下文作为备选...")
            base_context = GenerationContext(
                chapter_number=chapter_num,
                total_chapters=self.novel_data.get("current_progress", {}).get("total_chapters", 30) if hasattr(self, 'novel_data') and self.novel_data else 30,
                novel_data=self.novel_data if hasattr(self, 'novel_data') else {},
                stage_plan={},
                event_context={},
                foreshadowing_context={},
                growth_context={}
            )
            base_context.generator = self
            
            # 验证基础上下文
            is_valid, validation_message = base_context.validate()
            if not is_valid:
                print(f"⚠️ 基础上下文验证警告: {validation_message}")
            
            return base_context
        
    def _coordinate_chapter_preparation(self, context: GenerationContext) -> Dict:
        """协调章节准备 - 通过事件总线"""
        preparation_events = [
            'foreshadowing.prepare',
            'event.prepare', 
            'growth.prepare'
        ]
        
        results = {}
        for event_type in preparation_events:
            self.event_bus.publish(event_type, {'context': context})
            # 可以等待异步结果或设置超时
        
        return {'success': True, 'details': results}

    def _print_generation_summary(self):
        """打印生成摘要"""
        print("\n" + "="*60)
        print("🎊 小说生成完成摘要")
        print("="*60)
        
        print(f"📖 小说标题: {self.novel_data['novel_title']}")
        print(f"📚 小说分类: {self.novel_data.get('category', '未分类')}") 
        print(f"📝 总章节数: {self.novel_data['current_progress']['completed_chapters']}/{self.novel_data['current_progress']['total_chapters']}")
        
        # 显示质量信息
        stats = self.project_manager.calculate_quality_statistics(self.novel_data)
        if stats:
            print(f"📊 平均质量评分: {stats['average_score']:.1f}/10分")
            print(f"🔧 优化章节比例: {stats['optimization_rate']}%")
            
            ai_stats = stats.get('ai_quality', {})
            print(f"🤖 AI痕迹平均得分: {ai_stats.get('average_ai_score', 2):.1f}/2分")
            print(f"🔍 存在AI痕迹章节: {ai_stats.get('chapters_with_ai_artifacts', 0)}章")
        
        if self.novel_data["selected_plan"]:
            print(f"🎯 创作方向: {self.novel_data['selected_plan']['core_direction']}")
            print(f"👥 目标读者: {self.novel_data['selected_plan']['target_audience']}")
        
        if self.novel_data["character_design"]:
            main_char = self.novel_data["character_design"]['main_character']
            print(f"👤 主角: {main_char['name']} - {main_char['personality']}")
        
        if self.novel_data["core_worldview"]:
            print(f"🌍 世界观: {self.novel_data['core_worldview']['era']} - {self.novel_data['core_worldview']['core_conflict']}")
        
        # 显示章节衔接情况
        if len(self.novel_data["generated_chapters"]) > 1:
            good_connections = sum(1 for i in range(2, len(self.novel_data["generated_chapters"]) + 1)
                               if i in self.novel_data["generated_chapters"] and 
                               "自然承接" in self.novel_data["generated_chapters"][i].get("connection_to_previous", ""))
            print(f"🔗 章节衔接质量: {good_connections}/{len(self.novel_data['generated_chapters'])-1} 章衔接良好")
        
        # 显示文件结构
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        print(f"📁 文件结构:")
        print(f"   项目信息: 小说项目/{safe_title}_项目信息.json")
        print(f"   章节总览: 小说项目/{safe_title}_章节总览.json")
        print(f"   章节文件: 小说项目/{safe_title}_章节/第XXX章_标题.txt")
        
        # 统计字数
        total_words = sum(chapter.get('word_count', 0) for chapter in self.novel_data["generated_chapters"].values())
        print(f"📊 总字数: {total_words}字")
        
        # 生成时间统计
        if self.novel_data['current_progress']['start_time']:
            try:
                start_time = datetime.fromisoformat(self.novel_data['current_progress']['start_time'])
                end_time = datetime.now()
                duration = end_time - start_time
                print(f"⏱️ 生成耗时: {duration.total_seconds()/60:.1f}分钟")
            except:
                print("⏱️ 生成耗时: 无法计算")
        
        print("="*60)

    def ensure_stage_plan_for_chapter(self, chapter_number: int):
        """确保章节有阶段计划 - 修复版本，同时更新事件系统"""
        print(f"🔍 确保第{chapter_number}章阶段计划")
        
        # 获取全局阶段计划
        if not self.novel_data.get("overall_stage_plans") or not self.novel_data.get("stage_writing_plans"):
            print(f"  ⚠️ 没有可用的阶段计划数据")
            return None
        
        # 查找章节所属的阶段
        stage_name = self._find_stage_for_chapter(chapter_number)
        if not stage_name:
            print(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
            return None
        
        # 检查阶段是否发生变化
        self.current_progress['current_stage'] = stage_name
        current_stage = getattr(self, '_current_stage', None)
        if current_stage != stage_name:
            print(f"🔄 检测到阶段变化: {current_stage} -> {stage_name}")
            self._current_stage = stage_name
            
            # 更新事件系统以反映新阶段
            self._update_event_system_for_stage(stage_name, chapter_number)
        
        # 获取该阶段的详细写作计划
        stage_plan_data = self.novel_data["stage_writing_plans"].get(stage_name)
        if not stage_plan_data:
            print(f"  ⚠️ 没有找到{stage_name}的详细写作计划")
            return None
        
        # 确保返回的数据包含 stage_writing_plan 字段
        if "stage_writing_plan" in stage_plan_data:
            stage_plan = stage_plan_data["stage_writing_plan"]
        else:
            print(f"  ⚠️ 阶段计划数据缺少stage_writing_plan字段，使用原始数据")
            stage_plan = stage_plan_data
        
        print(f"  ✅ 第{chapter_number}章属于{stage_name}阶段")
        print(f"  📋 阶段计划类型: 包含字段: {list(stage_plan.keys())}")
        
        return stage_plan

    def _update_event_system_for_stage(self, stage_name: str, chapter_number: int):
        """为特定阶段更新事件系统"""
        print(f"🔄 为{stage_name}阶段更新事件系统...")
        
        try:
            # 获取该阶段的详细计划
            stage_plan_data = self.novel_data["stage_writing_plans"].get(stage_name)
            if not stage_plan_data:
                print(f"  ⚠️ 没有找到{stage_name}的详细计划数据")
                return
            
            # 提取事件系统信息
            event_system = {}
            if "stage_writing_plan" in stage_plan_data:
                event_system = stage_plan_data["stage_writing_plan"].get("event_system", {})
            else:
                event_system = stage_plan_data.get("event_system", {})
            
            # 更新事件驱动管理器
            if hasattr(self, 'event_driven_manager') and self.event_driven_manager:
                # 清除旧的事件
                self.event_driven_manager.active_events.clear()
                
                # 添加新阶段的事件
                if event_system:
                    # 处理重大事件
                    major_events = event_system.get("major_events", [])
                    for event in major_events:
                        if event:
                            self.event_driven_manager.add_event(
                                name=event.get("name", f"重大事件_{len(self.event_driven_manager.active_events)}"),
                                event_type="major",
                                start_chapter=event.get("start_chapter", chapter_number),
                                description=event.get("description", ""),
                                impact_level=event.get("impact_level", "high")
                            )
                    
                    # 处理大事件
                    big_events = event_system.get("big_events", [])
                    for event in big_events:
                        if event:
                            self.event_driven_manager.add_event(
                                name=event.get("name", f"大事件_{len(self.event_driven_manager.active_events)}"),
                                event_type="big",
                                start_chapter=event.get("start_chapter", chapter_number),
                                description=event.get("description", ""),
                                impact_level=event.get("impact_level", "medium")
                            )
                    
                    print(f"  ✅ 事件系统已更新: {len(major_events)}个重大事件, {len(big_events)}个大事件")
                else:
                    print(f"  ⚠️ {stage_name}阶段没有事件系统定义")
            
            # 同时更新伏笔管理器
            self._update_foreshadowing_for_stage(stage_name, chapter_number)
            
        except Exception as e:
            print(f"❌ 更新{stage_name}阶段事件系统失败: {e}")
            import traceback
            traceback.print_exc()

    def _update_foreshadowing_for_stage(self, stage_name: str, chapter_number: int):
        """为特定阶段更新伏笔系统"""
        try:
            stage_plan_data = self.novel_data["stage_writing_plans"].get(stage_name)
            if not stage_plan_data:
                return
            
            # 提取需要铺垫的元素
            if "stage_writing_plan" in stage_plan_data:
                stage_plan = stage_plan_data["stage_writing_plan"]
            else:
                stage_plan = stage_plan_data
            
            # 从阶段计划中提取伏笔元素
            special_elements = []
            
            # 检查事件系统中的特殊元素
            event_system = stage_plan.get("event_system", {})
            for event_type in ["major_events", "big_events"]:
                events = event_system.get(event_type, [])
                for event in events:
                    if event and "special_elements" in event:
                        special_elements.append({
                            "name": event["special_elements"],
                            "type": "concept",
                            "purpose": f"为{event.get('name', '事件')}做铺垫",
                            "target_chapter": event.get("start_chapter", chapter_number + 5)
                        })
            
            # 更新伏笔管理器
            if hasattr(self, 'foreshadowing_manager') and self.foreshadowing_manager:
                # 清除旧的阶段相关伏笔
                self.foreshadowing_manager.clear_stage_elements()
                
                # 添加新的伏笔元素
                for element in special_elements:
                    self.foreshadowing_manager.register_element(
                        element_type=element["type"],
                        element_name=element["name"],
                        importance="medium",
                        target_chapter=element["target_chapter"],
                        purpose=element["purpose"]
                    )
                
                print(f"  ✅ 伏笔系统已更新: {len(special_elements)}个新元素")
                
        except Exception as e:
            print(f"❌ 更新{stage_name}阶段伏笔系统失败: {e}")

    def _find_stage_for_chapter(self, chapter_number: int) -> str:
        """确定章节所属的阶段"""
        overall_plan = self.novel_data["overall_stage_plans"]["overall_stage_plan"]
        
        for stage_name, stage_info in overall_plan.items():
            # 提取章节范围字符串，例如 "第1章-第3章" -> (1, 3)
            chapter_range_str = stage_info["chapter_range"]
            
            # 将中文章节范围转换为数字范围
            import re
            numbers = re.findall(r'\d+', chapter_range_str)
            if len(numbers) >= 2:
                start_chap = int(numbers[0])
                end_chap = int(numbers[1])
                
                # 检查章节是否在此阶段范围内
                if start_chap <= chapter_number <= end_chap:
                    return stage_name
        
        return None

    def _check_and_generate_new_stage_plan(self, chapter_number: int):
        """检查是否需要为当前章节生成新的阶段详细计划 - 协调阶段计划管理器"""
        try:
            print(f"  🔍 检查第{chapter_number}章是否需要新的阶段计划...")
            
            # 获取当前章节所属的阶段
            current_stage = self.stage_plan_manager.get_current_stage(chapter_number)
            print(f"  当前阶段: {current_stage}")
            
            # 检查该阶段是否已经有详细计划
            existing_plan = self.novel_data["stage_writing_plans"].get(current_stage)
            
            if not existing_plan:
                print(f"  ⚠️ 阶段 '{current_stage}' 没有详细计划，正在生成...")
                
                # 生成该阶段的详细计划
                stage_plan = self.stage_plan_manager.get_stage_plan_for_chapter(chapter_number)
                
                if stage_plan:
                    self.novel_data["stage_writing_plans"][current_stage] = stage_plan
                    print(f"  ✅ 已生成 '{current_stage}' 的详细写作计划")
                    
                    # 更新事件系统
                    self.event_driven_manager.update_event_system()
                    print(f"  ✅ 事件系统已更新")
                    
                    return stage_plan
                else:
                    print(f"  ❌ 生成 '{current_stage}' 阶段计划失败")
            else:
                print(f"  ✅ 阶段 '{current_stage}' 已有详细计划")
                
            return existing_plan
            
        except Exception as e:
            print(f"❌ 检查阶段计划时出错: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return None

    def initialize_foreshadowing_elements(self):
        """初始化需要铺垫的重要元素 - 协调伏笔管理器"""
        # 从世界观中提取重要势力
        if self.novel_data["core_worldview"]:
            factions = self.novel_data["core_worldview"].get("major_factions", [])
            for i, faction in enumerate(factions):
                intro_chapter = 10 + (i * 15)
                self.foreshadowing_manager.register_element(
                    "factions", faction, "major", min(intro_chapter, 50)
                )
                print(f"✓ 从世界观注册势力伏笔: {faction}")
        
        # 从角色设计中提取重要配角/反派
        if self.novel_data["character_design"]:
            important_chars = self.novel_data["character_design"].get("important_characters", [])
            for i, char in enumerate(important_chars):
                if i < 3:  # 只取前3个重要角色
                    intro_chapter = 5 + (i * 8)
                    self.foreshadowing_manager.register_element(
                        "characters", char["name"], "major", intro_chapter
                    )
                    print(f"✓ 从角色设计注册角色伏笔: {char['name']}")
        
        # 从各阶段写作计划中提取重要物品/概念
        if self.novel_data["stage_writing_plans"]:
            print("🔍 从阶段写作计划提取伏笔元素...")
            for stage_name, stage_plan in self.novel_data["stage_writing_plans"].items():
                try:
                    if not stage_plan:
                        continue
                        
                    # 事件系统可能在不同的位置
                    event_system = {}
                    if "stage_writing_plan" in stage_plan and stage_plan["stage_writing_plan"]:
                        event_system = stage_plan["stage_writing_plan"].get("event_system", {})
                    elif "event_system" in stage_plan:
                        event_system = stage_plan["event_system"]
                    else:
                        event_system = stage_plan
                    
                    # 提取重大事件
                    major_events = event_system.get("major_events", [])
                    for event in major_events:
                        if event and "special_elements" in event and event["special_elements"]:
                            start_chapter = event.get("start_chapter", 10)
                            self.foreshadowing_manager.register_element(
                                "concepts", event["special_elements"], "medium", start_chapter
                            )
                            print(f"  ✓ 从{stage_name}注册概念伏笔: {event['special_elements']} (第{start_chapter}章)")
                    
                    # 提取大事件中的元素
                    big_events = event_system.get("big_events", [])
                    for event in big_events:
                        if event and "special_elements" in event and event["special_elements"]:
                            start_chapter = event.get("start_chapter", 15)
                            self.foreshadowing_manager.register_element(
                                "items", event["special_elements"], "minor", start_chapter
                            )
                            print(f"  ✓ 从{stage_name}注册物品伏笔: {event['special_elements']} (第{start_chapter}章)")
                            
                except Exception as e:
                    print(f"  ⚠️ 处理{stage_name}阶段计划时出错: {e}")
                    continue
        
        print("✅ 伏笔元素初始化完成")

    def get_stage_boundary_info(self) -> Dict:
        """获取阶段边界信息 - 协调阶段计划管理器"""
        if hasattr(self.stage_plan_manager, 'stage_boundaries'):
            return {
                "stage_boundaries": self.stage_plan_manager.stage_boundaries,
                "current_stage_plan": self.stage_plan_manager.overall_stage_plans
            }
        return {"stage_boundaries": {}, "current_stage_plan": {}}

    # 简化版本
    def print_generation_summary(self):
        """打印小说生成摘要 - 简化版本"""
        print("\n" + "="*50)
        print("🎉 小说生成完成！")
        print("="*50)
        
        novel_title = self.novel_data.get("novel_title", "未知小说")
        total_chapters = self.novel_data["current_progress"]["total_chapters"]
        generated_chapters = self.novel_data.get("generated_chapters", {})
        success_count = len(generated_chapters)
        
        print(f"📖 小说标题: {novel_title}")
        print(f"📊 总章节数: {total_chapters}")
        print(f"✅ 成功生成: {success_count}章")
        print(f"📈 完成进度: {success_count}/{total_chapters}")
        
        # 字数统计
        total_words = sum(chapter_data.get("word_count", 0) for chapter_data in generated_chapters.values())
        print(f"📝 总字数: {total_words:,}字")
        
        # 质量统计
        quality_scores = [chapter_data.get("quality_score", 0) for chapter_data in generated_chapters.values() if "quality_score" in chapter_data]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"⭐ 平均质量: {avg_quality:.1f}/10分")
        
        print("="*50)
        
    def print_foundation_quality_report(self):
        """打印基础内容质量报告"""
        print("\n" + "="*50)
        print("📊 基础内容质量报告")
        print("="*50)
        
        foundation_elements = {
            "方案设计": self.novel_data.get("selected_plan"),
            "市场分析": self.novel_data.get("market_analysis"), 
            "世界观": self.novel_data.get("core_worldview"),
            "角色设计": self.novel_data.get("character_design"),
            "全书阶段计划": self.novel_data.get("overall_stage_plans"),
            "阶段详细计划": self.novel_data.get("stage_writing_plans")
        }
        
        for element_name, element_data in foundation_elements.items():
            if element_data:
                print(f"✅ {element_name}: 已完成")
            else:
                print(f"❌ {element_name}: 缺失")
        
        print("="*50)        