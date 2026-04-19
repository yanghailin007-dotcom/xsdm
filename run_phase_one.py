# -*- coding: utf-8 -*-
"""
启动一阶段生成脚本

使用 NovelGenerator.phase_one_generation() 启动一阶段
"""
import sys
import io
import json
from pathlib import Path

# 修复 Windows 编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.core.NovelGenerator import NovelGenerator

# 加载创意种子
with open("data/creative_ideas/yanghailin/novel_ideas.txt", "r", encoding="utf-8") as f:
    ideas_data = json.load(f)

creative_seed = ideas_data["creativeWorks"][0]
print(f"创意种子: {creative_seed.get('novelTitle', '未命名')}")

# 构建配置
config = {
    "defaults": {
        "total_chapters": creative_seed.get("totalChapters", 200),
        "chapters_per_batch": 3,
        "max_tokens": 8192,  # deepseek 限制
    },
    "use_creative_conversation_mode": True,
    "use_domain_session_mode": True,
    # 🔥 强制使用 deepseek（gemini 密钥已过期）
    "default_provider": "deepseek",
    # API 配置（旧版格式，向后兼容）
    "api_keys": {
        "gemini": "sk-zwgxnnUut1E7zJMxXjCAQ3zeUefeM8tm9HYQCY50lVTM53CD",
        "deepseek": "sk-1342f04c85c5452ab46c673aa1a12c0b",
    },
    "api_urls": {
        "gemini": "https://newapi.xiaochuang.cc/v1/chat/completions",
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
    },
    "models": {
        "gemini": "gemini-3-flash-preview-thinking",
        "deepseek": "deepseek-chat",
    },
}

# 创建 NovelGenerator
print("初始化 NovelGenerator...")
generator = NovelGenerator(config)

# 启动一阶段
print("=" * 60)
print("启动一阶段生成...")
print("=" * 60)

result = generator.phase_one_generation(
    creative_seed=creative_seed,
    total_chapters=creative_seed.get("totalChapters", 200),
    start_new=True,
    target_platform="fanqie",
)

print("=" * 60)
print(f"一阶段生成结果: {result}")
print("=" * 60)
