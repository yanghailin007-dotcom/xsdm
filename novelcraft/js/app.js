import { storage } from './storage.js';
import { ai } from './ai.js';
import { renderTimeline, openEditorFromTimeline } from './views/timeline.js';
import { renderCharacters } from './views/characters.js';
import { initAIWorkshop, loadAIConfig } from './views/ai-workshop.js';
import { initEditor, loadEditor } from './views/editor.js';

// ===== 全局状态 =====
window.$app = {
  project: null,
  currentView: 'dashboard',
  ai,
  storage,
  refreshAll() {
    if (!this.project) return;
    renderTimeline(this.project);
    renderCharacters(this.project);
    updateSidebar();
    updateStageStatus();
  },
  switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));

    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    const tab = document.querySelector(`.nav-tab[data-view="${viewName}"]`);
    if (tab) tab.classList.add('active');

    this.currentView = viewName;

    if (viewName === 'timeline') renderTimeline(this.project);
    if (viewName === 'characters') renderCharacters(this.project);
    if (viewName === 'editor') initEditor(this.project);
  },
};

// ===== DOM 引用 =====
const els = {
  topNav: document.getElementById('top-nav'),
  sidebar: document.getElementById('sidebar'),
  fileTree: document.getElementById('file-tree'),
  dashboard: document.getElementById('view-dashboard'),
  projectList: document.getElementById('project-list'),
  modalNew: document.getElementById('modal-new'),
  newName: document.getElementById('new-project-name'),
  importFile: document.getElementById('import-file'),
};

// ===== 初始化 =====
function init() {
  bindEvents();
  loadDashboard();
  initAIWorkshop();
  initEditor();

  // 自动恢复上次打开的项目
  const lastId = storage.getCurrentProjectId();
  if (lastId) {
    const p = storage.getProject(lastId);
    if (p) enterProject(p);
  }
}

