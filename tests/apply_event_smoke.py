import sys
sys.path.insert(0, r'd:\work6.03')
from WorldStateManager import WorldStateManager
w = WorldStateManager(r'd:\work6.03\quality_data')
self.logger.info('--- APPLY relationship.create')
e = {'action':'relationship.create','actor':'林渊','payload':{'from':'林渊','to':'韩立','relation_type':'盟友','description':'结为盟友'}}
self.logger.info(w.apply_event('凡人_我与韩立共掌落云宗', e))
self.logger.info('--- APPLY money.transfer')
e2 = {'action':'money.transfer','actor':'林渊','payload':{'from':'林渊','to':'韩立','amount':100,'reason':'借款'}}
self.logger.info(w.apply_event('凡人_我与韩立共掌落云宗', e2))
import os
from src.utils.logger import get_logger
self.logger.info('events file path:', os.path.join(r'd:\work6.03\quality_data','events','凡人_我与韩立共掌落云宗_events.jsonl'))
self.logger.info('events file exists:', os.path.exists(os.path.join(r'd:\work6.03\quality_data','events','凡人_我与韩立共掌落云宗_events.jsonl')))
self.logger.info('relationships file exists:', os.path.exists(os.path.join(r'd:\work6.03\quality_data','relationships','凡人_我与韩立共掌落云宗_relationships.json')))
