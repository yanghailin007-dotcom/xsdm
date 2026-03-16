/**
 * 多账号管理器 - Token + LocalStorage 方案
 * 支持多账号切换、Token 自动刷新
 * 🔥 关键：按用户隔离存储，避免多用户数据混淆
 */
class MultiAccountManager {
    constructor() {
        // 🔥 获取当前用户标识，用于隔离存储
        this.currentUser = this._getCurrentUserIdentifier();
        
        // 🔥 按用户隔离存储键名
        this.STORAGE_KEY = `xsdm_accounts_v1_${this.currentUser}`;
        this.CURRENT_KEY = `xsdm_current_account_id_${this.currentUser}`;
        
        // 🔥 首先检查并清除损坏的数据（从 v2 迁移到 v3）
        this.migrateFromV2();
        
        // 加载保存的账号
        this.accounts = this.loadAccounts();
        this.currentId = localStorage.getItem(this.CURRENT_KEY);
        
        // Token 刷新定时器
        this.refreshTimer = null;
        
        // 初始化时检查 Token 过期
        this.scheduleRefresh();
        
        // 🔥 检查是否有需要重新登录的账号
        this.checkNeedsRelogin();
        
        console.log('[AccountManager] 初始化完成，用户:', this.currentUser, '账号数量:', this.accounts.length);
    }
    
    /**
     * 🔥 获取当前用户标识，用于隔离存储
     */
    _getCurrentUserIdentifier() {
        // 尝试从 window.currentUser 获取
        if (typeof window !== 'undefined' && window.currentUser) {
            return window.currentUser.username || window.currentUser.id || 'guest';
        }
        // 尝试从页面中的用户数据获取
        const userMeta = document.querySelector('meta[name="current-user"]');
        if (userMeta) {
            return userMeta.content || 'guest';
        }
        // 兜底：使用 'guest'，但这样多用户仍会混淆
        // 建议后端在页面模板中注入当前用户信息
        return 'guest';
    }
    
    /**
     * 🔥 从 v2 迁移：检测并清除损坏的 token 数据
     * 🔥 同时处理从旧版（不分用户）到新版（按用户隔离）的迁移
     */
    migrateFromV2() {
        // 🔥 首先检查是否需要从旧版（不分用户）迁移到新版（按用户隔离）
        const oldKey = 'xsdm_accounts_v1';
        const oldCurrentKey = 'xsdm_current_account_id';
        
        // 如果当前使用的是新版键名，且旧版数据存在，则进行迁移
        if (this.STORAGE_KEY !== oldKey) {
            try {
                const oldData = localStorage.getItem(oldKey);
                const oldCurrentId = localStorage.getItem(oldCurrentKey);
                
                // 检查新版键名是否已经有数据
                const newDataExists = localStorage.getItem(this.STORAGE_KEY);
                
                if (oldData && !newDataExists) {
                    console.log('[AccountManager] 检测到旧版数据，开始迁移到用户隔离存储...');
                    localStorage.setItem(this.STORAGE_KEY, oldData);
                    if (oldCurrentId) {
                        localStorage.setItem(this.CURRENT_KEY, oldCurrentId);
                    }
                    console.log('[AccountManager] 数据迁移完成，用户:', this.currentUser);
                    
                    // 🔥 可选：清理旧数据（如果不希望保留）
                    // localStorage.removeItem(oldKey);
                    // localStorage.removeItem(oldCurrentKey);
                }
            } catch (e) {
                console.error('[AccountManager] 迁移旧数据失败:', e);
            }
        }
        
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (!data) return;
            
            // 🔥 检测是否包含损坏的 bytes 格式数据
            if (data.includes("b'") || data.includes('b"')) {
                console.warn('[AccountManager] 检测到损坏的 token 数据，执行清理...');
                
                const accounts = JSON.parse(data);
                const cleanedAccounts = accounts.map(acc => {
                    // 检测损坏的 token（Python bytes 格式 b'...'）
                    const accessCorrupted = acc.accessToken && 
                        (acc.accessToken.startsWith("b'") || acc.accessToken.startsWith('b"'));
                    const refreshCorrupted = acc.refreshToken && 
                        (acc.refreshToken.startsWith("b'") || acc.refreshToken.startsWith('b"'));
                    
                    if (accessCorrupted || refreshCorrupted) {
                        console.warn(`[AccountManager] 清理账号 ${acc.username} 的损坏 token`);
                        return {
                            ...acc,
                            accessToken: null,
                            refreshToken: null,
                            needsRelogin: true
                        };
                    }
                    return acc;
                });
                
                // 保存清理后的数据
                localStorage.setItem(this.STORAGE_KEY, JSON.stringify(cleanedAccounts));
                console.warn('[AccountManager] 已清除损坏的 token 数据，请重新登录');
                
                // 强制刷新页面以应用更改
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } catch (e) {
            console.error('[AccountManager] 迁移数据失败:', e);
            // 如果解析失败，清除所有数据
            localStorage.removeItem(this.STORAGE_KEY);
            localStorage.removeItem(this.CURRENT_KEY);
        }
    }
    
