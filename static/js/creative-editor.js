// ==================== 创意编辑器功能 ====================

// 创意编辑器相关变量
let currentEditingIdea = null;
let originalIdeaData = null;

// 初始化字符计数功能
function initCharCounter() {
    const coreSettingTextarea = document.getElementById('edit-core-setting');
    const charCountSpan = document.getElementById('char-count');
    
    if (coreSettingTextarea && charCountSpan) {
        // 初始计数
        updateCharCount();
        
        // 监听输入变化
        coreSettingTextarea.addEventListener('input', updateCharCount);
        coreSettingTextarea.addEventListener('paste', function() {
            setTimeout(updateCharCount, 10);
        });
    }
}

// 更新字符计数
function updateCharCount() {
    const coreSettingTextarea = document.getElementById('edit-core-setting');
    const charCountSpan = document.getElementById('char-count');
    
    if (coreSettingTextarea && charCountSpan) {
        const charCount = coreSettingTextarea.value.length;
        charCountSpan.textContent = charCount + ' 字符';
        
        // 根据字符数改变颜色
        if (charCount < 100) {
            charCountSpan.style.color = '#ef4444'; // 红色 - 太少
        } else if (charCount < 300) {
            charCountSpan.style.color = '#f59e0b'; // 橙色 - 建议增加
        } else {
            charCountSpan.style.color = '#10b981'; // 绿色 - 良好
        }
    }
}

// 打开创意编辑器
function openCreativeEditor() {
    console.log('=== 创意编辑器调试信息 ===');
    console.log('选中的创意ID:', selectedCreativeId);
    console.log('已加载的创意列表:', loadedCreativeIdeas);
    
    if (!selectedCreativeId) {
        alert('请先选择一个创意');
        return;
    }
    
    const idea = loadedCreativeIdeas.find(i => i.id === selectedCreativeId);
    if (!idea) {
        console.error('找不到选中的创意数据，ID:', selectedCreativeId);
        alert('找不到选中的创意数据');
        return;
    }
    
    console.log('找到的创意数据:', idea);
    
    currentEditingIdea = idea;
    
    // 备份原始数据
    if (idea.raw_data) {
        originalIdeaData = JSON.parse(JSON.stringify(idea.raw_data));
        console.log('备份的原始数据:', originalIdeaData);
    } else {
        originalIdeaData = JSON.parse(JSON.stringify(idea));
        console.log('备份的创意对象:', originalIdeaData);
    }
    
    // 填充编辑器表单
    try {
        if (idea.raw_data && typeof idea.raw_data === 'object') {
            console.log('使用raw_data填充编辑器');
            populateCreativeEditor(idea.raw_data);
        } else if (idea && typeof idea === 'object') {
            console.log('使用创意对象本身填充编辑器');
            populateCreativeEditor(idea);
        } else {
            console.error('创意数据格式不正确:', idea);
            alert('创意数据格式不正确，无法编辑');
            return;
        }
    } catch (error) {
        console.error('填充编辑器时出错:', error);
        alert('填充编辑器数据时出错: ' + error.message);
        return;
    }
    
    // 使用内联样式强制显示编辑器模态框
    const modal = document.getElementById('creative-editor-modal');
    modal.style.cssText = `
        display: block !important;
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background: rgba(0,0,0,0.5) !important;
        z-index: 999999 !important;
    `;
    
    // 设置内容区域样式
    const modalContent = modal.querySelector('.modal-content') || modal.children[1];
    if (modalContent) {
        modalContent.style.cssText = `
            position: absolute !important;
            top: 50% !important;
            left: 50% !important;
            transform: translate(-50%, -50%) !important;
            background: white !important;
            border-radius: 12px !important;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3) !important;
            max-width: 900px !important;
            width: 90% !important;
            max-height: 85vh !important;
            overflow: hidden !important;
            z-index: 1000000 !important;
        `;
    }
    
    // 确保所有输入框可见
    const allInputs = modal.querySelectorAll('input, textarea');
    allInputs.forEach(input => {
        input.style.cssText = `
            background: white !important;
            color: #1f2937 !important;
            border: 2px solid #d1d5db !important;
            padding: 12px !important;
            border-radius: 8px;
            font-size: 14px;
        `;
    });
    
    document.body.style.overflow = 'hidden';
    
    console.log('创意编辑器已强制打开');
}

