# 项目文件使用情况分析报告

**分析时间:** 2026-04-07  
**项目路径:** c:\work\xsdm  
**总文件数:** 865 个文件 (Python: 493, Markdown: 209, JSON: 194)

---

## 一、确认正在使用的核心文件列表

### 1.1 核心应用文件 (正在使用)

| 文件路径 | 说明 | 状态 |
|---------|------|------|
| `start.py` | 项目启动入口 | 使用中 |
| `web/app.py` | Web 应用主入口 | 使用中 |
| `web/api/*.py` | API 接口文件 (40+个) | 使用中 |
| `src/core/*.py` | 核心功能模块 | 使用中 |
| `src/managers/*.py` | 管理器模块 | 使用中 |
| `src/utils/*.py` | 工具模块 | 使用中 |
| `web/services/market_driven/*.py` | 市场驱动服务 | 使用中 |

### 1.2 配置和基础文件 (正在使用)

| 文件路径 | 说明 | 状态 |
|---------|------|------|
| `config/config.py` | 主配置 | 使用中 |
| `requirements.txt` | 依赖列表 | 使用中 |
| `setup.py` | 安装脚本 | 使用中 |

---

## 二、可疑的未使用文件列表（按优先级排序）

### 2.1 高优先级 - 建议删除 (42个文件)

#### A. 备份文件 (可安全删除)

| 文件路径 | 原因 | 最后修改 | 建议 |
|---------|------|---------|------|
| `web/fanqie_uploader/novel_publisher_backup.py` | 备份文件 | 2026-03-29 | **删除** |
| `web/services/upload_package_manager_old.py` | 旧版本文件 | 2026-03-29 | **删除** |

#### B. Archive 目录文件 (可安全删除)

| 文件路径 | 原因 | 建议 |
|---------|------|------|
| `archive/tests/test_first_time_hint.py` | 存档测试文件 | **删除** |
| `archive/tests/test_first_time_hint_final.py` | 存档测试文件 | **删除** |
| `archive/tests/test_first_time_hint_v2.py` | 存档测试文件 | **删除** |
| `archive/tests/test_phase_two_quick.py` | 存档测试文件 | **删除** |
| `archive/tests/test_phase_two_simple.py` | 存档测试文件 | **删除** |
| `archive/tests/test_quick.py` | 存档测试文件 | **删除** |
| `archive/tests/test_special_emotional_events_redesign.py` | 存档测试文件 | **删除** |
| `archive/tests/test_stage_plan_refactoring.py` | 存档测试文件 | **删除** |
| `archive/tests/test_stage_plan_simple.py` | 存档测试文件 | **删除** |
| `archive/tools/create_test_checkpoint.py` | 存档工具 | **删除** |
| `archive/tools/test_density_monitor.py` | 存档工具 | **删除** |
| `archive/tools/test_fanqie_simple.py` | 存档工具 | **删除** |
| `archive/tools/test_import_existing_images.py` | 存档工具 | **删除** |
| `archive/tools/test_optimizer.py` | 存档工具 | **删除** |
| `archive/tools/test_stage_planning_fix.py` | 存档工具 | **删除** |
| `archive/tools/test_still_image_library.py` | 存档工具 | **删除** |
| `archive/docs/E2E_TEST_GUIDE.md` | 存档文档 | **删除** |
| `archive/docs/RESUME_TESTING_GUIDE.md` | 存档文档 | **删除** |
| `archive/screenshots/` | 存档截图 (30+文件) | **删除** |

#### C. 废弃工具文件

| 文件路径 | 原因 | 最后修改 | 建议 |
|---------|------|---------|------|
| `tools/batch_delete_deprecated.py` | 文件名含 deprecated | 2026-03-29 | **删除** |
| `tools/batch_migrate_templates.py` | 临时迁移工具 | 2026-03-29 | **删除** |
| `tools/migrate_to_base_template.py` | 临时迁移工具 | 2026-03-29 | **删除** |
| `tools/temp_write.py` | 临时文件 | 2026-03-29 | **删除** |
| `tools/upload_script_template.py` | 临时文件 | 2026-03-29 | **删除** |

#### D. 未使用的旧模块

