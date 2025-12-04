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

// 分页系统相关变量
let paginationEnabled = true; // 是否启用分页
let currentPage = 1; // 当前页码
let totalPages = 1; // 总页数
let pageSizeLines = 25; // 每页行数
let pageMode = 'line'; // 分页模式: 'line' 按行数, 'height' 按高度
let chapterPages = []; // 章节分页数据
let currentChapterContent = ''; // 当前章节的完整内容

// 章节分页相关变量
let chapterPaginationEnabled = true; // 是否启用章节分页
let currentChapterPage = 1; // 当前章节页码
let totalChapterPages = 1; // 章节总页数
let chapterPageItems = 8; // 每页显示章节数
let chapterPagesData = []; // 章节分页数据

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

        // 初始化章节分页和布局调整（在数据加载完成后）
        initializeChapterPagination();
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
        // 更新核心设定 - 改为可展开的JSON组件
        const coreSettingElement = document.getElementById('core-setting');
        const coreSellingPointsElement = document.getElementById('core-selling-points');
        
        if (coreSettingElement) {
            // 辅助函数：从多个可能路径获取数据
            function getValueFromPaths(obj, paths) {
                for (const path of paths) {
                    const keys = path.split('.');
                    let current = obj;
                    let found = true;
                    
                    for (const key of keys) {
                        if (current && typeof current === 'object' && key in current) {
                            current = current[key];
                        } else {
                            found = false;
                            break;
                        }
                    }
                    
                    if (found && current) {
                        return current;
                    }
                }
                return null;
            }
            
            // 构建核心设定数据段
            const coreSettingSections = [];
            
            // 1. 核心设定信息
            const coreSetting = getValueFromPaths(novelData, [
                'novel_info.creative_seed.coreSetting',
                'creative_seed.coreSetting',
                'novel_metadata.coreSetting',
                'core_setting',
                'coreSetting'
            ]);
            
            if (coreSetting) {
                coreSettingSections.push({
                    title: `⚙️ 核心设定`,
                    data: { 核心设定: coreSetting },
                    options: {
                        id: 'core-setting-data',
                        icon: '⚙️',
                        expanded: false,
                        maxHeight: 200
                    }
                });
            }
            
            // 2. 世界观信息
            const worldview = getValueFromPaths(novelData, [
                'novel_info.creative_seed.worldview',
                'creative_seed.worldview',
                'worldview'
            ]);
            
            if (worldview) {
                coreSettingSections.push({
                    title: `🌍 世界观设定`,
                    data: { 世界观: worldview },
                    options: {
                        id: 'worldview-data',
                        icon: '🌍',
                        expanded: false,
                        maxHeight: 250
                    }
                });
            }
            
            // 3. 故事线信息
            const storyline = getValueFromPaths(novelData, [
                'novel_info.creative_seed.completeStoryline',
                'creative_seed.completeStoryline',
                'completeStoryline'
            ]);
            
            if (storyline && typeof storyline === 'object') {
                coreSettingSections.push({
                    title: `📖 完整故事线`,
                    data: storyline,
                    options: {
                        id: 'storyline-data',
                        icon: '📖',
                        expanded: false,
                        maxHeight: 300
                    }
                });
            }
            
            // 4. 全书成长规划
            const growthPlan = getValueFromPaths(novelData, [
                'creative_seed.growthPlan',
                'growth_plan',
                'global_growth_plan'
            ]);
            
            if (growthPlan) {
                coreSettingSections.push({
                    title: `📈 成长规划`,
                    data: growthPlan,
                    options: {
                        id: 'growth-plan-data',
                        icon: '📈',
                        expanded: false,
                        maxHeight: 350
                    }
                });
            }
            
            // 5. 角色设定
            const characterSetting = getValueFromPaths(novelData, [
                'creative_seed.characterSetting',
                'characterSetting'
            ]);
            
            if (characterSetting) {
                coreSettingSections.push({
                    title: `👥 角色设计`,
                    data: { 角色设定: characterSetting },
                    options: {
                        id: 'character-setting-data',
                        icon: '👥',
                        expanded: false,
                        maxHeight: 250
                    }
                });
            }
            
            // 6. 情节结构
            const plotStructure = getValueFromPaths(novelData, [
                'creative_seed.plotStructure',
                'plotStructure'
            ]);
            
            if (plotStructure) {
                coreSettingSections.push({
                    title: `🎭 情节结构`,
                    data: { 情节结构: plotStructure },
                    options: {
                        id: 'plot-structure-data',
                        icon: '🎭',
                        expanded: false,
                        maxHeight: 200
                    }
                });
            }
            
            // 7. 选定方案信息
            const selectedPlan = getValueFromPaths(novelData, [
                'novel_info.selected_plan',
                'selected_plan'
            ]);
            
            if (selectedPlan) {
                coreSettingSections.push({
                    title: `📋 市场分析方案`,
                    data: selectedPlan,
                    options: {
                        id: 'selected-plan-data',
                        icon: '📋',
                        expanded: false,
                        maxHeight: 400
                    }
                });
            }
            
            // 8. 创意种子完整数据
            const creativeSeed = getValueFromPaths(novelData, [
                'novel_info.creative_seed',
                'creative_seed'
            ]);
            
            if (creativeSeed && typeof creativeSeed === 'object') {
                coreSettingSections.push({
                    title: `🎨 创意种子完整数据`,
                    data: creativeSeed,
                    options: {
                        id: 'creative-seed-data',
                        icon: '🎨',
                        expanded: false,
                        maxHeight: 500
                    }
                });
            }
            
            // 9. 小说元数据
            const novelMetadata = getValueFromPaths(novelData, [
                'novel_metadata',
                'novel_info'
            ]);
            
            if (novelMetadata && typeof novelMetadata === 'object') {
                coreSettingSections.push({
                    title: `📚 小说元数据`,
                    data: novelMetadata,
                    options: {
                        id: 'novel-metadata-data',
                        icon: '📚',
                        expanded: false,
                        maxHeight: 400
                    }
                });
            }
            
            // 生成HTML
            if (coreSettingSections.length > 0) {
                const html = coreSettingSections.map(section => {
                    return createExpandableJSON(section.title, section.data, section.options);
                }).join('');
                
                coreSettingElement.innerHTML = html;
            } else {
                coreSettingElement.innerHTML = '<div style="color: #999; font-style: italic; padding: 8px; text-align: center;">暂无核心设定信息</div>';
            }
        }
        
        if (coreSellingPointsElement) {
            // 使用相同的辅助函数获取卖点信息
            function getValueFromPaths(obj, paths) {
                for (const path of paths) {
                    const keys = path.split('.');
                    let current = obj;
                    let found = true;
                    
                    for (const key of keys) {
                        if (current && typeof current === 'object' && key in current) {
                            current = current[key];
                        } else {
                            found = false;
                            break;
                        }
                    }
                    
                    if (found && current) {
                        return current;
                    }
                }
                return null;
            }
            
            // 构建卖点数据段
            const sellingPointSections = [];
            
            const sellingPoints = getValueFromPaths(novelData, [
                'novel_info.creative_seed.coreSellingPoints',
                'creative_seed.coreSellingPoints',
                'novel_metadata.coreSellingPoints',
                'core_selling_points',
                'coreSellingPoints',
                'selected_plan.competitive_advantage'
            ]);
            
            if (sellingPoints) {
                // 处理不同格式的卖点数据
                let processedSellingPoints;
                if (Array.isArray(sellingPoints)) {
                    processedSellingPoints = {
                        类型: '数组格式',
                        卖点列表: sellingPoints,
                        数量: sellingPoints.length
                    };
                } else if (typeof sellingPoints === 'string') {
                    // 处理用+号分隔的卖点
                    const points = sellingPoints.split('+').map(p => p.trim()).filter(p => p);
                    if (points.length > 1) {
                        processedSellingPoints = {
                            类型: '分隔符格式',
                            原始文本: sellingPoints,
                            解析结果: points,
                            数量: points.length
                        };
                    } else {
                        processedSellingPoints = {
                            类型: '文本格式',
                            卖点描述: sellingPoints
                        };
                    }
                } else {
                    processedSellingPoints = sellingPoints;
                }
                
                sellingPointSections.push({
                    title: `💎 核心卖点分析`,
                    data: processedSellingPoints,
                    options: {
                        id: 'core-selling-points-data',
                        icon: '💎',
                        expanded: false,
                        maxHeight: 300
                    }
                });
            }
            
            // 添加市场竞争分析数据
            const marketAnalysis = getValueFromPaths(novelData, [
                'selected_plan.market_analysis',
                'market_analysis',
                'creative_seed.marketAnalysis'
            ]);
            
            if (marketAnalysis) {
                sellingPointSections.push({
                    title: `📊 市场竞争分析`,
                    data: marketAnalysis,
                    options: {
                        id: 'market-analysis-data',
                        icon: '📊',
                        expanded: false,
                        maxHeight: 350
                    }
                });
            }
            
            // 添加竞争优势数据
            const competitiveAdvantage = getValueFromPaths(novelData, [
                'selected_plan.competitive_advantage',
                'competitive_advantage',
                'creative_seed.competitiveAdvantage'
            ]);
            
            if (competitiveAdvantage) {
                sellingPointSections.push({
                    title: `🏆 竞争优势`,
                    data: { 竞争优势: competitiveAdvantage },
                    options: {
                        id: 'competitive-advantage-data',
                        icon: '🏆',
                        expanded: false,
                        maxHeight: 250
                    }
                });
            }
            
            // 生成HTML
            if (sellingPointSections.length > 0) {
                const html = sellingPointSections.map(section => {
                    return createExpandableJSON(section.title, section.data, section.options);
                }).join('');
                
                coreSellingPointsElement.innerHTML = html;
            } else {
                coreSellingPointsElement.innerHTML = '<div style="color: #999; font-style: italic; padding: 8px; text-align: center;">暂无卖点信息</div>';
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

        // 执行章节分页
        paginateChaptersList();

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
        
        // 直接显示HTML内容，不添加批量操作按钮
        container.innerHTML = html;
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
    
    console.log('更新角色发展信息...', qualityData);
    
    // 尝试从多个路径获取角色发展数据
    let characterDev = null;
    
    // 路径1: 从质量数据中获取
    if (qualityData && qualityData.character_development) {
        characterDev = qualityData.character_development;
        console.log('从qualityData.character_development获取到角色数据:', characterDev);
    }
    
    // 路径2: 从质量数据的不同字段中获取
    if (!characterDev && qualityData) {
        const possiblePaths = [
            'character_development_data',
            'character_data',
            'characters',
            'role_development'
        ];
        
        for (const path of possiblePaths) {
            if (qualityData[path] && typeof qualityData[path] === 'object') {
                characterDev = qualityData[path];
                console.log(`从qualityData.${path}获取到角色数据:`, characterDev);
                break;
            }
        }
    }
    
    // 路径3: 从章节数据中获取
    if (!characterDev && chapter) {
        if (chapter.character_development) {
            characterDev = chapter.character_development;
            console.log('从chapter.character_development获取到角色数据:', characterDev);
        }
    }
    
    // 路径4: 从小说全局数据中获取
    if (!characterDev && novelData) {
        const globalPaths = [
            'novel_info.character_development',
            'character_development',
            'characters_data'
        ];
        
        for (const path of globalPaths) {
            if (novelData[path] && typeof novelData[path] === 'object') {
                characterDev = novelData[path];
                console.log(`从novelData.${path}获取到角色数据:`, characterDev);
                break;
            }
        }
    }
    
    // 如果仍然没有数据，显示调试信息
    if (!characterDev || Object.keys(characterDev).length === 0) {
        console.log('未找到角色发展数据，显示调试信息');
        container.innerHTML = `
            <div style="text-align: center; color: #999; padding: 20px;">
                <div style="margin-bottom: 10px;">暂无角色发展信息</div>
                <details style="text-align: left; margin-top: 10px;">
                    <summary style="cursor: pointer; color: #666;">调试信息</summary>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 11px; overflow: auto; max-height: 200px;">
qualityData: ${JSON.stringify(qualityData, null, 2)}
chapter: ${JSON.stringify(chapter, null, 2)}
novelData: ${JSON.stringify(novelData, null, 2)}
                    </pre>
                </details>
            </div>
        `;
        return;
    }
    
    const characterNames = Object.keys(characterDev);
    console.log(`找到 ${characterNames.length} 个角色:`, characterNames);

    // 生成人物卡片HTML
    let html = '<div class="character-cards-container">';
    
    characterNames.slice(0, 6).forEach(name => {
        const char = characterDev[name];
        const attributes = char.attributes || char.attribute_data || {};
        
        // 确定角色类型和重要性
        const roleType = char.role_type || char.type || '配角';
        const importance = char.importance || char.level || '次要';
        const isActive = char.status === 'active' || char.is_active === true;
        
        // 生成角色头像（使用角色名的首字母或默认图标）
        let avatarText = name.charAt(0).toUpperCase();
        if (name.includes('韩') || name.includes('主角')) {
            avatarText = '主';
        } else if (name.includes('女')) {
            avatarText = '女';
        } else if (name.includes('男')) {
            avatarText = '男';
        }
        
        // 根据重要性确定状态颜色
        let statusClass = 'status-inactive';
        if (isActive) {
            statusClass = 'status-active';
        } else if (importance === '主要' || importance === '重要') {
            statusClass = 'status-important';
        }

        // 获取属性值，支持多种可能的字段名
        const cultivationLevel = attributes.cultivation_level || attributes.level || attributes.修为 || '未知';
        const location = attributes.location || attributes.位置 || '未知';
        const money = attributes.money || attributes.灵石 || attributes.财富 || '0';

        html += `
            <div class="character-card">
                <div class="character-status ${statusClass}">${importance}</div>
                <div class="character-card-header">
                    <div class="character-avatar">${avatarText}</div>
                    <div class="character-info">
                        <div class="character-name">${name}</div>
                        <div class="character-title">${roleType} • ${importance}</div>
                    </div>
                </div>
                <div class="character-card-body">
                    <div class="character-attributes">
                        <div class="character-attribute">
                            <div class="attribute-label">修为</div>
                            <div class="attribute-value">${cultivationLevel}</div>
                        </div>
                        <div class="character-attribute">
                            <div class="attribute-label">位置</div>
                            <div class="attribute-value">${location}</div>
                        </div>
                        <div class="character-attribute">
                            <div class="attribute-label">灵石</div>
                            <div class="attribute-value">${money}</div>
                        </div>
                    </div>
                    
                    <div class="character-stats">
                        <div class="stat-item">
                            <div class="stat-value">${char.total_appearances || char.appearances || 0}</div>
                            <div class="stat-label">出现次数</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${char.first_appearance_chapter || char.first_chapter || 0}</div>
                            <div class="stat-label">首章</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value">${char.last_updated_chapter || char.last_chapter || 0}</div>
                            <div class="stat-label">终章</div>
                        </div>
                    </div>
                    
                    <div class="character-description">
                        ${char.description || char.desc || char简介 || '暂无描述信息'}
                    </div>
                </div>
            </div>
        `;
    });

    if (characterNames.length > 6) {
        html += `<div style="text-align: center; color: #666; font-size: 12px; margin-top: 16px;">
            <div style="background: rgba(43, 108, 176, 0.1); padding: 8px 12px; border-radius: 4px; margin: 0 8px;">
                查看全部 ${characterNames.length} 个角色 →
            </div>
            <div style="text-align: center; color: #999; font-size: 11px;">
                ...还有 ${characterNames.length - 6} 个角色未显示
            </div>
        </div>`;
    }

    html += '</div>';
    container.innerHTML = html;
    
    console.log(`角色发展信息更新完成，显示了 ${Math.min(6, characterNames.length)} 个角色`);
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

    // 创建大窗口查看按钮（如果启用大弹窗）
    const expandButton = enableLargeModal ? `
        <button class="btn-expand-large" data-title="${escapeHtml(title)}" data-content="${rawContent.replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/`/g, '&#96;')}" title="在大弹窗中查看">
            🔍 大窗口查看
        </button>
    ` : '';

    return `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    ${expandButton}
                </div>
            </div>
        </div>
    `;
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
    
    // 初始显示加载状态（移除展开功能，只显示加载状态）
    let component = `
        <div class="expandable-json-section" id="${componentId}">
            <div class="json-header">
                <div class="json-title">
                    <span>${icon}</span>
                    <span>${title}</span>
                </div>
            </div>
            <div class="json-content" style="max-height: 0; overflow: hidden;">
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

        // 更新组件内容（自动显示，不需要点击展开）
        setTimeout(() => {
            const section = document.getElementById(componentId);
            if (section) {
                const contentDiv = section.querySelector('.json-content');
                if (contentDiv) {
                    contentDiv.innerHTML = content;
                    // 自动显示内容
                    contentDiv.style.maxHeight = contentDiv.scrollHeight + 'px';
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
                    // 自动显示错误信息
                    contentDiv.style.maxHeight = contentDiv.scrollHeight + 'px';
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


// ==================== 大弹窗功能 ====================

/**
 * 显示大JSON弹窗 - 全屏新界面
 */
function showLargeJSONModal(title, content) {
    console.log('显示大弹窗:', title, content?.substring(0, 100) + '...');
    
    try {
        // 先关闭已存在的弹窗
        closeLargeJSONModal();
        
        // 创建全屏模态背景
        const modalOverlay = document.createElement('div');
        modalOverlay.className = 'modal-overlay fullscreen-modal';
        modalOverlay.id = 'large-json-modal';
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.95);
            backdrop-filter: blur(10px);
            z-index: 10000;
            display: flex;
            flex-direction: column;
            animation: fadeIn 0.3s ease-out;
            width: 100vw;
            height: 100vh;
            overflow: hidden;
        `;

        // 创建全屏模态内容
        const modalContent = document.createElement('div');
        modalContent.className = 'modal-large fullscreen-modal-content';
        modalContent.style.cssText = `
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            width: 100%;
            height: 100%;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: none;
            animation: slideUp 0.3s ease-out;
            position: relative;
        `;

        // 格式化JSON内容
        let formattedContent = content;
        try {
            const parsed = JSON.parse(content);
            formattedContent = JSON.stringify(parsed, null, 2);
        } catch (e) {
            console.log('内容不是JSON格式，保持原样');
            // 如果不是JSON，保持原样
        }

        // 应用语法高亮
        const highlightedContent = highlightJSON(formattedContent);

        // 创建唯一的按钮ID
        const copyBtnId = 'copy-btn-' + Date.now();
        const downloadBtnId = 'download-btn-' + Date.now() + '-1';

        // 安全地转义内容用于HTML属性
        const safeTitle = escapeHtml(title);

        modalContent.innerHTML = `
            <div class="fullscreen-modal-header" style="background: linear-gradient(135deg, #00d4ff 0%, #0099cc 50%, #006699 100%); color: white; padding: 16px 24px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.2); flex-shrink: 0; height: 60px;">
                <div style="display: flex; align-items: center; gap: 16px; flex: 1;">
                    <h3 style="margin: 0; font-size: 20px; font-weight: 700; display: flex; align-items: center; gap: 12px;">${safeTitle}</h3>
                    <div style="display: flex; gap: 8px; margin-left: auto;">
                        <button class="btn btn-secondary btn-small fullscreen-action-btn" id="${copyBtnId}" style="background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s ease; backdrop-filter: blur(10px);">
                            📋 复制内容
                        </button>
                        <button class="btn btn-secondary btn-small fullscreen-action-btn" id="${downloadBtnId}" style="background: rgba(255, 255, 255, 0.2); color: white; border: 1px solid rgba(255, 255, 255, 0.3); padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.15s ease; backdrop-filter: blur(10px);">
                            💾 下载文件
                        </button>
                    </div>
                </div>
                <button class="modal-close-btn fullscreen-close-btn" style="background: rgba(255, 255, 255, 0.2); border: 1px solid rgba(255, 255, 255, 0.3); color: white; font-size: 20px; cursor: pointer; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; border-radius: 8px; transition: all 0.15s ease; backdrop-filter: blur(10px); margin-left: 16px;">×</button>
            </div>
            <div class="fullscreen-modal-body" style="flex: 1; padding: 0; overflow: hidden; background: #f9fafb; display: flex; flex-direction: column;">
                <div class="fullscreen-content-container" style="flex: 1; padding: 24px; overflow-y: auto; background: #f9fafb;">
                    <div style="background: white; border-radius: 12px; padding: 24px; border: 1px solid #e5e7eb; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); height: 100%; display: flex; flex-direction: column;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 2px solid #dbeafe;">
                            <div style="font-size: 20px; font-weight: 700; color: #1d4ed8; display: flex; align-items: center; gap: 12px;">
                                <span>📄</span>
                                <span>JSON 数据内容</span>
                                <span style="font-size: 14px; color: #6b7280; font-weight: 400;">(${content.length} 字符)</span>
                            </div>
                        </div>
                        <div class="fullscreen-json-display" style="flex: 1; background: #f8f9fa; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace; font-size: 14px; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word; overflow-y: auto; min-height: 400px;">${highlightedContent}</div>
                    </div>
                </div>
            </div>
        `;

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        console.log('弹窗已添加到DOM');

        // 使用事件委托而不是内联onclick，避免转义问题
        const copyBtn = modalContent.querySelector(`#${copyBtnId}`);
        const downloadBtn = modalContent.querySelector(`#${downloadBtnId}`);
        const closeBtn = modalContent.querySelector('.modal-close-btn');

        if (copyBtn) {
            copyBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                copyJSONContent(formattedContent);
            });
        }
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                downloadJSONContent(title, formattedContent);
            });
        }
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeLargeJSONModal();
            });
        }

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
        
        console.log('弹窗显示完成');
    } catch (error) {
        console.error('显示大弹窗时发生错误:', error);
        showNotification('❌ 显示大弹窗失败: ' + error.message);
    }
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
        console.log('尝试复制内容:', content?.substring(0, 100) + '...');
        
        // 解码转义的内容
        let decodedContent = content;
        if (typeof content === 'string') {
            decodedContent = content
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\')
                .replace(/\\n/g, '\n');
        }
        
        console.log('解码后的内容长度:', decodedContent?.length);
        
        await navigator.clipboard.writeText(decodedContent);
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
        console.log('尝试下载文件:', title, content?.substring(0, 100) + '...');
        
        // 解码转义的内容
        let decodedContent = content;
        let decodedTitle = title;
        
        if (typeof content === 'string') {
            decodedContent = content
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\')
                .replace(/\\n/g, '\n');
        }
        
        if (typeof title === 'string') {
            decodedTitle = title
                .replace(/\\'/g, "'")
                .replace(/\\"/g, '"')
                .replace(/\\`/g, '`')
                .replace(/\\\\/g, '\\');
        }
        
        console.log('解码后的内容长度:', decodedContent?.length);
        
        const blob = new Blob([decodedContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `${decodedTitle.replace(/[^\w\u4e00-\u9fa5]/g, '_')}_${new Date().getTime()}.json`;
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
        // 同时关闭大弹窗
        if (window.closeLargeJSONModal) {
            window.closeLargeJSONModal();
        }
    }
});

// 确保函数在页面加载完成后可用
document.addEventListener('DOMContentLoaded', function() {
    // 将函数绑定到全局作用域
    window.showLargeJSONModal = showLargeJSONModal;
    window.closeLargeJSONModal = closeLargeJSONModal;
    
    console.log('弹窗函数初始化完成');
    console.log('showLargeJSONModal 可用性:', typeof window.showLargeJSONModal);
    console.log('closeLargeJSONModal 可用性:', typeof window.closeLargeJSONModal);
    
    // 添加事件委托处理大窗口查看按钮
    document.body.addEventListener('click', function(event) {
        if (event.target.classList.contains('btn-expand-large') || event.target.closest('.btn-expand-large')) {
            const button = event.target.classList.contains('btn-expand-large') ? event.target : event.target.closest('.btn-expand-large');
            
            // 从data属性获取标题和内容
            const title = button.getAttribute('data-title') || '数据查看';
            let content = button.getAttribute('data-content') || '{}';
            
            // 解码HTML实体
            content = content
                .replace(/&quot;/g, '"')
                .replace(/&#39;/g, "'")
                .replace(/&#96;/g, '`')
                .replace(/&amp;/g, '&');
            
            console.log('点击大窗口查看按钮:', title, content.substring(0, 100) + '...');
            
            // 调用弹窗函数
            if (window.showLargeJSONModal) {
                window.showLargeJSONModal(title, content);
            } else {
                console.error('showLargeJSONModal 函数不可用');
                alert('弹窗功能暂时不可用，请刷新页面重试');
            }
            
            event.preventDefault();
            event.stopPropagation();
        }
    });
    
    // 添加全局调试函数
    window.testModal = function() {
        console.log('测试弹窗功能...');
        if (window.showLargeJSONModal) {
            window.showLargeJSONModal('测试弹窗', JSON.stringify({
                test: true,
                message: '这是一个测试弹窗',
                timestamp: new Date().toISOString()
            }, null, 2));
        } else {
            console.error('showLargeJSONModal 函数不可用');
        }
    };
    
    console.log('测试函数已添加: window.testModal()');
});

// ==================== 分页系统功能 ====================

/**
 * 初始化分页系统
 */
function initializePagination() {
    // 从本地存储加载分页设置
    loadPaginationSettings();
    
    // 应用分页设置
    applyPaginationSettings();
    
    console.log('分页系统已初始化');
}

/**
 * 加载分页设置
 */
function loadPaginationSettings() {
    try {
        const settings = localStorage.getItem('novel-pagination-settings');
        if (settings) {
            const parsed = JSON.parse(settings);
            paginationEnabled = parsed.paginationEnabled !== false;
            pageSizeLines = parsed.pageSizeLines || 25;
            pageMode = parsed.pageMode || 'line';
        }
    } catch (error) {
        console.warn('加载分页设置失败:', error);
    }
}

/**
 * 保存分页设置
 */
function savePaginationSettings() {
    try {
        const settings = {
            paginationEnabled,
            pageSizeLines,
            pageMode
        };
        localStorage.setItem('novel-pagination-settings', JSON.stringify(settings));
    } catch (error) {
        console.warn('保存分页设置失败:', error);
    }
}

/**
 * 应用分页设置
 */
function applyPaginationSettings() {
    // 更新设置面板显示
    updatePaginationSettingsDisplay();
    
    // 应用分页模式
    applyPaginationMode();
}

/**
 * 更新分页设置显示
 */
function updatePaginationSettingsDisplay() {
    // 更新每页行数显示
    const pageSizeDisplay = document.getElementById('page-size-display');
    if (pageSizeDisplay) {
        pageSizeDisplay.textContent = `${pageSizeLines}行`;
    }
    
    // 更新自动分页开关
    const autoPageToggle = document.getElementById('auto-page-toggle');
    if (autoPageToggle) {
        autoPageToggle.checked = paginationEnabled;
    }
    
    // 更新分页模式按钮
    const pageModeButtons = document.querySelectorAll('.page-mode-btn');
    pageModeButtons.forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.mode === pageMode) {
            btn.classList.add('active');
        }
    });
}

/**
 * 应用分页模式
 */
function applyPaginationMode() {
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    if (paginationEnabled) {
        // 启用分页模式
        if (contentBody) contentBody.classList.add('paged');
        if (readingText) readingText.classList.add('paged');
        
        // 显示分页导航
        showPaginationNavigation();
        
        // 如果有章节内容，重新分页
        if (currentChapterContent) {
            paginateChapterContent(currentChapterContent);
        }
    } else {
        // 禁用分页模式
        if (contentBody) contentBody.classList.remove('paged');
        if (readingText) readingText.classList.remove('paged');
        
        // 隐藏分页导航
        hidePaginationNavigation();
        
        // 恢复完整内容显示
        if (currentChapterContent) {
            displayFullContent(currentChapterContent);
        }
    }
}

/**
 * 章节内容分页
 */
function paginateChapterContent(content) {
    if (!paginationEnabled) {
        displayFullContent(content);
        return;
    }
    
    currentChapterContent = content;
    
    if (pageMode === 'line') {
        paginateByLines(content);
    } else {
        paginateByHeight(content);
    }
    
    // 显示第一页
    currentPage = 1;
    displayCurrentPage();
    
    // 更新分页导航
    updatePaginationNavigation();
}

/**
 * 按行数分页
 */
function paginateByLines(content) {
    // 将内容按段落分割
    const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
    const pages = [];
    let currentPageLines = [];
    let currentLineCount = 0;
    
    for (const paragraph of paragraphs) {
        const lines = paragraph.split('\n').filter(line => line.trim());
        
        // 如果当前段落加上后不会超过页面限制
        if (currentLineCount + lines.length <= pageSizeLines) {
            currentPageLines.push(...lines);
            currentLineCount += lines.length;
        } else {
            // 保存当前页面
            if (currentPageLines.length > 0) {
                pages.push(currentPageLines.join('\n'));
            }
            
            // 开始新页面
            currentPageLines = [...lines];
            currentLineCount = lines.length;
            
            // 如果单个段落就超过页面限制，强制分页
            if (currentLineCount > pageSizeLines) {
                const remainingLines = currentPageLines.splice(pageSizeLines);
                pages.push(currentPageLines.join('\n'));
                currentPageLines = remainingLines;
                currentLineCount = remainingLines.length;
            }
        }
    }
    
    // 添加最后一页
    if (currentPageLines.length > 0) {
        pages.push(currentPageLines.join('\n'));
    }
    
    chapterPages = pages;
    totalPages = pages.length;
}

/**
 * 按高度分页
 */
function paginateByHeight(content) {
    // 获取正文内容区域的实际可用高度
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    let targetHeight = 450; // 默认目标高度
    let containerWidth = 700; // 默认宽度
    
    if (contentBody && !isReadingMode) {
        // 调试模式：获取正文区域的高度（减去导航栏和边距）
        const contentHeight = contentBody.clientHeight;
        const navigationHeight = document.querySelector('.chapter-navigation') ?
            document.querySelector('.chapter-navigation').offsetHeight : 60;
        targetHeight = contentHeight - navigationHeight - 20; // 减去导航栏和边距
        containerWidth = contentBody.clientWidth - 40; // 减去内边距
    } else if (readingText && isReadingMode) {
        // 阅读模式：获取阅读区域的高度
        const contentHeight = readingText.clientHeight;
        const navigationHeight = document.querySelector('.reading-navigation') ?
            document.querySelector('.reading-navigation').offsetHeight : 60;
        targetHeight = contentHeight - navigationHeight - 20; // 减去导航栏和边距
        containerWidth = readingText.clientWidth - 40; // 减去内边距
    }
    
    console.log(`获取到目标高度: ${targetHeight}px, 容器宽度: ${containerWidth}px`);
    
    // 创建临时元素来测量高度，模拟实际的显示效果
    const tempDiv = document.createElement('div');
    tempDiv.style.cssText = `
        position: absolute;
        top: -9999px;
        left: -9999px;
        width: ${containerWidth}px;
        height: ${targetHeight}px;
        font-size: ${isReadingMode ? currentFontSize + 'px' : '16px'};
        line-height: ${currentLineHeight};
        padding: ${isReadingMode ? '24px' : '20px'};
        visibility: hidden;
        box-sizing: border-box;
        overflow: hidden;
        font-family: ${isReadingMode ? 'var(--font-serif)' : 'var(--font-sans)'};
    `;
    
    document.body.appendChild(tempDiv);
    
    // 将内容处理成HTML格式进行测量
    const processContentForMeasurement = (text) => {
        return text
            .replace(/\r\n/g, '\n').replace(/\r/g, '\n')
            .replace(/[═]{10,}/g, '<hr class="novel-hr">')
            .replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>')
            .replace(/\n\s*\n/g, '</p><p style="margin-bottom: 1em;">')
            .replace(/\n/g, '<br>');
    };
    
    const paragraphs = content.split(/\n\s*\n/).filter(p => p.trim());
    const pages = [];
    let currentContent = '';
    
    // 逐段添加内容，直到填满目标高度
    for (let i = 0; i < paragraphs.length; i++) {
        const paragraph = paragraphs[i];
        const testContent = currentContent + (currentContent ? '\n\n' : '') + paragraph;
        
        // 处理内容为HTML格式进行测量
        const htmlContent = `<p style="margin-bottom: 1em;">${processContentForMeasurement(testContent)}</p>`;
        tempDiv.innerHTML = htmlContent;
        
        // 检查是否超出目标高度
        if (tempDiv.scrollHeight > targetHeight && currentContent) {
            // 保存当前页面
            pages.push(currentContent.trim());
            currentContent = paragraph;
            
            // 重置临时元素内容为当前段落
            const currentHtml = `<p style="margin-bottom: 1em;">${processContentForMeasurement(paragraph)}</p>`;
            tempDiv.innerHTML = currentHtml;
        } else {
            currentContent = testContent;
        }
    }
    
    // 添加最后一页
    if (currentContent.trim()) {
        pages.push(currentContent.trim());
    }
    
    document.body.removeChild(tempDiv);
    
    chapterPages = pages;
    totalPages = pages.length;
    
    console.log(`按高度分页完成: ${totalPages}页, 目标高度: ${targetHeight}px`);
    
    // 如果只有一页但内容很少，确保内容填满整个高度
    if (totalPages === 1 && chapterPages[0]) {
        console.log('单页内容，确保填满整个高度');
    }
}

/**
 * 显示完整内容（非分页模式）
 */
function displayFullContent(content) {
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    if (contentBody && isReadingMode === false) {
        // 调试模式
        contentBody.innerHTML = `<div class="novel-content-raw">${escapeHtml(content)}</div>`;
        postProcessContent(contentBody);
    }
    
    if (readingText && isReadingMode === true) {
        // 阅读模式
        let html = content;
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        const paragraphs = html.split(/\n\s*\n/);
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
}

/**
 * 显示当前页
 */
function displayCurrentPage() {
    if (!paginationEnabled || chapterPages.length === 0) return;
    
    const pageContent = chapterPages[currentPage - 1];
    const contentBody = document.getElementById('chapter-content');
    const readingText = document.getElementById('reading-text');
    
    if (contentBody && isReadingMode === false) {
        // 调试模式
        contentBody.innerHTML = `
            <div class="page-content">
                <div class="page-progress">
                    <div class="page-progress-bar" style="width: ${(currentPage / totalPages) * 100}%"></div>
                </div>
                <div class="page-content-inner">
                    <div class="novel-content-raw" style="min-height: 100%;">${escapeHtml(pageContent)}</div>
                </div>
            </div>
        `;
        // 后处理内容
        setTimeout(() => {
            postProcessContent(contentBody);
        }, 50);
    }
    
    if (readingText && isReadingMode === true) {
        // 阅读模式
        let html = pageContent;
        html = html.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        html = html.replace(/[═]{10,}/g, '<hr class="novel-hr">');
        html = html.replace(/【([^】]+)】/g, '<span class="novel-tag">【$1】</span>');
        
        const paragraphs = html.split(/\n\s*\n/);
        let result = '';
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (paragraph) {
                paragraph = paragraph.replace(/\n/g, '<br>');
                result += `<p style="margin-bottom: 1em;">${paragraph}</p>`;
            }
        }
        
        readingText.innerHTML = `
            <div class="page-content">
                <div class="page-progress">
                    <div class="page-progress-bar" style="width: ${(currentPage / totalPages) * 100}%"></div>
                </div>
                <div class="page-content-inner" style="min-height: 100%;">${result}</div>
            </div>
        `;
    }
}

/**
 * 更新分页导航
 */
function updatePaginationNavigation() {
    // 更新调试模式分页导航
    updateDebugPaginationNavigation();
    
    // 更新阅读模式分页导航
    updateReadingPaginationNavigation();
}

/**
 * 更新调试模式分页导航
 */
function updateDebugPaginationNavigation() {
    const currentPageSpan = document.getElementById('current-page');
    const totalPagesSpan = document.getElementById('total-pages');
    const prevPageBtn = document.getElementById('prev-page-btn');
    const nextPageBtn = document.getElementById('next-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentPage <= 1;
    }
    
    if (nextPageBtn) {
        nextPageBtn.disabled = currentPage >= totalPages;
    }
}

/**
 * 更新阅读模式分页导航
 */
function updateReadingPaginationNavigation() {
    const currentPageSpan = document.getElementById('reading-current-page');
    const totalPagesSpan = document.getElementById('reading-total-pages');
    const prevPageBtn = document.getElementById('reading-prev-page-btn');
    const nextPageBtn = document.getElementById('reading-next-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentPage <= 1;
    }
    
    if (nextPageBtn) {
        nextPageBtn.disabled = currentPage >= totalPages;
    }
}

/**
 * 显示分页导航
 */
function showPaginationNavigation() {
    const pageNavigation = document.getElementById('page-navigation');
    const readingPageNavigation = document.getElementById('reading-page-navigation');
    
    if (pageNavigation) {
        pageNavigation.style.display = 'flex';
    }
    
    if (readingPageNavigation && isReadingMode) {
        readingPageNavigation.style.display = 'flex';
    }
}

/**
 * 隐藏分页导航
 */
function hidePaginationNavigation() {
    const pageNavigation = document.getElementById('page-navigation');
    const readingPageNavigation = document.getElementById('reading-page-navigation');
    
    if (pageNavigation) {
        pageNavigation.style.display = 'none';
    }
    
    if (readingPageNavigation) {
        readingPageNavigation.style.display = 'none';
    }
}

/**
 * 上一页
 */
function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        displayCurrentPage();
        updatePaginationNavigation();
        scrollToContentTop();
        showKeyboardHint('← 上一页');
    }
}

