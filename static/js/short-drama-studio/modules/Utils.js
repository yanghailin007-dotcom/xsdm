/**
 * 工具函数模块
 * 包含纯函数，不依赖实例状态
 */

const UtilsMixin = {
    /**
     * HTML 转义
     * @param {string} text - 要转义的文本
     * @returns {string} 转义后的文本
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    },

    /**
     * 解析对话数据
     * @param {string|object} dialogue - 对话数据
     * @returns {object} { speaker, lines, tone }
     */
    parseDialogue(dialogue) {
        let speaker = '';
        let lines = '';
        let tone = '';

        if (typeof dialogue === 'string') {
            lines = dialogue;
            // 尝试从字符串中解析角色名: "(角色名): 台词" 或 "角色名: 台词"
            const speakerMatch = lines.match(/^[(\[]?([^)\]:]+)[)\]]?:?\s*(.+)$/);
            if (speakerMatch) {
                speaker = speakerMatch[1].trim();
                lines = speakerMatch[2].trim();
            } else {
                speaker = '未知';
            }
        } else if (typeof dialogue === 'object' && dialogue !== null) {
            speaker = dialogue.speaker || '';
            lines = dialogue.lines || '';
            tone = dialogue.tone || '';
            // 如果speaker为空，尝试从lines中解析
            if (!speaker && lines) {
                const speakerMatch = lines.match(/^[(\[]?([^)\]:]+)[)\]]?:?\s*(.+)$/);
                if (speakerMatch) {
                    speaker = speakerMatch[1].trim();
                    lines = speakerMatch[2].trim();
                }
            }
        }

        return { speaker, lines, tone };
    },

    /**
     * 清理文件名（移除非法字符）
     * @param {string} name - 原始文件名
     * @returns {string} 清理后的文件名
     */
    sanitizeFileName(name) {
        const invalidChars = ['<', '>', ':', '"', '/', '\\', '|', '?', '、', '？', '！', '＊', '＂', '＜', '＞', '／', '＼', '｜', '!'];
        let result = name;
        for (const char of invalidChars) {
            result = result.replace(new RegExp(char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), '_');
        }
        return result.replace(/^_+|_+$/g, '');
    }
};

// 导出模块（支持多种模块系统）
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UtilsMixin;
} else if (typeof define === 'function' && define.amd) {
    define([], function() { return UtilsMixin; });
} else {
    window.UtilsMixin = UtilsMixin;
}
