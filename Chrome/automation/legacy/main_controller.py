"""
番茄小说自动发布系统 - 主控制模块
整合所有功能模块，提供主要的控制逻辑
"""

import os
import time
from datetime import datetime
from typing import List, Dict, Any

from .config import CONFIG
from .utils import ensure_directory_exists, list_json_files, format_synopsis_for_fanqie
from .file_manager import find_chapter_files, load_chapter_data, extract_novel_info_from_json
from .progress_manager import load_publish_progress2, save_publish_progress2
from .browser_manager import connect_to_browser, navigate_to_writer_platform, manage_browser_pages, ensure_fanqie_page, close_browser_connection
from .novel_manager import create_new_book, navigate_to_correct_book, find_existing_book_in_list
from .chapter_publisher import process_scheduled_publishing, process_immediate_publishing


def publish_novel(page2, json_file):
    """发布单个小说"""
    print(f"\n处理小说项目: {os.path.basename(json_file)}")

    # 提取小说信息
    novel_info = extract_novel_info_from_json(json_file)
    if not novel_info:
        return False
    
    novel_title = novel_info['novel_title']
    novel_synopsis = novel_info['novel_synopsis']
    main_character = novel_info['main_character']
    full_data = novel_info['full_data']

    print(f"小说名称: {novel_title}")
    print(f"主角: {main_character}")

    # 优化简介排版
    formatted_synopsis = format_synopsis_for_fanqie(novel_synopsis, full_data)
    print("优化后的简介:")
    print(f"  字数: {len(formatted_synopsis)} 字符")
    print(f"  预览: {formatted_synopsis[:100]}..." if len(formatted_synopsis) > 100 else f"  内容: {formatted_synopsis}")
    print("-" * 50)

    # 加载发布进度
    progress = load_publish_progress2(novel_title)

    # 确保 published_chapters 是一个列表，且每个元素是一个字典
    published_chapters = progress.get("published_chapters", [])
    total_content_len = progress.get("total_content_len", 0)
    base_chapter_num = progress.get("base_chapter_num", 0)
    book_created = progress.get("book_created", False)

    # 修复逻辑：先检查网页上书籍是否存在，再决定是否创建新书
    print("检查书籍是否已在番茄小说网存在...")
    
    # 首先尝试在网上查找现有书籍
    existing_book_found = find_existing_book_in_list(page2, novel_title)
    
    if existing_book_found:
        print(f"[OK] 找到已存在的书籍《{novel_title}》，直接使用")
        
        # 更新进度文件，标记书籍已创建
        if not book_created:
            book_created = True
            progress["book_created"] = book_created
            progress["total_content_len"] = total_content_len
            progress["base_chapter_num"] = base_chapter_num
            
            # 保存基本进度
            from .progress_manager import save_publish_progress
            save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num, book_created)
            print(f"[OK] 已更新本地进度，标记书籍《{novel_title}》为已创建状态")
    else:
        print(f"[INFO] 网页上未找到书籍《{novel_title}》")
        
        if book_created:
            print("[WARNING] 本地进度显示书籍已创建，但网页上未找到，可能书籍已被删除")
        
        print(f"[INFO] 开始创建新书《{novel_title}》...")
        if create_new_book(page2, novel_title, formatted_synopsis, main_character, full_data):
            # 标记书籍已创建
            book_created = True
            progress["book_created"] = book_created
            progress["total_content_len"] = total_content_len
            progress["base_chapter_num"] = base_chapter_num
            
            # 保存基本进度
            from .progress_manager import save_publish_progress
            save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num, book_created)
            
            print(f"[OK] 书籍《{novel_title}》创建成功")

            # 导航到新创建的书籍
            if not navigate_to_correct_book(page2, novel_title):
                print(f"[ERROR] 无法导航到新创建的书籍《{novel_title}》")
                return False
        else:
            print(f"[ERROR] 书籍《{novel_title}》创建失败")
            return False

    # 等待页面完全加载
    print("等待书籍详情页完全加载...")
    try:
        page2.wait_for_load_state("networkidle")
        time.sleep(2)
    except Exception as e:
        print(f"等待页面加载时出错: {e}")

    # 查找章节文件
    chapter_files_sorted = find_chapter_files(novel_title)
    if not chapter_files_sorted:
        return False

    # 构建章节发布信息
    chapter_publish_info = []
    for chap_index, chapter_file in enumerate(chapter_files_sorted):
        # 检查章节是否已经发布 - 使用文件名基础部分匹配，忽略扩展名和路径差异
        is_published = False
        matched_pub_chap = None
        chapter_basename = os.path.basename(chapter_file)
        chapter_name_without_ext = os.path.splitext(chapter_basename)[0]  # 去掉扩展名
        
        for pub_chap in published_chapters:
            pub_file = pub_chap.get('file', '')
            pub_basename = os.path.basename(pub_file)
            pub_name_without_ext = os.path.splitext(pub_basename)[0]  # 去掉扩展名
            
            # 比较文件名的基础部分（去掉扩展名）
            if chapter_name_without_ext == pub_name_without_ext:
                is_published = True
                matched_pub_chap = pub_chap
                break
        
        if is_published and matched_pub_chap:
            chapter_publish_info.append({
                'file': chapter_file,
                'chap_num': str(matched_pub_chap.get('chap_num', '0')),
                'chap_title': matched_pub_chap.get('chap_title', ''),
                'chap_content': '',  # 已发布的章节暂时不加载内容，需要时再加载
                'chap_len': matched_pub_chap.get('chap_len', 0),
                'index': chap_index,
                'published': True,
                'target_date': matched_pub_chap.get('target_date', ''),
                'target_time': matched_pub_chap.get('target_time', ''),
                'time_slot_index': matched_pub_chap.get('time_slot_index', 0)
            })
            continue

        # 加载章节数据（不包含内容，避免读取大文件）
        chapter_data = load_chapter_data(chapter_file, load_content=False)
        if chapter_data:
            chapter_publish_info.append({
                'file': chapter_file,
                'chap_num': chapter_data['chap_num'],
                'chap_title': chapter_data['chap_title'],
                'chap_content': '',  # 初始不加载内容，需要时再加载
                'chap_len': chapter_data['chap_len'],
                'index': chap_index,
                'published': False,
                'target_date': '',
                'target_time': '',
                'time_slot_index': 0
            })

    published_count = len(published_chapters)
    print(f"检测到已发布 {published_count} 章，将从第 {published_count + 1} 章继续...")

    if base_chapter_num > 0:
        print(f"基准章节号: 第 {base_chapter_num} 章 (从这一章开始定时发布)")

    # 根据累计字数决定发布策略
    from .config import WORD_COUNT_THRESHOLD
    if total_content_len >= WORD_COUNT_THRESHOLD:
        print(f"累计字数已达 {total_content_len}，超过阈值 {WORD_COUNT_THRESHOLD}，开始定时发布")
        return process_scheduled_publishing(
            page2, novel_title, chapter_publish_info, published_chapters,
            total_content_len, base_chapter_num, json_file
        )
    else:
        print(f"累计字数 {total_content_len} 小于阈值 {WORD_COUNT_THRESHOLD}，进行立即发布")
        return process_immediate_publishing(
            page2, novel_title, chapter_publish_info, published_chapters,
            total_content_len, base_chapter_num, book_created, json_file
        )


