from typing import Dict, List


class FactionDevelopmentManager:
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.faction_relationships = {}
    
    def initialize_faction_system(self, worldview: Dict) -> Dict:
        """初始化势力系统"""
        factions = worldview.get("major_factions", [])
        faction_system = {
            "factions": {},
            "relationship_network": {},
            "conflict_timeline": [],
            "power_balance": {}
        }
        
        for faction in factions:
            faction_system["factions"][faction["name"]] = {
                "leader": faction.get("leader", ""),
                "territory": faction.get("territory", []),
                "resources": faction.get("resources", {}),
                "military_power": faction.get("power_level", 0),
                "goals": faction.get("goals", []),
                "allies": [],
                "enemies": [],
                "development_arc": self._generate_faction_development_arc(faction)
            }
        
        return faction_system
    
    def _generate_faction_development_arc(self, faction: Dict) -> List[Dict]:
        """生成势力发展轨迹"""
        development_arc = [
            {
                "stage": "初期",
                "status": "稳定发展",
                "key_events": ["确立地位", "招募成员"],
                "power_change": "+0%"
            },
            {
                "stage": "发展期", 
                "status": "快速扩张",
                "key_events": ["领土扩张", "技术突破"],
                "power_change": "+30%"
            },
            {
                "stage": "冲突期",
                "status": "激烈竞争", 
                "key_events": ["资源争夺", "外交危机"],
                "power_change": "-10%"
            },
            {
                "stage": "稳定期",
                "status": "格局定型",
                "key_events": ["签订条约", "内部改革"],
                "power_change": "+15%"
            }
        ]
        return development_arc