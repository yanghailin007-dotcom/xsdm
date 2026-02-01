"""
TTS文字转语音API
集成MiniMax语音合成服务
"""

from flask import Blueprint, request, jsonify, send_from_directory
from pathlib import Path
import requests
import json
import os
from datetime import datetime
import time

# 创建蓝图
tts_api = Blueprint('tts_api', __name__, url_prefix='/api/tts')

# 导入日志记录器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 导入配置文件
try:
    from config.config import CONFIG
    MINIMAX_CONFIG = CONFIG.get("minimax_tts", {})
except ImportError:
    MINIMAX_CONFIG = {}

# 基础目录
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
VIDEO_PROJECTS_DIR = BASE_DIR / '视频项目'

# MiniMax TTS配置
TTS_CONFIG = {
    "async_url": "https://api.minimaxi.com/v1/t2a_async_v2",  # 异步API
    "query_url": "https://api.minimaxi.com/v1/query/t2a_async_query_v2",  # 查询API
    "files_url": "https://api.minimaxi.com/v1/files/retrieve",  # 文件检索API
    'model_audio': MINIMAX_CONFIG.get("model", 'speech-2.8-turbo'),
    'default_sample_rate': MINIMAX_CONFIG.get("default_sample_rate", 32000),
    'default_bitrate': MINIMAX_CONFIG.get("default_bitrate", 128000),
    'default_format': MINIMAX_CONFIG.get("default_format", 'mp3')
}

# 角色音色映射
CHARACTER_VOICES = MINIMAX_CONFIG.get("character_voices", {
    '林战': 'male-qn-qingse',
    '大长老': 'male-qn-jingying',
    '三长老': 'male-qn-yuansu',
    '叶凡': 'male-qn-qingche',
    '旁白': 'male-qn-pingshu',
    '系统音': 'female-qn-dahu',
    '林啸天': 'male-qn-wengeng',
    '默认': 'female-qn-dahu'
})

