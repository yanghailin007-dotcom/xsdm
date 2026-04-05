#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试：填写章节号 -> 下一步 -> 处理模态框 -> 发布
处理多个弹窗：发布设置、风险检测
"""

import time
import sys
from playwright.sync_api import sync_playwright

def generate_content(min_length: int = 1100) -> str:
    p = """这是一段测试文字。故事发生在一个神奇的世界，主人公踏上了冒险的旅程。在这个充满未知的世界里，每一步都充满了危险，但也蕴含着无限的机遇。"""
    content = ""
    while len(content) < min_length:
        content += p + "\n\n"
    return content

def click_any_button(page, texts, timeout=2000):
    """快速点击任意匹配按钮"""
    for text in texts:
        try:
            btn = page.locator(f'button:has-text("{text}")').first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                return text
        except:
            pass
    return None

def handle_all_modals(page, max_wait=10):
    """处理所有弹窗"""
    for i in range(max_wait):
        time.sleep(0.3)
        
        # 1. 发布设置模态框
        modal = page.locator('.publish-confirm-container-new, .arco-modal:has(.publish-confirm-card)').first
        if modal.count() > 0 and modal.is_visible():
            print("  [发现] 发布设置模态框")
            
            # 选 AI "否" - 点击第二个 radio
            try:
                # 方法1: 查找所有 radio，点击第二个
                radios = page.locator('.arco-radio').all()
                if len(radios) >= 2:
                    radios[1].click()
                    print("  [点击] AI: 否")
                else:
                    # 方法2: 通过文本
                    page.locator('text=否').first.click()
                    print("  [点击] AI: 否(文本)")
            except Exception as e:
                print(f"  [WARN] AI选择: {e}")
            
            time.sleep(0.2)
            
            # 点击确认发布
            try:
                footer_btn = page.locator('.arco-modal-footer button.arco-btn-primary').first
                if footer_btn.count() > 0:
                    footer_btn.click()
                    print("  [点击] 确认发布")
            except Exception as e:
                print(f"  [WARN] 确认发布: {e}")
            continue
        
        # 2. 风险检测弹窗
        risk_modal = page.locator('.arco-modal:has-text("风险检测")').first
        if risk_modal.count() > 0 and risk_modal.is_visible():
            print("  [发现] 风险检测弹窗")
            try:
                # 点击确定（开启风险检测）或取消（跳过）
                # 这里点击确定
                risk_modal.locator('button.arco-btn-primary').first.click()
                print("  [点击] 确定（风险检测）")
            except:
                pass
            continue
        
        # 3. 其他确认弹窗
        confirm = click_any_button(page, ["确定", "确认", "提交"])
        if confirm:
            print(f"  [点击] {confirm}")
            continue
        
        # 检查是否已完成（返回管理页）
        if '/manage' in page.url or '/book/' in page.url:
            print("  [完成] 已返回管理页")
            return True
    
    return False

def test_complete_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 1. 填写章节号
        print("\n[1] 填写章节号...")
        page.locator('.serial-editor-title-left input').first.fill("999")
        print("  [OK] 999")
        
        # 2. 填写标题
        print("[2] 填写标题...")
        page.locator('.serial-editor-title-right input').first.fill("测试章节-快速")
        print("  [OK]")
        
        # 3. 填写内容
        print("[3] 填写内容...")
        content = generate_content(1100)
        page.locator('.ProseMirror').first.fill(content)
        length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
        print(f"  [OK] {length}字")
        
        # 4. 点击下一步
        print("[4] 点击下一步...")
        page.locator('button:has-text("下一步")').first.click()
        print("  [OK]")
        
        # 5. 处理所有弹窗
        print("[5] 处理弹窗...")
        success = handle_all_modals(page)
        
        # 6. 结果
        print(f"\n[结果] URL: {page.url}")
        print(f"[结果] 成功: {success}")
        
        print("\n[完成]")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_complete_flow(port)
