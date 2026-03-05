"""
小说生成管理器
"""
import os
import json
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from web.web_config import logger, BASE_DIR, CREATIVE_IDEAS_FILE
from web.utils.path_utils import (
    get_user_novel_dir,
    get_public_projects_dir,
    find_novel_project,
    list_user_projects,
    is_admin,
    get_current_username,
    NOVEL_PROJECTS_ROOT
)


class NovelGenerationManager:
    """小说生成管理器"""
    
    def __init__(self):
        self.task_results = {}
        self.task_progress = {}
        self.novel_projects = {}
        self.active_tasks = {}
        self.task_threads = {}
        
        # 🔥 新增：初始化检查点管理器
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            self.checkpoint_enabled = True
            logger.info("✅ 检查点功能已启用")
        except Exception as e:
            self.checkpoint_enabled = False
            logger.warning(f"⚠️ 检查点功能未启用: {e}")
        
        logger.info("🔧 NovelGenerationManager 初始化开始")
        self.load_existing_novels()
        logger.info(f"🔧 NovelGenerationManager 初始化完成，加载了 {len(self.novel_projects)} 个小说项目")

    def _update_task_status(self, task_id: str, status: str, progress: int, error: Optional[str] = None):
        """更新任务状态和进度"""
        # 🔥 修复：即使task_id不在task_results中，也要初始化它（防止任务初始化失败导致的404）
        if task_id not in self.task_results:
            logger.info(f"⚠️ 任务 {task_id} 不在 task_results 中，初始化基础结构")
            self.task_results[task_id] = {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        else:
            self.task_results[task_id].update({
                "status": status,
                "progress": progress,
                "updated_at": datetime.now().isoformat()
            })
            if error:
                self.task_results[task_id]["error"] = error

        # 🔥 修复：始终更新task_progress，确保get_task_progress能返回数据
        self.task_progress[task_id] = {
            "status": status,
            "progress": progress,
            "timestamp": datetime.now().isoformat()
        }
        if error:
            self.task_progress[task_id]["error"] = error
            
            # 添加当前步骤信息（从novel_data中获取）
            try:
                # 这里可以通过事件总线或其他方式获取当前步骤
                # 暂时使用状态映射
                step_mapping = {
                    20: "planning",
                    40: "planning",
                    45: "worldview_generation",
                    60: "character_design",
                    65: "story_outline",
                    68: "global_growth_planning",
                    70: "global_growth_planning",
                    72: "global_growth_planning",
                    75: "stage_planning",
                    80: "story_outline",
                    85: "validation",
                    95: "validation",
                    100: "completed"
                }
                
                current_step = step_mapping.get(progress, "initialization")
                self.task_results[task_id]["current_step"] = current_step
                self.task_progress[task_id]["current_step"] = current_step
                
                logger.info(f"任务 {task_id}: 进度更新 {progress}% - 当前步骤: {current_step}")
                
            except Exception as e:
                logger.debug(f"任务 {task_id}: 更新当前步骤失败: {e}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id not in self.task_results:
            return {"error": "任务不存在"}
        return self.task_results[task_id]

    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务进度"""
        return self.task_progress.get(task_id, {})

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务"""
        return list(self.task_results.values())

    def load_existing_novels(self):
        """从文件系统加载已存在的小说项目 - 支持新旧路径结构"""
        # 添加线程锁保护，避免并发调用导致文件I/O错误
        import threading
        lock = getattr(self, '_load_lock', None)
        if lock is None:
            lock = threading.Lock()
            self._load_lock = lock
        
        with lock:
            self._load_existing_novels_impl()
    
    def _load_existing_novels_impl(self):
        """实际加载小说项目的实现 - 支持用户隔离"""
        try:
            # 导入路径配置
            from src.config.path_config import path_config
            
            username = get_current_username()
            logger.info(f"👤 当前用户: {username} (管理员: {is_admin(username)})")
            
            # 获取所有可访问的项目
            projects = list_user_projects(username, include_public=True)
            
            if not projects:
                logger.info("📁 没有找到小说项目")
                return
            
            logger.info(f"🔍 扫描到 {len(projects)} 个可访问的小说项目...")

            for project in projects:
                try:
                    project_path = Path(project['path'])
                    title = project['title']
                    owner = project['owner']
                    
                    # 查找项目信息文件
                    project_info_path = self._find_project_info_file(project_path)
                    
                    if project_info_path and project_info_path.exists():
                        with open(project_info_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            novel_data = json.loads(content)
                        
                        # 加载项目数据，添加 owner 信息
                        self._load_project_from_data(title, novel_data, title, owner=owner)
                        
                        owner_label = "[公共]" if project['is_public'] else f"[{owner}]"
                        logger.info(f"✅ 加载小说项目 {owner_label}: {title}")
                    else:
                        logger.warning(f"⚠️ 项目信息文件不存在: {project_path}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON解析失败 {project['path']}: {e}")
                except Exception as e:
                    logger.error(f"❌ 加载项目失败 {project['title']}: {e}")

            logger.info(f"📚 总共加载了 {len(self.novel_projects)} 个小说项目")

        except Exception as e:
            logger.error(f"❌ 加载已存在小说项目失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")
    
    def _find_project_info_file(self, project_path: Path) -> Optional[Path]:
        """查找项目信息文件"""
        # 优先查找 小说名_项目信息.json
        info_file = project_path / f"{project_path.name}_项目信息.json"
        if info_file.exists():
            return info_file
        
        # 备选：project_info.json
        info_file = project_path / "project_info.json"
        if info_file.exists():
            return info_file
        
        # 备选：project_info/ 子目录
        info_dir = project_path / "project_info"
        if info_dir.is_dir():
            json_files = list(info_dir.glob("*_项目信息*.json"))
            if json_files:
                return json_files[0]
        
        return None

    def _load_project_from_data(self, title: str, novel_data: Dict, path_key: str, owner: str = None):
        """从已加载的数据中提取并加载项目信息（辅助方法）"""
        try:
            from src.config.path_config import path_config
            
            # 添加所有者信息
            if owner:
                novel_data['owner'] = owner
            
            # 使用新的路径配置系统获取章节目录
            paths = path_config.get_project_paths(title)
            chapter_dirs = [
                Path(paths["chapters_dir"]),  # 新路径：小说项目/小说名/chapters
                Path("小说项目") / f"{title}_章节",   # 旧路径：小说项目/小说名_章节
                Path("小说项目") / title / "chapters"  # 兼容路径：小说项目/小说名/chapters
            ]
            
            generated_chapters = {}
            actual_chapter_dir = None

            # 尝试从多个可能的章节目录加载
            for chapter_dir in chapter_dirs:
                if chapter_dir.exists():
                    actual_chapter_dir = chapter_dir
                    
                    # 查找章节文件（支持.txt和.json格式）
                    chapter_files = list(chapter_dir.glob("第*.txt")) + list(chapter_dir.glob("第*.json"))
                    
                    for chapter_file in chapter_files:
                        # 提取章节号
                        try:
                            match = re.search(r'第(\d+)章', chapter_file.name)
                            if match:
                                chapter_num = int(match.group(1))
                            else:
                                continue
                            with open(chapter_file, 'r', encoding='utf-8') as cf:
                                file_content = cf.read()

                            # 尝试解析JSON文件并提取内容
                            try:
                                chapter_json = json.loads(file_content)
                                chapter_content = chapter_json.get("content", file_content)
                                chapter_title = chapter_json.get("chapter_title", chapter_file.stem.replace("第", "").replace("章", ""))
                                chapter_word_count = chapter_json.get("word_count", len(chapter_content))

                            except json.JSONDecodeError:
                                # 如果不是JSON格式，直接使用原始内容
                                chapter_content = file_content
                                chapter_title = chapter_file.stem.replace("第", "").replace("章", "")
                                chapter_word_count = len(chapter_content)

                            generated_chapters[chapter_num] = {
                                "chapter_number": chapter_num,
                                "title": chapter_title,
                                "content": chapter_content,
                                "word_count": chapter_word_count,
                                "file_path": str(chapter_file)
                            }
                        except Exception as e:
                            logger.info(f"⚠️ 加载章节 {chapter_file.name} 失败: {e}")
                    
                    break  # 找到有效的章节目录后停止搜索

            # 更新小说数据
            novel_data["generated_chapters"] = generated_chapters
            novel_data["creation_time"] = novel_data.get("creation_time", datetime.now().isoformat())
            
            # 添加章节目录信息
            if actual_chapter_dir:
                novel_data["chapter_directory"] = str(actual_chapter_dir)

            # 加载质量数据
            quality_data = self.load_quality_data(title)
            novel_data["quality_data"] = quality_data

            # 🔥 修复：从独立文件加载写作风格指南
            try:
                writing_style_path = Path(paths.get("writing_style_guide", ""))
                if writing_style_path.exists():
                    with open(writing_style_path, 'r', encoding='utf-8') as f:
                        writing_style_guide = json.load(f)
                    novel_data["writing_style_guide"] = writing_style_guide
                    logger.info(f"  ✅ 已加载写作风格指南: {len(writing_style_guide)} 个键")
                else:
                    # 如果独立文件不存在，尝试从项目信息中获取
                    if novel_data.get("writing_style_guide"):
                        logger.info(f"  ✅ 从项目信息中获取写作风格指南")
                    else:
                        logger.warning(f"  ⚠️ 写作风格指南文件不存在: {writing_style_path}")
                        novel_data["writing_style_guide"] = {}
            except Exception as e:
                logger.warning(f"  ⚠️ 加载写作风格指南失败: {e}")
                novel_data["writing_style_guide"] = novel_data.get("writing_style_guide", {})

            # 添加到项目集合
            self.novel_projects[title] = novel_data
            logger.info(f"  - 已加载 {len(generated_chapters)} 章")

        except Exception as e:
            logger.error(f"❌ 处理项目数据 {title} 失败: {e}")

    def load_quality_data(self, title: str) -> Dict[str, Any]:
        """加载小说的质量数据"""
        # 导入路径配置
        from src.config.path_config import path_config
        
        # 获取安全的标题
        safe_title = path_config.get_safe_title(title)
        
        quality_data = {
            "character_development": {},
            "world_state": {},
            "events": [],
            "writing_plans": {},
            "relationships": {},
            "chapter_failures": []
        }

        try:
            # 使用新的路径配置系统
            paths = path_config.get_project_paths(title)
            
            # 基础路径 - 使用新的目录结构
            novel_base = Path(paths["project_root"])
            quality_base = Path("quality_data")  # 保留作为后备
            chapter_base = Path("chapter_failures")

            # 加载角色发展数据 - 优先从新路径加载
            character_file = Path(paths.get("character_development", novel_base / "character_development" / f"{title}_character_development.json"))
            if not character_file.exists():
                character_file = quality_base / f"{title}_character_development.json"
            
            if character_file.exists():
                with open(character_file, 'r', encoding='utf-8') as f:
                    quality_data["character_development"] = json.load(f)

            # 加载世界观数据 - 优先从新路径加载
            world_file = Path(paths["world_state"])
            if not world_file.exists():
                world_file = quality_base / f"{title}_world_state.json"
            
            if world_file.exists():
                with open(world_file, 'r', encoding='utf-8') as f:
                    quality_data["world_state"] = json.load(f)

            # 加载事件数据 - 优先从新路径加载
            events_file = Path(paths.get("events", novel_base / "events" / f"{title}_events.json"))
            if not events_file.exists():
                events_file = quality_base / f"{title}_events.json"
            
            if events_file.exists():
                with open(events_file, 'r', encoding='utf-8') as f:
                    quality_data["events"] = json.load(f)

            # 加载思维设定数据 - 新增
            mindset_dir = Path(paths.get("mindset_dir", novel_base / "mindset"))
            if mindset_dir.exists():
                quality_data["mindset"] = {}
                mindset_files = list(mindset_dir.glob(f"{title}_mindset_*.json"))
                for mindset_file in mindset_files:
                    with open(mindset_file, 'r', encoding='utf-8') as f:
                        mindset_data = json.load(f)
                        character_name = mindset_file.stem.replace(f"{title}_mindset_", "")
                        quality_data["mindset"][character_name] = mindset_data

            # 加载事件详细记录（JSONL格式）
            events_jsonl = quality_base / "events" / f"{title}_events.jsonl"
            if events_jsonl.exists():
                events = []
                with open(events_jsonl, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            try:
                                events.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
                quality_data["detailed_events"] = events

            # 加载写作计划 - 从新路径加载（支持 planning 和 plans 两个目录）
            planning_dir = Path(paths.get("writing_plans_dir", novel_base / "planning"))
            plans_dir = novel_base / "plans"  # 🔥 新增：也支持 plans 目录
            
            # 检查两个目录
            plan_files = []
            
            # 优先从 plans 目录加载（包含四个阶段文件）
            if plans_dir.exists():
                plan_files = list(plans_dir.glob(f"*_stage_writing_plan.json"))
                if plan_files:
                    logger.info(f"✅ 从 plans 目录找到 {len(plan_files)} 个阶段写作计划文件")
            
            # 如果 plans 目录没有，尝试 planning 目录
            if not plan_files and planning_dir.exists():
                plan_files = list(planning_dir.glob(f"{title}*writing_plan*.json"))
                
                # 如果没找到，尝试直接匹配常见文件名格式
                if not plan_files:
                    common_names = [
                        planning_dir / f"{title}_写作计划.json",
                        planning_dir / f"{safe_title}_写作计划.json"
                    ]
                    for common_name in common_names:
                        if common_name.exists():
                            plan_files = [common_name]
                            logger.info(f"✅ 通过常见文件名找到写作计划: {common_name}")
                            break
            
            # 🔥 修复：处理找到的所有计划文件（无论来自哪个目录）
            for plan_file in plan_files:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    # 🔥 修复：从文件名提取阶段名
                    # 文件名格式：吞噬万界：从一把生锈铁剑开始_opening_stage_writing_plan.json
                    match = re.search(r'_(.+?)_stage_writing_plan\.json$', plan_file.name)
                    if match:
                        stage_name = match.group(1)
                    else:
                        # 尝试从 plan_data 中获取 stage_name
                        if isinstance(plan_data, dict):
                            stage_writing_plan = plan_data.get("stage_writing_plan", {})
                            if isinstance(stage_writing_plan, dict):
                                stage_name = stage_writing_plan.get("stage_name", "unknown")
                            else:
                                stage_name = "unknown"
                        else:
                            stage_name = "unknown"
                    quality_data["writing_plans"][stage_name] = plan_data
                    logger.info(f"✅ 已加载写作计划: {plan_file.name} -> 阶段: {stage_name}")

            # 加载关系数据
            relationships_file = Path(paths.get("relationships", novel_base / "relationships.json"))
            if not relationships_file.exists():
                relationships_file = quality_base / "relationships" / f"{title}_relationships.json"
            
            if relationships_file.exists():
                with open(relationships_file, 'r', encoding='utf-8') as f:
                    quality_data["relationships"] = json.load(f)

            # 加载章节失败记录
            failures_file = chapter_base / f"failures_{title}.json"
            if failures_file.exists():
                with open(failures_file, 'r', encoding='utf-8') as f:
                    failures = json.load(f)
                    # 按章节号组织失败记录
                    chapter_failures = {}
                    for failure in failures if isinstance(failures, list) else [failures]:
                        chapter_num = failure.get("chapter_number", 0)
                        if chapter_num not in chapter_failures:
                            chapter_failures[chapter_num] = []
                        chapter_failures[chapter_num].append(failure)
                    quality_data["chapter_failures"] = chapter_failures

            logger.info(f"📊 加载质量数据完成: {title}")

        except Exception as e:
            logger.error(f"❌ 加载质量数据失败 {title}: {e}")

        return quality_data

    def get_novel_projects(self) -> List[Dict[str, Any]]:
        """获取所有小说项目"""
        projects = []
        for title, data in self.novel_projects.items():
            generated_chapters = data.get("generated_chapters", {})
            completed_chapters = len(generated_chapters)
            
            # 计算总字数
            total_word_count = 0
            for chapter_num, chapter_data in generated_chapters.items():
                if isinstance(chapter_data, dict):
                    total_word_count += chapter_data.get("word_count", 0)
                else:
                    total_word_count += len(str(chapter_data))
            
            # 计算平均评分
            total_score = 0
            scored_chapters = 0
            for chapter_num, chapter_data in generated_chapters.items():
                if isinstance(chapter_data, dict):
                    quality_assessment = chapter_data.get("quality_assessment", {})
                    if quality_assessment and "overall_score" in quality_assessment:
                        total_score += quality_assessment["overall_score"]
                        scored_chapters += 1
            
            average_score = total_score / scored_chapters if scored_chapters > 0 else 0
            
            # 获取目标章节数，优先从数据中获取，否则使用已生成章节数
            # 修复：正确的字段路径是 progress.total_chapters，而不是 current_progress.total_chapters
            # 修复：使用明确的检查，避免将0视为False
            target_chapters = (
                data.get("progress", {}).get("total_chapters", 0) if data.get("progress", {}).get("total_chapters", 0) > 0 else
                (data.get("total_chapters", 0) if data.get("total_chapters", 0) > 0 else
                (data.get("novel_info", {}).get("total_chapters", 0) if data.get("novel_info", {}).get("total_chapters", 0) > 0 else
                (data.get("novel_info", {}).get("creative_seed", {}).get("totalChapters", 0) if data.get("novel_info", {}).get("creative_seed", {}).get("totalChapters", 0) > 0 else
                completed_chapters)))
            )
            
            # 获取核心设定和简介
            creative_seed = data.get("creative_seed", {})
            core_setting = creative_seed.get("coreSetting", "") if isinstance(creative_seed, dict) else str(creative_seed)[:200]
            synopsis = data.get("novel_synopsis", "") or data.get("synopsis", "")
            
            # 获取项目所有者
            owner = data.get('owner', 'unknown')
            is_public = owner == 'public'
            
            projects.append({
                "title": title,
                "novel_title": title,  # 🔥 修复：添加 novel_title 字段以匹配前端期望
                "total_chapters": int(target_chapters),
                "completed_chapters": completed_chapters,
                "word_count": total_word_count,
                "average_score": round(average_score, 1),
                "created_at": data.get("creation_time", datetime.now().isoformat()),
                "last_updated": data.get("current_progress", {}).get("last_updated", ""),
                "status": "completed" if completed_chapters >= target_chapters and target_chapters > 0 else "generating",
                # 添加前端需要的字段
                "story_synopsis": synopsis,
                "core_setting": core_setting,
                "synopsis": synopsis,  # 保留向后兼容
                # 用户隔离相关字段
                "owner": owner,
                "is_public": is_public,
                "is_owner": owner == get_current_username() or is_public
            })
        return sorted(projects, key=lambda x: x["last_updated"], reverse=True)

    def get_novel_detail(self, title: str) -> Optional[Dict[str, Any]]:
        """获取小说详情，并标准化字段名以兼容前端"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return None
        
        # 获取核心世界观数据 - 尝试从多个字段获取
        core_worldview = novel_data.get("core_worldview", {})
        
        # 如果 core_worldview 为空，尝试从其他字段获取
        if not core_worldview or (isinstance(core_worldview, dict) and len(core_worldview) == 0):
            # 尝试从 quality_data 获取
            quality_data = novel_data.get("quality_data", {})
            if quality_data:
                # 从 world_state 获取世界观信息
                world_state = quality_data.get("world_state", {})
                if world_state:
                    core_worldview = {
                        "worldview": world_state.get("worldview", {}),
                        "setting": world_state.get("setting", {}),
                        "rules": world_state.get("rules", {})
                    }
                
                # 如果仍然为空，尝试从 creative_seed 构建
                if not core_worldview or (isinstance(core_worldview, dict) and len(core_worldview) == 0):
                    creative_seed = novel_data.get("creative_seed", {})
                    if creative_seed:
                        core_worldview = {
                            "core_setting": creative_seed.get("coreSetting", ""),
                            "genre": creative_seed.get("genre", ""),
                            "target_platform": creative_seed.get("targetPlatform", ""),
                            "source_material": creative_seed.get("sourceMaterial", "")
                        }
        
        # 标准化字段名，确保前端能正确读取
        standardized_data = {
            # 保留所有原始字段
            **novel_data,

            # 🔥 修复：同时添加 title 和 novel_title 字段以匹配前端期望
            "title": title,
            "novel_title": title,
            
            # 添加前端期望的字段名映射
            "story_synopsis": novel_data.get("novel_synopsis", "") or novel_data.get("synopsis", ""),
            "core_setting": novel_data.get("creative_seed", {}).get("coreSetting", ""),
            # 🔥 新增：添加 core_worldview 字段，用于视频生成
            "core_worldview": core_worldview if core_worldview else {},
        }
        
        # 🔥 修复：确保 stage_writing_plans 字段存在
        # 从 quality_data.writing_plans 映射到 stage_writing_plans
        if "stage_writing_plans" not in standardized_data or not standardized_data["stage_writing_plans"]:
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                standardized_data["stage_writing_plans"] = writing_plans
                logger.info(f"✅ 从 quality_data.writing_plans 映射到 stage_writing_plans: {len(writing_plans)} 个阶段")
        
        # 🔥 修复：确保 overall_stage_plans 字段存在
        if "overall_stage_plans" not in standardized_data or not standardized_data.get("overall_stage_plans", {}):
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                # 从所有阶段的写作计划中提取 overall_stage_plan
                overall_stage_plan = {}
                for stage_name, stage_data in writing_plans.items():
                    if isinstance(stage_data, dict) and "stage_writing_plan" in stage_data:
                        stage_plan = stage_data["stage_writing_plan"]
                        overall_stage_plan[stage_name] = {
                            "chapter_range": stage_plan.get("chapter_range", ""),
                            "stage_overview": stage_plan.get("stage_overview", ""),
                            "event_system": stage_plan.get("event_system", {})
                        }
                
                if overall_stage_plan:
                    standardized_data["overall_stage_plans"] = {"overall_stage_plan": overall_stage_plan}
                    logger.info(f"✅ 从 writing_plans 构建 overall_stage_plans: {len(overall_stage_plan)} 个阶段")
        
        # 🔥 修复：确保 global_growth_plan 字段存在
        if "global_growth_plan" not in standardized_data or not standardized_data.get("global_growth_plan", {}):
            # 从写作计划中提取成长规划信息
            quality_data = novel_data.get("quality_data", {})
            writing_plans = quality_data.get("writing_plans", {})
            if writing_plans:
                # 构建基础的全局成长规划
                global_growth_plan = {
                    "growth_stages": [],
                    "power_systems": {},
                    "world_building": {}
                }
                standardized_data["global_growth_plan"] = global_growth_plan
                logger.info("✅ 创建基础 global_growth_plan 结构")

        # 🔥 修复：确保 writing_style_guide 字段存在（动态加载）
        if "writing_style_guide" not in standardized_data or not standardized_data.get("writing_style_guide"):
            try:
                from src.config.path_config import path_config
                writing_style_path = Path(path_config.get_project_paths(title).get("writing_style_guide", ""))
                if writing_style_path.exists():
                    with open(writing_style_path, 'r', encoding='utf-8') as f:
                        writing_style_guide = json.load(f)
                    standardized_data["writing_style_guide"] = writing_style_guide
                    logger.info(f"✅ 动态加载写作风格指南成功: {len(writing_style_guide)} 个键")
                else:
                    logger.warning(f"⚠️ 写作风格指南文件不存在: {writing_style_path}")
                    standardized_data["writing_style_guide"] = {}
            except Exception as e:
                logger.warning(f"⚠️ 动态加载写作风格指南失败: {e}")
                standardized_data["writing_style_guide"] = {}

        return standardized_data

    def get_chapter_detail(self, title: str, chapter_num: int) -> Optional[Dict[str, Any]]:
        """获取章节详情"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return None
        return novel_data.get("generated_chapters", {}).get(chapter_num)

    def get_chapter_quality_data(self, title: str, chapter_num: int) -> Dict[str, Any]:
        """获取章节质量数据"""
        quality_data = {
            "character_development": {},
            "world_state": {},
            "events": [],
            "generation_context": {},
            "chapter_failures": [],
            "writing_plan": {},
            "character_relationships": {}
        }

        try:
            # 从项目的质量数据中提取章节相关信息
            novel_data = self.novel_projects.get(title)
            if not novel_data or "quality_data" not in novel_data:
                return quality_data

            project_quality = novel_data["quality_data"]

            # 获取角色发展数据（过滤到当前章节）
            character_data = project_quality.get("character_development", {})
            if character_data and isinstance(character_data, dict):
                # 提取在当前章节活跃的角色
                active_characters = {}
                for char_name, char_info in character_data.items():
                    if isinstance(char_info, dict) and char_info.get("first_appearance_chapter", 0) <= chapter_num <= char_info.get("last_updated_chapter", 0):
                        active_characters[char_name] = char_info
                quality_data["character_development"] = active_characters

            # 获取世界观数据
            quality_data["world_state"] = project_quality.get("world_state", {})

            # 获取事件数据（过滤到当前章节）
            all_events = project_quality.get("detailed_events", [])
            if isinstance(all_events, list):
                chapter_events = [event for event in all_events if isinstance(event, dict) and event.get("chapter_number") == chapter_num]
            else:
                chapter_events = []
            quality_data["events"] = chapter_events

            # 获取章节失败记录
            chapter_failures_data = project_quality.get("chapter_failures", {})
            if isinstance(chapter_failures_data, dict):
                chapter_failures = chapter_failures_data.get(chapter_num, [])
                if not isinstance(chapter_failures, list):
                    chapter_failures = []
            else:
                chapter_failures = []
            quality_data["chapter_failures"] = chapter_failures

            # 获取当前章节的写作计划
            writing_plans = project_quality.get("writing_plans", {})
            for stage_name, plan_data in writing_plans.items():
                # 确保plan_data是字典类型
                if not isinstance(plan_data, dict):
                    continue
                
                stage_writing_plan = plan_data.get("stage_writing_plan", {})
                # 确保stage_writing_plan也是字典类型
                if not isinstance(stage_writing_plan, dict):
                    continue
                    
                chapter_range = stage_writing_plan.get("chapter_range", "")
                if self._is_chapter_in_range(chapter_num, chapter_range):
                    quality_data["writing_plan"] = plan_data
                    break

            # 获取关系数据
            quality_data["character_relationships"] = project_quality.get("relationships", {})

        except Exception as e:
            logger.error(f"❌ 获取章节质量数据失败 {title} 第{chapter_num}章: {e}")

        return quality_data

    def _is_chapter_in_range(self, chapter_num: int, chapter_range: str) -> bool:
        """检查章节是否在范围内"""
        try:
            if not chapter_range or "-" not in chapter_range:
                return False

            start_str, end_str = chapter_range.replace(" ", "").split("-")
            start = int(start_str)
            end = int(end_str)
            return start <= chapter_num <= end
        except:
            return False

    def export_novel(self, title: str, format_type: str = "json") -> Dict[str, Any]:
        """导出小说"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return {"error": "小说不存在"}

        if format_type == "json":
            return novel_data
        elif format_type == "text":
            # 生成文本格式
            text_content = []
            text_content.append(f"# {novel_data.get('novel_title', '未命名')}")
            text_content.append(f"## 简介\n{novel_data.get('story_synopsis', '')}")
            text_content.append("---\n")

            chapters = novel_data.get("generated_chapters", {})
            for chapter_num in sorted(chapters.keys()):
                chapter = chapters[chapter_num]
                text_content.append(f"## {chapter.get('outline', {}).get('章节标题', f'第{chapter_num}章')}")
                text_content.append(chapter.get('content', ''))
                text_content.append("\n---\n")

            return {
                "content": "\n".join(text_content),
                "title": novel_data.get('novel_title', '未命名'),
                "format": "text"
            }
        else:
            return {"error": "不支持的导出格式"}

    def start_generation(self, config: Dict[str, Any]) -> str:
        """启动小说生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        self.task_results[task_id] = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": config,
            "title": config.get("title", "未命名小说"),
            "synopsis": config.get("synopsis", ""),
            "total_chapters": config.get("total_chapters", 200),
            "generation_mode": config.get("generation_mode", "full_auto")
        }
        
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 启动后台任务
        def run_generation():
            try:
                generation_mode = config.get("generation_mode", "full_auto")
                if generation_mode == "phase_one_only":
                    self._run_phase_one_task(task_id, config)
                else:
                    self._run_generation_task(task_id, config)
            except Exception as e:
                logger.error(f"生成任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
        
        thread = threading.Thread(target=run_generation)
        thread.daemon = True
        thread.start()
        
        self.task_threads[task_id] = thread
        
        return task_id

    def _run_phase_one_task(self, task_id: str, config: Dict[str, Any]):
        """执行第一阶段生成任务"""
        try:
            title = config.get("title", "未命名小说")
            is_resume_mode = config.get("is_resume_mode", False)
            
            # 🔥 新增：获取 start_new 参数，用户选择"从新开始"时应删除现有检查点
            start_new = config.get("start_new", False)
            if start_new:
                logger.info(f"🆕 用户选择从头开始，将删除现有检查点")
                self._delete_existing_checkpoint(title)
            
            # 创建初始检查点（仅在非恢复模式下）
            if self.checkpoint_enabled and not is_resume_mode:
                self._create_initial_checkpoint(title, config, task_id)
            
            self._update_task_status(task_id, "generating", 10)
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                
                # 导入完整配置 - 使用绝对路径避免冲突
                import sys
                from pathlib import Path
                
                # 确保项目根目录在路径中
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                # 使用importlib来动态导入config
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置 - 使用完整的CONFIG而不是简化的配置
                generator_config = CONFIG.copy()
                # 更新一些默认值
                generator_config["defaults"]["total_chapters"] = config.get("total_chapters", 200)
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            
            # 更新进度
            self._update_task_status(task_id, "generating", 20)
            
            # 🔥 新增：更新检查点 - 初始化完成
            if self.checkpoint_enabled:
                self._update_checkpoint(title, "phase_one", "initialization", {"status": "generator_initialized"}, step_status="completed")
            
            logger.info(f"任务 {task_id}: 📋 分析创意种子 (40%)")
            self._update_task_status(task_id, "generating", 40)
            
            # 更新检查点 - 开始分析
            if self.checkpoint_enabled:
                self._update_checkpoint(title, "phase_one", "worldview_generation", {"status": "analyzing_seed"}, step_status="in_progress")
            self._update_task_status(task_id, "generating", 60)
            
            # 更新检查点 - 开始角色生成（在实际调用前保存为 in_progress）
            if self.checkpoint_enabled:
                self._update_checkpoint(title, "phase_one", "character_generation", {"status": "generating_worldview"}, step_status="in_progress")
            
            try:
                # 为生成器设置进度回调（使用动态属性设置）
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                # 🔥 传递 start_new 和 target_platform 参数给生成器
                success = novel_generator.phase_one_generation(
                    creative_seed,
                    total_chapters,
                    start_new=config.get("start_new", False),
                    target_platform=config.get("target_platform", "fanqie")
                )
                
                if success:
                    # 标记步骤完成
                    if self.checkpoint_enabled:
                        self._update_checkpoint(title, "phase_one", "character_generation", {"status": "completed"}, step_status="completed")
                    
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 保存第一阶段结果到任务结果中
                    task_result = self.task_results.get(task_id, {})
                    task_result["result"] = {
                        "novel_title": novel_generator.novel_data.get("novel_title", "未命名"),
                        "total_chapters": total_chapters,
                        "phase_one_completed": True,
                        "next_phase": "second_phase_content_generation",
                        "novel_data_summary": {
                            "core_worldview": novel_generator.novel_data.get("core_worldview", {}),
                            "character_design": novel_generator.novel_data.get("character_design", {}),
                            "overall_stage_plans": novel_generator.novel_data.get("overall_stage_plans", {}),
                            "market_analysis": novel_generator.novel_data.get("market_analysis", {})
                        }
                    }
                    self.task_results[task_id] = task_result
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 第一阶段设定生成失败")
                    self._update_task_status(task_id, "failed", 0, "第一阶段设定生成返回 False")
                    
                    # 标记步骤失败，保留检查点以便恢复
                    if self.checkpoint_enabled:
                        self._update_checkpoint(title, "phase_one", "character_generation", {"status": "failed", "error": "第一阶段设定生成返回 False"}, step_status="failed")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: phase_one_generation 执行异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"第一阶段生成过程异常: {str(e)}")
                
                # 标记步骤失败
                if self.checkpoint_enabled:
                    self._update_checkpoint(title, "phase_one", "character_generation", {"status": "failed", "error": str(e)}, step_status="failed")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 第一阶段生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")
    
    def _create_initial_checkpoint(self, title: str, config: Dict[str, Any], task_id: str):
        """创建初始检查点，保存创意标题到实际书名的映射"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
             
            # 获取创意标题和创意ID
            creative_seed = config.get("creative_seed", {})
            creative_title = None
            creative_seed_id = None
            
            if isinstance(creative_seed, dict):
                # 尝试从不同字段获取创意标题
                creative_title = (
                    creative_seed.get("novelTitle") or
                    creative_seed.get("title") or
                    creative_seed.get("coreSetting", "")[:50]  # 使用核心设定作为后备
                )
                # 获取创意ID（如果存在）
                creative_seed_id = creative_seed.get("id") or creative_seed.get("seedId")
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
             
            logger.info(f"📁 检查点目录: {checkpoint_mgr.checkpoint_dir}")
            logger.info(f"📄 检查点文件: {checkpoint_mgr.checkpoint_file}")
            
            # 创建检查点数据，包含创意标题映射
            checkpoint_data = {
                'generation_params': config,
                'task_id': task_id,
                'status': 'started',
                'created_at': datetime.now().isoformat()
            }
            
            # 添加创意标题映射信息
            if creative_title:
                checkpoint_data['creative_title'] = creative_title
                logger.info(f"💾 保存创意标题映射: {creative_title} -> {title}")
            
            if creative_seed_id:
                checkpoint_data['creative_seed_id'] = creative_seed_id
                logger.info(f"💾 保存创意ID: {creative_seed_id}")
             
            checkpoint_mgr.create_checkpoint(
                phase='phase_one',
                step='initialization',
                data=checkpoint_data
            )
             
            logger.info(f"✅ 初始检查点已创建: {title}")
             
        except Exception as e:
            logger.error(f"❌ 创建初始检查点失败: {e}")
    
    def _delete_existing_checkpoint(self, title: str):
        """删除现有检查点（用于从头开始生成）"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
             
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
            checkpoint_mgr.delete_checkpoint()
             
            logger.info(f"✅ 已删除现有检查点: {title}")
             
        except Exception as e:
            logger.error(f"❌ 删除检查点失败: {e}")
    
    def _update_checkpoint(self, title: str, phase: str, step: str, data: Dict, step_status: str = "in_progress"):
        """
        更新检查点
        
        Args:
            title: 小说标题
            phase: 生成阶段
            step: 当前步骤
            data: 要保存的数据
            step_status: 步骤状态 (pending/in_progress/completed/failed)
        """
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
            
            # 保留原有的生成参数
            existing_checkpoint = checkpoint_mgr.load_checkpoint()
            if existing_checkpoint and 'data' in existing_checkpoint:
                existing_data = existing_checkpoint['data']
                data = {**existing_data, **data}
            
            checkpoint_mgr.create_checkpoint(phase, step, data, step_status)
            logger.info(f"✅ 检查点已更新: {title} - {step} (状态: {step_status})")
            
        except Exception as e:
            logger.error(f"❌ 更新检查点失败: {e}")
    
    def _complete_checkpoint(self, title: str):
        """完成任务时删除检查点"""
        try:
            from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
            from pathlib import Path
            
            checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())
            success = checkpoint_mgr.delete_checkpoint()
            
            if success:
                logger.info(f"✅ 检查点已删除: {title}（任务完成）")
            
        except Exception as e:
            logger.error(f"❌ 删除检查点失败: {e}")

    def _run_generation_task(self, task_id: str, config: Dict[str, Any]):
        """执行完整生成任务（兼容原有逻辑）"""
        try:
            self._update_task_status(task_id, "generating", 10)
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                
                # 导入完整配置 - 使用绝对路径避免冲突
                import sys
                from pathlib import Path
                
                # 确保项目根目录在路径中
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                # 使用importlib来动态导入config
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置 - 使用完整的CONFIG而不是简化的配置
                generator_config = CONFIG.copy()
                # 更新一些默认值
                generator_config["defaults"]["total_chapters"] = config.get("total_chapters", 200)
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            
            # 更新进度
            self._update_task_status(task_id, "generating", 20)
            self._update_task_status(task_id, "generating", 40)
            self._update_task_status(task_id, "generating", 60)
            try:
                # 为生成器设置进度回调
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                success = novel_generator.full_auto_generation(creative_seed, total_chapters)
                
                if success:
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                        # 检查是否真的生成了文件
                        self._check_generated_files(task_id, config)
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 小说生成失败")
                    self._update_task_status(task_id, "failed", 0, "小说生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: full_auto_generation 执行异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def _check_generated_files(self, task_id: str, config: Dict[str, Any]):
        """检查是否真的生成了小说文件"""
        try:
            # 获取小说标题（从配置或创意种子）
            novel_title = config.get("title") or config.get("creative_seed", {}).get("novelTitle", "未命名小说")
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 检查项目目录
            project_dir = Path("小说项目")
            if not project_dir.exists():
                return False
            
            # 检查具体的小说文件 - 优先使用新路径
            novel_dir = project_dir / safe_title / "chapters"
            if not novel_dir.exists():
                novel_dir = project_dir / f"{safe_title}_章节"
            
            if novel_dir.exists():
                chapter_files = list(novel_dir.glob("*.txt"))
                
                # 检查文件内容是否为空
                empty_files = 0
                for file_path in chapter_files:
                    if file_path.stat().st_size == 0:
                        empty_files += 1
                
                total_words = 0
                for file_path in chapter_files:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 尝试解析JSON格式
                            try:
                                chapter_data = json.loads(content)
                                content = chapter_data.get("content", content)
                            except json.JSONDecodeError:
                                # 如果不是JSON格式，使用原始文本
                                pass
                            total_words += len(content)
                    except Exception as e:
                        logger.error(f"任务 {task_id}: 读取章节文件失败: {e}")
                
                return True
                
            else:
                return False
                
        except Exception as e:
            logger.error(f"任务 {task_id}: 检查生成文件时出错: {e}")
            return False

    def _run_resume_task(self, task_id: str, title: str, from_chapter: int, additional_chapters: int):
        """执行续写任务"""
        try:
            logger.info(f"任务 {task_id}: 🚀 开始续写小说: {title}")
            logger.info(f"任务 {task_id}: 从第{from_chapter}章开始，续写{additional_chapters}章")
            
            self._update_task_status(task_id, "loading_data", 10)
            
            # 加载现有小说数据
            novel_detail = self.get_novel_detail(title)
            if not novel_detail:
                logger.error(f"任务 {task_id}: ❌ 无法加载小说数据: {title}")
                self._update_task_status(task_id, "failed", 0, f"无法加载小说数据: {title}")
                return
            
            logger.info(f"任务 {task_id}: ✅ 成功加载小说数据")
            self._update_task_status(task_id, "initializing_generator", 20)
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                # 使用和上面相同的方式导入配置
                try:
                    import importlib.util
                    from pathlib import Path
                    
                    # 确保项目根目录在路径中
                    current_file = Path(__file__).resolve()
                    project_root = current_file.parent.parent.parent
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    logger.error(f"无法导入配置文件: {e}")
                    # 使用默认配置
                    CONFIG = {
                        "defaults": {
                            "total_chapters": from_chapter + additional_chapters,
                            "chapters_per_batch": 3
                        }
                    }
                
                # 构建生成器配置
                generator_config = CONFIG.copy()
                generator_config["defaults"]["total_chapters"] = from_chapter + additional_chapters
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                logger.info(f"任务 {task_id}: ✅ NovelGenerator 初始化成功")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 创建 NovelGenerator 失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            self._update_task_status(task_id, "preparing_resume", 30)
            
            # 准备续写数据
            try:
                # 设置小说数据到生成器
                novel_generator.novel_data = novel_detail
                novel_generator.novel_data["is_resuming"] = True
                novel_generator.novel_data["resume_data"] = {
                    "from_chapter": from_chapter,
                    "additional_chapters": additional_chapters,
                    "total_target_chapters": from_chapter + additional_chapters
                }
                
                # 更新进度信息
                novel_generator.novel_data["current_progress"]["total_chapters"] = from_chapter + additional_chapters
                novel_generator.novel_data["current_progress"]["stage"] = "续写生成"
                
                logger.info(f"任务 {task_id}: ✅ 续写数据准备完成")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 准备续写数据失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"准备续写数据失败: {str(e)}")
                return
            
            self._update_task_status(task_id, "generating", 50)
            
            # 执行续写生成
            try:
                logger.info(f"任务 {task_id}: 📝 开始续写章节生成...")
                
                # 计算实际需要生成的章节范围
                end_chapter = from_chapter + additional_chapters - 1
                
                # 批量生成章节
                success = novel_generator.generate_chapters_batch(from_chapter, end_chapter)
                
                if success:
                    logger.info(f"任务 {task_id}: ✅ 续写生成完成")
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 重新加载项目数据以获取最新状态
                    try:
                        self.load_existing_novels()
                        logger.info(f"任务 {task_id}: ✅ 项目数据重新加载完成")
                    except Exception as e:
                        logger.info(f"任务 {task_id}: ⚠️ 重新加载项目数据失败: {e}")
                        
                else:
                    logger.error(f"任务 {task_id}: ❌ 续写生成失败")
                    self._update_task_status(task_id, "failed", 0, "续写生成返回失败")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 续写生成过程异常: {e}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"续写生成异常: {str(e)}")
                
        except Exception as e:
            logger.error(f"任务 {task_id}: 🔥 续写任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def start_resume_generation(self, title: str, from_chapter: int, additional_chapters: int) -> str:
        """启动续写生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化续写任务
        resume_task = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": {
                "title": title,
                "from_chapter": from_chapter,
                "additional_chapters": additional_chapters,
                "total_chapters": from_chapter + additional_chapters,
                "novel_data": self.get_novel_detail(title)
            }
        }
        
        self.task_results[task_id] = resume_task
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 启动后台续写任务
        def run_resume_generation():
            try:
                self._run_resume_task(task_id, title, from_chapter, additional_chapters)
            except Exception as e:
                logger.error(f"续写任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
        
        thread = threading.Thread(target=run_resume_generation)
        thread.daemon = True
        thread.start()
        
        self.task_threads[task_id] = thread
        
        return task_id

    def start_phase_two_generation(self, config: Dict[str, Any]) -> str:
        """启动第二阶段章节生成任务"""
        task_id = str(uuid.uuid4())
        
        # 初始化第二阶段任务
        phase_two_task = {
            "task_id": task_id,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "config": config,
            "novel_title": config.get("novel_title", "未命名小说"),
            "phase_one_file": config.get("phase_one_file", ""),
            "from_chapter": config.get("from_chapter", 1),
            "chapters_to_generate": config.get("chapters_to_generate"),
            "generation_mode": "phase_two_only"
        }
        
        self.task_results[task_id] = phase_two_task
        self.task_progress[task_id] = {
            "status": "initializing",
            "progress": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # 启动后台第二阶段任务
        def run_phase_two_generation():
            try:
                self._run_phase_two_task(task_id, config)
            except Exception as e:
                logger.error(f"第二阶段任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
        
        thread = threading.Thread(target=run_phase_two_generation)
        thread.daemon = True
        thread.start()
        
        self.task_threads[task_id] = thread
        
        return task_id

    def _run_phase_two_task(self, task_id: str, config: Dict[str, Any]):
        """执行第二阶段生成任务"""
        try:
            novel_title = config.get("novel_title", "未命名小说")
            phase_one_file = config.get("phase_one_file", "")
            from_chapter = config.get("from_chapter", 1)
            chapters_to_generate = config.get("chapters_to_generate", 200)
            
            logger.info(f"任务 {task_id}: 🚀 开始第二阶段章节生成")
            logger.info(f"任务 {task_id}: 📚 小说标题: {novel_title}")
            logger.info(f"任务 {task_id}: 📖 起始章节: {from_chapter}")
            logger.info(f"任务 {task_id}: 📊 生成章节数: {chapters_to_generate}")
            
            # 初始化章节进度跟踪字典
            chapter_progress_dict = {}
            for i in range(chapters_to_generate):
                chapter_num = from_chapter + i
                chapter_progress_dict[chapter_num] = {
                    "chapter_number": chapter_num,
                    "status": "pending",
                    "chapter_title": "",
                    "word_count": 0,
                    "error": None
                }
            
            # 定义第二阶段进度计算函数
            def update_phase_two_progress(chapter_num: int, step: str = "generating",
                                         chapter_data: Optional[Dict[str, Any]] = None):
                """根据已生成章节数动态更新进度"""
                # 计算进度：准备阶段30% + 生成阶段(已完成章节数/总章节数)*60%
                if chapter_num < from_chapter:
                    progress = 10  # 初始化阶段
                else:
                    completed = chapter_num - from_chapter + 1
                    progress = 30 + min(int((completed / chapters_to_generate) * 60), 60)
                
                # 更新章节状态
                if chapter_num in chapter_progress_dict and chapter_data:
                    chapter_progress_dict[chapter_num].update({
                        "status": chapter_data.get("status", step),
                        "chapter_title": chapter_data.get("chapter_title", f"第{chapter_num}章"),
                        "word_count": chapter_data.get("word_count", 0),
                        "error": chapter_data.get("error")
                    })
                    logger.info(f"任务 {task_id}: 📖 第{chapter_num}章状态: {chapter_progress_dict[chapter_num]['status']}, 字数: {chapter_progress_dict[chapter_num]['word_count']}")
                
                # 更新进度，包含章节进度列表
                self._update_task_status(task_id, step, progress)
                
                # 将章节进度同步到 task_progress 中，供前端查询使用
                if task_id in self.task_progress:
                    # 转换为列表格式供前端使用
                    chapter_progress_list = list(chapter_progress_dict.values())
                    self.task_progress[task_id]["chapter_progress"] = chapter_progress_list
                    self.task_progress[task_id]["current_chapter"] = {
                        "number": chapter_num,
                        "title": chapter_progress_dict.get(chapter_num, {}).get("chapter_title", f"第{chapter_num}章")
                    }
                    self.task_progress[task_id]["total_chapters"] = chapters_to_generate
            
            # 初始化阶段 (10%)
            self._update_task_status(task_id, "initializing", 10)
            
            # 初始化NovelGenerator
            try:
                from src.core.NovelGenerator import NovelGenerator
                
                import sys
                from pathlib import Path
                
                current_file = Path(__file__).resolve()
                project_root = current_file.parent.parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                
                try:
                    import importlib.util
                    config_path = project_root / "config" / "config.py"
                    spec = importlib.util.spec_from_file_location("config_module", config_path)
                    if spec is not None and spec.loader is not None:
                        config_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(config_module)
                        CONFIG = config_module.CONFIG
                    else:
                        raise ImportError("无法创建config模块规格")
                except Exception as e:
                    CONFIG = {
                        "defaults": {
                            "total_chapters": 200,
                            "chapters_per_batch": 3
                        }
                    }
                
                generator_config = CONFIG.copy()
                generator_config["defaults"]["chapters_per_batch"] = 3
                
                novel_generator = NovelGenerator(generator_config)
                
            except Exception as e:
                logger.error(f"任务 {task_id}: 创建 NovelGenerator 失败: {e}")
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            # 初始化完成 (20%)
            self._update_task_status(task_id, "initializing", 20)
            
            # 🔥 修复：加载现有项目数据到NovelGenerator (25%)
            self._update_task_status(task_id, "loading_project", 25)
            
            # 加载现有项目数据
            novel_detail = self.get_novel_detail(novel_title)
            if not novel_detail:
                logger.error(f"任务 {task_id}: ❌ 无法加载小说数据: {novel_title}")
                self._update_task_status(task_id, "failed", 30, f"无法加载小说数据: {novel_title}")
                return
            
            logger.info(f"任务 {task_id}: ✅ 成功加载小说数据，开始准备第二阶段生成")
            
            # 🔥 关键修复：将现有项目数据设置到novel_generator中
            # 这样phase_two_generation才能访问到novel_title等数据
            novel_generator.novel_data = novel_detail
            novel_generator.novel_data["is_resuming"] = True
            novel_generator.novel_data["resume_data"] = {
                "from_chapter": from_chapter,
                "chapters_to_generate": chapters_to_generate
            }
            
            # 初始化材料管理器（如果需要）
            if not novel_generator.material_manager:
                novel_generator._initialize_material_manager()
            
            # 加载第一阶段数据完成 (30%)
            self._update_task_status(task_id, "preparing", 30)
            
            try:
                # 设置进度回调 - 用于在生成过程中动态更新进度
                setattr(novel_generator, '_phase_two_progress_callback', update_phase_two_progress)
                setattr(novel_generator, '_phase_two_from_chapter', from_chapter)
                setattr(novel_generator, '_phase_two_total_chapters', chapters_to_generate)
                
                # 🔥 修复：传递novel_title而不是phase_one_file
                success = novel_generator.phase_two_generation(
                    novel_title,  # 使用实际的小说标题
                    from_chapter,
                    chapters_to_generate
                )
                
                if success:
                    logger.info(f"任务 {task_id}: 第二阶段章节生成成功")
                    self._update_task_status(task_id, "completed", 100)
                    
                    task_result = self.task_results.get(task_id, {})
                    task_result["result"] = {
                        "novel_title": novel_title,
                        "from_chapter": from_chapter,
                        "chapters_to_generate": chapters_to_generate,
                        "phase_two_completed": True,
                        "generated_chapters": novel_generator.novel_data.get("generated_chapters", {}),
                        "total_generated": len(novel_generator.novel_data.get("generated_chapters", {}))
                    }
                    self.task_results[task_id] = task_result
                    
                    try:
                        self.load_existing_novels()
                    except Exception as e:
                        logger.info(f"任务 {task_id}: 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: 第二阶段章节生成失败")
                    self._update_task_status(task_id, "failed", 0, "第二阶段章节生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: phase_two_generation 执行异常: {e}")
                self._update_task_status(task_id, "failed", 0, f"第二阶段生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 第二阶段生成任务异常: {e}")
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")