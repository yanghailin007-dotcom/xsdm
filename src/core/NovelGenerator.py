"""
小说生成器主类 - 重构版本
这是一个轻量级的控制器，负责协调各个专门模块的工作
"""

import sys
import signal
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Union, Any, List, Tuple

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

# 导入原有的核心组件
from src.core.APIClient import APIClient
from src.core.ContentGenerator import ContentGenerator
from src.core.Contexts import GenerationContext
from src.core.MaterialManager import MaterialManager
from src.core.EventBus import EventBus
from src.core.ProjectManager import ProjectManager
from src.core.QualityAssessor import QualityAssessor

# 导入管理器
from src.managers.ElementTimingPlanner import ElementTimingPlanner
from src.managers.EmotionalBlueprintManager import EmotionalBlueprintManager
from src.managers.EmotionalPlanManager import EmotionalPlanManager
from src.managers.EventDrivenManager import EventDrivenManager
from src.managers.ForeshadowingManager import ForeshadowingManager
from src.managers.GlobalGrowthPlanner import GlobalGrowthPlanner
from src.managers.RomancePatternManager import RomancePatternManager
from src.managers.StagePlanManager import StagePlanManager

# 导入新的模块化组件
from src.core.generation.PlanGenerator import PlanGenerator
from src.core.fanfiction.FanfictionDetector import FanfictionDetector
from src.core.content.CoverGenerator import CoverGenerator

# 导入工具组件
from src.utils.DouBaoImageGenerator import DouBaoImageGenerator
from src.core.ContentVerifier import ContentVerifier
from config import doubaoconfig

# 导入提示词
from src.prompts.Prompts import Prompts

# 导入工具
from src.utils.logger import get_logger


