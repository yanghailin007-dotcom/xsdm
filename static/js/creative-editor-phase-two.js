// 第二阶段页面创意编辑器JavaScript

let loadedCreativeIdeasForPhaseTwo = [];
let selectedCreativeIdForPhaseTwo = null;
let currentEditingIdeaForPhaseTwo = null;
let originalIdeaDataForPhaseTwo = null;

// ==================== 创意编辑器功能 ====================

// 基于当前项目初始化编辑器
function initializeEditorWithCurrentProject() {
    if (!currentProject) return;
    
    const projectData = {
        novelTitle: currentProject.novel_title || currentProject.title,
        synopsis: currentProject.story_synopsis || currentProject.synopsis,
        coreSetting: currentProject.core_setting,
        totalChapters: currentProject.total_chapters || 200,
        coreSellingPoints: currentProject.core_selling_points || '',
        completeStoryline: currentProject.complete_storyline || {}
    };
    
    currentEditingIdeaForPhaseTwo = { id: 'current_project', title: projectData.novelTitle };
    originalIdeaDataForPhaseTwo = JSON.parse(JSON.stringify(projectData));
    
    populateCreativeEditorForPhaseTwo(projectData);
    showCreativeEditorModalForPhaseTwo();
}

// 显示创意编辑器模态框
function showCreativeEditorModalForPhaseTwo() {
    const modal = document.getElementById('creative-editor-modal-phase-two');
    // 🔥 修复闪烁：使用 visible 类而不是内联样式
    modal.classList.add('visible');
    
    document.body.style.overflow = 'hidden';
    
    // 初始化字符计数
    initCharCounterForPhaseTwo();
}

// 填充创意编辑器（两阶段页面专用）
function populateCreativeEditorForPhaseTwo(ideaData) {
    try {
        // 基本信息
        const title = ideaData.novelTitle || ideaData.title || ideaData.novel_title || '';
        const synopsis = ideaData.synopsis || ideaData.description || ideaData.novel_synopsis || '';
        const coreSetting = ideaData.coreSetting || ideaData.core_setting || ideaData.coreSetting || '';
        const totalChapters = ideaData.totalChapters || ideaData.total_chapters || 50;
        
        const titleElement = document.getElementById('edit-novel-title-phase-two');
        const synopsisElement = document.getElementById('edit-novel-synopsis-phase-two');
        const coreSettingElement = document.getElementById('edit-core-setting-phase-two');
        
        if (titleElement) titleElement.value = title;
        if (synopsisElement) synopsisElement.value = synopsis;
        if (coreSettingElement) coreSettingElement.value = coreSetting;
        
        // 核心卖点
        const sellingPoints = ideaData.coreSellingPoints || ideaData.core_selling_points || ideaData.sellingPoints || '';
        let pointsArray = [];
        if (typeof sellingPoints === 'string') {
            pointsArray = sellingPoints.split('+').map(p => p.trim()).filter(p => p);
        } else if (Array.isArray(sellingPoints)) {
            pointsArray = sellingPoints;
        }
        
        populateSellingPointsForPhaseTwo(pointsArray);
        
        // 故事线
        const storyline = ideaData.completeStoryline || ideaData.complete_storyline || ideaData.storyline || {};
        populateStorylineForPhaseTwo(storyline);
        
    } catch (error) {
        console.error('填充创意编辑器时出错:', error);
        showStatusMessage('❌ 填充数据时出错: ' + error.message, 'error');
    }
}

// 填充核心卖点（两阶段页面专用）
function populateSellingPointsForPhaseTwo(points) {
    const container = document.getElementById('selling-points-container-phase-two');
    container.innerHTML = '';
    
    points.forEach((point, index) => {
        addSellingPointElementForPhaseTwo(point, index);
    });
}