/**
 * 下一页
 */
function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        displayCurrentPage();
        updatePaginationNavigation();
        scrollToContentTop();
        showKeyboardHint('→ 下一页');
    }
}

/**
 * 滚动到内容顶部
 */
function scrollToContentTop() {
    if (isReadingMode) {
        // 阅读模式：滚动到阅读内容区域顶部
        const readingContent = document.getElementById('reading-content');
        if (readingContent) {
            readingContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } else {
        // 调试模式：滚动到正文内容区域顶部
        const centerContent = document.getElementById('center-content');
        if (centerContent) {
            centerContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
}

/**
 * 切换分页设置面板
 */
function togglePageSettings() {
    const settingsPanel = document.getElementById('page-settings-panel');
    if (settingsPanel.style.display === 'none') {
        settingsPanel.style.display = 'block';
    } else {
        settingsPanel.style.display = 'none';
    }
}

/**
 * 切换阅读模式分页设置
 */
function toggleReadingPageSettings() {
    // 这里可以添加阅读模式专用的分页设置
    togglePageSettings();
}

/**
 * 调整页面大小
 */
function adjustPageSize(delta) {
    pageSizeLines = Math.max(10, Math.min(50, pageSizeLines + delta));
    updatePaginationSettingsDisplay();
    savePaginationSettings();
    
    // 重新分页
    if (currentChapterContent) {
        paginateChapterContent(currentChapterContent);
    }
}

/**
 * 切换自动分页
 */
function toggleAutoPage() {
    const autoPageToggle = document.getElementById('auto-page-toggle');
    paginationEnabled = autoPageToggle.checked;
    savePaginationSettings();
    applyPaginationMode();
}

/**
 * 设置分页模式
 */
function setPageMode(mode) {
    pageMode = mode;
    updatePaginationSettingsDisplay();
    savePaginationSettings();
    
    // 重新分页
    if (currentChapterContent) {
        paginateChapterContent(currentChapterContent);
    }
}

/**
 * 显示键盘快捷键提示
 */
function showKeyboardHint(action) {
    // 移除现有提示
    const existingHint = document.querySelector('.keyboard-hint');
    if (existingHint) {
        existingHint.remove();
    }
    
    // 创建新提示
    const hint = document.createElement('div');
    hint.className = 'keyboard-hint';
    hint.textContent = action;
    document.body.appendChild(hint);
    
    // 显示提示
    setTimeout(() => hint.classList.add('show'), 10);
    
    // 自动隐藏
    setTimeout(() => {
        hint.classList.remove('show');
        setTimeout(() => hint.remove(), 300);
    }, 2000);
}

/**
 * 重写updateCenterContent函数，支持分页
 */
const originalUpdateCenterContent = updateCenterContent;
updateCenterContent = function(chapter) {
    // 调用原始函数
    originalUpdateCenterContent(chapter);
    
    // 如果启用分页，对内容进行分页处理
    if (paginationEnabled && chapter.content) {
        setTimeout(() => {
            paginateChapterContent(chapter.content);
        }, 100);
    }
};

/**
 * 重写updateReadingContent函数，支持分页
 */
const originalUpdateReadingContent = updateReadingContent;
updateReadingContent = function() {
    // 调用原始函数
    originalUpdateReadingContent();
    
    // 如果启用分页且在阅读模式，对内容进行分页处理
    if (paginationEnabled && isReadingMode) {
        const currentChapterData = chaptersData.find(c => c.chapter_number === currentChapter);
        if (currentChapterData && currentChapterData.content) {
            setTimeout(() => {
                paginateChapterContent(currentChapterData.content);
            }, 100);
        }
    }
};

// 初始化分页系统
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(() => {
        initializePagination();
    }, 500);
});

// 添加键盘快捷键支持
document.addEventListener('keydown', function(event) {
    if (!paginationEnabled) return;
    
    // 防止在输入框中触发
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }
    
    if (event.key === 'ArrowLeft' && event.ctrlKey) {
        // Ctrl + 左箭头：上一页
        event.preventDefault();
        prevPage();
    } else if (event.key === 'ArrowRight' && event.ctrlKey) {
        // Ctrl + 右箭头：下一页
        event.preventDefault();
        nextPage();
    } else if (event.key === 'PageUp') {
        // Page Up：上一页
        event.preventDefault();
        prevPage();
    } else if (event.key === 'PageDown') {
        // Page Down：下一页
        event.preventDefault();
        nextPage();
    } else if (event.key === 'Home' && event.ctrlKey) {
        // Ctrl + Home：第一页
        event.preventDefault();
        if (currentPage > 1) {
            currentPage = 1;
            displayCurrentPage();
            updatePaginationNavigation();
            scrollToContentTop();
            showKeyboardHint('Ctrl + Home 第一页');
        }
    } else if (event.key === 'End' && event.ctrlKey) {
        // Ctrl + End：最后一页
        event.preventDefault();
        if (currentPage < totalPages) {
            currentPage = totalPages;
            displayCurrentPage();
            updatePaginationNavigation();
            scrollToContentTop();
            showKeyboardHint('Ctrl + End 最后一页');
        }
    }
});

