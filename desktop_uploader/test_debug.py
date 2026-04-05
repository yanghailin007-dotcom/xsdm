#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试定时发布开关
"""

import time
import sys
from playwright.sync_api import sync_playwright

def debug_switch(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        
        # 等待模态框
        print("\n[等待] 等待模态框...")
        for i in range(10):
            time.sleep(0.5)
            card = page.locator('.publish-confirm-card').first
            if card.count() > 0:
                print("[OK] 找到模态框")
                break
        
        # 调试：列出所有 switch
        print("\n[调试] 查找所有 switch 按钮...")
        switches = page.locator('button[role="switch"]').all()
        print(f"  找到 {len(switches)} 个 switch")
        
        for i, sw in enumerate(switches):
            try:
                checked = sw.get_attribute('aria-checked')
                class_name = sw.get_attribute('class')
                visible = sw.is_visible()
                print(f"  Switch {i}: checked={checked}, visible={visible}, class={class_name[:50]}")
            except Exception as e:
                print(f"  Switch {i}: 错误 {e}")
        
        # 尝试点击第一个 switch
        if len(switches) > 0:
            print("\n[点击] 点击第一个 switch...")
            try:
                switches[0].click()
                print("[OK] 已点击")
                
                time.sleep(1)
                
                # 再次检查状态
                new_checked = switches[0].get_attribute('aria-checked')
                print(f"  点击后状态: {new_checked}")
                
                # 检查时间选择器是否出现
                picker = page.locator('.arco-picker, .arco-date-picker, input[placeholder*="时间"]').first
                print(f"  时间选择器存在: {picker.count() > 0}")
                if picker.count() > 0:
                    print(f"  时间选择器可见: {picker.is_visible()}")
                    
            except Exception as e:
                print(f"[ERR] {e}")
        
        # 调试：检查定时发布相关元素
        print("\n[调试] 查找定时发布相关元素...")
        
        # 查找包含"定时发布"文本的元素
        timed_labels = page.locator('text=定时发布').all()
        print(f"  '定时发布' 文本出现 {len(timed_labels)} 次")
        
        # 查找 publish-confirm-timed-help
        help_divs = page.locator('.publish-confirm-timed-help').all()
        print(f"  help div 存在: {len(help_divs)}")
        
        # 查找时间选择器
        pickers = page.locator('.arco-picker').all()
        print(f"  arco-picker 存在: {len(pickers)}")
        
        print("\n[完成]")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    debug_switch(port)
