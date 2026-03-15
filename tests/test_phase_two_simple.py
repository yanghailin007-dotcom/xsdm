#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版二阶段UI测试
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time


def test_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            # 先登录
            print("🔑 登录...")
            page.goto('http://localhost:5000/login')
            time.sleep(2)
            page.screenshot(path='screenshots/01_login.png')
            
            page.fill('#username', 'yanghailin')
            page.fill('#password', 'yanghailin')
            page.click('button[type="submit"]')
            time.sleep(3)
            page.screenshot(path='screenshots/02_after_login.png')
            
            # 访问二阶段页面
            print("🌐 访问二阶段页面...")
            page.goto('http://localhost:5000/phase-two-generation')
            time.sleep(3)
            page.screenshot(path='screenshots/03_phase2.png')
            
            # 等待项目列表
            print("⏳ 等待项目列表...")
            page.wait_for_selector('.project-select-card', timeout=10000)
            time.sleep(2)
            page.screenshot(path='screenshots/04_projects.png')
            
            # 获取项目数量
            cards = page.locator('.project-select-card').all()
            print(f"📊 找到 {len(cards)} 个项目")
            
            if len(cards) > 0:
                # 点击第一个项目
                print("🖱️ 选择第一个项目...")
                cards[0].click()
                time.sleep(2)
                page.screenshot(path='screenshots/05_selected.png')
                
                # 切换到生成标签
                generate_tab = page.locator('[data-tab="generate"]').first
                if generate_tab.is_visible():
                    print("🖱️ 切换到章节生成...")
                    generate_tab.click()
                    time.sleep(1)
                    page.screenshot(path='screenshots/06_generate_tab.png')
                
                # 填写表单
                print("📝 填写表单...")
                page.fill('#from-chapter', '1')
                page.fill('#chapters-to-generate', '3')
                time.sleep(0.5)
                page.screenshot(path='screenshots/07_form_filled.png')
                
                # 开始生成
                start_btn = page.locator('#start-btn').first
                if start_btn.is_visible():
                    print("🚀 开始生成...")
                    start_btn.click()
                    time.sleep(3)
                    page.screenshot(path='screenshots/08_started.png')
                    
                    # 检查队列
                    print("🔍 检查队列...")
                    check_queue(page)
                    
                    # 观察进度
                    print("⏳ 观察进度...")
                    for i in range(5):
                        time.sleep(3)
                        page.screenshot(path=f'screenshots/09_progress_{i+1}.png')
                        check_queue(page)
            
            print("\n✅ 测试完成!")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            page.screenshot(path='screenshots/error.png')
        finally:
            browser.close()


def check_queue(page):
    """检查队列"""
    items = page.locator('.chapter-queue__item').all()
    if not items:
        print("  ⚠️ 无队列项目")
        return
    
    numbers = []
    for item in items:
        num_el = item.locator('.chapter-queue__number').first
        if num_el.is_visible():
            numbers.append(num_el.text_content())
    
    print(f"  📊 队列: {numbers}")
    
    # 检查重复
    seen = set()
    dups = []
    for n in numbers:
        if n in seen:
            dups.append(n)
        seen.add(n)
    
    if dups:
        print(f"  ❌ 重复: {dups}")
    else:
        print(f"  ✅ 无重复")


if __name__ == '__main__':
    os.makedirs('screenshots', exist_ok=True)
    test_ui()
