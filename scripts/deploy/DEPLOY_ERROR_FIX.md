# 部署脚本错误修复说明

## 问题描述

运行 `deploy_now_fixed.bat` 时出现错误：
```
<< was unexpected at this time.
```

## 错误原因

原脚本在第93行使用了 **Linux heredoc 语法**：
```batch
ssh ... "bash -s" << 'ENDSSH'
...脚本内容...
ENDSSH
```

**问题：** Windows CMD 不支持 `<<` heredoc 语法，这是 Linux/Unix shell 的特性。当 Windows batch 解释器遇到 `<<` 时，会报错 "was unexpected at this time"。

## 解决方案

将远程脚本分三步执行：

### 1. **创建临时脚本文件**
在 Windows 临时目录创建部署脚本文件：
```batch
set TEMP_DEPLOY_SCRIPT=%TEMP%\deploy_server_%RANDOM%.sh
```

### 2. **传输脚本到服务器**
使用 SCP 将脚本文件上传到服务器：
```batch
scp -i "%KEY_PATH%" ... "%TEMP_DEPLOY_SCRIPT%" ...:/tmp/deploy_script.sh
```

### 3. **执行远程脚本**
通过 SSH 执行上传的脚本：
```batch
ssh ... "chmod +x /tmp/deploy_script.sh && bash /tmp/deploy_script.sh"
```

### 4. **清理临时文件**
部署完成后删除临时文件：
```batch
del "%TEMP_DEPLOY_SCRIPT%"
ssh ... "rm -f /tmp/deploy_script.sh"
```

## 关键改进

1. **Windows 兼容性：** 移除了 heredoc 语法，改用临时文件方式
2. **转义处理：** 对 bash 脚本中的特殊字符进行转义：
   - `>` → `^>`
   - `&` → `^&`
   - `|` → `^|`
   - `<` → `^<`

3. **错误处理：** 保存部署结果代码，用于最终状态显示
4. **自动清理：** 部署完成后自动删除临时文件

## 使用方法

### 方式一：直接运行
```cmd
cd d:\work6.05
scripts\deploy\deploy_now_fixed.bat
```

### 方式二：双击运行
在文件管理器中双击 `deploy_now_fixed.bat`

## 预期输出

### 成功部署输出示例：
```
========================================
   完整自动部署工具
========================================

服务器信息:
  IP: 8.163.37.124
  用户: root
  密钥: d:\work6.05\xsdm.pem

正在设置私钥权限...
正在测试SSH连接...
SSH连接成功

正在创建部署压缩包...
压缩包创建成功: novel_system_20260115_101730.tar.gz
大小: 709727320 字节

正在上传到服务器...
上传成功

========================================
   开始服务器部署
========================================

正在创建部署脚本...
正在传输部署脚本到服务器...
正在执行部署脚本...

步骤 1/5: 检查上传的压缩包...
找到压缩包: /tmp/novel_system_20260115_101730.tar.gz

步骤 2/5: 创建项目目录...
目录已创建

步骤 3/5: 解压代码...
代码已解压

步骤 4/5: 设置虚拟环境...
虚拟环境已创建
依赖已安装

步骤 5/5: 创建配置文件...
配置文件已创建

正在测试应用导入...
Application imported successfully

========================================
部署完成!
========================================

手动启动服务:
  cd /home/novelapp/novel-system
  source venv/bin/activate
  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app

访问网站: http://8.163.37.124:5000

========================================
   所有步骤完成!
========================================

连接到服务器启动服务:

ssh -i "d:\work6.05\xsdm.pem" root@8.163.37.124

然后运行:
  cd /home/novelapp/novel-system
  source venv/bin/activate
  gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app

请按任意键继续. . .
```

## 常见问题排查

### 1. 如果仍然出现语法错误
**检查：** 确保你运行的是修复后的 `deploy_now_fixed.bat`，而不是旧版本

### 2. SSH 连接失败
**检查：**
- 私钥文件路径是否正确
- 私钥权限是否正确设置
- 服务器 IP 和端口是否正确

### 3. 压缩包上传失败
**检查：**
- 网络连接是否稳定
- 服务器磁盘空间是否充足

### 4. 部署脚本执行失败
**连接到服务器查看详情：**
```bash
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124
cd /home/novelapp/novel-system
cat logs/error.log
```

## 技术细节

### Windows Batch 特殊字符转义规则

| 原字符 | 转义后 | 说明 |
|--------|--------|------|
| `<` | `^<` | 输入重定向 |
| `>` | `^>` | 输出重定向 |
| `&` | `^&` | 命令连接符 |
| `\|` | `^\|` | 管道符 |
| `^` | `^^` | 转义符本身 |

### 临时文件命名策略

使用 `%RANDOM%` 生成随机数，避免并发执行时的文件冲突：
```batch
set TEMP_DEPLOY_SCRIPT=%TEMP%\deploy_server_%RANDOM%.sh
```

### 错误码保存

```batch
set DEPLOY_RESULT=%ERRORLEVEL%
```
保存部署结果，在脚本清理后仍能判断部署是否成功。

## 相关文件

- **修复后的脚本：** `scripts/deploy/deploy_now_fixed.bat`
- **原始脚本（已修复）：** 同上
- **服务器部署脚本：** 动态生成在 `/tmp/deploy_script.sh`

## 下一步

部署成功后，你需要连接到服务器启动应用服务：

```bash
# 连接到服务器
ssh -i d:\work6.05\xsdm.pem root@8.163.37.124

# 进入项目目录
cd /home/novelapp/novel-system

# 激活虚拟环境
source venv/bin/activate

# 启动服务
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app
```

或者使用后台运行模式：
```bash
nohup gunicorn -w 2 -b 0.0.0.0:5000 --timeout 600 web.web_server_refactored:app > server.log 2>&1 &
```

---

**修复日期：** 2026-01-15  
**修复版本：** deploy_now_fixed.bat v2.0
