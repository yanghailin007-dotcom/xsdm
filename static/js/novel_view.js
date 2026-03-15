/**
 * 小说阅读页面 - 前端逻辑
 * Novel View Page - Frontend Logic
 */

let currentChapter = 1;
let novelData = null;
let chaptersData = [];
let currentNovelTitle = null; // 当前小说标题

// 阅读模式相关变量
let isReadingMode = false; // 当前是否为阅读模式
let currentTheme = 'light'; // 当前阅读主题
let currentFontSize = 18; // 当前字体大小
let currentLineHeight = 1.8; // 当前行间距

// 分页系统相关变量
let paginationEnabled = true; // 是否启用分页
let currentPage = 1; // 当前页码
let totalPages = 1; // 总页数
let pageSizeLines = 40; // 每页行数 - 增加到40行以减少页数
let pageMode = 'line'; // 分页模式: 'line' 按行数, 'height' 按高度
let chapterPages = []; // 章节分页数据
let currentChapterContent = ''; // 当前章节的完整内容

// 章节分页相关变量
let chapterPaginationEnabled = true; // 是否启用章节分页
let currentChapterPage = 1; // 当前章节页码
let totalChapterPages = 1; // 章节总页数
let chapterPageItems = 8; // 每页显示章节数
let chapterPagesData = []; // 章节分页数据

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('初始化小说阅读页面...');

        // 从URL参数获取小说标题
        const urlParams = new URLSearchParams(window.location.search);
        const novelTitle = urlParams.get('title');

        if (!novelTitle) {
            showError('未指定小说标题，请从首页选择小说');
            return;
        }

        currentNovelTitle = novelTitle; // 设置当前小说标题

        // 加载指定小说的数据
        await loadNovelData(novelTitle);

        // 加载章节列表
        await loadChaptersList(novelTitle);

        // 加载第一章（如果存在）
        if (chaptersData.length > 0) {
            await loadChapter(novelTitle, chaptersData[0].chapter_number);
        }

        // 初始化章节分页和布局调整（在数据加载完成后）
        initializeChapterPagination();
    } catch (error) {
        console.error('初始化失败:', error);
        showError('页面初始化失败，请刷新重试');
    }
});

/**
 * 加载指定小说的数据
 */
async function loadNovelData(novelTitle) {
    try {
        const response = await fetch(`/api/project/${encodeURIComponent(novelTitle)}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('小说数据响应错误:', response.status, errorText);
            if (response.status === 404) {
                throw new Error('小说不存在');
            }
            throw new Error(`加载失败 (${response.status}): ${errorText}`);
        }

        novelData = await response.json();
        console.log('小说数据:', novelData);

        // 更新 UI
        const titleElement = document.getElementById('novel-title');
        const progressElement = document.getElementById('novel-progress');
        const toolbarTitle = document.getElementById('toolbar-title');
        
        const displayTitle = novelData.novel_title || novelData.title || novelTitle;
        
        if (titleElement) {
            titleElement.textContent = displayTitle;
        }
        
        if (toolbarTitle) {
            toolbarTitle.textContent = displayTitle;
        }
        
        if (progressElement) {
            // 优先使用 current_progress.total_chapters，然后是其他可能的字段
            const totalChapters = novelData.current_progress?.total_chapters ||
                               novelData.total_chapters ||
                               novelData.chapter_index?.length ||
                               50; // 默认50章
            
            const completedChapters = chaptersData.length || 0;
            progressElement.textContent = `${completedChapters}/${totalChapters} 章`;
            
            console.log('📊 进度更新:', {
                completedChapters: completedChapters,
                totalChapters: totalChapters,
                progressText: `${completedChapters}/${totalChapters}`
            });
        }

        // 更新页面标题
        document.title = `${displayTitle} - 大文娱创作平台`;

    } catch (error) {
        console.error('加载小说数据失败:', error);
        console.error('错误详情:', error.message, error.stack);
        throw error;
    }
}

/**
 * 加载章节列表
 */
async function loadChaptersList(novelTitle) {
    try {
        const response = await fetch(`/api/project/${encodeURIComponent(novelTitle)}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('章节列表响应错误:', response.status, errorText);
            throw new Error(`加载失败 (${response.status}): ${errorText}`);
        }

        const novelProject = await response.json();
        const generatedChapters = novelProject.generated_chapters || {};

        // 将生成的章节转换为数组格式
        chaptersData = Object.values(generatedChapters).map(chapter => ({
            chapter_number: chapter.chapter_number,
            title: chapter.title || `第${chapter.chapter_number}章`,
            content: chapter.content,
            word_count: chapter.content ? chapter.content.length : 0,
            score: '-' // 暂时没有评分
        })).sort((a, b) => a.chapter_number - b.chapter_number);

        console.log('章节列表:', chaptersData);

        // 生成章节列表 HTML
        const listContainer = document.getElementById('chapters-list');

        if (chaptersData.length === 0) {
            listContainer.innerHTML = '<div style="text-align: center; color: #999;">暂无章节</div>';
            return;
        }

        // 执行章节分页
        paginateChaptersList();

        // 初始化导航按钮
        updateNavigationButtons();

    } catch (error) {
        console.error('加载章节列表失败:', error);
        console.error('错误详情:', error.message, error.stack);
        throw error;
    }
}

/**
 * 加载特定章节
 */
async function loadChapter(novelTitle, chapterNum) {
    try {
        console.log('加载第', chapterNum, '章...');

        // 同时加载章节内容和质量数据
        const [chapterResponse, qualityResponse] = await Promise.all([
            fetch(`/api/project/${encodeURIComponent(novelTitle)}/chapter/${chapterNum}`),
            fetch(`/api/project/${encodeURIComponent(novelTitle)}/chapter/${chapterNum}/quality`)
        ]);

        if (!chapterResponse.ok) {
            const errorText = await chapterResponse.text();
            console.error('章节响应错误:', chapterResponse.status, errorText);
            throw new Error(`章节不存在 (${chapterResponse.status}): ${errorText}`);
        }

        const chapter = await chapterResponse.json();
        const qualityData = qualityResponse.ok ? await qualityResponse.json() : {};

        console.log('章节数据:', chapter);
        console.log('质量数据:', qualityData);

        currentChapter = chapterNum;

        // 更新活跃状态
        document.querySelectorAll('.chapter-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chapter == chapterNum) {
                item.classList.add('active');
            }
        });

        // 更新中间内容区
        updateCenterContent(chapter);

        // 更新右侧生成信息区
        updateGenerationInfoPanel(chapter, qualityData);

        // 更新导航按钮
        updateNavigationButtons();

    } catch (error) {
        console.error('加载章节失败:', error);
        console.error('错误详情:', error.message, error.stack);
        showError(`加载章节失败: ${error.message}`);
    }
}

/**
 * 更新中间内容区
 */
