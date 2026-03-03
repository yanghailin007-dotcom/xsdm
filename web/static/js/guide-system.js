/**
 * ============================================
 * 大文娱系统 - 用户引导系统
 * ============================================
 * 用于首次使用时的分步指引界面
 * 
 * 使用方法:
 * 1. 引入 guide-system.css 和 guide-system.js
 * 2. 定义引导配置对象
 * 3. 调用 GuideSystem.show(guideConfig)
 */

const GuideSystem = {
    currentStep: 0,
    steps: [],
    onComplete: null,
    storageKey: '',
    
    /**
     * 检查用户是否已看过引导
     * @param {string} guideId - 引导标识
     * @returns {boolean}
     */
    hasSeen(guideId) {
        try {
            const seen = localStorage.getItem(`guide_seen_${guideId}`);
            return seen === 'true';
        } catch (e) {
            return false;
        }
    },
    
    /**
     * 标记引导为已看过
     * @param {string} guideId - 引导标识
     */
    markAsSeen(guideId) {
        try {
            localStorage.setItem(`guide_seen_${guideId}`, 'true');
        } catch (e) {
            console.warn('无法保存引导状态:', e);
        }
    },
    
    /**
     * 重置引导状态（用于测试）
     * @param {string} guideId - 引导标识，不传则重置所有
     */
    reset(guideId) {
        try {
            if (guideId) {
                localStorage.removeItem(`guide_seen_${guideId}`);
            } else {
                // 重置所有引导
                for (let i = localStorage.length - 1; i >= 0; i--) {
                    const key = localStorage.key(i);
                    if (key && key.startsWith('guide_seen_')) {
                        localStorage.removeItem(key);
                    }
                }
            }
        } catch (e) {
            console.warn('无法重置引导状态:', e);
        }
    },
    
    /**
     * 显示引导
     * @param {Object} config - 引导配置
     * @param {string} config.id - 引导唯一标识
     * @param {Array} config.steps - 步骤数组
     * @param {Function} config.onComplete - 完成回调
     * @param {boolean} config.forceShow - 强制显示（无视已看过标记）
     */
    show(config) {
        if (!config || !config.steps || config.steps.length === 0) {
            console.error('GuideSystem: 配置无效');
            return;
        }
        
        // 检查是否已看过
        if (!config.forceShow && this.hasSeen(config.id)) {
            if (config.onComplete) config.onComplete();
            return;
        }
        
        this.steps = config.steps;
        this.currentStep = 0;
        this.onComplete = config.onComplete;
        this.storageKey = config.id;
        
        this.render();
        this.bindEvents();
        this.updateStep();
    },
    
    /**
     * 渲染引导DOM
     */
    render() {
        // 移除已存在的引导
        const existing = document.getElementById('guide-system');
        if (existing) existing.remove();
        
        const overlay = document.createElement('div');
        overlay.id = 'guide-system';
        overlay.className = 'guide-overlay';
        
        const stepsHTML = this.steps.map((step, index) => {
            const layout = step.layout || 'center';
            const visual = step.visual ? this.renderVisual(step.visual) : '';
            const features = step.features ? this.renderFeatures(step.features) : '';
            const flowchart = step.flowchart ? this.renderFlowchart(step.flowchart) : '';
            const example = step.example ? this.renderExample(step.example) : '';
            const tip = step.tip ? this.renderTip(step.tip) : '';
            
            return `
                <div class="guide-step" data-step="${index}">
                    <div class="guide-step-layout ${layout}">
                        ${visual ? `<div class="guide-step-visual">${visual}</div>` : ''}
                        <div class="guide-step-content">
                            ${step.badge ? `<div class="guide-step-badge">${step.badge}</div>` : ''}
                            <h2 class="guide-step-title">${step.title}</h2>
                            <div class="guide-step-description">${step.description}</div>
                            ${features}
                            ${flowchart}
                            ${example}
                            ${tip}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        overlay.innerHTML = `
            <div class="guide-container">
                <div class="guide-header">
                    <div class="guide-progress">
                        <span class="guide-progress-text">第 <span id="guide-current-step">1</span> / ${this.steps.length} 步</span>
                        <div class="guide-progress-bar">
                            <div class="guide-progress-fill" id="guide-progress-fill" style="width: 0%"></div>
                        </div>
                    </div>
                    <button class="guide-skip-btn" id="guide-skip">跳过引导</button>
                </div>
                
                <div class="guide-content">
                    ${stepsHTML}
                </div>
                
                <div class="guide-footer">
                    <label class="guide-checkbox">
                        <input type="checkbox" id="guide-dont-show">
                        <span>下次不再显示此引导</span>
                    </label>
                    <div class="guide-nav">
                        <button class="guide-btn guide-btn-prev" id="guide-prev" style="display: none;">
                            ← 上一步
                        </button>
                        <button class="guide-btn guide-btn-next" id="guide-next">
                            下一步 →
                        </button>
                        <button class="guide-btn guide-btn-finish" id="guide-finish" style="display: none;">
                            ✓ 开始创作
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // 触发重绘以启动动画
        requestAnimationFrame(() => {
            overlay.classList.add('active');
        });
    },
    
    /**
     * 渲染视觉元素
     */
    renderVisual(visual) {
        if (visual.type === 'icon') {
            return `<div class="icon-large">${visual.content}</div>`;
        } else if (visual.type === 'image') {
            return `<img src="${visual.content}" alt="" class="guide-image">`;
        } else if (visual.type === 'emoji') {
            return `<div class="icon-large">${visual.content}</div>`;
        }
        return '';
    },
    
    /**
     * 渲染特性列表
     */
    renderFeatures(features) {
        const items = features.map(f => `
            <div class="guide-feature-item">
                <div class="guide-feature-icon">${f.icon}</div>
                <div class="guide-feature-text">
                    <h4>${f.title}</h4>
                    <p>${f.description}</p>
                </div>
            </div>
        `).join('');
        
        return `<div class="guide-features">${items}</div>`;
    },
    
    /**
     * 渲染流程图
     */
    renderFlowchart(flowchart) {
        const steps = flowchart.steps.map((step, index) => `
            <div class="guide-flow-step">
                <div class="guide-flow-step-icon">${step.icon}</div>
                <div class="guide-flow-step-title">${step.title}</div>
                <div class="guide-flow-step-desc">${step.description}</div>
            </div>
            ${index < flowchart.steps.length - 1 ? '<div class="guide-flow-arrow">→</div>' : ''}
        `).join('');
        
        return `<div class="guide-flowchart">${steps}</div>`;
    },
    
    /**
     * 渲染示例卡片
     */
    renderExample(example) {
        return `
            <div class="guide-example-card">
                <div class="guide-example-header">💡 ${example.title}</div>
                <div class="guide-example-content">${example.content}</div>
            </div>
        `;
    },
    
    /**
     * 渲染提示
     */
    renderTip(tip) {
        return `
            <div class="guide-tip">
                <div class="guide-tip-icon">${tip.icon || '💡'}</div>
                <div class="guide-tip-content">
                    <div class="guide-tip-title">${tip.title}</div>
                    <div class="guide-tip-text">${tip.content}</div>
                </div>
            </div>
        `;
    },
    
    /**
     * 绑定事件
     */
    bindEvents() {
        const overlay = document.getElementById('guide-system');
        const prevBtn = document.getElementById('guide-prev');
        const nextBtn = document.getElementById('guide-next');
        const finishBtn = document.getElementById('guide-finish');
        const skipBtn = document.getElementById('guide-skip');
        const dontShowCheckbox = document.getElementById('guide-dont-show');
        
        prevBtn.addEventListener('click', () => this.prev());
        nextBtn.addEventListener('click', () => this.next());
        finishBtn.addEventListener('click', () => this.finish());
        skipBtn.addEventListener('click', () => this.skip());
        
        // ESC键关闭
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.skip();
            } else if (e.key === 'ArrowRight') {
                if (this.currentStep < this.steps.length - 1) this.next();
            } else if (e.key === 'ArrowLeft') {
                if (this.currentStep > 0) this.prev();
            }
        });
    },
    
    /**
     * 更新步骤显示
     */
    updateStep() {
        const steps = document.querySelectorAll('.guide-step');
        const prevBtn = document.getElementById('guide-prev');
        const nextBtn = document.getElementById('guide-next');
        const finishBtn = document.getElementById('guide-finish');
        const currentStepEl = document.getElementById('guide-current-step');
        const progressFill = document.getElementById('guide-progress-fill');
        
        steps.forEach((step, index) => {
            step.classList.toggle('active', index === this.currentStep);
        });
        
        currentStepEl.textContent = this.currentStep + 1;
        progressFill.style.width = `${((this.currentStep + 1) / this.steps.length) * 100}%`;
        
        // 按钮状态
        prevBtn.style.display = this.currentStep === 0 ? 'none' : 'flex';
        
        if (this.currentStep === this.steps.length - 1) {
            nextBtn.style.display = 'none';
            finishBtn.style.display = 'flex';
        } else {
            nextBtn.style.display = 'flex';
            finishBtn.style.display = 'none';
        }
    },
    
    /**
     * 上一步
     */
    prev() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.updateStep();
        }
    },
    
    /**
     * 下一步
     */
    next() {
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.updateStep();
        }
    },
    
    /**
     * 完成引导
     */
    finish() {
        const dontShow = document.getElementById('guide-dont-show').checked;
        if (dontShow) {
            this.markAsSeen(this.storageKey);
        }
        this.close();
        if (this.onComplete) this.onComplete();
    },
    
    /**
     * 跳过引导
     */
    skip() {
        const dontShow = document.getElementById('guide-dont-show').checked;
        if (dontShow) {
            this.markAsSeen(this.storageKey);
        }
        this.close();
        if (this.onComplete) this.onComplete();
    },
    
    /**
     * 关闭引导
     */
    close() {
        const overlay = document.getElementById('guide-system');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 300);
        }
    }
};

// 导出模块（如果支持）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GuideSystem;
}
