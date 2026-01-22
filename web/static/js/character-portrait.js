/**
 * 人物剧照生成页面 - 前端逻辑
 */

// 全局状态
const state = {
    novels: [],
    characters: [],
    selectedNovel: null,
    selectedCharacter: null,
    referenceImages: [],
    generationHistory: []
};

// DOM元素
const elements = {
    novelSelect: document.getElementById('novel-select'),
    characterGrid: document.getElementById('character-grid'),
    characterInfoCard: document.getElementById('character-info-card'),
    useReferenceCheckbox: document.getElementById('use-reference-image'),
    referenceImageSection: document.getElementById('reference-image-section'),
    referenceUploadArea: document.getElementById('reference-upload-area'),
    referenceImageInput: document.getElementById('reference-image-input'),
    referenceThumbnails: document.getElementById('reference-thumbnails'),
    aspectRatio: document.getElementById('aspect-ratio'),
    imageSize: document.getElementById('image-size'),
    customPrompt: document.getElementById('custom-prompt'),
    generateBtn: document.getElementById('generate-btn'),
    generationResult: document.getElementById('generation-result'),
    historyGrid: document.getElementById('history-grid'),
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingMessage: document.getElementById('loading-message'),
    toast: document.getElementById('toast')
};

// 初始化
async function init() {
    console.log('🎨 初始化人物剧照生成页面');
    
    // 绑定事件
    bindEvents();
    
    // 加载小说列表
    await loadNovels();
    
    // 从本地存储加载历史记录
    loadHistory();
}

// 绑定事件
function bindEvents() {
    // 小说选择
    elements.novelSelect.addEventListener('change', handleNovelChange);

    // 参考图像
    elements.useReferenceCheckbox.addEventListener('change', toggleReferenceImage);
    elements.referenceUploadArea.addEventListener('click', () => elements.referenceImageInput.click());
    elements.referenceImageInput.addEventListener('change', handleReferenceImageUpload);

    // 拖拽上传
    elements.referenceUploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        elements.referenceUploadArea.classList.add('drag-over');
    });
    elements.referenceUploadArea.addEventListener('dragleave', () => {
        elements.referenceUploadArea.classList.remove('drag-over');
    });
    elements.referenceUploadArea.addEventListener('drop', handleDrop);

    // 生成按钮
    elements.generateBtn.addEventListener('click', generatePortrait);
}

// 加载小说列表
async function loadNovels() {
    try {
        console.log('📚 加载小说列表...');
        const response = await fetch('/api/video/novels');
        const data = await response.json();
        
        if (data.success) {
            state.novels = data.novels;
            renderNovels(data.novels);
            console.log(`✅ 成功加载 ${data.novels.length} 个小说`);
        } else {
            throw new Error(data.error || '加载失败');
        }
    } catch (error) {
        console.error('❌ 加载小说列表失败:', error);
        showToast('error', '加载小说列表失败: ' + error.message);
    }
}

// 渲染小说列表
function renderNovels(novels) {
    elements.novelSelect.innerHTML = '<option value="">请选择小说...</option>';
    
    novels.forEach(novel => {
        const option = document.createElement('option');
        option.value = novel.title;
        option.textContent = `${novel.title} (${novel.total_medium_events || 0} 个事件)`;
        elements.novelSelect.appendChild(option);
    });
}

// 处理小说选择变化
async function handleNovelChange(e) {
    const title = e.target.value;
    state.selectedNovel = title;
    
    if (!title) {
        elements.characterGrid.innerHTML = '<div class="loading-message">请先选择小说</div>';
        elements.generateBtn.disabled = true;
        return;
    }
    
    await loadCharacters(title);
}

