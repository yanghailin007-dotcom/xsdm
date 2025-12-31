// ==================== 分阶段生成页面功能 ====================

class PhaseOneSetup {
    constructor() {
        this.currentTaskId = null;
        this.progressInterval = null;
        this.isGenerating = false;
    }

    static init() {
        const instance = new PhaseOneSetup();
        instance.bindEvents();
        instance.initializeUI();
        return instance;
    }

    bindEvents() {
        // 表单提交事件
        const form = document.getElementById('phase-one-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // 重置按钮
        const resetBtn = document.getElementById('reset-form-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetForm());
        }

        // 生成模式选择
        const modeSelect = document.getElementById('generation-mode');
        if (modeSelect) {
            modeSelect.addEventListener('change', (e) => this.onModeChange(e));
        }

        // 结果标签页切换
        const resultTabs = document.querySelectorAll('.result-tab');
        resultTabs.forEach(tab => {
            tab.addEventListener('click', (e) => this.switchResultTab(e));
        });

        // 结果操作按钮
        const continueBtn = document.getElementById('continue-phase-two-btn');
        if (continueBtn) {
            continueBtn.addEventListener('click', () => this.continueToPhaseTwo());
        }

        const saveBtn = document.getElementById('save-project-btn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveProject());
        }

        const regenerateBtn = document.getElementById('regenerate-btn');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => this.regenerate());
        }

