/**
 * 人物剧照工作室 JavaScript
 * 管理剧照生成、参考图上传和素材库访问
 */

// 全局变量
let referenceImages = [];
let currentGeneratedImage = null;
let loadedCharacter = null; // 🔥 从工作流传入的角色数据

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    loadCharacterFromWorkflow(); // 🔥 加载角色数据
    initializeEventListeners();
});

/**
 * 🔥 从工作流传入的角色数据
 */
function loadCharacterFromWorkflow() {
    try {
        console.log('📸 [剧照工作室] 尝试从localStorage加载角色数据...');
        const characterData = localStorage.getItem('portraitStudio_character');
        console.log('📸 [剧照工作室] localStorage中的数据:', characterData);

        if (characterData) {
            loadedCharacter = JSON.parse(characterData);
            console.log('📸 [剧照工作室] 成功解析角色数据:', loadedCharacter);

            // 检查数据是否过期（超过1小时视为过期）
            const timestamp = loadedCharacter.timestamp || 0;
            const now = Date.now();
            const oneHour = 60 * 60 * 1000;
            
            if (now - timestamp > oneHour) {
                console.log('ℹ️ [剧照工作室] 角色数据已过期（超过1小时），使用默认工作区');
                localStorage.removeItem('portraitStudio_character');
                loadedCharacter = null;
                setupDefaultBackButton();
                return;
            }

            // 如果有预生成的提示词，自动填充
            if (loadedCharacter.generatedPrompt) {
                console.log('📸 [剧照工作室] 发现预生成的提示词，准备填充...');
                const promptEditor = document.getElementById('promptEditor');
                console.log('📸 [剧照工作室] promptEditor元素:', promptEditor);

                if (promptEditor) {
                    promptEditor.value = loadedCharacter.generatedPrompt;
                    console.log('✅ [剧照工作室] 已自动填充提示词');
                } else {
                    console.warn('⚠️ [剧照工作室] 找不到promptEditor元素');
                }
            } else {
                console.warn('⚠️ [剧照工作室] 没有预生成的提示词');
            }

            // 更新页面标题显示角色名称和剧集
            const pageHeader = document.querySelector('.page-header h2');
            if (pageHeader && loadedCharacter.name) {
                let title = `🎨 ${loadedCharacter.name} - 剧照创作`;
                if (loadedCharacter.episode_info) {
                    title += ` (${loadedCharacter.episode_info})`;
                }
                pageHeader.textContent = title;
                console.log('✅ [剧照工作室] 已更新页面标题');
            }

            // 设置返回按钮
            const backBtn = document.getElementById('btnBack');
            if (backBtn) {
                const returnUrl = loadedCharacter.return_url || '/landing';
                backBtn.onclick = () => {
                    window.location.href = returnUrl;
                };
                console.log('✅ [剧照工作室] 已设置返回按钮到:', returnUrl);
            }

            // 🔥 使用完后立即清除，避免下次进入还显示旧数据
            localStorage.removeItem('portraitStudio_character');
            console.log('✅ [剧照工作室] 已清除localStorage中的角色数据');
        } else {
            console.log('ℹ️ [剧照工作室] localStorage中没有角色数据，显示默认工作区');
            setupDefaultBackButton();
        }
    } catch (e) {
        console.error('❌ [剧照工作室] 加载角色数据失败:', e);
        setupDefaultBackButton();
    }
}

/**
 * 设置默认返回按钮（首页）
 */
function setupDefaultBackButton() {
    const backBtn = document.getElementById('btnBack');
    if (backBtn) {
        backBtn.onclick = () => {
            window.location.href = '/landing';
        };
    }
}

/**
 * 初始化事件监听器
 */
