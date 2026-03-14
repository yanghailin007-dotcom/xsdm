// ==================== 第一阶段生成功能 ====================
let currentTaskId = null;
let progressInterval = null;
let phaseOneResult = null;
let estimatedPoints = 0;  // 预估点数
let pointsCheckInterval = null;  // 点数轮询间隔

// 详细步骤映射（14个步骤）- 对应实际的设定生成流程
const DETAILED_STEP_ORDER = [
    'creative_refinement',      // 1. 创意精炼
    'fanfiction_detection',     // 2. 同人检测
    'multiple_plans',           // 3. 生成多个方案
    'plan_selection',           // 4. 选择最佳方案
    'foundation_planning',      // 5. 基础规划（写作风格+市场分析）
    'worldview_with_factions',  // 6. 世界观与势力系统
    'character_design',         // 7. 核心角色设计
    'emotional_growth_planning', // 8. 情绪蓝图与成长规划
    'stage_plan',               // 9. 全书阶段计划
    'detailed_stage_plans',     // 10. 阶段详细计划
    'expectation_mapping',      // 11. 期待感映射
    'system_init',              // 12. 系统初始化
    'saving',                   // 13. 保存设定结果
    'quality_assessment'        // 14. AI质量评估
];

// 步骤名称映射（14个步骤）
const STEP_NAMES = {
    'creative_refinement': '✨ 创意精炼',
    'fanfiction_detection': '🔍 同人检测',
    'multiple_plans': '📋 生成多个方案',
    'plan_selection': '🎯 选择最佳方案',
    'foundation_planning': '📝 基础规划',
    'worldview_with_factions': '🌍 世界观与势力',
    'character_design': '👥 核心角色设计',
    'emotional_growth_planning': '💫 情绪与成长规划',
    'stage_plan': '📚 全书阶段计划',
    'detailed_stage_plans': '📖 阶段详细计划',
    'expectation_mapping': '🎯 期待感映射',
    'system_init': '🔧 系统初始化',
    'saving': '💾 保存设定结果',
    'quality_assessment': '✅ AI质量评估',
    // 兼容旧步骤名
    'writing_style': '📝 写作风格制定',
    'market_analysis': '📊 市场分析',
    'worldview': '🌍 世界观构建',
    'faction_system': '⚔️ 势力系统设计',
    'emotional_blueprint': '💫 情绪蓝图规划',
    'growth_plan': '📈 成长规划'
};

