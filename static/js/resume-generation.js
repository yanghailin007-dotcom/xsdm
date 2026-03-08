/**
 * 恢复生成功能 - 简洁版
 * 在生成模式下拉框中添加恢复模式选项
 */

// 全局变量
let currentResumeInfo = null;

/**
 * 检查特定任务是否有可恢复的检查点
 */
async function checkTaskResumeStatus(title) {
    if (!title) {
        return null;
    }
    
    console.log(`🔍 [RESUME] 检查任务恢复状态: ${title}`);
    
    try {
        const response = await fetch(`/api/resumable-tasks/${encodeURIComponent(title)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            console.warn(`⚠️ [RESUME] API响应失败: ${response.status}`);
            return null;
        }
        
        const result = await response.json();
        
        if (result.success && result.resume_info) {
            console.log('✅ [RESUME] 发现可恢复的检查点:', result.resume_info);
            return result.resume_info;
        }
        
        console.log('ℹ️ [RESUME] 没有找到可恢复的检查点');
        return null;
        
    } catch (error) {
        console.error('❌ [RESUME] 检查任务恢复状态失败:', error);
        return null;
    }
}

/**
 * 显示恢复选项（在生成模式下拉框中）
 */
function showResumeOption(resumeInfo) {
    if (!resumeInfo) {
        return;
    }
    
    console.log('🎯 [RESUME] 显示恢复选项:', resumeInfo);
    currentResumeInfo = resumeInfo;
    
    // 在生成模式下拉框中显示恢复模式选项
    const resumeOption = document.getElementById('resume-mode-option');
    if (resumeOption) {
        resumeOption.style.display = 'block';
        resumeOption.textContent = `🔄 恢复模式（继续未完成的生成 - ${resumeInfo.progress_percentage}%）`;
        console.log('✅ [RESUME] 恢复模式选项已显示');
    } else {
        console.error('❌ [RESUME] 找不到 resume-mode-option 元素');
    }
}

/**
 * 清除恢复选项
 */
function clearResumeOption() {
    console.log('🧹 [RESUME] 清除恢复选项');
    currentResumeInfo = null;
    
    // 隐藏恢复模式选项
    const resumeOption = document.getElementById('resume-mode-option');
    if (resumeOption) {
        resumeOption.style.display = 'none';
        console.log('✅ [RESUME] 恢复模式选项已隐藏');
    }
    
    // 如果当前选中了恢复模式，切换回默认模式
    const modeSelect = document.getElementById('generation-mode');
    if (modeSelect && modeSelect.value === 'resume_mode') {
        modeSelect.value = 'phase_one_only';
        console.log('✅ [RESUME] 已切换回默认模式');
    }
}

/**
 * 检查是否启用恢复模式
 */
function isResumeModeEnabled() {
    const modeSelect = document.getElementById('generation-mode');
    return modeSelect && modeSelect.value === 'resume_mode' && currentResumeInfo;
}

/**
 * 处理生成模式变化
 */
function handleGenerationModeChange() {
    const modeSelect = document.getElementById('generation-mode');
    
    if (modeSelect.value === 'resume_mode') {
        if (!currentResumeInfo) {
            showResumeAlertModal('当前没有可恢复的任务', '请选择其他生成模式');
            modeSelect.value = 'phase_one_only';
            return;
        }
        
        // 显示 V2 风格的恢复确认弹窗
        showResumeConfirmModal(currentResumeInfo, modeSelect);
    }
}

/**
 * 显示 V2 风格的恢复确认弹窗
 */
function showResumeConfirmModal(resumeInfo, modeSelect) {
    // 移除已存在的弹窗
    const existingModal = document.getElementById('resume-confirm-modal');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'resume-confirm-modal';
    modal.innerHTML = `
        <div class="v2-dialog-overlay" onclick="if(event.target === this) closeResumeConfirmModal(false)">
            <div class="v2-dialog-content" style="max-width: 480px;">
                <div class="v2-dialog-header" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
                    <div class="v2-dialog-icon">🔄</div>
                    <h3 class="v2-dialog-title">恢复生成确认</h3>
                    <p class="v2-dialog-subtitle">继续未完成的创作任务</p>
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
                            <span style="color: var(--v2-text-muted); font-size: 0.875rem;">任务名称</span>
                            <div style="color: var(--v2-text-primary); font-weight: 600; font-size: 1.1rem;">${escapeHtml(resumeInfo.novel_title)}</div>
                        </div>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                            <div>
                                <span style="color: var(--v2-text-muted); font-size: 0.875rem;">当前阶段</span>
                                <div style="color: var(--v2-text-secondary);">${escapeHtml(resumeInfo.phase_name)}</div>
                            </div>
                            <div>
                                <span style="color: var(--v2-text-muted); font-size: 0.875rem;">当前步骤</span>
                                <div style="color: var(--v2-text-secondary);">${escapeHtml(resumeInfo.current_step)}</div>
                            </div>
                        </div>
                        <div style="margin-top: 0.75rem;">
                            <span style="color: var(--v2-text-muted); font-size: 0.875rem;">完成进度</span>
                            <div style="display: flex; align-items: center; gap: 0.75rem; margin-top: 0.25rem;">
                                <div style="flex: 1; height: 8px; background: var(--v2-bg-tertiary); border-radius: 4px; overflow: hidden;">
                                    <div style="width: ${resumeInfo.progress_percentage}%; height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 4px;"></div>
                                </div>
                                <span style="color: var(--v2-primary-400); font-weight: 600;">${resumeInfo.progress_percentage}%</span>
                            </div>
                        </div>
                    </div>
                    <p style="color: var(--v2-text-secondary); font-size: 0.9rem; line-height: 1.5; margin: 0;">
                        💡 将从上次保存的步骤继续生成，无需重新开始。
                    </p>
                </div>
                <div class="v2-dialog-actions">
                    <button class="v2-btn v2-btn--secondary" onclick="closeResumeConfirmModal(false)">
                        <span>取消</span>
                    </button>
                    <button class="v2-btn v2-btn--primary" onclick="closeResumeConfirmModal(true)" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);">
                        <span>🔄 确认恢复</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 保存回调
    window._resumeConfirmCallback = (confirmed) => {
        if (!confirmed) {
            modeSelect.value = 'phase_one_only';
        }
        modal.remove();
    };
}

/**
 * 关闭恢复确认弹窗
 */
function closeResumeConfirmModal(confirmed) {
    if (window._resumeConfirmCallback) {
        window._resumeConfirmCallback(confirmed);
    }
}

/**
 * 显示 V2 风格的提示弹窗
 */
function showResumeAlertModal(title, message) {
    const existingModal = document.getElementById('resume-alert-modal');
    if (existingModal) existingModal.remove();
    
    const modal = document.createElement('div');
    modal.id = 'resume-alert-modal';
    modal.innerHTML = `
        <div class="v2-dialog-overlay" onclick="if(event.target === this) closeResumeAlertModal()">
            <div class="v2-dialog-content" style="max-width: 400px;">
                <div class="v2-dialog-header" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                    <div class="v2-dialog-icon">⚠️</div>
                    <h3 class="v2-dialog-title">${escapeHtml(title)}</h3>
                </div>
                <div class="v2-dialog-body">
                    <p style="color: var(--v2-text-secondary); font-size: 0.95rem; line-height: 1.5; margin: 0;">
                        ${escapeHtml(message)}
                    </p>
                </div>
                <div class="v2-dialog-actions">
                    <button class="v2-btn v2-btn--primary" onclick="closeResumeAlertModal()" style="width: 100%; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                        <span>知道了</span>
                    </button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

/**
 * 关闭提示弹窗
 */
function closeResumeAlertModal() {
    const modal = document.getElementById('resume-alert-modal');
    if (modal) modal.remove();
}

/**
 * HTML 转义辅助函数
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 修改表单提交，支持恢复模式
 */
async function startPhaseOneGenerationWithResume(event) {
    event.preventDefault();
    
    // 检查是否启用恢复模式
    if (isResumeModeEnabled() && currentResumeInfo) {
        try {
            // 显示进度区域
            const progressSection = document.getElementById('progress-section');
            if (progressSection) {
                progressSection.style.display = 'block';
            }
            
            const progressMessage = document.getElementById('progress-message');
            if (progressMessage) {
                progressMessage.textContent = `🔄 恢复生成中... 从 ${currentResumeInfo.current_step} 继续`;
            }
            
            const response = await fetch('/api/generation/resume', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: currentResumeInfo.novel_title
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '恢复生成失败');
            }
            
            const result = await response.json();
            
            if (result.success) {
                console.log(`✅ 已从 ${currentResumeInfo.current_step} 继续生成！任务ID: ${result.task_id}`);
                
                // 在当前页面显示进度，不跳转
                if (result.task_id) {
                    startMonitoringTask(result.task_id);
                }
                return;
            } else {
                throw new Error(result.error || '恢复生成失败');
            }
            
        } catch (error) {
            console.error('恢复生成失败:', error);
            alert('恢复失败: ' + error.message + '\n\n将尝试从头开始生成...');
            // 如果恢复失败，继续执行正常的生成流程
        }
    }
    
    // 执行正常的生成流程
    if (typeof startPhaseOneGeneration === 'function') {
        await startPhaseOneGeneration(event);
    } else {
        console.error('找不到startPhaseOneGeneration函数');
        alert('生成功能未正确加载');
    }
}

/**
 * 监控任务进度
 */
function startMonitoringTask(taskId) {
    console.log(`🔍 开始监控任务: ${taskId}`);
    
    // 定期查询任务状态
    const intervalId = setInterval(async () => {
        try {
            const response = await fetch(`/api/phase-one/task/${taskId}/status`);
            if (!response.ok) {
                clearInterval(intervalId);
                return;
            }
            
            const data = await response.json();
            
            if (data.success) {
                // 更新进度显示
                updateProgressDisplay(data);
                
                // 检查是否完成
                if (data.status === 'completed' || data.status === 'failed') {
                    clearInterval(intervalId);
                    handleTaskCompletion(data);
                }
            }
        } catch (error) {
            console.error('查询任务状态失败:', error);
        }
    }, 2000); // 每2秒查询一次
}

/**
 * 更新进度显示
 */
function updateProgressDisplay(data) {
    const progressMessage = document.getElementById('progress-message');
    const progressFill = document.getElementById('progress-bar-fill');
    const progressPercentage = document.getElementById('progress-percentage');
    
    if (progressMessage) {
        progressMessage.textContent = `🔄 正在生成... 当前步骤: ${data.current_step || '初始化'}`;
    }
    
    if (progressFill) {
        progressFill.style.width = `${data.progress || 0}%`;
    }
    
    if (progressPercentage) {
        progressPercentage.textContent = `${data.progress || 0}%`;
    }
}

/**
 * 处理任务完成
 */
function handleTaskCompletion(data) {
    const progressMessage = document.getElementById('progress-message');
    const resultsSection = document.getElementById('results-section');
    const progressSection = document.getElementById('progress-section');
    
    if (data.status === 'completed') {
        if (progressMessage) {
            progressMessage.textContent = '✅ 生成完成！';
        }
        
        // 显示结果区域
        if (resultsSection) {
            resultsSection.style.display = 'block';
            
            // 填充结果数据
            const resultOverview = document.getElementById('result-overview');
            if (resultOverview && data.result) {
                resultOverview.innerHTML = `
                    <h3>🎉 第一阶段设定生成完成</h3>
                    <p><strong>小说标题:</strong> ${data.result.novel_title || '未命名'}</p>
                    <p><strong>总章节数:</strong> ${data.result.total_chapters || 200}</p>
                    <p><strong>生成模式:</strong> 恢复模式</p>
                `;
            }
        }
        
        // 隐藏进度区域
        if (progressSection) {
            setTimeout(() => {
                progressSection.style.display = 'none';
            }, 2000);
        }
        
    } else if (data.status === 'failed') {
        if (progressMessage) {
            progressMessage.textContent = `❌ 生成失败: ${data.error || '未知错误'}`;
        }
    }
}

/**
 * 监听创意选择变化
 */
function setupResumeModeListener() {
    console.log('🔧 [RESUME] 设置恢复模式监听器');
    
    const ideaSelect = document.getElementById('creative-idea-select');
    
    if (ideaSelect) {
        ideaSelect.addEventListener('change', async function() {
            const selectedOption = this.options[this.selectedIndex];
            const title = selectedOption.text.replace(/^📚\s*/, '').trim();
            
            console.log(`📝 [RESUME] 创意选择变化: ${title}`);
            
            // 清除旧的恢复选项
            clearResumeOption();
            
            // 检查是否有检查点
            if (title) {
                const resumeInfo = await checkTaskResumeStatus(title);
                if (resumeInfo) {
                    showResumeOption(resumeInfo);
                }
            }
        });
    } else {
        console.log('ℹ️ [RESUME] 未找到 creative-idea-select 元素');
    }
    
    // 监听填充创意按钮
    const fillButton = document.querySelector('button[onclick="fillFromCreativeIdea()"]');
    if (fillButton) {
        const originalOnClick = fillButton.onclick;
        fillButton.onclick = async function() {
            // 先执行原有的填充逻辑
            if (originalOnClick) {
                originalOnClick.call(this);
            }
            
            // 延迟检查，等待表单填充完成
            setTimeout(async () => {
                const titleInput = document.getElementById('novel-title');
                if (titleInput && titleInput.value) {
                    const resumeInfo = await checkTaskResumeStatus(titleInput.value);
                    if (resumeInfo) {
                        showResumeOption(resumeInfo);
                    }
                }
            }, 100);
        };
    }
    
    // 监听标题输入框变化
    const titleInput = document.getElementById('novel-title');
    if (titleInput) {
        let debounceTimer;
        titleInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const title = this.value.trim();
                clearResumeOption();
                
                if (title) {
                    const resumeInfo = await checkTaskResumeStatus(title);
                    if (resumeInfo) {
                        showResumeOption(resumeInfo);
                    }
                }
            }, 500);
        });
    }
    
    console.log('✅ [RESUME] 恢复模式监听器设置完成');
}

/**
 * 页面加载时设置监听器
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 [RESUME] DOM加载完成，准备设置监听器');
    setTimeout(() => {
        setupResumeModeListener();
        
        // 页面加载后也检查一次当前标题
        const titleInput = document.getElementById('novel-title');
        if (titleInput && titleInput.value) {
            console.log(`🔍 [RESUME] 页面加载时检查标题: ${titleInput.value}`);
            checkTaskResumeStatus(titleInput.value).then(resumeInfo => {
                if (resumeInfo) {
                    showResumeOption(resumeInfo);
                }
            });
        }
    }, 500);
});