// 加载角色列表
async function loadCharacters(title) {
    try {
        console.log(`👥 加载小说角色: ${title}`);
        elements.characterGrid.innerHTML = '<div class="loading-message">正在加载角色...</div>';
        
        const response = await fetch(`/api/video/novel-content?title=${encodeURIComponent(title)}`);
        const data = await response.json();
        
        if (data.success) {
            state.characters = data.characters;
            renderCharacters(data.characters);
            updateGenerateButton();
            console.log(`✅ 成功加载 ${data.characters.length} 个角色`);
        } else {
            throw new Error(data.error || '加载失败');
        }
    } catch (error) {
        console.error('❌ 加载角色失败:', error);
        elements.characterGrid.innerHTML = '<div class="loading-message">加载失败</div>';
        showToast('error', '加载角色失败: ' + error.message);
    }
}

// 渲染角色列表
function renderCharacters(characters) {
    elements.characterGrid.innerHTML = '';
    
    if (characters.length === 0) {
        elements.characterGrid.innerHTML = '<div class="loading-message">该小说暂无角色设计</div>';
        return;
    }
    
    characters.forEach((char, index) => {
        const card = document.createElement('div');
        card.className = 'character-card';
        card.dataset.index = index;
        
        const avatar = document.createElement('div');
        avatar.className = 'character-avatar';
        avatar.textContent = char.name.charAt(0);
        
        const name = document.createElement('div');
        name.className = 'character-name';
        name.textContent = char.name;
        
        const role = document.createElement('div');
        role.className = 'character-role';
        role.textContent = char.role || '角色';
        
        card.appendChild(avatar);
        card.appendChild(name);
        card.appendChild(role);
        
        card.addEventListener('click', () => selectCharacter(index));
        
        elements.characterGrid.appendChild(card);
    });
}