function updateCenterContent(chapter) {
    const title = chapter.title || `第${chapter.chapter_number}章`;
    const wordCount = chapter.content ? chapter.content.length : 0;
    const generatedTime = chapter.generated_at
        ? new Date(chapter.generated_at).toLocaleString('zh-CN')
        : '未知';

    // 更新标题和元信息
    const titleElement = document.getElementById('chapter-title');
    const numberElement = document.getElementById('chapter-number');
    
    if (titleElement) titleElement.textContent = title;
    if (numberElement) numberElement.textContent = `第 ${chapter.chapter_number} 章`;

    // 保存章节内容到全局变量，供分页系统使用
    if (chapter.content) {
        currentChapterContent = chapter.content;
        console.log('设置章节内容供分页使用，字数:', chapter.content.length);
    }

    // 更新内容（保留原始格式，包括特殊标记）
    const contentBody = document.getElementById('chapter-content');
    if (chapter.content) {
        // 如果启用分页，使用分页显示
        if (paginationEnabled) {
            setTimeout(() => {
                paginateChapterContent(chapter.content);
            }, 100);
        } else {
            // 直接使用内容，让CSS处理换行
            contentBody.innerHTML = `<div class="novel-content-raw">${escapeHtml(chapter.content)}</div>`;
            // 后处理特殊标记
            postProcessContent(contentBody);
        }
    } else {
        contentBody.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚠️</div>
                <div class="empty-title">内容加载失败</div>
                <div class="empty-desc">该章节暂无内容</div>
            </div>
        `;
    }

    // 更新元信息
    const wordCountElement = document.getElementById('word-count');
    const genTimeElement = document.getElementById('generated-time');
    
    if (wordCountElement) wordCountElement.textContent = wordCount.toLocaleString() + ' 字';
    if (genTimeElement) genTimeElement.textContent = generatedTime;
    
    // 更新工具栏标题
    const toolbarTitle = document.getElementById('toolbar-title');
    if (toolbarTitle) toolbarTitle.textContent = title;
}

/**
 * 后处理内容，应用特殊格式（网络小说样式）
 */
function postProcessContent(container) {
    const contentDiv = container.querySelector('.novel-content-raw');
    if (!contentDiv) return;

    let html = contentDiv.textContent; // 获取纯文本内容

    // 确保换行符统一
    html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // 处理分隔线 "══" - 网络小说常见样式
    html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');

    // 处理特殊标记，使其更像网络小说风格
    html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');

    // 网络小说常见的段落处理：每两个换行符分成一个段落
    let paragraphs = html.split(/\n\s*\n/);
    let result = '<div class="novel-content">';

    for (let paragraph of paragraphs) {
        paragraph = paragraph.trim();
        if (paragraph) {
            // 处理段落内的单换行符，但保留段落结构
            paragraph = paragraph.replace(/\n/g, '<br>');
            result += `<p class="novel-text">${paragraph}</p>`;
        }
    }

    result += '</div>';
    contentDiv.innerHTML = result;
}

/**
 * 更新评估面板
 */
function updateAssessmentPanel(chapter) {
    const assessment = chapter.assessment || {};
    
    // 评分
    const score = assessment.score 
        || assessment.整体评分 
        || assessment['整体评分']
        || '-';
    
    document.getElementById('quality-score').textContent = 
        typeof score === 'number' ? score.toFixed(1) : score;
    
    // 评级
    const rating = assessment.rating 
        || assessment.评级
        || assessment['评级']
        || calculateRating(score);
    
    document.getElementById('quality-rating').textContent = rating;
    
    // 优点列表
    const pros = assessment.pros 
        || assessment.优点
        || assessment['优点']
        || [];
    
    const prosList = document.getElementById('pros-list');
    prosList.innerHTML = (Array.isArray(pros) && pros.length > 0)
        ? pros.map(p => `<li>${escapeHtml(p)}</li>`).join('')
        : '<li>暂无优点评价</li>';
    
    // 改进建议列表
    const cons = assessment.cons 
        || assessment.建议
        || assessment['改进建议']
        || assessment['改进建议']
        || [];
    
    const consList = document.getElementById('cons-list');
    consList.innerHTML = (Array.isArray(cons) && cons.length > 0)
        ? cons.map(c => `<li>${escapeHtml(c)}</li>`).join('')
        : '<li>暂无改进建议</li>';
}

/**
 * 更新生成信息面板（新版抽屉式UI）
 */
function updateGenerationInfoPanel(chapter, qualityData) {
    console.log('更新生成信息面板...', qualityData);

    // 更新概览Tab
    updateDebugOverview(chapter, qualityData);

    // 更新提示词Tab
    updateDebugPrompts(chapter, qualityData);

    // 更新AI响应Tab
    updateDebugAIResponse(chapter, qualityData);

    // 更新质量评价Tab
    updateDebugQuality(chapter, qualityData);
}

/**
 * 更新调试概览Tab
 */
function updateDebugOverview(chapter, qualityData) {
    // 基本信息
    const wordCount = chapter.content ? chapter.content.length : 0;
    const genTime = chapter.generated_at 
        ? new Date(chapter.generated_at).toLocaleString('zh-CN')
        : '未知';
    
    document.getElementById('debug-chapter-num').textContent = chapter.chapter_number || '-';
    document.getElementById('debug-word-count').textContent = wordCount.toLocaleString() + ' 字';
    document.getElementById('debug-gen-time').textContent = genTime;
    document.getElementById('debug-status').textContent = chapter.content ? '已完成' : '未生成';
    
    // 文件路径
    document.getElementById('debug-file-path').textContent = chapter.file_path || '无';
}

/**
 * 更新提示词Tab
 */
function updateDebugPrompts(chapter, qualityData) {
    const container = document.getElementById('debug-prompts-content');
    if (!container) return;
    
    const data = {
        chapter_info: {
            chapter_number: chapter.chapter_number,
            title: chapter.title,
            word_count: chapter.content ? chapter.content.length : 0,
            file_path: chapter.file_path,
            generated_at: chapter.generated_at
        },
        writing_plans: qualityData.writing_plan || {},
        events: qualityData.events || [],
        character_relationships: qualityData.character_relationships || {}
    };
    
    container.textContent = JSON.stringify(data, null, 2);
}

/**
 * 更新AI响应Tab
 */
function updateDebugAIResponse(chapter, qualityData) {
    const container = document.getElementById('debug-ai-content');
    if (!container) return;
    
    const data = {
        generation_result: {
            chapter_number: chapter.chapter_number,
            title: chapter.title,
            word_count: chapter.content ? chapter.content.length : 0,
            content_preview: chapter.content ? chapter.content.substring(0, 500) + '...' : '无内容',
            generated_at: chapter.generated_at
        },
        failures: qualityData.chapter_failures || [],
        generation_context: qualityData.generation_context || {},
        api_calls: qualityData.api_calls || []
    };
    
    container.textContent = JSON.stringify(data, null, 2);
}

/**
 * 更新质量评价Tab
 */
function updateDebugQuality(chapter, qualityData) {
    const container = document.getElementById('debug-quality-content');
    if (!container) return;
    
    const data = {
        assessment: chapter.assessment || {},
        character_development: qualityData.character_development || {},
        world_state: qualityData.world_state || {},
        events: qualityData.events || [],
        quality_metrics: {
            章节字数: chapter.content ? chapter.content.length : 0,
            段落数量: chapter.content ? chapter.content.split(/\n\s*\n/).length : 0,
            生成时间: chapter.generated_at || '未知',
            生成状态: '已完成'
        }
    };
    
    container.textContent = JSON.stringify(data, null, 2);
}

// 保留旧版函数以兼容（如果有其他地方调用）
function updateInputPrompts(chapter, qualityData) {
    // 新版UI已整合到 updateDebugPrompts
    updateDebugPrompts(chapter, qualityData);
}

function updateAIResponses(chapter, qualityData) {
    // 新版UI已整合到 updateDebugAIResponse
    updateDebugAIResponse(chapter, qualityData);
}

function updateQualityEvaluation(chapter, qualityData) {
    // 新版UI已整合到 updateDebugQuality
    updateDebugQuality(chapter, qualityData);
}


/**
 * 根据评分计算评级
 */
function calculateRating(score) {
    if (typeof score !== 'number') return '未评估';
    if (score >= 9) return '优秀';
    if (score >= 8) return '很好';
    if (score >= 7) return '良好';
    if (score >= 6) return '及格';
    return '需改进';
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * 显示错误信息
 */
function showError(message) {
    const contentBody = document.getElementById('chapter-content');
    if (contentBody) {
        contentBody.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <div class="empty-title">加载失败</div>
                <div class="empty-desc">${escapeHtml(message)}</div>
            </div>
        `;
    } else {
        // 如果contentBody不存在，使用alert作为备用
        alert(`错误: ${message}`);
    }
}

/**
 * 导出 JSON
 */
async function exportJSON() {
    try {
        const response = await fetch('/api/export-json');
        if (!response.ok) throw new Error('导出失败');
        
        const data = await response.json();
        
        // 生成 JSON 文件
        const filename = `novel_${data.novel.id}_${new Date().getTime()}.json`;
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        alert('✅ JSON 导出成功！');
    } catch (error) {
        console.error('导出失败:', error);
        alert('❌ 导出失败: ' + error.message);
    }
}

/**
 * 上一章
 */
function prevChapter() {
    const prevChapterData = chaptersData.find(c => c.chapter_number < currentChapter);
    if (prevChapterData) {
        loadChapter(currentNovelTitle, prevChapterData.chapter_number);
        // 在阅读模式下，切换章节后滚动到开头
        if (isReadingMode) {
            setTimeout(() => {
                scrollToReadingContentTop();
            }, 100);
        }
    }
}

/**
 * 下一章
 */
function nextChapter() {
    const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
    if (nextChapterData) {
        loadChapter(currentNovelTitle, nextChapterData.chapter_number);
        // 在阅读模式下，切换章节后滚动到开头
        if (isReadingMode) {
            setTimeout(() => {
                scrollToReadingContentTop();
            }, 100);
        }
    }
}

/**
 * 更新导航按钮状态
 */
function updateNavigationButtons() {
    const hasPrev = chaptersData.some(c => c.chapter_number < currentChapter);
    const hasNext = chaptersData.some(c => c.chapter_number > currentChapter);
    
    const prevBtn = document.getElementById('prev-chapter-btn');
    const nextBtn = document.getElementById('next-chapter-btn');
    
    if (prevBtn) prevBtn.disabled = !hasPrev;
    if (nextBtn) nextBtn.disabled = !hasNext;
}

// 键盘快捷键
document.addEventListener('keydown', (event) => {
    // 防止在输入框中触发
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        // 上一章
        const prevChapter = chaptersData.find(c => c.chapter_number < currentChapter);
        if (prevChapter) {
            loadChapter(currentNovelTitle, prevChapter.chapter_number);
            // 在阅读模式下，切换章节后滚动到开头
            if (isReadingMode) {
                setTimeout(() => {
                    scrollToReadingContentTop();
                }, 100);
            }
        }
    } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        // 下一章
        const nextChapter = chaptersData.find(c => c.chapter_number > currentChapter);
        if (nextChapter) {
            loadChapter(currentNovelTitle, nextChapter.chapter_number);
            // 在阅读模式下，切换章节后滚动到开头
            if (isReadingMode) {
                setTimeout(() => {
                    scrollToReadingContentTop();
                }, 100);
            }
        }
    }
});

// 自动刷新进度 - 智能版本
let progressInterval = null;
let hasStartedGeneration = false;
let progressHidden = false;

function startProgressMonitoring() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/novel/summary');
            if (response.ok) {
                const data = await response.json();
                const currentChapters = data.chapters_count || 0;
                const totalChapters = data.total_chapters || 200;
                
                // 更新进度显示（仅在没有隐藏时显示）
                const progressElement = document.getElementById('novel-progress');
                const statusElement = document.getElementById('novel-status');
                
                if (!progressHidden && progressElement) {
                    progressElement.textContent = `${currentChapters}/${totalChapters}`;
                }
                
                // 检测是否开始生成小说
                if (currentChapters > 0 && !hasStartedGeneration) {
                    hasStartedGeneration = true;
                    console.log('🚀 检测到小说开始生成，准备隐藏进度条');
                }
                
                // 如果开始生成后已经有章节，并且不是刚开始，就隐藏进度条
                if (hasStartedGeneration && currentChapters >= 1 && !progressHidden) {
                    hideProgressBar();
                    progressHidden = true;
                    
                    // 停止进度监控
                    clearInterval(progressInterval);
                    progressInterval = null;
                    
                    console.log('✅ 进度条已隐藏 - 小说正在正常生成，可以自由操作');
                    
                    // 显示友好通知
                    showProgressNotification('小说正在生成中，您可以自由浏览和操作');
                }
            }
        } catch (error) {
            // 静默处理错误
            console.warn('进度更新失败:', error);
        }
    }, 3000); // 改为3秒检查一次，更快响应
}