# MiniMax 官方完整音色列表 (speech-2.8-turbo 模型支持)
# 来源: https://platform.minimaxi.com/docs
# 最后更新: 2026-02-01
MINIMAX_ALL_VOICES = [
    # ===== 中文 (普通话) - 京剧风格音色 =====
    {"id": "male-qn-qingse", "name": "青涩青年", "lang": "zh", "desc": "适合青年男主"},
    {"id": "male-qn-jingying", "name": "精英青年", "lang": "zh", "desc": "精英青年音色"},
    {"id": "male-qn-badao", "name": "霸道青年", "lang": "zh", "desc": "霸道青年音色"},
    {"id": "male-qn-daxuesheng", "name": "青年大学生", "lang": "zh", "desc": "青年大学生音色"},
    {"id": "female-shaonv", "name": "少女", "lang": "zh", "desc": "少女音色"},
    {"id": "female-yujie", "name": "御姐", "lang": "zh", "desc": "御姐音色"},
    {"id": "female-chengshu", "name": "成熟女性", "lang": "zh", "desc": "成熟女性音色"},
    {"id": "female-tianmei", "name": "甜美女性", "lang": "zh", "desc": "甜美女性音色"},
    {"id": "male-qn-qingse-jingpin", "name": "青涩青年-beta", "lang": "zh", "desc": "青涩青年音色-beta"},
    {"id": "male-qn-jingying-jingpin", "name": "精英青年-beta", "lang": "zh", "desc": "精英青年音色-beta"},
    {"id": "male-qn-badao-jingpin", "name": "霸道青年-beta", "lang": "zh", "desc": "霸道青年音色-beta"},
    {"id": "male-qn-daxuesheng-jingpin", "name": "青年大学生-beta", "lang": "zh", "desc": "青年大学生音色-beta"},
    {"id": "female-shaonv-jingpin", "name": "少女-beta", "lang": "zh", "desc": "少女音色-beta"},
    {"id": "female-yujie-jingpin", "name": "御姐-beta", "lang": "zh", "desc": "御姐音色-beta"},
    {"id": "female-chengshu-jingpin", "name": "成熟女性-beta", "lang": "zh", "desc": "成熟女性音色-beta"},
    {"id": "female-tianmei-jingpin", "name": "甜美女性-beta", "lang": "zh", "desc": "甜美女性音色-beta"},

    # ===== 中文 (普通话) - 儿童/特殊音色 =====
    {"id": "clever_boy", "name": "聪明男童", "lang": "zh", "desc": "聪明男童"},
    {"id": "cute_boy", "name": "可爱男童", "lang": "zh", "desc": "可爱男童"},
    {"id": "lovely_girl", "name": "萌萌女童", "lang": "zh", "desc": "萌萌女童"},
    {"id": "cartoon_pig", "name": "卡通猪小琪", "lang": "zh", "desc": "卡通猪小琪"},
    {"id": "bingjiao_didi", "name": "病娇弟弟", "lang": "zh", "desc": "病娇弟弟"},
    {"id": "junlang_nanyou", "name": "俊朗男友", "lang": "zh", "desc": "俊朗男友"},
    {"id": "chunzhen_xuedi", "name": "纯真学弟", "lang": "zh", "desc": "纯真学弟"},
    {"id": "lengdan_xiongzhang", "name": "冷淡学长", "lang": "zh", "desc": "冷淡学长"},
    {"id": "badao_shaoye", "name": "霸道少爷", "lang": "zh", "desc": "霸道少爷"},
    {"id": "tianxin_xiaoling", "name": "甜心小玲", "lang": "zh", "desc": "甜心小玲"},
    {"id": "qiaopi_mengmei", "name": "俏皮萌妹", "lang": "zh", "desc": "俏皮萌妹"},
    {"id": "wumei_yujie", "name": "妩媚御姐", "lang": "zh", "desc": "妩媚御姐"},
    {"id": "diadia_xuemei", "name": "嗲嗲学妹", "lang": "zh", "desc": "嗲嗲学妹"},
    {"id": "danya_xuejie", "name": "淡雅学姐", "lang": "zh", "desc": "淡雅学姐"},

    # ===== 中文 (普通话) - 描述性音色ID =====
    {"id": "Chinese (Mandarin)_Reliable_Executive", "name": "沉稳高管", "lang": "zh", "desc": "沉稳高管"},
    {"id": "Chinese (Mandarin)_News_Anchor", "name": "新闻女声", "lang": "zh", "desc": "新闻女声"},
    {"id": "Chinese (Mandarin)_Mature_Woman", "name": "傲娇御姐", "lang": "zh", "desc": "傲娇御姐"},
    {"id": "Chinese (Mandarin)_Unrestrained_Young_Man", "name": "不羁青年", "lang": "zh", "desc": "不羁青年"},
    {"id": "Arrogant_Miss", "name": "嚣张小姐", "lang": "zh", "desc": "嚣张小姐"},
    {"id": "Robot_Armor", "name": "机械战甲", "lang": "zh", "desc": "机械战甲"},
    {"id": "Chinese (Mandarin)_Kind-hearted_Antie", "name": "热心大婶", "lang": "zh", "desc": "热心大婶"},
    {"id": "Chinese (Mandarin)_HK_Flight_Attendant", "name": "港普空姐", "lang": "zh", "desc": "港普空姐"},
    {"id": "Chinese (Mandarin)_Humorous_Elder", "name": "搞笑大爷", "lang": "zh", "desc": "搞笑大爷"},
    {"id": "Chinese (Mandarin)_Gentleman", "name": "温润男声", "lang": "zh", "desc": "温润男声"},
    {"id": "Chinese (Mandarin)_Warm_Bestie", "name": "温暖闺蜜", "lang": "zh", "desc": "温暖闺蜜"},
    {"id": "Chinese (Mandarin)_Male_Announcer", "name": "播报男声", "lang": "zh", "desc": "播报男声"},
    {"id": "Chinese (Mandarin)_Sweet_Lady", "name": "甜美女声", "lang": "zh", "desc": "甜美女声"},
    {"id": "Chinese (Mandarin)_Southern_Young_Man", "name": "南方小哥", "lang": "zh", "desc": "南方小哥"},
    {"id": "Chinese (Mandarin)_Wise_Women", "name": "阅历姐姐", "lang": "zh", "desc": "阅历姐姐"},
    {"id": "Chinese (Mandarin)_Gentle_Youth", "name": "温润青年", "lang": "zh", "desc": "温润青年"},
    {"id": "Chinese (Mandarin)_Warm_Girl", "name": "温暖少女", "lang": "zh", "desc": "温暖少女"},
    {"id": "Chinese (Mandarin)_Kind-hearted_Elder", "name": "花甲奶奶", "lang": "zh", "desc": "花甲奶奶"},
    {"id": "Chinese (Mandarin)_Cute_Spirit", "name": "憨憨萌兽", "lang": "zh", "desc": "憨憨萌兽"},
    {"id": "Chinese (Mandarin)_Radio_Host", "name": "电台男主播", "lang": "zh", "desc": "电台男主播"},
    {"id": "Chinese (Mandarin)_Lyrical_Voice", "name": "抒情男声", "lang": "zh", "desc": "抒情男声"},
    {"id": "Chinese (Mandarin)_Straightforward_Boy", "name": "率真弟弟", "lang": "zh", "desc": "率真弟弟"},
    {"id": "Chinese (Mandarin)_Sincere_Adult", "name": "真诚青年", "lang": "zh", "desc": "真诚青年"},
    {"id": "Chinese (Mandarin)_Gentle_Senior", "name": "温柔学姐", "lang": "zh", "desc": "温柔学姐"},
    {"id": "Chinese (Mandarin)_Stubborn_Friend", "name": "嘴硬竹马", "lang": "zh", "desc": "嘴硬竹马"},
    {"id": "Chinese (Mandarin)_Crisp_Girl", "name": "清脆少女", "lang": "zh", "desc": "清脆少女"},
    {"id": "Chinese (Mandarin)_Pure-hearted_Boy", "name": "清澈邻家弟弟", "lang": "zh", "desc": "清澈邻家弟弟"},
    {"id": "Chinese (Mandarin)_Soft_Girl", "name": "柔和少女", "lang": "zh", "desc": "柔和少女"},

    # ===== 粤语 =====
    {"id": "Cantonese_ProfessionalHost（F）", "name": "专业女主持(粤语)", "lang": "yue", "desc": "专业女主持"},
    {"id": "Cantonese_GentleLady", "name": "温柔女声(粤语)", "lang": "yue", "desc": "温柔女声"},
    {"id": "Cantonese_ProfessionalHost（M）", "name": "专业男主持(粤语)", "lang": "yue", "desc": "专业男主持"},
    {"id": "Cantonese_PlayfulMan", "name": "活泼男声(粤语)", "lang": "yue", "desc": "活泼男声"},
    {"id": "Cantonese_CuteGirl", "name": "可爱女孩(粤语)", "lang": "yue", "desc": "可爱女孩"},
    {"id": "Cantonese_KindWoman", "name": "善良女声(粤语)", "lang": "yue", "desc": "善良女声"},

    # ===== 英文 =====
    {"id": "Santa_Claus", "name": "Santa Claus", "lang": "en", "desc": "Santa Claus"},
    {"id": "Grinch", "name": "Grinch", "lang": "en", "desc": "Grinch"},
    {"id": "Rudolph", "name": "Rudolph", "lang": "en", "desc": "Rudolph"},
    {"id": "Arnold", "name": "Arnold", "lang": "en", "desc": "Arnold"},
    {"id": "Charming_Santa", "name": "Charming Santa", "lang": "en", "desc": "Charming Santa"},
    {"id": "Charming_Lady", "name": "Charming Lady", "lang": "en", "desc": "Charming Lady"},
    {"id": "Sweet_Girl", "name": "Sweet Girl", "lang": "en", "desc": "Sweet Girl"},
    {"id": "Cute_Elf", "name": "Cute Elf", "lang": "en", "desc": "Cute Elf"},
    {"id": "Attractive_Girl", "name": "Attractive Girl", "lang": "en", "desc": "Attractive Girl"},
    {"id": "Serene_Woman", "name": "Serene Woman", "lang": "en", "desc": "Serene Woman"},
    {"id": "English_Trustworthy_Man", "name": "Trustworthy Man", "lang": "en", "desc": "Trustworthy Man"},
    {"id": "English_Graceful_Lady", "name": "Graceful Lady", "lang": "en", "desc": "Graceful Lady"},
    {"id": "English_Aussie_Bloke", "name": "Aussie Bloke", "lang": "en", "desc": "Aussie Bloke"},
    {"id": "English_Whispering_girl", "name": "Whispering girl", "lang": "en", "desc": "Whispering girl"},
    {"id": "English_Diligent_Man", "name": "Diligent Man", "lang": "en", "desc": "Diligent Man"},
    {"id": "English_Gentle-voiced_man", "name": "Gentle-voiced man", "lang": "en", "desc": "Gentle-voiced man"},

    # ===== 日文 =====
    {"id": "Japanese_IntellectualSenior", "name": "Intellectual Senior(日)", "lang": "ja", "desc": "Intellectual Senior"},
    {"id": "Japanese_DecisivePrincess", "name": "Decisive Princess(日)", "lang": "ja", "desc": "Decisive Princess"},
    {"id": "Japanese_LoyalKnight", "name": "Loyal Knight(日)", "lang": "ja", "desc": "Loyal Knight"},
    {"id": "Japanese_DominantMan", "name": "Dominant Man(日)", "lang": "ja", "desc": "Dominant Man"},
    {"id": "Japanese_SeriousCommander", "name": "Serious Commander(日)", "lang": "ja", "desc": "Serious Commander"},
    {"id": "Japanese_ColdQueen", "name": "Cold Queen(日)", "lang": "ja", "desc": "Cold Queen"},
    {"id": "Japanese_DependableWoman", "name": "Dependable Woman(日)", "lang": "ja", "desc": "Dependable Woman"},
    {"id": "Japanese_GentleButler", "name": "Gentle Butler(日)", "lang": "ja", "desc": "Gentle Butler"},
    {"id": "Japanese_KindLady", "name": "Kind Lady(日)", "lang": "ja", "desc": "Kind Lady"},
    {"id": "Japanese_CalmLady", "name": "Calm Lady(日)", "lang": "ja", "desc": "Calm Lady"},
    {"id": "Japanese_OptimisticYouth", "name": "Optimistic Youth(日)", "lang": "ja", "desc": "Optimistic Youth"},
    {"id": "Japanese_GenerousIzakayaOwner", "name": "Generous Izakaya Owner(日)", "lang": "ja", "desc": "Generous Izakaya Owner"},
    {"id": "Japanese_SportyStudent", "name": "Sporty Student(日)", "lang": "ja", "desc": "Sporty Student"},
    {"id": "Japanese_InnocentBoy", "name": "Innocent Boy(日)", "lang": "ja", "desc": "Innocent Boy"},
    {"id": "Japanese_GracefulMaiden", "name": "Graceful Maiden(日)", "lang": "ja", "desc": "Graceful Maiden"},

    # ===== 韩文 =====
    {"id": "Korean_SweetGirl", "name": "Sweet Girl(韩)", "lang": "ko", "desc": "Sweet Girl"},
    {"id": "Korean_CheerfulBoyfriend", "name": "Cheerful Boyfriend(韩)", "lang": "ko", "desc": "Cheerful Boyfriend"},
    {"id": "Korean_EnchantingSister", "name": "Enchanting Sister(韩)", "lang": "ko", "desc": "Enchanting Sister"},
    {"id": "Korean_ShyGirl", "name": "Shy Girl(韩)", "lang": "ko", "desc": "Shy Girl"},
    {"id": "Korean_ReliableSister", "name": "Reliable Sister(韩)", "lang": "ko", "desc": "Reliable Sister"},
    {"id": "Korean_StrictBoss", "name": "Strict Boss(韩)", "lang": "ko", "desc": "Strict Boss"},
    {"id": "Korean_SassyGirl", "name": "Sassy Girl(韩)", "lang": "ko", "desc": "Sassy Girl"},
    {"id": "Korean_ChildhoodFriendGirl", "name": "Childhood Friend Girl(韩)", "lang": "ko", "desc": "Childhood Friend Girl"},
    {"id": "Korean_PlayboyCharmer", "name": "Playboy Charmer(韩)", "lang": "ko", "desc": "Playboy Charmer"},
    {"id": "Korean_ElegantPrincess", "name": "Elegant Princess(韩)", "lang": "ko", "desc": "Elegant Princess"},
    {"id": "Korean_BraveFemaleWarrior", "name": "Brave Female Warrior(韩)", "lang": "ko", "desc": "Brave Female Warrior"},
    {"id": "Korean_BraveYouth", "name": "Brave Youth(韩)", "lang": "ko", "desc": "Brave Youth"},
    {"id": "Korean_CalmLady", "name": "Calm Lady(韩)", "lang": "ko", "desc": "Calm Lady"},
    {"id": "Korean_EnthusiasticTeen", "name": "Enthusiastic Teen(韩)", "lang": "ko", "desc": "Enthusiastic Teen"},
    {"id": "Korean_SoothingLady", "name": "Soothing Lady(韩)", "lang": "ko", "desc": "Soothing Lady"},
    {"id": "Korean_IntellectualSenior", "name": "Intellectual Senior(韩)", "lang": "ko", "desc": "Intellectual Senior"},
    {"id": "Korean_LonelyWarrior", "name": "Lonely Warrior(韩)", "lang": "ko", "desc": "Lonely Warrior"},
    {"id": "Korean_MatureLady", "name": "Mature Lady(韩)", "lang": "ko", "desc": "Mature Lady"},
    {"id": "Korean_InnocentBoy", "name": "Innocent Boy(韩)", "lang": "ko", "desc": "Innocent Boy"},
    {"id": "Korean_CharmingSister", "name": "Charming Sister(韩)", "lang": "ko", "desc": "Charming Sister"},
    {"id": "Korean_AthleticStudent", "name": "Athletic Student(韩)", "lang": "ko", "desc": "Athletic Student"},
    {"id": "Korean_BraveAdventurer", "name": "Brave Adventurer(韩)", "lang": "ko", "desc": "Brave Adventurer"},
    {"id": "Korean_CalmGentleman", "name": "Calm Gentleman(韩)", "lang": "ko", "desc": "Calm Gentleman"},
    {"id": "Korean_WiseElf", "name": "Wise Elf(韩)", "lang": "ko", "desc": "Wise Elf"},
    {"id": "Korean_CheerfulCoolJunior", "name": "Cheerful Cool Junior(韩)", "lang": "ko", "desc": "Cheerful Cool Junior"},
    {"id": "Korean_DecisiveQueen", "name": "Decisive Queen(韩)", "lang": "ko", "desc": "Decisive Queen"},
    {"id": "Korean_ColdYoungMan", "name": "Cold Young Man(韩)", "lang": "ko", "desc": "Cold Young Man"},
    {"id": "Korean_MysteriousGirl", "name": "Mysterious Girl(韩)", "lang": "ko", "desc": "Mysterious Girl"},
    {"id": "Korean_QuirkyGirl", "name": "Quirky Girl(韩)", "lang": "ko", "desc": "Quirky Girl"},
    {"id": "Korean_ConsiderateSenior", "name": "Considerate Senior(韩)", "lang": "ko", "desc": "Considerate Senior"},
    {"id": "Korean_CheerfulLittleSister", "name": "Cheerful Little Sister(韩)", "lang": "ko", "desc": "Cheerful Little Sister"},
    {"id": "Korean_DominantMan", "name": "Dominant Man(韩)", "lang": "ko", "desc": "Dominant Man"},
    {"id": "Korean_AirheadedGirl", "name": "Airheaded Girl(韩)", "lang": "ko", "desc": "Airheaded Girl"},
    {"id": "Korean_ReliableYouth", "name": "Reliable Youth(韩)", "lang": "ko", "desc": "Reliable Youth"},
    {"id": "Korean_FriendlyBigSister", "name": "Friendly Big Sister(韩)", "lang": "ko", "desc": "Friendly Big Sister"},
    {"id": "Korean_GentleBoss", "name": "Gentle Boss(韩)", "lang": "ko", "desc": "Gentle Boss"},
    {"id": "Korean_ColdGirl", "name": "Cold Girl(韩)", "lang": "ko", "desc": "Cold Girl"},
    {"id": "Korean_HaughtyLady", "name": "Haughty Lady(韩)", "lang": "ko", "desc": "Haughty Lady"},
    {"id": "Korean_CharmingElderSister", "name": "Charming Elder Sister(韩)", "lang": "ko", "desc": "Charming Elder Sister"},
    {"id": "Korean_IntellectualMan", "name": "Intellectual Man(韩)", "lang": "ko", "desc": "Intellectual Man"},
    {"id": "Korean_CaringWoman", "name": "Caring Woman(韩)", "lang": "ko", "desc": "Caring Woman"},
    {"id": "Korean_WiseTeacher", "name": "Wise Teacher(韩)", "lang": "ko", "desc": "Wise Teacher"},
    {"id": "Korean_ConfidentBoss", "name": "Confident Boss(韩)", "lang": "ko", "desc": "Confident Boss"},
    {"id": "Korean_AthleticGirl", "name": "Athletic Girl(韩)", "lang": "ko", "desc": "Athletic Girl"},
    {"id": "Korean_PossessiveMan", "name": "Possessive Man(韩)", "lang": "ko", "desc": "Possessive Man"},
    {"id": "Korean_GentleWoman", "name": "Gentle Woman(韩)", "lang": "ko", "desc": "Gentle Woman"},
    {"id": "Korean_CockyGuy", "name": "Cocky Guy(韩)", "lang": "ko", "desc": "Cocky Guy"},
    {"id": "Korean_ThoughtfulWoman", "name": "Thoughtful Woman(韩)", "lang": "ko", "desc": "Thoughtful Woman"},
    {"id": "Korean_OptimisticYouth", "name": "Optimistic Youth(韩)", "lang": "ko", "desc": "Optimistic Youth"},

    # ===== 其他常用语言音色（泰语、波兰语、罗马尼亚语等）=====
    {"id": "Thai_male_1_sample8", "name": "Serene Man(泰)", "lang": "th", "desc": "Serene Man"},
    {"id": "Thai_male_2_sample2", "name": "Friendly Man(泰)", "lang": "th", "desc": "Friendly Man"},
    {"id": "Thai_female_1_sample1", "name": "Confident Woman(泰)", "lang": "th", "desc": "Confident Woman"},
    {"id": "Thai_female_2_sample2", "name": "Energetic Woman(泰)", "lang": "th", "desc": "Energetic Woman"},
    {"id": "Polish_male_1_sample4", "name": "Male Narrator(波兰)", "lang": "pl", "desc": "Male Narrator"},
    {"id": "Polish_male_2_sample3", "name": "Male Anchor(波兰)", "lang": "pl", "desc": "Male Anchor"},
    {"id": "Polish_female_1_sample1", "name": "Calm Woman(波兰)", "lang": "pl", "desc": "Calm Woman"},
    {"id": "Polish_female_2_sample3", "name": "Casual Woman(波兰)", "lang": "pl", "desc": "Casual Woman"},
    {"id": "Romanian_male_1_sample2", "name": "Reliable Man(罗马尼亚)", "lang": "ro", "desc": "Reliable Man"},
    {"id": "Romanian_male_2_sample1", "name": "Energetic Youth(罗马尼亚)", "lang": "ro", "desc": "Energetic Youth"},
    {"id": "Romanian_female_1_sample4", "name": "Optimistic Youth(罗马尼亚)", "lang": "ro", "desc": "Optimistic Youth"},
    {"id": "Romanian_female_2_sample1", "name": "Gentle Woman(罗马尼亚)", "lang": "ro", "desc": "Gentle Woman"},
]


