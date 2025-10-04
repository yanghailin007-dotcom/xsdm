"""API客户端类 - 优化版本"""

import json
import re
import time
import requests
from typing import Optional, Any

from prompts import Prompts

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
            "章节质量评估": 120,
            "章节内容优化": 120,
            "生成第": 120,  # 章节生成
            "生成三套小说方案": 60,
            "市场分析": 75,
            "制定写作计划": 240,
            "构建世界观": 120,
            "角色设计": 75,
            "生成唯一章节标题": 90
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
    
    # 在 api_client.py 中修改 optimized_call_api 方法，添加详细的调试信息
    def optimized_call_api(self, api_type: str, system_prompt: str, user_prompt: str, 
                        temperature: float = None, purpose: str = "未知") -> Optional[str]:
        """优化的API调用 - 添加详细调试信息"""
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
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # 智能重试策略
        for attempt in range(self.config["defaults"]["max_retries"]):
            start_time = time.time()
            timeout = self._calculate_timeout(purpose, attempt)
            
            try:
                print(f"  调用{api_type.upper()} API (第{attempt+1}次) - 目的: {purpose} (超时: {timeout}秒)...")
                
                # 打印请求摘要（不包含完整内容避免过长）
                print(f"  \n请求摘要user_prompt:\n {user_prompt}")
                print(f"  \n请求摘要system_prompt:\n {system_prompt}")
                
                
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
                
                # 检查HTTP状态码
                if response.status_code != 200:
                    print(f"  ❌ HTTP错误: 状态码 {response.status_code}")
                    print(f"  响应头: {dict(response.headers)}")
                    # 尝试获取错误详情
                    try:
                        error_detail = response.json()
                        print(f"  错误详情: {error_detail}")
                    except:
                        print(f"  错误响应文本: {response.text[:500]}")
                    response.raise_for_status()
                
                result = response.json()
                
                # 检查API返回结构
                if 'choices' not in result:
                    print(f"  ❌ API返回结构异常: 缺少choices字段")
                    print(f"  完整响应: {result}")
                    continue
                    
                if not result['choices']:
                    print(f"  ❌ API返回结构异常: choices为空列表")
                    print(f"  完整响应: {result}")
                    continue
                    
                if 'message' not in result['choices'][0]:
                    print(f"  ❌ API返回结构异常: 缺少message字段")
                    print(f"  完整响应: {result}")
                    continue
                    
                if 'content' not in result['choices'][0]['message']:
                    print(f"  ❌ API返回结构异常: 缺少content字段")
                    print(f"  完整响应: {result}")
                    continue
                
                content = result['choices'][0]['message']['content']
                
                # 详细检查内容
                print(f"  原始内容长度: {str(content)}")
                print(f"  原始内容长度: {len(content) if content else 0}字符")
                
                if not content:
                    print(f"  ❌ API返回空内容")
                    print(f"  完整响应结构: {str(result)[:500]}...")
                    continue
                
                cleaned_content = self.clean_api_response(content)
                print(f"  清理后内容长度: {len(cleaned_content)}字符")
                
                # 记录请求时间
                request_time = time.time() - start_time
                self.request_times.append((purpose, request_time))
                
                # 输出性能信息
                if request_time > 30:
                    print(f"  ⏱️  API调用耗时: {request_time:.1f}秒")
                
                # 快速验证响应有效性
                validation_result = self._validate_api_response(cleaned_content)
                if validation_result:
                    print(f"  ✓ API响应验证通过")
                    return cleaned_content
                else:
                    print(f"  ❌ API响应验证失败，准备重试...")
                    # 打印验证失败的具体原因
                    print(f"  验证失败时的内容预览: {cleaned_content[:200] if cleaned_content else '空内容'}")
                    continue
                    
            except requests.exceptions.Timeout:
                request_time = time.time() - start_time
                print(f"  ⏰ {api_type.upper()} API超时 (已等待{request_time:.1f}秒)")
                print(f"  请求URL: {api_url}")
                print(f"  请求超时设置: {timeout}秒")
                if attempt == 0:
                    continue
                else:
                    time.sleep(2)
                    
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
    
    def _validate_api_response(self, content: str) -> bool:
        """快速验证API响应是否有效 - 修复版本"""
        if not content or len(content.strip()) < 1:
            print(f"  验证失败：内容过短 - {len(content) if content else 0}字符")
            return False
        
        # 检查是否包含明显的API错误信息
        error_indicators = [
            "无法生成", "failed", "error", 
            "invalid", "unauthorized", "quota", "limit"
        ]
        
        # 只检查开头100个字符，避免误判小说内容
        content_preview = content.lower()[:100]
        if any(indicator in content_preview for indicator in error_indicators):
            print(f"  验证失败：检测到API错误信息")
            return False
        
        # 检查是否为JSON格式
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            # 如果不是JSON，检查是否是纯文本内容
            if len(content) > 50:  # 有一定长度的内容也算有效
                return True
            print("  验证失败：不是有效的JSON格式且内容过短")
            return False
        
    def parse_json_response(self, response: str) -> Optional[Any]:
        """解析JSON响应，带修复机制"""
        if not response:
            return None
            
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            try:
                # 尝试修复JSON格式
                fixed_response = re.sub(r',\s*}', '}', response)
                fixed_response = re.sub(r',\s*]', ']', fixed_response)
                fixed_response = re.sub(
                    r'("[^"]+"):\s*([^"\d\[\]{}\s][^,}\]]*)', 
                    r'\1: "\2"', 
                    fixed_response
                )
                return json.loads(fixed_response)
            except:
                print("  ❌ JSON解析失败")
                return None

    def generate_content_with_retry(self, content_type: str, user_prompt: str, 
                                temperature: float = None, purpose: str = "内容生成") -> Optional[Any]:
        """带重试机制的内容生成 - 优化版本"""
        if content_type not in self.Prompts["prompts"]:
            print(f"❌ 不支持的内容类型: {content_type}")
            return None
            
        system_prompt = self.Prompts["prompts"][content_type]
        
        for json_attempt in range(self.config["defaults"]["json_retries"]):
            for api_type in ['deepseek', 'yuanbao']:
                result = self.optimized_call_api(api_type, system_prompt, user_prompt, temperature, purpose)
                if result:
                    parsed = self.parse_json_response(result)
                    if parsed:
                        return parsed
                    else:
                        print(f"  🔄 JSON解析失败，第{json_attempt+1}次重试...")
                        user_prompt += "\n\n请确保输出是严格的JSON格式。"
                        time.sleep(1)
                else:
                    print(f"  🔄 {api_type.upper()} API调用无结果，尝试下一个API...")
        
        print(f"❌ {content_type}生成失败")
        return None
    
    def call_api(self, api_type: str, system_prompt: str, user_prompt: str, 
                temperature: float = None, purpose: str = "未知") -> Optional[str]:
        """通用API调用函数"""
        return self.optimized_call_api(api_type, system_prompt, user_prompt, temperature, purpose)