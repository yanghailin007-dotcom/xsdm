# 市场导向对话打磨集成方案

## 集成概述

在现有的 `market-driven-plan.html` 页面中，添加对话打磨流程，替代/增强原有的表单填写方式。

## 改造点

### 1. 在页面头部引入评估组件

```html
{% block extra_css %}
<!-- 原有样式... -->

<!-- 引入对话打磨和评估组件样式 -->
<style>
/* ===== 对话打磨样式 ===== */
.dialog-polish-container {
  max-width: 900px;
  margin: 0 auto;
}

.dialog-round {
  background: var(--v2-bg-secondary);
  border: 1px solid var(--v2-border-subtle);
  border-radius: var(--radius-lg);
  padding: 28px;
  margin-bottom: 24px;
}

.dialog-round__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.dialog-round__badge {
  padding: 6px 14px;
  background: rgba(245, 158, 11, 0.15);
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  color: var(--primary-gold);
}

.dialog-round__title {
  font-size: 18px;
  font-weight: 700;
  color: var(--v2-text-primary);
}

.dialog-message {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(251, 191, 36, 0.04));
  border-left: 4px solid var(--primary-gold);
  padding: 20px;
  border-radius: 0 12px 12px 0;
  margin-bottom: 24px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--v2-text-primary);
  white-space: pre-wrap;
}

.dialog-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.dialog-option {
  background: var(--v2-bg-tertiary);
  border: 2px solid var(--v2-border-subtle);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.dialog-option:hover {
  border-color: rgba(245, 158, 11, 0.5);
  transform: translateY(-2px);
}

.dialog-option--selected {
  border-color: var(--primary-gold);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(251, 191, 36, 0.05));
}

.dialog-option__label {
  font-size: 16px;
  font-weight: 600;
  color: var(--v2-text-primary);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-option__description {
  font-size: 13px;
  color: var(--v2-text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
}

.dialog-option__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.dialog-option__tag {
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 500;
}

.dialog-option__tag--high {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.dialog-option__tag--medium {
  background: rgba(245, 158, 11, 0.15);
  color: var(--primary-gold);
}

.dialog-option__tag--low {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.dialog-option__tag--risk-high {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.dialog-custom {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--v2-border-subtle);
}

.dialog-custom__label {
  font-size: 14px;
  font-weight: 600;
  color: var(--v2-text-primary);
  margin-bottom: 12px;
  display: block;
}

.dialog-custom__input {
  width: 100%;
  padding: 12px 16px;
  background: var(--v2-bg-tertiary);
  border: 1px solid var(--v2-border-subtle);
  border-radius: 10px;
  font-size: 15px;
  color: var(--v2-text-primary);
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
}

.dialog-custom__input:focus {
  outline: none;
  border-color: var(--primary-gold);
}

.dialog-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid var(--v2-border-subtle);
}

.dialog-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.dialog-btn--primary {
  background: linear-gradient(135deg, var(--primary-gold), var(--primary-gold-dark, #d97706));
  color: #fff;
}

.dialog-btn--primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px -5px rgba(245, 158, 11, 0.4);
}

.dialog-btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.dialog-btn--secondary {
  background: var(--v2-bg-tertiary);
  color: var(--v2-text-primary);
  border: 1px solid var(--v2-border-subtle);
}

.dialog-btn--secondary:hover {
  background: var(--v2-border-subtle);
}

.dialog-history {
  margin-bottom: 24px;
}

.dialog-history__title {
  font-size: 14px;
  font-weight: 600;
  color: var(--v2-text-muted);
  margin-bottom: 12px;
}

.dialog-history__item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--v2-border-subtle);
}

.dialog-history__item:last-child {
  border-bottom: none;
}

.dialog-history__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.dialog-history__avatar--ai {
  background: rgba(245, 158, 11, 0.15);
  color: var(--primary-gold);
}

.dialog-history__avatar--user {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.dialog-history__content {
  flex: 1;
  font-size: 14px;
  color: var(--v2-text-primary);
  line-height: 1.6;
}

.dialog-mode-toggle {
  display: flex;
  justify-content: center;
  margin-bottom: 32px;
}

.dialog-mode-toggle__inner {
  display: inline-flex;
  background: var(--v2-bg-secondary);
  border: 1px solid var(--v2-border-subtle);
  border-radius: 100px;
  padding: 4px;
}

.dialog-mode-toggle__btn {
  padding: 10px 24px;
  border-radius: 100px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  background: transparent;
  color: var(--v2-text-secondary);
}

.dialog-mode-toggle__btn--active {
  background: linear-gradient(135deg, var(--primary-gold), var(--primary-gold-dark, #d97706));
  color: #fff;
}

/* 原有表单区域在对话模式下隐藏 */
.plan-form--hidden {
  display: none;
}
</style>
{% endblock %}
```