class TTSManager:
    """TTS管理器"""

    def __init__(self):
        # 优先从环境变量读取，其次从配置文件读取
        self.group_id = os.getenv('MINIMAX_GROUP_ID') or MINIMAX_CONFIG.get("group_id", '')
        self.api_key = os.getenv('MINIMAX_API_KEY') or MINIMAX_CONFIG.get("api_key", '')

    def generate_speech(self, text, voice_id='female-qn-dahu', speed=1.0, pitch=0, vol=1.0):
        """
        生成语音 (使用异步API)

        Args:
            text: 要转换的文本
            voice_id: 音色ID
            speed: 语速 0.5-2.0
            pitch: 音调 -12到12
            vol: 音量 0.1-10.0

        Returns:
            {"success": bool, "audio_url": str, "audio_path": str, "duration": float}
        """
        if not self.group_id or not self.api_key:
            return {
                'success': False,
                'error': '未配置MiniMax API密钥，请在 config/config.py 中配置 minimax_tts.group_id 和 api_key'
            }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # 按照新API格式构建请求
        payload = {
            'model': TTS_CONFIG['model_audio'],
            'text': text,
            'voice_setting': {
                'voice_id': voice_id,
                'speed': speed,
                'vol': vol,
                'pitch': pitch
            },
            'audio_setting': {
                'audio_sample_rate': TTS_CONFIG['default_sample_rate'],
                'bitrate': TTS_CONFIG['default_bitrate'],
                'format': TTS_CONFIG['default_format'],
                'channel': 1
            },
            'language_boost': 'Chinese'
        }

        try:
            logger.info(f'🎙️ [TTS] 提交异步任务: voice_id={voice_id}, text="{text[:30]}..."')
            logger.info(f'🎙️ [TTS] 请求URL: {TTS_CONFIG["async_url"]}')
            logger.info(f'🎙️ [TTS] 请求参数: model={TTS_CONFIG["model_audio"]}, speed={speed}, pitch={pitch}, vol={vol}')

            # 第一步：提交异步任务
            submit_response = requests.post(
                TTS_CONFIG['async_url'],
                headers=headers,
                json=payload,
                timeout=30
            )

            logger.info(f'🎙️ [TTS] 响应状态码: {submit_response.status_code}')

            if submit_response.status_code != 200:
                logger.error(f'TTS任务提交失败: {submit_response.status_code} - {submit_response.text}')
                return {
                    'success': False,
                    'error': f'任务提交失败: HTTP {submit_response.status_code}'
                }

            submit_data = submit_response.json()
            logger.info(f'🎙️ [TTS] 响应数据: {submit_data}')

            # 检查base_resp
            if 'base_resp' in submit_data:
                base_resp = submit_data['base_resp']
                logger.info(f'🎙️ [TTS] base_resp: status_code={base_resp.get("status_code")}, status_msg={base_resp.get("status_msg")}')
                if base_resp.get('status_code') != 0:
                    error_msg = base_resp.get('status_msg', '未知错误')
                    return {
                        'success': False,
                        'error': f'API返回错误: {error_msg} (code: {base_resp.get("status_code")})'
                    }

            # 获取task_id
            task_id = submit_data.get('task_id')
            if not task_id:
                logger.error(f'TTS响应缺少task_id: {submit_data}')
                return {
                    'success': False,
                    'error': f'API响应异常: 未返回task_id'
                }

            logger.info(f'🎙️ [TTS] 任务已提交: task_id={task_id}')

            # 第二步：轮询查询任务状态
            max_attempts = 60  # 最多查询60次
            poll_interval = 2  # 每2秒查询一次
            last_log_time = time.time()

            logger.info(f'🎙️ [TTS] 开始轮询任务状态，最多{max_attempts}次，间隔{poll_interval}秒')

            for attempt in range(max_attempts):
                query_url = f"{TTS_CONFIG['query_url']}?task_id={task_id}"

                query_response = requests.get(
                    query_url,
                    headers=headers,
                    timeout=10
                )

                if query_response.status_code != 200:
                    logger.warning(f'🎙️ [TTS] 查询任务状态失败: {query_response.status_code}')
                    time.sleep(poll_interval)
                    continue

                query_data = query_response.json()
                status = query_data.get('status', 'Unknown')

                # 每10秒或状态变化时记录一次日志
                current_time = time.time()
                if current_time - last_log_time >= 10 or attempt == 0:
                    logger.info(f'🎙️ [TTS] 任务状态: {status} ({attempt + 1}/{max_attempts})')
                    last_log_time = current_time

                if status == 'Success':
                    # 任务成功完成
                    file_id = query_data.get('file_id')
                    logger.info(f'🎙️ [TTS] 任务完成，file_id={file_id}')

                    # 🔥 使用 /v1/files/retrieve 获取下载链接
                    retrieve_url = f"https://api.minimaxi.com/v1/files/retrieve?file_id={file_id}"
                    retrieve_response = requests.get(
                        retrieve_url,
                        headers=headers,
                        timeout=10
                    )

                    if retrieve_response.status_code != 200:
                        logger.error(f'🎙️ [TTS] 获取文件信息失败: {retrieve_response.status_code}')
                        return {
                            'success': False,
                            'error': f'获取文件信息失败: HTTP {retrieve_response.status_code}'
                        }

                    retrieve_data = retrieve_response.json()
                    logger.info(f'🎙️ [TTS] 文件信息: {retrieve_data}')

                    if 'file' not in retrieve_data:
                        return {
                            'success': False,
                            'error': '文件信息异常'
                        }

                    file_info = retrieve_data['file']
                    download_url = file_info.get('download_url')
                    filename = file_info.get('filename', '')

                    if not download_url:
                        return {
                            'success': False,
                            'error': '未获取到下载链接'
                        }

                    logger.info(f'🎙️ [TTS] 下载音频文件: {filename}')

                    # 下载音频文件
                    audio_response = requests.get(download_url, timeout=30)
                    if audio_response.status_code == 200:
                        import base64

                        # 检查是否是tar包（包含音频+字幕+元数据）
                        if filename.endswith('.tar'):
                            import tarfile
                            import io
                            import os

                            # 解析tar包
                            tar_data = io.BytesIO(audio_response.content)
                            audio_base64 = None

                            with tarfile.open(fileobj=tar_data, mode='r') as tar:
                                for member in tar.getmembers():
                                    if member.name.endswith('.mp3') or member.name.endswith('.wav'):
                                        f = tar.extractfile(member)
                                        if f:
                                            audio_content = f.read()
                                            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                                            logger.info(f'🎙️ [TTS] 从tar包中提取音频: {member.name} ({len(audio_content)} bytes)')
                                            break

                            if not audio_base64:
                                logger.error(f'🎙️ [TTS] tar包内容: {tarfile.getmembers(tar_data)}')
                                return {
                                    'success': False,
                                    'error': 'tar包中未找到音频文件'
                                }
                        else:
                            # 直接是音频文件
                            audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')

                        # 估算时长
                        duration = len(text) / 3.5

                        return {
                            'success': True,
                            'audio_base64': audio_base64,
                            'download_url': download_url,
                            'file_id': str(file_id),
                            'task_id': str(task_id),
                            'duration': duration,
                            'text_length': len(text)
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'下载音频失败: HTTP {audio_response.status_code}'
                        }

                elif status == 'Failed':
                    error_info = query_data.get('error_info', {})
                    error_msg = error_info.get('message', '未知错误')
                    return {
                        'success': False,
                        'error': f'任务失败: {error_msg}'
                    }

                elif status == 'Expired':
                    return {
                        'success': False,
                        'error': '任务已过期'
                    }

                # Processing状态，继续轮询
                time.sleep(poll_interval)

            # 超时
            return {
                'success': False,
                'error': f'任务超时 (超过{max_attempts * poll_interval}秒)'
            }

        except requests.exceptions.Timeout:
            logger.error(f'TTS请求超时')
            return {
                'success': False,
                'error': '请求超时，请稍后重试'
            }
        except Exception as e:
            logger.error(f'TTS生成失败: {e}')
            import traceback
            logger.error(f'错误堆栈: {traceback.format_exc()}')
            return {
                'success': False,
                'error': str(e)
            }

    def save_audio(self, audio_base64, output_path):
        """保存音频文件"""
        try:
            import base64
            audio_data = base64.b64decode(audio_base64)

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(audio_data)

            logger.info(f'🎙️ [TTS] 音频已保存: {output_path}')
            return str(output_path)
        except Exception as e:
            logger.error(f'保存音频失败: {e}')
            return None


