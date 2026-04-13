/**
 * 章节精修功能 - 阅读即精修
 */

let isEditMode = false;

// ==================== 精修模式切换 ====================
function toggleEditMode() {
    isEditMode = !isEditMode;
    
    const chapterTitle = document.getElementById('chapter-title');
    const chapterContent = document.getElementById('chapter-content');
    const chapterHeader = document.getElementById('chapter-header');
    const editToolbar = document.getElementById('edit-toolbar');
    const editFooterToolbar = document.getElementById('edit-footer-toolbar');
    const chapterFooter = document.getElementById('chapter-footer');
    const editBtns = document.querySelectorAll('#edit-mode-btn');
    
    if (isEditMode) {
        // 进入精修模式
        if (chapterTitle) {
            chapterTitle.contentEditable = 'true';
            chapterTitle.focus();
        }
        if (chapterContent) {
            chapterContent.contentEditable = 'true';
            // 将正文从 innerHTML 转为纯文本段落，方便编辑
            // 但 contentEditable 直接编辑 HTML 即可
        }
        if (chapterHeader) chapterHeader.classList.add('editing');
        if (chapterContent) chapterContent.classList.add('editing');
        if (editToolbar) editToolbar.classList.add('active');
        if (editFooterToolbar) editFooterToolbar.classList.add('active');
        if (chapterFooter) chapterFooter.style.display = 'none';
        editBtns.forEach(btn => btn && btn.classList.add('editing'));
        
        updateEditWordCount();
    } else {
        // 退出精修模式
        if (chapterTitle) chapterTitle.contentEditable = 'false';
        if (chapterContent) chapterContent.contentEditable = 'false';
        if (chapterHeader) chapterHeader.classList.remove('editing');
        if (chapterContent) chapterContent.classList.remove('editing');
        if (editToolbar) editToolbar.classList.remove('active');
        if (editFooterToolbar) editFooterToolbar.classList.remove('active');
        if (chapterFooter) chapterFooter.style.display = '';
        editBtns.forEach(btn => btn && btn.classList.remove('editing'));
        
        // 重新渲染当前章节，丢弃未保存的修改
        if (currentChapterIndex >= 0 && chaptersList[currentChapterIndex]) {
            selectChapter(currentChapterIndex);
        }
    }
}

// ==================== 精修辅助工具 ====================
function copyChapterContent() {
    const chapterContent = document.getElementById('chapter-content');
    if (!chapterContent) return;
    
    // 提取纯文本（去掉 HTML 标签）
    const text = chapterContent.innerText || chapterContent.textContent || '';
    navigator.clipboard.writeText(text).then(() => {
        showToast('📋 全文已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('❌ 复制失败，请手动复制');
    });
}

async function pasteChapterContent() {
    const chapterContent = document.getElementById('chapter-content');
    if (!chapterContent) return;
    
    try {
        const text = await navigator.clipboard.readText();
        if (!text) {
            showToast('⚠️ 剪贴板为空');
            return;
        }
        if (!confirm('确定要用剪贴板内容覆盖当前正文吗？此操作不可撤销（可通过恢复原始还原）。')) {
            return;
        }
        // 将纯文本按段落拆分
        const paragraphs = text.split(/\n{2,}/).map(p => p.trim()).filter(p => p.length > 0);
        if (paragraphs.length === 0) {
            // 单换行也处理
            const singleParagraphs = text.split(/\n/).map(p => p.trim()).filter(p => p.length > 0);
            chapterContent.innerHTML = singleParagraphs.map(p => `<p>${escapeHtml(p)}</p>`).join('');
        } else {
            chapterContent.innerHTML = paragraphs.map(p => `<p>${escapeHtml(p)}</p>`).join('');
        }
        updateEditWordCount();
        showToast('✅ 已粘贴覆盖');
    } catch (err) {
        console.error('粘贴失败:', err);
        showToast('❌ 无法读取剪贴板，请手动粘贴');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateEditWordCount() {
    const chapterContent = document.getElementById('chapter-content');
    const display = document.getElementById('edit-word-count');
    if (!chapterContent || !display) return;
    const text = chapterContent.innerText || chapterContent.textContent || '';
    display.textContent = text.length + ' 字';
}

// 监听输入更新字数
function initEditListeners() {
    const chapterContent = document.getElementById('chapter-content');
    const chapterTitle = document.getElementById('chapter-title');
    if (chapterContent) {
        chapterContent.addEventListener('input', updateEditWordCount);
    }
}
document.addEventListener('DOMContentLoaded', initEditListeners);

// ==================== 保存 / 恢复 / 评分 API ====================
async function saveChapterChanges() {
    if (currentChapterIndex < 0 || !chaptersList[currentChapterIndex]) return;
    
    const chapter = chaptersList[currentChapterIndex];
    const chapterTitle = document.getElementById('chapter-title');
    const chapterContent = document.getElementById('chapter-content');
    
    const newTitle = (chapterTitle ? chapterTitle.innerText : chapter.title).trim();
    // 提取正文 HTML 中的纯段落文本，保持换行
    let newContent = '';
    if (chapterContent) {
        // 如果有 <p> 标签，按 <p> 拆分
        if (chapterContent.querySelector('p')) {
            newContent = Array.from(chapterContent.querySelectorAll('p'))
                .map(p => p.innerText.trim())
                .filter(t => t)
                .join('\n\n');
        } else {
            newContent = (chapterContent.innerText || '').trim();
        }
    }
    
    try {
        const response = await fetch('/chapter/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: currentNovelTitle,
                chapter_number: chapter.number,
                new_title: newTitle,
                new_content: newContent
            })
        });
        const data = await response.json();
        
        if (data.success) {
            // 更新本地章节列表缓存
            chapter.title = newTitle;
            chapter.content = newContent;
            chapter.word_count = data.data.word_count;
            chapter.quality_score = data.data.quality_score;
            chapter.is_edited = true;
            
            // 更新章节列表显示
            renderChaptersList();
            // 重新渲染头部信息
            const wordCountEl = document.getElementById('word-count');
            if (wordCountEl) wordCountEl.textContent = chapter.word_count;
            updateEditStatus(true);
            
            // 更新精修分析面板
            await reanalyzeCurrentChapter();
            
            showToast('💾 保存成功');
            // 退出编辑模式但保留在页面
            isEditMode = false;
            if (chapterTitle) chapterTitle.contentEditable = 'false';
            if (chapterContent) chapterContent.contentEditable = 'false';
            document.getElementById('chapter-header')?.classList.remove('editing');
            chapterContent?.classList.remove('editing');
            document.getElementById('edit-toolbar')?.classList.remove('active');
            document.getElementById('edit-footer-toolbar')?.classList.remove('active');
            document.getElementById('chapter-footer').style.display = '';
            document.querySelectorAll('#edit-mode-btn').forEach(btn => btn && btn.classList.remove('editing'));
            
            // 重新渲染确保格式一致
            if (typeof renderChapter === 'function') renderChapter(chapter);
        } else {
            showToast('❌ 保存失败: ' + (data.error || '未知错误'));
        }
    } catch (err) {
        console.error('保存失败:', err);
        showToast('❌ 保存失败');
    }
}

