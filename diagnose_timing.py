#!/usr/bin/env python3
"""
诊断脚本：测量 phase-one-setup 启动延迟
"""
import time
import sys
from pathlib import Path

# 添加项目根目录到路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

print("=" * 60)
print("诊断：测量 NovelGenerator 初始化时间")
print("=" * 60)

# 1. 测量配置加载时间
print("\n[1/5] 测量配置加载时间...")
start = time.time()
import importlib.util
config_path = BASE_DIR / "config" / "config.py"
spec = importlib.util.spec_from_file_location("config_module", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
CONFIG = config_module.CONFIG
config_time = time.time() - start
print(f"   配置加载完成: {config_time:.3f}秒")

# 2. 测量导入 NovelGenerator 的时间
print("\n[2/5] 测量导入 NovelGenerator 时间...")
start = time.time()
from src.core.NovelGenerator import NovelGenerator
import_time = time.time() - start
print(f"   导入完成: {import_time:.3f}秒")

# 3. 测量 NovelGenerator 初始化时间
print("\n[3/5] 测量 NovelGenerator 初始化时间...")
start = time.time()
novel_generator = NovelGenerator(CONFIG)
init_time = time.time() - start
print(f"   初始化完成: {init_time:.3f}秒")

# 4. 测量第二次创建实例时间（验证单例效果）
print("\n[4/5] 测量第二次创建实例时间...")
start = time.time()
novel_generator2 = NovelGenerator(CONFIG)
init_time2 = time.time() - start
print(f"   第二次初始化完成: {init_time2:.3f}秒")

# 5. 检查单例是否生效
print("\n[5/5] 检查单例状态...")
print(f"   实例1 ID: {id(novel_generator)}")
print(f"   实例2 ID: {id(novel_generator2)}")
print(f"   是否为同一实例: {novel_generator is novel_generator2}")

print("\n" + "=" * 60)
print("诊断结果汇总")
print("=" * 60)
print(f"配置加载时间:     {config_time:.3f}秒")
print(f"导入时间:         {import_time:.3f}秒")
print(f"首次初始化时间:   {init_time:.3f}秒")
print(f"第二次初始化时间: {init_time2:.3f}秒")
print("=" * 60)

if init_time > 5:
    print("警告: 初始化时间超过5秒，需要优化")
elif init_time > 2:
    print("提示: 初始化时间在2-5秒，可接受但可优化")
else:
    print("良好: 初始化时间小于2秒")
