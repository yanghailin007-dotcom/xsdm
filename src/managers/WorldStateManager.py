"""世界状态管理器类 - 专注世界状态和角色发展管理"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import re
import json
import os
from typing import List, Dict, Optional, Tuple, Callable
from datetime import datetime
import uuid
import time
from src.utils.logger import get_logger
from src.config.path_config import path_config

class WorldStateManager:
    def __init__(self, storage_path: Optional[str] = None, novel_title: Optional[str] = None):
        """
        初始化世界状态管理器
        
        Args:
            storage_path: 存储路径（已弃用，保留用于向后兼容）
            novel_title: 小说标题，用于获取统一的项目路径
        """
        # 如果提供了小说标题，使用统一的路径配置系统
        if novel_title:
            self.novel_title = novel_title
            paths = path_config.get_project_paths(novel_title)
            self.storage_path = os.path.abspath(paths["quality_reports_dir"])
        elif storage_path:
            # 向后兼容：使用提供的存储路径
            self.storage_path = os.path.normpath(storage_path)
            self.novel_title = None
        else:
            # 默认使用新路径配置系统的基础目录
            self.storage_path = os.path.abspath(path_config.base_dir / "quality_reports")
            self.novel_title = None
        
        # 初始化日志系统
        self.logger = get_logger("WorldStateManager")
        self.logger.info(f"🌐 世界状态管理器初始化:")
        self.logger.info(f"   存储路径: {self.storage_path}")
        self.logger.info(f"   小说标题: {self.novel_title or '未指定'}")
        self.logger.info(f"   当前工作目录: {os.getcwd()}")
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        # 角色发展模板
        self.character_development_templates = {
            "core_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active", 
                "role_type": "主角/重要配角/次要配角",
                "importance": "major",
                "first_appearance_chapter": 0,  # 首次出场章节 - 系统维护
                "last_updated_chapter": 0,      # 最后更新章节 - 系统维护
                "total_appearances": 1,         # 总出场次数 - 系统维护
                # ▼▼▼ 添加下面这个字段 ▼▼▼
                "attributes": {
                    "status": "active",
                    "location": "未知",
                    "title": "",
                    "occupation": "", 
                    "faction": "",
                    "cultivation_level": "",
                    "money": 0
                },
                # ▲▲▲ 添加结束 ▲▲▲
                # 性格特征 - 会被更新
                "personality_traits": {
                    "core_traits": [],  # 核心特质 - 会被更新
                    "contradictions": "",  # 性格矛盾点 - 可能被更新
                    "behavior_patterns": "",  # 行为模式 - 可能被更新
                    "speech_style": ""  # 语言风格 - 可能被更新
                },
                # 背景故事 - 会被更新
                "background_story": {
                    "basic_info": "",  # 基本信息 - 会被更新
                    "key_experiences": [],  # 关键经历 - 会被更新
                    "motivations": "",  # 动机和追求 - 可能被更新
                },
                # 名场面 - 会被更新
                "iconic_scenes": [],  # 改为空数组，实际数据会动态添加
                # 关系网络 - 会被更新
                "relationship_network": {
                    "allies": [],  # 盟友 - 会被更新
                    "rivals": [],  # 对手 - 会被更新
                    "complex_relationships": []  # 复杂关系 - 可能被更新
                },
                # 发展里程碑 - 会被更新
                "development_milestones": [],  # 改为空数组，实际数据会动态添加
            },
            "minor_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active",
                "role_type": "次要配角/路人角色", 
                "importance": "minor",  # 次要角色标识
                "first_appearance_chapter": 0,
                "last_updated_chapter": 0,
                "total_appearances": 1,
                # 基本信息 - 可能被更新
                "basic_description": "",  # 角色基本描述
                "purpose_in_story": ""  # 在故事中的用途
            },
            "unnamed_character": {
                # 基础信息 - 会被系统维护
                "name": "",
                "status": "active",
                "role_type": "路人/群众",
                "importance": "unnamed",  # 未命名角色标识
                "first_appearance_chapter": 0,
                "last_updated_chapter": 0, 
                "total_appearances": 1,
                # 场景信息 - 可能被更新
                "appearance_context": ""  # 出现场景描述
            }
        }
        # 角色重要性判断规则
        self.character_importance_rules = {
            "major_character_indicators": [
                "主角", "主要角色", "重要角色", "主人公", "主角团",
                "有名字且在多个章节出现",
                "有详细背景故事", 
                "有性格描写和发展轨迹"
            ],
            "minor_character_indicators": [
                "配角", "次要角色", "路人", "群众", "士兵", "村民",
                "只在单一章节出现",
                "没有名字或使用通用称谓",
                "没有性格描写"
            ],
            "unnamed_character_patterns": [
                r"路人[甲乙丙丁]?", r"士兵[一二三四]?", r"村民[ABCD]?",
                r"老者", r"少年", r"女子", r"男子", r"官员", r"侍卫",
                r"店小二", r"掌柜", r"大夫", r"书生"
            ]
        }
        # ⭐️ 新增：角色心境档案模板
        self.character_mindset_template = {
            "character_name": "",
            "core_belief": "string (角色的核心世界观或信念，例如：'实力才是一切' 或 '善良终有回报')",
            "core_desire": "string (角色的根本欲望，例如：'保护家人' 或 '探寻父母死亡的真相')",
            "core_fear": "string (角色最深的恐惧，例如：'再次变得无能为力' 或 '失去所有亲人')",
            "internal_conflict": "string (内心的主要矛盾，是信念、欲望和恐惧的冲突点)",
            "emotional_baseline": "string (情绪基调，例如：乐观/悲观/警惕/淡漠)",
            "evolution_log": [
                # 日志条目会动态添加，格式如下：
                # {
                #    "chapter": 0,
                #    "event_summary": "导致变化的事件摘要",
                #    "change_analysis": "对心境变化的分析",
                #    "belief_change": "信念的变化（如有）",
                #    "desire_change": "欲望的变化（如有）"
                # }
            ]
        }
        # 当前小说的世界状态（用于一致性检查）
        self.current_world_state = {}
        # 初始化事件/关系/账本子目录
        self.events_path = os.path.join(self.storage_path, 'events')
        self.relationships_path = os.path.join(self.storage_path, 'relationships')
        self.ledgers_path = os.path.join(self.storage_path, 'ledgers')
        os.makedirs(self.events_path, exist_ok=True)
        os.makedirs(self.relationships_path, exist_ok=True)
        os.makedirs(self.ledgers_path, exist_ok=True)
        # 内存缓存小索引
        self._edges_index = {}  # novel_title -> {edge_id: edge_obj}
        self._events_index = {} # novel_title -> list of events (lazy load)
        # 验证器注册表：name -> callable(novel_title, event) -> (bool, message)
        self._validators: Dict[str, Callable[[str, Dict], Tuple[bool, str]]] = {}
        # 注册基础验证器（后续可扩展/覆盖）
        self.register_validator('death', lambda novel_title, ev: self._death_validator(novel_title, ev.get('actor') or ev.get('payload', {}).get('name', ''), ev.get('chapter') or ev.get('chapter_number') or 0))
        self.register_validator('money_balance', self._validator_money_balance)
        self.register_validator('ownership', self._validator_ownership)
        self.register_validator('relationship_contradiction', self._validator_relationship_contradiction)
    def load_previous_assessments(self, novel_title: str, novel_data: Optional[Dict] = None) -> Dict:
        """加载之前章节的评估数据，如果没有则从novel_data初始化"""
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.info(f"加载世界状态失败: {e}")
        # 如果没有找到世界状态文件且有novel_data，则初始化
        if novel_data:
            self.logger.info(f"🔄 未找到现有世界状态，从novel_data初始化...")
            return self.initialize_world_state_from_novel_data(novel_title, novel_data)
        return {}
    # ------------------- Event Store / Relationship / Ledger helpers -------------------
    def _event_file(self, novel_title: str) -> str:
        # 如果有指定小说标题，使用统一路径配置
        if self.novel_title == novel_title:
            paths = path_config.get_project_paths(novel_title)
            return str(Path(paths["events_dir"]) / f"{novel_title}_events.jsonl")
        # 向后兼容
        return os.path.join(self.events_path, f"{novel_title}_events.jsonl")
    def append_event(self, novel_title: str, event: Dict) -> bool:
        """Append an event to the event log (jsonl)."""
        event_file = self._event_file(novel_title)
        try:
            if 'event_id' not in event:
                event['event_id'] = str(uuid.uuid4())
            if 'timestamp' not in event:
                event['timestamp'] = datetime.now().isoformat()
            with open(event_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
            self._events_index.setdefault(novel_title, []).append(event)
            return True
        except Exception as e:
            self.logger.info(f"❌ 无法追加事件: {e}")
            return False
    def load_events(self, novel_title: str) -> List[Dict]:
        if novel_title in self._events_index:
            return self._events_index[novel_title]
        events = []
        event_file = self._event_file(novel_title)
        if os.path.exists(event_file):
            try:
                with open(event_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line: continue
                        try:
                            events.append(json.loads(line))
                        except:
                            continue
            except Exception as e:
                self.logger.info(f"❌ 读取事件文件失败: {e}")
        self._events_index[novel_title] = events
        return events
    def apply_event(self, novel_title: str, event: Dict) -> Tuple[bool, str]:
        # Basic validation
        if not isinstance(event, dict):
            return False, "event must be a dict"
        action = event.get('action')
        actor = event.get('actor')
        chapter = event.get('chapter') or event.get('chapter_number') or 0
        if not action:
            return False, "missing action in event"
        # Run registered validators (death, money, ownership, relationship contradictions, etc.)
        ok, msg = self.run_validators(novel_title, event)
        if not ok:
            return False, msg
        # Dispatch by action
        try:
            # Relationship events
            if action in ('relationship.create', 'relationship.add'):
                payload = event.get('payload', {})
                if not payload.get('from') or not payload.get('to'):
                    return False, 'relationship.create requires payload.with from and to'
                edge_obj = {
                    'from': payload.get('from'),
                    'to': payload.get('to'),
                    'type': payload.get('relation_type', payload.get('type', '盟友')),
                    'description': payload.get('description', ''),
                    'confidence': payload.get('confidence', 1.0),
                    'first_chapter': chapter,
                    'last_updated_chapter': chapter,
                    'visibility': payload.get('visibility', 'public')
                }
                edge_id = self.create_edge(novel_title, edge_obj)
                event['applied'] = True
                event['applied_result'] = {'edge_id': edge_id}
            elif action == 'relationship.update':
                payload = event.get('payload', {})
                edge_id = payload.get('id') or payload.get('edge_id')
                if not edge_id:
                    # try match by characters
                    chars = payload.get('characters') or payload.get('characters_pair')
                    edge_id = None
                    if chars and isinstance(chars, (list, tuple)) and len(chars) >= 2:
                        for e in self.load_relationships(novel_title).values():
                            if set(e.get('from', '')) | set(e.get('to', '')):
                                pass
                    if not edge_id:
                        return False, 'relationship.update requires edge id or matching characters'
                success = self.update_edge(novel_title, edge_id, payload.get('patch', payload))
                event['applied'] = success
                event['applied_result'] = {'updated': success}
            elif action == 'money.transfer':
                payload = event.get('payload', {})
                frm = payload.get('from')
                to = payload.get('to')
                amount = float(payload.get('amount', 0))
                reason = payload.get('reason', '')
                if not frm or not to or amount == 0:
                    return False, 'money.transfer requires from, to and amount'
                # block transfers from dead actors
                ok, reason_text = self._death_validator(novel_title, frm, chapter)
                if not ok:
                    return False, f'blocked by death validator for sender {frm}: {reason_text}'
                tx_from = {
                    'character': frm,
                    'amount': -abs(amount),
                    'counterparty': to,
                    'reason': reason,
                    'chapter': chapter
                }
                tx_to = {
                    'character': to,
                    'amount': abs(amount),
                    'counterparty': frm,
                    'reason': reason,
                    'chapter': chapter
                }
                ok1 = self.append_money_tx(novel_title, tx_from)
                ok2 = self.append_money_tx(novel_title, tx_to)
                event['applied'] = ok1 and ok2
                event['applied_result'] = {'tx_recorded': event['applied']}
            elif action in ('character.update', 'character.add'):
                payload = event.get('payload', {})
                name = payload.get('name') or actor
                if not name:
                    return False, 'character.update requires payload.name or actor'
                # delegate to existing safe manager which handles saves
                self.manage_character_development_table(novel_title, payload, chapter, 'update' if action=='character.update' else 'add')
                event['applied'] = True
                event['applied_result'] = {'character': name}
            else:
                # Unknown action: just append event for audit, no state changes
                event['applied'] = False
                event['applied_result'] = {'note': 'no-op for unknown action'}
            # persist the event log entry (intent + result)
            self.append_event(novel_title, event)
            return True, 'event applied and logged'
        except Exception as e:
            return False, f'exception applying event: {e}'
    def _relationships_file(self, novel_title: str) -> str:
        # 如果有指定小说标题，使用统一路径配置
        if self.novel_title == novel_title:
            paths = path_config.get_project_paths(novel_title)
            return paths["relationships"]
        # 向后兼容
        return os.path.join(self.relationships_path, f"{novel_title}_relationships.json")
    def load_relationships(self, novel_title: str) -> Dict:
        if novel_title in self._edges_index:
            return self._edges_index[novel_title]
        edges = {}
        rel_file = self._relationships_file(novel_title)
        if os.path.exists(rel_file):
            try:
                with open(rel_file, 'r', encoding='utf-8') as f:
                    edges = json.load(f)
            except Exception as e:
                self.logger.info(f"❌ 读取关系文件失败: {e}")
        self._edges_index[novel_title] = edges
        return edges
    def save_relationships(self, novel_title: str) -> bool:
        rel_file = self._relationships_file(novel_title)
        edges = self._edges_index.get(novel_title, {})
        try:
            with open(rel_file, 'w', encoding='utf-8') as f:
                json.dump(edges, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.info(f"❌ 保存关系文件失败: {e}")
            return False
    def create_edge(self, novel_title: str, edge_obj: Dict) -> str:
        edges = self.load_relationships(novel_title)
        edge_id = edge_obj.get('id') or f"e{int(time.time()*1000)}_{str(uuid.uuid4())[:6]}"
        edge_obj['id'] = edge_id
        edge_obj.setdefault('history', [])
        edges[edge_id] = edge_obj
        self._edges_index[novel_title] = edges
        self.save_relationships(novel_title)
        return edge_id
    def update_edge(self, novel_title: str, edge_id: str, patch: Dict) -> bool:
        edges = self.load_relationships(novel_title)
        if edge_id not in edges:
            self.logger.info(f"⚠️ 尝试更新不存在的 edge: {edge_id}")
            return False
        edges[edge_id].update(patch)
        edges[edge_id]['last_updated_chapter'] = patch.get('last_updated_chapter', edges[edge_id].get('last_updated_chapter'))
        self._edges_index[novel_title] = edges
        return self.save_relationships(novel_title)
    def get_edges_for_actor(self, novel_title: str, actor_name: str) -> List[Dict]:
        edges = self.load_relationships(novel_title)
        return [e for e in edges.values() if e.get('from') == actor_name or e.get('to') == actor_name]
    def _money_ledger_file(self, novel_title: str) -> str:
        # 如果有指定小说标题，使用统一路径配置
        if self.novel_title == novel_title:
            paths = path_config.get_project_paths(novel_title)
            return str(Path(paths["events_dir"]) / f"{novel_title}_money_ledger.json")
        # 向后兼容
        return os.path.join(self.ledgers_path, f"{novel_title}_money_ledger.json")
    def append_money_tx(self, novel_title: str, tx: Dict) -> bool:
        ledger_file = self._money_ledger_file(novel_title)
        ledger = []
        if os.path.exists(ledger_file):
            try:
                with open(ledger_file, 'r', encoding='utf-8') as f:
                    ledger = json.load(f)
            except:
                ledger = []
        tx['tx_id'] = tx.get('tx_id') or str(uuid.uuid4())
        tx['timestamp'] = tx.get('timestamp') or datetime.now().isoformat()
        ledger.append(tx)
        try:
            with open(ledger_file, 'w', encoding='utf-8') as f:
                json.dump(ledger, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.info(f"❌ 保存金钱账本失败: {e}")
            return False
    def _death_validator(self, novel_title: str, actor_name: str, chapter_number: int) -> Tuple[bool, str]:
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return True, "no character file"
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                chars = json.load(f)
        except:
            return True, "cannot read character file"
        char = chars.get(actor_name)
        if not char:
            return True, "unknown character"
        status = char.get('status', '').lower()
        if status in ['死亡', 'dead', '已故']:
            return False, f"角色 {actor_name} 已被记录为死亡 (status={status})，阻止后续行为。"
        return True, "ok"
    # ---------------- Validator engine ----------------
    def register_validator(self, name: str, fn: Callable[[str, Dict], Tuple[bool, str]]):
        """Register a validator function. Signature: fn(novel_title, event) -> (bool, message)"""
        if not callable(fn):
            raise ValueError("validator must be callable")
        self._validators[name] = fn
    def run_validators(self, novel_title: str, event: Dict) -> Tuple[bool, str]:
        """Run all registered validators. Returns (True, 'ok') if all pass, else (False, message)."""
        for name, fn in self._validators.items():
            try:
                ok, msg = fn(novel_title, event)
                if not ok:
                    return False, f"validator:{name} -> {msg}"
            except Exception as e:
                return False, f"validator:{name} exception: {e}"
        return True, 'ok'
    def _compute_money_balance(self, novel_title: str, character: str) -> float:
        """Compute approximate current balance by summing money ledger entries for a character."""
        ledger_file = self._money_ledger_file(novel_title)
        if not os.path.exists(ledger_file):
            return 0.0
        try:
            with open(ledger_file, 'r', encoding='utf-8') as f:
                ledger = json.load(f)
        except Exception:
            return 0.0
        bal = 0.0
        for tx in ledger:
            if tx.get('character') == character:
                try:
                    bal += float(tx.get('amount', 0))
                except Exception:
                    continue
        return bal
    def _validator_money_balance(self, novel_title: str, event: Dict) -> Tuple[bool, str]:
        """Ensure senders have enough balance for money.transfer events."""
        action = event.get('action')
        if action != 'money.transfer':
            return True, 'not applicable'
        payload = event.get('payload', {})
        frm = payload.get('from')
        amount = float(payload.get('amount', 0) or 0)
        if not frm:
            return False, 'missing sender'
        balance = self._compute_money_balance(novel_title, frm)
        if balance < amount:
            return False, f'insufficient funds: {frm} balance={balance} required={amount}'
        return True, 'ok'
    def _validator_ownership(self, novel_title: str, event: Dict) -> Tuple[bool, str]:
        payload = event.get('payload', {})
        item = payload.get('item') or payload.get('item_name')
        if not item:
            return True, 'not applicable'
        # load world state
        ws = self.load_previous_assessments(novel_title)
        items = ws.get('cultivation_items', {}) or ws.get('items', {})
        item_entry = items.get(item)
        if not item_entry:
            return False, f'unknown item: {item}'
        expected_owner = item_entry.get('owner')
        actor = event.get('actor') or payload.get('from') or payload.get('actor')
        if expected_owner and actor and expected_owner != actor:
            return False, f'ownership mismatch: item {item} owned by {expected_owner}, actor {actor}'
        return True, 'ok'
    def _validator_relationship_contradiction(self, novel_title: str, event: Dict) -> Tuple[bool, str]:
        action = event.get('action')
        if not action or not action.startswith('relationship'):
            return True, 'not applicable'
        payload = event.get('payload', {})
        from_c = payload.get('from')
        to_c = payload.get('to')
        rel_type = payload.get('relation_type') or payload.get('type') or payload.get('relation')
        if not from_c or not to_c or not rel_type:
            return True, 'insufficient data'
        # load existing edges and check for contradictory types
        edges = self.load_relationships(novel_title)
        contradictions = {
            '盟友': ['敌对', '对手'],
            '恋人': ['敌人'],
            '师徒': []
        }
        for e in edges.values():
            a = e.get('from')
            b = e.get('to')
            if set([a, b]) == set([from_c, to_c]):
                existing_type = e.get('type', '')
                # if new rel_type contradicts existing_type, block
                bad = contradictions.get(rel_type, [])
                if existing_type in bad or (rel_type in contradictions.get(existing_type, [])):
                    return False, f'contradiction with existing relation {existing_type} between {from_c} and {to_c}'
        return True, 'ok'
    def get_current_mindset(self, novel_title: str, character_name: str) -> Dict:
        """获取指定角色的当前心境状态。"""
        mindset_file = os.path.join(self.storage_path, f"{novel_title}_mindset_{character_name}.json")
        if not os.path.exists(mindset_file):
            # 如果文件不存在，返回一个基于模板的初始心境
            initial_mindset = self.character_mindset_template.copy()
            initial_mindset["character_name"] = character_name
            # 可以在这里调用AI进行初次心境生成，或使用默认值
            initial_mindset["core_belief"] = "（待AI在角色设计或首次出场时定义）"
            initial_mindset["core_desire"] = "（待AI在角色设计或首次出场时定义）"
            initial_mindset["core_fear"] = "（待AI在角色设计或首次出场时定义）"
            return initial_mindset
        try:
            with open(mindset_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.info(f"❌ 读取角色 {character_name} 的心境文件失败: {e}")
            return self.character_mindset_template.copy()
    def manage_character_mindset(self, novel_title: str, character_name: str, mindset_change: Dict, chapter_number: int):
        """更新并保存角色的心境档案。"""
        if not character_name or not mindset_change:
            return
        self.logger.info(f"🧠 更新角色 {character_name} 的心境档案 (第{chapter_number}章)...")
        current_mindset = self.get_current_mindset(novel_title, character_name)
        # 更新核心字段
        for key in ["core_belief", "core_desire", "core_fear", "internal_conflict", "emotional_baseline"]:
            if key in mindset_change and mindset_change[key]:
                old_value = current_mindset.get(key)
                new_value = mindset_change[key]
                if old_value != new_value:
                    self.logger.info(f"   - {key} 变化: '{old_value}' -> '{new_value}'")
                    current_mindset[key] = new_value
        # 添加到演变日志
        log_entry = {
            "chapter": chapter_number,
            "event_summary": mindset_change.get("triggering_event", "未知事件"),
            "change_analysis": mindset_change.get("change_analysis", "无分析"),
        }
        current_mindset["evolution_log"].append(log_entry)
        current_mindset["evolution_log"] = current_mindset["evolution_log"][-20:] # 只保留最近20条
        # 保存文件
        mindset_file = os.path.join(self.storage_path, f"{novel_title}_mindset_{character_name}.json")
        try:
            with open(mindset_file, 'w', encoding='utf-8') as f:
                json.dump(current_mindset, f, ensure_ascii=False, indent=4)
            self.logger.info(f"   ✅ 角色 {character_name} 的心境档案已保存。")
        except Exception as e:
            self.logger.info(f"❌ 保存角色 {character_name} 的心境档案失败: {e}")
    def save_assessment_data(self, novel_title: str, chapter_number: int, assessment_data: Dict):
        """保存评估数据"""
        # 更新并保存世界状态
        if 'updated_world_state' in assessment_data:
            self.current_world_state = assessment_data['updated_world_state']
            state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
            try:
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.current_world_state, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.info(f"保存世界状态失败: {e}")
    def assess_character_importance(self, character_data: Dict, chapter_content: str = "") -> str:
        """评估角色重要性"""
        character_name = character_data.get("name", "")
        # 检查是否为未命名角色
        if self._is_unnamed_character(character_name):
            return "unnamed"
        # 检查角色类型
        role_type = character_data.get("role_type", "").lower()
        if any(indicator in role_type for indicator in ["主角", "主要", "重要"]):
            return "major"
        elif any(indicator in role_type for indicator in ["配角", "次要", "路人"]):
            return "minor"
        # 基于内容分析重要性
        if chapter_content:
            importance_score = self._analyze_character_importance_from_content(character_name, chapter_content)
            if importance_score >= 0.7:
                return "major"
            elif importance_score >= 0.3:
                return "minor"
            else:
                return "unnamed"
        # 默认作为次要角色
        return "minor"
    def _is_unnamed_character(self, character_name: str) -> bool:
        """判断是否为未命名角色"""
        if not character_name or len(character_name) <= 1:
            return True
        # 检查是否符合未命名角色模式
        for pattern in self.character_importance_rules["unnamed_character_patterns"]:
            if re.match(pattern, character_name):
                return True
        # 检查是否为通用称谓
        generic_titles = ["老者", "少年", "女子", "男子", "官员", "侍卫", "店小二", "掌柜", "大夫", "书生"]
        if character_name in generic_titles:
            return True
        return False
    def _analyze_character_importance_from_content(self, character_name: str, content: str) -> float:
        """从内容分析角色重要性得分"""
        if not character_name:
            return 0.0
        score = 0.0
        # 1. 提及频率（权重：0.4）
        total_words = len(content)
        mention_count = content.count(character_name)
        mention_frequency = mention_count / max(total_words / 1000, 1)  # 每千字提及次数
        score += min(mention_frequency / 5, 1.0) * 0.4
        # 2. 是否有对话（权重：0.3）
        dialogue_indicators = [f"{character_name}说：", f"{character_name}道：", f"{character_name}问："]
        has_dialogue = any(indicator in content for indicator in dialogue_indicators)
        score += 0.3 if has_dialogue else 0
        # 3. 是否有行动描写（权重：0.2）
        action_indicators = [f"{character_name}站起身", f"{character_name}走过去", f"{character_name}笑了笑"]
        has_actions = any(indicator in content for indicator in action_indicators)
        score += 0.2 if has_actions else 0
        # 4. 是否有心理活动（权重：0.1）
        thought_indicators = [f"{character_name}心想", f"{character_name}思考", f"{character_name}暗想"]
        has_thoughts = any(indicator in content for indicator in thought_indicators)
        score += 0.1 if has_thoughts else 0
        return min(score, 1.0)
    def _update_world_state_incrementally(self, novel_title: str, changes: Dict, chapter_number: int):
        """增量更新世界状态 - 使用清洗后的数据，并增加更新计数 (已整合冗余分类)"""
        # 加载当前世界状态
        current_state = self.load_previous_assessments(novel_title)
        if not current_state:
            current_state = {
                # 初始化时就只使用我们的标准分类
                "characters": {},
                "cultivation_items": {},
                "cultivation_skills": {},
                "relationships": {},
                "locations": {},
                "economy": {}
            }
        # ▼▼▼ 【核心修改】数据合并与迁移逻辑 ▼▼▼
        # 作用：将废弃的通用分类 (items, skills) 自动合并到标准的修仙分类中
        self.logger.info("   🔍 正在检查并合并冗余数据分类...")
        # 1. 合并 items -> cultivation_items
        if 'items' in changes and isinstance(changes['items'], dict):
            if 'cultivation_items' not in changes:
                changes['cultivation_items'] = {}
            # 将 items 中的所有条目合并到 cultivation_items 中
            changes['cultivation_items'].update(changes['items'])
            self.logger.info(f"      ✅ 已将 {len(changes['items'])} 个条目从 'items' 合并到 'cultivation_items'")
            del changes['items'] # 删除旧分类，避免后续处理
        # 2. 合并 skills -> cultivation_skills
        if 'skills' in changes and isinstance(changes['skills'], dict):
            if 'cultivation_skills' not in changes:
                changes['cultivation_skills'] = {}
            # 将 skills 中的所有条目合并到 cultivation_skills 中
            changes['cultivation_skills'].update(changes['skills'])
            self.logger.info(f"      ✅ 已将 {len(changes['skills'])} 个条目从 'skills' 合并到 'cultivation_skills'")
            del changes['skills'] # 删除旧分类
        self.logger.info("   ✨ 数据合并完成。")
        # ▲▲▲ 修改结束 ▲▲▲
        # 应用增量更新 - 现在数据已经是清洗后的格式
        for category, elements in changes.items():
            if category == "characters":
                self.logger.info(f"   ℹ️ 跳过 world_state 中的 'characters' 更新，由 character_development_table 统一管理。")
                continue
            if category not in current_state:
                current_state[category] = {}
            for element_id, element_data in elements.items():
                if element_id in current_state[category]:
                    # 更新现有元素 - 只更新清洗后的字段
                    current_element = current_state[category][element_id]
                    # 更新基础字段
                    for field in ['description', 'owner', 'status', 'level', 'quality', 'type']:
                        if field in element_data:
                            current_element[field] = element_data[field]
                    # 更新attributes字段（如果存在）
                    if 'attributes' in element_data:
                        if 'attributes' not in current_element:
                            current_element['attributes'] = {}
                        current_element['attributes'].update(element_data['attributes'])
                    # 增加更新计数
                    current_element['update_count'] = current_element.get('update_count', 0) + 1
                    current_element['last_updated'] = chapter_number
                else:
                    # 新增元素 - 初始化更新计数为1
                    element_data['first_appearance'] = chapter_number
                    element_data['last_updated'] = chapter_number
                    element_data['update_count'] = 1  # 新增元素的初始更新计数
                    current_state[category][element_id] = element_data
        # 【清理】从最终状态中移除空的废弃分类，保持文件整洁
        for deprecated_key in ['items', 'skills']:
            if deprecated_key in current_state:
                del current_state[deprecated_key]
        # 保存更新后的世界状态
        self.current_world_state = current_state
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(current_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.info(f"保存世界状态失败: {e}")
    def _simplify_character_status(self, novel_title: str, character_name: str, status: str, chapter_number: int):
        """简化死亡/退场角色的信息，只保留状态和姓名"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            if character_name in characters:
                # 保留核心信息，删除详细设定
                characters[character_name] = {
                    "name": character_name,
                    "status": status,
                    "first_appearance_chapter": characters[character_name].get("first_appearance_chapter", chapter_number),
                    "last_updated_chapter": chapter_number,
                    "death_chapter": chapter_number if status == "dead" else None,
                    "total_appearances": characters[character_name].get("total_appearances", 1)
                }
                # 保存简化后的角色信息
                with open(character_file, 'w', encoding='utf-8') as f:
                    json.dump(characters, f, ensure_ascii=False, indent=2)
                self.logger.info(f"✅ 角色 {character_name} 状态已简化为 {status}")
        except Exception as e:
            self.logger.info(f"❌ 简化角色状态失败: {e}")
    def _validate_and_clean_world_state_changes(self, changes: Dict, chapter_number: int) -> Dict:
        """验证和清洗世界状态变化数据，确保字段统一 - 带详细调试"""
        self.logger.info(f"🔍 [DEBUG] 开始清洗世界状态变化数据...")
        self.logger.info(f"   📁 原始数据总览:")
        for category, elements in changes.items():
            element_type = type(elements).__name__
            element_count = len(elements) if hasattr(elements, '__len__') else "N/A"
            self.logger.info(f"      {category}: {element_type} - {element_count}")
        ALLOWED_FIELDS = {
            "characters": {
                "name": str,
                "description": str,
                "attributes": {
                    "status": str,
                    "location": str,
                    "title": str,
                    "occupation": str, 
                    "faction": str,
                    "cultivation_level": str,  # 修为等级
                    "cultivation_system": str,  # 修为体系（修仙/异能/武侠等）
                    "money": (int, float),  # 金钱数量
                    "money_sources": list,   # 金钱来源记录
                    "recent_transactions": list  # 最近交易记录
                }
            },
            "economy": {  # 新增：经济系统
                "type": str,  # 收入/支出
                "amount": (int, float),
                "from_character": str,
                "to_character": str, 
                "reason": str,  # 交易原因
                "item_involved": str,  # 涉及物品
                "chapter": int
            },
            "cultivation_items": {  # 新增：修炼相关物品
                "description": str,
                "owner": str,
                "type": str,  # 丹药/法宝/材料等
                "quality": str,  # 品质等级
                "status": str,
                "location": str
            },
            "cultivation_skills": {  # 新增：功法技能
                "description": str,
                "owner": str,
                "type": str,  # 功法/神通/秘术等
                "level": str,
                "quality": str,  # 品质等级
                "status": str
            },
            "relationships": {
                "type": str,
                "description": str,
                "status": str
            },
            "locations": {
                "description": str,
                "status": str
            }
        }
        cleaned_changes = {}
        for category, elements in changes.items():
            self.logger.info(f"🔍 [DEBUG] 处理类别: {category}")
            if category not in ALLOWED_FIELDS:
                self.logger.info(f"⚠️ 跳过未知类别: {category}")
                continue
            # 处理列表类型的elements
            if isinstance(elements, list):
                self.logger.info(f"🔄 检测到列表格式的 {category}，转换为字典格式...")
                self.logger.info(f"   📊 原始列表长度: {len(elements)}")
                elements_dict = {}
                for i, element in enumerate(elements):
                    self.logger.info(f"   🔍 处理列表元素 {i}: {type(element)}")
                    if isinstance(element, dict):
                        # 尝试从元素中获取标识符
                        element_id = element.get('name') or element.get('id') or f"{category}_{i}"
                        self.logger.info(f"   ✅ 列表元素 {i} -> 字典键: {element_id}")
                        elements_dict[element_id] = element
                    else:
                        self.logger.info(f"⚠️ 跳过无效列表元素 {i}: {type(element)} -> {element}")
                elements = elements_dict
                self.logger.info(f"   📊 转换后字典长度: {len(elements)}")
            # 现在elements应该是字典了
            if not isinstance(elements, dict):
                self.logger.info(f"⚠️ 跳过无效数据格式的类别: {category}，期望字典，实际为 {type(elements)}")
                continue
            cleaned_changes[category] = {}
            allowed_structure = ALLOWED_FIELDS[category]
            self.logger.info(f"   📊 处理 {category} 中的 {len(elements)} 个元素")
            for element_id, element_data in elements.items():
                self.logger.info(f"   🔍 处理元素: {category}.{element_id}")
                self.logger.info(f"      数据类型: {type(element_data)}")
                if not isinstance(element_data, dict):
                    self.logger.info(f"⚠️ 跳过无效数据格式: {element_id} -> {type(element_data)}")
                    continue
                cleaned_data = {}
                # 验证和清洗字段
                for field, field_type in allowed_structure.items():
                    self.logger.info(f"      检查字段: {field} (期望类型: {field_type})")
                    if field in element_data:
                        field_value = element_data[field]
                        self.logger.info(f"        找到字段值: {field_value} (类型: {type(field_value)})")
                        if isinstance(field_type, dict):
                            # 嵌套字典字段（如attributes）
                            self.logger.info(f"        处理嵌套字典字段: {field}")
                            if isinstance(field_value, dict):
                                cleaned_nested = {}
                                for nested_field, nested_type in field_type.items():
                                    self.logger.info(f"          检查嵌套字段: {nested_field} (期望类型: {nested_type})")
                                    if nested_field in field_value:
                                        nested_value = field_value[nested_field]
                                        self.logger.info(f"            找到嵌套字段值: {nested_value} (类型: {type(nested_value)})")
                                        if isinstance(nested_value, nested_type):
                                            cleaned_nested[nested_field] = nested_value
                                            self.logger.info(f"            ✅ 嵌套字段验证通过: {nested_field}")
                                        else:
                                            self.logger.info(f"            ⚠️ 嵌套字段类型不匹配: {nested_field} -> 期望 {nested_type}, 实际 {type(nested_value)}")
                                if cleaned_nested:
                                    cleaned_data[field] = cleaned_nested
                                    self.logger.info(f"        ✅ 嵌套字典处理完成: {len(cleaned_nested)} 个字段")
                                else:
                                    self.logger.info(f"        ⚠️ 嵌套字典无有效字段")
                            else:
                                self.logger.info(f"        ⚠️ 字段格式错误: {field} -> 期望字典, 实际 {type(field_value)}")
                        else:
                            # 简单字段
                            if isinstance(field_value, field_type):
                                cleaned_data[field] = field_value
                                self.logger.info(f"        ✅ 简单字段验证通过: {field}")
                            else:
                                self.logger.info(f"        ⚠️ 字段类型不匹配: {field} -> 期望 {field_type}, 实际 {type(field_value)}")
                    else:
                        self.logger.info(f"        字段不存在: {field}")
                # 确保必要字段存在
                if category == "characters":
                    if "attributes" not in cleaned_data:
                        self.logger.info(f"        🔧 为角色添加默认attributes")
                        cleaned_data["attributes"] = {}
                    if "status" not in cleaned_data["attributes"]:
                        cleaned_data["attributes"]["status"] = "活跃"
                        self.logger.info(f"        🔧 添加默认status: 活跃")
                    if "location" not in cleaned_data["attributes"]:
                        cleaned_data["attributes"]["location"] = "未知"
                        self.logger.info(f"        🔧 添加默认location: 未知")
                if cleaned_data:
                    cleaned_changes[category][element_id] = cleaned_data
                    self.logger.info(f"   ✅ 已清洗: {category}.{element_id} -> {len(cleaned_data)} 个字段")
                else:
                    self.logger.info(f"   ❌ 数据无效已跳过: {category}.{element_id}")
            self.logger.info(f"   📊 {category} 清洗完成: {len(cleaned_changes[category])} 个有效元素")
        self.logger.info(f"🎉 [DEBUG] 清洗完成总结:")
        total_cleaned = sum(len(elements) for elements in cleaned_changes.values())
        self.logger.info(f"   总有效元素: {total_cleaned}")
        for category, elements in cleaned_changes.items():
            self.logger.info(f"   {category}: {len(elements)} 个元素")
        return cleaned_changes
    def initialize_world_state_from_novel_data(self, novel_title: str, novel_data: Dict):
        """基于小说数据初始化世界状态"""
        world_state = {
            "characters": {},
            "items": {},
            "relationships": {},
            "skills": {},
            "locations": {}
        }
        # 从角色设计中提取角色信息
        character_design = novel_data.get("character_design", {})
        if character_design:
            # 处理主角
            main_character = character_design.get("main_character", {})
            if main_character:
                name = main_character.get("name", "主角")
                world_state["characters"][name] = {
                    "first_appearance": 1,
                    "description": main_character.get("personality", ""),
                    "attributes": main_character.get("attributes", {}),
                    "last_updated": 1
                }
            # 处理配角
            supporting_characters = character_design.get("supporting_characters", [])
            for char in supporting_characters:
                name = char.get("name", "")
                if name:
                    world_state["characters"][name] = {
                        "first_appearance": 1,
                        "description": char.get("personality", ""),
                        "attributes": char.get("attributes", {}),
                        "last_updated": 1
                    }
        # 从世界观中提取地点、物品等信息
        worldview = novel_data.get("core_worldview", {})
        if worldview:
            # 提取地点
            locations = worldview.get("locations", [])
            for loc in locations:
                name = loc.get("name", "")
                if name:
                    world_state["locations"][name] = {
                        "description": loc.get("description", ""),
                        "first_appearance": 1,
                        "last_updated": 1
                    }
            # 提取物品
            items = worldview.get("items", [])
            for item in items:
                name = item.get("name", "")
                if name:
                    world_state["items"][name] = {
                        "owner": item.get("owner", ""),
                        "status": item.get("status", ""),
                        "first_appearance": 1,
                        "last_updated": 1
                    }
        # 保存初始世界状态
        state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(world_state, f, ensure_ascii=False, indent=2)
            self.logger.info(f"✅ 从novel_data初始化世界状态成功，保存到 {state_file}")
        except Exception as e:
            self.logger.info(f"❌ 保存初始世界状态失败: {e}")
        return world_state
    def manage_character_development_table(self, novel_title: str, character_data: Dict,
                                        current_chapter: int, action: str = "update") -> Dict:
        """管理角色发展表 - 修复数据清空问题
        
        🔧 修复版本：实现严格的新角色准入过滤机制
        """
        # 使用统一路径配置获取角色发展文件路径
        if self.novel_title == novel_title:
            character_file = path_config.get_quality_data_path(novel_title, "character_development")
        else:
            # 向后兼容：使用旧路径
            character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        
        # 确保目录存在
        os.makedirs(os.path.dirname(character_file), exist_ok=True)
        
        self.logger.info(f"🔄 开始管理角色发展表:")
        self.logger.info(f"   角色文件路径: {os.path.abspath(character_file)}")
        self.logger.info(f"   小说: {novel_title}")
        self.logger.info(f"   角色: {character_data.get('name')}")
        self.logger.info(f"   章节: {current_chapter}")
        self.logger.info(f"   操作: {action}")
        # 确保存储目录存在
        os.makedirs(self.storage_path, exist_ok=True)
        # 加载现有数据 - 修复文件读取问题
        characters = {}
        if os.path.exists(character_file):
            try:
                with open(character_file, 'r', encoding='utf-8') as f:
                    file_content = f.read().strip()
                    if file_content:  # 确保文件不是空的
                        characters = json.loads(file_content)
                        self.logger.info(f"✅ 已加载现有角色数据: {len(characters)} 个角色")
                    else:
                        self.logger.info(f"⚠️ 角色文件为空，将重新初始化")
                        characters = {}
            except Exception as e:
                self.logger.info(f"❌ 加载角色文件失败: {e}")
                self.logger.info(f"   文件路径: {character_file}")
                characters = {}
        else:
            self.logger.info(f"🆕 角色发展文件不存在，将创建新文件")
            characters = {}
        character_name = character_data.get("name")
        if not character_name:
            self.logger.info(f"❌ 角色数据中没有name字段，无法管理")
            return characters
        
        # 🔧 修复1: 严格的角色名称验证
        if not self._is_valid_character_name(character_name):
            self.logger.info(f"❌ 角色名称 '{character_name}' 未通过有效性验证，拒绝添加")
            return characters
        
        # 评估角色重要性
        importance = self.assess_character_importance(character_data)
        self.logger.info(f"📊 角色 {character_name} 的重要性评估为: {importance}")
        
        # 🔧 修复2: 新角色准入机制
        if action == "add" and character_name not in characters:
            # 对新角色进行更严格的验证
            if not self._should_accept_new_character(character_name, character_data, characters, current_chapter):
                self.logger.info(f"❌ 新角色 '{character_name}' 未通过准入验证，拒绝添加")
                return characters
        
        # 保存当前角色数量用于比较
        previous_count = len(characters)
        if action == "add":
            # 首次出场时添加
            if character_name not in characters:
                # 根据重要性选择模板
                if importance == "major":
                    template = self.character_development_templates["core_character"].copy()
                elif importance == "minor":
                    template = self.character_development_templates["minor_character"].copy()
                else:
                    template = self.character_development_templates["unnamed_character"].copy()
                # 合并模板和传入数据
                characters[character_name] = {
                    **template,
                    **character_data,
                    "importance": importance,
                    "first_appearance_chapter": current_chapter,
                    "last_updated_chapter": current_chapter,
                    "total_appearances": 1
                }
                self.logger.info(f"✅ 新增角色到发展表: {character_name}")
                self.logger.info(f"   重要性: {importance}")
                self.logger.info(f"   首次出场: 第{current_chapter}章")
                self.logger.info(f"   角色类型: {character_data.get('role_type', '未知')}")
            else:
                # 如果角色已存在，更新出场信息
                characters[character_name]["total_appearances"] = characters[character_name].get("total_appearances", 0) + 1
                characters[character_name]["last_updated_chapter"] = current_chapter
                self.logger.info(f"🔄 角色已存在，更新出场信息: {character_name}")
                self.logger.info(f"   总出场次数: {characters[character_name]['total_appearances']}")
                self.logger.info(f"   最后更新章节: {current_chapter}")
        elif action == "update":
            # 更新现有角色 - 修复数据丢失问题
            if character_name in characters:
                # 更新出场次数和最后出场章节
                characters[character_name]["total_appearances"] = characters[character_name].get("total_appearances", 0) + 1
                characters[character_name]["last_updated_chapter"] = current_chapter
                current_importance = characters[character_name].get("importance", "minor")
                self.logger.info(f"🔄 更新角色: {character_name} (重要性: {current_importance})")
                # 更新基础字段 - 只更新有值的字段
                base_fields = ["name", "status", "role_type", "importance"]
                for field in base_fields:
                    if field in character_data and character_data[field]:
                        old_value = characters[character_name].get(field)
                        new_value = character_data[field]
                        if old_value != new_value:
                            characters[character_name][field] = new_value
                            self.logger.info(f"   更新字段 {field}: {old_value} -> {new_value}")
                            # ▼▼▼ 在更新基础字段之后，添加这段代码 ▼▼▼
                # 合并更新 attributes
                if "attributes" in character_data and character_data["attributes"]:
                    if "attributes" not in characters[character_name]:
                        characters[character_name]["attributes"] = {}
                    # 使用.update()方法合并字典，只更新传入的字段
                    characters[character_name]["attributes"].update(character_data["attributes"])
                    self.logger.info(f"   更新 attributes: {character_data['attributes']}")
                # ▲▲▲ 添加结束 ▲▲▲
                # 更新修为信息 - 修复空数据问题
                if "cultivation_info" in character_data and character_data["cultivation_info"]:
                    if "cultivation_info" not in characters[character_name]:
                        characters[character_name]["cultivation_info"] = {}
                    cultivation_updates = character_data["cultivation_info"]
                    for key, value in cultivation_updates.items():
                        if value:  # 只更新非空值
                            old_value = characters[character_name]["cultivation_info"].get(key)
                            if old_value != value:
                                characters[character_name]["cultivation_info"][key] = value
                                self.logger.info(f"   更新修为 {key}: {old_value} -> {value}")
                # 更新性格特征
                if "personality_traits" in character_data and character_data["personality_traits"]:
                    if "personality_traits" not in characters[character_name]:
                        characters[character_name]["personality_traits"] = {}
                    personality_updates = character_data["personality_traits"]
                    for key, value in personality_updates.items():
                        if value:
                            if key == "core_traits" and isinstance(value, list):
                                # 合并核心特质列表
                                existing_traits = characters[character_name]["personality_traits"].get(key, [])
                                for trait in value:
                                    if trait not in existing_traits:
                                        existing_traits.append(trait)
                                        self.logger.info(f"   新增核心特质: {trait}")
                                characters[character_name]["personality_traits"][key] = existing_traits
                            else:
                                old_value = characters[character_name]["personality_traits"].get(key)
                                if old_value != value:
                                    characters[character_name]["personality_traits"][key] = value
                                    self.logger.info(f"   更新性格 {key}: {old_value} -> {value}")
                # 更新背景故事
                if "background_story" in character_data and character_data["background_story"]:
                    if "background_story" not in characters[character_name]:
                        characters[character_name]["background_story"] = {}
                    background_updates = character_data["background_story"]
                    for key, value in background_updates.items():
                        if value:
                            if key == "key_experiences" and isinstance(value, list):
                                # 合并关键经历
                                existing_experiences = characters[character_name]["background_story"].get(key, [])
                                for exp in value:
                                    if exp not in existing_experiences:
                                        existing_experiences.append(exp)
                                        self.logger.info(f"   新增关键经历: {exp}")
                                characters[character_name]["background_story"][key] = existing_experiences
                            else:
                                old_value = characters[character_name]["background_story"].get(key)
                                if old_value != value:
                                    characters[character_name]["background_story"][key] = value
                                    self.logger.info(f"   更新背景 {key}: {old_value} -> {value}")
                # 更新名场面
                if "iconic_scenes" in character_data and character_data["iconic_scenes"]:
                    if "iconic_scenes" not in characters[character_name]:
                        characters[character_name]["iconic_scenes"] = []
                    for new_scene in character_data["iconic_scenes"]:
                        # 检查是否已存在类似场景
                        scene_exists = False
                        for existing_scene in characters[character_name]["iconic_scenes"]:
                            if (existing_scene.get("chapter") == new_scene.get("chapter") and 
                                existing_scene.get("description") == new_scene.get("description")):
                                scene_exists = True
                                break
                        if not scene_exists:
                            characters[character_name]["iconic_scenes"].append(new_scene)
                            self.logger.info(f"   新增名场面: {new_scene.get('description', '新场景')}")
                # 更新关系网络
                if "relationship_network" in character_data and character_data["relationship_network"]:
                    if "relationship_network" not in characters[character_name]:
                        characters[character_name]["relationship_network"] = {"allies": [], "rivals": [], "complex_relationships": []}
                    relationship_updates = character_data["relationship_network"]
                    for rel_type, rel_list in relationship_updates.items():
                        if rel_type in characters[character_name]["relationship_network"] and isinstance(rel_list, list):
                            existing_rels = characters[character_name]["relationship_network"][rel_type]
                            for new_rel in rel_list:
                                if new_rel not in existing_rels:
                                    existing_rels.append(new_rel)
                                    self.logger.info(f"   新增{rel_type}: {new_rel}")
                # 更新发展里程碑
                if "development_milestones" in character_data and character_data["development_milestones"]:
                    if "development_milestones" not in characters[character_name]:
                        characters[character_name]["development_milestones"] = []
                    for new_milestone in character_data["development_milestones"]:
                        # 检查是否已存在类似里程碑
                        milestone_exists = False
                        for existing_milestone in characters[character_name]["development_milestones"]:
                            if (existing_milestone.get("chapter") == new_milestone.get("chapter") and 
                                existing_milestone.get("description") == new_milestone.get("description")):
                                milestone_exists = True
                                break
                        if not milestone_exists:
                            characters[character_name]["development_milestones"].append(new_milestone)
                            self.logger.info(f"   新增里程碑: {new_milestone.get('description', '新里程碑')}")
                # 对于次要和未命名角色，更新基本信息
                if current_importance in ["minor", "unnamed"]:
                    minor_fields = ["basic_description", "purpose_in_story", "appearance_context"]
                    for field in minor_fields:
                        if field in character_data and character_data[field]:
                            old_value = characters[character_name].get(field)
                            new_value = character_data[field]
                            if old_value != new_value:
                                characters[character_name][field] = new_value
                                self.logger.info(f"   更新{field}: {old_value} -> {new_value}")
                self.logger.info(f"✅ 成功更新角色发展表: {character_name}")
                self.logger.info(f"   总出场次数: {characters[character_name]['total_appearances']}")
                self.logger.info(f"   最后更新章节: {current_chapter}")
            else:
                self.logger.info(f"⚠️ 角色 {character_name} 不存在于发展表中，将自动添加")
                # 如果角色不存在，自动转为添加操作
                return self.manage_character_development_table(novel_title, character_data, current_chapter, "add")
        # 保存数据 - 添加保护机制
        try:
            # 检查数据是否有效
            if not characters:
                self.logger.info(f"❌ 警告: 尝试保存空的角色发展表!")
                return characters
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(characters, f, ensure_ascii=False, indent=2)
            current_count = len(characters)
            abs_path = os.path.abspath(character_file)
            self.logger.info(f"💾 角色发展表已保存到: {abs_path}")
            self.logger.info(f"   角色总数: {current_count} (之前: {previous_count})")
            self.logger.info(f"   文件大小: {os.path.getsize(character_file)} 字节")
            # 验证保存是否成功
            if os.path.getsize(character_file) < 10:  # 文件太小，可能保存失败
                self.logger.info(f"⚠️ 警告: 保存的文件大小异常，可能保存失败")
        except Exception as e:
            self.logger.info(f"❌ 保存角色发展表失败: {e}")
            import traceback
            traceback.print_exc()
        return characters
    def get_character_development_suggestions(self, character_name: str, novel_title: str, current_chapter: int) -> List[Dict]:
        """获取角色发展建议 - 仅对重要角色提供建议"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return []
        with open(character_file, 'r', encoding='utf-8') as f:
            characters = json.load(f)
        if character_name not in characters:
            return []
        character = characters[character_name]
        character_status = character.get("status", "active")
        # 只对活跃的重要角色提供建议
        if character_status != "active" or character.get("importance") != "major":
            return []
        suggestions = []
        # 基于出场次数和章节进度生成建议
        appearance_gap = current_chapter - character.get("last_updated_chapter", 0)
        total_appearances = character.get("total_appearances", 1)
        # 判断角色是否已充分建立
        is_character_established = total_appearances >= 5 and appearance_gap <= 10
        # 检查是否需要添加名场面（只在角色未充分建立时建议）
        if not is_character_established:
            iconic_scenes = character.get("iconic_scenes", [])
            if len(iconic_scenes) < 3 and total_appearances >= 3:
                core_trait = (character.get('personality_traits', {}).get('core_traits') or ['性格'])[0]
                suggestions.append({
                    "type": "添加名场面",
                    "description": f"为{character_name}设计一个展现{core_trait}特质的名场面",
                    "priority": "高",
                    "implementation": f"在第{current_chapter}章安排一个关键场景，通过具体行动展示{character_name}的{core_trait}特质",
                    "reason": f"角色已出场{total_appearances}次，需要强化形象"
                })
        # 检查是否需要背景故事（在角色出场3-5章后，且未充分建立时）
        if not is_character_established:
            background_revealed = character.get("development_status", {}).get("background_revealed", False)
            if not background_revealed and total_appearances >= 3 and total_appearances <= 5:
                suggestions.append({
                    "type": "背景故事",
                    "description": f"为{character_name}添加背景故事，解释其性格形成原因",
                    "priority": "中",
                    "implementation": f"通过回忆、对话或第三方提及的方式，在第{current_chapter}章揭示{character_name}的过去经历",
                    "reason": f"角色已出场{total_appearances}次，是揭示背景的合适时机"
                })
        # 检查对话强化（如果超过5章没有特色对话，无论角色是否建立都需要）
        last_dialogue_chapter = character.get("last_dialogue_chapter", 0)
        if current_chapter - last_dialogue_chapter > 5:
            speech_style = character.get('personality_traits', {}).get('speech_style', '普通')
            suggestions.append({
                "type": "对话强化",
                "description": f"为{character_name}安排特色对话，强化'{speech_style}'语言风格",
                "priority": "中",
                "implementation": f"在第{current_chapter}章设计符合{character_name}语言风格的对话",
                "reason": f"已{current_chapter - last_dialogue_chapter}章没有特色对话"
            })
        # 检查关系发展（持续发展，无论角色是否建立）
        relationships = character.get("relationship_network", {})
        total_relationships = len(relationships.get("allies", [])) + len(relationships.get("rivals", []))
        if total_relationships < 2 and total_appearances >= 5:
            suggestions.append({
                "type": "关系发展",
                "description": f"为{character_name}建立新的人际关系",
                "priority": "中",
                "implementation": f"在第{current_chapter}章通过互动建立新的盟友或对手关系",
                "reason": f"角色人际关系网络较简单，需要丰富"
            })
        # 如果角色已充分建立，添加深化建议
        if is_character_established:
            suggestions.append({
                "type": "角色深化",
                "description": f"深化{character_name}的性格层次，展现更多复杂性",
                "priority": "低",
                "implementation": f"通过内心独白或矛盾选择展示{character_name}的性格多面性",
                "reason": f"角色基础已稳固，需要展现更深层次的特质"
            })
        return suggestions[:3]  # 返回前3个最高优先级的建议
    def assess_character_development(self, chapter_content: str, characters_in_chapter: List[str], 
                                novel_title: str, chapter_number: int) -> Dict:
        """评估角色发展质量并返回更新建议 - 基于章节编号"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        # 加载现有角色数据
        existing_characters = {}
        if os.path.exists(character_file):
            with open(character_file, 'r', encoding='utf-8') as f:
                existing_characters = json.load(f)
        assessment_result = {
            "chapter_number": chapter_number,
            "character_updates": {},
            "development_suggestions": [],
            "new_characters": []
        }
        for character_name in characters_in_chapter:
            if character_name in existing_characters:
                # 更新角色出场信息
                self.manage_character_development_table(
                    novel_title, 
                    {"name": character_name}, 
                    chapter_number, 
                    "update"
                )
                # 获取发展建议
                suggestions = self.get_character_development_suggestions(character_name, novel_title, chapter_number)
                # 分析角色表现
                character_presence = self._analyze_character_presence(character_name, chapter_content)
                assessment_result["character_updates"][character_name] = {
                    "presence_analysis": character_presence,
                    "development_suggestions": suggestions,
                    "current_appearance": chapter_number,
                    "total_appearances": existing_characters[character_name].get("total_appearances", 1) + 1
                }
                assessment_result["development_suggestions"].extend(suggestions)
            else:
                # 新角色首次出现
                assessment_result["new_characters"].append({
                    "name": character_name,
                    "first_appearance_chapter": chapter_number
                })
        return assessment_result
    def _analyze_character_presence(self, character_name: str, chapter_content: str) -> Dict:
        """分析角色在章节中的存在感"""
        # 统计角色提及次数
        mention_count = chapter_content.count(character_name)
        # 检测是否有对话
        has_dialogue = f"{character_name}说：" in chapter_content or f"{character_name}道：" in chapter_content
        # 检测是否有行动描写
        action_indicators = ["站起身", "走过去", "笑了笑", "皱眉头", "叹息", "握拳"]
        has_actions = any(indicator in chapter_content for indicator in action_indicators)
        # 检测是否有心理活动
        thought_indicators = ["心想", "思考", "暗想", "寻思"]
        has_thoughts = any(indicator in chapter_content for indicator in thought_indicators)
        return {
            "mention_count": mention_count,
            "has_dialogue": has_dialogue,
            "has_actions": has_actions,
            "has_thoughts": has_thoughts,
            "presence_score": min(10, mention_count * 2 + has_dialogue * 3 + has_actions * 2 + has_thoughts * 2)
        }
    def _load_character_development_data(self, novel_title: str) -> Dict:
        """加载角色发展数据"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return {}
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.info(f"加载角色发展数据失败: {e}")
            return {}
    def _gather_text_from_assessment(self, assessment: Dict) -> str:
        """从评估结果中收集所有可能的文本片段，供后处理解析使用。"""
        texts = []
        def _recursively_collect(obj):
            if not obj:
                return
            if isinstance(obj, str):
                texts.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    _recursively_collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    _recursively_collect(item)
        _recursively_collect(assessment)
        return "\n".join(t for t in texts if t and len(t) > 10)
    def _is_valid_character_name(self, name: str) -> bool:
        """验证是否为有效的角色名称
        
        🔧 修复版本：更严格的角色名称验证机制
        """
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # 长度检查：角色名应该在1-20个字符之间（允许单字姓氏）
        if len(name) < 1 or len(name) > 20:
            return False
        
        # 🔧 修复：单字姓氏特殊情况
        if len(name) == 1:
            # 单字必须是常见姓氏 - 扩展常见姓氏列表
            common_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
                              '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
                              '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
                              '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金', '石', '廖', '贾', '夏']
            if name in common_surnames:
                return True
            else:
                return False
        
        # 🔧 修复1: 大幅扩展无效词汇黑名单
        invalid_words = {
            # 基础虚词和功能词
            "的", "之", "是", "在", "有", "没有", "可", "可以", "能够", "应该", "需要", "想要", "希望", "愿", "要", "会", "将", "已", "未",
            
            # 认知和感觉词汇
            "感觉", "认为", "知道", "明白", "理解", "发现", "意识到", "察觉", "想到", "想到", "预料", "意外", "突然", "忽然",
            "情绪", "心情", "态度", "想法", "观念", "概念", "思想", "意识", "念头", "心思", "心意",
            
            # 状态和变化词汇
            "活跃", "死亡", "生存", "存在", "出现", "消失", "变化", "发展", "成长", "进化", "退化", "转变",
            "伪装", "潜伏", "隐藏", "暴露", "危险", "安全", "威胁", "机会", "危机", "转机",
            
            # 时间和顺序词汇
            "第一", "第二", "第三", "开始", "结束", "之前", "之后", "同时", "接着", "然后", "随后", "最后", "最终",
            "立刻", "马上", "立即", "稍后", "片刻", "瞬间", "一时", "一时", "起初", "原本", "现在", "目前", "如今",
            "过去", "未来", "明天", "昨天", "今天", "早上", "晚上", "中午", "深夜",
            
            # 动作和动词短语
            "站起身", "走过去", "笑了笑", "皱眉头", "叹息", "握拳", "抬头", "低头", "躺下", "坐起", "转身", "离开", "返回", "进入", "退出", "靠近",
            "拿起", "放下", "握住", "松开", "推开", "拉开", "打开", "关闭", "锁住", "解开",
            
            # 修饰词和形容词
            "极大", "巨大", "很大", "非常", "特别", "极其", "相当", "比较", "稍微", "略微", "十分", "万分",
            "更多", "更少", "更好", "更坏", "更快", "更慢", "更高", "更低", "更强", "更弱", "更大", "更小",
            "美丽", "丑陋", "英俊", "普通", "特殊", "稀有", "常见", "罕见", "独特",
            
            # 逻辑连接词
            "因为", "所以", "但是", "然而", "而且", "并且", "或者", "如果", "虽然", "尽管", "无论", "不管", "只要",
            
            # 🔧 修复2: 修仙小说特有的非角色词汇（移除可能是角色称谓的词汇）
            "妖兽", "灵兽", "魔兽", "神兽", "圣兽", "凶兽", "异兽",
            "灵石", "灵药", "丹药", "法宝", "灵器", "仙器", "神器", "魔器", "宝物", "珍宝",
            "剑气", "刀光", "杀气", "威压", "气势", "威势", "灵压",
            "修为", "境界", "等级", "品级", "阶位", "位阶", "修士", "修真者", "修仙者",
            # 注意：移除了"师兄", "师妹", "师姐", "师弟", "师父", "师尊", "师祖", "掌门", "长老", "宗主", "门主", "教主", "宫主"
            # 这些可能是有效的角色名称或称谓，应该在后续验证中处理
            
            # 情绪词汇
            "愤怒", "悲伤", "快乐", "高兴", "痛苦", "绝望", "希望", "恐惧", "惊讶", "震惊",
            
            # 通用称谓和职业
            "老者", "少年", "女子", "男子", "官员", "侍卫", "店小二", "掌柜", "大夫", "书生", "商人", "工匠", "农夫",
            "路人", "士兵", "村民", "弟子", "门徒", "教众", "信徒", "仆人", "奴隶", "囚犯",
            "侠客", "剑客", "刀客", "刺客", "盗贼", "强盗", "土匪", "山贼",
            
            # 物品和装备
            "王座", "李子", "张开", "陈旧", "青虹剑", "倚天剑", "屠龙刀", "打狗棒",
            
            # 地点和位置
            "山顶", "山脚", "山腰", "河边", "湖边", "海边", "城门", "门口", "窗前", "门前",
            "东边", "西边", "南边", "北边", "左边", "右边", "前面", "后面", "上面", "下面",
            
            # 方位和方向
            "东方", "西方", "南方", "北方", "中央", "中间", "旁边", "附近", "远处", "近处",
            
            # 数字和数量
            "一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "万", "亿",
            "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖", "拾",
            "一个", "两个", "三个", "几个", "许多", "无数", "一些", "所有", "全部", "整个",
            
            # 抽象概念
            "爱情", "友情", "仇恨", "恩怨", "因果", "命运", "天意", "天道", "人道", "地道",
            "正义", "邪恶", "光明", "黑暗", "善良", "邪恶", "美丽", "丑陋", "强大", "弱小",
            
            # 自然现象
            "风雨", "雷电", "冰雪", "火焰", "洪水", "地震", "火山", "流星", "日月", "星辰",
            
            # 常见的错误识别
            "张开", "李子", "王座", "陈旧", "青虹", "那把", "这把", "一把", "几把",
        }
        
        # 🔧 修复3: 严格的黑名单检查
        # 直接匹配
        if name in invalid_words:
            return False
        
        # 前缀检查
        for invalid_word in invalid_words:
            if name.startswith(invalid_word):
                return False
        
        # 后缀检查
        invalid_suffixes = ["的", "之", "中", "上", "下", "前", "后", "时", "间", "里", "外", "内"]
        for suffix in invalid_suffixes:
            if name.endswith(suffix):
                return False
        
        # 🔧 修复4: 包含检查（避免包含无效词汇的名字）
        for invalid_word in invalid_words:
            if invalid_word in name and len(invalid_word) >= 2:
                return False
        
        # 标点符号检查（除了·和中文字符括号（））
        # 修仙小说中常见的括号用于补充说明，如"韩立（老魔）"、"古魔（主魂）"
        if any(char in name for char in "，。！？；：""''""''【】《》""，、；："):
            return False
        
        # 单个字符或纯数字检查
        if len(name) == 1 or name.isdigit():
            return False
        
        # 🔧 修复5: 更严格的描述性模式检查
        descriptive_patterns = [
            r".*的$",  # 以"的"结尾
            r".*之.*$",  # 包含"之"
            r".*中$",  # 以"中"结尾
            r".*上$",  # 以"上"结尾
            r".*下$",  # 以"下"结尾
            r".*前$",  # 以"前"结尾
            r".*后$",  # 以"后"结尾
            r".*时$",  # 以"时"结尾
            r".*间$",  # 以"间"结尾
            r".*里$",  # 以"里"结尾
            r".*外$",  # 以"外"结尾
            r".*内$",  # 以"内"结尾
            r".*[东西南北中上下左右前后].*",  # 包含方位词
        ]
        
        for pattern in descriptive_patterns:
            if re.match(pattern, name):
                return False
        
        # 🔧 修复6: 特殊模式检查（修仙小说常见错误）
        special_patterns = [
            r".*[剑刀枪戟斧钺钩叉鞭锏锤拐棒].*",  # 武器名称
            r".*[丹药丸散膏汤剂露酒茶].*",  # 药物名称
            r".*[山川湖海江河溪涧泉瀑峰岭崖谷峡].*",  # 地理名称
            r".*[金银铜铁玉石珍珠宝石翡翠玛瑙].*",  # 宝物名称
        ]
        
        for pattern in special_patterns:
            if re.match(pattern, name):
                return False
        
        return True
    
    def _is_relationship_keyword(self, text: str) -> bool:
        """判断是否为关系关键词"""
        relationship_keywords = [
            "盟友", "朋友", "对手", "敌对", "敌人", "师徒", "恋人", "合作", "冲突", "竞争",
            "结为", "成为", "是", "关系", "联系", "互动", "交往", "相处", "对峙",
            "敌我", "敌友", "同伴", "伙伴", "同事", "同门", "师兄", "师妹",
            "父子", "母子", "夫妻", "兄弟", "姐妹", "叔侄", "表兄弟"
        ]
        return any(keyword in text for keyword in relationship_keywords)
    
    def _parse_relationships_from_text(self, text: str) -> List[Dict]:
        """从文本中解析角色关系 - 🔧 修复版本，增加严格的角色验证和干扰过滤"""
        if not text or not isinstance(text, str):
            return []
        
        interactions = []
        
        # 🔧 修复1: 更严格的匹配模式，要求明确的角色名称和关系关键词
        patterns = [
            # 模式1: [角色A]和[角色B]成为[关系类型]
            r"([\u4e00-\u9fa5]{2,10})(?:和|与)([\u4e00-\u9fa5]{2,10})(?:是|为|成为)(.{0,5})(盟友|朋友|对手|敌对|敌人|师徒|恋人|合作|冲突|竞争)",
            # 模式2: [角色A]与[角色B]的[关系]
            r"([\u4e00-\u9fa5]{2,10})与([\u4e00-\u9fa5]{2,10})(?:的|之间)(.{0,10})(关系|联系|互动)",
            # 模式3: [角色A]和[角色B]发生[冲突类型]
            r"([\u4e00-\u9fa5]{2,10})(?:和|与)([\u4e00-\u9fa5]{2,10})发生(冲突|争执|矛盾)",
            # 模式4: [角色A]对[角色B]的态度
            r"([\u4e00-\u9fa5]{2,10})对([\u4e00-\u9fa5]{2,10})(?:的)?(态度|看法|印象)",
            # 模式5: [角色A]和[角色B]是[关系类型]
            r"([\u4e00-\u9fa5]{2,10})(?:和|与)([\u4e00-\u9fa5]{2,10})是(盟友|朋友|对手|敌人|师徒|恋人)"
        ]
        
        # 🔧 修复2: 预先过滤文本，移除明显的非角色内容
        filtered_text = self._filter_text_for_relationship_parsing(text)
        
        for pattern in patterns:
            for m in re.finditer(pattern, filtered_text):
                try:
                    char1 = m.group(1).strip()
                    char2 = m.group(2).strip()
                    relationship_part = m.group(3) if m.lastindex is not None and m.lastindex >= 3 else ""
                    
                    # 🔧 修复3: 双重角色名称验证
                    if not self._is_valid_character_name(char1) or not self._is_valid_character_name(char2):
                        self.logger.debug(f"   ❌ 跳过无效角色名称: {char1} 或 {char2}")
                        continue
                    
                    # 🔧 修复4: 排除物品、地点等非角色实体
                    if self._is_non_character_entity(char1) or self._is_non_character_entity(char2):
                        self.logger.debug(f"   ❌ 跳过非角色实体: {char1} 或 {char2}")
                        continue
                    
                    # 🔧 修复5: 检查角色名称是否在合理的上下文中出现
                    if not self._is_character_in_relationship_context(char1, char2, m.start(), filtered_text):
                        self.logger.debug(f"   ❌ 角色关系上下文验证失败: {char1} 和 {char2}")
                        continue
                    
                    # 提取关系类型
                    rel_type = "关系"
                    if relationship_part:
                        if "盟友" in relationship_part or "朋友" in relationship_part:
                            rel_type = "盟友"
                        elif "对手" in relationship_part or "敌对" in relationship_part or "敌人" in relationship_part:
                            rel_type = "对手"
                        elif "师徒" in relationship_part:
                            rel_type = "师徒"
                        elif "恋人" in relationship_part:
                            rel_type = "恋人"
                        elif "合作" in relationship_part:
                            rel_type = "合作"
                        elif "冲突" in relationship_part or "争执" in relationship_part:
                            rel_type = "冲突"
                        elif "关系" in relationship_part:
                            rel_type = "关系"
                        else:
                            rel_type = "未知关系"
                    
                    # 🔧 修复6: 创建交互记录（增加置信度）
                    confidence = self._calculate_relationship_confidence(char1, char2, rel_type, filtered_text)
                    
                    interaction = {
                        "characters": [char1, char2],
                        "interaction_type": rel_type,
                        "description": f"{char1}与{char2}建立{rel_type}关系",
                        "chapter": None,
                        "confidence": confidence  # 新增置信度字段
                    }
                    
                    # 🔧 修复7: 避免重复和低置信度结果
                    existing = False
                    for existing_interaction in interactions:
                        if (set(existing_interaction['characters']) == set(interaction['characters']) and
                            existing_interaction['interaction_type'] == interaction['interaction_type']):
                            # 保留置信度更高的版本
                            if interaction['confidence'] > existing_interaction.get('confidence', 0):
                                interactions.remove(existing_interaction)
                            else:
                                existing = True
                            break
                    
                    if not existing and interaction['confidence'] >= 0.5:  # 只保留置信度≥0.5的结果
                        interactions.append(interaction)
                        self.logger.debug(f"   ✅ 解析到关系: {char1} + {char2} -> {rel_type} (置信度: {confidence:.2f})")
                        
                except Exception as e:
                    # 记录错误但继续处理其他模式
                    self.logger.debug(f"   ⚠️ 解析关系时出错: {e}")
                    continue
        
        # 🔧 修复8: 更严格的已知角色配对处理
        known_characters = self._get_known_characters_from_text(filtered_text)
        if len(known_characters) >= 2:
            # 检查这些角色之间是否有明确的关系描述
            for i, char1 in enumerate(known_characters):
                for char2 in known_characters[i+1:]:
                    # 在文本中查找这两个角色的关系描述
                    relationship_patterns = [
                        f"{char1}.*?{char2}.*?(盟友|朋友|对手|敌人|师徒|恋人)",
                        f"{char2}.*?{char1}.*?(盟友|朋友|对手|敌人|师徒|恋人)",
                        f"{char1}.*?与.*?{char2}.*?(合作|冲突|竞争|互动)"
                    ]
                    
                    for pattern in relationship_patterns:
                        if re.search(pattern, filtered_text):
                            # 验证这不是物品名称的误识别
                            if not self._is_non_character_entity(char1) and not self._is_non_character_entity(char2):
                                interactions.append({
                                    "characters": [char1, char2],
                                    "interaction_type": "已知角色关系",
                                    "description": f"文本中描述{char1}与{char2}的关系",
                                    "chapter": None,
                                    "confidence": 0.8  # 已知角色的置信度较高
                                })
                                break
        
        # 🔧 修复9: 最终过滤，移除低质量结果
        filtered_interactions = []
        for interaction in interactions:
            char1, char2 = interaction['characters']
            
            # 检查角色名称是否合理
            if (len(char1) >= 2 and len(char1) <= 6 and
                len(char2) >= 2 and len(char2) <= 6 and
                not self._contains_suspicious_words(char1) and
                not self._contains_suspicious_words(char2)):
                filtered_interactions.append(interaction)
            else:
                self.logger.debug(f"   ❌ 过滤掉低质量关系: {char1} + {char2}")
        
        self.logger.info(f"🔧 关系解析完成: 从文本中解析出 {len(filtered_interactions)} 条有效关系")
        return filtered_interactions
    
    def _filter_text_for_relationship_parsing(self, text: str) -> str:
        """🔧 新增：过滤文本，移除明显的非角色内容"""
        if not text:
            return text
        
        # 移除明显的物品描述段落
        item_patterns = [
            r'.*[剑刀枪戟斧钺钩叉鞭锏锤拐棒].*?(?:斩断|击碎|挥舞|舞动|出现|消失)',
            r'.*[丹药丸散膏汤剂露酒茶].*?(?:服用|吞服|炼制|散发)',
            r'.*[金银铜铁玉石珍珠宝石翡翠玛瑙].*?(?:闪耀|发光|珍贵|罕见)',
        ]
        
        filtered_text = text
        for pattern in item_patterns:
            filtered_text = re.sub(pattern, '', filtered_text)
        
        # 移除地点描述
        location_patterns = [
            r'.*[山川湖海江河溪涧泉瀑峰岭崖谷峡].*?(?:位于|坐落|风景优美)',
            r'.*[东西南北中上下左右前后].*?(?:方向|方位|位置)',
        ]
        
        for pattern in location_patterns:
            filtered_text = re.sub(pattern, '', filtered_text)
        
        return filtered_text
    
    def _is_non_character_entity(self, name: str) -> bool:
        """🔧 新增：判断名称是否为非角色实体（物品、地点等）"""
        non_character_patterns = [
            r'.*[剑刀枪戟斧钺钩叉鞭锏锤拐棒].*$',      # 武器
            r'.*[丹药丸散膏汤剂露酒茶].*$',            # 药物
            r'.*[山川湖海江河溪涧泉瀑峰岭崖谷峡].*$',  # 地理
            r'.*[金银铜铁玉石珍珠宝石翡翠玛瑙].*$',  # 宝物
            r'.*[东西南北中上下左右前后].*$',        # 方位
        ]
        
        for pattern in non_character_patterns:
            if re.match(pattern, name):
                return True
        
        return False
    
    def _is_character_in_relationship_context(self, char1: str, char2: str, position: int, text: str) -> bool:
        """🔧 新增：检查角色名称是否在合理的关系上下文中出现"""
        # 获取匹配位置前后的文本片段
        start = max(0, position - 50)
        end = min(len(text), position + 100)
        context = text[start:end]
        
        # 检查是否包含关系相关词汇
        relationship_keywords = ["盟友", "朋友", "对手", "敌对", "敌人", "师徒", "恋人", "合作", "冲突", "竞争", "关系", "联系", "互动"]
        has_relationship_keyword = any(keyword in context for keyword in relationship_keywords)
        
        # 检查是否包含动作词汇（表明这是角色的行为）
        action_keywords = ["说", "道", "问", "答", "看", "望", "走", "来", "去", "站", "坐", "笑", "哭", "怒", "喜"]
        has_action_keyword = any(keyword in context for keyword in action_keywords)
        
        # 如果有关系关键词或动作关键词，认为上下文合理
        return has_relationship_keyword or has_action_keyword
    
    def _calculate_relationship_confidence(self, char1: str, char2: str, rel_type: str, text: str) -> float:
        """🔧 新增：计算关系解析的置信度"""
        confidence = 0.5  # 基础置信度
        
        # 角色名称长度合理性
        if 2 <= len(char1) <= 4:
            confidence += 0.1
        if 2 <= len(char2) <= 4:
            confidence += 0.1
        
        # 包含常见姓氏 - 扩展常见姓氏列表
        common_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
                          '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
                          '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
                          '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金', '石', '廖', '贾', '夏']
        if char1[0] in common_surnames:
            confidence += 0.1
        if char2[0] in common_surnames:
            confidence += 0.1
        
        # 在文本中出现频率适中
        char1_count = text.count(char1)
        char2_count = text.count(char2)
        if 1 <= char1_count <= 5:
            confidence += 0.05
        if 1 <= char2_count <= 5:
            confidence += 0.05
        
        # 关系类型的明确性
        clear_relationships = ["盟友", "朋友", "对手", "敌人", "师徒", "恋人"]
        if rel_type in clear_relationships:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _contains_suspicious_words(self, name: str) -> bool:
        """🔧 新增：检查名称是否包含可疑词汇"""
        suspicious_words = [
            "剑", "刀", "枪", "戟", "斧", "钺", "钩", "叉", "鞭", "锏", "锤", "拐", "棒",  # 武器
            "丹", "药", "丸", "散", "膏", "汤", "剂", "露", "酒", "茶",  # 药物
            "山", "川", "湖", "海", "江", "河", "溪", "涧", "泉", "瀑", "峰", "岭", "崖", "谷", "峡",  # 地理
            "金", "银", "铜", "铁", "玉", "石", "珍珠", "宝石", "翡翠", "玛瑙",  # 宝物
            "东", "西", "南", "北", "中", "上", "下", "左", "右", "前", "后",  # 方位
        ]
        
        return any(word in name for word in suspicious_words)
    
    def _get_known_characters_from_text(self, text: str, novel_title: Optional[str] = None) -> List[str]:
        """
        从文本中提取主配角名称
        
        专注于识别和返回已知的角色，特别是主要角色和重要配角，
        避免返回过多的路人角色或误识别的普通词汇。
        
        Args:
            text (str): 要分析的文本内容
            novel_title (Optional[str]): 小说标题，用于加载已知角色列表
            
        Returns:
            List[str]: 识别到的主配角名称列表，按重要性和文本中出现顺序排序
            
        Performance:
            - 时间复杂度: O(n*m) 其中n是文本长度，m是已知角色数量
            - 空间复杂度: O(k) 其中k是找到的角色数量
            - 优化：优先处理主要角色，减少不必要的文本扫描
        """
        # 输入验证
        if not text or not isinstance(text, str):
            self.logger.info("输入文本无效，返回空列表")
            return []
        
        if len(text.strip()) == 0:
            return []
            
        try:
            # 1. 加载并分类角色数据
            major_characters = set()
            minor_characters = set()
            
            if novel_title:
                # 从角色发展表加载角色，按重要性分类
                try:
                    character_development = self._load_character_development_data(novel_title)
                    for char_name, char_data in character_development.items():
                        importance = char_data.get("importance", "minor")
                        status = char_data.get("status", "active")
                        
                        # 只考虑活跃角色
                        if status in ["active", "活跃"]:
                            if importance == "major":
                                major_characters.add(char_name)
                            elif importance == "minor":
                                minor_characters.add(char_name)
                                
                    self.logger.debug(f"加载角色: 主要角色 {len(major_characters)} 个, 次要角色 {len(minor_characters)} 个")
                except Exception as e:
                    self.logger.info(f"加载角色发展表失败: {e}")
            
            # 2. 如果没有角色数据，尝试从世界状态获取
            if not major_characters and not minor_characters and novel_title:
                try:
                    world_state = self.load_previous_assessments(novel_title)
                    world_characters = world_state.get("characters", {})
                    # 将世界状态中的角色都视为次要角色
                    minor_characters.update(world_characters.keys())
                    self.logger.debug(f"从世界状态加载了 {len(world_characters)} 个角色")
                except Exception as e:
                    self.logger.info(f"加载世界状态失败: {e}")
            
            # 3. 如果仍然没有角色数据，返回空列表（不进行模式匹配，避免误识别）
            if not major_characters and not minor_characters:
                self.logger.info("未找到已知角色数据，返回空列表")
                return []
            
            # 4. 按优先级在文本中查找角色
            found_characters = []
            
            # 首先查找主要角色
            for character in major_characters:
                if self._is_character_mentioned_in_text(character, text):
                    found_characters.append(character)
                    self.logger.debug(f"找到主要角色: {character}")
            
            # 然后查找次要角色
            for character in minor_characters:
                if character not in major_characters and self._is_character_mentioned_in_text(character, text):
                    found_characters.append(character)
                    self.logger.debug(f"找到次要角色: {character}")
            
            # 5. 按在文本中的出现顺序重新排序
            ordered_characters = self._sort_characters_by_text_order(set(found_characters), text)
            
            # 6. 限制返回数量，避免返回过多角色
            max_characters = 20  # 限制最大返回数量
            final_characters = ordered_characters[:max_characters]
            
            self.logger.info(f"在文本中识别到 {len(final_characters)} 个角色 (主要: {len([c for c in final_characters if c in major_characters])}, 次要: {len([c for c in final_characters if c in minor_characters])})")
            if len(final_characters) > 0:
                self.logger.debug(f"角色列表: {final_characters}")
                
            return final_characters
            
        except Exception as e:
            self.logger.error(f"提取角色名称时发生错误: {e}")
            return []
    
    def _is_character_mentioned_in_text(self, character_name: str, text: str) -> bool:
        """
        检查角色是否在文本中被提及
        
        Args:
            character_name (str): 角色名称
            text (str): 文本内容
            
        Returns:
            bool: 是否找到角色提及
        """
        if not character_name or not text:
            return False
            
        # 直接匹配
        if character_name in text:
            return True
            
        # 模糊匹配（处理可能的变体）
        patterns = [
            rf"{character_name}",
            rf"{character_name}说",
            rf"{character_name}道",
            rf"{character_name}问",
            rf"{character_name}想",
            rf"{character_name}见",
            rf"{character_name}听",
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
                
        return False
    
    def _sort_characters_by_text_order(self, characters: set, text: str) -> List[str]:
        """
        按角色在文本中的首次出现顺序排序
        
        Args:
            characters (set): 角色名称集合
            text (str): 文本内容
            
        Returns:
            List[str]: 按出现顺序排序的角色列表
        """
        if not characters:
            return []
            
        # 记录每个角色的首次出现位置
        character_positions = {}
        
        for character in characters:
            first_pos = text.find(character)
            if first_pos != -1:
                character_positions[character] = first_pos
        
        # 按位置排序
        sorted_characters = sorted(character_positions.items(), key=lambda x: x[1])
        return [char for char, pos in sorted_characters]
    
    def _extract_potential_character_names_from_text(self, text: str) -> List[str]:
        """
        当没有已知角色数据时，从文本中提取潜在的角色名称
        
        🔧 修复版本：更加严格的角色名称提取策略
        
        Args:
            text (str): 文本内容
            
        Returns:
            List[str]: 潜在角色名称列表
        """
        potential_names = set()
        
        # 🔧 修复1: 更严格的中文姓名模式
        # 限制在常见姓氏+1-2个汉字，并排除常见的非角色词汇
        chinese_name_patterns = [
            # 精确的常见姓氏+1-2个汉字模式
            r'(?:王|李|张|刘|陈|杨|黄|赵|吴|周|徐|孙|马|朱|胡|郭|何|高|林|罗|郑|梁|谢|宋|唐|许|韩|冯|邓|曹|彭|曾|萧|田|董|袁|潘|于|蒋|蔡|余|杜|叶|程|苏|魏|吕|丁|任|沈|姚|卢|姜|崔|钟|谭|陆|汪|范|金|石|廖|贾|夏|韦|付|方|白|邹|孟|熊|秦|邱|江|尹|薛|闫|段|雷|侯|龙|史|陶|黎|贺|顾|毛|郝|龚|邵|万|钱|严|覃|武|戴|莫|孔|向|汤)[一-龥]{1,2}(?![的之而是与和在有和对把被让给为])',
            # 常见的复姓（更严格）
            r'(?:欧阳|司马|上官|东方|诸葛|司徒|夏侯|皇甫)[一-龥]{1,2}(?![的之而是与和在有和对把被让给为])',
            # 修仙小说特殊名字模式（更严格的上下文验证）
            r'([一-龥]{2,3})(?:道人|真人|仙子|神君|天尊|魔尊|剑圣|法王)(?![的之而是与在和有])',
        ]
        
        # 🔧 修复2: 增加上下文验证，避免在描述性文本中误识别
        # 检查名字是否出现在合适的上下文中
        valid_context_patterns = [
            # 说/道/问等动词前（对话语境）
            r'([一-龥]{2,4})(?:说|道|问|喝|喝道|笑道|怒道|冷声道|感叹道|说道)',
            # 动作主语
            r'([一-龥]{2,4})(?:站起身|走过来|走过去|笑了笑|皱了皱眉|点了点头|摇了摇头|转过身|抬起头|低下头)',
            # 称呼语境
            r'(?:叫|称呼|名为|名叫|名字是|是)([一-龯]{2,4})',
        ]
        
        # 提取符合严格模式的名字
        for pattern in chinese_name_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if self._is_valid_character_name(match):
                    potential_names.add(match)
        
        # 提取符合上下文模式的名字
        for pattern in valid_context_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if self._is_valid_character_name(match):
                    potential_names.add(match)
        
        # 🔧 修复3: 按可信度排序，优先返回更有可能的角色名
        def calculate_name_confidence(name):
            """计算名字的可信度分数"""
            score = 0
            # 长度适中的名字更可信
            if 2 <= len(name) <= 3:
                score += 2
            elif len(name) == 4:
                score += 1
            
            # 包含常见姓氏更可信 - 扩展常见姓氏列表
            common_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
                              '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
                              '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
                              '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金', '石', '廖', '贾', '夏']
            if name[0] in common_surnames:
                score += 2
            
            # 在文本中出现频率适中的更可信
            count = text.count(name)
            if 1 <= count <= 5:
                score += 1
            elif count > 10:
                score -= 1  # 出现太多可能是常用词
            
            return score
        
        # 按可信度排序
        scored_names = [(name, calculate_name_confidence(name)) for name in potential_names]
        scored_names.sort(key=lambda x: x[1], reverse=True)
        
        # 🔧 修复4: 更严格的数量限制，只返回高可信度的名字
        filtered_names = [name for name, score in scored_names if score > 0]
        
        return filtered_names[:5]  # 减少到最多5个，提高准确性
    def update_character_development_from_assessment(self, novel_title: str, assessment: Dict, chapter_number: int):
        """从评估结果更新角色发展表 - 根据角色重要性区分处理"""
        character_development = assessment.get("character_development_assessment", {})
        # 如果评估没有返回结构化的 character_interactions 或 relationship 信息，尝试从评估的文本摘要中解析
        if (not character_development or not character_development.get("character_interactions") and not character_development.get("iconic_scenes_identified")):
            # 尝试从assessment里收集文本并解析关系
            text_blob = ""
            # 优先使用明确提供的文本字段
            dev_text = assessment.get('character_development_text')
            if dev_text and isinstance(dev_text, str) and len(dev_text) > 20:
                text_blob = assessment.get('character_development_text')
            else:
                # 否则从整个assessment深度收集可用文本片段
                text_blob = self._gather_text_from_assessment(assessment)
            if text_blob:
                parsed_interactions = self._parse_relationships_from_text(text_blob)
                if parsed_interactions:
                    self.logger.info(f"🔧 从文本后处理解析出 {len(parsed_interactions)} 条人物交互，准备回填到 character_development 中。")
                    if not isinstance(character_development, dict):
                        character_development = {}
                    # 将解析结果注入到character_development的兼容字段中
                    character_development.setdefault('character_interactions', [])
                    # 转换为内部期望的结构：每项包含 characters + interaction_type
                    for inter in parsed_interactions:
                        character_development['character_interactions'].append({
                            'characters': inter.get('characters', []),
                            'interaction_type': inter.get('interaction_type', ''),
                            'description': inter.get('description', '')
                        })
                    # 将解析到的交互写回 assessment，方便后续步骤也能使用
                    assessment['character_development_assessment'] = character_development
        # 处理新角色
        for new_char in character_development.get("new_characters_introduced", []):
            char_name = new_char["name"]
            role_type = new_char.get("role_type", "次要配角")
            # 构建基础角色数据
            character_data = {
                "name": char_name,
                "role_type": role_type
            }
            # 评估角色重要性
            importance = self.assess_character_importance(character_data)
            # 根据重要性构建不同的数据
            if importance == "major":
                # 重要角色：保存完整信息
                character_data.update({
                    "personality_traits": {
                        "core_traits": [new_char.get("initial_impression", "待完善")],
                        "contradictions": "待发掘",
                        "behavior_patterns": "待观察", 
                        "speech_style": "待定义"
                    },
                    # ... 其他完整字段
                })
            elif importance == "minor":
                # 次要角色：保存基本信息
                character_data.update({
                    "basic_description": new_char.get("initial_impression", "待完善"),
                    "purpose_in_story": "推动情节发展"
                })
            else:
                # 未命名角色：极简信息
                character_data.update({
                    "appearance_context": "在场景中出现"
                })
            self.manage_character_development_table(novel_title, character_data, chapter_number, "add")
        # 处理名场面
        for scene in character_development.get("iconic_scenes_identified", []):
            char_name = scene["character"]
            self.manage_character_development_table(novel_title, {
                "name": char_name,
                "iconic_scenes": [{
                    "scene_type": "性格展示/情感爆发/高光时刻",
                    "chapter": scene.get("chapter", chapter_number),
                    "description": scene["scene_description"],
                    "purpose": scene["trait_demonstrated"],
                    "impact_level": scene.get("impact_level", "中")
                }]
            }, chapter_number, "update")
        # 处理性格揭示
        for revelation in character_development.get("personality_revelations", []):
            char_name = revelation["character"]
            self.manage_character_development_table(novel_title, {
                "name": char_name,
                "personality_traits": {
                    "core_traits": [revelation["trait_revealed"]]
                }
            }, chapter_number, "update")
        # 处理角色互动和关系发展
        for interaction in character_development.get("character_interactions", []):
            characters = interaction.get("characters", [])
            for char_name in characters:
                # 更新角色的关系网络
                relationship_type = "allies" if "合作" in interaction.get("interaction_type", "") else "rivals"
                other_chars = [c for c in characters if c != char_name]
                if other_chars:
                    self.manage_character_development_table(novel_title, {
                        "name": char_name,
                        "relationship_network": {
                            relationship_type: other_chars
                        }
                    }, chapter_number, "update")
    def cleanup_characters_by_strategy(self, novel_title: str, strategy_config: Dict) -> Dict:
        """根据策略清理角色数据 - 智能版本"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return {"cleaned_count": 0, "remaining_count": 0, "error": "角色文件不存在"}
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            # 统计清理前的角色数量
            total_before = len(characters)
            importance_counts_before = self._count_characters_by_importance(characters)
            # 应用清理策略
            keep_major_only = strategy_config.get("keep_major_only", False)
            preserve_recent = strategy_config.get("preserve_recent_chapters", 5)
            current_chapter = strategy_config.get("current_chapter", 1)
            stage_type = strategy_config.get("stage_type", "normal")
            characters_after_cleanup = {}
            for char_name, char_data in characters.items():
                if self._should_keep_character(char_data, keep_major_only, preserve_recent, current_chapter, stage_type):
                    # 根据策略简化角色数据
                    simplified_data = self._simplify_character_data(char_data, strategy_config)
                    characters_after_cleanup[char_name] = simplified_data
            # 保存清理后的数据
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(characters_after_cleanup, f, ensure_ascii=False, indent=2)
            # 统计清理后的角色数量
            total_after = len(characters_after_cleanup)
            importance_counts_after = self._count_characters_by_importance(characters_after_cleanup)
            result = {
                "cleaned_count": total_before - total_after,
                "remaining_count": total_after,
                "importance_distribution_before": importance_counts_before,
                "importance_distribution_after": importance_counts_after,
                "strategy_used": strategy_config
            }
            self.logger.info(f"✅ 策略清理完成: 清理了 {result['cleaned_count']} 个角色，剩余 {total_after} 个角色")
            return result
        except Exception as e:
            self.logger.info(f"❌ 策略清理失败: {e}")
            return {"cleaned_count": 0, "remaining_count": 0, "error": str(e)}
    def _should_keep_character(self, char_data: Dict, keep_major_only: bool, preserve_recent: int, 
                            current_chapter: int, stage_type: str) -> bool:
        """判断是否应该保留角色"""
        importance = char_data.get("importance", "minor")
        status = char_data.get("status", "active")
        # 已死亡或退场的角色总是保留极简信息
        if status in ["dead", "exited"]:
            return True
        # 重要角色总是保留
        if importance == "major":
            return True
        # 如果策略要求只保留重要角色
        if keep_major_only:
            return False
        # 检查角色是否最近活跃
        last_updated = char_data.get("last_updated_chapter", 0)
        if current_chapter - last_updated <= preserve_recent:
            return True
        # 根据阶段类型决定保留策略
        if stage_type == "opening" and importance == "minor":
            # 开局阶段保留所有次要角色
            return True
        elif stage_type == "climax" and importance == "unnamed":
            # 高潮阶段不保留未命名角色
            return False
        elif stage_type == "ending" and importance != "major":
            # 结局阶段只保留重要角色
            return False
        # 默认保留
        return True
    def _simplify_character_data(self, char_data: Dict, strategy_config: Dict) -> Dict:
        """根据策略简化角色数据"""
        importance = char_data.get("importance", "minor")
        stage_type = strategy_config.get("stage_type", "normal")
        # 基础保留字段
        base_fields = {
            "name", "status", "role_type", "importance", 
            "first_appearance_chapter", "last_updated_chapter", "total_appearances"
        }
        simplified_data = {field: char_data[field] for field in base_fields if field in char_data}
        # 根据重要性和阶段类型决定保留哪些额外字段
        if importance == "major":
            # 重要角色保留完整信息
            preserved_fields = [
                "personality_traits", "background_story", "relationship_network",
                "development_milestones", "iconic_scenes", "development_status"
            ]
            for field in preserved_fields:
                if field in char_data:
                    simplified_data[field] = char_data[field]
        elif importance == "minor":
            # 次要角色根据阶段类型决定保留程度
            if stage_type in ["opening", "development"]:
                # 开局和发展阶段保留基本信息
                simplified_data["basic_description"] = char_data.get("basic_description", "角色基本描述")
                simplified_data["purpose_in_story"] = char_data.get("purpose_in_story", "推动情节发展")
            else:
                # 其他阶段进一步简化
                simplified_data["basic_description"] = char_data.get("basic_description", "角色基本描述")[:50] + "..."
        else:  # unnamed
            # 未命名角色总是极简
            simplified_data["appearance_context"] = char_data.get("appearance_context", "在场景中出现")
        return simplified_data
    def _count_characters_by_importance(self, characters: Dict) -> Dict:
        """统计角色按重要性的分布"""
        counts = {"major": 0, "minor": 0, "unnamed": 0}
        for char_data in characters.values():
            importance = char_data.get("importance", "minor")
            if importance in counts:
                counts[importance] += 1
        return counts
    def get_novel_consistency_report(self, novel_title: str) -> Dict:
        """获取小说的整体一致性报告"""
        world_state_file = os.path.join(self.storage_path, f"{novel_title}_world_state.json")
        if not os.path.exists(world_state_file):
            return {"error": "未找到该小说的世界状态数据"}
        try:
            with open(world_state_file, 'r', encoding='utf-8') as f:
                world_state = json.load(f)
            # 分析世界状态
            characters_count = len(world_state.get('characters', {}))
            items_count = len(world_state.get('items', {}))
            relationships_count = len(world_state.get('relationships', {}))
            skills_count = len(world_state.get('skills', {}))
            locations_count = len(world_state.get('locations', {}))
            return {
                "novel_title": novel_title,
                "world_state_summary": {
                    "characters": characters_count,
                    "items": items_count,
                    "relationships": relationships_count,
                    "skills": skills_count,
                    "locations": locations_count
                },
                "consistency_score": self._calculate_overall_consistency(world_state),
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": f"生成一致性报告失败: {e}"}
    def _calculate_overall_consistency(self, world_state: Dict) -> float:
        """计算整体一致性分数"""
        # 简化的计算方法，实际可以根据具体需求调整
        total_elements = 0
        consistency_score = 0
        for category, elements in world_state.items():
            for element_id, element_data in elements.items():
                total_elements += 1
                # 检查元素是否有完整的更新记录
                if element_data.get('last_updated'):
                    consistency_score += 1
        return round(consistency_score / max(total_elements, 1) * 10, 2) if total_elements > 0 else 10.0
    def get_characters_cultivation_info(self, novel_title: str, character_names: Optional[List[str]] = None) -> Dict[str, str]:
        """获取角色的修为信息，用于生成前情提要"""
        world_state = self.load_previous_assessments(novel_title)
        if not world_state:
            return {}
        characters = world_state.get("characters", {})
        cultivation_info = {}
        for char_name, char_data in characters.items():
            # 如果指定了特定角色，只返回这些角色的信息
            if character_names and char_name not in character_names:
                continue
            attributes = char_data.get("attributes", {})
            cultivation_level = attributes.get("cultivation_level")
            if cultivation_level:
                cultivation_info[char_name] = cultivation_level
        return cultivation_info
    def get_character_comprehensive_status(self, novel_title: str, character_names: Optional[List[str]] = None) -> Dict:
        """获取角色综合状态信息（修为+功法+关系+物品+心理状态）"""
        world_state = self.load_previous_assessments(novel_title)
        character_development = self._load_character_development_data(novel_title)
        if not world_state and not character_development:
            return {}
        comprehensive_status = {}
        # 处理指定角色或所有角色
        all_characters = set()
        if character_names:
            all_characters.update(character_names)
        else:
            # 获取所有活跃的重要角色
            for char_name, char_data in character_development.items():
                if char_data.get("importance") == "major" and char_data.get("status") == "active":
                    all_characters.add(char_name)
        for char_name in all_characters:
            char_status = {
                "basic_info": {},
                "cultivation_info": {},
                "skills": [],
                "relationships": [],
                "items": [],
                "mental_state": {},
                "recent_development": {}
            }
            # 1. 基础信息
            char_data = character_development.get(char_name, {})
            char_status["basic_info"] = {
                "name": char_name,
                "role_type": char_data.get("role_type", ""),
                "importance": char_data.get("importance", "minor"),
                "status": char_data.get("status", "active"),
                "total_appearances": char_data.get("total_appearances", 1),
                "last_updated_chapter": char_data.get("last_updated_chapter", 1)
            }
            # 2. 修为信息
            world_char_data = world_state.get("characters", {}).get(char_name, {})
            attributes = world_char_data.get("attributes", {})
            char_status["cultivation_info"] = {
                "level": attributes.get("cultivation_level", "未知"),
                "system": attributes.get("cultivation_system", "未知"),
                "location": attributes.get("location", "未知"),
                "faction": attributes.get("faction", ""),
                "title": attributes.get("title", "")
            }
            # 3. 功法技能
            cultivation_skills = world_state.get("cultivation_skills", {})
            for skill_name, skill_data in cultivation_skills.items():
                if skill_data.get("owner") == char_name:
                    char_status["skills"].append({
                        "name": skill_name,
                        "type": skill_data.get("type", ""),
                        "level": skill_data.get("level", ""),
                        "quality": skill_data.get("quality", ""),
                        "description": skill_data.get("description", "")[:100] + "..." if len(skill_data.get("description", "")) > 100 else skill_data.get("description", "")
                    })
            # 4. 人际关系
            # 从角色发展数据中获取
            dev_relationships = char_data.get("relationship_network", {})
            char_status["relationships"].extend([
                {"type": "盟友", "character": ally, "status": "active"} 
                for ally in dev_relationships.get("allies", [])
            ])
            char_status["relationships"].extend([
                {"type": "对手", "character": rival, "status": "active"} 
                for rival in dev_relationships.get("rivals", [])
            ])
            # 从世界状态中获取
            world_relationships = world_state.get("relationships", {})
            for rel_key, rel_data in world_relationships.items():
                if char_name in rel_key:
                    other_char = rel_key.replace(f"{char_name}-", "").replace(f"-{char_name}", "")
                    char_status["relationships"].append({
                        "type": rel_data.get("type", ""),
                        "character": other_char,
                        "description": rel_data.get("description", ""),
                        "status": rel_data.get("status", "active")
                    })
            # 5. 物品装备
            cultivation_items = world_state.get("cultivation_items", {})
            for item_name, item_data in cultivation_items.items():
                if item_data.get("owner") == char_name:
                    char_status["items"].append({
                        "name": item_name,
                        "type": item_data.get("type", ""),
                        "quality": item_data.get("quality", ""),
                        "status": item_data.get("status", ""),
                        "description": item_data.get("description", "")[:100] + "..." if len(item_data.get("description", "")) > 100 else item_data.get("description", "")
                    })
            # 6. 心理状态
            personality = char_data.get("personality_traits", {})
            char_status["mental_state"] = {
                "core_traits": personality.get("core_traits", []),
                "contradictions": personality.get("contradictions", ""),
                "behavior_patterns": personality.get("behavior_patterns", ""),
                "speech_style": personality.get("speech_style", ""),
                "recent_emotional_state": self._infer_recent_emotional_state(char_data, world_char_data)
            }
            # 7. 近期发展
            char_status["recent_development"] = {
                "milestones": char_data.get("development_milestones", [])[-3:],  # 最近3个里程碑
                "iconic_scenes": char_data.get("iconic_scenes", [])[-2:],  # 最近2个名场面
                "growth_trajectory": self._assess_growth_trajectory(char_data)
            }
            comprehensive_status[char_name] = char_status
        return comprehensive_status
    def _infer_recent_emotional_state(self, char_data: Dict, world_char_data: Dict) -> str:
        """推断角色近期情绪状态"""
        # 基于角色发展和最近事件推断情绪状态
        milestones = char_data.get("development_milestones", [])
        attributes = world_char_data.get("attributes", {})
        if not milestones:
            return "平稳"
        recent_milestone = milestones[-1] if milestones else {}
        milestone_type = recent_milestone.get("type", "")
        emotional_map = {
            "突破": "兴奋",
            "获得宝物": "喜悦", 
            "战斗胜利": "振奋",
            "亲友死亡": "悲伤",
            "失败": "沮丧",
            "背叛": "愤怒",
            "奇遇": "惊喜"
        }
        return emotional_map.get(milestone_type, "平稳")
    def _assess_growth_trajectory(self, char_data: Dict) -> str:
        """评估角色成长轨迹"""
        milestones = char_data.get("development_milestones", [])
        total_appearances = char_data.get("total_appearances", 1)
        if len(milestones) == 0:
            return "平稳发展"
        recent_milestones = milestones[-min(3, len(milestones)):]
        positive_events = sum(1 for m in recent_milestones if m.get("type") in ["突破", "获得宝物", "战斗胜利", "奇遇"])
        if positive_events >= 2:
            return "快速成长"
        elif positive_events >= 1:
            return "稳步提升"
        else:
            return "面临挑战"
    def update_character_mental_state(self, novel_title: str, character_name: str, 
                                    mental_data: Dict, chapter_number: int):
        """更新角色心理状态"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            if character_name not in characters:
                return
            # 初始化心理状态记录
            if "mental_state_records" not in characters[character_name]:
                characters[character_name]["mental_state_records"] = []
            # 添加新的心理状态记录
            mental_record = {
                "chapter": chapter_number,
                "timestamp": datetime.now().isoformat(),
                **mental_data
            }
            characters[character_name]["mental_state_records"].append(mental_record)
            # 只保留最近10条记录
            characters[character_name]["mental_state_records"] = \
                characters[character_name]["mental_state_records"][-10:]
            # 更新当前心理状态摘要
            characters[character_name]["current_mental_state"] = {
                "emotional_state": mental_data.get("emotional_state", "平静"),
                "main_motivation": mental_data.get("motivation", ""),
                "internal_conflict": mental_data.get("internal_conflict", ""),
                "last_updated": chapter_number
            }
            with open(character_file, 'w', encoding='utf-8') as f:
                json.dump(characters, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.info(f"更新角色心理状态失败: {e}")
    def get_character_mental_timeline(self, novel_title: str, character_name: str) -> List[Dict]:
        """获取角色心理状态时间线"""
        character_file = os.path.join(self.storage_path, f"{novel_title}_character_development.json")
        if not os.path.exists(character_file):
            return []
        try:
            with open(character_file, 'r', encoding='utf-8') as f:
                characters = json.load(f)
            if character_name not in characters:
                return []
            return characters[character_name].get("mental_state_records", [])
        except Exception as e:
            self.logger.info(f"获取角色心理时间线失败: {e}")
            return []        
    def validate_and_clean_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """验证和清理关系数据，消除矛盾"""
        cleaned_relationships = []
        relationship_map = {}  # 按对方角色分组
        # 按对方角色分组关系
        for rel in relationships:
            other_char = rel.get("character")
            if other_char not in relationship_map:
                relationship_map[other_char] = []
            relationship_map[other_char].append(rel)
        # 合并和清理矛盾关系
        for other_char, rel_list in relationship_map.items():
            if len(rel_list) == 1:
                # 单一关系，直接保留
                cleaned_relationships.append(rel_list[0])
            else:
                # 多个关系，需要合并
                merged_rel = self._merge_relationships(rel_list)
                cleaned_relationships.append(merged_rel)
        return cleaned_relationships
    def _merge_relationships(self, rel_list: List[Dict]) -> Dict:
        """合并多个关系类型"""
        base_rel = rel_list[0].copy()
        all_types = []
        for rel in rel_list:
            rel_type = rel.get("type", "")
            if rel_type and rel_type not in all_types:
                all_types.append(rel_type)
        # 处理矛盾关系
        if "对手" in all_types and "师徒" in all_types:
            # 师徒兼对手 -> 改为"竞争师徒"
            base_rel["type"] = "竞争师徒"
            base_rel["description"] = "既是师徒又存在竞争关系的复杂关系"
        elif "对手" in all_types and "敌对" in all_types:
            # 对手和敌对 -> 合并为"敌对"
            base_rel["type"] = "敌对"
        else:
            # 其他情况用顿号连接
            base_rel["type"] = "、".join(all_types)
        return base_rel
    def enhance_location_descriptions(self, novel_title: str, character_status: Dict) -> Dict:
        """增强位置描述的可读性"""
        enhanced_status = character_status.copy()
        for char_name, status in enhanced_status.items():
            location = status["cultivation_info"].get("location", "")
            if "途中" in location:
                # 解析途中状态
                if "内门天字号洞府" in location and char_name == "林凡":
                    status["cultivation_info"]["location"] = "前往内门天字号洞府的途中"
                    status["cultivation_info"]["movement"] = "正在移动"
                elif "后山" in location and char_name == "王二牛":
                    status["cultivation_info"]["location"] = "后山追踪路径上"
                    status["cultivation_info"]["movement"] = "追踪状态"
            # 添加位置状态
            current_location = status["cultivation_info"]["location"]
            if any(word in current_location for word in ["途中", "追踪", "移动"]):
                status["cultivation_info"]["location_status"] = "移动中"
            else:
                status["cultivation_info"]["location_status"] = "静止"
        return enhanced_status
    def infer_emotional_state_enhanced(self, char_data: Dict, world_char_data: Dict, novel_title: str) -> str:
        """通用情绪状态推断模板 - 基于角色状态和描述分析"""
        # 如果数据为空，返回默认值
        if not char_data and not world_char_data:
            return "未知"
        attributes = world_char_data.get("attributes", {}) if world_char_data else {}
        description = world_char_data.get("description", "") if world_char_data else ""
        character_name = attributes.get("name", "")
        # 1. 基于角色状态的直接推断
        status = attributes.get("status", "活跃")
        status_emotion_map = {
            "死亡": "终结", "重伤": "痛苦", "重伤昏迷": "昏迷", "失踪": "迷茫",
            "濒死": "绝望", "被囚": "压抑", "逃亡": "恐惧"
        }
        if status in status_emotion_map:
            return status_emotion_map[status]
        # 2. 基于描述文本的情感关键词分析
        description_lower = description.lower() if description else ""
        # 积极情绪关键词（权重从高到低）
        strong_positive = ["喜悦", "兴奋", "激动", "狂喜", "满足", "得意"]
        moderate_positive = ["高兴", "愉悦", "欣慰", "安心", "平静", "专注"]
        weak_positive = ["满意", "期待", "好奇", "悠闲"]
        # 消极情绪关键词（权重从高到低）
        strong_negative = ["愤怒", "暴怒", "绝望", "恐惧", "恐慌", "痛苦"]
        moderate_negative = ["沮丧", "失望", "焦虑", "紧张", "屈辱", "震惊"]
        weak_negative = ["不满", "担忧", "困惑", "疲惫"]
        # 复杂情绪关键词
        complex_emotions = ["深邃", "内敛", "隐忍", "坚定", "决绝", "矛盾"]
        # 检查描述中的关键词（按权重顺序）
        for keyword in strong_positive:
            if keyword in description_lower:
                return keyword
        for keyword in strong_negative:
            if keyword in description_lower:
                return keyword
        for keyword in moderate_positive:
            if keyword in description_lower:
                return keyword
        for keyword in moderate_negative:
            if keyword in description_lower:
                return keyword
        for keyword in complex_emotions:
            if keyword in description_lower:
                return keyword
        for keyword in weak_positive:
            if keyword in description_lower:
                return keyword
        for keyword in weak_negative:
            if keyword in description_lower:
                return keyword
        # 3. 基于情境的推断
        current_location = attributes.get("location", "")
        # 战斗/危险情境
        if any(word in description_lower for word in ["战斗", "厮杀", "危险", "危机", "追杀"]):
            return "紧张"
        # 突破/成长情境
        if any(word in description_lower for word in ["突破", "晋升", "领悟", "炼化", "成功"]):
            return "兴奋"
        # 失败/挫折情境
        if any(word in description_lower for word in ["失败", "羞辱", "嘲讽", "退婚", "休书"]):
            return "愤怒"
        # 安全/修炼情境
        if any(word in description_lower for word in ["闭关", "修炼", "安宁", "踏实", "安全"]):
            return "平静"
        # 4. 基于位置的推断
        location_emotion_map = {
            "战场": "紧张", "前线": "警惕", "思过崖": "反思", 
            "藏经阁": "专注", "宗门大殿": "严肃", "房梁": "悠闲"
        }
        for location_keyword, emotion in location_emotion_map.items():
            if location_keyword in current_location:
                return emotion
        # 5. 默认情绪基于角色活跃状态
        if status == "活跃":
            return "平静"  # 默认活跃角色为平静
        else:
            return "未知"
    def _get_character_relationships(self, character_name: str, novel_title: str) -> List[Dict]:
        """获取角色关系"""
        character_development = self._load_character_development_data(novel_title)
        char_data = character_development.get(character_name, {})
        relationships = char_data.get("relationship_network", {})
        rel_list = []
        rel_list.extend([{"type": "盟友", "character": ally} for ally in relationships.get("allies", [])])
        rel_list.extend([{"type": "对手", "character": rival} for rival in relationships.get("rivals", [])])
        return rel_list  
    def get_character_comprehensive_status_enhanced(self, novel_title: str, character_names: Optional[List[str]] = None) -> Dict:
        """增强版角色综合状态获取 - 修复版本，合并死亡角色"""
        self.logger.info(f"🔄 开始获取增强版角色综合状态...")
        self.logger.info(f"   小说: {novel_title}")
        self.logger.info(f"   指定角色: {character_names if character_names else '全部角色'}")
        # 1. 首先获取基础状态
        basic_status = self.get_character_comprehensive_status(novel_title, character_names)
        if not basic_status:
            self.logger.info("⚠️ 基础状态为空，尝试从世界状态直接构建...")
            basic_status = self._build_comprehensive_status_from_world_state(novel_title, character_names)
        self.logger.info(f"✅ 获取到基础状态，角色数量: {len(basic_status)}")
        # 2. 合并死亡角色
        self.logger.info("🔄 合并死亡角色...")
        merged_status = self._merge_dead_characters(basic_status)
        # 3. 清理关系矛盾
        self.logger.info("🔄 清理关系矛盾...")
        for char_name, status in merged_status.items():
            if "relationships" in status:
                original_count = len(status["relationships"])
                status["relationships"] = self.validate_and_clean_relationships(status["relationships"])
                cleaned_count = len(status["relationships"])
                if original_count != cleaned_count:
                    self.logger.info(f"   清理 {char_name} 的关系: {original_count} -> {cleaned_count}")
        # 4. 增强位置描述
        self.logger.info("🔄 增强位置描述...")
        enhanced_status = self.enhance_location_descriptions(novel_title, merged_status)
        # 5. 更新情绪状态
        self.logger.info("🔄 更新情绪状态...")
        world_state = self.load_previous_assessments(novel_title)
        character_development = self._load_character_development_data(novel_title)
        for char_name, status in enhanced_status.items():
            char_data = character_development.get(char_name, {})
            world_char_data = world_state.get("characters", {}).get(char_name, {})
            # 确保传递正确的参数
            emotional_state = self.infer_emotional_state_enhanced(char_data, world_char_data, novel_title)
            status["mental_state"]["recent_emotional_state"] = emotional_state
        self.logger.info(f"🎉 增强版角色状态获取完成: {len(enhanced_status)} 个角色 (合并后)")
        return enhanced_status
    def _merge_dead_characters(self, character_status: Dict) -> Dict:
        """合并死亡角色，减少角色数量"""
        alive_characters = {}
        dead_characters = []
        self.logger.info(f"  🔍 开始合并死亡角色，原始数量: {len(character_status)}")
        for char_name, status in character_status.items():
            char_status = status.get("basic_info", {}).get("status", "活跃")
            if char_status in ["死亡", "dead", "阵亡", "牺牲"]:
                dead_characters.append(char_name)
                self.logger.info(f"   标记为死亡角色: {char_name}")
            else:
                alive_characters[char_name] = status
                self.logger.info(f"   活跃角色: {char_name} - {char_status}")
        # 如果有死亡角色，创建合并条目
        if dead_characters:
            # 限制死亡角色显示数量，避免过长
            if len(dead_characters) > 10:
                display_dead = dead_characters[:10] + [f"等{len(dead_characters)-10}个角色"]
            else:
                display_dead = dead_characters
            dead_names = "、".join(display_dead)
            alive_characters["已死亡角色"] = {
                "basic_info": {
                    "name": dead_names,
                    "status": "死亡",
                    "role_type": "已故角色",
                    "importance": "minor",
                    "total_appearances": 0,
                    "last_updated_chapter": 0
                },
                "cultivation_info": {
                    "level": "已故",
                    "system": "无",
                    "location": "已故",
                    "faction": "无",
                    "title": "已故角色"
                },
                "skills": [],
                "relationships": [],
                "items": [],
                "mental_state": {
                    "core_traits": ["已故"],
                    "contradictions": "",
                    "behavior_patterns": "",
                    "speech_style": "",
                    "recent_emotional_state": "终结"
                },
                "recent_development": {
                    "milestones": [{"description": "角色已死亡", "chapter": 0}],
                    "iconic_scenes": [],
                    "growth_trajectory": "已故"
                }
            }
            self.logger.info(f"  ✅ 合并死亡角色: {len(dead_characters)} 个 -> 1 个条目")
            self.logger.info(f"     死亡角色列表: {dead_names}")
        self.logger.info(f"  📊 角色统计: 活跃 {len(alive_characters)} 个, 死亡 {len(dead_characters)} 个")
        return alive_characters
    def _build_comprehensive_status_from_world_state(self, novel_title: str, character_names: Optional[List[str]] = None) -> Dict:
        """从世界状态直接构建综合状态（备用方法）"""
        world_state = self.load_previous_assessments(novel_title)
        character_development = self._load_character_development_data(novel_title)
        if not world_state:
            self.logger.info("❌ 世界状态为空，无法构建综合状态")
            return {}
        comprehensive_status = {}
        characters_data = world_state.get("characters", {})
        # 确定要处理的角色
        target_characters = character_names if character_names else list(characters_data.keys())
        for char_name in target_characters:
            if char_name not in characters_data:
                self.logger.info(f"⚠️ 角色 {char_name} 不在世界状态中，跳过")
                continue
            char_data = characters_data[char_name]
            dev_data = character_development.get(char_name, {})
            attributes = char_data.get("attributes", {})
            # 使用增强的情绪推断
            emotional_state = self.infer_emotional_state_enhanced(dev_data, char_data, novel_title)
            # 构建综合状态
            char_status = {
                "basic_info": {
                    "name": char_name,
                    "role_type": attributes.get("occupation", ""),
                    "importance": dev_data.get("importance", "minor"),
                    "status": attributes.get("status", "active"),
                    "total_appearances": dev_data.get("total_appearances", 1),
                    "last_updated_chapter": dev_data.get("last_updated_chapter", 1)
                },
                "cultivation_info": {
                    "level": attributes.get("cultivation_level", "未知"),
                    "system": attributes.get("cultivation_system", "未知"),
                    "location": attributes.get("location", "未知"),
                    "faction": attributes.get("faction", ""),
                    "title": attributes.get("title", "")
                },
                "skills": self._get_character_skills_from_world_state(world_state, char_name),
                "relationships": self._get_character_relationships_from_world_state(world_state, char_name),
                "items": self._get_character_items_from_world_state(world_state, char_name),
                "mental_state": {
                    "core_traits": dev_data.get("personality_traits", {}).get("core_traits", []),
                    "contradictions": dev_data.get("personality_traits", {}).get("contradictions", ""),
                    "behavior_patterns": dev_data.get("personality_traits", {}).get("behavior_patterns", ""),
                    "speech_style": dev_data.get("personality_traits", {}).get("speech_style", ""),
                    "recent_emotional_state": emotional_state  # 使用推断的情绪状态
                },
                "recent_development": {
                    "milestones": dev_data.get("development_milestones", [])[-3:],
                    "iconic_scenes": dev_data.get("iconic_scenes", [])[-2:],
                    "growth_trajectory": self._assess_growth_trajectory(dev_data)
                }
            }
            comprehensive_status[char_name] = char_status
            self.logger.info(f"✅ 从世界状态构建: {char_name} -> 情绪: {emotional_state}")
        return comprehensive_status
    def _get_character_skills_from_world_state(self, world_state: Dict, character_name: str) -> List[Dict]:
        """从世界状态获取角色技能"""
        skills = []
        cultivation_skills = world_state.get("cultivation_skills", {})
        for skill_name, skill_data in cultivation_skills.items():
            if skill_data.get("owner") == character_name:
                skills.append({
                    "name": skill_name,
                    "type": skill_data.get("type", ""),
                    "level": skill_data.get("level", ""),
                    "quality": skill_data.get("quality", ""),
                    "description": skill_data.get("description", "")[:100] + "..." if len(skill_data.get("description", "")) > 100 else skill_data.get("description", "")
                })
        return skills
    def _get_character_relationships_from_world_state(self, world_state: Dict, character_name: str) -> List[Dict]:
        """从世界状态获取角色关系"""
        relationships = []
        world_relationships = world_state.get("relationships", {})
        for rel_key, rel_data in world_relationships.items():
            if character_name in rel_key:
                # 提取关系中的另一个角色
                parts = rel_key.split('-')
                if len(parts) == 2:
                    other_char = parts[0] if parts[1] == character_name else parts[1]
                    relationships.append({
                        "type": rel_data.get("type", ""),
                        "character": other_char,
                        "description": rel_data.get("description", ""),
                        "status": rel_data.get("status", "active")
                    })
        return relationships
    def _get_character_items_from_world_state(self, world_state: Dict, character_name: str) -> List[Dict]:
        """从世界状态获取角色物品"""
        items = []
        cultivation_items = world_state.get("cultivation_items", {})
        for item_name, item_data in cultivation_items.items():
            if item_data.get("owner") == character_name:
                items.append({
                    "name": item_name,
                    "type": item_data.get("type", ""),
                    "quality": item_data.get("quality", ""),
                    "status": item_data.get("status", ""),
                    "description": item_data.get("description", "")[:100] + "..." if len(item_data.get("description", "")) > 100 else item_data.get("description", "")
                })
        return items
    def validate_money_consistency(self, novel_title: str, chapter_number: int, changes: Dict) -> List[Dict]:
        """验证金钱变化的一致性 - 修复版，支持非交易性金钱变化"""
        consistency_issues = []
        # 加载之前的世界状态
        previous_state = self.load_previous_assessments(novel_title)
        if not previous_state:
            return consistency_issues
        characters_changes = changes.get('characters', {})
        economy_changes = changes.get('economy', {})
        # 处理列表类型的 economy_changes
        if isinstance(economy_changes, list):
            economy_changes_dict = {}
            for i, transaction in enumerate(economy_changes):
                if isinstance(transaction, dict):
                    economy_changes_dict[f"transaction_{i}"] = transaction
            economy_changes = economy_changes_dict
        # 检查每个角色的金钱变化
        for char_name, char_data in characters_changes.items():
            attributes = char_data.get('attributes', {})
            # 只检查金钱发生变化的角色
            if 'money' not in attributes:
                continue
            # --- 核心逻辑重构开始 ---
            # 安全地获取新旧金钱数值
            new_money = attributes.get('money')
            if new_money is None: continue
            try:
                new_money = float(new_money)
            except (TypeError, ValueError):
                continue
            prev_char = previous_state.get('characters', {}).get(char_name, {})
            prev_attributes = prev_char.get('attributes', {})
            prev_money = prev_attributes.get('money', 0)
            try:
                prev_money = float(prev_money if prev_money is not None else 0)
            except (TypeError, ValueError):
                prev_money = 0
            # 1. 计算金钱总变化量
            money_change = new_money - prev_money
            if abs(money_change) < 0.01: # 变化太小，忽略
                continue
            # 2. 计算所有相关交易导致的变化量
            related_transactions = self._find_related_transactions(char_name, economy_changes, money_change)
            total_transaction_amount = 0
            for transaction in related_transactions:
                amount = transaction.get('amount', 0)
                try:
                    amount = float(amount if amount is not None else 0)
                except (TypeError, ValueError):
                    amount = 0
                if transaction.get('to_character') == char_name:
                    total_transaction_amount += amount
                elif transaction.get('from_character') == char_name:
                    total_transaction_amount -= amount
            # 3. 计算无法被交易记录解释的差额
            unexplained_change = money_change - total_transaction_amount
            # 4. 检查无法解释的差额是否合理
            # 如果差额大于一个很小的值 (例如0.01)，说明存在无法解释的金钱变化
            if abs(unexplained_change) > 0.01:
                # 检查AI是否为这个无法解释的变化提供了“原因说明”
                if 'money_change_reason' in attributes and attributes['money_change_reason']:
                    # 如果有原因说明，我们认为这是合理的非交易性变化，通过检查
                    self.logger.info(f"   - 角色 {char_name} 的金钱变化被解释为: '{attributes['money_change_reason']}'，验证通过。")
                else:
                    # 如果没有原因说明，这才是真正的一致性问题
                    consistency_issues.append({
                        "type": "MONEY_CONSISTENCY",
                        "character": char_name,
                        "description": f"{char_name}的金钱从{prev_money}变为{new_money}(变化:{money_change})，但交易记录总额({total_transaction_amount})与此不符，且未找到非交易性原因说明。",
                        "severity": "高",
                        "suggestion": f"请为{char_name}的金钱变化添加明确的交易记录，或在情节中说明差额({unexplained_change:.2f})的来源/去向，以便AI能提取到原因。"
                    })
            # --- 核心逻辑重构结束 ---
        # 检查交易双方的对应关系 (这部分逻辑保持不变)
        for transaction_id, transaction in economy_changes.items():
            from_char = transaction.get('from_character')
            to_char = transaction.get('to_character')
            if from_char and from_char not in characters_changes and from_char != "系统":
                consistency_issues.append({
                    "type": "TRANSACTION_CONSISTENCY",
                    "description": f"交易{transaction_id}的付款方{from_char}不存在于角色列表中",
                    "severity": "中", 
                    "suggestion": "确认付款方角色名称是否正确，或改为系统交易"
                })
            if to_char and to_char not in characters_changes and to_char != "系统":
                consistency_issues.append({
                    "type": "TRANSACTION_CONSISTENCY",
                    "description": f"交易{transaction_id}的收款方{to_char}不存在于角色列表中", 
                    "severity": "中",
                    "suggestion": "确认收款方角色名称是否正确，或改为系统交易"
                })
        return consistency_issues
    def _find_related_transactions(self, character_name: str, transactions: Dict, money_change: float) -> List[Dict]:
        """查找与角色相关的交易记录"""
        related = []
        for transaction_id, transaction in transactions.items():
            from_char = transaction.get('from_character')
            to_char = transaction.get('to_character')
            if from_char == character_name or to_char == character_name:
                related.append(transaction)
        return related
    def get_novel_world_state(self, novel_title: str) -> Dict:
        """获取小说的世界状态（ContentGenerator需要的接口）"""
        return self.load_previous_assessments(novel_title)
    
    def _should_accept_new_character(self, character_name: str, character_data: Dict,
                                   existing_characters: Dict, current_chapter: int) -> bool:
        """
        🔧 新增：新角色准入验证机制
        
        对新角色进行多维度验证，避免误将非角色词汇添加到角色表中
        
        Args:
            character_name (str): 角色名称
            character_data (Dict): 角色数据
            existing_characters (Dict): 现有角色字典
            current_chapter (int): 当前章节
            
        Returns:
            bool: 是否接受该新角色
        """
        self.logger.info(f"🔍 开始新角色准入验证: {character_name}")
        
        # 1. 基础名称验证（再次检查）
        if not self._is_valid_character_name(character_name):
            self.logger.info(f"   ❌ 名称验证失败: {character_name}")
            return False
        
        # 2. 长度和结构合理性检查
        if len(character_name) < 2 or len(character_name) > 6:
            self.logger.info(f"   ❌ 名称长度不合理: {len(character_name)} 字符")
            return False
        
        # 3. 检查是否为常见的误识别模式
        suspicious_patterns = [
            r'.*[剑刀枪戟斧钺钩叉鞭锏锤拐棒].*$',  # 武器名称
            r'.*[丹药丸散膏汤剂露酒茶].*$',        # 药物名称
            r'.*[山川湖海江河溪涧泉瀑峰岭崖谷峡].*$',  # 地理名称
            r'.*[金银铜铁玉石珍珠宝石翡翠玛瑙].*$',  # 宝物名称
            r'.*[东西南北中上下左右前后].*$',      # 方位词
            r'.*[的之而是与和在有对把被让给为].*$',  # 功能词
        ]
        
        for pattern in suspicious_patterns:
            if re.match(pattern, character_name):
                self.logger.info(f"   ❌ 匹配到可疑模式: {pattern}")
                return False
        
        # 4. 检查角色数据完整性
        required_fields = ["name"]
        missing_fields = [field for field in required_fields if field not in character_data]
        if missing_fields:
            self.logger.info(f"   ❌ 缺少必需字段: {missing_fields}")
            return False
        
        # 5. 检查是否与现有角色过于相似（可能的重复）
        for existing_name in existing_characters.keys():
            similarity = self._calculate_name_similarity(character_name, existing_name)
            if similarity > 0.8:  # 80%相似度阈值
                self.logger.info(f"   ❌ 与现有角色过于相似: {existing_name} (相似度: {similarity:.2f})")
                return False
        
        # 6. 章节合理性检查（放宽：允许章节号为0，用于初始化阶段）
        if current_chapter < 0:
            self.logger.info(f"   ❌ 章节号无效（负数）: {current_chapter}")
            return False
        
        # 只在章节号为0时给出警告，但不拒绝
        if current_chapter == 0:
            self.logger.info(f"   ⚠️ 章节号为0，可能为初始化阶段，允许添加")
        
        # 7. 角色类型合理性检查
        role_type = character_data.get("role_type", "")
        if role_type and len(role_type) > 20:
            self.logger.info(f"   ❌ 角色类型过长: {len(role_type)} 字符")
            return False
        
        # 8. 特殊情况：如果是双字名称，需要更严格的验证
        if len(character_name) == 2:
            # 双字名称必须是常见的姓氏+单字 - 扩展常见姓氏列表
            common_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
                              '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
                              '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
                              '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金', '石', '廖', '贾', '夏']
            if character_name[0] not in common_surnames:
                self.logger.info(f"   ❌ 双字名称首字不是常见姓氏: {character_name[0]}")
                return False
        
        # 9. 检查是否为修仙小说中的特殊称谓（这些通常不是个人名字）
        special_titles = [
            "剑尊", "刀圣", "药王", "毒皇", "阵仙", "器宗", "丹神", "武圣", "法王", "魔尊",
            "天尊", "地尊", "人尊", "神尊", "仙尊", "佛尊", "道尊", "儒尊", "魔君", "仙君",
            "真人", "道人", "仙子", "神君", "天君", "地君", "人君", "星君", "月君", "日君"
        ]
        
        if character_name in special_titles:
            self.logger.info(f"   ❌ 是特殊称谓而非个人名字: {character_name}")
            return False
        
        # 10. 特殊检查：如果是常见的文学作品人名，放宽其他限制
        literary_names = [
            "张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一",
            "林黛玉", "贾宝玉", "孙悟空", "猪八戒", "沙和尚", "唐三藏", "宋江", "武松",
            "林冲", "鲁智深", "杨过", "小龙女", "郭靖", "黄蓉", "张无忌", "赵敏"
        ]
        
        if character_name in literary_names:
            self.logger.info(f"   ✅ 是常见文学人名，放宽验证: {character_name}")
            return True
        
        # 10. 最终检查：角色名称的"人物感"评估
        if not self._has_human_like_quality(character_name):
            self.logger.info(f"   ❌ 缺乏人物感的名称: {character_name}")
            return False
        
        self.logger.info(f"   ✅ 新角色 '{character_name}' 通过所有准入验证")
        return True
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """计算两个名字的相似度"""
        if not name1 or not name2:
            return 0.0
        
        # 简单的字符重叠度计算
        set1 = set(name1)
        set2 = set(name2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0.0
        
        return intersection / union
    
    def _has_human_like_quality(self, name: str) -> bool:
        """检查名称是否具有人物感 - 🔧 修复版本：大幅放宽准入原则"""
        
        # 🔧 重大修复：对于常见的中文名字结构，直接通过验证
        # 1. 检查是否为标准的中文名字结构：姓氏 + 名字
        common_surnames = [
            '王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周', '徐', '孙', '马', '朱', '胡', '郭',
            '何', '高', '林', '罗', '郑', '梁', '谢', '宋', '唐', '许', '韩', '冯', '邓', '曹', '彭', '曾',
            '萧', '田', '董', '袁', '潘', '于', '蒋', '蔡', '余', '杜', '叶', '程', '苏', '魏', '吕', '丁',
            '任', '沈', '姚', '卢', '姜', '崔', '钟', '谭', '陆', '汪', '范', '金', '石', '廖', '贾', '夏',
            '韦', '付', '方', '白', '邹', '孟', '熊', '秦', '邱', '江', '尹', '薛', '闫', '段', '雷', '侯',
            '龙', '史', '陶', '黎', '贺', '顾', '毛', '郝', '龚', '邵', '万', '钱', '严', '覃', '武', '戴',
            '莫', '孔', '向', '汤'
        ]
        
        # 2. 如果名字以常见姓氏开头，直接通过验证
        for surname in common_surnames:
            if name.startswith(surname):
                self.logger.info(f"   ✅ 常见姓氏开头，直接通过: {name} (姓氏: {surname})")
                return True
        
        # 3. 检查是否为复姓开头
        compound_surnames = ['欧阳', '司马', '上官', '东方', '诸葛', '司徒', '夏侯', '皇甫']
        for compound_surname in compound_surnames:
            if name.startswith(compound_surname):
                self.logger.info(f"   ✅ 复姓开头，直接通过: {name} (复姓: {compound_surname})")
                return True
        
        # 4. 🔧 放宽检查：修仙小说特殊称谓检查
        cultivation_titles = [
            '师兄', '师妹', '师姐', '师弟', '师父', '师尊', '师祖', '掌门', '长老', '宗主', '门主', '教主', '宫主',
            '真人', '道人', '仙子', '神君', '天尊', '魔尊', '剑圣', '法王', '剑仙', '刀神', '药王', '毒皇'
        ]
        
        for title in cultivation_titles:
            if name == title or name.endswith(title) or name.startswith(title):
                self.logger.info(f"   ✅ 修仙称谓，直接通过: {name} (称谓: {title})")
                return True
        
        # 5. 🔧 放宽检查：文学经典人名检查
        literary_names = [
            "林黛玉", "贾宝玉", "孙悟空", "猪八戒", "沙和尚", "唐三藏", "宋江", "武松",
            "林冲", "鲁智深", "杨过", "小龙女", "郭靖", "黄蓉", "张无忌", "赵敏",
            "张三", "李四", "王五", "赵六", "李青元", "慕沛灵"  # 特别添加这两个被拒绝的名字
        ]
        
        if name in literary_names:
            self.logger.info(f"   ✅ 文学人名，直接通过: {name}")
            return True
        
        # 6. 🔧 大幅放宽：包含常见人名用字即可通过
        human_name_chars = [
            # 常见人名用字
            '伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '洋', '艳', '勇', '军', '杰', '娟', '涛',
            '明', '超', '秀英', '霞', '平', '刚', '桂英', '玉兰', '萍', '鹏', '华', '红', '金', '春梅',
            '龙', '林', '辉', '晨', '宇', '欣', '婷', '琴', '玲', '兰', '琳', '燕', '芳', '萍', '娟',
            '浩', '宇', '博', '文', '轩', '涵', '梓', '睿', '皓', '辰', '羽', '诺', '晨', '曦', '语',
            '思', '佳', '梦', '诗', '雨', '晴', '雪', '月', '花', '柳', '风', '云', '天', '地', '山',
            
            # 🔧 扩展更多常见人名用字
            '青', '元', '志', '德', '仁', '义', '礼', '智', '信', '忠', '孝', '廉', '耻', '勇', '毅',
            '刚', '柔', '和', '顺', '良', '正', '直', '诚', '实', '朴', '素', '雅', '致', '高', '尚',
            '美', '善', '慈', '祥', '瑞', '吉', '庆', '安', '宁', '静', '平', '和', '乐', '康', '健',
            '福', '禄', '寿', '喜', '财', '宝', '珍', '珠', '玉', '金', '银', '铜', '铁', '石', '木',
            '春', '夏', '秋', '冬', '东', '南', '西', '北', '中', '上', '下', '左', '右', '前', '后',
            '日', '月', '星', '辰', '天', '地', '山', '川', '河', '海', '江', '湖', '溪', '泉', '瀑',
            
            # 修仙小说常见人名用字
            '玄', '虚', '尘', '心', '性', '灵', '神', '仙', '魔', '妖', '鬼', '圣', '贤', '君', '王',
            '皇', '帝', '主', '宗', '师', '祖', '尊', '长', '老', '徒', '弟', '兄', '姐', '妹', '郎',
            '生', '子', '公', '侯', '伯', '子', '男', '女', '儿', '童', '叟', '翁', '媪', '妪', '婆',
            
            # 文学作品中的经典人名用字
            '黛', '玉', '宝', '悟', '空', '无', '忌', '小', '杨', '过', '孙', '欧', '阳', '修', '林', '冲',
            
            # 特别添加：李青元和慕沛灵中的人名用字
            '沛', '灵', '慕'
        ]
        
        has_human_char = any(char in name for char in human_name_chars)
        if has_human_char:
            self.logger.info(f"   ✅ 包含人名用字，通过: {name}")
            return True
        
        # 7. 🔧 最后放宽：如果长度在2-4个字符之间，且不包含明显非人名字符，直接通过
        if 2 <= len(name) <= 4:
            # 检查是否包含明显非人名字符
            non_human_chars = ['的', '之', '是', '在', '有', '没有', '可', '可以', '能够', '应该', '需要', '想要', '希望']
            has_non_human = any(char in name for char in non_human_chars)
            if not has_non_human:
                self.logger.info(f"   ✅ 长度合理且无非人名字符，通过: {name}")
                return True
        
        # 8. 如果以上检查都未通过，才拒绝
        self.logger.info(f"   ❌ 未通过人物感检查: {name}")
        return False
    
    def _filter_descriptive_content(self, text: str) -> str:
        """🔧 新增：过滤文本，移除明显的描述性内容片段"""
        if not text:
            return text
        
        # 移除明显的描述性段落
        descriptive_patterns = [
            r'[^。！？]*的坦诚果断[^。！？]*[。！？]?',  # "墨衍的坦诚果断"这类描述
            r'[^。！？]*的核心聚焦[^。！？]*[。！？]?',  # "本章核心聚焦于墨衍"这类描述
            r'[^。！？]*的基本描述[^。！？]*[。！？]?',   # "基本描述"类内容
            r'[^。！？]*的故事目的[^。！？]*[。！？]?',   # "故事目的"类内容
            r'[^。！？]*的微妙变化[^。！？]*[。！？]?',   # "微妙变化"类内容
            r'[^。！？]*的个人立场[^。！？]*[。！？]?',   # "个人立场"类内容
            r'[^。！？]*的反思过程[^。！？]*[。！？]?',   # "反思过程"类内容
            r'[^。！？]*从上一章[^。！？]*[。！？]?',     # "从上一章"类过渡描述
            r'[^。！？]*但实际[^。！？]*[。！？]?',       # "但实际"类对比描述
            r'[^。！？]*通过[^。！？]*[。！？]?',         # "通过"类过程描述
            r'[^。！？]*两处体现[^。！？]*[。！？]?',     # "两处体现"类分析描述
        ]
        
        filtered_text = text
        for pattern in descriptive_patterns:
            filtered_text = re.sub(pattern, '', filtered_text)
        
        return filtered_text
    
    def _is_descriptive_phrase(self, name: str, text: str) -> bool:
        """🔧 新增：判断名称是否为描述性短语"""
        # 检查名称是否包含描述性关键词
        descriptive_keywords = [
            '的', '之', '是', '在', '有', '没有', '可', '可以', '能够', '应该', '需要', '想要', '希望',
            '感觉', '认为', '知道', '明白', '理解', '发现', '意识到', '察觉', '想到', '预料', '意外',
            '活跃', '死亡', '生存', '存在', '出现', '消失', '变化', '发展', '成长', '进化', '退化', '转变',
            '本章', '上一章', '下一章', '核心', '聚焦', '基本', '描述', '目的', '微妙', '变化', '个人', '立场',
            '反思', '过程', '实际', '通过', '两处', '体现', '坦诚', '果断', '状态', '属性', '特征', '模式'
        ]
        
        # 如果名称包含任何描述性关键词，认为是描述性短语
        for keyword in descriptive_keywords:
            if keyword in name:
                return True
        
        # 检查名称的语法结构
        if '的' in name and len(name) > 4:  # 包含"的"且长度较长，很可能是描述性短语
            return True
        
        # 检查是否在文本中以描述性方式出现
        context_patterns = [
            f'{name}：.*？',  # 疑问句式
            f'{name}是.*',   # 判断句式
            f'{name}的.*',   # 所属关系
        ]
        
        for pattern in context_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _is_in_descriptive_context(self, name: str, text: str) -> bool:
        """🔧 新增：检查名称是否出现在描述性上下文中"""
        # 获取名称在文本中的所有出现位置
        import re
        positions = []
        for match in re.finditer(re.escape(name), text):
            positions.append(match.start())
        
        for pos in positions:
            # 获取名称前后的上下文（各50个字符）
            start = max(0, pos - 50)
            end = min(len(text), pos + len(name) + 50)
            context = text[start:end]
            
            # 检查上下文是否包含描述性关键词
            descriptive_indicators = [
                '基本描述', '故事目的', '角色类型', '重要性', '首次出场', '最后更新', '总出场次数',
                '核心聚焦', '个人立场', '微妙变化', '反思过程', '情绪状态', '行为模式', '性格特征',
                '本章', '章节', '从上一章', '但实际', '通过', '两处体现', '的坦诚', '的果断'
            ]
            
            for indicator in descriptive_indicators:
                if indicator in context:
                    return True
            
            # 检查是否在数据结构或元数据描述中
            metadata_indicators = [
                '"name":', '"status":', '"role_type":', '"importance":', '"first_appearance":',
                '"last_updated":', '"total_appearances":', '"basic_description":', '"purpose_in_story":'
            ]
            
            for indicator in metadata_indicators:
                if indicator in context:
                    return True
        
        return False
