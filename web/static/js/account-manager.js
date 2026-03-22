/**
 * Account Manager Module
 * 账户管理相关功能
 */

const AccountManager = {
    init() {
        this.setupEventListeners();
    },
    
    setupEventListeners() {
        // 账户相关事件监听
        document.addEventListener('userLoggedIn', (e) => {
            console.log('[AccountManager] User logged in:', e.detail);
        });
        
        document.addEventListener('userLoggedOut', () => {
            console.log('[AccountManager] User logged out');
        });
    },
    
    async logout() {
        try {
            const response = await fetch('/api/logout', { method: 'POST' });
            if (response.ok) {
                localStorage.removeItem('currentUser');
                window.location.href = '/';
            }
        } catch (error) {
            console.error('[AccountManager] Logout failed:', error);
        }
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    AccountManager.init();
});
