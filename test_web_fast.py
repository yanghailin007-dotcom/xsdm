#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速Web端小说生成流程测试
Fast Web Novel Generation Flow Test
"""

import requests
import json
import time
import os
from datetime import datetime

# 设置环境变量使用模拟API
os.environ["USE_MOCK_API"] = "true"

class FastWebTest:
    """快速Web测试"""

    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.api_url = f"{self.base_url}/api"
        self.test_config = {
            "title": "异界医神传说",
            "synopsis": "现代医生穿越到修仙异界，用医学知识开创传奇",
            "core_setting": "现代医学与修仙异界的结合",
            "core_selling_points": ["穿越", "医学", "系统", "修仙"],
            "total_chapters": 3  # 测试用，只生成3章
        }

    def test_server_health(self):
        """测试服务器健康状态"""
        print("🔍 测试服务器健康状态...")
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 服务器状态: {data.get('status')}")
                return True
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            print(f"请先启动Web服务器: python run_web.py")
            return False

    def submit_generation_task(self):
        """提交生成任务"""
        print("📝 提交小说生成任务...")
        print(f"小说标题: {self.test_config['title']}")
        print(f"目标章节数: {self.test_config['total_chapters']}")

        try:
            response = requests.post(
                f"{self.api_url}/start-generation",
                json=self.test_config,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    task_id = data.get('task_id')
                    print(f"✅ 任务已提交，ID: {task_id}")
                    return task_id
                else:
                    print(f"❌ 任务提交失败: {data.get('error')}")
                    return None
            else:
                print(f"❌ 请求失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 提交任务异常: {e}")
            return None

    def monitor_progress(self, task_id, max_wait_time=120):
        """监控生成进度"""
        print(f"⏳ 监控任务进度，最大等待时间: {max_wait_time}秒")

        start_time = time.time()
        last_status = None

        while time.time() - start_time < max_wait_time:
            try:
                response = requests.get(
                    f"{self.api_url}/task/{task_id}/status",
                    timeout=10
                )

                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data.get('status')
                    progress = status_data.get('progress', 0)

                    if current_status != last_status:
                        elapsed = int(time.time() - start_time)
                        print(f"[{elapsed}s] 状态: {current_status} | 进度: {progress}%")
                        last_status = current_status

                    if current_status == 'completed':
                        print(f"✅ 生成完成！耗时: {int(time.time() - start_time)}秒")
                        return True
                    elif current_status == 'failed':
                        error = status_data.get('error', '未知错误')
                        print(f"❌ 生成失败: {error}")
                        return False

                time.sleep(3)  # 每3秒检查一次

            except Exception as e:
                print(f"❌ 监控异常: {e}")
                return False

        print("⏰ 监控超时")
        return False

    def verify_results(self, task_id):
        """验证生成结果"""
        print("🔍 验证生成结果...")

        try:
            response = requests.get(
                f"{self.api_url}/task/{task_id}/status",
                timeout=10
            )

            if response.status_code == 200:
                task_data = response.json()
                novel_data = task_data.get('novel_data', {})

                # 基本信息
                title = novel_data.get('novel_title', '未知')
                print(f"📚 小说标题: {title}")

                # 章节信息
                chapters = novel_data.get('generated_chapters', {})
                chapter_count = len(chapters)
                print(f"📖 生成章节数: {chapter_count}")

                if chapter_count == 0:
                    print("❌ 没有生成任何章节")
                    return False

                total_words = 0
                all_valid = True

                for chapter_num, chapter in chapters.items():
                    content = chapter.get('content', '')
                    outline = chapter.get('outline', {})
                    assessment = chapter.get('assessment', {})

                    word_count = len(content)
                    total_words += word_count

                    chapter_title = outline.get('章节标题', f'第{chapter_num}章')
                    score = assessment.get('整体评分', 0) if assessment else 0

                    has_content = len(content) > 100
                    has_outline = bool(outline)
                    has_assessment = bool(assessment)

                    status = "✅" if (has_content and has_outline and has_assessment) else "❌"
                    print(f"   {status} 第{chapter_num}章: {chapter_title}")
                    print(f"      字数: {word_count} | 评分: {score}")

                    if not (has_content and has_outline and has_assessment):
                        all_valid = False

                print(f"\n📊 总结:")
                print(f"   总章节数: {chapter_count}")
                print(f"   总字数: {total_words}")
                print(f"   数据完整性: {'✅ 完整' if all_valid else '❌ 不完整'}")

                return all_valid
            else:
                print(f"❌ 获取结果失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 验证结果异常: {e}")
            return False

    def test_additional_endpoints(self):
        """测试其他API端点"""
        print("\n🔍 测试其他API端点...")

        endpoints = [
            ("/api/tasks", "任务列表"),
            ("/api/projects", "项目列表"),
            ("/api/novel/summary", "小说摘要"),
            ("/api/chapters", "章节列表"),
        ]

        success_count = 0
        for endpoint, description in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    item_count = len(data) if isinstance(data, list) else len(data.keys()) if isinstance(data, dict) else 1
                    print(f"   ✅ {description}: {item_count} 项")
                    success_count += 1
                else:
                    print(f"   ⚠️  {description}: 状态码 {response.status_code}")
            except Exception as e:
                print(f"   ❌ {description}: {e}")

        print(f"\n额外端点测试: {success_count}/{len(endpoints)} 通过")
        return success_count == len(endpoints)

    def run_full_test(self):
        """运行完整测试"""
        print("=" * 60)
        print("🚀 快速Web端小说生成流程测试")
        print("=" * 60)
        print(f"⚡ 测试模式: 模拟API (快速，无真实API消耗)")

        # 1. 健康检查
        if not self.test_server_health():
            return False

        # 2. 提交任务
        task_id = self.submit_generation_task()
        if not task_id:
            return False

        # 3. 监控进度
        if not self.monitor_progress(task_id):
            print("⚠️ 生成过程未完成，继续验证部分结果...")

        # 4. 验证结果
        success = self.verify_results(task_id)

        # 5. 测试其他端点
        self.test_additional_endpoints()

        # 总结
        print("\n" + "=" * 60)
        if success:
            print("✅ 测试成功！Web端小说生成流程正常")
        else:
            print("⚠️  测试部分通过，某些功能可能需要调整")
        print("=" * 60)

        return success

def main():
    """主函数"""
    print("📌 注意：请确保Web服务器已启动 (python run_web.py)")
    input("按回车键开始测试...")

    tester = FastWebTest()
    success = tester.run_full_test()

    if success:
        print("\n🎉 建议下一步：")
        print("   1. 在浏览器中访问 http://localhost:5000")
        print("   2. 尝试手动测试前端界面")
        print("   3. 运行完整版测试: python test_web_full_flow.py")
    else:
        print("\n🔧 故障排除：")
        print("   1. 检查Web服务器是否正常启动")
        print("   2. 确认端口5000没有被占用")
        print("   3. 查看服务器日志获取详细错误信息")

    input("\n按回车键退出...")

if __name__ == "__main__":
    main()