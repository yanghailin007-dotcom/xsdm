# 部署系统使用说明

## 📌 核心概念

### rsync 是如何工作的？

**rsync 的核心优势**：**增量同步** - 只传输修改过的文件

```
第一次部署：传输所有文件（约几百MB）
第二次部署：只传输修改过的文件（可能只有几KB）
```

**工作原理**：
1. rsync 比较本地和远程文件的：
   - 文件大小
   - 修改时间
   - 校验和（可选）

2. 只传输有差异的文件
3. 保留文件的权限、时间戳等属性

## 🎯 部署脚本说明

### 1. [`deploy_rsync.bat`](deploy_rsync.bat) - 推荐使用 ⭐

**特点**：
- ✅ 使用 rsync 增量同步
- ✅ 自动检测 Git Bash 的 rsync
- ✅ 显示传输进度和统计信息
- ✅ 只传输修改的文件，速度快

**适用场景**：
- 日常开发部署
- 文件修改频繁
- 网络带宽有限

**使用方法**：
```batch
REM 1. 编辑脚本顶部的配置
set SERVER_IP=8.163.37.124
set SERVER_USER=root
set KEY_PATH=d:\work6.05\xsdm.pem

REM 2. 运行脚本
scripts\deploy\deploy_rsync.bat
```

**rsync 排除规则**（不同步这些文件）：
- `__pycache__` - Python 缓存
- `*.pyc` - 编译的 Python 文件
- `.git` - Git 仓库
- `logs/*` - 日志文件
- `generated_images/*` - 生成的图片
- `temp_fanqie_upload/*` - 临时上传
- `.env` - 环境变量
- `test_*.py` - 测试文件
- `*.db` - 数据库文件
- `小说项目/*` - 小说项目
- `Chrome/*` - Chrome 相关
- `knowledge_base/*` - 知识库
- `ai_enhanced_settings/*` - AI 设置
- `fusion_settings/*` - 融合设置
- `*.bat` - Windows 批处理
- `*.sh` - Shell 脚本
- `*.md` - Markdown 文档

**重要**：这些文件不会被同步，避免：
- 传输无用文件（缓存、日志）
- 覆盖服务器本地配置（.env）
- 传输大文件（数据库、图片）

### 2. [`restart_server.bat`](restart_server.bat) - 快速重启

**特点**：
- ✅ 不传输文件
- ✅ 只重启服务
- ✅ 速度快

**适用场景**：
- 只修改了 Python 代码
- 确认服务器文件已是最新

**使用方法**：
```batch
REM 1. 先手动同步需要修改的文件（如果需要）
scp -i "d:\work6.05\xsdm.pem" -P 22 ^
    web\api\your_api.py ^
    root@8.163.37.124:/home/novelapp/novel-system/web/api/

REM 2. 重启服务
scripts\deploy\restart_server.bat
```

### 3. [`server_deploy_stable.sh`](server_deploy_stable.sh) - 服务器端脚本

**功能**：
- 清理端口 5000（使用 5 种方法检测）
- 终止旧的 gunicorn 进程
- 启动新的 gunicorn 服务
- 验证服务状态

**自动执行**：由 Windows 脚本上传并执行

## 🔍 rsync 传输示例

### 场景 1：首次部署
```
sent 125,400,200 bytes  received 84,200 bytes
total size is 125,300,000  speedup is 1.00

传输：125MB（所有文件）
时间：约 2-5 分钟
```

### 场景 2：修改了 1 个文件
```
sent 12,400 bytes  received 84,200 bytes
total size is 125,300,000  speedup is 5,234.21

传输：12KB（只有修改的文件）
时间：约 2-5 秒
```

**节省**：
- 时间：从 2-5 分钟 → 2-5 秒
- 带宽：从 125MB → 12KB
- 成本：显著降低

## 🛠️ 安装 rsync

### Windows

**方法 1：安装 Git for Windows（推荐）**
1. 下载：https://git-scm.com/download/win
2. 安装（默认选项即可）
3. rsync 位置：
   - `C:\Program Files\Git\usr\bin\rsync.exe`
   - 或 `C:\Program Files\Git\mingw64\bin\rsync.exe`

**方法 2：使用 cwRsync**
1. 下载：https://itefix.net/cwrsync
2. 解压到指定目录
3. 添加到系统 PATH

**验证安装**：
```batch
where rsync
REM 应该显示 rsync 路径
```

