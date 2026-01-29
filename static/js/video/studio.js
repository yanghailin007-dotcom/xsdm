/**
 * 视频工作台 - JavaScript逻辑
 */

// 当前状态
let currentUploadMode = 'reference';
let selectedRatio = '16:9';
let referenceImage = null;
let firstFrame = null;
let lastFrame = null;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    setupUploadHandlers();
    loadGenerationHistory();
    checkImportedData();  // 🔥 检查是否有导入的分镜头数据
});

/**
 * 🔥 检查并加载导入的分镜头数据
 */
function checkImportedData() {
    const importedDataStr = localStorage.getItem('videoStudio_importData');
    if (!importedDataStr) return;

    try {
        const importedData = JSON.parse(importedDataStr);
        console.log('🎬 [视频工作台] 检测到导入的分镜头数据:', importedData);

        // 清除已导入的数据标记
        localStorage.removeItem('videoStudio_importData');

        // 🔥 处理角色剧照
        if (importedData.character_portraits && importedData.character_portraits.length > 0) {
            loadCharacterPortraits(importedData.character_portraits);
        }

        // 显示导入成功提示
        const portraitCount = importedData.character_portraits?.length || 0;
        const episodeCount = Object.keys(importedData.storyboard || {}).length;
        showToast(`已导入 ${importedData.novel_title} 的分镜头数据（${episodeCount}集，${portraitCount}个角色剧照）`, 'success');

        // 生成提示语并填充到编辑器
        const prompt = generatePromptFromStoryboard(importedData, importedData.character_portraits);
        const editor = document.getElementById('videoPrompt');
        if (editor) {
            editor.value = prompt;
        }

        // 显示导入数据概览
        showImportedDataOverview(importedData);

    } catch (e) {
        console.error('❌ [视频工作台] 解析导入数据失败:', e);
    }
}

/**
 * 🔥 加载角色剧照到参考图区域
 */
function loadCharacterPortraits(portraits) {
    // 自动切换到参考图模式
    setUploadMode('reference');

    // 显示已导入的角色剧照
    const uploadArea = document.getElementById('referenceUploadArea');
    if (!uploadArea) return;

    // 创建角色剧照容器
    const portraitsContainer = document.createElement('div');
    portraitsContainer.id = 'importedPortraitsContainer';
    portraitsContainer.style.cssText = `
        margin-top: 1rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
    `;

    portraits.forEach((portrait, index) => {
        const portraitDiv = document.createElement('div');
        portraitDiv.className = 'imported-portrait';
        portraitDiv.style.cssText = `
            position: relative;
            width: 80px;
            height: 80px;
            border-radius: 4px;
            overflow: hidden;
            border: 2px solid var(--accent-color);
        `;

        portraitDiv.innerHTML = `
            <img src="${portrait.url}" alt="${portrait.name}" style="width: 100%; height: 100%; object-fit: cover;">
            <div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); color: white; font-size: 0.7rem; padding: 2px 4px; text-align: center;">
                角色${index + 1}: ${portrait.name}
            </div>
            <button onclick="this.parentElement.remove();" style="position: absolute; top: 2px; right: 2px; background: rgba(255,0,0,0.8); color: white; border: none; border-radius: 50%; width: 16px; height: 16px; cursor: pointer; font-size: 10px;">×</button>
        `;

        portraitsContainer.appendChild(portraitDiv);
    });

    // 添加到参考图区域
    const previewDiv = document.getElementById('referencePreview');
    const placeholderDiv = document.getElementById('referencePlaceholder');

    if (previewDiv) {
        previewDiv.style.display = 'block';
        previewDiv.innerHTML = '';
        previewDiv.appendChild(portraitsContainer);
    }
    if (placeholderDiv) {
        placeholderDiv.style.display = 'none';
    }

    console.log(`🎬 [视频工作台] 已加载 ${portraits.length} 个角色剧照`);
}

/**
 * 🔥 从分镜头数据生成视频提示语（包含角色信息）
 */
