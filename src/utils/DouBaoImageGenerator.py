from pathlib import Path
import sys
# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import requests
import json
import os
import sys
from datetime import datetime
import time
import logging
from openai import OpenAI
from src.utils.logger import get_logger
from config.doubaoconfig import API_URL, ARK_API_KEY, DEFAULT_MODEL, DEFAULT_SIZE, FILE_CONFIG, REQUEST_CONFIG


class DouBaoImageGenerator:
    def __init__(self, api_key=None, base_url=None):
        """
        初始化豆包文生图客户端
        
        Args:
            api_key: API密钥，如果为None则从配置获取
            base_url: API基础URL，如果为None则使用默认值
        """
        self.logger = get_logger("DouBaoImageGenerator")
        self.api_key = api_key or ARK_API_KEY
        self.base_url = base_url or API_URL
        
        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError(
                "请设置ARK_API_KEY环境变量或在config.py中配置API密钥\n"
                "Linux/Mac: export ARK_API_KEY='your_actual_api_key'\n"
                "Windows: set ARK_API_KEY=your_actual_api_key"
            )
        
        # 使用OpenAI客户端
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            self.logger.info("✅ OpenAI客户端初始化成功")
        except Exception as e:
            self.logger.error(f"❌ OpenAI客户端初始化失败: {e}")
            raise e
        
        # 确保输出目录存在
        if FILE_CONFIG['auto_create_dir']:
            output_dir = os.path.join(BASE_DIR, FILE_CONFIG['default_output_dir'])
            os.makedirs(output_dir, exist_ok=True)
        
        logging.info("豆包文生图客户端初始化完成")
    
    def generate_image(self, prompt, size=None, model=None, 
                      watermark=False, save_path=None):
        """
        生成图像
        
        Args:
            prompt: 提示词
            size: 图片尺寸，默认为2K
            model: 模型名称
            watermark: 是否添加水印
            save_path: 保存路径，如果为None则自动生成
            
        Returns:
            dict: 包含生成结果的字典
        """
        # 设置默认值
        model = model or DEFAULT_MODEL
        size = size or DEFAULT_SIZE
        
        if size not in ['1K', '2K']:
            logging.warning(f"不支持的尺寸: {size}，使用默认值: {DEFAULT_SIZE}")
            size = DEFAULT_SIZE
        
        try:
            logging.info("开始生成图像...")
            logging.debug(f"请求参数 - 模型: {model}, 尺寸: {size}, 水印: {watermark}")
            start_time = time.time()
            
            # 完全按照test.py的方式调用
            # 将豆包的尺寸格式转换为OpenAI支持的格式
            size_mapping = {
                '1K': '1024x1024',
                '2K': '1024x1792'  # 使用较高的分辨率
            }
            openai_size = size_mapping.get(size, '1024x1024')
            
            # 确保尺寸是OpenAI支持的格式
            valid_sizes = ['256x256', '512x512', '1024x1024', '1792x1024', '1024x1792']
            if openai_size not in valid_sizes:
                openai_size = '1024x1024'  # 默认尺寸
            
            imagesResponse = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=openai_size,  # type: ignore
                response_format="url",
                extra_body={
                    "watermark": watermark,
                },
            )
            
            end_time = time.time()
            logging.info(f"图像生成成功! 耗时: {end_time - start_time:.2f}秒")
            
            # 构建结果字典
            result = {
                'data': [{'url': imagesResponse.data[0].url}],
                'created': getattr(imagesResponse, 'created', None),
            }
            
            # 豆包API可能不支持usage信息，跳过此项
            # if hasattr(imagesResponse, 'usage'):
            #     result['usage'] = imagesResponse.usage
            
            # 下载并保存图像
            if imagesResponse.data and len(imagesResponse.data) > 0 and imagesResponse.data[0].url:
                image_url = imagesResponse.data[0].url
                
                # 下载图像
                saved_path = self._download_image(image_url, save_path, prompt)
                result['local_path'] = saved_path
            else:
                raise Exception("API返回的图像数据为空或URL无效")
                
            return result
            
        except Exception as e:
            error_msg = f"生成图像时发生错误: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def _download_image(self, image_url, save_path, prompt):
        """
        下载图像到本地
        
        Args:
            image_url: 图像URL
            save_path: 保存路径
            prompt: 提示词（用于生成文件名）
            
        Returns:
            str: 保存的文件路径
        """
        try:
            # 获取图像数据
            logging.info("正在下载图像...")
            image_response = requests.get(image_url, timeout=30)
            image_response.raise_for_status()
            
            # 生成文件名
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 清理提示词用于文件名
                clean_name = "".join(x for x in prompt[:30] if x.isalnum() or x in (' ', '-', '_')).strip()
                clean_name = clean_name.replace(' ', '_')
                filename = f"{FILE_CONFIG['filename_prefix']}{timestamp}_{clean_name}.{FILE_CONFIG['default_format']}"
                
                # 确保使用项目根目录的generated_images目录
                output_dir = os.path.join(BASE_DIR, FILE_CONFIG['default_output_dir'])
                save_path = os.path.join(output_dir, filename)
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # 保存图像
            with open(save_path, 'wb') as f:
                f.write(image_response.content)
            
            logging.info(f"图像已保存到: {save_path}")
            return save_path
            
        except Exception as e:
            error_msg = f"下载图像失败: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def batch_generate(self, prompts, size=None, output_dir=None, delay=1):
        """
        批量生成图像
        
        Args:
            prompts: 提示词列表或字典{名称: 提示词}
            size: 图片尺寸
            output_dir: 输出目录
            delay: 请求间隔(秒)
            
        Returns:
            list: 生成结果列表
        """
        results = []
        # 确保使用项目根目录的generated_images目录
        if output_dir is None:
            output_dir = os.path.join(BASE_DIR, FILE_CONFIG['default_output_dir'])
        os.makedirs(output_dir, exist_ok=True)
        
        # 处理提示词格式
        if isinstance(prompts, list):
            prompt_items = [(f"batch_{i+1}", prompt) for i, prompt in enumerate(prompts)]
        elif isinstance(prompts, dict):
            prompt_items = list(prompts.items())
        else:
            raise ValueError("prompts必须是列表或字典")
        
        for name, prompt in prompt_items:
            logging.info(f"正在生成图像 '{name}'...")
            try:
                save_path = os.path.join(output_dir, f"{name}_{datetime.now().strftime('%H%M%S')}.jpg")
                result = self.generate_image(prompt, size=size, save_path=save_path, watermark=False)
                result['name'] = name
                results.append(result)
                
                # 避免频繁调用，添加延迟
                if delay > 0:
                    time.sleep(delay)
                
            except Exception as e:
                logging.error(f"图像 '{name}' 生成失败: {str(e)}")
                results.append({"error": str(e), "name": name, "prompt": prompt})
        
        success_count = len([r for r in results if 'error' not in r])
        logging.info(f"批量生成完成，成功: {success_count}/{len(prompt_items)}")
        
        return results
    
    def get_usage_info(self):
        """
        获取API使用信息（如果API支持）
        注意：这个功能需要API支持相应的端点
        """
        logging.info("使用量统计功能需要API支持相应端点")
        return {"message": "功能待实现"}


