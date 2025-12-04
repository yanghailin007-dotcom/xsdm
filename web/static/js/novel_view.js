/**
 * 小说阅读页面 - 前端逻辑
 * Novel View Page - Frontend Logic
 */

let currentChapter = 1;
let novelData = null;
let chaptersData = [];
let currentNovelTitle = null; // 当前小说标题

// 阅读模式相关变量
let isReadingMode = false; // 当前是否为阅读模式
let currentTheme = 'light'; // 当前阅读主题
let currentFontSize = 18; // 当前字体大小
let currentLineHeight = 1.8; // 当前行间距

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.log('初始化小说阅读页面...');

        // 从URL参数获取小说标题
        const urlParams = new URLSearchParams(window.location.search);
        const novelTitle = urlParams.get('title');

        if (!novelTitle) {
            showError('未指定小说标题，请从首页选择小说');
            return;
        }

        currentNovelTitle = novelTitle; // 设置当前小说标题

        // 加载指定小说的数据
        await loadNovelData(novelTitle);

        // 加载章节列表
        await loadChaptersList(novelTitle);

        // 加载第一章（如果存在）
        if (chaptersData.length > 0) {
            await loadChapter(novelTitle, chaptersData[0].chapter_number);
        }
    } catch (error) {
        console.error('初始化失败:', error);
        showError('页面初始化失败，请刷新重试');
    }
});

/**
 * 加载指定小说的数据
 */
async function loadNovelData(novelTitle) {
    try {
        const response = await fetch(`/api/project/${encodeURIComponent(novelTitle)}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('小说数据响应错误:', response.status, errorText);
            if (response.status === 404) {
                throw new Error('小说不存在');
            }
            throw new Error(`加载失败 (${response.status}): ${errorText}`);
        }

        novelData = await response.json();
        console.log('小说数据:', novelData);

        // 更新 UI
        const titleElement = document.getElementById('novel-title');
        const progressElement = document.getElementById('novel-progress');
        
        if (titleElement) {
            const title = novelData.novel_title ||
                        novelData.title ||
                        novelTitle;
            titleElement.textContent = title;
        }
        
        if (progressElement) {
            const totalChapters = novelData.total_chapters ||
                               novelData.chapter_index?.length ||
                               chaptersData.length ||
                               50;
            progressElement.textContent = `${chaptersData.length || 0}/${totalChapters}`;
        }
        // 更新核心设定
        const coreSettingElement = document.getElementById('core-setting');
        const coreSellingPointsElement = document.getElementById('core-selling-points');
        
        if (coreSettingElement) {
            const coreSetting = novelData.core_setting ||
                              novelData.novel_metadata?.coreSetting ||
                              novelData.creative_seed?.coreSetting ||
                              '暂无设定';
            coreSettingElement.textContent = coreSetting;
        }
        
        if (coreSellingPointsElement) {
            const sellingPoints = novelData.core_selling_points ||
                               novelData.novel_metadata?.coreSellingPoints ||
                               novelData.creative_seed?.coreSellingPoints ||
                               '';
            
            if (Array.isArray(sellingPoints)) {
                coreSellingPointsElement.textContent = sellingPoints.join(' • ');
            } else if (typeof sellingPoints === 'string') {
                coreSellingPointsElement.textContent = sellingPoints;
            } else {
                coreSellingPointsElement.textContent = '暂无卖点';
            }
        }

        // 更新页面标题
        document.title = `${novelData.novel_title || novelTitle} - 小说阅读页面`;

    } catch (error) {
        console.error('加载小说数据失败:', error);
        console.error('错误详情:', error.message, error.stack);
        throw error;
    }
}

/**
 * 加载章节列表
 */
async function loadChaptersList(novelTitle) {
    try {
        const response = await fetch(`/api/project/${encodeURIComponent(novelTitle)}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error('章节列表响应错误:', response.status, errorText);
            throw new Error(`加载失败 (${response.status}): ${errorText}`);
        }

        const novelProject = await response.json();
        const generatedChapters = novelProject.generated_chapters || {};

        // 将生成的章节转换为数组格式
        chaptersData = Object.values(generatedChapters).map(chapter => ({
            chapter_number: chapter.chapter_number,
            title: chapter.title || `第${chapter.chapter_number}章`,
            content: chapter.content,
            word_count: chapter.content ? chapter.content.length : 0,
            score: '-' // 暂时没有评分
        })).sort((a, b) => a.chapter_number - b.chapter_number);

        console.log('章节列表:', chaptersData);

        // 生成章节列表 HTML
        const listContainer = document.getElementById('chapters-list');

        if (chaptersData.length === 0) {
            listContainer.innerHTML = '<div style="text-align: center; color: #999;">暂无章节</div>';
            return;
        }

        listContainer.innerHTML = chaptersData.map(chapter => `
            <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
                 onclick="loadChapter('${novelTitle.replace(/'/g, "\\'")}', ${chapter.chapter_number})"
                 data-chapter="${chapter.chapter_number}">
                <div class="chapter-item-title">
                    第${chapter.chapter_number}章 ${chapter.title}
                </div>
                <div class="chapter-item-meta">
                    ${chapter.word_count} 字 • 评分: ${chapter.score || '-'}
                </div>
            </div>
        `).join('');

        // 初始化导航按钮
        updateNavigationButtons();

    } catch (error) {
        console.error('加载章节列表失败:', error);
        console.error('错误详情:', error.message, error.stack);
        throw error;
    }
}

/**
 * 加载特定章节
 */
async function loadChapter(novelTitle, chapterNum) {
    try {
        console.log('加载第', chapterNum, '章...');

        // 同时加载章节内容和质量数据
        const [chapterResponse, qualityResponse] = await Promise.all([
            fetch(`/api/project/${encodeURIComponent(novelTitle)}/chapter/${chapterNum}`),
            fetch(`/api/project/${encodeURIComponent(novelTitle)}/chapter/${chapterNum}/quality`)
        ]);

        if (!chapterResponse.ok) {
            const errorText = await chapterResponse.text();
            console.error('章节响应错误:', chapterResponse.status, errorText);
            throw new Error(`章节不存在 (${chapterResponse.status}): ${errorText}`);
        }

        const chapter = await chapterResponse.json();
        const qualityData = qualityResponse.ok ? await qualityResponse.json() : {};

        console.log('章节数据:', chapter);
        console.log('质量数据:', qualityData);

        currentChapter = chapterNum;

        // 更新活跃状态
        document.querySelectorAll('.chapter-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chapter == chapterNum) {
                item.classList.add('active');
            }
        });

        // 更新中间内容区
        updateCenterContent(chapter);

        // 更新右侧生成信息区
        updateGenerationInfoPanel(chapter, qualityData);

        // 更新导航按钮
        updateNavigationButtons();

    } catch (error) {
        console.error('加载章节失败:', error);
        console.error('错误详情:', error.message, error.stack);
        showError(`加载章节失败: ${error.message}`);
    }
}

