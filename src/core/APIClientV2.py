"""
APIClient V2 - 支持单次模式和会话模式的统一接口

两种模式：
1. 单次模式 (SingleCall): 直接调用，无状态，适用于独立任务
2. 会话模式 (Session): 维护上下文，多轮对话，适用于连贯创作

提供商适配：
- Kimi: 原生支持 messages 数组，使用官方多轮对话格式
- 其他(Gemini/Deepseek等): 使用 prompt 拼接模拟会话
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List, Iterator, Union
from enum import Enum
import json
import time
from dataclasses import dataclass, field


class CallMode(Enum):
    """调用模式"""
    SINGLE = "single"      # 单次调用
    SESSION = "session"    # 会话模式


@dataclass
class Message:
    """消息结构"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: float = field(default_factory=time.time)


class BaseSession(ABC):
    """
    会话基类 - 定义统一接口
    
    子类实现:
    - NativeSession: Kimi等原生支持会话的模型
    - SimulatedSession: 通过拼接模拟会话的模型
    """
    
    def __init__(self, api_client: Any, system_prompt: str,
                 provider: str, model_name: Optional[str] = None,
                 temperature: float = 0.8, max_history: int = 20):
        self.api_client = api_client
        self.system_prompt = system_prompt
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.max_history = max_history
        
        # 消息历史
        self.messages: List[Message] = [
            Message(role="system", content=system_prompt)
        ]
        self.turn_count = 0
        
    @abstractmethod
    def send(self, user_prompt: str, **kwargs) -> Optional[str]:
        """发送消息并获取响应"""
        pass
    
    @abstractmethod
    def send_stream(self, user_prompt: str, **kwargs) -> Iterator[str]:
        """流式发送消息"""
        pass
    
    def get_context_prompt(self) -> str:
        """
        获取上下文字符串（用于拼接模式）
        将历史消息格式化为文本
        """
        lines = []
        for msg in self.messages:
            if msg.role == "system":
                lines.append(f"[系统指令]\n{msg.content}\n")
            elif msg.role == "user":
                lines.append(f"[用户]\n{msg.content}\n")
            elif msg.role == "assistant":
                lines.append(f"[助手]\n{msg.content}\n")
        lines.append("[用户]\n")  # 准备接收新输入
        return "\n".join(lines)
    
    def add_to_history(self, user_msg: str, assistant_msg: str):
        """添加到历史"""
        self.messages.append(Message(role="user", content=user_msg))
        self.messages.append(Message(role="assistant", content=assistant_msg))
        self.turn_count += 1
        
        # 裁剪历史（保留 system + 最近 max_history 对对话）
        max_messages = 1 + self.max_history * 2  # system + N对问答
        if len(self.messages) > max_messages:
            self.messages = [self.messages[0]] + self.messages[-(self.max_history * 2):]
    
    def clear(self, keep_system: bool = True):
        """清空历史"""
        if keep_system:
            self.messages = [self.messages[0]]
        else:
            self.messages = []
        self.turn_count = 0
    
    def export_history(self) -> List[Dict]:
        """导出历史为字典列表"""
        return [{"role": m.role, "content": m.content} for m in self.messages]


class NativeSession(BaseSession):
    """
    原生会话模式 - 适用于 Kimi 等支持 messages 数组的 API
    直接传递 messages 数组，由模型维护上下文
    """
    
    def send(self, user_prompt: str, temperature: Optional[float] = None,
             max_tokens: Optional[int] = None, purpose: str = "") -> Optional[str]:
        """发送消息 - 使用原生 messages 格式"""
        
        # 添加用户消息
        self.messages.append(Message(role="user", content=user_prompt))
        
        # 调用底层 API（传递 messages 数组）
        response = self.api_client._call_native_session(
            messages=self.export_history(),
            provider=self.provider,
            model_name=self.model_name,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens,
            purpose=purpose
        )
        
        if response:
            # 添加助手响应到历史
            self.messages.append(Message(role="assistant", content=response))
            self.turn_count += 1
            
            # 裁剪历史
            self._trim_history()
            
        return response
    
    def send_stream(self, user_prompt: str, temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None) -> Iterator[str]:
        """流式发送"""
        self.messages.append(Message(role="user", content=user_prompt))
        
        full_response = ""
        for chunk in self.api_client._call_native_session_stream(
            messages=self.export_history(),
            provider=self.provider,
            model_name=self.model_name,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens
        ):
            full_response += chunk
            yield chunk
        
        if full_response:
            self.messages.append(Message(role="assistant", content=full_response))
            self.turn_count += 1
            self._trim_history()
    
    def _trim_history(self):
        """裁剪历史"""
        max_messages = 1 + self.max_history * 2
        if len(self.messages) > max_messages:
            self.messages = [self.messages[0]] + self.messages[-(self.max_history * 2):]


