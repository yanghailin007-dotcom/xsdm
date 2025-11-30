#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
修复prompts文件的中文编码问题
问题：UTF-8字节被当作GBK来解读导致乱码
解决方案：读取乱码的UTF-8字节 -> 按GBK解码 -> 重新保存为UTF-8
"""

import os

files_to_fix = [
    r'D:\work6.03\src\prompts\AnalysisPrompts.py',
    r'D:\work6.03\src\prompts\BasePrompts.py',
    r'D:\work6.03\src\prompts\PlanningPrompts.py',
    r'D:\work6.03\src\prompts\WorldviewPrompts.py',
    r'D:\work6.03\src\prompts\WritingPrompts.py',
    r'D:\work6.03\src\prompts\OptimizationPrompts.py'
]

def fix_file_encoding(file_path):
    """
    修复文件编码：UTF-8字节被当作GBK解读的问题
    """
    if not os.path.exists(file_path):
        print("FILE NOT FOUND: {}".format(file_path))
        return False

    try:
        # 读取文件的原始字节
        with open(file_path, 'rb') as f:
            raw_bytes = f.read()

        # 尝试多种方式修复
        fixed_content = None

        # 方法1：UTF-8字节被当作GBK解码（最常见的乱码情况）
        try:
            # 将UTF-8字节当作GBK解码，得到正确的中文
            decoded = raw_bytes.decode('gbk', errors='ignore')
            fixed_content = decoded
            print("SUCCESS (Method1): {}".format(file_path))
        except:
            pass

        # 如果方法1失败，尝试方法2
        if fixed_content is None:
            try:
                # 直接用UTF-8重新编码再解码
                temp = raw_bytes.decode('utf-8', errors='ignore')
                fixed_content = temp
                print("SUCCESS (Method2): {}".format(file_path))
            except:
                pass

        # 如果都失败，使用原始内容
        if fixed_content is None:
            print("WARNING - Using original content: {}".format(file_path))
            fixed_content = raw_bytes.decode('utf-8', errors='replace')

        # 保存修复后的内容为UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed_content)

        print("SAVED: {}".format(file_path))
        return True

    except Exception as e:
        print("ERROR: {} - {}".format(file_path, str(e)))
        return False


def main():
    print("=" * 60)
    print("Start fixing prompts files encoding")
    print("=" * 60)

    success_count = 0
    for file_path in files_to_fix:
        print("\nProcessing: {}".format(file_path))
        if fix_file_encoding(file_path):
            success_count += 1

    print("\n" + "=" * 60)
    print("Done! Fixed {}/{} files".format(success_count, len(files_to_fix)))
    print("=" * 60)


if __name__ == '__main__':
    main()