/**
 * 更新中间内容区
 */
function updateCenterContent(chapter) {
    const title = chapter.title || `第${chapter.chapter_number}章`;
    const wordCount = chapter.content ? chapter.content.length : 0;
    const generatedTime = chapter.generated_at
        ? new Date(chapter.generated_at).toLocaleString('zh-CN')
        : '未知';

    // 更新标题和元信息
    document.getElementById('chapter-title').textContent = title;
    document.getElementById('chapter-meta').textContent =
        `${wordCount} 字 • 生成时间: ${generatedTime}`;

    // 更新内容（保留原始格式，包括特殊标记）
    const contentBody = document.getElementById('chapter-content');
    if (chapter.content) {
        // 直接使用内容，让CSS处理换行
        contentBody.innerHTML = `<div class="novel-content-raw">${escapeHtml(chapter.content)}</div>`;

        // 后处理特殊标记
        postProcessContent(contentBody);
    } else {
        contentBody.innerHTML = '<div style="text-align: center; color: #999; padding: 40px;">内容加载失败</div>';
    }

    // 记录字数
    document.getElementById('word-count').textContent = `${wordCount} 字`;
    document.getElementById('generated-time').textContent = generatedTime;
}

/**
 * 后处理内容，应用特殊格式（网络小说样式）
 */
function postProcessContent(container) {
    const contentDiv = container.querySelector('.novel-content-raw');
    if (!contentDiv) return;

    let html = contentDiv.textContent; // 获取纯文本内容

    // 确保换行符统一
    html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

    // 处理分隔线 "══" - 网络小说常见样式
    html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');

    // 处理特殊标记，使其更像网络小说风格
    html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');

    // 网络小说常见的段落处理：每两个换行符分成一个段落
    let paragraphs = html.split(/\n\s*\n/);
    let result = '<div class="novel-content">';

    for (let paragraph of paragraphs) {
        paragraph = paragraph.trim();
        if (paragraph) {
            // 处理段落内的单换行符，但保留段落结构
            paragraph = paragraph.replace(/\n/g, '<br>');
            result += `<p class="novel-text">${paragraph}</p>`;
        }
    }

    result += '</div>';
    contentDiv.innerHTML = result;
}

/**
 * 更新评估面板
 */
function updateAssessmentPanel(chapter) {
    const assessment = chapter.assessment || {};
    
    // 评分
    const score = assessment.score 
        || assessment.整体评分 
        || assessment['整体评分']
        || '-';
    
    document.getElementById('quality-score').textContent = 
        typeof score === 'number' ? score.toFixed(1) : score;
    
    // 评级
    const rating = assessment.rating 
        || assessment.评级
        || assessment['评级']
        || calculateRating(score);
    
    document.getElementById('quality-rating').textContent = rating;
    
    // 优点列表
    const pros = assessment.pros 
        || assessment.优点
        || assessment['优点']
        || [];
    
    const prosList = document.getElementById('pros-list');
    prosList.innerHTML = (Array.isArray(pros) && pros.length > 0)
        ? pros.map(p => `<li>${escapeHtml(p)}</li>`).join('')
        : '<li>暂无优点评价</li>';
    
    // 改进建议列表
    const cons = assessment.cons 
        || assessment.建议
        || assessment['改进建议']
        || assessment['改进建议']
        || [];
    
    const consList = document.getElementById('cons-list');
    consList.innerHTML = (Array.isArray(cons) && cons.length > 0)
        ? cons.map(c => `<li>${escapeHtml(c)}</li>`).join('')
        : '<li>暂无改进建议</li>';
}

/**
 * 更新生成信息面板
 */
function updateGenerationInfoPanel(chapter, qualityData) {
    console.log('更新生成信息面板...', qualityData);

    // 1. 更新输入提示词
    updateInputPrompts(chapter, qualityData);

    // 2. 更新AI输出响应
    updateAIResponses(chapter, qualityData);

    // 3. 更新质量评价
    updateQualityEvaluation(chapter, qualityData);

    // 4. 更新角色发展信息
    updateCharacterDevelopment(chapter, qualityData);

    // 5. 更新生成状态
    updateGenerationStatus(chapter, qualityData);
}

function updateInputPrompts(chapter, qualityData) {
    const container = document.getElementById('input-prompts');
    
    // 构建JSON数据段
    const jsonSections = [];

    // 1. 源文件信息
    if (chapter.file_path) {
        const fileInfo = {
            file_path: chapter.file_path,
            word_count: chapter.word_count || 0,
            chapter_number: chapter.chapter_number,
            title: chapter.title,
            generated_at: chapter.generated_at
        };
        
        jsonSections.push({
            title: `📄 源文件信息 (${chapter.word_count || 0}字)`,
            data: fileInfo,
            options: {
                id: 'source-file-info',
                icon: '📄',
                expanded: false,
                maxHeight: 200
            }
        });
    }

    // 2. 原始章节数据（异步加载）
    if (chapter.file_path) {
        jsonSections.push({
            title: `📋 原始章节JSON数据`,
            async: true,
            loadData: async () => {
                const response = await fetch(`/api/raw-chapter-data?file_path=${encodeURIComponent(chapter.file_path)}`);
                if (!response.ok) throw new Error('获取章节数据失败');
                return await response.json();
            },
            options: {
                id: 'raw-chapter-data',
                icon: '📋',
                expanded: false,
                maxHeight: 300,
                errorMessage: '获取原始章节数据失败',
                loadingText: '正在加载原始章节数据...'
            }
        });
    }

    // 3. 写作计划数据
    const writingPlan = qualityData.writing_plan || {};
    Object.keys(writingPlan).forEach(stageName => {
        if (writingPlan[stageName] && writingPlan[stageName].stage_writing_plan) {
            const planData = writingPlan[stageName].stage_writing_plan;
            const chapterRange = planData.chapter_range || '未知';
            const timestamp = planData.novel_metadata?.generation_timestamp ?
                new Date(planData.novel_metadata.generation_timestamp).toLocaleString() : '未知';
            
            jsonSections.push({
                title: `📝 ${stageName}计划 (${chapterRange})`,
                data: planData,
                options: {
                    id: `writing-plan-${stageName}`,
                    icon: '📝',
                    expanded: false,
                    maxHeight: 350
                }
            });
        }
    });

    // 4. 事件记录
    const events = qualityData.events || [];
    if (events.length > 0) {
        jsonSections.push({
            title: `📅 事件记录 (${events.length}条)`,
            data: events.slice(0, 20), // 限制显示数量
            options: {
                id: 'events-log',
                icon: '📅',
                expanded: false,
                maxHeight: 400
            }
        });
    }

    // 5. 角色关系数据
    const relationships = qualityData.character_relationships || {};
    if (Object.keys(relationships).length > 0) {
        jsonSections.push({
            title: `👥 角色关系数据 (${Object.keys(relationships).length}个角色)`,
            data: relationships,
            options: {
                id: 'character-relationships',
                icon: '👥',
                expanded: false,
                maxHeight: 300
            }
        });
    }

    // 生成HTML
    if (jsonSections.length > 0) {
        const html = jsonSections.map(section => {
            if (section.async && section.loadData) {
                return createAsyncExpandableJSON(section.title, section.loadData, section.options);
            } else {
                return createExpandableJSON(section.title, section.data, section.options);
            }
        }).join('');
        
        // 添加批量操作按钮
        const batchButtons = `
            <div style="display: flex; gap: 8px; margin-bottom: 12px; justify-content: center;">
                <button class="btn btn-secondary btn-small" onclick="expandAllJSONSections()" style="font-size: 10px; padding: 4px 8px;">
                    ▼ 全部展开
                </button>
                <button class="btn btn-secondary btn-small" onclick="collapseAllJSONSections()" style="font-size: 10px; padding: 4px 8px;">
                    ▲ 全部收起
                </button>
            </div>
        `;
        
        container.innerHTML = batchButtons + html;
    } else {
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 20px; font-size: 12px;">暂无输入信息</div>';
    }
}

