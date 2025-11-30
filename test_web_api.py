#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 Web API 完整流程"""

import json
import time
import requests

def test_web_api():
    """测试完整的 Web API 流程"""
    
    BASE_URL = 'http://localhost:5000/api'
    
    print('\n' + '='*60)
    print('🌐 开始测试 Web API 完整流程')
    print('='*60)
    
    # 1. 检查服务是否运行
    print('\n1️⃣ 检查 Web 服务状态...')
    try:
        response = requests.get(f'{BASE_URL}/tasks', timeout=5)
        print(f'  ✅ Web 服务已启动 (状态码: {response.status_code})')
    except Exception as e:
        print(f'  ❌ 无法连接到 Web 服务: {e}')
        return
    
    # 2. 提交生成任务
    print('\n2️⃣ 提交生成任务...')
    generation_params = {
        'novel_title': '穿越异世的医生',
        'author': 'Test Author',
        'genre': '网络文学',
        'style': '男频衍生',
        'target_audience': '成年读者',
        'core_theme': '穿越成长',
        'main_plot': '现代医生穿越到异世界，用医学知识开创新的治疗体系',
        'character_count': 5,
        'chapter_count': 3
    }
    
    print(f'  📝 小说标题: {generation_params["novel_title"]}')
    print(f'  📊 章节数: {generation_params["chapter_count"]}')
    
    new_task_id = None
    try:
        response = requests.post(
            f'{BASE_URL}/generate-chapters',
            json=generation_params,
            timeout=30
        )
        print(f'  ✅ 请求已提交 (状态码: {response.status_code})')
        
        if response.status_code == 200:
            data = response.json()
            new_task_id = data.get('task_id')
            print(f'  📌 新任务ID: {new_task_id}')
            print(f'  📌 响应内容:')
            print(f'     {json.dumps(data, ensure_ascii=False, indent=2)[:300]}...')
    except Exception as e:
        print(f'  ❌ 请求失败: {e}')
        return
    
    # 3. 获取任务列表
    print('\n3️⃣ 获取任务列表...')
    
    # 等待任务启动
    print('  ⏳ 等待 5 秒让后台任务启动...')
    time.sleep(5)
    
    try:
        response = requests.get(f'{BASE_URL}/tasks', timeout=5)
        tasks = response.json()
        print(f'  ✅ 任务列表已获取')
        print(f'  📌 任务数量: {len(tasks)}')
        
        # 查找最新提交的任务
        if new_task_id:
            print(f'\n4️⃣ 检查新任务状态 (ID: {new_task_id})...')
            for task in tasks:
                if task.get('task_id') == new_task_id:
                    print(f'  ✅ 找到新任务')
                    print(f'     ID: {task.get("task_id")}')
                    print(f'     标题: {task.get("title")}')
                    print(f'     状态: {task.get("status")}')
                    print(f'     进度: {task.get("progress")}%')
                    if task.get('error'):
                        print(f'     ❌ 错误: {task.get("error")}')
                    else:
                        print(f'     ✅ 无错误')
                    break
            else:
                print(f'  ⚠️ 未找到任务ID为 {new_task_id} 的任务')
                print(f'  任务列表中的ID: {[t.get("task_id") for t in tasks[:5]]}...')
        
        # 也显示最新的任务（用于调试）
        if tasks:
            print(f'\n📝 最新任务概览:')
            for i, task in enumerate(tasks[:3]):
                print(f'     [{i+1}] {task.get("task_id")[:8]}... - 状态: {task.get("status")} - 错误: {bool(task.get("error"))}')
    except Exception as e:
        print(f'  ❌ 获取失败: {e}')
    
    print('\n' + '='*60)
    print('✅ Web API 测试完成！')
    print('='*60)
    print('\n💡 下一步:')
    print('  1. 访问 http://localhost:5000 查看 Web UI')
    print('  2. 填写小说参数，提交生成任务')
    print('  3. 实时监控生成进度')

if __name__ == '__main__':
    # 给服务一点时间启动
    print('⏳ 等待 Web 服务启动...')
    time.sleep(2)
    test_web_api()
