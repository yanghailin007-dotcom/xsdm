#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
直接处理发布设置模态框 - 基于实际 HTML 结构
"""

import time
import sys
from playwright.sync_api import sync_playwright

def handle_modal(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 等待模态框出现
        print("\n[等待] 等待模态框...")
        for i in range(10):
            time.sleep(0.5)
            
            # 检查模态框 - 使用 card 类
            card = page.locator('.publish-confirm-card').first
            if card.count() > 0:
                print(f"[OK] 找到 publish-confirm-card")
                break
        else:
            print("[ERR] 未找到模态框")
            browser.close()
            return
        
        # 1. 点击 AI "否" - 直接点击第二个 label
        print("\n[1] 点击 AI 选项...")
        try:
            # 在 card 内部查找所有 radio label
            labels = card.locator('label.arco-radio').all()
            print(f"  找到 {len(labels)} 个 radio 选项")
            
            if len(labels) >= 2:
                # 点击第一个（是）
                labels[0].click()
                print("  [OK] 点击了第一个选项（是）")
            else:
                # 备选：通过 arco-radio-text 查找
                no_text = card.locator('.arco-radio-text:has-text("否")').first
                if no_text.count() > 0:
                    no_text.click()
                    print("  [OK] 通过文本点击是")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        time.sleep(0.3)
        
        # 2. 点击确认发布
        print("\n[2] 点击确认发布...")
        try:
            # 在整个页面中查找 footer 中的主按钮
            footer = page.locator('.arco-modal-footer').first
            if footer.count() > 0:
                confirm_btn = footer.locator('button.arco-btn-primary').first
                if confirm_btn.count() > 0:
                    confirm_btn.click()
                    print("  [OK] 点击确认发布")
                else:
                    print("  [ERR] footer 中没有主按钮")
            else:
                # 备选：直接查找所有按钮
                btns = page.locator('button:has-text("确认发布")').all()
                if len(btns) > 0:
                    btns[-1].click()  # 点击最后一个
                    print("  [OK] 点击确认发布(备选)")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 3. 处理风险检测弹窗
        print("\n[3] 等待并处理风险检测弹窗...")
        for i in range(5):
            time.sleep(0.5)
            
            try:
                # 查找风险检测弹窗
                risk_modal = page.locator('.arco-modal:has-text("风险检测")').first
                if risk_modal.count() > 0 and risk_modal.is_visible():
                    print("  [发现] 风险检测弹窗")
                    
                    # 点击确定
                    ok_btn = risk_modal.locator('button.arco-btn-primary').first
                    if ok_btn.count() > 0:
                        ok_btn.click()
                        print("  [OK] 点击确定")
                        break
            except:
                pass
            
            # 检查是否已完成
            if '/manage' in page.url:
                print("  [OK] 已返回管理页")
                break
        
        print(f"\n[结果] URL: {page.url}")
        print("[完成]")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    handle_modal(port)
