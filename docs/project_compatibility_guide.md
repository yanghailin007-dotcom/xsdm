# 项目格式兼容性指南

## 项目类型检测

### 1. 新模式 (market_driven)
**特征文件**: `project_info.json`
```json
{
  "generation_mode": "market_driven",
  "novel_title": "...",
  "project_info.json存在": true
}
```

**目录结构**:
```
小说项目/{username}/{novel_title}/
├── project_info.json          # 项目信息
├── chapters/                  # 章节文件
├── phase_one_products/        # 第一阶段产物
├── .world_state.json         # 世界状态
├── .character_state.json     # 角色状态
└── generation_history.json   # 生成历史
```

### 2. 旧模式 (phase_one/two)
**特征**: 没有 `project_info.json`，有 `novel_info.json` 或 `products/` 目录

**目录结构**:
```
小说项目/{username}/{novel_title}/
├── novel_info.json           # 小说信息
├── chapters/                 # 章节文件
├── products/                 # 产物目录
│   ├── worldview.json
│   ├── characters.json
│   └── ...
└── phase_status.json        # 阶段状态
```

## API兼容性修改

### 项目列表接口
```python
def get_project_type(project_path: Path) -> str:
    '''检测项目类型'''
    if (project_path / "project_info.json").exists():
        return "market_driven"
    elif (project_path / "products").exists() or (project_path / "novel_info.json").exists():
        return "phase_one"
    else:
        return "legacy"
```

### 续写路由区分
```python
@app.route('/api/novel/<title>/continue', methods=['GET'])
def continue_novel(title):
    project_type = get_project_type(title)
    
    if project_type == "market_driven":
        return redirect(f'/market-driven/continue/{title}')
    else:
        return redirect(f'/phase-two/continue/{title}')
```

## 前端界面适配

### 作品列表页 (novels-v2.html)
```javascript
// 根据项目类型显示不同操作按钮
function renderProjectActions(project) {
    if (project.type === 'market_driven') {
        return `
            <a href="/market-driven/plan?title=${project.title}" class="btn">市场分析</a>
            <a href="/market-driven/continue?title=${project.title}" class="btn btn-primary">续写</a>
        `;
    } else {
        return `
            <a href="/phase-one/status?title=${project.title}" class="btn">第一阶段</a>
            <a href="/phase-two/continue?title=${project.title}" class="btn btn-primary">续写</a>
        `;
    }
}
```

### 项目管理页 (project-management-v2.html)
```javascript
// 根据项目类型加载不同数据
async function loadProjectData(title) {
    const type = await detectProjectType(title);
    
    if (type === 'market_driven') {
        await loadMarketDrivenData(title);
    } else {
        await loadPhaseData(title);
    }
}
```

## 数据迁移工具

### 旧项目升级脚本
```python
def migrate_legacy_project(project_path: Path):
    '''将旧项目升级为新格式'''
    # 1. 读取旧数据
    old_info = json.load((project_path / "novel_info.json").open())
    
    # 2. 创建 project_info.json
    project_info = {
        "novel_title": old_info.get("title"),
        "generation_mode": "market_driven",  # 或保持原模式
        "created_at": old_info.get("created_at"),
        "generation_metadata": {
            "mode": old_info.get("generation_mode", "phase_one"),
            "total_chapters": old_info.get("completed_chapters", 0),
        }
    }
    
    # 3. 保存新格式
    json.dump(project_info, (project_path / "project_info.json").open('w'))
```

## 界面兼容性组件

### 通用项目卡片
```html
<div class="project-card" data-type="{{ project.type }}">
    <div class="project-header">
        <h3>{{ project.title }}</h3>
        <span class="badge badge-{{ project.type }}">
            {{ '市场导向' if project.type == 'market_driven' else '两阶段' }}
        </span>
    </div>
    
    <div class="project-actions">
        {% if project.type == 'market_driven' %}
            <a href="/market-driven/plan?title={{ project.title }}" class="btn">规划</a>
            <a href="/market-driven/continue?title={{ project.title }}" class="btn-primary">续写</a>
        {% else %}
            <a href="/phase-one/status?title={{ project.title }}" class="btn">第一阶段</a>
            <a href="/phase-two/generation?title={{ project.title }}" class="btn-primary">第二阶段</a>
        {% endif %}
    </div>
</div>
```

## 路由配置

### 续写路由统一入口
```python
# web/api/novel_routes.py

@novel_api.route('/novel/<title>/continue', methods=['GET', 'POST'])
def novel_continue(title):
    """
    统一的续写入口
    自动检测项目类型并路由到对应处理
    """
    username = get_current_username()
    project_path = find_project_path(title, username)
    
    if not project_path:
        return jsonify({"error": "项目不存在"}), 404
    
    # 检测项目类型
    project_type = detect_project_type(project_path)
    
    if request.method == 'GET':
        # 返回续写页面URL
        if project_type == 'market_driven':
            return jsonify({
                "redirect_url": f"/pages/v2/market-driven-continue.html?title={quote(title)}",
                "type": "market_driven"
            })
        else:
            return jsonify({
                "redirect_url": f"/pages/v2/phase-two-generation.html?title={quote(title)}",
                "type": "phase_two"
            })
    
    else:  # POST
        # 执行续写
        if project_type == 'market_driven':
            return continue_market_driven(title, request.json)
        else:
            return continue_phase_two(title, request.json)
```

## 快速修复清单

### 1. API修改
- [ ] 修改 `get_projectsWithPhaseStatus()` 支持检测 project_info.json
- [ ] 添加 `detect_project_type()` 工具函数
- [ ] 修改续写接口，根据类型路由

### 2. 前端修改
- [ ] novels-v2.html: 根据项目类型显示不同按钮
- [ ] novel-v2.html: 根据项目类型加载不同数据
- [ ] project-management-v2.html: 兼容两种项目格式

### 3. 新增页面
- [ ] market-driven-continue.html: 市场导向续写界面
- [ ] 或复用现有 market-driven-plan.html 添加续写模式
