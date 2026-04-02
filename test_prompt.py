#!/usr/bin/env python3
"""
测试章节生成提示词是否正确包含标题格式要求
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 模拟必要的数据
novel_data = {
    "title": "测试小说",
    "protagonist": {"name": "测试主角", "traits": ["勇敢", "聪明"]},
    "genre": "玄幻",
    "tropes": {"核心套路": "废柴流"},
    "world_building": {"世界观": "修真世界"},
    "plan": {
        "outline_first_30": [
            {"chapter": 1, "title": "开局测试", "event": "主角获得金手指", "emotion": "期待"}
        ]
    },
    "character_design": {
        "protagonist": {"name": "测试主角", "core_traits": "勇敢正义"}
    },
    "emotion_curve": {}
}

# 测试 1: SimpleOptimizer
print("=" * 60)
print("测试 1: SimpleOptimizer.build_chapter_prompt")
print("=" * 60)

from web.services.market_driven.chapter_conversation_generator import SimpleOptimizer

simple_opt = SimpleOptimizer(novel_data)
prompt = simple_opt.build_chapter_prompt(1, {}, "")

print("提示词内容:")
print("-" * 40)
print(prompt)
print("-" * 40)

if "---标题---" in prompt and "---正文---" in prompt:
    print("✅ SimpleOptimizer 包含分隔符格式要求")
else:
    print("❌ SimpleOptimizer 缺少分隔符格式要求")
    if "---标题---" not in prompt:
        print("   - 缺少 '---标题---'")
    if "---正文---" not in prompt:
        print("   - 缺少 '---正文---'")

print()

# 测试 2: ChapterPromptOptimizer
print("=" * 60)
print("测试 2: ChapterPromptOptimizer.build_chapter_prompt")
print("=" * 60)

try:
    from web.services.market_driven.chapter_prompt_optimizer import ChapterPromptOptimizer
    
    opt = ChapterPromptOptimizer(novel_data)
    
    blueprint = {
        "chapter_number": 1,
        "beat_type": "SETUP",
        "emotion": "期待",
        "event": "测试事件"
    }
    
    prompt = opt.build_chapter_prompt(1, blueprint, "")
    
    print("提示词内容 (最后500字符):")
    print("-" * 40)
    print(prompt[-500:])
    print("-" * 40)
    
    if "---标题---" in prompt and "---正文---" in prompt:
        print("✅ ChapterPromptOptimizer 包含分隔符格式要求")
    else:
        print("❌ ChapterPromptOptimizer 缺少分隔符格式要求")
        if "---标题---" not in prompt:
            print("   - 缺少 '---标题---'")
        if "---正文---" not in prompt:
            print("   - 缺少 '---正文---'")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试 3: 重试提示词
print("=" * 60)
print("测试 3: 重试提示词模板")
print("=" * 60)

from web.services.market_driven.chapter_conversation_generator import ChapterConversationGenerator

# 创建实例来加载配置
try:
    ccg = ChapterConversationGenerator(
        api_client=None,
        novel_data=novel_data,
        session_id="test"
    )
    
    retry_prompt = ccg._get_retry_prompt_template(1)
    
    print("重试提示词内容:")
    print("-" * 40)
    print(retry_prompt)
    print("-" * 40)
    
    if "---标题---" in retry_prompt and "---正文---" in retry_prompt:
        print("✅ 重试提示词包含分隔符格式要求")
    else:
        print("❌ 重试提示词缺少分隔符格式要求")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()

# 测试 4: trope_prompt_builder
print("=" * 60)
print("测试 4: TropePromptBuilder 系统提示")
print("=" * 60)

try:
    from web.services.market_driven.trope_prompt_builder import TropePromptBuilder
    
    builder = TropePromptBuilder(novel_data)
    
    system_prompt = builder._build_chapter_prompt(
        novel_title="测试小说",
        chapter_num=1,
        protagonist_name="测试主角",
        emotion_arc={"type": "反转", "intensity": 8}
    )
    
    print("系统提示内容 (输出格式部分):")
    print("-" * 40)
    # 找到输出格式部分
    if "## ⚠️ 输出格式" in system_prompt:
        format_start = system_prompt.find("## ⚠️ 输出格式")
        print(system_prompt[format_start:format_start+400])
    else:
        print(system_prompt[-400:])
    print("-" * 40)
    
    if "---标题---" in system_prompt and "---正文---" in system_prompt:
        print("✅ TropePromptBuilder 系统提示包含分隔符格式要求")
    else:
        print("❌ TropePromptBuilder 系统提示缺少分隔符格式要求")
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("测试完成!")
print("=" * 60)
