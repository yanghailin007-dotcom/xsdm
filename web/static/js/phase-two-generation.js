// 第二阶段章节生成页面JavaScript

let currentProject = null;
let currentTaskId = null;
let progressInterval = null;
let generationStartTime = null;

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
    loadAvailableProjects();
    
    // 检查URL参数中是否有项目标题，如果有则自动选择
    checkUrlParameterForProject();
    
    // 测试goToContentReview函数是否可用
    console.log('🧪 [TEST] goToContentReview函数是否存在:', typeof goToContentReview);
    console.log('🧪 [TEST] window.goToContentReview是否存在:', typeof window.goToContentReview);
    
    // 添加全局测试：3秒后自动测试函数
    setTimeout(() => {
        console.log('🧪 [AUTO-TEST] 3秒后自动测试goToContentReview函数...');
        if (currentProject) {
            console.log('🧪 [AUTO-TEST] currentProject存在，标题:', currentProject.novel_title || currentProject.title);
        } else {
            console.log('🧪 [AUTO-TEST] currentProject为空');
        }
    }, 3000);
});

// ==================== 认证功能 ====================
async function checkLoginStatus() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            showStatusMessage('⚠️ 请先登录后再使用生成功能', 'error');
        }
    } catch (error) {
        showStatusMessage('⚠️ 请先登录后再使用生成功能', 'error');
    }
}

// ==================== URL参数处理功能 ====================
function checkUrlParameterForProject() {
    const urlParams = new URLSearchParams(window.location.search);
    const projectTitleFromUrl = urlParams.get('title');
    
    if (projectTitleFromUrl) {
        console.log('📋 [DEBUG] 从URL获取到项目标题:', decodeURIComponent(projectTitleFromUrl));
        addLogEntry('info', `检测到URL中的项目参数，等待项目列表加载后自动选中`);
        
        // 保存到localStorage以便后续使用
        localStorage.setItem('selectedProjectTitle', decodeURIComponent(projectTitleFromUrl));
    }
}

// ==================== 项目管理功能 ====================
let projectsCache = []; // 缓存项目列表

