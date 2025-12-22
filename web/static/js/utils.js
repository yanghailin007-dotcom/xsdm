// ==================== 通用工具函数 ====================

// 显示状态消息
function showStatusMessage(message, type) {
    const msgElement = document.getElementById('status-message');
    if (!msgElement) {
        console.warn('找不到状态消息元素');
        return;
    }
    
    msgElement.className = `status-message ${type}`;
    msgElement.textContent = message;
    msgElement.style.display = 'block';
    
    // 5秒后自动隐藏成功消息
    if (type === 'success') {
        setTimeout(() => {
            msgElement.style.display = 'none';
        }, 5000);
    }
}

// 检查登录状态
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            showLoginReminder();
        }
    } catch (error) {
        showLoginReminder();
    }
}

// 显示登录提醒
function showLoginReminder() {
    const msg = document.getElementById('status-message');
    if (msg && !msg.classList.contains('success')) {
        msg.className = 'status-message error';
        msg.textContent = '⚠️ 请先登录后再使用生成功能';
        msg.style.display = 'block';
    }
}

// 退出登录函数
function logout() {
    if (confirm('确定要退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// 页面卸载时清理定时器
function setupPageCleanup() {
    window.addEventListener('beforeunload', function() {
        if (progressInterval) {
            clearInterval(progressInterval);
        }
    });
}

// 获取默认阶段名称
function getDefaultStageName(stageKey) {
    const defaultNames = {
        'opening': '开篇阶段',
        'development': '发展阶段',
        'conflict': '高潮阶段',
        'ending': '结局阶段'
    };
    return defaultNames[stageKey] || stageKey;
}

// 文本截取辅助函数
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
}

// 安全的JSON解析
function safeJSONParse(str, defaultValue = null) {
    try {
        return JSON.parse(str);
    } catch (error) {
        console.warn('JSON解析失败:', error);
        return defaultValue;
    }
}

// 防抖函数
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 节流函数
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化日期
function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    return new Date(date).toLocaleDateString('zh-CN', finalOptions);
}

// 复制到剪贴板
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showStatusMessage('✅ 已复制到剪贴板', 'success');
    } catch (err) {
        console.error('复制失败:', err);
        // 降级方案
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            showStatusMessage('✅ 已复制到剪贴板', 'success');
        } catch (err) {
            console.error('降级复制也失败:', err);
            showStatusMessage('❌ 复制失败', 'error');
        }
        document.body.removeChild(textArea);
    }
}

// 生成随机ID
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// 深度克隆对象
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    if (obj instanceof Date) return new Date(obj.getTime());
    if (obj instanceof Array) return obj.map(item => deepClone(item));
    if (typeof obj === 'object') {
        const clonedObj = {};
        for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
                clonedObj[key] = deepClone(obj[key]);
            }
        }
        return clonedObj;
    }
}

// 等待指定时间
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 检查元素是否在视口中
function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

// 平滑滚动到元素
function smoothScrollTo(element, offset = 0) {
    const targetPosition = element.offsetTop - offset;
    window.scrollTo({
        top: targetPosition,
        behavior: 'smooth'
    });
}

// 获取URL参数
function getUrlParam(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

// 设置URL参数
function setUrlParam(name, value) {
    const url = new URL(window.location);
    url.searchParams.set(name, value);
    window.history.replaceState({}, '', url);
}

// 移除URL参数
function removeUrlParam(name) {
    const url = new URL(window.location);
    url.searchParams.delete(name);
    window.history.replaceState({}, '', url);
}

// 验证邮箱格式
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// 验证手机号格式（中国）
function isValidPhone(phone) {
    const phoneRegex = /^1[3-9]\d{9}$/;
    return phoneRegex.test(phone);
}

// 本地存储封装
const storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('localStorage存储失败:', error);
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('localStorage读取失败:', error);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            console.error('localStorage删除失败:', error);
        }
    },
    
    clear: function() {
        try {
            localStorage.clear();
        } catch (error) {
            console.error('localStorage清空失败:', error);
        }
    }
};

// 会话存储封装
const sessionStorage = {
    set: function(key, value) {
        try {
            window.sessionStorage.setItem(key, JSON.stringify(value));
        } catch (error) {
            console.error('sessionStorage存储失败:', error);
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = window.sessionStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (error) {
            console.error('sessionStorage读取失败:', error);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            window.sessionStorage.removeItem(key);
        } catch (error) {
            console.error('sessionStorage删除失败:', error);
        }
    },
    
    clear: function() {
        try {
            window.sessionStorage.clear();
        } catch (error) {
            console.error('sessionStorage清空失败:', error);
        }
    }
};

// 导出函数供其他模块使用
window.utils = {
    showStatusMessage,
    checkLoginStatus,
    logout,
    setupPageCleanup,
    getDefaultStageName,
    truncateText,
    safeJSONParse,
    debounce,
    throttle,
    formatFileSize,
    formatDate,
    copyToClipboard,
    generateId,
    deepClone,
    sleep,
    isElementInViewport,
    smoothScrollTo,
    getUrlParam,
    setUrlParam,
    removeUrlParam,
    isValidEmail,
    isValidPhone,
    storage,
    sessionStorage
};