class SimulatedSession(BaseSession):
    """
    模拟会话模式 - 适用于 Gemini/Deepseek 等不原生支持会话的 API
    通过拼接历史消息到 prompt 中模拟上下文
    """
    
    def __init__(self, *args, context_format: str = "default", **kwargs):
        super().__init__(*args, **kwargs)
        self.context_format = context_format  # 拼接格式
        
    def _build_prompt(self, user_prompt: str) -> tuple:
        """
        构建带上下文的 prompt
        
        Returns:
            (system_prompt, user_prompt_with_context)
        """
        if len(self.messages) <= 1:
            # 第一轮，只有 system，直接返回
            return self.system_prompt, user_prompt
        
        # 构建上下文
        context_parts = []
        
        # 添加历史对话（跳过第一条 system）
        for msg in self.messages[1:]:
            if msg.role == "user":
                context_parts.append(f"用户：{msg.content}")
            elif msg.role == "assistant":
                context_parts.append(f"助手：{msg.content}")
        
        # 添加上下文说明
        context_str = "\n\n".join(context_parts)
        
        # 构建完整 prompt
        full_user_prompt = f"""以下是我们的对话历史：

{context_str}

---

用户新问题：{user_prompt}

请基于以上上下文回答。"""
        
        return self.system_prompt, full_user_prompt
    
    def send(self, user_prompt: str, temperature: Optional[float] = None,
             max_tokens: Optional[int] = None, purpose: str = "") -> Optional[str]:
        """发送消息 - 使用拼接方式"""
        
        # 构建带上下文的 prompt
        system_prompt, full_user_prompt = self._build_prompt(user_prompt)
        
        # 调用单次 API
        response = self.api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=full_user_prompt,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens,
            purpose=purpose
        )
        
        if response:
            # 记录到历史（使用原始 user_prompt，不是拼接后的）
            self.add_to_history(user_prompt, response)
        
        return response
    
    def send_stream(self, user_prompt: str, temperature: Optional[float] = None,
                   max_tokens: Optional[int] = None) -> Iterator[str]:
        """流式发送"""
        system_prompt, full_user_prompt = self._build_prompt(user_prompt)
        
        full_response = ""
        for chunk in self.api_client.call_api_stream(
            system_prompt=system_prompt,
            user_prompt=full_user_prompt,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens
        ):
            full_response += chunk
            yield chunk
        
        if full_response:
            self.add_to_history(user_prompt, full_response)


class SingleCallClient:
    """
    单次调用客户端 - 无状态，每次调用独立
    适用于：独立任务、批量处理、不需要上下文的场景
    """
    
    def __init__(self, api_client: Any):
        self.api_client = api_client
    
    def call(self, system_prompt: str, user_prompt: str,
             provider: Optional[str] = None,
             model_name: Optional[str] = None,
             temperature: float = 0.8,
             max_tokens: Optional[int] = None,
             purpose: str = "") -> Optional[str]:
        """
        单次调用
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            provider: 提供商（None使用默认）
            model_name: 模型名
            temperature: 温度
            max_tokens: 最大token
            purpose: 用途标识
            
        Returns:
            响应文本
        """
        return self.api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            purpose=purpose,
            provider=provider
        )
    
    def call_with_retry(self, system_prompt: str, user_prompt: str,
                       max_retries: int = 3,
                       **kwargs) -> Optional[str]:
        """带重试的单次调用"""
        for attempt in range(max_retries):
            result = self.call(system_prompt, user_prompt, **kwargs)
            if result:
                return result
            time.sleep(1 * (attempt + 1))
        return None


class SessionManager:
    """
    会话管理器 - 管理多个会话实例
    """
    
    def __init__(self, api_client: Any):
        self.api_client = api_client
        self.sessions: Dict[str, BaseSession] = {}
    
    def create(self, session_id: str, system_prompt: str,
               provider: Optional[str] = None,
               **kwargs) -> BaseSession:
        """
        创建新会话
        
        根据提供商自动选择会话类型：
        - kimi -> NativeSession
        - 其他 -> SimulatedSession
        """
        provider = provider or self.api_client.default_provider
        
        if provider.lower() == "kimi":
            session = NativeSession(
                api_client=self.api_client,
                system_prompt=system_prompt,
                provider=provider,
                **kwargs
            )
        else:
            session = SimulatedSession(
                api_client=self.api_client,
                system_prompt=system_prompt,
                provider=provider,
                **kwargs
            )
        
        self.sessions[session_id] = session
        return session
    
    def get(self, session_id: str) -> Optional[BaseSession]:
        """获取会话"""
        return self.sessions.get(session_id)
    
    def close(self, session_id: str):
        """关闭会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def close_all(self):
        """关闭所有会话"""
        self.sessions.clear()


# 兼容性：保持原有 APIClient 的接口
class APIClientFacade:
    """
    APIClient 外观类 - 提供统一的简洁接口
    
    使用示例:
        client = APIClientFacade(config)
        
        # 单次模式
        result = client.single.call("你是作家", "写第一章")
        
        # 会话模式
        session = client.session.create("novel_001", "你是作家", provider="kimi")
        chapter1 = session.send("写第一章")
        chapter2 = session.send("继续写第二章")  # 自动带上下文
    """
    
    def __init__(self, config: Dict):
        # 这里会初始化真实的 APIClient
        # from src.core.APIClient import APIClient
        # self._client = APIClient(config)
        pass
    
    @property
    def single(self) -> SingleCallClient:
        """获取单次调用客户端"""
        # return SingleCallClient(self._client)
        pass
    
    @property  
    def session(self) -> SessionManager:
        """获取会话管理器"""
        # return SessionManager(self._client)
        pass


if __name__ == "__main__":
    # 测试代码
    print("APIClient V2 设计完成")
    print("\n使用模式:")
    print("1. 单次模式: client.single.call(system, user)")
    print("2. 会话模式: session = client.session.create(id, system)")
    print("            session.send(user)")
