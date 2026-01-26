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
        target_platform: document.getElementById('target-platform').value || 'fanqie',
        creative_seed: selectedCreativeId ? loadedCreativeIdeas.find(i => i.id === selectedCreativeId)?.raw_data : null
    };

    console.log('🎯 目标平台:', formData.target_platform);

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

    // 加载质量评估报告
    loadQualityAssessment(result.novel_title);
}

// ==================== 质量评估功能 ====================

// 加载质量评估报告
async function loadQualityAssessment(novelTitle) {
    if (!novelTitle) {
        document.getElementById('quality-loading').innerHTML = '<p style="color: #ef4444;">无法加载评估报告：缺少小说标题</p>';
        return;
    }

    try {
        const encodedTitle = encodeURIComponent(novelTitle);
        const response = await fetch(`/api/quality-assessment/${encodedTitle}`);

        if (response.status === 404) {
            document.getElementById('quality-loading').innerHTML = `
                <div style="text-align: center; padding: 40px;">
                    <p style="color: #f59e0b; margin-bottom: 16px;">📊 质量评估报告未找到</p>
                    <p style="color: #6b7280; margin-bottom: 16px;">这可能是因为生成是在此功能添加之前完成的</p>
                    <button class="btn btn-primary" onclick="triggerQualityAssessment('${encodedTitle}')">
                        🔄 立即生成评估报告
                    </button>
                </div>
            `;
            return;
        }

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        if (data.success) {
            displayQualityAssessment(data.report);
        } else {
            throw new Error(data.error || '加载失败');
        }
    } catch (error) {
        console.error('加载质量评估失败:', error);
        document.getElementById('quality-loading').innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <p style="color: #ef4444; margin-bottom: 16px;">❌ 加载评估报告失败: ${error.message}</p>
                <button class="btn btn-secondary" onclick="triggerQualityAssessment('${encodedTitle}')">
                    🔄 重试
                </button>
            </div>
        `;
    }
}

// 触发质量评估
async function triggerQualityAssessment(encodedTitle) {
    const loadingDiv = document.getElementById('quality-loading');
    loadingDiv.innerHTML = '<p style="text-align: center;">🔄 正在生成AI质量评估报告，请稍候...</p>';

    try {
        const response = await fetch(`/api/quality-assessment/trigger/${encodedTitle}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ deep_analysis: true })
        });

        const data = await response.json();
        if (data.success) {
            displayQualityAssessment(data.report);
            showStatusMessage('✅ 质量评估完成', 'success');
        } else {
            throw new Error(data.error || '评估失败');
        }
    } catch (error) {
        console.error('触发质量评估失败:', error);
        loadingDiv.innerHTML = `
            <div style="text-align: center; padding: 40px;">
                <p style="color: #ef4444;">❌ 评估失败: ${error.message}</p>
            </div>
        `;
    }
}

