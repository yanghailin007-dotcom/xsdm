// ==================== 简化版世界观查看器 ====================

let worldviewData = null;

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadWorldviewData();
});

async function loadWorldviewData() {
    try {
        // 从URL获取项目标题
        const urlParams = new URLSearchParams(window.location.search);
        const projectTitle = urlParams.get('title');
        
        if (!projectTitle) {
            showError('未找到项目参数');
            return;
        }
        
        // 加载世界观数据
        const response = await fetch(`/api/worldview/${encodeURIComponent(projectTitle)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.worldview) {
            worldviewData = result.worldview;
            displayWorldview();
        } else {
            showError('加载世界观数据失败');
        }
        
    } catch (error) {
        console.error('加载世界观数据失败:', error);
        showError('加载失败: ' + error.message);
    }
}

function displayWorldview() {
    if (!worldviewData) return;
    
    // 显示世界标题和描述
    document.getElementById('world-title').textContent = worldviewData.worldName || '未命名世界';
    document.getElementById('world-description').textContent = worldviewData.worldDescription || '暂无描述';
    
    // 显示势力信息
    displayFactions();
    
    // 显示地点信息
    displayLocations();
    
    // 显示修炼体系
    displayPowerSystem();
    
    // 显示法术系统
    displayMagicSystem();
    
    // 显示社会制度
    displaySocialSystem();
}

function displayFactions() {
    const container = document.getElementById('factions-container');
    
    if (!worldviewData.factions || worldviewData.factions.length === 0) {
        container.innerHTML = '<p style="color: #6b7280;">暂无势力数据</p>';
        return;
    }
    
    let html = '';
    worldviewData.factions.forEach(faction => {
        html += `
            <div class="faction-card">
                <h4>${faction.icon || '⚔️'} ${faction.name}</h4>
                <p style="margin: 8px 0; color: #4b5563;">${faction.description || '暂无描述'}</p>
                ${faction.power ? `<p style="margin: 4px 0; font-size: 14px;"><strong>力量值：</strong>${faction.power}/100</p>` : ''}
                ${faction.territories && faction.territories.length > 0 ? 
                  `<p style="margin: 4px 0; font-size: 14px;"><strong>领土：</strong>${faction.territories.join('、')}</p>` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function displayLocations() {
    const container = document.getElementById('locations-container');
    
    if (!worldviewData.locations || worldviewData.locations.length === 0) {
        container.innerHTML = '<li style="color: #6b7280;">暂无地点数据</li>';
        return;
    }
    
    let html = '';
    worldviewData.locations.forEach(location => {
        html += `
            <li>
                <div>
                    <strong>${location.name}</strong>
                    <p style="margin: 4px 0 0 0; font-size: 14px; color: #6b7280;">${location.description || '暂无描述'}</p>
                </div>
                <span style="background: #667eea; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                    ${location.faction || '中立'}
                </span>
            </li>
        `;
    });
    
    container.innerHTML = html;
}

function displayPowerSystem() {
    const container = document.getElementById('power-system-content');
    
    if (!worldviewData.powerSystem) {
        container.innerHTML = '<p style="color: #6b7280;">暂无修炼体系数据</p>';
        return;
    }
    
    // 如果是HTML格式，直接显示
    if (worldviewData.powerSystem.includes('<')) {
        container.innerHTML = worldviewData.powerSystem;
    } else {
        container.innerHTML = `<p>${worldviewData.powerSystem}</p>`;
    }
}

function displayMagicSystem() {
    const container = document.getElementById('magic-system-content');
    
    if (!worldviewData.magicSystem) {
        container.innerHTML = '<p style="color: #6b7280;">暂无法术系统数据</p>';
        return;
    }
    
    // 如果是HTML格式，直接显示
    if (worldviewData.magicSystem.includes('<')) {
        container.innerHTML = worldviewData.magicSystem;
    } else {
        container.innerHTML = `<p>${worldviewData.magicSystem}</p>`;
    }
}

function displaySocialSystem() {
    const container = document.getElementById('social-system-content');
    
    if (!worldviewData.socialSystem) {
        container.innerHTML = '<p style="color: #6b7280;">暂无社会制度数据</p>';
        return;
    }
    
    // 如果是HTML格式，直接显示
    if (worldviewData.socialSystem.includes('<')) {
        container.innerHTML = worldviewData.socialSystem;
    } else {
        container.innerHTML = `<p>${worldviewData.socialSystem}</p>`;
    }
}

function showError(message) {
    console.error(message);
    // 可以在页面上显示错误信息
    const containers = ['factions-container', 'locations-container', 'power-system-content', 'magic-system-content', 'social-system-content'];
    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = `<p style="color: #ef4444;">${message}</p>`;
        }
    });
}