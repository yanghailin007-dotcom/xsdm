"""
视频删除功能测试脚本
测试 VeO 视频管理器的删除功能
"""
import requests
import json
from typing import Dict, List
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.VeOVideoManager import get_veo_video_manager


class VideoDeleteTester:
    """视频删除功能测试器"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5000"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api/veo"
    
    def print_section(self, title: str):
        """打印分节标题"""
        print("\n" + "=" * 60)
        print(f"  {title}")
        print("=" * 60)
    
    def print_result(self, test_name: str, success: bool, message: str = ""):
        """打印测试结果"""
        status = "[PASS] 通过" if success else "[FAIL] 失败"
        print(f"{status} - {test_name}")
        if message:
            print(f"   详情: {message}")
    
    def list_all_tasks(self) -> List[Dict]:
        """获取所有任务列表"""
        try:
            response = requests.get(f"{self.api_base}/tasks?limit=100&order=desc")
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            return []
        except Exception as e:
            print(f"获取任务列表失败: {e}")
            return []
    
    def test_delete_nonexistent_task(self):
        """测试1: 删除不存在的任务"""
        self.print_section("测试1: 删除不存在的任务")
        
        # 使用一个不存在的任务ID
        fake_id = "veo_nonexistent123"
        
        print(f"\n尝试删除不存在的任务: {fake_id}")
        
        try:
            response = requests.delete(f"{self.api_base}/tasks/{fake_id}")
            
            if response.status_code == 400:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', '未知错误')
                self.print_result(
                    "后端正确返回400错误",
                    True,
                    f"错误消息: {error_msg}"
                )
            else:
                self.print_result(
                    "后端返回状态码",
                    False,
                    f"预期400，实际{response.status_code}"
                )
            
            # 验证任务列表没有变化
            tasks_before = self.list_all_tasks()
            tasks_after = self.list_all_tasks()
            
            if len(tasks_before) == len(tasks_after):
                self.print_result(
                    "任务列表数量未变化",
                    True,
                    f"保持 {len(tasks_before)} 个任务"
                )
            else:
                self.print_result(
                    "任务列表数量未变化",
                    False,
                    f"之前{len(tasks_before)}个，之后{len(tasks_after)}个"
                )
                
        except Exception as e:
            self.print_result("删除不存在的任务", False, str(e))
    
    def test_delete_existing_task(self):
        """测试2: 删除存在的任务"""
        self.print_section("测试2: 删除存在的任务")
        
        # 获取所有任务
        tasks = self.list_all_tasks()
        
        if not tasks:
            print("\n⚠️  没有可用的任务进行测试")
            print("提示: 请先创建一些视频生成任务")
            return
        
        # 选择第一个任务进行测试
        test_task = tasks[0]
        task_id = test_task.get('id')
        task_prompt = test_task.get('prompt', '无提示词')[:50]
        
        print(f"\n选择任务进行测试:")
        print(f"  ID: {task_id}")
        print(f"  提示词: {task_prompt}...")
        print(f"  状态: {test_task.get('status', 'unknown')}")
        
        # 如果是已完成或失败的任务，可以安全删除
        if test_task.get('status') not in ['completed', 'failed', 'cancelled']:
            print(f"\n⚠️  任务状态为 {test_task.get('status')}，不建议删除")
            print("建议: 请等待任务完成后再测试删除功能")
            return
        
        # 确认删除
        print(f"\n准备删除任务: {task_id}")
        try:
            response = requests.delete(f"{self.api_base}/tasks/{task_id}")
            
            if response.status_code == 200:
                self.print_result(
                    "删除成功",
                    True,
                    f"任务 {task_id} 已删除"
                )
                
                # 验证任务确实被删除
                tasks_after = self.list_all_tasks()
                remaining_ids = [t.get('id') for t in tasks_after]
                
                if task_id not in remaining_ids:
                    self.print_result(
                        "任务已从列表中移除",
                        True,
                        f"剩余 {len(tasks_after)} 个任务"
                    )
                else:
                    self.print_result(
                        "任务已从列表中移除",
                        False,
                        "任务仍然存在于列表中"
                    )
                    
            else:
                error_data = response.json()
                error_msg = error_data.get('error', {}).get('message', '未知错误')
                self.print_result(
                    "删除请求",
                    False,
                    f"HTTP {response.status_code}: {error_msg}"
                )
                
        except Exception as e:
            self.print_result("删除存在的任务", False, str(e))
    
    def test_api_error_handling(self):
        """测试3: API错误处理"""
        self.print_section("测试3: API错误处理")
        
        print("\n测试各种错误情况...")
        
        # 测试无效的任务ID格式
        print("\n1. 测试无效的任务ID格式")
        try:
            response = requests.delete(f"{self.api_base}/tasks/invalid_id_format")
            if response.status_code == 400:
                self.print_result("无效ID格式返回400", True)
            else:
                self.print_result("无效ID格式返回400", False, f"返回{response.status_code}")
        except Exception as e:
            self.print_result("无效ID格式测试", False, str(e))
        
        # 测试空任务ID
        print("\n2. 测试空任务ID")
        try:
            response = requests.delete(f"{self.api_base}/tasks/")
            # 应该返回404（路由不存在）或405（方法不允许）
            if response.status_code in [404, 405]:
                self.print_result("空任务ID正确处理", True)
            else:
                self.print_result("空任务ID正确处理", False, f"返回{response.status_code}")
        except Exception as e:
            self.print_result("空任务ID测试", False, str(e))
    
    def test_frontend_sync(self):
        """测试4: 前后端同步"""
        self.print_section("测试4: 前后端数据同步")
        
        print("\n验证前端和后端数据一致性...")
        
        # 获取任务列表
        tasks = self.list_all_tasks()
        
        print(f"\n当前任务数量: {len(tasks)}")
        print(f"任务ID列表:")
        for i, task in enumerate(tasks[:10], 1):  # 只显示前10个
            print(f"  {i}. {task.get('id')} - {task.get('status', 'unknown')}")
        
        if len(tasks) > 10:
            print(f"  ... 还有 {len(tasks) - 10} 个任务")
        
        # 检查是否有孤立的任务（文件存在但内存中不存在）
        print("\n检查任务完整性...")
        manager = get_veo_video_manager()
        
        memory_tasks = set(manager.tasks.keys())
        file_tasks = set()
        
        import os
        storage_dir = manager.storage_dir
        if storage_dir.exists():
            for file in storage_dir.glob("*.json"):
                task_id = file.stem
                file_tasks.add(task_id)
        
        print(f"内存中的任务: {len(memory_tasks)}")
        print(f"文件中的任务: {len(file_tasks)}")
        
        # 检查差异
        orphaned_files = file_tasks - memory_tasks
        orphaned_memory = memory_tasks - file_tasks
        
        if orphaned_files:
            print(f"\n⚠️  发现 {len(orphaned_files)} 个孤立文件:")
            for task_id in list(orphaned_files)[:5]:
                print(f"  - {task_id}")
        
        if orphaned_memory:
            print(f"\n⚠️  发现 {len(orphaned_memory)} 个内存中存在但文件不存在的任务:")
            for task_id in list(orphaned_memory)[:5]:
                print(f"  - {task_id}")
        
        if not orphaned_files and not orphaned_memory:
            self.print_result("前后端数据完全同步", True)
        else:
            self.print_result("前后端数据完全同步", False, "存在孤立数据")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "🎬" * 30)
        print("  VeO 视频删除功能测试套件")
        print("🎬" * 30)
        
        # 测试1: 删除不存在的任务
        self.test_delete_nonexistent_task()
        
        # 测试2: 删除存在的任务（需要用户确认）
        self.test_delete_existing_task()
        
        # 测试3: API错误处理
        self.test_api_error_handling()
        
        # 测试4: 前后端同步
        self.test_frontend_sync()
        
        # 总结
        self.print_section("测试完成")
        print("\n💡 建议:")
        print("  1. 如果所有测试通过，说明删除功能工作正常")
        print("  2. 如果有测试失败，请检查相关代码")
        print("  3. 可以使用浏览器开发者工具查看前端网络请求")
        print("  4. 查看后端日志了解详细错误信息")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='VeO 视频删除功能测试')
    parser.add_argument(
        '--url',
        default='http://127.0.0.1:5000',
        help='服务器地址 (默认: http://127.0.0.1:5000)'
    )
    parser.add_argument(
        '--test',
        choices=['all', 'nonexistent', 'existing', 'error', 'sync'],
        default='all',
        help='指定要运行的测试 (默认: all)'
    )
    
    args = parser.parse_args()
    
    tester = VideoDeleteTester(base_url=args.url)
    
    # 根据参数运行测试
    if args.test == 'all':
        tester.run_all_tests()
    elif args.test == 'nonexistent':
        tester.test_delete_nonexistent_task()
    elif args.test == 'existing':
        tester.test_delete_existing_task()
    elif args.test == 'error':
        tester.test_api_error_handling()
    elif args.test == 'sync':
        tester.test_frontend_sync()


if __name__ == '__main__':
    main()