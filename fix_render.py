with open('web/templates/pages/v2/chapter-generation.html', 'r', encoding='utf-8') as f:
    data = f.read()

# 1. Fix renderMarkdown
old_render = """function renderMarkdown(text) {
    if (!text) return '';
    const lines = text.split('\\n');
    let html = '';
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
            html += '<br>';
            continue;
        }
        if (trimmed.startsWith('# ')) {
            html += `<h3 style="color:var(--text-primary);font-size:16px;margin:14px 0 8px;font-weight:700;">${escapeHtml(trimmed.replace(/^#\\s*/, ''))}</h3>`;
        } else if (trimmed.startsWith('## ')) {
            html += `<h4 style="color:var(--accent);font-size:14px;margin:12px 0 6px;font-weight:600;">${escapeHtml(trimmed.replace(/^##\\s*/, ''))}</h4>`;
        } else if (trimmed.startsWith('### ')) {
            html += `<h5 style="color:var(--text-secondary);font-size:13px;margin:10px 0 5px;font-weight:600;">${escapeHtml(trimmed.replace(/^###\\s*/, ''))}</h5>`;
        } else if (trimmed.startsWith('- ')) {
            html += `<p style="margin-left:16px;color:var(--text-secondary);font-size:13px;">• ${escapeHtml(trimmed.replace(/^-\\s*/, ''))}</p>`;
        } else if (trimmed.startsWith('**') && trimmed.endsWith('**')) {
            html += `<p style="font-weight:600;color:var(--text-primary);">${escapeHtml(trimmed.replace(/\\*\\*/g, ''))}</p>`;
        } else {
            html += `<p>${escapeHtml(trimmed)}</p>`;
        }
    }
    return html;
}"""

new_render = """function renderMarkdown(text) {
    if (!text) return '';
    const lines = text.split('\\n');
    let html = '';
    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
            html += '<br>';
            continue;
        }
        // 先处理行内 **粗体**
        let processed = escapeHtml(trimmed);
        processed = processed.replace(/\\*\\*(.+?)\\*\\*/g, '<strong style="color:var(--text-primary);">$1</strong>');

        if (trimmed.startsWith('# ')) {
            html += '<h3 style="color:var(--text-primary);font-size:16px;margin:14px 0 8px;font-weight:700;">' + processed.replace(/^#\\s*/, '') + '</h3>';
        } else if (trimmed.startsWith('## ')) {
            html += '<h4 style="color:var(--accent);font-size:14px;margin:12px 0 6px;font-weight:600;">' + processed.replace(/^##\\s*/, '') + '</h4>';
        } else if (trimmed.startsWith('### ')) {
            html += '<h5 style="color:var(--text-secondary);font-size:13px;margin:10px 0 5px;font-weight:600;">' + processed.replace(/^###\\s*/, '') + '</h5>';
        } else if (trimmed.startsWith('- ')) {
            html += '<p style="margin-left:16px;color:var(--text-secondary);font-size:13px;">• ' + processed.replace(/^-\\s*/, '') + '</p>';
        } else if (/^\\d+\\.\\s/.test(trimmed)) {
            html += '<p style="margin-left:16px;color:var(--text-secondary);font-size:13px;">' + processed + '</p>';
        } else {
            html += '<p>' + processed + '</p>';
        }
    }
    return html;
}"""

if old_render in data:
    data = data.replace(old_render, new_render)
    print('renderMarkdown updated')
else:
    print('ERROR: old renderMarkdown not found')

with open('web/templates/pages/v2/chapter-generation.html', 'w', encoding='utf-8', newline='\n') as f:
    f.write(data)
