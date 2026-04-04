"""
小说生成专用会话基类

在 ConversationSession 基础上增加：
1. Domain 角色定位
2. Context Brief 输入
3. 自约束机制
4. 结构化输出解析增强
5. 会话结束时自动生成 Brief 摘要
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any

from src.core.APIClient import ConversationSession
from src.utils.logger import get_logger


class NovelGenerationSession(ConversationSession):
    """
    小说生成专用多轮对话会话基类
    
    Args:
        api_client: APIClient 实例
        domain: 创作域名称，如 "foundation", "character", "structure", "writing"
        context_briefs: 上游会话传来的 Context Brief 列表
        novel_data: 当前小说的基础数据
        provider: 模型提供商
        model_name: 模型名称
        temperature: 默认温度参数
    """

    # 子类必须定义自己负责的步骤列表（用于进度映射）
    STEPS: List[str] = []

    def __init__(
        self,
        api_client,
        domain: str,
        context_briefs: Optional[List[str]] = None,
        novel_data: Optional[Dict] = None,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
    ):
        self.domain = domain
        self.context_briefs = context_briefs or []
        self.novel_data = novel_data or {}
        self.session_logger = get_logger(f"Session.{domain}")
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        super().__init__(
            api_client=api_client,
            system_prompt=system_prompt,
            provider=provider,
            model_name=model_name,
            temperature=temperature,
            purpose_prefix=f"session_{domain}",
        )
        
        self.session_logger.info(
            f"[{domain}] 会话已创建 | 模型: {model_name or 'default'} | "
            f"上游 briefs: {len(self.context_briefs)} | 历史限制: {self.max_history}"
        )

    # ------------------------------------------------------------------
    # 系统提示词构建
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        """构建包含领域角色、约束机制和上下文 brief 的系统提示词"""
        parts = []
        
        # 1. 角色定位
        parts.append(self._get_role_prompt())
        
        # 2. 小说基础信息
        parts.append(self._get_novel_info_prompt())
        
        # 3. 上游 Context Briefs
        if self.context_briefs:
            parts.append(self._get_context_briefs_prompt())
        
        # 4. 自约束机制
        parts.append(self._get_constraint_prompt())
        
        # 5. 输出格式要求
        parts.append(self._get_output_format_prompt())
        
        return "\n\n".join(parts)

    def _get_role_prompt(self) -> str:
        """子类可覆盖，返回该域的专家角色描述"""
        return f"""# 角色定位
你是一位顶级的网络小说{self._get_domain_chinese_name()}专家。
你的任务是在当前创作域内完成最专业的设定工作，确保输出高质量、一致、可执行的内容。"""

    def _get_domain_chinese_name(self) -> str:
        mapping = {
            "foundation": "世界观与风格",
            "character": "角色与叙事",
            "structure": "结构规划",
            "writing": "执笔创作",
        }
        return mapping.get(self.domain, "创作")

    def _get_novel_info_prompt(self) -> str:
        title = self.novel_data.get("novel_title", "未命名")
        synopsis = self.novel_data.get("novel_synopsis", "暂无简介")
        category = self.novel_data.get("category", "未分类")
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        
        return f"""## 小说基础信息
- **书名**: {title}
- **类型**: {category}
- **总章节数**: {total_chapters}
- **简介**: {synopsis}"""

    def _get_context_briefs_prompt(self) -> str:
        briefs_text = []
        for i, brief in enumerate(self.context_briefs, 1):
            briefs_text.append(f"--- 上游摘要 {i} ---\n{brief}")
        
        joined_briefs = "\n\n".join(briefs_text)
        
        return f"""## 上游创作域摘要（已确定，不可修改）
以下内容是前面创作域已经确定的结果，你只能引用，不能修改。
如果当前域的设定与以下内容冲突，请在输出中明确标注冲突点。

{joined_briefs}"""

    def _get_constraint_prompt(self) -> str:
        return """## 当前会话规则（必须遵守）
1. 你只能修改当前创作域负责的内容，不能越域修改上游已确定的设定。
2. 对于上游 Context Brief，你只能引用，不能修改。
3. 如果你发现当前域的设定与上游摘要冲突，请在输出开头用【冲突标注】列出冲突点，而不是擅自修改上游设定。
4. 所有输出必须是合法的 JSON 格式（除非明确允许纯文本）。
5. 使用中文，符合中国网文市场特点。
6. 每轮输出后，请在 JSON 内增加一个字段 `_round_summary`，用 1-2 句话总结本轮对设定的关键变更（该字段不会被持久化，仅用于调试）。"""

    def _get_output_format_prompt(self) -> str:
        return """## 输出格式要求