function generatePromptFromStoryboard(data, characterPortraits) {
    const storyboard = data.storyboard || {};
    const episodes = Object.entries(storyboard);

    if (episodes.length === 0) return '';

    // 生成角色映射
    let charMap = '';
    if (characterPortraits && characterPortraits.length > 0) {
        charMap = '\n【角色参考图】\n';
        characterPortraits.forEach((portrait, index) => {
            charMap += `  角色${index + 1}: ${portrait.name}（参考图 ${index + 1}）\n`;
        });
        charMap += '\n';
    }

    let prompt = `【${data.novel_title}】视频生成提示语${charMap}`;
    prompt += `\n共 ${episodes.length} 集，`;

    // 收集每个镜头的提示语（包含角色）
    let allShots = [];
    for (const [epId, epData] of episodes) {
        const scenes = epData.scenes || [];
        prompt += `\n📺 ${epData.title}（${epData.stage}）`;

        // 添加涉及角色
        const charsInvolved = epData.characters_involved || [];
        if (charsInvolved.length > 0) {
            prompt += ` - 角色: ${charsInvolved.join('、')}`;
        }
        prompt += `\n`;

        for (const scene of scenes) {
            const shots = scene.shot_sequence || [];
            for (const shot of shots) {
                if (shot.veo_prompt) {
                    allShots.push(`【${shot.shot_type}】${shot.veo_prompt}`);
                }
            }
        }
    }

    prompt += `\n总计 ${allShots.length} 个镜头：\n\n`;
    prompt += allShots.join('\n\n');

    return prompt;
}

/**
 * 🔥 显示导入数据概览
 */
function showImportedDataOverview(data) {
    const storyboard = data.storyboard || {};
    const episodes = Object.entries(storyboard);

    // 在历史记录上方显示导入信息
    const historyList = document.getElementById('historyList');
    if (!historyList) return;

    // 移除旧的概览
    const oldOverview = historyList.querySelector('.imported-data-overview');
    if (oldOverview) oldOverview.remove();

    const overviewDiv = document.createElement('div');
    overviewDiv.className = 'imported-data-overview';
    overviewDiv.style.cssText = `
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 182, 212, 0.1) 100%);
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        border-left: 3px solid var(--success-color);
    `;

    const portraitCount = data.character_portraits?.length || 0;

    let html = '<div style="font-weight: bold; margin-bottom: 0.5rem;">📥 导入的分镜头数据</div>';
    html += `<div style="font-size: 0.9rem; color: var(--text-secondary);">`;
    html += `<div>📖 小说：${data.novel_title}</div>`;
    html += `<div>📺 集数：${episodes.length} 集</div>`;
    html += `<div>👤 角色剧照：${portraitCount} 个</div>`;

    // 计算镜头总数
    let totalShots = 0;
    for (const [epId, epData] of episodes) {
        const scenes = epData.scenes || [];
        for (const scene of scenes) {
            totalShots += (scene.shot_sequence || []).length;
        }
    }
    html += `<div>🎬 镜头：${totalShots} 个</div>`;
    html += `</div>`;

    // 显示角色列表
    if (data.character_portraits && data.character_portraits.length > 0) {
        html += '<div style="margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.5rem;">';
        data.character_portraits.forEach((portrait, index) => {
            html += `
                <div style="display: flex; align-items: center; gap: 0.25rem; background: var(--bg-dark); padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;">
                    <span style="color: var(--accent-color);">👤</span>
                    <span>角色${index + 1}: ${portrait.name}</span>
                </div>
            `;
        });
        html += '</div>';
    }

    overviewDiv.innerHTML = html;
    historyList.insertBefore(overviewDiv, historyList.firstChild);
}

/**
 * 设置上传处理器
 */
