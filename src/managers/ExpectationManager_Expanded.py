# 扩充版期待感管理系统 - 网文完整套路覆盖

## 概述

本文档定义了扩充到20种的期待感类型，覆盖主流网文的所有常见套路，并解决了原系统的三个核心问题：
1. **类型扩充**: 从6种扩充到20种
2. **深度集成**: 真正集成到章节生成流程
3. **事件驱动**: 与事件系统深度绑定，避免固定章节要求

---

## 一、20种期待感类型完整定义

### 原有6种（保留）

#### 1. 展示橱窗 (showcase)
**原理**: 提前展示奖励或能力的强大，让读者期待获得
**种植**: 反派展示法术/传说描述宝物/目睹高阶修士施法
**释放**: 主角获得/学会/达成
**最小间隔**: 3章

#### 2. 压抑释放 (suppression_release)
**原理**: 制造阻碍→积累势能→释放爽感
**种植**: 立靶子/给限制/攒资源
**释放**: 至暗时刻→最终逆转
**最小间隔**: 5章

#### 3. 套娃期待 (nested_doll)
**原理**: 大期待包小期待，环环相扣
**种植**: 在满足期待的同时开启新期待
**释放**: 分层满足，层层推进
**最小间隔**: 2章

#### 4. 情绪钩子 (emotional_hook)
**原理**: 打脸、认同、身份揭秘
**种植**: 误解/轻视/隐藏身份
**释放**: 展示实力/真相揭晓/他人震惊
**最小间隔**: 2章

#### 5. 实力差距 (power_gap)
**原理**: 展示主角与目标的差距，期待变强
**种植**: 遭遇碾压/展示强者/明确差距
**释放**: 实力提升/缩小差距/逆转局面
**最小间隔**: 5章

#### 6. 伏笔揭秘 (mystery_foreshadow)
**原理**: 埋下线索，期待真相
**种植**: 埋线索/提谜题/暗示秘密
**释放**: 答案揭晓/逻辑自洽/恍然大悟
**最小间隔**: 7章

---

### 新增14种

#### 7. 扮猪吃虎 (pig_eats_tiger)
**原理**: 主角隐藏实力，被轻视后打脸
**种植**: 主角故意示弱/他人轻视嘲讽
**释放**: 主角展露真实实力，全场震惊
**触发条件**: 主动隐藏或被迫隐藏实力
**最小间隔**: 2-3章

**实现示例**:
```python
# 第5章：主角被嘲笑是废物
{
    "expectation_type": "pig_eats_tiger",
    "planting_chapter": 5,
    "description": "长老嘲讽主角资质平庸，主角默默承受",
    "target_chapter": 8,
    "planting_method": "描写他人的轻视态度和主角的隐忍",
    "release_method": "关键时刻主角展露真实实力，所有人震惊后悔"
}
```

#### 8. 装逼打脸 (show_off_face_slap)
**原理**: 主角展示实力/财富/人脉，让轻视者打脸
**种植**: 主角准备展示/有人质疑/立下赌约
**释放**: 展示成果/事实说话/众人震惊
**触发条件**: 他人质疑或不相信主角
**最小间隔**: 1-2章

**实现示例**:
```python
# 第10章：主角扬言能炼制极品丹药
{
    "expectation_type": "show_off_face_slap",
    "planting_chapter": 10,
    "description": "宗门长老不信主角能炼制四品丹药",
    "target_chapter": 12,
    "planting_method": "立下赌约，众人质疑",
    "release_method": "炼制成功，丹药品质超预期，长老打脸"
}
```

#### 9. 身份反转 (identity_reveal)
**原理**: 主角隐藏真实身份，揭晓时带来震撼
**种植**: 埋下身份线索/暗示特殊背景
**释放**: 身份揭晓/众人震惊/地位改变
**触发条件**: 剧情发展到关键时刻
**最小间隔**: 10-15章（长期伏笔）

