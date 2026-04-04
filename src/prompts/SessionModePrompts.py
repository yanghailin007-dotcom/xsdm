"""
分域会话模式提示词管理器

支持从 prompt_packages/_base/system_components/session_mode_prompts.json 加载外部配置，
如果 JSON 文件不存在或解析失败，则回退到内置默认提示词。
"""

import json
from pathlib import Path
from typing import Dict


class SessionModePrompts:
    """分域会话模式提示词集合"""

    def __init__(self):
        self.prompts: Dict[str, str] = {}
        self._load_builtin_prompts()
        self._load_external_prompts()

    def _load_builtin_prompts(self):
        """加载内置默认提示词（作为 JSON 加载失败的回退）"""
        # 内置默认值已迁移到 session_mode_prompts.json 中统一管理
        # 如果外部文件加载失败，将使用空字典，实际运行时由调用方处理
        pass

    def _load_external_prompts(self):
        """尝试从 prompt_packages 加载外部 JSON 配置"""
        json_path = Path(__file__).parent.parent.parent / "prompt_packages" / "_base" / "system_components" / "session_mode_prompts.json"
        
        if not json_path.exists():
            print(f"[SessionModePrompts] 未找到外部提示词配置: {json_path}")
            return
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            prompts = data.get("prompts", {})
            if prompts:
                self.prompts.update(prompts)
                print(f"[SessionModePrompts] 成功加载 {len(prompts)} 个外部提示词模板")
            else:
                print(f"[SessionModePrompts] 外部配置中未找到 prompts 字段")
                
        except Exception as e:
            print(f"[SessionModePrompts] 加载外部提示词失败: {e}")

    def get(self, key: str, default: str = None) -> str:
        """获取指定提示词模板"""
        return self.prompts.get(key, default)

    def format(self, key: str, default: str = None, **kwargs) -> str:
        """获取并格式化提示词模板"""
        template = self.get(key, default)
        if template is None:
            return ""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            print(f"[SessionModePrompts] 格式化提示词 '{key}' 失败，缺少变量: {e}")
            return template
