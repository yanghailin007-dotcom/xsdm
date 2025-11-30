"""
Web API 调试脚本
用于测试和调试 Web 生成流程
"""

import sys
import os
from pathlib import Path
import json
import traceback

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)

# 启用详细日志
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["USE_MOCK_API"] = "true"

from src.utils.logger import get_logger
from src.core.NovelGenerator import NovelGenerator
from config.config import CONFIG

logger = get_logger("WebDebug")

def test_prepare_creative_seed():
    """测试创意种子准备函数"""
    print("\n" + "=" * 60)
    print("测试 1: 准备创意种子")
    print("=" * 60)

    # 模拟从web前端传入的配置
    test_configs = [
        {
            "name": "表单输入模式",
            "config": {
                "title": "测试小说",
                "synopsis": "这是一个测试简介",
                "core_setting": "这是核心设定",
                "core_selling_points": ["卖点1", "卖点2"],
                "total_chapters": 50
            }
        },
        {
            "name": "创意文件模式",
            "config": {
                "title": "创意1的小说",
                "synopsis": "简介",
                "total_chapters": 50,
                "use_creative_file": True,
                "creative_seed": {
                    "coreSetting": "凡人修仙传同人",
                    "coreSellingPoints": "观战悟道+修仙体系",
                    "completeStoryline": {
                        "opening": "开篇",
                        "development": "发展",
                        "climax": "高潮",
                        "ending": "结局"
                    }
                }
            }
        }
    ]

    for test in test_configs:
        print(f"\n--- {test['name']} ---")
        print(f"输入配置: {json.dumps(test['config'], ensure_ascii=False, indent=2)}")

        try:
            # 模拟 web_server.py 中的 _prepare_creative_seed 函数
            novel_config = test['config']

            from src.utils.seed_utils import ensure_seed_dict

            # 检查是否有从创意文件传入的完整创意数据
            if novel_config.get("use_creative_file") and novel_config.get("creative_seed"):
                creative_data = novel_config["creative_seed"]
                # Defensive normalization
                creative_data = ensure_seed_dict(creative_data)
                creative_seed = {
                    "coreSetting": creative_data.get("coreSetting", ""),
                    "coreSellingPoints": creative_data.get("coreSellingPoints", ""),
                    "completeStoryline": creative_data.get("completeStoryline", {}),
                    "targetAudience": creative_data.get("targetAudience", "网文读者"),
                    "novelTitle": novel_config.get("title", "未命名小说"),
                    "themes": creative_data.get("themes", []),
                    "writingStyle": creative_data.get("writingStyle", "现代网文风格")
                }
            else:
                # 原有逻辑：从表单输入构建创意种子
                constructed = {
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
                creative_seed = ensure_seed_dict(constructed)

            print(f"✅ 创意种子准备成功:")
            print(json.dumps(creative_seed, ensure_ascii=False, indent=2))

            # 检查数据类型
            print(f"\n类型检查:")
            print(f"  - creative_seed 类型: {type(creative_seed)}")
            print(f"  - 是否为字典: {isinstance(creative_seed, dict)}")

        except Exception as e:
            print(f"❌ 失败: {e}")
            traceback.print_exc()

def test_novel_generator_init():
    """测试 NovelGenerator 初始化"""
    print("\n" + "=" * 60)
    print("测试 2: NovelGenerator 初始化")
    print("=" * 60)

    try:
        generator = NovelGenerator(CONFIG)
        print("✅ NovelGenerator 初始化成功")
        print(f"  - 生成器类型: {type(generator)}")
        print(f"  - novel_data 类型: {type(generator.novel_data)}")
        return generator
    except Exception as e:
        print(f"❌ NovelGenerator 初始化失败: {e}")
        traceback.print_exc()
        return None

def test_full_auto_generation(generator):
    """测试完整的自动生成流程"""
    print("\n" + "=" * 60)
    print("测试 3: 完整生成流程（生成1章）")
    print("=" * 60)

    if not generator:
        print("❌ 跳过测试：生成器未初始化")
        return

    # 准备一个简单的创意种子
    creative_seed = {
        "coreSetting": "一个测试用的现代都市故事",
        "coreSellingPoints": "快节奏+爽点密集",
        "completeStoryline": {
            "opening": "主角发现自己拥有特殊能力",
            "development": "主角利用能力解决问题",
            "climax": "主角面临重大挑战",
            "ending": "主角成功克服挑战"
        },
        "targetAudience": "网文读者",
        "novelTitle": "测试小说",
        "themes": ["都市", "异能"],
        "writingStyle": "现代网文风格"
    }

    print(f"创意种子:")
    print(json.dumps(creative_seed, ensure_ascii=False, indent=2))

    try:
        print("\n开始生成...")
        success = generator.full_auto_generation(
            creative_seed=creative_seed,
            total_chapters=1,  # 只生成1章用于测试
            overwrite=True
        )

        if success:
            print("✅ 生成成功！")
            print(f"  - 小说标题: {generator.novel_data.get('novel_title', 'N/A')}")
            print(f"  - 生成章节数: {len(generator.novel_data.get('generated_chapters', {}))}")
        else:
            print("❌ 生成失败")

    except Exception as e:
        print(f"❌ 生成过程出错: {e}")
        traceback.print_exc()

def test_request_data_parsing():
    """测试请求数据解析"""
    print("\n" + "=" * 60)
    print("测试 4: 模拟 Flask request.json 解析")
    print("=" * 60)

    # 模拟各种可能的请求数据格式
    test_cases = [
        {
            "name": "正常字典",
            "data": {"title": "测试", "total_chapters": 50}
        },
        {
            "name": "空字典",
            "data": {}
        },
        {
            "name": "JSON字符串",
            "data": '{"title": "测试", "total_chapters": 50}'
        },
        {
            "name": "None",
            "data": None
        }
    ]

    for test in test_cases:
        print(f"\n--- {test['name']} ---")
        print(f"输入数据: {test['data']} (类型: {type(test['data'])})")

        try:
            # 模拟 Flask 的 request.json or {} 逻辑
            if isinstance(test['data'], str):
                # 如果是字符串，尝试解析
                config = json.loads(test['data']) or {}
            else:
                config = test['data'] or {}

            print(f"✅ 解析结果: {config} (类型: {type(config)})")

            # 测试 .get() 方法
            title = config.get("title", "默认标题")
            print(f"  - 获取标题: {title}")

        except Exception as e:
            print(f"❌ 解析失败: {e}")
            traceback.print_exc()

def main():
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🔍 Web API 调试工具")
    print("=" * 80)
    print(f"项目根目录: {project_root}")
    print(f"工作目录: {os.getcwd()}")
    print(f"使用模拟API: {CONFIG.get('use_mock_api', False)}")
    print("=" * 80)

    # 运行所有测试
    test_request_data_parsing()
    test_prepare_creative_seed()
    generator = test_novel_generator_init()
    test_full_auto_generation(generator)

    print("\n" + "=" * 80)
    print("✅ 所有调试测试完成")
    print("=" * 80)

    print("\n💡 调试建议:")
    print("1. 检查 Web 服务器日志输出（控制台）")
    print("2. 查看是否有 debug_task_*.json 文件生成")
    print("3. 使用浏览器开发者工具查看网络请求")
    print("4. 确认前端发送的 JSON 数据格式")
    print("\n📝 常见问题:")
    print("- 'str' object has no attribute 'get' → 某个应该是字典的变量实际上是字符串")
    print("- 检查 request.json 是否正确解析")
    print("- 检查 creative_seed 是否正确传递")

if __name__ == "__main__":
    main()
