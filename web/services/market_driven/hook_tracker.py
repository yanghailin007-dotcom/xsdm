"""
剧情钩子追踪器 (HookTracker)

解决"挖坑不填"、伏笔丢失、剧情线断裂的通用问题

核心功能：
1. 追踪所有埋下的钩子（章尾悬念、系统提示、伏笔、角色约定）
2. 强制要求钩子回收（在N章内必须解决或延续）
3. 生成钩子回收提醒提示词
4. 追踪多线并行的剧情线索

适用题材：所有（修仙/都市/科幻/国运等）
钩子类型：悬念型、信息型、道具型、关系型、系统型
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    """钩子定义"""
    hook_id: str  # 唯一ID
    chapter: int  # 埋钩子的章节
    content: str  # 钩子内容
    hook_type: str  # 悬念型/震惊型/期待型/爽点型
    priority: int = 5  # 优先级 1-10
    expected_resolve_chapter: int = 0  # 预期解决章节
    actual_resolve_chapter: int = 0  # 实际解决章节
    status: str = "pending"  # pending/resolved/ongoing/abandoned
    related_plotlines: List[str] = field(default_factory=list)  # 相关剧情线
    notes: str = ""  # 备注


@dataclass
class Plotline:
    """剧情线定义"""
    name: str
    introduced_chapter: int
    status: str = "active"  # active/paused/resolved
    priority: int = 5
    hooks: List[str] = field(default_factory=list)  # 关联的钩子ID
    last_mentioned: int = 0
    description: str = ""


class HookTracker:
    """
    通用钩子追踪器
    
    解决的核心问题：
    1. 章尾钩子/悬念在后续章节被遗忘
    2. 系统提示/伏笔被忽略
    3. 多线并行时某些剧情线断裂
    
    使用示例：
        tracker = HookTracker(project_path)
        
        # 记录钩子（通用，不限于特定题材）
        tracker.add_hook(
            chapter=6,
            content="神秘老者说：'我们还会再见'",
            hook_type="悬念型",
            priority=8,
            expected_resolve_chapter=15,
            related_plotlines=["神秘势力线"]
        )
        
        # 生成回收提醒
        reminder = tracker.build_resolve_reminder(15)
        # 输出：悬念型钩子已悬挂9章，需要回收或延续
    """
    
    # 通用钩子回收期限配置（按类型）
    HOOK_RESOLVE_DEADLINES = {
        # 情绪/悬念类
        "cliffhanger": 3,      # 章尾悬念：3章内必须推进
        "mystery": 5,          # 谜团：5章内必须有线索
        "promise": 5,          # 角色约定：5章内兑现
        "threat": 4,           # 威胁/警告：4章内显现
        
        # 系统/信息类  
        "system_warning": 3,   # 系统警告：3章内体现
        "prophecy": 8,         # 预言：8章内应验
        "secret": 10,          # 秘密：10章内揭露
        
        # 物品/资源类
        "item": 10,            # 道具/物品：10章内使用
        "resource": 6,         # 资源/奖励：6章内发挥作用
        
        # 关系/势力类
        "character": 7,        # 角色伏笔：7章内再登场
        "faction": 8,          # 势力伏笔：8章内展现
        
        # 通用
        "general": 5,          # 通用钩子：5章默认期限
    }
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.hooks_file = self.project_path / ".hooks.json"
        self.plotlines_file = self.project_path / ".plotlines.json"
        
        self.hooks: Dict[str, Hook] = {}
        self.plotlines: Dict[str, Plotline] = {}
        
        self._load_state()
        logger.info(f"[HookTracker] 初始化完成 | 钩子数: {len(self.hooks)}")
    
    def _load_state(self):
        """加载状态"""
        # 加载钩子
        if self.hooks_file.exists():
            try:
                with open(self.hooks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for hook_id, hook_data in data.items():
                    self.hooks[hook_id] = Hook(**hook_data)
                logger.info(f"[HookTracker] 已加载 {len(self.hooks)} 个钩子")
            except Exception as e:
                logger.error(f"[HookTracker] 加载钩子失败: {e}")
        
        # 加载剧情线
        if self.plotlines_file.exists():
            try:
                with open(self.plotlines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for name, plot_data in data.items():
                    self.plotlines[name] = Plotline(**plot_data)
            except Exception as e:
                logger.error(f"[HookTracker] 加载剧情线失败: {e}")
    
    def save_state(self):
        """保存状态"""
        try:
            # 保存钩子
            hooks_data = {k: asdict(v) for k, v in self.hooks.items()}
            with open(self.hooks_file, 'w', encoding='utf-8') as f:
                json.dump(hooks_data, f, ensure_ascii=False, indent=2)
            
            # 保存剧情线
            plotlines_data = {k: asdict(v) for k, v in self.plotlines.items()}
            with open(self.plotlines_file, 'w', encoding='utf-8') as f:
                json.dump(plotlines_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[HookTracker] 状态已保存")
        except Exception as e:
            logger.error(f"[HookTracker] 保存失败: {e}")
    
    def add_hook(self, chapter: int, content: str, hook_type: str = "悬念型",
                 priority: int = 5, expected_resolve_chapter: int = 0,
                 related_plotlines: List[str] = None) -> str:
        """
        添加新钩子
        
        Args:
            chapter: 埋钩子的章节
            content: 钩子内容（建议50字以内）
            hook_type: 钩子类型
            priority: 优先级 1-10
            expected_resolve_chapter: 预期解决章节（0表示自动计算）
            related_plotlines: 关联的剧情线名称
        """
        hook_id = f"hook_{chapter:03d}_{datetime.now().strftime('%H%M%S')}"
        
        # 自动计算预期解决章节
        if expected_resolve_chapter == 0:
            deadline = self.HOOK_RESOLVE_DEADLINES.get(hook_type, 5)
            expected_resolve_chapter = chapter + deadline
        
        hook = Hook(
            hook_id=hook_id,
            chapter=chapter,
            content=content,
            hook_type=hook_type,
            priority=priority,
            expected_resolve_chapter=expected_resolve_chapter,
            related_plotlines=related_plotlines or []
        )
        
        self.hooks[hook_id] = hook
        
        # 关联到剧情线
        for plotline_name in (related_plotlines or []):
            if plotline_name not in self.plotlines:
                self.plotlines[plotline_name] = Plotline(
                    name=plotline_name,
                    introduced_chapter=chapter
                )
            self.plotlines[plotline_name].hooks.append(hook_id)
            self.plotlines[plotline_name].last_mentioned = chapter
        
        self.save_state()
        logger.info(f"[HookTracker] 新增钩子 #{chapter}: {content[:30]}...")
        return hook_id
    
    def resolve_hook(self, hook_id: str, chapter: int, resolution: str = ""):
        """标记钩子已解决"""
        if hook_id in self.hooks:
            hook = self.hooks[hook_id]
            hook.status = "resolved"
            hook.actual_resolve_chapter = chapter
            hook.notes = resolution
            self.save_state()
            logger.info(f"[HookTracker] 钩子已解决: {hook_id} (第{chapter}章)")
    
    def continue_hook(self, hook_id: str, chapter: int, new_content: str = ""):
        """延续钩子（未解决但推进）"""
        if hook_id in self.hooks:
            hook = self.hooks[hook_id]
            hook.status = "ongoing"
            # 延长预期解决时间
            hook.expected_resolve_chapter = chapter + self.HOOK_RESOLVE_DEADLINES.get(hook.hook_type, 5)
            if new_content:
                hook.content += f" -> {new_content}"
            
            # 更新相关剧情线
            for plotline_name in hook.related_plotlines:
                if plotline_name in self.plotlines:
                    self.plotlines[plotline_name].last_mentioned = chapter
            
            self.save_state()
            logger.info(f"[HookTracker] 钩子延续: {hook_id} -> 第{hook.expected_resolve_chapter}章")
    
    def get_pending_hooks(self, current_chapter: int) -> List[Hook]:
        """获取所有待解决的钩子"""
        return [h for h in self.hooks.values() 
                if h.status in ["pending", "ongoing"]]
    
    def get_overdue_hooks(self, current_chapter: int) -> List[Hook]:
        """获取已超期的钩子"""
        return [h for h in self.hooks.values()
                if h.status in ["pending", "ongoing"]
                and h.expected_resolve_chapter < current_chapter]
    
    def get_hooks_by_plotline(self, plotline_name: str) -> List[Hook]:
        """获取指定剧情线的所有钩子"""
        if plotline_name not in self.plotlines:
            return []
        plotline = self.plotlines[plotline_name]
        return [self.hooks[hid] for hid in plotline.hooks 
                if hid in self.hooks]
    
    def build_resolve_reminder(self, current_chapter: int) -> str:
        """
        构建钩子回收提醒提示词
        
        在生成新章节前调用，提醒AI需要回收哪些钩子
        """
        pending = self.get_pending_hooks(current_chapter)
        overdue = self.get_overdue_hooks(current_chapter)
        
        if not pending:
            return ""
        
        lines = ["\n## 【钩子回收提醒】⚠️\n"]
        
        # 超期钩子（必须处理）
        if overdue:
            lines.append("### 🔴 超期钩子（必须在本章处理）")
            for hook in sorted(overdue, key=lambda h: h.priority, reverse=True):
                overdue_chapters = current_chapter - hook.expected_resolve_chapter
                lines.append(f"""
