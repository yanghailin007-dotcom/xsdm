/**
 * 本地存储层
 * 使用 localStorage 存储项目数据（markdown 文件内容、角色、关系、伏笔等）
 */

const STORAGE_KEY = 'novelcraft_projects';
const CURRENT_KEY = 'novelcraft_current';

export const storage = {
  // 项目列表
  listProjects() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    try {
      const map = JSON.parse(raw);
      return Object.values(map).sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    } catch {
      return [];
    }
  },

  getProject(id) {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    try {
      const map = JSON.parse(raw);
      return map[id] || null;
    } catch {
      return null;
    }
  },

  saveProject(project) {
    const raw = localStorage.getItem(STORAGE_KEY);
    const map = raw ? JSON.parse(raw) : {};
    project.updatedAt = Date.now();
    map[project.id] = project;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  },

  deleteProject(id) {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const map = JSON.parse(raw);
    delete map[id];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  },

  getCurrentProjectId() {
    return localStorage.getItem(CURRENT_KEY) || null;
  },

  setCurrentProjectId(id) {
    if (id) localStorage.setItem(CURRENT_KEY, id);
    else localStorage.removeItem(CURRENT_KEY);
  },

  // 快捷：初始化一个带默认结构的项目
  createDefaultProject(name = '未命名小说') {
    const id = 'proj_' + Date.now();
    const project = {
      id,
      name,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      files: {
        'core-setting.md': { content: '', updatedAt: Date.now() },
        'rough-outline.md': { content: '', updatedAt: Date.now() },
        'detailed-outline.md': { content: '', updatedAt: Date.now() },
      },
      chapters: {}, // key: "第1章.md", value: { content, summary: {...} }
      aiConfig: { apiKey: '', baseURL: 'https://api.openai.com/v1', model: 'gpt-4o' },
      prompts: {},
      characters: [],
      relations: [],
      foreshadows: [], // { id, text, sourceChapter, resolvedIn, resolved }
      timeline: [],
    };
    this.saveProject(project);
    this.setCurrentProjectId(id);
    return project;
  },

  // 读取文件内容
  getFile(projectId, filename) {
    const p = this.getProject(projectId);
    if (!p) return '';
    return p.files?.[filename]?.content || '';
  },

  // 写入文件内容
  setFile(projectId, filename, content) {
    const p = this.getProject(projectId);
    if (!p) return;
    if (!p.files) p.files = {};
    p.files[filename] = { content, updatedAt: Date.now() };
    this.saveProject(p);
  },

  getChapter(projectId, chapterName) {
    const p = this.getProject(projectId);
    if (!p) return null;
    return p.chapters?.[chapterName] || { content: '', summary: {} };
  },

  setChapter(projectId, chapterName, data) {
    const p = this.getProject(projectId);
    if (!p) return;
    if (!p.chapters) p.chapters = {};
    p.chapters[chapterName] = { ...p.chapters[chapterName], ...data, updatedAt: Date.now() };
    this.saveProject(p);
  },

  // 导出整个项目为 JSON 文件
  exportProject(projectId) {
    const p = this.getProject(projectId);
    if (!p) return null;
    return JSON.stringify(p, null, 2);
  },

  // 导入 JSON 文件
  importProject(jsonStr) {
    const p = JSON.parse(jsonStr);
    if (!p.id) throw new Error('无效的项目数据');
    p.updatedAt = Date.now();
    this.saveProject(p);
    return p;
  },
};