function setupUploadHandlers() {
    // 参考图上传
    const referenceUploadArea = document.getElementById('referenceUploadArea');
    const referenceInput = document.getElementById('referenceImageInput');

    referenceUploadArea.addEventListener('click', () => referenceInput.click());
    referenceInput.addEventListener('change', (e) => handleReferenceUpload(e.target.files[0]));

    // 首帧上传
    const firstFrameArea = document.getElementById('firstFrameUploadArea');
    const firstFrameInput = document.getElementById('firstFrameInput');

    firstFrameArea.addEventListener('click', () => firstFrameInput.click());
    firstFrameInput.addEventListener('change', (e) => handleFrameUpload('first', e.target.files[0]));

    // 尾帧上传
    const lastFrameArea = document.getElementById('lastFrameUploadArea');
    const lastFrameInput = document.getElementById('lastFrameInput');

    lastFrameArea.addEventListener('click', () => lastFrameInput.click());
    lastFrameInput.addEventListener('change', (e) => handleFrameUpload('last', e.target.files[0]));
}

/**
 * 设置上传模式
 */
function setUploadMode(mode) {
    currentUploadMode = mode;

    // 更新按钮状态
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });

    // 更新内容显示
    document.querySelectorAll('.upload-mode-content').forEach(content => {
        content.classList.toggle('active', content.id === `${mode}Mode`);
    });
}

/**
 * 处理参考图上传
 */
function handleReferenceUpload(file) {
    if (!file || !file.type.startsWith('image/')) {
        showToast('请选择图片文件', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        referenceImage = e.target.result;
        document.getElementById('referencePlaceholder').style.display = 'none';
        document.getElementById('referencePreview').style.display = 'block';
        document.getElementById('referencePreviewImg').src = referenceImage;
        showToast('参考图已上传', 'success');
    };
    reader.readAsDataURL(file);
}

/**
 * 处理首尾帧上传
 */
function handleFrameUpload(type, file) {
    if (!file || !file.type.startsWith('image/')) {
        showToast('请选择图片文件', 'error');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        if (type === 'first') {
            firstFrame = e.target.result;
            document.getElementById('firstFramePlaceholder').style.display = 'none';
            document.getElementById('firstFramePreview').style.display = 'block';
            document.getElementById('firstFramePreviewImg').src = firstFrame;
        } else {
            lastFrame = e.target.result;
            document.getElementById('lastFramePlaceholder').style.display = 'none';
            document.getElementById('lastFramePreview').style.display = 'block';
            document.getElementById('lastFramePreviewImg').src = lastFrame;
        }
        showToast(`${type === 'first' ? '首' : '尾'}帧已上传`, 'success');
    };
    reader.readAsDataURL(file);
}

/**
 * 移除参考图
 */
function removeReference() {
    referenceImage = null;
    document.getElementById('referenceInput').value = '';
    document.getElementById('referencePlaceholder').style.display = 'flex';
    document.getElementById('referencePreview').style.display = 'none';
}

/**
 * 移除首尾帧
 */
function removeFrame(type) {
    if (type === 'first') {
        firstFrame = null;
        document.getElementById('firstFrameInput').value = '';
        document.getElementById('firstFramePlaceholder').style.display = 'flex';
        document.getElementById('firstFramePreview').style.display = 'none';
    } else {
        lastFrame = null;
        document.getElementById('lastFrameInput').value = '';
        document.getElementById('lastFramePlaceholder').style.display = 'flex';
        document.getElementById('lastFramePreview').style.display = 'none';
    }
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
        xianxia: '一位剑仙在云端修行的场景，使用水墨画风，背景是壮观的云海和山峦，仙气缭绕',
        modern: '现代都市夜景，高楼大厦林立，霓虹灯闪烁，车流穿梭',
        scifi: '未来科幻城市，飞行汽车穿梭，全息广告牌，金属建筑',
        fantasy: '魔法森林，发光的植物，神秘的生物，魔法光芒缭绕'
    };

    const editor = document.getElementById('videoPrompt');
    if (editor && templates[type]) {
        editor.value = templates[type];
    }
}

/**
 * 生成视频
 */
