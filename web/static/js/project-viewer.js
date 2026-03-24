/**
 * Project Viewer - 项目查看器
 * 处理项目概览、角色网络、势力关系、世界地图等视图
 */

// 项目数据
let projectData = null;
let currentView = 'overview';

// 角色网络图实例
let characterNetwork = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('📋 Project Viewer 初始化');
    initProjectViewer();
});

/**
 * 初始化项目查看器
 */
async function initProjectViewer() {
    // 从 URL 获取项目标题
    const pathParts = window.location.pathname.split('/');
    const projectTitle = decodeURIComponent(pathParts[pathParts.length - 1]);
    
    if (!projectTitle) {
        showError('未找到项目标题');
        return;
    }
    
    console.log('📖 加载项目:', projectTitle);
    
    // 加载项目数据
    await loadProjectData(projectTitle);
    
    // 初始化视图切换
    initViewTabs();
    
    // 初始化角色网络
    initCharacterNetwork();
}

/**
 * 加载项目数据
 */
async function loadProjectData(title) {
    try {
        showLoading(true);
        
        const response = await fetch(`/api/project/${encodeURIComponent(title)}`);
        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }
        
        projectData = await response.json();
        window.projectData = projectData; // 暴露给全局，供其他脚本使用
        console.log('✅ 项目数据加载成功:', projectData);
        
        // 更新页面标题
        document.title = `${projectData.title} - 项目查看器`;
        
        // 渲染项目概览
        renderOverview(projectData);
        
        // 如果有角色数据，渲染角色网络
        if (projectData.characters && projectData.characters.length > 0) {
            renderCharacterNetwork(projectData.characters);
        }
        
    } catch (error) {
        console.error('❌ 加载项目数据失败:', error);
        showError('加载项目数据失败: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * 初始化视图切换标签
 */
function initViewTabs() {
    const tabs = document.querySelectorAll('.view-tab');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const viewName = this.dataset.view;
            switchView(viewName);
        });
    });
}

/**
 * 切换视图
 */
function switchView(viewName) {
    console.log('🔄 切换视图:', viewName);
    
    // 更新标签状态
    document.querySelectorAll('.view-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.dataset.view === viewName) {
            tab.classList.add('active');
        }
    });
    
    // 隐藏所有视图
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    
    // 显示目标视图
    const targetView = document.getElementById(`${viewName}-view`);
    if (targetView) {
        targetView.classList.add('active');
        
        // 如果切换到角色视图，调整 canvas 尺寸并重新渲染
        if (viewName === 'characters') {
            setTimeout(() => {
                if (resizeCharacterCanvas() && projectData && projectData.characters) {
                    renderCharacterNetwork(projectData.characters);
                } else if (!projectData || !projectData.characters || projectData.characters.length === 0) {
                    // 没有角色数据时显示空状态
                    const canvas = document.getElementById('characters-graph');
                    if (canvas) {
                        resizeCharacterCanvas();
                        const ctx = canvas.getContext('2d');
                        const width = canvas.width / (window.devicePixelRatio || 1);
                        const height = canvas.height / (window.devicePixelRatio || 1);
                        ctx.clearRect(0, 0, width, height);
                        ctx.fillStyle = '#94a3b8';
                        ctx.font = '16px sans-serif';
                        ctx.textAlign = 'center';
                        ctx.fillText('暂无角色数据', width / 2, height / 2);
                    }
                }
            }, 150); // 增加延迟确保视图已渲染
        }
    }
    
    currentView = viewName;
}

/**
 * 初始化角色网络
 */
function initCharacterNetwork() {
    const canvas = document.getElementById('characters-graph');
    if (!canvas) {
        console.warn('❌ 找不到角色网络 canvas');
        return;
    }
    
    console.log('✅ 角色网络 canvas 已初始化');
    
    // 监听窗口调整
    window.addEventListener('resize', () => {
        if (currentView === 'characters' && projectData && projectData.characters) {
            resizeCharacterCanvas();
            renderCharacterNetwork(projectData.characters);
        }
    });
}

