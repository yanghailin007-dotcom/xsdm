#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token 管理器 - 持久化保存和自动刷新
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta


class TokenManager:
    """Token 持久化管理"""
    
    def __init__(self, storage_file: str = "tokens.json"):
        self.storage_path = Path(__file__).parent / storage_file
        self.tokens: Dict[str, dict] = {}
        self._load()
    
    def _load(self):
        """从文件加载 tokens"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tokens = data.get('tokens', {})
                print(f"📂 已加载 {len(self.tokens)} 个账户的 token")
            except Exception as e:
                print(f"⚠️ 加载 token 失败: {e}")
                self.tokens = {}
    
    def save(self):
        """保存 tokens 到文件"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'tokens': self.tokens,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"❌ 保存 token 失败: {e}")
            return False
    
    def store_token(self, username: str, token_data: dict):
        """
        保存用户 token
        
        Args:
            username: 用户名
            token_data: 包含 access_token, refresh_token, expires_at, user_id 等
        """
        self.tokens[username] = {
            'username': username,
            'user_id': token_data.get('user_id'),
            'access_token': token_data.get('access_token'),
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': token_data.get('expires_at'),
            'is_admin': token_data.get('is_admin', False),
            'points_balance': token_data.get('points_balance', 0),
            'saved_at': time.time(),
            'last_used': time.time()
        }
        self.save()
        print(f"💾 Token 已保存: {username}")
    
    def get_token(self, username: str) -> Optional[dict]:
        """获取用户 token"""
        token = self.tokens.get(username)
        if token:
            # 更新最后使用时间
            token['last_used'] = time.time()
            self.save()
        return token
    
    def is_token_valid(self, username: str, buffer_seconds: int = 300) -> bool:
        """
        检查 token 是否有效
        
        Args:
            username: 用户名
            buffer_seconds: 提前多少秒认为过期（默认5分钟）
        """
        token = self.tokens.get(username)
        if not token:
            return False
        
        expires_at = token.get('expires_at', 0)
        # 检查是否过期（提前 buffer_seconds）
        return time.time() < (expires_at - buffer_seconds)
    
    def should_refresh(self, username: str, refresh_threshold: int = 3600) -> bool:
        """
        判断是否需要刷新 token
        
        Args:
            username: 用户名
            refresh_threshold: 提前多少秒刷新（默认1小时）
        """
        token = self.tokens.get(username)
        if not token:
            return False
        
        expires_at = token.get('expires_at', 0)
        # 如果将在 refresh_threshold 秒内过期，建议刷新
        return time.time() > (expires_at - refresh_threshold)
    
    def update_token(self, username: str, new_token_data: dict):
        """更新 token（刷新后使用）"""
        if username in self.tokens:
            self.tokens[username].update({
                'access_token': new_token_data.get('access_token'),
                'refresh_token': new_token_data.get('refresh_token'),
                'expires_at': new_token_data.get('expires_at'),
                'saved_at': time.time()
            })
            self.save()
            print(f"🔄 Token 已更新: {username}")
    
    def remove_token(self, username: str):
        """删除用户 token"""
        if username in self.tokens:
            del self.tokens[username]
            self.save()
            print(f"🗑️ Token 已删除: {username}")
    
    def get_all_users(self) -> list:
        """获取所有保存的用户名"""
        return list(self.tokens.keys())
    
    def cleanup_expired(self, max_age_days: int = 30):
        """清理过期的 token"""
        now = time.time()
        expired_users = []
        
        for username, token in self.tokens.items():
            saved_at = token.get('saved_at', 0)
            # 超过 max_age_days 天未使用
            if now - saved_at > (max_age_days * 24 * 3600):
                expired_users.append(username)
        
        for username in expired_users:
            self.remove_token(username)
        
        if expired_users:
            print(f"🧹 清理了 {len(expired_users)} 个过期 token")


# 全局 token 管理器实例
token_manager = TokenManager()


if __name__ == "__main__":
    # 测试代码
    print("=" * 50)
    print("Token 管理器测试")
    print("=" * 50)
    
    # 模拟保存 token
    test_token = {
        'user_id': 1,
        'username': 'test_user',
        'access_token': 'test_access_token',
        'refresh_token': 'test_refresh_token',
        'expires_at': time.time() + 7200,  # 2小时后过期
        'is_admin': False,
        'points_balance': 100
    }
    
    token_manager.store_token('test_user', test_token)
    
    # 读取 token
    stored = token_manager.get_token('test_user')
    print(f"\n已保存的 token: {stored}")
    
    # 检查有效性
    is_valid = token_manager.is_token_valid('test_user')
    print(f"\nToken 是否有效: {is_valid}")
    
    # 检查是否需要刷新
    should_refresh = token_manager.should_refresh('test_user')
    print(f"是否需要刷新: {should_refresh}")
    
    # 列出所有用户
    users = token_manager.get_all_users()
    print(f"\n所有用户: {users}")
