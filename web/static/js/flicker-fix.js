// ==================== 页面闪烁修复 - JavaScript补丁 ====================
// 修复加载创意后的持续闪烁问题

(function() {
    'use strict';
    
    // 防止重复调用
    let isFillingFromCreative = false;
    let lastSelectedIdeaId = null;
    let fillRequestTimer = null;
    
    // 保存原始函数
    const originalFillFromCreativeIdea = window.fillFromCreativeIdea;
    
    // 创建修复版本
    window.fillFromCreativeIdea = function() {
        const select = document.getElementById('creative-idea-select');
        if (!select) return;
        
        const ideaId = parseInt(select.value);
        
        // 检查是否真的是新的选择
        if (ideaId === lastSelectedIdeaId) {
            console.log('[闪烁修复] 跳过重复的创意ID:', ideaId);
            return;
        }
        
        // 清除之前的定时器
        if (fillRequestTimer) {
            clearTimeout(fillRequestTimer);
        }
        
        // 使用防抖,延迟50ms执行
        fillRequestTimer = setTimeout(() => {
            // 再次检查是否已在处理中
            if (isFillingFromCreative) {
                console.log('[闪烁修复] 已在填充中,跳过此次请求');
                return;
            }
            
            // 标记开始处理
            isFillingFromCreative = true;
            lastSelectedIdeaId = ideaId;
            
            console.log('[闪烁修复] 开始填充创意:', ideaId);
            
            try {
                // 调用原始函数
                if (typeof originalFillFromCreativeIdea === 'function') {
                    originalFillFromCreativeIdea();
                } else {
                    // 如果原始函数不存在,执行内联逻辑
                    fillFromCreativeIdeaInline(ideaId);
                }
                
                // 禁用预览区域的所有动画
                disableAnimationsForPreview();
                
            } finally {
                // 延迟重置标志,确保DOM更新完成
                setTimeout(() => {
                    isFillingFromCreative = false;
                    console.log('[闪烁修复] 填充完成');
                }, 100);
            }
        }, 50);
    };
    
    // 内联填充逻辑(备用)
    function fillFromCreativeIdeaInline(ideaId) {
        if (!ideaId) {
            const previewDiv = document.getElementById('creative-idea-preview-simple');
            if (previewDiv) {
                previewDiv.style.display = 'none';
            }
            return;
        }
        
        const idea = window.loadedCreativeIdeas?.find(i => i.id === ideaId);
        if (!idea) return;
        
        // 填充表单
        const titleField = document.getElementById('novel-title');
        const synopsisField = document.getElementById('novel-synopsis');
        const coreSettingField = document.getElementById('core-setting');
        const sellingPointsField = document.getElementById('core-selling-points');
        
        if (titleField) titleField.value = idea.raw_data?.novelTitle || `创意${idea.id}的小说`;
        if (synopsisField) synopsisField.value = idea.core_setting ? idea.core_setting.substring(0, 200) : '';
        if (coreSettingField) coreSettingField.value = idea.core_setting || '';
        if (sellingPointsField) sellingPointsField.value = idea.core_selling_points || '爽文节奏 + 独特设定 + 人物成长';
        
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
            
            previewContent.innerHTML = previewHtml;
        }
    }
    
    // 禁用预览区域的动画
    function disableAnimationsForPreview() {
        const previewElements = [
            'creative-idea-preview-simple',
            'preview-content',
            'creative-library-content'
        ];
        
        previewElements.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.setProperty('transition', 'none', 'important');
                element.style.setProperty('animation', 'none', 'important');
                element.style.setProperty('transform', 'none', 'important');
            }
        });
        
        // 禁用所有子元素的动画
        const previewContent = document.getElementById('preview-content');
        if (previewContent) {
            const allChildren = previewContent.querySelectorAll('*');
            allChildren.forEach(child => {
                child.style.setProperty('transition', 'none', 'important');
                child.style.setProperty('animation', 'none', 'important');
            });
        }
    }
    
    // 监听DOM变化,防止其他脚本触发闪烁
    function observePreviewChanges() {
        const previewContent = document.getElementById('preview-content');
        if (!previewContent) return;
        
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    // 禁用新添加元素的动画
                    disableAnimationsForPreview();
                }
            });
        });
        
        observer.observe(previewContent, {
            childList: true,
            subtree: true,
            characterData: true
        });
        
        console.log('[闪烁修复] 已启动预览区域监听');
    }
    
    // 页面加载完成后初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    function init() {
        console.log('[闪烁修复] 初始化防闪烁补丁');
        
        // 等待一下确保创意库元素已加载
        setTimeout(() => {
            observePreviewChanges();
            
            // 立即禁用现有元素的动画
            disableAnimationsForPreview();
            
            console.log('[闪烁修复] 补丁已激活');
        }, 100);
    }
    
    // 导出调试函数
    window.FlickerFix = {
        isEnabled: true,
        disableAnimations: disableAnimationsForPreview,
        getStatus: function() {
            return {
                isFilling: isFillingFromCreative,
                lastSelectedId: lastSelectedIdeaId,
                hasPendingRequest: fillRequestTimer !== null
            };
        }
    };
    
})();
