"""小说生成器主类"""

import os
import json
import signal
import sys
import re
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any

import CharacterGrowthManager
import EventDrivenManager
import FactionDevelopmentManager
import ForeshadowingManager
import GlobalGrowthPlanner
from ItemUpgradeSystem import ItemUpgradeSystem
import StagePlanManager
from api_client import APIClient
from content_generator import ContentGenerator
from project_manager import ProjectManager
from quality_assessor import QualityAssessor

class NovelGenerator:
    """小说生成器主类"""
    
    def __init__(self, config):
        self.config = config
        self.api_client = APIClient(config)
        self.quality_assessor = QualityAssessor(self.api_client, config)
        self.content_generator = ContentGenerator(self.api_client, config, self.quality_assessor)
        self.project_manager = ProjectManager(config)

        self.stage_plan_manager = StagePlanManager.StagePlanManager(self)
        self.event_driven_manager = EventDrivenManager.EventDrivenManager(self)
        self.major_event_manager = self.event_driven_manager  # 向后兼容
        self.foreshadowing_manager = ForeshadowingManager.ForeshadowingManager(self)
        self.character_growth_manager = CharacterGrowthManager.CharacterGrowthManager(self)
        self.faction_development_manager = FactionDevelopmentManager.FactionDevelopmentManager(self) 
        self.item_upgrade_system = ItemUpgradeSystem(self)
        self.global_growth_planner = GlobalGrowthPlanner(self)

        # 小说数据
        self.novel_data = {
            "novel_title": "未命名小说",
            "novel_synopsis": "",
            "creative_seed": "",
            "selected_plan": None,
            "market_analysis": None,
            "overall_stage_plan": None,        # 全书阶段划分
            "stage_writing_plans": {},         # 各阶段详细写作计划 {stage_name: plan}
            "current_stage": "opening_stage",  # 当前阶段名称
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
            "subplot_tracking": {
                "foreshadowing_lines": [],
                "emotional_lines": [],
                "subplot_chapters": {"foreshadowing": [], "emotional": []},
                "ratio": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15}
            }
        }

        # 初始化
        self._initialize_subplot_plan()
        self._summary_cache = {}
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def _initialize_subplot_plan(self):
        """初始化暗线推进计划"""
        total_chapters = self.config["defaults"]["total_chapters"]
        
        # 伏笔线推进章节 (每5-8章安排一次伏笔推进)
        foreshadowing_chapters = [i for i in range(5, total_chapters, 7) if i <= total_chapters]
        
        # 感情线推进章节 (每4-6章安排一次感情推进)  
        emotional_chapters = [i for i in range(4, total_chapters, 5) if i <= total_chapters]
        
        self.novel_data["subplot_tracking"]["subplot_chapters"] = {
            "foreshadowing": foreshadowing_chapters,
            "emotional": emotional_chapters
        }

    def is_subplot_chapter(self, chapter_number: int, subplot_type: str) -> bool:
        """判断本章是否应该推进特定暗线"""
        return chapter_number in self.novel_data["subplot_tracking"]["subplot_chapters"][subplot_type]

    def get_chapter_focus(self, chapter_number: int, total_chapters: int) -> str:
        """确定本章的重点内容"""
        if self.is_subplot_chapter(chapter_number, "foreshadowing"):
            return "本章重点推进伏笔线，埋设新伏笔或回收旧伏笔"
        elif self.is_subplot_chapter(chapter_number, "emotional"):
            return "本章重点推进感情线，发展角色关系和情感冲突"
        else:
            # 主线章节
            plot_direction = self.get_plot_direction_for_chapter(chapter_number, total_chapters)
            return plot_direction["main_plot_progress"]

    def signal_handler(self, signum, frame):
        """处理中断信号"""
        print(f"\n\n收到中断信号，正在保存进度...")
        self.project_manager.save_project_progress(self.novel_data)
        print("进度已保存，可以安全退出。")
        sys.exit(0)
    
    def present_plans_to_user(self, plans_data: Dict) -> Optional[Dict]:
        """向用户展示三套方案并让其选择，10秒超时自动选择方案1"""
        print("\n" + "="*60)
        print("📚 基于番茄小说流量趋势，为您生成三套完整方案")
        print("="*60)
        
        plans = plans_data.get("plans", [])
        trend_analysis = plans_data.get("trend_analysis", "")
        
        print(f"📈 当前番茄小说平台趋势分析: {trend_analysis}\n")
        
        for i, plan in enumerate(plans, 1):
            print(f"🎯 方案 {i}:")
            print(f"   书名: 《{plan['title']}》")
            print(f"   简介: {plan['synopsis'][:100]}...")
            print(f"   核心方向: {plan['core_direction']}")
            print(f"   目标读者: {plan['target_audience']}")
            print(f"   竞争优势: {plan['competitive_advantage']}")
            print("-" * 50)
        
        print(f"\n⏰ 您有10秒时间选择，超时将自动选择方案1")
        print("请选择您喜欢的方案 (1-3): ", end="", flush=True)
        
        # 使用多线程实现超时自动选择
        user_choice = [None]
        
        def get_user_input():
            try:
                choice = input()
                user_choice[0] = choice
            except:
                pass
        
        # 启动输入线程
        input_thread = threading.Thread(target=get_user_input)
        input_thread.daemon = True
        input_thread.start()
        
        # 等待用户输入，最多10秒
        start_time = time.time()
        timeout = 10
        
        while time.time() - start_time < timeout and user_choice[0] is None:
            time.sleep(0.1)
        
        # 处理用户选择或超时
        if user_choice[0] is not None:
            try:
                choice = int(user_choice[0])
                if 1 <= choice <= 3:
                    selected_plan = plans[choice-1]
                    print(f"\n✓ 已选择方案 {choice}: 《{selected_plan['title']}》")
                    print(f"  核心创作方向: {selected_plan['core_direction']}")
                    return selected_plan
                else:
                    print("\n⚠️  输入数字不在1-3范围内，自动选择方案1")
            except ValueError:
                print("\n⚠️  输入无效，自动选择方案1")
        
        # 超时或无效输入自动选择方案1
        selected_plan = plans[0]
        print(f"\n✓ 自动选择方案 1: 《{selected_plan['title']}》")
        return selected_plan
    
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
    
    def safe_get_chapter_params(self, chapter_num: int) -> Dict:
        """安全获取章节参数，确保所有必要参数都存在"""
        try:
            print(f"  🔍 开始准备第{chapter_num}章参数...")
            
            # 首先尝试批量参数准备
            batch_params = self.prepare_batch_chapter_params(chapter_num, chapter_num)
            if batch_params and len(batch_params) > 0:
                params = batch_params[0]
                
                # 调试信息
                print(f"  ✅ 第{chapter_num}章批量参数准备成功")
                print(f"  🔍 foreshadowing_guidance 存在: {'foreshadowing_guidance' in params}")
                print(f"  🔍 foreshadowing_guidance 内容长度: {len(params.get('foreshadowing_guidance', '')) if 'foreshadowing_guidance' in params else 0}")
                print(f"  🔍 event_driven_guidance 存在: {'event_driven_guidance' in params}")
                print(f"  🔍 event_driven_guidance 内容长度: {len(params.get('event_driven_guidance', '')) if 'event_driven_guidance' in params else 0}")
                
                return params
            else:
                print(f"  ⚠️  批量参数准备失败，返回基础参数")
                return self._get_chapter_params(chapter_num)
        except Exception as e:
            print(f"❌ 准备章节参数失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            return ""

    def _get_chapter_params(self, chapter_num: int) -> Dict:        
        plot_direction = self.get_plot_direction_for_chapter(chapter_num, self.novel_data["current_progress"]["total_chapters"])
        previous_summary = self._get_cached_previous_summary(chapter_num)
        
        return {
            "chapter_number": chapter_num,
            "total_chapters": self.novel_data["current_progress"]["total_chapters"],
            "novel_title": self.novel_data["novel_title"],
            "novel_synopsis": self.novel_data["novel_synopsis"],
            "worldview_info": json.dumps(self.novel_data["core_worldview"], ensure_ascii=False) if self.novel_data["core_worldview"] else "{}",
            "character_info": json.dumps(self.novel_data["character_design"], ensure_ascii=False) if self.novel_data["character_design"] else "{}",
            "stage_writing_plan": json.dumps(self.ensure_stage_plan_for_chapter(chapter_num), ensure_ascii=False) if self.ensure_stage_plan_for_chapter(chapter_num) else "{}",
            "previous_chapters_summary": previous_summary,
            "main_plot_progress": plot_direction["plot_direction"],
            "plot_direction": plot_direction["plot_direction"],
            "chapter_connection_note": self.get_chapter_connection_note(chapter_num),
            "character_development_focus": plot_direction.get("character_development_focus", ""),
            "major_event_info": "",
            "event_specific_requirements": "",
            "foreshadowing_guidance": ""
        }
    
    def get_plot_direction_for_chapter(self, chapter_number: int, total_chapters: int) -> Dict[str, str]:
        """根据章节位置确定情节发展方向"""
        progress_ratio = chapter_number / total_chapters
        
        if progress_ratio <= 0.1:
            return {
                "plot_direction": "引入核心冲突，建立主角初始状态，埋下故事伏笔",
                "main_plot_progress": "展现世界观基础，介绍主角背景，引发初始事件",
                "character_development_focus": "展示主角性格特点，建立读者共鸣"
            }
        elif progress_ratio <= 0.3:
            return {
                "plot_direction": "主角开始成长，遇到重要盟友和敌人，小冲突不断",
                "main_plot_progress": "推进主线任务，引入重要支线，建立势力关系",
                "character_development_focus": "角色能力提升，人际关系深化"
            }
        elif progress_ratio <= 0.7:
            return {
                "plot_direction": "主要冲突激化，重大转折发生，主角面临重大挑战",
                "main_plot_progress": "核心矛盾爆发，关键事件发生，故事走向转折",
                "character_development_focus": "角色经历重大变化，价值观可能重塑"
            }
        elif progress_ratio <= 0.9:
            return {
                "plot_direction": "冲突走向解决，各条线索开始收束",
                "main_plot_progress": "准备最终决战，解决主要矛盾",
                "character_development_focus": "角色完成最终成长，准备迎接结局"
            }
        else:
            return {
                "plot_direction": "故事圆满收尾，交代各角色最终命运",
                "main_plot_progress": "解决所有矛盾，完成故事主线",
                "character_development_focus": "展示角色最终状态和未来展望"
            }
    
    def initialize_foreshadowing_elements(self):
        """初始化需要铺垫的重要元素"""
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
                    # 检查阶段计划的结构
                    if not stage_plan:
                        continue
                        
                    # 事件系统可能在不同的位置
                    event_system = {}
                    if "stage_writing_plan" in stage_plan and stage_plan["stage_writing_plan"]:
                        event_system = stage_plan["stage_writing_plan"].get("event_system", {})
                    elif "event_system" in stage_plan:
                        event_system = stage_plan["event_system"]
                    else:
                        # 尝试直接从阶段计划中查找事件
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

    def get_foreshadowing_guidance(self, chapter_number: int) -> str:
        """获取本章的铺垫指导"""
        guidance = self.foreshadowing_manager.generate_foreshadowing_prompt(chapter_number)
        if not guidance or not guidance.strip():
            guidance = "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"
        return guidance

    def get_event_driven_guidance(self, chapter_number: int) -> str:
        """获取事件驱动指导"""
        if hasattr(self, 'event_driven_manager'):
            guidance = self.event_driven_manager.generate_event_driven_prompt(chapter_number)
            if not guidance or not guidance.strip():
                guidance = "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"
            return guidance
        return "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"

    def _extract_ending_content(self, content: str) -> str:
        """提取内容结尾部分"""
        content_length = len(content)
        print(f"  📏 章节内容长度: {content_length}字符")
        
        # 尝试多种方法提取结尾
        extraction_methods = [
            self._extract_by_paragraphs,
            self._extract_by_sentences,
            self._extract_by_length
        ]
        
        for method in extraction_methods:
            try:
                ending = method(content)
                if ending and len(ending.strip()) > 50:
                    print(f"  ✅ 使用方法 '{method.__name__}' 成功提取结尾: {ending[:100]}...")
                    return ending
            except Exception as e:
                print(f"  ⚠️  方法 '{method.__name__}' 提取失败: {e}")
                continue
        
        # 所有方法都失败，使用最后200字作为备选
        fallback_ending = content[-200:] if content_length > 200 else content
        print(f"  ⚠️  所有提取方法失败，使用备选结尾: {fallback_ending[:100]}...")
        return fallback_ending

    def _extract_by_paragraphs(self, content: str) -> str:
        """通过段落分割提取结尾"""
        paragraph_separators = ['\n\n', '\n', '。', '！', '？']
        
        for separator in paragraph_separators:
            paragraphs = [p.strip() for p in content.split(separator) if p.strip()]
            if len(paragraphs) >= 2:
                ending_paragraphs = paragraphs[-2:] if len(paragraphs) >= 3 else paragraphs[-1:]
                ending = separator.join(ending_paragraphs)
                if len(ending) > 50:
                    return ending
        
        return content[-300:] if len(content) > 300 else content

    def _extract_by_sentences(self, content: str) -> str:
        """通过句子分割提取结尾"""
        sentence_endings = ['。', '！', '？', '……', '」', '」']
        
        last_end_pos = -1
        for i in range(len(content)-1, max(0, len(content)-500), -1):
            if content[i] in sentence_endings:
                last_end_pos = i
                break
        
        if last_end_pos != -1:
            sentences = []
            sentence_count = 0
            for i in range(last_end_pos, max(0, last_end_pos-500), -1):
                if content[i] in sentence_endings and i != last_end_pos:
                    sentence_count += 1
                    if sentence_count >= 2:
                        return content[i+1:last_end_pos+1]
            
            return content[max(0, last_end_pos-200):last_end_pos+1]
        
        return content[-200:] if len(content) > 200 else content

    def _extract_by_length(self, content: str) -> str:
        """根据内容长度按比例提取结尾"""
        content_length = len(content)
        
        if content_length > 3000:
            return content[-500:]
        elif content_length > 1500:
            return content[-300:]
        else:
            return content[-200:]

    def get_previous_chapter_content(self, current_chapter: int) -> Tuple[Optional[Dict], str]:
        """获取上一章内容，返回内容和状态信息"""
        if current_chapter <= 1:
            return None, "开篇章节"
        
        prev_chapter = current_chapter - 1
        print(f"  🔍 开始获取第{prev_chapter}章的结尾内容...")
        
        # 尝试从内存或文件加载上一章内容
        prev_chapter_data = None
        if prev_chapter in self.novel_data["generated_chapters"]:
            chapter_data = self.novel_data["generated_chapters"][prev_chapter]
            if chapter_data and "content" in chapter_data and chapter_data["content"]:
                print(f"  ✅ 第{prev_chapter}章已在内存中找到且包含内容")
                prev_chapter_data = chapter_data
            else:
                print(f"  ⚠️ 第{prev_chapter}章在内存中但缺少内容，尝试从文件加载...")
                prev_chapter_data = self.load_chapter_content(prev_chapter)
                if prev_chapter_data:
                    print(f"  ✅ 第{prev_chapter}章从文件加载成功")
                    self.novel_data["generated_chapters"][prev_chapter] = prev_chapter_data
                else:
                    print(f"  ❌ 第{prev_chapter}章从文件加载失败")
        else:
            print(f"  🔍 第{prev_chapter}章不在内存中，尝试从文件加载...")
            prev_chapter_data = self.load_chapter_content(prev_chapter)
            if prev_chapter_data:
                print(f"  ✅ 第{prev_chapter}章从文件加载成功")
                self.novel_data["generated_chapters"][prev_chapter] = prev_chapter_data
            else:
                print(f"  ❌ 第{prev_chapter}章从文件加载失败")
        
        return prev_chapter_data, "加载成功" if prev_chapter_data else "加载失败"

    def get_previous_chapter_ending(self, current_chapter: int) -> str:
        """获取上一章的结尾内容和悬念，用于衔接"""
        if current_chapter <= 1:
            print(f"  📖 第{current_chapter}章是开篇第一章，无需获取前一章结尾")
            return "这是开篇第一章，需要建立故事基础。"
        
        prev_chapter_data, status = self.get_previous_chapter_content(current_chapter)
        
        if prev_chapter_data:
            chapter_summary = prev_chapter_data.get("plot_advancement") or prev_chapter_data.get("key_events", "")
            chapter_ending = self._extract_ending_content(prev_chapter_data.get("content", ""))
            next_chapter_hook = prev_chapter_data.get("next_chapter_hook", "")
            
            self.novel_data["previous_chapter_endings"][current_chapter-1] = {
                "summary": chapter_summary,
                "ending": chapter_ending,
                "hook": next_chapter_hook
            }
            
            # 构建详细的上一章结尾描述
            summary_description = f"上一章核心情节: {chapter_summary}" if chapter_summary else "上一章具体情节内容暂不可用。"
            ending_description = f"上一章结尾: {chapter_ending}" if chapter_ending else ""
            hook_description = f"上一章设置的悬念: {next_chapter_hook}" if next_chapter_hook else "上一章未明确设置悬念。"
            
            result_parts = [summary_description]
            if ending_description:
                result_parts.append(ending_description)
            if hook_description:
                result_parts.append(hook_description)
                
            result = "\n\n".join(result_parts)
            print(f"  ✅ 第{current_chapter-1}章结尾信息组合成功，长度: {len(result)}字符")
            return result
        
        error_msg = f"第{current_chapter-1}章的内容无法加载，请确保该章已成功生成并保存。"
        print(f"  ❌❌ {error_msg}")
        print(f"  🔍 内存中的章节: {list(self.novel_data['generated_chapters'].keys())}")
        
        # 尝试检查文件系统
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", self.novel_data["novel_title"])
        chapter_dir = f"小说项目/{safe_title}_章节"
        if os.path.exists(chapter_dir):
            files = os.listdir(chapter_dir)
            print(f"  📁 章节目录存在，包含文件: {files}")
        else:
            print(f"  ❌ 章节目录不存在: {chapter_dir}")
            
        return error_msg

    def generate_previous_chapters_summary(self, current_chapter: int) -> str:
        """生成前情提要，特别关注章节衔接"""
        if current_chapter == 1:
            return "这是开篇第一章，需要建立故事基础。"
        
        # 获取上一章的详细结尾信息
        previous_ending_info = self.get_previous_chapter_ending(current_chapter)
        
        # 尝试加载最近3章的摘要信息
        summary_parts = []
        for i in range(max(1, current_chapter-3), current_chapter):
            chapter_data, _ = self.get_previous_chapter_content(i+1)  # +1因为get_previous_chapter_content需要下一章的编号
            
            if chapter_data:
                chapter_summary = chapter_data.get('plot_advancement') or chapter_data.get('summary')
                if not chapter_summary:
                    chapter_summary = "（该章摘要信息缺失）"
                summary_line = f"第{i}章《{chapter_data.get('chapter_title', '未知标题')}》: {chapter_summary}"
                summary_parts.append(summary_line)
        
        if summary_parts:
            return f"{previous_ending_info}\n\n最近章节摘要：\n" + "\n".join(summary_parts)
        else:
            return previous_ending_info

    def _get_cached_previous_summary(self, chapter_num: int) -> str:
        """获取缓存的上一章摘要"""
        if chapter_num == 1:
            return "这是开篇第一章，需要建立故事基础。"
        
        cache_key = f"prev_summary_{chapter_num - 1}"

        print(f"  📁 获取缓存: {cache_key}")

        if cache_key in self._summary_cache:
            return self._summary_cache[cache_key]
        
        summary = self.generate_previous_chapters_summary(chapter_num)
        print(f"  📁 生成前瞻摘要: {summary}")

        self._summary_cache[cache_key] = summary
        
        return summary
    
    def get_chapter_connection_note(self, chapter_number: int) -> str:
        """根据章节位置生成衔接提示"""
        if chapter_number == 1:
            return "这是开篇第一章，需要建立故事基础，吸引读者继续阅读。"
        else:
            return f"本章必须自然承接第{chapter_number-1}章的结尾，特别是要处理好上一章设置的悬念，确保情节连贯性。"
        
    def prepare_batch_chapter_params(self, start_chapter: int, end_chapter: int) -> List[Dict]:
        """批量准备章节参数 - 集成阶段事件"""
        batch_params = []
        
        print(f"  🔍 prepare_batch_chapter_params 开始准备第{start_chapter}-{end_chapter}章参数")
        
        # 预加载常用数据
        worldview_str = json.dumps(self.novel_data["core_worldview"], ensure_ascii=False) if self.novel_data["core_worldview"] else "{}"
        character_str = json.dumps(self.novel_data["character_design"], ensure_ascii=False) if self.novel_data["character_design"] else "{}"
        
        # 生成主角名字指令
        main_character_instruction = ""
        if self.novel_data.get("custom_main_character_name"):
            main_character_instruction = f"\n# 主角名字\n**主角**: {self.novel_data['custom_main_character_name']} - 请确保在对话和叙述中正确使用这个名字"

        for chapter_num in range(start_chapter, end_chapter + 1):
            # 确保有当前阶段的详细计划（关键修复）
            stage_plan = self.ensure_stage_plan_for_chapter(chapter_num)
            stage_plan_str = json.dumps(stage_plan, ensure_ascii=False) if stage_plan else "{}"
            
            # 获取阶段信息
            current_stage = self.stage_plan_manager.get_current_stage(chapter_num)
            stage_progress = self.stage_plan_manager.get_stage_progress(chapter_num)
            
            # 主线剧情方向
            plot_direction = self.get_plot_direction_for_chapter(chapter_num, self.novel_data["current_progress"]["total_chapters"])
            
            # 确定本章重点
            chapter_focus = self.get_chapter_focus(chapter_num, self.novel_data["current_progress"]["total_chapters"])
            
            # 前情提要
            previous_summary = self._get_cached_previous_summary(chapter_num)

            # 章节衔接提示
            connection_note = self.get_chapter_connection_note(chapter_num)

            # 添加事件驱动和伏笔指导
            event_driven_guidance = self.get_event_driven_guidance(chapter_num) or "# 🎯 事件驱动写作指导\n\n本章为普通主线推进章节。"
            foreshadowing_guidance = self.get_foreshadowing_guidance(chapter_num) or "# 🎭 重要元素铺垫指导\n\n暂无需要铺垫的重要元素。"

            # 基础参数
            params = {
                "chapter_number": chapter_num,
                "total_chapters": self.novel_data["current_progress"]["total_chapters"],
                "novel_title": self.novel_data["novel_title"],
                "novel_synopsis": self.novel_data["novel_synopsis"],
                "worldview_info": worldview_str,
                "character_info": character_str,
                "stage_writing_plan": stage_plan_str,  # 使用阶段详细计划
                "writing_plan_info": stage_plan_str,   # 保持一致
                "current_stage": current_stage,
                "stage_progress": stage_progress,
                "foreshadowing_guidance": foreshadowing_guidance,
                "event_driven_guidance": event_driven_guidance,
                "previous_chapters_summary": previous_summary,
                "main_plot_progress": chapter_focus,
                "main_character_instruction": main_character_instruction,
                "plot_direction": plot_direction["plot_direction"],
                "main_plot_direction": plot_direction["plot_direction"],
                "chapter_connection_note": connection_note,
                "character_development_focus": plot_direction["character_development_focus"],
                "major_event_info": "",
                "event_specific_requirements": ""
            }
            
            # 使用事件驱动管理器处理事件
            event_prompt = self.event_driven_manager.generate_event_driven_prompt(chapter_num)
            params["major_event_info"] = event_prompt
            
            # 设置事件类型标志
            event_context = self.event_driven_manager.get_chapter_event_context(chapter_num)
            params["is_major_event"] = (event_context["event_type"] == "major_event")
            params["event_type"] = event_context["event_type"]
            params["event_stage"] = ""
            
            # 为重大事件章节添加专属要求
            if event_context["event_type"] == "major_event":
                progress = self.event_driven_manager.get_event_progress(chapter_num, event_context["event_info"])
                params["event_stage"] = progress['stage']
                params["event_specific_requirements"] = self._get_event_specific_requirements(progress['stage'])
            
            batch_params.append(params)
        
        print(f"  ✅ prepare_batch_chapter_params 完成，准备了{len(batch_params)}章参数")
        return batch_params

    def _get_event_specific_requirements(self, stage: str) -> str:
        """根据事件阶段获取专属要求"""
        requirements_map = {
            "开局阶段": "重点建立事件基础，引入核心冲突，让读者理解事件的重要性和规模",
            "发展阶段": "深化矛盾冲突，展示角色成长，推进事件核心目标，增加复杂性",
            "高潮阶段": "集中展现冲突激化，制造关键转折和情感爆发点，这是事件的决定性时刻",
            "收尾阶段": "妥善解决主要冲突，展示事件后果，为后续影响做好自然铺垫",
            "结局阶段": "完整收尾事件，总结角色收获，平滑衔接回主线剧情"
        }
        return requirements_map.get(stage, "保持事件连贯性，推进情节发展")

    def _should_optimize_based_on_config(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """基于配置决定是否需要优化"""
        score = assessment.get("overall_score", 0)
        thresholds = self.config["optimization_settings"]["quality_thresholds"]
        
        # 强制优化阈值
        if score < thresholds["needs_optimization"]:
            return True, f"评分低于优化阈值{thresholds['needs_optimization']}分，需要优化"
        
        # 智能跳过优化检查
        skip_optimization, skip_reason = self.quality_assessor.should_skip_optimization(assessment, chapter_data)
        
        if skip_optimization:
            return False, skip_reason
        
        # 建议优化范围
        if score < thresholds["acceptable"]:
            return True, "质量合格但建议优化提升"
        
        return False, "质量良好，跳过优化"

    def _validate_chapter_params(self, params: Dict) -> bool:
        """验证章节参数是否完整"""
        required = [
            'chapter_number', 'novel_title', 'novel_synopsis', 'plot_direction',
            'event_driven_guidance', 'foreshadowing_guidance'
        ]
        for key in required:
            if key not in params or not params[key]:
                print(f"❌ 参数验证失败: 缺少 {key}")
                return False
        return True

    def ensure_chapter_title_uniqueness(self, chapter_data: Dict, chapter_number: int, plot_direction: str) -> Dict:
        """确保章节标题唯一性"""
        original_title = chapter_data.get("chapter_title", "")
        if not original_title:
            return chapter_data
        
        # 检查是否重复
        is_unique, duplicate_chapter = self.is_chapter_title_unique(original_title, chapter_number)
        if is_unique:
            self.novel_data["used_chapter_titles"].add(original_title)
            chapter_data["title_was_changed"] = False
            return chapter_data
        
        print(f"⚠️  章节标题重复: '{original_title}' 与第{duplicate_chapter}章重复，正在生成新标题...")
        
        # 方法1: 使用智能重命名
        new_title = self.generate_unique_chapter_title(original_title, chapter_number, plot_direction)
        
        if new_title != original_title:
            chapter_data["chapter_title"] = new_title
            chapter_data["title_was_changed"] = True
            chapter_data["original_title"] = original_title
            self.novel_data["used_chapter_titles"].add(new_title)
            print(f"✓ 使用新标题: '{new_title}'")
        
        return chapter_data

    def generate_unique_chapter_title(self, original_title: str, chapter_number: int, 
                                    plot_direction: str, retry_count: int = 0) -> str:
        """生成唯一的章节标题"""
        if retry_count >= 2:
            return self._generate_deterministic_title(original_title, chapter_number)
        
        # 基于情节方向生成新标题
        title_prompt = f"""
请为小说的第{chapter_number}章生成一个新的、富有吸引力的章节标题。

原始标题（已重复）: {original_title}
情节发展方向: {plot_direction}

要求:
1. 与原始标题风格一致但完全不同
2. 反映本章情节发展
3. 长度8-15字
4. 避免与已有章节标题重复
5. 富有文学性和吸引力

已有章节标题: {list(self.novel_data["used_chapter_titles"])[-10:]}

请只返回标题文本，不要其他内容。
"""
        
        try:
            new_title = self.api_client.call_api('deepseek', "你是小说章节标题生成专家", title_prompt, 0.7, purpose="生成唯一章节标题")
            if new_title and new_title.strip():
                new_title = new_title.strip().strip('"').strip("'").strip()
                new_title = re.sub(r'^["\']|["\']$', '', new_title)
                
                # 再次检查唯一性
                is_unique, _ = self.is_chapter_title_unique(new_title)
                if is_unique and len(new_title) >= 4:
                    return new_title
                else:
                    return self.generate_unique_chapter_title(original_title, chapter_number, plot_direction, retry_count + 1)
        except Exception as e:
            print(f"生成新标题失败: {e}")
        
        return self._generate_deterministic_title(original_title, chapter_number)

    def _generate_deterministic_title(self, original_title: str, chapter_number: int) -> str:
        """使用确定性方法生成标题"""
        base_title = re.sub(r'[（(].*[）)]', '', original_title).strip()
        
        alternatives = [
            f"{base_title}·新篇",
            f"{base_title}·风云再起",
            f"{base_title}·波澜再起",
            f"{base_title}·暗流涌动",
            f"{base_title}·转折时刻",
            f"{base_title}·命运交错",
            f"第{chapter_number}章 {base_title}",
            f"{base_title}（续）"
        ]
        
        for alt in alternatives:
            if self.is_chapter_title_unique(alt)[0]:
                return alt
        
        return f"第{chapter_number}章 {base_title}"

    def is_chapter_title_unique(self, title: str, exclude_chapter: int = None) -> Tuple[bool, Optional[int]]:
        """检查章节标题是否唯一，返回是否唯一和重复的章节号"""
        for chapter_num, chapter_data in self.novel_data["generated_chapters"].items():
            if exclude_chapter and chapter_num == exclude_chapter:
                continue
            existing_title = chapter_data.get("chapter_title", "")
            if existing_title and existing_title == title:
                return False, chapter_num
        return True, None

    def generate_and_optimize_chapter(self, chapter_number: int, total_chapters: int) -> Optional[Dict]:
        """生成并优化章节内容 - 严格两步法"""
        print(f"生成第{chapter_number}章...")

        # 使用安全的参数获取方法
        chapter_params = self.safe_get_chapter_params(chapter_number)
        
        if not chapter_params or not self._validate_chapter_params(chapter_params):
            print(f"❌ 第{chapter_number}章参数获取失败")
            return None
        
        print(f"  ✅ 第{chapter_number}章所有参数验证通过")
        
        # 确定本章重点
        chapter_focus = self.get_chapter_focus(chapter_number, total_chapters)
        print(f"  本章重点: {chapter_focus}")
        
        # 添加主角名字指令
        if self.novel_data.get("custom_main_character_name"):
            main_character_instruction = f"\n# 主角名字\n**主角**: {self.novel_data['custom_main_character_name']} - 请确保在对话和叙述中正确使用这个名字"
            chapter_params['main_character_instruction'] = main_character_instruction
        
        # 使用严格的两步法生成章节内容
        chapter_data = self.content_generator.generate_chapter_content(chapter_params)
        if not chapter_data:
            print(f"✗ 第{chapter_number}章生成失败")
            return None
        
        # 确保章节标题唯一性
        chapter_data = self.ensure_chapter_title_uniqueness(chapter_data, chapter_number, chapter_params.get("plot_direction", ""))
        # 设置章节特定信息
        chapter_data["key_events"] = chapter_data.get("key_events", [])
        chapter_data["next_chapter_hook"] = chapter_data.get("next_chapter_hook", "")
        chapter_data["connection_to_previous"] = chapter_data.get("connection_to_previous", "")
        chapter_data["plot_advancement"] = chapter_data.get("plot_advancement", "")
        chapter_data["character_development"] = chapter_data.get("character_development", "")
        chapter_data["previous_chapters_summary"] = chapter_params.get("previous_chapters_summary", "")
        
        # 质量评估
        assessment = self.quality_assessor.quick_assess_chapter_quality(
            chapter_data.get("content", ""),
            chapter_data.get("chapter_title", ""),
            chapter_number,
            self.novel_data["novel_title"],
            chapter_params.get("previous_chapters_summary", ""),
            chapter_data.get("word_count", 0)
        )
        
        # 设置质量评分
        score = assessment.get("overall_score", 0)
        chapter_data["quality_score"] = score
        chapter_data["quality_assessment"] = assessment
        
        print(f"  质量评分: {score:.1f}分")
        
        # 根据配置决定是否优化
        optimize_needed, optimize_reason = self._should_optimize_based_on_config(assessment, chapter_data)
        
        if optimize_needed:
            print(f"  🔧 进行优化: {optimize_reason}")
            optimized_data = self.quality_assessor.optimize_chapter_content({
                "assessment_results": json.dumps(assessment, ensure_ascii=False),
                "original_content": chapter_data.get("content", ""),
                "priority_fix_1": assessment.get("weaknesses", [""])[0] if assessment.get("weaknesses") else "提升质量",
                "priority_fix_2": assessment.get("weaknesses", [""])[1] if len(assessment.get("weaknesses", [])) > 1 else "",
                "priority_fix_3": assessment.get("weaknesses", [""])[2] if len(assessment.get("weaknesses", [])) > 2 else ""
            })
            if optimized_data:
                chapter_data.update(optimized_data)
                # 重新评估优化后的质量
                new_assessment = self.quality_assessor.quick_assess_chapter_quality(
                    chapter_data.get("content", ""),
                    chapter_data.get("chapter_title", ""),
                    chapter_number,
                    self.novel_data["novel_title"],
                    chapter_params.get("previous_chapters_summary", ""),
                    chapter_data.get("word_count", 0)
                )
                new_score = new_assessment.get("overall_score", 0)
                improvement = new_score - score
                print(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{improvement:+.1f}分)")
                chapter_data["quality_assessment"] = new_assessment
            else:
                print(f"  ⚠️ 优化失败，保持原内容")
                chapter_data["quality_assessment"] = assessment
        else:
            print(f"  ✓ {optimize_reason}")
            chapter_data["quality_assessment"] = assessment
        
        return chapter_data

    def check_chapter_connection(self, current_chapter: int, new_chapter_data: Dict) -> bool:
        """检查章节衔接是否自然"""
        if current_chapter <= 1:
            return True
        
        # 获取上一章的结尾
        prev_ending_info = self.novel_data["previous_chapter_endings"].get(current_chapter - 1)
        if not prev_ending_info:
            return True
        
        new_chapter_content = new_chapter_data.get("content", "")
        prev_hook = prev_ending_info.get("hook", "")
        
        # 检查新章节是否回应了上一章的悬念
        if prev_hook and prev_hook not in new_chapter_content[:500]:
            print(f"⚠️  警告: 第{current_chapter}章可能没有很好承接上一章的悬念")
            return False
        
        print(f"✓ 第{current_chapter}章与前一章衔接检查通过")
        return True
    
    def optimized_generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """优化的批量生成"""
        print(f"=== 优化生成第{start_chapter}-{end_chapter}章 ===")
        
        # 批量准备参数
        batch_params = self.prepare_batch_chapter_params(start_chapter, end_chapter)
        
        successful_chapters = 0
        total_quality_score = 0
        optimized_chapters = 0
        
        for i, chapter_params in enumerate(batch_params):
            chapter_num = start_chapter + i
            
            result = self.generate_and_optimize_chapter(chapter_num, self.novel_data["current_progress"]["total_chapters"])
            if result:
                # 检查章节衔接
                if not self.check_chapter_connection(chapter_num, result):
                    print(f"⚠️  第{chapter_num}章衔接可能存在问题，但将继续生成")
                
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
    
    def generate_chapters_batch(self, start_chapter: int, end_chapter: int) -> bool:
        """批量生成章节内容 - 使用优化版本"""
        return self.optimized_generate_chapters_batch(start_chapter, end_chapter)

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
        
        # 根据分类自动设置推荐配比
        self.set_ratio_by_category(selected_category)

    def set_ratio_by_category(self, category: str):
        """根据分类自动设置推荐配比"""
        category_ratios = {
            "西方奇幻": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "东方仙侠": {"main": 0.65, "emotional": 0.20, "foreshadowing": 0.15},
            "科幻末世": {"main": 0.75, "emotional": 0.10, "foreshadowing": 0.15},
            "男频衍生": {"main": 0.8, "emotional": 0.1, "foreshadowing": 0.1},
            "都市高武": {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1},
            "悬疑灵异": {"main": 0.6, "emotional": 0.1, "foreshadowing": 0.3},
            "悬疑脑洞": {"main": 0.6, "emotional": 0.1, "foreshadowing": 0.3},
            "抗战谍战": {"main": 0.75, "emotional": 0.15, "foreshadowing": 0.1},
            "历史古代": {"main": 0.65, "emotional": 0.2, "foreshadowing": 0.15},
            "历史脑洞": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "都市种田": {"main": 0.6, "emotional": 0.3, "foreshadowing": 0.1},
            "都市脑洞": {"main": 0.65, "emotional": 0.2, "foreshadowing": 0.15},
            "都市日常": {"main": 0.6, "emotional": 0.3, "foreshadowing": 0.1},
            "玄幻脑洞": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "战神赘婿": {"main": 0.75, "emotional": 0.2, "foreshadowing": 0.05},
            "动漫衍生": {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1},
            "游戏体育": {"main": 0.8, "emotional": 0.1, "foreshadowing": 0.1},
            "传统玄幻": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15},
            "都市修真": {"main": 0.65, "emotional": 0.2, "foreshadowing": 0.15}
        }
        
        if category in category_ratios:
            self.novel_data["subplot_tracking"]["ratio"] = category_ratios[category]
            ratio = self.novel_data["subplot_tracking"]["ratio"]
            print(f"🎯 根据 {category} 分类自动设置配比: 主线{ratio['main']*100}%, 感情线{ratio['emotional']*100}%, 伏笔线{ratio['foreshadowing']*100}%")
        else:
            self.novel_data["subplot_tracking"]["ratio"] = {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1}
            ratio = self.novel_data["subplot_tracking"]["ratio"]
            print(f"⚠️  未找到 {category} 的推荐配比，使用默认配比")

    def set_recommended_ratio(self, experience_level: str = "beginner", genre: str = None):
        """设置推荐配比"""
        recommended_ratios = {
            "beginner": {"main": 0.75, "emotional": 0.15, "foreshadowing": 0.10},
            "intermediate": {"main": 0.70, "emotional": 0.15, "foreshadowing": 0.15},
            "advanced": {"main": 0.65, "emotional": 0.20, "foreshadowing": 0.15}
        }
    
        if genre:
            genre_ratios = {
                "爽文": {"main": 0.75, "emotional": 0.10, "foreshadowing": 0.15},
                "言情": {"main": 0.60, "emotional": 0.30, "foreshadowing": 0.10},
                "悬疑": {"main": 0.65, "emotional": 0.05, "foreshadowing": 0.30},
                "玄幻": {"main": 0.70, "emotional": 0.15, "foreshadowing": 0.15},
                "都市": {"main": 0.65, "emotional": 0.25, "foreshadowing": 0.10}
            }
            if genre in genre_ratios:
                self.novel_data["subplot_tracking"]["ratio"] = genre_ratios[genre]
                print(f"🎯 使用{genre}题材推荐配比")
            else:
                self.novel_data["subplot_tracking"]["ratio"] = recommended_ratios[experience_level]
                print(f"🎯 使用{experience_level}级别推荐配比")
        else:
            self.novel_data["subplot_tracking"]["ratio"] = recommended_ratios[experience_level]
            print(f"🎯 使用{experience_level}级别推荐配比")
        
        self._initialize_subplot_plan_with_ratio()

    def _initialize_subplot_plan_with_ratio(self):
        """根据配比初始化暗线推进计划"""
        if "total_chapters" not in self.novel_data["current_progress"]:
            print("❌ 错误: total_chapters 未设置，无法初始化暗线计划")
            return
        
        total_chapters = self.novel_data["current_progress"]["total_chapters"]
        ratio = self.novel_data["subplot_tracking"]["ratio"]
        
        # 验证配比
        total_ratio = sum(ratio.values())
        if abs(total_ratio - 1.0) > 0.01:
            print(f"⚠️  配比总和为{total_ratio*100}%，自动调整为100%")
            scale_factor = 1.0 / total_ratio
            for key in ratio:
                ratio[key] *= scale_factor
        
        # 修复章节分配计算
        emotional_count = max(1, int(total_chapters * ratio["emotional"]))
        foreshadowing_count = max(1, int(total_chapters * ratio["foreshadowing"]))
        main_count = total_chapters - emotional_count - foreshadowing_count
        
        print(f"📈 章节分配: 主线{main_count}章, 感情线{emotional_count}章, 伏笔线{foreshadowing_count}章")
        print(f"📊 配比: 主线{ratio['main']*100}%, 感情线{ratio['emotional']*100}%, 伏笔线{ratio['foreshadowing']*100}%")
        
        # 生成均匀分布的章节编号
        emotional_chapters = self._generate_evenly_distributed_chapters(emotional_count, total_chapters, "emotional")
        foreshadowing_chapters = self._generate_evenly_distributed_chapters(foreshadowing_count, total_chapters, "foreshadowing")
        
        self.novel_data["subplot_tracking"]["subplot_chapters"] = {
            "foreshadowing": foreshadowing_chapters,
            "emotional": emotional_chapters
        }

    def _generate_evenly_distributed_chapters(self, count: int, total: int, line_type: str) -> List[int]:
        """生成均匀分布的章节编号"""
        if count <= 0:
            return []
        
        count = max(1, count)
        
        # 根据暗线类型确定起始位置
        start_chapter = max(5, 1) if line_type == "emotional" else max(3, 1)
        
        # 避免最后一章
        available_chapters = list(range(start_chapter, total))
        
        if count >= len(available_chapters):
            return available_chapters
        
        # 智能分布算法
        if count == 1:
            return [available_chapters[len(available_chapters) // 2]]
        elif count == 2:
            return [
                available_chapters[len(available_chapters) // 3],
                available_chapters[len(available_chapters) * 2 // 3]
            ]
        else:
            chapters = []
            step = len(available_chapters) / count
            for i in range(count):
                index = min(int(i * step), len(available_chapters) - 1)
                chapters.append(available_chapters[index])
            
            return sorted(chapters)

    def set_custom_ratio(self):
        """设置自定义配比，确保主线占比合理"""
        print("\n📝 自定义配比 (请确保主线占比在60-85%之间)")
        
        while True:
            try:
                main_ratio = float(input("请输入主线比例 (0.6-0.85): "))
                if 0.6 <= main_ratio <= 0.85:
                    break
                else:
                    print("主线比例必须在0.6-0.85之间")
            except ValueError:
                print("请输入有效的数字")
        
        remaining = 1.0 - main_ratio
        print(f"剩余比例: {remaining*100}% 可分配给感情线和伏笔线")
        
        emotional_ratio = 0
        if remaining > 0:
            while True:
                try:
                    emotional_ratio = float(input(f"请输入感情线比例 (0-{remaining}): "))
                    if 0 <= emotional_ratio <= remaining:
                        break
                    else:
                        print(f"感情线比例必须在0-{remaining}之间")
                except ValueError:
                    print("请输入有效的数字")
        
        foreshadowing_ratio = remaining - emotional_ratio
        
        custom_ratio = {
            "main": main_ratio,
            "emotional": emotional_ratio,
            "foreshadowing": foreshadowing_ratio
        }
        
        self.set_subplot_ratio(custom_ratio=custom_ratio)

    def set_subplot_ratio(self, ratio_type: str = "auto", custom_ratio: Dict = None):
        """设置暗线配比"""
        if custom_ratio:
            self.novel_data["subplot_tracking"]["ratio"] = custom_ratio
            ratio = self.novel_data["subplot_tracking"]["ratio"]
            print(f"📊 使用自定义配比: 主线{ratio['main']*100}%, 感情线{ratio['emotional']*100}%, 伏笔线{ratio['foreshadowing']*100}%")
        
        elif ratio_type == "auto":
            genre = self.detect_genre_from_seed(self.novel_data["creative_seed"])
            auto_ratio = self.config["subplot_ratios"]["by_genre"].get(genre, self.config["subplot_ratios"]["by_genre"]["默认"])
            self.novel_data["subplot_tracking"]["ratio"] = auto_ratio
            ratio = self.novel_data["subplot_tracking"]["ratio"]
            print(f"📊 自动检测题材 '{genre}'，设定配比: 主线{ratio['main']*100}%, 感情线{ratio['emotional']*100}%, 伏笔线{ratio['foreshadowing']*100}%")
        
        else:
            preset_ratio = self.config["subplot_ratios"]["presets"].get(ratio_type, self.config["subplot_ratios"]["presets"]["平衡发展"])
            self.novel_data["subplot_tracking"]["ratio"] = preset_ratio
            ratio = self.novel_data["subplot_tracking"]["ratio"]
            print(f"📊 使用预设配比 '{ratio_type}': 主线{ratio['main']*100}%, 感情线{ratio['emotional']*100}%, 伏笔线{ratio['foreshadowing']*100}%")
        
        # 重新初始化暗线计划
        self._initialize_subplot_plan_with_ratio()

    def choose_subplot_ratio(self):
        """让用户选择暗线配比"""
        print("\n  🎯 请选择剧情配比方案 (主线占比60-85%):")
        print("1. 自动配比 (根据题材智能设定)")
        print("2. 情感主导 (主线60%，感情线30%，伏笔线10%)")
        print("3. 悬疑主导 (主线60%，感情线10%，伏笔线30%)") 
        print("4. 平衡发展 (主线70%，感情线15%，伏笔线15%)")
        print("5. 轻度暗线 (主线80%，感情线10%，伏笔线10%)")
        print("6. 主线优先 (主线85%，感情线10%，伏笔线5%)")
        print("7. 推荐配比 (新手作者适用)")
        print("8. 自定义配比")
        
        # 10秒超时自动选择
        choice = self._get_user_choice_with_timeout(
            options=["1", "2", "3", "4", "5", "6", "7", "8"],
            timeout=10,
            default_choice="7",
            prompt="请选择配比方案 (1-8): "
        )
        
        ratio_map = {
            "1": "auto",
            "2": "情感主导", 
            "3": "悬疑主导",
            "4": "平衡发展",
            "5": "轻度暗线",
            "6": "主线优先"
        }
        
        if choice == "7":
            self.set_recommended_ratio("beginner")
        elif choice == "8":
            self.set_custom_ratio()
        else:
            ratio_type = ratio_map.get(choice, "auto")
            self.set_subplot_ratio(ratio_type)

    def detect_genre_from_seed(self, creative_seed: str) -> str:
        """根据创意种子自动检测题材"""
        seed_lower = creative_seed.lower()
        
        genre_keywords = {
            "都市情感": ["都市", "爱情", "婚姻", "恋爱", "职场", "霸总", "追妻"],
            "玄幻修真": ["玄幻", "修真", "修仙", "仙侠", "魔法", "斗气", "飞升"],
            "科幻末世": ["科幻", "末世", "星际", "机甲", "外星", "废土", "丧尸"],
            "历史权谋": ["历史", "权谋", "宫斗", "朝堂", "帝王", "将军", "古代"],
            "悬疑推理": ["悬疑", "推理", "破案", "侦探", "犯罪", "谜案", "解谜"],
            "系统流": ["系统", "加点", "面板", "任务", "奖励", "升级", "兑换"],
            "无限流": ["无限", "主神", "轮回", "副本", "任务世界", "穿越"],
            "穿越重生": ["穿越", "重生", "回到", "转世", "复活", "再来一次"]
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in seed_lower for keyword in keywords):
                return genre
        
        return "默认"
    
    def load_project_data(self, filename: str) -> bool:
        """加载项目数据 - 修复版本：确保所有必要字段都存在"""
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
            
            # 关键修复：确保所有必要字段都存在
            print("🔄 补全缺失字段...")
            
            # 定义必须存在的字段及其默认值
            required_fields = {
                "previous_chapter_endings": {},
                "used_chapter_titles": set(),
                "subplot_tracking": {
                    "foreshadowing_lines": [],
                    "emotional_lines": [],
                    "subplot_chapters": {"foreshadowing": [], "emotional": []},
                    "ratio": {"main": 0.7, "emotional": 0.15, "foreshadowing": 0.15}
                },
                "plot_progression": [],
                "chapter_quality_records": {},
                "optimization_history": {},
                "is_resuming": False,
                "resume_data": None
            }
            
            # 补全缺失字段
            for field, default_value in required_fields.items():
                if field not in data:
                    print(f"  ⚠️  补全缺失字段: {field}")
                    data[field] = default_value
            
            # 关键修复：将数据同步到self.novel_data
            print("🔄 同步数据到self.novel_data...")
            
            import copy
            self.novel_data = copy.deepcopy(data)
            
            # 设置恢复模式标志
            self.novel_data["is_resuming"] = True
            self.novel_data["resume_data"] = copy.deepcopy(data)
            
            # 为了向后兼容，也设置独立的属性
            self.novel_title = self.novel_data["novel_title"]
            self.novel_synopsis = self.novel_data["novel_synopsis"]
            self.creative_seed = self.novel_data.get("creative_seed", "")
            self.selected_plan = self.novel_data.get("selected_plan", {})
            
            # 修复：确保进度信息正确加载
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
            
            # 加载其他数据...
            self.market_analysis = self.novel_data.get("market_analysis", {})
            self.overall_stage_plans = self.novel_data.get("overall_stage_plan", {})
            
            # 修复：确保写作计划正确加载
            self.stage_writing_plans = self.novel_data.get("stage_writing_plans", {})
            print(f"🔍 生成器调试 - 加载的写作计划: {len(self.stage_writing_plans)} 个阶段")
            if self.stage_writing_plans:
                for stage_name, stage_data in self.stage_writing_plans.items():
                    print(f"  - 阶段 '{stage_name}': {len(stage_data)} 个属性")
            
            self.core_worldview = self.novel_data.get("core_worldview", {})
            self.character_design = self.novel_data.get("character_design", {})
            self.generated_chapters = self.novel_data.get("generated_chapters", {})
            self.plot_progression = self.novel_data.get("plot_progression", [])
            self.subplot_tracking = self.novel_data.get("subplot_tracking", {
                "ratio": {"emotional": 0.3, "foreshadowing": 0.3},
                "subplot_chapters": {"emotional": [], "foreshadowing": []}
            })
            self.quality_statistics = self.novel_data.get("quality_statistics", {})
            
            # 修复：初始化阶段计划管理器
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
        """初始化阶段计划管理器 - 修复版本"""
        try:
            # 如果有写作计划，初始化阶段计划管理器
            if self.stage_writing_plans:
                # 获取当前阶段
                current_stage = self.current_progress.get("current_stage", "opening_stage")
                
                # 打印所有可用阶段
                available_stages = list(self.stage_writing_plans.keys())
                print(f"📋 可用写作阶段: {available_stages}")
                
                # 如果指定的阶段不存在，使用第一个可用阶段
                if current_stage not in self.stage_writing_plans:
                    current_stage = available_stages[0]
                    print(f"⚠️ 指定阶段 '{self.current_progress.get('current_stage')}' 不存在，使用第一个可用阶段: {current_stage}")
                
                # 初始化阶段计划管理器
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
        
        # 步骤1: 用户输入
        self._get_user_inputs()
        
        # 步骤2: 生成三套方案并选择
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
            print("⚠️  全局成长规划生成失败，使用基础规划")
        
        # 步骤8: 初始化系统
        self.novel_data["current_progress"]["stage"] = "系统初始化"
        self._initialize_systems()
        
        # ==================== 第四阶段：内容生成准备 ====================
        print("\n" + "="*60)
        print("🛠️ 第四阶段：内容生成准备")
        print("="*60)
        
        # 步骤9: 选择剧情配比
        self.novel_data["current_progress"]["stage"] = "配比选择"
        self.choose_subplot_ratio()
        
        # 步骤10: 创建项目目录和保存初始进度
        self.novel_data["current_progress"]["stage"] = "项目初始化"
        self._initialize_project()
        
        # ==================== 第五阶段：章节内容生成 ====================
        return self._generate_all_chapters(total_chapters)

    def _get_user_inputs(self):
        """获取用户输入"""
        # 询问主角名字
        main_character_name = input("请输入主角名字（直接回车使用自动生成）: ").strip()
        if main_character_name:
            print(f"✓ 使用自定义主角名字: {main_character_name}")
            self.novel_data["custom_main_character_name"] = main_character_name
            self.content_generator.set_custom_main_character_name(main_character_name)
        
        # 选择分类
        self.choose_category()

    def _generate_and_select_plan(self, creative_seed: str) -> bool:
        """生成并选择方案"""
        print("=== 步骤1: 基于番茄小说流量趋势生成三套方案 ===")
        
        plans_data = self.content_generator.generate_three_plans(creative_seed)
        if not plans_data:
            print("❌ 方案生成失败，终止生成")
            return False
        
        self.novel_data["selected_plan"] = self.present_plans_to_user(plans_data)
        if not self.novel_data["selected_plan"]:
            print("❌ 用户未选择方案，终止生成")
            return False
        
        # 设置选定方案的小说标题和简介
        self.novel_data["novel_title"] = self.novel_data["selected_plan"]["title"]
        self.novel_data["novel_synopsis"] = self.novel_data["selected_plan"]["synopsis"]
        
        print(f"✅ 已选择方案: 《{self.novel_data['novel_title']}》")
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
            self.novel_data.get("market_analysis", {}),
            self.novel_data.get("custom_main_character_name")
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
        """生成全局成长规划"""
        print("=== 步骤6: 制定全书成长规划 ===")
        
        # 如果有全局成长规划器，使用它
        if hasattr(self, 'global_growth_planner'):
            try:
                self.novel_data["global_growth_plan"] = self.global_growth_planner.create_comprehensive_growth_plan(
                    creative_seed,
                    self.novel_data["novel_title"],
                    self.novel_data["novel_synopsis"],
                    total_chapters
                )
                
                if self.novel_data["global_growth_plan"]:
                    print("✅ 全书成长规划制定完成")
                    return True
            except Exception as e:
                print(f"⚠️  全局成长规划器出错: {e}，使用独立系统")
        
        # 如果没有全局成长规划器或出错，使用独立的系统（向后兼容）
        print("⚠️  使用独立成长系统（兼容模式）")
        
        success = True
        
        # 人物成长设计
        if hasattr(self, 'character_growth_manager'):
            try:
                self.novel_data["character_growth"] = self.character_growth_manager.design_main_character_growth(
                    self.novel_data["character_design"],
                    total_chapters
                )
                print("✅ 人物成长设计完成")
            except Exception as e:
                print(f"❌ 人物成长设计失败: {e}")
                success = False
        
        # 势力发展设计
        if hasattr(self, 'faction_development_manager'):
            try:
                self.novel_data["faction_development"] = self.faction_development_manager.initialize_faction_system(
                    self.novel_data["core_worldview"]
                )
                print("✅ 势力发展设计完成")
            except Exception as e:
                print(f"❌ 势力发展设计失败: {e}")
                success = False
        
        # 物品升级系统
        if hasattr(self, 'item_upgrade_system'):
            try:
                self.novel_data["upgrade_system"] = self.item_upgrade_system.create_upgrade_system(
                    self.novel_data["core_worldview"]
                )
                print("✅ 物品升级系统设计完成")
            except Exception as e:
                print(f"❌ 物品升级系统设计失败: {e}")
                success = False
        
        return success

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
        self.print_generation_summary()
        return True
        
    def print_generation_summary(self):
        """打印生成摘要"""
        print("\n" + "="*60)
        print("🎊 小说生成完成摘要")
        print("="*60)
        
        print(f"📖 小说标题: {self.novel_data['novel_title']}")
        print(f"📚 小说分类: {self.novel_data.get('category', '未分类')}") 
        print(f"📝 总章节数: {self.novel_data['current_progress']['completed_chapters']}/{self.novel_data['current_progress']['total_chapters']}")
        
        # 添加主角名字验证
        self.validate_main_character_usage()
        
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
        
        # 询问是否显示详细质量报告
        show_quality_report = input("\n是否显示详细质量评估报告？(y/n): ").lower() == 'y'
        if show_quality_report:
            self.print_quality_report()

    def validate_main_character_usage(self):
        """验证主角名字在所有内容中的使用情况"""
        custom_name = self.novel_data.get("custom_main_character_name")
        if not custom_name:
            print("未设置自定义主角名字，跳过验证")
            return
        
        print(f"\n🔍 验证主角名字 '{custom_name}' 的使用情况:")
        
        # 检查选定方案
        selected_plan = self.novel_data.get("selected_plan")
        if selected_plan:
            title_usage = custom_name in selected_plan.get("title", "")
            synopsis_usage = custom_name in selected_plan.get("synopsis", "")
            print(f"  方案: 标题中{'✓' if title_usage else '✗'} | 简介中{'✓' if synopsis_usage else '✗'}")
        
        # 检查写作计划
        overall_stage_plan = self.novel_data.get("overall_stage_plan")
        if overall_stage_plan:
            plan_usage = any(
                custom_name in str(value) 
                for value in overall_stage_plan.values() 
                if isinstance(value, str)
            )
            print(f"  写作计划: {'✓' if plan_usage else '✗'}")
        
        # 检查角色设计
        character_design = self.novel_data.get("character_design")
        if character_design:
            main_char = character_design.get("main_character", {})
            name_correct = main_char.get("name") == custom_name
            print(f"  角色设计: {'✓' if name_correct else '✗'} (主角名字: {main_char.get('name', '未设置')})")
        
        # 检查已生成章节
        generated_chapters = self.novel_data.get("generated_chapters", {})
        if generated_chapters:
            chapters_with_name = sum(1 for chapter_data in generated_chapters.values() 
                                   if custom_name in chapter_data.get("content", ""))
            print(f"  章节内容: {chapters_with_name}/{len(generated_chapters)} 章使用了主角名字")
        
        print("验证完成")          

    def print_foundation_quality_report(self):
        """打印基础内容质量报告"""
        print("\n" + "="*60)
        print("🏗️  基础内容质量报告")
        print("="*60)
        
        foundation_contents = {
            "市场分析": self.novel_data.get("market_analysis"),
            "写作计划": self.novel_data.get("stage_writing_plan"), 
            "世界观": self.novel_data.get("core_worldview"),
            "角色设计": self.novel_data.get("character_design")
        }
        
        for name, content in foundation_contents.items():
            if content:
                completeness = self._assess_foundation_completeness(content, name)
                print(f"📊 {name}: {completeness}")
            else:
                print(f"❌ {name}: 缺失")
        
        print("="*60)      

    def _assess_foundation_completeness(self, content: Dict, content_type: str) -> str:
        """评估基础内容的完整性"""
        if not content:
            return "无内容"
        
        required_fields = {
            "市场分析": ["target_audience", "core_selling_points", "market_trend_analysis"],
            "写作计划": ["writing_approach", "chapter_rhythm", "key_plot_points"],
            "世界观": ["era", "core_conflict", "overview", "power_system"],
            "角色设计": ["main_character", "important_characters"]
        }
        
        fields = required_fields.get(content_type, [])
        missing_fields = [field for field in fields if not self._get_nested_value(content, field)]
        
        return "基本完整 (缺失: {})".format(", ".join(missing_fields)) if missing_fields else "完整"
    
    def _get_nested_value(self, obj, key_path):
        """获取嵌套字典的值"""
        if isinstance(key_path, str):
            return obj.get(key_path)
        
        current = obj
        for key in key_path.split('.'):
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current    
    
    def ensure_stage_plan_for_chapter(self, chapter_number: int):
        """确保为当前章节所属阶段生成详细写作计划"""
        try:
            print(f"  🔍 确保第{chapter_number}章有阶段计划...")
            
            # 记录阶段转换
            self.log_stage_transition(chapter_number)
            
            # 检查并生成新的阶段计划
            stage_plan = self.check_and_generate_new_stage_plan(chapter_number)
            
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

    def print_quality_report(self):
        """打印质量报告"""
        if not self.novel_data["chapter_quality_records"]:
            print("暂无质量评估数据")
            return
        
        stats = self.project_manager.calculate_quality_statistics(self.novel_data)
        
        print("\n" + "="*60)
        print("📊 章节质量评估报告")
        print("="*60)
        
        print(f"📈 总体质量统计:")
        print(f"   评估章节数: {stats['total_chapters_assessed']}")
        print(f"   平均评分: {stats['average_score']:.1f}/10分")
        print(f"   最高分: {stats['max_score']:.1f}分")
        print(f"   最低分: {stats['min_score']:.1f}分")
        print(f"   优化章节: {stats['optimized_chapters']}章 ({stats['optimization_rate']}%)")
        
        print(f"\n🎯 质量分布:")
        distribution = stats.get('quality_distribution', {})
        for level, count in distribution.items():
            percentage = (count / stats['total_chapters_assessed']) * 100 if stats['total_chapters_assessed'] > 0 else 0
            print(f"   {level}: {count}章 ({percentage:.1f}%)")
        
        print(f"\n🤖 AI痕迹检测统计:")
        ai_stats = stats.get('ai_quality', {})
        print(f"   平均AI痕迹得分: {ai_stats.get('average_ai_score', 2):.1f}/2分")
        print(f"   存在AI痕迹的章节: {ai_stats.get('chapters_with_ai_artifacts', 0)}章")
        
        ai_distribution = ai_stats.get('ai_distribution', {})
        for level, count in ai_distribution.items():
            percentage = (count / stats['total_chapters_assessed']) * 100 if stats['total_chapters_assessed'] > 0 else 0
            print(f"   {level}: {count}章 ({percentage:.1f}%)")
        
        print(f"\n🔍 详细评分分析:")
        detailed_scores = stats.get('average_detailed_scores', {})
        for aspect, score in detailed_scores.items():
            aspect_name = {
                'plot_coherence': '情节连贯性',
                'character_consistency': '角色一致性', 
                'chapter_connection': '章节衔接',
                'writing_quality': '文笔质量',
                'ai_artifacts_detected': 'AI痕迹检测',
                'emotional_impact': '爽点设置'
            }.get(aspect, aspect)
            print(f"   {aspect_name}: {score:.1f}/2分")
        
        # 显示需要重点关注的章节
        low_quality_chapters = []
        high_ai_chapters = []
        
        for chap_num, record in self.novel_data["chapter_quality_records"].items():
            score = record.get('assessment', {}).get('overall_score', 0)
            ai_score = record.get('assessment', {}).get('detailed_scores', {}).get('ai_artifacts_detected', 2)
            
            if score < self.config["quality_thresholds"]["acceptable"]:
                low_quality_chapters.append((chap_num, score))
            
            if ai_score < 1.5:  # AI痕迹较明显
                high_ai_chapters.append((chap_num, ai_score))
        
        if low_quality_chapters:
            print(f"\n⚠️  需要关注的章节 (评分低于8分):")
            for chap_num, score in sorted(low_quality_chapters, key=lambda x: x[1]):
                print(f"   第{chap_num}章: {score:.1f}分")
        
        if high_ai_chapters:
            print(f"\n🤖 AI痕迹较明显的章节:")
            for chap_num, ai_score in sorted(high_ai_chapters, key=lambda x: x[1]):
                print(f"   第{chap_num}章: AI痕迹得分{ai_score:.1f}/2分")
        
        print("="*60)

    def check_and_generate_new_stage_plan(self, chapter_number: int):
        """检查是否需要为当前章节生成新的阶段详细计划"""
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

    def get_stage_boundary_info(self) -> Dict:
        """获取阶段边界信息"""
        if hasattr(self.stage_plan_manager, 'stage_boundaries'):
            return {
                "stage_boundaries": self.stage_plan_manager.stage_boundaries,
                "current_stage_plan": self.stage_plan_manager.overall_stage_plans
            }
        return {"stage_boundaries": {}, "current_stage_plan": {}}

    def log_stage_transition(self, chapter_number: int):
        """记录阶段转换信息"""
        current_stage = self.stage_plan_manager.get_current_stage(chapter_number)
        prev_stage = self.stage_plan_manager.get_current_stage(chapter_number - 1) if chapter_number > 1 else None
        
        if prev_stage != current_stage:
            print(f"🎯 阶段转换: 第{chapter_number}章从 '{prev_stage}' 进入 '{current_stage}'")
            
            # 显示阶段边界信息
            boundaries = self.get_stage_boundary_info()
            print(f"  阶段边界: {boundaries['stage_boundaries']}")