- **{hook.hook_type}** | 第{hook.chapter}章埋下 | 已超期{overdue_chapters}章
  内容：{hook.content}
  **必须在本章回收或明确延续！**
""")
        
        # 即将到期钩子（建议处理）
        upcoming = [h for h in pending 
                   if h not in overdue 
                   and h.expected_resolve_chapter <= current_chapter + 2]
        if upcoming:
            lines.append("\n### 🟡 即将到期钩子（建议本章处理）")
            for hook in sorted(upcoming, key=lambda h: h.priority, reverse=True)[:3]:
                lines.append(f"""
- **{hook.hook_type}** | 第{hook.chapter}章埋下 | 预期第{hook.expected_resolve_chapter}章解决
  内容：{hook.content}
""")
        
        # 剧情线状态
        active_plotlines = [p for p in self.plotlines.values() 
                           if p.status == "active"]
        if active_plotlines:
            lines.append("\n### 📖 活跃剧情线")
            for plotline in active_plotlines:
                last_mentioned = plotline.last_mentioned
                chapters_since = current_chapter - last_mentioned
                if chapters_since > 3:
                    lines.append(f"- **{plotline.name}**: 已{chapters_since}章未提及，建议在本章穿插")
                else:
                    lines.append(f"- **{plotline.name}**: 上次提及第{last_mentioned}章")
        
        lines.append("\n**注意：** 如果本章不处理某钩子，请明确埋下新的线索延续它！")
        
        return "\n".join(lines)
    
    def build_chapter_hook_requirement(self, current_chapter: int) -> str:
        """
        构建本章钩子要求
        
        确保每章都有合适的结尾钩子
        """
        lines = ["\n## 【本章钩子要求】\n"]
        
        # 根据章节位置确定钩子类型
        if current_chapter % 3 == 0:
            hook_type = "震惊型"
            desc = "重大反转或揭露"
        elif current_chapter % 3 == 1:
            hook_type = "悬念型"
            desc = "新危机或疑问"
        else:
            hook_type = "期待型"
            desc = "即将发生的冲突"
        
        lines.append(f"**本章推荐钩子类型：{hook_type}**")
        lines.append(f"要求：{desc}")
        lines.append("\n**钩子标准：**")
        lines.append("1. 位置：最后50-100字")
        lines.append("2. 功能：让读者必须点击下一章")
        lines.append("3. 形式：新危机/新角色/新信息/倒计时")
        
        # 检查是否有超期钩子，如果有，建议用于章尾
        overdue = self.get_overdue_hooks(current_chapter)
        if overdue:
            lines.append(f"\n**建议：** 本章结尾可以使用这个超期钩子作为章尾悬念：")
            lines.append(f"  {overdue[0].content}")
        
        return "\n".join(lines)
    
    def analyze_chapter_for_hooks(self, chapter_num: int, content: str) -> List[str]:
        """
        分析章节内容，自动提取新钩子
        
        返回检测到的钩子ID列表
        """
        detected_hooks = []
        
        # 检测系统提示中的钩子
        import re
        
        # 匹配【警告】类型的系统提示
        warning_patterns = [
            r'【警告.*?】(.*?)(?:】|$)',
            r'【获得情报.*?:(.*?)】',
            r'距离.*?还剩.*?(\d+).*?(小时|天|章)',
        ]
        
        for pattern in warning_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                hook_content = match if isinstance(match, str) else match[0]
                hook_id = self.add_hook(
                    chapter=chapter_num,
                    content=hook_content.strip()[:100],
                    hook_type="系统提示",
                    priority=8
                )
                detected_hooks.append(hook_id)
        
        # 检测章尾钩子（最后100字）
        last_100 = content[-100:] if len(content) > 100 else content
        if any(kw in last_100 for kw in ["倒计时", "即将", "还有", "危机", "陷阱", "真相", "背叛"]):
            # 提取最后一句作为钩子
            sentences = last_100.split('。')
            if len(sentences) >= 2:
                hook_text = sentences[-2] + '。'
                if len(hook_text) > 10:
                    hook_id = self.add_hook(
                        chapter=chapter_num,
                        content=hook_text.strip()[:80],
                        hook_type="悬念型",
                        priority=7
                    )
                    detected_hooks.append(hook_id)
        
        if detected_hooks:
            logger.info(f"[HookTracker] 第{chapter_num}章检测到 {len(detected_hooks)} 个新钩子")
        
        return detected_hooks
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self.hooks)
        resolved = len([h for h in self.hooks.values() if h.status == "resolved"])
        pending = len([h for h in self.hooks.values() if h.status in ["pending", "ongoing"]])
        abandoned = len([h for h in self.hooks.values() if h.status == "abandoned"])
        
        return {
            "total_hooks": total,
            "resolved": resolved,
            "pending": pending,
            "abandoned": abandoned,
            "resolution_rate": resolved / total if total > 0 else 0,
            "active_plotlines": len([p for p in self.plotlines.values() if p.status == "active"]),
        }
