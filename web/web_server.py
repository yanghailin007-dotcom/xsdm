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
            'yang': self._hash_password('yang')
        }
        logger.info("🔐 用户认证系统已初始化")
        logger.info(f"📝 默认用户: yang / yang")

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
            # 更新状态为生成中
            self._update_task_status(task_id, "generating", 5)

            # 创建NovelGenerator实例
            generator = NovelGenerator(CONFIG)
            self.generators[task_id] = generator

            # 更新进度：准备生成器
            self._update_task_status(task_id, "generator_ready", 10)

            # 准备创意种子
            creative_seed = self._prepare_creative_seed(novel_config)
            self._update_task_status(task_id, "creative_ready", 15)

            # 开始生成
            total_chapters = novel_config.get("total_chapters", 50)
            overwrite = novel_config.get("overwrite", False)  # 获取覆盖设置 (当前未使用,保留以备将来)
            success = generator.full_auto_generation(creative_seed, total_chapters)

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

    def _prepare_creative_seed(self, novel_config: Dict[str, Any]) -> Dict[str, Any]:
        """准备创意种子字典"""
        # 检查是否有从创意文件传入的完整创意数据
        if novel_config.get("use_creative_file") and novel_config.get("creative_seed"):
            # 直接使用创意文件中的数据
            creative_data = novel_config["creative_seed"]
            # Defensive normalization: ensure we return a dict
            from src.utils.seed_utils import ensure_seed_dict
            creative_data = ensure_seed_dict(creative_data)
            return {
                "coreSetting": creative_data.get("coreSetting", ""),
                "coreSellingPoints": creative_data.get("coreSellingPoints", ""),
                "completeStoryline": creative_data.get("completeStoryline", {}),
                "targetAudience": creative_data.get("targetAudience", "网文读者"),
                "novelTitle": novel_config.get("title", "未命名小说"),
                "themes": creative_data.get("themes", []),
                "writingStyle": creative_data.get("writingStyle", "现代网文风格")
            }

        # 原有逻辑：从表单输入构建创意种子
        from src.utils.seed_utils import ensure_seed_dict
        constructed = {
            "coreSetting": novel_config.get("core_setting", ""),
            "coreSellingPoints": ", ".join(novel_config.get("core_selling_points", [])),
            "completeStoryline": {
                "opening": f"故事开始于{novel_config.get('synopsis', '')}",
                "development": "故事发展",
                "climax": "故事高潮",
                "ending": "故事结局"
            },
            "targetAudience": "网文读者",
            "novelTitle": novel_config.get("title", "未命名小说"),
            "themes": [],
            "writingStyle": "现代网文风格"
        }
        return ensure_seed_dict(constructed)

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
                                        chapter_content = cf.read()

                                    generated_chapters[chapter_num] = {
                                        "chapter_number": chapter_num,
                                        "title": chapter_file.name.replace(".txt", "").split("_", 1)[-1],
                                        "content": chapter_content,
                                        "file_path": str(chapter_file)
                                    }
                                except Exception as e:
                                    logger.warning(f"⚠️ 加载章节 {chapter_file.name} 失败: {e}")

                        # 更新小说数据
                        novel_data["generated_chapters"] = generated_chapters
                        novel_data["creation_time"] = novel_data.get("creation_time", datetime.now().isoformat())

                        # 添加到项目集合
                        self.novel_projects[title] = novel_data
                        logger.info(f"✅ 加载小说项目: {title} ({len(generated_chapters)} 章)")

                    except Exception as e:
                        logger.error(f"❌ 加载项目文件 {project_file} 失败: {e}")

            logger.info(f"📚 总共加载了 {len(self.novel_projects)} 个小说项目")

        except Exception as e:
            logger.error(f"❌ 加载已存在小说项目失败: {e}")

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
        username = data.get('username', '').strip()
        password = data.get('password', '')

        if user_auth.verify_user(username, password):
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True
            logger.info(f"✅ 用户登录成功: {username}")

            if request.is_json:
                return jsonify({'success': True, 'message': '登录成功'})
            return redirect(url_for('index'))
        else:
            logger.warning(f"❌ 登录失败: {username}")
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
        return jsonify(projects)
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<title>', methods=['GET'])
def get_novel_detail(title):
    """获取小说详情"""
    try:
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"error": "小说不存在"}), 404
        return jsonify(novel_detail)
    except Exception as e:
        logger.error(f"❌ 获取小说详情失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/project/<title>/chapter/<int:chapter_num>', methods=['GET'])
def get_chapter_detail(title, chapter_num):
    """获取章节详情"""
    try:
        chapter_detail = manager.get_chapter_detail(title, chapter_num)
        if not chapter_detail:
            return jsonify({"error": "章节不存在"}), 404
        return jsonify(chapter_detail)
    except Exception as e:
        logger.error(f"❌ 获取章节详情失败: {e}")
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
            logger.warning(f"创意文件不存在: {full_path}")
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
        total_chapters = data.get("total_chapters", 50)

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

# ==================== 页面路由 ====================

@app.route('/', methods=['GET'])
@login_required
def index():
    """首页"""
    logger.info(f"📄 Loading index.html from template folder: {app.template_folder}")
    return render_template('index.html')

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
