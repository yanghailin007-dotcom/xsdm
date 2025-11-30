/**
 * 小说阅读页面 - 前端逻辑
 * Novel View Page - Frontend Logic
 */

let currentChapter = 1;
let novelData = null;
let chaptersData = [];

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('初始化小说阅读页面...');
        
        // 加载小说摘要
        await loadNovelSummary();
        
        // 加载章节列表
        await loadChaptersList();
        
        // 加载第一章（如果存在）
        if (chaptersData.length > 0) {
            await loadChapter(chaptersData[0].chapter_number);
        }
    } catch (error) {
        console.error('初始化失败:', error);
        showError('页面初始化失败，请刷新重试');
    }
});

/**
 * 加载小说摘要
 */
async function loadNovelSummary() {
    try {
        const response = await fetch('/api/novel/summary');
        if (!response.ok) throw new Error('加载失败');
        
        novelData = await response.json();
        console.log('小说摘要:', novelData);
        
        // 更新 UI
        document.getElementById('novel-title').textContent = novelData.title || '未命名小说';
        document.getElementById('novel-progress').textContent = 
            `${novelData.chapters_count || 0}/${novelData.total_chapters || 50}`;
        document.getElementById('core-setting').textContent = 
            novelData.core_setting || '暂无设定';
        document.getElementById('core-selling-points').textContent = 
            Array.isArray(novelData.core_selling_points) 
                ? novelData.core_selling_points.join(' • ')
                : '暂无卖点';
    } catch (error) {
        console.error('加载摘要失败:', error);
        throw error;
    }
}

/**
 * 加载章节列表
 */
async function loadChaptersList() {
    try {
        const response = await fetch('/api/chapters');
        if (!response.ok) throw new Error('加载失败');
        
        chaptersData = await response.json();
        console.log('章节列表:', chaptersData);
        
        // 生成章节列表 HTML
        const listContainer = document.getElementById('chapters-list');
        
        if (chaptersData.length === 0) {
            listContainer.innerHTML = '<div style="text-align: center; color: #999;">暂无章节</div>';
            return;
        }
        
        listContainer.innerHTML = chaptersData.map(chapter => `
            <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}" 
                 onclick="loadChapter(${chapter.chapter_number})"
                 data-chapter="${chapter.chapter_number}">
                <div class="chapter-item-title">
                    第${chapter.chapter_number}章 ${chapter.title}
                </div>
                <div class="chapter-item-meta">
                    ${chapter.word_count} 字 • 评分: ${chapter.score || '-'}
                </div>
            </div>
        `).join('');
        
        // 初始化导航按钮
        updateNavigationButtons();
        
    } catch (error) {
        console.error('加载章节列表失败:', error);
        throw error;
    }
}

/**
 * 加载特定章节
 */
async function loadChapter(chapterNum) {
    try {
        console.log('加载第', chapterNum, '章...');
        
        const response = await fetch(`/api/chapter/${chapterNum}`);
        if (!response.ok) throw new Error('章节不存在');
        
        const chapter = await response.json();
        console.log('章节数据:', chapter);
        
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
        
        // 更新右侧评估区
        updateAssessmentPanel(chapter);
        
        // 更新导航按钮
        updateNavigationButtons();
        
    } catch (error) {
        console.error('加载章节失败:', error);
        showError('加载章节失败');
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
    document.getElementById('chapter-title').textContent = title;
    document.getElementById('chapter-meta').textContent = 
        `${wordCount} 字 • 生成时间: ${generatedTime}`;
    
    // 更新内容（保留格式）
    const contentBody = document.getElementById('chapter-content');
    contentBody.innerHTML = `
        <div style="white-space: pre-wrap; word-wrap: break-word;">
            ${escapeHtml(chapter.content || '内容加载失败')}
        </div>
    `;
    
    // 记录字数
    document.getElementById('word-count').textContent = `${wordCount} 字`;
    document.getElementById('generated-time').textContent = generatedTime;
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
    contentBody.innerHTML = `
        <div style="text-align: center; color: #dc3545; padding: 40px;">
            <div style="font-size: 24px; margin-bottom: 16px;">❌</div>
            <p>${escapeHtml(message)}</p>
        </div>
    `;
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
        loadChapter(prevChapterData.chapter_number);
    }
}

/**
 * 下一章
 */
function nextChapter() {
    const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
    if (nextChapterData) {
        loadChapter(nextChapterData.chapter_number);
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
    const indicator = document.getElementById('chapter-indicator');
    
    // 按钮始终显示，根据状态启用/禁用
    prevBtn.style.display = 'block';
    nextBtn.style.display = 'block';
    
    // 设置启用/禁用状态和透明度
    if (hasPrev) {
        prevBtn.disabled = false;
        prevBtn.style.opacity = '1';
        prevBtn.style.cursor = 'pointer';
    } else {
        prevBtn.disabled = true;
        prevBtn.style.opacity = '0.5';
        prevBtn.style.cursor = 'not-allowed';
    }
    
    if (hasNext) {
        nextBtn.disabled = false;
        nextBtn.style.opacity = '1';
        nextBtn.style.cursor = 'pointer';
    } else {
        nextBtn.disabled = true;
        nextBtn.style.opacity = '0.5';
        nextBtn.style.cursor = 'not-allowed';
    }
    
    // 更新指示器
    if (indicator) {
        indicator.textContent = `第 ${currentChapter} 章`;
    }
}

// 键盘快捷键
document.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        // 上一章
        const prevChapter = chaptersData.find(c => c.chapter_number < currentChapter);
        if (prevChapter) loadChapter(prevChapter.chapter_number);
    } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        // 下一章
        const nextChapter = chaptersData.find(c => c.chapter_number > currentChapter);
        if (nextChapter) loadChapter(nextChapter.chapter_number);
    }
});

// 自动刷新进度
setInterval(async () => {
    try {
        const response = await fetch('/api/novel/summary');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('novel-progress').textContent = 
                `${data.chapters_count || 0}/${data.total_chapters || 50}`;
        }
    } catch (error) {
        // 静默处理
    }
}, 5000);
