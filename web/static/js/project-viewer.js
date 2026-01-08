// ==================== 小说可视化系统 ====================

console.log('🚀 project-viewer.js 开始加载');

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

console.log('✅ 全局状态已初始化');

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('📝 DOMContentLoaded 事件触发');
    initializeNovelViewer();
    loadNovelData();
    initializeEventListeners();
    loadCharacterEditorModal();
});

// 加载角色编辑器模态框
async function loadCharacterEditorModal() {
    try {
        const response = await fetch('/templates/components/character-editor-modal.html');
        const html = await response.text();
        const modalContainer = document.getElementById('character-editor-modal');
        if (modalContainer) {
            modalContainer.innerHTML = html;
        }
    } catch (error) {
        console.error('加载角色编辑器模态框失败:', error);
    }
}

async function initializeNovelViewer() {
    console.log('🎯 初始化小说可视化系统');
    console.log('当前URL:', window.location.href);
    console.log('URL路径:', window.location.pathname);
    
    // 从URL路径获取项目标题
    // URL格式: /project-viewer/项目标题
    const pathParts = window.location.pathname.split('/');
    console.log('URL路径分割:', pathParts);
    
    // 获取最后一部分作为项目标题
    const projectTitle = pathParts[pathParts.length - 1];
    console.log('提取的项目标题:', projectTitle);
    
    if (projectTitle && projectTitle !== 'project-viewer') {
        novelData.projectTitle = decodeURIComponent(projectTitle);
        console.log('解码后的项目标题:', novelData.projectTitle);
        await loadNovelData();
    } else {
        console.error('❌ 未找到项目参数');
        showStatusMessage('未找到项目参数', 'error');
    }
}

