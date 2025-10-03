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

class NovelGenerator:
    """小说生成器主类 - 专注流程控制和协调"""
    
    def __init__(self, config):
        self.config = config
        self.api_client = APIClient(config)
        self.quality_assessor = QualityAssessor(self.api_client, config)
        self.content_generator = ContentGenerator(self.api_client, config, self.quality_assessor)
        self.project_manager = ProjectManager(config)

        # 初始化各个管理器
        self.stage_plan_manager = StagePlanManager.StagePlanManager(self)
        self.event_driven_manager = EventDrivenManager.EventDrivenManager(self)
        self.major_event_manager = self.event_driven_manager  # 向后兼容
        self.foreshadowing_manager = ForeshadowingManager.ForeshadowingManager(self)
        self.global_growth_planner = GlobalGrowthPlanner.GlobalGrowthPlanner(self)

        # 小说数据
        self.novel_data = {
            "novel_title": "未命名小说",
            "novel_synopsis": "",
            "creative_seed": "",
            "selected_plan": None,
            "market_analysis": None,
            "overall_stage_plan": None,
            "stage_writing_plans": {},
            "current_stage": "opening_stage",
            "core_worldview": None,
            "character_design": None,
            "generated_chapters": {},
            "current_progress": {
                "stage": "未开始",
                "completed_chapters": 0,
                "total_chapters": 0,
                "start_time": None,
                "current_batch": 0,
                "last_saved_chapter": 0
            },
            "plot_progression": [],
            "chapter_quality_records": {},
            "optimization_history": {},
            "previous_chapter_endings": {},
            "is_resuming": False,
            "resume_data": None,
            "used_chapter_titles": set(),
        }

        # 初始化
        self._summary_cache = {}
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
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
        
        print(f"🎯 为您生成的方案:")
        print(f"   书名: 《{plan_data['title']}》")
        print(f"   简介: {plan_data['synopsis']}")
        print(f"   核心方向: {plan_data['core_direction']}")
        print(f"   目标读者: {plan_data['target_audience']}")
        print(f"   竞争优势: {plan_data['competitive_advantage']}")
        print("=" * 60)
        
        print(f"✓ 已确定方案: 《{plan_data['title']}》")
        print(f"  核心创作方向: {plan_data['core_direction']}")
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
            
            # 如果进度信息为空但实际有章节，自动修复
            if (self.current_progress["total_chapters"] == 0 and 
                "generated_chapters" in self.novel_data and 
                self.novel_data["generated_chapters"]):
                
                max_chapter = max(self.novel_data["generated_chapters"].keys())
                self.current_progress["total_chapters"] = max_chapter
                self.current_progress["completed_chapters"] = len(self.novel_data["generated_chapters"])
                self.current_progress["stage"] = "写作中"
                print(f"🔄 生成器层面修复进度: {len(self.novel_data['generated_chapters'])}/{max_chapter}章")
            
            # 加载其他数据
            self.market_analysis = self.novel_data.get("market_analysis", {})
            self.overall_stage_plans = self.novel_data.get("overall_stage_plan", {})
            self.stage_writing_plans = self.novel_data.get("stage_writing_plans", {})
            self.core_worldview = self.novel_data.get("core_worldview", {})
            self.character_design = self.novel_data.get("character_design", {})
            self.generated_chapters = self.novel_data.get("generated_chapters", {})
            self.plot_progression = self.novel_data.get("plot_progression", [])
            self.quality_statistics = self.novel_data.get("quality_statistics", {})
            
            # 初始化阶段计划管理器
            self._initialize_stage_plan_manager()
            
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
        
        # 记录创意种子和基础设置
        self.novel_data["creative_seed"] = creative_seed
        self.novel_data["current_progress"]["total_chapters"] = total_chapters
        self.novel_data["current_progress"]["start_time"] = datetime.now().isoformat()

        # 如果是续写模式，跳过前期规划步骤
        if self.novel_data["is_resuming"]:
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
        
        # 步骤7: 全局成长规划（人物成长、势力发展、物品升级）
        self.novel_data["current_progress"]["stage"] = "成长规划"
        if not self._generate_global_growth_plan(creative_seed, total_chapters):
            print("⚠️  全局成长规划生成失败，使用基础框架")
        
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

    def _get_user_inputs(self):
        """获取用户输入（仅选择分类）"""
        self.choose_category()

    def _generate_and_select_plan(self, creative_seed: str) -> bool:
        """生成并选择单一方案"""
        print("=== 步骤1: 基于创意种子生成小说方案 ===")
        
        plan_data = self.content_generator.generate_single_plan(creative_seed)
        if not plan_data:
            print("❌ 方案生成失败，终止生成")
            return False
        
        self.novel_data["selected_plan"] = self.present_plan_to_user(plan_data)
        if not self.novel_data["selected_plan"]:
            print("❌ 方案生成失败，终止生成")
            return False
        
        # 设置选定方案的小说标题和简介
        self.novel_data["novel_title"] = self.novel_data["selected_plan"]["title"]
        self.novel_data["novel_synopsis"] = self.novel_data["selected_plan"]["synopsis"]
        
        print(f"✅ 已确定方案: 《{self.novel_data['novel_title']}》")
        return True

    def _generate_market_analysis(self, creative_seed: str) -> bool:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        self.novel_data["market_analysis"] = self.content_generator.generate_market_analysis(
            creative_seed, self.novel_data["selected_plan"])
        
        if not self.novel_data["market_analysis"]:
            print("❌ 市场分析失败，终止生成")
            return False
        
        print("✅ 市场分析完成")
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

    def _generate_overall_stage_plan(self, creative_seed: str, total_chapters: int) -> bool:
        """生成全书阶段计划"""
        print("=== 步骤5: 生成全书阶段计划 ===")
        
        self.novel_data["overall_stage_plan"] = self.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data.get("market_analysis", {}),
            total_chapters
        )
        
        if self.novel_data["overall_stage_plan"]:
            print("✅ 全书阶段计划生成成功")
            return True
        else:
            return False

    def _generate_global_growth_plan(self, creative_seed: str, total_chapters: int) -> bool:
        """生成全局成长规划 - 精简分层版本"""
        print("=== 步骤6: 制定全书成长规划框架 ===")
        
        try:
            self.novel_data["global_growth_plan"] = self.global_growth_planner.create_comprehensive_growth_plan(
                creative_seed,
                self.novel_data["novel_title"],
                self.novel_data["novel_synopsis"], 
                total_chapters
            )
            
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
        if self.novel_data["overall_stage_plan"]:
            self.event_driven_manager.initialize_event_system()
            print("✅ 事件系统初始化完成")
        
        # 初始化伏笔管理系统
        if self.novel_data["character_design"]:
            self.initialize_foreshadowing_elements()
            print("✅ 伏笔管理系统初始化完成")
        
        # 生成第一阶段详细计划
        self.ensure_stage_plan_for_chapter(1)
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
        """批量生成章节内容 - 调度协调"""
        print(f"=== 生成第{start_chapter}-{end_chapter}章 ===")
        
        successful_chapters = 0
        total_quality_score = 0
        optimized_chapters = 0
        
        for chapter_num in range(start_chapter, end_chapter + 1):
            result = self.content_generator.generate_chapter_content_for_novel(
                chapter_num, 
                self.novel_data
            )
            
            if result:
                self.novel_data["generated_chapters"][chapter_num] = result
                successful_chapters += 1
                
                # 记录情节发展
                self.novel_data["plot_progression"].append({
                    "chapter": chapter_num,
                    "title": result.get("chapter_title", ""),
                    "plot_advancement": result.get("plot_advancement", ""),
                    "key_events": result.get("key_events", []),
                    "connection_to_previous": result.get("connection_to_previous", "")
                })
                
                # 记录质量评估
                assessment = result.get("quality_assessment", {})
                score = assessment.get("overall_score", 0)
                total_quality_score += score
                
                # 记录本地AI痕迹检测结果
                ai_artifacts = self.quality_assessor.detect_ai_artifacts(result.get("content", ""))
                self.novel_data["chapter_quality_records"][chapter_num] = {
                    "assessment": assessment,
                    "timestamp": datetime.now().isoformat(),
                    "original_score": score,
                    "local_ai_artifacts": ai_artifacts
                }
                
                if result.get("optimization_info", {}).get("optimized", False):
                    optimized_chapters += 1
                
                self.novel_data["current_progress"]["completed_chapters"] = chapter_num
                self.novel_data["current_progress"]["last_saved_chapter"] = chapter_num
                
                # 立即保存单章内容
                self.project_manager.save_single_chapter(self.novel_data["novel_title"], chapter_num, result)
                
                # 显示进度和质量信息
                progress = (chapter_num / self.novel_data["current_progress"]["total_chapters"]) * 100
                quality_info = f"质量: {score:.1f}分"
                if result.get("optimization_info", {}).get("optimized", False):
                    quality_info += " (已优化)"
                
                print(f"✓ 第{chapter_num}章《{result['chapter_title']}》完成 ({progress:.1f}%) - {quality_info}")
                
                # 保存整体进度（每3章保存一次）
                if chapter_num % 3 == 0 or chapter_num == self.novel_data["current_progress"]["total_chapters"]:
                    self.project_manager.save_project_progress(self.novel_data)
                
                # 减少延迟
                if chapter_num < end_chapter:
                    time.sleep(2)
            else:
                print(f"✗ 第{chapter_num}章生成失败")
                if chapter_num > start_chapter + 2:
                    print("连续多章生成失败，建议检查API配置或网络连接")
                    break
        
        # 批次质量统计
        if successful_chapters > 0:
            avg_score = total_quality_score / successful_chapters
            print(f"📊 本批次质量统计: 平均分{avg_score:.1f}, 优化章节{optimized_chapters}/{successful_chapters}")
        
        return successful_chapters > 0

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
        """确保为当前章节所属阶段生成详细写作计划 - 协调阶段计划管理器"""
        try:
            print(f"  🔍 确保第{chapter_number}章有阶段计划...")
            
            # 记录阶段转换
            self._log_stage_transition(chapter_number)
            
            # 检查并生成新的阶段计划
            stage_plan = self._check_and_generate_new_stage_plan(chapter_number)
            
            if not stage_plan:
                print(f"  ⚠️ 无法获取第{chapter_number}章的阶段计划，使用基础信息")
                # 返回基础阶段信息
                current_stage = self.stage_plan_manager.get_current_stage(chapter_number)
                return {
                    "stage_name": current_stage,
                    "stage_overview": f"{current_stage}的写作计划",
                    "chapter_range": f"第{chapter_number}章所在阶段"
                }
            
            return stage_plan
            
        except Exception as e:
            print(f"❌ 确保阶段计划时出错: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
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

    def _log_stage_transition(self, chapter_number: int):
        """记录阶段转换信息"""
        current_stage = self.stage_plan_manager.get_current_stage(chapter_number)
        prev_stage = self.stage_plan_manager.get_current_stage(chapter_number - 1) if chapter_number > 1 else None
        
        if prev_stage != current_stage:
            print(f"🎯 阶段转换: 第{chapter_number}章从 '{prev_stage}' 进入 '{current_stage}'")
            
            # 显示阶段边界信息
            boundaries = self.get_stage_boundary_info()
            print(f"  阶段边界: {boundaries['stage_boundaries']}")

    def get_stage_boundary_info(self) -> Dict:
        """获取阶段边界信息 - 协调阶段计划管理器"""
        if hasattr(self.stage_plan_manager, 'stage_boundaries'):
            return {
                "stage_boundaries": self.stage_plan_manager.stage_boundaries,
                "current_stage_plan": self.stage_plan_manager.overall_stage_plans
            }
        return {"stage_boundaries": {}, "current_stage_plan": {}}

    def _get_user_choice_with_timeout(self, options: List[str], timeout: int, default_choice: str, prompt: str) -> str:
        """带超时的用户选择方法"""
        user_choice = [None]
        
        def get_input():
            try:
                choice = input(prompt).strip()
                if choice in options:
                    user_choice[0] = choice
            except:
                pass
        
        # 启动输入线程
        input_thread = threading.Thread(target=get_input)
        input_thread.daemon = True
        input_thread.start()
        
        # 等待用户输入，最多timeout秒
        start_time = time.time()
        
        while time.time() - start_time < timeout and user_choice[0] is None:
            time.sleep(0.1)
        
        return user_choice[0] if user_choice[0] is not None else default_choice