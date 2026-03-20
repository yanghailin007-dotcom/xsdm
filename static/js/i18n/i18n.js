/**
 * 大文娱创作平台 - 国际化(i18n)系统 v2
 * 支持动态加载语言文件
 * 
 * 使用方法:
 * 1. 确保 i18n 目录下有对应语言的 JSON 文件 (zh-CN.json, en.json 等)
 * 2. 页面加载时会自动初始化并加载保存的语言
 * 3. 使用 I18N.t('key') 获取翻译
 * 4. 使用 I18N.setLanguage('en') 切换语言
 */

const I18N = {
    // 当前语言
    currentLang: 'zh-CN',
    
    // 可用语言列表
    availableLanguages: ['zh-CN', 'zh-TW', 'en', 'es', 'fr', 'de', 'ja', 'ko'],
    
    // 翻译字典（动态加载）
    translations: {},
    
    // 是否正在加载
    isLoading: false,
    
    // 加载队列
    loadQueue: [],

    /**
     * 初始化 i18n 系统
     */
    async init() {
        // 从 localStorage 读取语言设置
        const savedSettings = JSON.parse(localStorage.getItem('userSettings') || '{}');
        if (savedSettings.language && this.availableLanguages.includes(savedSettings.language)) {
            this.currentLang = savedSettings.language;
        } else {
            // 检测浏览器语言
            const browserLang = navigator.language || navigator.userLanguage;
            if (browserLang.startsWith('zh-TW') || browserLang.startsWith('zh-HK')) {
                this.currentLang = 'zh-TW';
            } else if (browserLang.startsWith('zh')) {
                this.currentLang = 'zh-CN';
            } else if (this.availableLanguages.includes(browserLang)) {
                this.currentLang = browserLang;
            } else {
                // 检查浏览器语言的前缀是否匹配
                const langPrefix = browserLang.split('-')[0];
                const matchedLang = this.availableLanguages.find(l => l.startsWith(langPrefix));
                if (matchedLang) {
                    this.currentLang = matchedLang;
                } else {
                    this.currentLang = 'en';
                }
            }
        }
        
        // 加载当前语言的翻译文件
        await this.loadLanguage(this.currentLang);
        
        // 应用语言到页面
        this.applyToPage();
        
        // 触发自定义事件
        window.dispatchEvent(new CustomEvent('i18nReady', { detail: { language: this.currentLang } }));
    },

    /**
     * 加载指定语言的翻译文件
     * @param {string} lang - 语言代码
     */
    async loadLanguage(lang) {
        if (this.translations[lang]) {
            // 已经加载过
            return;
        }
        
        if (this.isLoading) {
            // 如果正在加载其他语言，等待
            return new Promise((resolve) => {
                this.loadQueue.push(() => {
                    resolve();
                });
            });
        }
        
        this.isLoading = true;
        
        try {
            // 从 body 的 data-static-url 获取静态文件基础路径（支持部署到子路径）
            const staticUrl = document.body.dataset.staticUrl || '/static/';
            const response = await fetch(`${staticUrl}js/i18n/${lang}.json`);
            if (!response.ok) {
                throw new Error(`Failed to load ${lang}.json: ${response.status}`);
            }
            
            this.translations[lang] = await response.json();
            console.log(`[I18N] Loaded ${lang}.json: ${Object.keys(this.translations[lang]).length} keys`);
        } catch (error) {
            console.error(`[I18N] Error loading ${lang}.json:`, error);
            // 加载失败时使用空对象
            this.translations[lang] = {};
        } finally {
            this.isLoading = false;
            
            // 处理队列
            while (this.loadQueue.length > 0) {
                const callback = this.loadQueue.shift();
                callback();
            }
        }
    },

    /**
     * 切换语言
     * @param {string} lang - 语言代码
     */
    async setLanguage(lang) {
        if (!this.availableLanguages.includes(lang)) {
            console.error(`[I18N] Unsupported language: ${lang}`);
            return;
        }
        
        if (this.currentLang === lang) {
            return;
        }
        
        // 加载新语言（如果还没加载）
        await this.loadLanguage(lang);
        
        this.currentLang = lang;
        
        // 保存设置
        this.saveLanguage();
        
        // 应用新语言
        this.applyToPage();
        
        // 更新 HTML lang 属性
        document.documentElement.lang = lang;
        
        // 触发自定义事件
        const event = new CustomEvent('languageChanged', { 
            detail: { language: lang },
            bubbles: true,
            cancelable: true
        });
        window.dispatchEvent(event);
        document.dispatchEvent(event);
        
        console.log(`[I18N] Language changed to: ${lang}`);
    },

    /**
     * 保存语言设置到 localStorage
     */
    saveLanguage() {
        const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
        settings.language = this.currentLang;
        localStorage.setItem('userSettings', JSON.stringify(settings));
    },

    /**
     * 获取翻译文本
     * @param {string} key - 翻译键
     * @param {object} params - 替换参数
     * @returns {string} 翻译后的文本
     */
    t(key, params = {}) {
        // 优先使用当前语言的翻译
        let translation = this.translations[this.currentLang]?.[key];
        
        // 如果当前语言没有，尝试英文
        if (!translation && this.currentLang !== 'en') {
            translation = this.translations['en']?.[key];
        }
        
        // 如果还没有，返回键名本身
        if (!translation) {
            return key;
        }
        
        // 替换参数
        return translation.replace(/\{\{(\w+)\}\}/g, (match, paramKey) => {
            return params[paramKey] !== undefined ? params[paramKey] : match;
        });
    },

    /**
     * 应用翻译到页面所有带有 data-i18n 属性的元素
     */
    applyToPage() {
        // 翻译带有 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const attr = el.getAttribute('data-i18n-attr');
            const paramsAttr = el.getAttribute('data-i18n-params');
            
            // 解析参数
            let params = {};
            if (paramsAttr) {
                try {
                    params = JSON.parse(paramsAttr);
                } catch (e) {
                    console.warn('Invalid data-i18n-params:', paramsAttr);
                }
            }
            
            if (key) {
                const translation = this.t(key, params);
                if (attr) {
                    // 如果指定了属性，则翻译该属性
                    el.setAttribute(attr, translation);
                } else if (el.hasAttribute('placeholder')) {
                    el.placeholder = translation;
                } else if (el.tagName === 'OPTION') {
                    // 对于下拉选项，保持 value 不变，只更新显示文本
                    el.textContent = translation;
                } else if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    if (el.hasAttribute('value')) {
                        el.value = translation;
                    } else {
                        el.textContent = translation;
                    }
                } else {
                    el.textContent = translation;
                }
            }
        });
        
        // 翻译带有 data-i18n-html 属性的元素（保留 HTML）
        document.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            if (key) {
                el.innerHTML = this.t(key);
            }
        });
        
        // 翻译带有 data-i18n-title 属性的元素的 title
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (key) {
                el.title = this.t(key);
            }
        });
        
        // 翻译带有 data-i18n-placeholder 属性的元素的 placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (key) {
                el.placeholder = this.t(key);
            }
        });
        
        // 更新页面标题
        const titleEl = document.querySelector('title[data-i18n]');
        if (titleEl) {
            document.title = this.t(titleEl.getAttribute('data-i18n'));
        }
    },

    /**
     * 动态翻译单个元素
     * @param {HTMLElement} element - 要翻译的元素
     */
    translateElement(element) {
        if (element.hasAttribute('data-i18n')) {
            const key = element.getAttribute('data-i18n');
            if (element.hasAttribute('placeholder')) {
                element.placeholder = this.t(key);
            } else {
                element.textContent = this.t(key);
            }
        }
    },

    /**
     * 获取当前语言
     * @returns {string} 当前语言代码
     */
    getCurrentLanguage() {
        return this.currentLang;
    },

    /**
     * 检查翻译键是否存在
     * @param {string} key - 翻译键
     * @returns {boolean}
     */
    hasKey(key) {
        return !!this.translations[this.currentLang]?.[key] || 
               !!this.translations['en']?.[key];
    }
};

// 简写函数
function t(key, params) {
    return I18N.t(key, params);
}

// 页面加载时初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => I18N.init());
} else {
    // DOM 已加载
    I18N.init();
}

// 导出供其他脚本使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = I18N;
}
