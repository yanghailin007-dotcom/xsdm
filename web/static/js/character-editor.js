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
        // 🔥 优先级1：检查是否有从第二阶段传递的原始数据
        if (window.rawPhaseOneCharacters && window.rawPhaseOneCharacters.rawData) {
            console.log('📦 使用从第二阶段传递的原始角色数据');
            try {
                const content = window.rawPhaseOneCharacters.rawData;
                console.log('📖 解析原始角色数据，数据类型:', typeof content);
                
                const charData = JSON.parse(content);
                
                // 处理复杂的角色数据结构
                if (charData && typeof charData === 'object') {
                    // 如果是 {main_character, important_characters} 结构
                    if (charData.main_character || charData.important_characters) {
                        characterData = [];
                        
                        // 添加主角
                        if (charData.main_character) {
                            const mainChar = charData.main_character;
                            characterData.push({
                                name: mainChar.name || '主角',
                                characterName: mainChar.name || '主角',
                                role: '主角',
                                character_type: '主角',
                                // 基本信息
                                core_personality: mainChar.core_personality || '',
                                dialogue_style_example: mainChar.dialogue_style_example || '',
                                character_tag_for_reader: mainChar.character_tag_for_reader || '',
                                // 生活特征
                                living_characteristics: mainChar.living_characteristics || {},
                                // 内心世界
                                inner_world_and_flaws: mainChar.inner_world_and_flaws || {},
                                // 背景成长
                                background: mainChar.background || '',
                                motivation: mainChar.motivation || {},
                                growth_arc: mainChar.growth_arc || '',
                                cool_point_upgrade_path: mainChar.cool_point_upgrade_path || '',
                                // 势力归属
                                faction_affiliation: mainChar.faction_affiliation || {},
                                // 势力关系网络
                                faction_relationships: mainChar.faction_relationships || {},
                                // 能力状态
                                cultivation_level: mainChar.character_states?.[0]?.cultivation_level || '',
                                abilities: mainChar.abilities || '',
                                skills: mainChar.skills || '',
                                // 初始状态
                                initial_state: mainChar.character_states?.[0] || {},
                                // 角色状态规划
                                character_states: mainChar.character_states || [],
                                // 叙事作用
                                narrative_purpose: mainChar.narrative_purpose || '',
                                reader_impression: mainChar.reader_impression || '',
                                // 兼容旧字段
                                description: mainChar.core_personality || '',
                                personality: mainChar.core_personality || '',
                                appearance: mainChar.living_characteristics?.physical_presence || '',
                                relationships: []
                            });
                        }
                        
                        // 添加重要角色
                        if (Array.isArray(charData.important_characters)) {
                            charData.important_characters.forEach((char, idx) => {
                                characterData.push({
                                    name: char.name || '未命名',
                                    characterName: char.name || '未命名',
                                    role: char.role || '配角',
                                    character_type: char.role || '配角',
                                    // 基本信息
                                    core_personality: char.soul_matrix?.[0]?.core_trait || '',
                                    dialogue_style_example: char.dialogue_style_example || '',
                                    // 生活特征
                                    living_characteristics: char.living_characteristics || {},
                                    // 背景成长
                                    background: char.background || '',
                                    motivation: char.motivation || {},
                                    // 势力归属
                                    faction_affiliation: char.faction_affiliation || {},
                                    // 势力关系网络
                                    faction_relationships: char.faction_relationships || {},
                                    // 能力状态
                                    cultivation_level: char.initial_state?.cultivation_level || '',
                                    // 初始状态
                                    initial_state: char.initial_state || {},
                                    // 叙事作用
                                    narrative_purpose: char.narrative_purpose || '',
                                    reader_impression: char.reader_impression || '',
                                    relationship_with_protagonist: char.relationship_with_protagonist || {},
                                    // 兼容旧字段
                                    description: char.initial_state?.description || char.soul_matrix?.[0]?.core_trait || '',
                                    personality: char.soul_matrix?.[0]?.core_trait || '',
                                    appearance: char.living_characteristics?.physical_presence || '',
                                    relationships: []
                                });
                            });
                        }
                        
                        console.log('✅ 从原始数据解析了角色数据:', characterData.length, '个角色');
                        return;
                    }
                    
                    // 如果是简单的数组结构
                    if (Array.isArray(charData)) {
                        characterData = charData;
                        console.log('✅ 从原始数据加载了角色数据:', characterData.length, '个角色');
                        return;
                    }
                }
            } catch (e) {
                console.log('⚠️ 解析原始角色数据失败:', e);
            }
        }
        
        // 🔥 优先级2：从window.novelData中获取角色数据（优先使用已设置的数据）
        if (window.novelData && window.novelData.characters && window.novelData.characters.content) {
            try {
                const content = window.novelData.characters.content;
                console.log('📖 从window.novelData解析角色数据，数据类型:', typeof content);
                
                const charData = JSON.parse(content);
                
                // 处理复杂的角色数据结构
                if (charData && typeof charData === 'object') {
                    // 如果是 {main_character, important_characters} 结构
                    if (charData.main_character || charData.important_characters) {
                        characterData = [];
                        
                        // 添加主角
                        if (charData.main_character) {
                            const mainChar = charData.main_character;
                            characterData.push({
                                name: mainChar.name || '主角',
                                characterName: mainChar.name || '主角',
                                role: '主角',
                                character_type: '主角',
                                // 基本信息
                                core_personality: mainChar.core_personality || '',
                                dialogue_style_example: mainChar.dialogue_style_example || '',
                                character_tag_for_reader: mainChar.character_tag_for_reader || '',
                                // 生活特征
                                living_characteristics: mainChar.living_characteristics || {},
                                // 内心世界
                                inner_world_and_flaws: mainChar.inner_world_and_flaws || {},
                                // 背景成长
                                background: mainChar.background || '',
                                motivation: mainChar.motivation || {},
                                growth_arc: mainChar.growth_arc || '',
                                cool_point_upgrade_path: mainChar.cool_point_upgrade_path || '',
                                // 势力归属
                                faction_affiliation: mainChar.faction_affiliation || {},
                                // 势力关系网络
                                faction_relationships: mainChar.faction_relationships || {},
                                // 能力状态
                                cultivation_level: mainChar.character_states?.[0]?.cultivation_level || '',
                                abilities: mainChar.abilities || '',
                                skills: mainChar.skills || '',
                                // 初始状态
                                initial_state: mainChar.character_states?.[0] || {},
                                // 角色状态规划
                                character_states: mainChar.character_states || [],
                                // 叙事作用
                                narrative_purpose: mainChar.narrative_purpose || '',
                                reader_impression: mainChar.reader_impression || '',
                                // 兼容旧字段
                                description: mainChar.core_personality || '',
                                personality: mainChar.core_personality || '',
                                appearance: mainChar.living_characteristics?.physical_presence || '',
                                relationships: []
                            });
                        }
                        
                        // 添加重要角色
                        if (Array.isArray(charData.important_characters)) {
                            charData.important_characters.forEach((char, idx) => {
                                characterData.push({
                                    name: char.name || '未命名',
                                    characterName: char.name || '未命名',
                                    role: char.role || '配角',
                                    character_type: char.role || '配角',
                                    // 基本信息
                                    core_personality: char.soul_matrix?.[0]?.core_trait || '',
                                    dialogue_style_example: char.dialogue_style_example || '',
                                    // 生活特征
                                    living_characteristics: char.living_characteristics || {},
                                    // 背景成长
                                    background: char.background || '',
                                    motivation: char.motivation || {},
                                    // 势力归属
                                    faction_affiliation: char.faction_affiliation || {},
                                    // 势力关系网络
                                    faction_relationships: char.faction_relationships || {},
                                    // 能力状态
                                    cultivation_level: char.initial_state?.cultivation_level || '',
                                    // 初始状态
                                    initial_state: char.initial_state || {},
                                    // 叙事作用
                                    narrative_purpose: char.narrative_purpose || '',
                                    reader_impression: char.reader_impression || '',
                                    relationship_with_protagonist: char.relationship_with_protagonist || {},
                                    // 兼容旧字段
                                    description: char.initial_state?.description || char.soul_matrix?.[0]?.core_trait || '',
                                    personality: char.soul_matrix?.[0]?.core_trait || '',
                                    appearance: char.living_characteristics?.physical_presence || '',
                                    relationships: []
                                });
                            });
                        }
                        
                        console.log('✅ 从复杂结构解析了角色数据:', characterData.length, '个角色');
                        return;
                    }
                    
                    // 如果是简单的数组结构
                    if (Array.isArray(charData)) {
                        characterData = charData;
                        console.log('✅ 从window.novelData加载了角色数据:', characterData.length, '个角色');
                        return;
                    }
                }
            } catch (e) {
                console.log('⚠️ 解析window.novelData中的角色数据失败:', e);
            }
        }
        
        // 🔥 优先级3：如果window.novelData中没有，从API加载
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
    
    // 🔥 防止重复渲染导致的闪烁
    if (container.dataset.rendering === 'true') {
        console.log('⚠️ 正在渲染中，跳过重复渲染');
        return;
    }
    container.dataset.rendering = 'true';
    
    if (characterData.length === 0) {
        container.innerHTML = `
            <div class="empty-state" style="padding: 40px 20px;">
                <div class="empty-icon">📝</div>
                <h3>暂无角色</h3>
                <p>点击上方按钮创建第一个角色</p>
            </div>
        `;
        console.log('✅ 显示空状态');
        container.dataset.rendering = 'false';
        return;
    }
    
    let html = characterData.map((char, index) => {
        const name = char.name || char.characterName || '未命名';
        const type = char.role || char.character_type || '未知类型';
        
        // 🔥 提取更多关键信息用于展示
        const corePersonality = char.core_personality || char.personality || '';
        const faction = char.faction_affiliation?.current_faction ||
                      char.initial_state?.faction ||
                      '无势力';
        const cultivationLevel = char.cultivation_level ||
                               char.initial_state?.cultivation_level ||
                               '未知';
        const position = char.faction_affiliation?.position || '';
        
        // 构建描述文本
        let descParts = [];
        if (corePersonality) {
            descParts.push(corePersonality);
        }
        if (faction !== '无势力') {
            descParts.push(`🏰 ${faction}`);
        }
        if (cultivationLevel !== '未知') {
            descParts.push(`⚡ ${cultivationLevel}`);
        }
        if (position) {
            descParts.push(`📌 ${position}`);
        }
        
        const desc = descParts.length > 0 ? descParts.join(' | ') : (char.description || '暂无描述');
        
        // 构建标签信息
        let tags = [];
        if (faction !== '无势力') {
            tags.push(`<span class="character-tag faction-tag">🏰 ${faction}</span>`);
        }
        if (cultivationLevel !== '未知') {
            tags.push(`<span class="character-tag level-tag">⚡ ${cultivationLevel}</span>`);
        }
        if (position) {
            tags.push(`<span class="character-tag position-tag">${position}</span>`);
        }
        
        const tagsHtml = tags.length > 0 ? `<div class="character-tags">${tags.join('')}</div>` : '';
        
        return `
            <div class="character-card ${currentEditingCharacter === index ? 'active' : ''}"
                 onclick="selectCharacter(${index})"
                 data-index="${index}">
                <div class="character-card-header">
                    <div class="character-info">
                        <h4 class="character-name">${name}</h4>
                        <p class="character-type">${type}</p>
                    </div>
                    <button class="icon-btn" onclick="event.stopPropagation(); deleteCharacter(${index})"
                            style="background: none; border: none; cursor: pointer; font-size: 18px; opacity: 0.5;">
                        🗑️
                    </button>
                </div>
                ${tagsHtml}
                <div class="character-preview">${desc}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = html;
    console.log('✅ 角色列表渲染完成，HTML长度:', html.length);
    
    // 🔥 渲染完成后重置标志
    setTimeout(() => {
        container.dataset.rendering = 'false';
    }, 100);
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
    // 使用新的数据收集函数（如果可用）
    if (typeof collectDataFromForm === 'function') {
        console.log('💾 使用JSON驱动数据收集器');
        const charData = collectDataFromForm();
        
        // 验证必填字段
        if (!charData.name || !charData.name.trim()) {
            alert('请输入角色名称');
            return;
        }
        
        // 确保基本字段存在
        if (!charData.description && charData.personality) {
            charData.description = charData.personality;
        }
        if (!charData.personality && charData.description) {
            charData.personality = charData.description;
        }
    
    // 确保基本字段存在
    if (!charData.description && charData.personality) {
        charData.description = charData.personality;
    }
    if (!charData.personality && charData.description) {
        charData.personality = charData.description;
    }
    
    } else {
        // 降级到旧的数据收集方式
        console.log('⚠️ 使用旧版数据收集方式');
        
        const nameInput = document.getElementById('char-name');
        if (!nameInput || !nameInput.value.trim()) {
            alert('请输入角色名称');
            return;
        }
        
        const name = nameInput.value.trim();
        
        // 获取选中的图标和颜色
        const selectedIcon = document.querySelector('.icon-option.selected');
        const selectedColor = document.querySelector('.color-option.selected');
        
        // 从动态表单收集所有数据
        const charData = {
            name: name,
            characterName: name,
            role: document.getElementById('char-role')?.value || '主角',
            character_type: document.getElementById('char-role')?.value || '主角',
            icon: selectedIcon ? selectedIcon.dataset.icon : '👤',
            color: selectedColor ? selectedColor.dataset.color : '#667eea',
        };
        
        // 收集所有动态生成的字段
        const allInputs = document.querySelectorAll('#dynamic-form-sections input, #dynamic-form-sections textarea');
        allInputs.forEach(input => {
            if (input.dataset.fieldId && input.id !== 'char-name' && input.id !== 'char-role') {
                const fieldId = input.dataset.fieldId;
                charData[fieldId] = input.value;
            }
        });
        
        // 确保基本字段存在
        if (!charData.description && charData.personality) {
            charData.description = charData.personality;
        }
        if (!charData.personality && charData.description) {
            charData.personality = charData.description;
        }
    }
    
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

// ==================== 动态表单生成 ====================

// 重新定义populateCharacterForm以支持动态表单
function populateCharacterForm(character) {
    const container = document.getElementById('dynamic-form-sections');
    if (!container) {
        console.error('❌ 找不到dynamic-form-sections容器');
        return;
    }
    
    // 清空容器
    container.innerHTML = '';
    
    // 使用新的JSON驱动表单生成器
    if (typeof generateFormFromJSON === 'function') {
        console.log('🎨 使用JSON驱动表单生成器');
        const form = generateFormFromJSON(character);
        container.appendChild(form);
        
        // 设置图标和颜色（兼容旧数据）
        if (character.icon) selectCharIcon(character.icon);
        if (character.color) selectCharColor(character.color);
        
        console.log('✅ 动态表单生成完成');
        return;
    }
    
    // 降级到旧的表单生成方式
    console.log('⚠️ 使用旧版表单生成方式');
    
    // 生成基本信息部分
    const basicSection = createFormSection('基本信息', [
        createFormField('角色名称', 'text', 'name', character.name || character.characterName || '', true),
        createFormField('角色类型', 'text', 'role', character.role || character.character_type || '', false)
    ], 'grid');
    container.appendChild(basicSection);
    
    // 添加图标和颜色选择器
    const iconSection = document.createElement('div');
    iconSection.className = 'form-section';
    iconSection.innerHTML = `
        <div class="form-group">
            <label>角色图标</label>
            <div class="icon-selector" id="char-icon-selector">
                <span class="icon-option selected" data-icon="👤" onclick="selectCharIcon('👤')">👤</span>
                <span class="icon-option" data-icon="🧑" onclick="selectCharIcon('🧑')">🧑</span>
                <span class="icon-option" data-icon="👨" onclick="selectCharIcon('👨')">👨</span>
                <span class="icon-option" data-icon="👩" onclick="selectCharIcon('👩')">👩</span>
                <span class="icon-option" data-icon="🧓" onclick="selectCharIcon('🧓')">🧓</span>
                <span class="icon-option" data-icon="👴" onclick="selectCharIcon('👴')">👴</span>
                <span class="icon-option" data-icon="👵" onclick="selectCharIcon('👵')">👵</span>
                <span class="icon-option" data-icon="🧙" onclick="selectCharIcon('🧙')">🧙</span>
                <span class="icon-option" data-icon="🧝" onclick="selectCharIcon('🧝')">🧝</span>
                <span class="icon-option" data-icon="🦸" onclick="selectCharIcon('🦸')">🦸</span>
                <span class="icon-option" data-icon="🦹" onclick="selectCharIcon('🦹')">🦹</span>
                <span class="icon-option" data-icon="👼" onclick="selectCharIcon('👼')">👼</span>
            </div>
        </div>
        <div class="form-group">
            <label>代表颜色</label>
            <div class="color-selector" id="char-color-selector">
                <span class="color-option selected" data-color="#667eea" style="background: #667eea;" onclick="selectCharColor('#667eea')"></span>
                <span class="color-option" data-color="#10b981" style="background: #10b981;" onclick="selectCharColor('#10b981')"></span>
                <span class="color-option" data-color="#f59e0b" style="background: #f59e0b;" onclick="selectCharColor('#f59e0b')"></span>
                <span class="color-option" data-color="#ef4444" style="background: #ef4444;" onclick="selectCharColor('#ef4444')"></span>
                <span class="color-option" data-color="#8b5cf6" style="background: #8b5cf6;" onclick="selectCharColor('#8b5cf6')"></span>
                <span class="color-option" data-color="#ec4899" style="background: #ec4899;" onclick="selectCharColor('#ec4899')"></span>
                <span class="color-option" data-color="#06b6d4" style="background: #06b6d4;" onclick="selectCharColor('#06b6d4')"></span>
                <span class="color-option" data-color="#84cc16" style="background: #84cc16;" onclick="selectCharColor('#84cc16')"></span>
            </div>
        </div>
    `;
    container.appendChild(iconSection);
    
    // 动态生成其他字段
    const otherFields = generateDynamicFields(character);
    if (otherFields.length > 0) {
        const otherSection = createFormSection('详细信息', otherFields);
        container.appendChild(otherSection);
    }
    
    // 设置图标和颜色
    selectCharIcon(character.icon || '👤');
    selectCharColor(character.color || '#667eea');
}

// 创建表单区块
function createFormSection(title, fields, layout = 'vertical') {
    const section = document.createElement('div');
    section.className = 'form-section';
    
    const titleElement = document.createElement('h4');
    titleElement.textContent = title;
    section.appendChild(titleElement);
    
    const grid = document.createElement('div');
    grid.className = layout === 'grid' ? 'form-grid' : 'form-vertical';
    
    fields.forEach(field => {
        grid.appendChild(field);
    });
    
    section.appendChild(grid);
    return section;
}

// 创建表单字段
function createFormField(label, type, id, value, required = false) {
    const group = document.createElement('div');
    group.className = 'form-group';
    
    const labelElement = document.createElement('label');
    labelElement.textContent = label + (required ? ' *' : '');
    group.appendChild(labelElement);
    
    let input;
    if (type === 'textarea') {
        input = document.createElement('textarea');
        input.rows = 3;
    } else {
        input = document.createElement('input');
        input.type = type;
    }
    
    input.id = `char-${id}`;
    input.value = value;
    input.dataset.fieldId = id;
    if (required) {
        input.required = true;
    }
    
    group.appendChild(input);
    return group;
}

// 根据角色数据动态生成字段
function generateDynamicFields(character) {
    const fields = [];
    
    // 定义字段映射和显示名称
    const fieldMappings = {
        'core_personality': '核心性格',
        'living_characteristics': '生活特征',
        'background': '背景故事',
        'motivation': '动机',
        'growth_arc': '成长弧线',
        'dialogue_style_example': '对话风格示例',
        'cultivation_level': '修炼等级',
        'abilities': '特殊能力',
        'skills': '主要技能',
        'physical_presence': '外貌特征',
        'speech_patterns': '言语模式',
        'inner_conflicts': '内心冲突',
        'description': '角色描述',
        'personality': '性格特点',
        'appearance': '外貌特征'
    };
    
    // 遍历角色数据，为每个字段创建表单元素
    for (const [key, value] of Object.entries(character)) {
        // 跳过已处理的字段
        if (['name', 'characterName', 'role', 'character_type', 'icon', 'color'].includes(key)) {
            continue;
        }
        
        // 跳过复杂对象和数组
        if (typeof value === 'object' && value !== null) {
            continue;
        }
        
        // 获取字段显示名称
        const displayName = fieldMappings[key] || key;
        
        // 根据值的长度决定使用input还是textarea
        const fieldType = String(value || '').length > 50 ? 'textarea' : 'text';
        const field = createFormField(displayName, fieldType, key, value || '');
        fields.push(field);
    }
    
    return fields;
}

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
window.createFormSection = createFormSection;
window.createFormField = createFormField;
window.generateDynamicFields = generateDynamicFields;