// 点击页面其他地方隐藏分页设置面板
document.addEventListener('click', function(event) {
    const settingsPanel = document.getElementById('page-settings-panel');
    const settingsBtn = event.target.closest('[onclick*="togglePageSettings"]');
    
    if (settingsPanel &&
        settingsPanel.style.display !== 'none' &&
        !settingsPanel.contains(event.target) &&
        !settingsBtn) {
        settingsPanel.style.display = 'none';
    }
});


// ==================== 章节分页功能 ====================

/**
 * 章节列表分页 - 在固定高度容器中智能分页
 */
function paginateChaptersList() {
    if (!chapterPaginationEnabled || chaptersData.length === 0) {
        displayAllChapters();
        return;
    }

    const chaptersContainer = document.getElementById('chapters-list-container');
    const chaptersList = document.getElementById('chapters-list');
    
    if (!chaptersContainer || !chaptersList) return;
    
    // 首先渲染所有章节以获取实际高度
    displayAllChapters();
    
    // 等待DOM更新完成后检查是否需要分页
    setTimeout(() => {
        const containerHeight = chaptersContainer.clientHeight;
        const listHeight = chaptersList.scrollHeight;
        
        console.log(`章节容器检查: 容器高度${containerHeight}px, 列表高度${listHeight}px, 章节数${chaptersData.length}`);
        
        // 如果列表高度超过容器高度，启用分页
        if (listHeight > containerHeight) {
            console.log(`章节列表需要分页`);
            
            // 计算可用高度（减去分页导航栏和边距）
            const paginationElement = document.getElementById('chapter-pagination');
            let paginationHeight = 50; // 分页导航栏的估计高度
            if (paginationElement) {
                paginationElement.style.display = 'flex'; // 临时显示以获取高度
                paginationHeight = paginationElement.offsetHeight || 50;
            }
            
            const availableHeight = containerHeight - paginationHeight - 10; // 减去边距
            
            // 创建临时章节项来测量单个章节的实际高度
            const tempItem = chaptersList.querySelector('.chapter-item');
            let chapterItemHeight = 80; // 默认估计高度
            
            if (tempItem) {
                chapterItemHeight = tempItem.offsetHeight + parseInt(window.getComputedStyle(tempItem).marginBottom);
            }
            
            // 计算每页可以显示的章节数量
            const itemsPerPage = Math.max(3, Math.floor(availableHeight / chapterItemHeight));
            
            console.log(`分页计算: 可用高度${availableHeight}px, 章节项高度${chapterItemHeight}px, 每页${itemsPerPage}个章节`);
            
            // 分页处理
            chapterPagesData = [];
            for (let i = 0; i < chaptersData.length; i += itemsPerPage) {
                chapterPagesData.push(chaptersData.slice(i, i + itemsPerPage));
            }
            
            totalChapterPages = chapterPagesData.length;
            currentChapterPage = 1;
            
            console.log(`章节分页完成: ${totalChapterPages}页, 每页${itemsPerPage}个章节`);
            
            // 显示分页内容
            displayCurrentChapterPage();
            updateChapterPaginationNavigation();
        } else {
            console.log(`章节列表无需分页，可以完全显示`);
            // 隐藏分页导航
            const paginationElement = document.getElementById('chapter-pagination');
            if (paginationElement) {
                paginationElement.style.display = 'none';
            }
        }
    }, 200); // 增加等待时间确保DOM完全更新
}

