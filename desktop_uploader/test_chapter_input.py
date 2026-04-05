#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试章节号输入框激活逻辑
使用 Playwright 连接已存在的 Chrome 浏览器（应用程序管理的实例）
"""

import time
import sys
from playwright.sync_api import sync_playwright

def test_chapter_input(port: int = 10002):
    """连接到指定端口的 Chrome 实例进行测试"""
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print(f"[连接] 连接到 Chrome (端口 {port})...")
        try:
            browser = p.chromium.connect_over_cdp(cdp_url)
            print(f"[OK] 已连接到 Chrome (端口 {port})")
        except Exception as e:
            print(f"[ERR] 连接失败: {e}")
            print(f"\n请确保 Chrome 已在端口 {port} 启动")
            print("或者尝试其他端口: python test_chapter_input.py 10001")
            return
        
        # 获取第一个页面
        contexts = browser.contexts
        if contexts and contexts[0].pages:
            page = contexts[0].pages[0]
        else:
            print("❌ 没有找到页面")
            return
        
        print(f"[页面] 当前页面: {page.url}")
        
        # 如果不是发布页面，等待用户导航
        if "serial-editor" not in page.url:
            print("[!] 当前不在章节发布页面")
            print("请在浏览器中手动点击'创建章节'，然后按回车继续...")
            input()
        
        print("\n[测试] 开始测试章节号输入框激活...")
        print("=" * 60)
        
        # 测试1: 检查当前DOM状态
        print("\n[测试1] 检查DOM状态...")
        try:
            result = page.evaluate('''() => {
                const left = document.querySelector('.serial-editor-title-left');
                const input = document.querySelector('.serial-editor-title-left input.serial-input');
                return {
                    containerExists: !!left,
                    containerClass: left ? left.className : null,
                    containerHidden: left ? left.classList.contains('none') : null,
                    inputExists: !!input,
                    inputVisible: input ? input.offsetParent !== null : null
                };
            }''')
            print(f"  容器存在: {result['containerExists']}")
            print(f"  容器 class: {result['containerClass']}")
            print(f"  容器隐藏 (none): {result['containerHidden']}")
            print(f"  输入框存在: {result['inputExists']}")
            print(f"  输入框可见: {result['inputVisible']}")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 测试2: 点击激活
        print("\n[测试2] 点击激活...")
        try:
            left_container = page.locator('.serial-editor-title-left, .left-input').first
            if left_container.count() > 0:
                left_container.click()
                print("  [OK] 已点击容器")
                time.sleep(1)
                
                # 检查激活后的状态
                result = page.evaluate('''() => {
                    const left = document.querySelector('.serial-editor-title-left');
                    const input = document.querySelector('.serial-editor-title-left input.serial-input');
                    return {
                        containerClass: left ? left.className : null,
                        containerHidden: left ? left.classList.contains('none') : null,
                        inputVisible: input ? input.offsetParent !== null : null
                    };
                }''')
                print(f"  点击后容器 class: {result['containerClass']}")
                print(f"  点击后容器隐藏: {result['containerHidden']}")
                print(f"  点击后输入框可见: {result['inputVisible']}")
            else:
                print("  [ERR] 未找到容器")
        except Exception as e:
            print(f"  错误: {e}")
        
        # 测试3: JS 移除 none 类
        print("\n[测试3] JS 移除 none 类...")
        try:
            result = page.evaluate('''() => {
                const left = document.querySelector('.serial-editor-title-left');
                if (left) {
                    const hadNone = left.classList.contains('none');
                    left.classList.remove('none');
                    // 同时设置 style
                    left.style.display = 'flex';
                    left.style.visibility = 'visible';
                    return { success: true, hadNone, classNow: left.className };
                }
                return { success: false, error: 'container not found' };
            }''')
            print(f"  结果: {result}")
            time.sleep(0.5)
            
            # 检查输入框是否可交互
            num_input = page.locator('.serial-editor-title-left input.serial-input').first
            if num_input.count() > 0:
                visible = num_input.is_visible()
                print(f"  JS操作后输入框可见: {visible}")
                
                if visible:
                    print("  [OK] 输入框已可见，尝试输入...")
                    num_input.fill("")
                    time.sleep(0.2)
                    num_input.fill("123")
                    print("  [OK] 已成功输入 '123'")
        except Exception as e:
            print(f"  错误: {e}")
        
        print("\n" + "=" * 60)
        print("[OK] 测试完成！")
        print("请查看浏览器中的实际效果。")
        print("\n保持浏览器打开，可以手动验证。")
        input("\n按回车断开连接...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_chapter_input(port)
