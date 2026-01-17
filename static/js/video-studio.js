/**
 * 视频工作室 JavaScript
 * 管理视频生成、素材库访问和页面交互
 */

// 全局变量
let currentMode = 'reference'; // reference 或 frame
let selectedRatio = '16:9';

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePageSwitching();
    initializeUploadModeSwitch();
    initializeRatioButtons();
    initializeFileUpload();
    initializeVideoCards();
    initializeLibraryControls();
    initializeGenerateButton();
    initializeTemplateButtons();
});

/**
 * 页面切换功能
 */
function initializePageSwitching() {
    const workspaceTab = document.getElementById('workspaceTab');
    const libraryTab = document.getElementById('libraryTab');
    const workspacePage = document.getElementById('workspacePage');
    const libraryPage = document.getElementById('libraryPage');
    
    if (workspaceTab && libraryTab && workspacePage && libraryPage) {
        workspaceTab.addEventListener('click', (e) => {
            e.preventDefault();
            switchPage('workspace');
        });
        
        libraryTab.addEventListener('click', (e) => {
            e.preventDefault();
            switchPage('library');
        });
    }
}

function switchPage(page) {
    const workspaceTab = document.getElementById('workspaceTab');
    const libraryTab = document.getElementById('libraryTab');
    const workspacePage = document.getElementById('workspacePage');
    const libraryPage = document.getElementById('libraryPage');
    
    // 更新导航状态
    if (page === 'workspace') {
        workspaceTab.classList.add('active');
        libraryTab.classList.remove('active');
        workspacePage.classList.add('active');
        libraryPage.classList.remove('active');
    } else {
        workspaceTab.classList.remove('active');
        libraryTab.classList.add('active');
        workspacePage.classList.remove('active');
        libraryPage.classList.add('active');
        
        // 加载视频列表
        loadVideoLibrary();
    }
}

/**
 * 上传模式切换
 */
function initializeUploadModeSwitch() {
    const modeBtns = document.querySelectorAll('.mode-btn');
    const referenceMode = document.getElementById('referenceMode');
    const frameMode = document.getElementById('frameMode');
    
    modeBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const mode = btn.dataset.mode;
            currentMode = mode;
            
            // 更新按钮状态
            modeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // 切换模式显示
            if (mode === 'reference') {
                referenceMode.classList.add('active');
                frameMode.classList.remove('active');
            } else {
                referenceMode.classList.remove('active');
                frameMode.classList.add('active');
            }
        });
    });
}

/**
 * 比例按钮选择
 */
function initializeRatioButtons() {
    const ratioBtns = document.querySelectorAll('.ratio-btn');
    
    ratioBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            selectedRatio = btn.dataset.ratio;
            
            // 更新按钮状态
            ratioBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
}

/**
 * 文件上传功能
 */
function initializeFileUpload() {
    // 参考图上传
    const referenceUploadArea = document.getElementById('referenceUploadArea');
    const referenceImageInput = document.getElementById('referenceImageInput');
    const referencePlaceholder = document.getElementById('referencePlaceholder');
    const referencePreview = document.getElementById('referencePreview');
    const referencePreviewImg = document.getElementById('referencePreviewImg');
    const removeReferenceBtn = document.getElementById('removeReferenceBtn');
    
    if (referenceUploadArea && referenceImageInput) {
        referenceUploadArea.addEventListener('click', () => {
            referenceImageInput.click();
        });
        
        referenceImageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    referencePreviewImg.src = event.target.result;
                    referencePlaceholder.style.display = 'none';
                    referencePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
        
        if (removeReferenceBtn) {
            removeReferenceBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                referenceImageInput.value = '';
                referencePreviewImg.src = '';
                referencePlaceholder.style.display = 'flex';
                referencePreview.style.display = 'none';
            });
        }
    }
    
    // 首帧上传
    const firstFrameUploadArea = document.getElementById('firstFrameUploadArea');
    const firstFrameInput = document.getElementById('firstFrameInput');
    const firstFramePlaceholder = document.getElementById('firstFramePlaceholder');
    const firstFramePreview = document.getElementById('firstFramePreview');
    const firstFramePreviewImg = document.getElementById('firstFramePreviewImg');
    
    if (firstFrameUploadArea && firstFrameInput) {
        firstFrameUploadArea.addEventListener('click', () => {
            firstFrameInput.click();
        });
        
        firstFrameInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    firstFramePreviewImg.src = event.target.result;
                    firstFramePlaceholder.style.display = 'none';
                    firstFramePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
    
    // 尾帧上传
    const lastFrameUploadArea = document.getElementById('lastFrameUploadArea');
    const lastFrameInput = document.getElementById('lastFrameInput');
    const lastFramePlaceholder = document.getElementById('lastFramePlaceholder');
    const lastFramePreview = document.getElementById('lastFramePreview');
    const lastFramePreviewImg = document.getElementById('lastFramePreviewImg');
    
    if (lastFrameUploadArea && lastFrameInput) {
        lastFrameUploadArea.addEventListener('click', () => {
            lastFrameInput.click();
        });
        
        lastFrameInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    lastFramePreviewImg.src = event.target.result;
                    lastFramePlaceholder.style.display = 'none';
                    lastFramePreview.style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        });
    }
}

