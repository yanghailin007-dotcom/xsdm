# 小说AI生成系统

> 一个基于AI的小说创作平台，支持两阶段生成、短剧视频制作、封面生成等功能。

## ✨ 功能特性

### 📚 小说生成
- **两阶段生成模式**: 先完善设定再生成内容，质量更可控
- **创意库管理**: 保存和管理多个创意种子
- **章节管理**: 支持批量生成和续写

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

## 🚀 快速开始

### 环境要求
- Python 3.9+
- Node.js 16+
- SQLite / PostgreSQL

### 安装步骤

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/novel-ai-generator.git
cd novel-ai-generator

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置 API 密钥

# 启动服务
python app.py
```

访问 http://localhost:5000 即可使用。

## 🛠️ 技术栈

- **后端**: Python Flask
- **前端**: HTML + CSS + JavaScript (原生)
- **数据库**: SQLite / PostgreSQL
- **AI 服务**: 
  - OpenAI API
  - NanoBanana Image Generator
  - VeO Video Generator

## 📁 项目结构

```
.
├── app.py                 # 应用入口
├── config/               # 配置文件
├── src/                  # 核心代码
│   ├── managers/        # 业务逻辑管理器
│   ├── generators/      # 生成器
│   └── models/          # 数据模型
├── web/                  # Web 界面
│   ├── templates/       # HTML 模板
│   └── static/          # 静态资源
├── 视频项目/            # 视频项目存储
├── 小说项目/            # 小说项目存储
└── tests/               # 测试文件
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📝 开源协议

本项目采用 [MIT](LICENSE) 协议开源。

## 🙏 致谢

- OpenAI
- NanoBanana
- VeO

---

⭐ 如果这个项目对你有帮助，请给个 Star 支持一下！