def create_prompt_template():
        prompt = f"""
        小说封面设计，768×1024像素，竖版比例，简约风格

        【封面文字内容】：
        书名：《我爱我家》
        作者：北莽王庭的达延
        
        【严格禁止的内容】：
        - 禁止添加任何其他文字
        - 禁止出现"番茄小说"、"番茄"等平台相关文字
        - 禁止水印、标语、宣传语
        - 禁止任何额外标注文字
        
        【设计要求】：
        - 封面设计精美，符合科幻类型风格
        - 书名要醒目突出，使用清晰易读的字体
        - 作者名放在适当位置
        - 背景设计基于: 
        - 整体设计专业简洁
        
        【文字要求】：
        - 文字清晰可读但不要过于突兀
        - 文字与背景和谐统一
        - 只能出现书名和作者
        """
        
        return prompt.strip()


def main():
    """主函数演示"""
    try:
        # 初始化生成器
        generator = DouBaoImageGenerator()

        # 示例提示词 - 与test.py完全相同
        prompt = create_prompt_template()

        generator.logger.info("开始生成示例图像...")
        # 生成图像 - 完全按照test.py的方式，watermark=False确保无水印
        result = generator.generate_image(
            prompt=prompt,
            size="2K",
            watermark=False
        )

        generator.logger.info("\n" + "="*50)
        generator.logger.info("生成完成!")
        if 'local_path' in result:
            generator.logger.info(f"图像文件: {result['local_path']}")

        # 显示URL（与test.py输出一致）
        if 'data' in result and len(result['data']) > 0:
            generator.logger.info(f"图像URL: {result['data'][0]['url']}")

    except Exception as e:
        logging.error(f"错误: {e}")
        logging.error(f"主程序执行失败: {e}")


if __name__ == "__main__":
    main()