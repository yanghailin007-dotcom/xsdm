# 大文娱系统（小说AI生成系统）

> 一个基于AI的小说创作平台，支持两阶段生成、短剧视频制作、封面生成、自动上传等功能。

## ✨ 功能特性

### 📚 小说生成
- **两阶段生成模式**: 先完善设定再生成内容，质量更可控
- **创意库管理**: 保存和管理多个创意种子
- **章节管理**: 支持批量生成和续写
- **平台适配**: 针对番茄小说风格优化

### 🎬 短剧制作
- **分镜头脚本**: 自动生成创意分镜头
- **视频生成**: 集成 VeO 视频生成API
- **配音合成**: 自动为镜头台词生成语音

### 🎨 封面制作
- **AI封面生成**: 使用 NanoBanana 生成精美封面
- **批量处理**: 支持多种尺寸和风格

### 📤 平台对接
- **番茄小说**: 一键上传到番茄小说平台
- **签约管理**: 合同管理功能

---

## 🚀 快速开始

### 系统要求
- Windows 10/11
- 网络连接（首次安装需要下载Python和依赖）
- 磁盘空间：约 200MB

### 两种启动方式

#### 方式一：Windows 批处理（推荐）

**第一次使用（安装环境 + 启动）：**
```
双击运行：初始化安装.bat
```
- 自动检查 Python 环境
- 如无 Python，自动下载安装嵌入式 Python 3.11
- 自动安装所有依赖
- 安装完成后自动启动服务

**日常使用（仅启动）：**
```
双击运行：启动服务.bat
```
- 快速启动 Web 服务
- 自动打开浏览器访问首页

#### 方式二：命令行

**第一次使用：**
```bash
python setup.py
```

**日常使用：**
```bash
python start.py
```

---

## 🌐 访问地址

服务启动后，访问以下地址：

- **首页**: http://localhost:5000/landing
- **小说创作**: http://localhost:5000/
- **API 接口**: http://localhost:5000/api

---

## 📁 项目结构

```
.
├── setup.py                 # 初始化安装脚本
├── start.py                 # 日常启动脚本
├── 初始化安装.bat            # Windows 初始化入口
├── 启动服务.bat              # Windows 启动入口
├── python-embed/            # 嵌入式 Python 环境（自动创建）
├── config/                  # 配置文件
├── src/                     # 核心代码
│   ├── managers/           # 业务逻辑管理器
│   ├── generators/         # 生成器
│   └── models/             # 数据模型
├── web/                     # Web 服务
│   ├── web_server_refactored.py  # Web服务器主文件
│   ├── templates/          # HTML 模板
│   └── static/             # 静态资源
├── scripts/                 # 工具脚本
├── 视频项目/               # 视频项目存储
├── 小说项目/               # 小说项目存储
└── data/                   # 数据库文件
```

---

## 🛠️ 技术栈

- **后端**: Python 3.11 + Flask
- **前端**: HTML5 + CSS3 + JavaScript (原生)
- **数据库**: SQLite
- **AI 服务**: 
  - OpenAI API / DeepSeek / Gemini
  - NanoBanana Image Generator
  - VeO Video Generator

---

## ⚙️ 配置说明

### API 密钥配置

首次使用前，需要配置 AI 服务的 API 密钥：

1. 复制环境变量示例文件：
   ```bash
   copy .env.example .env
   ```

2. 编辑 `.env` 文件，填入你的 API 密钥：
   ```
   DEEPSEEK_API_KEY=your_deepseek_api_key
   GEMINI_API_KEY=your_gemini_api_key
   # 其他配置...
   ```

### 添加额外依赖

如需安装其他 Python 包：
```bash
# 使用嵌入式 Python 的 pip
python-embed\python.exe -m pip install <包名>
```

---

## 📝 常见问题

### Q: 提示找不到 Python？
运行 `初始化安装.bat`，会自动下载安装嵌入式 Python。

### Q: 端口 5000 被占用？
脚本会自动清理端口 5000 的进程，无需手动操作。

### Q: 依赖安装失败？
检查网络连接，然后重新运行 `初始化安装.bat`。

### Q: 如何停止服务？
在运行服务的窗口中按 **Ctrl+C** 两次（防止误触）。

---

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

---

## 📄 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

---

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
