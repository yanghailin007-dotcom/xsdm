"""
网页展示服务 - 小说生成过程可视化平台
Web Display Service for Novel Generation Process Visualization
"""

import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import tempfile
import uuid
import hashlib
from functools import wraps

from flask import Flask, render_template, jsonify, request, send_from_directory, session, redirect, url_for
from flask_cors import CORS

# 获取项目根目录 - 使用resolve()确保绝对路径
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# 改变工作目录到项目根目录
os.chdir(BASE_DIR)

from src.utils.logger import get_logger
from src.core.NovelGenerator import NovelGenerator
from config.config import CONFIG
from src.core.Contexts import GenerationContext
from src.utils.DouBaoImageGenerator import DouBaoImageGenerator

logger = get_logger("WebServer")

# 启用模拟API客户端以加快测试（可通过环境变量USE_MOCK_API控制）
USE_MOCK_API = os.getenv("USE_MOCK_API", "true").lower() == "true"
CONFIG["use_mock_api"] = USE_MOCK_API

if USE_MOCK_API:
    logger.info("🎭 Web服务使用模拟API客户端（快速测试模式）")
else:
    logger.info("🌐 Web服务使用真实API客户端")

# 创意文件路径
CREATIVE_IDEAS_FILE = str(BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt")

# Flask应用 - 使用正确的路径
# 确保使用绝对路径并验证路径存在
template_dir = BASE_DIR / "web" / "templates"
static_dir = BASE_DIR / "web" / "static"

# 验证路径存在
if not template_dir.exists():
    raise RuntimeError(f"Templates directory not found: {template_dir}")
if not static_dir.exists():
    raise RuntimeError(f"Static directory not found: {static_dir}")

logger.info(f"📁 Template folder: {template_dir}")
logger.info(f"📁 Static folder: {static_dir}")

app = Flask(
    __name__,
    template_folder=str(template_dir.resolve()),
    static_folder=str(static_dir.resolve())
)
CORS(app)

# 配置 Flask session
app.secret_key = 'yang-novel-generator-secret-key-2024'  # 生产环境应使用更安全的密钥
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # session 有效期24小时

# 用户认证系统
class UserAuth:
    """简单的用户认证系统"""

    def __init__(self):
        # 默认用户：用户名 yang，密码 yang
        self.users = {
            'yang': self._hash_password('yang'),
            'test': self._hash_password('test'),  # 添加测试用户
            'admin': self._hash_password('admin'),  # 添加管理员用户
            '': self._hash_password('')  # 添加空密码用户（测试模式）
        }
        logger.info("🔐 用户认证系统已初始化")
        logger.info(f"📝 默认用户: yang / yang, test / test, admin / admin, 空用户名 / 空密码")

    def _hash_password(self, password: str) -> str:
        """使用 SHA256 哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_user(self, username: str, password: str) -> bool:
        """验证用户名和密码"""
        if username not in self.users:
            return False
        return self.users[username] == self._hash_password(password)

    def add_user(self, username: str, password: str) -> bool:
        """添加新用户"""
        if username in self.users:
            return False
        self.users[username] = self._hash_password(password)
        return True

# 初始化用户认证
user_auth = UserAuth()

# 登录装饰器
def login_required(f):
    """要求登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            # 如果是 API 请求，返回 JSON 错误
            if request.path.startswith('/api/'):
                return jsonify({'error': '未登录', 'redirect': '/login'}), 401
            # 如果是页面请求，重定向到登录页
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 全局状态管理
class NovelGenerationManager:
    """小说生成管理器 - 集成真实的NovelGenerator"""

    def __init__(self):
        self.generators = {}  # 存储不同任务的generator实例
        self.active_tasks = {}  # 存储正在执行的后台任务
        self.task_results = {}  # 存储任务结果
        self.task_progress = {}  # 存储任务进度
        self.novel_projects = {}  # 存储小说项目数据

        # 启动时加载已存在的小说项目
        self.load_existing_novels()

    def start_generation(self, novel_config: Dict[str, Any]) -> str:
        """开始生成小说"""
        task_id = str(uuid.uuid4())

        # 检查是否允许覆盖
        overwrite = novel_config.get("overwrite", False)
        title = novel_config.get('title', '未命名')

        logger.info(f"🚀 启动生成任务: {task_id} - {title}")
        if overwrite:
            logger.info(f"⚠️ 覆盖模式已启用")

        # 创建任务记录
        self.task_results[task_id] = {
            "task_id": task_id,
            "title": novel_config.get("title", "新建小说"),
            "synopsis": novel_config.get("synopsis", ""),
            "core_setting": novel_config.get("core_setting", ""),
            "core_selling_points": novel_config.get("core_selling_points", []),
            "total_chapters": novel_config.get("total_chapters", 50),
            "overwrite": overwrite,  # 新增：存储覆盖设置
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "initializing",
            "progress": 0,
            "chapters_generated": [],
            "error": None
        }

        # 启动后台生成任务
        thread = threading.Thread(
            target=self._run_generation_task,
            args=(task_id, novel_config),
            daemon=True
        )
        self.active_tasks[task_id] = thread
        thread.start()

        return task_id

    def _run_generation_task(self, task_id: str, novel_config: Dict[str, Any]):
        """运行生成任务（后台线程）"""
        try:
            logger.info(f"🚀 开始运行生成任务: {task_id}")
            
            # 更新状态为生成中
            self._update_task_status(task_id, "generating", 5)

            # 创建NovelGenerator实例
            logger.info(f"📦 创建NovelGenerator实例...")
            generator = NovelGenerator(CONFIG)
            self.generators[task_id] = generator

            # 更新进度：准备生成器
            self._update_task_status(task_id, "generator_ready", 10)

            # 准备创意种子
            logger.info(f"📝 准备创意种子...")
            creative_seed = self._prepare_creative_seed(novel_config)
            self._update_task_status(task_id, "creative_ready", 15)

            logger.info(f"✅ 创意种子准备完成，开始调用full_auto_generation...")
            logger.info(f"   - total_chapters: {novel_config.get('total_chapters', 50)}")
            logger.info(f"   - creative_seed type: {type(creative_seed)}")
            
            # 开始生成
            total_chapters = novel_config.get("total_chapters", 50)
            overwrite = novel_config.get("overwrite", False)  # 获取覆盖设置 (当前未使用,保留以备将来)
            
            logger.info(f"🎯 调用 generator.full_auto_generation...")
            logger.info(f"   - creative_seed type: {type(creative_seed)}")
            if isinstance(creative_seed, dict):
                logger.info(f"   - creative_seed keys: {list(creative_seed.keys())}")
                logger.info(f"   - coreSetting: {creative_seed.get('coreSetting', '')[:100]}...")
            else:
                logger.info(f"   - creative_seed content: {str(creative_seed)[:200]}...")
            
            success = generator.full_auto_generation(creative_seed, total_chapters)
            
            logger.info(f"🏁 full_auto_generation 返回: {success}")

            if success:
                # 保存生成结果
                novel_data = generator.novel_data
                self.task_results[task_id].update({
                    "status": "completed",
                    "progress": 100,
                    "novel_data": novel_data,
                    "chapters_generated": list(novel_data.get("generated_chapters", {}).keys()),
                    "completion_time": datetime.now().isoformat()
                })

                # 保存到项目集合中
                self.novel_projects[novel_data.get("novel_title", f"项目_{task_id}")] = novel_data

                logger.info(f"✅ 生成任务完成: {task_id}")
            else:
                raise Exception("Novel generation failed")

        except Exception as e:
            logger.error(f"❌ 生成任务失败: {task_id} - {e}")
            import traceback
            error_detail = traceback.format_exc()
            logger.error(f"详细错误: {error_detail}")

            # 提取更友好的错误信息
            error_msg = str(e)
            if "'str' object has no attribute 'get'" in error_msg:
                detailed_error = f"数据格式错误: 期望字典但收到字符串 - {error_msg}"
            elif "ModuleNotFoundError" in error_msg:
                detailed_error = f"模块缺失错误 - {error_msg}"
            elif "AttributeError" in error_msg:
                detailed_error = f"属性访问错误 - {error_msg}"
            else:
                detailed_error = f"{error_msg}"

            logger.error(f"用户友好错误: {detailed_error}")

            # 创建调试报告
            debug_info = {
                "task_id": task_id,
                "error_type": type(e).__name__,
                "error_message": error_msg,
                "detailed_error": detailed_error,
                "traceback": error_detail,
                "config_received": novel_config
            }

            # 保存调试信息到文件
            import json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"debug_task_{task_id}_{timestamp}.json"

            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(debug_info, f, ensure_ascii=False, indent=2)
                logger.info(f"调试信息已保存到: {debug_file}")
            except Exception as save_error:
                logger.error(f"保存调试信息失败: {save_error}")

            self._update_task_status(task_id, "failed", 0, detailed_error)
        finally:
            # 清理活动任务
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]

    def _prepare_creative_seed(self, novel_config: Dict[str, Any]) -> Any:
        """准备创意种子数据 - 修复数据类型传递问题"""
        # 检查是否有从创意文件传入的完整创意数据
        if novel_config.get("use_creative_file") and novel_config.get("creative_seed"):
            # 直接使用创意文件中的数据
            creative_data = novel_config["creative_seed"]
            # Defensive normalization: ensure we return a dict
            from src.utils.seed_utils import ensure_seed_dict
            creative_data = ensure_seed_dict(creative_data)
            
            # 返回字典格式，而不是字符串格式，这样NovelGenerator可以直接处理
            return creative_data

        # 原有逻辑：从表单输入构建创意种子字典
        core_setting = novel_config.get("core_setting", "")
        core_selling_points = novel_config.get("core_selling_points", [])
        synopsis = novel_config.get("synopsis", "")
        
        # 处理core_selling_points，确保它是列表格式
        if isinstance(core_selling_points, str):
            core_selling_points = [sp.strip() for sp in core_selling_points.split(",") if sp.strip()]
        
        # 构建创意种子字典，符合NovelGenerator的期望格式
        creative_seed_dict = {
            "coreSetting": core_setting,
            "coreSellingPoints": core_selling_points,
            "completeStoryline": {
                "opening": {
                    "stageName": "开局阶段",
                    "summary": f"故事开始于{synopsis}",
                    "arc_goal": "建立主角形象和初始冲突"
                },
                "development": {
                    "stageName": "发展阶段",
                    "summary": "故事发展",
                    "arc_goal": "推进主线情节"
                },
                "climax": {
                    "stageName": "高潮阶段",
                    "summary": "故事高潮",
                    "arc_goal": "解决核心冲突"
                },
                "ending": {
                    "stageName": "结局阶段",
                    "summary": "故事结局",
                    "arc_goal": "完成故事闭环"
                }
            },
            "targetAudience": "网文读者",
            "novelTitle": novel_config.get("title", "未命名小说"),
            "themes": [],
            "writingStyle": "现代网文风格"
        }
        
        return creative_seed_dict

    def _update_task_status(self, task_id: str, status: str, progress: int, error: str = None):
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
        """从文件系统加载已存在的小说项目"""
        try:
            novel_dir = Path("小说项目")
            if not novel_dir.exists():
                logger.info("📁 小说项目目录不存在，将在首次生成时创建")
                return

            logger.info("🔍 扫描已存在的小说项目...")

            # 遍历小说项目目录
            for item in novel_dir.iterdir():
                if item.is_file() and item.name.endswith("_项目信息.json"):
                    # 提取小说标题
                    title = item.name.replace("_项目信息.json", "")
                    project_file = item

                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            novel_data = json.load(f)

                        # 检查章节目录并加载章节信息
                        chapter_dir = novel_dir / f"{title}_章节"
                        generated_chapters = {}

                        if chapter_dir.exists():
                            for chapter_file in chapter_dir.glob("第*.txt"):
                                # 提取章节号
                                try:
                                    chapter_num = int(chapter_file.name.split("章")[0].replace("第", ""))
                                    with open(chapter_file, 'r', encoding='utf-8') as cf:
                                        file_content = cf.read()

                                    # 尝试解析JSON文件并提取内容
                                    try:
                                        chapter_json = json.loads(file_content)
                                        chapter_content = chapter_json.get("content", file_content)
                                        chapter_title = chapter_json.get("chapter_title", chapter_file.name.replace(".txt", "").split("_", 1)[-1])
                                        chapter_word_count = chapter_json.get("word_count", len(chapter_content))

                                        # 添加调试日志
                                        if "quality_assessment" in chapter_json:
                                            logger.info(f"🔍 {title} 第{chapter_num}章 - JSON格式，包含质量评估数据")
                                        else:
                                            logger.info(f"📄 {title} 第{chapter_num}章 - JSON格式，无质量评估数据")
                                    except json.JSONDecodeError:
                                        # 如果不是JSON格式，直接使用原始内容
                                        chapter_content = file_content
                                        chapter_title = chapter_file.name.replace(".txt", "").split("_", 1)[-1]
                                        chapter_word_count = len(chapter_content)
                                        logger.info(f"📝 {title} 第{chapter_num}章 - 纯文本格式")

                                    generated_chapters[chapter_num] = {
                                        "chapter_number": chapter_num,
                                        "title": chapter_title,
                                        "content": chapter_content,
                                        "word_count": chapter_word_count,
                                        "file_path": str(chapter_file)
                                    }
                                except Exception as e:
                                    logger.info(f"⚠️ 加载章节 {chapter_file.name} 失败: {e}")

                        # 更新小说数据
                        novel_data["generated_chapters"] = generated_chapters
                        novel_data["creation_time"] = novel_data.get("creation_time", datetime.now().isoformat())

                        # 加载质量数据
                        quality_data = self.load_quality_data(title)
                        novel_data["quality_data"] = quality_data

                        # 添加到项目集合
                        self.novel_projects[title] = novel_data
                        logger.info(f"✅ 加载小说项目: {title} ({len(generated_chapters)} 章)")

                    except Exception as e:
                        logger.error(f"❌ 加载项目文件 {project_file} 失败: {e}")

            logger.info(f"📚 总共加载了 {len(self.novel_projects)} 个小说项目")

        except Exception as e:
            logger.error(f"❌ 加载已存在小说项目失败: {e}")

    def load_quality_data(self, title: str) -> Dict[str, Any]:
        """加载小说的质量数据"""
        quality_data = {
            "character_development": {},
            "world_state": {},
            "events": [],
            "writing_plans": {},
            "relationships": {},
            "chapter_failures": []
        }

        try:
            # 基础路径
            quality_base = Path("quality_data")
            chapter_base = Path("chapter_failures")

            # 加载角色发展数据
            character_file = quality_base / f"{title}_character_development.json"
            if character_file.exists():
                with open(character_file, 'r', encoding='utf-8') as f:
                    quality_data["character_development"] = json.load(f)

            # 加载世界观数据
            world_file = quality_base / f"{title}_world_state.json"
            if world_file.exists():
                with open(world_file, 'r', encoding='utf-8') as f:
                    quality_data["world_state"] = json.load(f)

            # 加载事件数据
            events_file = quality_base / f"{title}_events.json"
            if events_file.exists():
                with open(events_file, 'r', encoding='utf-8') as f:
                    quality_data["events"] = json.load(f)

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

            # 加载写作计划
            for plan_file in (quality_base / "plans").glob(f"{title.replace(':', '').replace('，', '')}*_writing_plan.json"):
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                    stage_name = plan_data.get("stage_writing_plan", {}).get("stage_name", "unknown")
                    quality_data["writing_plans"][stage_name] = plan_data

            # 加载关系数据
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
            projects.append({
                "title": title,
                "total_chapters": data.get("current_progress", {}).get("total_chapters", 0),
                "completed_chapters": len(data.get("generated_chapters", {})),
                "created_at": data.get("creation_time", datetime.now().isoformat()),
                "last_updated": data.get("current_progress", {}).get("last_updated", "")
            })
        return sorted(projects, key=lambda x: x["last_updated"], reverse=True)

    def get_novel_detail(self, title: str) -> Optional[Dict[str, Any]]:
        """获取小说详情"""
        return self.novel_projects.get(title)

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
            if character_data:
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
            chapter_events = [event for event in all_events if event.get("chapter_number") == chapter_num]
            quality_data["events"] = chapter_events

            # 获取章节失败记录
            chapter_failures = project_quality.get("chapter_failures", {}).get(chapter_num, [])
            quality_data["chapter_failures"] = chapter_failures

            # 获取当前章节的写作计划
            writing_plans = project_quality.get("writing_plans", {})
            for stage_name, plan_data in writing_plans.items():
                chapter_range = plan_data.get("stage_writing_plan", {}).get("chapter_range", "")
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