async function loadAvailableProjects() {
    try {
        const response = await fetch('/api/projects/with-phase-status');
        
        if (response.status === 401) {
            showStatusMessage('请先登录才能加载项目', 'error');
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        projectsCache = result.projects || [];
        displayProjectsList(projectsCache);
        addLogEntry('info', `成功加载 ${projectsCache.length} 个项目`);
        
        // 检查是否需要自动选择项目
        checkAndAutoSelectProject();
    } catch (error) {
        console.error('加载项目列表失败:', error);
        showStatusMessage(`❌ 加载项目失败: ${error.message}`, 'error');
        addLogEntry('error', `加载项目失败: ${error.message}`);
    }
}

function displayProjectsList(projects) {
    const projectsList = document.getElementById('projects-list');
    
    if (projects.length === 0) {
        projectsList.innerHTML = `
            <div style="text-align: center; color: #6b7280; padding: 20px;">
                <p>暂无可用的项目</p>
                <button class="btn btn-primary" style="margin-top: 12px;" onclick="location.href='/phase-one-setup'">
                    🎨 创建第一个项目
                </button>
            </div>
        `;
        return;
    }

    let html = '';
    projects.forEach(project => {
        // 对标题进行HTML转义，避免特殊字符导致的问题
        const escapedTitle = project.title.replace(/'/g, "\\'").replace(/"/g, '\\"');
        
        // 🔥 改进：所有项目都可以点击，移除点击限制
        html += `
            <div class="project-card"
                 data-title="${escapedTitle}"
                 onclick="selectProject('${escapedTitle}')"
                 style="cursor: pointer;">
                <div class="project-title">${project.title}</div>
                <div class="project-info">总章节: ${project.total_chapters || 0}</div>
                <div class="project-info">已完成: ${project.completed_chapters || 0} 章</div>
                <div class="project-status ${getProjectStatusClass(project)}">
                    ${getProjectStatusText(project)}
                </div>
            </div>
        `;
    });
    
    projectsList.innerHTML = html;
}

// 🔥 新增：根据项目状态返回对应的样式类
function getProjectStatusClass(project) {
    if (project.phase_one && project.phase_one.status === 'completed') {
        if (project.phase_two && project.phase_two.status === 'completed') {
            return 'status-completed';
        } else if (project.phase_two && project.phase_two.status === 'generating') {
            return 'status-generating';
        } else {
            return 'status-ready';
        }
    } else if (project.phase_one && project.phase_one.status === 'generating') {
        return 'status-designing';
    } else {
        return 'status-pending';
    }
}

// 自动选择项目的函数
async function checkAndAutoSelectProject() {
    const urlParams = new URLSearchParams(window.location.search);
    const projectTitleFromUrl = urlParams.get('title');
    
    // 也检查localStorage
    const storedProjectTitle = localStorage.getItem('selectedProjectTitle');
    const targetProjectTitle = projectTitleFromUrl || storedProjectTitle;
    
    if (!targetProjectTitle) {
        console.log('📋 [DEBUG] 没有检测到需要自动选择的项目');
        return;
    }
    
    const decodedTitle = decodeURIComponent(targetProjectTitle);
    console.log('📋 [DEBUG] 尝试自动选择项目:', decodedTitle);
    
    // 在项目缓存中查找匹配的项目
    const targetProject = projectsCache.find(p => p.title === decodedTitle);
    
    if (!targetProject) {
        console.warn('⚠️ [DEBUG] 在项目列表中未找到匹配的项目:', decodedTitle);
        showStatusMessage(`⚠️ 未找到项目 "${decodedTitle}"，请手动选择`, 'warning');
        // 清除localStorage
        localStorage.removeItem('selectedProjectTitle');
        return;
    }
    
    console.log('✅ [DEBUG] 找到匹配的项目，准备自动选择');
    
    // 延迟一下，确保DOM已完全渲染
    setTimeout(async () => {
        try {
            // 模拟点击选择项目
            await autoSelectProject(decodedTitle);
        } catch (error) {
            console.error('❌ [DEBUG] 自动选择项目失败:', error);
            showStatusMessage(`⚠️ 自动选择项目失败，请手动选择`, 'warning');
        }
    }, 500);
}

// 自动选择项目的内部函数
async function autoSelectProject(projectTitle) {
    console.log('🔄 [DEBUG] 开始自动选择项目:', projectTitle);
    
    // 查找项目卡片并触发选择
    const projectCards = document.querySelectorAll('.project-card');
    let foundCard = null;
    
    for (const card of projectCards) {
        const titleElement = card.querySelector('.project-title');
        if (titleElement && titleElement.textContent === projectTitle) {
            foundCard = card;
            break;
        }
    }
    
    if (!foundCard) {
        console.error('❌ [DEBUG] 未找到项目卡片元素');
        return;
    }
    
    // 触发点击事件
    foundCard.click();
    
    console.log('✅ [DEBUG] 项目卡片点击已触发');
    addLogEntry('info', `已自动选择项目: ${projectTitle}`);
    
    // 🔥 移除多余弹窗 - 只保留日志
    // showStatusMessage(`✅ 已自动选择项目: ${projectTitle}`, 'success');
    
    // 清除URL参数（避免重复触发）
    const url = new URL(window.location);
    url.searchParams.delete('title');
    window.history.replaceState({}, document.title, url);
    
    // 清除localStorage
    localStorage.removeItem('selectedProjectTitle');
    
    showStatusMessage(`✅ 已自动选择项目: ${projectTitle}`, 'success');
}

function getProjectStatusText(project) {
    if (project.phase_one && project.phase_one.status === 'completed') {
        if (project.phase_two && project.phase_two.status === 'completed') {
            return '已完成';
        } else if (project.phase_two && project.phase_two.status === 'generating') {
            return '生成中';
        } else {
            return '可生成';
        }
    } else if (project.phase_one && project.phase_one.status === 'generating') {
        return '设计中';
    } else {
        return '未完成';
    }
}

async function selectProject(projectTitle) {
    try {
        // 取消之前选中的项目
        document.querySelectorAll('.project-card').forEach(card => {
            card.classList.remove('selected');
        });

        // 选中当前项目
        event.currentTarget.classList.add('selected');

        // 加载项目详情
        const response = await fetch(`/api/project/${encodeURIComponent(projectTitle)}/with-phase-info`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const projectData = await response.json();
        currentProject = projectData;
        
        displayProjectInfo(projectData);
        displayProjectDetails(projectData);
        showCreativeEnhancement();
        showGenerationForm();
        
        addLogEntry('info', `选择项目: ${projectTitle}`);
        // 🔥 移除多余弹窗 - 只保留日志
        // showStatusMessage(`✅ 已选择项目: ${projectTitle}`, 'success');
    } catch (error) {
        console.error('选择项目失败:', error);
        showStatusMessage(`❌ 选择项目失败: ${error.message}`, 'error');
        addLogEntry('error', `选择项目失败: ${error.message}`);
    }
}

function displayProjectInfo(projectData) {
    const infoDiv = document.getElementById('selected-project-info');
    
    // 🔥 修复：优先从phase_info获取总章节数，然后尝试其他可能的位置
    const totalChapters = (
        projectData.phase_info?.total_chapters ||
        projectData.total_chapters ||
        projectData.current_progress?.total_chapters ||
        projectData.progress?.total_chapters ||
        projectData.novel_info?.total_chapters ||
        200  // 默认值
    );
    
    const completedChapters = Object.keys(projectData.generated_chapters || {}).length;
    
    infoDiv.style.display = 'block';
    document.getElementById('current-project-title').textContent = projectData.novel_title || projectData.title || '未命名';
    document.getElementById('current-project-total-chapters').textContent = totalChapters;
    document.getElementById('current-project-completed-chapters').textContent = completedChapters;
    document.getElementById('current-project-status').textContent = '准备就绪';
    
    // 更新表单默认值
    const fromChapter = document.getElementById('from-chapter');
    const chaptersToGenerate = document.getElementById('chapters-to-generate');
    
    if (fromChapter) {
        fromChapter.value = completedChapters + 1;
        fromChapter.min = 1;  // 允许从任何章节开始，包括重新生成已有章节
        // 添加事件监听器
        fromChapter.removeEventListener('input', updateChapterRange);
        fromChapter.addEventListener('input', updateChapterRange);
    }
    
    if (chaptersToGenerate) {
        const remainingChapters = totalChapters - completedChapters;
        // 移除 max 限制，允许生成任意数量的章节
        // chaptersToGenerate.max = Math.min(remainingChapters, 200);
        chaptersToGenerate.value = Math.min(10, remainingChapters);
        // 添加事件监听器
        chaptersToGenerate.removeEventListener('input', updateChapterRange);
        chaptersToGenerate.addEventListener('input', updateChapterRange);
    }
    
    // 初始化章节范围显示
    updateChapterRange();
}

// 更新章节范围显示
function updateChapterRange() {
    const fromChapter = parseInt(document.getElementById('from-chapter').value) || 1;
    const chaptersToGenerate = parseInt(document.getElementById('chapters-to-generate').value) || 0;
    const toChapter = fromChapter + chaptersToGenerate - 1;
    
    const rangeStart = document.getElementById('range-start');
    const rangeEnd = document.getElementById('range-end');
    
    if (rangeStart) {
        rangeStart.textContent = fromChapter;
    }
    if (rangeEnd) {
        if (chaptersToGenerate > 0) {
            rangeEnd.textContent = toChapter;
        } else {
            rangeEnd.textContent = fromChapter;
        }
    }
}

function displayProjectDetails(projectData) {
    const detailsDiv = document.getElementById('project-details');
    
    let html = `
        <div class="result-item">
            <h4>📋 项目信息</h4>
            <p><strong>标题:</strong> ${projectData.novel_title || '未命名'}</p>
            <p><strong>简介:</strong> ${projectData.story_synopsis || '暂无简介'}</p>
            <p><strong>核心设定:</strong> ${projectData.core_setting || '暂无设定'}</p>
        </div>
    `;
    
    if (projectData.phase_one) {
        html += `
            <div class="result-item">
                <h4>✅ 第一阶段状态</h4>
                <p><strong>状态:</strong> <span style="color: #10b981;">已完成</span></p>
                <p><strong>完成时间:</strong> ${new Date(projectData.phase_one.completed_at || Date.now()).toLocaleString()}</p>
            </div>
        `;
    }
    
    if (projectData.generated_chapters && Object.keys(projectData.generated_chapters).length > 0) {
        const generatedCount = Object.keys(projectData.generated_chapters).length;
        html += `
            <div class="result-item">
                <h4>📚 已生成章节</h4>
                <p><strong>章节数:</strong> ${generatedCount}</p>
                <p><strong>总字数:</strong> ${calculateTotalWords(projectData.generated_chapters)}</p>
            </div>
        `;
    }
    
    detailsDiv.innerHTML = html;
}

function calculateTotalWords(chapters) {
    let totalWords = 0;
    for (const chapterData of Object.values(chapters)) {
        if (chapterData.word_count) {
            totalWords += chapterData.word_count;
        } else if (chapterData.content) {
            totalWords += chapterData.content.length;
        }
    }
    return totalWords.toLocaleString();
}

function showCreativeEnhancement() {
    document.getElementById('phase-one-products-section').style.display = 'block';
    // 加载第一阶段产物数据
    loadPhaseOneProducts();
}

function showGenerationForm() {
    document.getElementById('phase-two-form').style.display = 'block';
}

// ==================== 第一阶段产物管理功能 ====================
let phaseOneProductsData = {};

async function loadPhaseOneProducts() {
    if (!currentProject) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '请先选择一个项目');
        return;
    }

    try {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('info', '正在加载第一阶段产物...');
        // showStatusMessage('🔄 正在加载第一阶段产物...', 'info');
        
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(currentProject.novel_title || currentProject.title)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.success) {
            phaseOneProductsData = result.products;
            
            // 单独加载势力系统状态
            await checkFactionSystemStatus();
            
            updateProductsDisplay();
            // 🔥 移除多余弹窗 - 只保留日志
            addLogEntry('success', '第一阶段产物加载完成');
            // showStatusMessage('✅ 第一阶段产物加载完成', 'success');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        console.error('加载第一阶段产物失败:', error);
        showStatusMessage(`❌ 加载产物失败: ${error.message}`, 'error');
        
        // 如果加载失败，显示模拟数据
        showMockProductsData();
    }
}

