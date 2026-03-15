// ==================== 创意库功能 - 仅列表视图 ====================
let loadedCreativeIdeas = [];
let selectedCreativeId = null;

// 编辑功能相关变量
let currentEditingId = null;
let originalData = {};

// 加载创意库
async function loadCreativeIdeas() {
    try {
        const response = await fetch('/api/creative-ideas');
        
        if (response.status === 401) {
            showStatusMessage('请先登录才能使用创意库功能', 'error');
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success && result.creative_ideas) {
            loadedCreativeIdeas = result.creative_ideas;

            // 检测页面结构并渲染
            const legacyContent = document.getElementById('creative-library-content');
            const legacySelect = document.getElementById('creative-idea-select');
            const newContainer = document.getElementById('creative-library-container');

            if (legacyContent && legacySelect) {
                // 旧版页面结构
                renderLegacyCreativeLibrary(result.creative_ideas);
            } else if (newContainer) {
                // 新版页面结构 (phase-one-setup-new.html)
                renderNewCreativeLibrary(result.creative_ideas);
            }

            showStatusMessage(`✅ 成功加载 ${result.count} 个创意`, 'success');
        } else {
            throw new Error(result.error || '未找到创意数据');
        }
    } catch (error) {
        console.error('加载创意库失败:', error);
        showStatusMessage(`❌ 加载创意库失败: ${error.message}`, 'error');
    }
}

// 渲染旧版创意库
function renderLegacyCreativeLibrary(ideas) {
    const content = document.getElementById('creative-library-content');
    const select = document.getElementById('creative-idea-select');
    
    if (content) content.style.display = 'block';
    if (select) {
        select.innerHTML = '<option value="">-- 请选择一个创意 --</option>';
        ideas.forEach(idea => {
            const option = document.createElement('option');
            option.value = idea.id;
            const title = idea.raw_data?.novelTitle || `创意 #${idea.id}`;
            option.textContent = title;
            select.appendChild(option);
        });
    }
}

