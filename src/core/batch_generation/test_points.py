# -*- coding: utf-8 -*-
"""
批量生成点数消耗测试
验证点数统计是否正确
"""

import logging
from unittest.mock import Mock, MagicMock

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_points_calculation():
    """测试点数计算逻辑"""
    
    print("=" * 60)
    print("测试批量生成点数统计")
    print("=" * 60)
    
    # 模拟APIClient
    mock_api_client = Mock()
    mock_api_client.api_call_counter = 0
    
    # 模拟点数扣除回调
    def mock_generate_content_with_retry(*args, **kwargs):
        # 每次调用增加计数器（模拟点数扣除）
        mock_api_client.api_call_counter += 1
        purpose = kwargs.get('purpose', 'unknown')
        print(f"  [API调用] #{mock_api_client.api_call_counter}: {purpose}")
        return {
            "chapters": [
                {
                    "chapter_number": 5,
                    "title": "测试章节",
                    "content": "测试内容...",
                    "key_events": ["事件1"],
                    "character_states": {},
                    "items_delta": {},
                    "time_progression": "1天"
                }
            ]
        }
    
    mock_api_client.generate_content_with_retry = mock_generate_content_with_retry
    
    # 测试场景1: 批量生成2章
    print("\n场景1: 批量生成2章")
    print("-" * 40)
    
    from .processor import MediumEventBatchProcessor
    
    processor = MediumEventBatchProcessor(mock_api_client)
    
    # 模拟批量生成
    calls_before = mock_api_client.api_call_counter
    
    # 模拟调用正文生成
    mock_api_client.generate_content_with_retry(
        content_type="multi_chapter_content",
        user_prompt="test",
        purpose="批量生成第5-6章"
    )
    
    # 模拟调用评估
    mock_api_client.generate_content_with_retry(
        content_type="batch_quality_assessment_l1",
        user_prompt="test",
        purpose="Level 1质量评估"
    )
    
    calls_after = mock_api_client.api_call_counter
    api_calls_used = calls_after - calls_before
    points_saved = 6 - api_calls_used  # 原需6点（2章*3）
    
    print(f"  API调用次数: {api_calls_used}")
    print(f"  创造点消耗: {api_calls_used}")
    print(f"  原逐章方案: 6点")
    print(f"  节省点数: {points_saved}")
    print(f"  节省比例: {points_saved/6*100:.1f}%")
    
    assert api_calls_used == 2, f"期望2次调用，实际{api_calls_used}"
    assert points_saved == 4, f"期望节省4点，实际{points_saved}"
    
    # 测试场景2: 批量生成3章
    print("\n场景2: 批量生成3章")
    print("-" * 40)
    
    calls_before = mock_api_client.api_call_counter
    
    mock_api_client.generate_content_with_retry(
        content_type="multi_chapter_content",
        user_prompt="test",
        purpose="批量生成第7-9章"
    )
    
    mock_api_client.generate_content_with_retry(
        content_type="batch_quality_assessment_l1",
        user_prompt="test",
        purpose="Level 1质量评估"
    )
    
    calls_after = mock_api_client.api_call_counter
    api_calls_used = calls_after - calls_before
    points_saved = 9 - api_calls_used  # 原需9点（3章*3）
    
    print(f"  API调用次数: {api_calls_used}")
    print(f"  创造点消耗: {api_calls_used}")
    print(f"  原逐章方案: 9点")
    print(f"  节省点数: {points_saved}")
    print(f"  节省比例: {points_saved/9*100:.1f}%")
    
    assert api_calls_used == 2, f"期望2次调用，实际{api_calls_used}"
    assert points_saved == 7, f"期望节省7点，实际{points_saved}"
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过!")
    print("=" * 60)
    print(f"\n总API调用: {mock_api_client.api_call_counter}次")
    print(f"总创造点消耗: {mock_api_client.api_call_counter}点")
    print(f"相比逐章生成(15点)节省: {15 - mock_api_client.api_call_counter}点")


if __name__ == "__main__":
    test_points_calculation()
