// 故事线时间线页面 JavaScript - V2 版本
// 适配 V2 设计系统，深色主题风格

console.log('[JS-LOADED] storyline.js V5.0 已加载');

let currentStorylineData = null;
let currentProjectTitle = null;
let selectedMajorEventIndex = null;
let hasUnsavedChanges = false;
let urlProjectTitle = null; // URL 参数中的项目名称

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    console.log('[JS-DOM] DOMContentLoaded 触发');
    
    // 检查 URL 参数
    const urlParams = new URLSearchParams(window.location.search);
    urlProjectTitle = urlParams.get('title');
    
    if (urlProjectTitle) {
        console.log('[JS-DOM] URL 参数项目:', urlProjectTitle);
        // 隐藏项目选择器
        const selectorContainer = document.getElementById('project-selector-container');
        if (selectorContainer) {
            selectorContainer.style.display = 'none';
        }
    }
    
    loadProjects();
});

// ==================== 项目管理功能 ====================

async function loadProjects() {
    console.log('[LOAD-PROJECTS] 开始加载项目列表');
    try {
        showLoadingState();
        
        const response = await fetch('/api/projects/with-phase-status');
        console.log('[LOAD-PROJECTS] 收到响应:', response.status);
        
        if (response.status === 401) {
            console.error('[LOAD-PROJECTS] 需要登录');
            showError('请先登录');
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        console.log('[LOAD-PROJECTS] 项目数量:', result.projects?.length || 0);
        
        // 只有没有 URL 参数时才更新选择器
        if (!urlProjectTitle) {
            updateProjectSelector(result.projects || []);
        }
        
        // 如果有 URL 参数项目，自动加载
        if (urlProjectTitle) {
            console.log('[LOAD-PROJECTS] 自动加载 URL 参数项目:', urlProjectTitle);
            currentProjectTitle = urlProjectTitle;
            // 更新项目显示
            const projectNameDisplay = document.getElementById('project-name-display');
            if (projectNameDisplay) {
                projectNameDisplay.textContent = urlProjectTitle;
            }
            await loadStorylineByTitle(urlProjectTitle);
        } else {
            showEmptyState();
        }
    } catch (error) {
        console.error('[LOAD-PROJECTS] 加载失败:', error);
        showError(`加载项目失败: ${error.message}`);
    }
}

function updateProjectSelector(projects) {
    const selectElement = document.getElementById('project-select');
    if (!selectElement) return;
    
    selectElement.innerHTML = '<option value="">选择项目...</option>';
    
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
    if (!selectElement) return;
    
    const projectTitle = selectElement.value;
    if (!projectTitle) {
        showEmptyState();
        return;
    }
    
    await loadStorylineByTitle(projectTitle);
}

async function loadStorylineByTitle(projectTitle) {
    console.log('[LOAD-STORYLINE] 加载项目:', projectTitle);
    
    currentProjectTitle = projectTitle;
    
    // 更新项目名显示
    const projectNameDisplay = document.getElementById('project-name-display');
    if (projectNameDisplay) {
        projectNameDisplay.textContent = projectTitle;
    }
    
    try {
        showLoadingState();
        
        const apiUrl = `/api/storyline/${encodeURIComponent(projectTitle)}`;
        const response = await fetch(apiUrl);
        
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
        console.error('[LOAD-STORYLINE] 加载失败:', error);
        showError(`加载失败: ${error.message}`);
    }
}

function renderStoryline(storyline) {
    console.log('[RENDER] 开始渲染故事线');
    
    try {
        hideAllStates();
        
        const storylineMain = document.getElementById('storyline-main');
        if (!storylineMain) {
            showError('页面元素初始化失败');
            return;
        }
        
        storylineMain.style.display = 'block';
        
        // 更新阶段信息
        const isMultiStage = storyline.stage_info && Array.isArray(storyline.stage_info) && storyline.stage_info.length > 0;
        
        if (isMultiStage) {
            const stageInfo = storyline.stage_info.map(si =>
                `${si.stage_name} (${si.chapter_range}, ${si.major_event_count}个事件)`
            ).join(' → ');
            
            setTextContent('stage-name', `全书故事线 (${storyline.stage_info.length}个阶段)`);
            setTextContent('chapter-range-text', stageInfo);
        } else {
            setTextContent('stage-name', storyline.stage_name || '全书故事线');
            setTextContent('chapter-range-text', storyline.chapter_range || '全章节');
        }
        
        // 渲染重大事件列表
        const majorEvents = storyline.major_events || [];
        renderMajorEventsList(majorEvents);
        
        // 更新事件计数
        const countElement = document.getElementById('major-events-count');
        if (countElement) {
            countElement.textContent = `${majorEvents.length} 个`;
        }
        
        // 重置状态
        selectedMajorEventIndex = null;
        hasUnsavedChanges = false;
        updateSaveButton();
        
        // 重置详情面板
        resetDetailPanel();
        
        console.log('[RENDER] 渲染完成');
    } catch (error) {
        console.error('[RENDER] 渲染出错:', error);
        showError(`渲染失败: ${error.message}`);
    }
}

function setTextContent(elementId, text) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = text;
    }
}

