"""
Web 系统演示脚本
Demonstrates all features of the web system
"""

import json
import time
import requests
from datetime import datetime

# API 基础 URL
BASE_URL = "http://localhost:5000/api"

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def print_status(message, icon="ℹ"):
    """打印状态信息"""
    print(f"  {icon} {message}")

def demo_health_check():
    """演示 1: 健康检查"""
    print_header("演示 1️⃣ : 健康检查")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_status("✅ 服务正常运行")
            print_status(f"状态: {data['status']}")
            print_status(f"时间: {data['timestamp']}")
        else:
            print_status(f"❌ 服务返回错误: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 无法连接服务: {e}", "✗")
        return False
    
    return True

def demo_start_generation():
    """演示 2: 启动生成"""
    print_header("演示 2️⃣ : 启动小说生成")
    
    novel_config = {
        "title": "凡人修仙同人·观战者",
        "synopsis": "穿越者李尘身具观战悟道体质，通过观摩强者对战获得修行启悟。",
        "core_setting": "时间线从韩立与温天仁结丹巅峰大战开始。",
        "core_selling_points": [
            "观战悟道体质",
            "因果干涉命运",
            "双星微妙博弈"
        ],
        "total_chapters": 50
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/start-generation",
            json=novel_config,
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                novel_id = data['novel_id']
                print_status(f"✅ 小说生成已启动")
                print_status(f"小说 ID: {novel_id}")
                return True
            else:
                print_status(f"❌ 生成失败: {data.get('error', '未知错误')}", "✗")
        else:
            print_status(f"❌ 服务错误: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_generate_chapters():
    """演示 3: 生成章节"""
    print_header("演示 3️⃣ : 生成 5 章节点")
    
    try:
        print_status("📍 正在生成 5 章内容...")
        
        response = requests.post(
            f"{BASE_URL}/generate-chapters",
            json={"chapters_count": 5},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print_status(f"✅ 成功生成 {data['chapters_generated']} 章")
                
                novel = data['novel_summary']
                print_status(f"小说标题: {novel['title']}")
                print_status(f"生成进度: {novel['chapters_count']}/{novel['total_chapters']}")
                
                return True
            else:
                print_status(f"❌ 生成失败: {data.get('error', '未知错误')}", "✗")
        else:
            print_status(f"❌ 服务错误: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_get_summary():
    """演示 4: 获取摘要"""
    print_header("演示 4️⃣ : 获取小说摘要")
    
    try:
        response = requests.get(f"{BASE_URL}/novel/summary", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data:
                print_status(f"✅ 成功获取摘要")
                print_status(f"标题: {data.get('title', '未知')}")
                print_status(f"进度: {data.get('chapters_count', 0)}/{data.get('total_chapters', 0)}")
                print_status(f"状态: {data.get('status', '未知')}")
                return True
            else:
                print_status(f"⚠️  未找到小说数据", "⚠")
        else:
            print_status(f"❌ 获取失败: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_list_chapters():
    """演示 5: 列出章节"""
    print_header("演示 5️⃣ : 章节列表")
    
    try:
        response = requests.get(f"{BASE_URL}/chapters", timeout=5)
        if response.status_code == 200:
            chapters = response.json()
            if chapters:
                print_status(f"✅ 获取 {len(chapters)} 章节")
                
                # 显示前 5 章
                for ch in chapters[:5]:
                    print_status(
                        f"第{ch['chapter_number']}章: "
                        f"{ch['title']} ({ch['word_count']}字, "
                        f"评分: {ch['score'] or '-'})"
                    )
                
                if len(chapters) > 5:
                    print_status(f"... 还有 {len(chapters)-5} 章")
                
                return True
            else:
                print_status(f"⚠️  暂无章节数据", "⚠")
        else:
            print_status(f"❌ 获取失败: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_get_chapter():
    """演示 6: 获取章节详情"""
    print_header("演示 6️⃣ : 第 1 章详情")
    
    try:
        response = requests.get(f"{BASE_URL}/chapter/1", timeout=5)
        if response.status_code == 200:
            chapter = response.json()
            if chapter:
                print_status(f"✅ 获取第 1 章详情")
                print_status(f"标题: {chapter.get('title', '未知')}")
                print_status(f"字数: {len(chapter.get('content', ''))} 字")
                
                assessment = chapter.get('assessment', {})
                score = assessment.get('score') or assessment.get('整体评分', '-')
                print_status(f"评分: {score}")
                
                pros = assessment.get('pros') or assessment.get('优点', [])
                if pros:
                    print_status(f"优点: {', '.join(pros[:2])} {'...' if len(pros) > 2 else ''}")
                
                return True
            else:
                print_status(f"⚠️  暂无第 1 章数据", "⚠")
        else:
            print_status(f"❌ 获取失败: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_get_progress():
    """演示 7: 获取进度"""
    print_header("演示 7️⃣ : 生成进度")
    
    try:
        response = requests.get(f"{BASE_URL}/progress", timeout=5)
        if response.status_code == 200:
            progress = response.json()
            if progress:
                print_status(f"✅ 获取进度信息")
                
                # 显示前 3 章的进度
                for ch_num in sorted(progress.keys())[:3]:
                    steps = progress[ch_num]
                    print_status(f"第 {ch_num} 章: ", "")
                    for step, info in steps.items():
                        status = "✓" if info['status'] == 'completed' else "⏳"
                        print(f"          {status} {step}")
                
                return True
            else:
                print_status(f"⚠️  暂无进度数据", "⚠")
        else:
            print_status(f"❌ 获取失败: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def demo_export_json():
    """演示 8: 导出 JSON"""
    print_header("演示 8️⃣ : 导出 JSON 数据")
    
    try:
        response = requests.get(f"{BASE_URL}/export-json", timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            print_status(f"✅ 导出成功")
            print_status(f"包含数据: ")
            print(f"  • novel: {len(json.dumps(data.get('novel', {})))} 字节")
            print(f"  • chapters: {len(data.get('chapters', []))} 章")
            print(f"  • chapters_detail: {len(data.get('chapters_detail', {}))} 项")
            
            # 显示大小
            total_size = len(json.dumps(data))
            print_status(f"总大小: {total_size:,} 字节 ({total_size/1024:.1f} KB)")
            
            return True
        else:
            print_status(f"❌ 导出失败: {response.status_code}", "✗")
    except Exception as e:
        print_status(f"❌ 请求失败: {e}", "✗")
    
    return False

def main():
    """主函数"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  🎨 小说生成系统 Web API 演示".center(58) + "║")
    print("║" + "  Novel Generation System - Web API Demo".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    print(f"\n⏰ 演示开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 API 基础地址: {BASE_URL}")
    print(f"🌐 Web 首页: http://localhost:5000")
    
    # 执行演示
    demos = [
        ("健康检查", demo_health_check),
        ("启动生成", demo_start_generation),
        ("生成章节", demo_generate_chapters),
        ("获取摘要", demo_get_summary),
        ("列出章节", demo_list_chapters),
        ("获取详情", demo_get_chapter),
        ("获取进度", demo_get_progress),
        ("导出 JSON", demo_export_json),
    ]
    
    results = []
    for name, demo_func in demos:
        try:
            success = demo_func()
            results.append((name, success))
            time.sleep(0.5)  # 稍微延迟
        except Exception as e:
            print_status(f"❌ 演示异常: {e}", "✗")
            results.append((name, False))
    
    # 总结
    print_header("📊 演示总结")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print_status(f"{status} | {name}")
    
    print_status(f"\n总体: {passed}/{total} 演示通过 ({passed*100//total}%)")
    
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  ✅ 演示完成！".center(58) + "║")
    print("║" + " "*58 + "║")
    print("║" + "  🌐 访问 Web 界面: http://localhost:5000".center(58) + "║")
    print("║" + "  📖 查看文档: WEB_COMPLETE_GUIDE.md".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝\n")

if __name__ == '__main__':
    main()