### Linux
通常已预装，如需安装：
```bash
# Ubuntu/Debian
sudo apt-get install rsync

# CentOS/RHEL
sudo yum install rsync
```

## 📋 工作流程对比

### 方案 A：使用 rsync（推荐）⭐

```
1. 修改代码
2. 运行 deploy_rsync.bat
   ├─ 自动检测 rsync
   ├─ 只传输修改的文件
   ├─ 上传部署脚本
   └─ 重启服务
3. 完成（2-5秒）
```

### 方案 B：手动 scp + 重启

```
1. 修改代码
2. 手动上传每个修改的文件
   scp -i key file.py server:/path/
3. 运行 restart_server.bat
4. 完成（需要多次操作）
```

### 方案 C：完整 scp 同步

```
1. 修改代码
2. 运行完整 scp 同步
   ├─ 传输所有文件（慢）
   └─ 浪费带宽和时间
3. 重启服务
4. 完成（2-5分钟）
```

## 🎯 推荐使用方式

### 日常开发流程

```batch
REM 1. 修改代码
REM 2. 运行部署（自动增量同步）
scripts\deploy\deploy_rsync.bat

REM 等待 2-5 秒，完成！
```

### 多次小修改

```batch
REM 第一次
scripts\deploy\deploy_rsync.bat

REM 修改代码...

REM 第二次（只传输修改的文件）
scripts\deploy\deploy_rsync.bat

REM 修改代码...

REM 第三次（还是只传输修改的文件）
scripts\deploy\deploy_rsync.bat
```

### 紧急修复单个文件

```batch
REM 1. 快速上传单个文件
scp -i "d:\work6.05\xsdm.pem" -P 22 ^
    web\api\fix.py ^
    root@8.163.37.124:/home/novelapp/novel-system/web/api/

REM 2. 快速重启
scripts\deploy\restart_server.bat
```

## 🚨 故障排查

### 问题：未找到 rsync

**症状**：
```
❌ 未找到rsync
请安装Git for Windows获得rsync支持
```

**解决方案**：
1. 安装 Git for Windows
2. 重启命令提示符
3. 重新运行脚本

### 问题：同步失败

**症状**：
```
❌ rsync同步失败 (错误代码: X)
```

**解决方案**：
1. 检查网络连接
2. 检查私钥文件是否存在
3. 检查服务器 IP 是否正确
4. 查看详细错误信息

### 问题：端口仍被占用

**症状**：
```
❌ Connection in use: ('0.0.0.0', 5000)
```

**解决方案**：
1. 脚本会自动清理端口
2. 如果仍然失败，手动清理：
   ```bash
   ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124
   lsof -ti:5000 | xargs kill -9
   ```

## 📊 性能对比

| 方案 | 首次部署 | 修改1个文件 | 修改10个文件 | 优点 | 缺点 |
|------|---------|------------|-------------|------|------|
| **rsync** | 2-5分钟 | 2-5秒 | 5-10秒 | 快速、智能、省带宽 | 需要安装 |
| **完整scp** | 2-5分钟 | 2-5分钟 | 2-5分钟 | 简单、无需安装 | 慢、浪费带宽 |
| **手动scp** | 手动上传 | 手动上传 | 手动上传 | 精确控制 | 繁琐、易错 |

## 💡 最佳实践

1. **首次部署**：使用 `deploy_rsync.bat` 传输所有文件
2. **日常开发**：使用 `deploy_rsync.bat` 增量同步
3. **紧急修复**：手动 scp + `restart_server.bat`
4. **定期维护**：查看日志，清理无用文件

## 📚 相关文件

- [`deploy_rsync.bat`](deploy_rsync.bat) - rsync 增量部署脚本
- [`restart_server.bat`](restart_server.bat) - 快速重启脚本
- [`server_deploy_stable.sh`](server_deploy_stable.sh) - 服务器端部署脚本
- [`deploy_config.ini`](deploy_config.ini) - 配置文件（可选）

## 🎓 总结

**rsync 的价值**：
- ✅ **速度**：增量同步，只传修改的文件
- ✅ **效率**：节省带宽和时间
- ✅ **智能**：自动检测文件差异
- ✅ **可靠**：保留文件属性，支持断点续传

**使用建议**：
1. 安装 Git for Windows（自带 rsync）
2. 使用 `deploy_rsync.bat` 进行日常部署
3. 享受快速、高效的部署体验！