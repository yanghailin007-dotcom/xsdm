#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 GitHub Releases 下载构建产物

使用方式:
    python scripts/download_release.py [tag]
    
示例:
    python scripts/download_release.py          # 下载最新版本
    python scripts/download_release.py v1.0.0   # 下载指定版本

下载后文件会保存到: desktop_uploader/release/
然后你需要手动提交到 GitHub
"""

import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import urlparse

# GitHub 仓库配置
GITHUB_OWNER = "yanghailin"  # 修改为你的 GitHub 用户名
GITHUB_REPO = "xsdm"
RELEASE_DIR = Path("desktop_uploader/release")


def get_latest_release():
    """获取最新 Release 信息"""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取 Release 信息失败: {e}")
        return None


def get_release_by_tag(tag):
    """获取指定 Tag 的 Release 信息"""
    url = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tags/{tag}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ 获取 Release 信息失败: {e}")
        return None


def download_file(url: str, dest_path: Path, filename: str):
    """下载文件并显示进度"""
    try:
        print(f"⬇️  开始下载: {filename}")
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        # 下载并显示进度
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        mb = downloaded / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        print(f"\r   进度: {percent:.1f}% ({mb:.1f}MB / {total_mb:.1f}MB)", end='', flush=True)
        
        print(f"\n✅ 下载完成: {filename} ({downloaded/1024/1024:.1f}MB)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"\n❌ 下载失败: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False


def download_release_assets(release_data: dict):
    """下载 Release 中的所有资源文件"""
    assets = release_data.get('assets', [])
    
    if not assets:
        print("⚠️  该 Release 没有可下载的文件")
        return False
    
    # 创建 release 目录
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📦 发现 {len(assets)} 个文件:")
    for asset in assets:
        print(f"   - {asset['name']} ({asset['size']/1024/1024:.1f}MB)")
    
    print(f"\n💾 下载位置: {RELEASE_DIR.absolute()}\n")
    
    # 下载每个文件
    success_count = 0
    for asset in assets:
        filename = asset['name']
        download_url = asset['browser_download_url']
        dest_path = RELEASE_DIR / filename
        
        # 如果文件已存在，询问是否覆盖
        if dest_path.exists():
            print(f"⚠️  文件已存在: {filename}")
            response = input(f"   是否覆盖? (y/n): ").strip().lower()
            if response != 'y':
                print(f"   跳过: {filename}")
                continue
        
        if download_file(download_url, dest_path, filename):
            success_count += 1
    
    return success_count == len(assets)


def main():
    """主函数"""
    print("=" * 60)
    print("🚀 GitHub Releases 下载工具")
    print("=" * 60)
    
    # 获取版本标签
    if len(sys.argv) > 1:
        tag = sys.argv[1]
        print(f"\n📋 指定版本: {tag}")
        release_data = get_release_by_tag(tag)
    else:
        print(f"\n📋 获取最新版本...")
        release_data = get_latest_release()
    
    if not release_data:
        print("\n❌ 无法获取 Release 信息")
        print("\n可能的解决方案:")
        print("1. 检查网络连接")
        print("2. 确认仓库名称正确 (当前: {}/{})".format(GITHUB_OWNER, GITHUB_REPO))
        print("3. 确认 Release 已发布")
        return False
    
    # 显示 Release 信息
    tag_name = release_data.get('tag_name', 'unknown')
    name = release_data.get('name', 'No title')
    published_at = release_data.get('published_at', '')
    
    print(f"\n✅ 找到 Release:")
    print(f"   标签: {tag_name}")
    print(f"   标题: {name}")
    print(f"   发布时间: {published_at}")
    
    # 下载文件
    if download_release_assets(release_data):
        print("\n" + "=" * 60)
        print("✅ 所有文件下载成功!")
        print("=" * 60)
        print(f"\n📂 文件位置: {RELEASE_DIR.absolute()}")
        print("\n下一步操作:")
        print("1. 检查文件是否正确")
        print("2. 提交到 GitHub:")
        print(f"   git add desktop_uploader/release/")
        print(f"   git commit -m \"chore: update build artifacts {tag_name}\"")
        print(f"   git push")
        return True
    else:
        print("\n" + "=" * 60)
        print("⚠️  部分文件下载失败")
        print("=" * 60)
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