function updateAIResponses(chapter, qualityData) {
    const container = document.getElementById('ai-responses');
    
    // 构建JSON数据段
    const jsonSections = [];

    // 1. 章节生成结果
    if (chapter.content) {
        const generationResult = {
            chapter_number: chapter.chapter_number,
            title: chapter.title,
            word_count: chapter.content.length,
            content_preview: chapter.content.substring(0, 500) + (chapter.content.length > 500 ? '...' : ''),
            generated_at: chapter.generated_at,
            file_path: chapter.file_path
        };
        
        jsonSections.push({
            title: `🤖 章节生成结果 (${chapter.content.length}字)`,
            data: generationResult,
            options: {
                id: 'generation-result',
                icon: '🤖',
                expanded: false,
                maxHeight: 250
            }
        });

        // 2. 完整章节内容
        jsonSections.push({
            title: `📝 完整章节内容`,
            data: {
                content: chapter.content,
                metadata: {
                    word_count: chapter.content.length,
                    chapter_number: chapter.chapter_number,
                    title: chapter.title,
                    generated_at: chapter.generated_at
                }
            },
            options: {
                id: 'full-chapter-content',
                icon: '📝',
                expanded: false,
                maxHeight: 400
            }
        });
    }

    // 3. 生成失败记录
    const failures = qualityData.chapter_failures || [];
    if (failures.length > 0) {
        const processedFailures = failures.map((failure, index) => ({
            序号: index + 1,
            失败时间: failure.failure_time,
            失败原因: failure.failure_reason,
            异常信息: failure.failure_details?.exception_message || '无',
            重试次数: failure.retry_count || 0,
            章节状态: failure.chapter_status || '未知'
        }));

        jsonSections.push({
            title: `❌ 生成失败记录 (${failures.length}次)`,
            data: processedFailures,
            options: {
                id: 'generation-failures',
                icon: '❌',
                expanded: false,
                maxHeight: 300
            }
        });
    }

    // 4. 生成上下文数据
    if (qualityData.generation_context) {
        jsonSections.push({
            title: `🎯 生成上下文`,
            data: qualityData.generation_context,
            options: {
                id: 'generation-context',
                icon: '🎯',
                expanded: false,
                maxHeight: 350
            }
        });
    }

    // 5. API调用记录（如果有的话）
    if (qualityData.api_calls && qualityData.api_calls.length > 0) {
        jsonSections.push({
            title: `🌐 API调用记录 (${qualityData.api_calls.length}次)`,
            data: qualityData.api_calls.slice(-10), // 只显示最近10次
            options: {
                id: 'api-calls-log',
                icon: '🌐',
                expanded: false,
                maxHeight: 400
            }
        });
    }

    // 生成HTML
    if (jsonSections.length > 0) {
        const html = jsonSections.map(section => {
            return createExpandableJSON(section.title, section.data, section.options);
        }).join('');
        
        container.innerHTML = html;
    } else {
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 20px; font-size: 12px;">暂无AI响应信息</div>';
    }
}

