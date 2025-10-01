"""API客户端类 - 优化版本"""

import json
import re
import time
import requests
from typing import Optional, Any
import threading

class APIClient:
    def __init__(self, config):
        self.config = config
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
            "制定写作计划": 90,
            "构建世界观": 75,
            "角色设计": 75,
            "生成唯一章节标题": 90
        }
        
        # 查找匹配的目的
        timeout = 60  # 默认超时
        for key, value in base_timeouts.items():
            if key in purpose:
                timeout = value
                break
        
        # 重试时增加超时时间
        if attempt > 0:
            timeout += 30 * attempt
        
        return min(timeout, 180)  # 最大不超过3分钟
    
    def optimized_call_api(self, api_type: str, system_prompt: str, user_prompt: str, 
                        temperature: float = None, purpose: str = "未知") -> Optional[str]:
        """优化的API调用 - 添加超时控制和性能监控"""
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
        if "快速" in purpose or "标题" in purpose:
            max_tokens = 2000  # 减少token数加快响应
        elif "质量评估" in purpose:
            max_tokens = 3000
        
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
                print(f"调用{api_type.upper()} API (第{attempt+1}次) - 目的: {purpose} (超时: {timeout}秒)...")
                response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                cleaned_content = self.clean_api_response(content)
                
                # 记录请求时间
                request_time = time.time() - start_time
                self.request_times.append((purpose, request_time))
                
                # 输出性能信息
                if request_time > 30:
                    print(f"  ⏱️  API调用耗时: {request_time:.1f}秒")
                
                # 快速验证响应有效性
                if self._validate_api_response(cleaned_content):
                    return cleaned_content
                else:
                    print(f"  ❌ API响应验证失败，准备重试...")
                    continue
                    
            except requests.exceptions.Timeout:
                request_time = time.time() - start_time
                print(f"  ⏰ {api_type.upper()} API超时 (已等待{request_time:.1f}秒)")
                if attempt == 0:
                    continue  # 首次超时立即重试
                else:
                    time.sleep(2)
            except Exception as e:
                request_time = time.time() - start_time
                print(f"  ❌ {api_type.upper()} API调用失败: {e} (耗时{request_time:.1f}秒)")
                if attempt < self.config["defaults"]["max_retries"] - 1:
                    # 渐进式延迟：1s, 3s, 5s
                    delay = 1 + (attempt * 2)
                    time.sleep(delay)
                
        return None
    
    def _validate_api_response(self, content: str) -> bool:
        """快速验证API响应是否有效 - 修复版本"""
        if not content or len(content.strip()) < 10:
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
        if content_type not in self.config["prompts"]:
            print(f"❌ 不支持的内容类型: {content_type}")
            return None
            
        system_prompt = self.config["prompts"][content_type]
        
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
    
    def print_performance_stats(self):
        """打印API性能统计"""
        if not self.request_times:
            return
        
        print("\n📊 API调用性能统计:")
        purposes = set([p[0] for p in self.request_times])
        
        for purpose in purposes:
            times = [t[1] for p, t in self.request_times if p == purpose]
            avg_time = sum(times) / len(times)
            max_time = max(times)
            min_time = min(times)
            print(f"  {purpose}: 平均{avg_time:.1f}秒 (最小{min_time:.1f}秒, 最大{max_time:.1f}秒)")