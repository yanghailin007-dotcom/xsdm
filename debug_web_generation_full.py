"""网页端生成流程完整模拟测试 - Debug版本"""

import sys
import json
import time
import requests
from pathlib import Path
import traceback

# 添加项目路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def print_safe(text):
    """安全打印，避免编码错误"""
    try:
        print(text)
    except UnicodeEncodeError:
        clean_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(clean_text)

def print_separator(title=""):
    """打印分隔符"""
    print(f"\n{'='*20} {title} {'='*20}")

def test_web_server_debug():
    """完整的网页端模拟测试，用于debug错误"""
    print_separator("网页端生成流程 - 完整模拟测试 (Debug版本)")

    base_url = "http://localhost:5000"

    # 1. 检查服务状态
    print_separator("Step 1: 检查Web服务状态")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✅ Web服务运行正常 (状态码: {response.status_code})")

        # 检查API端点
        print("🔍 检查API端点:")
        endpoints_to_check = [
            ("/api/start-generation", "POST", "启动生成"),
            ("/api/task", "GET", "任务状态"),
            ("/api/health", "GET", "健康检查")
        ]

        for endpoint, method, desc in endpoints_to_check:
            try:
                if method == "POST":
                    # 对于POST端点，使用OPTIONS检查是否支持
                    response = requests.options(f"{base_url}{endpoint}", timeout=3)
                else:
                    response = requests.get(f"{base_url}{endpoint}", timeout=3)

                if response.status_code in [200, 201, 204, 405]:
                    print(f"  ✅ {desc}端点正常: {endpoint}")
                else:
                    print(f"  ⚠️ {desc}端点异常: {response.status_code}")

            except Exception as e:
                print(f"  ❌ {desc}端点检查失败: {e}")

    except Exception as e:
        print(f"❌ Web服务连接失败: {e}")
        print("请先运行: python run_web.py")
        return False

    # 2. 测试正常的生成请求
    print_separator("Step 2: 测试正常生成请求")

    # 使用时间戳创建唯一标题，避免重复
    import uuid
    unique_title = f"Debug测试小说_{str(uuid.uuid4())[:8]}"

    normal_request = {
        "title": unique_title,
        "prompt": "这是一个用于debug的测试故事，主角名叫林云，是一个修仙者",
        "total_chapters": 3,
        "start_chapter": 1,
        "end_chapter": 3
    }

    print("📤 发送正常生成请求:")
    print(json.dumps(normal_request, ensure_ascii=False, indent=2))
    print()

    try:
        response = requests.post(
            f"{base_url}/api/start-generation",
            json=normal_request,
            timeout=30
        )

        print(f"📥 响应状态码: {response.status_code}")
        print(f"📥 响应头: {dict(response.headers)}")

        if response.status_code == 200:
            try:
                result = response.json()
                print("📥 响应JSON:")
                print(json.dumps(result, ensure_ascii=False, indent=2))

                if result.get("success"):
                    print("✅ 请求成功，任务已创建")
                    task_id = result.get("task_id")
                    print(f"任务ID: {task_id}")

                    # 查询任务状态
                    if task_id:
                        return test_task_status(base_url, task_id)
                else:
                    print(f"❌ 请求失败: {result}")

            except json.JSONDecodeError as e:
                print("❌ 无法解析JSON响应")
                print(f"原始响应: {response.text[:500]}")
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"响应内容: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("❌ 请求超时（超过30秒）")
    except Exception as e:
        print(f"❌ 请求异常: {e}")
        traceback.print_exc()

    return False

def test_task_status(base_url, task_id):
    """测试任务状态查询"""
    print_separator(f"Step 3: 测试任务状态查询 (Task ID: {task_id})")

    max_attempts = 10
    for attempt in range(max_attempts):
        print(f"🔍 查询任务状态 (第{attempt+1}次)...")

        try:
            response = requests.get(
                f"{base_url}/api/task/{task_id}/status",
                timeout=10
            )

            print(f"  状态码: {response.status_code}")

            if response.status_code == 200:
                try:
                    status_data = response.json()
                    print(f"  任务状态: {status_data}")

                    status = status_data.get("status", "unknown")
                    progress = status_data.get("progress", 0)

                    print(f"  📊 进度: {progress}%")
                    print(f"  📋 状态: {status}")

                    if status in ["completed", "failed"]:
                        print(f"✅ 任务{status}")
                        if status == "failed":
                            error_msg = status_data.get("error", "未知错误")
                            print(f"❌ 错误信息: {error_msg}")
                        return status == "completed"
                    elif status == "running":
                        print("⏳ 任务正在运行，等待下一检查...")
                        time.sleep(2)
                    else:
                        print(f"❓ 未知状态: {status}")
                        time.sleep(1)

                except json.JSONDecodeError:
                    print("❌ 无法解析状态JSON响应")
                    print(f"原始响应: {response.text[:200]}")
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                print(f"响应内容: {response.text[:200]}")
                time.sleep(1)

        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            time.sleep(1)

    print("⏰ 超时：任务状态查询完成")
    return False

