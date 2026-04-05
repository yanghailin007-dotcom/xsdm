#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键构建安装包脚本

依赖:
  - PyInstaller (pip install pyinstaller)
  - Inno Setup 6 (https://jrsoftware.org/isdl.php)

使用方法:
  python build_installer.py

输出:
  desktop_uploader/release/installer_output/大文娱小说发布助手_Setup_v1.3.7.exe
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# 当前脚本所在目录 (desktop_uploader/)
BASE_DIR = Path(__file__).parent.resolve()
RELEASE_DIR = BASE_DIR / "release"
ISS_PATH = RELEASE_DIR / "setup.iss"
SPEC_PATH = RELEASE_DIR / "NovelPublisher.spec"
OUTPUT_DIR = RELEASE_DIR / "installer_output"


def find_iscc() -> Path:
    """查找 Inno Setup 编译器 ISCC.exe"""
    common_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    for p in common_paths:
        if p.exists():
            return p
    # 尝试 PATH
    try:
        result = subprocess.run(
            ["where", "ISCC.exe"],
            capture_output=True,
            text=True,
            check=True,
        )
        path = Path(result.stdout.strip().splitlines()[0])
        if path.exists():
            return path
    except Exception:
        pass
    return None


def clean_release_build():
    """清理 release 目录下的旧构建文件"""
    dirs_to_clean = [RELEASE_DIR / "build", RELEASE_DIR / "dist"]
    for d in dirs_to_clean:
        if d.exists():
            print(f"清理 {d} ...")
            shutil.rmtree(d)


def build_onedir() -> bool:
    """使用 PyInstaller 构建单文件版本 (onefile)"""
    print("=" * 60)
    print("步骤 1/2: PyInstaller 构建单文件版本")
    print("=" * 60)
    
    # 使用单文件 spec
    onefile_spec = RELEASE_DIR / "NovelPublisher_onefile.spec"
    if not onefile_spec.exists():
        print(f"[X] 未找到单文件 spec: {onefile_spec}")
        return False

    clean_release_build()

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(onefile_spec),
        "--noconfirm",
        "--clean",
        "--workpath", str(RELEASE_DIR / "build"),
        "--distpath", str(RELEASE_DIR / "dist"),
    ]
    print("执行命令:")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd, cwd=str(RELEASE_DIR))
    if result.returncode != 0:
        print("\n[X] PyInstaller 构建失败！")
        return False

    exe_path = RELEASE_DIR / "dist" / "NovelPublisher.exe"
    if not exe_path.exists():
        print(f"\n[X] 未找到构建输出: {exe_path}")
        return False

    # 单文件版本 - 直接复制到 release 根目录
    target_exe = RELEASE_DIR / "NovelPublisher.exe"
    
    # 备份旧文件
    if target_exe.exists():
        backup = RELEASE_DIR / "NovelPublisher.exe.bak"
        shutil.move(str(target_exe), str(backup))
    
    # 移动新文件
    shutil.move(str(exe_path), str(target_exe))
    
    # 清理临时备份
    if (RELEASE_DIR / "NovelPublisher.exe.bak").exists():
        (RELEASE_DIR / "NovelPublisher.exe.bak").unlink()

    size_mb = target_exe.stat().st_size / (1024 * 1024)
    print(f"\n[OK] 单文件版本构建成功: {target_exe}")
    print(f"   文件大小: {size_mb:.2f} MB")
    return True


def build_installer(iscc_path: Path) -> bool:
    """使用 Inno Setup 构建安装包"""
    print("\n" + "=" * 60)
    print("步骤 2/2: Inno Setup 打包安装程序")
    print("=" * 60)

    if not ISS_PATH.exists():
        print(f"❌ 未找到 ISS 脚本: {ISS_PATH}")
        return False

    OUTPUT_DIR.mkdir(exist_ok=True)

    cmd = [str(iscc_path), str(ISS_PATH)]
    print("执行命令:")
    print(" ".join(cmd))
    print()

    result = subprocess.run(cmd, cwd=str(RELEASE_DIR))
    if result.returncode != 0:
        print("\n❌ Inno Setup 打包失败！")
        return False

    # 查找生成的安装包
    setups = list(OUTPUT_DIR.glob("*.exe"))
    if not setups:
        print("[X] 未找到生成的安装包")
        return False

    setup_file = max(setups, key=lambda p: p.stat().st_mtime)
    size_mb = setup_file.stat().st_size / (1024 * 1024)
    print(f"\n[OK] 安装包构建成功！")
    print(f"   文件: {setup_file}")
    print(f"   大小: {size_mb:.1f} MB")

    # 注意：单文件版本 (NovelPublisher.exe, ~72MB) 和安装包 (Setup.exe, ~145MB) 是不同的
    # 单文件版本直接运行，安装包需要安装
    # 两者都保留在 installer_output 目录中

    return True


def main():
    print("大文娱小说发布助手 - 安装包构建脚本\n")

    # 检查 PyInstaller
    try:
        import PyInstaller
        print("[OK] PyInstaller 已安装")
    except ImportError:
        print("[X] PyInstaller 未安装，请先运行: pip install pyinstaller")
        sys.exit(1)

    # 构建 onedir
    if not build_onedir():
        sys.exit(1)

    # 查找 Inno Setup
    iscc = find_iscc()
    if not iscc:
        print("\n[!] 未找到 Inno Setup 编译器 (ISCC.exe)")
        print("   安装包无法生成，但 onedir 版本已经构建完成。")
        print("   请从以下地址下载并安装 Inno Setup 6:")
        print("   https://jrsoftware.org/isdl.php")
        print("   安装后重新运行本脚本即可自动生成 Setup.exe")
        sys.exit(0)

    print(f"[OK] 找到 Inno Setup: {iscc}")

    # 构建安装包
    if not build_installer(iscc):
        sys.exit(1)

    print("\n[DONE] 全部完成！")


if __name__ == "__main__":
    main()
