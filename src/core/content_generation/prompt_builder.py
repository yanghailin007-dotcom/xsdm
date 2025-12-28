"""提示词构建器 - 专门负责生成各类提示词"""
import json
from typing import Dict, Optional
from src.utils.logger import get_logger


class PromptBuilder:
    """统一的提示词构建器 - 整合所有提示词生成逻辑"""
    
    def __init__(self, generator):
        self.logger = get_logger("PromptBuilder")
        self.generator = generator
    
    def build_character_prompt(self, plan, main_char_name=None):
        """构建核心角色提示词"""
        if not plan:
            return ""
        synopsis = plan.get("synopsis", "")
        system_info = plan.get("system", {})
        prompt = f"""作为一位优秀的角色设计专家，请根据以下小说方案，为主角 {main_char_name or '主角'} 设计详细的角色卡：
【小说方案摘要】
{synopsis}
【系统/金手指】
{json.dumps(system_info, ensure_ascii=False, indent=2)}
请为主角设计以下方面：
1. 人物基本信息（年龄、外貌、身份等）
2. 性格特点（3-5个核心性格特征）
3. 初始能力和背景
4. 核心目标和动机
5. 性格成长空间
返回JSON格式的角色卡。"""
        return prompt
    
    def build_consistency_prompt(self, context_dict):
        """构建一致性检查提示词"""
        prompt = f"""请根据以下上下文信息，提供内容一致性检查：
【已有信息】
{json.dumps(context_dict, ensure_ascii=False, indent=2)}
请检查：
1. 角色性格的一致性
2. 世界观的一致性
3. 情节逻辑的一致性
4. 语气风格的一致性
返回检查结果。"""
        return prompt