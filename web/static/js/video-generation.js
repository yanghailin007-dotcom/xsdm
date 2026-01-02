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
        
        // 新增：事件和角色选择
        this.events = [];
        this.characters = [];
        this.selectedEvents = new Set();
        this.selectedCharacters = new Set();
        this.activeTab = 'events'; // 'events' or 'characters'
        
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
        document.getElementById('eventCharacterSelectionScreen').style.display = 'none';
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('storyboardScreen').style.display = 'none';
        document.getElementById('shotGenerationScreen').style.display = 'none';
        
        // 显示帮助侧边栏，隐藏右侧分镜头
        document.getElementById('helpSidebar').style.display = 'block';
        document.getElementById('rightSidebar').style.display = 'none';
        
        // 隐藏左侧小说列表，使用CSS类
        document.querySelector('.main-container').classList.add('hide-sidebar');
        this.updateCurrentStatus('请选择生成模式');
        this.highlightWorkflowStep(1);
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
        
        // 🔥 新增：在自定义模式中显示视频类型选择器
        this.showVideoTypeSelectorInCustomMode();
    }
    
    showVideoTypeSelectorInCustomMode() {
        // 在自定义提示词屏幕中显示视频类型选择
        const videoTypeContainer = document.createElement('div');
        videoTypeContainer.id = 'customModeVideoTypeSelector';
        videoTypeContainer.className = 'custom-mode-video-type-selector';
        videoTypeContainer.innerHTML = `
            <h3>📹 选择视频类型</h3>
            <div class="video-type-quick-select">
                <button class="type-select-btn ${this.selectedType === 'short_film' ? 'selected' : ''}" data-type="short_film">
                    🎬 短片/动画电影<br>
                    <small>3-10分钟</small>
                </button>
                <button class="type-select-btn ${this.selectedType === 'long_series' ? 'selected' : ''}" data-type="long_series">
                    📺 长篇剧集<br>
                    <small>1-5分钟/集</small>
                </button>
                <button class="type-select-btn ${this.selectedType === 'short_video' ? 'selected' : ''}" data-type="short_video">
                    📱 短视频系列<br>
                    <small>30秒-1分钟</small>
                </button>
            </div>
            <p class="hint">请先选择视频类型，然后输入提示词生成分镜头脚本</p>
        `;
        
        // 插入到提示词输入框之前
        const promptInputCard = document.querySelector('.prompt-input-card');
        const existingSelector = document.getElementById('customModeVideoTypeSelector');
        
        if (existingSelector) {
            existingSelector.remove();
        }
        
        promptInputCard.insertBefore(videoTypeContainer, promptInputCard.firstChild);
        
        // 绑定点击事件
        videoTypeContainer.querySelectorAll('.type-select-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // 移除其他按钮的激活状态
                videoTypeContainer.querySelectorAll('.type-select-btn').forEach(b => b.classList.remove('selected'));
                // 激活当前按钮
                btn.classList.add('selected');
                // 保存选择
                this.selectedType = btn.dataset.type;
                console.log('📹 [自定义模式] 选择视频类型:', this.selectedType);
                this.showToast(`已选择: ${this.videoTypes[this.selectedType]?.name || this.selectedType}`, 'success');
            });
        });
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
        
        // 进入事件和角色选择阶段
        this.showEventCharacterSelection();
    }
    
    showEventCharacterSelection() {
        // 隐藏欢迎屏幕，显示事件和角色选择屏幕
        document.getElementById('welcomeScreen').style.display = 'none';
        document.getElementById('eventCharacterSelectionScreen').style.display = 'block';
        
        // 切换左侧边栏到事件和角色视图
        document.getElementById('novelListView').style.display = 'none';
        document.getElementById('eventCharacterView').style.display = 'block';
        
        // 更新标题
        const typeName = this.videoTypes[this.selectedType].name;
        document.getElementById('eventCharacterTitle').textContent =
            `选择事件和角色 - ${typeName}`;
        document.getElementById('sidebarTitle').textContent = '🎬 选择内容';
        
        // 加载事件和角色数据
        this.loadEventsAndCharacters();
        
        // 更新状态
        this.updateCurrentStatus(`已选择: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 选择事件和角色`);
        
        // 高亮第三步
        this.highlightWorkflowStep(3);
    }
    
    async loadEventsAndCharacters() {
        try {
            const response = await fetch(`/api/video/novel-content?title=${encodeURIComponent(this.selectedNovel)}`);
            const data = await response.json();
            
            if (data.success) {
                this.events = data.events || [];
                this.characters = data.characters || [];
                
                // 不再默认全选，由用户手动选择
                // this.events.forEach(e => this.selectedEvents.add(e.id));
                // this.characters.forEach(c => this.selectedCharacters.add(c.id));
                
                this.renderEventsList();
                this.renderCharactersList();
                this.updateSelectionStats();
            } else {
                throw new Error(data.error || '加载失败');
            }
        } catch (error) {
            console.error('加载事件和角色失败:', error);
            this.showToast('加载失败: ' + error.message, 'error');
        }
    }
    
    renderEventsList() {
        const container = document.getElementById('eventsList');
        
        if (this.events.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无事件</p>
                    <p class="hint">请先完成中级事件生成</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.events.map(event => {
            const isSelected = this.selectedEvents.has(event.id);
            const hasChildren = event.has_children;
            
            return `
                <div class="major-event-item ${isSelected ? 'selected' : ''}" data-id="${event.id}" data-type="major">
                    <div class="major-event-header">
                        <div class="item-checkbox">
                            <input type="checkbox" ${isSelected ? 'checked' : ''}>
                        </div>
                        <div class="expand-btn" data-expanded="false">
                            ${hasChildren ? '▶' : ''}
                        </div>
                        <div class="item-content">
                            <div class="item-header">
                                <div class="item-title">${event.title || event.name || '未命名事件'}</div>
                                ${hasChildren ? `<span class="children-count-badge">${event.children_count}个中级事件</span>` : ''}
                            </div>
                            ${event.description ? `<div class="item-description">${event.description}</div>` : ''}
                            ${event.characters ? `<div class="item-details"><span class="detail-item">👥 ${event.characters}</span></div>` : ''}
                        </div>
                    </div>
                    ${hasChildren ? `
                        <div class="medium-events-list" style="display: none;">
                            ${event.children.map(child => {
                                const childId = `${event.id}_${child.id}`;
                                const childSelected = this.selectedEvents.has(childId);
                                const stageBadges = {
                                    '起': '<span class="stage-badge stage-start">起</span>',
                                    '承': '<span class="stage-badge stage-develop">承</span>',
                                    '转': '<span class="stage-badge stage-turn">转</span>',
                                    '合': '<span class="stage-badge stage-end">合</span>'
                                };
                                const stageBadge = stageBadges[child.stage] || '';
                                
                                return `
                                    <div class="medium-event-item ${childSelected ? 'selected' : ''}" data-id="${childId}" data-type="medium" data-parent="${event.id}">
                                        <div class="item-checkbox">
                                            <input type="checkbox" ${childSelected ? 'checked' : ''}>
                                        </div>
                                        <div class="item-content">
                                            <div class="item-header">
                                                <div class="item-title">${child.title || child.name || child.event || child.main_goal || '未命名事件'}</div>
                                                ${stageBadge}
                                            </div>
                                            ${child.description ? `<div class="item-description">${child.description}</div>` : ''}
                                            ${child.characters || child.location || child.emotion ? `
                                                <div class="item-details">
                                                    ${child.characters ? `<span class="detail-item">👥 ${child.characters}</span>` : ''}
                                                    ${child.location ? `<span class="detail-item">📍 ${child.location}</span>` : ''}
                                                    ${child.emotion ? `<span class="detail-item">💭 ${child.emotion}</span>` : ''}
                                                </div>
                                            ` : ''}
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
        // 绑定点击事件 - 重大事件
        container.querySelectorAll('.major-event-item').forEach(item => {
            const expandBtn = item.querySelector('.expand-btn');
            const mediumEventsList = item.querySelector('.medium-events-list');
            
            // 展开/收起按钮
            if (expandBtn && mediumEventsList) {
                expandBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const isExpanded = expandBtn.dataset.expanded === 'true';
                    expandBtn.dataset.expanded = !isExpanded;
                    expandBtn.textContent = isExpanded ? '▶' : '▼';
                    mediumEventsList.style.display = isExpanded ? 'none' : 'block';
                });
            }
            
            // 点击整个项目
            item.querySelector('.major-event-header').addEventListener('click', () => {
                const id = item.dataset.id;
                if (this.selectedEvents.has(id)) {
                    this.selectedEvents.delete(id);
                    item.classList.remove('selected');
                    item.querySelector('input[type="checkbox"]').checked = false;
                } else {
                    this.selectedEvents.add(id);
                    item.classList.add('selected');
                    item.querySelector('input[type="checkbox"]').checked = true;
                }
                this.updateSelectionStats();
                this.updateDerivedCharacters();
            });
        });
        
        // 绑定点击事件 - 中级事件
        container.querySelectorAll('.medium-event-item').forEach(item => {
            item.addEventListener('click', () => {
                const id = item.dataset.id;
                if (this.selectedEvents.has(id)) {
                    this.selectedEvents.delete(id);
                    item.classList.remove('selected');
                    item.querySelector('input[type="checkbox"]').checked = false;
                } else {
                    this.selectedEvents.add(id);
                    item.classList.add('selected');
                    item.querySelector('input[type="checkbox"]').checked = true;
                }
                this.updateSelectionStats();
                this.updateDerivedCharacters();
            });
        });
    }
    
    renderCharactersList() {
        const container = document.getElementById('charactersList');
        
        if (this.characters.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无角色</p>
                    <p class="hint">请先完成角色生成</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.characters.map(character => {
            const isSelected = this.selectedCharacters.has(character.id);
            // 角色类型标签
            const roleType = character.role || character.role_type || '角色';
            const roleBadge = roleType === '主角' ?
                '<span class="role-badge role-main">主角</span>' :
                '<span class="role-badge role-supporting">配角</span>';
            
            return `
                <div class="content-item ${isSelected ? 'selected' : ''}" data-id="${character.id}" data-type="character">
                    <div class="item-checkbox">
                        <input type="checkbox" ${isSelected ? 'checked' : ''}>
                    </div>
                    <div class="item-content">
                        <div class="item-header">
                            <div class="item-title">${character.name}</div>
                            ${roleBadge}
                            <button class="btn-view-portrait" data-character-id="${character.id}" title="生成剧照">🎨</button>
                        </div>
                        ${character.personality || character.core_personality ? `
                            <div class="item-meta">
                                <span class="meta-tag">🎭 性格: ${character.personality || character.core_personality}</span>
                            </div>
                        ` : ''}
                        ${character.appearance || character.living_characteristics?.physical_presence ? `
                            <div class="item-description">
                                <strong>外貌:</strong> ${character.appearance || character.living_characteristics?.physical_presence || '暂无描述'}
                            </div>
                        ` : ''}
                        ${character.background ? `
                            <div class="item-description">
                                <strong>背景:</strong> ${character.background}
                            </div>
                        ` : ''}
                        ${character.dialogue_style || character.dialogue_style_example ? `
                            <div class="item-details">
                                <span class="detail-item">💬 对话风格: ${character.dialogue_style || character.dialogue_style_example}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.content-item').forEach(item => {
            // 复选框点击事件
            item.addEventListener('click', (e) => {
                // 如果点击的是剧照按钮，不切换选中状态
                if (e.target.classList.contains('btn-view-portrait')) {
                    return;
                }
                
                const id = item.dataset.id;
                if (this.selectedCharacters.has(id)) {
                    this.selectedCharacters.delete(id);
                    item.classList.remove('selected');
                    item.querySelector('input').checked = false;
                } else {
                    this.selectedCharacters.add(id);
                    item.classList.add('selected');
                    item.querySelector('input').checked = true;
                }
                this.updateSelectionStats();
            });
            
            // 剧照按钮点击事件
            const portraitBtn = item.querySelector('.btn-view-portrait');
            if (portraitBtn) {
                portraitBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const characterId = item.dataset.id;
                    this.showCharacterPortraitPanel(characterId);
                });
            }
        });
    }

    async showCharacterPortraitPanel(characterId) {
        try {
            // 获取角色详细信息
            const response = await fetch(`/api/video/character-details?title=${encodeURIComponent(this.selectedNovel)}&character_id=${characterId}`);
            const data = await response.json();
            
            if (!data.success) {
                this.showToast('获取角色详情失败: ' + data.error, 'error');
                return;
            }
            
            const character = data.character;
            
            // 填充角色信息
            document.getElementById('portraitCharacterName').textContent = character.name || '未命名角色';
            document.getElementById('portraitCharacterRole').textContent = character.role || '未知';
            document.getElementById('portraitAppearance').textContent = character.appearance || character.living_characteristics?.physical_presence || '暂无描述';
            document.getElementById('portraitPersonality').textContent = character.personality || character.core_personality || '暂无描述';
            document.getElementById('portraitBackground').textContent = character.background || '暂无描述';
            document.getElementById('portraitDialogueStyle').textContent = character.dialogue_style || character.dialogue_style_example || '暂无描述';
            
            // 填充相关事件
            const eventsContainer = document.getElementById('portraitRelatedEvents');
            if (data.related_events && data.related_events.length > 0) {
                eventsContainer.innerHTML = data.related_events.map(event => `
                    <div class="related-event-item">
                        <div class="event-name">${event.event_name}</div>
                        <div class="event-chapter">${event.chapter_range || '未知章节'}</div>
                        <div class="event-description">${event.description || '暂无描述'}</div>
                    </div>
                `).join('');
            } else {
                eventsContainer.innerHTML = '<p class="empty-hint">暂无相关事件</p>';
            }
            
            // 存储当前角色数据
            this.currentCharacter = {
                id: characterId,
                data: character,
                prompt: data.generation_prompt
            };
            
            // 显示面板
            document.getElementById('characterPortraitPanel').style.display = 'block';
            
            // 检查是否已有剧照（通过文件名模式）
            const possiblePortraitName = `${this.selectedNovel}_${character.name.replace(/[/\\ ]/g, '_')}_portrait`;
            
            // 默认重置生成状态
            document.getElementById('portraitResultSection').style.display = 'none';
            document.getElementById('portraitProgressSection').style.display = 'none';
            document.getElementById('regeneratePortraitBtn').style.display = 'none';
            document.getElementById('generatePortraitBtn').style.display = 'block';
            
            // 尝试加载可能存在的剧照
            this.checkExistingPortrait(character, possiblePortraitName);
            
        } catch (error) {
            console.error('获取角色详情失败:', error);
            this.showToast('获取角色详情失败: ' + error.message, 'error');
        }
    }

    async generateCharacterPortrait() {
        if (!this.currentCharacter) {
            this.showToast('请先选择角色', 'error');
            return;
        }
        
        const aspectRatio = document.getElementById('portraitAspectRatio').value;
        const imageSize = document.getElementById('portraitImageSize').value;
        
        // 显示进度
        document.getElementById('portraitProgressSection').style.display = 'block';
        document.getElementById('generatePortraitBtn').disabled = true;
        
        try {
            this.showToast('正在生成角色剧照...', 'success');
            
            console.log('🎨 [DEBUG] 开始生成剧照请求');
            const response = await fetch('/api/video/generate-character-portrait', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    character_id: this.currentCharacter.id,
                    character_data: this.currentCharacter.data,
                    aspect_ratio: aspectRatio,
                    image_size: imageSize
                })
            });
            
            const data = await response.json();
            console.log('📥 [DEBUG] API返回数据:', data);
            
            if (data.success) {
                console.log('✅ [DEBUG] 生成成功，准备显示图片');
                console.log('   - image_url:', data.image_url);
                console.log('   - image_path:', data.image_path);
                
                // 显示生成的图像 - 使用 image_url 而不是 image_path
                const resultImage = document.getElementById('generatedPortraitImage');
                console.log('🎯 [DEBUG] 找到结果图片元素:', resultImage);
                resultImage.src = data.image_url;
                console.log('🖼️ [DEBUG] 设置结果图片src:', data.image_url);
                
                // 同时更新角色预览图
                const previewImage = document.getElementById('characterPortraitPreview');
                console.log('🎯 [DEBUG] 找到预览图片元素:', previewImage);
                previewImage.src = data.image_url;
                console.log('🖼️ [DEBUG] 设置预览图片src:', data.image_url);
                
                // 显示结果区域
                document.getElementById('portraitResultSection').style.display = 'block';
                document.getElementById('regeneratePortraitBtn').style.display = 'block';
                document.getElementById('generatePortraitBtn').style.display = 'none';
                console.log('✅ [DEBUG] 结果区域已显示');
                
                this.showToast(`角色 ${data.character_name} 的剧照生成成功！`, 'success');
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('生成角色剧照失败:', error);
            this.showToast('生成失败: ' + error.message, 'error');
        } finally {
            document.getElementById('portraitProgressSection').style.display = 'none';
            document.getElementById('generatePortraitBtn').disabled = false;
        }
    }

    async checkExistingPortrait(character, baseName) {
        // 尝试从最近的剧照文件加载
        try {
            // 这里可以通过API获取已存在的剧照列表
            // 暂时跳过，等待用户重新生成
            console.log('检查角色剧照:', character.name, baseName);
        } catch (error) {
            console.log('未找到现有剧照');
        }
    }
    
    closePortraitPanel() {
        document.getElementById('characterPortraitPanel').style.display = 'none';
        this.currentCharacter = null;
    }

    downloadPortrait() {
        const resultImage = document.getElementById('generatedPortraitImage');
        if (resultImage.src) {
            const link = document.createElement('a');
            link.href = resultImage.src;
            link.download = `${this.currentCharacter?.data?.name || 'character'}_portrait.png`;
            link.click();
            this.showToast('剧照下载已开始', 'success');
        }
    }
    
    updateSelectionStats() {
        const eventCount = this.selectedEvents.size;
        // 角色数量现在是从事件中自动推导的
        const derivedCharacters = this.deriveCharactersFromEvents();
        const characterCount = derivedCharacters.length;
        
        // 更新左侧边栏
        document.getElementById('selectedEventsCount').textContent = `已选: ${eventCount}个事件`;
        document.getElementById('selectedCharactersCount').textContent = `推导: ${characterCount}个角色`;
        
        // 更新主屏幕
        document.getElementById('selectedEventsCountMain').textContent = eventCount;
        document.getElementById('selectedCharactersCountMain').textContent = characterCount;
        
        // 渲染推导的角色列表
        this.renderDerivedCharacters(derivedCharacters);
    }
    
    deriveCharactersFromEvents() {
        // 从选中的事件中推导角色
        const characterSet = new Set();
        const characterDetails = new Map();
        
        // 遍历所有选中事件
        this.selectedEvents.forEach(eventId => {
            const event = this.findEventById(eventId);
            if (!event) return;
            
            // 检查重大事件
            if (event.type === 'major') {
                const characters = event.characters || '';
                if (characters) {
                    this.parseCharacterString(characters, characterDetails);
                }
                
                // 如果选中了重大事件，也包含其子事件的角色
                if (event.children) {
                    event.children.forEach(child => {
                        const childCharacters = child.characters || '';
                        if (childCharacters) {
                            this.parseCharacterString(childCharacters, characterDetails);
                        }
                    });
                }
            }
            
            // 检查中级事件
            if (event.characters) {
                this.parseCharacterString(event.characters, characterDetails);
            }
        });
        
        // 如果没有推导出角色，返回主要角色
        if (characterDetails.size === 0) {
            return this.characters.slice(0, 5); // 返回前5个角色作为默认
        }
        
        return Array.from(characterDetails.values());
    }
    
    parseCharacterString(charactersStr, characterDetails) {
        // 解析角色字符串并提取角色信息
        if (!charactersStr) return;
        
        // 分割字符名（支持多种分隔符）
        const names = charactersStr.split(/[,，、;；]/).map(s => s.trim()).filter(s => s);
        
        names.forEach(name => {
            if (!characterDetails.has(name)) {
                // 尝试从完整角色列表中找到详细信息
                const fullChar = this.characters.find(c => c.name === name);
                characterDetails.set(name, fullChar || { name, role: '推导角色' });
            }
        });
    }
    
    findEventById(eventId) {
        // 根据ID查找事件
        // 检查重大事件
        const majorEvent = this.events.find(e => e.id === eventId);
        if (majorEvent) return majorEvent;
        
        // 检查中级事件
        for (const major of this.events) {
            if (major.children) {
                const child = major.children.find(c => `${major.id}_${c.id}` === eventId);
                if (child) return child;
            }
        }
        
        return null;
    }
    
    renderDerivedCharacters(characters) {
        // 渲染推导的角色列表（只读，不可手动选择）
        const container = document.getElementById('charactersList');
        
        if (characters.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无角色</p>
                    <p class="hint">选择事件后将自动推导相关角色</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = characters.map(character => {
            const roleType = character.role || character.role_type || '角色';
            const roleBadge = roleType === '主角' ?
                '<span class="role-badge role-main">主角</span>' :
                '<span class="role-badge role-supporting">配角</span>';
            
            return `
                <div class="content-item derived-character" data-id="${character.name || character.id}">
                    <div class="item-checkbox">
                        <input type="checkbox" checked disabled>
                    </div>
                    <div class="item-content">
                        <div class="item-header">
                            <div class="item-title">${character.name || '未命名角色'}</div>
                            ${roleBadge}
                            <span class="derived-badge">🔍 自动推导</span>
                        </div>
                        ${character.personality || character.core_personality ? `
                            <div class="item-meta">
                                <span class="meta-tag">🎭 性格: ${character.personality || character.core_personality}</span>
                            </div>
                        ` : ''}
                        ${character.appearance || character.living_characteristics?.physical_presence ? `
                            <div class="item-description">
                                <strong>外貌:</strong> ${character.appearance || character.living_characteristics?.physical_presence || '暂无描述'}
                            </div>
                        ` : ''}
                        ${character.background ? `
                            <div class="item-description">
                                <strong>背景:</strong> ${character.background}
                            </div>
                        ` : ''}
                        <button class="btn-view-portrait" data-character-id="${character.name || character.id}" title="生成剧照">🎨</button>
                    </div>
                </div>
            `;
        }).join('');
        
        // 绑定剧照按钮事件
        container.querySelectorAll('.btn-view-portrait').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const characterId = btn.dataset.characterId;
                this.showCharacterPortraitPanel(characterId);
            });
        });
    }
    
    updateDerivedCharacters() {
        // 更新推导的角色（当选择变化时调用）
        const derivedCharacters = this.deriveCharactersFromEvents();
        this.renderDerivedCharacters(derivedCharacters);
        this.updateSelectionStats();
    }
    
    switchTab(tabName) {
        this.activeTab = tabName;
        
        // 更新标签按钮状态
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.tab === tabName) {
                btn.classList.add('active');
            }
        });
        
        // 更新标签内容显示
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(`${tabName}Tab`).classList.add('active');
    }
    
    selectAllEvents() {
        this.events.forEach(e => this.selectedEvents.add(e.id));
        this.renderEventsList();
        this.updateSelectionStats();
    }
    
    selectAllCharacters() {
        this.characters.forEach(c => this.selectedCharacters.add(c.id));
        this.renderCharactersList();
        this.updateSelectionStats();
    }
    
    clearSelection() {
        this.selectedEvents.clear();
        this.selectedCharacters.clear();
        this.renderEventsList();
        this.renderCharactersList();
        this.updateSelectionStats();
    }
    
    async confirmSelection() {
        if (this.selectedEvents.size === 0 && this.selectedCharacters.size === 0) {
            this.showToast('请至少选择一个事件或角色', 'error');
            return;
        }
        
        // 生成提示词
        await this.generatePrompt();
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
                    video_type: this.selectedType,
                    selected_events: Array.from(this.selectedEvents),
                    selected_characters: Array.from(this.selectedCharacters)
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
        // 隐藏事件和角色选择屏幕，显示提示词预览
        document.getElementById('eventCharacterSelectionScreen').style.display = 'none';
        document.getElementById('promptPreviewScreen').style.display = 'block';
        
        // 更新标题
        const typeName = this.videoTypes[this.selectedType].name;
        document.getElementById('promptPreviewTitle').textContent =
            `${this.selectedNovel} - ${typeName}`;
        
        // 显示提示词
        document.getElementById('promptText').textContent = this.currentPrompt || '正在生成...';
        
        // 更新状态
        this.updateCurrentStatus(`已选择: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 查看提示词`);
        
        // 高亮第四步
        this.highlightWorkflowStep(4);
    }
    
    async generateStoryboard() {
        console.log('🎬 [前端] ===== 开始生成分镜头脚本 =====');
        console.log('📊 [前端] 当前模式:', this.selectedMode);
        console.log('📊 [前端] 选中的小说:', this.selectedNovel);
        console.log('📊 [前端] 视频类型:', this.selectedType);
        console.log('📊 [前端] 当前提示词长度:', this.currentPrompt?.length || 0);
        
        // 🔍 前置条件检查
        if (this.selectedMode === 'novel') {
            if (!this.selectedNovel) {
                console.error('❌ [前端] 未选择小说');
                this.showToast('请先选择小说', 'error');
                return;
            }
            if (!this.selectedType) {
                console.error('❌ [前端] 未选择视频类型');
                this.showToast('请先选择视频类型', 'error');
                return;
            }
        } else if (this.selectedMode === 'custom') {
            if (!this.selectedType) {
                console.error('❌ [前端] 未选择视频类型');
                this.showToast('请先选择视频类型', 'error');
                return;
            }
            if (!this.currentPrompt && !this.customPrompt) {
                console.error('❌ [前端] 未输入提示词');
                this.showToast('请先输入或生成提示词', 'error');
                return;
            }
        } else {
            console.error('❌ [前端] 未选择模式');
            this.showToast('请先选择生成模式', 'error');
            return;
        }
        
        try {
            // 显示加载状态
            const btn = document.getElementById('generateStoryboardBtn');
            if (btn) {
                btn.disabled = true;
                btn.textContent = '⏳ 生成中...';
            }
            this.showToast('正在生成分镜头脚本，请稍候...', 'success');
            
            let response, data;
            
            // 🔥 根据模式选择不同的API端点
            if (this.selectedMode === 'custom') {
                console.log('🔀 [前端] 使用自定义模式API');
                // 自定义模式：使用自定义提示词API
                const requestData = {
                    prompt: this.currentPrompt || this.customPrompt,
                    video_type: this.selectedType
                };
                console.log('📤 [前端] 请求数据:', requestData);
                
                response = await fetch('/api/video/generate-storyboard-custom', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            } else {
                console.log('🔀 [前端] 使用小说模式API');
                // 小说模式：使用小说数据API（传递选中事件）
                const requestData = {
                    title: this.selectedNovel,
                    video_type: this.selectedType,
                    selected_events: Array.from(this.selectedEvents)  // 🔥 传递选中事件
                };
                console.log('📤 [前端] 请求数据:', requestData);
                console.log('📊 [前端] 选中事件列表:', Array.from(this.selectedEvents));
                
                response = await fetch('/api/video/generate-storyboard', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(requestData)
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            console.log('📡 [前端] 响应状态:', response.status, response.statusText);
            
            data = await response.json();
            console.log('📥 [前端] 响应数据:', data);
            
            if (data.success) {
                console.log('✅ [前端] 分镜头生成成功');
                console.log('📊 [前端] 分镜头数量:', data.total_shots);
                this.storyboard = data.storyboard;
                this.shots = data.shots || [];
                this.showStoryboardScreen();
            } else {
                console.error('❌ [前端] API返回错误:', data.error);
                throw new Error(data.error || '生成分镜头失败');
            }
        } catch (error) {
            console.error('❌ [前端] 生成分镜头失败:', error);
            console.error('❌ [前端] 错误详情:', error.message);
            console.error('❌ [前端] 错误堆栈:', error.stack);
            
            // 显示详细的错误信息
            let errorMessage = error.message;
            if (error.message.includes('HTTP 404')) {
                errorMessage = 'API端点不存在，请检查服务器配置';
            } else if (error.message.includes('HTTP 500')) {
                errorMessage = '服务器内部错误，请稍后重试';
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = '无法连接到服务器，请检查网络连接';
            }
            
            this.showToast('生成分镜头失败: ' + errorMessage, 'error');
            
            // 在页面显示错误详情
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-details';
            errorDiv.style.cssText = 'margin-top: 20px; padding: 15px; background: #fee; border: 1px solid #f88; border-radius: 5px;';
            errorDiv.innerHTML = `
                <h4 style="color: #c00; margin: 0 0 10px 0;">❌ 生成失败</h4>
                <p style="margin: 5px 0;"><strong>错误信息:</strong> ${errorMessage}</p>
                <p style="margin: 5px 0; font-size: 12px; color: #666;">请检查浏览器控制台的详细日志</p>
            `;
            
            const promptInfoCard = document.querySelector('.prompt-info-card');
            const existingError = promptInfoCard.querySelector('.error-details');
            if (existingError) {
                existingError.remove();
            }
            promptInfoCard.appendChild(errorDiv);
            
        } finally {
            // 恢复按钮状态
            const btn = document.getElementById('generateStoryboardBtn');
            if (btn) {
                btn.disabled = false;
                btn.textContent = '🎬 生成分镜头脚本';
            }
        }
    }
    
    showStoryboardScreen() {
        // 隐藏提示词预览，显示分镜头列表
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('customPromptScreen').style.display = 'none';
        document.getElementById('eventCharacterSelectionScreen').style.display = 'none';
        document.getElementById('storyboardScreen').style.display = 'block';
        
        // 显示右侧分镜头列表，隐藏帮助侧边栏
        document.getElementById('helpSidebar').style.display = 'none';
        document.getElementById('rightSidebar').style.display = 'block';
        
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
        
        // 计算总时长（使用10秒作为默认值）
        const totalDuration = this.shots.reduce((sum, shot) =>
            sum + (shot.duration_seconds || 10), 0);
        document.getElementById('estimatedDuration').textContent =
            `${Math.round(totalDuration / 60)}分钟`;
        
        // 渲染镜头列表
        this.renderShotsList();
        this.renderGeneratedShotsList();
        
        // 更新状态
        this.updateCurrentStatus(`已生成 ${this.shots.length} 个分镜头<br>可逐个或批量生成`);
        
        // 高亮第五步
        this.highlightWorkflowStep(5);
    }
    
    renderGeneratedShotsList() {
        const container = document.getElementById('generatedShotsList');
        const count = this.shots.length;
        
        document.getElementById('generatedShotsCount').textContent = count;
        
        if (count === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬 还没有生成分镜头</p>
                    <p class="hint">选择事件和角色后开始生成</p>
                </div>
            `;
            document.getElementById('quickActions').style.display = 'none';
            return;
        }
        
        document.getElementById('quickActions').style.display = 'flex';
        
        container.innerHTML = this.shots.map((shot, index) => `
            <div class="generated-shot-item ${shot.status === 'completed' ? 'completed' : ''}">
                <div class="shot-mini-header">
                    <span class="shot-mini-number">#${index + 1}</span>
                    <span class="shot-mini-status">${this.getStatusText(shot.status)}</span>
                </div>
                <div class="shot-mini-content">
                    <p class="shot-mini-scene">${shot.scene_description || '暂无描述'}</p>
                    <div class="shot-mini-meta">
                        <span>⏱️ ${shot.duration_seconds || 10}秒</span>
                    </div>
                </div>
            </div>
        `).join('');
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
                        <span class="meta-item">⏱️ ${shot.duration_seconds || 10}秒</span>
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
            `预计时长: ${this.currentShot.duration_seconds || 10}秒`;
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
        console.log('🔧 [事件绑定] 开始绑定所有事件...');
        
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
        
        // 事件和角色选择相关事件
        document.getElementById('eventsTabBtn').addEventListener('click', () => {
            this.switchTab('events');
        });
        
        document.getElementById('charactersTabBtn').addEventListener('click', () => {
            this.switchTab('characters');
        });
        
        document.getElementById('selectAllEventsBtn').addEventListener('click', () => {
            this.selectAllEvents();
        });
        
        document.getElementById('selectAllCharactersBtn').addEventListener('click', () => {
            this.selectAllCharacters();
        });
        
        document.getElementById('clearSelectionBtn').addEventListener('click', () => {
            this.clearSelection();
        });
        
        document.getElementById('confirmSelectionBtn').addEventListener('click', () => {
            this.confirmSelection();
        });
        
        document.getElementById('selectAllContentBtn').addEventListener('click', () => {
            this.selectAllEvents();
            this.selectAllCharacters();
        });
        
        document.getElementById('refreshContentBtn').addEventListener('click', () => {
            this.loadEventsAndCharacters();
        });
        
        // 返回类型选择（从事件和角色选择返回）
        document.getElementById('backToTypesFromEventBtn').addEventListener('click', () => {
            document.getElementById('eventCharacterSelectionScreen').style.display = 'none';
            document.getElementById('welcomeScreen').style.display = 'block';
            
            // 切换左侧边栏回小说列表
            document.getElementById('eventCharacterView').style.display = 'none';
            document.getElementById('novelListView').style.display = 'block';
        });
        
        // 返回类型选择（从提示词预览返回）
        document.getElementById('backToTypesBtn').addEventListener('click', () => {
            if (this.selectedMode === 'novel') {
                // 小说模式：返回事件和角色选择
                document.getElementById('promptPreviewScreen').style.display = 'none';
                document.getElementById('eventCharacterSelectionScreen').style.display = 'block';
                this.highlightWorkflowStep(3);
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
        console.log('🔍 [绑定] 开始查找 generateStoryboardBtn 按钮...');
        const generateStoryboardBtn = document.getElementById('generateStoryboardBtn');
        console.log('🔍 [绑定] 按钮元素:', generateStoryboardBtn);
        
        if (generateStoryboardBtn) {
            console.log('✅ [绑定] 找到 generateStoryboardBtn 按钮，开始绑定事件');
            
            // 移除旧的事件监听器（如果有）
            const newBtn = generateStoryboardBtn.cloneNode(true);
            generateStoryboardBtn.parentNode.replaceChild(newBtn, generateStoryboardBtn);
            
            newBtn.addEventListener('click', (e) => {
                console.log('='.repeat(60));
                console.log('🔘 [按钮] generateStoryboardBtn 被点击!');
                console.log('📊 [按钮] this.selectedMode:', this.selectedMode);
                console.log('📊 [按钮] this.selectedNovel:', this.selectedNovel);
                console.log('📊 [按钮] this.selectedType:', this.selectedType);
                console.log('📊 [按钮] 当前提示词长度:', this.currentPrompt?.length || 0);
                console.log('='.repeat(60));
                
                // 防止默认行为
                e.preventDefault();
                e.stopPropagation();
                
                this.generateStoryboard();
            });
            
            console.log('✅ [绑定] 事件绑定完成');
        } else {
            console.error('❌ [绑定] 未找到 generateStoryboardBtn 按钮');
            console.error('❌ [绑定] 页面中可用的按钮:', document.querySelectorAll('button[id]'));
        }
        
        // 全部生成
        document.getElementById('generateAllBtn').addEventListener('click', () => {
            this.generateAll();
        });
        
        // 导出脚本
        document.getElementById('exportStoryboardBtn').addEventListener('click', () => {
            this.exportStoryboard();
        });
        
        // 右侧分镜头操作
        document.getElementById('exportGeneratedBtn').addEventListener('click', () => {
            this.exportStoryboard();
        });
        
        document.getElementById('clearGeneratedBtn').addEventListener('click', () => {
            if (confirm('确定要清空所有已生成的分镜头吗？')) {
                this.shots = [];
                this.renderGeneratedShotsList();
                this.showToast('已清空', 'success');
            }
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
        
        // 角色剧照生成相关事件
        const closePortraitPanelBtn = document.getElementById('closePortraitPanelBtn');
        if (closePortraitPanelBtn) {
            closePortraitPanelBtn.addEventListener('click', () => {
                this.closePortraitPanel();
            });
        }
        
        const generatePortraitBtn = document.getElementById('generatePortraitBtn');
        if (generatePortraitBtn) {
            generatePortraitBtn.addEventListener('click', () => {
                this.generateCharacterPortrait();
            });
        }
        
        const regeneratePortraitBtn = document.getElementById('regeneratePortraitBtn');
        if (regeneratePortraitBtn) {
            regeneratePortraitBtn.addEventListener('click', () => {
                this.generateCharacterPortrait();
            });
        }
        
        const downloadPortraitBtn = document.getElementById('downloadPortraitBtn');
        if (downloadPortraitBtn) {
            downloadPortraitBtn.addEventListener('click', () => {
                this.downloadPortrait();
            });
        }
        
        console.log('✅ [事件绑定] 所有事件绑定完成');
        console.log('📋 [事件绑定] 已绑定的按钮数量:', document.querySelectorAll('button').length);
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
console.log('🚀 [全局] 页面开始加载...');

document.addEventListener('DOMContentLoaded', () => {
    console.log('📜 [全局] DOM内容加载完成，开始初始化视频生成器');
    console.log('📋 [全局] 当前页面URL:', window.location.href);
    console.log('📋 [全局] 是否存在generateStoryboardBtn:', !!document.getElementById('generateStoryboardBtn'));
    
    try {
        const generator = new VideoGenerator();
        console.log('✅ [全局] 视频生成器初始化成功');
        console.log('📊 [全局] 生成器实例:', generator);
        
        // 将生成器实例挂载到全局对象，方便调试
        window.videoGenerator = generator;
        console.log('🔍 [全局] 生成器已挂载到 window.videoGenerator');
    } catch (error) {
        console.error('❌ [全局] 视频生成器初始化失败:', error);
        console.error('❌ [全局] 错误堆栈:', error.stack);
    }
});

// 额外的备用初始化
window.addEventListener('load', () => {
    console.log('📄 [全局] Window完全加载完成');
    
    // 检查是否已经初始化
    if (!window.videoGenerator) {
        console.warn('⚠️ [全局] DOMContentLoaded未触发，尝试手动初始化');
        try {
            const generator = new VideoGenerator();
            window.videoGenerator = generator;
            console.log('✅ [全局] 备用初始化成功');
        } catch (error) {
            console.error('❌ [全局] 备用初始化失败:', error);
        }
    }
});