function hideProgressBar() {
    // 隐藏进度显示区域
    const progressElement = document.getElementById('novel-progress');
    if (progressElement && progressElement.parentElement) {
        progressElement.parentElement.style.display = 'none';
    }
    
    // 更新状态为正常浏览
    const statusElement = document.getElementById('novel-status');
    if (statusElement) {
        const statusBadge = statusElement.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = '可正常浏览';
            statusBadge.className = 'status-badge status-normal';
        }
    }
    
    console.log('📖 进度条已隐藏，进入正常浏览模式');
}

function showProgressBar() {
    // 显示进度显示区域
    const progressElement = document.getElementById('novel-progress');
    if (progressElement && progressElement.parentElement) {
        progressElement.parentElement.style.display = 'block';
    }
    
    // 更新状态
    const statusElement = document.getElementById('novel-status');
    if (statusElement) {
        const statusBadge = statusElement.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.textContent = '生成中';
            statusBadge.className = 'status-badge status-generating';
        }
    }
}

// 显示进度通知
function showProgressNotification(message) {
    // 检查是否已有通知，避免重复显示
    const existingNotification = document.querySelector('.progress-notification');
    if (existingNotification) {
        return;
    }
    
    const notification = document.createElement('div');
    notification.className = 'progress-notification';
    notification.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        background: linear-gradient(135deg, #17a2b8, #138496);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(23, 162, 184, 0.3);
        z-index: 10002;
        font-size: 14px;
        font-weight: 600;
        backdrop-filter: blur(10px);
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
    `;
    notification.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 16px;">🎉</span>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // 自动移除通知
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, 6000);
}

// 添加CSS动画样式
const progressStyle = document.createElement('style');
progressStyle.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
    
    .status-generating {
        background: #ffc107 !important;
        color: #212529 !important;
    }
    
    .status-normal {
        background: #17a2b8 !important;
        color: white !important;
    }
    
    .status-completed {
        background: #28a745 !important;
        color: white !important;
    }
    
    .status-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
        display: inline-block;
    }
`;
document.head.appendChild(progressStyle);

// 启动进度监控
startProgressMonitoring();

// 添加手动控制进度条的函数
function toggleProgressBar() {
    if (progressHidden) {
        showProgressBar();
        progressHidden = false;
        console.log('📊 进度条已显示');
    } else {
        hideProgressBar();
        progressHidden = true;
        console.log('📖 进度条已隐藏');
    }
}

// 添加全局快捷键支持 (Ctrl+P 切换进度条)
document.addEventListener('keydown', (event) => {
    // 防止在输入框中触发
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (event.ctrlKey && event.key === 'p') {
        event.preventDefault();
        toggleProgressBar();
    }
});

// 页面卸载时清理定时器
window.addEventListener('beforeunload', () => {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
});

// 将控制函数暴露到全局作用域，方便调试
window.toggleProgress = toggleProgressBar;
window.showProgress = showProgressBar;
window.hideProgress = hideProgressBar;

// ==================== 原始数据显示功能 ====================

/**
 * 显示模态窗口
 */
function showModal(title, content) {
    // 创建模态背景
    const modalOverlay = document.createElement('div');
    modalOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
    `;

    // 创建模态内容
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        border-radius: 8px;
        max-width: 800px;
        max-height: 80vh;
        width: 90%;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;

    modalContent.innerHTML = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; font-size: 16px;">${title}</h3>
            <button onclick="closeModal(this)" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">×</button>
        </div>
        <div style="padding: 20px; overflow-y: auto; max-height: calc(80vh - 60px);">
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.4; margin: 0;">${escapeHtml(content)}</pre>
        </div>
        <div style="padding: 15px 20px; border-top: 1px solid #eee; text-align: right;">
            <button onclick="closeModal(this)" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">关闭</button>
        </div>
    `;

    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);

    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            document.body.removeChild(modalOverlay);
        }
    });
}

/**
 * 关闭模态窗口
 */
function closeModal(button) {
    const modal = button.closest('div[style*="position: fixed"], div[style*="position:fixed"]');
    if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal);
    }
}

/**
 * 显示原始章节JSON数据
 */
async function showOriginalChapterData(chapterTitle, filePath) {
    try {
        const response = await fetch(`/api/raw-chapter-data?file_path=${encodeURIComponent(filePath)}`);
        if (!response.ok) throw new Error('获取章节数据失败');

        const data = await response.json();
        const content = JSON.stringify(data, null, 2);

        showModal(`📄 原始章节数据 - ${decodeURIComponent(chapterTitle)}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `获取章节数据失败: ${error.message}`);
    }
}

/**
 * 显示写作计划数据
 */
function showWritingPlan(stageName, planData) {
    try {
        const plan = JSON.parse(decodeURIComponent(planData));
        const content = JSON.stringify(plan, null, 2);

        showModal(`📋 写作计划 - ${stageName}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `解析写作计划数据失败: ${error.message}`);
    }
}

/**
 * 显示事件记录
 */
function showEventLog(title, eventData) {
    try {
        const events = JSON.parse(decodeURIComponent(eventData));
        const content = Array.isArray(events) ?
            JSON.stringify(events, null, 2) :
            JSON.stringify([events], null, 2);

        showModal(`📅 ${title}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `解析事件记录失败: ${error.message}`);
    }
}

/**
 * 显示AI生成输出详情
 */
function showAIGenerationOutput(chapter) {
    const content = {
        chapter_number: chapter.chapter_number,
        title: chapter.title,
        content: chapter.content,
        word_count: chapter.content ? chapter.content.length : 0,
        generated_at: chapter.generated_at,
        file_path: chapter.file_path
    };

    const contentStr = JSON.stringify(content, null, 2);
    showModal(`🤖 AI生成输出 - 第${chapter.chapter_number}章`, contentStr);
}

/**
 * 显示质量评价详情
 */
function showQualityAssessment(qualityData) {
    const content = JSON.stringify(qualityData, null, 2);
    showModal(`📊 质量评价详情`, content);
}

/**
 * 显示角色发展数据
 */
function showCharacterDevelopment(characterData) {
    const content = JSON.stringify(characterData, null, 2);
    showModal(`👥 角色发展详情`, content);
}

// ==================== 可展开JSON组件功能 ====================

/**
 * 创建可展开的JSON组件
 */
function createExpandableJSON(title, data, options = {}) {
    const {
        id = null,
        icon = '📄',
        expanded = false,
        maxHeight = 600, // 增加默认高度
        syntaxHighlight = true,
        enableLargeModal = true // 添加大弹窗选项
    } = options;

    const componentId = id || `json-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 格式化JSON内容
    let formattedContent = '';
    let rawContent = '';
    if (data === null || data === undefined) {
        formattedContent = 'null';
        rawContent = 'null';
    } else if (typeof data === 'string') {
        try {
            // 尝试解析为JSON
            const parsed = JSON.parse(data);
            formattedContent = JSON.stringify(parsed, null, 2);
            rawContent = formattedContent;
        } catch (e) {
            // 如果不是JSON，直接显示字符串
            formattedContent = data;
            rawContent = data;
        }
    } else {
        formattedContent = JSON.stringify(data, null, 2);
        rawContent = formattedContent;
    }

    // 应用语法高亮
    if (syntaxHighlight) {
        formattedContent = highlightJSON(formattedContent);
    }

    // 创建大窗口查看按钮（如果启用大弹窗）
    const expandButton = enableLargeModal ? `
        <button class="btn-expand-large" data-title="${escapeHtml(title)}" data-content="${rawContent.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/`/g, '&#96;')}" title="在大弹窗中查看">
            🔍 大窗口查看
        </button>
    ` : '';

    return `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${expandButton}
                </div>
            </div>
        </div>
    `;
}


/**
 * JSON语法高亮
 */
function highlightJSON(jsonString) {
    return jsonString
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"(.*?)"\s*:/g, '<span class="json-key">"$1"</span>:')
        .replace(/:\s*"([^"]*)"/g, ': <span class="json-string">"$1"</span>')
        .replace(/:\s*(\d+)/g, ': <span class="json-number">$1</span>')
        .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
        .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
}

/**
 * 异步加载并创建可展开的JSON组件
 */
async function createAsyncExpandableJSON(title, loadFunction, options = {}) {
    const {
        id = null,
        icon = '📄',
        expanded = false,
        maxHeight = 400,
        errorMessage = '加载数据失败',
        loadingText = '正在加载数据...'
    } = options;

    const componentId = id || `json-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 初始显示加载状态（移除展开功能，只显示加载状态）
    let component = `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
            </div>
            <div class="json-content" style="max-height: 0; overflow: hidden;">
                <div class="json-loading">${loadingText}</div>
            </div>
        </div>
    `;

    // 异步加载数据
    try {
        const data = await loadFunction();
        let content = '';
        
        if (data === null || data === undefined) {
            content = '<div class="json-empty">暂无数据</div>';
        } else {
            let formattedContent = '';
            if (typeof data === 'string') {
                try {
                    const parsed = JSON.parse(data);
                    formattedContent = JSON.stringify(parsed, null, 2);
                } catch (e) {
                    formattedContent = data;
                }
            } else {
                formattedContent = JSON.stringify(data, null, 2);
            }
            content = `<div class="json-body">${highlightJSON(formattedContent)}</div>`;
        }

        // 更新组件内容（自动显示，不需要点击展开）
        setTimeout(() => {
            const section = document.getElementById(componentId);
            if (section) {
                const contentDiv = section.querySelector('.json-content');
                if (contentDiv) {
                    contentDiv.innerHTML = content;
                    // 自动显示内容
                    contentDiv.style.maxHeight = contentDiv.scrollHeight + 'px';
                }
            }
        }, 100);

    } catch (error) {
        console.error('加载JSON数据失败:', error);
        setTimeout(() => {
            const section = document.getElementById(componentId);
            if (section) {
                const contentDiv = section.querySelector('.json-content');
                if (contentDiv) {
                    contentDiv.innerHTML = `<div class="json-error">${errorMessage}: ${error.message}</div>`;
                    // 自动显示错误信息
                    contentDiv.style.maxHeight = contentDiv.scrollHeight + 'px';
                }
            }
        }, 100);
    }

    return component;
}

