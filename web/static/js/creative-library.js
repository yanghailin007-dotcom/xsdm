// ==================== 创意库功能 ====================
let currentView = 'card'; // 当前视图模式：'card' 或 'list'
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

            // 填充选择框（列表视图）
            const select = document.getElementById('creative-idea-select');
            select.innerHTML = '<option value="">-- 请选择一个创意 --</option>';

            result.creative_ideas.forEach(idea => {
                const option = document.createElement('option');
                option.value = idea.id;
                const preview = idea.core_setting.substring(0, 50) + '...';
                option.textContent = `创意 #${idea.id}: ${preview}`;
                select.appendChild(option);
            });

            // 生成卡片视图
            generateCreativeCards(result.creative_ideas);

            showStatusMessage(`✅ 成功加载 ${result.count} 个创意`, 'success');
        } else {
            throw new Error(result.error || '未找到创意数据');
        }
    } catch (error) {
        console.error('加载创意库失败:', error);
        showStatusMessage(`❌ 加载创意库失败: ${error.message}`, 'error');
    }
}

// 生成创意卡片
function generateCreativeCards(ideas) {
    const cardView = document.getElementById('card-view');
    cardView.innerHTML = '';

    ideas.forEach(idea => {
        const card = createCreativeCard(idea);
        cardView.appendChild(card);
    });
}

// 创建单个创意卡片 - 现代化详细展示
function createCreativeCard(idea) {
    const card = document.createElement('div');
    card.className = 'creative-idea-card';
    card.dataset.ideaId = idea.id;

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

    // 阶段图标和颜色映射
    const stageInfo = {
        'opening': { icon: '🌅', color: '#f59e0b' },
        'development': { icon: '📈', color: '#3b82f6' },
        'conflict': { icon: '⚡', color: '#ef4444' },
        'ending': { icon: '🎯', color: '#10b981' }
    };

    card.innerHTML = `
        <div class="creative-idea-header">
            <h3 class="creative-idea-title">${idea.raw_data?.novelTitle || `创意 #${idea.id}`}</h3>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span class="creative-idea-id">#${idea.id}</span>
                <button class="edit-button" onclick="editCreativeIdea(${idea.id}, event)" title="编辑创意">
                    ✏️
                </button>
            </div>
        </div>
        
        <div class="creative-idea-content">
            <div class="creative-idea-setting">
                <div style="font-weight: 700; color: #374151; margin-bottom: 6px; font-size: 0.9rem;">📋 核心设定</div>
                <div>${idea.core_setting ? truncateText(idea.core_setting, 120) : '暂无核心设定'}</div>
            </div>
            
            <div class="creative-idea-selling-points">
                <div class="creative-idea-selling-points-label">
                    💎 核心卖点
                </div>
                <div class="creative-idea-selling-points-text">
                    ${idea.core_selling_points || '爽文节奏 + 独特设定 + 人物成长'}
                </div>
            </div>
            
            ${stages.length > 0 ? `
                <div class="creative-idea-stages">
                    <div class="creative-idea-stages-label">
                        🎭 故事发展阶段 (${stages.length}/4)
                    </div>
                    <div class="stages-container">
                        ${stages.map(stage => {
                            const info = stageInfo[stage.key] || { icon: '📖', color: '#6b7280' };
                            return `
                                <div class="stage-item">
                                    <div class="stage-name">
                                        <span style="color: ${info.color}; margin-right: 6px;">${info.icon}</span>
                                        ${stage.name}
                                    </div>
                                    <div class="stage-summary">${truncateText(stage.summary, 80)}</div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}
        </div>
        
        <div class="creative-idea-actions">
            <button class="expand-details-btn" onclick="toggleCreativeDetails(${idea.id}, event)">
                📖 查看完整详情
            </button>
            <button class="select-creative-btn" onclick="selectCreativeIdea(${idea.id})">
                ✅ 选择此创意
            </button>
        </div>
        
        <div class="creative-idea-details" id="details-${idea.id}">
            <div class="detail-section">
                <div class="detail-section-title">
                    📋 完整核心设定
                </div>
                <div class="detail-section-content" id="core-setting-${idea.id}">
                    ${idea.core_setting || '暂无设定'}
                </div>
            </div>
            
            <div class="detail-section">
                <div class="detail-section-title">
                    💎 核心卖点
                </div>
                <div class="detail-section-content" id="selling-points-${idea.id}">
                    ${idea.core_selling_points || '暂无卖点'}
                </div>
            </div>
            
            ${stages.length > 0 ? `
                <div class="detail-section">
                    <div class="detail-section-title">
                        🎭 故事线详细设定
                    </div>
                    <div class="detail-section-content">
                        ${stages.map(stage => {
                            const info = stageInfo[stage.key] || { icon: '📖', color: '#6b7280' };
                            return `
                                <div class="story-stage-detail">
                                    <div class="story-stage-name">
                                        <span style="color: ${info.color}; margin-right: 8px;">${info.icon}</span>
                                        ${stage.name}
                                    </div>
                                    <div class="story-stage-summary" id="stage-${stage.key}-${idea.id}">
                                        ${stage.summary}
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            ` : ''}
            
            <div class="detail-section">
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                    ${idea.id === currentEditingId ? `
                        <button class="save-button" onclick="saveCreativeIdea(${idea.id})">
                            💾 保存修改
                        </button>
                        <button class="edit-button" onclick="cancelEditCreativeIdea(${idea.id})">
                            ❌ 取消
                        </button>
                    ` : `
                        <button class="edit-button" onclick="enableEditMode(${idea.id})">
                            ✏️ 编辑模式
                        </button>
                    `}
                </div>
            </div>
        </div>
    `;

    // 添加点击选择功能（排除按钮点击）
    card.addEventListener('click', function(e) {
        // 如果点击的是按钮或不希望触发选择的元素，不触发选择
        if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
            return;
        }
        selectCreativeIdea(idea.id);
    });

    return card;
}