// 渲染新版创意库 (V3 玻璃拟态UI)
function renderNewCreativeLibrary(ideas) {
    const container = document.getElementById('creative-library-container');
    if (!container) return;

    if (ideas.length === 0) {
        container.innerHTML = `
            <div class="pt-empty-state" style="padding: 24px; text-align: center;">
                <div style="font-size: 32px; margin-bottom: 8px;">💡</div>
                <p style="color: var(--pt-text-secondary); font-size: 14px;">暂无创意</p>
                <p style="color: var(--pt-text-tertiary); font-size: 12px; margin-top: 4px;">点击上方按钮创建新创意</p>
            </div>
        `;
        return;
    }

    // 构建创意卡片列表
    let html = '<div class="creative-list" style="display: flex; flex-direction: column; gap: 12px;">';
    
    ideas.forEach(idea => {
        const title = idea.raw_data?.novelTitle || `创意 #${idea.id}`;
        const coreSetting = idea.core_setting ? idea.core_setting.substring(0, 60) + '...' : '暂无设定';
        
        html += `
            <div class="creative-card" 
                 data-id="${idea.id}"
                 onclick="selectCreativeForNewUI(${idea.id})"
                 style="background: rgba(255,255,255,0.03); 
                        border: 1px solid rgba(255,255,255,0.08); 
                        border-radius: 8px; 
                        padding: 12px; 
                        cursor: pointer;
                        transition: all 0.2s;
                        hover: background: rgba(255,255,255,0.06);"
                 onmouseover="this.style.background='rgba(255,255,255,0.06)'"
                 onmouseout="this.style.background='rgba(255,255,255,0.03)'">
                <div style="font-weight: 600; font-size: 14px; color: var(--pt-text-primary); margin-bottom: 4px;">
                    ${title}
                </div>
                <div style="font-size: 12px; color: var(--pt-text-secondary); line-height: 1.4;">
                    ${coreSetting}
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// 新版UI选择创意
function selectCreativeForNewUI(ideaId, cardElement = null) {
    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;
    
    selectedCreativeId = ideaId;
    
    // 填充表单
    fillFormFromIdea(idea);
    
    // 高亮选中的卡片
    document.querySelectorAll('.creative-card').forEach(card => {
        card.style.borderColor = 'rgba(255,255,255,0.08)';
        card.style.background = 'rgba(255,255,255,0.03)';
    });
    
    // 🔥 修复：支持传入 cardElement 或使用 event.currentTarget
    const targetCard = cardElement || (typeof event !== 'undefined' ? event.currentTarget : null);
    if (targetCard) {
        targetCard.style.borderColor = 'var(--pt-primary, #6366f1)';
        targetCard.style.background = 'rgba(99,102,241,0.1)';
    }
    
    showStatusMessage(`✅ 已选择: ${idea.raw_data?.novelTitle || `创意 #${idea.id}`}`, 'success');
    
    // 🔥 新增：检查是否有可恢复的检查点
    const title = idea.raw_data?.novelTitle || idea.title;
    if (title && typeof checkTaskResumeStatus === 'function') {
        console.log(`🔍 [RESUME] 选择创意后检查检查点: ${title}`);
        checkTaskResumeStatus(title).then(resumeInfo => {
            if (resumeInfo && typeof showResumeOption === 'function') {
                showResumeOption(resumeInfo);
                console.log(`✅ [RESUME] 发现可恢复的检查点: ${resumeInfo.progress_percentage}%`);
            }
        });
    }
}

// 🔥 新增：程序化选择创意（用于恢复模式）
function selectCreativeById(ideaId) {
    console.log('[selectCreativeById] 开始执行, ideaId:', ideaId, '类型:', typeof ideaId);
    console.log('[selectCreativeById] loadedCreativeIdeas:', loadedCreativeIdeas);
    
    if (!loadedCreativeIdeas || loadedCreativeIdeas.length === 0) {
        console.warn('[selectCreativeById] 创意库未加载');
        return false;
    }
    
    // 🔥 修复：支持数字和字符串ID比较
    const idea = loadedCreativeIdeas.find(i => 
        i.id == ideaId || i.raw_data?.id == ideaId || i.raw_data?.seedId == ideaId
    );
    
    console.log('[selectCreativeById] 查找结果:', idea);
    
    if (!idea) {
        console.warn('[selectCreativeById] 未找到创意:', ideaId);
        console.warn('[selectCreativeById] 可用创意:', loadedCreativeIdeas.map(i => ({id: i.id, rawId: i.raw_data?.id, title: i.raw_data?.novelTitle})));
        return false;
    }
    
    selectedCreativeId = idea.id;
    
    // 填充表单
    fillFormFromIdea(idea);
    
    // 🔥 修复：使用 data-id 属性查找卡片
    const selector = `.creative-card[data-id="${idea.id}"]`;
    console.log('[selectCreativeById] 选择器:', selector);
    
    const targetCard = document.querySelector(selector);
    console.log('[selectCreativeById] 找到的卡片:', targetCard);
    
    // 重置所有卡片样式
    const allCards = document.querySelectorAll('.creative-card');
    console.log('[selectCreativeById] 总卡片数:', allCards.length);
    
    allCards.forEach(card => {
        card.style.borderColor = 'rgba(255,255,255,0.08)';
        card.style.background = 'rgba(255,255,255,0.03)';
    });
    
    // 高亮目标卡片
    if (targetCard) {
        targetCard.style.borderColor = 'var(--pt-primary, #6366f1)';
        targetCard.style.background = 'rgba(99,102,241,0.1)';
        console.log(`[selectCreativeById] ✅ 已高亮卡片: data-id=${idea.id}`);
    } else {
        console.warn('[selectCreativeById] ❌ 未找到对应卡片元素:', idea.id);
        // 列出所有卡片的data-id
        const allDataIds = Array.from(allCards).map(c => c.getAttribute('data-id'));
        console.log('[selectCreativeById] 可用data-id:', allDataIds);
    }
    
    console.log(`[selectCreativeById] ✅ 已程序化选中创意: ${idea.raw_data?.novelTitle || `创意 #${idea.id}`}`);
    return true;
}

// 从创意填充表单
function fillFromCreativeIdea() {
    const select = document.getElementById('creative-idea-select');
    if (!select) return;
    
    const ideaId = parseInt(select.value);

    if (!ideaId) {
        const previewDiv = document.getElementById('creative-idea-preview-simple');
        if (previewDiv) {
            previewDiv.style.display = 'none';
        }
        selectedCreativeId = null;
        return;
    }

    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;

    selectedCreativeId = ideaId;

    // 填充表单字段
    fillFormFromIdea(idea);

    // 显示预览
    const previewDiv = document.getElementById('creative-idea-preview-simple');
    const previewContent = document.getElementById('preview-content');
    
    if (previewDiv && previewContent) {
        previewDiv.style.display = 'block';

        let previewHtml = `
            <div class="creative-detail-card" style="background: var(--card-bg, rgba(255,255,255,0.05)); padding: 16px; border-radius: 8px; margin-top: 12px; border: 1px solid var(--border-color, rgba(255,255,255,0.1));">
                <p style="margin: 0 0 8px 0; font-weight: 600; color: var(--text-primary, #f8fafc);">📋 核心设定</p>
                <p style="margin: 0 0 16px 12px; color: var(--text-secondary, #cbd5e1); line-height: 1.6;">${idea.core_setting || '暂无设定'}</p>
                
                <p style="margin: 0 0 8px 0; font-weight: 600; color: var(--text-primary, #f8fafc);">💎 核心卖点</p>
                <p style="margin: 0 0 16px 12px; color: var(--text-secondary, #cbd5e1); line-height: 1.6;">${idea.core_selling_points || '暂无卖点'}</p>
        `;

        // 获取故事阶段信息
        const storyline = idea.storyline || {};
        const stages = [];
        for (const stageKey of ['opening', 'development', 'conflict', 'ending']) {
            if (storyline[stageKey]) {
                stages.push({
                    key: stageKey,
                    name: storyline[stageKey].stageName || getDefaultStageName(stageKey),
                    summary: storyline[stageKey].summary || ''
                });
            }
        }

        if (stages.length > 0) {
            const stageIcons = {
                'opening': '🌅',
                'development': '📈',
                'conflict': '⚡',
                'ending': '🎯'
            };

            previewHtml += `
                <p style="margin: 0 0 8px 0; font-weight: 600; color: var(--text-primary, #f8fafc);">🎭 故事阶段</p>
                <div style="margin-left: 12px;">
            `;

            stages.forEach(stage => {
                const icon = stageIcons[stage.key] || '📖';
                previewHtml += `
                    <div style="margin-bottom: 12px; padding: 8px; background: var(--card-bg-secondary, rgba(255,255,255,0.03)); border-radius: 6px;">
                        <div style="font-weight: 600; color: var(--text-primary, #f8fafc); margin-bottom: 4px;">${icon} ${stage.name}</div>
                        <div style="color: var(--text-secondary, #94a3b8); font-size: 14px; line-height: 1.5;">${stage.summary.substring(0, 150)}${stage.summary.length > 150 ? '...' : ''}</div>
                    </div>
                `;
            });

            previewHtml += `
                </div>
            `;
        }

        previewHtml += `
            </div>
        `;

        previewContent.innerHTML = previewHtml;
    }
}

// 从创意填充表单
function fillFormFromIdea(idea) {
    const titleField = document.getElementById('novel-title');
    const synopsisField = document.getElementById('novel-synopsis');
    const coreSettingField = document.getElementById('core-setting');
    const sellingPointsField = document.getElementById('core-selling-points');
    
    const title = idea.raw_data?.novelTitle || `创意${idea.id}的小说`;
    if (titleField) titleField.value = title;
    if (synopsisField) synopsisField.value = idea.core_setting ? idea.core_setting.substring(0, 200) : '';
    if (coreSettingField) coreSettingField.value = idea.core_setting || '';
    if (sellingPointsField) sellingPointsField.value = idea.core_selling_points || '爽文节奏 + 独特设定 + 人物成长';
    
    // 🔥 新增：填充后检查是否有可恢复的检查点（用于下拉框选择）
    if (title && typeof checkTaskResumeStatus === 'function') {
        console.log(`🔍 [RESUME] 填充表单后检查检查点: ${title}`);
        checkTaskResumeStatus(title).then(resumeInfo => {
            if (resumeInfo && typeof showResumeOption === 'function') {
                showResumeOption(resumeInfo);
                console.log(`✅ [RESUME] 发现可恢复的检查点: ${resumeInfo.progress_percentage}%`);
            }
        });
    }
}

// 获取默认阶段名称
function getDefaultStageName(stageKey) {
    const defaultNames = {
        'opening': '开篇阶段',
        'development': '发展阶段',
        'conflict': '高潮阶段',
        'ending': '结局阶段'
    };
    return defaultNames[stageKey] || stageKey;
}

// 选择创意（通过下拉框）
function handleIdeaSelection() {
    const select = document.getElementById('creative-idea-select');
    if (!select) return;
    
    const ideaId = parseInt(select.value);
    if (ideaId) {
        selectedCreativeId = ideaId;
        const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
        if (idea) {
            fillFormFromIdea(idea);
        }
    }
}

// 状态消息显示
function showStatusMessage(message, type = 'info') {
    const statusDiv = document.getElementById('status-message');
    if (!statusDiv) return;
    
    statusDiv.textContent = message;
    statusDiv.className = `status-message ${type}`;
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 3000);
}