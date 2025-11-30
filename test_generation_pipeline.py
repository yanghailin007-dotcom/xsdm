#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试完整的生成管道"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


import os
import sys

# 设置模拟 API 模式
os.environ['USE_MOCK_API'] = 'true'

from src.core.NovelGenerator import NovelGenerator
from config.config import CONFIG

def test_pipeline():
    """测试完整的生成管道"""
    
    CONFIG['use_mock_api'] = True
    
    # 初始化 NovelGenerator
    print('\n🔧 初始化 NovelGenerator...')
    ng = NovelGenerator(CONFIG)
    print('✅ NovelGenerator 初始化成功')
    
    # 准备生成参数
    params = {
        'novel_title': '测试小说：穿越异世',
        'author': '测试作者',
        'genre': '网络文学',
        'style': '男频衍生',
        'target_audience': '成年读者',
        'core_theme': '穿越成长',
        'main_plot': '主角穿越到异世界，从零开始的冒险故事',
        'character_count': 5,
        'chapter_count': 3
    }
    
    print(f'\n📝 生成参数:')
    print(f'  标题: {params["novel_title"]}')
    print(f'  章节数: {params["chapter_count"]}')
    print(f'  主题: {params["core_theme"]}')
    
    # 测试 MockAPIClient 调用
    print('\n🔄 测试 MockAPIClient 调用...')
    
    # 测试小说规划
    print('\n  📋 测试 novel_plan...')
    result = ng.api_client.generate_content_with_retry(
        purpose='小说方案',
        prompt='生成小说大纲'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    
    # 测试情感蓝图
    print('\n  💭 测试 emotional_blueprint...')
    result = ng.api_client.generate_content_with_retry(
        purpose='情绪蓝图',
        prompt='生成情感蓝图'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    
    # 测试阶段规划
    print('\n  📊 测试 stage_plan...')
    result = ng.api_client.generate_content_with_retry(
        purpose='阶段计划',
        prompt='生成阶段规划'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    
    # 测试章节大纲
    print('\n  📑 测试 chapter_outline...')
    result = ng.api_client.generate_content_with_retry(
        purpose='章节大纲',
        prompt='生成章节大纲'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    
    # 测试章节内容
    print('\n  📖 测试 chapter_content...')
    result = ng.api_client.generate_content_with_retry(
        purpose='章节内容',
        prompt='生成章节内容'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    print(f'  📄 内容片段: {result_str[:150]}...')
    
    # 测试质量评估
    print('\n  ⭐ 测试 quality_assessment...')
    result = ng.api_client.generate_content_with_retry(
        purpose='质量评估',
        prompt='质量评估'
    )
    result_str = str(result)
    print(f'  ✅ 返回长度: {len(result_str)} 字符')
    print(f'  📊 内容片段: {result_str[:150]}...')
    
    print('\n' + '='*60)
    print('✅ 全部 MockAPIClient 测试完成！')
    print('='*60)

if __name__ == '__main__':
    test_pipeline()
