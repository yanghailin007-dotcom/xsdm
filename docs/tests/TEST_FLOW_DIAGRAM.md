# 测试流程与数据流动图 (Test Flow & Data Flow Diagram)

## 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│         小说生成系统 - 完整测试架构                            │
└─────────────────────────────────────────────────────────────┘

                         测试入口层
                              │
                ┌─────────────┼─────────────┐
                │             │             │
         ┌──────▼───────┐     │      ┌──────▼───────┐
         │ test_quick.py│     │      │test_integration.py│
         │  (< 1 秒)    │     │      │   (3-5 秒)   │
         └──────┬───────┘     │      └──────┬───────┘
                │             │             │
                └─────────────┼─────────────┘
                              │
                         ┌────▼────┐
                         │ run_all  │
                         │ tests.py │
                         └────┬────┘
                              │
                    ┌─────────▼────────┐
                    │ test_e2e_with_   │
                    │ mock_data.py     │
                    │   (5-10 秒)      │
                    └──────┬───────────┘
                           │
                    ┌──────▼──────┐
                    │  测试报告   │
                    │  + 输出文件 │
                    └─────────────┘
```

## 快速测试流程 (test_quick.py)

```
test_quick.py
    │
    ├─ [1] 导入验证
    │   ├─ APIClient
    │   ├─ ContentGenerator
    │   └─ NovelGenerator
    │       └─ ✅ PASS
    │
    ├─ [2] Logger 功能
    │   ├─ get_logger("TestModule")
    │   ├─ logger.info("测试")
    │   └─ ✅ PASS
    │
    ├─ [3] GenerationContext
    │   ├─ 创建实例
    │   ├─ validate()
    │   └─ ✅ PASS
    │
    ├─ [4] 创意数据结构
    │   ├─ coreSetting 验证
    │   ├─ coreSellingPoints 验证
    │   └─ ✅ PASS
    │
    ├─ [5] JSON 序列化
    │   ├─ dumps + loads
    │   └─ ✅ PASS
    │
    ├─ [6] 文件操作
    │   ├─ 写入 JSON
    │   ├─ 读取 JSON
    │   └─ ✅ PASS
    │
    └─ [7] 系统配置
        ├─ CONFIG 加载
        ├─ api_keys 检查
        └─ ✅ PASS (7/7)
```

## 端到端测试流程 (test_e2e_with_mock_data.py)

```
test_e2e_with_mock_data.py
    │
    ├─ 初始化 TestScenario
    │   ├─ MockAPIClient
    │   ├─ MockEventBus
    │   └─ MockQualityAssessor
    │
    ├─ [1] 创意加载
    │   ├─ _create_mock_creative()
    │   ├─ 验证数据结构
    │   └─ ✅ PASS
    │
    ├─ [2] 小说初始化
    │   ├─ _create_mock_novel_data()
    │   ├─ 验证标题、简介、章节数
    │   └─ ✅ PASS
    │
    ├─ [3] 生成上下文
    │   ├─ GenerationContext(...)
    │   ├─ context.validate()
    │   └─ ✅ PASS
    │
    ├─ [4] 章节大纲
    │   ├─ api_client.call_api()
    │   ├─ 返回 JSON 大纲
    │   └─ ✅ PASS
    │
    ├─ [5] 章节内容
    │   ├─ api_client.call_api()
    │   ├─ 返回 3000+ 字文本
    │   └─ ✅ PASS
    │
    ├─ [6] 质量评估
    │   ├─ quality_assessor.assess()
    │   ├─ 返回评分数据
    │   └─ ✅ PASS
    │
    ├─ [7] 数据持久化
    │   ├─ 保存 creative.json
    │   ├─ 保存 novel_data.json
    │   ├─ 保存 chapter_001.txt
    │   └─ ✅ PASS
    │
    └─ [8] 完整流程 (5 章)
        ├─ Chapter 1
        │   ├─ 生成大纲
        │   ├─ 生成内容
        │   ├─ 质量评估
        │   └─ 保存 JSON
        │
        ├─ Chapter 2-5 (重复)
        │
        └─ ✅ PASS (7/8)

    输出文件结构:
    ├─ output/
    │   ├─ creative.json
    │   ├─ novel_data.json
    │   └─ chapter_001.txt
    │
    ├─ novel_output/
    │   ├─ chapter_001.json
    │   ├─ chapter_002.json
    │   ├─ chapter_003.json
    │   ├─ chapter_004.json
    │   ├─ chapter_005.json
    │   └─ test_report.txt
    │
    └─ test_report.txt
