"""测试Web端生成流程诊断"""
import sys
import requests
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

def print_safe(text):
    """安全打印"""
    try:
        print(text)
    except UnicodeEncodeError:
        clean_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(clean_text)

def test_web_generation_flow():
    """测试完整的web生成流程"""
    print("=" * 70)
    print("Web端生成流程诊断测试")
    print("=" * 70)

    base_url = "http://localhost:5000"

    # 测试1: 检查服务是否运行
    print("\n[1] 检查Web服务状态...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print_safe("  [OK] Web服务正在运行")
        else:
            print(f"  [WARN] 服务响应异常: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("  [ERROR] 无法连接到Web服务")
        print("  请先运行: python run_web.py")
        return False
    except Exception as e:
        print(f"  [ERROR] 连接错误: {e}")
        return False

    # 测试2: 检查API端点
    print("\n[2] 检查API端点...")
    endpoints_to_test = [
        ("/api/start-generation", "开始生成接口"),
        ("/api/generate-chapters", "章节生成接口"),
        ("/api/health", "健康检查接口"),
        ("/api/tasks", "任务列表接口")
    ]

    for endpoint, description in endpoints_to_test:
        try:
            response = requests.options(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 204, 405]:  # 405表示方法不允许但端点存在
                print(f"  [OK] {description}: {endpoint}")
            else:
                print(f"  [WARN] {description}响应异常: {response.status_code}")
        except Exception as e:
            print(f"  [ERROR] {description}检查失败: {e}")

    # 测试3: 测试开始生成流程
    print("\n[3] 测试开始生成流程...")

    import time
    test_title = f"测试小说_{int(time.time())}"  # 使用时间戳确保唯一性

    generation_request = {
        "title": test_title,
        "prompt": "一个关于修仙的故事，主角从凡人逐步成长为仙界强者",
        "total_chapters": 5,
        "start_chapter": 1,
        "end_chapter": 3
    }

    try:
        print("  发送生成请求...")
        response = requests.post(
            f"{base_url}/api/start-generation",
            json=generation_request,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                print_safe("  [OK] 生成任务已创建")
                task_id = result.get("task_id", "未知")
                print(f"  - 任务ID: {task_id}")

                # 查询任务状态
                if task_id != "未知":
                    import time
                    print("  等待2秒后查询任务状态...")
                    time.sleep(2)

                    status_response = requests.get(
                        f"{base_url}/api/task/{task_id}/status",
                        timeout=5
                    )
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        print(f"  - 任务状态: {status_data.get('status', '未知')}")
                        print(f"  - 进度: {status_data.get('progress', 0)}%")
            else:
                print(f"  [WARN] 生成任务创建失败: {result.get('message', '未知错误')}")
        else:
            print(f"  [ERROR] 请求失败: {response.status_code}")
            print(f"  响应: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("  [ERROR] 请求超时（超过30秒）")
    except Exception as e:
        print(f"  [ERROR] 大纲生成测试失败: {e}")

    # 测试4: 检查常见问题
    print("\n[4] 检查常见问题...")

    # 检查是否有配置文件
    config_files = [
        "config/config.json",
        "config/doubao_config.json",
        ".env"
    ]

    for config_file in config_files:
        config_path = BASE_DIR / config_file
        if config_path.exists():
            print(f"  [OK] 配置文件存在: {config_file}")
        else:
            print(f"  [WARN] 配置文件缺失: {config_file}")

    # 检查必要的目录
    required_dirs = [
        "data",
        "output",
        "resources",
        "static"
    ]

    for dir_name in required_dirs:
        dir_path = BASE_DIR / dir_name
        if dir_path.exists():
            print(f"  [OK] 目录存在: {dir_name}/")
        else:
            print(f"  [WARN] 目录缺失: {dir_name}/")

    print("\n" + "=" * 70)
    print_safe("诊断测试完成")
    print("=" * 70)

    return True

if __name__ == "__main__":
    test_web_generation_flow()
