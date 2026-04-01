"""
字数强制达标机制 (WordCountEnforcer)

解决章节字数不足问题的通用方案

核心功能：
1. 实时字数检测与追踪
2. 智能扩写策略（通用，不限题材）
3. 强制字数检查（不达标则扩写）
4. 字数分配优化（段落级字数控制）

适用题材：所有（修仙/都市/科幻/国运等）
扩写策略：反应链、细节分层、情绪递进、后果展开
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class WordCountEnforcer:
    """
    通用字数强制达标执行器
    
    平台标准（可配置）：
    - 单章目标：2000-2500字（番茄/起点等）
    - 最低红线：1800字（低于此必须扩写）
    - 黄金字数：2200字（最佳阅读体验）
    
    扩写策略（通用，不依赖特定题材）：
    1. 反应链扩写：事件→旁观者反应→更广泛反应
    2. 细节分层扩写：宏观→微观→感官细节
    3. 情绪递进扩写：平静→紧张→爆发→余波
    4. 后果扩写：即时后果→短期影响→长期暗示
    
    禁止：无意义的环境描写、心理独白、水字数对话
    """
    
    # 配置路径
    CONFIG_PATH = "prompt_packages/default/market_driven/word_count_enforcement_prompts.json"
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载提示词配置"""
        try:
            import json
            from pathlib import Path
            config_path = Path(self.CONFIG_PATH)
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"[WordEnforcer] 无法加载配置: {e}")
            return {}
    
    # 字数标准
    TARGET_WORD_COUNT = 2200  # 目标字数
    MIN_WORD_COUNT = 1800     # 最低红线
    MAX_WORD_COUNT = 2500     # 上限
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.expansion_history: List[Dict] = []
    
    def check_word_count(self, content: str, chapter_num: int) -> Tuple[bool, int, str]:
        """
        检查字数是否达标
        
        Returns:
            (is_valid, actual_count, message)
        """
        # 清理内容，只计算正文
        clean_content = self._extract_main_content(content)
        word_count = len(clean_content)
        
        if word_count < self.MIN_WORD_COUNT:
            return False, word_count, f"字数不足！{word_count} < {self.MIN_WORD_COUNT}，需要扩写"
        elif word_count > self.MAX_WORD_COUNT:
            return False, word_count, f"字数超标！{word_count} > {self.MAX_WORD_COUNT}，需要精简"
        elif word_count < self.TARGET_WORD_COUNT:
            return True, word_count, f"字数略低（{word_count}），建议扩写至{self.TARGET_WORD_COUNT}"
        else:
            return True, word_count, f"字数达标（{word_count}）"
    
    def expand_content(self, content: str, chapter_num: int, 
                       target_increase: int = 400,
                       expansion_type: str = "auto") -> str:
        """
        智能扩写内容（番茄风格）
        
        Args:
            content: 原始内容
            chapter_num: 章节号
            target_increase: 目标增加字数
            expansion_type: 扩写类型 (auto/barrage/shock/numbers/emotion)
        
        Returns:
            扩写后的内容
        """
        current_count = len(content)
        needed = target_increase
        
        logger.info(f"[WordEnforcer] 第{chapter_num}章扩写 | 当前{current_count}字 | 目标+{needed}字")
        
        # 自动判断扩写类型
        if expansion_type == "auto":
            expansion_type = self._determine_expansion_type(content, chapter_num)
        
        # 根据类型选择扩写策略
        expansion_prompt = self._build_expansion_prompt(content, expansion_type, needed)
        
        # 调用API扩写（如果可用）
        if self.api_client:
            try:
                expanded = self._call_expansion_api(content, expansion_prompt)
                new_count = len(expanded)
                actual_increase = new_count - current_count
                
                self.expansion_history.append({
                    "chapter": chapter_num,
                    "type": expansion_type,
                    "before": current_count,
                    "after": new_count,
                    "increase": actual_increase
                })
                
                logger.info(f"[WordEnforcer] 扩写完成 | +{actual_increase}字 | 类型:{expansion_type}")
                return expanded
            except Exception as e:
                logger.error(f"[WordEnforcer] API扩写失败: {e}")
        
        # 备用：本地扩写
        return self._local_expansion(content, expansion_type, needed)
    
    def _determine_expansion_type(self, content: str, chapter_num: int) -> str:
        """根据内容判断最佳扩写类型"""
        # 检查是否有战斗/冲突场景
        has_combat = any(kw in content for kw in ["战", "杀", "拳", "刀", "雷", "轰"])
        
        # 检查是否有系统提示
        has_system = "【叮" in content or "系统" in content
        
        # 检查是否有观众/弹幕
        has_audience = any(kw in content for kw in ["弹幕", "直播间", "观众", "全网"])
        
        # 检查是否有数值变化
        has_numbers = bool(re.search(r'\d+%|\d+万|\d+亿', content))
        
        if has_audience and has_combat:
            return "barrage"  # 弹幕反应扩写
        elif has_system and has_numbers:
            return "numbers"  # 数字可视化扩写
        elif has_combat:
            return "shock"    # 震惊层级扩写
        else:
            return "emotion"  # 情绪渲染扩写
    
    def _build_expansion_prompt(self, content: str, expansion_type: str, needed: int) -> str:
        """构建扩写提示词"""
        
        # 🔥 从JSON配置加载模板
        templates = self._config.get("expansion_templates", {})
        base_template = templates.get("base", "")
        type_templates = templates.get("type_specific", {})
        
        if not base_template:
            error_msg = """
❌ 错误：字数扩写提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/word_count_enforcement_prompts.json
"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        base_prompt = base_template.format(
            needed=needed,
            content_preview=f"{content[:500]}...（省略中间内容）...{content[-200:]}",
            current_words=len(content)
        )
        
        type_specific = type_templates.get(expansion_type, type_templates.get("emotion", ""))
        
        return base_prompt + type_specific
    
    def _call_expansion_api(self, content: str, prompt: str) -> str:
        """调用API扩写"""
        if not self.api_client:
            raise ValueError("API client not available")
        
        # 🔥 从JSON配置加载system prompt
        system_prompt = self._config.get("system_prompt", "")
        if not system_prompt:
            error_msg = """
