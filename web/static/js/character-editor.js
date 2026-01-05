// ==================== 角色编辑器 ====================

let currentEditingCharacter = null;
let characterData = [];
let projectTitle = '';

// ==================== 初始化和加载 ====================

async function openCharacterEditor() {
    console.log('🎯 开始打开角色编辑器');
    
    // 获取项目标题 - 支持多种来源
    if (window.currentProjectTitle) {
        projectTitle = window.currentProjectTitle;
        console.log('✅ 使用全局项目标题:', projectTitle);
    } else {
        // 尝试从URL参数获取
        const urlParams = new URLSearchParams(window.location.search);
        const titleFromUrl = urlParams.get('title');
        if (titleFromUrl) {
            projectTitle = decodeURIComponent(titleFromUrl);
            console.log('✅ 从URL参数获取项目标题:', projectTitle);
        } else {
            // 尝试从路径获取
            const pathParts = window.location.pathname.split('/');
            projectTitle = decodeURIComponent(pathParts[pathParts.length - 1]);
            console.log('✅ 从路径获取项目标题:', projectTitle);
        }
    }
    
    const modal = document.getElementById('character-editor-modal');
    if (!modal) {
        console.error('❌ 角色编辑器模态框未找到');
        return;
    }
    
    console.log('✅ 找到模态框元素，当前innerHTML长度:', modal.innerHTML.length);
    
    // 如果模态框为空，加载模态框内容
    if (modal.innerHTML.trim() === '' || modal.innerHTML.length < 100) {
        console.log('🔄 模态框为空或内容过少，正在加载内容...');
        try {
            const response = await fetch('/templates/components/character-editor-modal.html');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const html = await response.text();
            modal.innerHTML = html;
            console.log('✅ 模态框内容加载成功，HTML长度:', html.length);
        } catch (error) {
            console.error('❌ 加载角色编辑器模态框失败:', error);
            showStatusMessage(`❌ 加载模态框失败: ${error.message}`, 'error');
            return;
        }
    } else {
        console.log('✅ 模态框已有内容，长度:', modal.innerHTML.length);
    }
    
    // 显示wrapper和模态框
    console.log('👀 显示模态框');
    
    // 确保wrapper容器也显示
    const wrapper = document.getElementById('character-editor-modal-wrapper');
    if (wrapper) {
        wrapper.style.display = 'block';
        wrapper.style.pointerEvents = 'auto';
    }
    
    modal.classList.add('active');
    modal.style.display = 'flex';
    
    // 等待DOM更新
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // 加载角色数据
    console.log('🔄 开始加载角色数据...');
    await loadCharacterData();
    console.log('📊 角色数据加载完成，角色数量:', characterData.length);
    
    // 渲染角色列表
    console.log('🎨 开始渲染角色列表...');
    renderCharacterList();
    console.log('✅ 角色列表渲染完成');
    
    // 如果没有角色数据，显示空状态提示
    if (characterData.length === 0) {
        console.log('⚠️ 没有角色数据，显示空状态');
    }
    
    console.log('✅ 角色编辑器打开完成');
    
    // 检查关键元素是否存在
    const characterList = document.getElementById('character-list');
    const formContainer = document.getElementById('character-form-container');
    console.log('🔍 character-list元素存在:', !!characterList);
    console.log('🔍 character-form-container元素存在:', !!formContainer);
}

function closeCharacterEditor(event) {
    // 如果有事件对象，且点击的不是背景遮罩，则不关闭
    if (event && event.target !== event.currentTarget) {
        return;
    }
    
    const modal = document.getElementById('character-editor-modal');
    if (modal) {
        modal.classList.remove('active');
        modal.style.display = 'none';
    }
    
    // 同时隐藏wrapper容器
    const wrapper = document.getElementById('character-editor-modal-wrapper');
    if (wrapper) {
        wrapper.style.display = 'none';
    }
    
    currentEditingCharacter = null;
    resetCharacterForm();
    console.log('✅ 角色编辑器已关闭');
}

