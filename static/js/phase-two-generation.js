// 第二阶段章节生成页面JavaScript

let currentProject = null;
let currentTaskId = null;
let progressInterval = null;
let generationStartTime = null;

// ==================== 🚀 章节队列管理器 ====================
class ChapterQueueManager {
    constructor(containerId = 'chapterQueueTrack') {
        this.container = document.getElementById(containerId);
        this.chapters = new Map();
        this.currentChapter = null;
    }

    initQueue(totalChapters, startFrom = 1) {
        this.chapters.clear();
        for (let i = 0; i < totalChapters; i++) {
            const chapterNum = startFrom + i;
            this.chapters.set(chapterNum, {
                number: chapterNum,
                status: 'pending',
                progress: 0,
                title: `第${chapterNum}章`
            });
        }
        this.render();
        this.updateStats();
        // 显示队列容器
        const container = document.getElementById('chapterQueueContainer');
        if (container) container.style.display = 'block';
        
        // 添加初始动画效果 - 展示流水线活力
        this.playEntryAnimation();
    }
    
    // 入场动画 - 让用户感受到流水线的活力
    playEntryAnimation() {
        const items = this.container.querySelectorAll('.chapter-queue__item');
        const connectors = this.container.querySelectorAll('.chapter-queue__connector');
        
        // 逐个显示章节卡片
        items.forEach((item, index) => {
            item.style.opacity = '0';
            item.style.transform = 'translateY(20px) scale(0.9)';
            setTimeout(() => {
                item.style.transition = 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
                item.style.opacity = '1';
                item.style.transform = 'translateY(0) scale(1)';
            }, index * 80);
        });
        
        // 逐个显示连接器并添加流动效果
        connectors.forEach((connector, index) => {
            connector.style.opacity = '0';
            setTimeout(() => {
                connector.style.transition = 'opacity 0.3s ease';
                connector.style.opacity = '1';
                // 添加临时流动效果展示
                connector.classList.add('chapter-queue__connector--flowing');
                setTimeout(() => {
                    connector.classList.remove('chapter-queue__connector--flowing');
                }, 1500);
            }, (index + 1) * 80 + 50);
        });
        
        // 全部显示完成后，滚动到第一个
        setTimeout(() => {
            const firstItem = items[0];
            if (firstItem) {
                firstItem.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
            }
        }, items.length * 80 + 300);
    }

    updateChapterStatus(chapterNumber, status, progress = 0) {
        const chapter = this.chapters.get(chapterNumber);
        if (!chapter) return;
        chapter.status = status;
        chapter.progress = progress;
        this.updateChapterElement(chapterNumber);
        this.updateStats();
        if (status === 'generating') {
            this.currentChapter = chapterNumber;
            this.scrollToChapter(chapterNumber);
        }
    }

    render() {
        if (!this.container) return;
        const chapters = Array.from(this.chapters.values());
        if (chapters.length === 0) return;
        let html = '';
        chapters.forEach((chapter, index) => {
            if (index > 0) {
                const prevChapter = chapters[index - 1];
                const connectorClass = (prevChapter.status === 'generating' || prevChapter.status === 'completed') ? 'chapter-queue__connector--flowing' : '';
                const fromColor = this.getStatusColor(prevChapter.status);
                const toColor = this.getStatusColor(chapter.status);
                html += `<div class="chapter-queue__connector ${connectorClass}" style="--from-color: ${fromColor}; --to-color: ${toColor}"></div>`;
            }
            html += this.createChapterElement(chapter);
        });
        this.container.innerHTML = html;
    }

    createChapterElement(chapter) {
        const statusClass = `chapter-queue__item--${chapter.status}`;
        const isCurrent = chapter.number === this.currentChapter ? 'chapter-queue__item--current' : '';
        let iconHtml = '';
        switch (chapter.status) {
            case 'pending': iconHtml = '<span class="chapter-queue__icon">⏳</span>'; break;
            case 'generating': iconHtml = '<div class="chapter-queue__spinner"></div>'; break;
            case 'completed': iconHtml = '<div class="chapter-queue__check">✓</div>'; break;
            case 'error': iconHtml = '<span class="chapter-queue__icon">⚠</span>'; break;
        }
        const progressHtml = chapter.status === 'generating' ? 
            `<div class="chapter-queue__progress"><div class="chapter-queue__progress-bar" style="width: ${chapter.progress}%"></div></div>` : '';
        return `<div class="chapter-queue__item ${statusClass} ${isCurrent}" data-chapter="${chapter.number}"><span class="chapter-queue__number">${chapter.number}</span>${iconHtml}${progressHtml}</div>`;
    }

    updateChapterElement(chapterNumber) {
        const oldElement = this.container.querySelector(`[data-chapter="${chapterNumber}"]`);
        if (!oldElement) return;
        const chapter = this.chapters.get(chapterNumber);
        
        // 检查是否是刚完成的状态变化
        const wasCompleted = oldElement.classList.contains('chapter-queue__item--completed');
        const isNowCompleted = chapter.status === 'completed';
        const justCompleted = !wasCompleted && isNowCompleted;
        
        const newElementHtml = this.createChapterElement(chapter);
        const parser = new DOMParser();
        const doc = parser.parseFromString(newElementHtml, 'text/html');
        const newElement = doc.body.firstElementChild;
        
        // 如果刚完成，添加完成动画类
        if (justCompleted) {
            newElement.classList.add('chapter-queue__item--just-completed');
            // 动画结束后移除该类
            setTimeout(() => {
                const el = this.container.querySelector(`[data-chapter="${chapterNumber}"]`);
                if (el) el.classList.remove('chapter-queue__item--just-completed');
            }, 800);
        }
        
        oldElement.replaceWith(newElement);
        this.updateConnectors();
        
        // 如果是生成中状态，自动滚动到视图中心
        if (chapter.status === 'generating') {
            this.scrollToChapter(chapterNumber);
        }
    }

    updateConnectors() {
        const connectors = this.container.querySelectorAll('.chapter-queue__connector');
        const chapters = Array.from(this.chapters.values());
        connectors.forEach((connector, index) => {
            const prevChapter = chapters[index];
            const nextChapter = chapters[index + 1];
            if (prevChapter && nextChapter) {
                connector.style.setProperty('--from-color', this.getStatusColor(prevChapter.status));
                connector.style.setProperty('--to-color', this.getStatusColor(nextChapter.status));
                const shouldFlow = prevChapter.status === 'generating' || prevChapter.status === 'completed';
                connector.classList.toggle('chapter-queue__connector--flowing', shouldFlow);
            }
        });
    }

    getStatusColor(status) {
        const colors = { pending: '#6b7280', generating: '#3b82f6', completed: '#10b981', error: '#ef4444' };
        return colors[status] || '#6b7280';
    }

    updateStats() {
        const chapters = Array.from(this.chapters.values());
        const pending = chapters.filter(c => c.status === 'pending').length;
        const generating = chapters.filter(c => c.status === 'generating').length;
        const completed = chapters.filter(c => c.status === 'completed').length;
        
        // 🔍 调试日志：检查生成中章节
        if (generating > 0) {
            console.log('[ChapterQueue] Generating chapters:', chapters.filter(c => c.status === 'generating').map(c => c.number));
        }
        
        const pendingEl = document.getElementById('queue-pending-count');
        const generatingEl = document.getElementById('queue-generating-count');
        const completedEl = document.getElementById('queue-completed-count');
        if (pendingEl) pendingEl.textContent = `${pending} 等待`;
        if (generatingEl) generatingEl.textContent = `${generating} 生成中`;
        if (completedEl) completedEl.textContent = `${completed} 完成`;
    }

    scrollToChapter(chapterNumber) {
        const element = this.container.querySelector(`[data-chapter="${chapterNumber}"]`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    }

    getProgressPercentage() {
        const chapters = Array.from(this.chapters.values());
        if (chapters.length === 0) return 0;
        const completed = chapters.filter(c => c.status === 'completed').length;
        return Math.round((completed / chapters.length) * 100);
    }

    clear() {
        this.chapters.clear();
        this.currentChapter = null;
        if (this.container) this.container.innerHTML = '';
        const container = document.getElementById('chapterQueueContainer');
        if (container) container.style.display = 'none';
    }
}

// 创建全局实例
const chapterQueue = new ChapterQueueManager();

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    loadAvailableProjects();
    
    // 加载点数配置和用户余额
    loadPointsConfig();
    loadUserBalance();
    
    // 检查URL参数中是否有项目标题，如果有则自动选择
    checkUrlParameterForProject();
    
    // 添加表单事件监听器，用于更新创造点估算
    const fromChapterInput = document.getElementById('from-chapter');
    const chaptersToGenerateInput = document.getElementById('chapters-to-generate');
    
    if (fromChapterInput) {
        fromChapterInput.addEventListener('input', updateChapterRange);
    }
    if (chaptersToGenerateInput) {
        chaptersToGenerateInput.addEventListener('input', updateChapterRange);
    }
    
    // 测试goToContentReview函数是否可用
    console.log('🧪 [TEST] goToContentReview函数是否存在:', typeof goToContentReview);
    console.log('🧪 [TEST] window.goToContentReview是否存在:', typeof window.goToContentReview);
    
    // 添加全局测试：3秒后自动测试函数
    setTimeout(() => {
        console.log('🧪 [AUTO-TEST] 3秒后自动测试goToContentReview函数...');
        if (currentProject) {
            console.log('🧪 [AUTO-TEST] currentProject存在，标题:', currentProject.novel_title || currentProject.title);
        } else {
            console.log('🧪 [AUTO-TEST] currentProject为空');
        }
    }, 3000);
});

// ==================== 认证功能 ====================
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            showStatusMessage('⚠️ 请先登录后再使用生成功能', 'error');
        }
    } catch (error) {
        showStatusMessage('⚠️ 请先登录后再使用生成功能', 'error');
    }
}

// ==================== URL参数处理功能 ====================
function checkUrlParameterForProject() {
    const urlParams = new URLSearchParams(window.location.search);
    const projectTitleFromUrl = urlParams.get('title');
    
    if (projectTitleFromUrl) {
        console.log('📋 [DEBUG] 从URL获取到项目标题:', decodeURIComponent(projectTitleFromUrl));
        addLogEntry('info', `检测到URL中的项目参数，等待项目列表加载后自动选中`);
        
        // 保存到localStorage以便后续使用
        localStorage.setItem('selectedProjectTitle', decodeURIComponent(projectTitleFromUrl));
    }
}

// ==================== 项目管理功能 ====================
let projectsCache = []; // 缓存项目列表

