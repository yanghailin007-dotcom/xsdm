/**
 * 剧照图片素材库 JavaScript
 * 管理和显示剧照图片
 */

// API 基础URL
const API_BASE = '/api/still-images';

// 当前选中的图片
let currentImage = null;

// 所有图片数据
let allImages = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadStatistics();
    loadImages();
});

/**
 * 初始化事件监听器
 */
function initializeEventListeners() {
    // 过滤器变化
    document.getElementById('typeFilter').addEventListener('change', loadImages);
    document.getElementById('novelFilter').addEventListener('change', loadImages);
    document.getElementById('statusFilter').addEventListener('change', loadImages);
    
    // 刷新按钮
    document.getElementById('refreshBtn').addEventListener('click', () => {
        loadStatistics();
        loadImages();
    });
    
    // 导出按钮
    document.getElementById('exportBtn').addEventListener('click', exportMetadata);
    
    // 模态框关闭
    document.querySelector('.close').addEventListener('click', closeModal);
    
    // 点击模态框外部关闭
    document.getElementById('imageModal').addEventListener('click', (e) => {
        if (e.target.id === 'imageModal') {
            closeModal();
        }
    });
    
    // 模态框中的按钮
    document.getElementById('downloadBtn').addEventListener('click', downloadCurrentImage);
    document.getElementById('deleteBtn').addEventListener('click', deleteCurrentImage);
}