function updateQualityEvaluation(chapter, qualityData) {
    const container = document.getElementById('quality-evaluation');
    
    // 构建JSON数据段
    const jsonSections = [];

    // 1. 角色发展评估
    const characterDev = qualityData.character_development || {};
    const characterNames = Object.keys(characterDev);
    if (characterNames.length > 0) {
        const processedCharacters = {};
        characterNames.forEach(name => {
            const char = characterDev[name];
            processedCharacters[name] = {
                角色类型: char.role_type || '未知',
                重要性: char.importance || '未知',
                状态: char.status || '未知',
                属性: char.attributes || {},
                总出现次数: char.total_appearances || 0,
                首次登场章节: char.first_appearance_chapter || 0,
                最后更新章节: char.last_updated_chapter || 0,
                角色简介: char.description || '无'
            };
        });

        jsonSections.push({
            title: `👥 角色发展评估 (${characterNames.length}个角色)`,
            data: processedCharacters,
            options: {
                id: 'character-development',
                icon: '👥',
                expanded: false,
                maxHeight: 400
            }
        });
    }

    // 2. 世界观状态
    const worldState = qualityData.world_state || {};
    if (Object.keys(worldState).length > 0) {
        const processedWorldState = {
            世界状态记录: `${Object.keys(worldState).length} 项数据`,
            最后更新: worldState.last_updated || '未知',
            详细数据: worldState
        };

        jsonSections.push({
            title: `🌍 世界观状态 (${Object.keys(worldState).length}项)`,
            data: processedWorldState,
            options: {
                id: 'world-state',
                icon: '🌍',
                expanded: false,
                maxHeight: 350
            }
        });
    }

    // 3. 质量评估详情（如果有的话）
    if (chapter.assessment) {
        const assessment = chapter.assessment;
        const processedAssessment = {
            整体评分: assessment.score || assessment.整体评分 || assessment['整体评分'] || '未评分',
            评级: assessment.rating || assessment.评级 || assessment['评级'] || '未评级',
            优点: assessment.pros || assessment.优点 || assessment['优点'] || [],
            改进建议: assessment.cons || assessment.建议 || assessment['改进建议'] || assessment['改进建议'] || [],
            详细评估: assessment
        };

        jsonSections.push({
            title: `📊 章节质量评估`,
            data: processedAssessment,
            options: {
                id: 'quality-assessment',
                icon: '📊',
                expanded: false,
                maxHeight: 300
            }
        });
    }

    // 4. 事件详细记录
    const events = qualityData.events || [];
    if (events.length > 0) {
        const processedEvents = events.map((event, index) => ({
            序号: index + 1,
            事件类型: event.event_type || '未知',
            章节号: event.chapter_number || '未知',
            事件描述: event.description || event.event_description || '无',
            发生时间: event.timestamp || event.event_time || '未知',
            相关角色: event.involved_characters || [],
            事件影响: event.impact || '无'
        }));

        jsonSections.push({
            title: `📅 事件详细记录 (${events.length}个事件)`,
            data: processedEvents,
            options: {
                id: 'detailed-events',
                icon: '📅',
                expanded: false,
                maxHeight: 400
            }
        });
    }

    // 5. 写作质量指标
    const qualityMetrics = {
        章节字数: chapter.content ? chapter.content.length : 0,
        段落数量: chapter.content ? chapter.content.split(/\n\s*\n/).length : 0,
        生成时间: chapter.generated_at || '未知',
        文件大小: chapter.word_count || 0,
        生成状态: '已完成',
        数据完整性: {
            有内容: !!chapter.content,
            有标题: !!chapter.title,
            有章节号: !!chapter.chapter_number,
            有生成时间: !!chapter.generated_at,
            有文件路径: !!chapter.file_path
        }
    };

    jsonSections.push({
        title: `📈 写作质量指标`,
        data: qualityMetrics,
        options: {
            id: 'quality-metrics',
            icon: '📈',
            expanded: false,
            maxHeight: 250
        }
    });

    // 生成HTML
    if (jsonSections.length > 0) {
        const html = jsonSections.map(section => {
            return createExpandableJSON(section.title, section.data, section.options);
        }).join('');
        
        container.innerHTML = html;
    } else {
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 20px; font-size: 12px;">暂无质量评价信息</div>';
    }
}

function updateCharacterDevelopment(chapter, qualityData) {
    const container = document.getElementById('character-development');
    const characterDev = qualityData.character_development || {};
    const characterNames = Object.keys(characterDev);

    if (characterNames.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;">暂无角色发展信息</div>';
        return;
    }

    let html = '';
    characterNames.slice(0, 5).forEach(name => {
        const char = characterDev[name];
        const attributes = char.attributes || {};

        html += `<div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 10px; font-size: 12px;">
            <h6 style="margin: 0 0 8px 0; color: #333;">${name}</h6>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px;">
                <div><strong>类型:</strong> ${char.role_type || '未知'}</div>
                <div><strong>重要性:</strong> ${char.importance || '未知'}</div>
                <div><strong>状态:</strong> ${char.status || '未知'}</div>
                <div><strong>修为:</strong> ${attributes.cultivation_level || '未知'}</div>
                <div><strong>位置:</strong> ${attributes.location || '未知'}</div>
                <div><strong>灵石:</strong> ${attributes.money || '0'}</div>
            </div>
            <div style="margin-top: 8px; font-size: 10px; color: #666;">
                出现次数: ${char.total_appearances || 0} |
                首次登场: 第${char.first_appearance_chapter || 0}章 |
                最后更新: 第${char.last_updated_chapter || 0}章
            </div>
        </div>`;
    });

    if (characterNames.length > 5) {
        html += `<div style="text-align: center; color: #666; font-size: 11px;">...还有${characterNames.length - 5}个角色</div>`;
    }

    container.innerHTML = html;
}

function updateGenerationStatus(chapter, qualityData) {
    const container = document.getElementById('generation-status');
    let html = '';

    // 基本生成信息
    html += `<div style="margin-bottom: 10px;">
        <h5 style="color: #666; font-size: 12px; margin-bottom: 5px;">生成状态:</h5>
        <div style="background: #e8f5e8; padding: 8px; border-radius: 4px; font-size: 11px;">
            <strong>章节:</strong> 第${chapter.chapter_number}章<br>
            <strong>字数:</strong> ${chapter.content ? chapter.content.length : 0} 字<br>
            <strong>生成时间:</strong> ${chapter.generated_at ? new Date(chapter.generated_at).toLocaleString('zh-CN') : '未知'}<br>
            <strong>状态:</strong> <span style="color: #28a745;">✅ 已完成</span>
        </div>
    </div>`;

    // 失败状态
    const failures = qualityData.chapter_failures || [];
    if (failures.length > 0) {
        html += `<div>
            <h5 style="color: #666; font-size: 12px; margin-bottom: 5px;">失败记录:</h5>
            <div style="background: #f8d7da; padding: 8px; border-radius: 4px; font-size: 11px;">
                <strong>失败次数:</strong> ${failures.length} 次<br>
                <strong>最后失败:</strong> ${failures[failures.length - 1]?.failure_time || '未知'}<br>
                <strong>主要原因:</strong> ${failures[failures.length - 1]?.failure_reason || '未知'}
            </div>
        </div>`;
    }

    container.innerHTML = html;
}

/**
 * 根据评分计算评级
 */
