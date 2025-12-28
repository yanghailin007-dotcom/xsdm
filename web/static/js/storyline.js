// 故事线时间线页面JavaScript - 左右分栏版本

let currentStorylineData = null;
let currentProjectTitle = null;
let selectedMajorEventIndex = null;
let hasUnsavedChanges = false;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    loadProjects();
});

// ==================== 项目管理功能 ====================

async function loadProjects() {
    try {
        showLoadingState();
        
        const response = await fetch('/api/projects/with-phase-status');
        
        if (response.status === 401) {
            showError('请先登录');
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        updateProjectSelector(result.projects || []);
        
        // 如果有项目且URL中有指定项目，自动加载
        const urlParams = new URLSearchParams(window.location.search);
        const projectTitle = urlParams.get('title');
        
        if (projectTitle) {
            const selectElement = document.getElementById('project-select');
            selectElement.value = projectTitle;
            await loadStoryline();
        } else {
            showEmptyState();
        }
    } catch (error) {
        console.error('加载项目列表失败:', error);
        showError(`加载项目失败: ${error.message}`);
    }
}

function updateProjectSelector(projects) {
    const selectElement = document.getElementById('project-select');
    
    // 保留第一项（选择提示）
    selectElement.innerHTML = '<option value="">选择项目...</option>';
    
    // 添加项目选项
    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.title;
        option.textContent = project.title;
        selectElement.appendChild(option);
    });
}

// ==================== 故事线加载功能 ====================

