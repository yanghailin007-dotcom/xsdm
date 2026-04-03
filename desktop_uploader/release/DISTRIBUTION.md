# NovelPublisher 分发方案

由于 GitHub 仓库有 100MB 文件大小限制，EXE 文件使用以下替代方案分发：

## 方案一：GitHub Releases（推荐）

### 上传步骤：
1. 打开 GitHub 仓库页面
2. 点击右侧 "Releases" → "Create a new release"
3. 填写版本号（如 v1.3.3）
4. 上传 `NovelPublisher.exe` 文件
5. 发布 Release

### 用户下载链接：
```
https://github.com/yanghailin007-dotcom/xsdm/releases/latest/download/NovelPublisher.exe
```

## 方案二：官网直链

部署到服务器后，在官网提供下载：
```
https://novel-ai.online/downloads/NovelPublisher.exe
```

需要配置 nginx/apache 静态文件服务。

## 方案三：云存储

使用阿里云 OSS / 腾讯云 COS / AWS S3：
```
https://your-bucket.oss-cn-beijing.aliyuncs.com/NovelPublisher.exe
```

## 方案四：本地构建

用户自行构建：
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

## 推荐做法

1. **开发测试**：本地构建使用
2. **内测分发**：GitHub Releases
3. **正式用户**：官网直链 + CDN

## 当前版本

- 版本：v1.3.3
- 大小：约 72MB
- 更新日期：2026-04-03
