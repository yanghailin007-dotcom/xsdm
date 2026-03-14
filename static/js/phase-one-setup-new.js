// ==================== 分阶段生成页面功能 ====================

class PhaseOneSetup {
    constructor() {
        this.currentTaskId = null;
        this.progressInterval = null;
        this.isGenerating = false;
        this.estimatedPoints = 0;  // 预估消耗点数
    }

    static init() {
        console.log('🚀 [PhaseOneSetup] 开始初始化');
        const instance = new PhaseOneSetup();
        console.log('✅ [PhaseOneSetup] 实例创建成功');
        instance.bindEvents();
        console.log('✅ [PhaseOneSetup] 事件绑定完成');
        instance.initializeUI();
        console.log('✅ [PhaseOneSetup] UI初始化完成');
        return instance;
    }

    bindEvents() {
        console.log('🔧 [PhaseOneSetup] 开始绑定事件');
        
        // 表单提交事件 - 使用捕获阶段确保最早处理
        const form = document.getElementById('phase-one-form');
        if (form) {
            console.log('✅ [PhaseOneSetup] 找到表单元素，绑定submit事件');
            form.addEventListener('submit', (e) => {
                console.log('🚀 [PhaseOneSetup] 表单submit事件触发，准备阻止默认行为');
                e.preventDefault();
                e.stopPropagation();
                console.log('✅ [PhaseOneSetup] 默认行为已阻止，准备处理提交');
                this.handleFormSubmit(e);
            }, true); // 使用捕获阶段
        } else {
            console.error('❌ [PhaseOneSetup] 未找到表单元素 #phase-one-form');
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
        console.log('🚀 [DEBUG] =================== handleFormSubmit 被调用 ===================');
        
        // 确保阻止默认表单提交
        if (event) {
            event.preventDefault();
            event.stopPropagation();
            console.log('✅ [DEBUG] event.preventDefault() 和 stopPropagation() 已执行');
        } else {
            console.warn('⚠️ [DEBUG] event 参数为空');
        }
        
        // 防止重复提交
        if (this.isGenerating) {
            console.log('⚠️ [DEBUG] 已有任务在生成中，忽略此次请求');
            this.showToast('正在生成中，请稍候...', 'warning');
            return false;
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

            // 💰 检查创造点余额
            console.log('💰 [DEBUG] 开始检查创造点余额');
            let hasEnoughPoints = false;
            try {
                hasEnoughPoints = await this.checkPointsBalance();
                console.log('💰 [DEBUG] 余额检查结果:', hasEnoughPoints);
            } catch (balanceError) {
                console.error('❌ [DEBUG] 检查余额时发生异常:', balanceError);
                this.showToast('检查余额失败，请刷新页面重试', 'error');
                return;
            }
            
            if (!hasEnoughPoints) {
                console.log('❌ [DEBUG] 创造点余额不足，停止提交');
                return;
            }
            console.log('✅ [DEBUG] 创造点余额充足，继续提交');

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
                
                // 🔥 处理 401 未授权错误
                if (response.status === 401 || errorData.code === 'AUTH_REQUIRED') {
                    console.error('🔐 [DEBUG] 用户未登录，需要重新登录');
                    this.showToast('请先登录后再试', 'error');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                    return;
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
                
                // 保存后端返回的预估点数
                if (result.points_estimated || result.points_spent) {
                    this.estimatedPoints = result.points_estimated || result.points_spent;
                    console.log('💰 [DEBUG] 后端返回预估点数:', this.estimatedPoints);
                }
                
                // 立即更新点数显示
                this.updatePointsCost(0, this.estimatedPoints);
                
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

    // 💰 检查创造点余额 - 调用后端API获取准确预估
    async checkPointsBalance() {
        try {
            console.log('💰 [DEBUG] 开始检查创造点余额');
            
            // 获取用户余额
            const balanceResponse = await fetch('/api/points/balance');
            console.log('📥 [DEBUG] 余额查询响应:', balanceResponse.status);
            
            if (!balanceResponse.ok) {
                if (balanceResponse.status === 401) {
                    console.error('🔐 [DEBUG] 用户未登录，需要重新登录');
                    this.showToast('请先登录后再试', 'error');
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                    return false;
                }
                throw new Error('无法获取余额信息');
            }
            
            const balanceData = await balanceResponse.json();
            // 后端返回格式: { success: true, data: { balance: xxx } }
            // 兼容处理：优先从 data.balance 获取，如果不存在则尝试从 balance 获取
            const balance = (balanceData.data?.balance ?? balanceData.balance) || 0;
            console.log('💰 [DEBUG] 当前余额:', balance);
            
            // 从后端获取准确的预估消耗
            const totalChapters = parseInt(document.getElementById('total-chapters')?.value) || 200;
            const generationMode = document.getElementById('generation-mode')?.value || 'phase_one_only';
            
            // 调用后端API计算预估点数
            const estimateResponse = await fetch('/api/points/estimate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    action: 'phase1',
                    params: {
                        total_chapters: totalChapters,
                        estimated_characters: 4
                    }
                })
            });
            
            let estimatedPoints = 33; // 默认值
            if (estimateResponse.ok) {
                const estimateData = await estimateResponse.json();
                if (estimateData.success && estimateData.data) {
                    estimatedPoints = estimateData.data.estimated_cost || 33;
                    console.log('💰 [DEBUG] 从后端获取预估消耗:', estimatedPoints);
                    console.log('💰 [DEBUG] 费用明细:', estimateData.data.breakdown);
                }
            } else {
                console.warn('⚠️ [DEBUG] 无法从后端获取预估，使用默认值33');
                // 使用与后端一致的计算
                // planning:1 + worldview:3 + characters:2*4=8 + outline:chapters/10 + validation:1
                estimatedPoints = 1 + 3 + 8 + Math.floor(totalChapters / 10) + 1;
            }
            
            console.log('💰 [DEBUG] 预估消耗:', estimatedPoints);
            
            // 保存预估点数供后续使用
            this.estimatedPoints = estimatedPoints;
            
            if (balance < estimatedPoints) {
                const needed = estimatedPoints - balance;
                console.log('❌ [DEBUG] 余额不足，需要:', needed, '当前:', balance, '预估:', estimatedPoints);
                console.log('❌ [DEBUG] 准备显示余额不足弹窗');
                try {
                    this.showInsufficientPointsModal(needed, balance, estimatedPoints);
                    console.log('✅ [DEBUG] 余额不足弹窗显示成功');
                } catch (modalError) {
                    console.error('❌ [DEBUG] 显示弹窗失败:', modalError);
                    this.showToast(`创造点不足，需要${needed}点，请充值`, 'error');
                }
                return false;
            }
            
            console.log('✅ [DEBUG] 余额充足');
            return true;
            
        } catch (error) {
            console.error('❌ [DEBUG] 检查余额失败:', error);
            this.showToast('检查余额失败，请重试', 'error');
            return false;
        }
    }
    
    // 显示余额不足弹窗
    showInsufficientPointsModal(needed, balance, estimated) {
        console.log('🪟 [DEBUG] showInsufficientPointsModal 被调用', {needed, balance, estimated});
        
        // 参数检查
        needed = parseInt(needed) || 0;
        balance = parseInt(balance) || 0;
        estimated = parseInt(estimated) || 0;
        
        if (needed <= 0) {
            console.warn('⚠️ [DEBUG] 需要的点数为0或负数，不显示弹窗');
            return;
        }
        
        try {
            // 移除已存在的弹窗
            const existingModal = document.getElementById('insufficient-points-modal');
            if (existingModal) existingModal.remove();
            
            const modal = document.createElement('div');
            modal.id = 'insufficient-points-modal';
            modal.innerHTML = `
            <div style="
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(8px);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 99999;
            ">
                <div style="
                    background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
                    border: 2px solid #fbbf24;
                    border-radius: 1rem;
                    padding: 2rem;
                    max-width: 380px;
                    width: 90%;
                    text-align: center;
                ">
                    <div style="
                        width: 70px;
                        height: 70px;
                        margin: 0 auto 1.25rem;
                        background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                        border-radius: 50%;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 10px 25px rgba(251, 191, 36, 0.4);
                    ">
                        <span style="font-size: 2rem;">⚡</span>
                    </div>
                    
                    <h3 style="color: #fbbf24; margin-bottom: 1rem; font-size: 1.35rem; font-weight: 700;">
                        创造点余额不足
                    </h3>
                    
                    <div style="
                        background: rgba(0, 0, 0, 0.4);
                        border-radius: 0.75rem;
                        padding: 1rem;
                        margin-bottom: 1.25rem;
                        border: 1px solid rgba(255, 255, 255, 0.1);
                    ">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                            <span style="color: #94a3b8; font-size: 0.875rem;">当前余额</span>
                            <span style="color: #e2e8f0; font-size: 1rem; font-weight: 600;">${balance} 点</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                            <span style="color: #94a3b8; font-size: 0.875rem;">本次需要</span>
                            <span style="color: #fbbf24; font-size: 1rem; font-weight: 600;">${estimated} 点</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; padding-top: 0.25rem;">
                            <span style="color: #f87171; font-size: 0.875rem; font-weight: 500;">⚠️ 还差</span>
                            <span style="color: #ef4444; font-size: 1.25rem; font-weight: 700;">${needed} 点</span>
                        </div>
                    </div>
                    
                    <div style="display: flex; gap: 0.75rem;">
                        <button onclick="this.closest('#insufficient-points-modal').remove(); document.body.style.overflow = '';" style="
                            flex: 1;
                            padding: 0.875rem 1rem;
                            background: rgba(255, 255, 255, 0.08);
                            border: 1px solid rgba(255, 255, 255, 0.2);
                            border-radius: 0.5rem;
                            color: #94a3b8;
                            cursor: pointer;
                            font-size: 0.875rem;
                            font-weight: 500;
                        ">
                            取消
                        </button>
                        <button onclick="window.location.href = '/recharge';" style="
                            flex: 1.2;
                            padding: 0.875rem 1rem;
                            background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                            border: none;
                            border-radius: 0.5rem;
                            color: #0f172a;
                            cursor: pointer;
                            font-size: 0.875rem;
                            font-weight: 700;
                            box-shadow: 0 4px 15px rgba(251, 191, 36, 0.4);
                        ">
                            💎 立即充值
                        </button>
                    </div>
                </div>
            </div>
        `;
            document.body.appendChild(modal);
            document.body.style.overflow = 'hidden';
            console.log('✅ [DEBUG] 弹窗DOM元素已创建并添加到页面');
        } catch (error) {
            console.error('❌ [DEBUG] 创建弹窗失败:', error);
            // 降级方案：使用简单的alert
            alert(`创造点余额不足！\n当前余额: ${balance} 点\n本次需要: ${estimated} 点\n还差: ${needed} 点\n\n请前往充值页面充值。`);
            window.location.href = '/recharge';
        }
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

                const result = await response.json();
                console.log('📋 [DEBUG] 任务状态数据:', result);
                
                // 🔥 修复：后端返回的数据嵌套在 data 字段中
                const taskStatus = result.data || result;
                
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

        // 更新步骤指示器 - 传递详细状态
        this.updateProgressSteps(taskStatus.current_step, taskStatus.step_status);
        
        // 更新创造点消耗
        if (taskStatus.points_consumed !== undefined || taskStatus.points_cost) {
            const consumed = taskStatus.points_consumed || taskStatus.points_cost || 0;
            // 使用后端返回的预估点数，或本机保存的预估点数
            const estimated = taskStatus.points_estimated || taskStatus.points_total || this.estimatedPoints || 0;
            this.updatePointsCost(consumed, estimated);
        }
    }

    getStepMessage(step) {
        const stepMessages = {
            'initialization': '正在初始化生成环境...',
            // 🔥 优化：合并方案生成和评估步骤
            'creative_refinement': '正在精炼创意...',
            'fanfiction_detection': '正在检测同人文...',
            'multiple_plans': '正在生成并评估方案...',
            'detailed_stage_plans': '正在并行生成各阶段详细计划...',
            'freshness_assessment': '正在评估方案质量...',
            'quality_evaluation': '正在评估方案质量...',
            'plan_selection': '正在选择最佳方案...',
            // 核心生成阶段
            'writing_style': '正在生成写作风格...',
            'worldview': '正在生成世界观...',
            'worldview_generation': '正在生成世界观设定...',
            'character_design': '正在设计角色...',
            'character_generation': '正在生成角色设定...',
            'stage_plan': '正在规划阶段计划...',
            'stage_planning': '正在规划故事阶段...',
            'story_outline': '正在生成故事大纲...',
            'validation': '正在验证生成结果...',
            'completed': '生成完成！'
        };
        
        return stepMessages[step] || `正在处理: ${step}...`;
    }

    updateProgressSteps(currentStep, stepStatus = null) {
        // 步骤映射：API 返回的步骤名 -> HTML data-step 属性
        // 注意：以下是新流程的所有可能步骤
        const stepMapping = {
            // 初始化
            'initialization': 'planning',
            // 创意精炼阶段
            'creative_refinement': 'planning',
            // 同人文检测
            'fanfiction_detection': 'planning',
            // 多方案生成
            'multiple_plans': 'planning',
            // 方案评估
            'freshness_assessment': 'planning',
            'quality_evaluation': 'planning',
            'plan_selection': 'planning',
            // 核心生成阶段（合并优化）
            'writing_style': 'planning',
            'market_analysis': 'planning',
            'foundation_planning': 'planning',  // 合并步骤
            'planning': 'planning',
            'worldview_generation': 'worldview',
            'worldview': 'worldview',
            'faction_system': 'worldview',
            'worldview_with_factions': 'worldview',  // 合并步骤
            'character_design': 'characters',
            'character_generation': 'characters',
            'characters': 'characters',
            'stage_plan': 'planning-detailed',
            'stage_planning': 'planning-detailed',
            'story_outline': 'outlines',
            'outlines': 'outlines',
            'validation': 'validation',
            'completed': 'validation'
        };
        
        const stepOrder = [
            'planning',
            'worldview', 
            'characters',
            'planning-detailed',
            'outlines',
            'validation'
        ];
        
        const currentStepKey = stepMapping[currentStep] || currentStep;
        const currentIndex = stepOrder.indexOf(currentStepKey);
        
        // 更新步骤列表项
        const stepItems = document.querySelectorAll('.progress-step-item');
        let completedCount = 0;
        
        stepItems.forEach((item) => {
            const stepKey = item.dataset.step;
            const stepIndex = stepOrder.indexOf(stepKey);
            const statusBadge = item.querySelector('.step-status-badge');
            const icon = item.querySelector('.step-icon');
            
            if (stepStatus && stepStatus[stepKey]) {
                // 使用服务器返回的详细状态
                const status = stepStatus[stepKey];
                item.dataset.status = status;
                
                if (status === 'completed') {
                    statusBadge.textContent = '已完成';
                    icon.textContent = '✓';
                    completedCount++;
                } else if (status === 'running') {
                    statusBadge.textContent = '进行中';
                    icon.textContent = '⏳';
                } else if (status === 'failed') {
                    statusBadge.textContent = '失败';
                    icon.textContent = '✗';
                } else {
                    statusBadge.textContent = '等待中';
                    icon.textContent = '⏳';
                }
            } else {
                // 使用简单的进度计算
                if (stepIndex < currentIndex) {
                    item.dataset.status = 'completed';
                    statusBadge.textContent = '已完成';
                    icon.textContent = '✓';
                    completedCount++;
                } else if (stepIndex === currentIndex) {
                    item.dataset.status = 'running';
                    statusBadge.textContent = '进行中';
                    icon.textContent = '⏳';
                } else {
                    item.dataset.status = 'waiting';
                    statusBadge.textContent = '等待中';
                    icon.textContent = '⏳';
                }
            }
        });
        
        // 更新步骤状态文本
        const stepsStatusEl = document.getElementById('steps-status');
        if (stepsStatusEl) {
            stepsStatusEl.textContent = `${completedCount}/${stepOrder.length} 完成`;
        }
        
        // 更新当前步骤详情
        this.updateCurrentStepDetail(currentStep);
    }
    
    updateCurrentStepDetail(currentStep) {
        const stepDetails = {
            // 新流程步骤（合并优化）
            'creative_refinement': {
                name: '✨ 创意精炼',
                desc: '正在将创意精炼为AI可执行的生成指令...'
            },
            'fanfiction_detection': {
                name: '🔍 同人文检测',
                desc: '正在检测是否为同人作品并评估合规性...'
            },
            'multiple_plans': {
                name: '🎯 方案生成',
                desc: '正在基于创意生成多个可行的小说方案...'
            },
            'freshness_assessment': {
                name: '🎯 方案评估',
                desc: '正在综合评估方案的质量和市场竞争力...'
            },
            'quality_evaluation': {
                name: '🎯 方案评估',
                desc: '正在综合评估方案的质量和市场竞争力...'
            },
            'plan_selection': {
                name: '✅ 方案选择',
                desc: '正在综合评估选择最佳方案...'
            },
            'foundation_planning': {
                name: '📋 基础规划',
                desc: '正在合并生成写作风格指南和市场分析...'
            },
            'writing_style': {
                name: '✍️ 写作风格',
                desc: '正在生成符合市场定位的写作风格指南...'
            },
            'planning': {
                name: '📋 基础规划',
                desc: '正在分析创意种子，制定写作风格和市场定位...'
            },
            'worldview_generation': {
                name: '🌍 世界观设计',
                desc: '正在构建完整的世界观和背景设定...'
            },
            'worldview': {
                name: '🌍 世界观设计',
                desc: '正在构建完整的世界观和背景设定...'
            },
            'worldview_with_factions': {
                name: '🌍 世界观与势力',
                desc: '正在合并生成世界观框架和势力系统...'
            },
            'character_design': {
                name: '👥 角色设计',
                desc: '正在设计主要角色和人物关系...'
            },
            'character_generation': {
                name: '👥 角色生成',
                desc: '正在生成详细的角色设定...'
            },
            'characters': {
                name: '👥 角色设计',
                desc: '正在设计主要角色和人物关系...'
            },
            'stage_plan': {
                name: '📅 阶段规划',
                desc: '正在规划全书的阶段结构和情节节奏...'
            },
            'stage_planning': {
                name: '📅 阶段规划',
                desc: '正在规划全书的阶段结构和情节节奏...'
            },
            'detailed_stage_plans': {
                name: '📅 阶段详细计划',
                desc: '正在并行生成4个阶段的详细写作计划（起承转合）...'
            },
            'story_outline': {
                name: '📝 详细规划',
                desc: '正在制定情绪蓝图和阶段计划...'
            },
            'outlines': {
                name: '📚 章节大纲',
                desc: '正在生成详细的章节情节大纲...'
            },
            'validation': {
                name: '✅ 验证完善',
                desc: '正在验证设定完整性和一致性...'
            },
            'completed': {
                name: '✅ 生成完成',
                desc: '所有步骤已完成！'
            },
            'initialization': {
                name: '🚀 初始化',
                desc: '正在初始化生成环境...'
            }
        };
        
        const detail = stepDetails[currentStep] || { name: '处理中...', desc: '' };
        
        const nameEl = document.getElementById('current-step-name');
        const descEl = document.getElementById('current-step-desc');
        
        if (nameEl) nameEl.textContent = detail.name;
        if (descEl) descEl.textContent = detail.desc;
    }
    
    updatePointsCost(consumed, estimated) {
        const consumedEl = document.getElementById('points-consumed');
        const estimatedEl = document.getElementById('points-estimated');
        
        if (consumedEl) {
            // 数字动画
            const current = parseInt(consumedEl.textContent) || 0;
            this.animateNumber(current, consumed, consumedEl);
        }
        if (estimatedEl) estimatedEl.textContent = estimated || this.estimatedPoints || 0;
    }
    
    animateNumber(from, to, element) {
        const duration = 500;
        const start = performance.now();
        
        const animate = (now) => {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(from + (to - from) * easeProgress);
            
            element.textContent = current;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
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
        // 优先使用详细进度区域，如果没有则使用loading-overlay
        const progressSection = document.getElementById('progress-section');
        const loadingOverlay = document.getElementById('loading-overlay');
        
        if (progressSection) {
            progressSection.style.display = 'block';
            progressSection.classList.add('active');
        } else if (loadingOverlay) {
            loadingOverlay.classList.add('active');
        }
        
        // 初始化创造点显示（使用预估点数或默认值）
        const estimated = this.estimatedPoints || 33;
        this.updatePointsCost(0, estimated);
        
        // 初始化步骤状态
        this.updateProgressSteps('initialization');
        
        // 重置当前步骤详情
        this.updateCurrentStepDetail('initialization');
    }

    hideProgress() {
        const progressSection = document.getElementById('progress-section');
        const loadingOverlay = document.getElementById('loading-overlay');
        
        if (progressSection) {
            progressSection.style.display = 'none';
        } else if (loadingOverlay) {
            loadingOverlay.classList.remove('active');
        }
    }

    hideResults() {
        const resultsSection = document.getElementById('results-section');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }

    updateProgressMessage(message) {
        // 优先使用详细进度消息区域
        const progressMessage = document.getElementById('progress-message');
        if (progressMessage) {
            progressMessage.textContent = message;
        }
        
        // 同时更新loading-overlay中的文本（如果存在）
        const loadingText = document.getElementById('loading-text');
        if (loadingText) {
            loadingText.textContent = message;
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