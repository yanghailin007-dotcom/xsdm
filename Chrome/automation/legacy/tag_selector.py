"""
番茄小说自动发布系统 - 标签选择模块
处理小说标签的选择和验证
"""

import time
from typing import Dict, Any, List

from .config import PLATFORM_CATEGORIES
from .utils import safe_click, calculate_similarity


def validate_tags_with_platform(tags_info):
    """
    验证标签是否在番茄平台的实际分类中，如果不匹配则使用最接近的有效标签
    """
    validated_tags = {}
    
    # 验证目标受众
    target_audience = tags_info.get("target_audience", "男频")
    validated_tags["target_audience"] = target_audience if target_audience in ["男频", "女频"] else "男频"
    
    # 验证主分类
    main_category = tags_info.get("main_category", "传统玄幻")
    available_categories = PLATFORM_CATEGORIES.get(target_audience, {}).get("main_category", [])
    
    if main_category in available_categories:
        validated_tags["main_category"] = main_category
    else:
        # 查找最接近的匹配
        best_match = None
        best_match_score = 0
        for category in available_categories:
            # 计算相似度
            similarity = calculate_similarity(main_category, category)
            if similarity > best_match_score:
                best_match_score = similarity
                best_match = category
        
        if best_match and best_match_score > 0.3:  # 设置最低相似度阈值
            validated_tags["main_category"] = best_match
            print(f"主分类 '{main_category}' 不在平台分类中，使用最接近的匹配: {best_match} (相似度: {best_match_score:.2f})")
        else:
            print(f"无法找到合适的主分类匹配: {main_category}，使用默认分类")
            validated_tags["main_category"] = "东方玄幻" if target_audience == "男频" else "古代言情"
    
    # 验证主题标签（最多选择2个）
    original_themes = tags_info.get("themes", [])
    validated_themes = []
    available_themes = PLATFORM_CATEGORIES.get(target_audience, {}).get("themes", [])
    
    for theme in original_themes[:2]:  # 最多选择2个主题
        validated_theme = validate_single_tag(theme, available_themes, f"主题标签")
        if validated_theme:
            validated_themes.append(validated_theme)
    
    # 如果没有有效的主题，添加默认主题
    if not validated_themes:
        default_themes = ["玄幻", "都市"] if target_audience == "男频" else ["甜宠", "言情"]
        for default_theme in default_themes[:1]:  # 至少添加一个默认主题
            if default_theme in available_themes:
                validated_themes.append(default_theme)
                print(f"添加默认主题标签: {default_theme}")
                break
    
    validated_tags["themes"] = validated_themes
    
    # 验证角色标签（最多选择2个）
    original_roles = tags_info.get("roles", [])
    validated_roles = []
    available_roles = PLATFORM_CATEGORIES.get(target_audience, {}).get("roles", [])
    
    for role in original_roles[:2]:  # 最多选择2个角色
        validated_role = validate_single_tag(role, available_roles, f"角色标签")
        if validated_role:
            validated_roles.append(validated_role)
    
    # 如果没有有效的角色，添加默认角色
    if not validated_roles:
        default_roles = ["天才", "大佬"] if target_audience == "男频" else ["总裁", "学霸"]
        for default_role in default_roles[:1]:  # 至少添加一个默认角色
            if default_role in available_roles:
                validated_roles.append(default_role)
                print(f"添加默认角色标签: {default_role}")
                break
    
    validated_tags["roles"] = validated_roles
    
    # 验证情节标签（最多选择2个）
    original_plots = tags_info.get("plots", [])
    validated_plots = []
    available_plots = PLATFORM_CATEGORIES.get(target_audience, {}).get("plots", [])
    
    for plot in original_plots[:2]:  # 最多选择2个情节
        validated_plot = validate_single_tag(plot, available_plots, f"情节标签")
        if validated_plot:
            validated_plots.append(validated_plot)
    
    # 如果没有有效的情节，添加默认情节
    if not validated_plots:
        default_plots = ["系统", "重生"] if target_audience == "男频" else ["穿越", "重生"]
        for default_plot in default_plots[:1]:  # 至少添加一个默认情节
            if default_plot in available_plots:
                validated_plots.append(default_plot)
                print(f"添加默认情节标签: {default_plot}")
                break
    
    validated_tags["plots"] = validated_plots
    
    return validated_tags


