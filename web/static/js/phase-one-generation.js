// ==================== 第一阶段生成功能 ====================
let currentTaskId = null;
let progressInterval = null;
let phaseOneResult = null;

async function startPhaseOneGeneration(event) {
    event.preventDefault();

    const formData = {
        title: document.getElementById('novel-title').value,
        synopsis: document.getElementById('novel-synopsis').value,
        core_setting: document.getElementById('core-setting').value,
        core_selling_points: document.getElementById('core-selling-points').value,
        total_chapters: parseInt(document.getElementById('total-chapters').value),
        generation_mode: document.getElementById('generation-mode').value,
        creative_seed: selectedCreativeId ? loadedCreativeIdeas.find(i => i.id === selectedCreativeId)?.raw_data : null
    };

    try {
        // 显示进度区域
        showProgressSection();
        updateProgress(5, '正在启动第一阶段生成...');

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
            updateProgressStatus(result.task_id);
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
        updateProgress(taskStatus.progress || 0, taskStatus.status_message || '生成中...');

        // 更新进度步骤状态
        if (taskStatus.current_step) {
            updateProgressSteps(taskStatus.current_step);
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

function pauseGeneration() {
    // 暂停功能待实现
    showStatusMessage('⏸️ 暂停功能开发中...', 'info');
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