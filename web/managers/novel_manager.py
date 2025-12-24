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


class NovelGenerationManager:
    """小说生成管理器"""
    
    def __init__(self):
        self.task_results = {}
        self.task_progress = {}
        self.novel_projects = {}
        self.active_tasks = {}
        self.task_threads = {}
        logger.info("🔧 NovelGenerationManager 初始化开始")
        self.load_existing_novels()
        logger.info(f"🔧 NovelGenerationManager 初始化完成，加载了 {len(self.novel_projects)} 个小说项目")

    def _update_task_status(self, task_id: str, status: str, progress: int, error: Optional[str] = None):
        """更新任务状态和进度"""
        if task_id in self.task_results:
            self.task_results[task_id].update({
                "status": status,
                "progress": progress,
                "updated_at": datetime.now().isoformat()
            })
            if error:
                self.task_results[task_id]["error"] = error

            # 更新进度记录
            self.task_progress[task_id] = {
                "status": status,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            }
            
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
        """实际加载小说项目的实现"""
        try:
            # 导入路径配置
            from src.config.path_config import path_config
            
            novel_dir = Path("小说项目")
            if not novel_dir.exists():
                logger.info("📁 小说项目目录不存在，将在首次生成时创建")
                return

            logger.info("🔍 扫描已存在的小说项目...")

            # 1. 首先扫描新路径结构（项目目录中的 project_info.json 或 project_info/ 目录）
            for item in novel_dir.iterdir():
                if item.is_dir():
                    # 检查直接在项目目录中的 project_info.json
                    project_info_path = item / "project_info.json"
                    
                    # 如果不存在，检查 project_info/ 子目录
                    if not project_info_path.exists():
                        project_info_dir = item / "project_info"
                        if project_info_dir.is_dir():
                            # 查找 project_info 目录中的 JSON 文件
                            json_files = list(project_info_dir.glob("*_项目信息*.json"))
                            if json_files:
                                project_info_path = json_files[0]  # 使用第一个找到的文件
                    
                    if project_info_path.exists():
                        novel_data = None
                        try:
                            # 使用完整的文件读取流程，确保文件正确关闭
                            with open(project_info_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                novel_data = json.loads(content)
                            
                            title = novel_data.get("novel_info", {}).get("title", item.name)
                            self._load_project_from_data(title, novel_data, item.name)
                            logger.info(f"✅ 加载小说项目(新路径): {title}")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ JSON解析失败 {project_info_path}: {e}")
                        except IOError as e:
                            logger.error(f"❌ 文件读取失败 {project_info_path}: {e}")
                        except Exception as e:
                            logger.error(f"❌ 加载新路径项目文件 {project_info_path} 失败: {e}")
                            import traceback
                            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")

            # 2. 扫描旧路径结构（根目录下的 *_项目信息.json 文件）
            for item in novel_dir.iterdir():
                if item.is_file() and item.name.endswith("_项目信息.json"):
                    # 提取小说标题
                    title = item.name.replace("_项目信息.json", "")
                    project_file = item

                    novel_data = None
                    try:
                        # 使用完整的文件读取流程，确保文件正确关闭
                        with open(project_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            novel_data = json.loads(content)
                        
                        # 检查是否已经从新路径加载过（避免重复）
                        if title not in self.novel_projects:
                            self._load_project_from_data(title, novel_data, title)
                            logger.info(f"✅ 加载小说项目(旧路径): {title}")

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON解析失败 {project_file}: {e}")
                    except IOError as e:
                        logger.error(f"❌ 文件读取失败 {project_file}: {e}")
                    except Exception as e:
                        logger.error(f"❌ 加载旧路径项目文件 {project_file} 失败: {e}")
                        import traceback
                        logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")

            logger.info(f"📚 总共加载了 {len(self.novel_projects)} 个小说项目")

        except Exception as e:
            logger.error(f"❌ 加载已存在小说项目失败: {e}")
            import traceback
            logger.error(f"❌ 错误堆栈: {traceback.format_exc()}")

    def _load_project_from_data(self, title: str, novel_data: Dict, path_key: str):
        """从已加载的数据中提取并加载项目信息（辅助方法）"""
        try:
            from src.config.path_config import path_config
            
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

            # 加载写作计划 - 从新路径加载（直接从 planning 目录）
            planning_dir = Path(paths.get("writing_plans_dir", novel_base / "planning"))
            if planning_dir.exists():
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
                
                for plan_file in plan_files:
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan_data = json.load(f)
                        # 确保plan_data是字典类型
                        if isinstance(plan_data, dict):
                            stage_writing_plan = plan_data.get("stage_writing_plan", {})
                            # 确保stage_writing_plan也是字典类型
                            if isinstance(stage_writing_plan, dict):
                                stage_name = stage_writing_plan.get("stage_name", "unknown")
                            else:
                                stage_name = "unknown"
                        else:
                            stage_name = "unknown"
                        quality_data["writing_plans"][stage_name] = plan_data
                        logger.info(f"✅ 已加载写作计划: {plan_file.name}")

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
            target_chapters = (
                data.get("current_progress", {}).get("total_chapters") or
                data.get("total_chapters") or
                completed_chapters
            )
            
            # 获取核心设定和简介
            creative_seed = data.get("creative_seed", {})
            core_setting = creative_seed.get("coreSetting", "") if isinstance(creative_seed, dict) else str(creative_seed)[:200]
            synopsis = data.get("novel_synopsis", "") or data.get("synopsis", "")
            
            projects.append({
                "title": title,
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
                "synopsis": synopsis  # 保留向后兼容
            })
        return sorted(projects, key=lambda x: x["last_updated"], reverse=True)

    def get_novel_detail(self, title: str) -> Optional[Dict[str, Any]]:
        """获取小说详情，并标准化字段名以兼容前端"""
        novel_data = self.novel_projects.get(title)
        if not novel_data:
            return None
        
        # 标准化字段名，确保前端能正确读取
        standardized_data = {
            # 保留所有原始字段
            **novel_data,
            
            # 添加前端期望的字段名映射
            "story_synopsis": novel_data.get("novel_synopsis", "") or novel_data.get("synopsis", ""),
            "core_setting": novel_data.get("creative_seed", {}).get("coreSetting", ""),
        }
        
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
            self._update_task_status(task_id, "generating", 10)
            
            logger.info(f"任务 {task_id}: 🚀 开始第一阶段设定生成")
            logger.info(f"任务 {task_id}: 📋 配置参数: {json.dumps(config, ensure_ascii=False, indent=2)}")
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: ❌ 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            logger.info(f"任务 {task_id}: ✅ 创意种子检查通过")
            logger.info(f"任务 {task_id}: 📄 创意种子类型: {type(creative_seed)}")
            logger.info(f"任务 {task_id}: 📄 创意种子大小: {len(str(creative_seed))} 字符")
            
            # 初始化NovelGenerator
            logger.info(f"任务 {task_id}: 🔧 初始化 NovelGenerator...")
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
                
                logger.info(f"任务 {task_id}: 📋 生成器配置: {json.dumps(generator_config, ensure_ascii=False, indent=2)}")
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                logger.info(f"任务 {task_id}: ✅ NovelGenerator 实例创建成功")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 创建 NovelGenerator 失败: {e}")
                logger.error(f"任务 {task_id}: 📋 错误详情: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            logger.info(f"任务 {task_id}: 📚 开始第一阶段设定，计划{total_chapters}章")
            
            # 更新进度
            logger.info(f"任务 {task_id}: 🔧 初始化生成器 (20%)")
            self._update_task_status(task_id, "generating", 20)
            
            logger.info(f"任务 {task_id}: 📋 分析创意种子 (40%)")
            self._update_task_status(task_id, "generating", 40)
            
            logger.info(f"任务 {task_id}: 📝 生成方案 (60%)")
            self._update_task_status(task_id, "generating", 60)
            
            logger.info(f"任务 {task_id}: 🚀 调用 phase_one_generation 方法...")
            
            # 执行第一阶段生成
            logger.info(f"任务 {task_id}: 📝 开始第一阶段设定生成 (70%)")
            self._update_task_status(task_id, "generating", 70)
            
            try:
                # 为生成器设置进度回调（使用动态属性设置）
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                success = novel_generator.phase_one_generation(creative_seed, total_chapters)
                logger.info(f"任务 {task_id}: ✅ phase_one_generation 完成，返回结果: {success}")
                
                if success:
                    logger.info(f"任务 {task_id}: 🎉 第一阶段设定生成成功！")
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
                    logger.info(f"任务 {task_id}: 🔍 重新加载项目数据...")
                    try:
                        self.load_existing_novels()
                        logger.info(f"任务 {task_id}: ✅ 项目数据重新加载完成")
                    except Exception as e:
                        logger.info(f"任务 {task_id}: ⚠️ 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: ❌ 第一阶段设定生成失败")
                    self._update_task_status(task_id, "failed", 0, "第一阶段设定生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ phase_one_generation 执行异常: {e}")
                logger.error(f"任务 {task_id}: 📋 错误类型: {type(e).__name__}")
                logger.error(f"任务 {task_id}: 📋 错误详情: {str(e)}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"第一阶段生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 🔥 第一阶段生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def _run_generation_task(self, task_id: str, config: Dict[str, Any]):
        """执行完整生成任务（兼容原有逻辑）"""
        try:
            self._update_task_status(task_id, "generating", 10)
            
            logger.info(f"任务 {task_id}: 🚀 开始实际小说生成")
            logger.info(f"任务 {task_id}: 📋 配置参数: {json.dumps(config, ensure_ascii=False, indent=2)}")
            
            # 检查创意种子
            creative_seed = config.get("creative_seed", {})
            if not creative_seed:
                logger.error(f"任务 {task_id}: ❌ 创意种子为空")
                self._update_task_status(task_id, "failed", 0, "创意种子为空")
                return
            
            logger.info(f"任务 {task_id}: ✅ 创意种子检查通过")
            logger.info(f"任务 {task_id}: 📄 创意种子类型: {type(creative_seed)}")
            logger.info(f"任务 {task_id}: 📄 创意种子大小: {len(str(creative_seed))} 字符")
            
            # 初始化NovelGenerator
            logger.info(f"任务 {task_id}: 🔧 初始化 NovelGenerator...")
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
                
                logger.info(f"任务 {task_id}: 📋 生成器配置: {json.dumps(generator_config, ensure_ascii=False, indent=2)}")
                
                # 创建生成器实例
                novel_generator = NovelGenerator(generator_config)
                logger.info(f"任务 {task_id}: ✅ NovelGenerator 实例创建成功")
                
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ 创建 NovelGenerator 失败: {e}")
                logger.error(f"任务 {task_id}: 📋 错误详情: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"创建生成器失败: {str(e)}")
                return
            
            total_chapters = config.get("total_chapters", 200)
            logger.info(f"任务 {task_id}: 📚 开始生成 {total_chapters} 章")
            
            # 更新进度 - 修复：只在真正完成阶段时更新进度
            logger.info(f"任务 {task_id}: 🔧 初始化生成器 (20%)")
            self._update_task_status(task_id, "generating", 20)
            
            logger.info(f"任务 {task_id}: 📋 分析创意种子 (40%)")
            self._update_task_status(task_id, "generating", 40)
            
            logger.info(f"任务 {task_id}: 📝 生成方案 (60%)")
            self._update_task_status(task_id, "generating", 60)
            
            logger.info(f"任务 {task_id}: 🚀 调用 full_auto_generation 方法...")
            
            # 在实际生成过程中动态更新进度
            logger.info(f"任务 {task_id}: 📝 开始实际章节生成 (70%)")
            self._update_task_status(task_id, "generating", 70)
            
            try:
                # 为生成器设置进度回调（使用动态属性设置）
                setattr(novel_generator, '_update_task_status_callback', self._update_task_status)
                setattr(novel_generator, '_current_task_id', task_id)
                
                success = novel_generator.full_auto_generation(creative_seed, total_chapters)
                logger.info(f"任务 {task_id}: ✅ full_auto_generation 完成，返回结果: {success}")
                
                if success:
                    logger.info(f"任务 {task_id}: 🎉 小说生成成功！")
                    self._update_task_status(task_id, "completed", 100)
                    
                    # 重新加载项目数据以获取最新状态
                    logger.info(f"任务 {task_id}: 🔍 重新加载项目数据...")
                    try:
                        self.load_existing_novels()
                        logger.info(f"任务 {task_id}: ✅ 项目数据重新加载完成")
                        
                        # 检查是否真的生成了文件
                        self._check_generated_files(task_id, config)
                        
                    except Exception as e:
                        logger.info(f"任务 {task_id}: ⚠️ 重新加载项目数据失败: {e}")
                
                else:
                    logger.error(f"任务 {task_id}: ❌ 小说生成失败")
                    self._update_task_status(task_id, "failed", 0, "小说生成返回 False")
                    
            except Exception as e:
                logger.error(f"任务 {task_id}: ❌ full_auto_generation 执行异常: {e}")
                logger.error(f"任务 {task_id}: 📋 错误类型: {type(e).__name__}")
                logger.error(f"任务 {task_id}: 📋 错误详情: {str(e)}")
                import traceback
                traceback.print_exc()
                self._update_task_status(task_id, "failed", 0, f"生成过程异常: {str(e)}")
            
        except Exception as e:
            logger.error(f"任务 {task_id}: 🔥 生成任务发生未捕获的异常: {e}")
            import traceback
            traceback.print_exc()
            self._update_task_status(task_id, "failed", 0, f"未捕获的异常: {str(e)}")

    def _check_generated_files(self, task_id: str, config: Dict[str, Any]):
        """检查是否真的生成了小说文件"""
        try:
            logger.info(f"任务 {task_id}: 🔍 检查生成的小说文件...")
            
            # 获取小说标题（从配置或创意种子）
            novel_title = config.get("title") or config.get("creative_seed", {}).get("novelTitle", "未命名小说")
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 检查项目目录
            project_dir = Path("小说项目")
            if not project_dir.exists():
                logger.info(f"任务 {task_id}: ⚠️ 小说项目目录不存在: {project_dir}")
                return False
            
            # 检查具体的小说文件 - 优先使用新路径
            novel_dir = project_dir / safe_title / "chapters"
            if not novel_dir.exists():
                novel_dir = project_dir / f"{safe_title}_章节"
            
            if novel_dir.exists():
                chapter_files = list(novel_dir.glob("*.txt"))
                logger.info(f"任务 {task_id}: 📚 找到 {len(chapter_files)} 个章节文件")
                
                # 检查文件内容是否为空
                empty_files = 0
                for file_path in chapter_files:
                    if file_path.stat().st_size == 0:
                        empty_files += 1
                
                if empty_files > 0:
                    logger.info(f"任务 {task_id}: ⚠️ 发现 {empty_files} 个空章节文件")
                
                # 统计生成的总字数
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
                
                logger.info(f"任务 {task_id}: 📊 生成总字数: {total_words} 字")
                logger.info(f"任务 {task_id}: ✅ 文件检查完成")
                return True
                
            else:
                logger.info(f"任务 {task_id}: ⚠️ 章节目录不存在: {novel_dir}")
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
            
            # 加载第一阶段数据 (30%)
            self._update_task_status(task_id, "preparing", 30)
            
            try:
                # 设置进度回调 - 用于在生成过程中动态更新进度
                setattr(novel_generator, '_phase_two_progress_callback', update_phase_two_progress)
                setattr(novel_generator, '_phase_two_from_chapter', from_chapter)
                setattr(novel_generator, '_phase_two_total_chapters', chapters_to_generate)
                
                success = novel_generator.phase_two_generation(
                    phase_one_file,
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