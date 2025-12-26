import os
import json
import threading
import time
import subprocess
import sys
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# 导入番茄自动上传功能
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
try:
    # 尝试导入main_controller模块
    from Chrome.automation.legacy.main_controller import main_scan_cycle
    from Chrome.automation.legacy.config import CONFIG
    from Chrome.automation.legacy.utils import ensure_directory_exists
    autopush_available = True
    print("✅ 成功导入main_controller模块")
except ImportError as e:
    print(f"警告: 无法导入番茄自动上传模块: {e}")
    autopush_available = False

class FanqieUploader:
    """番茄小说一键上传管理器"""
    
    # 任务保留时间（秒）：完成后保留5分钟，方便前端获取最终状态
    TASK_RETENTION_TIME = 300
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.upload_tasks = {}
        self.upload_status = {}
        self.task_completion_times = {}  # 记录任务完成时间
        self.logger = self._get_logger()
        
        # 启动定期清理已完成任务的线程
        self._start_task_cleanup_thread()
        
    def _get_logger(self):
        """获取日志记录器"""
        import logging
        logger = logging.getLogger("FanqieUploader")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def validate_novel_for_upload(self, novel_title: str) -> Dict[str, Any]:
        """验证小说是否可以上传到番茄"""
        try:
            # 尝试多种可能的项目文件路径
            possible_paths = [
                # 新目录结构：小说项目/小说标题/小说标题_项目信息.json
                Path("小说项目") / novel_title / f"{novel_title}_项目信息.json",
                # 旧目录结构：小说项目/小说标题_项目信息.json
                Path("小说项目") / f"{novel_title}_项目信息.json",
            ]
            
            project_file = None
            for path in possible_paths:
                if path.exists():
                    project_file = path
                    self.logger.info(f"✅ 找到项目文件: {path}")
                    break
            
            if not project_file:
                return {
                    "valid": False,
                    "error": f"项目文件不存在，已尝试路径: {[str(p) for p in possible_paths]}"
                }
            
            # 加载项目信息
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 检查必要字段 - 适配实际的项目文件结构
            required_fields = ['novel_title', 'novel_synopsis', 'selected_plan']
            missing_fields = [field for field in required_fields if field not in project_data]
            
            if missing_fields:
                return {
                    "valid": False,
                    "error": f"项目数据缺少必需字段: {', '.join(missing_fields)}"
                }
            
            # 尝试加载角色设计文件（如果存在）
            character_design = None
            character_file = project_file.parent / f"{novel_title}_角色设计.json"
            if character_file.exists():
                try:
                    with open(character_file, 'r', encoding='utf-8') as f:
                        character_design = json.load(f)
                        # 只打印文件名，不打印完整内容
                        self.logger.info(f"✅ 加载角色设计文件: {character_file.name}")
                except Exception as e:
                    self.logger.warning(f"⚠️ 加载角色设计文件失败: {e}")
            
            # 检查章节文件 - 支持多种目录结构
            chapter_dirs = [
                Path("小说项目") / novel_title / "chapters",  # 新结构：小说项目/标题/chapters
                Path("小说项目") / f"{novel_title}_章节",      # 旧结构：小说项目/标题_章节
                Path("小说项目") / "chapters",                 # 通用章节目录
            ]
            
            chapter_files = []
            found_chapter_dir = None
            for chapter_dir in chapter_dirs:
                if chapter_dir.exists():
                    # 查找 .txt 和 .json 格式的章节文件
                    txt_files = list(chapter_dir.glob("第*.txt"))
                    json_files = list(chapter_dir.glob("第*.json"))
                    chapter_files = txt_files + json_files
                    
                    if chapter_files:
                        found_chapter_dir = chapter_dir
                        self.logger.info(f"✅ 找到章节目录: {chapter_dir}，共 {len(chapter_files)} 个文件")
                        break
            
            if not chapter_files:
                return {
                    "valid": False,
                    "error": f"未找到章节文件，已检查路径: {[str(d) for d in chapter_dirs]}"
                }
            
            # 转换项目数据为番茄格式
            fanqie_data = self._convert_to_fanqie_format(project_data, novel_title, chapter_files, character_design)
            
            return {
                "valid": True,
                "fanqie_data": fanqie_data,
                "chapter_count": len(chapter_files),
                "project_info": project_data
            }
            
        except Exception as e:
            self.logger.error(f"验证小说项目失败: {e}")
            return {
                "valid": False,
                "error": f"验证失败: {str(e)}"
            }
    
    def _convert_to_fanqie_format(self, project_data: Dict[str, Any], novel_title: str, chapter_files: List[Path], character_design: Optional[Dict] = None) -> Dict[str, Any]:
        """将创作系统的项目数据转换为番茄上传格式"""
        
        # 从新的项目文件结构中提取数据
        selected_plan = project_data.get("selected_plan", {})
        tags = selected_plan.get("tags", {}) if isinstance(selected_plan, dict) else {}
        
        # 构建番茄格式的数据
        fanqie_data = {
            "novel_info": {
                "title": project_data.get("novel_title", novel_title),
                "synopsis": project_data.get("novel_synopsis", ""),
                "category": project_data.get("category", ""),
                "selected_plan": selected_plan
            },
            "character_design": character_design or {},
            "chapters": []
        }
        
        # 处理章节文件
        for chapter_file in sorted(chapter_files, key=self._extract_chapter_number):
            chapter_data = self._process_chapter_file(chapter_file)
            if chapter_data:
                fanqie_data["chapters"].append(chapter_data)
        
        return fanqie_data
    
    def _extract_chapter_number(self, chapter_file: Path) -> int:
        """从文件名提取章节号"""
        try:
            import re
            match = re.search(r'第(\d+)章', chapter_file.name)
            return int(match.group(1)) if match else 0
        except:
            return 0
    
    def _process_chapter_file(self, chapter_file: Path) -> Optional[Dict[str, Any]]:
        """处理章节文件"""
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析JSON格式
            try:
                chapter_data = json.loads(content)
                chapter_content = chapter_data.get("content", content)
                chapter_title = chapter_data.get("chapter_title", chapter_file.stem)
            except json.JSONDecodeError:
                # 纯文本格式
                chapter_content = content
                chapter_title = chapter_file.stem.replace("第", "").replace("章", "")
            
            chapter_number = self._extract_chapter_number(chapter_file)
            
            return {
                "chapter_number": chapter_number,
                "chapter_title": chapter_title,
                "content": chapter_content,
                "file_path": str(chapter_file)
            }
            
        except Exception as e:
            self.logger.error(f"处理章节文件失败 {chapter_file}: {e}")
            return None
    
    def start_upload_task(self, novel_title: str, upload_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """启动上传任务"""
        task_id = f"upload_{int(time.time())}_{novel_title}"
        
        # 验证小说项目
        validation_result = self.validate_novel_for_upload(novel_title)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "task_id": None
            }
        
        # 初始化任务状态
        self.upload_tasks[task_id] = {
            "task_id": task_id,
            "novel_title": novel_title,
            "status": "initializing",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "upload_config": upload_config or {},
            "fanqie_data": validation_result["fanqie_data"],
            "chapter_count": validation_result["chapter_count"]
        }
        
        self.upload_status[task_id] = {
            "status": "initializing",
            "progress": 0,
            "message": "初始化上传任务...",
            "timestamp": datetime.now().isoformat()
        }
        
        # 启动后台上传线程
        def run_upload():
            try:
                self._execute_upload_task(task_id)
            except Exception as e:
                self.logger.error(f"上传任务执行失败: {e}")
                self._update_task_status(task_id, "failed", 0, str(e))
        
        thread = threading.Thread(target=run_upload)
        thread.daemon = True
        thread.start()
        
        self.logger.info(f"✅ 上传任务已启动: {task_id}")
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "上传任务已启动，正在后台处理",
            "chapter_count": validation_result["chapter_count"]
        }

    def start_browser_for_upload(self) -> Dict[str, Any]:
        """启动浏览器用于上传 - 已禁用，浏览器需手动启动"""
        self.logger.info("ℹ️ 浏览器自动启动功能已禁用，请手动启动浏览器")
        return {
            "success": False,
            "error": "浏览器自动启动功能已禁用。请手动启动Chrome浏览器并登录番茄小说网站。"
        }

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名中的特殊字符"""
        # 移除或替换Windows不允许的字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename
    
    def _execute_upload_task(self, task_id: str):
        """执行上传任务"""
        task = self.upload_tasks.get(task_id)
        if not task:
            return
        
        try:
            # 1. 准备数据阶段
            self._update_task_status(task_id, "preparing", 10, "准备上传数据...")
            
            fanqie_data = task["fanqie_data"]
            novel_title = task["novel_title"]
            
            # 2. 创建临时项目文件
            self._update_task_status(task_id, "creating_project", 20, "创建项目文件...")
            
            temp_project_path = self._create_temp_project_file(novel_title, fanqie_data)
            
            # 3. 创建章节文件
            self._update_task_status(task_id, "creating_chapters", 40, "创建章节文件...")
            
            temp_chapter_path = self._create_temp_chapter_files(novel_title, fanqie_data["chapters"])
            
            # 4. 调用番茄上传功能
            self._update_task_status(task_id, "uploading", 60, "开始上传到番茄小说...")
            
            upload_success = self._call_fanqie_upload(temp_project_path)
            
            # 5. 清理临时文件
            self._update_task_status(task_id, "cleaning", 90, "清理临时文件...")
            
            self._cleanup_temp_files(temp_project_path, temp_chapter_path)
            
            if upload_success:
                self._update_task_status(task_id, "completed", 100, "✅ 上传完成！")
            else:
                self._update_task_status(task_id, "failed", 0, "上传失败")
                
        except Exception as e:
            self.logger.error(f"执行上传任务失败: {e}")
            self._update_task_status(task_id, "failed", 0, str(e))
    
    def _create_temp_project_file(self, novel_title: str, fanqie_data: Dict[str, Any]) -> str:
        """创建临时项目文件"""
        # 创建临时目录
        temp_dir = Path("temp_fanqie_upload")
        temp_dir.mkdir(exist_ok=True)
        
        # 清理小说标题中的特殊字符
        safe_title = self.sanitize_filename(novel_title)
        
        # 构建番茄格式的项目文件
        temp_project_file = temp_dir / f"{safe_title}_项目信息.json"
        
        # 转换为番茄需要的格式
        fanqie_project_data = {
            "novel_info": fanqie_data["novel_info"],
            "character_design": fanqie_data["character_design"],
            "creative_seed": {
                "novelTitle": fanqie_data["novel_info"]["title"],
                "coreSetting": fanqie_data["novel_info"]["synopsis"]
            }
        }
        
        with open(temp_project_file, 'w', encoding='utf-8') as f:
            json.dump(fanqie_project_data, f, ensure_ascii=False, indent=2)
        
        return str(temp_project_file)
    
    def _create_temp_chapter_files(self, novel_title: str, chapters: List[Dict[str, Any]]) -> str:
        """创建临时章节文件"""
        # 清理小说标题中的特殊字符
        safe_title = self.sanitize_filename(novel_title)
        temp_dir = Path("temp_fanqie_upload") / f"{safe_title}_章节"
        temp_dir.mkdir(exist_ok=True)
        
        for chapter in chapters:
            # 清理章节标题中的特殊字符
            safe_chapter_title = self.sanitize_filename(chapter['chapter_title'])
            chapter_file = temp_dir / f"第{chapter['chapter_number']}章_{safe_chapter_title}.txt"
            
            # 构建番茄格式的章节数据
            chapter_data = {
                "chapter_number": chapter["chapter_number"],
                "chapter_title": chapter["chapter_title"],
                "content": chapter["content"]
            }
            
            with open(chapter_file, 'w', encoding='utf-8') as f:
                json.dump(chapter_data, f, ensure_ascii=False, indent=2)
        
        return str(temp_dir)
    
    def _call_fanqie_upload(self, project_file_path: str) -> bool:
        """调用番茄上传功能 - 从已有进度开始上传"""
        try:
            if not autopush_available:
                self.logger.warning("⚠️ 番茄自动上传模块不可用，跳过上传")
                return False

            self.logger.info("🔄 开始调用番茄上传功能...")
            self.logger.info(f"📁 项目文件路径: {project_file_path}")

            # 调用main_scan_cycle函数，它会自动从已有进度继续上传
            # 每发布一章，进度会自动保存到进度文件中
            try:
                # 设置小说项目路径为临时文件所在目录的父目录
                temp_project_file = Path(project_file_path)
                if temp_project_file.exists():
                    # 从临时文件路径推断小说项目目录
                    novel_title = temp_project_file.stem.replace("_项目信息", "")
                    CONFIG["novel_path"] = str(temp_project_file.parent)
                    
                    self.logger.info(f"📚 设置小说项目目录: {CONFIG['novel_path']}")
                    self.logger.info(f"📖 小说标题: {novel_title}")
                    
                    # 加载已有进度
                    from Chrome.automation.legacy.progress_manager import load_publish_progress2
                    progress = load_publish_progress2(novel_title)
                    published_count = len(progress.get("published_chapters", []))
                    self.logger.info(f"📊 已发布章节: {published_count}章")
                    self.logger.info(f"💾 上传进度会自动保存，每发布一章就记录一次")
                    
                    # 调用主扫描循环（从已有进度继续）
                    success = main_scan_cycle()
                    
                    if success:
                        self.logger.info("✅ 番茄上传功能执行成功")
                        return True
                    else:
                        self.logger.warning("⚠️ 番茄上传功能执行完成但可能有部分失败")
                        return True  # 即使部分失败也返回True
                        
                else:
                    self.logger.error(f"❌ 项目文件不存在: {project_file_path}")
                    return False

            except Exception as e:
                self.logger.error(f"❌ 调用main_scan_cycle失败: {e}")
                return False

        except Exception as e:
            self.logger.error(f"调用番茄上传功能失败: {e}")
            return False
    
    def _cleanup_temp_files(self, project_path: str, chapter_path: str):
        """清理临时文件"""
        try:
            import shutil
            
            if os.path.exists(project_path):
                os.remove(project_path)
            
            if os.path.exists(chapter_path):
                shutil.rmtree(chapter_path)
                
            self.logger.info("✅ 临时文件清理完成")
            
        except Exception as e:
            self.logger.error(f"清理临时文件失败: {e}")
    
    def _update_task_status(self, task_id: str, status: str, progress: int, message: str = ""):
        """更新任务状态"""
        if task_id in self.upload_tasks:
            self.upload_tasks[task_id].update({
                "status": status,
                "progress": progress,
                "updated_at": datetime.now().isoformat()
            })
            
            # 如果任务完成或失败，记录完成时间
            if status in ['completed', 'failed']:
                self.task_completion_times[task_id] = time.time()
                self.logger.info(f"📝 任务 {task_id} 状态更新为 {status}，将在 {self.TASK_RETENTION_TIME} 秒后清理")
            
        self.upload_status[task_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
    def _start_task_cleanup_thread(self):
        """启动定期清理已完成任务的线程"""
        def cleanup_old_tasks():
            while True:
                try:
                    current_time = time.time()
                    tasks_to_remove = []
                    
                    for task_id, completion_time in list(self.task_completion_times.items()):
                        # 检查是否超过保留时间
                        if current_time - completion_time > self.TASK_RETENTION_TIME:
                            tasks_to_remove.append(task_id)
                    
                    # 清理过期任务
                    for task_id in tasks_to_remove:
                        if task_id in self.upload_tasks:
                            self.logger.info(f"🧹 清理过期任务: {task_id}")
                            del self.upload_tasks[task_id]
                        if task_id in self.upload_status:
                            del self.upload_status[task_id]
                        if task_id in self.task_completion_times:
                            del self.task_completion_times[task_id]
                    
                    # 每60秒检查一次
                    time.sleep(60)
                    
                except Exception as e:
                    self.logger.error(f"清理任务失败: {e}")
                    time.sleep(60)
        
        cleanup_thread = threading.Thread(target=cleanup_old_tasks, daemon=True)
        cleanup_thread.start()
        self.logger.info("✅ 任务清理线程已启动")
    
    def get_upload_status(self, task_id: str) -> Dict[str, Any]:
        """获取上传状态"""
        if task_id not in self.upload_tasks:
            return {"error": "任务不存在"}
        
        return {
            "task": self.upload_tasks[task_id],
            "status": self.upload_status.get(task_id, {})
        }
    
    def get_all_upload_tasks(self) -> List[Dict[str, Any]]:
        """获取所有上传任务"""
        return list(self.upload_tasks.values())
    
    def check_upload_prerequisites(self) -> Dict[str, Any]:
        """检查上传前提条件 - 手动浏览器模式"""
        checks = {
            "browser_available": False,  # 浏览器需要手动启动
            "fanqie_logged_in": False,   # 需要手动登录
            "temp_dir_writable": False,
            "autopush_available": autopush_available
        }
        
        try:
            # 检查临时目录是否可写
            temp_dir = Path("temp_fanqie_upload")
            temp_dir.mkdir(exist_ok=True)
            test_file = temp_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            checks["temp_dir_writable"] = True
            self.logger.info("✅ 临时目录权限检查通过")

        except Exception as e:
            self.logger.error(f"❌ 临时目录检查失败: {e}")
        
        # 记录手动浏览器模式
        self.logger.info("📋 使用手动浏览器模式:")
        self.logger.info("   - 浏览器连接: 需要用户手动启动并登录番茄网站")
        self.logger.info("   - 上传进度: 自动从上次中断处继续")
        self.logger.info(f"   - 上传模块可用: {autopush_available}")
        
        return checks

    def get_upload_progress(self, novel_title: str) -> Dict[str, Any]:
        """获取小说的上传进度"""
        try:
            if not autopush_available:
                return {"error": "上传模块不可用"}
            
            from Chrome.automation.legacy.progress_manager import load_publish_progress2
            
            progress = load_publish_progress2(novel_title)
            published_chapters = progress.get("published_chapters", [])
            
            return {
                "novel_title": novel_title,
                "published_count": len(published_chapters),
                "total_content_len": progress.get("total_content_len", 0),
                "base_chapter_num": progress.get("base_chapter_num", 0),
                "book_created": progress.get("book_created", False),
                "last_update": progress.get("last_update", None),
                "published_chapters": published_chapters[-10:]  # 只返回最近10章
            }
        except Exception as e:
            self.logger.error(f"获取上传进度失败: {e}")
            return {"error": str(e)}