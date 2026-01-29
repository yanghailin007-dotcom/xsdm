/**
 * 剧照工作台 - JavaScript逻辑
 */

// 当前状态
let currentMode = 'create';
let selectedRatio = '9:16';
let referenceImages = [];
let loadedCharacter = null; // 从工作流传入的角色数据

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    setupUploadZone();
    setupTabs();
    loadNovels();
    loadCharacterFromWorkflow(); // 🔥 加载从工作流传入的角色数据
});

/**
 * 设置标签切换
 */
function setupTabs() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            switchTab(tabName);
        });
    });
}

/**
 * 切换标签
 */
function switchTab(tabName) {
    // 更新标签状态
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.tab[data-tab="${tabName}"]`)?.classList.add('active');

    // 更新面板显示
    document.querySelectorAll('.tab-content').forEach(p => p.classList.remove('active'));
    document.getElementById(`${tabName}Panel`)?.classList.add('active');

    currentMode = tabName;
}

/**
 * 设置上传区域
 */
function setupUploadZone() {
    const uploadZone = document.getElementById('refUploadZone');
    const fileInput = document.getElementById('refFileInput');

    uploadZone.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        handleFileSelect(e.target.files);
    });

    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = 'var(--primary-color)';
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = '';
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = '';
        handleFileSelect(e.dataTransfer.files);
    });
}

/**
 * 处理文件选择
 */
function handleFileSelect(files) {
    if (referenceImages.length + files.length > 5) {
        showToast('最多只能上传5张参考图', 'error');
        return;
    }

    Array.from(files).forEach(file => {
        if (!file.type.startsWith('image/')) {
            showToast('请选择图片文件', 'error');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            referenceImages.push(e.target.result);
            updatePreview();
        };
        reader.readAsDataURL(file);
    });
}

/**
 * 更新预览
 */
function updatePreview() {
    const container = document.getElementById('refPreviewContainer');
    const countInfo = document.getElementById('refCountInfo');
    const countSpan = document.getElementById('refCount');
    const placeholder = document.getElementById('uploadPlaceholder');

    if (referenceImages.length > 0) {
        placeholder.style.display = 'none';
        container.style.display = 'grid';
        countInfo.style.display = 'block';
        countSpan.textContent = referenceImages.length;

        container.innerHTML = referenceImages.map((img, index) => `
            <div class="upload-preview-item">
                <img src="${img}" alt="参考图${index + 1}">
                <button class="remove-btn" onclick="removeReference(${index})">×</button>
            </div>
        `).join('');
    } else {
        placeholder.style.display = 'flex';
        container.style.display = 'none';
        countInfo.style.display = 'none';
    }
}

/**
 * 移除参考图
 */
function removeReference(index) {
    referenceImages.splice(index, 1);
    updatePreview();
}

/**
 * 清空参考图
 */
function clearReferences() {
    referenceImages = [];
    document.getElementById('refFileInput').value = '';
    updatePreview();
}

/**
 * 选择比例
 */
function selectRatio(btn) {
    document.querySelectorAll('.ratio-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedRatio = btn.dataset.ratio;
}

/**
 * 应用模板
 */
function applyTemplate(type) {
    const templates = {
        xianxia: '一位仙风道骨的剑仙，身穿白色仙袍，手持长剑，站在云端之上，背景是壮观的云海和山峦，水墨画风',
        modern: '一位时尚的都市青年，穿着休闲装，站在繁华的城市街头，背景是高楼大厦和霓虹灯光',
        fantasy: '一位神秘的魔法师，身穿魔法长袍，手持法杖，周围环绕着魔法光芒，奇幻风格',
        scifi: '一位未来战士，身穿机甲装备，站在科幻城市中，霓虹灯光，赛博朋克风格',
        romance: '一对浪漫的情侣，手牵手走在海边，夕阳西下，温暖的橙色光线，浪漫风格'
    };

    const editor = document.getElementById('promptEditor');
    if (editor && templates[type]) {
        editor.value = templates[type];
    }
}

/**
 * 复制提示词
 */
function copyPrompt() {
    const prompt = document.getElementById('promptEditor').value;
    if (!prompt) {
        showToast('请先输入提示词', 'error');
        return;
    }

    navigator.clipboard.writeText(prompt).then(() => {
        showToast('已复制到剪贴板', 'success');
    });
}

/**
 * 生成剧照
 */
async function generatePortrait() {
    const prompt = document.getElementById('promptEditor').value.trim();
    if (!prompt) {
        showToast('请输入生成提示词', 'error');
        return;
    }

    const btn = document.getElementById('generateBtn');
    const progressCard = document.getElementById('progressCard');
    const resultCard = document.getElementById('resultCard');

    btn.disabled = true;
    btn.innerHTML = '<span class="btn-text">生成中...</span>';
    progressCard.style.display = 'block';
    resultCard.style.display = 'none';

    try {
        const quality = document.getElementById('qualitySelect').value;
        const style = document.getElementById('styleSelect').value;

        // TODO: 调用实际的API
        // const result = await videoAPI.generatePortrait({
        //     prompt,
        //     ratio: selectedRatio,
        //     quality,
        //     style,
        //     reference_images: referenceImages
        // });

        // 模拟生成延迟
        await new Promise(resolve => setTimeout(resolve, 3000));

        // 模拟结果（实际应从API获取）
        document.getElementById('resultImage').src = '/static/images/placeholder.png';

        resultCard.style.display = 'block';
        showToast('剧照生成成功！', 'success');

    } catch (error) {
        console.error('生成剧照失败:', error);
        showToast('生成失败，请重试', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🎨</span><span class="btn-text">生成剧照</span>';
        progressCard.style.display = 'none';
    }
}

/**
 * 下载结果
 */
function downloadResult() {
    const img = document.getElementById('resultImage');
    if (img && img.src) {
        const link = document.createElement('a');
        link.href = img.src;
        link.download = `portrait_${Date.now()}.png`;
        link.click();
        showToast('下载已开始', 'success');
    }
}

/**
 * 用作参考图
 */
function useAsReference() {
    const img = document.getElementById('resultImage');
    if (img && img.src) {
        referenceImages.push(img.src);
        updatePreview();
        showToast('已添加到参考图', 'success');
        switchTab('create');
    }
}

/**
 * 重新生成
 */
function regenerate() {
    document.getElementById('resultCard').style.display = 'none';
    generatePortrait();
}

/**
 * 加载小说列表
 */
async function loadNovels() {
    const select = document.getElementById('novelSelect');

    try {
        const data = await videoAPI.getNovels();

        if (data.success && data.novels) {
            select.innerHTML = '<option value="">请选择小说...</option>' +
                data.novels.map(novel =>
                    `<option value="${escapeHtml(novel.title)}">${escapeHtml(novel.title)}</option>`
                ).join('');
        }
    } catch (error) {
        console.error('加载小说列表失败:', error);
    }
}

/**
 * 加载角色列表
 */
async function loadCharacters() {
    const novelTitle = document.getElementById('novelSelect').value;
    const grid = document.getElementById('characterGrid');

    if (!novelTitle) {
        grid.innerHTML = '<p class="empty-hint">请先选择小说</p>';
        return;
    }

    grid.innerHTML = '<p class="empty-hint">加载中...</p>';

    try {
        // TODO: 调用实际的API获取角色列表
        // const data = await videoAPI.getCharacters(novelTitle);

        // 模拟角色数据
        await new Promise(resolve => setTimeout(resolve, 500));

        const mockCharacters = [
            { name: '主角', role: '主角', avatar: '👤' },
            { name: '女主角', role: '主角', avatar: '👩' },
            { name: '长老', role: '配角', avatar: '👴' },
            { name: '反派', role: '反派', avatar: '🦹' }
        ];

        grid.innerHTML = mockCharacters.map(char => `
            <div class="character-card" onclick="selectCharacter('${escapeHtml(char.name)}')">
                <div class="character-avatar">${char.avatar}</div>
                <span class="character-name">${escapeHtml(char.name)}</span>
                <span class="character-role">${escapeHtml(char.role)}</span>
            </div>
        `).join('');

    } catch (error) {
        console.error('加载角色失败:', error);
        grid.innerHTML = '<p class="empty-hint">加载失败，请重试</p>';
    }
}

/**
 * 选择角色
 */
function selectCharacter(name) {
    document.getElementById('promptEditor').value = `角色：${name}，高质量人物剧照，详细的面部特征和表情`;
    showToast(`已选择角色：${name}`, 'success');
    switchTab('create');
}

/**
 * 筛选剧照
 */
function filterPortraits(type) {
    // TODO: 实现筛选逻辑
    console.log('筛选类型:', type);
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

/**
 * 🔥 从工作流传入的角色数据
 */
function loadCharacterFromWorkflow() {
    try {
        const characterData = localStorage.getItem('portraitStudio_character');
        if (characterData) {
            loadedCharacter = JSON.parse(characterData);
            console.log('📸 [剧照工作台] 加载角色数据:', loadedCharacter);

            // 如果有预生成的提示词，自动填充
            if (loadedCharacter.generatedPrompt) {
                const promptEditor = document.getElementById('promptEditor');
                if (promptEditor) {
                    promptEditor.value = loadedCharacter.generatedPrompt;
                    console.log('✅ [剧照工作台] 已自动填充提示词');
                }
            }

            // 更新标题显示角色名称
            const pageTitle = document.querySelector('.create-panel h3, .panel-header h3');
            if (pageTitle && loadedCharacter.name) {
                pageTitle.textContent = `🎨 生成剧照 - ${loadedCharacter.name}`;
            }

            // 清除localStorage，避免下次打开还使用旧数据
            localStorage.removeItem('portraitStudio_character');
        }
    } catch (e) {
        console.error('❌ [剧照工作台] 加载角色数据失败:', e);
    }
}