async function loadAvailableProjects() {
    try {
        const response = await fetch('/api/projects/with-phase-status');
        
        if (response.status === 401) {
            showStatusMessage('请先登录才能加载项目', 'error');
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        projectsCache = result.projects || [];
        displayProjectsList(projectsCache);
        addLogEntry('info', `成功加载 ${projectsCache.length} 个项目`);
        
        // 检查是否需要自动选择项目
        checkAndAutoSelectProject();
    } catch (error) {
        console.error('加载项目列表失败:', error);
        showStatusMessage(`❌ 加载项目失败: ${error.message}`, 'error');
        addLogEntry('error', `加载项目失败: ${error.message}`);
    }
}

function displayProjectsList(projects) {
    const projectsList = document.getElementById('projects-list');
    
    if (projects.length === 0) {
        projectsList.innerHTML = `
            <div style="text-align: center; color: #6b7280; padding: 20px;">
                <p>暂无可用的项目</p>
                <button class="btn btn-primary" style="margin-top: 12px;" onclick="location.href='/phase-one-setup'">
                    🎨 创建第一个项目
                </button>
            </div>
        `;
        return;
    }

    // 🔥 排序：1. 章节生成中的项目置顶 2. 按最后更新时间倒序（最近在上）
    const sortedProjects = [...projects].sort((a, b) => {
        const aIsGenerating = a.phase_two?.status === 'generating';
        const bIsGenerating = b.phase_two?.status === 'generating';
        
        // 生成中的项目置顶
        if (aIsGenerating && !bIsGenerating) return -1;
        if (!aIsGenerating && bIsGenerating) return 1;
        
        // 同状态内按最后更新时间倒序
        const aTime = a.last_updated || a.created_at || '';
        const bTime = b.last_updated || b.created_at || '';
        return new Date(bTime) - new Date(aTime);
    });

    let html = '<div style="display: flex; flex-direction: column; gap: 12px;">';
    
    sortedProjects.forEach((project, index) => {
        // 对标题进行HTML转义，避免特殊字符导致的问题
        const escapedTitle = project.title.replace(/'/g, "\\'").replace(/"/g, '\\"');
        const statusText = getProjectStatusText(project);
        const statusClass = getProjectStatusClass(project);
        
        // 🔥 检测是否是章节生成中的项目
        const isGenerating = project.phase_two?.status === 'generating';
        const progressPercent = Math.round(((project.completed_chapters || 0) / (project.total_chapters || 1)) * 100);
        
        // 状态徽章类名
        let statusBadgeClass = 'status-badge--pending';
        if (isGenerating) statusBadgeClass = 'status-badge--generating';
        else if (project.phase_two?.status === 'completed') statusBadgeClass = 'status-badge--completed';
        
        // 🔥 新的统一卡片设计
        html += `
            <div class="project-select-card"
                 data-title="${escapedTitle}"
                 data-status="${statusClass.replace('status-', '')}"
                 data-generating="${isGenerating}"
                 onclick="selectProject('${escapedTitle}', this)">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                    <h4 class="project-title">${project.title}</h4>
                    <div style="display: flex; gap: 8px; align-items: center; flex-shrink: 0;">
                        ${isGenerating ? '<span class="generating-indicator">生成中</span>' : `<span class="status-badge ${statusBadgeClass}">${statusText}</span>`}
                    </div>
                </div>
                <div class="project-stats">
                    <div class="project-stat">
                        <span>📚</span>
                        <span>总章节: <span class="project-stat-value">${project.total_chapters || 0}</span></span>
                    </div>
                    <div class="project-stat">
                        <span>✅</span>
                        <span>已完成: <span class="project-stat-value">${project.completed_chapters || 0}</span></span>
                    </div>
                    <div class="project-stat">
                        <span>📊</span>
                        <span>进度: <span class="project-stat-value">${progressPercent}%</span></span>
                    </div>
                </div>
                <div class="project-progress-track">
                    <div class="project-progress-fill ${isGenerating ? 'project-progress-fill--generating' : 'project-progress-fill--normal'}" 
                         style="width: ${progressPercent}%"></div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    projectsList.innerHTML = html;
}

// 🔥 新增：根据项目状态返回对应的样式类
function getProjectStatusClass(project) {
    if (project.phase_one && project.phase_one.status === 'completed') {
        if (project.phase_two && project.phase_two.status === 'completed') {
            return 'status-completed';
        } else if (project.phase_two && project.phase_two.status === 'generating') {
            return 'status-generating';
        } else {
            return 'status-ready';
        }
    } else if (project.phase_one && project.phase_one.status === 'generating') {
        return 'status-designing';
    } else {
        return 'status-pending';
    }
}

// 自动选择项目的函数
async function checkAndAutoSelectProject() {
    const urlParams = new URLSearchParams(window.location.search);
    const projectTitleFromUrl = urlParams.get('title');
    
    // 也检查localStorage
    const storedProjectTitle = localStorage.getItem('selectedProjectTitle');
    const targetProjectTitle = projectTitleFromUrl || storedProjectTitle;
    
    if (!targetProjectTitle) {
        console.log('📋 [DEBUG] 没有检测到需要自动选择的项目');
        return;
    }
    
    const decodedTitle = decodeURIComponent(targetProjectTitle);
    console.log('📋 [DEBUG] 尝试自动选择项目:', decodedTitle);
    
    // 在项目缓存中查找匹配的项目
    const targetProject = projectsCache.find(p => p.title === decodedTitle);
    
    if (!targetProject) {
        console.warn('⚠️ [DEBUG] 在项目列表中未找到匹配的项目:', decodedTitle);
        showStatusMessage(`⚠️ 未找到项目 "${decodedTitle}"，请手动选择`, 'warning');
        // 清除localStorage
        localStorage.removeItem('selectedProjectTitle');
        return;
    }
    
    console.log('✅ [DEBUG] 找到匹配的项目，准备自动选择');
    
    // 延迟一下，确保DOM已完全渲染
    setTimeout(async () => {
        try {
            // 模拟点击选择项目
            await autoSelectProject(decodedTitle);
        } catch (error) {
            console.error('❌ [DEBUG] 自动选择项目失败:', error);
            showStatusMessage(`⚠️ 自动选择项目失败，请手动选择`, 'warning');
        }
    }, 500);
}

// 自动选择项目的内部函数
async function autoSelectProject(projectTitle) {
    console.log('🔄 [DEBUG] 开始自动选择项目:', projectTitle);
    
    // 查找项目卡片并触发选择
    const projectCards = document.querySelectorAll('.project-select-card');
    let foundCard = null;
    
    for (const card of projectCards) {
        const titleElement = card.querySelector('.project-title');
        if (titleElement && titleElement.textContent === projectTitle) {
            foundCard = card;
            break;
        }
    }
    
    if (!foundCard) {
        console.error('❌ [DEBUG] 未找到项目卡片元素');
        return;
    }
    
    // 触发点击事件
    foundCard.click();
    
    console.log('✅ [DEBUG] 项目卡片点击已触发');
    addLogEntry('info', `已自动选择项目: ${projectTitle}`);
    
    // 清除URL参数（避免重复触发）
    const url = new URL(window.location);
    url.searchParams.delete('title');
    window.history.replaceState({}, document.title, url);
    
    // 清除localStorage
    localStorage.removeItem('selectedProjectTitle');
    
    showStatusMessage(`✅ 已自动选择项目: ${projectTitle}`, 'success');
}

function getProjectStatusText(project) {
    if (project.phase_one && project.phase_one.status === 'completed') {
        if (project.phase_two && project.phase_two.status === 'completed') {
            return '已完成';
        } else if (project.phase_two && project.phase_two.status === 'generating') {
            return '生成中';
        } else {
            return '待生成';
        }
    } else if (project.phase_one && project.phase_one.status === 'generating') {
        return '设计中';
    } else {
        return '未开始';
    }
}

async function selectProject(projectTitle, clickedElement = null) {
    try {
        // 取消之前选中的项目
        document.querySelectorAll('.project-select-card').forEach(card => {
            card.classList.remove('selected');
        });

        // 选中当前项目 - 使用传入的元素或根据标题查找
        const clickedCard = clickedElement || document.querySelector(`.project-select-card[data-title="${projectTitle}"]`);
        
        if (clickedCard) {
            clickedCard.classList.add('selected');
        }

        // 加载项目详情
        const response = await fetch(`/api/project/${encodeURIComponent(projectTitle)}/with-phase-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const projectData = await response.json();
        currentProject = projectData;
        
        displayProjectInfo(projectData);
        displayProjectDetails(projectData);
        showCreativeEnhancement();
        showGenerationForm();
        
        addLogEntry('info', `选择项目: ${projectTitle}`);
        showStatusMessage(`✅ 已选择项目: ${projectTitle}`, 'success');
    } catch (error) {
        console.error('选择项目失败:', error);
        showStatusMessage(`❌ 选择项目失败: ${error.message}`, 'error');
        addLogEntry('error', `选择项目失败: ${error.message}`);
    }
}

function displayProjectInfo(projectData) {
    console.log('[DEBUG] displayProjectInfo 开始执行:', projectData.novel_title || projectData.title);
    
    // 🔥 延迟检查元素是否存在
    setTimeout(() => {
        const delayedCheck = document.getElementById('selected-project-info');
        console.log('[DEBUG] 100ms后检查 selected-project-info:', delayedCheck);
    }, 100);
    
    const infoDiv = document.getElementById('selected-project-info');
    console.log('[DEBUG] selected-project-info 元素:', infoDiv);
    
    // 🔥 检查整个文档中是否有这个 ID
    const allElements = document.querySelectorAll('[id]');
    const hasSelectedInfo = Array.from(allElements).some(el => el.id === 'selected-project-info');
    console.log('[DEBUG] 文档中是否存在 selected-project-info ID:', hasSelectedInfo);
    console.log('[DEBUG] 所有ID列表:', Array.from(allElements).map(el => el.id).slice(0, 20));
    
    // 🔥 修复：优先从phase_info获取总章节数，然后尝试其他可能的位置
    const totalChapters = (
        projectData.phase_info?.total_chapters ||
        projectData.total_chapters ||
        projectData.current_progress?.total_chapters ||
        projectData.progress?.total_chapters ||
        projectData.novel_info?.total_chapters ||
        200  // 默认值
    );
    
    // 🔥 修复：处理 generated_chapters 可能是对象、数组或undefined的情况
    let generatedChapters = projectData.generated_chapters || {};
    let completedChapters = 0;
    
    if (Array.isArray(generatedChapters)) {
        completedChapters = generatedChapters.length;
    } else if (typeof generatedChapters === 'object') {
        completedChapters = Object.keys(generatedChapters).length;
    }
    
    // 优先使用后端计算的 completed_chapters（如果有）
    // 先检查顶层 completed_chapters，如果不存在或无效，再检查 phase_info
    if (projectData.completed_chapters !== undefined && projectData.completed_chapters > 0) {
        completedChapters = projectData.completed_chapters;
    } else if (projectData.phase_info && projectData.phase_info.completed_chapters !== undefined && projectData.phase_info.completed_chapters > 0) {
        completedChapters = projectData.phase_info.completed_chapters;
    }
    
    console.log(`[DEBUG] 总章节: ${totalChapters}, 已完成: ${completedChapters}`, generatedChapters);
    
    // 🔥 修复：添加空值检查，兼容不同版本的HTML结构
    if (infoDiv) {
        infoDiv.style.display = 'block';
        console.log('[DEBUG] selected-project-info 已显示');
    } else {
        console.warn('[DEBUG] selected-project-info 元素不存在');
    }
    
    const titleEl = document.getElementById('current-project-title');
    if (titleEl) {
        titleEl.textContent = projectData.novel_title || projectData.title || '未命名';
        console.log('[DEBUG] current-project-title 已更新:', titleEl.textContent);
    } else {
        console.warn('[DEBUG] current-project-title 元素不存在');
    }
    
    const totalChaptersEl = document.getElementById('current-project-total-chapters');
    if (totalChaptersEl) {
        totalChaptersEl.textContent = totalChapters;
        console.log('[DEBUG] current-project-total-chapters 已更新');
    } else {
        console.warn('[DEBUG] current-project-total-chapters 元素不存在');
    }
    
    const completedChaptersEl = document.getElementById('current-project-completed-chapters');
    if (completedChaptersEl) {
        completedChaptersEl.textContent = completedChapters;
        console.log('[DEBUG] current-project-completed-chapters 已更新');
    } else {
        console.warn('[DEBUG] current-project-completed-chapters 元素不存在');
    }
    
    const statusEl = document.getElementById('current-project-status');
    if (statusEl) {
        statusEl.textContent = '准备就绪';
        console.log('[DEBUG] current-project-status 已更新');
    } else {
        console.warn('[DEBUG] current-project-status 元素不存在');
    }
    
    // 更新表单默认值
    const fromChapter = document.getElementById('from-chapter');
    const chaptersToGenerate = document.getElementById('chapters-to-generate');

    if (fromChapter) {
        fromChapter.value = completedChapters + 1;
        // 移除最小值限制，允许从任何章节开始
        // fromChapter.min = completedChapters + 1;
        // 添加事件监听器
        fromChapter.removeEventListener('input', updateChapterRange);
        fromChapter.addEventListener('input', updateChapterRange);
    }
    
    if (chaptersToGenerate) {
        const remainingChapters = totalChapters - completedChapters;
        chaptersToGenerate.max = Math.min(remainingChapters, 200);
        chaptersToGenerate.value = Math.min(10, remainingChapters);
        // 添加事件监听器
        chaptersToGenerate.removeEventListener('input', updateChapterRange);
        chaptersToGenerate.addEventListener('input', updateChapterRange);
    }
    
    // 初始化章节范围显示
    updateChapterRange();
}

// 更新章节范围显示和创造点消耗估算
function updateChapterRange() {
    const fromChapter = parseInt(document.getElementById('from-chapter').value) || 1;
    const chaptersToGenerate = parseInt(document.getElementById('chapters-to-generate').value) || 0;
    const toChapter = fromChapter + chaptersToGenerate - 1;
    
    const rangeStart = document.getElementById('range-start');
    const rangeEnd = document.getElementById('range-end');
    
    if (rangeStart) {
        rangeStart.textContent = fromChapter;
    }
    if (rangeEnd) {
        if (chaptersToGenerate > 0) {
            rangeEnd.textContent = toChapter;
        } else {
            rangeEnd.textContent = fromChapter;
        }
    }
    
    // 更新创造点消耗估算
    updatePointsCostEstimate(chaptersToGenerate);
}

// 创造点配置缓存
let pointsConfig = null;
let userBalance = 0;

// 获取点数配置
async function loadPointsConfig() {
    try {
        const response = await fetch('/api/points/config');
        if (response.ok) {
            const data = await response.json();
            pointsConfig = data.config || {};
        }
    } catch (error) {
        console.error('加载点数配置失败:', error);
        // 使用默认配置：生成1点 + 质检1点 = 2点/章
        pointsConfig = {
            phase2_chapter_batch: 2,
            phase2_chapter_refined: 3
        };
    }
}

// 获取用户当前余额
async function loadUserBalance() {
    try {
        console.log('开始加载余额...');
        const response = await fetch('/api/points/balance');
        console.log('余额API响应:', response.status);
        if (response.ok) {
            const result = await response.json();
            console.log('余额API返回:', result);
            // API 返回结构: { success: true, data: { balance: xx, ... } }
            if (result.success && result.data) {
                userBalance = result.data.balance || 0;
                console.log('解析余额成功:', userBalance);
            } else {
                console.error('余额API返回异常:', result);
                userBalance = 0;
            }
            updateBalanceDisplay();
        } else {
            console.error('余额API请求失败:', response.status);
        }
    } catch (error) {
        console.error('加载用户余额失败:', error);
    }
}

// 更新余额显示
function updateBalanceDisplay() {
    console.log('更新余额显示:', userBalance);
    
    // 更新消耗估算区域的余额
    const balanceElement = document.getElementById('points-current-balance');
    if (balanceElement) {
        // 检查是否足够
        const chaptersToGenerate = parseInt(document.getElementById('chapters-to-generate').value) || 0;
        // 默认：生成1点 + 质检1点 = 2点/章
        const costPerChapter = pointsConfig?.phase2_chapter_batch || 2;
        const totalCost = chaptersToGenerate * costPerChapter;
        
        if (userBalance < totalCost && totalCost > 0) {
            balanceElement.classList.add('insufficient');
            balanceElement.textContent = userBalance + ' 点 (不足)';
        } else {
            balanceElement.classList.remove('insufficient');
            balanceElement.textContent = userBalance + ' 点';
        }
    }
    
    // 更新侧边栏的余额显示
    const sidebarBalanceElement = document.getElementById('sidebar-balance-amount');
    if (sidebarBalanceElement) {
        sidebarBalanceElement.textContent = userBalance + ' 点';
    }
}

// 更新创造点消耗估算
function updatePointsCostEstimate(chapterCount) {
    // 默认配置：生成1点 + 质检1点 = 2点/章
    const costPerChapter = pointsConfig?.phase2_chapter_batch || 2;
    const totalCost = chapterCount * costPerChapter;
    
    // 更新显示
    const chapterCountElement = document.getElementById('points-chapter-count');
    const totalCostElement = document.getElementById('points-total-cost');
    
    if (chapterCountElement) {
        chapterCountElement.textContent = chapterCount + ' 章';
    }
    if (totalCostElement) {
        totalCostElement.textContent = totalCost + ' 点';
    }
    
    // 检查余额是否足够
    updateBalanceDisplay();
}

function displayProjectDetails(projectData) {
    const detailsDiv = document.getElementById('project-details');
    
    // 添加空值检查
    if (!detailsDiv) {
        console.warn('[DEBUG] project-details 元素不存在，跳过显示项目详情');
        return;
    }
    
    // 关键修复：从多个可能的位置获取数据
    const novelTitle = projectData.novel_title || projectData.title || '未命名';
    const synopsis = projectData.story_synopsis || projectData.synopsis || projectData.novel_synopsis || '暂无简介';
    const setting = projectData.core_setting || projectData.core_worldview || projectData.worldview_setting || '暂无设定';
    
    let html = `
        <div class="result-item" style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px; padding: 16px; margin-bottom: 16px;">
            <h4 style="margin: 0 0 12px 0; color: #a78bfa; font-size: 14px; font-weight: 600;">📋 项目信息</h4>
            <p style="margin: 8px 0; color: #fff; font-size: 13px;"><strong style="color: rgba(255,255,255,0.6);">标题:</strong> ${novelTitle}</p>
            <p style="margin: 8px 0; color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.6;"><strong style="color: rgba(255,255,255,0.6);">简介:</strong> ${synopsis}</p>
            <p style="margin: 8px 0; color: rgba(255,255,255,0.8); font-size: 13px; line-height: 1.6;"><strong style="color: rgba(255,255,255,0.6);">核心设定:</strong> ${setting}</p>
        </div>
    `;
    
    // 关键修复：更准确地判断第一阶段完成状态
    const phaseOneStatus = projectData.phase_one?.status || 
                          (projectData.phase_info?.phase_one?.status);
    
    if (phaseOneStatus === 'completed' || phaseOneStatus === '已完成') {
        const completedAt = projectData.phase_one?.completed_at || 
                           projectData.phase_info?.phase_one?.completed_at ||
                           projectData.created_at;
        html += `
            <div class="result-item" style="background: rgba(34, 197, 94, 0.05); border: 1px solid rgba(34, 197, 94, 0.2); border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 12px 0; color: #22c55e; font-size: 14px; font-weight: 600;">✅ 第一阶段状态</h4>
                <p style="margin: 8px 0; font-size: 13px;"><strong style="color: rgba(255,255,255,0.6);">状态:</strong> <span style="color: #22c55e; font-weight: 500;">已完成</span></p>
                <p style="margin: 8px 0; color: rgba(255,255,255,0.7); font-size: 13px;"><strong style="color: rgba(255,255,255,0.6);">完成时间:</strong> ${completedAt ? new Date(completedAt).toLocaleString('zh-CN') : '未知'}</p>
            </div>
        `;
    } else {
        html += `
            <div class="result-item" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 16px;">
                <h4 style="margin: 0 0 12px 0; color: rgba(255,255,255,0.5); font-size: 14px; font-weight: 600;">⏳ 第一阶段状态</h4>
                <p style="margin: 8px 0; font-size: 13px;"><strong style="color: rgba(255,255,255,0.6);">状态:</strong> <span style="color: rgba(255,255,255,0.5);">未完成</span></p>
            </div>
        `;
    }
    
    if (projectData.generated_chapters && Object.keys(projectData.generated_chapters).length > 0) {
        const generatedCount = Object.keys(projectData.generated_chapters).length;
        html += `
            <div class="result-item">
                <h4>📚 已生成章节</h4>
                <p><strong>章节数:</strong> ${generatedCount}</p>
                <p><strong>总字数:</strong> ${calculateTotalWords(projectData.generated_chapters)}</p>
            </div>
        `;
    }
    
    detailsDiv.innerHTML = html;
}

function calculateTotalWords(chapters) {
    let totalWords = 0;
    for (const chapterData of Object.values(chapters)) {
        if (chapterData.word_count) {
            totalWords += chapterData.word_count;
        } else if (chapterData.content) {
            totalWords += chapterData.content.length;
        }
    }
    return totalWords.toLocaleString();
}

function showCreativeEnhancement() {
    console.log('[DEBUG] showCreativeEnhancement 被调用');
    // 🔥 修复：兼容不同版本的HTML结构
    const productsSection = document.getElementById('phase-one-products-section') || document.getElementById('products-section');
    console.log('[DEBUG] productsSection 元素:', productsSection);
    if (productsSection) {
        productsSection.style.display = 'block';
        console.log('[DEBUG] productsSection 已显示');
    } else {
        console.warn('[DEBUG] productsSection 元素不存在 (phase-one-products-section 或 products-section)');
    }
    // 加载第一阶段产物数据
    loadPhaseOneProducts();
}

function showGenerationForm() {
    console.log('[DEBUG] showGenerationForm 被调用');
    // 🔥 修复：兼容不同版本的HTML结构
    const form = document.getElementById('phase-two-form') || document.getElementById('generation-form');
    console.log('[DEBUG] form 元素:', form);
    if (form) {
        form.style.display = 'block';
        console.log('[DEBUG] form 已显示');
    } else {
        console.warn('[DEBUG] form 元素不存在 (phase-two-form 或 generation-form)');
    }
}

// ==================== 第一阶段产物管理功能 ====================
let phaseOneProductsData = {};

async function loadPhaseOneProducts() {
    if (!currentProject) {
        console.log('[DEBUG] loadPhaseOneProducts: 没有当前项目，跳过');
        return;
    }

    const projectTitle = currentProject.novel_title || currentProject.title;
    console.log(`[DEBUG] loadPhaseOneProducts: 开始加载项目 ${projectTitle}`);

    try {
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(projectTitle)}`);
        
        if (response.status === 404) {
            console.warn(`[DEBUG] 产物API返回404，项目可能尚未生成产物: ${projectTitle}`);
            // 不显示错误，直接使用模拟数据
            showMockProductsData();
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.success) {
            phaseOneProductsData = result.products;
            
            // 单独加载势力系统状态
            await checkFactionSystemStatus();
            
            updateProductsDisplay();
            console.log('[DEBUG] 第一阶段产物加载完成');
        } else {
            console.warn('[DEBUG] 产物加载返回失败，使用模拟数据:', result.error);
            showMockProductsData();
        }
    } catch (error) {
        console.error('[DEBUG] 加载第一阶段产物失败:', error);
        // 不显示错误提示，直接使用模拟数据
        showMockProductsData();
    }
}

// 检查势力系统状态
async function checkFactionSystemStatus() {
    try {
        const response = await fetch(`/api/factions/${encodeURIComponent(currentProject.novel_title || currentProject.title)}`);
        
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.faction_system) {
                // 势力系统存在，添加到产物数据中
                phaseOneProductsData.factions = {
                    title: '势力/阵营系统',
                    content: JSON.stringify(result.faction_system, null, 2),
                    complete: true
                };
                console.log('✅ 势力系统已加载');
            }
        }
    } catch (error) {
        console.log('势力系统未生成或加载失败:', error.message);
        // 势力系统不存在是正常情况，不显示错误
    }
}

function updateProductsDisplay() {
    const categories = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market', 'viewer'];
    
    categories.forEach(category => {
        const card = document.querySelector(`.pt-product-card--${category}`);
        const statusRow = document.getElementById(`${category}-status-text`)?.parentElement;
        
        const hasData = phaseOneProductsData[category] && phaseOneProductsData[category].content;
        
        // 设置卡片数据状态属性
        if (card) {
            card.setAttribute('data-has-data', hasData ? 'true' : 'false');
        }
        
        // 隐藏/显示状态行 - 只在未完成时显示提示
        if (statusRow) {
            statusRow.style.display = hasData ? 'none' : 'flex';
        }
    });
}

function showMockProductsData() {
    phaseOneProductsData = {
        worldview: {
            title: '世界观设定',
            content: '这是一个修仙世界，分为凡人界、修仙界、仙界三重境界。主要修炼体系包括炼气、筑基、金丹、元婴等境界。世界中有各大宗门、家族势力，以及丰富的灵兽、法宝设定。',
            complete: true
        },
        factions: {
            title: '势力/阵营系统',
            content: JSON.stringify({
                "main_conflict": "正道与魔道百年来争夺修真界主导权的大战即将爆发",
                "faction_power_balance": "正道与魔道势均力敌，散修势力在中间摇摆",
                "recommended_starting_faction": "青云宗（正道大派，资源丰富，适合作为主角初始势力）",
                "factions": [
                    {
                        "name": "青云宗",
                        "type": "正道",
                        "background": "修真界百年大派，以剑道闻名",
                        "core_philosophy": "以剑证道，匡扶正义",
                        "goals": ["维护正道秩序", "培养优秀弟子", "对抗魔道"],
                        "power_level": "一流势力",
                        "strengths": ["剑法高超", "底蕴深厚", "弟子众多"],
                        "weaknesses": ["思想保守", "内部派系林立"],
                        "territory": "占据云州七郡",
                        "relationships": {
                            "allies": ["天剑宗", "佛门圣地"],
                            "enemies": ["血魔宗", "炼魂殿"],
                            "neutrals": ["散修联盟"]
                        },
                        "role_in_plot": "主角的初始势力，提供基础资源和保护",
                        "suitable_for_protagonist": "是"
                    },
                    {
                        "name": "血魔宗",
                        "type": "魔道",
                        "background": "三百年前崛起的魔道巨擘",
                        "core_philosophy": "弱肉强食，以杀证道",
                        "goals": ["统一魔道", "消灭正道", "搜集血魂"],
                        "power_level": "一流势力",
                        "strengths": ["功法霸道", "行事狠辣", "信徒狂热"],
                        "weaknesses": ["树敌过多", "内部缺乏凝聚力"],
                        "territory": "占据幽冥渊",
                        "relationships": {
                            "allies": ["炼魂殿", "万毒谷"],
                            "enemies": ["青云宗", "天剑宗", "佛门圣地"],
                            "neutrals": []
                        },
                        "role_in_plot": "主要敌对势力，推动主线冲突",
                        "suitable_for_protagonist": "否"
                    }
                ]
            }),
            complete: true
        },
        characters: {
            title: '角色设计',
            content: '主角：张三，天赋异禀的修仙奇才，性格坚毅不屈。女主角：李四，来自名门正派，实力高强。主要配角：王五（主角好友）、赵六（导师）等。每个角色都有独特的背景故事和性格特点。',
            complete: true
        },
        growth: {
            title: '成长路线',
            content: '从炼气期开始，逐步升级到筑基、金丹、元婴。每个阶段都有不同的挑战和机遇。主角将通过修炼、奇遇、战斗等方式提升实力。成长过程中注重实力与心境的双重提升。',
            complete: true
        },
        writing: {
            title: '写作计划',
            content: '全书共200章，分为四个阶段。第一阶段（1-50章）：基础设定和成长初期；第二阶段（51-100章）：实力提升和冒险；第三阶段（101-150章）：高潮冲突；第四阶段（151-200章）：结局和新开始。',
            complete: true
        },
        storyline: {
            title: '故事线',
            content: '开篇：主角获得奇遇，踏上修仙之路；发展：修炼成长，结识伙伴，面对挑战；高潮：终极对决，揭开身世之谜；结局：功成身退，开启新的征程。故事中包含多个重大事件和转折点。',
            complete: true
        },
        market: {
            title: '市场分析',
            content: '目标读者：15-35岁男性，喜爱玄幻修仙类小说。市场定位：爽文风格，节奏明快，升级体系清晰。竞品分析：参考凡人修仙传、斗破苍穹等成功作品。特色卖点：独特的修炼体系和丰富的世界观设定。',
            complete: true
        }
    };
    
    updateProductsDisplay();
}

function editProductCategory(category) {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    const productData = phaseOneProductsData[category];
    
    // 所有产物都使用抽屉面板编辑
    createProductEditDrawer(category, productData);
}

// 从第二阶段打开角色编辑器
async function openCharacterEditorFromPhaseTwo() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    console.log('🎯 准备打开角色编辑器，项目标题:', projectTitle);
    
    try {
        showStatusMessage('🔄 正在加载角色编辑器...', 'info');
        
        // 动态加载角色编辑器模态框（如果还没加载）
        let modalContainer = document.getElementById('character-editor-modal-wrapper');
        if (!modalContainer) {
            console.log('📦 创建模态框容器');
            modalContainer = document.createElement('div');
            modalContainer.id = 'character-editor-modal-wrapper';
            modalContainer.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 999999;';
            document.body.appendChild(modalContainer);
        }
        
        if (modalContainer.innerHTML.trim() === '') {
            console.log('📥 加载模态框HTML');
            const response = await fetch('/templates/components/character-editor-modal.html');
            if (!response.ok) {
                throw new Error(`加载模态框HTML失败: ${response.status}`);
            }
            const html = await response.text();
            modalContainer.innerHTML = html;
            console.log('✅ 模态框HTML加载完成，长度:', html.length);
        }
        
        // 动态加载角色编辑器JavaScript（如果还没加载）
        if (typeof openCharacterEditor === 'undefined') {
            console.log('📜 加载角色编辑器JavaScript');
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/static/js/character-editor.js';
                script.onload = () => {
                    console.log('✅ 角色编辑器JavaScript加载完成');
                    resolve();
                };
                script.onerror = () => {
                    console.error('❌ 角色编辑器JavaScript加载失败');
                    reject(new Error('JavaScript加载失败'));
                };
                document.head.appendChild(script);
            });
        } else {
            console.log('✅ 角色编辑器JavaScript已加载');
        }
        
        // 解析角色设计数据
        let characterDataList = [];
        const characterProduct = phaseOneProductsData.characters;
        
        console.log('📋 角色产品数据:', characterProduct);
        console.log('📋 角色产品类型:', typeof characterProduct);
        
        if (characterProduct && characterProduct.content) {
            try {
                // 尝试解析为JSON
                const parsed = JSON.parse(characterProduct.content);
                console.log('📝 解析后的数据:', parsed);
                
                if (Array.isArray(parsed)) {
                    // 直接是数组
                    characterDataList = parsed;
                    console.log('✅ 解析到角色数组:', characterDataList.length, '个角色');
                } else if (parsed && typeof parsed === 'object') {
                    // 如果是对象，检查是否包含 main_character 和 important_characters
                    if (parsed.main_character) {
                        characterDataList = [parsed.main_character];
                        if (Array.isArray(parsed.important_characters)) {
                            characterDataList = [parsed.main_character, ...parsed.important_characters];
                        }
                        console.log('✅ 从复杂对象解析到:', characterDataList.length, '个角色');
                    } else if (parsed.characters && Array.isArray(parsed.characters)) {
                        characterDataList = parsed.characters;
                        console.log('✅ 从characters字段解析到:', characterDataList.length, '个角色');
                    } else {
                        console.log('⚠️ 解析结果不是数组或可识别对象，尝试将对象包装为数组');
                        characterDataList = [parsed];
                    }
                } else {
                    console.log('⚠️ 解析结果不是数组或对象，创建默认角色');
                    throw new Error('不是有效的JSON格式');
                }
            } catch (e) {
                console.log('⚠️ 角色设计内容不是有效的JSON:', e.message);
                console.log('📝 原始内容前200字符:', characterProduct.content.substring(0, 200));
                 
                // 如果不是JSON，可能只是文本描述
                const contentText = characterProduct.content.trim();
                
                // 尝试从文本中提取角色信息
                characterDataList = [];
                
                // 如果是描述性文本，创建一个默认角色
                if (contentText.length > 0) {
                    characterDataList = [{
                        name: '角色',
                        characterName: '角色',
                        role: '主角',
                        character_type: '主角',
                        icon: '👤',
                        color: '#667eea',
                        description: contentText,
                        personality: contentText,
                        background: contentText,
                        cultivation_level: '未知'
                    }];
                }
                
                console.log('✅ 从文本内容创建了默认角色:', characterDataList.length, '个角色');
            }
        } else {
            console.log('⚠️ 没有角色产品数据，创建空数组');
            characterDataList = [];
        }
        
        console.log('📊 最终角色数据列表:', characterDataList);
        
        // 设置全局变量供角色编辑器使用
        window.currentProjectTitle = projectTitle;
        
        // 🔥 修复：直接设置原始角色数据，避免双重解析
        // 保存原始数据到特殊字段，供角色编辑器使用
        window.rawPhaseOneCharacters = {
            rawData: characterProduct?.content || '',
            parsedData: characterDataList,
            source: 'phase-two'
        };
        
        // 同时保留向后兼容的novelData结构
        window.novelData = {
            projectTitle: projectTitle,
            characters: {
                content: characterProduct?.content || '', // 🔥 使用原始内容，不要重新序列化
                complete: true
            }
        };
        
        console.log('💾 设置novelData完成');
        console.log('📦 原始角色数据已保存到window.rawPhaseOneCharacters');
        
        // 等待一小段时间确保DOM更新完成
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 打开角色编辑器
        if (typeof openCharacterEditor === 'function') {
            console.log('🎯 调用openCharacterEditor函数');
            await openCharacterEditor();
            console.log('✅ openCharacterEditor函数调用完成');
            
            // 检查模态框是否真的显示了
            const modal = document.getElementById('character-editor-modal');
            if (modal) {
                console.log('✅ 模态框元素存在，类名:', modal.className);
                console.log('✅ 模态框display样式:', window.getComputedStyle(modal).display);
            } else {
                console.error('❌ 模态框元素不存在');
            }
        } else {
            throw new Error('角色编辑器函数未加载');
        }
        
    } catch (error) {
        console.error('❌ 打开角色编辑器失败:', error);
        showStatusMessage(`❌ 打开角色编辑器失败: ${error.message}`, 'error');
    }
}

// 查看势力系统
async function viewFactionSystem() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    try {
        showStatusMessage('🔄 正在加载势力系统...', 'info');
        
        const response = await fetch(`/api/factions/${encodeURIComponent(projectTitle)}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            createFactionSystemModal(result.faction_system);
            showStatusMessage('✅ 势力系统加载完成', 'success');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        console.error('加载势力系统失败:', error);
        showStatusMessage(`❌ 加载势力系统失败: ${error.message}`, 'error');
    }
}

// 全局变量存储势力数据
let currentFactionsData = null;

function createFactionSystemModal(factionData) {
    currentFactionsData = factionData;
    const factions = factionData.factions || [];
    const mainConflict = factionData.main_conflict || '未设置主要冲突';
    const powerBalance = factionData.faction_power_balance || '未设置势力平衡';
    const recommendedFaction = factionData.recommended_starting_faction || '未推荐';
    
    // 创建势力卡片HTML
    let factionsHtml = '';
    factions.forEach((faction, index) => {
        const factionType = faction.type || '未分类';
        const powerLevel = faction.power_level || '未知';
        const isRecommended = faction.suitable_for_protagonist === '是';
        
        factionsHtml += `
            <div class="faction-card ${isRecommended ? 'recommended' : ''}"
                 style="animation-delay: ${index * 0.1}s"
                 data-faction-index="${index}">
                ${isRecommended ? '<div class="recommended-badge">⭐ 推荐主角加入</div>' : ''}
                <div class="faction-header">
                    <div class="faction-name">${faction.name}</div>
                    <div class="faction-type-badge">${factionType}</div>
                </div>
                <div class="faction-info faction-info-collapsed" id="faction-info-${index}">
                    <div class="info-row">
                        <span class="info-label">势力等级</span>
                        <span class="info-value power-level-${powerLevel}">${powerLevel}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">核心理念</span>
                        <span class="info-value philosophy-preview">${faction.core_philosophy || '未设置'}</span>
                    </div>
                    <div class="info-row expand-hint" onclick="toggleFactionDetails(${index}, event)">
                        <span class="info-value">点击查看详细信息 ↓</span>
                    </div>
                    <div class="faction-details-expanded" id="faction-details-${index}" style="display: none;">
                        <div class="info-row">
                            <span class="info-label">势力背景</span>
                            <span class="info-value">${faction.background || '未设置'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">优势</span>
                            <span class="info-value">${(faction.strengths || []).slice(0, 3).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">劣势</span>
                            <span class="info-value">${(faction.weaknesses || []).slice(0, 3).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">盟友势力</span>
                            <span class="info-value allies">${(faction.relationships?.allies || []).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">敌对势力</span>
                            <span class="info-value enemies">${(faction.relationships?.enemies || []).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">剧情作用</span>
                            <span class="info-value">${faction.role_in_plot || '未设置'}</span>
                        </div>
                        <div class="info-row collapse-hint" onclick="toggleFactionDetails(${index}, event)">
                            <span class="info-value">点击收起 ↑</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    const modalHtml = `
        <div id="faction-system-modal" class="faction-modal" onclick="closeFactionModal(event)">
            <div class="faction-modal-content" onclick="event.stopPropagation()">
                <div class="faction-modal-header" id="modal-header">
                    <div class="header-icon">⚔️</div>
                    <div class="header-text">
                        <h2>势力/阵营系统</h2>
                        <p>查看和管理世界中的各个势力及其关系</p>
                    </div>
                    <button class="close-btn" onclick="closeFactionModal()">×</button>
                </div>
                
                <div id="faction-list-view">
                    <div class="faction-overview">
                        <div class="overview-card">
                            <div class="overview-icon">⚡</div>
                            <div class="overview-content">
                                <div class="overview-label">主要冲突</div>
                                <div class="overview-value">${mainConflict}</div>
                            </div>
                        </div>
                        <div class="overview-card">
                            <div class="overview-icon">⚖️</div>
                            <div class="overview-content">
                                <div class="overview-label">势力平衡</div>
                                <div class="overview-value">${powerBalance}</div>
                            </div>
                        </div>
                        <div class="overview-card">
                            <div class="overview-icon">🎯</div>
                            <div class="overview-content">
                                <div class="overview-label">推荐势力</div>
                                <div class="overview-value">${recommendedFaction}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="factions-grid-container">
                        <div class="factions-grid">
                            ${factionsHtml}
                        </div>
                    </div>
                    
                    <div class="faction-modal-footer">
                        <button class="btn btn-secondary" onclick="closeFactionModal()">关闭</button>
                    </div>
                </div>
                
                <div id="faction-detail-view" class="faction-detail-view"></div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 🔥 修复闪烁：添加 visible 类来显示模态框
    const modal = document.getElementById('faction-system-modal');
    if (modal) {
        modal.classList.add('visible');
    }
    
    // 动态设置滚动容器的高度
    setTimeout(() => {
        const modalContent = document.querySelector('.faction-modal-content');
        const listView = document.getElementById('faction-list-view');
        const gridContainer = document.querySelector('.factions-grid-container');
        
        if (modalContent && listView && gridContainer) {
            // 计算可用空间
            const headerHeight = document.querySelector('.faction-modal-header').offsetHeight;
            const overviewHeight = document.querySelector('.faction-overview').offsetHeight;
            const footerHeight = document.querySelector('.faction-modal-footer').offsetHeight;
            
            // 计算网格容器的高度
            const availableHeight = modalContent.offsetHeight - headerHeight - overviewHeight - footerHeight - 32; // 32px for margins
            
            // 设置高度
            gridContainer.style.height = `${availableHeight}px`;
            console.log('📏 势力网格容器高度已设置为:', availableHeight + 'px');
        }
    }, 100);
}

// 展开/收起势力详情
function toggleFactionDetails(index, event) {
    event.stopPropagation();
    
    const factionInfo = document.getElementById(`faction-info-${index}`);
    const expandedDetails = document.getElementById(`faction-details-${index}`);
    const expandHint = factionInfo.querySelector('.expand-hint');
    
    if (!expandedDetails || !factionInfo) return;
    
    if (expandedDetails.style.display === 'none') {
        // 展开详情
        expandedDetails.style.display = 'block';
        factionInfo.classList.remove('faction-info-collapsed');
        factionInfo.classList.add('faction-info-expanded');
        if (expandHint) {
            expandHint.style.display = 'none';
        }
    } else {
        // 收起详情
        expandedDetails.style.display = 'none';
        factionInfo.classList.remove('faction-info-expanded');
        factionInfo.classList.add('faction-info-collapsed');
        if (expandHint) {
            expandHint.style.display = 'flex';
        }
    }
}

// 显示势力详情（全屏详情视图，保留用于其他需要的地方）
function showFactionDetail(index) {
    if (!currentFactionsData || !currentFactionsData.factions) return;
    
    const faction = currentFactionsData.factions[index];
    if (!faction) return;
    
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏列表视图
    if (listView) listView.style.display = 'none';
    
    // 更新头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = faction.name;
        modalHeader.querySelector('.header-text p').textContent = faction.type || '未分类';
    }
    
    // 获取势力信息
    const powerLevel = faction.power_level || '未知';
    const strengths = (faction.strengths || []).join('、') || '无';
    const weaknesses = (faction.weaknesses || []).join('、') || '无';
    const allies = (faction.relationships?.allies || []).join('、') || '无';
    const enemies = (faction.relationships?.enemies || []).join('、') || '无';
    const territory = faction.territory || '未设置';
    const goals = (faction.goals || []).join('、') || '未设置';
    
    // 渲染详情视图
    if (detailView) {
        detailView.innerHTML = `
            <button class="detail-back-btn" onclick="hideFactionDetail()">
                <span>←</span>
                <span>返回列表</span>
            </button>
            
            <div class="detail-header">
                <div class="detail-header-content">
                    <h1 class="detail-name">${faction.name}</h1>
                    <div>
                        <span class="detail-type">${faction.type || '未分类'}</span>
                        <span class="detail-power-level">
                            <span>⚡</span>
                            <span>${powerLevel}</span>
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="detail-philosophy">
                "${faction.core_philosophy || '未设置核心理念'}"
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">📖</span>
                    <span>势力背景</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.background || '未设置背景信息'}</p>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🎯</span>
                    <span>势力目标</span>
                </h3>
                <div class="detail-section-content">
                    <p>${goals}</p>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🗺️</span>
                    <span>势力领地</span>
                </h3>
                <div class="detail-section-content">
                    <p>${territory}</p>
                </div>
            </div>
            
            <div class="detail-grid">
                <div class="detail-grid-item">
                    <div class="detail-grid-label">优势</div>
                    <div class="detail-grid-value">${strengths}</div>
                </div>
                <div class="detail-grid-item">
                    <div class="detail-grid-label">劣势</div>
                    <div class="detail-grid-value">${weaknesses}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🤝</span>
                    <span>势力关系</span>
                </h3>
                <div class="detail-grid">
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">盟友势力</div>
                        <div class="detail-grid-value allies">${allies}</div>
                    </div>
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">敌对势力</div>
                        <div class="detail-grid-value enemies">${enemies}</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🎬</span>
                    <span>剧情作用</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.role_in_plot || '未设置剧情作用'}</p>
                </div>
            </div>
            
            ${faction.suitable_for_protagonist === '是' ? `
                <div class="detail-section" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-color: var(--primary-color);">
                    <h3 class="detail-section-title">
                        <span class="detail-section-icon">⭐</span>
                        <span>主角推荐</span>
                    </h3>
                    <div class="detail-section-content">
                        <p style="color: var(--primary-light); font-weight: 600;">此势力推荐作为主角的初始势力</p>
                    </div>
                </div>
            ` : ''}
        `;
        
        detailView.classList.add('active');
    }
}

// 隐藏势力详情
function hideFactionDetail() {
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏详情视图
    if (detailView) {
        detailView.classList.remove('active');
    }
    
    // 恢复头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = '势力/阵营系统';
        modalHeader.querySelector('.header-text p').textContent = '查看和管理世界中的各个势力及其关系';
    }
    
    // 显示列表视图
    if (listView) listView.style.display = 'block';
}

function closeFactionModal(event) {
    // 如果没有事件对象，或者点击的是模态框背景，则关闭
    if (!event || event.target.id === 'faction-system-modal' || event.target.classList.contains('close-btn')) {
        const modal = document.getElementById('faction-system-modal');
        if (modal) {
            modal.classList.remove('visible');
            modal.classList.add('closing');
            setTimeout(() => modal.remove(), 300);
        }
    }
}

// 跳转到项目可视化界面
function viewProjectViewer() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到项目可视化界面
    window.location.href = `/project-viewer/${encodeURIComponent(projectTitle)}`;
}

