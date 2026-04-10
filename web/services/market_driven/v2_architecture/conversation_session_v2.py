# -*- coding: utf-8 -*-
"""
V2 六层架构对话会话类

支持 System Prompt 和 User Prompt 的分层管理
特别适配 V2 六层架构：
- System Prompt: Layer 1-4 (核心设定、战术规划、题材技法、文风)
- User Prompt: Layer 5-6 + 任务 (AI约束、自检清单、具体章节任务)
"""

import logging
from typing import Dict, List, Optional, Any, Iterator, Union
from dataclasses import dataclass, field


@dataclass
class LayeredSystemPrompt:
    """
    分层 System Prompt
    
    对应 V2 架构的 Layer 1-4
    """
    layer1_core_setting: str = ""      # 核心设定: 世界观、金手指、人设
    layer2_tactical_planning: str = "" # 战术规划: 阶段目标、情绪曲线
    layer3_genre_techniques: str = ""  # 题材技法: 国运文/神豪文特定规则
    layer4_writing_style: str = ""     # 文风技法: 快节奏、震惊流
    
    def combine(self, include_layers: List[int] = None) -> str:
        """
        组合指定层为完整 System Prompt
        
        Args:
            include_layers: 要包含的层号列表，如 [3, 4] 只包含题材技法+文风
                       None 表示包含所有层
        
        Returns:
            组合后的 System Prompt
        """
        if include_layers is None:
            include_layers = [1, 2, 3, 4]
        
        layers = {
            1: self.layer1_core_setting,
            2: self.layer2_tactical_planning,
            3: self.layer3_genre_techniques,
            4: self.layer4_writing_style
        }
        
        parts = []
        for layer_num in include_layers:
            if layer_num in layers and layers[layer_num]:
                parts.append(layers[layer_num])
        
        return "\n\n".join(parts)
    
    def update_layer(self, layer_num: int, content: str):
        """更新指定层的内容"""
        if layer_num == 1:
            self.layer1_core_setting = content
        elif layer_num == 2:
            self.layer2_tactical_planning = content
        elif layer_num == 3:
            self.layer3_genre_techniques = content
        elif layer_num == 4:
            self.layer4_writing_style = content


@dataclass
class LayeredUserPrompt:
    """
    分层 User Prompt
    
    对应 V2 架构的 Layer 5-6 + 具体任务
    """
    layer5_ai_constraints: str = ""    # AI约束: 字数、格式、情绪曲线
    layer6_self_check: str = ""        # 自检清单
    task_instruction: str = ""         # 具体任务指令
    
    def combine(self, include_layers: List[int] = None) -> str:
        """
        组合为完整 User Prompt
        
        Args:
            include_layers: 要包含的层号，如 [5] 只包含AI约束
        
        Returns:
            组合后的 User Prompt
        """
        if include_layers is None:
            include_layers = [5, 6]
        
        parts = []
        
        if 5 in include_layers and self.layer5_ai_constraints:
            parts.append(self.layer5_ai_constraints)
        
        if 6 in include_layers and self.layer6_self_check:
            parts.append(self.layer6_self_check)
        
        if self.task_instruction:
            parts.append(self.task_instruction)
        
        return "\n\n".join(parts)