async function generateVideo() {
    const prompt = document.getElementById('videoPrompt').value.trim();

    if (!prompt && !referenceImage && (!firstFrame || !lastFrame)) {
        showToast('请输入视频描述或上传图片', 'error');
        return;
    }

    // 首尾帧模式需要两张图片
    if (currentUploadMode === 'frame' && (!firstFrame || !lastFrame)) {
        showToast('请上传首尾帧两张图片', 'error');
        return;
    }

    const btn = document.querySelector('.btn-generate');
    btn.disabled = true;
    btn.innerHTML = '<span class="btn-text">生成中...</span>';

    try {
        const duration = document.getElementById('durationSelect').value;
        const resolution = document.getElementById('resolutionSelect').value;

        // TODO: 调用实际的API
        // const result = await videoAPI.generateVideo({
        //     prompt,
        //     duration,
        //     resolution,
        //     ratio: selectedRatio,
        //     mode: currentUploadMode,
        //     reference_image: referenceImage,
        //     first_frame: firstFrame,
        //     last_frame: lastFrame
        // });

        // 模拟生成延迟
        showToast('开始生成视频，请稍候...', 'info');
        await new Promise(resolve => setTimeout(resolve, 5000));

        showToast('视频生成完成！', 'success');

        // 显示视频播放器
        document.getElementById('videoPlaceholder').style.display = 'none';
        const videoPlayer = document.getElementById('videoPlayer');
        videoPlayer.style.display = 'block';
        // videoPlayer.src = result.video_url; // 实际应从API获取

        document.getElementById('videoInfoPanel').style.display = 'block';
        document.getElementById('videoResolution').textContent = resolution;
        document.getElementById('videoDuration').textContent = `${duration}秒`;

        // 添加到历史记录
        addToHistory({
            id: Date.now(),
            prompt: prompt || '使用图片生成',
            duration,
            resolution,
            timestamp: new Date().toLocaleString()
        });

    } catch (error) {
        console.error('生成视频失败:', error);
        showToast('生成失败，请重试', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<span class="btn-icon">🎬</span><span class="btn-text">生成视频</span>';
    }
}

/**
 * 添加到历史记录
 */
function addToHistory(item) {
    const list = document.getElementById('historyList');

    // 移除空提示
    const emptyHint = list.querySelector('.empty-hint');
    if (emptyHint) emptyHint.remove();

    const historyItem = document.createElement('div');
    historyItem.className = 'history-item';
    historyItem.innerHTML = `
        <div class="history-thumbnail">
            <div style="width:100%;height:100%;background:var(--bg-tertiary);display:flex;align-items:center;justify-content:center;font-size:20px;">🎬</div>
        </div>
        <div class="history-info">
            <div class="history-title">${escapeHtml(item.prompt.substring(0, 30))}${item.prompt.length > 30 ? '...' : ''}</div>
            <div class="history-meta">${item.resolution} · ${item.duration}秒</div>
        </div>
        <div class="history-status completed"></div>
    `;

    list.insertBefore(historyItem, list.firstChild);
}

/**
 * 加载生成历史
 */
async function loadGenerationHistory() {
    try {
        // TODO: 调用实际的API
        // const data = await videoAPI.getVideoHistory();

        // 暂时显示空提示
        const list = document.getElementById('historyList');
        if (!list.querySelector('.history-item')) {
            list.innerHTML = '<p class="empty-hint">暂无生成记录</p>';
        }
    } catch (error) {
        console.error('加载历史失败:', error);
    }
}

/**
 * 下载视频
 */
function downloadVideo() {
    showToast('下载已开始', 'success');
    // TODO: 实现实际下载
}

/**
 * 重新生成
 */
function regenerateVideo() {
    document.getElementById('videoPlaceholder').style.display = 'flex';
    document.getElementById('videoPlayer').style.display = 'none';
    document.getElementById('videoInfoPanel').style.display = 'none';
    generateVideo();
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
