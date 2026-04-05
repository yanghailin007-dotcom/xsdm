#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试：多样化内容 + 定时发布
"""

import time
import sys
from playwright.sync_api import sync_playwright

def generate_diverse_content(min_length: int = 1100) -> str:
    """生成多样化内容，避免重复"""
    paragraphs = [
        "清晨的阳光透过窗帘洒进房间，新的一天开始了。",
        "他走在繁华的街道上，周围是来来往往的行人。",
        "这座城市的夜晚格外迷人，霓虹灯闪烁着五彩斑斓的光芒。",
        "远方的山峦在云雾中若隐若现，仿佛一幅水墨画。",
        "咖啡的香气弥漫在空气中，让人感到一丝温暖。",
        "他翻开那本旧书，泛黄的纸页记录着岁月的故事。",
        "雨滴轻轻敲打着窗户，节奏舒缓而有规律。",
        "海边的风带着咸湿的气息，吹拂着脸庞。",
        "星空下，两人并肩而坐，享受着宁静的夜晚。",
        "古老的小镇保留着原始的风貌，青石板路延伸到远方。"
    ]
    
    content = ""
    idx = 0
    while len(content) < min_length:
        content += paragraphs[idx % len(paragraphs)] + "\n\n"
        idx += 1
    return content

def test_complete_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 1. 填写章节号
        print("\n[1] 填写章节号...")
        page.locator('.serial-editor-title-left input').first.fill("1000")
        print("  [OK] 1000")
        
        # 2. 填写标题
        print("[2] 填写标题...")
        page.locator('.serial-editor-title-right input').first.fill("定时发布测试章节")
        print("  [OK]")
        
        # 3. 填写多样化内容
        print("[3] 填写内容...")
        content = generate_diverse_content(1100)
        page.locator('.ProseMirror').first.fill(content)
        length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
        print(f"  [OK] {length}字")
        
        # 4. 点击下一步
        print("[4] 点击下一步...")
        page.locator('button:has-text("下一步")').first.click()
        print("  [OK]")
        
        # 5. 处理发布设置模态框
        print("\n[5] 处理发布设置模态框...")
        for i in range(10):
            time.sleep(0.5)
            
            card = page.locator('.publish-confirm-card').first
            if card.count() > 0:
                print("  [OK] 找到模态框")
                
                # 5.1 选择 AI "是"
                try:
                    labels = card.locator('label.arco-radio').all()
                    if len(labels) >= 1:
                        labels[0].click()  # 第一个是"是"
                        print("  [OK] 选择 AI: 是")
                except Exception as e:
                    print(f"  [WARN] AI: {e}")
                
                time.sleep(0.3)
                
                # 5.2 开启定时发布
                print("  [6] 开启定时发布...")
                try:
                    # 查找定时发布开关
                    switch = page.locator('.arco-switch').first
                    if switch.count() > 0:
                        is_on = switch.get_attribute('aria-checked') == 'true'
                        if not is_on:
                            switch.click()
                            print("    [OK] 开启定时发布")
                            time.sleep(0.5)
                            
                            # 选择时间（默认明天同一时间）
                            # 或者点击时间选择器选择具体时间点
                            time_picker = page.locator('.arco-picker, .publish-confirm-timed-picker').first
                            if time_picker.count() > 0:
                                time_picker.click()
                                time.sleep(0.3)
                                # 选择第一个可用时间
                                first_time = page.locator('.arco-timepicker-cell, .arco-picker-cell').first
                                if first_time.count() > 0:
                                    first_time.click()
                                    print("    [OK] 选择时间")
                        else:
                            print("    [OK] 定时发布已开启")
                except Exception as e:
                    print(f"    [WARN] 定时发布: {e}")
                
                time.sleep(0.3)
                
                # 5.3 点击确认发布
                try:
                    footer = page.locator('.arco-modal-footer').first
                    confirm = footer.locator('button.arco-btn-primary').first
                    confirm.click()
                    print("  [OK] 点击确认发布")
                except Exception as e:
                    print(f"  [ERR] {e}")
                
                break
        
        # 6. 处理风险检测弹窗
        print("\n[7] 处理风险检测...")
        for i in range(5):
            time.sleep(0.5)
            
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                print("  [发现] 风险检测弹窗")
                risk.locator('button.arco-btn-primary').first.click()
                print("  [OK] 点击确定")
                break
            
            if '/manage' in page.url:
                print("  [OK] 已返回管理页")
                break
        
        # 7. 结果
        print(f"\n[结果] 最终URL: {page.url}")
        print("[完成]")
        
        input("按回车断开...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_complete_flow(port)
