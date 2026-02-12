/**
 * 短剧工作台 - 前端逻辑
 * 参考按集制作工作流的实现
 */

class ShortDramaStudio {
    constructor() {
        this.currentProject = null;
        this.currentStep = 'select-episodes';
        this.projects = [];
        this.novels = [];
        this.events = [];
        this.characters = [];
        this.characterVoices = {}; // 配音音色映射（默认配置）
        this.characterVoiceMap = {}; // 用户选择的角色-音色映射
        this.selectedNovel = null;
        this.selectedMajorEvent = null;
        this.selectedEpisodes = []; // 🔥 改为数组以保持选择顺序
        this.characterPortraits = new Map();
        this.shots = [];
        this.stopBatchGeneration = false;
        this._improvedData = null; // 用于存储剧本改进数据

        // 后台任务跟踪
        this.backgroundTasks = new Map(); // taskId -> { shotIndex, shot, startTime, progress, status }

        // Konva 无限画布相关
        this.portraitStage = null;
        this.portraitLayer = null;
        this.portraitTransformer = null;
        this.portraitScale = 1;
        this.portraitCanvasItems = [];

        this.init();
    }

    async init() {
        console.log('🎬 [短剧工作台] 初始化...');

        // 绑定事件
        this.bindEvents();

        // 加载项目列表
        await this.loadProjects();

        // 加载小说列表
        await this.loadNovels();

        // 加载TTS音色列表
        await this.loadVoices();

        console.log('✅ [短剧工作台] 初始化完成');
    }

