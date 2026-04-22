/**
 * 工具函数
 */

export function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function formatDate(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}

// 从细纲文本中提取章节信息
export function parseOutline(md) {
  const chapters = [];
  const lines = md.split('\n');
  let current = null;

  for (const line of lines) {
    const trimmed = line.trim();
    // 匹配 # 第X章 或 ## 第X章
    const chapterMatch = trimmed.match(/^#{1,2}\s*第[\d一二三四五六七八九十百千]+章[\s:：]+(.+)$/);
    if (chapterMatch) {
      if (current) chapters.push(current);
      current = {
        title: trimmed.replace(/^#+\s*/, ''),
        purpose: '',
        events: '',
        characters: '',
        foreshadows: '',
      };
      continue;
    }
    if (!current) continue;

    // 标准细纲子标题
    if (/^#{2,3}\s*本?章目的/.test(trimmed)) { current._mode = 'purpose'; continue; }
    if (/^#{2,3}\s*关键情节/.test(trimmed)) { current._mode = 'events'; continue; }
    if (/^#{2,3}\s*出场人物/.test(trimmed)) { current._mode = 'characters'; continue; }
    if (/^#{2,3}\s*伏[^\n]*/.test(trimmed)) { current._mode = 'foreshadows'; continue; }

    // 兼容自定义格式：- **涉及角色**：林默、苏倩倩
    if (/^[-*]\s*\*\*(涉及角色|出场人物|人物|角色)\*\*/.test(trimmed)) {
      current._mode = 'characters';
      // 提取冒号后的内容
      const colonIdx = trimmed.indexOf('：') >= 0 ? trimmed.indexOf('：') : trimmed.indexOf(':');
      if (colonIdx >= 0) {
        current.characters += (current.characters ? '\n' : '') + trimmed.slice(colonIdx + 1).trim();
      }
      continue;
    }
    if (/^[-*]\s*\*\*(场景设定|本章目的|目的|背景)\*\*/.test(trimmed)) {
      current._mode = 'purpose';
      const colonIdx = trimmed.indexOf('：') >= 0 ? trimmed.indexOf('：') : trimmed.indexOf(':');
      if (colonIdx >= 0) {
        current.purpose += (current.purpose ? '\n' : '') + trimmed.slice(colonIdx + 1).trim();
      }
      continue;
    }
    if (/^[-*]\s*\*\*(核心爽点|关键情节|具体情节|情节|爽点|事件)\*\*/.test(trimmed)) {
      current._mode = 'events';
      const colonIdx = trimmed.indexOf('：') >= 0 ? trimmed.indexOf('：') : trimmed.indexOf(':');
      if (colonIdx >= 0) {
        current.events += (current.events ? '\n' : '') + trimmed.slice(colonIdx + 1).trim();
      }
      continue;
    }
    if (/^[-*]\s*\*\*(关键对话|对话示例|伏笔|钩子|章节钩子)\*\*/.test(trimmed)) {
      current._mode = 'foreshadows';
      const colonIdx = trimmed.indexOf('：') >= 0 ? trimmed.indexOf('：') : trimmed.indexOf(':');
      if (colonIdx >= 0) {
        current.foreshadows += (current.foreshadows ? '\n' : '') + trimmed.slice(colonIdx + 1).trim();
      }
      continue;
    }

    if (current._mode && trimmed) {
      current[current._mode] += (current[current._mode] ? '\n' : '') + trimmed;
    }
  }
  if (current) chapters.push(current);
  return chapters;
}

// 解析角色信息（简单从文本提取）
export function extractCharacters(md) {
  const chars = [];
  const re = /[-*]\s*([^（：(]+)[（(]?(主角|配角|反派|女主|导师|龙套)?[）)]?\s*[：:]?\s*(.+)/g;
  let m;
  while ((m = re.exec(md)) !== null) {
    chars.push({
      name: m[1].trim(),
      role: (m[2] || '配角').trim(),
      desc: m[3].trim(),
    });
  }
  return chars;
}

// 生成唯一ID
export function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