/**
 * 创建多个可展开的JSON组件
 */
function createMultipleExpandableJSON(sections) {
    return sections.map(section => {
        if (section.async && section.loadData) {
            return createAsyncExpandableJSON(section.title, section.loadData, section.options);
        } else {
            return createExpandableJSON(section.title, section.data, section.options);
        }
    }).join('');
}


// ==================== 大弹窗功能 ====================

/**
 * 显示大JSON弹窗 - 全屏新界面
 */
function showLargeJSONModal(title, content) {
    console.log('显示大弹窗:', title, content?.substring(0, 100) + '...');
    
    try {
        // 先关闭已存在的弹窗
        closeLargeJSONModal();
        
        // 创建全屏模态背景
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay fullscreen-modal';
        modalOverlay.id = 'large-json-modal';
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(10px);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.3s ease-out;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        `;

        // 创建全屏模态内容
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-large fullscreen-modal-content';
        modalContent.style.cssText = `
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            width: 100%;
            height: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: none;
            animation: slideUp 0.3s ease-out;
            position: relative;
        `;

        // 格式化JSON内容
        let formattedContent = content;
        try {
            const parsed = JSON.parse(content);
            formattedContent = JSON.stringify(parsed, null, 2);
        } catch (e) {
            console.log('内容不是JSON格式，保持原样');
            // 如果不是JSON，保持原样
        }

        // 应用语法高亮
        const highlightedContent = highlightJSON(formattedContent);

        // 创建唯一的按钮ID
        const copyBtnId = 'copy-btn-' + Date.now();
        const downloadBtnId = 'download-btn-' + Date.now() + '-1';

        // 安全地转义内容用于HTML属性
        const safeTitle = escapeHtml(title);

        modalContent.innerHTML = `
            <div class="fullscreen-modal-header" style="background: linear-gradient(135deg, #00d4ff 0%, #0099cc 50%, #006699 100%); color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.2); flex-shrink: 0; height: 60px;">
                <div style="display: flex; align-items: center; gap: 16px; flex: 1;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 12px;">${safeTitle}</h3>
                    <div style="display: flex; gap: 8px; margin-left: auto;">
                        <button class="btn btn-secondary btn-small fullscreen-action-btn" id="${copyBtnId}" style="background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s ease; backdrop-filter: blur(10px);">
                            📋 复制内容
                        </button>
                        <button class="btn btn-secondary btn-small fullscreen-action-btn" id="${downloadBtnId}" style="background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s ease; backdrop-filter: blur(10px);">
                            💾 下载文件
                        </button>
                    </div>
                </div>
                <button class="modal-close-btn fullscreen-close-btn" style="background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; font-size: 20px; cursor: pointer; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 8px; transition: all 0.15s ease; backdrop-filter: blur(10px); margin-left: 16px;">×</button>
            </div>
            <div class="fullscreen-modal-body" style="flex: 1; padding: 0; overflow: hidden; background: #f9fafb; display: flex; flex-direction: column;">
                <div class="fullscreen-content-container" style="flex: 1; padding: 24px; overflow-y: auto; background: #f9fafb;">
                    <div style="background: white; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); height: 100%; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #dbeafe;">
                            <div style="font-size: 20px; font-weight: 700; color: #1d4ed8; display: flex; align-items: center; gap: 12px;">
                                <span>📄</span>
                                <span>JSON 数据内容</span>
                                <span style="font-size: 14px; color: #6b7280; font-weight: 400;">(${content.length} 字符)</span>
                            </div>
                        </div>
                        <div class="fullscreen-json-display" style="flex: 1; background: #f8f9fa; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; overflow-y: auto; min-height: 400px;">${highlightedContent}</div>
                    </div>
                </div>
            </div>
        `;

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        console.log('弹窗已添加到DOM');

        // 使用事件委托而不是内联onclick，避免转义问题
        const copyBtn = modalContent.querySelector(`#${copyBtnId}`);
        const downloadBtn = modalContent.querySelector(`#${downloadBtnId}`);
        const closeBtn = modalContent.querySelector('.modal-close-btn');

        if (copyBtn) {
            copyBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                copyJSONContent(formattedContent);
            });
        }
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                downloadJSONContent(title, formattedContent);
            });
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeLargeJSONModal();
            });
        }

        // 点击背景关闭
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeLargeJSONModal();
            }
        });

        // ESC键关闭
        const handleEscape = (e) => {
            if (e.key === 'Escape') {
                closeLargeJSONModal();
                document.removeEventListener('keydown', handleEscape);
            }
        };
        document.addEventListener('keydown', handleEscape);
        
        console.log('弹窗显示完成');
    } catch (error) {
        console.error('显示大弹窗时发生错误:', error);
        showNotification('❌ 显示大弹窗失败: ' + error.message);
    }
}

/**
 * 关闭大JSON弹窗
 */
function closeLargeJSONModal() {
    const modal = document.getElementById('large-json-modal');
    if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal);
    }
}

/**
 * 复制JSON内容到剪贴板
 */
async function copyJSONContent(content) {
    try {
        console.log('尝试复制内容:', content?.substring(0, 100) + '...');
        
        // 解码转义的内容
        let decodedContent = content;
        if (typeof content === 'string') {
            decodedContent = content
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\')
                .replace(/\\n/g, '\n');
        }
        
        console.log('解码后的内容长度:', decodedContent?.length);
        
        await navigator.clipboard.writeText(decodedContent);
        showNotification('✅ 内容已复制到剪贴板');
    } catch (error) {
        console.error('复制失败:', error);
        showNotification('❌ 复制失败，请手动选择复制');
    }
}

/**
 * 下载JSON内容为文件
 */