/**
 * 视频卡片功能
 */
function initializeVideoCards() {
    // 播放按钮
    document.querySelectorAll('.btn-play').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const url = btn.dataset.url;
            if (url) {
                // 打开全屏播放器
                openFullscreenPlayer(url);
            }
        });
    });
    
    // 下载按钮
    document.querySelectorAll('.btn-download').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const url = btn.dataset.url;
            if (url) {
                downloadVideo(url);
            }
        });
    });
    
    // 复用按钮
    document.querySelectorAll('.btn-reuse').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const prompt = btn.dataset.prompt;
            if (prompt) {
                // 切换到工作台并填充提示词
                switchPage('workspace');
                const promptEditor = document.getElementById('promptEditor');
                if (promptEditor) {
                    promptEditor.value = prompt;
                }
                showToast('提示词已加载到工作台');
            }
        });
    });
    
    // 删除按钮
    document.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const videoId = btn.dataset.id;
            if (videoId && confirm('确定要删除这个视频吗？')) {
                deleteVideo(videoId);
            }
        });
    });
}

/**
 * 素材库控制
 */
function initializeLibraryControls() {
    const refreshBtn = document.getElementById('refreshBtn');
    const searchInput = document.getElementById('searchInput');
    const statusFilter = document.getElementById('statusFilter');
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadVideoLibrary();
            showToast('素材库已刷新');
        });
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterVideos(e.target.value);
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            loadVideoLibrary();
        });
    }
}

/**
 * 生成按钮
 */
function initializeGenerateButton() {
    const generateBtn = document.getElementById('generateBtn');
    const copyPromptBtn = document.getElementById('copyPromptBtn');
    
    if (generateBtn) {
        generateBtn.addEventListener('click', generateVideo);
    }
    
    if (copyPromptBtn) {
        copyPromptBtn.addEventListener('click', copyPrompt);
    }
}

/**
 * 加载视频素材库
 */
async function loadVideoLibrary() {
    const videoLibrary = document.getElementById('videoLibrary');
    const libraryLoading = document.getElementById('libraryLoading');
    const libraryEmpty = document.getElementById('libraryEmpty');
    const statusFilter = document.getElementById('statusFilter');
    
    if (!videoLibrary) return;
    
    // 显示加载状态
    if (libraryLoading) libraryLoading.style.display = 'block';
    if (libraryEmpty) libraryEmpty.style.display = 'none';
    
    try {
        const status = statusFilter ? statusFilter.value : 'all';
        const response = await fetch(`/api/video/studio/library?status=${status}`);
        const data = await response.json();
        
        if (data.success && data.videos) {
            renderVideoCards(data.videos);
        } else {
            throw new Error(data.error || '加载失败');
        }
    } catch (error) {
        console.error('加载视频素材库失败:', error);
        if (libraryEmpty) libraryEmpty.style.display = 'block';
    } finally {
        if (libraryLoading) libraryLoading.style.display = 'none';
    }
}

