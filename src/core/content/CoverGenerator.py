"""
封面生成器
负责小说封面的生成
"""

import os
import re
from typing import Dict, Optional


class CoverGenerator:
    """封面生成器类"""
    
    def __init__(self, cover_generator=None, username: str = None):
        self.cover_generator = cover_generator
        self._username = username  # 🔥 存储用户名用于用户隔离路径
        
        # 完整的风格模板字典，覆盖所有主分类
        self.style_templates = {
            # 女频分类风格
            "女频悬疑": "女性向悬疑风格，神秘氛围，柔和中带悬疑，淡雅色调与暗黑元素结合，细腻情感表达",
            "科幻末世": "赛博朋克风格，未来城市，机械装甲，霓虹灯光，科技感，金属质感，末日氛围",
            "女频衍生": "女性向衍生风格，二次元元素，精致人物设计，浪漫氛围，色彩柔和",
            "民国言情": "复古民国风格，旗袍，老上海风情，怀旧色调，浪漫与时代感结合",
            "悬疑脑洞": "创意悬疑风格，想象力丰富，离奇情节视觉化，神秘诡异氛围",
            "青春甜宠": "甜美青春风格，明亮色彩，浪漫场景，年轻角色，温馨治愈氛围",
            "双男主": "双男主CP风格，男性角色互动，帅气人物设计，热血或暧昧氛围",
            "古言脑洞": "古风创意风格，传统元素与现代脑洞结合，仙侠奇幻色彩",
            "现言脑洞": "现代都市奇幻风格，日常场景中的超现实元素，轻松幽默",
            "玄幻言情": "仙侠爱情风格，唯美场景，仙气缭绕，浪漫与修行结合",
            "宫斗宅斗": "古代宫廷风格，华丽服饰，权谋氛围，女性角色群像",
            "豪门总裁": "现代奢华风格，商务精英，豪门场景，浪漫霸道氛围",
            "动漫衍生": "二次元风格，动漫人物，日系画风，色彩明亮，角色鲜明",
            "星光璀璨": "娱乐圈风格，明星光环，舞台效果，时尚奢华",
            "游戏体育": "竞技热血风格，游戏或运动元素，动态感，团队精神",
            "职场婚恋": "都市情感风格，职场场景，现代生活，情感细腻",
            "双女主": "双女主CP风格，女性角色互动，优雅或帅气设计",
            "年代": "怀旧年代风格，特定时代元素，复古色调，历史感",
            "种田": "田园乡村风格，自然风光，农家生活，温馨朴实",
            "快穿": "多元时空风格，不同世界场景切换，穿越元素",
            
            # 男频分类风格
            "西方奇幻": "史诗奇幻风格，魔法光芒，巨龙，城堡，骑士，油画质感，神秘氛围",
            "东方仙侠": "水墨风格，仙气缭绕，飞剑，仙宫，修真者，传统国风，飘逸潇洒",
            "男频衍生": "热血战斗风格，主角特写，霸气侧漏，力量感，光影对比，电影质感",
            "都市高武": "现代都市与武道结合，都市夜景，武道气息，气功波动，力量感",
            "悬疑灵异": "暗黑风格，神秘氛围，阴影效果，诡异光线，悬疑感，冷色调",
            "抗战谍战": "历史战争风格，民国背景，谍战元素，紧张氛围，怀旧色调",
            "历史古代": "传统历史风格，古代场景，历史人物，文化底蕴",
            "历史脑洞": "创意历史风格，历史与幻想结合，穿越元素，幽默夸张",
            "都市种田": "现代田园风格，城市与自然结合，轻松生活氛围",
            "都市脑洞": "现代奇幻风格，都市生活中的超现实元素，创意想象",
            "都市日常": "温馨治愈风格，日常生活场景，柔和光线，温暖色彩，情感细腻",
            "玄幻脑洞": "创意奇幻风格，想象力丰富，奇特生物，异世界景观，色彩鲜艳",
            "战神赘婿": "霸气回归风格，主角逆袭，身份反差，豪华场景，金色红色主调",
            "传统玄幻": "经典玄幻风格，修行世界，法宝灵兽，传统仙侠元素",
            "都市修真": "现代修真风格，都市与修仙结合，灵气复苏，现代修仙者"
        }

    def generate_novel_cover(self, novel_title: str, novel_synopsis: str, category: str, author_name: str = "北莽王庭的达延") -> Dict:
        """
        生成小说封面
        
        Args:
            novel_title: 小说标题
            novel_synopsis: 小说简介
            category: 小说分类
            author_name: 作者名，默认为"北莽王庭的达延"
            
        Returns:
            生成结果字典
        """
        if not self.cover_generator:
            print("❌ 封面生成器不可用，跳过封面生成")
            return {"success": False, "error": "封面生成器不可用"}
        
        try:
            print("🎨 开始生成小说封面...")
            
            if not novel_title:
                print("❌ 小说标题为空，无法生成封面")
                return {"success": False, "error": "小说标题为空"}
            
            # 生成封面提示词
            cover_prompt = self._generate_cover_prompt(novel_title, novel_synopsis, category, author_name)
            
            print(f"  📝 封面提示词: {cover_prompt[:100]}...")
            
            # 创建小说项目目录（使用用户隔离路径）
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 🔥 使用用户隔离路径
            try:
                from web.utils.path_utils import get_user_novel_dir
                project_dir = get_user_novel_dir(username=self._username, create=True)
            except Exception as e:
                # 如果失败，使用默认路径
                print(f"  ⚠️ 获取用户隔离路径失败: {e}，使用默认路径")
                project_dir = "小说项目"
            
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            
            # 设置封面保存路径
            cover_filename = f"{safe_title}_封面.jpg"
            cover_path = os.path.join(project_dir, cover_filename)
            
            print(f"  💾 封面将保存到: {cover_path}")
            
            # 调用豆包文生图生成封面，使用600×800尺寸
            result = self.cover_generator.generate_image(
                prompt=cover_prompt,
                size="600x800",  # 固定为600×800像素
                watermark=False,  # 不加水印
                save_path=cover_path
            )
            
            if result and 'local_path' in result:
                print(f"✅ 封面生成成功: {result['local_path']}")
                print(f"📖 封面包含: 书名《{novel_title}》 作者: {author_name}")
                
                return {
                    "success": True,
                    "local_path": result['local_path'],
                    "cover_image": result['local_path'],
                    "cover_generated": True,
                    "novel_title": novel_title,
                    "author": author_name
                }
            else:
                print("❌ 封面生成失败")
                return {"success": False, "error": "封面生成失败"}
                
        except Exception as e:
            print(f"❌ 封面生成过程中出错: {e}")
            return {"success": False, "error": str(e)}

    def _generate_cover_prompt(self, title: str, synopsis: str, category: str, author_name: str = "北莽王庭的达延") -> str:
        """
        生成封面提示词 - 只包含书名和作者，无其他文字
        
        Args:
            title: 小说标题
            synopsis: 小说简介
            category: 小说分类
            author_name: 作者名，默认为"北莽王庭的达延"
            
        Returns:
            封面生成提示词
        """
        # 获取对应分类的风格，如果没有找到则使用默认风格
        style = self.style_templates.get(category, "精美插画风格，小说封面设计，符合类型特点")
        
        # 构建提示词 - 完全避免提及任何平台名称
        prompt = f"""
        小说封面设计，{style}，768×1024像素，竖版比例，简约风格

        【封面文字内容】：
        书名：《{title}》
        作者：{author_name}

        【严格禁止的内容】：
        - 绝对禁止添加任何其他文字
        - 禁止出现"番茄小说"、"番茄"、"起点"、"晋江"等任何平台相关文字
        - 禁止出现水印、标语、宣传语、广告语
        - 禁止任何额外标注文字（如"完结"、"爆笑"等标签）

        【设计要求】：
        - 封面设计精美，符合东方仙侠类型风格特色
        - 书名要醒目突出，使用清晰易读的艺术字体
        - 作者名放在适当位置（通常右下角或下方）
        - 整体设计专业简洁，具有商业出版品质
        - 背景与文字形成良好对比，确保可读性

        【色彩搭配】：
        - 根据小说东方仙侠类型选择合适的色调
        - 色彩要和谐统一，突出主题氛围
        - 避免过于花哨或单调的色彩搭配

        【图像元素】：
        - 可以包含与小说类型相关的背景图案或装饰元素
        - 图案要简约不抢夺文字主体地位
        - 如有人物，要符合东方仙侠类型特征

        【文字排版要求】：
        - 文字清晰可读但不要过于突兀
        - 文字与背景和谐统一
        - 字体选择要与整体设计风格匹配
        - 只能出现书名和作者名，无其他任何文字

        【质量要求】：
        - 高分辨率，清晰锐利
        - 专业级设计水准
        - 适合作为网络小说封面使用
        - 视觉效果吸引目标读者群体
        """
        
        return prompt.strip()

    def is_available(self) -> bool:
        """检查封面生成器是否可用"""
        return self.cover_generator is not None