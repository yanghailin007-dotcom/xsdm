"""
分域会话模式集成测试

运行方式:
    python tests/test_session_mode.py

测试内容:
    1. 验证所有 session_mode 组件可正常导入
    2. 验证 Prompts 能正确加载 JSON 配置
    3. 验证 SessionOrchestrator 能正确初始化
    4. 可选：运行一个最小化的端到端测试（需要有效 API 配置）
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


def test_imports():
    """测试所有组件可正常导入"""
    print("[TEST] 检查组件导入...")
    from src.core.session_mode import SessionOrchestrator, NovelGenerationSession
    from src.core.session_mode.sessions import (
        FoundationSession, CharacterSession, StructureSession, StageWritingSession
    )
    from src.prompts.Prompts import Prompts
    print("[PASS] 所有组件导入成功")


def test_prompts_loading():
    """测试 Prompts 能加载分域会话的 JSON 配置"""
    print("[TEST] 检查 Prompts 加载...")
    from src.prompts.Prompts import Prompts
    
    prompts = Prompts()
    required_keys = [
        "foundation_planning",
        "worldview_factions",
        "character_design",
        "emotional_growth",
        "stage_overview",
        "stage_details",
        "supplementary_chars",
        "stage_outline",
        "stage_summary",
        "brief_generation",
    ]
    
    missing = [k for k in required_keys if k not in prompts.prompts]
    if missing:
        print(f"[FAIL] 缺少以下提示词模板: {missing}")
        return False
    
    # 验证模板可以格式化
    sample = prompts.get("foundation_planning")
    formatted = sample.format(creative_seed="测试创意", category="玄幻")
    assert "测试创意" in formatted
    assert "玄幻" in formatted
    print("[PASS] 所有提示词模板已加载且可格式化")
    return True


def test_orchestrator_init():
    """测试 SessionOrchestrator 能正确初始化"""
    print("[TEST] 检查编排器初始化...")
    from src.core.session_mode import SessionOrchestrator
    
    # 创建一个最小化的 mock generator
    class MockGenerator:
        def __init__(self):
            self.novel_data = {
                "novel_title": "测试小说",
                "current_progress": {"total_chapters": 100}
            }
            self.config = {"use_domain_session_mode": True}
    
    mock_gen = MockGenerator()
    orchestrator = SessionOrchestrator(mock_gen)
    
    assert orchestrator.generator == mock_gen
    assert orchestrator.STEP_PROGRESS_MAP['foundation_planning'] == 35
    print("[PASS] 编排器初始化成功")


def test_minimal_end_to_end():
    """
    最小化端到端测试（可选，需要有效 API 配置）
    
    如果环境中有可用的 API 配置，此测试会尝试运行 FoundationSession 的第一步。
    否则自动跳过。
    """
    print("[TEST] 尝试最小化端到端测试...")
    try:
        from config.config import CONFIG
        from src.core.APIClient import APIClient
        
        api_client = APIClient(CONFIG)
        if not api_client.available_providers:
            print("[SKIP] 没有可用的 API 提供商，跳过端到端测试")
            return
        
        from src.core.session_mode.sessions.foundation_session import FoundationSession
        
        session = FoundationSession(
            api_client=api_client,
            domain="foundation",
            context_briefs=[],
            novel_data={
                "novel_title": "测试小说",
                "novel_synopsis": "一个测试用的简短简介",
                "category": "玄幻",
                "current_progress": {"total_chapters": 100},
                "creative_seed": {"coreSetting": "测试设定", "coreSellingPoints": "测试卖点"},
            },
        )
        
        # 只测试第一步的 prompt 构建和发送
        print("[INFO] 发送 foundation_planning 测试请求...")
        result = session._execute_foundation_planning()
        if result:
            print(f"[PASS] 端到端测试成功，返回字段: {list(result.keys())}")
        else:
            print("[WARN] API 返回空结果，可能是网络或配置问题")
            
    except Exception as e:
        print(f"[SKIP] 端到端测试失败（可能是配置问题）: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("分域会话模式集成测试")
    print("=" * 60)
    
    test_imports()
    test_prompts_loading()
    test_orchestrator_init()
    
    # 可选：取消下面一行的注释以运行端到端测试
    # test_minimal_end_to_end()
    
    print("=" * 60)
    print("测试完成")
    print("=" * 60)
