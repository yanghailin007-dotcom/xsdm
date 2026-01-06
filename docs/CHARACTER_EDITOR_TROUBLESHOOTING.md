# 角色编辑器JSON驱动系统 - 问题排查指南

## 🔍 问题现象

从第二阶段页面进入角色设计界面后，UI没有发生变化。

## 📋 排查步骤

### 步骤1: 清除浏览器缓存

1. **Chrome/Edge**: 
   - 按 `Ctrl + Shift + Delete` 打开清除浏览数据对话框
   - 选择"缓存的图片和文件"
   - 时间范围选择"全部时间"
   - 点击"清除数据"

2. **Firefox**:
   - 按 `Ctrl + Shift + Delete`
   - 选择"缓存"
   - 时间范围"全部"
   - 点击"立即清除"

3. **强制刷新**:
   - Windows: `Ctrl + F5`
   - Mac: `Cmd + Shift + R`

### 步骤2: 检查文件是否正确加载

打开浏览器开发者工具（F12），检查：

#### 检查1: Console 控制台

```javascript
// 在控制台输入以下命令检查

// 1. 检查新函数是否存在
console.log('generateFormFromJSON:', typeof generateFormFromJSON);
console.log('collectDataFromForm:', typeof collectDataFromForm);

// 应该都输出 "function"

// 2. 检查字段定义
console.log('FIELD_DEFINITIONS:', typeof FIELD_DEFINITIONS);
console.log('CATEGORY_CONFIG:', typeof CATEGORY_CONFIG);

// 应该都输出 "object"

// 3. 手动测试表单生成
if (typeof generateFormFromJSON === 'function') {
    const testChar = {
        name: '测试角色',
        role: '主角',
        core_personality: '勇敢'
    };
    
    const form = generateFormFromJSON(testChar);
    console.log('生成的表单HTML:', form.innerHTML.substring(0, 200) + '...');
}
```

#### 检查2: Network 网络标签

在Network标签中查找：
- `character-editor-json-based.js` - 状态应该是200
- `character-editor-json-based.css` - 状态应该是200

如果看到404错误，说明文件路径不正确。

### 步骤3: 验证集成是否生效

#### 在角色编辑器打开时，检查控制台输出

应该看到类似的日志：
```
🎯 开始打开角色编辑器
✅ 使用JSON驱动表单生成器
✅ 动态表单生成完成
```

如果看到：
```
⚠️ 使用旧版表单生成方式
```

说明新的系统没有生效。

## 🛠️ 修复方案

### 方案1: 确保文件加载顺序

修改 [`phase-two-generation.html`](web/templates/phase-two-generation.html:375) 的脚本加载顺序：

```html
<!-- 确保这个顺序 -->
<script src="/static/js/character-editor-json-based.js"></script>  <!-- 先加载新系统 -->
<script src="/static/js/character-editor.js"></script>                     <!-- 再加载编辑器 -->
```

### 方案2: 强制使用新系统

在 [`character-editor.js`](web/static/js/character-editor.js:677) 中，修改 [`populateCharacterForm`](web/static/js/character-editor.js:677) 函数：

```javascript
function populateCharacterForm(character) {
    const container = document.getElementById('dynamic-form-sections');
    if (!container) {
        console.error('❌ 找不到dynamic-form-sections容器');
        return;
    }
    
    // 清空容器
    container.innerHTML = '';
    
    // 强制使用新的JSON驱动表单生成器
    console.log('🎨 使用JSON驱动表单生成器（强制模式）');
    
    const form = generateFormFromJSON(character);
    container.appendChild(form);
    
    // 设置图标和颜色
    if (character.icon) selectCharIcon(character.icon);
    if (character.color) selectCharColor(character.color);
    
    console.log('✅ 动态表单生成完成');
}
```

### 方案3: 使用测试页面验证

访问测试页面：

```
http://localhost:5000/test_character_editor.html
```

如果测试页面可以正常显示新的表单，说明：
- ✅ 核心功能正常
- ❌ 集成有问题

## 🔍 深入调试

### 检查点1: 打开角色编辑器时的日志

在浏览器控制台中查找：

**期望看到的日志**：
```javascript
🎯 开始打开角色编辑器
✅ 使用JSON驱动表单生成器
🎨 使用JSON驱动表单生成器（强制模式）
✅ 动态表单生成完成
```

**如果看到旧版本日志**：
```javascript
⚠️ 使用旧版表单生成方式
```

说明代码没有正确执行到新的逻辑。

### 检查点2: 表单生成的HTML

在角色编辑器打开后，在控制台输入：

```javascript
// 检查生成的表单结构
const formSections = document.querySelectorAll('.form-section');
console.log('表单区块数量:', formSections.length);

// 检查是否有新的分类区块
const categories = document.querySelectorAll('[data-category]');
console.log('分类区块数量:', categories.length);

// 检查具体区块
categories.forEach(cat => {
    console.log('分类名称:', cat.dataset.category);
    console.log('区块标题:', cat.querySelector('.section-header h4')?.textContent);
});
```

期望看到8个分类：
- basic (基本信息)
- personality (核心性格)
- appearance (生活特征)
- background (背景故事)
- faction (势力关系)
- abilities (能力状态)
- narrative (叙事作用)
- other (其他信息)

### 检查点3: 字段是否正确生成

```javascript
// 检查所有字段
const allFields = document.querySelectorAll('[data-field-key]');
console.log('字段总数:', allFields.length);

// 列出所有字段
allFields.forEach(field => {
    console.log('字段:', field.dataset.fieldKey, '标签:', field.previousElementSibling?.textContent);
});
```

## 🎯 快速修复

### 立即生效的方法

1. **重启Web服务器**
```bash
# 停止当前服务器（Ctrl+C）
# 重新启动
python web/web_server_refactored.py
```

2. **强制刷新页面**
   - Windows: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. **清除所有缓存**
   - Chrome设置 > 隐私和安全 > 清除浏览数据
   - 勾选"所有时间范围"
   - 点击"清除数据"

## 📞 需要更多信息

如果以上方法都无法解决问题，请提供：

1. **浏览器控制台的完整日志**
2. **Network标签的截图**（显示JS/CSS文件加载情况）
3. **实际看到的UI截图**
4. **打开角色编辑器时的完整控制台输出**

这些信息将帮助我准确定位问题所在。

## 🔄 回退方案

如果新系统无法正常工作，可以临时使用旧版本：

1. 重命名 [`character-editor.js`](web/static/js/character-editor.js) 为 `character-editor-new.js`
2. 保留旧版本的 [`character-editor.js`](web/static/js/character-editor.js:1) 
3. 在HTML中引入新文件：
   ```html
   <script src="/static/js/character-editor-new.js"></script>
   ```

## 📝 验证成功的标志

当系统正常工作时，您应该看到：

1. **清晰的分类区块** - 每个分类有图标和标题
2. **可折叠功能** - 点击分类标题可以折叠/展开
3. **更多字段** - 比旧版本有更多的输入字段
4. **嵌套字段支持** - 可以看到 `motivation.inner_drive` 这样的嵌套字段

---

**最后更新**: 2026-01-05  
**状态**: 等待用户反馈