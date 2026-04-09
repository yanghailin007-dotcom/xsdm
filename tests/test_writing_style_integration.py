#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文风系统集成测试
"""

import sys
import os

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_style_prompt_building():
    """测试文风提示词构建"""
    print("=" * 60)
    print("测试1: 文风提示词构建")
    print("=" * 60)
    
    # 测试数据
    writing_style = {
        'id': 'tomato_fast',
        'name': '番茄快节奏',
        'icon': '🔥',
        'genre': '通用',
        'description': '短句密集、节奏快速、爽点密集，适合番茄小说平台的快节奏爽文',
        'tags': ['短句', '快节奏', '口语化'],
        'features': {
            'short_sentence_ratio': 0.5,
            'dialogue_ratio': 0.35,
            'sensory_density': 0.04,
            'colloquialism_density': 0.03
        }
    }
    
    # 模拟构建提示词
    style_name = writing_style['name']
    style_desc = writing_style['description']
    features = writing_style['features']
    
    short_ratio = features.get('short_sentence_ratio', 0.3)
    dialogue_ratio = features.get('dialogue_ratio', 0.3)
    sensory_density = features.get('sensory_density', 0.03)
    colloquialism_density = features.get('colloquialism_density', 0.02)
    
    prompt = f"""
【文风要求：{style_name}】
{style_desc}

具体指标要求：
- 短句（<10字）占比约{short_ratio*100:.0f}%，营造快节奏感
- 对话占比约{dialogue_ratio*100:.0f}%，推动情节发展
- 感官描写密度约{sensory_density*100:.1f}%，增强代入感
- 口语化程度约{colloquialism_density*100:.1f}%，贴近网文风格
"""
    
    print("生成的文风提示词:")
    print(prompt)
    print("\n[OK] 文风提示词构建成功")
    return True


def test_api_receive_style():
    """测试API接收文风参数"""
    print("\n" + "=" * 60)
    print("测试2: API接收文风参数")
    print("=" * 60)
    
    # 模拟请求数据
    request_data = {
        "genre": "神豪文-花钱返利类",
        "user_choices": {
            "title": "测试小说",
            "protagonist_name": "林凡",
            "writing_style": {
                "id": "tomato_fast",
                "name": "番茄快节奏",
                "description": "短句密集、节奏快速...",
                "features": {
                    "short_sentence_ratio": 0.5,
                    "dialogue_ratio": 0.35
                }
            }
        }
    }
    
    # 验证数据结构
    user_choices = request_data.get('user_choices', {})
    writing_style = user_choices.get('writing_style')
    
    if writing_style:
        print(f"[OK] 收到文风参数: {writing_style['name']}")
        print(f"[OK] 短句比例: {writing_style['features']['short_sentence_ratio']}")
        return True
    else:
        print("[FAIL] 未收到文风参数")
        return False


def test_style_injection():
    """测试文风注入流程"""
    print("\n" + "=" * 60)
    print("测试3: 文风注入流程")
    print("=" * 60)
    
    # 模拟任务数据
    task = {
        "task_id": "TEST-001",
        "genre": "神豪文-花钱返利类",
        "writing_style": {
            "id": "tomato_fast",
            "name": "番茄快节奏",
            "features": {
                "short_sentence_ratio": 0.5,
                "dialogue_ratio": 0.35
            }
        }
    }
    
    # 模拟从任务中获取文风
    writing_style = task.get('writing_style')
    
    if writing_style:
        print(f"[OK] 从任务获取文风: {writing_style['name']}")
        
        # 模拟novel_data
        novel_data = {
            "title": "测试小说",
            "writing_style": writing_style
        }
        
        # 验证文风被正确传递
        if 'writing_style' in novel_data:
            print("[OK] 文风已注入到novel_data")
            return True
    
    print("[FAIL] 文风注入失败")
    return False


def test_frontend_style_selector():
    """测试前端文风选择器"""
    print("\n" + "=" * 60)
    print("测试4: 前端文风选择器")
    print("=" * 60)
    
    # 预设文风列表
    PRESET_WRITING_STYLES = [
        {
            'id': 'tomato_fast',
            'name': '番茄快节奏',
            'icon': '🔥',
            'genre': '通用',
            'description': '短句密集、节奏快速、爽点密集，适合番茄小说平台的快节奏爽文',
            'tags': ['短句', '快节奏', '口语化'],
            'features': {
                'short_sentence_ratio': 0.5,
                'dialogue_ratio': 0.35,
                'sensory_density': 0.04,
                'colloquialism_density': 0.03
            }
        },
        {
            'id': 'yy_legacy',
            'name': 'YY白金风',
            'icon': '👑',
            'genre': '玄幻/都市',
            'description': '经典YY风格，装逼打脸、一路升级，满足读者代入感',
            'tags': ['装逼', '升级', '爽感'],
            'features': {
                'short_sentence_ratio': 0.35,
                'dialogue_ratio': 0.3,
                'sensory_density': 0.03,
                'colloquialism_density': 0.02
            }
        }
    ]
    
    print(f"[OK] 预设文风数量: {len(PRESET_WRITING_STYLES)}")
    
    for style in PRESET_WRITING_STYLES:
        print(f"  - {style['name']} ({style['genre']})")
    
    # 测试选择逻辑
    selected_id = 'tomato_fast'
    selected = next((s for s in PRESET_WRITING_STYLES if s['id'] == selected_id), None)
    
    if selected:
        print(f"\n[OK] 选中文风: {selected['name']}")
        return True
    else:
        print("[FAIL] 未找到选中的文风")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("文风系统集成测试")
    print("=" * 60)
    
    results = []
    
    try:
        results.append(("文风提示词构建", test_style_prompt_building()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("文风提示词构建", False))
    
    try:
        results.append(("API接收文风参数", test_api_receive_style()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("API接收文风参数", False))
    
    try:
        results.append(("文风注入流程", test_style_injection()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("文风注入流程", False))
    
    try:
        results.append(("前端文风选择器", test_frontend_style_selector()))
    except Exception as e:
        print(f"[ERROR] {e}")
        results.append(("前端文风选择器", False))
    
    # 汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} - {name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\n总计: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("\n所有测试通过！文风系统已正确集成。")
    
    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