def validate_single_tag(tag, available_tags, tag_type):
    """
    验证单个标签是否在可用标签列表中，如果不匹配则返回最接近的匹配
    """
    if tag in available_tags:
        return tag
    
    # 如果直接匹配失败，查找最接近的匹配
    best_match = None
    best_match_score = 0
    
    for available_tag in available_tags:
        # 计算相似度
        similarity = calculate_similarity(tag, available_tag)
        if similarity > best_match_score and similarity > 0.6:  # 相似度阈值
            best_match_score = similarity
            best_match = available_tag
    
    if best_match:
        print(f"⚠ {tag_type}标签 '{tag}' 不在平台分类中，使用最接近的匹配: {best_match}")
        return best_match
    else:
        print(f"无法找到合适的{tag_type}标签匹配: {tag}")
        return None  # 返回None表示无法找到匹配


def select_novel_tags_interactive(page, novel_data):
    """
    交互式选择小说标签 - 基于当前弹窗结构，支持动态JSON结构，并匹配番茄平台实际分类
    """
    try:
        print("开始选择小说标签...")
        
        # 等待弹窗完全加载
        time.sleep(2)
        
        # 动态获取标签信息 - 支持多种JSON结构
        tags_info = {}
        
        # 方法1: 尝试从 project_info.tags 获取（当前结构）
        if "project_info" in novel_data and "tags" in novel_data["project_info"]:
            tags_info = novel_data["project_info"]["tags"]
            print("✓ 从 project_info.tags 获取标签信息")
        
        # 方法2: 尝试从 novel_info.tags 获取（兼容结构）
        elif "novel_info" in novel_data and "tags" in novel_data["novel_info"]:
            tags_info = novel_data["novel_info"]["tags"]
            print("✓ 从 novel_info.tags 获取标签信息")
        
        # 方法3: 尝试从 novel_info.selected_plan.tags 获取（旧结构）
        elif "novel_info" in novel_data and "selected_plan" in novel_data["novel_info"] and "tags" in novel_data["novel_info"]["selected_plan"]:
            tags_info = novel_data["novel_info"]["selected_plan"]["tags"]
            print("✓ 从 novel_info.selected_plan.tags 获取标签信息")
        
        else:
            print("⚠ 未找到标准标签信息，使用默认标签")
            # 使用默认标签作为备选
            tags_info = {
                "target_audience": "男频",
                "main_category": "东方玄幻",
                "themes": ["种田流", "凡人流"],
                "roles": ["谨慎型主角", "稳健发育"],
                "plots": ["凡人流", "种田"]
            }
        
        print(f"原始标签信息: {tags_info}")
        
        # 验证标签是否在番茄平台的实际分类中
        valid_tags_info = validate_tags_with_platform(tags_info)
        
        print(f"验证后的标签信息:")
        print(f"- 目标受众: {valid_tags_info['target_audience']}")
        print(f"- 主分类: {valid_tags_info['main_category']}")
        print(f"- 主题: {valid_tags_info['themes']}")
        print(f"- 角色: {valid_tags_info['roles']}")
        print(f"- 情节: {valid_tags_info['plots']}")
        
        # 1. 选择主分类
        print("\n=== 选择主分类 ===")
        if select_category_tag(page, "主分类", valid_tags_info["main_category"]):
            print(f"✓ 主分类选择成功: {valid_tags_info['main_category']}")
        else:
            print(f"⚠ 主分类选择失败: {valid_tags_info['main_category']}")
        
        # 2. 选择主题（最多2个）
        print("\n=== 选择主题 ===")
        theme_selected = 0
        for theme in valid_tags_info["themes"][:2]:  # 最多选择2个主题
            if select_category_tag(page, "主题", theme):
                theme_selected += 1
                print(f"✓ 主题选择成功: {theme}")
                time.sleep(0.5)
            else:
                print(f"⚠ 主题选择失败: {theme}")
        
        print(f"主题选择完成: {theme_selected}/2 个主题")
        
        # 3. 选择角色（最多2个）
        print("\n=== 选择角色 ===")
        role_selected = 0
        for role in valid_tags_info["roles"][:2]:  # 最多选择2个角色
            if select_category_tag(page, "角色", role):
                role_selected += 1
                print(f"✓ 角色选择成功: {role}")
                time.sleep(0.5)
            else:
                print(f"⚠ 角色选择失败: {role}")
        
        print(f"角色选择完成: {role_selected}/2 个角色")
        
        # 4. 选择情节（最多2个）
        print("\n=== 选择情节 ===")
        plot_selected = 0
        for plot in valid_tags_info["plots"][:2]:  # 最多选择2个情节
            if select_category_tag(page, "情节", plot):
                plot_selected += 1
                print(f"✓ 情节选择成功: {plot}")
                time.sleep(0.5)
            else:
                print(f"⚠ 情节选择失败: {plot}")
        
        print(f"情节选择完成: {plot_selected}/2 个情节")
        
        # 5. 确认选择
        print("\n=== 确认标签选择 ===")
        return confirm_tag_selection(page)
        
    except Exception as e:
        print(f"标签选择过程中出错: {e}")
        return False