| 文件路径 | 原因 | 最后修改 | 建议 |
|---------|------|---------|------|
| `src/core/batch_generation/golden_chapters.py` | 未被 import，旧模块 | 2026-03-29 | **确认后删除** |
| `src/core/batch_generation/golden_chapters_assessor.py` | 未被 import，旧模块 | 2026-03-29 | **确认后删除** |
| `src/managers/SystemPowerDensityMonitor.py` | 未被 import，临时监控 | 2026-03-29 | **确认后删除** |
| `web/services/market_driven/prompt_templates.py` | 文件名含 temp，未 import | 2026-03-29 | **确认后删除** |

#### E. 重复/旧版本配置文件

| 文件路径 | 原因 | 建议 |
|---------|------|------|
| `prompt_packages/default/market_driven/chapter_templates.json` | 文件名含 temp | **删除** |
| `prompt_packages/default/market_driven/components/golden_chapter_guide.json` | 文件名含 old | **删除** |
| `prompt_packages/default/market_driven/components/golden_finger_templates.json` | 文件名含 old/temp | **删除** |
| `prompt_packages/default/market_driven/components/report_templates.json` | 文件名含 temp | **删除** |
| `prompt_packages/default/market_driven/phase_two/chapter_prompt_template.json` | 文件名含 temp | **删除** |
| `prompt_packages/default/market_driven/steps/step_templates.json` | 文件名含 temp | **删除** |
| `prompt_packages/default/market_driven/templates/chapter_templates.json` | 文件名含 temp | **删除** |
| `src/core/batch_generation/GOLDEN_CHAPTERS_GUIDE.md` | 文件名含 old | **删除** |

### 2.2 中优先级 - 需要确认 (59个文件)

#### A. 测试文件 (需要确认是否仍在使用)

| 文件路径 | 原因 | 建议 |
|---------|------|------|
| `test_base_conversation.py` | 根目录测试文件 | **检查引用后决定** |
| `test_conversation_api.py` | 根目录测试文件 | **检查引用后决定** |
| `test_global_float.py` | 根目录测试文件 | **检查引用后决定** |
| `test_prompt.py` | 根目录测试文件 | **检查引用后决定** |
| `test_session_memory.py` | 根目录测试文件 | **检查引用后决定** |
| `desktop_uploader/test_*.py` | 桌面上传器测试文件 (13个) | **检查引用后决定** |
| `tests/*.py` | 测试目录文件 (31个) | **保留/评估** |

#### B. 可能废弃的配置和模块

| 文件路径 | 原因 | 最后修改 | 建议 |
|---------|------|---------|------|
| `config/doubaoconfig.py` | 未被 import，旧豆包配置 | 2026-03-29 | **确认后删除** |
| `scripts/automain.py` | 未被 import | 2026-03-29 | **确认后删除** |
| `src/core/PhaseOneConversation.py` | 未被 import，内容含废弃标记 | 2026-04-04 | **确认后删除** |
| `src/prompts/VideoScenePrompts.py` | 未被 import，内容含废弃标记 | 2026-03-29 | **确认后删除** |

#### C. 旧版本文件

| 文件路径 | 原因 | 建议 |
|---------|------|------|
| `测试报告生成_v2.py` | v2 版本文件 | **确认新版本后删除** |
| `desktop_uploader/release/gui_account_manager_v2.py` | v2 版本文件 | **确认新版本后删除** |
| `scripts/update_navbar_v2.py` | v2 版本文件 | **确认新版本后删除** |

### 2.3 低优先级 - 建议保留但需检查 (9个文件)

| 文件路径 | 原因 | 建议 |
|---------|------|------|
| `temp_uploads/test_crlf/chrome_launcher/start_browser.py` | 临时目录但可能有用 | **保留观察** |
| `temp_uploads/test_crlf/upload/upload_script.py` | 临时目录但可能有用 | **保留观察** |
| `docs/PHASE_ONE_CONVERSATION_MODE.md` | 文档含废弃标记 | **归档或删除** |
| `docs/UNUSED_FILES_ANALYSIS.md` | 旧分析文档 | **归档或删除** |
| `docs/V2_MIGRATION_PLAN.md` | 旧迁移计划 | **归档或删除** |
| `docs/guides/WEB_GENERATION_GUIDE.md` | 文档含废弃标记 | **归档或删除** |
| `docs/novel_analysis/*.md` | 分析文档含废弃标记 | **归档或删除** |

