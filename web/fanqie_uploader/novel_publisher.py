"""
小说发布核心模块
负责小说的创建、章节发布和定时发布管理
"""

import os
import sys
import time
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from playwright.sync_api import Page

# 使用 web_config 的统一 logger
try:
    from web.web_config import logger
except ImportError:
    logger = logging.getLogger(__name__)

# 导入同级目录下的工具模块
try:
    from config_loader import ConfigLoader
    from file_handler import FileHandler
    from ui_helper import UIHelper
except ImportError:
    # 如果在包内导入失败，尝试完整路径
    from fanqie_uploader.config_loader import ConfigLoader
    from fanqie_uploader.file_handler import FileHandler
    from fanqie_uploader.ui_helper import UIHelper


class NovelPublisher:
    """小说发布器类"""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        初始化小说发布器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.file_handler = FileHandler(config_loader)
        self.ui_helper = UIHelper(config_loader)
    
    def _load_legacy_project_info(self, project_dir: Path, data: Dict) -> None:
        """
        🔥 兼容旧格式：从 project_info/ 目录加载项目信息
        
        Args:
            project_dir: 项目目录路径
            data: 已加载的项目数据（会被修改补充）
        """
        try:
            project_info_dir = project_dir / "project_info"
            if not project_info_dir.exists():
                return
            
            # 查找最新的项目信息文件
            info_files = list(project_info_dir.glob("*_项目信息_*.json"))
            if not info_files:
                return
            
            # 按修改时间排序，取最新的
            info_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            latest_info_file = info_files[0]
            
            logger.info(f"[Publisher] 发现旧格式项目信息文件: {latest_info_file.name}")
            
            # 加载旧格式数据
            legacy_data = self.file_handler.load_json_file(str(latest_info_file))
            if not legacy_data:
                return
            
            # 补充缺失的字段
            if 'selected_plan' not in data and 'selected_plan' in legacy_data:
                data['selected_plan'] = legacy_data['selected_plan']
                logger.info("[Publisher] 从旧格式补充 selected_plan")
            
            if 'creative_seed' not in data and 'creative_seed' in legacy_data:
                data['creative_seed'] = legacy_data['creative_seed']
                logger.info("[Publisher] 从旧格式补充 creative_seed")
            
            if 'novel_title' not in data and 'novel_title' in legacy_data:
                data['novel_title'] = legacy_data['novel_title']
                logger.info("[Publisher] 从旧格式补充 novel_title")
            
            if 'synopsis' not in data and 'synopsis' in legacy_data:
                data['synopsis'] = legacy_data['synopsis']
                logger.info("[Publisher] 从旧格式补充 synopsis")
                
        except Exception as e:
            logger.info(f"[Publisher] 加载旧格式项目信息失败: {e}")
    
    def publish_novel(self, page: Page, json_file: str) -> bool:
        """
        发布单个小说
        
        Args:
            page: 页面对象
            json_file: 小说项目JSON文件路径
            
        Returns:
            是否发布成功
        """
        logger.info(f"\n[Publisher] 处理小说项目: {os.path.basename(json_file)}")
        
        # 加载小说数据
        logger.info("[Publisher] 正在加载JSON文件...")
        data = self.file_handler.load_json_file(json_file)
        if not data:
            logger.info(f"✗ 无法加载小说项目文件: {json_file}")
            return False
        
        logger.info(f"[Publisher] JSON加载成功，数据键: {list(data.keys())}")
        
        # 🔥 兼容旧格式：从 project_info/ 目录加载额外数据
        json_file_path = Path(json_file)
        project_dir = json_file_path.parent
        self._load_legacy_project_info(project_dir, data)
        
        # 适配两种数据格式：直接字段或嵌套 novel_info
        if 'novel_info' in data and isinstance(data['novel_info'], dict):
            novel_title = data['novel_info'].get('title', '')
            novel_synopsis = data['novel_info'].get('synopsis', '')
            selected_plan = data['novel_info'].get('selected_plan', {})
            logger.info(f"[Publisher] 使用嵌套 novel_info 格式")
        else:
            # 旧格式：扁平结构
            novel_title = data.get('novel_title', '')
            novel_synopsis = data.get('synopsis', '') or data.get('novel_synopsis', '')
            selected_plan = data.get('selected_plan', {})
            logger.info(f"[Publisher] 使用直接字段格式（旧格式）")
        
        if not novel_title:
            logger.info(f"✗ 小说标题为空，请检查项目文件格式")
            return False
        
        # 🔥 处理主角名 - 优先从selected_plan中获取（兼容新旧格式）
        main_character = "未知主角"
        if selected_plan and isinstance(selected_plan, dict):
            suggestions = selected_plan.get('suggestions', {})
            if isinstance(suggestions, dict) and 'name' in suggestions:
                main_character = suggestions['name']
                logger.info(f"[Publisher] 从 selected_plan 获取主角名: {main_character}")
        
        # 备选：从 character_design 获取
        if main_character == "未知主角":
            char_design = data.get('character_design', {})
            if not char_design and 'novel_info' in data:
                char_design = data['novel_info'].get('character_design', {})
            if char_design and 'main_character' in char_design:
                main_character = char_design['main_character'].get('name', '未知主角')
                logger.info(f"[Publisher] 从 character_design 获取主角名: {main_character}")
        
        logger.info(f"[Publisher] 小说名称: {novel_title}")
        logger.info(f"[Publisher] 主角: {main_character}")
        
        # 优化简介排版
        logger.info("[Publisher] 正在格式化简介...")
        formatted_synopsis = self.file_handler.format_synopsis_for_fanqie(novel_synopsis, data)
        logger.info("[Publisher] 优化后的简介:")
        logger.info(formatted_synopsis[:200] + "..." if len(formatted_synopsis) > 200 else formatted_synopsis)
        logger.info("-" * 50)
        
        # 加载发布进度
        progress = self._load_publish_progress(novel_title)
        
        # 检查是否需要创建新书
        if not progress.get("book_created", False):
            logger.info("书籍未创建，开始创建新书...")
            if self._create_new_book(page, novel_title, formatted_synopsis, main_character, data):
                progress["book_created"] = True
                self._save_publish_progress(novel_title, progress)
                logger.info(f"✓ 书籍《{novel_title}》创建成功")
            else:
                logger.info(f"✗ 书籍《{novel_title}》创建失败")
                return False
        
        # 等待页面完全加载
        logger.info("等待书籍详情页完全加载...")
        try:
            page.wait_for_load_state("networkidle")
            time.sleep(2)
        except Exception as e:
            logger.info(f"等待页面加载时出错: {e}")
        
        # 处理章节发布
        return self._publish_chapters(page, novel_title, json_file, data, progress)
    
    def _publish_chapters(self, page: Page, novel_title: str, json_file: str, 
                         novel_data: Dict[str, Any], progress: Dict[str, Any]) -> bool:
        """
        发布章节
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            json_file: JSON文件路径
            novel_data: 小说数据
            progress: 发布进度
            
        Returns:
            是否发布成功
        """
        # 查找章节文件
        chapter_path = os.path.join(
            self.config_loader.get_novel_path() if self.config_loader else "小说项目",
            f"{novel_title}_章节"
        )
        
        if not os.path.exists(chapter_path):
            logger.info(f"章节目录不存在: {chapter_path}")
            logger.info("请确保章节文件位于正确的目录中")
            return False
        
        # 获取章节文件
        chapter_files = []
        for filename in os.listdir(chapter_path):
            if filename.endswith('.txt'):
                chapter_files.append(os.path.join(chapter_path, filename))
        
        # 验证并修复章节文件
        valid_chapter_files = self.file_handler.validate_and_fix_chapter_files(chapter_files, novel_title)
        chapter_files_sorted = self.file_handler.sort_files_by_chapter(valid_chapter_files)
        
        if not chapter_files_sorted:
            logger.info("未找到章节文件")
            return False
        
        logger.info(f"找到 {len(chapter_files_sorted)} 个章节")
        
        # 发布章节
        published_chapters = progress.get("published_chapters", [])
        total_content_len = progress.get("total_content_len", 0)
        
        published_count = len(published_chapters)
        logger.info(f"检测到已发布 {published_count} 章，将从第 {published_count + 1} 章继续...")
        
        # 检查小说是否已完成
        if self._check_if_novel_completed(json_file, published_count):
            logger.info(f"🎉 小说《{novel_title}》已完成所有章节发布!")
            if self.file_handler.move_completed_novel_to_published(novel_title, json_file):
                return True
        
        # 章节发布逻辑
        return self._process_chapter_publishing(page, novel_title, chapter_files_sorted, 
                                              json_file, progress, total_content_len)
    
    def _process_chapter_publishing(self, page: Page, novel_title: str, chapter_files: List[str],
                                   json_file: str, progress: Dict[str, Any], total_content_len: int) -> bool:
        """
        处理章节发布逻辑
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            chapter_files: 章节文件列表
            json_file: JSON文件路径
            progress: 发布进度
            total_content_len: 总字数
            
        Returns:
            是否处理成功
        """
        published_chapters = progress.get("published_chapters", [])
        base_chapter_num = progress.get("base_chapter_num", 0)
        
        # 获取配置
        word_threshold = self.config_loader.get_min_words_for_scheduled_publish() if self.config_loader else 60000
        publish_times = self.config_loader.get_publish_times() if self.config_loader else ["05:25", "11:25", "17:25", "23:25"]
        chapters_per_slot = self.config_loader.get_chapters_per_time_slot() if self.config_loader else 2
        
        # 构建章节发布信息
        chapter_publish_info = []
        for chap_index, chapter_file in enumerate(chapter_files):
            # 检查章节是否已经发布
            is_published = any(pub_chap.get('file') == chapter_file for pub_chap in published_chapters)
            
            if is_published:
                # 找到已发布的章节信息
                pub_chap = next(pc for pc in published_chapters if pc.get('file') == chapter_file)
                chapter_publish_info.append({
                    'file': chapter_file,
                    'chap_num': str(pub_chap.get('chap_num', '0')),
                    'chap_title': pub_chap.get('chap_title', ''),
                    'chap_content': pub_chap.get('chap_content', ''),
                    'chap_len': pub_chap.get('chap_len', 0),
                    'index': chap_index,
                    'published': True,
                    'target_date': pub_chap.get('target_date', ''),
                    'target_time': pub_chap.get('target_time', ''),
                    'time_slot_index': pub_chap.get('time_slot_index', 0)
                })
                continue
            
            # 加载未发布的章节信息
            chapter_data = self.file_handler.load_json_file(chapter_file)
            if chapter_data:
                chap_num = str(chapter_data['chapter_number'])
                chap_title = chapter_data['chapter_title']
                chap_content = chapter_data['content']
                chap_len = self.file_handler.count_content_chars(chap_content)
                
                chapter_publish_info.append({
                    'file': chapter_file,
                    'chap_num': chap_num,
                    'chap_title': chap_title,
                    'chap_content': chap_content,
                    'chap_len': chap_len,
                    'index': chap_index,
                    'published': False,
                    'target_date': '',
                    'target_time': '',
                    'time_slot_index': 0
                })
        
        # 发布章节
        current_chapter_index = 0
        total_chapters = len(chapter_publish_info)
        
        # 获取当前时间用于定时发布
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        # 检查是否需要恢复定时发布状态
        if published_chapters and total_content_len >= word_threshold:
            current_date, current_time = self._restore_scheduled_publish_state(
                published_chapters, publish_times, chapters_per_slot, now
            )
        
        # 主发布循环
        while current_chapter_index < total_chapters:
            current_chapter = chapter_publish_info[current_chapter_index]
            
            # 跳过已发布的章节
            if current_chapter['published']:
                logger.info(f"跳过已发布章节: {os.path.basename(current_chapter['file'])}")
                current_chapter_index += 1
                continue
            
            # 检查累计字数是否达到阈值
            if total_content_len < word_threshold:
                logger.info(f"当前累计字数 {total_content_len} 小于 {word_threshold}，跳过章节 {current_chapter['chap_num']} 的定时发布设置")
                
                # 直接发布章节但不设置定时
                if not self.ui_helper.check_and_recover_page(page):
                    logger.info("页面已失效，无法继续发布")
                    break
                
                logger.info(f"\n发布第 {current_chapter['chap_num']} 章: {current_chapter['chap_title']} (字数: {current_chapter['chap_len']}) - 不设置定时")
                
                # 发布章节（不设置定时）
                result = self._verify_and_create_chapter(
                    page, novel_title, current_chapter['chap_num'], current_chapter['chap_title'],
                    current_chapter['chap_content'], None, None
                )
                
                if result == 0:  # 成功
                    total_content_len += current_chapter['chap_len']
                    progress["total_content_len"] = total_content_len
                    self._save_publish_progress(novel_title, progress)
                    logger.info(f"✓ 发布成功 (累计字数: {total_content_len})")
                    
                    # 标记为已发布
                    current_chapter['published'] = True
                    current_chapter.update({
                        'target_date': '',
                        'target_time': '',
                        'time_slot_index': 0
                    })
                    published_chapters.append(current_chapter.copy())
                    progress["published_chapters"] = published_chapters
                    self._save_publish_progress(novel_title, progress)
                    
                    # 检查是否完成所有章节
                    if self._check_if_novel_completed(json_file, len(published_chapters)):
                        logger.info(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                        if self.file_handler.move_completed_novel_to_published(novel_title, json_file):
                            return True
                else:
                    logger.info("✗ 发布失败")
                    self.ui_helper.wait_for_enter("发布失败，按回车继续下一章...", timeout=10)
                
                current_chapter_index += 1
                continue
            
            # 累计字数达到阈值后，开始设置定时发布
            logger.info(f"累计字数已达 {total_content_len}，超过阈值 {word_threshold}，开始设置定时发布")
            
            # 定时发布逻辑
            success = self._handle_scheduled_publishing(
                page, novel_title, chapter_publish_info, current_chapter_index,
                published_chapters, total_content_len, json_file, progress,
                now, current_date, current_time, publish_times, chapters_per_slot
            )
            
            if success:
                return True
            else:
                break
        
        logger.info(f"\n✓ 小说《{novel_title}》发布完成，共 {len(chapter_files)} 章，总字数 {total_content_len}")
        return True
    
    def _create_new_book(self, page: Page, novel_title: str, formatted_synopsis: str, 
                        main_character: str, novel_data: Dict[str, Any]) -> bool:
        """
        创建新书
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            formatted_synopsis: 格式化的简介
            main_character: 主角名
            novel_data: 小说数据
            
        Returns:
            是否创建成功
        """
        logger.info("[Publisher] 开始创建新书...")
        import sys
        sys.stdout.flush()
        
        # 调试截图路径
        debug_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'debug_screenshots')
        os.makedirs(debug_dir, exist_ok=True)
        
        try:
            # 等待页面完全加载
            logger.info("[Publisher] 等待页面加载...")
            time.sleep(2)
            
            # 截图查看当前页面状态
            try:
                screenshot_path = os.path.join(debug_dir, f'create_book_{int(time.time())}.png')
                page.screenshot(path=screenshot_path, full_page=True)
                logger.info(f"页面截图已保存: {screenshot_path}")
            except Exception as e:
                logger.info(f"截图失败: {e}")
            
            # 打印当前页面URL和标题用于调试
            try:
                logger.info(f"当前页面URL: {page.url}")
            except:
                logger.info("无法获取页面URL")
            
            try:
                title = page.title()
                logger.info(f"当前页面标题: {title}")
            except:
                logger.info("无法获取页面标题")
            
            # 步骤1: 点击"创建新书"打开下拉菜单
            menu_opened = False
            
            try:
                # 查找"创建新书"按钮（div.hoverup 或包含 tomato-circle-add 图标）
                locator = page.locator('div.hoverup:has-text("创建新书"), div.font-4:has-text("创建新书")')
                if locator.count() > 0:
                    logger.info("找到创建新书按钮，点击打开下拉菜单...")
                    locator.first.click(timeout=5000)
                    menu_opened = True
                    time.sleep(0.5)  # 等待菜单展开
            except Exception as e:
                logger.info(f"点击创建新书按钮失败: {e}")
            
            if not menu_opened:
                logger.info("无法打开创建新书菜单")
                return False
            
            # 步骤2: 点击下拉菜单中的"创建书本"选项
            clicked = False
            
            # 策略1: 直接查找"创建书本"文本
            try:
                locator = page.get_by_text("创建书本", exact=True)
                if locator.count() > 0:
                    logger.info("找到'创建书本'选项")
                    locator.first.click(timeout=5000)
                    clicked = True
            except Exception as e:
                logger.info(f"查找创建书本(精确)失败: {e}")
            
            # 策略2: 查找包含"书本信息已准备好"的选项（根据截图中的描述文字）
            if not clicked:
                try:
                    # 先找到包含"书本信息已准备好"的元素，然后找到它的父级或兄弟元素"创建书本"
                    locator = page.locator('text=书本信息已准备好')
                    if locator.count() > 0:
                        logger.info("找到'书本信息已准备好'描述，尝试点击父级'创建书本'...")
                        # 向上查找包含"创建书本"的父元素
                        parent = locator.locator('xpath=ancestor::*[contains(., "创建书本")][1]')
                        if parent.count() > 0:
                            parent.first.click(timeout=5000)
                            clicked = True
                        else:
                            # 尝试直接查找附近的"创建书本"文本
                            locator2 = page.locator('text=创建书本:has-text("书本信息已准备好")')
                            if locator2.count() > 0:
                                locator2.first.click(timeout=5000)
                                clicked = True
                except Exception as e:
                    logger.info(f"通过描述查找创建书本失败: {e}")
            
            # 策略3: 查找所有包含"创建书本"的元素
            if not clicked:
                try:
                    elements = page.locator(':text("创建书本")').all()
                    logger.info(f"找到 {len(elements)} 个包含'创建书本'的元素")
                    for i, el in enumerate(elements):
                        try:
                            text = el.text_content()
                            logger.info(f"  元素 {i}: {text[:50] if text else 'N/A'}")
                            # 点击包含"书本信息已准备好"的那个
                            if text and "书本信息已准备好" in text:
                                el.click(timeout=5000)
                                clicked = True
                                logger.info(f"  点击元素 {i} 成功")
                                break
                            # 或者点击独立的"创建书本"文本
                            elif text and text.strip() == "创建书本":
                                el.click(timeout=5000)
                                clicked = True
                                logger.info(f"  点击独立'创建书本'成功")
                                break
                        except Exception as e2:
                            logger.info(f"  点击元素 {i} 失败: {e2}")
                except Exception as e:
                    logger.info(f"遍历创建书本元素失败: {e}")
            
            if not clicked:
                logger.info("未找到'创建书本'选项")
                # 截图记录当前状态
                try:
                    screenshot_path = os.path.join(debug_dir, f'create_book_menu_{int(time.time())}.png')
                    page.screenshot(path=screenshot_path, full_page=True)
                    logger.info(f"菜单截图已保存: {screenshot_path}")
                except:
                    pass
                return False
            
            logger.info("✓ 点击'创建书本'选项成功")
            time.sleep(2)  # 等待页面加载
            
            # 根据HTML结构更新选择器
            # 书名输入框: <input placeholder="请输入作品名称" value="...">
            title_short = novel_title[-15:] if len(novel_title) >= 15 else novel_title
            try:
                title_input = page.locator('input[placeholder="请输入作品名称"]')
                title_input.fill(title_short)
                logger.info(f"✓ 填写书名: {title_short}")
            except Exception as e:
                logger.info(f"填写书名失败: {e}")
            
            # 选择男女频
            if "novel_info" in novel_data and isinstance(novel_data["novel_info"], dict):
                tags_info = novel_data.get("novel_info", {}).get("selected_plan", {}).get("tags", {})
            else:
                selected_plan = novel_data.get("selected_plan", {})
                if isinstance(selected_plan, dict):
                    tags_info = selected_plan.get("tags", {})
                else:
                    tags_info = {}
            gender = tags_info.get("target_audience", "男频")
            
            # 根据HTML: <input type="radio" name="pindao" value="1">男频, value="0">女频
            try:
                if gender == "女频":
                    page.locator('input[name="pindao"][value="0"]').click()
                    logger.info("✓ 选择女频")
                else:
                    page.locator('input[name="pindao"][value="1"]').click()
                    logger.info("✓ 选择男频")
            except Exception as e:
                logger.info(f"选择男/女频失败: {e}")
            
            # 填写主角名 - HTML: <input placeholder="请输入主角名1">
            character_short = main_character[:5] if len(main_character) >= 5 else main_character
            try:
                character_input = page.locator('input[placeholder="请输入主角名1"]')
                character_input.fill(character_short)
                logger.info(f"✓ 填写主角名: {character_short}")
            except Exception as e:
                logger.info(f"填写主角名失败: {e}")
            
            # 填写作品简介 - HTML: <textarea placeholder="请输入50-500字以内的作品简介...">
            synopsis_short = formatted_synopsis[:500] if len(formatted_synopsis) >= 500 else formatted_synopsis
            try:
                synopsis_input = page.locator('textarea[placeholder*="作品简介"]')
                synopsis_input.fill(synopsis_short)
                logger.info("✓ 填写作品简介")
            except Exception as e:
                logger.info(f"填写简介失败: {e}")
            
            # 处理标签弹窗（如果存在）
            try:
                # 检查是否有标签选择弹窗
                modal = page.locator('.category-modal')
                if modal.count() > 0 and modal.is_visible():
                    logger.info("检测到标签选择弹窗，需要选择标签...")
                    # 简化处理：点击取消，手动选择标签
                    cancel_btn = page.locator('.category-modal button:has-text("取消")')
                    if cancel_btn.count() > 0:
                        cancel_btn.click()
                        logger.info("✓ 关闭标签弹窗（请手动选择标签）")
                        time.sleep(0.5)
            except Exception as e:
                logger.info(f"处理标签弹窗时出错: {e}")
            
            # 立即创建按钮 - HTML: <button type="button"><span>立即创建</span></button>
            try:
                create_button = page.locator('button:has-text("立即创建")')
                create_button.click()
                logger.info("✓ 点击立即创建")
            except Exception as e:
                logger.info(f"点击立即创建失败: {e}")
                return False
            
            # 等待创建完成
            for _ in range(10):
                novel_tab = page.locator('xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]')
                self.ui_helper.safe_click(novel_tab, "小说标签")
                time.sleep(1)
                try:
                    page.get_by_text(title_short, exact=True).wait_for(state="visible", timeout=1000)
                    return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            logger.info(f"创建新书时出错: {e}")
            return False
    
    def _select_book_tags(self, page: Page, tags_info: Dict[str, Any]) -> None:
        """
        选择书籍标签
        
        Args:
            page: 页面对象
            tags_info: 标签信息
        """
        logger.info("选择作品标签...")
        
        # 点击选择作品标签
        tag_button = page.locator('xpath=//*[@id="selectRow"]/div/div/span/div/span[1]')
        self.ui_helper.safe_click(tag_button, "选择作品标签")
        time.sleep(2)
        
        # 选择主分类
        main_category = tags_info.get("main_category", "")
        if main_category:
            self.ui_helper.scroll_and_click_enhanced(page, "主分类", main_category)
            logger.info(f"✓ 选择主分类: {main_category}")
        
        # 选择主题
        themes = tags_info.get("themes", [])
        if themes:
            selected_count = 0
            for theme in themes:
                if self.ui_helper.scroll_and_click_enhanced(page, "主题", theme):
                    selected_count += 1
                time.sleep(0.3)
            logger.info(f"主题选择完成: {selected_count}/{len(themes)} 个主题被选中")
        
        # 选择角色
        roles = tags_info.get("roles", [])
        if roles:
            selected_count = 0
            for role in roles:
                if self.ui_helper.scroll_and_click_enhanced(page, "角色", role):
                    selected_count += 1
                time.sleep(0.3)
            logger.info(f"角色选择完成: {selected_count}/{len(roles)} 个角色被选中")
        
        # 选择情节
        plots = tags_info.get("plots", [])
        if plots:
            selected_count = 0
            for plot in plots:
                if self.ui_helper.scroll_and_click_enhanced(page, "情节", plot):
                    selected_count += 1
                time.sleep(0.3)
            logger.info(f"情节选择完成: {selected_count}/{len(plots)} 个情节被选中")
        
        # 确认标签选择
        confirm_button = page.locator('div.arco-modal-footer button.arco-btn-primary')
        if confirm_button.count() > 0:
            self.ui_helper.safe_click(confirm_button.first, "确认标签")
            logger.info("✓ 标签选择完成")
        else:
            logger.info("⚠ 未找到确认标签按钮")
        
        time.sleep(1)
    
    def _verify_and_create_chapter(self, page: Page, expected_book_title: str, chap_number: str,
                                chap_title: str, chap_content: str, target_date: Optional[str] = None,
                                target_time: Optional[str] = None) -> int:
        """
        验证当前页面并创建章节
        
        Args:
            page: 页面对象
            expected_book_title: 期望的书籍标题
            chap_number: 章节号
            chap_title: 章节标题
            chap_content: 章节内容
            target_date: 目标日期
            target_time: 目标时间
            
        Returns:
            0-成功, 1-失败, 2-需要重新导航
        """
        try:
            # 等待页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 验证书名
            header_book_name = page.locator('.publish-header-book-name')
            if header_book_name.count() > 0:
                actual_title = header_book_name.first.text_content().strip()
                if expected_book_title not in actual_title:
                    logger.info(f"✗ 创建章节页面书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                    return 2
            
            # 填写章节信息
            input_elements = page.locator('input.serial-input.byte-input.byte-input-size-default')
            if input_elements.count() < 2:
                logger.info("未找到章节输入框")
                return 1
            
            # 填写章节序号和标题
            if not self.ui_helper.safe_fill(input_elements.nth(0), chap_number, "章节序号"):
                return 1
            if not self.ui_helper.safe_fill(input_elements.nth(1), chap_title, "章节标题"):
                return 1
            
            # 处理并填写内容
            content_cleaned = re.sub(r'^【.*?】\s*?\n', '', chap_content, flags=re.MULTILINE)
            processed_text = self.file_handler.normalize_line_breaks(content_cleaned)
            
            content_input = page.locator('div[class*="ProseMirror"][contenteditable]').first
            if not self.ui_helper.safe_fill(content_input, processed_text, "章节内容"):
                return 1
            
            # 点击下一步
            next_button = page.get_by_role("button", name="下一步")
            if not self.ui_helper.safe_click(next_button, "下一步按钮", retries=2):
                return 1
            
            time.sleep(0.5)
            
            # 处理可能的弹窗
            self._handle_popup_dialogs(page)
            
            # 选择AI选项
            try:
                page.locator(".arco-radio-text >> text=是").click(timeout=5000)
                time.sleep(0.3)
            except:
                pass
            
            # 设置定时发布
            if target_date or target_time:
                self._set_scheduled_publish(page, target_date, target_time)
            
            # 提交发布
            return self._submit_chapter(page, chap_number, chap_title)
            
        except Exception as e:
            logger.info(f"发布章节时发生错误: {e}")
            return 1
    
    def _handle_popup_dialogs(self, page: Page) -> None:
        """
        处理弹窗对话框
        
        Args:
            page: 页面对象
        """
        retry_times = 5
        while retry_times >= 0:
            time.sleep(0.3)
            retry_times -= 1
            for button_name in ["提交", "继续编辑本地", "确定", "确认"]:
                try:
                    button = page.get_by_role("button", name=button_name, exact=False)
                    button_text = button.text_content(timeout=100)
                    if "发布" not in button_text:
                        button.click(timeout=100)
                    time.sleep(0.3)
                except:
                    pass
    
    def _set_scheduled_publish(self, page: Page, target_date: Optional[str], target_time: Optional[str]) -> None:
        """
        设置定时发布
        
        Args:
            page: 页面对象
            target_date: 目标日期
            target_time: 目标时间
        """
        try:
            switch_button = page.get_by_role("switch")
            current_state = switch_button.get_attribute("aria-checked")
            if current_state == "false":
                switch_button.click()
                time.sleep(0.3)
            
            # 获取时间选择器
            all_pickers = page.locator('.arco-picker-start-time').all()
            page.wait_for_selector('.arco-picker-start-time', state='attached', timeout=12000)
            
            if len(all_pickers) < 2:
                raise Exception("未找到第二个时间选择器")
            
            # 设置日期
            if target_date:
                date_picker = all_pickers[0]
                date_picker.evaluate('''(el, date) => {
                    const prototype = HTMLInputElement.prototype;
                    const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    nativeSetter.call(el, date);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur'));
                }''', target_date)
                
                date_picker.click(timeout=2000)
                time.sleep(1)
                
                # 寻找日期
                self._find_target_date(page, target_date)
            
            # 设置时间
            if target_time:
                time_picker = all_pickers[1]
                time_picker.evaluate('''(el, time) => {
                    const prototype = HTMLInputElement.prototype;
                    const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    nativeSetter.call(el, time);
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new Event('blur'));
                }''', target_time)
                
                time_picker.click(timeout=2000)
                time.sleep(1)
                page.get_by_role("button", name="确定").click(timeout=12000)
                time.sleep(1)
                
        except Exception as e:
            logger.info(f"设置定时发布失败: {e}")
    
    def _find_target_date(self, page: Page, target_date: str) -> None:
        """
        寻找目标日期
        
        Args:
            page: 页面对象
            target_date: 目标日期
        """
        # 先尝试向前翻页
        timeout_cnt = 0
        date_found = False
        
        while timeout_cnt <= 12:
            try:
                selected_cell = page.locator('''
                    div.arco-picker-body 
                    >> div.arco-picker-row 
                    >> div.arco-picker-cell-selected
                ''')
                selected_cell.click(timeout=500)
                date_found = True
                break
            except Exception:
                next_selector = "div.arco-picker-header-icon:has(svg.arco-icon-right)"
                next_div = page.locator(next_selector)
                next_div.click(timeout=5000)
                timeout_cnt += 1
                time.sleep(1)
        
        # 如果向前翻页没找到，改为向后翻页
        if not date_found:
            logger.info("向前翻页12次未找到日期，改为向后翻页")
            back_count = 0
            max_back_count = 24
            
            while back_count < max_back_count and not date_found:
                try:
                    selected_cell = page.locator('''
                        div.arco-picker-body 
                        >> div.arco-picker-row 
                        >> div.arco-picker-cell-selected
                    ''')
                    selected_cell.click(timeout=500)
                    date_found = True
                    break
                except Exception:
                    prev_selector = "div.arco-picker-header-icon:has(svg.arco-icon-left)"
                    prev_div = page.locator(prev_selector)
                    prev_div.click(timeout=5000)
                    back_count += 1
                    time.sleep(1)
        
        if not date_found:
            logger.info(f"✗ 无法找到目标日期 {target_date}，发布失败，继续下一章")
    
    def _submit_chapter(self, page: Page, chap_number: str, chap_title: str) -> int:
        """
        提交章节发布
        
        Args:
            page: 页面对象
            chap_number: 章节号
            chap_title: 章节标题
            
        Returns:
            0-成功, 1-失败
        """
        try:
            # 处理可能的弹窗
            retry_times = 3
            while retry_times >= 0:
                time.sleep(0.5)
                retry_times -= 1
                for button_name in ["提交", "提交"]:
                    try:
                        button = page.get_by_role("button", name=button_name, exact=False)
                        button_text = button.text_content(timeout=100)
                        if "发布" not in button_text:
                            button.click(timeout=100)
                        time.sleep(0.5)
                    except:
                        pass
            
            # 确认发布
            confirm_button = page.get_by_role("button", name="确认发布")
            if self.ui_helper.safe_click(confirm_button, "确认发布按钮", retries=2):
                time.sleep(1)
                
                # 处理可能的弹窗
                retry_times = 3
                while retry_times >= 0:
                    time.sleep(0.5)
                    retry_times -= 1
                    for button_name in ["确定", "确认"]:
                        try:
                            button = page.get_by_role("button", name=button_name, exact=False)
                            button_text = button.text_content(timeout=100)
                            if "发布" not in button_text:
                                button.click(timeout=100)
                            time.sleep(0.5)
                        except:
                            pass
                
                # 验证发布成功
                divs = page.locator('div[class*="table-title"][class*="table-title-narrow"]')
                all_div_elements = divs.all()
                
                for element in all_div_elements:
                    element_inner_text = element.inner_text()
                    chap_no = f"""第{chap_number}章"""
                    if chap_title in element_inner_text and chap_no in element_inner_text:
                        logger.info(f"✓ 本章节 [{chap_no} {chap_title}] 发布成功,已确认! ")
                        return 0
                
                return 1
            
            return 1
            
        except Exception as e:
            logger.info(f"提交章节时出错: {e}")
            return 1
    
    def _load_publish_progress(self, novel_title: str) -> Dict[str, Any]:
        """
        加载发布进度
        
        Args:
            novel_title: 小说标题
            
        Returns:
            发布进度字典
        """
        progress_file = self.config_loader.get_progress_file() if self.config_loader else "发布进度.json"
        
        if not os.path.exists(progress_file):
            return {
                "published_chapters": [],
                "total_content_len": 0,
                "base_chapter_num": 0,
                "book_created": False
            }
        
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)
                progress = all_progress.get(novel_title, {
                    "published_chapters": [],
                    "total_content_len": 0,
                    "base_chapter_num": 0,
                    "book_created": False
                })
                
                # 确保有必要的字段
                if "base_chapter_num" not in progress:
                    progress["base_chapter_num"] = 0
                if "book_created" not in progress:
                    progress["book_created"] = False
                    
                return progress
        except:
            return {
                "published_chapters": [],
                "total_content_len": 0,
                "base_chapter_num": 0,
                "book_created": False
            }
    
    def _save_publish_progress(self, novel_title: str, progress: Dict[str, Any]) -> None:
        """
        保存发布进度
        
        Args:
            novel_title: 小说标题
            progress: 进度数据
        """
        progress_file = self.config_loader.get_progress_file() if self.config_loader else "发布进度.json"
        
        # 确保目录存在
        directory = os.path.dirname(progress_file) if os.path.dirname(progress_file) else "."
        self.file_handler.ensure_directory_exists(directory)
        
        # 加载现有进度
        all_progress = {}
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_progress = json.load(f)
            except:
                all_progress = {}
        
        # 更新当前小说的进度
        all_progress[novel_title] = {
            "published_chapters": progress.get("published_chapters", []),
            "total_content_len": progress.get("total_content_len", 0),
            "base_chapter_num": progress.get("base_chapter_num", 0),
            "book_created": progress.get("book_created", False),
            "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 保存进度
        try:
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(all_progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.info(f"保存发布进度时出错: {e}")
    
    def _check_if_novel_completed(self, json_file: str, published_chapters_count: int) -> bool:
        """
        检查小说是否已完成所有章节的发布
        
        Args:
            json_file: JSON文件路径
            published_chapters_count: 已发布章节数
            
        Returns:
            是否已完成
        """
        try:
            data = self.file_handler.load_json_file(json_file)
            if not data:
                return False
            
            if "progress" in data:
                progress = data["progress"]
                total_chapters = progress.get("total_chapters", 0)
                
                if total_chapters > 0 and published_chapters_count >= total_chapters:
                    return True
            
            return False
            
        except Exception as e:
            logger.info(f"检查小说完成状态时出错: {e}")
            return False
    
    def _restore_scheduled_publish_state(self, published_chapters: List[Dict[str, Any]], 
                                      publish_times: List[str], chapters_per_slot: int,
                                      now: datetime) -> Tuple[datetime.date, datetime.time]:
        """
        恢复定时发布状态
        
        Args:
            published_chapters: 已发布章节列表
            publish_times: 发布时间列表
            chapters_per_slot: 每个时间点的章节数
            now: 当前时间
            
        Returns:
            (当前日期, 当前时间)
        """
        # 找到最后一个设置了定时的章节
        timed_chapters = [chap for chap in published_chapters
                         if chap.get('target_date') and chap.get('target_time')]
        
        if timed_chapters:
            last_timed_chapter = timed_chapters[-1]
            last_date_str = last_timed_chapter.get('target_date', '')
            last_time_str = last_timed_chapter.get('target_time', '')
            last_slot_index = last_timed_chapter.get('time_slot_index', 0)
            
            if last_date_str and last_time_str:
                try:
                    last_datetime = datetime.strptime(f"{last_date_str} {last_time_str}", "%Y-%m-%d %H:%M")
                    last_date = last_datetime.date()
                    
                    if last_slot_index < chapters_per_slot:
                        # 继续使用相同的日期和时间
                        current_date = last_date
                        current_time = datetime.strptime(last_time_str, "%H:%M").time()
                        logger.info(f"✓ 恢复状态: 继续使用 {current_date} {current_time.strftime('%H:%M')} 的第 {last_slot_index + 1} 个位置")
                    else:
                        # 移动到下一个时间点
                        time_index = publish_times.index(last_time_str)
                        if time_index + 1 < len(publish_times):
                            next_time_str = publish_times[time_index + 1]
                            current_date = last_date
                            current_time = datetime.strptime(next_time_str, "%H:%M").time()
                            logger.info(f"✓ 恢复状态: 时间点已满，移动到同一天的下一个时间点 {current_date} {current_time.strftime('%H:%M')}")
                        else:
                            # 移动到下一天的第一个时间点
                            current_date = last_date + timedelta(days=1)
                            current_time = datetime.strptime(publish_times[0], "%H:%M").time()
                            logger.info(f"✓ 恢复状态: 当天时间点已满，移动到下一天 {current_date} {current_time.strftime('%H:%M')}")
                    
                    # 验证恢复的时间是否有效
                    restored_datetime = datetime.combine(current_date, current_time)
                    if restored_datetime <= now:
                        logger.info(f"⚠️  恢复的时间 {current_date} {current_time.strftime('%H:%M')} 已过期，使用当前时间")
                        return now.date(), now.time()
                    
                    return current_date, current_time
                    
                except Exception as e:
                    logger.info(f"恢复定时发布状态时出错: {e}, 将使用当前时间")
        
        return now.date(), now.time()
    
    def _handle_scheduled_publishing(self, page: Page, novel_title: str, 
                                   chapter_publish_info: List[Dict[str, Any]],
                                   current_chapter_index: int, published_chapters: List[Dict[str, Any]],
                                   total_content_len: int, json_file: str, progress: Dict[str, Any],
                                   now: datetime, current_date: datetime.date, current_time: datetime.time,
                                   publish_times: List[str], chapters_per_slot: int) -> bool:
        """
        处理定时发布逻辑
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            chapter_publish_info: 章节发布信息
            current_chapter_index: 当前章节索引
            published_chapters: 已发布章节
            total_content_len: 总字数
            json_file: JSON文件路径
            progress: 进度信息
            now: 当前时间
            current_date: 当前日期
            current_time: 当前时间
            publish_times: 发布时间列表
            chapters_per_slot: 每个时间点的章节数
            
        Returns:
            是否处理成功
        """
        # 初始化时间点使用情况跟踪
        date_time_slot_usage = {}
        
        # 从已发布的章节中恢复时间点使用情况
        for chap in published_chapters:
            if chap.get('target_date') and chap.get('target_time'):
                date = chap['target_date']
                time_slot = chap['target_time']
                if date not in date_time_slot_usage:
                    date_time_slot_usage[date] = {}
                if time_slot not in date_time_slot_usage[date]:
                    date_time_slot_usage[date][time_slot] = 0
                date_time_slot_usage[date][time_slot] += 1
        
        # 主发布循环
        while current_chapter_index < len(chapter_publish_info):
            current_chapter = chapter_publish_info[current_chapter_index]
            if current_chapter['published']:
                current_chapter_index += 1
                continue
            
            # 查找可用的时间点
            found_available_slot = False
            target_date = None
            target_time = None
            
            # 在多个日期中查找可用时间点
            for day_offset in range(30):
                search_date = current_date + timedelta(days=day_offset)
                date_str = search_date.strftime('%Y-%m-%d')
                
                if date_str not in date_time_slot_usage:
                    date_time_slot_usage[date_str] = {}
                
                # 检查该日期的每个时间点
                for time_slot in publish_times:
                    current_count = date_time_slot_usage[date_str].get(time_slot, 0)
                    
                    if current_count < chapters_per_slot:
                        # 验证时间是否有效
                        slot_datetime = datetime.strptime(f"{date_str} {time_slot}", "%Y-%m-%d %H:%M")
                        buffer_minutes = self.config_loader.get_publish_buffer_minutes() if self.config_loader else 35
                        
                        if slot_datetime > now + timedelta(minutes=buffer_minutes):
                            target_date = search_date
                            target_time = datetime.strptime(time_slot, "%H:%M").time()
                            found_available_slot = True
                            break
                
                if found_available_slot:
                    break
            
            if not found_available_slot:
                logger.info("✗ 在30天内未找到可用的发布时间点")
                break
            
            # 发布当前章节
            chap_file = current_chapter['file']
            chap_num = current_chapter['chap_num']
            chap_title = current_chapter['chap_title']
            chap_content = current_chapter['chap_content']
            chap_len = current_chapter['chap_len']
            
            if not self.ui_helper.check_and_recover_page(page):
                logger.info("页面已失效，无法继续发布")
                return False
            
            target_date_str = target_date.strftime('%Y-%m-%d')
            target_time_str = target_time.strftime('%H:%M')
            
            # 获取当前时间点的使用计数
            current_count = date_time_slot_usage.get(target_date_str, {}).get(target_time_str, 0)
            time_slot_index = current_count + 1
            
            logger.info(f"\n发布第 {chap_num} 章: {chap_title} (字数: {chap_len})")
            logger.info(f"定时发布: {target_date_str} {target_time_str} (第 {time_slot_index} 个位置)")
            
            # 发布章节
            result = self._verify_and_create_chapter(
                page, novel_title, chap_num, chap_title, chap_content,
                target_date_str, target_time_str
            )
            
            if result == 0:
                total_content_len += chap_len
                current_chapter.update({
                    'published': True,
                    'target_date': target_date_str,
                    'target_time': target_time_str,
                    'time_slot_index': time_slot_index
                })
                published_chapters.append(current_chapter.copy())
                
                progress["published_chapters"] = published_chapters
                progress["total_content_len"] = total_content_len
                self._save_publish_progress(novel_title, progress)
                
                logger.info(f"✓ 发布成功 (累计字数: {total_content_len})")
                
                # 更新时间点使用计数
                if target_date_str not in date_time_slot_usage:
                    date_time_slot_usage[target_date_str] = {}
                date_time_slot_usage[target_date_str][target_time_str] = time_slot_index
                
                # 检查是否完成所有章节
                if self._check_if_novel_completed(json_file, len(published_chapters)):
                    logger.info(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                    if self.file_handler.move_completed_novel_to_published(novel_title, json_file):
                        return True
            else:
                logger.info("✗ 发布失败")
                self.ui_helper.wait_for_enter("发布失败，按回车继续下一章...", timeout=10)
            
            current_chapter_index += 1
        
        return False