// 检查势力系统状态
async function checkFactionSystemStatus() {
    try {
        const response = await fetch(`/api/factions/${encodeURIComponent(currentProject.novel_title || currentProject.title)}`);
        
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.faction_system) {
                // 势力系统存在，添加到产物数据中
                phaseOneProductsData.factions = {
                    title: '势力/阵营系统',
                    content: JSON.stringify(result.faction_system, null, 2),
                    complete: true
                };
                console.log('✅ 势力系统已加载');
            }
        }
    } catch (error) {
        console.log('势力系统未生成或加载失败:', error.message);
        // 势力系统不存在是正常情况，不显示错误
    }
}

function updateProductsDisplay() {
    const categories = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market'];
    
    categories.forEach(category => {
        const statusElement = document.getElementById(`${category}-status`);
        if (statusElement) {
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('.status-text');
            
            if (phaseOneProductsData[category] && phaseOneProductsData[category].content) {
                indicator.className = 'status-indicator complete';
                text.textContent = '已完成';
            } else {
                indicator.className = 'status-indicator';
                text.textContent = '未生成';
            }
        }
    });
}

function showMockProductsData() {
    phaseOneProductsData = {
        worldview: {
            title: '世界观设定',
            content: '这是一个修仙世界，分为凡人界、修仙界、仙界三重境界。主要修炼体系包括炼气、筑基、金丹、元婴等境界。世界中有各大宗门、家族势力，以及丰富的灵兽、法宝设定。',
            complete: true
        },
        factions: {
            title: '势力/阵营系统',
            content: JSON.stringify({
                "main_conflict": "正道与魔道百年来争夺修真界主导权的大战即将爆发",
                "faction_power_balance": "正道与魔道势均力敌，散修势力在中间摇摆",
                "recommended_starting_faction": "青云宗（正道大派，资源丰富，适合作为主角初始势力）",
                "factions": [
                    {
                        "name": "青云宗",
                        "type": "正道",
                        "background": "修真界百年大派，以剑道闻名",
                        "core_philosophy": "以剑证道，匡扶正义",
                        "goals": ["维护正道秩序", "培养优秀弟子", "对抗魔道"],
                        "power_level": "一流势力",
                        "strengths": ["剑法高超", "底蕴深厚", "弟子众多"],
                        "weaknesses": ["思想保守", "内部派系林立"],
                        "territory": "占据云州七郡",
                        "relationships": {
                            "allies": ["天剑宗", "佛门圣地"],
                            "enemies": ["血魔宗", "炼魂殿"],
                            "neutrals": ["散修联盟"]
                        },
                        "role_in_plot": "主角的初始势力，提供基础资源和保护",
                        "suitable_for_protagonist": "是"
                    },
                    {
                        "name": "血魔宗",
                        "type": "魔道",
                        "background": "三百年前崛起的魔道巨擘",
                        "core_philosophy": "弱肉强食，以杀证道",
                        "goals": ["统一魔道", "消灭正道", "搜集血魂"],
                        "power_level": "一流势力",
                        "strengths": ["功法霸道", "行事狠辣", "信徒狂热"],
                        "weaknesses": ["树敌过多", "内部缺乏凝聚力"],
                        "territory": "占据幽冥渊",
                        "relationships": {
                            "allies": ["炼魂殿", "万毒谷"],
                            "enemies": ["青云宗", "天剑宗", "佛门圣地"],
                            "neutrals": []
                        },
                        "role_in_plot": "主要敌对势力，推动主线冲突",
                        "suitable_for_protagonist": "否"
                    }
                ]
            }),
            complete: true
        },
        characters: {
            title: '角色设计',
            content: '主角：张三，天赋异禀的修仙奇才，性格坚毅不屈。女主角：李四，来自名门正派，实力高强。主要配角：王五（主角好友）、赵六（导师）等。每个角色都有独特的背景故事和性格特点。',
            complete: true
        },
        growth: {
            title: '成长路线',
            content: '从炼气期开始，逐步升级到筑基、金丹、元婴。每个阶段都有不同的挑战和机遇。主角将通过修炼、奇遇、战斗等方式提升实力。成长过程中注重实力与心境的双重提升。',
            complete: true
        },
        writing: {
            title: '写作计划',
            content: '全书共200章，分为四个阶段。第一阶段（1-50章）：基础设定和成长初期；第二阶段（51-100章）：实力提升和冒险；第三阶段（101-150章）：高潮冲突；第四阶段（151-200章）：结局和新开始。',
            complete: true
        },
        storyline: {
            title: '故事线',
            content: '开篇：主角获得奇遇，踏上修仙之路；发展：修炼成长，结识伙伴，面对挑战；高潮：终极对决，揭开身世之谜；结局：功成身退，开启新的征程。故事中包含多个重大事件和转折点。',
            complete: true
        },
        market: {
            title: '市场分析',
            content: '目标读者：15-35岁男性，喜爱玄幻修仙类小说。市场定位：爽文风格，节奏明快，升级体系清晰。竞品分析：参考凡人修仙传、斗破苍穹等成功作品。特色卖点：独特的修炼体系和丰富的世界观设定。',
            complete: true
        }
    };
    
    updateProductsDisplay();
}

function editProductCategory(category) {
    if (!currentProject) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '请先选择一个项目');
        return;
    }

    const productData = phaseOneProductsData[category];
    
    // 对于势力系统，使用特殊的查看器
    if (category === 'factions') {
        viewFactionSystem();
    } else if (category === 'characters') {
        // 对于角色，使用友好的角色编辑器
        openCharacterEditorFromPhaseTwo();
    } else {
        // 其他产物使用编辑模态框
        createProductEditModal(category, productData);
    }
}

