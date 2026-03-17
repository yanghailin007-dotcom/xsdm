#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
番茄小说上传配置 API
支持配置：首次发布章节数、每日发布章节数、发布时间等
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, session

fanqie_config_api = Blueprint('fanqie_config_api', __name__)

# 配置文件目录
CONFIG_DIR = Path("config/fanqie")

# 默认配置（符合番茄平台签约要求：20章 6万字）
DEFAULT_UPLOAD_CONFIG = {
    # 首次发布配置
    "first_publish": {
        "enabled": True,
        "chapter_count": 20,   # 首次发布章节数（番茄签约要求：20章）
        "word_count": 60000,   # 首次发布字数（番茄签约要求：6万字）
        "publish_immediately": True  # 立即发布还是定时发布
    },
    # 每日发布配置
    "daily_publish": {
        "enabled": True,
        "chapter_count": 2,    # 每天发布章节数
        "word_count": 0,       # 每天发布字数（0表示不限制）
        "publish_time": "09:00",  # 发布时间（HH:MM格式）
        "interval_minutes": 30  # 章节间隔（分钟）
    },
    # 高级配置
    "advanced": {
        "auto_create_book": True,  # 自动创建书籍
        "auto_set_cover": True,    # 自动设置封面
        "skip_published": True,    # 跳过已发布章节
        "check_duplicate": True,   # 检查重复章节
        "retry_on_failure": 3,     # 失败重试次数
        "publish_mode": "immediate"  # immediate:立即, scheduled:定时, draft:草稿
    },
    # 书籍信息配置（可选，覆盖项目信息）
    "book_override": {
        "enabled": False,
        "title": "",           # 自定义书名
        "author": "",          # 自定义作者
        "category": "",        # 分类
        "tags": [],            # 标签
        "description": "",     # 简介
        "cover_image": ""      # 封面图片路径
    }
}


def get_user_config_file(novel_title: str) -> Path:
    """获取用户配置文件路径"""
    username = session.get('username', 'default')
    safe_title = "".join(c if c.isalnum() or c in '_-' else '_' for c in novel_title)
    
    user_config_dir = CONFIG_DIR / username
    user_config_dir.mkdir(parents=True, exist_ok=True)
    
    return user_config_dir / f"{safe_title}_upload_config.json"


def load_config(novel_title: str) -> Dict[str, Any]:
    """加载配置"""
    config_file = get_user_config_file(novel_title)
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                # 合并默认配置和保存的配置
                config = DEFAULT_UPLOAD_CONFIG.copy()
                _deep_merge(config, saved_config)
                return config
        except Exception as e:
            print(f"[ERROR] 加载配置失败: {e}")
    
    return DEFAULT_UPLOAD_CONFIG.copy()


