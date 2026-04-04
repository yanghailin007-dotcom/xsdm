/**
 * 小说阅读器 JavaScript
 * 功能：章节加载、导航、阅读进度跟踪
 */

// ==================== 全局状态 ====================
let currentNovelTitle = '';
let currentChapterIndex = -1;
let chaptersList = [];
let currentFontSize = 18;
let isLoading = false;

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    console.log('小说阅读器初始化...');
    
    // 获取小说标题
    const urlParams = new URLSearchParams(window.location.search);
    currentNovelTitle = urlParams.get('title') || '';
    
    if (currentNovelTitle) {
        const toolbarTitle = document.getElementById('toolbar-title');
        if (toolbarTitle) toolbarTitle.textContent = currentNovelTitle;
        loadNovelInfo();
        loadChaptersList();
    }
    
    // 初始化阅读进度监听
    initProgressTracking();
});

// ==================== 小说信息 ====================
async function loadNovelInfo() {
    try {
        const response = await fetch(`/api/novel-info?title=${encodeURIComponent(currentNovelTitle)}`);
        const data = await response.json();
        
        if (data.success) {
            const novelTitle = document.getElementById('novel-title');
            const novelProgress = document.getElementById('novel-progress');
            const statusBadge = document.getElementById('novel-status');
            
            if (novelTitle) novelTitle.textContent = data.novel.title;
            if (novelProgress) novelProgress.textContent = `${data.novel.completed_chapters}/${data.novel.total_chapters} 章`;
            
            if (statusBadge) {
                statusBadge.textContent = data.novel.status === 'completed' ? '已完成' : '生成中';
                statusBadge.className = `status-badge status-badge--${data.novel.status}`;
            }
        }
    } catch (error) {
        console.error('加载小说信息失败:', error);
    }
}

// ==================== 章节列表 ====================
let currentPage = 1;
const chaptersPerPage = 20;

async function loadChaptersList() {
    try {
        const response = await fetch(`/api/chapters?title=${encodeURIComponent(currentNovelTitle)}`);
        const data = await response.json();
        
        if (data.success) {
            chaptersList = data.chapters;
            const chaptersCount = document.getElementById('chapters-count');
            if (chaptersCount) chaptersCount.textContent = `${chaptersList.length} 章`;
            renderChaptersList();
        }
    } catch (error) {
        console.error('加载章节列表失败:', error);
        const listContainer = document.getElementById('chapters-list');
        if (listContainer) {
            listContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <div class="empty-title">加载失败</div>
                    <div class="empty-desc">请刷新页面重试</div>
                </div>
            `;
        }
    }
}

function renderChaptersList() {
    const listContainer = document.getElementById('chapters-list');
    if (!listContainer) return;
    
    const start = (currentPage - 1) * chaptersPerPage;
    const end = start + chaptersPerPage;
    const pageChapters = chaptersList.slice(start, end);
    
    listContainer.innerHTML = pageChapters.map((chapter, idx) => {
        const globalIndex = start + idx;
        const isActive = globalIndex === currentChapterIndex;
        return `
            <div class="chapter-item ${isActive ? 'active' : ''}" 
                 onclick="selectChapter(${globalIndex})" 
                 data-index="${globalIndex}">
                <div class="chapter-item-number">${chapter.number}</div>
                <div class="chapter-item-info">
                    <div class="chapter-item-title">${chapter.title}</div>
                    <div class="chapter-item-meta">${chapter.word_count || 0} 字</div>
                </div>
            </div>
        `;
    }).join('');
    
    // 更新分页信息
    const totalPages = Math.ceil(chaptersList.length / chaptersPerPage);
    const currentPageEl = document.getElementById('current-page');
    const totalPagesEl = document.getElementById('total-pages');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    
    if (currentPageEl) currentPageEl.textContent = currentPage;
    if (totalPagesEl) totalPagesEl.textContent = totalPages;
    if (prevPageBtn) prevPageBtn.disabled = currentPage <= 1;
    if (nextPageBtn) nextPageBtn.disabled = currentPage >= totalPages;
}

function prevChapterPage() {
    if (currentPage > 1) {
        currentPage--;
        renderChaptersList();
    }
}

function nextChapterPage() {
    const totalPages = Math.ceil(chaptersList.length / chaptersPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        renderChaptersList();
    }
}

// ==================== 章节加载 ====================
async function selectChapter(index) {
    if (isLoading || index < 0 || index >= chaptersList.length) return;
    
    isLoading = true;
    currentChapterIndex = index;
    const chapter = chaptersList[index];
    
    // 更新章节列表高亮
    document.querySelectorAll('.chapter-item').forEach(item => {
        item.classList.remove('active');
        if (parseInt(item.dataset.index) === index) {
            item.classList.add('active');
            item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
    
    // 显示加载状态
    const contentEl = document.getElementById('chapter-content');
    if (contentEl) {
        contentEl.innerHTML = `
            <div class="loading-state">
                <div class="loading-spinner"></div>
                <div class="loading-text">正在加载第${chapter.number}章...</div>
            </div>
        `;
    }
    
    try {
        const response = await fetch(
            `/api/chapter?title=${encodeURIComponent(currentNovelTitle)}&chapter=${chapter.number}`
        );
        const data = await response.json();
        
        if (data.success) {
            renderChapter(data.chapter);
            updateNavigationButtons();
            // 关键：自动滚动到章节顶部
            setTimeout(() => scrollToChapterTop(), 100);
        } else {
            throw new Error(data.error || '加载失败');
        }
    } catch (error) {
        console.error('加载章节失败:', error);
        if (contentEl) {
            contentEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <div class="empty-title">加载失败</div>
                    <div class="empty-desc">${error.message}</div>
                </div>
            `;
        }
    } finally {
        isLoading = false;
    }
}