/**
 * 显示所有章节（不分页模式）
 */
function displayAllChapters() {
    const listContainer = document.getElementById('chapters-list');
    
    listContainer.innerHTML = chaptersData.map(chapter => `
        <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
             onclick="loadChapter('${currentNovelTitle.replace(/'/g, "\\'")}', ${chapter.chapter_number})"
             data-chapter="${chapter.chapter_number}">
            <div class="chapter-item-title">
                第${chapter.chapter_number}章 ${chapter.title}
            </div>
            <div class="chapter-item-meta">
                ${chapter.word_count || 0} 字 • 评分: ${chapter.score || '-'}
            </div>
        </div>
    `).join('');
    
    // 默认隐藏分页导航，如果需要分页会在paginateChaptersList中显示
    const paginationElement = document.getElementById('chapter-pagination');
    if (paginationElement) {
        paginationElement.style.display = 'none';
    }
}

/**
 * 显示当前章节页
 */
function displayCurrentChapterPage() {
    if (chapterPagesData.length === 0) return;
    
    const listContainer = document.getElementById('chapters-list');
    const currentPageData = chapterPagesData[currentChapterPage - 1];
    
    if (!currentPageData) return;
    
    listContainer.innerHTML = `
        <div class="chapter-page-content">
            <div class="chapter-page-inner">
                ${currentPageData.map(chapter => `
                    <div class="chapter-item ${chapter.chapter_number === currentChapter ? 'active' : ''}"
                         onclick="loadChapter('${currentNovelTitle.replace(/'/g, "\\'")}', ${chapter.chapter_number})"
                         data-chapter="${chapter.chapter_number}">
                        <div class="chapter-item-title">
                            第${chapter.chapter_number}章 ${chapter.title}
                        </div>
                        <div class="chapter-item-meta">
                            ${chapter.word_count} 字 • 评分: ${chapter.score || '-'}
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
    
    // 显示分页导航
    const paginationElement = document.getElementById('chapter-pagination');
    if (paginationElement) {
        paginationElement.style.display = 'flex';
    }
}

