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

            // 显示创意库区域
            document.getElementById('creative-library-content').style.display = 'block';

            // 填充选择框
            const select = document.getElementById('creative-idea-select');
            select.innerHTML = '<option value="">-- 请选择一个创意 --</option>';

            result.creative_ideas.forEach(idea => {
                const option = document.createElement('option');
                option.value = idea.id;
                const title = idea.raw_data?.novelTitle || `创意 #${idea.id}`;
                option.textContent = title;
                select.appendChild(option);
            });

            showStatusMessage(`✅ 成功加载 ${result.count} 个创意`, 'success');
        } else {
            throw new Error(result.error || '未找到创意数据');
        }
    } catch (error) {
        console.error('加载创意库失败:', error);
        showStatusMessage(`❌ 加载创意库失败: ${error.message}`, 'error');
    }
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
            <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin-top: 12px;">
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #374151;">📋 核心设定</p>
                <p style="margin: 0 0 16px 12px; color: #4b5563; line-height: 1.6;">${idea.core_setting || '暂无设定'}</p>
                
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #374151;">💎 核心卖点</p>
                <p style="margin: 0 0 16px 12px; color: #4b5563; line-height: 1.6;">${idea.core_selling_points || '暂无卖点'}</p>
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
                <p style="margin: 0 0 8px 0; font-weight: 600; color: #374151;">🎭 故事阶段</p>
                <div style="margin-left: 12px;">
            `;

            stages.forEach(stage => {
                const icon = stageIcons[stage.key] || '📖';
                previewHtml += `
                    <div style="margin-bottom: 12px;">
                        <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">${icon} ${stage.name}</div>
                        <div style="color: #6b7280; font-size: 14px; line-height: 1.5;">${stage.summary.substring(0, 150)}${stage.summary.length > 150 ? '...' : ''}</div>
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
    
    if (titleField) titleField.value = idea.raw_data?.novelTitle || `创意${idea.id}的小说`;
    if (synopsisField) synopsisField.value = idea.core_setting ? idea.core_setting.substring(0, 200) : '';
    if (coreSettingField) coreSettingField.value = idea.core_setting || '';
    if (sellingPointsField) sellingPointsField.value = idea.core_selling_points || '爽文节奏 + 独特设定 + 人物成长';
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