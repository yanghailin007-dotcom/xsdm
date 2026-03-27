# 项目兼容性快速修复指南

## 已完成修改

### 1. 后端API修改 (phase_generation_api.py)

✅ **新增函数**:
- `detect_project_type(project_path)` - 自动检测项目类型
- `get_project_info_with_type(project_path, title)` - 获取包含类型的项目信息
- `detect_novel_type(title)` - API端点: GET /api/novel/{title}/detect-type
- `novel_continue_entry(title)` - API端点: GET/POST /api/novel/{title}/continue

✅ **修改函数**:
- `get_projectsWithPhaseStatus()` - 现在返回的项目包含 `project_type` 和 `type_display` 字段

### 2. API端点说明

```
GET /api/novel/{title}/detect-type
返回: {
    "success": true,
    "title": "...",
    "type": "market_driven|phase_one|legacy",
    "type_display": "市场导向|两阶段|传统",
    "info": {...}
}

GET /api/novel/{title}/continue
返回: {
    "success": true,
    "type": "market_driven",
    "redirect_url": "/pages/v2/market-driven-plan.html?title=...&mode=continue"
}

GET /api/projects/with-phase-status
返回的项目现在包含:
- project_type: "market_driven" | "phase_one" | "legacy"
- type_display: "市场导向" | "两阶段" | "传统"
```

### 3. 前端需要修改的文件

#### novels-v2.html (作品列表页)
需要添加根据项目类型显示不同按钮的逻辑：

```javascript
// 在渲染项目卡片时
function renderProjectCard(project) {
    const isMarketDriven = project.project_type === 'market_driven';
    
    return `
        <div class="project-card">
            <span class="badge ${isMarketDriven ? 'badge-market' : 'badge-phase'}">
                ${project.type_display}
            </span>
            
            ${isMarketDriven ? `
                <a href="/pages/v2/market-driven-plan.html?title=${encodeURIComponent(project.title)}" 
                   class="btn">规划</a>
                <a href="/pages/v2/market-driven-plan.html?title=${encodeURIComponent(project.title)}&mode=continue" 
                   class="btn btn-primary">续写</a>
            ` : `
                <a href="/pages/v2/project-management-v2.html?title=${encodeURIComponent(project.title)}" 
                   class="btn">管理</a>
                <a href="/pages/v2/phase-two-generation.html?title=${encodeURIComponent(project.title)}" 
                   class="btn btn-primary">续写</a>
            `}
        </div>
    `;
}
```

#### novel-v2.html (作品详情页)
需要根据类型加载不同数据：

```javascript
async function loadNovelData(title) {
    // 先检测项目类型
    const typeRes = await fetch(`/api/novel/${encodeURIComponent(title)}/detect-type`);
    const typeData = await typeRes.json();
    
    if (typeData.type === 'market_driven') {
        // 加载市场导向模式数据
        await loadMarketDrivenData(title);
    } else {
        // 加载两阶段模式数据
        await loadPhaseData(title);
    }
}
```

#### project-management-v2.html (项目管理页)
需要根据类型显示不同界面：

```javascript
async function initProject() {
    const title = getUrlParam('title');
    const typeRes = await fetch(`/api/novel/${encodeURIComponent(title)}/detect-type`);
    const typeData = await typeRes.json();
    
    if (typeData.type === 'market_driven') {
        // 重定向到市场导向规划页
        window.location.href = `/pages/v2/market-driven-plan.html?title=${encodeURIComponent(title)}`;
        return;
    }
    
    // 继续加载两阶段项目管理界面
    loadPhaseProjectData(title);
}
```

### 4. 项目类型判断逻辑

```python
def detect_project_type(project_path):
    """
    检测逻辑:
    1. 如果存在 project_info.json 且 generation_mode == "market_driven"
       -> "market_driven"
    2. 如果存在 products 目录或 novel_info.json
       -> "phase_one"
    3. 如果只有 chapters 目录
       -> "legacy"
    4. 其他
       -> "unknown"
    """
```

### 5. 新旧项目特征

| 特征 | 新模式 (market_driven) | 旧模式 (phase_one) |
|------|------------------------|-------------------|
| 标识文件 | project_info.json | novel_info.json |
| 产物目录 | phase_one_products/ | products/ |
| 状态文件 | .world_state.json | phase_status.json |
| generation_mode | "market_driven" | "phase_one" 或无 |

### 6. 快速测试

```bash
# 1. 重启服务器后，测试项目列表
curl http://localhost:5000/api/projects/with-phase-status

# 2. 测试项目类型检测
curl http://localhost:5000/api/novel/国运：扮演雷神队友白月魁/detect-type

# 3. 测试续写入口
curl http://localhost:5000/api/novel/国运：扮演雷神队友白月魁/continue
```

## 下一步

1. **重启服务器** - 使API修改生效
2. **测试API** - 使用上面的curl命令或test_project_api.py
3. **修改前端** - 根据上面的代码示例修改HTML文件
4. **验证功能** - 确保新旧项目都能正确显示和续写