### 2. 修改 content 区域，添加对话模式切换

```html
{% block content %}
<div class="v2-project-container">
  
  <!-- Header -->
  <div class="plan-header">
    <a href="/market-driven-analysis?genre={{ genre }}" class="plan-header__back">
      <span class="material-icons">arrow_back</span>
      返回分析结果
    </a>
    <h1 class="plan-header__title">生成创作方案</h1>
    <p class="plan-header__subtitle">基于市场规律，打造差异化爆款小说</p>
  </div>

  <!-- 模式切换 -->
  <div class="dialog-mode-toggle">
    <div class="dialog-mode-toggle__inner">
      <button class="dialog-mode-toggle__btn dialog-mode-toggle__btn--active" id="mode-dialog" onclick="switchMode('dialog')">
        <span class="material-icons" style="font-size: 16px; vertical-align: middle; margin-right: 4px;">chat</span>
        对话打磨模式
      </button>
      <button class="dialog-mode-toggle__btn" id="mode-form" onclick="switchMode('form')">
        <span class="material-icons" style="font-size: 16px; vertical-align: middle; margin-right: 4px;">edit</span>
        表单填写模式
      </button>
    </div>
  </div>

  <!-- 对话打磨模式 -->
  <div id="dialog-mode-container" class="dialog-polish-container">
    <div id="dialog-content">
      <!-- 对话内容将动态加载 -->
      <div class="dialog-round" style="text-align: center; padding: 60px;">
        <div class="eval-loading__spinner" style="margin: 0 auto 24px;"></div>
        <div style="font-size: 18px; font-weight: 600; color: var(--v2-text-primary);">
          正在初始化对话打磨...
        </div>
        <div style="font-size: 14px; color: var(--v2-text-secondary); margin-top: 8px;">
          基于{{ genre }}的Top100作品分析
        </div>
      </div>
    </div>
  </div>

  <!-- 表单填写模式（原有） -->
  <div id="form-mode-container" class="plan-form plan-form--hidden">
    <!-- 原有表单内容... -->
  </div>

  <!-- 生成按钮 -->
  <div class="generate-section">
    <div class="generate-section__info">
      <div class="generate-section__icon">
        <span class="material-icons">auto_fix_high</span>
      </div>
      <div class="generate-section__text">
        <span class="generate-section__label">准备生成</span>
        <span class="generate-section__value" id="generate-status">等待选择创作模式...</span>
      </div>
    </div>
    <button class="generate-btn" id="generate-btn" onclick="startGeneration()" disabled>
      <span class="material-icons">rocket_launch</span>
      开始生成
    </button>
  </div>

</div>

<!-- 引入评估报告组件 -->
{% include 'components/ai-evaluation-report.html' %}

<!-- 原有Modal... -->
{% endblock %}
```

### 3. 添加 JavaScript 逻辑