async function loadNovelData() {
    try {
        showStatusMessage('🔄 正在加载项目数据...', 'info');
        
        // 验证项目标题
        if (!novelData.projectTitle || novelData.projectTitle.trim() === '') {
            throw new Error('项目标题不能为空');
        }
        
        // 加载项目详情
        const projectResponse = await fetch(`/api/project/${encodeURIComponent(novelData.projectTitle)}/with-phase-info`);
        
        if (!projectResponse.ok) {
            throw new Error(`HTTP ${projectResponse.status}: ${projectResponse.statusText}`);
        }
        
        const projectDetail = await projectResponse.json();
        
        // 设置基本信息
        novelData.novelTitle = projectDetail.novel_title || projectDetail.title || novelData.projectTitle;
        novelData.synopsis = projectDetail.story_synopsis || projectDetail.description || '暂无简介';
        novelData.totalChapters = projectDetail.phase_info?.total_chapters || projectDetail.total_chapters || 200;
        novelData.completedChapters = Object.keys(projectDetail.generated_chapters || {}).length;
        
        // 如果没有获取到小说标题，使用项目标题
        if (!novelData.novelTitle) {
            novelData.novelTitle = novelData.projectTitle;
        }
        
        // 加载第一阶段产物
        const productsResponse = await fetch(`/api/phase-one/products/${encodeURIComponent(novelData.projectTitle)}`);
        
        if (!productsResponse.ok) {
            throw new Error(`HTTP ${productsResponse.status}: ${productsResponse.statusText}`);
        }
        
        const productsResult = await productsResponse.json();
        
        console.log('产物加载结果:', productsResult);
        
        if (productsResult.success && productsResult.products) {
            novelData.worldview = productsResult.products.worldview;
            novelData.characters = productsResult.products.characters;
            novelData.growth = productsResult.products.growth;
            novelData.storyline = productsResult.products.storyline;
            novelData.writing = productsResult.products.writing;
            novelData.market = productsResult.products.market;
            
            // 打印产物状态
            console.log('产物状态:', {
                worldview: novelData.worldview?.complete ? '已加载' : '未加载',
                characters: novelData.characters?.complete ? '已加载' : '未加载',
                growth: novelData.growth?.complete ? '已加载' : '未加载',
                storyline: novelData.storyline?.complete ? '已加载' : '未加载',
                writing: novelData.writing?.complete ? '已加载' : '未加载',
                market: novelData.market?.complete ? '已加载' : '未加载'
            });
            
            // 尝试解析worldview内容
            if (novelData.worldview && novelData.worldview.content) {
                try {
                    const worldviewData = JSON.parse(novelData.worldview.content);
                    console.log('世界观数据解析成功:', {
                        hasFactions: !!worldviewData.factions,
                        factionsCount: worldviewData.factions?.length || 0,
                        hasLocations: !!worldviewData.locations,
                        locationsCount: worldviewData.locations?.length || 0
                    });
                } catch (e) {
                    console.error('解析世界观数据失败:', e);
                }
            }
        }
        
        // 更新UI
        updateOverview();
        initializeViews();
        
        showStatusMessage('✅ 成功加载项目数据: ' + novelData.novelTitle, 'success');
        
        console.log('项目数据加载完成:', {
            title: novelData.novelTitle,
            projectTitle: novelData.projectTitle,
            hasWorldview: !!novelData.worldview,
            hasCharacters: !!novelData.characters,
            hasStoryline: !!novelData.storyline
        });
        
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
        const name = character.name || character.characterName || '未命名';
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
    const height = canvas.height = canvas.offsetHeight;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    // 绘制背景
    drawMapBackground(ctx, width, height);
    
    // 提取数据
    let locations = [];
    let factions = [];
    
    console.log('开始绘制地图，当前数据状态:', {
        hasWorldview: !!novelData.worldview,
        hasContent: !!novelData.worldview?.content,
        contentLength: novelData.worldview?.content?.length || 0
    });
    
    if (novelData.worldview && novelData.worldview.content) {
        try {
            const worldviewData = JSON.parse(novelData.worldview.content);
            locations = worldviewData.locations || [];
            factions = worldviewData.factions || [];
            console.log('成功解析世界观数据:', {
                locationsCount: locations.length,
                factionsCount: factions.length
            });
        } catch (e) {
            console.error('解析世界观数据失败:', e);
            console.log('原始内容:', novelData.worldview.content.substring(0, 200));
        }
    }
    
    // 如果没有地点数据，显示提示信息并返回
    if (locations.length === 0) {
        drawEmptyState(ctx, width, height, '暂无地点数据\n\n请在世界观设定中添加地点信息');
        console.log('没有地点数据，显示空状态');
        return;
    }
    
    console.log('开始绘制地图元素...');
    
    // 绘制势力控制区域
    drawFactionTerritories(ctx, width, height, factions, locations);
    
    // 绘制地点连接线（路线）
    drawLocationRoutes(ctx, width, height, locations);
    
    // 绘制地点标记
    drawLocationMarkers(ctx, width, height, locations, factions);
    
    // 绘制地图图例
    drawMapLegend(ctx, width, height, factions);
    
    // 更新侧边栏
    updateFactionList(factions);
    updateLocationList(locations);
    
    console.log('地图绘制完成');
}

function drawMapBackground(ctx, width, height) {
    // 创建更丰富的渐变背景
    const gradient = ctx.createRadialGradient(
        width / 2, height / 2, 0,
        width / 2, height / 2, Math.max(width, height) / 2
    );
    gradient.addColorStop(0, '#1e293b');
    gradient.addColorStop(0.5, '#1a1f35');
    gradient.addColorStop(1, '#0f172a');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);
    
    // 绘制更细致的网格
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.08)';
    ctx.lineWidth = 1;
    
    // 主网格
    const mainGridSize = 100;
    for (let x = 0; x < width; x += mainGridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    for (let y = 0; y < height; y += mainGridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
    
    // 细网格
    const subGridSize = 25;
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.04)';
    for (let x = 0; x < width; x += subGridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
    }
    for (let y = 0; y < height; y += subGridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }
    
    // 绘制一些装饰性的地形特征
    drawTerrainFeatures(ctx, width, height);
}

function drawTerrainFeatures(ctx, width, height) {
    // 绘制一些装饰性的等高线
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.15)';
    ctx.lineWidth = 2;
    
    // 绘制几个山脉区域的等高线
    const mountains = [
        {x: width * 0.2, y: height * 0.3, radius: 60},
        {x: width * 0.7, y: height * 0.25, radius: 50},
        {x: width * 0.5, y: height * 0.7, radius: 55}
    ];
    
    mountains.forEach(mtn => {
        for (let r = mtn.radius; r >= mtn.radius - 30; r -= 10) {
            ctx.beginPath();
            ctx.arc(mtn.x, mtn.y, r, 0, Math.PI * 2);
            ctx.stroke();
        }
    });
}