// 从第二阶段打开角色编辑器
async function openCharacterEditorFromPhaseTwo() {
    if (!currentProject) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '请先选择一个项目');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    console.log('🎯 准备打开角色编辑器，项目标题:', projectTitle);
    
    try {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('info', '正在加载角色编辑器...');
        // showStatusMessage('🔄 正在加载角色编辑器...', 'info');
        
        // 动态加载角色编辑器模态框（如果还没加载）
        let modalContainer = document.getElementById('character-editor-modal-wrapper');
        if (!modalContainer) {
            console.log('📦 创建模态框容器');
            modalContainer = document.createElement('div');
            modalContainer.id = 'character-editor-modal-wrapper';
            modalContainer.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 999999;';
            document.body.appendChild(modalContainer);
        }
        
        if (modalContainer.innerHTML.trim() === '') {
            console.log('📥 加载模态框HTML');
            const response = await fetch('/templates/components/character-editor-modal.html');
            if (!response.ok) {
                throw new Error(`加载模态框HTML失败: ${response.status}`);
            }
            const html = await response.text();
            modalContainer.innerHTML = html;
            console.log('✅ 模态框HTML加载完成，长度:', html.length);
        }
        
        // 动态加载角色编辑器JavaScript（如果还没加载）
        if (typeof openCharacterEditor === 'undefined') {
            console.log('📜 加载角色编辑器JavaScript');
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = '/static/js/character-editor.js';
                script.onload = () => {
                    console.log('✅ 角色编辑器JavaScript加载完成');
                    resolve();
                };
                script.onerror = () => {
                    console.error('❌ 角色编辑器JavaScript加载失败');
                    reject(new Error('JavaScript加载失败'));
                };
                document.head.appendChild(script);
            });
        } else {
            console.log('✅ 角色编辑器JavaScript已加载');
        }
        
        // 解析角色设计数据
        let characterDataList = [];
        const characterProduct = phaseOneProductsData.characters;
        
        console.log('📋 角色产品数据:', characterProduct);
        console.log('📋 角色产品类型:', typeof characterProduct);
        
        if (characterProduct && characterProduct.content) {
            try {
                // 尝试解析为JSON
                const parsed = JSON.parse(characterProduct.content);
                console.log('📝 解析后的数据:', parsed);
                
                if (Array.isArray(parsed)) {
                    // 直接是数组
                    characterDataList = parsed;
                    console.log('✅ 解析到角色数组:', characterDataList.length, '个角色');
                } else if (parsed && typeof parsed === 'object') {
                    // 如果是对象，检查是否包含 main_character 和 important_characters
                    if (parsed.main_character) {
                        characterDataList = [parsed.main_character];
                        if (Array.isArray(parsed.important_characters)) {
                            characterDataList = [parsed.main_character, ...parsed.important_characters];
                        }
                        console.log('✅ 从复杂对象解析到:', characterDataList.length, '个角色');
                    } else if (parsed.characters && Array.isArray(parsed.characters)) {
                        characterDataList = parsed.characters;
                        console.log('✅ 从characters字段解析到:', characterDataList.length, '个角色');
                    } else {
                        console.log('⚠️ 解析结果不是数组或可识别对象，尝试将对象包装为数组');
                        characterDataList = [parsed];
                    }
                } else {
                    console.log('⚠️ 解析结果不是数组或对象，创建默认角色');
                    throw new Error('不是有效的JSON格式');
                }
            } catch (e) {
                console.log('⚠️ 角色设计内容不是有效的JSON:', e.message);
                console.log('📝 原始内容前200字符:', characterProduct.content.substring(0, 200));
                 
                // 如果不是JSON，可能只是文本描述
                const contentText = characterProduct.content.trim();
                
                // 尝试从文本中提取角色信息
                characterDataList = [];
                
                // 如果是描述性文本，创建一个默认角色
                if (contentText.length > 0) {
                    characterDataList = [{
                        name: '角色',
                        characterName: '角色',
                        role: '主角',
                        character_type: '主角',
                        icon: '👤',
                        color: '#667eea',
                        description: contentText,
                        personality: contentText,
                        background: contentText,
                        cultivation_level: '未知'
                    }];
                }
                
                console.log('✅ 从文本内容创建了默认角色:', characterDataList.length, '个角色');
            }
        } else {
            console.log('⚠️ 没有角色产品数据，创建空数组');
            characterDataList = [];
        }
        
        console.log('📊 最终角色数据列表:', characterDataList);
        
        // 设置全局变量供角色编辑器使用
        window.currentProjectTitle = projectTitle;
        
        // 🔥 修复：直接设置原始角色数据，避免双重解析
        // 保存原始数据到特殊字段，供角色编辑器使用
        window.rawPhaseOneCharacters = {
            rawData: characterProduct?.content || '',
            parsedData: characterDataList,
            source: 'phase-two'
        };
        
        // 同时保留向后兼容的novelData结构
        window.novelData = {
            projectTitle: projectTitle,
            characters: {
                content: characterProduct?.content || '', // 🔥 使用原始内容，不要重新序列化
                complete: true
            }
        };
        
        console.log('💾 设置novelData完成');
        console.log('📦 原始角色数据已保存到window.rawPhaseOneCharacters');
        
        // 等待一小段时间确保DOM更新完成
        await new Promise(resolve => setTimeout(resolve, 100));
        
        // 打开角色编辑器
        if (typeof openCharacterEditor === 'function') {
            console.log('🎯 调用openCharacterEditor函数');
            await openCharacterEditor();
            console.log('✅ openCharacterEditor函数调用完成');
            
            // 检查模态框是否真的显示了
            const modal = document.getElementById('character-editor-modal');
            if (modal) {
                console.log('✅ 模态框元素存在，类名:', modal.className);
                console.log('✅ 模态框display样式:', window.getComputedStyle(modal).display);
            } else {
                console.error('❌ 模态框元素不存在');
            }
        } else {
            throw new Error('角色编辑器函数未加载');
        }
        
    } catch (error) {
        console.error('❌ 打开角色编辑器失败:', error);
        showStatusMessage(`❌ 打开角色编辑器失败: ${error.message}`, 'error');
    }
}

// 查看势力系统
async function viewFactionSystem() {
    if (!currentProject) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '请先选择一个项目');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '无法获取项目标题');
        return;
    }
    
    try {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('info', '正在加载势力系统...');
        // showStatusMessage('🔄 正在加载势力系统...', 'info');
        
        const response = await fetch(`/api/factions/${encodeURIComponent(projectTitle)}`);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            createFactionSystemModal(result.faction_system);
            // 🔥 移除多余弹窗 - 只保留日志
            addLogEntry('success', '势力系统加载完成');
            // showStatusMessage('✅ 势力系统加载完成', 'success');
        } else {
            throw new Error(result.error || '加载失败');
        }
    } catch (error) {
        console.error('加载势力系统失败:', error);
        showStatusMessage(`❌ 加载势力系统失败: ${error.message}`, 'error');
    }
}

// 全局变量存储势力数据
let currentFactionsData = null;