def select_category_tag(page, tab_name, target_text):
    """
    在指定标签页中选择目标分类
    """
    try:
        # 1. 点击标签页
        tab_selectors = [
            f'//span[text()="{tab_name}"]',
            f'//div[contains(@class, "arco-tabs-tab")]//span[text()="{tab_name}"]',
        ]
        
        tab_clicked = False
        for selector in tab_selectors:
            try:
                tab_element = page.locator(f'xpath={selector}')
                if tab_element.count() > 0:
                    tab_element.first.click()
                    time.sleep(1)  # 等待标签页切换
                    tab_clicked = True
                    print(f"✓ 成功点击标签页: {tab_name}")
                    break
            except Exception as e:
                continue
        
        if not tab_clicked:
            print(f"❌ 无法点击标签页: {tab_name}")
            return False
        
        # 2. 查找并点击目标标签
        target_selectors = [
            f'//div[contains(@class, "category-choose-item")]//div[contains(text(), "{target_text}")]',
            f'//div[contains(@class, "category-choose-item-title") and text()="{target_text}"]',
            f'//*[contains(text(), "{target_text}")]',
        ]
        
        # 首先尝试不滚动查找
        for selector in target_selectors:
            try:
                target_elements = page.locator(f'xpath={selector}')
                if target_elements.count() > 0:
                    for i in range(target_elements.count()):
                        element = target_elements.nth(i)
                        if element.is_visible():
                            element_text = element.text_content().strip()
                            if target_text in element_text:
                                print(f"找到目标标签: {element_text}")
                                element.click()
                                time.sleep(0.5)
                                return True
            except Exception as e:
                continue
        
        # 3. 如果没找到，尝试滚动查找
        print(f"未找到目标标签 '{target_text}'，开始滚动查找...")
        
        # 定位滚动容器
        scroll_container = page.locator('.category-choose-scroll-parent').first
        if scroll_container.count() == 0:
            scroll_container = page.locator('.arco-tabs-content-item-active').first
        
        # 滚动查找
        for scroll_attempt in range(20):  # 最多滚动20次
            try:
                # 再次尝试查找
                for selector in target_selectors:
                    try:
                        target_elements = page.locator(f'xpath={selector}')
                        if target_elements.count() > 0:
                            for i in range(target_elements.count()):
                                element = target_elements.nth(i)
                                if element.is_visible():
                                    element_text = element.text_content().strip()
                                    if target_text in element_text:
                                        print(f"滚动找到目标标签: {element_text}")
                                        element.click()
                                        time.sleep(0.5)
                                        return True
                    except:
                        continue
                
                # 滚动一小段距离
                page.evaluate('window.scrollBy(0, 200)')
                time.sleep(0.3)
                
            except Exception as e:
                break
        
        print(f"❌ 未找到目标标签: {target_text}")
        return False
        
    except Exception as e:
        print(f"选择标签时出错: {e}")
        return False


