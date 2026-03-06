// ==================== 第一阶段生成功能 ====================
let currentTaskId = null;
let progressInterval = null;
let phaseOneResult = null;
let estimatedPoints = 0;  // 预估点数
let pointsCheckInterval = null;  // 点数轮询间隔

// 详细步骤映射（12个步骤）- 对应实际的设定生成流程
const DETAILED_STEP_ORDER = [
    'writing_style',           // 1. 写作风格制定
    'market_analysis',         // 2. 市场分析
    'worldview',               // 3. 世界观构建
    'faction_system',          // 4. 势力系统设计
    'character_design',        // 5. 核心角色设计
    'emotional_blueprint',     // 6. 情绪蓝图规划
    'growth_plan',             // 7. 成长规划
    'stage_plan',              // 8. 全书阶段计划
    'detailed_stage_plans',    // 9. 阶段详细计划
    'expectation_mapping',     // 10. 期待感映射
    'system_init',             // 11. 系统初始化
    'saving',                  // 12. 保存设定结果
    'quality_assessment'       // 13. AI质量评估
];

// 步骤名称映射
const STEP_NAMES = {
    'writing_style': '📝 写作风格制定',
    'market_analysis': '📊 市场分析',
    'worldview': '🌍 世界观构建',
    'faction_system': '⚔️ 势力系统设计',
    'character_design': '👥 核心角色设计',
    'emotional_blueprint': '💫 情绪蓝图规划',
    'growth_plan': '📈 成长规划',
    'stage_plan': '📚 全书阶段计划',
    'detailed_stage_plans': '📖 阶段详细计划',
    'expectation_mapping': '🎯 期待感映射',
    'system_init': '🔧 系统初始化',
    'saving': '💾 保存设定结果',
    'quality_assessment': '✅ AI质量评估'
};

async function startPhaseOneGeneration(event) {
    event.preventDefault();

    const formData = {
        title: document.getElementById('novel-title').value,
        synopsis: document.getElementById('novel-synopsis').value,
        core_setting: document.getElementById('core-setting').value,
        core_selling_points: document.getElementById('core-selling-points').value,
        total_chapters: parseInt(document.getElementById('total-chapters').value),
        generation_mode: document.getElementById('generation-mode').value,
        target_platform: document.getElementById('target-platform').value || 'fanqie',
        creative_seed: selectedCreativeId ? loadedCreativeIdeas.find(i => i.id === selectedCreativeId)?.raw_data : null
    };

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
        hideProgressSection();
        showStatusMessage(`❌ 错误: ${error.message}`, 'error');
        console.error('第一阶段生成失败:', error);
    }
}

