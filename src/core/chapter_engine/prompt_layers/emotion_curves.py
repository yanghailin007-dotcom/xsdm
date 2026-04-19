"""
情绪曲线模板 - 从V2提取为通用常量

对应爽文章节类型：
- 打脸章：压抑→冲突→反击→悬念
- 爆发章：蓄势→高潮→收尾
- 收获章：争夺→获得→震惊
- 危机章：安稳→危机→逃脱
- 铺垫章：平静→伏笔→引子

同时支持按"爽点单元角色"映射：
- setup (铺垫) → 铺垫章
- suppression (压抑) → 打脸章/危机章
- payoff (爽点爆发) → 爆发章/打脸章
- harvest (收获) → 收获章
"""

from typing import Dict, List, Any, Optional


# ==================== 情绪曲线模板 ====================

EMOTION_CURVE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "打脸章": {
        "curve": "虐(4)→急(7)→爽(9)→悬(7)",
        "description": "先让主角受委屈/被轻视，再反转打脸，最后留悬念",
        "breakdown": [
            {"position": "0-20%", "emotion": "虐", "intensity": 4, "technique": "铺垫压抑场景"},
            {"position": "20-50%", "emotion": "急", "intensity": 7, "technique": "冲突升级"},
            {"position": "50-80%", "emotion": "爽", "intensity": 9, "technique": "主角反击高潮"},
            {"position": "80-100%", "emotion": "悬", "intensity": 7, "technique": "结尾留钩子"},
        ]
    },
    "爆发章": {
        "curve": "蓄(3)→爆(10)→收(5)",
        "description": "积蓄力量后全力释放，展示结果",
        "breakdown": [
            {"position": "0-30%", "emotion": "蓄势", "intensity": 3, "technique": "铺垫积累"},
            {"position": "30-70%", "emotion": "爆发", "intensity": 10, "technique": "全力释放高潮"},
            {"position": "70-100%", "emotion": "收尾", "intensity": 5, "technique": "结果展示+悬念"},
        ]
    },
    "收获章": {
        "curve": "争(6)→得(8)→惊(7)",
        "description": "多方竞争后主角获得，引发众人震惊",
        "breakdown": [
            {"position": "0-30%", "emotion": "争夺", "intensity": 6, "technique": "多方竞争"},
            {"position": "30-70%", "emotion": "获得", "intensity": 8, "technique": "主角得到宝物/认可"},
            {"position": "70-100%", "emotion": "震惊", "intensity": 7, "technique": "众人反应"},
        ]
    },
    "危机章": {
        "curve": "安(3)→危(8)→逃(6)",
        "description": "平静开局后突发危机，惊险脱身",
        "breakdown": [
            {"position": "0-20%", "emotion": "安稳", "intensity": 3, "technique": "平静开局"},
            {"position": "20-60%", "emotion": "危机", "intensity": 8, "technique": "突发危机"},
            {"position": "60-100%", "emotion": "逃脱", "intensity": 6, "technique": "惊险脱身"},
        ]
    },
    "铺垫章": {
        "curve": "平(4)→伏(5)→引(6)",
        "description": "日常描写中埋设伏笔，引出下文",
        "breakdown": [
            {"position": "0-40%", "emotion": "平静", "intensity": 4, "technique": "日常描写"},
            {"position": "40-80%", "emotion": "伏笔", "intensity": 5, "technique": "埋设线索"},
            {"position": "80-100%", "emotion": "引子", "intensity": 6, "technique": "引出下文"},
        ]
    },
}


# ==================== 爽点单元角色映射 ====================

CHAPTER_ROLES: Dict[str, Dict[str, Any]] = {
    "setup": {
        "name": "铺垫",
        "description": "为爽点做铺垫，引入冲突或问题",
        "default_curve": "铺垫章",
        "chapter_type_hint": "铺垫章",
    },
    "suppression": {
        "name": "压抑",
        "description": "强化矛盾，让主角/读者感到憋屈",
        "default_curve": "打脸章",
        "chapter_type_hint": "打脸章",
    },
    "payoff": {
        "name": "爆发",
        "description": "爽点释放，主角反击或展现实力",
        "default_curve": "爆发章",
        "chapter_type_hint": "爆发章",
    },
    "harvest": {
        "name": "收获",
        "description": "获得宝物/认可/成长，引发震惊",
        "default_curve": "收获章",
        "chapter_type_hint": "收获章",
    },
    "crisis": {
        "name": "危机",
        "description": "突发危机，制造紧张感",
        "default_curve": "危机章",
        "chapter_type_hint": "危机章",
    },
}