class LayeredConversationSession:
    """
    V2 分层对话会话类
    
    特点:
    1. 支持 System Prompt 分层管理 (Layer 1-4)
    2. 支持 User Prompt 动态组合 (Layer 5-6 + 任务)
    3. 支持在对话过程中更新 System Prompt 的特定层
    4. 自动维护对话历史
    
    使用示例:
        # 创建分层 System Prompt
        system_prompt = LayeredSystemPrompt(
            layer3_genre_techniques="国运文技法...",
            layer4_writing_style="快节奏写法..."
        )
        
        # 创建会话
        session = LayeredConversationSession(
            api_client=api_client,
            system_prompt=system_prompt
        )
        
        # 发送消息（自动组合 User Prompt）
        user_prompt = LayeredUserPrompt(
            layer5_ai_constraints="字数2000...",
            task_instruction="生成第7章..."
        )
        response = session.send_message(user_prompt)
        
        # 更新 System Prompt 的某一层
        session.update_system_layer(3, "新的题材技法...")
    """
    
    def __init__(self, 
                 api_client: Any,
                 system_prompt: Union[str, LayeredSystemPrompt],
                 provider: Optional[str] = None,
                 model_name: Optional[str] = None,
                 temperature: float = 0.9,
                 purpose_prefix: str = "",
                 max_history: int = 20):
        """
        初始化分层对话会话
        
        Args:
            api_client: APIClient 实例
            system_prompt: System Prompt（字符串或 LayeredSystemPrompt）
            provider: 模型提供商
            model_name: 模型名称
            temperature: 温度参数
            purpose_prefix: 用途前缀
            max_history: 最大历史消息数
        """
        self.api_client = api_client
        self.provider = provider or api_client.default_provider
        self.model_name = model_name
        self.temperature = temperature
        self.purpose_prefix = purpose_prefix
        self.max_history = max_history
        
        # 初始化分层 System Prompt
        if isinstance(system_prompt, str):
            # 如果是字符串，默认放入 Layer 3（题材技法）
            self.system_prompt = LayeredSystemPrompt(layer3_genre_techniques=system_prompt)
        else:
            self.system_prompt = system_prompt
        
        # 构建初始 messages
        self._rebuild_messages()
        
        self.turn_count = 0
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"[V2对话会话] 创建成功 | 提供商: {self.provider} | 历史限制: {max_history}")
    
    def _rebuild_messages(self):
        """重建 messages 列表（System Prompt 更新后调用）"""
        system_content = self.system_prompt.combine()
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]
    
    def update_system_layer(self, layer_num: int, content: str, rebuild: bool = True):
        """
        更新 System Prompt 的指定层
        
        Args:
            layer_num: 层号 (1-4)
            content: 新内容
            rebuild: 是否立即重建 messages 列表
        
        注意:
            更新 System Prompt 会清空对话历史，因为 System Prompt 变化
            相当于开始了一个新对话
        """
        old_content = self.system_prompt.combine()
        self.system_prompt.update_layer(layer_num, content)
        
        if rebuild:
            new_content = self.system_prompt.combine()
            
            # 如果 System Prompt 有实质变化，清空历史（除了system消息）
            if new_content != old_content:
                self._rebuild_messages()
                self.logger.info(f"[V2对话会话] System Prompt Layer {layer_num} 已更新，历史已清空")
            else:
                # 只更新 system 消息
                self.messages[0]["content"] = new_content
    
    def send_message(self, 
                     user_prompt: Union[str, LayeredUserPrompt],
                     temperature: Optional[float] = None,
                     max_tokens: Optional[int] = None,
                     purpose: Optional[str] = None) -> Optional[str]:
        """
        发送消息并获取响应
        
        Args:
            user_prompt: User Prompt（字符串或 LayeredUserPrompt）
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            purpose: 用途标识
            
        Returns:
            模型响应内容
        """
        self.turn_count += 1
        temp = temperature if temperature is not None else self.temperature
        purpose_str = f"{self.purpose_prefix}_{purpose or f'轮次{self.turn_count}' }"
        
        # 组合 User Prompt
        if isinstance(user_prompt, str):
            user_content = user_prompt
        else:
            user_content = user_prompt.combine()
        
        # 添加用户消息到历史
        self.messages.append({"role": "user", "content": user_content})
        
        self.logger.info(f"[V2对话会话] 第 {self.turn_count} 轮 | 历史消息数: {len(self.messages)} | {purpose_str}")
        
        # 调用 API
        try:
            response = self.api_client._call_with_messages(
                messages=self.messages,
                provider=self.provider,
                temperature=temp,
                max_tokens=max_tokens,
                purpose=purpose_str
            )
            
            if response:
                # 添加助手响应到历史
                self.messages.append({"role": "assistant", "content": response})
                
                # 控制历史长度
                self._trim_history()
                
                return response
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"[V2对话会话] API调用失败: {e}")
            return None
    
    def send_message_stream(self, 
                           user_prompt: Union[str, LayeredUserPrompt],
                           temperature: Optional[float] = None,
                           max_tokens: Optional[int] = None) -> Iterator[str]:
        """
        流式发送消息
        
        Args:
            user_prompt: User Prompt
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            
        Yields:
            响应片段
        """
        self.turn_count += 1
        temp = temperature if temperature is not None else self.temperature
        
        # 组合 User Prompt
        if isinstance(user_prompt, str):
            user_content = user_prompt
        else:
            user_content = user_prompt.combine()
        
        # 添加用户消息
        self.messages.append({"role": "user", "content": user_content})
        
        # 流式调用
        full_response = ""
        for chunk in self.api_client._call_with_messages_stream(
            messages=self.messages,
            provider=self.provider,
            temperature=temp,
            max_tokens=max_tokens
        ):
            yield chunk
            full_response += chunk
        
        # 添加完整响应到历史
        self.messages.append({"role": "assistant", "content": full_response})
        self._trim_history()
    
    def _trim_history(self):
        """裁剪历史消息，保留 system + 最近 max_history 条"""
        if len(self.messages) > self.max_history + 1:
            # 保留 system 消息 + 最近 max_history 条
            self.messages = [self.messages[0]] + self.messages[-self.max_history:]
            self.logger.info(f"[V2对话会话] 历史已裁剪，保留最新 {self.max_history} 条")
    
    def clear_history(self, keep_system: bool = True):
        """
        清空对话历史
        
        Args:
            keep_system: 是否保留 System Prompt
        """
        if keep_system:
            system_msg = self.messages[0] if self.messages and self.messages[0]["role"] == "system" else None
            self.messages = [system_msg] if system_msg else []
        else:
            self.messages = []
        
        self.turn_count = 0
        self.logger.info(f"[V2对话会话] 历史已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        system_length = len(self.messages[0]["content"]) if self.messages else 0
        
        return {
            "turn_count": self.turn_count,
            "message_count": len(self.messages),
            "system_prompt_length": system_length,
            "system_layers": {
                "layer1": len(self.system_prompt.layer1_core_setting),
                "layer2": len(self.system_prompt.layer2_tactical_planning),
                "layer3": len(self.system_prompt.layer3_genre_techniques),
                "layer4": len(self.system_prompt.layer4_writing_style)
            }
        }


# ==================== 便捷函数 ====================

def create_layered_conversation(
    api_client: Any,
    genre: str,
    core_setting: Optional[str] = None,
    tactical_planning: Optional[str] = None,
    writing_style: Optional[str] = None,
    **kwargs
) -> LayeredConversationSession:
    """
    便捷函数：创建分层对话会话
    
    Args:
        api_client: APIClient 实例
        genre: 题材名称（用于加载 Layer 3 题材技法）
        core_setting: Layer 1 核心设定（可选）
        tactical_planning: Layer 2 战术规划（可选）
        writing_style: Layer 4 文风技法（可选）
        **kwargs: 其他参数传递给 LayeredConversationSession
    
    Returns:
        LayeredConversationSession 实例
    """
    from . import GenreTechniquesLoader, GenreTechniquesRenderer
    
    # 加载题材技法（Layer 3）
    loader = GenreTechniquesLoader()
    genre_tech = loader.load(genre)
    
    renderer = GenreTechniquesRenderer()
    layer3_content = renderer.render(genre_tech)
    
    # 构建分层 System Prompt
    system_prompt = LayeredSystemPrompt(
        layer1_core_setting=core_setting or "",
        layer2_tactical_planning=tactical_planning or "",
        layer3_genre_techniques=layer3_content,
        layer4_writing_style=writing_style or ""
    )
    
    return LayeredConversationSession(
        api_client=api_client,
        system_prompt=system_prompt,
        **kwargs
    )


# ==================== 测试代码 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("测试 V2 分层对话会话")
    print("=" * 80)
    
    # 测试 LayeredSystemPrompt
    print("\n【测试 LayeredSystemPrompt】")
    sys_prompt = LayeredSystemPrompt(
        layer3_genre_techniques="国运文技法：弹幕...",
        layer4_writing_style="快节奏写法..."
    )
    
    print(f"完整组合: {len(sys_prompt.combine())} 字符")
    print(f"仅 Layer 3: {len(sys_prompt.combine([3]))} 字符")
    print(f"Layer 3+4: {len(sys_prompt.combine([3, 4]))} 字符")
    
    # 测试 LayeredUserPrompt
    print("\n【测试 LayeredUserPrompt】")
    user_prompt = LayeredUserPrompt(
        layer5_ai_constraints="字数2000-2500...",
        task_instruction="生成第7章..."
    )
    
    print(f"完整组合: {len(user_prompt.combine())} 字符")
    print(f"仅 Layer 5: {len(user_prompt.combine([5]))} 字符")
    
    print("\n[OK] 测试完成")