def test_web_server_direct_api():
    """直接测试Web服务器API，无需通过HTTP"""
    print_separator("Step 4: 直接测试Web服务器API")

    try:
        # 模拟直接调用Web服务器的逻辑
        from web.web_server import NovelGenerationManager

        manager = NovelGenerationManager()

        # 测试数据
        test_config = {
            "title": "直接API测试",
            "prompt": "这是一个直接API调用的测试",
            "total_chapters": 2
        }

        print("🧪 直接调用start_generation...")
        task_id = manager.start_generation(test_config)
        print(f"✅ 生成任务ID: {task_id}")

        # 查询状态
        print("🔍 查询任务状态...")
        status = manager.get_task_status(task_id)
        print(f"📋 任务状态: {status}")

        return True

    except Exception as e:
        print(f"❌ 直接API测试失败: {e}")
        traceback.print_exc()
        return False

def test_creative_seed_issue():
    """专门测试creative_seed相关的问题"""
    print_separator("Step 5: 测试creative_seed处理问题")

    try:
        # 模拟_prepare_creative_seed的逻辑
        from web.web_server import NovelGenerationManager

        manager = NovelGenerationManager()

        # 测试各种可能的novel_config格式
        test_configs = [
            # 正常格式
            {
                "title": "测试1",
                "prompt": "简单的prompt",
                "total_chapters": 2
            },
            # 包含creative_seed的格式
            {
                "title": "测试2",
                "prompt": "prompt with seed",
                "creative_seed": "这是字符串种子",
                "total_chapters": 2
            },
            # 字典格式的creative_seed
            {
                "title": "测试3",
                "prompt": "prompt with dict seed",
                "creative_seed": {
                    "coreSetting": "设置",
                    "coreSellingPoints": "卖点"
                },
                "total_chapters": 2
            }
        ]

        for i, config in enumerate(test_configs, 1):
            print(f"\n测试配置{i}:")
            print(json.dumps(config, ensure_ascii=False, indent=2))

            try:
                seed = manager._prepare_creative_seed(config)
                print(f"✅ 创意种子准备成功: {type(seed)}")
                print(f"种子内容: {seed}")

            except Exception as e:
                print(f"❌ 创意种子准备失败: {e}")
                traceback.print_exc()

        return True

    except Exception as e:
        print(f"❌ 创意种子测试失败: {e}")
        traceback.print_exc()
        return False

def test_generator_direct():
    """直接测试NovelGenerator生成功能"""
    print_separator("Step 6: 直接测试NovelGenerator")

    try:
        from src.core.NovelGenerator import NovelGenerator
        from src.config import CONFIG

        print("🔧 初始化NovelGenerator...")
        generator = NovelGenerator(CONFIG)
        print("✅ NovelGenerator初始化成功")

        # 测试基本配置
        creative_seed = {
            "coreSetting": "修仙世界，主角林云是散修",
            "coreSellingPoints": "宗门秘境，传承觉醒，命运转折"
        }

        print("🚀 开始全自动生成测试...")
        success = generator.full_auto_generation(creative_seed, 2, False)
        print(f"生成结果: {'✅ 成功' if success else '❌ 失败'}")

        if success:
            print("📖 生成的章节数:", len(generator.novel_data.get("generated_chapters", {})))

        return success

    except Exception as e:
        print(f"❌ NovelGenerator测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print_safe("[DEBUG] 开始网页端生成流程Debug测试...")
    print_safe("[TARGET] 目标: 找出并修复 'str' object has no attribute 'get' 错误")

    # 执行各个测试步骤
    tests = [
        ("Web服务器连接", test_web_server_debug),
        ("Web服务器直接API", test_web_server_direct_api),
        ("创意种子处理", test_creative_seed_issue),
        ("NovelGenerator直接测试", test_generator_direct),
    ]

    results = []
    for test_name, test_func in tests:
        print_separator(f"开始测试: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            traceback.print_exc()
            results.append((test_name, False))

    # 总结
    print_separator("测试结果总结")
    print("📊 测试结果:")
    all_passed = True
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False

    print()
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败，需要进一步调试。")

        # 提供调试建议
        print("\n🔍 调试建议:")
        print("1. 检查Web服务器日志中的错误信息")
        print("2. 验证CONFIG配置是否正确")
        print("3. 检查NovelGenerator的初始化参数")
        print("4. 查看creative_seed处理的逻辑")

    return all_passed

if __name__ == "__main__":
    main()