function downloadJSONContent(title, content) {
    try {
        console.log('尝试下载文件:', title, content?.substring(0, 100) + '...');
        
        // 解码转义的内容
        let decodedContent = content;
        let decodedTitle = title;
        
        if (typeof content === 'string') {
            decodedContent = content
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\')
                .replace(/\\n/g, '\n');
        }
        
        if (typeof title === 'string') {
            decodedTitle = title
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\');
        }
        
        console.log('解码后的内容长度:', decodedContent?.length);
        
        const blob = new Blob([decodedContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${decodedTitle.replace(/[^\w\u4e00-\u9fa5]/g, '_')}_${new Date().getTime()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showNotification('✅ 文件下载成功');
    } catch (error) {
        console.error('下载失败:', error);
        showNotification('❌ 下载失败，请重试');
    }
}

/**
 * 显示通知消息
 */
function showNotification(message, duration = 3000) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0, 212, 255, 0.9);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10001;
        font-size: 14px;
        font-weight: 600;
        backdrop-filter: blur(10px);
        animation: slideInRight 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // 自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, duration);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);


// ==================== 阅读模式功能 ====================

/**
 * 切换阅读模式（新版UI：打开调试抽屉）
 */
function toggleReadingMode() {
    // 新版UI使用抽屉而非切换布局
    openDebugDrawer();
}

/**
 * 初始化阅读模式
 */
function initReadingMode() {
    // 更新阅读模式标题
    const readingTitle = document.getElementById('reading-title');
    if (readingTitle && novelData) {
        readingTitle.textContent = novelData.novel_title || currentNovelTitle || '小说标题';
    }
    
    // 生成章节菜单
    generateChapterMenu();
    
    // 应用当前阅读设置
    applyReadingSettings();
    
    // 如果有当前章节，更新阅读内容
    if (currentChapter && chaptersData.length > 0) {
        updateReadingContent();
    }
}

/**
 * 生成章节菜单
 */
function generateChapterMenu() {
    const menuContent = document.getElementById('chapter-menu-content');
    if (!menuContent || chaptersData.length === 0) return;
    
    const menuHtml = chaptersData.map(chapter => `
        <div class="chapter-menu-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
             onclick="loadChapterFromMenu(${chapter.chapter_number})">
            <div class="chapter-menu-item-title">
                第${chapter.chapter_number}章 ${chapter.title}
            </div>
            <div class="chapter-menu-item-meta">
                ${chapter.word_count || 0} 字
            </div>
        </div>
    `).join('');
    
    menuContent.innerHTML = menuHtml;
}

/**
 * 从章节菜单加载章节
 */
function loadChapterFromMenu(chapterNum) {
    if (chapterNum !== currentChapter) {
        loadChapter(currentNovelTitle, chapterNum);
        hideChapterMenu();
        // 在阅读模式下，切换章节后滚动到开头
        if (isReadingMode) {
            setTimeout(() => {
                scrollToReadingContentTop();
            }, 100);
        }
    }
}

/**
 * 显示章节菜单
 */
function showChapterMenu() {
    const chapterMenu = document.getElementById('chapter-menu');
    if (chapterMenu) {
        chapterMenu.classList.add('show');
    }
}

/**
 * 隐藏章节菜单
 */
function hideChapterMenu() {
    const chapterMenu = document.getElementById('chapter-menu');
    if (chapterMenu) {
        chapterMenu.classList.remove('show');
    }
}

/**
 * 更新阅读内容
 */
function updateReadingContent() {
    const currentChapterData = chaptersData.find(c => c.chapter_number === currentChapter);
    if (!currentChapterData) return;
    
    // 更新章节标题
    const readingChapterTitle = document.getElementById('reading-chapter-title');
    const readingChapterMeta = document.getElementById('reading-chapter-meta');
    const readingChapterIndicator = document.getElementById('reading-chapter-indicator');
    const readingNavIndicator = document.getElementById('reading-nav-indicator');
    
    if (readingChapterTitle) {
        readingChapterTitle.textContent = currentChapterData.title || `第${currentChapter}章`;
    }
    
    if (readingChapterMeta) {
        const wordCount = currentChapterData.content ? currentChapterData.content.length : 0;
        const generatedTime = currentChapterData.generated_at
            ? new Date(currentChapterData.generated_at).toLocaleString('zh-CN')
            : '未知';
        readingChapterMeta.textContent = `${wordCount} 字 • 生成时间: ${generatedTime}`;
    }
    
    if (readingChapterIndicator) {
        readingChapterIndicator.textContent = `第 ${currentChapter} 章`;
    }
    
    if (readingNavIndicator) {
        readingNavIndicator.textContent = `第 ${currentChapter} 章`;
    }
    
    // 保存章节内容到全局变量，供分页系统使用
    if (currentChapterData.content) {
        currentChapterContent = currentChapterData.content;
        console.log('阅读模式：设置章节内容供分页使用，字数:', currentChapterData.content.length);
    }
    
    // 更新章节内容
    const readingText = document.getElementById('reading-text');
    if (readingText && currentChapterData.content) {
        // 阅读模式下始终禁用分页，直接显示完整内容
        // 使用相同的后处理逻辑
        let html = currentChapterData.content;
        
        // 确保换行符统一
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        
        // 处理分隔线
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        
        // 处理特殊标记
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        // 处理段落
        let paragraphs = html.split(/\n\s*\n/);
        let result = '';
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (paragraph) {
                paragraph = paragraph.replace(/\n/g, '<br>');
                result += `<p>${paragraph}</p>`;
            }
        }
        
        readingText.innerHTML = result;
        
        // 确保阅读模式下隐藏分页导航
        hidePaginationNavigation();
    }
    
    // 更新章节菜单的活跃状态
    updateChapterMenuActiveState();
    
    // 更新导航按钮状态
    updateReadingNavigationButtons();
}

/**
 * 更新章节菜单活跃状态
 */
function updateChapterMenuActiveState() {
    const menuItems = document.querySelectorAll('.chapter-menu-item');
    menuItems.forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = document.querySelector(`.chapter-menu-item[onclick*="${currentChapter}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

/**
 * 更新阅读模式导航按钮状态
 */
function updateReadingNavigationButtons() {
    const hasPrev = chaptersData.some(c => c.chapter_number < currentChapter);
    const hasNext = chaptersData.some(c => c.chapter_number > currentChapter);
    
    const navButtons = document.querySelectorAll('.reading-nav-btn');
    navButtons.forEach(btn => {
        if (btn.textContent.includes('上一章')) {
            btn.disabled = !hasPrev;
        } else if (btn.textContent.includes('下一章')) {
            btn.disabled = !hasNext;
        }
    });
}

/**
 * 切换阅读设置面板
 */
function toggleReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel.style.display === 'none') {
        showReadingSettings();
    } else {
        hideReadingSettings();
    }
}

/**
 * 显示阅读设置面板
 */
function showReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel) {
        settingsPanel.style.display = 'block';
        updateSettingsDisplay();
    }
}

/**
 * 隐藏阅读设置面板
 */
function hideReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel) {
        settingsPanel.style.display = 'none';
    }
}

/**
 * 更新设置显示
 */
function updateSettingsDisplay() {
    const fontSizeDisplay = document.getElementById('font-size-display');
    const lineHeightDisplay = document.getElementById('line-height-display');
    
    if (fontSizeDisplay) {
        fontSizeDisplay.textContent = currentFontSize + 'px';
    }
    
    if (lineHeightDisplay) {
        lineHeightDisplay.textContent = currentLineHeight.toFixed(1);
    }
    
    // 更新主题按钮状态
    const themeButtons = document.querySelectorAll('.theme-btn');
    themeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.theme === currentTheme) {
            btn.classList.add('active');
        }
    });
}

/**
 * 调整字体大小
 */
function adjustFontSize(delta) {
    currentFontSize = Math.max(12, Math.min(24, currentFontSize + delta));
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 调整行间距
 */
function adjustLineHeight(delta) {
    currentLineHeight = Math.max(1.2, Math.min(2.5, currentLineHeight + delta));
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 设置阅读主题
 */
function setReadingTheme(theme) {
    currentTheme = theme;
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 应用阅读设置
 */
function applyReadingSettings() {
    const readingText = document.getElementById('reading-text');
    if (!readingText) return;
    
    // 移除所有主题类
    readingText.classList.remove('theme-light', 'theme-sepia', 'theme-dark');
    
    // 应用当前主题
    readingText.classList.add(`theme-${currentTheme}`);
    
    // 应用字体大小和行间距
    readingText.style.fontSize = currentFontSize + 'px';
    readingText.style.lineHeight = currentLineHeight;
}

/**
 * 重写loadChapter函数，支持阅读模式更新
 */
const originalLoadChapter = loadChapter;
loadChapter = async function(novelTitle, chapterNum) {
    try {
        // 调用原始函数
        await originalLoadChapter(novelTitle, chapterNum);
        
        // 如果在阅读模式，更新阅读内容并滚动到开头
        if (isReadingMode) {
            updateReadingContent();
            // 延迟滚动，确保内容更新完成
            setTimeout(() => {
                scrollToReadingContentTop();
            }, 200);
        }
    } catch (error) {
        console.error('加载章节失败:', error);
        showError('加载章节失败');
    }
};

/**
 * 重写updateNavigationButtons函数，支持阅读模式
 */
const originalUpdateNavigationButtons = updateNavigationButtons;
updateNavigationButtons = function() {
    // 调用原始函数
    originalUpdateNavigationButtons();
    
    // 如果在阅读模式，也更新阅读模式的导航按钮
    if (isReadingMode) {
        updateReadingNavigationButtons();
    }
};

// 点击页面其他地方隐藏设置面板
document.addEventListener('click', function(event) {
    const settingsPanel = document.getElementById('reading-settings-panel');
    const settingsBtn = document.getElementById('reading-settings-btn');
    
    if (settingsPanel &&
        settingsPanel.style.display !== 'none' &&
        !settingsPanel.contains(event.target) &&
        !settingsBtn.contains(event.target)) {
        hideReadingSettings();
    }
});

// ESC键隐藏菜单和设置面板
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        hideChapterMenu();
        hideReadingSettings();
        // 同时关闭大弹窗
        if (window.closeLargeJSONModal) {
            window.closeLargeJSONModal();
        }
    }
});

// 确保函数在页面加载完成后可用
document.addEventListener('DOMContentLoaded', function() {
    // 将函数绑定到全局作用域
    window.showLargeJSONModal = showLargeJSONModal;
    window.closeLargeJSONModal = closeLargeJSONModal;
    
    console.log('弹窗函数初始化完成');
    console.log('showLargeJSONModal 可用性:', typeof window.showLargeJSONModal);
    console.log('closeLargeJSONModal 可用性:', typeof window.closeLargeJSONModal);
    
    // 添加事件委托处理大窗口查看按钮
    document.body.addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-expand-large') || event.target.closest('.btn-expand-large')) {
            const button = event.target.classList.contains('btn-expand-large') ? event.target : event.target.closest('.btn-expand-large');
            
            // 从data属性获取标题和内容
            const title = button.getAttribute('data-title') || '数据查看';
            let content = button.getAttribute('data-content') || '{}';
            
            // 解码HTML实体
            content = content
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&#96;/g, '`')
                .replace(/&amp;/g, '&');
            
            console.log('点击大窗口查看按钮:', title, content.substring(0, 100) + '...');
            
            // 调用弹窗函数
            if (window.showLargeJSONModal) {
                window.showLargeJSONModal(title, content);
            } else {
                console.error('showLargeJSONModal 函数不可用');
                alert('弹窗功能暂时不可用，请刷新页面重试');
            }
            
            event.preventDefault();
            event.stopPropagation();
        }
    });
    
    // 添加全局调试函数
    window.testModal = function() {
        console.log('测试弹窗功能...');
        if (window.showLargeJSONModal) {
            window.showLargeJSONModal('测试弹窗', JSON.stringify({
                test: true,
                message: '这是一个测试弹窗',
                timestamp: new Date().toISOString()
            }, null, 2));
        } else {
            console.error('showLargeJSONModal 函数不可用');
        }
    };
    
    console.log('测试函数已添加: window.testModal()');
});

// ==================== 分页系统功能 ====================

/**
 * 初始化分页系统
 */
