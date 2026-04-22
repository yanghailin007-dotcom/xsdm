import { ai } from '../ai.js';
import { storage } from '../storage.js';
import { DEFAULT_PROMPTS, getProjectPrompts } from '../prompts.js';

const msgsEl = document.getElementById('chat-messages');
const inputEl = document.getElementById('chat-input');
const sendBtn = document.getElementById('chat-send');
const modelSel = document.getElementById('ai-model');
const stageLabel = document.getElementById('ai-stage-label');
const btnAddModel = document.getElementById('btn-add-model');

let messages = [];
let currentStage = 'core-setting'; // core-setting | rough-outline | detailed-outline | chapter-content
let initialized = false;
let availableModels = { system: [], custom: [] };

const STAGE_LABELS = {
  'core-setting': '核心设定',
  'rough-outline': '粗纲生成',
  'detailed-outline': '细纲生成',
  'chapter-content': '正文生成',
};

export async function loadAIConfig(project) {
  if (!project) return;

  // 初始化默认 prompts
  if (!project.prompts || Object.keys(project.prompts).length === 0) {
    project.prompts = { ...DEFAULT_PROMPTS };
    storage.saveProject(project);
  }

  determineStage(project);
  messages = [];
  renderMessages();

  // 加载模型列表
  try {
    availableModels = await ai.fetchModels();
    renderModelSelect(project.aiConfig?.modelId || '');
  } catch (err) {
    console.error('加载模型列表失败:', err);
    modelSel.innerHTML = '<option value="">加载失败</option>';
  }
}

function renderModelSelect(selectedId) {
  let html = '<optgroup label="系统模型">';
  availableModels.system.forEach(m => {
    html += `<option value="${escapeHtml(m.id)}" ${m.id === selectedId ? 'selected' : ''}>${escapeHtml(m.name)}</option>`;
  });
  html += '</optgroup>';

  if (availableModels.custom.length) {
    html += '<optgroup label="自定义模型">';
    availableModels.custom.forEach(m => {
      html += `<option value="${escapeHtml(m.id)}" ${m.id === selectedId ? 'selected' : ''}>${escapeHtml(m.name)}</option>`;
    });
    html += '</optgroup>';
  }

  modelSel.innerHTML = html;
}

function saveAIConfigToProject() {
  const p = window.$app.project;
  if (!p) return;
  p.aiConfig = {
    modelId: modelSel.value,
  };
  storage.saveProject(p);
}

export function initAIWorkshop() {
  if (initialized) return;
  initialized = true;
  sendBtn.addEventListener('click', sendMessage);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  modelSel.addEventListener('change', saveAIConfigToProject);

  // 快捷提示词按钮
  document.getElementById('btn-prompt-core').addEventListener('click', () => insertPrompt('core-setting'));
  document.getElementById('btn-prompt-rough').addEventListener('click', () => insertPrompt('rough-outline'));
  document.getElementById('btn-prompt-detail').addEventListener('click', () => insertPrompt('detailed-outline'));

  // 生成正文（调V2引擎）
  const btnGenChapters = document.getElementById('btn-generate-chapters');
  if (btnGenChapters) {
    btnGenChapters.addEventListener('click', generateChapters);
  }

  document.getElementById('btn-insert-context').addEventListener('click', insertContext);
  document.getElementById('btn-parse-all').addEventListener('click', () => {
    window.$app.refreshAll();
    addSystemMessage('已解析当前文件内容到故事主线与角色图谱');
  });
  document.getElementById('btn-export-md').addEventListener('click', exportMD);

  // 提取发布信息
  const btnGenPublish = document.getElementById('btn-gen-publish');
  if (btnGenPublish) {
    btnGenPublish.addEventListener('click', generatePublishInfo);
  }

  // 添加自定义模型
  if (btnAddModel) {
    btnAddModel.addEventListener('click', openAddModelModal);
  }
  bindModelModal();
}

function determineStage(project) {
  const f = project.files || {};
  if (!f['core-setting.md']?.content?.trim()) currentStage = 'core-setting';
  else if (!f['rough-outline.md']?.content?.trim()) currentStage = 'rough-outline';
  else if (!f['detailed-outline.md']?.content?.trim()) currentStage = 'detailed-outline';
  else currentStage = 'chapter-content';
  stageLabel.textContent = `当前：${STAGE_LABELS[currentStage]}`;
}

