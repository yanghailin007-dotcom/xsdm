/**
 * 大文娱系统 V2 - 国际化 (i18n) 模块
 * 支持多语言切换和动态翻译
 */

const I18N = (function() {
    'use strict';

    // 翻译数据
    const translations = {
        'zh-CN': {
            // Phase 2 页面翻译
            'phase2.title': '第二阶段：章节生成',
            'phase2.subtitle': '生成小说章节内容',
            'phase2.step.select': '选择项目',
            'phase2.step.config': '配置参数',
            'phase2.step.generate': '生成章节',
            'phase2.step.preview': '预览结果',
            'phase2.project.placeholder': '请选择要续写的小说项目',
            'phase2.field.startChapter': '起始章节',
            'phase2.field.chapterCount': '生成章节数',
            'phase2.field.batchSize': '每批生成数量',
            'phase2.field.model': 'AI模型',
            'phase2.btn.start': '开始生成',
            'phase2.progress.title': '正在生成章节...',
            'phase2.progress.steps': '详细步骤进度',
            'phase2.result.title': '章节生成完成',
            'phase2.result.continue': '继续生成',
            'phase2.guide.title': '使用说明',
            'phase2.guide.tips': '生成技巧',
            
            // 通用翻译
            'common.loading': '加载中...',
            'common.save': '保存',
            'common.cancel': '取消',
            'common.confirm': '确认',
            'common.delete': '删除',
            'common.edit': '编辑',
            'common.create': '创建',
            'common.search': '搜索',
            'common.submit': '提交',
            'common.close': '关闭',
            'common.back': '返回',
            'common.next': '下一步',
            'common.prev': '上一步',
            'common.success': '成功',
            'common.error': '错误',
            'common.warning': '警告',
            'common.info': '信息',
        },
        'zh-TW': {
            // Phase 2 頁面翻譯
            'phase2.title': '第二階段：章節生成',
            'phase2.subtitle': '生成小說章節內容',
            'phase2.step.select': '選擇項目',
            'phase2.step.config': '配置參數',
            'phase2.step.generate': '生成章節',
            'phase2.step.preview': '預覽結果',
            'phase2.project.placeholder': '請選擇要續寫的小說項目',
            'phase2.field.startChapter': '起始章節',
            'phase2.field.chapterCount': '生成章節數',
            'phase2.field.batchSize': '每批生成數量',
            'phase2.field.model': 'AI模型',
            'phase2.btn.start': '開始生成',
            'phase2.progress.title': '正在生成章節...',
            'phase2.progress.steps': '詳細步驟進度',
            'phase2.result.title': '章節生成完成',
            'phase2.result.continue': '繼續生成',
            'phase2.guide.title': '使用說明',
            'phase2.guide.tips': '生成技巧',
            
            // 通用翻譯
            'common.loading': '載入中...',
            'common.save': '儲存',
            'common.cancel': '取消',
            'common.confirm': '確認',
            'common.delete': '刪除',
            'common.edit': '編輯',
            'common.create': '建立',
            'common.search': '搜尋',
            'common.submit': '提交',
            'common.close': '關閉',
            'common.back': '返回',
            'common.next': '下一步',
            'common.prev': '上一步',
            'common.success': '成功',
            'common.error': '錯誤',
            'common.warning': '警告',
            'common.info': '資訊',
        },
        'en': {
            // Phase 2 Page Translations
            'phase2.title': 'Phase 2: Chapter Generation',
            'phase2.subtitle': 'Generate Novel Chapters',
            'phase2.step.select': 'Select Project',
            'phase2.step.config': 'Configure Parameters',
            'phase2.step.generate': 'Generate Chapters',
            'phase2.step.preview': 'Preview Results',
            'phase2.project.placeholder': 'Please select a novel project to continue',
            'phase2.field.startChapter': 'Start Chapter',
            'phase2.field.chapterCount': 'Number of Chapters',
            'phase2.field.batchSize': 'Batch Size',
            'phase2.field.model': 'AI Model',
            'phase2.btn.start': 'Start Generation',
            'phase2.progress.title': 'Generating Chapters...',
            'phase2.progress.steps': 'Detailed Progress',
            'phase2.result.title': 'Chapter Generation Complete',
            'phase2.result.continue': 'Continue Generation',
            'phase2.guide.title': 'Instructions',
            'phase2.guide.tips': 'Generation Tips',
            
            // Common Translations
            'common.loading': 'Loading...',
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.confirm': 'Confirm',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.create': 'Create',
            'common.search': 'Search',
            'common.submit': 'Submit',
            'common.close': 'Close',
            'common.back': 'Back',
            'common.next': 'Next',
            'common.prev': 'Previous',
            'common.success': 'Success',
            'common.error': 'Error',
            'common.warning': 'Warning',
            'common.info': 'Info',
        }
    };

    // 当前语言
    let currentLanguage = 'zh-CN';

    // 从 localStorage 加载语言设置
    function loadLanguageSetting() {
        try {
            const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
            if (settings.language && translations[settings.language]) {
                currentLanguage = settings.language;
            }
        } catch (e) {
            console.warn('Failed to load language setting:', e);
        }
    }

    // 获取翻译
    function getTranslation(key, lang) {
        const language = lang || currentLanguage;
        const trans = translations[language];
        if (trans && trans[key]) {
            return trans[key];
        }
        // 回退到简体中文
        if (language !== 'zh-CN' && translations['zh-CN'][key]) {
            return translations['zh-CN'][key];
        }
        // 返回键名
        return key;
    }

    // 设置语言
    function setLanguage(lang) {
        if (translations[lang]) {
            currentLanguage = lang;
            applyTranslations();
            
            // 保存设置
            try {
                const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
                settings.language = lang;
                localStorage.setItem('userSettings', JSON.stringify(settings));
            } catch (e) {
                console.warn('Failed to save language setting:', e);
            }
            
            // 触发语言切换事件
            document.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
            
            return true;
        }
        return false;
    }

    // 应用翻译到页面
    function applyTranslations() {
        // 翻译带有 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = getTranslation(key);
            
            // 根据元素类型设置翻译
            if (element.hasAttribute('data-i18n-attr')) {
                // 设置指定属性
                const attr = element.getAttribute('data-i18n-attr');
                element.setAttribute(attr, translation);
            } else if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                // 输入框的 placeholder
                if (element.hasAttribute('placeholder')) {
                    element.placeholder = translation;
                } else {
                    element.value = translation;
                }
            } else {
                // 普通文本内容
                element.textContent = translation;
            }
        });

        // 翻译带有 data-i18n-placeholder 属性的元素（用于 placeholder）
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = getTranslation(key);
        });

        // 翻译带有 data-i18n-title 属性的元素（用于 title）
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = getTranslation(key);
        });
    }

    // 初始化
    function init() {
        loadLanguageSetting();
        applyTranslations();
    }

    // 公共 API
    return {
        init,
        setLanguage,
        getTranslation,
        applyTranslations,
        getCurrentLanguage: () => currentLanguage,
        getSupportedLanguages: () => Object.keys(translations)
    };
})();

// DOM 加载完成后自动初始化
document.addEventListener('DOMContentLoaded', function() {
    I18N.init();
});
