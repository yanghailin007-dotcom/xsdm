# 跨平台部署指南 - 本地与服务器环境一致

## 概述

好消息！**Web服务器本身完全不依赖浏览器或操作系统**。只有番茄上传功能需要Chrome浏览器。

## 环境一致性说明

### 核心Web服务（跨平台，无需浏览器）

以下功能在**任何操作系统**上都能正常工作：
- ✓ 项目管理
- ✓ 角色编辑
- ✓ 世界观查看
- ✓ 章节浏览
- ✓ 创意库管理
- ✓ AI内容生成（需要API密钥）
- ✓ AI图片生成（需要API密钥）
- ✓ AI视频生成（需要API密钥）

### 番茄上传功能（需要Chrome浏览器）

**重要说明**：番茄上传功能是一个**可选的独立功能**，不影响核心Web服务的运行。

#### 本地Windows环境
```python
# 启动Web服务（不需要浏览器）
python scripts/start_server.py

# 如果需要番茄上传功能，需要：
# 1. 手动启动Chrome浏览器
# 2. 访问 https://fanqienovel.com 并登录
# 3. 使用Web界面的番茄上传功能
```

#### Linux服务器环境
```bash
# 启动Web服务（不需要浏览器）
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app

# 如果需要番茄上传功能，需要额外配置：
# 1. 安装Chromium
# 2. 配置X11虚拟显示（xvfb）
# 3. 或者完全禁用番茄上传功能
```

## 推荐方案：环境一致性

### 方案A：完全禁用番茄上传（最简单）

**适用场景**：主要使用AI生成功能，不需要番茄上传

**优势**：
- ✅ 本地和服务器环境完全一致
- ✅ 部署简单，无需额外配置
- ✅ 服务器成本更低（Linux更便宜）

**实施方法**：

Web服务器已经做了容错处理，如果番茄上传器不可用，系统会自动跳过该功能：

```python
# web/web_server_refactored.py 中已有处理
try:
    from src.integration.fanqie_uploader import FanqieUploader
    fanqie_uploader = FanqieUploader()
except ImportError as e:
    logger.error(f"❌ 番茄上传器加载失败: {e}")
    fanqie_uploader = None  # 系统继续运行，只是番茄功能不可用
```

### 方案B：本地启用番茄上传，服务器禁用

**适用场景**：偶尔需要番茄上传，但不是核心功能

**本地Windows**：
```batch
# 1. 启动Web服务
python scripts/start_server.py

# 2. 需要上传时，手动启动Chrome并登录番茄
# 3. 使用Web界面上传功能
```

**Linux服务器**：
```bash
# 番茄上传功能会自动检测失败并禁用
# 其他所有功能正常工作
```

### 方案C：两端都配置Chromium（复杂）

**不推荐**，除非番茄上传是核心业务功能。

需要额外配置：
- Linux: 安装Chromium + X11 + xvfb
- 可能需要VNC或图形界面

## 立即开始使用

### 本地Windows启动

```batch
# 使用新的跨平台启动脚本
python scripts/start_server.py

# 访问: http://localhost:5000
```

### Linux服务器部署

```batch
# 1. 上传代码
cd d:\work6.05
scripts\deploy\complete_deploy.bat

# 2. 在服务器上启动
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
cd /home/novelapp/novel-system
source venv/bin/activate
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

## 功能对比

| 功能 | Windows本地 | Linux服务器 | 需要浏览器 |
|------|------------|-----------|-----------|
| Web界面 | ✅ | ✅ | ❌ |
| 项目管理 | ✅ | ✅ | ❌ |
| 角色编辑 | ✅ | ✅ | ❌ |
| 世界观查看 | ✅ | ✅ | ❌ |
| AI内容生成 | ✅ | ✅ | ❌ |
| AI图片生成 | ✅ | ✅ | ❌ |
| 番茄上传 | ✅ | ⚠️ | ✅ |

## 总结

**您现在可以：**

1. ✅ 本地使用Python启动服务（不依赖浏览器）
2. ✅ 服务器部署到Linux（环境一致）
3. ✅ 两端功能完全一致（除了番茄上传）
4. ✅ 开发和生产环境保持一致

**推荐做法：**

- **开发环境**：本地Windows + Python直接运行
- **生产环境**：Linux服务器 + Gunicorn
- **番茄上传**：作为可选功能，需要时在本地使用

这样您就可以在本地和服务器上使用完全相同的Python环境，不需要担心浏览器依赖问题！