function drawFactionTerritories(ctx, width, height, factions, locations) {
    // 为每个势力绘制控制区域
    factions.forEach(faction => {
        const factionLocations = locations.filter(loc => loc.faction === faction.name);
        if (factionLocations.length === 0) return;
        
        // 计算势力控制区域的中心
        const centerX = factionLocations.reduce((sum, loc) => sum + (loc.x / 100) * width, 0) / factionLocations.length;
        const centerY = factionLocations.reduce((sum, loc) => sum + (loc.y / 100) * height, 0) / factionLocations.length;
        
        // 计算控制区域半径
        const maxDist = Math.max(...factionLocations.map(loc => {
            const locX = (loc.x / 100) * width;
            const locY = (loc.y / 100) * height;
            return Math.sqrt((locX - centerX) ** 2 + (locY - centerY) ** 2);
        }));
        
        // 绘制势力控制区域（半透明背景）
        ctx.beginPath();
        ctx.arc(centerX, centerY, maxDist + 30, 0, Math.PI * 2);
        const gradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, maxDist + 30);
        gradient.addColorStop(0, faction.color + '20');
        gradient.addColorStop(1, faction.color + '05');
        ctx.fillStyle = gradient;
        ctx.fill();
        
        // 绘制控制区域边界（虚线）
        ctx.beginPath();
        ctx.arc(centerX, centerY, maxDist + 30, 0, Math.PI * 2);
        ctx.strokeStyle = faction.color + '40';
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 5]);
        ctx.stroke();
        ctx.setLineDash([]);
    });
}

function drawLocationRoutes(ctx, width, height, locations) {
    // 绘制地点之间的连接线（路线）
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.3)';
    ctx.lineWidth = 2;
    
    // 简单的最近邻连接
    const connected = new Set();
    
    locations.forEach((loc1, i) => {
        const x1 = (loc1.x / 100) * width;
        const y1 = (loc1.y / 100) * height;
        
        // 找到最近的2-3个地点
        const distances = locations
            .map((loc2, j) => {
                if (i === j) return null;
                const x2 = (loc2.x / 100) * width;
                const y2 = (loc2.y / 100) * height;
                const dist = Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
                return {index: j, distance: dist, x2, y2};
            })
            .filter(d => d !== null)
            .sort((a, b) => a.distance - b.distance)
            .slice(0, 3);
        
        // 绘制路线
        distances.forEach(d => {
            const key = [Math.min(i, d.index), Math.max(i, d.index)].join('-');
            if (!connected.has(key)) {
                ctx.beginPath();
                ctx.moveTo(x1, y1);
                ctx.lineTo(d.x2, d.y2);
                ctx.stroke();
                connected.add(key);
            }
        });
    });
}

function drawLocationMarkers(ctx, width, height, locations, factions) {
    locations.forEach(location => {
        const x = (location.x / 100) * width;
        const y = (location.y / 100) * height;
        
        // 查找所属势力
        const faction = factions.find(f => f.name === location.faction);
        const color = faction ? faction.color : '#667eea';
        const icon = getFactionIcon(location.faction);
        
        // 绘制光晕效果
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, 25);
        gradient.addColorStop(0, color + '60');
        gradient.addColorStop(1, color + '00');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, 25, 0, Math.PI * 2);
        ctx.fill();
        
        // 绘制外圈
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
        
        // 绘制图标
        ctx.font = '14px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(icon, x, y);
        
        // 绘制地点名称标签
        const textWidth = ctx.measureText(location.name).width;
        ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
        ctx.fillRect(x - textWidth / 2 - 6, y + 18, textWidth + 12, 20);
        
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 12px Arial';
        ctx.fillText(location.name, x, y + 28);
        
        // 如果有重要性标记，绘制星标
        if (location.importance >= 4) {
            ctx.fillStyle = '#fbbf24';
            ctx.font = '10px Arial';
            ctx.fillText('★', x + 12, y - 12);
        }
    });
}

