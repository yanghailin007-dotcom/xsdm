/**
 * 小说封面生成器 - 前端逻辑
 * Novel Cover Generator - Frontend Logic
 */

// 全局变量
let currentColorScheme = 'blue';
let generatedImages = [];
let selectedImages = new Set();
let generationHistory = [];
let isGenerating = false;

// 提示词模板
const promptTemplates = {
    fantasy: {
        title: '玄幻修仙模板',
        prompt: `小说封面设计，竖版比例，中国风玄幻修仙风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 古风修仙风格，云雾缭绕的仙山背景
- 主角形象：身穿白衣或青衫的修仙者，飘逸出尘
- 场景：古代宫殿、仙山云海、修炼洞府等
- 色调：以蓝色、青色、白色为主，营造仙气飘飘的氛围
- 书名要醒目突出，使用古风字体
- 作者名放在适当位置
- 整体设计神秘而高雅，体现修仙世界的宏大

【特色元素】：
- 可以加入飞剑、法宝、仙鹤、祥云等修仙元素
- 背景可以有远山、云海、古松等
- 人物姿态要飘逸，体现修仙者的气质`
    },
    urban: {
        title: '都市言情模板',
        prompt: `小说封面设计，竖版比例，现代都市言情风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 现代都市风格，背景为城市天际线或现代建筑
- 主角形象：时尚的男女主角，衣着现代得体
- 场景：咖啡厅、写字楼、街头、海边等浪漫场景
- 色调：温暖柔和的色调，粉色、橙色、蓝色等
- 书名要醒目突出，使用现代简约字体
- 作者名放在适当位置
- 整体设计时尚浪漫，体现都市爱情的美好

【特色元素】：
- 可以加入咖啡杯、手机、鲜花等现代元素
- 背景可以有城市夜景、霓虹灯等
- 人物表情要甜蜜，体现恋爱的幸福感`
    },
    historical: {
        title: '历史架空模板',
        prompt: `小说封面设计，竖版比例，古典历史风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 古典历史风格，背景为古代建筑或山水画
- 主角形象：身穿古装的古人，气质儒雅或英武
- 场景：古代宫殿、书院、战场、园林等历史场景
- 色调：以红色、金色、棕色等传统色调为主
- 书名要醒目突出，使用书法字体
- 作者名放在适当位置
- 整体设计古朴典雅，体现历史文化底蕴

【特色元素】：
- 可以加入古琴、毛笔、卷轴、古剑等传统元素
- 背景可以有古建筑、山水画、书法作品等
- 人物服饰要符合历史时期特色`
    },
    scifi: {
        title: '科幻未来模板',
        prompt: `小说封面设计，竖版比例，科幻未来风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 科幻未来风格，背景为太空、未来城市或科技场景
- 主角形象：身穿未来服装的角色，可以有人类和外星人
- 场景：太空站、未来都市、飞船、实验室等科幻场景
- 色调：以蓝色、紫色、银色等科技感色调为主
- 书名要醒目突出，使用科技感字体
- 作者名放在适当位置
- 整体设计充满科技感和未来感

【特色元素】：
- 可以加入飞船、机器人、全息投影、能量护盾等科幻元素
- 背景可以有星空、未来建筑、科技界面等
- 人物可以有多种族，体现未来世界的多样性`
    },
    martial: {
        title: '武侠江湖模板',
        prompt: `小说封面设计，竖版比例，传统武侠风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 传统武侠风格，背景为江湖山水或古战场
- 主角形象：身穿古装的武林高手，手持兵器
- 场景：古战场、武林大会、山间小路、酒楼等武侠场景
- 色调：以红色、黑色、金色等豪迈色调为主
- 书名要醒目突出，使用苍劲有力的字体
- 作者名放在适当位置
- 整体设计充满江湖豪情和武侠精神

【特色元素】：
- 可以加入刀剑、酒坛、古琴、江湖令牌等武侠元素
- 背景可以有古战场、名山大川、古建筑等
- 人物姿态要威武，体现武林高手的气概`
    },
    mystery: {
        title: '悬疑推理模板',
        prompt: `小说封面设计，竖版比例，悬疑推理风格

【封面文字内容】：
书名：《{novel_title}》
作者：{author_name}

【严格禁止的内容】：
- 禁止添加任何其他文字
- 禁止出现"番茄小说"、"番茄"等平台相关文字
- 禁止水印、标语、宣传语
- 禁止任何额外标注文字

【设计要求】：
- 悬疑推理风格，背景为神秘场景或犯罪现场
- 主角形象：侦探或相关人物，表情严肃专注
- 场景：雨夜街道、老旧建筑、犯罪现场、书房等悬疑场景
- 色调：以深色、灰色、蓝色等神秘色调为主
- 书名要醒目突出，使用神秘感字体
- 作者名放在适当位置
- 整体设计充满悬疑和推理氛围

【特色元素】：
- 可以加入放大镜、指纹、手铐、凶器等推理元素
- 背景可以有雨夜、阴影、老旧建筑等
- 人物表情要严肃，体现侦探的专注和智慧`
    }
};

