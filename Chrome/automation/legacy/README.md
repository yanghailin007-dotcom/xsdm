# 番茄小说自动发布程序 - Legacy版本

## 概述

这是番茄小说自动发布程序的Legacy版本，包含完整的自动发布和合同管理功能。

## 修复内容

### 导入问题修复
- ✅ 修复了相对导入问题 (`ImportError: attempted relative import with no known parent package`)
- ✅ 创建了模块化的启动器脚本
- ✅ 添加了智能导入回退机制

### 新增功能
- ✅ 创建了专用的启动器 `run_legacy_publisher.py`
- ✅ 添加了批处理启动脚本 `run_legacy_publisher.bat`
- ✅ 完善了模块结构和 `__init__.py` 文件

## 运行方法

### 方法1: 使用批处理脚本 (推荐)
```bash
# 双击运行或在命令行中执行
run_legacy_publisher.bat
```

### 方法2: 使用Python启动器
```bash
python Chrome/automation/run_legacy_publisher.py
```

### 方法3: 使用模块方式运行
```bash
cd Chrome/automation
python -m legacy.autopush_legacy
```

### 方法4: 直接运行 (需要正确设置Python路径)
```bash
python Chrome/automation/legacy/autopush_legacy.py
```

## 功能特性

### 核心功能
- 🚀 **自动发布章节**: 支持批量发布小说章节到番茄小说平台
- ⏰ **智能定时发布**: 根据累计字数自动设置定时发布时间
- 📚 **多小说管理**: 支持同时管理多本小说的发布流程
- 🔄 **断点续传**: 支持从中断点继续发布，避免重复

### 合同管理
- 📋 **自动签约**: 检测并处理小说的自动签约流程
- 📝 **合同填写**: 自动填写合同相关信息
- ✅ **状态跟踪**: 跟踪签约状态和失败处理

### 浏览器自动化
- 🌐 **智能连接**: 自动连接和管理Chrome浏览器
- 🎯 **精准定位**: 使用多种选择器确保元素定位准确
- 🛡️ **错误恢复**: 具备页面状态检测和恢复机制

## 配置要求

### 环境要求
- Python 3.7+
- Chrome浏览器
- Playwright库

### 目录结构
```
小说项目/                          # 小说项目目录
├── 小说名_项目信息.json           # 项目信息文件
├── 小说名_章节/                   # 章节目录
│   ├── 第1章_章节标题.txt
│   └── 第2章_章节标题.txt
└── 已经发布/                       # 已发布小说目录
```

## 使用说明

1. **准备小说项目**
   - 确保 `小说项目/` 目录存在
   - 准备好项目信息JSON文件
   - 组织好章节文件

2. **启动程序**
   - 运行 `run_legacy_publisher.bat`
   - 或使用其他启动方法

3. **按照提示操作**
   - 程序会自动检测Chrome浏览器
   - 导航到番茄小说作家专区
   - 自动处理发布和签约流程

## 故障排除

### 常见问题

**Q: 出现导入错误**
A: 确保使用提供的启动脚本，不要直接运行单个文件

**Q: 浏览器连接失败**
A: 检查Chrome是否已启动，或允许程序自动启动Chrome

**Q: 找不到小说文件**
A: 检查 `小说项目/` 目录和文件命名是否符合要求

### 日志和调试
- 程序会输出详细的执行日志
- 检查 `Chrome/logs/` 目录下的日志文件
- 使用 `-v` 参数启用详细输出

## 技术细节

### 修复的导入问题
原始代码使用相对导入：
```python
from .contract_manager_legacy import ContractManager
```

修复后支持多种导入方式：
```python
try:
    from .contract_manager_legacy import ContractManager
except ImportError:
    from Chrome.automation.legacy.contract_manager_legacy import ContractManager
```

### 智能路径管理
启动器自动处理Python路径：
```python
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

## 更新日志

### v1.1.0 (2024-12-20)
- ✅ 修复相对导入问题
- ✅ 添加启动器脚本
- ✅ 创建批处理启动脚本
- ✅ 完善模块结构
- ✅ 添加智能导入回退

### v1.0.0
- ✅ 基础自动发布功能
- ✅ 合同管理功能
- ✅ 浏览器自动化

## 支持

如果遇到问题，请：
1. 检查本文档的故障排除部分
2. 查看程序输出的错误信息
3. 确认环境配置是否正确