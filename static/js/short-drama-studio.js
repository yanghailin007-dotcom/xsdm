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
        this.selectedNovel = null;
        this.selectedMajorEvent = null;
        this.selectedEpisodes = new Set();
        this.characterPortraits = new Map();
        this.shots = [];
        this.stopBatchGeneration = false;

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
                const epId = ep.id || `episode_${idx}`;
                const isChecked = this.selectedEpisodes.has(epId) ? 'checked' : '';
                const selectedClass = this.selectedEpisodes.has(epId) ? 'selected' : '';

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
            if (this.selectedEpisodes.size === 0) {
                this.selectAllEpisodes(true);
            }
        }
    }

    /**
     * 切换集数选择状态
     */
    toggleEpisodeSelection(episodeId, selected) {
        if (selected) {
            this.selectedEpisodes.add(episodeId);
        } else {
            this.selectedEpisodes.delete(episodeId);
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
            countSpan.textContent = this.selectedEpisodes.size;
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
                this.selectedEpisodes.add(episodeId);
            } else {
                this.selectedEpisodes.delete(episodeId);
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
            countSpan.textContent = this.selectedEpisodes.size;
        }

        // 更新项目状态
        this.updateProjectStatus();
    }

    /**
     * 切换工作流步骤
     */
    goToStep(step) {
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
        if (step === 'video') {
            workspace?.classList.add('video-mode');
        } else {
            workspace?.classList.remove('video-mode');
        }

        // 根据步骤加载内容
        switch (step) {
            case 'check-portraits':
                this.loadCharacterPortraitsStep();
                break;
            case 'storyboard':
                this.loadStoryboardStep();
                break;
            case 'video':
                this.loadVideoStep();
                break;
            case 'export':
                this.loadExportStep();
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

                return `
                    <div class="character-card ${portraitInfo ? 'has-portrait' : ''}">
                        <div class="character-card-header">
                            <div class="character-avatar">
                                ${portraitInfo
                                    ? `<img src="${portraitInfo.mainPortrait.url}" alt="${charName}" onerror="this.parentElement.innerHTML='<span style=\\'font-size: 2rem;\\'>👤</span>'">`
                                    : '<span style="font-size: 2rem;">👤</span>'
                                }
                            </div>
                            <div class="character-info">
                                <div class="character-name">${charName}</div>
                                <div class="character-role">${charRole}</div>
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
    async generatePortrait(characterName) {
        const character = this.characters.find(c => c.name === characterName);
        if (!character) {
            this.showToast('找不到角色信息', 'error');
            return;
        }

        // 打开剧照生成页面
        const episodeDirectoryName = this.getEpisodeDirectoryName();
        window.location.href = `/portrait-studio?novel=${encodeURIComponent(this.selectedNovel)}&character=${encodeURIComponent(characterName)}&episode=${encodeURIComponent(episodeDirectoryName)}`;
    }

    /**
     * 获取剧集目录名称
     */
    getEpisodeDirectoryName() {
        if (!this.selectedMajorEvent) return '默认';

        const majorIndex = this.events.findIndex(e => e.id === this.selectedMajorEvent.id);
        const sanitize = (name) => name.replace(/[<>:"/\\|?]/g, '_');
        const eventTitle = sanitize(this.selectedMajorEvent.title || this.selectedMajorEvent.name);

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
                         style="cursor: pointer; border: 2px solid ${p.url === mainPortrait.url ? 'var(--primary)' : 'var(--border)'}; border-radius: 8px; overflow: hidden;">
                        <img src="${p.url}" alt="造型${p.number > 0 ? '_' + p.number : ''}"
                             style="width: 100%; height: 100px; object-fit: cover; display: block;">
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
                    <h2 style="margin: 0;">${characterName}</h2>
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

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>正在生成分镜头...</p></div>';

        try {
            const selectedEpisodesList = Array.from(this.selectedEpisodes);

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

            if (data.success && data.storyboard) {
                this.currentProject = { ...this.currentProject, storyboard: data.storyboard };
                this.renderStoryboard(data.storyboard);
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>分镜头生成失败</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${data.error || ''}</p>
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
                </div>
            `;
        }
    }

    /**
     * 渲染分镜头（从本地文件加载）
     */
    renderStoryboards(storyboards) {
        const container = document.getElementById('storyboardContent');
        if (!container) return;

        // 收集所有镜头
        const allShots = [];
        let episodeIndex = 0;

        for (const [title, data] of Object.entries(storyboards)) {
            const shots = data.shots || [];
            for (const shot of shots) {
                allShots.push({
                    ...shot,
                    episode_title: title,
                    episode_index: episodeIndex
                });
            }
            episodeIndex++;
        }

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
                    共 <strong>${allShots.length}</strong> 个镜头（从 ${Object.keys(storyboards).length} 个分镜头文件加载）
                </p>
            </div>
            <div class="shots-list">
                ${allShots.map((shot, idx) => `
                    <div class="shot-item" id="storyboardShot_${idx}">
                        <div class="shot-number">#${shot.shot_number || (idx + 1)}</div>
                        <div class="shot-info">
                            <div class="shot-type">${shot.shot_type || '镜头'}</div>
                            <div class="shot-duration">⏱️ ${shot.duration || 5}秒</div>
                            <div class="shot-episode" style="font-size: 0.75rem; color: var(--text-tertiary);">${shot.episode_title || ''}</div>
                            <div class="shot-desc">${shot.veo_prompt?.substring(0, 100) || shot.screen_action?.substring(0, 100) || ''}...</div>
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

        for (const [epId, epData] of Object.entries(storyboard)) {
            const scenes = epData.scenes || [];
            for (const scene of scenes) {
                const shots = scene.shot_sequence || [];
                for (const shot of shots) {
                    if (shot.veo_prompt) {
                        allShots.push({
                            ...shot,
                            episode_id: epId,
                            episode_title: epData.title,
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
                        <div class="shot-number">#${idx + 1}</div>
                        <div class="shot-info">
                            <div class="shot-type">${shot.shot_type || '镜头'}</div>
                            <div class="shot-duration">⏱️ ${shot.duration || 5}秒</div>
                            <div class="shot-desc">${shot.veo_prompt?.substring(0, 100)}...</div>
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
        const videosDir = `视频项目/${this.selectedNovel}/${episodeDirectoryName}/videos`;

        // 为每个镜头检查视频是否存在
        for (let i = 0; i < this.shots.length; i++) {
            const shot = this.shots[i];
            const videoFileName = this.sanitizeFileName(`${shot.shot_number || (i + 1)}_${shot.shot_type || 'shot'}.mp4`);
            const videoPath = `${videosDir}/${videoFileName}`;

            // 这里可以通过 API 检查文件是否存在
            try {
                const response = await fetch(`/api/short-drama/check-video?path=${encodeURIComponent(videoPath)}`);
                const data = await response.json();

                if (data.exists) {
                    shot.videoExists = true;
                    shot.videoPath = data.path || videoPath;
                    shot.videoUrl = data.url || `/api/short-drama/video-file?path=${encodeURIComponent(videoPath)}`;
                }
            } catch (e) {
                console.log('检查视频失败:', e);
            }
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
                        <button class="toolbar-btn primary" onclick="shortDramaStudio.batchGenerateFirstFive()">
                            <span class="btn-icon">🚀</span>
                            <span class="btn-text">批量生成（前5个）</span>
                        </button>
                    </div>
                </div>
                <div class="video-task-list">
                    ${this.shots.map((shot, idx) => this.renderVideoTaskRow(shot, idx)).join('')}
                </div>
            </div>
        `;
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

        // 参考图（如果有）
        const referenceImages = shot.reference_images || [];
        const thumbnailHtml = referenceImages.length > 0
            ? `<div class="task-thumbnail">
                <img src="${referenceImages[0]}" alt="参考图" onerror="this.parentElement.innerHTML='<span class=\\'no-image\\'>📷</span>'">
                ${referenceImages.length > 1 ? `<span class="thumb-count">+${referenceImages.length - 1}</span>` : ''}
               </div>`
            : `<div class="task-thumbnail"><span class="no-image">📷</span></div>`;

        // 视频预览（如果已完成）
        const videoPreviewHtml = isCompleted && shot.videoUrl
            ? `<div class="task-video-preview" onclick="shortDramaStudio.previewVideo(${idx})">
                <video src="${shot.videoUrl}" muted preload="metadata"></video>
                <span class="play-icon">▶</span>
               </div>`
            : `<div class="task-video-placeholder">${isGenerating ? '<span class="spinner"></span>' : '⏳'}</div>`;

        return `
            <div class="task-row ${statusClass}" id="taskRow_${idx}">
                <div class="task-index">#${shot.shot_number || (idx + 1)}</div>
                <div class="task-content">
                    <div class="task-prompt">
                        <span class="prompt-label">提示词:</span>
                        <span class="prompt-text">${(shot.veo_prompt || shot.screen_action || '').substring(0, 150)}${(shot.veo_prompt || shot.screen_action || '').length > 150 ? '...' : ''}</span>
                    </div>
                    <div class="task-meta">
                        <span class="meta-tag">${shot.shot_type || '镜头'}</span>
                        <span class="meta-tag">⏱️ ${shot.duration || 5}秒</span>
                    </div>
                </div>
                <div class="task-visual">
                    ${thumbnailHtml}
                    <span class="visual-arrow">→</span>
                    ${videoPreviewHtml}
                </div>
                <div class="task-actions">
                    <button class="task-btn edit-btn" onclick="shortDramaStudio.editShotPrompt(${idx})" title="编辑提示词">
                        <span>✏️</span>
                    </button>
                    <button class="task-btn ${isCompleted ? 'view-btn' : 'generate-btn'}"
                            onclick="${isCompleted ? `shortDramaStudio.previewVideo(${idx})` : `shortDramaStudio.generateShotVideo(${idx})`}"
                            title="${isCompleted ? '查看视频' : '生成视频'}">
                        <span>${isCompleted ? '👁️' : '🎬'}</span>
                    </button>
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
     * 刷新视频状态
     */
    async refreshVideos() {
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

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'veo_3_1-fast',
                    prompt: shot.veo_prompt || shot.screen_action || '',
                    image_urls: [],
                    orientation: 'portrait',
                    size: 'large',
                    watermark: false,
                    private: true,
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        shot_number: String(shot.shot_number || (shotIndex + 1)),
                        shot_type: shot.shot_type || 'shot'
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
            this.closeVideoProgressModal();
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
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'videoProgressModal';
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

        // 绑定停止按钮
        modal.querySelector('#btnStopGeneration').onclick = () => {
            this.closeVideoProgressModal();
            this.showToast('已停止生成', 'info');
        };
    }

    /**
     * 更新视频进度弹窗（参考旧样式）
     */
    updateVideoProgressModal(progress, status, shotIndex = null, videoUrl = null) {
        const modal = document.getElementById('videoProgressModal');
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
                this.closeVideoProgressModal();
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

        return new Promise((resolve) => {
            // 默认不选中任何图片，让用户手动选择
            const selectedImages = [];
            const allPortraits = Array.from(characterPortraits.entries());

            // 生成唯一键用于保存/加载提示词
            const shotKey = `videoPrompt_${this.selectedNovel}_${shot.episode_title || ''}_${shot.shot_number || (idx + 1)}`;

            // 尝试加载之前保存的提示词
            const savedPrompt = localStorage.getItem(shotKey);
            const promptToUse = savedPrompt || shot.veo_prompt || shot.screen_action || '';

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

                        <!-- 参考角色剧照选择 -->
                        <div class="reference-section" style="margin-bottom: 20px;">
                            <label style="font-weight: 600; display: block; margin-bottom: 12px; font-size: 1rem;">🖼️ 选择参考角色剧照：</label>
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
                                        <input type="checkbox" class="portrait-check" data-name="${name}" data-url="${portraitUrl}"
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
                                `}).join('') : '<div style="color: var(--text-tertiary); padding: 20px;">暂无角色剧照，请先在"角色剧照"步骤生成</div>'}
                            </div>
                            <p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 12px;">
                                已选择 <span id="selectedCount" style="color: var(--primary); font-weight: 600;">0</span> 张参考图
                                ${allPortraits.length > 0 ? '<span style="color: var(--text-tertiary); margin-left: 16px;">💡 点击图片选择，首尾帧模式需要选择2张</span>' : ''}
                            </p>
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
                                        <option value="veo_3_1-fast-components" selected>参考图模式 (推荐)</option>
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
                                        <option value="portrait" selected>竖屏 (9:16)</option>
                                        <option value="landscape">横屏 (16:9)</option>
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
                                        <option value="large" selected>大尺寸 (1080p)</option>
                                        <option value="small">小尺寸 (720p)</option>
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
                    promptArea.value = shot.veo_prompt || shot.screen_action || '';
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

                console.log('选中的图片数量:', checkedImages.length);
                console.log('首尾帧模式:', useFirstLastFrame);

                // 首尾帧模式需要2张图片
                if (useFirstLastFrame && checkedImages.length !== 2) {
                    this.showToast('首尾帧模式需要选择2张图片（首帧+尾帧）', 'warning');
                    return;
                }

                // 保存修改的提示词
                if (editedPrompt !== (shot.veo_prompt || shot.screen_action || '')) {
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

        // 开始生成，显示进度弹窗
        this.showVideoProgressModal(shot, idx);

        shot.generating = true;
        shot.hasError = false;
        this.updateVideoCard(idx);

        try {
            const episodeDirectoryName = this.getEpisodeDirectoryName();

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
                        shot_type: shot.shot_type || 'shot'
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
            this.closeVideoProgressModal();

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
     * 重新生成视频
     */
    async regenerateVideo(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

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

                    this.updateVideoProgressModal(Math.round(progress), statusText, shotIndex);

                    if (data.status === 'completed') {
                        // 视频生成完成
                        shot.generating = false;
                        shot.videoExists = true;
                        shot.hasError = false;

                        if (data.result && data.result.video_url) {
                            shot.videoUrl = data.result.video_url;
                            shot.videoPath = data.result.video_path;
                        }

                        this.updateVideoProgressModal(100, '✅ 完成!', shotIndex, shot.videoUrl);
                        this.updateVideoCard(shotIndex);
                        this.updateProjectStatus();

                        this.showToast(`镜头 #${shot.shot_number || (shotIndex + 1)} 生成完成`, 'success');
                        resolve();

                    } else if (data.status === 'failed') {
                        shot.generating = false;
                        shot.hasError = true;
                        this.updateVideoCard(shotIndex);
                        this.closeVideoProgressModal();
                        reject(new Error(data.error || '生成失败'));
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000);
                    } else {
                        shot.generating = false;
                        shot.hasError = true;
                        this.updateVideoCard(shotIndex);
                        this.closeVideoProgressModal();
                        reject(new Error('生成超时'));
                    }
                } catch (error) {
                    console.error('检查状态失败:', error);
                    shot.generating = false;
                    shot.hasError = true;
                    this.updateVideoCard(shotIndex);
                    this.closeVideoProgressModal();
                    this.showToast(`生成失败: ${error.message}`, 'error');
                    reject(error);
                }
            };

            poll();
        });
    }

    /**
     * 关闭视频进度弹窗
     */
    closeVideoProgressModal() {
        const modal = document.getElementById('videoProgressModal');
        if (modal) modal.remove();
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

            const response = await fetch('/api/veo/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: 'veo_3_1-fast',
                    prompt: shot.veo_prompt || shot.screen_action || '',
                    image_urls: [],
                    orientation: 'portrait',
                    size: 'large',
                    watermark: false,
                    private: true,
                    metadata: {
                        novel_title: this.selectedNovel || '',
                        episode_title: episodeDirectoryName,
                        event_name: shot.episode_title || '',
                        shot_number: String(shot.shot_number || (shotIndex + 1)),
                        shot_type: shot.shot_type || 'shot'
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

                        if (data.result && data.result.video_url) {
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
     * 保存项目
     */
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

        if (episodesEl) episodesEl.textContent = this.selectedEpisodes.size;
        if (portraitsEl) portraitsEl.textContent = this.characterPortraits.size;
        if (shotsEl) shotsEl.textContent = this.shots?.length || 0;
        if (videosEl) videosEl.textContent = '0'; // TODO: 计算已完成视频数
    }
}

// 初始化
const shortDramaStudio = new ShortDramaStudio();
