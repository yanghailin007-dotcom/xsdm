"""
写作风格加载器
从 JSON 配置文件加载写作风格指南

作者：AI Assistant
创建时间：2026-03-29
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from src.utils.logger import get_logger

logger = get_logger("StyleLoader")


class StyleLoader:
    """写作风格加载器 - 从 JSON 配置文件加载"""
    
    _instance = None
    _cache = {}
    
    def __new__(cls, *args, **kwargs):
        """单例模式 - 避免重复加载文件"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, styles_dir: Optional[str] = None):
        if self._initialized:
            return
            
        if styles_dir is None:
            # 默认路径：相对于项目根目录
            base_dir = Path(__file__).parent.parent.parent.parent
            styles_dir = base_dir / "prompt_packages" / "default" / "market_driven" / "styles"
        
        self.styles_dir = Path(styles_dir)
        self._initialized = True
        
        logger.info(f"[StyleLoader] 初始化 | 风格目录: {self.styles_dir}")
    
    def load_style(self, style_id: str) -> Optional[Dict[str, Any]]:
        """
        加载指定风格的配置
        
        Args:
            style_id: 风格ID，如 "shock_flow", "face_slap"
            
        Returns:
            风格配置字典，如果不存在返回 None
        """
        # 检查缓存
        if style_id in self._cache:
            logger.debug(f"[StyleLoader] 命中缓存: {style_id}")
            return self._cache[style_id]
        
        # 构建文件路径
        style_file = self.styles_dir / f"{style_id}.json"
        
        if not style_file.exists():
            logger.warning(f"[StyleLoader] 风格文件不存在: {style_file}")
            return None
        
        try:
            with open(style_file, 'r', encoding='utf-8') as f:
                style_config = json.load(f)
            
            # 存入缓存
            self._cache[style_id] = style_config
            logger.info(f"[StyleLoader] 加载风格成功: {style_id} ({style_file.name})")
            return style_config
            
        except json.JSONDecodeError as e:
            logger.error(f"[StyleLoader] JSON解析错误 {style_file}: {e}")
            return None
        except Exception as e:
            logger.error(f"[StyleLoader] 加载风格失败 {style_id}: {e}")
            return None
    
    def render_style_guide(self, style_id: str) -> str:
        """
        将风格配置渲染为 Prompt 字符串
        
        Args:
            style_id: 风格ID
            
        Returns:
            渲染后的风格指导字符串
        """
        style = self.load_style(style_id)
        if style is None:
            logger.warning(f"[StyleLoader] 无法渲染风格 {style_id}，使用空字符串")
            return ""
        
        try:
            return self._render_to_prompt(style)
        except Exception as e:
            logger.error(f"[StyleLoader] 渲染风格失败 {style_id}: {e}")
            return ""
    
    def _render_to_prompt(self, style: Dict[str, Any]) -> str:
        """将风格配置渲染为 Prompt 格式"""
        lines = []
        
        # 标题和警告
        lines.append(f"## 😱 {style.get('style_name', '写作风格')}")
        lines.append("")
        
        if 'warning' in style:
            lines.append(f"**{style['warning']}**")
            lines.append("")
        
        # 核心原则
        if 'core_principles' in style:
            lines.append("### 核心原则")
            for principle in style['core_principles']:
                lines.append(f"- {principle}")
            lines.append("")
        
        # 正确/错误示例
        if 'examples' in style:
            lines.append("### 示例对比")
            examples = style['examples']
            
            if 'correct' in examples:
                correct = examples['correct']
                lines.append(f"**✅ {correct.get('description', '正确写法')}：**")
                lines.append("```")
                lines.append(correct.get('text', ''))
                lines.append("```")
                lines.append("")
            
            if 'incorrect' in examples:
                incorrect = examples['incorrect']
                lines.append(f"**❌ {incorrect.get('description', '错误写法')}：**")
                lines.append("```")
                lines.append(incorrect.get('text', ''))
                lines.append("```")
                lines.append("")
        
        # 各层级技巧
        if 'levels' in style:
            lines.append("### 震惊铺展技巧")
            
            # 按 order 排序
            sorted_levels = sorted(
                style['levels'].items(),
                key=lambda x: x[1].get('order', 0)
            )
            
            for level_id, level_config in sorted_levels:
                level_name = level_config.get('name', level_id)
                lines.append(f"\n**{level_name}：** {level_config.get('description', '')}")
                
                techniques = level_config.get('techniques', {})
                
                # 表情描写
                if 'expression' in techniques:
                    lines.append("- 表情：" + " / ".join(techniques['expression'][:3]))
                
                # 语言描写
                if 'dialogue' in techniques:
                    lines.append("- 台词：" + " / ".join(techniques['dialogue'][:3]))
                
                # 动作描写
                if 'action' in techniques:
                    lines.append("- 动作：" + " / ".join(techniques['action'][:3]))
                
                # 弹幕
                if 'bullet_comments' in techniques:
                    lines.append("- 弹幕：" + " / ".join(techniques['bullet_comments'][:3]))
            
            lines.append("")
        
        # 常见错误
        if 'common_mistakes' in style:
            lines.append("### 常见错误")
            for mistake in style['common_mistakes']:
                lines.append(f"- **{mistake.get('mistake', '')}**：{mistake.get('solution', '')}")
            lines.append("")
        
        # 字数指导
        if 'word_count_guide' in style:
            lines.append("### 字数分配建议")
            guide = style['word_count_guide']
            for key, value in guide.items():
                if key != 'total':
                    level_name = style.get('levels', {}).get(key, {}).get('name', key)
                    lines.append(f"- {level_name}：{value}")
            if 'total' in guide:
                lines.append(f"- 总计：{guide['total']}")
            lines.append("")
        
        # 检查清单
        if 'checklist' in style:
            lines.append("### 自检清单")
            for item in style['checklist']:
                lines.append(f"- [ ] {item}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_available_styles(self) -> List[str]:
        """获取所有可用的风格ID列表"""
        if not self.styles_dir.exists():
            return []
        
        styles = []
        for file in self.styles_dir.glob("*.json"):
            if file.stem.startswith('_'):
                continue  # 跳过私有文件
            styles.append(file.stem)
        
        return sorted(styles)
    
    def clear_cache(self):
        """清除缓存 - 用于热更新"""
        self._cache.clear()
        logger.info("[StyleLoader] 缓存已清除")


# 便捷函数
def get_style_guide(style_id: str) -> str:
    """获取指定风格的指导文本（便捷函数）"""
    loader = StyleLoader()
    return loader.render_style_guide(style_id)


def get_style_config(style_id: str) -> Optional[Dict[str, Any]]:
    """获取指定风格的配置（便捷函数）"""
    loader = StyleLoader()
    return loader.load_style(style_id)
