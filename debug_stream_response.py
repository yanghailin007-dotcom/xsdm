#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试流式响应 - 捕获原始数据
"""
import json
import requests
import sys

# 设置UTF-8编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 配置
api_key = "sk-xxxxx"  # 需要替换为实际的API key
api_url = "https://api.devdove.site/v1/chat/completions"

# 测试用的简单提示
payload = {
    "model": "gemini-3-pro-preview",
    "messages": [
        {"role": "system", "content": "你是一个测试助手"},
        {"role": "user", "content": "请用JSON格式回复：{\"message\": \"hello world\"}"}
    ],
    "temperature": 0.7,
    "max_tokens": 100,
    "stream": True
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

print("=" * 80)
print("开始捕获流式响应...")
print("=" * 80)
print()

try:
    response = requests.post(api_url, headers=headers, json=payload, stream=True, timeout=30)
    
    if response.status_code != 200:
        print(f"❌ HTTP错误: {response.status_code}")
        print(f"响应内容: {response.text[:500]}")
        sys.exit(1)
    
    print(f"✅ 状态码: {response.status_code}")
    print(f"📡 开始接收流式数据...")
    print()
    
    line_count = 0
    data_count = 0
    sample_lines = []
    
    for line in response.iter_lines():
        if line:
            line_count += 1
            line_text = line.decode('utf-8').strip()
            
            # 保存前10行用于分析
            if len(sample_lines) < 10:
                sample_lines.append(line_text)
            
            if line_text.startswith('data: '):
                data_count += 1
                data_content = line_text[6:]
                
                if data_content == '[DONE]':
                    print(f"✅ 收到结束标记 [DONE]")
                    break
                
                try:
                    json_data = json.loads(data_content)
                    
                    # 尝试不同的路径提取内容
                    content = None
                    
                    # 路径1: choices[0].delta.content
                    if 'choices' in json_data and len(json_data['choices']) > 0:
                        choice = json_data['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            content = choice['delta']['content']
                        elif 'message' in choice and 'content' in choice['message']:
                            content = choice['message']['content']
                    
                    # 路径2: 直接在顶层
                    if not content and 'content' in json_data:
                        content = json_data['content']
                    
                    if content:
                        print(f"📝 内容片段: {content[:50]}...")
                
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"   原始数据: {data_content[:100]}...")
    
    print()
    print("=" * 80)
    print(f"📊 统计:")
    print(f"   总行数: {line_count}")
    print(f"   数据块数: {data_count}")
    print()
    print("=" * 80)
    print("📋 前10行原始数据样本:")
    print("=" * 80)
    for i, line in enumerate(sample_lines, 1):
        print(f"{i}. {line}")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()