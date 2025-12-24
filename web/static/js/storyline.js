// 故事线时间线页面JavaScript

let currentStorylineData = null;
let currentProjectTitle = null;

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
    
    // 显示时间线容器
    const timelineContainer = document.getElementById('timeline-container');
    timelineContainer.style.display = 'block';
    
    // 更新阶段信息
    document.getElementById('stage-name').textContent = storyline.stage_name || '全书故事线';
    document.getElementById('chapter-range-text').textContent = storyline.chapter_range || '全章节';
    
    // 渲染事件
    const eventsContainer = document.getElementById('timeline-events');
    eventsContainer.innerHTML = '';
    
    // 检查是否有重大事件
    if (!storyline.major_events || storyline.major_events.length === 0) {
        eventsContainer.innerHTML = '<div class="no-events">暂无故事线事件数据</div>';
        return;
    }
    
    // 合并所有重大事件和中型事件
    const allEvents = [];
    
    storyline.major_events.forEach((majorEvent, majorIndex) => {
        // 添加重大事件
        allEvents.push({
            type: 'major',
            order: majorIndex + 1,
            data: majorEvent
        });
        
        // 添加中型事件（如果存在）
        if (majorEvent.medium_events && majorEvent.medium_events.length > 0) {
            majorEvent.medium_events.forEach((mediumEvent, mediumIndex) => {
                allEvents.push({
                    type: 'medium',
                    order: mediumIndex + 1,
                    parentIndex: majorIndex + 1,
                    data: mediumEvent,
                    specialEvents: majorEvent.special_events || []
                });
            });
        }
    });
    
    // 渲染所有事件
    allEvents.forEach(event => {
        const eventElement = createEventElement(event);
        eventsContainer.appendChild(eventElement);
    });
    
    console.log(`✅ 渲染了 ${allEvents.length} 个事件 (重大事件: ${storyline.major_events.length})`);
}

function createEventElement(event) {
    const isMajor = event.type === 'major';
    const data = event.data;
    
    const eventDiv = document.createElement('div');
    eventDiv.className = 'timeline-event';
    
    // 创建节点
    const node = document.createElement('div');
    node.className = 'event-node';
    if (isMajor) {
        node.style.borderColor = '#667eea';
        node.style.boxShadow = '0 0 0 4px rgba(102, 126, 234, 0.3)';
    }
    eventDiv.appendChild(node);
    
    // 创建内容卡片
    const content = document.createElement('div');
    content.className = 'event-content';
    content.onclick = () => showEventModal(event);
    
    const header = document.createElement('div');
    header.className = 'event-header';
    
    const titleDiv = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'event-title';
    
    // 确保显示有意义的名称
    const displayName = data.name || data.main_goal || (isMajor ? `重大事件 ${event.order}` : `中型事件 ${event.order}`);
    title.textContent = displayName;
    titleDiv.appendChild(title);
    
    const badges = document.createElement('div');
    badges.style.marginTop = '8px';
    
    const chapterBadge = document.createElement('span');
    chapterBadge.className = 'event-chapter';
    chapterBadge.textContent = data.chapter_range || '全章节';
    badges.appendChild(chapterBadge);
    
    if (!isMajor) {
        const phaseBadge = document.createElement('span');
        phaseBadge.className = 'event-phase';
        phaseBadge.textContent = `${data.phase || '阶段'} ${event.order}`;
        badges.appendChild(phaseBadge);
    } else {
        const typeBadge = document.createElement('span');
        typeBadge.className = 'event-phase';
        typeBadge.textContent = '重大事件';
        typeBadge.style.background = 'linear-gradient(135deg, rgba(102, 126, 234, 0.2), rgba(118, 75, 162, 0.2))';
        typeBadge.style.color = '#667eea';
        badges.appendChild(typeBadge);
    }
    
    titleDiv.appendChild(badges);
    header.appendChild(titleDiv);
    
    content.appendChild(header);
    
    // 描述 - 优先使用description，如果没有则使用main_goal
    const descriptionText = data.description || data.main_goal || data.role_in_stage_arc || '';
    if (descriptionText) {
        const description = document.createElement('div');
        description.className = 'event-description';
        description.textContent = descriptionText;
        if (description.textContent.length > 100) {
            description.textContent = description.textContent.substring(0, 100) + '...';
        }
        content.appendChild(description);
    }
    
    // 情绪信息
    const emotionText = data.emotional_focus || data.emotional_goal || '';
    if (emotionText) {
        const emotionDiv = document.createElement('div');
        emotionDiv.className = 'event-emotion';
        
        const intensity = data.emotional_intensity || 'medium';
        const indicator = document.createElement('span');
        indicator.className = `emotion-indicator ${intensity}`;
        
        const label = document.createElement('span');
        label.className = 'emotion-label';
        label.textContent = '情绪焦点:';
        
        const value = document.createElement('span');
        value.className = 'emotion-value';
        value.textContent = emotionText;
        
        emotionDiv.appendChild(indicator);
        emotionDiv.appendChild(label);
        emotionDiv.appendChild(value);
        content.appendChild(emotionDiv);
    }
    
    eventDiv.appendChild(content);
    
    return eventDiv;
}