function calculateRating(score) {
    if (typeof score !== 'number') return '未评估';
    if (score >= 9) return '优秀';
    if (score >= 8) return '很好';
    if (score >= 7) return '良好';
    if (score >= 6) return '及格';
    return '需改进';
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * 显示错误信息
 */
function showError(message) {
    const contentBody = document.getElementById('chapter-content');
    if (contentBody) {
        contentBody.innerHTML = `
            <div style="text-align: center; color: #dc3545; padding: 40px;">
                <div style="font-size: 24px; margin-bottom: 16px;">❌</div>
                <p>${escapeHtml(message)}</p>
                <div style="margin-top: 20px; font-size: 14px; color: #666;">
                    <details>
                        <summary>查看详细错误信息</summary>
                        <pre style="text-align: left; background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 10px;">${escapeHtml(message)}</pre>
                    </details>
                </div>
            </div>
        `;
    } else {
        // 如果contentBody不存在，使用alert作为备用
        alert(`错误: ${message}`);
    }
}

/**
 * 导出 JSON
 */
async function exportJSON() {
    try {
        const response = await fetch('/api/export-json');
        if (!response.ok) throw new Error('导出失败');
        
        const data = await response.json();
        
        // 生成 JSON 文件
        const filename = `novel_${data.novel.id}_${new Date().getTime()}.json`;
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        
        alert('✅ JSON 导出成功！');
    } catch (error) {
        console.error('导出失败:', error);
        alert('❌ 导出失败: ' + error.message);
    }
}

/**
 * 上一章
 */
function prevChapter() {
    const prevChapterData = chaptersData.find(c => c.chapter_number < currentChapter);
    if (prevChapterData) {
        loadChapter(currentNovelTitle, prevChapterData.chapter_number);
    }
}

/**
 * 下一章
 */
function nextChapter() {
    const nextChapterData = chaptersData.find(c => c.chapter_number > currentChapter);
    if (nextChapterData) {
        loadChapter(currentNovelTitle, nextChapterData.chapter_number);
    }
}

/**
 * 更新导航按钮状态
 */
function updateNavigationButtons() {
    const hasPrev = chaptersData.some(c => c.chapter_number < currentChapter);
    const hasNext = chaptersData.some(c => c.chapter_number > currentChapter);
    
    const prevBtn = document.getElementById('prev-chapter-btn');
    const nextBtn = document.getElementById('next-chapter-btn');
    const indicator = document.getElementById('chapter-indicator');
    
    // 按钮始终显示，根据状态启用/禁用
    prevBtn.style.display = 'block';
    nextBtn.style.display = 'block';
    
    // 设置启用/禁用状态和透明度
    if (hasPrev) {
        prevBtn.disabled = false;
        prevBtn.style.opacity = '1';
        prevBtn.style.cursor = 'pointer';
    } else {
        prevBtn.disabled = true;
        prevBtn.style.opacity = '0.5';
        prevBtn.style.cursor = 'not-allowed';
    }
    
    if (hasNext) {
        nextBtn.disabled = false;
        nextBtn.style.opacity = '1';
        nextBtn.style.cursor = 'pointer';
    } else {
        nextBtn.disabled = true;
        nextBtn.style.opacity = '0.5';
        nextBtn.style.cursor = 'not-allowed';
    }
    
    // 更新指示器
    if (indicator) {
        indicator.textContent = `第 ${currentChapter} 章`;
    }
}

// 键盘快捷键
document.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        // 上一章
        const prevChapter = chaptersData.find(c => c.chapter_number < currentChapter);
        if (prevChapter) loadChapter(currentNovelTitle, prevChapter.chapter_number);
    } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        // 下一章
        const nextChapter = chaptersData.find(c => c.chapter_number > currentChapter);
        if (nextChapter) loadChapter(currentNovelTitle, nextChapter.chapter_number);
    }
});

// 自动刷新进度
setInterval(async () => {
    try {
        const response = await fetch('/api/novel/summary');
        if (response.ok) {
            const data = await response.json();
            document.getElementById('novel-progress').textContent =
                `${data.chapters_count || 0}/${data.total_chapters || 50}`;
        }
    } catch (error) {
        // 静默处理
    }
}, 5000);

// ==================== 原始数据显示功能 ====================

/**
 * 显示模态窗口
 */
function showModal(title, content) {
    // 创建模态背景
    const modalOverlay = document.createElement('div');
    modalOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 20px;
    `;

    // 创建模态内容
    const modalContent = document.createElement('div');
    modalContent.style.cssText = `
        background: white;
        border-radius: 8px;
        max-width: 800px;
        max-height: 80vh;
        width: 90%;
        overflow: hidden;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
    `;

    modalContent.innerHTML = `
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 16px 20px; display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 0; font-size: 16px;">${title}</h3>
            <button onclick="closeModal(this)" style="background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">×</button>
        </div>
        <div style="padding: 20px; overflow-y: auto; max-height: calc(80vh - 60px);">
            <pre style="background: #f8f9fa; padding: 15px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.4; margin: 0;">${escapeHtml(content)}</pre>
        </div>
        <div style="padding: 15px 20px; border-top: 1px solid #eee; text-align: right;">
            <button onclick="closeModal(this)" style="background: #667eea; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;">关闭</button>
        </div>
    `;

    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);

    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            document.body.removeChild(modalOverlay);
        }
    });
}

/**
 * 关闭模态窗口
 */
function closeModal(button) {
    const modal = button.closest('div[style*="position: fixed"], div[style*="position:fixed"]');
    if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal);
    }
}

/**
 * 显示原始章节JSON数据
 */
async function showOriginalChapterData(chapterTitle, filePath) {
    try {
        const response = await fetch(`/api/raw-chapter-data?file_path=${encodeURIComponent(filePath)}`);
        if (!response.ok) throw new Error('获取章节数据失败');

        const data = await response.json();
        const content = JSON.stringify(data, null, 2);

        showModal(`📄 原始章节数据 - ${decodeURIComponent(chapterTitle)}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `获取章节数据失败: ${error.message}`);
    }
}

/**
 * 显示写作计划数据
 */
