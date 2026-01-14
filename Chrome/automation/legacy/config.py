"""
番茄小说自动发布系统 - 配置模块
包含所有配置参数和常量
"""

# 配置参数 - 使用绝对路径解决工作目录问题
import os
from pathlib import Path

# 获取项目根目录 - 简化路径计算
import os
from pathlib import Path

# 使用环境变量或智能检测项目根目录
if os.environ.get('PROJECT_ROOT'):
    project_root = Path(os.environ['PROJECT_ROOT'])
else:
    # 尝试检测项目根目录
    current_dir = Path.cwd()
    
    # 方法1: 如果当前在项目根目录下（有Chrome目录）
    if (current_dir / "Chrome").exists():
        project_root = current_dir
    # 方法2: 如果当前在Chrome/automation目录下
    elif current_dir.name == "automation" and (current_dir.parent / "Chrome").exists():
        project_root = current_dir.parent.parent
    # 方法3: 如果当前在Chrome目录下
    elif current_dir.name == "Chrome":
        project_root = current_dir.parent
    # 方法4: 从配置文件位置计算
    else:
        config_file = Path(__file__).resolve()
        # config.py 在 Chrome/automation/legacy/，需要向上3级
        project_root = config_file.parent.parent.parent

# 最终验证：确保小说项目目录存在
if not (project_root / "小说项目").exists():
    # 如果还是找不到，尝试在当前目录及其父目录中查找
    search_dirs = [Path.cwd(), Path.cwd().parent, Path.cwd().parent.parent]
    for search_dir in search_dirs:
        if (search_dir / "小说项目").exists():
            project_root = search_dir
            break

CONFIG = {
    "debug_port": 9988,
    "novel_path": str(project_root / "小说项目"),  # 使用绝对路径
    "published_path": str(project_root / "已经发布"),  # 使用绝对路径
    "required_json_suffix": "项目信息.json",
    "timeouts": {
        "click": 15000,
        "fill": 12000,
        "wait_element": 5000
    },
    "auto_continue_delay": 10,
    "max_retries": 3,
    "min_words_for_scheduled_publish": 60000,
    "progress_file": "发布进度.json",
    "progress2_file": "发布进度细节.json",
    "date_format": "%Y-%m-%d",
    "time_format": "%H:%M",
    "scan_interval": 1800  # 每小时扫描一次（秒）
}

# 可配置参数
# 累计字数阈值，达到此值后才开始设置定时发布
WORD_COUNT_THRESHOLD = 20000

# 发布时间点列表，可修改此列表来调整发布时间
novel_publish_times = ["05:25", "11:25", "17:25", "23:25"]  # 可修改此列表

# 每个时间点最多发布的章节数
CHAPTERS_PER_TIME_SLOT = 2  # 可修改此值

# 发布时间缓冲，单位为分钟，当前为 35 分钟
PUBLISH_BUFFER_MINUTES = 35