def save_config(novel_title: str, config: Dict[str, Any]) -> bool:
    """保存配置"""
    try:
        config_file = get_user_config_file(novel_title)
        
        # 添加元数据
        config['_meta'] = {
            'updated_at': datetime.now().isoformat(),
            'version': '1.0'
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        print(f"[ERROR] 保存配置失败: {e}")
        return False


def _deep_merge(base: dict, update: dict):
    """深度合并字典"""
    for key, value in update.items():
        if key.startswith('_'):  # 跳过元数据
            continue
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def validate_config(config: Dict[str, Any]) -> tuple[bool, str]:
    """验证配置是否有效"""
    try:
        # 验证首次发布配置
        first = config.get('first_publish', {})
        if first.get('enabled', False):
            chapter_count = first.get('chapter_count', 0)
            if not isinstance(chapter_count, int) or chapter_count < 1:
                return False, "首次发布章节数必须大于0"
            if chapter_count > 100:
                return False, "首次发布章节数不能超过100"
        
        # 验证每日发布配置
        daily = config.get('daily_publish', {})
        if daily.get('enabled', False):
            chapter_count = daily.get('chapter_count', 0)
            if not isinstance(chapter_count, int) or chapter_count < 0:
                return False, "每日发布章节数不能为负数"
            if chapter_count > 50:
                return False, "每日发布章节数不能超过50"
            
            # 验证时间格式
            publish_time = daily.get('publish_time', '')
            if publish_time:
                try:
                    datetime.strptime(publish_time, "%H:%M")
                except ValueError:
                    return False, "发布时间格式错误，应为 HH:MM"
            
            # 验证间隔
            interval = daily.get('interval_minutes', 0)
            if not isinstance(interval, int) or interval < 0:
                return False, "发布间隔不能为负数"
            if interval > 1440:
                return False, "发布间隔不能超过24小时"
        
        # 验证高级配置
        advanced = config.get('advanced', {})
        retry = advanced.get('retry_on_failure', 3)
        if not isinstance(retry, int) or retry < 0 or retry > 10:
            return False, "重试次数应在0-10之间"
        
        return True, "配置有效"
        
    except Exception as e:
        return False, f"配置验证失败: {str(e)}"


@fanqie_config_api.route('/api/fanqie/config/<path:novel_title>', methods=['GET'])
def get_fanqie_config(novel_title: str):
    """获取番茄上传配置"""
    try:
        config = load_config(novel_title)
        
        # 移除元数据
        config.pop('_meta', None)
        
        return jsonify({
            'success': True,
            'config': config,
            'novel_title': novel_title
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fanqie_config_api.route('/api/fanqie/config/<path:novel_title>', methods=['POST'])
def save_fanqie_config(novel_title: str):
    """保存番茄上传配置"""
    try:
        data = request.get_json()
        
        if not data or 'config' not in data:
            return jsonify({
                'success': False,
                'error': '缺少配置数据'
            }), 400
        
        config = data['config']
        
        # 验证配置
        is_valid, message = validate_config(config)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': message
            }), 400
        
        # 保存配置
        if save_config(novel_title, config):
            return jsonify({
                'success': True,
                'message': '配置已保存',
                'novel_title': novel_title
            })
        else:
            return jsonify({
                'success': False,
                'error': '保存配置失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fanqie_config_api.route('/api/fanqie/config/<path:novel_title>/reset', methods=['POST'])
def reset_fanqie_config(novel_title: str):
    """重置配置为默认值"""
    try:
        if save_config(novel_title, DEFAULT_UPLOAD_CONFIG.copy()):
            config = DEFAULT_UPLOAD_CONFIG.copy()
            config.pop('_meta', None)
            
            return jsonify({
                'success': True,
                'message': '配置已重置为默认值',
                'config': config
            })
        else:
            return jsonify({
                'success': False,
                'error': '重置配置失败'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@fanqie_config_api.route('/api/fanqie/config/template', methods=['GET'])
def get_config_template():
    """获取配置模板（默认值）"""
    config = DEFAULT_UPLOAD_CONFIG.copy()
    config.pop('_meta', None)
    
    return jsonify({
        'success': True,
        'template': config,
        'description': {
            'first_publish': {
                'enabled': '是否启用首次发布',
                'chapter_count': '首次发布的章节数量',
                'word_count': '首次发布的字数（0表示不限制）',
                'publish_immediately': '是否立即发布（false为定时发布）'
            },
            'daily_publish': {
                'enabled': '是否启用每日自动发布',
                'chapter_count': '每天发布的章节数量',
                'word_count': '每天发布的字数（0表示不限制）',
                'publish_time': '发布时间（HH:MM格式）',
                'interval_minutes': '章节之间的发布间隔（分钟）'
            },
            'advanced': {
                'auto_create_book': '自动创建书籍（如果不存在）',
                'auto_set_cover': '自动设置书籍封面',
                'skip_published': '跳过已发布的章节',
                'check_duplicate': '检查并跳过重复章节',
                'retry_on_failure': '上传失败时的重试次数',
                'publish_mode': '发布模式：immediate(立即)/scheduled(定时)/draft(草稿)'
            },
            'book_override': {
                'enabled': '是否覆盖项目信息',
                'title': '自定义书名',
                'author': '自定义作者名',
                'category': '书籍分类',
                'tags': '书籍标签（数组）',
                'description': '书籍简介',
                'cover_image': '封面图片路径'
            }
        }
    })