// 颜色方案映射
const colorSchemes = {
    blue: '蓝色系，以蓝色为主色调，清新自然',
    red: '红色系，以红色为主色调，热情奔放',
    green: '绿色系，以绿色为主色调，生机勃勃',
    purple: '紫色系，以紫色为主色调，神秘优雅',
    gold: '金色系，以金色为主色调，华贵大气',
    dark: '暗色系，以深色为主色调，深沉神秘'
};

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    loadGenerationHistory();
});

// 初始化事件监听器
function initializeEventListeners() {
    // 配色方案选择
    document.querySelectorAll('.color-scheme-item').forEach(item => {
        item.addEventListener('click', function() {
            selectColorScheme(this.dataset.scheme);
        });
    });

    // 表单输入监听
    document.getElementById('novel-title').addEventListener('input', updatePreview);
    document.getElementById('author-name').addEventListener('input', updatePreview);
    document.getElementById('cover-style').addEventListener('change', updatePreview);

    // 键盘快捷键
    document.addEventListener('keydown', function(event) {
        if (event.ctrlKey && event.key === 'Enter') {
            event.preventDefault();
            if (isGenerating) {
                return;
            }
            generateCover();
        }
    });
}

// 选择配色方案
function selectColorScheme(scheme) {
    currentColorScheme = scheme;
    
    // 更新UI状态
    document.querySelectorAll('.color-scheme-item').forEach(item => {
        item.classList.remove('active');
    });
    document.querySelector(`[data-scheme="${scheme}"]`).classList.add('active');
    
    // 更新预览
    updatePreview();
}

// 加载提示词模板
function loadTemplate(type) {
    const template = promptTemplates[type];
    if (!template) return;

    const novelTitle = document.getElementById('novel-title').value.trim();
    const authorName = document.getElementById('author-name').value.trim();
    
    // 替换模板变量
    let prompt = template.prompt;
    prompt = prompt.replace('{novel_title}', novelTitle || '小说标题');
    prompt = prompt.replace('{author_name}', authorName || '作者名称');
    
    document.getElementById('custom-prompt').value = prompt;
    
    // 显示提示
    showNotification(`已加载${template.title}提示词模板`, 'success');
}

// 生成封面
async function generateCover() {
    if (isGenerating) {
        showNotification('正在生成中，请稍候...', 'warning');
        return;
    }

    // 验证输入
    const novelTitle = document.getElementById('novel-title').value.trim();
    const authorName = document.getElementById('author-name').value.trim();
    const customPrompt = document.getElementById('custom-prompt').value.trim();
    
    if (!novelTitle) {
        showNotification('请输入小说标题', 'error');
        return;
    }
    
    if (!customPrompt) {
        showNotification('请输入提示词或选择模板', 'error');
        return;
    }

    // 获取生成参数
    const params = {
        novel_title: novelTitle,
        author_name: authorName || '佚名',
        genre: document.getElementById('novel-genre').value,
        style: document.getElementById('cover-style').value,
        color_scheme: currentColorScheme,
        image_size: document.getElementById('image-size').value,
        custom_prompt: customPrompt,
        negative_prompt: document.getElementById('negative-prompt').value.trim(),
        add_watermark: document.getElementById('add-watermark').checked,
        generation_count: parseInt(document.getElementById('generation-count').value)
    };

    try {
        isGenerating = true;
        showGenerationProgress(true);
        
        // 调用API生成封面
        const response = await fetch('/api/generate-cover', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '生成失败');
        }

        const result = await response.json();
        
        // 处理生成结果
        handleGenerationResult(result);
        
    } catch (error) {
        console.error('生成封面失败:', error);
        showNotification(`生成失败: ${error.message}`, 'error');
    } finally {
        isGenerating = false;
        showGenerationProgress(false);
    }
}

// 处理生成结果
function handleGenerationResult(result) {
    if (!result.success) {
        showNotification(result.error || '生成失败', 'error');
        return;
    }

    // 添加到生成历史
    const historyItem = {
        id: Date.now(),
        timestamp: new Date().toISOString(),
        params: result.params,
        images: result.images || []
    };
    
    generationHistory.unshift(historyItem);
    if (generationHistory.length > 10) {
        generationHistory = generationHistory.slice(0, 10);
    }
    
    // 显示生成的图片
    displayGeneratedImages(result.images);
    
    // 更新历史记录显示
    updateHistoryDisplay();
    
    // 显示重新生成按钮
    document.getElementById('generate-btn').style.display = 'none';
    document.getElementById('regenerate-btn').style.display = 'inline-block';
    
    showNotification(`成功生成 ${result.images.length} 张封面`, 'success');
}

