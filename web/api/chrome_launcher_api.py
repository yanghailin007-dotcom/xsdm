#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome 启动器 API
用于检测本地 Chrome 状态和提供下载
"""

import os
import json
import requests
import sys
from flask import Blueprint, jsonify, send_file, current_app
from pathlib import Path

chrome_api = Blueprint('chrome_api', __name__)

# Chrome 调试端口
DEBUG_PORT = 9988


def get_chrome_search_paths() -> list:
    """获取 Chrome 搜索路径列表"""
    paths = []
    
    # 1. 项目内置路径
    project_dir = Path(current_app.root_path).parent / 'tools' / 'chrome_launcher'
    paths.append({
        'name': '项目目录',
        'launcher_dir': project_dir,
        'chrome_dir': project_dir / 'chrome'
    })
    
    # 2. 用户目录下的大文娱文件夹（推荐用户解压到这里）
    user_home = Path.home()
    user_dir = user_home / '大文娱' / 'chrome_launcher'
    paths.append({
        'name': '用户目录',
        'launcher_dir': user_dir,
        'chrome_dir': user_dir / 'chrome'
    })
    
    # 3. 下载目录（常见下载位置）
    downloads = user_home / 'Downloads'
    if downloads.exists():
        # 匹配 chrome-launcher 开头的文件夹
        for item in downloads.iterdir():
            if item.is_dir() and 'chrome' in item.name.lower() and 'launcher' in item.name.lower():
                paths.append({
                    'name': '下载目录',
                    'launcher_dir': item,
                    'chrome_dir': item / 'chrome'
                })
    
    # 4. 桌面
    desktop = user_home / 'Desktop'
    if desktop.exists():
        for item in desktop.iterdir():
            if item.is_dir() and 'chrome' in item.name.lower() and 'launcher' in item.name.lower():
                paths.append({
                    'name': '桌面',
                    'launcher_dir': item,
                    'chrome_dir': item / 'chrome'
                })
    
    return paths


def find_chrome_in_dir(chrome_dir: Path) -> tuple:
    """在指定目录查找 Chrome 可执行文件和启动脚本"""
    platform = sys.platform
    chrome_exe = None
    start_script = None
    
    # 检查 Chrome 可执行文件
    if platform == 'win32':
        possible_paths = [
            chrome_dir / 'chrome-win64' / 'chrome.exe',
            chrome_dir / 'chrome' / 'chrome.exe',
            chrome_dir / 'chrome.exe',
        ]
        script_names = ['一键启动.bat', 'start_browser.bat', 'start.bat']
    elif platform == 'darwin':
        possible_paths = [
            chrome_dir / 'chrome-mac-x64' / 'Google Chrome for Testing.app' / 'Contents' / 'MacOS' / 'Google Chrome for Testing',
            chrome_dir / 'Google Chrome.app' / 'Contents' / 'MacOS' / 'Google Chrome',
        ]
        script_names = ['start_chrome.sh', 'start_browser.sh', 'start.sh']
    else:  # linux
        possible_paths = [
            chrome_dir / 'chrome-linux64' / 'chrome',
            chrome_dir / 'chrome' / 'chrome',
            chrome_dir / 'chrome',
        ]
        script_names = ['start_chrome.sh', 'start_browser.sh', 'start.sh']
    
    for path in possible_paths:
        if path.exists():
            chrome_exe = path
            break
    
    # 检查启动脚本（在 launcher_dir 中）
    launcher_dir = chrome_dir.parent
    for script_name in script_names:
        script_path = launcher_dir / script_name
        if script_path.exists():
            start_script = script_path
            break
    
    return chrome_exe, start_script


def check_chrome_installed() -> dict:
    """检查 Chrome 是否已安装（在多个可能的位置）"""
    search_paths = get_chrome_search_paths()
    
    for location in search_paths:
        chrome_dir = location['chrome_dir']
        launcher_dir = location['launcher_dir']
        
        if chrome_dir.exists():
            chrome_exe, start_script = find_chrome_in_dir(chrome_dir)
            
            if chrome_exe:
                return {
                    'installed': True,
                    'chrome_path': str(chrome_exe),
                    'start_script': str(start_script) if start_script else None,
                    'launcher_dir': str(launcher_dir),
                    'location_name': location['name'],
                    'script_name': '一键启动.bat' if sys.platform == 'win32' else 'start_chrome.sh',
                    'all_search_paths': [
                        {'name': p['name'], 'path': str(p['launcher_dir']), 'exists': (p['chrome_dir']).exists()}
                        for p in search_paths
                    ]
                }
    
    # 未找到，返回所有搜索过的路径供参考
    return {
        'installed': False,
        'chrome_path': None,
        'start_script': None,
        'launcher_dir': None,
        'location_name': None,
        'script_name': '一键启动.bat' if sys.platform == 'win32' else 'start_chrome.sh',
        'all_search_paths': [
            {'name': p['name'], 'path': str(p['launcher_dir']), 'exists': (p['chrome_dir']).exists()}
            for p in search_paths
        ],
        'suggested_locations': [
            str(Path.home() / '大文娱' / 'chrome_launcher'),
            str(Path.home() / 'Downloads' / 'chrome-launcher'),
            str(Path(current_app.root_path).parent / 'tools' / 'chrome_launcher')
        ]
    }


def check_chrome_status() -> dict:
    """检查本地 Chrome 状态"""
    try:
        response = requests.get(
            f'http://127.0.0.1:{DEBUG_PORT}/json/version',
            timeout=2
        )
        if response.status_code == 200:
            data = response.json()
            return {
                'running': True,
                'version': data.get('Browser', 'Unknown'),
                'protocol': data.get('Protocol-Version', 'Unknown'),
                'webSocketDebuggerUrl': data.get('webSocketDebuggerUrl', None)
            }
    except Exception as e:
        pass
    
    # Chrome 未运行，检查是否已安装
    install_info = check_chrome_installed()
    
    return {
        'running': False,
        'version': None,
        'error': 'Chrome not running or debug port not accessible',
        'installed': install_info['installed'],
        'install_info': install_info
    }


@chrome_api.route('/api/chrome/status', methods=['GET'])
def get_chrome_status():
    """获取 Chrome 运行状态"""
    status = check_chrome_status()
    return jsonify(status)


@chrome_api.route('/api/chrome/launcher/download', methods=['GET'])
def download_launcher():
    """下载 Chrome 启动器"""
    # 获取启动器文件路径
    launcher_path = Path(current_app.root_path).parent / 'tools' / 'chrome_launcher' / 'dist'
    
    # 查找最新的启动器 zip
    zip_files = list(launcher_path.glob('chrome-launcher-*.zip'))
    
    if not zip_files:
        return jsonify({
            'success': False,
            'error': 'Launcher package not found'
        }), 404
    
    # 返回最新的文件
    latest_zip = max(zip_files, key=lambda p: p.stat().st_mtime)
    
    return send_file(
        latest_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=latest_zip.name
    )


@chrome_api.route('/api/chrome/launcher/info', methods=['GET'])
def get_launcher_info():
    """获取启动器信息"""
    return jsonify({
        'success': True,
        'version': '1.0.0',
        'platforms': ['windows', 'macos', 'linux'],
        'download_url': '/api/chrome/launcher/download',
        'debug_port': DEBUG_PORT,
        'instructions': [
            '下载并解压启动器',
            '双击运行 start_browser.exe',
            '在 Chrome 中登录番茄账号',
            '返回大文娱页面点击「检测连接」'
        ]
    })


@chrome_api.route('/api/chrome/connect', methods=['POST'])
def connect_chrome():
    """尝试连接 Chrome（供其他模块调用）"""
    from playwright.sync_api import sync_playwright
    
    status = check_chrome_status()
    
    if not status['running']:
        return jsonify({
            'success': False,
            'error': 'Chrome is not running',
            'message': '请先启动 Chrome 浏览器'
        }), 400
    
    try:
        # 测试连接
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(
            f'http://127.0.0.1:{DEBUG_PORT}'
        )
        
        # 获取基本信息
        contexts = browser.contexts
        pages = contexts[0].pages if contexts else []
        
        browser_info = {
            'success': True,
            'contexts': len(contexts),
            'pages': len(pages),
            'pages_info': [
                {'title': p.title(), 'url': p.url} 
                for p in pages[:5]  # 只返回前5个页面
            ]
        }
        
        browser.close()
        playwright.stop()
        
        return jsonify(browser_info)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': '连接 Chrome 失败'
        }), 500


@chrome_api.route('/api/chrome/navigate', methods=['POST'])
def navigate_chrome():
    """控制 Chrome 浏览器导航到指定 URL"""
    from playwright.sync_api import sync_playwright
    
    status = check_chrome_status()
    
    if not status['running']:
        return jsonify({
            'success': False,
            'error': 'Chrome is not running',
            'message': '请先启动 Chrome 浏览器'
        }), 400
    
    # 获取请求中的 URL
    from flask import request
    data = request.get_json()
    url = data.get('url') if data else None
    
    if not url:
        return jsonify({
            'success': False,
            'error': 'Missing URL parameter',
            'message': '请提供要打开的网址'
        }), 400
    
    try:
        # 连接到 Chrome
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(
            f'http://127.0.0.1:{DEBUG_PORT}'
        )
        
        # 获取第一个上下文和页面
        contexts = browser.contexts
        if not contexts:
            # 如果没有上下文，创建新页面
            context = browser.new_context()
            page = context.new_page()
        else:
            context = contexts[0]
            pages = context.pages
            if pages:
                page = pages[0]  # 使用第一个已有页面
            else:
                page = context.new_page()
        
        # 导航到指定 URL
        page.goto(url, wait_until='domcontentloaded')
        
        browser.close()
        playwright.stop()
        
        return jsonify({
            'success': True,
            'message': f'已打开: {url}',
            'url': url
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'打开页面失败: {str(e)}'
        }), 500
