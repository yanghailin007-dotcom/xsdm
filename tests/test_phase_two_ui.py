#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二阶段章节生成UI测试
检测队列重复和动画效果问题
"""
import sys
import os
import io

# 设置 stdout 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright
import time


def test_phase_two_generation_ui():
    """测试二阶段章节生成UI"""
    
    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=False, slow_mo=100)
        context = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = context.new_page()
        
        try:
            # 访问二阶段生成页面
            print("🌐 访问二阶段章节生成页面...")
            page.goto('http://localhost:5000/phase-two-generation')
            page.wait_for_load_state('networkidle')
            time.sleep(2)
            
            # 截图：页面初始状态
            page.screenshot(path='screenshots/phase2_initial.png')
            print("✅ 已截图：初始状态")
            
            # 检查页面标题
            title = page.title()
            print(f"📄 页面标题: {title}")
            
            # 如果需要登录
            if '登录' in title:
                print("🔑 需要登录，执行登录...")
                page.fill('#username', 'yanghailin')
                page.fill('#password', 'yanghailin')
                page.click('button[type="submit"]')
                time.sleep(3)
                page.goto('http://localhost:5000/phase-two-generation')
                page.wait_for_load_state('networkidle')
                time.sleep(2)
                title = page.title()
                print(f"📄 登录后页面标题: {title}")
            
            # 截图：页面加载完成
            page.screenshot(path='screenshots/phase2_page_loaded.png')
            print("✅ 已截图：页面加载完成")
            
            # 等待项目列表加载
            print("⏳ 等待项目列表加载...")
            page.wait_for_selector('#projects-list', timeout=10000)
            time.sleep(2)
            
            # 截图：项目列表
            page.screenshot(path='screenshots/phase2_projects.png')
            print("✅ 已截图：项目列表")
            
            # 检查是否有项目卡片
            project_cards = page.locator('.project-select-card').all()
            print(f"📊 找到 {len(project_cards)} 个项目")
            
            if len(project_cards) == 0:
                print("⚠️ 没有可用项目，测试结束")
                return
            
            # 点击第一个项目
            print("🖱️ 选择第一个项目...")
            project_cards[0].click()
            time.sleep(2)
            
            # 截图：选择项目后
            page.screenshot(path='screenshots/phase2_project_selected.png')
            print("✅ 已截图：项目已选择")
            
            # 切换到"章节生成"标签
            generate_tab = page.locator('[data-tab="generate"]').first
            if generate_tab.is_visible():
                print("🖱️ 切换到章节生成标签...")
                generate_tab.click()
                time.sleep(1)
                
                page.screenshot(path='screenshots/phase2_generate_tab.png')
                print("✅ 已截图：章节生成标签")
            
            # 检查表单元素
            from_chapter = page.locator('#from-chapter').first
            chapters_to_generate = page.locator('#chapters-to-generate').first
            
            if from_chapter.is_visible() and chapters_to_generate.is_visible():
                print("✅ 表单元素存在")
                
                # 设置生成参数（只生成3章用于测试）
                from_chapter.fill('1')
                chapters_to_generate.fill('3')
                time.sleep(0.5)
                
                page.screenshot(path='screenshots/phase2_form_filled.png')
                print("✅ 已截图：表单已填写")
                
                # 点击开始生成按钮
                start_btn = page.locator('#start-btn').first
                if start_btn.is_visible():
                    print("🚀 点击开始生成按钮...")
                    start_btn.click()
                    time.sleep(3)
                    
                    # 截图：开始生成后
                    page.screenshot(path='screenshots/phase2_generation_started.png')
                    print("✅ 已截图：生成已开始")
                    
                    # 检查章节队列
                    print("🔍 检查章节队列...")
                    check_chapter_queue(page)
                    
                    # 检查动画效果
                    print("🎨 检查动画效果...")
                    check_animation_effects(page)
                    
                    # 等待一段时间观察进度
                    print("⏳ 观察生成进度（15秒）...")
                    for i in range(5):
                        time.sleep(3)
                        page.screenshot(path=f'screenshots/phase2_progress_{i+1}.png')
                        print(f"✅ 已截图：进度 {i+1}/5")
                        
                        # 持续检查队列
                        has_duplicates = not check_chapter_queue_for_duplicates(page)
                        if has_duplicates:
                            print(f"  ❌ 第 {i+1} 次检查发现问题：队列有重复！")
                        else:
                            print(f"  ✅ 第 {i+1} 次检查通过：无重复")
                    
                    # 停止生成
                    stop_btn = page.locator('button:has-text("停止")').first
                    if stop_btn.is_visible():
                        print("🛑 点击停止按钮...")
                        stop_btn.click()
                        time.sleep(2)
                        page.screenshot(path='screenshots/phase2_stopped.png')
                        print("✅ 已截图：已停止")
            
            print("\n" + "="*60)
            print("✅ UI测试完成")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            page.screenshot(path='screenshots/phase2_error.png')
            import traceback
            traceback.print_exc()
            
        finally:
            browser.close()


def check_chapter_queue(page):
    """检查章节队列显示"""
    queue_container = page.locator('#chapterQueueContainer').first
    if queue_container.is_visible():
        print("  ✅ 章节队列容器已显示")
        
        # 检查队列项目
        queue_items = page.locator('.chapter-queue__item').all()
        print(f"  📊 队列中有 {len(queue_items)} 个章节项目")
        
        # 检查章节编号是否有重复
        chapter_numbers = []
        for item in queue_items:
            number_el = item.locator('.chapter-queue__number').first
            if number_el.is_visible():
                number = number_el.text_content()
                chapter_numbers.append(number)
        
        print(f"  📊 章节编号列表: {chapter_numbers}")
        
        # 检查重复
        duplicates = [n for n in chapter_numbers if chapter_numbers.count(n) > 1]
        if duplicates:
            print(f"  ❌ 发现重复章节编号: {set(duplicates)}")
        else:
            print("  ✅ 没有重复的章节编号")
            
        # 检查连接线
        connectors = page.locator('.chapter-queue__connector').all()
        print(f"  📊 队列中有 {len(connectors)} 个连接线")
        
        # 检查统计数字
        pending_count = page.locator('#queue-pending-count').first.text_content()
        generating_count = page.locator('#queue-generating-count').first.text_content()
        completed_count = page.locator('#queue-completed-count').first.text_content()
        print(f"  📊 队列统计 - 等待: {pending_count}, 生成中: {generating_count}, 完成: {completed_count}")
    else:
        print("  ⚠️ 章节队列容器未显示")


def check_chapter_queue_for_duplicates(page):
    """持续检查队列是否有重复"""
    queue_items = page.locator('.chapter-queue__item').all()
    chapter_numbers = []
    
    for item in queue_items:
        number_el = item.locator('.chapter-queue__number').first
        if number_el.is_visible():
            number = number_el.text_content()
            chapter_numbers.append(number)
    
    # 检查重复
    seen = set()
    duplicates = []
    for n in chapter_numbers:
        if n in seen:
            duplicates.append(n)
        seen.add(n)
    
    if duplicates:
        print(f"  ❌ 发现重复章节编号: {duplicates}")
        return False
    return True


def check_animation_effects(page):
    """检查动画效果"""
    # 检查队列项目动画
    generating_items = page.locator('.chapter-queue__item--generating').all()
    print(f"  📊 生成中章节数: {len(generating_items)}")
    
    # 检查连接线流动效果
    flowing_connectors = page.locator('.chapter-queue__connector--flowing').all()
    print(f"  📊 流动效果连接线数: {len(flowing_connectors)}")
    
    # 检查网格章节卡片
    chapter_cards = page.locator('.v2-chapter-mini').all()
    print(f"  📊 章节卡片数: {len(chapter_cards)}")
    
    # 检查各种状态的卡片
    pending_cards = page.locator('.v2-chapter-mini--pending').all()
    generating_cards = page.locator('.v2-chapter-mini--generating').all()
    queued_cards = page.locator('.v2-chapter-mini--queued').all()
    completed_cards = page.locator('.v2-chapter-mini--completed').all()
    
    print(f"    - 等待: {len(pending_cards)}")
    print(f"    - 排队: {len(queued_cards)}")
    print(f"    - 生成中: {len(generating_cards)}")
    print(f"    - 完成: {len(completed_cards)}")
    
    # 检查是否有异常状态
    if len(generating_cards) > 1:
        print("  ⚠️ 有多个章节同时显示为'生成中'状态，可能动画不同步")


if __name__ == '__main__':
    # 创建截图目录
    os.makedirs('screenshots', exist_ok=True)
    
    # 运行测试
    print("="*60)
    print("🚀 第二阶段章节生成UI测试")
    print("="*60)
    
    test_phase_two_generation_ui()