function insertPrompt(stage) {
  const p = window.$app.project;
  if (!p) return;
  const prompts = getProjectPrompts(p);
  const text = prompts[stage] || '';
  if (!text) return;

  const prefix = inputEl.value.trim() ? '\n\n' : '';
  inputEl.value += prefix + text;
  inputEl.focus();
  inputEl.scrollTop = inputEl.scrollHeight;
}

function insertContext() {
  const p = window.$app.project;
  if (!p) return;
  let context = '';
  if (currentStage === 'rough-outline') {
    context = `\n\n【已生成的核心设定】\n${p.files['core-setting.md']?.content || ''}`;
  } else if (currentStage === 'detailed-outline') {
    context = `\n\n【已生成的核心设定】\n${p.files['core-setting.md']?.content || ''}\n\n【已生成的粗纲】\n${p.files['rough-outline.md']?.content || ''}`;
  } else if (currentStage === 'chapter-content') {
    context = `\n\n【已生成的核心设定】\n${p.files['core-setting.md']?.content || ''}\n\n【已生成的细纲】\n${p.files['detailed-outline.md']?.content || ''}`;
  }
  inputEl.value += context;
  inputEl.focus();
  inputEl.scrollTop = inputEl.scrollHeight;
}

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text) return;

  const p = window.$app.project;
  if (!p) return;

  const modelId = modelSel.value;
  if (!modelId) {
    addSystemMessage('请先选择一个 AI 模型');
    return;
  }

  // 保存配置到项目
  saveAIConfigToProject();

  // UI
  addMessage('user', text);
  inputEl.value = '';
  messages.push({ role: 'user', content: text });

  const aiMsgDiv = addMessage('ai', '', true);
  let fullText = '';

  try {
    await ai.chatStream(messages, modelId, (chunk, done) => {
      if (!done) {
        fullText += chunk;
        aiMsgDiv.textContent = fullText;
        msgsEl.scrollTop = msgsEl.scrollHeight;
      }
    });

    messages.push({ role: 'assistant', content: fullText });

    // 自动保存到文件
    const filename = `${currentStage}.md`;
    const old = p.files[filename]?.content || '';
    const updated = old ? old + '\n\n---\n\n' + fullText : fullText;
    storage.setFile(p.id, filename, updated);
    // 关键：storage.setFile 会从 localStorage 重新读取对象保存，
    // 必须同步内存中的 project 对象，否则左侧文件树和编辑器显示的还是旧内容
    p.files[filename] = { content: updated, updatedAt: Date.now() };

    // 阶段推进
    determineStage(p);
    window.$app.refreshAll();
    addSystemMessage(`AI 回复已自动保存到 ${filename}`);
  } catch (err) {
    aiMsgDiv.textContent = `❌ 错误：${err.message}`;
  }
}

function addMessage(role, text, isStreaming = false) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  if (isStreaming) div.classList.add('streaming');
  div.textContent = text;
  msgsEl.appendChild(div);
  msgsEl.scrollTop = msgsEl.scrollHeight;
  return div;
}

function addSystemMessage(text) {
  const div = document.createElement('div');
  div.className = 'message system';
  div.textContent = text;
  msgsEl.appendChild(div);
  msgsEl.scrollTop = msgsEl.scrollHeight;
}

function renderMessages() {
  msgsEl.innerHTML = '';
  messages.forEach(m => addMessage(m.role, m.content));
}

