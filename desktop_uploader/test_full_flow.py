#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试流程：假设已在发布页面
填写章节 -> 下一步 -> AI选择 -> 定时发布 -> 确认 -> 风险弹窗
"""

import time
import sys
from playwright.sync_api import sync_playwright

def generate_content(min_length: int = 1100) -> str:
    """生成多样化内容，避免重复"""
    paragraphs = [
        "清晨的阳光透过窗帘洒进房间，新的一天开始了。这是一个充满希望的时刻，万物都在苏醒。",
        "他走在繁华的街道上，周围是来来往往的行人，每个人都有着自己的故事和目的地。",
        "这座城市的夜晚格外迷人，霓虹灯闪烁着五彩斑斓的光芒，照亮了每一个角落。",
        "远方的山峦在云雾中若隐若现，仿佛一幅水墨画，让人心旷神怡。",
        "咖啡的香气弥漫在空气中，让人感到一丝温暖，思绪也随之飘远。",
        "翻开那本旧书，泛黄的纸页记录着岁月的故事，文字间流淌着智慧的光芒。",
        "雨滴轻轻敲打着窗户，节奏舒缓而有规律，像是在演奏一首自然的乐曲。",
        "海边的风带着咸湿的气息，吹拂着脸庞，带来了大海的问候。"
    ]
    content = ""
    idx = 0
    while len(content) < min_length:
        content += paragraphs[idx % len(paragraphs)] + "\n\n"
        idx += 1
    return content

def test_full_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 1. 填写章节号
        print("\n[1] 填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input').first
            if num_input.count() == 0:
                num_input = page.locator('.left-input input').first
            if num_input.count() > 0:
                num_input.fill("888")
                print("  [OK] 888")
            else:
                print("  [ERR] 未找到")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 2. 填写标题
        print("[2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input').first
            if title_input.count() == 0:
                title_input = page.locator('.right-input input').first
            if title_input.count() > 0:
                title_input.fill("完整流程测试-定时发布")
                print("  [OK]")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 3. 填写内容（多样化，>1000字）
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
        
        time.sleep(1)
        
        # 4. 点击下一步
        print("\n[4] 点击下一步...")
        try:
            next_btn = page.locator('button:has-text("下一步")').first
            if next_btn.count() > 0:
                next_btn.click()
                print("  [OK] 已点击")
                time.sleep(2)
            else:
                print("  [ERR] 未找到按钮")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 5. 处理发布设置模态框
        print("\n[5] 处理发布设置...")
        for i in range(10):
            time.sleep(0.5)
            
            # 查找模态框
            card = page.locator('.publish-confirm-card').first
            if card.count() > 0:
                print("  [OK] 找到模态框")
                
                # 5.1 选择 AI "是"
                try:
                    radios = card.locator('label.arco-radio').all()
                    if len(radios) >= 1:
                        radios[0].click()
                        print("  [OK] AI: 是")
                except Exception as e:
                    print(f"  [WARN] AI: {e}")
                
                time.sleep(0.3)
                
                # 5.2 开启定时发布
                print("  [6] 定时发布...")
                try:
                    switch = page.locator('button[role="switch"]').first
                    if switch.count() > 0:
                        is_on = switch.get_attribute('aria-checked') == 'true'
                        print(f"    当前: {'开' if is_on else '关'}")
                        
                        if not is_on:
                            switch.click()
                            print("    [OK] 开启")
                            time.sleep(0.8)
                            
                            # 选择时间
                            picker = page.locator('.arco-picker-input input').first
                            if picker.count() > 0:
                                picker.click()
                                time.sleep(0.3)
                                cell = page.locator('.arco-timepicker-cell').first
                                if cell.count() > 0:
                                    cell.click()
                                    print("    [OK] 选时间")
                        else:
                            print("    [OK] 已开启")
                except Exception as e:
                    print(f"    [WARN] {e}")
                
                time.sleep(0.3)
                
                # 5.3 确认发布
                print("  [7] 确认发布...")
                try:
                    footer = page.locator('.arco-modal-footer').first
                    confirm = footer.locator('button.arco-btn-primary').first
                    confirm.click()
                    print("  [OK] 已点击")
                except Exception as e:
                    print(f"  [ERR] {e}")
                
                break
        
        # 6. 处理风险检测弹窗
        print("\n[8] 风险检测...")
        for i in range(5):
            time.sleep(0.5)
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                print("  [发现]")
                risk.locator('button.arco-btn-primary').first.click()
                print("  [OK] 确定")
                break
            if '/manage' in page.url:
                print("  [OK] 返回管理页")
                break
        
        print(f"\n[结果] URL: {page.url}")
        print("[完成]")
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_full_flow(port)