// 跳转到世界观可视化界面
function viewWorldviewViewer() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到世界观可视化界面
    window.location.href = `/worldview-viewer/${encodeURIComponent(projectTitle)}`;
}

function createProductEditDrawer(category, productData) {
    const categoryNames = {
        'worldview': '世界观设定',
        'factions': '势力/阵营系统',
        'characters': '角色设计',
        'growth': '成长路线',
        'writing': '写作计划',
        'storyline': '故事线',
        'market': '市场分析'
    };

    const categoryIcons = {
        'worldview': '🌍',
        'factions': '⚔️',
        'characters': '👥',
        'growth': '📈',
        'writing': '📝',
        'storyline': '📖',
        'market': '📊'
    };

    const isWorldview = category === 'worldview';
    const isCharacters = category === 'characters';
    
    const drawerHtml = `
        <div id="product-edit-drawer" class="pt-drawer-overlay" onclick="closeProductEditDrawer()">
            <div class="pt-drawer" onclick="event.stopPropagation()">
                <div class="pt-drawer__header">
                    <div class="pt-drawer__title-group">
                        <div class="pt-drawer__icon">${categoryIcons[category]}</div>
                        <div class="pt-drawer__title-text">
                            <h3>${categoryNames[category]}</h3>
                            <p>编辑${categoryNames[category]}内容</p>
                        </div>
                    </div>
                    <button class="pt-drawer__close" onclick="closeProductEditDrawer()">×</button>
                </div>
                
                ${isWorldview ? `
                <div class="pt-drawer__tabs">
                    <button class="pt-drawer__tab active" data-tab="overview" onclick="switchDrawerTab('overview')">基础设定</button>
                    <button class="pt-drawer__tab" data-tab="power" onclick="switchDrawerTab('power')">力量体系</button>
                    <button class="pt-drawer__tab" data-tab="rules" onclick="switchDrawerTab('rules')">核心规则</button>
                    <button class="pt-drawer__tab" data-tab="geo" onclick="switchDrawerTab('geo')">地理历史</button>
                </div>
                ` : isCharacters ? `
                <div class="pt-drawer__tabs">
                    <button class="pt-drawer__tab active" data-tab="main" onclick="switchDrawerTab('main')">主角色</button>
                    <button class="pt-drawer__tab" data-tab="supporting" onclick="switchDrawerTab('supporting')">配角设定</button>
                    <button class="pt-drawer__tab" data-tab="relationships" onclick="switchDrawerTab('relationships')">角色关系</button>
                </div>
                ` : ''}
                
                <div class="pt-drawer__content">
                    ${isWorldview ? getWorldviewPanels(productData) : isCharacters ? getCharactersPanels(productData) : getGenericPanel(category, categoryNames, productData)}
                </div>
                
                <div class="pt-drawer__footer">
                    <span class="pt-drawer__status" id="save-status">未保存更改</span>
                    <div class="pt-drawer__actions">
                        <button class="pt-btn pt-btn--secondary" onclick="closeProductEditDrawer()">取消</button>
                        <button class="pt-btn pt-btn--primary" onclick="saveProductEdit('${category}')">保存修改</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', drawerHtml);
    requestAnimationFrame(() => {
        const overlay = document.getElementById('product-edit-drawer');
        if (overlay) overlay.classList.add('active');
    });
    
    initDrawerCharCount();
}

function getWorldviewPanels(productData) {
    return `
        <div class="pt-drawer__panel active" data-panel="overview">
            <div class="pt-form-section">
                <div class="pt-form-section__title">世界概述</div>
                <div class="pt-form-field">
                    <textarea class="pt-form-field__textarea" id="world-overview" placeholder="描述你的世界概况...">${extractField(productData?.content, 'world_overview')}</textarea>
                </div>
            </div>
            <div class="pt-form-section">
                <div class="pt-form-section__title">独特特色</div>
                <div class="pt-form-field">
                    <textarea class="pt-form-field__textarea" id="unique-features" placeholder="世界的独特之处...">${extractField(productData?.content, 'unique_features')}</textarea>
                </div>
            </div>
        </div>
        
        <div class="pt-drawer__panel" data-panel="power">
            <div class="pt-form-section">
                <div class="pt-form-section__title">力量体系</div>
                <div class="pt-form-field">
                    <textarea class="pt-form-field__textarea" id="power-system" placeholder="描述力量体系...">${extractField(productData?.content, 'power_system')}</textarea>
                </div>
            </div>
        </div>
        
        <div class="pt-drawer__panel" data-panel="rules">
            <div class="pt-form-section">
                <div class="pt-form-section__title">核心规则</div>
                <div class="pt-form-field">
                    <textarea class="pt-form-field__textarea" id="core-rules" placeholder="世界运行的核心规则...">${extractField(productData?.content, 'core_rules')}</textarea>
                </div>
            </div>
        </div>
        
        <div class="pt-drawer__panel" data-panel="geo">
            <div class="pt-form-section">
                <div class="pt-form-section__title">地理与历史</div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">地理环境</label>
                    <textarea class="pt-form-field__textarea" id="geography" placeholder="主要地理区域...">${extractField(productData?.content, 'geography')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">历史背景</label>
                    <textarea class="pt-form-field__textarea" id="history" placeholder="世界的历史演变...">${extractField(productData?.content, 'history_background')}</textarea>
                </div>
            </div>
        </div>
    `;
}

function getCharactersPanels(productData) {
    return `
        <div class="pt-drawer__panel active" data-panel="main">
            <div class="pt-form-section">
                <div class="pt-form-section__title">主角设定</div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">姓名</label>
                    <input type="text" class="pt-form-field__input" id="main-char-name" placeholder="主角姓名" value="${extractField(productData?.content, 'main_character_name')}">
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">性格特点</label>
                    <textarea class="pt-form-field__textarea" id="main-char-personality" placeholder="性格、气质、行为特征...">${extractField(productData?.content, 'main_character_personality')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">能力/技能</label>
                    <textarea class="pt-form-field__textarea" id="main-char-abilities" placeholder="特殊能力、技能、优势...">${extractField(productData?.content, 'main_character_abilities')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">背景故事</label>
                    <textarea class="pt-form-field__textarea" id="main-char-background" placeholder="出身、经历、动机...">${extractField(productData?.content, 'main_character_background')}</textarea>
                </div>
            </div>
        </div>
        
        <div class="pt-drawer__panel" data-panel="supporting">
            <div class="pt-form-section">
                <div class="pt-form-section__title">配角设定</div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">反派角色</label>
                    <textarea class="pt-form-field__textarea" id="antagonist" placeholder="主要反派的性格、目标...">${extractField(productData?.content, 'antagonist')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">帮手/师长</label>
                    <textarea class="pt-form-field__textarea" id="mentor" placeholder="引导主角的关键角色...">${extractField(productData?.content, 'mentor')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">配角群体</label>
                    <textarea class="pt-form-field__textarea" id="supporting-chars" placeholder="其他重要配角...">${extractField(productData?.content, 'supporting_characters')}</textarea>
                </div>
            </div>
        </div>
        
        <div class="pt-drawer__panel" data-panel="relationships">
            <div class="pt-form-section">
                <div class="pt-form-section__title">角色关系网</div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">与主角关系</label>
                    <textarea class="pt-form-field__textarea" id="relationships" placeholder="角色之间的关系、矛盾、羁绊...">${extractField(productData?.content, 'relationships')}</textarea>
                </div>
                <div class="pt-form-field">
                    <label class="pt-form-field__label">角色弧光</label>
                    <textarea class="pt-form-field__textarea" id="character-arcs" placeholder="各角色的成长轨迹...">${extractField(productData?.content, 'character_arcs')}</textarea>
                </div>
            </div>
        </div>
    `;
}

function getGenericPanel(category, categoryNames, productData) {
    return `
        <div class="pt-form-section">
            <div class="pt-form-field">
                <label class="pt-form-field__label">标题</label>
                <input type="text" class="pt-form-field__input" id="product-title" value="${productData?.title || categoryNames[category]}">
            </div>
            <div class="pt-form-field">
                <label class="pt-form-field__label">内容</label>
                <textarea class="pt-form-field__textarea" id="product-content" rows="25">${productData?.content || ''}</textarea>
            </div>
        </div>
    `;
}

function extractField(content, fieldName) {
    if (!content) return '';
    try {
        const data = JSON.parse(content);
        return data[fieldName] || '';
    } catch (e) {
        return '';
    }
}

function switchDrawerTab(tabName) {
    document.querySelectorAll('.pt-drawer__tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });
    document.querySelectorAll('.pt-drawer__panel').forEach(panel => {
        panel.classList.toggle('active', panel.dataset.panel === tabName);
    });
}

function initDrawerCharCount() {
    const textareas = document.querySelectorAll('.pt-form-field__textarea');
    textareas.forEach(textarea => {
        textarea.addEventListener('input', function() {
            const status = document.getElementById('save-status');
            if (status) {
                status.textContent = '未保存更改';
                status.classList.remove('saved');
            }
        });
    });
}

function closeProductEditDrawer() {
    const overlay = document.getElementById('product-edit-drawer');
    if (overlay) {
        overlay.classList.remove('active');
        setTimeout(() => overlay.remove(), 350);
    }
}

async function saveProductEdit(category) {
    try {
        showStatusMessage('🔄 正在保存...', 'info');
        
        let title, content;
        
        // 根据类别获取数据
        if (category === 'worldview') {
            title = '世界观设定';
            content = JSON.stringify({
                world_overview: document.getElementById('world-overview')?.value || '',
                unique_features: document.getElementById('unique-features')?.value || '',
                power_system: document.getElementById('power-system')?.value || '',
                core_rules: document.getElementById('core-rules')?.value || '',
                geography: document.getElementById('geography')?.value || '',
                history_background: document.getElementById('history')?.value || ''
            }, null, 2);
        } else if (category === 'characters') {
            title = '角色设计';
            content = JSON.stringify({
                main_character_name: document.getElementById('main-char-name')?.value || '',
                main_character_personality: document.getElementById('main-char-personality')?.value || '',
                main_character_abilities: document.getElementById('main-char-abilities')?.value || '',
                main_character_background: document.getElementById('main-char-background')?.value || '',
                antagonist: document.getElementById('antagonist')?.value || '',
                mentor: document.getElementById('mentor')?.value || '',
                supporting_characters: document.getElementById('supporting-chars')?.value || '',
                relationships: document.getElementById('relationships')?.value || '',
                character_arcs: document.getElementById('character-arcs')?.value || ''
            }, null, 2);
        } else {
            // 普通单字段模式
            title = document.getElementById('product-title')?.value?.trim() || categoryNames[category];
            content = document.getElementById('product-content')?.value?.trim() || '';
        }
        
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(currentProject.novel_title || currentProject.title)}/${category}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                content: content
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // 更新本地数据
            phaseOneProductsData[category] = {
                title: title,
                content: content,
                complete: true
            };
            
            // 更新显示状态
            updateProductsDisplay();
            
            closeProductEditDrawer();
            showStatusMessage('✅ 保存成功', 'success');
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        console.error('保存产物失败:', error);
        showStatusMessage(`❌ 保存失败: ${error.message}`, 'error');
    }
}

function closeProductEditModal() {
    const modal = document.getElementById('product-edit-modal');
    if (modal) {
        modal.classList.remove('visible');
        // 延迟移除DOM，等待动画完成
        setTimeout(() => {
            modal.remove();
        }, 300);
    }
}

function refreshPhaseOneProducts() {
    loadPhaseOneProducts();
}

async function exportPhaseOneProducts() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    showStatusMessage('📦 正在打包产物，请稍候...', 'info');

    try {
        const zip = new JSZip();
        const title = currentProject.novel_title || currentProject.title || '未命名小说';
        const folderName = title.replace(/[\\/:*?"<>|]/g, '_');
        const productsFolder = zip.folder(`${folderName}_第一阶段产物`);
        
        // 🔥 修复：优先使用 currentProject（项目原始数据）
        // 其次使用 phaseOneProductsData（前端显示数据）
        const products = [];
        
        // 1. 创意种子 - 从 currentProject.creative_seed 获取
        if (currentProject.creative_seed) {
            productsFolder.file('01_创意种子.json', JSON.stringify(currentProject.creative_seed, null, 2));
            products.push('01_创意种子.json');
        }
        
        // 2. 世界观设定 - 优先使用 currentProject，其次 phaseOneProductsData
        const worldviewData = currentProject.core_worldview || phaseOneProductsData.worldview?.content;
        if (worldviewData) {
            const content = typeof worldviewData === 'string' ? worldviewData : JSON.stringify(worldviewData, null, 2);
            productsFolder.file('02_世界观设定.json', content);
            products.push('02_世界观设定.json');
        }
        
        // 3. 势力/阵营系统 - 优先使用 currentProject
        const factionsData = currentProject.faction_system || currentProject.factions || phaseOneProductsData.factions?.content;
        if (factionsData) {
            const content = typeof factionsData === 'string' ? factionsData : JSON.stringify(factionsData, null, 2);
            productsFolder.file('03_势力系统.json', content);
            products.push('03_势力系统.json');
        }
        
        // 4. 角色设计 - 优先使用 currentProject
        const charactersData = currentProject.character_design || currentProject.characters || phaseOneProductsData.characters?.content;
        if (charactersData) {
            const content = typeof charactersData === 'string' ? charactersData : JSON.stringify(charactersData, null, 2);
            productsFolder.file('04_角色设计.json', content);
            products.push('04_角色设计.json');
        }
        
        // 5. 成长路线 - 优先使用 currentProject，其次 phaseOneProductsData
        const growthData = currentProject.global_growth_plan || currentProject.growth || phaseOneProductsData.growth?.content;
        if (growthData) {
            const content = typeof growthData === 'string' ? growthData : JSON.stringify(growthData, null, 2);
            productsFolder.file('05_成长路线.json', content);
            products.push('05_成长路线.json');
        }
        
        // 6. 写作计划 - 优先使用 currentProject，其次 phaseOneProductsData
        const writingData = currentProject.stage_writing_plans || currentProject.writing || phaseOneProductsData.writing?.content;
        if (writingData) {
            const content = typeof writingData === 'string' ? writingData : JSON.stringify(writingData, null, 2);
            productsFolder.file('06_写作计划.json', content);
            products.push('06_写作计划.json');
        }
        
        // 7. 故事线 - 优先使用 currentProject
        const storylineData = currentProject.storyline || currentProject.plot_outline || phaseOneProductsData.storyline?.content;
        if (storylineData) {
            const content = typeof storylineData === 'string' ? storylineData : JSON.stringify(storylineData, null, 2);
            productsFolder.file('07_故事线.json', content);
            products.push('07_故事线.json');
        }
        
        // 8. 市场分析 - 优先使用 currentProject，其次 phaseOneProductsData
        const marketData = currentProject.market_analysis || currentProject.market || phaseOneProductsData.market?.content;
        if (marketData) {
            const content = typeof marketData === 'string' ? marketData : JSON.stringify(marketData, null, 2);
            productsFolder.file('08_市场分析.json', content);
            products.push('08_市场分析.json');
        }
        
        // 9. 写作风格指南 - 从 currentProject 获取
        if (currentProject.writing_style_guide) {
            productsFolder.file('09_写作风格指南.json', JSON.stringify(currentProject.writing_style_guide, null, 2));
            products.push('09_写作风格指南.json');
        }
        
        // 10. 创建产物清单
        const manifest = {
            项目标题: title,
            导出时间: new Date().toLocaleString(),
            产物数量: products.length,
            产物列表: products
        };
        
        productsFolder.file('📋产物清单.json', JSON.stringify(manifest, null, 2));
        
        // 生成并下载 ZIP
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        saveAs(zipBlob, `${folderName}_第一阶段产物.zip`);
        
        showStatusMessage(`✅ 产物打包完成！共 ${products.length} 个产物`, 'success');
        
    } catch (error) {
        console.error('导出产物失败:', error);
        showStatusMessage(`❌ 导出失败: ${error.message}`, 'error');
    }
}

function validatePhaseOneProducts() {
    const categories = ['worldview', 'characters', 'growth', 'writing', 'storyline'];
    let completedCount = 0;
    let totalCount = categories.length;
    
    categories.forEach(category => {
        if (phaseOneProductsData[category] && phaseOneProductsData[category].content) {
            completedCount++;
        }
    });
    
    const percentage = Math.round((completedCount / totalCount) * 100);
    
    if (percentage === 100) {
        showStatusMessage('✅ 所有产物都已完成，可以开始章节生成', 'success');
    } else if (percentage >= 80) {
        showStatusMessage(`⚠️ 产物完成度 ${percentage}%，建议完善后再开始生成`, 'info');
    } else {
        showStatusMessage(`❌ 产物完成度仅 ${percentage}%，请先完善基本设定`, 'error');
    }
}

// ==================== 故事线跳转功能 ====================

function goToStorylinePage() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到故事线页面，并传递项目标题作为参数
    window.location.href = `/storyline?title=${encodeURIComponent(projectTitle)}`;
}

// ==================== 第二阶段生成功能 ====================
async function startPhaseTwoGeneration(event) {
    event.preventDefault();

    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    const formData = {
        from_chapter: parseInt(document.getElementById('from-chapter').value),
        chapters_to_generate: parseInt(document.getElementById('chapters-to-generate').value),
        chapters_per_batch: parseInt(document.getElementById('chapters-per-batch').value),
        generation_notes: document.getElementById('generation-notes').value,
        // 🔥 新增：字数阈值参数
        min_word_threshold: parseInt(document.getElementById('min-word-threshold')?.value || 1500),
        max_word_threshold: parseInt(document.getElementById('max-word-threshold')?.value || 3500)
    };

    // 计算所需点数
    const costPerChapter = pointsConfig?.phase2_chapter_batch || 2;
    const totalCost = formData.chapters_to_generate * costPerChapter;

    // 检查点数余额
    if (userBalance < totalCost) {
        const deficit = totalCost - userBalance;
        const confirmed = await showPointsInsufficientDialog(userBalance, totalCost, deficit);
        if (confirmed) {
            window.open('/recharge', '_blank');
        }
        return;
    }

    try {
        // 显示进度区域
        showProgressSection();
        hideGenerationForm();
        updateProgress(5, '正在启动第二阶段生成...');
        generationStartTime = Date.now();
        
        // 🚀 初始化章节队列
        chapterQueue.initQueue(formData.chapters_to_generate, formData.from_chapter);
        
        addLogEntry('info', `开始生成章节: 第${formData.from_chapter}章开始，生成${formData.chapters_to_generate}章`);

        // 调用第二阶段生成API
        const response = await fetch('/api/phase-two/start-generation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                novel_title: currentProject.novel_title,
                ...formData
            })
        });

        if (response.status === 401) {
            showStatusMessage('❌ 请先登录后再试', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            currentTaskId = result.task_id;
            updateStepStatus('generation', true);
            startProgressMonitoring();
            showControlButtons('generating');
            addLogEntry('success', `生成任务已启动: ${result.task_id}`);
        } else {
            throw new Error(result.error || '启动生成失败');
        }
    } catch (error) {
        hideProgressSection();
        showGenerationForm();
        showStatusMessage(`❌ 错误: ${error.message}`, 'error');
        addLogEntry('error', `启动生成失败: ${error.message}`);
        console.error('第二阶段生成失败:', error);
    }
}

function startProgressMonitoring() {
    if (!currentTaskId) return;
    
    // 初始化章节进度卡片
    initializeChapterProgress();
    
    // 启动用时计时器（每秒更新）
    const elapsedInterval = setInterval(() => {
        updateElapsedTime();
    }, 1000);
    
    // 将用时计时器ID保存到全局变量，以便清理
    window.elapsedInterval = elapsedInterval;
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/phase-two/task/${currentTaskId}/status`);
            if (!response.ok) return;

            const result = await response.json();
            // 🔥 修复：兼容两种数据格式（嵌套data或直接返回）
            const taskStatus = result.data || result;
            
            updateProgress(taskStatus.progress || 0, taskStatus.status_message || '生成中...');
            updateChapterProgress(taskStatus);
            updateCurrentChapterInfo(taskStatus);

            // 检查是否完成
            if (taskStatus.status === 'completed') {
                clearInterval(progressInterval);
                clearInterval(window.elapsedInterval);
                handleGenerationComplete(taskStatus);
            } else if (taskStatus.status === 'failed' || taskStatus.status === 'paused') {
                clearInterval(progressInterval);
                clearInterval(window.elapsedInterval);
                handleGenerationStopped(taskStatus);
            }
        } catch (error) {
            console.error('获取进度状态失败:', error);
            addLogEntry('error', `获取进度失败: ${error.message}`);
        }
    }, 2000); // 每2秒检查一次，更快的更新频率
}

function initializeChapterProgress() {
    const fromChapter = parseInt(document.getElementById('from-chapter').value);
    const chaptersToGenerate = parseInt(document.getElementById('chapters-to-generate').value);
    const grid = document.getElementById('chapter-progress-grid');
    
    // 标记是否已经开始生成
    window.generationStarted = false;
    
    let html = '';
    for (let i = 0; i < chaptersToGenerate; i++) {
        const chapterNumber = fromChapter + i;
        html += `
            <div class="v2-chapter-mini v2-chapter-mini--pending" id="chapter-${chapterNumber}" 
                 title="第${chapterNumber}章 - 等待中" 
                 data-chapter="${chapterNumber}"
                 onclick="showChapterDetails(${chapterNumber})">
                <span class="v2-chapter-mini__num">${chapterNumber}</span>
                <span class="v2-chapter-mini__status">等待</span>
            </div>
        `;
    }
    
    grid.innerHTML = html;
    // 添加grid类以便应用样式
    grid.classList.add('v2-chapter-grid');
    
    // 添加队列演示动画 - 预览效果
    setTimeout(() => {
        // 如果已经开始生成了，不要覆盖实际状态
        if (window.generationStarted) return;
        
        const firstCard = document.getElementById(`chapter-${fromChapter}`);
        const secondCard = document.getElementById(`chapter-${fromChapter + 1}`);
        
        if (firstCard) {
            firstCard.classList.remove('v2-chapter-mini--pending');
            firstCard.classList.add('v2-chapter-mini--generating');
            firstCard.querySelector('.v2-chapter-mini__status').textContent = '生成中';
        }
        if (secondCard) {
            secondCard.classList.remove('v2-chapter-mini--pending');
            secondCard.classList.add('v2-chapter-mini--queued');
            secondCard.querySelector('.v2-chapter-mini__status').textContent = '排队';
        }
        
        // 3秒后恢复等待状态（给用户足够时间看到效果）
        setTimeout(() => {
            // 再次检查，如果已经开始生成了，不要覆盖
            if (window.generationStarted) return;
            
            if (firstCard) {
                firstCard.classList.remove('v2-chapter-mini--generating');
                firstCard.classList.add('v2-chapter-mini--pending');
                firstCard.querySelector('.v2-chapter-mini__status').textContent = '等待';
            }
            if (secondCard) {
                secondCard.classList.remove('v2-chapter-mini--queued');
                secondCard.classList.add('v2-chapter-mini--pending');
                secondCard.querySelector('.v2-chapter-mini__status').textContent = '等待';
            }
        }, 3000);
    }, 500);
}

/**
 * 触发完成涟漪效果 - 当一个章节完成时，相邻章节会有波纹扩散效果
 */
function triggerRippleEffect(completedChapterNum) {
    // 获取相邻的章节（前后各1个）
    const neighbors = [
        document.getElementById(`chapter-${completedChapterNum - 1}`),
        document.getElementById(`chapter-${completedChapterNum + 1}`)
    ];
    
    neighbors.forEach((neighbor, index) => {
        if (neighbor) {
            // 延迟触发，产生波纹扩散效果
            setTimeout(() => {
                neighbor.style.animation = 'completion-ripple 0.6s ease-out';
                setTimeout(() => {
                    neighbor.style.animation = '';
                }, 600);
            }, index * 100); // 100ms间隔
        }
    });
}

function updateChapterProgress(taskStatus) {
    if (!taskStatus.chapter_progress) return;
    
    // 标记已经开始生成
    window.generationStarted = true;
    
    // 添加队列流动线效果
    const grid = document.getElementById('chapter-progress-grid');
    if (grid) {
        grid.classList.add('v2-chapter-grid--active');
    }
    
    // 显示队列进度条
    const queueProgressContainer = document.getElementById('queue-progress-container');
    if (queueProgressContainer) {
        queueProgressContainer.style.display = 'block';
    }
    
    // 计算队列进度
    const totalChapters = taskStatus.chapter_progress.length;
    const completedChapters = taskStatus.chapter_progress.filter(ch => ch.status === 'completed').length;
    const progressPercent = Math.round((completedChapters / totalChapters) * 100);
    
    // 更新队列进度条
    const queueProgressFill = document.getElementById('queue-progress-fill');
    const queueProgressText = document.getElementById('queue-progress-text');
    if (queueProgressFill) {
        queueProgressFill.style.width = `${progressPercent}%`;
    }
    if (queueProgressText) {
        queueProgressText.textContent = `${progressPercent}% (${completedChapters}/${totalChapters})`;
    }
    
    // 找出正在生成的章节和下一个排队的章节
    const generatingChapters = taskStatus.chapter_progress.filter(ch => ch.status === 'generating');
    console.log('[UpdateProgress] Generating chapters from API:', generatingChapters.map(ch => ch.chapter_number));
    
    const generatingIndex = taskStatus.chapter_progress.findIndex(ch => ch.status === 'generating');
    const nextQueuedIndex = generatingIndex >= 0 ? generatingIndex + 1 : -1;
    
    // 获取范围
    const fromChapter = parseInt(document.getElementById('from-chapter').value);
    
    taskStatus.chapter_progress.forEach((chapter, index) => {
        // 🚀 更新章节队列状态
        if (chapter.status === 'generating') {
            chapterQueue.updateChapterStatus(chapter.chapter_number, 'generating', chapter.progress || 0);
        } else if (chapter.status === 'completed') {
            chapterQueue.updateChapterStatus(chapter.chapter_number, 'completed', 100);
        } else if (chapter.status === 'failed') {
            chapterQueue.updateChapterStatus(chapter.chapter_number, 'error', 0);
        }
        
        const chapterCard = document.getElementById(`chapter-${chapter.chapter_number}`);
        if (chapterCard) {
            // 获取之前的状态（用于检测状态变化）
            const previousStatus = chapterCard.dataset.status || 'pending';
            
            // 确定状态：如果是下一个要生成的，标记为queued
            let displayStatus = chapter.status;
            if (chapter.status === 'pending' && index === nextQueuedIndex) {
                displayStatus = 'queued';
            }
            
            // 检测状态变化
            const statusChanged = previousStatus !== displayStatus;
            chapterCard.dataset.status = displayStatus;
            
            // 更新状态样式
            const statusClassMap = {
                'pending': 'v2-chapter-mini--pending',
                'queued': 'v2-chapter-mini--queued',
                'generating': 'v2-chapter-mini--generating',
                'completed': 'v2-chapter-mini--completed',
                'failed': 'v2-chapter-mini--error'
            };
            
            chapterCard.className = `v2-chapter-mini ${statusClassMap[displayStatus] || 'v2-chapter-mini--pending'}`;
            
            // 如果状态变为完成，触发完成动画和涟漪效果
            if (statusChanged && displayStatus === 'completed') {
                chapterCard.classList.add('v2-chapter-mini--just-completed');
                // 动画结束后移除类
                setTimeout(() => {
                    chapterCard.classList.remove('v2-chapter-mini--just-completed');
                }, 1200);
                
                // 触发相邻章节的涟漪效果
                triggerRippleEffect(chapter.chapter_number);
            }
            // 如果是生成中状态，添加脉冲效果
            else if (displayStatus === 'generating') {
                chapterCard.style.animation = 'pulse-card 1.5s ease-in-out infinite';
            }
            // 如果是排队状态，添加呼吸效果
            else if (displayStatus === 'queued') {
                chapterCard.style.animation = 'queue-waiting 2s ease-in-out infinite';
            }
            else {
                chapterCard.style.animation = '';
            }
            
            // 更新状态文字
            const statusElement = chapterCard.querySelector('.v2-chapter-mini__status');
            if (statusElement) {
                const statusTextMap = {
                    'pending': '等待',
                    'queued': '排队',
                    'generating': '生成中',
                    'completed': '完成',
                    'failed': '失败'
                };
                statusElement.textContent = statusTextMap[displayStatus] || '等待';
            }
            
            // 更新tooltip
            const statusText = getStatusText(chapter.status);
            const titleText = chapter.chapter_title || `第${chapter.chapter_number}章`;
            chapterCard.title = `${titleText} - ${statusText}${chapter.word_count ? ` (${chapter.word_count}字)` : ''}`;
            
            // 更新日志
            if (chapter.status === 'completed') {
                addLogEntry('success', `第${chapter.chapter_number}章生成完成: ${chapter.chapter_title}`);
            } else if (chapter.status === 'failed') {
                addLogEntry('error', `第${chapter.chapter_number}章生成失败: ${chapter.error || '未知错误'}`);
            }
        }
    });
}

function updateCurrentChapterInfo(taskStatus) {
    const infoDiv = document.getElementById('current-chapter-info');
    const currentChapter = taskStatus.current_chapter;
    
    if (currentChapter) {
        infoDiv.style.display = 'block';
        document.getElementById('current-chapter-title').textContent = currentChapter.title || `第${currentChapter.number}章`;
        document.getElementById('current-chapter-number').textContent = currentChapter.number;
    }
    // 总章节数从表单获取如果 taskStatus 中没有
    const totalChapters = taskStatus.total_chapters || parseInt(document.getElementById('chapters-to-generate')?.value) || 0;
    document.getElementById('total-chapters').textContent = totalChapters;
}

// 更新已用时间
function updateElapsedTime() {
    if (!generationStartTime) return;
    
    const elapsedMs = Date.now() - generationStartTime;
    const elapsedSeconds = Math.floor(elapsedMs / 1000);
    const minutes = Math.floor(elapsedSeconds / 60);
    const seconds = elapsedSeconds % 60;
    
    // 格式化时间显示
    let timeText;
    if (minutes > 0) {
        timeText = `用时: ${minutes}分${seconds.toString().padStart(2, '0')}秒`;
    } else {
        timeText = `用时: ${seconds}秒`;
    }
    
    // 更新页面上的用时显示
    const timeEl = document.getElementById('progress-time-elapsed');
    if (timeEl) {
        timeEl.textContent = timeText;
    }
    
    // 同时更新统计卡片中的用时
    const genTimeEl = document.getElementById('generation-time');
    if (genTimeEl) {
        genTimeEl.textContent = minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;
    }
}

// 显示章节详情（点击章节卡片时）
function showChapterDetails(chapterNumber) {
    const chapterCard = document.getElementById(`chapter-${chapterNumber}`);
    if (!chapterCard) return;
    
    const statusText = chapterCard.querySelector('.v2-chapter-mini__status').textContent;
    const statusClass = chapterCard.className;
    
    let detailText = '';
    if (statusClass.includes('generating')) {
        detailText = `第${chapterNumber}章正在生成中，AI正在创作内容...`;
    } else if (statusClass.includes('queued')) {
        detailText = `第${chapterNumber}章正在排队等待生成，请稍候...`;
    } else if (statusClass.includes('completed')) {
        detailText = `第${chapterNumber}章已生成完成！`;
    } else if (statusClass.includes('error')) {
        detailText = `第${chapterNumber}章生成失败，请检查日志。`;
    } else {
        detailText = `第${chapterNumber}章等待中，即将开始生成...`;
    }
    
    // 显示提示
    showNotification(detailText, 'info');
    
    // 添加点击动画
    chapterCard.style.transform = 'scale(0.95)';
    setTimeout(() => {
        chapterCard.style.transform = '';
    }, 150);
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'queued': '排队中',
        'generating': '生成中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

function handleGenerationComplete(taskStatus) {
    hideProgressSection();
    updateStepStatus('review', true);
    showGenerationResults(taskStatus);
    addLogEntry('success', '章节生成任务完成！');
    showStatusMessage('🎉 章节生成完成！', 'success');
    
    // 隐藏队列进度条
    const queueProgressContainer = document.getElementById('queue-progress-container');
    if (queueProgressContainer) {
        queueProgressContainer.style.display = 'none';
    }
    
    // 移除队列流动效果
    const grid = document.getElementById('chapter-progress-grid');
    if (grid) {
        grid.classList.remove('v2-chapter-grid--active');
    }
    
    // 🚀 清理章节队列（延迟2秒让用户看到完成效果）
    setTimeout(() => {
        chapterQueue.clear();
    }, 3000);
}

function handleGenerationStopped(taskStatus) {
    // 清理定时器
    if (progressInterval) {
        clearInterval(progressInterval);
        progressInterval = null;
    }
    if (window.elapsedInterval) {
        clearInterval(window.elapsedInterval);
        window.elapsedInterval = null;
    }
    
    showControlButtons('stopped');
    addLogEntry('warning', `生成已${taskStatus.status === 'paused' ? '暂停' : '停止'}`);
    showStatusMessage(`⚠️ 生成已${taskStatus.status === 'paused' ? '暂停' : '停止'}`, 'info');
}

function showGenerationResults(taskStatus) {
    const resultsDiv = document.getElementById('generation-results');
    if (!resultsDiv) return;
    
    resultsDiv.style.display = 'block';
    resultsDiv.classList.add('active');
    
    // 🔥 修复：处理 generated_chapters 可能是对象或数组的情况
    let generatedChapters = taskStatus.generated_chapters || [];
    
    // 如果是对象格式（键值对），转换为数组
    if (generatedChapters && typeof generatedChapters === 'object' && !Array.isArray(generatedChapters)) {
        generatedChapters = Object.values(generatedChapters);
    }
    
    // 从 chapter_progress 中提取已完成的章节作为备选数据源
    if ((!generatedChapters || generatedChapters.length === 0) && taskStatus.chapter_progress) {
        generatedChapters = taskStatus.chapter_progress.filter(ch => ch.status === 'completed');
    }
    
    console.log('[DEBUG] showGenerationResults:', {
        generatedChaptersCount: generatedChapters.length,
        taskStatus: taskStatus
    });
    
    // 计算统计信息
    const totalChapters = generatedChapters.length;
    const totalWords = generatedChapters.reduce((sum, chapter) => sum + (chapter.word_count || chapter.content?.length || 0), 0);
    const avgScore = totalChapters > 0 ? generatedChapters.reduce((sum, chapter) => sum + (chapter.quality_score || 0), 0) / totalChapters : 0;
    const generationTime = generationStartTime ? Math.round((Date.now() - generationStartTime) / 60000) : 0;
    
    // 安全地更新DOM元素
    const totalGeneratedEl = document.getElementById('total-generated');
    const totalWordsEl = document.getElementById('total-words');
    const avgScoreEl = document.getElementById('average-score');
    const genTimeEl = document.getElementById('generation-time');
    
    if (totalGeneratedEl) totalGeneratedEl.textContent = totalChapters;
    if (totalWordsEl) totalWordsEl.textContent = totalWords.toLocaleString();
    if (avgScoreEl) avgScoreEl.textContent = avgScore.toFixed(1);
    if (genTimeEl) genTimeEl.textContent = `${generationTime}分钟`;
}

// ==================== 控制功能 ====================
function pauseGeneration() {
    // 暂停功能需要后端支持
    showStatusMessage('⏸️ 暂停功能开发中...', 'info');
}

function resumeGeneration() {
    // 恢复功能需要后端支持
    showStatusMessage('▶️ 恢复功能开发中...', 'info');
}

async function stopGeneration() {
    if (!currentTaskId) {
        showStatusMessage('❌ 没有正在运行的生成任务', 'error');
        return;
    }
    
    if (!confirm('确定要停止当前生成任务吗？已生成的章节将被保留。')) {
        return;
    }
    
    showStatusMessage('⏹️ 正在停止生成任务...', 'info');
    
    try {
        // 调用停止生成 API
        const response = await fetch(`/api/generation/${currentTaskId}/stop`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const result = await response.json();
            showStatusMessage('✅ 生成任务已停止', 'success');
            
            // 清理定时器
            if (progressInterval) {
                clearInterval(progressInterval);
                progressInterval = null;
            }
            if (window.elapsedInterval) {
                clearInterval(window.elapsedInterval);
                window.elapsedInterval = null;
            }
            
            // 重置 UI 状态
            currentTaskId = null;
            document.getElementById('stop-btn').style.display = 'none';
            document.getElementById('start-btn').disabled = false;
            document.getElementById('start-btn').textContent = '🚀 开始生成章节';
        } else {
            const error = await response.json();
            showStatusMessage(`❌ 停止失败: ${error.message || '未知错误'}`, 'error');
        }
    } catch (error) {
        console.error('停止生成失败:', error);
        showStatusMessage('❌ 停止请求失败，请稍后重试', 'error');
        
        // 即使没有后端支持，也要重置前端状态
        currentTaskId = null;
        document.getElementById('stop-btn').style.display = 'none';
        document.getElementById('start-btn').disabled = false;
        showStatusMessage('⏹️ 已重置生成状态', 'info');
    }
}

function viewChapters() {
    if (!currentProject) return;
    window.location.href = `/novel?title=${encodeURIComponent(currentProject.novel_title)}`;
}

function goToChapterView() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    const projectTitle = currentProject.novel_title || currentProject.title;
    window.location.href = `/chapter-view?title=${encodeURIComponent(projectTitle)}`;
}

function continueMoreChapters() {
    hideGenerationResults();
    showGenerationForm();
    showStatusMessage('📝 继续生成更多章节', 'info');
}

function goToReading() {
    if (!currentProject) return;
    window.location.href = `/novel?title=${encodeURIComponent(currentProject.novel_title)}`;
}

function goToNovelView() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    const projectTitle = currentProject.novel_title || currentProject.title;
    window.location.href = `/novel?title=${encodeURIComponent(projectTitle)}`;
}

