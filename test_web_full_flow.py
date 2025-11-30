#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整的网页端小说生成流程测试
测试从Web API发起到完整生成小说的全流程
"""

import json
import time
import requests
import sys
from datetime import datetime
from pathlib import Path

class WebNovelGenerationTester:
    """Web端小说生成完整流程测试器"""

    def __init__(self, base_url='http://localhost:5000'):
        self.base_url = base_url
        self.api_url = f'{base_url}/api'
        self.task_id = None
        self.test_results = {
            "start_time": datetime.now().isoformat(),
            "tests_passed": [],
            "tests_failed": [],
            "generation_data": {}
        }

    def print_section(self, title):
        """打印分隔线"""
        print('\n' + '='*70)
        print(f'  {title}')
        print('='*70)

    def print_step(self, step_num, description):
        """打印步骤"""
        print(f'\n[步骤 {step_num}] {description}')
        print('-' * 70)

    def test_server_health(self):
        """测试1: 检查服务器健康状态"""
        self.print_step(1, '检查Web服务器健康状态')

        try:
            response = requests.get(f'{self.api_url}/health', timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f'✅ 服务器状态: {data.get("status")}')
                print(f'   时间戳: {data.get("timestamp")}')
                self.test_results["tests_passed"].append("server_health")
                return True
            else:
                print(f'❌ 服务器响应异常: {response.status_code}')
                self.test_results["tests_failed"].append("server_health")
                return False
        except Exception as e:
            print(f'❌ 无法连接到服务器: {e}')
            print(f'   请确保Web服务已启动: python run_web.py')
            self.test_results["tests_failed"].append("server_health")
            return False

    def submit_generation_task(self):
        """测试2: 提交小说生成任务"""
        self.print_step(2, '提交小说生成任务')

        # 准备测试数据
        generation_config = {
            "title": "测试小说：穿越异世的医生",
            "synopsis": "现代医生穿越到异世界，用医学知识开创新的治疗体系，成为传奇医者",
            "core_setting": "现代医生穿越到魔法世界，医学知识与魔法结合",
            "core_selling_points": ["穿越", "医学", "魔法", "成长"],
            "total_chapters": 3  # 测试用，只生成3章
        }

        print(f'📝 小说标题: {generation_config["title"]}')
        print(f'📊 目标章节数: {generation_config["total_chapters"]}')
        print(f'🎯 核心卖点: {", ".join(generation_config["core_selling_points"])}')

        try:
            response = requests.post(
                f'{self.api_url}/start-generation',
                json=generation_config,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.task_id = data.get('task_id')
                    print(f'✅ 任务已提交')
                    print(f'   任务ID: {self.task_id}')
                    print(f'   状态: {data.get("status")}')
                    self.test_results["tests_passed"].append("submit_task")
                    self.test_results["generation_data"]["task_id"] = self.task_id
                    self.test_results["generation_data"]["config"] = generation_config
                    return True
                else:
                    print(f'❌ 任务提交失败: {data.get("error")}')
                    self.test_results["tests_failed"].append("submit_task")
                    return False
            else:
                print(f'❌ 请求失败: {response.status_code}')
                print(f'   响应: {response.text}')
                self.test_results["tests_failed"].append("submit_task")
                return False

        except Exception as e:
            print(f'❌ 提交任务异常: {e}')
            self.test_results["tests_failed"].append("submit_task")
            return False

    def monitor_generation_progress(self, max_wait_time=300):
        """测试3: 监控生成进度"""
        self.print_step(3, '监控生成进度')

        if not self.task_id:
            print('❌ 没有有效的任务ID')
            self.test_results["tests_failed"].append("monitor_progress")
            return False

        print(f'⏳ 开始监控任务: {self.task_id}')
        print(f'   最大等待时间: {max_wait_time}秒')

        start_time = time.time()
        last_status = None
        last_progress = 0

        try:
            while time.time() - start_time < max_wait_time:
                # 获取任务状态
                response = requests.get(
                    f'{self.api_url}/task/{self.task_id}/status',
                    timeout=10
                )

                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data.get('status')
                    current_progress = status_data.get('progress', 0)

                    # 只在状态或进度变化时打印
                    if current_status != last_status or current_progress != last_progress:
                        elapsed = int(time.time() - start_time)
                        print(f'   [{elapsed}s] 状态: {current_status} | 进度: {current_progress}%')

                        if status_data.get('error'):
                            print(f'   ⚠️  错误信息: {status_data.get("error")}')

                        last_status = current_status
                        last_progress = current_progress

                    # 检查是否完成
                    if current_status == 'completed':
                        print(f'✅ 生成完成！')
                        print(f'   总耗时: {int(time.time() - start_time)}秒')
                        self.test_results["tests_passed"].append("monitor_progress")
                        self.test_results["generation_data"]["status"] = status_data
                        return True

                    # 检查是否失败
                    if current_status == 'failed':
                        print(f'❌ 生成失败')
                        print(f'   错误: {status_data.get("error")}')
                        self.test_results["tests_failed"].append("monitor_progress")
                        return False

                # 等待后再次检查
                time.sleep(5)

            # 超时
            print(f'⏰ 监控超时（{max_wait_time}秒）')
            print(f'   最后状态: {last_status}')
            print(f'   最后进度: {last_progress}%')
            self.test_results["tests_failed"].append("monitor_progress_timeout")
            return False

        except Exception as e:
            print(f'❌ 监控异常: {e}')
            self.test_results["tests_failed"].append("monitor_progress")
            return False

    def verify_generated_data(self):
        """测试4: 验证生成的数据"""
        self.print_step(4, '验证生成的数据')

        if not self.task_id:
            print('❌ 没有有效的任务ID')
            self.test_results["tests_failed"].append("verify_data")
            return False

        try:
            # 获取任务详情
            response = requests.get(
                f'{self.api_url}/task/{self.task_id}/status',
                timeout=10
            )

            if response.status_code != 200:
                print(f'❌ 获取任务详情失败: {response.status_code}')
                self.test_results["tests_failed"].append("verify_data")
                return False

            task_data = response.json()
            novel_data = task_data.get('novel_data', {})

            # 验证基本信息
            print('\n📚 小说基本信息:')
            novel_title = novel_data.get('novel_title', '未知')
            print(f'   标题: {novel_title}')
            print(f'   简介: {novel_data.get("story_synopsis", "无")[:100]}...')

            # 验证章节数据
            generated_chapters = novel_data.get('generated_chapters', {})
            chapter_count = len(generated_chapters)
            print(f'\n📖 章节信息:')
            print(f'   已生成章节数: {chapter_count}')

            if chapter_count == 0:
                print('❌ 没有生成任何章节')
                self.test_results["tests_failed"].append("verify_data_no_chapters")
                return False

            # 验证每个章节的数据完整性
            all_chapters_valid = True
            for chapter_num in sorted(generated_chapters.keys()):
                chapter = generated_chapters[chapter_num]

                # 检查必要字段
                has_outline = 'outline' in chapter
                has_content = 'content' in chapter and len(chapter['content']) > 0
                has_assessment = 'assessment' in chapter

                chapter_title = chapter.get('outline', {}).get('章节标题', f'第{chapter_num}章')
                content_length = len(chapter.get('content', ''))
                score = chapter.get('assessment', {}).get('整体评分', 0)

                status = '✅' if (has_outline and has_content and has_assessment) else '❌'
                print(f'   {status} 第{chapter_num}章: {chapter_title}')
                print(f'      字数: {content_length} | 评分: {score}')

                if not (has_outline and has_content and has_assessment):
                    all_chapters_valid = False
                    print(f'      ⚠️  数据不完整: outline={has_outline}, content={has_content}, assessment={has_assessment}')

            # 验证世界观数据
            print(f'\n🌍 世界观数据:')
            worldview = novel_data.get('worldview', {})
            print(f'   世界设定: {"✅" if worldview.get("world_setting") else "❌"}')
            print(f'   势力体系: {"✅" if worldview.get("faction_system") else "❌"}')
            print(f'   能力体系: {"✅" if worldview.get("ability_system") else "❌"}')

            # 验证人物数据
            print(f'\n👥 人物数据:')
            characters = novel_data.get('characters', {})
            print(f'   人物数量: {len(characters)}')
            for char_name, char_data in list(characters.items())[:3]:  # 只显示前3个
                print(f'   - {char_name}: {char_data.get("角色定位", "未知")}')

            # 总结验证结果
            print(f'\n📊 数据验证总结:')
            print(f'   章节完整性: {"✅ 通过" if all_chapters_valid else "❌ 失败"}')
            print(f'   世界观完整性: {"✅ 通过" if worldview else "⚠️  部分缺失"}')
            print(f'   人物完整性: {"✅ 通过" if characters else "⚠️  部分缺失"}')

            if all_chapters_valid:
                self.test_results["tests_passed"].append("verify_data")
                self.test_results["generation_data"]["novel_data"] = {
                    "title": novel_title,
                    "chapter_count": chapter_count,
                    "total_words": sum(len(ch.get('content', '')) for ch in generated_chapters.values()),
                    "avg_score": sum(ch.get('assessment', {}).get('整体评分', 0) for ch in generated_chapters.values()) / chapter_count if chapter_count > 0 else 0
                }
                return True
            else:
                self.test_results["tests_failed"].append("verify_data_incomplete")
                return False

        except Exception as e:
            print(f'❌ 验证数据异常: {e}')
            import traceback
            traceback.print_exc()
            self.test_results["tests_failed"].append("verify_data")
            return False

    def test_api_endpoints(self):
        """测试5: 测试其他API端点"""
        self.print_step(5, '测试其他API端点')

        endpoints_to_test = [
            ('GET', '/api/tasks', '获取任务列表'),
            ('GET', '/api/projects', '获取项目列表'),
            ('GET', '/api/novel/summary', '获取小说摘要'),
            ('GET', '/api/chapters', '获取章节列表'),
        ]

        all_passed = True
        for method, endpoint, description in endpoints_to_test:
            try:
                url = f'{self.base_url}{endpoint}'
                response = requests.request(method, url, timeout=10)

                if response.status_code == 200:
                    data = response.json()
                    print(f'✅ {description}: {endpoint}')
                    if isinstance(data, list):
                        print(f'   返回数量: {len(data)}')
                    elif isinstance(data, dict):
                        print(f'   返回字段: {len(data)}')
                else:
                    print(f'⚠️  {description}: {endpoint} (状态码: {response.status_code})')

            except Exception as e:
                print(f'❌ {description}: {endpoint} - {e}')
                all_passed = False

        if all_passed:
            self.test_results["tests_passed"].append("api_endpoints")
        else:
            self.test_results["tests_failed"].append("api_endpoints")

        return all_passed

    def save_test_results(self):
        """保存测试结果"""
        self.print_step(6, '保存测试结果')

        self.test_results["end_time"] = datetime.now().isoformat()
        self.test_results["total_tests"] = len(self.test_results["tests_passed"]) + len(self.test_results["tests_failed"])
        self.test_results["passed_count"] = len(self.test_results["tests_passed"])
        self.test_results["failed_count"] = len(self.test_results["tests_failed"])

        # 保存到文件
        output_file = Path(__file__).parent / 'test_results' / f'web_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        output_file.parent.mkdir(exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

        print(f'✅ 测试结果已保存: {output_file}')
        return output_file

    def print_final_summary(self):
        """打印最终总结"""
        self.print_section('测试总结')

        total = self.test_results["total_tests"]
        passed = self.test_results["passed_count"]
        failed = self.test_results["failed_count"]

        print(f'\n📊 测试统计:')
        print(f'   总测试数: {total}')
        print(f'   通过: {passed} ✅')
        print(f'   失败: {failed} ❌')
        print(f'   成功率: {(passed/total*100) if total > 0 else 0:.1f}%')

        if self.test_results["tests_passed"]:
            print(f'\n✅ 通过的测试:')
            for test in self.test_results["tests_passed"]:
                print(f'   - {test}')

        if self.test_results["tests_failed"]:
            print(f'\n❌ 失败的测试:')
            for test in self.test_results["tests_failed"]:
                print(f'   - {test}')

        if "novel_data" in self.test_results["generation_data"]:
            novel_data = self.test_results["generation_data"]["novel_data"]
            print(f'\n📚 生成的小说数据:')
            print(f'   标题: {novel_data.get("title")}')
            print(f'   章节数: {novel_data.get("chapter_count")}')
            print(f'   总字数: {novel_data.get("total_words")}')
            print(f'   平均评分: {novel_data.get("avg_score", 0):.2f}')

        print('\n' + '='*70)

        # 返回是否全部通过
        return failed == 0

    def run_full_test(self):
        """运行完整测试流程"""
        self.print_section('开始Web端小说生成完整流程测试')

        print(f'\n🎯 测试目标:')
        print(f'   1. 验证Web服务器正常运行')
        print(f'   2. 提交小说生成任务')
        print(f'   3. 监控生成进度')
        print(f'   4. 验证生成的数据完整性')
        print(f'   5. 测试其他API端点')

        # 执行测试步骤
        if not self.test_server_health():
            print('\n❌ 服务器健康检查失败，终止测试')
            return False

        if not self.submit_generation_task():
            print('\n❌ 提交任务失败，终止测试')
            return False

        if not self.monitor_generation_progress():
            print('\n❌ 生成过程失败或超时')
            # 继续执行其他测试

        self.verify_generated_data()
        self.test_api_endpoints()

        # 保存结果
        self.save_test_results()

        # 打印总结
        all_passed = self.print_final_summary()

        return all_passed


def main():
    """主函数"""
    print('\n' + '='*70)
    print('  Web端小说生成完整流程测试工具')
    print('='*70)

    # 检查是否需要启动服务器
    print('\n💡 提示: 请确保Web服务器已启动')
    print('   启动命令: python run_web.py')
    print('   或者在另一个终端运行: python web/web_server.py')

    response = input('\n是否继续测试? (y/n): ')
    if response.lower() != 'y':
        print('测试已取消')
        return

    # 创建测试器并运行
    tester = WebNovelGenerationTester()
    success = tester.run_full_test()

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