async function startPhaseOneGeneration(event) {
    event.preventDefault();

    const modeSelect = document.getElementById('generation-mode');
    const isResumeMode = modeSelect && modeSelect.value === 'resume_mode';

    const formData = {
        title: document.getElementById('novel-title').value,
        synopsis: document.getElementById('novel-synopsis').value,
        core_setting: document.getElementById('core-setting').value,
        core_selling_points: document.getElementById('core-selling-points').value,
        total_chapters: parseInt(document.getElementById('total-chapters').value),
        generation_mode: modeSelect ? modeSelect.value : 'phase_one_only',
        target_platform: document.getElementById('target-platform').value || 'fanqie',
        creative_seed: selectedCreativeId ? loadedCreativeIdeas.find(i => i.id === selectedCreativeId)?.raw_data : null,
        // 🔥 关键修复：非恢复模式下，明确告知后端从头开始，不要检查检查点
        start_new: !isResumeMode
    };
    
    console.log(`🎯 生成模式: ${formData.generation_mode}, 从头开始: ${formData.start_new}`);

    console.log('🎯 目标平台:', formData.target_platform);

    try {
        // 显示进度区域
        showProgressSection();
        updateProgress(5, '正在启动第一阶段生成...');
        
        // 重置所有步骤状态
        resetAllSteps();

        // 调用第一阶段生成API
        const response = await fetch('/api/phase-one/start-generation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        if (response.status === 401) {
            showStatusMessage('❌ 请先登录后再试', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            currentTaskId = result.task_id;
            estimatedPoints = result.points_spent || 0;  // 保存预估点数
            
            // 初始化点数显示
            updatePointsDisplay(0, estimatedPoints);
            
            // 开始轮询进度
            progressInterval = setInterval(() => {
                updateProgressStatus(currentTaskId);
            }, 2000);
            
            updateStepStatus('generation', true);
        } else {
            throw new Error(result.error || '启动生成失败');
        }
    } catch (error) {
        // 显示错误但不隐藏进度区域，让用户可以看到错误信息
        showStatusMessage(`❌ 错误: ${error.message}`, 'error');
        console.error('第一阶段生成失败:', error);
        
        // 更新进度消息显示错误
        const progressMessage = document.getElementById('progress-message');
        if (progressMessage) {
            progressMessage.textContent = `❌ ${error.message}`;
            progressMessage.style.color = '#ef4444';
        }
    }
}

// 更新生成进度状态
async function updateProgressStatus(taskId) {
    try {
        console.log(`[DEBUG] 查询任务状态: ${taskId}`);
        const response = await fetch(`/api/phase-one/task/${taskId}/status`);
        if (!response.ok) {
            console.warn(`[DEBUG] 状态查询失败: ${response.status}`);
            return;
        }

        const result = await response.json();
        console.log(`[DEBUG] 收到状态更新:`, result);
        
        // 🔥 修复：后端返回的数据嵌套在 data 字段中
        const taskStatus = result.data || result;
        
        // 更新进度条和百分比
        updateProgress(taskStatus.progress || 0, taskStatus.message || taskStatus.status_message || '生成中...');

        // 更新详细步骤状态（如果后端返回了step_status）
        if (taskStatus.step_status && Object.keys(taskStatus.step_status).length > 0) {
            console.log(`[DEBUG] 更新详细步骤状态:`, taskStatus.step_status);
            updateDetailedStepStatus(taskStatus.step_status);
        } else {
            console.log(`[DEBUG] 无 step_status 或为空，跳过详细步骤更新`);
        }
        
        // 兼容旧版本，使用current_step
        if (taskStatus.current_step) {
            // 兼容旧版本，使用current_step
            console.log(`[DEBUG] 更新当前步骤: ${taskStatus.current_step}`);
            updateProgressSteps(taskStatus.current_step);
        }

        // 更新创造点消耗显示（实时）
        if (taskStatus.points_consumed !== undefined) {
            updatePointsDisplay(taskStatus.points_consumed, taskStatus.points_estimated || estimatedPoints);
        }

        // 更新当前步骤详情
        if (taskStatus.current_step) {
            updateCurrentStepDetail(taskStatus.current_step, taskStatus.message || taskStatus.status_message);
        }

        // 检查是否完成
        if (taskStatus.status === 'completed') {
            clearInterval(progressInterval);
            handlePhaseOneComplete(taskStatus);
        } else if (taskStatus.status === 'failed') {
            clearInterval(progressInterval);
            handlePhaseOneFailed(taskStatus);
        }
    } catch (error) {
        console.error('获取进度状态失败:', error);
    }
}

// 更新详细步骤状态
function updateDetailedStepStatus(stepStatus) {
    console.log(`[DEBUG] updateDetailedStepStatus 被调用:`, stepStatus);
    
    // 防御性检查：确保 stepStatus 是有效对象
    if (!stepStatus || typeof stepStatus !== 'object' || Object.keys(stepStatus).length === 0) {
        console.warn(`[DEBUG] stepStatus 为空或无效，跳过更新`);
        return;
    }
    
    // stepStatus 是一个对象，键是步骤名，值是状态
    let activeStepFound = false;
    
    for (const [stepName, status] of Object.entries(stepStatus)) {
        const stepElement = document.querySelector(`[data-step="${stepName}"]`);
        console.log(`[DEBUG] 查找步骤 ${stepName}:`, stepElement ? '找到' : '未找到');
        if (stepElement) {
            stepElement.setAttribute('data-status', status);
            const badge = stepElement.querySelector('.step-status-badge');
            const icon = stepElement.querySelector('.step-icon');
            const text = stepElement.querySelector('span:nth-child(2)');
            
            const statusText = {
                'waiting': '等待中',
                'active': '进行中',
                'completed': '已完成',
                'failed': '失败'
            };
            
            // 更新状态文本
            if (badge) badge.textContent = statusText[status] || status;
            
            // 更新图标
            if (icon) {
                if (status === 'completed') {
                    icon.textContent = '✅';
                } else if (status === 'failed') {
                    icon.textContent = '❌';
                } else if (status === 'active') {
                    icon.textContent = '⚡';
                    activeStepFound = true;
                } else {
                    icon.textContent = '⏳';
                }
            }
            
            // 更新样式
            if (status === 'completed') {
                stepElement.style.background = 'rgba(34, 197, 94, 0.1)';
                stepElement.style.borderColor = 'rgba(34, 197, 94, 0.3)';
                if (text) text.style.color = 'var(--v2-accent-green, #22c55e)';
                if (badge) badge.style.color = 'var(--v2-accent-green, #22c55e)';
            } else if (status === 'active') {
                stepElement.style.background = 'rgba(99, 102, 241, 0.15)';
                stepElement.style.borderColor = 'var(--v2-primary-500, #6366f1)';
                if (text) text.style.color = 'var(--v2-text-primary, #fafafa)';
                if (badge) badge.style.color = 'var(--v2-primary-400, #818cf8)';
            } else if (status === 'failed') {
                stepElement.style.background = 'rgba(239, 68, 68, 0.1)';
                stepElement.style.borderColor = 'rgba(239, 68, 68, 0.3)';
                if (text) text.style.color = 'var(--v2-accent-red, #ef4444)';
                if (badge) badge.style.color = 'var(--v2-accent-red, #ef4444)';
            } else {
                // waiting
                stepElement.style.background = 'rgba(255,255,255,0.03)';
                stepElement.style.borderColor = 'rgba(255,255,255,0.06)';
                if (text) text.style.color = 'var(--v2-text-secondary, #a1a1aa)';
                if (badge) badge.style.color = 'var(--v2-text-tertiary, #71717a)';
            }
        }
    }
    
    // 计算并更新完成步骤数
    const completedSteps = Object.values(stepStatus).filter(s => s === 'completed').length;
    const totalSteps = DETAILED_STEP_ORDER.length;
    const stepsStatusEl = document.getElementById('steps-status');
    if (stepsStatusEl) {
        stepsStatusEl.textContent = `${completedSteps}/${totalSteps} 完成`;
    }
}

// 更新创造点显示
function updatePointsDisplay(consumed, estimated) {
    const consumedEl = document.getElementById('points-consumed');
    const estimatedEl = document.getElementById('points-estimated');
    
    if (consumedEl) consumedEl.textContent = consumed;
    if (estimatedEl) estimatedEl.textContent = estimated;
}

// 更新当前步骤详情
function updateCurrentStepDetail(stepName, message) {
    const nameEl = document.getElementById('current-step-name');
    const descEl = document.getElementById('current-step-desc');
    
    if (nameEl) {
        nameEl.textContent = STEP_NAMES[stepName] || stepName;
    }
    if (descEl && message) {
        descEl.textContent = message;
    }
}

// 更新进度条
function updateProgress(percentage, message) {
    console.log(`[DEBUG] updateProgress: ${percentage}% - ${message}`);
    const progressBar = document.getElementById('progress-bar-fill');
    const percentageText = document.getElementById('progress-percentage');
    const progressMessage = document.getElementById('progress-message');
    
    console.log(`[DEBUG] progressBar:`, progressBar, 'percentageText:', percentageText, 'progressMessage:', progressMessage);
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        console.log(`[DEBUG] 进度条已更新: ${percentage}%`);
    }
    if (percentageText) {
        percentageText.textContent = `${percentage}%`;
        console.log(`[DEBUG] 百分比文本已更新: ${percentage}%`);
    }
    if (progressMessage && message) {
        progressMessage.textContent = message;
        console.log(`[DEBUG] 进度消息已更新: ${message}`);
    }
}