/**
 * 渲染视频卡片
 */
function renderVideoCards(videos) {
    const videoList = document.getElementById('videoList');
    const libraryEmpty = document.getElementById('libraryEmpty');
    
    if (!videoList) return;
    
    if (!videos || videos.length === 0) {
        if (libraryEmpty) libraryEmpty.style.display = 'block';
        videoList.innerHTML = '';
        return;
    }
    
    if (libraryEmpty) libraryEmpty.style.display = 'none';
    
    videoList.innerHTML = videos.map(video => {
        const statusClass = video.status === 'completed' ? 'status-completed' : 'status-failed';
        const statusText = video.status === 'completed' ? '已完成' : '失败';
        
        let previewHtml = '';
        if (video.status === 'completed' && video.url) {
            previewHtml = `
                <video src="${video.url}" preload="metadata" class="video-thumbnail"></video>
                <div class="video-overlay">
                    <button class="btn-play" data-url="${video.url}">▶</button>
                </div>
            `;
        } else {
            previewHtml = `
                <div class="video-placeholder">
                    <span class="placeholder-icon">🎬</span>
                    <span class="placeholder-status">${statusText}</span>
                </div>
            `;
        }
        
        let actionsHtml = '';
        if (video.status === 'completed') {
            actionsHtml = `
                <button class="btn-card-action btn-download" data-url="${video.url}" title="下载视频">📥 下载</button>
                <button class="btn-card-action btn-reuse" data-prompt="${escapeHtml(video.prompt)}" title="重新使用">🔄 复用</button>
            `;
        }
        actionsHtml += `<button class="btn-card-action btn-delete" data-id="${video.id}" title="删除">🗑️ 删除</button>`;
        
        return `
            <div class="video-card" data-video-id="${video.id}" data-status="${video.status}">
                <div class="video-card-preview">
                    ${previewHtml}
                    <span class="video-status ${statusClass}">${statusText}</span>
                </div>
                <div class="video-card-info">
                    <p class="video-prompt" title="${escapeHtml(video.prompt)}">${escapeHtml(video.prompt)}</p>
                    <div class="video-meta">
                        <span class="video-date">${video.date || ''}</span>
                        <span class="video-progress">${video.progress || 0}%</span>
                    </div>
                </div>
                <div class="video-card-actions">
                    ${actionsHtml}
                </div>
            </div>
        `;
    }).join('');
    
    // 重新绑定事件
    initializeVideoCards();
}

/**
 * 生成视频
 */
