// 章节内容查看页面JavaScript

let currentProjectTitle = null;
let currentChapterNumber = null;
let chaptersList = [];
let currentRawFiles = null;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 从URL参数获取项目标题
    const urlParams = new URLSearchParams(window.location.search);
    currentProjectTitle = urlParams.get('title');
    
    if (!currentProjectTitle) {
        showEmptyState('未指定项目', '请从第二阶段生成页面选择项目');
        return;
    }
    
    // 加载项目数据
    loadProjectData();
});

// ==================== 数据加载功能 ====================

async function loadProjectData() {
    try {
        // 更新导航栏项目标题
        document.getElementById('current-project-title').textContent = currentProjectTitle;
        
        // 获取项目详情
        const response = await fetch(`/api/project/${encodeURIComponent(currentProjectTitle)}/with-phase-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const projectData = await response.json();
        
        // 加载章节数据
        await loadChaptersList();
        
    } catch (error) {
        console.error('加载项目数据失败:', error);
        showEmptyState('加载失败', error.message);
    }
}

async function loadChaptersList() {
    try {
        const response = await fetch(`/api/phase-two/content-review/${encodeURIComponent(currentProjectTitle)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            chaptersList = result.chapters || [];
            displayChaptersList(chaptersList);
            
            // 如果有章节，自动加载第一章
            if (chaptersList.length > 0) {
                selectChapter(chaptersList[0].chapter_number);
            } else {
                showEmptyState('暂无章节', '该项目尚未生成任何章节内容');
            }
        }
    } catch (error) {
        console.error('加载章节列表失败:', error);
        showEmptyState('加载失败', error.message);
    }
}

function displayChaptersList(chapters) {
    const listContainer = document.getElementById('chapter-list');
    
    if (chapters.length === 0) {
        listContainer.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📭</div>
                <div class="empty-state-text">暂无章节</div>
                <p style="font-size: 13px; margin-top: 8px;">该项目尚未生成任何章节内容</p>
            </div>
        `;
        return;
    }
    
    // 计算总字数
    const totalWords = chapters.reduce((sum, ch) => sum + (ch.word_count || 0), 0);
    document.getElementById('total-chapters-count').textContent = chapters.length;
    document.getElementById('total-words-count').textContent = totalWords.toLocaleString();
    
    let html = '';
    chapters.forEach(chapter => {
        // 尝试从文件名或数据中获取章节标题
        let chapterTitle = chapter.title || '';
        
        // 如果没有标题，尝试从文件名提取
        if (!chapterTitle && chapter.file_name) {
            // 移除文件扩展名
            const nameWithoutExt = chapter.file_name.replace(/\.(txt|json)$/, '');
            // 如果文件名包含"第X章"，使用它作为标题
            const titleMatch = nameWithoutExt.match(/(.+第\d+章.*)/);
            if (titleMatch) {
                chapterTitle = titleMatch[1];
            } else {
                chapterTitle = nameWithoutExt;
            }
        }
        
        // 如果还是没有，使用默认格式
        if (!chapterTitle) {
            chapterTitle = `第${chapter.chapter_number}章`;
        }
        
        const wordCount = (chapter.word_count || 0).toLocaleString();
        
        html += `
            <div class="chapter-item" data-chapter-num="${chapter.chapter_number}" onclick="selectChapter(${chapter.chapter_number})">
                <div class="chapter-item-title" title="${chapterTitle}">${chapterTitle}</div>
                <div class="chapter-item-meta">
                    <span>第 ${chapter.chapter_number} 章</span>
                    <span>${wordCount} 字</span>
                </div>
            </div>
        `;
    });
    
    listContainer.innerHTML = html;
}

// ==================== 章节选择和显示 ====================

async function selectChapter(chapterNum) {
    currentChapterNumber = chapterNum;
    
    // 更新列表中的选中状态
    document.querySelectorAll('.chapter-item').forEach(item => {
        item.classList.remove('active');
        if (parseInt(item.dataset.chapterNum) === chapterNum) {
            item.classList.add('active');
        }
    });
    
    // 加载章节内容
    await loadChapterContent(chapterNum);
    
    // 加载章节原始文件
    await loadChapterRawFiles(chapterNum);
    
    // 更新导航按钮状态
    updateNavigationButtons();
}

async function loadChapterContent(chapterNum) {
    const contentDiv = document.getElementById('chapter-content');
    contentDiv.innerHTML = `
        <div class="loading-spinner"></div>
        <p style="text-align: center; color: #9ca3af; margin-top: 12px;">正在加载章节内容...</p>
    `;
    
    try {
        // 获取章节原始文件
        const response = await fetch(`/api/phase-two/content-review/${encodeURIComponent(currentProjectTitle)}/chapter/${chapterNum}/files`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success && result.raw_files && result.raw_files.output_files && result.raw_files.output_files.length > 0) {
            // 读取章节内容文件
            const chapterFile = result.raw_files.output_files[0];
            const content = await readFileContent(chapterFile.file_path);
            
            displayChapterContent(chapterNum, chapterFile, content);
        } else {
            contentDiv.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📄</div>
                    <div class="empty-state-text">章节内容不存在</div>
                    <p style="font-size: 13px; margin-top: 8px;">第${chapterNum}章的文件未找到</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载章节内容失败:', error);
        contentDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-text">加载失败</div>
                <p style="font-size: 13px; margin-top: 8px;">${error.message}</p>
            </div>
        `;
    }
}

async function readFileContent(filePath) {
    try {
        const response = await fetch(`/api/file-content?path=${encodeURIComponent(filePath)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const result = await response.json();
        return result.content || '';
    } catch (error) {
        console.error('读取文件内容失败:', error);
        return '';
    }
}

function displayChapterContent(chapterNum, fileInfo, content) {
    const contentDiv = document.getElementById('chapter-content');
    const chapterTitle = fileInfo.name.replace('.txt', '').replace('.json', '');
    const wordCount = (content.length).toLocaleString();
    
    // 解析JSON格式内容（如果是JSON）
    let displayContent = content;
    let chapterTitleText = chapterTitle;
    
    if (fileInfo.extension === '.json' || content.trim().startsWith('{')) {
        try {
            const jsonData = JSON.parse(content);
            if (jsonData.content) {
                displayContent = jsonData.content;
            }
            if (jsonData.chapter_title) {
                chapterTitleText = jsonData.chapter_title;
            }
        } catch (e) {
            // 不是有效的JSON，使用原始内容
        }
    }
    
    // 格式化内容：分段
    const formattedContent = formatChapterContent(displayContent);
    
    contentDiv.innerHTML = `
        <div class="chapter-header">
            <h1>${chapterTitleText}</h1>
            <div class="chapter-meta">
                <span>📖 第 ${chapterNum} 章</span>
                <span>📝 ${wordCount} 字</span>
            </div>
        </div>
        <div class="chapter-text-content">
            ${formattedContent}
        </div>
    `;
    
    // 显示导航
    document.getElementById('chapter-navigation').style.display = 'flex';
    document.getElementById('nav-current-chapter').textContent = `第 ${chapterNum} 章`;
}

function formatChapterContent(content) {
    // 按段落分割
    const paragraphs = content.split('\n').filter(p => p.trim());
    
    return paragraphs.map(p => {
        // 检查是否是章节标题（以"第"开头且包含"章"）
        if (/第\d+章|第[一二三四五六七八九十百千]+章/.test(p.trim())) {
            return `<h3 style="font-size: 18px; font-weight: 700; margin: 24px 0 16px 0; color: #1e293b;">${p.trim()}</h3>`;
        }
        // 普通段落
        return `<p>${p.trim()}</p>`;
    }).join('');
}

// ==================== 章节导航功能 ====================

function updateNavigationButtons() {
    const currentIndex = chaptersList.findIndex(ch => ch.chapter_number === currentChapterNumber);
    
    const prevBtn = document.getElementById('prev-chapter-btn');
    const nextBtn = document.getElementById('next-chapter-btn');
    
    prevBtn.disabled = currentIndex <= 0;
    nextBtn.disabled = currentIndex >= chaptersList.length - 1;
}

function navigateChapter(direction) {
    const currentIndex = chaptersList.findIndex(ch => ch.chapter_number === currentChapterNumber);
    const newIndex = currentIndex + direction;
    
    if (newIndex >= 0 && newIndex < chaptersList.length) {
        selectChapter(chaptersList[newIndex].chapter_number);
    }
}

// ==================== 原始文件管理 ====================

async function loadChapterRawFiles(chapterNum) {
    try {
        const response = await fetch(`/api/phase-two/content-review/${encodeURIComponent(currentProjectTitle)}/chapter/${chapterNum}/files`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentRawFiles = result.raw_files;
            displayRawFilesCategories();
        }
    } catch (error) {
        console.error('加载原始文件失败:', error);
    }
}

function displayRawFilesCategories() {
    const categoriesDiv = document.getElementById('file-categories');
    
    if (!currentRawFiles) {
        categoriesDiv.innerHTML = `
            <div class="empty-state" style="padding: 40px 20px;">
                <div class="empty-state-icon">📁</div>
                <div class="empty-state-text">暂无文件信息</div>
            </div>
        `;
        return;
    }
    
    const categories = [
        { key: 'input_files', name: '输入文件', icon: '📥', desc: '写作计划和事件记录' },
        { key: 'output_files', name: '输出文件', icon: '📤', desc: '生成的章节内容' },
        { key: 'quality_files', name: '质量评价', icon: '✅', desc: '角色发展和世界观状态' },
        { key: 'character_files', name: '角色更新', icon: '👤', desc: '角色心态变化记录' }
    ];
    
    let html = '';
    categories.forEach(cat => {
        const files = currentRawFiles[cat.key] || [];
        if (files.length > 0) {
            html += `
                <div class="file-category">
                    <div class="file-category-header" onclick="toggleFileCategory(this)">
                        <span class="file-category-icon">${cat.icon}</span>
                        <h4>${cat.name}</h4>
                        <span style="margin-left: auto; font-size: 12px; color: #9ca3af;">${files.length} 个文件</span>
                        <span class="file-category-toggle">▼</span>
                    </div>
                    <div class="file-list">
            `;
            
            files.forEach(file => {
                const fileName = file.name || file.type || '未知文件';
                const fileSize = formatFileSize(file.file_size || 0);
                
                html += `
                    <div class="file-item" onclick="viewFile('${cat.key}', '${fileName}')">
                        <span class="file-item-icon">📄</span>
                        <span class="file-item-name">${fileName}</span>
                        <span class="file-item-size">${fileSize}</span>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }
    });
    
    if (html === '') {
        html = `
            <div class="empty-state" style="padding: 40px 20px;">
                <div class="empty-state-icon">📁</div>
                <div class="empty-state-text">该章节暂无关联文件</div>
            </div>
        `;
    }
    
    categoriesDiv.innerHTML = html;
}

