/**
 * Confirm Dialog Module
 * 统一的确认对话框
 */

const ConfirmDialog = {
    show(message, onConfirm, onCancel) {
        // 创建对话框元素
        const dialog = document.createElement('div');
        dialog.className = 'confirm-dialog-overlay';
        dialog.innerHTML = `
            <div class="confirm-dialog">
                <div class="confirm-dialog-message">${message}</div>
                <div class="confirm-dialog-buttons">
                    <button class="btn btn-secondary" id="confirm-cancel">取消</button>
                    <button class="btn btn-primary" id="confirm-ok">确认</button>
                </div>
            </div>
        `;
        
        // 添加样式
        dialog.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
        `;
        
        const dialogBox = dialog.querySelector('.confirm-dialog');
        dialogBox.style.cssText = `
            background: var(--dark-bg-card, #1e293b);
            padding: 24px;
            border-radius: 12px;
            max-width: 400px;
            width: 90%;
            text-align: center;
        `;
        
        // 按钮事件
        dialog.querySelector('#confirm-ok').addEventListener('click', () => {
            document.body.removeChild(dialog);
            if (onConfirm) onConfirm();
        });
        
        dialog.querySelector('#confirm-cancel').addEventListener('click', () => {
            document.body.removeChild(dialog);
            if (onCancel) onCancel();
        });
        
        // 点击背景关闭
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) {
                document.body.removeChild(dialog);
                if (onCancel) onCancel();
            }
        });
        
        document.body.appendChild(dialog);
    },
    
    confirm(message) {
        return new Promise((resolve) => {
            this.show(message, () => resolve(true), () => resolve(false));
        });
    }
};

// 简化的确认函数
function confirm(message, onConfirm, onCancel) {
    ConfirmDialog.show(message, onConfirm, onCancel);
}
