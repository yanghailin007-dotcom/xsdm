#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试章节上传流程（含发布）
连接到已存在的 Chrome 浏览器进行实时调试
"""

import time
import sys
from playwright.sync_api import sync_playwright

def generate_long_content(min_length: int = 1100) -> str:
    """生成超过1000字的测试内容"""
    paragraph = """这是一段测试文字，用于验证章节上传功能是否正常。故事发生在一个遥远的世界，那里有着神奇的魔法和强大的武技。主人公踏上了冒险的旅程，经历了无数的挑战和磨难。在这个充满未知的世界里，每一步都充满了危险，但也蕴含着无限的机遇。我们的英雄将如何面对这些挑战呢？让我们拭目以待。"""
    
    content = ""
    while len(content) < min_length:
        content += paragraph + "\n\n"
    return content

def click_button_with_retry(page, button_texts, timeout=5000):
    """尝试多种方式点击按钮"""
    for text in button_texts:
        try:
            # 尝试精确匹配
            btn = page.locator(f'button:has-text("{text}")').first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                return f'button:has-text("{text}")'
            
            # 尝试包含文本
            btn = page.locator(f'button:has-text("{text[:2]}")').first
            if btn.count() > 0 and btn.is_visible():
                btn.click()
                return f'button:has-text("{text[:2]}")'
        except:
            continue
    
    # 尝试通用的submit按钮
    try:
        btn = page.locator('button[type="submit"], input[type="submit"]').first
        if btn.count() > 0 and btn.is_visible():
            btn.click()
            return 'submit button'
    except:
        pass
    
    return None

def test_chapter_upload(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print(f"[连接] 连接到 Chrome (端口 {port})...")
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            print(f"[OK] 已连接")
        except Exception as e:
            print(f"[ERR] 连接失败: {e}")
            return
        
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            print("[ERR] 没有找到页面")
            return
        
        print(f"[页面] {page.url}")
        time.sleep(2)
        
        print("\n" + "="*60)
        print("[测试] 开始完整章节上传测试...")
        print("="*60)
        
        # 1. 填写章节号
        print("\n[1] 填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input.serial-input, .left-input input').first
            num_input.fill("")
            time.sleep(0.2)
            num_input.fill("999")
            print("  [OK] 章节号: 999")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 2. 填写标题
        print("\n[2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input.serial-input, .right-input input').first
            title_input.fill("")
            time.sleep(0.2)
            title_input.fill("测试章节 - 完整流程验证")
            print("  [OK] 标题已填写")
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 3. 填写内容（超过1000字）
        print("\n[3] 填写内容...")
        try:
            content = generate_long_content(1100)
            print(f"  生成内容长度: {len(content)} 字")
            
            editor = page.locator('.ProseMirror[contenteditable]').first
            editor.fill("")
            time.sleep(0.3)
            editor.fill(content)
            print("  [OK] 内容已填写")
            
            # 验证内容长度
            actual_length = page.evaluate('''() => {
                const editor = document.querySelector('.ProseMirror');
                return editor ? editor.innerText.length : 0;
            }''')
            print(f"  实际内容长度: {actual_length} 字")
            
        except Exception as e:
            print(f"  [ERR] {e}")
        
        # 4. 点击下一步
        print("\n[4] 点击下一步...")
        time.sleep(1)  # 等待按钮可用
        
        # 先查找所有按钮
        buttons = page.locator('button').all()
        print(f"  页面共有 {len(buttons)} 个按钮")
        for i, btn in enumerate(buttons[:5]):  # 显示前5个
            try:
                text = btn.text_content()
                visible = btn.is_visible()
                print(f"    按钮{i}: '{text}' (可见:{visible})")
            except:
                pass
        
        clicked = click_button_with_retry(page, ["下一步", "保存", "提交"])
        if clicked:
            print(f"  [OK] 已点击: {clicked}")
        else:
            print("  [ERR] 未找到可点击的按钮")
        
        time.sleep(2)
        
        # 5. 检查是否进入确认页面
        print("\n[5] 检查页面状态...")
        current_url = page.url
        print(f"  当前URL: {current_url}")
        
        # 再次查找确认发布按钮
        buttons = page.locator('button').all()
        print(f"  页面共有 {len(buttons)} 个按钮")
        confirm_found = False
        for i, btn in enumerate(buttons):
            try:
                text = btn.text_content()
                if text and ("确认" in text or "发布" in text or "确定" in text):
                    print(f"    找到按钮: '{text}'")
                    if btn.is_visible():
                        btn.click()
                        print(f"  [OK] 已点击: {text}")
                        confirm_found = True
                        break
            except:
                pass
        
        if not confirm_found:
            print("  [WARN] 未找到确认按钮")
            # 检查是否有错误提示
            error_msg = page.locator('.error-message, .error-tip, .tips').first
            if error_msg.count() > 0:
                print(f"  错误信息: {error_msg.text_content()}")
        
        time.sleep(3)
        
        # 6. 检查结果
        print("\n[6] 检查发布结果...")
        final_url = page.url
        print(f"  最终URL: {final_url}")
        
        if "manage" in final_url or "book" in final_url:
            print("  [OK] 已返回到书籍管理页面，发布可能成功")
        else:
            print("  [INFO] 请手动检查页面状态")
        
        print("\n" + "="*60)
        print("[OK] 测试完成！")
        print("="*60)
        
        input("\n按回车断开连接...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_chapter_upload(port)
