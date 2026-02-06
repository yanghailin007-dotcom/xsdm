/**
 * 确认对话框模块
 * 提供可复用的确认对话框功能
 */

/**
 * 显示确认对话框
 * @param {Object} options - 对话框配置选项
 * @param {string} options.title - 对话框标题
 * @param {string} options.message - 对话框消息
 * @param {string} options.confirmText - 确认按钮文本
 * @param {string} options.cancelText - 取消按钮文本
 * @param {string} options.type - 对话框类型: 'default', 'danger', 'warning', 'logout'
 * @param {string} options.icon - 图标 emoji
 * @returns {Promise<boolean>} - 返回用户的选择结果
 */
function showConfirmDialog(options) {
    return new Promise((resolve) => {
        // 创建遮罩层
        const overlay = document.createElement('div');
        overlay.className = 'confirm-dialog-overlay';
        
        // 创建对话框
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog';
        
        // 特殊样式类
        if (options.type === 'logout') {
            dialog.classList.add('confirm-logout-dialog');
        }
        
        // 创建对话框内容
        let confirmBtnClass = 'confirm-dialog-btn-primary';
        let iconClass = options.type || 'default';
        let icon = options.icon || '❓';
        
        if (options.type === 'danger') {
            confirmBtnClass = 'confirm-dialog-btn-danger';
            icon = '🗑️';
        } else if (options.type === 'warning') {
            confirmBtnClass = 'confirm-dialog-btn-primary';
            icon = '⚠️';
        } else if (options.type === 'logout') {
            confirmBtnClass = 'confirm-dialog-btn-danger';
            icon = '🚪';
        }
        
        dialog.innerHTML = `
            <div class="confirm-dialog-header">
                <span class="confirm-dialog-icon ${iconClass}">${icon}</span>
                <h3 class="confirm-dialog-title">${escapeHtml(options.title || '确认')}</h3>
            </div>
            <div class="confirm-dialog-body">
                <p class="confirm-dialog-message">${escapeHtml(options.message || '')}</p>
            </div>
            <div class="confirm-dialog-footer">
                <button class="confirm-dialog-btn confirm-dialog-btn-secondary" data-action="cancel">
                    ${escapeHtml(options.cancelText || '取消')}
                </button>
                <button class="confirm-dialog-btn ${confirmBtnClass}" data-action="confirm">
                    ${escapeHtml(options.confirmText || '确认')}
                </button>
            </div>
        `;
        
        overlay.appendChild(dialog);
        document.body.appendChild(overlay);
        
        // 防止页面滚动
        document.body.style.overflow = 'hidden';
        
        // 绑定按钮事件
        const buttons = dialog.querySelectorAll('.confirm-dialog-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                document.body.removeChild(overlay);
                document.body.style.overflow = '';
                
                if (action === 'confirm') {
                    resolve(true);
                } else {
                    resolve(false);
                }
            });
        });
        
        // 点击遮罩层关闭（返回false）
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                document.body.style.overflow = '';
                resolve(false);
            }
        });
        
        // ESC键关闭
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                document.body.removeChild(overlay);
                document.body.style.overflow = '';
                resolve(false);
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
    });
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 退出登录确认
 */
function confirmLogout() {
    return showConfirmDialog({
        title: '确认退出登录',
        message: '退出后需要重新登录才能继续使用，确定要退出吗？',
        confirmText: '确认退出',
        cancelText: '取消',
        type: 'logout'
    });
}

/**
 * 删除确认
 */
function confirmDelete(message) {
    return showConfirmDialog({
        title: '确认删除',
        message: message || '确定要删除吗？此操作不可恢复。',
        confirmText: '确认删除',
        cancelText: '取消',
        type: 'danger'
    });
}

/**
 * 警告确认
 */
function confirmWarning(message) {
    return showConfirmDialog({
        title: '警告',
        message: message || '确定要执行此操作吗？',
        confirmText: '确定',
        cancelText: '取消',
        type: 'warning'
    });
}

/**
 * 自定义确认
 */
function confirm(message, title = '确认') {
    return showConfirmDialog({
        title: title,
        message: message,
        confirmText: '确定',
        cancelText: '取消',
        type: 'default'
    });
}