/**
 * 调整角色网络 canvas 尺寸
 */
function resizeCharacterCanvas() {
    const canvas = document.getElementById('characters-graph');
    if (!canvas) return false;
    
    const container = canvas.parentElement;
    if (!container) return false;
    
    // 获取容器实际尺寸
    const rect = container.getBoundingClientRect();
    const width = Math.floor(rect.width);
    const height = Math.floor(rect.height);
    
    // 只有当尺寸有效时才设置
    if (width > 0 && height > 0) {
        // 处理高清屏
        const dpr = window.devicePixelRatio || 1;
        canvas.width = width * dpr;
        canvas.height = height * dpr;
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        
        // 缩放上下文以匹配 DPR
        const ctx = canvas.getContext('2d');
        ctx.scale(dpr, dpr);
        
        console.log(`📐 Canvas 尺寸调整: ${width}x${height} (DPR: ${dpr})`);
        return true;
    }
    
    console.warn('⚠️ Canvas 容器尺寸无效:', width, height);
    return false;
}

/**
 * 渲染角色网络图
 */
function renderCharacterNetwork(characters) {
    const canvas = document.getElementById('characters-graph');
    if (!canvas) {
        console.warn('❌ 找不到角色网络 canvas');
        return;
    }
    
    // 确保 canvas 尺寸正确
    if (!resizeCharacterCanvas()) {
        console.warn('⚠️ Canvas 尺寸调整失败，尝试强制调整');
        const container = canvas.parentElement;
        if (container) {
            canvas.width = container.clientWidth || 800;
            canvas.height = container.clientHeight || 500;
            canvas.style.width = (container.clientWidth || 800) + 'px';
            canvas.style.height = (container.clientHeight || 500) + 'px';
        }
    }
    
    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    // 使用 CSS 像素尺寸进行计算
    const width = canvas.width / dpr;
    const height = canvas.height / dpr;
    
    // 清空画布
    ctx.clearRect(0, 0, width, height);
    
    if (!characters || characters.length === 0) {
        // 显示无数据提示
        ctx.fillStyle = '#94a3b8';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('暂无角色数据', width / 2, height / 2);
        return;
    }
    
    console.log('🎨 渲染角色网络:', characters.length, '个角色');
    
    // 计算角色位置（简单的圆形布局）
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.35;
    
    const characterPositions = {};
    
    // 主角放在中心
    let mainCharacter = characters.find(c => c.is_main) || characters[0];
    characterPositions[mainCharacter.name] = { x: centerX, y: centerY, character: mainCharacter };
    
    // 其他角色围绕中心分布
    const otherCharacters = characters.filter(c => c.name !== mainCharacter.name);
    otherCharacters.forEach((char, index) => {
        const angle = (2 * Math.PI * index) / otherCharacters.length - Math.PI / 2;
        characterPositions[char.name] = {
            x: centerX + radius * Math.cos(angle),
            y: centerY + radius * Math.sin(angle),
            character: char
        };
    });
    
    // 绘制连线（关系）
    ctx.strokeStyle = 'rgba(99, 102, 241, 0.3)';
    ctx.lineWidth = 2;
    
    characters.forEach(char => {
        const pos1 = characterPositions[char.name];
        if (!pos1) return;
        
        // 与其他角色连线
        characters.forEach(otherChar => {
            if (char.name === otherChar.name) return;
            
            const pos2 = characterPositions[otherChar.name];
            if (!pos2) return;
            
            // 检查是否有直接关系
            const hasRelation = char.relationships && char.relationships.some(
                r => r.target === otherChar.name
            );
            
            if (hasRelation) {
                ctx.beginPath();
                ctx.moveTo(pos1.x, pos1.y);
                ctx.lineTo(pos2.x, pos2.y);
                ctx.stroke();
            }
        });
    });
    
    // 绘制角色节点
    Object.values(characterPositions).forEach(({ x, y, character }) => {
        const isMain = character.is_main;
        const nodeRadius = isMain ? 30 : 20;
        
        // 节点背景
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, nodeRadius);
        if (isMain) {
            gradient.addColorStop(0, '#6366f1');
            gradient.addColorStop(1, '#4f46e5');
        } else {
            gradient.addColorStop(0, '#334155');
            gradient.addColorStop(1, '#1e293b');
        }
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, nodeRadius, 0, 2 * Math.PI);
        ctx.fill();
        
        // 节点边框
        ctx.strokeStyle = isMain ? '#818cf8' : '#475569';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // 角色名称
        ctx.fillStyle = '#ffffff';
        ctx.font = `${isMain ? 'bold 14px' : '12px'} sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // 截断名称
        let displayName = character.name;
        if (displayName.length > 4) {
            displayName = displayName.substring(0, 4) + '...';
        }
        ctx.fillText(displayName, x, y);
    });
    
    // 添加点击事件
    canvas.onclick = function(e) {
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        // 检查点击了哪个角色
        Object.values(characterPositions).forEach(({ x: cx, y: cy, character }) => {
            const dist = Math.sqrt((x - cx) ** 2 + (y - cy) ** 2);
            if (dist < 30) {
                showCharacterDetails(character);
            }
        });
    };
}

/**
 * 显示角色详情
 */
function showCharacterDetails(character) {
    const detailsContainer = document.getElementById('character-details');
    if (!detailsContainer) return;
    
    const html = `
        <div class="character-detail-card">
            <h4>${character.name} ${character.is_main ? '<span class="main-badge">主角</span>' : ''}</h4>
            <p><strong>身份:</strong> ${character.identity || '未设定'}</p>
            <p><strong>性格:</strong> ${character.personality || '未设定'}</p>
            <p><strong>背景:</strong> ${character.background || '未设定'}</p>
            ${character.goals ? `<p><strong>目标:</strong> ${character.goals}</p>` : ''}
            ${character.relationships && character.relationships.length > 0 ? `
                <p><strong>关系:</strong></p>
                <ul>
                    ${character.relationships.map(r => `
                        <li>${r.target}: ${r.type} ${r.description ? `(${r.description})` : ''}</li>
                    `).join('')}
                </ul>
            ` : ''}
        </div>
    `;
    
    detailsContainer.innerHTML = html;
}

/**
 * 渲染项目概览
 */
function renderOverview(data) {
    // 更新基本信息
    const titleEl = document.getElementById('novel-title-display');
    if (titleEl) titleEl.textContent = data.title || '未命名项目';
    
    const descEl = document.getElementById('novel-synopsis-display');
    if (descEl) descEl.textContent = data.description || data.story_synopsis || '暂无描述';
    
    // 更新统计
    const charCountEl = document.getElementById('overview-characters');
    if (charCountEl) charCountEl.textContent = data.characters ? data.characters.length : 0;
    
    const chapterCountEl = document.getElementById('overview-chapters');
    if (chapterCountEl) chapterCountEl.textContent = data.chapters ? data.chapters.length : 0;
    
    // 更新其他统计
    const factionsEl = document.getElementById('overview-factions');
    if (factionsEl) factionsEl.textContent = data.factions ? data.factions.length : 0;
    
    const eventsEl = document.getElementById('overview-events');
    if (eventsEl) eventsEl.textContent = data.events ? data.events.length : 0;
}

/**
 * 显示/隐藏加载状态
 */
function showLoading(show) {
    console.log(show ? '⏳ 加载中...' : '✅ 加载完成');
}

/**
 * 显示错误信息
 */
function showError(message) {
    console.error('❌ 错误:', message);
    alert(message);
}

console.log('✅ project-viewer.js 加载完成');