```html
{% block extra_js %}
<script>
// ==================== 对话打磨管理 ====================

let dialogSessionId = null;
let dialogHistory = [];
let creativeDraft = null;
let currentMode = 'dialog';

// 初始化
async function initDialogPolish() {
  try {
    const genre = getGenreFromUrl();
    const tropes = getTropesFromStorage();
    
    const response = await fetch('/api/market-driven/dialog/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ genre, tropes })
    });
    
    const data = await response.json();
    
    if (data.success) {
      dialogSessionId = data.session_id;
      renderDialogRound(data);
      updateGenerateStatus('对话打磨中，请选择选项');
    } else {
      showError('初始化对话失败: ' + data.error);
    }
  } catch (error) {
    showError('网络错误: ' + error.message);
  }
}

// 渲染对话轮次
function renderDialogRound(roundData) {
  const container = document.getElementById('dialog-content');
  
  // 构建历史记录
  let historyHtml = '';
  if (dialogHistory.length > 0) {
    historyHtml = `
      <div class="dialog-history">
        <div class="dialog-history__title">对话记录</div>
        ${dialogHistory.map(h => `
          <div class="dialog-history__item">
            <div class="dialog-history__avatar dialog-history__avatar--${h.role}">
              ${h.role === 'ai' ? '🤖' : '👤'}
            </div>
            <div class="dialog-history__content">${h.content}</div>
          </div>
        `).join('')}
      </div>
    `;
  }
  
  // 构建选项
  const optionsHtml = roundData.options.map((opt, idx) => `
    <div class="dialog-option" onclick="selectOption('${opt.id}', this)" data-option="${opt.id}">
      <div class="dialog-option__label">
        ${opt.label}
      </div>
      <div class="dialog-option__description">${opt.description}</div>
      <div class="dialog-option__meta">
        ${opt.market_score ? `<span class="dialog-option__tag dialog-option__tag--${opt.market_score >= 80 ? 'high' : opt.market_score >= 65 ? 'medium' : 'low'}">市场化评分: ${opt.market_score}</span>` : ''}
        ${opt.risk ? `<span class="dialog-option__tag ${opt.risk === '高' ? 'dialog-option__tag--risk-high' : 'dialog-option__tag--medium'}">风险: ${opt.risk}</span>` : ''}
        ${opt.combo_effect ? `<span class="dialog-option__tag" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">组合效果</span>` : ''}
      </div>
      ${opt.combo_effect ? `<div style="margin-top: 8px; font-size: 12px; color: var(--v2-text-muted); font-style: italic;">${opt.combo_effect}</div>` : ''}
    </div>
  `).join('');
  
  // 构建自定义输入
  const customHtml = roundData.allow_custom ? `
    <div class="dialog-custom">
      <label class="dialog-custom__label">💡 我有自己的想法：</label>
      <textarea class="dialog-custom__input" id="custom-input" placeholder="描述你的想法，AI会帮你评估可行性..."></textarea>
    </div>
  ` : '';
  
  // 构建按钮
  const buttonsHtml = `
    <div class="dialog-actions">
      <button class="dialog-btn dialog-btn--secondary" onclick="goBack()" ${roundData.round <= 1 ? 'style="visibility: hidden;"' : ''}>
        <span class="material-icons">arrow_back</span>
        返回上一步
      </button>
      <button class="dialog-btn dialog-btn--primary" id="confirm-btn" onclick="confirmSelection()" disabled>
        <span class="material-icons">check_circle</span>
        确认选择
      </button>
    </div>
  `;
  
  container.innerHTML = `
    ${historyHtml}
    <div class="dialog-round">
      <div class="dialog-round__header">
        <span class="dialog-round__badge">第 ${roundData.round} 轮</span>
        <span class="dialog-round__title">${getRoundTitle(roundData.round_type)}</span>
      </div>
      <div class="dialog-message">${roundData.ai_message}</div>
      <div class="dialog-options">
        ${optionsHtml}
      </div>
      ${customHtml}
      ${buttonsHtml}
    </div>
  `;
  
  // 滚动到新内容
  container.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 选择选项
let selectedOption = null;

function selectOption(optionId, element) {
  // 移除其他选中状态
  document.querySelectorAll('.dialog-option').forEach(el => {
    el.classList.remove('dialog-option--selected');
  });
  
  // 添加选中状态
  element.classList.add('dialog-option--selected');
  selectedOption = optionId;
  
  // 启用确认按钮
  document.getElementById('confirm-btn').disabled = false;
}

// 确认选择
async function confirmSelection() {
  if (!selectedOption) return;
  
  const customText = document.getElementById('custom-input')?.value || '';
  
  // 添加到历史
  const selectedLabel = document.querySelector(`[data-option="${selectedOption}"] .dialog-option__label`)?.textContent || selectedOption;
  dialogHistory.push(
    { role: 'ai', content: document.querySelector('.dialog-message').textContent },
    { role: 'user', content: selectedLabel + (customText ? `（自定义：${customText}）` : '') }
  );
  
  // 显示加载
  document.getElementById('confirm-btn').disabled = true;
  document.getElementById('confirm-btn').innerHTML = '<span class="material-icons">hourglass_top</span> 处理中...';
  
  try {
    const response = await fetch('/api/market-driven/dialog/continue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: dialogSessionId,
        choice: selectedOption,
        custom_text: customText
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      selectedOption = null;
      
      if (data.is_final) {
        // 对话结束，显示确认
        creativeDraft = data.creative_draft;
        renderFinalConfirm(data);
      } else {
        renderDialogRound(data);
      }
    } else {
      showError('提交失败: ' + data.error);
    }
  } catch (error) {
    showError('网络错误: ' + error.message);
  }
}

// 渲染最终确认
function renderFinalConfirm(roundData) {
  const container = document.getElementById('dialog-content');
  
  container.innerHTML = `
    <div class="dialog-round">
      <div class="dialog-round__header">
        <span class="dialog-round__badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">方案确认</span>
        <span class="dialog-round__title">创意方案整理完成</span>
      </div>
      <div class="dialog-message" style="border-left-color: #22c55e; background: linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(34, 197, 94, 0.04));">${roundData.ai_message}</div>
      <div class="dialog-actions" style="justify-content: center;">
        <button class="dialog-btn dialog-btn--primary" onclick="startAIEvaluation()" style="padding: 16px 32px; font-size: 16px;">
          <span class="material-icons">analytics</span>
          进行AI市场化评估
        </button>
      </div>
    </div>
  `;
  
  updateGenerateStatus('方案已确认，等待评估');
}

// 开始AI评估
async function startAIEvaluation() {
  if (!creativeDraft) return;
  
  // 显示评估报告加载
  showEvaluationReport({}, {
    onProceed: (data) => {
      // 用户接受评估，开始生成
      startGenerationWithDraft();
    },
    onOptimize: (data) => {
      // 用户想继续优化，返回对话
      goBackToDialog();
    }
  });
  
  try {
    const genre = getGenreFromUrl();
    
    const response = await fetch('/api/market-driven/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        genre: genre,
        dialog_history: creativeDraft.dialog_history || dialogHistory,
        creative_draft: creativeDraft
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      renderEvaluationReport(data.evaluation);
      updateGenerateStatus('评估完成，等待确认');
      document.getElementById('generate-btn').disabled = false;
    } else {
      closeEvaluationModal();
      showError('评估失败: ' + data.error);
    }
  } catch (error) {
    closeEvaluationModal();
    showError('网络错误: ' + error.message);
  }
}

// 基于草案开始生成
async function startGenerationWithDraft() {
  if (!creativeDraft) return;
  
  // 填充表单数据
  document.getElementById('novel-title').value = creativeDraft.title || '';
  document.getElementById('protagonist-name').value = creativeDraft.protagonist || '';
  document.getElementById('golden-finger-desc').value = creativeDraft.golden_finger || '';
  
  // 调用原有生成逻辑
  startGeneration();
}

// 返回上一步
async function goBack() {
  if (!dialogSessionId) return;
  
  const targetRound = Math.max(1, (dialogHistory.length / 2));
  
  try {
    const response = await fetch('/api/market-driven/dialog/back', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: dialogSessionId,
        target_round: targetRound
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      // 移除最后一条历史
      dialogHistory = dialogHistory.slice(0, -2);
      selectedOption = null;
      renderDialogRound(data);
    }
  } catch (error) {
    showError('返回失败: ' + error.message);
  }
}

// 返回对话
function goBackToDialog() {
  renderFinalConfirm({ ai_message: creativeDraft.unique_points });
}

// 获取轮次标题
function getRoundTitle(roundType) {
  const titles = {
    'init': '差异化方向选择',
    'protagonist': '主角性格设定',
    'golden_finger': '金手指设计',
    'plot_details': '剧情细节',
    'emotion_line': '情感副线',
    'confirm': '方案确认'
  };
  return titles[roundType] || '创意打磨';
}

// 切换模式
function switchMode(mode) {
  currentMode = mode;
  
  // 更新按钮样式
  document.getElementById('mode-dialog').classList.toggle('dialog-mode-toggle__btn--active', mode === 'dialog');
  document.getElementById('mode-form').classList.toggle('dialog-mode-toggle__btn--active', mode === 'form');
  
  // 显示/隐藏对应区域
  document.getElementById('dialog-mode-container').style.display = mode === 'dialog' ? 'block' : 'none';
  document.getElementById('form-mode-container').classList.toggle('plan-form--hidden', mode === 'dialog');
  
  // 更新状态
  updateGenerateStatus(mode === 'dialog' ? '对话打磨中...' : '表单填写模式');
  document.getElementById('generate-btn').disabled = mode === 'dialog';
}

// 更新生成状态文本
function updateGenerateStatus(text) {
  document.getElementById('generate-status').textContent = text;
}

// 辅助函数
function getGenreFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get('genre') || '国运文-直播类';
}

function getTropesFromStorage() {
  const cached = localStorage.getItem('marketDrivenAnalysis');
  return cached ? JSON.parse(cached).tropes : {};
}

function showError(message) {
  alert(message);
}

// 页面加载时初始化
if (document.getElementById('dialog-mode-container')) {
  initDialogPolish();
}

// ==================== 原有表单逻辑... ====================
</script>
{% endblock %}
```

## API 端点列表

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/market-driven/dialog/start` | POST | 开始对话打磨 |
| `/api/market-driven/dialog/continue` | POST | 继续对话 |
| `/api/market-driven/dialog/back` | POST | 返回上一步 |
| `/api/market-driven/dialog/draft/<id>` | GET | 获取创意草案 |
| `/api/market-driven/evaluate` | POST | AI市场化评估 |

## 流程图

```
用户选择题材
    ↓
套路分析
    ↓
对话打磨（6轮）
    ├─ 第1轮：差异化方向选择
    ├─ 第2轮：主角性格
    ├─ 第3轮：金手指设定
    ├─ 第4轮：剧情细节
    ├─ 第5轮：情感副线
    └─ 第6轮：方案确认
    ↓
AI市场化评估
    ├─ 预测完读率/留存率
    ├─ 风险分析
    ├─ 同类案例参考
    └─ 优化建议
    ↓
用户决策
    ├─ 接受 → 生成方案
    └─ 优化 → 返回对话
```