function goToContentReview() {
    console.log('📋 [DEBUG] goToContentReview函数被调用!!!');
    console.log('📋 [DEBUG] currentProject:', currentProject);
    
    try {
        let projectTitle = null;
    
    // 优先从currentProject获取
    if (currentProject) {
        projectTitle = currentProject.novel_title || currentProject.title;
        console.log('✅ 从currentProject获取到项目标题:', projectTitle);
    }
    
    // 如果currentProject没有，尝试从URL参数获取
    if (!projectTitle) {
        const urlParams = new URLSearchParams(window.location.search);
        const titleFromUrl = urlParams.get('title');
        if (titleFromUrl) {
            projectTitle = decodeURIComponent(titleFromUrl);
            console.log('✅ 从URL获取到项目标题:', projectTitle);
        }
    }
    
    // 如果还是没有，尝试从localStorage获取
    if (!projectTitle) {
        const storedProjectTitle = localStorage.getItem('selectedProjectTitle');
        if (storedProjectTitle) {
            projectTitle = storedProjectTitle;
            console.log('✅ 从localStorage获取到项目标题:', projectTitle);
        }
    }
    
    // 如果还是没有，提示用户选择项目
    if (!projectTitle) {
        showStatusMessage('⚠️ 请先在左侧列表选择一个项目', 'warning');
        showStatusMessage('💡 请先在左侧项目列表中点击选择一个项目', 'info');
        
        // 高亮显示项目列表
        const projectsList = document.getElementById('projects-list');
        if (projectsList) {
            projectsList.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // 闪烁效果提示
            projectsList.style.animation = 'highlight-pulse 2s ease-in-out 3';
        }
        return;
    }
    
        console.log('✅ [DEBUG] 准备跳转到内容审核页面');
        console.log('✅ [DEBUG] 项目标题:', projectTitle);
        
        if (!projectTitle) {
            console.error('❌ [DEBUG] 未能获取项目标题!');
            showStatusMessage('❌ 无法获取项目标题，请刷新页面重试', 'error');
            return;
        }
        
        console.log('🚀 [DEBUG] 执行跳转...');
        window.location.href = `/chapter-view?title=${encodeURIComponent(projectTitle)}`;
    } catch (error) {
        console.error('❌ [DEBUG] goToContentReview发生错误:', error);
        console.error('❌ [DEBUG] 错误堆栈:', error.stack);
        showStatusMessage(`❌ 跳转失败: ${error.message}`, 'error');
    }
}

