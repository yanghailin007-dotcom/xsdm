# Chrome自动化发布系统

## 项目概述

这是一个番茄小说自动化发布系统，提供小说自动发布、签约管理、作品推荐等功能。系统已经过重构，采用模块化设计，提高了代码的可维护性和扩展性。

## 目录结构

```
Chrome/
├── automation/                 # 自动化功能主目录
│   ├── core/                  # 核心模块
│   │   ├── browser_manager.py     # 浏览器管理器
│   │   └── novel_publisher.py     # 小说发布器
│   ├── managers/              # 管理器模块
│   │   └── contract_manager.py    # 签约管理器
│   ├── utils/                 # 工具模块
│   │   ├── config_loader.py        # 配置加载器
│   │   ├── file_handler.py         # 文件处理工具
│   │   └── ui_helper.py           # UI操作辅助
│   ├── legacy/                # 原有代码（已弃用）
│   │   ├── autopush_legacy.py      # 原始自动发布代码
│   │   └── contract_manager_legacy.py  # 原始签约管理代码
│   └── __init__.py            # 模块初始化
├── browser/                   # 浏览器相关文件
│   ├── chrome.exe            # Chrome浏览器
│   ├── chrome++.ini          # 浏览器配置
│   └── ...                   # 其他浏览器文件
├── config/                    # 配置文件目录
│   └── automation_config.yaml  # 自动化系统配置
├── data/                      # 数据存储目录
│   ├── cache/                 # 浏览器缓存
│   └── progress/              # 发布进度数据
├── scripts/                   # 启动脚本目录
│   └── start_automation.py    # 主启动脚本
├── docs/                      # 文档目录
│   └── README.md             # 本文档
└── logs/                      # 日志文件目录
```

## 核心功能

### 1. 自动小说发布
- 自动创建新书
- 章节批量发布
- 定时发布管理
- 进度跟踪和恢复

### 2. 签约管理
- 自动检测未签约小说
- 批量处理签约申请
- 自动填写签约信息
- 失败重试机制

### 3. 作品推荐
- 自动检测可推荐作品
- 批量处理推荐任务
- 智能状态管理

### 4. 浏览器管理
- 自动连接Chrome调试端口
- 页面导航和验证
- 多页面管理
- 错误恢复机制

## 配置说明

主配置文件位于 `config/automation_config.yaml`，包含以下配置项：

### 基础配置
- `debug_port`: Chrome调试端口（默认9988）
- `scan_interval`: 扫描间隔秒数（默认1800）
- `max_retries`: 最大重试次数（默认3）

### 路径配置
- `novel_path`: 小说项目目录
- `published_path`: 已发布小说目录
- `progress_file`: 发布进度文件

### 发布配置
- `min_words_for_scheduled_publish`: 定时发布字数阈值
- `publish_times`: 发布时间点列表
- `chapters_per_time_slot`: 每个时间点最大章节数

### 签约配置
- `max_retry_count`: 签约最大重试次数
- `contact_info`: 联系信息（手机、邮箱、QQ、银行卡等）

## 使用方法

### 1. 启动系统

```bash
# 进入Chrome目录
cd Chrome

# 运行自动化系统（连续扫描模式）
python scripts/start_automation.py

# 或指定单次扫描模式
python scripts/start_automation.py --mode single

# 或指定自定义配置目录
python scripts/start_automation.py --config /path/to/config
```

### 2. 准备小说项目

在配置的 `novel_path` 目录下创建小说项目，每个项目包含：
- `{小说标题}_项目信息.json`: 小说基本信息
- `{小说标题}_章节/`: 章节文件目录

### 3. 章节文件格式

每个章节文件为JSON格式，包含：
```json
{
  "chapter_number": 1,
  "chapter_title": "第一章标题",
  "content": "章节内容..."
}
```

## 依赖要求

### Python包
- `playwright`: 浏览器自动化
- `pyyaml`: YAML配置文件解析
- `pathlib`: 路径处理

### 浏览器环境
- Chrome浏览器（支持远程调试）
- 需要以调试模式启动：`chrome.exe --remote-debugging-port=9988`

## 日志和监控

### 日志文件
- 位置：`logs/automation.log`
- 包含详细的操作日志和错误信息

### 进度跟踪
- 发布进度：`发布进度.json`
- 详细进度：`发布进度细节.json`
- 自动保存和恢复

## 故障排除

### 常见问题

1. **浏览器连接失败**
   - 确保Chrome以调试模式启动
   - 检查调试端口配置
   - 确认防火墙设置

2. **配置文件错误**
   - 检查YAML语法
   - 验证必需的配置项
   - 查看系统初始化日志

3. **小说项目找不到**
   - 确认路径配置正确
   - 检查文件命名格式
   - 验证JSON文件格式

### 调试模式

修改配置文件中的日志级别为DEBUG：
```yaml
logging:
  level: "DEBUG"
```

## 开发说明

### 添加新功能

1. 在相应模块中添加功能
2. 更新配置文件结构
3. 添加单元测试
4. 更新文档

### 代码规范

- 使用类型注解
- 添加详细的文档字符串
- 遵循PEP 8代码风格
- 使用适当的异常处理

## 版本历史

- **v2.0.0**: 完全重构，模块化设计
- **v1.0.0**: 初始版本，单体应用

## 联系方式

如有问题或建议，请通过以下方式联系：
- 项目仓库：[GitHub链接]
- 问题反馈：[Issues链接]
- 文档更新：[Wiki链接]

## 许可证

本项目采用 [许可证名称] 许可证。详见 LICENSE 文件。