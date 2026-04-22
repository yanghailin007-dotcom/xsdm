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
  if (!els.right) {
    console.error('[renderSummary] els.right is null');
    return;
  }
  try {
    const p = window.$app.project || {};
    
    // 对于非细纲的大纲文件，显示简单提示
    const isOutlineFile = ['core-setting.md', 'rough-outline.md'].includes(currentFile);
    if (isOutlineFile) {
      els.right.innerHTML = `
        <div class="card summary-card">
          <h4>📄 ${escapeHtml(currentFile)}</h4>
          <p style="color:var(--text-secondary);">该文件为大纲文档，右侧摘要仅对细纲章节自动解析。</p>
        </div>
        <div class="card summary-card">
          <h4>📝 字数统计</h4>
          <p>${md.length} 字符</p>
        </div>
      `;
      return;
    }
    
    const ch = parseOutline(md + '\n')[0] || {};
    const purpose = ch.purpose || '（未填写）';
    const events = ch.events || '（未填写）';
    const charsText = ch.characters || '';
    const foreshadowsText = ch.foreshadows || '';

    // 提取角色标签：先尝试列表格式，再尝试顿号/逗号分隔的纯文本
    const charTags = [];
    if (charsText.trim()) {
      // 尝试匹配 - 名字 或 * 名字 格式
      const listRe = /[-*]\s*([^、，,（：:\n]+)/g;
      let m;
      while ((m = listRe.exec(charsText)) !== null) {
        charTags.push(m[1].trim());
      }
      // 如果没有匹配到列表项，尝试按顿号/逗号/空格分隔
      if (!charTags.length) {
        const names = charsText.split(/[、,，\s]+/).filter(n => n.trim().length >= 1);
        charTags.push(...names.map(n => n.trim()));
      }
    }

    // 提取伏笔
    const foreTags = [];
    const fre = /[-*]\s*(.+)/g;
    let m;
    while ((m = fre.exec(foreshadowsText)) !== null) {
      foreTags.push(m[1].trim());
    }

    const existingFores = (p.foreshadows || []).filter(f => f.sourceChapter === currentFile);

    let html = '';
    html += card('📌 本章目的', `<p>${escapeHtml(purpose).replace(/\n/g, '<br>')}</p>`);
    html += card('👥 出场人物', charTags.length ? charTags.map(c => `<span class="tag">${escapeHtml(c)}</span>`).join('') : '<p style="color:var(--text-secondary);">未识别到人物</p>');
    html += card('⚡ 关键事件', `<p>${escapeHtml(events).replace(/\n/g, '<br>')}</p>`);

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

    // 章节生成入口（编辑细纲中的具体章节时显示）
    const isChapterEditor = (currentMeta && currentMeta.source === 'detailed-outline.md') || /第\d+章/.test(currentFile || '');
    if (isChapterEditor) {
      html += `<div class="card summary-card">
        <h4>✍️ 章节生成</h4>
        <button id="btn-generate-chapter" class="btn btn-primary" style="margin-top:4px;">生成本章正文</button>
        <p style="color:var(--text-secondary);font-size:12px;margin-top:8px;">基于左侧细纲调用 V2 引擎生成本章正文，保存到服务器。</p>
      </div>`;
    }

    // 写入右侧面板
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

    // 章节生成按钮
    const generateBtn = document.getElementById('btn-generate-chapter');
    if (generateBtn) {
      generateBtn.addEventListener('click', generateCurrentChapter);
    }
  } catch (err) {
    console.error('[renderSummary] error:', err);
    els.right.innerHTML = `<div class="card summary-card"><h4>⚠️ 渲染错误</h4><p style="color:var(--text-secondary);">${escapeHtml(err.message)}</p></div>`;
  }
}

async function generateCurrentChapter() {
  const p = window.$app.project;
  if (!p) return;

  // 从 currentFile 提取章节号，如 "第15章 初入宗门"
  const match = String(currentFile).match(/第(\d+)章/);
  if (!match) {
    alert('无法识别当前章节号');
    return;
  }
  const chapterNum = parseInt(match[1], 10);

  const btn = document.getElementById('btn-generate-chapter');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '生成中，请稍候...';
  }

  try {
    const resp = await fetch('/api/novelcraft/generate-chapters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: p.name,
        start_chapter: chapterNum,
        end_chapter: chapterNum,
        use_v2: true
      })
    });
    const result = await resp.json();
    if (result.success) {
      const data = result.data || {};
      const chapters = data.chapters || [];
      alert(`生成完成！\n共生成 ${chapters.length} 章\n质量均分: ${(data.overall_score || 0).toFixed(1)}`);
      // 将生成的章节添加到本地 chapters 列表并同步
      chapters.forEach(ch => {
        if (!p.chapters) p.chapters = {};
        p.chapters[`第${ch.chapter_number}章 ${ch.title}`] = {
          content: '', // 正文保存在服务器，下次加载时读取
          wordCount: ch.word_count,
          updatedAt: Date.now()
        };
      });
      storage.saveProject(p);
      window.$app.refreshAll();
    } else {
      alert('生成失败: ' + (result.error || '未知错误'));
    }
  } catch (e) {
    alert('网络异常: ' + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '生成本章正文';
    }
  }
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
    p.files['detailed-outline.md'] = { content: updated, updatedAt: Date.now() };
  } else if (p.files[currentFile]) {
    storage.setFile(p.id, currentFile, newContent);
    p.files[currentFile] = { content: newContent, updatedAt: Date.now() };
  } else if (p.chapters[currentFile]) {
    storage.setChapter(p.id, currentFile, { content: newContent });
    p.chapters[currentFile] = { ...(p.chapters[currentFile] || {}), content: newContent, updatedAt: Date.now() };
  }

  // 自动提取并更新伏笔
  updateForeshadows(p, currentFile, newContent);

  // 刷新视图并自动返回故事主线
  window.$app.refreshAll();
  window.$app.switchView('timeline');

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
