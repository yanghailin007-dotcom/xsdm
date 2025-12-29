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
        const isPhaseOneCompleted = project.phase_one && project.phase_one.status === 'completed';
        const canGenerate = isPhaseOneCompleted && (!project.phase_two || project.phase_two.status !== 'completed');
        
        // 对标题进行HTML转义，避免特殊字符导致的问题
        const escapedTitle = project.title.replace(/'/g, "\\'").replace(/"/g, '\\"');
        
        // 如果可以生成，添加点击事件
        const onClickAttr = canGenerate ? `onclick="selectProject('${escapedTitle}')"` : '';
        const styleAttr = !canGenerate ? 'style="opacity: 0.6; cursor: not-allowed;"' : '';
        const disabledClass = !canGenerate ? 'disabled' : '';
        
        html += `
            <div class="project-card ${disabledClass}"
                 data-title="${escapedTitle}"
                 ${onClickAttr}
                 ${styleAttr}>
                <div class="project-title">${project.title}</div>
                <div class="project-info">总章节: ${project.total_chapters || 0}</div>
                <div class="project-info">已完成: ${project.completed_chapters || 0} 章</div>
                <div class="project-status ${canGenerate ? 'status-ready' : project.phase_one ? 'status-completed' : 'status-generating'}">
                    ${getProjectStatusText(project)}
                </div>
            </div>
        `;
    });
    
    projectsList.innerHTML = html;
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
        showStatusMessage(`✅ 已选择项目: ${projectTitle}`, 'success');
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
        fromChapter.min = completedChapters + 1;
        // 添加事件监听器
        fromChapter.removeEventListener('input', updateChapterRange);
        fromChapter.addEventListener('input', updateChapterRange);
    }
    
    if (chaptersToGenerate) {
        const remainingChapters = totalChapters - completedChapters;
        chaptersToGenerate.max = Math.min(remainingChapters, 200);
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
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    try {
        showStatusMessage('🔄 正在加载第一阶段产物...', 'info');
        
        const response = await fetch(`/api/phase-one/products/${encodeURIComponent(currentProject.novel_title || currentProject.title)}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        
        if (result.success) {
            phaseOneProductsData = result.products;
            updateProductsDisplay();
            showStatusMessage('✅ 第一阶段产物加载完成', 'success');
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

function updateProductsDisplay() {
    const categories = ['worldview', 'characters', 'growth', 'writing', 'storyline', 'market'];
    
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
        showStatusMessage('❌ 请先选择一个项目', 'error');
        return;
    }

    const productData = phaseOneProductsData[category];
    
    // 创建编辑模态框
    createProductEditModal(category, productData);
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
        showStatusMessage('❌ 请先选择一个项目', 'error');
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
    }, 2000); // 每2秒检查一次
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