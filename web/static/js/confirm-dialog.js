/**
 * 通用确认对话框组件
 * 用于替代简陋的浏览器原生confirm()对话框
 */

class ConfirmDialog {
    constructor() {
        this.overlay = null;
        this.dialog = null;
        this.onConfirm = null;
        this.onCancel = null;
    }

    /**
     * 显示确认对话框
     * @param {Object} options - 配置选项
     * @param {string} options.title - 对话框标题
     * @param {string} options.message - 主要消息
     * @param {string} options.subMessage - 次要消息（可选）
     * @param {string} options.confirmText - 确认按钮文本
     * @param {string} options.cancelText - 取消按钮文本
     * @param {string} options.type - 对话框类型：'question', 'warning', 'danger', 'success'
     * @param {string} options.icon - 自定义图标（emoji或文本）
     * @returns {Promise<boolean>} - 返回Promise，true表示确认，false表示取消
     */
    show(options = {}) {
        return new Promise((resolve) => {
            const {
                title = '确认操作',
                message = '您确定要执行此操作吗？',
                subMessage = '',
                confirmText = '确认',
                cancelText = '取消',
                type = 'question',
                icon = this.getDefaultIcon(type)
            } = options;

            this.onConfirm = () => resolve(true);
            this.onCancel = () => resolve(false);

            // 创建对话框HTML
            const dialogHTML = `
                <div class="confirm-dialog-overlay" id="confirmDialogOverlay">
                    <div class="confirm-dialog">
                        <div class="confirm-dialog-header">
                            <span class="icon ${this.getIconClass(type)}">${icon}</span>
                            <h3>${title}</h3>
                        </div>
                        <div class="confirm-dialog-body">
                            <p class="message">${message}</p>
                            ${subMessage ? `<p class="sub-message">${subMessage}</p>` : ''}
                        </div>
                        <div class="confirm-dialog-footer">
                            <button class="confirm-dialog-btn cancel" id="cancelBtn">
                                <span class="icon">✕</span>
                                <span>${cancelText}</span>
                            </button>
                            <button class="confirm-dialog-btn confirm ${this.getButtonClass(type)}" id="confirmBtn">
                                <span class="icon">${this.getConfirmIcon(type)}</span>
                                <span>${confirmText}</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;

            // 添加到页面
            document.body.insertAdjacentHTML('beforeend', dialogHTML);

            // 获取元素引用
            this.overlay = document.getElementById('confirmDialogOverlay');
            this.dialog = this.overlay.querySelector('.confirm-dialog');

            // 绑定事件
            this.bindEvents();

            // 阻止body滚动
            document.body.style.overflow = 'hidden';
        });
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        const confirmBtn = document.getElementById('confirmBtn');
        const cancelBtn = document.getElementById('cancelBtn');

        // 确认按钮
        confirmBtn.addEventListener('click', () => {
            this.hide();
            if (this.onConfirm) {
                this.onConfirm();
            }
        });

        // 取消按钮
        cancelBtn.addEventListener('click', () => {
            this.hide();
            if (this.onCancel) {
                this.onCancel();
            }
        });

        // 点击遮罩层关闭
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.hide();
                if (this.onCancel) {
                    this.onCancel();
                }
            }
        });

        // ESC键关闭
        this.handleEscape = (e) => {
            if (e.key === 'Escape') {
                this.hide();
                if (this.onCancel) {
                    this.onCancel();
                }
            }
        };
        document.addEventListener('keydown', this.handleEscape);

        // 确认按钮获得焦点
        setTimeout(() => {
            confirmBtn.focus();
        }, 100);
    }

    /**
     * 隐藏对话框
     */
    hide() {
        if (this.overlay) {
            // 添加淡出动画
            this.overlay.style.opacity = '0';
            
            setTimeout(() => {
                if (this.overlay && this.overlay.parentNode) {
                    this.overlay.parentNode.removeChild(this.overlay);
                }
                
                // 恢复body滚动
                document.body.style.overflow = '';
                
                // 移除键盘事件监听
                document.removeEventListener('keydown', this.handleEscape);
                
                this.overlay = null;
                this.dialog = null;
            }, 200);
        }
    }

    /**
     * 获取默认图标
     */
    getDefaultIcon(type) {
        const icons = {
            question: '❓',
            warning: '⚠️',
            danger: '🗑️',
            success: '✅'
        };
        return icons[type] || icons.question;
    }

    /**
     * 获取图标CSS类
     */
    getIconClass(type) {
        const classes = {
            question: 'confirm-dialog-icon-question',
            warning: 'confirm-dialog-icon-warning',
            danger: 'confirm-dialog-icon-danger',
            success: 'confirm-dialog-icon-success'
        };
        return classes[type] || classes.question;
    }

    /**
     * 获取按钮CSS类
     */
    getButtonClass(type) {
        const classes = {
            question: '',
            warning: 'warning',
            danger: 'danger',
            success: ''
        };
        return classes[type] || '';
    }

    /**
     * 获取确认按钮图标
     */
    getConfirmIcon(type) {
        const icons = {
            question: '✓',
            warning: '⚠️',
            danger: '🗑️',
            success: '✓'
        };
        return icons[type] || icons.question;
    }
}

// 创建全局实例
const confirmDialog = new ConfirmDialog();

/**
 * 全局函数：显示确认对话框
 * @param {string} message - 要显示的消息
 * @param {Object} options - 其他配置选项
 * @returns {Promise<boolean>}
 */
function showConfirm(message, options = {}) {
    return confirmDialog.show({
        message,
        ...options
    });
}

/**
 * 退出登录确认对话框
 */
function confirmLogout() {
    return confirmDialog.show({
        title: '退出登录',
        message: '您确定要退出登录吗？',
        subMessage: '退出后需要重新登录才能访问系统功能',
        confirmText: '退出登录',
        cancelText: '取消',
        type: 'warning',
        icon: '🚪'
    });
}

/**
 * 删除确认对话框
 */
function confirmDelete(itemName = '此项目') {
    return confirmDialog.show({
        title: '确认删除',
        message: `您确定要删除${itemName}吗？`,
        subMessage: '此操作不可撤销，请谨慎操作',
        confirmText: '确认删除',
        cancelText: '取消',
        type: 'danger',
        icon: '🗑️'
    });
}

/**
 * 通用操作确认对话框
 */
function confirmAction(actionName, options = {}) {
    const defaultOptions = {
        title: '确认操作',
        message: `您确定要执行"${actionName}"操作吗？`,
        type: 'question',
        icon: '❓'
    };
    
    return confirmDialog.show({
        ...defaultOptions,
        ...options
    });
}

// 导出（如果使用模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { confirmDialog, showConfirm, confirmLogout, confirmDelete, confirmAction };
}