def confirm_tag_selection(page):
    """
    确认标签选择 - 修复版本
    """
    try:
        print("尝试确认标签选择...")
        
        # 等待一下确保选择完成
        time.sleep(1)
        
        # 使用更精确的确认按钮选择器，基于你提供的HTML结构
        confirm_selectors = [
            # 基于你提供的HTML结构的精确选择器
            'div.arco-modal-footer button.arco-btn-primary:has-text("确认")',
            'div.arco-modal-footer button.arco-btn-primary span:has-text("确认")',
            '//div[@class="arco-modal-footer"]//button[@class="arco-btn arco-btn-primary"]//span[text()="确认"]',
            '//div[@class="arco-modal-footer"]//button[@class="arco-btn arco-btn-primary" and contains(text(), "确认")]',
            '//div[@class="arco-modal-footer"]//button[contains(@class, "arco-btn-primary") and .//span[text()="确认"]]',
            # 备用选择器
            '//button[contains(@class, "arco-btn-primary")]//span[text()="确认"]',
            '//button[contains(@class, "arco-btn-primary") and text()="确认"]',
            'button:has-text("确认")',
            'button:has(span:text("确认"))',
        ]
        
        for attempt in range(8):  # 增加重试次数
            print(f"尝试点击确认按钮 (第 {attempt + 1} 次)...")
            
            # 每次重试前等待一下，让页面有时间响应
            if attempt > 0:
                time.sleep(1.5)
            
            for selector_idx, selector in enumerate(confirm_selectors):
                try:
                    if selector.startswith('//'):
                        button_element = page.locator(f'xpath={selector}')
                    else:
                        button_element = page.locator(selector)
                    
                    if button_element.count() > 0:
                        button = button_element.first
                        
                        # 检查按钮是否可见和可点击
                        if button.is_visible() and button.is_enabled():
                            print(f"找到确认按钮 (选择器 {selector_idx + 1}), 尝试点击...")
                            
                            # 滚动到按钮位置
                            button.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            
                            # 尝试多种点击方式
                            click_success = False
                            
                            # 方法1: 普通点击
                            try:
                                button.click(timeout=5000)
                                print("✓ 普通点击成功")
                                click_success = True
                            except Exception as click_error:
                                print(f"普通点击失败: {click_error}")
                                
                                # 方法2: 强制点击
                                try:
                                    button.click(force=True, timeout=3000)
                                    print("✓ 强制点击成功")
                                    click_success = True
                                except Exception as force_error:
                                    print(f"强制点击失败: {force_error}")
                                    
                                    # 方法3: JavaScript点击
                                    try:
                                        button.evaluate('(element) => element.click()')
                                        print("✓ JavaScript点击成功")
                                        click_success = True
                                    except Exception as js_error:
                                        print(f"JavaScript点击失败: {js_error}")
                            
                            if click_success:
                                print("✓ 确认按钮点击成功")
                                time.sleep(2)  # 等待弹窗关闭
                                return True
                            else:
                                print(f"所有点击方式都失败")
                                continue
                        else:
                            print(f"按钮不可见或不可用 (选择器 {selector_idx + 1})")
                            continue
                    else:
                        print(f"未找到按钮元素 (选择器 {selector_idx + 1})")
                        continue
                
                except Exception as e:
                    print(f"选择器 {selector_idx + 1} 失败: {e}")
                    continue
            
            # 如果所有选择器都失败，尝试滚动页面后重试
            if attempt < 7:
                print(f"第 {attempt + 1} 次尝试失败，尝试滚动页面后重试...")
                try:
                    # 滚动到页面底部
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(1)
                    
                    # 再滚动回顶部
                    page.evaluate('window.scrollTo(0, 0)')
                    time.sleep(0.5)
                except:
                    pass
        
        print("❌ 所有尝试都无法点击确认按钮")
        
        # 最后的备用方案：尝试按ESC键关闭弹窗
        try:
            page.keyboard.press('Escape')
            print("尝试按ESC键关闭弹窗")
            time.sleep(1)
            return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"确认标签选择时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def scroll_and_click_enhanced(page, tab_name, target_text, max_scrolls=30, scroll_step=300):
    """
    增强版：在分类选择模态框中查找目标文本并点击
    使用更通用的选择器来适应网页结构变化
    """
    try:
        print(f"🔍 开始在'{tab_name}'标签页中查找: '{target_text}'")
        
        # 1. 首先点击对应的标签页 - 使用多种选择器
        tab_selectors = [
            f".arco-tabs-header-title:has-text('{tab_name}')",
            f"//span[contains(text(), '{tab_name}')]",
            f"[class*='tabs'] span:has-text('{tab_name}')",
            f"div[class*='tab'] span:has-text('{tab_name}')"
        ]
        
        tab_clicked = False
        for selector in tab_selectors:
            try:
                if selector.startswith('//'):
                    tab_element = page.locator(f'xpath={selector}')
                else:
                    tab_element = page.locator(selector)
                
                if tab_element.count() > 0:
                    tab_element.first.click()
                    time.sleep(0.8)  # 等待标签页切换动画
                    tab_clicked = True
                    print(f"✅ 成功点击标签页: {tab_name}")
                    break
            except Exception as e:
                continue
        
        if not tab_clicked:
            print(f"❌ 无法点击标签页: {tab_name}")
            return False
        
        # 2. 定位滚动容器 - 使用多种选择器
        scroll_selectors = [
            ".arco-tabs-content-item-active .category-choose-scroll-parent",
            ".arco-tabs-content-item-active [class*='scroll']",
            ".arco-tabs-content-item-active div[class*='content']",
            "[class*='tabs-content'] [class*='scroll']",
            "[class*='category'] [class*='scroll']",
            ".arco-modal-body [class*='scroll']"
        ]
        
        scrollable = None
        for selector in scroll_selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    scrollable = element.first
                    print(f"✅ 找到滚动容器: {selector}")
                    break
            except Exception as e:
                continue
        
        if scrollable is None:
            print(f"❌ 未找到滚动容器，尝试全局搜索")
            # 如果找不到特定的滚动容器，尝试在整个模态框中搜索
            scrollable = page.locator(".arco-modal-body").first
            if scrollable.count() == 0:
                scrollable = page.locator("body").first
        
        # 3. 将鼠标悬停在滚动区域上
        try:
            scrollable.hover(timeout=3000)
        except:
            print(f"⚠️ 无法悬停在滚动区域，继续尝试")
        
        # 4. 循环查找和滚动 - 使用多种目标选择器
        target_selectors = [
            f".category-choose-item:has-text('{target_text}')",
            f"[class*='category-item']:has-text('{target_text}')",
            f"[class*='choose-item']:has-text('{target_text}')",
            f"div:has-text('{target_text}')",
            f"span:has-text('{target_text}')",
            f"//*[contains(text(), '{target_text}')]"
        ]
        
        for i in range(max_scrolls):
            # 尝试多种目标选择器
            for target_selector in target_selectors:
                try:
                    if target_selector.startswith('//'):
                        target = scrollable.locator(f'xpath={target_selector}')
                    else:
                        target = scrollable.locator(target_selector)
                    
                    if target.count() > 0:
                        # 检查元素是否可见和可点击
                        for j in range(target.count()):
                            element = target.nth(j)
                            if element.is_visible() and element.is_enabled():
                                element_text = element.text_content().strip()
                                if target_text in element_text:
                                    print(f"✅ 在'{tab_name}'标签页找到目标: {element_text}")
                                    # 滚动到元素并点击
                                    element.scroll_into_view_if_needed()
                                    time.sleep(0.3)
                                    element.click()
                                    time.sleep(0.5)  # 等待点击响应
                                    return True
                except Exception as e:
                    continue
            
            # 使用鼠标滚轮滚动
            try:
                page.mouse.wheel(0, scroll_step)
                time.sleep(0.4)
            except Exception as e:
                # 如果鼠标滚轮失败，尝试JavaScript滚动
                try:
                    page.evaluate("() => window.scrollBy(0, 300)")
                    time.sleep(0.4)
                except:
                    pass
            
            # 检查是否到达底部
            if i % 5 == 0:
                try:
                    scroll_height = page.evaluate("() => document.body.scrollHeight")
                    current_scroll = page.evaluate("() => window.pageYOffset")
                    viewport_height = page.evaluate("() => window.innerHeight")
                    
                    if current_scroll + viewport_height >= scroll_height - 100:
                        print(f"🟡 已滚动到底部，停止滚动")
                        break
                except:
                    pass

        print(f"🟡 在'{tab_name}'标签页滚动{max_scrolls}次后未找到: '{target_text}'")
        return False

    except Exception as e:
        print(f"✗ 在'{tab_name}'标签页操作'{target_text}'时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False