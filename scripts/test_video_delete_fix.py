"""
测试VeO视频删除功能修复
验证任务ID一致性问题是否解决
"""
import requests
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "http://localhost:5000"

def test_list_tasks():
    """列出所有任务"""
    try:
        response = requests.get(f"{BASE_URL}/api/veo/tasks?limit=50&order=desc")
        
        if response.status_code == 200:
            data = response.json()
            tasks = data.get("data", [])
            logger.info(f"✅ 获取到 {len(tasks)} 个任务")
            
            for task in tasks:
                logger.info(f"  - ID: {task.get('id')}, 状态: {task.get('status')}")
            
            return tasks
        else:
            logger.error(f"❌ 获取任务列表失败: HTTP {response.status_code}")
            return []
    
    except Exception as e:
        logger.error(f"❌ 获取任务列表异常: {e}")
        return []

def test_delete_task(task_id):
    """删除指定任务"""
    try:
        logger.info(f"🗑️ 尝试删除任务: {task_id}")
        
        response = requests.delete(f"{BASE_URL}/api/veo/tasks/{task_id}")
        
        if response.status_code == 200:
            logger.info(f"✅ 删除成功: {task_id}")
            return True
        else:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "未知错误")
            logger.error(f"❌ 删除失败: {error_msg}")
            return False
    
    except Exception as e:
        logger.error(f"❌ 删除任务异常: {e}")
        return False

def test_task_persistence():
    """测试任务持久化"""
    logger.info("=" * 60)
    logger.info("测试1: 验证任务列表加载")
    logger.info("=" * 60)
    
    tasks = test_list_tasks()
    
    if not tasks:
        logger.warn("⚠️  没有找到任何任务")
        return False
    
    logger.info(f"✅ 成功加载 {len(tasks)} 个任务")
    
    # 检查ID格式
    valid_count = 0
    for task in tasks:
        task_id = task.get("id", "")
        if task_id.startswith("veo_"):
            valid_count += 1
        else:
            logger.warn(f"⚠️  发现无效ID格式: {task_id}")
    
    logger.info(f"✅ {valid_count}/{len(tasks)} 个任务ID格式正确")
    
    return True

def test_delete_flow():
    """测试完整删除流程"""
    logger.info("=" * 60)
    logger.info("测试2: 验证删除功能")
    logger.info("=" * 60)
    
    tasks = test_list_tasks()
    
    if not tasks:
        logger.warn("⚠️  没有可删除的任务")
        return True
    
    # 选择第一个任务进行删除测试
    test_task = tasks[0]
    task_id = test_task.get("id")
    
    logger.info(f"📋 选择任务进行删除测试: {task_id}")
    logger.info(f"   状态: {test_task.get('status')}")
    logger.info(f"   创建时间: {test_task.get('created')}")
    
    # 执行删除
    success = test_delete_task(task_id)
    
    if success:
        logger.info("✅ 删除测试通过")
        
        # 验证删除后任务确实不存在
        time.sleep(1)
        tasks_after = test_list_tasks()
        
        remaining_ids = [t.get("id") for t in tasks_after]
        if task_id not in remaining_ids:
            logger.info(f"✅ 确认任务已从列表中移除: {task_id}")
            return True
        else:
            logger.error(f"❌ 任务仍在列表中: {task_id}")
            return False
    else:
        logger.error("❌ 删除测试失败")
        return False

def main():
    """主测试流程"""
    logger.info("=" * 60)
    logger.info("VeO视频删除功能修复验证")
    logger.info("=" * 60)
    
    # 测试1: 验证任务加载
    test1_passed = test_task_persistence()
    
    # 测试2: 验证删除功能
    test2_passed = test_delete_flow()
    
    # 总结
    logger.info("=" * 60)
    logger.info("测试结果总结")
    logger.info("=" * 60)
    logger.info(f"测试1 - 任务加载: {'✅ 通过' if test1_passed else '❌ 失败'}")
    logger.info(f"测试2 - 删除功能: {'✅ 通过' if test2_passed else '❌ 失败'}")
    
    if test1_passed and test2_passed:
        logger.info("🎉 所有测试通过！删除功能修复成功")
        return 0
    else:
        logger.error("⚠️  部分测试失败，需要进一步检查")
        return 1

if __name__ == "__main__":
    sys.exit(main())