# 番茄上传封面预检查功能

## 功能描述

在番茄上传页面，当用户选择项目并点击"开始上传"按钮时，系统会先检查项目是否有封面。如果缺少封面，会弹出一个提示对话框，引导用户先制作封面。

## 实现文件

### 1. 后端 API（已存在）
- **文件**: `web/api/cover_check_api.py`
- **接口**: `GET /api/project/<title>/check-cover`
- **返回**: `{ "has_cover": true/false, "cover_path": "...", "checked_paths": [...] }`

### 2. 前端页面
- **文件**: `web/templates/pages/v2/fanqie-upload-v2.html`
- **修改位置**: 
  - `startUploadWithConfig()` 函数 - 添加上传前封面检查
  - 新增 `checkProjectCover()` 函数 - 调用后端 API 检查封面
  - 新增 `showFanqieCoverMissingDialog()` 函数 - 显示封面缺失提示对话框
  - 新增 `startUploadWithConfigSkipCoverCheck()` 函数 - 跳过封面检查继续上传

## 用户交互流程

1. 用户选择项目并配置上传选项
2. 用户点击"开始上传"按钮
3. 系统调用 `checkProjectCover()` 检查封面
4. **如果封面存在**: 直接开始上传流程
5. **如果封面不存在**: 显示提示对话框，提供三个选项：
   - 🎨 **去制作封面** - 在新标签页打开封面制作工具
   - **继续上传（不推荐）** - 跳过封面检查继续上传
   - **取消** - 关闭对话框，不上传

## 对话框样式

- 背景: 半透明黑色遮罩 + 模糊效果
- 图标: 🖼️ 封面图标
- 标题: "缺少封面"
- 消息: "小说《{title}》需要封面才能上传。"
- 按钮:
  - 主按钮: 去制作封面（渐变紫色）
  - 次要按钮: 继续上传（边框样式）
  - 取消按钮: 取消（文字按钮）

## 国际化支持

对话框支持国际化，使用 `getFanqieText()` 函数获取翻译：
- `fanqie.coverDialog.title` - 对话框标题
- `fanqie.coverDialog.message` - 提示消息
- `fanqie.coverDialog.createCover` - "去制作封面"按钮
- `fanqie.coverDialog.continueAnyway` - "继续上传"按钮
- `fanqie.coverDialog.cancel` - "取消"按钮

如果 I18N 未加载，使用默认中文文本。

## 测试方法

1. 进入番茄上传页面
2. 选择一个**没有封面**的项目
3. 配置上传选项
4. 点击"开始上传"按钮
5. 应该弹出封面缺失提示对话框
6. 测试三个按钮功能是否正常

## 相关依赖

- 依赖已实现的 `cover_check_api.py` 接口
- 依赖封面制作页面 `/cover-maker`
- 依赖 i18n 系统（可选，有默认值）
