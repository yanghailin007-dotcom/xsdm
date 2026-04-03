# NovelPublisher 构建说明

## 下载 EXE

由于 GitHub 仓库有 100MB 文件限制，EXE 文件通过 **GitHub Releases** 分发：

### 方式一：GitHub Releases（推荐）
1. 访问项目 Releases 页面：
   `https://github.com/yanghailin007-dotcom/xsdm/releases`

2. 下载最新版本的 `NovelPublisher.exe`

### 方式二：本地构建
```bash
cd desktop_uploader/release
pip install pyinstaller requests urllib3 charset_normalizer idna certifi
pyinstaller --onefile --windowed --name NovelPublisher --clean ^
    --additional-hooks-dir=. ^
    --hidden-import=requests ^
    --hidden-import=urllib3 ^
    --hidden-import=charset_normalizer ^
    --hidden-import=idna ^
    --hidden-import=certifi ^
    --hidden-import=config_env ^
    main.py
```

构建完成后，EXE 位于 `dist/NovelPublisher.exe`

## 版本说明

- 当前版本：v1.3.3
- 官网：https://novel-ai.online
- 本地测试：http://localhost:5000

## 功能特性

1. **多账户系统 V2**：每个官网账户对应一个浏览器实例
2. **自动创建书籍**：找不到书籍时自动创建新书
3. **环境自适应**：自动检测本地/服务器环境
