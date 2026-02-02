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
        this.characterVoices = {}; // 配音音色映射
        this.selectedNovel = null;
        this.selectedMajorEvent = null;
        this.selectedEpisodes = []; // 🔥 改为数组以保持选择顺序
        this.characterPortraits = new Map();
        this.shots = [];
        this.stopBatchGeneration = false;
        this._improvedData = null; // 用于存储剧本改进数据

        // 后台任务跟踪
        this.backgroundTasks = new Map(); // taskId -> { shotIndex, shot, startTime, progress, status }

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

        // 新建项目按钮
        document.getElementById('createProjectBtn')?.addEventListener('click', () => {
            this.createNewProject();
        });

        // 从小说创建按钮
        document.getElementById('createFromNovelBtn')?.addEventListener('click', () => {
            this.createFromNovel();
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

        // 监听从剧照工作室返回
        window.addEventListener('storage', (e) => {
            if (e.key === 'portraitStudio_result' && e.newValue) {
                console.log('📸 检测到剧照已保存，刷新角色剧照列表');
                this.loadCharacterPortraitsStep();
            }
        });

        // 页面重新可见时刷新剧照
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && this.currentStep === 'check-portraits') {
                console.log('📸 页面重新可见，刷新角色剧照列表');
                this.loadCharacterPortraitsStep();
            }
        });
    }

    /**
     * 加载项目列表
     */
    async loadProjects() {
        try {
            const response = await fetch('/api/short-drama/projects');
            const data = await response.json();

            if (data.success) {
                this.projects = data.projects || [];
                this.renderProjectsList();
            }
        } catch (error) {
            console.error('加载项目失败:', error);
        }
    }

    /**
     * 渲染项目列表
     */
    renderProjectsList() {
        const container = document.getElementById('projectsList');

        if (this.projects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">📭</p>
                    <p>还没有项目</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        从小说创建项目，或新建空项目
                    </p>
                </div>
            `;
            return;
        }

        // 按标题分组，检测重复项目
        const grouped = {};
        this.projects.forEach(project => {
            if (!grouped[project.title]) {
                grouped[project.title] = [];
            }
            grouped[project.title].push(project);
        });

        container.innerHTML = `
            <div class="projects-grid">
                ${this.projects.map(project => {
                    const duplicates = grouped[project.title] || [];
                    const isDuplicate = duplicates.length > 1;

                    return `
                    <div class="project-card" onclick="shortDramaStudio.openProject('${project.id}')">
                        <div class="project-card-header">
                            <div class="project-card-title">${project.title}</div>
                            ${isDuplicate ? '<span class="project-card-badge pending">重复</span>' : ''}
                        </div>
                        <div class="project-card-meta">
                            <span>📊 ${project.episodes_count || 0}集</span>
                            <span>👥 ${project.characters_count || 0}角色</span>
                        </div>
                        <div class="project-card-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${project.progress || 0}%"></div>
                            </div>
                            <div class="project-card-stats">
                                <span>进度: ${project.progress || 0}%</span>
                            </div>
                        </div>
                        <div class="project-card-actions">
                            <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); shortDramaStudio.openProject('${project.id}')">打开</button>
                            <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); shortDramaStudio.deleteProject('${project.id}')" style="color: var(--danger);">删除</button>
                        </div>
                    </div>
                `}).join('')}
            </div>
        `;
    }

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
        document.getElementById('projectListView').classList.remove('active');
        document.getElementById('projectWorkspaceView').classList.add('active');
        document.getElementById('currentProjectName').textContent = `📺 ${novelTitle} - 按集制作`;

        // 加载重大事件
        await this.loadMajorEvents();

        // 显示第一步
        this.goToStep('select-episodes');
    }

    /**
     * 加载事件和角色数据
     */
    async loadEventsAndCharacters() {
        try {
            // 加载事件数据
            const eventsResponse = await fetch(`/api/video/novel-content?title=${encodeURIComponent(this.selectedNovel)}`);
            const eventsData = await eventsResponse.json();

            console.log('📊 API 返回数据:', eventsData);

            if (eventsData.success) {
                // 构建事件树
                this.events = this.buildEventTree(eventsData);
                console.log('✅ [工作流] 加载事件:', this.events.length);

                // 加载角色数据
                if (eventsData.characters && Array.isArray(eventsData.characters)) {
                    this.characters = eventsData.characters;
                    console.log('✅ [工作流] 加载角色:', this.characters.length);
                }
            } else {
                console.error('❌ 加载事件失败:', eventsData.error);
                this.showToast(eventsData.error || '加载数据失败', 'error');
            }
        } catch (error) {
            console.error('加载数据失败:', error);
            this.showToast('加载数据失败', 'error');
        }
    }

    /**
     * 构建事件树
     */
    buildEventTree(data) {
        const events = [];

        // 从数据中提取事件 - API返回的是events字段
        const eventData = data.events || [];

        eventData.forEach((major, idx) => {
            events.push({
                id: major.id || `major_${idx}`,
                title: major.title || major.name,
                name: major.title || major.name,
                type: 'major',
                description: major.description || '',
                stage: major.stage,
                children: major.children || [],
                children_count: major.children_count || (major.children || []).length,
                has_children: major.has_children,
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

        container.innerHTML = this.events.map((event, idx) => `
            <div class="major-event-option" data-event-id="${event.id}">
                <div class="event-name">${event.title}</div>
                <div class="event-info">
                    <span class="episode-count">${event.children_count}集</span>
                    ${event.description ? `<span>${event.description.substring(0, 50)}...</span>` : ''}
                </div>
            </div>
        `).join('');
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
        document.querySelectorAll('.major-event-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        const selectedOption = document.querySelector(`.major-event-option[data-event-id="${eventId}"]`);
        if (selectedOption) {
            selectedOption.classList.add('selected');
        }

        // 显示集数列表
        this.showEpisodeList(event);
    }

    /**
     * 显示集数列表
     */
    showEpisodeList(majorEvent) {
        const panel = document.getElementById('episodeSelectorPanel');
        const container = document.getElementById('episodeList');
        const nameSpan = document.getElementById('selectedMajorEventNameTitle');

        if (nameSpan) nameSpan.textContent = majorEvent.title;
        if (panel) panel.style.display = 'block';

        const episodes = majorEvent.children || [];

        if (episodes.length === 0) {
            if (container) {
                container.innerHTML = `
                    <div class="empty-state" style="grid-column: 1 / -1;">
                        <p>该重大事件下没有中级事件</p>
                    </div>
                `;
            }
            return;
        }

        if (container) {
            container.innerHTML = episodes.map((ep, idx) => {
                // 🔥 使用后端生成的事件ID（后端已经计算好了正确的ID格式）
                const epId = ep.id || `episode_${idx}`;
                const isChecked = this.selectedEpisodes.includes(epId) ? 'checked' : '';
                const selectedClass = this.selectedEpisodes.includes(epId) ? 'selected' : '';

                return `
                    <div class="episode-item ${selectedClass}" data-episode-id="${epId}">
                        <input type="checkbox" class="episode-checkbox" id="ep_${idx}" ${isChecked}>
                        <span class="episode-number">第${idx + 1}集</span>
                        <div class="episode-info">
                            <span class="episode-title">${ep.title || ep.name || `集数 ${idx + 1}`}</span>
                            <span class="episode-stage">${ep.stage || ''}</span>
                        </div>
                    </div>
                `;
            }).join('');

            // 默认全选（如果还没有选中任何集数）
            if (this.selectedEpisodes.length === 0) {
                this.selectAllEpisodes(true);
            }
        }
    }

    /**
     * 切换集数选择状态
     */
    toggleEpisodeSelection(episodeId, selected) {
        if (selected) {
            if (!this.selectedEpisodes.includes(episodeId)) {
                this.selectedEpisodes.push(episodeId);
            }
        } else {
            const index = this.selectedEpisodes.indexOf(episodeId);
            if (index > -1) {
                this.selectedEpisodes.splice(index, 1);
            }
        }

        // 更新选中项样式和复选框状态
        const item = document.querySelector(`.episode-item[data-episode-id="${episodeId}"]`);
        if (item) {
            item.classList.toggle('selected', selected);
            const checkbox = item.querySelector('.episode-checkbox');
            if (checkbox) {
                checkbox.checked = selected;
            }
        }

        // 更新计数
        const countSpan = document.getElementById('selectedEpisodesCount');
        if (countSpan) {
            countSpan.textContent = this.selectedEpisodes.length;
        }

        // 更新项目状态
        this.updateProjectStatus();
    }

    /**
     * 全选/清空集数
     */
    selectAllEpisodes(selectAll) {
        document.querySelectorAll('.episode-item').forEach(item => {
            const episodeId = item.dataset.episodeId;
            const checkbox = item.querySelector('.episode-checkbox');

            // 更新数据
            if (selectAll) {
                if (!this.selectedEpisodes.includes(episodeId)) {
                    this.selectedEpisodes.push(episodeId);
                }
            } else {
                const index = this.selectedEpisodes.indexOf(episodeId);
                if (index > -1) {
                    this.selectedEpisodes.splice(index, 1);
                }
            }

            // 更新UI
            item.classList.toggle('selected', selectAll);
            if (checkbox) {
                checkbox.checked = selectAll;
            }
        });

        // 更新计数
        const countSpan = document.getElementById('selectedEpisodesCount');
        if (countSpan) {
            countSpan.textContent = this.selectedEpisodes.length;
        }

        // 更新项目状态
        this.updateProjectStatus();
    }

    /**
     * 切换工作流步骤
     */
    goToStep(step, forceReload = false) {
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

        // 视频生成模式下隐藏侧边栏
        const workspace = document.querySelector('.workspace-content');
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
                    this.loadCharacterPortraitsStep();
                    this.loadedSteps.add('check-portraits');
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
     * 加载角色剧照步骤
     */
    async loadCharacterPortraitsStep() {
        try {
            const container = document.getElementById('charactersGrid');
            if (!container) {
                console.error('❌ 找不到 charactersGrid 容器');
                return;
            }

            container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>加载角色信息...</p></div>';

            // 如果角色还没加载，先加载角色数据
            if (!this.characters || this.characters.length === 0) {
                console.log('🎭 [角色剧照] 角色数据为空，正在加载...');
                await this.loadEventsAndCharacters();
            }

            console.log('🎭 [角色剧照] 开始加载');
            console.log('🎭 [角色剧照] this.characters:', this.characters);
            console.log('🎭 [角色剧照] selectedEpisodes:', Array.from(this.selectedEpisodes));

            // 直接使用全局角色列表（API 已经返回了所有角色）
            let characters = [];

            if (this.characters && this.characters.length > 0) {
                characters = [...this.characters];
                console.log('🎭 [角色剧照] 使用全局角色列表:', characters.length);
            } else {
                // 尝试从选中的集中提取角色
                characters = this.extractCharactersFromEpisodes();
                console.log('🎭 [角色剧照] 从集数提取角色:', characters.length);
            }

            if (characters.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">👥</p>
                        <p>没有找到角色</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">
                            请先在小说中配置角色信息
                        </p>
                    </div>
                `;
                return;
            }

            // 加载剧照信息
            await this.loadPortraits();

            console.log('🎭 [角色剧照] 最终角色列表:', characters.length);
            console.log('🎭 [角色剧照] 剧照映射:', this.characterPortraits);

            // 渲染角色卡片
            container.innerHTML = characters.map((char, idx) => {
                const charName = char.name || `角色${idx + 1}`;
                const charRole = char.role || '角色';
                const portraitInfo = this.characterPortraits.get(charName);

                // 提取角色外观描述
                let appearanceDesc = '';
                if (char.living_characteristics?.physical_presence) {
                    appearanceDesc = char.living_characteristics.physical_presence;
                } else if (char.initial_state?.description) {
                    appearanceDesc = char.initial_state.description;
                } else if (char.appearance) {
                    appearanceDesc = char.appearance;
                } else if (char.description) {
                    appearanceDesc = char.description;
                }

                // 限制描述长度
                if (appearanceDesc.length > 50) {
                    appearanceDesc = appearanceDesc.substring(0, 50) + '...';
                }

                // 🔥 检查是否为三视图（优先级剧照）
                const isThreeView = portraitInfo && portraitInfo.mainPortrait && portraitInfo.mainPortrait.isPriority;

                return `
                    <div class="character-card ${portraitInfo ? 'has-portrait' : ''}">
                        <div class="character-card-header">
                            <div class="character-avatar" style="position: relative;">
                                ${portraitInfo
                                    ? `<img src="${portraitInfo.mainPortrait.url}" alt="${charName}" onerror="this.parentElement.innerHTML='<span style=\\'font-size: 2rem;\\'>👤</span>'">`
                                    : '<span style="font-size: 2rem;">👤</span>'
                                }
                                ${isThreeView ? `
                                    <div style="position: absolute; top: -5px; right: -5px; background: linear-gradient(135deg, #ff6b6b, #feca57); color: white; font-size: 10px; padding: 2px 6px; border-radius: 10px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2); z-index: 1;">三视图</div>
                                ` : ''}
                            </div>
                            <div class="character-info">
                                <div class="character-name">${charName}</div>
                                <div class="character-role">${charRole}</div>
                                ${appearanceDesc ? `<div class="character-appearance" title="${char.living_characteristics?.physical_presence || char.initial_state?.description || char.appearance || char.description}">${appearanceDesc}</div>` : ''}
                                ${portraitInfo && portraitInfo.portraits.length > 1
                                    ? `<div class="portrait-count">${portraitInfo.portraits.length} 个造型</div>`
                                    : ''
                                }
                            </div>
                        </div>
                        <div class="character-actions">
                            ${portraitInfo
                                ? `<button class="btn btn-sm btn-secondary" onclick="shortDramaStudio.viewPortrait('${charName}')">查看</button>`
                                : `<button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generatePortrait('${charName}')">📸 生成剧照</button>`
                            }
                        </div>
                    </div>
                `;
            }).join('');

            console.log('✅ [角色剧照] 渲染完成，共', characters.length, '个角色');

            // 更新项目状态
            this.updateProjectStatus();
        } catch (error) {
            console.error('❌ [角色剧照] 加载失败:', error);
            const container = document.getElementById('charactersGrid');
            if (container) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">❌</p>
                        <p>加载角色失败</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${error.message}</p>
                    </div>
                `;
            }
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
     * 从选中集数中提取角色
     */
    extractCharactersFromEpisodes() {
        const characters = [];
        const seen = new Set();

        for (const eventId of this.selectedEpisodes) {
            // 在重大事件的子事件中查找
            for (const majorEvent of this.events) {
                const episode = majorEvent.children?.find(e =>
                    e.id === eventId || e.name === eventId
                );
                if (episode && episode.characters) {
                    episode.characters.forEach(char => {
                        if (!seen.has(char.name)) {
                            seen.add(char.name);
                            characters.push(char);
                        }
                    });
                }
            }
        }

        return characters;
    }

    /**
     * 生成角色剧照
     */
    /**
     * 生成角色剧照
     */
    async generatePortrait(characterName) {
        const character = this.characters.find(c => c.name === characterName);
        if (!character) {
            this.showToast('找不到角色信息', 'error');
            return;
        }

        // 构建剧集目录名称
        const episodeDirectoryName = this.getEpisodeDirectoryName();

        // 生成角色剧照提示词（参考旧代码逻辑）
        const prompt = this.generateCharacterPortraitPrompt(character);

        // 保存数据到localStorage供剧照工作台使用
        const dataToSave = {
            id: character.id,
            name: character.name,
            role: character.role || '',
            description: character.description || '',
            appearance: character.appearance || '',
            generatedPrompt: prompt,
            episode_info: episodeDirectoryName,
            novel_title: this.selectedNovel,
            return_url: `/short-drama-studio`, // 保存返回地址
            return_step: 'check-portraits' // 保存返回步骤
        };

        console.log('📸 保存角色数据到localStorage:', dataToSave);
        localStorage.setItem('portraitStudio_character', JSON.stringify(dataToSave));

        // 打开剧照工作台（新窗口）
        window.open('/portrait-studio?mode=episode', '_blank');
    }

    /**
     * 根据角色信息生成AI剧照提示词（使用角色设计文件中的详细特征）
     */
    generateCharacterPortraitPrompt(character) {
        const name = character.name || '';
        const role = character.role || '';

        // 从角色设计文件结构中提取详细外观信息
        let physicalDescription = '';
        let personality = '';
        let age = '';
        let clothing = '';

        // 尝试从不同字段中提取信息
        if (character.living_characteristics) {
            physicalDescription = character.living_characteristics.physical_presence || '';
            personality = character.living_characteristics.distinctive_traits || character.living_characteristics.communication_style || '';
        }

        // 从initial_state中提取
        if (character.initial_state) {
            if (!physicalDescription) {
                physicalDescription = character.initial_state.description || '';
            }
        }

        // 从top-level字段提取（兼容旧格式）
        if (!physicalDescription) {
            physicalDescription = character.appearance || character.description || '';
        }

        // 从soul_matrix中提取核心特质
        if (character.soul_matrix && character.soul_matrix.length > 0) {
            const firstTrait = character.soul_matrix[0];
            if (typeof firstTrait === 'object') {
                personality = firstTrait.core_trait || personality;
            } else if (typeof firstTrait === 'string') {
                personality = firstTrait;
            }
        }

        // 提取年龄
        age = character.age || character.initial_state?.age || '';

        // 构建详细的角色特征描述
        let characterFeatures = [];

        // 添加身体特征（最重要）
        if (physicalDescription) {
            characterFeatures.push(`外形：${physicalDescription}`);
        }

        // 添加性格特质
        if (personality) {
            characterFeatures.push(`性格：${personality}`);
        }

        // 添加年龄
        if (age) {
            characterFeatures.push(`年龄：${age}`);
        }

        // 添加服装/装备信息（从physical_description中提取关键词）
        const clothingKeywords = ['身穿', '身披', '着', '战甲', '锦袍', '长袍', '铠甲', '盔甲', '衣服', '套装'];
        for (const keyword of clothingKeywords) {
            if (physicalDescription.includes(keyword)) {
                // 找到包含服装关键词的句子
                const sentences = physicalDescription.split(/[，。；！]/);
                for (const sentence of sentences) {
                    if (sentence.includes(keyword)) {
                        clothing = sentence.trim();
                        break;
                    }
                }
                if (clothing) break;
            }
        }
        if (clothing) {
            characterFeatures.push(`服装：${clothing}`);
        }

        // 根据角色的actual特征构建提示词，而不是用通用模板
        let prompt = `角色名称：${name}\n`;
        prompt += `角色定位：${role}\n`;
        prompt += `\n`;

        // 如果有详细的特征描述，优先使用
        if (characterFeatures.length > 0) {
            prompt += `【角色特征】\n`;
            prompt += characterFeatures.join('\n');
            prompt += `\n\n`;
        }

        // 根据角色定位添加画面要求（使用更精确的风格）
        prompt += `【画面要求】\n`;

        // 根据实际角色特征确定风格，而不是通用模板
        let style = '高质量人物立绘，细节丰富';
        let composition = '半身正面像，突出面部特征和表情';
        let expression = '自然生动';
        let background = '东方玄幻修仙世界风格背景';

        // 根据physical_description中的关键词调整风格
        if (physicalDescription) {
            if (physicalDescription.includes('横肉') || physicalDescription.includes('魁梧') || physicalDescription.includes('壮汉')) {
                // 粗犷威猛型角色
                style = '东方玄幻风格，粗犷威猛，力量感十足';
                expression = '威严霸气，眼神锐利，气势逼人';
                background = '压抑的氛围，强者威压的视觉效果';
            } else if (physicalDescription.includes('仙风') || physicalDescription.includes('鹤发') || physicalDescription.includes('童颜')) {
                // 仙风道骨型角色
                style = '东方玄幻风格，仙风道骨，高人风范';
                expression = '慈祥深邃，眼神空灵，道法自然';
                background = '仙气缭绕，云雾飘渺，道韵天成';
            } else if (physicalDescription.includes('绝美') || physicalDescription.includes('容') || physicalDescription.includes('少女') || physicalDescription.includes('美女')) {
                // 美女型角色
                style = '东方玄幻风格，精致唯美，仙气飘飘';
                expression = '温柔恬静或清冷孤傲，眼神灵动';
                background = '花海仙宫，梦幻氛围';
            } else if (physicalDescription.includes('阴鸷') || physicalDescription.includes('阴') || physicalDescription.includes('煞')) {
                // 阴狠型角色
                style = '东方玄幻风格，阴狠霸气，魔道气息';
                expression = '阴鸷狠戾，眼神如蛇，压迫感强';
                background = '黑暗气息，血煞之气，魔道氛围';
            } else {
                // 默认风格
                style = '东方玄幻修真风格，高质量人物立绘';
                expression = '生动自然，眼神有神';
                background = '东方玄幻修仙世界风格，灵气氤氲';
            }
        }

        prompt += `风格：${style}\n`;
        prompt += `构图：${composition}\n`;
        prompt += `表情：${expression}\n`;
        prompt += `背景：${background}\n`;

        // 添加技术要求
        prompt += `\n【技术要求】\n`;
        prompt += `- 高清画质，细节精致\n`;
        prompt += `- 专业插画质量\n`;
        prompt += `- 光影效果出色，立体感强\n`;
        prompt += `- 色彩和谐，符合东方玄幻美学\n`;
        prompt += `- 人物比例协调，五官端正\n`;
        prompt += `- 空气中弥漫灵气粒子效果\n`;

        return prompt;
    }

    /**
     * 获取剧集目录名称
     */
    getEpisodeDirectoryName() {
        if (!this.selectedMajorEvent) return '默认';

        const majorIndex = this.events.findIndex(e => e.id === this.selectedMajorEvent.id);
        // 使用原始标题，不要替换特殊字符（因为目录名保留了原始字符）
        const eventTitle = this.selectedMajorEvent.title || this.selectedMajorEvent.name;

        return `${majorIndex + 1}集_${eventTitle}`;
    }

    /**
     * 查看剧照
     */
    viewPortrait(characterName) {
        const portrait = this.characterPortraits.get(characterName);
        if (portrait) {
            // 打开模态框显示剧照
            this.showPortraitModal(characterName, portrait);
        }
    }

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
            if (e.target === modal) modal.remove();
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

        // 4K需要使用专门的4K模型
        let model = 'veo_3_1-fast-components';
        if (quality === '4K') {
            model = 'veo_3_1-fast-components-4K';
        }

        return {
            orientation: aspectRatio === '16:9' ? 'landscape' : 'portrait',
            size: size,
            model: model
        };
    }

    /**
     * 加载分镜头步骤
     */
    async loadStoryboardStep() {
        const container = document.getElementById('storyboardContent');
        if (!container) return;

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>加载分镜头...</p></div>';

        try {
            // 先尝试从本地文件加载已存在的分镜头
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            const response = await fetch(`/api/short-drama/storyboards?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            if (data.success && data.storyboards && Object.keys(data.storyboards).length > 0) {
                console.log('✅ [分镜头] 从本地加载分镜头:', Object.keys(data.storyboards));
                this.renderStoryboards(data.storyboards);
            } else {
                // 没有本地分镜头，显示生成按钮
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">🎬</p>
                        <p>暂无分镜头数据</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">
                            请先生成分镜头
                        </p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryboard()">🎬 生成分镜头</button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('加载分镜头失败:', error);
            container.innerHTML = `
                <div class="empty-state">
                    <p>加载分镜头失败</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">${error.message}</p>
                </div>
            `;
        }
    }

    /**
     * 生成新分镜头
     */
    async generateStoryboard() {
        const container = document.getElementById('storyboardContent');
        if (!container) return;

        // 检查是否选择了小说
        if (!this.selectedNovel) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>请先选择小说项目</p>
                </div>
            `;
            return;
        }

        // 检查是否选择了事件
        const selectedEpisodesList = Array.from(this.selectedEpisodes);
        console.log('🎬 [分镜头] ===== 生成调试信息 =====');
        console.log('🎬 [分镜头] 选择小说:', this.selectedNovel);
        console.log('🎬 [分镜头] 选择事件:', selectedEpisodesList);
        console.log('🎬 [分镜头] 事件数量:', selectedEpisodesList.length);
        console.log('🎬 [分镜头] 事件对象:', this.events);
        console.log('🎬 [分镜头] 第一个事件:', this.events[0]);
        if (this.events[0] && this.events[0].children) {
            console.log('🎬 [分镜头] 第一个事件的子事件数量:', this.events[0].children.length);
            console.log('🎬 [分镜头] 第一个子事件:', this.events[0].children[0]);
        }
        console.log('🎬 [分镜头] ========================');

        if (selectedEpisodesList.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>请先选择要生成分镜头的集数</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">在左侧面板勾选要生成的集数</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>正在生成分镜头...</p></div>';

        try {
            const response = await fetch('/api/video/generate-storyboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: this.selectedNovel,
                    video_type: 'short_video',
                    selected_events: selectedEpisodesList,
                    use_workflow_portraits: true
                })
            });

            const data = await response.json();
            console.log('🎬 [分镜头] ===== API响应调试 =====');
            console.log('🎬 [分镜头] 响应状态:', response.status);
            console.log('🎬 [分镜头] 响应数据:', data);
            console.log('🎬 [分镜头] success:', data.success);
            console.log('🎬 [分镜头] storyboard:', data.storyboard);
            console.log('🎬 [分镜头] shots数量:', data.storyboard?.shots?.length || 0);
            console.log('🎬 [分镜头] total_shots:', data.storyboard?.total_shots || 0);
            console.log('🎬 [分镜头] ========================');

            if (data.success && data.storyboard) {
                this.currentProject = { ...this.currentProject, storyboard: data.storyboard };
                // 🔥 保存项目到文件系统，这样后续剧照API才能找到目录
                await this.saveProject();
                this.renderStoryboard(data.storyboard);
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>分镜头生成失败</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${data.error || '未知错误'}</p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryboard()">重试</button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('生成分镜头失败:', error);
            container.innerHTML = `
                <div class="empty-state">
                    <p>生成分镜头失败</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">${error.message}</p>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryboard()">重试</button>
                </div>
            `;
        }
    }

    /**
     * 标准化镜头数据 - 支持新旧两种格式
     * 新格式: {scene_number, visual: {shot_type, description, veo_prompt}, dialogue: {speaker, lines, tone}}
     * 旧格式: {shot_number, shot_type, screen_action, dialogue, veo_prompt}
     * 对话格式: {scene_number, visual, dialogues: [{speaker, lines, tone}, ...]}
     */
    normalizeShotData(shot, title, episodeNumber, selectedIndex) {
        // 检查是否是新格式 (有 visual 字段)
        if (shot.visual) {
            // 新格式转旧格式
            const visual = shot.visual || {};

            // 检查是否有多个对话 (对话场景)
            if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
                // 对话场景：保留原始结构，不展开
                // 视频生成时生成1个视频，配音生成时展开为多个音频
                return {
                    shot_number: shot.scene_number || shot.shot_number,
                    shot_type: visual.shot_type || shot.shot_type || '镜头',
                    screen_action: visual.description || shot.screen_action || '',
                    // 保留dialogues数组用于配音展开
                    dialogues: shot.dialogues,
                    // 使用第一个对话作为默认显示（用于视频步骤）
                    dialogue: shot.dialogues[0].lines || shot.dialogues[0].speaker || '',
                    _dialogue_data: shot.dialogues[0],
                    veo_prompt: visual.veo_prompt || shot.veo_prompt || '',
                    duration: shot.duration || 5,
                    plot_content: shot.plot_content || '',
                    episode_title: title,
                    event_name: title,  // 事件名用于文件命名
                    episode_index: episodeNumber,
                    episode_order: selectedIndex === -1 ? 9999 : selectedIndex,
                    audio: shot.dialogues[0].audio_note || shot.audio || '',
                    is_dialogue_scene: true,  // 标记为对话场景
                    dialogue_count: shot.dialogues.length  // 对话总数
                };
            }

            const dialogue = shot.dialogue || {};
            return {
                shot_number: shot.scene_number || shot.shot_number,
                shot_type: visual.shot_type || shot.shot_type || '镜头',
                screen_action: visual.description || shot.screen_action || '',
                dialogue: dialogue.lines || dialogue.speaker || '',
                // 保留原始dialogue对象供后期使用
                _dialogue_data: dialogue,
                veo_prompt: visual.veo_prompt || shot.veo_prompt || '',
                duration: shot.duration || 5,
                plot_content: shot.plot_content || '',
                episode_title: title,
                event_name: title,  // 事件名用于文件命名
                episode_index: episodeNumber,
                episode_order: selectedIndex === -1 ? 9999 : selectedIndex,
                audio: dialogue.audio_note || shot.audio || ''
            };
        } else {
            // 旧格式，直接使用
            return {
                ...shot,
                episode_title: title,
                event_name: shot.event_name || title,  // 确保有 event_name
                episode_index: episodeNumber,
                episode_order: selectedIndex === -1 ? 9999 : selectedIndex
            };
        }
    }

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
    renderStoryboards(storyboards) {
        const container = document.getElementById('storyboardContent');
        if (!container) return;

        // 将分镜头转换为数组
        const storyboardArray = Object.entries(storyboards).map(([title, data]) => {
            // 从标题中提取集数进行排序，格式如 "1集_xxx"
            const episodeMatch = title.match(/^(\d+)[集期]/);
            const episodeNumber = episodeMatch ? parseInt(episodeMatch[1]) : 999;
            return { title, data, episodeNumber };
        });

        // 🔥 按照选择事件的顺序排序
        storyboardArray.sort((a, b) => {
            // 获取两个事件在 selectedEpisodes 中的索引
            const indexA = this.selectedEpisodes.indexOf(a.title);
            const indexB = this.selectedEpisodes.indexOf(b.title);

            // 如果两个都在选择列表中，按选择顺序排序
            if (indexA !== -1 && indexB !== -1) {
                return indexA - indexB;
            }
            // 只有一个在选择列表中，选择的排在前面
            if (indexA !== -1) return -1;
            if (indexB !== -1) return 1;
            // 都不在选择列表中，按集数排序
            return a.episodeNumber - b.episodeNumber;
        });

        // 收集所有镜头，并按事件顺序 + 镜头编号排序
        const allShots = [];

        for (const { title, data, episodeNumber } of storyboardArray) {
            // 🔥 支持新旧两种格式
            // 旧格式: data.shots, 新格式: data.scenes
            const sourceShots = data.shots || data.scenes || [];
            const selectedIndex = this.selectedEpisodes.indexOf(title);

            // 🔥 先转换所有镜头
            const normalizedShots = [];
            for (const shot of sourceShots) {
                const normalizedShot = this.normalizeShotData(shot, title, episodeNumber, selectedIndex);
                // 🔥 对话场景返回的是数组，需要展开
                if (Array.isArray(normalizedShot)) {
                    normalizedShots.push(...normalizedShot);
                } else {
                    normalizedShots.push(normalizedShot);
                }
            }

            // 🔥 合并连续的对话场景
            const groupedShots = this.groupDialogueScenes(normalizedShots);
            allShots.push(...groupedShots);
        }

        // 🔥 按事件选择顺序 + 镜头编号排序
        allShots.sort((a, b) => {
            // 首先按事件选择顺序
            if (a.episode_order !== b.episode_order) {
                return a.episode_order - b.episode_order;
            }
            // 同一事件内按镜头编号排序 (支持 shot_number 和 scene_number)
            const numA = parseInt(a.shot_number || a.scene_number) || 0;
            const numB = parseInt(b.shot_number || b.scene_number) || 0;
            return numA - numB;
        });

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>没有找到分镜头</p>
                </div>
            `;
            return;
        }

        // 保存镜头数据供视频生成使用
        this.shots = allShots;

        container.innerHTML = `
            <div style="margin-bottom: 1.5rem;">
                <p style="font-size: 0.9rem; color: var(--text-secondary);">
                    共 <strong>${allShots.length}</strong> 个镜头（从 ${storyboardArray.length} 个分镜头文件加载）
                </p>
            </div>
            <div class="shots-list">
                ${allShots.map((shot, idx) => `
                    <div class="shot-item" id="storyboardShot_${idx}">
                        <div class="shot-number">#${shot.shot_number || shot.scene_number || (idx + 1)}</div>
                        <div class="shot-info">
                            <div class="shot-type">${shot.shot_type || '镜头'}</div>
                            <div class="shot-duration">⏱️ ${shot.duration || 5}秒</div>
                            <div class="shot-episode" style="font-size: 0.75rem; color: var(--text-tertiary);">${shot.episode_title || ''}</div>
                            <div class="shot-desc">${shot.veo_prompt?.substring(0, 100) || shot.screen_action?.substring(0, 100) || ''}...</div>
                            ${shot._dialogue_data && shot._dialogue_data.speaker ? `<div class="shot-dialogue" style="font-size: 0.75rem; color: var(--accent);">💬 ${shot._dialogue_data.speaker}: ${shot._dialogue_data.lines?.substring(0, 30) || ''}...</div>` : ''}
                        </div>
                        <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generateShotVideo(${idx})">生成视频</button>
                    </div>
                `).join('')}
            </div>
        `;

        // 更新项目状态
        this.updateProjectStatus();
    }

    /**
     * 渲染分镜头
     */
    renderStoryboard(storyboard) {
        const container = document.getElementById('storyboardContent');
        if (!container) return;

        const allShots = [];

        // 🔥 按章节顺序提取镜头（Object.entries在现代JS中保持插入顺序）
        // 后端已经按文件名中的章节号排序返回
        for (const [epId, epData] of Object.entries(storyboard)) {
            // 从文件名中提取事件名（去掉章节范围前缀）
            // 文件名格式: 第1-3章_事件名.json 或 事件名.json
            const eventName = epId.replace(/^第?\d+(?:-\d+)?章_?/, '').trim();
            const scenes = epData.scenes || [];
            for (const scene of scenes) {
                const shots = scene.shot_sequence || [];
                for (const shot of shots) {
                    if (shot.veo_prompt) {
                        allShots.push({
                            ...shot,
                            episode_id: epId,
                            episode_title: eventName,  // 使用从文件名提取的事件名
                            event_name: eventName,
                            scene_title: scene.scene_title
                        });
                    }
                }
            }
        }

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>没有生成分镜头</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div style="margin-bottom: 1.5rem;">
                <p style="font-size: 0.9rem; color: var(--text-secondary);">
                    共 <strong>${allShots.length}</strong> 个镜头
                </p>
            </div>
            <div class="shots-list">
                ${allShots.map((shot, idx) => `
                    <div class="shot-item" id="shot_${idx}">
                        <div class="shot-number">#${shot.shot_number || shot.scene_number || (idx + 1)}</div>
                        <div class="shot-info">
                            <div class="shot-type">${shot.shot_type || '镜头'}</div>
                            <div class="shot-duration">⏱️ ${shot.duration || 5}秒</div>
                            <div class="shot-episode" style="font-size: 0.75rem; color: var(--text-tertiary);">${shot.episode_title || ''}</div>
                            <div class="shot-desc">${shot.veo_prompt?.substring(0, 100)}...</div>
                            ${shot._dialogue_data && shot._dialogue_data.speaker ? `<div class="shot-dialogue" style="font-size: 0.75rem; color: var(--accent);">💬 ${shot._dialogue_data.speaker}: ${shot._dialogue_data.lines?.substring(0, 30) || ''}...</div>` : ''}
                        </div>
                        <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generateShotVideo(${idx})">生成视频</button>
                    </div>
                `).join('')}
            </div>
        `;

        // 保存镜头数据
        this.shots = allShots;
    }

    /**
     * 加载视频步骤
     */
    async loadVideoStep() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        if (!this.shots || this.shots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>还没有分镜头数据</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在"分镜头"步骤生成分镜头
                    </p>
                </div>
            `;
            return;
        }

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
                    const shotType = shot.shot_type || '';

                    console.log(`🔍 镜头 #${i + 1}: episode="${episodeTitle}", shot_number=${shotNumber}, shot_type="${shotType}"`);

                    // 🔥 在所有视频中查找匹配的视频
                    let matchedVideo = null;
                    for (const video of data.videos) {
                        // 新格式视频有 episode_name 字段
                        const videoEpisodeName = video.episode_name || video.storyboard_key || '';
                        const videoSeq = video.sequence;
                        const videoSceneNum = video.scene_number || 0;
                        const videoShotType = video.shot_type || '';

                        // 检查章节名是否匹配
                        if (videoEpisodeName === episodeTitle || videoEpisodeName.startsWith(episodeTitle)) {
                            // 进一步检查shot_type（可选）
                            if (!shotType || videoShotType.includes(shotType.replace('/', '_')) || shotType.includes(videoShotType)) {
                                matchedVideo = video;
                                console.log(`   ✅ 匹配成功!`);
                                break;
                            } else {
                                console.log(`   ⚠️ shot_type不匹配: 需要"${shotType}", video有"${videoShotType}"`);
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
                    const shotNumber = shot.shot_number || (i + 1);

                    console.log(`🎙️ [镜头 #${shotNumber}] 事件="${episodeTitle}"`);

                    // 检查是否是对话场景
                    if (shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues)) {
                        // 对话场景：遍历每个子对话
                        for (let dlgIdx = 0; dlgIdx < shot.dialogues.length; dlgIdx++) {
                            const dlg = shot.dialogues[dlgIdx];
                            const { speaker } = this.parseDialogue(dlg);
                            const dialogueIndex = dlgIdx + 1;

                            console.log(`   🔍 对话${dialogueIndex}: speaker="${speaker}"`);

                            // 查找匹配的音频文件
                            // 新格式: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话{对话序号:02d}_{角色}_{句子序号:03d}.mp3
                            let matchedAudio = null;
                            for (const audio of data.audios) {
                                const audioEventName = audio.event_name || '';
                                const audioSpeaker = audio.speaker || '';
                                const audioDialogueIdx = audio.dialogue_idx || 1;

                                // 匹配事件名和说话人
                                if (audioEventName === episodeTitle && audioSpeaker === speaker && audioDialogueIdx === dialogueIndex) {
                                    matchedAudio = audio;
                                    console.log(`      ✅ ${audio.filename}`);
                                    break;
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

                        let matchedAudio = null;
                        for (const audio of data.audios) {
                            const audioEventName = audio.event_name || '';
                            const audioSpeaker = audio.speaker || '';

                            // 匹配事件名和说话人
                            if (audioEventName === episodeTitle && audioSpeaker === speaker) {
                                matchedAudio = audio;
                                console.log(`   ✅ ${audio.filename}`);
                                break;
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

        const completedCount = this.shots.filter(s => s.videoExists).length;
        const totalCount = this.shots.length;

        // 按事件分组
        const eventGroups = this.groupShotsByEvent(this.shots);

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
    groupShotsByEvent(shots) {
        const groups = [];
        let currentEvent = null;
        let currentGroup = null;

        shots.forEach(shot => {
            const eventName = shot.episode_title || shot.event_name || '未分组';

            if (eventName !== currentEvent) {
                // 新的事件组
                currentGroup = {
                    eventName: eventName,
                    shots: []
                };
                groups.push(currentGroup);
                currentEvent = eventName;
            }

            currentGroup.shots.push(shot);
        });

        return groups;
    }

    /**
     * 渲染单个视频任务行（剪映风格）
     */
    renderVideoTaskRow(shot, idx) {
        const isCompleted = shot.videoExists;
        const isGenerating = shot.generating;
        const hasError = shot.hasError;

        const statusClass = isCompleted ? 'done' : isGenerating ? 'processing' : hasError ? 'error' : 'pending';
        const statusText = isCompleted ? '已完成' : isGenerating ? '生成中...' : hasError ? '失败' : '待生成';

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

        return `
            <div class="task-row ${statusClass}" id="taskRow_${idx}">
                <div class="task-index">#${shot.shot_number || shot.scene_number || (idx + 1)}</div>
                <div class="task-content">
                    <div class="task-prompt">
                        <span class="prompt-label">AI提示:</span>
                        <span class="prompt-text">${(shot.veo_prompt || shot.screen_action || '').substring(0, 150)}${(shot.veo_prompt || shot.screen_action || '').length > 150 ? '...' : ''}</span>
                    </div>
                    ${shot.plot_content ? `
                    <div class="task-plot">
                        <span class="plot-label">📖 情节:</span>
                        <span class="plot-text">${shot.plot_content.substring(0, 150)}${shot.plot_content.length > 150 ? '...' : ''}</span>
                    </div>
                    ` : ''}
                    ${hasDialogue ? dialogueDisplayHtml : ''}
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
                    <button class="task-btn edit-btn" onclick="shortDramaStudio.editShotPrompt(${idx})" title="编辑提示词">
                        <span>✏️</span>
                    </button>
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
                    <button class="btn-close" onclick="this.closest('.dubbing-confirm-modal').remove()" style="background: none; border: none; font-size: 1.8rem; cursor: pointer; color: var(--text-secondary);">×</button>
                </div>

                <div class="modal-body">
                    <!-- 镜头信息 -->
                    <div style="margin-bottom: 20px; padding: 16px; background: var(--bg-dark); border-radius: 12px;">
                        <div style="display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap;">
                            <span class="badge" style="background: var(--primary-light); color: var(--primary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">${shot.shot_type || '镜头'}</span>
                            <span class="badge" style="background: var(--bg-tertiary); padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">⏱️ ${shot.duration || 5}秒</span>
                        </div>
                        <p style="color: var(--text-secondary); margin: 0; font-size: 0.85rem;">
                            🎬 画面: ${(shot.veo_prompt || shot.screen_action || '').substring(0, 100)}...
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
                                    border: 1px solid var(--border);
                                    border-radius: 8px;
                                    color: var(--text-primary);
                                    font-size: 0.95rem;
                                ">
                                    ${Object.entries(this.characterVoices).map(([name, id]) => `
                                        <option value="${id}" ${id === defaultVoiceId ? 'selected' : ''}>${name} (${id})</option>
                                    `).join('')}
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
                    <button class="btn-cancel" onclick="this.closest('.dubbing-confirm-modal').remove()" style="
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

            // 移除弹窗
            modal.remove();
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

            // 移除弹窗
            modal.remove();

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
                    scene_number: shot.shot_number || shot.scene_number || (idx + 1),
                    event_name: shot.event_name || shot.event || '',  // 中级事件名
                    dialogue_index: shot.dialogue_index,  // 对话序号（对话场景用）
                    dialogue_count: shot.dialogue_count,  // 该场景对话总数
                    speaker: speaker,
                    lines: cleanLines,  // 使用清理后的台词
                    tone: tone,  // 传递语气描述，后端会自动转换为emotion
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
                    scene_number: shot.shot_number || shot.scene_number,
                    event_name: shot.event_name || shot.event || '',
                    dialogue_index: shot.dialogue_index,
                    dialogue_count: shot.dialogue_count,
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

    /**
     * 渲染单个配音场景（支持更新和返回模板）
     */
    renderDubbingScene(shot, idx) {
        const dialogue = shot._dialogue_data || shot.dialogue || {};
        const { speaker, lines, tone } = this.parseDialogue(dialogue);

        const hasAudio = shot.audioUrl || shot.audio_path;
        const isGenerating = shot.dubbingGenerating;
        const hasError = shot.dubbingError;

        // 状态样式和文字（与视频卡片保持一致）
        const statusClass = hasAudio ? 'done' : isGenerating ? 'processing' : hasError ? 'error' : 'pending';
        const statusText = hasAudio ? '已完成' : isGenerating ? '生成中...' : hasError ? '失败' : '待生成';

        // 获取事件名（从 episode_title 或 event_name）
        const eventName = shot.episode_title || shot.event_name || '';

        // 对话场景的序号显示
        const dialogueIndex = shot.dialogue_index;
        const dialogueCount = shot.dialogue_count;
        const dialogueLabel = (dialogueIndex && dialogueCount && dialogueCount > 1)
            ? `<span class="dialogue-index" style="font-size: 0.75rem; color: var(--primary); background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px; margin-left: 4px;">对话${dialogueIndex}/${dialogueCount}</span>`
            : '';

        const innerHTML = `
            <div class="scene-header">
                <span class="scene-number">#${shot.shot_number || shot.scene_number || (idx + 1)}${dialogueLabel}</span>
                ${eventName ? `<span class="scene-event" title="事件：${eventName}" style="font-size: 0.75rem; color: var(--accent); background: var(--bg-tertiary); padding: 2px 8px; border-radius: 4px;">📋 ${eventName.length > 12 ? eventName.substring(0, 12) + '...' : eventName}</span>` : ''}
                <span class="scene-type">${shot.shot_type || '镜头'}</span>
                <span class="scene-duration">⏱️ ${shot.duration || 5}秒</span>
                <span class="task-status ${statusClass}">${statusText}</span>
            </div>

            <div class="scene-content">
                <div class="scene-visual">
                    <div class="visual-label">🎬 画面</div>
                    <div class="visual-desc">${(shot.veo_prompt || shot.screen_action || '').substring(0, 100)}...</div>
                </div>

                <div class="scene-dialogue">
                    <div class="dialogue-label">💬 台词</div>
                    <div class="dialogue-speaker">${speaker}</div>
                    <div class="dialogue-lines">"${lines}"</div>
                    ${tone ? `<div class="dialogue-tone" style="font-size: 0.75rem; color: var(--text-tertiary);">🎭 ${tone}</div>` : ''}
                </div>
            </div>

            <div class="scene-actions">
                ${hasAudio ? `
                    <div class="audio-player-wrapper" style="width: 100%;">
                        <audio id="audio_${idx}" src="${shot.audioUrl}" controls style="width: 100%; height: 32px;"></audio>
                    </div>
                    <div style="display: flex; gap: 8px; margin-top: 8px;">
                        <button class="scene-btn edit-btn" onclick="shortDramaStudio.editDubbing(${idx})">
                            <span>✏️</span> 编辑台词
                        </button>
                        <button class="scene-btn download-btn" onclick="shortDramaStudio.downloadAudio('${shot.audioUrl}', '${speaker}_${shot.shot_number || idx}')">
                            <span>⬇️</span> 下载
                        </button>
                        <button class="scene-btn restore-btn" onclick="shortDramaStudio.showAudioRestoreModal(${idx})" title="还原备份">
                            <span>♻️</span> 还原
                        </button>
                        <button class="scene-btn regenerate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                            <span>🔄</span> 重生成
                        </button>
                    </div>
                ` : isGenerating ? `
                    <div class="generating-status">生成中...</div>
                    <button class="scene-btn" disabled>请稍候...</button>
                ` : hasError ? `
                    <button class="scene-btn generate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                        <span>🔄</span> 重试
                    </button>
                ` : `
                    <button class="scene-btn generate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                        <span>🎙️</span> 生成配音
                    </button>
                `}
            </div>
        `;

        // 如果元素存在，更新它；否则返回模板字符串
        const sceneEl = document.getElementById(`dubbingScene_${idx}`);
        if (sceneEl) {
            sceneEl.innerHTML = innerHTML;
            // 更新状态类
            sceneEl.classList.remove('generating', 'error', 'done', 'pending');
            if (isGenerating) {
                sceneEl.classList.add('generating');
            } else if (hasError) {
                sceneEl.classList.add('error');
            } else if (hasAudio) {
                sceneEl.classList.add('done');
            } else {
                sceneEl.classList.add('pending');
            }
            return;
        }

        // 返回带外层div的模板字符串（用于初始渲染）
        const initialClass = isGenerating ? 'generating' : hasError ? 'error' : hasAudio ? 'done' : 'pending';
        return `
            <div class="dubbing-scene ${initialClass}" id="dubbingScene_${idx}" data-idx="${idx}">
                ${innerHTML}
            </div>
        `;
    }

    /**
     * 更新配音统计数字
     */
    updateDubbingStats() {
        const dialogueShots = this.shots.filter(shot => {
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            if (typeof dialogue === 'string') return dialogue.trim();
            if (typeof dialogue === 'object') {
                const speaker = dialogue.speaker || '';
                const lines = dialogue.lines || '';
                return speaker && speaker !== '无' && lines;
            }
            return false;
        });

        const completedCount = dialogueShots.filter(s => s.audioUrl || s.audio_path).length;
        const pendingCount = dialogueShots.filter(s => !(s.audioUrl || s.audio_path)).length;
        const totalCount = dialogueShots.length;

        const statsContainer = document.querySelector('.dubbing-stats');
        if (statsContainer) {
            statsContainer.innerHTML = `
                <span class="stat-item">共 ${totalCount} 个镜头</span>
                <span class="stat-item completed">已完成 ${completedCount}</span>
                <span class="stat-item pending">待生成 ${pendingCount}</span>
            `;
        }
    }

    /**
     * 清除步骤缓存（用于数据更新后强制刷新）
     */
    invalidateStepCache(step = null) {
        if (!this.loadedSteps) return;

        if (step) {
            this.loadedSteps.delete(step);
        } else {
            this.loadedSteps.clear();
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

            // 🔥 构建包含台词的 prompt，用于 AI 口型同步
            let prompt = shot.veo_prompt || shot.screen_action || '';

            // 检查是否有英文台词，用于口型同步
            const dialogueData = shot._dialogue_data || shot.dialogue;
            if (dialogueData && dialogueData.lines_en && dialogueData.lines_en.trim()) {
                // 将英文台词添加到 prompt 中，用于 AI 视频生成时的口型同步
                prompt += `. Character speaking: "${dialogueData.lines_en}"`;
            }

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: videoSettings.model,
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
                        shot_number: String(shot.shot_number || (shotIndex + 1)),
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        lines_en: dialogueData?.lines_en || ''  // 传递英文台词
                    }
                })
            });

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

        if (row && shot) {
            row.outerHTML = this.renderVideoTaskRow(shot, shotIndex);
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
                    text-align: center;
                ">
                    <div class="video-progress-spinner" style="
                        width: 40px;
                        height: 40px;
                        border: 3px solid var(--border);
                        border-top-color: var(--primary);
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin: 0 auto 0.75rem;
                    "></div>
                    <p style="margin: 0; font-size: 0.9rem; color: var(--text-secondary);" id="videoProgressText">正在生成视频...</p>
                    <p style="margin: 0.25rem 0 0 0; font-size: 0.8rem; color: var(--text-tertiary);" id="videoProgressStatus">正在提交任务</p>
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

        // 添加到后台任务列表
        const taskId = shot.currentTaskId || `bg_${shotIndex}_${Date.now()}`;

        this.backgroundTasks.set(taskId, {
            shotIndex: shotIndex,
            shot: shot,
            taskId: taskId,
            startTime: Date.now(),
            progress: 0,
            status: '处理中...'
        });

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
                    return `
                        <div class="bg-task-item" data-task-id="${task.taskId}" style="
                            background: var(--bg-tertiary);
                            padding: 0.75rem;
                            border-radius: 8px;
                            margin-bottom: 0.5rem;
                            cursor: pointer;
                            transition: background 0.2s;
                        ">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="flex: 1; min-width: 0;">
                                    <div style="font-size: 0.85rem; font-weight: 500; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                                        #${shot.shot_number || (task.shotIndex + 1)} ${shot.shot_type || '镜头'}
                                    </div>
                                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 0.25rem;">
                                        ${task.status || '处理中...'}
                                    </div>
                                </div>
                                <div style="margin-left: 0.75rem;">
                                    <div class="task-spinner" style="
                                        width: 20px;
                                        height: 20px;
                                        border: 2px solid var(--border);
                                        border-top-color: var(--primary);
                                        border-radius: 50%;
                                        animation: spin 1s linear infinite;
                                    "></div>
                                </div>
                            </div>
                            <div style="
                                margin-top: 0.5rem;
                                height: 4px;
                                background: var(--bg-dark);
                                border-radius: 2px;
                                overflow: hidden;
                            ">
                                <div style="
                                    width: ${task.progress || 0}%;
                                    height: 100%;
                                    background: var(--primary);
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
    updateBackgroundTaskProgress(taskId, progress, status) {
        const task = this.backgroundTasks.get(taskId);
        if (task) {
            task.progress = progress;
            task.status = status;
            this.updateBackgroundTasksWidget();
        }
    }

    /**
     * 从后台任务中移除已完成的任务
     */
    removeBackgroundTask(taskId) {
        this.backgroundTasks.delete(taskId);
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

        if (statusIcon) {
            if (progress >= 100) {
                statusIcon.textContent = '✓';
                statusIcon.style.color = 'var(--success)';
            } else if (status.includes('失败')) {
                statusIcon.textContent = '✗';
                statusIcon.style.color = 'var(--danger)';
            }
        }

        if (progressText) progressText.textContent = progress >= 100 ? '✅ 生成完成!' : `生成进度: ${progress}%`;
        if (progressStatus) progressStatus.textContent = status;

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
            const shotKey = `videoPrompt_${this.selectedNovel}_${shot.episode_title || ''}_${shot.shot_number || (idx + 1)}`;

            // 🔥 构建AI提示词：只包含画面要求，不包含台词和情节
            const buildAIPrompt = (s) => {
                const parts = [];
                if (s.shot_type) parts.push(`【镜头类型】${s.shot_type}`);
                if (s.screen_action) parts.push(`【画面描述】${s.screen_action}`);
                if (s.veo_prompt) parts.push(`【AI提示】${s.veo_prompt}`);
                return parts.join('\n');
            };

            const aiPrompt = buildAIPrompt(shot);

            // 尝试加载之前保存的提示词，如果没有则使用AI提示词
            const savedPrompt = localStorage.getItem(shotKey);
            const promptToUse = savedPrompt || aiPrompt;

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
                                ${savedPrompt ? '<span class="badge" style="background: var(--success); color: white; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem;">已保存提示词</span>' : ''}
                            </div>
                            <p style="color: var(--text-secondary); margin: 0; font-size: 0.9rem;">📍 ${shot.scene_title || ''}</p>
                        </div>

                        <!-- 提示词编辑区 -->
                        <div class="prompt-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">📝 AI提示语${savedPrompt ? '<span style="font-size: 0.8rem; color: var(--success); margin-left: 8px;">(已加载保存的版本)</span>' : ''}</label>
                            <textarea id="promptEditArea" style="
                                width: 100%;
                                min-height: 120px;
                                background: var(--bg-dark);
                                border: 1px solid var(--border);
                                border-radius: 12px;
                                padding: 16px;
                                color: var(--text-primary);
                                font-size: 1rem;
                                line-height: 1.6;
                                resize: vertical;
                                font-family: inherit;
                            ">${promptToUse}</textarea>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px;">
                                <small style="color: var(--text-secondary); font-size: 0.9rem;">💾 修改后会自动保存到本地</small>
                                ${savedPrompt ? `<button id="resetPromptBtn" style="font-size: 0.85rem; padding: 6px 12px; background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: 6px; cursor: pointer;">重置为原始提示词</button>` : ''}
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
                                    ">
                                        <option value="veo_3_1-fast-components-4K" ${videoSettings.model === 'veo_3_1-fast-components-4K' ? 'selected' : ''}>4K参考图模式</option>
                                        <option value="veo_3_1-fast-components" ${videoSettings.model === 'veo_3_1-fast-components' ? 'selected' : ''}>1080p参考图模式</option>
                                        <option value="veo_3_1-fast">首尾帧模式</option>
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
                                    ">
                                        <option value="portrait" ${videoSettings.orientation === 'portrait' ? 'selected' : ''}>竖屏 (9:16)</option>
                                        <option value="landscape" ${videoSettings.orientation === 'landscape' ? 'selected' : ''}>横屏 (16:9)</option>
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
                                    ">
                                        <option value="2160x3840" ${videoSettings.size === '2160x3840' ? 'selected' : ''}>4K竖屏 (2160x3840)</option>
                                        <option value="3840x2160" ${videoSettings.size === '3840x2160' ? 'selected' : ''}>4K横屏 (3840x2160)</option>
                                        <option value="1440x2560" ${videoSettings.size === '1440x2560' ? 'selected' : ''}>2K竖屏 (1440x2560)</option>
                                        <option value="2560x1440" ${videoSettings.size === '2560x1440' ? 'selected' : ''}>2K横屏 (2560x1440)</option>
                                        <option value="1080x1920" ${videoSettings.size === '1080x1920' ? 'selected' : ''}>1080p竖屏 (1080x1920)</option>
                                        <option value="1920x1080" ${videoSettings.size === '1920x1080' ? 'selected' : ''}>1080p横屏 (1920x1080)</option>
                                    </select>
                                </div>
                            </div>
                            <div style="margin-top: 16px;">
                                <label style="display: flex; align-items: center; gap: 10px; font-size: 0.95rem; color: var(--text-secondary); cursor: pointer;">
                                    <input type="checkbox" id="paramFirstLastFrame" style="margin: 0; width: 18px; height: 18px;">
                                    <span>🎞️ 启用首尾帧模式（需选择2张图片：首帧+尾帧）</span>
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
            const resetBtn = modal.querySelector('#resetPromptBtn');
            const promptArea = document.getElementById('promptEditArea');

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
                    } else {
                        thumb.style.borderColor = 'var(--border)';
                        thumb.style.boxShadow = 'none';
                        indicator.textContent = '';
                        indicator.style.background = 'rgba(0,0,0,0.6)';
                    }

                    // 首尾帧模式提示
                    if (firstLastFrameCheck.checked && count !== 2) {
                        selectedCountEl.textContent = count + ' (首尾帧需要2张)';
                    }
                });
            });

            // 首尾帧模式切换
            firstLastFrameCheck.addEventListener('change', () => {
                const count = modal.querySelectorAll('.portrait-check:checked').length;
                if (firstLastFrameCheck.checked && count !== 2) {
                    selectedCountEl.textContent = count + ' (首尾帧需要2张)';
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

                            if (firstLastFrameCheck.checked && count !== 2) {
                                selectedCountEl.textContent = count + ' (首尾帧需要2张)';
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

            // 重置提示词按钮
            if (resetBtn) {
                resetBtn.onclick = () => {
                    // 重置为AI提示词（不包含情节）
                    promptArea.value = aiPrompt;
                    // 清除 localStorage 中的旧值
                    localStorage.removeItem(shotKey);
                    console.log('已清除保存的提示词:', shotKey);
                    console.log('已重置为AI提示词');
                };
            }

            // 生成按钮
            generateBtn.onclick = () => {
                const editedPrompt = promptArea.value;
                const checkedImages = Array.from(modal.querySelectorAll('.portrait-check:checked'))
                    .map(check => check.dataset.url);
                const model = document.getElementById('paramModel').value;
                const orientation = document.getElementById('paramOrientation').value;
                const size = document.getElementById('paramSize').value;
                const useFirstLastFrame = document.getElementById('paramFirstLastFrame').checked;

                console.log('📝 提示词调试信息:');
                console.log('  - shotKey:', shotKey);
                console.log('  - shot.episode_title:', shot.episode_title);
                console.log('  - shot.shot_number:', shot.shot_number);
                console.log('  - 原始 veo_prompt:', shot.veo_prompt);
                console.log('  - 原始 screen_action:', shot.screen_action);
                console.log('  - localStorage 中的值:', savedPrompt);
                console.log('  - 编辑后的提示词:', editedPrompt);
                console.log('选中的图片数量:', checkedImages.length);
                console.log('首尾帧模式:', useFirstLastFrame);

                // 首尾帧模式需要2张图片
                if (useFirstLastFrame && checkedImages.length !== 2) {
                    this.showToast('首尾帧模式需要选择2张图片（首帧+尾帧）', 'warning');
                    return;
                }

                // 保存修改的提示词（与原始AI提示词比较）
                if (editedPrompt !== aiPrompt) {
                    localStorage.setItem(shotKey, editedPrompt);
                    console.log('已保存修改的提示词:', shotKey);
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

        // 🔥 更新 shot 对象中的提示词，确保进度弹窗显示正确的提示词
        if (result.prompt && result.prompt !== (shot.veo_prompt || shot.screen_action || '')) {
            shot.veo_prompt = result.prompt;
            console.log('已更新 shot.veo_prompt:', result.prompt);
        }

        // 开始生成，显示进度弹窗
        this.showVideoProgressModal(shot, idx);

        shot.generating = true;
        shot.hasError = false;
        this.updateVideoCard(idx);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            // 直接使用用户编辑的提示词
            shot.veo_prompt = result.prompt;

            // 获取对话数据中的英文台词
            const dialogueData = shot._dialogue_data || shot.dialogue;

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: result.model || 'veo_3_1-fast-components',
                    prompt: result.prompt,
                    image_urls: result.selectedImages || [],
                    orientation: result.orientation || 'portrait',
                    size: result.size || 'large',
                    watermark: false,
                    private: true,
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        shot_number: String(shot.shot_number || (idx + 1)),
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        lines_en: dialogueData?.lines_en || ''  // 传递英文台词
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
     * 编辑提示词
     */
    editShotPrompt(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const newPrompt = prompt('编辑提示词:', shot.veo_prompt || shot.screen_action || '');
        if (newPrompt !== null && newPrompt.trim()) {
            shot.veo_prompt = newPrompt.trim();
            this.updateVideoCard(idx);
            this.showToast('提示词已更新', 'success');
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
     * 加载配音制作步骤
     */
    async loadDubbingStep() {
        const container = document.getElementById('dubbingContent');
        if (!container) return;

        if (!this.shots || this.shots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎙️</p>
                    <p>还没有分镜头数据</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在"分镜头"步骤生成分镜头
                    </p>
                </div>
            `;
            return;
        }

        // 🔥 加载角色数据
        if (!this.characters || this.characters.length === 0) {
            console.log('🎙️ [配音] 角色数据为空，正在加载...');
            await this.loadEventsAndCharacters();
        }

        // 🔥 提取所有有台词的角色（从镜头中提取）
        const speakerSet = new Set();
        this.shots.forEach(shot => {
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            const { speaker } = this.parseDialogue(dialogue);
            if (speaker && speaker !== '无' && speaker !== '未知') {
                speakerSet.add(speaker);
            }
        });

        // 合并项目角色和台词中的角色
        const allSpeakers = new Set([...speakerSet]);
        this.characters.forEach(char => {
            if (char.name) allSpeakers.add(char.name);
        });

        // 🔥 构建角色-音色映射
        this.characterVoiceMap = {};
        allSpeakers.forEach(speaker => {
            // 从配置中查找匹配的音色
            let matchedVoice = this.characterVoices[speaker];

            // 如果没有直接匹配，尝试模糊匹配
            if (!matchedVoice) {
                for (const [charName, voiceId] of Object.entries(this.characterVoices)) {
                    if (speaker.includes(charName) || charName.includes(speaker)) {
                        matchedVoice = voiceId;
                        break;
                    }
                }
            }

            // 如果还没找到，使用默认音色
            if (!matchedVoice) {
                matchedVoice = this.characterVoices['默认'] || 'female-qn-dahu';
            }

            this.characterVoiceMap[speaker] = matchedVoice;
        });

        console.log('🎙️ [配音] 角色-音色映射:', this.characterVoiceMap);

        // 检查TTS配置
        const ttsConfigResponse = await fetch('/api/tts/config');
        const ttsConfig = await ttsConfigResponse.json();
        const ttsConfigured = ttsConfig.success && ttsConfig.configured;

        // 🔥 获取当前配置的模型
        if (ttsConfig.model) {
            this.ttsModel = ttsConfig.model;
            console.log('🎙️ [配音] 当前TTS模型:', this.ttsModel);
        }

        // 🔥 展开对话场景为独立的配音子镜头
        const expandedDialogueShots = [];
        for (let i = 0; i < this.shots.length; i++) {
            const shot = this.shots[i];
            // 检查是否是对话场景（有dialogues数组）
            if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
                // 🔥 初始化子镜头音频状态数组（如果不存在）
                if (!shot._sub_audios || !Array.isArray(shot._sub_audios)) {
                    shot._sub_audios = new Array(shot.dialogues.length).fill(null);
                }

                // 对话场景：展开为多个子镜头
                shot.dialogues.forEach((dlg, dlgIdx) => {
                    expandedDialogueShots.push({
                        ...shot,
                        // 保存原始索引和子镜头索引
                        _original_shot_index: i,
                        _sub_dialogue_index: dlgIdx,
                        // 覆盖对话数据
                        _dialogue_data: dlg,
                        dialogue: dlg.lines || dlg.speaker || '',
                        // 子镜头特定信息
                        dialogue_index: dlgIdx + 1,
                        dialogue_count: shot.dialogues.length,
                        // 保留原始场景信息用于显示
                        original_scene_number: shot.shot_number,
                        is_dialogue_scene: true,
                        // 🔥 使用原始shot的状态引用（双向绑定）
                        get audioUrl() { return shot._sub_audios?.[dlgIdx]?.audioUrl; },
                        get audio_path() { return shot._sub_audios?.[dlgIdx]?.audio_path; },
                        get audioDuration() { return shot._sub_audios?.[dlgIdx]?.audioDuration; },
                        get dubbingGenerating() { return shot._sub_audios?.[dlgIdx]?.dubbingGenerating || false; },
                        get dubbingError() { return shot._sub_audios?.[dlgIdx]?.dubbingError || false; },
                        set audioUrl(v) {
                            if (!shot._sub_audios) shot._sub_audios = [];
                            if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                            shot._sub_audios[dlgIdx].audioUrl = v;
                        },
                        set audio_path(v) {
                            if (!shot._sub_audios) shot._sub_audios = [];
                            if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                            shot._sub_audios[dlgIdx].audio_path = v;
                        },
                        set audioDuration(v) {
                            if (!shot._sub_audios) shot._sub_audios = [];
                            if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                            shot._sub_audios[dlgIdx].audioDuration = v;
                        },
                        set dubbingGenerating(v) {
                            if (!shot._sub_audios) shot._sub_audios = [];
                            if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                            shot._sub_audios[dlgIdx].dubbingGenerating = v;
                        },
                        set dubbingError(v) {
                            if (!shot._sub_audios) shot._sub_audios = [];
                            if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                            shot._sub_audios[dlgIdx].dubbingError = v;
                        }
                    });
                });
            } else {
                // 普通镜头：直接检查是否有台词
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                const { speaker, lines } = this.parseDialogue(dialogue);
                if (speaker && speaker !== '无' && speaker !== '未知' && lines) {
                    // 添加原始索引
                    shot._original_shot_index = i;
                    expandedDialogueShots.push(shot);
                }
            }
        }

        // 检查已存在的音频文件
        await this.checkExistingAudio();

        // 🔥 保存展开后的镜头列表供后续使用
        this.expandedDubbingShots = expandedDialogueShots;
        console.log('🎙️ [配音] 展开后的镜头数量:', expandedDialogueShots.length);
        console.log('🎙️ [配音] 原始镜头数量:', this.shots.length);
        // 检查对话场景
        const dialogueScenes = expandedDialogueShots.filter(s => s.is_dialogue_scene);
        console.log('🎙️ [配音] 对话场景子镜头数量:', dialogueScenes.length);

        // 按事件分组
        const eventGroups = this.groupShotsByEvent(expandedDialogueShots);

        let scenesHtml = '';
        eventGroups.forEach((group, groupIdx) => {
            // 添加事件分隔线（第一个事件之前不添加）
            if (groupIdx > 0) {
                scenesHtml += `
                    <div class="event-separator">
                        <div class="event-separator-line"></div>
                        <div class="event-separator-label">${group.eventName}</div>
                        <div class="event-separator-line"></div>
                    </div>
                `;
            } else if (group.eventName) {
                // 第一个事件也显示标签，但没有上面的分隔线
                scenesHtml += `
                    <div class="event-separator first">
                        <div class="event-separator-label">${group.eventName}</div>
                    </div>
                `;
            }

            // 渲染该事件的所有镜头，使用展开后的索引
            group.shots.forEach((shot) => {
                // 🔥 在展开的镜头列表中查找索引
                const expandedIdx = expandedDialogueShots.indexOf(shot);
                console.log(`🎙️ [配音] 渲染镜头: scene=#${shot.shot_number}, expandedIdx=${expandedIdx}, dialogue="${shot._dialogue_data?.lines?.substring(0, 15)}..."`);
                scenesHtml += this.renderDubbingScene(shot, expandedIdx);
            });
        });

        container.innerHTML = `
            <div class="dubbing-workspace">
                <!-- 工具栏 -->
                <div class="dubbing-toolbar">
                    <div class="dubbing-stats">
                        <span class="stat-item">共 ${expandedDialogueShots.length} 个镜头</span>
                        <span class="stat-item completed">已完成 ${expandedDialogueShots.filter(s => s.audioUrl || s.audio_path).length}</span>
                        <span class="stat-item pending">待生成 ${expandedDialogueShots.filter(s => !(s.audioUrl || s.audio_path)).length}</span>
                    </div>
                    <div class="toolbar-actions">
                        ${ttsConfigured ?
                            '<button class="toolbar-btn primary" onclick="shortDramaStudio.batchGenerateDubbing()"><span class="btn-icon">🎙️</span><span class="btn-text">全部生成配音</span></button>' :
                            '<button class="toolbar-btn warning" onclick="shortDramaStudio.showTTSConfig()"><span class="btn-icon">⚙️</span><span class="btn-text">配置API</span></button>'
                        }
                        <button class="toolbar-btn" onclick="shortDramaStudio.exportSubtitle()"><span class="btn-icon">📝</span><span class="btn-text">导出字幕</span></button>
                        <button class="toolbar-btn" onclick="shortDramaStudio.downloadAllAudio()"><span class="btn-icon">📦</span><span class="btn-text">打包下载</span></button>
                    </div>
                </div>

                <!-- 镜头列表 -->
                <div class="dubbing-scene-list">
                    ${scenesHtml}
                </div>
            </div>
        `;

        // 更新项目状态
        this.updateProjectStatus();
    }

    /**
     * 加载导出步骤
     */
    loadExportStep() {
        const container = document.getElementById('exportContent');
        if (!container) return;

        container.innerHTML = `
            <div class="export-section">
                <div class="empty-state">
                    <p style="font-size: 2rem;">📤</p>
                    <p>导出功能</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        完成视频生成后，可以在这里导出最终成片
                    </p>
                </div>
            </div>
        `;
    }

    /**
     * 轮询视频生成状态
     */
    pollVideoStatus(taskId, shotIndex) {
        return new Promise((resolve, reject) => {
            const maxAttempts = 120;
            let attempts = 0;
            const shot = this.shots[shotIndex];

            // 保存任务ID，用于后台任务跟踪
            shot.currentTaskId = taskId;

            const poll = async () => {
                try {
                    const response = await fetch(`/api/veo/status/${taskId}`);
                    const data = await response.json();

                    // 更新进度
                    let progress = 0;
                    let statusText = '处理中...';

                    if (data.status === 'processing' || data.status === 'pending') {
                        progress = 10 + (attempts / maxAttempts) * 50;
                    } else if (data.status === 'generating') {
                        progress = 60 + (data.progress || 0) * 0.4;
                        statusText = `生成中 ${data.progress || 0}%`;
                    }

                    // 更新弹窗进度
                    this.updateVideoProgressModal(Math.round(progress), statusText, shotIndex);

                    // 同时更新后台任务进度
                    this.updateBackgroundTaskProgress(taskId, Math.round(progress), statusText);

                    if (data.status === 'completed') {
                        // 视频生成完成
                        shot.generating = false;
                        shot.videoExists = true;
                        shot.hasError = false;
                        delete shot.currentTaskId;

                        // 🔥 修复：根据实际数据结构获取视频URL
                        // 数据格式: data.result.videos[0].url
                        if (data.result && data.result.videos && data.result.videos.length > 0) {
                            shot.videoUrl = data.result.videos[0].url;
                            shot.videoPath = data.result.videos[0].url;
                        } else if (data.result && data.result.video_url) {
                            // 兼容旧格式
                            shot.videoUrl = data.result.video_url;
                            shot.videoPath = data.result.video_path;
                        }

                        this.updateVideoProgressModal(100, '✅ 完成!', shotIndex, shot.videoUrl);
                        this.updateVideoCard(shotIndex);
                        this.updateProjectStatus();

                        // 移除后台任务
                        this.removeBackgroundTask(taskId);

                        this.showToast(`镜头 #${shot.shot_number || (shotIndex + 1)} 生成完成`, 'success');
                        resolve();

                    } else if (data.status === 'failed') {
                        shot.generating = false;
                        shot.hasError = true;
                        delete shot.currentTaskId;
                        this.updateVideoCard(shotIndex);
                        // 🔥 只关闭当前任务的弹窗，不影响其他任务
                        this.closeVideoProgressModal(shotIndex);
                        this.removeBackgroundTask(taskId);
                        reject(new Error(data.error || '生成失败'));
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000);
                    } else {
                        shot.generating = false;
                        shot.hasError = true;
                        delete shot.currentTaskId;
                        this.updateVideoCard(shotIndex);
                        // 🔥 只关闭当前任务的弹窗，不影响其他任务
                        this.closeVideoProgressModal(shotIndex);
                        this.removeBackgroundTask(taskId);
                        reject(new Error('生成超时'));
                    }
                } catch (error) {
                    console.error('检查状态失败:', error);
                    shot.generating = false;
                    shot.hasError = true;
                    delete shot.currentTaskId;
                    this.updateVideoCard(shotIndex);
                    // 🔥 只关闭当前任务的弹窗，不影响其他任务
                    this.closeVideoProgressModal(shotIndex);
                    this.removeBackgroundTask(taskId);
                    this.showToast(`镜头 #${shot.shot_number || (shotIndex + 1)} 生成失败: ${error.message}`, 'error');
                    reject(error);
                }
            };

            poll();
        });
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

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: videoSettings.model,
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
                        shot_number: String(shot.shot_number || (shotIndex + 1)),
                        shot_type: shot.shot_type || 'shot',
                        dialogue_index: shot.dialogue_index || 1,
                        lines_en: dialogueData?.lines_en || ''  // 传递英文台词
                    }
                })
            });

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

            const poll = async () => {
                try {
                    const response = await fetch(`/api/veo/status/${taskId}`);
                    const data = await response.json();

                    if (data.status === 'completed') {
                        shot.generating = false;
                        shot.videoExists = true;
                        shot.hasError = false;

                        // 🔥 修复：根据实际数据结构获取视频URL
                        // 数据格式: data.result.videos[0].url
                        if (data.result && data.result.videos && data.result.videos.length > 0) {
                            shot.videoUrl = data.result.videos[0].url;
                            shot.videoPath = data.result.videos[0].url;
                        } else if (data.result && data.result.video_url) {
                            // 兼容旧格式
                            shot.videoUrl = data.result.video_url;
                            shot.videoPath = data.result.video_path;
                        }

                        this.updateVideoCard(shotIndex);
                        this.updateProjectStatus();
                        this.showToast(`镜头 #${shot.shot_number || (shotIndex + 1)} 生成完成`, 'success');
                        resolve();

                    } else if (data.status === 'failed') {
                        shot.generating = false;
                        shot.hasError = true;
                        this.updateVideoCard(shotIndex);
                        resolve();
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000);
                    } else {
                        shot.generating = false;
                        shot.hasError = true;
                        this.updateVideoCard(shotIndex);
                        resolve();
                    }
                } catch (error) {
                    console.error('检查状态失败:', error);
                    shot.generating = false;
                    shot.hasError = true;
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
    loadProjectSettings(settings) {
        if (!settings) return;

        if (settings.aspect_ratio) {
            const aspectSelect = document.getElementById('settingAspectRatio');
            if (aspectSelect) aspectSelect.value = settings.aspect_ratio;
        }
        if (settings.quality) {
            const qualitySelect = document.getElementById('settingQuality');
            if (qualitySelect) qualitySelect.value = settings.quality;
        }
        if (settings.model) {
            const modelSelect = document.getElementById('settingModel');
            if (modelSelect) modelSelect.value = settings.model;
        }
    }

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
    async deleteProject(projectId) {
        if (!confirm('确定要删除这个项目吗？')) {
            return;
        }

        try {
            const response = await fetch(`/api/short-drama/projects/${projectId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('项目已删除', 'success');
                await this.loadProjects();
            } else {
                this.showToast(data.error || '删除失败', 'error');
            }
        } catch (error) {
            console.error('删除项目失败:', error);
            this.showToast('删除项目失败', 'error');
        }
    }

    /**
     * 返回项目列表
     */
    backToProjects() {
        document.getElementById('projectWorkspaceView').classList.remove('active');
        document.getElementById('projectListView').classList.add('active');
        this.currentProject = null;
        this.currentStep = 'select-episodes';
    }

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
    async saveProject() {
        if (!this.selectedNovel) {
            this.showToast('没有活动项目', 'warning');
            return;
        }

        try {
            // 查找现有项目
            const existingProject = this.projects.find(p => p.title === this.selectedNovel);
            const projectId = existingProject?.id;

            const settings = this.getProjectSettings();

            // 更新当前项目对象的设置
            if (this.currentProject) {
                this.currentProject.settings = settings;
            }

            if (projectId) {
                // 更新现有项目
                const response = await fetch(`/api/short-drama/projects/${projectId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: this.selectedNovel,
                        episodes: Array.from(this.selectedEpisodes),
                        characters: this.characters,
                        settings: settings
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.showToast('项目保存成功', 'success');
                    // 刷新项目列表
                    await this.loadProjects();
                } else {
                    this.showToast(data.error || '保存失败', 'error');
                }
            } else {
                // 创建新项目
                const response = await fetch('/api/short-drama/projects', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: this.selectedNovel,
                        episodes: Array.from(this.selectedEpisodes),
                        characters: this.characters,
                        settings: settings
                    })
                });

                const data = await response.json();
                if (data.success) {
                    this.showToast('项目保存成功', 'success');
                    await this.loadProjects();
                } else {
                    this.showToast(data.error || '保存失败', 'error');
                }
            }
        } catch (error) {
            console.error('保存项目失败:', error);
            this.showToast('保存项目失败', 'error');
        }
    }

    /**
     * 获取项目设置
     */
    getProjectSettings() {
        return {
            aspect_ratio: document.getElementById('settingAspectRatio')?.value || '9:16',
            quality: document.getElementById('settingQuality')?.value || '4K',
            model: document.getElementById('settingModel')?.value || 'veo_3_1-fast'
        };
    }

    /**
     * 更新项目状态显示
     */
    updateProjectStatus() {
        const episodesEl = document.getElementById('statusEpisodes');
        const portraitsEl = document.getElementById('statusPortraits');
        const shotsEl = document.getElementById('statusShots');
        const videosEl = document.getElementById('statusVideos');

        if (episodesEl) episodesEl.textContent = this.selectedEpisodes.length;
        if (portraitsEl) portraitsEl.textContent = this.characterPortraits.size;
        if (shotsEl) shotsEl.textContent = this.shots?.length || 0;
        if (videosEl) videosEl.textContent = '0'; // TODO: 计算已完成视频数
    }
}

// 初始化
const shortDramaStudio = new ShortDramaStudio();
// 暴露到全局作用域供inline onclick使用
window.shortDramaStudio = shortDramaStudio;