// ==================== 标签页切换 ====================
function switchTab(tabName) {
    console.log(`[DEBUG] 切换到标签页: ${tabName}`);
    
    // 隐藏所有标签页内容
    const allTabs = document.querySelectorAll('.pt-tab-content');
    allTabs.forEach(tab => {
        tab.classList.remove('pt-tab-content--active');
    });
    
    // 显示目标标签页
    const targetTab = document.getElementById(`tab-${tabName}`);
    if (targetTab) {
        targetTab.classList.add('pt-tab-content--active');
    }
    
    // 更新步骤条状态
    const allSteps = document.querySelectorAll('.pt-step');
    allSteps.forEach(step => {
        step.classList.remove('pt-step--active');
        if (step.dataset.tab === tabName) {
            step.classList.add('pt-step--active');
        }
    });
    
    // 更新连接器状态
    updateStepConnectors(tabName);
    
    // 如果是阅读器标签，加载章节列表
    if (tabName === 'reader') {
        loadReaderChapterList();
    }
    
    // 如果是导出标签，更新统计数据
    if (tabName === 'export') {
        updateExportStats();
    }
}

// 更新步骤条连接器状态
function updateStepConnectors(activeTab) {
    const connectors = document.querySelectorAll('.pt-step-connector');
    const tabOrder = ['blueprint', 'generate', 'reader', 'export'];
    const activeIndex = tabOrder.indexOf(activeTab);
    
    connectors.forEach((connector, index) => {
        if (index < activeIndex) {
            connector.classList.add('pt-step-connector--completed');
        } else {
            connector.classList.remove('pt-step-connector--completed');
        }
    });
}