function initializePagination() {
    // 从本地存储加载分页设置
    loadPaginationSettings();
    
    // 应用分页设置
    applyPaginationSettings();
    
    console.log('分页系统已初始化');
}

/**
 * 加载分页设置
 */
function loadPaginationSettings() {
    try {
        const settings = localStorage.getItem('novel-pagination-settings');
        if (settings) {
            const parsed = JSON.parse(settings);
            paginationEnabled = parsed.paginationEnabled !== false;
            pageSizeLines = parsed.pageSizeLines || 25;
            pageMode = parsed.pageMode || 'line';
        }
    } catch (error) {
        console.warn('加载分页设置失败:', error);
    }
}

/**
 * 保存分页设置
 */
function savePaginationSettings() {
    try {
        const settings = {
            paginationEnabled,
            pageSizeLines,
            pageMode
        };
        localStorage.setItem('novel-pagination-settings', JSON.stringify(settings));
    } catch (error) {
        console.warn('保存分页设置失败:', error);
    }
}

/**
 * 应用分页设置
 */
function applyPaginationSettings() {
    // 更新设置面板显示
    updatePaginationSettingsDisplay();
    
    // 应用分页模式
    applyPaginationMode();
}

/**
 * 更新分页设置显示
 */
function updatePaginationSettingsDisplay() {
    // 更新每页行数显示
    const pageSizeDisplay = document.getElementById('page-size-display');
    if (pageSizeDisplay) {
        pageSizeDisplay.textContent = `${pageSizeLines}行`;
    }
    
    // 更新自动分页开关
    const autoPageToggle = document.getElementById('auto-page-toggle');
    if (autoPageToggle) {
        autoPageToggle.checked = paginationEnabled;
    }
    
    // 更新分页模式按钮
    const pageModeButtons = document.querySelectorAll('.page-mode-btn');
    pageModeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.mode === pageMode) {
            btn.classList.add('active');
        }
    });
}

/**
 * 应用分页模式
 */
function applyPaginationMode() {
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    // 阅读模式下始终禁用分页
    if (isReadingMode) {
        paginationEnabled = false;
        if (contentBody) contentBody.classList.remove('paged');
        if (readingText) readingText.classList.remove('paged');
        hidePaginationNavigation();
        
        // 恢复完整内容显示
        if (currentChapterContent) {
            displayFullContent(currentChapterContent);
        }
        return;
    }
    
    if (paginationEnabled) {
        // 启用分页模式（仅在调试模式下）
        if (contentBody) contentBody.classList.add('paged');
        if (readingText) readingText.classList.add('paged');
        
        // 显示分页导航
        showPaginationNavigation();
        
        // 如果有章节内容，重新分页
        if (currentChapterContent) {
            paginateChapterContent(currentChapterContent);
        }
    } else {
        // 禁用分页模式
        if (contentBody) contentBody.classList.remove('paged');
        if (readingText) readingText.classList.remove('paged');
        
        // 隐藏分页导航
        hidePaginationNavigation();
        
        // 恢复完整内容显示
        if (currentChapterContent) {
            displayFullContent(currentChapterContent);
        }
    }
}

/**
 * 章节内容分页
 */
function paginateChapterContent(content) {
    if (!paginationEnabled) {
        displayFullContent(content);
        return;
    }
    
    currentChapterContent = content;
    
    if (pageMode === 'line') {
        paginateByLines(content);
    } else {
        paginateByHeight(content);
    }
    
    // 显示第一页
    currentPage = 1;
    displayCurrentPage();
    
    // 更新分页导航
    updatePaginationNavigation();
}

/**
 * 按行数分页 - 优化版本，减少页数
 */
function paginateByLines(content) {
    // 将内容按段落分割
    const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
    const totalParagraphs = paragraphs.length;
    
    if (totalParagraphs === 0) {
        chapterPages = [''];
        totalPages = 1;
        return;
    }
    
    // 计算合适的页数目标
    // 考虑到加大的两倍高度，可以容纳更多内容
    let targetPageCount = Math.max(3, Math.min(6, Math.ceil(totalParagraphs / 18)));
    let adjustedPageSizeLines = Math.ceil(totalParagraphs * 2.5 / targetPageCount); // 增加每页行数以适应更大的高度
    
    console.log(`按行数分页策略: 总段落数${totalParagraphs}, 目标页数${targetPageCount}, 调整后每页${adjustedPageSizeLines}行`);
    
    const pages = [];
    let currentPageLines = [];
    let currentLineCount = 0;
    
    for (const paragraph of paragraphs) {
        const lines = paragraph.split('\n').filter(line => line.trim());
        
        // 如果当前段落加上后不会超过页面限制
        if (currentLineCount + lines.length <= adjustedPageSizeLines) {
            currentPageLines.push(...lines);
            currentLineCount += lines.length;
        } else {
            // 保存当前页面
            if (currentPageLines.length > 0) {
                pages.push(currentPageLines.join('\n'));
            }
            
            // 开始新页面
            currentPageLines = [...lines];
            currentLineCount = lines.length;
            
            // 如果单个段落就超过页面限制，强制分页
            if (currentLineCount > adjustedPageSizeLines) {
                const remainingLines = currentPageLines.splice(adjustedPageSizeLines);
                pages.push(currentPageLines.join('\n'));
                currentPageLines = remainingLines;
                currentLineCount = remainingLines.length;
            }
        }
    }
    
    // 添加最后一页
    if (currentPageLines.length > 0) {
        pages.push(currentPageLines.join('\n'));
    }
    
    // 如果页数仍然太多，进一步合并
    if (pages.length > 8) {
        console.log(`按行数分页页数过多(${pages.length}页)，重新合并为更少的页数`);
        const mergedPages = [];
        const targetMergePageCount = Math.max(3, Math.min(6, Math.ceil(pages.length / 2)));
        const pagesPerMerge = Math.ceil(pages.length / targetMergePageCount);
        
        for (let i = 0; i < pages.length; i += pagesPerMerge) {
            const mergedContent = pages.slice(i, i + pagesPerMerge).join('\n\n');
            mergedPages.push(mergedContent);
        }
        
        chapterPages = mergedPages;
        totalPages = mergedPages.length;
    } else {
        chapterPages = pages;
        totalPages = pages.length;
    }
    
    console.log(`按行数分页完成: ${totalPages}页, 总段落数: ${totalParagraphs}, 平均每页${Math.round(totalParagraphs/totalPages)}个段落`);
}

/**
 * 按高度分页 - 优化版本，减少页数
 */
function paginateByHeight(content) {
    // 获取容器尺寸和目标高度
    const contentContainer = document.getElementById('chapter-content') || document.getElementById('reading-text');
    if (!contentContainer) {
        console.warn('无法找到内容容器，回退到按行数分页');
        paginateByLines(content);
        return;
    }
    
    const containerWidth = contentContainer.clientWidth || 800;
    const targetHeight = 1100; // 使用加大两倍的高度，确保每页有足够内容
    
    console.log(`按高度分页: 容器宽度${containerWidth}px, 目标高度${targetHeight}px`);
    
    // 处理内容为段落
    const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
    const totalParagraphs = paragraphs.length;
    
    if (totalParagraphs === 0) {
        chapterPages = [''];
        totalPages = 1;
        return;
    }
    
    // 计算每页应该包含的段落数，确保合适的页数
    // 目标是分成3-5页，而不是16页，但考虑到加大的高度，可以容纳更多内容
    let targetPageCount = Math.max(3, Math.min(5, Math.ceil(totalParagraphs / 20))); // 增加每页段落数
    let paragraphsPerPage = Math.ceil(totalParagraphs / targetPageCount);
    
    console.log(`分页策略: 总段落数${totalParagraphs}, 目标页数${targetPageCount}, 每页${paragraphsPerPage}个段落`);
    
    // 创建临时元素来测量高度
    const tempDiv = document.createElement('div');
    tempDiv.style.cssText = `
        position: absolute;
        top: -9999px;
        left: -9999px;
        width: ${containerWidth}px;
        height: ${targetHeight}px;
        font-size: ${isReadingMode ? currentFontSize + 'px' : '16px'};
        line-height: ${currentLineHeight};
        padding: 20px;
        visibility: hidden;
        box-sizing: border-box;
        overflow: hidden;
        font-family: ${isReadingMode ? 'serif' : 'sans-serif'};
        white-space: pre-wrap;
        word-wrap: break-word;
    `;
    
    document.body.appendChild(tempDiv);
    
    // 将内容处理成HTML格式进行测量
    const processContentForMeasurement = (text) => {
        return text
            .replace(/\r\n/g, '\n').replace(/\r/g, '\n')
            .replace(/[═]{10,}/g, '<hr class="novel-hr">')
            .replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>')
            .replace(/\n\s*\n/g, '</p><p style="margin-bottom: 1em;">')
            .replace(/\n/g, '<br>');
    };
    
    const pages = [];
    let currentContent = '';
    
    // 逐段添加内容，优先按段落数分页，然后检查高度
    for (let i = 0; i < paragraphs.length; i++) {
        const paragraph = paragraphs[i];
        const testContent = currentContent + (currentContent ? '\n\n' : '') + paragraph;
        
        // 处理内容为HTML格式进行测量
        const htmlContent = `<div style="padding: 20px; font-family: sans-serif; line-height: 1.8;">${processContentForMeasurement(testContent)}</div>`;
        tempDiv.innerHTML = htmlContent;
        
        // 检查是否超出目标高度或段落数限制
        const currentParagraphCount = currentContent ? currentContent.split('\n\n').length : 0;
        const testParagraphCount = testContent.split('\n\n').length;
        
        if ((tempDiv.scrollHeight > targetHeight && currentContent) || testParagraphCount > paragraphsPerPage) {
            // 保存当前页面
            if (currentContent.trim()) {
                pages.push(currentContent.trim());
            }
            currentContent = paragraph;
        } else {
            currentContent = testContent;
        }
    }
    
    // 添加最后一页
    if (currentContent.trim()) {
        pages.push(currentContent.trim());
    }
    
    // 清理临时元素
    document.body.removeChild(tempDiv);
    
    // 如果页数仍然太多，进一步合并页面
    if (pages.length > 8) {
        console.log(`页数过多(${pages.length}页)，重新分页为更少的页数`);
        const mergedPages = [];
        const targetMergePageCount = Math.max(3, Math.min(6, Math.ceil(pages.length / 3)));
        const pagesPerMerge = Math.ceil(pages.length / targetMergePageCount);
        
        for (let i = 0; i < pages.length; i += pagesPerMerge) {
            const mergedContent = pages.slice(i, i + pagesPerMerge).join('\n\n');
            mergedPages.push(mergedContent);
        }
        
        chapterPages = mergedPages;
        totalPages = mergedPages.length;
    } else {
        chapterPages = pages;
        totalPages = pages.length;
    }
    
    console.log(`按高度分页完成: ${totalPages}页, 总段落数: ${totalParagraphs}, 平均每页${Math.round(totalParagraphs/totalPages)}个段落`);
}

