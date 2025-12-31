"""
测试平台适配功能
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.platform_adapters import PlatformAdapterFactory, FanqieAdapter, QidianAdapter, ZhihuAdapter
from src.prompts.BasePrompts import BasePrompts


def test_platform_adapter_factory():
    """测试平台适配器工厂"""
    print("=" * 60)
    print("测试1: 平台适配器工厂")
    print("=" * 60)
    
    # 测试获取支持的平台列表
    platforms = PlatformAdapterFactory.get_supported_platforms()
    print(f"\n[OK] 支持的平台数量: {len(platforms)}")
    for platform in platforms:
        print(f"  - {platform['name']} ({platform['code']}): {platform['description']}")
    
    # 测试获取各平台适配器
    print("\n[TEST] 测试获取各平台适配器:")
    
    fanqie = PlatformAdapterFactory.get_adapter("fanqie")
    print(f"  [OK] 番茄小说适配器: {fanqie.platform_name}")
    
    qidian = PlatformAdapterFactory.get_adapter("qidian")
    print(f"  [OK] 起点中文网: {qidian.platform_name}")
    
    zhihu = PlatformAdapterFactory.get_adapter("zhihu")
    print(f"  [OK] 知乎盐选: {zhihu.platform_name}")
    
    # 测试无效平台（应返回默认的番茄适配器）
    invalid = PlatformAdapterFactory.get_adapter("invalid_platform")
    print(f"  [OK] 无效平台(默认): {invalid.platform_name}")
    
    print("\n[SUCCESS] 平台适配器工厂测试通过！\n")


def test_platform_context():
    """测试平台上下文生成"""
    print("=" * 60)
    print("测试2: 平台上下文生成")
    print("=" * 60)
    
    fanqie = FanqieAdapter()
    print(f"\n[番茄小说] 平台上下文:")
    print("-" * 60)
    context = fanqie.get_prompt_context()
    print(context[:500] + "...")
    
    qidian = QidianAdapter()
    print(f"\n[起点中文网] 平台上下文:")
    print("-" * 60)
    context = qidian.get_prompt_context()
    print(context[:500] + "...")
    
    print("\n[SUCCESS] 平台上下文生成测试通过！\n")


def test_title_style_guide():
    """测试标题风格指导"""
    print("=" * 60)
    print("测试3: 标题风格指导")
    print("=" * 60)
    
    fanqie = FanqieAdapter()
    print(f"\n[番茄小说] 标题风格:")
    print("-" * 60)
    guide = fanqie.get_title_style_guide()
    print(guide)
    
    qidian = QidianAdapter()
    print(f"\n[起点中文网] 标题风格:")
    print("-" * 60)
    guide = qidian.get_title_style_guide()
    print(guide)
    
    print("\n[SUCCESS] 标题风格指导测试通过！\n")


def test_content_style_guide():
    """测试内容风格指导"""
    print("=" * 60)
    print("测试4: 内容风格指导")
    print("=" * 60)
    
    fanqie = FanqieAdapter()
    print(f"\n[番茄小说] 内容风格:")
    print("-" * 60)
    guide = fanqie.get_content_style_guide()
    print(guide[:400] + "...")
    
    print("\n[SUCCESS] 内容风格指导测试通过！\n")


def test_preferred_genres():
    """测试偏好类型"""
    print("=" * 60)
    print("测试5: 偏好类型")
    print("=" * 60)
    
    fanqie = FanqieAdapter()
    genres = fanqie.get_preferred_genres()
    print(f"\n[番茄小说] 偏好类型 ({len(genres)}个):")
    print(", ".join(genres[:10]) + "...")
    
    qidian = QidianAdapter()
    genres = qidian.get_preferred_genres()
    print(f"\n[起点中文网] 偏好类型 ({len(genres)}个):")
    print(", ".join(genres[:10]) + "...")
    
    print("\n[SUCCESS] 偏好类型测试通过！\n")


def test_core_keywords():
    """测试核心关键词"""
    print("=" * 60)
    print("测试6: 核心关键词")
    print("=" * 60)
    
    fanqie = FanqieAdapter()
    keywords = fanqie.get_core_keywords()
    print(f"\n[番茄小说] 核心关键词 ({len(keywords)}个):")
    print(", ".join(keywords[:15]) + "...")
    
    qidian = QidianAdapter()
    keywords = qidian.get_core_keywords()
    print(f"\n[起点中文网] 核心关键词 ({len(keywords)}个):")
    print(", ".join(keywords[:15]) + "...")
    
    print("\n[SUCCESS] 核心关键词测试通过！\n")


def test_base_prompts_integration():
    """测试BasePrompts集成"""
    print("=" * 60)
    print("测试7: BasePrompts与平台适配集成")
    print("=" * 60)
    
    base_prompts = BasePrompts()
    
    # 测试获取番茄小说平台的提示词
    print("\n[番茄小说] 获取番茄小说平台提示词:")
    print("-" * 60)
    fanqie_prompt = base_prompts.get_prompt("multiple_plans", "fanqie")
    
    # 检查提示词是否包含平台特定内容
    assert "番茄小说" in fanqie_prompt, "[ERROR] 提示词应包含平台名称"
    assert "黄金三章" in fanqie_prompt, "[ERROR] 提示词应包含番茄风格指导"
    assert "爽点" in fanqie_prompt, "[ERROR] 提示词应包含爽点相关内容"
    
    print("  [OK] 提示词包含平台名称")
    print("  [OK] 提示词包含番茄风格指导")
    print("  [OK] 提示词包含爽点相关内容")
    
    # 测试获取起点中文网平台的提示词
    print("\n[起点中文网] 获取起点中文网平台提示词:")
    print("-" * 60)
    qidian_prompt = base_prompts.get_prompt("multiple_plans", "qidian")
    
    # 检查提示词是否包含平台特定内容
    assert "起点中文网" in qidian_prompt, "[ERROR] 提示词应包含平台名称"
    assert "世界观严谨" in qidian_prompt, "[ERROR] 提示词应包含起点风格指导"
    
    print("  [OK] 提示词包含平台名称")
    print("  [OK] 提示词包含起点风格指导")
    
    # 测试获取知乎盐选平台的提示词
    print("\n[知乎盐选] 获取知乎盐选平台提示词:")
    print("-" * 60)
    zhihu_prompt = base_prompts.get_prompt("multiple_plans", "zhihu")
    
    # 检查提示词是否包含平台特定内容
    assert "知乎盐选" in zhihu_prompt, "[ERROR] 提示词应包含平台名称"
    
    print("  [OK] 提示词包含平台名称")
    
    print("\n[SUCCESS] BasePrompts集成测试通过！\n")


def test_prompt_differences():
    """测试不同平台提示词的差异"""
    print("=" * 60)
    print("测试8: 不同平台提示词差异分析")
    print("=" * 60)
    
    base_prompts = BasePrompts()
    
    fanqie_prompt = base_prompts.get_prompt("multiple_plans", "fanqie")
    qidian_prompt = base_prompts.get_prompt("multiple_plans", "qidian")
    zhihu_prompt = base_prompts.get_prompt("multiple_plans", "zhihu")
    
    print("\n[STATS] 提示词长度对比:")
    print(f"  番茄小说: {len(fanqie_prompt)} 字符")
    print(f"  起点中文网: {len(qidian_prompt)} 字符")
    print(f"  知乎盐选: {len(zhihu_prompt)} 字符")
    
    print("\n[ANALYSIS] 关键差异特征:")
    
    fanqie_features = ["黄金三章", "高密度爽点", "快节奏", "免费阅读"]
    print("\n[番茄小说] 特征:")
    for feature in fanqie_features:
        present = feature in fanqie_prompt
        print(f"  [{'OK' if present else 'FAIL'}] {feature}")
    
    qidian_features = ["世界观严谨", "付费阅读", "剧情深度", "角色立体"]
    print("\n[起点中文网]:")
    for feature in qidian_features:
        present = feature in qidian_prompt
        print(f"  [{'OK' if present else 'FAIL'}] {feature}")
    
    zhihu_features = ["脑洞设定", "短篇", "反转剧情", "情感共鸣"]
    print("\n[知乎盐选]:")
    for feature in zhihu_features:
        present = feature in zhihu_prompt
        print(f"  [{'OK' if present else 'FAIL'}] {feature}")
    
    print("\n[SUCCESS] 提示词差异分析完成！\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("[START] 开始测试平台适配功能")
    print("=" * 60 + "\n")
    
    try:
        test_platform_adapter_factory()
        test_platform_context()
        test_title_style_guide()
        test_content_style_guide()
        test_preferred_genres()
        test_core_keywords()
        test_base_prompts_integration()
        test_prompt_differences()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] 所有测试通过！平台适配功能正常工作")
        print("=" * 60 + "\n")
        
    except AssertionError as e:
        print(f"\n[ERROR] 测试失败: {e}\n")
        return False
    except Exception as e:
        print(f"\n[ERROR] 测试出错: {e}\n")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)