# -*- coding: utf-8 -*-
"""
番茄小说榜单抓取器

抓取番茄小说热门榜单数据，分析当前热门题材
- 阅读榜
- 畅销榜  
- 新书榜
- 完结榜
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class FanqieRankingCrawler:
    """
    番茄小说榜单抓取器
    
    使用番茄小说公开API或页面抓取获取榜单数据
    """
    
    # 番茄榜单API（需要根据实际情况调整）
    RANKING_APIS = {
        "read": "https://fanqienovel.com/api/rank/read",           # 阅读榜
        "sale": "https://fanqienovel.com/api/rank/sale",           # 畅销榜
        "new": "https://fanqienovel.com/api/rank/new",             # 新书榜
        "finished": "https://fanqienovel.com/api/rank/finished",   # 完结榜
        "rise": "https://fanqienovel.com/api/rank/rise",           # 飙升榜
    }
    
    # 分类ID映射（需要根据实际API调整）
    CATEGORY_MAP = {
        "全部": 0,
        "都市": 1,
        "玄幻": 2,
        "仙侠": 3,
        "科幻": 4,
        "历史": 5,
        "游戏": 6,
        "体育": 7,
        "悬疑": 8,
        "奇幻": 9,
        "武侠": 10,
        "军事": 11,
        "诸天无限": 12,
        "现实": 13,
        "古言": 14,
        "现言": 15,
        "幻言": 16,
    }
    
    def __init__(self, cache_dir: str = "data/rankings"):
        """
        初始化榜单抓取器
        
        Args:
            cache_dir: 榜单数据缓存目录
        """
        import os
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.session = None
        
    def _get_session(self):
        """获取HTTP会话"""
        if self.session is None:
            import requests
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            })
        return self.session
    
    def fetch_ranking(self, rank_type: str = "read", category: str = "全部", 
                      limit: int = 100) -> Optional[List[Dict]]:
        """
        抓取榜单数据
        
        Args:
            rank_type: 榜单类型 (read/sale/new/finished/rise)
            category: 分类名称
            limit: 获取数量
            
        Returns:
            榜单书籍列表
        """
        try:
            # 检查缓存（1小时）
            cache_key = f"{rank_type}_{category}_{limit}"
            cached = self._load_cache(cache_key)
            if cached:
                cache_time = cached.get("fetch_time", 0)
                if time.time() - cache_time < 3600:  # 1小时缓存
                    logger.info(f"[FanqieCrawler] 使用缓存的榜单数据: {rank_type}")
                    return cached.get("data")
            
            # 实际抓取
            books = self._fetch_from_api(rank_type, category, limit)
            
            if books:
                # 保存缓存
                self._save_cache(cache_key, {
                    "fetch_time": time.time(),
                    "data": books
                })
            
            return books
            
        except Exception as e:
            logger.error(f"[FanqieCrawler] 抓取榜单失败: {e}")
            return None
    
    def _fetch_from_api(self, rank_type: str, category: str, limit: int) -> List[Dict]:
        """
        从API获取榜单数据
        
        注意：这里的API URL和参数需要根据番茄实际的API调整
        可能需要逆向分析或抓包获取真实接口
        """
        import requests
        
        api_url = self.RANKING_APIS.get(rank_type, self.RANKING_APIS["read"])
        category_id = self.CATEGORY_MAP.get(category, 0)
        
        params = {
            "category": category_id,
            "limit": limit,
            "page": 1,
        }
        
        try:
            response = self._get_session().get(
                api_url, 
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # 解析响应（根据实际API结构调整）
            books = self._parse_ranking_response(data)
            
            logger.info(f"[FanqieCrawler] 成功抓取 {len(books)} 本书籍")
            return books
            
        except Exception as e:
            logger.error(f"[FanqieCrawler] API请求失败: {e}")
            # 返回空列表或模拟数据
            return []
    
    def _parse_ranking_response(self, data: Dict) -> List[Dict]:
        """
        解析榜单API响应
        
        需要根据番茄实际API结构调整
        """
        books = []
        
        # 假设响应格式
        if "data" in data and "list" in data["data"]:
            for item in data["data"]["list"]:
                book = {
                    "rank": item.get("rank", 0),
                    "book_id": item.get("book_id", ""),
                    "title": item.get("title", ""),
                    "author": item.get("author", ""),
                    "category": item.get("category", ""),
                    "sub_category": item.get("sub_category", ""),
                    "total_words": item.get("total_words", 0),
                    "read_count": item.get("read_count", 0),
                    "score": item.get("score", 0),
                    "description": item.get("description", ""),
                }
                books.append(book)
        
        return books
    
    def analyze_genres_from_ranking(self, rank_type: str = "read", 
                                    limit: int = 100) -> Dict[str, int]:
        """
        分析榜单中的题材分布
        
        Args:
            rank_type: 榜单类型
            limit: 分析数量
            
        Returns:
            题材分布统计
        """
        books = self.fetch_ranking(rank_type, limit=limit)
        
        if not books:
            return {}
        
        # 统计题材分布
        genre_count = {}
        for book in books:
            category = book.get("category", "未知")
            sub_category = book.get("sub_category", "")
            
            # 组合主分类和子分类
            genre_key = f"{category}-{sub_category}" if sub_category else category
            genre_count[genre_key] = genre_count.get(genre_key, 0) + 1
        
        # 按数量排序
        sorted_genres = dict(sorted(
            genre_count.items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        return sorted_genres
    
    def get_trending_genres(self, days: int = 7) -> List[Dict]:
        """
        获取近期热门题材趋势
        
        Args:
            days: 分析天数
            
        Returns:
            热门题材列表（带趋势信息）
        """
        # 读取多天的榜单数据
        all_genres = []
        
        for day in range(days):
            date = datetime.now() - timedelta(days=day)
            date_str = date.strftime("%Y%m%d")
            
            # 尝试读取历史数据
            cache_file = f"{self.cache_dir}/ranking_{date_str}.json"
            if Path(cache_file).exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_genres.append(data)
        
        # 分析趋势（简化版）
        # 实际应该计算每天的占比变化
        
        return []
    
    def generate_genre_suggestions(self, api_client=None) -> List[Dict]:
        """
        基于榜单数据生成新题材建议
        
        Args:
            api_client: AI客户端，用于分析
            
        Returns:
            新题材建议列表
        """
        # 抓取多个榜单
        rankings = {
            "read": self.fetch_ranking("read", limit=100),
            "sale": self.fetch_ranking("sale", limit=100),
            "new": self.fetch_ranking("new", limit=100),
            "rise": self.fetch_ranking("rise", limit=100),
        }
        
        # 分析题材分布
        genre_stats = {}
        for rank_type, books in rankings.items():
            if books:
                stats = self.analyze_genres_from_ranking(rank_type, limit=len(books))
                genre_stats[rank_type] = stats
        
        # 如果有AI客户端，让AI分析趋势并生成建议
        if api_client and genre_stats:
            return self._ai_analyze_trends(genre_stats, api_client)
        
        return []
    
    def _ai_analyze_trends(self, genre_stats: Dict, api_client) -> List[Dict]:
        """使用AI分析趋势"""
        
        prompt = f"""你是一位资深网文市场分析师。