function createFactionSystemModal(factionData) {
    currentFactionsData = factionData;
    const factions = factionData.factions || [];
    const mainConflict = factionData.main_conflict || '未设置主要冲突';
    const powerBalance = factionData.faction_power_balance || '未设置势力平衡';
    const recommendedFaction = factionData.recommended_starting_faction || '未推荐';
    
    // 创建势力卡片HTML
    let factionsHtml = '';
    factions.forEach((faction, index) => {
        const factionType = faction.type || '未分类';
        const powerLevel = faction.power_level || '未知';
        const isRecommended = faction.suitable_for_protagonist === '是';
        
        factionsHtml += `
            <div class="faction-card ${isRecommended ? 'recommended' : ''}"
                 style="animation-delay: ${index * 0.1}s"
                 data-faction-index="${index}">
                ${isRecommended ? '<div class="recommended-badge">⭐ 推荐主角加入</div>' : ''}
                <div class="faction-header">
                    <div class="faction-name">${faction.name}</div>
                    <div class="faction-type-badge">${factionType}</div>
                </div>
                <div class="faction-info faction-info-collapsed" id="faction-info-${index}">
                    <div class="info-row">
                        <span class="info-label">势力等级</span>
                        <span class="info-value power-level-${powerLevel}">${powerLevel}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">核心理念</span>
                        <span class="info-value philosophy-preview">${faction.core_philosophy || '未设置'}</span>
                    </div>
                    <div class="info-row expand-hint" onclick="toggleFactionDetails(${index}, event)">
                        <span class="info-value">点击查看详细信息 ↓</span>
                    </div>
                    <div class="faction-details-expanded" id="faction-details-${index}" style="display: none;">
                        <div class="info-row">
                            <span class="info-label">势力背景</span>
                            <span class="info-value">${faction.background || '未设置'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">优势</span>
                            <span class="info-value">${(faction.strengths || []).slice(0, 3).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">劣势</span>
                            <span class="info-value">${(faction.weaknesses || []).slice(0, 3).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">盟友势力</span>
                            <span class="info-value allies">${(faction.relationships?.allies || []).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">敌对势力</span>
                            <span class="info-value enemies">${(faction.relationships?.enemies || []).join('、') || '无'}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">剧情作用</span>
                            <span class="info-value">${faction.role_in_plot || '未设置'}</span>
                        </div>
                        <div class="info-row collapse-hint" onclick="toggleFactionDetails(${index}, event)">
                            <span class="info-value">点击收起 ↑</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    const modalHtml = `
        <div id="faction-system-modal" class="faction-modal" onclick="closeFactionModal(event)">
            <div class="faction-modal-content" onclick="event.stopPropagation()">
                <div class="faction-modal-header" id="modal-header">
                    <div class="header-icon">⚔️</div>
                    <div class="header-text">
                        <h2>势力/阵营系统</h2>
                        <p>查看和管理世界中的各个势力及其关系</p>
                    </div>
                    <button class="close-btn" onclick="closeFactionModal()">×</button>
                </div>
                
                <div id="faction-list-view">
                    <div class="faction-overview">
                        <div class="overview-card">
                            <div class="overview-icon">⚡</div>
                            <div class="overview-content">
                                <div class="overview-label">主要冲突</div>
                                <div class="overview-value">${mainConflict}</div>
                            </div>
                        </div>
                        <div class="overview-card">
                            <div class="overview-icon">⚖️</div>
                            <div class="overview-content">
                                <div class="overview-label">势力平衡</div>
                                <div class="overview-value">${powerBalance}</div>
                            </div>
                        </div>
                        <div class="overview-card">
                            <div class="overview-icon">🎯</div>
                            <div class="overview-content">
                                <div class="overview-label">推荐势力</div>
                                <div class="overview-value">${recommendedFaction}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="factions-grid-container">
                        <div class="factions-grid">
                            ${factionsHtml}
                        </div>
                    </div>
                    
                    <div class="faction-modal-footer">
                        <button class="btn btn-secondary" onclick="closeFactionModal()">关闭</button>
                    </div>
                </div>
                
                <div id="faction-detail-view" class="faction-detail-view"></div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 动态设置滚动容器的高度
    setTimeout(() => {
        const modalContent = document.querySelector('.faction-modal-content');
        const listView = document.getElementById('faction-list-view');
        const gridContainer = document.querySelector('.factions-grid-container');
        
        if (modalContent && listView && gridContainer) {
            // 计算可用空间
            const headerHeight = document.querySelector('.faction-modal-header').offsetHeight;
            const overviewHeight = document.querySelector('.faction-overview').offsetHeight;
            const footerHeight = document.querySelector('.faction-modal-footer').offsetHeight;
            
            // 计算网格容器的高度
            const availableHeight = modalContent.offsetHeight - headerHeight - overviewHeight - footerHeight - 32; // 32px for margins
            
            // 设置高度
            gridContainer.style.height = `${availableHeight}px`;
            console.log('📏 势力网格容器高度已设置为:', availableHeight + 'px');
        }
    }, 100);
}

// 展开/收起势力详情
function toggleFactionDetails(index, event) {
    event.stopPropagation();
    
    const factionInfo = document.getElementById(`faction-info-${index}`);
    const expandedDetails = document.getElementById(`faction-details-${index}`);
    const expandHint = factionInfo.querySelector('.expand-hint');
    
    if (!expandedDetails || !factionInfo) return;
    
    if (expandedDetails.style.display === 'none') {
        // 展开详情
        expandedDetails.style.display = 'block';
        factionInfo.classList.remove('faction-info-collapsed');
        factionInfo.classList.add('faction-info-expanded');
        if (expandHint) {
            expandHint.style.display = 'none';
        }
    } else {
        // 收起详情
        expandedDetails.style.display = 'none';
        factionInfo.classList.remove('faction-info-expanded');
        factionInfo.classList.add('faction-info-collapsed');
        if (expandHint) {
            expandHint.style.display = 'flex';
        }
    }
}

// 显示势力详情（全屏详情视图，保留用于其他需要的地方）
function showFactionDetail(index) {
    if (!currentFactionsData || !currentFactionsData.factions) return;
    
    const faction = currentFactionsData.factions[index];
    if (!faction) return;
    
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏列表视图
    if (listView) listView.style.display = 'none';
    
    // 更新头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = faction.name;
        modalHeader.querySelector('.header-text p').textContent = faction.type || '未分类';
    }
    
    // 获取势力信息
    const powerLevel = faction.power_level || '未知';
    const strengths = (faction.strengths || []).join('、') || '无';
    const weaknesses = (faction.weaknesses || []).join('、') || '无';
    const allies = (faction.relationships?.allies || []).join('、') || '无';
    const enemies = (faction.relationships?.enemies || []).join('、') || '无';
    const territory = faction.territory || '未设置';
    const goals = (faction.goals || []).join('、') || '未设置';
    
    // 渲染详情视图
    if (detailView) {
        detailView.innerHTML = `
            <button class="detail-back-btn" onclick="hideFactionDetail()">
                <span>←</span>
                <span>返回列表</span>
            </button>
            
            <div class="detail-header">
                <div class="detail-header-content">
                    <h1 class="detail-name">${faction.name}</h1>
                    <div>
                        <span class="detail-type">${faction.type || '未分类'}</span>
                        <span class="detail-power-level">
                            <span>⚡</span>
                            <span>${powerLevel}</span>
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="detail-philosophy">
                "${faction.core_philosophy || '未设置核心理念'}"
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">📖</span>
                    <span>势力背景</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.background || '未设置背景信息'}</p>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🎯</span>
                    <span>势力目标</span>
                </h3>
                <div class="detail-section-content">
                    <p>${goals}</p>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🗺️</span>
                    <span>势力领地</span>
                </h3>
                <div class="detail-section-content">
                    <p>${territory}</p>
                </div>
            </div>
            
            <div class="detail-grid">
                <div class="detail-grid-item">
                    <div class="detail-grid-label">优势</div>
                    <div class="detail-grid-value">${strengths}</div>
                </div>
                <div class="detail-grid-item">
                    <div class="detail-grid-label">劣势</div>
                    <div class="detail-grid-value">${weaknesses}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🤝</span>
                    <span>势力关系</span>
                </h3>
                <div class="detail-grid">
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">盟友势力</div>
                        <div class="detail-grid-value allies">${allies}</div>
                    </div>
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">敌对势力</div>
                        <div class="detail-grid-value enemies">${enemies}</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🎬</span>
                    <span>剧情作用</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.role_in_plot || '未设置剧情作用'}</p>
                </div>
            </div>
            
            ${faction.suitable_for_protagonist === '是' ? `
                <div class="detail-section" style="background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-color: var(--primary-color);">
                    <h3 class="detail-section-title">
                        <span class="detail-section-icon">⭐</span>
                        <span>主角推荐</span>
                    </h3>
                    <div class="detail-section-content">
                        <p style="color: var(--primary-light); font-weight: 600;">此势力推荐作为主角的初始势力</p>
                    </div>
                </div>
            ` : ''}
        `;
        
        detailView.classList.add('active');
    }
}

// 隐藏势力详情
function hideFactionDetail() {
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏详情视图
    if (detailView) {
        detailView.classList.remove('active');
    }
    
    // 恢复头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = '势力/阵营系统';
        modalHeader.querySelector('.header-text p').textContent = '查看和管理世界中的各个势力及其关系';
    }
    
    // 显示列表视图
    if (listView) listView.style.display = 'block';
}