// ==================== 阅读器功能 ====================
let readerCurrentChapter = null;
let readerChapters = [];

// 加载阅读器章节列表
function loadReaderChapterList() {
    const listContainer = document.getElementById('reader-chapter-list');
    const countElement = document.getElementById('reader-chapter-count');
    const gridContainer = document.getElementById('reader-chapter-grid-list');
    const gridCountElement = document.getElementById('reader-chapter-grid-count');
    
    console.log('[DEBUG] loadReaderChapterList, currentProject:', currentProject);
    
    // 🔥 修复：处理多种数据格式
    let chapters = null;
    
    if (currentProject) {
        // 优先尝试 generated_chapters
        if (currentProject.generated_chapters) {
            chapters = currentProject.generated_chapters;
        }
        // 其次尝试 phase_info.generated_chapters
        else if (currentProject.phase_info && currentProject.phase_info.generated_chapters) {
            chapters = currentProject.phase_info.generated_chapters;
        }
    }
    
    if (!chapters) {
        console.log('[DEBUG] 没有章节数据');
        if (listContainer) {
            listContainer.innerHTML = '<div class="v2-reader-sidebar__empty">暂无章节</div>';
        }
        if (countElement) {
            countElement.textContent = '0章';
        }
        if (gridContainer) {
            gridContainer.innerHTML = '<div class="v2-reader-sidebar__empty">暂无已生成章节</div>';
        }
        if (gridCountElement) {
            gridCountElement.textContent = '0 章';
        }
        return;
    }
    
    console.log('[DEBUG] 章节数据:', chapters);
    
    // 转换章节数据为数组（如果还是对象格式）
    if (typeof chapters === 'object' && !Array.isArray(chapters)) {
        chapters = Object.values(chapters);
    }
    
    // 按章节号排序
    chapters.sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0));
    readerChapters = chapters;
    
    // 更新计数
    if (countElement) {
        countElement.textContent = `${chapters.length}章`;
    }
    if (gridCountElement) {
        gridCountElement.textContent = `${chapters.length} 章`;
    }
    
    // 生成传统列表HTML
    if (listContainer) {
        if (chapters.length === 0) {
            listContainer.innerHTML = '<div class="v2-reader-sidebar__empty">暂无章节</div>';
        } else {
            listContainer.innerHTML = chapters.map(ch => `
                <div class="v2-reader-sidebar__item ${ch.chapter_number === readerCurrentChapter ? 'v2-reader-sidebar__item--active' : ''}" 
                     onclick="readerLoadChapter(${ch.chapter_number})">
                    <span>第${ch.chapter_number}章</span>
                    <span style="color: rgba(255,255,255,0.4); font-size: 12px;">${ch.word_count || 0}字</span>
                </div>
            `).join('');
        }
    }
    
    // 生成网格入口HTML
    if (gridContainer) {
        if (chapters.length === 0) {
            gridContainer.innerHTML = '<div class="v2-reader-sidebar__empty">暂无已生成章节</div>';
        } else {
            gridContainer.innerHTML = chapters.map(ch => `
                <div class="v2-chapter-mini v2-chapter-mini--completed" 
                     onclick="openBookReaderAndLoadChapter(${ch.chapter_number})"
                     title="${ch.chapter_title || '第' + ch.chapter_number + '章'}">
                    <span class="v2-chapter-mini__num">${ch.chapter_number}</span>
                    <span class="v2-chapter-mini__status">已完成</span>
                </div>
            `).join('');
        }
    }
}

