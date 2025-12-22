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


class CoverService:
    """封面生成服务"""
    
    def __init__(self):
        self.generator = DouBaoImageGenerator()
    
    def generate_cover(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """生成小说封面"""
        try:
            # 验证必需参数
            required_fields = ['novel_title', 'custom_prompt']
            for field in required_fields:
                if not data.get(field):
                    return {
                        "success": False,
                        "error": f"缺少必需参数: {field}"
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
            
            logger.info(f"🎨 开始生成封面: {novel_title}")
            logger.info(f"📝 提示词长度: {len(final_prompt)} 字符")
            
            # 创建小说专用目录
            novel_cover_dir = os.path.join(BASE_DIR, 'generated_images', safe_title)
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
                    
                    # 生成单张图片，指定保存路径
                    result = self.generator.generate_image(
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
                            "author_name": data.get('author_name', '北莽王庭的达延')
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
        """构建最终的图片生成提示词"""
        novel_title = data.get('novel_title', '').strip()
        # 使用你指定的作者名作为默认值
        author_name = data.get('author_name', '北莽王庭的达延').strip()
        genre = data.get('genre', '').strip()
        style = data.get('style', '现代简约').strip()
        color_scheme = data.get('color_scheme', 'blue').strip()
        custom_prompt = data.get('custom_prompt', '').strip()
        negative_prompt = data.get('negative_prompt', '').strip()
        
        # 基础提示词模板
        base_prompt = f"""小说封面设计，768×1024像素，竖版比例，{style}风格

【封面文字内容】：
书名：《{novel_title}》
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
- 视觉效果吸引目标读者群体"""
        
        # 添加风格和类型特定的描述
        if genre:
            genre_descriptions = {
                '玄幻': '仙侠元素、奇幻场景',
                '都市': '现代都市背景、时尚人物',
                '历史': '古代建筑、传统元素',
                '科幻': '未来科技、太空场景',
                '武侠': '江湖气息、古风元素',
                '悬疑': '神秘氛围、推理元素',
                '游戏': '游戏界面、数字元素'
            }
            if genre in genre_descriptions:
                base_prompt += f"\n- 融入{genre_descriptions[genre]}"
        
        # 添加配色方案描述
        # 简化的配色方案
        colorSchemes = {
            "blue": "蓝色调",
            "red": "红色调",
            "green": "绿色调",
            "purple": "紫色调",
            "gold": "金色调"
        }
        
        if color_scheme in colorSchemes:
            base_prompt += f"\n- 主色调采用{colorSchemes[color_scheme]}"
        
        # 添加自定义提示词
        if custom_prompt:
            base_prompt += f"\n\n【自定义要求】:\n{custom_prompt}"
        
        # 添加负面提示词
        if negative_prompt:
            base_prompt += f"\n\n【严格禁止的内容】:\n{negative_prompt}"
        
        return base_prompt.strip()

    def get_novel_covers(self, title: str) -> Dict[str, Any]:
        """获取指定小说的封面列表"""
        try:
            # URL解码标题
            novel_title = unquote(title)
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
            
            # 搜索generated_images目录中与小说相关的图片
            generated_images_dir = os.path.join(BASE_DIR, 'generated_images')
            
            if not os.path.exists(generated_images_dir):
                return {
                    "success": True,
                    "covers": [],
                    "count": 0
                }
            
            # 优先查找小说专用子目录
            novel_cover_dir = os.path.join(generated_images_dir, safe_title)
            image_files = []
            
            if os.path.exists(novel_cover_dir):
                # 查找小说子目录中的所有jpg文件
                pattern = os.path.join(novel_cover_dir, "*.jpg")
                image_files = glob.glob(pattern)
                logger.info(f"在小说子目录中找到 {len(image_files)} 个封面文件: {novel_cover_dir}")
            else:
                # 兼容性：查找根目录中包含小说标题的图片文件
                pattern = os.path.join(generated_images_dir, f"*{safe_title}*.jpg")
                image_files = glob.glob(pattern)
                if image_files:
                    logger.info(f"在根目录中找到 {len(image_files)} 个包含小说名的封面文件")
            
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