function closeFactionModal(event) {
    // 如果没有事件对象，或者点击的是模态框背景，则关闭
    if (!event || event.target.id === 'faction-system-modal' || event.target.classList.contains('close-btn')) {
        const modal = document.getElementById('faction-system-modal');
        if (modal) {
            modal.classList.add('closing');
            setTimeout(() => modal.remove(), 300);
        }
    }
}

// 跳转到项目可视化界面
function viewProjectViewer() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到项目可视化界面
    window.location.href = `/project-viewer/${encodeURIComponent(projectTitle)}`;
}

// 跳转到世界观可视化界面
function viewWorldviewViewer() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到世界观可视化界面
    window.location.href = `/worldview-viewer/${encodeURIComponent(projectTitle)}`;
}

function createProductEditModal(category, productData) {
    const categoryNames = {
        'worldview': '世界观设定',
        'characters': '角色设计',
        'growth': '成长路线',
        'writing': '写作计划',
        'storyline': '故事线',
        'market': '市场分析'
    };

    const categoryIcons = {
        'worldview': '🌍',
        'characters': '👥',
        'growth': '📈',
        'writing': '📝',
        'storyline': '📖',
        'market': '📊'
    };

    const modalHtml = `
        <div id="product-edit-modal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 999999; backdrop-filter: blur(4px); display: flex; justify-content: center; align-items: center;">
            <div style="position: relative; background: white; border-radius: 16px; box-shadow: 0 25px 80px rgba(0,0,0,0.4); max-width: 900px; width: 90vw; max-height: 85vh; overflow: hidden; border: 1px solid rgba(255,255,255,0.2);">
                <!-- 头部 -->
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 32px; display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        <div style="width: 40px; height: 40px; background: rgba(255,255,255,0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px;">${categoryIcons[category]}</div>
                        <div>
                            <h3 style="margin: 0; font-size: 22px; font-weight: 700;">编辑${categoryNames[category]}</h3>
                            <p style="margin: 4px 0 0 0; font-size: 14px; opacity: 0.9;">修改和完善${categoryNames[category]}内容</p>
                        </div>
                    </div>
                    <div style="display: flex; gap: 12px; align-items: center;">
                        <button type="button" onclick="saveProductEdit('${category}')" style="background: rgba(255,255,255,0.25); color: white; border: 1px solid rgba(255,255,255,0.35); padding: 10px 20px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.2s;">💾 保存</button>
                        <button type="button" onclick="closeProductEditModal()" style="background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); font-size: 20px; cursor: pointer; padding: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 8px; transition: all 0.2s;">×</button>
                    </div>
                </div>
                
                <!-- 内容区域 -->
                <div style="padding: 32px; overflow-y: auto; max-height: calc(85vh - 100px); background: #fafbfc;">
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151; font-size: 14px;">标题</label>
                        <input type="text" id="product-title" value="${productData?.title || categoryNames[category]}" style="width: 100%; padding: 14px 16px; border: 2px solid #e5e7eb; border-radius: 10px; font-size: 15px; background: white; color: #1f2937; transition: all 0.2s; font-weight: 500; box-sizing: border-box;">
                    </div>
                    
                    <div style="margin-bottom: 20px;">
                        <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151; font-size: 14px;">内容</label>
                        <textarea id="product-content" rows="20" style="width: 100%; padding: 16px; border: 2px solid #e5e7eb; border-radius: 10px; font-size: 15px; background: white; color: #1f2937; resize: vertical; min-height: 400px; transition: all 0.2s; font-family: inherit; line-height: 1.6; box-sizing: border-box;">${productData?.content || ''}</textarea>
                    </div>
                    
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="color: #6b7280; font-size: 14px;">💡 提示：详细的内容有助于生成更高质量的小说章节</span>
                        <span id="product-char-count" style="color: #9ca3af; font-size: 13px; font-weight: 500;">${(productData?.content || '').length} 字符</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // 添加字符计数功能
    const contentTextarea = document.getElementById('product-content');
    const charCountSpan = document.getElementById('product-char-count');
    
    if (contentTextarea && charCountSpan) {
        contentTextarea.addEventListener('input', function() {
            charCountSpan.textContent = this.value.length + ' 字符';
        });
    }
}

async function saveProductEdit(category) {
    try {
        const title = document.getElementById('product-title').value.trim();
        const content = document.getElementById('product-content').value.trim();
        
        if (!title || !content) {
            alert('请填写完整的标题和内容');
            return;
        }

        showStatusMessage('🔄 正在保存...', 'info');
        
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(currentProject.novel_title || currentProject.title)}/${category}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                title: title,
                content: content
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // 更新本地数据
            phaseOneProductsData[category] = {
                title: title,
                content: content,
                complete: true
            };
            
            // 更新显示状态
            updateProductsDisplay();
            
            closeProductEditModal();
            showStatusMessage('✅ 保存成功', 'success');
        } else {
            throw new Error(result.error || '保存失败');
        }
    } catch (error) {
        console.error('保存产物失败:', error);
        showStatusMessage(`❌ 保存失败: ${error.message}`, 'error');
    }
}

function closeProductEditModal() {
    const modal = document.getElementById('product-edit-modal');
    if (modal) {
        modal.remove();
    }
}

function refreshPhaseOneProducts() {
    loadPhaseOneProducts();
}

async function exportPhaseOneProducts() {
    if (!currentProject) {
        // 🔥 移除多余弹窗 - 只保留日志
        addLogEntry('error', '请先选择一个项目');
        return;
    }

    try {
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(currentProject.novel_title || currentProject.title)}/export`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `${currentProject.novel_title || currentProject.title}_第一阶段产物.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showStatusMessage('✅ 产物导出成功', 'success');
    } catch (error) {
        console.error('导出产物失败:', error);
        showStatusMessage(`❌ 导出失败: ${error.message}`, 'error');
    }
}

function validatePhaseOneProducts() {
    const categories = ['worldview', 'characters', 'growth', 'writing', 'storyline'];
    let completedCount = 0;
    let totalCount = categories.length;
    
    categories.forEach(category => {
        if (phaseOneProductsData[category] && phaseOneProductsData[category].content) {
            completedCount++;
        }
    });
    
    const percentage = Math.round((completedCount / totalCount) * 100);
    
    if (percentage === 100) {
        showStatusMessage('✅ 所有产物都已完成，可以开始章节生成', 'success');
    } else if (percentage >= 80) {
        showStatusMessage(`⚠️ 产物完成度 ${percentage}%，建议完善后再开始生成`, 'info');
    } else {
        showStatusMessage(`❌ 产物完成度仅 ${percentage}%，请先完善基本设定`, 'error');
    }
}

// ==================== 故事线跳转功能 ====================

function goToStorylinePage() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    
    const projectTitle = currentProject.novel_title || currentProject.title;
    if (!projectTitle) {
        showStatusMessage('❌ 无法获取项目标题', 'error');
        return;
    }
    
    // 跳转到故事线页面，并传递项目标题作为参数
    window.location.href = `/storyline?title=${encodeURIComponent(projectTitle)}`;
}

// ==================== 第二阶段生成功能 ====================
async function startPhaseTwoGeneration(event) {
    event.preventDefault();

    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    const formData = {
        from_chapter: parseInt(document.getElementById('from-chapter').value),
        chapters_to_generate: parseInt(document.getElementById('chapters-to-generate').value),
        chapters_per_batch: parseInt(document.getElementById('chapters-per-batch').value),
        generation_notes: document.getElementById('generation-notes').value
    };

    try {
        // 显示进度区域
        showProgressSection();
        hideGenerationForm();
        updateProgress(5, '正在启动第二阶段生成...');
        generationStartTime = Date.now();
        
        addLogEntry('info', `开始生成章节: 第${formData.from_chapter}章开始，生成${formData.chapters_to_generate}章`);

        // 调用第二阶段生成API
        const response = await fetch('/api/phase-two/start-generation', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                novel_title: currentProject.novel_title,
                ...formData
            })
        });

        if (response.status === 401) {
            showStatusMessage('❌ 请先登录后再试', 'error');
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            return;
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.success) {
            currentTaskId = result.task_id;
            updateStepStatus('generation', true);
            startProgressMonitoring();
            showControlButtons('generating');
            addLogEntry('success', `生成任务已启动: ${result.task_id}`);
        } else {
            throw new Error(result.error || '启动生成失败');
        }
    } catch (error) {
        hideProgressSection();
        showGenerationForm();
        showStatusMessage(`❌ 错误: ${error.message}`, 'error');
        addLogEntry('error', `启动生成失败: ${error.message}`);
        console.error('第二阶段生成失败:', error);
    }
}

function startProgressMonitoring() {
    if (!currentTaskId) return;
    
    // 初始化章节进度卡片
    initializeChapterProgress();
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/phase-two/task/${currentTaskId}/status`);
            if (!response.ok) return;

            const taskStatus = await response.json();
            updateProgress(taskStatus.progress || 0, taskStatus.status_message || '生成中...');
            updateChapterProgress(taskStatus);
            updateCurrentChapterInfo(taskStatus);

            // 检查是否完成
            if (taskStatus.status === 'completed') {
                clearInterval(progressInterval);
                handleGenerationComplete(taskStatus);
            } else if (taskStatus.status === 'failed' || taskStatus.status === 'paused') {
                clearInterval(progressInterval);
                handleGenerationStopped(taskStatus);
            }
        } catch (error) {
            console.error('获取进度状态失败:', error);
            addLogEntry('error', `获取进度失败: ${error.message}`);
        }
    }, 5000); // 每5秒检查一次
}

