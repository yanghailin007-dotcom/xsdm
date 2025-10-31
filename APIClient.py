"""API客户端类 - 配置驱动，稳定JSON解析版本"""

import json
import re
import time
import requests
import os
from typing import Optional, Any, Dict, Iterator, List, Tuple
from datetime import datetime

from Prompts import Prompts

class APIClient:
    def __init__(self, config):
        self.config = config
        self.Prompts = Prompts
        self.request_times = []
        
        # 频率限制相关属性
        self.rate_limit_enabled = self.config["rate_limit"]["enabled"]
        self.rate_limit_interval = self.config["rate_limit"]["interval"]
        self.rate_limit_max_requests = self.config["rate_limit"]["max_requests"]
        self.last_request_time = 0  # 上次请求时间戳
        self.request_count = 0      # 当前间隔内的请求计数
        
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
        
        # 显示频率限制状态
        if self.rate_limit_enabled:
            print(f"⏰ 频率限制: 启用 ({self.rate_limit_interval}秒内最多{self.rate_limit_max_requests}次请求)")
        else:
            print("⏰ 频率限制: 禁用")
        
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
            return False
            
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        # 如果超过间隔时间，重置计数器
        if elapsed > self.rate_limit_interval:
            self.request_count = 0
            self.last_request_time = current_time
            return False
        
        # 检查是否超过最大请求数
        if self.request_count >= self.rate_limit_max_requests:
            wait_time = self.rate_limit_interval - elapsed
            if wait_time > 0:
                print(f"⏰ 频率限制: 需要等待 {wait_time:.1f} 秒")
                time.sleep(wait_time)
                # 等待结束后重置
                self.request_count = 0
                self.last_request_time = time.time()
                return False
        
        return False

    def _update_rate_limit(self):
        """更新频率限制计数器"""
        if self.rate_limit_enabled:
            self.request_count += 1
            if self.request_count == 1:  # 第一次请求时设置开始时间
                self.last_request_time = time.time()

    def _load_optimized_prompts(self) -> Dict[str, Dict[str, str]]:
        """加载已优化的提示词"""
        optimized_file = f"{self.optimized_prompts_dir}/optimized_prompts.json"
        if os.path.exists(optimized_file):
            try:
                with open(optimized_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ 加载优化提示词失败: {e}")
        return {}
    
    def _save_optimized_prompts(self):
        """保存优化的提示词到文件"""
        optimized_file = f"{self.optimized_prompts_dir}/optimized_prompts.json"
        try:
            with open(optimized_file, 'w', encoding='utf-8') as f:
                json.dump(self.optimized_prompts, f, ensure_ascii=False, indent=2)
            print(f"💾 优化提示词已保存到: {optimized_file}")
        except Exception as e:
            print(f"❌ 保存优化提示词失败: {e}")
    
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
            # 检查频率限制（在重试循环内部，因为重试也算作请求）
            self._check_rate_limit()
            
            start_time = time.time()
            timeout = self._calculate_timeout(purpose, attempt)
            
            try:
                print(f"  调用{target_provider.upper()} API (第{attempt+1}次) - 目的: {purpose} (超时: {timeout}秒)...")
                print(f"  使用模型: {model_name}")
                print(f"  使用流式传输模式")
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout, stream=True)
                
                # 更新频率限制计数器（只在成功建立连接时计数）
                self._update_rate_limit()
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    print(f"  ❌ HTTP错误: 状态码 {response.status_code}")
                    
                    # 特殊处理429错误 - 提取等待时间
                    if response.status_code == 429:
                        wait_time = self._extract_retry_after_from_error(response)
                        if wait_time:
                            print(f"  ⏰ 配额限制，需要等待 {wait_time:.1f} 秒后重试")
                            time.sleep(wait_time)
                            continue  # 直接重试，不消耗重试次数
                        else:
                            print(f"  ❌ 配额限制，但无法提取重试时间")
                    
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
                #self._save_api_call_debug(system_prompt, user_prompt, content, purpose, target_provider, model_name, attempt+1)
                
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
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except requests.exceptions.RequestException as e:
                request_time = time.time() - start_time
                print(f"  🌐 {target_provider.upper()} 网络请求异常: {e}")
                
                # 特殊处理429错误（在异常中）
                if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    wait_time = self._extract_retry_after_from_error(e.response)
                    if wait_time:
                        print(f"  ⏰ 配额限制，需要等待 {wait_time:.1f} 秒后重试")
                        time.sleep(wait_time)
                        continue  # 直接重试，不消耗重试次数
                
                self._save_api_call_debug(system_prompt, user_prompt, f"网络请求异常: {e}", purpose, target_provider, model_name, attempt+1)
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except Exception as e:
                request_time = time.time() - start_time
                print(f"  ❌ {target_provider.upper()} API调用失败: {e}")
                self._save_api_call_debug(system_prompt, user_prompt, f"API调用失败: {e}", purpose, target_provider, model_name, attempt+1)
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 30
                    time.sleep(delay)
        
        print(f"  💥 {target_provider.upper()} API所有重试均失败，目的: {purpose}")
        return None
    
    def _extract_retry_after_from_error(self, response) -> Optional[float]:
        """从错误响应中提取重试等待时间"""
        try:
            # 尝试从JSON响应中提取错误信息
            error_data = response.json()
            
            # 处理Gemini格式的错误信息
            if 'error' in error_data and 'message' in error_data['error']:
                message = error_data['error']['message']
                
                # 使用正则表达式提取等待时间
                import re
                retry_patterns = [
                    r'Please retry in (\d+\.?\d*)s',  # "Please retry in 4.307198169s"
                    r'retry after (\d+\.?\d*) seconds',  # 其他可能的格式
                    r'wait (\d+\.?\d*) seconds',  # 其他可能的格式
                ]
                
                for pattern in retry_patterns:
                    match = re.search(pattern, message)
                    if match:
                        wait_time = float(match.group(1))
                        # 添加缓冲时间，确保足够
                        return wait_time + 1.0  # 多等1秒确保
            
            # 检查Retry-After头部
            if 'Retry-After' in response.headers:
                retry_after = response.headers['Retry-After']
                try:
                    wait_time = float(retry_after)
                    return wait_time + 1.0  # 多等1秒确保
                except ValueError:
                    pass
                    
        except Exception as e:
            print(f"  ⚠️ 提取重试时间失败: {e}")
        
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
        """修复常见的JSON格式问题 - 增强版本"""
        if not json_str:
            return json_str
            
        # 修复1: 移除尾随逗号（对象和数组）
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
        
        # 修复5: 处理中文引号问题
        fixed = fixed.replace('"', '"').replace('"', '"')
        fixed = fixed.replace('"', '"').replace('"', '"')
        
        # 修复6: 处理可能的多余逗号
        fixed = re.sub(r',(\s*[}\]])', r'\1', fixed)
        
        # 修复7: 处理可能缺少的逗号
        fixed = re.sub(r'("[^"]*")\s*("[^"]*")', r'\1,\2', fixed)
        
        return fixed

    def parse_json_response(self, response: str) -> Optional[Any]:
        """解析JSON响应 - 超级增强版本"""
        if not response:
            print("  ❌ 传入的响应为空")
            return None
            
        print(f"  开始解析JSON响应，原始长度: {len(response)}")
        
        # 步骤1: 提取JSON内容
        json_content = self._extract_json_content(response)
        if not json_content:
            print("  ❌ 无法提取JSON内容")
            return None
            
        print(f"  提取的JSON内容长度: {len(json_content)}")
        
        # 步骤2: 尝试直接解析
        try:
            result = json.loads(json_content)
            print("  ✓ JSON直接解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"  ❌ 首次JSON解析失败: {e}")
            print(f"  错误位置: 第{e.lineno}行, 第{e.colno}列")
            
        # 步骤3: 尝试修复后解析
        try:
            fixed_json = self._fix_json_format(json_content)
            result = json.loads(fixed_json)
            print("  ✓ JSON修复后解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON修复后仍然解析失败: {e}")
            print(f"  错误位置: 第{e.lineno}行, 第{e.colno}列")
            
        # 步骤4: 尝试使用更宽松的解析
        try:
            import ast
            result = ast.literal_eval(json_content)
            print("  ✓ 使用ast.literal_eval解析成功")
            return result
        except Exception as e:
            print(f"  ❌ ast.literal_eval也失败: {e}")
            
        # 步骤5: 保存失败的JSON用于调试
        self._save_debug_response(json_content, "failed_json")
        
        # 步骤6: 尝试手动修复常见问题
        try:
            cleaned = json_content.lstrip('\ufeff')
            result = json.loads(cleaned)
            print("  ✓ 移除BOM后解析成功")
            return result
        except:
            pass
        
        # 步骤7: 最终手段 - 使用AI修复JSON
        print("  🔄 所有自动修复方法均失败，启动AI修复...")
        ai_repaired_result = self.repair_json_with_ai(json_content, "内容生成")
        
        if ai_repaired_result:
            return ai_repaired_result
        else:
            print("  💥 所有JSON解析方法均失败，包括AI修复")
            return None

    def _add_json_format_requirements(self, system_prompt: str) -> str:
        """在system_prompt中添加严格的JSON格式要求和中文语言要求"""
        strict_system_prompt = system_prompt + """

【严格的输出格式要求 - 必须遵守】
1. 输出必须是纯净的JSON格式，不要包含任何自然语言前缀、后缀或解释
2. 不要使用Markdown代码块标记（如```json）
3. 不要使用{{ }}或其他任何包裹符号
4. 直接以 { 开头，以 } 结尾
5. 确保所有字符串都使用双引号
6. 不要添加任何额外的文本

【语言要求】
- 所有文本内容必须使用简体中文
- 禁止使用英文、繁体中文或其他语言
- 确保角色名、对话、描述等所有文本元素都是简体中文

如果违反这些格式要求，内容将无法被正确解析。
"""
        return strict_system_prompt

    def generate_content_with_retry(self, content_type: str, user_prompt: str, 
                                  temperature: float = None, purpose: str = "内容生成",
                                  provider: str = None, enable_prompt_optimization: bool = False) -> Optional[Any]:
        """带重试机制的内容生成 - 增强JSON格式要求版本"""
        if content_type not in self.Prompts:
            print(f"❌ 不支持的内容类型: {content_type}")
            return None
            
        system_prompt = self.Prompts[content_type]
        
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
                    
                    # 如果启用了提示词优化，尝试优化提示词
                    if enable_prompt_optimization:
                        self.optimize_prompts(content_type, system_prompt, user_prompt, result, parsed)
                    
                    return parsed
                else:
                    print(f"  🔄 JSON解析失败，准备重试...")
                    time.sleep(10)
            else:
                print(f"  🔄 API调用无结果，准备重试...")
                time.sleep(10)
        
        print(f"❌ {content_type}生成失败，所有重试均未成功")
        return None

    def optimize_prompts(self, content_type: str, original_system_prompt: str, 
                        original_user_prompt: str, api_response: str, parsed_result: Any):
        """优化提示词 - 让AI分析并返回最佳提示词"""
        print(f"🔄 开始优化 {content_type} 的提示词...")
        
        optimization_system_prompt = """你是一位顶级的提示词工程师（Prompt Engineer），专注于设计和优化“可复用的提示词模板”。

你的核心任务是分析一个提示词模板及其在一次具体调用中的表现（输入 -> 输出），然后将其优化成一个更通用、更稳定、更高质量的“模板”。

**核心工作逻辑：**
把【当前提示词】想象成一个“函数”，而提供的【AI实际响应】和【解析结果】只是用于测试这个“函数”的一次“输入/输出”样本。你的优化必须是针对“函数”本身的逻辑和结构，使其能够更好地处理各种不同的输入，而不仅仅是优化本次的样本输出。

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

        optimization_user_prompt = f"""请根据system_prompt中的核心要求，对以下这个“提示词模板”进行通用性优化。

【当前system_prompt模板】：
{original_system_prompt}

【当前user_prompt模板】：
{original_user_prompt}

【用于测试的AI响应样本】：
{api_response}

【样本解析结果】：
{json.dumps(parsed_result, ensure_ascii=False, indent=2)}

请记住，你的目标是优化这个“模板”本身，而不是优化这份具体的“小说内容样本”。
"""

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
                    print("  ❌ 提示词优化结果解析失败")
            else:
                print("  ❌ 提示词优化API调用失败")
                
        except Exception as e:
            print(f"  ❌ 提示词优化过程中出错: {e}")
        
        return None

    def _save_optimized_prompt(self, content_type: str, optimized_data: Dict[str, Any],
                             original_system: str, original_user: str):
        """保存优化后的提示词"""
        timestamp = int(time.time())
        datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存到内存缓存
        self.optimized_prompts[content_type] = {
            "optimized_system_prompt": optimized_data.get("optimized_system_prompt", ""),
            "optimized_user_prompt": optimized_data.get("optimized_user_prompt", ""),
            "improvement_reasons": optimized_data.get("improvement_reasons", []),
            "optimized_at": datetime_str,
            "original_system_length": len(original_system),
            "original_user_length": len(original_user),
            "optimized_system_length": len(optimized_data.get("optimized_system_prompt", "")),
            "optimized_user_length": len(optimized_data.get("optimized_user_prompt", ""))
        }
        
        # 保存到文件
        self._save_optimized_prompts()
        
        # 保存详细对比文件
        self._save_optimization_details(content_type, optimized_data, original_system, original_user, datetime_str)
        
        print(f"  ✅ {content_type} 提示词优化完成并保存")

    def _save_optimization_details(self, content_type: str, optimized_data: Dict[str, Any],
                                 original_system: str, original_user: str, datetime_str: str):
        """保存详细的优化对比信息"""
        filename = f"{self.optimized_prompts_dir}/{content_type}_optimization_{datetime_str}.txt"
        
        content = f"""提示词优化报告 - {content_type}
优化时间: {datetime_str}

=== 原始 System Prompt ===
长度: {len(original_system)} 字符
内容:
{original_system}

=== 优化后 System Prompt ===
长度: {len(optimized_data.get('optimized_system_prompt', ''))} 字符
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
        
        print(f"  💾 详细优化报告已保存: {filename}")

    def get_optimized_prompt(self, content_type: str) -> Optional[Dict[str, str]]:
        """获取优化后的提示词"""
        return self.optimized_prompts.get(content_type)

    def use_optimized_prompt(self, content_type: str) -> bool:
        """使用优化后的提示词替换原始提示词"""
        optimized = self.get_optimized_prompt(content_type)
        if optimized and content_type in self.Prompts["prompts"]:
            self.Prompts["prompts"][content_type] = optimized["optimized_system_prompt"]
            print(f"✅ 已为 {content_type} 使用优化后的提示词")
            return True
        else:
            print(f"❌ 没有找到 {content_type} 的优化提示词")
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
    
    def repair_json_with_ai(self, broken_json: str, original_purpose: str) -> Optional[Any]:
        """使用AI修复破损的JSON"""
        print("  🛠️ 尝试使用AI修复破损的JSON...")
        
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
            print("  🤖 调用AI进行JSON修复...")
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
                print(f"  📏 AI修复后内容长度: {len(cleaned_repaired)}字符")
                
                # 尝试解析修复后的JSON
                try:
                    result = json.loads(cleaned_repaired)
                    print("  ✅ AI修复JSON成功！")
                    
                    # 保存修复记录
                    self._save_json_repair_record(broken_json, cleaned_repaired, original_purpose, True)
                    return result
                except json.JSONDecodeError as e:
                    print(f"  ❌ AI修复后的JSON仍然无法解析: {e}")
                    self._save_json_repair_record(broken_json, cleaned_repaired, original_purpose, False)
            else:
                print("  ❌ AI修复调用无返回")
                
        except Exception as e:
            print(f"  ❌ AI修复过程中出错: {e}")
        
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
        print(f"  💾 JSON修复记录已保存: {filename}")    