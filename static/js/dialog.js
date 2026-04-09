/**
 * 全局自定义弹窗工具 - 替换原生 confirm/alert/prompt
 * 用法：
 *   await Dialog.confirm('标题', '消息内容');
 *   await Dialog.alert('提示内容');
 *   const name = await Dialog.prompt('请输入名称', '默认值');
 */

const Dialog = {
    // 确认对话框
    confirm(title, message, options = {}) {
        return new Promise((resolve) => {
            const confirmText = options.confirmText || '确定';
            const cancelText = options.cancelText || '取消';
            const confirmClass = options.confirmClass || 'dialog-btn-primary';
            const icon = options.icon || '&#xe8b2;';
            
            const html = `
                <div class="dialog-overlay" onclick="Dialog._close(false)"></div>
                <div class="dialog-content">
                    <div class="dialog-header">
                        <span class="dialog-icon" style="color: ${confirmClass === 'dialog-btn-danger' ? '#ef4444' : '#3b82f6'};">${icon}</span>
                        <span class="dialog-title">${title}</span>
                    </div>
                    <div class="dialog-body">${message}</div>
                    <div class="dialog-footer">
                        <button class="dialog-btn dialog-btn-secondary" onclick="Dialog._close(false)">${cancelText}</button>
                        <button class="dialog-btn ${confirmClass}" onclick="Dialog._close(true)">${confirmText}</button>
                    </div>
                </div>
            `;
            
            this._show(html, resolve);
        });
    },
    
    // 提示框
    alert(message, title = '提示') {
        return new Promise((resolve) => {
            const html = `
                <div class="dialog-overlay" onclick="Dialog._close()"></div>
                <div class="dialog-content">
                    <div class="dialog-header">
                        <span class="dialog-icon" style="color: #f59e0b;">&#xe002;</span>
                        <span class="dialog-title">${title}</span>
                    </div>
                    <div class="dialog-body">${message}</div>
                    <div class="dialog-footer">
                        <button class="dialog-btn dialog-btn-primary" onclick="Dialog._close()">知道了</button>
                    </div>
                </div>
            `;
            
            this._show(html, resolve);
        });
    },
    
    // 输入框
    prompt(title, defaultValue = '', options = {}) {
        return new Promise((resolve) => {
            const confirmText = options.confirmText || '确定';
            const cancelText = options.cancelText || '取消';
            
            const html = `
                <div class="dialog-overlay" onclick="Dialog._close(null)"></div>
                <div class="dialog-content">
                    <div class="dialog-header">
                        <span class="dialog-icon" style="color: #3b82f6;">&#xe3c9;</span>
                        <span class="dialog-title">${title}</span>
                    </div>
                    <div class="dialog-body">
                        <input type="text" class="dialog-input" id="dialog-prompt-input" value="${defaultValue}" placeholder="${options.placeholder || ''}">
                    </div>
                    <div class="dialog-footer">
                        <button class="dialog-btn dialog-btn-secondary" onclick="Dialog._close(null)">${cancelText}</button>
                        <button class="dialog-btn dialog-btn-primary" onclick="Dialog._close(document.getElementById('dialog-prompt-input').value)">${confirmText}</button>
                    </div>
                </div>
            `;
            
            this._show(html, resolve);
            
            // 自动聚焦输入框
            setTimeout(() => {
                const input = document.getElementById('dialog-prompt-input');
                if (input) {
                    input.focus();
                    input.select();
                }
            }, 100);
        });
    },
    
    // 成功提示
    success(message) {
        return this.alert(message, '成功');
    },
    
    // 错误提示
    error(message) {
        return new Promise((resolve) => {
            const html = `
                <div class="dialog-overlay" onclick="Dialog._close()"></div>
                <div class="dialog-content">
                    <div class="dialog-header">
                        <span class="dialog-icon" style="color: #ef4444;">&#xe000;</span>
                        <span class="dialog-title">错误</span>
                    </div>
                    <div class="dialog-body">${message}</div>
                    <div class="dialog-footer">
                        <button class="dialog-btn dialog-btn-danger" onclick="Dialog._close()">知道了</button>
                    </div>
                </div>
            `;
            
            this._show(html, resolve);
        });
    },
    
    // 内部方法：显示弹窗
    _show(html, callback) {
        // 移除已存在的弹窗
        this._close();
        
        // 创建弹窗容器
        const modal = document.createElement('div');
        modal.id = 'global-dialog-modal';
        modal.className = 'dialog-modal';
        modal.innerHTML = html;
        document.body.appendChild(modal);
        
        // 保存回调
        this._callback = callback;
        
        // 禁止背景滚动
        document.body.style.overflow = 'hidden';
        
        // 支持 ESC 关闭
        this._keydownHandler = (e) => {
            if (e.key === 'Escape') {
                this._close(null);
            }
        };
        document.addEventListener('keydown', this._keydownHandler);
    },
    
    // 内部方法：关闭弹窗
    _close(result) {
        const modal = document.getElementById('global-dialog-modal');
        if (modal) {
            modal.remove();
        }
        
        document.body.style.overflow = '';
        
        if (this._keydownHandler) {
            document.removeEventListener('keydown', this._keydownHandler);
            this._keydownHandler = null;
        }
        
        if (this._callback) {
            const cb = this._callback;
            this._callback = null;
            cb(result);
        }
    }
};

// 添加 CSS 样式
(function() {
    if (document.getElementById('dialog-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'dialog-styles';
    style.textContent = `
        .dialog-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 99999;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        
        .dialog-overlay {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            backdrop-filter: blur(8px);
        }
        
        .dialog-content {
            position: relative;
            background: linear-gradient(145deg, #1e1e2e 0%, #2d2d3d 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05);
            min-width: 360px;
            max-width: 480px;
            margin: 20px;
            overflow: hidden;
            animation: dialog-show 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        
        @keyframes dialog-show {
            from {
                opacity: 0;
                transform: scale(0.9) translateY(20px);
            }
            to {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }
        
        .dialog-header {
            padding: 20px 24px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .dialog-icon {
            font-family: 'Material Icons';
            font-size: 24px;
            color: #3b82f6;
        }
        
        .dialog-title {
            font-size: 18px;
            font-weight: 600;
            color: #f1f5f9;
        }
        
        .dialog-body {
            padding: 16px 24px 24px;
            font-size: 14px;
            line-height: 1.7;
            color: #94a3b8;
        }
        
        .dialog-footer {
            padding: 0 24px 20px;
            display: flex;
            justify-content: flex-end;
            gap: 12px;
        }
        
        .dialog-btn {
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all 0.2s ease;
        }
        
        .dialog-btn-primary {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: #fff;
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
        }
        
        .dialog-btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
        }
        
        .dialog-btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .dialog-btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: rgba(255, 255, 255, 0.15);
        }
        
        .dialog-btn-danger {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: #fff;
            box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
        }
        
        .dialog-btn-danger:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(239, 68, 68, 0.4);
        }
        
        .dialog-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            font-size: 14px;
            color: #f1f5f9;
            box-sizing: border-box;
            transition: all 0.2s;
        }
        
        .dialog-input:focus {
            outline: none;
            border-color: rgba(99, 102, 241, 0.5);
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
        }
        
        .dialog-input::placeholder {
            color: #64748b;
        }
    `;
    
    document.head.appendChild(style);
})();