// 显示生成的图片
function displayGeneratedImages(images) {
    generatedImages = images;
    selectedImages.clear();
    
    const resultsGrid = document.getElementById('results-grid');
    resultsGrid.innerHTML = '';
    
    images.forEach((image, index) => {
        const resultItem = createResultItem(image, index);
        resultsGrid.appendChild(resultItem);
    });
    
    // 更新计数
    document.getElementById('results-count').textContent = `共 ${images.length} 张`;
    
    // 显示批量操作按钮
    if (images.length > 0) {
        document.getElementById('batch-actions').style.display = 'flex';
    }
}

// 创建结果项
function createResultItem(image, index) {
    const resultItem = document.createElement('div');
    resultItem.className = 'result-item';
    resultItem.dataset.index = index;
    
    const img = document.createElement('img');
    img.src = image.url;
    img.alt = `封面 ${index + 1}`;
    img.loading = 'lazy';
    
    const resultInfo = document.createElement('div');
    resultInfo.className = 'result-info';
    resultInfo.innerHTML = `
        <div>封面 ${index + 1}</div>
        <div>${image.size || '1K'}</div>
    `;
    
    const checkbox = document.createElement('div');
    checkbox.className = 'result-checkbox';
    checkbox.innerHTML = '✓';
    
    resultItem.appendChild(img);
    resultItem.appendChild(resultInfo);
    resultItem.appendChild(checkbox);
    
    // 添加点击事件
    resultItem.addEventListener('click', function(e) {
        if (e.target === checkbox) {
            toggleImageSelection(index);
        } else {
            showImageModal(image, index);
        }
    });
    
    return resultItem;
}

// 切换图片选择状态
function toggleImageSelection(index) {
    const resultItem = document.querySelector(`[data-index="${index}"]`);
    
    if (selectedImages.has(index)) {
        selectedImages.delete(index);
        resultItem.classList.remove('selected');
    } else {
        selectedImages.add(index);
        resultItem.classList.add('selected');
    }
}

// 显示图片模态框
function showImageModal(image, index) {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-image');
    const modalTime = document.getElementById('modal-time');
    const modalPrompt = document.getElementById('modal-prompt');
    const modalSize = document.getElementById('modal-size');
    
    modalImg.src = image.url;
    modalTime.textContent = new Date(image.timestamp || Date.now()).toLocaleString('zh-CN');
    modalPrompt.textContent = image.prompt || '无';
    modalSize.textContent = image.size || '1K';
    
    modal.style.display = 'flex';
    
    // 保存当前图片信息用于下载
    modal.dataset.imageIndex = index;
}

// 关闭图片模态框
function closeImageModal() {
    document.getElementById('image-modal').style.display = 'none';
}

// 下载模态框图片
function downloadModalImage() {
    const index = parseInt(document.getElementById('image-modal').dataset.imageIndex);
    downloadImage(index);
}

// 下载单张图片
function downloadImage(index) {
    const image = generatedImages[index];
    if (!image) return;
    
    const link = document.createElement('a');
    link.href = image.url;
    link.download = `cover_${index + 1}_${Date.now()}.jpg`;
    link.click();
}

// 下载选中的图片
function downloadSelected() {
    if (selectedImages.size === 0) {
        showNotification('请先选择要下载的图片', 'warning');
        return;
    }
    
    selectedImages.forEach(index => {
        setTimeout(() => downloadImage(index), 100);
    });
    
    showNotification(`开始下载 ${selectedImages.size} 张图片`, 'success');
}

// 全选图片
function selectAll() {
    generatedImages.forEach((_, index) => {
        selectedImages.add(index);
        const resultItem = document.querySelector(`[data-index="${index}"]`);
        if (resultItem) {
            resultItem.classList.add('selected');
        }
    });
}

// 取消全选
function deselectAll() {
    selectedImages.clear();
    document.querySelectorAll('.result-item').forEach(item => {
        item.classList.remove('selected');
    });
}

// 重新生成
function regenerateCover() {
    generateCover();
}

// 清空预览
function clearPreview() {
    const previewContainer = document.getElementById('preview-container');
    previewContainer.innerHTML = `
        <div class="preview-placeholder">
            <div class="preview-icon">🎨</div>
            <h3>封面预览区域</h3>
            <p>填写信息后点击生成按钮开始制作封面</p>
        </div>
    `;
    
    document.getElementById('clear-btn').style.display = 'none';
}

