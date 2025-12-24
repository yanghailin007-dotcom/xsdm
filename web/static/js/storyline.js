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
    
    // 更新阶段信息
    document.getElementById('stage-name').textContent = storyline.stage_name || '全书故事线';
    document.getElementById('chapter-range-text').textContent = storyline.chapter_range || '全章节';
    
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
    
    card.innerHTML = `
        <div class="major-event-header">
            <div class="major-event-title">${escapeHtml(displayName)}</div>
            <div class="major-event-number">${index + 1}</div>
        </div>
        <div class="major-event-badges">
            <span class="event-badge badge-chapter">${event.chapter_range || '全章节'}</span>
            ${event.emotional_focus ? `<span class="event-badge badge-emotion" style="color: ${emotionColor}; background: ${emotionColor}15;">${event.emotional_focus}</span>` : ''}
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
    
    // 渲染右侧详情
    renderMajorEventDetail(index);
}

function renderMajorEventDetail(index) {
    const event = currentStorylineData.major_events[index];
    const contentContainer = document.getElementById('medium-events-content');
    
    // 更新面板标题
    const displayName = event.name || event.main_goal || `重大事件 ${index + 1}`;
    document.getElementById('medium-panel-title').innerHTML = `📋 ${escapeHtml(displayName)}`;
    document.getElementById('medium-panel-subtitle').textContent = `${event.chapter_range || '全章节'}`;
    
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
    
    // 特殊情感事件
    const specialEvents = event.special_events || [];
    if (specialEvents.length > 0) {
        html += `
            <div class="detail-section">
                <div class="detail-section-title">✨ 特殊情感事件</div>
                <div class="special-events-grid">
                    ${specialEvents.map(se => `
                        <div class="special-event-card">
                            <h4>${escapeHtml(se.name || se.event_subtype || '特殊事件')}</h4>
                            <p>${escapeHtml(se.purpose || se.placement_hint || '-')}</p>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // 中级事件列表
    const mediumEvents = event.medium_events || [];
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
    
    return `
        <div class="medium-event-card">
            <div class="medium-event-header" onclick="toggleMediumEvent('${fieldId}')">
                <span class="medium-event-title">${escapeHtml(displayName)}</span>
                <span class="medium-event-badge">${event.phase || '阶段'} ${eventIndex + 1}</span>
            </div>
            <div class="medium-event-body" id="${fieldId}">
                <div class="medium-event-field">
                    <label class="medium-field-label">🎯 主要目标</label>
                    <textarea class="editable-field" data-field="main_goal" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.main_goal || event.role_in_stage_arc || '')}</textarea>
                </div>
                <div class="medium-event-field">
                    <label class="medium-field-label">💭 情绪焦点</label>
                    <textarea class="editable-field" data-field="emotional_focus" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.emotional_focus || event.emotional_goal || '')}</textarea>
                </div>
                <div class="medium-event-field">
                    <label class="medium-field-label">📝 描述</label>
                    <textarea class="editable-field" data-field="description" data-major="${majorIndex}" data-medium="${eventIndex}">${escapeHtml(event.description || '')}</textarea>
                </div>
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

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);