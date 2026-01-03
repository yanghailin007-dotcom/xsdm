#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
诊断检查点映射问题
"""
import json
import os
import sys

def main():
    # 设置UTF-8编码
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer.detach(), 'strict')
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer.detach(), 'strict')
    
    print('=' * 60)
    print('诊断检查点查找问题')
    print('=' * 60)

    projects_dir = "d:/work6.05/小说项目"
    
    if not os.path.exists(projects_dir):
        print(f"ERROR: 项目目录不存在: {projects_dir}")
        return
    
    print(f"项目目录: {projects_dir}")
    
    # 扫描所有项目
    count_dirs = 0
    count_checkpoints = 0
    checkpoints_found = []
    
    for item in os.listdir(projects_dir):
        item_path = os.path.join(projects_dir, item)
        if os.path.isdir(item_path):
            count_dirs += 1
            checkpoint_file = os.path.join(item_path, '.generation', 'checkpoint.json')
            
            if os.path.exists(checkpoint_file):
                count_checkpoints += 1
                print(f"\n目录: {item}")
                
                try:
                    with open(checkpoint_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    novel_title = data.get('novel_title', 'Unknown')
                    creative_title = data.get('creative_title', novel_title)
                    creative_seed_id = data.get('creative_seed_id')
                    
                    print(f"  novel_title: {novel_title}")
                    print(f"  creative_title: {creative_title}")
                    print(f"  creative_seed_id: {creative_seed_id}")
                    
                    checkpoints_found.append({
                        'directory': item,
                        'novel_title': novel_title,
                        'creative_title': creative_title,
                        'creative_seed_id': creative_seed_id
                    })
                    
                except json.JSONDecodeError as e:
                    print(f"  JSON解析失败: {e}")
                except Exception as e:
                    print(f"  其他错误: {e}")
    
    print(f"\n统计:")
    print(f"  扫描目录: {count_dirs}")
    print(f"  有检查点: {count_checkpoints}")
    print(f"  成功解析: {len(checkpoints_found)}")
    
    # 查找匹配项
    search_title = "修仙：我是一柄魔剑，专治各种不服"
    print(f"\n查找匹配项:")
    print(f"  查找标题: {search_title}")
    
    found = False
    for cp in checkpoints_found:
        if cp['creative_title'] == search_title:
            print(f"\n找到 creative_title 匹配！")
            print(f"  目录: {cp['directory']}")
            print(f"  实际书名: {cp['el_title']}")
            found = True
            break
    
    if not found:
        print(f"\n未找到匹配项")
        print("\n所有检查点列表:")
        for i, cp in enumerate(checkpoints_found, 1):
            print(f"{i}. {cp.get('creative_title', 'N/A')} ({cp.get('novel_title', 'N/A')})")

if __name__ == "__main__":
    main()