// 加载特定章节
function readerLoadChapter(chapterNum) {
    const chapter = readerChapters.find(ch => ch.chapter_number === chapterNum);
    if (!chapter) return;
    
    readerCurrentChapter = chapterNum;
    
    // 更新列表高亮
    document.querySelectorAll('.v2-reader-sidebar__item').forEach(item => {
        item.classList.remove('v2-reader-sidebar__item--active');
    });
    const activeItem = document.querySelector(`.v2-reader-sidebar__item:nth-child(${readerChapters.indexOf(chapter) + 1})`);
    if (activeItem) {
        activeItem.classList.add('v2-reader-sidebar__item--active');
    }
    
    // 更新标题和元数据
    const titleEl = document.getElementById('reader-chapter-title');
    const numberEl = document.getElementById('reader-chapter-number');
    const wordCountEl = document.getElementById('reader-word-count');
    const qualityScoreEl = document.getElementById('reader-quality-score');
    const textEl = document.getElementById('reader-chapter-text');
    
    // 更新右侧信息
    const infoWordCount = document.getElementById('info-word-count');
    const infoQualityScore = document.getElementById('info-quality-score');
    const infoGenTime = document.getElementById('info-gen-time');
    
    if (titleEl) titleEl.textContent = chapter.chapter_title || `第${chapter.chapter_number}章`;
    if (numberEl) numberEl.textContent = `第${chapter.chapter_number}章`;
    if (wordCountEl) wordCountEl.textContent = `${chapter.word_count || 0}字`;
    if (qualityScoreEl) qualityScoreEl.textContent = `质量分: ${chapter.quality_score || chapter.quality?.overall_score || '-'}`;
    
    if (infoWordCount) infoWordCount.textContent = `${chapter.word_count || 0}字`;
    if (infoQualityScore) infoQualityScore.textContent = chapter.quality_score || chapter.quality?.overall_score || '-';
    if (infoGenTime) infoGenTime.textContent = chapter.generated_at ? new Date(chapter.generated_at).toLocaleString() : '-';
    
    // 更新正文内容
    if (textEl) {
        const content = chapter.content || chapter.chapter_content || '暂无内容';
        // 将内容分段显示
        const paragraphs = content.split('\n').filter(p => p.trim());
        textEl.innerHTML = paragraphs.map(p => `<p style="margin-bottom: 1em; text-indent: 2em;">${p}</p>`).join('');
    }
    
    // 更新导航按钮状态
    updateReaderNavButtons();
}

// 更新导航按钮状态
function updateReaderNavButtons() {
    const prevBtn = document.getElementById('reader-prev-btn');
    const nextBtn = document.getElementById('reader-next-btn');
    
    if (prevBtn) {
        const currentIndex = readerChapters.findIndex(ch => ch.chapter_number === readerCurrentChapter);
        prevBtn.disabled = currentIndex <= 0;
    }
    
    if (nextBtn) {
        const currentIndex = readerChapters.findIndex(ch => ch.chapter_number === readerCurrentChapter);
        nextBtn.disabled = currentIndex >= readerChapters.length - 1;
    }
}

// 上一章
function readerPrevChapter() {
    const currentIndex = readerChapters.findIndex(ch => ch.chapter_number === readerCurrentChapter);
    if (currentIndex > 0) {
        readerLoadChapter(readerChapters[currentIndex - 1].chapter_number);
    }
}

// 下一章
function readerNextChapter() {
    const currentIndex = readerChapters.findIndex(ch => ch.chapter_number === readerCurrentChapter);
    if (currentIndex < readerChapters.length - 1) {
        readerLoadChapter(readerChapters[currentIndex + 1].chapter_number);
    }
}

// 返回列表
function readerBackToList() {
    readerCurrentChapter = null;
    document.getElementById('reader-chapter-title').textContent = '选择章节开始阅读';
    document.getElementById('reader-chapter-number').textContent = '-';
    document.getElementById('reader-word-count').textContent = '0字';
    document.getElementById('reader-quality-score').textContent = '质量分: -';
    document.getElementById('reader-chapter-text').innerHTML = `
        <div class="v2-reader-placeholder">
            <span>📖</span>
            <p>请从左侧选择章节开始阅读</p>
        </div>
    `;
    
    document.querySelectorAll('.v2-reader-sidebar__item').forEach(item => {
        item.classList.remove('v2-reader-sidebar__item--active');
    });
    
    updateReaderNavButtons();
}

// 重新生成章节
function readerRegenerateChapter() {
    if (!readerCurrentChapter) {
        showStatusMessage('请先选择一个章节', 'warning');
        return;
    }
    // 切换到生成标签并开始生成
    switchTab('generate');
    document.getElementById('from-chapter').value = readerCurrentChapter;
    document.getElementById('chapters-to-generate').value = 1;
    showStatusMessage(`已设置重新生成第${readerCurrentChapter}章，请点击"开始生成章节"`, 'info');
}

