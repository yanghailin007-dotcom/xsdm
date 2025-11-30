# 📖 番茄小说智能生成器

一个基于 AI 的智能小说生成系统，支持完整的从创意到发布的全流程。

## 🌟 特性

- ✅ **完整的小说生成流程** - 从创意精炼到章节内容生成
- ✅ **智能质量评估** - AI 驱动的内容质量分析和改进建议
- ✅ **Web 可视化界面** - 实时查看生成进度和阅读小说
- ✅ **多种生成模式** - 支持手动和全自动生成
- ✅ **项目管理** - 保存和恢复生成进度
- ✅ **灵活配置** - 支持多种 AI 提供商

## 📁 项目结构

```
work6.03/
├── src/                    # 源代码
│   ├── core/              # 核心模块（生成器、API、质量评估等）
│   ├── managers/          # 管理器模块（事件、情感、伏笔等）
│   ├── prompts/           # 提示词模块
│   └── utils/             # 工具模块
├── web/                   # Web 服务
│   ├── web_server.py     # Flask 服务器
│   ├── templates/        # HTML 模板
│   └── static/           # 静态资源
├── config/                # 配置文件
├── scripts/               # 入口脚本（main.py, automain.py）
├── tests/                 # 测试文件
├── docs/                  # 文档
│   ├── guides/           # 使用指南
│   ├── reports/          # 项目报告
│   ├── tests/            # 测试文档
│   └── features/         # 功能文档
├── tools/                 # 工具脚本
├── data/                  # 数据存储
│   ├── projects/         # 小说项目
│   ├── creative_ideas/   # 创意想法
│   ├── quality_data/     # 质量数据
│   ├── generated_images/ # 生成的图片
│   └── debug_responses/  # 调试响应
└── resources/             # 资源文件
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

编辑 `config/config.py`：

```python
"api_keys": {
    "deepseek": "YOUR_API_KEY",
    "gemini": "YOUR_API_KEY"
}
```

### 3. 运行生成器

#### 方式 1: 命令行模式

```bash
# 手动交互式生成
python scripts/main.py

# 全自动连续生成
python scripts/automain.py
```

#### 方式 2: Web 界面模式

```bash
python web/web_server.py
```

然后访问 http://localhost:5000

## 📖 使用文档

### 核心文档
- [快速开始指南](docs/guides/QUICK_START.md) - 5分钟上手
- [Web 生成指南](docs/guides/WEB_GENERATION_GUIDE.md) - Web 端完整使用说明
- [Web 系统总结](docs/guides/WEB_ENHANCEMENT_SUMMARY.md) - Web 系统架构和特性

### 开发文档
- [项目完成报告](docs/reports/PROJECT_COMPLETION_REPORT.md) - 项目整体报告
- [测试文档](docs/tests/TEST_README.md) - 测试系统说明
- [E2E 测试指南](docs/guides/E2E_TEST_GUIDE.md) - 端到端测试

### 重组文档
- [重组总结](REORGANIZATION_SUMMARY.md) - 目录重组完整说明
- **⚠️ 重要**: 如果遇到导入错误，请查看此文档

## 🎯 主要功能

### 1. 命令行生成（scripts/main.py）

```bash
python scripts/main.py
```

功能：
- 交互式创意输入
- 项目管理（新建/继续）
- 章节生成
- 质量评估
- 进度保存

### 2. 全自动生成（scripts/automain.py）

```bash
python scripts/automain.py
```

功能：
- 从 `data/creative_ideas/novel_ideas.txt` 读取创意
- 自动循环生成多个小说
- 完成后自动备份
- 无需人工干预

### 3. Web 生成界面（web/web_server.py）

```bash
python web/web_server.py
```

功能：
- **首页** (`/`) - 创建新小说
- **阅读页** (`/novel`) - 查看生成的小说
- **仪表板** (`/dashboard`) - 统计和分析

特性：
- 后台异步生成
- 实时进度显示
- 三栏布局阅读
- 质量评估可视化

## 🔧 配置说明

### API 提供商

支持的提供商（在 `config/config.py` 中配置）：

- **DeepSeek** - 高质量文本生成
- **Gemini** - Google AI 模型
- **YuanBao** - 其他提供商

### 生成参数

```python
CONFIG = {
    "defaults": {
        "total_chapters": 50,      # 默认总章节数
        "chapter_length": 2000,    # 默认章节长度
        "quality_threshold": 7.0   # 质量阈值
    }
}
```

## 📊 数据管理

### 项目保存位置

所有生成的小说项目保存在：

```
data/projects/
├── <小说标题>_项目信息.json
├── <小说标题>_章节/
│   ├── 第1章.txt
│   ├── 第2章.txt
│   └── ...
└── <小说标题>_章节总览.json
```

### 创意管理

创意文件位置：`data/creative_ideas/novel_ideas.txt`

格式：JSON 格式的创意列表

```json
{
  "creativeWorks": [
    {
      "coreSetting": "故事设定...",
      "coreSellingPoints": "卖点...",
      "completeStoryline": {...}
    }
  ]
}
```

## 🧪 测试

运行所有测试：

```bash
python tests/run_all_tests.py
```

单独测试：

```bash
# 快速测试
python tests/test_quick.py

# Web API 测试
python tests/test_web_api.py

# 端到端测试
python tests/test_e2e_with_mock_data.py
```

## 🛠️ 工具脚本

位于 `tools/` 目录：

- `analyze_architecture.py` - 分析项目架构
- `cleanup_*.py` - 代码清理工具
- `generate_*_report.py` - 生成各类报告
- `web_api_demo.py` - Web API 演示

## 📝 最近更新

### 目录重组（2024-11-22）

✅ 完整重组项目目录结构
✅ 按功能分类组织代码
✅ 更新路径配置
✅ 创建详细文档

**注意**: 如果遇到导入错误，请查看 `REORGANIZATION_SUMMARY.md`

### Web 功能增强

✅ 真实 NovelGenerator 集成
✅ 后台异步任务系统
✅ 实时进度监控
✅ 完整的 API 端点
✅ 项目管理功能

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

此项目仅供学习和研究使用。

## 📞 联系方式

如有问题，请查看文档或提交 Issue。

---

**Happy Writing!** ✨📚
