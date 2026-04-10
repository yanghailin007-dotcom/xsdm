# V2 六层架构配置文件

## 重要区分

### 🔴 项目信息驱动（Layer 1-2）- 不能修改配置文件
这些层级内容从**项目信息动态提取**，每个项目不同：
- **Layer 1 核心设定**: 从 novel_data 的 character_design、golden_finger 等提取
- **Layer 2 战术规划**: 从 tactical_plan 的章节规划、阶段目标等提取

**修改方式**: 在项目页面修改角色设定、金手指设定等

---

### 🟢 用户可配置（Layer 3-6）- 可以修改 YAML
这些层级是**通用规则**，通过 YAML 文件配置：

#### Layer 3: 题材技法
`genre_techniques/神豪文.yaml` - 神豪文专项规则
`genre_techniques/国运文.yaml` - 国运文专项规则

#### Layer 4: 文风技法
`writing_style.yaml` - 番茄快节奏爽文规范（待添加）

#### Layer 5: AI约束
`ai_constraints.yaml` - 字数、格式、禁止事项

#### Layer 6: 自检清单
`self_check.yaml` - 写作前/后检查项

#### 情绪曲线
`emotion_curves.yaml` - 打脸章/爆发章等情绪曲线模板

---

## 修改示例

### ✅ 可以修改的（Layer 3-6）

修改神豪文的金额要求：
```yaml
# genre_techniques/神豪文.yaml
must_include:
  - element: "精确金额"
    check: "至少5处具体金额，精确到分"  # 从3处改为5处
```

修改字数要求：
```yaml
# ai_constraints.yaml
word_count:
  target: 2500  # 从2200改为2500
```

### ❌ 不要修改（Layer 1-2 从项目信息提取）

这些内容是动态生成的，修改 example 文件无效：
- `core_setting_example.yaml` - 仅作为示例
- `tactical_planning_example.yaml` - 仅作为示例

---

## 如何修改 Layer 1-2 的内容

### Layer 1 核心设定
在项目页面的以下位置修改：
1. **主角设定** → 修改 Layer 1.1 主角人设
2. **金手指设定** → 修改 Layer 1.2 金手指
3. **世界观设定** → 修改 Layer 1.3 世界规则

### Layer 2 战术规划
1. **阶段规划** → 修改 Layer 2.1 阶段信息
2. **章节规划** → 修改 Layer 2.2 本章目标
3. **情绪设计** → 修改 Layer 2.4 情绪曲线

---

## 故障排除

**Q: 为什么修改了 core_setting_example.yaml 没效果？**
A: Layer 1-2 是从项目信息动态提取的，不是从配置文件加载的。需要在项目页面修改。

**Q: 哪些配置修改后需要重启？**
A: 只有 Layer 3-6 的 YAML 文件修改后需要重启 Flask。