function renderChapter(chapter) {
    // 更新章节头部信息
    const chapterNumber = document.getElementById('chapter-number');
    const chapterTitle = document.getElementById('chapter-title');
    const wordCount = document.getElementById('word-count');
    const generatedTime = document.getElementById('generated-time');
    
    if (chapterNumber) chapterNumber.textContent = `第${chapter.number}章`;
    if (chapterTitle) chapterTitle.textContent = chapter.title;
    if (wordCount) wordCount.textContent = chapter.word_count || 0;
    if (generatedTime) generatedTime.textContent = 
        chapter.created_at ? new Date(chapter.created_at).toLocaleString() : '-';
    
    // 更新正文内容
    const contentEl = document.getElementById('chapter-content');
    if (contentEl) {
        contentEl.innerHTML = formatChapterContent(chapter.content);
    }
    
    // 更新调试信息
    updateDebugInfo(chapter);
}

function formatChapterContent(content) {
    if (!content) return '<p class="empty-text">本章暂无内容</p>';
    
    return content
        .split('\n')
        .filter(line => line.trim())
        .map(line => {
            // 检测对话
            if (line.includes('：') || line.includes(':')) {
                const [speaker, ...dialogue] = line.split(/[：:]/);
                if (dialogue.length > 0 && speaker.trim().length <= 20) {
                    return `<p class="dialogue"><span class="speaker">${speaker.trim()}</span>：${dialogue.join('：').trim()}</p>`;
                }
            }
            return `<p>${line.trim()}</p>`;
        })
        .join('');
}

