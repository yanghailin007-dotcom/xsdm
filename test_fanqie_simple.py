"""
番茄小说自动创建测试脚本 (简化版)
"""
import sys
import os
import time
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from playwright.sync_api import sync_playwright

def test_create():
    print("="*60)
    print("番茄小说自动创建测试")
    print("="*60)
    
    test_title = "测试小说" + str(int(time.time()))[-4:]
    test_synopsis = """这是一个测试小说的简介，用于测试番茄小说的自动创建功能。
主角穿越到玄幻世界，开启传奇冒险。简介需要超过50字才能通过验证。"""
    
    print(f"\n测试书名: {test_title}")
    
    with sync_playwright() as p:
        print("\n[1/5] 连接到 Chrome (端口 9988)...")
        try:
            browser = p.chromium.connect_over_cdp("http://localhost:9988")
            print("  [OK] 连接成功")
        except Exception as e:
            print(f"  [FAIL] 连接失败: {e}")
            print("\n请确保 Chrome 已启动 (运行 start_chrome.bat)")
            return False
        
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        pages = context.pages
        page = pages[0] if pages else context.new_page()
        
        print(f"[2/5] 当前页面: {page.title()}")
        
        print("[3/5] 加载发布器...")
        try:
            from web.fanqie_uploader.novel_publisher import NovelPublisher
            publisher = NovelPublisher()
            print("  [OK] 加载成功")
        except Exception as e:
            print(f"  [FAIL] 加载失败: {e}")
            browser.close()
            return False
        
        print("[4/5] 准备测试文件...")
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建测试封面
        try:
            from PIL import Image
            img = Image.new('RGB', (600, 800), color=(139, 0, 0))
            cover_path = temp_dir / 'cover.png'
            img.save(cover_path)
            print(f"  [OK] 创建测试封面: {cover_path}")
        except Exception as e:
            print(f"  [WARN] 创建封面失败: {e}")
        
        # 执行创建
        print("\n[5/5] 开始创建新书...")
        print("-"*60)
        
        try:
            result = publisher._create_new_book(
                page=page,
                novel_title=test_title,
                formatted_synopsis=test_synopsis,
                main_character="林轩",
                novel_data={"selected_plan": {"tags": {
                    "main_category": "玄幻",
                    "themes": ["东方玄幻"],
                    "roles": ["孤儿"],
                    "plots": ["废柴流"]
                }}},
                project_dir=temp_dir
            )
            
            print("-"*60)
            
            if result:
                print("\n[OK] 测试成功！书籍创建完成")
                print(f"请在浏览器中查看新书《{test_title}》")
            else:
                print("\n[FAIL] 测试失败！")
                
        except Exception as e:
            print(f"\n[FAIL] 执行出错: {e}")
            import traceback
            print(traceback.format_exc())
            result = False
        
        # 截图
        try:
            ss_path = f"test_result_{int(time.time())}.png"
            page.screenshot(path=ss_path, full_page=True)
            print(f"\n截图已保存: {ss_path}")
        except:
            pass
        
        # 清理
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass
        
        browser.close()
        return result


if __name__ == "__main__":
    test_create()
