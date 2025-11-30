"""Smoke test: Verify event emission from QualityAssessor assessment."""
import sys
from src.utils.logger import get_logger
sys.path.insert(0, r'd:\work6.03')

from WorldStateManager import WorldStateManager
import json
import os

def test_emit_events_from_assessment():
    self.logger.info("=" * 60)
    self.logger.info("SMOKE TEST: Event Emission from Assessment")
    self.logger.info("=" * 60)
    
    wsm = WorldStateManager(r'd:\work6.03\quality_data')
    novel_title = 'test_novel_emit_events'
    chapter = 5
    
    # Create a mock assessment with character development and interactions
    mock_assessment = {
        'overall_score': 8.5,
        'character_development_assessment': {
            'new_characters_introduced': [
                {'name': '张三', 'role_type': '重要配角'}
            ],
            'character_interactions': [
                {
                    'characters': ['林渊', '张三'],
                    'interaction_type': '盟友',
                    'description': '两人共同对抗敌人'
                },
                {
                    'characters': ['张三', '李四'],
                    'interaction_type': '对手',
                    'description': '两人产生冲突'
                }
            ],
            'character_updates': {
                '林渊': {
                    'status': 'active',
                    'location': '云山派',
                    'cultivation_level': '筑基期'
                }
            }
        }
    }
    
    # Access the QualityAssessor's event emission helper via WorldStateManager context
    # (We'll create a simple wrapper to test the event flow)
    self.logger.info(f"\n📋 Mock Assessment:")
    self.logger.info(f"   - New characters: 1 (张三)")
    self.logger.info(f"   - Interactions: 2 (盟友 + 对手)")
    self.logger.info(f"   - Character updates: 1 (林渊)")
    
    # Simulate what _emit_events_from_assessment does
    self.logger.info(f"\n🔄 Emitting events from assessment...")
    
    # 1. Character.add event
    event_add = {
        'action': 'character.add',
        'actor': '张三',
        'chapter': chapter,
        'payload': {
            'name': '张三',
            'role_type': '重要配角',
            'status': 'active'
        }
    }
    ok, msg = wsm.apply_event(novel_title, event_add)
    self.logger.info(f"   1️⃣ character.add: {msg}")
    
    # 2. Relationship.create events
    event_rel1 = {
        'action': 'relationship.create',
        'actor': '林渊',
        'chapter': chapter,
        'payload': {
            'from': '林渊',
            'to': '张三',
            'relation_type': '盟友',
            'description': '两人共同对抗敌人'
        }
    }
    ok, msg = wsm.apply_event(novel_title, event_rel1)
    self.logger.info(f"   2️⃣ relationship.create (盟友): {msg}")
    
    # Try a conflicting relationship (should be rejected if already allies)
    event_rel2_conflict = {
        'action': 'relationship.create',
        'actor': '张三',
        'chapter': chapter,
        'payload': {
            'from': '张三',
            'to': '林渊',
            'relation_type': '敌对',
            'description': 'test conflict'
        }
    }
    ok, msg = wsm.apply_event(novel_title, event_rel2_conflict)
    self.logger.info(f"   3️⃣ relationship.create (conflict test, should reject): {msg}")
    
    # 3. Character.update event
    event_update = {
        'action': 'character.update',
        'actor': '林渊',
        'chapter': chapter,
        'payload': {
            'name': '林渊',
            'attributes': {
                'status': 'active',
                'location': '云山派',
                'cultivation_level': '筑基期'
            }
        }
    }
    ok, msg = wsm.apply_event(novel_title, event_update)
    self.logger.info(f"   4️⃣ character.update: {msg}")
    
    # Verify persistence
    self.logger.info(f"\n💾 Checking persistence...")
    events = wsm.load_events(novel_title)
    rels = wsm.load_relationships(novel_title)
    self.logger.info(f"   - Events logged: {len(events)}")
    self.logger.info(f"   - Relationships stored: {len(rels)}")
    
    # Show relationship details
    if rels:
        self.logger.info(f"\n📊 Relationships:")
        for edge_id, edge in rels.items():
            self.logger.info(f"     {edge.get('from')} --[{edge.get('type')}]--> {edge.get('to')}")
    
    self.logger.info(f"\n✅ Smoke test completed successfully!")
    self.logger.info("=" * 60)

if __name__ == '__main__':
    test_emit_events_from_assessment()