// 填充创意编辑器
function populateCreativeEditor(ideaData) {
    console.log('=== 填充创意编辑器 ===');
    console.log('输入数据:', ideaData);
    
    try {
        // 基本信息 - 支持多种可能的字段名
        const title = ideaData.novelTitle || ideaData.title || ideaData.novel_title || '';
        const synopsis = ideaData.synopsis || ideaData.description || ideaData.novel_synopsis || '';
        const coreSetting = ideaData.coreSetting || ideaData.core_setting || ideaData.coreSetting || '';
        const totalChapters = ideaData.totalChapters || ideaData.total_chapters || 200;
        
        console.log('提取的基本信息:', { title, synopsis, coreSetting, totalChapters });
        
        const titleElement = document.getElementById('edit-novel-title');
        const synopsisElement = document.getElementById('edit-novel-synopsis');
        const coreSettingElement = document.getElementById('edit-core-setting');
        const totalChaptersElement = document.getElementById('edit-total-chapters');
        
        if (titleElement) titleElement.value = title;
        if (synopsisElement) synopsisElement.value = synopsis;
        if (coreSettingElement) coreSettingElement.value = coreSetting;
        if (totalChaptersElement) totalChaptersElement.value = totalChapters;
        
        // 核心卖点 - 支持多种格式
        const sellingPoints = ideaData.coreSellingPoints || ideaData.core_selling_points || ideaData.sellingPoints || '';
        console.log('原始卖点数据:', sellingPoints);
        
        let pointsArray = [];
        if (typeof sellingPoints === 'string') {
            pointsArray = sellingPoints.split('+').map(p => p.trim()).filter(p => p);
        } else if (Array.isArray(sellingPoints)) {
            pointsArray = sellingPoints;
        }
        
        console.log('处理后的卖点数组:', pointsArray);
        populateSellingPoints(pointsArray);
        
        // 故事线 - 支持多种字段名
        const storyline = ideaData.completeStoryline || ideaData.complete_storyline || ideaData.storyline || {};
        console.log('故事线数据:', storyline);
        populateStoryline(storyline);
        
        console.log('创意编辑器填充完成');
        
    } catch (error) {
        console.error('填充创意编辑器时出错:', error);
        alert('填充数据时出错: ' + error.message);
    }
}

// 填充核心卖点
function populateSellingPoints(points) {
    const container = document.getElementById('selling-points-container');
    container.innerHTML = '';
    
    points.forEach((point, index) => {
        addSellingPointElement(point, index);
    });
}

// 添加卖点元素
function addSellingPointElement(point, index) {
    const container = document.getElementById('selling-points-container');
    const pointElement = document.createElement('div');
    pointElement.className = 'selling-point-item';
    pointElement.style.cssText = 'display: flex; gap: 8px; margin-bottom: 12px; align-items: center; padding: 8px; background: white; border-radius: 8px; border: 1px solid #e5e7eb;';
    pointElement.innerHTML = `
        <input type="text" value="${point}" placeholder="卖点描述"
               style="flex: 1; padding: 10px 14px; border: 2px solid #e5e7eb; border-radius: 8px; font-size: 14px; background: white; color: #1f2937; transition: all 0.2s; box-sizing: border-box;"
               class="selling-point-input">
        <button type="button" onclick="removeSellingPoint(this)"
                style="padding: 8px 12px; border: none; border-radius: 6px; background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; box-shadow: 0 2px 4px rgba(239, 68, 68, 0.2);">
            🗑️ 删除
        </button>
    `;
    container.appendChild(pointElement);
}

// 添加新的卖点
function addSellingPoint() {
    const input = document.getElementById('new-selling-point');
    const point = input.value.trim();
    
    if (!point) {
        alert('请输入卖点描述');
        return;
    }
    
    addSellingPointElement(point);
    input.value = '';
}

// 删除卖点
function removeSellingPoint(button) {
    button.parentElement.remove();
}

// 填充故事线
function populateStoryline(storyline) {
    console.log('=== 填充故事线 ===');
    console.log('故事线数据:', storyline);
    
    // 修正阶段映射，匹配HTML中的data-stage属性
    const stages = [
        { key: 'opening', dataKey: 'opening' },
        { key: 'development', dataKey: 'development' },
        { key: 'climax', dataKey: 'conflict' }, // HTML中是climax，数据中可能是conflict
        { key: 'ending', dataKey: 'ending' }
    ];
    
    stages.forEach(stage => {
        // 尝试从数据中获取阶段信息，支持多种可能的键名
        let stageData = storyline[stage.dataKey] || storyline[stage.key] || {};
        
        // 如果是字符串格式，尝试解析
        if (typeof stageData === 'string') {
            stageData = { stageName: stage.key, summary: stageData };
        }
        
        console.log(`阶段 ${stage.key} 数据:`, stageData);
        
        // 查找阶段编辑器容器
        const stageEditor = document.querySelector(`div[data-stage="${stage.key}"]`);
        console.log(`找到阶段编辑器 ${stage.key}:`, stageEditor);
        
        if (stageEditor) {
            // 查找对应的输入框
            const nameInput = stageEditor.querySelector(`input[data-stage="${stage.key}"]`);
            const descriptionInput = stageEditor.querySelector(`textarea[data-stage="${stage.key}"]`);
            
            console.log(`找到输入框 ${stage.key} - 名称:`, nameInput, '描述:', descriptionInput);
            
            if (nameInput) {
                const stageName = stageData.stageName || stageData.name || getDefaultStageName(stage.key);
                nameInput.value = stageName;
                console.log(`设置阶段名称 ${stage.key}:`, stageName);
            }
            if (descriptionInput) {
                const description = stageData.summary || stageData.description || stageData.content || '';
                descriptionInput.value = description;
                console.log(`设置阶段描述 ${stage.key}:`, description);
            }
        } else {
            console.warn(`未找到故事线阶段编辑器: ${stage.key}`);
        }
    });
}