function exportMD() {
  const p = window.$app.project;
  if (!p) return;
  let md = '';
  ['core-setting.md', 'rough-outline.md', 'detailed-outline.md'].forEach(f => {
    md += `# ${f}\n\n${p.files[f]?.content || ''}\n\n---\n\n`;
  });
  const blob = new Blob([md], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${p.name || 'outline'}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

async function generateChapters() {
  const p = window.$app.project;
  if (!p) return;

  // 解析细纲中第一章和最后一章的章节号
  const outline = p.files['detailed-outline.md']?.content || '';
  const matches = outline.match(/^#{1,3}\s*第(\d+)章/gm);
  if (!matches || matches.length === 0) {
    addSystemMessage('❌ 细纲中未找到章节，请先生成细纲');
    return;
  }
  const chapterNumbers = matches.map(m => {
    const n = m.match(/第(\d+)章/);
    return n ? parseInt(n[1], 10) : 0;
  }).filter(n => n > 0);
  if (chapterNumbers.length === 0) {
    addSystemMessage('❌ 无法解析细纲中的章节号');
    return;
  }
  const startChapter = Math.min(...chapterNumbers);
  const endChapter = Math.max(...chapterNumbers);

  const btn = document.getElementById('btn-generate-chapters');
  if (btn) {
    btn.disabled = true;
    btn.textContent = '生成中，请稍候...';
  }

  addSystemMessage(`正在调用 V2 引擎生成第${startChapter}-${endChapter}章正文，请稍候...`);

  try {
    const resp = await fetch('/api/novelcraft/generate-chapters', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: p.name,
        start_chapter: startChapter,
        end_chapter: endChapter,
        use_v2: true
      })
    });
    const result = await resp.json();
    if (result.success) {
      const data = result.data || {};
      const chapters = data.chapters || [];
      const mode = data.generation_mode || 'unknown';
      addSystemMessage(`✅ V2 正文生成完成！模式：${mode}，共 ${chapters.length} 章，质量均分: ${(data.overall_score || 0).toFixed(1)}`);
      // 将生成的章节添加到本地 chapters 列表
      chapters.forEach(ch => {
        if (!p.chapters) p.chapters = {};
        p.chapters[`第${ch.chapter_number}章 ${ch.title}`] = {
          content: '',
          wordCount: ch.word_count,
          updatedAt: Date.now()
        };
      });
      storage.saveProject(p);
      window.$app.refreshAll();
    } else {
      addSystemMessage('❌ 生成失败：' + (result.error || '未知错误'));
    }
  } catch (e) {
    addSystemMessage('❌ 请求失败：' + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = '🚀 生成正文（V2引擎）';
    }
  }
}

async function generatePublishInfo() {
  const p = window.$app.project;
  if (!p) return;
  
  addSystemMessage('正在调用 AI 提取发布信息，请稍候...');
  
  try {
    const resp = await fetch('/api/novelcraft/publish-info', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_name: p.name }),
    });
    const result = await resp.json();
    
    if (result.success) {
      const data = result.data;
      addSystemMessage(`✅ 发布信息已生成：书名《${data.title}》，分类：${data.category}`);
      // 可选：把书名同步到项目
      if (data.title && data.title !== p.name) {
        p.name = data.title;
        storage.saveProject(p);
      }
    } else {
      addSystemMessage('❌ 生成失败：' + result.error);
    }
  } catch (e) {
    addSystemMessage('❌ 请求失败：' + e.message);
  }
}

// ===== 添加模型模态框 =====
function openAddModelModal() {
  const modal = document.getElementById('modal-model');
  if (!modal) return;
  document.getElementById('model-name').value = '';
  document.getElementById('model-id').value = '';
  document.getElementById('model-key').value = '';
  document.getElementById('model-url').value = '';
  modal.classList.add('active');
}

function bindModelModal() {
  const modal = document.getElementById('modal-model');
  if (!modal) return;
  document.getElementById('model-cancel').addEventListener('click', () => {
    modal.classList.remove('active');
  });
  document.getElementById('model-confirm').addEventListener('click', async () => {
    const name = document.getElementById('model-name').value.trim();
    const modelId = document.getElementById('model-id').value.trim();
    const apiKey = document.getElementById('model-key').value.trim();
    const apiUrl = document.getElementById('model-url').value.trim();

    if (!name || !modelId || !apiKey || !apiUrl) {
      alert('请填写所有字段');
      return;
    }

    try {
      const result = await ai.addCustomModel({
        id: `custom_${Date.now()}`,
        name,
        model: modelId,
        api_key: apiKey,
        api_url: apiUrl,
      });
      if (result.success) {
        modal.classList.remove('active');
        addSystemMessage('自定义模型添加成功');
        // 刷新模型列表
        availableModels = await ai.fetchModels();
        const p = window.$app.project;
        renderModelSelect(p?.aiConfig?.modelId || '');
      } else {
        alert(result.error || '添加失败');
      }
    } catch (e) {
      alert('添加失败: ' + e.message);
    }
  });
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