// 添加卖点元素（两阶段页面专用）
function addSellingPointElementForPhaseTwo(point, index) {
    const container = document.getElementById('selling-points-container-phase-two');
    const pointElement = document.createElement('div');
    pointElement.className = 'selling-point-item';
    pointElement.style.cssText = 'display: flex; gap: 8px; margin-bottom: 12px; align-items: center; padding: 8px; background: white; border-radius: 8px; border: 1px solid #e5e7eb;';
    pointElement.innerHTML = `
        <input type="text" value="${point}" placeholder="卖点描述"
               style="flex: 1; padding: 10px 14px; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 14px; background: white; color: #1f2937; transition: all 0.2s; box-sizing: border-box;"
               class="selling-point-input">
        <button type="button" onclick="removeSellingPointForPhaseTwo(this)"
                style="padding: 8px 12px; border: none; border-radius: 6px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);">
            🗑️ 删除
        </button>
    `;
    container.appendChild(pointElement);
}

// 添加新的卖点（两阶段页面专用）
function addSellingPointForPhaseTwo() {
    const input = document.getElementById('new-selling-point-phase-two');
    const point = input.value.trim();
    
    if (!point) {
        alert('请输入卖点描述');
        return;
    }
    
    addSellingPointElementForPhaseTwo(point);
    input.value = '';
}

// 删除卖点（两阶段页面专用）
function removeSellingPointForPhaseTwo(button) {
    button.parentElement.remove();
}

// 填充故事线（两阶段页面专用）
function populateStorylineForPhaseTwo(storyline) {
    const stages = [
        { key: 'opening', dataKey: 'opening' },
        { key: 'development', dataKey: 'development' },
        { key: 'climax', dataKey: 'conflict' },
        { key: 'ending', dataKey: 'ending' }
    ];
    
    stages.forEach(stage => {
        let stageData = storyline[stage.dataKey] || storyline[stage.key] || {};
        
        if (typeof stageData === 'string') {
            stageData = { stageName: stage.key, summary: stageData };
        }
        
        const stageEditor = document.querySelector(`#creative-editor-modal-phase-two div[data-stage="${stage.key}"]`);
        if (stageEditor) {
            const nameInput = stageEditor.querySelector(`input[data-stage="${stage.key}"]`);
            const descriptionInput = stageEditor.querySelector(`textarea[data-stage="${stage.key}"]`);
            
            if (nameInput) {
                const stageName = stageData.stageName || stageData.name || getDefaultStageNameForPhaseTwo(stage.key);
                nameInput.value = stageName;
            }
            if (descriptionInput) {
                const description = stageData.summary || stageData.description || stageData.content || '';
                descriptionInput.value = description;
            }
        }
    });
}

// 获取默认阶段名称（两阶段页面专用）
function getDefaultStageNameForPhaseTwo(stageKey) {
    const defaultNames = {
        'opening': '开篇',
        'development': '发展',
        'climax': '高潮',
        'ending': '结局'
    };
    return defaultNames[stageKey] || stageKey;
}

// 初始化字符计数（两阶段页面专用）
function initCharCounterForPhaseTwo() {
    const coreSettingTextarea = document.getElementById('edit-core-setting-phase-two');
    const charCountSpan = document.getElementById('char-count-phase-two');
    
    if (coreSettingTextarea && charCountSpan) {
        updateCharCountForPhaseTwo();
        
        coreSettingTextarea.addEventListener('input', updateCharCountForPhaseTwo);
        coreSettingTextarea.addEventListener('paste', function() {
            setTimeout(updateCharCountForPhaseTwo, 10);
        });
    }
}

// 更新字符计数（两阶段页面专用）
function updateCharCountForPhaseTwo() {
    const coreSettingTextarea = document.getElementById('edit-core-setting-phase-two');
    const charCountSpan = document.getElementById('char-count-phase-two');
    
    if (coreSettingTextarea && charCountSpan) {
        const charCount = coreSettingTextarea.value.length;
        charCountSpan.textContent = charCount + ' 字符';
        
        if (charCount < 100) {
            charCountSpan.style.color = '#ef4444';
        } else if (charCount < 300) {
            charCountSpan.style.color = '#f59e0b';
        } else {
            charCountSpan.style.color = '#10b981';
        }
    }
}