function showWritingPlan(stageName, planData) {
    try {
        const plan = JSON.parse(decodeURIComponent(planData));
        const content = JSON.stringify(plan, null, 2);

        showModal(`📋 写作计划 - ${stageName}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `解析写作计划数据失败: ${error.message}`);
    }
}

/**
 * 显示事件记录
 */
function showEventLog(title, eventData) {
    try {
        const events = JSON.parse(decodeURIComponent(eventData));
        const content = Array.isArray(events) ?
            JSON.stringify(events, null, 2) :
            JSON.stringify([events], null, 2);

        showModal(`📅 ${title}`, content);
    } catch (error) {
        showModal(`❌ 错误`, `解析事件记录失败: ${error.message}`);
    }
}

/**
 * 显示AI生成输出详情
 */
function showAIGenerationOutput(chapter) {
    const content = {
        chapter_number: chapter.chapter_number,
        title: chapter.title,
        content: chapter.content,
        word_count: chapter.content ? chapter.content.length : 0,
        generated_at: chapter.generated_at,
        file_path: chapter.file_path
    };

    const contentStr = JSON.stringify(content, null, 2);
    showModal(`🤖 AI生成输出 - 第${chapter.chapter_number}章`, contentStr);
}

/**
 * 显示质量评价详情
 */
function showQualityAssessment(qualityData) {
    const content = JSON.stringify(qualityData, null, 2);
    showModal(`📊 质量评价详情`, content);
}

/**
 * 显示角色发展数据
 */
function showCharacterDevelopment(characterData) {
    const content = JSON.stringify(characterData, null, 2);
    showModal(`👥 角色发展详情`, content);
}

// ==================== 可展开JSON组件功能 ====================

/**
 * 创建可展开的JSON组件
 */
function createExpandableJSON(title, data, options = {}) {
    const {
        id = null,
        icon = '📄',
        expanded = false,
        maxHeight = 600, // 增加默认高度
        syntaxHighlight = true,
        enableLargeModal = true // 添加大弹窗选项
    } = options;

    const componentId = id || `json-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 格式化JSON内容
    let formattedContent = '';
    let rawContent = '';
    if (data === null || data === undefined) {
        formattedContent = 'null';
        rawContent = 'null';
    } else if (typeof data === 'string') {
        try {
            // 尝试解析为JSON
            const parsed = JSON.parse(data);
            formattedContent = JSON.stringify(parsed, null, 2);
            rawContent = formattedContent;
        } catch (e) {
            // 如果不是JSON，直接显示字符串
            formattedContent = data;
            rawContent = data;
        }
    } else {
        formattedContent = JSON.stringify(data, null, 2);
        rawContent = formattedContent;
    }

    // 应用语法高亮
    if (syntaxHighlight) {
        formattedContent = highlightJSON(formattedContent);
    }

    // 创建展开按钮（如果启用大弹窗）
    const expandButton = enableLargeModal ? `
        <button class="btn-expand-large" onclick="showLargeJSONModal('${escapeHtml(title)}', '${escapeHtml(rawContent).replace(/'/g, "\\'").replace(/`/g, '\\`')}')" title="在大弹窗中查看">
            🔍 大窗口查看
        </button>
    ` : '';

    return `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header ${expanded ? 'expanded' : ''}" onclick="toggleJSONSection('${componentId}')">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${expandButton}
                    <div class="json-toggle">▼</div>
                </div>
            </div>
            <div class="json-content ${expanded ? 'expanded' : ''}" style="max-height: ${expanded ? maxHeight + 'px' : '0'}">
                <div class="json-body">${formattedContent}</div>
            </div>
        </div>
    `;
}

/**
 * 切换JSON组件展开/收起状态
 */
function toggleJSONSection(componentId) {
    const section = document.getElementById(componentId);
    if (!section) return;

    const header = section.querySelector('.json-header');
    const content = section.querySelector('.json-content');
    const toggle = section.querySelector('.json-toggle');

    const isExpanded = header.classList.contains('expanded');

    if (isExpanded) {
        // 收起
        header.classList.remove('expanded');
        content.classList.remove('expanded');
        content.style.maxHeight = '0';
        toggle.style.transform = 'rotate(0deg)';
    } else {
        // 展开
        header.classList.add('expanded');
        content.classList.add('expanded');
        content.style.maxHeight = content.scrollHeight + 'px';
        toggle.style.transform = 'rotate(180deg)';
    }
}

/**
 * JSON语法高亮
 */
function highlightJSON(jsonString) {
    return jsonString
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"(.*?)"\s*:/g, '<span class="json-key">"$1"</span>:')
        .replace(/:\s*"([^"]*)"/g, ': <span class="json-string">"$1"</span>')
        .replace(/:\s*(\d+)/g, ': <span class="json-number">$1</span>')
        .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
        .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
}

/**
 * 异步加载并创建可展开的JSON组件
 */
async function createAsyncExpandableJSON(title, loadFunction, options = {}) {
    const {
        id = null,
        icon = '📄',
        expanded = false,
        maxHeight = 400,
        errorMessage = '加载数据失败',
        loadingText = '正在加载数据...'
    } = options;

    const componentId = id || `json-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    // 初始显示加载状态
    let component = `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header ${expanded ? 'expanded' : ''}" onclick="toggleJSONSection('${componentId}')">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
                <div class="json-toggle">▼</div>
            </div>
            <div class="json-content ${expanded ? 'expanded' : ''}" style="max-height: ${expanded ? maxHeight + 'px' : '0'}">
                <div class="json-loading">${loadingText}</div>
            </div>
        </div>
    `;

    // 异步加载数据
    try {
        const data = await loadFunction();
        let content = '';
        
        if (data === null || data === undefined) {
            content = '<div class="json-empty">暂无数据</div>';
        } else {
            let formattedContent = '';
            if (typeof data === 'string') {
                try {
                    const parsed = JSON.parse(data);
                    formattedContent = JSON.stringify(parsed, null, 2);
                } catch (e) {
                    formattedContent = data;
                }
            } else {
                formattedContent = JSON.stringify(data, null, 2);
            }
            content = `<div class="json-body">${highlightJSON(formattedContent)}</div>`;
        }

        // 更新组件内容
        setTimeout(() => {
            const section = document.getElementById(componentId);
            if (section) {
                const contentDiv = section.querySelector('.json-content');
                if (contentDiv) {
                    contentDiv.innerHTML = content;
                }
            }
        }, 100);

    } catch (error) {
        console.error('加载JSON数据失败:', error);
        setTimeout(() => {
            const section = document.getElementById(componentId);
            if (section) {
                const contentDiv = section.querySelector('.json-content');
                if (contentDiv) {
                    contentDiv.innerHTML = `<div class="json-error">${errorMessage}: ${error.message}</div>`;
                }
            }
        }, 100);
    }

    return component;
}

/**
 * 创建多个可展开的JSON组件
 */
function createMultipleExpandableJSON(sections) {
    return sections.map(section => {
        if (section.async && section.loadData) {
            return createAsyncExpandableJSON(section.title, section.loadData, section.options);
        } else {
            return createExpandableJSON(section.title, section.data, section.options);
        }
    }).join('');
}

/**
 * 批量展开/收起所有JSON组件
 */
function toggleAllJSONSections(expand = true) {
    const sections = document.querySelectorAll('.expandable-json-section');
    sections.forEach(section => {
        const header = section.querySelector('.json-header');
        const content = section.querySelector('.json-content');
        const toggle = section.querySelector('.json-toggle');

        if (expand) {
            header.classList.add('expanded');
            content.classList.add('expanded');
            content.style.maxHeight = content.scrollHeight + 'px';
            toggle.style.transform = 'rotate(180deg)';
        } else {
            header.classList.remove('expanded');
            content.classList.remove('expanded');
            content.style.maxHeight = '0';
            toggle.style.transform = 'rotate(0deg)';
        }
    });
}

// ==================== 大弹窗功能 ====================

/**
 * 显示大JSON弹窗
 */
