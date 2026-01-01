/**
 * 视频生成系统 - 前端逻辑
 * 改进版：支持分步骤生成视频
 */

class VideoGenerator {
    constructor() {
        this.selectedNovel = null;
        this.selectedType = null;
        this.videoTypes = {};
        this.storyboard = null;
        this.currentPrompt = null;
        this.currentShot = null;
        this.shots = [];
        this.selectedMode = null; // 'custom' or 'novel'
        this.customPrompt = '';
        
        this.init();
    }
    
    async init() {
        console.log('🎬 视频生成系统初始化...');
        
        // 加载视频类型
        await this.loadVideoTypes();
        
        // 加载小说列表
        await this.loadNovels();
        
        // 绑定事件
        this.bindEvents();
        
        // 显示模式选择屏幕
        this.showModeSelectionScreen();
        
        console.log('✅ 初始化完成');
    }
    
    showModeSelectionScreen() {
        // 隐藏所有屏幕
        document.getElementById('modeSelectionScreen').style.display = 'block';
        document.getElementById('welcomeScreen').style.display = 'none';
        document.getElementById('customPromptScreen').style.display = 'none';
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('storyboardScreen').style.display = 'none';
        document.getElementById('shotGenerationScreen').style.display = 'none';
        
        // 隐藏左侧小说列表，使用CSS类
        document.querySelector('.main-container').classList.add('hide-sidebar');
        this.updateCurrentStatus('请选择生成模式');
    }
    