**实现示例**:
```python
# 第3章：暗示主角身世不凡
{
    "expectation_type": "identity_reveal",
    "planting_chapter": 3,
    "description": "主角身上的玉佩散发奇异光芒",
    "target_chapter": 30,
    "planting_method": "埋下身份线索，偶尔暗示",
    "release_method": "身份揭晓，原来是某某大能转世/遗孤"
}
```

#### 10. 美人恩 (beauty_favor)
**原理**: 女主对主角有好感，制造感情期待
**种植**: 女主出现/初次互动/埋下好感种子
**释放**: 女主主动/表白/维护主角
**触发条件**: 主角展现魅力/拯救女主
**最小间隔**: 3-5章

**实现示例**:
```python
# 第8章：主角救下女主
{
    "expectation_type": "beauty_favor",
    "planting_chapter": 8,
    "description": "主角从魔兽爪下救下圣女",
    "target_chapter": 12,
    "planting_method": "女主对主角产生好感，但未明说",
    "release_method": "关键时刻女主主动帮助主角，暗示心意"
}
```

#### 11. 机缘巧合 (fortuitous_encounter)
**原理**: 意外获得奇遇/宝物/传承
**种植**: 发现线索/误入秘境/偶然机会
**释放**: 获得机缘/实力提升/命运改变
**触发条件**: 主角探索或冒险
**最小间隔**: 2-3章

**实现示例**:
```python
# 第15章：主角发现古老洞府
{
    "expectation_type": "fortuitous_encounter",
    "planting_chapter": 15,
    "description": "主角在深山发现隐藏洞府入口",
    "target_chapter": 17,
    "planting_method": "发现线索，引起好奇",
    "release_method": "进入洞府，获得上古大能传承"
}
```

#### 12. 比试切磋 (competition)
**原理**: 宗门大比/擂台赛/武会切磋
**种植**: 宣布比赛/立下赌约/众人质疑
**释放**: 比赛进行/主角获胜/打脸质疑者
**触发条件**: 定期赛事或临时挑战
**最小间隔**: 5章（准备期）+ 3章（比赛期）

**实现示例**:
```python
# 第20章：宣布宗门大比
{
    "expectation_type": "competition",
    "planting_chapter": 20,
    "description": "宗门宣布年度大比，前三名可获得筑基丹",
    "target_chapter": 28,
    "planting_method": "宣布比赛规则，众人看好种子选手",
    "release_method": "主角一路过关斩将，最终夺得冠军"
}
```

#### 13. 拍卖会争宝 (auction_treasure)
**原理**: 拍卖会上看中宝物，与竞拍者争夺
**种植**: 发现宝物/准备资金/遇到竞拍对手
**释放**: 拍卖开始/激烈竞价/最终获得
**触发条件**: 参加拍卖会
**最小间隔**: 3-5章

**实现示例**:
```python
# 第25章：主角参加拍卖会
{
    "expectation_type": "auction_treasure",
    "planting_chapter": 25,
    "description": "拍卖会上出现稀世灵药",
    "target_chapter": 28,
    "planting_method": "主角看中灵药，但发现竞争对手",
    "release_method": "激烈竞价，最终高价拍得"
}
```

#### 14. 秘境探险 (secret_realm_exploration)
**原理**: 进入秘境/遗迹/副本探险
**种植**: 发现秘境入口/组建队伍/准备物资
**释放**: 探险过程/获得宝物/遭遇危险
**触发条件**: 获得秘境线索或地图
**最小间隔**: 8-10章

**实现示例**:
```python
# 第30章：发现上古遗迹地图
{
    "expectation_type": "secret_realm_exploration",
    "planting_chapter": 30,
    "description": "主角获得上古遗迹地图",
    "target_chapter": 40,
    "planting_method": "召集伙伴，准备探险",
    "release_method": "进入遗迹，历经凶险，获得重宝"
}
```

