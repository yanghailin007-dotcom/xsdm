import { storage } from '../storage.js';
import { parseOutline, uid } from '../utils.js';
import { updateSidebar } from '../app.js';

const els = {
  view: document.getElementById('view-editor'),
  back: document.getElementById('editor-back'),
  title: document.getElementById('editor-title'),
  textarea: document.getElementById('md-editor'),
  save: document.getElementById('editor-save'),
  right: document.getElementById('editor-right'),
};

let currentFile = null; // 文件名或章节名
let currentMeta = {};   // { source, startLine, endLine }
let currentContent = '';
let initialized = false;

export function initEditor() {
  if (!els.save || initialized) return;
  initialized = true;
  els.back.addEventListener('click', () => window.$app.switchView('timeline'));
  els.save.addEventListener('click', doSave);
}

export function loadEditor(title, content, meta = null) {
  currentFile = title;
  currentMeta = meta || {};
  currentContent = content;
  els.title.textContent = title;
  els.textarea.value = content;
  window.$app.switchView('editor');
  renderSummary(content);
}

function renderSummary(md) {
  const ch = parseOutline(md + '\n')[0] || {};
  const purpose = ch.purpose || '（未填写）';
  const events = ch.events || '（未填写）';
  const charsText = ch.characters || '';
  const foreshadowsText = ch.foreshadows || '';

  // 提取角色标签
  const charTags = [];
  const re = /[-*]\s*([^（：:\n]+)/g;
  let m;
  while ((m = re.exec(charsText)) !== null) {
    charTags.push(m[1].trim());
  }

  // 提取伏笔
  const foreTags = [];
  const fre = /[-*]\s*(.+)/g;
  while ((m = fre.exec(foreshadowsText)) !== null) {
    foreTags.push(m[1].trim());
  }

  const p = window.$app.project;
  const existingFores = (p.foreshadows || []).filter(f => f.sourceChapter === currentFile);

  let html = '';
  html += card('📌 本章目的', `<p>${escapeHtml(purpose)}</p>`);
  html += card('👥 出场人物', charTags.length ? charTags.map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('') : '<p style="color:var(--text-secondary);">未识别到人物</p>');
  html += card('⚡ 关键事件', `<p>${escapeHtml(events)}</p>`);

  // 伏笔
  html += '<div class="card summary-card"><h4>❓ 未完成伏笔</h4>';
  if (!existingFores.length && !foreTags.length) {
    html += '<p style="color:var(--text-secondary);">暂无伏笔</p>';
  }
  existingFores.forEach(f => {
    html += `<div class="foreshadow-item ${f.resolved ? 'resolved' : ''}">
      <input type="checkbox" ${f.resolved ? 'checked' : ''} data-fid="${f.id}">
      <span>${escapeHtml(f.text)}</span>
    </div>`;
  });
  html += '</div>';

  els.right.innerHTML = html;

  // 绑定伏笔 checkbox
  els.right.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      const fid = cb.dataset.fid;
      const f = p.foreshadows.find(x => x.id === fid);
      if (f) {
        f.resolved = cb.checked;
        storage.saveProject(p);
        renderSummary(els.textarea.value);
      }
    });
  });
}

function card(title, body) {
  return `<div class="card summary-card"><h4>${title}</h4>${body}</div>`;
}

function doSave() {
  const p = window.$app.project;
  const newContent = els.textarea.value;

  if (currentMeta.source === 'detailed-outline.md' && currentMeta.startLine !== undefined) {
    // 替换细纲文件中的片段
    const full = p.files['detailed-outline.md'].content;
    const lines = full.split('\n');
    const before = lines.slice(0, currentMeta.startLine).join('\n');
    const after = lines.slice(currentMeta.endLine).join('\n');
    const updated = (before ? before + '\n' : '') + newContent + (after ? '\n' + after : '');
    storage.setFile(p.id, 'detailed-outline.md', updated);
  } else if (p.files[currentFile]) {
    storage.setFile(p.id, currentFile, newContent);
  } else if (p.chapters[currentFile]) {
    storage.setChapter(p.id, currentFile, { content: newContent });
  }

  // 自动提取并更新伏笔
  updateForeshadows(p, currentFile, newContent);

  // 刷新视图
  window.$app.refreshAll();

  // 显示保存成功提示（简单替换按钮文字）
  const old = els.save.textContent;
  els.save.textContent = '已保存 ✓';
  setTimeout(() => els.save.textContent = old, 1200);
}

function updateForeshadows(project, chapterName, md) {
  if (!project.foreshadows) project.foreshadows = [];
  const oldFores = project.foreshadows.filter(f => f.sourceChapter === chapterName);
  const oldMap = new Map(oldFores.map(f => [f.text, f]));

  const ch = parseOutline(md + '\n')[0];
  const newFores = [];

  if (ch) {
    const foreText = ch.foreshadows || '';
    const re = /[-*]\s*(.+)/g;
    let m;
    while ((m = re.exec(foreText)) !== null) {
      const text = m[1].trim();
      const existing = oldMap.get(text);
      newFores.push({
        id: existing ? existing.id : uid(),
        text,
        sourceChapter: chapterName,
        resolved: existing ? existing.resolved : false,
      });
    }
  }

  project.foreshadows = project.foreshadows.filter(f => f.sourceChapter !== chapterName).concat(newFores);
  storage.saveProject(project);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
