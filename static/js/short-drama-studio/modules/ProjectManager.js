/**
 * 项目管理模块
 * Project Manager Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.ProjectManagerMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
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

        renderProjectsList() {
            const container = document.getElementById('projectsList');

            if (this.projects.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">📭</p>
                        <p>还没有项目</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">
                            从小说创建项目，或从创意快速导入
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

            // 直接生成项目卡片，不嵌套projects-grid
            container.innerHTML = this.projects.map(project => {
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
                            <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); shortDramaStudio.openProject('${project.id}')">📂 打开</button>
                            <button class="btn btn-sm btn-danger" onclick="event && event.stopPropagation(); event && event.preventDefault(); return shortDramaStudio.deleteProject('${project.id}');">🗑️ 删除</button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        async loadEventsAndCharacters() {
            try {
                // 加载事件数据
                const eventsResponse = await fetch(`/api/video/novel-content?title=${encodeURIComponent(this.selectedNovel)}`);
                const eventsData = await eventsResponse.json();

                console.log('📊 API 返回数据:', eventsData);

                if (eventsData.success) {
                    // 🔥 检查是否是创意导入项目
                    const isCreativeProject = eventsData.is_creative_project || false;
                    this.isCreativeProject = isCreativeProject; // 保存为实例属性
                    console.log('📝 [创意导入] 是否为创意项目:', isCreativeProject);

                    // 构建事件树
                    this.events = this.buildEventTree(eventsData);
                    console.log('✅ [工作流] 加载事件:', this.events.length);

                    // 🔥 如果是创意导入项目且只有一个事件，自动选择它
                    if (isCreativeProject && this.events.length === 1) {
                        this.selectedMajorEvent = this.events[0];
                        // 同时添加到 selectedEpisodes，确保步骤依赖检查通过
                        const eventId = this.events[0].id;
                        if (eventId && !this.selectedEpisodes.includes(eventId)) {
                            this.selectedEpisodes.push(eventId);
                        }
                        console.log('📝 [创意导入] 自动选择唯一事件:', this.selectedMajorEvent);
                        console.log('📝 [创意导入] 已自动加入selectedEpisodes:', this.selectedEpisodes);
                    }

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

            // 🔥 从项目数据中恢复配音音色映射
            if (this.currentProject && this.currentProject.character_voice_map) {
                this.characterVoiceMap = this.currentProject.character_voice_map;
                console.log('🎙️ [配音] 恢复角色-音色映射:', this.characterVoiceMap);
            }
        }

        async deleteProject(projectId) {
            // 显示确认对话框 - 确保用户确认
            const message = '确定要删除这个项目吗？\n\n此操作不可撤销！';
            const confirmed = window.confirm(message);
            
            if (confirmed !== true) {
                console.log('[删除] 用户取消删除, projectId:', projectId);
                return false;
            }
            
            console.log('[删除] 用户确认删除, projectId:', projectId);

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

        backToProjects() {
            document.getElementById('projectWorkspaceView').classList.remove('active');
            document.getElementById('projectListView').classList.add('active');
            this.currentProject = null;
            this.currentStep = 'select-episodes';
        }

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
                            settings: settings,
                            character_voice_map: this.characterVoiceMap  // 🔥 保存配音音色映射
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
                            settings: settings,
                            character_voice_map: this.characterVoiceMap  // 🔥 保存配音音色映射
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

        getProjectSettings() {
            return {
                aspect_ratio: document.getElementById('settingAspectRatio')?.value || '9:16',
                quality: document.getElementById('settingQuality')?.value || '4K',
                model: document.getElementById('settingModel')?.value || 'veo_3_1-fast'
            };
        }

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

        toggleProjectsSection() {
            const section = document.getElementById('projectsSection');
            const list = document.getElementById('projectsList');
            const titleBtn = section.querySelector('.section-title .btn-text');

            if (list.style.display === 'none') {
                // 展开
                list.style.display = 'grid';
                titleBtn.textContent = '▼ 收起';
            } else {
                // 收起
                list.style.display = 'none';
                titleBtn.textContent = '▶ 展开';
            }
        }

    };
}));