#### 15. 炼丹炼器 (alchemy_crafting)
**原理**: 炼制丹药/炼制法器，展示能力
**种植**: 获得配方/准备材料/开始炼制
**释放**: 炼制成功/品质超预期/众人震惊
**触发条件**: 主角掌握炼丹/炼器技能
**最小间隔**: 2-3章

**实现示例**:
```python
# 第18章：主角开始炼制筑基丹
{
    "expectation_type": "alchemy_crafting",
    "planting_chapter": 18,
    "description": "主角获得筑基丹配方",
    "target_chapter": 21,
    "planting_method": "收集材料，准备炼制",
    "release_method": "炼制成功，品质达到上品"
}
```

#### 16. 阵法破解 (formation_breaking)
**原理**: 破解阵法/解谜/过关
**种植**: 遇到阵法/分析阵法/尝试破解
**释放**: 破解成功/获得奖励/展现智慧
**触发条件**: 遇到阵法阻拦
**最小间隔**: 2-4章

**实现示例**:
```python
# 第22章：主角遇到上古护山大阵
{
    "expectation_type": "formation_breaking",
    "planting_chapter": 22,
    "description": "遗迹入口被大阵封印",
    "target_chapter": 25,
    "planting_method": "分析阵法原理，寻找破解之法",
    "release_method": "成功破解，进入遗迹"
}
```

#### 17. 宗门任务 (sect_mission)
**原理**: 完成宗门任务获得奖励
**种植**: 接取任务/了解要求/开始执行
**释放**: 完成任务/获得奖励/提升地位
**触发条件**: 宗门发布任务
**最小间隔**: 3-5章

**实现示例**:
```python
# 第12章：主角接取宗门任务
{
    "expectation_type": "sect_mission",
    "planting_chapter": 12,
    "description": "接取击杀二阶魔兽的任务",
    "target_chapter": 16,
    "planting_method": "了解任务要求，准备出发",
    "release_method": "完成任务，获得贡献点和奖励"
}
```

#### 18. 跨界传送 (cross_world_teleport)
**原理**: 跨越位面/世界/传送
**种植**: 发现传送阵/获得传送符/偶然触发
**释放**: 传送到新世界/探索新环境/遇到新挑战
**触发条件**: 获得传送机会
**最小间隔**: 10-15章（长期主线）

**实现示例**:
```python
# 第35章：主角发现上古传送阵
{
    "expectation_type": "cross_world_teleport",
    "planting_chapter": 35,
    "description": "发现通往上界的传送阵",
    "target_chapter": 50,
    "planting_method": "修复传送阵，准备穿越",
    "release_method": "成功传送到上界，开启新篇章"
}
```

#### 19. 危机救援 (crisis_rescue)
**原理**: 他人陷入危机，主角出手相救
**种植**: 发现危机/决定救援/制定计划
**释放**: 实施救援/化险为夷/获得感激
**触发条件**: 重要人物陷入危机
**最小间隔**: 2-3章

**实现示例**:
```python
# 第14章：得知好友被绑架
{
    "expectation_type": "crisis_rescue",
    "planting_chapter": 14,
    "description": "得知好友被魔修绑架",
    "target_chapter": 17,
    "planting_method": "调查线索，追踪魔修",
    "release_method": "成功救出好友，击败魔修"
}
```

#### 20. 师恩传承 (master_inheritance)
**原理**: 获得师父指点/传承功法
**种植**: 遇到良师/展现天赋/获得认可
**释放**: 师父传授/功法升级/实力大增
**触发条件**: 遇到潜在的师父
**最小间隔**: 5-8章

**实现示例**:
```python
# 第7章：主角遇到隐世高人
{
    "expectation_type": "master_inheritance",
    "planting_chapter": 7,
    "description": "主角遇到隐居的元婴期老祖",
    "target_chapter": 15,
    "planting_method": "老祖考验主角心性",
    "release_method": "老祖收主角为徒，传授绝世功法"
}
```