/**
 * 显示完整内容（非分页模式）
 */
function displayFullContent(content) {
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    if (contentBody && isReadingMode === false) {
        // 调试模式
        contentBody.innerHTML = `<div class="novel-content-raw">${escapeHtml(content)}</div>`;
        postProcessContent(contentBody);
    }
    
    if (readingText && isReadingMode === true) {
        // 阅读模式
        let html = content;
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        const paragraphs = html.split(/\n\s*\n/);
        let result = '';
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (paragraph) {
                paragraph = paragraph.replace(/\n/g, '<br>');
                result += `<p>${paragraph}</p>`;
            }
        }
        
        readingText.innerHTML = result;
    }
}

/**
 * 显示当前页
 */
function displayCurrentPage() {
    if (!paginationEnabled || chapterPages.length === 0) return;
    
    const pageContent = chapterPages[currentPage - 1];
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    if (contentBody && isReadingMode === false) {
        // 调试模式
        contentBody.innerHTML = `
            <div class="page-content">
                <div class="page-progress">
                    <div class="page-progress-bar" style="width: ${(currentPage / totalPages) * 100}%"></div>
                </div>
                <div class="page-content-inner">
                    <div class="novel-content-raw" style="min-height: 100%;">${escapeHtml(pageContent)}</div>
                </div>
            </div>
        `;
        // 后处理内容
        setTimeout(() => {
            postProcessContent(contentBody);
        }, 50);
    }
    
    if (readingText && isReadingMode === true) {
        // 阅读模式
        let html = pageContent;
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        const paragraphs = html.split(/\n\s*\n/);
        let result = '';
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (paragraph) {
                paragraph = paragraph.replace(/\n/g, '<br>');
                result += `<p style="margin-bottom: 1em;">${paragraph}</p>`;
            }
        }
        
        readingText.innerHTML = `
            <div class="page-content">
                <div class="page-progress">
                    <div class="page-progress-bar" style="width: ${(currentPage / totalPages) * 100}%"></div>
                </div>
                <div class="page-content-inner" style="min-height: 100%;">${result}</div>
            </div>
        `;
    }
}

/**
 * 更新分页导航
 */
function updatePaginationNavigation() {
    // 更新调试模式分页导航
    updateDebugPaginationNavigation();
    
    // 更新阅读模式分页导航
    updateReadingPaginationNavigation();
}

/**
 * 更新调试模式分页导航
 */
function updateDebugPaginationNavigation() {
    const currentPageSpan = document.getElementById('current-page');
    const totalPagesSpan = document.getElementById('total-pages');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentPage <= 1;
    }
    
    if (nextPageBtn) {
        // 修改：最后一页时不禁用按钮，允许点击进入下一章
        // 如果没有下一章，nextPage 函数会显示提示
        const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
        nextPageBtn.disabled = (currentPage >= totalPages) && !nextChapterData;
    }
}

/**
 * 更新阅读模式分页导航
 */
function updateReadingPaginationNavigation() {
    const currentPageSpan = document.getElementById('reading-current-page');
    const totalPagesSpan = document.getElementById('reading-total-pages');
    const prevPageBtn = document.getElementById('reading-prev-page-btn');
    const nextPageBtn = document.getElementById('reading-next-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentPage <= 1;
    }
    
    if (nextPageBtn) {
        // 修改：最后一页时不禁用按钮，允许点击进入下一章
        // 如果没有下一章，nextPage 函数会显示提示
        const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
        nextPageBtn.disabled = (currentPage >= totalPages) && !nextChapterData;
    }
}

/**
 * 显示分页导航
 */
function showPaginationNavigation() {
    const pageNavigation = document.getElementById('page-navigation');
    const readingPageNavigation = document.getElementById('reading-page-navigation');
    
    // 阅读模式下不显示分页导航
    if (isReadingMode) {
        return;
    }
    
    if (pageNavigation) {
        pageNavigation.style.display = 'flex';
    }
    
    if (readingPageNavigation) {
        readingPageNavigation.style.display = 'flex';
    }
}

/**
 * 隐藏分页导航
 */
function hidePaginationNavigation() {
    const pageNavigation = document.getElementById('page-navigation');
    const readingPageNavigation = document.getElementById('reading-page-navigation');
    
    if (pageNavigation) {
        pageNavigation.style.display = 'none';
    }
    
    if (readingPageNavigation) {
        readingPageNavigation.style.display = 'none';
    }
}

/**
 * 上一页
 */
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayCurrentPage();
        updatePaginationNavigation();
        scrollToContentTop();
        showKeyboardHint('← 上一页');
    }
}

/**
 * 下一页
 */
function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        displayCurrentPage();
        updatePaginationNavigation();
        scrollToContentTop();
        showKeyboardHint('→ 下一页');
    } else if (currentPage >= totalPages) {
        // 当前章节最后一页，自动进入下一章
        const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
        if (nextChapterData) {
            showKeyboardHint('→ 下一章');
            loadChapter(currentNovelTitle, nextChapterData.chapter_number);
        } else {
            showNotification('已经是最后一章了', 'info');
        }
    }
}

/**
 * 滚动到内容顶部
 */