function toggleFileCategory(header) {
    header.classList.toggle('collapsed');
    const fileList = header.nextElementSibling;
    fileList.classList.toggle('collapsed');
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

// ==================== 文件查看器 ====================

function showRawFiles() {
    if (!currentRawFiles || !currentChapterNumber) {
        alert('请先选择要查看的章节');
        return;
    }
    
    const modal = document.getElementById('raw-file-viewer-modal');
    const tabsDiv = document.getElementById('file-tabs');
    
    // 生成文件标签
    let tabsHtml = '';
    let allFiles = [];
    
    const categories = [
        { key: 'input_files', name: '输入文件' },
        { key: 'output_files', name: '输出文件' },
        { key: 'quality_files', name: '质量评价' },
        { key: 'character_files', name: '角色更新' }
    ];
    
    categories.forEach(cat => {
        const files = currentRawFiles[cat.key] || [];
        files.forEach(file => {
            allFiles.push({ ...file, category: cat.name });
        });
    });
    
    if (allFiles.length === 0) {
        tabsHtml = '<div style="padding: 16px; color: #9ca3af; text-align: center;">暂无文件</div>';
    } else {
        allFiles.forEach((file, index) => {
            tabsHtml += `
                <button class="file-tab ${index === 0 ? 'active' : ''}" 
                        onclick="viewRawFile('${file.file_path}', '${file.name}', this)">
                    ${file.name || file.type}
                </button>
            `;
        });
    }
    
    tabsDiv.innerHTML = tabsHtml;
    modal.style.display = 'flex';
    
    // 自动显示第一个文件
    if (allFiles.length > 0) {
        viewRawFile(allFiles[0].file_path, allFiles[0].name, tabsDiv.querySelector('.file-tab'));
    }
}

async function viewRawFile(filePath, fileName, tabElement) {
    // 更新标签状态
    document.querySelectorAll('.file-tab').forEach(tab => tab.classList.remove('active'));
    if (tabElement) {
        tabElement.classList.add('active');
    }
    
    // 更新标题
    document.getElementById('raw-file-title').textContent = fileName || '文件内容';
    document.getElementById('raw-file-path').textContent = filePath;
    
    // 显示加载状态
    const contentDisplay = document.getElementById('file-content-display');
    contentDisplay.textContent = '正在加载文件内容...';
    
    try {
        const content = await readFileContent(filePath);
        
        // 根据文件扩展名格式化显示
        let formattedContent = content;
        if (filePath.endsWith('.json')) {
            try {
                const jsonData = JSON.parse(content);
                formattedContent = JSON.stringify(jsonData, null, 2);
            } catch (e) {
                formattedContent = content;
            }
        }
        
        contentDisplay.textContent = formattedContent || '(空文件)';
    } catch (error) {
        contentDisplay.textContent = `加载文件失败: ${error.message}`;
    }
}

function viewFile(category, fileName) {
    // 从currentRawFiles中查找文件
    const files = currentRawFiles[category] || [];
    const file = files.find(f => f.name === fileName || f.type === fileName);
    
    if (file) {
        showRawFiles();
        // 切换到对应的标签
        setTimeout(() => {
            const tabs = document.querySelectorAll('.file-tab');
            tabs.forEach(tab => {
                if (tab.textContent.includes(fileName)) {
                    viewRawFile(file.file_path, fileName, tab);
                }
            });
        }, 100);
    }
}

function closeRawFileViewer() {
    document.getElementById('raw-file-viewer-modal').style.display = 'none';
}

function closeQuickChapterModal() {
    document.getElementById('quick-chapter-modal').style.display = 'none';
}

// ==================== 快速查看功能 ====================

function copyChapterContent() {
    const contentDiv = document.getElementById('quick-chapter-content');
    const text = contentDiv.innerText;
    
    navigator.clipboard.writeText(text).then(() => {
        alert('章节内容已复制到剪贴板');
    }).catch(err => {
        alert('复制失败: ' + err.message);
    });
}

// ==================== 工具函数 ====================

function showEmptyState(title, message) {
    const contentDiv = document.getElementById('chapter-content');
    contentDiv.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📖</div>
            <div class="empty-state-text">${title}</div>
            <p style="font-size: 13px; margin-top: 8px;">${message}</p>
        </div>
    `;
}

function goBack() {
    if (document.referrer && document.referrer.includes(window.location.hostname)) {
        window.history.back();
    } else {
        window.location.href = '/phase-two-generation';
    }
}

// 键盘快捷键
document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (e.key === 'ArrowLeft') {
        navigateChapter(-1);
    } else if (e.key === 'ArrowRight') {
        navigateChapter(1);
    } else if (e.key === 'Escape') {
        closeRawFileViewer();
        closeQuickChapterModal();
    }
});