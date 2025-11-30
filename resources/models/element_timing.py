# models/element_timing.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from pydantic import BaseModel, Field
from typing import List, Optional
from src.utils.logger import get_logger

class CharacterTimingInfo(BaseModel):
    name: str
    type: str
    importance: str
    first_appearance_chapter: int
    foreshadowing_chapter: Optional[int] = None
    reasoning: Optional[str] = ""

class FactionTimingInfo(BaseModel):
    name: str
    importance: str
    first_appearance_chapter: int
    introduction_method: Optional[str] = ""

class AbilityTimingInfo(BaseModel):
    name: str
    first_appearance_chapter: int
    acquisition_method: Optional[str] = ""

# ... 你可以为 item 和 concept 也创建类似的Info模型

class ElementTimingPlan(BaseModel):
    character_timing: List[CharacterTimingInfo] = Field(default_factory=list)
    faction_timing: List[FactionTimingInfo] = Field(default_factory=list)
    ability_timing: List[AbilityTimingInfo] = Field(default_factory=list)
    # 假设 item_timing 和 concept_timing 暂时保持为字典列表
    item_timing: List[dict] = Field(default_factory=list)
    concept_timing: List[dict] = Field(default_factory=list)
