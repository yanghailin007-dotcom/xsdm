    def _build_round2_prompt(self) -> str:
        """构建第2轮提示词 - 使用format方法避免f-string解析问题"""
        # 获取第1轮输出
        round1 = self.round1_result.get('core_framework', {}) if self.round1_result else {}
        
        # 获取情绪蓝图
        emotion_blueprint = self.phase_one_data.get('emotional_blueprint', {})
        climax_moments = emotion_blueprint.get('climax_moments', [])
        
        # 过滤出本章批内的高潮节点
        batch_climax = [c for c in climax_moments 
                       if self.start_chapter <= self._parse_chapter_num(c) <= self.end_chapter]
        
        # 获取情绪曲线（如果有）
        emotion_curve_text = ""
        if self.emotion_curve:
            relevant = [e for e in self.emotion_curve 
                       if self.start_chapter <= e.get('chapter', 0) <= self.end_chapter]
            emotion_curve_text = "\n".join([
                f"第{e.get('chapter')}章: {e.get('emotion', '')} (强度{e.get('intensity', 5)})"
                for e in relevant[:10]
            ])
        
        # 准备所有需要插入的变量
        world_building = self._format_simple_list(round1.get('world_building_chapters', []))
        golden_finger = self._format_simple_list(round1.get('golden_finger_progression', []))
        protagonist_moments = self._format_simple_list(round1.get('protagonist_moments', []))
        goal_milestones = json.dumps(round1.get('goal_milestones', {}), ensure_ascii=False, indent=2)
        key_constraints = self._format_list(round1.get('key_constraints', []))
        batch_climax_str = self._format_list(batch_climax)
        batch_climax_raw = ', '.join(str(c) for c in batch_climax) if batch_climax else '无'
        emotion_text = emotion_curve_text or '未提供详细曲线'
        
        # 使用format方法而不是f-string
        prompt = """# 番茄爆款细纲规划 - 第2轮：情绪爽点规划【核心轮】

## 任务
为小说《{novel_title}》规划第{start_chapter}-{end_chapter}章的**详细情绪设计**。
这是三轮中**最重要的一轮**，直接决定读者是否追读。

---

## 一、第1轮输出：设定框架（必须遵守）

### 世界观落地节点
{world_building}

### 金手指升级路线
{golden_finger}

### 主角人设高光时刻
{protagonist_moments}

### 阶段目标里程碑
{goal_milestones}

### 设定约束（绝对不能违反）
{key_constraints}

---

## 二、番茄爆款情绪公式（必须遵循）

### 黄金三章公式
- 第1章：极端压抑(9) - 主角被踩在泥里，读者憋屈想反击
- 第2章：持续嘲讽(8) - 反派疯狂嘲讽，读者愤怒积累  
- 第3章：强势反转(9) - 主角打脸，读者爽感爆发

### 小循环公式（每3-5章）
铺垫(6) → 冲突(7) → 爽点(8) → 渲染(7) → 新伏笔(6)

### 大高潮公式（每10章）
紧张(7) → 冲突升级(8) → 第一波爽(8) → 第二波爽(9) → 巅峰(10)

### 章尾钩子类型
- 悬念：提出新问题（"那个神秘人是谁？"）
- 危机：突然的危险（"一把刀架在了脖子上"）
- 反转：出乎意料（"没想到背后的黑手竟是他"）
- 震惊：颠覆认知（"原来一切都是假的"）
- 期待：预告即将发生（"明天就是决战之日"）

---

## 三、一阶段情绪设计（参考）

### 高潮节点（本章批内）
{batch_climax_str}

### 情绪曲线（前10章）
{emotion_text}

---

## 四、输出要求

请输出第{start_chapter}-{end_chapter}章的详细设计，JSON格式：

```json
{{
  "chapters": [
    {{
      "chapter_number": {start_chapter},
      "emotion": "压抑",
      "intensity": 9,
      "emotion_type": "绝望/愤怒/期待/爽快/震惊/满足",
      "beat_type": "铺垫/冲突/反转/渲染/爽点/伏笔",
      
      "event": "主要事件简述（100字内，必须体现设定）",
      "satisfaction_point": "本章爽点（可无，但不能连续2章无爽点）",
      "face_slapping": "打脸元素（如有）：反派嚣张→主角反转→反派崩溃",
      
      "hook_type": "悬念/危机/反转/震惊/期待",
      "hook_content": "章尾钩子内容（50字内，必须让读者想点下一章）",
      
      "goal_alignment": "如何推进阶段目标",
      "character_highlight": "哪个角色本章高光",
      "constraints": "本章必须遵守的设定约束"
    }}
  ],
  "emotion_analysis": {{
    "pattern": "开局爆发型/递进高潮型/蓄力积累型",
    "variance_score": "情绪起伏评分（1-10）",
    "satisfaction_distribution": "爽点分布说明",
    "hook_distribution": "钩子类型统计",
    "expected_retention": "预估追读率"
  }}
}}
```

---

## 五、番茄爆款硬性要求（必须遵守）

1. **章章有钩子**：每章最后50字必须是钩子，让读者忍不住点下一章
2. **不能连续2章无爽点**：最多隔1章必须有爽点交付
3. **打脸必须爽**：反派先嚣张→主角反转→反派崩溃，三层结构
4. **情绪有起伏**：相邻章情绪强度差必须≥1，不能平铺直叙
5. **高潮节点要对齐**：{batch_climax_raw} 必须是情绪巅峰
6. **设定不能丢**：每章必须体现国运绑定或金手指运用

---

## 六、参考示例

第1章（压抑9）：
- 事件：沈浪带二哈进禁地，全球嘲讽，华夏绝望
- 爽点：无（压抑开局）
- 钩子：沈浪对二哈说"看你的了"，二哈露出诡异微笑

第3章（反转9）：
- 事件：BOSS出现，沈浪弹幕改写规则，二哈啃死BOSS
- 爽点：首次展现金手指，荒诞方式击杀领主
- 打脸：詹姆斯从嘲讽到震惊到恐惧
- 钩子：不可一世的BOSS在二哈嘴里发出咔嚓声，全球直播间：？？？
""".format(
            novel_title=self.novel_title,
            start_chapter=self.start_chapter,
            end_chapter=self.end_chapter,
            world_building=world_building,
            golden_finger=golden_finger,
            protagonist_moments=protagonist_moments,
            goal_milestones=goal_milestones,
            key_constraints=key_constraints,
            batch_climax_str=batch_climax_str,
            batch_climax_raw=batch_climax_raw,
            emotion_text=emotion_text
        )
        
        return prompt
