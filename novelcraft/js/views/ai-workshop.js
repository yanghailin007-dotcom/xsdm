import { ai } from '../ai.js';
import { storage } from '../storage.js';
import { DEFAULT_PROMPTS, getProjectPrompts } from '../prompts.js';

const msgsEl = document.getElementById('chat-messages');
const inputEl = document.getElementById('chat-input');
const sendBtn = document.getElementById('chat-send');
const modelSel = document.getElementById('ai-model');
const keyInput = document.getElementById('ai-key');
const baseInput = document.getElementById('ai-base');
const stageLabel = document.getElementById('ai-stage-label');

let messages = [];
let currentStage = 'core-setting'; // core-setting | rough-outline | detailed-outline
let initialized = false;

const STAGE_LABELS = {
  'core-setting': '核心设定',
  'rough-outline': '粗纲生成',
  'detailed-outline': '细纲生成',
  'chapter-content': '正文生成',
};

export function loadAIConfig(project) {
  if (!project) return;
  const cfg = project.aiConfig || {};
  modelSel.value = cfg.model || 'gpt-4o';
  keyInput.value = cfg.apiKey || '';
  baseInput.value = cfg.baseURL || 'https://api.openai.com/v1';

  // 初始化默认 prompts
  if (!project.prompts || Object.keys(project.prompts).length === 0) {
    project.prompts = { ...DEFAULT_PROMPTS };
    storage.saveProject(project);
  }

  determineStage(project);
  messages = [];
  renderMessages();
}

function saveAIConfigToProject() {
  const p = window.$app.project;
  if (!p) return;
  p.aiConfig = {
    model: modelSel.value,
    apiKey: keyInput.value.trim(),
    baseURL: baseInput.value.trim() || 'https://api.openai.com/v1',
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
  keyInput.addEventListener('change', saveAIConfigToProject);
  baseInput.addEventListener('change', saveAIConfigToProject);

  // 快捷提示词按钮
  document.getElementById('btn-prompt-core').addEventListener('click', () => insertPrompt('core-setting'));
  document.getElementById('btn-prompt-rough').addEventListener('click', () => insertPrompt('rough-outline'));
  document.getElementById('btn-prompt-detail').addEventListener('click', () => insertPrompt('detailed-outline'));
  // 本地版本暂不支持直接调用 V2 引擎生成正文，请使用 Web 版本
  const btnGenChapters = document.getElementById('btn-generate-chapters');
  if (btnGenChapters) {
    btnGenChapters.addEventListener('click', () => {
      addSystemMessage('💡 本地编辑器暂不支持 V2 引擎正文生成，请部署到 Web 后使用');
    });
  }

  document.getElementById('btn-insert-context').addEventListener('click', insertContext);
  document.getElementById('btn-parse-all').addEventListener('click', () => {
    window.$app.refreshAll();
    addSystemMessage('已解析当前文件内容到故事主线与角色图谱');
  });
  document.getElementById('btn-export-md').addEventListener('click', exportMD);
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

  // 保存配置到项目
  saveAIConfigToProject();

  // UI
  addMessage('user', text);
  inputEl.value = '';
  messages.push({ role: 'user', content: text });

  const aiMsgDiv = addMessage('ai', '', true);
  let fullText = '';

  try {
    await ai.chatStream(messages, p.aiConfig, (chunk, done) => {
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
