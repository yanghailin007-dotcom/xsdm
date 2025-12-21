"""
番茄小说自动发布系统 - 章节发布模块
处理章节的发布和定时发布逻辑
"""

import os
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from .config import CONFIG, WORD_COUNT_THRESHOLD, novel_publish_times, CHAPTERS_PER_TIME_SLOT, PUBLISH_BUFFER_MINUTES
from .utils import safe_click, safe_fill, normalize_all_line_breaks, wait_for_enter
from .novel_manager import click_create_chapter_button_by_novel_title


def publish_chapter_with_retry(target_page, chap_number, chap_title, chap_content, target_date, target_time,
                               expected_book_title, max_retries=9):
    """
    带有重试机制的章节发布函数
    """
    retry_count = 0

    while retry_count < max_retries:
        result = verify_and_create_chapter(target_page, expected_book_title, chap_number, chap_title, chap_content,
                                           target_date, target_time)

        if result == 0:  # 成功
            return 0
        elif result == 2:  # 需要重新导航
            print("需要重新导航到正确书籍...")
            from .novel_manager import navigate_to_correct_book
            if not navigate_to_correct_book(target_page, expected_book_title):
                print("重新导航失败")
                return 1
            retry_count += 1
            print(f"重新导航后重试发布 (第{retry_count}次重试)")
        else:  # 其他错误
            retry_count += 1
            continue

    print(f"达到最大重试次数({max_retries})，发布失败")
    return 1