async function generateVideo() {
    const promptEditor = document.getElementById('promptEditor');
    const prompt = promptEditor ? promptEditor.value.trim() : '';
    
    if (!prompt) {
        showToast('请输入生成提示词');
        return;
    }
    
    const progressCard = document.getElementById('progressCard');
    const resultCard = document.getElementById('resultCard');
    const generateBtn = document.getElementById('generateBtn');
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressDetail = document.getElementById('progressDetail');
    
    progressCard.style.display = 'block';
    resultCard.style.display = 'none';
    generateBtn.disabled = true;
    
    // 重置进度
    if (progressFill) progressFill.style.width = '0%';
    if (progressPercent) progressPercent.textContent = '0%';
    if (progressDetail) progressDetail.textContent = '准备中...';
    
    try {
        // 收集图片数据
        const images = [];
        
        // 参考图模式
        if (currentMode === 'reference') {
            const referencePreviewImg = document.getElementById('referencePreviewImg');
            if (referencePreviewImg && referencePreviewImg.src && referencePreviewImg.style.display !== 'none') {
                // 如果是base64图片数据
                if (referencePreviewImg.src.startsWith('data:')) {
                    // 移除data:image/xxx;base64,前缀
                    const base64Data = referencePreviewImg.src.split(',')[1];
                    images.push(base64Data);
                } else {
                    // 如果是URL，直接使用
                    images.push(referencePreviewImg.src);
                }
            }
        } else {
            // 首尾帧模式
            const firstFramePreviewImg = document.getElementById('firstFramePreviewImg');
            const lastFramePreviewImg = document.getElementById('lastFramePreviewImg');
            
            if (firstFramePreviewImg && firstFramePreviewImg.src && firstFramePreviewImg.style.display !== 'none') {
                if (firstFramePreviewImg.src.startsWith('data:')) {
                    images.push(firstFramePreviewImg.src.split(',')[1]);
                } else {
                    images.push(firstFramePreviewImg.src);
                }
            }
            
            if (lastFramePreviewImg && lastFramePreviewImg.src && lastFramePreviewImg.style.display !== 'none') {
                if (lastFramePreviewImg.src.startsWith('data:')) {
                    images.push(lastFramePreviewImg.src.split(',')[1]);
                } else {
                    images.push(lastFramePreviewImg.src);
                }
            }
        }
        
        // 根据比例选择方向
        const orientationMap = {
            '9:16': 'portrait',
            '16:9': 'landscape',
            '1:1': 'square',
            '4:3': 'landscape'
        };
        
        // 使用VeO API端点
        const response = await fetch('/api/veo/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                mode: currentMode,  // reference 或 frame
                images: images.length > 0 ? images : undefined,
                orientation: orientationMap[selectedRatio] || 'portrait',
                size: 'large'
            })
        });
        
        const result = await response.json();
        
        if (result.id) {
            // 轮询任务状态
            await pollVideoGeneration(result.id);
        } else {
            throw new Error(result.error?.message || '生成失败');
        }
    } catch (error) {
        console.error('生成视频失败:', error);
        showToast(`生成失败: ${error.message || '未知错误'}`);
        progressCard.style.display = 'none';
    } finally {
        generateBtn.disabled = false;
    }
}

/**
 * 轮询视频生成状态
 */
async function pollVideoGeneration(generationId) {
    const progressFill = document.getElementById('progressFill');
    const progressPercent = document.getElementById('progressPercent');
    const progressDetail = document.getElementById('progressDetail');
    
    const maxAttempts = 120; // 最多轮询2分钟
    let attempts = 0;
    
    const pollInterval = setInterval(async () => {
        attempts++;
        
        try {
            const response = await fetch(`/api/veo/status/${generationId}`);
            const result = await response.json();
            
            if (result.id && result.status) {
                const status = result.status;
                let progress = 0;
                
                // 更新进度
                switch(status) {
                    case 'pending':
                        progress = 10;
                        if (progressDetail) progressDetail.textContent = '等待中...';
                        break;
                    case 'processing':
                        progress = 50;
                        if (progressDetail) progressDetail.textContent = '生成中...';
                        break;
                    case 'succeeded':
                        progress = 100;
                        if (progressDetail) progressDetail.textContent = '完成！';
                        break;
                    case 'failed':
                        progress = 0;
                        if (progressDetail) progressDetail.textContent = '失败';
                        break;
                }
                
                if (progressFill) progressFill.style.width = `${progress}%`;
                if (progressPercent) progressPercent.textContent = `${progress}%`;
                
                // 检查是否完成
                if (status === 'succeeded' && result.result && result.result.videos && result.result.videos.length > 0) {
                    clearInterval(pollInterval);
                    
                    // 显示结果
                    const resultVideo = document.getElementById('resultVideo');
                    if (resultVideo) {
                        resultVideo.src = result.result.videos[0].url;
                    }
                    
                    document.getElementById('progressCard').style.display = 'none';
                    document.getElementById('resultCard').style.display = 'block';
                    
                    showToast('视频生成成功！');
                    
                } else if (status === 'failed') {
                    clearInterval(pollInterval);
                    document.getElementById('progressCard').style.display = 'none';
                    showToast('视频生成失败，请重试');
                } else if (attempts >= maxAttempts) {
                    clearInterval(pollInterval);
                    document.getElementById('progressCard').style.display = 'none';
                    showToast('生成超时，请稍后在素材库中查看');
                }
            } else {
                throw new Error(result.error?.message || '获取状态失败');
            }
        } catch (error) {
            console.error('轮询状态失败:', error);
            clearInterval(pollInterval);
            document.getElementById('progressCard').style.display = 'none';
            showToast('获取状态失败，请稍后在素材库中查看');
        }
    }, 1000);
}

