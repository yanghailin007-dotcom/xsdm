# 多账号切换系统 - 快速设置指南

## 已完成的改动

### 后端改动
1. ✅ **JWT 认证模块** (`web/jwt_auth.py`)
   - Token 生成/验证
   - 兼容 Session 旧认证

2. ✅ **登录接口改造** (`web/routes/auth_routes.py`)
   - 返回 `access_token` 和 `refresh_token`
   - 新增 `/api/auth/refresh` 刷新接口
   - 新增 `/api/auth/verify` 验证接口

3. ✅ **API 装饰器更新** (`web/api/points_api.py`)
   - 支持从 Header 读取 JWT Token
   - 优先使用 `Authorization: Bearer <token>`

4. **依赖安装**
   ```bash
   pip install PyJWT
   ```

### 前端改动
1. ✅ **账号管理器** (`static/js/account-manager.js`)
2. ✅ **API 客户端** (`static/js/api-client.js`)
3. ✅ **账号切换 UI** (`web/templates/components/account-switcher.html`)

---

## 如何使用

### 1. 现有用户 - 无需改动
现有 Session 认证仍然有效，用户无需重新登录。

### 2. 添加新账号
用户登录时，返回的 Token 会自动保存到 LocalStorage：

```javascript
// 登录成功后，账号管理器自动保存
const loginResponse = await fetch('/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'xxx', password: 'xxx' })
});

const data = await loginResponse.json();
if (data.success) {
    // 自动保存到 AccountManager
    window.accountManager.addAccount(data);
}
```

### 3. 切换账号
```javascript
// 切换到另一个账号
window.accountManager.switchAccount(accountId);
// 页面自动刷新，加载新账号的数据
```

### 4. API 请求（自动带 Token）
```javascript
// 使用 apiClient，Token 自动附加
const result = await window.apiClient.get('/api/points/balance');

// 或使用 fetch 手动添加
const token = await window.accountManager.getValidToken();
fetch('/api/points/balance', {
    headers: { 'Authorization': `Bearer ${token}` }
});
```

---

## 在其他页面集成账号切换器

### 方法 1：引入组件（推荐）

在页面中添加：
```html
<!-- 在 <head> 中添加样式 -->
<style>
  {% include 'components/account-switcher.html' %}
</style>

<!-- 在导航栏位置添加 -->
<div class="navbar-right">
    {% include 'components/account-switcher.html' %}
</div>

<!-- 在页面底部添加脚本 -->
<script src="/static/js/account-manager.js"></script>
<script src="/static/js/api-client.js"></script>
```

### 方法 2：使用 iframe 或 AJAX 加载
```javascript
// 动态加载账号切换器
fetch('/components/account-switcher')
    .then(r => r.text())
    .then(html => {
        document.getElementById('account-switcher-container').innerHTML = html;
    });
```

---

## Token 过期处理

系统自动处理：
1. **Token 即将过期**（5分钟前）→ 自动刷新
2. **Token 已过期** → 显示重新登录提示
3. **Refresh Token 过期** → 移除账号，提示重新登录

---

## 调试信息

在浏览器 Console 查看：
```
[AccountManager] 初始化完成，账号数量: 2
[AccountManager] 切换到账号: user_a
[AccountManager] 刷新 Token: user_a
[ApiClient] Token 自动附加
```

---

## 安全注意事项

1. **XSS 风险**：Token 存储在 LocalStorage，需防范 XSS 攻击
   - 已添加：敏感操作二次验证
   - 建议：对重要操作（消费、删除）要求输入密码

2. **Token 撤销**：如需强制下线用户，需在服务端维护 Token 黑名单

3. **HTTPS**：生产环境必须使用 HTTPS，防止 Token 被中间人窃取

---

## 后续优化建议

1. **云端同步**：将账号列表加密同步到服务器，换设备可恢复
2. **扫码登录**：支持手机扫码快速添加账号
3. **生物识别**：移动端支持指纹/Face ID 解锁账号切换
4. **子账号系统**：主账号 + 多个子账号，共享余额

---

## 测试检查清单

- [ ] 登录后 Token 正确保存
- [ ] 多账号保存在 LocalStorage
- [ ] 切换账号后页面刷新
- [ ] Token 自动刷新（等待2小时或手动调短过期时间测试）
- [ ] Token 过期后显示重新登录提示
- [ ] API 请求自动携带正确 Token
- [ ] Session 兼容模式（旧用户）正常工作