def verify_and_create_chapter(target_page, expected_book_title, chap_number, chap_title, chap_content, target_date,
                              target_time):
    """
    验证当前页面并创建章节，如果不匹配则退出并重新开始
    """

    current_page = click_create_chapter_button_by_novel_title(target_page, expected_book_title)

    try:
        # 等待页面加载
        current_page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 在创建章节页面中验证书名
        header_book_name = current_page.locator('.publish-header-book-name')
        if header_book_name.count() > 0:
            actual_title = header_book_name.first.text_content().strip()
            if expected_book_title not in actual_title:
                print(f"✗ 创建章节页面书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                current_page.close()
                return 2  # 返回2表示需要重新导航

        # 填写章节信息
        input_elements = current_page.locator('input.serial-input.byte-input.byte-input-size-default')
        if input_elements.count() < 2:
            print("未找到章节输入框")
            current_page.close()
            return 1

        # 填写章节序号和标题
        if not safe_fill(input_elements.nth(0), chap_number, "章节序号"):
            current_page.close()
            return 1
        if not safe_fill(input_elements.nth(1), chap_title, "章节标题"):
            current_page.close()
            return 1

        # 处理并填写内容
        content_cleaned = re.sub(r'^【.*?】\s*?\n', '', chap_content, flags=re.MULTILINE)
        
        # 确保内容不为空
        if not content_cleaned.strip():
            print("❌ 章节内容为空，发布失败")
            current_page.close()
            return 1
        
        processed_text = normalize_all_line_breaks(content_cleaned)
        
        # 验证处理后的内容
        if not processed_text.strip():
            print("❌ 处理后章节内容为空，发布失败")
            current_page.close()
            return 1

        content_input = current_page.locator('div[class*="ProseMirror"][contenteditable]').first
        if not safe_fill(content_input, processed_text, "章节内容"):
            current_page.close()
            return 1
        
        print(f"✓ 成功填充章节内容 (长度: {len(processed_text)} 字符)")

        # 点击下一步
        if not safe_click(current_page.get_by_role("button", name="下一步"), "下一步按钮", retries=2):
            current_page.close()
            return 1

        time.sleep(0.5)

        # 处理可能的弹窗
        retry_times = 5
        while retry_times >= 0:
            time.sleep(0.3)
            retry_times = retry_times - 1
            for button_name in ["提交", "继续编辑本地", "确定", "确认"]:
                try:
                    button = current_page.get_by_role("button", name=button_name, exact=False)
                    button_text = button.text_content(timeout=100)
                    if "发布" not in button_text:
                        button.click(timeout=100)

                    time.sleep(0.3)
                except:
                    pass

        # 选择AI选项
        try:
            current_page.locator(".arco-radio-text >> text=是").click(timeout=5000)
            time.sleep(0.3)
        except:
            pass

        # 设置定时发布
        if target_date or target_time:
            if not setup_scheduled_publish(current_page, target_date, target_time):
                print(f"✗ 无法设置定时发布 {target_date} {target_time}，发布失败，继续下一章")
                current_page.close()
                return 1

        # 处理可能的弹窗
        retry_times = 3
        while retry_times >= 0:
            time.sleep(0.5)
            retry_times = retry_times - 1
            for button_name in ["提交", "提交"]:
                try:
                    button = current_page.get_by_role("button", name=button_name, exact=False)
                    button_text = button.text_content(timeout=100)
                    if "发布" not in button_text:
                        button.click(timeout=100)

                    time.sleep(0.5)
                except:
                    pass

        # 确认发布
        if safe_click(current_page.get_by_role("button", name="确认发布"), "确认发布按钮", retries=2):
            time.sleep(1)
            # 处理可能的弹窗
            retry_times = 3
            while retry_times >= 0:
                time.sleep(0.5)
                retry_times = retry_times - 1
                for button_name in ["确定", "确认"]:
                    try:
                        button = current_page.get_by_role("button", name=button_name, exact=False)
                        button_text = button.text_content(timeout=100)
                        if "发布" not in button_text:
                            button.click(timeout=100)

                        time.sleep(0.5)
                    except:
                        pass

            # 发布完后，会自动进入章节列表，且最新的排在前面。所以只要检查上面发布的章节标题，是否在其中即可确认发布成功没有。
            divs = current_page.locator('div[class*="table-title"][class*="table-title-narrow"]')
            # 获取所有匹配的元素
            all_div_elements = divs.all()

            # 遍历并使用 enumerate 打印索引和文本内容
            for index, element in enumerate(all_div_elements):
                element_inner_text = element.inner_text()
                chap_no = f"""第{chap_number}章"""
                if chap_title in element_inner_text and chap_no in element_inner_text:
                    print(f"✓ 本章节 [{chap_no} {chap_title}] 发布成功,已确认! ")
                    current_page.close()
                    return 0

            current_page.close()
            return 1

    except Exception as e:
        print(f"发布章节时发生错误: {e}")
        try:
            current_page.close()
        except:
            pass
        current_page.close()
        return 1

    current_page.close()
    return 1


def setup_scheduled_publish(current_page, target_date, target_time):
    """设置定时发布"""
    try:
        switch_button = current_page.get_by_role("switch")
        current_state = switch_button.get_attribute("aria-checked")
        if current_state == "false":
            switch_button.click()  # 点击切换状态
            time.sleep(0.3)

        # 获取所有匹配元素（使用更严格的等待）
        all_pickers = current_page.locator('.arco-picker-start-time').all()
        current_page.wait_for_selector('.arco-picker-start-time', state='attached', timeout=12000)

        if len(all_pickers) < 2:
            raise Exception("未找到第二个时间选择器")
        else:
            # 禁用页面的重置脚本
            current_page.evaluate('''() => {
                const originalBlur = HTMLInputElement.prototype.blur;
                HTMLInputElement.prototype.blur = function() {
                    if (this.type === 'time' && this.value) {
                        this.value = this.value.slice(0, 5);  // 强制保留HH:MM格式
                    }
                    originalBlur.call(this);
                };
            }''')

        if target_date is not None:
            date_picker = all_pickers[0]
            date_picker.evaluate('''(el, date) => {
                // 绕过框架的拦截
                const prototype = HTMLInputElement.prototype;
                const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                nativeSetter.call(el, date);

                // 触发框架监听的所有事件
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur'));
            }''', target_date)

            date_picker.click(timeout=2000)
            time.sleep(1)

            # 先尝试向前翻页最多12次
            timeout_cnt = 0
            date_found = False

            # 向前翻页寻找日期
            while timeout_cnt <= 12:
                try:
                    # 点击设置的日期
                    selected_cell = current_page.locator('''
                        div.arco-picker-body 
                        >> div.arco-picker-row 
                        >> div.arco-picker-cell-selected
                    ''')
                    selected_cell.click(timeout=500)
                    date_found = True
                    break
                except Exception as e:
                    next_selector = "div.arco-picker-header-icon:has(svg.arco-icon-right)"
                    next_div = current_page.locator(next_selector)
                    next_div.click(timeout=5000)
                    timeout_cnt = timeout_cnt + 1
                    time.sleep(1)

            # 如果向前翻页没找到，改为向后翻页
            if not date_found:
                print("向前翻页12次未找到日期，改为向后翻页")
                back_count = 0
                max_back_count = 24  # 最多向后翻24个月（两年）

                while back_count < max_back_count and not date_found:
                    try:
                        # 点击设置的日期
                        selected_cell = current_page.locator('''
                            div.arco-picker-body 
                            >> div.arco-picker-row 
                            >> div.arco-picker-cell-selected
                        ''')
                        selected_cell.click(timeout=500)
                        date_found = True
                        break
                    except Exception as e:
                        prev_selector = "div.arco-picker-header-icon:has(svg.arco-icon-left)"
                        prev_div = current_page.locator(prev_selector)
                        prev_div.click(timeout=5000)
                        back_count += 1
                        time.sleep(1)

            # 如果最终都没找到日期，发布失败，继续下一章
            if not date_found:
                print(f"✗ 无法找到目标日期 {target_date}，发布失败，继续下一章")
                return False

        if target_time is not None:
            time_picker = all_pickers[1]
            time_picker.evaluate('''(el, time) => {
                // 绕过框架的拦截
                const prototype = HTMLInputElement.prototype;
                const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                nativeSetter.call(el, time);

                // 触发框架监听的所有事件
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur'));
            }''', target_time)

            time_picker.click(timeout=2000)
            time.sleep(1)
            # 点击确定
            current_page.get_by_role("button", name="确定").click(timeout=12000)
            time.sleep(1)

        return True

    except Exception as e:
        print(f"设置定时发布失败: {e}")
        return False


def process_scheduled_publishing(page2, novel_title, chapter_publish_info, published_chapters, 
                               total_content_len, base_chapter_num, json_file):
    """
    处理定时发布逻辑
    """
    # 获取当前日期和时间，仅一次，在进入定时发布逻辑之前
    now = datetime.now()  # 仅获取一次，后续不再修改
    current_date = now.date()
    current_time = now.time()

    # 检查是否需要恢复定时发布状态
    if published_chapters and total_content_len >= WORD_COUNT_THRESHOLD:
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
                    # 解析最后发布日期和时间
                    last_datetime = datetime.strptime(f"{last_date_str} {last_time_str}", "%Y-%m-%d %H:%M")
                    last_date = last_datetime.date()

                    # 根据 time_slot_index 决定下一步操作
                    if last_slot_index < CHAPTERS_PER_TIME_SLOT:
                        # 当前时间点还有空位，继续使用相同的日期和时间
                        current_date = last_date
                        current_time = datetime.strptime(last_time_str, "%H:%M").time()
                        print(
                            f"✓ 恢复状态: 继续使用 {current_date} {current_time.strftime('%H:%M')} 的第 {last_slot_index + 1} 个位置")
                    else:
                        # 当前时间点已满，需要移动到下一个时间点
                        time_index = novel_publish_times.index(last_time_str)
                        if time_index + 1 < len(novel_publish_times):
                            # 同一天的下一个时间点
                            next_time_str = novel_publish_times[time_index + 1]
                            current_date = last_date
                            current_time = datetime.strptime(next_time_str, "%H:%M").time()
                            print(
                                f"✓ 恢复状态: 时间点已满，移动到同一天的下一个时间点 {current_date} {current_time.strftime('%H:%M')}")
                        else:
                            # 需要到下一天的第一个时间点
                            current_date = last_date + timedelta(days=1)
                            current_time = datetime.strptime(novel_publish_times[0], "%H:%M").time()
                            print(
                                f"✓ 恢复状态: 当天时间点已满，移动到下一天 {current_date} {current_time.strftime('%H:%M')}")

                    # 验证恢复的时间是否有效（不能早于当前时间）
                    restored_datetime = datetime.combine(current_date, current_time)
                    if restored_datetime <= now:
                        print(f"⚠️  恢复的时间 {current_date} {current_time.strftime('%H:%M')} 已过期，使用当前时间")
                        current_date = now.date()
                        current_time = now.time()

                except Exception as e:
                    print(f"恢复定时发布状态时出错: {e}, 将使用当前时间")
                    current_date = now.date()
                    current_time = now.time()

    # 主发布循环
    current_chapter_index = 0
    total_chapters = len(chapter_publish_info)

    # 初始化时间点使用情况跟踪
    date_time_slot_usage = {}  # 格式: {date: {time: count}}

    # 首先，从已发布的章节中恢复时间点使用情况
    for chap in published_chapters:
        if chap.get('target_date') and chap.get('target_time'):
            date = chap['target_date']
            time_slot = chap['target_time']
            if date not in date_time_slot_usage:
                date_time_slot_usage[date] = {}
            if time_slot not in date_time_slot_usage[date]:
                date_time_slot_usage[date][time_slot] = 0
            date_time_slot_usage[date][time_slot] += 1

    while current_chapter_index < total_chapters:
        current_chapter = chapter_publish_info[current_chapter_index]
        if current_chapter['published']:
            current_chapter_index += 1
            continue

        # 检查累计字数是否仍然超过阈值
        if total_content_len < WORD_COUNT_THRESHOLD:
            print(f"当前累计字数 {total_content_len} 小于 {WORD_COUNT_THRESHOLD}，退出定时发布逻辑")
            break

        # 查找可用的时间点
        found_available_slot = False
        temp_date = current_date
        temp_time = current_time

        # 在多个日期中查找可用时间点
        for day_offset in range(30):  # 最多查找30天
            search_date = current_date + timedelta(days=day_offset)
            date_str = search_date.strftime('%Y-%m-%d')

            # 初始化该日期的时间点使用情况
            if date_str not in date_time_slot_usage:
                date_time_slot_usage[date_str] = {}

            # 检查该日期的每个时间点
            for time_slot in novel_publish_times:
                # 获取该时间点的当前使用计数
                current_count = date_time_slot_usage[date_str].get(time_slot, 0)

                # 检查是否还有空位
                if current_count < CHAPTERS_PER_TIME_SLOT:
                    # 验证时间是否有效
                    slot_datetime = datetime.strptime(f"{date_str} {time_slot}", "%Y-%m-%d %H:%M")
                    if slot_datetime > now + timedelta(minutes=PUBLISH_BUFFER_MINUTES):
                        # 找到可用时间点
                        current_date = search_date
                        current_time = datetime.strptime(time_slot, "%H:%M").time()
                        found_available_slot = True
                        break

            if found_available_slot:
                break

        if not found_available_slot:
            print("✗ 在30天内未找到可用的发布时间点")
            break

        # 发布当前章节到找到的时间点
        chap_file = current_chapter['file']
        chap_num = current_chapter['chap_num']
        chap_title = current_chapter['chap_title']
        chap_content = current_chapter['chap_content']
        chap_len = current_chapter['chap_len']

        from .browser_manager import check_and_recover_page
        if not check_and_recover_page(page2):
            print("页面已失效，无法继续发布")
            return False

        target_date = current_date.strftime('%Y-%m-%d')
        target_time = current_time.strftime('%H:%M')

        # 获取当前时间点的使用计数
        current_count = date_time_slot_usage.get(target_date, {}).get(target_time, 0)
        time_slot_index = current_count + 1

        print(f"\n发布第 {chap_num} 章: {chap_title} (字数: {chap_len})")
        print(f"定时发布: {target_date} {target_time} (第 {time_slot_index} 个位置)")

        # 发布章节
        result = publish_chapter_with_retry(page2, chap_num, chap_title, chap_content,
                                            target_date, target_time, novel_title)
        if result == 0:
            total_content_len += chap_len
            # 更新进度
            current_chapter.update({
                'published': True,
                'target_date': target_date,
                'target_time': target_time,
                'time_slot_index': time_slot_index
            })
            published_chapters.append(current_chapter.copy())
            
            from .progress_manager import save_publish_progress2
            save_publish_progress2(novel_title, published_chapters, total_content_len, base_chapter_num,
                                   True)  # book_created = True
            print(f"✓ 发布成功 (累计字数: {total_content_len})")

            # 更新时间点使用计数
            if target_date not in date_time_slot_usage:
                date_time_slot_usage[target_date] = {}
            date_time_slot_usage[target_date][target_time] = time_slot_index

            # 检查是否已完成所有章节发布
            current_published_count = len(published_chapters)
            from .progress_manager import is_novel_completed
            if is_novel_completed(novel_title, json_file):
                print(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                from .utils import move_completed_novel_to_published
                if move_completed_novel_to_published(novel_title, json_file):
                    return True
        else:
            print("✗ 发布失败")
            wait_for_enter("发布失败，按回车继续下一章...", timeout=10)

        current_chapter_index += 1

    return True


def process_immediate_publishing(page2, novel_title, chapter_publish_info, published_chapters,
                                total_content_len, base_chapter_num, book_created, json_file):
    """
    处理立即发布逻辑（未达到字数阈值时）
    """
    current_chapter_index = 0
    total_chapters = len(chapter_publish_info)

    while current_chapter_index < total_chapters:
        current_chapter = chapter_publish_info[current_chapter_index]

        # 跳过已发布的章节
        if current_chapter['published']:
            print(f"跳过已发布章节: {os.path.basename(current_chapter['file'])}")
            current_chapter_index += 1
            continue

        # 检查累计字数是否达到阈值
        if total_content_len < WORD_COUNT_THRESHOLD:
            print(
                f"当前累计字数 {total_content_len} 小于 {WORD_COUNT_THRESHOLD}，跳过章节 {current_chapter['chap_num']} 的定时发布设置")
            
            from .browser_manager import check_and_recover_page
            if not check_and_recover_page(page2):
                print("页面已失效，无法继续发布")
                break

            print(
                f"\n发布第 {current_chapter['chap_num']} 章: {current_chapter['chap_title']} (字数: {current_chapter['chap_len']}) - 不设置定时")

            # 发布章节（不设置定时）
            result = publish_chapter_with_retry(page2, current_chapter['chap_num'], current_chapter['chap_title'],
                                                current_chapter['chap_content'], None, None, novel_title)
            if result == 0:
                total_content_len += current_chapter['chap_len']
                print(f"✓ 发布成功 (累计字数: {total_content_len})")

                # 标记为已发布
                current_chapter['published'] = True
                # 保存章节详细信息（无定时信息）
                current_chapter.update({
                    'target_date': '',
                    'target_time': '',
                    'time_slot_index': 0
                })
                published_chapters.append(current_chapter.copy())
                
                # 保存到两个进度文件
                from .progress_manager import save_publish_progress, save_publish_progress2
                save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num,
                                      book_created)
                save_publish_progress2(novel_title, published_chapters, total_content_len, base_chapter_num,
                                       book_created)

                # 检查是否达到定时发布阈值，如果达到则切换到定时发布模式
                if total_content_len >= WORD_COUNT_THRESHOLD:
                    print(f"🎯 累计字数 {total_content_len} 已达到阈值 {WORD_COUNT_THRESHOLD}，后续章节将使用定时发布")
                    # 设置基准章节号（如果还未设置）
                    if base_chapter_num == 0:
                        base_chapter_num = current_chapter['chap_num']
                        print(f"✓ 设置基准章节号为第 {base_chapter_num} 章")
                        # 更新进度
                        save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num,
                                              book_created)
                        save_publish_progress2(novel_title, published_chapters, total_content_len, base_chapter_num,
                                               book_created)
                    
                    # 切换到定时发布模式
                    print("🔄 切换到定时发布模式...")
                    return process_scheduled_publishing(
                        page2, novel_title, chapter_publish_info, published_chapters,
                        total_content_len, base_chapter_num, json_file
                    )

                # 检查是否已完成所有章节发布
                current_published_count = len(published_chapters)
                from .progress_manager import is_novel_completed
                if is_novel_completed(novel_title, json_file):
                    print(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                    from .utils import move_completed_novel_to_published
                    if move_completed_novel_to_published(novel_title, json_file):
                        return True
            else:
                print("✗ 发布失败")
                wait_for_enter("发布失败，按回车继续下一章...", timeout=10)

        current_chapter_index += 1

    return True