---

## 二、事件驱动的期待绑定机制

### 核心改进：从"固定章节"到"事件驱动"

**原系统问题**:
```python
# ❌ 固定章节要求，可能打乱叙事节奏
min_chapters_before_release=3  # 必须等待3章
```

**改进方案**:
```python
# ✅ 与事件深度绑定，根据事件进度自动判断
{
    "expectation_type": "show_off_face_slap",
    "bound_event_id": "alchemy_competition_001",  # 绑定到事件
    "trigger_condition": "event_reaches_climax",  # 触发条件
    "flexible_range": {  # 灵活范围，而非固定章节
        "min_chapters": 1,  # 最少1章
        "max_chapters": 5,  # 最多5章
        "optimal_chapters": 3  # 最佳3章
    }
}
```

### 事件绑定策略

#### 1. 自动事件匹配

```python
def auto_bind_expectation_to_event(event: Dict) -> ExpectationType:
    """根据事件类型自动匹配最合适的期待类型"""
    
    event_goal = event.get("main_goal", "").lower()
    event_type = event.get("type", "")
    
    # 决策树
    if "比试" in event_goal or "大比" in event_goal:
        return ExpectationType.COMPETITION
    
    if "炼丹" in event_goal or "炼器" in event_goal:
        return ExpectationType.ALCHEMY_CRAFTING
    
    if "拍卖" in event_goal or "竞拍" in event_goal:
        return ExpectationType.AUCTION_TREASURE
    
    if "秘境" in event_goal or "遗迹" in event_goal:
        return ExpectationType.SECRET_REALM_EXPLORATION
    
    if "救援" in event_goal or "救" in event_goal:
        return ExpectationType.CRISIS_RESCUE
    
    # ... 更多匹配规则
    
    return ExpectationType.NESTED_DOLL  # 默认套娃期待
```

#### 2. 事件进度追踪

```python
class EventDrivenExpectationManager(ExpectationManager):
    """事件驱动的期待管理器"""
    
    def check_expectation_readiness(self, chapter_num: int, event_context: Dict) -> List[str]:
        """检查哪些期待已经准备好可以释放"""
        
        ready_expectations = []
        
        for exp_id, exp_record in self.expectations.items():
            if exp_record.status != ExpectationStatus.PLANTED:
                continue
            
            # 获取绑定的信息
            bound_event_id = exp_record.bound_event_id
            if not bound_event_id:
                # 如果没有绑定事件，使用传统的章节判断
                if exp_record.target_chapter and chapter_num >= exp_record.target_chapter:
                    ready_expectations.append(exp_id)
                continue
            
            # 获取事件进度
            event_progress = self._get_event_progress(bound_event_id, event_context)
            
            # 判断事件是否到达合适的释放时机
            if self._should_release_expectation(exp_record, event_progress):
                ready_expectations.append(exp_id)
        
        return ready_expectations
    
    def _get_event_progress(self, event_id: str, event_context: Dict) -> Dict:
        """获取事件的进度信息"""
        
        # 从事件上下文中查找
        active_events = event_context.get("active_events", [])
        for event in active_events:
            if event.get("id") == event_id:
                return {
                    "current_chapter": event.get("current_chapter", 0),
                    "total_chapters": event.get("total_chapters", 0),
                    "phase": event.get("current_phase", "unknown"),
                    "progress_percentage": event.get("progress_percentage", 0)
                }
        
        return {}
    
    def _should_release_expectation(
        self, 
        exp_record: ExpectationRecord, 
        event_progress: Dict
    ) -> bool:
        """判断是否应该释放期待"""
        
        if not event_progress:
            return False
        
        # 获取灵活范围
        flexible_range = exp_record.flexible_range
        if not flexible_range:
            # 如果没有灵活范围，使用传统的目标章节
            return False
        
        # 根据事件进度判断
        progress_percentage = event_progress.get("progress_percentage", 0)
        
        # 事件进度达到60-90%时是最佳释放时机
        if 60 <= progress_percentage <= 90:
            return True
        
        # 如果超过最大等待范围，强制释放
        if progress_percentage > 90:
            return True
        
        return False
```