function showLargeJSONModal(title, content) {
    // 创建模态背景
    const modalOverlay = document.createElement('div');
    modalOverlay.className = 'modal-overlay';
    modalOverlay.id = 'large-json-modal';

    // 创建模态内容
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-large';

    // 格式化JSON内容
    let formattedContent = content;
    try {
        const parsed = JSON.parse(content);
        formattedContent = JSON.stringify(parsed, null, 2);
    } catch (e) {
        // 如果不是JSON，保持原样
    }

    // 应用语法高亮
    const highlightedContent = highlightJSON(formattedContent);

    modalContent.innerHTML = `
        <div class="modal-header">
            <h3>${title}</h3>
            <button class="modal-close-btn" onclick="closeLargeJSONModal()">×</button>
        </div>
        <div class="modal-body">
            <div class="data-display-container">
                <div class="data-display-header">
                    <div class="data-display-title">
                        <span>📄</span>
                        <span>JSON 数据内容</span>
                    </div>
                    <div class="data-display-actions">
                        <button class="btn btn-secondary btn-small" onclick="copyJSONContent('${escapeHtml(formattedContent).replace(/'/g, "\\'")}')">
                            📋 复制内容
                        </button>
                        <button class="btn btn-secondary btn-small" onclick="downloadJSONContent('${escapeHtml(title).replace(/'/g, "\\'")}', '${escapeHtml(formattedContent).replace(/'/g, "\\'")}')">
                            💾 下载文件
                        </button>
                    </div>
                </div>
                <div class="modal-json-display">${highlightedContent}</div>
            </div>
        </div>
        <div class="modal-footer">
            <button class="btn btn-primary" onclick="closeLargeJSONModal()">关闭</button>
        </div>
    `;

    modalOverlay.appendChild(modalContent);
    document.body.appendChild(modalOverlay);

    // 点击背景关闭
    modalOverlay.addEventListener('click', (e) => {
        if (e.target === modalOverlay) {
            closeLargeJSONModal();
        }
    });

    // ESC键关闭
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeLargeJSONModal();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}

/**
 * 关闭大JSON弹窗
 */
function closeLargeJSONModal() {
    const modal = document.getElementById('large-json-modal');
    if (modal && modal.parentNode) {
        modal.parentNode.removeChild(modal);
    }
}

/**
 * 复制JSON内容到剪贴板
 */
async function copyJSONContent(content) {
    try {
        await navigator.clipboard.writeText(content);
        showNotification('✅ 内容已复制到剪贴板');
    } catch (error) {
        console.error('复制失败:', error);
        showNotification('❌ 复制失败，请手动选择复制');
    }
}

/**
 * 下载JSON内容为文件
 */
function downloadJSONContent(title, content) {
    try {
        const blob = new Blob([content], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${title.replace(/[^\w\u4e00-\u9fa5]/g, '_')}_${new Date().getTime()}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        showNotification('✅ 文件下载成功');
    } catch (error) {
        console.error('下载失败:', error);
        showNotification('❌ 下载失败，请重试');
    }
}

/**
 * 显示通知消息
 */
function showNotification(message, duration = 3000) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: rgba(0, 212, 255, 0.9);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10001;
        font-size: 14px;
        font-weight: 600;
        backdrop-filter: blur(10px);
        animation: slideInRight 0.3s ease-out;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // 自动移除
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }
    }, duration);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);

/**
 * 展开所有JSON组件
 */
function expandAllJSONSections() {
    toggleAllJSONSections(true);
}

/**
 * 收起所有JSON组件
 */
function collapseAllJSONSections() {
    toggleAllJSONSections(false);
}

// ==================== 阅读模式功能 ====================

/**
 * 切换阅读模式/调试模式
 */
function toggleReadingMode() {
    isReadingMode = !isReadingMode;
    const debugLayout = document.getElementById('debug-layout');
    const readingLayout = document.getElementById('reading-layout');
    const modeToggleBtn = document.getElementById('mode-toggle-btn');
    const modeText = document.getElementById('mode-text');
    const readingSettingsBtn = document.getElementById('reading-settings-btn');
    const exportJsonBtn = document.getElementById('export-json-btn');
    const printBtn = document.getElementById('print-btn');
    
    if (isReadingMode) {
        // 切换到阅读模式
        debugLayout.style.display = 'none';
        readingLayout.style.display = 'block';
        modeText.textContent = '🔧 调试模式';
        readingSettingsBtn.style.display = 'inline-block';
        exportJsonBtn.style.display = 'none';
        printBtn.style.display = 'none';
        
        // 初始化阅读模式界面
        initReadingMode();
    } else {
        // 切换到调试模式
        debugLayout.style.display = 'grid';
        readingLayout.style.display = 'none';
        modeText.textContent = '📖 沉浸阅读';
        readingSettingsBtn.style.display = 'none';
        exportJsonBtn.style.display = 'inline-block';
        printBtn.style.display = 'inline-block';
        
        // 隐藏阅读设置面板
        hideReadingSettings();
    }
}

/**
 * 初始化阅读模式
 */
function initReadingMode() {
    // 更新阅读模式标题
    const readingTitle = document.getElementById('reading-title');
    if (readingTitle && novelData) {
        readingTitle.textContent = novelData.novel_title || currentNovelTitle || '小说标题';
    }
    
    // 生成章节菜单
    generateChapterMenu();
    
    // 应用当前阅读设置
    applyReadingSettings();
    
    // 如果有当前章节，更新阅读内容
    if (currentChapter && chaptersData.length > 0) {
        updateReadingContent();
    }
}

/**
 * 生成章节菜单
 */
function generateChapterMenu() {
    const menuContent = document.getElementById('chapter-menu-content');
    if (!menuContent || chaptersData.length === 0) return;
    
    const menuHtml = chaptersData.map(chapter => `
        <div class="chapter-menu-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
             onclick="loadChapterFromMenu(${chapter.chapter_number})">
            <div class="chapter-menu-item-title">
                第${chapter.chapter_number}章 ${chapter.title}
            </div>
            <div class="chapter-menu-item-meta">
                ${chapter.word_count || 0} 字
            </div>
        </div>
    `).join('');
    
    menuContent.innerHTML = menuHtml;
}

/**
 * 从章节菜单加载章节
 */
function loadChapterFromMenu(chapterNum) {
    if (chapterNum !== currentChapter) {
        loadChapter(currentNovelTitle, chapterNum);
        hideChapterMenu();
    }
}

/**
 * 显示章节菜单
 */
function showChapterMenu() {
    const chapterMenu = document.getElementById('chapter-menu');
    if (chapterMenu) {
        chapterMenu.classList.add('show');
    }
}

/**
 * 隐藏章节菜单
 */