- 默认输出合法 JSON。
- 不要在 JSON 外包裹 Markdown 代码块标记（如 ```json）。
- 确保所有字符串使用双引号。
- 不要出现尾随逗号。"""

    # ------------------------------------------------------------------
    # 结构化对话方法
    # ------------------------------------------------------------------
    def send_structured_message(
        self,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        purpose: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        发送消息并尝试将响应解析为 JSON
        
        相比 send_message，增加了多层容错解析。
        """
        response = self.send_message(
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            purpose=purpose,
        )
        
        if not response:
            self.session_logger.error(f"[{self.domain}] API 返回空响应")
            return None
        
        return self._parse_json_response(response, purpose or "structured_msg")

    def _parse_json_response(
        self,
        response: str,
        purpose: str,
    ) -> Optional[Dict[str, Any]]:
        """多层容错 JSON 解析"""
        cleaned = response.strip().lstrip('\ufeff')
        
        parsers = [
            ("直接解析", lambda s: json.loads(s)),
            ("代码块提取", lambda s: json.loads(re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', s, re.DOTALL).group(1).strip())),
            ("括号匹配", self._extract_json_by_braces),
            ("宽松匹配", self._extract_json_loose),
        ]
        
        for name, parser in parsers:
            try:
                result = parser(cleaned)
                if isinstance(result, dict):
                    # 移除调试用的 _round_summary
                    result.pop("_round_summary", None)
                    return result
            except Exception as e:
                self.session_logger.debug(f"[{self.domain}] {name} 失败: {e}")
                continue
        
        # 全部失败，保存调试文件
        self._save_parse_error(cleaned, purpose)
        return None

    @staticmethod
    def _extract_json_by_braces(text: str) -> Dict:
        start = text.find('{')
        if start == -1:
            raise ValueError("未找到 JSON 对象起始位置")
        brace_count = 0
        end = start
        for i, char in enumerate(text[start:]):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = start + i + 1
                    break
        return json.loads(text[start:end])

    @staticmethod
    def _extract_json_loose(text: str) -> Dict:
        match = re.search(r'\{[\s\S]*\}', text)
        if not match:
            raise ValueError("未找到 JSON 对象")
        json_str = re.sub(r',(\s*[}\]])', r'\1', match.group(0))
        return json.loads(json_str)

    def _save_parse_error(self, raw_response: str, purpose: str):
        """保存 JSON 解析失败的内容供调试"""
        try:
            debug_dir = Path("debug_responses") / "session_mode"
            debug_dir.mkdir(parents=True, exist_ok=True)
            timestamp = int(time.time())
            file_path = debug_dir / f"parse_error_{self.domain}_{purpose}_{timestamp}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Domain: {self.domain}\nPurpose: {purpose}\n\n")
                f.write(raw_response)
            self.session_logger.warning(f"[{self.domain}] 解析失败响应已保存: {file_path}")
        except Exception as e:
            self.session_logger.error(f"[{self.domain}] 保存解析失败响应时出错: {e}")

    # ------------------------------------------------------------------
    # Context Brief 生成
    # ------------------------------------------------------------------
    def generate_brief(self, session_results: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        会话结束时，调用 LLM 生成本域的 Context Brief 摘要。
        
        Args:
            session_results: 本会话产出的所有结构化结果
            
        Returns:
            Context Brief 文本，供下游会话使用
        """
        prompt = self._build_brief_generation_prompt(session_results)
        
        self.session_logger.info(f"[{self.domain}] 正在生成 Context Brief...")
        
        # 生成 Brief 时使用较低 temperature，确保信息密度和准确性
        brief = self.send_message(
            user_prompt=prompt,
            temperature=0.5,
            purpose="generate_brief",
        )
        
        if brief:
            # 清理可能的代码块标记
            brief = re.sub(r'^```(?:markdown)?\s*|\s*```$', '', brief, flags=re.MULTILINE).strip()
            self.session_logger.info(f"[{self.domain}] Context Brief 生成完成，长度: {len(brief)} 字符")
            return brief
        
        self.session_logger.error(f"[{self.domain}] Context Brief 生成失败")
        return None

    def _build_brief_generation_prompt(self, session_results: Optional[Dict[str, Any]]) -> str:
        """构建 Brief 生成提示词，子类可覆盖以控制摘要重点"""
        return f"""
当前 {self._get_domain_chinese_name()} 会话已经完成。

请基于本会话的所有对话内容和输出结果，生成一份精炼的【Context Brief】（上下文摘要），
供下游创作域的专家在后续步骤中引用。

## 要求
1. 只保留对下游创作域**最关键**的约束和信息。
2. 使用自然语言，条理清晰，分点列出。
3. 明确标注哪些是"硬性约束"（不可修改），哪些是"参考信息"。
4. 长度控制在 1500~2500 个汉字之间。
5. 不要包含 JSON 格式，使用 Markdown 标题和列表即可。

## 输出格式
# {self._get_domain_chinese_name()}摘要

## 硬性约束
...

## 核心设定
...

## 参考信息
...
"""

    # ------------------------------------------------------------------
    # 步骤进度映射（供外部使用）
    # ------------------------------------------------------------------
    def get_steps(self) -> List[str]:
        """返回本会话负责的标准步骤列表"""
        return self.STEPS

    def get_step_count(self) -> int:
        """返回本会话包含的标准步骤数"""
        return len(self.STEPS)