❌ 错误：字数扩写系统提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/word_count_enforcement_prompts.json
"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # 构建完整消息
        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        response = self.api_client.generate(messages=messages, temperature=0.7)
        return response.get("content", content)
    
    def _local_expansion(self, content: str, expansion_type: str, needed: int) -> str:
        """
        本地扩写（备用方案）
        
        通过插入模板内容来增加字数
        """
        # 简单策略：在关键位置插入扩写标记，让AI后续处理
        logger.warning(f"[WordEnforcer] 使用本地扩写策略")
        
        # 插入扩写提示
        expansion_markers = {
            "barrage": "\n【此处需扩写：弹幕三层反应】\n",
            "shock": "\n【此处需扩写：震惊三层递进】\n",
            "numbers": "\n【此处需扩写：数字可视化】\n",
            "emotion": "\n【此处需扩写：情绪渲染链】\n"
        }
        
        marker = expansion_markers.get(expansion_type, "")
        
        # 在高潮部分插入扩写标记
        # 找到最后30%的内容位置
        content_len = len(content)
        insert_pos = int(content_len * 0.7)
        
        # 在插入位置找到最近的段落结束点
        while insert_pos < content_len and content[insert_pos] not in ['\n', '。', '！']:
            insert_pos += 1
        
        expanded = content[:insert_pos] + marker + content[insert_pos:]
        
        return expanded
    
    def _extract_main_content(self, content: str) -> str:
        """提取正文内容（去除系统提示等）"""
        # 移除常见的非正文标记
        markers = [
            "---正文结束---",
            "【AI自检报告】",
            "【字数统计】",
            "【系统提示】"
        ]
        
        result = content
        for marker in markers:
            if marker in result:
                result = result.split(marker)[0]
        
        return result.strip()
    
    def get_word_count_distribution(self, content: str) -> Dict[str, int]:
        """
        分析字数分布
        
        返回各部分字数占比
        """
        total = len(content)
        
        # 分析结构
        paragraphs = content.split('\n\n')
        
        distribution = {
            "total": total,
            "paragraphs": len(paragraphs),
            "avg_paragraph_length": total // len(paragraphs) if paragraphs else 0,
            "dialogue_chars": len(re.findall(r'["""][^"""]*["""]', content)),
            "system_notifications": content.count("【叮"),
        }
        
        return distribution
    
    def suggest_paragraph_distribution(self, chapter_num: int, chapter_type: str) -> Dict:
        """
        建议段落字数分配
        
        根据章节类型给出最佳字数分配方案
        """
        distributions = {
            "SETUP": {
                "description": "铺垫章（压抑积蓄）",
                "sections": [
                    {"name": "开篇钩子", "words": 200, "percent": 10},
                    {"name": "困境升级", "words": 600, "percent": 27},
                    {"name": "反派嚣张", "words": 600, "percent": 27},
                    {"name": "情绪积蓄", "words": 500, "percent": 23},
                    {"name": "章尾钩子", "words": 300, "percent": 13},
                ]
            },
            "FACE_SLAP": {
                "description": "打脸章（爽点爆发）",
                "sections": [
                    {"name": "前情回顾", "words": 200, "percent": 9},
                    {"name": "反派继续嚣张", "words": 400, "percent": 18},
                    {"name": "主角反击", "words": 800, "percent": 36},
                    {"name": "震惊反应", "words": 500, "percent": 23},
                    {"name": "收获/展望", "words": 300, "percent": 14},
                ]
            },
            "REWARD": {
                "description": "收获章（系统奖励）",
                "sections": [
                    {"name": "战斗结束", "words": 200, "percent": 9},
                    {"name": "系统结算", "words": 600, "percent": 27},
                    {"name": "能力提升", "words": 600, "percent": 27},
                    {"name": "外界反应", "words": 500, "percent": 23},
                    {"name": "新目标", "words": 300, "percent": 14},
                ]
            }
        }
        
        return distributions.get(chapter_type, distributions["FACE_SLAP"])


# ==================== 便捷函数 ====================

def enforce_word_count(content: str, chapter_num: int, 
                       api_client=None,
                       min_words: int = 1800,
                       target_words: int = 2200) -> Tuple[str, bool, str]:
    """
    便捷函数：强制字数达标
    
    Returns:
        (final_content, success, message)
    """
    enforcer = WordCountEnforcer(api_client)
    
    # 检查字数
    is_valid, count, message = enforcer.check_word_count(content, chapter_num)
    
    if is_valid and count >= target_words:
        return content, True, f"字数达标（{count}字）"
    
    if count < min_words:
        # 必须扩写
        needed = target_words - count
        expanded = enforcer.expand_content(content, chapter_num, needed)
        new_count = len(expanded)
        
        if new_count >= min_words:
            return expanded, True, f"扩写完成（{count}→{new_count}字）"
        else:
            return expanded, False, f"扩写后仍不足（{new_count} < {min_words}）"
    
    # 字数在min和target之间，建议但不强制
    return content, True, f"字数可接受（{count}字），建议扩写到{target_words}字"
