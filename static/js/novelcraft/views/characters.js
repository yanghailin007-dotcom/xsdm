import { storage } from '../storage.js';
import { parseOutline } from '../utils.js';

const svg = document.getElementById('graph-svg');
const panel = document.getElementById('char-panel');

export function renderCharacters(project) {
  if (!svg || !project) return;

  // 从细纲提取角色
  const md = project.files?.['detailed-outline.md']?.content || '';
  const chapters = parseOutline(md);
  const charMap = new Map();

  chapters.forEach((ch, idx) => {
    const charsText = ch.characters || '';
    if (!charsText.trim()) return;

    // 先尝试解析标准格式：- 名字（角色）：描述
    const re = /[-*]\s*([^、，,（：:\n]+)[（(]?(主角|配角|反派|女主|导师|龙套)?[）)]?\s*[：:]?\s*(.+)/g;
    let m;
    let matched = false;
    while ((m = re.exec(charsText)) !== null) {
      matched = true;
      const name = m[1].trim();
      const role = (m[2] || '配角').trim();
      const desc = m[3].trim();
      if (!charMap.has(name)) {
        charMap.set(name, { name, role, desc, arcs: [], faction: '未知势力' });
      }
      const c = charMap.get(name);
      c.arcs.push({ chapter: ch.title, event: ch.events?.split('\n')[0] || '' });
      if (role) c.role = role;
      if (desc) c.desc = desc;
    }

    // 如果没匹配到标准格式，尝试顿号/逗号分隔的纯名字列表（如：林默、苏倩倩、赵天磊）
    if (!matched) {
      const names = charsText.split(/[、,，\s]+/).filter(n => n.trim().length >= 1);
      names.forEach(name => {
        name = name.trim();
        if (!name) return;
        if (!charMap.has(name)) {
          charMap.set(name, { name, role: '配角', desc: '', arcs: [], faction: '未知势力' });
        }
        const c = charMap.get(name);
        c.arcs.push({ chapter: ch.title, event: ch.events?.split('\n')[0] || '' });
      });
    }

    // 简单势力推断（基于章节事件）
    charMap.forEach(c => {
      if (/青云|正道|宗/.test(ch.events + ch.purpose)) c.faction = '青云宗';
      if (/魔|邪|黑/.test(ch.events + ch.purpose)) c.faction = '魔道';
    });
  });

  // 从核心设定再补一次势力信息
  const setting = project.files?.['core-setting.md']?.content || '';
  const factions = [];
  const fre = /^[-*]\s*([^：:\n]+)[势力|阵营|组织|宗门]+/gm;
  let fm;
  while ((fm = fre.exec(setting)) !== null) {
    factions.push(fm[1].trim());
  }

  // 合并到项目数据
  const characters = Array.from(charMap.values());
  project.characters = characters;
  storage.saveProject(project);

  // 绘制 SVG 力导向简化版：固定圆环布局
  const rect = svg.getBoundingClientRect();
  const width = rect.width || 800;
  const height = rect.height || 500;
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

  const cx = width / 2;
  const cy = height / 2;
  const radius = Math.min(width, height) * 0.32;

  const nodes = characters.map((c, i) => {
    const angle = (i / Math.max(characters.length, 1)) * Math.PI * 2 - Math.PI / 2;
    return {
      ...c,
      x: cx + Math.cos(angle) * radius,
      y: cy + Math.sin(angle) * radius,
      color: c.role === '主角' ? '#1f6feb' : (c.role === '反派' ? '#da3633' : (c.faction === '魔道' ? '#da3633' : '#238636')),
    };
  });

  // 关系：基于同章节共现
  const links = [];
  const linkSet = new Set();
  chapters.forEach(ch => {
    const charsText = ch.characters || '';
    const names = [];
    // 先尝试标准列表格式
    const re = /[-*]\s*([^、，,（：:\n]+)/g;
    let m;
    while ((m = re.exec(charsText)) !== null) {
      names.push(m[1].trim());
    }
    // 如果没匹配到，尝试顿号/逗号分隔
    if (!names.length && charsText.trim()) {
      const splitNames = charsText.split(/[、,，\s]+/).filter(n => n.trim().length >= 1);
      names.push(...splitNames.map(n => n.trim()));
    }
    for (let i = 0; i < names.length; i++) {
      for (let j = i + 1; j < names.length; j++) {
        const a = names[i], b = names[j];
        const key = a < b ? `${a}-${b}` : `${b}-${a}`;
        if (!linkSet.has(key)) {
          linkSet.add(key);
          links.push({ source: a, target: b, relation: '同章出现' });
        }
      }
    }
  });
  project.relations = links;

  let html = '';
  // 连线
  links.forEach(link => {
    const s = nodes.find(n => n.name === link.source);
    const t = nodes.find(n => n.name === link.target);
    if (s && t) {
      html += `<line x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}" class="graph-link" />`;
    }
  });

  // 节点
  nodes.forEach(n => {
    html += `
      <g class="graph-node" data-name="${escapeHtml(n.name)}">
        <circle cx="${n.x}" cy="${n.y}" r="24" fill="${n.color}" class="graph-node-circle" stroke="#0d1117" stroke-width="3"/>
        <text x="${n.x}" y="${n.y + 4}" class="graph-text">${escapeHtml(n.name)}</text>
      </g>
    `;
  });

  svg.innerHTML = html;

  svg.querySelectorAll('.graph-node').forEach(g => {
    g.addEventListener('click', () => {
      const name = g.dataset.name;
      showCharDetail(nodes.find(n => n.name === name));
    });
  });
}

function showCharDetail(char) {
  if (!char) return;
  const project = window.$app.project;
  const relations = (project.relations || []).filter(r => r.source === char.name || r.target === char.name);

  panel.innerHTML = `
    <div class="char-avatar" style="background:${char.color}">${char.name[0]}</div>
    <div class="char-name">${escapeHtml(char.name)}</div>
    <div class="char-role">${escapeHtml(char.role)} · ${escapeHtml(char.faction)}</div>
    
    <div class="card" style="margin-bottom:12px;">
      <div class="stat-row"><span class="stat-label">身份描述</span></div>
      <p style="font-size:13px; color:var(--text-primary); line-height:1.5;">${escapeHtml(char.desc)}</p>
    </div>
    
    <div class="card" style="margin-bottom:12px;">
      <h4 style="font-size:12px; color:var(--text-secondary); margin-bottom:10px;">🔗 关键关系</h4>
      ${relations.length ? relations.map(r => {
        const other = r.source === char.name ? r.target : r.source;
        return `<div class="stat-row"><span>${escapeHtml(other)}</span><span style="color:var(--text-secondary)">${r.relation}</span></div>`;
      }).join('') : '<p style="font-size:12px;color:var(--text-secondary);">暂无明确关系</p>'}
    </div>
    
    <div class="card">
      <h4 style="font-size:12px; color:var(--text-secondary); margin-bottom:10px;">📈 人物弧光</h4>
      ${char.arcs.length ? char.arcs.map(a => `
        <div style="font-size:12px; margin-bottom:8px; line-height:1.5;">
          <div style="color:var(--accent-blue)">${escapeHtml(a.chapter)}</div>
          <div style="color:var(--text-secondary)">${escapeHtml(a.event)}</div>
        </div>
      `).join('') : '<p style="font-size:12px;color:var(--text-secondary);">暂无弧光记录</p>'}
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
