"""
封面生成服务
"""
import os
import re
import glob
from datetime import datetime
from urllib.parse import unquote
from typing import Dict, Any, List

from web.web_config import logger, BASE_DIR
from src.utils.DouBaoImageGenerator import DouBaoImageGenerator
from src.utils.NanoBananaProGenerator import NanoBananaProGenerator


class CoverService:
    """封面生成服务 - 支持多供应商"""
    
    def __init__(self):
        self.generators = {
            'doubao': DouBaoImageGenerator(),
            'nanobanana': NanoBananaProGenerator()
        }
        self.default_provider = 'doubao'
    
    def generate_cover(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成小说封面 - 支持多供应商"""
        try:
            # 验证必需参数
            required_fields = ['novel_title', 'custom_prompt']
            for field in required_fields:
                if not data.get(field):
                    return {
                        "success": False,
                        "error": f"缺少必需参数: {field}"
                    }
            
            # 获取供应商配置
            provider = data.get('provider', self.default_provider)
            if provider not in self.generators:
                provider = self.default_provider
            
            generator = self.generators[provider]
            
            # 验证供应商配置
            if hasattr(generator, 'validate_config') and not generator.validate_config():
                return {
                    "success": False,
                    "error": f"{provider} 供应商未正确配置 API Key"
                }
            
            # 构建最终的提示词
            final_prompt = self.build_final_prompt(data)
            
            # 生成参数 - 默认生成1张图片
            generation_count = min(data.get('generation_count', 1), 4)  # 最多生成4张
            image_size = data.get('image_size', '1K')
            add_watermark = data.get('add_watermark', False)
            
            # 获取小说标题并清理特殊字符
            novel_title = data.get('novel_title', '').strip()
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 获取当前用户名（按用户隔离）
            username = data.get('username', 'anonymous')
            if not username or username == 'anonymous':
                try:
                    from web.utils.path_utils import get_current_username
                    username = get_current_username()
                except Exception:
                    username = 'anonymous'
            
            logger.info(f"🎨 开始生成封面: {novel_title}, 用户: {username}, 供应商: {provider}")
            logger.info(f"📝 提示词长度: {len(final_prompt)} 字符")
            
            # 创建用户隔离的小说专用目录: generated_images/username/safe_title
            novel_cover_dir = os.path.join(BASE_DIR, 'generated_images', username, safe_title)
            os.makedirs(novel_cover_dir, exist_ok=True)
            
            # 批量生成图片
            generated_images = []
            for i in range(generation_count):
                try:
                    logger.info(f"正在生成第 {i+1}/{generation_count} 张封面...")
                    
                    # 生成包含小说信息的文件名
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{safe_title}_封面_{timestamp}_{i+1}.jpg"
                    save_path = os.path.join(novel_cover_dir, filename)
                    
                    # 根据不同供应商调用不同参数
                    if provider == 'nanobanana':
                        # NanoBanana Pro 使用 3:4 比例（适合书籍封面）
                        result = generator.generate_image(
                            prompt=final_prompt,
                            size=image_size,
                            save_path=save_path,
                            aspect_ratio="3:4"
                        )
                    else:
                        # 豆包使用原有参数
                        result = generator.generate_image(
                            prompt=final_prompt,
                            size=image_size,
                            watermark=add_watermark,
                            save_path=save_path
                        )
                    
                    if result and 'local_path' in result:
                        # 构建正确的图片URL路径（包含小说子目录）
                        relative_path = os.path.relpath(result['local_path'], os.path.join(BASE_DIR, 'generated_images')).replace('\\', '/')
                        image_url = f"/generated_images/{relative_path}"
                        
                        # 构建图片信息
                        image_info = {
                            "url": image_url,
                            "local_path": result['local_path'],
                            "size": image_size,
                            "timestamp": datetime.now().isoformat(),
                            "prompt": final_prompt,
                            "index": i + 1,
                            "novel_title": novel_title,  # 添加小说标题信息
                            "author_name": data.get('author_name', '北莽王庭的达延'),
                            "provider": provider  # 添加供应商信息
                        }
                        generated_images.append(image_info)
                        logger.info(f"✅ 第 {i+1} 张封面生成成功: {result['local_path']}")
                        logger.info(f"🔗 图片访问URL: {image_url}")
                    else:
                        logger.info(f"第 {i+1} 张封面生成失败")
                        
                except Exception as e:
                    logger.error(f"生成第 {i+1} 张封面时发生错误: {e}")
                    # 继续尝试生成其他图片
                    continue
            
            if not generated_images:
                return {
                    "success": False,
                    "error": "所有图片生成都失败了"
                }
            
            logger.info(f"🎉 封面生成完成: {len(generated_images)} 张成功")
            
            # 返回生成结果
            return {
                "success": True,
                "message": f"成功生成 {len(generated_images)} 张封面",
                "images": generated_images,
                "params": data
            }
            
        except Exception as e:
            logger.error(f"❌ 生成封面失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }

    def build_final_prompt(self, data: Dict[str, Any]) -> str:
        """构建番茄风格的网文封面提示词 - 高视觉冲击力的爽文审美"""
        novel_title = data.get('novel_title', '').strip()
        author_name = data.get('author_name', '北莽王庭的达延').strip()
        genre = data.get('genre', '').strip()
        style = data.get('style', '现代简约').strip()
        color_scheme = data.get('color_scheme', 'blue').strip()
        custom_prompt = data.get('custom_prompt', '').strip()
        negative_prompt = data.get('negative_prompt', '').strip()
        
        # 番茄风格类型映射 - 网文爽文审美
        genre_fanqie_styles = {
            '玄幻': {
                'atmosphere': '仙气缭绕/魔气滔天的史诗感',
                'elements': '主角光环、神兵利器、远古神兽、天地异象',
                'mood': '霸气张扬、唯我独尊、逆天改命'
            },
            '都市': {
                'atmosphere': '现代都市的繁华与神秘',
                'elements': '系统面板、财富象征、豪车豪宅、美女环绕、强者姿态',
                'mood': '低调奢华、强势崛起、扮猪吃虎'
            },
            '历史': {
                'atmosphere': '王朝争霸的恢弘气势',
                'elements': '龙袍冠冕、千军万马、权谋算计、江山社稷',
                'mood': '君临天下、运筹帷幄、豪情万丈'
            },
            '科幻': {
                'atmosphere': '未来科技的冷峻与宏大',
                'elements': '机甲战舰、星际战场、能量光环、数据流',
                'mood': '科技霸权、星际征服、人类荣耀'
            },
            '武侠': {
                'atmosphere': '江湖风云的快意恩仇',
                'elements': '神兵宝剑、绝世武功、门派标识、江湖气息',
                'mood': '侠骨柔情、一剑封喉、笑傲江湖'
            },
            '悬疑': {
                'atmosphere': '神秘诡谲的紧张氛围',
                'elements': '阴影迷雾、符号线索、诡异场景、心理压迫',
                'mood': '惊心动魄、步步紧逼、真相迷雾'
            },
            '游戏': {
                'atmosphere': '游戏世界的奇幻冒险',
                'elements': '游戏界面、技能特效、装备道具、等级标识',
                'mood': '升级快感、满级大佬、全服第一'
            },
            '国运': {
                'atmosphere': '国家荣耀与民族自豪感',
                'elements': '龙国标志、直播弹幕、禁地场景、国运绑定、民族象征',
                'mood': '为国争光、全球震惊、龙国崛起'
            },
            '修仙': {
                'atmosphere': '问道长生的飘渺仙气',
                'elements': '飞剑法宝、灵根异象、洞天福地、渡劫天雷',
                'mood': '逆天修仙、长生不死、大道争锋'
            },
            '末世': {
                'atmosphere': '末日废土的残酷生存',
                'elements': '废墟城市、丧尸怪物、生存装备、基地建设',
                'mood': '绝境求生、强者生存、重建文明'
            }
        }
        
        # 获取类型风格，默认为玄幻
        genre_style = genre_fanqie_styles.get(genre, genre_fanqie_styles['玄幻'])
        
        # 番茄风格配色 - 高饱和度网文审美
        fanqie_colors = {
            "blue": {
                "name": "深邃蓝金",
                "desc": "以深蓝色为底，搭配金色光效，营造神秘尊贵的王者气息"
            },
            "red": {
                "name": "炽焰红金", 
                "desc": "以炽红色为主，金色点缀，充满热血霸气的战斗氛围"
            },
            "green": {
                "name": "翡翠青冥",
                "desc": "以翠绿青碧为基调，仙气飘渺，适合修仙玄幻题材"
            },
            "purple": {
                "name": "紫气东来",
                "desc": "以深紫和金色搭配，神秘高贵，暗示主角不凡身份"
            },
            "gold": {
                "name": "至尊金黄",
                "desc": "以金色和黑色对比，奢华霸气，彰显无敌流主角气场"
            },
            "black": {
                "name": "暗夜黑红",
                "desc": "以黑色为底，红色光效，冷酷神秘，适合暗黑系主角"
            }
        }
        
        color_info = fanqie_colors.get(color_scheme, fanqie_colors['blue'])
        
        # 番茄风格封面提示词模板 - 高视觉冲击力
        base_prompt = f"""番茄小说风格封面设计，768×1024竖版，网文爽文审美，强视觉冲击力

【封面文字 - 必须清晰呈现】：
主标题：《{novel_title}》 - 要求字体大气醒目，有发光/描边效果
作者：{novel_title}  
作者名：{author_name} - 放在封面底部或右下角

【番茄风格设计要求】：
1. 视觉层次：前景主角（占画面60%）+ 中景元素 + 远景氛围
2. 主角形象：要有主角光环、强者气场、自信姿态，不能太普通
3. 色彩风格：{color_info['name']} - {color_info['desc']}
4. 光影效果：强烈的明暗对比，主角要有光效/特效环绕
5. 网文感：画面要有"爽点"暗示，让人一眼看出这是爽文

【类型特征 - {genre}】：
氛围：{genre_style['atmosphere']}
元素：{genre_style['elements']}
情绪：{genre_style['mood']}

【文字排版 - 番茄风格】：
- 书名大字居中偏上，占封面宽度80%，字体要霸气有设计感
- 书名要有发光效果或立体描边，确保在复杂背景上清晰可读
- 作者名小字放底部，不抢主角和书名的视觉焦点
- 严禁其他文字、水印、标签、平台标识

【绝对禁止】：
- 禁止"番茄小说"、"起点"、"晋江"等平台字样
- 禁止"连载中"、"完结"、"爆款"等标签
- 禁止除书名和作者名之外的任何文字
- 禁止二维码、网址、水印

【质量要求】：
- 高分辨率768×1024，清晰锐利
- 专业网文封面水准，符合番茄平台审美
- 缩略图模式下依然清晰醒目
- 目标：让读者在书架上一眼被吸引"""
        
        # 添加自定义提示词
        if custom_prompt:
            base_prompt += f"\n\n【额外要求】:\n{custom_prompt}"
        
        # 添加负面提示词
        if negative_prompt:
            base_prompt += f"\n\n【负面要求】:\n{negative_prompt}"
        else:
            base_prompt += """\n\n【负面要求】:
low quality, blurry, deformed, ugly, bad anatomy, watermark, signature, text error, extra text, cropped, worst quality, jpeg artifacts"""
        
        return base_prompt.strip()

    def get_novel_covers(self, title: str, username: str = None) -> Dict[str, Any]:
        """获取指定小说的封面列表"""
        try:
            # URL解码标题
            novel_title = unquote(title)
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 获取当前用户名（按用户隔离）
            if not username:
                try:
                    from web.utils.path_utils import get_current_username
                    username = get_current_username()
                except Exception:
                    username = 'anonymous'
            
            # 搜索generated_images目录中与小说相关的图片
            generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
            
            if not os.path.exists(generated_images_dir):
                return {
                    "success": True,
                    "covers": [],
                    "count": 0
                }
            
            # 优先查找用户隔离的小说子目录: generated_images/username/safe_title
            novel_cover_dir = os.path.join(generated_images_dir, username, safe_title)
            image_files = []
            
            if os.path.exists(novel_cover_dir):
                # 查找小说子目录中的所有jpg文件
                pattern = os.path.join(novel_cover_dir, "*.jpg")
                image_files = glob.glob(pattern)
                logger.info(f"在用户目录中找到 {len(image_files)} 个封面文件: {novel_cover_dir}")
            else:
                # 兼容性：查找旧路径（不带用户隔离）
                old_cover_dir = os.path.join(generated_images_dir, safe_title)
                if os.path.exists(old_cover_dir):
                    pattern = os.path.join(old_cover_dir, "*.jpg")
                    image_files = glob.glob(pattern)
                    if image_files:
                        logger.info(f"在旧路径找到 {len(image_files)} 个封面文件: {old_cover_dir}")
            
            covers = []
            for image_file in image_files:
                try:
                    # 获取文件信息
                    stat = os.stat(image_file)
                    filename = os.path.basename(image_file)
                    
                    # 生成Web访问URL（如果是在子目录中，需要包含子目录路径）
                    relative_path = os.path.relpath(image_file, generated_images_dir).replace('\\', '/')
                    web_url = f"/generated_images/{relative_path}"
                    
                    covers.append({
                        "id": filename,  # 使用文件名作为ID
                        "url": web_url,
                        "local_path": image_file,
                        "novel_title": novel_title,
                        "author_name": "北莽王庭的达延",
                        "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "file_size": stat.st_size,
                        "filename": filename
                    })
                except Exception as e:
                    logger.error(f"处理图片文件 {image_file} 时出错: {e}")
                    continue
            
            # 按时间排序，最新的在前
            covers.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"找到小说 '{novel_title}' 的 {len(covers)} 个封面文件")
            
            return {
                "success": True,
                "covers": covers,
                "count": len(covers),
                "novel_title": novel_title
            }
            
        except Exception as e:
            logger.error(f"获取小说封面失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_all_covers(self) -> Dict[str, Any]:
        """获取所有封面列表"""
        try:
            generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
            
            if not os.path.exists(generated_images_dir):
                return {
                    "success": True,
                    "covers": [],
                    "count": 0
                }
            
            covers = []
            
            # 遍历所有子目录和根目录的jpg文件
            for root, dirs, files in os.walk(generated_images_dir):
                for filename in files:
                    if filename.lower().endswith('.jpg'):
                        image_file = os.path.join(root, filename)
                        try:
                            stat = os.stat(image_file)
                            
                            # 生成相对路径和Web URL
                            relative_path = os.path.relpath(image_file, generated_images_dir).replace('\\', '/')
                            web_url = f"/generated_images/{relative_path}"
                            
                            # 从文件路径推断小说标题
                            # 如果文件在子目录中，使用子目录名作为小说标题
                            # 否则尝试从文件名中提取
                            novel_title = "未知小说"
                            if os.path.dirname(image_file) != generated_images_dir:
                                # 文件在子目录中，使用子目录名
                                dir_name = os.path.basename(os.path.dirname(image_file))
                                # 将下划线替换回空格，恢复原始标题
                                novel_title = dir_name.replace('_', ' ')
                            else:
                                # 文件在根目录中，尝试从文件名提取
                                if filename.startswith('doubao_'):
                                    # 豆包生成的文件，移除前缀
                                    clean_name = filename[7:].split('_')[0]  # 移除日期前缀
                                    if clean_name:
                                        novel_title = clean_name.replace('_', ' ')
                            
                            covers.append({
                                "id": filename,
                                "url": web_url,
                                "local_path": image_file,
                                "novel_title": novel_title,
                                "author_name": "北莽王庭的达延",
                                "timestamp": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "file_size": stat.st_size,
                                "filename": filename
                            })
                        except Exception as e:
                            logger.error(f"处理图片文件 {image_file} 时出错: {e}")
                            continue
            
            # 按时间排序，最新的在前
            covers.sort(key=lambda x: x['timestamp'], reverse=True)
            
            logger.info(f"找到总共 {len(covers)} 个封面文件")
            
            return {
                "success": True,
                "covers": covers,
                "count": len(covers)
            }
            
        except Exception as e:
            logger.error(f"获取所有封面失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def copy_cover_to_novel_directory(self, cover_url: str, novel_title: str) -> Dict[str, Any]:
        """将选中的封面拷贝到小说目录，覆盖原图片"""
        try:
            import shutil
            
            # URL解码
            cover_url = unquote(cover_url)
            
            # 构建源图片路径
            if cover_url.startswith('/generated_images/'):
                filename = cover_url.replace('/generated_images/', '')
                source_path = os.path.join(BASE_DIR, 'generated_images', filename)
            else:
                return {
                    "success": False,
                    "error": f"不支持的图片URL格式: {cover_url}"
                }
            
            # 检查源文件是否存在
            if not os.path.exists(source_path):
                return {
                    "success": False,
                    "error": f"源图片文件不存在: {source_path}"
                }
            
            # 清理小说标题中的特殊字符
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 构建目标路径 - 小说项目目录（正确的目录结构：小说项目/XXX小说/）
            novel_project_dir = os.path.join("小说项目", safe_title)
            
            # 确保目录存在
            os.makedirs(novel_project_dir, exist_ok=True)
            
            # 目标文件名 - 使用小说名作为文件名，与上传逻辑保持一致
            target_filename = f"{safe_title}_封面.jpg"
            target_path = os.path.join(novel_project_dir, target_filename)
            
            # 执行拷贝操作
            shutil.copy2(source_path, target_path)
            logger.info(f"✅ 封面拷贝成功: {source_path} -> {target_path}")
            
            return {
                "success": True,
                "message": f"封面已成功拷贝到小说目录: {target_filename}",
                "source_path": source_path,
                "target_path": target_path,
                "novel_title": novel_title,
                "cover_filename": target_filename
            }
            
        except Exception as e:
            logger.error(f"❌ 拷贝封面到小说目录失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"操作失败: {str(e)}"
            }

    def batch_copy_covers_to_novel_directories(self, covers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量将选中的封面拷贝到对应的小说目录"""
        try:
            import shutil
            
            results = []
            success_count = 0
            
            for cover_data in covers:
                cover_url = cover_data.get('cover_url')
                novel_title = cover_data.get('novel_title')
                
                if not cover_url or not novel_title:
                    results.append({
                        "cover_url": cover_url,
                        "novel_title": novel_title,
                        "success": False,
                        "error": "缺少必需参数"
                    })
                    continue
                
                # 调用单个拷贝逻辑
                try:
                    # URL解码
                    cover_url = unquote(cover_url)
                    
                    # 构建源图片路径
                    if cover_url.startswith('/generated_images/'):
                        filename = cover_url.replace('/generated_images/', '')
                        source_path = os.path.join(BASE_DIR, 'generated_images', filename)
                    else:
                        results.append({
                            "cover_url": cover_url,
                            "novel_title": novel_title,
                            "success": False,
                            "error": "不支持的图片URL格式"
                        })
                        continue
                    
                    # 检查源文件是否存在
                    if not os.path.exists(source_path):
                        results.append({
                            "cover_url": cover_url,
                            "novel_title": novel_title,
                            "success": False,
                            "error": "源图片文件不存在"
                        })
                        continue
                    
                    # 清理小说标题中的特殊字符
                    safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                    
                    # 构建目标路径
                    novel_project_dir = os.path.join("小说项目", safe_title)
                    os.makedirs(novel_project_dir, exist_ok=True)
                    
                    target_filename = f"{safe_title}_封面.jpg"
                    target_path = os.path.join(novel_project_dir, target_filename)
                    
                    # 执行拷贝
                    shutil.copy2(source_path, target_path)
                    logger.info(f"✅ 批量封面拷贝成功: {source_path} -> {target_path}")
                    
                    results.append({
                        "cover_url": cover_url,
                        "novel_title": novel_title,
                        "success": True,
                        "target_path": target_path,
                        "cover_filename": target_filename
                    })
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ 批量拷贝封面失败 {novel_title}: {e}")
                    results.append({
                        "cover_url": cover_url,
                        "novel_title": novel_title,
                        "success": False,
                        "error": str(e)
                    })
            
            return {
                "success": True,
                "message": f"批量拷贝完成，成功: {success_count}/{len(covers)}",
                "results": results,
                "success_count": success_count,
                "total_count": len(covers)
            }
            
        except Exception as e:
            logger.error(f"❌ 批量拷贝封面失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"批量操作失败: {str(e)}"
            }

    def serve_generated_image(self, filename: str):
        """提供生成的图片文件"""
        try:
            from flask import send_file
            
            # URL解码文件名
            decoded_filename = unquote(filename)
            
            # 构建完整的文件路径
            generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
            file_path = os.path.join(generated_images_dir, decoded_filename)
            
            # 安全检查：确保文件路径在允许的目录内
            if not os.path.abspath(file_path).startswith(os.path.abspath(generated_images_dir)):
                logger.error(f"尝试访问不允许的路径: {file_path}")
                return {"error": "访问被拒绝"}, 403
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                logger.error(f"图片文件不存在: {file_path}")
                return {"error": "图片文件不存在"}, 404
            
            # 检查是否为文件（不是目录）
            if not os.path.isfile(file_path):
                logger.error(f"路径不是文件: {file_path}")
                return {"error": "请求的不是文件"}, 400
            
            # 获取文件的MIME类型
            if decoded_filename.lower().endswith(('.jpg', '.jpeg')):
                mimetype = 'image/jpeg'
            elif decoded_filename.lower().endswith('.png'):
                mimetype = 'image/png'
            elif decoded_filename.lower().endswith('.gif'):
                mimetype = 'image/gif'
            else:
                mimetype = 'application/octet-stream'
            
            return send_file(
                file_path,
                mimetype=mimetype,
                as_attachment=False,
                download_name=decoded_filename
            )
            
        except Exception as e:
            logger.error(f"无法访问生成的图片 {filename}: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {"error": f"访问图片失败: {str(e)}"}, 500