---

## 三、深度集成到章节生成流程

### ContentGenerator集成方案

```python
class ContentGenerator:
    def generate_chapter_content_for_novel(
        self, 
        chapter_number: int, 
        novel_data: Dict, 
        context: GenerationContext = None
    ) -> Optional[Dict]:
        """生成章节内容 - 集成期待系统"""
        
        # 1. 初始化期待管理器（如果尚未初始化）
        if not hasattr(self, 'expectation_manager'):
            from src.managers.ExpectationManager import ExpectationManager
            self.expectation_manager = ExpectationManager()
        
        # 2. 生成前检查：获取本章期待约束
        expectation_constraints = self.expectation_manager.pre_generation_check(
            chapter_num=chapter_number,
            event_context=context.event_context if context else {}
        )
        
        # 3. 构建期待感指导
        expectation_guidance = self._build_expectation_guidance(
            chapter_number,
            expectation_constraints,
            context
        )
        
        # 4. 将期待指导添加到章节参数
        chapter_params = self._prepare_chapter_params(
            chapter_number, 
            novel_data
        )
        chapter_params["expectation_guidance"] = expectation_guidance
        
        # 5. 生成章节内容（AI会根据期待指导生成）
        chapter_data = self.generate_chapter_content(chapter_params)
        
        # 6. 生成后验证：检查期待是否被满足
        validation_result = self.expectation_manager.post_generation_validate(
            chapter_num=chapter_number,
            content_analysis={"content": chapter_data.get("content", "")},
            released_expectation_ids=chapter_data.get("released_expectations", [])
        )
        
        # 7. 将验证结果添加到章节数据
        chapter_data["expectation_validation"] = validation_result
        
        # 8. 如果验证失败，记录警告
        if not validation_result.get("passed", True):
            self.logger.warning(
                f"⚠️ 第{chapter_number}章期待感验证未完全通过: "
                f"{len(validation_result.get('violations', []))}个违规"
            )
        
        return chapter_data
    
    def _build_expectation_guidance(
        self,
        chapter_number: int,
        expectation_constraints: List[ExpectationConstraint],
        context: GenerationContext
    ) -> str:
        """构建期待感指导文本"""
        
        if not expectation_constraints:
            return ""
        
        guidance_parts = [
            "\n## 🎯 本章期待感要求（AI必须严格遵守）\n"
        ]
        
        for constraint in expectation_constraints:
            urgency_icon = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }.get(constraint.urgency, "⚪")
            
            guidance_parts.append(
                f"{urgency_icon} **{constraint.message}**"
            )
            
            if constraint.suggestions:
                guidance_parts.append("\n**建议操作:**")
                for suggestion in constraint.suggestions:
                    guidance_parts.append(f"  - {suggestion}")
            
            guidance_parts.append("")
        
        # 添加核心原则
        guidance_parts.extend([
            "### 核心原则",
            "1. **永远不要让读者\"清静\"**: 每章都要么释放旧期待,要么种植新期待",
            "2. **接力式期待**: 在满足一个期待的同时,开启下一个期待",
            "3. **可视化期待**: 让读者明确知道\"好东西\"在哪里,但主角暂时得不到",
            "4. **自然融入情节**: 期待感的释放必须符合剧情发展,不要生硬插入",
            ""
        ])
        
        return "\n".join(guidance_parts)
```

---

## 四、期待感质量监控

### 期待感密度指标