---

## 三、建议删除的文件清单

### 3.1 可安全删除的文件 (推荐)

```
# 备份文件
web/fanqie_uploader/novel_publisher_backup.py
web/services/upload_package_manager_old.py

# Archive 目录 (全部)
archive/tests/
archive/tools/
archive/docs/
archive/screenshots/

# 废弃工具
tools/batch_delete_deprecated.py
tools/batch_migrate_templates.py
tools/migrate_to_base_template.py
tools/temp_write.py
tools/upload_script_template.py

# 旧配置文件
prompt_packages/default/market_driven/chapter_templates.json
prompt_packages/default/market_driven/components/golden_chapter_guide.json
prompt_packages/default/market_driven/components/golden_finger_templates.json
prompt_packages/default/market_driven/components/report_templates.json
prompt_packages/default/market_driven/phase_two/chapter_prompt_template.json
prompt_packages/default/market_driven/steps/step_templates.json
prompt_packages/default/market_driven/templates/chapter_templates.json
src/core/batch_generation/GOLDEN_CHAPTERS_GUIDE.md

# 临时目录
temp_uploads/
```

**预计可释放空间:** 约 10-20 MB (主要来自 archive/screenshots)

### 3.2 需要确认后再删除的文件

```
# 旧模块 (需要确认是否被其他地方引用)
src/core/batch_generation/golden_chapters.py
src/core/batch_generation/golden_chapters_assessor.py
src/managers/SystemPowerDensityMonitor.py
web/services/market_driven/prompt_templates.py

# 可能废弃的配置
config/doubaoconfig.py

# 可能废弃的模块
src/core/PhaseOneConversation.py
src/prompts/VideoScenePrompts.py
scripts/automain.py
```

---

## 四、建议保留但需要确认的文件清单

### 4.1 测试文件 (tests/ 目录)

```
tests/ 目录下的 44 个测试文件
```
**建议:** 保留但需要评估哪些测试仍在维护中。

### 4.2 Desktop Uploader 相关文件

```
desktop_uploader/release/ 目录下的核心文件 (保留)
desktop_uploader/test_*.py 测试文件 (评估)
```

### 4.3 分析脚本文件

```
analyze_log_times.py
analyze_unused_files.py
generate_report.py
deep_analysis.py
```
**建议:** 这些是本次分析使用的临时脚本，分析完成后可删除。

---

## 五、重复文件检测

### 5.1 可能重复的配置文件

```
prompt_packages/default/market_driven/chapter_templates.json
prompt_packages/default/market_driven/templates/chapter_templates.json
```
**分析:** 内容可能重复，保留一份即可。

### 5.2 重复的 Manager 文件

```
src/managers/ExpectationManager.py
src/managers/ExpectationManager_enriched.py
src/managers/ExpectationManager_Expanded.py
```
**建议:** 检查是否都是必需的，可能可以合并。

---

## 六、总结与建议

### 6.1 立即行动项

1. **删除 archive/ 目录** - 包含 51 个存档文件，可安全删除
2. **删除备份文件** - novel_publisher_backup.py, upload_package_manager_old.py
3. **删除废弃工具** - batch_delete_deprecated.py 等

### 6.2 需要评估的项

1. **确认旧模块使用情况** - golden_chapters.py, PhaseOneConversation.py 等
2. **整理 tests/ 目录** - 评估哪些测试仍在使用
3. **清理 docs/ 目录** - 将旧文档归档或删除

### 6.3 风险说明

- **低风险:** archive/ 目录、backup 文件、明确标记为废弃的文件
- **中风险:** 未被 import 但可能通过动态导入使用的文件
- **高风险:** 正在被使用的核心模块文件

### 6.4 建议的删除顺序

1. **第一阶段:** 删除 archive/ 目录和明显的备份文件
2. **第二阶段:** 删除标记为 deprecated 的工具脚本
3. **第三阶段:** 确认后删除未使用的旧模块
4. **第四阶段:** 整理测试文件和文档

---

**注意:** 本报告仅用于分析，实际删除文件前请确保已备份重要数据，并在开发/测试环境中验证后再应用到生产环境。