    /**
     * 🔥 检查是否有需要重新登录的账号，并显示提示
     */
    checkNeedsRelogin() {
        const needReloginAccounts = this.accounts.filter(acc => acc.needsRelogin);
        if (needReloginAccounts.length > 0) {
            console.warn('[AccountManager] 以下账号需要重新登录:', 
                needReloginAccounts.map(acc => acc.username).join(', '));
            
            // 显示提示（延迟执行，确保页面已加载）
            setTimeout(() => {
                this.showReloginNotification(needReloginAccounts);
            }, 2000);
        }
    }
    
    /**
     * 显示重新登录提示
     */
    showReloginNotification(accounts) {
        // 创建通知元素
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: white;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
            z-index: 9999;
            max-width: 320px;
            font-family: system-ui, -apple-system, sans-serif;
        `;
        
        const usernames = accounts.map(acc => acc.username).join(', ');
        notification.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 8px;">⚠️ 需要重新登录</div>
            <div style="font-size: 14px; opacity: 0.9; margin-bottom: 12px;">
                账号 <strong>${usernames}</strong> 的登录信息已过期，请重新登录
            </div>
            <button onclick="window.location.href='/login?mode=add-account'" 
                    style="background: white; color: #d97706; border: none; padding: 8px 16px; 
                           border-radius: 6px; cursor: pointer; font-weight: 500;">
                去登录 →
            </button>
        `;
        
        document.body.appendChild(notification);
        
        // 5秒后自动关闭
        setTimeout(() => {
            notification.remove();
        }, 10000);
    }

    // ==================== 数据持久化 ====================
    
    loadAccounts() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (!data) return [];
            
