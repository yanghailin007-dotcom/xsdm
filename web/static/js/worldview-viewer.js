// ==================== 小说可视化系统 ====================

// 全局状态
let currentView = 'overview';
let editMode = false;
let novelData = {
    projectTitle: '',
    novelTitle: '',
    synopsis: '',
    totalChapters: 0,
    completedChapters: 0,
    // 从产物中提取的数据
    worldview: null,
    characters: null,
    growth: null,
    storyline: null,
    writing: null,
    market: null
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    initializeNovelViewer();
    loadNovelData();
    initializeEventListeners();
});

async function initializeNovelViewer() {
    console.log('初始化小说可视化系统');
    
    // 从URL获取项目标题
    const urlParams = new URLSearchParams(window.location.search);
    const projectTitle = urlParams.get('title');
    
    if (projectTitle) {
        novelData.projectTitle = decodeURIComponent(projectTitle);
        await loadNovelData();
    } else {
        showStatusMessage('未找到项目参数', 'error');
    }
}

async function loadNovelData() {
    try {
        showStatusMessage('🔄 正在加载项目数据...', 'info');
        
        // 加载项目详情
        const projectResponse = await fetch(`/api/project/${encodeURIComponent(novelData.projectTitle)}/with-phase-info`);
        
        if (!projectResponse.ok) {
            throw new Error(`HTTP ${projectResponse.status}: ${projectResponse.statusText}`);
        }
        
        const projectDetail = await projectResponse.json();
        
        // 设置基本信息
        novelData.novelTitle = projectDetail.novel_title || projectDetail.title || '';
        novelData.synopsis = projectDetail.story_synopsis || projectDetail.description || '';
        novelData.totalChapters = projectDetail.phase_info?.total_chapters || projectDetail.total_chapters || 200;
        novelData.completedChapters = Object.keys(projectDetail.generated_chapters || {}).length;
        
        // 加载第一阶段产物
        const productsResponse = await fetch(`/api/phase-one/products/${encodeURIComponent(novelData.projectTitle)}`);
        
        if (!productsResponse.ok) {
            throw new Error(`HTTP ${productsResponse.status}: ${productsResponse.statusText}`);
        }
        
        const productsResult = await productsResponse.json();
        
        if (productsResult.success && productsResult.products) {
            novelData.worldview = productsResult.products.worldview;
            novelData.characters = productsResult.products.characters;
            novelData.growth = productsResult.products.growth;
            novelData.storyline = productsResult.products.storyline;
            novelData.writing = productsResult.products.writing;
            novelData.market = productsResult.products.market;
        }
        
        // 更新UI
        updateOverview();
        initializeViews();
        
        showStatusMessage('✅ 成功加载项目数据: ' + novelData.novelTitle, 'success');
        
    } catch (error) {
        console.error('加载项目数据失败:', error);
        showStatusMessage('❌ 加载失败: ' + error.message, 'error');
    }
}

// ==================== UI更新函数 ====================
function updateOverview() {
    // 更新概览统计
    document.getElementById('novel-title-display').textContent = novelData.novelTitle;
    document.getElementById('novel-synopsis-display').textContent = novelData.synopsis || '暂无简介';
    
    // 更新统计数据
    updateOverviewStats();
}

function updateOverviewStats() {
    // 计算角色数量
    let characterCount = 0;
    if (novelData.characters && novelData.characters.content) {
        try {
            const charData = JSON.parse(novelData.characters.content);
            if (Array.isArray(charData)) {
                characterCount = charData.length;
            }
        } catch (e) {
            console.log('解析角色数据失败:', e);
        }
    }
    
    // 计算势力数量
    let factionCount = 0;
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            if (worldviewData.factions && Array.isArray(worldviewData.factions)) {
                factionCount = worldviewData.factions.length;
            }
        } catch (e) {
            console.log('解析势力数据失败:', e);
        }
    }
    
    // 计算事件数量
    let eventCount = 0;
    if (novelData.storyline && novelData.storyline.content) {
        try {
            const storylineData = JSON.parse(novelData.storyline.content);
            if (storylineData.major_events && Array.isArray(storylineData.major_events)) {
                eventCount = storylineData.major_events.length;
            }
        } catch (e) {
            console.log('解析故事线数据失败:', e);
        }
    }
    
    document.getElementById('overview-chapters').textContent = novelData.totalChapters;
    document.getElementById('overview-characters').textContent = characterCount;
    document.getElementById('overview-factions').textContent = factionCount;
    document.getElementById('overview-events').textContent = eventCount;
}

