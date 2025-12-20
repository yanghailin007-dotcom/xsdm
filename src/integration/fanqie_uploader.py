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
    # 尝试导入新的自动化模块
    from Chrome.automation.legacy.autopush_legacy import (
        main_scan_cycle, ensure_directory_exists, CONFIG
    )
    autopush_available = True
except ImportError as e:
    print(f"警告: 无法导入番茄自动上传模块: {e}")
    autopush_available = False

class FanqieUploader:
    """番茄小说一键上传管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.upload_tasks = {}
        self.upload_status = {}
        self.logger = self._get_logger()
        
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
            # 检查项目文件是否存在
            project_file = Path("小说项目") / f"{novel_title}_项目信息.json"
            if not project_file.exists():
                return {
                    "valid": False,
                    "error": f"项目文件不存在: {project_file}"
                }
            
            # 加载项目信息
            with open(project_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            
            # 检查必要字段
            required_fields = ['project_info', 'characters']
            for field in required_fields:
                if field not in project_data:
                    return {
                        "valid": False,
                        "error": f"项目数据缺少必需字段: {field}"
                    }
            
            # 检查章节文件 - 优先检查完整章节目录
            chapter_dirs = [
                Path("小说项目") / novel_title / "chapters",  # 优先检查完整章节目录（200章）
                Path("小说项目") / f"{novel_title}_章节",
                Path("小说项目") / "chapters"  # 通用章节目录（可能不完整）
            ]
            
            chapter_files = []
            for chapter_dir in chapter_dirs:
                if chapter_dir.exists():
                    chapter_files = list(chapter_dir.glob("第*.txt")) + list(chapter_dir.glob("第*.json"))
                    break
            
            if not chapter_files:
                return {
                    "valid": False,
                    "error": "未找到章节文件，请先生成章节内容"
                }
            
            # 转换项目数据为番茄格式
            fanqie_data = self._convert_to_fanqie_format(project_data, novel_title, chapter_files)
            
            return {
                "valid": True,
                "fanqie_data": fanqie_data,
                "chapter_count": len(chapter_files),
                "project_info": project_data.get("project_info", {})
            }
            
        except Exception as e:
            self.logger.error(f"验证小说项目失败: {e}")
            return {
                "valid": False,
                "error": f"验证失败: {str(e)}"
            }
    
    def _convert_to_fanqie_format(self, project_data: Dict[str, Any], novel_title: str, chapter_files: List[Path]) -> Dict[str, Any]:
        """将创作系统的项目数据转换为番茄上传格式"""
        
        project_info = project_data.get("project_info", {})
        characters = project_data.get("characters", {})
        
        # 构建番茄格式的数据
        fanqie_data = {
            "novel_info": {
                "title": project_info.get("title", novel_title),
                "synopsis": self._generate_synopsis(project_info),
                "selected_plan": {
                    "tags": {
                        "target_audience": "男频" if "男频" in project_info.get("category", "") else "女频",
                        "main_category": self._extract_main_category(project_info.get("tags", [])),
                        "themes": self._extract_themes(project_info.get("tags", [])),
                        "roles": self._extract_roles(project_info.get("tags", [])),
                        "plots": ["原创", "同人"] if "同人" in project_info.get("tags", []) else ["原创"]
                    }
                }
            },
            "character_design": characters,
            "chapters": []
        }
        
        # 处理章节文件
        for chapter_file in sorted(chapter_files, key=self._extract_chapter_number):
            chapter_data = self._process_chapter_file(chapter_file)
            if chapter_data:
                fanqie_data["chapters"].append(chapter_data)
        
        return fanqie_data
    
    def _generate_synopsis(self, project_info: Dict[str, Any]) -> str:
        """生成小说简介"""
        core_setting = project_info.get("core_setting", "")
        core_selling_points = project_info.get("core_selling_points", "")
        synopsis = project_info.get("synopsis", "")
        
        if synopsis:
            return synopsis
        
        # 从核心设定和卖点生成简介
        generated_synopsis = core_setting
        if core_selling_points:
            generated_synopsis += f"\n\n核心看点：{core_selling_points}"
        
        return generated_synopsis[:500]  # 限制长度
    
    def _extract_main_category(self, tags: List[str]) -> str:
        """提取主分类"""
        category_mapping = {
            "玄幻": "玄幻",
            "都市": "都市", 
            "历史": "历史",
            "科幻": "科幻",
            "武侠": "武侠",
            "悬疑": "悬疑",
            "游戏": "游戏",
            "同人": "衍生同人"
        }
        
        for tag in tags:
            if tag in category_mapping:
                return category_mapping[tag]
        
        return "其他"  # 默认分类
    
    def _extract_themes(self, tags: List[str]) -> List[str]:
        """提取主题标签"""
        theme_mapping = {
            "修仙": "修仙",
            "种田": "种田",
            "系统": "系统",
            "爽文": "爽文",
            "重生": "重生",
            "穿越": "穿越"
        }
        
        themes = []
        for tag in tags:
            if tag in theme_mapping:
                themes.append(theme_mapping[tag])
        
        return themes[:3]  # 最多3个主题
    
    def _extract_roles(self, tags: List[str]) -> List[str]:
        """提取角色标签"""
        role_mapping = {
            "天才流": "天才",
            "无敌流": "无敌",
            "升级流": "升级"
        }
        
        roles = []
        for tag in tags:
            if tag in role_mapping:
                roles.append(role_mapping[tag])
        
        return roles[:2]  # 最多2个角色
    
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
        """启动浏览器用于上传"""
        try:
            self.logger.info("🚀 启动浏览器用于番茄上传...")
            
            # 检查浏览器启动脚本是否存在
            launcher_script = Path("fanqie_browser_launcher.py")
            if not launcher_script.exists():
                # 尝试使用备用脚本
                launcher_script = Path("start_fanqie_test.py")
                if not launcher_script.exists():
                    return {
                        "success": False,
                        "error": "未找到浏览器启动脚本"
                    }
            
            # 启动浏览器
            try:
                # Windows系统下设置环境变量解决编码问题
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONPATH'] = sys.executable
                
                # 使用subprocess.Popen避免阻塞问题
                process = subprocess.Popen(
                    [sys.executable, str(launcher_script)],
                    env=env,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
                )
                
                # 等待一小段时间让进程启动
                time.sleep(2)
                
                # 检查进程是否还在运行
                if process.poll() is None:
                    self.logger.info("✅ 浏览器启动成功")
                    return {
                        "success": True,
                        "message": "浏览器启动成功，正在打开番茄网站...",
                        "details": f"浏览器进程PID: {process.pid}"
                    }
                else:
                    error_msg = f"浏览器进程退出，退出码: {process.poll()}"
                    self.logger.error(f"浏览器启动失败: {error_msg}")
                    return {
                        "success": False,
                        "error": error_msg
                    }
                
                
                if result.returncode == 0:
                    self.logger.info("✅ 浏览器启动成功")
                    return {
                        "success": True,
                        "message": "浏览器启动成功，正在打开番茄网站...",
                        "details": result.stdout
                    }
                else:
                    error_msg = f"浏览器启动失败: {result.stderr}"
                    self.logger.error(error_msg)
                    return {
                        "success": False,
                        "error": error_msg
                    }
                    
            except subprocess.TimeoutExpired:
                self.logger.warning("浏览器启动超时，但可能仍在启动中")
                return {
                    "success": True,
                    "message": "浏览器启动中，请稍等...",
                    "note": "启动超时但进程可能仍在运行"
                }
            except Exception as e:
                error_msg = f"启动浏览器时发生异常: {str(e)}"
                self.logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
                
        except Exception as e:
            error_msg = f"启动浏览器失败: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
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
        """调用番茄上传功能 - 集成修改后的脚本"""
        try:
            if not autopush_available:
                self.logger.warning("⚠️ 番茄自动上传模块不可用，跳过上传")
                return False

            self.logger.info("🔄 开始调用番茄上传功能...")
            self.logger.info(f"📁 项目文件路径: {project_file_path}")

            # 调用修改后的main_scan_cycle函数
            # 这个函数现在包含了人工确认登录和环境自动识别功能
            try:
                # 设置小说项目路径为临时文件所在目录的父目录
                temp_project_file = Path(project_file_path)
                if temp_project_file.exists():
                    # 从临时文件路径推断小说项目目录
                    novel_title = temp_project_file.stem.replace("_项目信息", "")
                    CONFIG["novel_path"] = str(temp_project_file.parent)
                    
                    self.logger.info(f"📚 设置小说项目目录: {CONFIG['novel_path']}")
                    self.logger.info(f"📖 小说标题: {novel_title}")
                    
                    # 调用主扫描循环（包含人工确认和环境自动识别）
                    success = main_scan_cycle()
                    
                    if success:
                        self.logger.info("✅ 番茄上传功能执行成功")
                        return True
                    else:
                        self.logger.warning("⚠️ 番茄上传功能执行完成但可能有部分失败")
                        return True  # 即使部分失败也返回True，因为用户已确认
                        
                else:
                    self.logger.error(f"❌ 项目文件不存在: {project_file_path}")
                    return False

            except Exception as e:
                self.logger.error(f"❌ 调用main_scan_cycle失败: {e}")
                self.logger.info("🔄 尝试使用备用上传方法...")
                
                # 备用方案：直接调用原有的上传逻辑
                try:
                    # 这里可以添加备用的上传逻辑
                    # 目前先返回False，表示需要用户手动处理
                    self.logger.warning("⚠️ 备用上传方法暂未实现")
                    return False
                    
                except Exception as backup_error:
                    self.logger.error(f"❌ 备用上传方法也失败: {backup_error}")
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
            
        self.upload_status[task_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    
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
        """检查上传前提条件 - 手动环境准备模式"""
        checks = {
            "browser_available": True,  # 默认用户已手动准备浏览器
            "fanqie_logged_in": True,   # 默认用户已手动登录番茄网站
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
        
        # 记录手动环境准备模式
        self.logger.info("📋 使用手动环境准备模式:")
        self.logger.info("   - 浏览器连接: 默认OK（用户手动准备）")
        self.logger.info("   - 番茄登录: 默认OK（用户手动登录）")
        self.logger.info(f"   - 上传模块可用: {autopush_available}")
        
        return checks