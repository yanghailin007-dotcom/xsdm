# 🚀 快速启动指南

## 安装依赖

```bash
# 安装所需的 Python 包
pip install -r requirements.txt
```

如果遇到问题，可以分别安装：

```bash
pip install flask flask-cors requests python-dotenv
```

## 检查配置

确保 `config.py` 中的 API 密钥已配置：

```python
"api_keys": {
    "doubao": "YOUR_DOUBAO_API_KEY",
    "claude": "YOUR_CLAUDE_API_KEY"
}
```

## 启动 Web 服务

```bash
python web_server.py
```

## 访问网页

- **首页（生成页面）**: http://localhost:5000/
- **阅读页面**: http://localhost:5000/novel
- **仪表板**: http://localhost:5000/dashboard

## API 文档

查看完整 API 文档：`WEB_GENERATION_GUIDE.md`