// 选择角色
function selectCharacter(index) {
    // 移除之前的选中状态
    document.querySelectorAll('.character-card').forEach(card => {
        card.classList.remove('selected');
    });
    
    // 添加选中状态
    const selectedCard = document.querySelector(`.character-card[data-index="${index}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }
    
    state.selectedCharacter = state.characters[index];
    renderCharacterInfo(state.selectedCharacter);
    updateGenerateButton();
    
    console.log('✅ 选择角色:', state.selectedCharacter.name);
}

// 渲染角色信息
function renderCharacterInfo(character) {
    elements.characterInfoCard.innerHTML = `
        <div class="selected-character-info">
            <div class="selected-character-avatar">
                ${character.name.charAt(0)}
            </div>
            <div class="selected-character-details">
                <h4>${character.name}</h4>
                <span class="role-badge">${character.role || '角色'}</span>
                <p>${character.description || '暂无描述'}</p>
            </div>
        </div>
    `;
}

// 切换参考图像
function toggleReferenceImage(e) {
    const checked = e.target.checked;
    if (checked) {
        elements.referenceImageSection.classList.remove('hidden');
    } else {
        elements.referenceImageSection.classList.add('hidden');
        state.referenceImages = [];
        renderThumbnails();
    }
}

// 处理参考图像上传
function handleReferenceImageUpload(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    addReferenceImages(files);
    e.target.value = '';
}

// 处理拖拽上传
function handleDrop(e) {
    e.preventDefault();
    elements.referenceUploadArea.classList.remove('drag-over');

    const files = Array.from(e.dataTransfer.files).filter(file => file.type.startsWith('image/'));
    if (files.length === 0) {
        showToast('error', '请上传图片文件');
        return;
    }

    addReferenceImages(files);
}

// 添加参考图像
function addReferenceImages(files) {
    const remainingSlots = 5 - state.referenceImages.length;
    if (remainingSlots <= 0) {
        showToast('warning', '最多只能上传5张参考图像');
        return;
    }

    const filesToAdd = files.slice(0, remainingSlots);
    if (files.length > remainingSlots) {
        showToast('warning', `最多只能上传5张图像，已选择前${remainingSlots}张`);
    }

    filesToAdd.forEach(file => {
        const reader = new FileReader();
        reader.onload = (e) => {
            state.referenceImages.push(e.target.result);
            renderThumbnails();
            if (state.referenceImages.length === filesToAdd.length) {
                showToast('success', `成功添加${filesToAdd.length}张参考图像`);
            }
        };
        reader.readAsDataURL(file);
    });
}

// 渲染缩略图
function renderThumbnails() {
    elements.referenceThumbnails.innerHTML = '';

    if (state.referenceImages.length === 0) {
        elements.referenceUploadArea.querySelector('.upload-placeholder').classList.remove('hidden');
        return;
    }

    elements.referenceUploadArea.querySelector('.upload-placeholder').classList.add('hidden');

    state.referenceImages.forEach((imageData, index) => {
        const thumbnailItem = document.createElement('div');
        thumbnailItem.className = 'thumbnail-item';

        const img = document.createElement('img');
        img.src = imageData;
        img.alt = `参考图 ${index + 1}`;

        const removeBtn = document.createElement('button');
        removeBtn.className = 'thumbnail-remove';
        removeBtn.textContent = '×';
        removeBtn.onclick = () => removeReferenceImage(index);

        thumbnailItem.appendChild(img);
        thumbnailItem.appendChild(removeBtn);
        elements.referenceThumbnails.appendChild(thumbnailItem);
    });
}

// 移除参考图像
function removeReferenceImage(index) {
    state.referenceImages.splice(index, 1);
    renderThumbnails();
    console.log(`🗑️ 已移除参考图像 ${index + 1}`);
}

// 更新生成按钮状态
function updateGenerateButton() {
    const canGenerate = state.selectedNovel && state.selectedCharacter;
    elements.generateBtn.disabled = !canGenerate;
}

// 生成剧照
async function generatePortrait() {
    if (!state.selectedNovel || !state.selectedCharacter) {
        showToast('error', '请先选择小说和角色');
        return;
    }
    
    // 显示加载状态
    showLoading('正在生成剧照，请稍候...');
    
    try {
        console.log('🎨 开始生成剧照');
        console.log('📝 参数:', {
            title: state.selectedNovel,
            character: state.selectedCharacter.name,
            aspectRatio: elements.aspectRatio.value,
            imageSize: elements.imageSize.value,
            referenceImagesCount: state.referenceImages.length,
            customPrompt: elements.customPrompt.value
        });
        
        // 准备请求数据
        const requestData = {
            title: state.selectedNovel,
            character_id: state.selectedCharacter.name,
            character_data: state.selectedCharacter,
            aspect_ratio: elements.aspectRatio.value,
            image_size: elements.imageSize.value
        };
        
        // 如果有参考图像，先上传
        if (state.referenceImages.length > 0) {
            console.log(`📷 上传${state.referenceImages.length}张参考图像...`);
            // 将base64转换为文件
            const refImagePaths = [];
            for (const imageData of state.referenceImages) {
                const response = await fetch(imageData);
                const blob = await response.blob();
                const formData = new FormData();
                formData.append('reference_image', blob);

                // 这里需要添加上传接口
                // 暂时使用本地存储方式
                const refImagePath = await uploadReferenceImage(blob);
                if (refImagePath) {
                    refImagePaths.push(refImagePath);
                }
            }
            if (refImagePaths.length > 0) {
                requestData.reference_images = refImagePaths;
            }
        }
        
        // 如果有自定义提示词，添加到请求数据
        if (elements.customPrompt.value.trim()) {
            // 注意：这里需要在后端处理自定义提示词
            console.log('📝 使用自定义提示词:', elements.customPrompt.value);
        }
        
        // 调用生成API
        const apiResponse = await fetch('/api/video/generate-character-portrait', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await apiResponse.json();
        
        if (result.success) {
            console.log('✅ 剧照生成成功:', result.image_url);
            
            // 显示结果
            renderGeneratedImage(result);
            
            // 添加到历史记录
            addToHistory({
                ...result,
                characterName: state.selectedCharacter.name,
                characterRole: state.selectedCharacter.role,
                timestamp: new Date().toISOString()
            });
            
            showToast('success', `角色 ${state.selectedCharacter.name} 的剧照生成成功！`);
        } else {
            throw new Error(result.error || '生成失败');
        }
    } catch (error) {
        console.error('❌ 生成剧照失败:', error);
        showToast('error', '生成失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

// 上传参考图像（简化版）
async function uploadReferenceImage(blob) {
    // 这里需要实现实际的上传逻辑
    // 暂时返回null，表示不上传
    console.warn('⚠️ 参考图像上传功能需要后端支持');
    return null;
}

// 渲染生成的图像
function renderGeneratedImage(result) {
    elements.generationResult.innerHTML = `
        <div class="generated-image-container">
            <img src="${result.image_url}" alt="${result.character_name} 剧照" />
            <div class="image-actions">
                <button class="btn btn-secondary" onclick="downloadImage('${result.image_url}', '${result.character_name}_剧照.png')">
                    📥 下载
                </button>
                <button class="btn btn-secondary" onclick="useAsReference('${result.image_url}')">
                    🔄 用作参考图
                </button>
            </div>
            ${result.used_reference_image ? '<p style="text-align: center; color: #666; margin-top: 12px;">✨ 使用了参考图像生成</p>' : ''}
        </div>
    `;
}

// 下载图像
function downloadImage(url, filename) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    console.log('📥 下载图像:', filename);
}

// 用作参考图
function useAsReference(url) {
    if (state.referenceImages.length >= 5) {
        showToast('warning', '最多只能添加5张参考图像');
        return;
    }
    state.referenceImages.push(url);
    renderThumbnails();
    elements.useReferenceCheckbox.checked = true;
    elements.referenceImageSection.classList.remove('hidden');
    showToast('success', '已将生成的图像添加为参考图');
}

// 添加到历史记录
function addToHistory(item) {
    state.generationHistory.unshift(item);
    
    // 限制历史记录数量
    if (state.generationHistory.length > 20) {
        state.generationHistory.pop();
    }
    
    // 保存到本地存储
    localStorage.setItem('portrait_history', JSON.stringify(state.generationHistory));
    
    // 渲染历史记录
    renderHistory();
}

// 从本地存储加载历史记录
function loadHistory() {
    const saved = localStorage.getItem('portrait_history');
    if (saved) {
        try {
            state.generationHistory = JSON.parse(saved);
            renderHistory();
            console.log(`📜 加载了 ${state.generationHistory.length} 条历史记录`);
        } catch (error) {
            console.error('❌ 加载历史记录失败:', error);
        }
    }
}

// 渲染历史记录
function renderHistory() {
    if (state.generationHistory.length === 0) {
        elements.historyGrid.innerHTML = '<div class="no-history">暂无生成历史</div>';
        return;
    }
    
    elements.historyGrid.innerHTML = '';
    
    state.generationHistory.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.title = `${item.characterName} - ${new Date(item.timestamp).toLocaleString()}`;
        
        const img = document.createElement('img');
        img.src = item.image_url;
        img.alt = item.characterName;
        
        historyItem.appendChild(img);
        historyItem.addEventListener('click', () => {
            renderGeneratedImage(item);
        });
        
        elements.historyGrid.appendChild(historyItem);
    });
}

// 显示加载状态
function showLoading(message) {
    elements.loadingMessage.textContent = message;
    elements.loadingOverlay.classList.remove('hidden');
}

// 隐藏加载状态
function hideLoading() {
    elements.loadingOverlay.classList.add('hidden');
}

// 显示Toast提示
function showToast(type, message) {
    const toast = elements.toast;
    const icon = toast.querySelector('.toast-icon');
    const msg = toast.querySelector('.toast-message');
    
    // 设置图标
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️'
    };
    icon.textContent = icons[type] || 'ℹ️';
    
    // 设置消息
    msg.textContent = message;
    
    // 设置类型
    toast.className = `toast ${type}`;
    
    // 显示
    toast.classList.remove('hidden');
    
    // 3秒后自动隐藏
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);