// 重置创意编辑器（两阶段页面专用）
function resetCreativeEditorForPhaseTwo() {
    if (!originalIdeaDataForPhaseTwo) {
        alert('没有原始数据可重置');
        return;
    }
    
    if (confirm('确定要重置所有修改吗？')) {
        populateCreativeEditorForPhaseTwo(originalIdeaDataForPhaseTwo);
    }
}

// 保存创意修改（两阶段页面专用）
async function saveCreativeChangesForPhaseTwo() {
    if (!currentEditingIdeaForPhaseTwo) {
        alert('没有正在编辑的创意');
        return;
    }
    
    try {
        const updatedData = collectCreativeEditorDataForPhaseTwo();
        
        if (!validateCreativeDataForPhaseTwo(updatedData)) {
            return;
        }
        
        // 如果是当前项目，直接应用修改
        if (currentEditingIdeaForPhaseTwo.id === 'current_project') {
            await applyCreativeDataToCurrentProject(updatedData);
            closeCreativeEditorForPhaseTwo();
            showStatusMessage('✅ 项目创意设定已更新', 'success');
            return;
        }
        
        // 否则保存到创意库
        const response = await fetch('/api/creative-ideas/' + currentEditingIdeaForPhaseTwo.id, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || '保存失败');
        }
        
        const result = await response.json();
        
        if (result.success) {
            alert('创意保存成功！');
            closeCreativeEditorForPhaseTwo();
            await loadCreativeIdeasForPhaseTwo();
        } else {
            throw new Error(result.error || '保存失败');
        }
        
    } catch (error) {
        console.error('保存创意失败:', error);
        alert('保存失败: ' + error.message);
    }
}

// 收集创意编辑器数据（两阶段页面专用）
function collectCreativeEditorDataForPhaseTwo() {
    const data = {
        novelTitle: document.getElementById('edit-novel-title-phase-two').value.trim(),
        synopsis: document.getElementById('edit-novel-synopsis-phase-two').value.trim(),
        coreSetting: document.getElementById('edit-core-setting-phase-two').value.trim(),
        coreSellingPoints: '',
        completeStoryline: {}
    };
    
    // 收集卖点
    const sellingPointInputs = document.querySelectorAll('#selling-points-container-phase-two .selling-point-input');
    const sellingPoints = Array.from(sellingPointInputs)
        .map(input => input.value.trim())
        .filter(point => point);
    data.coreSellingPoints = sellingPoints.join(' + ');
    
    // 收集故事线
    const stageMappings = [
        { htmlKey: 'opening', dataKey: 'opening' },
        { htmlKey: 'development', dataKey: 'development' },
        { htmlKey: 'climax', dataKey: 'conflict' },
        { htmlKey: 'ending', dataKey: 'ending' }
    ];
    
    stageMappings.forEach(mapping => {
        const stageEditor = document.querySelector(`#creative-editor-modal-phase-two div[data-stage="${mapping.htmlKey}"]`);
        if (stageEditor) {
            const nameInput = stageEditor.querySelector(`input[data-stage="${mapping.htmlKey}"]`);
            const descriptionInput = stageEditor.querySelector(`textarea[data-stage="${mapping.htmlKey}"]`);
            
            data.completeStoryline[mapping.dataKey] = {
                stageName: nameInput ? nameInput.value.trim() : '',
                summary: descriptionInput ? descriptionInput.value.trim() : ''
            };
        }
    });
    
    return data;
}

