import { parseOutline, extractCharacters } from '../utils.js';
import { storage } from '../storage.js';
import { loadEditor } from './editor.js';

const track = document.getElementById('timeline-track');

export function renderTimeline(project) {
  if (!track || !project) return;
  const md = project.files?.['detailed-outline.md']?.content || '';
  const chapters = parseOutline(md);

  // 同时解析粗纲中的里程碑
  const rough = project.files?.['rough-outline.md']?.content || '';
  const milestones = [];
  const roughLines = rough.split('\n');
  for (const line of roughLines) {
    const m = line.match(/^#{1,2}\s*第[\d一二三四五六七八九十百千]+卷[\s:：]+(.+)$/);
    if (m) milestones.push({ title: line.replace(/^#+\s*/, ''), type: 'milestone' });
  }

  // 如果有章节但没有里程碑，生成一个默认里程碑
  if (chapters.length && !milestones.length) {
    milestones.push({ title: '第一卷：启程', type: 'milestone' });
  }

  // 合并节点：里程碑插入到对应位置（简单策略：每若干章插入一个里程碑，或开头/结尾）
  const nodes = [];
  let mIdx = 0;
  if (milestones.length && chapters.length) {
    nodes.push({ ...milestones[0], type: 'milestone' });
    mIdx = 1;
  }

  chapters.forEach((ch, idx) => {
    // 检测是否含人物重大事件关键字
    const isCharEvent = /觉醒|突破|死亡|背叛|重逢|觉醒|复仇/.test(ch.events || '');
    const isKeyEvent = /陨石|战争|袭击|阴谋|灾难/.test(ch.events || '');
    nodes.push({
      title: ch.title,
      type: isCharEvent ? 'character-event' : (isKeyEvent ? 'event' : 'chapter'),
      summary: ch,
    });
    // 简单地在中间插入下一个里程碑
    if (mIdx < milestones.length && idx === Math.floor(chapters.length / milestones.length * mIdx) - 1) {
      nodes.push({ ...milestones[mIdx], type: 'milestone' });
      mIdx++;
    }
  });

  // 保存解析后的时间线到项目
  project.timeline = nodes;
  storage.saveProject(project);

  // 渲染
  let html = '<div class="timeline-line"></div>';
  nodes.forEach((node, i) => {
    const icon = node.type === 'milestone' ? '🚩' : (node.type === 'event' ? '⚡' : (node.type === 'character-event' ? '👤' : ''));
    html += `
      <div class="node ${node.type}" data-index="${i}">
        <div class="node-dot">${icon}</div>
        <div class="node-label">${escapeHtml(node.title).replace(/\s/g, '<br>')}</div>
        <div class="node-type">${typeLabel(node.type)}</div>
      </div>
    `;
  });

  track.innerHTML = html;

  track.querySelectorAll('.node').forEach(n => {
    n.addEventListener('click', () => {
      const idx = parseInt(n.dataset.index);
      openEditorFromTimeline(idx);
    });
  });
}

export function openEditorFromTimeline(index) {
  const project = window.$app.project;
  if (!project || !project.timeline) return;
  const node = project.timeline[index];
  if (!node) return;

  // 章节节点直接编辑对应的细纲片段；里程碑和事件则编辑整个细纲文件（并定位）
  const md = project.files?.['detailed-outline.md']?.content || '';
  if (node.type === 'chapter') {
    // 尝试找到该章节在 detailed-outline.md 中的位置，并提取该章节内容作为临时编辑
    const lines = md.split('\n');
    let start = -1, end = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes(node.title)) start = i;
      if (start !== -1 && i > start && lines[i].match(/^#{1,2}\s*第[\d一二三四五六七八九十百千]+章/)) {
        end = i;
        break;
      }
    }
    if (end === -1) end = lines.length;
    const content = lines.slice(start, end).join('\n');
    loadEditor(node.title, content, { source: 'detailed-outline.md', startLine: start, endLine: end });
  } else {
    loadEditor('detailed-outline.md', md, { source: 'detailed-outline.md' });
  }
}

function typeLabel(type) {
  const map = {
    'milestone': '里程碑',
    'event': '关键事件',
    'character-event': '人物重大事件',
    'chapter': '章节',
  };
  return map[type] || type;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
