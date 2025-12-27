# 番茄章节发布"确认发布"按钮超时修复

## 问题描述

在发布章节时出现以下错误：

1. **"确认发布"按钮点击超时**
   - 点击"下一步"后，"确认发布"按钮还未加载完成就尝试点击
   - 错误：`Locator.scroll_into_view_if_needed: Timeout 5000ms exceeded`

2. **page对象变成None**
   - 错误：`'NoneType' object has no attribute 'wait_for_load_state'`
   - 错误：`'NoneType' object has no attribute 'close'`

3. **后续操作失败**
   - 无法找到小说
   - 发布流程中断

## 根本原因

1. **页面加载时序问题**
   - 点击"下一步"后，只等待0.5秒就尝试点击"确认发布"
   - 实际页面需要更长时间加载

2. **缺少None检查**
   - `click_create_chapter_button_by_novel_title`可能返回`None`
   - 代码直接使用`current_page`而没有检查是否为`None`

## 修复方案

### 1. 增加页面加载等待时间

**文件**: `Chrome/automation/legacy/chapter_publisher.py:113-116`

```python
# 点击下一步
if not safe_click(current_page.get_by_role("button", name="下一步"), "下一步按钮", retries=2):
    current_page.close()
    return 1

# 增加等待时间，让页面完全加载
print("等待页面加载完成...")
time.sleep(2)
```

**修改**: 将等待时间从0.5秒增加到2秒

### 2. 增加"确认发布"按钮等待逻辑

**文件**: `Chrome/automation/legacy/chapter_publisher.py:167-177`

```python
# 确认发布 - 增加等待时间和重试次数
print("准备点击确认发布按钮...")

# 先等待按钮出现
try:
    publish_button = current_page.get_by_role("button", name="确认发布")
    publish_button.wait_for(state="visible", timeout=10000)
    print("✓ 确认发布按钮已出现")
except Exception as e:
    print(f"⚠️ 等待确认发布按钮超时: {e}")

if safe_click(current_page.get_by_role("button", name="确认发布"), "确认发布按钮", retries=3):
```

**修改**: 
- 添加了`wait_for(state="visible", timeout=10000)`显式等待按钮出现
- 将重试次数从2次增加到3次

### 3. 添加None检查和错误处理

**文件**: `Chrome/automation/legacy/chapter_publisher.py:53-72`

```python
current_page = click_create_chapter_button_by_novel_title(target_page, expected_book_title)

# 检查是否成功获取到新页面
if current_page is None:
    print("❌ 无法获取章节编辑页面，可能的原因：")
    print("   1. 小说《{}》未找到".format(expected_book_title))
    print("   2. 小说没有'创建章节'按钮（可能状态不是'连载中'）")
    print("   3. 浏览器页面已关闭或导航失败")
    return 2  # 返回2表示需要重新导航

try:
    # 等待页面加载
    try:
        current_page.wait_for_load_state("networkidle", timeout=15000)
    except Exception as e:
        print(f"⚠️ 页面加载超时: {e}，继续执行...")
    
    time.sleep(2)
```

**修改**:
- 添加了`current_page is None`检查
- 提供详细的错误信息帮助调试
- 增加了`networkidle`等待超时时间到15秒

## 测试建议

1. **测试场景**: 发布包含中文字符的小说章节
2. **预期结果**: 
   - 不再出现"确认发布"按钮超时
   - page对象正确传递
   - 发布流程顺利完成

## 相关文件

- `Chrome/automation/legacy/chapter_publisher.py` - 章节发布逻辑
- `Chrome/automation/legacy/novel_manager.py` - 小说导航逻辑
- `Chrome/automation/legacy/utils.py` - 工具函数

## 注意事项

1. 如果仍然遇到超时，可能需要进一步增加等待时间
2. 确保浏览器已手动启动并登录番茄小说网站
3. 检查小说状态是否为"连载中"
4. 检查网络连接是否稳定

## 修复日期

2025-12-25