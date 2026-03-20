# 封面检查功能实现

## 功能描述

在项目管理页面，当用户点击"继续生成"或"查看内容"按钮时，如果项目缺少封面，会弹出一个提示对话框，引导用户先制作封面。

## 实现文件

### 1. 后端 API
- **文件**: `web/api/cover_check_api.py`
- **功能**: 提供 `/api/project/<title>/check-cover` 接口，检查项目封面是否存在
- **检查路径**:
  - `{project_dir}/cover.png`
  - `{project_dir}/cover.jpg`
  - `{project_dir}/images/cover.png`
  - `{project_dir}/images/cover.jpg`

### 2. 后端项目列表接口
- **文件**: `web/api/phase_generation_api.py`
- **修改**: 在 `/api/projects/with-phase-status` 接口返回的数据中添加了 `has_cover` 字段

### 3. 前端页面
- **文件**: `web/templates/pages/v2/project-management-v2.html`
- **修改**:
  - 在项目卡片上添加了封面缺失警告图标 ⚠️
  - 添加了 `viewProjectWithCoverCheck()` 和 `continueToPhaseTwoWithCoverCheck()` 函数
  - 添加了 `showCoverMissingDialog()` 函数显示封面缺失提示对话框

### 4. 服务器注册
- **文件**: `web/web_server_refactored.py`
- **修改**: 注册了 `cover_check_api` 蓝图

### 5. i18n 翻译
- **文件**: `static/js/i18n.js`
- **添加的翻译键**:
  - `projectMgmt.coverDialog.title`
  - `projectMgmt.coverDialog.message`
  - `projectMgmt.coverDialog.createCover`
  - `projectMgmt.coverDialog.continueAnyway`
  - `projectMgmt.coverDialog.cancel`

## 对话框功能

当用户尝试进入缺少封面的项目时，会显示一个对话框，提供三个选项：

1. **🎨 去制作封面** - 打开封面制作工具（在新标签页）
2. **继续（不推荐）** - 继续进入项目（不推荐）
3. **取消** - 关闭对话框

## 截图

封面缺失的项目会在按钮上显示 ⚠️ 警告图标，提示用户需要先制作封面。

## 测试方法

1. 进入项目管理页面
2. 找一个没有封面的项目（按钮上有 ⚠️ 图标）
3. 点击"继续生成"或"查看内容"按钮
4. 应该会弹出封面缺失提示对话框