function updateDebugInfo(chapter) {
    const debugChapterNum = document.getElementById('debug-chapter-num');
    const debugWordCount = document.getElementById('debug-word-count');
    const debugGenTime = document.getElementById('debug-gen-time');
    const debugStatus = document.getElementById('debug-status');
    const debugFilePath = document.getElementById('debug-file-path');
    
    if (debugChapterNum) debugChapterNum.textContent = chapter.number;
    if (debugWordCount) debugWordCount.textContent = chapter.word_count || 0;
    if (debugGenTime) debugGenTime.textContent = chapter.created_at ? new Date(chapter.created_at).toLocaleString() : '-';
    if (debugStatus) debugStatus.textContent = chapter.status || 'completed';
    if (debugFilePath) debugFilePath.textContent = chapter.file_path || '-';
    
    if (chapter.prompts) {
        const debugPrompts = document.getElementById('debug-prompts-content');
        if (debugPrompts) debugPrompts.textContent = 
            typeof chapter.prompts === 'string' ? chapter.prompts : JSON.stringify(chapter.prompts, null, 2);
    }
    if (chapter.ai_response) {
        const debugAi = document.getElementById('debug-ai-content');
        if (debugAi) debugAi.textContent = 
            typeof chapter.ai_response === 'string' ? chapter.ai_response : JSON.stringify(chapter.ai_response, null, 2);
    }
}

// ==================== 章节导航 ====================
function prevChapter() {
    if (currentChapterIndex > 0) {
        selectChapter(currentChapterIndex - 1);
    }
}

function nextChapter() {
    if (currentChapterIndex < chaptersList.length - 1) {
        selectChapter(currentChapterIndex + 1);
    }
}

function updateNavigationButtons() {
    const prevBtn = document.getElementById('prev-chapter-btn');
    const nextBtn = document.getElementById('next-chapter-btn');
    
    if (prevBtn) prevBtn.disabled = currentChapterIndex <= 0;
    if (nextBtn) nextBtn.disabled = currentChapterIndex >= chaptersList.length - 1;
    
    // 更新上下章标题
    const prevTitle = document.getElementById('prev-chapter-title');
    const nextTitle = document.getElementById('next-chapter-title');
    
    if (prevTitle) {
        if (currentChapterIndex > 0) {
            const prevChapter = chaptersList[currentChapterIndex - 1];
            prevTitle.textContent = `第${prevChapter.number}章 ${prevChapter.title}`;
        } else {
            prevTitle.textContent = '';
        }
    }
    
    if (nextTitle) {
        if (currentChapterIndex < chaptersList.length - 1) {
            const nextChapter = chaptersList[currentChapterIndex + 1];
            nextTitle.textContent = `第${nextChapter.number}章 ${nextChapter.title}`;
        } else {
            nextTitle.textContent = '';
        }
    }
}

// ==================== 滚动功能 ====================
function scrollToChapterTop() {
    // 平滑滚动到页面顶部
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    // 同时滚动章节头部到可视区域
    const chapterHeader = document.querySelector('.chapter-header');
    if (chapterHeader) {
        chapterHeader.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function scrollToChapterBottom() {
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}

// ==================== 阅读进度跟踪 ====================
function initProgressTracking() {
    const progressBar = document.getElementById('reading-progress-bar');
    if (!progressBar) return;
    
    window.addEventListener('scroll', () => {
        const scrollTop = window.scrollY;
        const docHeight = document.documentElement.scrollHeight - window.innerHeight;
        const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
        progressBar.style.width = progress + '%';
    });
}

// ==================== 主题切换 ====================
function setReadingTheme(theme) {
    const body = document.body;
    body.classList.remove('theme-light', 'theme-sepia', 'theme-dark');
    body.classList.add(`theme-${theme}`);
    localStorage.setItem('reading-theme', theme);
}

// 加载保存的主题
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('reading-theme') || 'dark';
    setReadingTheme(savedTheme);
});

// ==================== 键盘导航 ====================
document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    
    switch(e.key) {
        case 'ArrowLeft':
        case 'PageUp':
            e.preventDefault();
            prevChapter();
            break;
        case 'ArrowRight':
        case 'PageDown':
        case ' ':
            e.preventDefault();
            nextChapter();
            break;
        case 'Home':
            e.preventDefault();
            scrollToChapterTop();
            break;
        case 'End':
            e.preventDefault();
            scrollToChapterBottom();
            break;
    }
});

console.log('小说阅读器加载完成');