async function loadCharacterData() {
    try {
        // 首先从window.novelData中获取角色数据（优先使用已设置的数据）
        if (window.novelData && window.novelData.characters && window.novelData.characters.content) {
            try {
                const charData = JSON.parse(window.novelData.characters.content);
                if (Array.isArray(charData)) {
                    characterData = charData;
                    console.log('✅ 从window.novelData加载了角色数据:', characterData.length, '个角色');
                    return;
                }
            } catch (e) {
                console.log('⚠️ 解析window.novelData中的角色数据失败:', e);
            }
        }
        
        // 如果window.novelData中没有，从API加载
        console.log('🔄 从API加载角色数据，项目标题:', projectTitle);
        const response = await fetch(`/api/characters/${encodeURIComponent(projectTitle)}`);
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                characterData = result.characters || [];
                console.log('✅ 从API加载了角色数据:', characterData.length, '个角色');
                // 同步到window.novelData
                if (!window.novelData) {
                    window.novelData = {};
                }
                if (!window.novelData.characters) {
                    window.novelData.characters = {};
                }
                window.novelData.characters.content = JSON.stringify(characterData);
            }
        }
    } catch (error) {
        console.error('❌ 加载角色数据失败:', error);
        characterData = [];
    }
}

// ==================== 渲染函数 ====================

function renderCharacterList() {
    const container = document.getElementById('character-list');
    if (!container) {
        console.error('❌ 找不到character-list容器');
        return;
    }
    
    console.log('🎨 开始渲染角色列表，角色数量:', characterData.length);
    
    if (characterData.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 40px 20px;">
                <div class="empty-icon">📝</div>
                <h3>暂无角色</h3>
                <p>点击上方按钮创建第一个角色</p>
            </div>
        `;
        console.log('✅ 显示空状态');
        return;
    }
    
    let html = characterData.map((char, index) => {
        const icon = char.icon || '👤';
        const color = char.color || '#667eea';
        const name = char.name || char.characterName || '未命名';
        const type = char.role || char.character_type || '未知类型';
        const desc = char.description || char.personality || '暂无描述';
        
        return `
            <div class="character-card ${currentEditingCharacter === index ? 'active' : ''}" 
                 onclick="selectCharacter(${index})"
                 data-index="${index}">
                <div class="character-card-header">
                    <div class="character-icon" style="background: ${color};">
                        ${icon}
                    </div>
                    <div class="character-info">
                        <h4 class="character-name">${name}</h4>
                        <p class="character-type">${type}</p>
                    </div>
                    <button class="icon-btn" onclick="event.stopPropagation(); deleteCharacter(${index})" 
                            style="background: none; border: none; cursor: pointer; font-size: 18px; opacity: 0.5;">
                        🗑️
                    </button>
                </div>
                <div class="character-preview">${desc}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
    console.log('✅ 角色列表渲染完成，HTML长度:', html.length);
}

function selectCharacter(index) {
    console.log('🎯 选择角色，索引:', index);
    currentEditingCharacter = index;
    const character = characterData[index];
    
    // 更新UI状态
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('active');
    });
    document.querySelector(`.character-card[data-index="${index}"]`)?.classList.add('active');
    
    // 显示表单
    const formContainer = document.getElementById('character-form-container');
    const emptyState = document.getElementById('no-character-selected');
    
    if (formContainer) {
        formContainer.style.display = 'block';
    }
    if (emptyState) {
        emptyState.style.display = 'none';
    }
    
    // 填充表单数据
    populateCharacterForm(character);
    console.log('✅ 角色表单填充完成');
}

function populateCharacterForm(character) {
    document.getElementById('char-name').value = character.name || character.characterName || '';
    document.getElementById('char-type').value = character.role || character.character_type || '主角';
    document.getElementById('char-appearance').value = character.appearance || '';
    document.getElementById('char-personality').value = character.personality || character.description || '';
    document.getElementById('char-background').value = character.background || '';
    document.getElementById('char-abilities').value = character.abilities || '';
    document.getElementById('char-cultivation').value = character.cultivation_level || '';
    document.getElementById('char-skills').value = character.skills || '';
    
    // 设置图标
    const icon = character.icon || '👤';
    selectCharIcon(icon);
    
    // 设置颜色
    const color = character.color || '#667eea';
    selectCharColor(color);
    
    // 加载关系
    renderRelationships(character.relationships || []);
}