// 文本截取辅助函数
function truncateText(text, maxLength) {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
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

// 启用编辑模式
function enableEditMode(ideaId) {
    if (currentEditingId && currentEditingId !== ideaId) {
        cancelEditCreativeIdea(currentEditingId);
    }

    currentEditingId = ideaId;
    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;

    // 保存原始数据
    originalData[ideaId] = {
        core_setting: idea.core_setting,
        core_selling_points: idea.core_selling_points,
        storyline: JSON.parse(JSON.stringify(idea.storyline || {}))
    };

    // 将卡片设置为编辑模式
    const card = document.querySelector(`[data-idea-id="${ideaId}"]`);
    if (card) {
        card.classList.add('edit-mode');
    }

    // 展开详情区域
    const detailsDiv = document.getElementById(`details-${ideaId}`);
    if (detailsDiv && !detailsDiv.classList.contains('expanded')) {
        const expandBtn = detailsDiv.previousElementSibling?.querySelector('.expand-details-btn');
        if (expandBtn) {
            toggleCreativeDetails(ideaId, { target: expandBtn });
        }
    }

    // 将内容转换为可编辑字段
    makeContentEditable(ideaId);

    // 重新生成卡片以显示编辑按钮
    refreshCard(ideaId);
}

// 使内容可编辑
function makeContentEditable(ideaId) {
    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;

    // 核心设定
    const coreSettingDiv = document.getElementById(`core-setting-${ideaId}`);
    if (coreSettingDiv) {
        coreSettingDiv.innerHTML = `
            <textarea class="editable-field editable-textarea" id="edit-core-setting-${ideaId}">
                ${idea.core_setting || ''}
            </textarea>
        `;
    }

    // 核心卖点
    const sellingPointsDiv = document.getElementById(`selling-points-${ideaId}`);
    if (sellingPointsDiv) {
        sellingPointsDiv.innerHTML = `
            <textarea class="editable-field editable-textarea" id="edit-selling-points-${ideaId}">
                ${idea.core_selling_points || ''}
            </textarea>
        `;
    }

    // 故事阶段
    const storyline = idea.storyline || {};
    for (const stageKey of ['opening', 'development', 'conflict', 'ending']) {
        if (storyline[stageKey]) {
            const stageDiv = document.getElementById(`stage-${stageKey}-${ideaId}`);
            if (stageDiv) {
                stageDiv.innerHTML = `
                    <input type="text" class="editable-field" id="edit-stage-name-${stageKey}-${ideaId}"
                           value="${storyline[stageKey].stageName || ''}" placeholder="阶段名称">
                    <textarea class="editable-field editable-textarea" id="edit-stage-summary-${stageKey}-${ideaId}"
                              placeholder="阶段描述">${storyline[stageKey].summary || ''}</textarea>
                `;
            }
        }
    }
}

// 保存创意
async function saveCreativeIdea(ideaId) {
    try {
        // 收集编辑后的数据
        const newCoreSetting = document.getElementById(`edit-core-setting-${ideaId}`)?.value || '';
        const newSellingPoints = document.getElementById(`edit-selling-points-${ideaId}`)?.value || '';

        const storyline = {};
        for (const stageKey of ['opening', 'development', 'conflict', 'ending']) {
            const nameField = document.getElementById(`edit-stage-name-${stageKey}-${ideaId}`);
            const summaryField = document.getElementById(`edit-stage-summary-${stageKey}-${ideaId}`);
            
            if (nameField && summaryField) {
                storyline[stageKey] = {
                    stageName: nameField.value,
                    summary: summaryField.value
                };
            }
        }

        const updateData = {
            coreSetting: newCoreSetting,
            coreSellingPoints: newSellingPoints,
            completeStoryline: storyline,
            novelTitle: loadedCreativeIdeas.find(i => i.id === ideaId)?.raw_data?.novelTitle || `创意${ideaId}的小说`
        };

        // 发送更新请求
        const response = await fetch(`/api/creative-ideas/${ideaId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updateData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '保存失败');
        }

        const result = await response.json();
        if (result.success) {
            // 更新本地数据
            const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
            if (idea) {
                idea.core_setting = newCoreSetting;
                idea.core_selling_points = newSellingPoints;
                idea.storyline = storyline;
            }

            // 退出编辑模式
            exitEditMode(ideaId);
            
            // 重新加载创意库以显示最新数据
            await loadCreativeIdeas();
            
            showStatusMessage(`✅ 创意 #${ideaId} 保存成功`, 'success');
        } else {
            throw new Error(result.error || '保存失败');
        }

    } catch (error) {
        console.error('保存创意失败:', error);
        showStatusMessage(`❌ 保存失败: ${error.message}`, 'error');
    }
}

// 取消编辑
function cancelEditCreativeIdea(ideaId) {
    exitEditMode(ideaId);
    refreshCard(ideaId);
}

// 退出编辑模式
function exitEditMode(ideaId) {
    currentEditingId = null;
    delete originalData[ideaId];
    
    const card = document.querySelector(`[data-idea-id="${ideaId}"]`);
    if (card) {
        card.classList.remove('edit-mode');
    }
}

// 刷新单个卡片
function refreshCard(ideaId) {
    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;

    const card = document.querySelector(`[data-idea-id="${ideaId}"]`);
    if (card) {
        const newCard = createCreativeCard(idea);
        card.replaceWith(newCard);
    }
}

// 编辑创意（从标题旁的编辑按钮）
function editCreativeIdea(ideaId, event) {
    event.stopPropagation();
    enableEditMode(ideaId);
    
    // 展开详情
    const detailsDiv = document.getElementById(`details-${ideaId}`);
    if (detailsDiv && !detailsDiv.classList.contains('expanded')) {
        // 模拟点击展开按钮
        const expandBtn = detailsDiv.previousElementSibling?.querySelector('.expand-details-btn');
        if (expandBtn) {
            toggleCreativeDetails(ideaId, { target: expandBtn });
        }
    }
}

// 选择创意
function selectCreativeIdea(ideaId) {
    // 移除之前的选择
    document.querySelectorAll('.creative-idea-card').forEach(card => {
        card.classList.remove('selected');
    });

    // 添加新选择
    const selectedCard = document.querySelector(`[data-idea-id="${ideaId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    selectedCreativeId = ideaId;
    
    // 填充表单
    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (idea) {
        fillFormFromIdea(idea);
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

// 切换创意详情显示 - 优化动画效果
function toggleCreativeDetails(ideaId, event) {
    const detailsDiv = document.getElementById(`details-${ideaId}`);
    const button = event?.target;
    
    if (detailsDiv.classList.contains('expanded')) {
        // 收起详情
        detailsDiv.classList.remove('expanded');
        if (button) {
            button.innerHTML = '📖 查看完整详情';
        }
        
        // 平滑滚动到卡片顶部
        setTimeout(() => {
            const card = document.querySelector(`[data-idea-id="${ideaId}"]`);
            if (card) {
                card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }, 300);
    } else {
        // 展开详情
        detailsDiv.classList.add('expanded');
        if (button) {
            button.innerHTML = '📕 收起详情';
        }
        
        // 确保详情区域完全可见
        setTimeout(() => {
            detailsDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }, 100);
    }
}

// 切换视图模式
function switchView(viewMode) {
    currentView = viewMode;
    
    // 更新按钮状态
    document.querySelectorAll('.view-toggle-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    if (viewMode === 'card') {
        document.getElementById('card-view-btn').classList.add('active');
        document.getElementById('card-view').style.display = 'block';
        document.getElementById('list-view').style.display = 'none';
    } else {
        document.getElementById('list-view-btn').classList.add('active');
        document.getElementById('card-view').style.display = 'none';
        document.getElementById('list-view').style.display = 'block';
    }
}

// 列表视图相关函数
function fillFromCreativeIdea() {
    const select = document.getElementById('creative-idea-select');
    if (!select) return;
    
    const ideaId = parseInt(select.value);

    if (!ideaId) {
        document.getElementById('creative-idea-preview-simple').style.display = 'none';
        selectedCreativeId = null;
        // 清除卡片选择
        document.querySelectorAll('.creative-idea-card').forEach(card => {
            card.classList.remove('selected');
        });
        return;
    }

    const idea = loadedCreativeIdeas.find(i => i.id === ideaId);
    if (!idea) return;

    selectedCreativeId = ideaId;

    // 同步卡片视图的选择状态
    document.querySelectorAll('.creative-idea-card').forEach(card => {
        card.classList.remove('selected');
    });
    const selectedCard = document.querySelector(`[data-idea-id="${ideaId}"]`);
    if (selectedCard) {
        selectedCard.classList.add('selected');
    }

    // 填充表单字段
    fillFormFromIdea(idea);

    // 显示预览（列表视图）
    const previewDiv = document.getElementById('creative-idea-preview-simple');
    const previewContent = document.getElementById('preview-content');
    
    if (previewDiv && previewContent) {
        previewDiv.style.display = 'block';

        let previewHtml = `
            <p><strong>核心设定:</strong></p>
            <p style="margin-left: 10px; color: #333;">${idea.core_setting || '暂无设定'}</p>
            <p style="margin-top: 10px;"><strong>核心卖点:</strong></p>
            <p style="margin-left: 10px; color: #333;">${idea.core_selling_points || '暂无卖点'}</p>
        `;

        // 获取故事阶段信息
        const storyline = idea.storyline || {};
        const stages = [];
        for (const stageKey of ['opening', 'development', 'conflict', 'ending']) {
            if (storyline[stageKey]) {
                stages.push({
                    name: storyline[stageKey].stageName || stageKey,
                    summary: storyline[stageKey].summary || ''
                });
            }
        }

        if (stages.length > 0) {
            previewHtml += `
                <p style="margin-top: 10px;"><strong>故事阶段:</strong></p>
                <ul style="margin-left: 20px; color: #333;">
                    ${stages.map(stage => `<li><strong>${stage.name}:</strong> ${stage.summary.substring(0, 100)}...</li>`).join('')}
                </ul>
            `;
        }

        previewContent.innerHTML = previewHtml;
    }
}