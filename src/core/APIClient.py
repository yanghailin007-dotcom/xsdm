"""API客户端类 - 配置驱动，稳定JSON解析版本"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import re
import time
import requests
import os
from typing import Optional, Any, Dict, Iterator, List, Tuple
from datetime import datetime
from src.utils.logger import get_logger
from src.prompts.Prompts import Prompts

class APIClient:
    def __init__(self, config):
        self.logger = get_logger("APIClient")
        self.config = config
        self.Prompts = Prompts()
        self.request_times = []
        # 频率限制相关属性 - 安全访问配置
        rate_limit_config = self.config.get("rate_limit", {})
        self.rate_limit_enabled = rate_limit_config.get("enabled", False)
        self.rate_limit_interval = rate_limit_config.get("interval", 20)
        self.rate_limit_max_requests = rate_limit_config.get("max_requests", 1)
        self.last_request_time = 0  # 上次请求时间戳
        self.request_count = 0      # 当前间隔内的请求计数
        # 从配置中获取默认提供商
        self.default_provider = self.config.get("default_provider", "gemini")
        self.available_providers = self._get_available_providers()
        # 加载模型路由配置
        self.model_routing_enabled = self.config.get("model_routing", {}).get("enabled", False)
        self.model_routes = self.config.get("model_routing", {}).get("routes", {})
        self.default_routed_model = self.config.get("model_routing", {}).get("default_model", None)
        if self.model_routing_enabled:
            self.logger.info(f"🔄 模型路由: 已启用 (配置了 {len(self.model_routes)} 个路由)")
        # 验证默认提供商是否可用
        if self.default_provider not in self.available_providers:
            if self.available_providers:
                self.default_provider = self.available_providers[0]
                self.logger.info(f"⚠️ 配置的默认提供商不可用，已切换到: {self.default_provider}")
            else:
                self.logger.info("❌ 没有可用的AI服务提供商")
        self.logger.info(f"✓ 默认使用: {self.default_provider.upper()}") 
        self.logger.info(f"✓ 可用提供商: {self.available_providers}")
        # 显示频率限制状态
        if self.rate_limit_enabled:
            self.logger.info(f"⏰ 频率限制: 启用 ({self.rate_limit_interval}秒内最多{self.rate_limit_max_requests}次请求)")
        else:
            self.logger.info("⏰ 频率限制: 禁用")
        # 加载网站风格适配配置
        self.website_style_enabled = self.config.get("website_style_adaptation", {}).get("enabled", False)
        self.website_style_text = self.config.get("website_style_adaptation", {}).get("text", "")
        if self.website_style_enabled and self.website_style_text:
            self.logger.info(f"🌐 网站风格适配: 启用 - 最高优先级风格要求: '{self.website_style_text}'")
        # 创建调试目录
        self.debug_dir = "debug_responses"
        os.makedirs(self.debug_dir, exist_ok=True)
        # 创建提示词优化目录
        self.optimized_prompts_dir = "optimized_prompts"
        os.makedirs(self.optimized_prompts_dir, exist_ok=True)
        # 加载已优化的提示词
        self.optimized_prompts = self._load_optimized_prompts()
    def _check_rate_limit(self) -> bool:
        """检查频率限制，如果需要等待则返回True"""
        if not self.rate_limit_enabled:
            self.logger.debug("🔓 频率限制: 已禁用，跳过检查")
            return False
        
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # 详细日志：当前状态
        self.logger.info(f"🔍 频率限制检查:")
        self.logger.info(f"   - 当前时间: {current_time:.2f}")
        self.logger.info(f"   - 上次请求时间: {self.last_request_time:.2f}")
        self.logger.info(f"   - 已过时间: {elapsed:.2f}s (间隔: {self.rate_limit_interval}s)")
        self.logger.info(f"   - 当前请求计数: {self.request_count}/{self.rate_limit_max_requests}")
        
        # 如果超过间隔时间，重置计数器
        if elapsed > self.rate_limit_interval:
            self.logger.info(f"✅ 频率限制: 时间间隔已超过，重置计数器")
            self.request_count = 0
            self.last_request_time = current_time
            return False
        
        # 检查是否超过最大请求数
        if self.request_count >= self.rate_limit_max_requests:
            wait_time = self.rate_limit_interval - elapsed
            self.logger.warn(f"⚠️ 频率限制触发!")
            self.logger.warn(f"   - 请求计数: {self.request_count} >= {self.rate_limit_max_requests}")
            self.logger.warn(f"   - 需要等待: {wait_time:.2f}s")
            
            if wait_time > 0:
                self.logger.info(f"⏰ 频率限制: 等待 {wait_time:.1f} 秒...")
                time.sleep(wait_time)
                # 等待结束后重置
                self.request_count = 0
                self.last_request_time = time.time()
                self.logger.info(f"✅ 频率限制: 等待结束，计数器已重置")
                return False
        
        self.logger.info(f"✅ 频率限制: 检查通过，可以发起请求")
        return False
    def _update_rate_limit(self):
        """更新频率限制计数器"""
        if self.rate_limit_enabled:
            self.request_count += 1
            if self.request_count == 1:  # 第一次请求时设置开始时间
                self.last_request_time = time.time()
            
            self.logger.info(f"📊 频率限制更新:")
            self.logger.info(f"   - 请求计数: {self.request_count}/{self.rate_limit_max_requests}")
            self.logger.info(f"   - 计数开始时间: {self.last_request_time:.2f}")
    def _load_optimized_prompts(self) -> Dict[str, Dict[str, Any]]:
        """加载已优化的提示词"""
        optimized_file = f"{self.optimized_prompts_dir}/optimized_prompts.json"
        if os.path.exists(optimized_file):
            try:
                with open(optimized_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.info(f"❌ 加载优化提示词失败: {e}")
        return {}
    def _save_optimized_prompts(self):
        """保存优化的提示词到文件"""
        optimized_file = f"{self.optimized_prompts_dir}/optimized_prompts.json"
        try:
            with open(optimized_file, 'w', encoding='utf-8') as f:
                json.dump(self.optimized_prompts, f, ensure_ascii=False, indent=2)
            self.logger.info(f"💾 优化提示词已保存到: {optimized_file}")
        except Exception as e:
            self.logger.info(f"❌ 保存优化提示词失败: {e}")
    def _get_available_providers(self) -> List[str]:
        """获取配置中启用的AI服务提供商"""
        available = []
        api_keys = self.config.get("api_keys", {})
        for provider in ["deepseek", "yuanbao", "gemini"]:
            if api_keys.get(provider):
                available.append(provider)
        return available
    def _get_routed_model(self, content_type: str, chapter_number: Optional[int] = None) -> Optional[str]:
        """
        根据内容类型和章节号获取路由的模型名称
        
        Args:
            content_type: 内容类型（如 "chapter_quality_assessment"）
            chapter_number: 章节号（用于判断是否为黄金三章）
        
        Returns:
            路由的模型名称，如果没有匹配则返回 None
        """
        if not self.model_routing_enabled:
            return None
        
        # 特殊处理：黄金三章使用专用模型
        if content_type == "chapter_quality_assessment" and chapter_number in [1, 2, 3]:
            golden_key = "chapter_quality_assessment_golden"
            if golden_key in self.model_routes:
                self.logger.info(f"🎯 检测到黄金第{chapter_number}章，使用路由模型: {golden_key} -> {self.model_routes[golden_key]}")
                return self.model_routes[golden_key]
        
        # 查找精确匹配的路由
        if content_type in self.model_routes:
            routed_model = self.model_routes[content_type]
            self.logger.info(f"🔄 使用路由模型: {content_type} -> {routed_model}")
            return routed_model
        
        # 如果没有精确匹配，返回默认路由模型
        if self.default_routed_model:
            self.logger.info(f"⚠️ 未找到精确路由，使用默认路由模型: {self.default_routed_model}")
            return self.default_routed_model
        
        return None

    def _get_provider_config(self, provider: Optional[str] = None,
                            content_type: Optional[str] = None,
                            chapter_number: Optional[int] = None) -> Dict[str, Any]:
        """
        获取特定提供商的配置，支持模型路由
        
        Args:
            provider: 提供商名称（可选）
            content_type: 内容类型（用于模型路由）
            chapter_number: 章节号（用于黄金三章判断）
        """
        if provider is None:
            provider = self.default_provider
        
        # 检查是否有模型路由
        routed_model = None
        if content_type:
            routed_model = self._get_routed_model(content_type, chapter_number)
        
        # 如果有路由模型且提供商是 gemini，使用路由模型
        if routed_model and provider == "gemini":
            model_name = routed_model
        else:
            model_name = self.config["models"][provider]
        
        return {
            "api_key": self.config["api_keys"][provider],
            "api_url": self.config["api_urls"][provider],
            "model": model_name,
            "temperature": self.config["defaults"]["temperature"],
            "max_tokens": self.config["defaults"]["max_tokens"]
        }
    def clean_api_response(self, response: str) -> str:
        """清理API响应，移除Markdown代码块标记"""
        if not response:
            return ""
        return re.sub(r'^```json\s*|\s*```$', '', response, flags=re.MULTILINE).strip()
    def _calculate_timeout(self, purpose: str, attempt: int) -> int:
        """根据目的和尝试次数计算超时时间"""
        base_timeouts = {
            "快速质量评估": 120,
            "提示词优化": 60  # 提示词优化通常较快
        }
        timeout = 120  # 默认超时
        for key, value in base_timeouts.items():
            if key in purpose:
                timeout = value
                break
        if attempt > 0:
            timeout += 30 * attempt
        return min(timeout, 300)
    def _process_stream_response(self, response) -> str:
        """处理流式响应并返回完整内容"""
        full_content = ""
        line_count = 0
        data_count = 0
        self.logger.info(f"  开始接收流式响应...")
        try:
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    line_text = line.decode('utf-8').strip()
                    if line_text.startswith('data: '):
                        data_count += 1
                        data_content = line_text[6:]  # 移除 'data: ' 前缀
                        if data_content == '[DONE]':
                            self.logger.info(f"  收到流式传输结束标记 [DONE]")
                            break
                        try:
                            json_data = json.loads(data_content)
                            # 提取内容 - 根据OpenAI兼容API的流式格式
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                choice = json_data['choices'][0]
                                if 'delta' in choice and 'content' in choice['delta']:
                                    content = choice['delta']['content']
                                    if content:
                                        full_content += content
                                elif 'message' in choice and 'content' in choice['message']:
                                    content = choice['message']['content']
                                    if content:
                                        full_content += content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.info(f"  流式响应处理异常: {e}")
        self.logger.info(f"  流式传输完成 - 总行数: {line_count}, 数据块数: {data_count}")
        self.logger.info(f"  最终内容长度: {len(full_content)}字符")
        return full_content
    def _save_api_call_debug(self, system_prompt: str, user_prompt: str, response: str, 
                           purpose: str, provider: str, model: str, attempt: int = 1):
        """保存完整的API调用调试信息，包括输入和回复"""
        timestamp = int(time.time())
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.debug_dir}/api_call_{purpose}_{datetime_str}_attempt{attempt}.txt"
        debug_content = f"""========== API调用调试信息 ==========
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
提供商: {provider.upper()}
模型: {model}
目的: {purpose}
尝试次数: {attempt}
响应长度: {len(response) if response else 0}字符
========== 系统提示 (System Prompt) ==========
{system_prompt}
========== 用户提示 (User Prompt) ==========
{user_prompt}
========== API响应 (API Response) ==========
{response if response else '空响应'}
========== 清理后响应 (Cleaned Response) ==========
{self.clean_api_response(response) if response else '空响应'}
========== 结束 =========="""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(debug_content)
        self.logger.info(f"  💾 API调用调试信息已保存到: {filename}")
        # 同时保存JSON解析相关的调试信息
        if response:
            self._save_debug_response(response, f"raw_{purpose}_{attempt}")
    def _save_debug_response(self, content: str, stage: str):
        """保存调试响应到文件"""
        timestamp = int(time.time())
        filename = f"{self.debug_dir}/{stage}_response_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"  💾 {stage}响应已保存到: {filename}")
    def call_api(self, system_prompt: str, user_prompt: str,
                temperature: Optional[float] = None, purpose: str = "未知",
                provider: Optional[str] = None, model_name: Optional[str] = None) -> Optional[str]:
        """API调用 - 使用配置的默认提供商或指定提供商，支持自定义模型名称"""
        # 最高优先级：在发送给AI之前，将网站风格适配文本添加到system_prompt的最前面
        if self.website_style_enabled and self.website_style_text:
            system_prompt = self.website_style_text + "\n\n" + system_prompt
        target_provider = provider if provider else self.default_provider
        if target_provider not in self.available_providers:
            self.logger.info(f"❌ {target_provider.upper()} 未配置或不可用")
            return None
        provider_config = self._get_provider_config(target_provider)
        api_url = provider_config["api_url"]
        api_key = provider_config["api_key"]
        # 如果没有指定自定义模型名称，使用配置中的模型
        # 确保model_name是str类型，不是Optional[str]
        if model_name is None:
            model_name = provider_config["model"]
        # model_name现在保证是str类型
        temperature = temperature or provider_config["temperature"]
        max_tokens = provider_config["max_tokens"]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # 强制开启流式传输
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        # 智能重试策略
        for attempt in range(self.config["defaults"]["max_retries"]):
            self.logger.info(f"🚀 开始第 {attempt+1}/{self.config['defaults']['max_retries']} 次API调用尝试")
            
            # 检查频率限制（在重试循环内部，因为重试也算作请求）
            rate_limit_result = self._check_rate_limit()
            
            start_time = time.time()
            timeout = self._calculate_timeout(purpose, attempt)
            
            try:
                self.logger.info(f"  📡 发起{target_provider.upper()} API请求:")
                self.logger.info(f"     - 目的: {purpose}")
                self.logger.info(f"     - 模型: {model_name}")
                self.logger.info(f"     - 超时: {timeout}秒")
                self.logger.info(f"     - 流式传输: 启用")
                self.logger.info(f"     - API URL: {api_url[:50]}...")
                self.logger.info(f"     - 请求载荷大小: {len(str(payload))} 字符")
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout, stream=True)
                
                self.logger.info(f"  📡 API响应收到:")
                self.logger.info(f"     - 状态码: {response.status_code}")
                self.logger.info(f"     - 响应时间: {time.time() - start_time:.2f}秒")
                
                # 更新频率限制计数器（只在成功建立连接时计数）
                self._update_rate_limit()
                # 检查HTTP状态码
                if response.status_code != 200:
                    self.logger.error(f"  ❌ HTTP错误: 状态码 {response.status_code}")
                    
                    # 特殊处理429错误 - 提取等待时间
                    if response.status_code == 429:
                        self.logger.error(f"  🚨 触发429错误 - API配额限制!")
                        wait_time = self._extract_retry_after_from_error(response)
                        if wait_time:
                            self.logger.error(f"  ⏰ API返回等待时间: {wait_time:.1f} 秒")
                            self.logger.error(f"  💤 开始等待...")
                            time.sleep(wait_time)
                            self.logger.error(f"  ✅ 等待结束，立即重试")
                            continue  # 直接重试，不消耗重试次数
                        else:
                            self.logger.error(f"  ❌ 无法从API响应中提取重试时间")
                    
                    # 记录详细的错误信息
                    try:
                        error_detail = response.json()
                        self.logger.error(f"  📋 错误详情: {json.dumps(error_detail, ensure_ascii=False, indent=2)}")
                        
                        # 检查是否是rate_limit相关的错误
                        if 'error' in error_detail:
                            error_msg = error_detail['error'].get('message', '').lower()
                            if 'rate' in error_msg or 'limit' in error_msg or 'quota' in error_msg:
                                self.logger.error(f"  🚨 检测到配额/频率限制错误!")
                                
                    except Exception as parse_error:
                        self.logger.error(f"  📋 解析错误响应失败: {parse_error}")
                        self.logger.error(f"  📋 原始响应文本: {response.text[:500]}")
                    
                    response.raise_for_status()
                # 处理流式响应
                content = self._process_stream_response(response)
                if not content:
                    self.logger.info(f"  ❌ API返回空内容")
                    # 即使空内容也保存调试信息
                    self._save_api_call_debug(system_prompt, user_prompt, "", purpose, target_provider, model_name, attempt+1)
                    if attempt < self.config["defaults"]["max_retries"] - 1:
                        continue
                    else:
                        return None
                # 保存完整的API调用调试信息（输入+回复）
                self._save_api_call_debug(system_prompt, user_prompt, content, purpose, target_provider, model_name, attempt+1)
                cleaned_content = self.clean_api_response(content)
                self.logger.info(f"  清理后内容长度: {len(cleaned_content)}字符")
                # 记录请求时间
                request_time = time.time() - start_time
                self.request_times.append((purpose, request_time, target_provider))
                self.logger.info(f"  ⏱️  API调用总耗时: {request_time:.1f}秒")
                # 基本内容验证
                if len(cleaned_content) > 10:
                    self.logger.info(f"  ✓ API响应验证通过")
                    return cleaned_content
                else:
                    self.logger.info(f"  ❌ 内容过短，准备重试...")
                    continue
            except requests.exceptions.Timeout as e:
                request_time = time.time() - start_time
                self.logger.error(f"  ⏰ {target_provider.upper()} API超时:")
                self.logger.error(f"     - 已等待时间: {request_time:.1f}秒")
                self.logger.error(f"     - 设置超时: {timeout}秒")
                self.logger.error(f"     - 超时异常: {str(e)}")
                
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    self.logger.warn(f"  ⏳ 超时重试策略: 等待{delay}秒后进行第{attempt+2}次尝试...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"  💥 所有重试尝试均已超时失败")
                    
            except requests.exceptions.RequestException as e:
                request_time = time.time() - start_time
                self.logger.error(f"  🌐 {target_provider.upper()} 网络请求异常:")
                self.logger.error(f"     - 请求时间: {request_time:.1f}秒")
                self.logger.error(f"     - 异常类型: {type(e).__name__}")
                self.logger.error(f"     - 异常信息: {str(e)}")
                
                # 特殊处理429错误（在异常中）
                if hasattr(e, 'response') and e.response is not None:
                    self.logger.error(f"     - HTTP状态码: {e.response.status_code}")
                    
                    if e.response.status_code == 429:
                        self.logger.error(f"  🚨 异常中检测到429错误 - API配额限制!")
                        wait_time = self._extract_retry_after_from_error(e.response)
                        if wait_time:
                            self.logger.error(f"  ⏰ 从异常响应提取等待时间: {wait_time:.1f} 秒")
                            self.logger.error(f"  💤 开始等待...")
                            time.sleep(wait_time)
                            self.logger.error(f"  ✅ 等待结束，立即重试")
                            continue  # 直接重试，不消耗重试次数
                        else:
                            self.logger.error(f"  ❌ 无法从异常响应中提取重试时间")
                            
                    # 记录响应内容
                    try:
                        error_content = e.response.text
                        self.logger.error(f"  📋 错误响应内容: {error_content[:500]}...")
                        
                        # 检查是否包含rate_limit相关信息
                        if 'rate' in error_content.lower() or 'limit' in error_content.lower() or 'quota' in error_content.lower():
                            self.logger.error(f"  🚨 错误响应中包含配额/频率限制信息!")
                            
                    except Exception as response_error:
                        self.logger.error(f"  📋 读取错误响应失败: {response_error}")
                
                self._save_api_call_debug(system_prompt, user_prompt, f"网络请求异常: {e}", purpose, target_provider, model_name, attempt+1)
                
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    self.logger.warn(f"  ⏳ 网络异常重试策略: 等待{delay}秒后进行第{attempt+2}次尝试...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"  💥 所有重试尝试均因网络异常失败")
                    
            except Exception as e:
                request_time = time.time() - start_time
                self.logger.error(f"  ❌ {target_provider.upper()} API调用发生未知异常:")
                self.logger.error(f"     - 请求时间: {request_time:.1f}秒")
                self.logger.error(f"     - 异常类型: {type(e).__name__}")
                self.logger.error(f"     - 异常信息: {str(e)}")
                
                # 记录完整的堆栈跟踪
                import traceback
                self.logger.error(f"  📋 堆栈跟踪:")
                for line in traceback.format_exc().split('\n'):
                    if line.strip():
                        self.logger.error(f"     {line}")
                
                self._save_api_call_debug(system_prompt, user_prompt, f"API调用失败: {e}", purpose, target_provider, model_name, attempt+1)
                
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    self.logger.warn(f"  ⏳ 未知异常重试策略: 等待{delay}秒后进行第{attempt+2}次尝试...")
                    time.sleep(delay)
                else:
                    self.logger.error(f"  💥 所有重试尝试均因未知异常失败")
        self.logger.info(f"  💥 {target_provider.upper()} API所有重试均失败，目的: {purpose}")
        return None
    def _extract_retry_after_from_error(self, response) -> Optional[float]:
        """从错误响应中提取重试等待时间"""
        self.logger.info(f"  🔍 开始提取重试等待时间...")
        
        try:
            # 尝试从JSON响应中提取错误信息
            error_data = response.json()
            self.logger.info(f"  📋 成功解析错误响应JSON: {type(error_data)}")
            
            # 处理Gemini格式的错误信息
            if 'error' in error_data and 'message' in error_data['error']:
                message = error_data['error']['message']
                self.logger.info(f"  📝 错误消息: {message[:200]}...")
                
                # 使用正则表达式提取等待时间
                import re
                retry_patterns = [
                    r'Please retry in (\d+\.?\d*)s',  # "Please retry in 4.307198169s"
                    r'retry after (\d+\.?\d*) seconds',  # 其他可能的格式
                    r'wait (\d+\.?\d*) seconds',  # 其他可能的格式
                    r'(\d+\.?\d*) seconds',  # 通用格式
                ]
                
                self.logger.info(f"  🔍 尝试从错误消息中提取等待时间，使用 {len(retry_patterns)} 种模式...")
                
                for i, pattern in enumerate(retry_patterns):
                    match = re.search(pattern, message, re.IGNORECASE)
                    if match:
                        wait_time = float(match.group(1))
                        buffered_time = wait_time + 1.0  # 多等1秒确保
                        self.logger.info(f"  ✅ 模式 {i+1} 匹配成功: 原始={wait_time}s, 缓冲后={buffered_time}s")
                        return buffered_time
                    else:
                        self.logger.debug(f"  ❌ 模式 {i+1} 未匹配: {pattern}")
                
                self.logger.info(f"  ❌ 所有重试时间模式均未匹配")
            else:
                self.logger.info(f"  ⚠️ 错误响应中没有找到 'error.message' 字段")
                self.logger.info(f"  📋 错误响应结构: {list(error_data.keys()) if isinstance(error_data, dict) else type(error_data)}")
                
            # 检查Retry-After头部
            if 'Retry-After' in response.headers:
                retry_after = response.headers['Retry-After']
                self.logger.info(f"  📋 发现Retry-After头部: {retry_after}")
                
                try:
                    wait_time = float(retry_after)
                    buffered_time = wait_time + 1.0
                    self.logger.info(f"  ✅ 从Retry-After头部提取等待时间: 原始={wait_time}s, 缓冲后={buffered_time}s")
                    return buffered_time
                except ValueError:
                    self.logger.info(f"  ❌ Retry-After头部无法转换为数字: {retry_after}")
            else:
                self.logger.info(f"  📋 响应头部: {dict(response.headers)}")
                
        except json.JSONDecodeError as e:
            self.logger.error(f"  ❌ 解析错误响应JSON失败: {e}")
            self.logger.error(f"  📋 原始响应文本: {response.text[:200]}...")
        except Exception as e:
            self.logger.error(f"  ❌ 提取重试时间时发生异常: {e}")
            self.logger.error(f"  📋 异常类型: {type(e).__name__}")
            
        self.logger.info(f"  ❌ 无法提取重试等待时间，返回None")
        return None
# 文件: APIClient.py
    def _extract_json_content(self, response: str) -> Optional[str]:
        """从响应中提取JSON内容 - 多策略提取，【增强版：支持对象和数组】"""
        if not response:
            return None
        # 策略1: 查找Markdown JSON代码块 (支持对象和数组)
        # 【关键修改】：使用 (\{.*?\}|\[.*?\]) 来匹配花括号对象或方括号数组
        json_blocks = re.findall(r'```json\s*(\{.*?\}|\[.*?\])\s*```', response, re.DOTALL)
        if json_blocks:
            self.logger.info("  ✓ 通过Markdown代码块提取JSON")
            return json_blocks[-1].strip()
        # 策略2: 查找被 {{ }} 包裹的JSON (支持对象和数组)
        # 【关键修改】：同上
        json_blocks = re.findall(r'\{\{\s*(\{.*?\}|\[.*?\])\s*\}\}', response, re.DOTALL)
        if json_blocks:
            self.logger.info("  ✓ 通过{{ }}包裹提取JSON")
            return json_blocks[-1].strip()
        # 策略3: 【全新、更健壮的边界查找】
        # 寻找第一个出现的 '{' 或 '['
        start_obj_idx = response.find('{')
        start_arr_idx = response.find('[')
        start_idx = -1
        is_array = False
        if start_obj_idx != -1 and start_arr_idx != -1:
            if start_obj_idx < start_arr_idx:
                start_idx = start_obj_idx
            else:
                start_idx = start_arr_idx
                is_array = True
        elif start_obj_idx != -1:
            start_idx = start_obj_idx
        elif start_arr_idx != -1:
            start_idx = start_arr_idx
            is_array = True
        if start_idx != -1:
            # 根据找到的起始括号，查找对应的结束括号
            end_char = ']' if is_array else '}'
            end_idx = response.rfind(end_char)
            if end_idx > start_idx:
                potential_json = response[start_idx : end_idx + 1]
                self.logger.info("  ✓ 通过增强的边界查找提取潜在JSON")
                return potential_json
        # 策略4: 如果内容本身就是JSON，直接返回 (支持对象和数组)
        stripped_response = response.strip()
        if (stripped_response.startswith('{') and stripped_response.endswith('}')) or \
           (stripped_response.startswith('[') and stripped_response.endswith(']')):
            self.logger.info("  ✓ 内容本身是JSON格式")
            return stripped_response
        self.logger.info("  ❌ 所有策略均无法提取有效的JSON内容")
        return None
    def _fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题 - 增强版本"""
        if not json_str:
            return json_str

        # 修复0: 处理中文引号（最高优先级）
        # 将各种中文引号替换为英文双引号
        fixed = json_str.replace('"', '"').replace('"', '"')  # 中文双引号
        fixed = fixed.replace(''', "'").replace(''', "'")      # 中文单引号左右
        fixed = fixed.replace('＂', '"')                        # 全角双引号
        fixed = fixed.replace('＇', "'")                        # 全角单引号

        # 修复1: 移除尾随逗号（对象和数组）
        fixed = re.sub(r',\s*}', '}', fixed)
        fixed = re.sub(r',\s*]', ']', fixed)

        # 修复2: 为未加引号的键添加引号
        fixed = re.sub(
            r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
            r'\1"\2":',
            fixed
        )

        # 修复3: 处理未转义的特殊字符（保留中文字符）
        # 只转义控制字符，不要转义中文
        fixed = fixed.replace('\t', '\\t').replace('\r', '\\r')
        # 处理换行符，但保留可能正常的换行
        lines = fixed.split('\n')
        fixed = ''.join(lines)

        # 修复4: 确保字符串使用双引号（单引号包围的转为双引号）
        # 但要小心不要误伤中文文本中的引号
        fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)

        # 修复5: 处理可能的多余逗号
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)

        # 修复6: 处理可能缺少的逗号
        fixed = re.sub(r'("[^"]*")\s*("[^"]*")', r'\1,\2', fixed)

        # 修复7: 处理可能的控制字符
        # 移除不可见的控制字符（但保留\n等转义）
        fixed = ''.join(char for char in fixed if ord(char) >= 32 or char in '\n\t\r')

        return fixed