function bindEvents() {
  // Tab 切换
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const view = tab.dataset.view;
      if (view === 'editor') return; // editor 不通过 tab 直接进
      $app.switchView(view);
    });
  });

  // 新建项目
  document.getElementById('btn-new-project').addEventListener('click', () => {
    els.newName.value = '';
    els.modalNew.classList.add('active');
    els.newName.focus();
  });
  document.getElementById('modal-cancel').addEventListener('click', () => els.modalNew.classList.remove('active'));
  document.getElementById('modal-confirm').addEventListener('click', createProject);
  els.newName.addEventListener('keydown', e => { if (e.key === 'Enter') createProject(); });

  // 导入项目
  document.getElementById('btn-import-project').addEventListener('click', () => els.importFile.click());
  els.importFile.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      try {
        const p = storage.importProject(ev.target.result);
        enterProject(p);
      } catch (err) {
        alert('导入失败：' + err.message);
      }
    };
    reader.readAsText(file);
    els.importFile.value = '';
  });

  // 导出项目
  document.getElementById('btn-export').addEventListener('click', () => {
    if (!$app.project) return;
    const blob = new Blob([storage.exportProject($app.project.id)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${$app.project.name || 'project'}.novelcraft.json`;
    a.click();
    URL.revokeObjectURL(url);
  });
}

function createProject() {
  const name = els.newName.value.trim() || '未命名小说';
  const p = storage.createDefaultProject(name);
  enterProject(p);
  els.modalNew.classList.remove('active');
  loadDashboard();
}

function enterProject(project) {
  $app.project = project;
  storage.setCurrentProjectId(project.id);

  // 显示工作区
  els.dashboard.classList.remove('active');
  els.topNav.style.display = 'flex';
  els.sidebar.style.display = 'flex';

  // 默认进入故事主线
  $app.switchView('timeline');
  updateSidebar();
  updateStageStatus();
  loadAIConfig(project);
}

function loadDashboard() {
  const list = storage.listProjects();
  if (!list.length) {
    els.projectList.innerHTML = '<div style="text-align:center;color:var(--text-secondary);">暂无项目，点击上方按钮创建</div>';
    return;
  }
  els.projectList.innerHTML = list.map(p => `
    <div class="project-item" data-id="${p.id}">
      <div>
        <div style="font-weight:600;">${escapeHtml(p.name)}</div>
        <div class="project-meta">更新于 ${formatDate(p.updatedAt)} · ${Object.keys(p.files || {}).length} 个文件</div>
      </div>
      <button class="btn btn-sm btn-danger" data-del="${p.id}">删除</button>
    </div>
  `).join('');

  els.projectList.querySelectorAll('.project-item').forEach(item => {
    item.addEventListener('click', e => {
      if (e.target.dataset.del) {
        if (confirm('确定删除该项目？数据无法恢复。')) {
          storage.deleteProject(e.target.dataset.del);
          loadDashboard();
        }
        return;
      }
      const p = storage.getProject(item.dataset.id);
      if (p) enterProject(p);
    });
  });
}

export function updateSidebar() {
  const p = $app.project;
  if (!p) return;

  const files = [
    { key: 'core-setting.md', icon: '📄', label: 'core-setting.md' },
    { key: 'rough-outline.md', icon: '📄', label: 'rough-outline.md' },
    { key: 'detailed-outline.md', icon: '📄', label: 'detailed-outline.md' },
  ];

  const chapters = Object.keys(p.chapters || {}).sort();

  let html = '<div class="sidebar-title">大纲文件</div>';
  html += files.map(f => `
    <div class="file-item" data-file="${f.key}">
      <span class="file-icon">${f.icon}</span> ${f.label}
    </div>
  `).join('');

  if (chapters.length) {
    html += '<div style="margin-top:16px; border-top:1px solid var(--border-light); padding-top:12px;"><div class="sidebar-title">章节</div>';
    html += chapters.map(c => `
      <div class="file-item" data-chapter="${escapeHtml(c)}">
        <span class="file-icon">📝</span> ${escapeHtml(c)}
      </div>
    `).join('');
    html += '</div>';
  }

  els.fileTree.innerHTML = html;

  // 绑定点击
  els.fileTree.querySelectorAll('.file-item').forEach(item => {
    item.addEventListener('click', () => {
      const file = item.dataset.file;
      const chapter = item.dataset.chapter;
      if (file) {
        loadEditor(file, p.files[file]?.content || '');
      } else if (chapter) {
        const ch = p.chapters[chapter];
        loadEditor(chapter, ch?.content || '');
      }
    });
  });
}

export function updateStageStatus() {
  const p = $app.project;
  if (!p) return;
  const stages = [
    { key: 'core-setting.md', el: 'stage-1', label: '核心设定' },
    { key: 'rough-outline.md', el: 'stage-2', label: '粗纲生成' },
    { key: 'detailed-outline.md', el: 'stage-3', label: '细纲生成' },
    { key: null, el: 'stage-4', label: '正文生成', check: () => !!(p.chapters && Object.keys(p.chapters).length > 0) },
  ];

  stages.forEach((s, idx) => {
    const hasContent = s.check ? s.check() : !!(p.files[s.key]?.content?.trim());
    const el = document.getElementById(s.el);
    if (!el) return;
    const prevDone = idx === 0 || (stages[idx-1].check ? stages[idx-1].check() : !!(p.files[stages[idx-1].key]?.content?.trim()));
    el.className = 'stage-item' + (hasContent ? ' complete' : (prevDone ? ' current' : ' pending'));
    el.querySelector('.stage-status').textContent = hasContent ? '✅ 已完成' : (el.classList.contains('current') ? '🔄 待生成' : '⏳ 未解锁');
  });
}

export function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function formatDate(ts) {
  if (!ts) return '-';
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

// 全局暴露一些工具
window.openEditorFromTimeline = openEditorFromTimeline;

init();
