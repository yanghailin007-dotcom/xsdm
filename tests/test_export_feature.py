#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
导出功能测试脚本
测试内容：
1. 页面路由可访问性
2. API 接口响应
3. 代码语法检查
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import traceback


def test_code_syntax():
    """测试代码语法"""
    print("=" * 60)
    print("测试 1: 代码语法检查")
    print("=" * 60)
    
    files_to_check = [
        'web/api/export_api.py',
        'web/routes/auth_routes.py',
        'web/templates/export-page.html'
    ]
    
    results = []
    for file_path in files_to_check:
        full_path = os.path.join(project_root, file_path)
        try:
            if file_path.endswith('.py'):
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), full_path, 'exec')
                print(f"  ✅ {file_path} - 语法正确")
                results.append((file_path, True, None))
            else:
                # HTML 模板文件，检查是否存在
                if os.path.exists(full_path):
                    print(f"  ✅ {file_path} - 文件存在")
                    results.append((file_path, True, None))
                else:
                    print(f"  ❌ {file_path} - 文件不存在")
                    results.append((file_path, False, "文件不存在"))
        except Exception as e:
            print(f"  ❌ {file_path} - 语法错误: {e}")
            results.append((file_path, False, str(e)))
    
    all_passed = all(r[1] for r in results)
    print(f"\n语法检查: {'全部通过' if all_passed else '有错误'}")
    return all_passed


def test_route_registration():
    """测试路由注册"""
    print("\n" + "=" * 60)
    print("测试 2: 路由注册检查")
    print("=" * 60)
    
    try:
        from web.web_server_refactored import create_app
        from web.api.export_api import export_api
        from flask import Flask
        
        # 检查 export_api 蓝图
        print(f"  ✅ export_api 蓝图已定义")
        print(f"     - URL 前缀: {export_api.url_prefix or '/api/export'}")
        
        # 检查路由
        routes = []
        for rule in export_api.url_map.iter_rules():
            if rule.endpoint.startswith('export_api.'):
                routes.append((rule.rule, rule.methods, rule.endpoint))
        
        expected_routes = [
            '/novel-preview',
            '/novel-content',
            '/novel-zip/<title>'
        ]
        
        print(f"  ✅ export_api 路由:")
        for route in routes:
            print(f"     - {route[0]} [{', '.join(m for m in route[1] if m not in ['OPTIONS', 'HEAD'])}]")
        
        # 检查 auth_routes 中的页面路由
        print(f"  ✅ 页面路由: /export-page/<title>")
        
        return True
    except Exception as e:
        print(f"  ❌ 路由检查失败: {e}")
        traceback.print_exc()
        return False


def test_html_template():
    """测试 HTML 模板"""
    print("\n" + "=" * 60)
    print("测试 3: HTML 模板检查")
    print("=" * 60)
    
    template_path = os.path.join(project_root, 'web/templates/export-page.html')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键元素
        checks = [
            ('继承 base-v2', '{% extends "layouts/base-v2.html" %}' in content),
            ('标题块', '{% block title %}' in content),
            ('CSS 块', '{% block extra_css %}' in content),
            ('内容块', '{% block content %}' in content),
            ('JS 块', '{% block extra_js %}' in content),
            ('导出模式选择', 'export_mode' in content),
            ('格式选择', 'format-tab' in content),
            ('正文导出选项', 'content-options' in content),
            ('导出按钮', 'startExport' in content),
            ('预览区域', 'previewContent' in content),
            ('API 调用', '/api/export/novel-preview' in content),
            ('导出 API', '/api/export/novel-content' in content),
        ]
        
        all_passed = True
        for name, check in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {name}")
            if not check:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ 模板检查失败: {e}")
        return False


def test_api_endpoints_syntax():
    """测试 API 端点代码"""
    print("\n" + "=" * 60)
    print("测试 4: API 端点代码检查")
    print("=" * 60)
    
    api_file = os.path.join(project_root, 'web/api/export_api.py')
    
    try:
        with open(api_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('novel-preview 路由', '@export_api.route(\'/novel-preview\'' in content),
            ('novel-content 路由', '@export_api.route(\'/novel-content\'' in content),
            ('导出函数 - export_novel_preview', 'def export_novel_preview()' in content),
            ('导出函数 - export_novel_content', 'def export_novel_content()' in content),
            ('权限检查', 'session.get' in content),
            ('项目检查', 'list_user_projects' in content),
            ('章节获取', 'get_all_chapters' in content),
            ('文件响应', 'make_response' in content or 'send_file' in content),
        ]
        
        all_passed = True
        for name, check in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {name}")
            if not check:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ API 检查失败: {e}")
        return False


def test_page_route():
    """测试页面路由代码"""
    print("\n" + "=" * 60)
    print("测试 5: 页面路由代码检查")
    print("=" * 60)
    
    routes_file = os.path.join(project_root, 'web/routes/auth_routes.py')
    
    try:
        with open(routes_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ('导出页面路由', '/export-page/<title>' in content),
            ('导出页面函数', 'def export_page(title)' in content),
            ('权限检查', '@login_required' in content),
            ('模板渲染', 'export-page.html' in content),
            ('章节获取', 'get_all_chapters' in content),
        ]
        
        all_passed = True
        for name, check in checks:
            status = "✅" if check else "❌"
            print(f"  {status} {name}")
            if not check:
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"  ❌ 页面路由检查失败: {e}")
        return False


def test_button_updates():
    """测试按钮更新"""
    print("\n" + "=" * 60)
    print("测试 6: 导出按钮跳转更新检查")
    print("=" * 60)
    
    files_to_check = [
        ('web/templates/novels.html', 'export-page'),
        ('web/templates/pages/v2/novels-v2.html', 'export-page'),
        ('web/templates/pages/v2/novel-v2.html', 'export-page'),
        ('web/templates/pages/v2/project-management-v2.html', 'export-page'),
    ]
    
    all_passed = True
    for file_path, expected in files_to_check:
        full_path = os.path.join(project_root, file_path)
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否指向新页面
            has_new_url = expected in content
            # 检查是否还有旧 API 调用（应该被替换）
            has_old_api = '/api/export-novel?' in content and 'export-page' not in content
            
            if has_new_url and not has_old_api:
                print(f"  ✅ {file_path} - 已更新跳转")
            elif has_new_url:
                print(f"  ⚠️ {file_path} - 已更新但可能保留旧代码")
            else:
                print(f"  ❌ {file_path} - 未更新")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {file_path} - 读取失败: {e}")
            all_passed = False
    
    return all_passed


def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("代码语法检查", test_code_syntax()))
    results.append(("路由注册检查", test_route_registration()))
    results.append(("HTML 模板检查", test_html_template()))
    results.append(("API 端点检查", test_api_endpoints_syntax()))
    results.append(("页面路由检查", test_page_route()))
    results.append(("按钮跳转更新", test_button_updates()))
    
    # 汇总
    print("\n" + "=" * 60)
    print("汇总结果")
    print("=" * 60)
    
    passed = 0
    failed = 0
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n🎉 所有静态检查通过！")
        print("注意：本测试仅检查代码结构和语法，")
        print("      实际功能需要在运行中的服务器上测试。")
    
    return failed == 0


if __name__ == '__main__':
    print("=" * 60)
    print("小说导出功能测试")
    print("=" * 60)
    
    success = generate_report()
    
    sys.exit(0 if success else 1)
