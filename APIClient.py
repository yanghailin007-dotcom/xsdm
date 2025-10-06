"""API客户端类 - 优化版本"""

import json
import re
import time
import requests
from typing import Optional, Any

from Prompts import Prompts

class APIClient:
    def __init__(self, config):
        self.config = config
        self.Prompts = Prompts
        self.request_times = []  # 记录请求时间用于分析
    
    def clean_api_response(self, response: str) -> str:
        """清理API响应，移除Markdown代码块标记"""
        return re.sub(r'^```json\s*|\s*```$', '', response, flags=re.MULTILINE).strip()
    
    def _calculate_timeout(self, purpose: str, attempt: int) -> int:
        """根据目的和尝试次数计算超时时间"""
        base_timeouts = {
            "快速质量评估": 120,
        }
        
        # 查找匹配的目的
        timeout = 90  # 默认超时
        for key, value in base_timeouts.items():
            if key in purpose:
                timeout = value
                break
        
        # 重试时增加超时时间
        if attempt > 0:
            timeout += 30 * attempt
        
        return min(timeout, 180)  # 最大不超过3分钟
    
    def _handle_stream_response(self, response) -> str:
        """处理流式传输的响应 - 增强调试版本"""
        full_content = ""
        line_count = 0
        data_count = 0
        all_lines = []  # 记录所有行用于调试
        
        print(f"  开始接收流式响应...")
        
        try:
            for line in response.iter_lines():
                if line:
                    line_count += 1
                    line_text = line.decode('utf-8').strip()
                    all_lines.append(line_text)  # 记录所有行
                    
                    # 检查是否是数据行 (以 "data: " 开头)
                    if line_text.startswith('data: '):
                        data_count += 1
                        data_content = line_text[6:]  # 移除 'data: ' 前缀
                        
                        # 检查流式传输结束标记
                        if data_content == '[DONE]':
                            print(f"  收到流式传输结束标记 [DONE]")
                            break
                        
                        # 解析JSON数据块
                        try:
                            json_data = json.loads(data_content)
                            
                            # 提取内容 - 根据OpenAI兼容API的流式格式
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                choice = json_data['choices'][0]
                                
                                # 流式响应可能包含 delta 或 message
                                if 'delta' in choice:
                                    content = choice['delta'].get('content', '')
                                    finish_reason = choice.get('finish_reason')
                                elif 'message' in choice and 'content' in choice['message']:
                                    content = choice['message']['content']
                                    finish_reason = None
                                else:
                                    content = ''
                                    finish_reason = None
                                
                                if content:
                                    full_content += content
                                    if data_count <= 3:
                                        print(f"  提取到内容: '{content}'")
                                
                                if finish_reason:
                                    print(f"  完成原因: {finish_reason}")
                            
                        except json.JSONDecodeError as e:
                            print(f"  数据块JSON解析失败: {e}")
                            print(f"  原始数据: {data_content}")
                            continue
                
        except Exception as e:
            print(f"  流式响应处理异常: {e}")
            import traceback
            print(f"  异常堆栈: {traceback.format_exc()}")
        
        # 打印流式传输结束时的全部内容
        print(f"\n  === 流式传输完整内容 ===")
        print(f"  总行数: {line_count}, 数据块数: {data_count}")
        print(f"  最终内容长度: {len(full_content)}")
        print(f"  最终内容预览: {full_content}...")
        
        print(f"\n  === 流式传输原始数据 ===")
        print(f"  === 流式传输结束 ===\n")
        if '```json' in full_content:
            # 找到最后一个JSON代码块
            json_blocks = full_content.split('```json')
            if len(json_blocks) > 1:
                # 取最后一个代码块并清理
                last_block = json_blocks[-1].replace('```', '').strip()
                print(f"  提取最后一个JSON块，长度: {len(last_block)}")
                full_content = last_block
        
        print(f"  最终处理内容长度: {len(full_content)}")
        return full_content        
    
    def _validate_stream_initial_response(self, response) -> tuple:
        """验证流式传输的初始响应是否有效，返回验证结果和重新创建的响应对象"""
        try:
            # 先读取几行来验证响应格式
            lines_checked = 0
            valid_data_found = False
            initial_lines = []
            
            for line in response.iter_lines():
                if line:
                    lines_checked += 1
                    line_text = line.decode('utf-8').strip()
                    initial_lines.append(line_text)
                    
                    # 检查是否是有效的数据行
                    if line_text.startswith('data: '):
                        data_content = line_text[6:]
                        
                        if data_content == '[DONE]':
                            print(f"  流式验证: 过早收到结束标记")
                            return False, None
                        
                        try:
                            json_data = json.loads(data_content)
                            # 检查基本结构
                            if 'choices' in json_data:
                                valid_data_found = True
                                print(f"  流式验证: 发现有效数据块")
                                break
                        except json.JSONDecodeError:
                            continue
                    
                    # 检查前5行
                    if lines_checked >= 5:
                        break
            
            # 重新创建响应对象供后续处理
            try:
                new_response = requests.post(
                    response.request.url, 
                    headers=response.request.headers, 
                    json=json.loads(response.request.body),
                    stream=True,
                    timeout=response.request.timeout if hasattr(response.request, 'timeout') else 120
                )
                return valid_data_found, new_response
            except Exception as e:
                print(f"  重新创建请求失败: {e}")
                return valid_data_found, None
            
        except Exception as e:
            print(f"  流式初始验证异常: {e}")
            return False, None
    
    def optimized_call_api(self, api_type: str, system_prompt: str, user_prompt: str, 
                        temperature: float = None, purpose: str = "未知") -> Optional[str]:
        """优化的API调用 - 修复流式传输问题"""
        if api_type not in self.config["api_keys"] or not self.config["api_keys"][api_type]:
            print(f"{api_type.upper()} API密钥未设置")
            return None
            
        api_url = self.config["api_urls"][api_type]
        api_key = self.config["api_keys"][api_type]
        model_name = self.config["models"][api_type]
        temperature = temperature or self.config["defaults"]["temperature"]
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 根据目的调整max_tokens
        max_tokens = self.config["defaults"]["max_tokens"]
        
        # 强制开启流式传输
        use_stream = True
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": use_stream
        }
        
        # 智能重试策略
        for attempt in range(self.config["defaults"]["max_retries"]):
            start_time = time.time()
            timeout = self._calculate_timeout(purpose, attempt)
            
            try:
                print(f"  调用{api_type.upper()} API (第{attempt+1}次) - 目的: {purpose} (超时: {timeout}秒)...")
                print(f"  使用流式传输模式")
                
                # 打印请求摘要
                print(f"  请求摘要user_prompt: {user_prompt[:100]}...")
                print(f"  请求摘要system_prompt: {system_prompt[:100]}...")
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout, stream=use_stream)
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    print(f"  ❌ HTTP错误: 状态码 {response.status_code}")
                    print(f"  响应头: {dict(response.headers)}")
                    
                    # 对于流式传输错误，尝试读取错误信息
                    error_info = ""
                    try:
                        for line in response.iter_lines():
                            if line:
                                line_text = line.decode('utf-8')
                                if line_text.startswith('data: '):
                                    data_content = line_text[6:]
                                    try:
                                        error_data = json.loads(data_content)
                                        if 'error' in error_data:
                                            error_info = str(error_data['error'])
                                            break
                                    except:
                                        continue
                    except:
                        error_info = response.text[:500] if hasattr(response, 'text') else "无法读取错误详情"
                    
                    if error_info:
                        print(f"  错误详情: {error_info}")
                    
                    response.raise_for_status()
                
                # 验证流式响应的初始格式
                print(f"  验证流式响应初始格式...")
                is_valid, new_response = self._validate_stream_initial_response(response)
                
                if not is_valid:
                    print(f"  ❌ 流式响应初始验证失败")
                    if attempt < self.config["defaults"]["max_retries"] - 1:
                        continue
                    else:
                        return None
                
                if not new_response:
                    print(f"  ❌ 无法重新创建请求")
                    if attempt < self.config["defaults"]["max_retries"] - 1:
                        continue
                    else:
                        return None
                
                # 使用重新创建的响应对象处理完整响应
                print(f"  开始处理完整流式响应...")
                content = self._handle_stream_response(new_response)
                
                # 详细检查内容
                print(f"  最终内容长度: {len(content) if content else 0}字符")
                
                if not content:
                    print(f"  ❌ API返回空内容")
                    if attempt < self.config["defaults"]["max_retries"] - 1:
                        print(f"  🔄 准备重试...")
                        continue
                    else:
                        return None
                
                cleaned_content = self.clean_api_response(content)
                print(f"  清理后内容长度: {len(cleaned_content)}字符")
                
                # 记录请求时间
                request_time = time.time() - start_time
                self.request_times.append((purpose, request_time))
                
                # 输出性能信息
                print(f"  ⏱️  API调用总耗时: {request_time:.1f}秒")
                
                # 内容验证
                if len(cleaned_content) > 10:  # 基本长度验证
                    print(f"  ✓ API响应验证通过")
                    return cleaned_content
                else:
                    print(f"  ❌ 内容过短，准备重试...")
                    continue
                    
            except requests.exceptions.Timeout:
                request_time = time.time() - start_time
                print(f"  ⏰ {api_type.upper()} API超时 (已等待{request_time:.1f}秒)")
                print(f"  请求URL: {api_url}")
                print(f"  请求超时设置: {timeout}秒")
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 1 + (attempt * 2)
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except requests.exceptions.RequestException as e:
                request_time = time.time() - start_time
                print(f"  🌐 {api_type.upper()} 网络请求异常: {e}")
                print(f"  请求URL: {api_url}")
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 1 + (attempt * 2)
                    print(f"  ⏳ 等待{delay}秒后重试...")
                    time.sleep(delay)
                    
            except Exception as e:
                request_time = time.time() - start_time
                print(f"  ❌ {api_type.upper()} API调用失败: {e}")
                print(f"  异常类型: {type(e).__name__}")
                import traceback
                print(f"  异常堆栈: {traceback.format_exc()}")
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    delay = 1 + (attempt * 2)
                    time.sleep(delay)
        
        print(f"  💥 {api_type.upper()} API所有重试均失败，目的: {purpose}")
        return None

    def parse_json_response(self, response: str) -> Optional[Any]:
        """解析JSON响应 - 增强调试"""
        if not response:
            return None
            
        print(f"  开始解析JSON，输入长度: {len(response)}")
        print(f"  输入预览: {response[:200]}...")
        
        # 提取JSON内容
        json_content = self.extract_json_from_response(response)
        if not json_content:
            print("  ❌ 无法从响应中提取JSON内容")
            return None
            
        print(f"  提取的JSON内容长度: {len(json_content)}")
        print(f"  JSON预览: {json_content[:200]}...")
        
        try:
            result = json.loads(json_content)
            print(f"  ✓ JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            print(f"  JSON解析错误: {e}")
            print(f"  错误位置: 第{e.lineno}行, 第{e.colno}列")
            print(f"  错误上下文: ...{json_content[max(0, e.pos-50):e.pos+50]}...")
            
            try:
                fixed_response = self.fix_json_format(json_content)
                print(f"  尝试修复后解析...")
                return json.loads(fixed_response)
            except json.JSONDecodeError as e2:
                print(f"  ❌ JSON修复后仍然解析失败: {e2}")
                return None

    def extract_json_from_response(self, response: str) -> Optional[str]:
        """从API响应中提取JSON内容 - 增强版本"""
        if not response:
            return None
            
        # 查找所有JSON代码块，取最后一个
        json_blocks = re.findall(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_blocks:
            print(f"  找到{len(json_blocks)}个JSON块，使用最后一个")
            return json_blocks[-1].strip()
        
        # 如果没有代码块标记，尝试从字符串中找到最外层的JSON对象
        start_idx = response.find('{')
        # 从后往前找，找到最后一个 '}'
        end_idx = response.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            potential_json = response[start_idx:end_idx+1]
            try:
                # 尝试解析来验证它是否是一个完整的JSON
                json.loads(potential_json)
                print(f"  直接提取并验证通过一个有效的JSON对象，长度: {len(potential_json)}")
                return potential_json
            except json.JSONDecodeError:
                print("  提取的潜在JSON块验证失败，可能结构不完整。")
                # 即使验证失败，也可以尝试返回，让后续的修复逻辑处理
                # 但更好的方式是返回None或者记录错误
                pass

        # 如果已经是干净的JSON，直接返回
        if response.strip().startswith('{') and response.strip().endswith('}'):
            return response.strip()

        print("  未能从响应中提取出有效的JSON结构。")
        return None # 改为返回None，避免将非JSON内容传递给解析器
    def fix_json_format(self, json_str: str) -> str:
        """修复常见的JSON格式问题"""
        if not json_str:
            return json_str
            
        # 修复1：移除尾随逗号
        fixed = re.sub(r',\s*}', '}', json_str)
        fixed = re.sub(r',\s*]', ']', fixed)
        
        # 修复2：为未加引号的键添加引号
        fixed = re.sub(
            r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', 
            r'\1"\2":', 
            fixed
        )
        
        # 修复3：处理未转义的特殊字符
        fixed = fixed.replace('\n', '\\n').replace('\t', '\\t')
        
        return fixed

    def generate_content_with_retry(self, content_type: str, user_prompt: str, 
                                temperature: float = None, purpose: str = "内容生成") -> Optional[Any]:
        """带重试机制的内容生成 - 优化版本"""
        if content_type not in self.Prompts["prompts"]:
            print(f"❌ 不支持的内容类型: {content_type}")
            return None
            
        system_prompt = self.Prompts["prompts"][content_type]
        
        for json_attempt in range(self.config["defaults"]["json_retries"]):
            for api_type in ['gemini']:  # 修改：只使用gemini
                result = self.optimized_call_api(api_type, system_prompt, user_prompt, temperature, purpose)
                if result:
                    parsed = self.parse_json_response(result)
                    if parsed:
                        return parsed
                    else:
                        print(f"  🔄 JSON解析失败，第{json_attempt+1}次重试...")
                        user_prompt += "\n\n请确保输出是严格的JSON格式，不要添加任何额外的解释或自然语言前缀。"
                        time.sleep(1)
                else:
                    print(f"  🔄 {api_type.upper()} API调用无结果，尝试下一个API...")
        
        print(f"❌ {content_type}生成失败")
        return None
    
    def call_api(self, api_type: str, system_prompt: str, user_prompt: str, 
                temperature: float = None, purpose: str = "未知") -> Optional[str]:
        """通用API调用函数"""
        return self.optimized_call_api(api_type, system_prompt, user_prompt, temperature, purpose)