# 文件: APIClient.py
    def parse_json_response(self, response: str) -> Optional[Any]:
        """解析JSON响应 - 超级增强版本（已移除不稳定的AI修复）"""
        if not response:
            self.logger.info("  ❌ 传入的响应为空")
            return None
        self.logger.info(f"  开始解析JSON响应，原始长度: {len(response)}")
        # 步骤1: 提取JSON内容
        json_content = self._extract_json_content(response)
        if not json_content:
            self.logger.info("  ❌ 无法提取JSON内容")
            # 即使无法提取，也保存原始响应用于调试
            self._save_debug_response(response, "failed_extraction")
            return None
        self.logger.info(f"  提取的JSON内容长度: {len(json_content)}")
        # 步骤2: 尝试直接解析
        try:
            result = json.loads(json_content)
            self.logger.info("  ✓ JSON直接解析成功")
            return result
        except json.JSONDecodeError as e:
            self.logger.info(f"  - 首次JSON解析失败: {e}")
        # 步骤3: 尝试修复后解析
        try:
            fixed_json = self._fix_json_format(json_content)
            result = json.loads(fixed_json)
            self.logger.info("  ✓ JSON修复后解析成功")
            return result
        except json.JSONDecodeError as e:
            self.logger.info(f"  - JSON修复后仍然解析失败: {e}")
        # 步骤4: 尝试使用更宽松的解析 (已禁用，因为会导致slice对象bug)
        # ast.literal_eval 会把 slice(None, 20, None) 解析成实际的 slice 对象而不是字符串
        # 这会导致 chapter_data["content"] 变成 slice 对象，引发严重bug
        # try:
        #     import ast
        #     result = ast.literal_eval(json_content)
        #     self.logger.info("  ✓ 使用ast.literal_eval解析成功")
        #     return result
        # except Exception as e:
        #     self.logger.info(f"  - ast.literal_eval也失败: {e}")
        # 步骤5: 保存失败的JSON用于调试
        self._save_debug_response(json_content, "failed_json_parse")
        self.logger.info("  💥 所有本地解析和修复方法均失败。放弃本次结果，交由上层重试。")
        return None
    def _add_json_format_requirements(self, system_prompt: str) -> str:
        """在system_prompt中添加严格的JSON格式要求和中文语言要求"""
        strict_system_prompt = system_prompt + """
【严格的输出格式要求 - 必须遵守】
1. 输出必须是纯净的JSON格式，不要包含任何自然语言前缀、后缀或解释
2. 不要使用Markdown代码块标记（如```json）
3. 不要使用{{ }}或其他任何包裹符号
4. 直接以 { 开头，以 } 结尾
5. 确保所有字符串都使用双引号（"），不要使用单引号或中文引号
6. 文本内容中的引号必须完全匹配，检查是否有遗漏的闭合引号
7. 特别注意：不要在JSON中混入中文引号（'、'、"、"）
8. 所有特殊字符（如单引号、制表符等）必须正确转义
9. 不要添加任何额外的文本

【具体要求】
- 每个字符串值必须被双引号包围："value"
- 文本中如果需要引用，用中文符号表示，放在双引号内："这是'示例'文本"
- 数组和对象的逗号位置要正确
- 不要在JSON中包含换行符，除非用\n转义
- 检查所有的花括号、方括号是否成对出现

【语言要求】
- 所有文本内容必须使用简体中文
- 禁止使用英文、繁体中文或其他语言
- 确保角色名、对话、描述等所有文本元素都是简体中文
如果违反这些格式要求，内容将无法被正确解析。"""
        return strict_system_prompt
    def generate_content_with_retry(self, content_type: str, user_prompt: str,
                                  temperature: Optional[float] = None, purpose: str = "内容生成",
                                  provider: Optional[str] = None, enable_prompt_optimization: bool = False,
                                  chapter_number: Optional[int] = None) -> Optional[Any]:
        """带重试机制的内容生成 - 增强JSON格式要求版本，支持模型路由"""
        # 验证内容类型是否支持
        if content_type not in self.Prompts:
            self.logger.info(f"❌ 不支持的内容类型: {content_type}")
            self.logger.info(f"💡 支持的内容类型: {list(self.Prompts.prompts.keys())}")
            return None
        
        # 获取基础系统提示词
        try:
            base_system_prompt = self.Prompts[content_type]
            if not base_system_prompt:
                self.logger.info(f"❌ 内容类型 {content_type} 的提示词为空")
                return None
        except Exception as e:
            self.logger.info(f"❌ 获取内容类型 {content_type} 的提示词时出错: {e}")
            return None
        # 确定使用的提供商
        target_provider = provider if provider else self.default_provider
        if target_provider not in self.available_providers:
            self.logger.info(f"❌ {target_provider.upper()} 未配置或不可用")
            return None
        # 传入 content_type 和 chapter_number 以支持模型路由
        provider_config = self._get_provider_config(target_provider, content_type, chapter_number)
        routed_model = provider_config['model']  # 获取路由后的模型名称
        self.logger.info(f"✓ 使用 {target_provider.upper()} ({routed_model}) 生成 {content_type}")
        if chapter_number is not None:
            self.logger.info(f"  📖 章节号: {chapter_number}")
        # 在system_prompt中添加严格的JSON格式要求
        final_system_prompt_for_api = self._add_json_format_requirements(base_system_prompt)
        # 准备重试的用户提示词
        retry_prompts = [
            user_prompt,
            user_prompt + "\n\n重要：请确保输出是严格的JSON格式，不要包含任何其他文本。",
            user_prompt + "\n\n关键要求：直接以 { 开头，以 } 结尾，中间是完整的JSON对象，不要有任何前缀或后缀。"
        ]
        for json_attempt in range(self.config["defaults"]["json_retries"]):
            current_user_prompt = retry_prompts[min(json_attempt, len(retry_prompts)-1)]
            self.logger.info(f"  第{json_attempt+1}次生成尝试...")
            # 传递路由后的模型名称给 call_api
            result = self.call_api(final_system_prompt_for_api, current_user_prompt, temperature, purpose, target_provider, model_name=routed_model)
            if result:
                self.logger.info(f"  API调用成功，开始解析JSON...")
                parsed = self.parse_json_response(result)
                if parsed:
                    self.logger.info(f"  ✓ JSON解析成功，返回结果")
                    # 如果启用了提示词优化，尝试优化提示词
                    if enable_prompt_optimization:
                        self.optimize_prompts(content_type, base_system_prompt, user_prompt, result, parsed)
                    return parsed
                else:
                    self.logger.info(f"  🔄 JSON解析失败，准备重试...")
                    time.sleep(10)
            else:
                self.logger.info(f"  🔄 API调用无结果，准备重试...")
                time.sleep(10)
        self.logger.info(f"❌ {content_type}生成失败，所有重试均未成功")
        return None
    def optimize_prompts(self, content_type: str, original_system_prompt: str,
                        original_user_prompt: str, api_response: str, parsed_result: Any):
        """优化提示词 - 让AI分析并返回最佳提示词"""
        self.logger.info(f"🔄 开始优化 {content_type} 的提示词...")
        optimization_system_prompt = """你是一位顶级的提示词工程师（Prompt Engineer），专注于设计和优化"可复用的提示词模板"。
你的核心任务是分析一个提示词模板及其在一次具体调用中的表现（输入 -> 输出），然后将其优化成一个更通用、更稳定、更高质量的"模板"。
**核心工作逻辑：**
把【当前提示词】想象成一个"函数"，而提供的【AI实际响应】和【解析结果】只是用于测试这个"函数"的一次"输入/输出"样本。你的优化必须是针对"函数"本身的逻辑和结构，使其能够更好地处理各种不同的输入，而不仅仅是优化本次的样本输出。
**关键原则：绝对不要针对内容进行优化。**
- **禁止**：修改或建议修改小说情节、角色名、世界观等具体内容。
- **聚焦**：提示词的 **措辞、结构、指令清晰度、格式要求和示例**。你的目标是让这个提示词模板在面对**任何一本小说**时都能表现出色。
请严格按照以下JSON格式返回你的分析和优化结果：
{
    "optimized_system_prompt": "优化后的system_prompt模板",
    "optimized_user_prompt": "优化后的user_prompt模板",
    "improvement_reasons": ["解释为什么这样优化能提高模板的通用性和稳定性", "分析原始模板可能存在的问题"]
}
**优化目标：**
1.  **通用性与可复用性**：确保模板适用于不同的小说内容。
2.  **指令清晰性**：减少AI对指令的误解和歧义。
3.  **输出稳定性**：提高JSON等结构化输出的成功率和准确性。
4.  **效率**：在保持质量的前提下，简化不必要的复杂指令。
5.  **忠实于原始意图**：优化后的模板必须仍然服务于原始的核心需求。
"""
        optimization_user_prompt = f"""请根据system_prompt中的核心要求，对以下这个"提示词模板"进行通用性优化。
【当前system_prompt模板】：
{original_system_prompt}
【当前user_prompt模板】：
{original_user_prompt}
【用于测试的AI响应样本】：
{api_response}
【样本解析结果】：
{json.dumps(parsed_result, ensure_ascii=False, indent=2)}
请记住，你的目标是优化这个"模板"本身，而不是优化这份具体的"小说内容样本"。"""
        try:
            result = self.call_api(
                optimization_system_prompt, 
                optimization_user_prompt, 
                temperature=0.3, 
                purpose="提示词优化", 
                provider=self.default_provider
            )
            if result:
                optimized_data = self.parse_json_response(result)
                if optimized_data and isinstance(optimized_data, dict):
                    self._save_optimized_prompt(content_type, optimized_data, 
                                              original_system_prompt, original_user_prompt)
                    return optimized_data
                else:
                    self.logger.info("  ❌ 提示词优化结果解析失败")
            else:
                self.logger.info("  ❌ 提示词优化API调用失败")
        except Exception as e:
            self.logger.info(f"  ❌ 提示词优化过程中出错: {e}")
        return None
    def _save_optimized_prompt(self, content_type: str, optimized_data: Dict[str, Any],
                             original_system: str, original_user: str):
        """保存优化后的提示词"""
        timestamp = int(time.time())
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 保存到内存缓存
        self.optimized_prompts[content_type] = {
            "optimized_system_prompt": str(optimized_data.get("optimized_system_prompt", "")),
            "optimized_user_prompt": str(optimized_data.get("optimized_user_prompt", "")),
            "improvement_reasons": list(optimized_data.get("improvement_reasons", [])),
            "optimized_at": str(datetime_str),
            "original_system_length": int(len(original_system)),
            "original_user_length": int(len(original_user)),
            "optimized_system_length": int(len(optimized_data.get("optimized_system_prompt", ""))),
            "optimized_user_length": int(len(optimized_data.get("optimized_user_prompt", "")))
        }
        # 保存到文件
        self._save_optimized_prompts()
        # 保存详细对比文件
        self._save_optimization_details(content_type, optimized_data, original_system, original_user, datetime_str)
        self.logger.info(f"  ✅ {content_type} 提示词优化完成并保存")
    def _save_optimization_details(self, content_type: str, optimized_data: Dict[str, Any],
                                 original_system: str, original_user: str, datetime_str: str):
        """保存详细的优化对比信息"""
        filename = f"{self.optimized_prompts_dir}/{content_type}_optimization_{datetime_str}.txt"
        content = f"""提示词优化报告 - {content_type}
优化时间: {datetime_str}
=== 原始 System Prompt ===
长度: {len(original_system)}
内容:
{original_system}
=== 优化后 System Prompt ===
长度: {len(optimized_data.get('optimized_system_prompt', ''))}
内容:
{optimized_data.get('optimized_system_prompt', '')}
=== 原始 User Prompt ===
长度: {len(original_user)} 字符
内容:
{original_user}
=== 优化后 User Prompt ===
长度: {len(optimized_data.get('optimized_user_prompt', ''))} 字符
内容:
{optimized_data.get('optimized_user_prompt', '')}
=== 改进原因 ===
{chr(10).join(f"- {reason}" for reason in optimized_data.get('improvement_reasons', []))}
=== 长度变化 ===
System Prompt: {len(original_system)} → {len(optimized_data.get('optimized_system_prompt', ''))} 字符
User Prompt: {len(original_user)} → {len(optimized_data.get('optimized_user_prompt', ''))} 字符
"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        self.logger.info(f"  💾 详细优化报告已保存: {filename}")
    def get_optimized_prompt(self, content_type: str) -> Optional[Dict[str, Any]]:
        """获取优化后的提示词"""
        return self.optimized_prompts.get(content_type)
    def use_optimized_prompt(self, content_type: str) -> bool:
        """使用优化后的提示词替换原始提示词"""
        optimized = self.get_optimized_prompt(content_type)
        if optimized and content_type in self.Prompts.prompts:
            self.Prompts.prompts[content_type] = optimized["optimized_system_prompt"]
            self.logger.info(f"✅ 已为 {content_type} 使用优化后的提示词")
            return True
        else:
            self.logger.info(f"❌ 没有找到 {content_type} 的优化提示词")
            return False
    def list_optimized_prompts(self) -> List[str]:
        """列出所有已优化的提示词"""
        return list(self.optimized_prompts.keys())
    def get_available_providers(self) -> List[str]:
        """获取可用的AI服务提供商列表"""
        return self.available_providers.copy()
    def is_provider_available(self, provider: str) -> bool:
        """检查特定提供商是否可用"""
        return provider in self.available_providers
    def get_default_provider(self) -> str:
        """获取默认的提供商"""
        return self.default_provider
    def set_default_provider(self, provider: str) -> bool:
        """设置默认提供商"""
        if provider in self.available_providers:
            self.default_provider = provider
            self.logger.info(f"✓ 默认提供商已设置为: {provider.upper()}")
            return True
        else:
            self.logger.info(f"❌ {provider.upper()} 不可用，无法设置为默认")
            return False
    def get_current_model(self, provider: Optional[str] = None) -> str:
        """获取当前使用的模型"""
        target_provider = provider if provider else self.default_provider
        config = self._get_provider_config(target_provider)
        return config.get("model", "未知")
    def repair_json_with_ai(self, broken_json: str, original_purpose: str) -> Optional[Any]:
        """使用AI修复破损的JSON"""
        self.logger.info("  🛠️ 尝试使用AI修复破损的JSON...")
        repair_system_prompt = """你是一个专业的JSON格式修复专家。请修复用户提供的破损JSON，使其成为完全有效的JSON格式。
    修复要求：
    1. 只修复格式问题，不要修改内容含义
    2. 确保所有引号、括号、逗号都正确匹配
    3. 移除任何可能导致解析错误的字符
    4. 确保JSON结构完整
    5. 输出必须是纯净的、可直接解析的JSON
    请直接返回修复后的JSON，不要包含任何解释性文字。"""
        repair_user_prompt = f"""请修复以下JSON内容，使其成为有效的JSON格式：
    原始内容（用于{original_purpose}）：
    {broken_json}
    请只返回修复后的JSON："""
        try:
            self.logger.info("  🤖 调用AI进行JSON修复...")
            repaired_content = self.call_api(
                repair_system_prompt,
                repair_user_prompt,
                temperature=0.1,  # 使用低温度确保稳定性
                purpose="JSON修复",
                provider=self.default_provider
            )
            if repaired_content:
                # 清理修复后的内容
                cleaned_repaired = self.clean_api_response(repaired_content)
                self.logger.info(f"  📏 AI修复后内容长度: {len(cleaned_repaired)}字符")
                # 尝试解析修复后的JSON
                try:
                    result = json.loads(cleaned_repaired)
                    self.logger.info("  ✅ AI修复JSON成功！")
                    # 保存修复记录
                    self._save_json_repair_record(broken_json, cleaned_repaired, original_purpose, True)
                    return result
                except json.JSONDecodeError as e:
                    self.logger.info(f"  ❌ AI修复后的JSON仍然无法解析: {e}")
                    self._save_json_repair_record(broken_json, cleaned_repaired, original_purpose, False)
            else:
                self.logger.info("  ❌ AI修复调用无返回")
        except Exception as e:
            self.logger.info(f"  ❌ AI修复过程中出错: {e}")
        return None
    def _save_json_repair_record(self, original_json: str, repaired_json: str, purpose: str, success: bool):
        """保存JSON修复记录"""
        timestamp = int(time.time())
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        status = "success" if success else "failed"
        filename = f"{self.debug_dir}/json_repair_{purpose}_{datetime_str}_{status}.txt"
        content = f"""========== JSON修复记录 ==========
    时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    目的: {purpose}
    状态: {'成功' if success else '失败'}
    ========== 原始JSON (解析失败) ==========
    {original_json}
    ========== 修复后JSON ==========
    {repaired_json}
    ========== 原始JSON长度: {len(original_json)} ==========
    ========== 修复后JSON长度: {len(repaired_json)} ==========
"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"  💾 JSON修复记录已保存: {filename}")