function initializeEventListeners() {
    // 文件上传
    const refFileInput = document.getElementById('refFileInput');
    const refUploadZone = document.getElementById('refUploadZone');
    
    if (refFileInput && refUploadZone) {
        // 点击上传区域
        refUploadZone.addEventListener('click', () => {
            refFileInput.click();
        });
        
        // 文件选择
        refFileInput.addEventListener('change', (e) => {
            handleFileSelect(e.target.files);
        });
        
        // 拖拽上传
        refUploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            refUploadZone.classList.add('dragover');
        });
        
        refUploadZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            refUploadZone.classList.remove('dragover');
        });
        
        refUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            refUploadZone.classList.remove('dragover');
            const files = e.dataTransfer.files;
            handleFileSelect(files);
        });
    }
    
    // 比例按钮
    const ratioBtns = document.querySelectorAll('.ratio-btn');
    ratioBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            ratioBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });
    
    // 快速模板
    const templateBtns = document.querySelectorAll('.template-btn');
    templateBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            applyTemplate(btn.dataset.template);
        });
    });
    
    // 生成按钮
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generatePortrait);
    }
    
    // 复制按钮
    const copyPromptBtn = document.getElementById('copyPromptBtn');
    if (copyPromptBtn) {
        copyPromptBtn.addEventListener('click', copyPrompt);
    }
    
    // 结果卡片按钮
    const downloadResultBtn = document.getElementById('downloadResultBtn');
    if (downloadResultBtn) {
        downloadResultBtn.addEventListener('click', downloadResult);
    }
    
    const useAsRefBtn = document.getElementById('useAsRefBtn');
    if (useAsRefBtn) {
        useAsRefBtn.addEventListener('click', useAsReference);
    }
    
    const viewLibraryBtn = document.getElementById('viewLibraryBtn');
    if (viewLibraryBtn) {
        viewLibraryBtn.addEventListener('click', () => {
            window.location.href = '/still-image-library';
        });
    }
    
    const regenerateBtn = document.getElementById('regenerateBtn');
    if (regenerateBtn) {
        regenerateBtn.addEventListener('click', generatePortrait);
    }
}

/**
 * 处理文件选择
 */
function handleFileSelect(files) {
    const maxFiles = 5;
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    
    for (let file of files) {
        if (referenceImages.length >= maxFiles) {
            showToast('最多只能上传5张参考图');
            break;
        }
        
        if (!validTypes.includes(file.type)) {
            showToast(`不支持的文件类型: ${file.type}`);
            continue;
        }
        
        // 读取文件为base64
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result;
            referenceImages.push(base64);
            updateReferencePreview();
        };
        reader.readAsDataURL(file);
    }
    
    // 清空input，允许重新选择相同文件
    const refFileInput = document.getElementById('refFileInput');
    if (refFileInput) {
        refFileInput.value = '';
    }
}

/**
 * 更新参考图预览
 */
function updateReferencePreview() {
    const container = document.getElementById('refPreviewContainer');
    const countInfo = document.getElementById('refCountInfo');
    const uploadZone = document.getElementById('refUploadZone');
    
    if (referenceImages.length === 0) {
        container.style.display = 'none';
        countInfo.style.display = 'none';
        uploadZone.style.display = 'block';
        return;
    }
    
    container.style.display = 'flex';
    countInfo.style.display = 'block';
    uploadZone.style.display = 'none';
    
    document.getElementById('refCount').textContent = referenceImages.length;
    
    // 清空容器
    container.innerHTML = '';
    
    // 添加预览图
    referenceImages.forEach((base64, index) => {
        const wrapper = document.createElement('div');
        wrapper.className = 'preview-item';
        
        const img = document.createElement('img');
        img.src = base64;
        img.alt = `参考图 ${index + 1}`;
        
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-preview-btn';
        removeBtn.innerHTML = '✕';
        removeBtn.onclick = () => {
            referenceImages.splice(index, 1);
            updateReferencePreview();
        };
        
        wrapper.appendChild(img);
        wrapper.appendChild(removeBtn);
        container.appendChild(wrapper);
    });
}

/**
 * 应用快速模板
 */
function applyTemplate(template) {
    const templates = {
        'xianxia': '仙侠剑仙风格：一位修仙者的形象，白发如雪，仙气缭绕，身穿白色仙袍，手持发光的长剑，站在云端之上，背景是壮观的云海和山峦。',
        'modern': '现代都市风格：时尚的都市青年，穿着潮流服装，背景是繁华的城市街道，霓虹灯闪烁。',
        'fantasy': '奇幻魔法风格：神秘的魔法师，穿着华丽的法师袍，手持发光的法杖，周围环绕着魔法元素。',
        'sci': '科幻未来风格：未来战士，穿着高科技战甲，手持能量武器，站在充满科技感的未来城市。',
        'romance': '浪漫唯美风格：温柔美丽的少女，长发飘逸，身穿轻盈的连衣裙，站在花海中，阳光洒落。'
    };
    
    const promptEditor = document.getElementById('promptEditor');
    if (promptEditor && templates[template]) {
        // 直接替换提示词内容，而不是追加
        promptEditor.value = templates[template];
        
        // 模板名称映射
        const templateNames = {
            'xianxia': '仙侠剑仙',
            'modern': '现代都市',
            'fantasy': '奇幻魔法',
            'sci': '科幻未来',
            'romance': '浪漫唯美'
        };
        
        showToast(`已应用${templateNames[template] || template}模板`);
    }
}