// 更新预览
function updatePreview() {
    const novelTitle = document.getElementById('novel-title').value.trim();
    const authorName = document.getElementById('author-name').value.trim();
    
    if (novelTitle || authorName) {
        // 这里可以添加实时预览逻辑
        console.log('更新预览:', { novelTitle, authorName });
    }
}

// 显示生成进度
function showGenerationProgress(show) {
    const progressSection = document.getElementById('generation-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    if (show) {
        progressSection.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = '正在生成封面...';
        
        // 模拟进度更新
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) {
                clearInterval(progressInterval);
                progress = 90;
            }
            progressFill.style.width = progress + '%';
            progressText.textContent = `正在生成封面... ${Math.round(progress)}%`;
        }, 500);
        
        progressSection.dataset.interval = progressInterval;
    } else {
        progressSection.style.display = 'none';
        if (progressSection.dataset.interval) {
            clearInterval(progressSection.dataset.interval);
        }
    }
}

// 更新历史记录显示
function updateHistoryDisplay() {
    const historyContainer = document.getElementById('history-container');
    
    if (generationHistory.length === 0) {
        historyContainer.innerHTML = `
            <div class="history-placeholder">
                <p>暂无生成历史</p>
            </div>
        `;
        return;
    }
    
    historyContainer.innerHTML = generationHistory.map(item => `
        <div class="history-item" onclick="loadHistoryItem('${item.id}')">
            <div class="history-title">${item.params.novel_title}</div>
            <div class="history-time">${new Date(item.timestamp).toLocaleString('zh-CN')}</div>
            <div class="history-count">${item.images.length} 张图片</div>
        </div>
    `).join('');
}

// 加载历史记录项
function loadHistoryItem(id) {
    const historyItem = generationHistory.find(item => item.id == id);
    if (!historyItem) return;
    
    // 恢复表单参数
    document.getElementById('novel-title').value = historyItem.params.novel_title;
    document.getElementById('author-name').value = historyItem.params.author_name;
    document.getElementById('novel-genre').value = historyItem.params.genre;
    document.getElementById('cover-style').value = historyItem.params.style;
    document.getElementById('image-size').value = historyItem.params.image_size;
    document.getElementById('custom-prompt').value = historyItem.params.custom_prompt;
    document.getElementById('negative-prompt').value = historyItem.params.negative_prompt;
    document.getElementById('add-watermark').checked = historyItem.params.add_watermark;
    document.getElementById('generation-count').value = historyItem.params.generation_count;
    
    // 显示历史图片
    displayGeneratedImages(historyItem.images);
    
    showNotification('已加载历史记录', 'success');
}

// 清空历史记录
function clearHistory() {
    if (confirm('确定要清空所有历史记录吗？')) {
        generationHistory = [];
        updateHistoryDisplay();
        showNotification('历史记录已清空', 'success');
    }
}

// 加载生成历史（从localStorage）
function loadGenerationHistory() {
    try {
        const saved = localStorage.getItem('cover-generation-history');
        if (saved) {
            generationHistory = JSON.parse(saved);
            updateHistoryDisplay();
        }
    } catch (error) {
        console.error('加载历史记录失败:', error);
    }
}

// 保存生成历史（到localStorage）
function saveGenerationHistory() {
    try {
        localStorage.setItem('cover-generation-history', JSON.stringify(generationHistory));
    } catch (error) {
        console.error('保存历史记录失败:', error);
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    // 移除现有通知
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建新通知
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // 添加样式
    const styles = {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '8px',
        fontSize: '14px',
        fontWeight: '600',
        zIndex: '10000',
        animation: 'slideInRight 0.3s ease-out',
        maxWidth: '300px',
        wordWrap: 'break-word'
    };
    
    // 根据类型设置颜色
    const colors = {
        success: { bg: '#10b981', color: 'white' },
        error: { bg: '#ef4444', color: 'white' },
        warning: { bg: '#f59e0b', color: 'white' },
        info: { bg: '#3b82f6', color: 'white' }
    };
    
    const color = colors[type] || colors.info;
    Object.assign(styles, {
        backgroundColor: color.bg,
        color: color.color
    });
    
    Object.assign(notification.style, styles);
    
    document.body.appendChild(notification);
    
    // 自动移除
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// 添加通知动画样式
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(notificationStyles);

// 页面卸载时保存历史记录
window.addEventListener('beforeunload', saveGenerationHistory);

// 导出函数供HTML调用
window.loadTemplate = loadTemplate;
window.generateCover = generateCover;
window.regenerateCover = generateCover;
window.clearPreview = clearPreview;
window.selectAll = selectAll;
window.deselectAll = deselectAll;
window.downloadSelected = downloadSelected;
window.showImageModal = showImageModal;
window.closeImageModal = closeImageModal;
window.downloadModalImage = downloadModalImage;
window.loadHistoryItem = loadHistoryItem;
window.clearHistory = clearHistory;