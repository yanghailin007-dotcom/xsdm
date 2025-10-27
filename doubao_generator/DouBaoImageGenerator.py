import requests
import json
import os
from datetime import datetime
import time
import logging

from doubao_generator.doubaoconfig import API_URL, ARK_API_KEY, DEFAULT_MODEL, DEFAULT_SIZE, FILE_CONFIG, QUALITY_SETTINGS, REQUEST_CONFIG

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('doubao_generator.log'),
        logging.StreamHandler()
    ]
)

class DouBaoImageGenerator:
    def __init__(self, api_key=None, base_url=None):
        """
        初始化豆包文生图客户端
        
        Args:
            api_key: API密钥，如果为None则从配置获取
            base_url: API基础URL，如果为None则从配置获取
        """
        self.api_url = base_url or API_URL
        self.api_key = api_key or ARK_API_KEY
        
        if not self.api_key or self.api_key == 'your_api_key_here':
            raise ValueError(
                "请设置ARK_API_KEY环境变量或在config.py中配置API密钥\n"
                "Linux/Mac: export ARK_API_KEY='your_actual_api_key'\n"
                "Windows: set ARK_API_KEY=your_actual_api_key"
            )
        
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 确保输出目录存在
        if FILE_CONFIG['auto_create_dir']:
            os.makedirs(FILE_CONFIG['default_output_dir'], exist_ok=True)
        
        logging.info("豆包文生图客户端初始化完成")
    
    def generate_image(self, prompt, size=None, model=None, 
                      watermark=False, save_path=None, quality_preset='high'):
        """
        生成图像
        
        Args:
            prompt: 提示词
            size: 图片尺寸，默认为2K
            model: 模型名称
            watermark: 是否添加水印
            save_path: 保存路径，如果为None则自动生成
            quality_preset: 质量预设 'high' 或 'fast'
            
        Returns:
            dict: 包含生成结果的字典
        """
        # 设置默认值
        model = model or DEFAULT_MODEL
        size = size or DEFAULT_SIZE
        
        if size not in ['1K', '2K']:
            logging.warning(f"不支持的尺寸: {size}，使用默认值: {DEFAULT_SIZE}")
            size = DEFAULT_SIZE
        
        # 构建请求数据
        data = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "sequential_image_generation": "disabled",
            "stream": False,
            "response_format": "url",
            "watermark": watermark
        }
        
        # 应用质量预设
        if quality_preset in QUALITY_SETTINGS:
            data.update(QUALITY_SETTINGS[quality_preset])
        
        try:
            logging.info("开始生成图像...")
            logging.debug(f"请求参数: {json.dumps(data, ensure_ascii=False)}")
            start_time = time.time()
            
            # 发送请求
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=REQUEST_CONFIG['timeout']
            )
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败: {response.status_code} - {response.text}"
                logging.error(error_msg)
                raise Exception(error_msg)
            
            result = response.json()
            end_time = time.time()
            
            logging.info(f"图像生成成功! 耗时: {end_time - start_time:.2f}秒")
            
            # 打印使用情况
            if 'usage' in result:
                usage = result['usage']
                logging.info(f"使用情况 - 生成图像: {usage.get('generated_images', 1)}, "
                           f"输出token: {usage.get('output_tokens', 'N/A')}, "
                           f"总token: {usage.get('total_tokens', 'N/A')}")
            
            # 下载并保存图像
            if 'data' in result and len(result['data']) > 0:
                image_url = result['data'][0]['url']
                image_size = result['data'][0].get('size', '未知尺寸')
                logging.info(f"图像尺寸: {image_size}")
                
                # 下载图像
                saved_path = self._download_image(image_url, save_path, prompt)
                result['local_path'] = saved_path
                
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "请求超时，请稍后重试"
            logging.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.ConnectionError:
            error_msg = "网络连接错误，请检查网络设置"
            logging.error(error_msg)
            raise Exception(error_msg)
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
                save_path = os.path.join(FILE_CONFIG['default_output_dir'], filename)
            
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
        output_dir = output_dir or FILE_CONFIG['default_output_dir']
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
                result = self.generate_image(prompt, size=size, save_path=save_path)
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
        # 这里可以添加获取使用量统计的代码
        # 具体实现取决于API是否提供相关端点
        logging.info("使用量统计功能需要API支持相应端点")
        return {"message": "功能待实现"}


def create_prompt_template():
    """
    创建提示词模板示例
    """
    templates = {
        "sci_fi": "星际穿越，黑洞，{object}从黑洞中冲出，电影大片，超现实主义，{color}色调，极致光影",
        "fantasy": "奇幻风格，{creature}在{location}，魔法光芒，详细纹理，史诗场景",
        "realistic": "真实照片风格，{subject}在{environment}，自然光线，细节丰富，{time}",
        "anime": "动漫风格，{character}，{style}画风，色彩鲜艳，大眼睛，精美背景"
    }
    return templates


def main():
    """主函数演示"""
    try:
        # 初始化生成器
        generator = DouBaoImageGenerator()
        
        # 示例提示词
        prompt = """星际穿越，黑洞，黑洞里冲出一辆快支离破碎的复古列车，抢视觉冲击力，电影大片，末日既视感，动感，对比色，oc渲染，光线追踪，动态模糊，景深，超现实主义，深蓝，画面通过细腻的丰富的色彩层次塑造主体与场景，质感真实，暗黑风背景的光影效果营造出氛围，整体兼具艺术幻想感，夸张的广角透视效果，耀光，反射，极致的光影，强引力，吞噬"""
        
        print("开始生成示例图像...")
        # 生成图像
        result = generator.generate_image(prompt)
        
        print("\n" + "="*50)
        print("生成完成!")
        if 'local_path' in result:
            print(f"图像文件: {result['local_path']}")
        
        # 显示使用情况
        if 'usage' in result:
            usage = result['usage']
            print(f"使用情况: {usage.get('generated_images', 1)}张图像, "
                  f"{usage.get('total_tokens', 'N/A')} tokens")
        
    except Exception as e:
        print(f"错误: {e}")
        logging.error(f"主程序执行失败: {e}")


if __name__ == "__main__":
    main()