function initializeViews() {
    // 初始化各个视图
    initializeCharactersView();
    initializeFactionsView();
    initializeTimelineView();
    initializeMapView();
    initializeSystemsView();
}

// ==================== 视图切换 ====================
function switchView(view) {
    currentView = view;
    
    // 更新按钮状态
    document.querySelectorAll('.view-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    const activeBtn = document.querySelector(`[data-view="${view}"]`);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // 更新视图显示
    document.querySelectorAll('.view').forEach(v => {
        v.classList.remove('active');
    });
    
    const targetView = document.getElementById(view + '-view');
    if (targetView) {
        targetView.classList.add('active');
        
        // 触发视图初始化
        switch(view) {
            case 'characters':
                redrawCharacterGraph();
                break;
            case 'factions':
                redrawFactionGraph();
                break;
            case 'timeline':
                updateTimelineView();
                break;
            case 'map':
                redrawMapView();
                break;
            case 'systems':
                updateSystemsView();
                break;
        }
    }
}

// ==================== 角色网络视图 ====================
function initializeCharactersView() {
    setTimeout(() => redrawCharacterGraph(), 100);
}

function redrawCharacterGraph() {
    const canvas = document.getElementById('characters-graph');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    // 绘制背景
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, width, height);
    
    // 提取角色数据
    let characters = [];
    if (novelData.characters && novelData.characters.content) {
        try {
            const characterData = JSON.parse(novelData.characters.content);
            if (Array.isArray(characterData)) {
                characters = characterData;
            }
        } catch (e) {
            console.log('解析角色数据失败:', e);
        }
    }
    
    if (characters.length === 0) {
        drawEmptyState(ctx, width, height, '暂无角色数据');
        return;
    }
    
    // 计算节点位置（圆形布局）
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;
    const nodePositions = {};
    
    characters.forEach((character, index) => {
        const name = character.name || character.characterName || '未命名角色';
        nodePositions[name] = {
            x: centerX + Math.cos((index / characters.length) * Math.PI * 2 - Math.PI / 2) * radius,
            y: centerY + Math.sin((index / characters.length) * Math.PI * 2 - Math.PI / 2) * radius,
            data: character
        };
    });
    
    // 绘制关系连线
    characters.forEach(character => {
        if (character.relationships && Array.isArray(character.relationships)) {
            character.relationships.forEach(relation => {
                const targetName = relation.related_character || relation.relatedCharacterName;
                if (nodePositions[targetName]) {
                    const start = nodePositions[name];
                    const end = nodePositions[targetName];
                    
                    ctx.beginPath();
                    ctx.moveTo(start.x, start.y);
                    ctx.lineTo(end.x, end.y);
                    
                    const relationType = relation.relation_type || 'neutral';
                    switch(relationType) {
                        case 'ally':
                            ctx.strokeStyle = '#10b981';
                            break;
                        case 'enemy':
                            ctx.strokeStyle = '#ef4444';
                            break;
                        case 'neutral':
                            ctx.strokeStyle = '#6b7280';
                            break;
                        default:
                            ctx.strokeStyle = '#667eea';
                    }
                    
                    ctx.lineWidth = 1.5;
                    ctx.stroke();
                }
            });
        }
    });
    
    // 绘制角色节点
    characters.forEach(character => {
        const name = character.name || character.characterName || '未命名';
        const pos = nodePositions[name];
        const color = character.color || '#667eea';
        const icon = character.icon || '👤';
        
        // 绘制节点背景
        const gradient = ctx.createRadialGradient(
            pos.x, pos.y, 0,
            pos.x, pos.y, 35
        );
        gradient.addColorStop(0, color);
        gradient.addColorStop(1, color + '40');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 32, 0, Math.PI * 2);
        ctx.fill();
        
        // 绘制边框
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // 绘制图标
        ctx.font = '20px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(icon, pos.x, pos.y);
        
        // 绘制名称
        ctx.font = 'bold 12px Arial';
        ctx.fillStyle = '#f1f5f9';
        ctx.fillText(name, pos.x, pos.y + 45);
    });
    
    // 更新角色详情
    updateCharacterDetails(characters);
}

