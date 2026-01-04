# 势力系统检测修复总结

## 问题描述

**症状**：
- 日志显示：`✅ 势力/阵营系统已保存: 小说项目\重生成剑：宿主祭天，法力无边\materials\worldview\重生成剑：宿主祭天，法力无边_势力系统.js`
- 但产物检测显示：`❌ factions`

**矛盾点**：文件明明保存成功了，为什么检测不到？

## 根本原因

通过诊断脚本发现：

1. **文件实际位置**：`小说项目/重生成剑：宿主祭天，法力无边/materials/worldview/重生成剑：宿主祭天，法力无边_势力系统.json` ✅ 存在

2. **ProductLoader 加载逻辑**：
   ```python
   # 旧代码（错误）
   worldview_dir = self.project_dir / "worldview"  # 先检查这个
   if not worldview_dir.exists():
       worldview_dir = self.project_dir / "materials" / "worldview"  # 再检查这个
   ```

3. **问题所在**：
   - 项目同时存在 `worldview/` 和 `materials/worldview/` 两个目录
   - `worldview/` 目录存在但是**空的**
   - ProductLoader 找到 `worldview/` 后就停止查找，没有继续检查 `materials/worldview/`
   - 结果：在空目录中找不到势力系统文件 ❌

## 修复方案

### 1. 调整加载优先级

**修改文件**：[`web/api/phase_generation_api.py`](web/api/phase_generation_api.py:235)

**修改前**：
```python
def _load_faction_system(self, products):
    worldview_dir = self.project_dir / "worldview"  # ❌ 先检查旧路径
    if not worldview_dir.exists():
        worldview_dir = self.project_dir / "materials" / "worldview"
```

**修改后**：
```python
def _load_faction_system(self, products):
    worldview_dir = self.project_dir / "materials" / "worldview"  # ✅ 优先检查新路径
    if not worldview_dir.exists():
        worldview_dir = self.project_dir / "worldview"
```

### 2. 同步修复其他产物加载

同样的逻辑也应用于：
- [`_load_worldview`](web/api/phase_generation_api.py:319) - 世界观加载
- 其他可能从 `materials/` 目录加载的产物

### 3. 添加 MaterialManager 命名规则

**修改文件**：[`src/core/MaterialManager.py`](src/core/MaterialManager.py:52)

**新增**：
```python
"faction_system": "{safe_title}_势力系统.json",  # 固定文件名，不带时间戳
```

这确保势力系统文件名的一致性。

## 验证结果

运行诊断脚本后：

```
[SUCCESS] 找到 2 个势力系统相关文件:

1. 小说项目/重生成剑：宿主祭天，法力无边/materials/worldview\重生成剑：宿主祭天，法力无边_势力系统.json
   扩展名: .json
   ✅ 文件可读，包含 4 个顶级键
```

修复后，ProductLoader 应该能正确检测到势力系统文件。

## 相关文件

- [`web/api/phase_generation_api.py`](web/api/phase_generation_api.py) - ProductLoader 类
- [`src/core/MaterialManager.py`](src/core/MaterialManager.py) - 材料管理器
- [`src/core/PhaseGenerator.py`](src/core/PhaseGenerator.py:581) - 保存势力系统
- [`src/config/path_config.py`](src/config/path_config.py) - 路径配置

## 后续建议

1. **统一目录结构**：建议逐步废弃 `worldview/` 目录，统一使用 `materials/worldview/`
2. **添加迁移逻辑**：自动将旧目录中的文件迁移到新目录
3. **增强日志**：在加载产物时记录检查的所有路径，便于调试

## 修复时间

2026-01-04 10:16 UTC+8