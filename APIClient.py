"""API客户端类 - 配置驱动，稳定JSON解析版本"""

import json
import re
import time
import requests
import os
from typing import Optional, Any, Dict, Iterator, List
from datetime import datetime

from Prompts import Prompts

class APIClient:
    def __init__(self, config):
        self.config = config
        self.Prompts = Prompts
        self.request_times = []
        
        # 从配置中获取默认提供商
        self.default_provider = self.config.get("default_provider", "gemini")
        self.available_providers = self._get_available_providers()
        
        # 验证默认提供商是否可用
        if self.default_provider not in self.available_providers:
            if self.available_providers:
                self.default_provider = self.available_providers[0]
                print(f"⚠️ 配置的默认提供商不可用，已切换到: {self.default_provider}")
            else:
                print("❌ 没有可用的AI服务提供商")
        
        print(f"✓ 默认使用: {self.default_provider.upper()}") 
        print(f"✓ 可用提供商: {self.available_providers}")
        
        # 创建调试目录
        self.debug_dir = "debug_responses"
        os.makedirs(self.debug_dir, exist_ok=True)
    
    def _get_available_providers(self) -> List[str]:
        """获取配置中启用的AI服务提供商"""
        available = []
        api_keys = self.config.get("api_keys", {})
        
        for provider in ["deepseek", "yuanbao", "gemini"]:
            if api_keys.get(provider):
                available.append(provider)
        
        return available
    
    def _get_provider_config(self, provider: str = None) -> Dict[str, Any]:
        """获取特定提供商的配置"""
        if provider is None:
            provider = self.default_provider
            
        return {
            "api_key": self.config["api_keys"][provider],
            "api_url": self.config["api_urls"][provider],
            "model": self.config["models"][provider],
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
            "快速质量评估": 120
        }
        
        timeout = 120  # 默认超时
        for key, value in base_timeouts.items():
            if key in purpose:
                timeout = value
                break
        
        if attempt > 0:
            timeout += 30 * attempt
        
        return min(timeout, 300)
    
    def _process_stream_response(self, response: requests.Response) -> str:
        """处理流式响应并返回完整内容"""
        full_content = ""
        line_count = 0
        data_count = 0
        
        print(f"  开始接收流式响应...")
        
        try:
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    line_text = line.decode('utf-8').strip()
                    
                    if line_text.startswith('data: '):
                        data_count += 1
                        data_content = line_text[6:]  # 移除 'data: ' 前缀
                        
                        if data_content == '[DONE]':
                            print(f"  收到流式传输结束标记 [DONE]")
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
            print(f"  流式响应处理异常: {e}")
        
        print(f"  流式传输完成 - 总行数: {line_count}, 数据块数: {data_count}")
        print(f"  最终内容长度: {len(full_content)}字符")
        
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
        print(f"  💾 API调用调试信息已保存到: {filename}")
        
        # 同时保存JSON解析相关的调试信息
        if response:
            self._save_debug_response(response, f"raw_{purpose}_{attempt}")
    
    def _save_debug_response(self, content: str, stage: str):
        """保存调试响应到文件"""
        timestamp = int(time.time())
        filename = f"{self.debug_dir}/{stage}_response_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  💾 {stage}响应已保存到: {filename}")
    
    def call_api(self, system_prompt: str, user_prompt: str, 
                temperature: float = None, purpose: str = "未知",
                provider: str = None) -> Optional[str]:
        """API调用 - 使用配置的默认提供商或指定提供商"""
        
        target_provider = provider if provider else self.default_provider
        
        if target_provider not in self.available_providers:
            print(f"❌ {target_provider.upper()} 未配置或不可用")
            return None
            
        provider_config = self._get_provider_config(target_provider)
        
        api_url = provider_config["api_url"]
        api_key = provider_config["api_key"]
        model_name = provider_config["model"]
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
            start_time = time.time()
            timeout = self._calculate_timeout(purpose, attempt)
            
            try:
                print(f"  调用{target_provider.upper()} API (第{attempt+1}次) - 目的: {purpose} (超时: {timeout}秒)...")
                print(f"  使用模型: {model_name}")
                print(f"  使用流式传输模式")
                
                # 打印请求摘要
                print(f"  请求摘要user_prompt: {user_prompt[:100]}...")
                print(f"  请求摘要system_prompt: {system_prompt[:100]}...")
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout, stream=True)
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    print(f"  ❌ HTTP错误: 状态码 {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"  错误详情: {error_detail}")
                    except:
                        print(f"  错误响应文本: {response.text[:500]}")
                    response.raise_for_status()
                
                # 处理流式响应
                content = self._process_stream_response(response)
                
                if not content:
                    print(f"  ❌ API返回空内容")
                    # 即使空内容也保存调试信息
                    self._save_api_call_debug(system_prompt, user_prompt, "", purpose, target_provider, model_name, attempt+1)
                    if attempt < self.config["defaults"]["max_retries"] - 1:
                        continue
                    else:
                        return None
                
                # 保存完整的API调用调试信息（输入+回复）
                self._save_api_call_debug(system_prompt, user_prompt, content, purpose, target_provider, model_name, attempt+1)
                
                cleaned_content = self.clean_api_response(content)
                print(f"  清理后内容长度: {len(cleaned_content)}字符")
                
                # 记录请求时间
                request_time = time.time() - start_time
                self.request_times.append((purpose, request_time, target_provider))
                
                print(f"  ⏱️  API调用总耗时: {request_time:.1f}秒")
                
                # 基本内容验证
                if len(cleaned_content) > 10:
                    print(f"  ✓ API响应验证通过")
                    return cleaned_content
                else:
                    print(f"  ❌ 内容过短，准备重试...")
                    continue
                    
            except requests.exceptions.Timeout:
                request_time = time.time() - start_time
                print(f"  ⏰ {target_provider.upper()} API超时 (已等待{request_time:.1f}秒)")
                # 保存超时调试信息
                self._save_api_call_debug(system_prompt, user_prompt, f"请求超时 (已等待{request_time:.1f}秒)", purpose, target_provider, model_name, attempt+1)
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except requests.exceptions.RequestException as e:
                request_time = time.time() - start_time
                print(f"  🌐 {target_provider.upper()} 网络请求异常: {e}")
                # 保存异常调试信息
                self._save_api_call_debug(system_prompt, user_prompt, f"网络请求异常: {e}", purpose, target_provider, model_name, attempt+1)
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except Exception as e:
                request_time = time.time() - start_time
                print(f"  ❌ {target_provider.upper()} API调用失败: {e}")
                # 保存异常调试信息
                self._save_api_call_debug(system_prompt, user_prompt, f"API调用失败: {e}", purpose, target_provider, model_name, attempt+1)
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    time.sleep(delay)
        
        print(f"  💥 {target_provider.upper()} API所有重试均失败，目的: {purpose}")
        return None
    
    def _extract_json_content(self, response: str) -> Optional[str]:
        """从响应中提取JSON内容 - 多策略提取"""
        if not response:
            return None
            
        # 策略1: 查找Markdown JSON代码块
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_blocks:
            print("  ✓ 通过Markdown代码块提取JSON")
            return json_blocks[-1].strip()
        
        # 策略2: 查找被 {{ }} 包裹的JSON
        json_blocks = re.findall(r'\{\{\s*(\{.*?\})\s*\}\}', response, re.DOTALL)
        if json_blocks:
            print("  ✓ 通过{{ }}包裹提取JSON")
            return json_blocks[-1].strip()
        
        # 策略3: 查找第一个{和最后一个}
        start_idx = response.find('{')
        end_idx = response.rfind('}')
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = response[start_idx:end_idx+1]
            print("  ✓ 通过边界查找提取潜在JSON")
            return potential_json
        
        # 策略4: 如果内容本身就是JSON，直接返回
        if response.strip().startswith('{') and response.strip().endswith('}'):
            print("  ✓ 内容本身是JSON格式")
            return response.strip()
        
        print("  ❌ 无法提取JSON内容")
        return None
    
    def _fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题"""
        if not json_str:
            return json_str
            
        # 修复1: 移除尾随逗号
        fixed = re.sub(r',\s*}', '}', json_str)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # 修复2: 为未加引号的键添加引号
        fixed = re.sub(
            r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', 
            r'\1"\2":', 
            fixed
        )
        
        # 修复3: 处理未转义的特殊字符
        fixed = fixed.replace('\n', '\\n').replace('\t', '\\t').replace('\r', '\\r')
        
        # 修复4: 确保字符串使用双引号
        fixed = re.sub(r"'([^']*)'", r'"\1"', fixed)
        
        return fixed
    
    def parse_json_response(self, response: str) -> Optional[Any]:
        """解析JSON响应 - 增强版本"""
        if not response:
            print("  ❌ 传入的响应为空")
            return None
            
        print(f"  开始解析JSON响应，原始长度: {len(response)}")
        
        # 保存原始响应用于调试
        #self._save_debug_response(response, "before_parse")
        
        # 步骤1: 提取JSON内容
        json_content = self._extract_json_content(response)
        if not json_content:
            return None
            
        print(f"  提取的JSON内容长度: {len(json_content)}")
        
        # 步骤2: 尝试直接解析
        try:
            result = json.loads(json_content)
            print("  ✓ JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"  ❌ 首次JSON解析失败: {e}")
            print(f"  错误位置: {e.lineno}:{e.colno}")
            
        # 步骤3: 尝试修复后解析
        try:
            fixed_json = self._fix_json_format(json_content)
            result = json.loads(fixed_json)
            print("  ✓ JSON修复后解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON修复后仍然解析失败: {e}")
            
            # 保存失败的JSON用于调试
            self._save_debug_response(json_content, "failed_json")
            self._save_debug_response(fixed_json, "fixed_json")
            
        return None

    def _add_json_format_requirements(self, system_prompt: str) -> str:
        """在system_prompt中添加严格的JSON格式要求"""
        strict_system_prompt = system_prompt + """

【严格的输出格式要求 - 必须遵守】
1. 输出必须是纯净的JSON格式，不要包含任何自然语言前缀、后缀或解释
2. 不要使用Markdown代码块标记（如```json）
3. 不要使用{{ }}或其他任何包裹符号
4. 直接以 { 开头，以 } 结尾
5. 确保所有字符串都使用双引号
6. 不要添加任何额外的文本

如果违反这些格式要求，内容将无法被正确解析。
"""
        return strict_system_prompt

    def generate_content_with_retry(self, content_type: str, user_prompt: str, 
                                  temperature: float = None, purpose: str = "内容生成",
                                  provider: str = None) -> Optional[Any]:
        """带重试机制的内容生成 - 增强JSON格式要求版本"""
        if content_type not in self.Prompts["prompts"]:
            print(f"❌ 不支持的内容类型: {content_type}")
            return None
            
        system_prompt = self.Prompts["prompts"][content_type]
        
        # 确定使用的提供商
        target_provider = provider if provider else self.default_provider
        
        if target_provider not in self.available_providers:
            print(f"❌ {target_provider.upper()} 未配置或不可用")
            return None
        
        provider_config = self._get_provider_config(target_provider)
        print(f"✓ 使用 {target_provider.upper()} ({provider_config['model']}) 生成 {content_type}")
        
        # 在system_prompt中添加严格的JSON格式要求
        strict_system_prompt = self._add_json_format_requirements(system_prompt)
        
        # 准备重试的用户提示词
        retry_prompts = [
            user_prompt,
            user_prompt + "\n\n重要：请确保输出是严格的JSON格式，不要包含任何其他文本。",
            user_prompt + "\n\n关键要求：直接以 { 开头，以 } 结尾，中间是完整的JSON对象，不要有任何前缀或后缀。"
        ]
        
        for json_attempt in range(self.config["defaults"]["json_retries"]):
            current_user_prompt = retry_prompts[min(json_attempt, len(retry_prompts)-1)]
            
            print(f"  第{json_attempt+1}次生成尝试...")
            result = self.call_api(strict_system_prompt, current_user_prompt, temperature, purpose, target_provider)
            
            if result:
                print(f"  API调用成功，开始解析JSON...")
                parsed = self.parse_json_response(result)
                if parsed:
                    print(f"  ✓ JSON解析成功，返回结果")
                    return parsed
                else:
                    print(f"  🔄 JSON解析失败，准备重试...")
                    time.sleep(10)
            else:
                print(f"  🔄 API调用无结果，准备重试...")
                time.sleep(10)
        
        print(f"❌ {content_type}生成失败，所有重试均未成功")
        return None
    
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
            print(f"✓ 默认提供商已设置为: {provider.upper()}")
            return True
        else:
            print(f"❌ {provider.upper()} 不可用，无法设置为默认")
            return False
    
    def get_current_model(self, provider: str = None) -> str:
        """获取当前使用的模型"""
        target_provider = provider if provider else self.default_provider
        config = self._get_provider_config(target_provider)
        return config.get("model", "未知")