function drawEmptyState(ctx, width, height, message) {
    ctx.fillStyle = '#6b7280';
    ctx.font = '16px Arial';
    ctx.textAlign = 'center';
    ctx.fillText(message, width / 2, height / 2);
}

function updateCharacterDetails(characters) {
    const container = document.getElementById('character-details');
    
    if (!characters || characters.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无角色数据</p>';
        return;
    }
    
    let html = '';
    characters.forEach(character => {
        const name = character.name || character.characterName || '未命名';
        const role = character.role || character.character_type || '未知角色';
        const description = character.description || character.personality || '暂无描述';
        const abilities = character.abilities || '';
        
        html += `
            <div class="detail-item">
                <h4>${name} <span class="badge">${role}</span></h4>
                <p>${description}</p>
                ${abilities ? `<p class="abilities"><strong>能力：</strong>${abilities}</p>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ==================== 势力关系视图 ====================
function initializeFactionsView() {
    setTimeout(() => redrawFactionGraph(), 100);
}

function redrawFactionGraph() {
    const canvas = document.getElementById('factions-graph');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = canvas.offsetHeight;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    // 绘制背景
    ctx.fillStyle = '#1e293b';
    ctx.fillRect(0, 0, width, height);
    
    // 提取势力数据
    let factions = [];
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            factions = worldviewData.factions || [];
        } catch (e) {
            console.log('解析势力数据失败:', e);
        }
    }
    
    if (factions.length === 0) {
        drawEmptyState(ctx, width, height, '暂无势力数据');
        return;
    }
    
    // 计算节点位置
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;
    const nodePositions = {};
    
    factions.forEach((faction, index) => {
        const angle = (index / factions.length) * Math.PI * 2 - Math.PI / 2;
        nodePositions[faction.name] = {
            x: centerX + Math.cos(angle) * radius,
            y: centerY + Math.sin(angle) * radius,
            data: faction
        };
    });
    
    // 绘制关系连线
    factions.forEach(faction => {
        if (faction.relations) {
            Object.entries(faction.relations).forEach(([targetFaction, relationType]) => {
                if (nodePositions[targetFaction]) {
                    const start = nodePositions[faction.name];
                    const end = nodePositions[targetFaction];
                    
                    ctx.beginPath();
                    ctx.moveTo(start.x, start.y);
                    ctx.lineTo(end.x, end.y);
                    
                    switch(relationType) {
                        case '敌对':
                            ctx.strokeStyle = '#ef4444';
                            ctx.setLineDash([5, 5]);
                            break;
                        case '联盟':
                            ctx.strokeStyle = '#10b981';
                            ctx.setLineDash([]);
                            break;
                        case '中立':
                            ctx.strokeStyle = '#6b7280';
                            ctx.setLineDash([2, 2]);
                            break;
                        default:
                            ctx.strokeStyle = '#667eea';
                            ctx.setLineDash([]);
                    }
                    
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    ctx.setLineDash([]);
                }
            });
        }
    });
    
    // 绘制势力节点
    factions.forEach(faction => {
        const pos = nodePositions[faction.name];
        const gradient = ctx.createRadialGradient(
            pos.x, pos.y, 0,
            pos.x, pos.y, 40
        );
        gradient.addColorStop(0, faction.color);
        gradient.addColorStop(1, faction.color + '40');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 38, 0, Math.PI * 2);
        ctx.fill();
        
        ctx.strokeStyle = faction.color;
        ctx.lineWidth = 3;
        ctx.stroke();
        
        ctx.font = '24px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(faction.icon, pos.x, pos.y);
        
        ctx.font = 'bold 14px Arial';
        ctx.fillStyle = '#f1f5f9';
        ctx.fillText(faction.name, pos.x, pos.y + 52);
    });
    
    // 更新势力详情
    updateFactionDetails(factions);
}