def main_scan_cycle():
    """主扫描循环 - 修改：在发布小说前先检查签约管理"""
    print("=== 番茄小说自动发布程序 - 扫描模式 ===")
    print(f"扫描间隔: {CONFIG['scan_interval']} 秒")

    # 确保小说项目目录存在
    ensure_directory_exists(CONFIG["novel_path"])
    print(f"小说项目目录: {os.path.abspath(CONFIG['novel_path'])}")

    # 连接浏览器
    playwright, browser, page1, default_context = connect_to_browser()
    if not browser or not page1 or not default_context:
        print("❌ 浏览器连接失败，等待下次扫描")
        print("💡 请确保:")
        print("   1. Chrome浏览器已安装")
        print("   2. 运行: python fanqie_browser_launcher.py")
        print("   3. 检查防火墙设置")
        return False

    print("✅ 浏览器连接成功，开始页面管理...")
    
    # 管理浏览器页面
    main_page = manage_browser_pages(default_context)
    if main_page:
        page1 = main_page

    # 确保在番茄小说页面
    if not ensure_fanqie_page(page1):
        print("❌ 无法导航到番茄小说页面")
        close_browser_connection(playwright, browser, page1)
        return False

    # 导航到作家专区
    print("🎯 开始导航到作家专区...")
    page2 = navigate_to_writer_platform(page1, default_context)
    if not page2:
        print("❌ 导航到作家专区失败")
        close_browser_connection(playwright, browser, page1)
        return False

    # 检查小说项目
    print("=" * 50)
    print("📚 小说项目检查")
    print("=" * 50)
    
    json_files = list_json_files(CONFIG["novel_path"])
    if not json_files:
        print(f"❌ 在目录 '{CONFIG['novel_path']}' 中未找到小说项目文件")
        print(f"💡 请确保您的JSON文件命名以 '{CONFIG['required_json_suffix']}' 结尾")
        print("📁 示例文件名: '我的小说_项目信息.json'")
        close_browser_connection(playwright, browser, page2)
        return False
    else:
        print(f"✅ 找到 {len(json_files)} 个小说项目:")
        for file_index, json_file in enumerate(json_files):
            file_name = os.path.basename(json_file)
            print(f"   {file_index + 1}. {file_name}")

    # 环境就绪确认
    print("=" * 50)
    print("🎯 环境就绪确认")
    print("=" * 50)
    print("✅ 浏览器连接: 成功")
    print("✅ 番茄小说页面: 已进入")
    print("✅ 登录状态: 用户确认")
    print(f"✅ 作家专区: 已进入")
    print(f"✅ 小说项目: {len(json_files)} 个")
    print()
    
    # 自动执行发布流程，无需用户选择
    print("🚀 自动开始执行发布流程...")
    
    # 初始化 success_count 变量，确保在任何情况下都有定义
    success_count = 0
    
    # 处理每个小说项目
    for file_index, json_file in enumerate(json_files):
        print(f"\n{'=' * 50}")
        print(f"📖 处理第 {file_index + 1} 个小说项目")

        try:
            if publish_novel(page2, json_file):
                success_count += 1
                print(f"✅ 小说项目 {file_index + 1} 处理成功")
            else:
                print(f"❌ 小说项目 {file_index + 1} 处理失败")
        except Exception as e:
            print(f"❌ 处理小说项目时出错: {e}")
            continue

    print(f"\n{'=' * 50}")
    print(f"📊 发布完成！成功处理 {success_count}/{len(json_files)} 个小说项目")

    # 签约管理功能已禁用
    print("=" * 50)
    print("📋 签约管理检查 [已禁用]")
    print("=" * 50)
    print("ℹ️ 签约管理功能已被禁用，跳过签约检查流程")

    # 清理和退出
    close_browser_connection(playwright, browser, page2)

    return success_count > 0 if json_files else True


def main():
    """主函数 - 定时扫描模式"""
    print("=== 番茄小说自动发布程序 - 定时扫描模式 ===")
    print("程序将每小时自动扫描一次新书并发布")
    print("按 Ctrl+C 退出程序")

    scan_count = 0

    try:
        while True:
            scan_count += 1
            print(f"\n{'=' * 60}")
            print(f"开始第 {scan_count} 次扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print('=' * 60)

            try:
                main_scan_cycle()
            except Exception as e:
                print(f"扫描过程中发生错误: {e}")

            # 等待下一次扫描
            print(f"\n[{datetime.now()}]#等待下一次扫描... ({CONFIG['scan_interval']} 秒后)")
            time.sleep(CONFIG["scan_interval"])

    except KeyboardInterrupt:
        print("\n\n程序被用户中断，退出...")
    except Exception as e:
        print(f"\n程序发生未知错误: {e}")


if __name__ == "__main__":
    main()