function resetDetailPanel() {
    const titleElement = document.getElementById('detail-panel-title');
    const subtitleElement = document.getElementById('detail-panel-subtitle');
    const contentElement = document.getElementById('detail-panel-content');
    
    if (titleElement) titleElement.textContent = '📋 事件详情';
    if (subtitleElement) subtitleElement.textContent = '请选择一个重大事件';
    if (contentElement) {
        contentElement.innerHTML = `
            <div class="storyline-empty-selection">
                <div class="storyline-empty-selection__icon">👈</div>
                <p class="storyline-empty-selection__text">请从左侧选择一个重大事件查看详情</p>
            </div>
        `;
    }
}

// ==================== 重大事件列表渲染 ====================

function renderMajorEventsList(majorEvents) {
    const listContainer = document.getElementById('major-events-list');
    if (!listContainer) return;
    
    listContainer.innerHTML = '';
    
    if (majorEvents.length === 0) {
        listContainer.innerHTML = '<div class="storyline-empty-selection__text" style="padding: 20px; text-align: center;">暂无重大事件</div>';
        return;
    }
    
    majorEvents.forEach((event, index) => {
        const card = createMajorEventCard(event, index);
        listContainer.appendChild(card);
    });
}

function createMajorEventCard(event, index) {
    const card = document.createElement('div');
    card.className = 'timeline-card';
    card.dataset.index = index;
    card.onclick = () => selectMajorEvent(index);
    
    const displayName = event.name || event.main_goal || `重大事件 ${index + 1}`;
    
    // 情绪强度
    const intensity = event.emotional_intensity || 'medium';
    const emotionClass = `timeline-badge--emotion-${intensity}`;
    
    // 期待感徽章
    const expectationBadge = getExpectationBadge(event);
    
    const content = document.createElement('div');
    content.className = 'timeline-card__content';
    content.innerHTML = `
        <div class="timeline-card__header">
            <div class="timeline-card__title">${escapeHtml(displayName)}</div>
            <div class="timeline-card__number">${index + 1}</div>
        </div>
        <div class="timeline-card__badges">
            <span class="timeline-badge timeline-badge--chapter">${event.chapter_range || '全章节'}</span>
            ${event.emotional_focus ? `<span class="timeline-badge ${emotionClass}">${event.emotional_focus}</span>` : ''}
            ${expectationBadge}
        </div>
        <div class="timeline-card__preview">${escapeHtml(event.main_goal || event.description || event.role_in_stage_arc || '')}</div>
    `;
    
    card.appendChild(content);
    return card;
}

function selectMajorEvent(index) {
    // 更新选中状态
    const cards = document.querySelectorAll('.timeline-card');
    cards.forEach(card => card.classList.remove('active'));
    if (cards[index]) {
        cards[index].classList.add('active');
    }
    
    selectedMajorEventIndex = index;
    
    // 渲染详情
    try {
        renderMajorEventDetail(index);
    } catch (error) {
        console.error('[ERROR] 渲染详情时出错:', error);
        showV2Notification(`显示详情失败: ${error.message}`, 'error');
    }
}

// ==================== 详情面板渲染 ====================

