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
            alert('当前没有可恢复的任务，请选择其他生成模式');
            modeSelect.value = 'phase_one_only';
            return;
        }
        
        // 确认是否要恢复
        const confirmMsg = `确认要恢复生成吗？\n\n` +
                          `任务：${currentResumeInfo.novel_title}\n` +
                          `阶段：${currentResumeInfo.phase_name}\n` +
                          `当前步骤：${currentResumeInfo.current_step}\n` +
                          `进度：${currentResumeInfo.progress_percentage}%\n\n` +
                          `将从上次的下一步骤继续生成。`;
        
        if (!confirm(confirmMsg)) {
            modeSelect.value = 'phase_one_only';
        }
    }
}

/**
 * 修改表单提交，支持恢复模式
 */
async function startPhaseOneGenerationWithResume(event) {
    event.preventDefault();
    
    // 检查是否启用恢复模式
    if (isResumeModeEnabled() && currentResumeInfo) {
        try {
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
                alert(`✅ 已从 ${currentResumeInfo.current_step} 继续生成！\n\n任务ID: ${result.task_id}`);
                
                // 跳转到生成页面
                if (result.task_id) {
                    window.location.href = `/phase-one-generation?task_id=${result.task_id}`;
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