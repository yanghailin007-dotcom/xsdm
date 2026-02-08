/**
 * 用户信息管理 - 用户头像下拉菜单
 * 在所有页面加载时显示当前登录用户头像和菜单
 */

// 获取当前用户信息
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/current-user');
        const data = await response.json();
        
        const username = data.success ? data.username : '访客';
        
        // 更新所有用户名显示元素
        const usernameElements = document.querySelectorAll('#usernameText, .username-text');
        usernameElements.forEach(el => {
            el.textContent = username;
        });
        
        // 更新下拉菜单中的用户名
        const dropdownUsername = document.getElementById('dropdownUsername');
        if (dropdownUsername) {
            dropdownUsername.textContent = username;
        }
        
        // 更新头像文字（首字母）
        const avatarText = document.getElementById('avatarText');
        if (avatarText) {
            avatarText.textContent = username.charAt(0).toUpperCase();
        }
        
        // 更新旧版导航用户名
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
        
        const avatarText = document.getElementById('avatarText');
        if (avatarText) {
            avatarText.textContent = '访';
        }
    }
}

// 切换用户下拉菜单
function toggleUserMenu(event) {
    if (event) {
        event.stopPropagation();
    }
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// 关闭用户下拉菜单
function closeUserMenu() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.remove('active');
    }
}

// 点击外部关闭下拉菜单
document.addEventListener('click', function(event) {
    const userMenu = document.querySelector('.user-menu');
    if (userMenu && !userMenu.contains(event.target)) {
        closeUserMenu();
    }
});

// 页面加载时自动获取
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadCurrentUser);
} else {
    loadCurrentUser();
}

// 导出函数供全局使用
window.toggleUserMenu = toggleUserMenu;
window.closeUserMenu = closeUserMenu;
