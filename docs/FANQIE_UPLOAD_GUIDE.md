# 番茄小说自动上传功能使用指南

## 更新内容

本次修复解决了以下问题：
1. ✅ **作品标签选择** - 新增 `_select_book_tags_v2()` 方法，自动选择主分类、主题、角色、情节
2. ✅ **封面上传功能** - 新增 `_handle_cover_upload()` 方法，自动上传封面图片
3. ✅ **封面缺失提示** - 当封面不存在时，会提示用户创建封面并提供路径指导

## 文件结构

```
web/fanqie_uploader/
├── novel_publisher.py          # 修复后的发布器（主要文件）
├── novel_publisher_backup.py   # 原文件备份
├── config_loader.py            # 配置加载器
├── file_handler.py             # 文件处理
└── ui_helper.py                # UI辅助工具
```

## 封面要求

### 封面文件位置
系统会在以下位置查找封面（按优先级排序）：
1. `项目目录/cover.png`
2. `项目目录/cover.jpg`
3. `项目目录/cover.jpeg`
4. `项目目录/小说名_封面.png`
5. `项目目录/小说名_封面.jpg`
6. `项目目录/images/cover.png`
7. `项目目录/images/cover.jpg`

### 封面规格
- **建议尺寸**: 600 × 800 像素
- **格式**: PNG 或 JPG/JPEG
- **文件大小**: 不超过 5MB

### 创建封面
你可以通过以下方式创建封面：
1. 使用大文娱平台的"封面制作"功能
2. 使用第三方设计工具（如 Canva、PS）
3. 使用 AI 绘画工具生成

## 测试脚本

### 运行完整测试
```bash
python test_fanqie_create.py
```

### 仅测试封面提示功能
```bash
python test_fanqie_create.py --test=cover
```

### 仅测试创建书籍功能
```bash
python test_fanqie_create.py --test=create
```

## 使用步骤

### 1. 启动 Chrome
双击运行 `chrome_launcher/start_chrome.bat`，等待 Chrome 完全启动

### 2. 登录番茄小说
在 Chrome 中访问 https://fanqienovel.com/ 并登录作家账号

### 3. 准备小说项目
确保项目目录包含：
```
小说项目/
├── cover.png              # 封面图片（必需）
├── 小说数据.json          # 小说信息
└── chapters/              # 章节文件夹
    ├── 第1章_xxx.txt
    ├── 第2章_xxx.txt
    └── ...
```

### 4. 运行自动上传
通过大文娱平台的 Web 界面启动番茄上传功能

## 标签数据结构

小说 JSON 文件中的标签信息格式：
```json
{
  "selected_plan": {
    "tags": {
      "main_category": "玄幻",
      "themes": ["东方玄幻", "异世大陆"],
      "roles": ["孤儿", "老师"],
      "plots": ["废柴流", "奇遇"],
      "target_audience": "男频"
    }
  }
}
```

## 故障排除

### 问题1: 无法连接到 Chrome
**错误信息**: `连接失败: Error connecting to Chrome`

**解决方案**:
1. 确保已运行 `start_chrome.bat`
2. 检查 Chrome 是否已完全启动（看到浏览器窗口）
3. 检查端口 9988 是否被占用

### 问题2: 标签选择失败
**错误信息**: `未找到标签选择器` 或 `点击标签失败`

**解决方案**:
1. 番茄平台界面可能已更新，需要更新选择器
2. 检查网络连接是否稳定
3. 查看 `debug_screenshots/` 目录下的调试截图

### 问题3: 封面上传失败
**错误信息**: `封面上传失败`

**解决方案**:
1. 检查封面文件是否存在且格式正确
2. 检查封面文件大小是否超过 5MB
3. 尝试手动上传封面，查看是否有平台限制

### 问题4: 书名重复
**错误信息**: `书名已存在`

**解决方案**:
- 修改小说标题后重新运行
- 番茄平台不允许重复的书名

## 调试信息

调试截图保存在 `debug_screenshots/` 目录下，包含：
- `create_book_form_*.png` - 创建表单页面
- `create_book_filled_*.png` - 填写后的表单
- `create_book_menu_*.png` - 创建菜单

## 注意事项

1. **书名长度限制**: 番茄平台限制书名最多15个字符（会自动截断）
2. **主角名长度**: 最多5个字符
3. **简介长度**: 需要50-500字
4. **标签数量**: 主题/角色/情节各最多选择3个
5. **上传频率**: 避免频繁上传，建议每章间隔至少几秒

## 技术支持

如遇到问题，请提供以下信息：
1. 错误日志（控制台输出）
2. 调试截图（`debug_screenshots/` 目录）
3. Chrome 版本号
4. 操作系统版本
