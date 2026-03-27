# v3.0 优化器 + AI质检系统 上线报告

## 发布日期
2026-03-26

## 核心功能

### 1. v3.0 提示词优化器升级

#### 新增：微创新原则指南
System Prompt 现在包含完整的微创新指导：

**时间场景微创新**
- ❌ 避免：深夜23:47暴雨倾盆
- ✅ 尝试：凌晨5:30刚下班、早高峰地铁、正午烈日工地

**系统激活微创新**
- ❌ 避免：天降金光、额头流血
- ✅ 尝试：
  - 手机APP式：收到神秘短信，发件人是自己手机号
  - 延迟确认式：系统提示"24小时后激活"
  - AI助手式：像ChatGPT一样对话交互

**反派塑造微创新**
- ❌ 避免：纯嚣张"穷鬼就该有穷鬼的觉悟"
- ✅ 尝试：
  - 有目的的恶：为了利益/地位
  - 智商在线：会设局，借力打力
  - 网络暴力式：直播/朋友圈羞辱
  - 规则打压式：利用制度漏洞

**配角塑造微创新**
- ❌ 避免：只有主角和反派
- ✅ 尝试：至少2-3个配角在线
  - 支持者：偷偷帮助的小人物
  - 观望者：暂时中立，看形势站队
  - 记录者：拍照/直播的人

**钩子设计微创新**
- ❌ 避免："明天你就知道了"
- ✅ 尝试：
  - 时间锁："71小时59分后开奖"
  - 信息差：主角知道但读者不完全知道
  - 蝴蝶效应：系统警告小改变引发大后果
  - 多重可能：展示3种未来，主角必须选择

#### 第1章提示词增强
- 明确字数分配结构（0-500困境+500-2000系统+2000-2500钩子）
- 增加微创新自检清单
- 增加配角设计专项要求
- 增加主角情绪层次要求（希望→警惕→算计）

### 2. AI质检系统（新增模块）

#### 模块文件
- `web/services/market_driven/chapter_quality_checker.py`

#### 核心功能
**6大检查类别：**
1. **structure** - 结构检查（黄金三章合规性）
2. **tomato_algo** - 番茄算法指标验证
3. **genre** - 题材专项检查
4. **emotion** - 情绪曲线检查
5. **micro_innov** - 微创新检查
6. **completeness** - 完整性检查

**质检报告内容：**
- 总分（0-100）
- 检查项通过率
- 问题分类统计
- 自动修复后的提示词
- 是否可通过生成

#### 检查规则示例
```python
# 番茄算法检查
- 前300字必须有冲突
- 对话占比≥50%
- 章尾50字必须是钩子

# 微创新检查
- 避免"深夜暴雨"套路
- 避免"天降金光"系统激活
- 配角必须在线

# 结构检查
- 黄金三章必须包含字数分配
- 必须包含关键节拍
```

### 3. 生成器集成

#### 配置选项
```python
QUALITY_CHECK_CONFIG = {
    "enabled": True,           # 是否启用质检
    "min_score": 70,           # 最低通过分数
    "auto_fix": True,          # 是否自动修复
    "stop_on_critical": True,  # 严重问题是否停止
}
```

#### 使用方式
```python
from web.services.market_driven.chapter_conversation_generator import (
    generate_chapters_with_conversation
)

# 自定义质检配置
quality_config = {
    "enabled": True,
    "min_score": 80,
    "auto_fix": True,
    "stop_on_critical": False
}

chapters = generate_chapters_with_conversation(
    api_client=api_client,
    novel_data=novel_data,
    blueprint=blueprint,
    tropes=tropes,
    start_chapter=1,
    end_chapter=3,
    quality_config=quality_config
)
```

#### 质检汇总
生成完成后可获取质检汇总：
```python
generator = ChapterConversationGenerator(api_client, novel_data, tropes)
# ... 生成章节 ...
summary = generator.get_quality_summary()
# {
#   "total_chapters": 3,
#   "passed": 3,
#   "failed": 0,
#   "avg_score": 85.3,
#   "pass_rate": "100%"
# }
```

## 测试报告

### 测试结果
```
System Prompt 长度: 5676 字符
  [OK] 包含微创新指南

第1章提示词长度: 2466 字符
关键元素检查:
   [OK] 字数分配结构
   [OK] 番茄算法指标
   [OK] 微创新要求
   [OK] 系统激活
   [OK] 钩子要求

质检报告:
   总分: 90/100
   是否可通过: [OK] 是
   问题数: 3（均为INFO/WARNING级别）
   已生成优化提示词（+127字符）
```

### 发现的问题示例
```
🔵 [emotion] 未明确要求情绪转变次数
   建议: 添加'一章内至少3次情绪转变'的要求

🟡 [micro_innov] 系统激活方式过于老套（天降金光）
   建议: 尝试现代激活方式：手机APP、短信邀请等

🟡 [completeness] 未明确视角要求
   建议: 添加'第三人称上帝视角'的要求
```

## 文件变更

### 新增文件
- `web/services/market_driven/chapter_quality_checker.py` - AI质检系统
- `test_v3_quality_check.py` - 测试脚本
- `V3_QUALITY_CHECK_RELEASE.md` - 本发布文档

### 修改文件
- `web/services/market_driven/chapter_prompt_optimizer_v3.py`
  - 新增 `_build_micro_innovation_guide()` 方法
  - 新增 `_get_micro_innov_for_chapter_1()` 方法
  - 修改 `build_system_prompt()` 包含微创新指南
  - 修改 `_build_golden_chapter_1()` 增强微创新要求

- `web/services/market_driven/chapter_conversation_generator.py`
  - 导入质检模块
  - 新增质检配置
  - 集成质检到生成流程
  - 新增质检汇总功能

## 后续优化方向

1. **质检规则扩展**
   - 增加更多题材专项检查
   - 增加人设一致性检查
   - 增加剧情连贯性检查

2. **自动修复增强**
   - 基于AI的提示词优化
   - 学习历史优质提示词模式
   - 自动补充缺失的关键元素

3. **生成后质检**
   - 检查生成内容是否符合提示词要求
   - 字数/段落/对话占比验证
   - 情绪曲线实际表现分析

## 使用建议

1. **黄金三章必检**：前3章必须启用质检，确保开局质量
2. **关键章节必检**：打脸章、揭秘章等重要章节启用
3. **分数阈值**：建议设置min_score=75，确保基本质量
4. **自动修复**：建议开启auto_fix，让系统自动优化提示词
5. **人工复核**：质检分数<80的提示词建议人工复核
