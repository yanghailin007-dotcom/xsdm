/**
 * Internationalization (i18n) Module
 * 简单的国际化支持
 */

const I18N = {
    currentLang: 'zh-CN',
    translations: {},
    
    init() {
        // 检测浏览器语言
        const browserLang = navigator.language || navigator.userLanguage;
        this.currentLang = this.supportedLanguages().includes(browserLang) ? browserLang : 'zh-CN';
        
        // 加载翻译文件
        this.loadTranslations(this.currentLang);
    },
    
    supportedLanguages() {
        return ['zh-CN', 'zh-TW', 'en', 'ja', 'ko'];
    },
    
    async loadTranslations(lang) {
        try {
            const response = await fetch(`/static/js/i18n/${lang}.json`);
            if (response.ok) {
                this.translations = await response.json();
                console.log(`[I18N] Loaded ${lang}.json: ${Object.keys(this.translations).length} keys`);
                this.applyTranslations();
            }
        } catch (error) {
            console.warn(`[I18N] Failed to load ${lang}.json:`, error);
        }
    }
    
    applyTranslations() {
        // 应用翻译到所有 data-i18n 元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const fallback = el.textContent;
            const translation = this.t(key, fallback);
            if (translation) {
                el.textContent = translation;
            }
        });
        
        // 应用翻译到所有 data-i18n-placeholder 元素
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const fallback = el.getAttribute('placeholder');
            const translation = this.t(key, fallback);
            if (translation) {
                el.setAttribute('placeholder', translation);
            }
        });
        
        console.log('[I18N] Translations applied');
    },
    
    t(key, fallback = null) {
        return this.translations[key] || fallback || key;
    },
    
    setLanguage(lang) {
        this.currentLang = lang;
        this.loadTranslations(lang);
    }
};

// 简单的翻译函数（全局可用）
function t(key, fallback = null) {
    return I18N.t(key, fallback);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    I18N.init();
});