/**
 * 更新章节分页导航
 */
function updateChapterPaginationNavigation() {
    const currentPageSpan = document.getElementById('current-chapter-page');
    const totalPagesSpan = document.getElementById('total-chapter-pages');
    const prevPageBtn = document.getElementById('prev-chapter-page-btn');
    const nextPageBtn = document.getElementById('next-chapter-page-btn');
    
    if (currentPageSpan) currentPageSpan.textContent = currentChapterPage;
    if (totalPagesSpan) totalPagesSpan.textContent = totalChapterPages;
    
    if (prevPageBtn) {
        prevPageBtn.disabled = currentChapterPage <= 1;
    }
    
    if (nextPageBtn) {
        nextPageBtn.disabled = currentChapterPage >= totalChapterPages;
    }
}

/**
 * 上一章节页
 */
function prevChapterPage() {
    if (currentChapterPage > 1) {
        currentChapterPage--;
        displayCurrentChapterPage();
        updateChapterPaginationNavigation();
        console.log(`切换到章节页 ${currentChapterPage}`);
    }
}

/**
 * 下一章节页
 */
function nextChapterPage() {
    if (currentChapterPage < totalChapterPages) {
        currentChapterPage++;
        displayCurrentChapterPage();
        updateChapterPaginationNavigation();
        console.log(`切换到章节页 ${currentChapterPage}`);
    }
}

