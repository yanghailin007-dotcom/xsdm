/**
 * Character Editor - 角色编辑器
 * 用于编辑角色信息和关系
 */

// 当前编辑的角色
let editingCharacter = null;
let allCharacters = [];

/**
 * 打开角色编辑器
 */
function openCharacterEditor(characterName = null) {
    console.log('📝 打开角色编辑器:', characterName);
    
    const modal = document.getElementById('character-editor-modal');
    if (!modal) {
        console.warn('❌ 找不到角色编辑器模态框');
        return;
    }
    
    // 获取项目数据中的角色
    if (window.projectData && window.projectData.characters) {
        allCharacters = window.projectData.characters;
    }
    
    // 如果指定了角色名称，加载该角色数据
    if (characterName) {
        editingCharacter = allCharacters.find(c => c.name === characterName) || null;
    } else {
        editingCharacter = null;
    }
    
    // 填充表单
    fillCharacterForm(editingCharacter);
    
    // 显示模态框
    modal.style.display = 'flex';
    
    // 添加淡入动画
    setTimeout(() => {
        modal.style.opacity = '1';
        modal.querySelector('.modal-content').style.transform = 'translateY(0)';
    }, 10);
}

/**
 * 关闭角色编辑器
 */
function closeCharacterEditor() {
    const modal = document.getElementById('character-editor-modal');
    if (!modal) return;
    
    // 淡出动画
    modal.style.opacity = '0';
    modal.querySelector('.modal-content').style.transform = 'translateY(-20px)';
    
    setTimeout(() => {
        modal.style.display = 'none';
        editingCharacter = null;
    }, 300);
}

/**
 * 填充角色表单
 */
function fillCharacterForm(character) {
    const form = document.getElementById('character-form');
    if (!form) return;
    
    if (character) {
        // 编辑模式
        form.querySelector('[name="name"]').value = character.name || '';
        form.querySelector('[name="identity"]').value = character.identity || '';
        form.querySelector('[name="personality"]').value = character.personality || '';
        form.querySelector('[name="background"]').value = character.background || '';
        form.querySelector('[name="goals"]').value = character.goals || '';
        form.querySelector('[name="is_main"]').checked = character.is_main || false;
    } else {
        // 新建模式
        form.reset();
        form.querySelector('[name="is_main"]').checked = false;
    }
    
    // 渲染关系列表
    renderRelationshipList(character ? character.relationships : []);
}

/**
 * 渲染关系列表
 */
function renderRelationshipList(relationships = []) {
    const container = document.getElementById('relationship-list');
    if (!container) return;
    
    if (!relationships || relationships.length === 0) {
        container.innerHTML = '<p class="empty-text">暂无关系</p>';
        return;
    }
    
    container.innerHTML = relationships.map((rel, index) => `
        <div class="relationship-item" data-index="${index}">
            <span class="rel-target">${rel.target}</span>
            <span class="rel-type">${rel.type}</span>
            <span class="rel-desc">${rel.description || ''}</span>
            <button type="button" class="btn-icon" onclick="removeRelationship(${index})">✕</button>
        </div>
    `).join('');
}

/**
 * 添加关系
 */
function addRelationship() {
    const targetSelect = document.getElementById('rel-target');
    const typeInput = document.getElementById('rel-type');
    const descInput = document.getElementById('rel-description');
    
    const target = targetSelect ? targetSelect.value : '';
    const type = typeInput ? typeInput.value : '';
    const description = descInput ? descInput.value : '';
    
    if (!target || !type) {
        alert('请选择关系对象和关系类型');
        return;
    }
    
    // 添加到当前角色的关系列表
    if (!editingCharacter) {
        editingCharacter = { relationships: [] };
    }
    if (!editingCharacter.relationships) {
        editingCharacter.relationships = [];
    }
    
    editingCharacter.relationships.push({ target, type, description });
    
    // 重新渲染关系列表
    renderRelationshipList(editingCharacter.relationships);
    
    // 清空输入
    if (typeInput) typeInput.value = '';
    if (descInput) descInput.value = '';
}

/**
 * 移除关系
 */
function removeRelationship(index) {
    if (editingCharacter && editingCharacter.relationships) {
        editingCharacter.relationships.splice(index, 1);
        renderRelationshipList(editingCharacter.relationships);
    }
}

/**
 * 保存角色
 */
async function saveCharacter() {
    const form = document.getElementById('character-form');
    if (!form) return;
    
    const formData = new FormData(form);
    const characterData = {
        name: formData.get('name'),
        identity: formData.get('identity'),
        personality: formData.get('personality'),
        background: formData.get('background'),
        goals: formData.get('goals'),
        is_main: formData.get('is_main') === 'on',
        relationships: editingCharacter ? editingCharacter.relationships || [] : []
    };
    
    if (!characterData.name) {
        alert('请输入角色名称');
        return;
    }
    
    try {
        // 获取项目标题
        const pathParts = window.location.pathname.split('/');
        const projectTitle = decodeURIComponent(pathParts[pathParts.length - 1]);
        
        const response = await fetch(`/api/project/${encodeURIComponent(projectTitle)}/characters`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(characterData)
        });
        
        if (!response.ok) {
            throw new Error('保存失败');
        }
        
        console.log('✅ 角色保存成功');
        
        // 关闭编辑器
        closeCharacterEditor();
        
        // 刷新角色网络
        if (window.projectData) {
            const charIndex = window.projectData.characters.findIndex(c => c.name === characterData.name);
            if (charIndex >= 0) {
                window.projectData.characters[charIndex] = characterData;
            } else {
                window.projectData.characters.push(characterData);
            }
            
            // 重新渲染
            if (typeof renderCharacterNetwork === 'function') {
                renderCharacterNetwork(window.projectData.characters);
            }
        }
        
        // 显示成功提示
        showToast('角色保存成功');
        
    } catch (error) {
        console.error('❌ 保存角色失败:', error);
        alert('保存失败: ' + error.message);
    }
}

/**
 * 删除角色
 */
async function deleteCharacter() {
    if (!editingCharacter || !editingCharacter.name) {
        alert('没有可删除的角色');
        return;
    }
    
    if (!confirm(`确定要删除角色 "${editingCharacter.name}" 吗？`)) {
        return;
    }
    
    try {
        const pathParts = window.location.pathname.split('/');
        const projectTitle = decodeURIComponent(pathParts[pathParts.length - 1]);
        
        const response = await fetch(
            `/api/project/${encodeURIComponent(projectTitle)}/characters/${encodeURIComponent(editingCharacter.name)}`,
            { method: 'DELETE' }
        );
        
        if (!response.ok) {
            throw new Error('删除失败');
        }
        
        console.log('✅ 角色删除成功');
        
        // 关闭编辑器
        closeCharacterEditor();
        
        // 刷新数据
        if (window.projectData) {
            window.projectData.characters = window.projectData.characters.filter(
                c => c.name !== editingCharacter.name
            );
            
            if (typeof renderCharacterNetwork === 'function') {
                renderCharacterNetwork(window.projectData.characters);
            }
        }
        
        showToast('角色已删除');
        
    } catch (error) {
        console.error('❌ 删除角色失败:', error);
        alert('删除失败: ' + error.message);
    }
}

/**
 * 显示提示消息
 */
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(34, 197, 94, 0.9);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        z-index: 10000;
        animation: slideUp 0.3s ease;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 2000);
}

// 点击模态框外部关闭
document.addEventListener('click', function(e) {
    const modal = document.getElementById('character-editor-modal');
    if (modal && e.target === modal) {
        closeCharacterEditor();
    }
});

console.log('✅ character-editor.js 加载完成');
