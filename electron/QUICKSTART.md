# 🚀 快速开始 - 打包Windows桌面应用

## 第一次打包？按这个顺序来！

### 1. 安装Node.js依赖

```bash
cd electron
npm install
```

等待安装完成（可能需要几分钟）

### 2. 测试开发模式（可选但推荐）

```bash
# 在electron目录下
dev.bat
```

这会启动应用，你可以测试功能是否正常。

### 3. 一键打包

```bash
# 在electron目录下
build_all.bat
```

这个脚本会：
- ✅ 打包Python后端为exe
- ✅ 打包Electron前端
- ✅ 生成Windows安装包

### 4. 获取安装包

打包完成后，你会在 `electron/dist/` 目录找到：

```
短剧工作室-Setup-1.0.0.exe  (约200-300MB)
```

### 5. 测试安装包

- 双击安装包
- 安装到测试目录
- 启动应用测试功能

### 6. 分发给用户

将 `短剧工作室-Setup-1.0.0.exe` 上传到：
- GitHub Releases
- 百度网盘
- 阿里云OSS
- 你的网站

---

## 常见问题

### Q: npm install 很慢怎么办？

使用国内镜像：
```bash
npm config set registry https://registry.npmmirror.com
npm install
```

### Q: PyInstaller打包失败？

确保安装了所有Python依赖：
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Q: 打包后的exe很大？

这是正常的，因为包含了：
- Python运行时
- 所有依赖库
- Electron框架
- Chromium浏览器

### Q: 如何减小体积？

1. 使用UPX压缩（在build_backend.bat中添加 `--upx-dir=upx`）
2. 移除不必要的依赖
3. 使用7z压缩分发

### Q: 用户安装后无法启动？

检查：
1. 是否有杀毒软件拦截
2. 是否缺少VC++运行库
3. 查看日志文件

---

## 下一步

- [ ] 添加应用图标（icon.ico和icon.png）
- [ ] 自定义安装界面
- [ ] 添加自动更新功能
- [ ] 配置代码签名（避免Windows警告）
- [ ] 创建便携版（zip格式）

---

## 需要帮助？

如果遇到问题，请提供：
1. 错误信息截图
2. 日志文件
3. 操作系统版本
4. Node.js和Python版本
