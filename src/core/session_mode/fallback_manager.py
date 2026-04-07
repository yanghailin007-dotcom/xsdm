"""
回退管理器 - 处理 Session 失败时的自动降级
===========================================

提供功能：
1. Session 执行失败时自动降级到传统模式
2. 支持手动配置各 Session 的执行模式
3. 记录失败原因和回退历史
4. 支持检查点恢复后的模式选择

使用示例：
    from src.core.session_mode.fallback_manager import FallbackManager, ExecutionMode
    
    fallback_mgr = FallbackManager(config)
    
    # 执行 Session，失败时自动降级
    result = fallback_mgr.execute_with_fallback(
        session_name="foundation_planning",
        conversation_func=lambda: foundation_session.execute(),
        traditional_func=lambda: phase_generator._generate_foundation_planning()
    )
"""

import json
import logging
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    AUTO = "auto"           # 自动选择，优先对话模式
    CONVERSATION = "conversation"  # 强制使用对话模式
    TRADITIONAL = "traditional"    # 强制使用传统模式
    HYBRID = "hybrid"       # 混合模式（部分步骤对话）


class FallbackReason(Enum):
    """回退原因"""
    EXECUTION_ERROR = "execution_error"      # 执行出错
    VALIDATION_FAILED = "validation_failed"  # 验证失败
    TIMEOUT = "timeout"                      # 超时
    USER_REQUEST = "user_request"           # 用户请求
    CONFIG_FORCED = "config_forced"         # 配置强制
    CHECKPOINT_RESUME = "checkpoint_resume" # 检查点恢复


@dataclass
class FallbackRecord:
    """回退记录"""
    session_name: str
    timestamp: str
    original_mode: ExecutionMode
    fallback_mode: ExecutionMode
    reason: FallbackReason
    error_message: str = ""
    duration_ms: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "session_name": self.session_name,
            "timestamp": self.timestamp,
            "original_mode": self.original_mode.value,
            "fallback_mode": self.fallback_mode.value,
            "reason": self.reason.value,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms
        }


@dataclass
class SessionConfig:
    """Session 配置"""
    mode: ExecutionMode = ExecutionMode.AUTO
    max_retries: int = 1
    timeout_seconds: int = 600  # 10分钟超时
    fallback_on_validation_error: bool = True
    fallback_on_timeout: bool = True
    
    def to_dict(self) -> Dict:
        return {
            "mode": self.mode.value,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "fallback_on_validation_error": self.fallback_on_validation_error,
            "fallback_on_timeout": self.fallback_on_timeout
        }