// 显示质量评估报告
function displayQualityAssessment(report) {
    const qualityContent = document.getElementById('quality-content');

    // 移除加载动画
    const loadingDiv = document.getElementById('quality-loading');
    if (loadingDiv) loadingDiv.remove();

    // 生成报告HTML
    const readinessInfo = {
        'ready': { text: '可以继续', color: '#10b981', icon: '✅' },
        'needs_review': { text: '建议检查', color: '#f59e0b', icon: '⚠️' },
        'needs_revision': { text: '需要修改', color: '#ef4444', icon: '❌' }
    };

    const readiness = readinessInfo[report.readiness] || readinessInfo['needs_review'];
    const score = report.overall_score || 0;
    const scoreColor = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

    let html = `
        <div class="quality-assessment-report">
            <!-- 总体评分卡片 -->
            <div class="quality-score-card" style="background: linear-gradient(135deg, ${readiness.color}20 0%, ${readiness.color}10 100%); border: 2px solid ${readiness.color}; border-radius: 12px; padding: 24px; margin-bottom: 24px; text-align: center;">
                <div style="font-size: 14px; color: #6b7280; margin-bottom: 8px;">总体评分</div>
                <div style="font-size: 48px; font-weight: bold; color: ${scoreColor};">${score}<span style="font-size: 24px; color: #9ca3af;">/100</span></div>
                <div style="margin-top: 12px; padding: 8px 16px; background: ${readiness.color}; color: white; border-radius: 20px; display: inline-block;">
                    ${readiness.icon} ${readiness.text}
                </div>
                ${report.token_saved > 0 ? `<div style="margin-top: 12px; font-size: 12px; color: #6b7280;">节省约 ${report.token_saved.toLocaleString()} tokens</div>` : ''}
            </div>

            <!-- 优点列表 -->
            <div class="quality-section" style="margin-bottom: 24px;">
                <h4 style="color: #10b981; margin-bottom: 12px;">✅ 优点 (${report.strengths?.length || 0})</h4>
                <div style="display: grid; gap: 8px;">
    `;

    if (report.strengths && report.strengths.length > 0) {
        report.strengths.forEach(strength => {
            html += `
                <div style="padding: 12px; background: #f0fdf4; border-left: 4px solid #10b981; border-radius: 6px;">
                    ${strength}
                </div>
            `;
        });
    } else {
        html += `<div style="padding: 12px; color: #9ca3af; text-align: center;">暂无优点记录</div>`;
    }

    html += `
                </div>
            </div>

            <!-- 问题列表 -->
            <div class="quality-section" style="margin-bottom: 24px;">
                <h4 style="color: #ef4444; margin-bottom: 12px;">⚠️ 发现的问题 (${report.issues?.length || 0})</h4>
    `;

    if (report.issues && report.issues.length > 0) {
        // 按严重程度分组
        const severityOrder = ['critical', 'high', 'medium', 'low', 'info'];
        const severityLabels = {
            'critical': '🔴 严重',
            'high': '🟠 高',
            'medium': '🟡 中等',
            'low': '🟢 低',
            'info': '🔵 信息'
        };

        for (const severity of severityOrder) {
            const issues = report.issues.filter(i => i.severity === severity);
            if (issues.length === 0) continue;

            html += `
                <div style="margin-bottom: 16px;">
                    <div style="font-weight: bold; margin-bottom: 8px;">${severityLabels[severity]} (${issues.length})</div>
                    <div style="display: grid; gap: 8px;">
            `;

            issues.forEach((issue, idx) => {
                const issueId = `issue-${severity}-${idx}`;
                html += `
                    <div class="issue-card" id="${issueId}" style="padding: 12px; background: #fef2f2; border-left: 4px solid #ef4444; border-radius: 6px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
                            <span style="font-weight: bold; color: #374151;">[${issue.category}] ${issue.location}</span>
                            ${issue.auto_fixable ? '<span style="font-size: 11px; padding: 2px 8px; background: #dbeafe; color: #1d4ed8; border-radius: 10px;">可自动修复</span>' : ''}
                        </div>
                        <div style="color: #4b5563; margin-bottom: 8px;">${issue.description}</div>
                        <div style="color: #6b7280; font-size: 14px; font-style: italic;">💡 建议: ${issue.suggestion}</div>
                    </div>
                `;
            });

            html += `
                    </div>
                </div>
            `;
        }

        // 添加批量修复按钮
        const autoFixableCount = report.issues.filter(i => i.auto_fixable).length;
        if (autoFixableCount > 0) {
            html += `
                <div style="margin-top: 16px; text-align: center;">
                    <button class="btn btn-primary" onclick="fixQualityIssues('${encodeURIComponent(report.plan_file || '')}')">
                        🔧 自动修复 ${autoFixableCount} 个可修复问题
                    </button>
                </div>
            `;
        }
    } else {
        html += `<div style="padding: 24px; background: #f0fdf4; border-radius: 8px; text-align: center; color: #10b981;">🎉 未发现问题！</div>`;
    }

    html += `
            </div>

            <!-- 总结 -->
            <div class="quality-section">
                <h4 style="color: #6b7280; margin-bottom: 12px;">📝 总结</h4>
                <div style="padding: 16px; background: #f9fafb; border-radius: 8px; color: #374151;">
                    ${report.summary || '无总结信息'}
                </div>
            </div>
        </div>
    `;

    qualityContent.innerHTML = html;
}

// 修复质量问题
async function fixQualityIssues(encodedPlanFile) {
    if (!confirm('确定要自动修复这些问题吗？将创建备份文件。')) {
        return;
    }

    showStatusMessage('🔄 正在修复问题...', 'info');

    try {
        // 这里需要novel_title而不是plan_file
        // 从phaseOneResult获取
        const novelTitle = phaseOneResult?.novel_title;
        if (!novelTitle) {
            throw new Error('无法获取小说标题');
        }

        const encodedTitle = encodeURIComponent(novelTitle);
        const response = await fetch(`/api/quality-assessment/fix/${encodedTitle}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_fix_only: true })
        });

        const data = await response.json();
        if (data.success) {
            showStatusMessage(`✅ 修复完成: ${data.fixed_count}个已修复, ${data.skipped_count}个需手动处理`, 'success');
            // 重新加载评估报告
            setTimeout(() => loadQualityAssessment(novelTitle), 1000);
        } else {
            throw new Error(data.error || '修复失败');
        }
    } catch (error) {
        console.error('修复失败:', error);
        showStatusMessage(`❌ 修复失败: ${error.message}`, 'error');
    }
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