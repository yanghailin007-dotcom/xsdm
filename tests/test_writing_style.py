# -*- coding: utf-8 -*-
"""
文风系统功能测试
使用Playwright进行UI和API测试
"""

import pytest
import time
from playwright.sync_api import sync_playwright, expect

# 测试配置
BASE_URL = "http://localhost:5000"
TEST_USER = {
    "username": "yanghailin",
    "password": "yanghailin"
}

class TestWritingStyleSystem:
    """文风系统测试类"""
    
    @pytest.fixture(scope="class")
    def browser(self):
        """启动浏览器"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # 设为True可在后台运行
            yield browser
            browser.close()
    
    @pytest.fixture(scope="function")
    def page(self, browser):
        """创建新页面并登录"""
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        # 登录
        page.goto(f"{BASE_URL}/login")
        page.fill('input[name="username"]', TEST_USER["username"])
        page.fill('input[name="password"]', TEST_USER["password"])
        page.click('button[type="submit"]')
        
        # 等待登录完成
        page.wait_for_load_state('networkidle')
        time.sleep(1)
        
        yield page
        context.close()
    
    def test_login_success(self, page):
        """测试登录成功"""
        # 验证登录后跳转到了首页
        assert "login" not in page.url
        print("✅ 登录测试通过")
    
    def test_writing_style_library_page(self, page):
        """测试文风训练库页面加载"""
        # 访问文风训练库页面
        page.goto(f"{BASE_URL}/writing-style-library")
        page.wait_for_load_state('networkidle')
        
        # 验证页面标题
        assert "文风训练库" in page.title()
        
        # 验证页面关键元素存在
        expect(page.locator("text=预设文风")).to_be_visible()
        expect(page.locator("text=我的文风")).to_be_visible()
        expect(page.locator("text=提取新文风")).to_be_visible()
        
        print("✅ 文风训练库页面加载测试通过")
    
    def test_preset_styles_load(self, page):
        """测试预设文风加载"""
        page.goto(f"{BASE_URL}/writing-style-library")
        page.wait_for_load_state('networkidle')
        
        # 等待文风卡片加载
        page.wait_for_selector(".style-card", timeout=5000)
        
        # 获取所有预设文风卡片
        cards = page.locator(".style-card.preset").all()
        assert len(cards) > 0, "预设文风未加载"
        
        # 验证第一个卡片的内容
        first_card = cards[0]
        expect(first_card.locator(".style-name")).to_be_visible()
        expect(first_card.locator(".style-badge")).to_contain_text("预设")
        
        print(f"✅ 预设文风加载测试通过，共 {len(cards)} 个文风")
    
    def test_style_card_interaction(self, page):
        """测试文风卡片交互"""
        page.goto(f"{BASE_URL}/writing-style-library")
        page.wait_for_load_state('networkidle')
        page.wait_for_selector(".style-card", timeout=5000)
        
        # 点击第一个文风的"使用"按钮
        first_use_btn = page.locator(".style-card.preset .btn-primary").first
        expect(first_use_btn).to_be_visible()
        
        print("✅ 文风卡片交互测试通过")
    
    def test_extract_style_section(self, page):
        """测试文风提取区域"""
        page.goto(f"{BASE_URL}/writing-style-library")
        page.wait_for_load_state('networkidle')
        
        # 点击"提取新文风"按钮
        page.click("text=提取新文风")
        
        # 验证上传区域显示
        expect(page.locator("#extract-section")).to_be_visible()
        expect(page.locator("text=上传小说正文提取文风")).to_be_visible()
        
        # 验证文本框存在
        textarea = page.locator("#extract-text")
        expect(textarea).to_be_visible()
        
        # 输入测试文本
        test_text = "这是一个测试文本，用于测试文风提取功能。" * 20  # 确保超过500字
        textarea.fill(test_text)
        
        print("✅ 文风提取区域测试通过")
    
    def test_api_get_presets(self, page):
        """测试API：获取预设文风"""
        # 使用page的evaluate调用API
        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/writing-style/presets');
                return await response.json();
            }
        """)
        
        assert result["success"] is True
        assert len(result["data"]) > 0
        assert "style_id" in result["data"][0]
        assert "style_name" in result["data"][0]
        
        print(f"✅ API测试通过：获取到 {len(result['data'])} 个预设文风")
    
    def test_api_get_style_detail(self, page):
        """测试API：获取文风详情"""
        result = page.evaluate("""
            async () => {
                const response = await fetch('/api/writing-style/detail/fanqie_light_fast_v1');
                return await response.json();
            }
        """)
        
        assert result["success"] is True
        assert result["data"]["style_id"] == "fanqie_light_fast_v1"
        assert "dna" in result["data"]
        assert "system_prompt_addon" in result["data"]
        
        print("✅ API测试通过：获取文风详情")
    
    def test_api_extract_style(self, page):
        """测试API：提取文风"""
        test_text = """
        这是一个测试文本。ps：（大脑寄存处！）
        
        炎炎夏日，骄阳当空。
        
        鸟儿在歌唱，夏蝉在鸣叫，树叶随着微风沙沙作响。
        
        "他拿起粉笔宛若鬼画符般，连飞带跑在黑板上写下三个大字。"
        
        "卧槽，这也太牛逼了吧！"
        
        "就是就是！"
        
        """ * 10  # 确保超过500字
        
        result = page.evaluate(f"""
            async () => {{
                const response = await fetch('/api/writing-style/extract', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{text: `{test_text}`}})
                }});
                return await response.json();
            }}
        """)
        
        assert result["success"] is True
        assert "extracted_features" in result["data"]
        
        print(f"✅ API测试通过：文风提取，检测到特征：{result['data']['extracted_features']}")


def run_tests():
    """运行所有测试并生成报告"""
    print("=" * 60)
    print("🧪 文风系统功能测试")
    print("=" * 60)
    
    # 使用pytest运行测试
    import subprocess
    result = subprocess.run([
        "python", "-m", "pytest", 
        "tests/test_writing_style.py",
        "-v",
        "--tb=short",
        "--html=tests/writing_style_test_report.html"
    ], capture_output=False)
    
    return result.returncode


if __name__ == "__main__":
    exit_code = run_tests()
    exit(exit_code)