function renderMajorEventDetail(index) {
    const event = currentStorylineData.major_events[index];
    if (!event) {
        showV2Notification('事件数据不存在', 'error');
        return;
    }
    
    const titleElement = document.getElementById('detail-panel-title');
    const subtitleElement = document.getElementById('detail-panel-subtitle');
    const contentElement = document.getElementById('detail-panel-content');
    
    if (!contentElement) return;
    
    const displayName = event.name || event.main_goal || `重大事件 ${index + 1}`;
    const stageInfo = event._stage ? `【${event._stage}】` : '';
    
    if (titleElement) {
        titleElement.innerHTML = `📋 ${stageInfo}${escapeHtml(displayName)}`;
    }
    if (subtitleElement) {
        subtitleElement.textContent = event.chapter_range || event._chapter_range || '全章节';
    }
    
    // 获取期待感信息
    const expectationInfo = getExpectationInfo(event);
    
    let html = '<div class="detail-content">';
    
    // 元信息
    html += `
        <div class="detail-meta">
            <div class="detail-meta__item">
                <span class="detail-meta__label">章节范围</span>
                <span class="detail-meta__value">${event.chapter_range || '全章节'}</span>
            </div>
            <div class="detail-meta__item">
                <span class="detail-meta__label">情绪强度</span>
                <span class="detail-meta__value">${getEmotionIntensityText(event.emotional_intensity)}</span>
            </div>
        </div>
    `;
    
    // 期待感区域
    if (expectationInfo) {
        html += `
            <div class="detail-section expectation-section">
                <div class="detail-section__title">🎯 期待感设置</div>
                <div class="detail-section__content">${expectationInfo}</div>
            </div>
        `;
    }
    
    // 主要目标
    html += `
        <div class="detail-section">
            <div class="detail-section__title">🎯 主要目标</div>
            <textarea class="editable-textarea" data-field="main_goal" data-index="${index}">${escapeHtml(event.main_goal || event.role_in_stage_arc || '')}</textarea>
        </div>
    `;
    
    // 情绪焦点
    html += `
        <div class="detail-section">
            <div class="detail-section__title">💭 情绪焦点</div>
            <textarea class="editable-textarea" data-field="emotional_focus" data-index="${index}">${escapeHtml(event.emotional_focus || event.emotional_goal || '')}</textarea>
        </div>
    `;
    
    // 详细描述
    html += `
        <div class="detail-section">
            <div class="detail-section__title">📝 详细描述</div>
            <textarea class="editable-textarea" data-field="description" data-index="${index}">${escapeHtml(event.description || '')}</textarea>
        </div>
    `;
    
    // 关键情绪节拍
    const keyBeats = event.key_emotional_beats || [];
    if (keyBeats.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section__title">🎵 关键情绪节拍</div>
                <ul class="detail-list">
                    ${keyBeats.map(beat => `<li class="detail-list__item">${escapeHtml(beat)}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    // 中级事件
    const mediumEvents = extractMediumEvents(event);
    if (mediumEvents.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section__title">🔸 中级事件 (${mediumEvents.length})</div>
                <div class="medium-events">
                    ${mediumEvents.map((me, meIndex) => createMediumEventHTML(me, meIndex, index)).join('')}
                </div>
            </div>
        `;
    }
    
    html += '</div>';
    
    contentElement.innerHTML = html;
    
    // 绑定编辑事件
    bindEditableFields();
}

function extractMediumEvents(event) {
    let mediumEvents = [];
    
    if (event.composition && typeof event.composition === 'object' && Object.keys(event.composition).length > 0) {
        const phases = ['起', '承', '转', '合'];
        phases.forEach(phase => {
            if (event.composition[phase] && Array.isArray(event.composition[phase])) {
                event.composition[phase].forEach(me => {
                    me.phase = phase;
                    mediumEvents.push(me);
                });
            }
        });
    } else if (event._medium_events && event._medium_events.length > 0) {
        mediumEvents = event._medium_events;
    } else if (event.medium_events && event.medium_events.length > 0) {
        mediumEvents = event.medium_events;
    }
    
    return mediumEvents;
}

function createMediumEventHTML(event, eventIndex, majorIndex) {
    const displayName = event.name || event.main_goal || `中级事件 ${eventIndex + 1}`;
    const fieldId = `medium-${majorIndex}-${eventIndex}`;
    const phase = event.phase || '起';
    const phaseIndex = ['起', '承', '转', '合'].indexOf(phase) + 1;
    const chapterRange = event._chapter_range_normalized || event.chapter_range || '';
    
    const specialEmotionalEvents = event.special_emotional_events || [];
    const hasSpecialEvents = specialEmotionalEvents.length > 0;
    
    let specialEventsHtml = '';
    if (hasSpecialEvents) {
        specialEventsHtml = `
            <div class="medium-event__field">
                <label class="medium-event__label">✨ 特殊情感事件 (${specialEmotionalEvents.length})</label>
                <div class="special-events">
                    ${specialEmotionalEvents.map(se => `
                        <div class="special-event">
                            <div class="special-event__header">
                                <div class="special-event__name">${escapeHtml(se.name || '特殊事件')}</div>
                                ${se.target_chapter ? `<div class="special-event__chapter">第${se.target_chapter}章</div>` : ''}
                            </div>
                            ${se.purpose ? `<div class="special-event__field"><strong>目的:</strong> ${escapeHtml(se.purpose)}</div>` : ''}
                            ${se.emotional_tone ? `<div class="special-event__field"><strong>情感基调:</strong> ${escapeHtml(se.emotional_tone)}</div>` : ''}
                            ${se.key_elements && se.key_elements.length > 0 ? `<div class="special-event__field"><strong>关键元素:</strong> ${escapeHtml(se.key_elements.join(', '))}</div>` : ''}
                            ${se.context_hint ? `<div class="special-event__field"><strong>上下文:</strong> ${escapeHtml(se.context_hint)}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    return `
        <div class="medium-event ${hasSpecialEvents ? 'has-special-events' : ''}">
            <div class="medium-event__header" onclick="toggleMediumEvent('${fieldId}')">
                <span class="medium-event__title">${escapeHtml(displayName)}</span>
                <div class="medium-event__badges">
                    <span class="timeline-badge timeline-badge--chapter">${phase} ${phaseIndex}</span>
                    ${chapterRange ? `<span class="timeline-badge timeline-badge--chapter">${escapeHtml(chapterRange)}</span>` : ''}
                    ${hasSpecialEvents ? `<span class="timeline-badge badge-expectation">✨ ${specialEmotionalEvents.length}</span>` : ''}
                </div>
            </div>
            <div class="medium-event__body" id="${fieldId}">
                ${specialEventsHtml}
                <div class="medium-event__field">
                    <label class="medium-event__label">🎯 主要目标</label>
                    <textarea class="editable-textarea" data-field="main_goal" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.main_goal || event.role_in_stage_arc || '')}</textarea>
                </div>
                <div class="medium-event__field">
                    <label class="medium-event__label">💭 情绪焦点</label>
                    <textarea class="editable-textarea" data-field="emotional_focus" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.emotional_focus || '')}</textarea>
                </div>
                ${event.description ? `
                <div class="medium-event__field">
                    <label class="medium-event__label">📝 描述</label>
                    <textarea class="editable-textarea" data-field="description" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.description)}</textarea>
                </div>
                ` : ''}
            </div>
        </div>
    `;
}

function toggleMediumEvent(fieldId) {
    const body = document.getElementById(fieldId);
    if (body) {
        body.classList.toggle('expanded');
    }
}

// ==================== 编辑功能 ====================

function bindEditableFields() {
    const fields = document.querySelectorAll('.editable-textarea');
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
        saveBtn.style.display = hasUnsavedChanges ? 'inline-flex' : 'none';
    }
}

// ==================== 保存功能 ====================

async function saveStorylineChanges() {
    if (!hasUnsavedChanges) return;
    
    const saveBtn = document.getElementById('btn-save');
    if (!saveBtn) return;
    
    const originalText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span>⏳</span> 保存中...';
    
    try {
        const changedFields = document.querySelectorAll('.editable-textarea.changed');
        
        changedFields.forEach(field => {
            const fieldName = field.dataset.field;
            const value = field.value;
            
            if (field.dataset.major !== undefined && field.dataset.medium !== undefined) {
                const majorIndex = parseInt(field.dataset.major);
                const mediumIndex = parseInt(field.dataset.medium);
                if (currentStorylineData.major_events[majorIndex].medium_events) {
                    currentStorylineData.major_events[majorIndex].medium_events[mediumIndex][fieldName] = value;
                }
            } else if (field.dataset.index !== undefined) {
                const index = parseInt(field.dataset.index);
                currentStorylineData.major_events[index][fieldName] = value;
            }
        });
        
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
            changedFields.forEach(field => field.classList.remove('changed'));
            hasUnsavedChanges = false;
            updateSaveButton();
            showV2Notification('保存成功！', 'success');
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        showV2Notification(`保存失败: ${error.message}`, 'error');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalText;
    }
}

// ==================== 通知功能 ====================

function showV2Notification(message, type = 'info') {
    const container = document.getElementById('notification-container');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `v2-notification v2-notification--${type}`;
    notification.textContent = message;
    
    container.appendChild(notification);
    
    // 触发动画
    requestAnimationFrame(() => {
        notification.classList.add('v2-notification--show');
    });
    
    setTimeout(() => {
        notification.classList.remove('v2-notification--show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ==================== 状态显示功能 ====================

function showLoadingState() {
    hideAllStates();
    const el = document.getElementById('loading-state');
    if (el) el.style.display = 'flex';
}

function showError(message) {
    hideAllStates();
    const errorEl = document.getElementById('error-state');
    const msgEl = document.getElementById('error-message');
    if (errorEl) errorEl.style.display = 'flex';
    if (msgEl) msgEl.textContent = message;
}

function showEmptyState() {
    hideAllStates();
    const el = document.getElementById('empty-state');
    if (el) el.style.display = 'flex';
}

function hideAllStates() {
    const ids = ['loading-state', 'error-state', 'empty-state', 'storyline-main'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
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

// ==================== 键盘快捷键 ====================

document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.key === 's') {
        event.preventDefault();
        if (hasUnsavedChanges) {
            saveStorylineChanges();
        }
    }
});

// ==================== 期待感相关功能 ====================

function getExpectationBadge(event) {
    if (event.expectation_tag && event.expectation_tag.type) {
        return createExpectationBadgeHTML(event.expectation_tag.type, event.expectation_tag.status || 'planted');
    }
    
    const expectationMaps = currentStorylineData?.expectation_maps || currentStorylineData?.expectation_map;
    if (!expectationMaps) return '';
    
    let allExpectations = [];
    const stageNames = Object.keys(expectationMaps);
    const isMultiStage = stageNames.some(key => 
        ['opening_stage', 'development_stage', 'climax_stage', 'ending_stage'].includes(key) ||
        ['opening', 'development', 'climax', 'ending'].includes(key)
    );
    
    if (isMultiStage) {
        stageNames.forEach(stageName => {
            const stageMap = expectationMaps[stageName];
            if (stageMap && stageMap.expectations) {
                allExpectations.push(...Object.values(stageMap.expectations));
            }
        });
    } else if (expectationMaps.expectations) {
        allExpectations = Object.values(expectationMaps.expectations);
    }
    
    const eventExpectations = allExpectations.filter(exp => {
        if (event.id && exp.event_id === event.id) return true;
        
        if (!event.id && exp.event_id && exp.event_id.startsWith('event_')) {
            const expEventName = exp.event_id.replace('event_', '');
            if (expEventName === event.name || (event.main_goal && event.main_goal.includes(expEventName))) {
                return true;
            }
        }
        
        const shortName = event.name ? event.name.split('：')[0].split(':')[0].trim() : '';
        const shortMainGoal = event.main_goal ? event.main_goal.split('：')[0].split(':')[0].trim() : '';
        const matchName = shortName || shortMainGoal;
        
        if (matchName && exp.description && exp.description.includes(matchName)) {
            return true;
        }
        
        const eventName = event.name || event.main_goal || '';
        if (exp.description && exp.description.includes(eventName)) {
            return true;
        }
        
        return false;
    });
    
    if (eventExpectations.length === 0) return '';
    
    const expectation = eventExpectations[0];
    return createExpectationBadgeHTML(expectation.type, expectation.status);
}

function createExpectationBadgeHTML(type, status) {
    const typeLabels = {
        'showcase': '展示橱窗',
        'suppression_release': '压抑释放',
        'nested_doll': '套娃期待',
        'emotional_hook': '情绪钩子',
        'power_gap': '实力差距',
        'mystery_foreshadow': '伏笔揭秘',
        'pig_eats_tiger': '扮猪吃虎',
        'show_off_face_slap': '装逼打脸',
        'identity_reveal': '身份反转',
        'beauty_favor': '美人恩',
        'fortuitous_encounter': '机缘巧合',
        'competition': '比试切磋',
        'auction_treasure': '拍卖会争宝',
        'secret_realm_exploration': '秘境探险',
        'alchemy_crafting': '炼丹炼器',
        'formation_breaking': '阵法破解',
        'sect_mission': '宗门任务',
        'cross_world_teleport': '跨界传送',
        'crisis_rescue': '危机救援',
        'master_inheritance': '师恩传承'
    };
    
    const typeLabel = typeLabels[type] || type;
    const statusColors = {
        'planted': '#10b981',
        'fermenting': '#f59e0b',
        'ready_to_release': '#ef4444',
        'released': '#6b7280',
        'failed': '#ef4444'
    };
    
    const statusColor = statusColors[status] || '#6b7280';
    
    return `<span class="timeline-badge badge-expectation" style="background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.3); color: #a78bfa;">🎯 ${typeLabel}</span>`;
}

function getExpectationInfo(event) {
    const expectationMaps = currentStorylineData?.expectation_maps || currentStorylineData?.expectation_map;
    if (!expectationMaps) return null;
    
    let allExpectations = [];
    const stageNames = Object.keys(expectationMaps);
    const isMultiStage = stageNames.some(key => ['opening', 'development', 'climax', 'ending'].includes(key));
    
    if (isMultiStage) {
        stageNames.forEach(stageName => {
            const stageMap = expectationMaps[stageName];
            if (stageMap && stageMap.expectations) {
                allExpectations.push(...Object.values(stageMap.expectations));
            }
        });
    } else if (expectationMaps.expectations) {
        allExpectations = Object.values(expectationMaps.expectations);
    }
    
    const eventExpectations = allExpectations.filter(exp => {
        if (event.id && exp.event_id === event.id) return true;
        
        if (!event.id && exp.event_id && exp.event_id.startsWith('event_')) {
            const expEventName = exp.event_id.replace('event_', '');
            if (expEventName === event.name || (event.main_goal && event.main_goal.includes(expEventName))) {
                return true;
            }
        }
        
        const shortName = event.name ? event.name.split('：')[0].split(':')[0].trim() : '';
        const shortMainGoal = event.main_goal ? event.main_goal.split('：')[0].split(':')[0].trim() : '';
        const matchName = shortName || shortMainGoal;
        
        if (matchName && exp.description && exp.description.includes(matchName)) {
            return true;
        }
        
        const eventName = event.name || event.main_goal || '';
        if (exp.description && exp.description.includes(eventName)) {
            return true;
        }
        
        return false;
    });
    
    if (eventExpectations.length === 0) return null;
    
    const expectation = eventExpectations[0];
    const typeLabels = {
        'showcase': '展示橱窗效应',
        'suppression_release': '压抑与释放',
        'nested_doll': '套娃式期待',
        'emotional_hook': '情绪钩子',
        'power_gap': '实力差距期待',
        'mystery_foreshadow': '伏笔揭秘期待',
        'pig_eats_tiger': '扮猪吃虎',
        'show_off_face_slap': '装逼打脸',
        'identity_reveal': '身份反转',
        'beauty_favor': '美人恩',
        'fortuitous_encounter': '机缘巧合',
        'competition': '比试切磋',
        'auction_treasure': '拍卖会争宝',
        'secret_realm_exploration': '秘境探险',
        'alchemy_crafting': '炼丹炼器',
        'formation_breaking': '阵法破解',
        'sect_mission': '宗门任务',
        'cross_world_teleport': '跨界传送',
        'crisis_rescue': '危机救援',
        'master_inheritance': '师恩传承'
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
        <div class="expectation-info">
            <div class="expectation-info__header">
                <span class="expectation-info__icon">🎯</span>
                <strong class="expectation-info__type">${typeLabel}</strong>
                <span class="expectation-info__status">${statusLabel}</span>
            </div>
    `;
    
    if (expectation.description) {
        html += `<div class="expectation-info__desc">${escapeHtml(expectation.description)}</div>`;
    }
    
    if (expectation.planted_chapter) {
        html += `<div class="expectation-info__timeline">`;
        html += `<span>种植: 第${expectation.planted_chapter}章</span>`;
        if (expectation.target_chapter) {
            html += `<span class="expectation-info__arrow">→</span>`;
            html += `<span>目标: 第${expectation.target_chapter}章</span>`;
        }
        html += `</div>`;
    }
    
    if (expectation.released_chapter) {
        html += `<div class="expectation-info__release">`;
        html += `<span>释放: 第${expectation.released_chapter}章</span>`;
        if (expectation.satisfaction_score) {
            html += `<span class="expectation-info__score">满足度: ${expectation.satisfaction_score.toFixed(1)}/10</span>`;
        }
        html += `</div>`;
    }
    
    html += `</div>`;
    
    return html;
}
