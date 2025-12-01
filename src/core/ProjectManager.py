"""项目管理器类 - 专注项目管理"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import os
import json
import re
from datetime import datetime
import shutil
from typing import List, Dict, Optional
from src.utils.logger import get_logger
from src.utils.seed_utils import ensure_seed_dict
class ProjectManager:
    def __init__(self):
        self.logger = get_logger("ProjectManager")
        # 内化质量阈值配置
        self.quality_thresholds = {
            "excellent": 9.0,
            "good": 8.5,
            "acceptable": 8.0,
            "needs_optimization": 7.5,
            "needs_rewrite": 6.0
        }
        # 其他相关配置
        self.optimization_settings = {
            "quality_thresholds": self.quality_thresholds
        }
    # vvv 2. 在类的末尾添加下面的新方法 vvv
    def copy_project_to_directory(self, novel_title: str, target_directory: str):
        """将指定的小说项目文件完整复制到目标目录。"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            source_dir = "data/projects"
            # 检查源目录
            if not os.path.exists(source_dir):
                self.logger.info(f"❌ 源目录 '{source_dir}' 不存在，无法复制。")
                return False
            # 确保目标目录存在
            os.makedirs(target_directory, exist_ok=True)
            # 查找所有与该小说相关的文件和目录
            project_files_to_copy = []
            for item_name in os.listdir(source_dir):
                if safe_title in item_name:
                    project_files_to_copy.append(item_name)
            if not project_files_to_copy:
                self.logger.info(f"🤔 在源目录中未找到与 '{novel_title}' 相关的文件。")
                return False
            self.logger.info(f"找到 {len(project_files_to_copy)} 个相关文件/目录准备复制...")
            copied_count = 0
            for item_name in project_files_to_copy:
                source_path = os.path.join(source_dir, item_name)
                target_path = os.path.join(target_directory, item_name)
                try:
                    if os.path.isdir(source_path):
                        # 如果目标目录已存在，先删除再复制，以确保是最新内容
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(source_path, target_path)
                    else:
                        shutil.copy2(source_path, target_path) # copy2 保留元数据
                    self.logger.info(f"  - ✅ 已复制: {item_name}")
                    copied_count += 1
                except Exception as e:
                    self.logger.info(f"  - ❌ 复制 '{item_name}' 失败: {e}")
            # 记录复制操作
            if copied_count > 0:
                log_file = os.path.join(target_directory, "复制记录.txt")
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - 复制小说项目: {novel_title} (共 {copied_count} 个文件/目录)\n")
                self.logger.info(f"🎯 项目复制完成！共 {copied_count} 个文件/目录已复制到: {target_directory}")
            else:
                self.logger.info("⚠️ 没有文件被成功复制。")
            return copied_count > 0
        except Exception as e:
            self.logger.info(f"❌ 复制项目时发生严重错误: {e}")
            return False
    # ^^^ 以上是新添加的方法 ^^^
    def find_existing_projects(self, creative_seed: str = None) -> List[Dict]:
        """查找现有项目"""
        projects = []
        if not os.path.exists("小说项目/"):
            return projects
        # 确保 creative_seed 是字符串
        if creative_seed is None:
            safe_seed = ""
        elif isinstance(creative_seed, dict):
            # 如果是字典，提取核心设定
            safe_seed = creative_seed.get('coreSetting', '')[:50]
        else:
            safe_seed = str(creative_seed)[:50]
        # 安全处理字符串
        safe_seed = re.sub(r'[\\/*?:"<>|]', "_", safe_seed) if safe_seed else ""
        for filename in os.listdir("小说项目/"):
            if filename.endswith("_项目信息.json"):
                try:
                    with open(f"小说项目/{filename}", 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    project_seed = data.get("novel_info", {}).get("creative_seed", "")
                    # normalize loaded project seed to dict
                    project_seed = ensure_seed_dict(project_seed)
                    project_title = data.get("novel_info", {}).get("title", "")
                    progress = data.get("progress", {})
                    # 如果提供了creative_seed，只匹配相关项目
                    # normalize input creative_seed for comparison
                    try:
                        input_seed_norm = ensure_seed_dict(creative_seed) if creative_seed is not None else {}
                    except Exception:
                        input_seed_norm = {}
                    if creative_seed and safe_seed not in filename and input_seed_norm != project_seed:
                        continue
                    projects.append({
                        "filename": filename,
                        "title": project_title,
                        "seed": project_seed,
                        "completed_chapters": progress.get("completed_chapters", 0),
                        "total_chapters": progress.get("total_chapters", 0),
                        "stage": progress.get("stage", "未知"),
                        "timestamp": data.get("timestamp", "")
                    })
                except Exception as e:
                    self.logger.info(f"读取项目文件 {filename} 失败: {e}")
        # 按时间倒序排序
        projects.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return projects
    def load_project(self, filename: str) -> Optional[Dict]:
        """加载项目数据"""
        try:
            with open(f"小说项目/{filename}", 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            # 构建完整的novel_data结构
            novel_data = {
                # 基本信息
                "novel_title": project_data["novel_info"]["title"],
                "novel_synopsis": project_data["novel_info"]["synopsis"],
                "creative_seed": ensure_seed_dict(project_data["novel_info"].get("creative_seed", {})),
                "selected_plan": project_data["novel_info"]["selected_plan"],
                "category": project_data["novel_info"].get("category", "未分类"),
                # 新增：添加novel_info键以保持兼容性
                "novel_info": project_data["novel_info"],
                # 核心数据
                "market_analysis": project_data.get("market_analysis", {}),
                "global_growth_plan": project_data.get("global_growth_plan", {}),
                "overall_stage_plans": project_data.get("overall_stage_plans", {}),
                "stage_writing_plans": project_data.get("stage_writing_plans", {}),
                "core_worldview": project_data.get("core_worldview", {}),
                "character_design": project_data.get("character_design", {}),
                # 修复：正确加载进度信息
                "current_progress": project_data.get("progress", {
                    "completed_chapters": 0,
                    "total_chapters": 0,
                    "stage": "大纲阶段",
                    "current_stage": "第一阶段"
                }),
                # 初始化其他必要字段
                "generated_chapters": {},
                "plot_progression": project_data.get("plot_progression", []),
                "subplot_tracking": project_data.get("subplot_settings", {
                    "ratio": {"emotional": 0.3, "foreshadowing": 0.3},
                    "subplot_chapters": {"emotional": [], "foreshadowing": []}
                }),
                "quality_statistics": project_data.get("quality_statistics", {})
            }
            # 加载章节具体内容
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data["novel_title"])
            chapters_dir = f"小说项目/{safe_title}_章节"
            if os.path.exists(chapters_dir):
                generated_chapters = {}
                for chapter_file in os.listdir(chapters_dir):
                    if chapter_file.endswith('.txt'):
                        try:
                            with open(f"{chapters_dir}/{chapter_file}", 'r', encoding='utf-8') as f:
                                chapter_data = json.load(f)
                                chapter_num = chapter_data.get("chapter_number")
                                if chapter_num:
                                    # 确保 chapter_num 是字符串以保持键的一致性
                                    chapter_num_key = str(chapter_num)
                                    generated_chapters[chapter_num_key] = {
                                        "chapter_title": chapter_data.get("chapter_title", ""),
                                        "content": chapter_data.get("content", ""),
                                        "word_count": chapter_data.get("word_count", 0),
                                        "quality_assessment": chapter_data.get("quality_assessment", {}),
                                        "optimization_info": chapter_data.get("optimization_info", {}),
                                        "chapter_design": chapter_data.get("chapter_design", {}),
                                        "design_followed": chapter_data.get("design_followed", True),
                                        "base_settings_used": chapter_data.get("base_settings_used", {}),
                                        "key_events": chapter_data.get("key_events", []),
                                        "next_chapter_hook": chapter_data.get("next_chapter_hook", ""),
                                        "connection_to_previous": chapter_data.get("connection_to_previous", ""),
                                        "plot_advancement": chapter_data.get("plot_advancement", ""),
                                        "character_development": chapter_data.get("character_development", ""),
                                        "quality_score": chapter_data.get("quality_score", 0),
                                        "previous_chapter_summary": chapter_data.get("previous_chapter_summary", "")
                                    }
                        except Exception as e:
                            self.logger.info(f"加载章节文件 {chapter_file} 失败: {e}")
                novel_data["generated_chapters"] = generated_chapters
                # 修复：如果进度信息中章节数为0，但实际有章节，则更新进度
                if novel_data["current_progress"]["total_chapters"] == 0 and generated_chapters:
                    novel_data["current_progress"]["total_chapters"] = max(generated_chapters.keys())
                    novel_data["current_progress"]["completed_chapters"] = len(generated_chapters)
                    novel_data["current_progress"]["stage"] = "写作中"
                    self.logger.info(f"🔄 自动修复进度信息: {len(generated_chapters)}/{max(generated_chapters.keys())}章")
            # 确保嵌套的 novel_info 中的 creative_seed 也被正规化为 dict
            try:
                if "novel_info" in novel_data:
                    novel_data["novel_info"]["creative_seed"] = ensure_seed_dict(novel_data["novel_info"].get("creative_seed", {}))
                    # 同步顶层 creative_seed
                    novel_data["creative_seed"] = novel_data["novel_info"]["creative_seed"]
            except Exception:
                pass
            self.logger.info(f"✓ 项目加载成功: {novel_data['novel_title']}")
            self.logger.info(f"  - 世界观数据: {len(novel_data['core_worldview'])} 项")
            self.logger.info(f"  - 角色设定: {len(novel_data['character_design'])} 个角色")
            self.logger.info(f"  - 写作计划: {len(novel_data['stage_writing_plans'])} 个阶段")
            self.logger.info(f"  - 已生成章节: {len(novel_data['generated_chapters'])} 章")
            self.logger.info(f"  - 当前进度: {novel_data['current_progress']['completed_chapters']}/{novel_data['current_progress']['total_chapters']}章")
            self.logger.info(f"  - 当前阶段: {novel_data['current_progress']['stage']}")
            return novel_data
        except Exception as e:
            self.logger.info(f"❌❌ 加载项目失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    def save_single_chapter(self, novel_title: str, chapter_number: int, chapter_data: Dict):
        """保存单章内容"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        chapter_dir = f"小说项目/{safe_title}_章节"
        os.makedirs(chapter_dir, exist_ok=True)
        # 提取所有章节特定的信息
        chapter_json_data = {
            "chapter_number": chapter_number,
            "chapter_title": chapter_data["chapter_title"],
            "content": chapter_data["content"],
            "word_count": chapter_data.get("word_count", 0),
            "quality_assessment": chapter_data.get("quality_assessment", {}),
            "optimization_info": chapter_data.get("optimization_info", {}),
            "chapter_design": chapter_data.get("chapter_design", {}),
            "design_followed": chapter_data.get("design_followed", True),
            "base_settings_used": chapter_data.get("base_settings_used", {}),
            "generation_time": datetime.now().isoformat(),
            # 章节特定的信息
            "key_events": chapter_data.get("key_events", []),
            "next_chapter_hook": chapter_data.get("next_chapter_hook", ""),
            "connection_to_previous": chapter_data.get("connection_to_previous", ""),
            "plot_advancement": chapter_data.get("plot_advancement", ""),
            "character_development": chapter_data.get("character_development", ""),
            # 质量评分
            "quality_score": chapter_data.get("quality_assessment", {}).get("overall_score", 0),
            # 衔接信息
            "previous_chapter_summary": chapter_data.get("previous_chapters_summary", ""),
        }
        try:
            filename = f"{chapter_dir}/第{chapter_number:03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', chapter_data['chapter_title'])}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(chapter_json_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"  已保存: {filename}")
        except Exception as e:
            self.logger.info(f"保存第{chapter_number}章失败: {e}")
    def save_project_progress(self, novel_data: Dict):
        """保存项目整体进度"""
        # 防御式编程：如果 novel_title 缺失，使用默认值
        novel_title = novel_data.get("novel_title", "未定稿创意")
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        os.makedirs("小说项目/", exist_ok=True)
        # 确保 creative_seed 被保存为 dict（防止字符串持久化）
        normalized_creative_seed = ensure_seed_dict(novel_data.get("creative_seed", {}))
        # 计算质量统计
        quality_stats = self.calculate_quality_statistics(novel_data)
        # 确保进度信息存在
        current_progress = novel_data.get("current_progress", {
            "completed_chapters": 0,
            "total_chapters": 0,
            "stage": "大纲阶段",
            "current_stage": "第一阶段"
        })
        # 如果有章节但进度信息不正确，自动修复
        generated_chapters = novel_data.get("generated_chapters", {})
        if generated_chapters:
            if current_progress["total_chapters"] == 0:
                current_progress["total_chapters"] = max(generated_chapters.keys())
            if current_progress["completed_chapters"] == 0:
                current_progress["completed_chapters"] = len(generated_chapters)
            if current_progress["stage"] == "未开始" or current_progress["stage"] == "大纲阶段":
                current_progress["stage"] = "写作中"
        # 构建完整的项目数据
        data = {
            "novel_info": {
                "title": novel_data["novel_title"],
                "synopsis": novel_data["novel_synopsis"],
                "creative_seed": normalized_creative_seed,
                "selected_plan": novel_data["selected_plan"],
                "category": novel_data.get("category", "未分类") 
            },
            # 核心数据
            "market_analysis": novel_data.get("market_analysis", {}),
            "global_growth_plan": novel_data.get("global_growth_plan", {}),
            "overall_stage_plans": novel_data.get("overall_stage_plans", {}),
            "stage_writing_plans": novel_data.get("stage_writing_plans", {}),
            "core_worldview": novel_data.get("core_worldview", {}),
            "character_design": novel_data.get("character_design", {}),
            # 修复：使用正确的进度信息
            "progress": current_progress,
            # 其他数据...
            "chapter_index": [
                {
                    "chapter_number": chapter_num,
                    "chapter_title": chapter_data["chapter_title"],
                    "filename": f"第{int(chapter_num):03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', chapter_data['chapter_title'])}.txt",
                    "quality_score": chapter_data.get("quality_assessment", {}).get("overall_score", 0),
                    "word_count": chapter_data.get("word_count", 0)
                }
                for chapter_num, chapter_data in sorted(generated_chapters.items(), key=lambda x: int(x[0]))
            ],
            "quality_statistics": quality_stats,
            "plot_progression": novel_data.get("plot_progression", []),
            "subplot_settings": {
                "ratio": novel_data.get("subplot_tracking", {}).get("ratio", {"emotional": 0.3, "foreshadowing": 0.3}),
                "subplot_chapters": novel_data.get("subplot_tracking", {}).get("subplot_chapters", {"emotional": [], "foreshadowing": []})
            },
            "timestamp": datetime.now().isoformat(),
            "file_structure": {
                "chapters_directory": f"{safe_title}_章节",
                "total_chapters": len(generated_chapters)
            },
            "category_info": {
                "name": novel_data.get("category", "未分类"),
                "subplot_ratio": novel_data.get("subplot_tracking", {}).get("ratio", {"main": 0.7, "emotional": 0.2, "foreshadowing": 0.1})
            }
        }
        try:
            with open(f"小说项目/{safe_title}_项目信息.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"✓ 项目进度已保存: 小说项目/{safe_title}_项目信息.json")
            self.logger.info(f"  - 进度信息: {current_progress['completed_chapters']}/{current_progress['total_chapters']}章")
            self.logger.info(f"  - 当前阶段: {current_progress['stage']}")
        except Exception as e:
            self.logger.info(f"保存项目信息文件失败: {e}")
    def calculate_quality_statistics(self, novel_data: Dict) -> Dict:
        """计算质量统计信息"""
        generated_chapters = novel_data.get("generated_chapters", {})
        if not generated_chapters:
            return {}
        scores = []
        optimized_count = 0
        ai_scores = []
        detailed_scores = {
            "plot_coherence": [],
            "character_consistency": [],
            "chapter_connection": [],
            "writing_quality": [],
            "ai_artifacts_detected": [],
            "emotional_impact": []
        }
        for chapter_num, chapter_data in generated_chapters.items():
            assessment = chapter_data.get("quality_assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            # 收集详细分数
            detailed = assessment.get("detailed_scores", {})
            for key in detailed_scores.keys():
                if key in detailed:
                    detailed_scores[key].append(detailed[key])
            # 特别收集AI痕迹分数
            ai_score = detailed.get('ai_artifacts_detected', 2)
            ai_scores.append(ai_score)
            # 统计优化章节
            if chapter_data.get("optimization_info", {}).get("optimized", False):
                optimized_count += 1
        if not scores:
            return {}
        # 计算统计信息
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 2
        # 使用内化的质量阈值
        quality_thresholds = self.quality_thresholds
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= quality_thresholds["excellent"]]),
            "良好": len([s for s in scores if quality_thresholds["good"] <= s < quality_thresholds["excellent"]]),
            "合格": len([s for s in scores if quality_thresholds["acceptable"] <= s < quality_thresholds["good"]]),
            "需要优化": len([s for s in scores if s < quality_thresholds["acceptable"]])
        }
        # 计算AI痕迹分布
        ai_distribution = {
            "优秀(2分)": len([s for s in ai_scores if s == 2]),
            "良好(1.5-2分)": len([s for s in ai_scores if 1.5 <= s < 2]),
            "需改进(1-1.5分)": len([s for s in ai_scores if 1 <= s < 1.5]),
            "较差(<1分)": len([s for s in ai_scores if s < 1])
        }
        # 计算详细分数平均值
        avg_detailed_scores = {}
        for key, values in detailed_scores.items():
            if values:
                avg_detailed_scores[key] = round(sum(values) / len(values), 2)
        return {
            "total_chapters_assessed": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "optimized_chapters": optimized_count,
            "optimization_rate": round(optimized_count / len(scores) * 100, 1) if scores else 0,
            "quality_distribution": quality_distribution,
            "average_detailed_scores": avg_detailed_scores,
            "ai_quality": {
                "average_ai_score": round(avg_ai_score, 2),
                "ai_distribution": ai_distribution,
                "chapters_with_ai_artifacts": len([s for s in ai_scores if s < 2])
            },
            "last_assessment_time": datetime.now().isoformat()
        }
    def export_novel_overview(self, novel_data: Dict):
        """导出小说总览文件"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_data.get("novel_title", "未命名小说"))
        # 获取当前进度信息，提供默认值
        current_progress = novel_data.get("current_progress", {})
        generated_chapters = novel_data.get("generated_chapters", {})
        overview_data = {
            "novel_overview": {
                "title": novel_data.get("novel_title", "未命名小说"),
                "synopsis": novel_data.get("novel_synopsis", ""),
                "total_chapters": current_progress.get("total_chapters", 0),
                "completed_chapters": current_progress.get("completed_chapters", 0),
                "total_word_count": sum(
                    chapter.get('word_count', 0)
                    for chapter in generated_chapters.values()
                ),
                "selected_plan": novel_data.get("selected_plan", ""),
                "creative_seed": novel_data.get("creative_seed", {})
            },
            "worldview_summary": novel_data.get("core_worldview", {}),
            "character_summary": novel_data.get("character_design", {}),
            "writing_plan_summary": {
                "total_stages": len(novel_data.get("stage_writing_plans", {})),
                "current_stage": current_progress.get("current_stage", "第一阶段")
            },
            "chapters_index": [
                {
                    "chapter_number": num,
                    "chapter_title": data.get("chapter_title", ""),
                    "word_count": data.get("word_count", 0),
                    "plot_advancement": data.get("plot_advancement", ""),
                    "next_chapter_hook": data.get("next_chapter_hook", ""),
                    "quality_score": data.get("quality_assessment", {}).get("overall_score", 0),
                    "ai_score": data.get("quality_assessment", {}).get("detailed_scores", {}).get("ai_artifacts_detected", 2),
                    "was_optimized": data.get("optimization_info", {}).get("optimized", False),
                    "filename": f"第{int(num):03d}章_{re.sub(r'[\\/*?:\"<>|]', '_', data.get('chapter_title', '未命名'))}.txt"
                }
                for num, data in sorted(generated_chapters.items(), key=lambda x: int(x[0]))
            ],
            "generation_info": {
                "start_time": current_progress.get("start_time"),
                "completion_time": datetime.now().isoformat(),
                "creative_seed": novel_data.get("creative_seed", {})
            }
        }
        try:
            os.makedirs("小说项目", exist_ok=True)
            with open(f"小说项目/{safe_title}_章节总览.json", 'w', encoding='utf-8') as f:
                json.dump(overview_data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"章节总览已导出到: 小说项目/{safe_title}_章节总览.json")
        except Exception as e:
            self.logger.info(f"导出章节总览失败: {e}")
    def save_element_timing_plan(self, novel_title: str, timing_plan: Dict):
        """保存元素登场时机规划"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            file_path = f"小说项目/{safe_title}_元素登场时机.json"
            # 确保目录存在
            os.makedirs("小说项目/", exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(timing_plan, f, ensure_ascii=False, indent=2)
            self.logger.info(f"✅ 元素登场时机规划已保存: {file_path}")
            return True
        except Exception as e:
            self.logger.info(f"❌ 保存元素登场时机规划失败: {e}")
            return False
    def load_element_timing_plan(self, novel_title: str) -> Dict:
        """加载元素登场时机规划"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            file_path = f"小说项目/{safe_title}_元素登场时机.json"
            if not os.path.exists(file_path):
                return {}
            with open(file_path, 'r', encoding='utf-8') as f:
                timing_plan = json.load(f)
            self.logger.info(f"✅ 元素登场时机规划已加载: {file_path}")
            return timing_plan
        except Exception as e:
            self.logger.info(f"❌ 加载元素登场时机规划失败: {e}")
            return {}
    def save_element_introduction_schedule(self, novel_title: str, schedule: Dict, chapter_range: str):
        """保存章节元素引入计划"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            file_path = f"小说项目/{safe_title}_元素引入计划.json"
            # 加载现有计划或创建新的
            existing_schedule = self.load_element_introduction_schedule(novel_title)
            # 更新指定章节范围的计划
            existing_schedule[chapter_range] = schedule
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_schedule, f, ensure_ascii=False, indent=2)
            self.logger.info(f"✅ 元素引入计划已保存: {chapter_range}")
            return True
        except Exception as e:
            self.logger.info(f"❌ 保存元素引入计划失败: {e}")
            return False
    def load_element_introduction_schedule(self, novel_title: str) -> Dict:
        """加载元素引入计划"""
        try:
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            file_path = f"小说项目/{safe_title}_元素引入计划.json"
            if not os.path.exists(file_path):
                return {}
            with open(file_path, 'r', encoding='utf-8') as f:
                schedule = json.load(f)
            return schedule
        except Exception as e:
            self.logger.info(f"❌ 加载元素引入计划失败: {e}")
            return {}    
    def get_actual_chapter_files(self, novel_title: str) -> Dict:
        """获取实际的章节文件信息"""
        safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
        chapters_dir = f"小说项目/{safe_title}_章节"
        result = {
            "total_files": 0,
            "existing_chapters": [],
            "missing_chapters": [],
            "chapter_files": {}
        }
        if not os.path.exists(chapters_dir):
            return result
        # 收集所有章节文件
        existing_chapters = set()
        for filename in os.listdir(chapters_dir):
            if filename.endswith('.txt'):
                match = re.search(r'第(\d+)章', filename)
                if match:
                    chapter_num = int(match.group(1))
                    existing_chapters.add(chapter_num)
                    result["chapter_files"][chapter_num] = filename
        result["total_files"] = len(existing_chapters)
        result["existing_chapters"] = sorted(existing_chapters)
        return result
    def validate_chapter_integrity(self, novel_data: Dict) -> Dict:
        """验证章节完整性，返回详细的完整性报告"""
        novel_title = novel_data["novel_title"]
        total_chapters = novel_data["current_progress"]["total_chapters"]
        # 获取实际文件信息
        file_info = self.get_actual_chapter_files(novel_title)
        # 计算缺失章节
        expected_chapters = set(range(1, total_chapters + 1))
        existing_chapters = set(file_info["existing_chapters"])
        missing_chapters = sorted(expected_chapters - existing_chapters)
        # 检查内存中的数据
        generated_in_memory = set(novel_data.get("generated_chapters", {}).keys())
        memory_but_no_file = sorted(generated_in_memory - existing_chapters)
        file_but_no_memory = sorted(existing_chapters - generated_in_memory)
        return {
            "expected_total": total_chapters,
            "actual_files": file_info["total_files"],
            "memory_chapters": len(generated_in_memory),
            "missing_chapters": missing_chapters,
            "memory_but_no_file": memory_but_no_file,
            "file_but_no_memory": file_but_no_memory,
            "completion_rate": round(file_info["total_files"] / total_chapters * 100, 1) if total_chapters > 0 else 0,
            "is_complete": len(missing_chapters) == 0
        }           