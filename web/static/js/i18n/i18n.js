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
            }
        } catch (error) {
            console.warn(`[I18N] Failed to load ${lang}.json:`, error);
        }
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