    selectMode(mode) {
        this.selectedMode = mode;
        console.log('🎯 选择模式:', mode);
        
        // 移除之前的选中状态
        document.querySelectorAll('.mode-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 添加新的选中状态
        const selectedCard = document.querySelector(`.mode-card[data-mode="${mode}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
        
        // 根据模式进入相应流程
        if (mode === 'custom') {
            this.showCustomPromptScreen();
        } else if (mode === 'novel') {
            this.showNovelSelectionScreen();
        }
    }
    
    showCustomPromptScreen() {
        document.getElementById('modeSelectionScreen').style.display = 'none';
        document.getElementById('customPromptScreen').style.display = 'block';
        this.updateCurrentStatus('自定义模式：输入提示词');
        
        // 隐藏左侧小说列表，使用CSS类
        document.querySelector('.main-container').classList.add('hide-sidebar');
        
        // 更新标题
        document.getElementById('customPromptTitle').textContent = '✨ 自定义模式 - 输入提示词';
    }
    
    showNovelSelectionScreen() {
        document.getElementById('modeSelectionScreen').style.display = 'none';
        document.getElementById('welcomeScreen').style.display = 'block';
        this.updateCurrentStatus('小说模式：选择小说和视频类型');
        
        // 显示左侧小说列表，使用CSS类
        document.querySelector('.main-container').classList.remove('hide-sidebar');
    }
    
    async loadVideoTypes() {
        try {
            const response = await fetch('/api/video/types');
            const data = await response.json();
            
            if (data.success) {
                this.videoTypes = data.video_types;
                this.renderVideoTypeSelector();
                this.renderTypeDescriptions();
            }
        } catch (error) {
            console.error('加载视频类型失败:', error);
            this.showToast('加载视频类型失败', 'error');
        }
    }
    
    async loadNovels() {
        try {
            // 使用新的API端点获取可用的小说
            const response = await fetch('/api/video/novels');
            const data = await response.json();
            
            if (data.success) {
                this.renderNovelList(data.novels);
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载小说列表失败:', error);
            this.showToast('加载小说列表失败: ' + error.message, 'error');
        }
    }
    
    renderVideoTypeSelector() {
        const container = document.getElementById('videoTypeSelector');
        container.innerHTML = '';
        
        const typeConfigs = {
            'short_film': {
                icon: '🎬',
                title: '短片/动画电影',
                duration: '3-10分钟',
                description: this.videoTypes.short_film?.description || '完整的短片故事',
                features: this.videoTypes.short_film?.characteristics || []
            },
            'long_series': {
                icon: '📺',
                title: '长篇剧集',
                duration: '1-5分钟/集',
                description: this.videoTypes.long_series?.description || '连续剧集形式',
                features: this.videoTypes.long_series?.characteristics || []
            },
            'short_video': {
                icon: '📱',
                title: '短视频系列',
                duration: '30秒-1分钟',
                description: this.videoTypes.short_video?.description || '竖屏短视频',
                features: this.videoTypes.short_video?.characteristics || []
            }
        };
        
        Object.entries(typeConfigs).forEach(([type, config]) => {
            const card = document.createElement('div');
            card.className = 'type-card';
            card.dataset.type = type;
            
            card.innerHTML = `
                <div class="type-icon">${config.icon}</div>
                <h3>${config.title}</h3>
                <span class="duration">${config.duration}</span>
                <p>${config.description}</p>
                <ul class="type-features">
                    ${config.features.map(f => `<li>${f}</li>`).join('')}
                </ul>
            `;
            
            card.addEventListener('click', () => this.selectType(type));
            container.appendChild(card);
        });
    }
    
    renderTypeDescriptions() {
        const container = document.getElementById('typeDescriptions');
        container.innerHTML = '';
        
        Object.entries(this.videoTypes).forEach(([type, info]) => {
            const item = document.createElement('div');
            item.className = 'type-desc-item';
            item.innerHTML = `
                <h4>${info.name}</h4>
                <p>${info.description}</p>
            `;
            container.appendChild(item);
        });
    }
    
    renderNovelList(novels) {
        const container = document.getElementById('novelList');
        
        if (novels.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无可用小说</p>
                    <p class="hint">请先完成第一阶段设定生成</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = novels.map(novel => {
            // 检查是否是新格式数据（包含video_ready字段）
            const isNewFormat = novel.video_ready === true;
            
            if (isNewFormat) {
                // 新格式：显示中级事件信息
                return `
                    <div class="novel-item video-ready" data-title="${novel.title || novel.novel_title}">
                        <div class="novel-header">
                            <div class="novel-title">${novel.title || novel.novel_title}</div>
                            <span class="video-ready-badge">✅ 可生成</span>
                        </div>
                        <div class="novel-stats">
                            <span class="stat-item">
                                <span class="stat-label">📊 中级事件:</span>
                                <span class="stat-value">${novel.total_medium_events || 0}个</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-label">🎬 预计分集:</span>
                                <span class="stat-value">${novel.estimated_episodes || 0}集</span>
                            </span>
                            <span class="stat-item">
                                <span class="stat-label">⏱️ 总时长:</span>
                                <span class="stat-value">${novel.total_duration_minutes || 0}分钟</span>
                            </span>
                        </div>
                    </div>
                `;
            } else {
                // 旧格式：使用章节数信息
                return `
                    <div class="novel-item" data-title="${novel.title}" data-chapters="${novel.total_chapters}">
                        <div class="novel-title">${novel.title}</div>
                        <div class="novel-info">
                            ${novel.total_chapters}章 |
                            ${novel.completed_chapters}/${novel.total_chapters} 已完成
                        </div>
                    </div>
                `;
            }
        }).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.novel-item').forEach(item => {
            item.addEventListener('click', () => {
                this.selectNovel(item.dataset.title);
            });
        });
    }
    
    selectNovel(title) {
        // 移除之前的选中状态
        document.querySelectorAll('.novel-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // 添加新的选中状态
        const selectedItem = document.querySelector(`.novel-item[data-title="${title}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }
        
        this.selectedNovel = title;
        console.log('📚 选中小说:', title);
        
        // 更新状态显示
        this.updateCurrentStatus(`已选择小说: ${title}<br>请选择视频类型`);
        
        // 高亮第一步
        this.highlightWorkflowStep(1);
    }
    
    selectType(type) {
        // 移除之前的选中状态
        document.querySelectorAll('.type-card').forEach(card => {
            card.classList.remove('selected');
        });
        
        // 添加新的选中状态
        const selectedCard = document.querySelector(`.type-card[data-type="${type}"]`);
        if (selectedCard) {
            selectedCard.classList.add('selected');
        }
        
        this.selectedType = type;
        console.log('🎬 选中类型:', type);
        
        // 生成提示词并进入下一步
        this.generatePrompt();
    }
    
    async generatePrompt() {
        try {
            this.showToast('正在生成提示词...', 'success');
            
            const response = await fetch('/api/video/generate-prompt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    video_type: this.selectedType
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentPrompt = data.prompt;
                this.showPromptPreview();
            } else {
                throw new Error(data.error || '生成提示词失败');
            }
        } catch (error) {
            console.error('生成提示词失败:', error);
            this.showToast('生成提示词失败: ' + error.message, 'error');
        }
    }
    
    showPromptPreview() {
        // 隐藏欢迎屏幕，显示提示词预览
        document.getElementById('welcomeScreen').style.display = 'none';
        document.getElementById('promptPreviewScreen').style.display = 'block';
        
        // 更新标题
        const typeName = this.videoTypes[this.selectedType].name;
        document.getElementById('promptPreviewTitle').textContent = 
            `${this.selectedNovel} - ${typeName}`;
        
        // 显示提示词
        document.getElementById('promptText').textContent = this.currentPrompt || '正在生成...';
        
        // 更新状态
        this.updateCurrentStatus(`已选择: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 查看提示词`);
        
        // 高亮第二步
        this.highlightWorkflowStep(2);
    }
    
    async generateStoryboard() {
        try {
            this.showToast('正在生成分镜头脚本...', 'success');
            
            const response = await fetch('/api/video/generate-storyboard', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    video_type: this.selectedType,
                    prompt: this.currentPrompt
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.storyboard = data.storyboard;
                this.shots = data.shots || [];
                this.showStoryboardScreen();
            } else {
                throw new Error(data.error || '生成分镜头失败');
            }
        } catch (error) {
            console.error('生成分镜头失败:', error);
            this.showToast('生成分镜头失败: ' + error.message, 'error');
        }
    }
    
    showStoryboardScreen() {
        // 隐藏提示词预览，显示分镜头列表
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('customPromptScreen').style.display = 'none';
        document.getElementById('storyboardScreen').style.display = 'block';
        
        // 更新标题和统计
        const typeName = this.videoTypes[this.selectedType].name;
        let titleText = '';
        
        if (this.selectedMode === 'custom') {
            titleText = `✨ 自定义视频 - ${typeName}`;
        } else {
            titleText = `${this.selectedNovel} - ${typeName}`;
        }
        
        document.getElementById('storyboardTitle').textContent = titleText;
        
        document.getElementById('totalShots').textContent = this.shots.length;
        document.getElementById('completedShots').textContent = '0';
        
        // 计算总时长
        const totalDuration = this.shots.reduce((sum, shot) => 
            sum + (shot.duration_seconds || 5), 0);
        document.getElementById('estimatedDuration').textContent = 
            `${Math.round(totalDuration / 60)}分钟`;
        
        // 渲染镜头列表
        this.renderShotsList();
        
        // 更新状态
        this.updateCurrentStatus(`已生成 ${this.shots.length} 个分镜头<br>可逐个或批量生成`);
        
        // 高亮第三步
        this.highlightWorkflowStep(3);
    }
    
    renderShotsList() {
        const container = document.getElementById('shotsList');
        container.innerHTML = '';
        
        this.shots.forEach((shot, index) => {
            const shotCard = document.createElement('div');
            shotCard.className = 'shot-card';
            shotCard.dataset.index = index;
            
            const statusClass = shot.status === 'completed' ? 'completed' : 
                               shot.status === 'generating' ? 'generating' : 'pending';
            
            shotCard.innerHTML = `
                <div class="shot-card-header">
                    <div class="shot-number">镜头 #${index + 1}</div>
                    <div class="shot-status ${statusClass}">
                        ${this.getStatusText(shot.status)}
                    </div>
                </div>
                <div class="shot-card-body">
                    <p class="shot-scene">${shot.scene_description || '暂无描述'}</p>
                    <div class="shot-meta">
                        <span class="meta-item">⏱️ ${shot.duration_seconds || 5}秒</span>
                        <span class="meta-item">🎬 ${shot.shot_type || '中景'}</span>
                    </div>
                </div>
                <div class="shot-card-actions">
                    <button class="btn-view btn-sm" data-index="${index}">
                        👁️ 查看
                    </button>
                    <button class="btn-generate btn-sm" data-index="${index}" ${shot.status === 'completed' ? 'disabled' : ''}>
                        🚀 生成
                    </button>
                </div>
            `;
            
            container.appendChild(shotCard);
        });
        
        // 绑定事件
        container.querySelectorAll('.btn-view').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.viewShot(parseInt(e.target.dataset.index));
            });
        });
        