/**
 * 生成剧照
 */
async function generatePortrait() {
    const promptEditor = document.getElementById('promptEditor');
    const prompt = promptEditor.value.trim();

    if (!prompt) {
        showToast('请输入生成提示词');
        return;
    }

    const aspectRatio = document.querySelector('.ratio-btn.active')?.dataset.ratio || '9:16';
    const imageSize = document.getElementById('qualitySelect')?.value || '1K';
    const styleSelect = document.getElementById('styleSelect')?.value || '';

    // 显示进度
    const progressCard = document.getElementById('progressCard');
    const resultCard = document.getElementById('resultCard');
    const generateBtn = document.getElementById('generateBtn');

    progressCard.style.display = 'block';
    resultCard.style.display = 'none';
    generateBtn.disabled = true;

    try {
        // 🔥 获取剧集信息（如果有）
        let episodeInfo = '';
        if (loadedCharacter && loadedCharacter.episode_info) {
            episodeInfo = loadedCharacter.episode_info;
        }

        const response = await fetch('/api/video/generate-character-portrait', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                custom_prompt: prompt,
                style: styleSelect,
                aspect_ratio: aspectRatio,
                image_size: imageSize,
                reference_images: referenceImages,
                // 🔥 传递角色和剧集信息用于文件命名
                character_data: loadedCharacter || {},
                episode_info: episodeInfo
            })
        });

        const result = await response.json();

        if (result.success) {
            currentGeneratedImage = result;

            // 显示结果
            const resultImage = document.getElementById('resultImage');
            resultImage.src = result.image_url;

            progressCard.style.display = 'none';
            resultCard.style.display = 'block';

            showToast(`剧照生成成功！${result.message || ''}`);

            // 🔥 如果是从工作流打开的，保存剧照信息并返回
            if (loadedCharacter && loadedCharacter.name) {
                console.log('📸 [剧照工作室] 准备保存剧照信息到localStorage...');
                console.log('📸 [剧照工作室] loadedCharacter:', loadedCharacter);
                console.log('📸 [剧照工作室] result:', result);

                const portraitResult = {
                    characterName: loadedCharacter.name,
                    imageUrl: result.image_url,
                    imagePath: result.image_path,
                    timestamp: new Date().toISOString()
                };
                console.log('📸 [剧照工作室] 即将保存的数据:', portraitResult);

                localStorage.setItem('portraitStudio_result', JSON.stringify(portraitResult));
                console.log('✅ [剧照工作室] 剧照信息已保存到localStorage');
                console.log('📸 [剧照工作室] 保存的imageUrl:', portraitResult.imageUrl);
            }
        } else {
            throw new Error(result.error || '生成失败');
        }
    } catch (error) {
        console.error('生成剧照失败:', error);
        showToast(`生成失败: ${error.message || '未知错误'}`);
        progressCard.style.display = 'none';
    } finally {
        generateBtn.disabled = false;
    }
}

/**
 * 复制提示词
 */
function copyPrompt() {
    const promptEditor = document.getElementById('promptEditor');
    const prompt = promptEditor?.value || '';
    
    if (!prompt) {
        showToast('没有可复制的提示词');
        return;
    }
    
    navigator.clipboard.writeText(prompt).then(() => {
        showToast('提示词已复制到剪贴板');
    }).catch(() => {
        showToast('复制失败，请手动复制');
    });
}

/**
 * 下载剧照
 */
function downloadResult() {
    if (!currentGeneratedImage || !currentGeneratedImage.image_url) {
        showToast('没有可下载的剧照');
        return;
    }
    
    const link = document.createElement('a');
    link.href = currentGeneratedImage.image_url;
    link.download = `portrait_${Date.now()}.png`;
    link.target = '_blank';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('剧照下载已开始');
}

/**
 * 用作参考图
 */
function useAsReference() {
    if (!currentGeneratedImage || !currentGeneratedImage.image_url) {
        showToast('没有可用的剧照');
        return;
    }
    
    // 将当前生成的剧照添加到参考图列表
    if (referenceImages.length >= 5) {
        showToast('参考图已满（最多5张），请先删除一些');
        return;
    }
    
    referenceImages.push(currentGeneratedImage.image_url);
    updateReferencePreview();
    
    showToast('已添加到参考图列表');
}

/**
 * 显示Toast通知
 */
function showToast(message) {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
