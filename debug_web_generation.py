#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
网页端调试工具 - 完全模拟Web端的小说生成流程
Debug Tool for Web - Simulate Complete Web Novel Generation Process
"""

import os
import sys
import json
import time
from datetime import datetime

# 设置环境变量
os.environ["USE_MOCK_API"] = "true"

# 添加项目路径
sys.path.insert(0, '.')

def debug_web_generation(novel_config):
    """调试Web端生成流程，完全模拟网页端行为"""
    print("=" * 80)
    print("网页端调试工具 - 模拟完整Web生成流程")
    print("=" * 80)
    print(f"⚡ 模拟模式: 已启用")
    print(f"📝 输入配置: {json.dumps(novel_config, ensure_ascii=False, indent=2)}")
    print()

    try:
        # 导入Web服务器中的组件
        from src.utils.logger import get_logger
        from src.core.NovelGenerator import NovelGenerator
        from config.config import CONFIG

        logger = get_logger("DebugTool")

        # 设置配置
        CONFIG["use_mock_api"] = True
        logger.info("✅ 调试工具启动，使用模拟API")

        # 步骤1: 创建NovelGenerator (模拟web服务器的操作)
        print("[步骤1/3] 创建NovelGenerator...")
        generator = NovelGenerator(CONFIG)
        print(f"   ✅ 成功创建，模拟API模式: {generator.use_mock_api}")
        print(f"   ✅ API客户端类型: {type(generator.api_client).__name__}")

        # 步骤2: 准备创意种子 (模拟web_server的_prepare_creative_seed方法)
        print("\n[步骤2/3] 准备创意种子...")

        creative_seed = {
            "coreSetting": novel_config.get("core_setting", ""),
            "coreSellingPoints": ", ".join(novel_config.get("core_selling_points", [])),
            "completeStoryline": {
                "opening": f"故事开始于{novel_config.get('synopsis', '')}",
                "development": "故事发展",
                "climax": "故事高潮",
                "ending": "故事结局"
            },
            "targetAudience": "网文读者",
            "novelTitle": novel_config.get("title", "未命名小说"),
            "themes": [],
            "writingStyle": "现代网文风格"
        }

        print(f"   📋 创意种子准备完成")
        print(f"   📚 小说标题: {creative_seed['novelTitle']}")
        print(f"   ⚙️  核心设定: {creative_seed['coreSetting']}")
        print(f"   🎯 核心卖点: {creative_seed['coreSellingPoints']}")

        # 步骤3: 执行完整生成 (模拟web服务器的_run_generation_task)
        print(f"\n[步骤3/3] 开始生成小说...")
        print(f"   目标章节数: {novel_config.get('total_chapters', 50)}")

        start_time = time.time()

        try:
            success = generator.full_auto_generation(
                creative_seed,
                novel_config.get("total_chapters", 50)
            )

            generation_time = time.time() - start_time
            print(f"\n⏱️  生成耗时: {generation_time:.1f}秒")
            print(f"📊 生成结果: {'成功' if success else '失败'}")

            # 步骤4: 分析结果
            if success and hasattr(generator, 'novel_data'):
                novel_data = generator.novel_data
                print(f"\n📚 小说数据分析:")
                print(f"   📖 小说标题: {novel_data.get('novel_title', '未知')}")

                chapters = novel_data.get('generated_chapters', {})
                print(f"   📄 生成章节数: {len(chapters)}")

                if chapters:
                    total_words = 0
                    for chapter_num, chapter in sorted(chapters.items()):
                        content = chapter.get('content', '')
                        outline = chapter.get('outline', {})
                        assessment = chapter.get('assessment', {})

                        word_count = len(content)
                        total_words += word_count

                        chapter_title = outline.get('章节标题', f'第{chapter_num}章')
                        score = assessment.get('整体评分', 0) if assessment else 0

                        print(f"     ✅ 第{chapter_num}章: {chapter_title}")
                        print(f"        📝 字数: {word_count}")
                        print(f"        ⭐ 评分: {score}")

                    print(f"   📊 总字数: {total_words}")
                    print(f"   📈 平均字数/章: {total_words // len(chapters)}")

                    # 保存结果到文件
                    output_file = f"debug_generation_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(novel_data, f, ensure_ascii=False, indent=2)
                    print(f"   💾 结果已保存: {output_file}")
                else:
                    print(f"   ❌ 未生成任何章节")

                # 分析其他数据
                worldview = novel_data.get('worldview', {})
                characters = novel_data.get('characters', {})
                print(f"   🌍 世界观数据: {'有' if worldview else '无'}")
                print(f"   👥 人物数据: {len(characters)} 个")

            else:
                print(f"   ❌ 生成失败或无数据")
                print(f"   🐛 请查看上面的错误日志")

            return success

        except Exception as generation_error:
            print(f"\n❌ 生成过程异常:")
            print(f"   错误类型: {type(generation_error).__name__}")
            print(f"   错误信息: {str(generation_error)}")

            # 输出详细追踪信息
            import traceback
            print(f"   详细追踪:\n{traceback.format_exc()}")

            return False

    except Exception as e:
        print(f"\n💥 调试工具异常:")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")
        import traceback
        print(f"   详细追踪:\n{traceback.format_exc()}")
        return False

def main():
    """主函数"""
    print("🔧 网页端小说生成调试工具")
    print("💡 使用方法:")
    print("   1. 直接运行: 使用默认配置")
    print("   2. 修改配置: 编辑test_config")
    print("   3. 查看日志: 观察详细错误信息")
    print()

    # 默认测试配置 (与网页端完全一致)
    test_config = {
        "title": "异界医神传说",
        "synopsis": "现代医生穿越到修仙异界，用医学知识开创传奇",
        "core_setting": "现代医学与修仙异界的结合",
        "core_selling_points": ["穿越", "医学", "系统", "修仙"],
        "total_chapters": 2  # 测试用，只生成2章
    }

    # 可以在这里修改配置
    # test_config["total_chapters"] = 1
    # test_config["title"] = "你的自定义标题"

    print("📋 使用配置:")
    for key, value in test_config.items():
        print(f"   {key}: {value}")

    print("\n🚀 开始调试...")
    success = debug_web_generation(test_config)

    print("\n" + "=" * 80)
    if success:
        print("✅ 调试成功! 模拟Web端流程正常工作")
        print("💡 建议:")
        print("   1. 检查浏览器中 http://localhost:5000 是否正常")
        print("   2. 在网页端尝试相同的配置")
        print("   3. 查看生成的文件内容")
    else:
        print("❌ 调试发现问题")
        print("🔧 故障排除:")
        print("   1. 查看上面的详细错误信息")
        print("   2. 检查依赖是否完整安装")
        print("   3. 确认环境变量设置正确")

    print("=" * 80)

if __name__ == "__main__":
    main()