```

## 数据流动图 (Data Flow)

### 创意数据流

```
┌──────────────────────────────┐
│   虚假创意数据                │
│ _create_mock_creative()      │
│                              │
│  coreSetting: "凡人修仙..."  │
│  coreSellingPoints: "..."    │
│  completeStoryline: {...}    │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│    创意验证                   │
│  assert coreSetting           │
│  assert coreSellingPoints     │
│  assert completeStoryline     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│    JSON 序列化                 │
│  json.dumps(creative_data)   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│    保存为文件                  │
│  creative.json               │
└──────────────────────────────┘
```

### 小说生成流

```
┌─────────────────────────┐
│  虚假小说数据            │
│  mock_novel_data        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 小说初始化               │
│ • novel_title           │
│ • novel_synopsis        │
│ • total_chapters: 50    │
│ • current_progress      │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ 创建 GenerationContext   │
│ • chapter_number: 1     │
│ • total_chapters: 50    │
│ • novel_data            │
│ • stage_plan            │
└────────┬────────────────┘
         │
         ▼ (循环 5 次)
    ┌───┴────────────────────────────┐
    │                                │
    ▼                                │
┌─────────────────────────┐          │
│ 1. 生成大纲              │          │
│ chapter_title           │          │
│ outline                 │          │
│ word_count              │          │
└────────┬────────────────┘          │
         │                           │
         ▼                           │
┌─────────────────────────┐          │
│ 2. 生成内容              │          │
│ [3000+ 字小说内容]      │          │
└────────┬────────────────┘          │
         │                           │
         ▼                           │
┌─────────────────────────┐          │
│ 3. 质量评估              │          │
│ • 总体评分: 8.7         │          │
│ • 各维度评分            │          │
│ • 优点和建议            │          │
└────────┬────────────────┘          │
         │                           │
         ▼                           │
┌─────────────────────────┐          │
│ 4. 保存 JSON             │          │
│ chapter_XXX.json        │          │
└────────┬────────────────┘          │
         │                           │
         └───────────────┬───────────┘
                         │
                    (5 次后)
                         │
                         ▼
                ┌─────────────────┐
                │ 生成完整 JSON    │
                │ + 测试报告      │
                └─────────────────┘
```

### 模拟 API 调用流

```
├─ 用户请求
│  └─ messages: [{"role": "user", "content": "..."}]
│
└─ MockAPIClient.call_api()
   │
   ├─ 关键词检查
   │  ├─ "精炼|指令" → _mock_creative_refinement()
   │  ├─ "章节|大纲" → _mock_chapter_outline()
   │  ├─ "内容|情节" → _mock_chapter_content()
   │  ├─ "评估|质量" → _mock_quality_assessment()
   │  ├─ "角色|人物" → _mock_character_design()
   │  ├─ "世界|设定" → _mock_world_setting()
   │  └─ 其他        → _mock_default_response()
   │
   └─ 返回 JSON/文本
      └─ 传递给测试流程

响应示例:
{
  "创意精炼": { "plan_score": 9.2, ... },
  "章节大纲": { "chapter_title": "...", ... },
  "章节内容": "第一章 ...",
  "质量评估": { "score": 8.7, ... }
}
```

## 测试执行流 (Execution Flow)

```
run_all_tests.py
    │
    ├─ 记录开始时间
    │
    ├─ run_test("test_quick.py", "快速测试")
    │   ├─ subprocess.run()
    │   ├─ 捕获输出
    │   └─ 返回 (success, error)
    │
    ├─ run_test("test_e2e_with_mock_data.py", "端到端测试")
    │   ├─ subprocess.run()
    │   ├─ 捕获输出
    │   └─ 返回 (success, error)
    │
    ├─ run_test("test_integration.py", "集成测试")
    │   ├─ subprocess.run()
    │   ├─ 捕获输出
    │   └─ 返回 (success, error)
    │
    ├─ 记录结束时间
    │
    ├─ 统计结果
    │   └─ passed = 总通过数
    │
    └─ 输出总结
        ├─ 每个测试的通过/失败
        ├─ 总体通过率
        ├─ 总耗时
        └─ 最终状态信息