/**
 * 获取固定高度 - 视口高度的3倍
 */
function getFixedHeight() {
    const viewportHeight = window.innerHeight;
    return viewportHeight * 3; // 视口高度的3倍
}

/**
 * 动态调整布局高度 - 保持3倍固定高度
 */
function adjustLayoutHeight() {
    const threeColumnLayout = document.querySelector('.three-column-layout');
    
    if (threeColumnLayout) {
        // 使用3倍视口高度：视口高度的3倍减去导航栏
        const layoutHeight = window.innerHeight * 3 - 80; // 视口高度的3倍减去顶部导航栏高度
        threeColumnLayout.style.height = `${layoutHeight}px`;
        
        console.log(`使用3倍固定高度布局: ${layoutHeight}px (视口高度: ${window.innerHeight}px, 3倍高度: ${window.innerHeight * 3}px)`);
        
        // 确保各栏也使用3倍固定高度
        const leftSidebar = document.getElementById('left-sidebar');
        const centerContent = document.getElementById('center-content');
        const rightSidebar = document.getElementById('right-sidebar');
        
        if (leftSidebar) {
            leftSidebar.style.height = `${layoutHeight}px`;
        }
        
        if (centerContent) {
            centerContent.style.height = `${layoutHeight}px`;
        }
        
        if (rightSidebar) {
            rightSidebar.style.height = `${layoutHeight}px`;
        }
        
        // 重新评估章节分页需求
        if (chapterPaginationEnabled) {
            setTimeout(() => {
                paginateChaptersList();
                // 如果有章节内容，也重新计算正文分页
                if (currentChapterContent) {
                    paginateChapterContent(currentChapterContent);
                }
            }, 100);
        }
    }
}

/**
 * 初始化章节分页
 */
function initializeChapterPagination() {
    // 监听窗口大小变化
    window.addEventListener('resize', () => {
        setTimeout(adjustLayoutHeight, 100);
    });
    
    // 初始调整布局
    setTimeout(adjustLayoutHeight, 500);
}