async function loadStoryline() {
    const selectElement = document.getElementById('project-select');
    const projectTitle = selectElement.value;
    
    if (!projectTitle) {
        showEmptyState();
        return;
    }
    
    currentProjectTitle = projectTitle;
    
    try {
        showLoadingState();
        
        const response = await fetch(`/api/storyline/${encodeURIComponent(projectTitle)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentStorylineData = result.storyline;
            renderStoryline(result.storyline);
        } else {
            showError(result.error || '加载故事线失败');
        }
    } catch (error) {
        console.error('加载故事线失败:', error);
        showError(`加载失败: ${error.message}`);
    }
}

function renderStoryline(storyline) {
    // 隐藏加载状态
    hideAllStates();
    
    // 显示主容器
    const storylineMain = document.getElementById('storyline-main');
    storylineMain.style.display = 'block';
    
    // 检查是否是多阶段数据
    const isMultiStage = storyline.stage_info && Array.isArray(storyline.stage_info) && storyline.stage_info.length > 0;
    
    if (isMultiStage) {
        // 显示多阶段信息
        const stageInfo = storyline.stage_info.map(si =>
            `${si.stage_name} (${si.chapter_range}, ${si.major_event_count}个事件)`
        ).join(' → ');
        document.getElementById('stage-name').textContent = `全书故事线 (${storyline.stage_info.length}个阶段)`;
        document.getElementById('chapter-range-text').textContent = stageInfo;
    } else {
        // 单阶段数据
        document.getElementById('stage-name').textContent = storyline.stage_name || '全书故事线';
        document.getElementById('chapter-range-text').textContent = storyline.chapter_range || '全章节';
    }
    
    // 渲染重大事件列表
    renderMajorEventsList(storyline.major_events || []);
    
    // 重置选择状态
    selectedMajorEventIndex = null;
    hasUnsavedChanges = false;
    updateSaveButton();
    
    console.log(`✅ 渲染了 ${storyline.major_events?.length || 0} 个重大事件`);
}

function renderMajorEventsList(majorEvents) {
    const listContainer = document.getElementById('major-events-list');
    listContainer.innerHTML = '';
    
    if (majorEvents.length === 0) {
        listContainer.innerHTML = '<div class="empty-events">暂无重大事件</div>';
        return;
    }
    
    majorEvents.forEach((event, index) => {
        const card = createMajorEventCard(event, index);
        listContainer.appendChild(card);
    });
}

function createMajorEventCard(event, index) {
    const card = document.createElement('div');
    card.className = 'major-event-card';
    card.dataset.index = index;
    card.onclick = () => selectMajorEvent(index);
    
    const displayName = event.name || event.main_goal || `重大事件 ${index + 1}`;
    
    // 情绪强度对应的颜色
    const intensity = event.emotional_intensity || 'medium';
    const emotionColor = {
        'high': '#ef4444',
        'medium': '#f59e0b',
        'low': '#10b981'
    }[intensity] || '#f59e0b';
    
    // 获取期待感标签（新增）
    const expectationBadge = getExpectationBadge(event);
    
    card.innerHTML = `
        <div class="major-event-header">
            <div class="major-event-title">${escapeHtml(displayName)}</div>
            <div class="major-event-number">${index + 1}</div>
        </div>
        <div class="major-event-badges">
            <span class="event-badge badge-chapter">${event.chapter_range || '全章节'}</span>
            ${event.emotional_focus ? `<span class="event-badge badge-emotion" style="color: ${emotionColor}; background: ${emotionColor}15;">${event.emotional_focus}</span>` : ''}
            ${expectationBadge}
        </div>
        <div class="major-event-preview">${escapeHtml(event.main_goal || event.description || event.role_in_stage_arc || '')}</div>
    `;
    
    return card;
}

function selectMajorEvent(index) {
    // 更新选中状态
    const cards = document.querySelectorAll('.major-event-card');
    cards.forEach(card => card.classList.remove('active'));
    cards[index].classList.add('active');
    
    selectedMajorEventIndex = index;
    
    // 🔥 添加调试信息
    console.log(`[DEBUG] 选择重大事件 ${index}:`, currentStorylineData.major_events[index]?.name);
    console.log('[DEBUG] 事件数据:', currentStorylineData.major_events[index]);
    
    // 渲染右侧详情
    try {
        renderMajorEventDetail(index);
    } catch (error) {
        console.error('[ERROR] 渲染详情时出错:', error);
        showError(`显示详情失败: ${error.message}`);
    }
}

function renderMajorEventDetail(index) {
    console.log(`[DEBUG] renderMajorEventDetail 开始, index=${index}`);
    
    const event = currentStorylineData.major_events[index];
    const contentContainer = document.getElementById('medium-events-content');
    
    if (!event) {
        console.error('[ERROR] 事件不存在:', index);
        showError('事件数据不存在');
        return;
    }
    
    if (!contentContainer) {
        console.error('[ERROR] medium-events-content 容器不存在');
        showError('详情容器不存在');
        return;
    }
    
    // 🔥 添加调试信息
    console.log('[DEBUG] 事件数据:', event);
    console.log('[DEBUG] composition:', event.composition);
    console.log('[DEBUG] _medium_events:', event._medium_events);
    console.log('[DEBUG] medium_events:', event.medium_events);
    
    // 更新面板标题
    const displayName = event.name || event.main_goal || `重大事件 ${index + 1}`;
    
    // 显示阶段信息（如果有）
    const stageInfo = event._stage ? `【${event._stage}】` : '';
    
    document.getElementById('medium-panel-title').innerHTML = `📋 ${stageInfo}${escapeHtml(displayName)}`;
    document.getElementById('medium-panel-subtitle').textContent = `${event.chapter_range || event._chapter_range || '全章节'}`;
    
    // 获取期待感信息（新增）
    const expectationInfo = getExpectationInfo(event);
    
    let html = `
        <div class="major-event-detail">
            <div class="detail-header">
                <h3>${escapeHtml(displayName)}</h3>
                <div class="detail-meta">
                    <div class="detail-meta-item">
                        <span class="label">章节范围:</span>
                        <span>${event.chapter_range || '全章节'}</span>
                    </div>
                    <div class="detail-meta-item">
                        <span class="label">情绪强度:</span>
                        <span>${getEmotionIntensityText(event.emotional_intensity)}</span>
                    </div>
                </div>
            </div>
            
            ${expectationInfo ? `
            <div class="detail-section expectation-section">
                <div class="detail-section-title">🎯 期待感设置</div>
                ${expectationInfo}
            </div>
            ` : ''}
            
            <div class="detail-section">
                <div class="detail-section-title">🎯 主要目标</div>
                <textarea class="editable-field" data-field="main_goal" data-index="${index}">${escapeHtml(event.main_goal || event.role_in_stage_arc || '')}</textarea>
            </div>
            
            <div class="detail-section">
                <div class="detail-section-title">💭 情绪焦点</div>
                <textarea class="editable-field" data-field="emotional_focus" data-index="${index}">${escapeHtml(event.emotional_focus || event.emotional_goal || '')}</textarea>
            </div>
            
            <div class="detail-section">
                <div class="detail-section-title">📝 详细描述</div>
                <textarea class="editable-field" data-field="description" data-index="${index}">${escapeHtml(event.description || '')}</textarea>
            </div>
    `;
    
    // 关键情绪节拍
    const keyBeats = event.key_emotional_beats || [];
    if (keyBeats.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">🎵 关键情绪节拍</div>
                <ul class="key-beats-list">
                    ${keyBeats.map(beat => `<li>${escapeHtml(beat)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    // 🔥 重新设计：特殊情感事件不再在重大事件级别显示
    // 它们现在附着在中型事件上，会在中型事件卡片中作为子元素展示
    
    // 中级事件列表 - 优先从 composition 中提取
    let mediumEvents = [];
    
    // 🔥 修复：只从一个来源提取，避免重复
    // 优先级：composition > _medium_events > medium_events
    if (event.composition && typeof event.composition === 'object' && Object.keys(event.composition).length > 0) {
        // composition 是一个包含 '起', '承', '转', '合' 的对象
        const phases = ['起', '承', '转', '合'];
        phases.forEach(phase => {
            if (event.composition[phase] && Array.isArray(event.composition[phase])) {
                event.composition[phase].forEach(me => {
                    me.phase = phase;
                    mediumEvents.push(me);
                });
            }
        });
        console.log(`[DEBUG] 从composition提取了 ${mediumEvents.length} 个中型事件`);
    } else if (event._medium_events && event._medium_events.length > 0) {
        // 从 _medium_events 提取
        mediumEvents = event._medium_events;
        console.log(`[DEBUG] 从_medium_events提取了 ${mediumEvents.length} 个中型事件`);
    } else if (event.medium_events && event.medium_events.length > 0) {
        // 从 medium_events 数组提取
        mediumEvents = event.medium_events;
        console.log(`[DEBUG] 从medium_events提取了 ${mediumEvents.length} 个中型事件`);
    }
    
    console.log(`[DEBUG] 总共 ${mediumEvents.length} 个中型事件`);
    
    if (mediumEvents.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">🔸 中级事件 (${mediumEvents.length})</div>
                <div class="medium-events-list">
                    ${mediumEvents.map((me, meIndex) => createMediumEventCard(me, meIndex, index)).join('')}
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    contentContainer.innerHTML = html;
    
    // 绑定编辑事件
    bindEditableFields();
}

function createMediumEventCard(event, eventIndex, majorIndex) {
    const displayName = event.name || event.main_goal || `中级事件 ${eventIndex + 1}`;
    const fieldId = `medium-${majorIndex}-${eventIndex}`;
    const phase = event.phase || '起';
    const phaseIndex = ['起', '承', '转', '合'].indexOf(phase) + 1;
    
    // 使用标准化的章节范围（如果有的话），否则使用原始值
    const chapterRange = event._chapter_range_normalized || event.chapter_range || '';
    
    // 🔥 重新设计：检查是否有特殊情感事件（新格式）
    const specialEmotionalEvents = event.special_emotional_events || [];
    const hasSpecialEvents = specialEmotionalEvents.length > 0;
    
    let specialEventsHtml = '';
    if (hasSpecialEvents) {
        specialEventsHtml = `
            <div class="medium-event-field">
                <label class="medium-field-label">✨ 特殊情感事件 (${specialEmotionalEvents.length})</label>
                <div class="special-events-list">
                    ${specialEmotionalEvents.map(se => `
                        <div class="special-event-item">
                            <div class="special-event-header">
                                <div class="special-event-name">${escapeHtml(se.name || '特殊事件')}</div>
                                ${se.target_chapter ? `<div class="special-event-chapter">第${se.target_chapter}章</div>` : ''}
                            </div>
                            <div class="special-event-purpose"><strong>目的:</strong> ${escapeHtml(se.purpose || '-')}</div>
                            ${se.emotional_tone ? `<div class="special-event-tone"><strong>情感基调:</strong> ${escapeHtml(se.emotional_tone)}</div>` : ''}
                            ${se.key_elements && se.key_elements.length > 0 ? `
                            <div class="special-event-elements"><strong>关键元素:</strong> ${escapeHtml(se.key_elements.join(', '))}</div>
                            ` : ''}
                            ${se.context_hint ? `<div class="special-event-context"><strong>上下文:</strong> ${escapeHtml(se.context_hint)}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    return `
        <div class="medium-event-card ${hasSpecialEvents ? 'has-special-events' : ''}">
            <div class="medium-event-header" onclick="toggleMediumEvent('${fieldId}')">
                <span class="medium-event-title">${escapeHtml(displayName)}</span>
                <div class="medium-event-badges">
                    <span class="medium-event-badge badge-phase">${phase} ${phaseIndex}</span>
                    ${chapterRange ? `<span class="medium-event-badge badge-chapter">${escapeHtml(chapterRange)}</span>` : ''}
                    ${hasSpecialEvents ? `<span class="medium-event-badge badge-special">✨ ${specialEmotionalEvents.length}个特殊事件</span>` : ''}
                </div>
            </div>
            <div class="medium-event-body" id="${fieldId}">
                ${specialEventsHtml}
                <div class="medium-event-field">
                    <label class="medium-field-label">🎯 主要目标</label>
                    <textarea class="editable-field" data-field="main_goal" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.main_goal || event.role_in_stage_arc || '')}</textarea>
                </div>
                <div class="medium-event-field">
                    <label class="medium-field-label">💭 情绪焦点</label>
                    <textarea class="editable-field" data-field="emotional_focus" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.emotional_focus || '')}</textarea>
                </div>
                ${event.description ? `
                <div class="medium-event-field">
                    <label class="medium-field-label">📝 描述</label>
                    <textarea class="editable-field" data-field="description" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.description)}</textarea>
                </div>
                ` : ''}
                ${event.decomposition_type ? `
                <div class="medium-event-field">
                    <label class="medium-field-label">🔧 分解类型</label>
                    <div class="field-value">${escapeHtml(event.decomposition_type)}</div>
                </div>
                ` : ''}
            </div>
        </div>
    `;
}

function toggleMediumEvent(fieldId) {
    const body = document.getElementById(fieldId);
    body.classList.toggle('expanded');
}

function bindEditableFields() {
    const fields = document.querySelectorAll('.editable-field');
    fields.forEach(field => {
        field.addEventListener('input', handleFieldChange);
    });
}

function handleFieldChange(event) {
    const field = event.target;
    field.classList.add('changed');
    hasUnsavedChanges = true;
    updateSaveButton();
}

function updateSaveButton() {
    const saveBtn = document.getElementById('btn-save');
    if (saveBtn) {
        saveBtn.style.display = hasUnsavedChanges ? 'flex' : 'none';
    }
}

async function saveStorylineChanges() {
    if (!hasUnsavedChanges) {
        return;
    }
    
    const saveBtn = document.getElementById('btn-save');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span>⏳</span> 保存中...';
    
    try {
        // 收集所有更改
        const changedFields = document.querySelectorAll('.editable-field.changed');
        
        changedFields.forEach(field => {
            const fieldName = field.dataset.field;
            const value = field.value;
            
            if (field.dataset.major !== undefined && field.dataset.medium !== undefined) {
                // 中级事件
                const majorIndex = parseInt(field.dataset.major);
                const mediumIndex = parseInt(field.dataset.medium);
                currentStorylineData.major_events[majorIndex].medium_events[mediumIndex][fieldName] = value;
            } else if (field.dataset.index !== undefined) {
                // 重大事件
                const index = parseInt(field.dataset.index);
                currentStorylineData.major_events[index][fieldName] = value;
            }
        });
        
        // 发送到服务器保存
        const response = await fetch(`/api/storyline/${encodeURIComponent(currentProjectTitle)}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                storyline: currentStorylineData
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // 清除更改标记
            changedFields.forEach(field => field.classList.remove('changed'));
            hasUnsavedChanges = false;
            updateSaveButton();
            
            // 显示成功消息
            showNotification('保存成功！', 'success');
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        showNotification(`保存失败: ${error.message}`, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span>💾</span> 保存更改';
    }
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 12px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
        font-weight: 600;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==================== 辅助函数 ====================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getEmotionIntensityText(intensity) {
    const map = {
        'high': '高',
        'medium': '中',
        'low': '低'
    };
    return map[intensity] || '中';
}

// ==================== 状态显示功能 ====================

function showLoadingState() {
    hideAllStates();
    document.getElementById('loading-state').style.display = 'block';
}

function showError(message) {
    hideAllStates();
    document.getElementById('error-message').textContent = message;
    document.getElementById('error-state').style.display = 'block';
}

function showEmptyState() {
    hideAllStates();
    document.getElementById('empty-state').style.display = 'block';
}

function hideAllStates() {
    document.getElementById('loading-state').style.display = 'none';
    document.getElementById('error-state').style.display = 'none';
    document.getElementById('empty-state').style.display = 'none';
    document.getElementById('storyline-main').style.display = 'none';
}

// ==================== 键盘事件处理 ====================

document.addEventListener('keydown', function(event) {
    // Ctrl+S 保存
    if (event.ctrlKey && event.key === 's') {
        event.preventDefault();
        if (hasUnsavedChanges) {
            saveStorylineChanges();
        }
    }
});

// ==================== 期待感相关功能（新增）====================

function getExpectationBadge(event) {
    // 获取事件的期待感标签
    if (!currentStorylineData.expectation_map) {
        return '';
    }
    
    const expectations = currentStorylineData.expectation_map.expectations || {};
    const eventExpectations = Object.values(expectations).filter(exp =>
        exp.description && exp.description.includes(event.name || event.main_goal || '')
    );
    
    if (eventExpectations.length === 0) {
        return '';
    }
    
    const expectation = eventExpectations[0];
    const typeLabels = {
        'showcase': '展示橱窗',
        'suppression_release': '压抑释放',
        'nested_doll': '套娃期待',
        'emotional_hook': '情绪钩子',
        'power_gap': '实力差距',
        'mystery_foreshadow': '伏笔揭秘'
    };
    
    const typeLabel = typeLabels[expectation.type] || expectation.type;
    const statusLabels = {
        'planted': '已种植',
        'fermenting': '发酵中',
        'ready_to_release': '即将释放',
        'released': '已释放',
        'failed': '失败'
    };
    
    const statusLabel = statusLabels[expectation.status] || expectation.status;
    const statusColors = {
        'planted': '#10b981',
        'fermenting': '#f59e0b',
        'ready_to_release': '#ef4444',
        'released': '#6b7280',
        'failed': '#ef4444'
    };
    
    const statusColor = statusColors[expectation.status] || '#6b7280';
    
    return `
        <span class="event-badge badge-expectation" title="期待感: ${typeLabel}\n状态: ${statusLabel}">
            🎯 ${typeLabel}
            <span class="expectation-status" style="color: ${statusColor}">● ${statusLabel}</span>
        </span>
    `;
}

function getExpectationInfo(event) {
    // 获取事件的期待感详细信息
    if (!currentStorylineData.expectation_map) {
        return null;
    }
    
    const expectations = currentStorylineData.expectation_map.expectations || {};
    const eventExpectations = Object.values(expectations).filter(exp =>
        exp.description && exp.description.includes(event.name || event.main_goal || '')
    );
    
    if (eventExpectations.length === 0) {
        return null;
    }
    
    const expectation = eventExpectations[0];
    const typeLabels = {
        'showcase': '展示橱窗效应',
        'suppression_release': '压抑与释放',
        'nested_doll': '套娃式期待',
        'emotional_hook': '情绪钩子',
        'power_gap': '实力差距',
        'mystery_foreshadow': '伏笔揭秘'
    };
    
    const typeLabel = typeLabels[expectation.type] || expectation.type;
    const statusLabels = {
        'planted': '已种植',
        'fermenting': '发酵中',
        'ready_to_release': '即将释放',
        'released': '已释放',
        'failed': '释放失败'
    };
    
    const statusLabel = statusLabels[expectation.status] || expectation.status;
    
    let html = `
        <div class="expectation-item">
            <div class="expectation-type">
                <span class="expectation-icon">🎯</span>
                <strong>${typeLabel}</strong>
            </div>
            <div class="expectation-status">
                <span class="status-label">状态:</span>
                <span class="status-value">${statusLabel}</span>
            </div>
            <div class="expectation-description">
                <span class="label">期待描述:</span>
                <span class="value">${escapeHtml(expectation.description || '无描述')}</span>
            </div>
            ${expectation.planted_chapter ? `
            <div class="expectation-timeline">
                <span class="label">种植章节:</span>
                <span class="value">第 ${expectation.planted_chapter} 章</span>
                ${expectation.target_chapter ? `
                <span class="timeline-arrow">→</span>
                <span class="label">目标章节:</span>
                <span class="value">第 ${expectation.target_chapter} 章</span>
                ` : ''}
            </div>
            ` : ''}
            ${expectation.released_chapter ? `
            <div class="expectation-release">
                <span class="label">释放章节:</span>
                <span class="value">第 ${expectation.released_chapter} 章</span>
                ${expectation.satisfaction_score ? `
                <span class="satisfaction-score">
                    满足度: ${expectation.satisfaction_score.toFixed(1)}/10
                </span>
                ` : ''}
            </div>
            ` : ''}
        </div>
    `;
    
    return html;
}

// 添加期待感相关的CSS样式
const expectationStyle = document.createElement('style');
expectationStyle.textContent = `
    /* 期待感样式 */
    .badge-expectation {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        display: inline-flex;
        align-items: center;
        gap: 4px;
        box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
    }
    
    .expectation-status {
        font-size: 10px;
        margin-left: 4px;
    }
    
    .expectation-section {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-left: 4px solid #667eea;
        padding: 16px;
        margin-bottom: 16px;
        border-radius: 8px;
    }
    
    .expectation-item {
        background: white;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .expectation-type {
        font-size: 16px;
        margin-bottom: 12px;
        color: #667eea;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .expectation-status {
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .expectation-description {
        margin-bottom: 8px;
        padding: 8px;
        background: #f9fafb;
        border-radius: 4px;
        font-size: 14px;
    }
    
    .expectation-timeline {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 8px;
        font-size: 14px;
    }
    
    .timeline-arrow {
        color: #9ca3af;
        font-weight: bold;
    }
    
    .expectation-release {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        padding: 8px;
        background: #ecfdf5;
        border-radius: 4px;
        font-size: 14px;
    }
    
    .satisfaction-score {
        background: #10b981;
        color: white;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 600;
    }

    /* 中级事件特殊事件样式 */
    .medium-event-card.has-special-events {
        border-left: 3px solid #f59e0b;
    }
    
    .badge-special {
        background: linear-gradient(135deg, #f59e0b 0%, #ef4444 100%);
        color: white;
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 11px;
        display: inline-flex;
        align-items: center;
        gap: 2px;
    }
    
    .special-events-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 8px;
    }
    
    .special-event-item {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border-left: 3px solid #f59e0b;
        padding: 12px;
        border-radius: 6px;
        margin-bottom: 8px;
    }
    
    .special-event-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .special-event-name {
        font-weight: 600;
        color: #92400e;
        font-size: 14px;
    }
    
    .special-event-chapter {
        background: linear-gradient(135deg, #fed7aa 0%, #fbbf24 100%);
        color: #78350f;
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 11px;
        font-weight: 600;
    }
    
    .special-event-purpose {
        color: #78350f;
        font-size: 13px;
        line-height: 1.4;
        margin-bottom: 4px;
    }
    
    .special-event-tone {
        color: #92400e;
        font-size: 12px;
        margin-bottom: 4px;
    }
    
    .special-event-elements {
        color: #78350f;
        font-size: 12px;
        margin-bottom: 4px;
        padding: 4px 8px;
        background: rgba(251, 191, 36, 0.05);
        border-radius: 4px;
    }
    
    .special-event-context {
        color: #92400e;
        font-size: 12px;
        font-style: italic;
        opacity: 0.8;
    }
`;
document.head.appendChild(expectationStyle);