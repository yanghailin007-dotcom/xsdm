/**
 * 项目管理器 - JavaScript逻辑
 */

// 当前项目数据
let currentProjects = [];

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', async () => {
    await loadNovels();
    await loadProjects();
});

/**
 * 加载小说列表
 */
async function loadNovels() {
    const select = document.getElementById('novelSelect');

    try {
        const data = await videoAPI.getNovels();

        if (data.success && data.novels) {
            select.innerHTML = '<option value="">请选择小说...</option>' +
                data.novels.map(novel => `
                    <option value="${escapeHtml(novel.title)}">
                        ${escapeHtml(novel.title)}
                        ${novel.total_medium_events ? ` (${novel.total_medium_events} 个事件)` : ''}
                    </option>
                `).join('');
        }
    } catch (error) {
        console.error('加载小说列表失败:', error);
    }
}

/**
 * 加载项目列表
 */
async function loadProjects() {
    const container = document.getElementById('projectsContainer');
    const emptyState = document.getElementById('emptyState');

    try {
        const data = await videoAPI.getProjects();

        if (!data.projects || data.projects.length === 0) {
            container.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }

        currentProjects = data.projects;
        renderProjects(data.projects);

    } catch (error) {
        console.error('加载项目失败:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <p>加载失败，请刷新重试</p>
            </div>
        `;
    }
}

/**
 * 渲染项目列表
 */
function renderProjects(projects) {
    const container = document.getElementById('projectsContainer');
    const emptyState = document.getElementById('emptyState');

    if (!projects || projects.length === 0) {
        container.style.display = 'none';
        emptyState.style.display = 'block';
        return;
    }

    container.style.display = 'grid';
    emptyState.style.display = 'none';

    container.innerHTML = projects.map(project => `
        <div class="project-item" onclick="openProject('${project.id}')">
            <div class="project-cover">
                <div class="project-type-badge">
                    ${getTypeIcon(project.project_type || 'long_series')}
                </div>
                <div class="project-status-badge ${getStatusClass(project.status)}">
                    ${getStatusText(project.status)}
                </div>
            </div>
            <div class="project-content">
                <h3 class="project-title">${escapeHtml(project.title)}</h3>
                ${project.novel_title ? `<p class="project-novel">📖 ${escapeHtml(project.novel_title)}</p>` : ''}

                <div class="project-meta">
                    <div class="meta-item">
                        <span>📊</span>
                        <span>${project.total_episodes || 0} 集</span>
                    </div>
                    <div class="meta-item">
                        <span>👥</span>
                        <span>${project.character_count || 0} 角色</span>
                    </div>
                    <div class="meta-item">
                        <span>🎨</span>
                        <span>${project.portrait_count || 0} 剧照</span>
                    </div>
                </div>

                ${project.progress !== undefined ? `
                    <div class="project-progress">
                        <div class="progress-header">
                            <span>完成度</span>
                            <span>${Math.round(project.progress)}%</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${project.progress}%"></div>
                        </div>
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
}

/**
 * 显示创建项目模态框
 */
function showCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    modal.classList.add('active');

    // 自动选择第一个小说
    const select = document.getElementById('novelSelect');
    if (select.options.length > 1) {
        select.selectedIndex = 1;
        loadNovelDetails(select.value);
    }
}

/**
 * 关闭模态框
 */
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
}

/**
 * 处理创建项目
 */
async function handleCreateProject(event) {
    event.preventDefault();

    const novelSelect = document.getElementById('novelSelect');
    const projectName = document.getElementById('projectName').value;
    const projectDesc = document.getElementById('projectDesc').value;
    const videoType = document.querySelector('input[name="videoType"]:checked')?.value;

    if (!novelSelect.value) {
        showToast('请选择小说项目', 'error');
        return;
    }

    const createBtn = event.target.querySelector('button[type="submit"]');
    createBtn.disabled = true;
    createBtn.textContent = '创建中...';

    try {
        // TODO: 调用创建项目API
        // const result = await videoAPI.createProject({...});

        showToast('项目创建成功！', 'success');
        closeModal('createProjectModal');

        // 重置表单
        event.target.reset();

        // 重新加载项目列表
        await loadProjects();

    } catch (error) {
        console.error('创建项目失败:', error);
        showToast('创建失败，请重试', 'error');
    } finally {
        createBtn.disabled = false;
        createBtn.textContent = '创建项目';
    }
}

/**
 * 打开项目详情
 */
function openProject(projectId) {
    window.location.href = `/video/project/${projectId}`;
}

/**
 * 加载小说详情（用于预览集数规划）
 */
async function loadNovelDetails(novelTitle) {
    // TODO: 实现加载小说详情的逻辑
    console.log('加载小说详情:', novelTitle);
}

/**
 * 获取类型图标
 */
function getTypeIcon(type) {
    const icons = {
        'short_film': '🎬 短片',
        'long_series': '📺 剧集',
        'short_video': '📱 短视频'
    };
    return icons[type] || '🎬';
}

/**
 * 获取状态样式类
 */
function getStatusClass(status) {
    const map = {
        'draft': 'draft',
        'in_progress': 'in-progress',
        'completed': 'completed'
    };
    return map[status] || 'draft';
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const map = {
        'draft': '草稿',
        'in_progress': '进行中',
        'completed': '已完成'
    };
    return map[status] || '草稿';
}

/**
 * HTML转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * 显示Toast通知
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}
