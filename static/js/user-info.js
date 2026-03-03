/**
 * 用户信息管理 - 用户头像下拉菜单
 * 在所有页面加载时显示当前登录用户头像和菜单
 */

// 默认头像配置
const DEFAULT_AVATAR = {
    // 使用渐变色背景 + 首字母作为默认头像
    type: 'gradient', // 'gradient' | 'image'
    // 如果要使用图片，请设置 type 为 'image' 并配置 url
    // url: 'https://example.com/default-avatar.png'
    gradients: [
        'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)', // 紫罗兰
        'linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%)', // 青蓝色
        'linear-gradient(135deg, #ec4899 0%, #f97316 100%)', // 粉橙色
        'linear-gradient(135deg, #10b981 0%, #3b82f6 100%)', // 绿蓝色
        'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)', // 橙红色
    ]
};

// 根据用户名生成固定的渐变色
function getGradientForUsername(username) {
    const index = username.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return DEFAULT_AVATAR.gradients[index % DEFAULT_AVATAR.gradients.length];
}

// 获取当前用户信息
async function loadCurrentUser() {
    try {
        const response = await fetch('/api/current-user');
        const data = await response.json();
        
        const username = data.success ? data.username : '访客';
        const avatarUrl = data.success ? data.avatar_url : null;
        
        // 同步设置到引导系统（如果存在）
        if (data.success && typeof GuideSystem !== 'undefined') {
            GuideSystem.setUser({ username: data.username, id: data.user_id });
        }
        
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
        
        // 更新头像
        const avatarElements = document.querySelectorAll('.user-avatar');
        avatarElements.forEach(avatar => {
            // 清除现有内容
            avatar.innerHTML = '';
            
            if (avatarUrl) {
                // 使用用户设置的头像图片
                const img = document.createElement('img');
                img.src = avatarUrl;
                img.alt = username;
                img.onerror = () => {
                    // 图片加载失败时回退到首字母
                    avatar.innerHTML = `<span class="avatar-text">${username.charAt(0).toUpperCase()}</span>`;
                    avatar.style.background = getGradientForUsername(username);
                };
                avatar.appendChild(img);
                avatar.style.background = 'transparent';
            } else {
                // 使用默认头像（渐变色 + 首字母）
                const span = document.createElement('span');
                span.className = 'avatar-text';
                span.textContent = username.charAt(0).toUpperCase();
                avatar.appendChild(span);
                avatar.style.background = getGradientForUsername(username);
            }
        });
        
        // 更新旧版导航用户名
        const navUsername = document.getElementById('navUsername');
        if (navUsername && !navUsername.querySelector('#usernameText')) {
            navUsername.textContent = '👤 ' + username;
        }
        
    } catch (error) {
        console.error('获取用户信息失败:', error);
        const username = '访客';
        
        const usernameElements = document.querySelectorAll('#usernameText, .username-text');
        usernameElements.forEach(el => {
            el.textContent = username;
        });
        
        // 错误时使用默认头像
        const avatarElements = document.querySelectorAll('.user-avatar');
        avatarElements.forEach(avatar => {
            avatar.innerHTML = `<span class="avatar-text">访</span>`;
            avatar.style.background = DEFAULT_AVATAR.gradients[0];
        });
    }
}

// 切换用户下拉菜单
function toggleUserMenu(event) {
    if (event) {
        event.stopPropagation();
    }
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('active');
    }
}

// 关闭用户下拉菜单
function closeUserMenu() {
    const dropdown = document.getElementById('user-dropdown');
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
window.DEFAULT_AVATAR = DEFAULT_AVATAR;

// ==================== 点数系统功能 ====================

// 加载用户点数
async function loadUserPoints() {
    try {
        const response = await fetch('/api/points/balance');
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                const pointsDisplay = document.getElementById('dropdownPoints');
                if (pointsDisplay) {
                    pointsDisplay.innerHTML = `💰 ${result.data.balance} 点`;
                }
            }
        }
    } catch (error) {
        console.error('加载点数失败:', error);
        const pointsDisplay = document.getElementById('dropdownPoints');
        if (pointsDisplay) {
            pointsDisplay.innerHTML = '💰 --';
        }
    }
}

// 检查签到状态
async function checkCheckinStatus() {
    try {
        const response = await fetch('/api/points/checkin/status');
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                const checkinBtn = document.getElementById('checkinBtn');
                
                if (checkinBtn) {
                    if (result.data.can_checkin) {
                        checkinBtn.style.opacity = '1';
                        checkinBtn.style.cursor = 'pointer';
                        checkinBtn.innerHTML = result.data.streak > 0 
                            ? `📅 签到 (+连续${result.data.streak}天)` 
                            : '📅 签到 (+10点)';
                    } else {
                        checkinBtn.style.opacity = '0.5';
                        checkinBtn.style.cursor = 'not-allowed';
                        checkinBtn.innerHTML = `✅ 已签到 (连续${result.data.streak}天)`;
                        checkinBtn.onclick = (e) => {
                            e.stopPropagation();
                            alert('今天已经签到过了，明天再来吧！');
                        };
                    }
                }
            }
        }
    } catch (error) {
        console.error('检查签到状态失败:', error);
    }
}

// 页面加载时也加载点数
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        loadCurrentUser();
        setTimeout(() => {
            loadUserPoints();
            checkCheckinStatus();
        }, 100);
    });
} else {
    loadCurrentUser();
    setTimeout(() => {
        loadUserPoints();
        checkCheckinStatus();
    }, 100);
}