// 更新生成进度状态
async function updateProgressStatus(taskId) {
    try {
        const response = await fetch(`/api/phase-one/task/${taskId}/status`);
        if (!response.ok) return;

        const taskStatus = await response.json();
        
        // 更新进度条和百分比
        updateProgress(taskStatus.progress || 0, taskStatus.status_message || '生成中...');

        // 更新详细步骤状态（如果后端返回了step_status）
        if (taskStatus.step_status) {
            updateDetailedStepStatus(taskStatus.step_status);
        } else if (taskStatus.current_step) {
            // 兼容旧版本，使用current_step
            updateProgressSteps(taskStatus.current_step);
        }

        // 更新创造点消耗显示（实时）
        if (taskStatus.points_consumed !== undefined) {
            updatePointsDisplay(taskStatus.points_consumed, taskStatus.points_estimated || estimatedPoints);
        }

        // 更新当前步骤详情
        if (taskStatus.current_step) {
            updateCurrentStepDetail(taskStatus.current_step, taskStatus.status_message);
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
    // stepStatus 是一个对象，键是步骤名，值是状态
    for (const [stepName, status] of Object.entries(stepStatus)) {
        const stepElement = document.querySelector(`[data-step="${stepName}"]`);
        if (stepElement) {
            stepElement.setAttribute('data-status', status);
            const badge = stepElement.querySelector('.step-status-badge');
            const icon = stepElement.querySelector('.step-icon');
            
            const statusText = {
                'waiting': '等待中',
                'active': '进行中',
                'completed': '已完成',
                'failed': '失败'
            };
            
            if (badge) badge.textContent = statusText[status] || status;
            if (icon) icon.textContent = status === 'completed' ? '✓' : status === 'failed' ? '✗' : '⏳';
        }
    }
    
    // 计算并更新完成步骤数
    const completedSteps = Object.values(stepStatus).filter(s => s === 'completed').length;
    const stepsStatusEl = document.getElementById('steps-status');
    if (stepsStatusEl) {
        stepsStatusEl.textContent = `${completedSteps}/${DETAILED_STEP_ORDER.length} 完成`;
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
    const progressBar = document.getElementById('progress-bar-fill');
    const percentageText = document.getElementById('progress-percentage');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (percentageText) {
        percentageText.textContent = `${percentage}%`;
    }
    
    console.log(`进度: ${percentage}% - ${message}`);
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
    if (!phaseOneResult || !phaseOneResult.novel_title) {
        showStatusMessage('❌ 没有有效的第一阶段结果', 'error');
        return;
    }

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
    
    // 确认对话框
    if (!confirm('确定要停止生成吗？\n\n已消耗的创作点不会返还，但未使用的预估点数将返还到您的账户。\n当前进度将被保存，您可以稍后恢复生成。')) {
        return;
    }
    
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
            
            // 隐藏进度区域
            hideProgressSection();
            
            // 刷新用户点数显示
            if (typeof loadUserPointsBalance === 'function') {
                await loadUserPointsBalance();
            }
            
            // 显示恢复选项
            showResumeOption(result.checkpoint_info);
        } else {
            throw new Error(result.error || '停止生成失败');
        }
    } catch (error) {
        showStatusMessage(`❌ 停止生成失败: ${error.message}`, 'error');
        console.error('停止生成失败:', error);
    }
}

// 显示恢复生成选项
function showResumeOption(checkpointInfo) {
    if (!checkpointInfo) return;
    
    // 创建恢复提示弹窗
    const resumeModal = document.createElement('div');
    resumeModal.id = 'resume-option-modal';
    resumeModal.innerHTML = `
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
                border: 2px solid #6366f1;
                border-radius: 1rem;
                padding: 2rem;
                max-width: 420px;
                width: 90%;
                text-align: center;
            ">
                <div style="
                    width: 70px;
                    height: 70px;
                    margin: 0 auto 1.25rem;
                    background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    box-shadow: 0 10px 25px rgba(99, 102, 241, 0.4);
                ">
                    <span style="font-size: 2rem;">💾</span>
                </div>
                
                <h3 style="color: #818cf8; margin-bottom: 1rem; font-size: 1.35rem; font-weight: 700;">
                    进度已保存
                </h3>
                
                <p style="color: #94a3b8; margin-bottom: 1.5rem; line-height: 1.6;">
                    生成进度已保存到检查点<br>
                    <strong style="color: #e2e8f0;">${checkpointInfo.novel_title || '未命名'}</strong><br>
                    当前步骤: ${checkpointInfo.current_step || '未知'}
                </p>
                
                <div style="display: flex; gap: 0.75rem;">
                    <button onclick="closeResumeModal()" style="
                        flex: 1;
                        padding: 0.875rem 1rem;
                        background: rgba(255, 255, 255, 0.08);
                        border: 1px solid rgba(255, 255, 255, 0.2);
                        border-radius: 0.5rem;
                        color: #94a3b8;
                        cursor: pointer;
                        font-size: 0.875rem;
                        font-weight: 500;
                    " onmouseover="this.style.background='rgba(255,255,255,0.15)';this.style.color='#e2e8f0'" 
                    onmouseout="this.style.background='rgba(255,255,255,0.08)';this.style.color='#94a3b8'">
                        稍后继续
                    </button>
                    <button onclick="resumeGeneration('${checkpointInfo.novel_title}')" style="
                        flex: 1.2;
                        padding: 0.875rem 1rem;
                        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
                        border: none;
                        border-radius: 0.5rem;
                        color: white;
                        cursor: pointer;
                        font-size: 0.875rem;
                        font-weight: 700;
                        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
                    " onmouseover="this.style.transform='translateY(-2px)';this.style.boxShadow='0 6px 20px rgba(99, 102, 241, 0.5)'" 
                    onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 4px 15px rgba(99, 102, 241, 0.4)'">
                        🚀 立即恢复
                    </button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(resumeModal);
    document.body.style.overflow = 'hidden';
}

// 关闭恢复弹窗
window.closeResumeModal = function() {
    const modal = document.getElementById('resume-option-modal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
};

// 恢复生成
async function resumeGeneration(novelTitle) {
    closeResumeModal();
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
    document.getElementById('progress-section').classList.add('active');
    document.getElementById('results-section').classList.remove('active');
}

function hideProgressSection() {
    document.getElementById('progress-section').classList.remove('active');
}

function showResultsSection(result) {
    hideProgressSection();
    document.getElementById('results-section').classList.add('active');
    updateStepStatus('preview', true);
}

function hideResultsSection() {
    document.getElementById('results-section').classList.remove('active');
}

function updateStepStatus(stepName, isActive) {
    const steps = ['input', 'generation', 'preview', 'complete'];
    const currentIndex = steps.indexOf(stepName);
    
    steps.forEach((step, index) => {
        const stepElement = document.getElementById(`step-${step}`);
        if (stepElement) {
            stepElement.classList.remove('active', 'completed');
            if (index < currentIndex) {
                stepElement.classList.add('completed');
            } else if (index === currentIndex && isActive) {
                stepElement.classList.add('active');
            } else {
                stepElement.classList.add('pending');
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
            if (badge) badge.textContent = '等待中';
            if (icon) icon.textContent = '⏳';
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