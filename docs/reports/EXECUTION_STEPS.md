# ✅ Web服务完整启动步骤 (一步步执行)

## 📋 执行步骤

### 第1步：打开PowerShell终端
```
快捷键: Win + R
输入: powershell
按回车
```

### 第2步：进入项目目录
```powershell
cd d:\work6.03
```

**确认看到这样的提示:**
```
PS D:\work6.03>
```

### 第3步：启动Web服务
```powershell
python web_server.py
```

**如果成功，你会看到:**
```
[WebServer] 🚀 Web 服务启动
[WebServer] 📱 前端地址: http://localhost:5000
[WebServer] 🌐 API 地址: http://localhost:5000/api
Serving Flask app 'web_server'
Running on http://127.0.0.1:5000
```

**这一步不要关闭终端，保持运行状态**

### 第4步：打开浏览器（新建一个浏览器窗口）
```
Chrome/Edge/Firefox 都可以
```

### 第5步：访问网页
```
在浏览器地址栏输入: http://localhost:5000
按回车
```

**如果成功，你会看到:**
- 首页加载
- 显示"🚀 开始生成"按钮
- 输入框让你填写配置

### 第6步：填写小说配置（可选，可以用默认值）
```
标题: 凡人修仙同人·观战者  (或任意标题)
简介: 精彩的穿越小说故事   (或任意简介)
设定: 架空世界              (或任意设定)
卖点: 创意新颖              (或任意卖点)
章数: 5                      (生成5章)
```

### 第7步：点击生成按钮
```
点击: 🚀 开始生成
```

**系统会自动:**
1. 初始化小说信息
2. 调用模拟API生成
3. 进行质量评估
4. 跳转到阅读页面

### 第8步：查看生成结果
```
左侧面板:  设计信息 + 章节列表
中间面板:  生成的正文内容
右侧面板:  质量评估结果
底部:      仪表板统计
```

---

## ⚠️ 常见问题排查

### 问题 1: 启动时出现 ModuleNotFoundError
**错误信息:**
```
ModuleNotFoundError: No module named 'flask'
```

**解决方案:**
```powershell
pip install flask flask-cors requests
```

然后重新运行:
```powershell
python web_server.py
```

### 问题 2: 端口已被占用
**错误信息:**
```
Address already in use
```

**解决方案:**
```powershell
# 方法1: 找到占用端口的进程并关闭
netstat -ano | Select-String "5000"
taskkill /PID <PID> /F

# 方法2: 改用其他端口
# 编辑 web_server.py 最后一行
# 改成: app.run(port=8000)
```

### 问题 3: 浏览器无法连接
**错误信息:**
```
无法连接到 localhost:5000
ERR_CONNECTION_REFUSED
```

**解决方案:**
```powershell
# 1. 检查终端是否还在运行
#    (看第3步的终端是否还有 "Running on..." 的信息)

# 2. 检查防火墙
#    (Windows Defender 可能阻止了Python)
#    -> 允许 python.exe 通过防火墙

# 3. 重新启动服务
Ctrl+C  (在终端按停止)
python web_server.py  (重新启动)
```

### 问题 4: 生成时出现错误
**错误信息:**
```
500 Internal Server Error
```

**解决方案:**
```powershell
# 1. 查看终端的错误信息
#    (第3步的终端会显示详细错误)

# 2. 常见原因:
#    - MockAPIClient 没有初始化
#    - TestScenario 导入失败
#    - JSON 解析错误

# 3. 解决方法:
#    - 重启服务
#    - 清空浏览器缓存 (Ctrl+Shift+Delete)
#    - 尝试用 http://127.0.0.1:5000 代替 localhost
```

---

## 🧪 快速验证（不需要浏览器）

如果你不想用浏览器，可以用这个快速测试脚本来验证API:

### 在另一个PowerShell窗口运行:
```powershell
cd d:\work6.03
python test_web_api_request.py
```

**如果成功，会显示:**
```
✅ 健康检查: HTTP 200
✅ 首页加载: HTTP 200
✅ 生成成功！
📊 生成了 2 章
📚 小说标题: ...
```

---

## 📊 三个终端窗口配置

### 终端 1: Web服务（主要）
```powershell
cd d:\work6.03
python web_server.py

# 保持运行状态，看日志
# Ctrl+C 停止
```

### 终端 2: 浏览器（或测试）
```
浏览器: http://localhost:5000
或
PowerShell: python test_web_api_request.py
```

### 终端 3: 备用
```
以防需要其他操作
```

---

## ✨ 一键快速启动脚本

如果你想简化步骤，可以用这个脚本:

```powershell
# 保存为: start.ps1

cd d:\work6.03

# 检查依赖
python -m pip install flask flask-cors requests -q

# 启动服务
Write-Host "🚀 启动Web服务..."
python web_server.py
```

**使用方法:**
```powershell
# 1. 打开 PowerShell
# 2. 进入项目目录
cd d:\work6.03

# 3. 运行脚本
.\start.ps1

# 或直接用一行命令:
python -m pip install flask flask-cors requests -q; python web_server.py
```

---

## 🎯 最简洁的操作流程

### 一共只需 3 步:

#### Step 1: 打开PowerShell并进入目录
```powershell
cd d:\work6.03
```

#### Step 2: 启动服务（这个窗口不要关）
```powershell
python web_server.py
```

#### Step 3: 打开浏览器访问
```
http://localhost:5000
```

**完成！现在可以生成小说了**

---

## 🔧 调试技巧

### 看服务是否真的运行了:
```powershell
# 在第二个终端运行
curl http://localhost:5000

# 如果返回 HTML 内容，说明服务正常
# 如果显示 "无法连接"，说明服务没启动
```

### 看详细的错误信息:
```
# 第3步启动时，如果有错误会在终端显示
# 不要关闭终端，复制错误信息给我
```

### 强制停止服务:
```powershell
# 如果 Ctrl+C 不工作
Get-Process python | Stop-Process -Force

# 然后重新启动
python web_server.py
```

---

## ✅ 验证清单

启动成功的标志:
- [ ] 能看到 "Running on http://127.0.0.1:5000"
- [ ] 浏览器打开 http://localhost:5000 能看到首页
- [ ] 页面显示"🚀 开始生成"按钮
- [ ] 能填写配置信息
- [ ] 点击生成后能跳转到阅读页

---

## 📞 如果还是无法工作

请告诉我:
1. **错误信息是什么?** (完整复制)
2. **终端显示了什么?** (启动时的所有日志)
3. **你用的是什么系统?** (Windows 10/11, Python 版本)
4. **防火墙是否允许 Python?**

我会根据具体错误来帮你解决！

---

**版本**: 2.0  
**日期**: 2025-11-21  
**状态**: 完整可执行步骤
