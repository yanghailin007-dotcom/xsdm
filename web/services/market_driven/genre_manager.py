# -*- coding: utf-8 -*-
"""
Genre Manager Service
小说类型管理器

管理小说类型的获取和自动更新
- 支持静态类型列表
- 支持AI动态生成新类型（每周自动更新）
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class GenreManager:
    """
    小说类型管理器
    
    功能：
    1. 维护基础类型列表（20个）
    2. 每周通过AI自动更新/扩展类型
    3. 缓存类型列表，避免重复请求
    """
    
    # 基础类型列表（20个）
    BASE_GENRES = {
        "神豪文-花钱返利类": {
            "description": "主角获得花钱返利系统，越花越有钱，装逼打脸",
            "expected_retention": "12-18%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "神豪文-签到奖励类": {
            "description": "每日签到获得奖励，逐步积累财富和实力",
            "expected_retention": "10-15%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "国运文-直播类": {
            "description": "主角代表国家参赛，全国直播，获得国运奖励",
            "expected_retention": "15-20%",
            "competition": "激烈",
            "market_status": "上升期"
        },
        "国运文-禁地探险类": {
            "description": "探索禁地，为国争光，获得神秘奖励",
            "expected_retention": "12-16%",
            "competition": "中等",
            "market_status": "平稳"
        },
        "签到文-日常签到类": {
            "description": "日常生活签到获得各种奖励，轻松变强",
            "expected_retention": "10-14%",
            "competition": "低",
            "market_status": "蓝海"
        },
        "奶爸文-萌宝类": {
            "description": "主角带娃，萌宝助攻，温馨搞笑",
            "expected_retention": "18-25%",
            "competition": "低",
            "market_status": "上升期"
        },
        "奶爸文-修炼类": {
            "description": "带娃同时修炼，保护家人，双重爽点",
            "expected_retention": "15-20%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "神选文-神明选拔类": {
            "description": "被神明选中，获得神级能力，征战诸天",
            "expected_retention": "12-16%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "模拟器文-人生模拟类": {
            "description": "可以模拟人生，提前知道未来，改变命运",
            "expected_retention": "14-18%",
            "competition": "中等",
            "market_status": "上升期"
        },
        "灵气复苏-觉醒类": {
            "description": "灵气复苏时代，主角觉醒特殊能力，崛起",
            "expected_retention": "12-16%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "末日求生-囤货类": {
            "description": "末日来临前大量囤货，末日中享受生活",
            "expected_retention": "15-20%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "四合院-日常类": {
            "description": "在四合院中生活，处理邻里关系，逐步发展",
            "expected_retention": "15-22%",
            "competition": "低",
            "market_status": "蓝海"
        },
        # 新增8个类型
        "诡异复苏-规则怪谈类": {
            "description": "诡异降临，主角破解规则怪谈，在死亡边缘求生",
            "expected_retention": "16-22%",
            "competition": "中等",
            "market_status": "上升期"
        },
        "游戏异界-虚拟现实类": {
            "description": "虚拟现实游戏与现实融合，主角成为最强玩家",
            "expected_retention": "13-17%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "美食文-系统烹饪类": {
            "description": "获得美食系统，通过烹饪获得能力，成为厨神",
            "expected_retention": "14-19%",
            "competition": "低",
            "market_status": "蓝海"
        },
        "宠物文-御兽进化类": {
            "description": "契约宠物，培养进化，成为最强御兽师",
            "expected_retention": "15-21%",
            "competition": "中等",
            "market_status": "上升期"
        },
        "历史架空-权谋争霸类": {
            "description": "穿越历史，运用现代知识权谋争霸，统一天下",
            "expected_retention": "14-18%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "文娱文-文抄公类": {
            "description": "穿越平行世界，搬运地球文娱作品，成为文娱教父",
            "expected_retention": "13-17%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "盗墓文-探险寻宝类": {
            "description": "寻龙点穴，探索古墓，解开千年谜团",
            "expected_retention": "15-20%",
            "competition": "中等",
            "market_status": "平稳"
        },
        "综漫文-无限流类": {
            "description": "穿越诸天万界，在各个动漫世界历练变强",
            "expected_retention": "14-18%",
            "competition": "激烈",
            "market_status": "稳定"
        }
    }
    
    def __init__(self, cache_dir: str = "data/genres", api_client=None):
        """
        初始化类型管理器
        
        Args:
            cache_dir: 缓存目录
            api_client: AI API客户端（用于自动生成新类型）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.api_client = api_client
        self._genres_cache = None
        self._cache_file = self.cache_dir / "genres_cache.json"
        self._last_update_file = self.cache_dir / "last_update.txt"
        
        logger.info(f"[GenreManager] 初始化完成，缓存目录: {self.cache_dir}")
    
    def get_genres(self, force_refresh: bool = False) -> Dict[str, Dict]:
        """
        获取类型列表
        
        Args:
            force_refresh: 强制刷新，忽略缓存
            
        Returns:
            类型字典
        """
        # 检查是否需要更新（每周一自动更新）
        if not force_refresh and self._should_update():
            logger.info("[GenreManager] 检测到需要更新类型列表")
            force_refresh = True
        
        if force_refresh:
            # 尝试通过AI获取新类型
            ai_genres = self._fetch_ai_genres()
            if ai_genres:
                # 合并基础类型和AI生成的新类型
                merged = {**self.BASE_GENRES, **ai_genres}
                self._save_cache(merged)
                self._genres_cache = merged
                self._update_last_update_time()
                logger.info(f"[GenreManager] 类型列表已更新，共 {len(merged)} 个类型")
                return merged
        
        # 从缓存加载
        if self._genres_cache is not None:
            return self._genres_cache
        
        cached = self._load_cache()
        if cached:
            self._genres_cache = cached
            return cached
        
        # 返回基础类型
        self._genres_cache = self.BASE_GENRES
        return self.BASE_GENRES
    
    def _should_update(self) -> bool:
        """检查是否需要更新（每周检查一次）"""
        if not self._last_update_file.exists():
            return True
        
        try:
            last_update = self._last_update_file.read_text(encoding='utf-8').strip()
            last_date = datetime.fromisoformat(last_update)
            
            # 检查是否超过7天
            days_since_update = (datetime.now() - last_date).days
            if days_since_update >= 7:
                logger.info(f"[GenreManager] 距离上次更新已过去 {days_since_update} 天")
                return True
            
            return False
        except Exception as e:
            logger.warning(f"[GenreManager] 检查更新时间失败: {e}")
            return True
    
    def _update_last_update_time(self):
        """更新最后更新时间"""
        try:
            self._last_update_file.write_text(
                datetime.now().isoformat(), 
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"[GenreManager] 保存更新时间失败: {e}")
    
    def _load_cache(self) -> Optional[Dict[str, Dict]]:
        """从文件加载缓存"""
        if not self._cache_file.exists():
            return None
        
        try:
            with open(self._cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"[GenreManager] 从缓存加载了 {len(data)} 个类型")
                return data
        except Exception as e:
            logger.error(f"[GenreManager] 加载缓存失败: {e}")
            return None
    
    def _save_cache(self, genres: Dict[str, Dict]):
        """保存缓存到文件"""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                json.dump(genres, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[GenreManager] 保存缓存失败: {e}")
    
    def _fetch_ai_genres(self) -> Optional[Dict[str, Dict]]:
        """
        通过AI请求获取新类型
        
        Returns:
            AI生成的新类型字典，失败返回None
        """
        if not self.api_client:
            logger.warning("[GenreManager] 未配置API客户端，跳过AI生成")
            return None
        
        try:
            logger.info("[GenreManager] 开始请求AI生成新类型...")
            
            prompt = self._build_genre_generation_prompt()
            
            response = self.api_client.generate_content_with_retry(
                content_type="genre_generation",
                user_prompt=prompt,
                temperature=0.7,
                purpose="生成新的热门小说类型"
            )
            
            # 解析响应
            genres = self._parse_ai_response(response)
            if genres:
                logger.info(f"[GenreManager] AI生成了 {len(genres)} 个新类型")
                return genres
            else:
                logger.warning("[GenreManager] AI返回的类型解析失败")
                return None
                
        except Exception as e:
            logger.error(f"[GenreManager] AI请求失败: {e}")
            return None
    
    def _build_genre_generation_prompt(self) -> str:
        """构建AI生成类型的提示词"""
        current_genres = list(self.BASE_GENRES.keys())
        
        return f"""你是一位资深的网络文学市场分析师，熟悉番茄小说平台的最新流行趋势。

请基于当前市场热点，生成3-5个**全新的、有潜力**的小说类型。

## 当前已有的类型（不要重复）
{chr(10).join(f"- {g}" for g in current_genres)}

## 生成要求
1. 类型必须是最近6个月内新兴或热度上升的题材
2. 每个类型需要有独特的卖点和市场定位
3. 避免与已有类型重复

## 输出格式（必须是有效的JSON）
{{
    "类型名称-子分类": {{
        "description": "类型的核心卖点和故事模式（50字以内）",
        "expected_retention": "预期留存率，如 12-18%",
        "competition": "竞争程度：低/中等/激烈",
        "market_status": "市场状态：蓝海/上升期/稳定/平稳"
    }}
}}

请直接输出JSON，不要有任何其他说明文字。"""
    
    def _parse_ai_response(self, response) -> Optional[Dict[str, Dict]]:
        """解析AI响应"""
        import re
        
        try:
            # 处理不同类型的响应
            if isinstance(response, dict):
                return response
            
            if isinstance(response, str):
                # 尝试直接解析
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    pass
                
                # 尝试提取JSON代码块
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                
                # 尝试提取花括号内容
                brace_match = re.search(r'\{.*\}', response, re.DOTALL)
                if brace_match:
                    return json.loads(brace_match.group(0))
            
            logger.warning(f"[GenreManager] 无法解析AI响应: {type(response)}")
            return None
            
        except json.JSONDecodeError as e:
            logger.error(f"[GenreManager] JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"[GenreManager] 解析AI响应时出错: {e}")
            return None
    
    def manual_refresh(self) -> bool:
        """
        手动触发类型更新
        
        Returns:
            是否成功更新
        """
        logger.info("[GenreManager] 手动触发类型更新")
        genres = self.get_genres(force_refresh=True)
        return len(genres) > len(self.BASE_GENRES)
    
    def get_update_status(self) -> Dict:
        """获取更新状态信息"""
        last_update = None
        days_since = None
        
        if self._last_update_file.exists():
            try:
                last_update = self._last_update_file.read_text(encoding='utf-8').strip()
                last_date = datetime.fromisoformat(last_update)
                days_since = (datetime.now() - last_date).days
            except:
                pass
        
        current_genres = self.get_genres()
        
        return {
            "total_genres": len(current_genres),
            "base_genres": len(self.BASE_GENRES),
            "ai_genres": len(current_genres) - len(self.BASE_GENRES),
            "last_update": last_update,
            "days_since_update": days_since,
            "next_update_due": days_since is not None and days_since >= 7
        }


# 全局管理器实例（单例）
_genre_manager_instance: Optional[GenreManager] = None


def get_genre_manager(api_client=None) -> GenreManager:
    """
    获取GenreManager单例
    
    Args:
        api_client: AI API客户端
        
    Returns:
        GenreManager实例
    """
    global _genre_manager_instance
    if _genre_manager_instance is None:
        _genre_manager_instance = GenreManager(api_client=api_client)
    elif api_client is not None:
        _genre_manager_instance.api_client = api_client
    
    return _genre_manager_instance