class NovelGenerator:
    """
    小说生成器主类 - 重构版本
    这是一个轻量级的控制器，负责协调各个专门模块的工作
    """

    def __init__(self, config):
        """初始化小说生成器"""
        self.config = config
        
        # 核心组件初始化
        self._initialize_core_components()
        
        # 模块化组件初始化
        self._initialize_modular_components()
        
        # 管理器初始化
        self._initialize_managers()
        
        # 事件系统设置
        self._setup_event_handlers()
        
        # 数据结构初始化
        self._initialize_data_structures()
        
        # 信号处理
        self._setup_signal_handlers()
        
        # 打印初始化信息
        self._print_initialization_info()

    def _initialize_core_components(self):
        """初始化核心组件"""
        # 日志器（必须最先初始化）
        self.logger = get_logger("NovelGenerator")
        
        # API客户端和质量评估器
        self.api_client = APIClient(self.config)
        self.quality_assessor = QualityAssessor(self.api_client)
        
        # 内容生成器和项目管理者
        self.content_generator = ContentGenerator(
            novel_generator=self,
            api_client=self.api_client,
            config=self.config,
            event_bus=EventBus(),  # 临时创建，后面会被覆盖
            quality_assessor=self.quality_assessor
        )
        self.project_manager = ProjectManager()
        
        # 事件总线（重新创建以正确的引用）
        self.event_bus = EventBus()
        self.content_generator.event_bus = self.event_bus
        
        # 材料管理器（延迟初始化）
        self.material_manager = None
        
        # 内容验证器
        self.content_verifier = ContentVerifier()
        
        # 提示词管理器
        self.Prompts = Prompts()

    def _initialize_modular_components(self):
        """初始化模块化组件"""
        # 方案生成器
        self.plan_generator = PlanGenerator(
            api_client=self.api_client,
            quality_assessor=self.quality_assessor,
            content_generator=self.content_generator
        )
        
        # 同人小说检测器（传递API客户端用于获取背景资料）
        self.fanfiction_detector = FanfictionDetector(api_client=self.api_client)
        
        # 封面生成器
        cover_generator = None
        try:
            doubao_api_key = doubaoconfig.ARK_API_KEY
            if doubao_api_key:
                cover_generator = DouBaoImageGenerator()
                self.logger.info("封面生成器初始化成功")
            else:
                self.logger.info("未配置豆包API密钥，封面生成功能不可用")
        except Exception as e:
            self.logger.info(f"封面生成器初始化失败: {e}")
        
        self.cover_generator = CoverGenerator(cover_generator)
        
        # 章节生成器（暂时使用原方式，后续可以进一步模块化）
        self.chapter_generator = None  # 暂时设为None，避免导入问题

    def _initialize_managers(self):
        """初始化各管理器"""
        # 事件驱动管理器
        self.event_driven_manager = EventDrivenManager(novel_generator=self)
        
        # 伏笔管理器
        self.foreshadowing_manager = ForeshadowingManager(novel_generator=self)
        
        # 全局成长规划器
        self.global_growth_planner = GlobalGrowthPlanner(novel_generator=self)
        
        # 阶段计划管理器
        self.stage_plan_manager = StagePlanManager(novel_generator=self)
        
        # 情感蓝图管理器
        self.emotional_blueprint_manager = EmotionalBlueprintManager(novel_generator=self)
        
        # 情感计划管理器
        self.emotional_plan_manager = EmotionalPlanManager(novel_generator=self)
        
        # 元素时机规划器
        self.element_timing_planner = ElementTimingPlanner(novel_generator=self)
        
        # 联姻模式管理器
        self.romance_manager = RomancePatternManager(self.stage_plan_manager)
        
        # 设置依赖关系
        self._setup_manager_dependencies()

    def _setup_manager_dependencies(self):
        """设置管理器间的依赖关系"""
        self.element_timing_planner.set_foreshadowing_manager(self.foreshadowing_manager)
        self.element_timing_planner.set_project_manager(self.project_manager)
        self.foreshadowing_manager.set_element_timing_planner(self.element_timing_planner)

    def _setup_event_handlers(self):
        """设置事件处理器"""
        self.event_bus.subscribe('chapter.generated', self._on_chapter_generated)
        self.event_bus.subscribe('chapter.assessed', self._on_chapter_assessed)
        self.event_bus.subscribe('error.occurred', self._on_error_occurred)

    def _initialize_data_structures(self):
        """初始化数据结构"""
        self.novel_data = {
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
            "resume_data": None
        }

    def _setup_signal_handlers(self):
        """设置中断信号处理"""
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
        except ValueError:
            pass  # signal only works in main thread of the main interpreter

    def _print_initialization_info(self):
        """打印初始化信息"""
        default_provider = self.api_client.get_default_provider()
        current_model = self.api_client.get_current_model()
        print(f"默认提供商: {default_provider}")
        print(f"当前模型: {current_model}")

    # ==================== 主要接口方法 ====================

    def full_auto_generation(self, creative_seed, total_chapters: Optional[int] = None):
        """
        全自动生成完整小说 - 重构版本
        使用模块化的方式处理生成流程
        """
        print("[START] 开始全自动小说生成 (重构版本)...")
        print(f"创意种子: {creative_seed}")

        if total_chapters is None:
            total_chapters = self.config.get("defaults", {}).get("total_chapters", 50)
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

        try:
            # 预处理：检测同人小说并获取背景资料
            processed_creative_seed = self._preprocess_creative_seed(refined_creative_seed)
            
            # 第一步：生成和选择方案
            selected_plan = self.plan_generator.generate_and_select_plan(processed_creative_seed, self.content_generator)
            if not selected_plan:
                print("❌ 方案生成失败")
                return False

            # 第二步：设置基础信息
            if not self._setup_novel_info(selected_plan, creative_seed, total_chapters):
                return False

            # 第三步：生成完整小说
            return self._generate_complete_novel()

        except Exception as e:
            print(f"❌ 全自动生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _setup_novel_info(self, selected_plan: Dict, creative_seed, total_chapters: Optional[int]) -> bool:
        """设置小说基础信息"""
        try:
            self.novel_data["selected_plan"] = selected_plan
            self.novel_data["novel_title"] = selected_plan["title"]
            self.novel_data["novel_synopsis"] = selected_plan["synopsis"]
            self.novel_data["creative_seed"] = creative_seed
            self.novel_data["category"] = selected_plan.get('tags', {}).get('main_category', '未分类')
            self.novel_data["current_progress"]["total_chapters"] = total_chapters
            self.novel_data["current_progress"]["start_time"] = datetime.now().isoformat()

            # 初始化材料管理器
            self._initialize_material_manager()

            print(f"✅ 小说信息设置完成: 《{selected_plan['title']}》")
            return True

        except Exception as e:
            print(f"❌ 设置小说信息失败: {e}")
            return False

    def _generate_complete_novel(self) -> bool:
        """生成完整小说"""
        try:
            print("开始生成完整小说...")
            
            # 第一阶段：基础规划
            if not self._generate_foundation_planning():
                return False
            
            # 第二阶段：世界观与角色设计
            if not self._generate_worldview_and_characters():
                return False
            
            # 第三阶段：全书规划
            if not self._generate_overall_planning():
                return False
            
            # 第四阶段：内容生成准备
            if not self._prepare_content_generation():
                return False
            
            # 第五阶段：章节内容生成
            total_chapters = self.novel_data["current_progress"]["total_chapters"]
            return self._generate_all_chapters(total_chapters)

        except Exception as e:
            print(f"❌ 小说生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    # ==================== 事件处理器 ====================

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

    def _on_error_occurred(self, data):
        """处理错误事件"""
        error_type = data.get('type')
        chapter = data.get('chapter', '未知')
        message = data.get('message') or data.get('error', '未知错误')
        print(f"❌ 错误({error_type}) 第{chapter}章: {message}")
        
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
        print(f"  📋 输入参数检查:")
        print(f"    - creative_work类型: {type(creative_work)}")
        print(f"    - novel_title: {novel_title}")
        
        # 1. 提取核心组件
        core_setting = creative_work.get("coreSetting", "未提供核心设定。")
        core_selling_points = creative_work.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_work.get("completeStoryline", {})
        
        print(f"  📊 核心组件提取:")
        print(f"    - core_setting长度: {len(core_setting)} 字符")
        print(f"    - core_selling_points长度: {len(core_selling_points)} 字符")
        print(f"    - storyline键数量: {len(storyline)} 个")
        
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
        
        print(f"  📝 精炼提示词构建完成，长度: {len(refinement_prompt)} 字符")
        
        refined_instruction = None
        try:
            # 3. 调用AI进行真正的精炼
            print("  🤖 开始调用AI进行创意精炼...")
            print(f"  🔍 API客户端检查: {type(self.api_client)}")
            print(f"  🔍 API客户端方法: {hasattr(self.api_client, 'call_api')}")
            
            if not hasattr(self.api_client, 'call_api'):
                print("  ❌ API客户端缺少call_api方法，尝试使用generate_content_with_retry")
                if hasattr(self.api_client, 'generate_content_with_retry'):
                    refined_instruction = self.api_client.generate_content_with_retry(
                        "refine_creative_work_for_ai",
                        refinement_prompt,
                        purpose="创意精炼为AI指令"
                    )
                else:
                    print("  ❌ API客户端没有可用的调用方法")
            else:
                refined_instruction = self.api_client.call_api(
                    "refine_creative_work_for_ai",
                    refinement_prompt,
                    0.7,  # 适度创造性
                    purpose="创意精炼为AI指令"
                )
            
            print(f"  📊 AI调用结果检查:")
            print(f"    - 结果类型: {type(refined_instruction)}")
            print(f"    - 结果是否为None: {refined_instruction is None}")
            if refined_instruction:
                print(f"    - 结果长度: {len(refined_instruction)} 字符")
            
            if not refined_instruction or not isinstance(refined_instruction, str):
                print("  ⚠️ AI精炼失败或返回无效结果，使用基础模板")
                refined_instruction = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
            else:
                print("  ✅ AI精炼成功")
            
            # 4. 保存到文件
            print("  💾 开始保存精炼指令到文件...")
            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                output_dir = "小说项目"
                os.makedirs(output_dir, exist_ok=True)
                output_filepath = os.path.join(output_dir, f"{safe_title}_Refined_AI_Brief.txt")
                
                print(f"  📁 文件路径: {output_filepath}")
                
                with open(output_filepath, 'w', encoding='utf-8') as f:
                    f.write(refined_instruction)
                
                print(f"✅  指令精炼完成，已保存至: {output_filepath}")
                print(f"✅  文件大小: {len(refined_instruction)} 字符")
                
                # 验证文件是否真的被创建
                if os.path.exists(output_filepath):
                    file_size = os.path.getsize(output_filepath)
                    print(f"✅  文件验证成功，实际大小: {file_size} 字节")
                else:
                    print(f"❌ 文件验证失败，文件不存在: {output_filepath}")
                    
            except Exception as e:
                print(f"⚠️  保存精炼指令文件失败: {e}")
                import traceback
                traceback.print_exc()
                
            print(f"✅  refine_creative_work_for_ai方法执行完成")
            print(f"  📤 返回结果类型: {type(refined_instruction)}")
            print(f"  📤 返回结果长度: {len(refined_instruction) if refined_instruction else 0} 字符")
            
            return refined_instruction
            
        except Exception as e:
            print(f"❌ AI精炼过程出错: {e}")
            import traceback
            traceback.print_exc()
            print("  🔄 降级到基础模板")
            # 降级到基础模板
            try:
                fallback_result = self._build_basic_instruction_template(core_setting, core_selling_points, storyline)
                print(f"✅  基础模板生成成功，长度: {len(fallback_result)} 字符")
                return fallback_result
            except Exception as fallback_error:
                print(f"❌ 基础模板生成也失败: {fallback_error}")
                # 返回一个最基本的指令
                return f"# AI创作指令\n\n请基于以下创意进行创作：\n核心设定：{core_setting}\n核心卖点：{core_selling_points}"

    # ==================== 预处理方法 ====================

    def _preprocess_creative_seed(self, creative_seed):
        """
        预处理创意种子，检测同人小说并获取背景资料
        
        Args:
            creative_seed: 原始创意种子
            
        Returns:
            处理后的创意种子（包含背景资料信息）
        """
        print("🔍 预处理创意种子：检测同人小说并获取背景资料...")
        
        # 如果是字符串，转换为字典格式
        if isinstance(creative_seed, str):
            try:
                creative_work = json.loads(creative_seed)
            except:
                creative_work = {"coreSetting": creative_seed, "coreSellingPoints": "", "completeStoryline": {}}
        else:
            creative_work = creative_seed
        
        # 检测是否为同人小说
        is_fanfiction, work_name = self.fanfiction_detector.detect_fanfiction(creative_work)
        
        if not is_fanfiction:
            print("    ✅ 检测为原创作品，无需背景资料")
            return creative_seed
        
        print(f"    ✅ 检测为同人小说：《{work_name}》")
        
        # 获取背景资料并进行可信度验证
        background_info = self.fanfiction_detector.get_original_work_background(
            work_name,
            creative_work,
            self.content_verifier
        )
        
        if background_info:
            # 检查验证结果
            verification_result = background_info.get("verification_result")
            if verification_result:
                if verification_result["is_credible"]:
                    print(f"    ✅ 背景资料可信度验证通过 (置信度: {verification_result['confidence_score']:.2f})")
                else:
                    print(f"    ⚠️ 背景资料可信度验证未通过 (置信度: {verification_result['confidence_score']:.2f})")
                    print(f"    📊 等级: {verification_result['credibility_level']}")
                    if verification_result["issues_found"]:
                        print(f"    ❌ 发现问题: {len(verification_result['issues_found'])}个")
                        for issue in verification_result["issues_found"][:3]:  # 只显示前3个问题
                            print(f"       - {issue}")
            
            # 将背景资料添加到创意种子中
            creative_work["original_work_background"] = background_info
            creative_work["is_fanfiction"] = True
            creative_work["original_work_name"] = work_name
            
            print(f"    ✅ 背景资料已整合到创意种子中")
            
            # 返回更新后的创意种子（转换为JSON字符串格式）
            return json.dumps(creative_work, ensure_ascii=False)
        else:
            print(f"    ⚠️ 无法获取《{work_name}》的背景资料，使用原始创意种子")
            return creative_seed

    # ==================== 辅助方法 ====================

    def _initialize_material_manager(self):
        """初始化材料管理器"""
        try:
            novel_title = self.novel_data.get("novel_title")
            if novel_title:
                self.material_manager = MaterialManager(novel_title)
                print(f"✅ 材料管理器初始化成功: {novel_title}")
                
                # 保存项目信息到材料管理器
                self._save_project_info_to_materials()
            else:
                print("⚠️ 小说标题未确定，延迟初始化材料管理器")
        except Exception as e:
            print(f"❌ 材料管理器初始化失败: {e}")
            self.material_manager = None

    def _save_project_info_to_materials(self):
        """保存项目基础信息到材料管理器"""
        if not self.material_manager:
            return
            
        try:
            project_info = {
                "novel_title": self.novel_data.get("novel_title"),
                "category": self.novel_data.get("category"),
                "synopsis": self.novel_data.get("novel_synopsis"),
                "creative_seed": self.novel_data.get("creative_seed"),
                "selected_plan": self.novel_data.get("selected_plan"),
                "total_chapters": self.novel_data.get("current_progress", {}).get("total_chapters", 0),
                "start_time": self.novel_data.get("current_progress", {}).get("start_time"),
                "generation_config": self.config,
                "created_time": datetime.now().isoformat()
            }
            
            result = self.material_manager.create_material("项目信息", project_info)
            if result.get("success"):
                print("✅ 项目信息已保存到材料管理器")
            else:
                print(f"⚠️ 项目信息保存失败: {result.get('error')}")
                
        except Exception as e:
            print(f"❌ 保存项目信息到材料管理器失败: {e}")

    def signal_handler(self, signum, frame):
        """处理中断信号"""
        print(f"\n\n收到中断信号，正在保存进度...")
        self.project_manager.save_project_progress(self.novel_data)
        print("进度已保存，可以安全退出。")
        sys.exit(0)

    # ==================== 兼容性方法 ====================
    # 为了保持向后兼容，保留一些常用的方法签名

    def load_project_data(self, filename: str) -> bool:
        """加载项目数据（兼容性方法）"""
        try:
            data = self.project_manager.load_project(filename)
            if not data:
                return False
                
            self.novel_data = data
            print(f"✅ 项目数据加载完成: {self.novel_data.get('novel_title', '未知标题')}")
            return True
            
        except Exception as e:
            print(f"❌ 加载项目数据失败: {e}")
            return False

    def resume_generation(self, total_chapters: int = 50) -> bool:
        """继续生成小说（兼容性方法）"""
        print("继续生成小说...")
        # TODO: 实现继续生成逻辑
        return True

    def generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """批量生成章节"""
        for chapter_num in range(start_chapter, end_chapter + 1):
            try:
                print(f"\n📖 开始生成第{chapter_num}章...")
                
                # 1. 准备生成上下文
                context = self._prepare_generation_context(chapter_num)
                
                if context is None:
                    print(f"❌ 第{chapter_num}章生成上下文为None，跳过该章")
                    continue
                
                # 2. 委托给ContentGenerator生成内容
                print(f"🔄 调用ContentGenerator生成第{chapter_num}章内容...")
                chapter_result = self.content_generator.generate_chapter_content_for_novel(
                    chapter_num, self.novel_data, context
                )

                if not chapter_result:
                    print(f"❌ 第{chapter_num}章内容生成失败")
                    continue

                # 3. 发布生成完成事件
                self.event_bus.publish('chapter.generated', {
                    'chapter_number': chapter_num,
                    'result': chapter_result,
                    'context': context
                })

                print(f"✅ 第{chapter_num}章生成完成: {chapter_result.get('chapter_title', '未知标题')}")
                
            except Exception as e:
                error_msg = f"生成第{chapter_num}章时出错: {e}"
                print(f"❌ {error_msg}")
                
                self.event_bus.publish('error.occurred', {
                    'type': 'generation_failed',
                    'chapter': chapter_num,
                    'error': str(e)
                })
        
        return True

    def _prepare_generation_context(self, chapter_num: int):
        """准备生成上下文"""
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
                except Exception as e:
                    print(f"    ⚠️ 获取事件上下文失败: {e}")
                    event_context = {}
            
            print(f"  🎭 获取伏笔上下文...")
            if hasattr(self, 'foreshadowing_manager') and hasattr(self.foreshadowing_manager, 'get_context'):
                try:
                    foreshadowing_context = self.foreshadowing_manager.get_context(chapter_num)
                    print(f"    ✅ 伏笔上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取伏笔上下文失败: {e}")
                    foreshadowing_context = {}
            
            print(f"  📈 获取成长规划上下文...")
            if hasattr(self, 'global_growth_planner') and hasattr(self.global_growth_planner, 'get_context'):
                try:
                    growth_context = self.global_growth_planner.get_context(chapter_num)
                    print(f"    ✅ 成长规划上下文获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取成长规划上下文失败: {e}")
                    growth_context = {}
            
            print(f"  🎯 获取阶段计划...")
            if hasattr(self, 'stage_plan_manager'):
                try:
                    stage_plan = self.stage_plan_manager.get_stage_plan_for_chapter(chapter_num) or {}
                    print(f"    ✅ 阶段计划获取成功")
                except Exception as e:
                    print(f"    ⚠️ 获取阶段计划失败: {e}")
                    stage_plan = {}
            
            # 检查novel_data
            print(f"  📚 检查novel_data...")
            if not hasattr(self, 'novel_data') or not self.novel_data:
                print(f"    ⚠️ novel_data不存在或为空，创建基础结构")
                self._initialize_data_structures()
            
            total_chapters = self.novel_data["current_progress"]["total_chapters"]
            print(f"    ✅ novel_data存在, 总章节数: {total_chapters}")
            
            context = GenerationContext(
                chapter_number=chapter_num,
                total_chapters=total_chapters,
                novel_data=self.novel_data,
                stage_plan=stage_plan,
                event_context=event_context,
                foreshadowing_context=foreshadowing_context,
                growth_context=growth_context
            )
            
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
                # generator引用在重构版本中不是必需的
                return base_context
            except Exception as base_error:
                print(f"❌ 创建基础上下文也失败: {base_error}")
                return None

    def choose_category(self):
        """让用户选择小说分类（兼容性方法）"""
        categories = [
            "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武",
            "悬疑灵异", "悬疑脑洞", "抗战谍战", "历史古代", "历史脑洞",
            "都市种田", "都市脑洞", "都市日常", "玄幻脑洞", "战神赘婿",
            "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
        ]
        
        print("\n📚 请选择小说分类:")
        for i, category in enumerate(categories, 1):
            print(f"  {i:2d}. {category}")
        
        # 简化版本，直接返回第一个分类
        selected_category = categories[0]
        self.novel_data["category"] = selected_category
        print(f"  ✓ 已选择分类: {selected_category}")
        return selected_category

    # ==================== 完整的生成流程方法 ====================

    def _generate_foundation_planning(self) -> bool:
        """生成基础规划"""
        print("\n" + "="*60)
        print("📝 第一阶段：基础规划")
        print("="*60)
        
        # 生成写作风格指南
        self.novel_data["current_progress"]["stage"] = "写作风格制定"
        if not self._generate_writing_style_guide():
            print("⚠️ 写作风格指南生成失败，使用默认风格")
        
        # 市场分析
        self.novel_data["current_progress"]["stage"] = "市场分析"
        if not self._generate_market_analysis():
            return False
        
        return True

    def _generate_worldview_and_characters(self) -> bool:
        """生成世界观和角色设计"""
        print("\n" + "="*60)
        print("🌍 第二阶段：世界观与角色设计")
        print("="*60)
        
        # 世界观构建
        self.novel_data["current_progress"]["stage"] = "世界观构建"
        if not self._generate_worldview():
            return False
        
        # 核心角色设计
        print("=== 步骤4: 设计核心角色 (主角/核心盟友/宿敌) ===")
        self.novel_data["current_progress"]["stage"] = "核心角色设计"
        
        core_characters = self.content_generator.generate_character_design(
            novel_title=self.novel_data["novel_title"],
            core_worldview=self.novel_data.get("core_worldview", {}),
            selected_plan=self.novel_data["selected_plan"],
            market_analysis=self.novel_data.get("market_analysis", {}),
            design_level="core",
            global_growth_plan=self.novel_data.get("global_growth_plan"),
            overall_stage_plans=self.novel_data.get("overall_stage_plans"),
            custom_main_character_name=getattr(self, 'custom_main_character_name', None) or ""
        )
        
        if not core_characters:
            print("❌ 核心角色设计失败，终止生成")
            return False
        
        # 持久化核心角色数据
        print("=== 步骤 4.5: 持久化核心角色数据 ===")
        self.quality_assessor.persist_initial_character_designs(
            novel_title=self.novel_data["novel_title"],
            character_design=core_characters
        )
        
        self.novel_data["character_design"] = core_characters
        print("✅ 核心角色设计完成，已建立角色基础库。")
        
        return True

    def _generate_overall_planning(self) -> bool:
        """生成全书规划"""
        print("\n" + "="*60)
        print("📊 第三阶段：全书规划")
        print("="*60)
        
        # 生成情绪蓝图
        self.novel_data["current_progress"]["stage"] = "情绪蓝图规划"
        if not self.emotional_blueprint_manager.generate_emotional_blueprint(
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data["creative_seed"]
        ):
            print("❌ 情绪蓝图生成失败，无法进行后续情绪引导。")
            return False
        
        # 全局成长规划
        self.novel_data["current_progress"]["stage"] = "成长规划"
        if not self._generate_global_growth_plan():
            print("⚠️ 全局成长规划生成失败，使用基础框架")
        
        # 生成全书阶段计划
        self.novel_data["current_progress"]["stage"] = "阶段计划"
        creative_seed = self.novel_data["creative_seed"]
        total_chapters = self.novel_data["current_progress"]["total_chapters"]
        
        overall_stage_plans = self.stage_plan_manager.generate_overall_stage_plan(
            creative_seed,
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data.get("market_analysis", {}),
            self.novel_data.get("global_growth_plan", {}),
            self.novel_data.get("emotional_blueprint", {}),
            total_chapters
        )
        
        self.novel_data["overall_stage_plans"] = overall_stage_plans
        
        if not overall_stage_plans:
            print("⚠️ 全书阶段计划生成失败，使用默认阶段划分")
        
        # 生成阶段详细写作计划
        self.novel_data["current_progress"]["stage"] = "阶段详细计划"
        if not self._generate_stage_writing_plans():
            print("❌ 生成阶段详细写作计划失败")
            return False
        
        # 生成元素时机规划
        self.novel_data["current_progress"]["stage"] = "元素时机规划"
        if not self._generate_element_timing_plan():
            print("⚠️ 元素登场时机规划生成失败，使用基础时机")
        
        # 初始化系统
        self.novel_data["current_progress"]["stage"] = "系统初始化"
        self._initialize_systems()
        
        return True

    def _prepare_content_generation(self) -> bool:
        """准备内容生成"""
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 创建项目目录和保存初始进度
        self.novel_data["current_progress"]["stage"] = "项目初始化"
        self._initialize_project()
        
        return True

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
        actual_chapters_per_batch = min(3, self.config.get("defaults", {}).get("chapters_per_batch", 3))
        
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

    # ==================== 辅助生成方法 ====================

    def _generate_writing_style_guide(self) -> bool:
        """生成写作风格指南"""
        print("=== 步骤1.5: 生成写作风格指南 ===")
        
        try:
            creative_seed = self.novel_data["creative_seed"]
            category = self.novel_data.get("category", "未分类")
            selected_plan = self.novel_data["selected_plan"]
            market_analysis = self.novel_data.get("market_analysis", {})
            
            writing_style = self.content_generator.generate_writing_style_guide(
                creative_seed, category, selected_plan, market_analysis
            )
            
            if writing_style:
                self.novel_data["writing_style_guide"] = writing_style
                print("✅ 写作风格指南生成完成")
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

    def _generate_market_analysis(self) -> bool:
        """生成市场分析"""
        print("=== 步骤2: 进行市场分析和卖点提炼 ===")
        
        creative_seed = self.novel_data["creative_seed"]
        selected_plan = self.novel_data["selected_plan"]
        
        market_analysis = self.content_generator.generate_market_analysis(creative_seed, selected_plan)
        
        self.novel_data["market_analysis"] = market_analysis
        
        if not market_analysis:
            print("  ❌ 市场分析失败，终止生成")
            return False
        
        print("  ✅ 市场分析完成")
        
        # 保存到材料管理器
        self._save_material_to_manager("市场分析", market_analysis, creative_seed=creative_seed)
        return True

    def _generate_worldview(self) -> bool:
        """生成世界观"""
        print("=== 步骤3: 构建核心世界观 ===")
        
        core_worldview = self.content_generator.generate_core_worldview(
            self.novel_data["novel_title"],
            self.novel_data["novel_synopsis"],
            self.novel_data["selected_plan"],
            self.novel_data.get("market_analysis", {})
        )
        
        self.novel_data["core_worldview"] = core_worldview
        
        if not core_worldview:
            print("❌ 世界观构建失败，终止生成")
            return False
        
        print("✅ 世界观构建完成")
        
        # 保存到材料管理器
        self._save_material_to_manager("世界观", core_worldview, novel_title=self.novel_data["novel_title"])
        return True

    def _generate_global_growth_plan(self) -> bool:
        """生成全局成长规划"""
        print("=== 步骤5: 制定全书成长规划框架 ===")
        
        try:
            self.novel_data["global_growth_plan"] = self.global_growth_planner.generate_global_growth_plan()
            
            if self.novel_data["global_growth_plan"]:
                print("✅ 全书成长规划框架制定完成")
                return True
            else:
                print("❌ 全书成长规划生成失败，使用基础框架")
                return False
                
        except Exception as e:
            print(f"⚠️ 全局成长规划器出错: {e}，使用基础框架")
            return False

    def _generate_stage_writing_plans(self) -> bool:
        """生成各阶段详细写作计划"""
        print("=== 步骤6: 生成各阶段详细写作计划 ===")
        
        overall_stage_plans = self.novel_data.get("overall_stage_plans", {})
        if not overall_stage_plans or "overall_stage_plan" not in overall_stage_plans:
            print("❌ 没有全书阶段计划，无法生成详细写作计划")
            return False
        
        try:
            stage_plan_container = overall_stage_plans
            stage_plan_dict = stage_plan_container["overall_stage_plan"]
            
            self.novel_data["stage_writing_plans"] = {}
            
            for stage_name, stage_info in stage_plan_dict.items():
                chapter_range_str = stage_info["chapter_range"]
                
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    stage_range = f"{numbers[0]}-{numbers[1]}"
                else:
                    stage_range = "1-3"
                
                print(f"  📋 生成 {stage_name} 的详细写作计划...")
                print(f"  📋 章节范围: {stage_range}")
                
                stage_plan = self.stage_plan_manager.generate_stage_writing_plan(
                    stage_name=stage_name,
                    stage_range=stage_range,
                    creative_seed=self.novel_data["creative_seed"],
                    novel_title=self.novel_data["novel_title"],
                    novel_synopsis=self.novel_data["novel_synopsis"],
                    overall_stage_plan=stage_plan_dict
                )
                
                if stage_plan:
                    self.novel_data["stage_writing_plans"][stage_name] = stage_plan
                    print(f"  ✅ {stage_name} 详细计划生成成功")
                else:
                    print(f"  ❌ {stage_name} 详细计划生成失败")
            
            success_count = len(self.novel_data["stage_writing_plans"])
            if success_count > 0:
                print(f"✅ 阶段详细计划生成完成: {success_count}/{len(stage_plan_dict)} 个阶段")
                self._save_material_to_manager("阶段计划", self.novel_data["stage_writing_plans"], total_stages=success_count)
                return True
            else:
                print("❌ 所有阶段详细计划生成失败")
                return False
                
        except Exception as e:
            print(f"❌ 生成阶段详细写作计划时出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _generate_element_timing_plan(self) -> bool:
        """生成元素登场时机规划"""
        print("=== 步骤7.5: 制定元素登场时机规划 ===")
        
        try:
            if not self.novel_data.get("global_growth_plan"):
                print("  ⚠️ 没有全局成长计划，无法生成元素时机规划")
                return False
            
            if not self.novel_data.get("overall_stage_plans"):
                print("  ⚠️ 没有全局写作计划成长计划，无法生成元素时机规划")
                return False
            
            timing_plan = self.element_timing_planner.generate_element_timing_plan(
                self.novel_data["global_growth_plan"],
                self.novel_data.get("overall_stage_plans") or {}
            )
            
            if timing_plan:
                self.novel_data["element_timing_plan"] = timing_plan
                print("✅ 元素登场时机规划制定完成并已保存")
                return True
            else:
                print("❌ 元素登场时机规划生成失败")
                return False
                
        except Exception as e:
            print(f"⚠️ 元素时机规划器出错: {e}")
            return False

    def _initialize_systems(self):
        """初始化各种系统"""
        print("=== 步骤7: 初始化系统 ===")
        
        if self.novel_data["overall_stage_plans"]:
            self.event_driven_manager.initialize_event_system()
            print("✅ 事件系统初始化完成")
        
        if self.novel_data["character_design"]:
            self.initialize_foreshadowing_elements()
            print("✅ 伏笔管理系统初始化完成")
        
        print("✅ 第一阶段详细写作计划已生成")

    def _initialize_project(self):
        """初始化项目"""
        import re
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        import os
        os.makedirs(f"小说项目/{safe_title}_章节", exist_ok=True)
        
        self.project_manager.save_project_progress(self.novel_data)
        print("✅ 项目初始进度已保存")

    def _finalize_generation(self) -> bool:
        """完成生成过程"""
        self.novel_data["current_progress"]["stage"] = "完成"
        
        # 保存最终进度和导出总览
        self.project_manager.save_project_progress(self.novel_data)
        self.project_manager.export_novel_overview(self.novel_data)
        
        # 生成小说封面
        print("\n" + "="*60)
        print("🎨 最后一步：生成小说封面")
        print("="*60)
        self.novel_data["current_progress"]["stage"] = "封面生成"
        if not self._generate_novel_cover():
            print("⚠️ 封面生成失败，项目已完成但无封面。")
        
        # 复制项目文件到执行目录
        print("\n" + "="*60)
        print("🚚 正在复制项目文件到执行目录...")
        print("="*60)
        
        target_dir = r"C:\work1.0\Chrome\小说项目"
        novel_title = self.novel_data.get("novel_title")
        
        if novel_title:
            copy_success = self.project_manager.copy_project_to_directory(novel_title, target_dir)
            if not copy_success:
                print(f"⚠️ 项目《{novel_title}》文件复制失败。")
        else:
            print("❌ 无法复制项目文件，因为小说标题未知。")
        
        # 材料管理器导出功能
        if self.material_manager:
            print("\n" + "="*60)
            print("📦 正在生成材料包...")
            print("="*60)
            
            try:
                bundle_result = self.material_manager.create_material_bundle(
                    bundle_name="完整生成材料",
                    material_types=[],
                    time_range=("", ""),
                    include_metadata=True
                )
                
                if isinstance(bundle_result, dict) and bundle_result.get("success"):
                    print(f"✅ 完整材料包生成成功: {bundle_result.get('bundle_name')}")
                    print(f"📁 包含材料数量: {bundle_result.get('total_materials', 0)}个")
                    print(f"📍 保存路径: {bundle_result.get('bundle_path')}")
                else:
                    print(f"⚠️ 材料包生成失败")
                
                manifest = self.material_manager.generate_material_manifest()
                if manifest:
                    print(f"✅ 材料清单生成成功")
                    print(f"📊 材料统计: {manifest.get('total_materials', 0)}个材料")
                    print(f"📂 材料类别: {len(manifest.get('material_categories', {}))}类")
                
                statistics = self.material_manager.get_material_statistics()
                if statistics:
                    print(f"✅ 材料统计完成")
                    print(f"📈 总材料数: {statistics.get('total_materials', 0)}个")
                    print(f"💾 总大小: {statistics.get('total_size', 0)}字节")
                    print(f"📋 材料类型: {len(statistics.get('by_type', {}))}种")
                    
            except Exception as e:
                print(f"❌ 材料导出过程出错: {e}")
        
        print("\n🎉 小说生成完成！")
        self._print_generation_summary()
        return True

    def _generate_novel_cover(self) -> bool:
        """生成小说封面"""
        result = self.cover_generator.generate_novel_cover(
            self.novel_data.get("novel_title", ""),
            self.novel_data.get("novel_synopsis", ""),
            self.novel_data.get("category", "未分类")
        )
        
        if result.get("success"):
            self.novel_data["cover_image"] = result.get("local_path")
            self.novel_data["cover_generated"] = True
            return True
        else:
            return False

    # ==================== 其他辅助方法 ====================

    def initialize_foreshadowing_elements(self):
        """初始化需要铺垫的重要元素"""
        if self.novel_data["core_worldview"]:
            factions = self.novel_data["core_worldview"].get("major_factions", [])
            for i, faction in enumerate(factions):
                intro_chapter = 10 + (i * 15)
                self.foreshadowing_manager.register_element(
                    "factions", faction, "major", min(intro_chapter, 50)
                )
                print(f"✓ 从世界观注册势力伏笔: {faction}")
        
        if self.novel_data["character_design"]:
            important_chars = self.novel_data["character_design"].get("important_characters", [])
            for i, char in enumerate(important_chars):
                if i < 3:
                    intro_chapter = 5 + (i * 8)
                    self.foreshadowing_manager.register_element(
                        "characters", char["name"], "major", intro_chapter
                    )
                    print(f"✓ 从角色设计注册角色伏笔: {char['name']}")

    def _save_writing_style_to_file(self, writing_style: Dict):
        """保存写作风格指南到JSON文件"""
        try:
            from src.utils.path_manager import path_manager
            
            style_data = {
                "novel_title": self.novel_data["novel_title"],
                "category": self.novel_data.get("category", "未分类"),
                "creative_seed": self.novel_data.get("creative_seed", ""),
                "created_time": datetime.now().isoformat(),
                "writing_style_guide": writing_style
            }
            
            success = path_manager.save_writing_style_guide(self.novel_data["novel_title"], writing_style)
            
            if success:
                paths = path_manager.path_config.get_project_paths(self.novel_data["novel_title"])
                actual_path = paths["writing_style_guide"]
                print(f"📝 写作风格指南已保存到: {actual_path}")
            else:
                print(f"⚠️ 写作风格指南保存失败")
            
        except Exception as e:
            print(f"⚠️ 保存写作风格指南失败: {e}")
            import traceback
            traceback.print_exc()

    def _get_default_writing_style(self, category: str) -> Dict:
        """根据分类获取默认的写作风格"""
        # 这里可以返回一个基础的默认风格
        return {
            "core_style": "语言流畅自然，情节推进合理",
            "language_features": ["表达清晰", "描写生动", "节奏适中"],
            "narrative_pace": "稳步推进，高潮适当",
            "dialogue_style": "符合人物身份，自然流畅",
            "description_focus": ["情节推进", "人物刻画", "环境描写"],
            "emotional_tone": "情感真实，有感染力",
            "chapter_structure": "章节完整，衔接自然",
            "important_notes": ["保持风格一致性", "注意情节逻辑", "强化读者代入感"]
        }

    def _save_material_to_manager(self, material_type: str, content: Any, **kwargs):
        """保存材料到材料管理器的通用方法"""
        if not self.material_manager:
            return
            
        try:
            result = self.material_manager.create_material(material_type, content, **kwargs)
            if result.get("success"):
                print(f"✅ {material_type}已保存到材料管理器")
            else:
                print(f"⚠️ {material_type}保存失败: {result.get('error')}")
        except Exception as e:
            print(f"❌ 保存{material_type}到材料管理器失败: {e}")

    def _print_generation_summary(self):
        """打印生成摘要"""
        print("\n" + "="*60)
        print("🎊 小说生成完成摘要")
        print("="*60)
        
        print(f"📖 小说标题: {self.novel_data['novel_title']}")
        print(f"📚 小说分类: {self.novel_data.get('category', '未分类')}")
        print(f"📝 总章节数: {self.novel_data['current_progress']['completed_chapters']}/{self.novel_data['current_progress']['total_chapters']}")
        
        # 字数统计
        total_words = sum(chapter.get('word_count', 0) for chapter in self.novel_data["generated_chapters"].values())
        print(f"📊 总字数: {total_words}字")
        
        print("="*60)