/**
 * 视频工作室 - 专注于视频生成
 * 支持自定义提示词和多种视频配置
 * 支持参考图、首帧、尾图上传
 */

class VideoStudio {
    constructor() {
        this.generatedVideoUrl = null;
        this.selectedRatio = '16:9';
        this.uploadMode = 'reference'; // reference 或 frame
        this.referenceImageBase64 = null;
        this.firstFrameBase64 = null;
        this.lastFrameBase64 = null;
        this.videoLibrary = []; // 存储视频列表
        this.currentFilter = 'all';
        
        this.init();
    }
    
    init() {
        console.log('🎬 视频工作室初始化...');
        this.bindEvents();
        this.loadVideoLibrary(); // 加载素材库
        console.log('✅ 初始化完成');
    }
    
    bindEvents() {
        // 提示词操作
        document.getElementById('copyPromptBtn')?.addEventListener('click', () => {
            this.copyPrompt();
        });
        
        // 上传模式切换
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchUploadMode(btn.dataset.mode);
            });
        });
        
        // 参考图上传
        const referenceUploadArea = document.getElementById('referenceUploadArea');
        const referenceInput = document.getElementById('referenceImageInput');
        
        referenceUploadArea?.addEventListener('click', (e) => {
            if (e.target.closest('.remove-image-btn')) return;
            referenceInput.click();
        });
        
        referenceUploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            referenceUploadArea.classList.add('dragover');
        });
        
        referenceUploadArea?.addEventListener('dragleave', () => {
            referenceUploadArea.classList.remove('dragover');
        });
        
        referenceUploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            referenceUploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                this.handleReferenceImageUpload(file);
            }
        });
        
        referenceInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleReferenceImageUpload(file);
            }
        });
        
        document.getElementById('removeReferenceBtn')?.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removeReferenceImage();
        });
        
        // 首帧上传
        const firstFrameUploadArea = document.getElementById('firstFrameUploadArea');
        const firstFrameInput = document.getElementById('firstFrameInput');
        
        firstFrameUploadArea?.addEventListener('click', (e) => {
            if (e.target.closest('.remove-image-btn')) return;
            firstFrameInput.click();
        });
        
        firstFrameUploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            firstFrameUploadArea.classList.add('dragover');
        });
        
        firstFrameUploadArea?.addEventListener('dragleave', () => {
            firstFrameUploadArea.classList.remove('dragover');
        });
        
        firstFrameUploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            firstFrameUploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                this.handleFirstFrameUpload(file);
            }
        });
        
        firstFrameInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleFirstFrameUpload(file);
            }
        });
        
        firstFrameUploadArea?.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-image-btn') && e.target.dataset.type === 'first') {
                e.stopPropagation();
                this.removeFirstFrame();
            }
        });
        
        // 尾帧上传
        const lastFrameUploadArea = document.getElementById('lastFrameUploadArea');
        const lastFrameInput = document.getElementById('lastFrameInput');
        
        lastFrameUploadArea?.addEventListener('click', (e) => {
            if (e.target.closest('.remove-image-btn')) return;
            lastFrameInput.click();
        });
        
        lastFrameUploadArea?.addEventListener('dragover', (e) => {
            e.preventDefault();
            lastFrameUploadArea.classList.add('dragover');
        });
        
        lastFrameUploadArea?.addEventListener('dragleave', () => {
            lastFrameUploadArea.classList.remove('dragover');
        });
        
        lastFrameUploadArea?.addEventListener('drop', (e) => {
            e.preventDefault();
            lastFrameUploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file && file.type.startsWith('image/')) {
                this.handleLastFrameUpload(file);
            }
        });
        
        lastFrameInput?.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.handleLastFrameUpload(file);
            }
        });
        
        lastFrameUploadArea?.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-image-btn') && e.target.dataset.type === 'last') {
                e.stopPropagation();
                this.removeLastFrame();
            }
        });
        
        // 比例选择
        document.querySelectorAll('.ratio-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.ratio-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.selectedRatio = btn.dataset.ratio;
            });
        });
        
        // 生成按钮
        document.getElementById('generateBtn')?.addEventListener('click', () => {
            this.generateVideo();
        });
        
        // 结果操作
        document.getElementById('downloadResultBtn')?.addEventListener('click', () => {
            this.downloadResult();
        });
        
        document.getElementById('regenerateBtn')?.addEventListener('click', () => {
            this.generateVideo();
        });
        
        // 全屏播放按钮
        document.getElementById('fullscreenBtn')?.addEventListener('click', () => {
            this.openFullscreen();
        });
        
        // 关闭全屏按钮
        document.getElementById('closeFullscreenBtn')?.addEventListener('click', () => {
            this.closeFullscreen();
        });
        
        // 点击视频包装器也可以全屏
        document.querySelector('.video-wrapper')?.addEventListener('click', (e) => {
            if (e.target.closest('.fullscreen-btn')) return;
            this.openFullscreen();
        });
        
        // ESC键关闭全屏
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFullscreen();
            }
        });
        
        // 模板按钮
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyTemplate(btn.dataset.template);
            });
        });
        
        // 页面切换
        document.getElementById('workspaceTab')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchPage('workspace');
        });
        
        document.getElementById('libraryTab')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.switchPage('library');
        });
        
        // 素材库筛选
        document.getElementById('statusFilter')?.addEventListener('change', (e) => {
            this.currentFilter = e.target.value;
            this.renderVideoLibrary();
        });
        
        // 素材库搜索
        document.getElementById('searchInput')?.addEventListener('input', (e) => {
            this.renderVideoLibrary();
        });
        
        // 刷新按钮
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.loadVideoLibrary();
        });
    }
    
    switchPage(pageName) {
        // 更新导航状态
        document.querySelectorAll('.nav-link[data-page]').forEach(link => {
            link.classList.remove('active');
            if (link.dataset.page === pageName) {
                link.classList.add('active');
            }
        });
        
        // 切换页面显示
        document.querySelectorAll('.page').forEach(page => {
            page.classList.remove('active');
        });
        
        document.getElementById(`${pageName}Page`).classList.add('active');
        
        // 如果切换到素材库，刷新数据
        if (pageName === 'library') {
            this.loadVideoLibrary();
        }
    }
    
    async loadVideoLibrary() {
        console.log('📁 加载视频素材库...');
        
        const loadingEl = document.getElementById('libraryLoading');
        const emptyEl = document.getElementById('libraryEmpty');
        const listEl = document.getElementById('videoList');
        
        if (loadingEl) loadingEl.style.display = 'block';
        if (emptyEl) emptyEl.style.display = 'none';
        if (listEl) listEl.innerHTML = '';
        
        try {
            const response = await fetch('/api/veo/tasks?limit=50&order=desc');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.data && Array.isArray(data.data)) {
                this.videoLibrary = data.data;
                console.log(`✅ 加载了 ${this.videoLibrary.length} 个视频`);
            } else {
                this.videoLibrary = [];
            }
            
            this.renderVideoLibrary();
            
        } catch (error) {
            console.error('❌ 加载素材库失败:', error);
            this.showToast('加载素材库失败: ' + error.message, 'error');
            if (loadingEl) loadingEl.style.display = 'none';
            if (emptyEl) {
                emptyEl.style.display = 'block';
                emptyEl.querySelector('p').textContent = '加载失败，请稍后重试';
            }
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
        }
    }
    
    renderVideoLibrary() {
        const listEl = document.getElementById('videoList');
        const emptyEl = document.getElementById('libraryEmpty');
        const searchText = document.getElementById('searchInput')?.value.toLowerCase() || '';
        
        if (!listEl) return;
        
        // 筛选视频
        let filteredVideos = this.videoLibrary.filter(video => {
            // 状态筛选
            if (this.currentFilter !== 'all' && video.status !== this.currentFilter) {
                return false;
            }
            
            // 搜索筛选
            if (searchText) {
                const prompt = (video.prompt || '').toLowerCase();
                if (!prompt.includes(searchText)) {
                    return false;
                }
            }
            
            return true;
        });
        
        // 显示/隐藏空状态
        if (filteredVideos.length === 0) {
            if (emptyEl) {
                emptyEl.style.display = 'block';
                if (this.videoLibrary.length === 0) {
                    emptyEl.querySelector('p').textContent = '暂无视频素材';
                    emptyEl.querySelector('.empty-hint').style.display = 'block';
                } else {
                    emptyEl.querySelector('p').textContent = '没有符合条件的视频';
                    emptyEl.querySelector('.empty-hint').style.display = 'none';
                }
            }
            listEl.innerHTML = '';
            return;
        }
        
        if (emptyEl) emptyEl.style.display = 'none';
        
        // 渲染视频列表
        listEl.innerHTML = filteredVideos.map(video => this.renderVideoCard(video)).join('');
        
        // 绑定视频卡片事件
        this.bindVideoCardEvents();
    }
    
    renderVideoCard(video) {
        const status = video.status || 'pending';
        const statusText = {
            'pending': '等待中',
            'processing': '生成中',
            'completed': '已完成',
            'failed': '失败',
            'cancelled': '已取消'
        }[status] || status;
        
        const statusClass = {
            'pending': 'status-pending',
            'processing': 'status-processing',
            'completed': 'status-completed',
            'failed': 'status-failed',
            'cancelled': 'status-cancelled'
        }[status] || '';
        
        const createdAt = video.created ? new Date(video.created * 1000).toLocaleString('zh-CN') : '';
        const prompt = video.prompt || '无提示词';
        const truncatedPrompt = prompt.length > 100 ? prompt.substring(0, 100) + '...' : prompt;
        
        // 视频URL（如果已完成）
        const videoUrl = video.result?.videos?.[0]?.url || '';
        const thumbnailUrl = video.result?.videos?.[0]?.thumbnail_url || '';
        
        return `
            <div class="video-card" data-video-id="${video.id}" data-status="${status}">
                <div class="video-card-preview">
                    ${status === 'completed' && videoUrl ? `
                        <video src="${videoUrl}" preload="metadata" class="video-thumbnail"></video>
                        <div class="video-overlay">
                            <button class="btn-play" data-url="${videoUrl}">▶</button>
                        </div>
                    ` : `
                        <div class="video-placeholder">
                            <span class="placeholder-icon">🎬</span>
                            <span class="placeholder-status">${statusText}</span>
                        </div>
                    `}
                    <span class="video-status ${statusClass}">${statusText}</span>
                </div>
                <div class="video-card-info">
                    <p class="video-prompt" title="${this.escapeHtml(prompt)}">${this.escapeHtml(truncatedPrompt)}</p>
                    <div class="video-meta">
                        <span class="video-date">${createdAt}</span>
                        ${video.progress !== undefined ? `<span class="video-progress">${video.progress}%</span>` : ''}
                    </div>
                </div>
                <div class="video-card-actions">
                    ${status === 'completed' && videoUrl ? `
                        <button class="btn-card-action btn-download" data-url="${videoUrl}" title="下载视频">📥 下载</button>
                        <button class="btn-card-action btn-reuse" data-prompt="${this.escapeHtml(prompt)}" title="重新使用">🔄 复用</button>
                        <button class="btn-card-action btn-delete" data-id="${video.id}" title="删除">🗑️ 删除</button>
                    ` : status === 'processing' ? `
                        <button class="btn-card-action btn-refresh" data-id="${video.id}" title="刷新状态">🔄 刷新</button>
                    ` : `
                        <button class="btn-card-action btn-delete" data-id="${video.id}" title="删除">🗑️ 删除</button>
                    `}
                </div>
            </div>
        `;
    }
    
    bindVideoCardEvents() {
        console.log('🔗 绑定视频卡片事件...');
        
        // 播放按钮
        const playButtons = document.querySelectorAll('.btn-play');
        console.log(`🎯 找到 ${playButtons.length} 个播放按钮`);
        
        playButtons.forEach((btn, index) => {
            console.log(`📍 按钮 ${index} URL:`, btn.dataset.url);
            btn.addEventListener('click', (e) => {
                console.log('🖱️ 播放按钮被点击');
                e.stopPropagation();
                const url = btn.dataset.url;
                console.log('🔗 获取的URL:', url);
                this.openVideoPlayer(url);
            });
        });
        
        // 点击视频卡片播放
        const completedCards = document.querySelectorAll('.video-card[data-status="completed"]');
        console.log(`🎯 找到 ${completedCards.length} 个已完成视频卡片`);
        
        completedCards.forEach((card, index) => {
            card.addEventListener('click', () => {
                console.log(`🖱️ 视频卡片 ${index} 被点击`);
                const videoUrl = card.querySelector('.btn-play')?.dataset.url;
                console.log('🔗 卡片中的URL:', videoUrl);
                if (videoUrl) {
                    this.openVideoPlayer(videoUrl);
                } else {
                    console.error('❌ 视频卡片中没有找到播放按钮或URL');
                }
            });
        });
        
        console.log('✅ 视频卡片事件绑定完成');
        
        // 下载按钮
        document.querySelectorAll('.btn-download').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const url = btn.dataset.url;
                this.downloadVideo(url);
            });
        });
        
        // 复用按钮
        document.querySelectorAll('.btn-reuse').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const prompt = btn.dataset.prompt;
                document.getElementById('promptEditor').value = prompt;
                this.switchPage('workspace');
                this.showToast('提示词已复制到编辑器', 'success');
            });
        });
        
        // 刷新按钮（处理中的任务）
        document.querySelectorAll('.btn-refresh').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                this.refreshVideoStatus(id);
            });
        });
        
        // 删除按钮
        document.querySelectorAll('.btn-delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                this.deleteVideo(id);
            });
        });
    }
    
    openVideoPlayer(url) {
        console.log('🎬 打开视频播放器:', url);
        
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const fullscreenVideo = document.getElementById('fullscreenVideo');
        
        if (!fullscreenPlayer || !fullscreenVideo) {
            console.error('❌ 找不到全屏播放器元素');
            this.showToast('播放器初始化失败', 'error');
            return;
        }
        
        // 验证URL
        if (!url || url === '') {
            console.error('❌ 视频URL为空');
            this.showToast('视频URL无效', 'error');
            return;
        }
        
        console.log('✅ 设置视频源:', url);
        fullscreenVideo.src = url;
        
        // 🔥 关键修复：确保全屏播放器可见
        fullscreenPlayer.style.display = 'flex';
        fullscreenPlayer.style.zIndex = '9999';
        fullscreenPlayer.style.position = 'fixed';
        fullscreenPlayer.style.top = '0';
        fullscreenPlayer.style.left = '0';
        fullscreenPlayer.style.width = '100vw';
        fullscreenPlayer.style.height = '100vh';
        
        console.log('✅ 全屏播放器样式已设置');
        console.log('🎨 播放器display:', fullscreenPlayer.style.display);
        console.log('🎨 播放器zIndex:', fullscreenPlayer.style.zIndex);
        
        // 监听视频加载事件
        fullscreenVideo.addEventListener('loadstart', () => {
            console.log('📡 开始加载视频');
        });
        
        fullscreenVideo.addEventListener('canplay', () => {
            console.log('✅ 视频可以播放');
        });
        
        fullscreenVideo.addEventListener('error', (e) => {
            console.error('❌ 视频加载失败:', e);
            console.error('❌ 视频错误详情:', fullscreenVideo.error);
            this.showToast('视频加载失败，请检查URL', 'error');
        });
        
        // 尝试播放
        fullscreenVideo.play().then(() => {
            console.log('✅ 视频开始播放');
            console.log('🎬 播放器状态:', {
                display: fullscreenPlayer.style.display,
                zIndex: fullscreenPlayer.style.zIndex,
                videoSrc: fullscreenVideo.src
            });
        }).catch(e => {
            console.warn('⚠️ 自动播放失败，需要用户交互:', e);
            // 不显示错误，因为可能需要用户手动点击播放
        });
        
        document.body.style.overflow = 'hidden';
        console.log('✅ Body overflow已设置为hidden');
    }
    
    downloadVideo(url) {
        const link = document.createElement('a');
        link.href = url;
        link.download = `video_${Date.now()}.mp4`;
        link.target = '_blank';
        link.click();
        
        this.showToast('视频下载已开始', 'success');
    }
    
    async refreshVideoStatus(videoId) {
        try {
            const response = await fetch(`/api/veo/status/${videoId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            // 更新本地数据
            const index = this.videoLibrary.findIndex(v => v.id === videoId);
            if (index !== -1) {
                this.videoLibrary[index] = data;
            }
            
            this.renderVideoLibrary();
            this.showToast('状态已更新', 'success');
            
        } catch (error) {
            console.error('刷新状态失败:', error);
            this.showToast('刷新失败: ' + error.message, 'error');
        }
    }
    
    async deleteVideo(videoId) {
        if (!confirm('确定要删除这个视频吗？')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/veo/tasks/${videoId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                // 解析错误信息
                const errorData = await response.json();
                const errorMessage = errorData.error?.message || `HTTP ${response.status}`;
                throw new Error(errorMessage);
            }
            
            // 只有在成功时才从列表中移除
            this.videoLibrary = this.videoLibrary.filter(v => v.id !== videoId);
            this.renderVideoLibrary();
            this.showToast('视频已删除', 'success');
            
        } catch (error) {
            console.error('删除失败:', error);
            this.showToast('删除失败: ' + error.message, 'error');
            // 🔥 修复：删除失败时重新加载列表，确保前后端同步
            this.loadVideoLibrary();
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    switchUploadMode(mode) {
        this.uploadMode = mode;
        
        // 更新按钮状态
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.mode === mode) {
                btn.classList.add('active');
            }
        });
        
        // 切换内容显示
        document.querySelectorAll('.upload-mode-content').forEach(content => {
            content.classList.remove('active');
        });
        
        if (mode === 'reference') {
            document.getElementById('referenceMode').classList.add('active');
        } else if (mode === 'frame') {
            document.getElementById('frameMode').classList.add('active');
        }
        
        console.log(`切换到${mode === 'reference' ? '参考图' : '首尾帧'}模式`);
    }
    
    // 将文件转换为base64
    fileToBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => {
                // 移除data:image/xxx;base64,前缀，只保留base64数据
                const base64 = reader.result.split(',')[1];
                resolve(base64);
            };
            reader.onerror = error => reject(error);
            reader.readAsDataURL(file);
        });
    }
    
    // 处理参考图上传
    async handleReferenceImageUpload(file) {
        try {
            console.log('上传参考图:', file.name, file.type, file.size);
            
            // 验证文件类型
            if (!file.type.startsWith('image/')) {
                this.showToast('请上传图片文件', 'error');
                return;
            }
            
            // 验证文件大小（限制10MB）
            if (file.size > 10 * 1024 * 1024) {
                this.showToast('图片大小不能超过10MB', 'error');
                return;
            }
            
            // 转换为base64
            this.referenceImageBase64 = await this.fileToBase64(file);
            console.log('参考图base64长度:', this.referenceImageBase64.length);
            
            // 显示预览
            const preview = document.getElementById('referencePreview');
            const placeholder = document.getElementById('referencePlaceholder');
            const img = document.getElementById('referencePreviewImg');
            
            img.src = `data:${file.type};base64,${this.referenceImageBase64}`;
            preview.style.display = 'flex';
            placeholder.style.display = 'none';
            
            this.showToast('参考图上传成功', 'success');
        } catch (error) {
            console.error('上传参考图失败:', error);
            this.showToast('上传失败: ' + error.message, 'error');
        }
    }
    
    // 移除参考图
    removeReferenceImage() {
        this.referenceImageBase64 = null;
        const preview = document.getElementById('referencePreview');
        const placeholder = document.getElementById('referencePlaceholder');
        const input = document.getElementById('referenceImageInput');
        
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        input.value = '';
        
        this.showToast('参考图已移除', 'success');
    }
    
    // 处理首帧上传
    async handleFirstFrameUpload(file) {
        try {
            console.log('上传首帧:', file.name, file.type, file.size);
            
            if (!file.type.startsWith('image/')) {
                this.showToast('请上传图片文件', 'error');
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) {
                this.showToast('图片大小不能超过10MB', 'error');
                return;
            }
            
            this.firstFrameBase64 = await this.fileToBase64(file);
            console.log('首帧base64长度:', this.firstFrameBase64.length);
            
            const preview = document.getElementById('firstFramePreview');
            const placeholder = document.getElementById('firstFramePlaceholder');
            const img = document.getElementById('firstFramePreviewImg');
            
            img.src = `data:${file.type};base64,${this.firstFrameBase64}`;
            preview.style.display = 'flex';
            placeholder.style.display = 'none';
            
            this.showToast('首帧上传成功', 'success');
        } catch (error) {
            console.error('上传首帧失败:', error);
            this.showToast('上传失败: ' + error.message, 'error');
        }
    }
    
    // 移除首帧
    removeFirstFrame() {
        this.firstFrameBase64 = null;
        const preview = document.getElementById('firstFramePreview');
        const placeholder = document.getElementById('firstFramePlaceholder');
        const input = document.getElementById('firstFrameInput');
        
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        input.value = '';
        
        this.showToast('首帧已移除', 'success');
    }
    
    // 处理尾帧上传
    async handleLastFrameUpload(file) {
        try {
            console.log('上传尾帧:', file.name, file.type, file.size);
            
            if (!file.type.startsWith('image/')) {
                this.showToast('请上传图片文件', 'error');
                return;
            }
            
            if (file.size > 10 * 1024 * 1024) {
                this.showToast('图片大小不能超过10MB', 'error');
                return;
            }
            
            this.lastFrameBase64 = await this.fileToBase64(file);
            console.log('尾帧base64长度:', this.lastFrameBase64.length);
            
            const preview = document.getElementById('lastFramePreview');
            const placeholder = document.getElementById('lastFramePlaceholder');
            const img = document.getElementById('lastFramePreviewImg');
            
            img.src = `data:${file.type};base64,${this.lastFrameBase64}`;
            preview.style.display = 'flex';
            placeholder.style.display = 'none';
            
            this.showToast('尾帧上传成功', 'success');
        } catch (error) {
            console.error('上传尾帧失败:', error);
            this.showToast('上传失败: ' + error.message, 'error');
        }
    }
    
    // 移除尾帧
    removeLastFrame() {
        this.lastFrameBase64 = null;
        const preview = document.getElementById('lastFramePreview');
        const placeholder = document.getElementById('lastFramePlaceholder');
        const input = document.getElementById('lastFrameInput');
        
        preview.style.display = 'none';
        placeholder.style.display = 'block';
        input.value = '';
        
        this.showToast('尾帧已移除', 'success');
    }
    
    applyTemplate(templateType) {
        const templates = {
            xianxia: '一位仙风道骨的剑仙在云端修行的场景，使用水墨画风，背景是壮观的云海和山峦，仙气缭绕。镜头从远处缓缓推进，展现剑仙的修炼姿态，周围云雾缭绕，仙鹤飞翔，营造出超凡脱俗的仙境氛围。',
            modern: '繁华都市夜景，霓虹灯闪烁，年轻的主角走在街道上，充满活力和希望。使用现代电影风格，镜头跟随主角移动，展现城市的繁华和现代感，背景音乐轻快愉悦。',
            scifi: '未来科技城市，高科技建筑林立，飞行器穿梭。主角身穿高科技战甲，站在城市高处俯瞰。使用赛博朋克风格，霓虹灯光和全息投影交织，营造出强烈的科技感和未来感。',
            fantasy: '神秘的魔法森林，古老的巨树参天，魔法光芒闪烁。魔法师施展强大的魔法咒语，周围元素环绕。使用奇幻魔法风格，镜头缓缓旋转展现魔法效果，色彩丰富绚丽，充满神秘感。',
            nature: '壮丽的自然风光，高山流水，云雾缭绕。镜头从高空俯瞰山脉，展现大自然的壮美。使用写实风格，光影效果真实自然，色彩清新自然，营造出宁静祥和的氛围。'
        };
        
        const prompt = templates[templateType];
        if (prompt) {
            document.getElementById('promptEditor').value = prompt;
            this.showToast('已应用模板', 'success');
        }
    }
    
    copyPrompt() {
        const prompt = document.getElementById('promptEditor').value;
        if (!prompt) {
            this.showToast('提示词为空', 'error');
            return;
        }
        
        navigator.clipboard.writeText(prompt).then(() => {
            this.showToast('提示词已复制到剪贴板', 'success');
        }).catch(() => {
            this.showToast('复制失败', 'error');
        });
    }
    
    async generateVideo() {
        const prompt = document.getElementById('promptEditor').value.trim();
        
        if (!prompt) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        
        // VeO只支持10秒视频，60fps
        const duration = 10;
        const resolution = document.getElementById('resolutionSelect').value;
        const fps = 60;
        const style = document.getElementById('styleSelect').value;
        
        // 收集图片数据
        const images = [];
        
        if (this.uploadMode === 'reference' && this.referenceImageBase64) {
            images.push(this.referenceImageBase64);
            console.log('使用参考图模式');
        } else if (this.uploadMode === 'frame') {
            if (this.firstFrameBase64) {
                images.push(this.firstFrameBase64);
                console.log('添加首帧');
            }
            if (this.lastFrameBase64) {
                images.push(this.lastFrameBase64);
                console.log('添加尾帧');
            }
            if (images.length === 0) {
                this.showToast('请至少上传首帧或尾帧', 'error');
                return;
            }
            console.log('使用首尾帧模式');
        }
        
        // 显示进度
        document.getElementById('progressCard').style.display = 'block';
        document.getElementById('resultCard').style.display = 'none';
        document.getElementById('generateBtn').disabled = true;
        
        // 更新进度详情
        this.updateProgressDetail('正在初始化视频生成任务...');
        
        try {
            this.showToast('正在生成视频...', 'success');
            
            // 构建请求数据
            // 🔥 关键修复：不要在前端硬编码model，让后端根据mode自动选择
            const requestData = {
                prompt: prompt,
                images: images, // 使用base64数据
                orientation: this.selectedRatio === '16:9' ? 'landscape' : 'portrait',
                size: 'large',
                duration: parseInt(duration),
                watermark: false,
                private: true,
                mode: this.uploadMode  // 传递mode，让后端根据mode自动选择model
            };
            
            console.log('请求数据:', {
                ...requestData,
                images: `[${images.length}张图片，每张${images[0]?.length || 0}字符]`,
                mode: this.uploadMode,
                model: this.uploadMode === 'frame' ? 'veo_3_1-fl (后端自动选择)' : 'veo_3_1-fast (后端自动选择)'
            });
            
            this.updateProgressDetail('正在发送生成请求...');
            
            console.log('📊 请求数据:', {
                ...requestData,
                images: `[${images.length}张图片，每张${images[0]?.length || 0}字符]`,
                mode: this.uploadMode,
                model: this.uploadMode === 'frame' ? 'veo_3_1-fast-fl (首尾帧模式)' : 'veo_3_1-fast (参考图模式)'
            });
            
            // 调用VeO视频生成API
            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error.message || '生成失败');
            }
            
            // 获取生成任务ID
            const generationId = data.id;
            this.updateProgressDetail(`任务已创建 (ID: ${generationId})，正在生成中...`);
            
            // 轮询查询生成状态
            await this.pollGenerationStatus(generationId);
            
        } catch (error) {
            console.error('生成视频失败:', error);
            this.showToast('生成失败: ' + error.message, 'error');
            this.updateProgressDetail('生成失败: ' + error.message);
        } finally {
            document.getElementById('progressCard').style.display = 'none';
            document.getElementById('generateBtn').disabled = false;
        }
    }
    
    async pollGenerationStatus(generationId) {
        const maxAttempts = 120; // 最多轮询120次（4分钟）
        const pollInterval = 2000; // 每2秒轮询一次
        
        // 进度阶段映射
        const stageMessages = {
            'initializing': '正在初始化...',
            'preparing': '准备生成参数...',
            'sending': '发送生成请求...',
            'processing': 'AI正在生成视频...',
            'generating': '视频生成中...',
            'downloading': '正在下载视频...',
            'completed': '生成完成！'
        };
        
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const response = await fetch(`/api/veo/status/${generationId}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error.message || '查询失败');
                }
                
                const status = data.status;
                
                // 更新进度信息
                if (status === 'processing') {
                    // 获取后端返回的进度
                    const progress = data.progress || 0;
                    const stage = data.stage || 'processing';
                    
                    // 根据阶段获取友好的消息
                    let stageMessage = stageMessages[stage] || stageMessages['processing'];
                    if (stage.includes('生成进度')) {
                        stageMessage = `AI生成中: ${progress}%`;
                    }
                    
                    // 更新进度条和文本
                    this.updateProgress(progress, stageMessage);
                    
                } else if (status === 'completed') {
                    // 生成完成
                    this.updateProgress(100, '生成完成！');
                    this.showResult(data.result);
                    this.showToast('视频生成成功！', 'success');
                    return;
                } else if (status === 'failed') {
                    throw new Error(data.error?.message || '生成失败');
                } else if (status === 'cancelled') {
                    throw new Error('生成已取消');
                }
                
                // 继续轮询
                await new Promise(resolve => setTimeout(resolve, pollInterval));
                
            } catch (error) {
                console.error('轮询状态失败:', error);
                throw error;
            }
        }
        
        throw new Error('生成超时，请稍后查看任务状态');
    }
    
    updateProgress(progress, text) {
        // 更新进度条
        const progressFill = document.getElementById('progressFill');
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        
        // 更新百分比显示
        const progressPercent = document.getElementById('progressPercent');
        if (progressPercent) {
            progressPercent.textContent = `${progress}%`;
        }
        
        // 更新详细文本
        const detailElement = document.getElementById('progressDetail');
        if (detailElement) {
            detailElement.textContent = text;
        }
    }
    
    updateProgressDetail(text) {
        // 保持向后兼容
        this.updateProgress(0, text);
    }
    
    showResult(result) {
        console.log('🎬 显示视频结果:', result);
        
        // 显示结果卡片
        document.getElementById('resultCard').style.display = 'block';
        
        // 设置视频源
        const videoElement = document.getElementById('resultVideo');
        
        // API返回的数据结构是 result.videos[0].url
        if (result.videos && result.videos.length > 0) {
            const video = result.videos[0];
            this.generatedVideoUrl = video.url;
            videoElement.src = video.url;
            console.log('✅ 视频URL已设置:', video.url);
        } else if (result.video_url) {
            // 兼容旧格式
            videoElement.src = result.video_url;
            this.generatedVideoUrl = result.video_url;
            console.log('✅ 视频URL已设置(旧格式):', result.video_url);
        } else if (result.video_path) {
            // 如果是本地路径，需要转换为可访问的URL
            this.generatedVideoUrl = result.video_path;
            videoElement.src = result.video_path;
            console.log('✅ 视频路径已设置:', result.video_path);
        } else {
            console.error('❌ 无法找到视频URL，result结构:', result);
            this.showToast('无法获取视频URL', 'error');
            return;
        }
        
        // 自动播放视频
        videoElement.load();
        videoElement.play().catch(e => {
            console.log('⚠️ 自动播放失败:', e);
        });
    }
    
    downloadResult() {
        if (!this.generatedVideoUrl) {
            this.showToast('没有可下载的视频', 'error');
            return;
        }
        
        const link = document.createElement('a');
        link.href = this.generatedVideoUrl;
        link.download = `video_${Date.now()}.mp4`;
        link.target = '_blank';
        link.click();
        
        this.showToast('视频下载已开始', 'success');
    }
    
    openFullscreen() {
        if (!this.generatedVideoUrl) {
            this.showToast('没有可播放的视频', 'error');
            return;
        }
        
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const fullscreenVideo = document.getElementById('fullscreenVideo');
        
        // 设置全屏视频源
        fullscreenVideo.src = this.generatedVideoUrl;
        
        // 显示全屏播放器
        fullscreenPlayer.style.display = 'flex';
        
        // 播放视频
        fullscreenVideo.play().catch(e => {
            console.log('自动播放失败:', e);
        });
        
        // 阻止body滚动
        document.body.style.overflow = 'hidden';
    }
    
    closeFullscreen() {
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const fullscreenVideo = document.getElementById('fullscreenVideo');
        
        // 暂停视频
        fullscreenVideo.pause();
        
        // 隐藏全屏播放器
        fullscreenPlayer.style.display = 'none';
        
        // 恢复body滚动
        document.body.style.overflow = '';
    }
    
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const studio = new VideoStudio();
    window.videoStudio = studio;
});