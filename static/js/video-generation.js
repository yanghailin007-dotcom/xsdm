/**
 * 视频生成系统 - 前端逻辑
 * 改进版：支持分步骤生成视频，统一工作流
 */

// 统一工作流步骤定义
const WORKFLOW_STEPS = {
    1: {
        name: '风格转换',
        description: '将小说内容转换为选定视频风格的格式',
        icon: '🎨'
    },
    2: {
        name: '生成角色剧照',
        description: '为选中的重大事件/集生成主要角色的固定形象剧照',
        icon: '📸'
    },
    3: {
        name: '生成分镜头',
        description: '基于风格转换内容和角色剧照，生成具体的分镜头脚本',
        icon: '🎬'
    },
    4: {
        name: '生成视频',
        description: '根据分镜头脚本逐个或批量生成视频文件',
        icon: '🎥'
    }
};

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
        this.worldview = {};  // 🔥 世界观数据
        this.selectedEvents = new Set();
        this.selectedCharacters = new Set();
        this.activeTab = 'events'; // 'events' or 'characters'

        // 统一工作流状态
        this.workflowStep = 0; // 0=未开始, 1-4=对应步骤
        this.workflowData = {
            styleConversion: null,
            characterPortraits: null,
            storyboard: null,
            videos: null
        };

        this.init();
    }

    /**
     * 🔥 统一的路径清理函数（与后端sanitize_path保持一致）
     * 清理文件名，移除Windows不允许的字符
     */
    sanitizePath(name) {
        const invalidChars = ['<', '>', ':', '"', '/', '\\', '|', '?', '、', '？', '！', '＊', '＂', '＜', '＞', '／', '＼', '｜', '!'];
        let result = name;
        for (const char of invalidChars) {
            result = result.replace(new RegExp(char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '_');
        }
        return result.replace(/^_+|_+$/g, ''); // 去除首尾下划线
    }

    async init() {
        console.log('🎬 视频生成系统初始化...');

        // 🔥 优先检查URL参数，处理从短剧风格改造页面跳转过来的情况
        if (await this.checkURLParams()) {
            console.log('🔗 [URL参数] 已处理URL参数，跳过常规初始化');
            return; // 如果有URL参数，直接返回
        }

        // 加载视频类型
        await this.loadVideoTypes();

        // 加载小说列表
        await this.loadNovels();

        // 绑定事件
        this.bindEvents();

        // 🔥 监听页面可见性变化，用于从剧照工作室返回后自动刷新
        this.setupVisibilityListener();

        // 显示模式选择屏幕
        this.showModeSelectionScreen();

        console.log('✅ 初始化完成');
    }

    /**
     * 🔥 设置页面可见性监听器，用于从剧照工作室返回后自动刷新
     */
    setupVisibilityListener() {
        // 🔥 监听localStorage变化（当在剧照工作室保存结果时触发）
        window.addEventListener('storage', (e) => {
            if (e.key === 'portraitStudio_result' && e.newValue) {
                console.log('📺 [storage事件] 检测到剧照结果已保存:', e.newValue);
                // 检查是否在剧照步骤
                const portraitContainer = document.getElementById('episodeCharacterPortraits');
                if (portraitContainer) {
                    console.log('📺 [storage事件] 当前在剧照步骤，刷新显示...');
                    // 延迟一下确保数据已完全写入
                    setTimeout(() => {
                        this.checkPortraitStudioResult();
                        this.loadCharacterPortraitsStep();
                    }, 100);
                }
            }
        });

        // 监听页面可见性变化（当用户切回标签页时）
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                console.log('📺 [页面可见性] 页面重新获得可见性');
                this.handlePageVisible();
            }
        });

        // 也监听窗口焦点变化
        window.addEventListener('focus', () => {
            console.log('📺 [页面焦点] 窗口重新获得焦点');
            this.handlePageVisible();
        });
    }

    /**
     * 🔥 处理页面重新可见，检查是否需要刷新剧照步骤
     */
    handlePageVisible() {
        // 检查是否在剧照步骤（检查是否有剧照相关的DOM元素）
        const portraitContainer = document.getElementById('episodeCharacterPortraits');
        if (portraitContainer) {
            console.log('📺 [页面可见性] 检测到在剧照步骤，检查是否有新剧照...');

            // 先检查localStorage中是否有新剧照
            const resultData = localStorage.getItem('portraitStudio_result');
            if (resultData) {
                console.log('📺 [页面可见性] 发现localStorage中的剧照数据:', resultData);

                // 先调用checkPortraitStudioResult保存数据
                this.checkPortraitStudioResult();

                // 刷新角色剧照显示
                this.loadCharacterPortraitsStep();
            } else {
                console.log('📺 [页面可见性] localStorage中没有新剧照数据');
                // 即使没有新数据，也刷新一下显示（可能已经有之前的数据）
                this.loadCharacterPortraitsStep();
            }
        }
    }

    /**
     * 检查URL参数，处理从短剧风格改造页面跳转过来的情况
     * @returns {boolean} 如果处理了URL参数返回true，否则返回false
     */
    async checkURLParams() {
        const urlParams = new URLSearchParams(window.location.search);
        const mode = urlParams.get('mode');
        const novel = urlParams.get('novel');

        console.log('🔗 [URL参数] 检查URL参数:', { mode, novel });

        if (mode === 'episode-workflow' && novel) {
            console.log('🎯 [URL参数] 启动按集制作工作流，小说:', novel);

            // 先加载数据
            await this.loadVideoTypes();
            await this.loadNovels();
            this.bindEvents();
            this.setupVisibilityListener();

            // 启动工作流
            await this.startEpisodeWorkflowFromShortDrama(novel);
            return true; // 返回true表示已处理
        } else if (mode === 'unified-workflow' && novel) {
            console.log('🚀 [URL参数] 启动统一工作流，小说:', novel);

            // 先加载数据
            await this.loadVideoTypes();
            await this.loadNovels();
            this.bindEvents();
            this.setupVisibilityListener();

            // 启动工作流
            await this.startUnifiedWorkflowFromShortDrama(novel);
            return true; // 返回true表示已处理
        }

        return false; // 没有URL参数需要处理
    }

    /**
     * 从短剧风格改造页面启动按集制作工作流
     */
    async startEpisodeWorkflowFromShortDrama(novelTitle) {
        console.log('📺 [按集制作] 从短剧风格改造启动, 小说:', novelTitle);

        // 隐藏模式选择屏幕
        document.getElementById('modeSelectionScreen').style.display = 'none';

        // 🔥 清空之前的剧照数据（切换小说时）
        if (this.episodeWorkflow?.characterPortraits) {
            this.episodeWorkflow.characterPortraits.clear();
        }
        localStorage.removeItem('episodeWorkflow_characterPortraits');

        // 显示按集制作工作流屏幕
        const screen = document.getElementById('episodeWorkflowScreen');
        if (screen) {
            screen.style.display = 'block';
        }

        // 隐藏侧边栏
        document.querySelector('.main-container')?.classList.add('hide-sidebar');

        // 设置选中的小说
        this.selectedNovel = novelTitle;

        // 初始化工作流数据
        this.episodeWorkflow = {
            step: 'select-episodes',
            selectedMajorEvent: null,
            selectedEpisodes: new Set(),
            characterPortraits: new Map(),
            storyboardData: null,
            videoData: null
        };

        // 恢复剧照数据
        this.restoreCharacterPortraits();

        // 加载事件和角色
        await this.loadEventsAndCharacters();

        // 加载重大事件列表
        await this.loadMajorEventsForWorkflow();

        // 绑定工作流事件
        this.bindEpisodeWorkflowEvents();

        // 更新标题
        const titleEl = document.getElementById('episodeWorkflowTitle');
        if (titleEl) {
            titleEl.textContent = `📺 ${novelTitle} - 按集制作`;
        }

        console.log('✅ [按集制作] 工作流初始化完成');
    }

    /**
     * 从短剧风格改造页面启动统一工作流
     */
    async startUnifiedWorkflowFromShortDrama(novelTitle) {
        console.log('🚀 [统一工作流] 从短剧风格改造启动, 小说:', novelTitle);

        // 隐藏模式选择屏幕
        document.getElementById('modeSelectionScreen').style.display = 'none';

        // 显示统一工作流屏幕（如果有的话）
        const screen = document.getElementById('unifiedWorkflowScreen');
        if (screen) {
            screen.style.display = 'block';
        } else {
            // 如果没有统一工作流屏幕，显示提示
            this.showToast('统一工作流功能开发中，请使用分集制作模式', 'info');
            // 返回模式选择
            setTimeout(() => {
                window.location.href = '/short-drama';
            }, 2000);
        }

        // 设置选中的小说
        this.selectedNovel = novelTitle;

        // 加载事件和角色
        await this.loadEventsAndCharacters();

        console.log('✅ [统一工作流] 初始化完成');
    }

    /**
     * 🔥 从localStorage恢复剧照数据
     */
    restoreCharacterPortraits() {
        try {
            const saved = localStorage.getItem('episodeWorkflow_characterPortraits');
            if (saved) {
                const portraits = JSON.parse(saved);

                // 🔥 检查并清除旧格式URL的缓存
                let hasOldFormat = false;
                for (const [name, data] of Object.entries(portraits)) {
                    if (data.imageUrl && (data.imageUrl.includes('\\') || data.imageUrl.match(/_[^_]+_[^_]+\.png$/))) {
                        console.log(`🗑️ [清理缓存] 发现旧格式URL，清除缓存: ${name}`, data.imageUrl);
                        hasOldFormat = true;
                        break;
                    }
                }

                if (hasOldFormat) {
                    console.log('🗑️ [清理缓存] 清除旧格式剧照缓存');
                    localStorage.removeItem('episodeWorkflow_characterPortraits');
                    this.episodeWorkflow.characterPortraits = new Map();
                } else {
                    this.episodeWorkflow.characterPortraits = new Map(Object.entries(portraits));
                    console.log('📺 [恢复剧照] 从localStorage恢复剧照数据:', Array.from(this.episodeWorkflow.characterPortraits.keys()));
                }
            }
        } catch (e) {
            console.error('❌ [恢复剧照] 恢复剧照数据失败:', e);
        }
    }

    /**
     * 🔥 从视频项目目录发现已有的剧照
     */
    async discoverPortraits() {
        try {
            console.log('🔍 [发现剧照] 开始扫描视频项目目录...');
            console.log('📚 [发现剧照] 当前小说:', this.selectedNovel);

            const response = await fetch('/api/video/discover-portraits');
            const data = await response.json();

            if (data.success && data.portraits && data.portraits.length > 0) {
                // 🔥 只保留当前小说的剧照
                const currentNovelPortraits = data.portraits.filter(p => {
                    // 匹配小说标题（处理中文冒号等差异）
                    const portraitNovel = p.novel_title || '';
                    const selectedNovel = this.selectedNovel || '';

                    // 精确匹配或规范化匹配
                    const normalize = (s) => s.replace(/[<>:"/\\|?*：：、＿_]/g, '').toLowerCase();
                    return normalize(portraitNovel) === normalize(selectedNovel);
                });

                console.log(`✅ [发现剧照] 当前小说 ${this.selectedNovel} 的剧照: ${currentNovelPortraits.length} 个`);

                // 将发现的剧照添加到工作流
                let addedCount = 0;
                currentNovelPortraits.forEach(portrait => {
                    const characterName = portrait.character_name;
                    if (!this.episodeWorkflow.characterPortraits.has(characterName)) {
                        this.episodeWorkflow.characterPortraits.set(characterName, {
                            imageUrl: portrait.image_url,
                            imagePath: portrait.local_path,
                            timestamp: portrait.timestamp || new Date().toISOString()
                        });
                        addedCount++;
                        console.log(`✅ [发现剧照] 添加角色: ${characterName} -> ${portrait.image_url}`);
                    }
                });

                this.saveCharacterPortraits();

                if (currentNovelPortraits.length > 0) {
                    this.showToast(`发现 ${currentNovelPortraits.length} 个角色剧照`, 'success');
                } else {
                    this.showToast('当前小说没有发现剧照文件', 'info');
                }

                return { success: true, addedCount };
            } else {
                console.log('ℹ️ [发现剧照] 没有发现剧照文件');
                this.showToast('没有发现已有的剧照文件', 'info');
                return { success: true, addedCount: 0 };
            }
        } catch (error) {
            console.error('❌ [发现剧照] 发现剧照失败:', error);
            this.showToast('发现剧照失败: ' + error.message, 'error');
            return { success: false, error: error.message };
        }
    }

    /**
     * 🔥 保存剧照数据到localStorage
     */
    saveCharacterPortraits() {
        try {
            const portraits = Object.fromEntries(this.episodeWorkflow.characterPortraits);
            localStorage.setItem('episodeWorkflow_characterPortraits', JSON.stringify(portraits));
            console.log('📺 [保存剧照] 剧照数据已保存到localStorage');
        } catch (e) {
            console.error('❌ [保存剧照] 保存剧照数据失败:', e);
        }
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
        } else if (mode === 'portrait') {
            // 跳转到人物剧照工作室
            window.location.href = '/portrait-studio';
        } else if (mode === 'video-workspace') {
            // 跳转到视频工作室
            window.location.href = '/video-studio';
        } else if (mode === 'short-drama') {
            // 跳转到短剧风格改造独立页面
            console.log('🎭 跳转到短剧风格改造页面');
            window.location.href = '/short-drama';
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

        // 自动选中第一个小说（如果有的话）
        setTimeout(() => {
            const firstNovel = document.querySelector('.novel-item');
            if (firstNovel && !this.selectedNovel) {
                const novelTitle = firstNovel.dataset.title;
                this.selectNovel(novelTitle);
                console.log('📚 自动选中小说:', novelTitle);
            }
        }, 500);
    }

    /**
     * 🎭 短剧风格改造工作流
     * 直接引导用户通过：小说选择 → 事件选择 → 短剧改造 → 剧照优先生成
     */
    startShortDramaWorkflow() {
        console.log('🎭 [短剧模式] startShortDramaWorkflow 函数被调用');
        this.selectedMode = 'novel'; // 复用小说模式逻辑
        this.isShortDramaMode = true; // 标记为短剧模式
        console.log('🎭 [短剧模式] isShortDramaMode 设置为 true');

        document.getElementById('modeSelectionScreen').style.display = 'none';
        document.getElementById('welcomeScreen').style.display = 'block';
        this.updateCurrentStatus('🎭 短剧风格改造：选择小说');

        // 显示左侧小说列表
        document.querySelector('.main-container').classList.remove('hide-sidebar');

        // 自动选中第一个小说（如果有的话）
        setTimeout(() => {
            const firstNovel = document.querySelector('.novel-item');
            if (firstNovel && !this.selectedNovel) {
                const novelTitle = firstNovel.dataset.title;
                this.selectNovel(novelTitle);
                console.log('🎭 [短剧模式] 自动选中小说:', novelTitle);
                this.showToast(`🎭 已自动选择：${novelTitle}`, 'success');
            }
        }, 500);

        // 显示提示信息
        this.showToast('🎭 短剧模式：请选择视频类型，然后选择事件进行短剧风格改造', 'success');
        console.log('🎭 [短剧模式] 工作流初始化完成');
    }

    /**
     * 🎭 短剧风格改造 - 独立页面初始化
     */
    loadNovelsForEpisodeWorkflow() {
        console.log('🎭 短剧风格改造页面初始化');
        // 自动选中第一个小说并加载事件
        this.autoSelectFirstNovelAndLoadEvents();
    }

    /**
     * 加载小说列表用于短剧统一工作流
     */
    async loadNovelsForShortDramaWorkflow() {
        console.log('🚀 短剧统一工作流初始化');
        try {
            const response = await fetch('/api/video/novels');
            const data = await response.json();

            if (data.success && data.novels && data.novels.length > 0) {
                this.renderShortDramaNovelList(data.novels);
            } else {
                document.getElementById('shortDramaNovelList').innerHTML =
                    '<div class="empty-state"><p>暂无可用小说</p></div>';
            }
        } catch (error) {
            console.error('加载小说列表失败:', error);
            document.getElementById('shortDramaNovelList').innerHTML =
                '<div class="empty-state"><p>加载失败: ' + error.message + '</p></div>';
        }
    }

    /**
     * 渲染短剧工作流的小说列表
     */
    renderShortDramaNovelList(novels) {
        const container = document.getElementById('shortDramaNovelList');
        if (!container) return;

        if (novels.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无可用小说</p>
                    <p class="hint">请先完成第一阶段设定生成</p>
                </div>
            `;
            return;
        }

        container.innerHTML = novels.map(novel => `
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
                </div>
                <button class="btn-primary select-novel-btn" data-novel="${novel.title || novel.novel_title}">
                    选择此小说
                </button>
            </div>
        `).join('');

        // 绑定选择小说按钮事件
        container.querySelectorAll('.select-novel-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const novelTitle = btn.dataset.novel;
                this.selectNovelForUnifiedWorkflow(novelTitle);
            });
        });
    }

    /**
     * 选择小说用于统一工作流
     */
    async selectNovelForUnifiedWorkflow(novelTitle) {
        console.log('📚 选择小说:', novelTitle);
        this.selectedNovel = novelTitle;

        // 更新UI
        document.getElementById('workflowNovelName').textContent = novelTitle;
        document.getElementById('shortDramaNovelSelector').style.display = 'none';
        document.getElementById('unifiedWorkflowSteps').style.display = 'block';

        // 加载事件和角色
        await this.loadEventsAndCharacters();

        // 显示开始按钮
        document.getElementById('startUnifiedWorkflowBtn').style.display = 'inline-block';
    }

    /**
     * 自动选择第一个小说并加载事件
     */
    async autoSelectFirstNovelAndLoadEvents() {
        try {
            // 加载小说列表
            const response = await fetch('/api/video/novels');
            const data = await response.json();

            if (data.success && data.novels && data.novels.length > 0) {
                // 选择第一个小说
                const firstNovel = data.novels[0];
                this.selectedNovel = firstNovel.title;
                console.log('🎭 自动选择小说:', this.selectedNovel);

                // 加载事件和角色
                await this.loadEventsAndCharacters();

                // 初始化工作流
                if (this.events.length > 0) {
                    await this.loadMajorEventsForWorkflow();
                    this.bindEpisodeWorkflowEvents();
                }

                // 更新标题
                const titleEl = document.getElementById('episodeWorkflowTitle');
                if (titleEl) {
                    titleEl.textContent = `🎭 ${this.selectedNovel} - 按集制作`;
                }
            }
        } catch (error) {
            console.error('初始化失败:', error);
        }
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
        // 检查是否已选择小说
        if (!this.selectedNovel) {
            this.showToast('请先从左侧选择小说！', 'warning');
            // 高亮左侧小说列表提示用户
            const sidebar = document.querySelector('.sidebar');
            sidebar.style.boxShadow = '0 0 20px rgba(255, 165, 0, 0.5)';
            setTimeout(() => {
                sidebar.style.boxShadow = '';
            }, 2000);
            return;
        }

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
        console.log('📚 当前小说:', this.selectedNovel);

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

        // 🔥 短剧模式：修改按钮文本和提示
        if (this.isShortDramaMode) {
            const confirmBtn = document.getElementById('confirmSelectionBtn');
            if (confirmBtn) {
                confirmBtn.textContent = '🎭 确认并进入短剧改造';
                confirmBtn.classList.remove('btn-primary');
                confirmBtn.classList.add('btn-success');
            }

            // 更新状态提示
            this.updateCurrentStatus(`🎭 短剧模式: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 选择要改编的事件`);
        } else {
            const confirmBtn = document.getElementById('confirmSelectionBtn');
            if (confirmBtn) {
                confirmBtn.textContent = '✅ 确认选择并生成提示词';
                confirmBtn.classList.remove('btn-success');
                confirmBtn.classList.add('btn-primary');
            }
            // 更新状态
            this.updateCurrentStatus(`已选择: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 选择事件和角色`);
        }

        // 加载事件和角色数据
        this.loadEventsAndCharacters();

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
                // 🔥 存储世界观数据用于角色生成
                this.worldview = data.worldview || {};
                console.log('🌍 已加载世界观数据:', this.worldview);

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
                                // 🔥 修复：直接使用 child.id，不再拼接
                                const childId = child.id;
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
        // 短剧模式：如果没有选择事件，自动选择前3个重大事件
        if (this.isShortDramaMode && this.selectedEvents.size === 0) {
            if (this.events.length > 0) {
                const autoSelectCount = Math.min(3, this.events.length);
                for (let i = 0; i < autoSelectCount; i++) {
                    this.selectedEvents.add(this.events[i].id);
                }
                this.renderEventsList();
                this.updateSelectionStats();
                this.showToast(`🎭 短剧模式：自动选择了前 ${autoSelectCount} 个事件`, 'success');
            }
        }

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

        // 隐藏帮助侧边栏，显示右侧分镜头
        document.getElementById('helpSidebar').style.display = 'none';
        document.getElementById('rightSidebar').style.display = 'none';

        // 更新状态
        this.updateCurrentStatus(`已选择: ${this.selectedNovel}<br>类型: ${typeName}<br>步骤: 查看提示词`);

        // 高亮第四步
        this.highlightWorkflowStep(4);
    }

    // ========== 统一工作流方法 ==========

    /**
     * 启动统一工作流
     */
    startUnifiedWorkflow() {
        console.log('🚀 启动统一工作流');
        this.workflowStep = 0;
        this.workflowData = {
            styleConversion: null,
            characterPortraits: null,
            storyboard: null,
            videos: null
        };

        // 切换到工作流屏幕
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('unifiedWorkflowScreen').style.display = 'block';

        // 隐藏侧边栏
        document.querySelector('.main-container').classList.add('hide-sidebar');
        document.getElementById('helpSidebar').style.display = 'none';

        this.showWorkflowStep(1);
    }

    /**
     * 显示工作流指定步骤
     */
    showWorkflowStep(step) {
        this.workflowStep = step;

        // 更新步骤指示器
        const steps = document.querySelectorAll('.step-indicator .step');
        steps.forEach((el, index) => {
            const stepNum = index + 1;
            el.classList.remove('active', 'completed');
            if (stepNum < step) {
                el.classList.add('completed');
            } else if (stepNum === step) {
                el.classList.add('active');
            }
        });

        // 更新步骤信息
        const stepInfo = WORKFLOW_STEPS[step];
        document.getElementById('currentStepTitle').textContent =
            `${stepInfo.icon} 步骤${step}: ${stepInfo.name}`;
        document.getElementById('currentStepDesc').textContent = stepInfo.description;

        // 更新标题
        const typeName = this.videoTypes[this.selectedType]?.name || this.selectedType;
        document.getElementById('workflowTitle').textContent =
            `🎬 ${this.selectedNovel} - ${typeName}`;

        // 重置结果显示区
        this.resetWorkflowResult();

        // 更新按钮状态
        this.updateWorkflowButtons();

        console.log(`📍 工作流：进入步骤${step} - ${stepInfo.name}`);
    }

    /**
     * 重置工作流结果显示区
     */
    resetWorkflowResult() {
        document.getElementById('workflowResultContent').innerHTML = `
            <div class="placeholder">
                <p>👆 点击"开始执行"开始步骤${this.workflowStep}</p>
            </div>
        `;
    }

    /**
     * 更新工作流按钮状态
     */
    updateWorkflowButtons() {
        const startBtn = document.getElementById('startWorkflowBtn');
        const continueBtn = document.getElementById('continueWorkflowBtn');
        const regenerateBtn = document.getElementById('regenerateStepBtn');
        const skipBtn = document.getElementById('skipStepBtn');

        // 默认状态：显示开始按钮
        startBtn.style.display = 'inline-block';
        continueBtn.style.display = 'none';
        regenerateBtn.style.display = 'none';
        skipBtn.style.display = 'none';

        // 根据步骤调整按钮文本
        const stepInfo = WORKFLOW_STEPS[this.workflowStep];
        startBtn.textContent = `🚀 开始${stepInfo.name}`;
    }

    /**
     * 执行当前工作流步骤
     */
    async executeWorkflowStep() {
        const step = this.workflowStep;
        console.log(`▶️ 执行工作流步骤${step}`);

        // 显示进度
        this.showWorkflowProgress(`正在执行${WORKFLOW_STEPS[step].name}...`);

        try {
            let result;
            switch(step) {
                case 1:
                    result = await this.executeStyleConversion();
                    break;
                case 2:
                    result = await this.executePortraitGeneration();
                    break;
                case 3:
                    result = await this.executeStoryboardGeneration();
                    break;
                case 4:
                    result = await this.executeVideoGeneration();
                    break;
                default:
                    throw new Error('未知的工作流步骤');
            }

            // 显示结果
            this.showWorkflowStepResult(step, result);

            // 更新按钮状态：显示继续按钮
            document.getElementById('startWorkflowBtn').style.display = 'none';
            document.getElementById('continueWorkflowBtn').style.display = 'inline-block';
            document.getElementById('regenerateStepBtn').style.display = 'inline-block';

            // 最后一步不显示跳过按钮
            if (step < 4) {
                document.getElementById('skipStepBtn').style.display = 'inline-block';
            }

            this.showToast(`✅ ${WORKFLOW_STEPS[step].name}完成！`, 'success');

        } catch (error) {
            console.error(`工作流步骤${step}执行失败:`, error);
            this.showToast(`❌ ${WORKFLOW_STEPS[step].name}失败: ${error.message}`, 'error');
            this.resetWorkflowResult();
        }
    }

    /**
     * 继续到下一步
     */
    continueToNextStep() {
        if (this.workflowStep < 4) {
            this.showWorkflowStep(this.workflowStep + 1);
        } else {
            // 工作流完成
            this.showToast('🎉 工作流全部完成！', 'success');
            // 可以跳转到视频预览或结果页面
        }
    }

    /**
     * 跳过当前步骤
     */
    skipCurrentStep() {
        this.showToast(`⏭️ 已跳过${WORKFLOW_STEPS[this.workflowStep].name}`, 'warning');
        if (this.workflowStep < 4) {
            this.showWorkflowStep(this.workflowStep + 1);
        }
    }

    /**
     * 显示工作流进度
     */
    showWorkflowProgress(message) {
        document.getElementById('workflowResultContent').innerHTML = `
            <div class="workflow-progress">
                <h4>${message}</h4>
                <div class="progress-container">
                    <div class="progress-bar-wrapper">
                        <div class="progress-bar-fill animate-progress" style="width: 0%"></div>
                    </div>
                    <span class="progress-text">0%</span>
                </div>
                <p class="status-text">请稍候...</p>
            </div>
        `;

        // 模拟进度更新
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress > 90) {
                clearInterval(progressInterval);
                progress = 90;
            }
            const fill = document.querySelector('.workflow-progress .progress-bar-fill');
            const text = document.querySelector('.workflow-progress .progress-text');
            if (fill) fill.style.width = `${progress}%`;
            if (text) text.textContent = `${Math.round(progress)}%`;
        }, 500);
    }

    /**
     * 显示工作流步骤结果
     */
    showWorkflowStepResult(step, data) {
        let resultHTML = '';

        switch(step) {
            case 1: // 风格转换结果
                resultHTML = this.renderStyleConversionResult(data);
                break;
            case 2: // 角色剧照结果
                resultHTML = this.renderPortraitResult(data);
                // 为剧照结果添加事件委托
                this._bindPortraitResultEvents();
                break;
            case 3: // 分镜头结果
                resultHTML = this.renderStoryboardResult(data);
                break;
            case 4: // 视频生成结果
                resultHTML = this.renderVideoResult(data);
                break;
        }

        document.getElementById('workflowResultContent').innerHTML = `
            <div class="workflow-step-result">
                <h4>✅ ${WORKFLOW_STEPS[step].name}完成</h4>
                ${resultHTML}
            </div>
        `;

        // 保存结果数据
        switch(step) {
            case 1:
                this.workflowData.styleConversion = data;
                break;
            case 2:
                this.workflowData.characterPortraits = data;
                break;
            case 3:
                this.workflowData.storyboard = data;
                this.shots = data.shots || [];
                break;
            case 4:
                this.workflowData.videos = data;
                break;
        }
    }

    /**
     * 为剧照结果添加事件绑定
     */
    _bindPortraitResultEvents() {
        const resultContainer = document.getElementById('workflowResultContent');
        if (!resultContainer) return;

        resultContainer.removeEventListener('click', this._handlePortraitAction);
        resultContainer.addEventListener('click', this._handlePortraitAction.bind(this));
    }

    /**
     * 处理剧照结果中的按钮点击事件
     */
    _handlePortraitAction(e) {
        const btn = e.target.closest('button[data-action]');
        if (!btn) return;

        const action = btn.dataset.action;
        const idx = btn.dataset.index;

        if (action === 'download') {
            const url = btn.dataset.url;
            this.downloadPortrait(url);
        } else if (action === 'retry') {
            const portraits = this.workflowData.characterPortraits?.portraits || [];
            if (portraits[idx]) {
                this.regeneratePortrait(portraits[idx], idx);
            }
        }
    }

    /**
     * 渲染风格转换结果
     */
    renderStyleConversionResult(data) {
        return `
            <div class="style-conversion-result">
                <div class="style-info">
                    <div class="info-block">
                        <label>视频类型</label>
                        <span>${data.videoType || this.videoTypes[this.selectedType]?.name}</span>
                    </div>
                    <div class="info-block">
                        <label>选中事件数</label>
                        <span>${data.eventCount || this.selectedEvents.size}个</span>
                    </div>
                    <div class="info-block">
                        <label>角色数</label>
                        <span>${data.characterCount || 0}个</span>
                    </div>
                </div>
                <div class="converted-text">
                    <strong>风格转换预览：</strong>
                    <p>${data.convertedPreview || '转换完成，内容已适配目标视频风格。'}</p>
                </div>
            </div>
        `;
    }

    /**
     * 渲染角色剧照结果
     */
    /**
     * 渲染角色剧照结果
     */
    renderPortraitResult(data) {
        const portraits = data.portraits || [];
        if (portraits.length === 0) {
            return '<p>暂无剧照数据</p>';
        }

        // 统计成功和失败的数量
        const successful = portraits.filter(p => p.imageUrl && !p.error).length;
        const failed = portraits.length - successful;

        let summaryHTML = '';
        if (failed > 0) {
            summaryHTML = `<p style="color: var(--warning-color);">⚠️ ${successful}个成功, ${failed}个失败</p>`;
        } else {
            summaryHTML = `<p style="color: var(--success-color);">✅ 全部 ${portraits.length} 个角色剧照生成成功！</p>`;
        }

        return `
            <div class="portrait-result">
                ${summaryHTML}
                ${portraits.map((p, idx) => `
                    <div class="portrait-item" data-character-id="${p.characterId}" data-index="${idx}">
                        ${p.imageUrl
                            ? `<img src="${p.imageUrl}" alt="${p.characterName}" onerror="this.src='/static/images/placeholder-avatar.png'">`
                            : `<div class="portrait-error">
                                <p>生成失败</p>
                                <small>${p.error || '未知错误'}</small>
                               </div>`
                        }
                        <div class="portrait-info">
                            <div class="character-name">${p.characterName}</div>
                            <div class="character-role">${p.characterRole || '角色'}</div>
                            ${p.imageUrl ? `
                                <div class="portrait-actions">
                                    <button class="btn-secondary btn-sm" data-action="retry" data-index="${idx}">🔄 重试</button>
                                    <button class="btn-primary btn-sm" data-action="download" data-url="${p.imageUrl}">📥 下载</button>
                                </div>
                            ` : `
                                <div class="portrait-actions">
                                    <button class="btn-secondary btn-sm" data-action="retry" data-index="${idx}">🔄 重试</button>
                                </div>
                            `}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * 渲染分镜头结果
     */
    renderStoryboardResult(data) {
        const shots = data.shots || [];
        const totalDuration = shots.reduce((sum, s) => sum + (s.duration_seconds || 10), 0);

        return `
            <div class="storyboard-result">
                <div class="storyboard-summary">
                    <div class="summary-item">
                        <div class="label">总镜头数</div>
                        <div class="value">${shots.length}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">总时长</div>
                        <div class="value">${Math.round(totalDuration / 60)}:${String(Math.round(totalDuration % 60)).padStart(2, '0')}</div>
                    </div>
                    <div class="summary-item">
                        <div class="label">已完成</div>
                        <div class="value">0/${shots.length}</div>
                    </div>
                </div>
                <div class="storyboard-list">
                    ${shots.slice(0, 10).map((shot, i) => `
                        <div class="shot-item">
                            <div class="shot-number">${i + 1}</div>
                            <div class="shot-content">
                                <div class="shot-description">${shot.scene_description || '暂无描述'}</div>
                                <div class="shot-meta">⏱️ ${shot.duration_seconds || 10}秒 | 🎬 ${shot.shot_type || '中景'}</div>
                            </div>
                        </div>
                    `).join('')}
                    ${shots.length > 10 ? `<p style="text-align: center; color: var(--text-secondary);">...还有 ${shots.length - 10} 个镜头</p>` : ''}
                </div>
            </div>
        `;
    }

    /**
     * 渲染视频生成结果
     */
    renderVideoResult(data) {
        return `
            <div class="video-result">
                <p>🎉 视频生成完成！</p>
                <div class="video-stats">
                    <div class="stat-item">
                        <span class="stat-label">成功生成:</span>
                        <span class="stat-value">${data.completedCount || 0}/${data.totalCount || 0}</span>
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 步骤1：执行风格转换
     */
    async executeStyleConversion() {
        console.log('🎨 执行风格转换...');

        const response = await fetch('/api/video/style-conversion', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: this.selectedNovel,
                video_type: this.selectedType,
                selected_events: Array.from(this.selectedEvents),
                selected_characters: Array.from(this.selectedCharacters)
            })
        });

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || '风格转换失败');
        }

        return {
            videoType: this.videoTypes[this.selectedType]?.name,
            eventCount: this.selectedEvents.size,
            characterCount: data.character_count || 0,
            convertedPreview: data.converted_preview || '风格转换完成'
        };
    }

    /**
     * 步骤2：执行角色剧照生成
     * 引导用户跳转到剧照工作台手动制作
     */
    async executePortraitGeneration() {
        console.log('📸 引导到剧照工作台...');

        // 获取需要生成剧照的角色列表
        const characters = this.deriveCharactersFromEvents();

        if (characters.length === 0) {
            this.showToast('没有找到需要生成剧照的角色', 'warning');
            return;
        }

        // 将角色信息保存到localStorage，供剧照工作台使用
        const workflowData = {
            novelTitle: this.selectedNovel,
            videoType: this.selectedType,
            characters: characters.map(c => ({
                id: c.name,
                name: c.name,
                role: c.role || '角色',
                appearance: c.appearance || '',
                prompt: c.generation_prompt || ''
            })),
            timestamp: Date.now()
        };

        localStorage.setItem('videoWorkflow_portraitData', JSON.stringify(workflowData));
        console.log('💾 已保存工作流数据到localStorage');

        // 显示引导界面
        const charactersList = characters.map((c, i) =>
            `<li><strong>${c.name}</strong> - ${c.role || '角色'}</li>`
        ).join('');

        document.getElementById('workflowResultContent').innerHTML = `
            <div class="portrait-guide">
                <h4>📸 角色剧照制作指南</h4>
                <p>为保持角色形象一致性，建议先在剧照工作台手动制作每个角色的固定剧照。</p>

                <div class="guide-info">
                    <h5>需要制作的角色 (${characters.length}个):</h5>
                    <ul>${charactersList}</ul>
                </div>

                <div class="guide-steps">
                    <h5>制作步骤：</h5>
                    <ol>
                        <li>点击下方按钮打开剧照工作台</li>
li>选择角色，输入提示词，生成剧照</li>
                        <li>满意后点击"固定为工作流剧照"按钮</li>
                        <li>所有角色完成后，返回继续工作流</li>
                    </ol>
                </div>

                <div class="guide-actions">
                    <button id="openPortraitStudioBtn" class="btn-primary btn-large">
                        🎨 打开剧照工作台
                    </button>
                    <button id="skipPortraitBtn" class="btn-secondary btn-large">
                        ⏭️ 跳过此步骤
                    </button>
                </div>

                <div class="fixed-portraits-status" id="fixedPortraitsStatus">
                    <p><strong>已固定的角色剧照：</strong> <span id="fixedPortraitCount">0</span>/${characters.length}</p>
                    <div id="fixedPortraitsList" class="fixed-portraits-list"></div>
                </div>
            </div>
        `;

        // 绑定按钮事件
        document.getElementById('openPortraitStudioBtn').addEventListener('click', () => {
            // 跳转到剧照工作台
            window.open('/portrait-studio?mode=workflow', '_blank');
        });

        document.getElementById('skipPortraitBtn').addEventListener('click', () => {
            this.skipCurrentStep();
        });

        // 检查已有的固定剧照
        this.checkFixedPortraits();

        // 轮询检查固定剧照状态
        this.portraitCheckInterval = setInterval(() => {
            this.checkFixedPortraits();
        }, 3000);

        // 返回部分结果（供UI使用）
        return {
            characters: characters,
            total: characters.length
        };
    }

    /**
     * 检查已固定的角色剧照
     */
    checkFixedPortraits() {
        const savedData = localStorage.getItem('videoWorkflow_portraitData');
        if (!savedData) return;

        const data = JSON.parse(savedData);
        const fixedPortraits = data.fixedPortraits || [];

        const countSpan = document.getElementById('fixedPortraitCount');
        const listDiv = document.getElementById('fixedPortraitsList');

        if (countSpan) countSpan.textContent = fixedPortraits.length;
        if (listDiv) {
            if (fixedPortraits.length === 0) {
                listDiv.innerHTML = '<p class="empty-hint">还没有固定的角色剧照</p>';
            } else {
                listDiv.innerHTML = fixedPortraits.map(p => `
                    <div class="fixed-portrait-item">
                        <img src="${p.imageUrl}" alt="${p.characterName}">
                        <span>${p.characterName}</span>
                        <button class="btn-sm btn-secondary" onclick="window.videoGenerator.removeFixedPortrait('${p.characterId}')">×</button>
                    </div>
                `).join('');
            }
        }

        // 如果所有角色都固定了，自动启用继续按钮
        if (fixedPortraits.length >= data.characters.length && this.portraitCheckInterval) {
            clearInterval(this.portraitCheckInterval);
            this.portraitCheckInterval = null;

            const continueBtn = document.getElementById('continueWorkflowBtn');
            if (continueBtn) {
                continueBtn.style.display = 'inline-block';
                document.getElementById('startWorkflowBtn').style.display = 'none';
                this.showToast('✅ 所有角色剧照已完成，可以继续下一步！', 'success');
            }
        }
    }

    /**
     * 移除已固定的角色剧照
     */
    removeFixedPortrait(characterId) {
        const savedData = localStorage.getItem('videoWorkflow_portraitData');
        if (!savedData) return;

        const data = JSON.parse(savedData);
        data.fixedPortraits = (data.fixedPortraits || []).filter(p => p.characterId !== characterId);
        localStorage.setItem('videoWorkflow_portraitData', JSON.stringify(data));

        this.checkFixedPortraits();
        this.showToast('已移除该角色的固定剧照', 'success');
    }

    /**
     * 步骤3：执行分镜头生成
     */
    async executeStoryboardGeneration() {
        console.log('🎬 执行分镜头生成...');

        const response = await fetch('/api/video/generate-storyboard', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: this.selectedNovel,
                video_type: this.selectedType,
                selected_events: Array.from(this.selectedEvents),
                use_workflow_portraits: true // 使用工作流生成的剧照
            })
        });

        const data = await response.json();
        if (!data.success) {
            throw new Error(data.error || '分镜头生成失败');
        }

        this.storyboard = data.storyboard;
        this.shots = data.shots || [];

        return data;
    }

    /**
     * 步骤4：执行视频生成
     */
    async executeVideoGeneration() {
        console.log('🎥 执行视频生成...');

        // 这里可以批量生成所有视频
        // 或者返回到分镜头列表页面让用户逐个生成

        return {
            completedCount: 0,
            totalCount: this.shots.length,
            message: '视频准备就绪，可以开始生成'
        };
    }

    /**
     * 下载剧照
     */
    downloadPortrait(imageUrl) {
        if (!imageUrl) {
            this.showToast('没有可下载的剧照', 'error');
            return;
        }

        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = 'portrait.png';
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.showToast('剧照下载已开始', 'success');
    }

    /**
     * 重新生成单个剧照
     */
    async regeneratePortrait(portraitData, index) {
        const charName = portraitData.characterName;
        this.showToast(`正在重新生成 ${charName} 的剧照...`, 'success');

        try {
            const response = await fetch('/api/video/generate-character-portrait', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    character_id: portraitData.characterId,
                    prompt: portraitData.prompt,
                    aspect_ratio: '9:16',
                    image_size: '4K'
                })
            });

            const data = await response.json();

            if (data.success) {
                // 更新UI
                const portraitItem = document.querySelector(`.portrait-item[data-index="${index}"]`);
                if (portraitItem) {
                    const img = portraitItem.querySelector('img');
                    const info = portraitItem.querySelector('.portrait-info');
                    const actions = portraitItem.querySelector('.portrait-actions');

                    if (img) {
                        img.src = data.image_url;
                    }
                    if (actions) {
                        actions.innerHTML = `
                            <button class="btn-secondary btn-sm" data-action="retry" data-index="${index}">🔄 重试</button>
                            <button class="btn-primary btn-sm" data-action="download" data-url="${data.image_url}">📥 下载</button>
                        `;
                    }

                    // 移除错误状态
                    portraitItem.classList.remove('error');
                }

                // 更新数据
                if (this.workflowData.characterPortraits) {
                    this.workflowData.characterPortraits.portraits[index] = {
                        ...portraitData,
                        imageUrl: data.image_url,
                        localPath: data.image_path
                    };
                }

                this.showToast(`${charName} 的剧照重新生成成功！`, 'success');
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('重新生成剧照失败:', error);
            this.showToast(`重新生成失败: ${error.message}`, 'error');
        }
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

        // ========== 统一工作流按钮绑定 ==========
        const startWorkflowFromPromptBtn = document.getElementById('startWorkflowFromPromptBtn');
        if (startWorkflowFromPromptBtn) {
            startWorkflowFromPromptBtn.addEventListener('click', () => {
                console.log('🚀 [按钮] 启动统一工作流');
                this.startUnifiedWorkflow();
            });
        }

        // ========== 按集制作工作流按钮绑定 ==========
        const startEpisodeWorkflowBtn = document.getElementById('startEpisodeWorkflowBtn');
        if (startEpisodeWorkflowBtn) {
            startEpisodeWorkflowBtn.addEventListener('click', () => {
                console.log('📺 [按钮] 启动按集制作工作流');
                this.startEpisodeWorkflow();
            });
        }

        const startWorkflowBtn = document.getElementById('startWorkflowBtn');
        if (startWorkflowBtn) {
            startWorkflowBtn.addEventListener('click', () => {
                this.executeWorkflowStep();
            });
        }

        const continueWorkflowBtn = document.getElementById('continueWorkflowBtn');
        if (continueWorkflowBtn) {
            continueWorkflowBtn.addEventListener('click', () => {
                this.continueToNextStep();
            });
        }

        const skipStepBtn = document.getElementById('skipStepBtn');
        if (skipStepBtn) {
            skipStepBtn.addEventListener('click', () => {
                this.skipCurrentStep();
            });
        }

        const regenerateStepBtn = document.getElementById('regenerateStepBtn');
        if (regenerateStepBtn) {
            regenerateStepBtn.addEventListener('click', () => {
                this.executeWorkflowStep();
            });
        }

        const backToTypesFromWorkflowBtn = document.getElementById('backToTypesFromWorkflowBtn');
        if (backToTypesFromWorkflowBtn) {
            backToTypesFromWorkflowBtn.addEventListener('click', () => {
                document.getElementById('unifiedWorkflowScreen').style.display = 'none';
                document.getElementById('promptPreviewScreen').style.display = 'block';
                document.querySelector('.main-container').classList.remove('hide-sidebar');
                document.getElementById('helpSidebar').style.display = 'block';
            });
        }
        // ========== 统一工作流按钮绑定结束 ==========

        // 短剧风格改造按钮（已废弃，保留用于兼容）
        console.log('🔍 [绑定] 开始查找 adaptToShortDramaBtn 按钮...');
        const adaptToShortDramaBtn = document.getElementById('adaptToShortDramaBtn');
        console.log('🔍 [绑定] 按钮元素:', adaptToShortDramaBtn);

        if (adaptToShortDramaBtn) {
            console.log('✅ [绑定] 找到 adaptToShortDramaBtn 按钮，开始绑定事件');

            // 移除旧的事件监听器（如果有）
            const newAdaptBtn = adaptToShortDramaBtn.cloneNode(true);
            adaptToShortDramaBtn.parentNode.replaceChild(newAdaptBtn, adaptToShortDramaBtn);

            newAdaptBtn.addEventListener('click', (e) => {
                console.log('='.repeat(60));
                console.log('🎭 [按钮] adaptToShortDramaBtn 被点击!');
                console.log('📊 [按钮] this.isShortDramaMode:', this.isShortDramaMode);
                console.log('📊 [按钮] this.selectedNovel:', this.selectedNovel);
                console.log('📊 [按钮] this.selectedType:', this.selectedType);
                console.log('='.repeat(60));

                // 防止默认行为
                e.preventDefault();
                e.stopPropagation();

                // 短剧模式：直接生成分镜头脚本
                this.showToast('🎭 开始短剧风格改造...', 'success');
                this.generateStoryboard();
            });

            console.log('✅ [绑定] 短剧改造按钮事件绑定完成');
        } else {
            console.log('⚠️ [绑定] 未找到 adaptToShortDramaBtn 按钮（可能在非短剧模式下）');
        }

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

    // ========== 按集制作工作流方法 ==========

    /**
     * 启动按集制作工作流
     */
    async startEpisodeWorkflow() {
        console.log('📺 启动按集制作工作流');

        // 🔥 清空之前的剧照数据
        if (this.episodeWorkflow?.characterPortraits) {
            this.episodeWorkflow.characterPortraits.clear();
        }
        localStorage.removeItem('episodeWorkflow_characterPortraits');

        // 初始化工作流数据
        this.episodeWorkflow = {
            step: 'select-episodes',
            selectedMajorEvent: null,
            selectedEpisodes: new Set(),
            characterPortraits: new Map(), // characterId -> portraitData
            storyboardData: null,
            videoData: null
        };

        // 🔥 从localStorage恢复之前的剧照数据
        this.restoreCharacterPortraits();

        // 切换到按集制作屏幕
        document.getElementById('promptPreviewScreen').style.display = 'none';
        document.getElementById('episodeWorkflowScreen').style.display = 'block';

        // 隐藏侧边栏
        document.querySelector('.main-container').classList.add('hide-sidebar');
        document.getElementById('helpSidebar').style.display = 'none';

        // 更新标题
        document.getElementById('episodeWorkflowTitle').textContent =
            `📺 ${this.selectedNovel} - 按集制作`;

        // 确保事件和角色已加载（修复：同时检查events和characters）
        if (this.events.length === 0 || this.characters.length === 0) {
            console.log('📺 事件或角色未加载，先加载...');
            console.log(`📺 当前状态: events=${this.events.length}, characters=${this.characters.length}`);
            await this.loadEventsAndCharacters();
        } else {
            console.log(`📺 已有数据: events=${this.events.length}, characters=${this.characters.length}`);
        }

        // 加载重大事件列表（使用await确保完成）
        await this.loadMajorEventsForWorkflow();

        // 绑定工作流事件
        this.bindEpisodeWorkflowEvents();

        // 显示第一步
        this.showEpisodeWorkflowStep('select-episodes');
    }

    /**
     * 加载重大事件列表
     */
    async loadMajorEventsForWorkflow() {
        const container = document.getElementById('majorEventList');
        container.innerHTML = '<div class="loading">加载中...</div>';

        try {
            console.log('📺 加载重大事件, this.events.length:', this.events.length);
            console.log('📺 this.events:', this.events);

            // 从已加载的事件中获取重大事件
            const majorEvents = this.events.filter(e => e.type === 'major' || e.has_children);

            console.log('📺 筛选后的重大事件:', majorEvents.length);

            if (majorEvents.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>暂无重大事件</p>
                        <p class="hint">请先在小说中配置事件系统</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = majorEvents.map((event, idx) => `
                <div class="major-event-option" data-event-id="${event.id}">
                    <div class="event-name">${event.title || event.name || `重大事件 ${idx + 1}`}</div>
                    <div class="event-info">
                        <span class="episode-count">${event.children_count || event.children?.length || 0} 集</span>
                        <span>${event.description?.substring(0, 50) || ''}${event.description?.length > 50 ? '...' : ''}</span>
                    </div>
                </div>
            `).join('');

            console.log('📺 已渲染重大事件列表');
            console.log('📺 重大事件加载完成（点击事件通过事件委托处理）');

        } catch (error) {
            console.error('加载重大事件失败:', error);
            container.innerHTML = `
                <div class="empty-state">
                    <p>加载失败</p>
                    <p class="hint">${error.message}</p>
                </div>
            `;
        }
    }

    /**
     * 选择重大事件
     */
    selectMajorEventForWorkflow(eventId) {
        console.log('📺 选择重大事件:', eventId);
        console.log('📺 可用事件:', this.events.map(e => ({ id: e.id, title: e.title, hasChildren: e.children?.length })));

        const event = this.events.find(e => e.id === eventId);
        if (!event) {
            console.error('📺 找不到事件:', eventId);
            this.showToast('找不到事件数据', 'error');
            return;
        }

        console.log('📺 找到事件:', event);

        // 更新选中状态
        document.querySelectorAll('.major-event-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        const selectedOption = document.querySelector(`.major-event-option[data-event-id="${eventId}"]`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
        }

        this.episodeWorkflow.selectedMajorEvent = event;

        // 显示集数列表
        this.showEpisodeList(event);
    }

    /**
     * 显示集数列表（中级事件）
     */
    showEpisodeList(majorEvent) {
        console.log('📺 显示集数列表, 重大事件:', majorEvent);

        const selector = document.getElementById('episodeSelector');
        const container = document.getElementById('episodeList');
        const nameSpan = document.getElementById('selectedMajorEventName');

        nameSpan.textContent = `- ${majorEvent.title || majorEvent.name}`;
        selector.style.display = 'block';

        const episodes = majorEvent.children || [];
        console.log('📺 集数列表:', episodes);

        if (episodes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>该重大事件下没有中级事件</p>
                </div>
            `;
            return;
        }

        container.innerHTML = episodes.map((ep, idx) => `
            <div class="episode-item" data-episode-id="${ep.id}">
                <input type="checkbox" class="episode-checkbox" id="ep_${idx}">
                <span class="episode-number">第${idx + 1}集</span>
                <span class="episode-title">${ep.title || ep.name || `集数 ${idx + 1}`}</span>
                <span class="episode-stage">${ep.stage || ''}</span>
            </div>
        `).join('');

        console.log('📺 已渲染集数列表');

        // 绑定点击事件
        container.querySelectorAll('.episode-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (e.target.classList.contains('episode-checkbox')) return;
                const checkbox = item.querySelector('.episode-checkbox');
                checkbox.checked = !checkbox.checked;
                this.toggleEpisodeSelection(item.dataset.episodeId, checkbox.checked);
            });
        });

        container.querySelectorAll('.episode-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const item = e.target.closest('.episode-item');
                this.toggleEpisodeSelection(item.dataset.episodeId, e.target.checked);
            });
        });
    }

    /**
     * 切换集数选择状态
     */
    toggleEpisodeSelection(episodeId, selected) {
        if (selected) {
            this.episodeWorkflow.selectedEpisodes.add(episodeId);
        } else {
            this.episodeWorkflow.selectedEpisodes.delete(episodeId);
        }

        // 更新选中项样式
        const item = document.querySelector(`.episode-item[data-episode-id="${episodeId}"]`);
        if (item) {
            item.classList.toggle('selected', selected);
        }

        // 更新计数
        document.getElementById('selectedEpisodesCount').textContent =
            this.episodeWorkflow.selectedEpisodes.size;
    }

    /**
     * 绑定按集制作工作流事件
     */
    bindEpisodeWorkflowEvents() {
        // 使用事件委托处理重大事件点击（支持动态添加的元素）
        const majorEventList = document.getElementById('majorEventList');
        if (majorEventList) {
            // 移除旧的监听器（如果存在）
            majorEventList.removeEventListener('click', this._handleMajorEventClick);
            // 添加新的监听器
            this._handleMajorEventClick = (e) => {
                const option = e.target.closest('.major-event-option');
                if (option) {
                    console.log('📺 通过事件委托点击了重大事件:', option.dataset.eventId);
                    this.selectMajorEventForWorkflow(option.dataset.eventId);
                }
            };
            majorEventList.addEventListener('click', this._handleMajorEventClick);
            console.log('📺 已设置重大事件点击委托');
        }

        // 导航按钮
        document.querySelectorAll('.workflow-nav-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const step = btn.dataset.step;
                this.showEpisodeWorkflowStep(step);
            });
        });

        // 返回按钮
        document.getElementById('backToModeFromEpisodeBtn')?.addEventListener('click', () => {
            this.showModeSelectionScreen();
        });

        // 全选/清空按钮
        document.getElementById('selectAllEpisodesBtn')?.addEventListener('click', () => {
            document.querySelectorAll('.episode-checkbox').forEach(cb => {
                cb.checked = true;
                const item = cb.closest('.episode-item');
                this.toggleEpisodeSelection(item.dataset.episodeId, true);
            });
        });

        document.getElementById('clearEpisodesBtn')?.addEventListener('click', () => {
            document.querySelectorAll('.episode-checkbox').forEach(cb => {
                cb.checked = false;
                const item = cb.closest('.episode-item');
                this.toggleEpisodeSelection(item.dataset.episodeId, false);
            });
        });

        // 底部操作按钮
        document.getElementById('episodePrevBtn')?.addEventListener('click', () => {
            this.episodeWorkflowPrev();
        });

        document.getElementById('episodeNextBtn')?.addEventListener('click', () => {
            this.episodeWorkflowNext();
        });

        document.getElementById('episodeGenerateBtn')?.addEventListener('click', () => {
            this.executeEpisodeGeneration();
        });

        // 🔥 刷新剧照按钮
        document.getElementById('refreshPortraitsBtn')?.addEventListener('click', async () => {
            console.log('📺 [刷新按钮] 用户点击刷新按钮');
            this.checkPortraitStudioResult();

            // 🔥 自动发现视频项目中的剧照
            await this.discoverPortraits();

            this.loadCharacterPortraitsStep();
        });
    }

    /**
     * 显示工作流步骤
     */
    showEpisodeWorkflowStep(step) {
        // 更新导航状态
        document.querySelectorAll('.workflow-nav-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.step === step) {
                btn.classList.add('active');
            }
        });

        // 更新面板显示
        document.querySelectorAll('.workflow-step-panel').forEach(panel => {
            panel.classList.remove('active');
        });

        const stepMap = {
            'select-episodes': 'episodeStep1',
            'check-portraits': 'episodeStep2',
            'generate-storyboard': 'episodeStep3',
            'generate-video': 'episodeStep4'
        };

        const panelId = stepMap[step];
        if (panelId) {
            document.getElementById(panelId).classList.add('active');
        }

        // 更新按钮状态
        this.updateEpisodeWorkflowButtons(step);

        // 根据步骤加载内容
        switch(step) {
            case 'check-portraits':
                this.loadCharacterPortraitsStep();
                break;
            case 'generate-storyboard':
                this.loadStoryboardStep();
                break;
            case 'generate-video':
                this.loadVideoStep();
                break;
        }

        this.episodeWorkflow.step = step;
    }

    /**
     * 更新工作流按钮
     */
    updateEpisodeWorkflowButtons(step) {
        const prevBtn = document.getElementById('episodePrevBtn');
        const nextBtn = document.getElementById('episodeNextBtn');
        const generateBtn = document.getElementById('episodeGenerateBtn');

        const steps = ['select-episodes', 'check-portraits', 'generate-storyboard', 'generate-video'];
        const currentIndex = steps.indexOf(step);

        // 显示/隐藏上一步按钮
        prevBtn.style.display = currentIndex > 0 ? 'inline-block' : 'none';

        // 最后一步显示生成按钮，其他显示下一步
        if (step === 'generate-video') {
            nextBtn.style.display = 'none';
            generateBtn.style.display = 'inline-block';
        } else {
            nextBtn.style.display = 'inline-block';
            generateBtn.style.display = 'none';
        }
    }

    /**
     * 加载角色剧照步骤
     */
    loadCharacterPortraitsStep() {
        const container = document.getElementById('episodeCharacterPortraits');
        if (!container) return;

        // 🔥 检查 episodeWorkflow 是否已初始化
        if (!this.episodeWorkflow) {
            console.log('📺 [剧照步骤] episodeWorkflow 未初始化，跳过加载');
            return;
        }

        container.innerHTML = '<div class="loading">加载角色信息...</div>';

        console.log('📺 [剧照步骤] 加载角色剧照步骤');
        console.log('📺 [剧照步骤] 选中的集数:', this.episodeWorkflow.selectedEpisodes);
        console.log('📺 [剧照步骤] 全局角色数量:', this.characters?.length || 0);

        // 🔥 检查是否有从剧照工作室返回的结果
        this.checkPortraitStudioResult();

        // 从选中的集中提取角色
        const characters = this.extractCharactersFromEpisodes();

        console.log('📺 [剧照步骤] 提取到的角色数量:', characters.length);

        if (characters.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>没有找到角色</p>
                    <p class="hint">选中的集数中没有角色信息，且全局角色列表为空</p>
                </div>
            `;
            return;
        }

        // 🔥 美化的头部区域
        const headerHtml = `
            <div class="character-portraits-header" style="
                display: flex; justify-content: space-between; align-items: center;
                padding: 1rem; background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-secondary) 100%);
                border-radius: 12px; margin-bottom: 1.5rem; border: 1px solid var(--border-color);
            ">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="
                        width: 40px; height: 40px; background: var(--accent-color);
                        border-radius: 10px; display: flex; align-items: center; justify-content: center;
                        font-size: 1.2rem;
                    ">👥</div>
                    <div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary);">角色列表</div>
                        <div style="font-size: 1.1rem; font-weight: 600;">
                            已加载 <strong style="color: var(--accent-color);">${characters.length}</strong> 个角色
                        </div>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="text-align: right;">
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">剧照进度</div>
                        <div id="portraitStatusCount" style="font-size: 1.1rem; font-weight: 600; color: var(--primary-color);">0/${characters.length}</div>
                    </div>
                    <button id="addCharacterBtn" class="btn-primary" style="
                        display: flex; align-items: center; gap: 0.5rem;
                        padding: 0.6rem 1rem; border-radius: 8px; font-size: 0.9rem;
                        cursor: pointer; border: none;
                    ">
                        <span>➕</span>
                        <span>添加角色</span>
                    </button>
                </div>
            </div>
            <div class="character-portraits-grid" style="
                display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 1rem; max-height: 550px; overflow-y: auto; padding: 0;
            ">
        `;

        const cardsHtml = characters.map(char => {
            const hasPortrait = this.episodeWorkflow.characterPortraits.has(char.name);
            const portrait = hasPortrait ? this.episodeWorkflow.characterPortraits.get(char.name) : null;
            return `
                <div class="character-portrait-card ${hasPortrait ? 'has-portrait' : 'missing-portrait'}" data-character-id="${char.name}" style="
                    width: 120px; position: relative; overflow: hidden;
                ">
                    <div class="portrait-image-wrapper" style="
                        width: 120px; height: 160px; position: relative;
                        background: linear-gradient(180deg, var(--bg-tertiary) 0%, var(--bg-dark) 100%);
                        border-radius: 12px; overflow: hidden; border: 2px solid ${hasPortrait ? 'var(--primary-color)' : 'var(--border-color)'};
                    ">
                        ${hasPortrait
                            ? `<img src="${portrait.imageUrl}" alt="${char.name}" data-full-url="${portrait.imageUrl}" style="width: 100%; height: 100%; object-fit: cover;" />`
                            : `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-dark) 100%);">
                                <span style="font-size: 3rem; opacity: 0.3;">👤</span>
                               </div>`
                        }
                        <div class="status-badge" style="
                            position: absolute; top: 8px; right: 8px;
                            padding: 0.25rem 0.5rem; border-radius: 6px; font-size: 0.7rem; font-weight: 600;
                            background: ${hasPortrait ? 'var(--success-color, #22c55e)' : 'var(--warning-color, #f59e0b)'};
                            color: white; backdrop-filter: blur(4px);
                        ">${hasPortrait ? '✓' : '待生成'}</div>
                    </div>
                    <div class="portrait-name" style="
                        margin-top: 0.5rem; text-align: center;
                    ">
                        <div style="
                            font-weight: 600; font-size: 0.9rem; color: var(--text-primary);
                            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                            padding: 0 0.25rem;
                        " title="${char.name}">${char.name}</div>
                        ${char.role ? `<div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.1rem;">${char.role}</div>` : ''}
                    </div>
                    <div class="portrait-actions" style="
                        margin-top: 0.5rem; display: flex; gap: 0.25rem;
                    ">
                        ${hasPortrait
                            ? `<button class="btn-action" data-action="view" style="flex: 1; padding: 0.4rem; font-size: 0.8rem; background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);">查看</button>
                               <button class="btn-action" data-action="new-look" style="flex: 1; padding: 0.4rem; font-size: 0.8rem; background: var(--accent-color); border: none; border-radius: 6px; color: white;">新造型</button>`
                            : `<button class="btn-action" data-action="generate" style="width: 100%; padding: 0.5rem; font-size: 0.85rem; background: var(--primary-color); border: none; border-radius: 6px; color: white; font-weight: 500;">📸 生成剧照</button>`
                        }
                    </div>
                </div>
            `;
        }).join('') + `
            </div>
        `;

        // 🔥 设置容器HTML
        container.innerHTML = headerHtml + cardsHtml;

        // 🔥 清除容器的grid样式（现在grid在子容器中）
        container.style.display = 'block';
        container.style.maxHeight = 'none';
        container.style.overflowY = 'visible';
        container.style.padding = '0';

        // 更新统计
        const readyCount = characters.filter(c => this.episodeWorkflow.characterPortraits.has(c.name)).length;
        const portraitStatusCount = document.getElementById('portraitStatusCount');
        if (portraitStatusCount) {
            portraitStatusCount.textContent = `${readyCount}/${characters.length}`;
        }

        // 绑定按钮点击事件
        container.querySelectorAll('.btn-action').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const card = btn.closest('.character-portrait-card');
                const characterId = card.dataset.characterId;
                const action = btn.dataset.action;
                this.handlePortraitAction(action, characterId, characters.find(c => c.name === characterId));
            });
        });

        // 🔥 绑定卡片点击事件（放大查看剧照）
        container.querySelectorAll('.character-portrait-card.has-portrait').forEach(card => {
            card.style.cursor = 'pointer';
            card.addEventListener('click', (e) => {
                if (e.target.classList.contains('btn-action')) return;
                const characterId = card.dataset.characterId;
                const character = characters.find(c => c.name === characterId);
                const portrait = this.episodeWorkflow.characterPortraits.get(characterId);
                if (portrait) {
                    this.openPortraitModal(character, portrait);
                }
            });
        });

        // 🔥 绑定"添加角色"按钮事件
        const addCharacterBtn = document.getElementById('addCharacterBtn');
        if (addCharacterBtn) {
            addCharacterBtn.addEventListener('click', () => {
                this.showAddCharacterDialog();
            });
        }
    }

    /**
     * 🔶 显示添加角色对话框
     */
    showAddCharacterDialog() {
        const modalId = 'addCharacterModal';
        let modal = document.getElementById(modalId);

        if (!modal) {
            modal = document.createElement('div');
            modal.id = modalId;
            modal.className = 'modal-overlay';
            modal.style.cssText = `
                position: fixed; top: 0; left: 0; right: 0; bottom: 0;
                background: rgba(0,0,0,0.7); display: none;
                justify-content: center; align-items: center; z-index: 10000;
            `;
            document.body.appendChild(modal);
        }

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-primary); border-radius: 16px;
                max-width: 500px; width: 90%; max-height: 85vh;
                display: flex; flex-direction: column;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
                overflow: hidden; color: var(--text-primary);
            ">
                <!-- 头部 -->
                <div style="
                    padding: 1.5rem; background: linear-gradient(135deg, var(--accent-color) 0%, #6366f1 100%);
                    border-bottom: none;
                ">
                    <h2 style="margin: 0; display: flex; align-items: center; gap: 0.5rem; color: white; font-size: 1.3rem;">
                        <span>➕</span>
                        <span>添加新角色</span>
                    </h2>
                    <p style="margin: 0.5rem 0 0; color: rgba(255,255,255,0.9); font-size: 0.9rem;">
                        输入角色名，AI将根据小说背景自动生成角色描述
                    </p>
                </div>

                <!-- 内容区 -->
                <div style="padding: 1.5rem; overflow-y: auto; flex: 1; color: var(--text-primary);">
                    <!-- 角色名输入 -->
                    <div style="margin-bottom: 1.25rem;">
                        <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem; font-weight: 500;">
                            角色名 <span style="color: var(--accent-color);">*</span>
                        </label>
                        <input type="text" id="newCharNameInput" placeholder="如：林啸天、三长老" style="
                            width: 100%; padding: 0.75rem 1rem; border: 2px solid var(--border-color);
                            border-radius: 10px; background: var(--bg-primary); font-size: 1rem; color: var(--text-primary);
                            transition: all 0.2s;
                        " onfocus="this.style.borderColor='var(--accent-color)'" onblur="this.style.borderColor='var(--border-color)'" />
                    </div>

                    <!-- AI生成按钮 -->
                    <div style="text-align: center; margin: 1.5rem 0;">
                        <button id="aiGenerateDescBtn" class="btn-secondary" style="
                            width: 100%; padding: 0.75rem; border-radius: 10px;
                            font-size: 0.95rem; display: flex; align-items: center; justify-content: center; gap: 0.5rem;
                        ">
                            <span>🤖</span>
                            <span>AI生成角色描述</span>
                        </button>
                        <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem;">
                            点击后AI将根据角色名和小说背景自动生成详细描述
                        </p>
                    </div>

                    <!-- AI生成的字段 -->
                    <div id="aiGeneratedFields" style="display: none;">
                        <div style="
                            padding: 1rem; background: var(--bg-tertiary); border-radius: 10px;
                            margin-bottom: 1rem; border-left: 3px solid var(--accent-color);
                        ">
                            <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                                ✨ AI已生成角色档案，您可以根据需要修改
                            </div>
                        </div>

                        <!-- 角色定位 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">角色定位</label>
                            <select id="newCharRole" style="
                                width: 100%; padding: 0.6rem 1rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); color: var(--text-primary);
                            ">
                                <option value="" style="color: var(--text-primary);">请选择</option>
                                <option value="主角" style="color: var(--text-primary);">主角</option>
                                <option value="配角" style="color: var(--text-primary);">配角</option>
                                <option value="反派" style="color: var(--text-primary);">反派</option>
                                <option value="导师" style="color: var(--text-primary);">导师</option>
                                <option value="长者" style="color: var(--text-primary);">长者</option>
                                <option value="路人" style="color: var(--text-primary);">路人</option>
                            </select>
                        </div>

                        <!-- 角色背景 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">角色背景</label>
                            <textarea id="newCharBackground" rows="3" placeholder="身世、经历、动机等背景信息" style="
                                width: 100%; padding: 0.75rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); resize: vertical; font-size: 0.9rem; color: var(--text-primary);
                            "></textarea>
                        </div>

                        <!-- 性别 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">性别</label>
                            <select id="newCharGender" style="
                                width: 100%; padding: 0.6rem 1rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); color: var(--text-primary);
                            ">
                                <option value="" style="color: var(--text-primary);">请选择</option>
                                <option value="男" style="color: var(--text-primary);">男</option>
                                <option value="女" style="color: var(--text-primary);">女</option>
                            </select>
                        </div>

                        <!-- 年龄 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">年龄</label>
                            <input type="text" id="newCharAge" placeholder="如：50岁左右、中年" style="
                                width: 100%; padding: 0.6rem 1rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); color: var(--text-primary);
                            " />
                        </div>

                        <!-- 外貌描述 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">外貌描述</label>
                            <textarea id="newCharAppearance" rows="4" placeholder="AI将自动生成，也可手动编辑" style="
                                width: 100%; padding: 0.75rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); resize: vertical; font-size: 0.9rem; color: var(--text-primary);
                            "></textarea>
                        </div>

                        <!-- 性格特点 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">性格特点</label>
                            <input type="text" id="newCharPersonality" placeholder="如：威严、果断、温和等" style="
                                width: 100%; padding: 0.6rem 1rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); color: var(--text-primary);
                            " />
                        </div>

                        <!-- 出场事件/原因 -->
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">出场原因</label>
                            <textarea id="newCharAppearingEvent" rows="2" placeholder="该角色在当前事件中出现的原因" style="
                                width: 100%; padding: 0.75rem; border: 2px solid var(--border-color);
                                border-radius: 10px; background: var(--bg-primary); resize: vertical; font-size: 0.9rem; color: var(--text-primary);
                            "></textarea>
                        </div>
                    </div>
                </div>

                <!-- 底部按钮 -->
                <div style="padding: 1rem 1.5rem; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; gap: 0.75rem; background: var(--bg-secondary);">
                    <button id="closeAddCharModalBtn" style="
                        padding: 0.6rem 1.5rem; border-radius: 8px; font-size: 0.9rem;
                    " class="btn-secondary">取消</button>
                    <button id="saveNewCharBtn" class="btn-primary" disabled style="
                        padding: 0.6rem 1.5rem; border-radius: 8px; font-size: 0.9rem;
                        opacity: 0.5; cursor: not-allowed;
                    ">💾 保存角色</button>
                </div>
            </div>
        `;

        modal.style.display = 'flex';

        // 绑定事件
        const nameInput = modal.querySelector('#newCharNameInput');
        const aiGenerateBtn = modal.querySelector('#aiGenerateDescBtn');
        const saveBtn = modal.querySelector('#saveNewCharBtn');
        const closeBtn = modal.querySelector('#closeAddCharModalBtn');
        const aiFields = modal.querySelector('#aiGeneratedFields');

        // 名字输入时启用保存按钮
        nameInput.addEventListener('input', () => {
            const hasValue = nameInput.value.trim().length > 0;
            saveBtn.disabled = !hasValue;
            saveBtn.style.opacity = hasValue ? '1' : '0.5';
            saveBtn.style.cursor = hasValue ? 'pointer' : 'not-allowed';
        });

        // AI生成按钮
        aiGenerateBtn.addEventListener('click', async () => {
            const characterName = nameInput.value.trim();
            if (!characterName) {
                this.showToast('请先输入角色名', 'error');
                return;
            }

            aiGenerateBtn.disabled = true;
            aiGenerateBtn.innerHTML = '<span>🔄</span><span>生成中...</span>';

            try {
                // 🔥 构建增强的上下文信息
                let enhancedContext = `角色名: ${characterName}\n`;

                // 添加世界观数据
                if (this.worldview) {
                    if (this.worldview.quality_data) {
                        const qd = this.worldview.quality_data;
                        if (qd.theme) enhancedContext += `\n主题: ${qd.theme}`;
                        if (qd.tone) enhancedContext += `\n基调: ${qd.tone}`;
                        if (qd.genre) enhancedContext += `\n类型: ${qd.genre}`;
                        if (qd.worldview) enhancedContext += `\n世界观: ${qd.worldview}`;
                    }
                    if (this.worldview.core_worldview) {
                        const cw = this.worldview.core_worldview;
                        if (cw.worldview_name) enhancedContext += `\n核心世界观: ${cw.worldview_name}`;
                        if (cw.core_power) enhancedContext += `\n核心力量: ${cw.core_power}`;
                    }
                    if (this.worldview.novel_description) enhancedContext += `\n小说描述: ${this.worldview.novel_description}`;
                    if (this.worldview.novel_premise) enhancedContext += `\n故事前提: ${this.worldview.novel_premise}`;
                }

                // 添加现有角色信息
                if (this.characters && this.characters.length > 0) {
                    enhancedContext += `\n\n现有角色:\n`;
                    this.characters.forEach(char => {
                        enhancedContext += `- ${char.name}${char.role ? '(' + char.role + ')' : ''}: ${char.description || ''}\n`;
                    });
                }

                // 添加当前选中的事件上下文（如果是从某个事件添加角色）
                const selectedEventIds = Array.from(this.selectedEvents);
                if (selectedEventIds.length > 0) {
                    const selectedEvent = this.events.find(e => e.id === selectedEventIds[0]) ||
                                          this.events.flatMap(e => e.children || []).find(c => c.id === selectedEventIds[0]);
                    if (selectedEvent) {
                        enhancedContext += `\n\n当前事件: ${selectedEvent.title || selectedEvent.name || '未命名事件'}`;
                        if (selectedEvent.description) enhancedContext += `\n事件描述: ${selectedEvent.description}`;
                        if (selectedEvent.stage) enhancedContext += `\n阶段: ${selectedEvent.stage}`;
                    }
                }

                console.log('🔍 角色生成上下文:', enhancedContext);

                const response = await fetch('/api/characters/generate-description', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        novel_title: this.selectedNovel,
                        character_name: characterName,
                        context: enhancedContext
                    })
                });

                const result = await response.json();
                if (result.success && result.description) {
                    // 🔥 解析完整的角色数据
                    const characterData = result.character_data || {};

                    // 填充各字段
                    if (characterData.description || result.description) {
                        modal.querySelector('#newCharAppearance').value = characterData.description || result.description;
                    }
                    if (characterData.gender) {
                        modal.querySelector('#newCharGender').value = characterData.gender;
                    } else {
                        // 尝试从描述中提取性别
                        const desc = result.description;
                        if (desc.includes('男') || desc.includes('先生') || desc.includes('老先生') || desc.includes('族长') || desc.includes('父亲') || desc.includes('长老')) {
                            modal.querySelector('#newCharGender').value = '男';
                        } else if (desc.includes('女') || desc.includes('小姐') || desc.includes('女士') || desc.includes('母亲') || desc.includes('夫人')) {
                            modal.querySelector('#newCharGender').value = '女';
                        }
                    }
                    if (characterData.age) {
                        modal.querySelector('#newCharAge').value = characterData.age;
                    } else {
                        const ageMatch = result.description.match(/(\d+岁|中年|青年|老年|少年|少女|儿童)/);
                        if (ageMatch) {
                            modal.querySelector('#newCharAge').value = ageMatch[1];
                        }
                    }
                    if (characterData.personality) {
                        modal.querySelector('#newCharPersonality').value = characterData.personality;
                    }
                    if (characterData.role) {
                        modal.querySelector('#newCharRole').value = characterData.role;
                    }
                    if (characterData.background) {
                        modal.querySelector('#newCharBackground').value = characterData.background;
                    }
                    if (characterData.appearing_event) {
                        modal.querySelector('#newCharAppearingEvent').value = characterData.appearing_event;
                    }

                    // 显示字段
                    aiFields.style.display = 'block';
                    saveBtn.disabled = false;
                    saveBtn.style.opacity = '1';
                    saveBtn.style.cursor = 'pointer';
                    this.showToast('AI生成完成', 'success');
                } else {
                    this.showToast('AI生成失败，请手动输入', 'error');
                    aiFields.style.display = 'block';
                }
            } catch (e) {
                console.error('AI生成角色描述失败:', e);
                this.showToast('AI生成失败，请手动输入', 'error');
                aiFields.style.display = 'block';
            } finally {
                aiGenerateBtn.disabled = false;
                aiGenerateBtn.innerHTML = '<span>🤖</span><span>AI生成角色描述</span>';
            }
        });

        // 保存按钮
        saveBtn.addEventListener('click', () => {
            this.saveNewCharacterFromDialog(modal);
        });

        // 取消按钮
        closeBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });

        // 聚焦到名字输入框
        nameInput.focus();
    }

    /**
     * 💾 从对话框保存新角色
     */
    async saveNewCharacterFromDialog(modal) {
        const name = modal.querySelector('#newCharNameInput').value.trim();
        const role = modal.querySelector('#newCharRole')?.value.trim() || '';
        const background = modal.querySelector('#newCharBackground')?.value.trim() || '';
        const gender = modal.querySelector('#newCharGender').value.trim();
        const age = modal.querySelector('#newCharAge').value.trim();
        const appearance = modal.querySelector('#newCharAppearance').value.trim();
        const personality = modal.querySelector('#newCharPersonality').value.trim();
        const appearing_event = modal.querySelector('#newCharAppearingEvent')?.value.trim() || '';

        if (!name) {
            this.showToast('角色名不能为空', 'error');
            return;
        }

        const character = {
            name,
            role,  // 🔥 新增：角色定位
            background,  // 🔥 新增：角色背景
            appearing_event,  // 🔥 新增：出场原因
            gender,
            age,
            appearance,
            personality,
            description: `${gender ? gender + '，' : ''}${age ? age + '，' : ''}${appearance}`
        };

        try {
            const response = await fetch('/api/characters/add-character', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel,
                    character: character,
                    generate_portrait: false
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`✅ 角色 "${name}" 已添加`, 'success');
                modal.style.display = 'none';

                // 重新加载角色列表和剧照显示
                await this.loadEventsAndCharacters();
                this.loadCharacterPortraitsStep();
            } else {
                this.showToast('添加角色失败: ' + (result.error || '未知错误'), 'error');
            }
        } catch (error) {
            console.error('保存角色失败:', error);
            this.showToast('保存角色失败: ' + error.message, 'error');
        }
    }

    /**
     * 🔥 打开剧照预览模态框
     */
    openPortraitModal(character, portrait) {
        const modal = document.getElementById('portraitModal');
        const img = document.getElementById('portraitModalImage');
        const nameEl = document.getElementById('portraitModalName');
        const roleEl = document.getElementById('portraitModalRole');

        img.src = portrait.imageUrl;
        nameEl.textContent = character.name;
        roleEl.textContent = character.role || '角色';

        modal.classList.add('active');
    }

    /**
     * 🔥 关闭剧照预览模态框
     */
    closePortraitModal() {
        const modal = document.getElementById('portraitModal');
        modal.classList.remove('active');
    }

    /**
     * 检查是否有从剧照工作室返回的结果
     */
    checkPortraitStudioResult() {
        try {
            const resultData = localStorage.getItem('portraitStudio_result');
            if (resultData) {
                const result = JSON.parse(resultData);
                console.log('📺 [剧照步骤] 发现剧照工作室返回的结果:', result);
                console.log('📺 [剧照步骤] characterName:', result.characterName);
                console.log('📺 [剧照步骤] imageUrl:', result.imageUrl);

                // 保存剧照信息到工作流
                if (result.characterName && result.imageUrl) {
                    this.episodeWorkflow.characterPortraits.set(result.characterName, {
                        imageUrl: result.imageUrl,
                        imagePath: result.imagePath,
                        timestamp: result.timestamp
                    });
                    console.log(`✅ [剧照步骤] 已保存 ${result.characterName} 的剧照`);
                    console.log('📺 [剧照步骤] 当前所有已保存剧照的角色:', Array.from(this.episodeWorkflow.characterPortraits.keys()));

                    // 🔥 持久化到localStorage
                    this.saveCharacterPortraits();

                    this.showToast(`✅ ${result.characterName} 的剧照已保存`, 'success');
                }

                // 清除localStorage
                localStorage.removeItem('portraitStudio_result');
            } else {
                console.log('📺 [剧照步骤] localStorage中没有portraitStudio_result数据');
            }
        } catch (e) {
            console.error('❌ [剧照步骤] 检查剧照结果失败:', e);
        }
    }

    /**
     * 从选中的集中提取角色
     */
    extractCharactersFromEpisodes() {
        const characterMap = new Map();

        // 1. 首先尝试从episode数据中提取角色
        this.episodeWorkflow.selectedEpisodes.forEach(episodeId => {
            // 在重大事件的子事件中查找
            if (this.episodeWorkflow.selectedMajorEvent?.children) {
                const episode = this.episodeWorkflow.selectedMajorEvent.children.find(e => e.id === episodeId);
                if (episode) {
                    const chars = episode.characters || '';
                    if (chars) {
                        chars.split(/[,，、;；]/).forEach(name => {
                            name = name.trim();
                            if (name && !characterMap.has(name)) {
                                // 从全局角色列表中查找详细信息
                                const fullChar = this.characters.find(c => c.name === name);
                                characterMap.set(name, fullChar || { name, role: '角色' });
                            }
                        });
                    }
                }
            }
        });

        // 2. 🔥 始终添加全局角色列表（包括新添加的角色）
        if (this.characters && this.characters.length > 0) {
            console.log('📺 添加全局角色列表，当前角色数量:', this.characters.length);
            this.characters.forEach(char => {
                if (!characterMap.has(char.name)) {
                    characterMap.set(char.name, char);
                }
            });
        }

        console.log('📺 提取到的角色:', Array.from(characterMap.values()));
        return Array.from(characterMap.values());
    }

    /**
     * 处理剧照操作
     */
    async handlePortraitAction(action, characterId, characterData) {
        switch(action) {
            case 'generate':
            case 'new-look':
                // 跳转到剧照工作台
                this.openPortraitStudio(characterData);
                break;
            case 'view':
                // 显示剧照预览 - 使用模态框
                const portrait = this.episodeWorkflow.characterPortraits.get(characterId);
                if (portrait) {
                    this.openPortraitModal(characterData, portrait);
                }
                break;
        }
    }

    /**
     * 🔶 显示添加角色对话框
     */
    openPortraitStudio(character) {
        console.log('📸 [打开剧照工作台] 角色数据:', character);

        // 🔥 根据角色信息生成AI提示词
        const prompt = this.generateCharacterPortraitPrompt(character);
        console.log('📸 [打开剧照工作台] 生成的提示词:', prompt);

        // 🔥 获取剧集信息 - 使用实际的目录名
        let episodeInfo = '默认';
        if (this.episodeWorkflow.selectedMajorEvent) {
            // 🔥 使用重大事件的名称来构建目录名
            const majorEvent = this.episodeWorkflow.selectedMajorEvent;
            const majorIndex = majorEvent.major_index || 0;

            // 🔥 使用统一的路径清理函数
            const eventTitle = this.sanitizePath(majorEvent.title || majorEvent.name || '');
            episodeInfo = `${majorIndex + 1}集_${eventTitle}`;
        }

        console.log('📸 [打开剧照工作台] 剧集信息:', episodeInfo);

        // 保存工作流状态
        localStorage.setItem('episodeWorkflow_state', JSON.stringify({
            novelTitle: this.selectedNovel,
            selectedEpisodes: Array.from(this.episodeWorkflow.selectedEpisodes),
            selectedMajorEvent: this.episodeWorkflow.selectedMajorEvent,
            characterPortraits: Array.from(this.episodeWorkflow.characterPortraits.entries()),
            returnPath: '/video-generation?mode=episode-workflow'
        }));

        // 保存角色信息和生成的提示词
        const dataToSave = {
            ...character,
            generatedPrompt: prompt,  // 添加自动生成的提示词
            episode_info: episodeInfo,  // 🔥 添加剧集信息用于文件命名
            novel_title: this.selectedNovel,  // 🔥 添加小说标题用于保存到视频项目
            timestamp: Date.now() // 🔥 添加时间戳，用于过期检查
        };
        console.log('📸 [打开剧照工作台] 保存到localStorage的数据:', dataToSave);
        localStorage.setItem('portraitStudio_character', JSON.stringify(dataToSave));

        // 打开剧照工作台
        console.log('📸 [打开剧照工作台] 打开新窗口...');
        window.open('/portrait-studio?mode=episode', '_blank');
    }

    /**
     * 根据角色信息生成AI剧照提示词
     */
    generateCharacterPortraitPrompt(character) {
        const name = character.name || '';
        const role = character.role || '';
        const description = character.description || '';

        // 根据角色类型确定风格和构图
        let style = '';
        let composition = '';
        let expression = '';
        let background = '';

        // 角色类型分析
        if (role.includes('主角') || role.includes('女主')) {
            style = '仙侠修真风格，高质量人物立绘';
            composition = '半身正面像，胸部以上构图，突出面部特征';
            expression = '自信坚定，眼神有神，气场强大';
            background = '仙气缭绕的背景，云雾缭绕';
        } else if (role.includes('反派') || role.includes('BOSS')) {
            style = '仙侠反派风格，霸气外露';
            composition = '全身像或半身像，威严姿态';
            expression = '冷漠傲慢，眼神锐利，压迫感强';
            background = '黑暗气息，神秘背景';
        } else if (role.includes('长老') || role.includes('宗师') || role.includes('真仙')) {
            style = '仙侠高人风格，仙风道骨';
            composition = '半身像，端庄肃穆';
            expression = '慈祥中带着威严，眼神深邃';
            background = '道家仙山，古色古香';
        } else if (role.includes('少女') || role.includes('女主')) {
            style = '仙侠美女风格，精致唯美';
            composition = '半身像，优美姿态';
            expression = '温柔恬静或娇俏可爱';
            background = '花海或仙宫，梦幻氛围';
        } else {
            style = '仙侠人物立绘，精致细节';
            composition = '半身正面像';
            expression = '生动自然';
            background = '仙侠风格背景';
        }

        // 构建完整提示词
        let prompt = `角色名称：${name}\n`;
        prompt += `角色定位：${role}\n`;
        prompt += `\n`;
        prompt += `【画面要求】\n`;
        prompt += `风格：${style}\n`;
        prompt += `构图：${composition}\n`;
        prompt += `表情：${expression}\n`;
        prompt += `背景：${background}\n`;

        // 添加描述细节
        if (description) {
            prompt += `\n【角色特征】\n${description}\n`;
        }

        // 添加技术要求
        prompt += `\n【技术要求】\n`;
        prompt += `- 高清画质，细节精致\n`;
        prompt += `- 8k分辨率，专业插画质量\n`;
        prompt += `- 光影效果出色，立体感强\n`;
        prompt += `- 色彩和谐，符合仙侠美学\n`;
        prompt += `- 人物比例协调，五官端正\n`;

        return prompt;
    }

    /**
     * 加载分镜头步骤
     */
    async loadStoryboardStep() {
        const container = document.getElementById('episodeStoryboardPreview');
        const selectedCount = this.episodeWorkflow.selectedEpisodes.size;

        // 检查是否已生成过分镜头（内存中）
        if (this.episodeWorkflow.storyboardData) {
            this.renderStoryboardResults(this.episodeWorkflow.storyboardData);
            return;
        }

        // 获取选中的集数信息
        const selectedEpisodes = Array.from(this.episodeWorkflow.selectedEpisodes);
        const episodeList = [];

        selectedEpisodes.forEach(epId => {
            const item = document.querySelector(`.episode-item[data-episode-id="${epId}"]`);
            if (item) {
                const titleEl = item.querySelector('.episode-title');
                const stageEl = item.querySelector('.episode-stage');
                episodeList.push({
                    id: epId,
                    title: titleEl ? titleEl.textContent : epId,
                    stage: stageEl ? stageEl.textContent : ''
                });
            }
        });

        // 🔥 先检查服务端是否已有分镜头文件
        container.innerHTML = `
            <div class="storyboard-preview" style="padding: 2rem;">
                <div style="text-align: center;">
                    <div class="progress-spinner" style="margin: 0 auto 1.5rem;"></div>
                    <p style="color: var(--text-secondary);">正在检查分镜头文件...</p>
                </div>
            </div>
        `;

        try {
            const checkResponse = await fetch('/api/video/episode-workflow/check-storyboards', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel,
                    episodes: episodeList
                })
            });

            const checkResult = await checkResponse.json();

            if (checkResult.success && checkResult.existing_count > 0) {
                // 有部分或全部分镜头已存在
                const existing = checkResult.existing_storyboards;
                const missing = checkResult.missing_episodes || [];

                // 合并已存在的分镜头数据
                const allStoryboards = {};
                for (const [epId, data] of Object.entries(existing)) {
                    allStoryboards[epId] = this.convertStoryboardToDisplayFormat(epId, data.data, data);
                }

                // 如果全部都已存在，直接显示结果
                if (missing.length === 0) {
                    this.episodeWorkflow.storyboardData = allStoryboards;
                    this.renderStoryboardResults(allStoryboards);
                    this.showToast(`已加载 ${checkResult.existing_count} 个分镜头文件`, 'success');
                    return;
                }

                // 部分存在，显示混合界面
                this.renderPartialStoryboardUI(episodeList, existing, missing, allStoryboards);
                return;
            }
        } catch (e) {
            console.warn('检查分镜头文件失败:', e);
        }

        // 全部不存在或检查失败，显示生成界面
        this.renderGenerateStoryboardUI(episodeList, selectedCount);
    }

    /**
     * 渲染生成分镜头的UI
     */
    renderGenerateStoryboardUI(episodeList, selectedCount) {
        const container = document.getElementById('episodeStoryboardPreview');
        container.innerHTML = `
            <div class="storyboard-preview">
                <div class="storyboard-intro" style="text-align: center; padding: 2rem;">
                    <p style="font-size: 1.1rem; margin-bottom: 1rem;">🎬 将为选中的 ${selectedCount} 集生成分镜头脚本</p>
                    <p class="hint" style="color: var(--text-secondary); margin-bottom: 1.5rem;">使用AI自动为每集生成专业的分镜头脚本</p>
                    <div class="selected-episodes-summary" style="display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; margin-bottom: 1.5rem;">
                        ${episodeList.map(ep => `
                            <span class="episode-tag" style="background: var(--bg-tertiary); padding: 0.3rem 0.8rem; border-radius: 4px; font-size: 0.85rem;">
                                ${ep.title}
                            </span>
                        `).join('')}
                    </div>
                    <button id="generateStoryboardBtn" class="btn-primary btn-large" style="min-width: 200px;">
                        🎬 开始生成分镜头
                    </button>
                </div>
            </div>
        `;

        // 绑定生成按钮事件
        const generateBtn = document.getElementById('generateStoryboardBtn');
        if (generateBtn) {
            generateBtn.onclick = () => this.generateEpisodeStoryboard(episodeList);
        }
    }

    /**
     * 渲染部分分镜头已存在的UI
     */
    renderPartialStoryboardUI(episodeList, existing, missing, existingStoryboards) {
        const container = document.getElementById('episodeStoryboardPreview');

        const existingTitles = Object.values(existing).map(e => e.episode_title).join('、');
        const missingTitles = episodeList
            .filter(ep => missing.includes(ep.id))
            .map(ep => ep.title)
            .join('、');

        container.innerHTML = `
            <div class="storyboard-preview">
                <div class="storyboard-intro" style="text-align: center; padding: 2rem;">
                    <p style="font-size: 1.1rem; margin-bottom: 0.5rem;">✅ 已找到 ${Object.keys(existing).length} 个分镜头文件</p>
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">已存在：${existingTitles}</p>

                    ${missing.length > 0 ? `
                        <p style="font-size: 1rem; margin-bottom: 0.5rem;">📝 还需要生成 ${missing.length} 个分镜头</p>
                        <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1.5rem;">待生成：${missingTitles}</p>
                        <button id="generateMissingBtn" class="btn-primary btn-large" style="min-width: 200px;">
                            🎬 生成剩余分镜头
                        </button>
                    ` : ''}

                    <button id="loadExistingBtn" class="btn-secondary btn-large" style="min-width: 200px; margin-top: 1rem;">
                        📋 查看现有分镜头
                    </button>
                </div>
            </div>
        `;

        // 绑定按钮事件
        const generateBtn = document.getElementById('generateMissingBtn');
        if (generateBtn) {
            const missingEpisodes = episodeList.filter(ep => missing.includes(ep.id));
            generateBtn.onclick = () => this.generateEpisodeStoryboard(missingEpisodes, existingStoryboards);
        }

        const loadBtn = document.getElementById('loadExistingBtn');
        if (loadBtn) {
            loadBtn.onclick = () => {
                this.episodeWorkflow.storyboardData = existingStoryboards;
                this.renderStoryboardResults(existingStoryboards);
            };
        }
    }

    /**
     * 将分镜头数据转换为显示格式
     */
    convertStoryboardToDisplayFormat(episodeId, storyboardData, metaInfo) {
        const shots = storyboardData.shots || [];
        const scenes = shots.map(shot => ({
            scene_number: shot.shot_number,
            scene_title: (shot.screen_action || '').substring(0, 50),
            location: shot.location || '场景',
            estimated_duration_seconds: shot.duration || 8,
            shot_sequence: [{
                shot_number: shot.shot_number,
                shot_type: shot.shot_type || '中景',
                camera_movement: shot.shot_type || '中景',
                duration: shot.duration || 8,
                description: shot.screen_action || shot.description || '',
                dialogue: shot.dialogue || '',
                audio_note: shot.audio || '',
                veo_prompt: shot.veo_prompt || '',
                plot_points: shot.plot_content ? [shot.plot_content] : [],
                characters: shot.characters || []
            }]
        }));

        return {
            title: metaInfo.title || storyboardData.video_title || metaInfo.episode_title,
            stage: '',
            scenes: scenes,
            total_duration: scenes.reduce((sum, s) => sum + (s.estimated_duration_seconds || 8), 0),
            hook: storyboardData.hook || '',
            ending_hook: storyboardData.ending_hook || '',
            ai_generated: true,
            character_images: storyboardData.character_images || []
        };
    }

    /**
     * 生成选中的分镜头脚本
     */
    async generateEpisodeStoryboard(episodeList) {
        const container = document.getElementById('episodeStoryboardPreview');
        const generateBtn = document.getElementById('generateStoryboardBtn');

        // 显示进度
        container.innerHTML = `
            <div class="storyboard-preview" style="padding: 2rem;">
                <div style="text-align: center;">
                    <div class="progress-spinner" style="margin: 0 auto 1.5rem;"></div>
                    <p style="color: var(--text-secondary);">正在生成分镜头脚本...</p>
                    <p class="hint" id="storyboardProgressText">准备中...</p>
                </div>
            </div>
        `;

        const progressText = document.getElementById('storyboardProgressText');

        try {
            // 更新进度
            const progressSteps = [
                '分析剧本结构...',
                '生成场景分镜...',
                '设计镜头运动...',
                '添加音频指导...',
                '完成分镜头脚本...'
            ];

            let stepIndex = 0;
            const progressInterval = setInterval(() => {
                if (stepIndex < progressSteps.length) {
                    if (progressText) progressText.textContent = progressSteps[stepIndex];
                    stepIndex++;
                }
            }, 800);

            // 调用API生成分镜头
            const response = await fetch('/api/video/episode-workflow/generate-storyboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel,
                    episodes: episodeList
                })
            });

            clearInterval(progressInterval);

            const data = await response.json();
            console.log('分镜头生成结果:', data);

            if (data.success) {
                // 保存分镜头数据
                this.episodeWorkflow.storyboardData = data.storyboards;

                // 渲染结果
                this.renderStoryboardResults(data.storyboards);

                this.showToast(`已为 ${data.total_episodes} 集生成分镜头脚本`, 'success');
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('生成分镜头失败:', error);
            container.innerHTML = `
                <div class="storyboard-preview" style="padding: 2rem;">
                    <div style="text-align: center; color: var(--error-color);">
                        <p style="font-size: 1.1rem; margin-bottom: 1rem;">❌ 生成失败</p>
                        <p>${error.message}</p>
                        <button onclick="location.reload()" class="btn-secondary" style="margin-top: 1rem;">重试</button>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 渲染分镜头结果（包含AI视频生成提示语）
     */
    renderStoryboardResults(storyboards) {
        const container = document.getElementById('episodeStoryboardPreview');

        let html = '<div class="storyboard-results">';

        for (const [episodeId, storyboard] of Object.entries(storyboards)) {
            const scenes = storyboard.scenes || [];
            const totalDuration = scenes.reduce((sum, scene) => {
                return sum + (scene.estimated_duration_seconds || 0);
            }, 0);

            // 🔥 新增：角色参考图信息
            let characterImagesHtml = '';
            const characterImages = storyboard.character_images || [];
            if (characterImages.length > 0) {
                characterImagesHtml = `
                    <div style="padding: 0.75rem 1.5rem; background: var(--bg-dark); border-bottom: 1px solid var(--border);">
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem;">👥 角色参考图映射：</div>
                        <div style="display: flex; flex-wrap: wrap; gap: 0.5rem;">
                            ${characterImages.map(char => `
                                <span style="display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; background: var(--bg-tertiary); border-radius: 4px; font-size: 0.8rem;">
                                    <span style="color: var(--primary-color); font-weight: bold; margin-right: 0.5rem;">参考图${char.reference_index}</span>
                                    <span style="color: var(--text-primary);">${char.character_name}</span>
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            html += `
                <div class="episode-storyboard" style="background: var(--bg-secondary); border-radius: 12px; margin-bottom: 1.5rem; overflow: hidden;">
                    <div class="episode-storyboard-header" style="padding: 1rem 1.5rem; background: var(--bg-tertiary); border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: var(--text-primary);">${storyboard.title}</h4>
                            <span style="color: var(--text-secondary); font-size: 0.9rem;">${storyboard.stage} · ${scenes.length} 场景 · ${Math.floor(totalDuration / 60)}分${totalDuration % 60}秒</span>
                        </div>
                        <button class="btn-secondary btn-sm" onclick="this.closest('.episode-storyboard').querySelector('.scene-details').classList.toggle('hidden')">
                            📋 展开详情
                        </button>
                    </div>
                    ${characterImagesHtml}
                    <div class="scene-details">
                        ${scenes.map((scene, idx) => `
                            <div class="scene-block" style="padding: 1rem 1.5rem; border-bottom: 1px solid var(--border);">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <strong style="color: var(--primary-color);">场景 ${idx + 1}: ${scene.scene_title}</strong>
                                    <span style="color: var(--text-secondary); font-size: 0.85rem;">${Math.floor((scene.estimated_duration_seconds || 0) / 60)}分${(scene.estimated_duration_seconds || 0) % 60}秒</span>
                                </div>
                                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 0.5rem;">📍 ${scene.location || '场景'}</p>
                                <div class="shots-container">
                                    ${(scene.shot_sequence || []).map(shot => {
                                        // 🔥 新增：显示镜头中的角色信息
                                        let shotCharactersHtml = '';
                                        const shotCharacters = shot.characters || [];
                                        if (shotCharacters.length > 0) {
                                            shotCharactersHtml = `
                                                <div style="margin-top: 0.5rem; padding: 0.25rem 0.5rem; background: var(--bg-tertiary); border-radius: 4px; font-size: 0.75rem;">
                                                    <span style="color: var(--text-secondary);">👤 </span>
                                                    ${shotCharacters.map(ch => `
                                                        <span style="color: var(--primary-color);">参考图${ch.reference_index} ${ch.name}</span>
                                                        ${ch.action ? `<span style="color: var(--text-secondary);">: ${ch.action}</span>` : ''}
                                                    `).join(' · ')}
                                                </div>
                                            `;
                                        }

                                        return `
                                        <div class="shot-card" style="background: var(--bg-dark); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem;">
                                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                                <div>
                                                    <span style="color: var(--primary-color); font-weight: bold;">${shot.shot_number}.</span>
                                                    <strong style="margin-left: 0.5rem;">${shot.shot_type}</strong>
                                                    <span style="color: var(--text-secondary); margin-left: 0.5rem;">· ${shot.duration}秒</span>
                                                </div>
                                                <button class="btn-secondary btn-sm" onclick="this.parentElement.parentElement.querySelector('.veo-prompt').classList.toggle('hidden')" style="font-size: 0.75rem;">
                                                    🤖 AI提示语
                                                </button>
                                            </div>
                                            <p style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.25rem;">${shot.description || ''}</p>
                                            ${shotCharactersHtml}
                                            ${shot.dialogue ? `<p style="color: var(--accent-color); font-size: 0.8rem; margin-bottom: 0.25rem; font-style: italic;">💬 ${shot.dialogue}</p>` : ''}
                                            <div class="veo-prompt hidden" style="margin-top: 0.5rem; padding: 0.5rem; background: var(--bg-tertiary); border-radius: 4px; border-left: 3px solid var(--primary-color);">
                                                <p style="color: var(--accent-color); font-size: 0.8rem; margin: 0; font-family: monospace;">${shot.veo_prompt || '暂无提示语'}</p>
                                            </div>
                                        </div>
                                    `}).join('')}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        html += '</div>';
        container.innerHTML = html;
    }

    /**
     * 加载视频生成步骤
     */
    async loadVideoStep() {
        const container = document.getElementById('episodeVideoPreview');

        // 检查是否已生成分镜头
        if (!this.episodeWorkflow.storyboardData) {
            container.innerHTML = `
                <div class="video-preview-placeholder" style="padding: 3rem; text-align: center;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🎬</div>
                    <p style="color: var(--text-secondary); margin-bottom: 1.5rem;">请先完成分镜头脚本生成</p>
                    <button class="btn-primary" onclick="this.episodeWorkflow.step = 'generate-storyboard'; this.showEpisodeWorkflowStep('generate-storyboard');">返回上一步</button>
                </div>
            `;
            return;
        }

        // 先加载已生成的视频
        await this.loadGeneratedVideos();

        // 显示生成按钮区域
        const generateBtnArea = document.createElement('div');
        generateBtnArea.className = 'video-generate-action-area';
        generateBtnArea.style.cssText = `
            text-align: center;
            padding: 2rem;
            border-top: 1px solid var(--border);
            margin-top: 1.5rem;
        `;

        generateBtnArea.innerHTML = `
            <div style="margin-bottom: 1rem;">
                <button id="generateAllVideosBtn" class="btn-primary btn-large" style="min-width: 200px; padding: 1rem 2rem;">
                    🎬 批量生成视频
                </button>
            </div>
            <p style="color: var(--text-secondary); font-size: 0.9rem;">
                将为每个镜头使用 AI 生成视频（使用角色剧照作为参考图）
            </p>
        `;

        container.appendChild(generateBtnArea);

        // 绑定生成按钮事件
        const generateBtn = document.getElementById('generateAllVideosBtn');
        if (generateBtn) {
            generateBtn.onclick = () => this.generateAllVideos();
        }
    }

    /**
     * 加载已生成的视频
     */
    async loadGeneratedVideos() {
        const container = document.getElementById('episodeVideoPreview');

        try {
            const response = await fetch('/api/video/studio/library?status=all');
            const data = await response.json();

            if (data.success && data.videos && data.videos.length > 0) {
                // 按集数筛选当前项目的视频
                const novelVideos = this.filterVideosByNovel(data.videos);

                if (novelVideos.length > 0) {
                    this.renderGeneratedVideos(novelVideos);
                } else {
                    this.showNoVideosState();
                }
            } else {
                this.showNoVideosState();
            }
        } catch (error) {
            console.error('加载视频失败:', error);
            this.showNoVideosState();
        }
    }

    /**
     * 筛选当前小说的视频
     */
    filterVideosByNovel(videos) {
        const novelTitle = this.selectedNovel || '';
        return videos.filter(video => {
            const prompt = video.prompt || '';
            return prompt.includes(novelTitle) || prompt.includes(this.extractNovelShortTitle(novelTitle));
        });
    }

    /**
     * 提取小说简称
     */
    extractNovelShortTitle(fullTitle) {
        // 提取小说名的主要部分
        if (fullTitle.includes('：')) {
            return fullTitle.split('：')[0];
        }
        return fullTitle.substring(0, 10);
    }

    /**
     * 显示无视频状态
     */
    showNoVideosState() {
        const container = document.getElementById('episodeVideoPreview');
        if (container) {
            container.innerHTML = `
                <div class="no-videos-state" style="text-align: center; padding: 2rem; color: var(--text-secondary);">
                    <div style="font-size: 2rem; margin-bottom: 0.5rem;">🎬</div>
                    <p>还没有生成的视频</p>
                    <p style="font-size: 0.85rem;">点击下方按钮开始生成</p>
                </div>
            `;
        }
    }

    /**
     * 渲染已生成的视频列表
     */
    renderGeneratedVideos(videos) {
        const container = document.getElementById('episodeVideoPreview');

        const videosHTML = `
            <div class="generated-videos-section">
                <div class="section-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <h3 style="margin: 0;">📹 已生成的视频 (${videos.length})</h3>
                    <button class="btn-secondary btn-sm" onclick="window.location.reload()">🔄 刷新</button>
                </div>
                <div class="videos-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">
                    ${videos.map(video => this.renderVideoCard(video)).join('')}
                </div>
            </div>
        `;

        // 插入到容器开头
        const existingContent = container.innerHTML;
        container.innerHTML = videosHTML + existingContent;
    }

    /**
     * 渲染单个视频卡片
     */
    renderVideoCard(video) {
        const statusClass = video.status === 'completed' ? 'completed' : 'processing';
        const statusText = video.status === 'completed' ? '已完成' : '生成中';
        const statusIcon = video.status === 'completed' ? '✅' : '⏳';

        let content = '';
        if (video.status === 'completed' && video.url) {
            content = `
                <div class="video-player-wrapper" style="width: 100%; aspect-ratio: 16/9; background: #000; border-radius: 4px; overflow: hidden; margin-bottom: 0.5rem;">
                    <video src="${video.url}" controls style="width: 100%; height: 100%;"></video>
                </div>
            `;
        } else {
            content = `
                <div class="video-placeholder" style="width: 100%; aspect-ratio: 16/9; background: var(--bg-dark); border-radius: 4px; display: flex; align-items: center; justify-content: center; margin-bottom: 0.5rem;">
                    <div style="text-align: center;">
                        <div style="font-size: 1.5rem;">⏳</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">生成中...</div>
                    </div>
                </div>
            `;
        }

        return `
            <div class="video-card" data-video-id="${video.id}" style="background: var(--bg-secondary); border-radius: 8px; padding: 0.75rem; overflow: hidden;">
                ${content}
                <div class="video-info" style="font-size: 0.8rem; margin-bottom: 0.5rem;">
                    <div class="video-prompt" style="color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${video.prompt.substring(0, 40)}${video.prompt.length > 40 ? '...' : ''}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="status-badge ${statusClass}" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 4px;">
                        ${statusIcon} ${statusText}
                    </span>
                    <div class="video-actions">
                        ${video.status === 'completed' && video.url ? `
                            <button onclick="window.open('${video.url}', '_blank')" class="btn-sm" style="margin-right: 0.25rem;">🔗</button>
                            <button onclick="downloadVideo('${video.url}')" class="btn-sm">📥</button>
                        ` : `
                            <button onclick="location.reload()" class="btn-sm">🔄</button>
                        `}
                    </div>
                </div>
            </div>
        `;
    }

    /**
     * 批量生成所有视频（交互式模式：每个镜头需确认）
     */
    async generateAllVideos() {
        const storyboardData = this.episodeWorkflow.storyboardData;
        const characterPortraits = this.episodeWorkflow.characterPortraits;

        if (!storyboardData) {
            this.showToast('请先生成分镜头脚本', 'warning');
            return;
        }

        // 🔥 构建剧集目录名称（与openPortraitStudio中的逻辑一致）
        let episodeDirectoryName = '默认';
        if (this.episodeWorkflow.selectedMajorEvent) {
            const majorEvent = this.episodeWorkflow.selectedMajorEvent;
            const majorIndex = majorEvent.major_index || 0;

            // 🔥 使用统一的路径清理函数
            const eventTitle = this.sanitizePath(majorEvent.title || majorEvent.name || '');
            episodeDirectoryName = `${majorIndex + 1}集_${eventTitle}`;
        }

        console.log('🎬 [视频生成] 剧集目录名称:', episodeDirectoryName);

        // 收集所有镜头
        const allShots = [];
        for (const [epId, storyboard] of Object.entries(storyboardData)) {
            const scenes = storyboard.scenes || [];
            for (const scene of scenes) {
                const shots = scene.shot_sequence || [];
                for (const shot of shots) {
                    if (shot.veo_prompt) {
                        allShots.push({
                            episode_id: epId,
                            episode_title: storyboard.title,
                            episode_directory_name: episodeDirectoryName,  // 🔥 已使用sanitizePath清理
                            event_name: this.sanitizePath(storyboard.title || ''),  // 🔥 清理事件名
                            stage: storyboard.stage,
                            scene_title: scene.scene_title,
                            shot_number: shot.shot_number,
                            shot_type: (shot.shot_type || 'shot').replace(/\//g, '_'),  // 🔥 清理斜杠
                            prompt: shot.veo_prompt
                        });
                    }
                }
            }
        }

        if (allShots.length === 0) {
            this.showToast('没有可生成镜头', 'warning');
            return;
        }

        console.log(`🎬 [视频生成] 准备生成 ${allShots.length} 个视频`);

        // 显示生成进度概览
        this.showVideoGenerationOverview(allShots);

        // 交互式逐个生成：每个镜头需要确认
        let completedCount = 0;
        let skippedCount = 0;

        for (let i = 0; i < allShots.length; i++) {
            const shot = allShots[i];

            // 🔥 检查视频是否已存在
            const existingVideo = await this.checkVideoExists(shot);
            if (existingVideo) {
                console.log(`✅ 镜头 ${i + 1} 视频已存在: ${existingVideo.video_url}`);

                // 直接显示预览对话框（已存在的视频）
                const continueResult = await this.showVideoPreviewDialog(shot, i + 1, allShots.length, existingVideo.video_url, true);

                if (continueResult === 'cancel') {
                    this.showToast('已停止批量生成', 'info');
                    break;
                } else if (continueResult === 'regenerate') {
                    // 用户选择重新生成，显示确认对话框
                    const confirmResult = await this.showGenerationConfirmDialog(shot, i + 1, allShots.length, characterPortraits);

                    if (confirmResult.action === 'cancel') {
                        this.showToast('已取消批量生成', 'info');
                        break;
                    } else if (confirmResult.action === 'skip') {
                        skippedCount++;
                        this.updateShotStatus(i, 'skipped', '已跳过');
                        continue;
                    }

                    // 重新生成
                    this.updateShotStatus(i, 'processing', '生成中...');
                    const result = await this.generateSingleVideo(shot, i + 1, allShots.length, characterPortraits, confirmResult.selectedImages, confirmResult.prompt, confirmResult.model, confirmResult.orientation, confirmResult.size, confirmResult.useFirstLastFrame);

                    if (result.success) {
                        completedCount++;
                        const previewResult = await this.showVideoPreviewDialog(shot, i + 1, allShots.length, result.videoUrl, false);
                        if (previewResult === 'cancel') {
                            this.showToast('已停止批量生成', 'info');
                            break;
                        } else if (previewResult === 'regenerate') {
                            i--;
                            completedCount--;
                            continue;
                        }
                    } else {
                        const continueAnyway = await this.showGenerationFailedDialog(shot, i + 1, allShots.length, result.error);
                        if (!continueAnyway) {
                            break;
                        }
                    }
                } else {
                    // 用户确认使用现有视频
                    completedCount++;
                    this.updateShotStatus(i, 'completed', '已存在');
                    continue;
                }
            }

            // 显示生成前确认对话框
            const confirmResult = await this.showGenerationConfirmDialog(shot, i + 1, allShots.length, characterPortraits);

            if (confirmResult.action === 'cancel') {
                this.showToast('已取消批量生成', 'info');
                break;
            } else if (confirmResult.action === 'skip') {
                skippedCount++;
                this.updateShotStatus(i, 'skipped', '已跳过');
                continue;
            }

            // 更新状态为生成中
            this.updateShotStatus(i, 'processing', '生成中...');

            // 生成视频
            const result = await this.generateSingleVideo(shot, i + 1, allShots.length, characterPortraits, confirmResult.selectedImages, confirmResult.prompt, confirmResult.model, confirmResult.orientation, confirmResult.size, confirmResult.useFirstLastFrame);

            if (result.success) {
                completedCount++;

                // 显示生成后的预览对话框
                const continueResult = await this.showVideoPreviewDialog(shot, i + 1, allShots.length, result.videoUrl, false);

                if (continueResult === 'cancel') {
                    this.showToast('已停止批量生成', 'info');
                    break;
                } else if (continueResult === 'regenerate') {
                    // 重新生成当前镜头：回退索引，再次循环
                    i--;
                    completedCount--;
                    continue;
                }
            } else {
                // 生成失败，询问是否继续
                const continueAnyway = await this.showGenerationFailedDialog(shot, i + 1, allShots.length, result.error);
                if (!continueAnyway) {
                    break;
                }
            }
        }

        // 显示最终结果
        this.showToast(`批量生成完成！成功: ${completedCount}, 跳过: ${skippedCount}`, 'success');

        // 刷新列表
        setTimeout(() => {
            this.loadVideoStep();
        }, 1000);
    }

    /**
     * 显示生成前确认对话框
     */
    async showGenerationConfirmDialog(shot, currentIndex, total, characterPortraits) {
        return new Promise((resolve) => {
            // 🔥 默认不选中任何图片，让用户手动选择
            const selectedImages = [];
            const allPortraits = Array.from(characterPortraits.entries());

            // 🔥 生成唯一键用于保存/加载提示词
            const shotKey = `videoPrompt_${this.selectedNovel}_${shot.episode_id}_${shot.shot_number}`;

            // 🔥 尝试加载之前保存的提示词
            const savedPrompt = localStorage.getItem(shotKey);
            const promptToUse = savedPrompt || shot.prompt;

            // 创建对话框
            const modal = document.createElement('div');
            modal.className = 'video-confirm-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            modal.innerHTML = `
                <div class="modal-content" style="
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    max-width: 800px;
                    max-height: 90vh;
                    overflow-y: auto;
                    padding: 1.5rem;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                ">
                    <div class="modal-header" style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 1rem;
                        border-bottom: 1px solid var(--border);
                        padding-bottom: 1rem;
                    ">
                        <h3 style="margin: 0;">🎬 确认生成镜头 ${currentIndex}/${total}</h3>
                        <button class="btn-close" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>

                    <div class="modal-body">
                        <div class="shot-info-section" style="margin-bottom: 1rem;">
                            <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem;">
                                <span class="badge" style="background: var(--primary-light); padding: 0.25rem 0.5rem; border-radius: 4px;">${shot.episode_title}</span>
                                <span class="badge" style="background: var(--accent-color); padding: 0.25rem 0.5rem; border-radius: 4px;">${shot.shot_type}</span>
                                ${savedPrompt ? '<span class="badge" style="background: var(--success-color); color: white; padding: 0.25rem 0.5rem; border-radius: 4px;">已保存</span>' : ''}
                            </div>
                            <p style="color: var(--text-secondary); margin: 0;">📍 ${shot.scene_title}</p>
                        </div>

                        <div class="prompt-section" style="margin-bottom: 1rem;">
                            <label style="font-weight: bold; display: block; margin-bottom: 0.5rem;">📝 AI提示语：${savedPrompt ? '<span style="font-size: 0.75rem; color: var(--success-color);">(已加载保存的版本)</span>' : ''}</label>
                            <textarea id="promptEditArea" style="
                                width: 100%;
                                min-height: 100px;
                                background: var(--bg-dark);
                                border: 1px solid var(--border);
                                border-radius: 6px;
                                padding: 0.75rem;
                                color: var(--text-primary);
                                font-size: 0.9rem;
                                resize: vertical;
                            ">${promptToUse}</textarea>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.5rem;">
                                <small style="color: var(--text-secondary);">💾 修改后会自动保存</small>
                                ${savedPrompt ? `<button id="resetPromptBtn" style="font-size: 0.75rem; padding: 0.25rem 0.5rem; background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: 4px; cursor: pointer;">重置为原始提示词</button>` : ''}
                            </div>
                        </div>

                        <div class="reference-section" style="margin-bottom: 1rem;">
                            <label style="font-weight: bold; display: block; margin-bottom: 0.5rem;">🖼️ 参考角色剧照：</label>
                            <div id="portraitSelector" class="portrait-selector" style="
                                display: flex;
                                flex-wrap: wrap;
                                gap: 0.75rem;
                                padding: 0.75rem;
                                background: var(--bg-dark);
                                border-radius: 6px;
                                min-height: 80px;
                            ">
                                ${allPortraits.map(([name, data], idx) => `
                                    <label class="portrait-checkbox" style="
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        cursor: pointer;
                                        position: relative;
                                    ">
                                        <input type="checkbox" class="portrait-check" data-name="${name}" data-url="${data.imageUrl}"
                                            ${selectedImages.includes(data.imageUrl) ? 'checked' : ''}
                                            style="position: absolute; opacity: 0; width: 0; height: 0;">
                                        <div class="portrait-thumb" style="
                                            width: 60px;
                                            height: 60px;
                                            border-radius: 6px;
                                            overflow: hidden;
                                            border: 2px solid ${selectedImages.includes(data.imageUrl) ? 'var(--primary-color)' : 'var(--border)'};
                                            transition: all 0.2s;
                                        ">
                                            <img src="${data.imageUrl}" style="width: 100%; height: 100%; object-fit: cover;">
                                        </div>
                                        <span style="font-size: 0.7rem; margin-top: 0.25rem; max-width: 60px; overflow: hidden; text-overflow: ellipsis;">${name}</span>
                                        <div class="check-indicator" style="
                                            position: absolute;
                                            top: 4px;
                                            right: 4px;
                                            width: 16px;
                                            height: 16px;
                                            background: ${selectedImages.includes(data.imageUrl) ? 'var(--primary-color)' : 'rgba(0,0,0,0.5)'};
                                            border-radius: 50%;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            font-size: 10px;
                                        ">${selectedImages.includes(data.imageUrl) ? '✓' : ''}</div>
                                    </label>
                                `).join('')}
                            </div>
                            <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">
                                已选择 <span id="selectedCount">${selectedImages.length}</span> 张参考图
                            </p>
                        </div>

                        <div class="params-section" style="margin-bottom: 1rem;">
                            <label style="font-weight: bold; display: block; margin-bottom: 0.5rem;">⚙️ 生成参数：</label>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;">
                                <div>
                                    <label style="font-size: 0.85rem; color: var(--text-secondary);">模型：</label>
                                    <select id="paramModel" style="
                                        width: 100%;
                                        padding: 0.5rem;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 4px;
                                        color: var(--text-primary);
                                    ">
                                        <option value="veo_3_1-fast-components" selected>参考图模式 (推荐)</option>
                                        <option value="veo_3_1-fast">首尾帧模式</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="font-size: 0.85rem; color: var(--text-secondary);">方向：</label>
                                    <select id="paramOrientation" style="
                                        width: 100%;
                                        padding: 0.5rem;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 4px;
                                        color: var(--text-primary);
                                    ">
                                        <option value="portrait">竖屏 (9:16)</option>
                                        <option value="landscape" selected>横屏 (16:9)</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="font-size: 0.85rem; color: var(--text-secondary);">尺寸：</label>
                                    <select id="paramSize" style="
                                        width: 100%;
                                        padding: 0.5rem;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 4px;
                                        color: var(--text-primary);
                                    ">
                                        <option value="large" selected>大尺寸 (1080p)</option>
                                        <option value="small">小尺寸 (720p)</option>
                                    </select>
                                </div>
                            </div>
                            <div style="margin-top: 0.5rem;">
                                <label style="display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: var(--text-secondary); cursor: pointer;">
                                    <input type="checkbox" id="paramFirstLastFrame" checked style="margin: 0;">
                                    <span>启用首尾帧模式（需传2张图片：首帧+尾帧）</span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 1rem;
                        padding-top: 1rem;
                        border-top: 1px solid var(--border);
                    ">
                        <button class="btn-cancel" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--danger-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                        ">❌ 全部取消</button>
                        <button class="btn-skip" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--bg-tertiary);
                            border: 1px solid var(--border);
                            border-radius: 6px;
                            color: var(--text-primary);
                            cursor: pointer;
                        ">⏭️ 跳过此镜头</button>
                        <button class="btn-generate" style="
                            padding: 0.75rem 2rem;
                            background: var(--primary-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                            font-weight: bold;
                        ">✅ 开始生成</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // 绑定事件
            const closeBtn = modal.querySelector('.btn-close');
            const cancelBtn = modal.querySelector('.btn-cancel');
            const skipBtn = modal.querySelector('.btn-skip');
            const generateBtn = modal.querySelector('.btn-generate');
            const resetBtn = modal.querySelector('#resetPromptBtn');
            const promptArea = document.getElementById('promptEditArea');

            // 处理剧照选择
            const portraitChecks = modal.querySelectorAll('.portrait-check');
            const selectedCountEl = document.getElementById('selectedCount');

            portraitChecks.forEach(check => {
                check.addEventListener('change', () => {
                    const thumb = check.parentElement.querySelector('.portrait-thumb');
                    const indicator = check.parentElement.querySelector('.check-indicator');
                    const count = modal.querySelectorAll('.portrait-check:checked').length;

                    selectedCountEl.textContent = count;

                    if (check.checked) {
                        thumb.style.borderColor = 'var(--primary-color)';
                        indicator.textContent = '✓';
                        indicator.style.background = 'var(--primary-color)';
                    } else {
                        thumb.style.borderColor = 'var(--border)';
                        indicator.textContent = '';
                        indicator.style.background = 'rgba(0,0,0,0.5)';
                    }
                });
            });

            // 重置提示词按钮
            if (resetBtn) {
                resetBtn.onclick = () => {
                    if (confirm('确定要重置为原始提示词吗？已保存的版本将被删除。')) {
                        promptArea.value = shot.prompt;
                        localStorage.removeItem(shotKey);
                        resetBtn.remove();
                        // 移除"已保存"标签
                        const savedBadge = modal.querySelector('.badge[style*="success"]');
                        if (savedBadge) savedBadge.remove();
                        // 更新标签文本
                        const label = modal.querySelector('.prompt-section label');
                        if (label) {
                            label.innerHTML = '📝 AI提示语：';
                        }
                    }
                };
            }

            // 关闭/取消
            closeBtn.onclick = cancelBtn.onclick = () => {
                modal.remove();
                resolve({ action: 'cancel', selectedImages: [] });
            };

            // 跳过
            skipBtn.onclick = () => {
                modal.remove();
                resolve({ action: 'skip', selectedImages: [] });
            };

            // 生成 - 保存修改的提示词
            generateBtn.onclick = () => {
                const editedPrompt = promptArea.value;
                const checkedImages = Array.from(modal.querySelectorAll('.portrait-check:checked'))
                    .map(check => check.dataset.url);
                const model = document.getElementById('paramModel').value;
                const orientation = document.getElementById('paramOrientation').value;
                const size = document.getElementById('paramSize').value;
                const useFirstLastFrame = document.getElementById('paramFirstLastFrame').checked;

                console.log('🔍 [调试] 用户选中的图片数量:', checkedImages.length);
                console.log('🔍 [调试] 选中的图片URL:', checkedImages);
                console.log('🔍 [调试] 模型:', model);
                console.log('🔍 [调试] 首尾帧模式:', useFirstLastFrame);

                // 🔥 首尾帧模式需要2张图片
                if (useFirstLastFrame && checkedImages.length !== 2) {
                    this.showToast('首尾帧模式需要选择2张图片（首帧+尾帧）', 'warning');
                    return;
                }

                // 🔥 保存修改的提示词
                if (editedPrompt !== shot.prompt) {
                    localStorage.setItem(shotKey, editedPrompt);
                    console.log('💾 已保存修改的提示词:', shotKey);
                }

                modal.remove();
                resolve({
                    action: 'generate',
                    prompt: editedPrompt,
                    selectedImages: checkedImages,
                    model,
                    orientation,
                    size,
                    useFirstLastFrame
                });
            };
        });
    }

    /**
     * 显示生成后的视频预览对话框
     * @param {Object} shot - 镜头数据
     * @param {number} currentIndex - 当前索引
     * @param {number} total - 总数
     * @param {string} videoUrl - 视频URL
     * @param {boolean} isExistingVideo - 是否为已存在的视频
     */
    async showVideoPreviewDialog(shot, currentIndex, total, videoUrl, isExistingVideo = false) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'video-preview-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.9);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            // 根据是否为已存在的视频显示不同的标题和样式
            const titleIcon = isExistingVideo ? '📁' : '✅';
            const titleText = isExistingVideo ? '已存在的视频' : '生成完成';
            const titleColor = isExistingVideo ? 'var(--info-color)' : 'var(--success-color)';

            modal.innerHTML = `
                <div class="modal-content" style="
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    max-width: 900px;
                    width: 90%;
                    padding: 1.5rem;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                ">
                    <div class="modal-header" style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 1rem;
                    ">
                        <div>
                            <h3 style="margin: 0;">${titleIcon} 镜头 ${currentIndex}/${total} ${titleText}</h3>
                            <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                                ${shot.episode_title} - ${shot.scene_title}
                            </p>
                        </div>
                        <span style="color: ${titleColor}; font-size: 2rem;">${isExistingVideo ? '▶' : '✓'}</span>
                    </div>

                    ${isExistingVideo ? `
                    <div style="
                        background: var(--info-color);
                        color: white;
                        padding: 0.5rem 1rem;
                        border-radius: 6px;
                        margin-bottom: 1rem;
                        font-size: 0.9rem;
                        text-align: center;
                    ">
                        💡 该镜头的视频文件已存在，您可以选择直接使用或重新生成
                    </div>
                    ` : ''}

                    <div class="video-preview" style="
                        background: #000;
                        border-radius: 8px;
                        overflow: hidden;
                        aspect-ratio: 16/9;
                        margin-bottom: 1rem;
                    ">
                        <video src="${videoUrl}" controls autoplay style="width: 100%; height: 100%;"></video>
                    </div>

                    <div class="prompt-preview" style="
                        background: var(--bg-dark);
                        padding: 0.75rem;
                        border-radius: 6px;
                        margin-bottom: 1rem;
                        font-size: 0.85rem;
                        color: var(--text-secondary);
                        max-height: 80px;
                        overflow-y: auto;
                    ">
                        ${shot.prompt.substring(0, 200)}${shot.prompt.length > 200 ? '...' : ''}
                    </div>

                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 1rem;
                        flex-wrap: wrap;
                    ">
                        <button class="btn-stop" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--danger-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                        ">⏹️ 停止批量生成</button>
                        ${isExistingVideo ? `
                        <button class="btn-use-existing" style="
                            padding: 0.75rem 2rem;
                            background: var(--success-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                            font-weight: bold;
                        ">✅ 使用此视频</button>
                        ` : ''}
                        <button class="btn-regenerate" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--warning-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                        ">🔄 重新生成</button>
                        <button class="btn-download" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--bg-tertiary);
                            border: 1px solid var(--border);
                            border-radius: 6px;
                            color: var(--text-primary);
                            cursor: pointer;
                        ">📥 下载视频</button>
                        ${!isExistingVideo ? `
                        <button class="btn-continue" style="
                            padding: 0.75rem 2rem;
                            background: var(--success-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                            font-weight: bold;
                        ">➡️ 继续下一个</button>
                        ` : `
                        <button class="btn-continue" style="
                            padding: 0.75rem 2rem;
                            background: var(--bg-tertiary);
                            border: 1px solid var(--border);
                            border-radius: 6px;
                            color: var(--text-primary);
                            cursor: pointer;
                        ">➡️ 跳过</button>
                        `}
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // 绑定事件
            modal.querySelector('.btn-stop').onclick = () => {
                modal.remove();
                resolve('cancel');
            };

            modal.querySelector('.btn-regenerate').onclick = () => {
                modal.remove();
                resolve('regenerate');
            };

            modal.querySelector('.btn-download').onclick = () => {
                downloadVideo(videoUrl);
            };

            modal.querySelector('.btn-continue').onclick = () => {
                modal.remove();
                resolve('continue');
            };

            // 如果是已存在的视频，处理"使用此视频"按钮
            if (isExistingVideo) {
                const btnUseExisting = modal.querySelector('.btn-use-existing');
                if (btnUseExisting) {
                    btnUseExisting.onclick = () => {
                        modal.remove();
                        resolve('use-existing');  // 使用已存在的视频
                    };
                }
            }
        });
    }

    /**
     * 显示生成失败对话框
     */
    async showGenerationFailedDialog(shot, currentIndex, total, error) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'video-error-modal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            modal.innerHTML = `
                <div class="modal-content" style="
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    max-width: 500px;
                    padding: 1.5rem;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                ">
                    <div class="modal-header" style="
                        text-align: center;
                        margin-bottom: 1rem;
                    ">
                        <div style="font-size: 3rem; margin-bottom: 0.5rem;">❌</div>
                        <h3 style="margin: 0;">生成失败</h3>
                        <p style="color: var(--text-secondary); margin: 0.5rem 0 0 0;">
                            镜头 ${currentIndex}/${total}: ${shot.episode_title}
                        </p>
                    </div>

                    <div class="error-message" style="
                        background: var(--danger-light);
                        padding: 0.75rem;
                        border-radius: 6px;
                        margin-bottom: 1rem;
                        color: var(--danger-color);
                        font-size: 0.9rem;
                    ">
                        ${error || '未知错误'}
                    </div>

                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 1rem;
                    ">
                        <button class="btn-stop" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--danger-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                        ">停止生成</button>
                        <button class="btn-continue" style="
                            padding: 0.75rem 2rem;
                            background: var(--primary-color);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                        ">继续下一个</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            modal.querySelector('.btn-stop').onclick = () => {
                modal.remove();
                resolve(false);
            };

            modal.querySelector('.btn-continue').onclick = () => {
                modal.remove();
                resolve(true);
            };
        });
    }

    /**
     * 更新镜头状态
     */
    updateShotStatus(index, status, text) {
        const progressItem = document.getElementById(`shot-progress-${index}`);
        if (!progressItem) return;

        const statusBadge = progressItem.querySelector('.status-badge');
        const progressBar = progressItem.querySelector('.progress-bar-fill');

        if (status === 'processing') {
            statusBadge.className = 'status-badge processing';
            statusBadge.textContent = text || '生成中...';
            progressBar.style.width = '50%';
            progressBar.classList.add('processing');
        } else if (status === 'completed') {
            statusBadge.className = 'status-badge completed';
            statusBadge.textContent = text || '已完成';
            progressBar.style.width = '100%';
            progressBar.classList.remove('processing');
        } else if (status === 'error') {
            statusBadge.className = 'status-badge error';
            statusBadge.textContent = text || '失败';
            progressBar.style.width = '100%';
            progressBar.style.background = 'var(--danger-color)';
        } else if (status === 'skipped') {
            statusBadge.className = 'status-badge';
            statusBadge.textContent = text || '已跳过';
            progressBar.style.width = '100%';
            progressBar.style.background = 'var(--text-tertiary)';
        }
    }

    /**
     * 显示视频生成进度概览
     */
    showVideoGenerationOverview(shots) {
        const container = document.getElementById('episodeVideoPreview');
        const total = shots.length;

        container.innerHTML = `
            <div class="video-generation-progress">
                <div class="progress-header" style="text-align: center; padding: 2rem;">
                    <h3>🎬 准备批量生成</h3>
                    <p style="color: var(--text-secondary);">共 ${total} 个镜头需要确认生成</p>
                    <p style="font-size: 0.85rem; color: var(--text-tertiary); margin-top: 0.5rem;">
                        每个镜头将显示确认对话框，您可以：编辑提示语、选择参考图、调整参数
                    </p>
                </div>
                <div class="progress-list" style="max-height: 400px; overflow-y: auto; padding: 0 1rem;">
                    ${shots.map((shot, index) => `
                        <div class="video-progress-item" data-shot-index="${index}" id="shot-progress-${index}">
                            <div class="shot-info">
                                <span class="shot-number">镜头 ${index + 1}</span>
                                <span class="shot-title">${shot.episode_title} - ${shot.scene_title}</span>
                            </div>
                            <div class="progress-bar">
                                <div class="progress-bar-fill" style="width: 0%"></div>
                            </div>
                            <span class="status-badge">待确认</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;

        // 添加样式
        this.addProgressStyles();
    }

    /**
     * 添加进度样式
     */
    addProgressStyles() {
        // 检查是否已添加样式
        if (document.getElementById('video-progress-styles')) return;

        const style = document.createElement('style');
        style.id = 'video-progress-styles';
        style.textContent = `
            .video-generation-progress .video-progress-item {
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 0.75rem;
                background: var(--bg-secondary);
                border-radius: 6px;
                margin-bottom: 0.5rem;
            }
            .video-generation-progress .shot-info {
                flex: 1;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }
            .video-generation-progress .shot-number {
                font-weight: bold;
                color: var(--primary-color);
                min-width: 50px;
            }
            .video-generation-progress .shot-title {
                color: var(--text-secondary);
                font-size: 0.85rem;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .video-generation-progress .progress-bar {
                flex: 2;
                height: 8px;
                background: var(--bg-dark);
                border-radius: 4px;
                overflow: hidden;
            }
            .video-generation-progress .progress-bar-fill {
                height: 100%;
                background: linear-gradient(90deg, var(--primary-color), var(--accent-color));
                transition: width 0.3s ease;
            }
            .video-generation-progress .progress-bar-fill.processing {
                animation: progress-pulse 1.5s infinite;
            }
            @keyframes progress-pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .video-generation-progress .status-badge {
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                font-size: 0.75rem;
                background: var(--bg-dark);
                color: var(--text-secondary);
                min-width: 60px;
                text-align: center;
            }
            .video-generation-progress .status-badge.processing {
                background: var(--warning-light);
                color: var(--warning-color);
            }
            .video-generation-progress .status-badge.completed {
                background: var(--success-light);
                color: var(--success-color);
            }
            .video-generation-progress .status-badge.error {
                background: var(--danger-light);
                color: var(--danger-color);
            }
            .video-generation-progress .status-badge.skipped {
                background: var(--bg-tertiary);
                color: var(--text-tertiary);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * 检查指定镜头的视频文件是否已存在
     */
    async checkVideoExists(shot) {
        try {
            // 构造剧集目录名称（与generateAllVideos中的逻辑一致）
            let episodeDirectoryName = '默认';
            if (this.episodeWorkflow.selectedMajorEvent) {
                const majorEvent = this.episodeWorkflow.selectedMajorEvent;
                const majorIndex = majorEvent.major_index || 0;

                const eventTitle = this.sanitizePath(majorEvent.title || majorEvent.name || '');
                episodeDirectoryName = `${majorIndex + 1}集_${eventTitle}`;
            }

            // 调用后端API检查视频是否存在
            const response = await fetch('/api/video/check-exists', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel,
                    episode_title: episodeDirectoryName,
                    event_name: this.sanitizePath(shot.event_name || shot.episode_title || ''),
                    shot_number: shot.shot_number || '',
                    shot_type: (shot.shot_type || 'shot').replace(/\//g, '_')  // 清理斜杠
                })
            });

            const data = await response.json();

            if (data.success && data.exists) {
                return data;
            }

            return null;
        } catch (error) {
            console.error('检查视频是否存在失败:', error);
            return null;
        }
    }

    /**
     * 生成单个视频（使用确认对话框传递的参数）
     */
    async generateSingleVideo(shot, index, total, characterPortraits, selectedImages = null, customPrompt = null, model = 'veo_3_1-fast-components', orientation = 'landscape', size = 'large', useFirstLastFrame = false) {
        try {
            console.log('🔍 [调试] generateSingleVideo 收到的参数:', {
                selectedImagesType: Array.isArray(selectedImages) ? 'array' : typeof selectedImages,
                selectedImagesLength: Array.isArray(selectedImages) ? selectedImages.length : 'N/A',
                selectedImages: selectedImages,
                model: model,
                useFirstLastFrame: useFirstLastFrame
            });

            // 🔥 首尾帧模式需要2张图片
            if (useFirstLastFrame && Array.isArray(selectedImages) && selectedImages.length !== 2) {
                return { success: false, error: '首尾帧模式需要选择2张图片（首帧+尾帧）' };
            }

            // 🔥 处理图片选择：
            // - selectedImages 是数组（包括空数组）：使用用户选择的图片，空数组表示不使用图片
            // - selectedImages 是 null/undefined：自动匹配角色图片
            let imageUrls;
            if (Array.isArray(selectedImages)) {
                // 用户显式选择了图片（可能为空）
                imageUrls = selectedImages;
            } else {
                // 没有传 selectedImages，自动匹配
                imageUrls = this.getPortraitImageUrlsForShot(shot, characterPortraits);
            }

            console.log('🔍 [调试] 最终使用的 imageUrls:', imageUrls.length, '张');

            // 使用确认对话框编辑的提示词，如果没有则使用原始提示词
            const prompt = customPrompt || shot.prompt;

            console.log(`🎬 [生成视频] 镜头 ${index}:`, {
                prompt: prompt.substring(0, 100) + '...',
                imageCount: imageUrls.length,
                model,
                orientation,
                size,
                useFirstLastFrame
            });

            // 🔥 构建包含台词的 prompt，用于 AI 口型同步
            let finalPrompt = prompt;
            const dialogueData = shot.dialogue || shot._dialogue_data;
            if (dialogueData && dialogueData.lines_en && dialogueData.lines_en.trim()) {
                finalPrompt += `. Character speaking: "${dialogueData.lines_en}"`;
            }

            // 调用 VeO API
            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: model,
                    prompt: finalPrompt,
                    image_urls: imageUrls,
                    orientation: orientation,
                    size: size,
                    watermark: false,
                    private: true,
                    // 🔥 传递元数据用于按项目/分集组织视频
                    // 注意：shot.episode_directory_name, shot.event_name, shot.shot_type 都已经过清理
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: shot.episode_directory_name || shot.episode_title || '',
                        event_name: shot.event_name || this.sanitizePath(shot.episode_title || ''),
                        shot_number: shot.shot_number || '',
                        shot_type: shot.shot_type || '',
                        scene_title: shot.scene_title || '',
                        lines_en: dialogueData?.lines_en || ''  // 传递英文台词
                    }
                })
            });

            const result = await response.json();

            if (result.id) {
                console.log(`✅ 镜头 ${index} 生成任务创建成功: ${result.id}`);

                // 轮询检查状态并获取视频URL
                const videoUrl = await this.pollVideoStatusAndGetUrl(result.id);

                if (videoUrl) {
                    return { success: true, videoUrl };
                } else {
                    return { success: false, error: '生成超时或失败' };
                }

            } else if (result.error) {
                throw new Error(result.error?.message || '生成失败');
            }

        } catch (error) {
            console.error(`❌ 镜头 ${index} 生成失败:`, error);
            return { success: false, error: error.message };
        }
    }

    /**
     * 轮询视频生成状态并返回视频URL
     */
    async pollVideoStatusAndGetUrl(videoId) {
        const maxAttempts = 60; // 最多检查5分钟
        const interval = 5000; // 每5秒检查一次

        for (let i = 0; i < maxAttempts; i++) {
            await new Promise(resolve => setTimeout(resolve, interval));

            try {
                const response = await fetch(`/api/veo/status/${videoId}`);
                const result = await response.json();

                if (result.status === 'completed') {
                    console.log(`✅ 视频 ${videoId} 生成完成`, result);

                    // 🔥 获取视频URL - 检查多个可能的位置
                    let videoUrl = null;

                    // 优先级1: result.result.videos[0].url
                    if (result.result?.videos?.[0]?.url) {
                        videoUrl = result.result.videos[0].url;
                    }
                    // 优先级2: result.video_url
                    else if (result.video_url) {
                        videoUrl = result.video_url;
                    }
                    // 优先级3: fallback (仅当URL不包含project-files时使用)
                    else if (!result.result?.videos?.[0]?.url && !result.video_url) {
                        videoUrl = `/static/generated_videos/${videoId}.mp4`;
                    }

                    console.log(`📹 视频 URL: ${videoUrl}`);
                    return videoUrl;
                } else if (result.status === 'failed') {
                    console.error(`❌ 视频 ${videoId} 生成失败`, result);
                    return null;
                }

            } catch (error) {
                console.error('检查状态失败:', error);
            }
        }

        console.warn(`⏰ 视频 ${videoId} 生成超时`);
        return null;
    }

    /**
     * 获取镜头对应的角色剧照URL
     */
    getPortraitImageUrlsForShot(shot, characterPortraits) {
        const urls = [];

        // 从提示词中提取角色名
        for (const [charName, portraitData] of characterPortraits) {
            if (portraitData && portraitData.imageUrl) {
                // 检查这个角色是否在当前镜头中
                if (shot.prompt.includes(charName)) {
                    urls.push(portraitData.imageUrl);
                }
            }
        }

        // 如果没有匹配到角色，使用所有剧照
        if (urls.length === 0) {
            for (const [charName, portraitData] of characterPortraits) {
                if (portraitData && portraitData.imageUrl) {
                    urls.push(portraitData.imageUrl);
                }
            }
        }

        return urls;
    }

    /**
     * 打开视频工作台并传递提示语和剧照
     */
    openVideoStudioWithPrompts() {
        // 准备角色剧照数据
        const characterPortraits = [];
        for (const [charName, portraitData] of this.episodeWorkflow.characterPortraits) {
            if (portraitData && portraitData.imageUrl) {
                characterPortraits.push({
                    name: charName,
                    url: portraitData.imageUrl
                });
            }
        }

        // 准备视频生成数据
        const videoData = {
            novel_title: this.selectedNovel,
            storyboard: this.episodeWorkflow.storyboardData,
            selected_episodes: Array.from(this.episodeWorkflow.selectedEpisodes),
            character_portraits: characterPortraits,  // 🔥 新增：角色剧照
            timestamp: new Date().toISOString()
        };

        console.log('🎬 [视频生成] 准备传递到视频工作台的数据:', videoData);
        console.log(`🎬 [视频生成] 包含 ${characterPortraits.length} 个角色剧照`);

        // 保存到localStorage供视频工作台读取
        localStorage.setItem('videoStudio_importData', JSON.stringify(videoData));

        // 显示提示
        this.showToast(`正在跳转到视频工作台...（包含${characterPortraits.length}个角色剧照）`, 'info');

        // 跳转到视频工作台
        window.open('/video/studio', '_blank');
    }

    /**
     * 执行视频生成
     */
    async executeEpisodeGeneration() {
        const generateBtn = document.getElementById('episodeGenerateBtn');
        generateBtn.disabled = true;
        generateBtn.textContent = '⏳ 生成中...';

        try {
            this.showToast('开始生成视频...', 'success');

            // TODO: 调用API生成视频
            // 这里需要实现实际的API调用

            setTimeout(() => {
                this.showToast('视频生成完成！', 'success');
                generateBtn.textContent = '✅ 生成完成';
            }, 2000);

        } catch (error) {
            console.error('生成失败:', error);
            this.showToast('生成失败: ' + error.message, 'error');
            generateBtn.disabled = false;
            generateBtn.textContent = '🚀 开始生成';
        }
    }

    /**
     * 工作流上一步
     */
    episodeWorkflowPrev() {
        const steps = ['select-episodes', 'check-portraits', 'generate-storyboard', 'generate-video'];
        const currentIndex = steps.indexOf(this.episodeWorkflow.step);
        if (currentIndex > 0) {
            this.showEpisodeWorkflowStep(steps[currentIndex - 1]);
        }
    }

    /**
     * 工作流下一步
     */
    episodeWorkflowNext() {
        // 验证当前步骤
        if (this.episodeWorkflow.step === 'select-episodes') {
            if (this.episodeWorkflow.selectedEpisodes.size === 0) {
                this.showToast('请至少选择一集', 'error');
                return;
            }
        }

        const steps = ['select-episodes', 'check-portraits', 'generate-storyboard', 'generate-video'];
        const currentIndex = steps.indexOf(this.episodeWorkflow.step);
        if (currentIndex < steps.length - 1) {
            this.showEpisodeWorkflowStep(steps[currentIndex + 1]);
        }
    }

    /**
     * 检查并恢复剧照工作台返回的数据
     */
    checkPortraitStudioReturn() {
        const savedPortrait = localStorage.getItem('portraitStudio_result');
        if (savedPortrait) {
            try {
                const data = JSON.parse(savedPortrait);
                // 添加到工作流数据
                this.episodeWorkflow.characterPortraits.set(data.characterName, {
                    imageUrl: data.imageUrl,
                    timestamp: Date.now()
                });
                // 清除保存的数据
                localStorage.removeItem('portraitStudio_result');
                // 刷新当前步骤
                this.loadCharacterPortraitsStep();
                this.showToast('剧照已保存', 'success');
            } catch (e) {
                console.error('解析剧照数据失败:', e);
            }
        }
    }
}

/**
 * 全局函数：下载视频
 */
function downloadVideo(url) {
    if (!url) {
        console.error('下载视频失败：URL为空');
        return;
    }
    console.log('📥 [下载视频] URL:', url);
    // 创建一个隐藏的a标签来触发下载
    const a = document.createElement('a');
    a.href = url;
    a.download = `video_${Date.now()}.mp4`;
    a.target = '_blank';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    console.log('✅ [下载视频] 下载已触发');
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

        // 检查URL参数，处理从短剧风格改造页面跳转过来的情况
        generator.checkURLParams();
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

    // 检查是否从剧照工作台返回
    if (window.videoGenerator) {
        window.videoGenerator.checkPortraitStudioReturn();
    }
});

// 🔥 全局函数：关闭剧照预览模态框
function closePortraitModal() {
    const modal = document.getElementById('portraitModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// 🔥 点击模态框背景关闭
document.addEventListener('click', (e) => {
    const modal = document.getElementById('portraitModal');
    if (modal && e.target === modal) {
        closePortraitModal();
    }
});

// 🔥 ESC键关闭模态框
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closePortraitModal();
    }
});