// 更新进度步骤
function updateProgressSteps(currentStep) {
    const steps = document.querySelectorAll('.progress-step');
    const stepMapping = {
        'planning': 0,
        'worldview': 1,
        'characters': 2,
        'planning-detailed': 3,
        'outlines': 4,
        'validation': 5
    };

    const currentStepIndex = stepMapping[currentStep];
    if (currentStepIndex !== undefined) {
        steps.forEach((step, index) => {
            step.classList.remove('active');
            if (index < currentStepIndex) {
                step.classList.add('completed');
            } else if (index === currentStepIndex) {
                step.classList.add('active');
            }
        });
    }
}

// 处理第一阶段完成
function handlePhaseOneComplete(taskStatus) {
    hideProgressSection();
    updateStepStatus('preview', true);
    
    phaseOneResult = taskStatus.result;
    
    // 存储结果到 localStorage，确保刷新页面后按钮仍然可用
    if (phaseOneResult && phaseOneResult.novel_title) {
        localStorage.setItem('phaseOneResult', JSON.stringify(phaseOneResult));
        localStorage.setItem('lastNovelTitle', phaseOneResult.novel_title);
    }
    
    showResultsSection(phaseOneResult);
    showStatusMessage('✅ 第一阶段设定生成完成！', 'success');
    
    // 根据生成模式决定下一步操作
    const generationMode = document.getElementById('generation-mode').value;
    if (generationMode === 'full_two_phase') {
        // 自动继续第二阶段
        setTimeout(() => {
            continueToPhaseTwo();
        }, 2000);
    }
}

// 处理第一阶段失败
function handlePhaseOneFailed(taskStatus) {
    hideProgressSection();
    showStatusMessage(`❌ 第一阶段生成失败: ${taskStatus.error || '未知错误'}`, 'error');
    updateStepStatus('input', true);
}

// 显示结果区域
function showResultsSection(result) {
    const resultsSection = document.getElementById('results-section');
    resultsSection.classList.add('active');
    
    // 填充结果数据
    fillOverviewResult(result);
    fillWorldviewResult(result);
    fillCharactersResult(result);
    fillOutlinesResult(result);
    fillValidationResult(result);
}

// 填充总览结果
function fillOverviewResult(result) {
    const overviewContent = document.getElementById('overview-content');
    overviewContent.innerHTML = `
        <div class="result-item">
            <h4>📚 小说信息</h4>
            <p><strong>标题:</strong> ${result.novel_title || '未命名'}</p>
            <p><strong>简介:</strong> ${result.novel_synopsis || '暂无简介'}</p>
            <p><strong>总章节数:</strong> ${result.total_chapters || 0} 章</p>
        </div>
        <div class="result-item">
            <h4>📊 生成统计</h4>
            <p><strong>生成时间:</strong> ${new Date().toLocaleString()}</p>
            <p><strong>状态:</strong> <span style="color: #10b981;">✅ 生成完成</span></p>
            <p><strong>下一步:</strong> 可以继续第二阶段章节生成</p>
        </div>
    `;
}