# 番茄平台分类映射（从真实平台提取 - 2026年1月更新）
# 来源：番茄小说平台实际界面数据
PLATFORM_CATEGORIES = {
    "男频": {
        "main_category": [
            "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武", "悬疑灵异", "悬疑脑洞",
            "抗战谍战", "历史古代", "历史脑洞", "都市种田", "都市脑洞", "都市日常", "玄幻脑洞",
            "战神赘婿", "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
        ],
        "themes": [
            "衍生", "仕途", "综影视", "天灾", "第一人称", "赛博朋克", "第四天灾", "规则怪谈",
            "古代", "悬疑", "克苏鲁", "都市异能", "末日求生", "灵气复苏", "高武世界",
            "异世大陆", "东方玄幻", "谍战", "清朝", "宋朝", "断层", "武将", "国运", "综漫",
            "开局", "架空", "奇幻仙侠", "都市", "玄幻", "历史", "体育", "武侠"
        ],
        "roles": [
            "多女主", "赘婿", "全能", "大佬", "大小姐", "特工", "游戏主播", "神探",
            "宫廷侯爵", "皇帝", "单女主", "校花", "无女主", "女帝", "特种兵", "反派",
            "神医", "奶爸", "学霸", "天才", "腹黑", "扮猪吃虎"
        ],
        "plots": [
            "风水秘术", "斩神衍生", "十日衍生", "西游衍生", "公版衍生", "红楼衍生",
            "甄嬛衍生", "如懿衍生", "都市江湖", "惊悚游戏", "卡牌", "山海经", "捉鬼",
            "剑修", "废土", "副本", "黑科技", "无脑爽", "魂穿", "高手下山", "黑化",
            "迪化", "发家致富", "无后宫", "争霸", "1v1", "升级流", "灵魂互换", "封神",
            "四合院", "电竞", "双重生", "乡村", "同人", "打脸", "破案", "囤物资", "钓鱼",
            "网游", "奥特同人", "求生", "无敌", "九叔", "穿书", "聊天群", "大秦",
            "龙珠", "漫威", "神奇宝贝", "海贼", "火影", "职场", "明朝", "家庭",
            "三国", "末世", "直播", "无限流", "诸天万界", "大唐", "宠物", "外卖",
            "星际", "美食", "剑道", "盗墓", "灵异", "鉴宝", "系统", "神豪", "重生",
            "穿越", "二次元", "海岛", "娱乐圈", "空间", "推理", "洪荒"
        ]
    },
    "女频": {
        "main_category": [
            "古代言情", "现代言情", "玄幻言情", "科幻言情", "青春校园", "悬疑推理", "游戏竞技",
            "同人衍生", "次元幻想", "现实题材", "港台言情", "影视原著", "经典名著"
        ],
        "themes": [
            "甜宠", "虐恋", "穿书", "重生", "快穿", "系统", "空间", "爽文", "甜文", "虐文",
            "宫斗", "宅斗", "权谋", "江湖", "仙侠", "玄幻", "校园", "都市", "职场",
            "娱乐圈", "电竞", "直播", "美食", "萌宝", "种田", "经商", "军婚", "警匪",
            "悬疑", "推理", "惊悚", "灵异", "历史", "科幻", "奇幻", "神话", "武侠"
        ],
        "roles": [
            "总裁", "王爷", "皇帝", "影帝", "明星", "医生", "律师", "教授", "军人", "警察",
            "总裁夫人", "王妃", "皇后", "影后", "学霸", "校花", "才女", "美女", "主播", "网红",
            "霸道总裁", "温柔男主", "腹黑男主", "忠犬男主", "傲娇男主", "病娇男主", "清冷男主", "妖孽男主"
        ],
        "plots": [
            "先婚后爱", "一见钟情", "日久生情", "暗恋成真", "破镜重圆", "久别重逢", "青梅竹马",
            "欢喜冤家", "冤家路窄", "近水楼台", "朝夕相处", "共事", "邻居", "同事", "同学",
            "穿越", "重生", "系统", "空间", "快穿", "穿书", "玄幻", "修仙", "魔法", "异能",
            "宫斗", "宅斗", "权谋", "江湖", "武侠", "仙侠", "校园", "都市", "职场", "娱乐圈",
            "电竞", "直播", "美食", "萌宝", "种田", "经商", "军婚", "警匪", "悬疑", "推理",
            "惊悚", "灵异", "历史", "科幻", "奇幻", "神话", "同人", "衍生", "影视", "游戏"
        ]
    }
}

# 分类选择规则
CATEGORY_SELECTION_RULES = {
    "main_category": {
        "required": True,
        "max_count": 1,
        "description": "主分类必选且只能选一个，签约后不能修改"
    },
    "themes": {
        "required": False,
        "max_count": 2,
        "description": "主题最多可选两个"
    },
    "roles": {
        "required": False,
        "max_count": 2,
        "description": "角色最多可选两个"
    },
    "plots": {
        "required": False,
        "max_count": 2,
        "description": "情节最多可选两个"
    }
}