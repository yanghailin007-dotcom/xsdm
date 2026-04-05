#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试流程 V2 - 实时日志输出
假设已在发布页面
"""

import time
import sys
from playwright.sync_api import sync_playwright

def log(msg):
    """实时打印日志"""
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def generate_content(min_length: int = 1100) -> str:
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

def test_full_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        log("连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        log(f"当前页面: {page.url}")
        
        # 1. 填写章节号
        log("[步骤1] 查找并填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input').first
            if num_input.count() == 0:
                num_input = page.locator('.left-input input').first
            if num_input.count() > 0:
                num_input.fill("888")
                log(f"  [OK] 填写章节号: 888")
            else:
                log("  [ERR] 未找到章节号输入框")
                return
        except Exception as e:
            log(f"  [ERR] {e}")
            return
        
        # 2. 填写标题
        log("[步骤2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input').first
            if title_input.count() == 0:
                title_input = page.locator('.right-input input').first
            if title_input.count() > 0:
                title_input.fill("完整流程测试-定时发布")
                log("  [OK] 标题已填写")
            else:
                log("  [ERR] 未找到标题输入框")
        except Exception as e:
            log(f"  ✗ 错误: {e}")
        
        # 3. 填写内容
        log("[步骤3] 填写内容...")
        try:
            content = generate_content(1100)
            editor = page.locator('.ProseMirror[contenteditable]').first
            if editor.count() > 0:
                editor.fill(content)
                length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
                log(f"  [OK] 内容已填写: {length}字")
            else:
                log("  [ERR] 未找到编辑器")
        except Exception as e:
            log(f"  ✗ 错误: {e}")
        
        time.sleep(1)
        
        # 4. 点击下一步
        log("[步骤4] 点击下一步...")
        try:
            next_btn = page.locator('button:has-text("下一步")').first
            if next_btn.count() > 0:
                next_btn.click()
                log("  [OK] 已点击下一步")
                time.sleep(2)
            else:
                log("  [ERR] 未找到下一步按钮")
        except Exception as e:
            log(f"  ✗ 错误: {e}")
        
        # 5. 处理发布设置模态框
        log("[步骤5] 等待并处理发布设置模态框...")
        modal_found = False
        for i in range(15):  # 最多等待7.5秒
            time.sleep(0.5)
            
            # 检查模态框
            modal = page.locator('.publish-confirm-container-new').first
            if modal.count() > 0 and modal.is_visible():
                modal_found = True
                log("  [OK] 找到发布设置模态框")
                break
            
            # 也检查arco-modal
            modal2 = page.locator('.arco-modal:has(.publish-confirm-card)').first
            if modal2.count() > 0 and modal2.is_visible():
                modal_found = True
                log("  [OK] 找到模态框(备选)")
                break
        
        if not modal_found:
            log("  [ERR] 未找到模态框")
            return
        
        # 5.1 选择 AI "是" - 在第一个card中查找（AI选项在第一个publish-confirm-card里）
        log("[步骤5.1] 选择 AI: 是...")
        try:
            # 方法1: 在第一个publish-confirm-card中查找radio
            cards = page.locator('.publish-confirm-card').all()
            log(f"  找到 {len(cards)} 个 card")
            if len(cards) >= 1:
                ai_card = cards[0]  # AI选项在第一个card
                radios = ai_card.locator('label.arco-radio').all()
                log(f"  第一个card中有 {len(radios)} 个 radio")
                if len(radios) >= 1:
                    radios[0].click()  # 第一个是"是"
                    log("  [OK] 已选择 AI: 是")
                else:
                    log("  [WARN] 第一个card中没有radio")
            else:
                log("  [WARN] 未找到card")
        except Exception as e:
            log(f"  [WARN] AI选择失败: {e}")
        
        time.sleep(0.5)
        
        # 5.2 开启定时发布
        log("[步骤5.2] 开启定时发布...")
        try:
            switch = page.locator('button[role="switch"]').first
            if switch.count() > 0:
                is_on = switch.get_attribute('aria-checked') == 'true'
                log(f"  当前状态: {'已开启' if is_on else '已关闭'}")
                
                if not is_on:
                    switch.click()
                    log("  [OK] 已点击开启")
                    time.sleep(1)
                    
                    # 选择时间
                    picker = page.locator('.arco-picker-input input').first
                    if picker.count() > 0:
                        log("  [INFO] 打开时间选择器...")
                        picker.click()
                        time.sleep(0.5)
                        
                        # 选择第一个可用时间
                        time_cell = page.locator('.arco-timepicker-cell, .arco-picker-time-cell').first
                        if time_cell.count() > 0:
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
        
        time.sleep(0.5)
        
        # 5.3 确认发布
        log("[步骤5.3] 点击确认发布...")
        try:
            # 方法1: 通过footer查找
            confirm = page.locator('.arco-modal-footer button.arco-btn-primary').first
            if confirm.count() > 0 and confirm.is_visible():
                confirm.click()
                log("  [OK] 已点击确认发布(footer)")
            else:
                # 方法2: 通过文本查找
                confirm2 = page.locator('button:has-text("确认发布")').first
                if confirm2.count() > 0 and confirm2.is_visible():
                    confirm2.click()
                    log("  [OK] 已点击确认发布(文本)")
                else:
                    log("  [ERR] 未找到确认发布按钮")
                    return
        except Exception as e:
            log(f"  [ERR] 点击确认发布失败: {e}")
            return
        
        # 6. 处理风险检测弹窗
        log("[步骤6] 等待风险检测弹窗...")
        for i in range(10):
            time.sleep(0.5)
            
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                log("  [OK] 发现风险检测弹窗")
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
        
        log(f"\n[完成] 最终URL: {page.url}")
        input("\n按回车断开连接...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_full_flow(port)