/**
 * 复制提示词
 */
function copyPrompt() {
    const promptEditor = document.getElementById('promptEditor');
    const prompt = promptEditor ? promptEditor.value : '';
    
    if (!prompt) {
        showToast('没有可复制的提示词');
        return;
    }
    
    navigator.clipboard.writeText(prompt).then(() => {
        showToast('提示词已复制到剪贴板');
    }).catch(() => {
        showToast('复制失败，请手动复制');
    });
}

/**
 * 打开全屏播放器
 */
function openFullscreenPlayer(url) {
    const fullscreenPlayer = document.getElementById('fullscreenPlayer');
    const fullscreenVideo = document.getElementById('fullscreenVideo');
    const closeFullscreenBtn = document.getElementById('closeFullscreenBtn');
    
    if (fullscreenPlayer && fullscreenVideo) {
        fullscreenVideo.src = url;
        fullscreenPlayer.style.display = 'block';
        
        if (closeFullscreenBtn) {
            closeFullscreenBtn.onclick = () => {
                fullscreenVideo.pause();
                fullscreenPlayer.style.display = 'none';
                fullscreenVideo.src = '';
            };
        }
    }
}

/**
 * 下载视频
 */
function downloadVideo(url) {
    const link = document.createElement('a');
    link.href = url;
    link.download = `video_${Date.now()}.mp4`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('视频下载已开始');
}

/**
 * 删除视频
 */
async function deleteVideo(videoId) {
    try {
        const response = await fetch(`/api/video/studio/delete/${videoId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('视频已删除');
            loadVideoLibrary();
        } else {
            throw new Error(result.error || '删除失败');
        }
    } catch (error) {
        console.error('删除视频失败:', error);
        showToast(`删除失败: ${error.message || '未知错误'}`);
    }
}

/**
 * 过滤视频
 */
function filterVideos(searchTerm) {
    const videoCards = document.querySelectorAll('.video-card');
    
    videoCards.forEach(card => {
        const prompt = card.querySelector('.video-prompt');
        if (prompt) {
            const text = prompt.textContent.toLowerCase();
            const matches = text.includes(searchTerm.toLowerCase());
            card.style.display = matches ? 'block' : 'none';
        }
    });
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 快速模板功能
 */
function initializeTemplateButtons() {
    const templateBtns = document.querySelectorAll('.template-btn');
    
    templateBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const template = btn.dataset.template;
            applyTemplate(template);
        });
    });
}

/**
 * 应用快速模板
 */
function applyTemplate(template) {
    const templates = {
        'xianxia': '仙侠修真风格：一位剑仙在云端修行的场景，使用水墨画风，背景是壮观的云海和山峦，仙气缭绕。镜头从高空俯瞰山脉，展现大自然的壮美。使用写实风格，光影效果真实自然，色彩清新自然，营造出宁静祥和的氛围。',
        'modern': '现代都市风格：繁华的城市夜景，霓虹灯闪烁，高楼大厦林立。主角走在繁华的商业街上，镜头展示城市的现代化和活力。',
        'scifi': '科幻未来风格：未来的太空站内部，高科技设备遍布。透过巨大的舷窗可以看到遥远的星球和星云，展现出科技的进步和探索的精神。',
        'fantasy': '奇幻魔法风格：神秘的魔法森林，巨大的古树散发着微光。魔法生物在林间穿梭，空气中漂浮着魔法粒子，营造出梦幻般的氛围。',
        'nature': '自然风光风格：壮丽的自然风光，高山流水，云雾缭绕。镜头从高空俯瞰山脉，展现大自然的壮美。使用写实风格，光影效果真实自然，色彩清新自然，营造出宁静祥和的氛围。'
    };
    
    const promptEditor = document.getElementById('promptEditor');
    if (promptEditor && templates[template]) {
        // 清空现有提示词并应用新模板
        promptEditor.value = templates[template];
        showToast(`已应用${template}模板`);
    }
}

/**
 * 显示Toast通知
 */
function showToast(message) {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.className = 'toast show';
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}
