"""
短篇爆款拆解器
通过 3 轮 API 调用，将参考文本拆解为可复用的套路模板
"""

import json
import logging
from typing import Dict, Optional

from .models import TropeTemplate
from .prompt_builder import ShortStoryPromptBuilder

logger = logging.getLogger(__name__)


class ShortStoryDeconstructor:
    """短篇爆款拆解器"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.prompt_builder = ShortStoryPromptBuilder()
    
    def deconstruct(self, reference_text: str, 
                   protagonist_replacement: str = "",
                   era_replacement: str = "") -> TropeTemplate:
        """
        3 轮拆解参考文本，输出套路模板
        """
        logger.info("[Deconstructor] 开始拆解参考文本...")
        
        # Round 1: 结构拆解
        structure_analysis = self._round_1_structure(reference_text)
        logger.info("[Deconstructor] 结构拆解完成")
        
        # Round 2: 人设与名场面提取
        elements_analysis = self._round_2_elements(reference_text, structure_analysis)
        logger.info("[Deconstructor] 人设提取完成")
        
        # Round 3: 生成套路模板
        template_data = self._round_3_template(
            reference_text, structure_analysis, elements_analysis,
            protagonist_replacement, era_replacement
        )
        logger.info("[Deconstructor] 套路模板生成完成")
        
        return self._build_trope_template(template_data)
    
    def _round_1_structure(self, reference_text: str) -> Dict:
        """第一轮：结构拆解"""
        prompt = self.prompt_builder.get_deconstruction_prompt(
            "round_1_structure",
            reference_text=reference_text
        )
        response = self._call_api(prompt, "短篇结构拆解")
        return self._parse_json(response)
    
    def _round_2_elements(self, reference_text: str, structure_analysis: Dict) -> Dict:
        """第二轮：人设与名场面提取"""
        prompt = self.prompt_builder.get_deconstruction_prompt(
            "round_2_elements",
            reference_text=reference_text,
            structure_analysis=json.dumps(structure_analysis, ensure_ascii=False, indent=2)
        )
        response = self._call_api(prompt, "人设名场面提取")
        return self._parse_json(response)
    
    def _round_3_template(self, reference_text: str, structure_analysis: Dict,
                         elements_analysis: Dict, protagonist_replacement: str,
                         era_replacement: str) -> Dict:
        """第三轮：生成套路模板"""
        prompt = self.prompt_builder.get_deconstruction_prompt(
            "round_3_template",
            reference_text=reference_text,
            structure_analysis=json.dumps(structure_analysis, ensure_ascii=False, indent=2),
            elements_analysis=json.dumps(elements_analysis, ensure_ascii=False, indent=2),
            protagonist_replacement=protagonist_replacement or "保持原设定",
            era_replacement=era_replacement or "保持原时代"
        )
        response = self._call_api(prompt, "套路模板生成")
        return self._parse_json(response)
    
    def _call_api(self, prompt: str, purpose: str) -> str:
        """调用 API"""
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="general_writing",
                user_prompt=prompt,
                purpose=purpose
            )
            return result or ""
        except Exception as e:
            logger.error(f"[Deconstructor] API 调用失败 [{purpose}]: {e}")
            raise
    
    def _parse_json(self, text: str) -> Dict:
        """解析 JSON 响应，支持从 markdown 代码块提取"""
        if not text:
            return {}
        
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试从 markdown 代码块提取
        import re
        patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue
        
        logger.warning(f"[Deconstructor] JSON 解析失败，返回原始文本: {text[:200]}")
        return {"raw_text": text}
    
    def _build_trope_template(self, data: Dict) -> TropeTemplate:
        """从解析结果构建 TropeTemplate"""
        return TropeTemplate(
            genre=data.get("genre", ""),
            core_conflict=data.get("core_conflict", ""),
            protagonist_tag=data.get("protagonist_tag", ""),
            antagonist_tag=data.get("antagonist_tag", ""),
            opening_formula=data.get("opening_formula", ""),
            turning_points=data.get("turning_points", []),
            payoff_scenes=data.get("payoff_scenes", []),
            ending_formula=data.get("ending_formula", ""),
            hot_keywords=data.get("hot_keywords", [])
        )
