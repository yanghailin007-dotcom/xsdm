/**
 * 流程控制器 - JavaScript逻辑
 */

// 当前状态
let currentStep = 1;
let selectedNovel = null;
let selectedEvents = [];
let selectedCharacters = [];

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    loadNovels();
});

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
 * 加载章节树
 */
async function loadChapters() {
    const novelTitle = document.getElementById('novelSelect').value;
    const tree = document.getElementById('chapterTree');

    selectedNovel = novelTitle;

    if (!novelTitle) {
        tree.innerHTML = '<p class="empty-hint">请先选择小说</p>';
        return;
    }

    tree.innerHTML = '<p class="empty-hint">加载中...</p>';

    try {
        // TODO: 调用实际的API
        // const data = await videoAPI.getNovelStructure(novelTitle);

        // 模拟数据
        await new Promise(resolve => setTimeout(resolve, 500));

        const mockStructure = [
            {
                id: 'event1',
                name: '开篇：主角登场',
                count: 5,
                children: [
                    { id: 'm1', name: '第一章：神秘来客' },
                    { id: 'm2', name: '第二章：初次相遇' },
                    { id: 'm3', name: '第三章：意外发现' }
                ]
            },
            {
                id: 'event2',
                name: '第一卷：修炼之路',
                count: 8,
                children: [
                    { id: 'm4', name: '第四章：拜师学艺' },
                    { id: 'm5', name: '第五章：修炼开始' }
                ]
            }
        ];

        tree.innerHTML = mockStructure.map(event => `
            <div class="tree-item">
                <div class="tree-header" onclick="toggleTree(this)">
                    <span class="tree-toggle">▶</span>
                    <input type="checkbox" class="tree-checkbox" onchange="toggleEventSelection('${event.id}', this.checked)">
                    <span class="tree-label">${escapeHtml(event.name)}</span>
                    <span class="tree-count">${event.count}集</span>
                </div>
                <div class="tree-children">
                    ${event.children.map(child => `
                        <div class="tree-item leaf">
                            <div class="tree-header">
                                <span class="tree-toggle"></span>
                                <input type="checkbox" class="tree-checkbox" onchange="updateStats()">
                                <span class="tree-label">${escapeHtml(child.name)}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');

        updateStats();

    } catch (error) {
        console.error('加载章节失败:', error);
        tree.innerHTML = '<p class="empty-hint">加载失败，请重试</p>';
    }
}

/**
 * 切换树展开/收起
 */
function toggleTree(header) {
    header.classList.toggle('expanded');
    const children = header.parentElement.querySelector('.tree-children');
    if (children) {
        children.classList.toggle('visible');
    }
}

/**
 * 切换事件选择
 */
function toggleEventSelection(eventId, checked) {
    const container = document.querySelector(`[data-event-id="${eventId}"]`);
    if (container) {
        container.querySelectorAll('.tree-checkbox').forEach(cb => {
            cb.checked = checked;
        });
    }
    updateStats();
}

/**
 * 更新统计
 */
function updateStats() {
    const checkedEvents = document.querySelectorAll('.tree-item:not(.leaf) .tree-checkbox:checked').length;
    const checkedMedium = document.querySelectorAll('.tree-item.leaf .tree-checkbox:checked').length;

    document.getElementById('majorEventsCount').textContent = checkedEvents;
    document.getElementById('mediumEventsCount').textContent = checkedMedium;
    document.getElementById('charactersCount').textContent = '0'; // TODO: 计算角色数
}

/**
 * 上一步
 */
function prevStep() {
    if (currentStep > 1) {
        setStep(currentStep - 1);
    }
}

/**
 * 下一步
 */
function nextStep() {
    if (currentStep < 4) {
        // 验证当前步骤
        if (currentStep === 1 && !validateStep1()) return;
        if (currentStep === 2 && !validateStep2()) return;

        setStep(currentStep + 1);
    }
}

/**
 * 设置步骤
 */
function setStep(step) {
    currentStep = step;

    // 更新步骤指示器
    document.querySelectorAll('.workflow-step').forEach((s, index) => {
        s.classList.remove('active', 'completed');
        if (index + 1 < step) s.classList.add('completed');
        if (index + 1 === step) s.classList.add('active');
    });

    // 更新面板显示
    document.querySelectorAll('.step-panel').forEach((p, index) => {
        p.style.display = index + 1 === step ? 'block' : 'none';
    });

    // 更新按钮状态
    document.getElementById('prevStepBtn').disabled = step === 1;
    document.getElementById('nextStepBtn').style.display = step === 4 ? 'none' : 'inline-flex';

    // 执行步骤特定逻辑
    if (step === 2) loadCharactersForStep2();
    if (step === 3) prepareBatchGeneration();
    if (step === 4) showCompletion();
}

/**
 * 验证步骤1
 */
function validateStep1() {
    const checkedCount = document.querySelectorAll('.tree-item.leaf .tree-checkbox:checked').length;
    if (checkedCount === 0) {
        showToast('请至少选择一个中级事件', 'error');
        return false;
    }
    return true;
}

/**
 * 验证步骤2
 */
function validateStep2() {
    // TODO: 验证分镜配置
    return true;
}

/**
 * 自动生成全部剧照
 */
async function autoGeneratePortraits() {
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '生成中...';

    try {
        // TODO: 调用实际的API
        await new Promise(resolve => setTimeout(resolve, 2000));

        // 模拟角色列表更新
        document.getElementById('characterList').innerHTML = `
            <div class="character-card" style="display:inline-flex;align-items:center;gap:8px;padding:8px;background:var(--bg-secondary);border-radius:8px;margin:4px;">
                <span>👤 主角</span>
                <span style="color:var(--success-color);font-size:12px;">✓ 已生成</span>
            </div>
            <div class="character-card" style="display:inline-flex;align-items:center;gap:8px;padding:8px;background:var(--bg-secondary);border-radius:8px;margin:4px;">
                <span>👩 女主角</span>
                <span style="color:var(--success-color);font-size:12px;">✓ 已生成</span>
            </div>
        `;

        showToast('角色剧照已生成', 'success');

    } catch (error) {
        console.error('生成剧照失败:', error);
        showToast('生成失败，请重试', 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🚀 自动生成全部';
    }
}

/**
 * 加载步骤2的角色
 */
function loadCharactersForStep2() {
    // TODO: 加载选中事件中的角色
}

/**
 * 预览分镜
 */
function previewStoryboard() {
    showToast('分镜预览功能开发中', 'info');
}

/**
 * 准备批量生成
 */
function prepareBatchGeneration() {
    const checkedCount = document.querySelectorAll('.tree-item.leaf .tree-checkbox:checked').length;
    document.getElementById('totalCount').textContent = checkedCount;
}

/**
 * 开始批量生成
 */
async function startBatchGenerate() {
    const btn = event.target;
    btn.disabled = true;

    const totalCount = parseInt(document.getElementById('totalCount').textContent);
    let completed = 0;

    // 创建任务列表
    const taskList = document.getElementById('taskList');
    taskList.innerHTML = '';

    for (let i = 0; i < totalCount; i++) {
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item';
        taskItem.id = `task-${i}`;
        taskItem.innerHTML = `
            <div class="task-status pending">○</div>
            <div class="task-info">
                <div class="task-title">视频 ${i + 1}</div>
                <div class="task-meta">准备中...</div>
            </div>
            <div class="task-progress">
                <div class="task-progress-bar">
                    <div class="task-progress-fill"></div>
                </div>
            </div>
        `;
        taskList.appendChild(taskItem);
    }

    // 模拟批量生成
    for (let i = 0; i < totalCount; i++) {
        const task = document.getElementById(`task-${i}`);
        const status = task.querySelector('.task-status');
        const meta = task.querySelector('.task-meta');

        // 开始处理
        status.className = 'task-status processing';
        status.textContent = '⋯';
        meta.textContent = '生成中...';

        // 模拟进度
        for (let p = 0; p <= 100; p += 20) {
            await new Promise(resolve => setTimeout(resolve, 200));
            task.querySelector('.task-progress-fill').style.width = `${p}%`;
        }

        // 完成
        status.className = 'task-status completed';
        status.textContent = '✓';
        meta.textContent = '已完成';

        completed++;
        document.getElementById('completedCount').textContent = completed;
        document.getElementById('progressPercent').textContent = `${Math.round(completed / totalCount * 100)}%`;
        document.getElementById('batchProgressFill').style.width = `${completed / totalCount * 100}%`;

        // 添加到输出
        addToOutput(i + 1);
    }

    btn.disabled = false;
    showToast('所有视频生成完成！', 'success');

    // 自动跳转到完成步骤
    setTimeout(() => setStep(4), 1000);
}

/**
 * 添加到输出
 */
function addToOutput(index) {
    const grid = document.getElementById('outputGrid');

    // 移除空提示
    const emptyHint = grid.querySelector('.empty-hint');
    if (emptyHint) emptyHint.remove();

    const item = document.createElement('div');
    item.className = 'output-item';
    item.innerHTML = `
        <div class="output-thumbnail">
            <div style="width:100%;height:100%;background:var(--bg-tertiary);display:flex;align-items:center;justify-content:center;font-size:30px;">🎬</div>
            <div class="output-overlay">
                <span class="output-title">视频 ${index}</span>
                <div class="output-actions">
                    <button onclick="showToast('下载功能开发中', 'info')">📥</button>
                </div>
            </div>
        </div>
        <div class="output-info">
            <div class="output-meta">1080p · 10秒</div>
        </div>
    `;

    grid.appendChild(item);
}

/**
 * 显示完成页面
 */
function showCompletion() {
    const grid = document.getElementById('finalOutputs');
    const outputGrid = document.getElementById('outputGrid');

    if (outputGrid) {
        grid.innerHTML = outputGrid.innerHTML;
    }
}

/**
 * 下载全部
 */
function downloadAll() {
    showToast('批量下载功能开发中', 'info');
}

/**
 * 重置工作流
 */
function resetWorkflow() {
    currentStep = 1;
    setStep(1);

    // 清空选择
    document.querySelectorAll('.tree-checkbox').forEach(cb => cb.checked = false);
    updateStats();

    // 清空输出
    document.getElementById('outputGrid').innerHTML = '<p class="empty-hint">生成的视频将显示在这里</p>';

    // 重置进度
    document.getElementById('completedCount').textContent = '0';
    document.getElementById('progressPercent').textContent = '0%';
    document.getElementById('batchProgressFill').style.width = '0%';
}

/**
 * 保存进度
 */
function saveProgress() {
    const progress = {
        novel: selectedNovel,
        step: currentStep,
        events: selectedEvents,
        characters: selectedCharacters
    };

    // TODO: 调用实际的API保存进度
    console.log('保存进度:', progress);

    showToast('进度已保存', 'success');
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
