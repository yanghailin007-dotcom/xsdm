# 构建发布流程

## 快速开始

### 1. 推送版本标签触发构建

```bash
# 设置版本号
VERSION="v1.0.0"

# 创建标签
git tag $VERSION

# 推送到 GitHub 触发 Actions
git push origin $VERSION
```

### 2. 等待 GitHub Actions 构建完成

访问 Actions 页面查看进度：
`https://github.com/yanghailin/xsdm/actions`

构建大约需要 5-10 分钟。

### 3. 下载构建产物到本地

```bash
# 下载最新版本
python scripts/download_release.py

# 或下载指定版本
python scripts/download_release.py v1.0.0
```

### 4. 提交到 GitHub（供服务器同步）

```bash
# 添加下载的文件
git add desktop_uploader/release/

# 提交
git commit -m "chore: update build artifacts v1.0.0"

# 推送
git push origin main
```

### 5. 服务器自动同步

服务器会定期 `git pull` 同步最新代码，用户即可下载新版本。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `scripts/build_windows.py` | Windows 本地打包 |
| `scripts/build_macos.py` | macOS 本地打包 |
| `scripts/build_all.py` | 自动检测平台打包 |
| `scripts/download_release.py` | 从 GitHub Releases 下载构建产物 |
| `.github/workflows/build-release.yml` | GitHub Actions 配置 |

---

## 目录结构

```
desktop_uploader/release/
├── NovelPublisher.exe                  # Windows 版本（本地构建或下载）
├── NovelPublisher-macos.zip           # macOS Intel（GitHub Actions 下载）
└── NovelPublisher-macos-arm64.zip     # macOS ARM64（GitHub Actions 下载）
```

---

## 常见问题

### Q: 下载脚本提示 "无法获取 Release 信息"
- 检查网络连接
- 确认 GitHub 用户名和仓库名正确（修改脚本中的 `GITHUB_OWNER`）
- 确认 Release 已发布（推送 tag 后需要等待构建完成）

### Q: 只想构建 Windows 版本
```bash
python scripts/build_windows.py
```

### Q: macOS 版本构建失败
GitHub Actions 会自动构建 macOS 版本，不需要本地 Mac 电脑。
