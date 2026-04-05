#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试流程 - 模拟人类操作速度，防风控
"""

import time
import random
import sys
from playwright.sync_api import sync_playwright

def log(msg):
    """实时打印日志"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def human_sleep(min_sec=0.5, max_sec=2.0):
    """模拟人类操作的随机延迟"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

def generate_content(min_length: int = 1100) -> str:
    """生成多样化内容"""
    paragraphs = [
        "清晨的阳光透过窗帘洒进房间，新的一天开始了。这是充满希望的时刻，万物都在苏醒。",
        "他走在繁华的街道上，周围是来来往往的行人，每个人都有着自己的故事和目的地。",
        "这座城市的夜晚格外迷人，霓虹灯闪烁着五彩斑斓的光芒，照亮了每一个角落。",
        "远方的山峦在云雾中若隐若现，仿佛一幅水墨画，让人心旷神怡。",
        "咖啡的香气弥漫在空气中，让人感到一丝温暖，思绪也随之飘远。"
    ]
    content = ""
    idx = 0
    while len(content) < min_length:
        content += paragraphs[idx % len(paragraphs)] + "\n\n"
        idx += 1
    return content

def test_human_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        log("连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        log(f"当前页面: {page.url}")
        
        human_sleep(1, 2)  # 初始等待
        
        # 1. 填写章节号
        log("[步骤1] 查找并填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input').first
            if num_input.count() == 0:
                num_input = page.locator('.left-input input').first
            if num_input.count() > 0:
                num_input.click()  # 先点击聚焦
                human_sleep(0.3, 0.8)
                num_input.fill("")
                human_sleep(0.2, 0.5)
                num_input.type("888", delay=random.uniform(0.05, 0.15))  # 模拟打字
                log(f"  [OK] 填写章节号: 888")
            else:
                log("  [ERR] 未找到章节号输入框")
                return
        except Exception as e:
            log(f"  [ERR] {e}")
            return
        
        human_sleep(0.5, 1.5)  # 填写后思考时间
        
        # 2. 填写标题
        log("[步骤2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input').first
            if title_input.count() == 0:
                title_input = page.locator('.right-input input').first
            if title_input.count() > 0:
                title_input.click()
                human_sleep(0.3, 0.8)
                title_input.fill("")
                human_sleep(0.2, 0.5)
                title_input.type("完整流程测试-定时发布", delay=random.uniform(0.03, 0.1))
                log("  [OK] 标题已填写")
            else:
                log("  [ERR] 未找到标题输入框")
        except Exception as e:
            log(f"  [ERR] {e}")
        
        human_sleep(0.5, 1.5)
        
        # 3. 填写内容
        log("[步骤3] 填写内容...")
        try:
            content = generate_content(1100)
            editor = page.locator('.ProseMirror[contenteditable]').first
            if editor.count() > 0:
                editor.click()  # 先点击编辑器
                human_sleep(0.5, 1.0)
                editor.fill("")  # 清空
                human_sleep(0.3, 0.6)
                # 分段输入，模拟人类打字
                chunks = [content[i:i+50] for i in range(0, len(content), 50)]
                for i, chunk in enumerate(chunks):
                    editor.type(chunk, delay=random.uniform(0.01, 0.03))
                    if i % 5 == 0:  # 每5段暂停一下
                        human_sleep(0.2, 0.5)
                length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
                log(f"  [OK] 内容已填写: {length}字")
            else:
                log("  [ERR] 未找到编辑器")
        except Exception as e:
            log(f"  [ERR] {e}")
        
        human_sleep(1, 2)  # 填写完内容后检查
        
        # 4. 点击下一步
        log("[步骤4] 点击下一步...")
        try:
            next_btn = page.locator('button:has-text("下一步")').first
            if next_btn.count() > 0:
                human_sleep(0.5, 1.0)  # 找到按钮后犹豫一下
                next_btn.click()
                log("  [OK] 已点击下一步")
                human_sleep(2, 3)  # 等待模态框弹出
            else:
                log("  [ERR] 未找到下一步按钮")
        except Exception as e:
            log(f"  [ERR] {e}")
        
        # 5. 处理发布设置模态框
        log("[步骤5] 等待并处理发布设置模态框...")
        modal_found = False
        for i in range(15):
            time.sleep(0.5)
            
            modal = page.locator('.publish-confirm-container-new').first
            if modal.count() > 0 and modal.is_visible():
                modal_found = True
                log("  [OK] 找到发布设置模态框")
                break
            
            modal2 = page.locator('.arco-modal:has(.publish-confirm-card)').first
            if modal2.count() > 0 and modal2.is_visible():
                modal_found = True
                log("  [OK] 找到模态框(备选)")
                break
        
        if not modal_found:
            log("  [ERR] 未找到模态框")
            return
        
        human_sleep(0.8, 1.5)  # 模态框出现后阅读时间
        
        # 5.1 选择 AI "是"
        log("[步骤5.1] 选择 AI: 是...")
        try:
            cards = page.locator('.publish-confirm-card').all()
            log(f"  找到 {len(cards)} 个 card")
            if len(cards) >= 1:
                ai_card = cards[0]
                radios = ai_card.locator('label.arco-radio').all()
                log(f"  第一个card中有 {len(radios)} 个 radio")
                if len(radios) >= 1:
                    human_sleep(0.3, 0.8)  # 找到后犹豫
                    radios[0].click()
                    log("  [OK] 已选择 AI: 是")
                else:
                    log("  [WARN] 第一个card中没有radio")
            else:
                log("  [WARN] 未找到card")
        except Exception as e:
            log(f"  [WARN] AI选择失败: {e}")
        
        human_sleep(0.5, 1.2)
        
        # 5.2 开启定时发布
        log("[步骤5.2] 开启定时发布...")
        try:
            switch = page.locator('button[role="switch"]').first
            if switch.count() > 0:
                is_on = switch.get_attribute('aria-checked') == 'true'
                log(f"  当前状态: {'已开启' if is_on else '已关闭'}")
                
                if not is_on:
                    human_sleep(0.3, 0.6)
                    switch.click()
                    log("  [OK] 已点击开启")
                    human_sleep(1.5, 2.5)  # 等待时间选择器出现
                    
                    picker = page.locator('.arco-picker-input input').first
                    if picker.count() > 0:
                        log("  [INFO] 打开时间选择器...")
                        human_sleep(0.3, 0.6)
                        picker.click()
                        human_sleep(0.8, 1.5)  # 等待下拉展开
                        
                        time_cell = page.locator('.arco-timepicker-cell, .arco-picker-time-cell').first
                        if time_cell.count() > 0:
                            human_sleep(0.3, 0.6)
                            time_cell.click()
                            log("  [OK] 已选择时间")
                        else:
                            log("  [WARN] 未找到时间选项")
                    else:
                        log("  [WARN] 未找到时间选择器")
                else:
                    log("  [OK] 定时发布已开启")
            else:
                log("  [WARN] 未找到定时发布开关")
        except Exception as e:
            log(f"  [WARN] 定时发布失败: {e}")
        
        human_sleep(0.8, 1.5)  # 设置完定时后确认
        
        # 5.3 确认发布
        log("[步骤5.3] 点击确认发布...")
        try:
            confirm = page.locator('.arco-modal-footer button.arco-btn-primary').first
            if confirm.count() > 0 and confirm.is_visible():
                human_sleep(0.5, 1.0)  # 点击前犹豫
                confirm.click()
                log("  [OK] 已点击确认发布")
            else:
                confirm2 = page.locator('button:has-text("确认发布")').first
                if confirm2.count() > 0 and confirm2.is_visible():
                    human_sleep(0.5, 1.0)
                    confirm2.click()
                    log("  [OK] 已点击确认发布(文本)")
                else:
                    log("  [ERR] 未找到确认发布按钮")
                    return
        except Exception as e:
            log(f"  [ERR] 点击确认发布失败: {e}")
            return
        
        human_sleep(2, 3)  # 等待风险检测弹窗
        
        # 6. 处理风险检测弹窗
        log("[步骤6] 等待风险检测弹窗...")
        for i in range(10):
            time.sleep(0.5)
            
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                log("  [OK] 发现风险检测弹窗")
                human_sleep(0.5, 1.0)  # 阅读弹窗内容
                try:
                    ok_btn = risk.locator('button.arco-btn-primary').first
                    ok_btn.click()
                    log("  [OK] 已点击确定")
                except Exception as e:
                    log(f"  [WARN] 点击确定失败: {e}")
                break
            
            if '/manage' in page.url:
                log("  [OK] 已返回管理页，发布成功")
                break
        
        human_sleep(1, 2)
        log(f"\n[完成] 最终URL: {page.url}")
        input("\n按回车断开连接...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_human_flow(port)