```python
class ExpectationDensityMonitor:
    """期待感密度监控器"""
    
    def calculate_density(self, start_chapter: int, end_chapter: int) -> Dict:
        """计算期待感密度"""
        
        total_chapters = end_chapter - start_chapter + 1
        
        # 统计各类期待数量
        expectation_counts = {}
        for exp_record in self.expectation_manager.expectations.values():
            if start_chapter <= exp_record.planted_chapter <= end_chapter:
                exp_type = exp_record.expectation_type.value
                expectation_counts[exp_type] = expectation_counts.get(exp_type, 0) + 1
        
        # 计算密度
        density = {
            "total_expectations": sum(expectation_counts.values()),
            "expectations_per_chapter": sum(expectation_counts.values()) / total_chapters,
            "type_distribution": expectation_counts,
            "density_rating": self._rate_density(sum(expectation_counts.values()), total_chapters)
        }
        
        return density
    
    def _rate_density(self, total_expectations: int, total_chapters: int) -> str:
        """评估密度等级"""
        density = total_expectations / total_chapters
        
        if density >= 1.5:
            return "过高"
        elif density >= 1.0:
            return "优秀"
        elif density >= 0.7:
            return "良好"
        elif density >= 0.5:
            return "一般"
        else:
            return "不足"
    
    def generate_recommendations(self, density: Dict) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        rating = density.get("density_rating", "")
        
        if rating == "不足":
            recommendations.append(
                "期待感密度不足，建议增加期待种植。每10章应至少有5-8个期待。"
            )
        elif rating == "过高":
            recommendations.append(
                "期待感密度过高，可能导致读者疲劳。建议适当减少，或延长期待发酵时间。"
            )
        
        # 检查类型分布
        type_dist = density.get("type_distribution", {})
        if not type_dist.get("pig_eats_tiger"):
            recommendations.append("建议增加'扮猪吃虎'类型的期待，这是网文经典套路。")
        
        if not type_dist.get("show_off_face_slap"):
            recommendations.append("建议增加'装逼打脸'类型的期待，提升爽感。")
        
        return recommendations
```

---

## 五、使用示例

### 完整流程示例

```python
# 1. 阶段规划时，自动为事件添加期待标签
from src.managers.ExpectationManager import EventDrivenExpectationManager

expectation_manager = EventDrivenExpectationManager()

# 2. 为事件自动匹配合适的期待类型
event = {
    "id": "alchemy_competition_001",
    "name": "炼丹比试",
    "main_goal": "赢得宗门炼丹比赛",
    "chapter_range": "20-28"
}

exp_type = auto_bind_expectation_to_event(event)
# 返回: ExpectationType.ALCHEMY_CRAFTING

# 3. 添加期待标签
exp_id = expectation_manager.tag_event_with_expectation(
    event_id=event["id"],
    expectation_type=exp_type,
    planting_chapter=20,
    description="赢得炼丹比赛，证明主角实力",
    target_chapter=28,
    flexible_range={
        "min_chapters": 6,
        "max_chapters": 10,
        "optimal_chapters": 8
    }
)

# 4. 生成章节时，自动检查期待约束
constraints = expectation_manager.pre_generation_check(
    chapter_num=28,
    event_context={"active_events": [event]}
)

# 5. 生成后验证期待是否被满足
validation_result = expectation_manager.post_generation_validate(
    chapter_num=28,
    content_analysis={"content": chapter_content},
    released_expectation_ids=[exp_id]
)
```

---

## 六、总结

### 改进要点

1. **类型扩充**: 从6种扩充到20种，覆盖主流网文套路
2. **事件驱动**: 期待与事件深度绑定，根据事件进度灵活判断释放时机
3. **深度集成**: 真正集成到ContentGenerator的章节生成流程
4. **质量监控**: 密度监控和自动建议，确保期待感质量

### 核心优势

- ✅ 覆盖更全面的网文套路
- ✅ 避免固定章节要求的僵化
- ✅ 与叙事节奏自然融合
- ✅ 自动化程度更高
- ✅ 质量可控可衡量

这套系统真正让期待感管理落地，确保每章都能牵动读者的追读动力！
