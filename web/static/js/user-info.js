/**
 * User Info Module
 * 用户信息显示和管理
 */

const UserInfo = {
    init() {
        this.loadUserInfo();
    },
    
    async loadUserInfo() {
        try {
            const response = await fetch('/api/user/info');
            if (response.ok) {
                const data = await response.json();
                this.displayUserInfo(data);
            }
        } catch (error) {
            console.warn('Failed to load user info:', error);
        }
    },
    
    displayUserInfo(user) {
        // 更新页面上的用户信息元素
        document.querySelectorAll('.user-name').forEach(el => {
            el.textContent = user.username || 'Guest';
        });
        
        document.querySelectorAll('.user-credits').forEach(el => {
            el.textContent = user.credits || 0;
        });
    },
    
    getCurrentUser() {
        const userJson = localStorage.getItem('currentUser');
        return userJson ? JSON.parse(userJson) : null;
    },
    
    setCurrentUser(user) {
        localStorage.setItem('currentUser', JSON.stringify(user));
    },
    
    clearCurrentUser() {
        localStorage.removeItem('currentUser');
    }
};

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    UserInfo.init();
});
