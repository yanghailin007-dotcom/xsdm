/**
 * 短剧工作台 - 前端逻辑
 * 管理项目、角色、分镜头、视频生成等工作流
 */

class ShortDramaStudio {
    constructor() {
        this.currentProject = null;
        this.currentStep = 'characters';
        this.projects = [];
        this.novels = [];

        this.init();
    }

    async init() {
        console.log('🎬 短剧工作台初始化...');

        // 绑定事件
        this.bindEvents();

        // 加载项目列表
        await this.loadProjects();

        // 加载小说列表
        await this.loadNovels();

        console.log('✅ 短剧工作台初始化完成');
    }

    bindEvents() {
        // 步骤导航
        document.querySelectorAll('.step-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const step = item.dataset.step;
                if (this.currentProject) {
                    this.goToStep(step);
                }
            });
        });

        // 🔥 设置控件变更事件 - 自动保存
        const settingControls = [
            'settingAspectRatio',
            'settingQuality',
            'settingModel',
            'settingFirstLastFrame'
        ];
        
        settingControls.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => {
                    this.saveProjectSettings();
                });
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
            this.showToast('加载项目失败', 'error');
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
                    <p>📭 还没有项目</p>
                    <p style="font-size: 0.85rem; margin-top: 0.5rem;">点击"新建项目"或"导入小说"开始创建</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.projects.map(project => `
            <div class="project-card">
                <div class="project-card-header">
                    <div class="project-card-title">${project.title}</div>
                    <div class="project-card-badge ${project.status === 'completed' ? '' : 'pending'}">
                        ${project.status === 'completed' ? '✅ 完成' : '⏳ 进行中'}
                    </div>
                </div>

                <div class="project-card-meta">
                    <span>📊 ${project.episodes_count || 0}集</span>
                    <span>👥 ${project.characters_count || 0}角色</span>
                    <span>🎬 ${project.videos_count || 0}/${project.total_shots || 0}镜头</span>
                </div>

                <div class="project-card-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${project.progress || 0}%"></div>
                    </div>
                    <div class="project-card-stats">
                        <span>进度: ${project.progress || 0}%</span>
                        <span>更新: ${this.formatTime(project.updated_at)}</span>
                    </div>
                </div>

                <div class="project-card-actions">
                    <button class="btn btn-primary btn-sm" onclick="shortDramaStudio.openProject('${project.id}')">
                        📂 打开
                    </button>
                    <button class="btn btn-secondary btn-sm" onclick="shortDramaStudio.deleteProject('${project.id}')">
                        🗑️ 删除
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * 加载小说列表
     */
    async loadNovels() {
        try {
            const response = await fetch('/api/novels');
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
        select.innerHTML = '<option value="">选择小说项目...</option>' +
            this.novels.map(novel => `
                <option value="${novel.id}">${novel.title}</option>
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
            }
        } catch (error) {
            console.error('创建项目失败:', error);
            this.showToast('创建项目失败', 'error');
        }
    }

    /**
     * 从小说创建项目
     */
    async createFromNovel() {
        const novelId = document.getElementById('novelSelect').value;
        if (!novelId) {
            this.showToast('请选择小说项目', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/short-drama/projects/from-novel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ novel_id: novelId })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('项目创建成功', 'success');
                await this.loadProjects();
                document.getElementById('novelSelect').value = '';
            }
        } catch (error) {
            console.error('创建项目失败:', error);
            this.showToast('创建项目失败', 'error');
        }
    }

    /**
     * 打开项目
     */
    async openProject(projectId) {
        try {
            const response = await fetch(`/api/short-drama/projects/${projectId}`);
            const data = await response.json();

            if (data.success) {
                this.currentProject = data.project;
                this.showWorkspace();
                this.loadProjectData();
            }
        } catch (error) {
            console.error('打开项目失败:', error);
            this.showToast('打开项目失败', 'error');
        }
    }

    /**
     * 显示工作区
     */
    showWorkspace() {
        document.getElementById('projectListView').classList.remove('active');
        document.getElementById('projectWorkspaceView').classList.add('active');

        document.getElementById('currentProjectName').textContent = this.currentProject.title;

        this.goToStep('characters');
    }

    /**
     * 加载项目数据
     */
    async loadProjectData() {
        try {
            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}/data`);
            const data = await response.json();

            if (data.success) {
                this.currentProject = { ...this.currentProject, ...data.project };
                this.updateProjectStatus();
                this.renderEpisodesList();
                this.renderCharacters();
                this.renderStoryboard();
                this.loadProjectSettings();  // 🔥 加载项目设置
            }
        } catch (error) {
            console.error('加载项目数据失败:', error);
        }
    }

    /**
     * 🔥 加载项目设置到UI
     */
    loadProjectSettings() {
        const settings = this.currentProject?.settings || {};
        
        // 视频比例
        const aspectRatio = settings.aspect_ratio || '9:16';
        const ratioSelect = document.getElementById('settingAspectRatio');
        if (ratioSelect) ratioSelect.value = aspectRatio;
        
        // 视频质量
        const quality = settings.quality || '4K';
        const qualitySelect = document.getElementById('settingQuality');
        if (qualitySelect) qualitySelect.value = quality;
        
        // 生成模型
        const model = settings.model || 'veo_3_1-fast';
        const modelSelect = document.getElementById('settingModel');
        if (modelSelect) modelSelect.value = model;
        
        // 🔥 首尾帧模式（默认开启）
        const useFirstLastFrame = settings.use_first_last_frame !== false;  // 默认 true
        const firstLastFrameCheckbox = document.getElementById('settingFirstLastFrame');
        if (firstLastFrameCheckbox) firstLastFrameCheckbox.checked = useFirstLastFrame;
        
        console.log('🎬 项目设置已加载:', settings);
    }

    /**
     * 🔥 保存项目设置
     */
    async saveProjectSettings() {
        if (!this.currentProject) return;
        
        try {
            const settings = {
                aspect_ratio: document.getElementById('settingAspectRatio')?.value || '9:16',
                quality: document.getElementById('settingQuality')?.value || '4K',
                model: document.getElementById('settingModel')?.value || 'veo_3_1-fast',
                use_first_last_frame: document.getElementById('settingFirstLastFrame')?.checked ?? true
            };
            
            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ settings })
            });
            
            const data = await response.json();
            if (data.success) {
                this.currentProject.settings = settings;
                console.log('🎬 项目设置已保存:', settings);
            }
        } catch (error) {
            console.error('保存项目设置失败:', error);
        }
    }

    /**
     * 更新项目状态
     */
    updateProjectStatus() {
        const project = this.currentProject;

        document.getElementById('statusCharacters').textContent =
            `${project.characters_completed || 0}/${project.characters_count || 0}`;

        document.getElementById('statusShots').textContent =
            `${project.shots_completed || 0}/${project.total_shots || 0}`;

        document.getElementById('statusVideos').textContent =
            `${project.videos_completed || 0}/${project.total_shots || 0}`;
    }

    /**
     * 渲染章节列表
     */
    renderEpisodesList() {
        const container = document.getElementById('episodesList');
        const episodes = this.currentProject.episodes || [];

        if (episodes.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无章节</div>';
            return;
        }

        container.innerHTML = episodes.map((ep, idx) => `
            <div class="episode-item ${idx === 0 ? 'active' : ''}" onclick="shortDramaStudio.selectEpisode(${idx})">
                <div class="episode-info">
                    <div class="episode-title">${ep.title}</div>
                    <div class="episode-meta">${ep.shots_count || 0}个镜头</div>
                </div>
                <div class="episode-status ${ep.status}"></div>
            </div>
        `).join('');
    }

    /**
     * 渲染角色列表
     */
    renderCharacters() {
        const container = document.getElementById('charactersGrid');
        const characters = this.currentProject.characters || [];

        if (characters.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无角色</div>';
            return;
        }

        container.innerHTML = characters.map(char => `
            <div class="character-card">
                <div class="character-card-header">
                    <div class="character-avatar">
                        ${char.portrait_url ? `<img src="${char.portrait_url}" alt="${char.name}">` : '👤'}
                    </div>
                    <div class="character-info">
                        <div class="character-name">${char.name}</div>
                        <div class="character-role">${char.role || '配角'}</div>
                        <div class="character-status ${char.portrait_status || 'pending'}">
                            ${char.portrait_status === 'completed' ? '✅ 已生成' : '⏳ 待生成'}
                        </div>
                    </div>
                </div>
                <div class="character-actions">
                    <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generatePortrait('${char.id}')">
                        🎨 生成剧照
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="shortDramaStudio.editCharacter('${char.id}')">
                        ✏️ 编辑
                    </button>
                </div>
            </div>
        `).join('');
    }

    /**
     * 渲染分镜头
     */
    renderStoryboard() {
        const container = document.getElementById('storyboardContent');
        const episodes = this.currentProject.episodes || [];

        if (episodes.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无分镜头</div>';
            return;
        }

        const shots = episodes[0]?.shots || [];

        if (shots.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无镜头</div>';
            return;
        }

        container.innerHTML = `
            <div class="shots-list">
                ${shots.map((shot, idx) => `
                    <div class="shot-item">
                        <div class="shot-number">#${idx + 1}</div>
                        <div class="shot-info">
                            <div class="shot-type">${shot.shot_type || '镜头'}</div>
                            <div class="shot-duration">⏱️ ${shot.duration || 8}秒</div>
                        </div>
                        <div class="shot-status ${shot.status || 'pending'}">
                            ${this.getStatusText(shot.status)}
                        </div>
                        <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generateVideo('${shot.id}')">
                            🎬 生成
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * 获取状态文本
     */
    getStatusText(status) {
        const statusMap = {
            'pending': '⏸️ 待生成',
            'processing': '⏳ 处理中',
            'completed': '✅ 已完成',
            'failed': '❌ 失败'
        };
        return statusMap[status] || '未知';
    }

    /**
     * 切换步骤
     */
    goToStep(step) {
        this.currentStep = step;

        // 更新步骤导航
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

        // 控制左右面板显示/隐藏：只在"选集"步骤显示面板
        const workspaceContent = document.getElementById('workspaceContent');
        if (workspaceContent) {
            if (step === 'select-episodes') {
                workspaceContent.classList.remove('hide-side-panels');
            } else {
                workspaceContent.classList.add('hide-side-panels');
            }
        }

        // 根据步骤加载对应内容
        if (step === 'video') {
            this.renderVideoStep();
        } else if (step === 'dubbing') {
            this.renderDubbingStep();
        } else if (step === 'storyboard') {
            this.renderStoryboardStep();
        } else if (step === 'story-beats') {
            this.renderStoryBeatsStep();
        } else if (step === 'check-portraits') {
            this.renderPortraitsStep();
        }
    }

    /**
     * 渲染视频生成步骤
     */
    renderVideoStep() {
        const container = document.getElementById('videoContent');
        if (!container) return;
        
        // 如果没有项目数据，显示空状态
        if (!this.currentProject || !this.currentProject.episodes) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬</p>
                    <p>暂无视频生成任务</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">请先完成分镜头脚本</p>
                </div>
            `;
            return;
        }

        // 渲染视频生成界面
        this.loadVideoShots();
    }

    /**
     * 渲染配音制作步骤
     */
    renderDubbingStep() {
        const container = document.getElementById('dubbingContent');
        if (!container) return;
        
        // 如果没有项目数据，显示空状态
        if (!this.currentProject || !this.currentProject.episodes) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎙️</p>
                    <p>暂无配音任务</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">请先完成视频生成</p>
                </div>
            `;
            return;
        }

        // 渲染配音界面
        this.loadDubbingShots();
    }

    /**
     * 渲染故事节拍步骤
     */
    renderStoryBeatsStep() {
        const container = document.getElementById('storyBeatsContent');
        if (!container) return;
        
        if (!this.currentProject || !this.currentProject.episodes) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📝</p>
                    <p>请先生成故事节拍</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">AI将根据集数内容生成叙事节拍，包括场景划分、情绪曲线、对白设计</p>
                </div>
            `;
            return;
        }

        // 如果已有故事节拍数据，渲染编辑器
        if (this.currentProject.storyBeats) {
            this.renderStoryBeatsEditor();
        } else {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📝</p>
                    <p>请先生成故事节拍</p>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryBeats()" style="margin-top: 1rem;">
                        🚀 生成故事节拍
                    </button>
                </div>
            `;
        }
    }

    /**
     * 生成故事节拍
     */
    async generateStoryBeats() {
        if (!this.currentProject || !this.currentProject.episodes) {
            this.showToast('请先选择集数', 'warning');
            return;
        }

        const button = document.querySelector('#storyBeatsStep .btn-primary');
        if (button) {
            button.disabled = true;
            button.innerHTML = '⏳ 生成中...';
        }

        try {
            const response = await fetch('/api/short-drama/story-beats/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    projectId: this.currentProject.id,
                    episodeId: this.currentProject.episodes[0]?.id
                })
            });

            const data = await response.json();

            if (data.success) {
                this.currentProject.storyBeats = data.storyBeats;
                this.renderStoryBeatsEditor();
                this.showToast('故事节拍生成成功', 'success');
                this.updateProjectStatus();
            } else {
                this.showToast(data.message || '生成失败', 'error');
            }
        } catch (error) {
            console.error('生成故事节拍失败:', error);
            this.showToast('生成故事节拍失败', 'error');
        } finally {
            if (button) {
                button.disabled = false;
                button.innerHTML = '🚀 生成故事节拍';
            }
        }
    }

    /**
     * 渲染故事节拍编辑器
     */
    renderStoryBeatsEditor() {
        const container = document.getElementById('storyBeatsContent');
        const storyBeats = this.currentProject?.storyBeats;
        
        if (!storyBeats || !storyBeats.scenes) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📝</p>
                    <p>暂无故事节拍数据</p>
                </div>
            `;
            return;
        }

        const totalDuration = storyBeats.scenes.reduce((sum, scene) => sum + (scene.durationSeconds || 0), 0);

        let html = `
            <div class="story-beats-header" style="margin-bottom: 1.5rem; padding: 1rem; background: rgba(99, 102, 241, 0.1); border-radius: 0.75rem; border: 1px solid rgba(99, 102, 241, 0.2);">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="font-size: 1rem; color: var(--text-primary); margin: 0;">故事节拍概览</h3>
                    <span style="font-size: 0.875rem; color: var(--text-secondary);">${storyBeats.scenes.length} 场景 | ${totalDuration}秒</span>
                </div>
                <div style="display: flex; gap: 1rem; font-size: 0.875rem; color: var(--text-tertiary);">
                    <span>第一幕: 建立 (0-${Math.round(totalDuration * 0.3)}秒)</span>
                    <span>第二幕: 对抗 (${Math.round(totalDuration * 0.3)}-${Math.round(totalDuration * 0.7)}秒)</span>
                    <span>第三幕: 高潮 (${Math.round(totalDuration * 0.7)}-${totalDuration}秒)</span>
                </div>
            </div>
            <div class="story-beats-list" style="display: flex; flex-direction: column; gap: 1rem;">
        `;

        storyBeats.scenes.forEach((scene, index) => {
            const startTime = storyBeats.scenes.slice(0, index).reduce((sum, s) => sum + (s.durationSeconds || 0), 0);
            const endTime = startTime + (scene.durationSeconds || 0);
            
            html += `
                <div class="scene-card" style="background: var(--bg-secondary); border-radius: 0.75rem; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                        <div>
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                                <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; padding: 0.125rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">场景 ${index + 1}</span>
                                <span style="font-size: 0.75rem; color: var(--text-tertiary);">${startTime}-${endTime}秒</span>
                            </div>
                            <h4 style="font-size: 1rem; color: var(--text-primary); margin: 0;">${scene.sceneTitleCn || '未命名场景'}</h4>
                            <p style="font-size: 0.75rem; color: var(--text-tertiary); margin: 0.25rem 0 0 0;">${scene.sceneTitleEn || ''}</p>
                        </div>
                        <span style="font-size: 0.875rem; color: var(--text-secondary); background: rgba(255, 255, 255, 0.05); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">${scene.durationSeconds || 0}秒</span>
                    </div>
                    
                    <div style="margin-bottom: 0.75rem;">
                        <p style="font-size: 0.875rem; color: var(--text-secondary); margin: 0; line-height: 1.5;">
                            <strong style="color: var(--text-primary);">叙事目的:</strong> ${scene.storyBeatCn || '-'}
                        </p>
                    </div>

                    <div style="margin-bottom: 0.75rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <span style="font-size: 0.75rem; color: var(--text-tertiary);">情绪曲线:</span>
                            <span style="font-size: 0.875rem; color: var(--text-primary);">${scene.emotionalArc || '-'}</span>
                        </div>
                        <div style="height: 4px; background: rgba(255, 255, 255, 0.1); border-radius: 2px; overflow: hidden;">
                            <div style="height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); width: 100%;"></div>
                        </div>
                    </div>

                    ${scene.dialogues && scene.dialogues.length > 0 ? `
                        <div style="background: rgba(0, 0, 0, 0.2); border-radius: 0.5rem; padding: 0.75rem;">
                            <p style="font-size: 0.75rem; color: var(--text-tertiary); margin: 0 0 0.5rem 0;">对白:</p>
                            ${scene.dialogues.map(d => `
                                <div style="margin-bottom: 0.5rem;">
                                    <span style="font-size: 0.75rem; color: #818cf8; margin-right: 0.5rem;">${d.speaker}</span>
                                    <span style="font-size: 0.875rem; color: var(--text-primary);">${d.linesCn || d.lines || '-'}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        });

        html += `
            </div>
            <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: center;">
                <button class="btn btn-secondary" onclick="shortDramaStudio.generateStoryBeats()">
                    🔄 重新生成
                </button>
                <button class="btn btn-primary" onclick="shortDramaStudio.goToStep('storyboard')">
                    ✓ 确认并进入分镜生成 →
                </button>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * 渲染分镜头步骤
     */
    renderStoryboardStep() {
        const container = document.getElementById('storyboardContent');
        if (!container) return;
        
        if (!this.currentProject || !this.currentProject.episodes) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬</p>
                    <p>暂无分镜头</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">请先选择集数并生成剧本</p>
                </div>
            `;
            return;
        }

        this.renderShotsList();
    }

    /**
     * 渲染角色剧照步骤
     */
    renderPortraitsStep() {
        if (!this.currentProject) return;
        this.renderCharactersList();
    }

    /**
     * 加载视频镜头列表
     */
    async loadVideoShots() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        // 获取所有镜头
        const episodes = this.currentProject?.episodes || [];
        let allShots = [];
        episodes.forEach(ep => {
            if (ep.shots) {
                allShots = allShots.concat(ep.shots);
            }
        });

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬</p>
                    <p>暂无镜头</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">请先生成分镜头脚本</p>
                </div>
            `;
            return;
        }

        // 🔥 加载项目的参考图
        const referenceImages = await this.loadReferenceImages();

        // 渲染任务列表 - 使用 task-row 布局
        container.innerHTML = `
            <div class="batch-generate-panel">
                <h3>🚀 批量生成设置</h3>
                <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                    <span style="color: var(--text-secondary);">共 ${allShots.length} 个镜头</span>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateAllVideos()">
                        🎬 批量生成全部视频
                    </button>
                </div>
            </div>
            <div class="video-tasks-list">
                ${allShots.map((shot, idx) => this.renderVideoTaskRow(shot, idx, referenceImages)).join('')}
            </div>
        `;
    }

    /**
     * 加载项目的参考图
     */
    async loadReferenceImages() {
        try {
            const novelTitle = this.currentProject?.title;
            const episodeTitle = this.currentProject?.episodes?.[0]?.title || '1集_创意导入';
            
            if (!novelTitle) return [];

            const response = await fetch(`/api/short-drama/reference-images?novel=${encodeURIComponent(novelTitle)}&episode=${encodeURIComponent(episodeTitle)}`);
            const data = await response.json();

            if (data.success && data.images) {
                return data.images.map(img => img.url);
            }
        } catch (error) {
            console.error('加载参考图失败:', error);
        }
        return [];
    }

    /**
     * 渲染单个视频任务行
     */
    renderVideoTaskRow(shot, idx, projectReferenceImages = []) {
        const status = shot.status || 'pending';
        const isCompleted = status === 'completed' || status === 'done';
        const isProcessing = status === 'processing';
        
        // 🔥 获取参考图 - 支持多种字段名
        let refImages = [];
        if (shot.reference_images && shot.reference_images.length > 0) {
            refImages = shot.reference_images;
        } else if (shot.reference_image_urls && shot.reference_image_urls.length > 0) {
            refImages = shot.reference_image_urls;
        } else if (shot.reference_portraits && shot.reference_portraits.length > 0) {
            // 从角色肖像中提取URL
            refImages = shot.reference_portraits.map(p => p.portrait_url || p.image_url).filter(Boolean);
        } else if (shot.image_url) {
            refImages = [shot.image_url];
        } else if (isCompleted && projectReferenceImages.length > 0) {
            // 🔥 已完成任务使用项目的参考图
            refImages = projectReferenceImages;
        }
        
        // 参考图 HTML - 所有状态都显示
        let refsHtml = '';
        if (refImages.length > 0) {
            refsHtml = `
                <div class="refs-thumbnails">
                    ${refImages.slice(0, 2).map(img => `
                        <div class="ref-thumb">
                            <img src="${img}" alt="参考" onerror="this.style.display='none'">
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // 视频预览 HTML
        let videoHtml = '';
        if (isCompleted && shot.video_url) {
            videoHtml = `
                <div class="task-video-preview" onclick="shortDramaStudio.previewVideo('${shot.id}')">
                    <video src="${shot.video_url}" preload="metadata" muted></video>
                    <div class="play-icon">▶</div>
                </div>
            `;
        } else if (isProcessing) {
            videoHtml = `
                <div class="task-video-preview">
                    <div class="generating-indicator">
                        <div class="spinner" style="width: 20px; height: 20px;"></div>
                        <span style="font-size: 0.7rem; color: var(--text-secondary);">生成中</span>
                    </div>
                </div>
            `;
        } else {
            videoHtml = `
                <div class="task-video-placeholder" onclick="shortDramaStudio.generateVideo('${shot.id}')">
                    <span>⏳</span>
                </div>
            `;
        }
        
        // 操作按钮
        let actionHtml = '';
        if (isCompleted) {
            actionHtml = `
                <button class="btn btn-sm btn-secondary" onclick="shortDramaStudio.previewVideo('${shot.id}')">
                    👁️ 预览
                </button>
            `;
        } else if (isProcessing) {
            actionHtml = `
                <button class="btn btn-sm" disabled>
                    ⏳ 处理中
                </button>
            `;
        } else {
            actionHtml = `
                <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generateVideo('${shot.id}')">
                    🎬 生成
                </button>
            `;
        }
        
        // 🔥 已完成任务添加 completed 类用于样式区分
        const completedClass = isCompleted ? 'task-completed' : '';
        
        return `
            <div class="task-row ${status} ${completedClass}">
                <div class="task-number">#${idx + 1}</div>
                <div class="task-info">
                    <div class="task-title">${shot.shot_type || '镜头'}</div>
                    <div class="task-desc">${shot.description ? shot.description.substring(0, 50) + '...' : '暂无描述'} · ⏱️ ${shot.duration || 5}秒</div>
                    <div class="task-status-row">
                        <span class="status-badge ${status}">${this.getStatusText(status)}</span>
                    </div>
                </div>
                <div class="task-visual">
                    ${refsHtml}
                    ${videoHtml}
                </div>
                <div class="task-actions">
                    ${actionHtml}
                </div>
                <div class="task-meta">
                    <span style="font-size: 0.75rem; color: var(--text-secondary);">${shot.duration || 8}秒</span>
                </div>
            </div>
        `;
    }

    /**
     * 加载配音镜头列表
     */
    async loadDubbingShots() {
        const container = document.getElementById('dubbingContent');
        if (!container) return;

        // 获取已完成视频的镜头
        const episodes = this.currentProject?.episodes || [];
        let allShots = [];
        episodes.forEach(ep => {
            if (ep.shots) {
                allShots = allShots.concat(ep.shots.filter(s => s.status === 'completed'));
            }
        });

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎙️</p>
                    <p>暂无可配音的镜头</p>
                    <p style="font-size: 0.875rem; margin-top: 0.5rem;">请先完成视频生成</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="batch-generate-panel">
                <h3>🎙️ 批量配音设置</h3>
                <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap;">
                    <span style="color: var(--text-secondary);">共 ${allShots.length} 个镜头待配音</span>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateAllDubbing()">
                        🎙️ 批量生成全部配音
                    </button>
                </div>
            </div>
            <div class="dubbing-list">
                ${allShots.map((shot, idx) => `
                    <div class="dubbing-item">
                        <div class="dubbing-index">#${idx + 1}</div>
                        <div class="dubbing-info">
                            <div class="dubbing-type">${shot.shot_type || '镜头'}</div>
                            <div class="dubbing-dialogue">📝 ${shot.dialogue ? shot.dialogue.substring(0, 50) + '...' : '无台词'}</div>
                        </div>
                        <div class="dubbing-status ${shot.dubbing_status || 'pending'}">
                            ${this.getStatusText(shot.dubbing_status)}
                        </div>
                        ${shot.dubbing_status !== 'completed' ? `
                            <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.generateDubbing('${shot.id}')">
                                🎙️ 生成
                            </button>
                        ` : `
                            <button class="btn btn-sm btn-secondary" onclick="shortDramaStudio.playDubbing('${shot.id}')">
                                ▶️ 播放
                            </button>
                        `}
                    </div>
                `).join('')}
            </div>
        `;
    }

    /**
     * 批量生成所有视频
     */
    async generateAllVideos() {
        this.showToast('开始批量生成视频...', 'info');
        // 实现批量生成逻辑
    }

    /**
     * 批量生成所有配音
     */
    async generateAllDubbing() {
        this.showToast('开始批量生成配音...', 'info');
        // 实现批量生成逻辑
    }

    /**
     * 生成单个配音
     */
    async generateDubbing(shotId) {
        this.showToast('正在生成配音...', 'info');
        // 实现生成逻辑
    }

    /**
     * 预览视频
     */
    previewVideo(shotId) {
        this.showToast('视频预览功能开发中...', 'info');
    }

    /**
     * 播放配音
     */
    playDubbing(shotId) {
        this.showToast('播放配音功能开发中...', 'info');
    }

    /**
     * 显示VeO配置
     */
    showVeOConfig() {
        this.showToast('VeO配置功能开发中...', 'info');
    }

    /**
     * 显示TTS配置
     */
    showTTSConfig() {
        this.showToast('TTS配置功能开发中...', 'info');
    }

    /**
     * 添加角色
     */
    addCharacter() {
        const name = prompt('请输入角色名称:');
        if (!name) return;

        // 这里可以打开一个模态框进行详细编辑
        this.showToast('功能开发中...', 'info');
    }

    /**
     * 编辑角色
     */
    editCharacter(characterId) {
        this.showToast('功能开发中...', 'info');
    }

    /**
     * 生成角色剧照
     */
    async generatePortrait(characterId) {
        this.showToast('正在生成剧照...', 'info');

        try {
            const response = await fetch(`/api/short-drama/characters/${characterId}/portrait`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: this.currentProject.id
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('剧照生成成功', 'success');
                await this.loadProjectData();
            }
        } catch (error) {
            console.error('生成剧照失败:', error);
            this.showToast('生成剧照失败', 'error');
        }
    }

    /**
     * 生成视频
     */
    async generateVideo(shotId) {
        this.showToast('正在生成视频...', 'info');

        try {
            // 🔥 查找对应的 shot 对象
            let targetShot = null;
            let targetEpisode = null;
            const episodes = this.currentProject?.episodes || [];
            for (const ep of episodes) {
                const shot = ep.shots?.find(s => s.id === shotId);
                if (shot) {
                    targetShot = shot;
                    targetEpisode = ep;
                    break;
                }
            }

            if (!targetShot) {
                this.showToast('找不到对应的镜头', 'error');
                return;
            }

            // 🔥 构建生成参数
            const requestBody = {
                project_id: this.currentProject.id,
                prompt: targetShot.generation_prompt || targetShot.description || '',
                image_urls: targetShot.reference_images || targetShot.reference_image_urls || [],
                orientation: targetShot.orientation || 'portrait',
                duration: targetShot.duration || 8,  // 🔥 VeO API 只支持 8 秒
                // 元数据
                novel_title: this.currentProject.novel_title || this.currentProject.title,
                episode_title: targetEpisode.title,
                event_name: targetShot.event_name || '',
                scene_number: targetShot.scene_number || 1,
                shot_number: targetShot.shot_number || '1',
                shot_type: targetShot.shot_type || 'shot'
            };

            console.log('🎬 提交视频生成任务:', requestBody);

            const response = await fetch(`/api/short-drama/shots/${shotId}/video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('视频生成任务已提交', 'success');
                // 更新 shot 状态
                targetShot.status = 'processing';
                targetShot.video_task_id = data.task_id;
                // 刷新显示
                this.renderStoryboard();
                // 轮询检查状态
                this.pollVideoStatus(shotId);
            } else {
                this.showToast(data.error || '提交任务失败', 'error');
            }
        } catch (error) {
            console.error('生成视频失败:', error);
            this.showToast('生成视频失败', 'error');
        }
    }

    /**
     * 轮询视频生成状态
     */
    async pollVideoStatus(shotId) {
        const maxAttempts = 120; // 10分钟
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`/api/short-drama/shots/${shotId}/status`);
                const data = await response.json();

                if (data.success) {
                    if (data.status === 'completed') {
                        this.showToast('视频生成完成', 'success');
                        await this.loadProjectData();
                    } else if (data.status === 'failed') {
                        // 🔥 显示具体的错误信息
                        const errorMsg = data.error || '未知错误';
                        this.showToast(`视频生成失败: ${errorMsg}`, 'error');
                        console.error(`视频生成失败 [shotId=${shotId}]:`, errorMsg);
                        
                        // 🔥 更新 shot 状态并刷新 UI
                        let targetShot = null;
                        const episodes = this.currentProject?.episodes || [];
                        for (const ep of episodes) {
                            const shot = ep.shots?.find(s => s.id === shotId);
                            if (shot) {
                                targetShot = shot;
                                break;
                            }
                        }
                        if (targetShot) {
                            targetShot.status = 'failed';
                            targetShot.error_message = errorMsg;
                            this.renderStoryboard();
                        }
                    } else if (attempts < maxAttempts) {
                        attempts++;
                        setTimeout(poll, 5000); // 每5秒检查一次
                    }
                }
            } catch (error) {
                console.error('检查视频状态失败:', error);
            }
        };

        poll();
    }

    /**
     * 保存项目
     */
    async saveProject() {
        try {
            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.currentProject)
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('项目已保存', 'success');
            }
        } catch (error) {
            console.error('保存项目失败:', error);
            this.showToast('保存项目失败', 'error');
        }
    }

    /**
     * 导出项目
     */
    async exportProject() {
        this.showToast('导出功能开发中...', 'info');
    }

    /**
     * 删除项目
     */
    async deleteProject(projectId) {
        if (!confirm('确定要删除这个项目吗？')) return;

        try {
            const response = await fetch(`/api/short-drama/projects/${projectId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('项目已删除', 'success');
                await this.loadProjects();
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
    }

    /**
     * 选择章节
     */
    selectEpisode(index) {
        // 更新UI
        document.querySelectorAll('.episode-item').forEach((item, idx) => {
            item.classList.toggle('active', idx === index);
        });
    }

    /**
     * 显示Toast通知
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    /**
     * 格式化时间
     */
    formatTime(timestamp) {
        if (!timestamp) return '未知';

        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return '刚刚';
        if (minutes < 60) return `${minutes}分钟前`;
        if (hours < 24) return `${hours}小时前`;
        if (days < 7) return `${days}天前`;

        return date.toLocaleDateString('zh-CN');
    }
}

// 初始化
const shortDramaStudio = new ShortDramaStudio();