# ==================== 工具函数 ====================

def get_emotion_curve_text(chapter_type: str) -> str:
    """
    获取指定章节类型的情绪曲线文本（prompt格式）
    
    Args:
        chapter_type: 章节类型（打脸章/爆发章/收获章/危机章/铺垫章）
    
    Returns:
        格式化后的情绪曲线文本
    """
    data = EMOTION_CURVE_TEMPLATES.get(chapter_type, EMOTION_CURVE_TEMPLATES["铺垫章"])
    
    lines = ["### 情绪节奏规划"]
    lines.append(f"章节类型: {chapter_type}")
    lines.append(f"曲线: {data['curve']}")
    lines.append(f"设计思路: {data['description']}")
    lines.append("")
    lines.append("情绪点位:")
    for point in data['breakdown']:
        lines.append(
            f"  - {point['position']}: {point['emotion']} (强度{point['intensity']}/10) — {point['technique']}"
        )
    
    return "\n".join(lines)


def get_emotion_curve_for_role(role: str) -> str:
    """
    根据爽点单元角色获取情绪曲线
    
    Args:
        role: 角色（setup/suppression/payoff/harvest/crisis）
    
    Returns:
        情绪曲线文本
    """
    role_info = CHAPTER_ROLES.get(role, CHAPTER_ROLES["setup"])
    curve_type = role_info["default_curve"]
    return get_emotion_curve_text(curve_type)


def infer_chapter_role(
    chapter_index_in_batch: int,
    batch_size: int,
    stage_context: Optional[Dict] = None
) -> str:
    """
    根据章节在批次中的位置推断角色
    
    标准4章爽点闭环：
    - 第1章 (index=0): setup (铺垫)
    - 第2章 (index=1): suppression (压抑)
    - 第3章 (index=2): payoff (爆发)
    - 第4章 (index=3): harvest (收获)
    
    Args:
        chapter_index_in_batch: 章节在批次中的索引（0-based）
        batch_size: 批次大小
        stage_context: 大阶段上下文（可选，用于更精细推断）
    
    Returns:
        角色名称（setup/suppression/payoff/harvest/crisis）
    """
    # 标准映射：按批次位置推断
    if batch_size >= 4:
        mapping = {
            0: "setup",
            1: "suppression",
            2: "payoff",
            3: "harvest",
        }
        return mapping.get(chapter_index_in_batch % 4, "setup")
    elif batch_size == 3:
        mapping = {0: "setup", 1: "suppression", 2: "payoff"}
        return mapping.get(chapter_index_in_batch, "setup")
    elif batch_size == 2:
        mapping = {0: "setup", 1: "payoff"}
        return mapping.get(chapter_index_in_batch, "setup")
    else:
        return "setup"


def get_chapter_type_from_role(role: str) -> str:
    """根据角色获取章节类型"""
    role_info = CHAPTER_ROLES.get(role, CHAPTER_ROLES["setup"])
    return role_info.get("chapter_type_hint", "铺垫章")


def build_custom_emotion_curve(config: Dict[str, Any]) -> str:
    """
    构建自定义情绪曲线文本
    
    Args:
        config: {
            "emotion": str,      # 核心情绪
            "intensity": int,    # 强度 1-10
            "emotion_type": str, # 情绪类型
            "type": str,         # 章节类型
            "breakdown": [       # 可选，自定义点位
                {"position": "0-30%", "emotion": "...", "intensity": 5, "technique": "..."}
            ]
        }
    """
    lines = ["### 情绪节奏规划"]
    
    emotion = config.get("emotion")
    intensity = config.get("intensity")
    emotion_type = config.get("emotion_type")
    chapter_type = config.get("type", "自定义")
    
    if emotion or intensity is not None:
        lines.append(f"核心情绪: {emotion or '待定'} (强度: {intensity if intensity is not None else 5}/10)")
    if emotion_type:
        lines.append(f"情绪类型: {emotion_type}")
    lines.append(f"章节类型: {chapter_type}")
    
    breakdown = config.get("breakdown")
    if breakdown:
        lines.append("")
        lines.append("情绪点位:")
        for point in breakdown:
            pos = point.get("position", "")
            emo = point.get("emotion", "")
            intens = point.get("intensity", 5)
            tech = point.get("technique", "")
            lines.append(f"  - {pos}: {emo} (强度{intens}/10) — {tech}")
    
    return "\n".join(lines)