function updateFactionDetails(factions) {
    const container = document.getElementById('faction-details');
    
    if (!factions || factions.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无势力数据</p>';
        return;
    }
    
    let html = '';
    factions.forEach(faction => {
        html += `
            <div class="detail-item">
                <h4>${faction.icon} ${faction.name}</h4>
                <p>${faction.description}</p>
                ${faction.power ? `<p><strong>力量值：</strong>${faction.power}/100</p>` : ''}
                ${faction.territories && faction.territories.length > 0 ? 
                  `<p><strong>领土：</strong>${faction.territories.join('、')}</p>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// ==================== 故事事件时间轴视图 ====================
function initializeTimelineView() {
    updateTimelineView();
}

function updateTimelineView() {
    const container = document.getElementById('timeline-events');
    container.innerHTML = '';
    
    // 提取故事线数据
    let majorEvents = [];
    if (novelData.storyline && novelData.storyline.content) {
        try {
            const storylineData = JSON.parse(novelData.storyline.content);
            majorEvents = storylineData.major_events || [];
        } catch (e) {
            console.log('解析故事线数据失败:', e);
        }
    }
    
    if (majorEvents.length === 0) {
        container.innerHTML = '<p class="text-muted" style="text-align: center; padding: 40px;">暂无故事事件数据</p>';
        return;
    }
    
    // 显示重大事件
    majorEvents.forEach((event, index) => {
        const eventElement = document.createElement('div');
        eventElement.className = 'timeline-event';
        
        // 提取章节范围
        const chapterRange = event.chapter_range || event._chapter_range || '';
        const stage = event._stage || '未知阶段';
        
        eventElement.innerHTML = `
            <div class="event-number">${index + 1}</div>
            <h4>${event.name || event.main_goal || '未命名事件'}</h4>
            <div class="event-meta">
                <span class="event-stage">${stage}</span>
                ${chapterRange ? `<span class="event-range">${chapterRange}</span>` : ''}
            </div>
            <p>${event.description || event.summary || event.main_goal || '暂无描述'}</p>
        `;
        
        // 添加中级事件
        if (event._medium_events && event._medium_events.length > 0) {
            const mediumEventsDiv = document.createElement('div');
            mediumEventsDiv.className = 'medium-events';
            
            event._medium_events.forEach(me => {
                const meDiv = document.createElement('div');
                meDiv.className = 'medium-event';
                meDiv.innerHTML = `
                    <span class="phase-badge">${me._phase_name || '未分类'}</span>
                    <span class="chapter-range">${me._chapter_range_normalized || me.chapter_range || '未设定章节'}</span>
                    <p>${me.summary || me.description || ''}</p>
                `;
                mediumEventsDiv.appendChild(meDiv);
            });
            
            eventElement.appendChild(mediumEventsDiv);
        }
        
        container.appendChild(eventElement);
    });
}

// ==================== 世界地图视图 ====================
function initializeMapView() {
    setTimeout(() => redrawMapView(), 100);
}

function redrawMapView() {
    const canvas = document.getElementById('world-map');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.offsetWidth;
    const height = canvas.height = height;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    // 绘制背景
    drawMapBackground(ctx, width, height);
    
    // 提取地点数据
    let locations = [];
    let factions = [];
    
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            locations = worldviewData.locations || [];
            factions = worldviewData.factions || [];
        } catch (e) {
            console.log('解析世界观数据失败:', e);
        }
    }
    
    if (locations.length === 0) {
        drawEmptyState(ctx, width, height, '暂无地点数据');
        return;
    }
    
    // 绘制地点标记
    drawLocationMarkers(locations, factions);
}

function drawMapBackground(ctx, width, height) {
    const gradient = ctx.createRadialGradient(
        width / 2, height / 2, 0,
        width / 2, height / 2, Math.max(width, height) / 2
    );
    gradient.addColorStop(0, '#1e293b');
    gradient.addColorStop(1, '#0f172a');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
    
    // 绘制网格
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.1)';
    ctx.lineWidth = 1;
    
    const gridSize = 50;
    for (let x = 0; x < width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    for (let y = 0; y < height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
}

function drawLocationMarkers(locations, factions) {
    const container = document.getElementById('map-markers');
    container.innerHTML = '';
    
    const canvas = document.getElementById('world-map');
    const width = canvas.width;
    const height = canvas.height;
    
    locations.forEach(location => {
        const marker = document.createElement('div');
        marker.className = 'map-marker';
        marker.dataset.locationId = location.id;
        
        const x = (location.x / 100) * width;
        const y = (location.y / 100) * height;
        
        marker.style.left = `${x}px`;
        marker.style.top = `${y}px`;
        
        // 查找所属势力
        const faction = factions.find(f => f.name === location.faction);
        const color = faction ? faction.color : '#667eea';
        
        marker.innerHTML = `
            <div class="marker-icon" style="background: ${color};">
                ${getFactionIcon(location.faction)}
            </div>
            <div class="marker-label">${location.name}</div>
        `;
        
        marker.addEventListener('mouseenter', (e) => showLocationTooltip(e, location));
        marker.addEventListener('mouseleave', hideLocationTooltip);
        marker.addEventListener('click', () => focusOnLocation(location));
        
        container.appendChild(marker);
    });
    
    // 更新地点列表
    updateLocationList(locations);
}

function getFactionIcon(factionName) {
    if (!factionName) return '📍';
    
    if (factionName.includes('魔')) return '👿';
    if (factionName.includes('正') || factionName.includes('盟')) return '⚔️';
    if (factionName.includes('妖')) return '🐉';
    if (factionName.includes('道')) return '☯️';
    
    return '🏰';
}

function showLocationTooltip(e, location) {
    const tooltip = document.getElementById('map-tooltip');
    if (!tooltip) return;
    
    tooltip.innerHTML = `
        <h4>${location.name}</h4>
        <p>${location.description}</p>
        <p style="margin-top: 8px; font-size: 11px;">
            <strong>势力：</strong>${location.faction || '中立'}
        </p>
    `;
    
    tooltip.style.left = `${e.target.offsetLeft + 20}px`;
    tooltip.style.top = `${e.target.offsetTop - 10}px`;
    tooltip.classList.add('visible');
}

function hideLocationTooltip() {
    const tooltip = document.getElementById('map-tooltip');
    if (tooltip) {
        tooltip.classList.remove('visible');
    }
}

function focusOnLocation(location) {
    console.log('聚焦地点:', location.name);
}

function updateLocationList(locations) {
    const container = document.getElementById('location-list');
    container.innerHTML = '';
    
    if (!locations || locations.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无地点数据</p>';
        return;
    }
    
    locations.forEach(location => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.innerHTML = `
            <h4>${location.name}</h4>
            <p>${location.description}</p>
            <span class="badge">${location.faction || '中立'}</span>
        `;
        item.onclick = () => focusOnLocation(location);
        container.appendChild(item);
    });
}

// ==================== 系统设定视图 ====================
function initializeSystemsView() {
    updateSystemsView();
}

function updateSystemsView() {
    // 从产物数据中提取系统设定
    updateSystemContent('power-system', novelData.growth || novelData.worldview);
    updateSystemContent('magic-system', novelData.growth || novelData.worldview);
    updateSystemContent('social-system', novelData.growth || novelData.worldview);
    updateSystemContent('world-rules', novelData.growth || novelData.worldview);
}

function updateSystemContent(systemId, dataSource) {
    const container = document.querySelector(`#${systemId} .system-content`);
    if (!container) return;
    
    if (!dataSource || !dataSource.content) {
        container.innerHTML = '<p class="text-muted">暂无数据</p>';
        return;
    }
    
    let content = dataSource.content;
    if (typeof content === 'string') {
        try {
            content = JSON.parse(content);
        } catch (e) {
            // 不是JSON，直接显示
            content = { description: content };
        }
    }
    
    let html = '';
    
    if (content.description) {
        html += `<p>${content.description}</p>`;
    }
    
    if (content.levels && Array.isArray(content.levels)) {
        html += '<h4>等级划分</h4><ul>';
        content.levels.forEach(level => {
            html += `<li><strong>${level.name || level.title}</strong>：${level.description || ''}</li>`;
        });
        html += '</ul>';
    }
    
    if (content.rules && Array.isArray(content.rules)) {
        html += '<h4>相关规则</h4><ul>';
        content.rules.forEach(rule => {
            html += `<li>${rule.title || rule.name || ''}：${rule.description || ''}</li>`;
        });
        html += '</ul>';
    }
    
    if (html === '') {
        html = '<p class="text-muted">暂无详细数据</p>';
    }
    
    container.innerHTML = html;
}

// ==================== 编辑功能 ====================
function toggleEditMode() {
    editMode = !editMode;
    const modal = document.getElementById('edit-modal');
    
    if (editMode) {
        modal.classList.add('active');
        populateEditForm();
    } else {
        modal.classList.remove('active');
    }
}

function closeEditModal() {
    editMode = false;
    document.getElementById('edit-modal').classList.remove('active');
}

function populateEditForm() {
    // 填充世界观基本信息
    if (novelData.worldview && novelData.worldview.content) {
        const worldviewData = JSON.parse(novelData.worldview.content);
        document.getElementById('world-name').value = worldviewData.worldName || '';
        document.getElementById('world-description').value = worldviewData.worldDescription || '';
    }
    
    // 填充其他系统设定
    updateSystemContent('power-system-text', novelData.growth || novelData.worldview);
    updateSystemContent('magic-system-text', novelData.growth || novelData.worldview);
    updateSystemContent('social-system-text', novelData.growth || novelData.worldview);
    updateSystemContent('world-rules-text', novelData.growth || novelData.worldview);
    
    // 填充势力编辑器
    populateFactionsEditor();
    
    // 填充地点编辑器
    populateLocationsEditor();
}

function updateSystemContent(elementId, dataSource) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (!dataSource || !dataSource.content) {
        element.value = '';
        return;
    }
    
    let content = dataSource.content;
    if (typeof content === 'string') {
        try {
            content = JSON.parse(content);
        } catch (e) {
            // 不是JSON，直接使用
        }
    }
    
    // 如果有description字段，使用它
    if (content.description) {
        element.value = content.description;
    } else if (typeof content === 'string') {
        element.value = content;
    } else {
        element.value = JSON.stringify(content, null, 2);
    }
}