function initializeChapterProgress() {
    const fromChapter = parseInt(document.getElementById('from-chapter').value);
    const chaptersToGenerate = parseInt(document.getElementById('chapters-to-generate').value);
    const grid = document.getElementById('chapter-progress-grid');
    
    let html = '';
    for (let i = 0; i < chaptersToGenerate; i++) {
        const chapterNumber = fromChapter + i;
        html += `
            <div class="chapter-card" id="chapter-${chapterNumber}">
                <div class="chapter-number">第${chapterNumber}章</div>
                <div class="chapter-title">等待生成...</div>
                <div class="chapter-status pending">等待中</div>
            </div>
        `;
    }
    
    grid.innerHTML = html;
}

function updateChapterProgress(taskStatus) {
    if (!taskStatus.chapter_progress) return;
    
    taskStatus.chapter_progress.forEach(chapter => {
        const chapterCard = document.getElementById(`chapter-${chapter.chapter_number}`);
        if (chapterCard) {
            // 更新状态
            chapterCard.className = `chapter-card ${chapter.status}`;
            
            // 更新标题
            const titleElement = chapterCard.querySelector('.chapter-title');
            if (titleElement) {
                titleElement.textContent = chapter.chapter_title || `第${chapter.chapter_number}章`;
            }
            
            // 更新状态显示
            const statusElement = chapterCard.querySelector('.chapter-status');
            if (statusElement) {
                statusElement.className = `chapter-status ${chapter.status}`;
                statusElement.textContent = getStatusText(chapter.status);
            }
            
            // 更新字数
            let wordCountElement = chapterCard.querySelector('.chapter-word-count');
            if (!wordCountElement && chapter.word_count) {
                wordCountElement = document.createElement('div');
                wordCountElement.className = 'chapter-word-count';
                titleElement.parentNode.insertBefore(wordCountElement, statusElement);
            }
            if (wordCountElement) {
                wordCountElement.textContent = `${chapter.word_count || 0} 字`;
            }
            
            // 更新日志
            if (chapter.status === 'completed') {
                addLogEntry('success', `第${chapter.chapter_number}章生成完成: ${chapter.chapter_title}`);
            } else if (chapter.status === 'failed') {
                addLogEntry('error', `第${chapter.chapter_number}章生成失败: ${chapter.error || '未知错误'}`);
            }
        }
    });
}

function updateCurrentChapterInfo(taskStatus) {
    const infoDiv = document.getElementById('current-chapter-info');
    const currentChapter = taskStatus.current_chapter;
    
    if (currentChapter) {
        infoDiv.style.display = 'block';
        document.getElementById('current-chapter-title').textContent = currentChapter.title || `第${currentChapter.number}章`;
        document.getElementById('current-chapter-number').textContent = currentChapter.number;
        document.getElementById('total-chapters').textContent = taskStatus.total_chapters || 0;
    }
}