        container.querySelectorAll('.btn-generate').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.generateShot(parseInt(e.target.dataset.index));
            });
        });
    }
    
    getStatusText(status) {
        switch(status) {
            case 'completed': return '✅ 已完成';
            case 'generating': return '⏳ 生成中';
            case 'failed': return '❌ 失败';
            default: return '⏸️ 待生成';
        }
    }
    
    viewShot(index) {
        this.currentShot = this.shots[index];
        
        // 显示镜头详情屏幕
        document.getElementById('storyboardScreen').style.display = 'none';
        document.getElementById('shotGenerationScreen').style.display = 'block';
        
        // 更新标题
        document.getElementById('shotGenerationTitle').textContent = 
            `镜头 #${index + 1} 详情`;
        
        // 填充详情
        document.getElementById('shotNumber').textContent = `镜头 #${index + 1}`;
        document.getElementById('shotDuration').textContent = 
            `预计时长: ${this.currentShot.duration_seconds || 5}秒`;
        document.getElementById('shotSceneDescription').textContent = 
            this.currentShot.scene_description || '暂无描述';
        document.getElementById('shotType').textContent = 
            this.currentShot.shot_type || '中景';
        document.getElementById('shotVisualStyle').textContent = 
            this.currentShot.visual_style || '标准';
        document.getElementById('shotAudio').textContent = 
            this.currentShot.audio_cue || '无';
        document.getElementById('shotPrompt').value = 
            this.currentShot.generation_prompt || '';
        
        // 清空预览区域
        const preview = document.getElementById('shotPreview');
        preview.innerHTML = '<div class="preview-placeholder"><p>🎬 点击"开始生成"开始生成视频</p></div>';
        
        // 隐藏进度区域
        document.getElementById('shotProgressSection').style.display = 'none';
        
        // 更新状态
        this.updateCurrentStatus(`查看镜头 #${index + 1}`);
        
        // 高亮第四步
        this.highlightWorkflowStep(4);
    }
    
    async generateShot(index) {
        const shot = this.shots[index];
        
        // 更新状态
        shot.status = 'generating';
        this.renderShotsList();
        
        // 如果不是在详情页，则进入详情页
        if (this.currentShot?.shot_index !== index) {
            this.viewShot(index);
        }
        
        // 显示进度
        const progressSection = document.getElementById('shotProgressSection');
        const progressBar = document.getElementById('shotProgressBar');
        const progressText = document.getElementById('shotProgressText');
        
        progressSection.style.display = 'block';
        document.getElementById('startShotGenerationBtn').disabled = true;
        
        try {
            this.showToast(`正在生成镜头 #${index + 1}...`, 'success');
            
            const response = await fetch('/api/video/generate-shot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    video_type: this.selectedType,
                    shot_index: index,
                    shot_data: shot
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新镜头状态
                shot.status = 'completed';
                shot.video_path = data.video_path;
                shot.thumbnail_path = data.thumbnail_path;
                
                // 更新预览
                this.updateShotPreview(data);
                
                // 更新统计
                this.updateStats();
                
                this.showToast(`镜头 #${index + 1} 生成成功！`, 'success');
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('生成镜头失败:', error);
            shot.status = 'failed';
            this.showToast('生成失败: ' + error.message, 'error');
        } finally {
            document.getElementById('startShotGenerationBtn').disabled = false;
            this.renderShotsList();
        }
    }
    
    updateShotPreview(data) {
        const preview = document.getElementById('shotPreview');
        
        if (data.thumbnail_path) {
            preview.innerHTML = `
                <img src="${data.thumbnail_path}" alt="镜头预览" class="shot-thumbnail">
                ${data.video_path ? `
                    <video controls class="shot-video">
                        <source src="${data.video_path}" type="video/mp4">
                    </video>
                ` : ''}
            `;
        } else {
            preview.innerHTML = '<div class="preview-placeholder"><p>✅ 生成完成，但暂无预览</p></div>';
        }
    }
    
    updateStats() {
        const completed = this.shots.filter(s => s.status === 'completed').length;
        document.getElementById('completedShots').textContent = completed;
    }
    
    async generateAll() {
        if (this.shots.length === 0) {
            this.showToast('没有可生成的镜头', 'error');
            return;
        }
        
        const pendingShots = this.shots.filter(s => s.status !== 'completed');
        
        if (pendingShots.length === 0) {
            this.showToast('所有镜头已生成完成', 'success');
            return;
        }
        
        if (!confirm(`确定要生成所有 ${pendingShots.length} 个未完成的镜头吗？`)) {
            return;
        }
        
        this.showToast(`开始批量生成 ${pendingShots.length} 个镜头...`, 'success');
        
        // 依次生成每个镜头
        for (let i = 0; i < this.shots.length; i++) {
            if (this.shots[i].status !== 'completed') {
                await this.generateShot(i);
                // 等待一段时间再继续
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
        }
        
        this.showToast('批量生成完成！', 'success');
    }
    
    async exportStoryboard() {
        if (!this.storyboard) {
            this.showToast('没有可导出的内容', 'error');
            return;
        }
        
        this.showToast('正在导出...', 'success');
        
        try {
            const response = await fetch('/api/video/export-storyboard', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    video_type: this.selectedType
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('导出成功！', 'success');
                // 可以添加下载逻辑
            } else {
                throw new Error(data.error || '导出失败');
            }
        } catch (error) {
            console.error('导出失败:', error);
            this.showToast('导出失败: ' + error.message, 'error');
        }
    }
    
    bindEvents() {
        // 模式选择事件
        document.querySelectorAll('.mode-card').forEach(card => {
            card.addEventListener('click', () => {
                this.selectMode(card.dataset.mode);
            });
        });
        
        // 返回模式选择
        document.getElementById('backToModeBtn').addEventListener('click', () => {
            this.showModeSelectionScreen();
        });
        
        // 预览自定义提示词
        document.getElementById('previewCustomPromptBtn').addEventListener('click', () => {
            this.previewCustomPrompt();
        });
        
        // 从自定义提示词生成分镜头
        document.getElementById('generateStoryboardFromCustomBtn').addEventListener('click', () => {
            this.generateStoryboardFromCustom();
        });
        
        // 快速模板按钮
        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyPreset(btn.dataset.preset);
            });
        });
        
        // 刷新按钮
        document.getElementById('refreshNovelsBtn').addEventListener('click', () => {
            this.loadNovels();
        });
        
        // 返回类型选择（从提示词预览返回）
        document.getElementById('backToTypesBtn').addEventListener('click', () => {
            if (this.selectedMode === 'novel') {
                // 小说模式：返回视频类型选择
                document.getElementById('promptPreviewScreen').style.display = 'none';
                document.getElementById('welcomeScreen').style.display = 'block';
            } else {
                // 自定义模式：返回模式选择
                this.showModeSelectionScreen();
            }
        });
        
        // 从欢迎屏幕返回模式选择
        document.getElementById('backToModeFromWelcomeBtn').addEventListener('click', () => {
            this.showModeSelectionScreen();
        });
        
        // 返回提示词
        document.getElementById('backToPromptBtn').addEventListener('click', () => {
            document.getElementById('storyboardScreen').style.display = 'none';
            document.getElementById('promptPreviewScreen').style.display = 'block';
            this.highlightWorkflowStep(2);
        });
        
        // 返回分镜头列表
        document.getElementById('backToStoryboardBtn').addEventListener('click', () => {
            document.getElementById('shotGenerationScreen').style.display = 'none';
            document.getElementById('storyboardScreen').style.display = 'block';
            this.highlightWorkflowStep(3);
        });
        
        // 编辑提示词
        document.getElementById('editPromptBtn').addEventListener('click', () => {
            this.showPromptEditModal();
        });
        
        // 生成分镜头
        document.getElementById('generateStoryboardBtn').addEventListener('click', () => {
            this.generateStoryboard();
        });
        
        // 全部生成
        document.getElementById('generateAllBtn').addEventListener('click', () => {
            this.generateAll();
        });
        
        // 导出脚本
        document.getElementById('exportStoryboardBtn').addEventListener('click', () => {
            this.exportStoryboard();
        });
        
        // 重新生成分镜头
        document.getElementById('regenerateStoryboardBtn').addEventListener('click', () => {
            if (confirm('确定要重新生成分镜头吗？当前进度将丢失。')) {
                this.generateStoryboard();
            }
        });
        
        // 开始生成单个镜头
        document.getElementById('startShotGenerationBtn').addEventListener('click', () => {
            if (this.currentShot) {
                const index = this.shots.findIndex(s => s === this.currentShot);
                if (index !== -1) {
                    this.generateShot(index);
                }
            }
        });
        
        // 保存提示词修改
        document.getElementById('saveShotPromptBtn').addEventListener('click', () => {
            if (this.currentShot) {
                this.currentShot.generation_prompt = document.getElementById('shotPrompt').value;
                this.showToast('提示词已保存', 'success');
            }
        });
        
        // 提示词编辑模态框
        document.getElementById('closePromptModalBtn').addEventListener('click', () => {
            this.hidePromptEditModal();
        });
        
        document.getElementById('cancelPromptEditBtn').addEventListener('click', () => {
            this.hidePromptEditModal();
        });
        
        document.getElementById('savePromptEditBtn').addEventListener('click', () => {
            this.savePromptEdit();
        });
    }
    
    showPromptEditModal() {
        const modal = document.getElementById('promptEditModal');
        const textarea = document.getElementById('promptEditTextarea');
        textarea.value = this.currentPrompt || '';
        modal.style.display = 'block';
    }
    
    hidePromptEditModal() {
        document.getElementById('promptEditModal').style.display = 'none';
    }
    
    savePromptEdit() {
        const textarea = document.getElementById('promptEditTextarea');
        this.currentPrompt = textarea.value;
        document.getElementById('promptText').textContent = this.currentPrompt;
        this.hidePromptEditModal();
        this.showToast('提示词已更新', 'success');
    }
    
    previewCustomPrompt() {
        const promptInput = document.getElementById('customPromptInput').value.trim();
        if (!promptInput) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        this.customPrompt = promptInput;
        
        // 需要先选择视频类型
        if (!this.selectedType) {
            this.showToast('请先选择视频类型', 'error');
            return;
        }
        
        // 显示预览模态框
        document.getElementById('promptText').textContent = this.customPrompt;
        const typeName = this.videoTypes[this.selectedType].name;
        document.getElementById('promptPreviewTitle').textContent = `✨ 自定义模式 - ${typeName}`;
        document.getElementById('promptPreviewScreen').style.display = 'block';
        document.getElementById('customPromptScreen').style.display = 'none';
        
        // 修改编辑按钮行为
        document.getElementById('editPromptBtn').onclick = () => {
            document.getElementById('promptPreviewScreen').style.display = 'none';
            document.getElementById('customPromptScreen').style.display = 'block';
        };
    }
    
    async generateStoryboardFromCustom() {
        const promptInput = document.getElementById('customPromptInput').value.trim();
        if (!promptInput) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        
        this.customPrompt = promptInput;
        this.currentPrompt = promptInput;
        
        // 需要先选择视频类型
        if (!this.selectedType) {
            this.showToast('请先选择视频类型', 'error');
            return;
        }
        
        try {
            this.showToast('正在生成分镜头脚本...', 'success');
            
            const response = await fetch('/api/video/generate-storyboard-custom', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    prompt: this.customPrompt,
                    video_type: this.selectedType
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.storyboard = data.storyboard;
                this.shots = data.shots || [];
                this.showStoryboardScreen();
            } else {
                throw new Error(data.error || '生成分镜头失败');
            }
        } catch (error) {
            console.error('生成分镜头失败:', error);
            this.showToast('生成分镜头失败: ' + error.message, 'error');
        }
    }
    
    applyPreset(presetType) {
        const presets = {
            xianxia: `一个仙侠风格的视频场景：

场景描述：
主角站在云端，周围是缭绕的仙气和壮观的云海。远处是连绵起伏的山峦，山峰隐约可见。

视觉风格：
- 水墨画风，飘逸空灵
- 淡蓝和白色为主色调
- 光线柔和，有仙气缭绕的效果

镜头语言：
- 开场：大远景，展示宏大的仙界场景
- 中景：主角修行的特写，神态专注
- 特写：主角手中的法器，发光特效

音效建议：
- 轻柔的古琴背景音乐
- 风声和云海流动的声音
- 法器发光时的音效`,

            modern: `现代都市风格的视频场景：

场景描述：
繁华的城市夜景，霓虹灯闪烁，高楼大厦林立。主角走在繁华的商业街上。

视觉风格：
- 现代都市风格，时尚感强
- 多彩的霓虹灯效果
- 夜景灯光，氛围感十足

镜头语言：
- 城市全景，展示繁华景象
- 主角走路的跟拍镜头
- 街边店铺的快速剪辑

音效建议：
- 流行音乐背景
- 城市的环境音（车流、人群）
- 节奏感强的鼓点`,

            scifi: `科幻未来风格的视频场景：

场景描述：
未来的太空站内部，高科技设备遍布。透过巨大的舷窗可以看到遥远的星球和星云。

视觉风格：
- 科幻未来感，金属质感
- 蓝色和紫色为主色调
- 全息投影和光束效果

镜头语言：
- 太空站内部的全景
- 控制面板的特写
- 舷窗外太空景色的镜头

音效建议：
- 电子合成器音乐
- 设备运转的音效
- 太空的寂静感`,

            romance: `浪漫爱情风格的视频场景：

场景描述：
黄昏的海边，夕阳西下，天空呈现橙红色。情侣手牵手漫步在沙滩上，海浪轻拍着海岸。

视觉风格：
- 温馨浪漫的暖色调
- 柔和的光线，逆光效果
- 梦幻般的氛围

镜头语言：
- 海边全景，展示浪漫环境
- 情侣的侧脸特写
- 手牵手的特写镜头
- 夕阳下的剪影

音效建议：
- 温馨的钢琴曲或吉他曲
- 海浪的声音
- 海鸥的叫声`,

            fantasy: `奇幻魔法风格的视频场景：

场景描述：
神秘的魔法森林，巨大的古树散发着微光。魔法生物在林间穿梭，空气中漂浮着魔法粒子。

视觉风格：
- 奇幻梦幻风格
- 紫色、绿色、金色交织
- 发光的魔法效果

镜头语言：
- 魔法森林的全景
- 魔法生物的镜头
- 魔法粒子飘落的特写
- 古树发光的镜头

音效建议：
- 神秘的管弦乐
- 魔法生效的音效
- 森林的自然声音`
        };
        
        if (presets[presetType]) {
            document.getElementById('customPromptInput').value = presets[presetType];
            this.showToast('已应用模板', 'success');
        }
    }
    
    showScreen(screenName) {
        document.getElementById('welcomeScreen').style.display = 
            screenName === 'welcome' ? 'block' : 'none';
        document.getElementById('promptPreviewScreen').style.display = 
            screenName === 'prompt' ? 'block' : 'none';
        document.getElementById('storyboardScreen').style.display = 
            screenName === 'storyboard' ? 'block' : 'none';
        document.getElementById('shotGenerationScreen').style.display = 
            screenName === 'shot' ? 'block' : 'none';
    }
    
    updateCurrentStatus(html) {
        document.getElementById('currentStatus').innerHTML = html;
    }
    
    highlightWorkflowStep(step) {
        const steps = document.querySelectorAll('#workflowSteps li');
        steps.forEach((li, index) => {
            if (index + 1 === step) {
                li.classList.add('active');
            } else if (index + 1 < step) {
                li.classList.remove('active');
                li.classList.add('completed');
            } else {
                li.classList.remove('active', 'completed');
            }
        });
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
    new VideoGenerator();
});