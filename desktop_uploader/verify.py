#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整性验证工具 - 检查EXE是否被篡改

使用方法:
python verify.py --file "小说自动上传工具.exe"
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path


def calculate_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """计算文件哈希"""
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def verify_integrity(file_path: str, expected_hash: str = None) -> dict:
    """验证文件完整性"""
    result = {
        'file': file_path,
        'exists': False,
        'size': 0,
        'md5': '',
        'sha256': '',
        'match': False,
        'status': ''
    }
    
    if not os.path.exists(file_path):
        result['status'] = '文件不存在'
        return result
    
    result['exists'] = True
    result['size'] = os.path.getsize(file_path)
    result['md5'] = calculate_hash(file_path, 'md5')
    result['sha256'] = calculate_hash(file_path, 'sha256')
    
    if expected_hash:
        result['match'] = (result['sha256'] == expected_hash)
        result['status'] = '验证通过' if result['match'] else '哈希不匹配，文件可能被篡改'
    else:
        result['status'] = '已计算哈希（未提供期望值进行对比）'
    
    return result


def main():
    parser = argparse.ArgumentParser(description='验证EXE文件完整性')
    parser.add_argument('--file', '-f', required=True, help='要验证的文件')
    parser.add_argument('--hash', '-H', help='预期的SHA256哈希值')
    parser.add_argument('--save', '-s', action='store_true', help='保存哈希值到文件')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("文件完整性验证工具")
    print("=" * 60)
    print()
    
    # 执行验证
    result = verify_integrity(args.file, args.hash)
    
    # 显示结果
    print(f"文件: {result['file']}")
    print(f"存在: {'✅' if result['exists'] else '❌'}")
    print(f"大小: {result['size']:,} bytes ({result['size'] / (1024*1024):.2f} MB)")
    print()
    print(f"MD5:    {result['md5']}")
    print(f"SHA256: {result['sha256']}")
    print()
    print(f"状态: {result['status']}")
    
    # 保存哈希
    if args.save and result['exists']:
        hash_file = f"{args.file}.sha256"
        with open(hash_file, 'w') as f:
            f.write(f"{result['sha256']}  {os.path.basename(args.file)}\n")
        print(f"\n✅ 哈希值已保存到: {hash_file}")
    
    print()
    print("=" * 60)
    
    # 返回状态码
    sys.exit(0 if result['match'] or not args.hash else 1)


if __name__ == "__main__":
    main()