以下是番茄小说近期榜单的题材分布数据：

{json.dumps(genre_stats, ensure_ascii=False, indent=2)}

请分析这些数据，找出：
1. 当前最热门的题材是什么？
2. 哪些题材正在快速上升？
3. 蓝海题材（竞争小但有潜力）有哪些？
4. 基于趋势，推荐3-5个新的类型细分方向

请用JSON格式输出新类型建议：
[
    {{
        "genre_name": "类型名称-细分",
        "description": "类型描述",
        "trend": "上升/稳定/新兴",
        "potential": "高/中/低",
        "competition": "激烈/中等/低"
    }}
]
"""
        
        try:
            response = api_client.generate_content_with_retry(
                content_type="genre_trend_analysis",
                user_prompt=prompt,
                temperature=0.7,
                purpose="分析榜单趋势生成新类型"
            )
            
            if isinstance(response, list):
                return response
            elif isinstance(response, str):
                return json.loads(response)
                
        except Exception as e:
            logger.error(f"AI分析趋势失败: {e}")
        
        return []
    
    def _load_cache(self, cache_key: str) -> Optional[Dict]:
        """加载缓存"""
        import os
        cache_file = f"{self.cache_dir}/cache_{cache_key}.json"
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def _save_cache(self, cache_key: str, data: Dict):
        """保存缓存"""
        cache_file = f"{self.cache_dir}/cache_{cache_key}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")


# 使用示例说明
"""
# 1. 初始化抓取器
crawler = FanqieRankingCrawler()

# 2. 抓取榜单
books = crawler.fetch_ranking("read", category="全部", limit=100)

# 3. 分析题材分布
genre_stats = crawler.analyze_genres_from_ranking("read", limit=100)
print(genre_stats)
# 输出示例：
# {"都市-神豪": 25, "玄幻-东方玄幻": 20, "都市-奶爸": 15, ...}

# 4. 生成新题材建议（需要AI客户端）
suggestions = crawler.generate_genre_suggestions(api_client)
"""


class SimpleFanqieScraper:
    """
    简化版番茄抓取器（使用网页抓取）
    
    如果API不可用，可以使用Playwright/Selenium模拟浏览器抓取
    """
    
    def __init__(self):
        self.base_url = "https://fanqienovel.com"
    
    def scrape_ranking_page(self, rank_type: str = "read") -> List[Dict]:
        """
        抓取榜单页面
        
        需要使用Playwright或Selenium
        """
        # 实现网页抓取逻辑
        # 1. 打开榜单页面
        # 2. 解析书籍列表
        # 3. 提取分类信息
        pass


def test_crawler():
    """测试抓取器"""
    crawler = FanqieRankingCrawler()
    
    # 抓取阅读榜
    books = crawler.fetch_ranking("read", limit=50)
    
    if books:
        print(f"成功抓取 {len(books)} 本书")
        print("\n前10本书：")
        for book in books[:10]:
            print(f"{book['rank']}. {book['title']} - {book['category']}")
        
        # 分析题材分布
        print("\n题材分布：")
        genres = crawler.analyze_genres_from_ranking("read", limit=50)
        for genre, count in list(genres.items())[:10]:
            print(f"  {genre}: {count}本")
    else:
        print("抓取失败，请检查API配置")


if __name__ == "__main__":
    # 运行测试
    test_crawler()
