/**
 * V2 主题切换系统 - 支持暗色/浅色双主题
 * 默认浅色主题，localStorage 持久化
 */
(function() {
    'use strict';
    
    const STORAGE_KEY = 'v2-theme';
    const DEFAULT_THEME = 'light';
    
    function getTheme() {
        try {
            return localStorage.getItem(STORAGE_KEY) || DEFAULT_THEME;
        } catch (e) {
            return DEFAULT_THEME;
        }
    }
    
    function setTheme(theme) {
        if (theme !== 'light' && theme !== 'dark') {
            theme = DEFAULT_THEME;
        }
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem(STORAGE_KEY, theme);
        } catch (e) {}
        updateToggleButton();
    }
    
    function toggleTheme() {
        const current = getTheme();
        const next = current === 'dark' ? 'light' : 'dark';
        setTheme(next);
    }
    
    function updateToggleButton() {
        const btn = document.getElementById('v2-theme-toggle');
        if (!btn) return;
        const isDark = getTheme() === 'dark';
        btn.innerHTML = isDark ? '☀️' : '🌙';
        btn.title = isDark ? '切换浅色主题' : '切换暗色主题';
        btn.setAttribute('aria-label', isDark ? '切换浅色主题' : '切换暗色主题');
    }
    
    // 立即初始化（避免FOUC）
    var theme = getTheme();
    document.documentElement.setAttribute('data-theme', theme);
    
    // DOMReady 后更新按钮
    function onReady() {
        updateToggleButton();
    }
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', onReady);
    } else {
        onReady();
    }
    
    // 暴露全局 API
    window.v2Theme = {
        get: getTheme,
        set: setTheme,
        toggle: toggleTheme
    };
})();
