#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome 启动器 API
用于检测本地 Chrome 状态和提供下载
"""

import os
import json
import requests
from flask import Blueprint, jsonify, send_file, current_app
from pathlib import Path

chrome_api = Blueprint('chrome_api', __name__)

# Chrome 调试端口
DEBUG_PORT = 9988


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
    
    return {
        'running': False,
        'version': None,
        'error': 'Chrome not running or debug port not accessible'
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
