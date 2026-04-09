# 静态文件目录

## ⚠️ 重要提示

**本目录是唯一的静态文件目录**，位于项目根目录下。

Flask 配置：
```python
static_folder = os.path.join(BASE_DIR, 'static')
```

## 目录结构

```
static/
├── css/          # 样式文件
├── js/           # JavaScript 文件
└── generated_videos/  # 生成的视频文件
```

## 禁止操作

❌ **不要在 web/ 目录下创建 static 文件夹**  
❌ **不要分散静态文件到多个位置**

## 如果需要在模板中引用

使用 Flask 的 `url_for` 函数：
```html
<script src="{{ url_for('static', filename='js/dialog.js') }}"></script>
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

或直接路径（不推荐）：
```html
<script src="/static/js/dialog.js"></script>
```