// 重置创意编辑器
function resetCreativeEditor() {
    if (!originalIdeaData) {
        alert('没有原始数据可重置');
        return;
    }
    
    if (confirm('确定要重置所有修改吗？')) {
        populateCreativeEditor(originalIdeaData);
    }
}

// 保存创意修改
async function saveCreativeChanges() {
    if (!currentEditingIdea) {
        alert('没有正在编辑的创意');
        return;
    }
    
    try {
        // 收集表单数据
        const updatedData = collectCreativeEditorData();
        
        // 验证数据
        if (!validateCreativeData(updatedData)) {
            return;
        }
        
        // 发送到后端保存
        const response = await fetch('/api/creative-ideas/' + currentEditingIdea.id, {
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
            closeCreativeEditor();
            // 重新加载创意列表
            await loadCreativeIdeas();
            // 重新选择当前创意
            if (currentEditingIdea && currentEditingIdea.id) {
                const selectElement = document.getElementById('creative-idea-select');
                if (selectElement) {
                    selectElement.value = currentEditingIdea.id;
                    fillFromCreativeIdea();
                }
            }
        } else {
            throw new Error(result.error || '保存失败');
        }
        
    } catch (error) {
        console.error('保存创意失败:', error);
        alert('保存失败: ' + error.message);
    }
}

// 收集创意编辑器数据
function collectCreativeEditorData() {
    const totalChaptersElement = document.getElementById('edit-total-chapters');
    const totalChapters = totalChaptersElement ? parseInt(totalChaptersElement.value) || 200 : 200;
    
    const data = {
        novelTitle: document.getElementById('edit-novel-title').value.trim(),
        synopsis: document.getElementById('edit-novel-synopsis').value.trim(),
        coreSetting: document.getElementById('edit-core-setting').value.trim(),
        totalChapters: totalChapters,
        coreSellingPoints: '',
        completeStoryline: {}
    };
    
    // 收集卖点
    const sellingPointInputs = document.querySelectorAll('.selling-point-input');
    const sellingPoints = Array.from(sellingPointInputs)
        .map(input => input.value.trim())
        .filter(point => point);
    data.coreSellingPoints = sellingPoints.join(' + ');
    
    // 收集故事线 - 修正阶段映射
    const stageMappings = [
        { htmlKey: 'opening', dataKey: 'opening' },
        { htmlKey: 'development', dataKey: 'development' },
        { htmlKey: 'climax', dataKey: 'conflict' }, // 高潮阶段在数据中存储为conflict
        { htmlKey: 'ending', dataKey: 'ending' }
    ];
    
    stageMappings.forEach(mapping => {
        // 查找阶段编辑器容器
        const stageEditor = document.querySelector(`div[data-stage="${mapping.htmlKey}"]`);
        if (stageEditor) {
            // 查找对应的输入框
            const nameInput = stageEditor.querySelector(`input[data-stage="${mapping.htmlKey}"]`);
            const descriptionInput = stageEditor.querySelector(`textarea[data-stage="${mapping.htmlKey}"]`);
            
            data.completeStoryline[mapping.dataKey] = {
                stageName: nameInput ? nameInput.value.trim() : '',
                summary: descriptionInput ? descriptionInput.value.trim() : ''
            };
            
            console.log(`收集故事线阶段 ${mapping.htmlKey}:`, data.completeStoryline[mapping.dataKey]);
        } else {
            console.warn(`未找到故事线阶段编辑器: ${mapping.htmlKey}`);
        }
    });
    
    return data;
}

// 验证创意数据
function validateCreativeData(data) {
    if (!data.coreSetting) {
        alert('请填写核心设定');
        return false;
    }
    
    if (!data.novelTitle) {
        alert('请输入小说标题');
        return false;
    }
    
    if (data.totalChapters < 1 || data.totalChapters > 200) {
        alert('章节数必须在1-200之间');
        return false;
    }
    
    return true;
}

// 关闭创意编辑器
function closeCreativeEditor() {
    const modal = document.getElementById('creative-editor-modal');
    if (modal) {
        modal.style.display = 'none';
    }
    document.body.style.overflow = '';
    
    currentEditingIdea = null;
    originalIdeaData = null;
}