// 导出当前章节
function readerExportChapter() {
    if (!readerCurrentChapter) {
        showStatusMessage('请先选择一个章节', 'warning');
        return;
    }
    const chapter = readerChapters.find(ch => ch.chapter_number === readerCurrentChapter);
    if (chapter) {
        exportSingleChapter(chapter);
    }
}

// 复制章节内容
function readerCopyChapter() {
    if (!readerCurrentChapter) {
        showStatusMessage('请先选择一个章节', 'warning');
        return;
    }
    const chapter = readerChapters.find(ch => ch.chapter_number === readerCurrentChapter);
    if (chapter && chapter.content) {
        navigator.clipboard.writeText(chapter.content).then(() => {
            showStatusMessage('章节内容已复制到剪贴板', 'success');
        }).catch(() => {
            showStatusMessage('复制失败，请手动复制', 'error');
        });
    }
}

// ==================== 导出功能 ====================

// 更新导出页面统计数据
function updateExportStats() {
    if (!currentProject || !currentProject.generated_chapters) {
        document.getElementById('export-total-chapters').textContent = '0';
        document.getElementById('export-total-words').textContent = '0';
        document.getElementById('export-avg-score').textContent = '0';
        document.getElementById('export-avg-words').textContent = '0';
        return;
    }
    
    let chapters = currentProject.generated_chapters;
    if (typeof chapters === 'object' && !Array.isArray(chapters)) {
        chapters = Object.values(chapters);
    }
    
    const totalChapters = chapters.length;
    const totalWords = chapters.reduce((sum, ch) => sum + (ch.word_count || 0), 0);
    const avgScore = chapters.reduce((sum, ch) => sum + (ch.quality_score || ch.quality?.overall_score || 0), 0) / totalChapters;
    const avgWords = totalWords / totalChapters;
    
    document.getElementById('export-total-chapters').textContent = totalChapters;
    document.getElementById('export-total-words').textContent = totalWords.toLocaleString();
    document.getElementById('export-avg-score').textContent = avgScore.toFixed(1);
    document.getElementById('export-avg-words').textContent = Math.round(avgWords).toLocaleString();
}

// 导出小说
function exportNovel(format) {
    if (!currentProject || !currentProject.generated_chapters) {
        showStatusMessage('暂无章节可导出', 'warning');
        return;
    }
    
    let chapters = currentProject.generated_chapters;
    if (typeof chapters === 'object' && !Array.isArray(chapters)) {
        chapters = Object.values(chapters);
    }
    
    // 按章节号排序
    chapters.sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0));
    
    let content = '';
    const title = currentProject.novel_title || currentProject.title || '未命名小说';
    
    if (format === 'txt') {
        content = `${title}\n\n`;
        chapters.forEach(ch => {
            content += `第${ch.chapter_number}章 ${ch.chapter_title || ''}\n\n`;
            content += `${ch.content || ch.chapter_content || ''}\n\n`;
        });
    } else if (format === 'markdown') {
        content = `# ${title}\n\n`;
        chapters.forEach(ch => {
            content += `## 第${ch.chapter_number}章 ${ch.chapter_title || ''}\n\n`;
            content += `${ch.content || ch.chapter_content || ''}\n\n`;
        });
    } else if (format === 'docx') {
        showStatusMessage('Word导出功能开发中，请先使用Markdown格式', 'info');
        return;
    }
    
    // 下载文件
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showStatusMessage(`已导出 ${chapters.length} 章到 ${format.toUpperCase()} 文件`, 'success');
}

// 分章导出
function exportChaptersSeparate() {
    if (!currentProject || !currentProject.generated_chapters) {
        showStatusMessage('暂无章节可导出', 'warning');
        return;
    }
    
    showStatusMessage('分章导出功能开发中，将导出为ZIP压缩包', 'info');
}

// 导出单个章节
function exportSingleChapter(chapter) {
    const content = `第${chapter.chapter_number}章 ${chapter.chapter_title || ''}\n\n${chapter.content || chapter.chapter_content || ''}`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `第${chapter.chapter_number}章.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// 打包整个项目为 ZIP
async function exportProjectAsZip() {
    if (!currentProject) {
        showStatusMessage('请先选择一个项目', 'warning');
        return;
    }
    
    showStatusMessage('正在打包项目，请稍候...', 'info');
    
    try {
        const zip = new JSZip();
        const title = currentProject.novel_title || currentProject.title || '未命名小说';
        const folderName = title.replace(/[\\/:*?"<>|]/g, '_');
        const projectFolder = zip.folder(folderName);
        
        // 1. 添加小说正文（合并版）
        let novelContent = `${title}\n\n`;
        novelContent += `作者：${currentProject.author || 'AI生成'}\n`;
        novelContent += `总章节：${currentProject.total_chapters || 200}\n`;
        novelContent += `类别：${currentProject.category || '未分类'}\n\n`;
        novelContent += `简介：${currentProject.synopsis || '暂无简介'}\n\n`;
        novelContent += `========================\n\n`;
        
        // 获取章节列表
        let chapters = currentProject.generated_chapters || {};
        if (typeof chapters === 'object' && !Array.isArray(chapters)) {
            chapters = Object.values(chapters);
        }
        chapters.sort((a, b) => (a.chapter_number || 0) - (b.chapter_number || 0));
        
        // 添加每章内容到合并版
        chapters.forEach(ch => {
            novelContent += `第${ch.chapter_number}章 ${ch.chapter_title || ''}\n\n`;
            novelContent += `${ch.content || ch.chapter_content || ''}\n\n`;
            novelContent += `------------------------\n\n`;
        });
        
        projectFolder.file(`${folderName}_全文.txt`, novelContent);
        
        // 2. 创建分章文件夹
        const chaptersFolder = projectFolder.folder('分章');
        chapters.forEach(ch => {
            const chapterContent = `第${ch.chapter_number}章 ${ch.chapter_title || ''}\n\n`;
            const content = ch.content || ch.chapter_content || '暂无内容';
            chaptersFolder.file(`第${ch.chapter_number}章.txt`, chapterContent + content);
        });
        
        // 3. 添加设定文档
        const settingsFolder = projectFolder.folder('设定');
        
        // 世界观
        if (currentProject.core_worldview) {
            settingsFolder.file('世界观.txt', JSON.stringify(currentProject.core_worldview, null, 2));
        }
        
        // 角色设计
        if (currentProject.character_design) {
            settingsFolder.file('角色设计.txt', JSON.stringify(currentProject.character_design, null, 2));
        }
        
        // 成长路线
        if (currentProject.global_growth_plan) {
            settingsFolder.file('成长路线.txt', JSON.stringify(currentProject.global_growth_plan, null, 2));
        }
        
        // 写作计划
        if (currentProject.stage_writing_plans) {
            settingsFolder.file('写作计划.txt', JSON.stringify(currentProject.stage_writing_plans, null, 2));
        }
        
        // 4. 添加项目信息
        const projectInfo = {
            小说标题: title,
            作者: currentProject.author || 'AI生成',
            类别: currentProject.category || '未分类',
            总章节: currentProject.total_chapters || 200,
            已完成章节: chapters.length,
            总字数: chapters.reduce((sum, ch) => sum + (ch.word_count || 0), 0),
            创建时间: currentProject.created_at || '未知',
            简介: currentProject.synopsis || '暂无简介'
        };
        
        let infoContent = '项目信息\n';
        infoContent += '========================\n\n';
        Object.entries(projectInfo).forEach(([key, value]) => {
            infoContent += `${key}: ${value}\n`;
        });
        
        projectFolder.file('项目信息.txt', infoContent);
        
        // 5. 生成并下载 ZIP
        const zipBlob = await zip.generateAsync({ type: 'blob' });
        saveAs(zipBlob, `${folderName}_项目打包.zip`);
        
        showStatusMessage(`项目打包完成！包含 ${chapters.length} 章`, 'success');
        
    } catch (error) {
        console.error('打包项目失败:', error);
        showStatusMessage('打包项目失败: ' + error.message, 'error');
    }
}

// ==================== 工具函数 ====================
function showProgressSection() {
    const progressSection = document.getElementById('progress-section');
    const resultsSection = document.getElementById('generation-results');
    const formSection = document.getElementById('generation-form');
    const productsSection = document.getElementById('products-section');
    
    if (progressSection) {
        progressSection.classList.remove('pt-hidden');
        progressSection.classList.add('active');
    }
    if (resultsSection) {
        resultsSection.classList.add('pt-hidden');
        resultsSection.classList.remove('active');
    }
    if (formSection) {
        formSection.style.display = 'none';
    }
    // 隐藏第一阶段产物管理区域
    if (productsSection) {
        productsSection.style.display = 'none';
    }
}

function hideProgressSection() {
    const progressSection = document.getElementById('progress-section');
    if (progressSection) {
        progressSection.classList.add('pt-hidden');
        progressSection.classList.remove('active');
    }
}

function showGenerationForm() {
    // 🔥 修复：兼容不同版本的HTML结构
    const form = document.getElementById('phase-two-form') || document.getElementById('generation-form');
    const productsSection = document.getElementById('products-section');
    if (form) {
        form.style.display = 'block';
    }
    // 显示第一阶段产物管理区域
    if (productsSection) {
        productsSection.style.display = 'block';
    }
}

function hideGenerationForm() {
    // 🔥 修复：兼容不同版本的HTML结构
    const form = document.getElementById('phase-two-form') || document.getElementById('generation-form');
    if (form) {
        form.style.display = 'none';
    }
}

function hideGenerationResults() {
    const resultsDiv = document.getElementById('generation-results');
    if (resultsDiv) {
        resultsDiv.classList.remove('active');
    }
}

function updateProgress(percentage, message) {
    const progressBar = document.getElementById('progress-bar-fill');
    const percentageText = document.getElementById('progress-percentage');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (percentageText) {
        percentageText.textContent = `${percentage}%`;
    }
    
    addLogEntry('info', `进度: ${percentage}% - ${message}`);
}

function updateStepStatus(stepName, isActive) {
    const steps = ['setup', 'generation', 'review', 'complete'];
    const currentIndex = steps.indexOf(stepName);
    
    steps.forEach((step, index) => {
        const stepElement = document.getElementById(`step-${step}`);
        if (stepElement) {
            stepElement.classList.remove('active', 'completed');
            if (index < currentIndex) {
                stepElement.classList.add('completed');
            } else if (index === currentIndex && isActive) {
                stepElement.classList.add('active');
            } else {
                stepElement.classList.add('pending');
            }
        }
    });
}

function showControlButtons(state) {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    // 隐藏所有按钮
    [startBtn, pauseBtn, resumeBtn, stopBtn].forEach(btn => {
        if (btn) btn.style.display = 'none';
    });
    
    // 根据状态显示相应按钮
    if (state === 'generating') {
        if (pauseBtn) pauseBtn.style.display = 'inline-flex';
        if (stopBtn) stopBtn.style.display = 'inline-flex';
    } else if (state === 'stopped' || state === 'paused') {
        if (resumeBtn) resumeBtn.style.display = 'inline-flex';
        if (stopBtn) stopBtn.style.display = 'inline-flex';
    } else {
        if (startBtn) startBtn.style.display = 'inline-flex';
    }
}

function addLogEntry(level, message) {
    const logContainer = document.getElementById('generation-log');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    logContainer.appendChild(logEntry);
    
    // 保持最新的50条日志
    const entries = logContainer.children;
    if (entries.length > 50) {
        logContainer.removeChild(entries[0]);
    }
    
    // 自动滚动到底部
    logContainer.scrollTop = logContainer.scrollHeight;
}

function showStatusMessage(message, type) {
    const msgElement = document.getElementById('status-message');
    msgElement.className = `status-message ${type}`;
    msgElement.textContent = message;
    msgElement.style.display = 'block';
    
    // 5秒后自动隐藏成功和消息
    if (type === 'success') {
        setTimeout(() => {
            msgElement.style.display = 'none';
        }, 5000);
    }
}

// 退出登录函数
function logout() {
    if (confirm('确定要退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
});

// ==================== 翻页书阅读器兼容性函数 ====================
// 这些函数在 HTML 内联 script 中定义，这里提供空函数作为备份
if (typeof openBookReaderAndLoadChapter !== 'function') {
    window.openBookReaderAndLoadChapter = function(chapterNum) {
        // 如果 HTML 中的函数还未加载，显示提示
        console.warn('翻页书阅读器函数尚未加载');
        if (typeof showStatusMessage === 'function') {
            showStatusMessage('请等待页面加载完成后重试', 'info');
        }
    };
}

// ==================== 点数不足弹窗 ====================
function showPointsInsufficientDialog(currentBalance, requiredPoints, deficit) {
    return new Promise((resolve) => {
        // 创建弹窗背景
        const modalOverlay = document.createElement('div');
        modalOverlay.id = 'points-insufficient-modal';
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            backdrop-filter: blur(4px);
        `;
        
        // 创建弹窗内容
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: linear-gradient(135deg, #1e1e2e 0%, #2d2d44 100%);
            border-radius: 16px;
            padding: 32px;
            max-width: 420px;
            width: 90%;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.1);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        `;
        
        modalContent.innerHTML = `
            <div style="font-size: 48px; margin-bottom: 16px;">💎</div>
            <h3 style="font-size: 20px; font-weight: 600; color: #fff; margin-bottom: 8px;">点数不足</h3>
            <p style="font-size: 14px; color: rgba(255,255,255,0.6); margin-bottom: 24px;">
                当前余额不足以完成本次生成
            </p>
            
            <div style="background: rgba(0,0,0,0.2); border-radius: 12px; padding: 20px; margin-bottom: 24px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="color: rgba(255,255,255,0.6); font-size: 14px;">当前余额</span>
                    <span style="color: #fff; font-weight: 500;">${currentBalance} 点</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                    <span style="color: rgba(255,255,255,0.6); font-size: 14px;">需要点数</span>
                    <span style="color: #fff; font-weight: 500;">${requiredPoints} 点</span>
                </div>
                <div style="display: flex; justify-content: space-between; padding-top: 12px; border-top: 1px solid rgba(255,255,255,0.1);">
                    <span style="color: #ff6b6b; font-size: 14px;">还需充值</span>
                    <span style="color: #ff6b6b; font-weight: 600;">${deficit} 点</span>
                </div>
            </div>
            
            <div style="display: flex; gap: 12px;">
                <button id="btn-cancel-recharge" style="
                    flex: 1;
                    padding: 12px 20px;
                    background: rgba(255,255,255,0.1);
                    border: 1px solid rgba(255,255,255,0.2);
                    border-radius: 8px;
                    color: #fff;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s;
                ">稍后再说</button>
                <button id="btn-go-recharge" style="
                    flex: 1;
                    padding: 12px 20px;
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    border: none;
                    border-radius: 8px;
                    color: #fff;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                ">立即充值</button>
            </div>
            
            <p style="margin-top: 16px; font-size: 12px; color: rgba(255,255,255,0.4);">
                💡 充值后可立即继续生成
            </p>
        `;
        
        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);
        
        // 绑定按钮事件
        document.getElementById('btn-cancel-recharge').addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
            resolve(false);
        });
        
        document.getElementById('btn-go-recharge').addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
            resolve(true);
        });
        
        // 点击背景关闭
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                document.body.removeChild(modalOverlay);
                resolve(false);
            }
        });
    });
}