/**
 * 加载统计信息
 */
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/statistics`);
        const result = await response.json();
        
        if (result.success) {
            const stats = result.data;
            document.getElementById('totalCount').textContent = stats.total_count;
            document.getElementById('characterCount').textContent = stats.type_counts.character || 0;
            document.getElementById('sceneCount').textContent = stats.type_counts.scene || 0;
            document.getElementById('customCount').textContent = stats.type_counts.custom || 0;
            document.getElementById('totalSize').textContent = `${stats.total_size_mb} MB`;
            
            // 更新小说过滤器
            updateNovelFilter(stats.novel_counts);
        }
    } catch (error) {
        console.error('加载统计信息失败:', error);
    }
}

/**
 * 更新小说过滤器
 */
function updateNovelFilter(novelCounts) {
    const select = document.getElementById('novelFilter');
    select.innerHTML = '<option value="">全部</option>';
    
    for (const [novel, count] of Object.entries(novelCounts)) {
        const option = document.createElement('option');
        option.value = novel;
        option.textContent = `${novel} (${count})`;
        select.appendChild(option);
    }
}

/**
 * 加载图片列表
 */
async function loadImages() {
    showLoading();
    
    try {
        const typeFilter = document.getElementById('typeFilter').value;
        const novelFilter = document.getElementById('novelFilter').value;
        const statusFilter = document.getElementById('statusFilter').value;
        
        // 构建查询参数
        const params = new URLSearchParams();
        params.append('limit', '100');
        if (typeFilter) params.append('image_type', typeFilter);
        if (novelFilter) params.append('novel_title', novelFilter);
        if (statusFilter) params.append('status', statusFilter);
        
        const response = await fetch(`${API_BASE}?${params.toString()}`);
        const result = await response.json();
        
        if (result.success) {
            allImages = result.data;
            displayImages(result.data);
        } else {
            console.error('加载图片失败:', result.error);
        }
    } catch (error) {
        console.error('加载图片失败:', error);
    } finally {
        hideLoading();
    }
}

/**
 * 显示图片列表
 */
function displayImages(images) {
    const grid = document.getElementById('imageGrid');
    const emptyState = document.getElementById('emptyState');
    
    grid.innerHTML = '';
    
    if (images.length === 0) {
        grid.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }
    
    grid.style.display = 'grid';
    emptyState.style.display = 'none';
    
    images.forEach(image => {
        const card = createImageCard(image);
        grid.appendChild(card);
    });
}

/**
 * 创建图片卡片
 */
function createImageCard(image) {
    const card = document.createElement('div');
    card.className = 'image-card';
    card.dataset.imageId = image.image_id;
    
    const typeClass = `type-${image.image_type}`;
    const typeText = getTypeText(image.image_type);
    
    const createdAt = new Date(image.created_at).toLocaleString('zh-CN');
    const fileSize = formatFileSize(image.file_size);
    
    card.innerHTML = `
        <img src="${image.image_url}" alt="${image.prompt}" class="image-thumbnail" loading="lazy">
        <div class="image-info">
            <span class="image-type ${typeClass}">${typeText}</span>
            <div class="image-title">${getImageTitle(image)}</div>
            <div class="image-meta">
                <div class="meta-item">
                    <span>📅</span>
                    <span>${createdAt}</span>
                </div>
                <div class="meta-item">
                    <span>💾</span>
                    <span>${fileSize}</span>
                </div>
            </div>
            <div class="image-actions">
                <button class="btn btn-secondary" onclick="viewImage('${image.image_id}')">查看</button>
                <button class="btn btn-primary" onclick="downloadImage('${image.image_id}')">下载</button>
            </div>
        </div>
    `;
    
    card.addEventListener('click', (e) => {
        if (!e.target.closest('button')) {
            viewImage(image.image_id);
        }
    });
    
    return card;
}

/**
 * 获取图片类型文本
 */
function getTypeText(type) {
    const typeMap = {
        'character': '角色剧照',
        'scene': '场景剧照',
        'custom': '自定义剧照'
    };
    return typeMap[type] || type;
}

/**
 * 获取图片标题
 */
function getImageTitle(image) {
    if (image.image_type === 'character' && image.character_name) {
        return image.character_name;
    } else if (image.image_type === 'scene' && image.event_name) {
        return image.event_name;
    } else if (image.novel_title) {
        return image.novel_title;
    } else {
        return '自定义剧照';
    }
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * 查看图片详情
 */
function viewImage(imageId) {
    const image = allImages.find(img => img.image_id === imageId);
    if (!image) return;
    
    currentImage = image;
    
    document.getElementById('modalImage').src = image.image_url;
    document.getElementById('modalType').textContent = getTypeText(image.image_type);
    document.getElementById('modalNovel').textContent = image.novel_title || '-';
    document.getElementById('modalCharacter').textContent = 
        image.character_name || image.event_name || '-';
    document.getElementById('modalDate').textContent = 
        new Date(image.created_at).toLocaleString('zh-CN');
    document.getElementById('modalSize').textContent = formatFileSize(image.file_size);
    document.getElementById('modalPrompt').textContent = 
        image.prompt.length > 200 ? image.prompt.substring(0, 200) + '...' : image.prompt;
    
    openModal();
}

/**
 * 下载图片
 */
function downloadImage(imageId) {
    const image = allImages.find(img => img.image_id === imageId);
    if (!image || !image.image_url) return;
    
    const link = document.createElement('a');
    link.href = image.image_url;
    link.download = `${getImageTitle(image)}_${image.image_id}.png`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * 下载当前图片
 */
function downloadCurrentImage() {
    if (!currentImage) return;
    downloadImage(currentImage.image_id);
}

/**
 * 删除当前图片
 */
async function deleteCurrentImage() {
    if (!currentImage) return;
    
    if (!confirm(`确定要删除这张剧照吗？\n\n${getImageTitle(currentImage)}`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/${currentImage.image_id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('删除成功');
            closeModal();
            loadStatistics();
            loadImages();
        } else {
            alert(`删除失败: ${result.error}`);
        }
    } catch (error) {
        console.error('删除图片失败:', error);
        alert('删除失败，请重试');
    }
}

/**
 * 导出元数据
 */
async function exportMetadata() {
    try {
        const response = await fetch(`${API_BASE}/export`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert(`元数据导出成功！\n\n文件路径: ${result.output_file}`);
        } else {
            alert(`导出失败: ${result.error}`);
        }
    } catch (error) {
        console.error('导出元数据失败:', error);
        alert('导出失败，请重试');
    }
}

/**
 * 打开模态框
 */
function openModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
}

/**
 * 关闭模态框
 */
function closeModal() {
    const modal = document.getElementById('imageModal');
    modal.classList.remove('show');
    document.body.style.overflow = '';
    currentImage = null;
}

/**
 * 显示加载状态
 */
function showLoading() {
    document.getElementById('loadingState').style.display = 'block';
    document.getElementById('imageGrid').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
}

/**
 * 隐藏加载状态
 */
function hideLoading() {
    document.getElementById('loadingState').style.display = 'none';
}
