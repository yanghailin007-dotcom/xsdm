# -*- coding: utf-8 -*-
"""
Core Setting Bible Generator - 核心设定圣经生成器

将 phase_one_products 和 project_info 中的分散 JSON 数据
汇总为一份人可读、AI 可用、UI 可改的 layer_1_4_core_settings.md
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CoreSettingBibleGenerator:
    """核心设定圣经生成器"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.products_path = self.project_path / "phase_one_products"

    def _load_json(self, filename: str, default: Any = None) -> Any:
        path = self.products_path / filename
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[BibleGenerator] 加载 {filename} 失败: {e}")
            return default

    def _should_regenerate(self, output_path: Path) -> bool:
        """检查是否需要重新生成：若 MD 不存在，或任一源 JSON 比 MD 更新，则需要"""
        if not output_path.exists():
            return True
        md_mtime = output_path.stat().st_mtime
        source_files = [
            self.project_path / "project_info.json",
            self.products_path / "角色设计.json",
            self.products_path / "金手指设计.json",
            self.products_path / "世界观设定.json",
            self.products_path / "写作风格指南.json",
            self.products_path / "完整方案.json",
            self.products_path / "阶段目标.json",
            self.products_path / "情绪曲线.json",
        ]
        for sf in source_files:
            if sf.exists() and sf.stat().st_mtime > md_mtime:
                logger.info(f"[BibleGenerator] 源文件 {sf.name} 已更新，需要重新生成圣经")
                return True
        return False

    def generate(self, force: bool = False) -> Path:
        """生成 layer_1_4_core_settings.md，返回文件路径"""
        output_path = self.project_path / "layer_1_4_core_settings.md"
        if not force and not self._should_regenerate(output_path):
            logger.info(f"[BibleGenerator] 核心设定圣经已是最新，跳过生成: {output_path}")
            return output_path

        # 加载所有数据源
        info = self._load_json("../project_info.json", {})
        char_design = self._load_json("角色设计.json", {})
        gf = self._load_json("金手指设计.json", {})
        world = self._load_json("世界观设定.json", {})
        style = self._load_json("写作风格指南.json", {})
        plan = self._load_json("完整方案.json", {})

        # 提取数据
        protagonist = char_design.get("protagonist", {})
        if not isinstance(protagonist, dict):
            protagonist = {}
        allies = char_design.get("core_allies", [])
        if not isinstance(allies, list):
            allies = []
        antagonists = char_design.get("main_antagonists", {})
        # 🔥 兼容：AI 有时会返回 list 而不是 dict
        if isinstance(antagonists, list):
            # 尝试从 list 中按 stage 提取转换为 dict
            tmp = {"early": None, "mid": None, "late": None}
            for item in antagonists:
                if isinstance(item, dict):
                    stage = item.get("stage", "")
                    if stage in tmp:
                        tmp[stage] = item
                    elif not tmp["early"]:
                        tmp["early"] = item
                    elif not tmp["mid"]:
                        tmp["mid"] = item
                    elif not tmp["late"]:
                        tmp["late"] = item
            antagonists = tmp
        elif not isinstance(antagonists, dict):
            antagonists = {}

        gf_name = gf.get("name", "")
        gf_initial = gf.get("initial_ability", gf.get("initial_reward", ""))
        gf_growth = gf.get("growth_rule", "")
        gf_limits = gf.get("limitations", "")

        world_overview = world.get("world_overview", {})
        if not isinstance(world_overview, dict):
            world_overview = {}
        power_system = world.get("power_system", {})
        if not isinstance(power_system, dict):
            power_system = {}
        factions = world.get("factions", [])
        if not isinstance(factions, list):
            factions = []
        world_rules = world.get("world_rules", [])
        if not isinstance(world_rules, list):
            world_rules = []
        key_locations = world.get("key_locations", [])
        if not isinstance(key_locations, list):
            key_locations = []

        # 阶段目标 / 情绪曲线优先从 project_info 的 mode_specific 取
        mode_info = info.get("generation_metadata", {}).get("mode_specific", {}).get("info", {})
        stage_goals = mode_info.get("stage_goals", [])
        emotion_curve = mode_info.get("emotion_curve", [])

        # 如果 project_info 里没有，fallback 到 plan 或独立产物
        if not stage_goals:
            stage_goals = self._load_json("阶段目标.json", [])
        if not emotion_curve:
            emotion_curve = self._load_json("情绪曲线.json", [])

        # 选择最佳简介
        core_selling_points = plan.get("core_selling_points", [])
        if core_selling_points and core_selling_points[0].get("point"):
            best_synopsis = core_selling_points[0]["point"].strip()
        else:
            best_synopsis = plan.get("synopsis", "").strip() or info.get("novel_synopsis", "").strip()

        lines: List[str] = []

        # Header
        lines.append("# Layer 1-4 核心设定圣经")
        lines.append(f"> **书名**：《{info.get('novel_title', plan.get('title', '未命名'))}》")
        lines.append(f"> **版本**：v1.0（生成于 {datetime.now().strftime('%Y-%m-%d')}）")
        lines.append("> **⚠️ 警告**：所有生成/修复/复盘环节必须严格遵循以下设定。人工修改后请更新版本号。")
        lines.append("")

        # 简介
        lines.append("---")
        lines.append("")
        lines.append("## 📖 书籍简介（核心吸引力）")
        lines.append("")
        lines.append(best_synopsis)
        lines.append("")
        one_liner = plan.get("core_selling_point", "")
        if one_liner:
            lines.append(f"**一句话卖点**：{one_liner}")
            lines.append("")

        # Layer 1
        lines.append("---")
        lines.append("")
        lines.append("## Layer 1: 核心设定（全书不可变更）")
        lines.append("")

        lines.append("### 1.1 主角档案")
        lines.append(f"- **姓名**：{protagonist.get('name', '未设定')}（绝对禁止改名）")
        lines.append(f"- **年龄**：{protagonist.get('age', '未设定')}")
        lines.append(f"- **身份**：{protagonist.get('identity', '未设定')}")
        traits = protagonist.get("traits", [])
        lines.append(f"- **核心性格**：{'、'.join(traits) if traits else '未设定'}")
        lines.append(f"- **性格详述**：{protagonist.get('personality_description', '未设定')}")
        lines.append(f"- **背景**：{protagonist.get('background', '未设定')}")
        lines.append(f"- **动机**：{protagonist.get('motivation', '未设定')}")
        lines.append(f"- **成长弧**：{protagonist.get('growth_arc', '未设定')}")
        lines.append(f"- **独特标签**：{protagonist.get('unique_label', '未设定')}")
        lines.append(f"- **口头禅**：\"{protagonist.get('catchphrase', '未设定')}\"")
        lines.append("")
        lines.append("**🚫 主角 OOC 红线（严禁违反）**：")
        for item in protagonist.get("forbidden", []):
            lines.append(f"- {item}")
        lines.append("")

        if allies:
            lines.append("### 1.2 核心盟友")
            for ally in allies:
                at = ally.get("traits", [])
                lines.append(
                    f"- **{ally.get('name')}**：{ally.get('identity')}"
                    f"（{'、'.join(at) if at else '无'}）"
                )
            lines.append("")

        lines.append("### 1.3 主要反派")
        for key, label in [("early", "前期反派"), ("mid", "中期反派"), ("late", "后期反派")]:
            a = antagonists.get(key)
            if a:
                at = a.get("traits", [])
                lines.append(
                    f"- **{label} - {a.get('name')}**：{a.get('identity')}"
                    f"（{'、'.join(at) if at else '无'}）"
                )
        lines.append("")

        lines.append("### 1.4 金手指设定")
        lines.append(f"- **名称**：{gf_name or '未设定'}")
        lines.append(f"- **初始能力**：{gf_initial or '未设定'}")
        lines.append(f"- **升级规则**：{gf_growth or '未设定'}")
        lines.append(f"- **限制与代价**：{gf_limits or '未设定'}")
        if gf.get("growth_curve"):
            lines.append("- **成长阶段**：")
            for k, v in gf["growth_curve"].items():
                lines.append(f"  - {k}：{v}")
        lines.append("")

        lines.append("### 1.5 世界观与力量体系")
        lines.append(f"- **时代背景**：{world_overview.get('era', '未设定')}")
        lines.append(f"- **世界背景**：{world_overview.get('background', '未设定')}")
        lines.append(f"- **核心冲突**：{world_overview.get('main_conflict', '未设定')}")
        lines.append("")
        ps_name = power_system.get("name", "未设定")
        lines.append(f"- **力量体系**：{ps_name}")
        for lvl in power_system.get("levels", []):
            lines.append(f"  - {lvl}")
        lines.append("")
        mech = power_system.get("mechanics", {})
        if mech.get("core_rules"):
            lines.append("**核心规则**：")
            for rule in mech["core_rules"]:
                lines.append(f"- {rule}")
            lines.append("")
        if mech.get("limitations"):
            lines.append("**世界限制**：")
            for rule in mech["limitations"]:
                lines.append(f"- {rule}")
            lines.append("")

        if factions:
            lines.append("### 1.6 主要势力")
            for fac in factions:
                if isinstance(fac, dict):
                    lines.append(f"- **{fac.get('name', '未命名')}**（{fac.get('type', 'unknown')}）：{fac.get('description', '')}")
            lines.append("")

        if key_locations:
            lines.append("### 1.7 关键地点")
            for loc in key_locations:
                if isinstance(loc, dict):
                    lines.append(f"- **{loc.get('name', '未命名')}**（{loc.get('type', 'unknown')}）：{loc.get('description', '')}")
            lines.append("")

        if world_rules:
            lines.append("### 1.8 世界运行法则")
            for rule in world_rules:
                lines.append(f"- {rule}")
            lines.append("")

        # Layer 2
        lines.append("---")
        lines.append("")
        lines.append("## Layer 2: 战术规划索引")
        lines.append("> 注意：Layer 2 按阶段动态更新，以下为当前有效阶段规划。")
        lines.append("")
        if stage_goals:
            for goal in stage_goals:
                gid = goal.get("goal_id", "")
                gdesc = goal.get("description", "")
                lines.append(f"### {gid}：{gdesc}")
                lines.append(f"- **预计章节**：{goal.get('expected_chapters', '')}")
                lines.append("- **关键交付物**：")
                for d in goal.get("key_deliverables", []):
                    lines.append(f"  - {d}")
                lines.append(f"- **成功标准**：{goal.get('success_criteria', '')}")
                lines.append("")
        else:
            lines.append("（暂无阶段目标数据）")
            lines.append("")

        if emotion_curve:
            lines.append("### 情绪曲线规划")
            for ec in emotion_curve:
                lines.append(
                    f"- **{ec.get('chapters', '')}**：{ec.get('cycle', '')} —— {ec.get('description', '')}"
                )
            lines.append("")

        lines.append("- **当前战术规划文件**：`tactical_plan_1.json`（第1-30章阶段）")
        lines.append("")

        # Layer 3
        lines.append("---")
        lines.append("")
        lines.append("## Layer 3: 题材技法与禁区")
        genre = info.get("genre", plan.get("genre", "unknown"))
        lines.append(f"（题材标识：{genre}）")
        lines.append("")
        lines.append("### 3.1 必须出现的元素")
        lines.append("- [ ] 消费返利/投资收益时的**具体金额计算**（数字必须精确，这是爽点核心）")
        lines.append("- [ ] 股市操作前的**情报倒计时紧张感**（时间限制制造压迫）")
        lines.append("- [ ] 对反派/前女友的**打脸回旋镖**（当初看不起，现在高攀不起）")
        lines.append("- [ ] 旁人反应的**层层递进**（怀疑 → 震惊 → 恐惧 → 狂热）")
        lines.append("- [ ] 主角在金融博弈中展现的**近乎冷酷的冷静理智**")
        lines.append("")
        lines.append("### 3.2 禁用元素（🚫 严禁出现）")
        lines.append("- 玄幻修仙、灵气复苏、因果轮回")
        lines.append("- 系统直接给现金（必须通过投资/消费返利获得）")
        lines.append('- 主角突然获得格斗/异能/超自然力量（"神级格斗精通"仅限前期有限使用，不得喧宾夺主）')
        lines.append("- 政府/军方无理由为主角保驾护航")
        lines.append("- 后宫收女超过3人且分散主线注意力")
        lines.append("- 圣母心肠、以德报怨、对反派心软")
        lines.append("")
        lines.append("### 3.3 题材特定规则")
        lines.append('- 消费场景：必须写"返利到账"的具体数字和主角的情绪反馈')
        lines.append("- 金融场景：必须出现具体股票代码/公司名称、涨跌幅度、资金量级")
        lines.append("- 打脸场景：必须先写反派嘲讽，再写主角用事实/资金碾压，最后写旁观者反应")
        lines.append("")

        # Layer 4
        lines.append("---")
        lines.append("")
        lines.append("## Layer 4: 文风技法")
        lines.append("")
        lines.append("### 4.1 叙事风格")
        lines.append(f"- {style.get('narrative_style', '第一人称内心独白为主，对话简洁有力')}")
        lines.append(f"- {style.get('sentence_structure', '短句为主，节奏快，每章结尾留钩子')}")
        lines.append(f"- {style.get('vocabulary_preference', '口语化表达，避免过于书面的描述')}")
        lines.append(f"- {style.get('emotional_expression', '通过动作和对话展现情感，减少心理描写')}")
        lines.append("")
        lines.append("### 4.2 节奏要求")
        lines.append("- 开篇快速入戏，前3章必须有强冲突")
        lines.append('- 每章必须包含至少一个"情绪爆点"')
        lines.append("- 对话占比 ≥ 40%")
        lines.append("- 单章字数 **2000-2500 字**")
        lines.append("- 每章结尾必须留钩子（悬念/期待）")
        lines.append("- 禁止大段环境描写和无关心理独白")
        lines.append("")
        lines.append("### 4.3 段落格式硬性要求")
        lines.append("- 段落之间**必须保留空行/换行**")
        lines.append("- 对话必须单独成段")
        lines.append("- **禁止**合并成一段无换行的大文本")
        lines.append("- 标题格式：`---标题---\\n章节标题\\n\\n---正文---\\n正文内容`")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("*本文件为 AI 生成与人工修复的唯一真相源（Single Source of Truth）。*")

        md_content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"[BibleGenerator] 核心设定圣经已生成: {output_path} ({len(md_content)} 字符)")
        return output_path
