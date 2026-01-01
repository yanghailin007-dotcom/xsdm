"""
Nano Banana文生图服务
提供文本生成图像的API服务，用于角色生成
"""
import os
import re
from datetime import datetime
from typing import Dict, Any, List

from web.web_config import logger, BASE_DIR
from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator


class NanoBananaService:
    """Nano Banana文生图服务（用于角色生成）"""
    
    def __init__(self):
        self.generator = NanoBananaImageGenerator()
    
    def generate_image(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成图像
        
        Args:
            data: 包含生成参数的字典
                - prompt: 提示词 (必需)
                - aspect_ratio: 图片比例 (可选，默认16:9)
                - image_size: 图片尺寸 (可选，默认4K)
                - save_filename: 保存文件名 (可选)
                
        Returns:
            dict: 包含生成结果的字典
        """
        try:
            # 验证必需参数
            prompt = data.get('prompt', '').strip()
            if not prompt:
                return {
                    "success": False,
                    "error": "缺少必需参数: prompt"
                }
            
            # 检查服务是否可用
            if not self.generator.is_available():
                return {
                    "success": False,
                    "error": "Nano Banana服务不可用，请检查API密钥配置"
                }
            
            # 获取参数
            aspect_ratio = data.get('aspect_ratio', '16:9')
            image_size = data.get('image_size', '4K')
            
            # 验证参数
            valid_ratios = ['16:9', '4:3', '1:1', '9:16']
            if aspect_ratio not in valid_ratios:
                return {
                    "success": False,
                    "error": f"不支持的图片比例: {aspect_ratio}，支持的值: {', '.join(valid_ratios)}"
                }
            
            valid_sizes = ['1K', '2K', '4K']
            if image_size not in valid_sizes:
                return {
                    "success": False,
                    "error": f"不支持的图片尺寸: {image_size}，支持的值: {', '.join(valid_sizes)}"
                }
            
            # 生成保存路径
            save_path = None
            if data.get('save_filename'):
                filename = data['save_filename']
                # 确保文件扩展名正确
                if not filename.endswith('.png'):
                    filename += '.png'
                save_path = str(BASE_DIR / 'generated_images' / filename)
            
            logger.info(f"🎨 开始生成Nano Banana图像")
            logger.info(f"   提示词: {prompt[:100]}...")
            logger.info(f"   比例: {aspect_ratio}, 尺寸: {image_size}")
            
            # 生成图像
            result = self.generator.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                save_path=save_path
            )
            
            if result.get('success'):
                logger.info(f"✅ Nano Banana图像生成成功: {result['local_path']}")
            else:
                logger.error(f"❌ Nano Banana图像生成失败: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 生成Nano Banana图像失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"生成失败: {str(e)}"
            }
    
    def batch_generate_images(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        批量生成图像
        
        Args:
            data: 包含批量生成参数的字典
                - prompts: 提示词列表 (必需)
                - aspect_ratio: 图片比例 (可选，默认16:9)
                - image_size: 图片尺寸 (可选，默认4K)
                - delay: 请求间隔秒数 (可选，默认1.0)
                
        Returns:
            dict: 包含批量生成结果的字典
        """
        try:
            # 验证必需参数
            prompts = data.get('prompts', [])
            if not prompts or not isinstance(prompts, list):
                return {
                    "success": False,
                    "error": "缺少必需参数: prompts (需要是列表)"
                }
            
            # 检查服务是否可用
            if not self.generator.is_available():
                return {
                    "success": False,
                    "error": "Nano Banana服务不可用，请检查API密钥配置"
                }
            
            # 获取参数
            aspect_ratio = data.get('aspect_ratio', '16:9')
            image_size = data.get('image_size', '4K')
            delay = data.get('delay', 1.0)
            
            logger.info(f"🎨 开始批量生成Nano Banana图像: {len(prompts)}张")
            
            # 批量生成
            results = self.generator.batch_generate(
                prompts=prompts,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
                delay=delay
            )
            
            success_count = len([r for r in results if r.get('success')])
            logger.info(f"🎉 批量生成完成: {success_count}/{len(prompts)} 成功")
            
            return {
                "success": True,
                "results": results,
                "total_count": len(prompts),
                "success_count": success_count,
                "failed_count": len(prompts) - success_count
            }
            
        except Exception as e:
            logger.error(f"❌ 批量生成Nano Banana图像失败: {e}")
            import traceback
            logger.error(f"详细错误: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"批量生成失败: {str(e)}"
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            dict: 包含服务状态的字典
        """
        try:
            from config.config import CONFIG
            config = CONFIG.get('nanobanana', {})
            
            return {
                "success": True,
                "enabled": self.generator.enabled,
                "available": self.generator.is_available(),
                "base_url": self.generator.base_url,
                "has_api_key": bool(self.generator.api_key),
                "timeout": self.generator.timeout,
                "max_retries": self.generator.max_retries,
                "supported_aspect_ratios": config.get('supported_aspect_ratios', []),
                "supported_image_sizes": config.get('supported_image_sizes', [])
            }
        except Exception as e:
            logger.error(f"❌ 获取Nano Banana服务状态失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }