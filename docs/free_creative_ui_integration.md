# 自由创意对话模式前端UI集成文档

## 概述

自由创意模式已改造为4步对话流程，需要前端UI适配展示新的步骤。

## 4步流程与UI映射

```
┌─────────────────────────────────────────────────────────────────┐
│  步骤1: 商业化分析 (20%)  →  UI Stage: "analysis"               │
│  📊 检测同人文 + 补充背景 + 番茄适配分析                         │
├─────────────────────────────────────────────────────────────────┤
│  步骤2: 多方案生成 (40%)  →  UI Stage: "planning"               │
│  💡 AI生成2-3个方案 + 自动评分                                   │
├─────────────────────────────────────────────────────────────────┤
│  步骤3: 智能选优 (70%)    →  UI Stage: "optimization"           │
│  ⚡ 自动选择最优 + 对比爆款优化                                  │
├─────────────────────────────────────────────────────────────────┤
│  步骤4: 方案深化 (100%)   →  UI Stage: "finalization"           │
│  ✨ 输出完整final_plan + 番茄上传数据                            │
└─────────────────────────────────────────────────────────────────┘
```

## 后端配置启用

在小说配置文件或API调用参数中添加：

```json
{
  "use_creative_conversation_mode": true
}
```

## WebSocket/事件消息格式

### 1. 步骤状态更新

```javascript
// 后端发送的消息
{
  "type": "phase_one.progress",
  "data": {
    "stage": "analysis",           // UI stage标识
    "progress": 20,                // 进度百分比
    "message": "正在进行商业化分析...",
    "points_consumed": 150,
    "step_status": {
      "analysis": "active",        // 当前步骤状态
      "planning": "pending",
      "optimization": "pending",
      "finalization": "pending"
    },
    // 扩展信息
    "detail": "检测同人文类型并补充背景资料"
  }
}
```

### 2. 步骤完成事件

```javascript
{
  "type": "phase_one.step_status",
  "data": {
    "step": "analysis",
    "status": "completed",
    "progress": 20,
    "result": {
      "is_fanfiction": true,
      "original_work": { /* ... */ },
      "core_selling_points": { /* ... */ }
    }
  }
}
```

### 3. 最终结果

```javascript
{
  "type": "phase_one.complete",
  "data": {
    "mode": "creative_conversation",
    "total_turns": 4,
    "final_plan": { /* 完整方案 */ },
    "tomato_upload_data": {
      "title": "书名",
      "synopsis": "简介",
      "tags": ["标签1", "标签2"]
    }
  }
}
```

## UI组件建议

### 1. 步骤进度条

```vue
<template>
  <div class="creative-steps">
    <a-steps :current="currentStep" direction="vertical">
      <a-step 
        v-for="(step, index) in steps" 
        :key="step.step_id"
        :title="step.name"
        :description="step.description"
        :status="getStepStatus(index)"
      >
        <template #icon>
          <span class="step-icon">{{ step.icon }}</span>
        </template>
      </a-step>
    </a-steps>
  </div>
</template>

<script>
const steps = [
  { step_id: 'commercial_analysis', name: '商业化分析', icon: '📊', description: '同人文检测 + 背景补充' },
  { step_id: 'multi_plan_generation', name: '多方案生成', icon: '💡', description: 'AI生成2-3个方案并评分' },
  { step_id: 'selection_bestseller', name: '智能选优', icon: '⚡', description: '自动选择 + 爆款对标' },
  { step_id: 'final_plan_deepening', name: '方案深化', icon: '✨', description: '输出完整final_plan' }
];
</script>
```

### 2. 实时进度卡片

```vue
<template>
  <div class="progress-card" :style="{ borderColor: currentStage.color }">
    <div class="stage-icon">{{ currentStage.icon }}</div>
    <div class="stage-info">
      <h4>{{ currentStage.label }}</h4>
      <p>{{ progress.message }}</p>
      <a-progress :percent="progress.progress" :stroke-color="currentStage.color" />
      <span class="detail">{{ progress.detail }}</span>
    </div>
  </div>
</template>

<script>
const stageConfig = {
  analysis: { icon: '📊', label: '创意分析', color: '#1890ff' },
  planning: { icon: '💡', label: '方案生成', color: '#52c41a' },
  optimization: { icon: '⚡', label: '方案优化', color: '#faad14' },
  finalization: { icon: '✨', label: '方案完成', color: '#722ed1' }
};
</script>
```

### 3. 结果展示面板

```vue
<template>
  <div class="results-panel">
    <!-- 商业化分析结果 -->
    <a-card title="商业化分析" v-if="results.commercial_analysis">
      <p>类型: {{ results.commercial_analysis.is_fanfiction ? '同人文' : '原创' }}</p>
      <p v-if="results.commercial_analysis.is_fanfiction">
        原作: {{ results.commercial_analysis.original_work.name }}
      </p>
      <p>核心卖点: {{ results.commercial_analysis.core_selling_points.one_liner }}</p>
    </a-card>
    
    <!-- 生成的方案 -->
    <a-card title="生成的方案" v-if="results.multi_plan">
      <a-collapse>
        <a-collapse-panel 
          v-for="plan in results.multi_plan.plans" 
          :key="plan.id"
          :header="`${plan.title} (评分: ${plan.total_score})`"
        >
          <p>核心设定: {{ plan.core_setting.protagonist }} + {{ plan.core_setting.golden_finger }}</p>
          <p>差异化: {{ plan.differentiation }}</p>
          <p>风险: {{ plan.risks }}</p>
        </a-collapse-panel>
      </a-collapse>
    </a-card>
    
    <!-- 选定的方案 -->
    <a-card title="最终方案" v-if="results.selected_plan">
      <h3>{{ results.selected_plan.selection.selected_title }}</h3>
      <p>选择理由: {{ results.selected_plan.selection.selection_reason }}</p>
      <p>对比爆款: {{ results.selected_plan.bestseller_comparison.reference_works.map(w => w.title).join(', ') }}</p>
    </a-card>
    
    <!-- 番茄上传数据 -->
    <a-card title="番茄上传数据" v-if="results.tomato_data">
      <p><strong>书名:</strong> {{ results.tomato_data.title }}</p>
      <p><strong>简介:</strong> {{ results.tomato_data.synopsis }}</p>
      <p><strong>标签:</strong> <a-tag v-for="tag in results.tomato_data.tags" :key="tag">{{ tag }}</a-tag></p>
    </a-card>
  </div>
</template>
```

## API调用示例

### 启动自由创意生成

```javascript
// POST /api/novel/generate
{
  "mode": "free_creative",
  "title": "我的小说",
  "synopsis": "小说简介...",
  "category": "玄幻",
  "creative_seed": "创意种子...",
  "config": {
    "use_creative_conversation_mode": true,  // 启用对话模式
    "provider": "gemini",
    "model_name": "gemini-3-pro"
  }
}
```

### WebSocket订阅进度

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'phase_one.progress':
      updateProgress(data.data);
      break;
    case 'phase_one.step_status':
      updateStepStatus(data.data);
      break;
    case 'phase_one.complete':
      showResults(data.data);
      break;
  }
};
```

## 与传统模式的对比

| 特性 | 传统模式 | 对话模式（新） |
|------|----------|----------------|
| 步骤数 | 13+ 步骤 | 4 步骤 |
| API调用 | 15-20 次 | 4 次 |
| 耗时 | 8-12 分钟 | 3-5 分钟 |
| 前端展示 | 复杂，多阶段 | 简洁，4步清晰 |
| 用户干预 | 需要选择方案 | 全自动 |

## 回退机制

如果对话模式失败，后端会自动回退到传统模式：

```javascript
// 失败通知
{
  "type": "phase_one.failed",
  "data": {
    "error": "对话模式执行失败",
    "fallback": true,  // 是否已回退
    "message": "已回退到传统生成模式"
  }
}
```

## 配置文件路径

```
prompt_packages/default/free_creative/conversation/conversation_steps.json
```

可通过修改此文件调整UI显示文案。
