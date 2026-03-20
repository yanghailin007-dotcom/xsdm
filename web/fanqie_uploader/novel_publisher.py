"""
小说发布核心模块 - 修复版
修复了标签选择和封面上传功能
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
        兼容旧格式：从 project_info/ 目录加载项目信息
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
        
        # 兼容旧格式：从 project_info/ 目录加载额外数据
        json_file_path = Path(json_file)
        project_dir = json_file_path.parent
        self._load_legacy_project_info(project_dir, data)
        
        # 适配两种数据格式：直接字段或嵌套 novel_info
        if 'novel_info' in data and isinstance(data['novel_info'], dict):
            novel_title = data['novel_info'].get('title', '')
            novel_synopsis = data['novel_info'].get('synopsis', '')
            selected_plan = data['novel_info'].get('selected_plan', {})
            logger.info("[Publisher] 使用嵌套 novel_info 格式")
        else:
            # 旧格式：扁平结构
            novel_title = data.get('novel_title', '')
            novel_synopsis = data.get('synopsis', '') or data.get('novel_synopsis', '')
            selected_plan = data.get('selected_plan', {})
            logger.info("[Publisher] 使用直接字段格式（旧格式）")
        
        if not novel_title:
            logger.info(f"✗ 小说标题为空，请检查项目文件格式")
            return False
        
        # 处理主角名 - 优先从selected_plan中获取（兼容新旧格式）
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
            # 🔍 先检查番茄平台上是否已有该书
            logger.info("[Publisher] 检查番茄平台上是否已有该书...")
            existing_book_url = self._check_book_exists_on_fanqie(page, novel_title)
            if existing_book_url:
                logger.info(f"[Publisher] ✓ 书籍已在番茄平台存在: {existing_book_url}")
                progress["book_created"] = True
                progress["book_url"] = existing_book_url
                self._save_publish_progress(novel_title, progress)
            else:
                logger.info("书籍未创建，开始创建新书...")
                if self._create_new_book(page, novel_title, formatted_synopsis, main_character, data, project_dir):
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
    
    def _create_new_book(self, page: Page, novel_title: str, formatted_synopsis: str, 
                        main_character: str, novel_data: Dict[str, Any], project_dir: Path) -> bool:
        """
        创建新书 - 完整版（含标签选择和封面上传）
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            formatted_synopsis: 格式化的简介
            main_character: 主角名
            novel_data: 小说数据
            project_dir: 项目目录
            
        Returns:
            是否创建成功
        """
        logger.info("[Publisher] 开始创建新书...")
        
        # 调试截图路径
        debug_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'debug_screenshots')
        os.makedirs(debug_dir, exist_ok=True)
        
        # 检查页面是否仍然有效
        try:
            page_url = page.url
            logger.info(f"[Publisher] 当前页面URL: {page_url}")
            # 尝试一个简单的JS执行来验证页面确实活着
            page.evaluate("() => document.readyState")
        except Exception as e:
            logger.info(f"[Publisher] ⚠️ 页面可能已断开: {e}")
            logger.info("[Publisher] 可能原因: 1.Chrome被手动关闭 2.Chrome崩溃 3.页面被刷新")
            logger.info("[Publisher] 建议: 1.检查Chrome是否还在运行 2.刷新页面后重新上传")
            return False
        
        # 重试机制
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"[Publisher] 访问创建作品页面... (尝试 {attempt + 1}/{max_retries})")
                
                # 先检查网络状态
                try:
                    page.evaluate("() => navigator.onLine")
                except:
                    logger.info("[Publisher] ⚠️ 页面上下文已丢失")
                    return False
                
                page.goto("https://fanqienovel.com/main/writer/create?enter_from=home", timeout=30000, wait_until="domcontentloaded")
                
                # 等待页面稳定
                time.sleep(2)
                
                # 验证页面是否成功加载
                current_url = page.url
                if "fanqienovel.com" not in current_url:
                    logger.info(f"[Publisher] ⚠️ 页面可能未正确加载，当前URL: {current_url}")
                    if attempt < max_retries - 1:
                        continue
                
                break  # 成功则跳出循环
            except Exception as e:
                logger.info(f"[Publisher] ⚠️ 导航失败 (尝试 {attempt + 1}): {str(e)[:200]}")
                if attempt == max_retries - 1:
                    logger.info("[Publisher] ✗ 所有重试都失败")
                    logger.info("[Publisher] 可能原因: Chrome调试端口被占用、网络问题、番茄网站访问受限")
                    return False
                time.sleep(3)  # 等待后重试
            
        logger.info(f"当前URL: {page.url}")
        
        # 截图记录
        try:
            screenshot_path = os.path.join(debug_dir, f'create_book_form_{int(time.time())}.png')
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"页面截图已保存: {screenshot_path}")
        except Exception as e:
            logger.info(f"截图失败: {e}")
        
        # ===== 1. 填写书名 =====
        title_short = novel_title[:14] if len(novel_title) > 14 else novel_title
        try:
            title_input = page.locator('input[placeholder="请输入作品名称"]').first
            title_input.wait_for(state='visible', timeout=5000)
            title_input.fill(title_short)
            logger.info(f"✓ 填写书名: {title_short}")
        except Exception as e:
            logger.info(f"✗ 填写书名失败: {e}")
            return False
        
        # ===== 2. 选择男女频 =====
        if "novel_info" in novel_data and isinstance(novel_data["novel_info"], dict):
            tags_info = novel_data.get("novel_info", {}).get("selected_plan", {}).get("tags", {})
        else:
            selected_plan = novel_data.get("selected_plan", {})
            if isinstance(selected_plan, dict):
                tags_info = selected_plan.get("tags", {})
            else:
                tags_info = {}
        gender = tags_info.get("target_audience", "男频")
        
        try:
            if gender == "女频":
                page.locator('label:has-text("女频")').first.click()
                logger.info("✓ 选择女频")
            else:
                page.locator('label:has-text("男频")').first.click()
                logger.info("✓ 选择男频")
            time.sleep(0.5)
        except Exception as e:
            logger.info(f"⚠ 选择男/女频失败: {e}")
        
        # ===== 3. 选择作品标签 =====
        logger.info("[Publisher] 准备选择作品标签...")
        try:
            self._select_book_tags_v2(page, tags_info)
        except Exception as e:
            logger.info(f"⚠ 选择作品标签失败: {e}")
        
        # ===== 4. 处理封面 =====
        logger.info("[Publisher] 准备处理封面...")
        try:
            cover_result = self._handle_cover_upload(page, novel_title, project_dir)
            if not cover_result:
                logger.info("⚠ 封面处理未完成，继续创建...")
        except Exception as e:
            logger.info(f"⚠ 封面上传失败: {e}")
        
        # ===== 5. 填写主角名 =====
        character_short = main_character[:5] if len(main_character) >= 5 else main_character
        try:
            character_input = page.locator('input[placeholder="请输入主角名1"]').first
            character_input.fill(character_short)
            logger.info(f"✓ 填写主角名: {character_short}")
        except Exception as e:
            logger.info(f"⚠ 填写主角名失败: {e}")
        
        # ===== 6. 填写作品简介 =====
        synopsis_short = formatted_synopsis[:500] if len(formatted_synopsis) >= 500 else formatted_synopsis
        try:
            synopsis_input = page.locator('textarea').first
            synopsis_input.fill(synopsis_short)
            logger.info("✓ 填写作品简介")
        except Exception as e:
            logger.info(f"⚠ 填写简介失败: {e}")
        
        # 截图记录填写结果
        try:
            screenshot_path = os.path.join(debug_dir, f'create_book_filled_{int(time.time())}.png')
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"填写后截图: {screenshot_path}")
        except:
            pass
        
        # ===== 7. 点击立即创建 =====
        logger.info("[Publisher] 点击立即创建...")
        try:
            create_button = page.locator('button:has-text("立即创建")').first
            create_button.wait_for(state='visible', timeout=5000)
            create_button.click()
            logger.info("✓ 点击立即创建")
        except Exception as e:
            logger.info(f"✗ 点击立即创建失败: {e}")
            return False
        
        # 等待创建完成
        logger.info("[Publisher] 等待创建完成...")
        time.sleep(3)
        
        # 检查是否有错误提示（排除成功消息）
        try:
            error_msg = page.locator('.arco-message-content, .error-message, [class*="error"]').first
            if error_msg.count() > 0 and error_msg.is_visible():
                error_text = error_msg.text_content() or ""
                # 排除成功消息
                if "成功" in error_text or "success" in error_text.lower():
                    logger.info(f"✓ 操作成功提示: {error_text}")
                else:
                    logger.info(f"✗ 创建失败，错误信息: {error_text}")
                    return False
        except:
            pass
        
        # 等待跳转到书籍详情页
        for i in range(10):
            time.sleep(1)
            current_url = page.url
            if "/main/writer/book/" in current_url or "/main/writer/novel/" in current_url:
                logger.info(f"✓ 书籍创建成功，已跳转到详情页: {current_url}")
                return True
            # 检查是否还在创建页面
            if "/main/writer/create" in current_url:
                logger.info(f"仍在创建页面，等待中... ({i+1}/10)")
        
        logger.info("✗ 等待超时，无法确认创建是否成功")
        return False
    
    def _check_book_exists_on_fanqie(self, page: Page, novel_title: str) -> Optional[str]:
        """
        检查番茄平台上是否已有该书
        需要导航到作者后台书籍管理页面进行检查
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            
        Returns:
            书籍URL或None
        """
        try:
            # 检查当前URL
            current_url = page.url
            logger.info(f"[Publisher] 当前页面URL: {current_url}")
            
            # 如果已经在章节管理页面，说明书籍已存在
            if "/chapter-manage/" in current_url:
                book_id = current_url.split("/chapter-manage/")[-1].split("/")[0]
                if book_id and book_id.isdigit():
                    logger.info(f"[Publisher] 当前在章节管理页面，书籍已存在: {book_id}")
                    return current_url
            
            # 如果已经在书籍详情页
            if "/book-info/" in current_url:
                book_id = current_url.split("/book-info/")[-1].split("/")[0]
                if book_id and book_id.isdigit():
                    logger.info(f"[Publisher] 当前在书籍详情页，书籍已存在: {book_id}")
                    return f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
            
            # 如果不在作者后台页面，导航到书籍管理页面
            if "/main/writer" not in current_url:
                logger.info("[Publisher] 当前不在作者后台，导航到书籍管理页面...")
                try:
                    page.goto("https://fanqienovel.com/main/writer/book-manage", 
                             wait_until="networkidle", timeout=15000)
                    time.sleep(3)
                    logger.info(f"[Publisher] 已导航到: {page.url}")
                except Exception as e:
                    logger.info(f"[Publisher] 导航到书籍管理页面失败: {e}")
                    return None
            
            # 在作者后台页面检查是否包含书名
            try:
                title_short = novel_title[:10]
                logger.info(f"[Publisher] 在书籍管理页面查找书名: {title_short}...")
                
                # 等待页面内容加载
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # 检查页面内容
                page_text = page.content()
                if title_short in page_text or novel_title[:8] in page_text:
                    logger.info("[Publisher] 页面内容包含书名，尝试提取书籍ID")
                    import re
                    book_ids = re.findall(r'long-article-table-item-(\d+)', page_text)
                    if book_ids:
                        # 尝试找到匹配的书籍ID
                        for book_id in book_ids:
                            # 检查该书籍条目的标题
                            book_elem = page.locator(f'#long-article-table-item-{book_id}')
                            if book_elem.count() > 0:
                                title_elem = book_elem.locator('.info-content-title').first
                                if title_elem.count() > 0:
                                    title_text = title_elem.text_content().strip()
                                    if novel_title[:10] in title_text or title_text[:10] in novel_title:
                                        url = f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
                                        logger.info(f"[Publisher] 找到匹配书籍: {title_text} -> {url}")
                                        return url
                        # 如果没找到匹配的，返回第一个
                        book_id = book_ids[0]
                        url = f"https://fanqienovel.com/main/writer/chapter-manage/{book_id}"
                        logger.info(f"[Publisher] 找到书籍链接: {url}")
                        return url
            except Exception as e:
                logger.info(f"[Publisher] 页面检查失败: {e}")
            
            logger.info("[Publisher] 未找到已存在的书籍")
            return None
        except Exception as e:
            logger.info(f"[Publisher] 检查书籍存在性时出错: {e}")
            return None
    
    def _select_book_tags_v2(self, page: Page, tags_info: Dict[str, Any]) -> bool:
        """
        选择作品标签 - V2版本（适配番茄最新界面）
        
        Args:
            page: 页面对象
            tags_info: 标签信息
            
        Returns:
            是否选择成功
        """
        logger.info("[Tags] 开始选择作品标签...")
        
        try:
            # 点击作品标签下拉框
            tag_selector = page.locator('.select-row, .select-view, [placeholder*="请选择作品标签"]').first
            if tag_selector.count() == 0:
                logger.info("[Tags] 未找到标签选择器")
                return False
            
            tag_selector.click()
            logger.info("[Tags] 已点击标签选择器")
            time.sleep(2)
            
            # 获取要选择的标签
            main_category = tags_info.get("main_category", "")
            themes = tags_info.get("themes", [])
            roles = tags_info.get("roles", [])
            plots = tags_info.get("plots", [])
            
            logger.info(f"[Tags] 需要选择的标签: 主分类={main_category}, 主题={themes}, 角色={roles}, 情节={plots}")
            
            # 选择主分类（标签页名称为"主分类"）
            if main_category:
                if self._click_tag_in_modal(page, "主分类", main_category):
                    logger.info(f"[Tags] ✓ 选择主分类: {main_category}")
                else:
                    logger.info(f"[Tags] ⚠ 未找到主分类: {main_category}")
            
            # 选择主题（最多3个）
            selected_themes = 0
            for theme in themes[:3]:
                if self._click_tag_in_modal(page, "主题", theme):
                    logger.info(f"[Tags] ✓ 选择主题: {theme}")
                    selected_themes += 1
                    time.sleep(0.3)
                else:
                    logger.info(f"[Tags] ⚠ 未找到主题: {theme}")
            logger.info(f"[Tags] 主题选择完成: {selected_themes}/{len(themes)}")
            
            # 选择角色（最多3个）
            selected_roles = 0
            for role in roles[:3]:
                if self._click_tag_in_modal(page, "角色", role):
                    logger.info(f"[Tags] ✓ 选择角色: {role}")
                    selected_roles += 1
                    time.sleep(0.3)
                else:
                    logger.info(f"[Tags] ⚠ 未找到角色: {role}")
            logger.info(f"[Tags] 角色选择完成: {selected_roles}/{len(roles)}")
            
            # 选择情节（最多3个）
            selected_plots = 0
            for plot in plots[:3]:
                if self._click_tag_in_modal(page, "情节", plot):
                    logger.info(f"[Tags] ✓ 选择情节: {plot}")
                    selected_plots += 1
                    time.sleep(0.3)
                else:
                    logger.info(f"[Tags] ⚠ 未找到情节: {plot}")
            logger.info(f"[Tags] 情节选择完成: {selected_plots}/{len(plots)}")
            
            # 点击确认按钮
            try:
                confirm_btn = page.locator('button:has-text("确认"), button:has-text("确定"), .arco-btn-primary').filter(
                    has_text=re.compile(r'(确认|确定)')
                ).first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    logger.info("[Tags] ✓ 点击确认按钮")
                    time.sleep(1)
                else:
                    # 备选：点击弹窗外部关闭
                    page.keyboard.press("Escape")
                    logger.info("[Tags] 按ESC关闭标签弹窗")
            except Exception as e:
                logger.info(f"[Tags] 关闭标签弹窗时出错: {e}")
            
            return True
            
        except Exception as e:
            logger.info(f"[Tags] 选择标签时出错: {e}")
            return False
    
    def _click_tag_in_modal(self, page: Page, category: str, tag_name: str) -> bool:
        """
        在标签弹窗中点击指定标签
        
        Args:
            page: 页面对象
            category: 分类名称（分类/主题/角色/情节）
            tag_name: 标签名称
            
        Returns:
            是否点击成功
        """
        try:
            # 首先点击分类标签页（尝试多种选择器）
            tab_selectors = [
                f'.arco-tabs-header-title:has-text("{category}")',
                f'[role="tab"]:has-text("{category}")',
                f'text="{category}" >> xpath=ancestor::*[@role="tab" or contains(@class, "arco-tabs-header-title")]',
            ]
            
            for selector in tab_selectors:
                try:
                    tab = page.locator(selector).first
                    if tab.count() > 0 and tab.is_visible():
                        tab.click()
                        time.sleep(0.5)
                        break
                except Exception:
                    continue
            
            # 在当前标签页中查找标签
            # 策略1: 直接查找标签文本（尝试多种选择器）
            selectors = [
                f'.category-choose-item:has-text("{tag_name}")',
                f'.tag-item:has-text("{tag_name}")',
                f'text="{tag_name}"',
                f'[role="tabpanel"] >> text="{tag_name}"',
            ]
            
            for selector in selectors:
                try:
                    tag = page.locator(selector).first
                    if tag.count() > 0 and tag.is_visible():
                        tag.click()
                        time.sleep(0.3)
                        return True
                except Exception:
                    continue
            
            # 策略2: 滚动查找
            scroll_container = page.locator('.category-choose-scroll-parent, .arco-tabs-content-item-active').first
            if scroll_container.count() > 0:
                for _ in range(10):  # 最多滚动10次
                    try:
                        tag = scroll_container.locator(f'.category-choose-item:has-text("{tag_name}")').first
                        if tag.count() > 0 and tag.is_visible():
                            tag.click()
                            time.sleep(0.3)
                            return True
                    except Exception:
                        pass
                    # 滚动
                    scroll_container.evaluate('el => el.scrollTop += 200')
                    time.sleep(0.3)
            
            # 策略3: 使用JavaScript查找（最可靠的方式）
            clicked = page.evaluate(f'''(tagName) => {{
                // 方法1: 直接匹配 category-choose-item-title
                const titles = document.querySelectorAll('.category-choose-item-title');
                for (const title of titles) {{
                    if (title.textContent.trim() === tagName) {{
                        const item = title.closest('.category-choose-item');
                        if (item) {{
                            item.click();
                            return true;
                        }}
                    }}
                }}
                
                // 方法2: 匹配整个 item 的 textContent
                const items = document.querySelectorAll('.category-choose-item, .tag-item');
                for (const item of items) {{
                    const titleEl = item.querySelector('.category-choose-item-title');
                    if (titleEl && titleEl.textContent.trim() === tagName) {{
                        item.click();
                        return true;
                    }}
                    // 也尝试直接匹配整个元素的文本
                    if (item.textContent.trim().startsWith(tagName)) {{
                        item.click();
                        return true;
                    }}
                }}
                
                // 方法3: 使用 XPath
                const xpath = `//div[contains(@class, 'category-choose-item-title') and text()='${{tagName}}']`;
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const node = result.singleNodeValue;
                if (node) {{
                    const item = node.closest('.category-choose-item');
                    if (item) {{
                        item.click();
                        return true;
                    }}
                }}
                
                return false;
            }}''', tag_name)
            
            return clicked
            
        except Exception as e:
            logger.info(f"[Tags] 点击标签 '{tag_name}' 失败: {e}")
            return False
    
    def _handle_cover_upload(self, page: Page, novel_title: str, project_dir: Path) -> bool:
        """
        处理封面上传
        
        Args:
            page: 页面对象
            novel_title: 小说标题
            project_dir: 项目目录
            
        Returns:
            是否上传成功
        """
        logger.info("[Cover] 开始处理封面...")
        
        # 查找封面文件（项目目录）
        cover_paths = [
            project_dir / "cover.png",
            project_dir / "cover.jpg",
            project_dir / "cover.jpeg",
            project_dir / f"{novel_title}_封面.png",
            project_dir / f"{novel_title}_封面.jpg",
            project_dir / "images" / "cover.png",
            project_dir / "images" / "cover.jpg",
        ]
        
        cover_file = None
        for path in cover_paths:
            if path.exists():
                cover_file = path
                break
        
        # 如果在项目目录没找到，检查 generated_images 目录
        if not cover_file:
            logger.info("[Cover] 在项目目录未找到封面，检查 generated_images 目录...")
            
            # 获取用户名
            username = ""
            try:
                # 从 project_dir 提取用户名
                # project_dir 格式: .../小说项目/{username}/{novel_title}
                parts = project_dir.parts
                if "小说项目" in parts or "novel_projects" in parts:
                    for i, part in enumerate(parts):
                        if part in ["小说项目", "novel_projects"] and i + 1 < len(parts):
                            username = parts[i + 1]
                            break
            except:
                pass
            
            # 构建 generated_images 路径
            base_dir = project_dir.parent.parent.parent  # 项目根目录
            generated_images_dir = base_dir / "generated_images" / username / novel_title
            
            logger.info(f"[Cover] 检查目录: {generated_images_dir}")
            
            if generated_images_dir.exists():
                # 查找图片文件
                image_extensions = ['.png', '.jpg', '.jpeg', '.webp']
                cover_files = []
                
                for ext in image_extensions:
                    cover_files.extend(generated_images_dir.glob(f'*{ext}'))
                
                if cover_files:
                    # 按修改时间排序，取最新的
                    cover_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    cover_file = cover_files[0]
                    logger.info(f"[Cover] 在 generated_images 找到封面: {cover_file.name}")
        
        if not cover_file:
            logger.info("[Cover] ⚠ 未找到封面文件，跳过封面上传")
            logger.info("[Cover] 建议路径:")
            logger.info(f"  - {project_dir / 'cover.png'}")
            logger.info(f"  - {base_dir / 'generated_images' / '{username}' / novel_title}")
            return False
        
        logger.info(f"[Cover] 找到封面文件: {cover_file}")
        
        try:
            # 点击选择封面按钮
            cover_btn = page.locator('button:has-text("选择封面"), .left-cover-container button').first
            if cover_btn.count() == 0:
                logger.info("[Cover] 未找到'选择封面'按钮")
                return False
            
            cover_btn.click()
            logger.info("[Cover] 已点击选择封面按钮")
            time.sleep(2)
            
            # 等待上传弹窗
            page.wait_for_selector('.arco-modal, [class*="modal"], [class*="upload"]', timeout=5000)
            
            # 查找文件输入框
            file_input = page.locator('input[type="file"]').first
            if file_input.count() == 0:
                logger.info("[Cover] 未找到文件输入框，尝试点击上传区域...")
                # 点击上传区域
                upload_area = page.locator('.upload-area, .cover-upload, [class*="upload"]').first
                if upload_area.count() > 0:
                    upload_area.click()
                    time.sleep(1)
                    file_input = page.locator('input[type="file"]').first
            
            if file_input.count() > 0:
                file_input.set_input_files(str(cover_file))
                logger.info(f"[Cover] 已选择文件: {cover_file}")
                time.sleep(3)  # 等待上传
                
                # 点击确认
                confirm_btn = page.locator('button:has-text("确认"), button:has-text("确定"), button:has-text("保存")').last
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    logger.info("[Cover] 已点击确认")
                    time.sleep(1)
                
                logger.info("[Cover] ✓ 封面上传完成")
                return True
            else:
                logger.info("[Cover] 无法找到文件输入框")
                # 关闭弹窗
                page.keyboard.press("Escape")
                return False
                
        except Exception as e:
            logger.info(f"[Cover] 封面上传失败: {e}")
            # 确保弹窗关闭
            try:
                page.keyboard.press("Escape")
            except:
                pass
            return False
    
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
        # 查找章节文件 - 从 json_file 所在目录查找
        json_file_path = Path(json_file)
        project_dir = json_file_path.parent
        
        # 支持的章节目录名（按优先级排序）
        possible_chapter_dirs = [
            os.path.join(project_dir, "chapters"),  # 优先检查 chapters 目录
            os.path.join(project_dir, f"{novel_title}_章节"),  # 兼容旧命名
        ]
        
        chapter_path = None
        for path in possible_chapter_dirs:
            if os.path.exists(path):
                chapter_path = path
                logger.info(f"[Publisher] 找到章节目录: {path}")
                break
        
        # 如果项目目录下没找到，回退到旧路径逻辑（兼容旧路径）
        if not chapter_path and self.config_loader:
            legacy_path = os.path.join(
                self.config_loader.get_novel_path(),
                f"{novel_title}_章节"
            )
            if os.path.exists(legacy_path):
                chapter_path = legacy_path
                logger.info(f"[Publisher] 使用旧路径章节目录: {chapter_path}")
        
        if not chapter_path:
            logger.info(f"章节目录不存在，已尝试以下路径:")
            for path in possible_chapter_dirs:
                logger.info(f"  - {path}")
            logger.info(f"项目目录: {project_dir}")
            logger.info("请确保章节文件位于 'chapters' 或 '{小说名}_章节' 目录中")
            return False
        
        # 获取章节文件（支持 .txt 和 .json 格式）
        chapter_files = []
        for filename in os.listdir(chapter_path):
            if filename.endswith('.txt') or filename.endswith('.json'):
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
    def _load_publish_progress(self, novel_title: str) -> Dict[str, Any]:
        """加载发布进度"""
        # 简化实现
        return {"book_created": False, "published_chapters": []}
    
    def _save_publish_progress(self, novel_title: str, progress: Dict[str, Any]) -> None:
        """保存发布进度"""
        pass
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
        
        # 从 book_url 提取 book_id
        book_id = None
        book_url = progress.get("book_url", "")
        if book_url:
            book_id_match = re.search(r'/chapter-manage/(\d+)', book_url)
            if book_id_match:
                book_id = book_id_match.group(1)
                logger.info(f"[Publisher] 从进度中提取书籍ID: {book_id}")
        
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
                    current_chapter['chap_content'], None, None, book_id
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
                now, current_date, current_time, publish_times, chapters_per_slot, book_id
            )
            
            if success:
                return True
            else:
                break
        
        logger.info(f"\n✓ 小说《{novel_title}》发布完成，共 {len(chapter_files)} 章，总字数 {total_content_len}")
        return True

    def _verify_and_create_chapter(self, page: Page, expected_book_title: str, chap_number: str,
                                chap_title: str, chap_content: str, target_date: Optional[str] = None,
                                target_time: Optional[str] = None, book_id: Optional[str] = None) -> int:
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
            book_id: 书籍ID（用于点击创建章节按钮）
            
        Returns:
            0-成功, 1-失败, 2-需要重新导航
        """
        try:
            # 检查是否在创建章节页面
            current_url = page.url
            if "/publish/" not in current_url:
                logger.info("当前不在创建章节页面，尝试点击'创建章节'按钮...")
                
                # 尝试从当前页面提取book_id
                if not book_id:
                    book_id_match = re.search(r'/chapter-manage/(\d+)', current_url)
                    if book_id_match:
                        book_id = book_id_match.group(1)
                
                if not book_id:
                    # 从页面内容中查找书籍ID
                    page_content = page.content()
                    book_ids = re.findall(r'long-article-table-item-(\d+)', page_content)
                    if book_ids:
                        # 查找匹配书籍标题的ID
                        for bid in book_ids:
                            book_elem = page.locator(f'#long-article-table-item-{bid}')
                            if book_elem.count() > 0:
                                title_elem = book_elem.locator('.info-content-title').first
                                if title_elem.count() > 0:
                                    title_text = title_elem.text_content().strip()
                                    if expected_book_title[:10] in title_text:
                                        book_id = bid
                                        logger.info(f"找到匹配的书籍ID: {book_id}")
                                        break
                        if not book_id:
                            book_id = book_ids[0]  # 使用第一个
                
                if book_id:
                    # 先悬停到书籍条目上，让按钮显示
                    book_item = page.locator(f'#long-article-table-item-{book_id}')
                    if book_item.count() > 0:
                        logger.info(f"悬停到书籍条目: {book_id}")
                        book_item.first.hover()
                        time.sleep(1)
                    
                    # 查找并点击"创建章节"按钮
                    # 按钮可能在当前书籍条目内
                    create_btn = page.locator(f'#long-article-table-item-{book_id} a[href*="/publish/"] button, #long-article-table-item-{book_id} button:has-text("创建章节")').first
                    if create_btn.count() == 0:
                        # 尝试更通用的选择器
                        create_btn = page.locator('a[href*="/publish/"] button:has-text("创建章节"), button:has-text("创建章节")').first
                    
                    new_page = None
                    
                    if create_btn.count() > 0 and create_btn.is_visible():
                        logger.info("点击'创建章节'按钮...")
                        # 处理可能的新标签页（target="_blank"）
                        try:
                            with page.expect_popup(timeout=10000) as popup_info:
                                create_btn.click()
                            new_page = popup_info.value
                            logger.info("检测到新标签页打开")
                        except:
                            # 没有新标签页，在当前页打开
                            logger.info("在当前页打开")
                            time.sleep(5)
                    else:
                        # 尝试点击链接
                        create_link = page.locator(f'#long-article-table-item-{book_id} a[href*="/publish/"]').first
                        if create_link.count() == 0:
                            create_link = page.locator('a[href*="/publish/"]').first
                        if create_link.count() > 0:
                            logger.info("点击'创建章节'链接...")
                            try:
                                with page.expect_popup(timeout=10000) as popup_info:
                                    create_link.click()
                                new_page = popup_info.value
                                logger.info("检测到新标签页打开")
                            except:
                                logger.info("在当前页打开")
                                time.sleep(5)
                        else:
                            logger.info("未找到'创建章节'按钮或链接")
                            return 2
                    
                    # 如果打开了新标签页，切换到新页面
                    if new_page:
                        logger.info("切换到新标签页...")
                        page = new_page
                        time.sleep(3)
                    
                    # 处理可能的安全验证弹窗
                    logger.info("检查并处理安全验证弹窗...")
                    self._handle_security_verification(page)
                    
                else:
                    logger.info("无法获取书籍ID，无法点击创建章节")
                    return 2
            
            # 等待页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 验证书名（支持部分匹配，因为番茄可能截断显示）
            header_book_name = page.locator('.publish-header-book-name')
            if header_book_name.count() > 0:
                actual_title = header_book_name.first.text_content().strip()
                # 双向部分匹配：期望包含实际 或 实际包含期望（取前15字比较）
                expected_short = expected_book_title[:15]
                actual_short = actual_title[:15]
                if expected_short not in actual_title and actual_short not in expected_book_title:
                    logger.info(f"✗ 创建章节页面书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                    return 2
                logger.info(f"✓ 书名匹配: {actual_title}")
            
            # 检查是否找到了章节输入框
            # 根据实际HTML：第一个输入框是章节号，第二个是标题
            input_selectors = [
                '.serial-editor-title-left input.serial-input',  # 章节号
                '.serial-editor-title-right input.serial-input',  # 标题
                'input[placeholder="请输入标题"]',
                '.serial-editor-container input.serial-input',
                'input.serial-input.byte-input.byte-input-size-default'
            ]
            
            # 查找章节号输入框
            chapter_num_input = None
            for selector in input_selectors[:2]:  # 优先使用精确选择器
                try:
                    elem = page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        chapter_num_input = elem
                        logger.info(f"找到章节号输入框: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 出错: {e}")
            
            # 查找标题输入框
            chapter_title_input = None
            for selector in [input_selectors[1], input_selectors[2]]:  # 标题选择器
                try:
                    elem = page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible():
                        chapter_title_input = elem
                        logger.info(f"找到标题输入框: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"选择器 '{selector}' 出错: {e}")
            
            # 如果没找到，尝试通用选择器
            if not chapter_num_input or not chapter_title_input:
                logger.info("精确选择器未找到，尝试通用选择器...")
                all_inputs = page.locator('input.serial-input')
                count = all_inputs.count()
                logger.info(f"通用选择器找到 {count} 个输入框")
                
                if count >= 2:
                    chapter_num_input = all_inputs.nth(0)
                    chapter_title_input = all_inputs.nth(1)
            
            if not chapter_num_input or not chapter_title_input:
                logger.info("未找到章节输入框，等待页面完全加载...")
                time.sleep(5)
                
                # 再次尝试通用选择器
                all_inputs = page.locator('input.serial-input')
                if all_inputs.count() >= 2:
                    chapter_num_input = all_inputs.nth(0)
                    chapter_title_input = all_inputs.nth(1)
                
                if not chapter_num_input or not chapter_title_input:
                    logger.info("等待后仍未找到章节输入框")
                    logger.info(f"当前页面URL: {page.url}")
                    return 2
            
            # 填写章节序号和标题
            if not self.ui_helper.safe_fill(chapter_num_input, chap_number, "章节序号"):
                return 1
            if not self.ui_helper.safe_fill(chapter_title_input, chap_title, "章节标题"):
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
    
    def _handle_security_verification(self, page: Page) -> None:
        """
        处理安全验证弹窗（如滑块验证、人机检测等）
        
        Args:
            page: 页面对象
        """
        try:
            # 等待一段时间，看看是否有安全验证弹窗
            time.sleep(3)
            
            # 检查是否有验证弹窗（常见的验证弹窗特征）
            # 1. 检查是否有包含"验证"文字的弹窗
            verification_modal = page.locator('.arco-modal-content:has-text("验证"), .verify-modal, [class*="verify"]').first
            if verification_modal.count() > 0 and verification_modal.is_visible():
                logger.info("⚠️ 检测到安全验证弹窗，请手动完成验证...")
                # 等待用户完成验证（较长时间）
                time.sleep(15)
            
            # 2. 检查是否有滑块验证
            slider = page.locator('.slider-verify, .captcha-slider, [class*="slider"]').first
            if slider.count() > 0 and slider.is_visible():
                logger.info("⚠️ 检测到滑块验证，请手动完成...")
                time.sleep(15)
            
            # 3. 检查是否有覆盖层遮挡
            overlay = page.locator('div[style*="pointer-events: none"][style*="z-index: 99999"]').first
            if overlay.count() > 0:
                logger.info("⚠️ 检测到安全检测覆盖层，等待自动消失...")
                # 尝试点击覆盖层中央，有时会触发验证
                try:
                    page.mouse.click(page.viewport_size['width'] // 2, page.viewport_size['height'] // 2)
                    time.sleep(3)
                except:
                    pass
            
            # 4. 尝试关闭可能的弹窗
            close_buttons = page.locator('.arco-modal-close-btn, .arco-icon-close, button:has-text("关闭"), button:has-text("取消")').all()
            for btn in close_buttons:
                try:
                    if btn.is_visible():
                        btn.click()
                        time.sleep(0.5)
                except:
                    pass
                    
        except Exception as e:
            logger.debug(f"处理安全验证时出错: {e}")

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



# 测试函数
def test_create_book():
    """
    测试创建新书功能
    """
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    
    from playwright.sync_api import sync_playwright
    
    print("="*60)
    print("番茄小说自动创建测试")
    print("="*60)
    
    # 测试配置
    test_data = {
        "novel_title": "测试小说123",
        "formatted_synopsis": "这是一个测试小说的简介，用于测试番茄小说的自动创建功能。简介需要50字以上才能通过验证，所以我们需要写多一点内容来确保能够通过番茄平台的验证。",
        "main_character": "测试主角",
        "tags_info": {
            "main_category": "玄幻",
            "themes": ["东方玄幻", "异世大陆"],
            "roles": ["孤儿", "老师"],
            "plots": ["废柴流", "奇遇"]
        }
    }
    
    with sync_playwright() as p:
        # 连接到已启动的 Chrome
        print("\n连接到 Chrome (端口 9988)...")
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9988")
        except Exception as e:
            print(f"连接失败: {e}")
            print("请确保 Chrome 已启动 (运行 start_chrome.bat)")
            return False
        
        # 获取页面
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()
        
        print(f"已连接到页面: {page.title()}")
        
        # 创建发布器
        publisher = NovelPublisher()
        
        # 测试创建新书
        print("\n开始测试创建新书...")
        print("-"*60)
        
        # 创建临时项目目录
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建一个简单的封面文件用于测试
        try:
            from PIL import Image
            img = Image.new('RGB', (600, 800), color='red')
            img.save(temp_dir / 'cover.png')
            print(f"已创建测试封面: {temp_dir / 'cover.png'}")
        except ImportError:
            print("PIL 未安装，跳过创建测试封面")
        
        # 执行创建
        result = publisher._create_new_book(
            page=page,
            novel_title=test_data["novel_title"],
            formatted_synopsis=test_data["formatted_synopsis"],
            main_character=test_data["main_character"],
            novel_data={"selected_plan": {"tags": test_data["tags_info"]}},
            project_dir=temp_dir
        )
        
        print("-"*60)
        if result:
            print("✓ 测试成功！书籍创建完成")
        else:
            print("✗ 测试失败！请检查日志")
        
        # 清理
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
        browser.close()
        return result


if __name__ == "__main__":
    test_create_book()


class NovelPublisherV2(NovelPublisher):
    """增强版小说发布器，支持更多功能"""
    
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
                                   publish_times: List[str], chapters_per_slot: int, book_id: Optional[str] = None) -> bool:
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
                target_date_str, target_time_str, book_id
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