    bindEvents() {
        // 导航按钮
        document.querySelectorAll('.workflow-nav-btn')?.forEach(btn => {
            btn.addEventListener('click', () => {
                const step = btn.dataset.step;
                this.goToStep(step);
            });
        });

        // 重大事件选择（事件委托）
        document.getElementById('majorEventList')?.addEventListener('click', (e) => {
            const option = e.target.closest('.major-event-option');
            if (option) {
                this.selectMajorEvent(option.dataset.eventId);
            }
        });

        // 集数选择 - 使用事件委托
        const episodeListEl = document.getElementById('episodeList');
        if (episodeListEl) {
            episodeListEl.addEventListener('click', (e) => {
                const item = e.target.closest('.episode-item');
                if (!item) return;

                const checkbox = item.querySelector('.episode-checkbox');
                const episodeId = item.dataset.episodeId;

                // 如果点击的是复选框，切换状态
                if (e.target.classList.contains('episode-checkbox')) {
                    const isChecked = e.target.checked;
                    this.toggleEpisodeSelection(episodeId, isChecked);
                }
                // 如果点击的是整个项，也切换复选框状态
                else if (checkbox) {
                    checkbox.checked = !checkbox.checked;
                    this.toggleEpisodeSelection(episodeId, checkbox.checked);
                }
            });
        }

        // 全选/清空按钮
        document.getElementById('selectAllEpisodesBtn')?.addEventListener('click', () => {
            this.selectAllEpisodes(true);
        });

        document.getElementById('clearEpisodesBtn')?.addEventListener('click', () => {
            this.selectAllEpisodes(false);
        });

        // 返回按钮
        document.getElementById('backToModeFromEpisodeBtn')?.addEventListener('click', () => {
            this.backToProjects();
        });

        // Gemini配置按钮
        document.getElementById('geminiConfigBtn')?.addEventListener('click', () => {
            this.showGeminiConfig();
        });

        // 从小说创建按钮
        document.getElementById('createFromNovelBtn')?.addEventListener('click', () => {
            this.createFromNovel();
        });

        // 从创意创建按钮
        document.getElementById('createFromIdeaBtn')?.addEventListener('click', () => {
            this.openIdeaModal();
        });

        // 设置变更监听
        document.getElementById('settingAspectRatio')?.addEventListener('change', () => {
            this.onSettingChange();
        });
        document.getElementById('settingQuality')?.addEventListener('change', () => {
            this.onSettingChange();
        });
        document.getElementById('settingModel')?.addEventListener('change', () => {
            this.onSettingChange();
        });

        // JSON导入输入监听（实时验证）
        document.getElementById('jsonImportInput')?.addEventListener('input', () => {
            this.validateJson();
        });

        // 监听从剧照工作室返回
        window.addEventListener('storage', (e) => {
            if (e.key === 'portraitStudio_result' && e.newValue) {
                console.log('📸 检测到剧照已保存，刷新角色剧照列表');
                this.loadVisualAssetsStep();
            }
        });

        // 页面重新可见时刷新剧照（带防重复加载锁）
        this._refreshingAssets = false;
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.currentStep === 'check-portraits' && !this._refreshingAssets) {
                this._refreshingAssets = true;
                console.log('📸 页面重新可见，刷新角色剧照列表');
                this.loadVisualAssetsStep().finally(() => {
                    this._refreshingAssets = false;
                });
            }
        });

        // 侧边栏折叠按钮
        document.getElementById('toggleLeftPanel')?.addEventListener('click', () => {
            this.togglePanel('left');
        });
        document.getElementById('toggleRightPanel')?.addEventListener('click', () => {
            this.togglePanel('right');
        });
    }

    /**
    /**
     * 加载小说列表
     */
    async loadNovels() {
        try {
            // 使用正确的API路径
            const response = await fetch('/api/video/novels');
            const data = await response.json();

            if (data.success) {
                this.novels = data.novels || [];
                this.renderNovelSelect();
            }
        } catch (error) {
            console.error('加载小说失败:', error);
        }
    }

    /**
     * 渲染小说选择下拉框
     */
    renderNovelSelect() {
        const select = document.getElementById('novelSelect');
        if (!select) return;

        select.innerHTML = '<option value="">选择小说项目...</option>' +
            this.novels.map(novel => `
                <option value="${novel.title}">${novel.title}</option>
            `).join('');
    }

    /**
     * 加载TTS音色列表
     */
    async loadVoices() {
        try {
            const response = await fetch('/api/tts/voices');
            const data = await response.json();

            if (data.success) {
                // 优先使用后端返回的 character_voices 映射
                if (data.character_voices) {
                    this.characterVoices = data.character_voices;
                } else if (data.voices) {
                    // 兼容旧格式：从 voices 数组构建映射
                    this.characterVoices = {};
                    data.voices.forEach(voice => {
                        // 新格式：voice.id, voice.name
                        // 旧格式：voice.voice_id, voice.character
                        const id = voice.id || voice.voice_id;
                        const name = voice.name || voice.character;
                        if (id && name) {
                            this.characterVoices[name] = id;
                        }
                    });
                }
                console.log('🎙️ [TTS] 音色列表已加载:', this.characterVoices);
            } else {
                // 使用默认音色
                this.characterVoices = {
                    '林战': 'male-qn-qingse',
                    '大长老': 'male-qn-jingying',
                    '三长老': 'male-qn-badao',
                    '叶凡': 'male-qn-qingse',
                    '旁白': 'male-qn-qingse',
                    '系统音': 'female-tianmei',
                    '林啸天': 'male-qn-daxuesheng',
                    '默认': 'male-qn-qingse'
                };
            }
        } catch (error) {
            console.error('加载音色列表失败:', error);
            // 使用默认音色
            this.characterVoices = {
                '林战': 'male-qn-qingse',
                '大长老': 'male-qn-jingying',
                '三长老': 'male-qn-yuansu',
                '叶凡': 'male-qn-qingche',
                '旁白': 'male-qn-pingshu',
                '系统音': 'female-qn-dahu',
                '林啸天': 'male-qn-wengeng',
                '默认': 'female-qn-dahu'
            };
        }
    }

    /**
     * 创建新项目
     */
    async createNewProject() {
        const title = prompt('请输入项目名称:');
        if (!title) return;

        try {
            const response = await fetch('/api/short-drama/projects', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('项目创建成功', 'success');
                await this.loadProjects();
            } else {
                this.showToast(data.error || '创建项目失败', 'error');
            }
        } catch (error) {
            console.error('创建项目失败:', error);
            this.showToast('创建项目失败', 'error');
        }
    }

    /**
     * 从小说创建项目并启动工作流
     */
    async createFromNovel() {
        const novelTitle = document.getElementById('novelSelect')?.value;
        if (!novelTitle) {
            this.showToast('请选择小说项目', 'warning');
            return;
        }

        this.selectedNovel = novelTitle;

        // 检查是否已存在该项目
        const existingProject = this.projects.find(p => p.title === novelTitle);

        if (existingProject) {
            // 如果项目已存在，直接打开
            console.log('📺 [工作流] 项目已存在，直接打开:', existingProject.id);
            this.openProject(existingProject.id);
        } else {
            // 如果项目不存在，创建新项目
            try {
                const response = await fetch('/api/short-drama/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: novelTitle })
                });

                const data = await response.json();
                if (data.success) {
                    this.showToast('项目创建成功', 'success');
                    await this.loadProjects();
                    // 直接启动工作流
                    await this.startWorkflowFromNovel(novelTitle);
                } else {
                    this.showToast(data.error || '创建项目失败', 'error');
                }
            } catch (error) {
                console.error('创建项目失败:', error);
                this.showToast('创建项目失败', 'error');
            }
        }
    }

    /**
     * 从小说启动工作流
     */
    async startWorkflowFromNovel(novelTitle) {
        console.log('📺 [工作流] 从小说启动:', novelTitle);

        this.selectedNovel = novelTitle;

        // 查找是否已有项目，如果有则加载其设置
        const existingProject = this.projects.find(p => p.title === novelTitle);
        if (existingProject) {
            this.currentProject = existingProject;
            this.loadProjectSettings(existingProject.settings);
        } else {
            this.currentProject = { title: novelTitle };
        }

        // 加载事件和角色数据
        await this.loadEventsAndCharacters();

        // 切换到工作区视图
        const listView = document.getElementById('projectListView');
        const workspaceView = document.getElementById('projectWorkspaceView');
        console.log('🔄 [视图切换] 切换前:', {
            listView: listView?.className,
            workspaceView: workspaceView?.className
        });
        listView?.classList.remove('active');
        workspaceView?.classList.add('active');
        console.log('🔄 [视图切换] 切换后:', {
            listView: listView?.className,
            workspaceView: workspaceView?.className
        });
        document.getElementById('currentProjectName').textContent = `📺 ${novelTitle} - 按集制作`;

        // 加载重大事件
        await this.loadMajorEvents();

        // 显示第一步
        this.goToStep('select-episodes');
    }

    /**
     * 加载事件和角色数据
     */

    /**
     * 构建事件树
     */
    buildEventTree(data) {
        const events = [];

        // 从数据中提取事件 - API返回的是events字段
        const eventData = data.events || [];

        eventData.forEach((major, idx) => {
            // 处理children - 优先从composition中提取（创意导入项目）
            let children = [];

            if (major.composition && typeof major.composition === 'object' && Object.keys(major.composition).length > 0) {
                // composition 是一个包含 '起', '承', '转', '合' 的对象
                const phases = ['起', '承', '转', '合'];
                let sceneIndex = 0;
                phases.forEach(phase => {
                    if (major.composition[phase] && Array.isArray(major.composition[phase])) {
                        major.composition[phase].forEach(scene => {
                            // 确保每个场景都有id
                            const sceneWithId = {
                                ...scene,
                                id: scene.id || `scene_${sceneIndex}`,
                                phase: phase
                            };
                            children.push(sceneWithId);
                            sceneIndex++;
                        });
                    }
                });
            } else if (major.children) {
                // 普通小说项目的children结构
                children = major.children;
            }

            events.push({
                id: major.id || `major_${idx}`,
                title: major.title || major.name,
                name: major.title || major.name,
                type: 'major',
                description: major.description || '',
                stage: major.stage,
                children: children,
                children_count: major.children_count || children.length,
                has_children: children.length > 0,
                chapter_range: major.chapter_range,
                characters: major.characters,
                location: major.location,
                emotion: major.emotion
            });
        });

        return events;
    }

    /**
     * 加载重大事件列表
     */
    async loadMajorEvents() {
        const container = document.getElementById('majorEventList');
        if (!container) return;

        if (this.events.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>暂无重大事件</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在小说中配置事件系统
                    </p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.events.map((event, idx) => {
            // 🔥 判断是否是创意导入项目的事件
            const isCreativeImport = event.id && event.id.includes('creative_import');
            
            // 🔥 对于创意导入项目，显示"第X集"而不是"X集"
            // children_count 在这里表示镜头数，不是集数
            const countLabel = isCreativeImport 
                ? `第${idx + 1}集 · ${event.children_count || 0}镜头`
                : `${event.children_count || 0}集`;
            
            return `
            <div class="major-event-item ${isCreativeImport ? 'creative-import' : ''}" data-event-id="${event.id}">
                <div class="event-name">${event.title}</div>
                <div class="event-info">
                    <span class="episode-count">${countLabel}</span>
                    ${event.description ? `<span class="event-desc">${event.description.substring(0, 40)}${event.description.length > 40 ? '...' : ''}</span>` : ''}
                </div>
            </div>
        `}).join('');
    }

    /**
     * 选择重大事件
     */
    selectMajorEvent(eventId) {
        console.log('📺 [工作流] 选择重大事件:', eventId);

        const event = this.events.find(e => e.id === eventId);
        if (!event) return;

        this.selectedMajorEvent = event;

        // 🔥 调试：输出重大事件的完整数据
        console.log('📺 [工作流] 重大事件完整数据:', JSON.stringify(event, null, 2));
        console.log('📺 [工作流] 子事件数量:', event.children?.length || 0);
        console.log('📺 [工作流] 子事件数据:', event.children);

        // 更新选中状态
        document.querySelectorAll('.major-event-item').forEach(item => {
            item.classList.remove('selected');
        });
        const selectedItem = document.querySelector(`.major-event-item[data-event-id="${eventId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('selected');
        }

        // 显示集数列表
        this.showEpisodeList(event);
    }


    /**
     * 切换工作流步骤
     */
    goToStep(step, forceReload = false) {
        // 🔥 步骤依赖检查
        const dependencies = {
            'select-episodes': [],
            'check-portraits': ['select-episodes'],
            'story-beats': ['select-episodes'],
            'storyboard': ['select-episodes', 'check-portraits'],
            'video': ['storyboard'],
            'dubbing': ['storyboard'],
            'export': ['video', 'dubbing']
        };

        // 检查依赖是否满足
        const requiredSteps = dependencies[step] || [];
        for (const requiredStep of requiredSteps) {
            if (!this.checkStepCompleted(requiredStep)) {
                const stepNames = {
                    'select-episodes': '选集',
                    'check-portraits': '视觉资产库',
                    'story-beats': '故事节拍',
                    'storyboard': '分镜生成',
                    'video': '生成视频',
                    'dubbing': '配音制作',
                    'export': '导出'
                };

                this.showToast(`⚠️ 请先完成"${stepNames[requiredStep]}"步骤`, 'warning');
                console.warn(`⚠️ [步骤检查] 无法进入"${stepNames[step]}"，需要先完成"${stepNames[requiredStep]}"`);
                return;
            }
        }

        this.currentStep = step;

        // 更新步骤导航状态
        document.querySelectorAll('.step-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.step === step) {
                item.classList.add('active');
            }
        });

        // 更新内容显示
        document.querySelectorAll('.step-content').forEach(content => {
            content.classList.remove('active');
        });

        const stepContent = document.getElementById(`${step}Step`);
        if (stepContent) {
            stepContent.classList.add('active');
        }

        // 🔥 控制侧边栏显示：只在选集步骤显示侧边栏
        const workspace = document.querySelector('.workspace-content');
        if (step === 'select-episodes') {
            // 选集步骤：显示侧边栏
            workspace?.classList.remove('hide-side-panels');
        } else {
            // 其他步骤：隐藏侧边栏
            workspace?.classList.add('hide-side-panels');
        }

        // 视频生成模式下隐藏侧边栏
        if (step === 'video' || step === 'dubbing') {
            workspace?.classList.add('video-mode');
        } else {
            workspace?.classList.remove('video-mode');
        }

        // 初始化已加载步骤跟踪
        if (!this.loadedSteps) {
            this.loadedSteps = new Set();
        }

        // 根据步骤加载内容（仅未加载过或强制刷新时）
        switch (step) {
            case 'check-portraits':
                if (!this.loadedSteps.has('check-portraits') || forceReload) {
                    this.loadVisualAssetsStep();
                    this.loadedSteps.add('check-portraits');
                }
                break;
            case 'story-beats':
                if (!this.loadedSteps.has('story-beats') || forceReload) {
                    this.renderStoryBeatsStep();
                    this.loadedSteps.add('story-beats');
                }
                break;
            case 'storyboard':
                if (!this.loadedSteps.has('storyboard') || forceReload) {
                    this.loadStoryboardStep();
                    this.loadedSteps.add('storyboard');
                }
                break;
            case 'video':
                if (!this.loadedSteps.has('video') || forceReload) {
                    this.loadVideoStep();
                    this.loadedSteps.add('video');
                }
                break;
            case 'dubbing':
                if (!this.loadedSteps.has('dubbing') || forceReload) {
                    this.loadDubbingStep();
                    this.loadedSteps.add('dubbing');
                }
                break;
            case 'export':
                if (!this.loadedSteps.has('export') || forceReload) {
                    this.loadExportStep();
                    this.loadedSteps.add('export');
                }
                break;
        }
    }

    /**
     * 检查步骤是否已完成
     */
    checkStepCompleted(step) {
        switch (step) {
            case 'select-episodes':
                // 检查是否选择了集数
                return this.selectedEpisodes && this.selectedEpisodes.length > 0;

            case 'check-portraits':
                // 检查是否有视觉资产数据
                return this.currentProject?.visualAssets &&
                    (Object.keys(this.currentProject.visualAssets.characters || {}).length > 0 ||
                     Object.keys(this.currentProject.visualAssets.scenes || {}).length > 0);

            case 'story-beats':
                // 故事节拍步骤是可选的，总是返回true
                return true;

            case 'storyboard':
                // 检查是否有分镜数据
                return this.currentProject?.shots?.length > 0 || this.shots?.length > 0;

            case 'video':
                // 视频步骤依赖分镜数据，不需要已生成视频
                return this.currentProject?.shots?.length > 0 || this.shots?.length > 0;

            case 'dubbing':
                // 配音步骤依赖分镜数据，不需要视频完成
                return this.currentProject?.shots?.length > 0 || this.shots?.length > 0;

            default:
                return true;
        }
    }

    /**
     * 显示 Toast 通知
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            padding: 12px 24px;
            background: ${type === 'warning' ? '#f59e0b' : type === 'error' ? '#ef4444' : '#6366f1'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 10001;
            font-size: 14px;
            font-weight: 500;
            animation: slideDown 0.3s ease;
        `;
        toast.textContent = message;

        // 添加动画样式
        if (!document.getElementById('toast-animation-style')) {
            const style = document.createElement('style');
            style.id = 'toast-animation-style';
            style.textContent = `
                @keyframes slideDown {
                    from {
                        opacity: 0;
                        transform: translateX(-50%) translateY(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateX(-50%) translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(toast);

        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'slideDown 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * 从 API 加载视觉资产
     */
    async loadVisualAssetsFromAPI() {
        try {
            if (!this.currentProject?.id) return;

            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}/visual-assets`);
            const data = await response.json();

            if (data.success) {
                // 初始化视觉资产结构
                if (!this.currentProject.visualAssets) {
                    this.currentProject.visualAssets = { characters: {}, scenes: {}, props: {} };
                }

                // 合并 API 数据
                this.currentProject.visualAssets = {
                    characters: data.data?.characters || {},
                    scenes: data.data?.scenes || {},
                    props: data.data?.props || {}
                };

                console.log('✅ [视觉资产库] 从 API 加载完成:', 
                    Object.keys(this.currentProject.visualAssets.characters).length, '角色,',
                    Object.keys(this.currentProject.visualAssets.scenes).length, '场景,',
                    Object.keys(this.currentProject.visualAssets.props).length, '道具'
                );
            }
        } catch (error) {
            console.error('❌ [视觉资产库] API 加载失败:', error);
            // 使用本地数据
            if (!this.currentProject.visualAssets) {
                this.currentProject.visualAssets = { characters: {}, scenes: {}, props: {} };
            }
        }
    }

    /**
     * 初始化视觉资产库面板
     */

    /**
     * 加载素材网格
     */

    /**
     * 选中视觉资产
     */

    /**
     * 保存资产描述
     */
    async saveAssetDescription(name, type) {
        const description = document.getElementById('vaAssetDescription')?.value;
        if (!description) {
            this.showToast('请输入描述', 'warning');
            return;
        }

        // 收集额外字段
        const extraData = { description };
        
        if (type === 'character') {
            const clothing = document.getElementById('vaCharClothing')?.value;
            const expression = document.getElementById('vaCharExpression')?.value;
            if (clothing) extraData.clothing = clothing;
            if (expression) extraData.expression = expression;
        } else if (type === 'scene') {
            const lighting = document.getElementById('vaSceneLighting')?.value;
            const colorTone = document.getElementById('vaSceneColorTone')?.value;
            if (lighting) extraData.lighting = lighting;
            if (colorTone) extraData.colorTone = colorTone;
        } else if (type === 'prop') {
            const category = document.getElementById('vaPropCategory')?.value;
            if (category) extraData.category = category;
        }

        // 本地更新
        if (!this.currentProject.visualAssets) {
            this.currentProject.visualAssets = {};
        }
        if (!this.currentProject.visualAssets[type + 's']) {
            this.currentProject.visualAssets[type + 's'] = {};
        }
        this.currentProject.visualAssets[type + 's'][name] = {
            ...this.currentProject.visualAssets[type + 's'][name],
            ...extraData,
            updatedAt: new Date().toISOString()
        };

        // 同步到后端 API
        try {
            if (this.currentProject?.id) {
                const categoryMap = {
                    'character': 'characters',
                    'scene': 'scenes',
                    'prop': 'props'
                };
                const category = categoryMap[type];

                const response = await fetch(
                    `/api/projects/${this.currentProject.id}/visual-assets/${category}/${encodeURIComponent(name)}`,
                    {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(extraData)
                    }
                );

                const data = await response.json();
                if (data.success) {
                    this.showToast('✓ 描述已保存到服务器', 'success');
                } else {
                    this.showToast('✓ 已保存本地（后端同步失败）', 'warning');
                }
            } else {
                this.showToast('✓ 已保存本地', 'success');
            }
        } catch (error) {
            console.error('保存到后端失败:', error);
            this.showToast('✓ 已保存本地（后端同步失败）', 'warning');
        }
    }

    /**
     * 保存所有视觉资产到项目（用于分镜生成前同步）
     */

    /**
     * 上传视觉资产
     */

    /**
     * 创建视觉资产 - 使用已有 API 创建场景/道具
     */
    async generateVisualAsset() {
        const activeTab = document.querySelector('.va-category-tab.active');
        const category = activeTab?.dataset.category || 'characters';
        
        const categoryMap = {
            'characters': { name: '角色', icon: '🎭' },
            'scenes': { name: '场景', icon: '🏞️' },
            'props': { name: '道具', icon: '🎒' }
        };
        
        const info = categoryMap[category];
        
        // 角色暂不支持在此创建
        if (category === 'characters') {
            this.showToast(`🎭 角色请通过"导入角色"添加`, 'info');
            return;
        }
        
        // 显示创建对话框
        const name = prompt(`输入${info.name}名称:`, '');
        if (!name) return;
        
        const description = prompt('输入标准描述:', '');
        if (!description) return;
        
        // 根据类别收集额外字段
        const options = {};
        if (category === 'scenes') {
            const lighting = prompt('光线（可选）:', '');
            const colorTone = prompt('色调（可选）:', '');
            if (lighting) options.lighting = lighting;
            if (colorTone) options.colorTone = colorTone;
        } else if (category === 'props') {
            const propCategory = prompt('分类（可选，如:武器、饰品）:', '');
            if (propCategory) options.category = propCategory;
        }
        
        try {
            this.showToast(`⏳ 正在创建${info.name}...`, 'info');
            
            // 使用已有的 POST API 创建
            const result = await this.createVisualAsset(category, name, description, options);
            
            if (result) {
                this.showToast(`✅ ${info.name}「${name}」创建成功`, 'success');
                // 刷新网格
                this.loadVisualAssetsGrid(category);
                // 自动选中新创建的资产
                this.selectVisualAsset(category === 'scenes' ? 'scene' : 'prop', result, '');
            }
        } catch (error) {
            console.error('创建视觉资产失败:', error);
            this.showToast('❌ 创建失败，请重试', 'error');
        }
    }

    /**
     * 验证资产名称是否合法
     */
    validateAssetName(name) {
        if (!name || !name.trim()) {
            return { valid: false, error: '名称不能为空' };
        }
        
        const illegalChars = ['\\', '/', '*', '?', ':', '"', '<', '>', '|'];
        for (const char of illegalChars) {
            if (name.includes(char)) {
                return { valid: false, error: `名称不能包含特殊字符: "${char}"` };
            }
        }
        
        if (name.length > 50) {
            return { valid: false, error: '名称长度不能超过50个字符' };
        }
        
        return { valid: true };
    }

    /**
     * 创建新的视觉资产（用于场景和道具）
     */
    async createVisualAsset(category, name, description, options = {}) {
        if (!this.currentProject?.id) {
            this.showToast('请先创建项目', 'warning');
            return null;
        }
        
        // 🔥 验证名称合法性
        const validation = this.validateAssetName(name);
        if (!validation.valid) {
            this.showToast(`⚠️ ${validation.error}`, 'warning');
            return null;
        }
        
        try {
            const response = await fetch(`/api/projects/${this.currentProject.id}/visual-assets/${category}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    ...options
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                // 更新本地数据
                if (!this.currentProject.visualAssets) {
                    this.currentProject.visualAssets = { characters: {}, scenes: {}, props: {} };
                }
                if (!this.currentProject.visualAssets[category]) {
                    this.currentProject.visualAssets[category] = {};
                }
                this.currentProject.visualAssets[category][name] = data.data;
                
                // 刷新网格
                this.loadVisualAssetsGrid(category);
                
                return data.data;
            } else {
                this.showToast(`❌ 创建失败: ${data.error}`, 'error');
                return null;
            }
        } catch (error) {
            console.error('创建视觉资产失败:', error);
            this.showToast('❌ 创建失败', 'error');
            return null;
        }
    }

    /**
     * 加载剧照信息
     */
    async loadPortraits() {
        try {
            // 获取当前选中重大事件的目录名
            if (!this.selectedMajorEvent) {
                console.log('🎭 [剧照] 没有选中重大事件');
                return;
            }

            const episodeDirectoryName = this.getEpisodeDirectoryName();

            console.log('🎭 [剧照] 加载剧照目录:', this.selectedNovel, episodeDirectoryName);

            const response = await fetch(`/api/short-drama/portraits?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            if (data.success && data.portraits) {
                // 清空旧数据
                this.characterPortraits.clear();

                // 建立角色名 -> 剧照信息的映射
                for (const portrait of data.portraits) {
                    this.characterPortraits.set(portrait.character, portrait);
                }

                console.log('✅ [剧照] 加载了', this.characterPortraits.size, '个角色的剧照');
            } else {
                console.log('🎭 [剧照] 没有找到剧照:', data.error);
            }
        } catch (error) {
            console.error('❌ [剧照] 加载失败:', error);
        }
    }

    /**
     * 打开图片生成配置模态框
     */
    openImageGenConfigModal() {
        const modal = document.getElementById('imageGenConfigModal');
        if (!modal) return;
        
        // 加载已保存的配置
        const config = this.getImageGenConfig();
        document.getElementById('imgGenProvider').value = config.provider || '';
        document.getElementById('imgGenApiUrl').value = config.apiUrl || '';
        document.getElementById('imgGenApiKey').value = config.apiKey || '';
        document.getElementById('imgGenModel').value = config.model || '';
        document.getElementById('imgGenSize').value = config.size || '1024x1024';
        document.getElementById('imgGenSaveToProject').checked = config.saveToProject || false;
        
        modal.style.display = 'flex';
    }

    /**
     * 关闭图片生成配置模态框
     */
    closeImageGenConfigModal() {
        const modal = document.getElementById('imageGenConfigModal');
        if (modal) modal.style.display = 'none';
    }

    /**
     * 保存图片生成配置
     */
    async saveImageGenConfig() {
        const config = {
            provider: document.getElementById('imgGenProvider').value,
            apiUrl: document.getElementById('imgGenApiUrl').value.trim(),
            apiKey: document.getElementById('imgGenApiKey').value.trim(),
            model: document.getElementById('imgGenModel').value,
            size: document.getElementById('imgGenSize').value,
            saveToProject: document.getElementById('imgGenSaveToProject').checked
        };
        
        // 验证必填字段
        if (!config.provider) {
            this.showToast('请选择服务提供商', 'warning');
            return;
        }
        if (!config.apiUrl) {
            this.showToast('请输入 API URL', 'warning');
            return;
        }
        
        // 保存到本地存储
        localStorage.setItem('shortDrama_imageGenConfig', JSON.stringify({
            provider: config.provider,
            apiUrl: config.apiUrl,
            model: config.model,
            size: config.size,
            // 注意：API Key 单独存储以提高安全性
        }));
        
        if (config.apiKey) {
            localStorage.setItem('shortDrama_imageGenApiKey', config.apiKey);
        }
        
        // 如果选择保存到项目，则同步到项目配置
        if (config.saveToProject && this.currentProject?.id) {
            try {
                const projectConfig = {
                    imageGen: {
                        provider: config.provider,
                        apiUrl: config.apiUrl,
                        model: config.model,
                        size: config.size
                        // API Key 不保存到项目
                    }
                };
                
                const response = await fetch(`/api/projects/${this.currentProject.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ settings: projectConfig })
                });
                
                if (response.ok) {
                    this.showToast('配置已保存到项目', 'success');
                }
            } catch (error) {
                console.error('保存项目配置失败:', error);
            }
        }
        
        this.closeImageGenConfigModal();
        this.showToast('💾 图片生成配置已保存', 'success');
    }

    /**
     * Get image generation config
     */
    getImageGenConfig() {
        let config = {};
        if (this.currentProject?.settings?.imageGen) {
            config = { ...this.currentProject.settings.imageGen };
        }
        
        const localConfig = localStorage.getItem('shortDrama_imageGenConfig');
        if (localConfig) {
            try {
                const parsed = JSON.parse(localConfig);
                config = { ...config, ...parsed };
            } catch (e) {
                console.error('Parse local config failed:', e);
            }
        }
        
        const apiKey = localStorage.getItem('shortDrama_imageGenApiKey');
        if (apiKey) {
            config.apiKey = apiKey;
        }
        
        return config;
    }

    /**
     * 获取系统默认图片生成配置（从CONFIG）
     */
    getSystemImageGenConfig() {
        // 这些是与config/config.py中nanobanana配置对应的默认值
        return {
            provider: 'nano-banana',
            apiUrl: 'https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent',
            model: 'gemini-3-pro-image-preview',
            size: '2K'  // 默认2K竖屏 (1440x2560)，可选 1K/2K/4K
        };
    }

    /**
     * Show image generation config modal
     */
    async showImageGenConfig() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: flex;
            justify-content: center; align-items: center; z-index: 10000;
        `;

        // 获取系统默认配置
        const systemConfig = this.getSystemImageGenConfig();
        
        // 从后端获取当前配置
        let config = this.getImageGenConfig();
        try {
            const response = await fetch('/api/image-gen/config');
            const result = await response.json();
            if (result.success && result.configured) {
                config = {
                    provider: result.provider || config.provider,
                    apiUrl: result.api_url || config.apiUrl,
                    apiKey: result.api_key || config.apiKey,
                    model: result.model || config.model,
                    size: result.size || config.size
                };
            }
        } catch (e) {
            console.log('获取后端配置失败，使用本地缓存:', e);
        }
        
        // 优先级：已保存配置 > 系统默认配置
        const finalConfig = {
            provider: config.provider || systemConfig.provider,
            apiUrl: config.apiUrl || systemConfig.apiUrl,
            apiKey: config.apiKey || '',
            model: config.model || systemConfig.model,
            size: config.size || systemConfig.size
        };
        
        // 获取项目方向设置
        const settings = this.currentProject?.settings || {};
        const aspectRatio = settings.aspect_ratio || '9:16';
        const isLandscape = aspectRatio === '16:9';
        const isSquare = aspectRatio === '1:1';
        const orientationText = isLandscape ? '横屏' : (isSquare ? '方形' : '竖屏');

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-secondary); border-radius: 16px;
                max-width: 500px; width: 90%; padding: 2rem;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="margin: 0;">🖼️ 图片生成配置</h2>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">✕</button>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">服务提供商</label>
                    <select id="imgGenProviderModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="" style="background: var(--bg-dark); color: var(--text-primary);">-- 请选择 --</option>
                        <option value="nano-banana" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'nano-banana' ? 'selected' : ''}>Nano Banana (推荐)</option>
                        <option value="openai" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'openai' ? 'selected' : ''}>OpenAI (DALL-E)</option>
                        <option value="stability" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'stability' ? 'selected' : ''}>Stability AI</option>
                        <option value="midjourney" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'midjourney' ? 'selected' : ''}>Midjourney API</option>
                        <option value="custom" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'custom' ? 'selected' : ''}>自定义</option>
                    </select>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API URL</label>
                    <input type="text" id="imgGenApiUrlModal" value="${finalConfig.apiUrl || ''}" placeholder="https://api.nanobanana.com/v1/images" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Key</label>
                    <input type="password" id="imgGenApiKeyModal" value="${finalConfig.apiKey || ''}" placeholder="请输入API Key" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                        🔒 配置将保存到服务器
                    </div>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认模型</label>
                    <select id="imgGenModelModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="" style="background: var(--bg-dark); color: var(--text-primary);">-- 请选择 --</option>
                        <optgroup label="Nano Banana" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="flux-1.1-pro" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-1.1-pro' ? 'selected' : ''}>FLUX 1.1 Pro (推荐)</option>
                            <option value="flux-pro" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-pro' ? 'selected' : ''}>FLUX Pro</option>
                            <option value="flux-dev" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-dev' ? 'selected' : ''}>FLUX Dev</option>
                            <option value="flux-schnell" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-schnell' ? 'selected' : ''}>FLUX Schnell (快速)</option>
                        </optgroup>
                        <optgroup label="OpenAI" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="dall-e-3" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'dall-e-3' ? 'selected' : ''}>DALL-E 3</option>
                            <option value="dall-e-2" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'dall-e-2' ? 'selected' : ''}>DALL-E 2</option>
                        </optgroup>
                        <optgroup label="Stability AI" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="sd-xl" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'sd-xl' ? 'selected' : ''}>Stable Diffusion XL</option>
                            <option value="sd-3" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'sd-3' ? 'selected' : ''}>Stable Diffusion 3</option>
                        </optgroup>
                    </select>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认尺寸 (${orientationText})</label>
                    <select id="imgGenSizeModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="4K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '4K' ? 'selected' : ''}>4K (${isLandscape ? '3840x2160' : (isSquare ? '2160x2160' : '2160x3840')} ${orientationText} 推荐)</option>
                        <option value="2K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '2K' ? 'selected' : ''}>2K (${isLandscape ? '2560x1440' : (isSquare ? '1440x1440' : '1440x2560')} ${orientationText})</option>
                        <option value="1K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '1K' ? 'selected' : ''}>1K (${isLandscape ? '1920x1080' : (isSquare ? '1080x1080' : '1080x1920')} ${orientationText})</option>
                    </select>
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                        💡 当前项目设置为${orientationText} (${aspectRatio})，尺寸对应 NanoBanana 服务的 1K/2K/4K 规格
                    </div>
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                    <button id="saveImgGenConfigBtn" class="btn btn-primary" style="flex: 1;">保存配置</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()" style="flex: 1;">取消</button>
                </div>

                <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                    <p style="margin: 0 0 0.5rem 0;">📌 获取Nano Banana API密钥：</p>
                    <ol style="margin: 0; padding-left: 1.5rem;">
                        <li>访问 <a href="https://nanobanana.com" target="_blank" style="color: var(--primary);">Nano Banana官网</a></li>
                        <li>注册并登录账号</li>
                        <li>在控制台创建API Key</li>
                    </ol>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // 保存配置
        const saveBtn = modal.querySelector('#saveImgGenConfigBtn');
        saveBtn.addEventListener('click', async () => {
            const provider = modal.querySelector('#imgGenProviderModal').value;
            const apiUrl = modal.querySelector('#imgGenApiUrlModal').value.trim();
            const apiKey = modal.querySelector('#imgGenApiKeyModal').value.trim();
            const model = modal.querySelector('#imgGenModelModal').value;
            const size = modal.querySelector('#imgGenSizeModal').value;

            if (!provider) {
                this.showToast('请选择服务提供商', 'warning');
                return;
            }
            if (!apiUrl) {
                this.showToast('请输入 API URL', 'warning');
                return;
            }
            if (!apiKey) {
                this.showToast('请输入 API Key', 'warning');
                return;
            }

            // 保存到localStorage
            localStorage.setItem('shortDrama_imageGenConfig', JSON.stringify({
                provider: provider,
                apiUrl: apiUrl,
                model: model,
                size: size
            }));
            localStorage.setItem('shortDrama_imageGenApiKey', apiKey);

            // 同步到后端
            try {
                const response = await fetch('/api/image-gen/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider: provider,
                        api_url: apiUrl,
                        api_key: apiKey,
                        model: model,
                        size: size
                    })
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('💾 图片生成配置已保存并生效', 'success');
                    modal.remove();
                } else {
                    this.showToast(`保存失败: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('保存图片配置失败:', error);
                this.showToast('保存失败，请检查网络', 'error');
            }
        });
    }

    /**
     * 生成图片（使用配置的服务）
     */
    async generateImage(prompt, options = {}) {
        const config = this.getImageGenConfig();
        
        if (!config.apiUrl || !config.apiKey) {
            this.showToast('请先配置图片生成服务', 'warning');
            this.showImageGenConfig();
            return null;
        }
        
        try {
            this.showToast('🎨 正在生成图片...', 'info');
            
            const requestBody = {
                prompt: prompt,
                model: options.model || config.model || 'dall-e-3',
                size: options.size || config.size || '1024x1024',
                n: 1,
                ...options
            };
            
            const response = await fetch(config.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${config.apiKey}`
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || `生成失败: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 解析不同 API 格式
            let imageUrl = null;
            if (data.data?.[0]?.url) {
                imageUrl = data.data[0].url; // OpenAI 格式
            } else if (data.artifacts?.[0]?.base64) {
                imageUrl = `data:image/png;base64,${data.artifacts[0].base64}`; // Stability 格式
            } else if (data.image_url) {
                imageUrl = data.image_url; // 通用格式
            }
            
            if (imageUrl) {
                this.showToast('✅ 图片生成成功', 'success');
                return imageUrl;
            } else {
                throw new Error('未能获取图片 URL');
            }
            
        } catch (error) {
            console.error('图片生成失败:', error);
            this.showToast(`❌ 生成失败: ${error.message}`, 'error');
            return null;
        }
    }

    /**
     * 🔥 图片生成任务管理器
     */
    imageTasks = new Map();  // task_id -> task info
    imageTaskPolling = null; // 轮询计时器
    
    /**
     * 初始化图片任务管理器
     */
    initImageTaskManager() {
        // 开始轮询任务状态
        this.startImageTaskPolling();
    }
    
    /**
     * 开始轮询任务状态
     */
    startImageTaskPolling() {
        if (this.imageTaskPolling) return;
        
        this.imageTaskPolling = setInterval(() => {
            this.pollImageTasks();
        }, 2000); // 每2秒轮询一次
    }
    
    /**
     * 停止轮询
     */
    stopImageTaskPolling() {
        if (this.imageTaskPolling) {
            clearInterval(this.imageTaskPolling);
            this.imageTaskPolling = null;
        }
    }
    
    /**
     * 轮询所有进行中的任务
     */
    async pollImageTasks() {
        const pendingTasks = Array.from(this.imageTasks.values())
            .filter(t => t.status === 'pending' || t.status === 'running');
        
        if (pendingTasks.length === 0) return;
        
        for (const task of pendingTasks) {
            try {
                const response = await fetch(
                    `/api/short-drama/projects/${this.currentProject.id}/visual-assets/tasks/${task.task_id}`
                );
                const result = await response.json();
                
                if (result.success) {
                    const serverTask = result.task;
                    const oldStatus = task.status;
                    
                    // 更新本地状态
                    task.status = serverTask.status;
                    task.progress = serverTask.progress || 0;
                    task.result = serverTask.result;
                    task.error = serverTask.error;
                    
                    // 状态变化通知
                    if (serverTask.status !== oldStatus) {
                        if (serverTask.status === 'completed') {
                            this.handleImageTaskCompleted(task);
                        } else if (serverTask.status === 'failed') {
                            this.handleImageTaskFailed(task);
                        }
                    }
                    
                    // 刷新任务列表显示（进度更新也触发刷新）
                    this.updateImageTaskList();
                }
            } catch (error) {
                console.error(`轮询任务 ${task.task_id} 失败:`, error);
            }
        }
    }
    
    /**
     * 处理任务完成
     */
    handleImageTaskCompleted(task) {
        const result = task.result;
        if (!result?.success) return;
        
        const { category, name, data } = task;
        const asset = this.currentProject?.visualAssets?.[category]?.[name];
        if (!asset) return;
        
        // 更新资产数据
        const imageUrl = result.data?.referenceUrl;
        const localPath = result.data?.localPath;
        if (imageUrl) {
            asset.referenceUrl = imageUrl;
            asset.localPath = localPath;
            asset.updatedAt = new Date().toISOString();
            
            // 更新 characterPortraits
            if (category === 'characters') {
                if (!this.characterPortraits.has(name)) {
                    this.characterPortraits.set(name, {});
                }
                this.characterPortraits.get(name).mainPortrait = {
                    url: imageUrl,
                    path: localPath,
                    generatedAt: new Date().toISOString()
                };
                this.refreshPortraitCanvas();
            }
            
            // 刷新显示
            this.selectVisualAsset(category.slice(0, -1), asset, imageUrl);
            this.loadVisualAssetsGrid(category);
            
            this.showToast(`✅ ${name} 图片生成完成`, 'success');
        }
    }
    
    /**
     * 处理任务失败
     */
    handleImageTaskFailed(task) {
        this.showToast(`❌ ${task.name} 生成失败: ${task.error || '未知错误'}`, 'error');
    }
    
    /**
     * 为视觉资产生成图片 - 异步任务
     */
    async generateAssetImage(name, type) {
        const typeMap = {
            'character': 'characters',
            'scene': 'scenes', 
            'prop': 'props'
        };
        const category = typeMap[type];
        const asset = this.currentProject?.visualAssets?.[category]?.[name];
        
        if (!asset) {
            this.showToast('资产不存在', 'error');
            return;
        }
        
        // 检查是否已有进行中的任务
        const existingTask = Array.from(this.imageTasks.values())
            .find(t => t.name === name && t.category === category && 
                 (t.status === 'pending' || t.status === 'running'));
        if (existingTask) {
            this.showToast(`⚠️ ${name} 正在生成中，请耐心等待`, 'warning');
            return;
        }
        
        // 构建生成提示词
        let prompt = '';
        const description = asset.description || '';
        
        if (type === 'character') {
            prompt = JSON.stringify({
                type: 'character',
                id: name,
                name: name,
                raw_description: description || '',
                raw_clothing: asset.clothing || '',
                raw_expression: asset.expression || ''
            });
        } else if (type === 'scene') {
            const lighting = asset.lighting || '';
            const colorTone = asset.colorTone || '';
            let sceneDesc = description;
            if (sceneDesc && /[\u4e00-\u9fa5]/.test(sceneDesc)) {
                sceneDesc = 'detailed environment';
            }
            prompt = `Cinematic scene "${name}"`;
            prompt += `, SCENE_TAG: LOCATION_${name.replace(/\s+/g, '_').toUpperCase()}`;
            if (sceneDesc) prompt += `, ${sceneDesc}`;
            if (lighting) prompt += `, ${lighting} lighting`;
            if (colorTone) prompt += `, ${colorTone} color tone`;
            prompt += `, high quality, detailed environment, cinematic composition, photorealistic, 8k, sharp focus`;
        } else if (type === 'prop') {
            const propCategory = asset.category || '';
            let propDesc = description;
            if (propDesc && /[\u4e00-\u9fa5]/.test(propDesc)) {
                propDesc = 'detailed object';
            }
            prompt = `Detailed product shot of "${name}"`;
            prompt += `, PROP_TAG: ITEM_${name.replace(/\s+/g, '_').toUpperCase()}`;
            if (propDesc) prompt += `, ${propDesc}`;
            if (propCategory) prompt += `, ${propCategory}`;
            prompt += `, high quality, detailed, product photography style, clean background, photorealistic, 8k`;
        }
        
        // 获取视频设置
        const settings = this.currentProject?.settings || {};
        let aspectRatio, imageSize;
        if (type === 'character') {
            aspectRatio = '16:9';
            imageSize = '4K';
        } else {
            aspectRatio = settings.aspect_ratio || '9:16';
            const quality = settings.quality || '2K';
            imageSize = quality === '4K' ? '4K' : (quality === '2K' ? '2K' : '1K');
        }
        
        // 构建请求体
        const requestBody = {
            category: category,
            name: name,
            prompt: prompt,
            aspect_ratio: aspectRatio,
            image_size: imageSize
        };
        if (type === 'character') {
            requestBody.description = asset.description || '';
            requestBody.clothing = asset.clothing || '';
            requestBody.expression = asset.expression || '';
        }
        
        try {
            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}/visual-assets/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 添加到本地任务列表
                const task = {
                    task_id: result.task_id,
                    project_id: this.currentProject.id,
                    category: category,
                    name: name,
                    type: type,
                    status: result.status,
                    created_at: new Date().toISOString(),
                    result: null,
                    error: null
                };
                this.imageTasks.set(result.task_id, task);
                
                this.showToast(`🚀 ${name} 生成任务已提交（队列）`, 'success');
                
                // 显示任务列表
                this.showImageTaskList();
                
                // 立即轮询一次
                this.pollImageTasks();
            } else {
                this.showToast(`❌ ${result.error || '提交失败'}`, 'error');
            }
        } catch (error) {
            console.error('提交生成任务失败:', error);
            this.showToast(`❌ 提交失败: ${error.message}`, 'error');
        }
    }
    
    /**
     * 显示图片生成任务列表
     */
    showImageTaskList() {
        // 检查是否已有面板
        let panel = document.getElementById('image-task-panel');
        if (panel) {
            this.updateImageTaskList();
            return;
        }
        
        // 创建面板
        panel = document.createElement('div');
        panel.id = 'image-task-panel';
        panel.className = 'image-task-panel';
        panel.innerHTML = `
            <div class="task-panel-header">
                <h4>🎨 图片生成队列</h4>
                <button class="btn-close" onclick="shortDramaStudio.hideImageTaskList()">✕</button>
            </div>
            <div class="task-panel-body" id="task-panel-body">
                <div class="task-empty">暂无生成任务</div>
            </div>
        `;
        
        document.body.appendChild(panel);
        this.updateImageTaskList();
        
        // 添加样式
        if (!document.getElementById('image-task-panel-styles')) {
            const styles = document.createElement('style');
            styles.id = 'image-task-panel-styles';
            styles.textContent = `
                .image-task-panel {
                    position: fixed;
                    right: 20px;
                    top: 80px;
                    width: 320px;
                    background: rgba(15, 23, 42, 0.95);
                    border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                    z-index: 9999;
                    backdrop-filter: blur(10px);
                }
                .task-panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    border-bottom: 1px solid rgba(99, 102, 241, 0.2);
                }
                .task-panel-header h4 {
                    margin: 0;
                    color: #fff;
                    font-size: 14px;
                }
                .task-panel-body {
                    max-height: 400px;
                    overflow-y: auto;
                    padding: 8px;
                }
                .task-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 12px;
                    margin-bottom: 6px;
                    background: rgba(30, 41, 59, 0.8);
                    border-radius: 8px;
                    border-left: 3px solid #6366f1;
                    transition: all 0.3s;
                }
                .task-item.pending { border-left-color: #f59e0b; }
                .task-item.running { border-left-color: #3b82f6; }
                .task-item.completed { border-left-color: #10b981; }
                .task-item.failed { border-left-color: #ef4444; }
                .task-item-icon {
                    font-size: 20px;
                }
                .task-item-info {
                    flex: 1;
                    min-width: 0;
                }
                .task-item-name {
                    font-size: 13px;
                    color: #fff;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .task-item-status {
                    font-size: 11px;
                    color: rgba(255,255,255,0.6);
                    margin-top: 2px;
                }
                .task-item-progress {
                    width: 60px;
                    height: 4px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 2px;
                    overflow: hidden;
                }
                .task-item-progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    border-radius: 2px;
                    transition: width 0.3s ease;
                }
                .task-item-running .task-item-progress-bar {
                    animation: progress-pulse 1.5s ease-in-out infinite;
                }
                @keyframes progress-pulse {
                    0%, 100% { opacity: 0.6; }
                    50% { opacity: 1; }
                }
                .task-empty {
                    text-align: center;
                    padding: 30px;
                    color: rgba(255,255,255,0.5);
                    font-size: 13px;
                }
            `;
            document.head.appendChild(styles);
        }
    }
    
    /**
     * 隐藏任务列表
     */
    hideImageTaskList() {
        const panel = document.getElementById('image-task-panel');
        if (panel) {
            panel.remove();
        }
    }
    
    /**
     * 更新任务列表显示
     */
    updateImageTaskList() {
        const body = document.getElementById('task-panel-body');
        if (!body) return;
        
        const tasks = Array.from(this.imageTasks.values())
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        if (tasks.length === 0) {
            body.innerHTML = '<div class="task-empty">暂无生成任务</div>';
            return;
        }
        
        const statusIcons = {
            'pending': '⏳',
            'running': '🎨',
            'completed': '✅',
            'failed': '❌'
        };
        const statusText = {
            'pending': '等待中',
            'running': '生成中...',
            'completed': '完成',
            'failed': '失败'
        };
        
        // 只显示最近的10个任务
        const recentTasks = tasks.slice(0, 10);
        
        body.innerHTML = recentTasks.map(task => {
            const progress = task.progress || 0;
            const showProgress = task.status === 'running' || task.status === 'pending';
            const runningClass = task.status === 'running' ? 'task-item-running' : '';
            return `
            <div class="task-item ${task.status} ${runningClass}">
                <div class="task-item-icon">${statusIcons[task.status]}</div>
                <div class="task-item-info">
                    <div class="task-item-name">${task.name}</div>
                    <div class="task-item-status">${statusText[task.status]}${showProgress && progress > 0 ? ` ${progress}%` : ''}</div>
                </div>
                ${showProgress ? `
                <div class="task-item-progress">
                    <div class="task-item-progress-bar" style="width: ${progress}%"></div>
                </div>
                ` : ''}
            </div>
        `}).join('');
    }

    /**
     * 从选中集数中提取角色
     */

    /**
     * 生成角色剧照
     */
    /**
     * 生成角色剧照
     */

    /**
     * 根据角色信息生成AI剧照提示词（使用角色设计文件中的详细特征）
     */

    /**
     * 获取剧集目录名称
     */
    getEpisodeDirectoryName() {
        // 🔥 如果是创意导入项目，使用固定的目录名
        if (this.isCreativeProject) {
            // 创意导入项目固定使用 "1集_创意导入" 作为目录名
            return '1集_创意导入';
        }

        if (!this.selectedMajorEvent) return '默认';

        const majorIndex = this.events.findIndex(e => e.id === this.selectedMajorEvent.id);
        // 使用原始标题，不要替换特殊字符（因为目录名保留了原始字符）
        const eventTitle = this.selectedMajorEvent.title || this.selectedMajorEvent.name;

        return `${majorIndex + 1}集_${eventTitle}`;
    }

    /**
     * 查看剧照
     */

    /**
     * 显示剧照模态框
     */
    showPortraitModal(characterName, portraitInfo) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: flex;
            justify-content: center; align-items: center; z-index: 10000;
        `;

        const portraits = portraitInfo.portraits || [];
        const mainPortrait = portraitInfo.mainPortrait;

        // 生成所有剧照的HTML
        const portraitsHtml = portraits.length > 1 ? `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; margin-bottom: 1rem;">
                ${portraits.map((p, idx) => `
                    <div class="portrait-thumb ${p.url === mainPortrait.url ? 'active' : ''}"
                         onclick="shortDramaStudio.showMainPortrait('${p.url}')"
                         style="cursor: pointer; border: 2px solid ${p.url === mainPortrait.url ? 'var(--primary)' : 'var(--border)'}; border-radius: 8px; overflow: hidden; position: relative;">
                        <img src="${p.url}" alt="造型${p.number > 0 ? '_' + p.number : ''}"
                             style="width: 100%; height: 100px; object-fit: cover; display: block;">
                        ${p.isPriority ? `<div style="position: absolute; top: 2px; right: 2px; background: linear-gradient(135deg, #ff6b6b, #feca57); color: white; font-size: 9px; padding: 1px 4px; border-radius: 6px; font-weight: bold;">三视图</div>` : ''}
                    </div>
                `).join('')}
            </div>
        ` : '';

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-secondary); border-radius: 16px;
                max-width: 700px; width: 90%; padding: 2rem;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
                max-height: 90vh; overflow-y: auto;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="margin: 0;">${characterName}${mainPortrait.isPriority ? ' <span style="background: linear-gradient(135deg, #ff6b6b, #feca57); color: white; font-size: 12px; padding: 2px 8px; border-radius: 12px; vertical-align: middle;">三视图</span>' : ''}</h2>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; color: var(--text-secondary); font-size: 1.5rem; cursor: pointer;">✕</button>
                </div>
                ${portraitsHtml}
                <div style="text-align: center; margin-bottom: 1rem;">
                    <img id="mainPortraitImage" src="${mainPortrait.url}" alt="${characterName}" style="max-width: 100%; max-height: 50vh; border-radius: 12px;">
                </div>
                ${portraits.length > 1 ? `<p style="text-align: center; color: var(--text-secondary); font-size: 0.85rem;">共 ${portraits.length} 个造型，点击缩略图切换</p>` : ''}
                <div style="display: flex; gap: 1rem; justify-content: center; margin-top: 1rem;">
                    <button class="btn btn-primary" onclick="shortDramaStudio.generatePortrait('${characterName}')">🎨 生成新造型</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">关闭</button>
                </div>
            </div>
        `;

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                // 清理样式标签
                const styleEl = document.getElementById('dubbingModalStyles');
                if (styleEl) styleEl.remove();
            }
        });

        document.body.appendChild(modal);
    }

    /**
     * 切换主图显示
     */
    showMainPortrait(url) {
        const img = document.getElementById('mainPortraitImage');
        if (img) {
            img.src = url;
        }

        // 更新选中状态
        document.querySelectorAll('.portrait-thumb').forEach(thumb => {
            thumb.style.borderColor = thumb.querySelector('img').src === url ? 'var(--primary)' : 'var(--border)';
        });
    }

    /**
     * 显示图片预览模态框
     */
    showImagePreview(imageUrl) {
        const modal = document.createElement('div');
        modal.className = 'image-preview-modal';

        modal.innerHTML = `
            <button class="image-preview-close" onclick="this.parentElement.remove()">✕</button>
            <img src="${imageUrl}" alt="预览图">
        `;

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        // ESC键关闭
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                modal.remove();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);

        document.body.appendChild(modal);
    }

    /**
     * 获取项目视频生成设置
     */
    getVideoSettings() {
        const settings = this.currentProject?.settings || {};
        const aspectRatio = settings.aspect_ratio || '9:16';
        const quality = settings.quality || '4K';

        // 根据比例和质量计算实际分辨率
        let size = '1920x1080'; // 默认 1080p
        if (aspectRatio === '16:9') {
            // 横屏: 宽x高
            if (quality === '4K') size = '3840x2160';
            else if (quality === '2K') size = '2560x1440';
            else size = '1920x1080';
        } else {
            // 竖屏: 宽x高
            if (quality === '4K') size = '2160x3840';
            else if (quality === '2K') size = '1440x2560';
            else size = '1080x1920';
        }

        // 使用项目设置的模型，默认使用参考图模式
        let model = settings.model || 'veo_3_1-fast-components';

        // 🔥 首尾帧模式设置（默认开启）
        const useFirstLastFrame = settings.use_first_last_frame !== false;  // 默认 true

        return {
            orientation: aspectRatio === '16:9' ? 'landscape' : 'portrait',
            size: size,
            model: model,
            use_first_last_frame: useFirstLastFrame
        };
    }

    /**
     * 旧格式: {shot_number, shot_type, screen_action, dialogue, veo_prompt}
     * 对话格式: {scene_number, visual, dialogues: [{speaker, lines, tone}, ...]}
     */

    /**
     * 合并连续的对话场景
     * 将连续的对话镜头合并为一个场景，包含多个对话
     */
    groupDialogueScenes(shots) {
        if (!shots || shots.length === 0) return shots;

        const grouped = [];
        let currentDialogueGroup = null;
        let currentGroupIndex = 0;

        for (let i = 0; i < shots.length; i++) {
            const shot = shots[i];
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            const { speaker } = this.parseDialogue(dialogue);

            // 检查是否有台词（不是"无"或"未知"或空）
            const hasDialogue = speaker && speaker !== '无' && speaker !== '未知' && speaker !== '旁白' && speaker !== '主角内心混响';

            // 检查是否应该开始新的对话组
            if (hasDialogue) {
                if (!currentDialogueGroup) {
                    // 开始新的对话组
                    currentDialogueGroup = {
                        shot_number: shot.shot_number,
                        shot_type: shot.shot_type,
                        screen_action: shot.screen_action,
                        veo_prompt: shot.veo_prompt,
                        duration: shot.duration,
                        plot_content: shot.plot_content,
                        episode_title: shot.episode_title,
                        event_name: shot.event_name,
                        episode_index: shot.episode_index,
                        episode_order: shot.episode_order,
                        dialogues: [],
                        is_dialogue_scene: true,
                        shared_scene_id: `${shot.shot_number}_${shot.episode_title}`.replace(/\s+/g, '_')
                    };
                    grouped.push(currentDialogueGroup);
                }

                // 添加对话到当前组
                currentDialogueGroup.dialogues.push({
                    speaker: speaker,
                    lines: dialogue.lines || '',
                    tone: dialogue.tone || '',
                    audio_note: dialogue.audio_note || shot.audio || '',
                    _dialogue_data: dialogue,
                    // 用于子镜头索引
                    sub_shot_index: grouped.length - 1,
                    dialogue_index: currentDialogueGroup.dialogues.length + 1,
                    dialogue_count: 0 // 稍后更新总数
                });

                // 累计时长
                currentDialogueGroup.duration = (currentDialogueGroup.duration || 0) + (shot.duration || 0);
            } else {
                // 非对话镜头，结束当前对话组
                currentDialogueGroup = null;
                // 更新对话组中的对话总数
                if (grouped.length > 0) {
                    const lastGroup = grouped[grouped.length - 1];
                    if (lastGroup.is_dialogue_scene && lastGroup.dialogues) {
                        lastGroup.dialogues.forEach(d => d.dialogue_count = lastGroup.dialogues.length);
                    }
                }
                // 直接添加非对话镜头
                grouped.push(shot);
            }
        }

        // 更新最后一个对话组的对话总数
        if (grouped.length > 0) {
            const lastGroup = grouped[grouped.length - 1];
            if (lastGroup.is_dialogue_scene && lastGroup.dialogues) {
                lastGroup.dialogues.forEach(d => d.dialogue_count = lastGroup.dialogues.length);
            }
        }

        // 如果没有对话组，返回原数组
        if (grouped.every(s => !s.is_dialogue_scene)) {
            return shots;
        }

        return grouped;
    }

    /**
     * 渲染分镜头（从本地文件加载）
     */

    /**
     * 渲染分镜头
     */

    /**
     * 保存优化格式的分镜头数据到文件系统（数据流A持久化）
     */

    /**
     * 从文件系统加载优化格式的分镜头数据（数据流A）
     */

    /**
     * 统一数据格式：将优化格式的 shots 转换为视频生成步骤需要的格式
     */

    /**
     * 🔥 统一加载镜头数据（视频和配音步骤复用）
     */

    /**
     * 加载视频步骤
     */
    async loadVideoStep() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>加载分镜头数据...</p></div>';

        // 调用统一的数据加载方法
        const allShots = await this.loadShotsData();

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>还没有分镜头数据</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在"分镜生成"步骤生成分镜头
                    </p>
                    <button class="btn btn-primary" onclick="shortDramaStudio.goToStep('storyboard')" style="margin-top: 1rem;">
                        前往分镜生成
                    </button>
                </div>
            `;
            return;
        }

        console.log('✅ [视频步骤] 最终加载的镜头数:', this.shots.length);

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>检查视频文件...</p></div>';

        // 检查已存在的视频
        await this.checkExistingVideos();

        // 渲染视频卡片
        this.renderVideoCards();
    }

    /**
     * 检查已存在的视频文件
     */
    async checkExistingVideos() {
        const episodeDirectoryName = this.getEpisodeDirectoryName();

        console.log('🎬 [视频检查] 开始检查视频...');
        console.log('🎬 [视频检查] Episode:', episodeDirectoryName);
        console.log('🎬 [视频检查] Shots数量:', this.shots.length);

        try {
            // 使用新的API列出视频文件
            const response = await fetch(`/api/short-drama/list-videos?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            console.log('🎬 [视频检查] API返回的视频:', data.videos);

            // 🔥 详细打印每个视频的信息
            if (data.videos && data.videos.length > 0) {
                console.log('🎬 [视频检查] 视频文件详情:');
                data.videos.forEach((video, idx) => {
                    console.log(`   [${idx}] ${video.filename}`);
                    console.log(`       scene_number=${video.scene_number}, episode_name="${video.episode_name}", shot_type="${video.shot_type}", is_dialogue=${video.is_dialogue_scene}`);
                });
            }

            if (data.videos && data.videos.length > 0) {
                // 🔥 先重置所有镜头的videoExists标志
                for (let i = 0; i < this.shots.length; i++) {
                    this.shots[i].videoExists = false;
                    this.shots[i].videoPath = null;
                    this.shots[i].videoUrl = null;
                }

                // 🔥 按episode_title分组统计
                const episodeStats = {};
                for (const shot of this.shots) {
                    const ep = shot.episode_title || 'unknown';
                    if (!episodeStats[ep]) episodeStats[ep] = 0;
                    episodeStats[ep]++;
                }
                console.log('📊 Shots按episode分组:', episodeStats);

                // 为每个镜头匹配视频
                let matchedCount = 0;
                for (let i = 0; i < this.shots.length; i++) {
                    const shot = this.shots[i];
                    const episodeTitle = shot.episode_title || '';
                    const shotNumber = shot.shot_number || (i + 1);
                    const sceneNumber = shot.scene_number || 1;
                    const shotType = shot.shot_type || '';

                    console.log(`🔍 镜头 #${i + 1}: episode="${episodeTitle}", scene_number=${sceneNumber}, shot_number=${shotNumber}, shot_type="${shotType}"`);

                    // 🔥 在所有视频中查找匹配的视频
                    let matchedVideo = null;
                    for (const video of data.videos) {
                        // 新格式视频有 episode_name 和 scene_number 字段
                        const videoEpisodeName = video.episode_name || video.storyboard_key || '';
                        const videoSceneNum = video.scene_number || 0;
                        const videoShotType = video.shot_type || '';
                        const videoIsDialogue = video.is_dialogue_scene;

                        console.log(`   🔍 检查视频: scene_number=${videoSceneNum}, event="${videoEpisodeName}", shot_type="${videoShotType}", is_dialogue=${videoIsDialogue}`);

                        // 🔥 优先使用 scene_number 匹配（最可靠）
                        if (videoSceneNum === sceneNumber) {
                            // 再检查事件名是否匹配（包含关系即可）
                            const eventMatches = videoEpisodeName.includes(episodeTitle) ||
                                                 episodeTitle.includes(videoEpisodeName) ||
                                                 videoEpisodeName === episodeTitle;
                            if (eventMatches) {
                                matchedVideo = video;
                                console.log(`   ✅ 匹配成功! scene_number=${sceneNumber}, event="${videoEpisodeName}"`);
                                break;
                            } else {
                                console.log(`   ⚠️ scene_number匹配但事件名不匹配: video event="${videoEpisodeName}", shot event="${episodeTitle}"`);
                            }
                        }
                    }

                    if (matchedVideo) {
                        shot.videoExists = true;
                        shot.videoPath = matchedVideo.path;
                        shot.videoUrl = matchedVideo.url;
                        matchedCount++;
                        console.log(`✅ 镜头 #${i + 1} 视频已存在: ${matchedVideo.filename}`);
                    } else {
                        console.log(`⭕ 镜头 #${i + 1} 无视频`);
                    }
                }
                console.log(`🎬 匹配完成: ${matchedCount}/${this.shots.length} 个镜头有视频`);
            } else {
                console.log('🎬 没有找到已存在的视频');
            }
        } catch (e) {
            console.error('检查视频失败:', e);
        }
    }

    /**
     * 检查已存在的音频文件
     */
    async checkExistingAudio() {
        const episodeDirectoryName = this.getEpisodeDirectoryName();

        console.log('🎙️ [音频检查] 开始检查音频...');
        console.log('🎙️ [音频检查] Episode:', episodeDirectoryName);

        try {
            // 调用API列出音频文件
            const response = await fetch(`/api/tts/list-audio?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            console.log('🎙️ [音频检查] API返回的音频:', data.audios);
            console.log('🎙️ [音频检查] 音频文件详情:');
            data.audios.forEach((audio, idx) => {
                console.log(`   [${idx}] ${audio.filename}`);
                console.log(`       scene_number=${audio.scene_number}, event_name="${audio.event_name}", speaker="${audio.speaker}"`);
            });

            // 打印所有镜头信息用于对比
            console.log('🎙️ [音频检查] 镜头信息:');
            for (let i = 0; i < this.shots.length; i++) {
                const shot = this.shots[i];
                const episodeTitle = shot.episode_title || '';
                const shotNumber = shot.shot_number || (i + 1);
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                const { speaker } = this.parseDialogue(dialogue);
                const isDialogueScene = shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues);
                console.log(`   [${i}] shot_number=${shotNumber}, episode="${episodeTitle}", speaker="${speaker}", isDialogueScene=${isDialogueScene}`);
                if (isDialogueScene) {
                    shot.dialogues.forEach((dlg, dlgIdx) => {
                        const { speaker: dlgSpeaker } = this.parseDialogue(dlg);
                        console.log(`       对话${dlgIdx + 1}: speaker="${dlgSpeaker}"`);
                    });
                }
            }

            // 先重置所有镜头的音频状态
            for (let i = 0; i < this.shots.length; i++) {
                this.shots[i].audioUrl = null;
                this.shots[i].audio_path = null;
                // 重置子镜头音频状态
                if (this.shots[i]._sub_audios) {
                    this.shots[i]._sub_audios = new Array(this.shots[i]._sub_audios.length).fill(null);
                }
            }

            if (data.audios && data.audios.length > 0) {
                // 为每个镜头匹配音频（使用和视频一样的匹配逻辑）
                let matchedCount = 0;
                console.log('🎙️ [音频检查] 开始匹配镜头...');
                for (let i = 0; i < this.shots.length; i++) {
                    const shot = this.shots[i];
                    const episodeTitle = shot.episode_title || '';
                    const sceneNumber = shot.scene_number || 1;

                    console.log(`🎙️ [镜头 #${i + 1}] scene_number=${sceneNumber}, episode="${episodeTitle}"`);

                    // 检查是否是对话场景
                    if (shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues)) {
                        // 对话场景：遍历每个子对话
                        for (let dlgIdx = 0; dlgIdx < shot.dialogues.length; dlgIdx++) {
                            const dlg = shot.dialogues[dlgIdx];
                            const { speaker } = this.parseDialogue(dlg);
                            const dialogueIndex = dlgIdx + 1;

                            console.log(`   🔍 对话${dialogueIndex}: speaker="${speaker}"`);

                            // 🔥 优先使用 scene_number 匹配（最可靠）
                            let matchedAudio = null;
                            for (const audio of data.audios) {
                                const audioSceneNum = audio.scene_number || 0;
                                const audioEventName = audio.event_name || '';
                                const audioSpeaker = audio.speaker || '';
                                const audioDialogueIdx = audio.dialogue_idx || 1;

                                // 优先使用 scene_number 匹配
                                if (audioSceneNum === sceneNumber) {
                                    // 再检查事件名和说话人是否匹配（使用包含关系）
                                    const eventMatches = audioEventName.includes(episodeTitle) ||
                                                         episodeTitle.includes(audioEventName) ||
                                                         audioEventName === episodeTitle;
                                    const speakerMatches = audioSpeaker === speaker || audioSpeaker.includes(speaker) || speaker.includes(audioSpeaker);

                                    if (eventMatches && speakerMatches && audioDialogueIdx === dialogueIndex) {
                                        matchedAudio = audio;
                                        console.log(`      ✅ ${audio.filename} (scene_number=${audioSceneNum})`);
                                        break;
                                    }
                                }
                            }

                            if (matchedAudio) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                const timestamp = Date.now();
                                shot._sub_audios[dlgIdx].audioUrl = matchedAudio.url + (matchedAudio.url.includes('?') ? '&' : '?') + 't=' + timestamp;
                                shot._sub_audios[dlgIdx].audio_path = matchedAudio.path;
                                matchedCount++;
                            } else {
                                console.log(`      ❌ 无匹配`);
                            }
                        }
                    } else {
                        // 普通镜头：单个音频
                        const dialogue = shot._dialogue_data || shot.dialogue || {};
                        const { speaker } = this.parseDialogue(dialogue);

                        console.log(`   🔍 speaker="${speaker}"`);

                        // 🔥 优先使用 scene_number 匹配（最可靠）
                        let matchedAudio = null;
                        for (const audio of data.audios) {
                            const audioSceneNum = audio.scene_number || 0;
                            const audioEventName = audio.event_name || '';
                            const audioSpeaker = audio.speaker || '';

                            // 优先使用 scene_number 匹配
                            if (audioSceneNum === sceneNumber) {
                                // 再检查事件名和说话人是否匹配（使用包含关系）
                                const eventMatches = audioEventName.includes(episodeTitle) ||
                                                     episodeTitle.includes(audioEventName) ||
                                                     audioEventName === episodeTitle;
                                const speakerMatches = audioSpeaker === speaker || audioSpeaker.includes(speaker) || speaker.includes(audioSpeaker);

                                if (eventMatches && speakerMatches) {
                                    matchedAudio = audio;
                                    console.log(`   ✅ ${audio.filename} (scene_number=${audioSceneNum})`);
                                    break;
                                }
                            }
                        }

                        if (matchedAudio) {
                            const timestamp = Date.now();
                            shot.audioUrl = matchedAudio.url + (matchedAudio.url.includes('?') ? '&' : '?') + 't=' + timestamp;
                            shot.audio_path = matchedAudio.path;
                            matchedCount++;
                        } else {
                            console.log(`   ❌ 无匹配`);
                        }
                    }
                }
                console.log(`🎙️ [音频检查] 匹配完成: ${matchedCount} 个音频文件已匹配`);
            } else {
                console.log('🎙️ [音频检查] 没有找到已存在的音频');
            }
        } catch (e) {
            console.error('检查音频失败:', e);
        }
    }

    /**
     * 渲染视频卡片（使用剪映风格的列表）
     */
    renderVideoCards() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        console.log(`🎬 渲染视频卡片, shots数量: ${this.shots?.length || 0}`);
        console.log(`🎬 this.shots内容:`, this.shots);

        if (!this.shots || this.shots.length === 0) {
            console.error('❌ this.shots为空或未定义');
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>没有分镜头数据</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在"分镜头"步骤生成分镜头
                    </p>
                </div>
            `;
            return;
        }

        const completedCount = this.shots.filter(s => s.videoExists).length;
        const totalCount = this.shots.length;

        // 按事件分组
        const eventGroups = this.groupShotsByEvent(this.shots);

        console.log(`📊 分组数量: ${eventGroups.length}`);
        eventGroups.forEach((g, i) => console.log(`  组${i}: ${g.eventName}, ${g.shots.length}个镜头`));

        let rowsHtml = '';
        eventGroups.forEach((group, groupIdx) => {
            // 添加事件分隔线（第一个事件之前不添加）
            if (groupIdx > 0) {
                rowsHtml += `
                    <div class="event-separator">
                        <div class="event-separator-line"></div>
                        <div class="event-separator-label">${group.eventName}</div>
                        <div class="event-separator-line"></div>
                    </div>
                `;
            } else if (group.eventName) {
                // 第一个事件也显示标签，但没有上面的分隔线
                rowsHtml += `
                    <div class="event-separator first">
                        <div class="event-separator-label">${group.eventName}</div>
                    </div>
                `;
            }

            // 渲染该事件的所有镜头
            group.shots.forEach(shot => {
                const idx = this.shots.indexOf(shot);
                rowsHtml += this.renderVideoTaskRow(shot, idx);
            });
        });

        container.innerHTML = `
            <div class="video-workspace">
                <div class="video-toolbar">
                    <div class="video-stats">
                        <span class="stat-item">共 ${totalCount} 个镜头</span>
                        <span class="stat-item completed">已完成 ${completedCount}</span>
                        <span class="stat-item pending">待生成 ${totalCount - completedCount}</span>
                    </div>
                    <div class="toolbar-actions">
                        <button class="toolbar-btn" onclick="shortDramaStudio.refreshVideos()">
                            <span class="btn-icon">🔄</span>
                            <span class="btn-text">刷新</span>
                        </button>
                        <button class="toolbar-btn" onclick="shortDramaStudio.runQualityCheck()">
                            <span class="btn-icon">📋</span>
                            <span class="btn-text">剧本质量检查</span>
                        </button>
                        <button class="toolbar-btn primary" onclick="shortDramaStudio.batchGenerateFirstFive()">
                            <span class="btn-icon">🚀</span>
                            <span class="btn-text">批量生成（前5个）</span>
                        </button>
                    </div>
                </div>
                <div class="video-task-list">
                    ${rowsHtml}
                </div>
            </div>
        `;
    }

    /**
     * 按事件分组镜头
     */

    /**
     * 渲染单个视频任务行（剪映风格）
     */
    renderVideoTaskRow(shot, idx) {
        const isCompleted = shot.videoExists;
        const isGenerating = shot.generating;
        const hasError = shot.hasError;

        const statusClass = isCompleted ? 'done' : isGenerating ? 'processing' : hasError ? 'error' : 'pending';
        const statusText = isCompleted ? '已完成' : isGenerating ? '生成中...' : hasError ? '失败' : '待生成';

        // 🔥 获取错误信息
        const errorMessage = shot.errorMessage || '';
        const hasErrorMessage = hasError && errorMessage;

        // 参考图缩略图
        const referenceImages = shot.reference_images || [];
        const hasRefs = referenceImages.length > 0;

        // 🔥 获取台词信息（支持dialogues数组和dialogue对象）
        let hasDialogue = false;
        let dialogueDisplayHtml = '';

        // 检查是否是对话场景（dialogues数组）
        if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
            hasDialogue = true;
            const firstLines = shot.dialogues.slice(0, 2).map(d =>
                `${d.speaker}: ${d.lines?.substring(0, 20) || ''}${d.lines?.length > 20 ? '...' : ''}`
            ).join('\n');
            const count = shot.dialogues.length;
            dialogueDisplayHtml = `
                <div class="task-dialogue">
                    <span class="prompt-label">💬 对话:</span>
                    <span class="dialogue-text">${firstLines}${count > 2 ? `\n... 等 ${count} 句` : ''}</span>
                </div>
            `;
        } else {
            // 普通单个对话
            const dialogueData = shot._dialogue_data || shot.dialogue;
            if (dialogueData && dialogueData.speaker && dialogueData.speaker !== '无') {
                hasDialogue = true;
                dialogueDisplayHtml = `
                    <div class="task-dialogue">
                        <span class="prompt-label">💬 台词:</span>
                        <span class="dialogue-text">${dialogueData.speaker}: ${dialogueData.lines?.substring(0, 50) || ''}${dialogueData.lines?.length > 50 ? '...' : ''}</span>
                        ${dialogueData.tone ? `<span class="dialogue-tone">(${dialogueData.tone})</span>` : ''}
                    </div>
                `;
            }
        }

        // 生成参考图缩略图HTML（仅在有参考图时）
        const refsThumbnailsHtml = hasRefs ? referenceImages.map(img => `
            <div class="ref-thumb" onclick="event.stopPropagation(); shortDramaStudio.showImagePreview('${img}')">
                <img src="${img}" alt="参考图">
            </div>
        `).join('') : '';

        // 视频预览（如果已完成）
        const videoPreviewHtml = isCompleted && shot.videoUrl
            ? `<div class="task-video-preview" onclick="shortDramaStudio.previewVideo(${idx})">
                <video src="${shot.videoUrl}" muted preload="metadata"></video>
                <span class="play-icon">▶</span>
               </div>`
            : `<div class="task-video-placeholder">${isGenerating ? '<span class="spinner"></span>' : '⏳'}</div>`;

        // 🔥 检查是否支持多模式（数据流A）
        const hasMultipleModes = shot.veo_prompt_standard && shot.veo_prompt_reference && shot.veo_prompt_frames;
        const currentMode = shot.preferred_mode || 'standard';

        // 🔥 根据当前模式获取提示词
        const currentPrompt = this.getCurrentVeoPrompt(shot);
        const currentVisualDesc = this.getCurrentVisualDescription(shot);

        // 🔥 模式选择器HTML（仅在支持多模式时显示）
        const modeSelectorHtml = hasMultipleModes ? `
            <div class="task-mode-selector" style="margin-bottom: 0.5rem;">
                <span class="prompt-label">🎨 模式:</span>
                <select id="mode-select-${idx}" onchange="shortDramaStudio.updateShotMode(${idx})"
                        style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 0.25rem; background: rgba(0,0,0,0.3); color: var(--text-primary); border: 1px solid rgba(255,255,255,0.1);">
                    <option value="standard" ${currentMode === 'standard' ? 'selected' : ''}>标准模式</option>
                    <option value="reference" ${currentMode === 'reference' ? 'selected' : ''}>参考图模式</option>
                    <option value="frames" ${currentMode === 'frames' ? 'selected' : ''}>首尾帧模式</option>
                </select>
            </div>
        ` : '';

        return `
            <div class="task-row ${statusClass}" id="taskRow_${idx}">
                <div class="task-index">S${shot.scene_number || 1}-#${shot.shot_number || 1}</div>
                <div class="task-content">
                    ${modeSelectorHtml}
                    <div class="task-prompt">
                        <span class="prompt-label">画面描述:</span>
                        <span class="prompt-text" id="prompt-text-${idx}">${(currentVisualDesc || shot.visual_description || shot.screen_action || '').substring(0, 150)}${(currentVisualDesc || shot.visual_description || shot.screen_action || '').length > 150 ? '...' : ''}</span>
                    </div>
                    ${shot.plot_content ? `
                    <div class="task-plot">
                        <span class="plot-label">📖 情节:</span>
                        <span class="plot-text">${shot.plot_content.substring(0, 150)}${shot.plot_content.length > 150 ? '...' : ''}</span>
                    </div>
                    ` : ''}
                    ${hasDialogue ? dialogueDisplayHtml : ''}
                    ${hasErrorMessage ? `
                    <div class="task-error" style="
                        background: var(--danger-bg, rgba(239, 68, 68, 0.1));
                        border-left: 3px solid var(--danger);
                        padding: 0.5rem 0.75rem;
                        border-radius: 4px;
                        margin-top: 0.5rem;
                    ">
                        <span class="error-label" style="color: var(--danger); font-weight: 500;">❌ 错误原因:</span>
                        <span class="error-text" style="color: var(--text-secondary); margin-left: 0.5rem;">${errorMessage}</span>
                    </div>
                    ` : ''}
                    <div class="task-meta">
                        <span class="meta-tag">${shot.shot_type || '镜头'}</span>
                        <span class="meta-tag">⏱️ ${shot.duration || 5}秒</span>
                        ${isCompleted ? '<span class="meta-tag success">📸 ' + referenceImages.length + '张参考</span>' : ''}
                    </div>
                    ${isCompleted && hasRefs ? `
                    <div class="task-refs">
                        <span class="refs-label">参考图:</span>
                        <div class="refs-thumbnails">${refsThumbnailsHtml}</div>
                    </div>
                    ` : ''}
                </div>
                <div class="task-visual">
                    ${hasRefs ? `<div class="refs-thumbnails">${refsThumbnailsHtml}</div>` : '<div class="task-visual-empty"></div>'}
                    ${hasRefs ? '<span class="visual-arrow">→</span>' : ''}
                    ${videoPreviewHtml}
                </div>
                <div class="task-actions">
                    <button class="task-btn" onclick="shortDramaStudio.showBilingualPromptModal(${idx})" title="编辑中英文提示词" style="font-size: 11px; font-weight: bold; color: #6366f1;">EN</button>
                    ${isCompleted ? `
                    <button class="task-btn view-btn" onclick="shortDramaStudio.previewVideo(${idx})" title="查看视频">
                        <span>👁️</span>
                    </button>
                    <button class="task-btn restore-btn" onclick="shortDramaStudio.showVideoRestoreModal(${idx})" title="还原备份">
                        <span>♻️</span>
                    </button>
                    <button class="task-btn retry-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="重新生成">
                        <span>🔄</span>
                    </button>
                    ` : `
                    <button class="task-btn generate-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="生成视频">
                        <span>🎬</span>
                    </button>
                    `}
                    ${hasError ? `<button class="task-btn retry-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="重试"><span>🔄</span></button>` : ''}
                </div>
                <div class="task-status">
                    <span class="status-dot ${statusClass}"></span>
                    <span class="status-text">${statusText}</span>
                </div>
            </div>
        `;
    }

    /**
     * 获取当前模式的视觉描述
     */
    getCurrentVisualDescription(shot) {
        const mode = shot.preferred_mode || 'standard';
        if (mode === 'reference' && shot.visual_description_reference) {
            return shot.visual_description_reference;
        }
        if (mode === 'frames' && shot.visual_description_frames) {
            return shot.visual_description_frames;
        }
        return shot.visual_description_standard || shot.visual_description || shot.screen_action || '';
    }

    /**
     * 获取当前模式的VeO提示词
     */
    getCurrentVeoPrompt(shot) {
        const mode = shot.preferred_mode || 'standard';
        if (mode === 'reference' && shot.veo_prompt_reference) {
            return shot.veo_prompt_reference;
        }
        if (mode === 'frames' && shot.veo_prompt_frames) {
            return shot.veo_prompt_frames;
        }
        return shot.veo_prompt_standard || shot.veo_prompt || '';
    }

    /**
     * 更新镜头的提示词模式（视频生成页面使用）
     */
    updateShotMode(idx) {
        const shot = this.shots[idx];
        if (!shot) return;
        
        const select = document.getElementById(`mode-select-${idx}`);
        if (!select) return;
        
        const mode = select.value;
        shot.preferred_mode = mode;
        
        // 更新显示的画面描述
        const promptTextEl = document.getElementById(`prompt-text-${idx}`);
        if (promptTextEl) {
            const newDesc = this.getCurrentVisualDescription(shot);
            promptTextEl.textContent = newDesc ? (newDesc.substring(0, 150) + (newDesc.length > 150 ? '...' : '')) : '';
        }
        
        console.log(`🎨 镜头 ${idx} 切换到模式:`, mode === 'standard' ? '标准模式' : mode === 'reference' ? '参考图模式' : '首尾帧模式');
    }

    /**
     * 解析台词数据，返回 {speaker, lines, tone}
     * 支持格式:
     * - 对象: {speaker: "角色", lines: "台词", tone: "语气"}
     * - 字符串: "(角色): 台词内容" 或 "角色: 台词内容"
     */
    parseDialogue(dialogue) {
        let speaker = '';
        let lines = '';
        let tone = '';

        if (typeof dialogue === 'string') {
            lines = dialogue;
            // 尝试从字符串中解析角色名: "(角色名): 台词" 或 "角色名: 台词"
            const speakerMatch = lines.match(/^[(\[]?([^)\]:]+)[)\]]?:?\s*(.+)$/);
            if (speakerMatch) {
                speaker = speakerMatch[1].trim();
                lines = speakerMatch[2].trim();
            } else {
                speaker = '未知';
            }
        } else if (typeof dialogue === 'object' && dialogue !== null) {
            speaker = dialogue.speaker || '';
            lines = dialogue.lines || '';
            tone = dialogue.tone || '';
            // 如果speaker为空，尝试从lines中解析
            if (!speaker && lines) {
                const speakerMatch = lines.match(/^[(\[]?([^)\]:]+)[)\]]?:?\s*(.+)$/);
                if (speakerMatch) {
                    speaker = speakerMatch[1].trim();
                    lines = speakerMatch[2].trim();
                }
            }
        }

        return { speaker, lines, tone };
    }

    /**
     * 清文件名
     */
    sanitizeFileName(name) {
        const invalidChars = ['<', '>', ':', '"', '/', '\\', '|', '?', '、', '？', '！', '＊', '＂', '＜', '＞', '／', '＼', '｜', '!'];
        let result = name;
        for (const char of invalidChars) {
            result = result.replace(new RegExp(char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '_');
        }
        return result.replace(/^_+|_+$/g, '');
    }

    /**
     * 生成单个镜头的配音（带确认弹窗）
     */
    async generateDubbing(idx) {
        console.log('🎙️ [配音] generateDubbing called with idx:', idx);

        // 🔥 优先从展开的配音镜头中获取
        let shot = this.expandedDubbingShots?.[idx];
        console.log('🎙️ [配音] 从expandedDubbingShots获取:', shot ? 'found' : 'not found');

        if (!shot) {
            // 回退到原始shots
            shot = this.shots[idx];
            console.log('🎙️ [配音] 从this.shots获取:', shot ? 'found' : 'not found');
        }
        if (!shot) {
            console.error('🎙️ [配音] shot未找到, idx:', idx);
            return;
        }

        // 🔥 获取对话数据
        let speaker, lines, tone;

        // 如果是展开的子镜头（有_dialogue_data）
        if (shot._dialogue_data && typeof shot._dialogue_data === 'object') {
            speaker = shot._dialogue_data.speaker;
            lines = shot._dialogue_data.lines;
            tone = shot._dialogue_data.tone;
        } else {
            // 如果是对话场景（有dialogues数组）
            if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
                const firstDialogue = shot.dialogues[0];
                speaker = firstDialogue.speaker;
                lines = firstDialogue.lines;
                tone = firstDialogue.tone;
            } else {
                // 普通镜头：解析dialogue对象
                const dialogueData = shot.dialogue || {};
                const parsed = this.parseDialogue(dialogueData);
                speaker = parsed.speaker;
                lines = parsed.lines;
                tone = parsed.tone;
            }
        }

        if (!lines || speaker === '无' || speaker === '未知') {
            this.showToast('此镜头无台词或无法识别角色', 'info');
            return;
        }

        // 显示配音确认弹窗
        this.showDubbingConfirmModal(idx, shot, speaker, lines, tone);
    }

    /**
     * 编辑台词（打开编辑弹窗）
     */
    editDubbing(idx) {
        // 🔥 优先从展开的配音镜头中获取
        let shot = this.expandedDubbingShots?.[idx];
        if (!shot) {
            // 回退到原始shots
            shot = this.shots[idx];
        }
        if (!shot) return;

        // 🔥 获取对话数据
        let speaker, lines, tone;

        if (shot._dialogue_data && typeof shot._dialogue_data === 'object') {
            speaker = shot._dialogue_data.speaker;
            lines = shot._dialogue_data.lines;
            tone = shot._dialogue_data.tone;
        } else if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
            const firstDialogue = shot.dialogues[0];
            speaker = firstDialogue.speaker;
            lines = firstDialogue.lines;
            tone = firstDialogue.tone;
        } else {
            const dialogueData = shot.dialogue || {};
            const parsed = this.parseDialogue(dialogueData);
            speaker = parsed.speaker;
            lines = parsed.lines;
            tone = parsed.tone;
        }

        if (!lines || speaker === '无' || speaker === '未知') {
            this.showToast('此镜头无台词或无法识别角色', 'info');
            return;
        }

        // 显示配音编辑弹窗
        this.showDubbingConfirmModal(idx, shot, speaker, lines, tone);
    }

    /**
     * 显示配音生成确认弹窗
     */
    showDubbingConfirmModal(idx, shot, speaker, lines, tone) {
        const modal = document.createElement('div');
        modal.className = 'dubbing-confirm-modal';
        modal.id = 'dubbingConfirmModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.85);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        // 🔥 使用实际的角色-音色映射
        const characterVoiceMap = this.characterVoiceMap || {};

        // 获取所有角色（从台词中提取的 + 项目角色）
        const allCharacters = new Set();
        this.shots.forEach(s => {
            const d = s.dialogue || s._dialogue_data || {};
            const { speaker } = this.parseDialogue(d);
            if (speaker && speaker !== '无' && speaker !== '未知') {
                allCharacters.add(speaker);
            }
        });
        this.characters?.forEach(c => {
            if (c.name) allCharacters.add(c.name);
        });

        // 如果当前说话者不在列表中，添加进去
        if (speaker && speaker !== '无' && speaker !== '未知') {
            allCharacters.add(speaker);
        }

        // 按字母顺序排序
        const sortedCharacters = Array.from(allCharacters).sort();

        // 当前说话者的默认音色
        const defaultVoiceId = characterVoiceMap[speaker] || this.characterVoices['默认'] || 'audiobook_male_1';

        // 🔥 添加下拉菜单深色样式
        const styleEl = document.createElement('style');
        styleEl.id = 'dubbingModalStyles';
        styleEl.textContent = `
            #dubbingConfirmModal select {
                background-color: #0f172a !important;
                color: #ffffff !important;
            }
            #dubbingConfirmModal select option {
                background-color: #1e293b !important;
                color: #ffffff !important;
                padding: 10px !important;
            }
            #dubbingConfirmModal select option:hover,
            #dubbingConfirmModal select option:focus,
            #dubbingConfirmModal select option:checked {
                background-color: #3b82f6 !important;
                color: #ffffff !important;
            }
            #dubbingConfirmModal select optgroup {
                background-color: #0f172a !important;
                color: #94a3b8 !important;
            }
        `;
        document.head.appendChild(styleEl);

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-secondary);
                border-radius: 16px;
                max-width: 700px;
                width: 90%;
                max-height: 90vh;
                overflow-y: auto;
                padding: 24px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            ">
                <div class="modal-header" style="
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    border-bottom: 1px solid var(--border);
                    padding-bottom: 16px;
                ">
                    <div>
                        <h3 style="margin: 0; font-size: 1.4rem;">🎙️ 确认生成配音 #${shot.shot_number || shot.scene_number || (idx + 1)}</h3>
                        <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                            ${shot.episode_title || ''} · ${shot.shot_type || '镜头'}
                        </p>
                    </div>
                    <button class="btn-close" onclick="this.closest('.dubbing-confirm-modal').remove(); document.getElementById('dubbingModalStyles')?.remove();" style="background: none; border: none; font-size: 1.8rem; cursor: pointer; color: var(--text-secondary);">×</button>
                </div>

                <div class="modal-body">
                    <!-- 镜头信息 -->
                    <div style="margin-bottom: 20px; padding: 16px; background: var(--bg-dark); border-radius: 12px;">
                        <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
                            <span class="badge" style="background: var(--primary-light); color: var(--primary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">${shot.shot_type || '镜头'}</span>
                            <span class="badge" style="background: var(--bg-tertiary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">⏱️ ${shot.duration || 5}秒</span>
                        </div>
                        <p style="color: var(--text-secondary); margin: 0; font-size: 0.85rem;">
                            🎬 画面: ${(shot.visual_description || shot.screen_action || '').substring(0, 100)}...
                        </p>
                    </div>

                    <!-- 台词确认 -->
                    <div style="margin-bottom: 20px;">
                        <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">💬 台词确认：</label>
                        <div style="padding: 16px; background: var(--bg-dark); border-radius: 12px; border: 1px solid var(--border);">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                <span id="currentSpeakerBadge" style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600;">${speaker}</span>
                                ${tone ? `<span style="color: var(--text-tertiary); font-size: 0.85rem; font-style: italic;">🎭 ${tone}</span>` : ''}
                            </div>
                            <textarea id="dialogueLinesEdit" style="
                                width: 100%;
                                min-height: 80px;
                                background: var(--bg-tertiary);
                                border: 1px solid var(--border);
                                border-radius: 8px;
                                padding: 12px;
                                color: var(--text-primary);
                                font-size: 1rem;
                                line-height: 1.6;
                                resize: vertical;
                                font-family: inherit;
                            ">${lines}</textarea>
                        </div>
                    </div>

                    <!-- 音色配置 -->
                    <div style="margin-bottom: 20px;">
                        <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">🎵 音色配置：</label>
                        <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px;">
                            <!-- 角色选择 -->
                            <div>
                                <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">角色 (${sortedCharacters.length}个):</label>
                                <select id="paramSpeaker" style="
                                    width: 100%;
                                    padding: 10px;
                                    background: var(--bg-dark);
                                    border: 1px solid var(--border);
                                    border-radius: 8px;
                                    color: var(--text-primary);
                                    font-size: 0.95rem;
                                ">
                                    ${sortedCharacters.map(char => `
                                        <option value="${char}" ${char === speaker ? 'selected' : ''}>${char}</option>
                                    `).join('')}
                                </select>
                            </div>
                            <!-- 音色ID -->
                            <div>
                                <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">音色ID:</label>
                                <select id="paramVoiceId" style="
                                    width: 100%;
                                    padding: 10px;
                                    background: var(--bg-dark);
                                    border-style: solid;
                                    border-width: 3px;
                                    border-color: #3b82f6;
                                    border-radius: 8px;
                                    color: #ffffff;
                                    font-size: 0.95rem;
                                    font-weight: 600;
                                    cursor: pointer;
                                    outline: none;
                                " onfocus="this.style.borderColor='#60a5fa'; this.style.boxShadow='0 0 0 3px rgba(59, 130, 246, 0.3)'" onblur="this.style.borderColor='#3b82f6'; this.style.boxShadow='none'">
                                    ${(() => { let hasSelected = false; return Object.entries(this.characterVoices).map(([name, id]) => { const isSelected = !hasSelected && id === defaultVoiceId; if (isSelected) hasSelected = true; return `<option value="${id}" ${isSelected ? 'selected' : ''} style="background: #1e293b; color: #fff; padding: 8px;">${name} (${id})</option>`; }).join(''); })()}
                                </select>
                            </div>
                            <!-- 语速 -->
                            <div>
                                <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">语速: <span id="speedValue">1.0</span></label>
                                <input type="range" id="paramSpeed" min="0.5" max="2" step="0.1" value="1.0" style="width: 100%;">
                            </div>
                            <!-- 音调 -->
                            <div>
                                <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">音调: <span id="pitchValue">0</span></label>
                                <input type="range" id="paramPitch" min="-12" max="12" step="1" value="0" style="width: 100%;">
                            </div>
                            <!-- 音量 -->
                            <div>
                                <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">音量: <span id="volValue">1.0</span></label>
                                <input type="range" id="paramVol" min="0.1" max="10" step="0.1" value="1.0" style="width: 100%;">
                            </div>
                        </div>
                        <p style="font-size: 0.85rem; color: var(--text-tertiary); margin-top: 12px;">
                            💡 提示: 语速 0.5-2.0, 音调 -12到12, 音量 0.1-10.0
                        </p>
                    </div>

                    <!-- 预估时长 -->
                    <div style="padding: 12px; background: rgba(59, 130, 246, 0.1); border-radius: 8px; border-left: 4px solid var(--primary);">
                        <span style="font-size: 0.9rem; color: var(--text-secondary);">
                            ⏱️ 预估音频时长: <strong style="color: var(--text-primary);">${(lines.length / 3.5).toFixed(1)}秒</strong>
                            （约 ${Math.ceil(lines.length / 15)} 字）
                        </span>
                    </div>
                </div>

                <div class="modal-footer" style="
                    display: flex;
                    justify-content: center;
                    gap: 16px;
                    padding-top: 20px;
                    border-top: 1px solid var(--border);
                ">
                    <button class="btn-cancel" onclick="this.closest('.dubbing-confirm-modal').remove(); document.getElementById('dubbingModalStyles')?.remove();" style="
                        padding: 12px 24px;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border);
                        border-radius: 10px;
                        color: var(--text-primary);
                        font-size: 1rem;
                        cursor: pointer;
                    ">取消</button>
                    <button class="btn-save" style="
                        padding: 12px 24px;
                        background: var(--success);
                        border: none;
                        border-radius: 10px;
                        color: white;
                        font-size: 1rem;
                        cursor: pointer;
                        font-weight: 600;
                    ">💾 保存台词</button>
                    <button class="btn-generate" style="
                        padding: 12px 32px;
                        background: var(--primary);
                        border: none;
                        border-radius: 10px;
                        color: white;
                        font-size: 1rem;
                        cursor: pointer;
                        font-weight: 600;
                    ">🎙️ 保存并生成</button>
                </div>
            </div>
        `;

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        document.body.appendChild(modal);

        // 绑定滑块值显示
        const speedSlider = modal.querySelector('#paramSpeed');
        const pitchSlider = modal.querySelector('#paramPitch');
        const volSlider = modal.querySelector('#paramVol');

        speedSlider.addEventListener('input', (e) => {
            modal.querySelector('#speedValue').textContent = e.target.value;
        });
        pitchSlider.addEventListener('input', (e) => {
            modal.querySelector('#pitchValue').textContent = e.target.value;
        });
        volSlider.addEventListener('input', (e) => {
            modal.querySelector('#volValue').textContent = e.target.value;
        });

        // 角色切换时自动选择对应音色
        const speakerSelect = modal.querySelector('#paramSpeaker');
        const voiceIdSelect = modal.querySelector('#paramVoiceId');
        const speakerBadge = modal.querySelector('#currentSpeakerBadge');

        speakerSelect.addEventListener('change', (e) => {
            const selectedSpeaker = e.target.value;
            // 更新badge显示
            speakerBadge.textContent = selectedSpeaker;

            // 从映射中查找音色
            let voiceId = characterVoiceMap[selectedSpeaker];
            if (!voiceId) {
                // 尝试从配置中查找
                voiceId = this.characterVoices[selectedSpeaker];
            }
            if (!voiceId) {
                // 使用默认音色
                voiceId = this.characterVoices['默认'] || 'female-qn-dahu';
            }

            if (voiceId) {
                voiceIdSelect.value = voiceId;
            }
        });

        // 保存台词按钮（仅保存，不生成）
        const saveBtn = modal.querySelector('.btn-save');
        saveBtn.addEventListener('click', () => {
            const finalLines = modal.querySelector('#dialogueLinesEdit').value.trim();
            const finalSpeaker = modal.querySelector('#paramSpeaker').value;

            if (!finalLines) {
                this.showToast('台词不能为空', 'error');
                return;
            }

            // 保存台词到shot对象
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            if (typeof dialogue === 'object') {
                dialogue.lines = finalLines;
                dialogue.speaker = finalSpeaker;
            } else {
                shot.dialogue = { speaker: finalSpeaker, lines: finalLines };
            }

            // 保存角色-音色映射
            const finalVoiceId = modal.querySelector('#paramVoiceId').value;
            characterVoiceMap[finalSpeaker] = finalVoiceId;

            // 刷新显示
            this.renderDubbingScene(shot, idx);
            this.showToast('台词已保存', 'success');

            // 移除弹窗和样式
            modal.remove();
            const styleEl = document.getElementById('dubbingModalStyles');
            if (styleEl) styleEl.remove();
        });

        // 保存并生成按钮
        const generateBtn = modal.querySelector('.btn-generate');
        generateBtn.addEventListener('click', async () => {
            const finalLines = modal.querySelector('#dialogueLinesEdit').value.trim();
            const finalSpeaker = modal.querySelector('#paramSpeaker').value;
            const finalVoiceId = modal.querySelector('#paramVoiceId').value;
            const speed = parseFloat(modal.querySelector('#paramSpeed').value);
            const pitch = parseInt(modal.querySelector('#paramPitch').value);
            const vol = parseFloat(modal.querySelector('#paramVol').value);

            if (!finalLines) {
                this.showToast('台词不能为空', 'error');
                return;
            }

            // 保存台词到shot对象
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            if (typeof dialogue === 'object') {
                dialogue.lines = finalLines;
                dialogue.speaker = finalSpeaker;
            } else {
                shot.dialogue = { speaker: finalSpeaker, lines: finalLines };
            }

            // 保存角色-音色映射
            characterVoiceMap[finalSpeaker] = finalVoiceId;

            // 移除弹窗和样式
            modal.remove();
            const styleEl2 = document.getElementById('dubbingModalStyles');
            if (styleEl2) styleEl2.remove();

            // 执行生成
            await this.executeDubbingGeneration(idx, finalSpeaker, finalLines, finalVoiceId, speed, pitch, vol);
        });
    }

    /**
     * 执行配音生成（实际API调用）
     */
    async executeDubbingGeneration(idx, speaker, lines, voiceId, speed, pitch, vol) {
        // 🔥 优先从展开的配音镜头中获取
        let shot = this.expandedDubbingShots?.[idx];
        if (!shot) {
            shot = this.shots[idx];
        }
        if (!shot) return;

        // 清理台词：移除可能存在的角色名前缀
        // 匹配模式: "角色名:台词", "(角色名):台词", "角色名：台词" 等
        let cleanLines = lines;
        const prefixPattern = /^[[(\s]*[^\]):：]+[\])]:?\s*/;
        if (prefixPattern.test(cleanLines)) {
            cleanLines = cleanLines.replace(prefixPattern, '');
        }

        // 获取语气信息
        let tone = '';
        if (shot._dialogue_data && typeof shot._dialogue_data === 'object') {
            tone = shot._dialogue_data.tone || '';
        } else {
            const dialogue = shot.dialogue || {};
            const parsedDialogue = this.parseDialogue(dialogue);
            tone = parsedDialogue.tone || dialogue.tone || '';
        }

        // 检查是否有已存在的音频，如果有则备份
        if (shot.audioUrl || shot.audio_path) {
            try {
                const episodeDirectoryName = this.getEpisodeDirectoryName();
                const backupResponse = await fetch('/api/short-drama/backup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        file_type: 'audio',
                        shot_number: shot.shot_number || shot.scene_number || (idx + 1),
                        file_path: shot.audio_path
                    })
                });
                const backupResult = await backupResponse.json();
                if (backupResult.success) {
                    this.showToast('原配音已备份，可随时还原', 'success');
                }
            } catch (e) {
                console.error('备份音频失败:', e);
            }
        }

        // 标记为生成中
        shot.dubbingGenerating = true;
        shot.dubbingError = false;
        this.renderDubbingScene(shot, idx);
        document.getElementById(`dubbingScene_${idx}`)?.classList.add('generating');

        // 显示进度提示
        const progressToast = this.showToast(`正在生成配音: ${cleanLines.substring(0, 20)}...`, 'info', 0);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            const response = await fetch('/api/tts/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    scene_number: shot._scene_number || shot.scene_number || 1,  // 🔥 场景号
                    shot_number: shot.shot_number || (idx + 1),  // 🔥 镜头号（场景内的编号）
                    event_name: shot.event_name || shot.event || '',
                    dialogue_index: shot.dialogue_index,
                    dialogue_count: shot.dialogue_count,
                    is_dialogue_scene: shot.is_dialogue_scene || false,
                    speaker: speaker,
                    lines: cleanLines,
                    tone: tone,
                    voice_id: voiceId,
                    speed: speed,
                    pitch: pitch,
                    vol: vol
                })
            });

            const result = await response.json();

            // 移除进度提示
            if (progressToast) progressToast.remove();

            if (result.success && result.audio_url) {
                // 添加时间戳避免浏览器缓存旧音频
                const timestamp = Date.now();
                shot.audioUrl = result.audio_url + (result.audio_url.includes('?') ? '&' : '?') + 't=' + timestamp;
                shot.audioPath = result.audio_path;
                shot.audioDuration = result.duration;
                shot.dubbingGenerating = false;
                shot.dubbingError = false;

                this.renderDubbingScene(shot, idx);
                this.updateDubbingStats();
                this.showToast('配音生成成功', 'success');
            } else {
                shot.dubbingGenerating = false;
                shot.dubbingError = true;
                this.renderDubbingScene(shot, idx);
                this.showToast(`生成失败: ${result.error || '未知错误'}`, 'error');
            }

        } catch (error) {
            shot.dubbingGenerating = false;
            shot.dubbingError = true;
            this.renderDubbingScene(shot, idx);
            if (progressToast) progressToast.remove();
            this.showToast(`生成失败: ${error.message}`, 'error');
        }
    }

    /**
     * 批量生成所有配音
     */
    async batchGenerateDubbing() {
        // 🔥 展开对话场景为独立的配音子镜头
        const expandedDialogueShots = [];
        for (const shot of this.shots) {
            if (shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues)) {
                // 对话场景：展开为多个子镜头
                shot.dialogues.forEach((dlg, dlgIdx) => {
                    expandedDialogueShots.push({
                        ...shot,
                        _dialogue_data: dlg,
                        dialogue: dlg.lines || dlg.speaker || '',
                        dialogue_index: dlgIdx + 1,
                        dialogue_count: shot.dialogues.length
                    });
                });
            } else {
                // 普通镜头：检查是否有台词
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                const { speaker, lines } = this.parseDialogue(dialogue);
                if (speaker && speaker !== '无' && speaker !== '未知' && lines) {
                    expandedDialogueShots.push(shot);
                }
            }
        }

        if (expandedDialogueShots.length === 0) {
            this.showToast('没有找到有台词的镜头', 'info');
            return;
        }

        const total = expandedDialogueShots.length;
        let completed = 0;
        let failed = 0;

        for (const shot of expandedDialogueShots) {
            const idx = this.shots.indexOf(shot);
            if (idx === -1) {
                // 对于展开的子镜头，需要特殊处理
                await this.generateDubbingForSubShot(shot);
                completed++;
            } else {
                await this.generateDubbing(idx);
                completed++;
            }

            // 等待一小段时间避免API限流
            await new Promise(r => setTimeout(r, 1500));

            // 更新进度
            const progress = Math.round((completed / total) * 100);
            this.showToast(`批量生成进度: ${progress}%`, 'info');
        }

        this.showToast(`批量生成完成！`, 'success');
    }

    /**
     * 为子镜头生成配音（用于对话场景中的单句对话）
     */
    async generateDubbingForSubShot(shot) {
        const dialogue = shot._dialogue_data || shot.dialogue || {};
        const { speaker, lines, tone } = this.parseDialogue(dialogue);

        if (!lines || speaker === '无' || speaker === '未知') {
            return;
        }

        // 标记为生成中
        shot.dubbingGenerating = true;
        shot.dubbingError = false;

        // 显示进度提示
        const progressToast = this.showToast(`正在生成配音: ${lines.substring(0, 20)}...`, 'info', 0);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            // 获取角色-音色映射
            let voiceId = this.characterVoiceMap[speaker] || this.characterVoices['默认'] || 'female-qn-dahu';

            const response = await fetch('/api/tts/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    scene_number: shot._scene_number || shot.scene_number || 1,  // 🔥 场景号
                    shot_number: shot.shot_number || 1,  // 🔥 镜头号（场景内的编号）
                    event_name: shot.event_name || shot.event || '',
                    dialogue_index: shot.dialogue_index,
                    dialogue_count: shot.dialogue_count,
                    is_dialogue_scene: shot.is_dialogue_scene || false,  // 🔥 是否为对话场景
                    speaker: speaker,
                    lines: lines,
                    tone: tone,  // 传递语气描述，后端会自动转换为emotion
                    voice_id: voiceId,
                    speed: 1.0,
                    pitch: 0,
                    vol: 1.0
                })
            });

            const result = await response.json();

            // 移除进度提示
            if (progressToast) progressToast.remove();

            if (result.success && result.audio_url) {
                // 添加时间戳避免浏览器缓存
                const timestamp = Date.now();
                shot.audioUrl = result.audio_url + (result.audio_url.includes('?') ? '&' : '?') + 't=' + timestamp;
                shot.audioPath = result.audio_path;
                shot.audioDuration = result.duration;
                shot.dubbingGenerating = false;
                shot.dubbingError = false;
                this.showToast('配音生成成功', 'success');
            } else {
                shot.dubbingGenerating = false;
                shot.dubbingError = true;
                this.showToast(`生成失败: ${result.error || '未知错误'}`, 'error');
            }
        } catch (error) {
            shot.dubbingGenerating = false;
            shot.dubbingError = true;
            if (progressToast) progressToast.remove();
            this.showToast(`生成失败: ${error.message}`, 'error');
        }
    }

    /**
     * 导出SRT字幕文件
     */
    async exportSubtitle() {
        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            const response = await fetch('/api/tts/export-subtitle', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    scenes: this.shots
                })
            });

            const result = await response.json();

            if (result.success) {
                // 触发下载SRT文件
                const blob = new Blob([result.content], { type: 'text/plain;charset=utf-8' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${episodeDirectoryName}_配音字幕.srt`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.showToast('字幕文件已导出', 'success');
            } else {
                this.showToast(`导出失败: ${result.error}`, 'error');
            }

        } catch (error) {
            this.showToast(`导出失败: ${error.message}`, 'error');
        }
    }

    /**
     * 下载所有音频文件（打包成ZIP）
     */
    async downloadAllAudio() {
        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            const response = await fetch('/api/tts/download-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName
                })
            });

            if (response.ok) {
                // 下载ZIP文件
                const blob = await response.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${episodeDirectoryName}_配音合集.zip`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);

                this.showToast('配音合集已打包下载', 'success');
            } else {
                const result = await response.json();
                this.showToast(`下载失败: ${result.error || '未知错误'}`, 'error');
            }
        } catch (error) {
            this.showToast(`下载失败: ${error.message}`, 'error');
        }
    }

    /**
     * 播放音频
     */
    playAudio(url) {
        const audio = new Audio(url);
        audio.play().catch(e => {
            this.showToast('播放失败，请先下载音频到本地', 'error');
        });
    }

    /**
     * 下载单个音频
     */
    downloadAudio(url, filename) {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        this.showToast('开始下载', 'success');
    }

    /**
     * 显示TTS配置弹窗
     */
    showTTSConfig() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: flex;
            justify-content: center; align-items: center; z-index: 10000;
        `;

        // 🔥 可用的TTS模型列表
        const ttsModels = [
            { id: 'speech-2.8-turbo', name: 'speech-2.8-turbo (推荐)' },
            { id: 'speech-01-turbo', name: 'speech-01-turbo' },
            { id: 'speech-01-hd', name: 'speech-01-hd' },
            { id: 'speech-02-turbo', name: 'speech-02-turbo' },
            { id: 'speech-02-hd', name: 'speech-02-hd' },
        ];

        // 获取当前配置的模型
        const currentModel = this.ttsModel || 'speech-2.8-turbo';

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-secondary); border-radius: 16px;
                max-width: 500px; width: 90%; padding: 2rem;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="margin: 0;">🎙️ TTS配置</h2>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">✕</button>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">MiniMax Group ID</label>
                    <input type="text" id="ttsGroupId" placeholder="请输入MiniMax Group ID" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">MiniMax API Key</label>
                    <input type="password" id="ttsApiKey" placeholder="请输入MiniMax API Key" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">TTS模型</label>
                    <select id="ttsModel" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        ${ttsModels.map(m => `
                            <option value="${m.id}" ${m.id === currentModel ? 'selected' : ''}>${m.name}</option>
                        `).join('')}
                    </select>
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                        💡 不同模型支持不同的音色和功能
                    </div>
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                    <button id="saveTtsConfigBtn" class="btn btn-primary" style="flex: 1;">保存配置</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()" style="flex: 1;">取消</button>
                </div>

                <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                    <p style="margin: 0 0 0.5rem 0;">📌 获取MiniMax API密钥：</p>
                    <ol style="margin: 0; padding-left: 1.5rem;">
                        <li>访问 <a href="https://www.minimaxi.com" target="_blank">https://www.minimaxi.com</a></li>
                        <li>注册/登录账号</li>
                        <li>进入控制台获取 Group ID 和 API Key</li>
                    </ol>
                </div>
            </div>
        `;

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // 保存配置
        const saveBtn = modal.querySelector('#saveTtsConfigBtn');
        saveBtn.addEventListener('click', async () => {
            const groupId = document.getElementById('ttsGroupId').value.trim();
            const apiKey = document.getElementById('ttsApiKey').value.trim();
            const model = document.getElementById('ttsModel').value;

            if (!groupId || !apiKey) {
                this.showToast('Group ID和API Key不能为空', 'error');
                return;
            }

            const response = await fetch('/api/tts/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    group_id: groupId,
                    api_key: apiKey,
                    model: model
                })
            });

            const result = await response.json();
            if (result.success) {
                this.showToast('TTS配置已保存', 'success');
                this.ttsModel = model;  // 更新本地模型配置
                modal.remove();
                this.loadDubbingStep(); // 刷新页面
            } else {
                this.showToast(`保存失败: ${result.error}`, 'error');
            }
        });

        document.body.appendChild(modal);
    }

    // VeO配置功能

    /**
     * 显示VeO配置弹窗
     */
    showVeOConfig() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.8); display: flex;
        justify-content: center; align-items: center; z-index: 10000;
    `;

    // 🔥 可用的VeO模型列表
    const veoModels = [
        { id: 'veo_3_1-fast-components', name: 'veo_3_1-fast-components (推荐)', desc: '参考图模式，适合大多数场景' },
        { id: 'veo_3_1-fast', name: 'veo_3_1-fast', desc: '首尾帧模式，适合精确控制' },
        { id: 'veo_3_1', name: 'veo_3_1', desc: '标准模式，质量最高' }
    ];

    // 获取当前配置
    const currentConfig = this.loadVeOConfig();

    modal.innerHTML = `
        <div class="modal-content" style="
            background: var(--bg-secondary); border-radius: 16px;
            max-width: 500px; width: 90%; padding: 2rem;
            box-shadow: 0 25px 80px rgba(0,0,0,0.4);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2 style="margin: 0;">🎬 VeO视频生成配置</h2>
                <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">✕</button>
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Base URL</label>
                <input type="text" id="veoApiUrl" value="${currentConfig.apiUrl}" placeholder="https://jyapi.ai-wx.cn" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Key</label>
                <input type="password" id="veoApiKey" value="${currentConfig.apiKey}" placeholder="请输入API Key" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认模型</label>
                <select id="veoModel" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
                    ${veoModels.map(m => `
                        <option value="${m.id}" ${m.id === currentConfig.model ? 'selected' : ''}>${m.name}</option>
                    `).join('')}
                </select>
                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;" id="modelDesc">
                    💡 ${veoModels.find(m => m.id === currentConfig.model)?.desc || '选择合适的模型'}
                </div>
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">轮询间隔（秒）</label>
                <input type="number" id="veoPollInterval" value="${currentConfig.pollInterval}" min="5" max="60" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
                <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                    💡 查询任务状态的间隔时间，建议10-15秒
                </div>
            </div>

            <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                <button id="saveVeoConfigBtn" class="btn btn-primary" style="flex: 1;">保存配置</button>
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()" style="flex: 1;">取消</button>
            </div>

            <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                <p style="margin: 0 0 0.5rem 0;">📌 获取AI-WX API密钥：</p>
                <ol style="margin: 0; padding-left: 1.5rem;">
                    <li>访问 <a href="https://jyapi.ai-wx.cn" target="_blank">https://jyapi.ai-wx.cn</a></li>
                    <li>注册/登录账号</li>
                    <li>获取API Key</li>
                </ol>
            </div>
        </div>
    `;

    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    // 模型选择变化时更新提示
    const modelSelect = modal.querySelector('#veoModel');
    const modelDesc = modal.querySelector('#modelDesc');
    modelSelect.addEventListener('change', () => {
        const selectedModel = veoModels.find(m => m.id === modelSelect.value);
        if (selectedModel && modelDesc) {
            modelDesc.textContent = '💡 ' + selectedModel.desc;
        }
    });

    // 保存配置
    const saveBtn = modal.querySelector('#saveVeoConfigBtn');
    saveBtn.addEventListener('click', () => {
        const apiUrl = document.getElementById('veoApiUrl').value.trim();
        const apiKey = document.getElementById('veoApiKey').value.trim();
        const model = document.getElementById('veoModel').value;
        const pollInterval = parseInt(document.getElementById('veoPollInterval').value);

        if (!apiUrl || !apiKey) {
            this.showToast('API URL和API Key不能为空', 'error');
            return;
        }

        if (pollInterval < 5 || pollInterval > 60) {
            this.showToast('轮询间隔必须在5-60秒之间', 'error');
            return;
        }

        // 保存配置到localStorage
        this.saveVeOConfig({
            apiUrl,
            apiKey,
            model,
            pollInterval
        });

        this.showToast('VeO配置已保存', 'success');
        modal.remove();
    });

    document.body.appendChild(modal);
}

/**
 * 加载VeO配置
 */
loadVeOConfig() {
    const defaultConfig = {
        apiUrl: 'https://jyapi.ai-wx.cn',
        apiKey: 'sk-0dDn3ajqtCc0PTMmD045Ff7902774431Ad0304E396C856E7',
        model: 'veo_3_1-fast-components',
        pollInterval: 10
    };

    try {
        const saved = localStorage.getItem('veo_config');
        if (saved) {
            return { ...defaultConfig, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('加载VeO配置失败:', e);
    }

    return defaultConfig;
}

/**
 * 保存VeO配置
 */
saveVeOConfig(config) {
    try {
        localStorage.setItem('veo_config', JSON.stringify(config));
    } catch (e) {
        console.error('保存VeO配置失败:', e);
        this.showToast('保存配置失败', 'error');
    }
}

// Gemini配置功能

/**
 * 显示Gemini配置弹窗
 */
async showGeminiConfig() {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.8); display: flex;
        justify-content: center; align-items: center; z-index: 10000;
    `;

    // 从后端获取当前配置
    let currentConfig = this.loadGeminiConfig();
    try {
        const response = await fetch('/api/tts/gemini/config');
        const result = await response.json();
        if (result.success && result.configured) {
            // 使用后端配置覆盖本地缓存
            currentConfig = {
                apiUrl: result.api_url || currentConfig.apiUrl,
                apiKey: result.api_key || currentConfig.apiKey,
                model: result.model || currentConfig.model
            };
        }
    } catch (e) {
        console.log('获取后端配置失败，使用本地缓存:', e);
    }

    modal.innerHTML = `
        <div class="modal-content" style="
            background: var(--bg-secondary); border-radius: 16px;
            max-width: 500px; width: 90%; padding: 2rem;
            box-shadow: 0 25px 80px rgba(0,0,0,0.4);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2 style="margin: 0;">🤖 Gemini API配置</h2>
                <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">✕</button>
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Base URL</label>
                <input type="text" id="geminiApiUrl" value="${currentConfig.apiUrl}" placeholder="https://api.gemini.com" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Key</label>
                <input type="password" id="geminiApiKey" value="${currentConfig.apiKey}" placeholder="请输入Gemini API Key" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
            </div>

            <div style="margin-bottom: 1rem;">
                <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认模型</label>
                <select id="geminiModel" style="
                    width: 100%; padding: 10px; background: var(--bg-dark);
                    border: 1px solid var(--border); border-radius: 8px;
                    color: var(--text-primary); font-size: 1rem;
                ">
                    <option value="gemini-2.5-pro" ${currentConfig.model === 'gemini-2.5-pro' ? 'selected' : ''} style="background: #1e293b; color: #fff;">Gemini 2.5 Pro (推荐)</option>
                    <option value="gemini-2.0-flash" ${currentConfig.model === 'gemini-2.0-flash' ? 'selected' : ''} style="background: #1e293b; color: #fff;">Gemini 2.0 Flash</option>
                    <option value="gemini-1.5-pro" ${currentConfig.model === 'gemini-1.5-pro' ? 'selected' : ''} style="background: #1e293b; color: #fff;">Gemini 1.5 Pro</option>
                    <option value="gemini-3-pro-preview" ${currentConfig.model === 'gemini-3-pro-preview' ? 'selected' : ''} style="background: #1e293b; color: #fff;">Gemini 3 Pro Preview</option>
                </select>
            </div>

            <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                <button id="saveGeminiConfigBtn" class="btn btn-primary" style="flex: 1;">保存配置</button>
                <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()" style="flex: 1;">取消</button>
            </div>

            <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                <p style="margin: 0 0 0.5rem 0;">📌 获取Gemini API密钥：</p>
                <ol style="margin: 0; padding-left: 1.5rem;">
                    <li>访问 <a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a></li>
                    <li>登录Google账号</li>
                    <li>创建新的API Key</li>
                </ol>
            </div>
        </div>
    `;

    // 点击背景关闭
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });

    // 保存配置
    const saveBtn = modal.querySelector('#saveGeminiConfigBtn');
    saveBtn.addEventListener('click', async () => {
        const apiUrl = document.getElementById('geminiApiUrl').value.trim();
        const apiKey = document.getElementById('geminiApiKey').value.trim();
        const model = document.getElementById('geminiModel').value;

        if (!apiUrl || !apiKey) {
            this.showToast('API URL和API Key不能为空', 'error');
            return;
        }

        // 保存配置到localStorage
        this.saveGeminiConfig({
            apiUrl,
            apiKey,
            model
        });

        // 同步到后端
        try {
            const response = await fetch('/api/tts/gemini/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    api_url: apiUrl,
                    api_key: apiKey,
                    model: model
                })
            });

            const result = await response.json();
            if (result.success) {
                this.showToast('Gemini配置已保存并生效', 'success');
                modal.remove();
            } else {
                this.showToast(`保存失败: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('保存Gemini配置失败:', error);
            this.showToast('保存失败，请检查网络', 'error');
        }
    });

    document.body.appendChild(modal);
}

/**
 * 加载Gemini配置
 */
loadGeminiConfig() {
    const defaultConfig = {
        apiUrl: 'https://generativelanguage.googleapis.com',
        apiKey: '',
        model: 'gemini-2.5-pro'
    };

    try {
        const saved = localStorage.getItem('gemini_config');
        if (saved) {
            return { ...defaultConfig, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('加载Gemini配置失败:', e);
    }

    return defaultConfig;
}

/**
 * 保存Gemini配置
 */
saveGeminiConfig(config) {
    try {
        localStorage.setItem('gemini_config', JSON.stringify(config));
    } catch (e) {
        console.error('保存Gemini配置失败:', e);
        this.showToast('保存配置失败', 'error');
    }
}

    /**
     * 刷新当前步骤
     */
    refreshCurrentStep() {
        if (this.currentStep) {
            this.invalidateStepCache(this.currentStep);
            this.goToStep(this.currentStep, true);
        }
    }

    /**
     * 刷新视频状态
     */
    async refreshVideos() {
        this.invalidateStepCache('video');
        this.loadedSteps?.delete('video');
        await this.loadVideoStep();
        this.showToast('已刷新视频状态', 'success');
    }

    /**
     * 生成单个镜头视频
     */
    async generateShotVideo(shotIndex) {
        const shot = this.shots[shotIndex];
        if (!shot) return;

        // 标记为生成中
        shot.generating = true;
        shot.hasError = false;
        this.updateVideoCard(shotIndex);

        // 显示进度弹窗
        this.showVideoProgressModal(shot, shotIndex);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const videoSettings = this.getVideoSettings();

            // 🔥 构建包含台词和音频提示的 prompt，用于 AI 口型同步
            let prompt = shot.veo_prompt || shot.screen_action || '';

            // 检查是否有英文台词和音频提示，用于口型同步
            const dialogueData = shot._dialogue_data || shot.dialogue;
            if (dialogueData) {
                // 添加英文台词
                if (dialogueData.lines_en && dialogueData.lines_en.trim()) {
                    prompt += `. Character speaking: "${dialogueData.lines_en}"`;
                }
                // 添加音频提示（音效/BGM等）
                if (dialogueData.audio_note_en && dialogueData.audio_note_en.trim()) {
                    prompt += `. Audio: ${dialogueData.audio_note_en}`;
                }
            }

            // 🔥 打印发送给API的实际提示词，方便排查
            console.log('📤 [发送给VeO API的提示词 - 批量生成]');
            console.log('  - 镜头: S' + (shot._scene_number || shot.scene_number || 1) + '#' + (shot.shot_number || (shotIndex + 1)));
            console.log('  - 提示词长度:', prompt.length, '字符');
            console.log('  - 提示词内容:\n' + prompt);

            // 🔥 无参考图模式：强制使用 veo_3_1-fast 模型
            const finalModel = 'veo_3_1-fast';
            console.log('  - 模型: ' + finalModel + ' (无参考图模式)');

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: finalModel,
                    prompt: prompt,
                    image_urls: [],
                    orientation: videoSettings.orientation,
                    size: videoSettings.size,
                    watermark: false,
                    private: true,
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        scene_number: shot._scene_number || shot.scene_number || 1,  // 🔥 场景号（从分镜头文件获取）
                        shot_number: String(shot.shot_number || (shotIndex + 1)),  // 🔥 镜头号（场景内的编号）
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        is_dialogue_scene: shot.is_dialogue_scene || false,
                        lines_en: dialogueData?.lines_en || ''
                    }
                })
            });

            // 🔥 调试日志
            console.log('🎬 [视频生成] scene_number:', shot.scene_number, 'shot_number:', shot.shot_number, 'event_name:', shot.episode_title);

            const data = await response.json();

            if (data.id) {
                // 开始轮询状态
                await this.pollVideoStatus(data.id, shotIndex);
            } else {
                throw new Error(data.error?.message || '生成失败');
            }
        } catch (error) {
            console.error('生成视频失败:', error);
            shot.generating = false;
            shot.hasError = true;
            shot.errorMessage = error.message || '生成失败';
            this.updateVideoCard(shotIndex);
            this.closeVideoProgressModal(shotIndex);
            this.showToast('生成视频失败: ' + error.message, 'error');
        }
    }

    /**
     * 更新视频卡片状态
     */
    updateVideoCard(shotIndex) {
        const row = document.getElementById(`taskRow_${shotIndex}`);
        const shot = this.shots[shotIndex];

        console.log(`🎬 [更新卡片] shotIndex=${shotIndex}, row存在=${!!row}, shot.videoExists=${shot?.videoExists}, shot.generating=${shot?.generating}`);

        if (row && shot) {
            row.outerHTML = this.renderVideoTaskRow(shot, shotIndex);
        } else if (shot && shot.videoExists) {
            console.warn(`🎬 [更新卡片] 找不到行元素 taskRow_${shotIndex}, 但视频已生成`);
            // 尝试重新渲染整个视频列表
            this.renderVideoCards();
        } else {
            console.warn(`🎬 [更新卡片] row不存在, shot=${shot ? '存在但未完成' : '不存在'}`);
        }
    }

    /**
     * 显示视频进度弹窗（参考旧样式）
     */
    showVideoProgressModal(shot, shotIndex) {
        // 🔥 为每个任务创建独立的模态框 ID
        const modalId = `videoProgressModal_${shotIndex}`;
        // 先关闭可能存在的旧弹窗
        const oldModal = document.getElementById(modalId);
        if (oldModal) oldModal.remove();

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = modalId;
        modal.dataset.shotIndex = shotIndex; // 保存 shotIndex 用于识别
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
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
                max-width: 700px;
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
                        <h3 style="margin: 0;">🎬 生成视频 #${shot.shot_number || (shotIndex + 1)}</h3>
                        <p style="margin: 0.25rem 0 0 0; color: var(--text-secondary); font-size: 0.85rem;">
                            ${shot.shot_type || '镜头'} - ${shot.duration || 5}秒
                        </p>
                    </div>
                    <span style="color: var(--warning); font-size: 1.5rem;" id="videoStatusIcon">⏳</span>
                </div>

                <div style="
                    background: var(--bg-tertiary);
                    padding: 1rem;
                    border-radius: 8px;
                    margin-bottom: 1rem;
                ">
                    <!-- 进度条 -->
                    <div style="
                        width: 100%;
                        height: 8px;
                        background: var(--bg-dark);
                        border-radius: 4px;
                        overflow: hidden;
                        margin-bottom: 0.75rem;
                    ">
                        <div id="videoProgressBar" style="
                            width: 0%;
                            height: 100%;
                            background: linear-gradient(90deg, var(--primary), var(--accent));
                            border-radius: 4px;
                            transition: width 0.3s ease;
                        "></div>
                    </div>

                    <div style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    ">
                        <div class="video-progress-spinner" style="
                            width: 32px;
                            height: 32px;
                            border: 3px solid var(--border);
                            border-top-color: var(--primary);
                            border-radius: 50%;
                            animation: spin 1s linear infinite;
                        "></div>
                        <div style="flex: 1; margin-left: 1rem;">
                            <p style="margin: 0; font-size: 0.9rem; color: var(--text-secondary);" id="videoProgressText">正在生成视频...</p>
                            <p style="margin: 0.25rem 0 0 0; font-size: 0.8rem; color: var(--text-tertiary);" id="videoProgressStatus">⏳ 提交任务中...</p>
                        </div>
                        <span style="font-size: 1.5rem; font-weight: bold; color: var(--primary);" id="videoProgressPercent">0%</span>
                    </div>
                </div>

                <div style="
                    background: var(--bg-dark);
                    padding: 0.75rem;
                    border-radius: 6px;
                    margin-bottom: 1rem;
                    font-size: 0.85rem;
                    color: var(--text-secondary);
                    max-height: 120px;
                    overflow-y: auto;
                ">
                    ${(shot.veo_prompt || shot.screen_action || '').substring(0, 300)}...
                </div>

                <div style="
                    display: flex;
                    justify-content: center;
                    gap: 1rem;
                ">
                    <button class="btn-background" id="btnBackgroundGeneration" style="
                        padding: 0.75rem 1.5rem;
                        background: var(--warning);
                        border: none;
                        border-radius: 6px;
                        color: white;
                        cursor: pointer;
                        font-weight: 500;
                    ">📥 切换到后台</button>
                    <button class="btn-stop" id="btnStopGeneration" style="
                        padding: 0.75rem 1.5rem;
                        background: var(--danger);
                        border: none;
                        border-radius: 6px;
                        color: white;
                        cursor: pointer;
                        font-weight: 500;
                    ">⏹️ 停止生成</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 绑定后台运行按钮
        modal.querySelector('#btnBackgroundGeneration').onclick = () => {
            this.minimizeVideoProgressModal(shotIndex);
        };

        // 绑定停止按钮
        modal.querySelector('#btnStopGeneration').onclick = () => {
            this.closeVideoProgressModal(shotIndex);
            this.showToast('已停止生成', 'info');
        };
    }

    /**
     * 最小化视频进度弹窗到后台
     */
    minimizeVideoProgressModal(shotIndex) {
        // 获取当前的任务ID（如果已经开始生成）
        const shot = this.shots[shotIndex];
        if (!shot) return;

        // 关闭弹窗
        this.closeVideoProgressModal(shotIndex);

        // 🔥 修复：始终使用 shotIndex 作为后台任务的键，避免 ID 不匹配问题
        const bgTaskKey = `bg_${shotIndex}`;
        const apiTaskId = shot.currentTaskId || null;

        this.backgroundTasks.set(bgTaskKey, {
            shotIndex: shotIndex,
            shot: shot,
            taskId: bgTaskKey,
            apiTaskId: apiTaskId,  // 保存真实的 API 任务 ID
            startTime: Date.now(),
            progress: 0,
            status: '处理中...'
        });

        console.log(`🎬 [后台任务] 添加任务 bgTaskKey=${bgTaskKey}, apiTaskId=${apiTaskId}`);

        // 更新后台任务显示
        this.updateBackgroundTasksWidget();

        this.showToast('视频正在后台生成中...', 'info');
    }

    /**
     * 更新后台任务小组件
     */
    updateBackgroundTasksWidget() {
        let widget = document.getElementById('backgroundTasksWidget');

        if (this.backgroundTasks.size === 0) {
            if (widget) widget.remove();
            return;
        }

        if (!widget) {
            widget = document.createElement('div');
            widget.id = 'backgroundTasksWidget';
            widget.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 350px;
                width: auto;
            `;
            document.body.appendChild(widget);
        }

        widget.innerHTML = `
            <div style="
                background: var(--bg-secondary);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 1rem;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                margin-bottom: 0.5rem;
            ">
                <div style="
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 0.75rem;
                ">
                    <span style="font-weight: 600; color: var(--text-secondary);">
                        🎬 后台生成中 (${this.backgroundTasks.size})
                    </span>
                </div>
                ${Array.from(this.backgroundTasks.values()).map(task => {
                    const shot = task.shot;
                    const progress = task.progress || 0;
                    const status = task.status || '处理中...';
                    // 🔥 优化显示：显示场景编号和镜头编号
                    const sceneNum = shot._scene_number || shot.scene_number || '?';
                    const shotNum = shot.shot_number || (task.shotIndex + 1);
                    const displayTitle = `S${sceneNum}#${shotNum} ${shot.shot_type || '镜头'}`;
                    return `
                        <div class="bg-task-item" data-task-id="${task.taskId}" style="
                            background: var(--bg-tertiary);
                            padding: 0.75rem;
                            border-radius: 8px;
                            margin-bottom: 0.5rem;
                            cursor: pointer;
                            transition: background 0.2s;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                <div style="flex: 1; min-width: 0;">
                                    <div style="font-size: 0.85rem; font-weight: 500; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        ${displayTitle}
                                    </div>
                                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 0.25rem;">
                                        ${status}
                                    </div>
                                </div>
                                <div style="margin-left: 0.75rem; font-size: 0.85rem; font-weight: bold; color: var(--primary);">
                                    ${progress}%
                                </div>
                            </div>
                            <div style="
                                height: 4px;
                                background: var(--bg-dark);
                                border-radius: 2px;
                                overflow: hidden;
                            ">
                                <div style="
                                    width: ${progress}%;
                                    height: 100%;
                                    background: ${progress >= 100 ? 'var(--success)' : 'var(--primary)'};
                                    transition: width 0.3s;
                                "></div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;

        // 绑定点击事件，可以重新打开进度弹窗
        widget.querySelectorAll('.bg-task-item').forEach(item => {
            item.addEventListener('click', () => {
                const taskId = item.dataset.taskId;
                const task = this.backgroundTasks.get(taskId);
                if (task) {
                    // 从后台任务中移除
                    this.backgroundTasks.delete(taskId);
                    this.updateBackgroundTasksWidget();
                    // 重新显示进度弹窗
                    this.showVideoProgressModal(task.shot, task.shotIndex);
                }
            });
        });
    }

    /**
     * 更新后台任务的进度
     */
    updateBackgroundTaskProgress(shotIndex, progress, status, apiTaskId = null) {
        // 🔥 修复：使用 shotIndex 查找后台任务
        const bgTaskKey = `bg_${shotIndex}`;
        const task = this.backgroundTasks.get(bgTaskKey);

        if (task) {
            task.progress = progress;
            task.status = status;
            // 如果提供了 API 任务 ID，更新它
            if (apiTaskId) {
                task.apiTaskId = apiTaskId;
            }
            this.updateBackgroundTasksWidget();
            console.log(`🎬 [后台任务] 更新进度 shotIndex=${shotIndex}, progress=${progress}%, status=${status}`);
        } else {
            console.log(`🎬 [后台任务] 未找到任务 bgTaskKey=${bgTaskKey}`);
        }
    }

    /**
     * 从后台任务中移除已完成的任务
     */
    removeBackgroundTask(shotIndex) {
        // 🔥 修复：使用 shotIndex 查找后台任务
        const bgTaskKey = `bg_${shotIndex}`;
        this.backgroundTasks.delete(bgTaskKey);
        console.log(`🎬 [后台任务] 移除任务 bgTaskKey=${bgTaskKey}`);
        this.updateBackgroundTasksWidget();
    }

    /**
     * 更新视频进度弹窗（参考旧样式）
     */
    updateVideoProgressModal(progress, status, shotIndex = null, videoUrl = null) {
        // 🔥 优先使用特定任务的弹窗 ID
        const modalId = shotIndex !== null ? `videoProgressModal_${shotIndex}` : 'videoProgressModal';
        const modal = document.getElementById(modalId);
        if (!modal) return;

        const statusIcon = modal.querySelector('#videoStatusIcon');
        const progressText = modal.querySelector('#videoProgressText');
        const progressStatus = modal.querySelector('#videoProgressStatus');
        const progressBar = modal.querySelector('#videoProgressBar');
        const progressPercent = modal.querySelector('#videoProgressPercent');

        if (statusIcon) {
            if (progress >= 100) {
                statusIcon.textContent = '✓';
                statusIcon.style.color = 'var(--success)';
            } else if (status.includes('失败') || status.includes('❌')) {
                statusIcon.textContent = '✗';
                statusIcon.style.color = 'var(--danger)';
            }
        }

        if (progressBar) {
            progressBar.style.width = `${Math.min(100, progress)}%`;
            // 根据进度改变颜色
            if (progress >= 100) {
                progressBar.style.background = 'var(--success)';
            } else if (progress < 30) {
                progressBar.style.background = 'linear-gradient(90deg, #f59e0b, #f97316)';
            } else {
                progressBar.style.background = 'linear-gradient(90deg, var(--primary), var(--accent))';
            }
        }

        if (progressPercent) {
            progressPercent.textContent = `${Math.min(100, Math.round(progress))}%`;
        }

        if (progressText) {
            progressText.textContent = progress >= 100 ? '✅ 生成完成!' : status;
        }

        if (progressStatus) {
            // 提取状态文本中的表情符号和主要文本
            const statusLines = status.split('\n');
            progressStatus.textContent = statusLines[0] || status;
        }

        // 生成完成后，2秒后自动关闭弹窗
        if (progress >= 100 && shotIndex !== null) {
            setTimeout(() => {
                this.closeVideoProgressModal(shotIndex);
                // 更新卡片显示已完成
                this.updateVideoCard(shotIndex);
            }, 2000);
        }
    }

    /**
     * 显示视频预览弹窗（完全参考旧样式）
     */
    showVideoPreviewDialog(shot, currentIndex, total, videoUrl, isExistingVideo = false) {
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
                                ${shot.shot_type || '镜头'} - ${shot.duration || 5}秒
                            </p>
                        </div>
                        <span style="color: ${titleColor}; font-size: 2rem;">${isExistingVideo ? '▶' : '✓'}</span>
                    </div>

                    <div class="video-preview" style="
                        background: #000;
                        border-radius: 8px;
                        overflow: hidden;
                        aspect-ratio: 16/9;
                        margin-bottom: 1rem;
                    ">
                        <video src="${videoUrl}" controls autoplay loop style="width: 100%; height: 100%;"></video>
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
                        ${(shot.veo_prompt || shot.screen_action || '').substring(0, 200)}${(shot.veo_prompt || shot.screen_action || '').length > 200 ? '...' : ''}
                    </div>

                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 1rem;
                        flex-wrap: wrap;
                    ">
                        ${isExistingVideo ? `
                        <button class="btn-use-existing" style="
                            padding: 0.75rem 2rem;
                            background: var(--success);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                            font-weight: bold;
                        ">✅ 使用此视频</button>
                        ` : ''}
                        <button class="btn-regenerate" style="
                            padding: 0.75rem 1.5rem;
                            background: var(--warning);
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
                        <button class="btn-continue" style="
                            padding: 0.75rem 2rem;
                            background: var(--success);
                            border: none;
                            border-radius: 6px;
                            color: white;
                            cursor: pointer;
                            font-weight: bold;
                        ">➡️ 继续下一个</button>
                    </div>
                </div>
            `;

            document.body.appendChild(modal);

            // 绑定事件
            const btnStop = modal.querySelector('.btn-stop');
            if (btnStop) {
                btnStop.onclick = () => {
                    modal.remove();
                    resolve('cancel');
                };
            }

            const btnRegenerate = modal.querySelector('.btn-regenerate');
            if (btnRegenerate) {
                btnRegenerate.onclick = () => {
                    modal.remove();
                    // 获取镜头索引并重新生成
                    const shotIndex = this.shots.indexOf(shot);
                    if (shotIndex >= 0) {
                        this.generateShotVideo(shotIndex);
                    }
                };
            }

            const btnDownload = modal.querySelector('.btn-download');
            if (btnDownload) {
                btnDownload.onclick = () => {
                    this.downloadVideo(videoUrl);
                };
            }

            const btnContinue = modal.querySelector('.btn-continue');
            if (btnContinue) {
                btnContinue.onclick = () => {
                    modal.remove();
                    resolve('continue');
                };
            }

            const btnUseExisting = modal.querySelector('.btn-use-existing');
            if (btnUseExisting) {
                btnUseExisting.onclick = () => {
                    modal.remove();
                    resolve('continue');
                };
            }

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                    resolve('close');
                }
            });
        });
    }

    /**
     * 显示生成确认弹窗（完全参考旧UI）
     */
    async showGenerateConfirmModal(shot, idx) {
        // 获取角色剧照数据
        const characterPortraits = this.characterPortraits;

        // 获取项目视频设置作为默认值
        const videoSettings = this.getVideoSettings();

        // 🔥 自动加载 reference_images 目录中的图片
        let referenceImages = [];
        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const response = await fetch(`/api/short-drama/reference-images?novel=${encodeURIComponent(this.selectedNovel || '')}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();
            if (data.success && data.images) {
                referenceImages = data.images;
                console.log(`📸 自动加载了 ${referenceImages.length} 张参考图`);
            }
        } catch (error) {
            console.error('加载参考图失败:', error);
        }

        // 🔥 自动加载 场景道具 目录中的图片
        let sceneProps = [];
        try {
            const response = await fetch(`/api/short-drama/scene-props?novel=${encodeURIComponent(this.selectedNovel || '')}`);
            const data = await response.json();
            if (data.success && data.images) {
                sceneProps = data.images;
                console.log(`🎬 自动加载了 ${sceneProps.length} 张场景道具参考图`);
            }
        } catch (error) {
            console.error('加载场景道具失败:', error);
        }

        return new Promise((resolve) => {
            // 默认不选中任何图片，让用户手动选择
            const selectedImages = [];
            const allPortraits = Array.from(characterPortraits.entries());

            // 生成唯一键用于保存/加载提示词
            // 🔥 包含 scene_number 和 shot_number 确保唯一性
            const sceneNum = shot._scene_number || shot.scene_number || 1;
            const shotNum = shot.shot_number || (idx + 1);
            const shotKey = `videoPrompt_${this.selectedNovel}_${shot.episode_title || ''}_S${sceneNum}_#${shotNum}`;

            // 🔥 获取当前模式的英文提示词和中文描述
            const currentPromptEN = this.getCurrentVeoPrompt(shot);
            const currentPromptCN = this.getCurrentVisualDescription(shot);

            // 尝试加载之前保存的提示词
            const savedPromptEN = localStorage.getItem(shotKey + '_en');
            const savedPromptCN = localStorage.getItem(shotKey + '_cn');

            const promptToUseEN = savedPromptEN || currentPromptEN || '';
            const promptToUseCN = savedPromptCN || currentPromptCN || '';

            // 创建对话框
            const modal = document.createElement('div');
            modal.className = 'video-confirm-modal';
            modal.id = 'videoConfirmModal';
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            modal.innerHTML = `
                <div class="modal-content" style="
                    background: var(--bg-secondary);
                    border-radius: 16px;
                    max-width: 900px;
                    width: 90%;
                    max-height: 90vh;
                    overflow-y: auto;
                    padding: 24px;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
                ">
                    <div class="modal-header" style="
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        margin-bottom: 20px;
                        border-bottom: 1px solid var(--border);
                        padding-bottom: 16px;
                    ">
                        <div>
                            <h3 style="margin: 0; font-size: 1.4rem;">🎬 确认生成镜头 ${idx + 1}/${this.shots.length}</h3>
                            <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 0.9rem;">
                                ${shot.episode_title || ''} · ${shot.shot_type || '镜头'}
                            </p>
                        </div>
                        <button class="btn-close" style="background: none; border: none; font-size: 1.8rem; cursor: pointer; color: var(--text-secondary);">×
                        </button>
                    </div>

                    <div class="modal-body">
                        <!-- 镜头信息 -->
                        <div class="shot-info-section" style="margin-bottom: 16px;">
                            <div style="display: flex; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
                                <span class="badge" style="background: var(--primary-light, #e3f2fd); color: var(--primary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">${shot.episode_title || '镜头'}</span>
                                <span class="badge" style="background: var(--accent-color, #f3e5f5); color: var(--text-primary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">${shot.shot_type || '镜头'}</span>
                                <span class="badge" style="background: var(--bg-tertiary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">⏱️ ${shot.duration || 5}秒</span>
                                ${shot.preferred_mode ? `<span class="badge" style="background: #6366f1; color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">🎨 ${shot.preferred_mode === 'standard' ? '标准模式' : shot.preferred_mode === 'reference' ? '参考图模式' : '首尾帧模式'}</span>` : ''}
                                ${savedPromptCN || savedPromptEN ? '<span class="badge" style="background: var(--success); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">已保存提示词</span>' : ''}
                            </div>
                            <p style="color: var(--text-secondary); margin: 0; font-size: 0.9rem;">📍 ${shot.scene_title || ''}</p>
                        </div>

                        <!-- 提示词编辑区 -->
                        <div class="prompt-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">📝 AI提示语（中文）<span style="font-size: 0.8rem; color: #6366f1; margin-left: 8px;">(使用${shot.preferred_mode === 'standard' ? '标准' : shot.preferred_mode === 'reference' ? '参考图' : '首尾帧'}模式)</span></label>
                            <textarea id="promptEditAreaCN" style="
                                width: 100%;
                                min-height: 100px;
                                background: var(--bg-dark);
                                border: 1px solid var(--border);
                                border-radius: 12px;
                                padding: 16px;
                                color: var(--text-primary);
                                font-size: 1rem;
                                line-height: 1.6;
                                resize: vertical;
                                font-family: inherit;
                            ">${promptToUseCN}</textarea>

                            <label style="font-weight: 600; display: block; margin: 16px 0 12px 0; font-size: 1rem;">🌐 AI提示语（英文 - 实际发送给VeO）</label>
                            <textarea id="promptEditAreaEN" style="
                                width: 100%;
                                min-height: 100px;
                                background: var(--bg-dark);
                                border: 1px solid var(--border);
                                border-radius: 12px;
                                padding: 16px;
                                color: var(--text-primary);
                                font-size: 1rem;
                                line-height: 1.6;
                                resize: vertical;
                                font-family: inherit;
                            ">${promptToUseEN}</textarea>

                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; gap: 12px;">
                                <div style="display: flex; gap: 8px;">
                                    <button id="translateToEnBtn" style="font-size: 0.85rem; padding: 6px 12px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                                        中文 → 英文
                                    </button>
                                    <button id="translateToCnBtn" style="font-size: 0.85rem; padding: 6px 12px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                                        英文 → 中文
                                    </button>
                                </div>
                                <small style="color: var(--text-secondary); font-size: 0.9rem;">💾 修改后会自动保存到本地</small>
                            </div>
                        </div>

                        <!-- 情节参考区（只读） -->
                        ${shot.plot_content ? `
                        <div class="plot-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 8px; font-size: 0.95rem; color: var(--text-secondary);">📖 情节参考（仅供参考，不发送给AI）</label>
                            <div style="
                                width: 100%;
                                background: var(--bg-tertiary);
                                border: 1px dashed var(--border);
                                border-radius: 8px;
                                padding: 12px 16px;
                                color: var(--text-secondary);
                                font-size: 0.9rem;
                                line-height: 1.5;
                            ">${shot.plot_content}</div>
                        </div>
                        ` : ''}

                        <!-- 参考角色剧照选择 -->
                        <div class="reference-section" style="margin-bottom: 20px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <label style="font-weight: 600; font-size: 1rem; margin: 0;">🖼️ 选择参考角色剧照：</label>
                                <button type="button" id="addLocalImageBtn" style="
                                    padding: 8px 16px;
                                    background: var(--primary);
                                    border: none;
                                    border-radius: 8px;
                                    color: white;
                                    font-size: 0.9rem;
                                    cursor: pointer;
                                    display: flex;
                                    align-items: center;
                                    gap: 6px;
                                ">
                                    <span>+</span> 添加本地图片
                                </button>
                                <input type="file" id="localImageInput" accept="image/*" multiple style="display: none;">
                            </div>
                            <div id="portraitSelector" class="portrait-selector" style="
                                display: flex;
                                flex-wrap: wrap;
                                gap: 16px;
                                padding: 16px;
                                background: var(--bg-dark);
                                border-radius: 12px;
                                min-height: 100px;
                            ">
                                ${allPortraits.length > 0 ? allPortraits.map(([name, data], pIdx) => {
                                    const portrait = data.mainPortrait || data.portraits?.[0];
                                    const portraitUrl = portrait?.url;
                                    if (!portraitUrl) return '';
                                    return `
                                    <label class="portrait-checkbox" style="
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        cursor: pointer;
                                        position: relative;
                                        transition: transform 0.2s;
                                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                        <input type="checkbox" class="portrait-check" data-name="${name}" data-url="${portraitUrl}" data-type="character"
                                            style="position: absolute; opacity: 0; width: 0; height: 0;">
                                        <div class="portrait-thumb" style="
                                            width: 80px;
                                            height: 80px;
                                            border-radius: 12px;
                                            overflow: hidden;
                                            border: 3px solid var(--border);
                                            transition: all 0.2s;
                                            background: var(--bg-tertiary);
                                        ">
                                            <img src="${portraitUrl}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.parentElement.remove()">
                                        </div>
                                        <span style="font-size: 0.8rem; margin-top: 8px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);">${name}</span>
                                        <div class="check-indicator" style="
                                            position: absolute;
                                            top: 6px;
                                            right: 6px;
                                            width: 24px;
                                            height: 24px;
                                            background: rgba(0,0,0,0.6);
                                            border-radius: 50%;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            font-size: 12px;
                                            color: white;
                                        ">✓</div>
                                    </label>
                                `}).join('') : ''}
                                ${referenceImages.length > 0 ? referenceImages.map((img, rIdx) => `
                                    <label class="portrait-checkbox" style="
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        cursor: pointer;
                                        position: relative;
                                        transition: transform 0.2s;
                                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                        <input type="checkbox" class="portrait-check" data-name="参考图_${rIdx + 1}" data-url="${img.url}" data-type="reference"
                                            style="position: absolute; opacity: 0; width: 0; height: 0;">
                                        <div class="portrait-thumb" style="
                                            width: 80px;
                                            height: 80px;
                                            border-radius: 12px;
                                            overflow: hidden;
                                            border: 3px solid var(--success, #4caf50);
                                            transition: all 0.2s;
                                            background: var(--bg-tertiary);
                                        ">
                                            <img src="${img.url}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.parentElement.remove()">
                                        </div>
                                        <span style="font-size: 0.8rem; margin-top: 8px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);">参考图${rIdx + 1}</span>
                                        <div class="check-indicator" style="
                                            position: absolute;
                                            top: 6px;
                                            right: 6px;
                                            width: 24px;
                                            height: 24px;
                                            background: rgba(0,0,0,0.6);
                                            border-radius: 50%;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            font-size: 12px;
                                            color: white;
                                        ">✓</div>
                                    </label>
                                `).join('') : ''}
                                ${(allPortraits.length === 0 && referenceImages.length === 0) ? '<div style="color: var(--text-tertiary); padding: 20px;">暂无剧照，请先生成角色剧照，或点击上方按钮添加本地图片</div>' : ''}
                            </div>
                            <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 12px;">
                                已选择 <span id="selectedCount" style="color: var(--primary); font-weight: 600;">0</span> 张参考图
                                ${allPortraits.length > 0 || referenceImages.length > 0 ? '<span style="color: var(--text-tertiary); margin-left: 16px;">💡 点击图片选择，绿色边框为已上传的参考图</span>' : ''}
                            </p>
                        </div>

                        <!-- 🔥 场景道具参考图选择 -->
                        <div class="reference-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">🎬 选择场景道具参考图：</label>
                            <div id="scenePropsSelector" class="portrait-selector" style="
                                display: flex;
                                flex-wrap: wrap;
                                gap: 16px;
                                padding: 16px;
                                background: var(--bg-dark);
                                border-radius: 12px;
                                min-height: 80px;
                            ">
                                ${sceneProps.length > 0 ? sceneProps.map((img, sIdx) => `
                                    <label class="portrait-checkbox" style="
                                        display: flex;
                                        flex-direction: column;
                                        align-items: center;
                                        cursor: pointer;
                                        position: relative;
                                        transition: transform 0.2s;
                                    " onmouseover="this.style.transform='scale(1.05)'" onmouseout="this.style.transform='scale(1)'">
                                        <input type="checkbox" class="portrait-check" data-name="场景道具_${img.name}" data-url="${img.url}" data-type="scene-prop"
                                            style="position: absolute; opacity: 0; width: 0; height: 0;">
                                        <div class="portrait-thumb" style="
                                            width: 80px;
                                            height: 80px;
                                            border-radius: 12px;
                                            overflow: hidden;
                                            border: 3px solid #9c27b0;
                                            transition: all 0.2s;
                                            background: var(--bg-tertiary);
                                        ">
                                            <img src="${img.url}" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.parentElement.parentElement.remove()">
                                        </div>
                                        <span style="font-size: 0.8rem; margin-top: 8px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);">${img.name.replace(/\.[^/.]+$/, '')}</span>
                                        <div class="check-indicator" style="
                                            position: absolute;
                                            top: 6px;
                                            right: 6px;
                                            width: 24px;
                                            height: 24px;
                                            background: rgba(156, 39, 176, 0.8);
                                            border-radius: 50%;
                                            display: flex;
                                            align-items: center;
                                            justify-content: center;
                                            font-size: 12px;
                                            color: white;
                                        ">✓</div>
                                    </label>
                                `).join('') : ''}
                                ${sceneProps.length === 0 ? '<div style="color: var(--text-tertiary); padding: 12px;">暂无场景道具参考图，请将图片放在 <code>场景道具</code> 目录中</div>' : ''}
                            </div>
                        </div>

                        <!-- 生成参数 -->
                        <div class="params-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">⚙️ 生成参数：</label>
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;">
                                <div>
                                    <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">模型：</label>
                                    <select id="paramModel" style="
                                        width: 100%;
                                        padding: 10px;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 8px;
                                        color: var(--text-primary);
                                        font-size: 0.95rem;
                                        cursor: pointer;
                                    ">
                                        <option value="veo_3_1-fast-components" ${videoSettings.model === 'veo_3_1-fast-components' || videoSettings.model === 'veo_3_1-fast-components-4K' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">1080p参考图模式</option>
                                        <option value="veo_3_1-fast" ${videoSettings.model === 'veo_3_1-fast' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">首尾帧模式</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">方向：</label>
                                    <select id="paramOrientation" style="
                                        width: 100%;
                                        padding: 10px;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 8px;
                                        color: var(--text-primary);
                                        font-size: 0.95rem;
                                        cursor: pointer;
                                    ">
                                        <option value="portrait" ${videoSettings.orientation === 'portrait' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">竖屏 (9:16)</option>
                                        <option value="landscape" ${videoSettings.orientation === 'landscape' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">横屏 (16:9)</option>
                                    </select>
                                </div>
                                <div>
                                    <label style="font-size: 0.9rem; color: var(--text-secondary); display: block; margin-bottom: 6px;">尺寸：</label>
                                    <select id="paramSize" style="
                                        width: 100%;
                                        padding: 10px;
                                        background: var(--bg-dark);
                                        border: 1px solid var(--border);
                                        border-radius: 8px;
                                        color: var(--text-primary);
                                        font-size: 0.95rem;
                                        cursor: pointer;
                                    ">
                                        <option value="2160x3840" ${videoSettings.size === '2160x3840' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">4K竖屏 (2160x3840)</option>
                                        <option value="3840x2160" ${videoSettings.size === '3840x2160' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">4K横屏 (3840x2160)</option>
                                        <option value="1440x2560" ${videoSettings.size === '1440x2560' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">2K竖屏 (1440x2560)</option>
                                        <option value="2560x1440" ${videoSettings.size === '2560x1440' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">2K横屏 (2560x1440)</option>
                                        <option value="1080x1920" ${videoSettings.size === '1080x1920' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">1080p竖屏 (1080x1920)</option>
                                        <option value="1920x1080" ${videoSettings.size === '1920x1080' ? 'selected' : ''} style="background: #1e1e2e; color: #fff;">1080p横屏 (1920x1080)</option>
                                    </select>
                                </div>
                            </div>
                            <div style="margin-top: 16px;">
                                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.95rem; color: var(--text-secondary); cursor: pointer;">
                                    <input type="checkbox" id="paramFirstLastFrame" ${videoSettings.use_first_last_frame ? 'checked' : ''} style="margin: 0; width: 18px; height: 18px;">
                                    <span>🎞️ 启用首尾帧模式（需选择1-2张图片）</span>
                                </label>
                            </div>
                        </div>
                    </div>

                    <div class="modal-footer" style="
                        display: flex;
                        justify-content: center;
                        gap: 16px;
                        padding-top: 20px;
                        border-top: 1px solid var(--border);
                    ">
                        <button class="btn-cancel" style="
                            padding: 12px 24px;
                            background: var(--danger);
                            border: none;
                            border-radius: 10px;
                            color: white;
                            font-size: 1rem;
                            cursor: pointer;
                        ">❌ 全部取消</button>
                        <button class="btn-skip" style="
                            padding: 12px 24px;
                            background: var(--bg-tertiary);
                            border: 1px solid var(--border);
                            border-radius: 10px;
                            color: var(--text-primary);
                            font-size: 1rem;
                            cursor: pointer;
                        ">⏭️ 跳过此镜头</button>
                        <button class="btn-generate" style="
                            padding: 12px 32px;
                            background: var(--primary);
                            border: none;
                            border-radius: 10px;
                            color: white;
                            font-size: 1rem;
                            font-weight: 600;
                            cursor: pointer;
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
            const promptAreaCN = document.getElementById('promptEditAreaCN');
            const promptAreaEN = document.getElementById('promptEditAreaEN');
            const translateToEnBtn = document.getElementById('translateToEnBtn');
            const translateToCnBtn = document.getElementById('translateToCnBtn');

            // 处理剧照选择
            const portraitChecks = modal.querySelectorAll('.portrait-check');
            const selectedCountEl = document.getElementById('selectedCount');
            const firstLastFrameCheck = document.getElementById('paramFirstLastFrame');

            portraitChecks.forEach(check => {
                check.addEventListener('change', () => {
                    const thumb = check.parentElement.querySelector('.portrait-thumb');
                    const indicator = check.parentElement.querySelector('.check-indicator');
                    const count = modal.querySelectorAll('.portrait-check:checked').length;

                    selectedCountEl.textContent = count;

                    if (check.checked) {
                        thumb.style.borderColor = 'var(--primary)';
                        thumb.style.boxShadow = '0 0 0 3px var(--primary-light)';
                        indicator.textContent = '✓';
                        indicator.style.background = 'var(--primary)';

                        // 🔥 首尾帧模式：添加帧位置选择按钮
                        if (firstLastFrameCheck.checked) {
                            this.updateFramePositionButtons(check.parentElement, modal);
                        }
                    } else {
                        thumb.style.borderColor = 'var(--border)';
                        thumb.style.boxShadow = 'none';
                        indicator.textContent = '';
                        indicator.style.background = 'rgba(0,0,0,0.6)';

                        // 移除帧位置按钮
                        const frameButtons = check.parentElement.querySelector('.frame-position-buttons');
                        if (frameButtons) frameButtons.remove();
                        check.removeAttribute('data-frame-position');
                    }

                    // 首尾帧模式提示
                    if (firstLastFrameCheck.checked && count < 1) {
                        selectedCountEl.textContent = count + ' (首尾帧至少需要1张)';
                    } else if (firstLastFrameCheck.checked && count > 0) {
                        const firstCount = modal.querySelectorAll('.portrait-check[data-frame-position="first"]').length;
                        const lastCount = modal.querySelectorAll('.portrait-check[data-frame-position="last"]').length;
                        selectedCountEl.textContent = count + ` (首帧:${firstCount} 尾帧:${lastCount})`;
                    }
                });
            });

            // 首尾帧模式切换
            firstLastFrameCheck.addEventListener('change', () => {
                const modelSelect = document.getElementById('paramModel');
                if (firstLastFrameCheck.checked) {
                    // 启用首尾帧模式时，自动切换到 veo_3_1-fast 模型
                    if (modelSelect) {
                        modelSelect.value = 'veo_3_1-fast';
                        // 显示提示
                        shortDramaStudio.showToast('已切换到首尾帧模式 (veo_3_1-fast)', 'info');
                    }

                    // 为已选中的图片添加帧位置选择按钮
                    modal.querySelectorAll('.portrait-check:checked').forEach(check => {
                        this.updateFramePositionButtons(check.parentElement, modal);
                    });
                } else {
                    // 关闭首尾帧模式时，移除所有帧位置按钮和标记
                    modal.querySelectorAll('.frame-position-buttons').forEach(btn => btn.remove());
                    modal.querySelectorAll('.portrait-check').forEach(check => {
                        check.removeAttribute('data-frame-position');
                    });
                }

                const count = modal.querySelectorAll('.portrait-check:checked').length;
                if (firstLastFrameCheck.checked && count < 1) {
                    selectedCountEl.textContent = count + ' (首尾帧至少需要1张)';
                } else {
                    selectedCountEl.textContent = count;
                }
            });

            // 本地图片上传功能
            const addLocalImageBtn = document.getElementById('addLocalImageBtn');
            const localImageInput = document.getElementById('localImageInput');
            const portraitSelector = document.getElementById('portraitSelector');

            if (addLocalImageBtn && localImageInput) {
                addLocalImageBtn.onclick = () => {
                    localImageInput.click();
                };

                localImageInput.onchange = async (e) => {
                    const files = Array.from(e.target.files);
                    if (files.length === 0) return;

                    // 移除"暂无图片"提示
                    const emptyMsg = portraitSelector.querySelector('div[color="var(--text-tertiary)"]');
                    if (emptyMsg) emptyMsg.remove();

                    for (let idx = 0; idx < files.length; idx++) {
                        const file = files[idx];
                        const fileName = file.name.replace(/\.[^/.]+$/, ''); // 移除扩展名
                        const uniqueId = 'local_' + Date.now() + '_' + idx;

                        // 上传图片到服务器
                        let imageUrl = '';
                        try {
                            const formData = new FormData();
                            formData.append('image', file);
                            formData.append('novel_title', this.selectedNovel || '');
                            formData.append('episode_title', this.getEpisodeDirectoryName() || '');

                            const response = await fetch('/api/video/reference-image/upload', {
                                method: 'POST',
                                body: formData
                            });

                            if (!response.ok) {
                                throw new Error(`上传失败: ${response.status}`);
                            }

                            const result = await response.json();
                            imageUrl = result.url;
                        } catch (error) {
                            console.error('上传图片失败:', error);
                            // 降级到本地预览
                            const reader = new FileReader();
                            imageUrl = await new Promise((resolve) => {
                                reader.onload = (event) => resolve(event.target.result);
                                reader.readAsDataURL(file);
                            });
                        }

                        // 创建本地图片的复选框元素
                        const localImageLabel = document.createElement('label');
                        localImageLabel.className = 'portrait-checkbox';
                        localImageLabel.style.cssText = `
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            cursor: pointer;
                            position: relative;
                            transition: transform 0.2s;
                        `;
                        localImageLabel.onmouseover = () => localImageLabel.style.transform = 'scale(1.05)';
                        localImageLabel.onmouseout = () => localImageLabel.style.transform = 'scale(1)';

                        localImageLabel.innerHTML = `
                            <input type="checkbox" class="portrait-check" data-name="本地图片_${fileName}" data-url="${imageUrl}" data-type="local" data-blob="false"
                                style="position: absolute; opacity: 0; width: 0; height: 0;">
                            <div class="portrait-thumb" style="
                                width: 80px;
                                height: 80px;
                                border-radius: 12px;
                                overflow: hidden;
                                border: 3px solid var(--accent-color, #9c27b0);
                                transition: all 0.2s;
                                background: var(--bg-tertiary);
                                position: relative;
                            ">
                                <img src="${imageUrl}" style="width: 100%; height: 100%; object-fit: cover;">
                                <span style="
                                    position: absolute;
                                    bottom: 0;
                                    left: 0;
                                    right: 0;
                                    background: rgba(0,0,0,0.6);
                                    color: white;
                                    font-size: 0.65rem;
                                    padding: 2px;
                                    text-align: center;
                                ">本地</span>
                            </div>
                            <span style="font-size: 0.8rem; margin-top: 8px; max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary);">${fileName.substring(0, 8)}</span>
                            <button class="remove-local-img" data-id="${uniqueId}" style="
                                position: absolute;
                                top: -6px;
                                left: -6px;
                                width: 20px;
                                height: 20px;
                                background: var(--danger);
                                border: none;
                                border-radius: 50%;
                                color: white;
                                font-size: 12px;
                                cursor: pointer;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                padding: 0;
                                z-index: 10;
                            ">×</button>
                            <div class="check-indicator" style="
                                position: absolute;
                                top: 6px;
                                right: 6px;
                                width: 24px;
                                height: 24px;
                                background: rgba(0,0,0,0.6);
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 12px;
                                color: white;
                            ">✓</div>
                        `;

                        // 绑定复选框事件
                        const checkbox = localImageLabel.querySelector('.portrait-check');
                        checkbox.addEventListener('change', () => {
                            const thumb = localImageLabel.querySelector('.portrait-thumb');
                            const indicator = localImageLabel.querySelector('.check-indicator');
                            const count = modal.querySelectorAll('.portrait-check:checked').length;

                            selectedCountEl.textContent = count;

                            if (checkbox.checked) {
                                thumb.style.borderColor = 'var(--primary)';
                                thumb.style.boxShadow = '0 0 0 3px var(--primary-light)';
                                indicator.textContent = '✓';
                                indicator.style.background = 'var(--primary)';
                            } else {
                                thumb.style.borderColor = 'var(--accent-color, #9c27b0)';
                                thumb.style.boxShadow = 'none';
                                indicator.textContent = '';
                                indicator.style.background = 'rgba(0,0,0,0.6)';
                            }

                            if (firstLastFrameCheck.checked && count < 1) {
                                selectedCountEl.textContent = count + ' (首尾帧至少需要1张)';
                            }
                        });

                        // 绑定删除按钮事件
                        const removeBtn = localImageLabel.querySelector('.remove-local-img');
                        removeBtn.onclick = (e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            if (checkbox.checked) {
                                // 更新计数
                                const count = modal.querySelectorAll('.portrait-check:checked').length - 1;
                                selectedCountEl.textContent = count;
                            }
                            localImageLabel.remove();
                        };

                        portraitSelector.appendChild(localImageLabel);

                        // 🔥 本地图片默认选中
                        checkbox.checked = true;
                        // 手动触发选中视觉效果
                        const thumb = localImageLabel.querySelector('.portrait-thumb');
                        const indicator = localImageLabel.querySelector('.check-indicator');
                        thumb.style.borderColor = 'var(--primary)';
                        thumb.style.boxShadow = '0 0 0 3px var(--primary-light)';
                        indicator.textContent = '✓';
                        indicator.style.background = 'var(--primary)';
                        // 更新计数
                        const newCount = modal.querySelectorAll('.portrait-check:checked').length;
                        selectedCountEl.textContent = newCount;
                    }

                    // 清空input，允许重复选择同一文件
                    localImageInput.value = '';
                };
            }

            // 关闭按钮
            closeBtn.onclick = () => {
                modal.remove();
                resolve({ action: 'cancel' });
            };

            // 取消按钮 - 全部取消批量生成
            cancelBtn.onclick = () => {
                modal.remove();
                resolve({ action: 'cancelAll' });
            };

            // 跳过按钮
            skipBtn.onclick = () => {
                modal.remove();
                resolve({ action: 'skip' });
            };

            // 翻译按钮（TODO: 实现翻译功能）
            if (translateToEnBtn) {
                translateToEnBtn.onclick = () => {
                    this.showToast('翻译功能开发中...', 'info');
                };
            }
            if (translateToCnBtn) {
                translateToCnBtn.onclick = () => {
                    this.showToast('翻译功能开发中...', 'info');
                };
            }

            // 生成按钮
            generateBtn.onclick = () => {
                const editedPromptCN = promptAreaCN.value;
                const editedPromptEN = promptAreaEN.value;
                const model = document.getElementById('paramModel').value;
                const orientation = document.getElementById('paramOrientation').value;
                const size = document.getElementById('paramSize').value;
                const useFirstLastFrame = document.getElementById('paramFirstLastFrame').checked;

                // 🔥 收集选中的图片，首尾帧模式需要按顺序
                let checkedImages = [];
                if (useFirstLastFrame) {
                    // 首尾帧模式：按首帧、尾帧顺序收集
                    const firstFrames = Array.from(modal.querySelectorAll('.portrait-check[data-frame-position="first"]:checked'))
                        .map(check => check.dataset.url);
                    const lastFrames = Array.from(modal.querySelectorAll('.portrait-check[data-frame-position="last"]:checked'))
                        .map(check => check.dataset.url);

                    // 首帧在前，尾帧在后
                    checkedImages = [...firstFrames, ...lastFrames];

                    console.log('首尾帧模式图片顺序:');
                    console.log('  - 首帧数量:', firstFrames.length);
                    console.log('  - 尾帧数量:', lastFrames.length);
                    console.log('  - 传输顺序:', checkedImages);

                    // 验证：首尾帧模式至少需要1张图片
                    if (checkedImages.length < 1) {
                        this.showToast('首尾帧模式至少需要选择1张图片并标注为首帧或尾帧', 'warning');
                        return;
                    }
                } else {
                    // 普通模式：直接收集所有选中的图片
                    checkedImages = Array.from(modal.querySelectorAll('.portrait-check:checked'))
                        .map(check => check.dataset.url);
                }

                console.log('📝 提示词调试信息:');
                console.log('  - shotKey:', shotKey);
                console.log('  - shot.episode_title:', shot.episode_title);
                console.log('  - shot.shot_number:', shot.shot_number);
                console.log('  - 原始中文描述:', currentPromptCN);
                console.log('  - 原始英文提示词:', currentPromptEN);
                console.log('  - 编辑后的中文:', editedPromptCN);
                console.log('  - 编辑后的英文:', editedPromptEN);
                console.log('选中的图片数量:', checkedImages.length);
                console.log('首尾帧模式:', useFirstLastFrame);

                // 保存修改的提示词
                if (editedPromptCN !== currentPromptCN) {
                    localStorage.setItem(shotKey + '_cn', editedPromptCN);
                    console.log('已保存修改的中文描述');
                }
                if (editedPromptEN !== currentPromptEN) {
                    localStorage.setItem(shotKey + '_en', editedPromptEN);
                    console.log('已保存修改的英文提示词');
                }

                modal.remove();
                resolve({
                    action: 'generate',
                    prompt: editedPromptEN,  // 🔥 使用英文提示词发送给AI
                    promptCN: editedPromptCN,  // 保存中文描述用于显示
                    selectedImages: checkedImages,
                    model,
                    orientation,
                    size,
                    useFirstLastFrame
                });
            };

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.remove();
                    resolve({ action: 'cancel' });
                }
            });
        });
    }

    /**
     * 更新帧位置选择按钮（首尾帧模式）
     */
    updateFramePositionButtons(imageLabel, modal) {
        // 移除已存在的按钮
        const existingButtons = imageLabel.querySelector('.frame-position-buttons');
        if (existingButtons) existingButtons.remove();

        // 创建帧位置选择按钮容器
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'frame-position-buttons';
        buttonContainer.style.cssText = `
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 4px;
            z-index: 10;
        `;

        const checkbox = imageLabel.querySelector('.portrait-check');
        const currentPosition = checkbox.getAttribute('data-frame-position');

        // 首帧按钮
        const firstBtn = document.createElement('button');
        firstBtn.textContent = '首';
        firstBtn.style.cssText = `
            padding: 4px 8px;
            font-size: 0.75rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            background: ${currentPosition === 'first' ? 'var(--success)' : 'var(--bg-tertiary)'};
            color: white;
            font-weight: ${currentPosition === 'first' ? 'bold' : 'normal'};
        `;
        firstBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            checkbox.setAttribute('data-frame-position', 'first');
            this.updateFramePositionButtons(imageLabel, modal);
            this.updateFrameCountDisplay(modal);
        };

        // 尾帧按钮
        const lastBtn = document.createElement('button');
        lastBtn.textContent = '尾';
        lastBtn.style.cssText = `
            padding: 4px 8px;
            font-size: 0.75rem;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            background: ${currentPosition === 'last' ? 'var(--danger)' : 'var(--bg-tertiary)'};
            color: white;
            font-weight: ${currentPosition === 'last' ? 'bold' : 'normal'};
        `;
        lastBtn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            checkbox.setAttribute('data-frame-position', 'last');
            this.updateFramePositionButtons(imageLabel, modal);
            this.updateFrameCountDisplay(modal);
        };

        buttonContainer.appendChild(firstBtn);
        buttonContainer.appendChild(lastBtn);
        imageLabel.appendChild(buttonContainer);
    }

    /**
     * 更新帧数量显示
     */
    updateFrameCountDisplay(modal) {
        const selectedCountEl = document.getElementById('selectedCount');
        if (!selectedCountEl) return;

        const firstCount = modal.querySelectorAll('.portrait-check[data-frame-position="first"]:checked').length;
        const lastCount = modal.querySelectorAll('.portrait-check[data-frame-position="last"]:checked').length;
        const totalCount = modal.querySelectorAll('.portrait-check:checked').length;

        selectedCountEl.textContent = totalCount + ` (首帧:${firstCount} 尾帧:${lastCount})`;
    }

    /**
     * 从确认弹窗开始生成
     */
    async generateFromConfirm(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const result = await this.showGenerateConfirmModal(shot, idx);

        if (result.action === 'cancelAll') {
            this.showToast('已取消批量生成', 'info');
            throw new Error('cancelAll');
        }
        if (result.action !== 'generate') return;

        // 🔥 如果视频已存在，先备份
        if (shot.videoExists && (shot.videoPath || shot.videoUrl)) {
            try {
                const episodeDirectoryName = this.getEpisodeDirectoryName();
                const backupResponse = await fetch('/api/short-drama/backup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        file_type: 'video',
                        shot_number: shot.shot_number || shot.scene_number || (idx + 1),
                        file_path: shot.videoPath
                    })
                });
                const backupResult = await backupResponse.json();
                if (backupResult.success) {
                    this.showToast('原视频已备份，可随时还原', 'success');
                } else {
                    console.warn('视频备份失败:', backupResult.error);
                }
            } catch (e) {
                console.error('备份视频失败:', e);
            }
        }

        // 🔥 质量检查已禁用 - 直接生成视频，不再调用质量检查API
        // 如果需要质量检查，用户可以手动点击"剧本质量检查"按钮

        // 保存选中的参考图到镜头数据
        shot.reference_images = result.selectedImages || [];

        // 🔥 保存用户编辑的提示词到shot对象
        // result.prompt 是用户在弹窗中编辑的提示词（可能包含标签格式）
        if (result.prompt && result.prompt.trim()) {
            shot.veo_prompt = result.prompt.trim();
            console.log('✏️ [提示词更新] 已保存用户编辑的提示词到shot对象');
        }

        // 开始生成，显示进度弹窗
        this.showVideoProgressModal(shot, idx);

        shot.generating = true;
        shot.hasError = false;
        this.updateVideoCard(idx);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            // 🔥 使用当前模式的提示词（支持数据流A的多模式）
            const promptForApi = shot.veo_prompt || this.getCurrentVeoPrompt(shot) || shot.screen_action || '';
            const selectedMode = shot.preferred_mode || 'standard';

            // 🔥 打印发送给API的实际提示词，方便排查
            console.log('📤 [发送给VeO API的提示词]');
            console.log('  - 镜头: S' + (shot._scene_number || shot.scene_number || 1) + '#' + (shot.shot_number || (idx + 1)));
            console.log('  - 模式:', selectedMode);
            console.log('  - 提示词长度:', promptForApi.length, '字符');
            console.log('  - 提示词内容:\n' + promptForApi);

            // 获取对话数据中的英文台词
            const dialogueData = shot._dialogue_data || shot.dialogue;

            // 🔥 根据是否有参考图选择模型
            const selectedImages = result.selectedImages || [];
            const finalModel = selectedImages.length > 0
                ? (result.model || 'veo_3_1-fast-components')  // 有参考图：使用用户选择的模型
                : 'veo_3_1-fast';  // 无参考图：强制使用 veo_3_1-fast
            console.log('  - 模型:', finalModel, selectedImages.length > 0 ? '(参考图模式)' : '(无参考图模式)');

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: finalModel,
                    prompt: promptForApi,  // 🔥 使用当前模式的 veo_prompt
                    image_urls: selectedImages,
                    orientation: result.orientation || 'portrait',
                    size: result.size || 'large',
                    watermark: false,
                    private: true,
                    // 🔥 添加模式信息和图片提示词（数据流A）
                    mode: selectedMode,
                    image_prompts: shot.image_prompts || {},
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        scene_number: shot._scene_number || shot.scene_number || 1,
                        shot_number: String(shot.shot_number || (idx + 1)),
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        lines_en: dialogueData?.lines_en || '',  // 传递英文台词
                        mode: selectedMode  // 🔥 在metadata中也记录模式
                    }
                })
            });

            const data = await response.json();

            if (data.id) {
                await this.pollVideoStatus(data.id, idx);
            } else {
                throw new Error(data.error?.message || '生成失败');
            }
        } catch (error) {
            console.error('生成视频失败:', error);
            shot.generating = false;
            shot.hasError = true;
            shot.errorMessage = error.message || '生成失败';
            this.updateVideoCard(idx);
            this.closeVideoProgressModal(idx);

            if (error.message !== 'cancelAll' && error.message !== 'skip') {
                this.showToast('生成失败: ' + error.message, 'error');
            }
            throw error;
        }
    }

    /**
     * 批量生成前5个视频（带确认）
     */
    async batchGenerateFirstFive() {
        const pendingShots = this.shots
            .map((shot, idx) => ({ shot, idx }))
            .filter(({ shot }) => !shot.videoExists && !shot.generating)
            .slice(0, 5);

        if (pendingShots.length === 0) {
            this.showToast('没有待生成的视频', 'info');
            return;
        }

        for (const { shot, idx } of pendingShots) {
            try {
                await this.generateFromConfirm(idx);
            } catch (e) {
                if (e.message === 'cancelAll') {
                    return; // 全部取消
                }
                // 跳过或其他错误，继续下一个
            }
        }

        this.showToast(`批量生成完成！`, 'success');
    }

    /**
     * 生成单个镜头视频（兼容旧接口）
     */
    async generateShotVideo(shotIndex) {
        await this.generateFromConfirm(shotIndex);
    }

    /**
     * 预览视频（已完成的视频）
     */
    previewVideo(idx) {
        const shot = this.shots[idx];
        if (!shot || !shot.videoUrl) {
            this.showToast('视频不存在', 'error');
            return;
        }

        // 创建预览弹窗
        const modal = document.createElement('div');
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

        modal.innerHTML = `
            <div style="
                background: var(--bg-secondary);
                border-radius: 16px;
                width: 90%;
                max-width: 600px;
                padding: 24px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">🎬 镜头 #${shot.shot_number || (idx + 1)}</h3>
                    <button onclick="this.closest('.video-preview-modal')?.remove()" style="
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                        color: var(--text-secondary);
                    ">×</button>
                </div>
                <div style="
                    background: var(--bg-dark);
                    border-radius: 12px;
                    overflow: hidden;
                    aspect-ratio: 9/16;
                    margin-bottom: 16px;
                ">
                    <video src="${shot.videoUrl}" controls autoplay loop style="width: 100%; height: 100%;"></video>
                </div>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button onclick="shortDramaStudio.downloadVideo('${shot.videoUrl}')" style="
                        padding: 12px 24px;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border);
                        border-radius: 8px;
                        cursor: pointer;
                    ">📥 下载</button>
                    <button onclick="this.closest('.video-preview-modal')?.remove(); shortDramaStudio.regenerateVideo(${idx});" style="
                        padding: 12px 24px;
                        background: var(--warning);
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                    ">🔄 重新生成</button>
                    <button onclick="this.closest('.video-preview-modal')?.remove()" style="
                        padding: 12px 24px;
                        background: var(--primary);
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                    ">关闭</button>
                </div>
            </div>
        `;

        modal.className = 'video-preview-modal';
        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    /**
     * 预览配音（已完成的配音）
     */
    previewAudio(idx) {
        const shot = this.shots[idx];
        if (!shot || !shot.audioUrl) {
            this.showToast('配音不存在', 'error');
            return;
        }

        const dialogue = shot._dialogue_data || shot.dialogue || {};
        const { speaker, lines, tone } = this.parseDialogue(dialogue);

        // 创建预览弹窗
        const modal = document.createElement('div');
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

        modal.innerHTML = `
            <div style="
                background: var(--bg-secondary);
                border-radius: 16px;
                width: 90%;
                max-width: 500px;
                padding: 24px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">🎙️ 配音预览 #${shot.shot_number || (idx + 1)}</h3>
                    <button onclick="this.closest('.audio-preview-modal')?.remove()" style="
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                        color: var(--text-secondary);
                    ">×</button>
                </div>
                <div style="
                    background: var(--bg-dark);
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 16px;
                ">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                        <span style="background: var(--primary); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">${speaker || '未知'}</span>
                        ${tone ? `<span style="color: var(--text-tertiary); font-size: 0.85rem;">🎭 ${tone}</span>` : ''}
                    </div>
                    <div style="color: var(--text-secondary); font-style: italic; margin-bottom: 16px;">
                        "${lines || ''}"
                    </div>
                    <audio src="${shot.audioUrl}" controls autoplay style="width: 100%;"></audio>
                </div>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button onclick="shortDramaStudio.downloadAudio('${shot.audioUrl}', '${speaker || 'audio'}_${shot.shot_number || idx}')" style="
                        padding: 12px 24px;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border);
                        border-radius: 8px;
                        cursor: pointer;
                    ">📥 下载</button>
                    <button onclick="this.closest('.audio-preview-modal')?.remove(); shortDramaStudio.editDubbing(${idx});" style="
                        padding: 12px 24px;
                        background: var(--primary);
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                    ">✏️ 编辑台词</button>
                    <button onclick="this.closest('.audio-preview-modal')?.remove()" style="
                        padding: 12px 24px;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border);
                        border-radius: 8px;
                        cursor: pointer;
                    ">关闭</button>
                </div>
            </div>
        `;

        modal.className = 'audio-preview-modal';
        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }

    /**
     * 重新生成视频
     */
    async regenerateVideo(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        // 检查是否有已存在的视频
        if (shot.videoPath || shot.videoUrl) {
            // 备份原视频
            try {
                const episodeDirectoryName = this.getEpisodeDirectoryName();
                const backupResponse = await fetch('/api/short-drama/backup', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        file_type: 'video',
                        shot_number: shot.shot_number || shot.scene_number || (idx + 1),
                        file_path: shot.videoPath
                    })
                });
                const backupResult = await backupResponse.json();
                if (backupResult.success) {
                    this.showToast('原视频已备份，可随时还原', 'success');
                } else {
                    this.showToast(`备份失败: ${backupResult.error}`, 'warning');
                }
            } catch (e) {
                console.error('备份视频失败:', e);
            }
        }

        shot.videoExists = false;
        shot.videoUrl = null;
        shot.videoPath = null;
        await this.generateFromConfirm(idx);
    }

    /**
     * 显示中英文提示词对照编辑弹窗
     */
    showBilingualPromptModal(idx) {
        console.log(`🖊️ [EN弹窗] 点击索引: ${idx}, shots数量: ${this.shots?.length || 0}`);
        const shot = this.shots[idx];
        if (!shot) {
            console.error(`❌ [EN弹窗] 找不到镜头: idx=${idx}, shots=${this.shots?.length}`);
            this.showToast('找不到镜头数据', 'error');
            return;
        }

        const mode = shot.preferred_mode || 'standard';
        const modeNames = {
            'standard': '标准模式',
            'reference': '参考图模式',
            'frames': '首尾帧模式'
        };

        // 获取当前模式的中英文提示词
        let veoPrompt, visualDesc;
        if (mode === 'reference') {
            veoPrompt = shot.veo_prompt_reference || shot.veo_prompt || '';
            visualDesc = shot.visual_description_reference || shot.visual_description || '';
        } else if (mode === 'frames') {
            veoPrompt = shot.veo_prompt_frames || shot.veo_prompt || '';
            visualDesc = shot.visual_description_frames || shot.visual_description || '';
        } else {
            veoPrompt = shot.veo_prompt_standard || shot.veo_prompt || '';
            visualDesc = shot.visual_description_standard || shot.visual_description || '';
        }

        // 创建弹窗
        const modal = document.createElement('div');
        modal.id = 'bilingualPromptModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-secondary, #1e1e2e);
                border-radius: 12px;
                width: 90%;
                max-width: 900px;
                max-height: 85vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            ">
                <!-- 头部 -->
                <div style="
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--border, #333);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <h3 style="margin: 0; color: #fff; font-size: 1.1rem;">编辑提示词 - S${shot.scene_number || 1}#${shot.shot_number || idx+1}</h3>
                        <span style="color: #6366f1; font-size: 0.85rem;">${modeNames[mode]}</span>
                    </div>
                    <button onclick="document.getElementById('bilingualPromptModal').remove()" style="
                        background: none;
                        border: none;
                        color: #888;
                        font-size: 1.5rem;
                        cursor: pointer;
                    ">×</button>
                </div>

                <!-- 内容区 -->
                <div style="padding: 20px; overflow-y: auto; flex: 1;">
                    <!-- 中文视觉描述 -->
                    <div style="margin-bottom: 20px;">
                        <label style="
                            display: block;
                            color: #10b981;
                            font-size: 0.85rem;
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">🇨🇳 中文视觉描述 (Visual Description)</label>
                        <textarea id="bilingual-visual-desc" style="
                            width: 100%;
                            min-height: 80px;
                            padding: 12px;
                            background: var(--bg-dark, #0f0f1a);
                            border: 1px solid var(--border, #333);
                            border-radius: 8px;
                            color: #fff;
                            font-size: 0.9rem;
                            line-height: 1.5;
                            resize: vertical;
                        " placeholder="中文画面描述...">${visualDesc}</textarea>
                        <div style="color: #888; font-size: 0.75rem; margin-top: 4px;">用于前端显示，帮助理解画面内容</div>
                    </div>

                    <!-- 英文VEO提示词 -->
                    <div style="margin-bottom: 20px;">
                        <label style="
                            display: block;
                            color: #6366f1;
                            font-size: 0.85rem;
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">🇺🇸 英文VEO提示词 (Video Prompt)</label>
                        <textarea id="bilingual-veo-prompt" style="
                            width: 100%;
                            min-height: 120px;
                            padding: 12px;
                            background: var(--bg-dark, #0f0f1a);
                            border: 1px solid var(--border, #333);
                            border-radius: 8px;
                            color: #fff;
                            font-size: 0.9rem;
                            line-height: 1.5;
                            resize: vertical;
                            font-family: monospace;
                        " placeholder="英文视频生成提示词...">${veoPrompt}</textarea>
                        <div style="color: #888; font-size: 0.75rem; margin-top: 4px;">发送给VEO/AI视频生成模型的提示词</div>
                    </div>

                    <!-- 其他信息 -->
                    <div style="
                        background: rgba(99, 102, 241, 0.1);
                        padding: 12px;
                        border-radius: 8px;
                        font-size: 0.8rem;
                        color: #888;
                    ">
                        <div style="margin-bottom: 4px;"><strong>镜头类型:</strong> ${shot.shot_type || 'N/A'}</div>
                        <div style="margin-bottom: 4px;"><strong>时长:</strong> ${shot.duration || 5}秒</div>
                        ${shot.scene_title ? `<div><strong>场景:</strong> ${shot.scene_title}</div>` : ''}
                    </div>
                </div>

                <!-- 底部按钮 -->
                <div style="
                    padding: 16px 20px;
                    border-top: 1px solid var(--border, #333);
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                ">
                    <button onclick="document.getElementById('bilingualPromptModal').remove()" style="
                        padding: 10px 20px;
                        background: transparent;
                        border: 1px solid var(--border, #333);
                        border-radius: 8px;
                        color: #888;
                        cursor: pointer;
                        font-size: 0.9rem;
                    ">取消</button>
                    <button onclick="shortDramaStudio.saveBilingualPrompt(${idx})" style="
                        padding: 10px 24px;
                        background: linear-gradient(135deg, #6366f1, #8b5cf6);
                        border: none;
                        border-radius: 8px;
                        color: #fff;
                        cursor: pointer;
                        font-size: 0.9rem;
                        font-weight: 600;
                    ">保存</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    /**
     * 保存中英文提示词
     */
    saveBilingualPrompt(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const visualDesc = document.getElementById('bilingual-visual-desc').value.trim();
        const veoPrompt = document.getElementById('bilingual-veo-prompt').value.trim();

        if (!visualDesc && !veoPrompt) {
            this.showToast('提示词不能为空', 'warning');
            return;
        }

        const mode = shot.preferred_mode || 'standard';

        // 根据当前模式保存到对应的字段
        if (mode === 'reference') {
            shot.visual_description_reference = visualDesc;
            shot.veo_prompt_reference = veoPrompt;
        } else if (mode === 'frames') {
            shot.visual_description_frames = visualDesc;
            shot.veo_prompt_frames = veoPrompt;
        } else {
            shot.visual_description_standard = visualDesc;
            shot.veo_prompt_standard = veoPrompt;
        }

        // 同时更新兼容字段
        shot.visual_description = visualDesc;
        shot.veo_prompt = veoPrompt;

        // 关闭弹窗
        const modal = document.getElementById('bilingualPromptModal');
        if (modal) modal.remove();

        // 刷新显示
        this.updateVideoCard(idx);
        this.showToast('提示词已更新', 'success');
    }

    /**
     * 通过 shotId 打开多图生成弹窗
     * @param {string} shotId - 镜头ID (格式: shot_sceneNum_idx)
     */
    openMultiImageModalByShotId(shotId) {
        // 优先使用 this.currentProject.shots（renderShotsList 使用的数据源）
        const shots = this.currentProject?.shots || this.shots || [];
        
        if (!shots || shots.length === 0) {
            this.showToast('没有可用的镜头数据', 'error');
            return;
        }
        
        // 从 shotId 提取索引信息
        // shotId 格式: shot_${sceneNum}_${idx} 或 shot_1_2
        let idx = -1;
        
        // 尝试从 shots 中查找匹配的 shot
        idx = shots.findIndex(s => s.id === shotId || s.shot_id === shotId);
        
        // 如果没找到，尝试解析 shotId 提取索引
        if (idx === -1 && shotId.startsWith('shot_')) {
            const parts = shotId.split('_');
            if (parts.length >= 3) {
                const sceneNum = parseInt(parts[1]);
                const shotIdx = parseInt(parts[2]);
                // 计算全局索引
                idx = shots.findIndex(s => 
                    (s._scene_number || s.scene_number) == sceneNum && 
                    (s.shot_number == (shotIdx + 1) || s.idx == shotIdx)
                );
            }
        }
        
        // 如果还是没找到，尝试通过 scene_number 和 shot_number 查找
        if (idx === -1 && shotId.startsWith('shot_')) {
            const parts = shotId.split('_');
            if (parts.length >= 3) {
                const sceneNum = parseInt(parts[1]);
                const shotNum = parseInt(parts[2]) + 1; // idx 是从 0 开始的，shot_number 是从 1 开始的
                idx = shots.findIndex(s => 
                    (s.scene_number || s._scene_number) == sceneNum && 
                    s.shot_number == shotNum
                );
            }
        }
        
        if (idx === -1) {
            this.showToast('未找到对应的镜头: ' + shotId, 'error');
            return;
        }
        
        // 将找到的镜头设置到 this.shots 中，以便 openMultiImageModal 使用
        this.shots = shots;
        this.openMultiImageModal(idx);
    }

    /**
     * 打开多图生成弹窗
     */
    openMultiImageModal(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        // 获取当前提示词
        const promptText = shot.veo_prompt || shot.screen_action || '';
        
        // 创建弹窗
        const modal = document.createElement('div');
        modal.id = 'multiImageModal';
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
            padding: 20px;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--surface, #1e293b);
                border-radius: 12px;
                max-width: 900px;
                width: 100%;
                max-height: 90vh;
                overflow-y: auto;
                padding: 24px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0; color: var(--text-primary, #f1f5f9);">🎨 生成多图 - 镜头 ${shot.shot_number || idx + 1}</h3>
                    <button onclick="document.getElementById('multiImageModal').remove()" style="
                        background: none;
                        border: none;
                        color: var(--text-secondary, #94a3b8);
                        font-size: 24px;
                        cursor: pointer;
                    ">×</button>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94a3b8);">提示词</label>
                    <textarea id="multiImagePrompt" style="
                        width: 100%;
                        min-height: 80px;
                        padding: 12px;
                        background: var(--surface-light, #334155);
                        border: 1px solid var(--border, #475569);
                        border-radius: 8px;
                        color: var(--text-primary, #f1f5f9);
                        resize: vertical;
                    ">${promptText}</textarea>
                </div>
                
                <div style="display: flex; gap: 16px; margin-bottom: 20px;">
                    <div style="flex: 1;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94a3b8);">图片数量</label>
                        <select id="multiImageCount" style="
                            width: 100%;
                            padding: 10px;
                            background: var(--surface-light, #334155);
                            border: 1px solid var(--border, #475569);
                            border-radius: 8px;
                            color: var(--text-primary, #f1f5f9);
                        ">
                            <option value="3">3宫格 (3张)</option>
                            <option value="6">6宫格 (6张)</option>
                            <option value="9">9宫格 (9张)</option>
                        </select>
                    </div>
                    <div style="flex: 1;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94a3b8);">图片比例</label>
                        <select id="multiImageRatio" style="
                            width: 100%;
                            padding: 10px;
                            background: var(--surface-light, #334155);
                            border: 1px solid var(--border, #475569);
                            border-radius: 8px;
                            color: var(--text-primary, #f1f5f9);
                        ">
                            <option value="1:1" selected>1:1 (方形)</option>
                            <option value="16:9">16:9 (宽屏)</option>
                            <option value="9:16">9:16 (竖屏)</option>
                        </select>
                    </div>
                    <div style="flex: 1;">
                        <label style="display: block; margin-bottom: 8px; color: var(--text-secondary, #94a3b8);">画质</label>
                        <select id="multiImageQuality" style="
                            width: 100%;
                            padding: 10px;
                            background: var(--surface-light, #334155);
                            border: 1px solid var(--border, #475569);
                            border-radius: 8px;
                            color: var(--text-primary, #f1f5f9);
                        ">
                            <option value="2K">2K</option>
                            <option value="4K" selected>4K</option>
                        </select>
                    </div>
                </div>
                
                <div style="display: flex; gap: 12px; justify-content: flex-end;">
                    <button onclick="document.getElementById('multiImageModal').remove()" style="
                        padding: 10px 20px;
                        background: var(--surface-light, #334155);
                        border: 1px solid var(--border, #475569);
                        border-radius: 8px;
                        color: var(--text-primary, #f1f5f9);
                        cursor: pointer;
                    ">取消</button>
                    <button onclick="shortDramaStudio.generateMultiImages(${idx})" style="
                        padding: 10px 24px;
                        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                        border: none;
                        border-radius: 8px;
                        color: white;
                        font-weight: 500;
                        cursor: pointer;
                    ">🎨 开始生成</button>
                </div>
                
                <div id="multiImageResults" style="margin-top: 24px; display: none;">
                    <h4 style="color: var(--text-primary, #f1f5f9); margin-bottom: 16px;">生成结果</h4>
                    <div id="multiImageGrid" style="
                        display: grid;
                        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                        gap: 16px;
                    "></div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        
        // 如果已有生成的图片，显示它们
        if (shot.generatedImages && shot.generatedImages.length > 0) {
            this.displayMultiImageResults(shot.generatedImages);
        }
    }

    /**
     * 生成多图 - 🔥 使用九宫格大图生成后分割
     */
    async generateMultiImages(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const prompt = document.getElementById('multiImagePrompt').value;
        const count = parseInt(document.getElementById('multiImageCount').value);
        const ratio = document.getElementById('multiImageRatio').value;
        const quality = document.getElementById('multiImageQuality').value;

        if (!prompt.trim()) {
            this.showToast('请输入提示词', 'warning');
            return;
        }

        // 🔥 确定网格布局
        let gridLayout;
        switch (count) {
            case 3: gridLayout = '1x3'; break;
            case 6: gridLayout = '2x3'; break;
            case 9: gridLayout = '3x3'; break;
            default: gridLayout = '1x3';
        }

        // 🔥 构建 frames 数组（同一镜头的不同变体描述）
        const frames = [];
        for (let i = 1; i <= count; i++) {
            frames.push({
                frame_number: i,
                prompt: `${prompt}, variation ${i}, different angle and lighting`
            });
        }

        // 显示生成中状态
        const resultsDiv = document.getElementById('multiImageResults');
        const gridDiv = document.getElementById('multiImageGrid');
        resultsDiv.style.display = 'block';
        gridDiv.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                <div class="spinner" style="width: 40px; height: 40px; border: 3px solid rgba(99, 102, 241, 0.3); border-top-color: #6366f1; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 16px;"></div>
                <p style="color: var(--text-secondary, #94a3b8);">正在生成 ${count} 宫格大图并分割...</p>
            </div>
        `;

        try {
            // 🔥 获取项目信息
            const projectId = this.currentProject?.id || this.projectId;
            const episodeName = this.getEpisodeDirectoryName?.() || this.currentEpisode || '1集_创意导入';
            const shotId = `shot_${shot.shot_number || idx + 1}`;

            // 🔥 调用九宫格生成API
            const response = await fetch('/api/short-drama/storyboard/generate-frame-grid', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: projectId,
                    episode_name: episodeName,
                    shot_id: shotId,
                    grid_layout: gridLayout,
                    frame_count: count,
                    frames: frames,
                    aspect_ratio: ratio,
                    image_size: quality
                })
            });

            const result = await response.json();

            if (result.success && result.frame_images) {
                // 🔥 保存生成的图片到shot（分割后的小图）
                shot.generatedImages = result.frame_images.map((frame, i) => ({
                    url: frame.url,
                    path: frame.url, // 分割后的图片路径
                    prompt: frames[i].prompt,
                    index: i,
                    grid_image_url: result.grid_image_url // 保留大图URL
                }));
                
                // 显示结果
                this.displayMultiImageResults(shot.generatedImages);
                this.showToast(`✅ 成功生成九宫格并分割为 ${shot.generatedImages.length} 张图片`, 'success');
                
                // 刷新分镜列表以显示指示器
                if (this.currentStoryboards && this.currentStoryboards.length > 0) {
                    this.renderStoryboards(this.currentStoryboards);
                } else if (this.currentStoryboard) {
                    this.renderStoryboard(this.currentStoryboard);
                } else if (this.currentProject?.shots) {
                    this.renderShotsList();
                }
            } else {
                throw new Error(result.message || result.error || '生成失败');
            }
        } catch (error) {
            console.error('生成多图失败:', error);
            gridDiv.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--danger, #ef4444);">
                    <p>❌ 生成失败: ${error.message}</p>
                    <button onclick="shortDramaStudio.generateMultiImages(${idx})" style="margin-top: 16px;" class="btn btn-primary">重试</button>
                </div>
            `;
            this.showToast('生成失败: ' + error.message, 'error');
        }
    }

    /**
     * 显示多图生成结果
     */
    displayMultiImageResults(images) {
        const gridDiv = document.getElementById('multiImageGrid');
        if (!gridDiv) return;

        gridDiv.innerHTML = images.map((img, idx) => `
            <div style="
                background: var(--surface-light, #334155);
                border-radius: 8px;
                overflow: hidden;
                position: relative;
            ">
                <img src="${img.url}" style="width: 100%; height: 200px; object-fit: cover;" 
                    onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';"
                    onclick="window.open('${img.url}', '_blank')"
                >
                <div style="display: none; height: 200px; align-items: center; justify-content: center; color: var(--text-secondary, #94a3b8);">
                    加载失败
                </div>
                <div style="padding: 12px;">
                    <div style="font-size: 0.75rem; color: var(--text-secondary, #94a3b8); margin-bottom: 8px;">
                        图片 ${idx + 1}
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button onclick="window.open('${img.url}', '_blank')" style="
                            flex: 1;
                            padding: 6px 12px;
                            background: var(--primary, #6366f1);
                            border: none;
                            border-radius: 4px;
                            color: white;
                            font-size: 0.75rem;
                            cursor: pointer;
                        ">查看</button>
                        <button onclick="shortDramaStudio.downloadImage('${img.url}')" style="
                            flex: 1;
                            padding: 6px 12px;
                            background: var(--surface, #1e293b);
                            border: 1px solid var(--border, #475569);
                            border-radius: 4px;
                            color: var(--text-primary, #f1f5f9);
                            font-size: 0.75rem;
                            cursor: pointer;
                        ">下载</button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    /**
     * 下载图片
     */
    async downloadImage(url) {
        try {
            const response = await fetch(url);
            const blob = await response.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `image_${Date.now()}.png`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            this.showToast('下载开始', 'success');
        } catch (error) {
            console.error('下载失败:', error);
            this.showToast('下载失败', 'error');
        }
    }

    /**
     * 下载视频
     */
    async downloadVideo(videoUrl) {
        try {
            const response = await fetch(videoUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `video_${Date.now()}.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            this.showToast('下载开始', 'success');
        } catch (error) {
            console.error('下载失败:', error);
            this.showToast('下载失败', 'error');
        }
    }

    /**
     * 显示视频备份还原弹窗
     */
    async showVideoRestoreModal(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const episodeDirectoryName = this.getEpisodeDirectoryName();
        const shotNumber = shot.shot_number || shot.scene_number || (idx + 1);

        try {
            const response = await fetch(`/api/short-drama/backups?novel=${encodeURIComponent(this.selectedNovel || '')}&episode=${encodeURIComponent(episodeDirectoryName)}&file_type=video&shot_number=${shotNumber}`);
            const data = await response.json();

            if (!data.success) {
                this.showToast('获取备份列表失败', 'error');
                return;
            }

            const backups = data.backups || [];

            if (backups.length === 0) {
                this.showToast('没有可用的备份', 'info');
                return;
            }

            // 创建弹窗
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            const formatSize = (bytes) => {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            };

            modal.innerHTML = `
                <div style="
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    max-width: 500px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                    padding: 20px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="margin: 0;">♻️ 视频备份还原</h3>
                        <button onclick="this.closest('.restore-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 16px;">镜头 #${shotNumber} · ${backups.length} 个备份</p>
                    <div class="backup-list" style="display: flex; flex-direction: column; gap: 8px;">
                        ${backups.map((backup, bIdx) => `
                            <div style="
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                padding: 12px;
                                background: var(--bg-dark);
                                border-radius: 8px;
                                border: 1px solid var(--border);
                            ">
                                <div>
                                    <div style="font-size: 0.9rem; margin-bottom: 4px;">📅 ${backup.timestamp}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-tertiary);">${formatSize(backup.size)}</div>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button class="restore-btn" data-path="${backup.path}" style="
                                        padding: 6px 12px;
                                        background: var(--success);
                                        border: none;
                                        border-radius: 6px;
                                        color: white;
                                        cursor: pointer;
                                        font-size: 0.85rem;
                                    ">还原</button>
                                    <button class="delete-backup-btn" data-path="${backup.path}" style="
                                        padding: 6px 12px;
                                        background: var(--bg-tertiary);
                                        border: 1px solid var(--border);
                                        border-radius: 6px;
                                        color: var(--text-secondary);
                                        cursor: pointer;
                                        font-size: 0.85rem;
                                    ">删除</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;

            modal.className = 'restore-modal';
            document.body.appendChild(modal);

            // 绑定还原按钮事件
            modal.querySelectorAll('.restore-btn').forEach(btn => {
                btn.onclick = async () => {
                    const backupPath = btn.dataset.path;
                    const restoreResponse = await fetch('/api/short-drama/restore', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            novel_title: this.selectedNovel || '',
                            episode_title: episodeDirectoryName,
                            backup_path: backupPath,
                            backup_current: true
                        })
                    });
                    const restoreResult = await restoreResponse.json();
                    if (restoreResult.success) {
                        this.showToast('视频已还原', 'success');
                        modal.remove();
                        // 刷新视频状态
                        await this.refreshVideos();
                    } else {
                        this.showToast(`还原失败: ${restoreResult.error}`, 'error');
                    }
                };
            });

            // 绑定删除按钮事件
            modal.querySelectorAll('.delete-backup-btn').forEach(btn => {
                btn.onclick = async () => {
                    if (!confirm('确定要删除此备份吗？')) return;
                    const backupPath = btn.dataset.path;
                    const deleteResponse = await fetch('/api/short-drama/backup/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ backup_path: backupPath })
                    });
                    const deleteResult = await deleteResponse.json();
                    if (deleteResult.success) {
                        this.showToast('备份已删除', 'success');
                        btn.closest('div[style*="flex: justify-content"]').remove();
                        if (modal.querySelectorAll('.backup-list > div').length === 0) {
                            modal.remove();
                        }
                    } else {
                        this.showToast(`删除失败: ${deleteResult.error}`, 'error');
                    }
                };
            });

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.remove();
            });
        } catch (error) {
            console.error('显示备份弹窗失败:', error);
            this.showToast('获取备份列表失败', 'error');
        }
    }

    /**
     * 显示音频备份还原弹窗
     */
    async showAudioRestoreModal(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const episodeDirectoryName = this.getEpisodeDirectoryName();
        const shotNumber = shot.shot_number || shot.scene_number || (idx + 1);

        try {
            const response = await fetch(`/api/short-drama/backups?novel=${encodeURIComponent(this.selectedNovel || '')}&episode=${encodeURIComponent(episodeDirectoryName)}&file_type=audio&shot_number=${shotNumber}`);
            const data = await response.json();

            if (!data.success) {
                this.showToast('获取备份列表失败', 'error');
                return;
            }

            const backups = data.backups || [];

            if (backups.length === 0) {
                this.showToast('没有可用的备份', 'info');
                return;
            }

            // 创建弹窗
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.85);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;

            const formatSize = (bytes) => {
                if (bytes < 1024) return bytes + ' B';
                if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
                return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
            };

            modal.innerHTML = `
                <div style="
                    background: var(--bg-secondary);
                    border-radius: 12px;
                    max-width: 500px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                    padding: 20px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 style="margin: 0;">♻️ 音频备份还原</h3>
                        <button onclick="this.closest('.audio-restore-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">×</button>
                    </div>
                    <p style="color: var(--text-secondary); margin-bottom: 16px;">镜头 #${shotNumber} · ${backups.length} 个备份</p>
                    <div class="backup-list" style="display: flex; flex-direction: column; gap: 8px;">
                        ${backups.map((backup) => `
                            <div style="
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                                padding: 12px;
                                background: var(--bg-dark);
                                border-radius: 8px;
                                border: 1px solid var(--border);
                            ">
                                <div>
                                    <div style="font-size: 0.9rem; margin-bottom: 4px;">📅 ${backup.timestamp}</div>
                                    <div style="font-size: 0.8rem; color: var(--text-tertiary);">${formatSize(backup.size)}</div>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button class="restore-btn" data-path="${backup.path}" style="
                                        padding: 6px 12px;
                                        background: var(--success);
                                        border: none;
                                        border-radius: 6px;
                                        color: white;
                                        cursor: pointer;
                                        font-size: 0.85rem;
                                    ">还原</button>
                                    <button class="delete-backup-btn" data-path="${backup.path}" style="
                                        padding: 6px 12px;
                                        background: var(--bg-tertiary);
                                        border: 1px solid var(--border);
                                        border-radius: 6px;
                                        color: var(--text-secondary);
                                        cursor: pointer;
                                        font-size: 0.85rem;
                                    ">删除</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;

            modal.className = 'audio-restore-modal';
            document.body.appendChild(modal);

            // 绑定还原按钮事件
            modal.querySelectorAll('.restore-btn').forEach(btn => {
                btn.onclick = async () => {
                    const backupPath = btn.dataset.path;
                    const restoreResponse = await fetch('/api/short-drama/restore', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            novel_title: this.selectedNovel || '',
                            episode_title: episodeDirectoryName,
                            backup_path: backupPath,
                            backup_current: true
                        })
                    });
                    const restoreResult = await restoreResponse.json();
                    if (restoreResult.success) {
                        this.showToast('音频已还原，请刷新配音页面', 'success');
                        modal.remove();
                        // 重新加载配音步骤
                        this.loadedSteps.delete('dubbing');
                        await this.loadDubbingStep();
                    } else {
                        this.showToast(`还原失败: ${restoreResult.error}`, 'error');
                    }
                };
            });

            // 绑定删除按钮事件
            modal.querySelectorAll('.delete-backup-btn').forEach(btn => {
                btn.onclick = async () => {
                    if (!confirm('确定要删除此备份吗？')) return;
                    const backupPath = btn.dataset.path;
                    const deleteResponse = await fetch('/api/short-drama/backup/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ backup_path: backupPath })
                    });
                    const deleteResult = await deleteResponse.json();
                    if (deleteResult.success) {
                        this.showToast('备份已删除', 'success');
                        btn.closest('div[style*="flex: justify-content"]').remove();
                        if (modal.querySelectorAll('.backup-list > div').length === 0) {
                            modal.remove();
                        }
                    } else {
                        this.showToast(`删除失败: ${deleteResult.error}`, 'error');
                    }
                };
            });

            // 点击背景关闭
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.remove();
            });
        } catch (error) {
            console.error('显示音频备份弹窗失败:', error);
            this.showToast('获取备份列表失败', 'error');
        }
    }

    /**
     * 检查剧本质量
     * 在生成视频前对剧本进行严格检查，确保符合视频生成要求
     */
    async checkScriptQuality(shots) {
        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const response = await fetch('/api/script/quality-check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    shots: shots
                })
            });

            const data = await response.json();
            if (data.success !== false) {
                return {
                    passed: data.passed || false,
                    score: data.score || 0,
                    issues: data.issues || [],
                    warnings: data.warnings || [],
                    recommendations: data.recommendations || []
                };
            }
            // API返回失败，返回低分
            return { passed: false, score: 0, issues: [], warnings: [], recommendations: ['无法连接到质量检查服务'] };
        } catch (error) {
            console.error('质量检查失败:', error);
            // 质量检查失败时返回低分，表示无法验证
            return { passed: false, score: 0, issues: [], warnings: [], recommendations: ['质量检查服务异常'] };
        }
    }

    /**
     * 运行剧本质量检查（手动触发）
     */
    async runQualityCheck() {
        if (this.shots.length === 0) {
            this.showToast('没有可检查的镜头数据', 'warning');
            return;
        }

        this.showToast('正在检查剧本质量...', 'info');
        this.showLoading('正在分析剧本...');

        const result = await this.checkScriptQuality(this.shots);
        this.hideLoading();

        // 如果评分低于80分，自动获取改进建议
        let improvedData = null;
        if (result.score < 80) {
            this.showLoading('正在生成改进方案...');
            improvedData = await this.getScriptImprovements(this.shots, result);
            this.hideLoading();
        }

        // 显示质量检查结果弹窗
        this.showQualityCheckModal(result, improvedData);
    }

    /**
     * 获取剧本改进方案
     */
    async getScriptImprovements(shots, checkResult) {
        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const response = await fetch('/api/script/improve', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    shots: shots,
                    issues: checkResult.issues || [],
                    improve_type: 'script'
                })
            });

            const data = await response.json();
            if (data.success !== false && data.improved_shots) {
                return data;
            }
            return null;
        } catch (e) {
            console.error('获取改进方案失败:', e);
            return null;
        }
    }

    /**
     * 显示质量检查结果弹窗（带修复功能）
     */
    showQualityCheckModal(result, improvedData) {
        const issuesHtml = result.issues.map(i => {
            const severityIcon = i.severity === 'critical' ? '🔴' : i.severity === 'warning' ? '⚠️' : 'ℹ️';
            return `<li>${severityIcon} <strong>${i.category}:</strong> ${i.message}<br><small class="text-secondary">${i.suggestion || ''}</small></li>`;
        }).join('');

        const warningsHtml = result.warnings.map(w => `<li>⚠️ ${w}</li>`).join('');

        const recommendationsHtml = result.recommendations.map(r => `<li>💡 ${r}</li>`).join('');

        const scoreColor = result.score >= 80 ? '#4caf50' : result.score >= 60 ? '#ff9800' : '#f44336';
        const scoreText = result.score >= 80 ? '良好' : result.score >= 60 ? '及格' : '需改进';

        // 是否显示修复按钮
        const showFixButton = result.score < 80 && improvedData && improvedData.improved_shots;

        // 设计文件变更列表
        let designChangesHtml = '';
        if (improvedData && improvedData.design_changes && improvedData.design_changes.length > 0) {
            designChangesHtml = `
                <div style="margin-bottom: 16px; padding: 12px; background: rgba(255,152,0,0.1); border-left: 3px solid #ff9800; border-radius: 4px;">
                    <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #ff9800;">📁 需要修改的设计文件 (${improvedData.design_changes.length})</h4>
                    <ul style="margin: 0; padding-left: 20px; font-size: 13px;">
                        ${improvedData.design_changes.map(c => `
                            <li><strong>${c.file}</strong>: ${c.issue}</li>
                        `).join('')}
                    </ul>
                </div>
            `;
        }

        // 改进摘要
        let improvementSummaryHtml = '';
        if (improvedData && improvedData.improvements_summary) {
            improvementSummaryHtml = `
                <div style="margin-bottom: 16px; padding: 12px; background: rgba(76,175,80,0.1); border-left: 3px solid #4caf50; border-radius: 4px;">
                    <h4 style="margin: 0 0 8px 0; font-size: 14px; color: #4caf50;">✨ 改进方案摘要</h4>
                    <p style="margin: 0; font-size: 13px; line-height: 1.5;">${improvedData.improvements_summary}</p>
                </div>
            `;
        }

        const modalId = 'qualityCheckModal_' + Date.now();
        const modalHtml = `
            <div id="${modalId}" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10000;">
                <div class="modal-content" style="background: var(--bg-primary); border-radius: 12px; padding: 24px; max-width: 650px; max-height: 85vh; overflow-y: auto; color: var(--text-primary); box-shadow: 0 10px 40px rgba(0,0,0,0.3);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h2 style="margin: 0; display: flex; align-items: center; gap: 8px;">📋 剧本质量检查报告</h2>
                        <button onclick="document.getElementById('${modalId}').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-secondary);">×</button>
                    </div>

                    <div style="display: flex; align-items: center; gap: 20px; margin-bottom: 20px; padding: 16px; background: var(--bg-secondary); border-radius: 8px;">
                        <div style="text-align: center;">
                            <div style="font-size: 48px; font-weight: bold; color: ${scoreColor};">${result.score}</div>
                            <div style="font-size: 14px; color: var(--text-secondary);">质量评分</div>
                        </div>
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                <span style="width: 12px; height: 12px; border-radius: 50%; background: ${result.passed ? '#4caf50' : '#f44336'};"></span>
                                <span style="font-weight: 500;">${result.passed ? '检查通过 ✅' : '检查未通过 ❌'}</span>
                            </div>
                            <div style="font-size: 14px; color: ${scoreColor}; font-weight: 500;">${scoreText}</div>
                        </div>
                    </div>

                    ${improvementSummaryHtml}

                    ${result.issues.length > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 15px; display: flex; align-items: center; gap: 6px;">⚠️ 发现的问题 (${result.issues.length})</h3>
                        <ul style="margin: 0; padding-left: 20px; font-size: 13px;">${issuesHtml}</ul>
                    </div>
                    ` : ''}

                    ${result.warnings.length > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 15px;">💡 警告 (${result.warnings.length})</h3>
                        <ul style="margin: 0; padding-left: 20px; font-size: 13px;">${warningsHtml}</ul>
                    </div>
                    ` : ''}

                    ${result.recommendations.length > 0 ? `
                    <div style="margin-bottom: 16px;">
                        <h3 style="margin: 0 0 10px 0; font-size: 15px;">📝 改进建议</h3>
                        <ul style="margin: 0; padding-left: 20px; font-size: 13px;">${recommendationsHtml}</ul>
                    </div>
                    ` : ''}

                    ${designChangesHtml}

                    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border-color); display: flex; justify-content: flex-end; gap: 12px; flex-wrap: wrap;">
                        ${showFixButton ? `
                            <button onclick="shortDramaStudio.showFixConfirm()"
                                    style="padding: 10px 20px; background: linear-gradient(135deg, #4caf50, #45a049); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; display: flex; align-items: center; gap: 6px;">
                                <span>🔧</span>
                                <span>一键修复 (${improvedData.improved_shots.length}个镜头)</span>
                            </button>
                        ` : ''}
                        <button onclick="document.getElementById('${modalId}').remove()" style="padding: 10px 20px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer;">
                            关闭
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        // 保存改进数据供后续使用
        this.setImprovedData(improvedData);
    }

    /**
     * 显示修复确认对话框（从按钮触发）
     */
    showFixConfirm() {
        console.log('[DEBUG] showFixConfirm called');
        const improvedData = this.getImprovedData();
        console.log('[DEBUG] improvedData:', improvedData);
        if (!improvedData) {
            this.showToast('改进数据丢失，请重新检查', 'error');
            return;
        }
        this.showFixConfirmDialog(improvedData);
    }

    /**
     * 显示修复确认对话框
     */
    async showFixConfirmDialog(improvedData) {
        return new Promise((resolve) => {
            const improvedShots = improvedData.improved_shots || [];
            const designChanges = improvedData.design_changes || [];

            // 统计修复内容
            const fixSummary = [];
            fixSummary.push(`📝 将修复 ${improvedShots.length} 个镜头`);
            if (designChanges.length > 0) {
                fixSummary.push(`📁 将更新 ${designChanges.length} 个设计文件`);
            }

            // 生成完整的修复项列表（所有镜头）
            const keyFixesHtml = improvedShots.map((shot, i) => {
                // 优先使用index，否则使用数组索引+1作为镜头号
                const shotNum = shot.index !== undefined && shot.index !== null ? shot.index + 1 : i + 1;
                const reason = shot.improvement_reason || '优化描述';
                const shortReason = reason.length > 50 ? reason.substring(0, 50) + '...' : reason;
                return `<li style="padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.1);"><strong>镜头${shotNum}</strong>: ${shortReason}</li>`;
            }).join('');

            const modalId = 'fixConfirmModal_' + Date.now();
            const modalHtml = `
                <div id="${modalId}" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); display: flex; align-items: center; justify-content: center; z-index: 10001;">
                    <div class="modal-content" style="background: var(--bg-primary); border-radius: 12px; padding: 24px; max-width: 600px; max-height: 85vh; overflow: hidden; display: flex; flex-direction: column; color: var(--text-primary); box-shadow: 0 10px 40px rgba(0,0,0,0.4);">
                        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 20px; flex-shrink: 0;">
                            <span style="font-size: 32px;">🔧</span>
                            <h2 style="margin: 0;">确认应用修复</h2>
                        </div>

                        <div style="flex: 1; overflow-y: auto; margin-bottom: 20px;">
                            <p style="margin: 0 0 16px 0; color: var(--text-secondary);">AI分析发现剧本存在以下问题，建议应用修复。此操作将覆盖现有镜头数据。</p>

                            <div style="padding: 12px; background: var(--bg-secondary); border-radius: 8px; margin-bottom: 12px;">
                                <div style="font-weight: 500; margin-bottom: 8px;">修复摘要:</div>
                                ${fixSummary.map(s => `<div style="padding: 4px 0;">${s}</div>`).join('')}
                            </div>

                            ${improvedShots.length > 0 ? `
                            <div style="padding: 12px; background: rgba(255,152,0,0.1); border-radius: 8px;">
                                <div style="font-weight: 500; margin-bottom: 8px;">将修复以下镜头 (${improvedShots.length}个):</div>
                                <ul style="margin: 0; padding-left: 20px; font-size: 13px; max-height: 300px; overflow-y: auto;">
                                    ${keyFixesHtml}
                                </ul>
                            </div>
                            ` : ''}
                        </div>

                        <div style="display: flex; gap: 12px; justify-content: flex-end; flex-shrink: 0;">
                            <button onclick="shortDramaStudio.cancelFixConfirm('${modalId}')"
                                    style="padding: 10px 20px; background: var(--bg-secondary); color: var(--text-primary); border: 1px solid var(--border-color); border-radius: 6px; cursor: pointer;">
                                取消
                            </button>
                            <button onclick="shortDramaStudio.confirmFixApply()"
                                    style="padding: 10px 20px; background: linear-gradient(135deg, #4caf50, #45a049); color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 500;">
                                确认修复
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            // 保存当前modalId和resolve函数供按钮调用
            this._fixConfirmModalId = modalId;
            this._fixConfirmResolve = resolve;
        });
    }

    /**
     * 取消修复确认
     */
    cancelFixConfirm(modalId) {
        if (this._fixConfirmResolve) {
            this._fixConfirmResolve(false);
            this._fixConfirmResolve = null;
        }
        this._fixConfirmModalId = null;
        document.getElementById(modalId)?.remove();
    }

    /**
     * 确认并应用修复
     */
    async confirmFixApply() {
        if (this._fixConfirmResolve) {
            this._fixConfirmResolve(true);
            this._fixConfirmResolve = null;
        }
        // 关闭确认弹窗
        const modalId = this._fixConfirmModalId;
        this._fixConfirmModalId = null;
        document.getElementById(modalId)?.remove();

        // 执行应用修复
        await this._doApplyFixes();
    }

    /**
     * 执行修复的内部方法
     */
    async _doApplyFixes() {
        const improvedData = this.getImprovedData();
        if (!improvedData) {
            this.showToast('改进数据丢失，请重新检查', 'error');
            return;
        }

        this.showLoading('正在应用修复...');

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const response = await fetch('/api/script/apply-fixes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    novel_title: this.selectedNovel || '',
                    episode_title: episodeDirectoryName,
                    original_shots: this.shots,
                    improved_shots: improvedData.improved_shots || [],
                    design_changes: improvedData.design_changes || [],
                    apply_design_changes: true
                })
            });

            const data = await response.json();
            this.hideLoading();

            if (data.success) {
                // 更新本地镜头数据
                if (data.updated_shots) {
                    this.shots = data.updated_shots;
                    this.renderVideoCards();
                }

                // 显示成功消息
                let successMsg = `✅ 修复完成！\n\n${data.summary || ''}`;
                if (data.design_files_updated && data.design_files_updated.length > 0) {
                    successMsg += `\n\n已更新设计文件:\n• ${data.design_files_updated.join('\n• ')}`;
                }
                this.showToast(successMsg, 'success');

                // 显示修复对比弹窗
                this.showFixCompareModal(improvedData);
            } else {
                this.showToast(`修复失败: ${data.error || '未知错误'}`, 'error');
            }
        } catch (e) {
            this.hideLoading();
            console.error('应用修复失败:', e);
            this.showToast(`修复失败: ${e.message}`, 'error');
        }
    }

    /**
     * 显示修复对比弹窗
     */
    showFixCompareModal(improvedData) {
        const improvedShots = improvedData.improved_shots || [];
        if (improvedShots.length === 0) return;

        const modalId = 'fixCompareModal_' + Date.now();

        // 生成完整的修复列表（所有镜头）
        const compareItems = improvedShots.map((shot, i) => {
            // 优先使用index，否则使用数组索引+1作为镜头号
            const shotNum = shot.index !== undefined && shot.index !== null ? shot.index + 1 : i + 1;
            const newDesc = shot.description || '';
            const newDialogue = shot.dialogue || '';
            const reason = shot.improvement_reason || '优化描述';

            return `
                <div style="margin-bottom: 16px; padding: 12px; background: var(--bg-secondary); border-radius: 8px; border-left: 3px solid var(--primary);">
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap;">
                        <span style="background: var(--primary); color: white; padding: 3px 10px; border-radius: 4px; font-size: 13px; font-weight: 500;">📹 镜头 ${shotNum}</span>
                        <span style="color: #4caf50; font-size: 12px;">${reason}</span>
                    </div>
                    ${newDialogue ? `<div style="margin-bottom: 6px; padding: 6px 10px; background: rgba(100,149,237,0.1); border-radius: 4px; font-size: 13px;">💬 ${newDialogue}</div>` : ''}
                    <div style="font-size: 13px; color: var(--text-secondary); line-height: 1.5;">${newDesc}</div>
                </div>
            `;
        }).join('');

        const modalHtml = `
            <div id="${modalId}" class="modal-overlay" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 10002;">
                <div class="modal-content" style="background: var(--bg-primary); border-radius: 12px; padding: 24px; max-width: 650px; max-height: 85vh; overflow: hidden; display: flex; flex-direction: column; color: var(--text-primary);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-shrink: 0;">
                        <h2 style="margin: 0; display: flex; align-items: center; gap: 8px;">✅ 修复完成 - 共 ${improvedShots.length} 个镜头</h2>
                        <button onclick="document.getElementById('${modalId}').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-secondary);">×</button>
                    </div>

                    <p style="margin: 0 0 16px 0; color: var(--text-secondary); flex-shrink: 0;">以下是所有镜头的修复详情：</p>

                    <div style="flex: 1; overflow-y: auto; padding-right: 8px;">
                        ${compareItems}
                    </div>

                    <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border-color); text-align: right; flex-shrink: 0;">
                        <button onclick="document.getElementById('${modalId}').remove()" style="padding: 10px 20px; background: var(--primary); color: white; border: none; border-radius: 6px; cursor: pointer;">
                            知道了
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
    }

    /**
     * 存储改进数据到实例变量（用于跨方法传递）
     */
    setImprovedData(data) {
        this._improvedData = data;
    }

    getImprovedData() {
        return this._improvedData;
    }

    /**
     * 关闭视频进度弹窗
     * @param {number} shotIndex - 要关闭的任务索引，如果不传则关闭所有
     */
    closeVideoProgressModal(shotIndex = null) {
        if (shotIndex !== null) {
            // 只关闭特定任务的弹窗
            const modal = document.getElementById(`videoProgressModal_${shotIndex}`);
            if (modal) modal.remove();
        } else {
            // 关闭所有进度弹窗
            document.querySelectorAll('[id^="videoProgressModal_"]').forEach(modal => modal.remove());
            // 兼容旧的 ID
            const oldModal = document.getElementById('videoProgressModal');
            if (oldModal) oldModal.remove();
        }
    }

    /**
     * 包装的生成视频方法（返回Promise，用于批量生成）
     */
    async generateShotVideoWithPromise(shotIndex) {
        const shot = this.shots[shotIndex];
        if (!shot) return;

        shot.generating = true;
        shot.hasError = false;
        this.updateVideoCard(shotIndex);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();
            const videoSettings = this.getVideoSettings();

            // 🔥 构建包含台词的 prompt，用于 AI 口型同步
            let prompt = shot.veo_prompt || shot.screen_action || '';

            // 检查是否有英文台词，用于口型同步
            const dialogueData = shot._dialogue_data || shot.dialogue;
            if (dialogueData && dialogueData.lines_en && dialogueData.lines_en.trim()) {
                prompt += `. Character speaking: "${dialogueData.lines_en}"`;
            }

            // 🔥 打印发送给API的实际提示词，方便排查
            console.log('📤 [发送给VeO API的提示词 - Promise模式]');
            console.log('  - 镜头: S' + (shot._scene_number || shot.scene_number || 1) + '#' + (shot.shot_number || (shotIndex + 1)));
            console.log('  - 提示词长度:', prompt.length, '字符');
            console.log('  - 提示词内容:\n' + prompt);

            // 🔥 无参考图模式：强制使用 veo_3_1-fast 模型
            const finalModel = 'veo_3_1-fast';
            console.log('  - 模型: ' + finalModel + ' (无参考图模式)');

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: finalModel,
                    prompt: prompt,
                    image_urls: [],
                    orientation: videoSettings.orientation,
                    size: videoSettings.size,
                    watermark: false,
                    private: true,
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        scene_number: shot._scene_number || shot.scene_number || 1,  // 🔥 场景号（从分镜头文件获取）
                        shot_number: String(shot.shot_number || (shotIndex + 1)),  // 🔥 镜头号（场景内的编号）
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        is_dialogue_scene: shot.is_dialogue_scene || false,
                        lines_en: dialogueData?.lines_en || ''
                    }
                })
            });

            // 🔥 调试日志
            console.log('🎬 [视频生成] scene_number:', shot._scene_number || shot.scene_number, 'shot_number:', shot.shot_number, 'event_name:', shot.episode_title);

            const data = await response.json();

            if (data.id) {
                await this.pollVideoStatusForBatch(data.id, shotIndex);
            } else {
                throw new Error(data.error?.message || '生成失败');
            }
        } catch (error) {
            console.error('生成视频失败:', error);
            shot.generating = false;
            shot.hasError = true;
            shot.errorMessage = error.message || '生成失败';
            this.updateVideoCard(shotIndex);
        }
    }

    /**
     * 轮询视频生成状态（批量模式）
     */
    pollVideoStatusForBatch(taskId, shotIndex) {
        return new Promise((resolve) => {
            const maxAttempts = 120;
            let attempts = 0;
            const shot = this.shots[shotIndex];

            console.log(`🎬 [批量轮询] 开始轮询 shotIndex=${shotIndex}, taskId=${taskId}`);

            const poll = async () => {
                try {
                    const response = await fetch(`/api/veo/status/${taskId}`);
                    const data = await response.json();

                    console.log(`🎬 [批量轮询] shotIndex=${shotIndex}, status=${data.status}, attempt=${attempts + 1}/${maxAttempts}`);

                    if (data.status === 'completed') {
                        shot.generating = false;
                        shot.videoExists = true;
                        shot.hasError = false;

                        // 🔥 修复：根据实际数据结构获取视频URL
                        // 数据格式: data.result.videos[0].url
                        if (data.result && data.result.videos && data.result.videos.length > 0) {
                            shot.videoUrl = data.result.videos[0].url;
                            shot.videoPath = data.result.videos[0].url;
                            console.log(`🎬 [批量轮询] 视频URL: ${shot.videoUrl}`);
                        } else if (data.result && data.result.video_url) {
                            // 兼容旧格式
                            shot.videoUrl = data.result.video_url;
                            shot.videoPath = data.result.video_path;
                            console.log(`🎬 [批量轮询] 视频URL(旧格式): ${shot.videoUrl}`);
                        } else {
                            console.error(`🎬 [批量轮询] 完成但无视频URL:`, data.result);
                        }

                        console.log(`🎬 [批量轮询] shotIndex=${shotIndex} 准备更新卡片，videoExists=${shot.videoExists}`);
                        this.updateVideoCard(shotIndex);
                        this.updateProjectStatus();
                        this.showToast(`镜头 #${shot.shot_number || (shotIndex + 1)} 生成完成`, 'success');
                        resolve();

                    } else if (data.status === 'failed') {
                        shot.generating = false;
                        shot.hasError = true;
                        shot.errorMessage = data.error?.message || data.message || '生成失败';
                        this.updateVideoCard(shotIndex);
                        resolve();
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000);
                    } else {
                        shot.generating = false;
                        shot.hasError = true;
                        shot.errorMessage = '生成超时';
                        this.updateVideoCard(shotIndex);
                        resolve();
                    }
                } catch (error) {
                    console.error('检查状态失败:', error);
                    shot.generating = false;
                    shot.hasError = true;
                    shot.errorMessage = error.message || '检查状态失败';
                    this.updateVideoCard(shotIndex);
                    resolve();
                }
            };

            poll();
        });
    }

    /**
     * 停止批量生成
     */
    stopBatchGeneration() {
        this.stopBatchGeneration = true;
    }

    /**
     * 打开项目
     */
    /**
     * 打开项目
     */
    async openProject(projectId) {
        // 从项目列表中查找项目
        const project = this.projects.find(p => p.id === projectId);
        if (!project) {
            this.showToast('项目不存在', 'error');
            return;
        }

        console.log('📺 [工作流] 打开项目:', project);

        // 设置当前项目
        this.currentProject = project;
        this.selectedNovel = project.title;

        // 加载项目设置到UI
        this.loadProjectSettings(project.settings);

        // 启动工作流
        await this.startWorkflowFromNovel(project.title);
    }

    /**
     * 加载项目设置到UI
     */

    /**
     * 设置改变时自动保存
     */
    onSettingChange() {
        // 保存设置到当前项目
        if (this.currentProject) {
            this.currentProject.settings = this.getProjectSettings();
        }
    }

    /**
     * 删除项目
     */

    /**
     * 返回项目列表
     */

    /**
     * 显示Toast通知
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * 显示加载遮罩
     */
    showLoading(message = '加载中...') {
        // 移除已存在的loading
        this.hideLoading();

        const overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <div class="loading-text">${message}</div>
            </div>
        `;

        // 添加样式
        if (!document.getElementById('loadingStyles')) {
            const style = document.createElement('style');
            style.id = 'loadingStyles';
            style.textContent = `
                .loading-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.7);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                }
                .loading-spinner {
                    text-align: center;
                    color: white;
                }
                .spinner {
                    width: 40px;
                    height: 40px;
                    margin: 0 auto 16px;
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top-color: var(--primary, #4CAF50);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                .loading-text {
                    font-size: 14px;
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(overlay);
    }

    /**
     * 隐藏加载遮罩
     */
    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * 保存项目
     */

    /**
     * 获取项目设置
     */

    /**
     * 更新项目状态显示
     */

    /**
     * 打开创意导入模态框
     */
    openIdeaModal() {
        const modal = document.getElementById('ideaImportModal');
        if (modal) {
            modal.style.display = 'flex';
            // 清空之前的输入
            document.getElementById('ideaTitle').value = '';
            document.getElementById('ideaEpisode').value = '1';
            document.getElementById('ideaDescription').value = '';
            document.getElementById('ideaStyle').value = '通用';
            document.getElementById('ideaShotDuration').value = '8';
            // 清空主角信息
            document.getElementById('ideaProtagonistName').value = '';
            document.getElementById('ideaProtagonistAge').value = '';
            document.getElementById('ideaProtagonistAppearance').value = '';
            document.getElementById('ideaProtagonistRole').value = '';
            // 清空JSON输入
            const jsonInput = document.getElementById('jsonImportInput');
            if (jsonInput) jsonInput.value = '';
            const validationResult = document.getElementById('jsonValidationResult');
            if (validationResult) validationResult.style.display = 'none';
            // 默认切换到表单模式
            this.switchImportMode('form');
        }
    }

    /**
     * 关闭创意导入模态框
     */
    closeIdeaModal() {
        const modal = document.getElementById('ideaImportModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    /**
     * 切换导入模式
     */
    switchImportMode(mode) {
        const formTab = document.getElementById('formModeTab');
        const jsonTab = document.getElementById('jsonModeTab');
        const formArea = document.querySelector('#ideaImportModal .modal-body');
        const jsonArea = document.getElementById('jsonImportArea');
        
        if (mode === 'form') {
            // 切换到表单模式
            formTab.classList.add('active');
            formTab.style.color = 'var(--primary)';
            formTab.style.borderBottom = '2px solid var(--primary)';
            jsonTab.classList.remove('active');
            jsonTab.style.color = 'var(--text-secondary)';
            jsonTab.style.borderBottom = 'none';
            
            formArea.style.display = 'block';
            jsonArea.style.display = 'none';
        } else {
            // 切换到JSON模式
            jsonTab.classList.add('active');
            jsonTab.style.color = 'var(--primary)';
            jsonTab.style.borderBottom = '2px solid var(--primary)';
            formTab.classList.remove('active');
            formTab.style.color = 'var(--text-secondary)';
            formTab.style.borderBottom = 'none';
            
            formArea.style.display = 'none';
            jsonArea.style.display = 'block';
        }
        
        this.currentImportMode = mode;
    }

    /**
     * 加载Demo文件 - 验证全流程
     * @param {string} type - 'single' 单集示例或 'multi' 多集示例
     */
    async loadDemoFile(type = 'single') {
        const demoFile = type === 'multi' ? '/static/demo/multi_episode_demo.json' : '/static/demo/idea_import_demo.json';
        try {
            // 添加时间戳参数防止缓存
            const timestamp = new Date().getTime();
            const response = await fetch(`${demoFile}?t=${timestamp}`);
            if (!response.ok) {
                // 如果静态文件不存在，使用内置的demo数据
                console.log('Demo文件加载失败，使用内置数据');
                this.loadBuiltinDemo();
                return;
            }
            const data = await response.json();
            document.getElementById('jsonImportInput').value = JSON.stringify(data, null, 2);
            this.validateJson();
            
            // 根据类型显示不同提示
            if (type === 'multi' || (data.episodes && data.episodes.length > 0)) {
                this.showToast('✅ 多集Demo加载成功！请选择要生成的单一集数', 'success');
            } else {
                this.showToast('✅ 单集Demo加载成功！点击「开始创作」验证全流程', 'success');
            }
        } catch (error) {
            console.log('Demo文件加载失败，使用内置数据:', error);
            this.loadBuiltinDemo();
        }
    }

    /**
     * 加载内置Demo数据
     */
    loadBuiltinDemo() {
        const demoData = {
            "title": "废土：开局徒手掹高达",
            "episode": 1,
            "description": "2145年，核战后的末世废土。主角林小满是一名底层外卖骑手，在垃圾场发现一台神秘机甲残骸。他凭借机械改造天赋修复机甲，却遭遇掠夺者小队袭击。关键时刻，机甲启动，林小满驾驶机甲反杀敌人，开启废土霸主之路。",
            "world_setting": "2145年，核战后的末世废土，灵气复苏导致生物变异，旧时代科技遗迹散落各地。幸存者建立移动要塞，赏金猎人和机械师成为最吃香的职业。",
            "style": "废土",
            "shot_duration": 5,
            "protagonist": {
                "name": "林小满",
                "age": "22岁",
                "appearance": "黄色战术外卖服（改装版，有防刺钢板），黑色低马尾（用红色发绳扎起），戴黑框眼镜（左镜片有裂痕），左臂有红色山海经图腾胎记，腰间挂满机械工具，右手是机械义肢",
                "role": "底层外卖骑手，性格贪媚但勇敢，擅长机械改造，梦想成为废土机械大师"
            }
            // 不提供 shots 字段，让AI自动生成分镜
        };

        document.getElementById('jsonImportInput').value = JSON.stringify(demoData, null, 2);
        this.validateJson();
        this.showToast('✅ Demo加载成功！点击「开始创作」验证全流程', 'success');
    }

    /**
     * 加载JSON示例
     */
    loadJsonExample(type = 'full') {
        if (type === 'minimal') {
            // 简洁示例 - 只包含必填字段，让AI生成分镜
            const example = {
                "title": "废土：开局徒手搓高达",
                "episode": 1,
                "description": "主角在废土垃圾场发现神秘机甲残骸，凭借机械改造能力修复机甲，遭遇掠夺者袭击，驾驶机甲反杀。",
                "protagonist": {
                    "name": "林小满",
                    "appearance": "黄色战术外卖服（改装），黑色低马尾，戴黑框眼镜，左臂有红色山海经图腾胎记"
                }
            };
            document.getElementById('jsonImportInput').value = JSON.stringify(example, null, 2);
        } else {
            // 完整示例 - 包含分镜数据
            const example = {
                "title": "废土：开局徒手搓高达",
                "episode": 1,
                "description": "主角在废土垃圾场发现神秘机甲残骸，凭借机械改造能力修复机甲，遭遇掠夺者袭击，驾驶机甲反杀。",
                "world_setting": "2145年，核战后的末世废土，灵气复苏导致生物变异，旧时代科技遗迹散落各地。",
                "style": "废土",
                "shot_duration": 5,
                "protagonist": {
                    "name": "林小满",
                    "age": "22岁",
                    "appearance": "黄色战术外卖服（改装），黑色低马尾，戴黑框眼镜，左臂有红色山海经图腾胎记，机械工具腰带",
                    "role": "底层外卖骑手，性格贪婪但勇敢，擅长机械改造"
                },
                "shots": [
                    {
                        "shot_number": 1,
                        "scene_title": "开场-废土场景",
                        "content": "广角：荒芜的废土垃圾场，天空呈现诡异的紫红色，远处可见坍塌的高楼废墟",
                        "duration": 6,
                        "camera_angle": "广角",
                        "camera_movement": "慢推进",
                        "scene_type": "environment"
                    },
                    {
                        "shot_number": 2,
                        "scene_title": "发现机甲",
                        "content": "中景：林小满蹲在机甲残骸旁，眼镜反射着金属光泽，手中工具在发光",
                        "duration": 5,
                        "camera_angle": "中景",
                        "camera_movement": "固定",
                        "scene_type": "dialogue",
                        "dialogues": [
                            {
                                "speaker": "林小满",
                                "text": "这玩意儿...至少值三百信用点！"
                            }
                        ]
                    },
                    {
                        "shot_number": 3,
                        "scene_title": "敌人出现",
                        "content": "过肩：强盗小队从废墟后出现，手持改装武器，面具下露出策略性微笑",
                        "duration": 4,
                        "camera_angle": "过肩",
                        "camera_movement": "横摇",
                        "scene_type": "action",
                        "dialogues": [
                            {
                                "speaker": "强盗头目",
                                "text": "那台机甲，是我们的了。"
                            }
                        ]
                    }
                ]
            };
            document.getElementById('jsonImportInput').value = JSON.stringify(example, null, 2);
        }
        this.validateJson();
    }

    /**
     * 智能解析JSON - 支持多种常见格式
     */
    autoParseJson() {
        const input = document.getElementById('jsonImportInput');
        const value = input.value.trim();
        
        if (!value) {
            this.showToast('请先粘贴JSON内容', 'warning');
            return;
        }
        
        try {
            let data = JSON.parse(value);
            let parsed = this.parseVariousFormats(data);
            
            if (parsed) {
                // 用标准格式替换原始内容
                input.value = JSON.stringify(parsed, null, 2);
                this.showToast('✅ 智能解析成功！已转换为标准格式', 'success');
                this.validateJson();
            }
        } catch (e) {
            this.showToast('解析失败: ' + e.message, 'error');
        }
    }

    /**
     * 解析多种常见格式为标准格式
     */
    parseVariousFormats(data) {
        // 已经是标准格式
        if (data.title && data.description) {
            return this.normalizeToStandard(data);
        }
        
        // 格式1: 小说/故事结构
        if (data.story || data.plot || data.chapters) {
            return this.parseStoryFormat(data);
        }
        
        // 格式2: 分镜表/脚本结构
        if (data.shots || data.scenes || data.script) {
            return this.parseScriptFormat(data);
        }
        
        // 格式3: 视频描述结构
        if (data.video || data.timeline || data.segments) {
            return this.parseVideoFormat(data);
        }
        
        // 格式4: 简化结构
        if (data.name || data.idea || data.concept) {
            return this.parseSimpleFormat(data);
        }
        
        // 尝试从数组解析
        if (Array.isArray(data)) {
            return this.parseArrayFormat(data);
        }
        
        return null;
    }

    /**
     * 将数据标准化为统一格式
     */
    normalizeToStandard(data) {
        const normalized = {
            title: data.title || data.name || '未命名剧集',
            episode: parseInt(data.episode) || parseInt(data.ep) || 1,
            description: data.description || data.desc || data.summary || data.plot || '',
            world_setting: data.world_setting || data.world || data.background || data.setting || '',
            style: data.style || data.genre || data.type || '通用',
            shot_duration: parseInt(data.shot_duration) || parseInt(data.duration) || 5,
            protagonist: this.normalizeProtagonist(data.protagonist || data.character || data.hero || data.main_character || {}),
            shots: this.normalizeShotsForImport(data.shots || data.scenes || data.frames || [])
        };
        
        // 提取新版格式的额外字段
        if (data.episodes && Array.isArray(data.episodes)) {
            normalized.episodes = data.episodes.map(ep => ({
                episode: parseInt(ep.episode) || parseInt(ep.ep) || 1,
                episode_title: ep.episode_title || ep.title || `第${parseInt(ep.episode) || 1}集`,
                description: ep.description || ep.desc || ep.summary || '',
                shot_duration: parseInt(ep.shot_duration) || parseInt(ep.duration) || 5,
                focus: ep.focus || ep.plot_structure || {},
                // 新版格式字段
                plot_structure: ep.plot_structure || null,
                key_scenes: ep.key_scenes || null,
                character_arc: ep.character_arc || '',
                logline: ep.logline || '',
                theme: ep.theme || '',
                status: ep.status || 'pending'
            }));
        }
        
        return normalized;
    }

    /**
     * 标准化主角信息
     */
    normalizeProtagonist(protagonist) {
        if (typeof protagonist === 'string') {
            return { name: protagonist, appearance: '' };
        }
        return {
            name: protagonist.name || protagonist.title || protagonist.character_name || '',
            age: protagonist.age || protagonist.years || '',
            appearance: protagonist.appearance || protagonist.looks || protagonist.description || protagonist.desc || '',
            role: protagonist.role || protagonist.identity || protagonist.personality || protagonist.character || ''
        };
    }

    /**
     * 标准化分镜列表（专门用于创意导入）
     */

    /**
     * 标准化对话
     */
    normalizeDialogues(dialogues) {
        if (!Array.isArray(dialogues) || dialogues.length === 0) return [];
        
        return dialogues.map(d => {
            if (typeof d === 'string') {
                return { speaker: '角色', text: d };
            }
            return {
                speaker: d.speaker || d.character || d.role || d.name || d.person || '角色',
                text: d.text || d.line || d.content || d.dialogue || d.words || ''
            };
        }).filter(d => d.text);
    }

    /**
     * 解析小说/故事格式
     */
    parseStoryFormat(data) {
        const story = data.story || data.plot || '';
        const chapters = data.chapters || data.acts || data.parts || [];
        
        return this.normalizeToStandard({
            title: data.title || data.name || '未命名剧集',
            episode: 1,
            description: story,
            protagonist: data.main_character || data.protagonist || {},
            shots: chapters.flatMap((ch, i) => {
                const scenes = ch.scenes || ch.shots || [ch];
                return scenes.map((scene, j) => ({
                    shot_number: i * 100 + j + 1,
                    scene_title: ch.title || ch.name || `第${i+1}章`,
                    content: typeof scene === 'string' ? scene : (scene.content || scene.description || ''),
                    dialogues: scene.dialogues || scene.dialogue || []
                }));
            })
        });
    }

    /**
     * 解析脚本/分镜格式
     */
    parseScriptFormat(data) {
        const script = data.script || data;
        const shots = data.shots || data.scenes || [];
        
        return this.normalizeToStandard({
            title: data.title || script.title || '未命名剧集',
            episode: data.episode || script.episode || 1,
            description: data.description || script.description || script.summary || '',
            world_setting: data.world_setting || script.setting || '',
            protagonist: data.protagonist || script.character || script.main_character || {},
            shots: shots
        });
    }

    /**
     * 解析视频格式
     */
    parseVideoFormat(data) {
        const video = data.video || data;
        const segments = data.timeline || data.segments || data.scenes || [];
        
        return this.normalizeToStandard({
            title: data.title || video.title || '未命名视频',
            episode: 1,
            description: data.description || video.description || '',
            shots: segments.map((seg, i) => ({
                shot_number: i + 1,
                scene_title: seg.title || seg.name || `片段${i+1}`,
                content: seg.content || seg.description || seg.text || '',
                duration: seg.duration || seg.length || 5
            }))
        });
    }

    /**
     * 解析简化格式
     */
    parseSimpleFormat(data) {
        return this.normalizeToStandard({
            title: data.title || data.name || '未命名剧集',
            episode: data.episode || 1,
            description: data.idea || data.concept || data.description || data.plot || '',
            style: data.style || data.genre || '',
            protagonist: data.character || data.protagonist || data.main || {},
            shots: data.shots || data.frames || []
        });
    }

    /**
     * 解析数组格式
     */
    parseArrayFormat(data) {
        // 如果是纯文本数组，当作分镜列表
        if (data.every(item => typeof item === 'string')) {
            return this.normalizeToStandard({
                title: '从分镜列表导入',
                episode: 1,
                description: data.join('\n'),
                shots: data.map((content, i) => ({ content, shot_number: i + 1 }))
            });
        }
        
        // 如果是对象数组，使用第一个对象
        if (data.length > 0 && typeof data[0] === 'object') {
            return this.normalizeToStandard(data[0]);
        }
        
        return null;
    }

    /**
     * 验证JSON格式
     */
    validateJson() {
        const input = document.getElementById('jsonImportInput');
        const resultDiv = document.getElementById('jsonValidationResult');
        const value = input.value.trim();

        if (!value) {
            resultDiv.style.display = 'none';
            return false;
        }

        try {
            const data = JSON.parse(value);

            // 🔥 检查是否为多集结构
            if (data.episodes && Array.isArray(data.episodes) && data.episodes.length > 0) {
                // 验证多集结构
                if (!data.title) {
                    resultDiv.style.display = 'block';
                    resultDiv.style.background = 'rgba(239, 68, 68, 0.1)';
                    resultDiv.style.color = '#ef4444';
                    resultDiv.textContent = '❌ 缺少必填字段: title';
                    return false;
                }

                // 验证每一集的必填字段
                for (const ep of data.episodes) {
                    if (!ep.episode || !ep.description) {
                        resultDiv.style.display = 'block';
                        resultDiv.style.background = 'rgba(239, 68, 68, 0.1)';
                        resultDiv.style.color = '#ef4444';
                        resultDiv.textContent = `❌ 第${ep.episode || '?'}集缺少必填字段`;
                        return false;
                    }
                }

                // 显示多集验证成功信息
                resultDiv.style.display = 'block';
                resultDiv.style.background = 'rgba(34, 197, 94, 0.1)';
                resultDiv.style.color = '#22c55e';
                const hasProtagonist = data.protagonist && data.protagonist.name;
                const protagonist = hasProtagonist ? `主角：${data.protagonist.name}` : '无主角信息';
                const pendingCount = data.episodes.filter(ep => ep.status === 'pending').length;
                resultDiv.innerHTML = `✅ 多集格式正确 | ${protagonist} | 共${data.episodes.length}集 | <span style="color: var(--primary);">待生成${pendingCount}集</span>`;
                return true;
            }

            // 使用智能解析检查字段（单集结构）
            const parsed = this.parseVariousFormats(data);

            if (!parsed) {
                resultDiv.style.display = 'block';
                resultDiv.style.background = 'rgba(239, 68, 68, 0.1)';
                resultDiv.style.color = '#ef4444';
                resultDiv.textContent = '❌ 无法识别JSON格式，请点击「智能解析」尝试自动转换';
                return false;
            }

            const required = ['title', 'description'];
            const missing = required.filter(key => !parsed[key]);

            if (missing.length > 0) {
                resultDiv.style.display = 'block';
                resultDiv.style.background = 'rgba(239, 68, 68, 0.1)';
                resultDiv.style.color = '#ef4444';
                resultDiv.textContent = `❌ 缺少必填字段: ${missing.join(', ')}`;
                return false;
            }

            resultDiv.style.display = 'block';
            resultDiv.style.background = 'rgba(34, 197, 94, 0.1)';
            resultDiv.style.color = '#22c55e';

            const shotCount = parsed.shots ? parsed.shots.length : 0;
            const hasProtagonist = parsed.protagonist && parsed.protagonist.name;
            const protagonist = hasProtagonist ? `主角：${parsed.protagonist.name}` : '无主角信息';
            const mode = shotCount > 0 ? '导入分镜' : 'AI生成分镜';
            resultDiv.innerHTML = `✅ 格式正确 | ${protagonist} | 分镜：${shotCount} | <span style="color: var(--primary);">${mode}</span>`;
            return true;
        } catch (e) {
            resultDiv.style.display = 'block';
            resultDiv.style.background = 'rgba(239, 68, 68, 0.1)';
            resultDiv.style.color = '#ef4444';
            resultDiv.textContent = `❌ JSON格式错误: ${e.message}`;
            return false;
        }
    }

    /**
     * 提交创意导入
     */
    async submitIdeaImport() {
        // 根据当前模式决定如何提交
        if (this.currentImportMode === 'json') {
            await this.submitJsonImport();
        } else {
            await this.submitFormImport();
        }
    }

    /**
     * 表单模式提交
     */
    async submitFormImport() {
        const title = document.getElementById('ideaTitle').value.trim();
        const episode = parseInt(document.getElementById('ideaEpisode').value) || 1;
        const description = document.getElementById('ideaDescription').value.trim();
        const style = document.getElementById('ideaStyle').value;
        const shotDuration = parseInt(document.getElementById('ideaShotDuration').value) || 8;
        
        // 主角信息
        const protagonistName = document.getElementById('ideaProtagonistName')?.value.trim();
        const protagonistAge = document.getElementById('ideaProtagonistAge')?.value.trim();
        const protagonistAppearance = document.getElementById('ideaProtagonistAppearance')?.value.trim();
        const protagonistRole = document.getElementById('ideaProtagonistRole')?.value.trim();

        // 验证必填字段
        if (!title) {
            this.showToast('请输入剧集名称', 'warning');
            return;
        }
        if (!episode || episode < 1) {
            this.showToast('请输入有效的集数', 'warning');
            return;
        }
        if (!description) {
            this.showToast('请输入创意描述', 'warning');
            return;
        }
        if (!protagonistName) {
            this.showToast('请输入主角姓名', 'warning');
            return;
        }
        if (!protagonistAppearance) {
            this.showToast('请输入主角外观特征', 'warning');
            return;
        }

        await this.doCreateFromIdea({
            title,
            episode,
            description,
            style,
            shot_duration: shotDuration,
            protagonist: {
                name: protagonistName,
                age: protagonistAge,
                appearance: protagonistAppearance,
                role: protagonistRole
            }
        });
    }

    /**
     * JSON模式提交
     */
    async submitJsonImport() {
        const input = document.getElementById('jsonImportInput');
        const value = input.value.trim();

        if (!value) {
            this.showToast('请输入JSON内容', 'warning');
            return;
        }

        let data;
        try {
            data = JSON.parse(value);
        } catch (e) {
            this.showToast('JSON格式错误: ' + e.message, 'error');
            return;
        }

        // 🔥 处理多集结构 - 用户选择其中一集生成
        if (data.episodes && Array.isArray(data.episodes) && data.episodes.length > 0) {
            // 显示集数选择界面，让用户选择要生成哪一集
            await this.showEpisodeSelectionForGeneration(data);
            return;
        }

        // 使用智能解析器处理数据（单集结构）
        const parsed = this.parseVariousFormats(data);

        if (!parsed) {
            this.showToast('无法识别JSON格式，请点击「智能解析」尝试自动转换', 'error');
            return;
        }

        // 验证必填字段
        if (!parsed.title) {
            this.showToast('解析后缺少title字段', 'warning');
            return;
        }
        if (!parsed.description) {
            this.showToast('解析后缺少description字段', 'warning');
            return;
        }

        // 构建请求数据（单集）
        const requestData = {
            title: parsed.title,
            episode: parsed.episode || 1,
            description: parsed.description,
            style: parsed.style || '通用',
            shot_duration: parsed.shot_duration || 5,
            world_setting: parsed.world_setting || '',
            protagonist: parsed.protagonist || null,
            shots: parsed.shots || null  // 可选的完整分镜列表
        };

        await this.doCreateFromIdea(requestData);
    }

    /**
     * 显示集数选择界面（仅选择一集生成）
     */
    async showEpisodeSelectionForGeneration(data) {
        const modal = document.getElementById('ideaImportModal');
        const modalBody = modal.querySelector('.modal-body');
        const jsonArea = document.getElementById('jsonImportArea');

        // 保存原始内容
        if (!this.originalModalContent) {
            this.originalModalContent = jsonArea.innerHTML;
        }

        // 构建集数选择界面 - 单选模式
        let html = `
            <div class="episode-selection" style="padding: 1rem;">
                <h4 style="margin-bottom: 0.5rem;">📺 ${data.title}</h4>
                <p style="color: var(--text-secondary); font-size: 0.9rem;">${data.world_setting || ''}</p>
                <hr style="margin: 1rem 0; border-color: rgba(255,255,255,0.1);">
                <h5 style="margin-bottom: 1rem;">选择要生成的集数（单选）：</h5>
                <div class="episode-list" style="max-height: 300px; overflow-y: auto;">
        `;

        for (const ep of data.episodes) {
            const episodeNum = ep.episode || ep.ep;
            const episodeTitle = ep.episode_title || ep.title || `第${episodeNum}集`;
            const description = ep.description || ep.desc || ep.summary || '';

            html += `
                <div class="episode-option" style="
                    border: 2px solid rgba(99, 102, 241, 0.2);
                    border-radius: 8px;
                    padding: 12px;
                    margin-bottom: 10px;
                    cursor: pointer;
                    transition: all 0.2s;
                    background: rgba(0,0,0,0.2);
                " onclick="shortDramaStudio.selectEpisodeForGeneration(${episodeNum})" data-episode="${episodeNum}">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <input type="radio" name="selectedEpisode" value="${episodeNum}" style="width: 18px; height: 18px;">
                        <div style="flex: 1;">
                            <strong style="color: var(--primary);">第${episodeNum}集：${episodeTitle}</strong>
                            <div style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 4px;">${description.substring(0, 80)}${description.length > 80 ? '...' : ''}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        html += `
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                    <button class="btn btn-secondary" onclick="shortDramaStudio.cancelEpisodeSelection()">取消</button>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateSelectedEpisode()">生成该集</button>
                </div>
            </div>
        `;

        jsonArea.innerHTML = html;

        // 保存数据供后续使用
        this.multiEpisodeData = data;
        this.selectedEpisodeNum = null;
    }

    /**
     * 选择要生成的集
     */
    selectEpisodeForGeneration(episodeNum) {
        this.selectedEpisodeNum = episodeNum;
        // 更新UI显示
        document.querySelectorAll('.episode-option').forEach(el => {
            el.style.borderColor = 'rgba(99, 102, 241, 0.2)';
            el.style.background = 'rgba(0,0,0,0.2)';
        });
        const selected = document.querySelector(`.episode-option[data-episode="${episodeNum}"]`);
        if (selected) {
            selected.style.borderColor = 'var(--primary)';
            selected.style.background = 'rgba(99, 102, 241, 0.1)';
            selected.querySelector('input[type="radio"]').checked = true;
        }
    }

    /**
     * 取消集数选择
     */
    cancelEpisodeSelection() {
        const jsonArea = document.getElementById('jsonImportArea');
        if (this.originalModalContent) {
            jsonArea.innerHTML = this.originalModalContent;
            // 重新绑定事件
            document.getElementById('jsonImportInput')?.addEventListener('input', () => {
                this.validateJson();
            });
        }
        this.multiEpisodeData = null;
        this.selectedEpisodeNum = null;
    }

    /**
     * 生成选中的单集
     */
    async generateSelectedEpisode() {
        if (!this.multiEpisodeData) {
            this.showToast('数据丢失，请重新导入', 'error');
            return;
        }

        // 获取选中的集数
        const episodeNum = this.selectedEpisodeNum;
        if (!episodeNum) {
            this.showToast('请选择要生成的集数', 'warning');
            return;
        }

        const data = this.multiEpisodeData;
        const episode = data.episodes.find(ep => (ep.episode || ep.ep) === episodeNum);
        if (!episode) {
            this.showToast(`未找到第${episodeNum}集数据`, 'error');
            return;
        }

        // 构建请求数据
        const requestData = {
            title: data.title,
            episode: episodeNum,
            description: episode.description || episode.desc || episode.summary || '',
            world_setting: data.world_setting || data.world || '',
            style: data.style || '通用',
            shot_duration: episode.shot_duration || data.shot_duration || 5,
            protagonist: data.protagonist || null,
            shots: episode.shots || null,
            // 新版格式字段
            episode_title: episode.episode_title || episode.title || `第${episodeNum}集`,
            plot_structure: episode.plot_structure || null,
            key_scenes: episode.key_scenes || null,
            character_arc: episode.character_arc || '',
            logline: episode.logline || '',
            theme: episode.theme || ''
        };

        // 关闭选择界面
        this.cancelEpisodeSelection();

        // 调用单集生成
        await this.doCreateFromIdea(requestData);
    }

    /**
     * 执行创意导入请求
     */
    async doCreateFromIdea(requestData) {
        // 显示加载状态
        const submitBtn = document.querySelector('#ideaImportModal .btn-primary');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = '🔄 生成中...';
        submitBtn.disabled = true;

        try {
            const response = await fetch('/api/short-drama/create-from-idea', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            const data = await response.json();

            if (data.success) {
                this.showToast(`第${requestData.episode}集分镜头生成成功！`, 'success');
                this.closeIdeaModal();

                // 重新加载项目列表
                await this.loadProjects();

                // 打开新创建的项目
                const newProject = this.projects.find(p => p.title === requestData.title);
                if (newProject) {
                    await this.openProject(newProject.id);
                }
            } else {
                this.showToast(data.error || '生成失败', 'error');
            }
        } catch (error) {
            console.error('创意导入失败:', error);
            this.showToast('创意导入失败', 'error');
        } finally {
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    }

    /**
     * 从创意启动工作流（直接跳到分镜头预览）
     */
    async startWorkflowFromIdea(title) {
        console.log('📝 [工作流] 从创意启动:', title);

        this.selectedNovel = title;

        // 查找项目
        const existingProject = this.projects.find(p => p.title === title);
        if (existingProject) {
            this.currentProject = existingProject;
            this.loadProjectSettings(existingProject.settings);
        } else {
            this.currentProject = { title };
        }

        // 切换到工作区视图
        document.getElementById('projectListView').classList.remove('active');
        document.getElementById('projectWorkspaceView').classList.add('active');
        document.getElementById('currentProjectName').textContent = `📺 ${title} - 创意导入`;

        // 直接跳到分镜头步骤（跳过选事件步骤）
        this.goToStep('storyboard');
    }

    /**
     * 切换项目列表区域的折叠状态
     */




    /**
     * 检查是否有参考图
     */
    hasReferenceImages() {
        return this.currentProject?.characters?.some(char => char.portrait_url || char.reference_image) || false;
    }

    /**
     * 获取视频设置
     */
    getVideoSettings() {
        const sbFirstLastFrame = document.getElementById('sbUseFirstLastFrame');
        const sbReferenceImage = document.getElementById('sbUseReferenceImage');
        
        if (sbFirstLastFrame || sbReferenceImage) {
            return {
                useFirstLastFrame: sbFirstLastFrame?.checked || false,
                hasReferenceImages: sbReferenceImage?.checked || false
            };
        }
        
        return {
            useFirstLastFrame: document.getElementById('settingFirstLastFrame')?.checked || false,
            hasReferenceImages: this.hasReferenceImages()
        };
    }

    /**
     * 加载分镜步骤
     */

    /**
     * 生成分镜头（手动触发）
     */

    /**
     * 渲染分镜头列表
     */

    /**
     * 切换提示词模式
     */
    switchPromptMode(shotId) {
        const select = document.getElementById(`mode-select-${shotId}`);
        const mode = select.value;
        const dataDiv = document.getElementById(`shot-data-${shotId}`);
        const visualDescText = document.getElementById(`visual-desc-text-${shotId}`);
        const veoPromptText = document.getElementById(`veo-prompt-${shotId}`);
        
        visualDescText.textContent = dataDiv.getAttribute(`data-${mode}`);
        veoPromptText.textContent = dataDiv.getAttribute(`data-prompt-${mode}`);
        
        const shot = this.currentProject?.shots?.find(s => (s.id || '').toString() === shotId.toString());
        if (shot) {
            shot.preferred_mode = mode;
        }
    }

    /**
     * 保存镜头模式
     */

    /**
     * 复制到剪贴板
     */
    copyToClipboard(text) {
        if (!text) return;
        const textarea = document.createElement('textarea');
        textarea.innerHTML = text;
        const decodedText = textarea.value;
        
        navigator.clipboard.writeText(decodedText).then(() => {
            this.showToast('已复制到剪贴板', 'success');
        }).catch(err => {
            console.error('复制失败:', err);
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            this.showToast('已复制到剪贴板', 'success');
        });
    }

    // ==================== 角色剧照无限画布方法 ====================

    /**
     * 初始化角色剧照无限画布
     */
    initPortraitCanvas(characters) {
        if (typeof Konva === 'undefined') {
            console.warn('⚠️ Konva.js 未加载，跳过画布初始化');
            return;
        }

        const container = document.getElementById('portrait-konva-container');
        if (!container) {
            console.warn('⚠️ 找不到画布容器');
            return;
        }

        // 如果已有舞台，先清空
        if (this.portraitStage) {
            this.portraitStage.destroy();
            this.portraitStage = null;
        }

        const { width, height } = container.getBoundingClientRect();

        // 创建舞台
        this.portraitStage = new Konva.Stage({
            container: 'portrait-konva-container',
            width: width,
            height: height,
            draggable: false
        });

        // 创建主图层
        this.portraitLayer = new Konva.Layer();
        this.portraitStage.add(this.portraitLayer);

        // 创建变换器
        this.portraitTransformer = new Konva.Transformer({
            borderStroke: '#6366f1',
            borderStrokeWidth: 2,
            anchorStroke: '#6366f1',
            anchorFill: '#0f172a',
            anchorSize: 8,
            padding: 4,
            keepRatio: true,
            enabledAnchors: ['top-left', 'top-right', 'bottom-left', 'bottom-right']
        });
        this.portraitLayer.add(this.portraitTransformer);

        // 创建格子背景
        this.createPortraitGridBackground();

        // 绑定事件
        this.bindPortraitCanvasEvents();

        // 渲染角色到画布
        this.renderCharactersToCanvas(characters);

        // 初始化工具栏
        this.initPortraitToolbar();

        console.log('✅ [角色剧照画布] 初始化完成');
    }

    /**
     * 创建格子背景
     */
    createPortraitGridBackground() {
        const gridLayer = new Konva.Layer();
        const gridSize = 50;
        const stageWidth = 3000;
        const stageHeight = 2000;

        // 垂直线
        for (let x = 0; x <= stageWidth; x += gridSize) {
            gridLayer.add(new Konva.Line({
                points: [x, 0, x, stageHeight],
                stroke: 'rgba(99, 102, 241, 0.1)',
                strokeWidth: 1
            }));
        }

        // 水平线
        for (let y = 0; y <= stageHeight; y += gridSize) {
            gridLayer.add(new Konva.Line({
                points: [0, y, stageWidth, y],
                stroke: 'rgba(99, 102, 241, 0.1)',
                strokeWidth: 1
            }));
        }

        // 三大区域标记
        const regions = [
            { x: 500, y: 200, name: '🎭 角色区', color: 'rgba(236, 72, 153, 0.15)' },
            { x: 1500, y: 200, name: '🏞 ️场景区', color: 'rgba(34, 197, 94, 0.15)' },
            { x: 2500, y: 200, name: '🎒 道具区', color: 'rgba(245, 158, 11, 0.15)' }
        ];

        regions.forEach(region => {
            gridLayer.add(new Konva.Rect({
                x: region.x - 400,
                y: region.y - 150,
                width: 800,
                height: 1700,
                fill: region.color,
                stroke: region.color.replace('0.15', '0.3'),
                strokeWidth: 2,
                cornerRadius: 12
            }));

            gridLayer.add(new Konva.Text({
                x: region.x,
                y: region.y - 120,
                text: region.name,
                fontSize: 24,
                fontStyle: 'bold',
                fill: 'rgba(255, 255, 255, 0.6)',
                align: 'center'
            }));
        });

        this.portraitStage.add(gridLayer);
        gridLayer.moveToBottom();

        // 居中显示
        const container = document.getElementById('portrait-konva-container');
        const viewWidth = container.offsetWidth;
        const viewHeight = container.offsetHeight;
        
        this.portraitStage.x((viewWidth - stageWidth) / 2);
        this.portraitStage.y((viewHeight - stageHeight) / 2);
    }

    /**
     * 渲染角色到画布
     */
    renderCharactersToCanvas(characters) {
        // 🔥 如果没有传入角色数组，尝试从 visualAssets 获取
        if (!characters || characters.length === 0) {
            const visualAssetChars = this.currentProject?.visualAssets?.characters;
            if (visualAssetChars && Object.keys(visualAssetChars).length > 0) {
                characters = Object.entries(visualAssetChars).map(([name, data]) => ({
                    name: name,
                    ...data
                }));
                console.log('🎭 [画布] 从 visualAssets 加载角色:', characters.length);
            } else {
                console.log('🎭 [画布] 没有角色可渲染');
                return;
            }
        }

        // 角色区起始位置
        let startX = 200;
        let startY = 300;
        const gapX = 220;
        const gapY = 320;
        const perRow = 3;

        characters.forEach((char, idx) => {
            const charName = char.name || `角色${idx + 1}`;
            
            // 🔥 查找剧照 - 优先从 visualAssets 获取新生成的图片
            let portraitUrl = null;
            const visualAsset = this.currentProject?.visualAssets?.characters?.[charName];
            if (visualAsset?.referenceUrl) {
                // 优先使用 visualAssets 中的新生成图片
                portraitUrl = visualAsset.referenceUrl;
            } else {
                // 回退到 characterPortraits
                const portraitInfo = this.characterPortraits.get(charName);
                if (portraitInfo?.mainPortrait) {
                    portraitUrl = portraitInfo.mainPortrait.url;
                }
            }

            // 计算位置（网格布局）
            const row = Math.floor(idx / perRow);
            const col = idx % perRow;
            const x = startX + col * gapX;
            const y = startY + row * gapY;

            // 创建角色卡片组
            this.createCharacterCard(charName, char, portraitUrl, x, y);
        });

        this.portraitLayer.batchDraw();
    }

    /**
     * 创建角色卡片
     */
    createCharacterCard(name, charData, imageUrl, x, y) {
        const group = new Konva.Group({
            x: x,
            y: y,
            draggable: true,
            name: 'character-card'
        });

        // 卡片背景
        const cardWidth = 180;
        const cardHeight = imageUrl ? 260 : 120;

        group.add(new Konva.Rect({
            width: cardWidth,
            height: cardHeight,
            fill: 'rgba(30, 41, 59, 0.9)',
            stroke: 'rgba(99, 102, 241, 0.3)',
            strokeWidth: 1,
            cornerRadius: 12,
            shadowColor: 'rgba(0, 0, 0, 0.3)',
            shadowBlur: 10,
            shadowOffset: { x: 0, y: 4 }
        }));

        if (imageUrl) {
            // 有剧照 - 加载图片
            const imageObj = new Image();
            imageObj.onload = () => {
                const imgHeight = 180;
                const img = new Konva.Image({
                    x: 10,
                    y: 10,
                    image: imageObj,
                    width: cardWidth - 20,
                    height: imgHeight,
                    cornerRadius: 8
                });
                group.add(img);

                // 角色名
                group.add(new Konva.Text({
                    x: 10,
                    y: imgHeight + 20,
                    text: name,
                    fontSize: 14,
                    fontStyle: 'bold',
                    fill: '#f1f5f9',
                    width: cardWidth - 20,
                    ellipsis: true
                }));

                // 角色角色
                if (charData.role) {
                    group.add(new Konva.Text({
                        x: 10,
                        y: imgHeight + 40,
                        text: charData.role,
                        fontSize: 11,
                        fill: '#94a3b8',
                        width: cardWidth - 20
                    }));
                }

                this.portraitLayer.batchDraw();
            };

            // 🔥 添加错误处理
            imageObj.onerror = () => {
                console.error('❌ [画布] 图片加载失败:', imageUrl);
                // 显示占位符
                group.add(new Konva.Rect({
                    x: 10,
                    y: 10,
                    width: cardWidth - 20,
                    height: 180,
                    fill: 'rgba(239, 68, 68, 0.1)',
                    stroke: 'rgba(239, 68, 68, 0.3)',
                    strokeWidth: 1,
                    cornerRadius: 8
                }));

                group.add(new Konva.Text({
                    x: 0,
                    y: 90,
                    text: '❌',
                    fontSize: 32,
                    fill: '#ef4444',
                    width: cardWidth,
                    align: 'center'
                }));

                group.add(new Konva.Text({
                    x: 10,
                    y: 200,
                    text: name,
                    fontSize: 14,
                    fontStyle: 'bold',
                    fill: '#f1f5f9',
                    width: cardWidth - 20,
                    ellipsis: true
                }));

                this.portraitLayer.batchDraw();
            };

            imageObj.src = imageUrl;
        } else {
            // 无剧照 - 显示占位符
            group.add(new Konva.Rect({
                x: 10,
                y: 10,
                width: cardWidth - 20,
                height: 60,
                fill: 'rgba(99, 102, 241, 0.1)',
                cornerRadius: 8
            }));

            group.add(new Konva.Text({
                x: 0,
                y: 35,
                text: '👤',
                fontSize: 24,
                fill: '#64748b',
                width: cardWidth,
                align: 'center'
            }));

            group.add(new Konva.Text({
                x: 10,
                y: 80,
                text: name,
                fontSize: 14,
                fontStyle: 'bold',
                fill: '#f1f5f9',
                width: cardWidth - 20,
                ellipsis: true
            }));

            group.add(new Konva.Text({
                x: 10,
                y: 100,
                text: '点击生成剧照',
                fontSize: 11,
                fill: '#6366f1',
                width: cardWidth - 20
            }));
        }

        // 添加点击事件
        group.on('click tap', () => {
            this.selectPortraitCard(group);
        });

        group.on('dblclick dbltap', () => {
            // 双击打开生成/查看剧照
            const portraitInfo = this.characterPortraits.get(name);
            if (portraitInfo) {
                this.viewPortrait(name);
            } else {
                this.generatePortrait(name);
            }
        });

        // 拖拽事件
        group.on('dragstart', () => {
            group.shadowBlur(20);
        });

        group.on('dragend', () => {
            group.shadowBlur(10);
        });

        // 存储元数据
        group.setAttr('meta', {
            name: name,
            charData: charData,
            hasPortrait: !!imageUrl
        });

        this.portraitLayer.add(group);
        this.portraitCanvasItems.push(group);
    }

    /**
     * 刷新画布显示（重新渲染所有角色）
     */
    refreshPortraitCanvas() {
        if (!this.portraitStage || !this.portraitLayer) return;
        
        console.log('🎨 [画布] 刷新角色显示');
        
        // 清除现有角色卡片（保留网格背景）
        const charactersToRemove = [];
        this.portraitLayer.children.forEach(child => {
            if (child.hasName('character-card')) {
                charactersToRemove.push(child);
            }
        });
        charactersToRemove.forEach(child => child.destroy());
        
        // 清空变换器
        this.portraitTransformer.nodes([]);
        
        // 重新渲染角色
        this.renderCharactersToCanvas(this.characters);
        
        this.portraitLayer.batchDraw();
    }

    /**
     * 绑定画布事件
     */
    bindPortraitCanvasEvents() {
        const stage = this.portraitStage;
        const container = document.getElementById('portrait-konva-container');

        // 滚轮缩放（使用 passive: false 因为我们确实需要阻止默认滚动行为）
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            
            const oldScale = stage.scaleX();
            const pointer = stage.getPointerPosition();
            
            const mousePointTo = {
                x: (pointer.x - stage.x()) / oldScale,
                y: (pointer.y - stage.y()) / oldScale
            };

            const zoomDirection = e.deltaY > 0 ? -1 : 1;
            const newScale = Math.max(0.3, Math.min(2, oldScale + zoomDirection * 0.1));

            stage.scale({ x: newScale, y: newScale });
            
            const newPos = {
                x: pointer.x - mousePointTo.x * newScale,
                y: pointer.y - mousePointTo.y * newScale
            };
            
            stage.position(newPos);
            this.portraitScale = newScale;
            this.updatePortraitZoomDisplay();
            
            stage.batchDraw();
        }, { passive: false });

        // 鼠标事件用于平移
        let isPanning = false;
        let lastPos = { x: 0, y: 0 };

        stage.on('mousedown', (e) => {
            if (e.target === stage || e.target.hasName('grid-bg')) {
                isPanning = true;
                lastPos = { x: e.evt.clientX, y: e.evt.clientY };
                container.classList.add('panning');
            } else {
                // 点击空白处取消选择
                this.portraitTransformer.nodes([]);
            }
        });

        stage.on('mousemove', (e) => {
            if (isPanning) {
                const dx = e.evt.clientX - lastPos.x;
                const dy = e.evt.clientY - lastPos.y;
                
                stage.x(stage.x() + dx);
                stage.y(stage.y() + dy);
                
                lastPos = { x: e.evt.clientX, y: e.evt.clientY };
                stage.batchDraw();
            }
        });

        stage.on('mouseup', () => {
            isPanning = false;
            container.classList.remove('panning');
        });
    }

    /**
     * 选中卡片
     */
    selectPortraitCard(group) {
        this.portraitTransformer.nodes([group]);
        this.portraitTransformer.moveToTop();
        this.portraitLayer.batchDraw();
    }

    /**
     * 初始化工具栏
     */
    initPortraitToolbar() {
        // 工具切换
        document.getElementById('pc-tool-select')?.addEventListener('click', () => {
            this.setPortraitTool('select');
        });

        document.getElementById('pc-tool-hand')?.addEventListener('click', () => {
            this.setPortraitTool('hand');
        });

        document.getElementById('pc-tool-fit')?.addEventListener('click', () => {
            this.fitPortraitCanvas();
        });

        document.getElementById('pc-tool-export')?.addEventListener('click', () => {
            this.exportPortraitCanvas();
        });

        // 缩放控制
        document.getElementById('pc-zoom-in')?.addEventListener('click', () => {
            this.zoomPortraitCanvas(0.2);
        });

        document.getElementById('pc-zoom-out')?.addEventListener('click', () => {
            this.zoomPortraitCanvas(-0.2);
        });
    }

    /**
     * 设置工具
     */
    setPortraitTool(tool) {
        document.querySelectorAll('.pc-tool-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`pc-tool-${tool}`)?.classList.add('active');
        
        const container = document.getElementById('portrait-konva-container');
        if (tool === 'hand') {
            container.style.cursor = 'grab';
        } else {
            container.style.cursor = 'default';
        }
    }

    /**
     * 适应画布
     */
    fitPortraitCanvas() {
        if (!this.portraitStage) return;
        
        const stage = this.portraitStage;
        const container = document.getElementById('portrait-konva-container');
        
        stage.scale({ x: 0.5, y: 0.5 });
        stage.position({
            x: (container.offsetWidth - 3000 * 0.5) / 2,
            y: (container.offsetHeight - 2000 * 0.5) / 2
        });
        
        this.portraitScale = 0.5;
        this.updatePortraitZoomDisplay();
        stage.batchDraw();
    }

    /**
     * 缩放画布
     */
    zoomPortraitCanvas(delta) {
        if (!this.portraitStage) return;
        
        const stage = this.portraitStage;
        const oldScale = stage.scaleX();
        const newScale = Math.max(0.3, Math.min(2, oldScale + delta));
        
        const center = {
            x: stage.width() / 2,
            y: stage.height() / 2
        };
        
        const mousePointTo = {
            x: (center.x - stage.x()) / oldScale,
            y: (center.y - stage.y()) / oldScale
        };
        
        stage.scale({ x: newScale, y: newScale });
        stage.position({
            x: center.x - mousePointTo.x * newScale,
            y: center.y - mousePointTo.y * newScale
        });
        
        this.portraitScale = newScale;
        this.updatePortraitZoomDisplay();
        stage.batchDraw();
    }

    /**
     * 更新缩放显示
     */
    updatePortraitZoomDisplay() {
        const percentage = Math.round(this.portraitScale * 100);
        const zoomValue = document.getElementById('pc-zoom-value');
        if (zoomValue) {
            zoomValue.textContent = percentage + '%';
        }
    }

    /**
     * 导出画布
     */
    exportPortraitCanvas() {
        if (!this.portraitStage) return;
        
        // 隐藏变换器
        this.portraitTransformer.visible(false);
        this.portraitLayer.batchDraw();
        
        const dataURL = this.portraitStage.toDataURL({
            pixelRatio: 2,
            x: 0,
            y: 0,
            width: 3000,
            height: 2000
        });
        
        this.portraitTransformer.visible(true);
        this.portraitLayer.batchDraw();
        
        const link = document.createElement('a');
        link.download = `角色剧照画布_${new Date().toISOString().slice(0, 10)}.png`;
        link.href = dataURL;
        link.click();
    }

    /**
     * 重新生成视觉资产
     */
    async regenerateVisualAssets() {
        if (!this.currentProject) {
            this.showToast('请先选择项目', 'warning');
            return;
        }

        // 获取项目名称（novel）
        const novel = this.currentProject.title;

        // 获取当前选中的集（episode）
        let episode = null;
        if (this.selectedEpisodes && this.selectedEpisodes.length > 0) {
            episode = this.selectedEpisodes[0];
        }

        if (!novel) {
            this.showToast('项目信息不完整', 'error');
            console.error('项目信息:', { novel, currentProject: this.currentProject });
            return;
        }

        // 🔥 构建确认消息
        let confirmMsg = `确定要重新生成视觉资产吗？\n项目: ${novel}`;
        if (episode) {
            confirmMsg += `\n集数: ${episode}`;
        } else {
            confirmMsg += `\n集数: 自动检测`;
        }
        confirmMsg += `\n\n这将覆盖现有的视觉资产数据。`;

        // 确认对话框
        if (!confirm(confirmMsg)) {
            return;
        }

        try {
            this.showToast('🔄 正在重新生成视觉资产...', 'info');

            // 🔥 构建请求体，如果没有 episode 则不传，让后端自动检测
            const requestBody = { novel: novel };
            if (episode) {
                requestBody.episode = episode;
            }

            const response = await fetch('/api/short-drama/visual-assets/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`✅ 视觉资产重新生成成功！角色: ${result.stats.characters}, 场景: ${result.stats.scenes}, 道具: ${result.stats.props}`, 'success');

                // 刷新画布（如果函数存在）
                if (typeof this.loadCharacterPortraitsStep === 'function') {
                    this.loadCharacterPortraitsStep();
                }
            } else {
                // 🔥 改进错误提示，引导用户完成前置步骤
                let errorMsg = result.error || '未知错误';
                if (errorMsg.includes('分镜头文件') || errorMsg.includes('集数')) {
                    errorMsg += ' 💡提示：视觉资产是从分镜头数据中提取的，请先完成【分镜生成】步骤。';
                }
                this.showToast(`❌ 重新生成失败: ${errorMsg}`, 'error');
            }
        } catch (error) {
            console.error('重新生成视觉资产失败:', error);
            this.showToast(`❌ 重新生成失败: ${error.message}`, 'error');
        }
    }

    /**
     * 重新生成帧序列
     */
    async regenerateFrameSequences() {
        if (!this.currentProject) {
            this.showToast('请先选择项目', 'warning');
            return;
        }

        // 获取项目名称（novel）
        const novel = this.currentProject.title;

        // 获取当前选中的集（episode）
        let episode = null;
        if (this.selectedEpisodes && this.selectedEpisodes.length > 0) {
            episode = this.selectedEpisodes[0];
        }

        if (!novel || !episode) {
            this.showToast(`项目信息不完整: novel=${novel}, episode=${episode}`, 'error');
            console.error('项目信息:', { novel, episode, currentProject: this.currentProject, selectedEpisodes: this.selectedEpisodes });
            return;
        }

        // 确认对话框
        if (!confirm(`确定要重新生成帧序列吗？\n项目: ${novel}\n集数: ${episode}\n\n这将覆盖现有的帧序列数据。`)) {
            return;
        }

        try {
            this.showToast('🔄 正在重新生成帧序列...', 'info');

            const response = await fetch('/api/short-drama/frame-sequences/regenerate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    novel: novel,
                    episode: episode
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`✅ 帧序列重新生成成功！共 ${result.stats.total_shots} 个镜头`, 'success');
            } else {
                this.showToast(`❌ 重新生成失败: ${result.error}`, 'error');
            }
        } catch (error) {
            console.error('重新生成帧序列失败:', error);
            this.showToast(`❌ 重新生成失败: ${error.message}`, 'error');
        }
    }

    /**
     * 切换侧边栏显示/隐藏
     */
    togglePanel(side) {
        const panel = side === 'left' ? document.getElementById('leftPanel') : document.getElementById('rightPanel');
        const toggleBtn = side === 'left' ? document.getElementById('toggleLeftPanel') : document.getElementById('toggleRightPanel');

        if (!panel || !toggleBtn) return;

        const isCollapsed = panel.style.width === '0px' || panel.style.width === '';

        if (isCollapsed) {
            // 展开
            panel.style.width = side === 'left' ? '240px' : '280px';
            panel.style.opacity = '1';
            panel.style.pointerEvents = 'auto';
            toggleBtn.querySelector('span').textContent = side === 'left' ? '◀' : '▶';

            // 保存状态到localStorage
            localStorage.setItem(`panel_${side}_collapsed`, 'false');
        } else {
            // 收缩
            panel.style.width = '0px';
            panel.style.opacity = '0';
            panel.style.pointerEvents = 'none';
            toggleBtn.querySelector('span').textContent = side === 'left' ? '▶' : '◀';

            // 保存状态到localStorage
            localStorage.setItem(`panel_${side}_collapsed`, 'true');
        }

        // 调整画布大小（如果Konva画布存在）
        setTimeout(() => {
            if (this.portraitStage) {
                const container = document.getElementById('portraitCanvasContainer');
                if (container) {
                    this.portraitStage.width(container.offsetWidth);
                    this.portraitStage.height(container.offsetHeight);
                    this.portraitStage.batchDraw();
                }
            }
        }, 300); // 等待CSS过渡完成
    }

    /**
     * 恢复侧边栏状态
     */
    restorePanelStates() {
        // 恢复左侧面板状态
        const leftCollapsed = localStorage.getItem('panel_left_collapsed') === 'true';
        if (leftCollapsed) {
            this.togglePanel('left');
        }

        // 恢复右侧面板状态
        const rightCollapsed = localStorage.getItem('panel_right_collapsed') === 'true';
        if (rightCollapsed) {
            this.togglePanel('right');
        }
    }
}

// 🔥 混入模块功能
if (typeof UtilsMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, UtilsMixin);
    console.log('✅ [模块] Utils 模块已加载');
}

if (typeof ExportMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, ExportMixin);
    console.log('✅ [模块] Export 模块已加载');
}

if (typeof StoryBeatsMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, StoryBeatsMixin);
    console.log('✅ [模块] StoryBeats 模块已加载');
}

if (typeof EpisodeSelectorMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, EpisodeSelectorMixin);
    console.log('✅ [模块] EpisodeSelector 模块已加载');
}

if (typeof DubbingMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, DubbingMixin);
    console.log('✅ [模块] Dubbing 模块已加载');
}

if (typeof VisualAssetsMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, VisualAssetsMixin);
    console.log('✅ [模块] VisualAssets 模块已加载');
}

if (typeof StoryboardMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, StoryboardMixin);
    console.log('✅ [模块] Storyboard 模块已加载');
}

if (typeof ProjectManagerMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, ProjectManagerMixin);
    console.log('✅ [模块] ProjectManager 模块已加载');
}

if (typeof ImageGenerationMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, ImageGenerationMixin);
    console.log('✅ [模块] ImageGeneration 模块已加载');
}

if (typeof VideoGenerationMixin !== 'undefined') {
    Object.assign(ShortDramaStudio.prototype, VideoGenerationMixin);
    console.log('✅ [模块] VideoGeneration 模块已加载');
}

// 初始化
const shortDramaStudio = new ShortDramaStudio();
// 暴露到全局作用域供inline onclick使用
window.shortDramaStudio = shortDramaStudio;
