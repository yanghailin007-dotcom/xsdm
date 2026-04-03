#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置文件 - 区分本地开发和生产环境
"""

import os
from pathlib import Path

# 默认配置
DEFAULT_CONFIG = {
    # 官网地址
    'website_url': 'https://novel-ai.online',
    'upload_guide_path': '/pages/v2/uploader-guide',
    
    # API地址
    'api_base_url': 'https://novel-ai.online',
    
    # 本地开发配置
    'dev_website_url': 'http://localhost:5000',
    'dev_api_base_url': 'http://localhost:5000',
}

class EnvironmentConfig:
    """环境配置管理器"""
    
    def __init__(self):
        # 检测是否在开发环境
        self.is_development = self._detect_development()
        
        # 也可以强制通过环境变量设置
        env_mode = os.environ.get('NOVEL_PUBLISHER_ENV', '').lower()
        if env_mode == 'dev' or env_mode == 'development':
            self.is_development = True
        elif env_mode == 'prod' or env_mode == 'production':
            self.is_development = False
    
    def _detect_development(self) -> bool:
        """检测是否是开发环境"""
        # 检查是否存在开发标记文件
        dev_marker = Path(__file__).parent / '.dev_mode'
        if dev_marker.exists():
            return True
        
        # 检查是否在源代码目录运行（有.git目录）
        git_dir = Path(__file__).parent / '.git'
        if git_dir.exists():
            return True
        
        return False
    
    @property
    def website_url(self) -> str:
        """获取官网地址"""
        if self.is_development:
            return DEFAULT_CONFIG['dev_website_url']
        return DEFAULT_CONFIG['website_url']
    
    @property
    def api_base_url(self) -> str:
        """获取API基础地址"""
        if self.is_development:
            return DEFAULT_CONFIG['dev_api_base_url']
        return DEFAULT_CONFIG['api_base_url']
    
    @property
    def upload_guide_url(self) -> str:
        """获取上传指南完整URL"""
        return f"{self.website_url}{DEFAULT_CONFIG['upload_guide_path']}"
    
    def enable_dev_mode(self):
        """启用开发模式（创建标记文件）"""
        dev_marker = Path(__file__).parent / '.dev_mode'
        dev_marker.touch()
        self.is_development = True
        print(f"✅ 已启用开发模式，官网地址: {self.website_url}")
    
    def disable_dev_mode(self):
        """禁用开发模式（删除标记文件）"""
        dev_marker = Path(__file__).parent / '.dev_mode'
        if dev_marker.exists():
            dev_marker.unlink()
        self.is_development = False
        print(f"✅ 已切换到生产模式，官网地址: {self.website_url}")


# 全局配置实例
env_config = EnvironmentConfig()


if __name__ == "__main__":
    # 测试代码
    print(f"当前环境: {'开发模式' if env_config.is_development else '生产模式'}")
    print(f"官网地址: {env_config.website_url}")
    print(f"API地址: {env_config.api_base_url}")
    print(f"上传指南: {env_config.upload_guide_url}")
    print()
    print("使用方法:")
    print("  启用开发模式: python config_env.py dev")
    print("  禁用开发模式: python config_env.py prod")