async function revertChapterChanges() {
    if (currentChapterIndex < 0 || !chaptersList[currentChapterIndex]) return;
    const chapter = chaptersList[currentChapterIndex];
    
    if (!confirm('确定要恢复 AI 生成的原始版本吗？当前未保存的精修内容将丢失。')) {
        return;
    }
    
    try {
        const response = await fetch('/chapter/revert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: currentNovelTitle,
                chapter_number: chapter.number
            })
        });
        const data = await response.json();
        
        if (data.success) {
            chapter.word_count = data.data.word_count;
            chapter.is_edited = false;
            renderChaptersList();
            selectChapter(currentChapterIndex);
            updateEditStatus(false);
            showToast('↩️ 已恢复原始版本');
        } else {
            showToast('❌ 恢复失败: ' + (data.error || '未知错误'));
        }
    } catch (err) {
        console.error('恢复失败:', err);
        showToast('❌ 恢复失败');
    }
}

async function reanalyzeCurrentChapter() {
    if (currentChapterIndex < 0 || !chaptersList[currentChapterIndex]) return;
    const chapter = chaptersList[currentChapterIndex];
    
    let payload;
    if (isEditMode) {
        // 精修模式下，直接发送当前编辑的文本
        const chapterContent = document.getElementById('chapter-content');
        const text = chapterContent ? (chapterContent.innerText || chapterContent.textContent || '') : '';
        payload = { text: text };
    } else {
        payload = { title: currentNovelTitle, chapter_number: chapter.number };
    }
    
    try {
        const response = await fetch('/chapter/reanalyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        
        if (data.success) {
            updateEditAnalysis(data.data);
            // 同时更新头部质量分（仅非编辑模式时更新章节缓存，因为编辑模式尚未保存）
            if (!isEditMode) {
                chapter.quality_score = data.data.quality_score;
            }
        }
    } catch (err) {
        console.error('重新评分失败:', err);
    }
}

function updateEditAnalysis(data) {
    document.getElementById('ea-word-count').textContent = data.word_count || '-';
    document.getElementById('ea-dialogue-ratio').textContent = (data.dialogue_ratio !== undefined ? data.dialogue_ratio.toFixed(1) + '%' : '-');
    document.getElementById('ea-appeal-density').textContent = (data.appeal_density !== undefined ? data.appeal_density.toFixed(2) + '/千字' : '-');
    document.getElementById('ea-emotion-density').textContent = (data.emotion_density !== undefined ? data.emotion_density.toFixed(2) + '/千字' : '-');
    document.getElementById('ea-has-hook').textContent = data.has_hook ? '✅ 有' : '❌ 无';
    document.getElementById('ea-quality-score').textContent = (data.quality_score !== undefined ? data.quality_score + ' / 10.0' : '-');
}

function updateEditStatus(isEdited) {
    const el = document.getElementById('edit-status');
    if (el) el.style.display = isEdited ? 'inline-flex' : 'none';
}

// ==================== Toast 提示 ====================
function showToast(message) {
    let toast = document.getElementById('novel-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'novel-toast';
        toast.style.cssText = `
            position: fixed;
            top: 80px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.8);
            color: #fff;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 99999;
            pointer-events: none;
            transition: opacity 0.3s;
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.opacity = '1';
    setTimeout(() => { toast.style.opacity = '0'; }, 2500);
}

// ==================== 键盘保护 ====================
// 精修模式下禁用左右箭头切章
document.addEventListener('keydown', (e) => {
    if (!isEditMode) return;
    if (e.key === 'Escape') {
        toggleEditMode();
        e.preventDefault();
    }
});
