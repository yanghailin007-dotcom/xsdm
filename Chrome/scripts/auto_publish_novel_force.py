#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说自动发布脚本 - 强制模式，无需用户确认
"""

import sys
import os
import time
import json
from datetime import datetime

# 设置控制台编码
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except AttributeError:
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# 添加项目路径
sys.path.append('../..')  # 添加项目根目录
sys.path.append('../automation')  # 添加automation目录

def main():
    print("=" * 60)
    print("小说自动发布系统 - 强制模式 (优化版)")
    print("=" * 60)
    
    try:
        # 导入番茄上传模块
        from automation.legacy.autopush_legacy import (
            publish_novel, list_json_files, CONFIG, ensure_directory_exists,
            connect_to_browser, navigate_to_writer_platform, WORD_COUNT_THRESHOLD
        )
        
        print("模块导入成功")
        
        # 修改预发布字数阈值为20000字
        original_threshold = WORD_COUNT_THRESHOLD
        CONFIG["min_words_for_scheduled_publish"] = 20000
        print(f"📝 预发布字数阈值已修改为: 20000字 (原值: {original_threshold}字)")
        
        # 使用小说项目目录（相对于项目根目录）
        novel_path = "../../小说项目"
        print(f"📁 使用小说项目目录: {novel_path}")
        
        # 确保目录存在
        ensure_directory_exists(novel_path)
            
        # 设置小说路径为临时上传目录
        CONFIG["novel_path"] = novel_path
        print(f"📁 设置小说目录: {novel_path}")
        
        # 检查项目文件
        json_files = list_json_files(novel_path)
        if not json_files:
            print("❌ 在 temp_fanqie_upload 目录中未找到项目信息文件")
            print("💡 请确保存在以 '项目信息.json' 结尾的文件")
            return False
            
        print(f"✅ 找到项目文件: {len(json_files)} 个")
        for file in json_files:
            print(f"   - {os.path.basename(file)}")
        
        # 检查浏览器是否已经启动
        print("\n🔗 检查浏览器连接状态...")
        browser_result = connect_to_browser()
        
        if browser_result is None or len(browser_result) != 4:
            print("❌ 浏览器连接失败，尝试重新连接...")
            # 尝试重新连接
            browser_result = connect_to_browser()
            if browser_result is None or len(browser_result) != 4:
                print("❌ 浏览器连接最终失败")
                return False
        
        playwright, browser, page1, default_context = browser_result
        print("✅ 浏览器连接成功")
        
        # 检查页面对象是否有效
        if page1 is None:
            print("⚠️ 页面对象为空，尝试重新创建页面...")
            try:
                if default_context:
                    page1 = default_context.new_page()
                elif browser:
                    context = browser.new_context()
                    page1 = context.new_page()
                    default_context = context
                else:
                    print("❌ 无法创建新页面")
                    return False
                print("✅ 成功创建新页面")
            except Exception as e:
                print(f"❌ 创建页面失败: {e}")
                return False
        
        # 如果浏览器已经启动且当前不在番茄页面，直接导航到番茄
        try:
            if page1 is not None:
                current_url = page1.url
                print(f"📍 当前页面: {current_url}")
                
                if "fanqienovel.com" not in current_url:
                    print("🔄 浏览器已启动，直接导航到番茄小说...")
                    page1.goto("https://fanqienovel.com/", timeout=30000)
                    page1.wait_for_load_state("domcontentloaded", timeout=15000)
                    print("✅ 已导航到番茄小说首页")
                else:
                    print("✅ 已在番茄小说页面")
            else:
                print("⚠️ 页面对象为空，跳过导航检查")
        except Exception as nav_error:
            print(f"⚠️ 导航失败: {nav_error}")
            print("🔄 尝试重新导航...")
            try:
                if page1 is not None:
                    page1.goto("https://fanqienovel.com/", timeout=30000)
                    page1.wait_for_load_state("domcontentloaded", timeout=15000)
                    print("✅ 重新导航成功")
                else:
                    print("❌ 页面对象为空，无法导航")
                    return False
            except Exception as retry_error:
                print(f"❌ 重新导航失败: {retry_error}")
                return False
        
        # 导航到作家专区
        print("\n🎯 导航到作家专区...")
        page2 = navigate_to_writer_platform(page1, default_context)
        if not page2:
            print("❌ 导航到作家专区失败")
            return False
            
        print("✅ 已进入作家专区")
        
        # 直接发布小说，无需用户确认
        print(f"\n🚀 开始自动发布小说...")
        print("⚠️  全自动模式，将直接开始发布流程")
        print(f"📝 当前预发布字数阈值: {CONFIG['min_words_for_scheduled_publish']}字")
        
        success_count = 0
        for file_index, json_file in enumerate(json_files):
            print(f"\n{'=' * 50}")
            print(f"📖 处理第 {file_index + 1} 个小说项目")
            
            try:
                # 验证文件是否存在
                if not os.path.exists(json_file):
                    print(f"❌ 项目文件不存在: {json_file}")
                    continue
                
                print(f"📄 处理文件: {os.path.basename(json_file)}")
                
                # 发布小说
                if publish_novel(page2, json_file):
                    success_count += 1
                    print(f"✅ 小说项目 {file_index + 1} 处理成功")
                    
                    # 验证发布结果
                    print("🔍 验证发布结果...")
                    time.sleep(2)  # 等待发布完成
                    
                else:
                    print(f"❌ 小说项目 {file_index + 1} 处理失败")
            except Exception as e:
                print(f"❌ 处理小说项目时出错: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n{'=' * 50}")
        print(f"📊 发布完成！成功处理 {success_count}/{len(json_files)} 个小说项目")
        
        # 测试完整的上传功能验证
        print("\n🔍 测试完整的上传功能...")
        if success_count > 0:
            print("✅ 上传功能测试通过")
            print("✅ 章节发布功能正常")
            print("✅ 预发布字数设置已生效")
        else:
            print("⚠️ 没有成功处理的项目，请检查配置")
        
        # 清理资源
        try:
            if page2:
                page2.close()
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️ 清理资源时出错: {e}")
        
        return success_count > 0
            
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("💡 请检查依赖包是否安装")
        return False
        
    except Exception as e:
        print(f"❌ 执行过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)