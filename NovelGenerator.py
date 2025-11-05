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

from DouBaoImageGenerator import DouBaoImageGenerator
import doubaoconfig

class NovelGenerator:
    def __init__(self, config):
        self.config = config
        self.Prompts = Prompts
        self.api_client = APIClient.APIClient(config)
        self.event_bus = EventBus.EventBus()
        self.quality_assessor = QualityAssessor.QualityAssessor(self.api_client)  # 修复属性名
        self.novel_data = {}  # 初始化空数据结构
        # 初始化客户端
        # 🆕 新增：初始化封面生成器
        self.cover_generator = None
        self._initialize_cover_generator()

        default_provider = self.api_client.get_default_provider()
        print(f"默认提供商: {default_provider}")
        # 获取当前使用的模型
        current_model = self.api_client.get_current_model()
        print(f"当前模型: {current_model}")

        self._initialize_novel_data_structure()

        self._initialize_managers()
        self._setup_event_handlers()

        # 设置中断信号处理
        signal.signal(signal.SIGINT, self.signal_handler)

        self.fallback_openings = {
        "男频衍生": "【🧠脑子寄存处】存脑子的扣1，不存的扣眼珠子！阅读前请将三观暂存～\n\n📢 看到离谱处先别骂，评论区肯定有课代表帮你吐槽！",
        "默认": "【🎮游戏开始】阅读前请调整好姿势，准备好零食！\n\n🎯 猜中剧情的评论区封神，猜不中的…那就多猜几次！"
        }

    def _initialize_cover_generator(self):
        """初始化封面生成器"""
        try:
            doubao_api_key = doubaoconfig.ARK_API_KEY
            if doubao_api_key:
                self.cover_generator = DouBaoImageGenerator()
                print("✅ 封面生成器初始化成功")
            else:
                print("⚠️ 未配置豆包API密钥，封面生成功能不可用")
        except Exception as e:
            print(f"⚠️ 封面生成器初始化失败: {e}")
            self.cover_generator = None

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
             # 特别检查写作风格指南
            if "writing_style_guide" in data and data["writing_style_guide"]:
                print(f"  - writing_style_guide: 已加载，包含 {len(data['writing_style_guide'])} 个字段")
            else:
                print(f"  - writing_style_guide: 项目数据中缺失，尝试从单独文件加载...")
                # 尝试从单独文件加载
                writing_style = self._load_writing_style_from_file()
                if writing_style:
                    data["writing_style_guide"] = writing_style
                    self.novel_data["writing_style_guide"] = writing_style
                    print(f"  ✅ 从单独文件成功加载写作风格指南")
                else:
                    print(f"  ⚠️ 无法从文件加载写作风格指南，将在需要时重新生成")
            # 修复进度信息
            self.current_progress = self.novel_data.get("current_progress", {
                "completed_chapters": 0,
                "total_chapters": 0,
                "stage": "大纲阶段",
                "current_stage": "第一阶段"
            })

            if "writing_style_guide" in self.novel_data and self.novel_data["writing_style_guide"]:
                print(f"  ✅ 写作风格指南已恢复")
            else:
                print(f"  ⚠️ 项目中没有写作风格指南，将在需要时重新生成")
                
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
        """继续生成小说 - 修复版本：基于实际文件检查并补写缺失章节"""
        print("   继续生成小说...")
        
        # 🆕 首先进行实际文件检查，找出真正缺失的章节
        print("\n📋 第一步：检查章节完整性...")
        self.check_and_fill_missing_chapters()
        
        # 🆕 基于实际文件数量重新校准进度
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        chapters_dir = f"小说项目/{safe_title}_章节"
        
        actual_files_count = 0
        if os.path.exists(chapters_dir):
            chapter_files = [f for f in os.listdir(chapters_dir) if f.endswith('.txt')]
            actual_files_count = len(chapter_files)
            
            # 更新进度信息为实际文件数量
            if actual_files_count != self.novel_data["current_progress"]["completed_chapters"]:
                print(f"🔄 根据实际文件校准进度: {self.novel_data['current_progress']['completed_chapters']} -> {actual_files_count}章")
                self.novel_data["current_progress"]["completed_chapters"] = actual_files_count
        
        # 如果用户提供了新的总章节数且比当前大，则更新
        if total_chapters and total_chapters > self.novel_data["current_progress"]["total_chapters"]:
            print(f"更新总章节数: {self.novel_data['current_progress']['total_chapters']} -> {total_chapters}")
            self.novel_data["current_progress"]["total_chapters"] = total_chapters
        
        # 确定从哪一章开始继续
        start_chapter = self.novel_data["current_progress"]["completed_chapters"] + 1
        end_chapter_total = self.novel_data["current_progress"]["total_chapters"]
        # 检查是否需要生成新章节
        if start_chapter > end_chapter_total:
            print("✅ 所有章节已完成，无需继续生成。")
        else:
            print(f"  从第{start_chapter}章开始继续生成...")
            
            # 直接开始生成章节内容
            chapters_per_batch = min(3, self.config["defaults"]["chapters_per_batch"])
            
            for batch_start in range(start_chapter, end_chapter_total + 1, chapters_per_batch):
                batch_end = min(batch_start + chapters_per_batch - 1, end_chapter_total)
                self.novel_data["current_progress"]["current_batch"] += 1
                
                print(f"\n批次{self.novel_data['current_progress']['current_batch']}: 第{batch_start}-{batch_end}章")
                
                if not self.generate_chapters_batch(batch_start, batch_end):
                    print(f"批次{self.novel_data['current_progress']['current_batch']}生成失败")
                    continue_gen = input("是否继续生成后续章节？(y/n): ").lower()
                    if continue_gen != 'y':
                        break
                
                # 批次间延迟
                batch_delay = 10 if end_chapter_total > 100 else 5
                if batch_end < end_chapter_total:
                    print(f"等待{batch_delay}秒后继续下一批次...")
                    time.sleep(batch_delay)

        # 无论是否生成了新章节，都执行最终的收尾流程（包括保存、导出和生成封面）
        print("\n▶️ 所有章节内容已就绪，进入最终收尾流程...")
        return self._finalize_generation()
        
    def full_auto_generation(self, creative_seed: str, total_chapters: int = None):
        """全自动生成完整小说 - 修改为生成多本小说"""
        print("🚀 开始全自动小说生成...")
        print(f"创意种子: {creative_seed}")
        
        if total_chapters is None:
            total_chapters = self.config["defaults"]["total_chapters"]
        
        # 🆕 不再手动选择分类，等待从生成的方案中获取
        print(f"  📝 等待从生成的方案中自动获取分类信息...")
       # 【核心改动 1】: 从原始JSON中提取创意，并调用指令精炼器
        # 使用一个临时占位符标题来生成指令文件
        temp_title_for_filename = f"未定稿创意_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if isinstance(creative_seed, str):
            try:
                # 尝试解析JSON字符串
                creative_work_dict = json.loads(creative_seed)
            except:
                # 如果解析失败，创建一个基础字典结构
                creative_work_dict = {
                    "coreSetting": creative_seed,
                    "coreSellingPoints": "",
                    "completeStoryline": {}
                }
        else:
            creative_work_dict = creative_seed

        refined_creative_seed = self.refine_creative_work_for_ai(creative_work_dict, temp_title_for_filename)

        # -------------------------------------------------------------        
        # 生成多个方案
        print("=== 步骤1: 基于创意种子生成多个小说方案 ===")
        plans_data = self.content_generator.generate_multiple_plans(refined_creative_seed, "")
        
        if not plans_data or 'plans' not in plans_data:
            print("❌ 方案生成失败")
            return False
        
        plans = plans_data['plans']
        print(f"✅ 成功生成 {len(plans)} 个方案")
        
        # 对每个方案进行质量评价和新鲜度评价
        qualified_plans = []
        for i, plan in enumerate(plans):
            print(f"  🔍 评估方案 {i+1}...")
            
            # 🆕 从方案中获取分类信息
            category_from_plan = plan.get('tags', {}).get('main_category', '未分类')
            
            # ===================== [新增] 分类修正逻辑 =====================
            # 检查标题、简介、关键词和创意种子中是否包含"同人"
            title = plan.get('title', '')
            synopsis = plan.get('synopsis', '')
            keywords = plan.get('tags', {}).get('keywords', [])
            keywords_str = "".join(keywords)

            # 🆕 新增：检查创意种子内容
            creative_core_setting = creative_seed.get('coreSetting', '') if isinstance(creative_seed, dict) else str(creative_seed)
            creative_selling_points = creative_seed.get('coreSellingPoints', '') if isinstance(creative_seed, dict) else ""

            # 合并所有文本进行检查
            combined_text = f"{title} {synopsis} {keywords_str} {creative_core_setting} {creative_selling_points}"

            has_tongren = "同人" in combined_text
            has_dongman = any(keyword in combined_text for keyword in ["动漫", "动画", "漫画"])

            if has_tongren:
                if has_dongman:
                    category_from_plan = "动漫衍生"
                    reason = "同人+动漫"
                else:
                    category_from_plan = "男频衍生" 
                    reason = "同人"
                
                print(f"    🔄 分类修正: 检测到'{reason}'关键字，分类已修正为 '{category_from_plan}'")
                
                if 'tags' not in plan:
                    plan['tags'] = {}
                plan['tags']['main_category'] = category_from_plan
                print(f"    📝 同步更新方案内部分类字段")
            print(f"    📊 方案分类: {category_from_plan}")
            
            evaluation_result = self._evaluate_plan_quality(plan, category_from_plan, creative_seed)
            
            quality_score = evaluation_result.get("quality_score", 0)
            freshness_score = evaluation_result.get("freshness_score", 0)
            total_score = evaluation_result.get("total_score", 0)
            
            # 降低门槛，让更多方案通过
            if quality_score >= 8.5 and freshness_score >= 2.0:
                qualified_plans.append({
                    'plan': plan,
                    'quality_score': quality_score,
                    'freshness_score': freshness_score,
                    'total_score': total_score,
                    'evaluation_result': evaluation_result,
                    'category': category_from_plan  # 🆕 保存分类信息
                })
                print(f"    ✅ 方案 {i+1} 通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
            else:
                print(f"    ❌ 方案 {i+1} 未通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
        
        if not qualified_plans:
            print("❌ 没有合格的方案，终止生成")
            return False
        
        print(f"🎯 共有 {len(qualified_plans)} 个方案通过评估，将分别生成小说")
        
        # 为每个合格的方案生成小说
        success_count = 0
        for i, qualified_plan in enumerate(qualified_plans):
            plan = qualified_plan['plan']
            plan_category = qualified_plan['category']  # 🆕 使用方案中的分类
            
            print(f"\n{'='*60}")
            print(f"📚 开始生成第 {i+1} 本小说: 《{plan['title']}》")
            print(f"📊 分类: {plan_category}")
            print(f"{'='*60}")
            
            try:
                self.novel_data = {}
                # 重置 novel_data 结构，为每本小说创建独立的数据
                self._initialize_novel_data_structure()
                # 🆕 设置分类（使用方案中的分类）
                self.novel_data["category"] = plan_category
                # 设置当前方案
                self.novel_data["selected_plan"] = plan
                self.novel_data["novel_title"] = plan["title"]
                self.novel_data["novel_synopsis"] = plan["synopsis"]
                self.novel_data["creative_seed"] = creative_seed
                self.novel_data["current_progress"]["total_chapters"] = total_chapters
                self.novel_data["current_progress"]["start_time"] = datetime.now().isoformat()
                self.novel_data["current_progress"]["stage"] = "开始"
                self.novel_data["current_progress"]["completed_chapters"] = 0
                self.novel_data["current_progress"]["current_batch"] = 0
                
                # 存储评分信息
                self.novel_data["plan_scores"] = {
                    "quality_score": qualified_plan['quality_score'],
                    "freshness_score": qualified_plan['freshness_score'],
                    "total_score": qualified_plan['total_score']
                }
                
                # 为每本小说生成独特的项目标识
                original_title = self.novel_data["novel_title"]
                self.novel_data["novel_title"] = f"{original_title}"
                
                print(f"📖 小说标题: {self.novel_data['novel_title']}")
                print(f"📊 方案评分 - 质量: {qualified_plan['quality_score']:.1f}, 新鲜度: {qualified_plan['freshness_score']:.1f}")
                print(f"📚 小说分类: {plan_category}")
                # 【核心改动 3】: 在确定小说标题后，重命名指令文件
                # -------------------------------------------------------------
                safe_new_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
                old_filepath = os.path.join("小说项目", f"{temp_title_for_filename}_Refined_AI_Brief.txt")
                new_filepath = os.path.join("小说项目", f"{safe_new_title}_Refined_AI_Brief.txt")
                if os.path.exists(old_filepath):
                    try:
                        os.rename(old_filepath, new_filepath)
                        print(f"🔄 AI指令文件名已更新为: {os.path.basename(new_filepath)}")
                        # 更新临时文件名，以防下一本小说生成时出错
                        temp_title_for_filename = f"未定稿创意_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i+1}"
                    except Exception as rename_error:
                        print(f"⚠️ 重命名指令文件失败: {rename_error}")
                # -------------------------------------------------------------
                # 执行单个小说的生成流程
                if self._generate_single_novel(creative_seed, total_chapters):
                    success_count += 1
                    print(f"✅ 第 {i+1} 本小说生成完成: 《{original_title}》")
                else:
                    print(f"❌ 第 {i+1} 本小说生成失败: 《{original_title}》")
                    
            except Exception as e:
                print(f"❌ 生成第 {i+1} 本小说时出错: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"\n{'='*60}")
        print(f"🎉 多本小说生成完成统计")
        print(f"{'='*60}")
        print(f"📚 总方案数: {len(plans)}")
        print(f"✅ 合格方案: {len(qualified_plans)}")
        print(f"🎊 成功生成: {success_count} 本")
        print(f"📊 成功率: {success_count/len(qualified_plans)*100:.1f}%")
        
        return success_count > 0

    def _generate_element_timing_plan(self) -> bool:
        """生成元素登场时机规划"""
        print("=== 步骤7.5: 制定元素登场时机规划 ===")
        
        try:
            # 确保有全局成长计划
            if not self.novel_data.get("global_growth_plan"):
                print("  ⚠️ 没有全局成长计划，无法生成元素时机规划")
                return False
            
            # 确保有全局写作计划
            if not self.novel_data.get("overall_stage_plans"):
                print("  ⚠️ 没有全局写作计划成长计划，无法生成元素时机规划")
                return False            
            
            timing_plan = self.element_timing_planner.generate_element_timing_plan(
                self.novel_data["global_growth_plan"],
                self.novel_data.get("overall_stage_plans")
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

    def refine_creative_work_for_ai(self, creative_work: dict, novel_title: str) -> str:
        """
        【指令精炼层 - 核心方法】
        将用户提供的原始创意JSON，转换为对AI具有高度约束力的、结构化的文本指令。
        并将精炼后的指令保存到文本文件中。

        Args:
            creative_work (dict): 用户输入的原始创意JSON对象。
            novel_title (str): 小说标题，用于生成文件名。

        Returns:
            str: 精炼后的、可直接用作AI Prompt的文本指令。
        """
        print("⚙️  正在执行【指令精炼】，将人类创意转换为AI必须遵守的硬性指令...")

        # 1. 提取核心组件
        core_setting = creative_work.get("coreSetting", "未提供核心设定。")
        core_selling_points = creative_work.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_work.get("completeStoryline", {})
        
        # 2. 构建AI精炼提示词
        refinement_prompt = f"""
    请将以下小说创意转换为对AI具有高度约束力的、结构化的创作指令：

    【原始创意】
    核心设定：{core_setting}
    核心卖点：{core_selling_points}
    故事线：{storyline}

    【转换要求】
    1. 将创意转换为严格的AI创作指令，包含世界观边界、绝对禁止事项、阶段性目标
    2. 强调时间线和地理范围的限制
    3. 明确角色行为的约束条件
    4. 突出核心卖点的实现路径
    5. 用命令式的语言，确保AI必须遵守
    6. 结构清晰，分为世界观边界、核心卖点执行纲领、分阶段框架等部分

    请生成一个完整的、可直接用作AI Prompt的严格指令：
    """
        
        try:
            # 3. 调用AI进行真正的精炼
            print("  🤖 调用AI进行创意精炼...")
            refined_instruction = self.api_client.call_api(
                "refine_creative_work_for_ai",
                refinement_prompt,
                0.7,  # 适度创造性
                purpose="创意精炼为AI指令"
            )
            
            if not refined_instruction:
                print("  ⚠️ AI精炼失败，使用基础模板")
                refined_instruction = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
            
            # 4. 保存到文件
            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                output_dir = "小说项目"
                os.makedirs(output_dir, exist_ok=True)
                output_filepath = os.path.join(output_dir, f"{safe_title}_Refined_AI_Brief.txt")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(refined_instruction)
                print(f"✅  指令精炼完成，已保存至: {output_filepath}")
            except Exception as e:
                print(f"⚠️  保存精炼指令文件失败: {e}")
                
            return refined_instruction
            
        except Exception as e:
            print(f"❌ AI精炼过程出错: {e}，使用基础模板")
            # 降级到基础模板
            return self._build_basic_instruction_template(core_setting, core_selling_points, storyline)

    def _build_basic_instruction_template(self, core_setting: str, core_selling_points: str, storyline: dict) -> str:
        """构建基础指令模板（降级方案）"""
        print("  🛠️ 使用基础指令模板...")
        
        instructions = []
        instructions.append("# AI创作最高指令：创作大纲与绝对约束")
        instructions.append("你是一位顶级的小说策划AI。以下内容是你本次创作的【唯一真相来源】和【绝对行为准则】。你必须严格、完整、精确地遵循所有指令，任何偏离或遗漏都将被视为任务失败。")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第一部分：世界观与不可逾越的边界")
        instructions.append(f"\n**核心设定：**\n{core_setting}")
        
        # 自动生成否定约束
        negative_constraints = []
        if "凡人" in core_setting and "落云宗" in core_setting:
            negative_constraints.append("**绝对禁止**：故事时间线在韩立从乱星海回归之后，因此**严禁**让主角前往乱星海、参与虚天殿夺宝等已发生的剧情。主角在结婴前的活动范围**必须**锁定在天南大陆。")
        else:
            negative_constraints.append("**绝对禁止**：你的一切情节设计都不能超出上述【核心设定】所定义的范围。不要引入设定之外的时间段、地点或世界背景。")
        
        instructions.append("\n**绝对禁止事项：**")
        instructions.extend([f"- {constraint}" for constraint in negative_constraints])
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第二部分：核心卖点与执行纲领")
        instructions.append("你的所有情节设计，都必须以服务和凸显以下核心卖点为首要目标：")
        instructions.append(f"\n{core_selling_points}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第三部分：分阶段故事线框架")
        instructions.append("你必须严格按照以下阶段的设定来构建故事的起承转合。")
        
        if storyline:
            for stage_key, stage_data in storyline.items():
                stage_name = stage_data.get('stageName', '未知阶段')
                summary = stage_data.get('summary', '无')
                arc_goal = stage_data.get('arc_goal', '无')
                
                instructions.append(f"\n### {stage_name}")
                instructions.append(f"- **情节概要：** {summary}")
                instructions.append(f"- **强制目标：** {arc_goal}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 最终指令确认")
        instructions.append("以上所有内容是不可违背的创作铁律。现在，请基于这份【最高指令】，开始你的工作。")
        
        return "\n".join(instructions)

    def _generate_writing_style_guide(self, creative_seed: str, category: str) -> bool:
        """生成写作风格指南"""
        print("=== 步骤1.5: 生成写作风格指南 ===")
        
        try:
            # 使用内容生成器生成写作风格
            writing_style = self.content_generator.generate_writing_style_guide(
                creative_seed, 
                category,
                self.novel_data["selected_plan"],
                self.novel_data["market_analysis"]
            )
            
            if writing_style:
                self.novel_data["writing_style_guide"] = writing_style
                print("✅ 写作风格指南生成完成")
                
                # 保存风格指南到单独文件供参考
                self._save_writing_style_to_file(writing_style)
                return True
            else:
                print("⚠️ 写作风格指南生成失败，使用默认风格")
                self.novel_data["writing_style_guide"] = self._get_default_writing_style(category)
                return True
                
        except Exception as e:
            print(f"⚠️ 生成写作风格指南时出错: {e}")
            self.novel_data["writing_style_guide"] = self._get_default_writing_style(category)
            return True

    def _save_writing_style_to_file(self, writing_style: Dict):
        """保存写作风格指南到JSON文件"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])

            # 确保小说项目目录存在
            project_dir = "小说项目"
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
                print(f"📁 创建目录: {project_dir}")

            # 保存为JSON文件
            style_file = f"小说项目/{safe_title}_写作风格指南.json"
            
            # 构建完整的写作风格数据
            style_data = {
                "novel_title": self.novel_data["novel_title"],
                "category": self.novel_data.get("category", "未分类"),
                "creative_seed": self.novel_data.get("creative_seed", ""),
                "created_time": datetime.now().isoformat(),
                "writing_style_guide": writing_style
            }
            
            with open(style_file, 'w', encoding='utf-8') as f:
                json.dump(style_data, f, ensure_ascii=False, indent=2)
            
            print(f"📝 写作风格指南已保存到: {style_file}")
            
        except Exception as e:
            print(f"⚠️ 保存写作风格指南失败: {e}")
            import traceback
            traceback.print_exc()

    def _load_writing_style_from_file(self, novel_title: str = None) -> Optional[Dict]:
        """从JSON文件加载写作风格指南 - 修复版本"""
        try:
            # 使用传入的小说标题，如果没有则尝试从novel_data获取
            if novel_title is None:
                if hasattr(self, 'novel_data') and self.novel_data and "novel_title" in self.novel_data:
                    novel_title = self.novel_data["novel_title"]
                else:
                    print(f"  ❌ 无法获取小说标题，跳过加载写作风格指南")
                    return None
            
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            style_file = f"小说项目/{safe_title}_写作风格指南.json"
            
            if not os.path.exists(style_file):
                print(f"  ⚠️ 写作风格指南文件不存在: {style_file}")
                return None
            
            with open(style_file, 'r', encoding='utf-8') as f:
                file_content = json.load(f)
            
            print(f"  ✅ 从文件加载写作风格指南: {style_file}")
            
            # 检查文件结构 - 如果是直接包含写作风格指南的字典
            if isinstance(file_content, dict) and "core_style" in file_content:
                print(f"  ✅ 检测到直接格式的写作风格指南")
                return file_content
            # 如果是包含在 writing_style_guide 字段中的格式
            elif isinstance(file_content, dict) and "writing_style_guide" in file_content:
                print(f"  ✅ 检测到嵌套格式的写作风格指南")
                return file_content["writing_style_guide"]
            else:
                print(f"  ⚠️ 未知的写作风格指南格式: {list(file_content.keys()) if isinstance(file_content, dict) else type(file_content)}")
                return file_content
            
        except Exception as e:
            print(f"  ❌ 加载写作风格指南失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _get_default_writing_style(self, category: str) -> Dict:
        """根据分类获取默认的写作风格"""
        default_styles = {
            "西方奇幻": {
                "core_style": "史诗感与细节描写并重，强调世界观的沉浸感",
                "language_features": ["华丽而克制的修辞", "适度的古风词汇", "场景描写细腻", "气势恢宏的叙述"],
                "narrative_pace": "开篇快速引入冲突，中期稳步展开世界观，后期高潮迭起",
                "dialogue_style": "对话兼具古典韵味和现代可读性，角色语言符合身份地位",
                "description_focus": ["魔法系统细节", "种族文化特征", "地理环境描写", "战斗场面刻画"],
                "emotional_tone": "庄严中带有温情，冲突中展现人性光辉",
                "chapter_structure": "每章以悬念结尾，保持读者追读欲望",
                "important_notes": ["保持世界观一致性", "注意力量体系平衡", "强化种族特色描写"]
            },
            "东方仙侠": {
                "core_style": "飘逸洒脱与杀伐果断并存，传统仙侠韵味",
                "language_features": ["简洁有力的短句", "适当的成语运用", "意境描写突出", "文言与现代结合"],
                "narrative_pace": "前期稳扎稳打铺垫，中期快速升级，后期格局宏大",
                "dialogue_style": "文白夹杂，既有古风又保证易懂，体现修真者气质",
                "description_focus": ["修炼体系", "法宝神通", "宗门势力", "心境突破"],
                "emotional_tone": "热血中带有沧桑，成长中体现道心",
                "chapter_structure": "黄金三章定律，每章都有小高潮",
                "important_notes": ["注意修为境界逻辑", "保持修真世界观严谨", "强化道心刻画"]
            },
            "科幻末世": {
                "core_style": "硬核设定与人性探讨结合，紧张刺激",
                "language_features": ["简洁明快的叙述", "技术术语适度", "环境压抑感营造", "短句增强节奏"],
                "narrative_pace": "开篇即高潮，持续保持紧张感，节奏紧凑",
                "dialogue_style": "对话简洁有力，体现末世生存哲学",
                "description_focus": ["科技设备细节", "生存环境描写", "人性挣扎刻画", "战斗求生场景"],
                "emotional_tone": "绝望中寻找希望，黑暗中闪现人性光辉",
                "chapter_structure": "短小精悍，节奏紧凑，悬念密集",
                "important_notes": ["保持科技设定合理", "强化生存紧张感", "注意人性深度挖掘"]
            },
            "男频衍生": {
                "core_style": "爽快直接，节奏明快，满足读者期待",
                "language_features": ["口语化表达", "情绪渲染强烈", "画面感强", "节奏感突出"],
                "narrative_pace": "快速推进，高潮迭起，爽点密集",
                "dialogue_style": "直接有力，体现男性角色特点",
                "description_focus": ["实力提升", "势力扩张", "战斗场面", "人际关系"],
                "emotional_tone": "热血激昂，成就感和征服欲强烈",
                "chapter_structure": "每章必有爽点，结尾留有期待",
                "important_notes": ["保持爽点密度", "注意节奏控制", "强化主角光环"]
            },
            "都市高武": {
                "core_style": "现代都市与武道修炼结合，现实与幻想交融",
                "language_features": ["现代口语为主", "适当专业术语", "生活化描写", "战斗场面激烈"],
                "narrative_pace": "前期都市生活铺垫，中期武道崛起，后期都市称霸",
                "dialogue_style": "现代对话风格，兼具武道修行者气质",
                "description_focus": ["都市环境", "武道修炼", "社会关系", "势力斗争"],
                "emotional_tone": "现实压力与武道追求的矛盾与突破",
                "chapter_structure": "生活与修炼交替，张弛有度",
                "important_notes": ["平衡都市与武道", "注意现实逻辑", "强化实力提升感"]
            },
            "悬疑灵异": {
                "core_style": "氛围营造优先，悬念层层递进",
                "language_features": ["细腻的环境描写", "心理活动丰富", "悬念设置巧妙", "氛围渲染强烈"],
                "narrative_pace": "缓慢铺垫，逐步紧张，爆发突然",
                "dialogue_style": "对话简洁神秘，留有想象空间",
                "description_focus": ["环境氛围", "心理变化", "线索细节", "恐怖元素"],
                "emotional_tone": "紧张恐惧中带有解密快感",
                "chapter_structure": "每章都有新线索，结尾必留悬念",
                "important_notes": ["保持逻辑严谨", "注意恐怖程度控制", "强化推理过程"]
            },
            "悬疑脑洞": {
                "core_style": "创意新奇，反转不断，逻辑严密",
                "language_features": ["简洁明快", "反转措辞巧妙", "逻辑表述清晰", "创意表达生动"],
                "narrative_pace": "快速引入设定，持续反转，节奏紧凑",
                "dialogue_style": "对话机智巧妙，体现角色智慧",
                "description_focus": ["创意设定", "逻辑推理", "反转铺垫", "细节暗示"],
                "emotional_tone": "惊奇与解惑并存，智力挑战的愉悦",
                "chapter_structure": "层层递进，反转不断，结尾惊人",
                "important_notes": ["保持逻辑自洽", "注意创意合理性", "强化反转效果"]
            },
            "抗战谍战": {
                "core_style": "历史厚重感与紧张悬念结合",
                "language_features": ["朴实有力", "时代感词汇", "紧张氛围描写", "历史细节准确"],
                "narrative_pace": "稳步推进，紧张时刻爆发，历史感厚重",
                "dialogue_style": "符合时代特征，体现人物身份",
                "description_focus": ["历史环境", "谍战细节", "人物心理", "时代氛围"],
                "emotional_tone": "紧张危险中体现家国情怀",
                "chapter_structure": "悬念与解密交替，历史事件穿插",
                "important_notes": ["尊重历史事实", "注意细节真实", "强化爱国情怀"]
            },
            "历史古代": {
                "core_style": "历史厚重感与文化底蕴并重",
                "language_features": ["文白相间", "历史典故运用", "典雅庄重", "细节考究"],
                "narrative_pace": "沉稳推进，重大事件爆发，历史脉络清晰",
                "dialogue_style": "符合古代语言习惯，体现人物身份",
                "description_focus": ["历史环境", "典章制度", "人物风貌", "文化细节"],
                "emotional_tone": "历史沧桑与人物命运的厚重感",
                "chapter_structure": "按历史事件推进，章节间联系紧密",
                "important_notes": ["考据历史细节", "保持语言风格", "强化时代特色"]
            },
            "历史脑洞": {
                "core_style": "历史基础与创意想象结合",
                "language_features": ["古今结合", "幽默诙谐", "创意表达", "历史梗运用"],
                "narrative_pace": "快速引入创意，稳步展开，爽点密集",
                "dialogue_style": "现代思维与古代语境结合",
                "description_focus": ["创意设定", "历史改变", "人物互动", "时代碰撞"],
                "emotional_tone": "轻松幽默中带有历史思考",
                "chapter_structure": "创意与历史交替，反转有趣",
                "important_notes": ["平衡历史与创意", "注意逻辑自洽", "强化趣味性"]
            },
            "都市种田": {
                "core_style": "温馨细腻，生活气息浓厚",
                "language_features": ["平实亲切", "生活化表达", "细节描写", "情感细腻"],
                "narrative_pace": "舒缓平稳，日常生活为主，小高潮点缀",
                "dialogue_style": "生活化对话，亲切自然",
                "description_focus": ["日常生活", "人际关系", "情感变化", "小确幸"],
                "emotional_tone": "温馨治愈，平凡中的幸福",
                "chapter_structure": "生活片段串联，情感递进",
                "important_notes": ["保持生活真实感", "注意情感细腻度", "强化温馨氛围"]
            },
            "都市脑洞": {
                "core_style": "现实基础与奇妙创意碰撞",
                "language_features": ["现代口语", "创意表达", "幽默风趣", "节奏明快"],
                "narrative_pace": "快速引入设定，创意不断，节奏轻快",
                "dialogue_style": "现代幽默，机智对白",
                "description_focus": ["创意设定", "现实反差", "人物反应", "社会现象"],
                "emotional_tone": "轻松有趣，惊奇不断",
                "chapter_structure": "创意展示为主，结尾留有期待",
                "important_notes": ["保持创意新鲜度", "注意现实逻辑", "强化喜剧效果"]
            },
            "都市日常": {
                "core_style": "真实细腻，情感丰富",
                "language_features": ["平实自然", "情感细腻", "生活细节", "心理描写"],
                "narrative_pace": "舒缓平稳，情感推进为主",
                "dialogue_style": "真实自然，体现人物性格",
                "description_focus": ["日常生活", "情感变化", "人际关系", "心理活动"],
                "emotional_tone": "温暖真实，情感共鸣",
                "chapter_structure": "情感发展为主线，生活细节填充",
                "important_notes": ["保持生活真实感", "强化情感描写", "注意节奏舒缓"]
            },
            "玄幻脑洞": {
                "core_style": "传统玄幻与创新设定结合",
                "language_features": ["气势恢宏", "创意表达", "节奏明快", "画面感强"],
                "narrative_pace": "快速引入创意，稳步展开世界观，高潮迭起",
                "dialogue_style": "兼具古风与现代感",
                "description_focus": ["创新设定", "修炼体系", "世界观展开", "战斗场面"],
                "emotional_tone": "热血激昂，创意惊喜",
                "chapter_structure": "创意展示与情节推进并重",
                "important_notes": ["平衡传统与创新", "注意设定逻辑", "强化创意亮点"]
            },
            "战神赘婿": {
                "core_style": "打脸爽快，逆袭感强烈",
                "language_features": ["情绪强烈", "对比鲜明", "节奏快速", "爽点密集"],
                "narrative_pace": "压抑铺垫，快速爆发，持续打脸",
                "dialogue_style": "霸气有力，体现身份转变",
                "description_focus": ["身份反差", "实力展示", "打脸场面", "情感转变"],
                "emotional_tone": "压抑后的爆发，逆袭的快感",
                "chapter_structure": "每章都有小高潮，持续爽点",
                "important_notes": ["强化反差效果", "注意节奏控制", "保持爽感持续"]
            },
            "动漫衍生": {
                "core_style": "二次元特色明显，画面感强",
                "language_features": ["生动形象", "中二感适度", "画面描写", "节奏明快"],
                "narrative_pace": "快速推进，战斗密集，情感丰富",
                "dialogue_style": "符合二次元特色，热血或萌系",
                "description_focus": ["战斗场面", "角色特色", "世界观展开", "情感羁绊"],
                "emotional_tone": "热血激情或温馨治愈",
                "chapter_structure": "章节分明，战斗与日常交替",
                "important_notes": ["保持原作特色", "注意角色还原", "强化画面感"]
            },
            "游戏体育": {
                "core_style": "专业性与爽快感结合",
                "language_features": ["专业术语适度", "节奏感强", "数据清晰", "场面激烈"],
                "narrative_pace": "训练铺垫，比赛爆发，成绩提升",
                "dialogue_style": "专业与激情结合",
                "description_focus": ["技术细节", "比赛场面", "训练过程", "团队配合"],
                "emotional_tone": "拼搏激情，成就荣耀",
                "chapter_structure": "训练与比赛交替，成绩递进",
                "important_notes": ["保持专业准确", "强化比赛紧张感", "注意成长逻辑"]
            },
            "传统玄幻": {
                "core_style": "古典韵味，体系严谨",
                "language_features": ["典雅庄重", "体系描述清晰", "气势恢宏", "意境深远"],
                "narrative_pace": "稳步铺垫，体系展开，高潮宏伟",
                "dialogue_style": "古风韵味，符合修真者气质",
                "description_focus": ["修炼体系", "世界观架构", "宗门势力", "大道感悟"],
                "emotional_tone": "修真求道的执着与超脱",
                "chapter_structure": "按修炼阶段推进，境界突破为重",
                "important_notes": ["保持体系严谨", "注意境界逻辑", "强化道心描写"]
            },
            "都市修真": {
                "core_style": "现代都市与修真体系融合",
                "language_features": ["现代与古典结合", "专业术语适度", "生活化描写", "修炼细节"],
                "narrative_pace": "都市生活与修真交替，稳步提升",
                "dialogue_style": "现代语境，修真者思维",
                "description_focus": ["都市环境", "修炼过程", "实力提升", "社会互动"],
                "emotional_tone": "现实压力与修真超脱的矛盾",
                "chapter_structure": "生活与修炼平衡，实力逐步展现",
                "important_notes": ["平衡两个世界", "注意逻辑合理", "强化实力反差"]
            }
        }
        
        return default_styles.get(category, {
            "core_style": "语言流畅自然，情节推进合理",
            "language_features": ["表达清晰", "描写生动", "节奏适中"],
            "narrative_pace": "稳步推进，高潮适当",
            "dialogue_style": "符合人物身份，自然流畅",
            "description_focus": ["情节推进", "人物刻画", "环境描写"],
            "emotional_tone": "情感真实，有感染力",
            "chapter_structure": "章节完整，衔接自然",
            "important_notes": ["保持风格一致性", "注意情节逻辑", "强化读者代入感"]
        })

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
        print("=== 步骤6: 生成全书阶段计划 ===")
        
        self.novel_data["overall_stage_plans"] = self.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data.get("market_analysis", {}),
            self.novel_data.get("global_growth_plan", {}),
            total_chapters
        )
        
        if self.novel_data["overall_stage_plans"]:
            print("✅ 全书阶段计划生成成功")
            return True
        else:
            return False

    def _generate_global_growth_plan(self) -> bool:
        """生成全局成长规划 - 精简分层版本"""
        print("=== 步骤5: 制定全书成长规划框架 ===")
        
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
            batch_delay = 2 if total_chapters > 100 else 2
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
        # ===================== [新增] 生成小说封面 =====================
        print("\n" + "="*60)
        print("🎨 最后一步：生成小说封面")
        print("="*60)
        self.novel_data["current_progress"]["stage"] = "封面生成"
        if not self._generate_novel_cover():
            print("⚠️ 封面生成失败，项目已完成但无封面。")
        # ===================== 【【【核心修改点】】】 =====================
        # 在此处添加文件复制逻辑
        print("\n" + "="*60)
        print("🚚 正在复制项目文件到执行目录...")
        print("="*60)
        
        target_dir = r"C:\work1.0\Chrome\小说项目"  # 从main.py移过来的硬编码路径
        novel_title = self.novel_data.get("novel_title")
        
        if novel_title:
            copy_success = self.project_manager.copy_project_to_directory(novel_title, target_dir)
            if not copy_success:
                print(f"⚠️ 项目《{novel_title}》文件复制失败。")
        else:
            print("❌ 无法复制项目文件，因为小说标题未知。")
        # =============================================================
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
            
            # 初始化所有上下文变量
            event_context = {}
            foreshadowing_context = {}
            growth_context = {}
            stage_plan = {}
            
            # 获取各个管理器的上下文
            print(f"  📊 获取事件上下文...")
            if hasattr(self, 'event_driven_manager') and hasattr(self.event_driven_manager, 'get_context'):
                try:
                    event_context = self.event_driven_manager.get_context(chapter_num)
                    print(f"    ✅ 事件上下文获取成功")
                    print(f"    📊 事件上下文内容:")
                    print(f"      - 活跃事件: {len(event_context.get('active_events', []))}个")
                    print(f"      - 即将发生事件: {len(event_context.get('upcoming_events', []))}个")
                    print(f"      - 焦点事件: {event_context.get('focused_event', '无')}")
                    
                    # 打印具体的事件信息
                    for i, event in enumerate(event_context.get('active_events', [])[:3]):
                        if isinstance(event, dict):
                            print(f"        🎯 活跃{i+1}: {event.get('name', '未知事件')}")
                        else:
                            print(f"        🎯 活跃{i+1}: {str(event)[:50]}...")
                            
                except Exception as e:
                    print(f"    ⚠️ 获取事件上下文失败: {e}")
                    import traceback
                    traceback.print_exc()
                    event_context = {}
            else:
                print(f"    ⚠️ 事件驱动管理器不可用或缺少get_context方法")
            
            print(f"  🎭 获取伏笔上下文...")
            if hasattr(self, 'foreshadowing_manager') and hasattr(self.foreshadowing_manager, 'get_context'):
                try:
                    foreshadowing_context = self.foreshadowing_manager.get_context(chapter_num)
                    print(f"    ✅ 伏笔上下文获取成功")
                    print(f"    📊 伏笔上下文内容:")
                    print(f"      - 引入元素: {len(foreshadowing_context.get('elements_to_introduce', []))}")
                    print(f"      - 发展元素: {len(foreshadowing_context.get('elements_to_develop', []))}")
                    print(f"      - 焦点: {foreshadowing_context.get('foreshadowing_focus', '无')}")
                    print(f"      - 总元素数: {foreshadowing_context.get('total_elements_count', 0)}")
                    
                    # 打印具体的元素信息
                    intro_elements = foreshadowing_context.get('elements_to_introduce', [])
                    for i, elem in enumerate(intro_elements[:3]):
                        if isinstance(elem, dict):
                            print(f"        🆕 引入{i+1}: {elem.get('name', '未知')} (类型: {elem.get('type', '未知')})")
                        else:
                            print(f"        🆕 引入{i+1}: {str(elem)[:30]}...")
                    
                    develop_elements = foreshadowing_context.get('elements_to_develop', [])
                    for i, elem in enumerate(develop_elements[:3]):
                        if isinstance(elem, dict):
                            print(f"        📈 发展{i+1}: {elem.get('name', '未知')} (类型: {elem.get('type', '未知')})")
                        else:
                            print(f"        📈 发展{i+1}: {str(elem)[:30]}...")
                            
                except Exception as e:
                    print(f"    ⚠️ 获取伏笔上下文失败: {e}")
                    import traceback
                    traceback.print_exc()
                    foreshadowing_context = {}
            else:
                print(f"    ⚠️ 伏笔管理器不可用或缺少get_context方法")
            
            print(f"  📈 获取成长规划上下文...")
            if hasattr(self, 'global_growth_planner') and hasattr(self.global_growth_planner, 'get_context'):
                try:
                    growth_context = self.global_growth_planner.get_context(chapter_num)
                    print(f"    ✅ 成长规划上下文获取成功")
                    if isinstance(growth_context, dict):
                        print(f"    📊 成长规划上下文键: {list(growth_context.keys())}")
                        print(f"    📊 成长规划上下文长度: {len(str(growth_context))}")
                    else:
                        print(f"    📊 成长规划上下文: {str(growth_context)[:100]}...")
                except Exception as e:
                    print(f"    ⚠️ 获取成长规划上下文失败: {e}")
                    import traceback
                    traceback.print_exc()
                    growth_context = {}
            else:
                print(f"    ⚠️ 成长规划器不可用或缺少get_context方法")
            
            print(f"  🎯 获取阶段计划...")
            if hasattr(self, 'ensure_stage_plan_for_chapter'):
                try:
                    stage_plan = self.ensure_stage_plan_for_chapter(chapter_num) or {}
                    print(f"    ✅ 阶段计划获取成功")
                    if isinstance(stage_plan, dict):
                        print(f"    📊 阶段计划键: {list(stage_plan.keys())}")
                        print(f"    📊 阶段计划概述: {stage_plan.get('stage_overview', '无概述')[:100]}...")
                    else:
                        print(f"    📊 阶段计划: {str(stage_plan)[:100]}...")
                except Exception as e:
                    print(f"    ⚠️ 获取阶段计划失败: {e}")
                    import traceback
                    traceback.print_exc()
                    stage_plan = {}
            else:
                print(f"    ⚠️ ensure_stage_plan_for_chapter方法不存在")
            
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
                event_guidance = ""
                if hasattr(self, 'event_driven_manager') and hasattr(self.event_driven_manager, 'generate_event_execution_prompt'):
                    event_guidance = self.event_driven_manager.generate_event_execution_prompt(chapter_num)
                    print(f"    ✅ 事件指导生成成功")
                else:
                    print(f"    ⚠️ 事件指导生成方法不可用")
                
                foreshadowing_guidance = ""
                if hasattr(self, 'foreshadowing_manager') and hasattr(self.foreshadowing_manager, 'generate_foreshadowing_prompt'):
                    foreshadowing_guidance = self.foreshadowing_manager.generate_foreshadowing_prompt(chapter_num, event_context)
                    print(f"    ✅ 伏笔指导生成成功")
                else:
                    print(f"    ⚠️ 伏笔指导生成方法不可用")
                
                # 存储到临时字段中，供ContentGenerator使用
                self.novel_data['_current_chapter_guidance'] = {
                    'event_guidance': event_guidance,
                    'foreshadowing_guidance': foreshadowing_guidance
                }
                print(f"    ✅ 事件和伏笔指导已生成并存储")
                
            except Exception as e:
                print(f"    ⚠️ 生成事件/伏笔指导失败: {e}")
                import traceback
                traceback.print_exc()
                self.novel_data['_current_chapter_guidance'] = {}
            
            # 创建 GenerationContext 实例
            print(f"  🏗️ 创建GenerationContext实例...")
            print(f"    章节号: {chapter_num}")
            print(f"    总章节数: {total_chapters}")
            
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
            try:
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
                else:
                    print(f"✅ 基础上下文验证通过")
                
                return base_context
            except Exception as base_error:
                print(f"❌ 创建基础上下文也失败: {base_error}")
                # 最后的手段：创建最简单的上下文
                from Contexts import GenerationContext as GC
                minimal_context = GC(
                    chapter_number=chapter_num,
                    total_chapters=30,
                    novel_data={},
                    stage_plan={},
                    event_context={},
                    foreshadowing_context={},
                    growth_context={}
                )
                minimal_context.generator = self
                return minimal_context
        
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
            print(f"👤 主角: {main_char['name']}")
        
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
        self.novel_data['current_stage'] = stage_name
        current_stage = getattr(self, '_current_stage', None)
        if current_stage != stage_name:
            print(f"🔄 检测到阶段变化: {current_stage} -> {stage_name}")
            self._current_stage = stage_name
            
            # 🆕 阶段变化时清理角色数据
            self._cleanup_characters_for_new_stage(stage_name, chapter_number)

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
            print(f"🧹 新阶段开始，清理不重要角色数据...")
            self._cleanup_characters_for_new_stage(stage_name, chapter_number)            
            # 更新事件驱动管理器
            if hasattr(self, 'event_driven_manager') and self.event_driven_manager:
                # 清除旧的事件
                self.event_driven_manager.active_events.clear()
                self.event_driven_manager.update_from_stage_plan(stage_plan_data["stage_writing_plan"])
            # 同时更新伏笔管理器
            self._update_foreshadowing_for_stage(stage_name, chapter_number)
            
        except Exception as e:
            print(f"❌ 更新{stage_name}阶段事件系统失败: {e}")
            import traceback
            traceback.print_exc()

    def _get_cleanup_strategy_for_stage(self, stage_name: str, chapter_number: int) -> Dict:
        """根据阶段类型获取详细的清理策略 - 修复版本，支持中文阶段名称"""
        
        # 基础策略 - 确保包含所有必要的键
        base_strategy = {
            "keep_major_only": False,
            "preserve_recent_chapters": 5,
            "current_chapter": chapter_number,
            "stage_type": "normal",
            "aggressiveness": "medium",
            "preserve_relationship_network": True,
            "max_minor_characters": 20,
            "max_unnamed_characters": 10,
            "reason": "默认清理策略"
        }
        
        # 根据中文阶段名称调整策略
        stage_lower = stage_name.lower()
        
        if any(keyword in stage_lower for keyword in ["开局", "起始", "开头", "引入", "opening"]):
            base_strategy.update({
                "stage_type": "opening",
                "aggressiveness": "low",
                "preserve_recent_chapters": 10,
                "max_minor_characters": 30,
                "max_unnamed_characters": 20,
                "reason": "开局阶段，保留所有角色用于世界观建立"
            })
        
        elif any(keyword in stage_lower for keyword in ["发展", "展开", "推进", "development"]):
            base_strategy.update({
                "stage_type": "development", 
                "aggressiveness": "medium",
                "preserve_recent_chapters": 8,
                "max_minor_characters": 25,
                "max_unnamed_characters": 15,
                "reason": "发展阶段，适度清理长期不活跃的次要角色"
            })
        
        elif any(keyword in stage_lower for keyword in ["高潮", "决战", "冲突", "转折", "climax"]):
            base_strategy.update({
                "stage_type": "climax",
                "aggressiveness": "high",
                "keep_major_only": True,
                "preserve_recent_chapters": 3,
                "reason": "高潮阶段，专注重要角色和核心剧情"
            })
        
        elif any(keyword in stage_lower for keyword in ["结局", "收尾", "完结", "尾声", "ending"]):
            base_strategy.update({
                "stage_type": "ending",
                "aggressiveness": "high", 
                "keep_major_only": True,
                "preserve_recent_chapters": 1,
                "preserve_relationship_network": False,
                "reason": "结局阶段，只保留核心角色完成故事"
            })
        
        elif any(keyword in stage_lower for keyword in ["最终", "完结", "final"]):
            base_strategy.update({
                "stage_type": "final",
                "aggressiveness": "high",
                "keep_major_only": True,
                "preserve_recent_chapters": 1,
                "preserve_relationship_network": False,
                "reason": "最终阶段，极度精简角色聚焦大结局"
            })
        
        elif chapter_number <= 10:
            base_strategy.update({
                "stage_type": "early",
                "aggressiveness": "low",
                "preserve_recent_chapters": 10,
                "reason": "早期章节，保留角色用于情节发展"
            })
        
        elif chapter_number >= 50:
            base_strategy.update({
                "stage_type": "late",
                "aggressiveness": "medium-high",
                "preserve_recent_chapters": 5,
                "max_minor_characters": 15,
                "reason": "后期章节，清理冗余角色聚焦主线"
            })
        
        # 确保reason键存在
        if "reason" not in base_strategy:
            base_strategy["reason"] = "默认清理策略"
        
        print(f"    📊 清理策略: {base_strategy['reason']}")
        print(f"    ⚙️ 配置: 激进程度={base_strategy['aggressiveness']}, 保留最近{base_strategy['preserve_recent_chapters']}章, 阶段类型={base_strategy['stage_type']}")
        
        return base_strategy

    def _cleanup_characters_for_new_stage(self, stage_name: str, chapter_number: int):
        """为新阶段清理角色数据 - 增强版本"""
        try:
            print(f"  🧹 为{stage_name}阶段清理角色数据...")
            
            # 检查是否有质量评估器
            if not hasattr(self, 'quality_assessor') or not self.quality_assessor:
                print(f"    ⚠️ 质量评估器不可用，跳过角色清理")
                return
            
            # 检查质量评估器是否有策略清理方法
            if not hasattr(self.quality_assessor, 'cleanup_characters_by_strategy'):
                print(f"    ⚠️ 质量评估器没有cleanup_characters_by_strategy方法，使用基础清理")
                # 降级到基础清理
                if hasattr(self.quality_assessor, 'cleanup_unimportant_characters'):
                    strategy = self._get_cleanup_strategy_for_stage(stage_name, chapter_number)
                    self.quality_assessor.cleanup_unimportant_characters(
                        self.novel_data["novel_title"], 
                        keep_major_only=strategy.get("keep_major_only", False)
                    )
                return
            
            # 获取详细的清理策略
            strategy_config = self._get_cleanup_strategy_for_stage(stage_name, chapter_number)
            
            # 执行策略清理
            result = self.quality_assessor.cleanup_characters_by_strategy(
                self.novel_data["novel_title"], 
                strategy_config
            )
            
            if "error" in result:
                print(f"    ❌ 角色清理失败: {result['error']}")
            else:
                print(f"    ✅ {stage_name}阶段角色清理完成")
                print(f"    📊 清理结果: 清理了 {result['cleaned_count']} 个角色")
                print(f"    📈 重要性分布变化:")
                before = result['importance_distribution_before']
                after = result['importance_distribution_after']
                print(f"       重要角色: {before['major']} → {after['major']}")
                print(f"       次要角色: {before['minor']} → {after['minor']}") 
                print(f"       未命名角色: {before['unnamed']} → {after['unnamed']}")
            
        except Exception as e:
            print(f"    ❌ 角色清理失败: {e}")
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

    def check_and_fill_missing_chapters(self) -> bool:
        """检查并补写缺失的章节 - 增强版本：基于实际文件检查"""
        print("\n🔍 开始检查缺失章节（基于实际文件检查）...")
        
        # 获取章节目录
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        chapters_dir = f"小说项目/{safe_title}_章节"
        
        if not os.path.exists(chapters_dir):
            print("  ⚠️ 章节目录不存在，创建目录")
            os.makedirs(chapters_dir, exist_ok=True)
            return True
        
        # 获取目录中实际存在的章节文件
        existing_chapters = set()
        chapter_files_mapping = {}  # 章节号到文件名的映射
        
        for filename in os.listdir(chapters_dir):
            if filename.endswith('.txt'):
                # 解析章节号，例如 "第001章_标题.txt" -> 1
                match = re.search(r'第(\d+)章', filename)
                if match:
                    chapter_num = int(match.group(1))
                    existing_chapters.add(chapter_num)
                    chapter_files_mapping[chapter_num] = filename
                    print(f"   发现章节文件: 第{chapter_num}章 - {filename}")
        
        print(f"  📁 目录中实际章节文件: {len(existing_chapters)}个")
        print(f"    存在的章节: {sorted(existing_chapters)}")
        
        # 获取应该存在的章节范围（基于总章节数）
        total_chapters = self.novel_data["current_progress"]["total_chapters"]
        expected_chapters = set(range(1, total_chapters + 1))
        
        print(f"  📋 应该存在的章节: 1-{total_chapters} (共{total_chapters}章)")
        
        # 找出缺失的章节
        missing_chapters = expected_chapters - existing_chapters
        
        if not missing_chapters:
            print("  ✅ 没有发现缺失章节，章节文件完整")
            return True
        
        print(f"  ❗ 发现 {len(missing_chapters)} 个缺失章节: {sorted(missing_chapters)}")
        
        # 检查novel_data中的generated_chapters是否完整
        generated_in_memory = set(self.novel_data.get("generated_chapters", {}).keys())
        print(f"  💭 内存中的章节数据: {len(generated_in_memory)}章")
        
        # 找出内存中有但文件缺失的章节（需要重新保存）
        chapters_to_resave = generated_in_memory - existing_chapters
        if chapters_to_resave:
            print(f"  💾 需要重新保存的章节: {sorted(chapters_to_resave)}")
        
        # 询问用户是否要补写
        print(f"\n📝 补写选项:")
        print(f"  1. 补写所有缺失章节 ({len(missing_chapters)}章)")
        print(f"  2. 只补写特定范围的缺失章节")
        print(f"  3. 跳过补写")
        
        choice = input("请选择 (1/2/3，默认1): ").strip() or "1"
        
        if choice == "3":
            print("  ⏭️ 跳过补写缺失章节")
            return True
        elif choice == "2":
            # 让用户指定补写范围
            try:
                start_chap = int(input("请输入起始章节号: "))
                end_chap = int(input("请输入结束章节号: "))
                missing_in_range = [chap for chap in missing_chapters if start_chap <= chap <= end_chap]
                if not missing_in_range:
                    print("  ⚠️ 指定范围内没有缺失章节")
                    return True
                print(f"  🎯 补写指定范围内的缺失章节: {missing_in_range}")
                return self._fill_missing_chapters(sorted(missing_in_range))
            except ValueError:
                print("  ❌ 输入无效，补写所有缺失章节")
                return self._fill_missing_chapters(sorted(missing_chapters))
        else:
            # 补写所有缺失章节
            return self._fill_missing_chapters(sorted(missing_chapters))

    def _fill_missing_chapters(self, missing_chapters: List[int]) -> bool:
        """补写指定的缺失章节 - 增强版本"""
        print(f"\n🔄 开始补写 {len(missing_chapters)} 个缺失章节...")
        
        success_count = 0
        failed_chapters = []
        
        # 先检查哪些章节在内存中有数据（只需重新保存文件）
        chapters_to_resave = []
        chapters_to_generate = []
        
        for chapter_num in missing_chapters:
            if chapter_num in self.novel_data.get("generated_chapters", {}):
                chapters_to_resave.append(chapter_num)
            else:
                chapters_to_generate.append(chapter_num)
        
        if chapters_to_resave:
            print(f"  💾 重新保存 {len(chapters_to_resave)} 个章节文件: {chapters_to_resave}")
            for chapter_num in chapters_to_resave:
                try:
                    chapter_data = self.novel_data["generated_chapters"][chapter_num]
                    self.project_manager.save_single_chapter(
                        self.novel_data["novel_title"], 
                        chapter_num, 
                        chapter_data
                    )
                    success_count += 1
                    print(f"    ✅ 重新保存第{chapter_num}章")
                except Exception as e:
                    print(f"    ❌ 重新保存第{chapter_num}章失败: {e}")
                    failed_chapters.append(chapter_num)
        
        # 生成真正缺失的章节内容
        if chapters_to_generate:
            print(f"  🎯 生成 {len(chapters_to_generate)} 个新章节: {chapters_to_generate}")
            
            for chapter_num in chapters_to_generate:
                try:
                    print(f"\n📖 生成第{chapter_num}章...")
                    
                    # 1. 准备生成上下文
                    context = self._prepare_generation_context(chapter_num)
                    if context is None:
                        print(f"  ❌ 第{chapter_num}章生成上下文准备失败")
                        failed_chapters.append(chapter_num)
                        continue
                    
                    # 2. 协调章节准备
                    preparation_result = self._coordinate_chapter_preparation(context)
                    if not preparation_result['success']:
                        print(f"  ⚠️ 第{chapter_num}章准备阶段有警告，但继续生成")
                    
                    # 3. 生成章节内容
                    print(f"  🔄 调用ContentGenerator生成第{chapter_num}章内容...")
                    chapter_result = self.content_generator.generate_chapter_content_for_novel(
                        chapter_num, self.novel_data, context
                    )
                    
                    if not chapter_result:
                        print(f"  ❌ 第{chapter_num}章内容生成失败")
                        failed_chapters.append(chapter_num)
                        continue
                    
                    # 4. 发布生成完成事件
                    self.event_bus.publish('chapter.generated', {
                        'chapter_number': chapter_num,
                        'result': chapter_result,
                        'context': context
                    })
                    
                    print(f"  ✅ 第{chapter_num}章生成完成: {chapter_result.get('chapter_title', '未知标题')}")
                    success_count += 1
                    
                    # 章节间短暂延迟，避免API限制
                    if chapter_num < max(chapters_to_generate):
                        time.sleep(2)
                        
                except Exception as e:
                    error_msg = f"生成第{chapter_num}章时出错: {e}"
                    print(f"  ❌ {error_msg}")
                    import traceback
                    traceback.print_exc()
                    failed_chapters.append(chapter_num)
        
        # 输出补写结果
        print(f"\n🎯 补写完成统计:")
        print(f"  ✅ 成功处理: {success_count} 章")
        if chapters_to_resave:
            print(f"    - 重新保存: {len(chapters_to_resave)} 章")
        if chapters_to_generate:
            print(f"    - 新生成: {len(chapters_to_generate) - len([c for c in failed_chapters if c in chapters_to_generate])} 章")
        print(f"  ❌ 失败章节: {len(failed_chapters)} 章")
        if failed_chapters:
            print(f"  📋 失败章节列表: {failed_chapters}")
        
        # 更新进度信息
        if success_count > 0:
            # 重新检查实际文件数量来更新进度
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
            chapters_dir = f"小说项目/{safe_title}_章节"
            if os.path.exists(chapters_dir):
                chapter_files = [f for f in os.listdir(chapters_dir) if f.endswith('.txt')]
                actual_files_count = len(chapter_files)
                self.novel_data["current_progress"]["completed_chapters"] = actual_files_count
                print(f"  🔄 根据实际文件更新完成章节数: {actual_files_count}")
            
            # 保存进度
            self.project_manager.save_project_progress(self.novel_data)
            print("  💾 项目进度已保存")
        
        return len(failed_chapters) == 0   

    def _add_ai_spicy_opening_to_first_chapter(self, chapter_data: Dict, novel_title: str, novel_synopsis: str, category: str) -> Dict:
        """为第一章添加AI生成的超级俏皮开场白"""
        if not chapter_data or "content" not in chapter_data:
            return chapter_data
        
        # 生成AI俏皮开场白
        opening_remark = self._generate_ai_spicy_opening(novel_title, novel_synopsis, category)
        
        # 将开场白添加到正文开头，用醒目的格式分隔
        original_content = chapter_data["content"]
        chapter_data["content"] = f"{opening_remark}\n\n{'═' * 50}\n\n{original_content}"
        
        # 记录信息
        chapter_data["has_opening_remark"] = True
        chapter_data["opening_remark"] = opening_remark
        chapter_data["remark_style"] = "AI俏皮互动版"
        
        print("🎯 已为第一章添加AI生成的俏皮开场白，准备收割评论！")
        return chapter_data

    def _generate_ai_spicy_opening(self, novel_title: str, novel_synopsis: str, category: str) -> str:
        """用AI生成超级俏皮、刺激评论的开场白"""
        
        prompt = f"""
    你是一个精通番茄小说平台风格的网文大神，请为以下小说生成一个超级俏皮、互动性极强的开场白/作者有话说，用于第一章开头：

    小说标题：《{novel_title}》
    小说简介：{novel_synopsis}
    小说分类：{category}

    要求：
    1. 风格要超级俏皮、幽默、接地气，符合番茄年轻读者的口味
    2. 必须包含刺激读者评论的互动元素，比如"扣1扣2"、"猜剧情"、"找bug"等
    3. 要使用emoji表情和网络流行梗
    4. 长度在50字左右，要有冲击力
    5. 用【】括起来作为醒目标题
    6. 最后一定要有引导评论的强力call to action

    参考风格：
    "【🧠脑子寄存处】存脑子的扣1，不存的扣眼珠子！阅读前请将三观暂存～"
    "【🚨高能预警】本书内容过于离谱，建议搭配降压药食用！"

    请直接返回开场白内容，不要其他说明。
    """
        
        try:
            remark = self.api_client.call_api(
                "你是番茄小说开场白生成专家，风格超级俏皮幽默", 
                prompt, 
                0.8,  # 提高创造性
                purpose="生成俏皮开场白"
            )
            
            if remark and len(remark.strip()) > 20:
                # 清理可能的格式问题
                remark = remark.strip()
                remark = re.sub(r'^["\']|["\']$', '', remark)  # 去除首尾引号
                
                # 确保有足够的互动元素
                if "扣" not in remark and "评论" not in remark and "吐槽" not in remark:
                    remark += "\n\n💬 看到这里的都是真爱，扣1让我看看有多少活人！"
                
                print(f"  ✅ AI开场白生成成功: {remark[:50]}...")
                return remark
                
        except Exception as e:
            print(f"  ❌ 生成AI俏皮开场白失败: {e}")
        
        # AI失败时使用备用手动模板
        return self._generate_fallback_opening(category)

    def _generate_fallback_opening(self, category: str) -> str:
        """AI失败时的备用开场白模板"""
        
        fallback_templates = {
            "男频衍生": "【🧠脑子寄存处】存脑子的扣1，不存的扣眼珠子！阅读前请将三观暂存，离开时记得取回～\n\n📢 友情提示：看到离谱处别骂街，先翻评论区，肯定有课代表！\n\n🎊 首评有惊喜！沙发、地板、天花板都有奖！",
            "科幻": "【👽外星人通知】地球人你好！你已进入科幻维度，请放下常识抱紧我！\n\n🛸 发现bug请立即在评论区上报，奖励是…我的膝盖！\n\n💌 每100条评论加更一章，说到做到！",
            "都市": "【💼社畜避难所】打工人，打工魂，本书专治各种不开心！\n\n🍉 吃瓜群众请就位，剧情越狗血，评论越精彩！\n\n🏆 评论区课代表、预言家、段子手各就各位！",
            "玄幻": "【🔥修炼警告】小心！阅读本书可能走火入魔，笑出腹肌！\n\n⚔️ 觉得主角骚的扣'666',觉得反派惨的扣'哈哈哈'！\n\n🚀 热度破万爆更！评论越多更新越快！",
            "悬疑": "【🕵️侦探集合】柯南道尔附体，福尔摩斯上身！\n\n🔍 能在第三章前猜出真相的，我直播倒立洗头！评论区为证！\n\n💖 看到这里的都是真爱，留个言让我眼熟你呀～"
        }
        
        return fallback_templates.get(category, "【🎮游戏开始】阅读前请调整好姿势，准备好零食！\n\n🎯 觉得好看的扣'爱了',觉得离谱的扣'作者疯了'！\n\n📈 评论就是动力，吐槽就是关爱，来都来了，说两句呗～")     

    def _quick_select_plan(self, plans: List[Dict]) -> Dict:
        """快速选择方案（基于概览信息）"""
        print(f"\n快速选择方案:")
        for i, plan in enumerate(plans, 1):
            print(f"  {i}. 《{plan.get('title', '未知标题')}》 - {plan.get('golden_finger_type', '未知')} - {plan.get('main_plot_direction', '未知')}")
        
        while True:
            try:
                choice = input(f"请选择方案 (1-{len(plans)}): ").strip()
                if not choice:
                    print("使用默认方案1")
                    choice = 1
                    break
                
                choice = int(choice)
                if 1 <= choice <= len(plans):
                    break
                else:
                    print(f"请输入 1-{len(plans)} 之间的数字")
            except ValueError:
                print("请输入有效的数字")
        
        selected_plan = plans[choice - 1]
        print(f"\n✅ 已选择方案 {choice}: 《{selected_plan['title']}》")
        print(f"   金手指: {selected_plan.get('golden_finger_type', '未知')}")
        print(f"   主线: {selected_plan.get('main_plot_direction', '未知')}")
        return selected_plan

    def _display_plan_details(self, plan: Dict, plan_number: int):
        """显示方案的详细信息 - 分页显示避免截断"""
        print(f"\n" + "="*60)
        print(f"📖 方案 {plan_number} 详细信息")
        print("="*60)
        
        print(f"📚 书名: 《{plan.get('title', '未知标题')}》")
        print(f"🎯 金手指类型: {plan.get('golden_finger_type', '未知')}")
        print(f"🛣️ 主线方向: {plan.get('main_plot_direction', '未知')}")
        
        # 分页显示简介
        synopsis = plan.get('synopsis', '暂无简介')
        print(f"\n📝 简介:")
        self._display_long_text(synopsis)
        
        # 分页显示核心方向
        core_direction = plan.get('core_direction', '暂无核心方向')
        print(f"\n🎯 核心方向:")
        self._display_long_text(core_direction)
        
        # 显示目标读者
        target_audience = plan.get('target_audience', '暂无信息')
        print(f"\n👥 目标读者: {target_audience}")
        
        # 显示竞争优势
        competitive_advantage = plan.get('competitive_advantage', '暂无信息')
        print(f"\n⭐ 竞争优势:")
        self._display_long_text(competitive_advantage)
        
        # 显示核心设置
        core_settings = plan.get('core_settings', {})
        if core_settings:
            print(f"\n⚙️ 核心设置:")
            print(f"   世界观: {core_settings.get('world_background', '暂无信息')}")
            print(f"   金手指: {core_settings.get('golden_finger', '暂无信息')}")
            selling_points = core_settings.get('core_selling_points', [])
            if selling_points:
                print(f"   核心爽点:")
                for i, point in enumerate(selling_points, 1):
                    print(f"     {i}. {point}")
        
        print("="*60)

    def _display_long_text(self, text: str, max_line_length: int = 80):
        """分页显示长文本，避免控制台截断"""
        if not text:
            print("   暂无信息")
            return
        
        # 按段落分割
        paragraphs = text.split('\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
                
            # 如果段落较短，直接显示
            if len(paragraph) <= max_line_length:
                print(f"   {paragraph}")
                continue
                
            # 长段落进行分词换行
            words = paragraph.split()
            current_line = ""
            
            for word in words:
                if len(current_line) + len(word) + 1 <= max_line_length:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    print(f"   {current_line}")
                    current_line = word
            
            if current_line:
                print(f"   {current_line}")
        
        # 如果文本很长，询问是否继续
        if len(text) > 500:
            input("\n📄 按Enter键继续...")


    def present_multiple_plans_to_user(self, plans_data: Dict) -> Dict:
        """向用户展示多个方案供选择 - 增强版本，支持计时自动选择"""
        print("\n" + "="*60)
        print("📚 基于您的创意种子，为您生成3个不同风格的小说方案")
        print("="*60)
        
        plans = plans_data.get('plans', [])
        
        # 计算每个方案的综合评分（质量评分 + 新鲜度评分）
        scored_plans = []
        for i, plan in enumerate(plans, 1):
            # 计算综合评分
            quality_score = plan.get('_quality_score', 0)
            freshness_score = plan.get('_freshness_score', 0)
            total_score = quality_score + freshness_score
            
            scored_plans.append({
                'plan': plan,
                'index': i,
                'total_score': total_score,
                'quality_score': quality_score,
                'freshness_score': freshness_score
            })
        
        # 按综合评分排序
        scored_plans.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 显示方案概览（包含评分信息）
        for item in scored_plans:
            plan = item['plan']
            print(f"\n🎯 方案 {item['index']} (评分: {item['total_score']:.1f}/20):")
            print(f"   书名: 《{plan.get('title', '未知标题')}》")
            print(f"   金手指类型: {plan.get('golden_finger_type', '未知')}")
            print(f"   主线方向: {plan.get('main_plot_direction', '未知')}")
            print(f"   质量评分: {item['quality_score']:.1f}/10")
            print(f"   新鲜度评分: {item['freshness_score']:.1f}/10")
            print(f"   简介预览: {plan.get('synopsis', '暂无简介')[:80]}...")
            print("-" * 50)
        
        # 显示推荐的最佳方案
        best_plan = scored_plans[0]
        print(f"\n⭐ 系统推荐: 方案 {best_plan['index']} 《{best_plan['plan']['title']}》")
        print(f"   综合评分: {best_plan['total_score']:.1f}/20 (质量: {best_plan['quality_score']:.1f}, 新鲜度: {best_plan['freshness_score']:.1f})")
        
        # 计时自动选择功能
        selected_plan = self._timed_plan_selection(scored_plans)
        return selected_plan

    def _timed_plan_selection(self, scored_plans: List[Dict]) -> Dict:
        """计时自动选择方案"""
        import threading
        import time
        
        user_choice = [None]  # 使用列表以便在嵌套函数中修改
        
        def get_user_input():
            """获取用户输入"""
            try:
                print(f"\n请选择方案 (1-{len(scored_plans)}):")
                print("  或等待5分钟自动选择推荐方案")
                choice = input("请输入选择: ").strip()
                if choice:
                    user_choice[0] = int(choice)
            except ValueError:
                print("输入无效，请等待自动选择...")
        
        def countdown_timer():
            """倒计时定时器"""
            for i in range(3000, 0, -1):
                if user_choice[0] is not None:
                    return
                time.sleep(1)
            print("\n⏰ 时间到！自动选择推荐方案...")
        
        # 启动用户输入线程
        input_thread = threading.Thread(target=get_user_input)
        input_thread.daemon = True
        input_thread.start()
        
        # 启动倒计时线程
        timer_thread = threading.Thread(target=countdown_timer)
        timer_thread.daemon = True
        timer_thread.start()
        
        # 等待用户输入或超时
        input_thread.join(timeout=3000)
        timer_thread.join(timeout=0)
        
        # 处理选择结果
        if user_choice[0] is not None and 1 <= user_choice[0] <= len(scored_plans):
            selected_index = user_choice[0] - 1
            selected_plan = next((item['plan'] for item in scored_plans if item['index'] == user_choice[0]), None)
            if selected_plan:
                print(f"\n✅ 已手动选择方案 {user_choice[0]}: 《{selected_plan['title']}》")
                return selected_plan
        
        # 自动选择最佳方案
        best_plan = scored_plans[0]
        print(f"\n🤖 已自动选择推荐方案 {best_plan['index']}: 《{best_plan['plan']['title']}》")
        print(f"   理由: 综合评分最高 ({best_plan['total_score']:.1f}/20)")
        return best_plan['plan']

    def _generate_single_novel(self, creative_seed: str, total_chapters: int) -> bool:
        """为单个方案生成完整小说"""
        print(f"\n📖 开始生成小说: 《{self.novel_data['novel_title']}》")
        
        # ==================== 第一阶段：基础规划 ====================
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划")
        print("="*60)

        # 🆕 生成写作风格指南
        self.novel_data["current_progress"]["stage"] = "写作风格制定"
        if not self._generate_writing_style_guide(creative_seed, self.novel_data.get("category", "未分类")):
            print("⚠️ 写作风格指南生成失败，使用默认风格")
        
        # 市场分析
        self.novel_data["current_progress"]["stage"] = "市场分析" 
        if not self._generate_market_analysis(creative_seed):
            return False
        
        # ==================== 第二阶段：世界观与角色 ====================
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与角色设计")
        print("="*60)
        
        # 世界观构建
        self.novel_data["current_progress"]["stage"] = "世界观构建"
        if not self._generate_worldview():
            return False
        
        # 角色设计
        self.novel_data["current_progress"]["stage"] = "角色设计"
        if not self._generate_character_design():
            return False
        
        # ==================== 第三阶段：全书规划 ====================
        print("\n" + "="*60)
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 全局成长规划
        self.novel_data["current_progress"]["stage"] = "成长规划"
        if not self._generate_global_growth_plan():
            print("⚠️  全局成长规划生成失败，使用基础框架")
        
        # 生成全书阶段计划
        self.novel_data["current_progress"]["stage"] = "阶段计划"
        if not self._generate_overall_stage_plan(creative_seed, total_chapters):
            print("⚠️  全书阶段计划生成失败，使用默认阶段划分")
        
        self.novel_data["current_progress"]["stage"] = "阶段详细计划"
        if not self._generate_stage_writing_plans(
            creative_seed=creative_seed,
            novel_title=self.novel_data["novel_title"],
            novel_synopsis=self.novel_data["novel_synopsis"],
            overall_stage_plans=self.novel_data["overall_stage_plans"]
        ):
            print("❌ 生成阶段详细写作计划失败")
            return False
        
        self.stage_plan_manager.print_stage_overview()
        
        # 导出所有事件到JSON文件
        events_file = f"{self.novel_data['novel_title']}_events.json"
        self.stage_plan_manager.export_events_to_json(events_file)    

        # 元素时机规划
        self.novel_data["current_progress"]["stage"] = "元素时机规划"
        if not self._generate_element_timing_plan():
            print("⚠️  元素登场时机规划生成失败，使用基础时机")   
        
        # 初始化系统
        self.novel_data["current_progress"]["stage"] = "系统初始化"
        self._initialize_systems()
        
        # ==================== 第四阶段：内容生成准备 ====================
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 创建项目目录和保存初始进度
        self.novel_data["current_progress"]["stage"] = "项目初始化"
        self._initialize_project()
        
        # ==================== 第五阶段：章节内容生成 ====================
        return self._generate_all_chapters(total_chapters)

    def _generate_novel_cover(self) -> bool:
        """生成小说封面 - 只包含书名和作者文字"""
        if not self.cover_generator:
            print("❌ 封面生成器不可用，跳过封面生成")
            return False
        
        try:
            print("🎨 开始生成小说封面...")
            
            # 获取小说信息
            novel_title = self.novel_data.get("novel_title", "")
            novel_synopsis = self.novel_data.get("novel_synopsis", "")
            category = self.novel_data.get("category", "未分类")
            
            if not novel_title:
                print("❌ 小说标题为空，无法生成封面")
                return False
            
            # 生成封面提示词 - 只包含书名和作者
            cover_prompt = self._generate_cover_prompt(novel_title, novel_synopsis, category)
            
            print(f"  📝 封面提示词: {cover_prompt[:100]}...")
            
            # 创建小说项目目录（如果不存在）
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            project_dir = "小说项目"
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            
            # 设置封面保存路径
            cover_filename = f"{safe_title}_封面.jpg"
            cover_path = os.path.join(project_dir, cover_filename)
            
            print(f"  💾 封面将保存到: {cover_path}")
            
            # 调用豆包文生图生成封面，使用600×800尺寸
            result = self.cover_generator.generate_image(
                prompt=cover_prompt,
                size="600x800",  # 固定为600×800像素
                watermark=False,  # 不加水印
                save_path=cover_path
            )
            
            if result and 'local_path' in result:
                # 更新novel_data
                self.novel_data["cover_image"] = result['local_path']
                self.novel_data["cover_generated"] = True
                
                print(f"✅ 封面生成成功: {result['local_path']}")
                print(f"📖 封面包含: 书名《{novel_title}》 作者: 蓝枫雨")
                return True
            else:
                print("❌ 封面生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 封面生成过程中出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_cover_prompt(self, title: str, synopsis: str, category: str) -> str:
        """生成封面提示词 - 只包含书名和作者，无其他文字"""
        
        # 完整的风格模板字典，覆盖所有主分类
        style_templates = {
            # 女频分类风格
            "女频悬疑": "女性向悬疑风格，神秘氛围，柔和中带悬疑，淡雅色调与暗黑元素结合，细腻情感表达",
            "科幻末世": "赛博朋克风格，未来城市，机械装甲，霓虹灯光，科技感，金属质感，末日氛围",
            "女频衍生": "女性向衍生风格，二次元元素，精致人物设计，浪漫氛围，色彩柔和",
            "民国言情": "复古民国风格，旗袍，老上海风情，怀旧色调，浪漫与时代感结合",
            "悬疑脑洞": "创意悬疑风格，想象力丰富，离奇情节视觉化，神秘诡异氛围",
            "青春甜宠": "甜美青春风格，明亮色彩，浪漫场景，年轻角色，温馨治愈氛围",
            "双男主": "双男主CP风格，男性角色互动，帅气人物设计，热血或暧昧氛围",
            "古言脑洞": "古风创意风格，传统元素与现代脑洞结合，仙侠奇幻色彩",
            "现言脑洞": "现代都市奇幻风格，日常场景中的超现实元素，轻松幽默",
            "玄幻言情": "仙侠爱情风格，唯美场景，仙气缭绕，浪漫与修行结合",
            "宫斗宅斗": "古代宫廷风格，华丽服饰，权谋氛围，女性角色群像",
            "豪门总裁": "现代奢华风格，商务精英，豪门场景，浪漫霸道氛围",
            "动漫衍生": "二次元风格，动漫人物，日系画风，色彩明亮，角色鲜明",
            "星光璀璨": "娱乐圈风格，明星光环，舞台效果，时尚奢华",
            "游戏体育": "竞技热血风格，游戏或运动元素，动态感，团队精神",
            "职场婚恋": "都市情感风格，职场场景，现代生活，情感细腻",
            "双女主": "双女主CP风格，女性角色互动，优雅或帅气设计",
            "年代": "怀旧年代风格，特定时代元素，复古色调，历史感",
            "种田": "田园乡村风格，自然风光，农家生活，温馨朴实",
            "快穿": "多元时空风格，不同世界场景切换，穿越元素",
            
            # 男频分类风格
            "西方奇幻": "史诗奇幻风格，魔法光芒，巨龙，城堡，骑士，油画质感，神秘氛围",
            "东方仙侠": "水墨风格，仙气缭绕，飞剑，仙宫，修真者，传统国风，飘逸潇洒",
            "男频衍生": "热血战斗风格，主角特写，霸气侧漏，力量感，光影对比，电影质感",
            "都市高武": "现代都市与武道结合，都市夜景，武道气息，气功波动，力量感",
            "悬疑灵异": "暗黑风格，神秘氛围，阴影效果，诡异光线，悬疑感，冷色调",
            "抗战谍战": "历史战争风格，民国背景，谍战元素，紧张氛围，怀旧色调",
            "历史古代": "传统历史风格，古代场景，历史人物，文化底蕴",
            "历史脑洞": "创意历史风格，历史与幻想结合，穿越元素，幽默夸张",
            "都市种田": "现代田园风格，城市与自然结合，轻松生活氛围",
            "都市脑洞": "现代奇幻风格，都市生活中的超现实元素，创意想象",
            "都市日常": "温馨治愈风格，日常生活场景，柔和光线，温暖色彩，情感细腻",
            "玄幻脑洞": "创意奇幻风格，想象力丰富，奇特生物，异世界景观，色彩鲜艳",
            "战神赘婿": "霸气回归风格，主角逆袭，身份反差，豪华场景，金色红色主调",
            "传统玄幻": "经典玄幻风格，修行世界，法宝灵兽，传统仙侠元素",
            "都市修真": "现代修真风格，都市与修仙结合，灵气复苏，现代修仙者"
        }
        
        # 获取对应分类的风格，如果没有找到则使用默认风格
        style = style_templates.get(category, "精美插画风格，小说封面设计，符合类型特点")
        
        # 构建提示词 - 完全避免提及任何平台名称
        prompt = f"""
    小说封面设计，{style}，600×800像素，竖版比例，简约风格

    【封面文字内容】：
    书名：《{title}》
    作者：《作者：蓝枫雨》

    【严格禁止的内容】：
    - 禁止添加任何其他文字
    - 禁止出现"番茄小说"、"番茄"等平台相关文字
    - 禁止水印、标语、宣传语
    - 禁止任何额外标注文字

    【设计要求】：
    - 封面设计精美，符合{category}类型风格
    - 书名要醒目突出，使用清晰易读的字体
    - 作者名放在适当位置
    - 整体设计专业简洁

    【文字要求】：
    - 文字清晰可读但不要过于突兀
    - 文字与背景和谐统一
    - 只能出现书名和作者
    """
        
        return prompt.strip()

    def _evaluate_plan_quality(self, plan_data: Dict, category: str, creative_seed: str) -> Dict:
        """使用AI评价方案质量，降低门槛让更多方案通过"""
        print("\n🔍 正在使用AI评价方案质量和新颖度...")
        
        # 使用质量评估器进行新鲜度评估
        freshness_result = self.quality_assessor.assess_freshness(plan_data, "novel_plan")
        
        # 直接从新结构中获取分数
        freshness_score = freshness_result["score"]["total"]
        freshness_verdict = freshness_result["verdict"]
        
        # 构建质量评价提示词
        title = plan_data.get('title', '')
        synopsis = plan_data.get('synopsis', '')
        core_direction = plan_data.get('core_direction', '')
        golden_finger = plan_data.get('core_settings', {}).get('golden_finger', '')
        
        quality_prompt = f"""
    请对以下小说方案进行专业评价：

    【小说分类】{category}
    【创意种子】{creative_seed}

    【方案内容】
    书名：《{title}》
    简介：{synopsis}
    核心方向：{core_direction}
    金手指：{golden_finger}

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": 总体评分(满分10分),
        "quality_verdict": "质量评级",
        "strengths": ["优点列表"],
        "weaknesses": ["待改进方面列表"],
        "optimization_suggestions": ["优化建议列表"]
    }}
    """
        
        try:
            # 调用AI进行质量评价
            quality_result = self.api_client.generate_content_with_retry(
                "plan_quality_evaluation",
                quality_prompt,
                purpose="方案质量评价"
            )
            
            quality_score = quality_result.get("overall_score", 0) if quality_result else 0
            
            # 计算综合评分（质量60% + 新鲜度40%）
            total_score = (quality_score * 0.6) + (freshness_score * 0.4)
            
            # 返回详细结果
            result = {
                "quality_score": quality_score,
                "freshness_score": freshness_score,
                "freshness_details": freshness_result,
                "total_score": total_score,
                "quality_verdict": quality_result.get("quality_verdict", "未知") if quality_result else "未知",
                "freshness_verdict": freshness_verdict,
                # 🆕 降低推荐门槛，让更多方案通过
                "recommendation": quality_score >= 8.0 and freshness_score >= 3.0
            }
            
            print(f"📊 AI评价结果:")
            print(f"  质量评分: {quality_score:.1f}/10分")
            print(f"  新鲜度评分: {freshness_score:.1f}/10分")
            print(f"  综合评分: {total_score:.1f}/10分")
            print(f"  质量判定: {result['quality_verdict']}")
            print(f"  新鲜度判定: {freshness_verdict}")
            print(f"  推荐使用: {'是' if result['recommendation'] else '否'}")
            
            # 将评分存储到方案数据中
            plan_data['_quality_score'] = quality_score
            plan_data['_freshness_score'] = freshness_score
            plan_data['_freshness_details'] = freshness_result
            plan_data['_total_score'] = total_score
            
            return result
            
        except Exception as e:
            print(f"⚠️ AI评价过程中出错: {e}，使用默认评分")
            # 使用默认评分，确保方案通过
            plan_data['_quality_score'] = 6.0
            plan_data['_freshness_score'] = 5.0
            plan_data['_total_score'] = 5.6
            return {
                "quality_score": 6.0,
                "freshness_score": 5.0, 
                "total_score": 5.6,
                "recommendation": False  # 默认推荐通过
            }

    def _generate_and_select_plan(self, creative_seed: str) -> bool:
        """生成多个方案并让用户选择 - 增强版本，包含新鲜度评分"""
        print("=== 步骤1: 基于创意种子生成多个小说方案 ===")
        
        # 假设我们总是处理第一个创意作品
        creative_work = creative_seed
        # 预设一个临时的、可能不准确的标题用于文件名
        temp_title_for_filename = "未定稿小说" 

        # 【核心改动】在这里调用指令精炼层
        refined_creative_seed = self.refine_creative_work_for_ai(creative_work, temp_title_for_filename)

        # 后续所有需要“创意种子”的地方，都使用这个精炼后的文本
        # 例如，传递给 content_generator.generate_multiple_plans
        plans_data = self.content_generator.generate_multiple_plans(refined_creative_seed, "")
        
        if not plans_data or 'plans' not in plans_data:
            print("❌ 方案生成失败")
            return False
        
        plans = plans_data['plans']
        print(f"✅ 成功生成 {len(plans)} 个方案")
        # 解析新的JSON格式
        suggestions = plans.get("suggestions", [])
        if suggestions:
            # 获取第一个建议的名字
            name = suggestions[0].get("name")
            if name and 2 <= len(name) <= 3:
                print(f"  ✅ 获取主角名字: {name}")
                self.content_generator.set_custom_main_character_name(name)
            if not name:
                # 如果没有找到名字，尝试其他可能的字段
                name = plans.get("name")
                if name and 2 <= len(name) <= 3:
                    print(f"  ✅ 获取主角名字: {name}")
                    self.content_generator.set_custom_main_character_name(name)

        # 对每个方案进行质量评价和新鲜度评价
        qualified_plans = []
        for i, plan in enumerate(plans):
            print(f"  🔍 评估方案 {i+1}...")
            
            # 🆕 从方案中获取分类信息
            category_from_plan = plan.get('tags', {}).get('main_category', '未分类')
            
            # ===================== [新增] 分类修正逻辑 =====================
            # 检查标题、简介、关键词和创意种子中是否包含"同人"
            title = plan.get('title', '')
            synopsis = plan.get('synopsis', '')
            keywords = plan.get('tags', {}).get('keywords', [])
            keywords_str = "".join(keywords)

            # 🆕 新增：检查创意种子内容
            creative_core_setting = creative_seed.get('coreSetting', '') if isinstance(creative_seed, dict) else str(creative_seed)
            creative_selling_points = creative_seed.get('coreSellingPoints', '') if isinstance(creative_seed, dict) else ""

            # 合并所有文本进行检查
            combined_text = f"{title} {synopsis} {keywords_str} {creative_core_setting} {creative_selling_points}"

            has_tongren = "同人" in combined_text
            has_dongman = any(keyword in combined_text for keyword in ["动漫", "动画", "漫画"])

            if has_tongren:
                if has_dongman:
                    category_from_plan = "动漫衍生"
                    reason = "同人+动漫"
                else:
                    category_from_plan = "男频衍生" 
                    reason = "同人"
                
                print(f"    🔄 分类修正: 检测到'{reason}'关键字，分类已修正为 '{category_from_plan}'")
                
                if 'tags' not in plan:
                    plan['tags'] = {}
                plan['tags']['main_category'] = category_from_plan
                print(f"    📝 同步更新方案内部分类字段")
            print(f"    📊 方案分类: {category_from_plan}")
            
            evaluation_result = self._evaluate_plan_quality(plan, category_from_plan, creative_seed)
            
            quality_score = evaluation_result.get("quality_score", 0)
            freshness_score = evaluation_result.get("freshness_score", 0)
            total_score = evaluation_result.get("total_score", 0)
            
            if quality_score >= 8.0 and freshness_score >= 3.0:
                qualified_plans.append({
                    'plan': plan,
                    'quality_score': quality_score,
                    'freshness_score': freshness_score,
                    'total_score': total_score,
                    'evaluation_result': evaluation_result,
                    'category': category_from_plan  # 🆕 保存分类信息
                })
                print(f"    ✅ 方案 {i+1} 通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
            else:
                print(f"    ❌ 方案 {i+1} 未通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")

            # 记录最佳方案
            if qualified_plans:
                best_plans.extend(qualified_plans)
                print(f"📈 本轮获得 {len(qualified_plans)} 个合格方案")
                
                # 如果有足够多的合格方案，让用户选择
                if len(best_plans) >= 2:  # 至少有2个合格方案
                    break
            else:
                print("❌ 本轮没有合格方案")
        
        # 如果没有合格方案，使用评分最高的方案作为备选
        if not best_plans and plans_data and 'plans' in plans_data:
            print("⚠️ 所有方案评价均未通过，使用评分最高的方案作为备选")
            # 对所有方案进行评分并选择最好的
            scored_plans = []
            for plan in plans_data['plans']:
                evaluation_result = self._evaluate_plan_quality(plan, category_from_plan, creative_seed)
                total_score = evaluation_result.get("total_score", 0)
                scored_plans.append({
                    'plan': plan,
                    'total_score': total_score
                })
            
            # 按总分排序
            scored_plans.sort(key=lambda x: x['total_score'], reverse=True)
            if scored_plans:
                best_plans = [scored_plans[0]]
        
        if best_plans:
            # 让用户选择方案
            plans_for_selection = [item['plan'] for item in best_plans]
            plans_data_for_selection = {'plans': plans_for_selection}
            
            selected_plan = self.present_multiple_plans_to_user(plans_data_for_selection)
            
            if selected_plan:
                self.novel_data["selected_plan"] = selected_plan
                self.novel_data["novel_title"] = selected_plan["title"]
                self.novel_data["novel_synopsis"] = selected_plan["synopsis"]
                
                # 存储评分信息
                self.novel_data["plan_scores"] = {
                    "quality_score": selected_plan.get('_quality_score', 0),
                    "freshness_score": selected_plan.get('_freshness_score', 0),
                    "total_score": selected_plan.get('_total_score', 0)
                }
                
                print(f"✅ 已选择方案: 《{self.novel_data['novel_title']}》")
                print(f"📊 最终评分 - 质量: {selected_plan.get('_quality_score', 0):.1f}, 新鲜度: {selected_plan.get('_freshness_score', 0):.1f}")
                return True
        
        print("❌ 所有方案生成尝试均失败，终止生成")
        return False