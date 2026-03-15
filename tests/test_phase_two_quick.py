#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright
import time


def test_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page(viewport={'width': 1400, 'height': 900})
        
        try:
            # 登录
            print("🔑 登录...")
            page.goto('http://localhost:5000/login')
            time.sleep(2)
            
            page.fill('#username', 'yanghailin')
            page.fill('#password', 'yanghailin')
            page.click('button[type="submit"]')
            time.sleep(3)
            
            # 访问二阶段页面
            print("🌐 访问二阶段页面...")
            page.goto('http://localhost:5000/phase-two-generation')
            time.sleep(4)
            page.screenshot(path='screenshots/test1_page.png')
            print("✅ 截图: test1_page.png")
            
            # 查找项目卡片
            print("🔍 查找项目...")
            cards = page.locator('.project-select-card').all()
            print(f"📊 找到 {len(cards)} 个项目")
            
            if len(cards) == 0:
                print("⚠️ 没有项目，查看页面内容...")
                html = page.content()
                print(html[:2000])
                return
            
            # 选择项目
            cards[0].click()
            time.sleep(2)
            page.screenshot(path='screenshots/test2_selected.png')
            print("✅ 截图: test2_selected.png")
            
            # 切换到生成标签
            generate_tab = page.locator('[data-tab="generate"]').first
            if generate_tab.is_visible():
                generate_tab.click()
                time.sleep(1)
            
            # 填写并提交
            page.fill('#from-chapter', '1')
            page.fill('#chapters-to-generate', '3')
            time.sleep(0.5)
            
            start_btn = page.locator('#start-btn').first
            if start_btn.is_visible():
                start_btn.click()
                time.sleep(3)
                page.screenshot(path='screenshots/test3_started.png')
                print("✅ 截图: test3_started.png - 已启动生成")
                
                # 检查是否只有一个队列
                queue_items = page.locator('.chapter-queue__item').all()
                grid_items = page.locator('.v2-chapter-mini').all()
                print(f"📊 上方队列项目: {len(queue_items)}")
                print(f"📊 下方网格项目: {len(grid_items)}")
                
                if len(grid_items) == 0:
                    print("✅ 修复成功：下方网格队列已移除")
                else:
                    print(f"⚠️ 还有 {len(grid_items)} 个下方网格项目")
            
            print("\n✅ 测试完成!")
            
        except Exception as e:
            print(f"\n❌ 错误: {e}")
            page.screenshot(path='screenshots/test_error.png')
        finally:
            browser.close()


if __name__ == '__main__':
    os.makedirs('screenshots', exist_ok=True)
    test_ui()