// 填充世界观数据
function fillWorldviewResult(result) {
    const worldviewContent = document.getElementById('worldview-content');
    const worldview = result.core_worldview || {};
    
    worldviewContent.innerHTML = `
        <div class="result-item">
            <h4>🌍 核心世界观</h4>
            <p>${typeof worldview === 'string' ? worldview : JSON.stringify(worldview, null, 2)}</p>
        </div>
    `;
}

// 填充角色数据
function fillCharactersResult(result) {
    const charactersContent = document.getElementById('characters-content');
    const characters = result.character_design || {};
    
    charactersContent.innerHTML = `
        <div class="result-item">
            <h4>👥 角色设计</h4>
            <p>${typeof characters === 'string' ? characters : JSON.stringify(characters, null, 2)}</p>
        </div>
    `;
}

// 填充章节大纲
function fillOutlinesResult(result) {
    const outlinesContent = document.getElementById('outlines-content');
    const outlines = result.detailed_chapter_outlines || {};
    
    if (outlines.chapter_outlines && Array.isArray(outlines.chapter_outlines)) {
        let html = `<div class="result-item"><h4>📚 章节大纲 (${outlines.chapter_outlines.length} 章)</h4>`;
        
        // 只显示前10章作为预览
        const previewChapters = outlines.chapter_outlines.slice(0, 10);
        previewChapters.forEach(chapter => {
            html += `
                <div style="margin: 12px 0; padding: 12px; background: #f9fafb; border-radius: 6px;">
                    <strong>第${chapter.chapter_number}章: ${chapter.chapter_title}</strong>
                    <p style="margin: 8px 0 0 0; font-size: 14px; color: #6b7280;">
                        ${chapter.main_plot || '暂无描述'}
                    </p>
                </div>
            `;
        });
        
        if (outlines.chapter_outlines.length > 10) {
            html += `<p style="text-align: center; color: #6b7280;">... 还有 ${outlines.chapter_outlines.length - 10} 章</p>`;
        }
        
        html += '</div>';
        outlinesContent.innerHTML = html;
    } else {
        outlinesContent.innerHTML = `
            <div class="result-item">
                <h4>📚 章节大纲</h4>
                <p>${JSON.stringify(outlines, null, 2)}</p>
            </div>
        `;
    }
}

// 填充验证结果
function fillValidationResult(result) {
    const validationContent = document.getElementById('validation-content');
    const validation = result.validation_result || { is_valid: true, issues: [] };
    
    let html = `
        <div class="result-item">
            <h4>✅ 验证结果</h4>
            <p><strong>整体状态:</strong> 
                <span style="color: ${validation.is_valid ? '#10b981' : '#ef4444'};">
                    ${validation.is_valid ? '✅ 通过' : '❌ 有问题'}
                </span>
            </p>
    `;
    
    if (validation.issues && validation.issues.length > 0) {
        html += '<p><strong>发现问题:</strong></p><ul>';
        validation.issues.forEach(issue => {
            html += `<li style="color: #ef4444;">• ${issue}</li>`;
        });
        html += '</ul>';
    } else {
        html += '<p style="color: #10b981;">🎉 设定验证通过，可以继续第二阶段生成</p>';
    }
    
    html += '</div>';
    validationContent.innerHTML = html;
}

