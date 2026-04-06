#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双平台自动上传脚本
检测当前平台并上传对应的构建产物到服务器

使用方式:
    python scripts/upload_release.py

环境变量:
    UPLOAD_SERVER_URL: 上传服务器地址
    UPLOAD_API_KEY:    上传 API 密钥
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
from datetime import datetime

# 默认上传配置
DEFAULT_SERVER = "https://your-server.com/api/upload"
DEFAULT_VERSION = datetime.now().strftime("%Y%m%d")

def get_platform_info():
    """获取平台信息"""
    system = platform.system()
    machine = platform.machine()
    
    if system == 'Windows':
        return {
            'name': 'windows',
            'file': 'dist/NovelPublisher.exe',
            'remote_name': f'NovelPublisher-windows-{DEFAULT_VERSION}.exe',
            'mime_type': 'application/x-msdownload'
        }
    elif system == 'Darwin':  # macOS
        # 检测是 Intel 还是 Apple Silicon
        arch = 'arm64' if machine == 'arm64' else 'x64'
        return {
            'name': f'macos-{arch}',
            'file': 'dist/NovelPublisher-macos.zip',
            'remote_name': f'NovelPublisher-macos-{arch}-{DEFAULT_VERSION}.zip',
            'mime_type': 'application/zip'
        }
    else:
        raise RuntimeError(f"不支持的平台: {system}")

def check_file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"✅ 文件就绪: {file_path} ({size_mb:.1f} MB)")
    return True

def upload_file(file_path: str, remote_name: str, server_url: str = None, api_key: str = None) -> bool:
    """
    上传文件到服务器
    
    支持多种上传方式:
    1. SCP (推荐用于私有服务器)
    2. Rsync
    3. HTTP POST (用于支持的上传服务)
    4. S3/阿里云OSS等对象存储
    """
    
    server_url = server_url or os.getenv('UPLOAD_SERVER_URL', DEFAULT_SERVER)
    api_key = api_key or os.getenv('UPLOAD_API_KEY')
    
    path = Path(file_path)
    
    print(f"\n📤 上传文件...")
    print(f"  本地文件: {path.absolute()}")
    print(f"  远程名称: {remote_name}")
    print(f"  目标服务器: {server_url}")
    
    # 方式1: 使用 scp 上传到服务器 (最常用)
    scp_host = os.getenv('SCP_HOST')
    scp_user = os.getenv('SCP_USER')
    scp_path = os.getenv('SCP_PATH', '/var/www/downloads/')
    
    if scp_host and scp_user:
        try:
            print("\n📡 使用 SCP 上传...")
            cmd = [
                'scp',
                str(path),
                f'{scp_user}@{scp_host}:{scp_path}{remote_name}'
            ]
            subprocess.run(cmd, check=True)
            print("✅ SCP 上传成功")
            
            # 生成下载链接
            download_url = f"https://{scp_host}/downloads/{remote_name}"
            print(f"\n🔗 下载链接: {download_url}")
            
            # 保存链接到文件
            with open('dist/download_url.txt', 'w') as f:
                f.write(download_url)
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ SCP 上传失败: {e}")
            return False
        except FileNotFoundError:
            print("⚠️  未找到 scp 命令，尝试其他方式...")
    
    # 方式2: 使用 HTTP POST 上传到 API
    if api_key:
        try:
            print("\n📡 使用 HTTP POST 上传...")
            import requests
            
            with open(path, 'rb') as f:
                files = {'file': (remote_name, f, 'application/octet-stream')}
                headers = {'Authorization': f'Bearer {api_key}'}
                
                response = requests.post(
                    server_url,
                    files=files,
                    headers=headers,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ HTTP 上传成功")
                    print(f"🔗 下载链接: {result.get('download_url', 'N/A')}")
                    return True
                else:
                    print(f"❌ HTTP 上传失败: {response.status_code}")
                    print(f"响应: {response.text}")
                    return False
                    
        except ImportError:
            print("⚠️  未安装 requests，请安装: pip install requests")
            return False
        except Exception as e:
            print(f"❌ HTTP 上传失败: {e}")
            return False
    
    # 方式3: 保存到本地目录 (用于测试)
    local_upload_dir = os.getenv('LOCAL_UPLOAD_DIR', '/tmp/uploads')
    try:
        os.makedirs(local_upload_dir, exist_ok=True)
        dest = Path(local_upload_dir) / remote_name
        import shutil
        shutil.copy(path, dest)
        print(f"✅ 已保存到本地: {dest}")
        return True
    except Exception as e:
        print(f"❌ 本地保存失败: {e}")
        return False

def update_version_file(platform_name: str, download_url: str):
    """更新版本文件，用于客户端检查更新"""
    
    version_info = {
        'version': DEFAULT_VERSION,
        'platform': platform_name,
        'download_url': download_url,
        'release_date': datetime.now().isoformat()
    }
    
    import json
    with open(f'dist/version_{platform_name}.json', 'w') as f:
        json.dump(version_info, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 版本信息已保存: dist/version_{platform_name}.json")

def main():
    """主函数"""
    print("=" * 60)
    print("📤 NovelPublisher 自动上传工具")
    print("=" * 60)
    
    # 获取平台信息
    try:
        platform_info = get_platform_info()
    except RuntimeError as e:
        print(f"\n❌ {e}")
        return False
    
    print(f"\n🖥️  平台: {platform_info['name']}")
    print(f"📦 文件: {platform_info['file']}")
    
    # 检查文件是否存在
    if not check_file_exists(platform_info['file']):
        print("\n💡 提示: 请先运行打包脚本")
        print("   python scripts/build_all.py")
        return False
    
    # 上传文件
    server_url = os.getenv('UPLOAD_SERVER_URL', DEFAULT_SERVER)
    api_key = os.getenv('UPLOAD_API_KEY')
    
    success = upload_file(
        platform_info['file'],
        platform_info['remote_name'],
        server_url,
        api_key
    )
    
    if success:
        # 构建下载链接 (根据实际服务器配置修改)
        download_url = f"{server_url}/downloads/{platform_info['remote_name']}"
        update_version_file(platform_info['name'], download_url)
        
        print("\n" + "=" * 60)
        print("✅ 上传完成!")
        print("=" * 60)
        return True
    else:
        print("\n" + "=" * 60)
        print("❌ 上传失败")
        print("=" * 60)
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