# 全局TTS管理器实例
tts_manager = TTSManager()


@tts_api.route('/config', methods=['GET'])
def get_tts_config():
    """获取TTS配置状态"""
    return jsonify({
        'success': True,
        'configured': bool(tts_manager.group_id and tts_manager.api_key),
        'voices': CHARACTER_VOICES
    })


@tts_api.route('/config', methods=['POST'])
def update_tts_config():
    """更新TTS配置"""
    try:
        data = request.json
        group_id = data.get('group_id')
        api_key = data.get('api_key')

        if group_id and api_key:
            # 更新环境变量
            os.environ['MINIMAX_GROUP_ID'] = group_id
            os.environ['MINIMAX_API_KEY'] = api_key
            tts_manager.group_id = group_id
            tts_manager.api_key = api_key

            return jsonify({
                'success': True,
                'message': 'TTS配置已更新'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'group_id和api_key不能为空'
            }), 400

    except Exception as e:
        logger.error(f'更新TTS配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/voices', methods=['GET'])
def get_available_voices():
    """获取可用音色列表（返回所有官方音色 + 角色映射）"""
    return jsonify({
        'success': True,
        'voices': MINIMAX_ALL_VOICES,
        'character_voices': CHARACTER_VOICES
    })


@tts_api.route('/generate', methods=['POST'])
def generate_speech():
    """
    生成单个镜头的配音

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scene_number": 1,
        "event_name": "起因",  # 中级事件名
        "speaker": "林战",
        "lines": "老祖宗……苏醒了！",
        "voice_id": "male-qn-qingse",
        "speed": 1.0,
        "pitch": 0,
        "vol": 1.0
    }
    """
    try:
        data = request.json

        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scene_number = data.get('scene_number') or data.get('shot_number')
        event_name = data.get('event_name', '')  # 中级事件名
        speaker = data.get('speaker', '默认')
        lines = data.get('lines', '')
        voice_id = data.get('voice_id')
        speed = float(data.get('speed', 1.0))
        pitch = int(data.get('pitch', 0))
        vol = float(data.get('vol', 1.0))

        if not lines:
            return jsonify({
                'success': False,
                'error': '台词内容不能为空'
            }), 400

        # 使用指定的音色，或根据角色名选择默认音色
        final_voice_id = voice_id or CHARACTER_VOICES.get(speaker, CHARACTER_VOICES['默认'])

        # 生成语音
        result = tts_manager.generate_speech(lines, final_voice_id, speed, pitch, vol)

        if result.get('success'):
            # 保存音频文件
            from src.managers.VeOVideoManager import sanitize_path

            episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'

            # 文件名格式: {镜头号}_{事件名}_{角色}.mp3（与视频命名保持一致）
            safe_event = sanitize_path(event_name) if event_name else ''
            safe_speaker = sanitize_path(speaker)

            if safe_event:
                filename = f"{scene_number}_{safe_event}_{safe_speaker}.mp3"
            else:
                filename = f"{scene_number}_{safe_speaker}.mp3"

            audio_path = episode_dir / filename

            saved_path = tts_manager.save_audio(result['audio_base64'], audio_path)

            # 生成音频URL
            from urllib.parse import quote
            rel_path = audio_path.relative_to(VIDEO_PROJECTS_DIR)
            audio_url = f"/api/tts/audio/{quote(str(rel_path), safe='')}"

            result['audio_path'] = saved_path
            result['audio_url'] = audio_url
            result['filename'] = filename

        return jsonify(result)

    except Exception as e:
        logger.error(f'生成配音失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/generate-batch', methods=['POST'])
