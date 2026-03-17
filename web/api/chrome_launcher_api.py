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


# 固定的 Chrome 安装目录（在客户电脑上）
# Windows: D:\大文娱\chrome_launcher\ (首选位置，如果不存在可用 C 盘)
# Mac/Linux: ~/大文娱/chrome_launcher/
if sys.platform == 'win32':
    # Windows 首选 D 盘，备选 C 盘
    CHROME_INSTALL_DIR = 'D:\\大文娱\\chrome_launcher'
    CHROME_INSTALL_DIR_FALLBACK = 'C:\\大文娱\\chrome_launcher'
else:
    CHROME_INSTALL_DIR = str(Path.home() / '大文娱' / 'chrome_launcher')
    CHROME_INSTALL_DIR_FALLBACK = None


def get_chrome_install_dir() -> Path:
    """获取 Chrome 应该安装的固定目录（客户电脑上的绝对路径）"""
    # 如果 D 盘存在就用 D 盘，否则用备选路径
    if sys.platform == 'win32':
        if Path('D:\\').exists():
            return Path(CHROME_INSTALL_DIR)
        elif CHROME_INSTALL_DIR_FALLBACK and Path('C:\\').exists():
            return Path(CHROME_INSTALL_DIR_FALLBACK)
    return Path(CHROME_INSTALL_DIR)


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
    """检查 Chrome 是否已安装（仅在客户电脑的固定目录）"""
    # 获取实际检测路径（用于检查是否已安装）
    install_dir = get_chrome_install_dir()
    chrome_dir = install_dir / 'chrome'
    
    # 检查 Chrome 是否存在
    chrome_exe, start_script = find_chrome_in_dir(chrome_dir)
    
    # 根据平台显示不同的安装指引
    platform = sys.platform
    if platform == 'win32':
        # 始终向用户显示首选路径 D: 盘
        primary_path = 'D:\\大文娱\\chrome_launcher'
        fallback_path = 'C:\\大文娱\\chrome_launcher'
        
        setup_steps = [
            '1. 下载 chrome-launcher.zip 到任意位置（如：桌面）',
            '2. 解压后将文件夹重命名为 "chrome_launcher"',
            f'3. 将整个文件夹移动到: {primary_path}',
            f'4. 最终路径应该是: {primary_path}\\一键启动.bat',
            '5. 双击运行 一键启动.bat'
        ]
        tip = '如果 D: 盘不存在，请使用 C: 盘（即：' + fallback_path + '）'
        
        # 返回给前端显示的路径（优先 D 盘）
        display_dir = primary_path
    elif platform == 'darwin':
        mac_path = str(Path.home() / '大文娱' / 'chrome_launcher')
        setup_steps = [
            '1. 下载 chrome-launcher.zip 到任意位置',
            f'2. 解压后将文件夹重命名为 "chrome_launcher"',
            f'3. 将整个文件夹移动到: {mac_path}',
            f'4. 最终路径应该是: {mac_path}/start_chrome.sh',
            '5. 运行: chmod +x start_chrome.sh && ./start_chrome.sh'
        ]
        tip = None
        display_dir = mac_path
    else:  # linux
        linux_path = str(Path.home() / '大文娱' / 'chrome_launcher')
        setup_steps = [
            '1. 下载 chrome-launcher.zip 到任意位置',
            f'2. 解压后将文件夹重命名为 "chrome_launcher"',
            f'3. 将整个文件夹移动到: {linux_path}',
            f'4. 最终路径应该是: {linux_path}/start_chrome.sh',
            '5. 运行: chmod +x start_chrome.sh && ./start_chrome.sh'
        ]
        tip = None
        display_dir = linux_path
    
    return {
        'installed': chrome_exe is not None,
        'chrome_path': str(chrome_exe) if chrome_exe else None,
        'start_script': str(start_script) if start_script else None,
        'install_dir': display_dir,  # 始终向用户显示首选路径
        'script_name': '一键启动.bat' if platform == 'win32' else 'start_chrome.sh',
        'platform': 'windows' if platform == 'win32' else ('macos' if platform == 'darwin' else 'linux'),
        'setup_steps': setup_steps,
        'setup_tip': tip
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
