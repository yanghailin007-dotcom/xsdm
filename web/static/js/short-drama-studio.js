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
            }
        } catch (error) {
            console.error('加载项目数据失败:', error);
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
                            <div class="shot-duration">⏱️ ${shot.duration || 5}秒</div>
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
            const response = await fetch(`/api/short-drama/shots/${shotId}/video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: this.currentProject.id
                })
            });

            const data = await response.json();
            if (data.success) {
                this.showToast('视频生成任务已提交', 'success');
                // 轮询检查状态
                this.pollVideoStatus(shotId);
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
                        this.showToast('视频生成失败', 'error');
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