def generate_batch_speech():
    """
    批量生成配音

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scenes": [...]
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scenes = data.get('scenes', [])

        if not scenes:
            return jsonify({
                'success': False,
                'error': 'scenes不能为空'
            }), 400

        results = []
        success_count = 0

        for i, scene in enumerate(scenes):
            scene_number = scene.get('scene_number') or scene.get('shot_number') or (i + 1)

            # 检查是否有台词
            dialogue = scene.get('dialogue') or scene.get('_dialogue_data', {})
            if isinstance(dialogue, dict):
                speaker = dialogue.get('speaker', '')
                lines = dialogue.get('lines', '')
            else:
                speaker = str(dialogue) if dialogue else ''
                lines = ''

            if not speaker or not lines or speaker == '无':
                results.append({
                    'scene_number': scene_number,
                    'success': False,
                    'skipped': True,
                    'reason': '无台词'
                })
                continue

            # 确定音色
            voice_id = CHARACTER_VOICES.get(speaker, CHARACTER_VOICES['默认'])

            # 生成语音
            result = tts_manager.generate_speech(lines, voice_id)

            if result.get('success'):
                # 保存音频文件
                from src.managers.VeOVideoManager import sanitize_path

                episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'

                # 文件名格式: {镜头号}_{事件名}_{角色}.mp3（与视频命名保持一致）
                event_name = scene.get('event_name') or scene.get('event') or ''
                safe_event = sanitize_path(event_name) if event_name else ''
                safe_speaker = sanitize_path(speaker)

                if safe_event:
                    filename = f"{scene_number}_{safe_event}_{safe_speaker}.mp3"
                else:
                    filename = f"{scene_number}_{safe_speaker}.mp3"

                audio_path = episode_dir / filename

                saved_path = tts_manager.save_audio(result['audio_base64'], audio_path)

                from urllib.parse import quote
                rel_path = audio_path.relative_to(VIDEO_PROJECTS_DIR)
                audio_url = f"/api/tts/audio/{quote(str(rel_path), safe='')}"

                results.append({
                    'scene_number': scene_number,
                    'success': True,
                    'audio_url': audio_url,
                    'filename': filename,
                    'speaker': speaker,
                    'lines': lines,
                    'duration': result.get('duration', 0)
                })
                success_count += 1
            else:
                results.append({
                    'scene_number': scene_number,
                    'success': False,
                    'error': result.get('error', '未知错误')
                })

            # 避免API限流，每次请求间隔1秒
            time.sleep(1)

        return jsonify({
            'success': True,
            'results': results,
            'total': len(scenes),
            'success_count': success_count,
            'failed_count': len(scenes) - success_count
        })

    except Exception as e:
        logger.error(f'批量生成配音失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/audio/<path:filepath>', methods=['GET'])
def serve_audio_file(filepath):
    """提供音频文件访问"""
    try:
        from urllib.parse import unquote

        decoded_path = unquote(filepath)
        file_path = VIDEO_PROJECTS_DIR / decoded_path

        if file_path.exists() and file_path.is_file():
            return send_from_directory(str(file_path.parent), file_path.name)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        logger.error(f'提供音频访问失败: {e}')
        return jsonify({'error': str(e)}), 500


@tts_api.route('/download-batch', methods=['POST'])
def download_batch_audio():
    """
    批量下载音频文件（打包成ZIP）

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集名"
    }
    """
    try:
        import zipfile
        import io
        from urllib.parse import quote

        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')

        if not novel_title or not episode_title:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 音频目录
        audio_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'

        if not audio_dir.exists():
            return jsonify({'success': False, 'error': '音频目录不存在'}), 404

        # 收集所有音频文件
        audio_files = list(audio_dir.glob('*.mp3'))

        if not audio_files:
            return jsonify({'success': False, 'error': '没有音频文件'}), 404

        # 创建内存中的ZIP文件
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in audio_files:
                zf.write(file_path, file_path.name)

        memory_file.seek(0)

        # 生成ZIP文件名
        zip_filename = f"{quote(episode_title)}_配音合集.zip"

        # 返回ZIP文件
        from flask import Response
        response = Response(
            memory_file.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )

        logger.info(f'📦 [TTS] 批量下载ZIP: {len(audio_files)} 个文件')
        return response

    except Exception as e:
        logger.error(f'批量下载失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@tts_api.route('/list-audio', methods=['GET'])
def list_audio_files():
    """
    列出指定项目的所有音频文件

    参数：
        novel_title: 小说名
        episode_title: 集数名
    """
    try:
        novel_title = request.args.get('novel')
        episode_title = request.args.get('episode')

        if not novel_title or not episode_title:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 音频目录
        audio_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'

        logger.info(f'🎙️ [音频列表] 检查目录: {audio_dir}')

        if not audio_dir.exists():
            return jsonify({'success': True, 'audios': []})

        # 收集所有音频文件
        audio_files = []
        for audio_path in audio_dir.glob('*.mp3'):
            # 解析文件名: {scene_number}_{event_name}_{speaker}.mp3
            filename = audio_path.stem  # 不含扩展名
            parts = filename.split('_', 2)

            scene_number = int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else None
            event_name = parts[1] if len(parts) > 1 else ''
            speaker = parts[2] if len(parts) > 2 else ''

            logger.info(f'  📄 文件: {audio_path.name}')
            logger.info(f'     scene_number={scene_number}, event_name="{event_name}", speaker="{speaker}"')

            # 生成URL
            from urllib.parse import quote
            rel_path = audio_path.relative_to(VIDEO_PROJECTS_DIR)
            audio_url = f"/api/tts/audio/{quote(str(rel_path), safe='')}"

            audio_files.append({
                'filename': audio_path.name,
                'scene_number': scene_number,
                'event_name': event_name,
                'speaker': speaker,
                'path': str(audio_path),
                'url': audio_url
            })

        logger.info(f'🎙️ [音频列表] 找到 {len(audio_files)} 个音频文件')

        return jsonify({
            'success': True,
            'audios': audio_files
        })

    except Exception as e:
        logger.error(f'列出音频文件失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@tts_api.route('/export-subtitle', methods=['POST'])
def export_subtitle():
    """
    导出SRT字幕文件

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scenes": [...]
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scenes = data.get('scenes', [])

        # 生成SRT内容
        srt_content = []
        current_time = 0  # 当前时间（秒）

        for scene in scenes:
            scene_number = scene.get('scene_number') or scene.get('shot_number') or 1
            duration = scene.get('duration', 5)

            # 获取台词信息
            dialogue = scene.get('dialogue') or scene.get('_dialogue_data', {})
            if isinstance(dialogue, dict):
                speaker = dialogue.get('speaker', '')
                lines = dialogue.get('lines', '')
                tone = dialogue.get('tone', '')
            else:
                speaker = str(dialogue) if dialogue else ''
                lines = ''

            if not speaker or not lines or speaker == '无':
                # 无台词，跳过
                current_time += duration
                continue

            # 计算开始和结束时间
            start_time = current_time
            end_time = current_time + duration

            # 格式化为SRT时间格式
            def format_srt_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

            srt_content.append(f"{scene_number}")
            srt_content.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
            srt_content.append(f"{speaker}: {lines}")
            srt_content.append("")

            current_time += duration

        srt_text = '\n'.join(srt_content)

        # 保存SRT文件
        subtitle_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'subtitles'
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        subtitle_file = subtitle_dir / f"{episode_title}_配音字幕.srt"

        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write(srt_text)

        logger.info(f'📝 SRT字幕已生成: {subtitle_file}')

        return jsonify({
            'success': True,
            'subtitle_file': str(subtitle_file),
            'content': srt_text
        })

    except Exception as e:
        logger.error(f'导出字幕失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 路由注册函数 ====================

def register_tts_routes(app):
    """注册TTS API路由"""
    app.register_blueprint(tts_api)
    logger.debug("✅ TTS API路由已注册")