class FallbackManager:
    """
    回退管理器
    
    管理各 Session 的执行模式和回退策略
    """
    
    # 默认配置
    DEFAULT_CONFIG = {
        "foundation_planning": SessionConfig(
            mode=ExecutionMode.AUTO,
            timeout_seconds=900  # 15分钟
        ),
        "character_narrative": SessionConfig(
            mode=ExecutionMode.AUTO,
            timeout_seconds=900
        ),
        "structure_planning": SessionConfig(
            mode=ExecutionMode.AUTO,
            timeout_seconds=1800  # 30分钟（阶段详细计划可能较慢）
        ),
        "expectation_system": SessionConfig(
            mode=ExecutionMode.AUTO,
            timeout_seconds=600
        ),
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化回退管理器
        
        Args:
            config: 配置字典，格式为 {session_name: SessionConfig}
        """
        self.session_configs: Dict[str, SessionConfig] = {}
        self.fallback_history: List[FallbackRecord] = []
        self.execution_stats: Dict[str, Dict] = {}
        
        # 加载默认配置
        for session_name, default_config in self.DEFAULT_CONFIG.items():
            self.session_configs[session_name] = SessionConfig(
                **default_config.to_dict()
            )
        
        # 覆盖用户配置
        if config:
            for session_name, session_config in config.items():
                if isinstance(session_config, dict):
                    self.session_configs[session_name] = SessionConfig(**session_config)
                elif isinstance(session_config, SessionConfig):
                    self.session_configs[session_name] = session_config
        
        logger.info(f"FallbackManager 初始化完成，管理 {len(self.session_configs)} 个 Session")
    
    def get_session_config(self, session_name: str) -> SessionConfig:
        """获取 Session 配置"""
        return self.session_configs.get(session_name, SessionConfig())
    
    def set_session_mode(self, session_name: str, mode: ExecutionMode):
        """设置 Session 执行模式"""
        if session_name not in self.session_configs:
            self.session_configs[session_name] = SessionConfig()
        self.session_configs[session_name].mode = mode
        logger.info(f"设置 {session_name} 执行模式为 {mode.value}")
    
    def execute_with_fallback(
        self,
        session_name: str,
        conversation_func: Callable[[], Any],
        traditional_func: Callable[[], Any],
        validator_func: Optional[Callable[[Any], bool]] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Tuple[bool, Any, ExecutionMode]:
        """
        执行 Session，失败时自动降级
        
        Args:
            session_name: Session 名称
            conversation_func: 对话模式执行函数
            traditional_func: 传统模式执行函数
            validator_func: 可选的验证函数
            progress_callback: 进度回调
            
        Returns:
            Tuple[成功状态, 结果, 实际执行模式]
        """
        config = self.get_session_config(session_name)
        start_time = datetime.now()
        
        # 根据配置决定执行模式
        if config.mode == ExecutionMode.TRADITIONAL:
            logger.info(f"[{session_name}] 配置强制使用传统模式")
            result = traditional_func()
            duration = (datetime.now() - start_time).total_seconds() * 1000
            self._record_execution(session_name, ExecutionMode.TRADITIONAL, True, duration)
            return True, result, ExecutionMode.TRADITIONAL
        
        if config.mode == ExecutionMode.CONVERSATION:
            logger.info(f"[{session_name}] 配置强制使用对话模式")
            try:
                result = conversation_func()
                
                # 验证结果
                if validator_func and not validator_func(result):
                    if config.fallback_on_validation_error:
                        logger.warning(f"[{session_name}] 对话模式验证失败，但配置强制使用对话模式")
                    else:
                        raise ValueError("验证失败")
                
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self._record_execution(session_name, ExecutionMode.CONVERSATION, True, duration)
                return True, result, ExecutionMode.CONVERSATION
                
            except Exception as e:
                logger.error(f"[{session_name}] 对话模式执行失败: {e}")
                # 即使失败也不回退，因为配置强制使用对话模式
                duration = (datetime.now() - start_time).total_seconds() * 1000
                self._record_execution(session_name, ExecutionMode.CONVERSATION, False, duration)
                raise
        
        # AUTO 或 HYBRID 模式：优先尝试对话模式
        logger.info(f"[{session_name}] 尝试使用对话模式...")
        
        if progress_callback:
            progress_callback(session_name, 10, f"尝试使用对话模式生成...")
        
        try:
            result = conversation_func()
            
            # 验证结果
            if validator_func:
                if progress_callback:
                    progress_callback(session_name, 80, "验证产物格式...")
                
                if not validator_func(result):
                    if config.fallback_on_validation_error:
                        logger.warning(f"[{session_name}] 对话模式产物验证失败，降级到传统模式")
                        self._record_fallback(
                            session_name, ExecutionMode.CONVERSATION,
                            ExecutionMode.TRADITIONAL, FallbackReason.VALIDATION_FAILED,
                            "产物格式验证失败"
                        )
                        
                        if progress_callback:
                            progress_callback(session_name, 85, "验证失败，降级到传统模式...")
                        
                        result = traditional_func()
                        duration = (datetime.now() - start_time).total_seconds() * 1000
                        self._record_execution(session_name, ExecutionMode.TRADITIONAL, True, duration)
                        return True, result, ExecutionMode.TRADITIONAL
                    else:
                        raise ValueError("产物格式验证失败且不允许回退")
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"[{session_name}] 对话模式执行成功，耗时 {duration:.0f}ms")
            self._record_execution(session_name, ExecutionMode.CONVERSATION, True, duration)
            return True, result, ExecutionMode.CONVERSATION
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{session_name}] 对话模式执行失败: {error_msg}")
            
            if progress_callback:
                progress_callback(session_name, 85, f"对话模式失败: {error_msg[:50]}...")
            
            # 降级到传统模式
            logger.info(f"[{session_name}] 降级到传统模式...")
            
            if progress_callback:
                progress_callback(session_name, 90, "降级到传统模式...")
            
            try:
                result = traditional_func()
                duration = (datetime.now() - start_time).total_seconds() * 1000
                
                self._record_fallback(
                    session_name, ExecutionMode.CONVERSATION,
                    ExecutionMode.TRADITIONAL, FallbackReason.EXECUTION_ERROR,
                    error_msg, int(duration)
                )
                
                logger.info(f"[{session_name}] 传统模式执行成功")
                self._record_execution(session_name, ExecutionMode.TRADITIONAL, True, duration)
                return True, result, ExecutionMode.TRADITIONAL
                
            except Exception as e2:
                duration = (datetime.now() - start_time).total_seconds() * 1000
                logger.error(f"[{session_name}] 传统模式也失败: {e2}")
                self._record_execution(session_name, ExecutionMode.TRADITIONAL, False, duration)
                raise RuntimeError(f"{session_name} 对话模式和传统模式都失败: {e2}")
    
    def execute_batch_with_fallback(
        self,
        sessions: List[Tuple[str, Callable, Callable]],
        global_validator: Optional[Callable[[str, Any], bool]] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Tuple[bool, Any, ExecutionMode]]:
        """
        批量执行多个 Session
        
        Args:
            sessions: [(session_name, conversation_func, traditional_func), ...]
            global_validator: 全局验证函数
            progress_callback: 进度回调
            
        Returns:
            {session_name: (success, result, mode)}
        """
        results = {}
        
        for session_name, conv_func, trad_func in sessions:
            validator = None
            if global_validator:
                validator = lambda result, sn=session_name: global_validator(sn, result)
            
            try:
                success, result, mode = self.execute_with_fallback(
                    session_name, conv_func, trad_func, validator, progress_callback
                )
                results[session_name] = (success, result, mode)
            except Exception as e:
                logger.error(f"[{session_name}] 执行失败: {e}")
                results[session_name] = (False, None, ExecutionMode.AUTO)
        
        return results
    
    def _record_fallback(
        self,
        session_name: str,
        original_mode: ExecutionMode,
        fallback_mode: ExecutionMode,
        reason: FallbackReason,
        error_message: str = "",
        duration_ms: int = 0
    ):
        """记录回退事件"""
        record = FallbackRecord(
            session_name=session_name,
            timestamp=datetime.now().isoformat(),
            original_mode=original_mode,
            fallback_mode=fallback_mode,
            reason=reason,
            error_message=error_message,
            duration_ms=duration_ms
        )
        self.fallback_history.append(record)
        logger.warning(f"记录回退事件: {session_name} 从 {original_mode.value} 回退到 {fallback_mode.value}")
    
    def _record_execution(
        self,
        session_name: str,
        mode: ExecutionMode,
        success: bool,
        duration_ms: float
    ):
        """记录执行统计"""
        if session_name not in self.execution_stats:
            self.execution_stats[session_name] = {
                "total_executions": 0,
                "success_count": 0,
                "failure_count": 0,
                "conversation_count": 0,
                "traditional_count": 0,
                "total_duration_ms": 0
            }
        
        stats = self.execution_stats[session_name]
        stats["total_executions"] += 1
        stats["total_duration_ms"] += duration_ms
        
        if success:
            stats["success_count"] += 1
        else:
            stats["failure_count"] += 1
        
        if mode == ExecutionMode.CONVERSATION:
            stats["conversation_count"] += 1
        elif mode == ExecutionMode.TRADITIONAL:
            stats["traditional_count"] += 1
    
    def get_fallback_history(self) -> List[FallbackRecord]:
        """获取回退历史"""
        return self.fallback_history.copy()
    
    def get_execution_stats(self) -> Dict[str, Dict]:
        """获取执行统计"""
        return self.execution_stats.copy()
    
    def generate_report(self) -> str:
        """生成执行报告"""
        lines = [
            "=" * 80,
            "FallbackManager 执行报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]
        
        # 回退历史
        if self.fallback_history:
            lines.append("📊 回退历史:")
            for record in self.fallback_history:
                lines.append(
                    f"  - {record.session_name}: {record.original_mode.value} → "
                    f"{record.fallback_mode.value} ({record.reason.value})"
                )
        else:
            lines.append("✅ 无回退记录")
        
        lines.append("")
        
        # 执行统计
        if self.execution_stats:
            lines.append("📈 执行统计:")
            for session_name, stats in self.execution_stats.items():
                total = stats["total_executions"]
                success_rate = (stats["success_count"] / total * 100) if total > 0 else 0
                avg_duration = (stats["total_duration_ms"] / total / 1000) if total > 0 else 0
                
                lines.append(f"\n  【{session_name}】")
                lines.append(f"    总执行次数: {total}")
                lines.append(f"    成功率: {success_rate:.1f}%")
                lines.append(f"    对话模式: {stats['conversation_count']} 次")
                lines.append(f"    传统模式: {stats['traditional_count']} 次")
                lines.append(f"    平均耗时: {avg_duration:.1f} 秒")
        
        lines.append("")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def save_report(self, filepath: str):
        """保存报告到文件"""
        report = self.generate_report()
        Path(filepath).write_text(report, encoding='utf-8')
        logger.info(f"报告已保存到: {filepath}")
    
    def reset_stats(self):
        """重置统计"""
        self.fallback_history.clear()
        self.execution_stats.clear()
        logger.info("统计已重置")


# =============================================================================
# 便捷函数
# =============================================================================

def create_fallback_manager_from_config(config_dict: Dict[str, Any]) -> FallbackManager:
    """
    从配置字典创建 FallbackManager
    
    配置示例:
        {
            "foundation_planning": {
                "mode": "auto",
                "timeout_seconds": 900
            },
            "character_narrative": {
                "mode": "conversation"  # 强制使用对话模式
            },
            "structure_planning": {
                "mode": "traditional"   # 强制使用传统模式
            }
        }
    """
    parsed_config = {}
    
    for session_name, session_config in config_dict.items():
        if isinstance(session_config, dict):
            # 解析 mode
            mode_str = session_config.get("mode", "auto")
            mode = ExecutionMode(mode_str)
            
            parsed_config[session_name] = SessionConfig(
                mode=mode,
                max_retries=session_config.get("max_retries", 1),
                timeout_seconds=session_config.get("timeout_seconds", 600),
                fallback_on_validation_error=session_config.get(
                    "fallback_on_validation_error", True
                ),
                fallback_on_timeout=session_config.get(
                    "fallback_on_timeout", True
                )
            )
    
    return FallbackManager(parsed_config)


def get_default_fallback_manager() -> FallbackManager:
    """获取默认配置的 FallbackManager"""
    return FallbackManager()
