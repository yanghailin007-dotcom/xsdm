#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
处理发布设置模态框
"""

import time
import sys
from playwright.sync_api import sync_playwright

def handle_publish_modal(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接到 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        contexts = browser.contexts
        page = contexts[0].pages[0] if contexts and contexts[0].pages else None
        
        if not page:
            print("[ERR] 没有找到页面")
            return
        
        print(f"[页面] {page.url}")
        
        # 检查模态框 - 使用多种选择器
        print("\n[检查] 查找模态框...")
        
        # 列出所有可能的模态框
        selectors = [
            '.publish-confirm-container-new',
            '.arco-modal',
            '[role="dialog"]',
            '.arco-modal-wrapper'
        ]
        
        for sel in selectors:
            count = page.locator(sel).count()
            print(f"  {sel}: {count} 个")
        
        # 使用最具体的选择器
        modal = page.locator('.publish-confirm-container-new').first
        if modal.count() == 0:
            modal = page.locator('.arco-modal:has(.publish-confirm-card)').first
        if modal.count() == 0:
            modal = page.locator('.arco-modal').first
        
        if modal.count() == 0:
            print("[WARN] 未找到模态框")
            # 检查是否有遮罩层
            mask = page.locator('.arco-modal-mask, .arco-overlay').first
            print(f"  遮罩层存在: {mask.count() > 0}")
            return
        
        print("[OK] 找到模态框")
        
        # 检查模态框内容
        try:
            title = modal.locator('.arco-modal-title').text_content()
            print(f"  标题: {title}")
        except:
            pass
        
        # 1. 选择 AI 选项（选择"否"）
        print("\n[1] 选择 AI 选项...")
        try:
            # 查找 radio group
            radio_group = modal.locator('.arco-radio-group').first
            if radio_group.count() > 0:
                # 点击第二个选项（否）
                radios = radio_group.locator('.arco-radio').all()
                print(f"  找到 {len(radios)} 个选项")
                if len(radios) >= 2:
                    radios[1].click()  # 点击"否"
                    print("  [OK] 选择 AI: 否")
                else:
                    # 通过文本查找
                    no_option = modal.locator('text=否').first
                    if no_option.count() > 0:
                        no_option.click()
                        print("  [OK] 选择 AI: 否 (通过文本)")
            else:
                print("  [WARN] 未找到 radio group")
        except Exception as e:
            print(f"  [WARN] {e}")
        
        time.sleep(0.5)
        
        # 2. 点击确认发布
        print("\n[2] 点击确认发布...")
        try:
            # 方法1: footer 中的主按钮
            confirm_btn = modal.locator('.arco-modal-footer button.arco-btn-primary').first
            if confirm_btn.count() > 0:
                print(f"  找到按钮, 可见: {confirm_btn.is_visible()}")
                confirm_btn.click()
                print("  [OK] 已点击确认发布")
            else:
                # 方法2: 通过文本
                confirm_btn = modal.locator('button:has-text("确认发布")').first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    print("  [OK] 已点击确认发布 (文本)")
                else:
                    print("  [ERR] 未找到确认发布按钮")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        time.sleep(3)
        
        # 检查结果
        print("\n[3] 检查结果...")
        modal_gone = modal.count() == 0 or not modal.is_visible()
        print(f"  模态框已关闭: {modal_gone}")
        print(f"  当前URL: {page.url}")
        
        print("\n[完成]")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    handle_publish_modal(port)
