/**
 * 多账号管理器 - Token + LocalStorage 方案
 * 支持多账号切换、Token 自动刷新
 */
class MultiAccountManager {
    constructor() {
        this.STORAGE_KEY = 'xsdm_accounts_v1';
        this.CURRENT_KEY = 'xsdm_current_account_id';
        
        // 加载保存的账号
        this.accounts = this.loadAccounts();
        this.currentId = localStorage.getItem(this.CURRENT_KEY);
        
        // Token 刷新定时器
        this.refreshTimer = null;
        
        // 初始化时检查 Token 过期
        this.scheduleRefresh();
        
        console.log('[AccountManager] 初始化完成，账号数量:', this.accounts.length);
    }

    // ==================== 数据持久化 ====================
    
    loadAccounts() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            if (!data) return [];
            
            const accounts = JSON.parse(data);
            // 数据迁移：确保新字段存在
            return accounts.map(acc => ({
                needsRelogin: false,
                lastUsed: Date.now(),
                ...acc
            }));
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