function drawMapLegend(ctx, width, height, factions) {
    // 绘制图例
    const legendX = 20;
    const legendY = height - 20 - factions.length * 25;
    
    // 背景
    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.fillRect(legendX - 10, legendY - 10, 150, factions.length * 25 + 20);
    
    // 标题
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('势力图例', legendX, legendY + 5);
    
    // 势力列表
    factions.forEach((faction, index) => {
        const y = legendY + 25 + index * 25;
        
        // 颜色块
        ctx.fillStyle = faction.color;
        ctx.fillRect(legendX, y - 8, 15, 15);
        
        // 势力名称
        ctx.fillStyle = '#ffffff';
        ctx.font = '11px Arial';
        ctx.fillText(faction.name, legendX + 20, y + 3);
    });
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
    
    let html = `
        <div style="min-width: 200px;">
            <h4 style="margin: 0 0 8px 0; color: #667eea;">${location.name}</h4>
            <p style="margin: 0 0 8px 0; font-size: 12px; color: #94a3b8;">${location.description || '暂无描述'}</p>
            <div style="padding-top: 8px; border-top: 1px solid rgba(255,255,255,0.1);">
    `;
    
    if (location.faction) {
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>所属势力：</strong><span style="color: #10b981;">${location.faction}</span></p>`;
    }
    
    if (location.importance) {
        const stars = '★'.repeat(location.importance) + '☆'.repeat(5 - location.importance);
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>重要程度：</strong><span style="color: #fbbf24;">${stars}</span></p>`;
    }
    
    if (location.type) {
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>地点类型：</strong>${location.type}</p>`;
    }
    
    if (location.population) {
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>人口规模：</strong>${location.population}</p>`;
    }
    
    if (location.resources && location.resources.length > 0) {
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>资源特产：</strong>${location.resources.join('、')}</p>`;
    }
    
    if (location.events && location.events.length > 0) {
        html += `<p style="margin: 4px 0; font-size: 11px;"><strong>重要事件：</strong>${location.events.slice(0, 2).join('、')}</p>`;
    }
    
    html += `
            </div>
        </div>
    `;
    
    tooltip.innerHTML = html;
    tooltip.style.left = `${e.clientX + 15}px`;
    tooltip.style.top = `${e.clientY + 15}px`;
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

function updateFactionList(factions) {
    const container = document.getElementById('faction-list');
    if (!container) return;
    container.innerHTML = '';
    
    if (!factions || factions.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无势力数据</p>';
        return;
    }
    
    factions.forEach(faction => {
        const item = document.createElement('div');
        item.className = 'list-item faction-item';
        item.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">${faction.icon || '🏰'}</span>
                <div style="flex: 1;">
                    <h4 style="margin: 0; font-size: 14px;">${faction.name}</h4>
                    <p style="margin: 4px 0 0 0; font-size: 11px; color: #94a3b8;">${faction.description || ''}</p>
                </div>
            </div>
            ${faction.power ? `<span style="background: ${faction.color}; padding: 2px 8px; border-radius: 10px; font-size: 11px; color: white;">战力 ${faction.power}</span>` : ''}
        `;
        container.appendChild(item);
    });
}

function updateLocationList(locations) {
    const container = document.getElementById('location-list');
    if (!container) return;
    container.innerHTML = '';
    
    if (!locations || locations.length === 0) {
        container.innerHTML = '<p class="text-muted">暂无地点数据</p>';
        return;
    }
    
    locations.forEach(location => {
        const item = document.createElement('div');
        item.className = 'list-item location-item';
        
        let detailInfo = '';
        if (location.importance) {
            const stars = '★'.repeat(location.importance);
            detailInfo += `<span style="color: #fbbf24; font-size: 12px;">${stars}</span>`;
        }
        if (location.type) {
            detailInfo += `<span style="background: rgba(102, 126, 234, 0.2); padding: 2px 6px; border-radius: 4px; font-size: 10px; margin-left: 8px;">${location.type}</span>`;
        }
        
        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div style="flex: 1;">
                    <h4 style="margin: 0; font-size: 13px;">${location.name}</h4>
                    <p style="margin: 4px 0 0 0; font-size: 11px; color: #94a3b8;">${location.description || '暂无描述'}</p>
                    ${detailInfo ? `<div style="margin-top: 6px;">${detailInfo}</div>` : ''}
                </div>
                ${location.faction ? `<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 2px 8px; border-radius: 10px; font-size: 10px;">${location.faction}</span>` : ''}
            </div>
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
// 标记是否已初始化事件监听器，避免重复绑定
let eventListenersInitialized = false;

function initializeEventListeners() {
    // 如果已经初始化过，直接返回，避免重复绑定
    if (eventListenersInitialized) {
        return;
    }
    
    // 窗口大小改变时重绘（添加防抖，避免频繁重绘）
    let resizeTimer;
    window.addEventListener('resize', () => {
        // 使用防抖，避免频繁触发
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => {
            if (currentView === 'characters') {
                redrawCharacterGraph();
            } else if (currentView === 'factions') {
                redrawFactionGraph();
            } else if (currentView === 'map') {
                redrawMapView();
            }
        }, 100); // 100ms 防抖延迟
    });
    
    // 键盘快捷键
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && editMode) {
            closeEditModal();
        }
    });
    
    // 标记已初始化
    eventListenersInitialized = true;
}