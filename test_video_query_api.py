"""
测试 VeO 视频查询接口
验证新的 /v1/video/query 端点
"""
import requests
import json
import time
from pathlib import Path
from src.models.veo_models import VeOQueryResponse, VeOCreateVideoRequest
from config.aiwx_video_config import (
    get_request_headers,
    AIWX_VIDEO_CREATE_URL,
    AIWX_VIDEO_QUERY_URL,
    REQUEST_CONFIG
)


def test_video_query():
    """测试视频查询接口"""
    
    print("=" * 60)
    print("测试 VeO 视频查询接口")
    print("=" * 60)
    
    # 1. 创建一个视频生成任务
    print("\n[1] 创建视频生成任务...")
    
    create_request = VeOCreateVideoRequest(
        model="veo_3_1-fast",
        orientation="portrait",
        prompt="一只可爱的小猫在阳光下玩耍",
        size="small",
        duration=15,
        watermark=False,
        private=True
    )
    
    headers = get_request_headers()
    
    try:
        # 发送创建请求
        response = requests.post(
            AIWX_VIDEO_CREATE_URL,
            json=create_request.to_dict(),
            headers=headers,
            timeout=REQUEST_CONFIG['timeout']
        )
        
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('id')
            print(f"✅ 任务创建成功")
            print(f"📋 任务ID: {task_id}")
            print(f"📊 初始状态: {result.get('status')}")
        else:
            print(f"❌ 创建任务失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return
        
        # 2. 测试查询接口
        print(f"\n[2] 测试查询接口 /v1/video/query?id={task_id}")
        
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                # 构建查询URL
                query_url = f"{AIWX_VIDEO_QUERY_URL}?id={task_id}"
                print(f"\n📡 查询尝试 {attempt + 1}/{max_attempts}")
                print(f"🔗 URL: {query_url}")
                
                # 发送查询请求
                query_response = requests.get(
                    query_url,
                    headers=headers,
                    timeout=REQUEST_CONFIG['timeout']
                )
                
                print(f"📊 HTTP状态码: {query_response.status_code}")
                
                if query_response.status_code == 200:
                    # 解析响应
                    query_data = query_response.json()
                    print(f"📋 响应数据:")
                    print(json.dumps(query_data, ensure_ascii=False, indent=2))
                    
                    # 使用模型解析
                    veo_response = VeOQueryResponse.from_dict(query_data)
                    print(f"\n🎯 解析结果:")
                    print(f"  - 任务ID: {veo_response.id}")
                    print(f"  - 状态: {veo_response.status}")
                    print(f"  - 增强提示词: {veo_response.enhanced_prompt}")
                    print(f"  - 更新时间: {veo_response.status_update_time}")
                    
                    if veo_response.video_url:
                        print(f"  - 视频URL: {veo_response.video_url}")
                    if veo_response.width and veo_response.height:
                        print(f"  - 分辨率: {veo_response.width}x{veo_response.height}")
                    if veo_response.thumbnail_url:
                        print(f"  - 缩略图: {veo_response.thumbnail_url}")
                    
                    # 检查状态
                    if veo_response.is_completed():
                        print(f"\n✅ 任务已完成!")
                        break
                    elif veo_response.is_failed():
                        print(f"\n❌ 任务失败!")
                        break
                    elif veo_response.is_processing():
                        print(f"\n⏳ 任务处理中...")
                        if attempt < max_attempts - 1:
                            print(f"⌚ 等待5秒后继续查询...")
                            time.sleep(5)
                    
                else:
                    print(f"❌ 查询失败: HTTP {query_response.status_code}")
                    print(f"响应: {query_response.text}")
            
            except Exception as e:
                print(f"❌ 查询异常: {e}")
            
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


def test_query_with_existing_task():
    """使用现有任务ID测试查询接口"""
    
    print("=" * 60)
    print("测试查询接口 - 使用现有任务ID")
    print("=" * 60)
    
    # 可以在这里输入一个已知的任务ID进行测试
    task_id = input("\n请输入任务ID (按Enter跳过): ").strip()
    
    if not task_id:
        print("⏭️ 跳过测试")
        return
    
    headers = get_request_headers()
    query_url = f"{AIWX_VIDEO_QUERY_URL}?id={task_id}"
    
    try:
        print(f"\n📡 查询任务: {task_id}")
        print(f"🔗 URL: {query_url}")
        
        response = requests.get(
            query_url,
            headers=headers,
            timeout=REQUEST_CONFIG['timeout']
        )
        
        print(f"📊 HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            query_data = response.json()
            print(f"\n📋 响应数据:")
            print(json.dumps(query_data, ensure_ascii=False, indent=2))
            
            veo_response = VeOQueryResponse.from_dict(query_data)
            print(f"\n🎯 解析结果:")
            print(f"  - 任务ID: {veo_response.id}")
            print(f"  - 状态: {veo_response.status}")
            print(f"  - 增强提示词: {veo_response.enhanced_prompt}")
            
            if veo_response.video_url:
                print(f"  - 视频URL: {veo_response.video_url}")
            if veo_response.width and veo_response.height:
                print(f"  - 分辨率: {veo_response.width}x{veo_response.height}")
            if veo_response.thumbnail_url:
                print(f"  - 缩略图: {veo_response.thumbnail_url}")
        
        else:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    print("\n选择测试模式:")
    print("1. 创建新任务并查询")
    print("2. 查询现有任务")
    
    choice = input("\n请输入选择 (1/2): ").strip()
    
    if choice == "1":
        test_video_query()
    elif choice == "2":
        test_query_with_existing_task()
    else:
        print("❌ 无效选择")