// ==================== 事件详情模态框 ====================

function showEventModal(event) {
    const data = event.data;
    const isMajor = event.type === 'major';
    
    // 设置标题 - 确保有意义的显示
    const displayName = data.name || data.main_goal || (isMajor ? `重大事件 ${event.order}` : `中型事件 ${event.order}`);
    document.getElementById('modal-event-name').textContent = displayName;
    
    // 设置元数据
    document.getElementById('modal-chapter-range').textContent = data.chapter_range || '全章节';
    document.getElementById('modal-event-type').textContent = isMajor ? '重大事件' : `${data.phase || '阶段'}事件`;
    
    const intensity = data.emotional_intensity || 'medium';
    const intensityText = {
        'high': '高',
        'medium': '中',
        'low': '低'
    }[intensity] || '中';
    document.getElementById('modal-emotional-intensity').textContent = intensityText;
    
    // 主要目标 - 优先使用main_goal，如果没有则使用role_in_stage_arc
    const mainGoal = data.main_goal || data.role_in_stage_arc || '暂无主要目标';
    document.getElementById('modal-main-goal').textContent = mainGoal;
    
    // 情绪焦点 - 优先使用emotional_focus，如果没有则使用emotional_goal
    const emotionalFocus = data.emotional_focus || data.emotional_goal || data.role_in_stage_arc || '暂无情绪焦点';
    document.getElementById('modal-emotional-focus').textContent = emotionalFocus;
    
    // 详细描述 - 使用description或main_goal
    const description = data.description || data.main_goal || data.role_in_stage_arc || '暂无详细描述';
    document.getElementById('modal-description').textContent = description;
    
    // 关键情绪节拍
    const beatsSection = document.getElementById('modal-beats-section');
    const keyBeats = data.key_emotional_beats || [];
    
    if (keyBeats && keyBeats.length > 0) {
        beatsSection.style.display = 'block';
        const beatsList = document.getElementById('modal-key-beats');
        beatsList.innerHTML = '';
        keyBeats.forEach(beat => {
            const li = document.createElement('li');
            li.textContent = beat;
            beatsList.appendChild(li);
        });
    } else {
        beatsSection.style.display = 'none';
    }
    
    // 特殊情感事件
    const specialSection = document.getElementById('modal-special-section');
    const specialEvents = event.specialEvents || [];
    
    if (specialEvents && specialEvents.length > 0) {
        specialSection.style.display = 'block';
        const specialContainer = document.getElementById('modal-special-events');
        specialContainer.innerHTML = '';
        
        specialEvents.forEach(specialEvent => {
            const card = document.createElement('div');
            card.className = 'special-event-card';
            
            const title = document.createElement('h4');
            title.textContent = specialEvent.name || specialEvent.event_subtype || '特殊事件';
            card.appendChild(title);
            
            const purpose = document.createElement('p');
            purpose.textContent = specialEvent.purpose || specialEvent.placement_hint || '-';
            card.appendChild(purpose);
            
            specialContainer.appendChild(card);
        });
    } else {
        specialSection.style.display = 'none';
    }
    
    // 显示模态框
    document.getElementById('event-modal').style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeEventModal() {
    document.getElementById('event-modal').style.display = 'none';
    document.body.style.overflow = '';
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
    document.getElementById('timeline-container').style.display = 'none';
}

// ==================== 键盘事件处理 ====================

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closeEventModal();
    }
});

// 点击模态框外部关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('event-modal');
    if (event.target === modal.querySelector('.modal-overlay')) {
        closeEventModal();
    }
});