# 创建全局管理器实例
manager = NovelGenerationManager()

# ==================== 认证路由 ====================

@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面和登录处理"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        username = (data.get('username') or '').strip() if data else ''
        password = data.get('password') or '' if data else ''

        # 特殊处理：如果用户名是 "test"，允许空密码或任意密码登录（测试模式）
        if username.lower() == 'test':
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            logger.info(f"✅ 测试用户登录成功: {username} (密码: {'空' if not password else '***'})")

            if request.is_json:
                return jsonify({'success': True, 'message': '测试用户登录成功'})
            return redirect(url_for('index'))

        # 正常验证流程
        if user_auth.verify_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            logger.info(f"✅ 用户登录成功: {username}")

            if request.is_json:
                return jsonify({'success': True, 'message': '登录成功'})
            return redirect(url_for('index'))
        else:
            logger.info(f"❌ 登录失败: {username}")
            if request.is_json:
                return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
            return render_template('login.html', error='用户名或密码错误')

    # GET 请求 - 显示登录页面
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    """登出"""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"👋 用户登出: {username}")
    return redirect(url_for('login'))

# ==================== API 路由 ====================

@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/start-generation', methods=['POST'])
@login_required
def start_generation():
    """开始生成小说"""
    try:
        config = request.json or {}
        task_id = manager.start_generation(config)
        logger.info(f"✅ 生成任务已启动: {task_id}")
        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "小说生成任务已启动，正在后台处理",
            "status": "started"
        })
    except Exception as e:
        logger.error(f"❌ 启动生成任务失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """获取任务状态"""
    try:
        status = manager.get_task_status(task_id)
        return jsonify(status)
    except Exception as e:
        logger.error(f"❌ 获取任务状态失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/task/<task_id>/progress', methods=['GET'])
def get_task_progress(task_id):
    """获取任务进度"""
    try:
        progress = manager.get_task_progress(task_id)
        return jsonify(progress)
    except Exception as e:
        logger.error(f"❌ 获取任务进度失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_all_tasks():
    """获取所有任务"""
    try:
        tasks = manager.get_all_tasks()
        return jsonify(tasks)
    except Exception as e:
        logger.error(f"❌ 获取任务列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-chapters', methods=['POST'])
def generate_chapters_legacy():
    """兼容性端点：生成章节（使用新的后台任务系统）"""
    try:
        data = request.json or {}

        # 使用新的启动系统
        task_id = manager.start_generation(data)

        logger.info(f"✅ 生成任务已启动: {task_id}")

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": "小说生成已启动，使用新版本后台处理系统",
            "note": "请使用 /api/task/{task_id}/status 获取实时状态"
        })

    except Exception as e:
        logger.error(f"❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

# 小说项目管理 API
@app.route('/api/projects', methods=['GET'])
def get_novel_projects():
    """获取所有小说项目"""
    try:
        projects = manager.get_novel_projects()
        # 为每个项目添加状态信息
        for project in projects:
            total_chapters = project.get("total_chapters", 0)
            completed_chapters = project.get("completed_chapters", 0)
            if completed_chapters >= total_chapters and total_chapters > 0:
                project["status"] = "completed"
            elif completed_chapters > 0:
                project["status"] = "generating"
            else:
                project["status"] = "paused"
        return jsonify(projects)
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard-stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """获取仪表板统计数据"""
    try:
        projects = manager.get_novel_projects()
        
        total_projects = len(projects)
        total_chapters = sum(p.get("completed_chapters", 0) for p in projects)
        total_words = 0
        completed_projects = 0
        active_tasks = 0
        
        # 计算总字数和完成项目数
        for project in projects:
            total_words += project.get("word_count", 0)
            project_total_chapters = project.get("total_chapters", 0)
            project_completed_chapters = project.get("completed_chapters", 0)
            
            if project_completed_chapters >= project_total_chapters and project_total_chapters > 0:
                completed_projects += 1
        
        # 获取活动任务数
        active_tasks = len([task for task in manager.get_all_tasks()
                           if task.get("status") in ["initializing", "generating", "generator_ready", "creative_ready"]])
        
        return jsonify({
            "total_projects": total_projects,
            "total_chapters": total_chapters,
            "total_words": total_words,
            "completed_projects": completed_projects,
            "active_tasks": active_tasks
        })
    except Exception as e:
        logger.error(f"❌ 获取统计数据失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<title>', methods=['GET'])
def get_novel_detail(title):
    """获取小说详情"""
    try:
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"error": "小说不存在"}), 404
        
        # 标准化数据结构，确保前端能够正确获取核心设定信息
        standardized_detail = standardize_novel_data_structure(novel_detail)
        
        return jsonify(standardized_detail)
    except Exception as e:
        logger.error(f"❌ 获取小说详情失败: {e}")
        return jsonify({"error": str(e)}), 500

def standardize_novel_data_structure(novel_data):
    """标准化小说数据结构，确保前端能够正确获取核心设定信息"""
    
    # 创建标准化的数据结构
    standardized = {
        # 保留原始数据
        **novel_data,
        
        # 添加标准化的核心字段
        "novel_title": (
            novel_data.get("novel_title") or
            novel_data.get("novel_info", {}).get("title") or
            novel_data.get("title", "未命名小说")
        ),
        
        "story_synopsis": (
            novel_data.get("story_synopsis") or
            novel_data.get("novel_info", {}).get("synopsis") or
            novel_data.get("synopsis", "")
        ),
        
        # 标准化创意种子数据
        "creative_seed": (
            novel_data.get("creative_seed") or
            novel_data.get("novel_info", {}).get("creative_seed") or
            {}
        ),
        
        # 标准化核心设定
        "core_setting": (
            novel_data.get("core_setting") or
            extract_core_setting_from_paths(novel_data)
        ),
        
        # 标准化核心卖点
        "core_selling_points": (
            novel_data.get("core_selling_points") or
            extract_selling_points_from_paths(novel_data)
        ),
        
        # 标准化元数据
        "novel_metadata": {
            "coreSetting": (
                novel_data.get("core_setting") or
                extract_core_setting_from_paths(novel_data)
            ),
            "coreSellingPoints": (
                novel_data.get("core_selling_points") or
                extract_selling_points_from_paths(novel_data)
            ),
            "worldview": extract_worldview_from_paths(novel_data),
            "growthPlan": extract_growth_plan_from_paths(novel_data),
            "generation_timestamp": novel_data.get("timestamp", ""),
            **novel_data.get("novel_metadata", {})
        },
        
        # 确保章节数据存在
        "generated_chapters": (
            novel_data.get("generated_chapters") or
            novel_data.get("chapters", {})
        ),
        
        # 确保进度数据存在
        "current_progress": (
            novel_data.get("current_progress") or
            novel_data.get("progress", {})
        ),
        
        # 章节索引
        "chapter_index": (
            novel_data.get("chapter_index") or
            extract_chapter_index_from_paths(novel_data)
        )
    }
    
    # 确保creative_seed包含必要字段
    if not standardized["creative_seed"]:
        standardized["creative_seed"] = {}
    
    # 从selected_plan中提取核心设定到creative_seed
    selected_plan = (
        novel_data.get("selected_plan") or
        novel_data.get("novel_info", {}).get("selected_plan")
    )
    
    if selected_plan:
        if "coreSetting" not in standardized["creative_seed"] and selected_plan.get("core_direction"):
            standardized["creative_seed"]["coreSetting"] = selected_plan["core_direction"]
        
        if "coreSellingPoints" not in standardized["creative_seed"] and selected_plan.get("competitive_advantage"):
            standardized["creative_seed"]["coreSellingPoints"] = selected_plan["competitive_advantage"]
        
        if "completeStoryline" not in standardized["creative_seed"] and selected_plan.get("plot_outline"):
            standardized["creative_seed"]["completeStoryline"] = selected_plan["plot_outline"]
    
    return standardized

def extract_core_setting_from_paths(novel_data):
    """从多个可能路径提取核心设定"""
    paths = [
        ["novel_info", "creative_seed", "coreSetting"],
        ["creative_seed", "coreSetting"],
        ["novel_metadata", "coreSetting"],
        ["core_setting"],
        ["selected_plan", "core_direction"],
        ["novel_info", "selected_plan", "core_direction"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, str) and current.strip():
            return current.strip()
    
    return ""

def extract_selling_points_from_paths(novel_data):
    """从多个可能路径提取核心卖点"""
    paths = [
        ["novel_info", "creative_seed", "coreSellingPoints"],
        ["creative_seed", "coreSellingPoints"],
        ["novel_metadata", "coreSellingPoints"],
        ["core_selling_points"],
        ["selected_plan", "competitive_advantage"],
        ["novel_info", "selected_plan", "competitive_advantage"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current:
            if isinstance(current, list):
                return current
            elif isinstance(current, str) and current.strip():
                return current.strip()
    
    return ""

def extract_worldview_from_paths(novel_data):
    """从多个可能路径提取世界观"""
    paths = [
        ["novel_info", "creative_seed", "worldview"],
        ["creative_seed", "worldview"],
        ["worldview"],
        ["core_worldview", "result"]  # 如果是模拟响应
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, str) and current.strip():
            return current.strip()
    
    return ""

def extract_growth_plan_from_paths(novel_data):
    """从多个可能路径提取成长规划"""
    paths = [
        ["global_growth_plan"],
        ["growth_plan"],
        ["creative_seed", "growthPlan"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current:
            return current
    
    return {}

def extract_chapter_index_from_paths(novel_data):
    """从多个可能路径提取章节索引"""
    paths = [
        ["chapter_index"],
        ["novel_info", "chapter_index"]
    ]
    
    for path in paths:
        current = novel_data
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                current = None
                break
        
        if current and isinstance(current, list):
            return current
    
    # 如果没有章节索引，尝试从generated_chapters生成
    generated_chapters = novel_data.get("generated_chapters", {})
    if generated_chapters and isinstance(generated_chapters, dict):
        chapter_index = []
        for chapter_num, chapter_data in generated_chapters.items():
            if isinstance(chapter_data, dict):
                chapter_index.append({
                    "chapter_number": str(chapter_num),
                    "chapter_title": chapter_data.get("title", f"第{chapter_num}章"),
                    "filename": chapter_data.get("file_path", ""),
                    "quality_score": chapter_data.get("quality_score", 0),
                    "word_count": chapter_data.get("word_count", len(chapter_data.get("content", "")))
                })
        return chapter_index
    
    return []

@app.route('/api/project/<title>/chapter/<int:chapter_num>', methods=['GET'])
def get_chapter_detail(title, chapter_num):
    """获取章节详情"""
    try:
        chapter_detail = manager.get_chapter_detail(title, chapter_num)
        if not chapter_detail:
            return jsonify({"error": "章节不存在"}), 404

        # 获取质量数据
        quality_data = manager.get_chapter_quality_data(title, chapter_num)
        chapter_detail["quality_data"] = quality_data

        return jsonify(chapter_detail)
    except Exception as e:
        logger.error(f"❌ 获取章节详情失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<title>/chapter/<int:chapter_num>/quality', methods=['GET'])
def get_chapter_quality_data(title, chapter_num):
    """获取章节质量数据"""
    try:
        quality_data = manager.get_chapter_quality_data(title, chapter_num)
        return jsonify(quality_data)
    except Exception as e:
        logger.error(f"❌ 获取章节质量数据失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<title>/export', methods=['GET'])
def export_novel(title):
    """导出小说"""
    try:
        format_type = request.args.get('format', 'json')
        result = manager.export_novel(title, format_type)

        if "error" in result:
            return jsonify(result), 400

        if format_type == "text":
            # 下载文本文件
            response = app.response_class(
                result["content"],
                mimetype='text/plain',
                headers={"Content-Disposition": f"attachment; filename={result['title']}.txt"}
            )
            return response
        else:
            return jsonify(result)
    except Exception as e:
        logger.error(f"❌ 导出小说失败: {e}")
        return jsonify({"error": str(e)}), 500

# 兼容性API - 为了保持现有前端功能
@app.route('/api/novel/summary', methods=['GET'])
def get_novel_summary():
    """获取当前小说摘要（兼容性）"""
    try:
        # 获取最新的项目
        projects = manager.get_novel_projects()
        if projects:
            latest_project = projects[0]
            novel_detail = manager.get_novel_detail(latest_project["title"])
            if novel_detail:
                return jsonify({
                    "title": novel_detail.get("novel_title", ""),
                    "synopsis": novel_detail.get("story_synopsis", ""),
                    "chapters_count": len(novel_detail.get("generated_chapters", {})),
                    "total_chapters": novel_detail.get("current_progress", {}).get("total_chapters", 0),
                    "progress": f"{len(novel_detail.get('generated_chapters', {}))}/{novel_detail.get('current_progress', {}).get('total_chapters', 0)}"
                })
        return jsonify({})
    except Exception as e:
        logger.error(f"❌ 获取小说摘要失败: {e}")
        return jsonify({})

@app.route('/api/chapters', methods=['GET'])
def get_chapters_list():
    """获取章节列表（兼容性）"""
    try:
        # 获取最新项目的章节
        projects = manager.get_novel_projects()
        if projects:
            latest_project = projects[0]
            novel_detail = manager.get_novel_detail(latest_project["title"])
            if novel_detail:
                chapters = []
                generated_chapters = novel_detail.get("generated_chapters", {})
                for chapter_num in sorted(generated_chapters.keys()):
                    chapter_data = generated_chapters[chapter_num]
                    chapters.append({
                        "chapter_number": chapter_num,
                        "title": chapter_data.get("outline", {}).get("章节标题", f"第{chapter_num}章"),
                        "word_count": len(chapter_data.get("content", "")),
                        "score": chapter_data.get("assessment", {}).get("整体评分", 0),
                        "status": "completed",
                        "generated_at": chapter_data.get("generation_time", "")
                    })
                return jsonify(chapters)
        return jsonify([])
    except Exception as e:
        logger.error(f"❌ 获取章节列表失败: {e}")
        return jsonify([])

@app.route('/api/chapter/<int:chapter_num>', methods=['GET'])
def get_chapter(chapter_num):
    """获取章节详情（兼容性）"""
    try:
        # 获取最新项目的指定章节
        projects = manager.get_novel_projects()
        if projects:
            latest_project = projects[0]
            chapter_detail = manager.get_chapter_detail(latest_project["title"], chapter_num)
            if chapter_detail:
                return jsonify({
                    "chapter_number": chapter_num,
                    "title": chapter_detail.get("outline", {}).get("章节标题", f"第{chapter_num}章"),
                    "outline": chapter_detail.get("outline", {}),
                    "content": chapter_detail.get("content", ""),
                    "assessment": chapter_detail.get("assessment", {})
                })
        return jsonify({"error": "章节不存在"}), 404
    except Exception as e:
        logger.error(f"❌ 获取章节详情失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/export-json', methods=['GET'])
def export_json():
    """导出为 JSON（兼容性）"""
    try:
        # 获取最新项目
        projects = manager.get_novel_projects()
        if projects:
            latest_project = projects[0]
            novel_detail = manager.get_novel_detail(latest_project["title"])
            if novel_detail:
                return jsonify({
                    "novel": {
                        "title": novel_detail.get("novel_title", ""),
                        "synopsis": novel_detail.get("story_synopsis", ""),
                        "total_chapters": novel_detail.get("current_progress", {}).get("total_chapters", 0),
                        "chapters_generated": len(novel_detail.get("generated_chapters", {}))
                    },
                    "chapters": novel_detail.get("generated_chapters", {}),
                    "exported_at": datetime.now().isoformat()
                })
        return jsonify({"error": "没有找到小说项目"}), 404
    except Exception as e:
        logger.error(f"❌ 导出失败: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== 原始数据API ====================

@app.route('/api/raw-chapter-data', methods=['GET'])
def get_raw_chapter_data():
    """获取原始章节数据"""
    try:
        file_path = request.args.get('file_path')
        if not file_path:
            return jsonify({"error": "缺少file_path参数"}), 400

        # 安全检查：确保文件路径在允许的范围内
        allowed_dirs = [
            str(BASE_DIR / "小说项目"),
            str(BASE_DIR / "chapter_failures"),
            str(BASE_DIR / "quality_data")
        ]
        
        file_path = file_path.lstrip('/\\')
        full_path = BASE_DIR / file_path
        
        # 检查路径安全性
        if not any(str(full_path).startswith(allowed_dir) for allowed_dir in allowed_dirs):
            return jsonify({"error": "文件路径不被允许访问"}), 403

        if not full_path.exists():
            return jsonify({"error": "文件不存在"}), 404

        # 读取文件内容
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 尝试解析为JSON
        try:
            json_data = json.loads(content)
            return jsonify({
                "success": True,
                "file_path": str(full_path),
                "file_size": len(content.encode('utf-8')),
                "content_type": "json",
                "data": json_data
            })
        except json.JSONDecodeError:
            # 如果不是JSON，返回原始文本
            return jsonify({
                "success": True,
                "file_path": str(full_path),
                "file_size": len(content.encode('utf-8')),
                "content_type": "text",
                "data": content
            })

    except Exception as e:
        logger.error(f"❌ 获取原始章节数据失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/quality-data/<title>', methods=['GET'])
def get_quality_data(title):
    """获取小说的质量数据"""
    try:
        quality_data = manager.get_chapter_quality_data(title, 0)  # 获取所有质量数据
        return jsonify({
            "success": True,
            "title": title,
            "quality_data": quality_data
        })
    except Exception as e:
        logger.error(f"❌ 获取质量数据失败: {e}")
        return jsonify({"error": str(e)}), 500

# ==================== 创意文件解析 API ====================

def load_creative_ideas_from_file(file_path: str = None) -> dict:
    """从文件加载创意数据"""
    if file_path is None:
        file_path = CREATIVE_IDEAS_FILE

    try:
        # 获取项目根目录
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(project_root, file_path)

        if not os.path.exists(full_path):
            logger.info(f"创意文件不存在: {full_path}")
            return {"error": f"创意文件不存在: {file_path}"}

        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析JSON格式的创意文件
        creative_data = json.loads(content)
        logger.info(f"✅ 成功加载创意文件: {full_path}")
        return creative_data

    except json.JSONDecodeError as e:
        logger.error(f"❌ 创意文件JSON解析错误: {e}")
        return {"error": f"创意文件JSON格式错误: {str(e)}"}
    except Exception as e:
        logger.error(f"❌ 加载创意文件失败: {e}")
        return {"error": str(e)}

@app.route('/api/creative-ideas', methods=['GET'])
def get_creative_ideas():
    """获取创意文件内容"""
    try:
        creative_data = load_creative_ideas_from_file()

        if "error" in creative_data:
            return jsonify(creative_data), 404

        # 提取创意作品列表
        creative_works = creative_data.get("creativeWorks", [])

        # 格式化为前端友好的格式
        formatted_ideas = []
        for i, work in enumerate(creative_works):
            formatted_idea = {
                "id": i + 1,
                "core_setting": work.get("coreSetting", ""),
                "core_selling_points": work.get("coreSellingPoints", ""),
                "storyline": work.get("completeStoryline", {}),
                "raw_data": work  # 保留原始数据以便传递给生成器
            }

            # 提取故事线阶段名称作为预览
            storyline = work.get("completeStoryline", {})
            stages = []
            for stage_key in ["opening", "development", "conflict", "ending"]:
                if stage_key in storyline:
                    stage_name = storyline[stage_key].get("stageName", stage_key)
                    stages.append(stage_name)
            formatted_idea["stages_preview"] = stages

            formatted_ideas.append(formatted_idea)

        return jsonify({
            "success": True,
            "count": len(formatted_ideas),
            "creative_ideas": formatted_ideas
        })

    except Exception as e:
        logger.error(f"❌ 获取创意列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/creative-ideas/<int:idea_id>', methods=['GET'])
def get_creative_idea_detail(idea_id):
    """获取指定创意的详细信息"""
    try:
        creative_data = load_creative_ideas_from_file()

        if "error" in creative_data:
            return jsonify(creative_data), 404

        creative_works = creative_data.get("creativeWorks", [])

        if idea_id < 1 or idea_id > len(creative_works):
            return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404

        work = creative_works[idea_id - 1]

        # 详细格式化
        detail = {
            "id": idea_id,
            "core_setting": work.get("coreSetting", ""),
            "core_selling_points": work.get("coreSellingPoints", ""),
            "storyline": work.get("completeStoryline", {}),
            "raw_data": work
        }

        return jsonify({
            "success": True,
            "creative_idea": detail
        })

    except Exception as e:
        logger.error(f"❌ 获取创意详情失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/start-generation-from-idea', methods=['POST'])
def start_generation_from_idea():
    """从创意文件中的创意开始生成小说"""
    try:
        data = request.json or {}
        idea_id = data.get("idea_id")
        
        # 修复：确保total_chapters是有效的整数
        total_chapters = data.get("total_chapters", 50)
        if total_chapters is None or total_chapters == "":
            total_chapters = 50
        try:
            total_chapters = int(total_chapters)
            if total_chapters <= 0:
                total_chapters = 50
        except (ValueError, TypeError):
            total_chapters = 50

        if idea_id is None:
            return jsonify({"error": "缺少idea_id参数"}), 400

        # 加载创意数据
        creative_data = load_creative_ideas_from_file()

        if "error" in creative_data:
            return jsonify(creative_data), 404

        creative_works = creative_data.get("creativeWorks", [])

        if idea_id < 1 or idea_id > len(creative_works):
            return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404

        # 获取选定的创意
        selected_idea = creative_works[idea_id - 1]

        # 构建生成配置
        novel_config = {
            "title": f"创意{idea_id}的小说",  # 标题将由生成器根据创意内容生成
            "synopsis": selected_idea.get("coreSetting", "")[:200],
            "core_setting": selected_idea.get("coreSetting", ""),
            "core_selling_points": selected_idea.get("coreSellingPoints", "").split("+") if selected_idea.get("coreSellingPoints") else [],
            "total_chapters": total_chapters,
            "creative_seed": selected_idea,  # 传递完整的创意数据
            "use_creative_file": True
        }

        # 启动生成任务
        task_id = manager.start_generation(novel_config)

        logger.info(f"✅ 从创意ID {idea_id} 启动生成任务: {task_id}")

        return jsonify({
            "success": True,
            "task_id": task_id,
            "message": f"已从创意 #{idea_id} 启动小说生成",
            "idea_preview": {
                "core_setting": selected_idea.get("coreSetting", "")[:100] + "...",
                "selling_points": selected_idea.get("coreSellingPoints", "")
            }
        })

    except Exception as e:
        logger.error(f"❌ 从创意启动生成失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/creative-ideas/<int:idea_id>', methods=['PUT'])
@login_required
def update_creative_idea(idea_id):
    """更新指定创意"""
    try:
        data = request.json or {}
        
        # 验证必需字段
        required_fields = ['coreSetting', 'novelTitle']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"缺少必需字段: {field}"}), 400
        
        # 加载现有创意数据
        creative_data = load_creative_ideas_from_file()
        
        if "error" in creative_data:
            return jsonify(creative_data), 404
        
        creative_works = creative_data.get("creativeWorks", [])
        
        if idea_id < 1 or idea_id > len(creative_works):
            return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404
        
        # 更新创意数据
        updated_idea = creative_works[idea_id - 1]
        
        # 保留原始字段，更新提供的字段
        updated_idea["coreSetting"] = data.get("coreSetting", updated_idea.get("coreSetting", ""))
        updated_idea["novelTitle"] = data.get("novelTitle", updated_idea.get("novelTitle", ""))
        updated_idea["synopsis"] = data.get("synopsis", updated_idea.get("synopsis", ""))
        updated_idea["coreSellingPoints"] = data.get("coreSellingPoints", updated_idea.get("coreSellingPoints", ""))
        updated_idea["totalChapters"] = data.get("totalChapters", updated_idea.get("totalChapters", 50))
        
        # 更新故事线
        if data.get("completeStoryline"):
            updated_idea["completeStoryline"] = data["completeStoryline"]
        
        # 更新时间戳
        updated_idea["lastUpdated"] = datetime.now().isoformat()
        
        # 保存到文件
        try:
            with open(CREATIVE_IDEAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(creative_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 创意ID {idea_id} 更新成功")
            
            return jsonify({
                "success": True,
                "message": f"创意 #{idea_id} 更新成功",
                "updated_idea": {
                    "id": idea_id,
                    "core_setting": updated_idea.get("coreSetting", ""),
                    "novel_title": updated_idea.get("novelTitle", ""),
                    "last_updated": updated_idea.get("lastUpdated")
                }
            })
            
        except Exception as save_error:
            logger.error(f"❌ 保存创意文件失败: {save_error}")
            return jsonify({"error": f"保存失败: {str(save_error)}"}), 500
            
    except Exception as e:
        logger.error(f"❌ 更新创意失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/creative-ideas/<int:idea_id>', methods=['DELETE'])
@login_required
def delete_creative_idea(idea_id):
    """删除指定创意"""
    try:
        # 加载现有创意数据
        creative_data = load_creative_ideas_from_file()
        
        if "error" in creative_data:
            return jsonify(creative_data), 404
        
        creative_works = creative_data.get("creativeWorks", [])
        
        if idea_id < 1 or idea_id > len(creative_works):
            return jsonify({"error": f"创意ID {idea_id} 不存在"}), 404
        
        # 获取要删除的创意信息（用于日志）
        deleted_idea = creative_works[idea_id - 1]
        deleted_title = deleted_idea.get("coreSetting", "未知创意")[:50]
        
        # 从列表中移除创意
        creative_works.pop(idea_id - 1)
        
        # 保存到文件
        try:
            with open(CREATIVE_IDEAS_FILE, 'w', encoding='utf-8') as f:
                json.dump(creative_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 创意ID {idea_id} 删除成功: {deleted_title}...")
            
            return jsonify({
                "success": True,
                "message": f"创意 #{idea_id} 删除成功",
                "deleted_idea": {
                    "id": idea_id,
                    "title_preview": deleted_title
                }
            })
            
        except Exception as save_error:
            logger.error(f"❌ 保存创意文件失败: {save_error}")
            return jsonify({"error": f"保存失败: {str(save_error)}"}), 500
            
    except Exception as e:
        logger.error(f"❌ 删除创意失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==================== 页面路由 ====================

@app.route('/', methods=['GET'])
@login_required
def index():
    """首页 - 小说创意生成入口"""
    logger.info(f"📄 Loading index.html from template folder: {app.template_folder}")
    return render_template('index.html')

@app.route('/novels', methods=['GET'])
@login_required
def novels_view():
    """作品列表页面"""
    return render_template('novels.html')

@app.route('/novel', methods=['GET'])
@login_required
def novel_view():
    """小说阅读页面"""
    return render_template('novel_view.html')

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """仪表板"""
    return render_template('dashboard.html')

@app.route('/test_layout_improvements.html', methods=['GET'])
@login_required
def test_layout_improvements():
    """布局改进测试页面"""
    return send_from_directory('.', 'test_layout_improvements.html')

@app.route('/test_large_modal_fix.html', methods=['GET'])
@login_required
def test_large_modal_fix():
    """大弹窗功能测试页面"""
    return send_from_directory(str(BASE_DIR), 'test_large_modal_fix.html')

# ==================== 封面生成器路由 ====================

@app.route('/cover-generator', methods=['GET'])
@login_required
def cover_generator():
    """小说封面生成器页面"""
    return render_template('cover_generator.html')

# ==================== 封面生成API ====================

@app.route('/api/generate-cover', methods=['POST'])
@login_required
def generate_cover():
    """生成小说封面"""
    try:
        data = request.json or {}
        
        # 验证必需参数
        required_fields = ['novel_title', 'custom_prompt']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    "success": False,
                    "error": f"缺少必需参数: {field}"
                }), 400
        
        # 创建图片生成器实例
        generator = DouBaoImageGenerator()
        
        # 构建最终的提示词
        final_prompt = build_final_prompt(data)
        
        # 生成参数
        generation_count = min(data.get('generation_count', 1), 4)  # 限制最多生成4张
        image_size = data.get('image_size', '1K')
        add_watermark = data.get('add_watermark', False)
        
        logger.info(f"🎨 开始生成封面: {data['novel_title']}")
        logger.info(f"📝 提示词长度: {len(final_prompt)} 字符")
        
        # 批量生成图片
        generated_images = []
        for i in range(generation_count):
            try:
                logger.info(f"正在生成第 {i+1}/{generation_count} 张封面...")
                
                # 生成单张图片
                result = generator.generate_image(
                    prompt=final_prompt,
                    size=image_size,
                    watermark=add_watermark
                )
                
                if result and 'local_path' in result:
                    # 构建图片信息
                    image_info = {
                        "url": result['local_path'],
                        "size": image_size,
                        "timestamp": datetime.now().isoformat(),
                        "prompt": final_prompt,
                        "index": i + 1
                    }
                    generated_images.append(image_info)
                    logger.info(f"✅ 第 {i+1} 张封面生成成功: {result['local_path']}")
                else:
                    logger.info(f"第 {i+1} 张封面生成失败")
                    
            except Exception as e:
                logger.error(f"生成第 {i+1} 张封面时发生错误: {e}")
                # 继续尝试生成其他图片
                continue
        
        if not generated_images:
            return jsonify({
                "success": False,
                "error": "所有图片生成都失败了"
            }), 500
        
        logger.info(f"🎉 封面生成完成: {len(generated_images)} 张成功")
        
        # 返回生成结果
        return jsonify({
            "success": True,
            "message": f"成功生成 {len(generated_images)} 张封面",
            "images": generated_images,
            "params": data
        })
        
    except Exception as e:
        logger.error(f"❌ 生成封面失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": f"生成失败: {str(e)}"
        }), 500

def build_final_prompt(data):
    """构建最终的图片生成提示词"""
    novel_title = data.get('novel_title', '').strip()
    author_name = data.get('author_name', '佚名').strip()
    genre = data.get('genre', '').strip()
    style = data.get('style', '现代简约').strip()
    color_scheme = data.get('color_scheme', 'blue').strip()
    custom_prompt = data.get('custom_prompt', '').strip()
    negative_prompt = data.get('negative_prompt', '').strip()
    
    # 基础提示词模板
    base_prompt = f"""小说封面设计，竖版比例，{style}风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- {style}风格的精美封面设计，符合{genre}类型特点
- 书名要醒目突出，使用清晰易读的字体
- 作者名放在适当位置
- 背景设计基于小说类型和风格要求
- 整体设计专业简洁，符合出版标准
- 色调根据{color_scheme}方案进行搭配

【文字要求】：
- 文字清晰可读但不要过于突兀
- 文字与背景和谐统一
- 只能出现书名和作者"""
    
    # 添加风格和类型特定的描述
    if genre:
        genre_descriptions = {
            '玄幻': '仙侠元素、奇幻场景',
            '都市': '现代都市背景、时尚人物',
            '历史': '古代建筑、传统元素',
            '科幻': '未来科技、太空场景',
            '武侠': '江湖气息、古风元素',
            '悬疑': '神秘氛围、推理元素',
            '游戏': '游戏界面、数字元素'
        }
        if genre in genre_descriptions:
            base_prompt += f"\n- 融入{genre_descriptions[genre]}"
    
    # 添加配色方案描述
    # 简化的配色方案
    colorSchemes = {
        "blue": "蓝色调",
        "red": "红色调",
        "green": "绿色调",
        "purple": "紫色调",
        "gold": "金色调"
    }
    
    if color_scheme in colorSchemes:
        base_prompt += f"\n- 主色调采用{colorSchemes[color_scheme]}"
    
    # 添加自定义提示词
    if custom_prompt:
        base_prompt += f"\n\n【自定义要求】:\n{custom_prompt}"
    
    # 添加负面提示词
    if negative_prompt:
        base_prompt += f"\n\n【严格禁止的内容】：\n{negative_prompt}"
    
    return base_prompt.strip()

# 静态文件服务
@app.route('/static/<path:filename>')
def serve_static(filename):
    """提供静态文件"""
    return send_from_directory('static', filename)

# ==================== 错误处理 ====================

@app.errorhandler(404)
def not_found(error):
    """404 处理"""
    return jsonify({"error": "页面未找到"}), 404

@app.errorhandler(500)
def server_error(error):
    """500 处理"""
    return jsonify({"error": "服务器内部错误"}), 500

# ==================== 启动 ====================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Web 服务启动")
    logger.info("=" * 60)
    logger.info("📱 前端地址: http://localhost:5000")
    logger.info("🌐 API 地址: http://localhost:5000/api")
    logger.info("=" * 60)
    
    # 开发模式运行
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        use_reloader=False
    )