// 验证创意数据（两阶段页面专用）
function validateCreativeDataForPhaseTwo(data) {
    if (!data.coreSetting) {
        alert('请填写核心设定');
        return false;
    }
    
    if (!data.novelTitle) {
        alert('请填写小说标题');
        return false;
    }
    
    return true;
}

// 应用创意数据到当前项目
async function applyCreativeDataToCurrentProject(updatedData) {
    if (!currentProject) return;
    
    try {
        const response = await fetch(`/api/project/${encodeURIComponent(currentProject.novel_title)}/update-creative`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updatedData)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        if (result.success) {
            // 更新当前项目数据
            currentProject = { ...currentProject, ...updatedData };
            showStatusMessage('✅ 创意设定已应用到项目', 'success');
        } else {
            throw new Error(result.error || '应用失败');
        }
    } catch (error) {
        console.error('应用创意数据失败:', error);
        showStatusMessage(`❌ 应用失败: ${error.message}`, 'error');
    }
}

// 关闭创意编辑器（两阶段页面专用）
function closeCreativeEditorForPhaseTwo() {
    const modal = document.getElementById('creative-editor-modal-phase-two');
    if (modal) {
        // 🔥 修复闪烁：移除 visible 类而不是设置 display
        modal.classList.remove('visible');
    }
    document.body.style.overflow = '';
    
    currentEditingIdeaForPhaseTwo = null;
    originalIdeaDataForPhaseTwo = null;
}

// 创建新创意
function createNewCreativeIdeaForPhaseTwo() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    // 基于当前项目数据创建新创意
    const projectData = {
        novelTitle: currentProject.novel_title || currentProject.title,
        synopsis: currentProject.story_synopsis || currentProject.synopsis,
        coreSetting: currentProject.core_setting,
        totalChapters: currentProject.total_chapters || 200,
        coreSellingPoints: currentProject.core_selling_points || '',
        completeStoryline: currentProject.complete_storyline || {}
    };
    
    currentEditingIdeaForPhaseTwo = { id: 'new_creative', title: '新创意' };
    originalIdeaDataForPhaseTwo = JSON.parse(JSON.stringify(projectData));
    
    populateCreativeEditorForPhaseTwo(projectData);
    showCreativeEditorModalForPhaseTwo();
}

// 打开创意编辑器（两阶段页面专用）
function openCreativeEditorForPhaseTwo() {
    if (!selectedCreativeIdForPhaseTwo) {
        // 如果没有选择创意，则为当前项目创建编辑器
        if (!currentProject) {
            showStatusMessage('❌ 请先选择一个项目或创意', 'error');
            return;
        }
        
        // 基于当前项目数据初始化编辑器
        initializeEditorWithCurrentProject();
        return;
    }
    
    const idea = loadedCreativeIdeasForPhaseTwo.find(i => i.id === selectedCreativeIdForPhaseTwo);
    if (!idea) {
        showStatusMessage('❌ 找不到选中的创意数据', 'error');
        return;
    }
    
    currentEditingIdeaForPhaseTwo = idea;
    
    // 备份原始数据
    if (idea.raw_data) {
        originalIdeaDataForPhaseTwo = JSON.parse(JSON.stringify(idea.raw_data));
    } else {
        originalIdeaDataForPhaseTwo = JSON.parse(JSON.stringify(idea));
    }
    
    // 填充编辑器表单
    try {
        if (idea.raw_data && typeof idea.raw_data === 'object') {
            populateCreativeEditorForPhaseTwo(idea.raw_data);
        } else if (idea && typeof idea === 'object') {
            populateCreativeEditorForPhaseTwo(idea);
        } else {
            showStatusMessage('❌ 创意数据格式不正确，无法编辑', 'error');
            return;
        }
    } catch (error) {
        console.error('填充编辑器时出错:', error);
        showStatusMessage('❌ 填充编辑器数据时出错: ' + error.message, 'error');
        return;
    }
    
    // 显示编辑器模态框
    showCreativeEditorModalForPhaseTwo();
}