```

## 集成测试流程 (Integration Test Flow)

```
test_integration.py
    │
    ├─ create_mock_api_client()
    │   └─ Mock API 对象 (支持多种响应)
    │
    ├─ create_mock_event_bus()
    │   └─ Mock 事件总线 (支持 subscribe/emit)
    │
    ├─ test_with_real_components()
    │   │
    │   ├─ [步骤 1] 创建模拟 API 客户端
    │   ├─ [步骤 2] 创建模拟事件总线
    │   ├─ [步骤 3] 测试 API 调用
    │   ├─ [步骤 4] 构建创意数据
    │   ├─ [步骤 5] 构建小说数据
    │   ├─ [步骤 6] 创建生成上下文
    │   ├─ [步骤 7] 模拟 5 章生成
    │   └─ [步骤 8] 验证数据持久化
    │
    └─ test_mock_quality_assessment()
        ├─ 创建测试内容
        ├─ 调用质量评估
        └─ 验证评估结果
```

## 错误处理流程 (Error Handling)

```
测试执行
    │
    ├─ try:
    │   ├─ 执行测试逻辑
    │   └─ 返回成功
    │
    └─ except Exception as e:
        ├─ 记录错误信息
        ├─ logger.info(f"❌ 错误: {e}")
        └─ 返回失败


失败恢复:
    ├─ 如果是导入错误
    │   └─ 检查模块位置
    │
    ├─ 如果是文件错误
    │   └─ 检查文件权限
    │
    └─ 如果是数据错误
        └─ 检查模拟数据格式
```

## 文件生成结构 (Output Structure)

```
C:\Users\[user]\AppData\Local\Temp\
└─ test_凡人修仙同人E2E测试_xxxxx/
   │
   ├─ output/                 # [测试 7 生成]
   │   ├─ creative.json
   │   ├─ novel_data.json
   │   └─ chapter_001.txt
   │
   ├─ novel_output/           # [测试 8 生成]
   │   ├─ chapter_001.json    # 包含: 大纲 + 内容 + 评分
   │   ├─ chapter_002.json
   │   ├─ chapter_003.json
   │   ├─ chapter_004.json
   │   ├─ chapter_005.json
   │   └─ test_report.txt
   │
   └─ test_report.txt         # 最终报告


每个 chapter_XXX.json 的结构:
{
  "chapter_number": 1,
  "title": "乱星观劫·初现异象",
  "outline": {
    "章节号": 1,
    "核心事件": [...],
    "字数预估": "3500-4000"
  },
  "content": "第一章 乱星观劫·初现异象\n\n内容...",
  "assessment": {
    "整体评分": 8.7,
    "优点": [...],
    "改进建议": [...]
  },
  "generated_at": "2025-11-21T22:43:25"
}
```

## 数据验证流程 (Validation Flow)

```
测试数据
    │
    ├─ assert 检查
    │   ├─ 非空检查
    │   ├─ 类型检查
    │   ├─ 范围检查
    │   └─ 结构检查
    │
    ├─ validate() 方法
    │   ├─ GenerationContext.validate()
    │   ├─ 返回 (is_valid, message)
    │   └─ 完整的验证报告
    │
    └─ 结果判定
        ├─ 如果全部通过 → ✅ PASS
        └─ 如果任何失败 → ❌ FAIL
```

## 性能指标流 (Performance Metrics)

```
start_time = datetime.now()
    │
    ├─ 测试 1 (0.5s)
    ├─ 测试 2 (8s)
    └─ 测试 3 (4s)
    │
end_time = datetime.now()
    │
duration = (end_time - start_time).total_seconds()
    │
    └─ 总耗时: ~13-15s
        ├─ 快速测试: < 1s
        ├─ 端到端测试: 5-10s
        ├─ 集成测试: 3-5s
        └─ 总计: 15-20s
```

---

## 关键指标

| 阶段 | 输入 | 处理 | 输出 | 时间 |
|------|------|------|------|------|
| 快速测试 | 7 项检查 | 基础验证 | 7 个 PASS/FAIL | <1s |
| E2E 测试 | 8 个测试 | 完整流程 | 7-8 个 PASS/FAIL | 5-10s |
| 集成测试 | 2 个测试 | 真实+模拟 | 2 个 PASS/FAIL | 3-5s |
| 完全运行 | 17 项检查 | 全流程验证 | 总体通过率 | 15-20s |

---

**流程图版本**: v1.0  
**最后更新**: 2025-11-21