function getStatusText(status) {
    const statusMap = {
        'pending': '等待中',
        'generating': '生成中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

function handleGenerationComplete(taskStatus) {
    hideProgressSection();
    updateStepStatus('review', true);
    showGenerationResults(taskStatus);
    addLogEntry('success', '章节生成任务完成！');
    showStatusMessage('🎉 章节生成完成！', 'success');
}

function handleGenerationStopped(taskStatus) {
    showControlButtons('stopped');
    addLogEntry('warning', `生成已${taskStatus.status === 'paused' ? '暂停' : '停止'}`);
    showStatusMessage(`⚠️ 生成已${taskStatus.status === 'paused' ? '暂停' : '停止'}`, 'info');
}

function showGenerationResults(taskStatus) {
    const resultsDiv = document.getElementById('generation-results');
    resultsDiv.style.display = 'block';
    
    // 更新统计信息
    const generatedChapters = taskStatus.generated_chapters || [];
    const totalWords = generatedChapters.reduce((sum, chapter) => sum + (chapter.word_count || 0), 0);
    const avgScore = generatedChapters.reduce((sum, chapter) => sum + (chapter.quality_score || 0), 0) / generatedChapters.length;
    const generationTime = generationStartTime ? Math.round((Date.now() - generationStartTime) / 60000) : 0;
    
    document.getElementById('total-generated').textContent = generatedChapters.length;
    document.getElementById('total-words').textContent = totalWords.toLocaleString();
    document.getElementById('average-score').textContent = avgScore.toFixed(1);
    document.getElementById('generation-time').textContent = `${generationTime}分钟`;
}

// ==================== 控制功能 ====================
function pauseGeneration() {
    // 暂停功能需要后端支持
    showStatusMessage('⏸️ 暂停功能开发中...', 'info');
}

function resumeGeneration() {
    // 恢复功能需要后端支持
    showStatusMessage('▶️ 恢复功能开发中...', 'info');
}

function stopGeneration() {
    if (!currentTaskId) return;
    
    if (confirm('确定要停止当前生成任务吗？已生成的章节将被保留。')) {
        // 停止功能需要后端支持
        showStatusMessage('⏹️ 停止功能开发中...', 'info');
    }
}

function viewChapters() {
    if (!currentProject) return;
    window.location.href = `/novel?title=${encodeURIComponent(currentProject.novel_title)}`;
}

function goToChapterView() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    const projectTitle = currentProject.novel_title || currentProject.title;
    window.location.href = `/chapter-view?title=${encodeURIComponent(projectTitle)}`;
}

function continueMoreChapters() {
    hideGenerationResults();
    showGenerationForm();
    showStatusMessage('📝 继续生成更多章节', 'info');
}

function goToReading() {
    if (!currentProject) return;
    window.location.href = `/novel?title=${encodeURIComponent(currentProject.novel_title)}`;
}

function goToNovelView() {
    if (!currentProject) {
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }
    const projectTitle = currentProject.novel_title || currentProject.title;
    window.location.href = `/novel?title=${encodeURIComponent(projectTitle)}`;
}

function goToContentReview() {
    console.log('📋 [DEBUG] goToContentReview函数被调用!!!');
    console.log('📋 [DEBUG] currentProject:', currentProject);
    
    try {
        let projectTitle = null;
    
    // 优先从currentProject获取
    if (currentProject) {
        projectTitle = currentProject.novel_title || currentProject.title;
        console.log('✅ 从currentProject获取到项目标题:', projectTitle);
    }
    
    // 如果currentProject没有，尝试从URL参数获取
    if (!projectTitle) {
        const urlParams = new URLSearchParams(window.location.search);
        const titleFromUrl = urlParams.get('title');
        if (titleFromUrl) {
            projectTitle = decodeURIComponent(titleFromUrl);
            console.log('✅ 从URL获取到项目标题:', projectTitle);
        }
    }
    
    // 如果还是没有，尝试从localStorage获取
    if (!projectTitle) {
        const storedProjectTitle = localStorage.getItem('selectedProjectTitle');
        if (storedProjectTitle) {
            projectTitle = storedProjectTitle;
            console.log('✅ 从localStorage获取到项目标题:', projectTitle);
        }
    }
    
    // 如果还是没有，提示用户选择项目
    if (!projectTitle) {
        showStatusMessage('⚠️ 请先在左侧列表选择一个项目', 'warning');
        showStatusMessage('💡 请先在左侧项目列表中点击选择一个项目', 'info');
        
        // 高亮显示项目列表
        const projectsList = document.getElementById('projects-list');
        if (projectsList) {
            projectsList.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // 闪烁效果提示
            projectsList.style.animation = 'highlight-pulse 2s ease-in-out 3';
        }
        return;
    }
    
        console.log('✅ [DEBUG] 准备跳转到内容审核页面');
        console.log('✅ [DEBUG] 项目标题:', projectTitle);
        
        if (!projectTitle) {
            console.error('❌ [DEBUG] 未能获取项目标题!');
            showStatusMessage('❌ 无法获取项目标题，请刷新页面重试', 'error');
            return;
        }
        
        console.log('🚀 [DEBUG] 执行跳转...');
        window.location.href = `/chapter-view?title=${encodeURIComponent(projectTitle)}`;
    } catch (error) {
        console.error('❌ [DEBUG] goToContentReview发生错误:', error);
        console.error('❌ [DEBUG] 错误堆栈:', error.stack);
        showStatusMessage(`❌ 跳转失败: ${error.message}`, 'error');
    }
}

// ==================== 工具函数 ====================
function showProgressSection() {
    document.getElementById('progress-section').classList.add('active');
    document.getElementById('generation-results').classList.remove('active');
}

function hideProgressSection() {
    document.getElementById('progress-section').classList.remove('active');
}

function showGenerationForm() {
    document.getElementById('phase-two-form').style.display = 'block';
}

function hideGenerationForm() {
    document.getElementById('phase-two-form').style.display = 'none';
}

function showGenerationResults() {
    hideProgressSection();
    document.getElementById('generation-results').classList.add('active');
    updateStepStatus('complete', true);
}

function hideGenerationResults() {
    document.getElementById('generation-results').classList.remove('active');
}

function updateProgress(percentage, message) {
    const progressBar = document.getElementById('progress-bar-fill');
    const percentageText = document.getElementById('progress-percentage');
    
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
    if (percentageText) {
        percentageText.textContent = `${percentage}%`;
    }
    
    addLogEntry('info', `进度: ${percentage}% - ${message}`);
}

function updateStepStatus(stepName, isActive) {
    const steps = ['setup', 'generation', 'review', 'complete'];
    const currentIndex = steps.indexOf(stepName);
    
    steps.forEach((step, index) => {
        const stepElement = document.getElementById(`step-${step}`);
        if (stepElement) {
            stepElement.classList.remove('active', 'completed');
            if (index < currentIndex) {
                stepElement.classList.add('completed');
            } else if (index === currentIndex && isActive) {
                stepElement.classList.add('active');
            } else {
                stepElement.classList.add('pending');
            }
        }
    });
}

function showControlButtons(state) {
    const startBtn = document.getElementById('start-btn');
    const pauseBtn = document.getElementById('pause-btn');
    const resumeBtn = document.getElementById('resume-btn');
    const stopBtn = document.getElementById('stop-btn');
    
    // 隐藏所有按钮
    [startBtn, pauseBtn, resumeBtn, stopBtn].forEach(btn => {
        if (btn) btn.style.display = 'none';
    });
    
    // 根据状态显示相应按钮
    if (state === 'generating') {
        if (pauseBtn) pauseBtn.style.display = 'inline-flex';
        if (stopBtn) stopBtn.style.display = 'inline-flex';
    } else if (state === 'stopped' || state === 'paused') {
        if (resumeBtn) resumeBtn.style.display = 'inline-flex';
        if (stopBtn) stopBtn.style.display = 'inline-flex';
    } else {
        if (startBtn) startBtn.style.display = 'inline-flex';
    }
}

function addLogEntry(level, message) {
    const logContainer = document.getElementById('generation-log');
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${level}`;
    logEntry.textContent = `[${timestamp}] ${message}`;
    
    logContainer.appendChild(logEntry);
    
    // 保持最新的50条日志
    const entries = logContainer.children;
    if (entries.length > 50) {
        logContainer.removeChild(entries[0]);
    }
    
    // 自动滚动到底部
    logContainer.scrollTop = logContainer.scrollHeight;
}

function showStatusMessage(message, type) {
    const msgElement = document.getElementById('status-message');
    msgElement.className = `status-message ${type}`;
    msgElement.textContent = message;
    msgElement.style.display = 'block';
    
    // 5秒后自动隐藏成功和消息
    if (type === 'success') {
        setTimeout(() => {
            msgElement.style.display = 'none';
        }, 5000);
    }
}

// 退出登录函数
function logout() {
    if (confirm('确定要退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// 页面卸载时清理定时器
window.addEventListener('beforeunload', function() {
    if (progressInterval) {
        clearInterval(progressInterval);
    }
});