function resetCharacterForm() {
    const formContainer = document.getElementById('character-form-container');
    const emptyState = document.getElementById('no-character-selected');
    
    if (formContainer) {
        formContainer.style.display = 'none';
    }
    if (emptyState) {
        emptyState.style.display = 'flex';
    }
    
    if (document.getElementById('char-name')) {
        document.getElementById('char-name').value = '';
    }
    if (document.getElementById('char-type')) {
        document.getElementById('char-type').value = '主角';
    }
    if (document.getElementById('char-appearance')) {
        document.getElementById('char-appearance').value = '';
    }
    if (document.getElementById('char-personality')) {
        document.getElementById('char-personality').value = '';
    }
    if (document.getElementById('char-background')) {
        document.getElementById('char-background').value = '';
    }
    if (document.getElementById('char-abilities')) {
        document.getElementById('char-abilities').value = '';
    }
    if (document.getElementById('char-cultivation')) {
        document.getElementById('char-cultivation').value = '';
    }
    if (document.getElementById('char-skills')) {
        document.getElementById('char-skills').value = '';
    }
    
    // 重置图标和颜色
    selectCharIcon('👤');
    selectCharColor('#667eea');
    
    // 清空关系列表
    const relationshipsContainer = document.getElementById('character-relationships');
    if (relationshipsContainer) {
        relationshipsContainer.innerHTML = '';
    }
}

// ==================== 图标和颜色选择 ====================

function selectCharIcon(icon) {
    document.querySelectorAll('.icon-option').forEach(el => {
        el.classList.remove('selected');
        if (el.dataset.icon === icon) {
            el.classList.add('selected');
        }
    });
}

function selectCharColor(color) {
    document.querySelectorAll('.color-option').forEach(el => {
        el.classList.remove('selected');
        if (el.dataset.color === color) {
            el.classList.add('selected');
        }
    });
}

// ==================== 关系管理 ====================

function renderRelationships(relationships) {
    const container = document.getElementById('character-relationships');
    if (!container) {
        console.error('❌ 找不到character-relationships容器');
        return;
    }
    
    container.innerHTML = '';
    
    if (!relationships || relationships.length === 0) {
        container.innerHTML = '<p class="text-muted" style="font-size: 13px; color: #6b7280;">暂无关系数据</p>';
        return;
    }
    
    relationships.forEach((rel, index) => {
        const relItem = document.createElement('div');
        relItem.className = 'relationship-item';
        relItem.innerHTML = `
            <select>
                <option value="ally" ${rel.relation_type === 'ally' ? 'selected' : ''}>盟友</option>
                <option value="enemy" ${rel.relation_type === 'enemy' ? 'selected' : ''}>敌对</option>
                <option value="neutral" ${rel.relation_type === 'neutral' ? 'selected' : ''}>中立</option>
                <option value="family" ${rel.relation_type === 'family' ? 'selected' : ''}>家人</option>
                <option value="mentor" ${rel.relation_type === 'mentor' ? 'selected' : ''}>导师</option>
                <option value="friend" ${rel.relation_type === 'friend' ? 'selected' : ''}>朋友</option>
            </select>
            <input type="text" value="${rel.related_character || rel.relatedCharacterName || ''}" 
                   placeholder="角色名称">
            <button onclick="removeRelationship(${index})">删除</button>
        `;
        container.appendChild(relItem);
    });
}

function addRelationship() {
    const container = document.getElementById('character-relationships');
    if (!container) {
        console.error('❌ 找不到character-relationships容器');
        return;
    }
    
    // 移除空状态提示
    const emptyMsg = container.querySelector('.text-muted');
    if (emptyMsg) {
        emptyMsg.remove();
    }
    
    const relItem = document.createElement('div');
    relItem.className = 'relationship-item';
    relItem.innerHTML = `
        <select>
            <option value="ally">盟友</option>
            <option value="enemy">敌对</option>
            <option value="neutral">中立</option>
            <option value="family">家人</option>
            <option value="mentor">导师</option>
            <option value="friend">朋友</option>
        </select>
        <input type="text" placeholder="角色名称">
        <button onclick="removeRelationship(-1)">删除</button>
    `;
    container.appendChild(relItem);
}

function removeRelationship(index) {
    const container = document.getElementById('character-relationships');
    if (!container) {
        console.error('❌ 找不到character-relationships容器');
        return;
    }
    
    if (index === -1) {
        // 删除最后添加的关系
        const lastItem = container.lastElementChild;
        if (lastItem && lastItem.classList.contains('relationship-item')) {
            lastItem.remove();
        }
    } else {
        // 删除指定索引的关系
        const items = container.querySelectorAll('.relationship-item');
        if (items[index]) {
            items[index].remove();
        }
    }
    
    // 如果没有关系了，显示空状态
    if (container.children.length === 0) {
        container.innerHTML = '<p class="text-muted" style="font-size: 13px; color: #6b7280;">暂无关系数据</p>';
    }
}