function hideChapterMenu() {
    const chapterMenu = document.getElementById('chapter-menu');
    if (chapterMenu) {
        chapterMenu.classList.remove('show');
    }
}

/**
 * 更新阅读内容
 */
function updateReadingContent() {
    const currentChapterData = chaptersData.find(c => c.chapter_number === currentChapter);
    if (!currentChapterData) return;
    
    // 更新章节标题
    const readingChapterTitle = document.getElementById('reading-chapter-title');
    const readingChapterMeta = document.getElementById('reading-chapter-meta');
    const readingChapterIndicator = document.getElementById('reading-chapter-indicator');
    const readingNavIndicator = document.getElementById('reading-nav-indicator');
    
    if (readingChapterTitle) {
        readingChapterTitle.textContent = currentChapterData.title || `第${currentChapter}章`;
    }
    
    if (readingChapterMeta) {
        const wordCount = currentChapterData.content ? currentChapterData.content.length : 0;
        const generatedTime = currentChapterData.generated_at
            ? new Date(currentChapterData.generated_at).toLocaleString('zh-CN')
            : '未知';
        readingChapterMeta.textContent = `${wordCount} 字 • 生成时间: ${generatedTime}`;
    }
    
    if (readingChapterIndicator) {
        readingChapterIndicator.textContent = `第 ${currentChapter} 章`;
    }
    
    if (readingNavIndicator) {
        readingNavIndicator.textContent = `第 ${currentChapter} 章`;
    }
    
    // 更新章节内容
    const readingText = document.getElementById('reading-text');
    if (readingText && currentChapterData.content) {
        // 使用相同的后处理逻辑
        let html = currentChapterData.content;
        
        // 确保换行符统一
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        
        // 处理分隔线
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        
        // 处理特殊标记
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        // 处理段落
        let paragraphs = html.split(/\n\s*\n/);
        let result = '';
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (paragraph) {
                paragraph = paragraph.replace(/\n/g, '<br>');
                result += `<p>${paragraph}</p>`;
            }
        }
        
        readingText.innerHTML = result;
    }
    
    // 更新章节菜单的活跃状态
    updateChapterMenuActiveState();
    
    // 更新导航按钮状态
    updateReadingNavigationButtons();
}

/**
 * 更新章节菜单活跃状态
 */
function updateChapterMenuActiveState() {
    const menuItems = document.querySelectorAll('.chapter-menu-item');
    menuItems.forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = document.querySelector(`.chapter-menu-item[onclick*="${currentChapter}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

/**
 * 更新阅读模式导航按钮状态
 */
function updateReadingNavigationButtons() {
    const hasPrev = chaptersData.some(c => c.chapter_number < currentChapter);
    const hasNext = chaptersData.some(c => c.chapter_number > currentChapter);
    
    const navButtons = document.querySelectorAll('.reading-nav-btn');
    navButtons.forEach(btn => {
        if (btn.textContent.includes('上一章')) {
            btn.disabled = !hasPrev;
        } else if (btn.textContent.includes('下一章')) {
            btn.disabled = !hasNext;
        }
    });
}

/**
 * 切换阅读设置面板
 */
function toggleReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel.style.display === 'none') {
        showReadingSettings();
    } else {
        hideReadingSettings();
    }
}

/**
 * 显示阅读设置面板
 */
function showReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel) {
        settingsPanel.style.display = 'block';
        updateSettingsDisplay();
    }
}

/**
 * 隐藏阅读设置面板
 */
function hideReadingSettings() {
    const settingsPanel = document.getElementById('reading-settings-panel');
    if (settingsPanel) {
        settingsPanel.style.display = 'none';
    }
}

/**
 * 更新设置显示
 */
function updateSettingsDisplay() {
    const fontSizeDisplay = document.getElementById('font-size-display');
    const lineHeightDisplay = document.getElementById('line-height-display');
    
    if (fontSizeDisplay) {
        fontSizeDisplay.textContent = currentFontSize + 'px';
    }
    
    if (lineHeightDisplay) {
        lineHeightDisplay.textContent = currentLineHeight.toFixed(1);
    }
    
    // 更新主题按钮状态
    const themeButtons = document.querySelectorAll('.theme-btn');
    themeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.theme === currentTheme) {
            btn.classList.add('active');
        }
    });
}

/**
 * 调整字体大小
 */
function adjustFontSize(delta) {
    currentFontSize = Math.max(12, Math.min(24, currentFontSize + delta));
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 调整行间距
 */
function adjustLineHeight(delta) {
    currentLineHeight = Math.max(1.2, Math.min(2.5, currentLineHeight + delta));
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 设置阅读主题
 */
function setReadingTheme(theme) {
    currentTheme = theme;
    applyReadingSettings();
    updateSettingsDisplay();
}

/**
 * 应用阅读设置
 */
function applyReadingSettings() {
    const readingText = document.getElementById('reading-text');
    if (!readingText) return;
    
    // 移除所有主题类
    readingText.classList.remove('theme-light', 'theme-sepia', 'theme-dark');
    
    // 应用当前主题
    readingText.classList.add(`theme-${currentTheme}`);
    
    // 应用字体大小和行间距
    readingText.style.fontSize = currentFontSize + 'px';
    readingText.style.lineHeight = currentLineHeight;
}

/**
 * 重写loadChapter函数，支持阅读模式更新
 */
const originalLoadChapter = loadChapter;
loadChapter = async function(novelTitle, chapterNum) {
    try {
        // 调用原始函数
        await originalLoadChapter(novelTitle, chapterNum);
        
        // 如果在阅读模式，更新阅读内容
        if (isReadingMode) {
            updateReadingContent();
        }
    } catch (error) {
        console.error('加载章节失败:', error);
        showError('加载章节失败');
    }
};

/**
 * 重写updateNavigationButtons函数，支持阅读模式
 */
const originalUpdateNavigationButtons = updateNavigationButtons;
updateNavigationButtons = function() {
    // 调用原始函数
    originalUpdateNavigationButtons();
    
    // 如果在阅读模式，也更新阅读模式的导航按钮
    if (isReadingMode) {
        updateReadingNavigationButtons();
    }
};

// 点击页面其他地方隐藏设置面板
document.addEventListener('click', function(event) {
    const settingsPanel = document.getElementById('reading-settings-panel');
    const settingsBtn = document.getElementById('reading-settings-btn');
    
    if (settingsPanel &&
        settingsPanel.style.display !== 'none' &&
        !settingsPanel.contains(event.target) &&
        !settingsBtn.contains(event.target)) {
        hideReadingSettings();
    }
});

// ESC键隐藏菜单和设置面板
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        hideChapterMenu();
        hideReadingSettings();
    }
});
