"""
配置加载器模块
负责加载和管理自动化系统的配置
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录路径，默认为当前目录下的config
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent.parent / "config"
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        config_file = self.config_dir / "automation_config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            print(f"✓ 配置文件加载成功: {config_file}")
        except yaml.YAMLError as e:
            raise ValueError(f"配置文件格式错误: {e}")
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败: {e}")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，使用点号分隔，如 'basic.debug_port'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_basic_config(self) -> Dict[str, Any]:
        """获取基础配置"""
        return self.get('basic', {})
    
    def get_paths_config(self) -> Dict[str, Any]:
        """获取路径配置"""
        return self.get('paths', {})
    
    def get_publishing_config(self) -> Dict[str, Any]:
        """获取发布配置"""
        return self.get('publishing', {})
    
    def get_timeouts_config(self) -> Dict[str, Any]:
        """获取超时配置"""
        return self.get('timeouts', {})
    
    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return self.get('browser', {})
    
    def get_contract_config(self) -> Dict[str, Any]:
        """获取签约配置"""
        return self.get('contract', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def get_notification_config(self) -> Dict[str, Any]:
        """获取通知配置"""
        return self.get('notification', {})
    
    def get_debug_port(self) -> int:
        """获取调试端口"""
        return self.get('basic.debug_port', 9988)
    
    def get_scan_interval(self) -> int:
        """获取扫描间隔"""
        return self.get('basic.scan_interval', 1800)
    
    def get_max_retries(self) -> int:
        """获取最大重试次数"""
        return self.get('basic.max_retries', 3)
    
    def get_novel_path(self) -> str:
        """获取小说项目路径"""
        return self.get('paths.novel_path', '小说项目')
    
    def get_published_path(self) -> str:
        """获取已发布小说路径"""
        return self.get('paths.published_path', '已经发布')
    
    def get_progress_file(self) -> str:
        """获取进度文件路径"""
        return self.get('paths.progress_file', '发布进度.json')
    
    def get_progress_detail_file(self) -> str:
        """获取详细进度文件路径"""
        return self.get('paths.progress_detail_file', '发布进度细节.json')
    
    def get_publish_times(self) -> list:
        """获取发布时间点列表"""
        return self.get('publishing.publish_times', ['05:25', '11:25', '17:25', '23:25'])
    
    def get_chapters_per_time_slot(self) -> int:
        """获取每个时间点最大章节数"""
        return self.get('publishing.chapters_per_time_slot', 2)
    
    def get_min_words_for_scheduled_publish(self) -> int:
        """获取定时发布的最小字数阈值"""
        return self.get('publishing.min_words_for_scheduled_publish', 60000)
    
    def get_publish_buffer_minutes(self) -> int:
        """获取发布时间缓冲分钟数"""
        return self.get('publishing.publish_buffer_minutes', 35)
    
    def get_click_timeout(self) -> int:
        """获取点击超时时间"""
        return self.get('timeouts.click', 15000)
    
    def get_fill_timeout(self) -> int:
        """获取填充超时时间"""
        return self.get('timeouts.fill', 12000)
    
    def get_wait_element_timeout(self) -> int:
        """获取等待元素超时时间"""
        return self.get('timeouts.wait_element', 5000)
    
    def get_contract_contact_info(self) -> Dict[str, str]:
        """获取签约联系信息"""
        return self.get('contract.contact_info', {})
    
    def ensure_directory_exists(self, directory: str) -> str:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            目录路径
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")
        return directory
    
    def get_full_path(self, path_key: str) -> str:
        """
        获取完整路径
        
        Args:
            path_key: 路径配置键名
            
        Returns:
            完整路径
        """
        path_value = self.get(f'paths.{path_key}', '')
        if path_value:
            return os.path.abspath(path_value)
        return path_value
    
    def reload_config(self):
        """重新加载配置文件"""
        self._load_config()
        print("配置文件已重新加载")
    
    def validate_config(self) -> bool:
        """
        验证配置文件的完整性
        
        Returns:
            配置是否有效
        """
        required_keys = [
            'basic.debug_port',
            'paths.novel_path',
            'publishing.publish_times',
            'timeouts.click'
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                print(f"✗ 缺少必需的配置项: {key}")
                return False
        
        # 验证发布时间格式
        publish_times = self.get_publish_times()
        for time_str in publish_times:
            try:
                hours, minutes = map(int, time_str.split(':'))
                if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                    raise ValueError
            except (ValueError, AttributeError):
                print(f"✗ 无效的发布时间格式: {time_str}")
                return False
        
        print("✓ 配置文件验证通过")
        return True


# 全局配置加载器实例
config_loader = None


def get_config_loader(config_dir: Optional[str] = None) -> ConfigLoader:
    """
    获取全局配置加载器实例
    
    Args:
        config_dir: 配置文件目录路径
        
    Returns:
        配置加载器实例
    """
    global config_loader
    if config_loader is None:
        config_loader = ConfigLoader(config_dir)
    return config_loader


def reload_config(config_dir: Optional[str] = None):
    """
    重新加载配置
    
    Args:
        config_dir: 配置文件目录路径
    """
    global config_loader
    config_loader = ConfigLoader(config_dir)