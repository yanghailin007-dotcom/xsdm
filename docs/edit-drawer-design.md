# 编辑设定抽屉 - V2 设计规范

## 设计参考
- **Notion** - 页面属性侧边栏
- **飞书文档** - 右侧配置面板
- **Linear** - 任务详情抽屉
- **Figma** - 右侧属性面板

## 核心改进

### 1. 布局变化
```
Before (弹窗):
┌─────────────────────────────────────┐
│                                     │
│    ┌─────────────────────────┐      │
│    │       白色弹窗          │      │  ← 遮挡所有内容
│    │   (内容被限制)          │      │
│    └─────────────────────────┘      │
│                                     │
└─────────────────────────────────────┘

After (抽屉):
┌──────────────────────────────────────┬─────────────┐
│                                      │             │
│   产物卡片列表 (半透明遮罩)           │   编辑抽屉   │  ← 滑出
│   (上下文可见，可操作)                │   (宽480px) │
│                                      │             │
└──────────────────────────────────────┴─────────────┘
```

### 2. 视觉规范

#### 遮罩层
```css
.drawer-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 999;
    transition: opacity 0.3s ease;
}
```

#### 抽屉面板
```css
.drawer-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 480px;              /* 固定宽度 */
    max-width: 90vw;           /* 移动端适配 */
    height: 100vh;
    background: var(--v2-bg-secondary, #111);
    border-left: 1px solid var(--v2-border-default, rgba(255,255,255,0.1));
    z-index: 1000;
    transform: translateX(100%);
    transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
}

.drawer-panel.visible {
    transform: translateX(0);
}
```

#### 头部区域
```css
.drawer-header {
    padding: 20px 24px;
    border-bottom: 1px solid var(--v2-border-default);
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: var(--v2-bg-elevated, #161616);
}

.drawer-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--v2-text-primary, #fafafa);
    display: flex;
    align-items: center;
    gap: 12px;
}

.drawer-icon {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, var(--v2-primary-500), var(--v2-primary-600));
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
}
```

#### 内容区域
```css
.drawer-body {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
}

.drawer-field {
    margin-bottom: 24px;
}

.drawer-label {
    display: block;
    font-size: 13px;
    font-weight: 500;
    color: var(--v2-text-secondary, #a1a1aa);
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.drawer-input {
    width: 100%;
    padding: 12px 16px;
    background: var(--v2-bg-tertiary, #1a1a1a);
    border: 1px solid var(--v2-border-default);
    border-radius: 10px;
    color: var(--v2-text-primary);
    font-size: 15px;
    transition: all 0.2s;
}

.drawer-input:focus {
    outline: none;
    border-color: var(--v2-primary-500);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.drawer-textarea {
    min-height: calc(100vh - 400px);  /* 自适应高度 */
    resize: vertical;
    font-family: inherit;
    line-height: 1.7;
}
```

#### 底部操作栏
```css
.drawer-footer {
    padding: 16px 24px;
    border-top: 1px solid var(--v2-border-default);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--v2-bg-elevated);
}

.drawer-char-count {
    font-size: 13px;
    color: var(--v2-text-tertiary);
}

.drawer-actions {
    display: flex;
    gap: 12px;
}
```

### 3. 交互细节

#### 动画曲线
```css
/* 抽屉滑入 - 使用 ease-out 让运动更自然 */
transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);

/* 遮罩淡出 */
transition: opacity 0.2s ease-out;
```

#### 手势支持（移动端）
```javascript
// 从右边缘向左滑动关闭
let touchStartX = 0;
drawer.addEventListener('touchstart', (e) => {
    touchStartX = e.touches[0].clientX;
});

drawer.addEventListener('touchmove', (e) => {
    const diff = touchStartX - e.touches[0].clientX;
    if (diff < -50) {  // 向右滑动超过50px
        closeDrawer();
    }
});
```

#### 键盘快捷键
- `Esc` - 关闭抽屉
- `Ctrl/Cmd + S` - 保存
- `Ctrl/Cmd + Enter` - 保存并关闭

### 4. 响应式设计

```css
/* 平板 */
@media (max-width: 768px) {
    .drawer-panel {
        width: 100vw;
        max-width: 100vw;
    }
}

/* 手机 */
@media (max-width: 480px) {
    .drawer-panel {
        border-radius: 16px 16px 0 0;  /* 底部圆角 */
        height: 90vh;
        top: auto;
        bottom: 0;
        transform: translateY(100%);   /* 从底部滑入 */
    }
    
    .drawer-panel.visible {
        transform: translateY(0);
    }
}
```

### 5. 完整的HTML结构

```html
<!-- 遮罩层 -->
<div class="drawer-overlay" onclick="closeDrawer()"></div>

<!-- 抽屉面板 -->
<div class="drawer-panel">
    <!-- 头部 -->
    <div class="drawer-header">
        <div class="drawer-title">
            <div class="drawer-icon">🌍</div>
            <div>
                <h3>编辑世界观设定</h3>
                <p style="margin: 4px 0 0; font-size: 13px; color: var(--v2-text-secondary);">
                    修改和完善世界观内容
                </p>
            </div>
        </div>
        <button class="drawer-close" onclick="closeDrawer()">
            <svg>...</svg>
        </button>
    </div>
    
    <!-- 内容 -->
    <div class="drawer-body">
        <div class="drawer-field">
            <label class="drawer-label">标题</label>
            <input type="text" class="drawer-input" value="...">
        </div>
        
        <div class="drawer-field">
            <label class="drawer-label">内容</label>
            <textarea class="drawer-input drawer-textarea">...</textarea>
        </div>
    </div>
    
    <!-- 底部 -->
    <div class="drawer-footer">
        <span class="drawer-char-count">1,234 字符</span>
        <div class="drawer-actions">
            <button class="btn-secondary" onclick="closeDrawer()">取消</button>
            <button class="btn-primary" onclick="saveEdit()">保存</button>
        </div>
    </div>
</div>
```

## 优势对比

| 维度 | 旧弹窗 | 新抽屉 |
|------|--------|--------|
| 视觉一致性 | ❌ 白色，与主题冲突 | ✅ 深色，统一风格 |
| 上下文保留 | ❌ 完全遮挡 | ✅ 半透明遮罩可见 |
| 编辑空间 | ❌ 限制在小窗口 | ✅ 半屏，沉浸式 |
| 移动端体验 | ❌ 难以适配 | ✅ 底部Sheet |
| 关闭操作 | ❌ 必须点击× | ✅ 点击遮罩/滑动/ESC |

## 实现建议

1. **渐进增强** - 先实现基础抽屉，再添加动画和手势
2. **焦点管理** - 打开抽屉时自动聚焦第一个输入框
3. **状态保持** - 抽屉关闭时保留未保存的内容（防止误关）
4. **无障碍** - 添加 aria 属性支持屏幕阅读器