function populateFactionsEditor() {
    const container = document.getElementById('factions-editor');
    container.innerHTML = '';
    
    let factions = [];
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            factions = worldviewData.factions || [];
        } catch (e) {
            console.log('解析势力数据失败:', e);
        }
    }
    
    factions.forEach((faction, index) => {
        const item = document.createElement('div');
        item.className = 'editor-item';
        item.innerHTML = `
            <div class="editor-item-content">
                <h4>${faction.icon} ${faction.name}</h4>
                <p>${faction.description}</p>
            </div>
            <div class="editor-item-actions">
                <button class="icon-btn" onclick="editFaction(${index})" data-tooltip="编辑">
                    ✏️
                </button>
                <button class="icon-btn delete" onclick="deleteFaction(${index})" data-tooltip="删除">
                    🗑️
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

function populateLocationsEditor() {
    const container = document.getElementById('locations-editor');
    container.innerHTML = '';
    
    let locations = [];
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            locations = worldviewData.locations || [];
        } catch (e) {
            console.log('解析地点数据失败:', e);
        }
    }
    
    locations.forEach((location, index) => {
        const item = document.createElement('div');
        item.className = 'editor-item';
        item.innerHTML = `
            <div class="editor-item-content">
                <h4>${location.name}</h4>
                <p>${location.description}</p>
            </div>
            <div class="editor-item-actions">
                <button class="icon-btn" onclick="editLocation(${index})" data-tooltip="编辑">
                    ✏️
                </button>
                <button class="icon-btn delete" onclick="deleteLocation(${index})" data-tooltip="删除">
                    🗑️
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

function editFaction(index) {
    const faction = novelData.worldview ? 
        JSON.parse(novelData.worldview.content).factions[index] : null;
    console.log('编辑势力:', faction);
}

function deleteFaction(index) {
    if (confirm('确定要删除这个势力吗？')) {
        const worldviewData = JSON.parse(novelData.worldview.content);
        worldviewData.factions.splice(index, 1);
        novelData.worldview.content = JSON.stringify(worldviewData);
        
        populateFactionsEditor();
        updateFactionList();
        redrawMapView();
        redrawFactionGraph();
    }
}

function editLocation(index) {
    const location = novelData.worldview ? 
        JSON.parse(novelData.worldview.content).locations[index] : null;
    console.log('编辑地点:', location);
}

function deleteLocation(index) {
    if (confirm('确定要删除这个地点吗？')) {
        const worldviewData = JSON.parse(novelData.worldview.content);
        worldviewData.locations.splice(index, 1);
        novelData.worldview.content = JSON.stringify(worldviewData);
        
        populateLocationsEditor();
        updateLocationList();
        redrawMapView();
    }
}

function addFaction() {
    if (!novelData.worldview || !novelData.worldview.content) {
        novelData.worldview = { content: '{}' };
    }
    
    const worldviewData = JSON.parse(novelData.worldview.content);
    if (!worldviewData.factions) {
        worldviewData.factions = [];
    }
    
    const newFaction = {
        id: Date.now(),
        name: '新势力',
        description: '势力描述',
        color: '#667eea',
        icon: '🏰',
        power: 50,
        territories: [],
        relations: {}
    };
    
    worldviewData.factions.push(newFaction);
    novelData.worldview.content = JSON.stringify(worldviewData);
    
    populateFactionsEditor();
    updateFactionList();
    redrawMapView();
    redrawFactionGraph();
}

function addLocation() {
    if (!novelData.worldview || !novelData.worldview.content) {
        novelData.worldview = { content: '{}' };
    }
    
    const worldviewData = JSON.parse(novelData.worldview.content);
    if (!worldviewData.locations) {
        worldviewData.locations = [];
    }
    
    const newLocation = {
        id: Date.now(),
        name: '新地点',
        description: '地点描述',
        faction: '中立',
        x: 50,
        y: 50,
        importance: 3
    };
    
    worldviewData.locations.push(newLocation);
    novelData.worldview.content = JSON.stringify(worldviewData);
    
    populateLocationsEditor();
    updateLocationList();
    redrawMapView();
}

// ==================== 保存功能 ====================
async function saveWorldview() {
    showStatusMessage('🔄 正在保存...', 'info');
    
    try {
        // 收集表单数据
        novelData.worldName = document.getElementById('world-name').value;
        novelData.worldDescription = document.getElementById('world-description').value;
        novelData.powerSystem = document.getElementById('power-system-text').value;
        novelData.magicSystem = document.getElementById('magic-system-text').value;
        novelData.socialSystem = document.getElementById('social-system-text').value;
        novelData.worldRules = document.getElementById('world-rules-text').value;
        
        // 保存到服务器
        const response = await fetch('/api/worldview', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(novelData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            showStatusMessage('✅ 保存成功', 'success');
            closeEditModal();
            
            // 刷新数据
            await loadNovelData();
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        console.error('保存失败:', error);
        showStatusMessage('❌ 保存失败: ' + error.message, 'error');
    }
}

// ==================== 导航功能 ====================
function goBack() {
    window.history.back();
}

// ==================== 工具函数 ====================
function stripHtml(html) {
    const tmp = document.createElement('div');
    tmp.innerHTML = html;
    return tmp.textContent || tmp.innerText || '';
}

function showStatusMessage(message, type) {
    const msgElement = document.getElementById('status-message');
    if (!msgElement) return;
    
    msgElement.className = `status-message ${type}`;
    msgElement.textContent = message;
    msgElement.style.display = 'block';
    
    if (type === 'success') {
        setTimeout(() => {
            msgElement.style.display = 'none';
        }, 5000);
    }
}

// ==================== 事件监听器 ====================
function initializeEventListeners() {
    // 窗口大小改变时重绘
    window.addEventListener('resize', () => {
        if (currentView === 'characters') {
            redrawCharacterGraph();
        } else if (currentView === 'factions') {
            redrawFactionGraph();
        } else if (currentView === 'map') {
            redrawMapView();
        }
    });
    
    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && editMode) {
            closeEditModal();
        }
    });
}