function scrollToContentTop() {
    if (isReadingMode) {
        // 阅读模式：滚动到阅读内容区域顶部
        const readingContent = document.getElementById('reading-content');
        if (readingContent) {
            readingContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } else {
        // 调试模式：滚动到正文内容区域顶部
        const centerContent = document.getElementById('center-content');
        if (centerContent) {
            centerContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

/**
 * 滚动到阅读内容顶部（阅读模式专用）
 */
function scrollToReadingContentTop() {
    console.log('执行阅读模式滚动到顶部');
    
    // 方法1: 立即设置滚动位置到顶部
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
    
    // 方法2: 强制滚动到页面最顶部
    setTimeout(() => {
        window.scrollTo({
            top: 0,
            left: 0,
            behavior: 'instant'  // 使用 instant 而不是 smooth，确保立即执行
        });
        
        // 方法3: 确保所有可能的滚动容器都在顶部
        const readingLayout = document.getElementById('reading-layout');
        if (readingLayout) {
            readingLayout.scrollTop = 0;
        }
        
        const readingContent = document.getElementById('reading-content');
        if (readingContent) {
            readingContent.scrollTop = 0;
        }
        
        const readingText = document.getElementById('reading-text');
        if (readingText) {
            readingText.scrollTop = 0;
            readingText.scrollIntoView({ behavior: 'instant', block: 'start' });
        }
        
        console.log('阅读模式滚动完成');
    }, 50);
    
    // 方法4: 再次确保在顶部（防止异步内容加载影响）
    setTimeout(() => {
        window.scrollTo(0, 0);
        document.documentElement.scrollTop = 0;
        document.body.scrollTop = 0;
    }, 200);
}

/**
 * 切换分页设置面板
 */
function togglePageSettings() {
    const settingsPanel = document.getElementById('page-settings-panel');
    if (settingsPanel.style.display === 'none') {
        settingsPanel.style.display = 'block';
    } else {
        settingsPanel.style.display = 'none';
    }
}

/**
 * 切换阅读模式分页设置
 */
function toggleReadingPageSettings() {
    // 这里可以添加阅读模式专用的分页设置
    togglePageSettings();
}

/**
 * 调整页面大小
 */
function adjustPageSize(delta) {
    pageSizeLines = Math.max(10, Math.min(50, pageSizeLines + delta));
    updatePaginationSettingsDisplay();
    savePaginationSettings();
    
    // 重新分页
    if (currentChapterContent) {
        paginateChapterContent(currentChapterContent);
    }
}

/**
 * 切换自动分页
 */
function toggleAutoPage() {
    const autoPageToggle = document.getElementById('auto-page-toggle');
    paginationEnabled = autoPageToggle.checked;
    savePaginationSettings();
    applyPaginationMode();
}

/**
 * 设置分页模式
 */
function setPageMode(mode) {
    pageMode = mode;
    updatePaginationSettingsDisplay();
    savePaginationSettings();
    
    // 重新分页
    if (currentChapterContent) {
        paginateChapterContent(currentChapterContent);
    }
}

/**
 * 显示键盘快捷键提示
 */
function showKeyboardHint(action) {
    // 移除现有提示
    const existingHint = document.querySelector('.keyboard-hint');
    if (existingHint) {
        existingHint.remove();
    }
    
    // 创建新提示
    const hint = document.createElement('div');
    hint.className = 'keyboard-hint';
    hint.textContent = action;
    document.body.appendChild(hint);
    
    // 显示提示
    setTimeout(() => hint.classList.add('show'), 10);
    
    // 自动隐藏
    setTimeout(() => {
        hint.classList.remove('show');
        setTimeout(() => hint.remove(), 300);
    }, 2000);
}

// 分页支持已直接集成到updateCenterContent和updateReadingContent函数中

// 初始化分页系统
document.addEventListener('DOMContentLoaded', function() {
    // 确保分页系统在DOM完全加载后初始化
    setTimeout(() => {
        console.log('开始初始化分页系统...');
        initializePagination();
        console.log('分页系统初始化完成');
    }, 500);
});

// 添加键盘快捷键支持
document.addEventListener('keydown', function(event) {
    // 阅读模式下禁用分页快捷键
    if (isReadingMode || !paginationEnabled) return;
    
    // 防止在输入框中触发
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (event.key === 'ArrowLeft' && event.ctrlKey) {
        // Ctrl + 左箭头：上一页
        event.preventDefault();
        prevPage();
    } else if (event.key === 'ArrowRight' && event.ctrlKey) {
        // Ctrl + 右箭头：下一页
        event.preventDefault();
        nextPage();
    } else if (event.key === 'PageUp') {
        // Page Up：上一页
        event.preventDefault();
        prevPage();
    } else if (event.key === 'PageDown') {
        // Page Down：下一页
        event.preventDefault();
        nextPage();
    } else if (event.key === 'Home' && event.ctrlKey) {
        // Ctrl + Home：第一页
        event.preventDefault();
        if (currentPage > 1) {
            currentPage = 1;
            displayCurrentPage();
            updatePaginationNavigation();
            scrollToContentTop();
            showKeyboardHint('Ctrl + Home 第一页');
        }
    } else if (event.key === 'End' && event.ctrlKey) {
        // Ctrl + End：最后一页
        event.preventDefault();
        if (currentPage < totalPages) {
            currentPage = totalPages;
            displayCurrentPage();
            updatePaginationNavigation();
            scrollToContentTop();
            showKeyboardHint('Ctrl + End 最后一页');
        }
    }
});

// 点击页面其他地方隐藏分页设置面板
document.addEventListener('click', function(event) {
    const settingsPanel = document.getElementById('page-settings-panel');
    const settingsBtn = event.target.closest('[onclick*="togglePageSettings"]');
    
    if (settingsPanel &&
        settingsPanel.style.display !== 'none' &&
        !settingsPanel.contains(event.target) &&
        !settingsBtn) {
        settingsPanel.style.display = 'none';
    }
});


// ==================== 章节分页功能 ====================

/**
 * 章节列表分页 - 在固定高度容器中智能分页
 */
function paginateChaptersList() {
    // 直接渲染所有章节，不再需要动态分页
    displayAllChapters();
    
    // 如果章节数量很多，启用简单分页（每页15个）
    const ITEMS_PER_PAGE = 15;
    
    if (chaptersData.length > ITEMS_PER_PAGE) {
        // 分页处理
        chapterPagesData = [];
        for (let i = 0; i < chaptersData.length; i += ITEMS_PER_PAGE) {
            chapterPagesData.push(chaptersData.slice(i, i + ITEMS_PER_PAGE));
        }
        
        totalChapterPages = chapterPagesData.length;
        currentChapterPage = 1;
        
        console.log(`章节分页: ${totalChapterPages}页, 每页${ITEMS_PER_PAGE}个章节`);
        
        // 显示分页内容
        displayCurrentChapterPage();
        updateChapterPaginationNavigation();
    } else {
        // 章节少，全部显示
        displayAllChapters();
        
        // 隐藏分页导航
        const paginationElement = document.getElementById('chapter-pagination');
        if (paginationElement) {
            paginationElement.style.display = 'none';
        }
    }
}

/**
 * 显示所有章节（不分页模式）
 */
function displayAllChapters() {
    const listContainer = document.getElementById('chapters-list');
    
    console.log('显示章节列表，数据:', chaptersData);
    
    if (!chaptersData || chaptersData.length === 0) {
        listContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--v2-text-tertiary);">暂无章节</div>';
        return;
    }
    
    listContainer.innerHTML = chaptersData.map(chapter => `
        <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
             onclick="loadChapter('${(currentNovelTitle || '').replace(/'/g, "\\'")}', ${chapter.chapter_number})"
             data-chapter="${chapter.chapter_number}">
            <div class="chapter-item-number">${chapter.chapter_number}</div>
            <div class="chapter-item-info">
                <div class="chapter-item-title">${chapter.title}</div>
                <div class="chapter-item-meta">${chapter.word_count || 0} 字</div>
            </div>
        </div>
    `).join('');
    
    // 更新章节总数
    const countElement = document.getElementById('chapters-count');
    if (countElement) {
        countElement.textContent = chaptersData.length + ' 章';
    }
    
    // 默认隐藏分页导航，如果需要分页会在paginateChaptersList中显示
    const paginationElement = document.getElementById('chapter-pagination');
    if (paginationElement) {
        paginationElement.style.display = 'none';
    }
}

/**
 * 显示当前章节页
 */
function displayCurrentChapterPage() {
    if (chapterPagesData.length === 0) return;
    
    const listContainer = document.getElementById('chapters-list');
    const currentPageData = chapterPagesData[currentChapterPage - 1];
    
    if (!currentPageData) return;
    
    listContainer.innerHTML = currentPageData.map(chapter => `
        <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
             onclick="loadChapter('${(currentNovelTitle || '').replace(/'/g, "\\'")}', ${chapter.chapter_number})"
             data-chapter="${chapter.chapter_number}">
            <div class="chapter-item-number">${chapter.chapter_number}</div>
            <div class="chapter-item-info">
                <div class="chapter-item-title">${chapter.title}</div>
                <div class="chapter-item-meta">${chapter.word_count} 字</div>
            </div>
        </div>
    `).join('');
    
    // 显示分页导航
    const paginationElement = document.getElementById('chapter-pagination');
    if (paginationElement) {
        paginationElement.style.display = 'flex';
    }
}

/**
 * 更新章节分页导航
 */
function updateChapterPaginationNavigation() {
    const currentPageSpan = document.getElementById('current-page');
    const totalPagesSpan = document.getElementById('total-pages');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentChapterPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalChapterPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentChapterPage <= 1;
    }
    
    if (nextPageBtn) {
        nextPageBtn.disabled = currentChapterPage >= totalChapterPages;
    }
}

/**
 * 上一章节页
 */
function prevChapterPage() {
    if (currentChapterPage > 1) {
        currentChapterPage--;
        displayCurrentChapterPage();
        updateChapterPaginationNavigation();
        console.log(`切换到章节页 ${currentChapterPage}`);
    }
}

/**
 * 下一章节页
 */
function nextChapterPage() {
    if (currentChapterPage < totalChapterPages) {
        currentChapterPage++;
        displayCurrentChapterPage();
        updateChapterPaginationNavigation();
        console.log(`切换到章节页 ${currentChapterPage}`);
    } else if (currentChapterPage >= totalChapterPages) {
        // 当前章节最后一页，自动进入下一章
        const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
        if (nextChapterData) {
            console.log('当前章节已读完，自动进入下一章:', nextChapterData.chapter_number);
            loadChapter(currentNovelTitle, nextChapterData.chapter_number);
        } else {
            showNotification('已经是最后一章了', 'info');
        }
    }
}

/**
 * 获取加大两倍的固定高度
 */
function getFixedHeight() {
    const viewportHeight = window.innerHeight;
    const baseHeight = Math.max(600, viewportHeight - 120); // 基础高度
    return baseHeight * 2; // 加大两倍
}

/**
 * 动态调整布局高度 - 使用加大两倍的固定高度
 */
function adjustLayoutHeight() {
    const threeColumnLayout = document.querySelector('.three-column-layout');
    
    if (threeColumnLayout) {
        // 使用加大两倍的固定高度
        const baseHeight = Math.max(600, window.innerHeight - 120);
        const layoutHeight = baseHeight * 2; // 加大两倍高度
        threeColumnLayout.style.height = `${layoutHeight}px`;
        
        console.log(`使用加大两倍高度布局: ${layoutHeight}px (基础高度: ${baseHeight}px, 视口高度: ${window.innerHeight}px)`);
        
        // 确保各栏也使用相同高度
        const leftSidebar = document.getElementById('left-sidebar');
        const centerContent = document.getElementById('center-content');
        const rightSidebar = document.getElementById('right-sidebar');
        
        if (leftSidebar) {
            leftSidebar.style.height = `${layoutHeight}px`;
        }
        
        if (centerContent) {
            centerContent.style.height = `${layoutHeight}px`;
        }
        
        if (rightSidebar) {
            rightSidebar.style.height = `${layoutHeight}px`;
        }
        
        // 重新评估章节分页需求
        if (chapterPaginationEnabled) {
            setTimeout(() => {
                paginateChaptersList();
                // 如果有章节内容，也重新计算正文分页
                if (currentChapterContent) {
                    paginateChapterContent(currentChapterContent);
                }
            }, 100);
        }
    }
}

/**
 * 初始化章节分页
 */
function initializeChapterPagination() {
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
        setTimeout(adjustLayoutHeight, 100);
    });
    
    // 初始调整布局
    setTimeout(adjustLayoutHeight, 500);
}