        // 暂停按钮
        const pauseBtn = document.getElementById('pause-generation-btn');
        if (pauseBtn) {
            pauseBtn.addEventListener('click', () => this.togglePause());
        }
    }

    initializeUI() {
        // 隐藏进度和结果区域
        this.hideProgress();
        this.hideResults();
        
        // 设置默认值
        this.setDefaultValues();
        
        // 初始化工具提示
        this.initTooltips();
    }

    setDefaultValues() {
        const titleInput = document.getElementById('novel-title');
        const synopsisInput = document.getElementById('novel-synopsis');
        const coreSettingInput = document.getElementById('core-setting');
        const sellingPointsInput = document.getElementById('core-selling-points');
        const chaptersInput = document.getElementById('total-chapters');

        if (titleInput && !titleInput.value) {
            titleInput.placeholder = '例：凡人修仙同人·观战者';
        }
        
        if (synopsisInput && !synopsisInput.value) {
            synopsisInput.placeholder = '简要描述小说内容...';
        }
        
        if (coreSettingInput && !coreSettingInput.value) {
            coreSettingInput.placeholder = '描述故事的核心背景设定，包括世界观、主要设定、时代背景等...';
        }
        
        if (sellingPointsInput && !sellingPointsInput.value) {
            sellingPointsInput.value = '爽文节奏 + 独特设定 + 人物成长';
        }
        
        if (chaptersInput && !chaptersInput.value) {
            chaptersInput.value = 200;
        }
    }

    initTooltips() {
        // 为帮助图标添加提示功能
        const helpIcons = document.querySelectorAll('.help-icon');
        helpIcons.forEach(icon => {
            icon.style.cursor = 'help';
        });
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        
        console.log('🚀 [DEBUG] handleFormSubmit 开始执行');
        
        if (this.isGenerating) {
            console.log('⚠️ [DEBUG] 已有任务在生成中，忽略此次请求');
            this.showToast('正在生成中，请稍候...', 'warning');
            return;
        }

        try {
            console.log('📋 [DEBUG] 开始收集表单数据');
            const formData = this.collectFormData();
            console.log('📋 [DEBUG] 表单数据收集完成:', formData);
            
            // 验证表单数据
            console.log('✅ [DEBUG] 开始验证表单数据');
            if (!this.validateFormData(formData)) {
                console.log('❌ [DEBUG] 表单数据验证失败');
                return;
            }
            console.log('✅ [DEBUG] 表单数据验证通过');

            this.isGenerating = true;
            this.showProgress();
            this.updateProgressMessage('正在启动生成任务...');

            // 构建请求URL和选项
            const apiUrl = '/api/phase-one/generate';
            console.log('🌐 [DEBUG] 准备发送API请求');
            console.log('🌐 [DEBUG] 请求URL:', apiUrl);
            console.log('🌐 [DEBUG] 请求方法: POST');
            console.log('🌐 [DEBUG] 请求头: Content-Type: application/json');
            console.log('🌐 [DEBUG] 请求体:', JSON.stringify(formData, null, 2));

            // 启动生成任务
            console.log('📤 [DEBUG] 发送fetch请求...');
            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            console.log('📥 [DEBUG] 收到响应');
            console.log('📥 [DEBUG] 响应状态:', response.status);
            console.log('📥 [DEBUG] 响应状态文本:', response.statusText);
            console.log('📥 [DEBUG] 响应头:', Object.fromEntries(response.headers.entries()));

            if (!response.ok) {
                console.log('❌ [DEBUG] 响应状态错误，尝试解析错误信息');
                let errorData = {};
                try {
                    errorData = await response.json();
                    console.log('📋 [DEBUG] 错误响应数据:', errorData);
                } catch (parseError) {
                    console.log('⚠️ [DEBUG] 无法解析错误响应为JSON:', parseError);
                    const responseText = await response.text();
                    console.log('📋 [DEBUG] 原始响应文本:', responseText);
                }
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            console.log('✅ [DEBUG] 响应状态正常，开始解析JSON');
            const result = await response.json();
            console.log('📋 [DEBUG] 解析后的响应数据:', result);

            if (result.success) {
                console.log('✅ [DEBUG] 任务启动成功');
                this.currentTaskId = result.task_id;
                console.log('🎯 [DEBUG] 设置任务ID:', this.currentTaskId);
                this.updateProgressMessage(`任务已启动: ${this.currentTaskId}，正在生成中...`);
                this.startProgressMonitoring();
            } else {
                console.log('❌ [DEBUG] 任务启动失败，响应显示success=false');
                throw new Error(result.error || '启动任务失败');
            }

        } catch (error) {
            console.error('❌ [DEBUG] 生成任务失败:', error);
            console.error('❌ [DEBUG] 错误类型:', error.constructor.name);
            console.error('❌ [DEBUG] 错误消息:', error.message);
            console.error('❌ [DEBUG] 错误堆栈:', error.stack);
            
            // 检查是否是网络错误
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.error('🌐 [DEBUG] 可能是网络连接问题或服务器未启动');
                this.showToast(`网络错误: 无法连接到服务器，请检查服务器是否启动`, 'error');
            } else if (error.message.includes('404')) {
                console.error('🔗 [DEBUG] API端点未找到 (404)');
                this.showToast(`页面未找到: API端点不存在，请检查路由配置`, 'error');
            } else if (error.message.includes('401')) {
                console.error('🔐 [DEBUG] 未授权访问 (401)');
                this.showToast(`未授权: 请先登录`, 'error');
            } else {
                this.showToast(`生成失败: ${error.message}`, 'error');
            }
            
            this.hideProgress();
            this.isGenerating = false;
        }
    }

    collectFormData() {
        const title = document.getElementById('novel-title').value.trim();
        const synopsis = document.getElementById('novel-synopsis').value.trim();
        const coreSetting = document.getElementById('core-setting').value.trim();
        const coreSellingPoints = document.getElementById('core-selling-points').value.trim();
        const totalChapters = parseInt(document.getElementById('total-chapters').value) || 200;
        const generationMode = document.getElementById('generation-mode').value;
        const targetPlatform = document.getElementById('target-platform').value || 'fanqie';

        console.log('🎯 [DEBUG] 目标平台:', targetPlatform);

        return {
            title,
            synopsis,
            core_setting: coreSetting,
            core_selling_points: coreSellingPoints,
            total_chapters: totalChapters,
            generation_mode: generationMode,
            target_platform: targetPlatform
        };
    }

    validateFormData(data) {
        if (!data.title) {
            this.showToast('请输入小说标题', 'error');
            return false;
        }

        if (!data.synopsis) {
            this.showToast('请输入小说简介', 'error');
            return false;
        }

        if (!data.core_setting) {
            this.showToast('请输入核心设定', 'error');
            return false;
        }

        if (data.core_setting.length < 50) {
            this.showToast('核心设定建议至少50字，详细描述有助于生成更好的内容', 'warning');
        }

        if (data.total_chapters < 5 || data.total_chapters > 200) {
            this.showToast('章节数必须在5-200之间', 'error');
            return false;
        }

        return true;
    }

    startProgressMonitoring() {
        if (!this.currentTaskId) {
            console.log('⚠️ [DEBUG] 没有任务ID，无法开始进度监控');
            return;
        }

        console.log('🔄 [DEBUG] 开始进度监控，任务ID:', this.currentTaskId);

        this.progressInterval = setInterval(async () => {
            try {
                const statusUrl = `/api/phase-one/task/${this.currentTaskId}/status`;
                console.log('🔍 [DEBUG] 查询任务状态，URL:', statusUrl);
                
                const response = await fetch(statusUrl);
                console.log('📥 [DEBUG] 状态查询响应状态:', response.status);
                
                if (!response.ok) {
                    console.warn('⚠️ [DEBUG] 获取任务状态失败:', response.status);
                    return;
                }

                const taskStatus = await response.json();
                console.log('📋 [DEBUG] 任务状态数据:', taskStatus);
                
                this.updateProgressUI(taskStatus);

                // 检查任务是否完成
                if (taskStatus.status === 'completed') {
                    console.log('✅ [DEBUG] 任务已完成，停止监控');
                    clearInterval(this.progressInterval);
                    this.handleTaskCompletion(taskStatus);
                } else if (taskStatus.status === 'failed') {
                    console.log('❌ [DEBUG] 任务失败，停止监控');
                    clearInterval(this.progressInterval);
                    this.handleTaskFailure(taskStatus);
                }

            } catch (error) {
                console.error('❌ [DEBUG] 获取任务状态失败:', error);
                console.error('❌ [DEBUG] 错误详情:', error.message);
            }
        }, 2000); // 每2秒检查一次
    }

    updateProgressUI(taskStatus) {
        // 更新进度条
        const progressBar = document.getElementById('progress-bar-fill');
        const progressPercentage = document.getElementById('progress-percentage');
        
        if (progressBar && progressPercentage) {
            const progress = taskStatus.progress || 0;
            progressBar.style.width = `${progress}%`;
            progressPercentage.textContent = `${progress}%`;
        }

        // 更新进度消息
        if (taskStatus.current_step) {
            this.updateProgressMessage(this.getStepMessage(taskStatus.current_step));
        }

        // 更新步骤指示器
        this.updateProgressSteps(taskStatus.current_step);
    }

    getStepMessage(step) {
        const stepMessages = {
            'initialization': '正在初始化生成环境...',
            'planning': '正在规划故事结构...',
            'worldview_generation': '正在生成世界观设定...',
            'character_design': '正在设计角色...',
            'story_outline': '正在生成故事大纲...',
            'validation': '正在验证生成结果...',
            'completed': '生成完成！'
        };
        
        return stepMessages[step] || '处理中...';
    }

    updateProgressSteps(currentStep) {
        const steps = document.querySelectorAll('.progress-step');
        const stepOrder = [
            'planning',
            'worldview_generation', 
            'character_design',
            'story_outline',
            'validation'
        ];

        const currentIndex = stepOrder.indexOf(currentStep);
        
        steps.forEach((step, index) => {
            const stepKey = step.dataset.step;
            const stepIndex = stepOrder.indexOf(stepKey);
            
            if (stepIndex < currentIndex) {
                step.classList.add('completed');
                step.classList.remove('active');
            } else if (stepIndex === currentIndex) {
                step.classList.add('active');
                step.classList.remove('completed');
            } else {
                step.classList.remove('active', 'completed');
            }
        });
    }

    async handleTaskCompletion(taskStatus) {
        this.hideProgress();
        this.isGenerating = false;
        
        // 显示结果
        this.showResults(taskStatus.result);
        this.showToast('设定生成完成！', 'success');
        
        // 如果是完整两阶段模式，询问是否继续
        const generationMode = document.getElementById('generation-mode').value;
        if (generationMode === 'full_two_phase') {
            setTimeout(() => {
                if (confirm('第一阶段设定已完成，是否立即开始第二阶段章节生成？')) {
                    this.continueToPhaseTwo();
                }
            }, 1000);
        }
    }

    handleTaskFailure(taskStatus) {
        this.hideProgress();
        this.isGenerating = false;
        this.showToast(`生成失败: ${taskStatus.error || '未知错误'}`, 'error');
    }

    showResults(result) {
        const resultsSection = document.getElementById('results-section');
        if (!resultsSection) return;

        resultsSection.style.display = 'block';
        
        // 填充结果内容
        this.populateResultContent(result);
        
        // 滚动到结果区域
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    populateResultContent(result) {
        // 填充总览
        const overviewPane = document.getElementById('result-overview');
        if (overviewPane && result) {
            overviewPane.innerHTML = this.generateOverviewHTML(result);
        }

        // 填充世界观
        const worldviewPane = document.getElementById('result-worldview');
        if (worldviewPane && result.worldview) {
            worldviewPane.innerHTML = this.generateWorldviewHTML(result.worldview);
        }

        // 填充角色
        const charactersPane = document.getElementById('result-characters');
        if (charactersPane && result.characters) {
            charactersPane.innerHTML = this.generateCharactersHTML(result.characters);
        }

        // 填充大纲
        const outlinesPane = document.getElementById('result-outlines');
        if (outlinesPane && result.outlines) {
            outlinesPane.innerHTML = this.generateOutlinesHTML(result.outlines);
        }

        // 填充验证信息
        const validationPane = document.getElementById('result-validation');
        if (validationPane && result.validation) {
            validationPane.innerHTML = this.generateValidationHTML(result.validation);
        }
    }

    generateOverviewHTML(result) {
        return `
            <div class="result-overview-content">
                <h3>📊 生成概览</h3>
                <div class="overview-grid">
                    <div class="overview-item">
                        <h4>📖 小说标题</h4>
                        <p>${result.title || '未设置'}</p>
                    </div>
                    <div class="overview-item">
                        <h4>📝 简介</h4>
                        <p>${result.synopsis || '未设置'}</p>
                    </div>
                    <div class="overview-item">
                        <h4>🌍 世界观</h4>
                        <p>${result.worldview?.summary || '世界观设定已生成'}</p>
                    </div>
                    <div class="overview-item">
                        <h4>👥 主要角色</h4>
                        <p>${result.characters?.length || 0} 个角色已设计</p>
                    </div>
                    <div class="overview-item">
                        <h4>📚 章节大纲</h4>
                        <p>${result.outlines?.length || 0} 章大纲已生成</p>
                    </div>
                    <div class="overview-item">
                        <h4>⭐ 核心卖点</h4>
                        <p>${result.core_selling_points || '未设置'}</p>
                    </div>
                </div>
            </div>
        `;
    }

    generateWorldviewHTML(worldview) {
        return `
            <div class="worldview-content">
                <h3>🌍 世界观设定</h3>
                <div class="worldview-sections">
                    <div class="worldview-section">
                        <h4>📖 背景设定</h4>
                        <p>${worldview.background ||世界观设定背景}</p>
                    </div>
                    <div class="worldview-section">
                        <h4>⚙️ 核心规则</h4>
                        <p>${worldview.rules || '世界核心规则'}</p>
                    </div>
                    <div class="worldview-section">
                        <h4>🏰 主要势力</h4>
                        <p>${worldview.factions || '主要势力组织'}</p>
                    </div>
                </div>
            </div>
        `;
    }

    generateCharactersHTML(characters) {
        if (!characters || characters.length === 0) {
            return '<div class="characters-content"><h3>👥 角色设计</h3><p>暂无角色数据</p></div>';
        }

        let html = '<div class="characters-content"><h3>👥 角色设计</h3><div class="characters-grid">';
        
        characters.forEach(character => {
            html += `
                <div class="character-card">
                    <h4>${character.name || '未命名角色'}</h4>
                    <p><strong>身份:</strong> ${character.role || '未设定'}</p>
                    <p><strong>性格:</strong> ${character.personality || '未设定'}</p>
                    <p><strong>背景:</strong> ${character.background || '未设定'}</p>
                </div>
            `;
        });
        
        html += '</div></div>';
        return html;
    }

    generateOutlinesHTML(outlines) {
        if (!outlines || outlines.length === 0) {
            return '<div class="outlines-content"><h3>📚 章节大纲</h3><p>暂无大纲数据</p></div>';
        }

        let html = '<div class="outlines-content"><h3>📚 章节大纲</h3><div class="outlines-list">';
        
        outlines.forEach((outline, index) => {
            html += `
                <div class="outline-item">
                    <h4>第${outline.chapter || (index + 1)}章：${outline.title || '未命名'}</h4>
                    <p>${outline.summary || '暂无概要'}</p>
                    ${outline.key_events ? `<p><strong>关键事件:</strong> ${outline.key_events}</p>` : ''}
                </div>
            `;
        });
        
        html += '</div></div>';
        return html;
    }

    generateValidationHTML(validation) {
        return `
            <div class="validation-content">
                <h3>✅ 验证结果</h3>
                <div class="validation-items">
                    <div class="validation-item ${validation.worldview_complete ? 'success' : 'warning'}">
                        <span class="validation-icon">${validation.worldview_complete ? '✅' : '⚠️'}</span>
                        <span>世界观设定${validation.worldview_complete ? '完整' : '需要完善'}</span>
                    </div>
                    <div class="validation-item ${validation.characters_complete ? 'success' : 'warning'}">
                        <span class="validation-icon">${validation.characters_complete ? '✅' : '⚠️'}</span>
                        <span>角色设计${validation.characters_complete ? '完整' : '需要完善'}</span>
                    </div>
                    <div class="validation-item ${validation.outlines_complete ? 'success' : 'warning'}">
                        <span class="validation-icon">${validation.outlines_complete ? '✅' : '⚠️'}</span>
                        <span>章节大纲${validation.outlines_complete ? '完整' : '需要完善'}</span>
                    </div>
                    <div class="validation-item ${validation.logic_consistent ? 'success' : 'error'}">
                        <span class="validation-icon">${validation.logic_consistent ? '✅' : '❌'}</span>
                        <span>逻辑${validation.logic_consistent ? '一致' : '存在冲突'}</span>
                    </div>
                </div>
                ${validation.suggestions ? `
                    <div class="validation-suggestions">
                        <h4>💡 改进建议</h4>
                        <ul>
                            ${validation.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
            </div>
        `;
    }

    switchResultTab(event) {
        const tab = event.target;
        const tabName = tab.dataset.tab;
        
        // 更新标签状态
        document.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // 更新内容面板
        document.querySelectorAll('.result-pane').forEach(pane => pane.classList.remove('active'));
        const targetPane = document.getElementById(`result-${tabName}`);
        if (targetPane) {
            targetPane.classList.add('active');
        }
    }

    continueToPhaseTwo() {
        if (!this.currentTaskId) {
            this.showToast('没有可继续的任务', 'error');
            return;
        }
        
        // 跳转到第二阶段页面
        window.location.href = `/phase-two-generation?task_id=${this.currentTaskId}`;
    }

    async saveProject() {
        if (!this.currentTaskId) {
            this.showToast('没有可保存的项目', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/phase-one/save/${this.currentTaskId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('保存失败');
            }

            const result = await response.json();
            if (result.success) {
                this.showToast('项目保存成功！', 'success');
            } else {
                throw new Error(result.error || '保存失败');
            }

        } catch (error) {
            console.error('保存项目失败:', error);
            this.showToast(`保存失败: ${error.message}`, 'error');
        }
    }

    regenerate() {
        if (!this.currentTaskId) {
            this.showToast('没有可重新生成的任务', 'error');
            return;
        }

        if (confirm('确定要重新生成吗？这将覆盖当前的结果。')) {
            // 重置UI状态
            this.hideResults();
            this.showProgress();
            this.updateProgressMessage('正在重新启动生成任务...');
            
            // 重新启动生成
            const formData = this.collectFormData();
            this.handleFormSubmit({ preventDefault: () => {} });
        }
    }

    togglePause() {
        // 这里可以实现暂停功能
        this.showToast('暂停功能开发中...', 'info');
    }

    onModeChange(event) {
        const mode = event.target.value;
        const totalChaptersInput = document.getElementById('total-chapters');
        
        if (mode === 'phase_one_only') {
            // 仅第一阶段模式，建议较少章节数
            if (totalChaptersInput && parseInt(totalChaptersInput.value) > 100) {
                totalChaptersInput.value = 200;
                this.showToast('已调整为建议的章节数', 'info');
            }
        } else {
            // 完整两阶段模式
            this.showToast('将生成完整的设定和章节内容', 'info');
        }
    }

    resetForm() {
        if (confirm('确定要重置所有输入内容吗？')) {
            document.getElementById('phase-one-form').reset();
            this.setDefaultValues();
            this.hideResults();
            this.hideProgress();
            this.currentTaskId = null;
            this.isGenerating = false;
            this.showToast('表单已重置', 'success');
        }
    }

    showProgress() {
        const progressSection = document.getElementById('progress-section');
        if (progressSection) {
            progressSection.style.display = 'block';
        }
    }

    hideProgress() {
        const progressSection = document.getElementById('progress-section');
        if (progressSection) {
            progressSection.style.display = 'none';
        }
    }

    hideResults() {
        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }

    updateProgressMessage(message) {
        const progressMessage = document.getElementById('progress-message');
        if (progressMessage) {
            progressMessage.textContent = message;
        }
    }

    showToast(message, type = 'info') {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) return;

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;

        toastContainer.appendChild(toast);

        // 自动移除
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 5000);
    }

    // 清理资源
    destroy() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        this.isGenerating = false;
        this.currentTaskId = null;
    }
}

// 全局函数，供外部调用
window.PhaseOneSetup = PhaseOneSetup;

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
    if (window.phaseOneSetup) {
        window.phaseOneSetup.destroy();
    }
});