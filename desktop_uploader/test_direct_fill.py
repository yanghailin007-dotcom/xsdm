#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接在当前页面填写章节 - 假设已经在发布页面
"""

import time
import sys
from playwright.sync_api import sync_playwright

def generate_content(min_length: int = 1100) -> str:
    """生成超过1000字的内容"""
    paragraphs = [
        "清晨的阳光透过窗帘洒进房间，新的一天开始了。",
        "他走在繁华的街道上，周围是来来往往的行人。",
        "这座城市的夜晚格外迷人，霓虹灯闪烁着五彩斑斓的光芒。",
        "远方的山峦在云雾中若隐若现，仿佛一幅水墨画。",
        "咖啡的香气弥漫在空气中，让人感到一丝温暖。"
    ]
    content = ""
    idx = 0
    while len(content) < min_length:
        content += paragraphs[idx % len(paragraphs)] + "\n\n"
        idx += 1
    return content

def test_direct_fill(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 直接填写，不导航
        print("\n[1] 填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input').first
            if num_input.count() == 0:
                num_input = page.locator('.left-input input').first
            if num_input.count() > 0:
                num_input.fill("999")
                print("  [OK] 999")
            else:
                print("  [ERR] 未找到章节号输入框")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        print("[2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input').first
            if title_input.count() == 0:
                title_input = page.locator('.right-input input').first
            if title_input.count() > 0:
                title_input.fill("直接填充测试")
                print("  [OK]")
            else:
                print("  [ERR] 未找到标题输入框")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        print("[3] 填写内容...")
        try:
            content = generate_content(1100)
            editor = page.locator('.ProseMirror[contenteditable]').first
            if editor.count() > 0:
                editor.fill(content)
                length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
                print(f"  [OK] {length}字")
            else:
                print("  [ERR] 未找到编辑器")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        print("\n[完成] 请手动检查页面内容")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_direct_fill(port)