            const accounts = JSON.parse(data);
            // 数据迁移：确保新字段存在
            return accounts.map(acc => {
                // 🔥 修复：处理损坏的 token（Python bytes 格式 b'...'）
                let fixedAccessToken = acc.accessToken;
                let fixedRefreshToken = acc.refreshToken;
                
                if (fixedAccessToken && fixedAccessToken.startsWith("b'") && fixedAccessToken.endsWith("'")) {
                    console.warn('[AccountManager] 修复损坏的 accessToken');
                    fixedAccessToken = null; // 标记为需要重新登录
                }
                if (fixedRefreshToken && fixedRefreshToken.startsWith("b'") && fixedRefreshToken.endsWith("'")) {
                    console.warn('[AccountManager] 修复损坏的 refreshToken');
                    fixedRefreshToken = null;
                }
                
                return {
                    needsRelogin: !fixedAccessToken || !fixedRefreshToken, // 如果 token 损坏，标记需要重新登录
                    lastUsed: Date.now(),
                    ...acc,
                    accessToken: fixedAccessToken,
                    refreshToken: fixedRefreshToken
                };
            });
        } catch (e) {
            console.error('[AccountManager] 加载账号失败:', e);
            return [];
        }
    }

    save() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.accounts));
            localStorage.setItem(this.CURRENT_KEY, this.currentId || '');
        } catch (e) {
            console.error('[AccountManager] 保存账号失败:', e);
            // LocalStorage 满了，清理旧数据
            if (e.name === 'QuotaExceededError') {
                this.cleanupOldAccounts();
            }
        }
    }

    cleanupOldAccounts() {
        // 保留最近使用的 5 个账号
        this.accounts.sort((a, b) => (b.lastUsed || 0) - (a.lastUsed || 0));
        this.accounts = this.accounts.slice(0, 5);
        this.save();
    }

    // ==================== 账号管理 ====================

    /**
     * 添加新账号（登录成功后调用）
     * @param {Object} loginData - 登录接口返回的数据
     * @returns {Object} 账号对象
     */
    addAccount(loginData) {
        const { 
            user_id, 
            username, 
            access_token, 
            refresh_token, 
            expires_in,
            is_admin,
            points_balance,
            avatar 
        } = loginData;

        // 检查是否已存在
        const existingIndex = this.accounts.findIndex(a => a.userId === user_id);
        
        const account = {
            id: existingIndex >= 0 ? this.accounts[existingIndex].id : Date.now().toString(36),
            userId: user_id,
            username: username,
            accessToken: access_token,
            refreshToken: refresh_token,
            expiresAt: Date.now() + (expires_in * 1000),
            isAdmin: is_admin || false,
            points: points_balance || 0,
            avatar: avatar || `/static/images/avatar-default.png`,
            needsRelogin: false,
            lastUsed: Date.now(),
            addedAt: existingIndex >= 0 ? this.accounts[existingIndex].addedAt : new Date().toISOString()
        };

        if (existingIndex >= 0) {
            // 更新现有账号
            this.accounts[existingIndex] = account;
            console.log('[AccountManager] 更新账号:', username);
        } else {
            // 添加新账号
            this.accounts.push(account);
            console.log('[AccountManager] 添加账号:', username);
        }

        this.save();
        
        // 如果是新账号，自动切换
        if (existingIndex < 0) {
            this.switchAccount(account.id);
        }
        
        return account;
    }

    /**
     * 切换到指定账号
     * @param {string} accountId - 账号ID
     * @returns {Promise<boolean>} 是否切换成功
     */
    async switchAccount(accountId) {
        const account = this.accounts.find(a => a.id === accountId);
        if (!account) {
            console.warn('[AccountManager] 账号不存在:', accountId);
            return false;
        }

        try {
            // 调用后端 API 切换 session
            const response = await fetch('/api/auth/switch-account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: account.userId })
            });
            
            const data = await response.json();
            
            if (!data.success) {
                console.error('[AccountManager] 切换账户失败:', data.error);
                return false;
            }
            
            // 更新最后使用时间
            account.lastUsed = Date.now();
            account.points = data.points_balance || account.points;
            this.currentId = accountId;
            this.save();

            console.log('[AccountManager] 切换到账号:', account.username);
            
            // 触发全局事件
            window.dispatchEvent(new CustomEvent('account:switched', { 
                detail: { 
                    account: this.sanitizeAccount(account),
                    previousAccount: this.getCurrentAccount() 
                }
            }));

            // 重新调度 Token 刷新
            this.scheduleRefresh();
            
            return true;
        } catch (error) {
            console.error('[AccountManager] 切换账户请求失败:', error);
            return false;
        }
    }

    /**
     * 获取当前账号
     * @returns {Object|null}
     */
    getCurrentAccount() {
        if (!this.currentId) return null;
        return this.accounts.find(a => a.id === this.currentId) || null;
    }

    /**
     * 获取所有账号（用于 UI 展示）
     * @returns {Array}
     */
    getAllAccounts() {
        // 按最后使用时间排序
        return this.accounts
            .sort((a, b) => (b.lastUsed || 0) - (a.lastUsed || 0))
            .map(acc => this.sanitizeAccount(acc));
    }

    /**
     * 移除账号
     * @param {string} accountId 
     */
    removeAccount(accountId) {
        this.accounts = this.accounts.filter(a => a.id !== accountId);
        
        // 如果删除的是当前账号，切换到第一个
        if (this.currentId === accountId) {
            this.currentId = this.accounts.length > 0 ? this.accounts[0].id : null;
            if (this.currentId) {
                this.switchAccount(this.currentId);
            }
        }
        
        this.save();
        
        window.dispatchEvent(new CustomEvent('account:removed', { 
            detail: { accountId } 
        }));
    }

    // ==================== Token 管理 ====================

    /**
     * 获取当前有效的 Access Token
     * 如果即将过期，自动刷新
     * @returns {Promise<string>}
     */
    async getValidToken() {
        const account = this.getCurrentAccount();
        if (!account) {
            throw new Error('No account logged in');
        }

        // 检查是否需要刷新（5分钟缓冲）
        const needRefresh = Date.now() > (account.expiresAt - 5 * 60 * 1000);
        
        if (needRefresh || account.needsRelogin) {
            if (account.needsRelogin) {
                // 需要重新登录
                this.showReloginPrompt(account);
                throw new Error('Token expired, need relogin');
            }
            
            // 尝试刷新
            try {
                await this.refreshToken(account);
            } catch (e) {
                console.error('[AccountManager] Token 刷新失败:', e);
                account.needsRelogin = true;
                this.save();
                this.showReloginPrompt(account);
                throw e;
            }
        }

        return account.accessToken;
    }

    /**
     * 刷新 Token
     * @param {Object} account 
     */
    async refreshToken(account) {
        console.log('[AccountManager] 刷新 Token:', account.username);
        
        // 🔥 检查 refresh token 是否有效
        if (!account.refreshToken || account.refreshToken.startsWith("b'")) {
            console.error('[AccountManager] Refresh Token 格式错误，需要重新登录');
            account.needsRelogin = true;
            this.save();
            throw new Error('Token 格式错误，请重新登录');
        }
        
        const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: account.refreshToken })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error || 'Refresh failed');
        }

        const data = await response.json();
        
        // 更新账号信息
        account.accessToken = data.access_token;
        account.refreshToken = data.refresh_token || account.refreshToken;
        account.expiresAt = Date.now() + (data.expires_in * 1000);
        account.needsRelogin = false;
        
        this.save();
        
        window.dispatchEvent(new CustomEvent('account:token-refreshed', { 
            detail: { accountId: account.id } 
        }));
        
        return data;
    }

    /**
     * 调度 Token 刷新
     */
    scheduleRefresh() {
        // 清除旧的定时器
        if (this.refreshTimer) {
            clearTimeout(this.refreshTimer);
        }

        const account = this.getCurrentAccount();
        if (!account || account.needsRelogin) return;

        // 计算下次刷新时间（提前5分钟）
        const nextRefresh = account.expiresAt - Date.now() - 5 * 60 * 1000;
        
        if (nextRefresh > 0) {
            this.refreshTimer = setTimeout(() => {
                this.refreshToken(account).catch(console.error);
            }, nextRefresh);
            
            console.log('[AccountManager] 已调度 Token 刷新:', 
                new Date(Date.now() + nextRefresh).toLocaleTimeString());
        } else {
            // 已经过期或即将过期，立即刷新
            this.refreshToken(account).catch(console.error);
        }
    }

    // ==================== UI 辅助 ====================

    /**
     * 显示重新登录提示
     */
    showReloginPrompt(account) {
        window.dispatchEvent(new CustomEvent('account:need-relogin', { 
            detail: { 
                account: this.sanitizeAccount(account),
                message: `账号 ${account.username} 需要重新登录`
            }
        }));
    }

    /**
     * 清理敏感信息，用于 UI 展示
     */
    sanitizeAccount(account) {
        return {
            id: account.id,
            userId: account.userId,
            username: account.username,
            isAdmin: account.isAdmin,
            points: account.points,
            avatar: account.avatar,
            isCurrent: account.id === this.currentId,
            needsRelogin: account.needsRelogin || false,
            // 不返回 Token！
        };
    }

    /**
     * 更新账号信息（如余额变化）
     */
    updateAccountInfo(accountId, updates) {
        const account = this.accounts.find(a => a.id === accountId);
        if (account) {
            Object.assign(account, updates);
            this.save();
        }
    }

    /**
     * 同步当前账号的余额
     */
    async syncCurrentAccountPoints() {
        const account = this.getCurrentAccount();
        if (!account) return;

        try {
            const response = await fetch('/api/points/balance', {
                headers: {
                    'Authorization': `Bearer ${account.accessToken}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                if (data.success && data.data) {
                    this.updateAccountInfo(account.id, { 
                        points: data.data.balance 
                    });
                    
                    window.dispatchEvent(new CustomEvent('account:points-updated', {
                        detail: { accountId: account.id, points: data.data.balance }
                    }));
                }
            }
        } catch (e) {
            console.error('[AccountManager] 同步余额失败:', e);
        }
    }

    // ==================== 静态方法 ====================

    /**
     * 检查是否支持当前浏览器
     */
    static isSupported() {
        try {
            const test = '__storage_test__';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (e) {
            return false;
        }
    }
}

// 创建全局实例
window.accountManager = new MultiAccountManager();

// 兼容性导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = MultiAccountManager;
}
