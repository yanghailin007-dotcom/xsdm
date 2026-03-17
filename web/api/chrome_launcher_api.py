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


def check_chrome_installed() -> dict:
    """检查 Chrome 是否已安装（在 chrome_launcher 目录中）"""
    # 获取 chrome_launcher 目录
    # current_app.root_path 是 web/ 目录，parent 是项目根目录
    launcher_dir = Path(current_app.root_path).parent / 'tools' / 'chrome_launcher'
    chrome_dir = launcher_dir / 'chrome'
    
    # 检查一键启动脚本是否存在
    if sys.platform == 'win32':
        bat_file = launcher_dir / '一键启动.bat'
        start_script = bat_file if bat_file.exists() else None
    else:
        sh_file = launcher_dir / 'start_chrome.sh'
        start_script = sh_file if sh_file.exists() else None
    
    # 检查 Chrome 可执行文件是否存在
    platform = sys.platform
    chrome_exe = None
    
    if platform == 'win32':
        possible_paths = [
            chrome_dir / 'chrome-win64' / 'chrome.exe',
            chrome_dir / 'chrome' / 'chrome.exe',
            chrome_dir / 'chrome.exe',
        ]
    elif platform == 'darwin':
        possible_paths = [
            chrome_dir / 'chrome-mac-x64' / 'Google Chrome for Testing.app' / 'Contents' / 'MacOS' / 'Google Chrome for Testing',
            chrome_dir / 'Google Chrome.app' / 'Contents' / 'MacOS' / 'Google Chrome',
        ]
    else:  # linux
        possible_paths = [
            chrome_dir / 'chrome-linux64' / 'chrome',
            chrome_dir / 'chrome' / 'chrome',
            chrome_dir / 'chrome',
        ]
    
    for path in possible_paths:
        if path.exists():
            chrome_exe = path
            break
    
    # 返回检测结果
    return {
        'installed': chrome_exe is not None,
        'chrome_path': str(chrome_exe) if chrome_exe else None,
        'start_script': str(start_script) if start_script else None,
        'launcher_dir': str(launcher_dir),
        'script_name': '一键启动.bat' if sys.platform == 'win32' else 'start_chrome.sh'
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
