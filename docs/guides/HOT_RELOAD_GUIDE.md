# Flask 热重载功能说明

## 问题背景

之前每次修改代码后，都需要手动重启服务器才能看到效果，这非常影响开发效率。

## 解决方案

已启用 Flask 的自动重载功能（Hot Reload），现在修改代码后会自动生效，无需手动重启。

## 修改内容

在 [`web/web_server_refactored.py`](../../web/web_server_refactored.py) 中：

```python
# 之前（禁用热重载）
app.run(
    host=FlaskConfig.HOST,
    port=FlaskConfig.PORT,
    debug=FlaskConfig.DEBUG,
    use_reloader=False  # ❌ 禁用自动重载
)

# 现在（启用热重载）
app.run(
    host=FlaskConfig.HOST,
    port=FlaskConfig.PORT,
    debug=FlaskConfig.DEBUG,
    use_reloader=True  # ✅ 启用自动重载
)
```

## 工作原理

Flask 的热重载功能使用 **Werkzeug** 的文件监控机制：

1. **监控文件变化**：Flask 会监控项目中的所有 `.py` 文件
2. **检测到修改**：当你保存修改后的 Python 文件时
3. **自动重启**：Flask 会自动重启服务器进程
4. **加载新代码**：重启后会加载最新的代码

## 使用方法

### 1. 启动服务器

```bash
# 使用你的启动脚本
python web/web_server_refactored.py

# 或者
python scripts/start_web_server.py
```

### 2. 修改代码

- 编辑任何 Python 文件（路由、API、服务等）
- 保存文件（Ctrl+S）

### 3. 查看效果

- 终端会显示检测到文件变化
- 服务器自动重启
- 刷新浏览器即可看到修改效果

## 控制台输出示例

当你修改代码后，会看到类似这样的输出：

```
 * Detected change in 'web/web_server_refactored.py', reloading
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
 * Running on http://0.0.0.0:5000
```

## 注意事项

### ✅ 优点

1. **提高开发效率**：无需手动重启服务器
2. **快速迭代**：修改代码后立即看到效果
3. **减少错误**：避免忘记重启导致的困惑

### ⚠️ 限制

1. **仅限 Python 文件**：
   - `.py` 文件的修改会自动重载
   - 模板文件（`.html`）的修改通常也会自动更新
   - 静态文件（`.css`, `.js`）的修改刷新浏览器即可

2. **重载延迟**：
   - 小项目：通常 1-2 秒
   - 大项目：可能需要 5-10 秒

3. **开发环境专用**：
   - 热重载仅用于开发环境
   - 生产环境应该使用 `use_reloader=False`

4. **全局变量状态**：
   - 重载会清除全局变量的状态
   - 如果有重要的全局状态，需要考虑持久化

## 配置选项

### 在 `web/web_config.py` 中调整

```python
class FlaskConfig:
    """Flask应用配置"""
    SECRET_KEY = 'your-secret-key-here'
    DEBUG = True          # 必须为 True 才能使用热重载
    HOST = '0.0.0.0'
    PORT = 5000
```

- `DEBUG = True`：启用调试模式和热重载
- `DEBUG = False`：禁用热重载（生产环境）

### 完全禁用热重载

如果需要完全禁用热重载（不推荐）：

```python
app.run(
    host=FlaskConfig.HOST,
    port=FlaskConfig.PORT,
    debug=False,           # 禁用调试模式
    use_reloader=False     # 禁用重载器
)
```

## 常见问题

### Q: 为什么有时候修改了代码没有自动重载？

A: 可能的原因：
1. 文件保存后没有被 Flask 检测到（尝试再次保存）
2. 修改的是配置文件（某些配置需要完全重启）
3. Python 文件有语法错误（检查终端的错误信息）

### Q: 热重载会导致内存泄漏吗？

A: 不会。Flask 的重载器会完全终止旧进程并启动新进程，不会有内存残留。

### Q: 如何判断服务器是否支持热重载？

A: 启动服务器时，如果看到以下信息，说明热重载已启用：
```
 * Debug mode: on
 * Running on http://0.0.0.0:5000
 * Restarting with stat
```

### Q: 修改模板文件需要重启吗？

A: 不需要。Flask 默认会自动重新加载模板文件。只需刷新浏览器即可。

## 生产环境部署

在生产环境中，应该：

1. 设置 `DEBUG = False`
2. 使用专业的 WSGI 服务器（如 Gunicorn、uWSGI）
3. 不要使用 Flask 内置的开发服务器

```python
# 生产环境配置示例
class FlaskConfig:
    DEBUG = False           # 禁用调试模式
    HOST = '0.0.0.0'
    PORT = 5000
```

## 总结

✅ **已启用热重载**，现在你可以：
- 修改代码后自动生效
- 无需手动重启服务器
- 提高开发效率

享受更流畅的开发体验！🚀