function getRelationshipsFromForm() {
    const container = document.getElementById('character-relationships');
    if (!container) {
        console.error('❌ 找不到character-relationships容器');
        return [];
    }
    
    const items = container.querySelectorAll('.relationship-item');
    const relationships = [];
    
    items.forEach(item => {
        const select = item.querySelector('select');
        const input = item.querySelector('input');
        if (input && input.value.trim()) {
            relationships.push({
                relation_type: select.value,
                related_character: input.value.trim()
            });
        }
    });
    
    return relationships;
}

// ==================== 角色操作 ====================

function addNewCharacter() {
    const newCharacter = {
        name: '新角色',
        characterName: '新角色',
        role: '主角',
        character_type: '主角',
        icon: '👤',
        color: '#667eea',
        description: '',
        personality: '',
        appearance: '',
        background: '',
        abilities: '',
        cultivation_level: '',
        skills: '',
        relationships: []
    };
    
    characterData.push(newCharacter);
    renderCharacterList();
    selectCharacter(characterData.length - 1);
}

async function saveCharacter() {
    const name = document.getElementById('char-name').value.trim();
    if (!name) {
        alert('请输入角色名称');
        return;
    }
    
    // 获取选中的图标和颜色
    const selectedIcon = document.querySelector('.icon-option.selected');
    const selectedColor = document.querySelector('.color-option.selected');
    
    const charData = {
        name: name,
        characterName: name,
        role: document.getElementById('char-type').value,
        character_type: document.getElementById('char-type').value,
        icon: selectedIcon ? selectedIcon.dataset.icon : '👤',
        color: selectedColor ? selectedColor.dataset.color : '#667eea',
        description: document.getElementById('char-personality').value,
        personality: document.getElementById('char-personality').value,
        appearance: document.getElementById('char-appearance').value,
        background: document.getElementById('char-background').value,
        abilities: document.getElementById('char-abilities').value,
        cultivation_level: document.getElementById('char-cultivation').value,
        skills: document.getElementById('char-skills').value,
        relationships: getRelationshipsFromForm()
    };
    
    // 更新或添加角色
    if (currentEditingCharacter !== null) {
        characterData[currentEditingCharacter] = charData;
    } else {
        characterData.push(charData);
        currentEditingCharacter = characterData.length - 1;
    }
    
    // 更新window.novelData
    if (window.novelData && window.novelData.characters) {
        window.novelData.characters.content = JSON.stringify(characterData);
    }
    
    // 刷新列表
    renderCharacterList();
    
    // 显示成功提示
    showStatusMessage('✅ 角色保存成功', 'success');
}

function deleteCharacter(index) {
    if (!confirm('确定要删除这个角色吗？')) {
        return;
    }
    
    characterData.splice(index, 1);
    
    // 更新window.novelData
    if (window.novelData && window.novelData.characters) {
        window.novelData.characters.content = JSON.stringify(characterData);
    }
    
    // 如果删除的是当前编辑的角色，重置表单
    if (currentEditingCharacter === index) {
        currentEditingCharacter = null;
        resetCharacterForm();
    } else if (currentEditingCharacter > index) {
        currentEditingCharacter--;
    }
    
    renderCharacterList();
    showStatusMessage('✅ 角色已删除', 'success');
}

// ==================== 工具函数 ====================

function showStatusMessage(message, type) {
    // 创建提示元素
    const msgDiv = document.createElement('div');
    msgDiv.className = `status-message ${type}`;
    msgDiv.textContent = message;
    msgDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(msgDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        msgDiv.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => msgDiv.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ==================== 全局导出 ====================

// 确保函数在全局作用域可用
window.openCharacterEditor = openCharacterEditor;
window.closeCharacterEditor = closeCharacterEditor;
window.addNewCharacter = addNewCharacter;
window.saveCharacter = saveCharacter;
window.selectCharacter = selectCharacter;
window.deleteCharacter = deleteCharacter;
window.selectCharIcon = selectCharIcon;
window.selectCharColor = selectCharColor;
window.addRelationship = addRelationship;
window.removeRelationship = removeRelationship;