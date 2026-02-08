/**
 * 用户信息管理
 * 在所有页面加载时显示当前登录用户名
 */

// 获取当前用户信息
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/current-user');
        const data = await response.json();
        
        const usernameElements = document.querySelectorAll('#usernameText, .username-text');
        const username = data.success ? data.username : '访客';
        
        usernameElements.forEach(el => {
            el.textContent = username;
        });
        
        // 也更新单个元素
        const navUsername = document.getElementById('navUsername');
        if (navUsername && !navUsername.querySelector('#usernameText')) {
            navUsername.textContent = '👤 ' + username;
        }
        
    } catch (error) {
        console.error('获取用户信息失败:', error);
        const usernameElements = document.querySelectorAll('#usernameText, .username-text');
        usernameElements.forEach(el => {
            el.textContent = '访客';
        });
    }
}

// 页面加载时自动获取
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadCurrentUser);
} else {
    loadCurrentUser();
}