// ==================== 结果标签页切换 ====================
function switchResultTab(tabName) {
    // 更新标签状态
    const tabs = document.querySelectorAll('.result-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    event.target.classList.add('active');
    
    // 更新内容显示
    const contents = document.querySelectorAll('.result-content');
    contents.forEach(content => content.classList.remove('active'));
    document.getElementById(`result-${tabName}`).classList.add('active');
}

// ==================== 后续操作功能 ====================
async function continueToPhaseTwo() {
    // 优先使用内存中的结果，如果没有则尝试从 localStorage 读取
    let result = phaseOneResult;
    if (!result || !result.novel_title) {
        try {
            const savedResult = localStorage.getItem('phaseOneResult');
            if (savedResult) {
                result = JSON.parse(savedResult);
            }
        } catch (e) {
            console.error('读取 localStorage 失败:', e);
        }
    }
    
    if (!result || !result.novel_title) {
        showStatusMessage('❌ 没有有效的第一阶段结果，请重新生成', 'error');
        return;
    }
    
    // 使用读取到的结果
    phaseOneResult = result;

    try {
        showStatusMessage('🔄 正在准备第二阶段...', 'info');
        
        const response = await fetch(`/api/phase-one/continue-to-phase-two/${encodeURIComponent(phaseOneResult.novel_title)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                total_chapters: phaseOneResult.total_chapters || 200,
                chapters_per_batch: 3
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '继续第二阶段失败');
        }

        const result = await response.json();
        
        if (result.success) {
            showStatusMessage('✅ 正在跳转到第二阶段...', 'success');
            setTimeout(() => {
                window.location.href = '/phase-two-generation';
            }, 1500);
        } else {
            throw new Error(result.error || '操作失败');
        }
    } catch (error) {
        showStatusMessage(`❌ 继续第二阶段失败: ${error.message}`, 'error');
        console.error('继续第二阶段失败:', error);
    }
}

function saveAndContinue() {
    if (!phaseOneResult || !phaseOneResult.novel_title) {
        showStatusMessage('❌ 没有有效的第一阶段结果', 'error');
        return;
    }
    
    showStatusMessage('✅ 设定已保存，可以稍后继续', 'success');
    setTimeout(() => {
        window.location.href = '/project-management';
    }, 1500);
}

function editSettings() {
    showStatusMessage('📝 编辑功能开发中...', 'info');
}

function regenerateSettings() {
    if (confirm('确定要重新生成设定吗？当前的设定将被覆盖。')) {
        hideResultsSection();
        updateStepStatus('input', true);
        showStatusMessage('🔄 请重新配置生成参数', 'info');
    }
}

// 停止生成并返还剩余点数
async function stopGeneration() {
    if (!currentTaskId) {
        showStatusMessage('❌ 没有正在进行的生成任务', 'error');
        return;
    }
    
    // 🔥 使用 V2 风格的确认弹窗替代原生 confirm
    showStopConfirmModal();
}

// 🔥 显示 V2 风格的停止确认弹窗
function showStopConfirmModal() {
    // 移除已存在的弹窗
    const existingModal = document.getElementById('stop-confirm-modal');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'stop-confirm-modal';
    modal.innerHTML = `
        <div class="v2-dialog-overlay" onclick="if(event.target === this) closeStopConfirmModal(false)">
            <div class="v2-dialog-content" style="max-width: 480px;">
                <div class="v2-dialog-header" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">
                    <div class="v2-dialog-icon">🛑</div>
                    <h3 class="v2-dialog-title">确认停止生成</h3>
                    <p class="v2-dialog-subtitle">已生成的进度将被保存</p>
                </div>
                <div class="v2-dialog-body">
                    <div style="
                        background: rgba(239, 68, 68, 0.1);
                        border: 1px solid rgba(239, 68, 68, 0.2);
                        border-radius: 12px;
                        padding: 1.25rem;
                        margin-bottom: 1.5rem;
                        text-align: left;
                    ">
                        <p style="color: var(--v2-text-secondary); font-size: 0.95rem; line-height: 1.6; margin: 0 0 0.75rem 0;">
                            <strong style="color: var(--v2-text-primary);">💡 注意事项：</strong>
                        </p>
                        <ul style="color: var(--v2-text-secondary); font-size: 0.9rem; line-height: 1.7; margin: 0; padding-left: 1.25rem;">
                            <li>已消耗的创作点<strong style="color: var(--v2-text-primary);">不会返还</strong></li>
                            <li>未使用的预估点数将<strong style="color: var(--v2-accent-green);">返还到您的账户</strong></li>
                            <li>当前进度将被保存，您可以<strong style="color: var(--v2-primary-400);">稍后恢复生成</strong></li>
                        </ul>
                    </div>
                    <p style="color: var(--v2-text-tertiary); font-size: 0.85rem; text-align: center; margin: 0;">
                        停止后可以在生成模式下拉框选择"🔄 恢复模式"继续
                    </p>
                </div>
                <div class="v2-dialog-actions">
                    <button class="v2-btn v2-btn--secondary" onclick="closeStopConfirmModal(false)">
                        <span>取消，继续生成</span>
                    </button>
                    <button class="v2-btn v2-btn--primary" onclick="closeStopConfirmModal(true)" style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);">
                        <span>🛑 确认停止</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// 🔥 关闭停止确认弹窗
function closeStopConfirmModal(confirmed) {
    const modal = document.getElementById('stop-confirm-modal');
    if (modal) modal.remove();
    
    if (confirmed) {
        doStopGeneration();
    }
}

// 🔥 实际执行停止生成
async function doStopGeneration() {
    try {
        showStatusMessage('🛑 正在停止生成并返还剩余点数...', 'info');
        
        const response = await fetch(`/api/phase-one/task/${currentTaskId}/stop`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || '停止生成失败');
        }
        
        const result = await response.json();
        
        if (result.success) {
            // 清除轮询
            clearInterval(progressInterval);
            currentTaskId = null;
            
            // 显示成功消息
            const refundMsg = result.refunded_points > 0 
                ? `已返还 ${result.refunded_points} 创造点` 
                : '没有可返还的点数';
            showStatusMessage(`✅ 生成已停止！${refundMsg}。进度已保存，可以稍后恢复生成。`, 'success');
            
            // 🔥 修复：停止后停留在进度区域，不隐藏
            // 更新进度显示为已停止状态
            const progressMessage = document.getElementById('progress-message');
            const progressPercentage = document.getElementById('progress-percentage');
            
            if (progressMessage) {
                progressMessage.innerHTML = '<span style="color: var(--v2-accent-orange, #fbbf24);">⏸️ 生成已停止</span> - 进度已保存，可随时恢复';
            }
            if (progressPercentage) {
                progressPercentage.style.color = 'var(--v2-accent-orange, #fbbf24)';
            }
            
            // 更新步骤条状态
            updateStepStatus('generation', true);
            
            // 刷新用户点数显示
            if (typeof loadUserPointsBalance === 'function') {
                await loadUserPointsBalance();
            }
            
            // 显示恢复选项（V2 风格弹窗）
            if (result.checkpoint_info) {
                showResumeCheckpointModalV2(result.checkpoint_info);
            }
        } else {
            throw new Error(result.error || '停止生成失败');
        }
    } catch (error) {
        showStatusMessage(`❌ 停止生成失败: ${error.message}`, 'error');
        console.error('停止生成失败:', error);
    }
}

// 显示恢复生成选项弹窗（停止生成后使用）- V2 风格
function showResumeCheckpointModalV2(checkpointInfo) {
    if (!checkpointInfo) return;
    
    // 移除已存在的弹窗
    const existingModal = document.getElementById('resume-checkpoint-modal-v2');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'resume-checkpoint-modal-v2';
    modal.innerHTML = `
        <div class="v2-dialog-overlay" onclick="if(event.target === this) closeResumeCheckpointModalV2()">
            <div class="v2-dialog-content" style="max-width: 480px;">
                <div class="v2-dialog-header" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
                    <div class="v2-dialog-icon">💾</div>
                    <h3 class="v2-dialog-title">进度已保存</h3>
                    <p class="v2-dialog-subtitle">生成进度已保存到检查点</p>
                </div>
                <div class="v2-dialog-body">
                    <div style="
                        background: rgba(99, 102, 241, 0.1);
                        border: 1px solid rgba(99, 102, 241, 0.2);
                        border-radius: 12px;
                        padding: 1.25rem;
                        margin-bottom: 1.5rem;
                    ">
                        <div style="margin-bottom: 0.75rem;">
                            <span style="color: var(--v2-text-muted); font-size: 0.875rem;">项目名称</span>
                            <div style="color: var(--v2-text-primary); font-weight: 600; font-size: 1.1rem;">${escapeHtml(checkpointInfo.novel_title || '未命名')}</div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                            <div>
                                <span style="color: var(--v2-text-muted); font-size: 0.875rem;">当前步骤</span>
                                <div style="color: var(--v2-text-secondary);">${escapeHtml(checkpointInfo.current_step || '未知')}</div>
                            </div>
                            <div>
                                <span style="color: var(--v2-text-muted); font-size: 0.875rem;">保存时间</span>
                                <div style="color: var(--v2-text-secondary);">刚刚</div>
                            </div>
                        </div>
                    </div>
                    <p style="color: var(--v2-text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0;">
                        💡 您可以稍后从生成模式下拉框选择"🔄 恢复模式"继续生成，或点击"立即恢复"马上继续。
                    </p>
                </div>
                <div class="v2-dialog-actions">
                    <button class="v2-btn v2-btn--secondary" onclick="closeResumeCheckpointModalV2()">
                        <span>⏸️ 稍后继续</span>
                    </button>
                    <button class="v2-btn v2-btn--primary" onclick="resumeGenerationFromCheckpointV2('${checkpointInfo.novel_title}')" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
                        <span>🚀 立即恢复</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

// 关闭 V2 恢复弹窗
function closeResumeCheckpointModalV2() {
    const modal = document.getElementById('resume-checkpoint-modal-v2');
    if (modal) modal.remove();
}

// 从 V2 弹窗恢复生成
async function resumeGenerationFromCheckpointV2(novelTitle) {
    closeResumeCheckpointModalV2();
    await resumeGenerationFromCheckpoint(novelTitle);
}

// 兼容旧版本的恢复弹窗（空实现，使用 V2 版本）
function showResumeCheckpointModal(checkpointInfo) {
    showResumeCheckpointModalV2(checkpointInfo);
}

// HTML 转义辅助函数
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 关闭恢复弹窗（兼容旧版本和新版本）
window.closeResumeCheckpointModal = function() {
    // 关闭旧版本弹窗
    const oldModal = document.getElementById('resume-option-modal');
    if (oldModal) {
        oldModal.remove();
        document.body.style.overflow = '';
    }
    // 关闭 V2 弹窗
    closeResumeCheckpointModalV2();
};

// 从检查点恢复生成
async function resumeGenerationFromCheckpoint(novelTitle) {
    closeResumeCheckpointModal();
    showStatusMessage('🔄 正在恢复生成...', 'info');
    
    try {
        const response = await fetch('/api/phase-one/resume', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ novel_title: novelTitle })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || '恢复生成失败');
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentTaskId = result.task_id;
            estimatedPoints = result.estimated_points || 0;
            
            // 显示进度区域
            showProgressSection();
            updateProgress(result.progress || 0, '已从检查点恢复，继续生成...');
            
            // 初始化点数显示
            updatePointsDisplay(result.points_consumed || 0, estimatedPoints);
            
            // 开始轮询进度
            progressInterval = setInterval(() => {
                updateProgressStatus(currentTaskId);
            }, 2000);
            
            showStatusMessage('✅ 已恢复生成！', 'success');
        } else {
            throw new Error(result.error || '恢复生成失败');
        }
    } catch (error) {
        showStatusMessage(`❌ 恢复生成失败: ${error.message}`, 'error');
        console.error('恢复生成失败:', error);
    }
}

// ==================== 工具函数 ====================
function showProgressSection() {
    console.log('[DEBUG] showProgressSection 被调用');
    const formSection = document.getElementById('form-section');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    
    console.log('[DEBUG] formSection:', formSection, 'progressSection:', progressSection, 'resultsSection:', resultsSection);
    
    // 隐藏表单区域
    if (formSection) {
        formSection.style.display = 'none';
        console.log('[DEBUG] 表单区域已隐藏');
    }
    
    // 显示进度区域
    if (progressSection) {
        progressSection.classList.add('active');
        progressSection.classList.add('pt-progress-section--active');
        progressSection.style.display = 'block';
        console.log('[DEBUG] 进度区域已显示');
    }
    
    // 隐藏结果区域
    if (resultsSection) {
        resultsSection.classList.remove('active');
        resultsSection.classList.remove('pt-results-section--active');
    }
    
    // 更新步骤条状态
    updateStepStatus('generation', true);
    
    // 滚动到页面顶部，让用户看到进度
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideProgressSection() {
    const progressSection = document.getElementById('progress-section');
    
    if (progressSection) {
        progressSection.classList.remove('active');
        progressSection.classList.remove('pt-progress-section--active');
        progressSection.style.display = 'none';
    }
}

// 恢复到表单视图（生成失败时使用）
function showFormSection() {
    const formSection = document.getElementById('form-section');
    const progressSection = document.getElementById('progress-section');
    
    // 隐藏进度区域
    if (progressSection) {
        progressSection.classList.remove('active');
        progressSection.classList.remove('pt-progress-section--active');
        progressSection.style.display = 'none';
    }
    
    // 显示表单区域
    if (formSection) {
        formSection.style.display = 'block';
    }
}

// ==================== 步骤切换功能 ====================
function switchToStep(step) {
    console.log(`[DEBUG] switchToStep: ${step}`);
    
    const formSection = document.getElementById('form-section');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    
    switch(step) {
        case 'input':
            // 显示表单，隐藏进度和结果
            if (formSection) formSection.style.display = 'block';
            if (progressSection) {
                progressSection.classList.remove('active', 'pt-progress-section--active');
                progressSection.style.display = 'none';
            }
            if (resultsSection) {
                resultsSection.classList.remove('active', 'pt-results-section--active');
            }
            updateStepStatus('input', true);
            break;
            
        case 'generation':
            // 显示进度，隐藏表单（结果区域保持原状）
            if (formSection) formSection.style.display = 'none';
            if (progressSection) {
                progressSection.style.display = 'block';
                progressSection.classList.add('active', 'pt-progress-section--active');
            }
            updateStepStatus('generation', true);
            break;
            
        case 'preview':
            // 显示结果，隐藏表单和进度
            if (formSection) formSection.style.display = 'none';
            if (progressSection) {
                progressSection.classList.remove('active', 'pt-progress-section--active');
            }
            if (resultsSection) {
                resultsSection.classList.add('active', 'pt-results-section--active');
            }
            updateStepStatus('preview', true);
            break;
            
        case 'phase-two':
            // 跳转到第二阶段
            const title = document.getElementById('novel-title')?.value;
            if (title) {
                window.location.href = '/phase-two-generation?title=' + encodeURIComponent(title);
            } else {
                window.location.href = '/phase-two-generation';
            }
            return;
    }
    
    // 滚动到页面顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ==================== 返回表单功能 ====================
function showFormSection() {
    console.log('[DEBUG] showFormSection 被调用');
    // 使用新的步骤切换函数
    switchToStep('input');
}

function showResultsSection(result) {
    const formSection = document.getElementById('form-section');
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('results-section');
    
    // 隐藏进度区域
    if (progressSection) {
        progressSection.classList.remove('active');
        progressSection.classList.remove('pt-progress-section--active');
    }
    
    // 隐藏表单区域
    if (formSection) {
        formSection.style.display = 'none';
    }
    
    // 显示结果区域
    if (resultsSection) {
        resultsSection.classList.add('active');
        resultsSection.classList.add('pt-results-section--active');
    }
    
    updateStepStatus('preview', true);
    
    // 滚动到页面顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function hideResultsSection() {
    const formSection = document.getElementById('form-section');
    const resultsSection = document.getElementById('results-section');
    
    if (resultsSection) {
        resultsSection.classList.remove('active');
        resultsSection.classList.remove('pt-results-section--active');
    }
    
    // 恢复显示表单区域
    if (formSection) {
        formSection.style.display = 'block';
    }
}

function updateStepStatus(stepName, isActive) {
    const steps = ['input', 'generation', 'preview', 'complete'];
    const currentIndex = steps.indexOf(stepName);
    
    steps.forEach((step, index) => {
        const stepElement = document.getElementById(`step-${step}`);
        if (stepElement) {
            // 移除所有状态类
            stepElement.classList.remove('pt-step--active', 'pt-step--completed', 'pt-step--pending');
            
            if (index < currentIndex) {
                stepElement.classList.add('pt-step--completed');
            } else if (index === currentIndex && isActive) {
                stepElement.classList.add('pt-step--active');
            } else {
                stepElement.classList.add('pt-step--pending');
            }
        }
        
        // 更新连接线
        const connectorElement = document.getElementById(`connector-${step}`);
        if (connectorElement) {
            connectorElement.classList.remove('pt-step-connector--completed');
            if (index < currentIndex) {
                connectorElement.classList.add('pt-step-connector--completed');
            }
        }
    });
}

// 重置所有步骤状态
function resetAllSteps() {
    // 重置所有步骤为等待中
    DETAILED_STEP_ORDER.forEach(stepName => {
        const stepElement = document.querySelector(`[data-step="${stepName}"]`);
        if (stepElement) {
            stepElement.setAttribute('data-status', 'waiting');
            const badge = stepElement.querySelector('.step-status-badge');
            const icon = stepElement.querySelector('.step-icon');
            const text = stepElement.querySelector('span:nth-child(2)');
            
            if (badge) {
                badge.textContent = '等待中';
                badge.style.color = 'var(--v2-text-tertiary, #71717a)';
            }
            if (icon) icon.textContent = '⏳';
            if (text) text.style.color = 'var(--v2-text-secondary, #a1a1aa)';
            
            // 重置样式
            stepElement.style.background = 'rgba(255,255,255,0.03)';
            stepElement.style.borderColor = 'rgba(255,255,255,0.06)';
        }
    });
    
    // 重置步骤计数
    const stepsStatusEl = document.getElementById('steps-status');
    if (stepsStatusEl) {
        stepsStatusEl.textContent = '准备中';
    }
    
    // 重置点数显示
    updatePointsDisplay(0, 0);
    
    // 重置当前步骤详情
    const nameEl = document.getElementById('current-step-name');
    const descEl = document.getElementById('current-step-desc');
    if (nameEl) nameEl.textContent = '准备开始...';
    if (descEl) descEl.textContent = '正在初始化生成环境';
}

// 重置表单
function resetForm() {
    if (confirm('确定要重置表单吗？')) {
        document.getElementById('phase-one-form').reset();
        selectedCreativeId = null;
        
        // 重置列表视图
        const selectElement = document.getElementById('creative-idea-select');
        if (selectElement) {
            selectElement.value = '';
        }
        const previewSimpleElement = document.getElementById('creative-idea-preview-simple');
        if (previewSimpleElement) {
            previewSimpleElement.style.display = 'none';
        }
        
        // 重置卡片视图
        document.querySelectorAll('.creative-idea-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 收起所有展开的详情
        document.querySelectorAll('.creative-idea-details.expanded').forEach(details => {
            details.classList.remove('expanded');
        });
        document.querySelectorAll('.expand-details-btn').forEach(btn => {
            if (btn.textContent.includes('收起')) {
                btn.textContent = '📖 查看详情';
            }
        });
        
        showStatusMessage('🔄 表单已重置', 'info');
    }
}

// ==================== 页面加载时恢复活跃任务 ====================
async function restoreActiveTaskOnLoad() {
    console.log('[RESTORE] 检查是否有进行中的生成任务...');
    
    try {
        const response = await fetch('/api/phase-one/active-tasks');
        if (!response.ok) {
            console.warn('[RESTORE] 获取活跃任务失败:', response.status);
            return;
        }
        
        const result = await response.json();
        if (!result.success || !result.tasks || result.tasks.length === 0) {
            console.log('[RESTORE] 没有进行中的生成任务');
            return;
        }
        
        // 获取最新的活跃任务
        const activeTask = result.tasks[0];
        console.log('[RESTORE] 发现活跃任务:', activeTask);
        
        // 恢复任务状态
        currentTaskId = activeTask.task_id;
        
        // 显示恢复提示
        showStatusMessage(`🔄 检测到进行中的生成任务: ${activeTask.title}`, 'info');
        
        // 切换到进度区域
        switchToStep('generation');
        
        // 更新进度显示
        updateProgress(activeTask.progress || 0, `恢复任务: ${activeTask.current_step || '生成中...'}`);
        
        // 如果有小说标题，填充到表单
        if (activeTask.title && activeTask.title !== '未知') {
            const titleInput = document.getElementById('novel-title');
            if (titleInput && !titleInput.value) {
                titleInput.value = activeTask.title;
            }
        }
        
        // 开始轮询进度
        progressInterval = setInterval(() => {
            updateProgressStatus(currentTaskId);
        }, 2000);
        
        // 立即查询一次最新状态
        await updateProgressStatus(currentTaskId);
        
        console.log('[RESTORE] 任务恢复完成，开始轮询进度');
        
    } catch (error) {
        console.error('[RESTORE] 恢复活跃任务失败:', error);
    }
}

// 页面加载完成后检查活跃任务
document.addEventListener('DOMContentLoaded', function() {
    // 延迟执行，确保其他初始化完成
    setTimeout(restoreActiveTaskOnLoad, 1000);
});
// 🔥 兼容函数：phase-one-setup-new.html 使用的生成函数
// 这是 startPhaseOneGeneration 的别名，用于支持恢复模式
async function startPhaseOneGenerationWithResume(event) {
    return startPhaseOneGeneration(event);
}
