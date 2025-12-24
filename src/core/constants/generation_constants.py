"""
生成流程相关常量定义
包含小说生成过程中使用的各种常量和配置
"""

# 默认配置
DEFAULT_TOTAL_CHAPTERS = 200
DEFAULT_CHAPTERS_PER_BATCH = 3
DEFAULT_QUALITY_THRESHOLD = 8.0

# 评分权重配置
QUALITY_WEIGHT = 0.8
FRESHNESS_WEIGHT = 0.2

# 质量评估阈值
HIGH_QUALITY_THRESHOLD = 9.0
MEDIUM_QUALITY_THRESHOLD = 8.2
LOW_QUALITY_THRESHOLD = 6.5

# 新鲜度评估阈值
HIGH_FRESHNESS_THRESHOLD = 8.0
MEDIUM_FRESHNESS_THRESHOLD = 6.0
LOW_FRESHNESS_THRESHOLD = 4.0

# 文件大小和内容限制
MAX_FILE_SIZE_MB = 10
MAX_CONTENT_LENGTH = 10000
MIN_CHAPTER_LENGTH = 1000
MAX_CHAPTER_LENGTH = 5000

# 路径配置
PROJECT_BASE_DIR = "小说项目"
BACKUP_DIR = "backup"
TEMP_DIR = "temp"
CHAPTERS_DIR = "chapters"
MATERIALS_DIR = "materials"

# 时间配置
BATCH_DELAY_SECONDS = 2
LONG_BATCH_DELAY_SECONDS = 5
GENERATION_TIMEOUT_SECONDS = 300

# 重试配置
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 5

# 小说分类列表
NOVEL_CATEGORIES = [
    "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武",
    "悬疑灵异", "悬疑脑洞", "抗战谍战", "历史古代", "历史脑洞",
    "都市种田", "都市脑洞", "都市日常", "玄幻脑洞", "战神赘婿",
    "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
]

# 女频分类
FEMALE_CATEGORIES = [
    "女频悬疑", "科幻末世", "女频衍生", "民国言情", "悬疑脑洞",
    "青春甜宠", "双男主", "古言脑洞", "现言脑洞", "玄幻言情",
    "宫斗宅斗", "豪门总裁", "动漫衍生", "星光璀璨", "游戏体育",
    "职场婚恋", "双女主", "年代", "种田", "快穿"
]

# 生成阶段定义
GENERATION_STAGES = {
    "PLANNING": "规划阶段",
    "WORLDVIEW": "世界观构建", 
    "CHARACTER_DESIGN": "角色设计",
    "STAGE_PLANNING": "阶段规划",
    "CONTENT_GENERATION": "内容生成",
    "QUALITY_ASSESSMENT": "质量评估",
    "FINALIZATION": "完成阶段"
}

# 事件类型定义
EVENT_TYPES = {
    "CHAPTER_GENERATED": "chapter.generated",
    "CHAPTER_ASSESSED": "chapter.assessed",
    "ERROR_OCCURRED": "error.occurred",
    "STAGE_PLAN_READY": "stage.plan.ready",
    "FORESHADOWING_PREPARE": "foreshadowing.prepare",
    "EVENT_PREPARE": "event.prepare",
    "GROWTH_PREPARE": "growth.prepare"
}

# 错误类型定义
ERROR_TYPES = {
    "GENERATION_FAILED": "generation_failed",
    "CONTEXT_NONE": "context_none",
    "CONTEXT_INVALID": "context_invalid",
    "VALIDATION_FAILED": "validation_failed"
}

__all__ = [
    # 默认配置
    'DEFAULT_TOTAL_CHAPTERS',
    'DEFAULT_CHAPTERS_PER_BATCH',
    'DEFAULT_QUALITY_THRESHOLD',
    
    # 评分权重
    'QUALITY_WEIGHT',
    'FRESHNESS_WEIGHT',
    
    # 质量阈值
    'HIGH_QUALITY_THRESHOLD',
    'MEDIUM_QUALITY_THRESHOLD', 
    'LOW_QUALITY_THRESHOLD',
    
    # 新鲜度阈值
    'HIGH_FRESHNESS_THRESHOLD',
    'MEDIUM_FRESHNESS_THRESHOLD',
    'LOW_FRESHNESS_THRESHOLD',
    
    # 文件限制
    'MAX_FILE_SIZE_MB',
    'MAX_CONTENT_LENGTH',
    'MIN_CHAPTER_LENGTH',
    'MAX_CHAPTER_LENGTH',
    
    # 路径配置
    'PROJECT_BASE_DIR',
    'BACKUP_DIR',
    'TEMP_DIR',
    'CHAPTERS_DIR',
    'MATERIALS_DIR',
    
    # 时间配置
    'BATCH_DELAY_SECONDS',
    'LONG_BATCH_DELAY_SECONDS',
    'GENERATION_TIMEOUT_SECONDS',
    
    # 重试配置
    'MAX_RETRY_ATTEMPTS',
    'RETRY_DELAY_SECONDS',
    
    # 分类列表
    'NOVEL_CATEGORIES',
    'FEMALE_CATEGORIES',
    
    # 阶段和事件定义
    'GENERATION_STAGES',
    'EVENT_TYPES',
    'ERROR_TYPES'
]