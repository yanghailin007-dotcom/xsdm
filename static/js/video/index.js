/**
 * 视频制作中心 - 首页逻辑
 */

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', async () => {
    await loadRecentProjects();
    await loadStats();
});

/**
 * 加载最近项目
 */
async function loadRecentProjects() {
    const container = document.getElementById('recentProjects');

    try {
        const projects = await videoAPI.getProjects();

        if (!projects.projects || projects.projects.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📁</div>
                    <p>还没有项目，去创建第一个吧！</p>
                </div>
            `;
            return;
        }

        container.innerHTML = projects.projects.slice(0, 4).map(project => `
            <a href="/video/project/${project.id}" class="project-card">
                <div class="project-card-header">
                    <h3 class="project-title">${escapeHtml(project.title || project.novel_title)}</h3>
                    <span class="project-status ${getStatusClass(project.status)}">
                        ${getStatusText(project.status)}
                    </span>
                </div>
                <div class="project-meta">
                    <div class="project-meta-item">
                        <span>📊</span>
                        <span>${project.total_episodes || 0} 集</span>
                    </div>
                    <div class="project-meta-item">
                        <span>👥</span>
                        <span>${project.character_count || 0} 角色</span>
                    </div>
                    <div class="project-meta-item">
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
            </a>
        `).join('');

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
 * 加载统计数据
 */
async function loadStats() {
    try {
        const stats = await videoAPI.getStats();

        document.getElementById('statNovels').textContent = stats.novel_count || 0;
        document.getElementById('statPortraits').textContent = stats.portrait_count || 0;
        document.getElementById('statVideos').textContent = stats.video_count || 0;
        document.getElementById('statTasks').textContent = stats.task_count || 0;

    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

/**
 * 获取状态样式类
 */
function getStatusClass(status) {
    const statusMap = {
        'draft': 'draft',
        'in_progress': 'in-progress',
        'completed': 'completed',
        'paused': 'draft'
    };
    return statusMap[status] || 'draft';
}

/**
 * 获取状态文本
 */
function getStatusText(status) {
    const statusMap = {
        'draft': '草稿',
        'in_progress': '进行中',
        'completed': '已完成',
        'paused': '已暂停'
    };
    return statusMap[status] || '草稿';
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
    toast.innerHTML = `
        <span>${message}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}
